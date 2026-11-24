from pathlib import Path
from subprocess import CompletedProcess
import unittest
from unittest.mock import patch

from tools import forever, forever_availability as availability, forever_eg_link as eg_link
from tools import forever_review_carry as carry, forever_sources as sources
from tools.forever_catalog import CountedCatalog, ETERNA, ICY
from tools.forever_refresh import snapshot_content
from tools.forever_refresh_http import windows_https


BUILD = "1.60.1.70938"
AH = "https://ahledger.com/api/catalog?class=armor"
WHEN = "2026-11-15T03:00:00Z"
REVIEW = {"reviewer": "fixture", "reason": "fixture renewal", "reviewed_at": "2026-11-14", "client_build": BUILD}


def icy_page(first, last, total, ids):
    rows = "".join(f'<tr><td>{i}</td><td><a href="/wow-forever/items/{i}">Item #{i}</a></td><td>—</td></tr>'
                   for i in ids)
    return f"<p>Browse all {total} items in the Shields category</p>{first}–{last} of {total} items<table><tbody>{rows}</tbody></table>".encode()


class ForeverUnblockTests(unittest.TestCase):
    def test_counted_catalog_keeps_unknown_requirements_and_rejects_unstable_pages(self):
        urls = [ICY + f"armor/shields/?sort=id&dir=desc&page={page}" for page in (1, 2)]
        pages = {urls[0]: icy_page(1, 2, 3, [71, 32]), urls[1]: icy_page(3, 3, 3, [11])}
        catalog = CountedCatalog(lambda url: (pages[url], {"collected_at": WHEN}), BUILD, {71}, {32})
        result = catalog.icy(14)
        self.assertEqual(result["catalog_coverage"]["total"], 3)
        self.assertEqual(result["catalog_coverage"]["inventory_types"], [14])
        self.assertEqual(result["reconciliation"]["listing_only_ids"], [11])
        self.assertEqual(result["records"][0], {"item_id": 11, "slot": "Off Hand"})
        self.assertEqual(sources.source_provider(result["url"]), "icyveins")
        for body, message in ((icy_page(3, 3, 4, [11]), "pagination changed"),
                              (icy_page(3, 3, 3, [32]), "repeat"),
                              (icy_page(3, 3, 3, []), "page count")):
            with self.subTest(message=message):
                pages[urls[1]] = body
                catalog.pages.clear()
                with self.assertRaisesRegex(ValueError, message):
                    catalog.icy(14)

    def test_windows_https_preserves_error_headers_and_system_certificate_verification(self):
        payload = b"HTTP/1.1 429 Too Many Requests\r\nRetry-After: 60\r\n\r\nslow down"
        with patch("tools.forever_refresh_http.subprocess.run", return_value=CompletedProcess([], 0, payload, b"")) as run:
            code, fields, body = windows_https(Path("curl.exe"), "https://everloot.app/", {"If-None-Match": '"catalog"'}, 2)
        self.assertEqual((code, fields["retry-after"], body), (429, "60", b"slow down"))
        args = run.call_args.args[0]
        self.assertEqual(args[1], "--disable")
        self.assertIn("=https", args)
        self.assertIn('If-None-Match: "catalog"', args)
        self.assertNotIn("--insecure", args)

    def test_eternadex_counts_match_category_index_and_all_pages(self):
        home = ETERNA + "schilde/"
        def shield_page(ids, page_link):
            rows = "".join(f'<tr><td><a href="/en/item/{i}/">Shield</a></td></tr>' for i in ids)
            return f'<main>3 items, sorted by level<table><tbody>{rows}</tbody></table>{page_link}</main>'.encode()

        pages = {ETERNA: b'<section><h2>Armor</h2><ul><li><a href="schilde/">Shields</a> 3</li></ul></section>',
                 home: shield_page([71, 32], '<a href="2/">2</a>'), home + "2/": shield_page([11], "")}
        catalog = CountedCatalog(lambda url: (pages[url], {"collected_at": WHEN}), BUILD, {71}, {32})
        self.assertEqual(catalog.eternadex(14)["reconciliation"]["listing_only_ids"], [11])
        self.assertIsNone(sources.source_provider(home + "#inventory-type-22"))
        catalog.pages.clear()
        pages[home] = shield_page([71, 32], "")
        with self.assertRaisesRegex(ValueError, "Missing Eternadex page 2"):
            catalog.eternadex(14)

    def test_everloot_accepts_sorted_kinds_in_the_next_page_url(self):
        url = "https://everloot.app/api/corpus/public?kinds=quest,item_fact&limit=1"
        next_url = "https://everloot.app/api/corpus/public?kinds=item_fact%2Cquest&limit=1&offset=1"
        attribution = {"credit": "fixture", "licence": "CC BY-SA 4.0", "licenceUrl": "test", "source": url}
        envelope = {"total": 2, "limit": 1, "dataAsOf": WHEN, "kinds": ["item_fact", "quest"], "attribution": attribution}
        pages = {url: {**envelope, "records": [{"kind": "quest"}], "offset": 0, "next": next_url},
                 next_url: {**envelope, "records": [{"kind": "item_fact"}], "offset": 1, "next": None}}
        self.assertEqual(len(sources.collect_everloot(url, pages.__getitem__, collected_at=WHEN)["records"]), 2)
        pages[next_url]["dataAsOf"] = "changed"
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            sources.collect_everloot(url, pages.__getitem__, collected_at=WHEN)

    def test_durability_display_keeps_the_original_tooltip_binding(self):
        item = {"url": "https://www.wowhead.com/forever/item=71", "page_type": "item", "description": "Cloth +8 Spirit"}
        repeat = {**item, "provider": "wowhead", "description": "Cloth Durability 40 / 40 +8 Spirit"}
        self.assertEqual(snapshot_content(item), snapshot_content(repeat))
        self.assertNotEqual(snapshot_content(item), snapshot_content({**repeat, "description": "+9 Spirit"}))

    def test_additive_catalog_preserves_the_reviewed_item_and_original_receipt(self):
        exclusion_url = "https://www.wowhead.com/forever/item=71"
        cover = {"slots": ["Ring"], "inventory_types": [11], "qualities": list(range(8)),
                 "level_min": 1, "level_max": 59, "total": 1, "complete": True}
        market = {"url": AH, "provider": "ahledger", "page_type": "catalog", "catalog_kind": "ahledger_catalog",
                  "records": [{"item_id": 71, "slot": "Ring", "required_level": None}], "catalog_coverage": cover}
        snapshots = {AH: market, exclusion_url: {"url": exclusion_url, "unavailable_item_ids": [71]}}
        rules = {"review": {"client_build": BUILD}}
        document = {"version": availability.INVENTORY_VERSION, "client_build": BUILD, "source_reviews": [
            {**REVIEW, "kind": "ahledger_catalog", "record_count": 1, "source_url": AH,
             "evidence_refs": [sources.evidence_ref(AH, snapshots)]}]}
        old = availability.build_inventory(snapshots, document, rules, forever.evidence_index(snapshots))
        review = {**REVIEW, "source_url": exclusion_url, "exclusion": "unavailable", "item_id": 71,
                  "candidate_digest": old["candidates"][0]["candidate_digest"],
                  "evidence_refs": [sources.evidence_ref(url, snapshots) for url in snapshots]}
        document["decisions"] = [review]
        carried = carry.scoped_reviews({"availability": document}, snapshots, rules)
        appended = {**snapshots, AH: {**market, "catalog_coverage": {**cover, "total": 2},
                    "records": [*market["records"], {"item_id": 99, "slot": "Off Hand"}]}}
        carried = carry.carry_additive_catalogs(carried, snapshots, appended)["availability"]
        inventory = availability.build_inventory(appended, carried, rules, forever.evidence_index(appended))
        self.assertFalse(inventory["source_issues"] or inventory["decision_issues"])
        self.assertEqual(carried["decisions"][0]["evidence_refs"], review["evidence_refs"])
        appended[AH]["records"][0] = {"item_id": 71, "slot": "Ring", "required_level": 9}
        refreshed = availability.build_inventory(appended, carried, rules, forever.evidence_index(appended))
        self.assertEqual(refreshed["decision_issues"][0]["item_id"], 71)

    def test_market_corroboration_does_not_change_an_exact_equipment_proof(self):
        fact = {"name": "Ring of Evidence", "slot": "Ring", "required_level": 5}
        client = {**fact, "kind": "client_hotfix", "client_build": BUILD}
        market = {**fact, "kind": "ahledger_catalog", "slot": "FINGER", "subclass": "Miscellaneous"}
        candidate = {"item_id": 71, "slots": ["Ring"], "observations": [client]}
        expected = availability.candidate_proof(candidate, scoped=True, client_build=BUILD)
        candidate["observations"].append(market)
        self.assertEqual(availability.candidate_proof(candidate, scoped=True, client_build=BUILD), expected)
        market["required_level"] = 7
        self.assertNotEqual(availability.candidate_proof(candidate, scoped=True, client_build=BUILD), expected)

    def test_pinned_prerequisite_changes_only_the_linked_item_proof(self):
        root = f"{eg_link.ROOT}/{'a' * 40}/data/wowf/{BUILD}"
        url = root + "/quests.enUS.json"
        gate = root + "/quest_prerequisites.json"
        ids = {"item": {71, 72}, "quest": set()}
        meta = {"product": "wowf", "clientBuild": BUILD, "sources": 1, "license": "CC BY 4.0", "attribution": "fixture"}
        quests = {"917": {"minLevel": 11, "rewards": {"items": [{"itemId": 71}]}},
                  "918": {"minLevel": 20, "rewards": {"items": [{"itemId": 72}]}}}
        snapshots = {url: eg_link.normalize(url, "quests.enUS", {"meta": {**meta, "dataset": "quests"}, "quests": quests},
                                             BUILD, ids, collected_at=WHEN, digest="fixture")}
        urls = {i: f"https://www.wowhead.com/forever/item={i}" for i in ids["item"]}
        for item, source in urls.items():
            snapshots[source] = {"url": source, "page_type": "item", "item_id": item, "item_stats": {"slot": "Ring"}}
        document = {"client_build": BUILD, "version": availability.INVENTORY_VERSION, "proof_version": availability.SCOPED_PROOFS}
        records = forever.evidence_index(snapshots)
        previous = availability.item_acquisition_digests(snapshots, records, scoped=True)
        inventory = availability.build_inventory(snapshots, document, {}, records)
        document["decisions"] = [
            {**REVIEW, "exclusion": "unavailable", "item_id": row["item_id"], "candidate_digest": row["candidate_digest"],
             "item_acquisition_digest": previous[row["item_id"]], "source_url": urls[row["item_id"]],
             "evidence_refs": [sources.evidence_ref(urls[row["item_id"]], snapshots)]} for row in inventory["candidates"]]
        self.assertFalse(availability.build_inventory(snapshots, document, {}, records)["decision_issues"])
        snapshots[gate] = eg_link.normalize(gate, "quest_prerequisites", {"meta": {**meta, "dataset": "quest_prerequisites"},
            "quests": {"917": {"prerequisites": [11]}}}, BUILD, ids, collected_at=WHEN, digest="fixture")
        changed = availability.build_inventory(snapshots, document, {}, forever.evidence_index(snapshots))
        self.assertEqual(changed["decision_issues"], [{"item_id": 71, "reason": "Stale acquisition availability decision"}])
