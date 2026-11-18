"""The additional evidence and executable fixtures required to ship Forever scores."""
from __future__ import annotations

import math
import shutil
import subprocess

from tools.forever import has_review, numeric, roster, scoring_profiles
from tools.forever_comparison import normalized_item_stats, reference_profiles
from tools.project import ROOT, dataset_json


TOLERANCE = 0.01
SLOT_IDS = {
    "Head": (1,), "Neck": (2,), "Shoulder": (3,), "Chest": (5,), "Waist": (6,), "Legs": (7,), "Feet": (8,),
    "Wrist": (9,), "Hands": (10,), "Ring": (11, 12), "Trinket": (13, 14), "Back": (15,),
    "Main Hand": (16,), "Two Hand": (16,), "Off Hand": (17,),
    **dict.fromkeys(("Ranged", "Libram", "Idol", "Totem", "Relic"), (18,)),
}


def reference_issues() -> list[str]:
    rules = dataset_json("forever", "leveling_rules")
    references = reference_profiles(rules)
    issues = []
    if not has_review(dataset_json("forever", "leveling_scoring_profiles")["review"]):
        issues.append("Missing Leveling reference weight review")
    if not has_review(scoring_profiles()["review"]):
        issues.append("Missing Pre-Raid reference weight review")
    if references.keys() != {"/".join(row) for row in roster()}:
        issues.append("Reference profiles do not match the Forever spec roster")

    def valid_weights(weights: dict) -> bool:
        return any(value > 0 for value in weights.values() if numeric(value)) and all(
            numeric(value) and math.isfinite(value) and value >= 0 for value in weights.values())

    for name, profile in references.items():
        bands = profile["leveling"]["weights"]
        levels = [level for start, end, _ in bands for level in range(start, end + 1)]
        if levels != list(range(1, 60)) or not all(valid_weights(weights) for _, _, weights in bands):
            issues.append(f"{name}/leveling: invalid weight coverage")
        if not valid_weights(profile["pre_raid"]["weights"]):
            issues.append(f"{name}/pre_raid: invalid weights")
        for low, _, weights in [*bands, [60, 60, profile["pre_raid"]["weights"]]]:
            if name == "Druid/Feral tank" and low >= 10 and (
                    weights.get("stamina", 0) <= 0 or weights.get("armor", 0) <= 0
                    or weights.get("block_value", 0) or weights.get("parry_percent", 0)):
                issues.append(f"{name}/{low}: Bear Form weights require mitigation without shield block or parry")
            if name.startswith("Hunter/") and weights.get("ranged_dps", 0) <= 0:
                issues.append(f"{name}/{low}: ranged weapon damage has no weight")
    for family in ("item_stats", "leveling_item_stats"):
        for item in dataset_json("forever", family)["item_stats"]:
            stats = normalized_item_stats(item)
            damage = [stats.get(key) for key in ("weapon_min_damage", "weapon_max_damage", "weapon_speed")]
            dps = next((stats[key] for key in ("dps", "ranged_dps", "wand_dps") if key in stats), None)
            if dps is not None and all(v is not None for v in damage):
                low, high, speed = damage
                # Tooltips round each damage endpoint to whole points.
                if abs((low + high) / 2 - dps * speed) > 0.5 + 0.0051 * speed:
                    issues.append(f"{family}/{item['id']}: displayed weapon damage, speed and DPS disagree")
    return issues


def legal_loadout(gear: dict, target: int, slot: str, item: dict, scenario: dict, level: int) -> dict | None:
    """Check a single pinned swap independently of Lua's equipment checks."""
    outside = {index: worn for index, worn in gear.items() if index != target and (slot != "Two Hand" or index != 17)}
    group = item.get("unique_group")
    matching = [worn for worn in outside.values() if worn["id"] == item["id"] or (group and worn.get("unique_group") == group)]
    limits = [worn["max_equipped"] for worn in [item, *matching] if worn.get("max_equipped")]
    if len(matching) >= min(limits, default=1 if group else math.inf):
        return None
    if target == 17 and (outside.get(16, {}).get("slot") == "Two Hand" or (
            item.get("weapon_subtype") and item.get("requires_dual_wield") is not False
            and level < (scenario.get("dual_wield_level") or math.inf))):
        return None
    return {**outside, target: item}


def checked_fixture(runtime: dict, name: str, mode: str, fixture: dict) -> tuple[dict, list[dict], tuple[int, int]]:
    from tools.forever_scoring import swap_score

    profile = runtime["profiles"][name]
    scenario = profile["scenarios"][mode]
    level, target, slot, race = (fixture[key] for key in ("level", "target", "slot", "race_id"))
    if target not in SLOT_IDS[slot] or race not in scenario["personas"] or not fixture["reason"].strip():
        raise ValueError("missing a valid physical slot, character or independent calculation")
    start, end, weights = next(band for band in scenario["weights"] if band[0] <= level <= band[1])
    ranks = dict.fromkeys(profile["entries"], 0)
    for key, rank in fixture["ranks"].items():
        entry = int(key)
        if entry not in ranks or type(rank) is not int or not 0 <= rank <= runtime["traits"][entry]["max_rank"]:
            raise ValueError(f"invalid talent rank for {entry}")
        ranks[entry] = rank
    if level < 10 and any(ranks.values()):
        raise ValueError("talents are unavailable before level 10")
    if ability := profile.get("ability"):
        cadence = scenario.get("judgement_per_minute", 0)
        if ranks[ability["entry"]] and cadence:
            events = dict(scenario.get("events_per_minute", {}))
            for trigger in runtime["triggers"][str(ability["spell"])]["activates"]:
                events[trigger] = events.get(trigger, 0) + cadence
            scenario = {**scenario, "events_per_minute": events}
    items = runtime["items"][mode]
    gear = {int(index): items[key] for index, key in fixture["gear"].items()}
    for index, item in gear.items():
        equippable = [kind for kind, slots in SLOT_IDS.items() if index in slots
                      and (item["slot"] == kind or item["slot"] == "One Hand" and kind in {"Main Hand", "Off Hand"})]
        if not equippable or item["required_level"] > level:
            raise ValueError(f"{item['name']} cannot be equipped in fixture slot {index}")
    before, before_effects = swap_score(gear, weights, profile["operations"], ranks, scenario, race_id=race, level=level)
    permitted = {key for key, personas in scenario["pools"][slot]
                 if any(low <= level <= high for low, high in personas.get(race, []))}
    if len({row["variant"] for row in fixture["offers"]}) != len(fixture["offers"]):
        raise ValueError("duplicate candidate variant")
    offers, previous, affected = [], None, False
    for offer in fixture["offers"]:
        variant, expected = offer["variant"], offer["delta"]
        if variant not in permitted:
            raise ValueError(f"{variant} is outside the reviewed candidate pool")
        item = items[variant]
        proposal = legal_loadout(gear, target, slot, item, scenario, level)
        delta = None
        if proposal is None:
            if expected is not None:
                raise ValueError(f"{variant} is an illegal swap")
        else:
            result, effects = swap_score(proposal, weights, profile["operations"], ranks, scenario, race_id=race, level=level)
            delta = result - before
            if not numeric(expected) or abs(delta - expected) > TOLERANCE:
                raise ValueError(f"{variant}: expected {expected}, calculated {delta:.4f}")
            if previous:
                expected_gap, actual_gap = previous[0] - expected, previous[1] - delta
                if expected_gap < 0 or (expected_gap > 0 and actual_gap <= 0) or (
                        expected_gap == 0 and abs(actual_gap) >= 0.0001):
                    raise ValueError(f"{variant}: candidate rank order differs from the fixture")
            previous = (expected, delta)
            affected |= any(abs(effects.get(entry, 0) - before_effects.get(entry, 0)) >= 0.0001 for entry in ranks)
        offers.append({"item": item, "expected": expected, "python_delta": delta, "target": target, "slot": slot})
    if sum(offer.get("expected") is not None for offer in offers) < 2:
        raise ValueError("two legal candidates are required to check the order")
    return {"mode": mode, "level": level, "race": race, "gear": gear, "weights": weights, "ranks": ranks,
            "scenario": scenario, "profile": {"operations": profile["operations"]}, "talentAffected": affected}, offers, (start, end)


def find_lua51(lua: str | None) -> str | None:
    bundled = ROOT / "build" / "ui-acceptance-tools" / "lua5.1.exe"
    candidates = [lua] if lua else [shutil.which("lua5.1"), str(bundled) if bundled.is_file() else None, shutil.which("lua")]
    for candidate in filter(None, candidates):
        try:
            version = subprocess.run([candidate, "-e", "io.write(_VERSION)"], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if version.returncode == 0 and version.stdout == "Lua 5.1":
            return candidate
    return None


def ranking_snapshot(lua: str | None, phase: str) -> dict:
    from hashlib import sha256

    executable = find_lua51(lua)
    if not executable:
        raise ValueError("Lua 5.1 is required for the reference ranking report")
    try:
        result = subprocess.run([executable, "tools/forever_rank_report.lua", phase],
                                encoding="utf-8", capture_output=True, cwd=ROOT, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Forever reference ranking report timed out") from exc
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Forever ranking query failed")
    contexts = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if fields[0] == "context":
            context = contexts[fields[1]] = []
        else:
            _, slot, variant, band, score, rank, route, entity, location = fields
            context.append({"slot": slot, "variant": variant, "band": band,
                            "score": float(score) if score else None, "rank": int(rank) if rank else None,
                            "source": route, "source_id": entity, "activity": location})
    inputs = ("DataForever.lua", "Config.lua", "DataIndex.lua", "ForeverGearRating.lua", "tools/forever_rank_report.lua")
    input_digests = {name: sha256((ROOT / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                     for name in inputs}
    return {"content_phase": phase, "input_digests": input_digests, "contexts": contexts}


def check_lua(lua: str | None, cases: list[tuple]) -> str | None:
    from tools.project import lua_value

    executable = find_lua51(lua)
    if executable is None:
        return "Lua 5.1 is required for the scoring parity checks"
    parts = ["""
assert(_VERSION == "Lua 5.1", "Lua 5.1 is required")
BigBiSList = {}
dofile("ForeverScoring.lua")
local score = BigBiSList.ForeverScoring
local model = {items = {leveling = {}, pre_raid = {}}}
local cases = {"""]
    for label, state, offers in cases:
        state["scenario"] = {key: value for key, value in state["scenario"].items() if key != "pools"}
        parts.append(lua_value({"label": label, "state": state, "offers": offers}) + ",")
    parts.append("""
}
for _, case in ipairs(cases) do
    local state = case.state
    state.model = model
    local gear = {}
    for index, item in pairs(state.gear) do gear[tonumber(index)] = item end
    state.gear = gear
    local previous, previousExpected
    for _, option in ipairs(case.offers) do
        local result = score:EvaluateSwap(state, option.item, nil, option.target, option.slot, state.weights)
        local expected = option.expected
        local label = case.label .. " / " .. option.item.name
        if expected == nil then
            assert(not result, label .. " should be illegal")
        else
            assert(result and math.abs(result.delta - expected) <= 0.01,
                label .. " expected " .. expected .. ", calculated " .. tostring(result and result.delta))
            assert(math.abs(result.delta - option.python_delta) <= 0.01,
                label .. " differs from the Python swap by more than 0.01")
            if previous then
                local correct = previousExpected == expected and math.abs(previous - result.delta) < 0.0001
                    or previousExpected > expected and previous > result.delta
                assert(correct, label .. " has the wrong order")
            end
            previous, previousExpected = result.delta, expected
        end
    end
end
""")
    try:
        result = subprocess.run([executable, "-"], input="\n".join(parts), encoding="utf-8", capture_output=True, cwd=ROOT, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Lua 5.1 scoring parity failed to run: {exc}"
    if result.returncode:
        return result.stderr.strip() or "Lua 5.1 scoring parity failed"


def validation_issues(model: dict, runtime: dict, bindings: dict, lua: str | None) -> tuple[list[str], list[str]]:
    cases, issues, checked = [], [], []
    for name, profile in runtime["profiles"].items():
        for mode, scenario in profile["scenarios"].items():
            key = f"{name}/{mode}"
            validation = model["approvals"].get(key, {}).get("validation", {})
            if validation.get("input_digest") != bindings[key]:
                issues.append(f"{key}: missing or stale independent swap validation")
                continue
            covered, talent_affected = set(), False
            try:
                for index, fixture in enumerate(validation["fixtures"], 1):
                    state, offers, band = checked_fixture(runtime, name, mode, fixture)
                    cases.append((f"{key} #{index}", state, offers))
                    covered.add(band)
                    talent_affected |= state["talentAffected"]
                if covered != {(low, high) for low, high, _ in scenario["weights"]}:
                    raise ValueError("incomplete level-band validation")
                if not talent_affected:
                    raise ValueError("no swap fixture changes with an active talent")
            except (AttributeError, KeyError, StopIteration, TypeError, ValueError) as exc:
                issues.append(f"{key}: {exc}")
            else:
                checked.append(key)
    error = check_lua(lua, cases) if cases else None
    if error:
        issues.append(error)
        checked.clear()
    return issues, sorted(checked)
