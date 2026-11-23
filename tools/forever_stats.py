"""Forever combat-rating units and marginal reference-stat calculations."""
from __future__ import annotations

# Forever's level-independent client gametable units. Keep source ratings until
# the scoring boundary, where tooltip percentages can take precedence once.
RATING_UNITS = {
    "hit_rating": ("hit_percent", 10), "crit_rating": ("crit_percent", 14),
    "haste_rating": ("haste_percent", 10), "expertise_rating": ("expertise", 10),
    "defense_rating": ("defense", 1), "dodge_rating": ("dodge_percent", 12),
    "parry_rating": ("parry_percent", 15), "block_rating": ("block_percent", 5),
    "spell_hit_rating": ("spell_hit_percent", 10), "spell_crit_rating": ("spell_crit_percent", 14),
    "spell_haste_rating": ("spell_haste_percent", 10),
    "melee_hit_rating": ("melee_hit_percent", 10), "ranged_hit_rating": ("ranged_hit_percent", 10),
    "melee_crit_rating": ("melee_crit_percent", 14), "ranged_crit_rating": ("ranged_crit_percent", 14),
    "melee_haste_rating": ("melee_haste_percent", 10), "ranged_haste_rating": ("ranged_haste_percent", 10),
}


def normalized_stats(stats: dict) -> dict:
    result = dict(stats)
    for rating, (stat, divisor) in RATING_UNITS.items():
        if rating in result:
            result.setdefault(stat, result.pop(rating) / divisor)
    return result


def marginal_points(amount: float, bonus: float, curve: list) -> float:
    total, previous = 0.0, 0.0
    for cap, share in curve:
        total += (max(0, min(amount + bonus, cap) - previous)
                  - max(0, min(bonus, cap) - previous)) * share
        previous = cap
    return total


def hit_points(stats: dict, curves: list, level: int, talents: dict | None = None) -> float:
    talents = talents or {}
    total = 0.0
    for curve in curves:
        general = stats.get("hit_percent", 0)
        channel = curve["channel"]
        amount = general + stats.get(channel + "_hit_percent", 0)
        if channel == "offhand":
            amount += stats.get("melee_hit_percent", 0)
        bonus = talents.get("hit_percent", 0) + talents.get(channel + "_hit_percent", 0)
        if channel == "offhand":
            bonus += talents.get("melee_hit_percent", 0)
        previous = 0
        for cap, share in curve["segments"]:
            # Leveling references fight same-level outdoor enemies. Pre-Raid
            # uses the documented level-63 target with fully trained skills.
            boundary = cap if level == 60 else (4 if channel == "spell" else 5) + max(0, cap - (17 if channel == "spell" else 8))
            total += (max(0, min(amount + bonus, boundary) - previous)
                      - max(0, min(bonus, boundary) - previous)) * share
            previous = boundary
    return total


def weight_review() -> dict:
    from tools.project import dataset_json
    return dataset_json("forever", "stat_weight_review")


def profile_scenario(name: str, mode: str) -> dict:
    review = weight_review()["profiles"][name]
    scenario = {"hit_curves": review["hit_curves"], "caps": {"expertise": review["expertise_cap"]}}
    scenario["expertise_curve"] = review["expertise_curve"] if mode == "pre_raid" else [[5, 1]]
    scenario["crit_shares"] = review["crit_shares"]
    if mode == "pre_raid":
        scenario["reference_ranks"] = review["reference_ranks"]
        scenario["reference_bonuses"] = review.get("reference_bonuses", {})
        # A published marginal hit coefficient already includes the reference
        # talents. Normalize the curve's initial slope at those passive ranks.
        # Fury's off-hand hit talent can already be beyond the specials cap.
        slope = round(hit_points({"hit_percent": .0001}, review["hit_curves"], 60,
                                 scenario["reference_bonuses"]) / .0001, 6)
        if slope <= 0:
            raise ValueError(f"No marginal hit channel remains in {name}'s reference")
        scenario["hit_curves"] = [{**curve, "segments": [[cap, share / slope] for cap, share in curve["segments"]]}
                                  for curve in review["hit_curves"]]
        if review.get("offhand_dps_factor"):
            scenario["offhand_dps_factor"] = review["offhand_dps_factor"]
        if review.get("alternative_weights"):
            scenario["weight_alternatives"] = review["alternative_weights"]
    return scenario


def reference_score(item: dict, weights: dict, scenario: dict, level: int = 60, *, slot: str | None = None) -> float:
    """Use the loadout scorer for editorial pools as well as the shipped Guide."""
    from tools.forever_scoring import swap_score
    from tools.forever_item_effects import attach_rules

    position = {"Main Hand": 16, "One Hand": 16, "Two Hand": 16, "Off Hand": 17,
                "Ranged": 18, "Trinket": 13}.get(slot or item.get("slot"), 1)
    facts = {**item, "stats": normalized_stats(item.get("stats", {})), "shield": item.get("armor_type") == "Shield"}
    if "effect_rules" not in facts:
        facts.update(attach_rules(item))
    for key in ("dps", "armor", "weapon_speed", "weapon_min_damage", "weapon_max_damage"):
        if isinstance(item.get(key), (int, float)):
            facts["stats"][key] = item[key]
    from tools.recommend_leveling import separate_weapon_dps
    separate_weapon_dps(item, facts["stats"])
    return round(swap_score({position: facts}, weights, [], {}, scenario,
                            race_id=scenario.get("reference_race_id"), level=level)[0], 6)


def reference_scenario(name: str, role: str, mode: str, catalog: dict, level: int = 60) -> dict:
    from tools.forever_effect_benchmarks import policy, preset
    from tools.forever_scoring import read_model
    from tools.project import dataset_json

    model, snapshot = read_model()
    settings = model["profiles"][name]
    actor = next(row for row in dataset_json("forever", "leveling_rules")["races"] if name.split("/")[0] in row["classes"])
    scenario = {**model["scenarios"][mode], **settings.get("scenario_overrides", {}).get(mode, {}), **profile_scenario(name, mode),
                "effect_benchmark": preset(role, mode, name),
                "racial_scaling": snapshot.get("racial_scaling", []), "reference_race_id": actor["id"],
                "crit_domain": "spell" if role in {"caster", "healer"} else "physical"}
    for low, identifier in policy()["reference_weapons"]:
        if low > level:
            break
        stats = catalog[str(identifier)]["stats"]
        scenario["isolated_swing_damage"] = (stats["weapon_min_damage"] + stats["weapon_max_damage"]) / 2
        scenario["isolated_swing_seconds"] = stats["weapon_speed"]
    return scenario
