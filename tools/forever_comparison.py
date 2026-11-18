"""Build the item facts and reference profiles used by Forever stat ranks."""
from __future__ import annotations

import re

from tools.forever import eligible, item_conflicts, item_observations, numeric, scoring_profiles, snapshot_digest, valid_source
from tools.forever_item_effects import FLAT_PASSIVE_STATS, attach_rules, effect_lines, recover_permanent_stats, unresolved_lines
from tools.project import SLOT_NAMES, dataset_json
from tools.recommend_leveling import materialized_items, merged_stats, normalized_slot, profile_weights, separate_weapon_dps
from tools.sources import summarize_sources


VERSION = "forever-stat-ranks-1"
ARMOR_SLOTS = {"Head", "Shoulder", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet"}
RANKED_SLOTS = (SLOT_NAMES | {"One Hand"}) - {"Dual Wield", "Ammo", "Quiver"}
ITEM_FIELDS = (
    "id", "name", "slot", "level", "stats", "armor_type", "weapon_subtype",
    "classes", "races", "max_equipped", "unique_group", "effects", "utility",
    "variant_id", "has_random_stats", "requires_dual_wield", "excluded", "effect_rules", "set_bonuses",
)
TOOLTIP_CONFIDENCE = {"tooltip", "tooltip_endpoint", "observed_tooltip"}

def normalized_item_stats(item: dict) -> dict:
    stats = merged_stats(item)
    recover_permanent_stats(stats, effect_lines(item))
    stats.pop("socket", None)
    separate_weapon_dps(item, stats)
    if numeric(item.get("weapon_speed")) and item["weapon_speed"] > 0:
        stats["weapon_speed"] = item["weapon_speed"]
    low, high = item.get("weapon_min_damage"), item.get("weapon_max_damage")
    if numeric(low) and numeric(high) and 0 <= low <= high:
        stats["weapon_min_damage"], stats["weapon_max_damage"] = low, high
    return stats


BUILD_SLOTS = {slot: {slot} for slot in ("Head", "Neck", "Shoulder", "Back", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet")}
BUILD_SLOTS.update({
    "Finger0": {"Ring"}, "Finger1": {"Ring"}, "Trinket0": {"Trinket"}, "Trinket1": {"Trinket"},
    "MainHand": {"Main Hand", "One Hand", "Two Hand"}, "OffHand": {"Off Hand", "One Hand"},
    "Ranged": {"Ranged", "Libram", "Idol", "Totem", "Relic"},
})


def reviewed_guide_items(reviewed: list[dict]) -> tuple[list[dict], list[dict]]:
    items, stats = [], []
    for row in reviewed:
        review, sources = row.get("review", {}), row.get("sources", [])
        if (not comparison_facts(row) or not re.fullmatch(r"1\.60\.\d+\.\d+", review.get("client_build", ""))
                or not review.get("tooltip_url", "").startswith("https://")
                or not review.get("route_url", "").startswith("https://")
                or not sources or not all(map(valid_source, sources))):
            raise ValueError(f"Invalid Forever guide item review for {row.get('id')}")
        item = {key: row[key] for key in ("id", "name", "quality", "binding", "boe", "wowhead_url")}
        source = sources[0]
        item.update(inventory_slot=row["slot"], acquisition_phase="PR", primary_source=source,
                    sources=sources, source_summary=summarize_sources(sources))
        items.append(item)
        stats.append({key: value for key, value in row.items() if key != "review"})
    return items, stats


def compile_reviewed_builds(builds: list[dict], catalog: dict, items: list[dict], stats: list[dict]) -> list[dict]:
    profiles = {(profile["class"], profile["spec"]): profile for profile in scoring_profiles()["profiles"]}
    sources = {item["id"]: item["sources"] for item in items if item.get("sources")}
    library = {str(item["id"]): item for item in stats}
    seen = set()
    for build in builds:
        name = build["id"]
        start, end = build["level_min"], build["level_max"]
        leveling = build["phase"] == "LEVELING"
        profile = profiles.get((build["class"], build["spec"]))
        if (not name or name in seen or not profile or build["faction"] not in {"Alliance", "Horde"}
                or (not (1 <= start <= end < 60) if leveling else (start != 60 or end != 60 or build["phase"] != "PR"))
                or not build["source_url"].startswith("https://") or set(build["slots"]) != set(BUILD_SLOTS)):
            raise ValueError(f"Invalid Forever build {name}")
        seen.add(name)
        limits = {}
        for position, key in build["slots"].items():
            if key == 0:
                continue
            fields = catalog["items"].get(key)
            if not fields:
                raise ValueError(f"Unknown variant {key} in Forever build {name}")
            facts = dict(zip(catalog["item_fields"], fields))
            slot, identifier = facts["slot"], facts["id"]
            original = library.get(str(identifier), {})
            equip_slot = ("Off Hand" if position == "OffHand" else "Main Hand") if slot == "One Hand" else slot
            if (not original or slot not in BUILD_SLOTS[position] or equip_slot not in profile["slots"] or facts["has_random_stats"]
                    or (facts["level"] is not None and facts["level"] > start)
                    or not eligible(original, profile, equip_slot, require_source=False)
                    or not any(source.get("side") in {None, "Both", build["faction"]} and valid_source(source)
                               for source in sources.get(identifier, []))):
                raise ValueError(f"Ineligible {position} {key} in Forever build {name}")
            if slot == "Two Hand" and build["slots"]["OffHand"] != 0:
                raise ValueError(f"Two-handed build {name} equips an off-hand")
            group = facts["unique_group"]
            limit = facts["max_equipped"] or (1 if group else None)
            if limit is not None:
                identity = group.casefold() if group else identifier
                copies, cap = limits.get(identity, (0, limit))
                limits[identity] = (copies + 1, min(cap, limit))
        if any(copies > cap for copies, cap in limits.values()):
            raise ValueError(f"Unique-equip limit exceeded in Forever build {name}")
    return builds


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

    stats = normalized_item_stats(item)
    if not all(map(numeric, stats.values())):
        return None
    effects = unresolved_lines(item)
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
            # Effect-bearing items can still give context to an owned link.
            # The runtime checks the equip level before including a candidate.
            if facts.get("level") is None and facts["stats"] and not facts.get("effects"):
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
    items = {}
    for item in data["items"]:
        facts = {**item, "stats": dict(item["stats"])}
        recover_permanent_stats(facts["stats"], effect_lines(item))
        if "effects" in facts:
            facts["effects"] = unresolved_lines(item)
        items[str(item["id"])] = facts
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
            if item.get("set_bonuses"):
                facts["set_bonuses"] = [{"pieces": bonus["pieces"], "spell_id": bonus.get("spell_id")}
                                        for bonus in item["set_bonuses"]]
            items[key] = facts
        else:
            items.pop(key, None)

    rules = dataset_json("forever", "leveling_rules")
    profiles = reference_profiles(rules)
    guide_effects, seen_reviews = {}, set()
    known_roles = {profile["role"] for profile in profiles.values()}
    for review in dataset_json("forever", "leveling_guide_effects")["effects"]:
        key = review["variant"]
        roles, specs = review.get("roles", []), review.get("specs", [])
        if (key in seen_reviews or not (roles or specs) or set(roles) - known_roles or set(specs) - profiles.keys()
                or not review["note"].strip()):
            raise ValueError(f"Invalid Forever Gear Guide effect review for {key}")
        seen_reviews.add(key)
        if key not in items:
            continue
        if review["effect"] not in items[key].get("effects", []):
            raise ValueError(f"Forever Gear Guide effect changed for {key}")
        guide_effects[key] = {field: review[field] for field in ("roles", "specs", "note") if field in review}
    for key, item in items.items():
        items[key] = item | attach_rules(item)
    return {
        "version": VERSION,
        "published_routes_only": True,
        "flat_passive_stats": [list(rule) for rule in FLAT_PASSIVE_STATS],
        "profiles": profiles,
        "guide_effects": guide_effects,
        "equipment": rules["class_equipment"],
        "common_slots": rules["common_slots"],
        "feral_uses_weapon_dps": rules["feral_uses_weapon_dps"],
        "item_fields": list(ITEM_FIELDS),
        "items": {key: [item.get(field) for field in ITEM_FIELDS] for key, item in items.items()},
    }


def reference_profiles(rules: dict, *, leveling: dict | None = None, model: dict | None = None) -> dict:
    leveling = leveling or dataset_json("forever", "leveling_scoring_profiles")
    raid = scoring_profiles()
    # Match the reviewed passive Intellect and spell coefficients in the Ret
    # pilot. Conditional talent operations stay in the loadout scorer.
    model = model or dataset_json("forever", "scoring_model")
    ret_weights = model["profiles"]["Paladin/Retribution"]["weights"]
    profiles = {}
    for profile in raid["profiles"]:
        class_name, spec = profile["class"], profile["spec"]
        key = f"{class_name}/{spec}"
        weight_overrides = ret_weights if key == "Paladin/Retribution" else {}
        weights = [
            [low, high, {**profile_weights(leveling, class_name, spec, low, "best_overall", rules=rules)[1],
                         **weight_overrides}]
            for _, low, high in rules["level_bands"]
        ]
        raid_weights = {**raid["role_weights"][profile["role"]], **profile.get("weights", {}), **weight_overrides}
        if key == "Druid/Feral tank":
            raid_weights["parry_percent"] = 0
        profiles[key] = {
            "role": profile["role"],
            "leveling": {**rules["spec_policies"][key], "weights": weights},
            "pre_raid": {
                **{field: profile[field] for field in (
                    "slots", "armor_types", "weapon_types", "two_hand_weapon_types",
                    "dual_wield", "require_shield", "slot_weapon_types",
                ) if field in profile},
                "weights": raid_weights,
            },
        }
    return profiles
