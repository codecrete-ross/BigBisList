from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


MAX_LEVELING_LEVEL = 69

LEVEL_BANDS: list[tuple[str, int, int]] = [
    ("1-19", 1, 19),
    ("20-39", 20, 39),
    ("40-57", 40, 57),
    ("58-69", 58, MAX_LEVELING_LEVEL),
]

TBC_RACES = [
    "Blood Elf",
    "Draenei",
    "Dwarf",
    "Gnome",
    "Human",
    "Night Elf",
    "Orc",
    "Tauren",
    "Troll",
    "Undead",
]

RACE_TAG_PREFIXES = {
    "Draenei": ("draenei_",),
    "Dwarf": ("dwarf_",),
    "Gnome": ("gnome_",),
    "Human": ("human_",),
    "Night Elf": ("night_elf_",),
    "Orc": ("orc_",),
    "Tauren": ("tauren_",),
    "Troll": ("troll_",),
}

# Runtime recommendations intentionally ship only the contexts named in
# scoring_profiles.runtime_contexts. Other scoring hooks stay here so future
# contexts can be enabled by data, not code shape.
SOURCE_BUCKET_MODIFIERS = {
    "best_overall": {},
    "hit": {"hit_rating": 0.5, "spell_hit_rating": 0.5, "hit_percent": 8.0, "spell_hit_percent": 8.0},
    "survival": {"stamina": 0.8, "armor": 0.03, "dodge_rating": 0.5, "defense_rating": 0.5},
}

CLASS_WEAPON_SUBTYPES = {
    "Druid": {"Dagger", "Fist Weapon", "Mace", "Staff"},
    "Hunter": {"Axe", "Bow", "Crossbow", "Dagger", "Fist Weapon", "Gun", "Polearm", "Staff", "Sword", "Thrown"},
    "Mage": {"Dagger", "Staff", "Sword", "Wand"},
    "Paladin": {"Axe", "Mace", "Polearm", "Sword"},
    "Priest": {"Dagger", "Mace", "Staff", "Wand"},
    "Rogue": {"Bow", "Crossbow", "Dagger", "Fist Weapon", "Gun", "Mace", "Sword", "Thrown"},
    "Shaman": {"Axe", "Dagger", "Fist Weapon", "Mace", "Staff"},
    "Warlock": {"Dagger", "Staff", "Sword", "Wand"},
    "Warrior": {"Axe", "Bow", "Crossbow", "Dagger", "Fist Weapon", "Gun", "Mace", "Polearm", "Staff", "Sword", "Thrown"},
}

CLASS_RANGED_AMMO_SUBTYPES = {
    "Hunter": {"Bow", "Crossbow", "Gun"},
    "Rogue": {"Bow", "Crossbow", "Gun"},
    "Warrior": {"Bow", "Crossbow", "Gun"},
}

CLASS_RELIC_ARMOR_TYPES = {
    "Druid": {"Idol"},
    "Paladin": {"Libram"},
    "Shaman": {"Totem"},
}

RELIC_TYPE_TOKENS = {
    "Idol": ("idol",),
    "Libram": ("libram", "book", "tome"),
    "Totem": ("totem",),
}

CLASS_ARMOR_PROFICIENCIES = {
    "Druid": {1: {"Cloth", "Leather"}},
    "Hunter": {1: {"Cloth", "Leather"}, 40: {"Cloth", "Leather", "Mail"}},
    "Mage": {1: {"Cloth"}},
    "Paladin": {1: {"Cloth", "Leather", "Mail", "Shield"}, 40: {"Cloth", "Leather", "Mail", "Plate", "Shield"}},
    "Priest": {1: {"Cloth"}},
    "Rogue": {1: {"Cloth", "Leather"}},
    "Shaman": {1: {"Cloth", "Leather", "Shield"}, 40: {"Cloth", "Leather", "Mail", "Shield"}},
    "Warlock": {1: {"Cloth"}},
    "Warrior": {1: {"Cloth", "Leather", "Mail", "Shield"}, 40: {"Cloth", "Leather", "Mail", "Plate", "Shield"}},
}

DUAL_WIELD_LEVEL = {
    "Hunter": 20,
    "Rogue": 10,
    "Warrior": 20,
}

WEAPON_RECOMMENDATION_SLOTS = {"Main Hand", "Off Hand", "Two Hand", "One Hand", "Ranged", "Dual Wield"}

SPEC_WEAPON_STYLE_POLICIES = {
    ("Paladin", "Retribution"): "two_hand_best_overall",
    ("Warrior", "Arms"): "two_hand_best_overall",
    ("Warrior", "Fury"): "dual_wield_after_access",
    ("Rogue", "Assassination"): "dual_wield_after_access",
    ("Rogue", "Combat"): "dual_wield_after_access",
    ("Rogue", "Subtlety"): "dual_wield_after_access",
    ("Shaman", "Enhancement"): "dual_wield_after_access",
    ("Paladin", "Protection"): "shield_tank",
    ("Warrior", "Protection"): "shield_tank",
    ("Druid", "Feral dps"): "feral",
    ("Druid", "Feral tank"): "feral",
}

EXPERTISE_RATING_PER_EXPERTISE = 3.94

RAID_SOURCE_ZONES = {
    "Molten Core",
    "Blackwing Lair",
    "Zul'Gurub",
    "Ruins of Ahn'Qiraj",
    "Ahn'Qiraj",
    "Naxxramas",
    "Karazhan",
    "Gruul's Lair",
    "Magtheridon's Lair",
    "Serpentshrine Cavern",
    "Tempest Keep",
    "Hyjal Summit",
    "Black Temple",
    "Zul'Aman",
    "Sunwell Plateau",
}

CLASSIC_RAID_QUEST_MARKERS = (
    "blessed qiraji",
    "imperial qiraji",
    "dreadnaught",
    "redemption",
    "cryptstalker",
    "earthshatter",
    "dreamwalker",
    "bonescythe",
    "frostfire",
    "plagueheart",
    "garb of faith",
    "ring of the dreadnaught",
    "ring of redemption",
    "ring of the cryptstalker",
    "ring of the earthshatterer",
    "ring of the dreamwalker",
    "bonescythe ring",
    "frostfire ring",
    "plagueheart ring",
    "ring of faith",
)

PROFESSION_GATE_TYPES = {"profession", "profession_specialization", "recipe_known"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def level_band_for_level(level: int) -> str:
    level = max(1, min(MAX_LEVELING_LEVEL, int(level)))
    for band, minimum, maximum in LEVEL_BANDS:
        if minimum <= level <= maximum:
            return band
    return "58-69"


def level_bounds_for_band(level_band: str) -> tuple[int, int]:
    for band, minimum, maximum in LEVEL_BANDS:
        if band == level_band:
            return minimum, maximum
    return 1, MAX_LEVELING_LEVEL


def recommendation_levels_for_band(item_stats: list[dict[str, Any]], level_band: str) -> list[int]:
    minimum, maximum = level_bounds_for_band(level_band)
    levels = {minimum, maximum}
    for item in item_stats:
        required_level = item.get("required_level")
        if isinstance(required_level, int) and minimum <= required_level <= maximum:
            levels.add(required_level)
    return sorted(levels)


def apply_recommendation_level_range(rows: list[dict[str, Any]], level_min: int, level_max: int) -> list[dict[str, Any]]:
    for row in rows:
        row["level_min"] = level_min
        row["level_max"] = level_max
        row["level_band"] = level_band_for_level(level_min)
    return rows


def normalized_slot(slot: str | None) -> str:
    aliases = {
        "Finger": "Ring",
        "Held In Off-hand": "Off Hand",
        "Held In Off Hand": "Off Hand",
        "One-Hand": "One Hand",
        "One Hand": "One Hand",
        "Two-Hand": "Two Hand",
        "Two Hand": "Two Hand",
        "Ranged Right": "Ranged",
    }
    return aliases.get(str(slot or "").strip(), str(slot or "").strip())


def slot_matches(item_slot: str | None, requested_slot: str | None) -> bool:
    item_slot = normalized_slot(item_slot)
    requested_slot = normalized_slot(requested_slot)
    if not item_slot or not requested_slot:
        return True
    if item_slot == requested_slot:
        return True
    if item_slot == "One Hand" and requested_slot in {"Main Hand", "Off Hand", "Dual Wield"}:
        return True
    if item_slot == "Two Hand" and requested_slot == "Two Hand":
        return True
    return False


def restrictions_allow(item: dict[str, Any], class_name: str, race: str) -> bool:
    restrictions = item.get("restrictions") if isinstance(item.get("restrictions"), dict) else {}
    classes = restrictions.get("classes")
    if isinstance(classes, list) and classes and class_name not in classes:
        return False
    races = restrictions.get("races")
    if isinstance(races, list) and races and race not in races:
        return False
    return True


def item_available_at(item: dict[str, Any], level: int) -> bool:
    required_level = item.get("required_level")
    return required_level is None or (isinstance(required_level, int) and required_level <= level)


def profile_role(scoring_profiles: dict[str, Any], class_name: str, spec_name: str) -> str:
    spec_roles = scoring_profiles.get("spec_roles") if isinstance(scoring_profiles.get("spec_roles"), dict) else {}
    return str(spec_roles.get(f"{class_name}/{spec_name}") or "physical_dps")


def profile_weights(scoring_profiles: dict[str, Any], class_name: str, spec_name: str, level: int, context: str) -> tuple[str, dict[str, float]]:
    role = profile_role(scoring_profiles, class_name, spec_name)
    role_defaults = scoring_profiles.get("role_defaults") if isinstance(scoring_profiles.get("role_defaults"), dict) else {}
    weights = {key: float(value) for key, value in (role_defaults.get(role) or {}).items() if isinstance(value, (int, float))}
    level_band = level_band_for_level(level)

    for profile in scoring_profiles.get("profiles", []):
        if (
            profile.get("class") == class_name
            and profile.get("spec") == spec_name
            and profile.get("level_band") == level_band
            and profile.get("context", "best_overall") == context
        ):
            for key, value in (profile.get("weights") or {}).items():
                if isinstance(value, (int, float)):
                    weights[key] = float(value)

    for key, value in SOURCE_BUCKET_MODIFIERS.get(context, {}).items():
        weights[key] = weights.get(key, 0.0) + value

    return role, weights


def source_bucket(item: dict[str, Any]) -> str:
    explicit = item.get("source_bucket")
    if explicit:
        return str(explicit)
    primary = item.get("primary_source") if isinstance(item.get("primary_source"), dict) else {}
    source_type = primary.get("type")
    content_type = primary.get("content_type")
    if source_type == "drop":
        if content_type == "raid":
            return "raid_drop"
        if content_type == "heroic_dungeon":
            return "heroic_dungeon_drop"
        if content_type == "dungeon":
            return "dungeon_drop"
        return "other_drop"
    if source_type:
        return str(source_type)
    return "unknown"


def iter_sources(source: dict[str, Any] | None):
    if not isinstance(source, dict):
        return
    yield source
    for key in ["token_sources", "quest_starter_sources", "recipe_sources"]:
        for nested_source in source.get(key) or []:
            yield from iter_sources(nested_source)


def item_sources(item: dict[str, Any]):
    primary = item.get("primary_source") if isinstance(item.get("primary_source"), dict) else None
    yield from iter_sources(primary)
    for source in item.get("sources") or []:
        yield from iter_sources(source)


def source_is_raid_gated(source: dict[str, Any]) -> bool:
    if source.get("content_type") == "raid":
        return True
    zone = source.get("zone")
    return isinstance(zone, str) and zone in RAID_SOURCE_ZONES


def item_has_raid_gated_source(item: dict[str, Any]) -> bool:
    return any(source_is_raid_gated(source) for source in item_sources(item))


def item_looks_like_classic_raid_quest_reward(item: dict[str, Any]) -> bool:
    if source_bucket(item) != "quest":
        return False
    text_parts = [item.get("name"), item.get("source_summary")]
    primary = item.get("primary_source") if isinstance(item.get("primary_source"), dict) else {}
    text_parts.append(primary.get("entity_name"))
    text = " ".join(str(part or "") for part in text_parts).lower()
    return any(marker in text for marker in CLASSIC_RAID_QUEST_MARKERS)


def iter_requirements(source_or_item: dict[str, Any]):
    for requirement in source_or_item.get("requirements") or []:
        if isinstance(requirement, dict):
            yield requirement
    for source in item_sources(source_or_item):
        for requirement in source.get("requirements") or []:
            if isinstance(requirement, dict):
                yield requirement


def is_tradeable(item: dict[str, Any]) -> bool:
    return item.get("boe") is True or item.get("binding") == "bind_on_equip"


def item_has_leveling_profession_gate(item: dict[str, Any]) -> bool:
    tradeable = is_tradeable(item)
    for requirement in iter_requirements(item):
        if requirement.get("type") not in PROFESSION_GATE_TYPES:
            continue
        scope = requirement.get("scope")
        if scope == "equip_or_use":
            return True
        if not tradeable:
            return True
    return False


def class_can_use_item(item: dict[str, Any], class_name: str) -> bool:
    subtype = item.get("weapon_subtype")
    if not subtype:
        return True
    allowed = CLASS_WEAPON_SUBTYPES.get(class_name)
    if not allowed:
        return True
    return str(subtype) in allowed


def relic_type_for_item(item: dict[str, Any]) -> str | None:
    if normalized_slot(item.get("slot")) != "Relic":
        return None
    name = str(item.get("name") or "").lower()
    for relic_type, tokens in RELIC_TYPE_TOKENS.items():
        if any(token in name for token in tokens):
            return relic_type
    return None


def class_can_use_ammo(class_name: str) -> bool:
    ammo_subtypes = CLASS_RANGED_AMMO_SUBTYPES.get(class_name, set())
    weapon_subtypes = CLASS_WEAPON_SUBTYPES.get(class_name, set())
    return bool(ammo_subtypes & weapon_subtypes)


def class_can_use_equipment_slot(item: dict[str, Any], class_name: str) -> bool:
    slot = normalized_slot(item.get("slot"))
    if slot == "Ammo":
        return class_can_use_ammo(class_name)
    if slot == "Quiver":
        return class_name == "Hunter"
    if slot == "Relic":
        relic_type = relic_type_for_item(item)
        return relic_type in CLASS_RELIC_ARMOR_TYPES.get(class_name, set())
    return True


def class_armor_allowed(class_name: str, level: int) -> set[str]:
    tiers = CLASS_ARMOR_PROFICIENCIES.get(class_name, {1: set()})
    allowed: set[str] = set()
    for required_level, armor_types in tiers.items():
        if level >= required_level:
            allowed = set(armor_types)
    return allowed


def class_can_dual_wield(class_name: str, spec_name: str, level: int) -> bool:
    if class_name == "Shaman":
        return spec_name == "Enhancement" and level >= 40
    required_level = DUAL_WIELD_LEVEL.get(class_name)
    return required_level is not None and level >= required_level


def class_can_use_armor(item: dict[str, Any], class_name: str, level: int) -> bool:
    armor_type = item.get("armor_type")
    if not armor_type:
        return True
    if armor_type == "Shield" and normalized_slot(item.get("slot")) != "Off Hand":
        return False
    return str(armor_type) in class_armor_allowed(class_name, level)


def slot_is_legal_for_class(item: dict[str, Any], class_name: str, spec_name: str, level: int, requested_slot: str) -> bool:
    item_slot = normalized_slot(item.get("slot"))
    requested_slot = normalized_slot(requested_slot)
    if requested_slot == "Off Hand" and item_slot == "One Hand":
        return class_can_dual_wield(class_name, spec_name, level)
    if requested_slot == "Off Hand" and item.get("armor_type") == "Shield":
        return "Shield" in class_armor_allowed(class_name, level)
    return True


def item_weapon_style(item: dict[str, Any]) -> str:
    item_slot = normalized_slot(item.get("slot"))
    weapon_type = normalized_slot(item.get("weapon_type"))
    if item_slot == "Off Hand" and not item.get("weapon_subtype"):
        return ""
    if weapon_type in {"One Hand", "Two Hand", "Ranged"}:
        return weapon_type
    if weapon_type == "Main Hand":
        return "One Hand"
    if item_slot in {"One Hand", "Main Hand"} and item.get("weapon_subtype"):
        return "One Hand"
    if item_slot == "Off Hand" and item.get("weapon_subtype") and item.get("armor_type") != "Shield":
        return "One Hand"
    if item_slot in {"Two Hand", "Ranged"}:
        return item_slot
    return ""


def weapon_style_allowed(
    item: dict[str, Any],
    class_name: str,
    spec_name: str,
    role: str,
    level: int,
    requested_slot: str,
    context: str,
) -> bool:
    requested_slot = normalized_slot(requested_slot)
    if requested_slot not in WEAPON_RECOMMENDATION_SLOTS:
        return True

    item_slot = normalized_slot(item.get("slot"))
    style = item_weapon_style(item)
    is_weapon = bool(style)
    is_shield = item.get("armor_type") == "Shield"
    can_dual_wield = class_can_dual_wield(class_name, spec_name, level)
    policy = SPEC_WEAPON_STYLE_POLICIES.get((class_name, spec_name))

    if requested_slot == "Ranged":
        return style == "Ranged" or item_slot == "Ranged"
    if style == "Ranged":
        return False

    if requested_slot == "Off Hand" and is_weapon:
        if style != "One Hand" or not can_dual_wield:
            return False

    if policy == "shield_tank":
        if requested_slot == "Off Hand":
            return is_shield
        if requested_slot == "Two Hand":
            return False
        if requested_slot in {"Main Hand", "One Hand", "Dual Wield"}:
            return is_weapon and style == "One Hand"

    if policy == "feral":
        if requested_slot == "Off Hand" and is_weapon:
            return False
        return True

    if context == "best_overall" and role == "physical_dps":
        if policy == "two_hand_best_overall":
            if requested_slot == "Off Hand":
                return False
            if requested_slot in {"Main Hand", "One Hand", "Dual Wield"} and style == "One Hand":
                return False
        elif policy == "dual_wield_after_access" and can_dual_wield:
            if requested_slot == "Two Hand" or style == "Two Hand":
                return False
            if requested_slot == "Off Hand":
                return is_weapon and style == "One Hand"
            if requested_slot in {"Main Hand", "One Hand", "Dual Wield"} and is_weapon:
                return style == "One Hand"

    return True


def recommendation_slots_for_item(item: dict[str, Any]) -> list[str]:
    slot = normalized_slot(item.get("slot"))
    if not slot:
        return []
    if slot == "One Hand":
        return ["Main Hand", "Off Hand"]
    return [slot]


def leveling_source_allowed(item: dict[str, Any], level: int) -> bool:
    if level > MAX_LEVELING_LEVEL:
        return True

    bucket = source_bucket(item)
    if bucket in {"raid_drop", "pvp"}:
        return False
    if item_has_raid_gated_source(item):
        return False
    if item_looks_like_classic_raid_quest_reward(item):
        return False
    if item_has_leveling_profession_gate(item):
        return False
    return True


def context_source_bonus(item: dict[str, Any], context: str) -> tuple[float, list[str]]:
    bucket = source_bucket(item)
    tags: list[str] = []
    if context == "boe" and item.get("boe") is True:
        return 8.0, ["boe"]
    if context == "dungeon" and bucket in {"dungeon_drop", "heroic_dungeon_drop"}:
        return 8.0, ["dungeon"]
    if context == "easy_source":
        if bucket in {"quest", "vendor", "crafted", "world_drop"}:
            return 6.0, ["best_easy_source"]
        if bucket == "raid_drop":
            return -8.0, []
    return 0.0, tags


def merged_stats(item: dict[str, Any]) -> dict[str, float]:
    stats: dict[str, float] = {}
    raw_stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    for key, value in raw_stats.items():
        if isinstance(value, (int, float)):
            stats[str(key)] = float(value)
    for key in ["dps", "armor"]:
        value = item.get(key)
        if isinstance(value, (int, float)):
            stats[key] = float(value)
    sockets = item.get("sockets")
    if isinstance(sockets, list) and sockets:
        stats["socket"] = float(len(sockets))
    return stats


def effective_stats(item: dict[str, Any], class_name: str, spec_name: str, role: str, requested_slot: str) -> dict[str, float]:
    stats = merged_stats(item)
    expertise_rating = stats.get("expertise_rating")
    if isinstance(expertise_rating, (int, float)):
        stats["expertise"] = stats.get("expertise", 0.0) + (float(expertise_rating) / EXPERTISE_RATING_PER_EXPERTISE)
    ranged_attack_power = stats.get("ranged_attack_power")
    if class_name == "Hunter" and normalized_slot(requested_slot) == "Ranged" and isinstance(ranged_attack_power, (int, float)):
        stats["attack_power"] = stats.get("attack_power", 0.0) + float(ranged_attack_power)
    if class_name == "Druid" and spec_name.lower().startswith("feral"):
        stats.pop("dps", None)
        for effect in item.get("effect_stats", []) or []:
            if not isinstance(effect, dict) or effect.get("type") != "form_only":
                continue
            for key, value in (effect.get("stats") or {}).items():
                if isinstance(value, (int, float)):
                    stats[str(key)] = float(stats.get(str(key), 0.0)) + float(value)
    return stats


def applies_match(applies: dict[str, Any], item: dict[str, Any], role: str) -> bool:
    weapon_subtypes = applies.get("weapon_subtypes")
    if isinstance(weapon_subtypes, list) and weapon_subtypes:
        item_subtype = item.get("weapon_subtype") or item.get("weapon_type")
        return any(str(subtype).lower() in str(item_subtype or "").lower() for subtype in weapon_subtypes)
    roles = applies.get("roles")
    if isinstance(roles, list) and roles and role not in roles:
        return False
    stats = applies.get("stats")
    if isinstance(stats, list) and stats:
        item_stats = merged_stats(item)
        return any(stat in item_stats for stat in stats)
    return True


def racial_score_bonus(
    item: dict[str, Any],
    race: str,
    role: str,
    weights: dict[str, float],
    racial_modifiers: dict[str, Any],
) -> tuple[float, list[str]]:
    score = 0.0
    tags: list[str] = []
    for racial in racial_modifiers.get("racial_modifiers", []):
        if racial.get("race") != race:
            continue
        if racial.get("type") != "numeric":
            if racial.get("type") == "contextual":
                tags.extend(str(tag) for tag in racial.get("tags", []) if tag)
            continue
        applies = racial.get("applies") if isinstance(racial.get("applies"), dict) else {}
        if not applies_match(applies, item, role):
            continue
        modifier = racial.get("modifier") if isinstance(racial.get("modifier"), dict) else {}
        stat = str(modifier.get("stat") or "")
        value = modifier.get("value")
        if not stat or not isinstance(value, (int, float)):
            continue
        weight = weights.get(stat, 0.0)
        if not weight:
            continue
        score += float(value) * weight
        tags.extend(str(tag) for tag in racial.get("tags", []) if tag)
    return score, tags


def candidate_score(
    item: dict[str, Any],
    class_name: str,
    spec_name: str,
    race: str,
    level: int,
    slot: str,
    context: str,
    scoring_profiles: dict[str, Any],
    racial_modifiers: dict[str, Any],
) -> dict[str, Any] | None:
    level = max(1, min(MAX_LEVELING_LEVEL, int(level)))
    if not item_available_at(item, level):
        return None
    if not slot_matches(item.get("slot"), slot):
        return None
    if not class_can_use_equipment_slot(item, class_name):
        return None
    if not restrictions_allow(item, class_name, race):
        return None
    if not class_can_use_item(item, class_name):
        return None
    if not class_can_use_armor(item, class_name, level):
        return None
    if not slot_is_legal_for_class(item, class_name, spec_name, level, slot):
        return None
    if not leveling_source_allowed(item, level):
        return None

    role, weights = profile_weights(scoring_profiles, class_name, spec_name, level, context)
    if not weapon_style_allowed(item, class_name, spec_name, role, level, slot, context):
        return None

    stats = effective_stats(item, class_name, spec_name, role, slot)
    score = sum(stats.get(stat, 0.0) * weight for stat, weight in weights.items())
    racial_bonus, racial_tags = racial_score_bonus(item, race, role, weights, racial_modifiers)
    source_bonus, source_tags = context_source_bonus(item, context)
    score += racial_bonus + source_bonus

    reason_tags = ["best_overall" if context == "best_overall" else context]
    reason_tags.extend(racial_tags)
    reason_tags.extend(source_tags)
    if item.get("variant_id"):
        reason_tags.append("suffix_winner")

    return {
        "item": item,
        "score": round(score, 4),
        "reason_tags": sorted(dict.fromkeys(reason_tags)),
        "source_bucket": source_bucket(item),
        "role": role,
        "stats": stats,
        "weights": weights,
        "racial_bonus": round(racial_bonus, 4),
        "source_bonus": round(source_bonus, 4),
    }


def materialized_items(item_stats: list[dict[str, Any]], item_variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in item_stats if isinstance(item.get("id"), int)}
    items = [deepcopy(item) for item in item_stats]
    for variant in item_variants:
        item_id = variant.get("item_id")
        base = by_id.get(item_id)
        if not base:
            continue
        materialized = deepcopy(base)
        suffix_id = variant.get("random_suffix_id")
        materialized["variant_id"] = f"{item_id}:{suffix_id}"
        materialized["random_suffix_id"] = suffix_id
        materialized["suffix_name"] = variant.get("suffix_name")
        if variant.get("suffix_name"):
            materialized["name"] = f"{base.get('name', 'Item')} {variant['suffix_name']}"
        stats = deepcopy(base.get("stats") if isinstance(base.get("stats"), dict) else {})
        for key, value in (variant.get("stat_delta") or {}).items():
            if isinstance(value, (int, float)):
                stats[key] = float(stats.get(key, 0)) + float(value)
        for key, value in (variant.get("stats") or {}).items():
            if isinstance(value, (int, float)):
                stats[key] = float(value)
        materialized["stats"] = stats
        items.append(materialized)
    return items


def select_recommendations(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = sorted(scored, key=lambda row: (-row["score"], row["item"].get("name") or "", row["item"].get("id") or 0))
    if not scored:
        return []
    top_score = scored[0]["score"]
    selected: list[dict[str, Any]] = []
    for index, row in enumerate(scored):
        within_five_percent = top_score <= 0 or row["score"] >= top_score * 0.95
        if index < 3 or within_five_percent:
            selected.append(row)
    return selected


def recommendation_rows_for(
    item_stats_doc: dict[str, Any],
    item_variants_doc: dict[str, Any],
    racial_modifiers_doc: dict[str, Any],
    scoring_profiles_doc: dict[str, Any],
    *,
    class_name: str,
    spec_name: str,
    race: str,
    level: int,
    slot: str,
    context: str = "best_overall",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = materialized_items(item_stats_doc.get("item_stats", []), item_variants_doc.get("item_variants", []))
    return recommendation_rows_for_items(
        items,
        racial_modifiers_doc,
        scoring_profiles_doc,
        class_name=class_name,
        spec_name=spec_name,
        race=race,
        level=level,
        slot=slot,
        context=context,
    )


def recommendation_rows_for_items(
    items: list[dict[str, Any]],
    racial_modifiers_doc: dict[str, Any],
    scoring_profiles_doc: dict[str, Any],
    *,
    class_name: str,
    spec_name: str,
    race: str,
    level: int,
    slot: str,
    context: str = "best_overall",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    level = max(1, min(MAX_LEVELING_LEVEL, int(level)))
    candidates = []
    audit_rows = []
    for item in items:
        scored = candidate_score(item, class_name, spec_name, race, level, slot, context, scoring_profiles_doc, racial_modifiers_doc)
        if not scored:
            continue
        candidates.append(scored)
        audit_rows.append(
            {
                "class": class_name,
                "spec": spec_name,
                "race": race,
                "level": level,
                "slot": slot,
                "context": context,
                "item_id": item.get("id"),
                "variant_id": item.get("variant_id"),
                "name": item.get("name"),
                "score": scored["score"],
                "racial_bonus": scored["racial_bonus"],
                "source_bonus": scored["source_bonus"],
                "reason_tags": scored["reason_tags"],
            }
        )

    selected = select_recommendations(candidates)
    top_score = selected[0]["score"] if selected else 0.0
    level_band = level_band_for_level(level)
    level_min, level_max = level_bounds_for_band(level_band)
    rows = []
    for rank, scored in enumerate(selected, start=1):
        item = scored["item"]
        score_delta_pct = 0.0 if not top_score else round(((top_score - scored["score"]) / top_score) * 100, 3)
        reason_tags = list(scored["reason_tags"])
        if rank > 1 and score_delta_pct <= 5:
            reason_tags.append("near_equivalent")
        if race != "*" and any(tag.startswith(race.lower().replace(" ", "_")) or tag.startswith("human_") for tag in reason_tags):
            reason_tags.append(f"best_for_{race.lower().replace(' ', '_')}")
        rows.append(
            {
                "class": class_name,
                "spec": spec_name,
                "race": race,
                "level_min": level_min,
                "level_max": level_max,
                "level_band": level_band,
                "slot": slot,
                "item_id": item["id"],
                "variant_id": item.get("variant_id"),
                "rank": rank,
                "context": context,
                "source_bucket": scored["source_bucket"],
                "score": scored["score"],
                "score_delta_pct": score_delta_pct,
                "reason_tags": sorted(dict.fromkeys(reason_tags)),
                "source_summary": item.get("source_summary", ""),
                "source_url": item.get("wowhead_url") or item.get("source_url"),
            }
        )
    return rows, audit_rows


def recommendation_selection_signature(rows: list[dict[str, Any]]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (row.get("rank"), row.get("item_id"), row.get("variant_id"), row.get("source_bucket"))
        for row in rows
    )


def rows_have_numeric_racial_tags(rows: list[dict[str, Any]], race: str) -> bool:
    prefixes = RACE_TAG_PREFIXES.get(race, ())
    if not prefixes:
        return False
    for row in rows:
        for tag in row.get("reason_tags", []):
            if any(str(tag).startswith(prefix) for prefix in prefixes):
                return True
    return False


def recommendation_audit_rows(rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    audit_rows: list[dict[str, Any]] = []
    for row in rows:
        audit_rows.append(
            {
                "class": row.get("class"),
                "spec": row.get("spec"),
                "race": row.get("race"),
                "level_band": row.get("level_band"),
                "slot": row.get("slot"),
                "context": row.get("context"),
                "item_id": row.get("item_id"),
                "variant_id": row.get("variant_id"),
                "rank": row.get("rank"),
                "score": row.get("score"),
                "score_delta_pct": row.get("score_delta_pct"),
                "reason_tags": row.get("reason_tags", []),
                "scope": scope,
            }
        )
    return audit_rows


def recommendation_compaction_signature(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    ignored = {"level_min", "level_max"}
    return tuple((key, repr(row.get(key))) for key in sorted(row) if key not in ignored)


def compact_adjacent_recommendation_ranges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted_by_signature: dict[tuple[tuple[str, str], ...], list[dict[str, Any]]] = {}
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            recommendation_compaction_signature(row),
            int(row.get("level_min") or 0),
            int(row.get("level_max") or 0),
        ),
    )
    for row in sorted_rows:
        signature = recommendation_compaction_signature(row)
        bucket = compacted_by_signature.setdefault(signature, [])
        level_min = row.get("level_min")
        level_max = row.get("level_max")
        if (
            bucket
            and isinstance(level_min, int)
            and isinstance(level_max, int)
            and isinstance(bucket[-1].get("level_max"), int)
            and level_min == int(bucket[-1]["level_max"]) + 1
        ):
            bucket[-1]["level_max"] = level_max
            continue
        bucket.append(deepcopy(row))

    compacted = [row for bucket in compacted_by_signature.values() for row in bucket]
    return sorted(
        compacted,
        key=lambda row: (
            str(row.get("class") or ""),
            str(row.get("spec") or ""),
            int(row.get("level_min") or 0),
            str(row.get("slot") or ""),
            str(row.get("context") or ""),
            str(row.get("race") or ""),
            int(row.get("rank") or 0),
            int(row.get("item_id") or 0),
            str(row.get("variant_id") or ""),
        ),
    )


def build_recommendation_documents(
    item_stats_doc: dict[str, Any],
    item_variants_doc: dict[str, Any],
    racial_modifiers_doc: dict[str, Any],
    scoring_profiles_doc: dict[str, Any],
) -> dict[str, Any]:
    item_stats = item_stats_doc.get("item_stats", [])
    items = materialized_items(item_stats, item_variants_doc.get("item_variants", []))
    slots = sorted({slot for item in item_stats for slot in recommendation_slots_for_item(item)})
    items_by_slot = {
        slot: [item for item in items if slot_matches(item.get("slot"), slot)]
        for slot in slots
    }
    contexts = scoring_profiles_doc.get("runtime_contexts") if isinstance(scoring_profiles_doc.get("runtime_contexts"), list) else ["best_overall"]
    spec_roles = scoring_profiles_doc.get("spec_roles") if isinstance(scoring_profiles_doc.get("spec_roles"), dict) else {}
    recommendations: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for spec_key in sorted(spec_roles):
        class_name, _, spec_name = spec_key.partition("/")
        if not class_name or not spec_name:
            continue
        for level_band, _minimum, maximum in LEVEL_BANDS:
            checkpoint_levels = recommendation_levels_for_band(item_stats, level_band)
            for slot in slots:
                class_slot_items = [
                    item
                    for item in items_by_slot[slot]
                    if class_can_use_item(item, class_name)
                    and class_can_use_equipment_slot(item, class_name)
                ]
                for context in contexts:
                    for index, checkpoint_level in enumerate(checkpoint_levels):
                        level_max = checkpoint_levels[index + 1] - 1 if index + 1 < len(checkpoint_levels) else maximum
                        if level_max < checkpoint_level:
                            continue
                        checkpoint_items = [
                            item
                            for item in class_slot_items
                            if item_available_at(item, checkpoint_level)
                            and leveling_source_allowed(item, checkpoint_level)
                        ]
                        baseline_rows, _baseline_audit = recommendation_rows_for_items(
                            checkpoint_items,
                            racial_modifiers_doc,
                            scoring_profiles_doc,
                            class_name=class_name,
                            spec_name=spec_name,
                            race="*",
                            level=checkpoint_level,
                            slot=slot,
                            context=str(context),
                        )
                        apply_recommendation_level_range(baseline_rows, checkpoint_level, level_max)
                        recommendations.extend(baseline_rows)
                        audit_rows.extend(recommendation_audit_rows(baseline_rows, "baseline"))
                        baseline_signature = recommendation_selection_signature(baseline_rows)

                        for race in TBC_RACES:
                            rows, _audit = recommendation_rows_for_items(
                                checkpoint_items,
                                racial_modifiers_doc,
                                scoring_profiles_doc,
                                class_name=class_name,
                                spec_name=spec_name,
                                race=race,
                                level=checkpoint_level,
                                slot=slot,
                                context=str(context),
                            )
                            apply_recommendation_level_range(rows, checkpoint_level, level_max)
                            if recommendation_selection_signature(rows) == baseline_signature and not rows_have_numeric_racial_tags(rows, race):
                                continue
                            recommendations.extend(rows)
                            audit_rows.extend(recommendation_audit_rows(rows, "race_override"))

    compacted_recommendations = compact_adjacent_recommendation_ranges(recommendations)
    return {
        "leveling_recommendations": compacted_recommendations,
        "recommendation_audit": {
            "generated_at": now_utc(),
            "rows": audit_rows,
            "summary": {
                "candidates": len(audit_rows),
                "recommendations": len(compacted_recommendations),
                "uncompacted_recommendations": len(recommendations),
                "item_stats": len(item_stats),
            },
        },
    }
