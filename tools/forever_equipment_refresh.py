"""Stage Guide equipment facts using the existing Forever refresh receipts."""

from datetime import timedelta
import json
import re

from tools import forever, forever_eg_link as eg_link
from tools.forever_comparison import comparison_document
from tools.forever_equipment import equipment_report, reviewed_equipment
from tools.forever_equipment_sources import (ARMOR_TABLES, LIBITEMDB_URL, WOWSIMS_HEAD, WOWSIMS_ROOT, client_armor,
                                             normalize_libitemdb, normalize_wowsims, publication_key, wowsims_build)
from tools.forever_refresh_http import Unavailable, timestamp
from tools.forever_sources import WOWHEAD_ROOT, canonical_url
from tools.project import dataset_json


TOOLTIPS = "https://nether.wowhead.com/forever/tooltip/item/"
FORMAT = 1
BULK_FORMAT = 2
ROUTE_EXPORTS = ("quests.enUS", "vendors", "loot")


class EquipmentRefresh:
    def __init__(self, refresh, catalog: dict, revision: str | None):
        self.refresh = refresh
        self.http = refresh.http
        self.catalog = catalog
        self.build = catalog["client_build"]
        self.revision = revision
        self.lookups = self.http.state.setdefault("equipment_exact", {})
        self.ledger = refresh.ledger
        self.reviewed = reviewed_equipment()
        self.published = dataset_json("forever", "comparison_item_stats")
        self.item_ids = {row[0] for row in catalog["items"]} | {row["id"] for row in self.published["items"] + self.reviewed[0]}

    def _revision(self, head_url: str, cached_pattern: str) -> tuple[str, list[dict]]:
        if not self.http.online and head_url not in self.http.state["requests"]:
            candidates = [(timestamp(receipt["collected_at"]), match[1])
                          for url, receipt in self.http.state["requests"].items()
                          if (match := re.fullmatch(cached_pattern, url))]
            if not candidates:
                raise Unavailable("No cached publication index")
            return max(candidates)[1], []
        raw, receipt = self.refresh.read(head_url)
        commit = json.loads(raw)[0]["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Invalid equipment source revision")
        return commit, [receipt]

    def _wowsims(self) -> str:
        if self.revision:
            revision, receipts = self.revision, []
        else:
            revision, receipts = self._revision(WOWSIMS_HEAD, re.escape(WOWSIMS_ROOT) + r"/([0-9a-f]{40})/state\.json")
        root = f"{WOWSIMS_ROOT}/{revision}"
        state, state_receipt = self.refresh.read(f"{root}/state.json", immutable=True)
        observed_build = wowsims_build(state)
        if observed_build != self.build:
            return f"build_mismatch:{observed_build}"
        url = f"{root}/items/items.txt"
        current = self.refresh.snapshots
        if current.get(url, {}).get("parser_version") == BULK_FORMAT:
            self.item_ids.update(item["id"] for item in current[url]["items"])
            return "unchanged"
        raw, receipt = self.refresh.read(url, immutable=True)
        snapshot = normalize_wowsims(url, raw, state, receipt["collected_at"])
        snapshot["parser_version"] = BULK_FORMAT
        prior = {}
        for source in sorted(current.values(), key=publication_key):
            if source.get("confidence") == "client_equipment_export" and source.get("client_build") == self.build and source["url"] != url:
                prior.update((item["id"], item) for item in source["items"])
        self.item_ids.update(item["id"] for item in snapshot["items"])
        snapshot["items"] = [item for item in snapshot["items"] if prior.get(item["id"]) != item]
        if not snapshot["items"]:
            return "unchanged"
        return "changed" if self.refresh.stage(snapshot, [*receipts, state_receipt, receipt]) else "unchanged"

    def _libitemdb(self) -> str:
        if LIBITEMDB_URL in self.refresh.snapshots:
            return "unchanged"
        raw, receipt = self.http.get(LIBITEMDB_URL, immutable=True, project_cache=self.http.directory / "libitemdb-v1.10.0.zip")
        snapshot = normalize_libitemdb(raw, receipt["collected_at"])
        return "changed" if self.refresh.stage(snapshot, [receipt]) else "unchanged"

    def _armor(self) -> str:
        root = "https://wago.tools/db2"
        address = f"{root}/ItemSparse/csv?build={self.build}#gear-guide-armor"
        equipment = {}
        for snapshot in sorted(self.refresh.snapshots.values(), key=publication_key):
            if snapshot.get("confidence") == "client_equipment_export" and snapshot.get("client_build") == self.build:
                equipment.update((item["id"], item) for item in snapshot["items"])
        if not equipment:
            return "no_equipment_export"
        inputs = forever.digest(equipment)
        previous = self.refresh.snapshots.get(address, {})
        if previous.get("targets") == inputs and previous.get("parser_version") == BULK_FORMAT:
            return "unchanged"
        responses = {name: self.http.get(f"{root}/{name}/csv?build={self.build}", immutable=True) for name in ARMOR_TABLES}
        receipts = [receipt for _, receipt in responses.values()]
        snapshot = client_armor({name: raw for name, (raw, _) in responses.items()}, equipment, self.build, address,
                                max(row["collected_at"] for row in receipts))
        prior = {row["id"]: row for row in previous.get("items", [])} if previous.get("parser_version") == BULK_FORMAT else {}
        prior.update((row["id"], row) for row in snapshot["items"])
        snapshot.update(targets=inputs, parser_version=BULK_FORMAT, items=[prior[key] for key in sorted(prior)])
        return "changed" if self.refresh.stage(snapshot, receipts) else "unchanged"

    def _routes(self) -> str:
        from tools.forever_sources import public_observation

        commit, receipts = self._revision(eg_link.HEAD_URL,
            re.escape(eg_link.ROOT) + rf"/([0-9a-f]{{40}})/data/wowf/{re.escape(self.build)}/(?:quests\.enUS|vendors|loot)\.json")
        root = f"{eg_link.ROOT}/{commit}/data/wowf/{self.build}"
        ids = eg_link.acquisition_ids({identifier: {} for identifier in self.item_ids})
        scope = forever.digest(sorted(self.item_ids))
        checked = self.http.state.setdefault("equipment_route_targets", {})

        def collect_export(name):
            url = f"{root}/{name}.json"
            address = f"{url}#gear-guide"
            previous = self.refresh.snapshots.get(address, {})
            if previous.get("targets") == scope or checked.get(address) == scope:
                return "unchanged"
            raw, receipt = self.refresh.read(url, immutable=True)
            publication = eg_link.normalize(address, name, json.loads(raw), self.build, ids,
                collected_at=receipt["collected_at"], digest=receipt["source_content_digest"])
            snapshot = {key: publication[key] for key in ("url", "provider", "flavor", "client_build", "fetched_at",
                                                             "source_content_digest", "confidence", "attribution")}
            snapshot.update(page_type="equipment_routes", targets=scope,
                            relationships=public_observation(publication["relationships"]))
            def identity(edge):
                return forever.digest({key: value for key, value in edge.items() if key != "source_url"})

            old = {identity(edge) for source in self.refresh.snapshots.values()
                   if source.get("page_type") == "equipment_routes" and source.get("client_build") == self.build and source["url"] != address
                   for edge in source["relationships"]}
            snapshot["relationships"] = [edge for edge in snapshot["relationships"] if identity(edge) not in old]
            changed = bool(snapshot["relationships"]) and self.refresh.stage(snapshot, [*receipts, receipt])
            checked[address] = scope
            self.http.checkpoint()
            return "changed" if changed else "unchanged"

        for name in ROUTE_EXPORTS:
            self.refresh.collect(f"equipment_routes:{name}", lambda: collect_export(name), source_url=f"{root}/{name}.json")
        return "checked"

    def collect_bulk(self) -> None:
        self.refresh.collect("equipment_wowsims", self._wowsims, source_url=WOWSIMS_HEAD)
        self.refresh.collect("equipment_libitemdb", self._libitemdb, source_url=LIBITEMDB_URL)
        self.refresh.collect("equipment_routes", self._routes, source_url=eg_link.HEAD_URL)
        self.refresh.collect("equipment_armor_tables", self._armor,
                             source_url=f"https://wago.tools/db2/ItemSparse/csv?build={self.build}")

    def _refresh_tooltip(self, identifier: int, cycle: str, *, cached: bool = False) -> bool:
        from tools.scrape_wowhead import PARSER_VERSION, parse_item_tooltip_endpoint

        url = f"{TOOLTIPS}{identifier}"
        raw, receipt = self.http.get(url, cycle=cycle, immutable=cached or not self.http.online)
        digest = receipt["source_content_digest"]
        address = f"{url}#sha256-{digest}"
        parser_version = f"{PARSER_VERSION}/equipment-{FORMAT}"
        if self.refresh.snapshots.get(address, {}).get("parser_version") == parser_version:
            return False
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not payload.get("name") or not payload.get("tooltip"):
            raise ValueError("Missing Forever item tooltip")
        item = parse_item_tooltip_endpoint(canonical_url(WOWHEAD_ROOT + f"item={identifier}"), raw.decode("utf-8-sig"))
        if item.get("item_kind") != "equipment" or not item.get("item_stats", {}).get("slot"):
            raise ValueError("No supported equipment facts in the exact Forever tooltip")
        snapshot = {"url": address, "flavor": "forever", "provider": "wowhead", "page_type": "equipment_facts",
                    "confidence": "forever_tooltip", "fetched_at": receipt["collected_at"], "source_content_digest": digest,
                    "item_id": identifier, "normalized_sources": item["normalized_sources"],
                    "items": [{**item["item_stats"], "description": item["description"]}], "parser_version": parser_version}
        return self.refresh.stage(snapshot, [receipt])

    def _document(self) -> dict:
        return comparison_document(self.refresh.snapshots, self.catalog)

    def _report(self, document: dict, *, snapshots: dict | None = None) -> dict:
        if snapshots is None:
            snapshots = self.refresh.snapshots
        return equipment_report(document, self.catalog, snapshots, self.reviewed,
                                ledger={"entries": list(self.ledger.values())}, lookups=self.lookups)

    def collect_exact(self, *, max_requests: int | None = None) -> dict:
        from tools.scrape_wowhead import PARSER_VERSION

        snapshots = self.refresh.snapshots
        for url, receipt in self.http.state["requests"].items():
            if not url.startswith(TOOLTIPS):
                continue
            address = f"{url}#sha256-{receipt['source_content_digest']}"
            previous = snapshots.get(address)
            if previous and previous.get("parser_version") != f"{PARSER_VERSION}/equipment-{FORMAT}":
                self.refresh.collect(f"cached_equipment:{url}", lambda: self._refresh_tooltip(int(url.removeprefix(TOOLTIPS)), "", cached=True),
                                     source_url=url)
        document = self._document()
        before_exact = self._report(document)
        queued = []
        for key, item in before_exact["items"].items():
            identifier = item["id"]
            if key != str(identifier):
                continue
            url = f"{TOOLTIPS}{identifier}"
            has_cache = url in self.http.state["requests"]
            conflicts = [conflict for conflict in item.get("conflicts", []) if conflict["needs_tooltip"]]
            if not (item["missing"] or conflicts) or (not self.http.online and not has_cache):
                continue
            attempt = self.lookups.get(url, {})
            prior = self.ledger.get(WOWHEAD_ROOT + f"item={identifier}", {})
            revision = forever.digest([PARSER_VERSION, FORMAT, self.build, item["missing"], conflicts, item.get("sources"),
                                      self.http.state.get("disclosure_triggers", {}).get(str(identifier))])
            now = self.http.now()
            if timestamp(attempt.get("retry_at")) > now and (attempt.get("revision") == revision or attempt.get("provider_cooldown")):
                continue
            # Give each item a first pass, then retry the oldest attempts.
            # Persistent disagreements cannot keep fresh cases behind them.
            order = (not (has_cache and not attempt), bool(attempt), timestamp(attempt.get("attempted_at")),
                     not conflicts, "weapon" not in item["missing"], timestamp(prior.get("last_attempt_at")), identifier)
            queued.append((order, url, revision, identifier))

        starting = self.http.request_count
        changed = False
        for _, url, revision, identifier in sorted(queued):
            if max_requests is not None and self.http.request_count - starting >= max_requests:
                break
            if self.http.request_count >= self.http.request_limit:
                break
            prior = self.lookups.get(url, {})
            cycle = prior["attempted_at"] if prior.get("revision") == revision and prior.get("attempted_at") else revision
            try:
                changed |= self._refresh_tooltip(identifier, cycle)
                status, reason, cooldown = "collected", None, None
            except (Unavailable, ValueError, KeyError, TypeError) as exc:
                if isinstance(exc, Unavailable) and exc.status is None:
                    if self.http.online and (exc.retry_at or "budget" in str(exc)):
                        break
                    continue
                status, reason, cooldown = "pending", str(exc), getattr(exc, "retry_at", None)
            if self.http.online:
                now = self.http.now()
                self.lookups[url] = {"revision": revision, "status": status, "reason": reason,
                                     "attempted_at": now.isoformat(), "provider_cooldown": bool(cooldown),
                                     "retry_at": cooldown or (now + timedelta(days=7)).isoformat()}
                self.http.checkpoint()
        baseline = self._report(self.published, snapshots=self.refresh.original)
        after = self._report(self._document() if changed else document)

        def changed_items(previous):
            fields = ("facts_digest", "missing", "acquisition", "routes", "conflicts")
            prior_rows = previous["items"]
            current_rows = after["items"]
            return sorted(key for key in prior_rows.keys() | current_rows.keys()
                          if any(prior_rows.get(key, {}).get(field) != current_rows.get(key, {}).get(field) for field in fields))

        changes = changed_items(baseline)
        changed_this_run = changes
        if self.refresh.previous_staged:
            changed_this_run = []
            if self.refresh.previous_staged != self.refresh.staged:
                snapshots = {**self.refresh.original, **self.refresh.previous_staged}
                prior = self._report(comparison_document(snapshots, self.catalog), snapshots=snapshots)
                changed_this_run = changed_items(prior)
        return {"build": self.build, "before": baseline["counts"], "after": after["counts"],
                "changed_ids": changes, "changed_this_run": changed_this_run, "conflict_groups": after["conflict_groups"],
                "fidelity_errors": after["fidelity_errors"], "items": after["items"], "rolls": after["rolls"],
                "bulk_sources": after["bulk_sources"]}
