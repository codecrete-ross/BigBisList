from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import ADDON_DIR, add_flavor_argument, dataset_json, lua_value, write_text
from tools.validate_data import validate_dataset
from tools.sources import summarize_sources


OUTPUT_PATH = ADDON_DIR / "Data.lua"
FOREVER_OUTPUT_PATH = ADDON_DIR / "DataForever.lua"

SOURCE_FILTER_BY_CONTENT_TYPE = {
    "raid": "raid_drop",
    "heroic_dungeon": "heroic_dungeon_drop",
    "dungeon": "dungeon_drop",
    "other": "other_drop",
}

SOURCE_FILTER_ORDER = {
    "raid_drop": 1,
    "heroic_dungeon_drop": 2,
    "dungeon_drop": 3,
    "other_drop": 4,
    "quest": 10,
    "vendor": 11,
    "crafted": 12,
    "trade": 13,
    "pvp": 14,
    "token_turnin": 15,
    "taught_by_item": 16,
    "world_drop": 17,
    "unknown": 99,
}

ITEM_SCHEMA = [
    "id",
    "name",
    "quality",
    "binding",
    "boe",
    "inventory_slot",
    "source_summary",
    "wowhead_url",
    "acquisition_phase",
    "primary_source",
    "sources",
    "requirements",
    "tradeable",
]

ITEM_FALLBACK_SCHEMA = [
    "id",
    "name",
    "quality",
    "source_summary",
    "wowhead_url",
    "acquisition_phase",
    "primary_source",
    "sources",
    "requirements",
]

SOURCE_SCHEMA = [
    "type",
    "entity_id",
    "entity_name",
    "source_url",
    "zone",
    "location_area",
    "location_note",
    "content_type",
    "confidence",
    "count",
    "out_of",
    "drop_percent",
    "vendor_id",
    "price_copper",
    "purchase_quantity",
    "costs",
    "token_sources",
    "quest_id",
    "spell_id",
    "profession",
    "requirements",
    "difficulty",
    "recipe_sources",
    "side",
    "world_drop",
    "item_id",
    "quest_starter_sources",
    "raw_source_text",
    "token_count",
    "token_item_id",
    "token_name",
    "token_source_url",
    "quest_starter_item_id",
    "quest_starter_name",
    "quest_starter_relationship",
    "quest_starter_source_url",
    "available_from_phase",
    "available_until_phase",
    "tradeable",
    "activity_zones",
    "quest_steps",
    "destination",
    "attribution",
]

FOREVER_SOURCE_SCHEMA = SOURCE_SCHEMA + ["eligibility", "recipe_name"]

REQUIREMENT_SCHEMA = [
    "type",
    "scope",
    "raw_text",
    "confidence",
    "source_url",
    "profession",
    "reputation",
    "standing",
    "standing_rank",
    "skill",
    "spell_id",
    "spell_name",
    "specialization",
    "choices",
]

COST_SCHEMA = ["amount", "name", "currency_id", "item_id"]

USE_SCHEMA = [
    "class",
    "spec",
    "phase",
    "slot",
    "source_url",
    "item_id",
    "rank",
    "rank_label",
    "rank_group",
    "context",
    "note",
    "requirements",
    "content_phase",
    "guide_evidence",
]

GUIDE_EVIDENCE_SCHEMA = [
    "table_id", "guide_phase", "rating_phase", "original_rating", "grade",
    "conditions", "source_url", "content_phase", "table_heading",
]

GEM_SCHEMA = [
    "class",
    "spec",
    "phase",
    "id",
    "name",
    "context",
    "meta",
    "socket_category",
    "socket_color",
    "source_summary",
    "source_url",
    "quality",
    "requirements",
]

ENCHANT_SCHEMA = [
    "class",
    "spec",
    "phase",
    "id",
    "name",
    "type",
    "slot",
    "context",
    "source_summary",
    "source_url",
    "requirements",
    "taught_by",
    "formula_item_ids",
    "source_spell_id",
]

CONSUMABLE_SCHEMA = [
    "class",
    "spec",
    "phase",
    "category",
    "category_label",
    "items",
    "item_names",
    "item_categories",
    "relationship",
    "source_summaries",
    "source_url",
    "text",
    "requirements",
]

LEVELING_GEAR_SCHEMA = [
    "class",
    "spec",
    "level_min",
    "level_max",
    "level_label",
    "slot",
    "item_id",
    "rank",
    "category_label",
    "section",
    "source_note",
    "source_url",
    "requirements",
]

LEVELING_RECOMMENDATION_SCHEMA = [
    "class",
    "spec",
    "race",
    "level_min",
    "level_max",
    "level_band",
    "slot",
    "item_id",
    "variant_id",
    "rank",
    "context",
    "source_bucket",
    "score",
    "score_delta_pct",
    "reason_tags",
    "source_summary",
    "source_url",
    "requirements",
]

SOURCE_RECORD_SCHEMA = [
    "id",
    "name",
    "type",
    "source_summary",
    "source_url",
    "primary_source",
    "sources",
    "requirements",
    "binding",
    "boe",
    "tradeable",
]

ENCHANT_EFFECT_SCHEMA = [
    "id",
    "type",
    "name",
    "slot",
    "source_spell_id",
    "effect_ids",
    "source_url",
]


LEVELING_AVAILABILITY_SCHEMA = ["class", "spec", "faction", "race_id", "slot", "level_min", "level_max", "state", "reason"]

SCHEMAS = {
    "guide_evidence": GUIDE_EVIDENCE_SCHEMA,
    "item": ITEM_SCHEMA,
    "item_fallback": ITEM_FALLBACK_SCHEMA,
    "source": SOURCE_SCHEMA,
    "requirement": REQUIREMENT_SCHEMA,
    "cost": COST_SCHEMA,
    "use": USE_SCHEMA,
    "gem": GEM_SCHEMA,
    "enchant": ENCHANT_SCHEMA,
    "consumable": CONSUMABLE_SCHEMA,
    "leveling_gear": LEVELING_GEAR_SCHEMA,
    "leveling_recommendation": LEVELING_RECOMMENDATION_SCHEMA,
    "source_record": SOURCE_RECORD_SCHEMA,
    "enchant_effect": ENCHANT_EFFECT_SCHEMA,
}


def compact_list(values: list[dict], schema_name: str) -> list[list]:
    return [compact_record(value, schema_name) for value in values]


def compact_source(source: dict | None) -> list | None:
    if not source:
        return None
    return compact_record(source, "source")


def compact_requirements(requirements: list[dict] | None) -> list[list] | None:
    if not requirements:
        return None
    return compact_list(requirements, "requirement")


def compact_value(schema_name: str, key: str, value):
    if schema_name == "use" and key == "guide_evidence":
        if value and isinstance(value[0], int):
            return value
        return compact_list(value, "guide_evidence") if value else None
    if schema_name in {"item", "item_fallback", "source_record"}:
        if key == "primary_source":
            return compact_source(value)
        if key == "sources":
            return compact_list(value, "source") if value else None
        if key == "requirements":
            return compact_requirements(value)

    if schema_name == "source":
        if key in {"token_sources", "quest_starter_sources", "recipe_sources"}:
            return compact_list(value, "source") if value else None
        if key == "requirements":
            return compact_requirements(value)
        if key == "costs":
            return compact_list(value, "cost") if value else None

    if schema_name in {"use", "gem", "enchant", "consumable", "leveling_gear", "leveling_recommendation"} and key == "requirements":
        return compact_requirements(value)

    return value


def compact_record(record: dict, schema_name: str) -> list:
    schema = LEVELING_AVAILABILITY_SCHEMA if schema_name == "leveling_availability" else SCHEMAS[schema_name]
    if schema_name == "source" and "eligibility" in record:
        schema = FOREVER_SOURCE_SCHEMA
    elif schema_name == "leveling_recommendation" and "faction" in record:
        schema = schema + ["faction", "race_id", "variant_name", "random_suffix_id"]
    elif schema_name == "leveling_gear" and "faction" in record:
        schema = schema + ["race", "faction", "race_id", "variant_id", "variant_name", "random_suffix_id"]
    compacted = [
        compact_value(schema_name, key, record[key]) if key in record else None
        for key in schema
    ]
    while compacted and compacted[-1] is None:
        compacted.pop()
    return compacted


def source_filter_key(item: dict) -> str:
    source = item.get("primary_source") or next(iter(item.get("sources") or []), None)
    if not source:
        return "unknown"

    source_type = source.get("type") or "unknown"
    content_type = source.get("content_type")
    if source_type == "drop" or content_type:
        return SOURCE_FILTER_BY_CONTENT_TYPE.get(content_type, "other_drop")
    return source_type


def add_zone(zones: set[str], zone: str | None) -> None:
    if zone:
        zones.add(zone)


def add_zones_from_source(zones: set[str], source: dict | None, include_drop_zone: bool) -> None:
    if not source:
        return
    if source.get("type") != "drop" or include_drop_zone:
        add_zone(zones, source.get("zone"))
        for zone in source.get("activity_zones", []):
            add_zone(zones, zone)
    if source.get("type") == "token_turnin":
        for token_source in source.get("token_sources") or []:
            add_zone(zones, token_source.get("zone"))
    if source.get("type") == "quest":
        for starter_source in source.get("quest_starter_sources") or []:
            add_zone(zones, starter_source.get("zone"))


def item_zones(item: dict) -> set[str]:
    zones: set[str] = set()
    add_zones_from_source(zones, item.get("primary_source"), True)
    for source in item.get("sources") or []:
        add_zones_from_source(zones, source, False)
    return zones


def source_filter_sort_key(value: str) -> tuple[int, str]:
    return SOURCE_FILTER_ORDER.get(value, 50), value


def build_runtime_lookups(items: list[dict]) -> dict:
    source_types = sorted({source_filter_key(item) for item in items}, key=source_filter_sort_key)
    zones = sorted({zone for item in items for zone in item_zones(item)})
    tooltip_aliases = []

    for item in items:
        aliases = []
        seen = set()
        for source in item.get("sources") or []:
            for starter_source in source.get("quest_starter_sources") or []:
                starter_id = starter_source.get("quest_starter_item_id")
                if starter_id and starter_id not in seen:
                    seen.add(starter_id)
                    aliases.append(starter_id)
        if aliases:
            tooltip_aliases.append([item["id"], aliases])

    return {
        "source_types": source_types,
        "zones": zones,
        "tooltip_aliases": tooltip_aliases,
    }


def build_uses(bis_lists: list[dict], evidence_pool: list[list] | None = None) -> list[list]:
    uses = []
    evidence_ids = {}
    for row in bis_lists:
        for item in row["items"]:
            use = {
                "class": row["class"],
                "spec": row["spec"],
                "phase": row["phase"],
                "slot": row["slot"],
                "source_url": row["source_url"],
                "content_phase": row.get("content_phase"),
                **item,
            }
            if evidence_pool is not None and item.get("guide_evidence"):
                references = []
                for evidence in compact_list(item["guide_evidence"], "guide_evidence"):
                    key = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
                    if key not in evidence_ids:
                        evidence_pool.append(evidence)
                        evidence_ids[key] = len(evidence_pool)
                    references.append(evidence_ids[key])
                use["guide_evidence"] = references
            uses.append(compact_record(use, "use"))
    return uses


def build_item_fallbacks(items: list[dict], item_stats: list[dict], leveling_recommendations: list[dict]) -> list[dict]:
    full_item_ids = {item["id"] for item in items}
    needed_ids = {
        row["item_id"]
        for row in leveling_recommendations
        if row.get("item_id") not in full_item_ids
    }
    stats_by_id = {item["id"]: item for item in item_stats}
    fallbacks = []

    for item_id in sorted(needed_ids):
        item = stats_by_id.get(item_id)
        if not item:
            continue
        fallbacks.append({
            "id": item_id,
            "name": item.get("name"),
            "quality": item.get("quality"),
            "source_summary": item.get("source_summary"),
            "wowhead_url": item.get("wowhead_url"),
            "acquisition_phase": item.get("acquisition_phase") or item.get("phase"),
            "primary_source": item.get("primary_source"),
            "sources": item.get("sources"),
            "requirements": item.get("requirements"),
        })

    return fallbacks


def merge_forever_leveling_rows(base: list[dict], supplemental: list[dict]) -> list[dict]:
    """Shared items retain reviewed routes from both independently audited families."""
    merged = {row["id"]: dict(row) for row in base}
    fact_fields = ("name", "slot", "inventory_slot", "required_level", "item_level", "armor_type", "weapon_subtype",
                   "weapon_speed", "dps", "armor", "stats", "restrictions", "effect_stats", "equip_effects",
                   "use_effects", "set_bonuses", "sockets", "max_equipped")
    def route_base_identity(source):
        if source.get("type") == "trade":
            # Alliance and Horde price tables are distinct trade venues, not
            # conflicting faction claims about a single drop or vendor.
            market = source.get("market_observation", {}).get("market")
            return ("trade", source.get("item_id"), market or source.get("source_url"))
        keys = ("quest_id", "entity_id", "vendor_id", "spell_id", "item_id")
        if not any(source.get(key) for key in keys):
            return None
        return tuple(source.get(key) for key in ("type", *keys, "zone", "content_type", "difficulty", "profession"))
    def quest_branch(source):
        return tuple(sorted({step["quest_id"] for step in source.get("quest_steps", [])
                             if step.get("kind") == "prerequisite"}))
    def recipe_branch(source):
        # A shared craft can be learned from different faction vendors. Keep
        # their access paths separate; faction eligibility is still compared
        # for observations about the same named recipe supplier.
        return tuple(sorted(json.dumps(route_base_identity(child), separators=(",", ":"))
                            for child in source.get("recipe_sources", [])))
    def route_identity(source):
        identity = route_base_identity(source)
        if identity is not None and source.get("type") == "quest":
            # The same reward quest can have separately reviewed faction
            # entry chains, with different acquisition minimums.
            return (*identity, quest_branch(source))
        if identity is not None and source.get("type") == "crafted":
            return (*identity, recipe_branch(source))
        return identity
    def check_route_eligibility(left, right, item_id):
        def eligibility(rule):
            return {key: sorted(value) if isinstance(value, list) else value
                    for key, value in rule.items() if key != "basis"}
        if (left.get("side") != right.get("side") or
                (left.get("eligibility") and right.get("eligibility")
                 and eligibility(left["eligibility"]) != eligibility(right["eligibility"]))):
            raise ValueError(f"Conflicting approved Forever route eligibility for item {item_id}")
        def requirement_gates(source):
            keys = ("type", "scope", "profession", "skill", "reputation", "standing", "standing_rank",
                    "spell_id", "specialization", "choices")
            return sorted(json.dumps({key: sorted(row[key]) if isinstance(row[key], list) else row[key]
                                      for key in keys if key in row}, sort_keys=True, separators=(",", ":"))
                          for row in source.get("requirements", [])
                          if row.get("type") in {"profession", "profession_specialization", "recipe_known",
                                                 "reputation", "faction_choice"})
        if requirement_gates(left) != requirement_gates(right):
            raise ValueError(f"Conflicting approved Forever route requirements for item {item_id}")
        for family in ("recipe_sources", "token_sources", "quest_starter_sources"):
            for child in right.get(family, []):
                identity = route_identity(child)
                match = next((row for row in left.get(family, [])
                              if identity is not None and route_identity(row) == identity), None)
                if match is not None:
                    check_route_eligibility(match, child, item_id)
    for row in supplemental:
        previous = merged.get(row["id"])
        if previous is None:
            merged[row["id"]] = dict(row)
            continue
        for key in fact_fields:
            if previous.get(key) is not None and row.get(key) is not None and previous[key] != row[key]:
                raise ValueError(f"Conflicting approved Forever {key} for item {row['id']}")
        combined = {**previous, **row}
        sources = []
        for source in row.get("sources", []) + previous.get("sources", []):
            identity = route_identity(source)
            existing = next((candidate for candidate in sources if identity is not None and route_identity(candidate)==identity),None)
            if existing is None and source.get("type") == "quest" and identity is not None:
                for candidate in sources:
                    if (route_base_identity(candidate) == route_base_identity(source)
                            and (not quest_branch(candidate) or not quest_branch(source))):
                        # An older route without its prerequisite chain cannot
                        # become an unrestricted alternative to a reviewed one.
                        raise ValueError(f"Ambiguous approved Forever quest branch for item {row['id']}")
            if existing is None and source.get("type") == "crafted" and identity is not None:
                for candidate in sources:
                    if (route_base_identity(candidate) == route_base_identity(source)
                            and (not recipe_branch(candidate) or not recipe_branch(source))):
                        raise ValueError(f"Ambiguous approved Forever recipe access for item {row['id']}")
            if existing is not None:
                check_route_eligibility(existing, source, row["id"])
                # Prefer the leveling route's explicit eligibility over an
                # older representation of that same acquisition route.
                continue
            if source not in sources:
                sources.append(source)
        if sources:
            combined["sources"] = sources
            combined["primary_source"] = sources[0]
            combined["source_summary"] = summarize_sources(sources)
        merged[row["id"]] = combined
    return [merged[key] for key in sorted(merged)]


def build_data(flavor: str) -> dict:
    def document(name: str) -> dict:
        return dataset_json(flavor, name)

    def optional_rows(name: str) -> list:
        if flavor == "forever" and name not in {"leveling_gear", "leveling_recommendations"}:
            return []
        return document(name)[name]

    classes = document("classes")["classes"]
    phase_document = document("phases")
    phases = phase_document["phases"]
    items = document("items")["items"]
    item_stats = document("item_stats")["item_stats"]
    if flavor == "forever":
        from tools.project import FOREVER_CANONICAL_DIR
        for name, key in (("leveling_items", "items"), ("leveling_item_stats", "item_stats")):
            if (FOREVER_CANONICAL_DIR / (name + ".json")).is_file():
                if key == "items":
                    items = merge_forever_leveling_rows(items, document(name)[key])
                else:
                    item_stats = merge_forever_leveling_rows(item_stats, document(name)[key])
    bis_lists = document("bis_lists")["lists"]
    gems = optional_rows("gems")
    gem_sources = optional_rows("gem_sources")
    enchants = optional_rows("enchants")
    enchant_sources = optional_rows("enchant_sources")
    enchant_effects = optional_rows("enchant_effects")
    consumables = optional_rows("consumables")
    leveling_gear = optional_rows("leveling_gear")
    leveling_recommendations = optional_rows("leveling_recommendations")
    availability_data = {}
    if flavor == "forever":
        from tools.forever_comparison import compile_comparison_data
        from tools.forever_scoring import reviewed_runtime_model
        from tools.project import FOREVER_CANONICAL_DIR
        availability_rows = (document("leveling_availability")["leveling_availability"]
                             if (FOREVER_CANONICAL_DIR / "leveling_availability.json").is_file() else [])
        rules = document("leveling_rules")
        availability_data = {
            "stat_rank": compile_comparison_data(item_stats),
            "leveling_availability": compact_list(availability_rows, "leveling_availability"),
            "leveling_availability_rules": {
                "common_slots": rules["common_slots"], "races": rules["races"],
                "spec_policies": {key: {field: value[field] for field in ("slots", "slot_min_levels", "slot_max_levels") if field in value}
                                  for key, value in rules["spec_policies"].items()},
            },
        }
        character_scoring = reviewed_runtime_model()
        if character_scoring:
            availability_data["character_scoring"] = character_scoring
    overrides = document("overrides")["overrides"]
    manifest = document("scrape_manifest")
    lookups = build_runtime_lookups(items)
    item_fallbacks = build_item_fallbacks(items, item_stats, leveling_recommendations)
    guide_evidence = []
    uses = build_uses(bis_lists, guide_evidence)

    return {
        "format": 2,
        "schemas": ({**SCHEMAS, "source": FOREVER_SOURCE_SCHEMA,
                     "leveling_availability": LEVELING_AVAILABILITY_SCHEMA,
                     "leveling_gear": LEVELING_GEAR_SCHEMA + ["race", "faction", "race_id", "variant_id", "variant_name", "random_suffix_id"],
                     "leveling_recommendation": LEVELING_RECOMMENDATION_SCHEMA + ["faction", "race_id", "variant_name", "random_suffix_id"]}
                    if flavor == "forever" else SCHEMAS),
        "meta": {
            "addon": "Big BiS List",
            "data_version": "seed-0.1.0",
            "parser_version": manifest["parser_version"],
            "item_count": len(items),
            "slot_list_count": len(bis_lists),
            "use_count": sum(len(row["items"]) for row in bis_lists),
            "gem_count": len(gems),
            "enchant_count": len(enchants),
            "consumable_count": len(consumables),
            "leveling_gear_count": len(leveling_gear),
            "leveling_recommendation_count": len(leveling_recommendations),
            "item_fallback_count": len(item_fallbacks),
            "override_count": len(overrides),
            **({"flavor": flavor, "level_cap": 60, "supports_leveling": True} if flavor == "forever" else {}),
        },
        "classes": classes,
        "phases": phases,
        "active_schedule": phase_document.get("active_schedule"),
        "phase_schedules": phase_document.get("schedules", {}),
        "items": compact_list(items, "item"),
        "item_fallbacks": compact_list(item_fallbacks, "item_fallback"),
        "item_class_restrictions": {
            item["id"]: sorted(set(item["restrictions"]["classes"]))
            for item in item_stats if item.get("restrictions", {}).get("classes")
        },
        **({"item_eligibility": {item["id"]: {"min_level": item.get("required_level"),
                "classes": item.get("restrictions", {}).get("classes", []),
                "races": item.get("restrictions", {}).get("races", [])} for item in item_stats}}
           if flavor == "forever" else {}),
        "uses": uses,
        "guide_evidence": guide_evidence,
        "gems": compact_list(gems, "gem"),
        "gem_sources": compact_list(gem_sources, "source_record"),
        "enchants": compact_list(enchants, "enchant"),
        "enchant_sources": compact_list(enchant_sources, "source_record"),
        "enchant_effects": compact_list(enchant_effects, "enchant_effect"),
        "consumables": compact_list(consumables, "consumable"),
        "leveling_gear": compact_list(leveling_gear, "leveling_gear"),
        "leveling_recommendations": compact_list(leveling_recommendations, "leveling_recommendation"),
        **availability_data,
        "source_types": lookups["source_types"],
        "zones": lookups["zones"],
        "tooltip_aliases": lookups["tooltip_aliases"],
    }


def render_lua(flavor: str) -> str:
    data = build_data(flavor)
    return "\n".join(
        [
            "-- Generated by tools/generate_lua.py; do not edit by hand.",
            "BigBiSListData = " + lua_value(data),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic BigBiSListData Lua.")
    add_flavor_argument(parser)
    parser.add_argument("--check", action="store_true", help="Fail if the generated output differs from Data.lua.")
    args = parser.parse_args(argv)

    result = validate_dataset(args.flavor)
    if not result.ok:
        for error in result.errors:
            print(f"validation error: {error}", file=sys.stderr)
        return 1

    output_path = FOREVER_OUTPUT_PATH if args.flavor == "forever" else OUTPUT_PATH
    rendered = render_lua(args.flavor)
    if args.check:
        if not output_path.is_file():
            print(f"{output_path} does not exist", file=sys.stderr)
            return 1
        existing = output_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if existing != rendered:
            print(f"{output_path} is not up to date", file=sys.stderr)
            return 1
        print(f"{output_path} is up to date.")
        return 0

    write_text(output_path, rendered)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
