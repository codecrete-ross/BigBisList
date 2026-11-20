"""Audit the fields available for every bundled Forever equipment identity."""

from collections import Counter, defaultdict
from datetime import timedelta

from tools.forever import digest, read_snapshots
from tools.forever_comparison import (ARMOR_SLOTS, DPS_STATS, WEAPON_SLOTS, WEAPON_STATS, comparison_document, comparison_facts, compile_comparison_data,
                                     merge_comparison_facts)
from tools.forever_item_effects import unresolved_lines
from tools.forever_refresh_http import timestamp
from tools.forever_sources import WOWHEAD_ROOT, route_leads
from tools.generate_lua import FOREVER_OUTPUT_PATH, forever_items
from tools.project import FOREVER_CANONICAL_DIR, FOREVER_RAW_DIR, dataset_json, load_json, lua_value


def reviewed_equipment() -> tuple[list[dict], list[dict]]:
    return forever_items(dataset_json("forever", "items")["items"], dataset_json("forever", "item_stats")["item_stats"])


def unpack(packed: dict) -> dict:
    return {key: dict(zip(packed["item_fields"], row)) for key, row in packed["items"].items()}


def published_rank_matches(packed: dict, path=FOREVER_OUTPUT_PATH) -> bool:
    prefix = '    ["stat_rank"] = '
    if not path.is_file():
        return False
    expected = iter((prefix + lua_value(packed, 4) + ",\n").splitlines(keepends=True))
    with path.open(encoding="utf-8") as payload:
        for line in payload:
            if line.startswith(prefix):
                return line == next(expected) and all(payload.readline() == row for row in expected)
    return False


def fidelity_errors(document: dict, reviewed_stats: list[dict], packed: dict) -> list[dict]:
    items = unpack(packed)
    reviewed = {row["id"]: row for row in reviewed_stats}
    errors = []
    for evidence in document["items"]:
        identifier = evidence["id"]
        approval = comparison_facts(reviewed.get(identifier, {}), allow_empty=True)
        expected = merge_comparison_facts(approval, evidence) if approval else evidence
        actual = items.get(str(identifier))
        if not actual:
            errors.append({"id": identifier, "field": "identity"})
            continue
        generated_stats = actual.get("stats") or {}
        for key, value in expected["stats"].items():
            if generated_stats.get(key) != value:
                errors.append({"id": identifier, "field": key, "expected": value, "generated": generated_stats.get(key)})
        for key in ("name", "slot", "level", "armor_type", "weapon_subtype", "classes", "races", "max_equipped", "unique_group"):
            if key in expected and expected[key] != actual.get(key):
                errors.append({"id": identifier, "field": key, "expected": expected[key], "generated": actual.get(key)})
        absent = set(unresolved_lines(expected)) - set(actual.get("effects") or ())
        if absent:
            errors.append({"id": identifier, "field": "effects", "missing": sorted(absent)})
    return errors


def equipment_report(document: dict, catalog: dict, snapshots: dict, reviewed: tuple, *, ledger: dict | None = None,
                     lookups: dict | None = None, expected: dict | None = None, check_payload: bool = False) -> dict:
    reviewed_items, reviewed_stats = reviewed
    packed = compile_comparison_data(reviewed_stats, data=document, catalog=catalog)
    items = unpack(packed)
    evidence = {row["id"]: row for row in document["items"]}
    stats_reviewed = {row["id"] for row in reviewed_stats}
    acquisition_reviewed = {row["id"] for row in reviewed_items if row.get("sources")}
    leads = route_leads(snapshots, include_guide=True)
    source_fields = {"client_equipment_export": ("weapon", "attributes", "effects", "equip_level"),
                     "client_armor_tables": ("armor",), "equipment_scan": ("weapon",)}
    bulk_sources = defaultdict(list)
    for url, source in sorted(snapshots.items()):
        fields = (("acquisition",) if source.get("page_type") == "equipment_routes"
                  else source_fields.get(source.get("confidence"), ()))
        if source.get("client_build") == catalog["client_build"] or source.get("confidence") == "equipment_scan":
            for field in fields:
                bulk_sources[field].append(url)
    conflicts = defaultdict(list)
    groups = defaultdict(list)
    for conflict in document.get("conflicts", []):
        conflicts[conflict["id"]].append(conflict)
        providers = tuple(sorted({snapshots[url].get("provider") or "wowhead" for url in conflict["sources"]}))
        groups[(conflict["field"], providers, conflict["needs_tooltip"])].append(conflict["id"])

    ledger = {entry["url"]: entry for entry in (ledger or {}).get("entries", [])}
    lookups = lookups or {}
    rows, rolls, counts = {}, {}, Counter()
    for key, item in items.items():
        identifier = item["id"]
        stats = item.get("stats") or {}
        fact = evidence.get(identifier, {})
        known_stats = identifier in stats_reviewed or fact.get("attributes_known")
        known_effects = identifier in stats_reviewed or fact.get("effects_known")
        weapon = item.get("weapon_subtype") is not None and item["slot"] in WEAPON_SLOTS
        armor = (item.get("armor_type") == "Shield" or item.get("slot") in ARMOR_SLOTS | {"Back"}) and not weapon
        missing = []
        if weapon and (not DPS_STATS.intersection(stats) or not {"weapon_min_damage", "weapon_max_damage", "weapon_speed"} <= stats.keys()):
            missing.append("weapon")
        if armor and "armor" not in stats and not item.get("roll_armor"):
            missing.append("armor")
        if not known_stats:
            missing.append("attributes")
        if not known_effects:
            missing.append("effects")
        if item.get("level") is None:
            missing.append("equip_level")
        observed = sorted({(lead.get("relation", lead.get("type", "lead")),
                            lead.get("subject_type", lead.get("entity_type", "")),
                            lead.get("subject_id", lead.get("entity_id")) or 0, lead["evidence_url"],
                            lead.get("entity_name") or "")
                           for lead in leads.get(identifier, [])})
        acquisition = "verified" if identifier in acquisition_reviewed else "observed" if observed else "missing"
        counts.update(missing)
        counts[f"acquisition_{acquisition}"] += 1
        counts["base_ids" if str(identifier) == key else "variants"] += 1
        if item.get("stats_unavailable"):
            counts["stats_unavailable"] += 1
        if weapon and not DPS_STATS.intersection(stats):
            counts["weapons_without_dps"] += 1
        if item.get("roll_group"):
            available, missing_rolls = [], {}
            for bonus in packed["roll_groups"][item["roll_group"] - 1]:
                if f"{identifier}:0:0:0:1:{bonus}" in items:
                    continue
                template = packed["roll_templates"][str(bonus)]
                physical = DPS_STATS.intersection(stats) or (item.get("armor_type") == "Shield" and "block_value" in stats)
                if len(template) < 2 or template[1] is None:
                    missing_rolls[str(bonus)] = "unparsed bonus"
                elif item.get("roll_budget") is None or not (item.get("roll_complete") or physical):
                    missing_rolls[str(bonus)] = "missing base stats or scaling"
                else:
                    available.append(bonus)
            counts["variants"] += len(available) + len(missing_rolls)
            counts["variant_stats_missing"] += len(missing_rolls)
            rolls[key] = {"available": available, "missing": missing_rolls,
                          **({"retry_on": "new build-pinned base or bonus data"} if missing_rolls else {})}
        exact = WOWHEAD_ROOT + f"item={identifier}"
        tooltip = exact.replace("www.wowhead.com/forever/item=", "nether.wowhead.com/forever/tooltip/item/")
        attempt = lookups.get(tooltip, {})
        prior = ledger.get(exact, {})
        retry = attempt.get("retry_at")
        if not retry and prior.get("status") == "pending" and prior.get("last_attempt_at"):
            retry = (timestamp(prior["last_attempt_at"]) + timedelta(days=7)).isoformat()
        pending = any(conflict["needs_tooltip"] for conflict in conflicts[identifier])
        attributes = "available" if stats.keys() - WEAPON_STATS - {"armor"} else "empty" if known_stats else "missing"
        effects = "available" if known_effects and item.get("effects") else "empty" if known_effects else "missing"
        rows[key] = {"id": identifier, "name": item["name"], "missing": missing, "acquisition": acquisition,
                     "attributes": attributes, "effects": effects, "facts_digest": digest(item),
                     **({"routes": observed} if observed else {}),
                     **({"acquisition_retry_on": "new exact route or eligibility evidence"} if acquisition != "verified" else {}),
                     **({"effect_leads": fact["effect_leads"]} if not known_effects and fact.get("effect_leads") else {}),
                     **({"conflicts": conflicts[identifier]} if conflicts[identifier] else {}),
                     **({"sources": sorted({fact.get("evidence", {}).get("url"), *fact.get("supporting_sources", [])} - {None})}
                        if fact else {}),
                     **({"lookup": {"status": attempt.get("status", prior.get("status", "untried")),
                                    "last_attempt": attempt.get("attempted_at", prior.get("last_attempt_at")),
                                    "source": exact if prior and not attempt else tooltip, "reason": attempt.get("reason") or prior.get("last_error"),
                                    "next_retry_at": retry, "retry_on": "due date or relevant evidence change"}}
                        if missing or pending else {})}
    grouped = [{"field": field, "providers": providers, "needs_tooltip": needs_tooltip, "ids": sorted(set(ids))}
               for (field, providers, needs_tooltip), ids in sorted(groups.items())]
    errors = fidelity_errors(document if expected is None else expected, reviewed_stats, packed)
    if check_payload and not published_rank_matches(packed):
        errors.append({"field": "stat_rank", "reason": "DataForever.lua differs from the imported equipment facts"})
    return {"ok": not errors, "counts": dict(sorted(counts.items())), "items": rows, "bulk_sources": dict(bulk_sources),
            "rolls": rolls, "conflict_groups": grouped, "fidelity_errors": errors}


def audit(*, summary: bool) -> dict:
    snapshots = read_snapshots(FOREVER_RAW_DIR)
    catalog = dataset_json("forever", "guide_equipment")
    report = equipment_report(dataset_json("forever", "comparison_item_stats"), catalog, snapshots,
                              reviewed_equipment(), ledger=load_json(FOREVER_CANONICAL_DIR / "retry_ledger.json"),
                              expected=comparison_document(snapshots, catalog), check_payload=True)
    if summary:
        report.pop("items")
        report.pop("rolls")
        report.pop("bulk_sources")
        for group in report["conflict_groups"]:
            group["count"] = len(group.pop("ids"))
    return report
