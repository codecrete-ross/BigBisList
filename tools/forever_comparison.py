"""Build the item facts and reference profiles used by Forever stat ranks."""
from __future__ import annotations

import re

from tools.forever import item_conflicts, item_observations, numeric, scoring_profiles, snapshot_digest, valid_source
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
    "quality", "stats_unavailable", "roll_group", "roll_budget", "roll_armor", "roll_complete", "race_ids",
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


def reviewed_source_items(review: dict, inventory: dict) -> list[dict]:
    equipment = {row[0]: dict(zip(inventory["fields"], row)) for row in inventory["items"]}
    by_item = {}
    for route in review["routes"]:
        source = {**route["source"], "attribution": review["attribution"]}
        if not valid_source(source) or not route["corroboration_url"].startswith("https://"):
            raise ValueError(f"Invalid Forever acquisition review: {route}")
        for identifier in route["item_ids"]:
            if identifier not in equipment or source in by_item.get(identifier, []):
                raise ValueError(f"Invalid Forever route for item {identifier}")
            by_item.setdefault(identifier, []).append(source)
    return [{"id": identifier, "name": equipment[identifier]["name"], "quality": equipment[identifier]["quality"],
             "inventory_slot": equipment[identifier]["slot"], "binding": review["binding"], "boe": False,
             "wowhead_url": f"https://www.wowhead.com/forever/item={identifier}", "acquisition_phase": "PR",
             "primary_source": sources[0], "sources": sources, "source_summary": summarize_sources(sources)}
            for identifier, sources in sorted(by_item.items())]


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
    for key in ("armor_type", "weapon_subtype", "max_equipped", "unique_group", "variant_id", "requires_dual_wield", "variant_link"):
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
    catalog = dataset_json("forever", "guide_equipment")
    for row in catalog["items"]:
        base = dict(zip(catalog["fields"], row))
        key = str(base["id"])
        item = items.setdefault(key, {"stats_unavailable": True})
        for field in ("id", "name", "slot", "level", "armor_type", "weapon_subtype", "classes", "race_ids", "quality"):
            if base.get(field) is not None:
                item.setdefault(field, base[field])
        if base.get("group"):
            item["has_random_stats"] = True
            item.update(roll_group=base["group"], roll_budget=base.get("budget"),
                        roll_armor=base.get("armor"), roll_complete=base.get("roll_complete"))
    variant_links = {key: item["variant_link"] for key, item in items.items() if item.get("variant_link")}
    packed = {}
    for key, item in items.items():
        row = [item.get(field) for field in ITEM_FIELDS]
        while row[-1] is None:
            row.pop()
        packed[key] = row
    return {
        "version": VERSION,
        "roll_build": int(catalog["client_build"].split(".")[-1]),
        "roll_templates": catalog["templates"],
        "roll_groups": catalog["groups"],
        "flat_passive_stats": [list(rule) for rule in FLAT_PASSIVE_STATS],
        "profiles": profiles,
        "guide_effects": guide_effects,
        "equipment": rules["class_equipment"],
        "common_slots": rules["common_slots"],
        "feral_uses_weapon_dps": rules["feral_uses_weapon_dps"],
        "item_fields": list(ITEM_FIELDS),
        **({"variant_links": variant_links} if variant_links else {}),
        "items": packed,
    }


def reference_profiles(rules: dict, *, leveling: dict | None = None, model: dict | None = None) -> dict:
    leveling = leveling or dataset_json("forever", "leveling_scoring_profiles")
    raid = scoring_profiles()
    model = model or dataset_json("forever", "scoring_model")
    profiles = {}
    for profile in raid["profiles"]:
        class_name, spec = profile["class"], profile["spec"]
        key = f"{class_name}/{spec}"
        settings = model["profiles"][key]
        common = settings.get("weights", {})
        scenarios = settings.get("scenario_overrides", {})
        weights = [
            [low, high, {**profile_weights(leveling, class_name, spec, low, "best_overall", rules=rules)[1],
                         **common, **scenarios.get("leveling", {}).get("weights", {})}]
            for _, low, high in rules["level_bands"]
        ]
        raid_weights = {**raid["role_weights"][profile["role"]], **profile.get("weights", {}), **common,
                        **scenarios.get("pre_raid", {}).get("weights", {})}
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
