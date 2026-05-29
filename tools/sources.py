from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

PHASE_ORDER = ["PR", "T4", "T5", "T6", "ZA", "SWP"]
PHASE_INDEX = {phase: index for index, phase in enumerate(PHASE_ORDER)}

RAID_ZONE_PHASE = {
    "Karazhan": "T4",
    "Gruul's Lair": "T4",
    "Magtheridon's Lair": "T4",
    "Serpentshrine Cavern": "T5",
    "Tempest Keep": "T5",
    "Hyjal Summit": "T6",
    "Black Temple": "T6",
    "Zul'Aman": "ZA",
    "Sunwell Plateau": "SWP",
}

CLASSIC_RAID_ZONES = {
    "Molten Core",
    "Blackwing Lair",
    "Zul'Gurub",
    "Ruins of Ahn'Qiraj",
    "Ahn'Qiraj",
    "Naxxramas",
}

TBC_DUNGEON_ZONES = {
    "Hellfire Ramparts",
    "The Blood Furnace",
    "The Shattered Halls",
    "The Slave Pens",
    "The Underbog",
    "The Steamvault",
    "Mana-Tombs",
    "Auchenai Crypts",
    "Sethekk Halls",
    "Shadow Labyrinth",
    "Old Hillsbrad Foothills",
    "The Black Morass",
    "The Botanica",
    "The Mechanar",
    "The Arcatraz",
    "Magisters' Terrace",
}

CLASSIC_DUNGEON_ZONES = {
    "Blackrock Depths",
    "Blackrock Spire",
    "Dire Maul",
    "Scholomance",
    "Stratholme",
}

RAID_ZONES = frozenset(set(RAID_ZONE_PHASE) | CLASSIC_RAID_ZONES)
DUNGEON_ZONES = frozenset(TBC_DUNGEON_ZONES | CLASSIC_DUNGEON_ZONES)

ZONE_PHASE = {
    **RAID_ZONE_PHASE,
    "Isle of Quel'Danas": "SWP",
}

RAID_QUEST_PHASE_BY_ID = {
    10725: "T4",
    10726: "T4",
    10727: "T4",
    10728: "T4",
    11031: "T4",
    11032: "T4",
    11033: "T4",
    11034: "T4",
    11007: "T5",
}

SOURCE_TYPE_PRIORITY = {
    "drop": 0,
    "token_turnin": 1,
    "quest": 2,
    "pvp": 3,
    "vendor": 4,
    "crafted": 5,
    "world_drop": 6,
    "unknown": 99,
}

SOURCE_FILTER_KEYS_BY_CONTENT_TYPE = {
    "raid": "raid_drop",
    "heroic_dungeon": "heroic_dungeon_drop",
    "dungeon": "dungeon_drop",
    "other": "other_drop",
}


def phase_rank(phase: str | None) -> int:
    return PHASE_INDEX.get(str(phase or "PR"), 999)


def normalize_source_zone(zone: str | None) -> tuple[str | None, str | None]:
    if not isinstance(zone, str):
        return None, None

    normalized = zone.strip()
    match = re.match(r"^heroic\s+(.+)$", normalized, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(), "heroic"

    return normalized or None, None


def source_text_has_heroic(text: str | None) -> bool:
    return isinstance(text, str) and bool(re.search(r"\bheroic\b", text, flags=re.IGNORECASE))


def source_difficulty(source: dict[str, Any]) -> str | None:
    if source.get("difficulty") == "heroic":
        return "heroic"

    _, zone_difficulty = normalize_source_zone(source.get("zone"))
    if zone_difficulty == "heroic":
        return "heroic"

    if source_text_has_heroic(source.get("raw_source_text")):
        return "heroic"

    return None


def source_content_type(source: dict[str, Any]) -> str | None:
    source_type = source.get("type")

    if source_type == "token_turnin":
        token_sources = [token_source for token_source in source.get("token_sources", []) if isinstance(token_source, dict)]
        if not token_sources:
            return None
        return source_content_type(derive_primary_source(token_sources))

    if source_type != "drop":
        return None

    if source.get("world_drop"):
        return "other"

    zone, _ = normalize_source_zone(source.get("zone"))
    if zone in RAID_ZONES:
        return "raid"
    if zone in DUNGEON_ZONES:
        return "heroic_dungeon" if source_difficulty(source) == "heroic" else "dungeon"
    return "other"


def source_filter_key(source: dict[str, Any]) -> str:
    content_type = source_content_type(source)
    if content_type:
        return SOURCE_FILTER_KEYS_BY_CONTENT_TYPE.get(content_type, "other_drop")
    return str(source.get("type") or "unknown")


def classify_source(source: dict[str, Any]) -> dict[str, Any]:
    classified = deepcopy(source)

    zone, zone_difficulty = normalize_source_zone(classified.get("zone"))
    if zone:
        classified["zone"] = zone

    difficulty = classified.get("difficulty") or zone_difficulty
    if classified.get("type") == "drop" and (difficulty == "heroic" or source_text_has_heroic(classified.get("raw_source_text"))):
        classified["difficulty"] = "heroic"

    if isinstance(classified.get("token_sources"), list):
        classified["token_sources"] = [
            classify_source(token_source) if isinstance(token_source, dict) else token_source
            for token_source in classified["token_sources"]
        ]

    if isinstance(classified.get("recipe_sources"), list):
        classified["recipe_sources"] = [
            classify_source(recipe_source) if isinstance(recipe_source, dict) else recipe_source
            for recipe_source in classified["recipe_sources"]
        ]

    content_type = source_content_type(classified)
    if content_type:
        classified["content_type"] = content_type

    return classified


def classify_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [classify_source(source) for source in sources]


def derive_source_acquisition_phase(source: dict[str, Any]) -> str:
    source_type = source.get("type")
    zone, _ = normalize_source_zone(source.get("zone"))

    if source_type == "token_turnin":
        token_sources = [token_source for token_source in source.get("token_sources", []) if isinstance(token_source, dict)]
        return derive_acquisition_phase(token_sources) if token_sources else "PR"

    if source_type == "drop":
        return ZONE_PHASE.get(str(zone or ""), "PR")

    if source_type == "quest":
        quest_id = source.get("quest_id")
        if isinstance(quest_id, int):
            return RAID_QUEST_PHASE_BY_ID.get(quest_id, "PR")
        return "PR"

    if source_type == "crafted":
        recipe_sources = [recipe_source for recipe_source in source.get("recipe_sources", []) if isinstance(recipe_source, dict)]
        if recipe_sources:
            return derive_acquisition_phase(recipe_sources)
        return ZONE_PHASE.get(str(zone or ""), "PR")

    if source_type == "vendor" and zone in ZONE_PHASE:
        return ZONE_PHASE[str(zone)]

    if source_type == "vendor" and zone == "Black Temple":
        return "T6"

    return "PR"


def _is_concrete_raid_drop(source: dict[str, Any]) -> bool:
    zone, _ = normalize_source_zone(source.get("zone"))
    return source.get("type") == "drop" and zone in RAID_ZONE_PHASE


def _is_weak_ambiguous_drop(source: dict[str, Any]) -> bool:
    if source.get("type") != "drop" or _is_concrete_raid_drop(source):
        return False

    count = source.get("count")
    out_of = source.get("out_of")
    if isinstance(count, (int, float)) and isinstance(out_of, (int, float)):
        return count < 0 or out_of <= 0

    return source.get("drop_percent") is None


def _sources_for_acquisition_phase(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not any(_is_concrete_raid_drop(source) for source in sources):
        return sources

    filtered = [source for source in sources if not _is_weak_ambiguous_drop(source)]
    return filtered or sources


def derive_acquisition_phase(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "PR"
    return min((derive_source_acquisition_phase(source) for source in _sources_for_acquisition_phase(sources)), key=phase_rank)


def _source_data_quality_rank(source: dict[str, Any]) -> int:
    if source.get("type") != "drop":
        return 0

    count = source.get("count")
    out_of = source.get("out_of")
    if isinstance(count, (int, float)) and isinstance(out_of, (int, float)):
        if count >= 0 and out_of > 0:
            return 0
        return 2

    return 1 if source.get("drop_percent") is None else 0


def _source_sort_key(source: dict[str, Any]) -> tuple:
    drop_percent = source.get("drop_percent")
    drop_rank = -float(drop_percent) if isinstance(drop_percent, (int, float)) else 0.0
    return (
        _source_data_quality_rank(source),
        phase_rank(derive_source_acquisition_phase(source)),
        SOURCE_TYPE_PRIORITY.get(str(source.get("type", "unknown")), 99),
        drop_rank,
        str(source.get("entity_name") or ""),
        str(source.get("zone") or ""),
        int(source.get("quest_id") or source.get("vendor_id") or source.get("entity_id") or 0),
    )


def derive_primary_source(sources: list[dict[str, Any]]) -> dict[str, Any]:
    if not sources:
        return {"type": "unknown", "entity_name": "Unknown", "confidence": "missing"}
    return deepcopy(sorted(sources, key=_source_sort_key)[0])


def format_costs(costs: list[dict[str, Any]] | None) -> str:
    if not costs:
        return ""

    parts: list[str] = []
    for cost in costs:
        amount = cost.get("amount")
        name = cost.get("name") or cost.get("currency_name") or cost.get("item_name")
        if amount is None and not name:
            continue
        if amount is None:
            parts.append(str(name))
        elif name:
            parts.append(f"{amount} {name}")
        else:
            parts.append(str(amount))
    return ", ".join(parts)


def compact_source(source: dict[str, Any]) -> str:
    source_type = source.get("type")
    entity = source.get("entity_name") or source.get("profession") or "Unknown"
    zone = source.get("zone")
    costs = format_costs(source.get("costs"))

    if source_type == "drop":
        if source.get("world_drop"):
            return "World Drop"
        text = f"Drop: {entity}"
        if zone:
            text += f" ({zone})"
        if isinstance(source.get("drop_percent"), (int, float)):
            text += f" {float(source['drop_percent']):.1f}%"
        return text

    if source_type == "world_drop":
        return "World Drop"

    if source_type == "token_turnin":
        token_sources = source.get("token_sources") or []
        first_token_source = derive_primary_source(token_sources) if token_sources else {}
        token_name = (
            first_token_source.get("token_name")
            or first_token_source.get("token_item_name")
            or next((cost.get("name") for cost in source.get("costs", []) if cost.get("item_id")), None)
            or "Token"
        )
        text = f"Token: {token_name}"
        token_entity = first_token_source.get("entity_name")
        token_zone = first_token_source.get("zone")
        if token_entity:
            text += f" - {token_entity}"
            if token_zone:
                text += f" ({token_zone})"
            if isinstance(first_token_source.get("drop_percent"), (int, float)):
                text += f" {float(first_token_source['drop_percent']):.1f}%"
        elif source.get("entity_name"):
            text += f" - Turn in to {source['entity_name']}"
        if len(token_sources) > 1:
            text += f" +{len(token_sources) - 1}"
        return text

    if source_type == "quest":
        return f"Quest: {entity}"

    if source_type == "vendor":
        text = f"Vendor: {entity}"
        if costs:
            text += f" ({costs})"
        elif zone:
            text += f" ({zone})"
        return text

    if source_type == "pvp":
        text = f"PvP: {entity}"
        if costs:
            text += f" ({costs})"
        return text

    if source_type == "crafted":
        return f"Crafted: {entity}"

    return str(entity)


def summarize_sources(sources: list[dict[str, Any]]) -> str:
    primary = derive_primary_source(sources)
    text = compact_source(primary)
    extra_count = 0 if primary.get("type") == "token_turnin" else max(0, len(sources) - 1)
    if extra_count:
        text += f" +{extra_count}"
    return text
