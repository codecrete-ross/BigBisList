from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
from struct import Struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit

from test_forever_availability import approve, inventory_fixture, run_fixture
from tools import forever_availability, forever_hotfix as hotfix, forever_refresh as refresh
from tools.forever_refresh_http import RefreshHTTP, Unavailable
from tools.project import load_json


class PublicResponse(io.BytesIO):
    status = 200

    def __init__(self, payload, **headers):
        super().__init__(json.dumps(payload).encode())
        self.headers = headers


class RefreshTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.time = datetime(2026, 11, 14, tzinfo=timezone.utc)
        self.elapsed = 0

    def http(self, opener, *, online=True):
        return RefreshHTTP(self.directory, online=online, user_agent="fixture", opener=opener,
                           now=lambda: self.time, monotonic=lambda: self.elapsed, sleep=lambda _: None)

    def runner(self, http, snapshots=None, audit=None, ledger=None):
        return refresh.AvailabilityRefresh(http, set(snapshots or {}), snapshots or {}, audit or {
            "client_build": "1.60.1.70790", "candidate_reviews": [],
        }, {"availability_review_ranges": [], "availability_review_combinations": 0}, ledger or {"entries": []})

    def test_conditional_fetch_and_offline_replay_reuse_the_saved_body(self):
        url = refresh.AH_CATALOGS[0]
        seen = []

        def open_url(request, timeout):
            seen.append(request)
            if len(seen) == 1:
                return PublicResponse({"rows": []}, ETag='"catalog-1"')
            raise HTTPError(url, 304, "unchanged", {}, None)

        raw, first = self.http(open_url).get(url)
        cached, second = self.http(open_url).get(url)
        self.assertEqual(seen[1].get_header("If-none-match"), '"catalog-1"')
        self.assertEqual((raw, first["source_content_digest"]), (cached, second["source_content_digest"]))
        offline = self.http(lambda *_args, **_kwargs: self.fail("Unexpected HTTP request"), online=False)
        self.assertEqual(offline.get(url)[0], raw)
        self.assertEqual(offline.request_count, 0)

    def test_replayed_snapshot_cannot_replace_a_newer_published_catalog(self):
        url = refresh.AH_CATALOGS[0]
        archived = {"url": url, "provider": "ahledger", "page_type": "catalog",
                    "fetched_at": self.time.isoformat(), "catalog_coverage": {"complete": True},
                    "records": [{"item_id": 71}]}
        self.runner(self.http(None, online=False)).stage(archived, [])
        self.time += timedelta(days=1)
        published = {**archived, "fetched_at": self.time.isoformat(), "records": [{"item_id": 71}, {"item_id": 72}]}
        resumed = self.runner(self.http(None, online=False), {url: published})
        self.assertEqual(resumed.snapshots[url], published)
        self.assertNotIn(url, resumed.staged)

    def test_rolling_quest_export_preserves_missing_prior_observations(self):
        url = refresh.AH_QUESTS

        def export(*quest_ids):
            lines = ["# AHledger: fixture", "## Quests (latest)"]
            for identifier in quest_ids:
                lines.append(f"- Quest {identifier} | 20 | Zone | Giver | item {identifier} | - | - | "
                             f"https://ahledger.com/wow-forever/quests/{identifier}-fixture")
            return "\n".join(lines)

        baseline = refresh.sources.normalize_ahledger_text(url, export(71, 72), [], collected_at=self.time.isoformat())
        self.time += timedelta(days=1)
        rolling = refresh.sources.normalize_ahledger_text(url, export(72, 73), [], collected_at=self.time.isoformat())
        # Replay a replacement staged by the older collector.
        self.runner(self.http(None, online=False)).stage(rolling, [])
        runner = self.runner(self.http(None, online=False), {url: baseline})
        self.assertEqual(runner.snapshots[url], baseline)
        receipt = {"source_content_digest": "a" * 64, "collected_at": self.time.isoformat()}
        with patch.object(runner, "read", return_value=(export(72, 73).encode(), receipt)):
            self.assertEqual(runner.refresh_ahledger(url), "changed")
            self.assertEqual(runner.refresh_ahledger(url), "unchanged")
        archived = runner.snapshots[f"{url}#observations-{'a' * 64}"]
        self.assertEqual(runner.snapshots[url], baseline)
        self.assertEqual([row["quest_id"] for row in archived["records"]], [73])
        self.assertEqual([row["object_id"] for row in archived["relationships"]], [73])
        self.assertEqual(set(runner.evidence_changes({url: baseline})), {("item", 73), ("quest", 73)})

    def test_rate_limit_keeps_complete_snapshot_and_resume_reuses_prefix(self):
        url = refresh.EVERLOOT_FEEDS[0]
        tail = url + "&offset=1"
        credit = {"credit": "Everloot contributors", "licence": "CC BY-SA 4.0",
                  "licenceUrl": "https://creativecommons.org/licenses/by-sa/4.0/", "source": url}
        page = {"limit": 1, "total": 2, "dataAsOf": "revision-a", "attribution": credit}
        before = {"url": url, "provider": "everloot", "flavor": "forever", "page_type": "observations", "records": []}
        calls = []

        def open_page(request, timeout):
            calls.append(request.full_url)
            if request.full_url == url:
                return PublicResponse({**page, "records": [{"kind": "item_fact", "itemId": 71}], "offset": 0, "next": tail})
            if len(calls) == 2:
                raise HTTPError(tail, 429, "wait", {"Retry-After": "60"}, None)
            return PublicResponse({**page, "records": [{"kind": "item_fact", "itemId": 72}], "offset": 1, "next": None})

        with self.assertRaises(Unavailable) as error:
            self.runner(self.http(open_page), {url: before}).refresh_everloot(url)
        self.assertEqual(error.exception.status, 429)
        self.assertEqual(error.exception.retry_at, (self.time + timedelta(minutes=1)).isoformat())
        blocked = self.runner(self.http(open_page), {url: before})
        self.assertEqual(blocked.snapshots[url], before)
        with self.assertRaisesRegex(Unavailable, "cooldown"):
            blocked.refresh_everloot(url)
        self.assertEqual(calls, [url, tail])

        self.time += timedelta(minutes=1)
        resumed = self.runner(self.http(open_page), {url: before})
        self.assertEqual(resumed.refresh_everloot(url), "changed")
        self.assertEqual(calls, [url, tail, tail])
        self.assertEqual(resumed.snapshots[url]["attribution"], [credit])
        self.assertEqual(len(resumed.snapshots[url]["records"]), 2)

    def test_forbidden_host_defers_later_listings_and_preserves_staged_catalog(self):
        base = refresh.sources.WOWHEAD_ROOT + "items/armor/slot:11"
        snapshot = {"url": base, "provider": "wowhead", "page_type": "catalog", "records": [{"item_id": 71, "slot": "Ring"}],
                    "catalog_coverage": {"complete": True}, "fetched_at": self.time.isoformat()}
        seen = []

        def reject(request, timeout):
            seen.append(request.full_url)
            raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

        runner = self.runner(self.http(reject))
        runner.stage(snapshot, [])
        runner.collect(base, lambda: runner.refresh_listing(base), source_url=base)
        other = base + "/quality:1"
        runner.collect(other, lambda: runner.refresh_listing(other), source_url=other)
        self.assertEqual(seen, [base])
        self.assertEqual(runner.staged[base], snapshot)
        self.assertIn("cooldown", runner.bulk_results[other]["reason"])
        with self.assertRaisesRegex(ValueError, "partial catalog"):
            runner.stage({**snapshot, "catalog_coverage": {"complete": False}, "records": []}, [])

    def test_deadline_and_attempt_budget_stop_requests(self):
        url = refresh.AH_CATALOGS[0]
        http = self.http(lambda *args, **kwargs: self.fail("Budget permitted an HTTP call"))
        with patch("tools.forever_refresh_http.MAX_REQUESTS", 0), self.assertRaisesRegex(Unavailable, "budget"):
            http.get(url)
        self.elapsed = 301
        with self.assertRaisesRegex(Unavailable, "budget"):
            http.get(url)
        self.assertEqual(http.request_count, 0)

    def test_everloot_hourly_budget_is_shared_across_refreshes(self):
        def success(*_args, **_kwargs):
            return PublicResponse({"records": []})

        first, second = refresh.EVERLOOT_FEEDS
        with patch("tools.forever_refresh_http.EVERLOOT_HOURLY_LIMIT", 1):
            self.http(success).get(first)
            with self.assertRaisesRegex(Unavailable, "hourly"):
                self.http(success).get(second)
            self.time += timedelta(hours=1)
            self.http(success).get(second)

    def test_retry_waits_a_week_and_uses_entry_build(self):
        url = refresh.sources.WOWHEAD_ROOT + "item=71"
        old = self.time - timedelta(days=2)
        entry = {"url": url, "status": "pending", "last_attempt_at": old.isoformat(), "history": [
            {"at": old.isoformat(), "audit_client_build": "1.60.1.70790"}]}
        runner = self.runner(self.http(None, online=False), ledger={"entries": [entry], "client_build": "1.60.1.70000"})
        self.assertEqual(runner.next_attempt(url, "a", {"changed": []}), (False, (old + timedelta(days=7)).isoformat()))
        self.assertTrue(runner.next_attempt(url, "b", {"changed": [71]})[0])
        self.time += timedelta(days=5)
        self.assertTrue(runner.next_attempt(url, "a", {"changed": []})[0])

    def test_unrevealed_registry_requires_complete_current_ids_and_only_triggers_on_a_change(self):
        build = "1.60.1.70790"
        url = refresh.sources.ZEPHRAS_UNREVEALED
        body = ('<main>Current build · ' + build + '<h2>Not revealed yet 1</h2><table>'
                '<tr data-id="71"><td><span class="loot-item">Item 71</span></td></tr></table></main>')

        def collect(html):
            return refresh.sources.normalize_zephras_disclosures(html, build, {71, 72},
                collected_at=self.time.isoformat(), digest="fixture")

        old = collect(body)
        header_build = f'<header><a class="build-stamp" href="/builds/">Build {build}</a></header>'
        self.assertEqual(collect(header_build + body.replace("Current build · " + build, "")), old)
        with self.assertRaisesRegex(ValueError, "client build"):
            collect(header_build.replace(build, "1.60.1.70938") + body)
        self.assertEqual(old["records"][0]["state"], "unrevealed")
        self.assertNotIn(("item", 71), refresh.exact_facts(old))
        self.assertNotIn("required_level", old["records"][0])
        with self.assertRaisesRegex(ValueError, "reconcile"):
            collect(body.replace("revealed yet 1", "revealed yet 2"))
        with self.assertRaisesRegex(ValueError, "client build"):
            collect(body.replace(build, "1.60.1.70938"))
        runner = self.runner(self.http(None, online=False), {url: old})
        runner.stage(collect(body.replace("71", "72")), [])
        changes = runner.evidence_changes({url: old})
        self.assertEqual(changes[("item", 71)][0]["added"][0]["disclosure_state"], "not_on_unrevealed_list")

    def test_eg_link_disclosure_comparison_uses_prior_pinned_release(self):
        build = "1.60.1.70790"
        dataset = "item_hotfixes.enUS"
        meta = {"product": "wowf", "clientBuild": build, "dataset": "item_hotfixes", "sources": 1,
                "license": "CC BY 4.0", "attribution": "fixture"}

        def publish(commit, first_state):
            url = f"{refresh.eg_link.ROOT}/{commit * 40}/data/wowf/{build}/{dataset}.json"
            payload = {"meta": meta, "items": {"71": {"status": first_state, "pushId": 2, "sources": 1},
                                              "72": {"status": "valid", "name": "Known", "pushId": 1, "sources": 1}}}
            return refresh.eg_link.normalize(url, dataset, payload, build, {"item": {71, 72}},
                collected_at=self.time.isoformat(), digest="fixture")

        old = publish("a", "invalid")
        self.assertNotIn(("item", 71), refresh.exact_facts(old))
        self.assertEqual(refresh.sources.source_provider(old["url"]), "eg_link")
        self.time += timedelta(days=1)
        runner = self.runner(self.http(None, online=False), {old["url"]: old})
        runner.stage(publish("b", "valid"), [])
        self.assertEqual(set(runner.evidence_changes({old["url"]: old})), {("item", 71)})

    def test_staged_candidate_opens_approved_ranges_and_later_gate_excludes_it(self):
        snapshots, docs = inventory_fixture()
        approve(run_fixture(snapshots, docs, diagnostic=True), docs)
        initial = run_fixture(snapshots, docs)
        http = self.http(None, online=False)
        runner = self.runner(http, snapshots, initial["leveling_candidate_audit"])
        url = refresh.sources.WOWHEAD_ROOT + "item=999"
        item = {"url": url, "flavor": "forever", "provider": "wowhead", "page_type": "item", "item_kind": "equipment",
                "item_id": 999, "item_stats": {"slot": "Ring", "required_level": 1}}
        runner.stage(item, [], entity=True)
        after = run_fixture(runner.snapshots, docs, diagnostic=True)
        affected = next(row for row in after["leveling_candidate_audit"]["candidate_reviews"] if row["item_id"] == 999)
        self.assertGreater(affected["affected"]["combinations"], 9)
        self.assertTrue(after["coverage"]["review_issues"])
        self.assertNotIn(url, snapshots)

        item = {**item, "item_stats": {**item["item_stats"], "required_level": 14}}
        runner.stage(item, [], entity=True)
        resolved = run_fixture(runner.snapshots, docs, diagnostic=True)
        row = next(row for row in resolved["leveling_candidate_audit"]["candidate_reviews"] if row["item_id"] == 999)
        self.assertNotIn("affected", row)
        self.assertEqual(row["status"], "excluded_from_current_missing_scopes")

        tooltip_url = "https://nether.wowhead.com/forever/tooltip/item/999"
        runner.stage({**item, "url": tooltip_url, "item_stats": {**item["item_stats"], "required_level": 1}}, [])
        conflict = run_fixture(runner.snapshots, docs, diagnostic=True)
        self.assertGreater(conflict["coverage"]["summary"]["uncovered_combinations"], 0)
        self.assertTrue(any(row["item_id"] == 999 and row["status"].startswith("pending_")
                            for row in conflict["leveling_candidate_audit"]["candidate_reviews"]))
        state = load_json(self.directory / "state.json")
        self.assertTrue(state["snapshots"][url]["target"].startswith("data/raw/wowhead/forever/"))

    def test_sitemap_is_discovery_only(self):
        url = refresh.sources.WOWHEAD_ROOT + "item=71/a-ring"
        ids, pages = refresh.sitemap_page(f"<urlset><url><loc>{url}</loc></url></urlset>".encode())
        self.assertEqual((ids, pages), ({71}, []))
        with self.assertRaises(ValueError):
            refresh.sitemap_page(b"<html>No results</html>")
        snapshot = {"url": refresh.SITEMAP, "page_type": "reference", "records": [{"item_id": 71}]}
        result = forever_availability.build_inventory({refresh.SITEMAP: snapshot}, {}, {}, {})
        self.assertEqual(result["candidate_count"], 0)

    def test_exact_queue_follows_a_staged_quest_starter_link(self):
        open_rows = [{"item_id": 71, "status": "pending_availability_review", "route_leads": [
            {"subject_type": "item", "subject_id": 90, "relation": "contains"}]}]
        runner = self.runner(self.http(None, online=False), audit={"client_build": "1.60.1.70790", "candidate_reviews": open_rows})
        base = refresh.sources.WOWHEAD_ROOT
        runner.stage({"url": base + "item=90", "provider": "wowhead", "page_type": "item", "item_id": 90,
                      "item_kind": "quest_starter", "linked_entities": [{"type": "quest", "id": 321}]}, [], entity=True)
        target = runner.exact_targets({})[base + "quest=321"]
        self.assertEqual(target["items"], {71})
        self.assertTrue(target["changed"])

    def test_successful_http_challenge_body_is_not_an_item(self):
        runner = self.runner(self.http(None, online=False))
        receipt = {"collected_at": self.time.isoformat()}
        with patch.object(runner, "read", side_effect=[Unavailable("no cached tooltip"), (b"<title>Just a moment</title>", receipt)]):
            with self.assertRaisesRegex(ValueError, "no exact item tooltip"):
                runner.refresh_exact(refresh.sources.WOWHEAD_ROOT + "item=999", "revision")
        self.assertFalse(runner.staged)

    def test_identical_wago_exports_keep_reviewed_corrections(self):
        build = "1.60.1.70790"
        tables = {"Item": "ID,InventoryType,ClassID,SubclassID\n71,11,4,0\n",
                  "ItemSparse": "ID,RequiredLevel,AllowableClass\n72,4,8\n",
                  "ItemSearchName": "ID,RequiredLevel,AllowableClass\n72,4,8\n"}
        baseline = forever_availability.normalize_client_catalog(tables, build, collected_at=self.time.isoformat())
        baseline["records"][0]["class_mask"] = -1
        runner = self.runner(self.http(None, online=False), {baseline["url"]: baseline})

        def read(url, **_kwargs):
            table = urlsplit(url).path.split("/")[-2]
            return tables[table].encode(), {"collected_at": self.time.isoformat()}

        with patch.object(runner, "read", side_effect=read):
            self.assertEqual(runner.refresh_client(), "unchanged")
        self.assertEqual(runner.client_ids, {71, 72})
        self.assertEqual(runner.snapshots[baseline["url"]]["records"][0]["class_mask"], -1)
        self.assertFalse(runner.staged)

    def test_hotfix_cache_retains_exact_build_and_leaves_withheld_rows_unknown(self):
        table = 17
        layout = {"ItemSparse": (table, [("RequiredLevel", Struct("<B"))])}
        raw = hotfix.FILE_HEADER.pack(b"XFTH", 9, 70790).ljust(44, b"\0")

        def row(item_id, push, state, body):
            return hotfix.ROW_HEADER.pack(b"XFTH", 0, push, 0, table, item_id, len(body), state) + body

        raw += row(71, 1, 1, b"\x15") + row(71, 2, 3, b"") + row(72, 2, 1, b"\x07")
        parsed, quests = hotfix.read_cache(raw, "1.60.1.70790", layout)
        self.assertEqual(set(parsed["ItemSparse"]), {72})
        self.assertEqual(parsed["ItemSparse"][72][0], {"RequiredLevel": 7})
        self.assertEqual(quests, {})
        with self.assertRaisesRegex(ValueError, "reviewed build"):
            hotfix.read_cache(raw, "1.60.1.70938", layout)
        with self.assertRaisesRegex(ValueError, "row header"):
            hotfix.read_cache(raw[:-1], "1.60.1.70790", layout)


if __name__ == "__main__":
    unittest.main()
