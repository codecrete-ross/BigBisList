"""Compile the reviewed candidate pools and evaluate Forever gear swaps."""
from __future__ import annotations

from collections import defaultdict
import re

from tools.forever import SOURCE_CHILDREN, digest, eligible, has_review, numeric, roster, scoring_profiles, valid_source
from tools.forever_leveling import eligibility_allows, eligible_item
from tools.forever_mechanics import snapshot_path
from tools.forever_sources import check_evidence_refs, evidence_index, evidence_ref, source_provider
from tools.project import FOREVER_CANONICAL_DIR, dataset_json, load_json
from tools.recommend_leveling import materialized_items, merged_stats, profile_weights, separate_weapon_dps, slot_matches


VERSION = "forever-character-scoring-1"
MODES = ("leveling", "pre_raid")


def swap_score(loadout: list[dict], weights: dict, operations: list[dict], ranks: dict, scenario: dict,
               *, race_id: int | None = None) -> tuple[float, dict]:
    """Score gear-derived stats under a fixed encounter. Rank zero preserves base weights."""
    stats, sets, procs = defaultdict(float), defaultdict(int), []
    shield = any(item.get("shield") for item in loadout)
    for item in loadout:
        for key, value in item["stats"].items():
            stats[key] += value
        if item.get("set_id"):
            sets[item["set_id"]] += 1
        procs.extend(item.get("procs", []))
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

    def value() -> float:
        return sum(min(stats[key], scenario.get("caps", {}).get(key, float("inf"))) * weight
                   for key, weight in weights.items())

    explanations = {}
    for operation in operations:
        rank = ranks[operation["entry"]]
        if rank == 0 or (operation.get("condition") == "shield" and not shield):
            continue
        factor = operation["factors"][rank - 1]
        basis = value()
        for stat in operation["stats"]:
            if operation["kind"] == "convert":
                stats[stat] += stats[operation["from_stat"]] * factor
            elif operation["kind"] == "efficiency":
                stats[stat] /= 1 + factor
            else:
                stats[stat] *= 1 + factor
        explanations[operation["entry"]] = explanations.get(operation["entry"], 0) + value() - basis
    return value(), explanations


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
    stats = merged_stats(item)
    separate_weapon_dps(item, stats)
    return {"id": item["id"], "name": item["name"], "item_level": item.get("item_level") or 0,
            "slot": item["slot"], "required_level": item.get("required_level") or 1,
            "stats": stats, "shield": item.get("armor_type") == "Shield",
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
    variants = document("item_variants")["item_variants"]
    source_items = {
        "leveling": materialized_items(document("leveling_item_stats")["item_stats"], variants),
        "pre_raid": materialized_items(document("item_stats")["item_stats"], variants),
    }
    rules_build = rules["review"]["client_build"]
    compatibility = snapshot.get("equipment_compatibility", {})
    if rules_build != model["client_build"] and (
        compatibility.get("from_build") != rules_build
        or compatibility.get("to_build") != model["client_build"]
        or compatibility.get("scope_digest") != equipment_scope_digest(rules, source_items)
    ):
        raise ValueError("Forever scoring needs a current equipment comparison for both reviewed builds")
    sets = snapshot.get("flat_sets", [])
    item_sets = {item_id: row["set_id"] for row in sets for item_id in row["item_ids"]}
    if len(item_sets) != sum(len(row["item_ids"]) for row in sets):
        raise ValueError("Reviewed item sets have overlapping membership")
    items = {mode: {identity(item): {**pack_item(item),
                                    **({"set_id": item_sets[item["id"]]} if item["id"] in item_sets else {})}
                    for item in source_items[mode]} for mode in MODES}
    all_profiles = {f"{row['class']}/{row['spec']}": row for row in pre_raid["profiles"]}
    traits, profiles, bindings = {}, {}, {}
    enchants = {int(key): value["stats"] for key, value in snapshot["enchants"].items()}
    for name, settings in sorted(model["profiles"].items()):
        profile = all_profiles[name]
        class_name, spec = profile["class"], profile["spec"]
        if not settings["operations"] or not settings.get("unresolved"):
            raise ValueError(f"Scoring pilot profile must describe its reviewed and unresolved effects: {name}")
        operations = []
        for rule in settings["operations"]:
            trait = snapshot["traits"][str(rule["entry"])]
            effect = next(row for row in trait["effects"] if row["effect_index"] == rule["effect"])
            factors = [point["value"] / 100 for point in effect["ranks"]]
            if (rule["kind"] not in {"scale", "convert", "efficiency"} or not rule["stats"]
                    or (rule["kind"] == "convert" and (not rule.get("from_stat") or rule["from_stat"] in rule["stats"]))
                    or not all(numeric(value) and value > -1 for value in factors)):
                raise ValueError(f"Invalid rank operation for {name}")
            operations.append({**rule, "factors": factors, "name": trait["name"]})
        ability = settings.get("ability")
        entry_ids = sorted({rule["entry"] for rule in operations} | ({ability["entry"]} if ability else set()))
        selected_traits = {identifier: snapshot["traits"][str(identifier)] for identifier in entry_ids}
        for identifier, trait in selected_traits.items():
            traits[identifier] = {key: trait[key] for key in ("node_id", "definition_id", "spell_id", "tree_id", "max_rank", "name")}
        scenarios = {}
        personas = [row for row in rules["races"] if class_name in row["classes"]]
        allowed_personas = {row["id"]: [row["name"], row["faction"]] for row in personas}
        for mode in MODES:
            scenario_settings = settings.get("scenario_overrides", {}).get(mode, {})
            if scenario_settings.keys() - {"weights", "caps", "conversions", "evidence"}:
                raise ValueError(f"Unknown scenario override for {name}/{mode}")
            if not all(numeric(value) and value >= 0 for value in scenario_settings.get("caps", {}).values()):
                raise ValueError(f"Invalid stat cap for {name}/{mode}")
            if any(not entry.get("from_stat") or not entry.get("stat") or not numeric(entry.get("factor"))
                   or entry.get("condition") not in {None, "shield"} for entry in scenario_settings.get("conversions", [])):
                raise ValueError(f"Invalid stat conversion for {name}/{mode}")
            weight_overrides = {**settings.get("weights", {}), **scenario_settings.get("weights", {})}
            weights = []
            if mode == "leveling":
                policy = rules["spec_policies"][name]
                slots = rules["common_slots"] + policy["slots"]
                for _, start, end in rules["level_bands"]:
                    _, band_weights = profile_weights(leveling, class_name, spec, start, "best_overall", rules=rules)
                    weights.append([start, end, {**band_weights, **weight_overrides}])
                policies = {"dual_wield_level": policy.get("dual_wield_level"), "weapon_style": policy.get("weapon_style")}
            else:
                slots = profile["slots"]
                raid_weights = pre_raid["role_weights"][profile["role"]]
                weights.append([60, 60, {**raid_weights, **profile.get("weights", {}), **weight_overrides}])
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
                        **{key: scenario_settings[key] for key in ("caps", "conversions", "evidence") if key in scenario_settings}}
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
                "routes": routes, "enchants": enchants,
                **({"equipment_compatibility": compatibility} if compatibility else {})})
        profiles[name] = {"entries": entry_ids, "operations": operations, "scenarios": scenarios,
                          "unresolved": settings["unresolved"], "ability": ability}
    return {"version": VERSION, "build": int(model["client_build"].rsplit(".", 1)[-1]), "profiles": profiles,
            "traits": traits, "items": items, "enchants": enchants, "triggers": snapshot["ability_triggers"],
            **({"item_sets": item_sets} if item_sets else {})}, bindings


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
            if not has_review(approval) or approval["input_digest"] != current:
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
    return runtime


def scoring_audit() -> dict:
    try:
        model, snapshot = read_model()
        runtime, bindings = compile_model(model, snapshot)
        issues = review_issues(model, snapshot, bindings)
        return {"ok": not issues, "issues": issues, "client_build": model["client_build"],
                "mechanics": evidence_ref(snapshot["url"], {snapshot["url"]: snapshot}),
                "scoring_profiles": sorted(runtime["profiles"]),
                "reference_profiles": [key for key in sorted("/".join(row) for row in roster()) if key not in runtime["profiles"]],
                "candidate_counts": {key: {mode: sum(len(pool) for pool in value["scenarios"][mode]["pools"].values())
                                           for mode in MODES} for key, value in runtime["profiles"].items()},
                "bindings": bindings}
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "issues": [str(exc)]}
