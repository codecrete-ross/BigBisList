"""Compile the reviewed candidate pools and evaluate Forever gear swaps."""
from __future__ import annotations

from collections import defaultdict
import re
from pathlib import Path

from tools.forever import SOURCE_CHILDREN, digest, eligible, has_review, numeric, roster, scoring_profiles, valid_source
from tools.forever_comparison import normalized_item_stats, reference_profiles
from tools.forever_item_effects import VERSION as ITEM_EFFECT_VERSION, attach_rules
from tools.forever_leveling import eligibility_allows, eligible_item
from tools.forever_mechanics import snapshot_path
from tools.forever_sources import check_evidence_refs, evidence_index, evidence_ref, source_provider
from tools.project import FOREVER_CANONICAL_DIR, dataset_json, load_json
from tools.recommend_leveling import materialized_items, slot_matches


VERSION = "forever-character-scoring-1"
MODES = ("leveling", "pre_raid")
SCENARIO_FIELDS = {"weights", "caps", "conversions", "evidence", "terrain", "target_family",
                   "effect_expectations", "effect_state_observations"}
EFFECT_METRICS = {"per_minute", "uses", "seconds", "events_per_minute", "uptime", "useful_fraction",
                  "target_fraction", "mana_per_minute", "damage_factor", "weapon_slot", "cooldown_model",
                  "applicable", "evidence", "use_signature"}


def scenario_effect_inputs(settings: dict, items: dict, name: str) -> dict:
    expectations = settings.get("effect_expectations", {})
    exact_rules = set()
    for key, item_expectations in expectations.items():
        item = items.get(key)
        rules = {rule["key"]: rule for rule in attach_rules(item or {}).get("effect_rules", [])}
        for rule_id, observed in item_expectations.items():
            rule = rules.get(rule_id)
            if not rule or set(observed) - EFFECT_METRICS or not observed.get("evidence"):
                raise ValueError(f"Missing exact item effect or observation provenance for {name}/{key}/{rule_id}")
            if ("applicable" in observed and type(observed["applicable"]) is not bool
                    or observed.get("cooldown_model") not in {None, "poisson"}
                    or observed.get("weapon_slot", 16) not in {16, 17}
                    or ("uses" in observed and (not numeric(observed.get("seconds")) or observed["seconds"] <= 0))
                    or ("use_signature" in observed and not isinstance(observed["use_signature"], str))):
                raise ValueError(f"Invalid item effect observation for {name}/{key}/{rule_id}")
            for metric, value in observed.items():
                if metric not in {"cooldown_model", "applicable", "evidence", "use_signature"}:
                    if not numeric(value) or value < 0 or (metric in {"uptime", "useful_fraction", "target_fraction"} and value > 1):
                        raise ValueError(f"Invalid {metric} for {name}/{key}/{rule_id}")
            if rule["kind"] == "timed_stats":
                exact_rules.add((key, rule_id))

    states = settings.get("effect_state_observations", {})
    for signature, combinations in states.items():
        effects = signature.split("|")
        if effects != sorted(set(effects)) or len(effects) < 2 or not settings.get("evidence"):
            raise ValueError(f"Invalid joint item effect scope for {name}")
        if not all(re.fullmatch(r"(?:[1-9]|1[0-8]):[^|]+:[a-f0-9]{16}", key)
                   and tuple(key.partition(":")[2].rsplit(":", 1)) in exact_rules for key in effects):
            raise ValueError(f"Unknown timed effect in joint state for {name}")
        active_states = set()
        total = 0.0
        for state in combinations:
            active = tuple(sorted(state["active"]))
            fraction = state["fraction"]
            if not active or len(active) != len(set(active)) or not set(active) <= set(effects) or active in active_states:
                raise ValueError(f"Invalid or duplicate active effect state for {name}")
            if not numeric(fraction) or not 0 <= fraction <= 1:
                raise ValueError(f"Invalid effect state probability for {name}")
            active_states.add(active)
            total += fraction
        if not active_states or total > 1 + 1e-9:
            raise ValueError(f"Joint effect states exceed available combat time for {name}")
    fields = {key: settings[key] for key in SCENARIO_FIELDS - {"weights"} if key in settings}
    if expectations:
        fields["item_effect_version"] = ITEM_EFFECT_VERSION
    return fields


def validate_scenario(settings: dict, name: str) -> None:
    if set(settings) - SCENARIO_FIELDS:
        raise ValueError(f"Unknown scenario override for {name}")
    if not all(numeric(value) for value in settings.get("weights", {}).values()):
        raise ValueError(f"Invalid stat weight for {name}")
    if not all(numeric(value) and value >= 0 for value in settings.get("caps", {}).values()):
        raise ValueError(f"Invalid stat cap for {name}")
    if any(not entry.get("from_stat") or not entry.get("stat") or not numeric(entry.get("factor"))
           or entry.get("condition") not in {None, "shield"} for entry in settings.get("conversions", [])):
        raise ValueError(f"Invalid stat conversion for {name}")


def operation_applies(operation: dict, rank: int, level: int, shield: bool, two_hand: bool) -> bool:
    condition = operation.get("condition")
    return (rank > 0 and operation.get("min_level", 1) <= level <= operation.get("max_level", 60)
            and (not condition or condition == "shield" and shield or condition == "two_hand" and two_hand))


def base_loadout(loadout: dict[int, dict] | list[dict], weights: dict, operations: list[dict], ranks: dict,
                 scenario: dict, race_id: int | None, level: int, bonus_stats: dict,
                 breakdown: dict | None = None) -> tuple[float, dict]:
    stats, sets, procs = defaultdict(float), defaultdict(int), []
    gear = loadout if isinstance(loadout, dict) else {}
    items = gear.values() if isinstance(loadout, dict) else loadout
    shield = any(item.get("shield") for item in items)
    two_hand = gear.get(16, {}).get("slot") == "Two Hand"
    offhand_dps = gear.get(17, {}).get("stats", {}).get("dps", 0)
    offhand_factor = scenario.get("offhand_dps_factor", 1)
    for item in items:
        for key, value in item["stats"].items():
            stats[key] += value
        if item.get("set_id"):
            sets[item["set_id"]] += 1
        procs.extend(item.get("procs", []))
    stats["dps"] -= offhand_dps * (1 - offhand_factor)
    stats["weapon_speed"] = gear.get(16, {}).get("stats", {}).get("weapon_speed", 0)
    for key, value in bonus_stats.items():
        stats[key] += value
    for bonus in scenario.get("sets", []):
        if sets[bonus["set_id"]] >= bonus["pieces"]:
            for key, value in bonus["stats"].items():
                stats[key] += value
    for proc in procs:
        events = scenario.get("events_per_minute", {}).get(proc["trigger"], 0)
        rate = min(events * proc["chance"], proc.get("max_per_minute", events))
        for key, value in proc["stats"].items():
            stats[key] += value * min(1, rate * proc["duration"] / 60)
    for racial in scenario.get("racial_scaling", []):
        if racial["race_id"] == race_id:
            stats[racial["stat"]] *= racial["multiplier"]
    for conversion in scenario.get("conversions", []):
        if conversion.get("condition") != "shield" or shield:
            stats[conversion["stat"]] += stats[conversion["from_stat"]] * conversion["factor"]
    specific_crit = {"spell": "spell_crit_percent", "physical": "physical_crit_percent"}.get(scenario.get("crit_domain"))
    if specific_crit and specific_crit not in weights:
        stats["crit_percent"] += stats[specific_crit]
    if scenario.get("crit_domain") == "spell" and "spell_hit_percent" not in weights:
        stats["hit_percent"] += stats["spell_hit_percent"]

    caps = scenario.get("caps", {})

    def value(points: dict | None = None) -> float:
        total = 0.0
        for stat, weight in weights.items():
            contribution = min(stats[stat], caps.get(stat, float("inf"))) * weight
            total += contribution
            if points is not None:
                points[stat] = contribution
        return total

    explanations = {}
    for operation in operations:
        rank = ranks.get(operation["entry"], 0)
        if not operation_applies(operation, rank, level, shield, two_hand):
            continue
        factor = operation["factors"][rank - 1]
        basis = value()
        for stat in operation["stats"]:
            if operation["kind"] == "convert":
                stats[stat] += stats[operation["from_stat"]] * factor
            elif operation["kind"] == "efficiency":
                stats[stat] /= 1 + factor
            elif operation["kind"] == "offhand_damage":
                stats[stat] += offhand_dps * offhand_factor * factor
            else:
                stats[stat] *= 1 + factor
        explanations[operation["entry"]] = explanations.get(operation["entry"], 0) + value() - basis
    return value(breakdown), explanations


def effective_activations(rule: dict, observation: dict, loadout: dict, position: int) -> float | None:
    if "uses" in observation and observation.get("seconds", 0) > 0:
        return 60 * observation["uses"] / observation["seconds"]
    if "per_minute" in observation:
        return observation["per_minute"]
    if "events_per_minute" not in observation:
        return None
    chance = rule.get("chance")
    speed = loadout[position]["stats"].get("weapon_speed")
    if "ppm" in rule and speed:
        chance = min(1, rule["ppm"] * speed / 60)
    if chance is None:
        return None
    rate = observation["events_per_minute"] * chance
    cooldown = rule.get("cooldown", 0)
    if cooldown:
        if observation.get("cooldown_model") != "poisson":
            return None
        rate /= 1 + rate * cooldown / 60
    return rate


def expected_item_effect(rule: dict, observation: dict, loadout: dict, position: int, scenario: dict) -> tuple[dict, float | None]:
    if observation.get("applicable") is False:
        return {}, None
    kind = rule["kind"]
    if kind == "mana_cost" and "mana_per_minute" in observation:
        return {"mp5": observation["mana_per_minute"] * rule["fraction"] / 12}, None
    rate = effective_activations(rule, observation, loadout, position)
    if kind == "timed_stats":
        if rule.get("requires_target_fraction") and "target_fraction" not in observation:
            return {}, None
        uptime = observation.get("uptime")
        if uptime is None and rate is not None and rule.get("cooldown", 0) >= rule["duration"]:
            uptime = min(1, rate * rule["duration"] / 60)
        if uptime is None:
            return {}, None
        multiplier = (rule.get("terrain_multiplier", {}).get(scenario.get("terrain"), 1)
                      * rule.get("target_multiplier", {}).get(scenario.get("target_family"), 1))
        return {key: amount * multiplier for key, amount in rule["stats"].items()}, uptime * observation.get("target_fraction", 1)
    if rate is None:
        return {}, None
    if kind == "instant" and "useful_fraction" in observation:
        terrain = rule.get("terrain_multiplier", {}).get(scenario.get("terrain"), 1)
        scale = rate * terrain * observation["useful_fraction"] / 60
        return {key: amount * scale for key, amount in rule["amounts"].items()}, None
    if kind == "extra_attack" and "damage_factor" in observation:
        stats = loadout.get(observation.get("weapon_slot", position), {}).get("stats", {})
        if "weapon_min_damage" in stats and "weapon_max_damage" in stats:
            average = (stats["weapon_min_damage"] + stats["weapon_max_damage"]) / 2
            return {"dps": average * rate * rule["count"] * observation["damage_factor"] / 60}, None
    if kind == "damage" and "damage_factor" in observation:
        return {"proc_dps": rule["amount"] * rate * observation["damage_factor"] / 60}, None
    return {}, None


def swap_score(loadout: dict[int, dict] | list[dict], weights: dict, operations: list[dict], ranks: dict, scenario: dict,
               *, race_id: int | None = None, level: int = 60, breakdown: dict | None = None) -> tuple[float, dict]:
    """Score a legal loadout over the encounter's reviewed effects and active states."""
    flat, timed = defaultdict(float), []
    expectations = scenario.get("effect_expectations", {})
    use_rules = []
    if expectations and isinstance(loadout, dict):
        use_rules = sorted(f"{position}:{identity(item)}:{rule['key']}" for position, item in loadout.items()
                           for rule in item.get("effect_rules", []) if rule["trigger"] == "use")
        use_signature = "|".join(use_rules)
        for position, item in sorted(loadout.items()):
            for rule in item.get("effect_rules", []):
                observation = expectations.get(identity(item), {}).get(rule["key"])
                if observation is None:
                    continue
                stats, uptime = expected_item_effect(rule, observation, loadout, position, scenario)
                solo = rule["trigger"] != "use" or len(use_rules) < 2 or observation.get("use_signature") == use_signature
                if uptime is not None:
                    timed.append((f"{position}:{identity(item)}:{rule['key']}", stats, uptime, solo, rule["trigger"]))
                elif solo:
                    for key, value in stats.items():
                        flat[key] += value

    total, explanations = base_loadout(loadout, weights, operations, ranks, scenario, race_id, level, flat, breakdown)
    states = []
    if len(timed) == 1:
        key, _, uptime, solo, _ = timed[0]
        if solo:
            states = [{"active": [key], "fraction": uptime}]
    elif timed:
        scoped = sum(trigger == "use" for _, _, _, _, trigger in timed) == len(use_rules)
        if scoped or all(solo for _, _, _, solo, _ in timed):
            signature = "|".join(sorted(key for key, *_ in timed))
            states = scenario.get("effect_state_observations", {}).get(signature, [])
    if states:
        timed_stats = {key: stats for key, stats, *_ in timed}
        baseline, baseline_explanations = total, dict(explanations)
        baseline_breakdown = dict(breakdown) if breakdown is not None else None
        for state in states:
            stats = defaultdict(float, flat)
            for name in state["active"]:
                for key, value in timed_stats[name].items():
                    stats[key] += value
            active_breakdown = {} if breakdown is not None else None
            active, active_explanations = base_loadout(loadout, weights, operations, ranks, scenario, race_id, level, stats,
                                                       active_breakdown)
            fraction = state["fraction"]
            total += (active - baseline) * fraction
            for key, value in active_explanations.items():
                explanations[key] = explanations.get(key, 0) + (value - baseline_explanations.get(key, 0)) * fraction
            if breakdown is not None:
                for stat, points in active_breakdown.items():
                    breakdown[stat] += (points - baseline_breakdown[stat]) * fraction
    return total, explanations


def source_levels(source: dict) -> set[int]:
    rule = source.get("eligibility", {})
    points = {rule.get("min_level", 1), rule.get("max_level", 59) + 1}
    for key in SOURCE_CHILDREN:
        for child in source.get(key, []):
            points.update(source_levels(child))
    return points


def source_identity(source: dict) -> dict:
    """Bind the reviewed path, including prerequisite identities and requirements."""
    keys = ("type", "side", "entity_id", "item_id", "quest_id", "quest_starter_item_id", "eligibility",
            "requirements", "price_copper", "currency", "available_from_phase", "available_until_phase", "content_type")
    return {**{key: source[key] for key in keys if key in source},
            **{key: [source_identity(child) for child in source[key]] for key in SOURCE_CHILDREN if source.get(key)}}


def leveling_windows(item: dict, profile: dict, persona: dict, slot: str, rules: dict) -> list[list[int]]:
    class_name = profile["class"]
    equipment = rules["class_equipment"][class_name]
    policy = rules["spec_policies"][f"{class_name}/{profile['spec']}"]
    points = {1, 60, item["required_level"], policy.get("dual_wield_level") or 1,
              policy.get("slot_min_levels", {}).get(slot, 1), policy.get("slot_max_levels", {}).get(slot, 59) + 1}
    points.update(tier["level"] for tier in equipment.get("armor_tiers", []))
    points.update(unlock["min_level"] for unlock in equipment.get("weapon_unlocks", []))
    for source in item.get("sources", []):
        points.update(source_levels(source))
    boundaries = sorted(point for point in points if 1 <= point <= 60)
    windows: list[list[int]] = []
    for start, end in zip(boundaries, boundaries[1:]):
        if eligible_item(item, profile, persona, start, slot, rules):
            if windows and windows[-1][1] + 1 == start:
                windows[-1][1] = end - 1
            else:
                windows.append([start, end - 1])
    return windows


def pre_raid_route_allows(source: dict, persona: dict, class_name: str) -> bool:
    rule = source.get("eligibility", {"min_level": 1})
    return (source["side"] in {persona["faction"], "Both"}
            and eligibility_allows(rule, persona["faction"], persona["name"], class_name, 60)
            and all(not source.get(key) or any(pre_raid_route_allows(child, persona, class_name)
                                              for child in source[key]) for key in SOURCE_CHILDREN))


def pack_item(item: dict) -> dict:
    return {"id": item["id"], "name": item["name"], "item_level": item.get("item_level") or 0,
            "slot": item["slot"], "required_level": item.get("required_level") or 1,
            "stats": normalized_item_stats(item), "shield": item.get("armor_type") == "Shield",
            **{key: item[key] for key in ("variant_id", "random_suffix_id", "max_equipped", "unique_group",
                                         "weapon_subtype", "armor_type", "requires_dual_wield")
                if key in item}}


def identity(item: dict) -> str:
    return item.get("variant_id") or str(item["id"])


def model_url(model: dict) -> str:
    build = model["client_build"]
    if not re.fullmatch(r"1\.60\.\d+\.\d+", build):
        raise ValueError("Expected an exact Forever client build")
    url = model.get("source_url")
    if url:
        if source_provider(url) != "raidbots" or f"wow%2F{build.rsplit('.', 1)[1]}%2FenUS%2F" not in url:
            raise ValueError("Expected a build-pinned Forever Raidbots source")
        return url
    revision = model["source_revision"]
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Expected a pinned Forever EG Link revision")
    return (f"https://raw.githubusercontent.com/JIVESCORP/eg-link-output-wowf/{revision}/"
            f"data/wowf/{build}/hotfixes.enUS.json")


def equipment_scope_digest(rules: dict, items: dict) -> str:
    return digest({"rules": rules, "items": items})


def compile_model(model: dict, snapshot: dict, documents: dict | None = None) -> tuple[dict, dict]:
    if model["version"] != VERSION or snapshot["client_build"] != model["client_build"] or snapshot["url"] != model_url(model):
        raise ValueError("Wrong build, source revision or version for Forever character scoring")

    def document(name: str) -> dict:
        return (documents or {}).get(name) or dataset_json("forever", name)

    rules = document("leveling_rules")
    pre_raid = scoring_profiles()
    leveling = document("leveling_scoring_profiles")
    references = reference_profiles(rules, leveling=leveling, model=model)
    variants = document("item_variants")["item_variants"]
    source_items = {
        "leveling": materialized_items(document("leveling_item_stats")["item_stats"], variants),
        "pre_raid": materialized_items(document("item_stats")["item_stats"], variants),
    }
    rules_build = rules["review"]["client_build"]
    compatibility = snapshot.get("equipment_compatibility", {})
    scope_digest = equipment_scope_digest(rules, source_items) if rules_build != model["client_build"] else None
    if rules_build != model["client_build"] and (
        compatibility.get("from_build") != rules_build
        or compatibility.get("to_build") != model["client_build"]
        or compatibility.get("scope_digest") != scope_digest
    ):
        raise ValueError(f"Forever scoring needs a current equipment comparison for both reviewed builds "
                         f"({rules_build} to {model['client_build']}, scope digest {scope_digest})")
    sets = snapshot.get("flat_sets", [])
    item_sets = {item_id: row["set_id"] for row in sets for item_id in row["item_ids"]}
    set_names = {row["set_id"]: row["name"] for row in sets if row.get("name")}
    if len(item_sets) != sum(len(row["item_ids"]) for row in sets):
        raise ValueError("Reviewed item sets have overlapping membership")
    items = {mode: {identity(item): {**pack_item(item),
                                    **({"set_id": item_sets[item["id"]]} if item["id"] in item_sets else {})}
                    for item in source_items[mode]} for mode in MODES}
    effect_items = {identity(item): item for pool in source_items.values() for item in pool}
    effect_items.update({identity(item): item for item in document("guide_item_reviews")["items"]})
    all_profiles = {f"{row['class']}/{row['spec']}": row for row in pre_raid["profiles"]}
    traits, profiles, bindings = {}, {}, {}
    enchants = {int(key): value["stats"] for key, value in snapshot["enchants"].items()}
    for name, settings in sorted(model["profiles"].items()):
        profile = all_profiles[name]
        class_name, spec = profile["class"], profile["spec"]
        shared = model.get("class_mechanics", {}).get(class_name, {})
        rules_for_spec = [*shared.get("operations", []), *settings["operations"]]
        if not rules_for_spec or not settings.get("unresolved"):
            raise ValueError(f"Scoring profile must describe its reviewed and unresolved effects: {name}")
        operations = []
        for rule in rules_for_spec:
            trait = snapshot["traits"][str(rule["entry"])]
            effect = next(row for row in trait["effects"] if row["effect_index"] == rule["effect"])
            factors = [point["value"] / 100 for point in effect["ranks"]]
            if (rule["kind"] not in {"scale", "convert", "efficiency", "offhand_damage"} or not rule["stats"]
                    or (rule["kind"] == "convert" and (not rule.get("from_stat") or rule["from_stat"] in rule["stats"]))
                    or (rule["kind"] == "offhand_damage" and rule["stats"] != ["dps"])
                    or rule.get("condition") not in {None, "shield", "two_hand"}
                    or not 1 <= rule.get("min_level", 1) <= rule.get("max_level", 60) <= 60
                    or not all(numeric(value) and value > -1 for value in factors)):
                raise ValueError(f"Invalid rank operation for {name}")
            operations.append({**rule, "factors": factors, "name": trait["name"]})
        ability = settings.get("ability")
        speed_proc = settings.get("weapon_speed_proc")
        proc_rule = snapshot["ability_triggers"][str(speed_proc["spell"])] if speed_proc else None
        uncertainty = [*shared.get("uncertainty", []), *settings.get("uncertainty", [])]
        if any(not rule.get("reason") or not rule.get("stats") or not set(rule.get("entries", [])) <= {
                int(key) for key in snapshot["traits"]} for rule in uncertainty):
            raise ValueError(f"Invalid uncertainty rule for {name}")
        entry_ids = sorted({rule["entry"] for rule in operations} | ({ability["entry"]} if ability else set())
                           | ({speed_proc["entry"]} if speed_proc else set())
                           | {entry for rule in uncertainty for entry in rule.get("entries", [])})
        selected_traits = {identifier: snapshot["traits"][str(identifier)] for identifier in entry_ids}
        for identifier, trait in selected_traits.items():
            traits[identifier] = {key: trait[key] for key in ("node_id", "definition_id", "spell_id", "tree_id", "max_rank", "name")}
        scenarios, dungeon = {}, {}
        crit_domain = {"caster": "spell", "healer": "spell", "melee": "physical", "ranged": "physical"}.get(profile["role"])
        personas = [row for row in rules["races"] if class_name in row["classes"]]
        allowed_personas = {row["id"]: [row["name"], row["faction"]] for row in personas}
        for mode in MODES:
            scenario_settings = settings.get("scenario_overrides", {}).get(mode, {})
            validate_scenario(scenario_settings, f"{name}/{mode}")
            weight_overrides = {**settings.get("weights", {}), **scenario_settings.get("weights", {})}
            weights = []
            if mode == "leveling":
                policy = rules["spec_policies"][name]
                slots = rules["common_slots"] + policy["slots"]
                for start, end, band_weights in references[name][mode]["weights"]:
                    weights.append([start, end, {**band_weights, **weight_overrides}])
                policies = {"dual_wield_level": policy.get("dual_wield_level"), "weapon_style": policy.get("weapon_style")}
            else:
                slots = profile["slots"]
                weights.append([60, 60, {**references[name][mode]["weights"], **weight_overrides}])
                policies = {"dual_wield_level": 1 if profile.get("dual_wield") else None,
                            "weapon_style": "shield" if profile.get("require_shield") else "any"}
            pools = {}
            for slot in slots:
                pool = []
                for item in source_items[mode]:
                    if item.get("recommendation_excluded") or not slot_matches(item["slot"], slot):
                        continue
                    restricted = item.get("restrictions", {}).get("races", [])
                    access = {}
                    if mode == "leveling" and type(item.get("required_level")) is int:
                        access = {persona["id"]: windows for persona in personas
                                  if (windows := leveling_windows(item, profile, persona, slot, rules))}
                    elif mode == "pre_raid" and (item.get("required_level") or 1) <= 60 and eligible(item, profile, slot, require_source=False):
                        access = {persona["id"]: [[60, 60]] for persona in personas
                                  if (not restricted or persona["name"] in restricted)
                                  and any(valid_source(route) and pre_raid_route_allows(route, persona, class_name)
                                          for route in item["sources"])}
                    if access:
                        pool.append([identity(item), access])
                if pool:
                    pools[slot] = pool
            scenario = {**model["scenarios"][mode], "weights": weights, "pools": pools,
                        "personas": allowed_personas, **{k: v for k, v in policies.items() if v is not None},
                        **scenario_effect_inputs(scenario_settings, effect_items, f"{name}/{mode}")}
            offhand_factor = settings.get("offhand_dps_factor", shared.get("offhand_dps_factor"))
            if offhand_factor is not None:
                if not numeric(offhand_factor) or not 0 < offhand_factor <= 1:
                    raise ValueError(f"Invalid off-hand weapon contribution for {name}/{mode}")
                scenario["offhand_dps_factor"] = offhand_factor
            if settings.get("form_attack_period"):
                scenario["form_attack_period"] = settings["form_attack_period"]
            if sets:
                scenario["sets"] = [{key: row[key] for key in ("set_id", "pieces", "stats")} for row in sets]
            if racials := [row for row in snapshot.get("racial_scaling", []) if row["race_id"] in allowed_personas]:
                scenario["racial_scaling"] = racials
            scenarios[mode] = scenario
            pool_items = {key: items[mode][key] for pool in pools.values() for key, _ in pool}
            routes = {identity(item): [source_identity(route) for route in item["sources"]]
                      for item in source_items[mode] if identity(item) in pool_items}
            bindings[f"{name}/{mode}"] = digest({"model_version": VERSION, "client_build": model["client_build"],
                "profile_version": (leveling if mode == "leveling" else pre_raid)["version"], "rules_version": rules["version"],
                "operations": operations, "ability": ability and snapshot["ability_triggers"][str(ability["spell"])],
                "traits": selected_traits, "scenario": scenario, "candidate_facts": pool_items,
                "unresolved": settings["unresolved"], "uncertainty": uncertainty, "weapon_speed_proc": proc_rule,
                "routes": routes, "enchants": enchants,
                **({"equipment_compatibility": compatibility} if compatibility else {})})
            if crit_domain:
                scenario["crit_domain"] = crit_domain
            if sets:
                scenario["set_effect_spells"] = {row["spell_id"]: True for row in sets}
            if preset := settings.get("dungeon", {}).get(mode):
                low, high = preset.get("min_level"), preset.get("max_level")
                floor, ceiling = (1, 59) if mode == "leveling" else (60, 60)
                dungeon_settings = {key: value for key, value in preset.items()
                                    if key not in {"min_level", "max_level", "version", "basis"}}
                scope = f"{name}/dungeon/{mode}"
                if (type(low) is not int or type(high) is not int or not floor <= low <= high <= ceiling
                        or not preset.get("version") or not preset.get("basis") or not preset.get("evidence")):
                    raise ValueError(f"Missing reviewed level range or evidence for {scope}")
                validate_scenario(dungeon_settings, scope)
                dungeon[mode] = {"min_level": low, "max_level": high, "version": preset["version"], "basis": preset["basis"],
                    "weights": [[start, end, {**band, **dungeon_settings.get("weights", {})}]
                                for start, end, band in weights if start <= high and end >= low],
                    **scenario_effect_inputs(dungeon_settings, effect_items, scope)}
                bindings[scope] = digest({"base": bindings[f"{name}/{mode}"], "preset": dungeon[mode]})
        profiles[name] = {"entries": entry_ids, "operations": operations, "scenarios": scenarios,
                          "unresolved": settings["unresolved"], "uncertainty": uncertainty, "ability": ability,
                          "weapon_speed_proc": speed_proc, **({"dungeon": dungeon} if dungeon else {})}
    return {"version": VERSION, "build": int(model["client_build"].rsplit(".", 1)[-1]), "profiles": profiles,
            "traits": traits, "items": items, "enchants": enchants, "triggers": snapshot["ability_triggers"],
            **({"item_sets": item_sets} if item_sets else {}), **({"set_names": set_names} if set_names else {})}, bindings


def read_model(snapshots: dict | None = None) -> tuple[dict, dict] | None:
    path = FOREVER_CANONICAL_DIR / "scoring_model.json"
    if not path.is_file():
        return None
    model = load_json(path)
    url = model_url(model)
    snapshot = (snapshots or {}).get(url) if snapshots is not None else load_json(snapshot_path(url))
    if not snapshot or snapshot["page_type"] != "mechanics":
        raise ValueError("Missing registered Forever scoring snapshot")
    return model, snapshot


def review_issues(model: dict, snapshot: dict, bindings: dict) -> list[str]:
    records = evidence_index({snapshot["url"]: snapshot})
    issues = []
    for key, current in bindings.items():
        try:
            approval = model["approvals"][key]
            if (not has_review(approval) or approval.get("client_build") != model["client_build"]
                    or approval["input_digest"] != current):
                raise ValueError("scoring inputs changed or review is missing")
            check_evidence_refs(approval, records)
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"{key}: {exc}")
    for key in sorted(model["approvals"].keys() - bindings.keys()):
        issues.append(f"{key}: no matching scoring context")
    return issues


def reviewed_runtime_model(snapshots: dict | None = None, documents: dict | None = None) -> dict:
    source = read_model(snapshots)
    if source is None:
        return {}
    model, snapshot = source
    runtime, bindings = compile_model(model, snapshot, documents)
    issues = review_issues(model, snapshot, bindings)
    if issues:
        raise ValueError("Stale or missing Forever scoring approvals: " + "; ".join(issues))
    access_ids, access_windows = {}, []
    for profile in runtime["profiles"].values():
        for scenario in profile["scenarios"].values():
            for slot, pool in scenario["pools"].items():
                packed = []
                for key, access in pool:
                    signature = tuple((race, tuple(map(tuple, windows))) for race, windows in sorted(access.items()))
                    if signature not in access_ids:
                        access_windows.append(access)
                        access_ids[signature] = len(access_windows)
                    packed.append([key, access_ids[signature]])
                scenario["pools"][slot] = packed
    runtime["access_windows"] = access_windows
    return runtime


def refresh_review_scope(changed_items: set[int], newer_builds: list[int]) -> dict:
    result = {"changed_item_ids": sorted(changed_items), "newer_client_builds": sorted(newer_builds),
              "existing_contexts_to_recheck": {}}
    if not changed_items and not newer_builds:
        return result
    try:
        model, snapshot = read_model()
        runtime, _ = compile_model(model, snapshot)
        for name, profile in sorted(runtime["profiles"].items()):
            for mode, scenario in sorted(profile["scenarios"].items()):
                items = runtime["items"][mode]
                affected = {items[key]["id"] for pool in scenario["pools"].values() for key, _ in pool
                            if items[key]["id"] in changed_items}
                if affected or newer_builds:
                    result["existing_contexts_to_recheck"][f"{name}/{mode}"] = sorted(affected)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        result["scoring_input_error"] = str(exc)
    return result


def scoring_audit(*, strict: bool = False, lua: str | None = None, input_dir: Path | None = None,
                  include_breakdowns: bool = False) -> dict:
    try:
        snapshots, documents = None, None
        if input_dir is not None:
            from tools.forever import derive, read_snapshots
            from tools.forever_leveling import documents as leveling_documents

            snapshots = read_snapshots(input_dir)
            documents = {**derive(snapshots, include_leveling=False), **leveling_documents(snapshots)}
        model, snapshot = read_model(snapshots)
        runtime, bindings = compile_model(model, snapshot, documents)
        issues = review_issues(model, snapshot, bindings)
        required = {f"{class_name}/{spec}/{mode}" for class_name, spec in roster() for mode in MODES}
        missing = sorted(required - bindings.keys())
        validation = {}
        if strict:
            from tools.forever_scoring_checks import reference_issues, validation_issues

            issues.extend(reference_issues())
            fixture_issues, verified, breakdowns = validation_issues(model, runtime, bindings, lua)
            issues.extend(fixture_issues)
            validation = {"required_contexts": len(required), "validated_contexts": verified,
                          "missing_contexts": missing}
            if include_breakdowns:
                validation["swap_breakdowns"] = breakdowns
        return {"ok": not issues and (not strict or not missing), "issues": issues,
                "client_build": model["client_build"], **validation,
                "mechanics": evidence_ref(snapshot["url"], {snapshot["url"]: snapshot}),
                "scoring_profiles": sorted(runtime["profiles"]),
                "reference_profiles": [key for key in sorted("/".join(row) for row in roster()) if key not in runtime["profiles"]],
                "candidate_counts": {key: {mode: sum(len(pool) for pool in value["scenarios"][mode]["pools"].values())
                                           for mode in MODES} for key, value in runtime["profiles"].items()},
                "bindings": bindings}
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "issues": [str(exc)]}
