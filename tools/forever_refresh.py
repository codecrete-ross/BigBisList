"""Stage changes to the public evidence behind Forever's open availability audit."""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import timedelta
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

from tools import forever, forever_availability as availability, forever_hotfix as hotfix, forever_leveling as leveling
from tools import forever_sources as sources
from tools import forever_eg_link as eg_link, forever_review_carry as carry
from tools.forever_catalog import CountedCatalog, ICY, ICY_ARMOR, ETERNA, ETERNA_ARMOR
from tools.forever_refresh_http import RefreshHTTP, Unavailable, timestamp, workspace_lock, write_json
from tools.project import FOREVER_CANONICAL_DIR, FOREVER_RAW_DIR, ROOT, dataset_json, load_json


REFRESH_DIR = ROOT / "build" / "forever-refresh"
AH_CATALOGS = tuple(f"https://ahledger.com/api/catalog?class={kind}" for kind in ("armor", "weapon"))
AH_QUESTS = "https://ahledger.com/llms-full.txt"
EVERLOOT_FEEDS = (
    "https://everloot.app/api/corpus/public?kinds=item_fact,quest,vendor,loot&limit=500",
    "https://everloot.app/api/edges?from_kind=item&evidence=observed&limit=500",
)
EVERLOOT_CORPUS_PARTITIONS = tuple(
    f"https://everloot.app/api/corpus/public?kinds={kind}&limit=500" for kind in ("item_fact", "quest", "vendor")
)
SITEMAP = sources.WOWHEAD_ROOT + "sitemap/item?page=1"
DIRECT_KINDS = {"item", "quest", "npc", "spell", "object"}
EQUIPMENT_FACTS = (*availability.CANDIDATE_OBSERVATION_FIELDS, "item_level", "binding")
RECEIPT_FIELDS = {"fetched_at", "collected_at", "source_content_digest", "input_sources", "page_digests",
                  "data_as_of", "parser_version", "tooltip_url", "fetch_method"}


def snapshot_content(snapshot: dict) -> str:
    """Skip changes that only affect the collection receipt."""
    facts = {k: v for k, v in snapshot.items() if k not in RECEIPT_FIELDS}
    if snapshot.get("page_type") == "item":
        if facts.get("provider") == sources.source_provider(facts["url"]):
            facts.pop("provider", None)
        if isinstance(facts.get("description"), str):
            facts["description"] = re.sub(r"\bDurability \d+\s*/\s*\d+\s*", "", facts["description"]).strip()
    return forever.digest(facts)


def positive_id(value: object) -> bool:
    return type(value) is int and value > 0


def pending(row: dict) -> bool:
    return row["status"].startswith(("missing_", "pending_"))


def acquisition_keys(lead: dict) -> set[tuple[str, int]]:
    kind = lead.get("subject_type", lead.get("entity_type", lead.get("type")))
    identifier = lead.get("subject_id", lead.get("entity_id", lead.get("id")))
    keys = {(kind, identifier)} if kind in DIRECT_KINDS and positive_id(identifier) else set()
    keys.update((source_kind, lead[field]) for field, source_kind in (
        ("vendor_id", "npc"), ("npc_id", "npc"), ("quest_id", "quest"), ("spell_id", "spell"),
        ("object_id", "object"), ("item_id", "item"), ("recipe_item_id", "item"),
        ("questId", "quest"), ("vendorNpcId", "npc"), ("sourceNpcId", "npc"), ("sourceObjectId", "object"),
    ) if positive_id(lead.get(field)))
    return keys


def sitemap_page(raw: bytes) -> tuple[set[int], list[str]]:
    if b"<!DOCTYPE" in raw.upper():
        raise ValueError("Expected a Wowhead XML sitemap")
    page = ElementTree.fromstring(raw)
    children = [entry.findtext("{*}loc") for entry in page]
    if page.tag.rsplit("}", 1)[-1] == "sitemapindex":
        if not children or any(not child or not child.startswith(sources.WOWHEAD_ROOT + "sitemap/item?page=")
                               or not child.rsplit("=", 1)[-1].isdigit() for child in children):
            raise ValueError("Unexpected sitemap child URL")
        return set(), sorted(set(children))
    if page.tag.rsplit("}", 1)[-1] != "urlset" or not children:
        raise ValueError("Expected a Wowhead item sitemap")
    keys = [sources.entity_key(child) if child else None for child in children]
    if any(not key or key[0] != "item" for key in keys):
        raise ValueError("Unexpected record in the Wowhead item sitemap")
    return {key[1] for key in keys}, []


def exact_facts(snapshot: dict) -> dict:
    """Index fields by exact item or source ID for the retry queue and report."""
    index = defaultdict(set)

    def add(kind, identifier, value):
        if positive_id(identifier):
            index[(kind, identifier)].add(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))

    def add_edge(edge):
        for end in ("subject", "object"):
            add(edge.get(end + "_type"), edge.get(end + "_id"), edge)

    entity = sources.entity_key(snapshot.get("url", ""))
    if not entity and snapshot.get("page_type") in DIRECT_KINDS:
        entity = (snapshot["page_type"], snapshot.get("item_id", snapshot.get("entity_id")))
    if entity:
        if entity[0] == "item":
            add(*entity, {k: snapshot[k] for k in ("item_kind", "item_stats", "normalized_requirements", "normalized_sources")
                          if k in snapshot})
        else:
            add(*entity, {k: snapshot[k] for k in ("name", "description", "linked_entities") if k in snapshot})
    for edge in snapshot.get("relationships", []):
        add_edge(edge)
    for row in snapshot.get("records", []):
        item_id = row.get("item_id", row.get("itemId"))
        if row.get("kind") == "item_disclosure":
            if row["state"] in {"valid", "removed", "not_on_unrevealed_list"}:
                add("item", item_id, {"disclosure_state": row["state"], "name": row.get("name")})
            continue
        if row.get("kind") == "quest_disclosure":
            if row["state"] == "described":
                add("quest", row["quest_id"], {"disclosure_state": row["state"], "title": row.get("title")})
            continue
        if row.get("kind") == "item_fact":
            add("item", item_id, {k: row[k] for k in ("kind", "fact", "value", "clientBuild") if k in row})
        elif positive_id(item_id):
            add("item", item_id, {k: row[k] for k in EQUIPMENT_FACTS if k in row})
        quest_id = row.get("quest_id", row.get("questId"))
        if positive_id(quest_id):
            fact = {k: row[k] for k in ("quest_id", "questId", "level", "observed_quest_level", "faction",
                                      "rewardItemIds", "reward_leads", "clientBuild") if k in row}
            add("quest", quest_id, fact)
            for reward in row.get("rewardItemIds", []):
                add("item", reward, fact)
        if row.get("kind") in {"vendor", "loot"}:
            origin = {k: row[k] for k in ("kind", "vendorNpcId", "sourceNpcId", "sourceObjectId", "clientBuild", "faction") if k in row}
            for item in row.get("items", []):
                if isinstance(item, dict):
                    add("item", item.get("itemId"), {**origin, "item": item})
    for quest_id, checksum in snapshot.get("quest_record_digests", {}).items():
        add("quest", int(quest_id), {"quest_record_digest": checksum})
    for dependency in snapshot.get("availability_dependencies", []):
        add(dependency["entity_type"], dependency["entity_id"], dependency)
    return index


class AvailabilityRefresh:
    def __init__(self, http: RefreshHTTP, registered: set[str], baseline: dict, candidate_audit: dict, summary: dict, ledger: dict,
                 *, review_issues=()):
        self.http = http
        self.registered = {sources.canonical_url(url) for url in registered}
        self.original = baseline
        self.staged = self._load_staged()
        self.previous_staged = dict(self.staged)
        self.audit = candidate_audit
        self.summary = summary
        self.review_issues = list(review_issues)
        self.build = candidate_audit["client_build"]
        self.open = {row["item_id"]: row for row in candidate_audit["candidate_reviews"] if pending(row)}
        self.known = {row["item_id"] for row in candidate_audit["candidate_reviews"]}
        self.ledger = {sources.canonical_url(row["url"]): row for row in ledger["entries"]}
        self.registered_items = {key[1] for url in self.registered if (key := sources.entity_key(url)) and key[0] == "item"}
        self.client_ids = set()
        self.client_types = defaultdict(set)
        self.client_type_receipts = ()
        self.bulk_results = {}
        self.exact_results = {}

    @property
    def snapshots(self) -> dict:
        return {**self.original, **self.staged}

    def _load_staged(self) -> dict:
        result = {}
        for url, entry in self.http.state["snapshots"].items():
            snapshot = load_json(self.http.directory / entry["file"])
            if snapshot.get("url") != url or sources.content_digest(snapshot) != entry["digest"]:
                raise ValueError(f"Invalid staged snapshot: {url}")
            published = self.original.get(url, {})
            if published and (timestamp(snapshot.get("fetched_at")) < timestamp(published.get("fetched_at"))
                    or (published.get("catalog_coverage", {}).get("complete")
                        and not snapshot.get("catalog_coverage", {}).get("complete"))
                    or (url == AH_QUESTS and published.get("page_type") == "observations")):
                # Keep the published baseline when replaying older receipts or
                # a rolling quest export saved before snapshots were archived.
                continue
            if snapshot_content(snapshot) != snapshot_content(published):
                result[url] = snapshot
        return result

    def stage(self, snapshot: dict, receipts: list[dict], *, entity: bool = False) -> bool:
        from tools.scrape_wowhead import snapshot_name

        url = snapshot["url"]
        previous = self.staged.get(url, self.original.get(url))
        # Error and truncated responses can never replace a complete catalog.
        if previous and previous.get("catalog_coverage", {}).get("complete") and not snapshot.get("catalog_coverage", {}).get("complete"):
            raise ValueError("A partial catalog cannot replace the last complete snapshot")
        if previous and snapshot_content(snapshot) == snapshot_content(previous):
            return False
        if previous and timestamp(snapshot.get("fetched_at")) < timestamp(previous.get("fetched_at")):
            return False
        digest = sources.content_digest(snapshot)
        raw_directory = FOREVER_RAW_DIR if entity else sources.PROVIDER_RAW_DIR / snapshot["provider"]
        target = (raw_directory / snapshot_name(url)).relative_to(ROOT)
        path = Path("snapshots") / digest / target
        write_json(self.http.directory / path, snapshot)
        self.staged[url] = snapshot
        # Keep every staged version addressable by digest, including superseded evidence.
        self.http.state["snapshots"][url] = {"file": path.as_posix(), "target": target.as_posix(),
                                              "digest": digest, "receipts": receipts}
        self.http.checkpoint()
        return True

    def read(self, url: str, *, cycle: str | None = None, immutable: bool = False, cache_dir: Path | None = None) -> tuple[bytes, dict]:
        from tools.scrape_wowhead import html_cache_name

        return self.http.get(url, cycle=cycle, immutable=immutable,
                             project_cache=cache_dir / html_cache_name(url) if cache_dir else None)

    def collect(self, name: str, action, *, source_url: str) -> None:
        try:
            status = action()
            self.bulk_results[name] = {"source_url": source_url, "status": status}
        except (Unavailable, ValueError, ElementTree.ParseError, KeyError, TypeError) as exc:
            self.bulk_results[name] = {"source_url": source_url, "status": "deferred" if isinstance(exc, Unavailable) else "invalid",
                                       "reason": str(exc), "http_status": getattr(exc, "status", None),
                                       "retry_at": getattr(exc, "retry_at", None)}

    def refresh_client(self) -> str:
        root = "https://wago.tools/db2"
        names = ("Item", "ItemSparse", "ItemSearchName")
        responses = {name: self.read(f"{root}/{name}/csv?build={self.build}", immutable=True,
                                     cache_dir=sources.PROVIDER_RAW_DIR / "wago" / "html_cache") for name in names}
        tables = {name: raw.decode("utf-8-sig") for name, (raw, _) in responses.items()}
        receipts = [entry for _, entry in responses.values()]
        snapshot = availability.normalize_client_catalog(tables, self.build, collected_at=max(r["collected_at"] for r in receipts))
        for name, table in tables.items():
            for row in csv.DictReader(io.StringIO(table)):
                identifier = int(row["ID"])
                self.client_ids.add(identifier)
                value = row.get("InventoryType")
                if value and value.isdecimal() and int(value):
                    self.client_types[identifier].add(int(value))
        self.client_type_receipts = tuple(responses[name][1] for name in ("Item", "ItemSparse"))
        previous = self.original.get(snapshot["url"], {})
        if previous.get("input_sources") == snapshot["input_sources"]:
            # The reviewed catalog may contain import corrections for exactly
            # these bytes. Re-parsing the export does not supersede that review.
            return "unchanged"
        return "changed" if self.stage(snapshot, receipts) else "unchanged"

    def refresh_raidbots(self) -> str:
        index, index_receipt = self.read(hotfix.RAIDBOTS_INDEX)
        build_number = int(self.build.rsplit(".", 1)[1])
        options = [row for row in json.loads(index)["data"]
                   if row.get("version") == "forever" and row.get("verified") is True
                   and sources.source_provider(row.get("url")) == "raidbots"]
        newer = sorted({row["build"] for row in options if row["build"] > build_number})
        if newer:
            self.bulk_results["unreviewed_builds"] = {"build_numbers": newer, "status": "review_required"}
        compatible = [row for row in options if row.get("build") == build_number
                      and f"wow%2F{build_number}%2FenUS%2F" in row["url"]]
        if not compatible:
            raise ValueError("No verified Raidbots entry for the reviewed Forever build")
        latest = max(compatible, key=lambda row: timestamp(row["created"]))
        url = latest["url"]
        previous = self.staged.get(url, self.original.get(url, {}))
        if previous.get("catalog_kind") == "client_hotfix" and "quest_record_digests" in previous:
            return "unchanged"
        raw, receipt = self.read(url, immutable=True)
        receipts = [index_receipt, receipt]
        layouts = {}
        for table, file_id in hotfix.TABLE_FILES.items():
            db2, db_receipt = self.read(f"https://wago.tools/api/casc/{file_id}?version={self.build}", immutable=True)
            dbd, def_receipt = self.read(f"{hotfix.DBDEFS}/{table}.dbd", immutable=True)
            receipts.extend((db_receipt, def_receipt))
            layouts[table] = hotfix.table_layout(db2, dbd.decode("utf-8-sig"))
        equipment, quests = hotfix.read_cache(raw, self.build, layouts)
        # Carry only novel exact facts. Re-observing unchanged equipment in a
        # new cache URL should not change every candidate's evidence set.
        known_facts = defaultdict(set)
        for snapshot in self.snapshots.values():
            if snapshot.get("catalog_kind") in {"client_metadata", "client_hotfix"} and snapshot.get("client_build") == self.build:
                for row in snapshot["records"]:
                    known_facts[row["item_id"]].add(forever.digest({k: row[k] for k in EQUIPMENT_FACTS if k in row}))
        rows = [row for row in hotfix.equipment_rows(equipment) if
                forever.digest({k: row[k] for k in EQUIPMENT_FACTS if k in row}) not in known_facts[row["item_id"]]]
        snapshot = {"url": url, "flavor": "forever", "provider": "raidbots", "page_type": "catalog", "catalog_kind": "client_hotfix",
                    "confidence": "client_metadata_only", "fetched_at": receipt["collected_at"], "client_build": self.build,
                    "source_content_digest": receipt["source_content_digest"], "cache_created_at": latest["created"],
                    "records": rows, "quest_record_digests": {str(i): digest for i, digest in sorted(quests.items())},
                    "relationships": [], "attribution": [{"credit": "Blizzard game data, public enUS cache archived by Raidbots",
                                                           "source": hotfix.RAIDBOTS_INDEX}]}
        return "changed" if self.stage(snapshot, receipts) else "unchanged"

    def refresh_ahledger(self, url: str) -> str:
        raw, receipt = self.read(url, cache_dir=sources.PROVIDER_RAW_DIR / "ahledger" / "html_cache")
        if url == AH_QUESTS:
            catalog = [row for key in AH_CATALOGS for row in self.snapshots.get(key, {}).get("records", [])]
            snapshot = sources.normalize_ahledger_text(url, raw.decode("utf-8-sig"), catalog, collected_at=receipt["collected_at"])
            # The text export samples recent quests. A quest falling out of
            # that window supplies no evidence against its prior observation.
            archive_url = f"{url}#observations-{receipt['source_content_digest']}"
            if archive_url in self.snapshots:
                return "unchanged"
            known = {forever.digest(row) for address, publication in self.snapshots.items()
                     if address.split("#", 1)[0] == url and publication.get("page_type") == "observations"
                     for row in publication["records"]}
            records = [row for row in snapshot["records"] if forever.digest(row) not in known]
            if not records:
                return "unchanged"
            quest_ids = {row["quest_id"] for row in records}
            snapshot.update(url=archive_url, records=records, relationships=[
                row for row in snapshot["relationships"] if row["subject_id"] in quest_ids])
        else:
            snapshot = sources.normalize_ahledger(url, json.loads(raw), collected_at=receipt["collected_at"])
            if not snapshot["catalog_coverage"]["complete"]:
                raise ValueError("Incomplete AHledger catalog response")
        snapshot["source_content_digest"] = receipt["source_content_digest"]
        return "changed" if self.stage(snapshot, [receipt]) else "unchanged"

    def refresh_everloot(self, url: str) -> str:
        collections = self.http.state["collections"]
        token = collections.setdefault(url, self.http.started_at) if self.http.online else collections.get(url)
        receipts = []

        def fetch_page(page_url):
            raw, receipt = self.read(page_url, cycle=token, cache_dir=sources.PROVIDER_RAW_DIR / "everloot" / "html_cache")
            receipts.append(receipt)
            payload = json.loads(raw)
            if not isinstance(payload, dict) or payload.get("ok") is False or payload.get("unreachable"):
                raise ValueError("Everloot observations unavailable")
            return payload

        if self.http.online:
            self.http.checkpoint()
        try:
            snapshot = sources.collect_everloot(url, fetch_page, collected_at=self.http.started_at)
        except ValueError:
            # A changed pagination revision needs a new first page next time.
            if self.http.online:
                collections.pop(url, None)
                self.http.checkpoint()
            raise
        snapshot["fetched_at"] = max(r["collected_at"] for r in receipts)
        changed = self.stage(snapshot, receipts)
        if self.http.online:
            collections.pop(url, None)
            self.http.checkpoint()
        return "changed" if changed else "unchanged"

    def refresh_sitemap(self) -> str:
        if not self.client_ids:
            raise Unavailable("The full reviewed-build client export is needed to distinguish new sitemap IDs")
        receipts, identifiers, remaining, seen = [], set(), [SITEMAP], set()
        while remaining:
            url = remaining.pop(0)
            if url in seen:
                raise ValueError("Duplicate Wowhead sitemap page")
            seen.add(url)
            raw, receipt = self.read(url, cache_dir=sources.PROVIDER_RAW_DIR / "wowhead" / "html_cache")
            receipts.append(receipt)
            ids, pages = sitemap_page(raw)
            identifiers.update(ids)
            remaining.extend(pages)
        prior = self.staged.get(SITEMAP, {}).get("records", [])
        existing = self.original.get(SITEMAP, {})
        classifications = existing.get("reviewed_page_facts", {}).get("wowhead_ids_outside_exact_build_tables", [])
        classified = {row["item_id"] for row in classifications if row.get("disposition") == "non_equipment"}
        unknown = sorted(((identifiers - self.client_ids - self.known - self.registered_items) | {row["item_id"] for row in prior}) - classified)
        if not unknown and existing:
            return "unchanged"
        snapshot = {"url": SITEMAP, "flavor": "forever", "provider": "wowhead", "page_type": "reference",
                    "confidence": "discovery_only", "fetched_at": max(r["collected_at"] for r in receipts),
                    "source_content_digest": forever.digest([r["source_content_digest"] for r in receipts]),
                    "records": [{"item_id": i} for i in unknown], "listed_count": len(identifiers),
                    "attribution": [{"credit": "Wowhead Forever item sitemap", "source": SITEMAP}]}
        return "changed" if self.stage(snapshot, receipts) else "unchanged"

    def refresh_listing(self, url: str) -> str:
        raw, receipt = self.read(url, cache_dir=sources.PROVIDER_RAW_DIR / "wowhead" / "html_cache")
        snapshot = availability.normalize_item_listing(url, raw.decode("utf-8-sig"), collected_at=receipt["collected_at"])
        snapshot["attribution"] = [{"credit": "Wowhead Forever item listing", "source": url}]
        coverage = snapshot["catalog_coverage"]
        previous = self.snapshots.get(url, {}).get("catalog_coverage", {})
        changed = self.stage(snapshot, [receipt]) if coverage["complete"] or not previous.get("complete") else False
        if not coverage["complete"]:
            return "truncated" if coverage["truncated"] else "discovery_only"
        return "changed" if changed else "unchanged"

    def refresh_eg_link(self) -> str:
        if not self.open:
            return "unchanged"
        head, head_receipt = self.read(eg_link.HEAD_URL)
        commit = json.loads(head)[0]["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Invalid EG Link commit SHA")
        root = f"{eg_link.ROOT}/{commit}/data"
        contents, index_receipt = self.read(f"{root}/index.json", immutable=True)
        available = json.loads(contents)["products"]["wowf"][self.build]
        ids = eg_link.acquisition_ids(self.open)
        changed = False
        for name in eg_link.DATASETS:
            if name not in available:
                continue
            url = f"{root}/wowf/{self.build}/{name}.json"

            def collect_export():
                nonlocal changed
                raw, receipt = self.read(url, immutable=True)
                snapshot = eg_link.normalize(url, name, json.loads(raw), self.build, ids,
                    collected_at=receipt["collected_at"], digest=receipt["source_content_digest"])
                if not snapshot["records"]:
                    return "no_exact_matches"
                added = self.stage(snapshot, [head_receipt, index_receipt, receipt])
                changed |= added
                return "changed" if added else "unchanged"

            self.collect("eg_link:" + name, collect_export, source_url=url)
        return "changed" if changed else "unchanged"

    def refresh_zephras(self) -> str:
        identifiers = {identifier for identifier, row in self.open.items() if row["status"] == "missing_tooltip"}
        if not identifiers:
            return "unchanged"
        raw, receipt = self.read(sources.ZEPHRAS_UNREVEALED)
        snapshot = sources.normalize_zephras_disclosures(raw.decode("utf-8-sig"), self.build, identifiers,
            collected_at=receipt["collected_at"], digest=receipt["source_content_digest"])
        return "changed" if self.stage(snapshot, [receipt]) else "unchanged"

    def collect_equivalents(self, types: set[int]) -> set[int]:
        collections = self.http.state["collections"]
        batch = collections.setdefault("counted_catalog", self.http.started_at) if self.http.online else None
        client_ids = self.client_ids or {row["item_id"] for snapshot in self.original.values()
                     if snapshot.get("catalog_kind") == "client_metadata" and snapshot.get("client_build") == self.build
                     for row in snapshot["records"]}
        market_ids = {row["item_id"] for url in AH_CATALOGS for row in self.snapshots.get(url, {}).get("records", [])}
        catalog = CountedCatalog(lambda url: self.read(url, cycle=batch), self.build, client_ids, market_ids,
                                 self.client_types, self.client_type_receipts)
        covered = set()
        for number in sorted(types & (set(ICY_ARMOR) | {13, 22}), key=lambda n: (n in {13, 22}, n)):
            def stage_witness(normalize):
                snapshot = normalize(number)
                changed = self.stage(snapshot, snapshot["input_sources"])
                covered.add(number)
                return "changed" if changed else "unchanged"

            self.collect(f"icyveins:{number}", lambda: stage_witness(catalog.icy), source_url=ICY)
            if number not in covered and number in {*ETERNA_ARMOR, 13, 22}:
                self.collect(f"eternadex:{number}", lambda: stage_witness(catalog.eternadex), source_url=ETERNA)
        if self.http.online and types <= covered:
            collections.pop("counted_catalog", None)
            self.http.checkpoint()
        return covered

    def collect_bulk(self) -> None:
        client = f"https://wago.tools/db2/ItemSparse/csv?build={self.build}"
        self.collect("wago", self.refresh_client, source_url=client)
        self.collect("raidbots", self.refresh_raidbots, source_url=hotfix.RAIDBOTS_INDEX)
        for url in (*AH_CATALOGS, AH_QUESTS):
            if url in self.registered:
                self.collect(url, lambda: self.refresh_ahledger(url), source_url=url)
        self.collect("eg_link", self.refresh_eg_link, source_url=eg_link.HEAD_URL)
        self.collect("zephras", self.refresh_zephras, source_url=sources.ZEPHRAS_UNREVEALED)
        corpus, edges = EVERLOOT_FEEDS
        # Use the compact observed edges for loot. The raw loot corpus exceeds
        # the anonymous hourly allowance in a single pagination run.
        if edges in self.registered:
            self.collect(edges, lambda: self.refresh_everloot(edges), source_url=edges)
        for url in EVERLOOT_CORPUS_PARTITIONS:
            if corpus in self.registered or url in self.registered:
                self.collect(url, lambda: self.refresh_everloot(url), source_url=url)
        slots = {row["slot"] for row in self.summary["availability_review_ranges"]}
        types = set().union(*(availability.COVERAGE_TYPES[slot] for slot in slots))
        covered = self.collect_equivalents(types)
        self.collect("wowhead_sitemap", self.refresh_sitemap, source_url=SITEMAP)
        for number in sorted(types - covered - (set(ICY_ARMOR) | {13, 22})):
            family = "weapons" if number in {13, 22} else "armor"
            url = f"{sources.WOWHEAD_ROOT}items/{family}/slot:{number}"
            self.collect(url, lambda: self.refresh_listing(url), source_url=url)
            if self.bulk_results[url]["status"] == "truncated" or self.staged.get(url, {}).get("catalog_coverage", {}).get("truncated"):
                for quality in range(8):
                    partition = f"{url}/quality:{quality}"
                    self.collect(partition, lambda: self.refresh_listing(partition), source_url=partition)

    def evidence_changes(self, before: dict, *, bulk_only: bool = False) -> dict:
        result = defaultdict(list)
        for url, snapshot in sorted(self.staged.items()):
            if bulk_only and (sources.entity_key(url) or urlsplit(url).netloc == "nether.wowhead.com"):
                continue
            previous = before.get(url, {})
            if not previous and snapshot.get("publication_kind"):
                previous = max((row for row in before.values() if row.get("provider") == snapshot["provider"]
                                and row.get("publication_kind") == snapshot["publication_kind"]
                                and row.get("client_build") == self.build
                                and timestamp(row.get("fetched_at")) <= timestamp(snapshot.get("fetched_at"))),
                               key=lambda row: timestamp(row.get("fetched_at")), default={})
            if snapshot_content(snapshot) == snapshot_content(previous):
                continue
            if snapshot.get("catalog_kind") == "client_hotfix" and "quest_record_digests" in snapshot:
                # Quest fingerprints identify leads. Compare to the latest known
                # compatible capture, even though each binary has its own URL.
                prior = [row for row in before.values() if "quest_record_digests" in row and row["url"] != url
                         and row.get("client_build") == self.build and row.get("catalog_kind") == "client_hotfix"
                         and timestamp(row.get("cache_created_at")) < timestamp(snapshot.get("cache_created_at"))]
                if not previous and prior:
                    previous = {"quest_record_digests": max(prior, key=lambda row: timestamp(row["cache_created_at"]))["quest_record_digests"]}
            old_facts, new_facts = exact_facts(previous), exact_facts(snapshot)
            for key in sorted(old_facts.keys() | new_facts.keys()):
                old, new = old_facts.get(key, set()), new_facts.get(key, set())
                if old != new:
                    result[key].append({"source_url": url,
                                        "removed": [json.loads(value) for value in sorted(old - new)],
                                        "added": [json.loads(value) for value in sorted(new - old)]})
        return result

    def discoveries(self) -> set[int]:
        return {row["item_id"] for url, snapshot in self.staged.items() for row in snapshot.get("records", [])
                if (url == SITEMAP or (snapshot.get("page_type") == "catalog" and availability.candidate_slots(row)))
                and positive_id(row.get("item_id"))} - self.known

    def exact_targets(self, changes: dict) -> dict:
        targets = {}
        discoveries = self.discoveries()
        staged_leads = sources.route_leads(self.staged)
        staged_item_links = defaultdict(set)
        for snapshot in self.staged.values():
            if snapshot.get("item_kind") in {"recipe", "quest_starter"}:
                for link in snapshot.get("linked_entities", []):
                    staged_item_links[snapshot["item_id"]].update(acquisition_keys(link))
        for item_id in sorted(self.open.keys() | discoveries):
            row = self.open.get(item_id, {})
            root = ("item", item_id)
            related = {root}
            for lead in (*row.get("route_leads", []), *staged_leads.get(item_id, [])):
                related.update(acquisition_keys(lead))
            for fact in row.get("pending_facts", []):
                related.update(key for url in fact.get("source_urls", []) if (key := sources.entity_key(url)) and key[0] in DIRECT_KINDS)
            for change in changes.get(root, []):
                # Keep single-source Everloot reports as leads. Query the named
                # entity for its own acquisition and eligibility evidence.
                for fact in change["added"]:
                    related.update(acquisition_keys(fact))
            discovered_links = set().union(*(staged_item_links[identifier] for kind, identifier in related if kind == "item"))
            related.update(discovered_links)
            revised = [change for key in sorted(related) for change in changes.get(key, [])]
            for kind, identifier in sorted(related):
                url = f"{sources.WOWHEAD_ROOT}{kind}={identifier}"
                target = targets.setdefault(url, {"items": set(), "changed": []})
                target["items"].add(item_id)
                target["changed"].extend(change for change in revised if change["added"])
                if (kind, identifier) in discovered_links:
                    target["changed"].append({"linked_from_item": item_id, "entity": [kind, identifier]})
        return targets

    def next_attempt(self, url: str, revision: str, target: dict) -> tuple[bool, str | None]:
        attempt = self.http.state["exact"].get(url)
        now = self.http.now()
        if attempt:
            if attempt.get("provider_cooldown") and timestamp(attempt.get("retry_at")) > now:
                return False, attempt["retry_at"]
            if (attempt["revision"] != revision and (target["changed"] or attempt.get("build") not in {None, self.build})
                    or attempt.get("provider_cooldown")):
                return True, None
            if attempt["status"] == "collected":
                return False, None
            date = timestamp(attempt["attempted_at"]) + timedelta(days=7)
            return date <= now, date.isoformat()
        entry = self.ledger.get(url)
        if target["changed"] or not entry:
            return True, None
        last = entry.get("history", [])[-1:]
        prior_build = next((last[0][key] for key in ("audit_client_build", "client_build_checked", "client_build")
                            if last and last[0].get(key)), None)
        if prior_build and prior_build != self.build:
            return True, None
        if entry.get("status") == "pending":
            date = timestamp(entry.get("last_attempt_at")) + timedelta(days=7)
            return date <= now, date.isoformat()
        return False, None

    def refresh_exact(self, url: str, cycle: str) -> bool:
        from tools.scrape_wowhead import item_tooltip_html, normalize_html, parse_item_tooltip_endpoint

        kind, identifier = sources.entity_key(url)
        cache = FOREVER_RAW_DIR / "html_cache"
        if kind == "item":
            tooltip_url = f"https://nether.wowhead.com/forever/tooltip/item/{identifier}"
            try:
                raw, receipt = self.read(tooltip_url, cycle=cycle, cache_dir=cache)
                payload = json.loads(raw)
                if not isinstance(payload, dict) or not payload.get("name") or not payload.get("tooltip"):
                    raise ValueError("Invalid Forever item tooltip")
                snapshot = parse_item_tooltip_endpoint(url, raw.decode("utf-8-sig"))
                snapshot["tooltip_url"] = tooltip_url
            except Unavailable as exc:
                if exc.status not in {None, 404} or exc.retry_at:
                    raise
                if (exc.status == 404 and timestamp(self.http.state["cooldown"].get("www.wowhead.com")) > self.http.now()):
                    raise
                raw, receipt = self.read(url, cycle=cycle, cache_dir=cache)
                html = raw.decode("utf-8-sig")
                tooltip = item_tooltip_html(identifier, html)
                if not tooltip:
                    raise ValueError("Wowhead page has no exact item tooltip")
                snapshot = normalize_html(url, html)
                classification = parse_item_tooltip_endpoint(url, json.dumps({
                    "name": snapshot["name"], "quality": snapshot["quality"], "tooltip": tooltip,
                }))
                for field in ("item_kind", "embedded_items", "linked_entities"):
                    if field in classification:
                        snapshot[field] = classification[field]
        else:
            try:
                raw, receipt = self.read(url, cycle=cycle, cache_dir=cache)
                snapshot = sources.parse_entity_html(url, raw.decode("utf-8-sig"))
            except Unavailable as exc:
                if kind == "object" or exc.status not in {None, 403, 404}:
                    raise
                tooltip_url = f"https://nether.wowhead.com/forever/tooltip/{kind}/{identifier}"
                raw, receipt = self.read(tooltip_url, cycle=cycle, cache_dir=cache)
                snapshot = sources.parse_entity_tooltip(url, raw.decode("utf-8-sig"))
                snapshot["tooltip_url"] = tooltip_url
        if not snapshot.get("name") or snapshot.get("item_id", snapshot.get("entity_id")) != identifier:
            raise ValueError("Public response does not identify the requested Forever entity")
        snapshot.update(flavor="forever", provider="wowhead", fetched_at=receipt["collected_at"],
                        source_content_digest=receipt["source_content_digest"])
        previous = self.snapshots.get(url, {})
        if kind == "item" and previous.get("observed_item_spells") and snapshot.get("item_kind") == "equipment":
            snapshot["observed_item_spells"] = previous["observed_item_spells"]
        if snapshot.get("tooltip_url") and (previous.get("normalized_sources") or previous.get("relationships")):
            if exact_facts(snapshot).get((kind, identifier)) == exact_facts(previous).get((kind, identifier)):
                return False
            # Preserve the full page and its relationships. The public tooltip
            # has its own URL and proves only the fields it exposes.
            snapshot["url"] = snapshot["tooltip_url"]
            return self.stage(snapshot, [receipt])
        return self.stage(snapshot, [receipt], entity=True)

    def collect_exact(self, changes: dict, *, items: bool) -> None:
        targets = self.exact_targets(changes)
        order = sorted(targets, key=lambda url: (not targets[url]["changed"], not url.startswith(sources.WOWHEAD_ROOT + "item="),
                                               -sum(self.open.get(i, {}).get("affected", {}).get("combinations", 0)
                                                    for i in targets[url]["items"]), url))
        for url in order:
            if (sources.entity_key(url)[0] == "item") != items:
                continue
            target = targets[url]
            revision = forever.digest([self.build, sorted({forever.digest(change) for change in target["changed"]})])
            due, retry_at = self.next_attempt(url, revision, target)
            old = self.http.state["exact"].get(url)
            if not due and (self.http.online or url in self.snapshots or old):
                self.exact_results[url] = {"status": "waiting", "retry_at": retry_at}
                continue
            before = self.http.request_count
            generation = revision if not old or old["revision"] != revision else old["attempted_at"]
            status, reason, provider_cooldown = "collected", None, False
            try:
                self.refresh_exact(url, generation)
                retry_at = None
            except (Unavailable, ValueError, KeyError, TypeError) as exc:
                status, reason = "unresolved", str(exc)
                retry_at = getattr(exc, "retry_at", None)
                provider_cooldown = bool(retry_at)
                if self.http.request_count == before:
                    status = "deferred"
                elif not retry_at:
                    retry_at = (self.http.now() + timedelta(days=7)).isoformat()
            self.exact_results[url] = {"status": status, "reason": reason, "retry_at": retry_at}
            # A cached replay and a budget/cooldown deferral do not consume a lookup.
            if self.http.online and (self.http.request_count > before or status == "collected"):
                self.http.state["exact"][url] = {**self.exact_results[url], "revision": revision,
                                                 "attempted_at": self.http.now().isoformat(), "build": self.build,
                                                 "provider_cooldown": provider_cooldown}
                self.http.checkpoint()

    def audit_overlay(self) -> dict:
        def compact(rows):
            fields = ("item_id", "name", "status", "missing_fact", "next_evidence_trigger", "affected", "disclosure_observations")
            return [{key: row[key] for key in fields if key in row} for row in rows if pending(row)]

        if not self.staged:
            return {"summary": self.summary, "unresolved": compact(self.open.values()),
                    "review_issues": {"leveling": self.review_issues, "pre_raid": []},
                    "errors": [], "conflicts": {}, "inventory_ids": sorted(self.known), "audit_reused": True}

        inputs = ("leveling_rules", "leveling_scoring_profiles", "racial_modifiers", "item_variants", "leveling_reviews",
                  "overrides", "scoring_profiles", "scrape_manifest")
        fingerprint = forever.digest({
            "tools": [sha256((ROOT / "tools" / path).read_bytes()).hexdigest() for path in (
                "forever_refresh.py", "forever_availability.py", "forever.py", "forever_leveling.py", "forever_sources.py",
                "forever_review_carry.py", "recommend_leveling.py")],
            "inputs": [sha256((FOREVER_CANONICAL_DIR / f"{name}.json").read_bytes()).hexdigest() for name in inputs],
            "evidence": {url: sources.content_digest(snapshot) for url, snapshot in self.snapshots.items()},
        })
        audit_cache = self.http.directory / "diagnostic.json"
        previous = load_json(audit_cache) if audit_cache.is_file() else {}
        if previous.get("fingerprint") == fingerprint:
            return {**previous["result"], "audit_reused": True}

        snapshots = self.snapshots
        rules = dataset_json("forever", "leveling_rules")
        reviews = dataset_json("forever", "leveling_reviews")
        migrated = carry.scoped_reviews(reviews, self.original, rules)
        effective = carry.carry_additive_catalogs(migrated, self.original, snapshots)
        result = leveling.generate(snapshots, diagnostic=True, review_document=effective)
        coverage = result["coverage"]
        inventory = result["leveling_candidate_audit"]
        affected = self.open.keys() | self.discoveries()
        conflicts = {str(i): {"tooltip_sources": urls} for i, urls in forever.item_conflicts(snapshots).items() if i in affected}
        for row in inventory["candidates"]:
            if row["item_id"] not in affected:
                continue
            levels = defaultdict(set)
            for observation in row["observations"]:
                if (observation.get("kind") in {"client_metadata", "client_hotfix", "item", "server_equip_requirement"}
                        and observation.get("client_build") in {None, self.build} and type(observation.get("required_level")) is int
                        and observation["required_level"] >= 0):
                    levels[observation["required_level"]].add(observation["source_url"])
            if len(levels) > 1:
                conflicts.setdefault(str(row["item_id"]), {})["equip_levels"] = {str(level): sorted(urls) for level, urls in sorted(levels.items())}
        pre_raid = forever.gaps(snapshots)
        review_issues = {"leveling": coverage["review_issues"], "pre_raid": pre_raid["review_issues"]}
        result = {"summary": coverage["summary"], "unresolved": compact(inventory["candidate_reviews"]),
                  "review_issues": review_issues, "errors": coverage["errors"], "conflicts": conflicts,
                  "inventory_ids": [row["item_id"] for row in inventory["candidate_reviews"]]}
        write_json(audit_cache, {"fingerprint": fingerprint, "result": result})
        return {**result, "audit_reused": False}

    def run(self) -> dict:
        self.collect_bulk()
        changed_bulk = self.evidence_changes(self.original, bulk_only=True)
        self.collect_exact(changed_bulk, items=True)
        self.collect_exact(changed_bulk, items=False)
        diagnostic = self.audit_overlay()
        unresolved = [{**row, "next_retry_at": self.exact_results.get(f"{sources.WOWHEAD_ROOT}item={row['item_id']}", {}).get("retry_at")}
                      for row in diagnostic["unresolved"]]
        open_ids = {row["item_id"] for row in unresolved}
        known_now = set(diagnostic["inventory_ids"])
        still_unclassified = self.discoveries() - known_now
        for identifier in sorted(still_unclassified):
            url = f"{sources.WOWHEAD_ROOT}item={identifier}"
            if any(row.get("item_id") == identifier and (row.get("item_kind") not in {None, "equipment"}
                   or (row.get("item_kind") == "equipment" and row.get("item_stats", {}).get("slot")))
                   for row in self.staged.values()):
                continue
            unresolved.append({"item_id": identifier, "status": "pending_discovery_classification",
                               "missing_fact": "Current equipment slot or non-equipment classification",
                               "next_evidence_trigger": f"Exact Forever tooltip or typed catalog record for {url}"})
        changes = self.evidence_changes(self.original)
        new_changes = self.evidence_changes({**self.original, **self.previous_staged}) if self.previous_staged else changes
        relevant = self.open.keys() | self.discoveries() | open_ids
        linked = self.exact_targets({})
        records = [{"entity_type": kind, "entity_id": identifier, "changes": change}
                   for (kind, identifier), change in sorted(changes.items())
                   if (kind == "item" and identifier in relevant) or f"{sources.WOWHEAD_ROOT}{kind}={identifier}" in linked]
        staged_snapshots = [{"url": url, **self.http.state["snapshots"][url]} for url in sorted(self.staged)]
        proposed = [{"url": url, "provider": snapshot["provider"], "data_family": "acquisition" if sources.entity_key(url) else "leveling_evidence",
                     "status": "pending_live_review"} for url, snapshot in sorted(self.staged.items()) if url not in self.registered]
        return {"build": self.build, "mode": "online" if self.http.online else "cached", "http_attempts": self.http.request_count,
                "http_results": self.http.state["attempts"][self.http.attempts_before:], "providers": self.bulk_results,
                "candidate_ids_before": len(self.open), "availability_ranges_before": len(self.summary["availability_review_ranges"]),
                "availability_ranges_after": diagnostic["summary"]["availability_review_ranges"],
                "candidate_ids_after": len(open_ids), "uncovered_combinations": diagnostic["summary"].get("uncovered_combinations", 0),
                "audit_reused": diagnostic["audit_reused"], "new_snapshot_count": sum(
                    url not in self.previous_staged or snapshot_content(snapshot) != snapshot_content(self.previous_staged[url])
                    for url, snapshot in self.staged.items()),
                "new_item_ids": sorted(self.discoveries()), "resolved_item_ids": sorted((self.open.keys() - open_ids) & known_now),
                "unclassified_discoveries": len(unresolved) - len(open_ids),
                "disappeared_item_ids": sorted(self.open.keys() - known_now), "changed_facts": records,
                "changed_this_run": [{"type": row["entity_type"], "id": row["entity_id"]} for row in records
                                     if (row["entity_type"], row["entity_id"]) in new_changes],
                "unresolved": unresolved, "exact_lookups": self.exact_results, "conflicts": diagnostic["conflicts"],
                "review_issues": diagnostic["review_issues"], "audit_errors": diagnostic["errors"],
                "staged_snapshots": staged_snapshots, "proposed_manifest_sources": proposed}


def refresh_availability(*, online: bool, directory: Path = REFRESH_DIR) -> dict:
    from tools.scrape_wowhead import USER_AGENT

    with workspace_lock(directory):
        audit = dataset_json("forever", "leveling_candidate_audit")
        rules_build = dataset_json("forever", "leveling_rules")["review"]["client_build"]
        if audit["client_build"] != rules_build:
            raise ValueError("Refresh needs the candidate audit for the reviewed Forever build")
        leveling_audit = dataset_json("forever", "leveling_audit")
        summary, review_issues = leveling_audit["summary"], leveling_audit["review_issues"]
        del leveling_audit
        ledger = load_json(FOREVER_CANONICAL_DIR / "retry_ledger.json")
        registered = forever.registered_urls()
        snapshots = forever.read_snapshots(FOREVER_RAW_DIR)
        http = RefreshHTTP(directory, online=online, user_agent=USER_AGENT)
        if http.state.get("reviewed_build") != rules_build:
            http.state.update(reviewed_build=rules_build, snapshots={}, collections={})
            http.checkpoint()
        refresh = AvailabilityRefresh(http, registered, snapshots, audit, summary, ledger, review_issues=review_issues)
        report = refresh.run()
        write_json(directory / "report.json", report)
        if online:
            write_json(directory / "online-report.json", report)
        return report


def print_summary(report: dict) -> None:
    examples = report["changed_this_run"][:5]
    print(json.dumps({
        "mode": report["mode"], "http_attempts": report["http_attempts"], "new_snapshots": report["new_snapshot_count"],
        "new_item_ids": len(report["new_item_ids"]), "candidate_ids_before": report["candidate_ids_before"],
        "candidate_ids_after": report["candidate_ids_after"], "availability_ranges": len(report["availability_ranges_after"]),
        "audit_reused": report["audit_reused"], "conflicts": len(report["conflicts"]),
        "changed_examples": examples,
        "report": (REFRESH_DIR / "report.json").relative_to(ROOT).as_posix(),
    }, indent=2))
