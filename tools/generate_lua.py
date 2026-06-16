from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import ADDON_DIR, canonical_json, lua_value, write_text
from tools.validate_data import validate


OUTPUT_PATH = ADDON_DIR / "Data.lua"

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
]

ITEM_FALLBACK_SCHEMA = [
    "id",
    "name",
    "quality",
]

SOURCE_SCHEMA = [
    "type",
    "entity_id",
    "entity_name",
    "source_url",
    "zone",
    "content_type",
    "confidence",
    "count",
    "out_of",
    "drop_percent",
    "vendor_id",
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
]

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


SCHEMAS = {
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
    if schema_name in {"item", "source_record"}:
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

    if schema_name in {"use", "enchant", "consumable", "leveling_gear", "leveling_recommendation"} and key == "requirements":
        return compact_requirements(value)

    return value


def compact_record(record: dict, schema_name: str) -> list:
    schema = SCHEMAS[schema_name]
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


def build_uses(bis_lists: list[dict]) -> list[list]:
    uses = []
    for row in bis_lists:
        for item in row["items"]:
            use = {
                "class": row["class"],
                "spec": row["spec"],
                "phase": row["phase"],
                "slot": row["slot"],
                "source_url": row["source_url"],
                **item,
            }
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
        })

    return fallbacks


def build_data() -> dict:
    classes = canonical_json("classes")["classes"]
    phases = canonical_json("phases")["phases"]
    items = canonical_json("items")["items"]
    item_stats = canonical_json("item_stats")["item_stats"]
    bis_lists = canonical_json("bis_lists")["lists"]
    gems = canonical_json("gems")["gems"]
    gem_sources = canonical_json("gem_sources")["gem_sources"]
    enchants = canonical_json("enchants")["enchants"]
    enchant_sources = canonical_json("enchant_sources")["enchant_sources"]
    enchant_effects = canonical_json("enchant_effects")["enchant_effects"]
    consumables = canonical_json("consumables")["consumables"]
    leveling_gear = canonical_json("leveling_gear")["leveling_gear"]
    leveling_recommendations = canonical_json("leveling_recommendations")["leveling_recommendations"]
    overrides = canonical_json("overrides")["overrides"]
    manifest = canonical_json("scrape_manifest")
    lookups = build_runtime_lookups(items)
    item_fallbacks = build_item_fallbacks(items, item_stats, leveling_recommendations)

    return {
        "format": 2,
        "schemas": SCHEMAS,
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
        },
        "classes": classes,
        "phases": phases,
        "items": compact_list(items, "item"),
        "item_fallbacks": compact_list(item_fallbacks, "item_fallback"),
        "uses": build_uses(bis_lists),
        "gems": compact_list(gems, "gem"),
        "gem_sources": compact_list(gem_sources, "source_record"),
        "enchants": compact_list(enchants, "enchant"),
        "enchant_sources": compact_list(enchant_sources, "source_record"),
        "enchant_effects": compact_list(enchant_effects, "enchant_effect"),
        "consumables": compact_list(consumables, "consumable"),
        "leveling_gear": compact_list(leveling_gear, "leveling_gear"),
        "leveling_recommendations": compact_list(leveling_recommendations, "leveling_recommendation"),
        "source_types": lookups["source_types"],
        "zones": lookups["zones"],
        "tooltip_aliases": lookups["tooltip_aliases"],
    }


def render_lua() -> str:
    data = build_data()
    return "\n".join(
        [
            "-- Generated by tools/generate_lua.py; do not edit by hand.",
            "BigBiSListData = " + lua_value(data),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic BigBiSListData Lua.")
    parser.add_argument("--check", action="store_true", help="Fail if the generated output differs from Data.lua.")
    args = parser.parse_args(argv)

    result = validate()
    if not result.ok:
        for error in result.errors:
            print(f"validation error: {error}", file=sys.stderr)
        return 1

    rendered = render_lua()
    if args.check:
        if not OUTPUT_PATH.is_file():
            print(f"{OUTPUT_PATH} does not exist", file=sys.stderr)
            return 1
        existing = OUTPUT_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
        if existing != rendered:
            print(f"{OUTPUT_PATH} is not up to date", file=sys.stderr)
            return 1
        print(f"{OUTPUT_PATH} is up to date.")
        return 0

    write_text(OUTPUT_PATH, rendered)
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
