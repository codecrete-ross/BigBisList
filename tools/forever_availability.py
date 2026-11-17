"""Finite, evidence-bound inventories for Forever's empty leveling slots.

Catalogs identify candidates; they do not establish acquisition. An empty-slot
approval requires reviewed complete source coverage and an exclusion for every
candidate, including candidates that have never been approved as gear.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import csv
import hashlib
import io
import re
from urllib.parse import unquote, urlsplit

from tools.forever import check_evidence_refs, digest, has_review, valid_source, validate_route_review
from tools.forever_sources import evidence_ref, route_leads, source_provider
from tools.recommend_leveling import rules_allow_equipment, slot_matches


INVENTORY_VERSION = "forever-availability-1"
INVENTORY_SLOTS = {"Head", "Shoulder", "Ring", "Trinket", "Off Hand", "Idol", "Totem", "Libram"}
SLOT_ALIASES = {"HEAD": "Head", "SHOULDER": "Shoulder", "FINGER": "Ring", "TRINKET": "Trinket",
                "HOLDABLE": "Off Hand", "SHIELD": "Off Hand", "WEAPONOFFHAND": "Off Hand",
                "WEAPON": "One Hand", "RELIC": "Relic"}
RELIC_TYPES = {"Idol", "Totem", "Libram"}
REQUIRED_SOURCE_KINDS = {"client_metadata", "ahledger_catalog", "counted_listing"}
LISTING_KINDS = {"wowhead_listing", "counted_listing"}
SCOPED_PROOFS = 2
EMPTY_SUPPORT_DIGEST = digest([])
INVENTORY_TYPES = {1: "Head", 3: "Shoulder", 11: "Ring", 12: "Trinket", 13: "One Hand",
                   14: "Off Hand", 21: "Main Hand", 22: "Off Hand", 23: "Off Hand", 28: "Relic"}
ARMOR_TYPES = {1: "Cloth", 2: "Leather", 3: "Mail", 4: "Plate", 6: "Shield", 7: "Libram", 8: "Idol", 9: "Totem"}
WEAPON_TYPES = {0: "Axe", 1: "Axe", 2: "Bow", 3: "Gun", 4: "Mace", 5: "Mace", 6: "Polearm",
                7: "Sword", 8: "Sword", 9: "Warglaive", 10: "Staff", 13: "Fist Weapon",
                15: "Dagger", 16: "Thrown", 18: "Crossbow", 19: "Wand"}
ALWAYS_ALLOW_DUAL_WIELD = 1 << 19
CLASS_BITS = {"Warrior": 0, "Paladin": 1, "Hunter": 2, "Rogue": 3, "Priest": 4,
              "Shaman": 6, "Mage": 7, "Warlock": 8, "Druid": 10}
COVERAGE_TYPES = {slot: {key} for key, slot in INVENTORY_TYPES.items() if slot in INVENTORY_SLOTS and slot != "Off Hand"}
COVERAGE_TYPES.update({"Off Hand": {13, 14, 22, 23}, "Idol": {28}, "Totem": {28}, "Libram": {28}})
CANDIDATE_OBSERVATION_FIELDS = (
    "name", "slot", "subclass", "armor_type", "weapon_subtype", "required_level", "required_skill",
    "required_skill_rank", "class_mask", "race_mask", "restrictions", "item_kind", "requirements",
    "requires_dual_wield",
)


def normalize_client_catalog(tables: dict[str, str], build: str, *, collected_at: str) -> dict:
    if not re.fullmatch(r"1\.60\.\d+\.\d+", build) or set(tables) != {"Item", "ItemSparse", "ItemSearchName"}:
        raise ValueError("Current Forever client catalog needs all three exact-build exports")
    parsed, inputs = {}, []
    for name, text in tables.items():
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows or any(not str(row.get("ID", "")).isdigit() or None in row for row in rows):
            raise ValueError("Malformed client item export")
        required = {"ID", "InventoryType", "ClassID", "SubclassID"} if name == "Item" else {"ID", "RequiredLevel", "AllowableClass"}
        if not required.issubset(rows[0]):
            raise ValueError("Client export is missing required equipment columns")
        keyed = {int(row["ID"]): row for row in rows}
        if len(keyed) != len(rows):
            raise ValueError("Duplicate client export item ID")
        parsed[name] = keyed
        inputs.append({"source_url": f"https://wago.tools/db2/{name}/csv?build={build}",
                       "sha256": hashlib.sha256(text.encode()).hexdigest(), "records": len(rows)})
    records = []
    for identifier in sorted(set(parsed["Item"]) | set(parsed["ItemSparse"]) | set(parsed["ItemSearchName"])):
        base = parsed["Item"].get(identifier, {})
        sparse = parsed["ItemSparse"].get(identifier, {})
        search = parsed["ItemSearchName"].get(identifier, {})
        def field(key):
            return (sparse.get(key) if sparse.get(key) not in (None, "") else search.get(key)) or None
        inventory_type = int(sparse.get("InventoryType") or base.get("InventoryType") or 0)
        slot = INVENTORY_TYPES.get(inventory_type)
        if not slot:
            continue
        item_class, subclass = int(base.get("ClassID") or -1), int(base.get("SubclassID") or -1)
        row = {"item_id": identifier, "name": field("Display_lang"), "slot": slot,
               "item_level": int(field("ItemLevel")) if field("ItemLevel") is not None else None,
               "required_level": int(field("RequiredLevel")) if field("RequiredLevel") is not None else None,
               "required_skill": int(field("RequiredSkill") or 0),
               "required_skill_rank": int(field("RequiredSkillRank") or 0)}
        if (class_mask := field("AllowableClass")) is not None:
            row["class_mask"] = int(class_mask)
        if sparse.get("AllowableRace_0") is not None and sparse.get("AllowableRace_1") is not None:
            row["race_mask"] = (int(sparse["AllowableRace_0"]) & 0xffffffff) | ((int(sparse["AllowableRace_1"]) & 0xffffffff) << 32)
        elif search.get("AllowableRaces_0") is not None and search.get("AllowableRaces_1") is not None:
            row["race_mask"] = (int(search["AllowableRaces_0"]) & 0xffffffff) | ((int(search["AllowableRaces_1"]) & 0xffffffff) << 32)
        for key in ("RequiredLevel", "AllowableClass", "RequiredSkill", "RequiredSkillRank", "Flags_2"):
            if sparse.get(key) not in (None, "") and search.get(key) not in (None, "") and int(sparse[key]) != int(search[key]):
                raise ValueError(f"Conflicting current client requirement: item {identifier}, {key}")
        if item_class == 4 and subclass in ARMOR_TYPES:
            row["armor_type"] = row["subclass"] = ARMOR_TYPES[subclass]
        # Some profession tools have a weapon class and use the holdable slot.
        if item_class == 2 and subclass in WEAPON_TYPES and inventory_type in (13, 21, 22):
            row["weapon_subtype"] = WEAPON_TYPES[subclass]
        if inventory_type in (14, 23):
            row["requires_dual_wield"] = False
        elif inventory_type in (13, 22) and item_class == 2 and field("Flags_2") is not None:
            row["requires_dual_wield"] = not bool(int(field("Flags_2")) & ALWAYS_ALLOW_DUAL_WIELD)
        records.append(row)
    return {"url": f"https://wago.tools/db2/ItemSparse/csv?build={build}", "provider": "wago", "flavor": "forever",
            "page_type": "catalog", "catalog_kind": "client_metadata", "confidence": "client_metadata_only",
            "client_build": build, "fetched_at": collected_at, "input_sources": sorted(inputs, key=lambda r:r["source_url"]),
            "records": records, "relationships": [],
            "catalog_coverage": {"slots": sorted(INVENTORY_SLOTS), "level_min": 1, "level_max": 59,
                                 "inventory_types": sorted(set().union(*COVERAGE_TYPES.values())),
                                 "total": len(records), "complete": True, "qualities": list(range(8))},
            "attribution": [{"credit": "Game data © Blizzard Entertainment; client table exports from Wago.tools.",
                             "source": "https://wago.tools", "licence": "Blizzard game-file metadata; availability unconfirmed"}]}


def normalize_item_listing(url: str, html: str, *, collected_at: str) -> dict:
    """A whole slot or one quality partition, with its advertised count checked."""
    from tools.scrape_wowhead import extract_all_listview_data, element_text, item_list_count_metadata, make_soup
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    match = re.search(r"/slot:(\d+)(?:/|$)", path)
    if parsed.netloc != "www.wowhead.com" or not re.match(r"/forever/items/(?:armor|weapons)/", path) or not match:
        raise ValueError("Item inventory listing needs an explicit Forever armor slot")
    slot = INVENTORY_TYPES.get(int(match[1]))
    if slot not in INVENTORY_SLOTS | {"Relic", "One Hand"}:
        raise ValueError("Unsupported availability listing slot")
    quality_match = re.search(r"/quality:([0-7])(?:/|$)", path)
    maximum_match = re.search(r"/max-req-level:(\d+)(?:/|$)", path)
    maximum = int(maximum_match[1]) if maximum_match else 59
    filters = path.rstrip("/").split("/")[4:]
    supported = {result[0][1:].rstrip("/") for result in (match, quality_match, maximum_match) if result}
    if (set(filters) != supported or len(filters) != len(supported) or parsed.query or parsed.fragment
            or not 1 <= maximum <= 59):
        raise ValueError("Filtered listing cannot establish whole-slot inventory coverage")
    views = extract_all_listview_data(html)
    if "items" not in views:
        raise ValueError("Missing actual item listing; an error page cannot establish an empty inventory")
    rows = views["items"]
    text = element_text(make_soup(html))
    found = re.search(r"([\d,]+) items? found", text, re.I)
    page_count = re.search(r"[\d,]+\s*[-–]\s*[\d,]+ of ([\d,]+)", text)
    metadata = item_list_count_metadata(html)
    counts = {int(match[1].replace(",", "")) for match in (found, page_count) if match}
    if metadata["total_items"] is not None:
        counts.add(metadata["total_items"])
    if not counts and "No results" in text:
        counts.add(0)
    total = next(iter(counts)) if len(counts) == 1 else None
    truncated = metadata["truncated"] or len(rows) >= 1000 or any(count > len(rows) for count in counts)
    records = []
    for row in rows:
        if type(row.get("id")) is not int or row["id"] <= 0:
            raise ValueError("Listing item ID is missing")
        records.append({"item_id": row["id"], "name": row.get("name"), "slot": slot,
                        "required_level": row.get("reqlevel"), "item_level": row.get("level")})
    # A required-level filter has no documented treatment for undisclosed
    # requirements. Its advertised count only covers the returned partition.
    complete = (maximum_match is None and not truncated and total == len(records)
                and metadata["displayed_items"] in (None, total)
                and len({r["item_id"] for r in records}) == len(records))
    return {"url": url, "provider": "wowhead", "flavor": "forever", "page_type": "catalog",
            "catalog_kind": "wowhead_listing", "fetched_at": collected_at, "records": records,
            "source_content_digest": hashlib.sha256(html.encode()).hexdigest(),
            "catalog_coverage": {"slots": sorted(RELIC_TYPES) if slot == "Relic" else ["Off Hand"] if slot == "One Hand" else [slot],
                                 "inventory_types": [int(match[1])], "level_min": 1, "level_max": maximum,
                                 "qualities": [int(quality_match[1])] if quality_match else list(range(8)),
                                 "total": total, "complete": complete, "truncated": truncated}}


def useful_effect(snapshot: dict) -> bool:
    stats = snapshot.get("item_stats", snapshot.get("variant_facts", {}))
    return (bool(snapshot.get("observed_item_spells"))
            or any(stats.get(key) for key in ("stats", "armor", "block", "dps", "ranged_dps", "weapon_dps",
                                           "equip_effects", "use_effects", "effect_stats", "set_bonuses"))
            or bool(re.search(r"(?:Equip|Use|Chance on hit|Set):|[+−-]\s*\d[\d,.]*\s+[A-Za-z]",
                              snapshot.get("description", ""))))


def item_spell_ids(snapshot: dict) -> set[int]:
    return ({link["id"] for link in snapshot.get("linked_entities", []) if link.get("type") == "spell"}
            | set(snapshot.get("observed_item_spells", {}).get("spell_ids", [])))


def validate_non_gearing_effect(decision: dict, candidate: dict, support: list[dict], snapshots: dict) -> None:
    """Check an explicit effect review against the complete current item tooltip."""
    identifier = candidate["item_id"]
    build = decision["client_build"]
    item = snapshots[decision["source_url"]]
    stats = item.get("item_stats", {})
    if (item.get("page_type") != "item" or item.get("item_id") != identifier
            or item.get("item_kind") != "equipment" or not item.get("description")
            or stats.get("parse_confidence") != "tooltip_endpoint"
            or stats.get("slot") not in INVENTORY_SLOTS):
        raise ValueError("Non-gearing effect review needs the exact equipment tooltip")

    supported = [snapshots[row["source_url"]] for row in support]
    reviews = [fact for source in supported if source.get("client_build") == build
               for fact in source.get("reviewed_item_effects", []) if fact.get("item_id") == identifier]
    observed_spells = item.get("observed_item_spells", {})
    spell_ids = item_spell_ids(item)
    if (len(reviews) != 1 or not spell_ids or not spell_ids.issubset(reviews[0].get("reviewed_spell_ids", []))
            or reviews[0].get("gearing_benefit") is not False or not reviews[0].get("finding")):
        raise ValueError("Non-gearing exclusion needs a current review of every linked item effect")

    effects = {effect.get("raw_text") for effect in stats.get("effect_stats", [])}
    effects.update(stats.get("equip_effects", []))
    effects.update(stats.get("use_effects", []))
    if ((not effects and not observed_spells.get("spell_ids"))
            or not all(isinstance(effect, str) and effect for effect in effects)
            or effects != set(reviews[0].get("tooltip_effects", []))):
        raise ValueError("Non-gearing review does not cover the exact tooltip effects")

    support_by_id = {record["evidence_id"]: record for record in support}
    for observation in candidate["observations"]:
        if observation["kind"] != "item":
            continue
        tooltip = snapshots[observation["source_url"]]
        if tooltip.get("observed_item_spells"):
            check_evidence_refs(tooltip["observed_item_spells"], support_by_id)
        observed_stats = tooltip.get("item_stats", {})
        observed_effects = observed_stats.get("effect_stats", [])
        observed_lines = set(observed_stats.get("equip_effects", [])) | set(observed_stats.get("use_effects", []))
        if (any(observed_stats.get(field) for field in ("sockets", "socket_bonus", "weapon_min_damage", "weapon_max_damage"))
                or any(effect.get("stats") or effect.get("raw_text") not in effects for effect in observed_effects)
                or not observed_lines.issubset(effects)
                or not item_spell_ids(tooltip).issubset(reviews[0]["reviewed_spell_ids"])):
            raise ValueError("Non-gearing exclusion conflicts with item stats or an unreviewed effect")
        description = tooltip.get("description", "")
        for effect in sorted(effects, key=len, reverse=True):
            description = description.replace(effect, "")
        stat_fields = {key: value for key, value in observed_stats.items()
                       if key not in {"effect_stats", "equip_effects", "use_effects"}}
        if useful_effect({"item_stats": stat_fields, "description": description}):
            raise ValueError("Non-gearing exclusion conflicts with item stats or an unreviewed effect")


def candidate_slots(row: dict) -> list[str]:
    slot = SLOT_ALIASES.get(row.get("slot"), row.get("slot"))
    if slot == "Relic":
        subtype = row.get("subclass") or row.get("armor_type")
        return [subtype] if subtype in RELIC_TYPES else sorted(RELIC_TYPES)
    if slot == "One Hand":
        return ["Off Hand"]
    return [slot] if slot in INVENTORY_SLOTS else []


def item_acquisition_digests(snapshots: dict, records: dict, *, scoped: bool = False) -> dict[int, str]:
    """Bind each item's published leads to their source evidence."""
    source_digests = {record["source_url"]: record["content_digest"] for record in records.values()}
    leads = route_leads(snapshots)
    if scoped:
        dependencies = {}
        for url, snapshot in snapshots.items():
            for row in snapshot.get("availability_dependencies", []):
                key = (row["entity_type"], row["entity_id"])
                dependencies.setdefault(key, []).append((url, digest(row)))
        scoped_digests = scoped_source_digests(snapshots, leads)
        return {identifier: digest(sorted((digest(lead),
                    scoped_digests.get((lead["evidence_url"], identifier), source_digests[lead["evidence_url"]]),
                    sorted(dependencies.get((lead.get("subject_type", lead.get("entity_type")),
                                             lead.get("subject_id", lead.get("entity_id"))), [])))
                    for lead in rows)) for identifier, rows in leads.items()}
    return {
        identifier: digest(sorted((digest(lead), source_digests[lead["evidence_url"]]) for lead in leads))
        for identifier, leads in leads.items()
    }


def scoped_source_digests(snapshots: dict, leads: dict | None = None) -> dict:
    """Project supported bulk sources to the exact rows cited for each item."""
    results = {}
    for url, snapshot in snapshots.items():
        context = {k: snapshot.get(k) for k in ("provider", "confidence", "client_build", "catalog_kind", "attribution")}
        if snapshot.get("catalog_kind") == "ahledger_catalog":
            coverage = snapshot.get("catalog_coverage", {})
            context["coverage"] = {k: v for k, v in coverage.items() if k != "total"}
            if coverage.get("complete") is True and coverage.get("truncated") is not True:
                for row in snapshot["records"]:
                    results[(url, row["item_id"])] = digest([context, row])
        elif url.split("#", 1)[0] == "https://ahledger.com/llms-full.txt" and snapshot.get("page_type") == "observations":
            if leads is None:
                leads = route_leads(snapshots)
            quests = {row["quest_id"]: row for row in snapshot["records"]}
            for identifier, routes in leads.items():
                ids = {lead["subject_id"] for lead in routes if lead["evidence_url"] == url and lead.get("subject_type") == "quest"}
                if ids and ids <= quests.keys():
                    results[(url, identifier)] = digest([context, [quests[q] for q in sorted(ids)]])
    return results


def resolve_scoped_decision(decision: dict, records: dict, scoped_digests: dict) -> dict:
    """Validate against the current evidence while retaining the original approval receipts."""
    scoped_refs = decision.get("scoped_evidence_refs", {})
    if not scoped_refs:
        return decision

    def resolve(value):
        if isinstance(value, list):
            return [resolve(entry) for entry in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {"evidence_id", "content_digest"}:
            identifier = value["evidence_id"]
            record = records.get(identifier)
            if identifier in scoped_refs:
                if not record or scoped_digests.get((record["source_url"], decision["item_id"])) != scoped_refs[identifier]:
                    raise ValueError("Stale scoped availability evidence")
                return {**value, "content_digest": record["content_digest"]}
            return value
        return {key: resolve(entry) for key, entry in value.items()}

    return resolve(decision)


def candidate_proof(candidate: dict, *, scoped: bool, client_build: str | None = None) -> str:
    if not scoped:
        return digest(candidate)
    def equipment_facts(row):
        slot = SLOT_ALIASES.get(row.get("slot"), row.get("slot"))
        return slot, tuple(candidate_slots(row)), row.get("name"), row.get("required_level")

    observed = candidate["observations"]
    known = {equipment_facts(row) for row in observed if client_build and row.get("client_build") == client_build
             and row["kind"] in {"client_metadata", "client_hotfix"} and type(row.get("required_level")) is int}
    facts = []
    for row in observed:
        if (row["kind"] == "ahledger_catalog" and set(row) <= {"kind", "source_url", "client_build", "evidence_ref",
                "slot", "subclass", "name", "required_level"} and equipment_facts(row) in known):
            # Corroboration remains in the audit. A decision citing that source
            # directly also verifies its exact row through scoped_evidence_refs.
            continue
        facts.append({k: v for k, v in row.items() if k != "evidence_ref"})
    return digest({**candidate, "observations": facts})


def build_inventory(snapshots: dict, document: dict, rules: dict, records: dict) -> dict:
    """Union all observed IDs; source completeness is separately reviewed."""
    candidates = {}
    main_hand_observations = {}
    useful_variant_ids = set()
    client_build = document.get("client_build")
    scoped = document.get("proof_version") == SCOPED_PROOFS
    identity_listings = []
    for url, snapshot in sorted(snapshots.items()):
        rows = []
        if snapshot.get("page_type") == "catalog":
            rows = snapshot.get("records", [])
        elif snapshot.get("page_type") == "item":
            parsed = snapshot.get("item_stats", {})
            # Keep non-equipment identities if a catalog placed them in a slot.
            rows = [{**parsed, "item_id": snapshot.get("item_id"), "item_kind": snapshot.get("item_kind"),
                     "requirements":snapshot.get("normalized_requirements", [])}]
        elif snapshot.get("confidence") == "variant_tooltip_endpoint" and snapshot.get("variant_facts"):
            rows = [snapshot["variant_facts"]]
        source_ref = evidence_ref(url, snapshots) if rows else None
        for row in rows:
            identifier = row.get("item_id", row.get("id"))
            slots = candidate_slots(row)
            if type(identifier) is not int or identifier <= 0:
                continue
            kind = snapshot.get("catalog_kind", snapshot.get("page_type"))
            if kind == "counted_listing":
                identity_listings.append((identifier, slots, row, url, source_ref, snapshot.get("client_build")))
                continue
            exact_main_hand = (row.get("slot") == "Main Hand" and kind == "client_metadata"
                               and client_build and snapshot.get("client_build") == client_build
                               and source_provider(url) == "wago")
            if not slots and not exact_main_hand:
                continue
            observation = {key: deepcopy(row[key]) for key in CANDIDATE_OBSERVATION_FIELDS if key in row}
            observation.update(source_url=url, evidence_ref=source_ref, kind=kind,
                               client_build=snapshot.get("client_build"))
            if exact_main_hand:
                main_hand_observations.setdefault(identifier, []).append(observation)
                continue
            if snapshot.get("confidence") == "variant_tooltip_endpoint" and useful_effect(snapshot):
                useful_variant_ids.add(identifier)
            candidate = candidates.setdefault(identifier, {"item_id": identifier, "slots": [], "observations": []})
            candidate["slots"] = sorted(set(candidate["slots"]) | set(slots))
            candidate["observations"].append(observation)

    # Counted witnesses verify identities and scope. Add only slot hypotheses
    # that are absent from the underlying inventory, never placeholder levels.
    for identifier, slots, row, url, ref, build in identity_listings:
        candidate = candidates.setdefault(identifier, {"item_id": identifier, "slots": [], "observations": []})
        if set(slots) - set(candidate["slots"]):
            candidate["slots"] = sorted(set(candidate["slots"]) | set(slots))
            candidate["observations"].append({**{k: row[k] for k in ("slot", "subclass") if k in row},
                "source_url": url, "evidence_ref": ref, "kind": "counted_listing", "client_build": build})

    # An exact main-hand record can rule out a candidate seeded by a generic
    # weapon listing. It does not add any off-hand candidates by itself.
    for identifier in candidates.keys() & main_hand_observations.keys():
        candidates[identifier]["observations"].extend(main_hand_observations[identifier])

    # Keep exact tooltip facts for catalog candidates whose tooltip has a
    # different slot, or no equipment slot at all.
    for url, snapshot in sorted(snapshots.items()):
        candidate = candidates.get(snapshot.get("item_id"))
        if (candidate and snapshot.get("page_type") == "item"
                and not any(row["source_url"] == url for row in candidate["observations"])):
            observation = {"source_url": url, "kind": "item", "item_kind": snapshot.get("item_kind"),
                           "evidence_ref": evidence_ref(url, snapshots), "client_build": snapshot.get("client_build")}
            if observation["item_kind"] == "equipment":
                stats = snapshot.get("item_stats", {})
                observation.update({key: deepcopy(stats[key]) for key in CANDIDATE_OBSERVATION_FIELDS if key in stats})
                observation["requirements"] = deepcopy(snapshot.get("normalized_requirements", []))
            candidate["observations"].append(observation)
    for candidate in candidates.values():
        candidate["candidate_digest"] = candidate_proof(candidate, scoped=scoped, client_build=client_build)
    source_reviews, issues = [], []
    if document and (document.get("version") != INVENTORY_VERSION or document.get("proof_version", 1) not in {1, SCOPED_PROOFS}
                     or not re.fullmatch(r"1\.60\.\d+\.\d+", str(document.get("client_build", "")))
                     or (rules.get("review", {}).get("client_build")
                         and document.get("client_build") != rules["review"]["client_build"])):
        issues.append({"reason":"Availability inventory version or client build does not match the reviewed rules"})
    for rule in document.get("profession_rules", []):
        try:
            if (not has_review(rule) or rule.get("client_build") != document.get("client_build")
                    or not rule.get("profession") or not isinstance(rule.get("skill_bonus_by_race"),dict)):
                raise ValueError("Invalid profession availability rule")
            check_evidence_refs(rule,records)
            ranks=rule.get("ranks")
            if (not isinstance(ranks,list) or not ranks or any(type(r.get("min_level")) is not int
                    or not 1<=r["min_level"]<=60 or type(r.get("max_skill")) is not int or r["max_skill"]<1 for r in ranks)
                    or any(type(value) is not int or value<0 for value in rule["skill_bonus_by_race"].values())):
                raise ValueError("Invalid reviewed profession rank or racial skill bonus")
        except (KeyError,TypeError,ValueError) as exc:
            issues.append({"profession":rule.get("profession"),"reason":str(exc)})
    for review in document.get("source_reviews", []):
        try:
            if not has_review(review) or review.get("kind") not in REQUIRED_SOURCE_KINDS | LISTING_KINDS:
                raise ValueError("Invalid availability source review")
            support = check_evidence_refs(review, records)
            if review.get("source_url") not in {record["source_url"] for record in support}:
                raise ValueError("Catalog review must bind its own source evidence")
            snapshot = snapshots[review["source_url"]]
            if snapshot.get("catalog_kind") != review["kind"]:
                raise ValueError("Availability source kind does not match its collected catalog")
            rows = snapshot.get("records")
            if snapshot.get("page_type") != "catalog" or not isinstance(rows, list):
                raise ValueError("Availability inventory needs an actual catalog")
            if (type(review.get("record_count")) is not int or review["record_count"] != len(rows)
                    or any(not isinstance(r,dict) or type(r.get("item_id",r.get("id"))) is not int
                           or r.get("item_id",r.get("id")) <= 0 for r in rows)
                    or len({r.get("item_id", r.get("id")) for r in rows}) != len(rows)):
                raise ValueError("Incomplete or duplicate availability catalog records")
            if review.get("kind") in {"client_metadata", "counted_listing"} and snapshot.get("client_build") != document.get("client_build"):
                raise ValueError("Availability client catalog has the wrong build")
            if review.get("kind") == "counted_listing" and source_provider(review["source_url"]) not in {"icyveins", "eternadex"}:
                raise ValueError("Unsupported counted inventory witness")
            coverage = snapshot.get("catalog_coverage", {})
            if review["kind"] == "wowhead_listing" and "/max-req-level:" in unquote(urlsplit(review["source_url"]).path):
                raise ValueError("Required-level filter leaves unknown item requirements unaudited")
            if (coverage.get("complete") is not True or type(coverage.get("total")) is not int
                    or coverage["total"] != len(rows) or coverage.get("truncated") is True):
                raise ValueError("Catalog pagination or export completeness is unverified")
            if (not isinstance(coverage.get("slots"), list) or not set(coverage["slots"]).issubset(INVENTORY_SLOTS)
                    or type(coverage.get("level_min")) is not int or type(coverage.get("level_max")) is not int
                    or not 1 <= coverage["level_min"] <= coverage["level_max"] <= 59):
                raise ValueError("Invalid availability catalog scope")
            if (not coverage["slots"] or not isinstance(coverage.get("qualities"), list)
                    or not coverage["qualities"] or any(type(q) is not int or q not in range(8) for q in coverage["qualities"])
                    or not isinstance(coverage.get("inventory_types"), list) or not coverage["inventory_types"]
                    or any(type(t) is not int or t not in INVENTORY_TYPES for t in coverage["inventory_types"])):
                raise ValueError("Invalid availability catalog quality or equipment partition")
            source_reviews.append({"kind": review["kind"], "coverage": coverage,
                                   "source_url": review["source_url"], "review_digest": digest(review)})
        except (KeyError, TypeError, ValueError) as exc:
            issues.append({"source_url": review.get("source_url"), "reason": str(exc)})
    candidate_rows = [candidates[key] for key in sorted(candidates)]
    acquisition_digest = digest({key:row["content_digest"] for key,row in sorted(records.items())})
    signature = digest({"version": INVENTORY_VERSION, "build": document.get("client_build"),
                        "candidates": candidate_rows, "sources": source_reviews, "acquisition_evidence":acquisition_digest,
                        "profession_rules":document.get("profession_rules", [])})
    decisions = document.get("decisions", [])
    route_digests = item_acquisition_digests(snapshots, records, scoped=scoped) if any("item_acquisition_digest" in row for row in decisions) else {}
    scoped_digests = scoped_source_digests(snapshots) if scoped and any(r.get("scoped_evidence_refs") for r in decisions) else {}
    decision_issues = []
    effective = []
    for decision in decisions:
        try:
            original_decision = decision
            candidate = candidates.get(decision.get("item_id"))
            if (not candidate or not has_review(decision) or decision.get("client_build") != document.get("client_build")
                    or decision.get("candidate_digest") != candidate["candidate_digest"]):
                raise ValueError("Stale availability candidate decision")
            if decision.get("exclusion") in {"not_useful", "non_gearing_effect"} and candidate["item_id"] in useful_variant_ids:
                raise ValueError("A captured variant has gameplay stats or effects")
            if "item_acquisition_digest" in decision:
                expected = route_digests.get(decision["item_id"], EMPTY_SUPPORT_DIGEST)
                if decision["item_acquisition_digest"] != expected:
                    raise ValueError("Stale acquisition availability decision")
            elif decision.get("exclusion") == "acquisition_minimum":
                if decision.get("acquisition_evidence_digest") != acquisition_digest:
                    raise ValueError("Stale acquisition availability decision")
            if scoped:
                decision = resolve_scoped_decision(decision, records, scoped_digests)
            if decision.get("exclusion") == "acquisition_minimum":
                validate_exclusion_routes(decision, records, snapshots)
            support = check_evidence_refs(decision, records)
            if decision.get("source_url") not in {record["source_url"] for record in support}:
                raise ValueError("Availability decision must bind its own source evidence")
            if decision.get("exclusion") == "non_gearing_effect":
                validate_non_gearing_effect(decision, candidate, support, snapshots)
            effective.append((decision, original_decision))
        except (KeyError, TypeError, ValueError) as exc:
            decision_issues.append({"item_id": decision.get("item_id"), "reason": str(exc)})
    complete_levels = {}
    for slot in sorted(INVENTORY_SLOTS):
        coverage_by_kind = {kind:set() for kind in REQUIRED_SOURCE_KINDS}
        for source in source_reviews:
            coverage = source["coverage"]
            if slot in coverage["slots"]:
                kind = "counted_listing" if source["kind"] in LISTING_KINDS else source["kind"]
                coverage_by_kind[kind].update(
                    (level, quality, item_type) for level in range(coverage["level_min"], coverage["level_max"]+1)
                    for quality in coverage["qualities"] for item_type in coverage["inventory_types"])
        complete_levels[slot] = [level for level in range(1,60) if not issues and all(
            {(level,quality,item_type) for quality in range(8) for item_type in COVERAGE_TYPES[slot]}.issubset(covered)
            for covered in coverage_by_kind.values())]
    return {"version": INVENTORY_VERSION, "client_build": document.get("client_build"),
            "inventory_digest": signature, "candidates": candidate_rows, "source_reviews": source_reviews,
            "acquisition_evidence_digest": acquisition_digest,
            "effective_decisions": effective,
            "useful_variant_ids": sorted(useful_variant_ids),
            "source_issues": issues, "decision_issues": decision_issues, "candidate_count": len(candidate_rows),
            "complete_levels": complete_levels, "profession_rules":document.get("profession_rules", [])}


def complete_for(inventory: dict, slot: str, minimum: int, maximum: int) -> bool:
    return set(range(minimum,maximum+1)).issubset(inventory["complete_levels"].get(slot, []))


def scope_matches(review: dict, profile: dict, persona: dict, slot: str, minimum: int, maximum: int) -> bool:
    scope = review.get("scope", {})
    return (scope.get("slot", slot) == slot
            and scope.get("class", profile["class"]) == profile["class"]
            and scope.get("spec", profile["spec"]) == profile["spec"]
            and scope.get("faction", persona["faction"]) == persona["faction"]
            and scope.get("race_id", persona["id"]) == persona["id"]
            and type(scope.get("level_min", 1)) is int and type(scope.get("level_max", 59)) is int
            and scope.get("level_min", 1) <= minimum <= maximum <= scope.get("level_max", 59))


def validate_exclusion_routes(decision: dict, records: dict, snapshots: dict) -> list[dict]:
    from tools.forever_leveling import valid_eligibility, validate_starter_gates
    routes = decision.get("routes")
    if not isinstance(routes,list) or not routes:
        raise ValueError("Acquisition exclusion needs explicit reviewed dependency routes")
    for route in routes:
        if not valid_source(route):
            raise ValueError("Acquisition exclusion has an invalid route identity")
        validate_route_review(route,records)
        if not valid_eligibility(route):
            raise ValueError("Acquisition exclusion needs complete route eligibility")
        validate_starter_gates(route,snapshots)
    return routes


def automatic_exclusion(candidate: dict, profile: dict, persona: dict, slot: str, minimum: int, maximum: int, rules: dict,
                        *, equipment_cache: dict | None = None) -> str | None:
    if slot not in candidate["slots"]:
        return "other_slot"
    reviewed_build = rules.get("review", {}).get("client_build")
    # Keep historical identities in the inventory. A superseded client record
    # cannot establish the item's current slot or equipment restrictions.
    observed = [row for row in candidate["observations"]
                if row.get("kind") not in {"client_metadata", "client_hotfix"} or not reviewed_build
                or row.get("client_build") in (None, reviewed_build)]
    equipment_evidence = {"item", "client_metadata", "client_hotfix"}
    # A direct equip requirement can exclude a candidate only if the sources agree.
    levels = {row["required_level"] for row in observed
              if (row.get("kind") in equipment_evidence
                  or (row.get("kind") == "server_equip_requirement" and reviewed_build
                      and row.get("client_build") == reviewed_build
                      and source_provider(row.get("source_url")) == "foreverchanges"))
              and type(row.get("required_level")) is int and row["required_level"] >= 0}
    if len(levels) == 1 and next(iter(levels)) > maximum:
        return "equip_minimum"
    actual_slots = set()
    for row in observed:
        if row.get("kind") not in equipment_evidence:
            continue
        actual_slot = SLOT_ALIASES.get(row.get("slot"), row.get("slot"))
        if actual_slot == "Relic":
            actual_slot = row.get("armor_type") if row.get("armor_type") in RELIC_TYPES else None
        if actual_slot:
            actual_slots.add(actual_slot)
    if actual_slots and all(not slot_matches(actual, slot) for actual in actual_slots):
        return "other_slot"
    # A weapon can require dual wield before its specific proficiency is known.
    requires_dual_wield = True
    if slot == "Off Hand":
        policy = rules.get("spec_policies", {}).get(profile["class"] + "/" + profile["spec"], {})
        dual_wield_level = policy.get("dual_wield_level")
        dual_wield_requirements = {row["requires_dual_wield"] for row in observed
                                  if reviewed_build and row.get("kind") in {"client_metadata", "client_hotfix"}
                                  and row.get("client_build") == reviewed_build and "requires_dual_wield" in row}
        requires_dual_wield = False not in dual_wield_requirements
        confirmed_weapon = actual_slots == {"One Hand"} or (actual_slots == {"Off Hand"} and dual_wield_requirements == {True})
        if confirmed_weapon and requires_dual_wield and (dual_wield_level is None or dual_wield_level > maximum):
            return "equipment_rule"
    class_checks, race_checks = [], []
    for row in observed:
        if row.get("kind") not in equipment_evidence:
            continue
        restrictions = row.get("restrictions", {})
        class_mask = row.get("class_mask")
        # Older client catalogs assigned -1 to base Item rows without sparse
        # requirements. Those rows have no equip level requirement or race mask.
        legacy_unknown_class = (row.get("kind") == "client_metadata" and class_mask == -1
                                and "required_level" in row and row["required_level"] is None and "race_mask" not in row)
        if type(class_mask) is int and class_mask != 0 and not legacy_unknown_class and profile["class"] in CLASS_BITS:
            class_checks.append(bool(class_mask & (1 << CLASS_BITS[profile["class"]])))
        race_mask = row.get("race_mask")
        race_bit = {95: 32, 96: 33}.get(persona["id"], persona["id"] - 1)
        if type(race_mask) is int and race_mask > 0:
            race_checks.append(bool(race_mask & (1 << race_bit)))
        if restrictions.get("classes"):
            class_checks.append(profile["class"] in restrictions["classes"])
        if restrictions.get("races"):
            race_checks.append(persona["name"] in restrictions["races"])
    if class_checks and not any(class_checks):
        return "class_restriction"
    if race_checks and not any(race_checks):
        return "race_restriction"
    # Do not interpret an unknown subtype as evidence of incompatibility.
    equipment_observations = [row for row in observed if row.get("kind") in equipment_evidence
                              and (row.get("armor_type") or row.get("weapon_subtype"))]
    if len({(row.get("armor_type"), row.get("weapon_subtype")) for row in equipment_observations}) > 1:
        return None
    for row in equipment_observations:
        actual_slot = SLOT_ALIASES.get(row.get("slot"), row.get("slot"))
        if actual_slot == "Relic":
            actual_slot = row.get("armor_type") if row.get("armor_type") in RELIC_TYPES else None
        if not actual_slot or not slot_matches(actual_slot, slot):
            continue
        if not (row.get("armor_type") or row.get("weapon_subtype")):
            continue
        item = {**row, "slot": actual_slot, "requires_dual_wield": requires_dual_wield}
        def allowed(level):
            key = (profile["class"], profile["spec"], actual_slot, row.get("armor_type"),
                   row.get("weapon_subtype"), requires_dual_wield, level, slot)
            if equipment_cache is None:
                return rules_allow_equipment(item, profile["class"], profile["spec"], level, slot, rules)
            if key not in equipment_cache:
                equipment_cache[key] = rules_allow_equipment(item, profile["class"], profile["spec"], level, slot, rules)
            return equipment_cache[key]
        if all(not allowed(level) for level in range(minimum, maximum + 1)):
            return "equipment_rule"
    return None


def profession_exclusion(candidate: dict, persona: dict, maximum: int, profession_rules: list[dict]) -> str | None:
    observations=[row for row in candidate["observations"] if row.get("kind")=="item"]
    requirements={tuple(sorted((r["profession"],r["skill"]) for r in row.get("requirements", [])
                              if r.get("type")=="profession" and r.get("scope")=="equip_or_use"
                              and r.get("profession") and type(r.get("skill")) is int)) for row in observations}
    if len(requirements)!=1:
        return None
    for profession,skill in next(iter(requirements), ()):
        for rule in profession_rules:
            bonus=rule["skill_bonus_by_race"].get(str(persona["id"]))
            if rule["profession"]!=profession or type(bonus) is not int:
                continue
            caps=[rank["max_skill"]+bonus for rank in rule["ranks"] if rank["min_level"]<=maximum]
            if caps and skill>max(caps):
                return "profession_minimum"
    return None


def review_scope(inventory: dict, document: dict, profile: dict, persona: dict, slot: str, minimum: int,
                 maximum: int, rules: dict, records: dict, snapshots: dict, *, excluded_items: dict | None = None,
                 equipment_cache: dict | None = None, rules_digest: str | None = None,
                 support_digest_cache: dict | None = None) -> dict:
    decisions = {}
    invalid_items = {issue["item_id"] for issue in inventory.get("decision_issues", [])}
    scoped = document.get("proof_version") == SCOPED_PROOFS
    pairs = inventory.get("effective_decisions") if scoped else None
    if pairs is None:
        pairs = [(row, row) for row in document.get("decisions", [])]
    for row, original in pairs:
        if row.get("item_id") not in invalid_items and scope_matches(row, profile, persona, slot, minimum, maximum):
            decisions.setdefault(row.get("item_id"), []).append((row, original))
    unresolved, outcomes, issues = [], [], []
    for candidate in inventory["candidates"]:
        if slot not in candidate["slots"]:
            continue
        identifier = candidate["item_id"]
        exclusion = automatic_exclusion(candidate, profile, persona, slot, minimum, maximum, rules, equipment_cache=equipment_cache)
        if not exclusion and not inventory["source_issues"]:
            exclusion=profession_exclusion(candidate,persona,maximum,inventory["profession_rules"])
        support = []
        if not exclusion and identifier in (excluded_items or {}) and identifier not in inventory["useful_variant_ids"]:
            declared = excluded_items[identifier]
            actual = snapshots.get(declared.get("snapshot_url"), {})
            if not useful_effect(actual):
                exclusion, support = "not_useful", [declared]
        if not exclusion:
            for decision, original in decisions.get(identifier, []):
                try:
                    if (not has_review(decision) or decision.get("candidate_digest") != candidate["candidate_digest"]
                            or decision.get("client_build") != document.get("client_build")):
                        raise ValueError("Stale availability candidate decision")
                    support_records = check_evidence_refs(decision, records)
                    if decision.get("source_url") not in {record["source_url"] for record in support_records}:
                        raise ValueError("Availability decision must bind its own source evidence")
                    reason = decision.get("exclusion")
                    if reason == "acquisition_minimum":
                        if (decision.get("all_routes_reviewed") is not True
                                or type(decision.get("minimum_level")) is not int
                                or decision["minimum_level"] <= maximum):
                            raise ValueError("Acquisition exclusion needs all routes and a higher minimum")
                        from tools.forever_leveling import route_allows
                        if any(route_allows(route,persona["faction"],persona["name"],profile["class"],level)
                               for route in decision["routes"] for level in range(minimum,maximum+1)):
                            raise ValueError("A reviewed acquisition route is available within this scope")
                    elif reason == "not_useful":
                        item = snapshots.get(decision["source_url"], {})
                        stats = item.get("item_stats", {})
                        if (item.get("page_type") != "item" or item.get("item_id") != identifier
                                or not item.get("description") or useful_effect(item)
                                or not stats.get("slot") or stats["slot"] in {"One Hand","Main Hand","Two Hand","Ranged"}
                                or stats.get("parse_confidence") != "tooltip_endpoint"):
                            raise ValueError("Cosmetic exclusion needs the complete effect-free item tooltip")
                    elif reason == "non_gearing_effect":
                        if identifier in inventory["useful_variant_ids"]:
                            raise ValueError("A captured variant has gameplay stats or effects")
                        validate_non_gearing_effect(decision, candidate, support_records, snapshots)
                    elif reason == "not_equipment":
                        item = snapshots.get(decision["source_url"], {})
                        if (item.get("item_id") != identifier or item.get("item_kind") not in {"recipe", "quest_starter", "non_equipment"}
                                or not item.get("description")):
                            raise ValueError("Non-equipment exclusion needs the actual recipe or quest-starter tooltip")
                    elif reason == "unavailable":
                        sources = (snapshots[record["source_url"]] for record in support_records)
                        if not any(identifier in (source.get("unavailable_item_ids") or [])
                                   and scope_matches({"scope": source.get("unavailable_scope", {})}, profile,
                                                     persona, slot, minimum, maximum)
                                   for source in sources):
                            raise ValueError("Unavailable exclusion needs explicit evidence for this scope")
                    else:
                        raise ValueError("Unknown availability exclusion")
                    exclusion, support = reason, [original]
                    break
                except (KeyError, TypeError, ValueError) as exc:
                    issues.append({"item_id": identifier, "reason": str(exc)})
        if not exclusion:
            unresolved.append(identifier)
        support_digest=EMPTY_SUPPORT_DIGEST
        if support:
            identity=id(support[0])
            if support_digest_cache is None:
                support_digest=digest(support)
            else:
                if identity not in support_digest_cache:
                    support_digest_cache[identity]=digest(support)
                support_digest=support_digest_cache[identity]
        outcomes.append({"item_id": identifier, "exclusion": exclusion,
                         "candidate_digest": candidate["candidate_digest"], "support_digest": support_digest})
    scope = {**profile, "race_id": persona["id"], "faction": persona["faction"], "slot": slot,
             "level_min": minimum, "level_max": maximum}
    complete = complete_for(inventory, slot, minimum, maximum)
    coverage_proof = ({"build": inventory["client_build"], "complete": complete, "proof_version": SCOPED_PROOFS}
                      if scoped else inventory["inventory_digest"])
    signature = digest({"inventory": coverage_proof, "rules": rules_digest or digest(rules),
                        "scope": scope, "outcomes": outcomes})
    return {"availability_digest": signature, "complete": complete,
            "unresolved_item_ids": unresolved, "review_issues": issues,
            "exclusion_counts": dict(Counter(row["exclusion"] or "unresolved" for row in outcomes))}


def candidate_backlog(inventory: dict, missing_rows: list[dict], snapshots: dict, approved: dict,
                      excluded: dict, leads: dict, pending_facts: list[dict] | None = None) -> list[dict]:
    """One actionable record per identity; exact affected scopes remain in the gap rows."""
    affected = {}
    for row in missing_rows:
        for identifier in row.get("availability", {}).get("unresolved_item_ids", []):
            entry = affected.setdefault(identifier, {"levels": set(), "profiles": set(), "race_ids": set(),
                                                      "factions": set(), "slots": set(), "combinations": 0})
            entry["levels"].update(range(row["level_min"], row["level_max"] + 1))
            entry["profiles"].add(row["class"] + "/" + row["spec"])
            for key in ("race_ids", "factions", "slots"):
                entry[key].add(row[{"race_ids": "race_id", "factions": "faction", "slots": "slot"}[key]])
            entry["combinations"] += row["level_max"] - row["level_min"] + 1
    actual_items, disclosures = {}, {}
    for url, snapshot in sorted(snapshots.items()):
        if snapshot.get("page_type") == "item":
            actual_items.setdefault(snapshot.get("item_id"), []).append(url)
        if snapshot.get("publication_kind") not in {"item_hotfixes.enUS", "unrevealed_registry"} or snapshot.get("client_build") != inventory["client_build"]:
            continue
        ref = evidence_ref(url, snapshots)
        for row in snapshot["records"]:
            by_provider = disclosures.setdefault(row["item_id"], {})
            provider = snapshot["provider"]
            collected_at = snapshot["fetched_at"]
            if collected_at >= by_provider.get(provider, {}).get("collected_at", ""):
                by_provider[provider] = {"state": row["state"], "provider": provider, "source_url": url,
                                         "collected_at": collected_at, "client_build": snapshot["client_build"],
                                         "evidence_ref": ref}
    result = []
    for candidate in inventory["candidates"]:
        identifier = candidate["item_id"]
        urls = actual_items.get(identifier, [])
        entry = {"item_id": identifier, "candidate_digest": candidate["candidate_digest"],
                 "slots": candidate["slots"], "tooltip_urls": urls,
                 "name": next((row["name"] for row in candidate["observations"] if row.get("name")), None)}
        if identifier not in affected:
            entry["status"] = ("reviewed_non_gearing_exclusion" if excluded.get(identifier, {}).get("exclusion") == "non_gearing_effect"
                               else "reviewed_cosmetic_exclusion" if identifier in excluded else "verified_route"
                               if identifier in approved else "excluded_from_current_missing_scopes")
        else:
            scope = affected[identifier]
            entry["affected"] = {key: sorted(value) if isinstance(value, set) else value for key, value in scope.items()}
            entry["route_leads"] = leads.get(identifier, [])
            if identifier in disclosures:
                entry["disclosure_observations"] = list(disclosures[identifier].values())
            if not urls:
                entry.update(status="missing_tooltip",
                             missing_fact="Whether this item can be equipped and obtained in the affected early levels.",
                             next_evidence_trigger=f"Current Forever evidence for item {identifier}, such as an equip requirement, "
                             "equipment restriction, complete acquisition gate or full tooltip.")
                if entry.get("disclosure_observations") and all(row["state"] in {"invalid", "unrevealed"}
                                                               for row in entry["disclosure_observations"]):
                    entry["next_evidence_trigger"] = (f"A disclosure change for item {identifier}, a new verified client/cache record, "
                                                       "or an independently verified requirement or acquisition gate.")
            elif any(snapshots[url].get("item_kind") in {"recipe", "quest_starter", "non_equipment"} for url in urls):
                entry.update(status="pending_classification_review", missing_fact="Resolve the catalog's equipment identity against the actual item tooltip.",
                             next_evidence_trigger="An evidence-bound classification decision, retaining any acquisition relationship.")
            else:
                entry.update(status="pending_availability_review", missing_fact="Complete obtainable route or a supported exclusion for the affected early levels.",
                             next_evidence_trigger="Current quest/prerequisite, vendor stock, recipe-access or drop evidence for this exact item.")
            targeted = [row for row in pending_facts or [] if row.get("item_id") == identifier]
            if targeted:
                entry["pending_facts"] = targeted
                entry["missing_fact"] = " ".join(dict.fromkeys(row["missing_fact"] for row in targeted))
                entry["next_evidence_trigger"] = " ".join(dict.fromkeys(row["next_evidence_trigger"] for row in targeted))
        result.append(entry)
    return result
