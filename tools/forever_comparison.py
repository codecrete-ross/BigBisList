"""Build the item facts and reference profiles used by Forever stat ranks."""
from __future__ import annotations

import re

from tools.forever import item_conflicts, item_observations, numeric, scoring_profiles, snapshot_digest
from tools.project import SLOT_NAMES, dataset_json
from tools.recommend_leveling import materialized_items, merged_stats, normalized_slot, profile_weights, separate_weapon_dps


VERSION = "forever-stat-ranks-1"
ARMOR_SLOTS = {"Head", "Shoulder", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet"}
RANKED_SLOTS = (SLOT_NAMES | {"One Hand"}) - {"Dual Wield", "Ammo", "Quiver"}
ITEM_FIELDS = (
    "id", "name", "slot", "level", "stats", "armor_type", "weapon_subtype",
    "classes", "races", "max_equipped", "unique_group", "effects", "utility",
    "variant_id", "has_random_stats", "requires_dual_wield", "excluded",
)
TOOLTIP_CONFIDENCE = {"tooltip", "tooltip_endpoint", "observed_tooltip"}


def comparison_facts(item: dict, description: str = "") -> dict | None:
    slot = normalized_slot(item.get("slot"))
    identifier, name = item.get("id"), item.get("name")
    if slot not in RANKED_SLOTS or type(identifier) is not int or identifier <= 0 or not name:
        return None
    level = item.get("required_level")
    if level is not None and (type(level) is not int or not 0 <= level <= 60):
        return None
    if slot in ARMOR_SLOTS and not item.get("armor_type"):
        return None
    weapon = item.get("weapon_subtype")
    if (slot in {"One Hand", "Main Hand", "Two Hand", "Ranged"} or item.get("dps")) and not weapon:
        return None
    if not isinstance(item.get("stats", {}), dict) or not all(map(numeric, item.get("stats", {}).values())):
        return None
    if any(item.get(field) is not None and not numeric(item[field]) for field in ("armor", "dps", "weapon_speed")):
        return None

    stats = merged_stats(item)
    stats.pop("socket", None)
    if numeric(item.get("weapon_speed")):
        stats["weapon_speed"] = item["weapon_speed"]
    separate_weapon_dps(item, stats)
    if not all(map(numeric, stats.values())):
        return None
    modeled_effects, effects = set(), []
    for effect in item.get("effect_stats", []):
        label = effect.get("raw_text")
        if label and effect.get("type") == "passive" and effect.get("stats"):
            modeled_effects.add(label)
        elif label:
            effects.append(label)
    effects.extend(label for label in item.get("equip_effects", []) + item.get("use_effects", [])
                   if isinstance(label, str) and label not in modeled_effects)
    if item.get("set_bonuses"):
        effects.append("Set bonuses")
    effects = list(dict.fromkeys(effects))
    if not stats and not effects:
        return None
    utility = not stats and bool(effects) and all(
        re.fullmatch(r"(?:Equip:\s*)?Increases mount speed by \d+%\.?", effect, re.IGNORECASE) for effect in effects
    )

    facts = {"id": identifier, "name": name, "slot": slot, "stats": stats}
    if level is not None:
        facts["level"] = level
    if effects:
        facts["effects"] = effects
    if utility:
        facts["utility"] = True
    if item.get("recommendation_excluded"):
        facts["excluded"] = True
    for key in ("armor_type", "weapon_subtype", "max_equipped", "unique_group", "variant_id", "requires_dual_wield"):
        if item.get(key) is not None:
            facts[key] = item[key]
    for key in ("classes", "races"):
        if item.get("restrictions", {}).get(key):
            facts[key] = sorted(set(item["restrictions"][key]))

    unique = re.search(r"\bUnique[- ]Equipped\s*:\s*([^()\r\n<]+?)\s*\((\d+)\)", description, re.IGNORECASE)
    if unique:
        facts.setdefault("unique_group", unique[1].strip())
        facts.setdefault("max_equipped", int(unique[2]))
    elif re.search(r"\bUnique(?:[- ]Equipped)?\b", description, re.IGNORECASE):
        facts.setdefault("max_equipped", 1)
    if item.get("variant_only") or re.search(r"\bRandom Enchantment\b", description, re.IGNORECASE):
        facts["has_random_stats"] = True
    return facts


def comparison_document(snapshots: dict[str, dict]) -> dict:
    conflicts = item_conflicts(snapshots)
    rows = []
    digests = {}
    build = dataset_json("forever", "leveling_rules")["review"]["client_build"]
    for identifier, observations in item_observations(snapshots).items():
        if identifier in conflicts:
            continue
        for observed in observations:
            item = observed.get("item_stats", {})
            confidence = item.get("parse_confidence")
            source = snapshots[observed["evidence_url"]]
            if item.get("id") != identifier or observed.get("item_kind") != "equipment" or confidence not in TOOLTIP_CONFIDENCE:
                continue
            if confidence == "observed_tooltip" and source.get("client_build") != build:
                continue
            facts = comparison_facts(item, observed.get("description") or "")
            if facts is None:
                continue
            # A missing level can identify an effect on an owned link. Numeric
            # catalog candidates need a known equip level.
            if facts.get("level") is None and facts["stats"]:
                continue
            url = observed["evidence_url"]
            if url not in digests:
                digests[url] = snapshot_digest(source)
            rows.append({**facts, "evidence": {"url": url, "digest": digests[url]}})
            break
    return {"version": VERSION, "items": sorted(rows, key=lambda row: row["id"])}


def compile_comparison_data(item_stats: list[dict]) -> dict:
    data = dataset_json("forever", "comparison_item_stats")
    if data["version"] != VERSION:
        raise ValueError("Unexpected Forever comparison catalog version")
    items = {str(item["id"]): item for item in data["items"]}
    variants = dataset_json("forever", "item_variants")["item_variants"]
    for item in materialized_items(item_stats, variants):
        facts = comparison_facts(item)
        key = item.get("variant_id") or str(item["id"])
        if facts:
            inherited = items.get(str(item["id"]), {})
            # Preserve tooltip-only restrictions when an independently reviewed
            # item record omits them.
            for field in ("unique_group", "max_equipped", "has_random_stats"):
                if field in inherited and field not in facts:
                    facts[field] = inherited[field]
            if item.get("variant_id"):
                facts.pop("has_random_stats", None)
            items[key] = facts
        else:
            items.pop(key, None)

    rules = dataset_json("forever", "leveling_rules")
    leveling = dataset_json("forever", "leveling_scoring_profiles")
    raid = scoring_profiles()
    profiles = {}
    for profile in raid["profiles"]:
        class_name, spec = profile["class"], profile["spec"]
        key = f"{class_name}/{spec}"
        weights = [
            [low, high, profile_weights(leveling, class_name, spec, low, "best_overall", rules=rules)[1]]
            for _, low, high in rules["level_bands"]
        ]
        profiles[key] = {
            "leveling": {**rules["spec_policies"][key], "weights": weights},
            "pre_raid": {
                **{field: profile[field] for field in (
                    "slots", "armor_types", "weapon_types", "two_hand_weapon_types",
                    "dual_wield", "require_shield", "slot_weapon_types",
                ) if field in profile},
                "weights": {**raid["role_weights"][profile["role"]], **profile.get("weights", {})},
            },
        }
    return {
        "version": VERSION,
        "profiles": profiles,
        "equipment": rules["class_equipment"],
        "common_slots": rules["common_slots"],
        "feral_uses_weapon_dps": rules["feral_uses_weapon_dps"],
        "item_fields": list(ITEM_FIELDS),
        "items": {key: [item.get(field) for field in ITEM_FIELDS] for key, item in items.items()},
    }
