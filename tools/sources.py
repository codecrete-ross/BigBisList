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

    if source_type == "quest":
        quest_starter_sources = [
            starter_source
            for starter_source in source.get("quest_starter_sources", [])
            if isinstance(starter_source, dict)
        ]
        if not quest_starter_sources:
            return None
        return source_content_type(derive_primary_source(quest_starter_sources))

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

    if isinstance(classified.get("quest_starter_sources"), list):
        classified["quest_starter_sources"] = [
            classify_source(starter_source) if isinstance(starter_source, dict) else starter_source
            for starter_source in classified["quest_starter_sources"]
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


def _infer_source_acquisition_phase(source: dict[str, Any]) -> str:
    source_type = source.get("type")
    zone, _ = normalize_source_zone(source.get("zone"))

    if source_type == "token_turnin":
        token_sources = [token_source for token_source in source.get("token_sources", []) if isinstance(token_source, dict)]
        return derive_acquisition_phase(token_sources) if token_sources else "PR"

    if source_type == "drop":
        return ZONE_PHASE.get(str(zone or ""), "PR")

    if source_type == "quest":
        quest_starter_sources = [
            starter_source
            for starter_source in source.get("quest_starter_sources", [])
            if isinstance(starter_source, dict)
        ]
        if quest_starter_sources:
            return derive_acquisition_phase(quest_starter_sources)
        quest_id = source.get("quest_id")
        if isinstance(quest_id, int):
            return RAID_QUEST_PHASE_BY_ID.get(quest_id, "PR")
        return "PR"

    if source_type in {"crafted", "taught_by_item"}:
        recipe_sources = [recipe_source for recipe_source in source.get("recipe_sources", []) if isinstance(recipe_source, dict)]
        if recipe_sources:
            return derive_acquisition_phase(recipe_sources)
        return ZONE_PHASE.get(str(zone or ""), "PR")

    if source_type == "vendor" and zone in ZONE_PHASE:
        return ZONE_PHASE[str(zone)]

    if source_type == "vendor" and zone == "Black Temple":
        return "T6"

    return "PR"


def derive_source_acquisition_phase(source: dict[str, Any]) -> str:
    # A token/recipe can exist before its seller or recipe becomes accessible.
    inferred = _infer_source_acquisition_phase(source)
    zone, _ = normalize_source_zone(source.get("zone"))
    zone_phase = ZONE_PHASE.get(str(zone or ""), "PR") if source.get("type") != "quest" else "PR"
    return max((inferred, zone_phase,
                source.get("available_from_phase", "PR")), key=phase_rank)


def source_is_phase_available(source: dict[str, Any], phase: str) -> bool:
    if phase_rank(derive_source_acquisition_phase(source)) > phase_rank(phase):
        return False
    until = source.get("available_until_phase")
    if until and phase_rank(phase) >= phase_rank(until):
        return False
    for child_key in ("token_sources", "quest_starter_sources", "recipe_sources"):
        children = source.get(child_key)
        if children and not any(source_is_phase_available(child, phase) for child in children):
            return False
    return True


RAID_REPUTATIONS = {"The Scale of the Sands", "Ashtongue Deathsworn", "The Violet Eye"}


def source_requires_raid(source: dict[str, Any], phase: str | None = None) -> bool:
    if source.get("tradeable") is True:
        return False
    inferred_craft_zone = source.get("type") == "crafted" and source.get("recipe_sources")
    if (source.get("type") != "quest" and not inferred_craft_zone and source.get("zone") in RAID_ZONES) or (
        source.get("type") not in {"quest", "token_turnin"} and source_content_type(source) == "raid"
    ):
        return True
    if source.get("quest_id") in RAID_QUEST_PHASE_BY_ID:
        return True
    if any(req.get("reputation") in RAID_REPUTATIONS for req in source.get("requirements", [])):
        return True
    # A crafted item can be bought or made using tradeable materials; learning a
    # raid-only recipe personally is represented by its recipe-source gates.
    for key in ("token_sources", "quest_starter_sources", "recipe_sources"):
        children = [child for child in source.get(key, [])
                    if phase is None or source_is_phase_available(child, phase)]
        if children and all(source_requires_raid(child, phase) for child in children):
            return True
    return False


def item_has_pre_raid_route(item: dict[str, Any], phase: str) -> bool:
    sources = item.get("sources", [])
    available = [source for source in sources if source_is_phase_available(source, phase)]
    if not available:
        return False
    if item.get("tradeable") is True or item.get("boe") is True or item.get("binding") == "bind_on_equip":
        return True
    if any(req.get("reputation") in RAID_REPUTATIONS for req in item.get("requirements", [])):
        return False
    return any(source.get("type") != "unknown" and not source_requires_raid(source, phase) for source in available)


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


def _purchase_source_quality_rank(source: dict[str, Any]) -> int:
    if source.get("type") == "unknown":
        return 4
    if source.get("type") not in {"vendor", "pvp", "token_turnin"}:
        return 0

    missing_fields = 0
    if not source.get("entity_name"):
        missing_fields += 1
    if not (source.get("location_area") or source.get("zone")):
        missing_fields += 1
    if not source.get("price_copper") and not source.get("costs"):
        missing_fields += 1
    return missing_fields


def _source_sort_key(source: dict[str, Any]) -> tuple:
    drop_percent = source.get("drop_percent")
    drop_rank = -float(drop_percent) if isinstance(drop_percent, (int, float)) else 0.0
    raw_id = source.get("quest_id") or source.get("vendor_id") or source.get("entity_id") or 0
    # Trainer groups use stable symbolic identities, whereas NPCs use numbers.
    identity = (0, int(raw_id)) if isinstance(raw_id, int) or str(raw_id).isdigit() else (1, str(raw_id))
    return (
        _source_data_quality_rank(source),
        _purchase_source_quality_rank(source),
        phase_rank(derive_source_acquisition_phase(source)),
        SOURCE_TYPE_PRIORITY.get(str(source.get("type", "unknown")), 99),
        drop_rank,
        str(source.get("entity_name") or ""),
        str(source.get("zone") or ""),
        identity,
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
        if not isinstance(cost, dict):
            continue
        amount = cost.get("amount")
        name = cost.get("name") or cost.get("currency_name") or cost.get("item_name")
        if isinstance(amount, bool) or (isinstance(amount, (int, float)) and amount <= 0):
            continue
        if amount is None and not name:
            continue
        if amount is None:
            parts.append(str(name))
        elif name:
            parts.append(f"{amount} {name}")
        else:
            parts.append(str(amount))
    return ", ".join(parts)


def format_price_copper(price_copper: Any, purchase_quantity: Any = None) -> str:
    if isinstance(price_copper, bool) or not isinstance(price_copper, (int, float)) or price_copper <= 0:
        return ""

    copper = int(price_copper)
    gold, remainder = divmod(copper, 10_000)
    silver, copper = divmod(remainder, 100)
    parts: list[str] = []
    if gold:
        parts.append(f"{gold}g")
    if silver:
        parts.append(f"{silver}s")
    if copper:
        parts.append(f"{copper}c")
    text = " ".join(parts)

    if isinstance(purchase_quantity, int) and not isinstance(purchase_quantity, bool) and purchase_quantity > 1:
        text += f" per {purchase_quantity}"
    return text


def format_purchase_cost(source: dict[str, Any]) -> str:
    parts: list[str] = []
    money = format_price_copper(source.get("price_copper"), source.get("purchase_quantity"))
    if money:
        parts.append(money)

    item_or_currency_costs = format_costs(source.get("costs"))
    if item_or_currency_costs:
        if (
            not money
            and isinstance(source.get("purchase_quantity"), int)
            and not isinstance(source.get("purchase_quantity"), bool)
            and source["purchase_quantity"] > 1
        ):
            item_or_currency_costs += f" per {source['purchase_quantity']}"
        parts.append(item_or_currency_costs)
    return " + ".join(parts)


def compact_source(source: dict[str, Any]) -> str:
    source_type = source.get("type")
    entity = source.get("entity_name") or source.get("profession")
    zone = source.get("location_area") or source.get("zone")
    costs = format_purchase_cost(source)

    if source_type == "drop":
        if source.get("world_drop"):
            return "World Drop"
        if entity:
            text = f"Drop: {entity}"
            if zone:
                text += f" ({zone})"
        elif zone:
            text = f"Drop: {zone}"
        else:
            text = "Drop"
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
        if entity:
            text = f"Quest: {entity}"
        elif zone:
            text = f"Quest: {zone}"
        else:
            text = "Quest"
        quest_starter_sources = [
            starter_source
            for starter_source in source.get("quest_starter_sources", [])
            if isinstance(starter_source, dict)
        ]
        if quest_starter_sources:
            starter_source = derive_primary_source(quest_starter_sources)
            starter_name = starter_source.get("quest_starter_name") or starter_source.get("starter_name")
            starter_entity = starter_source.get("entity_name")
            starter_zone = starter_source.get("zone")
            if starter_name:
                text += f" via {starter_name}"
            if starter_entity:
                text += f" - {starter_entity}"
                if starter_zone:
                    text += f" ({starter_zone})"
                if isinstance(starter_source.get("drop_percent"), (int, float)):
                    text += f" {float(starter_source['drop_percent']):.1f}%"
        return text

    if source_type == "vendor":
        text = f"Vendor: {entity}" if entity else "Vendor"
        if zone:
            text += f" ({zone})"
        elif costs:
            text += f" ({costs})"
        return text

    if source_type == "pvp":
        text = f"PvP: {entity}" if entity else "PvP Vendor"
        if zone:
            text += f" ({zone})"
        elif costs:
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
