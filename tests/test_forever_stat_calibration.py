import unittest
from tools.forever_stats import normalized_stats, profile_scenario, reference_score, weight_review
from tools.forever_scoring import swap_score
from tests.test_addon_runtime_lua import find_lua51
import subprocess
import copy


class ForeverStatCalibrationTests(unittest.TestCase):
    def points(self, stats, weights, scenario=None, operations=None, ranks=None):
        return swap_score({16: {"slot": "Two Hand", "stats": stats}}, weights, operations or [],
                          ranks or {}, scenario or {}, level=60)[0]

    def test_rating_units_are_fractional_and_count_a_tooltip_once(self):
        raw = {"hit_rating": 9, "crit_rating": 7, "expertise_rating": 12,
               "defense_rating": 5, "dodge_rating": 6, "parry_rating": 7.5, "block_rating": 2.5}
        values = normalized_stats(raw)
        self.assertEqual(values, {"hit_percent": .9, "crit_percent": .5, "expertise": 1.2,
                                 "defense": 5, "dodge_percent": .5, "parry_percent": .5, "block_percent": .5})
        self.assertEqual(normalized_stats({**raw, "hit_percent": .9}), values)
        self.assertEqual(normalized_stats(values), values)

    def test_reference_scores_keep_race_slot_and_shield_context(self):
        spirit = {"id": 1, "slot": "Neck", "stats": {"spirit": 10}}
        human = {"reference_race_id": 1, "racial_scaling": [{"race_id": 1, "stat": "spirit", "multiplier": 1.1}]}
        self.assertEqual(reference_score(spirit, {"spirit": 1}, human), 11)
        weapon = {"id": 2, "slot": "One Hand", "stats": {"dps": 20}}
        scenario = {"offhand_dps_factor": .3}
        self.assertEqual(reference_score(weapon, {"dps": 1}, scenario, slot="Main Hand"), 20)
        self.assertEqual(reference_score(weapon, {"dps": 1}, scenario, slot="Off Hand"), 6)
        shield = {"id": 3, "slot": "Off Hand", "armor_type": "Shield", "stats": {"strength": 10}}
        scenario = {"conversions": [{"from_stat": "strength", "stat": "block_value", "factor": .05, "condition": "shield"}]}
        self.assertEqual(reference_score(shield, {"block_value": 1}, scenario), .5)

    def test_ranged_hit_changes_the_real_ring_choice_at_the_cap(self):
        weights = {"hit_percent": 11, "attack_power": .6, "crit_percent": 7, "stamina": .2}
        scenario = {"hit_curves": [{"channel": "ranged", "segments": [[8, 1]]}]}
        def ring(outside, stats):
            return swap_score({5: {"stats": {"hit_percent": outside}}, 11: {"stats": stats}},
                              weights, [], {}, scenario, level=60)[0]
        blackstone = {"attack_power": 20, "hit_percent": 1, "stamina": 6}
        painweaver = {"attack_power": 12, "crit_percent": 1, "stamina": 9}
        self.assertAlmostEqual(ring(0, blackstone) - ring(0, painweaver), 8.2)
        self.assertAlmostEqual(ring(8, blackstone) - ring(8, painweaver), -2.8)
        self.assertAlmostEqual(ring(9.5, blackstone) - ring(9.5, painweaver), -2.8)
        self.assertAlmostEqual(ring(7.5, blackstone) - ring(7.5, painweaver), 2.7)

    def test_passive_hit_does_not_give_empty_gear_points(self):
        scenario = {"hit_curves": [{"channel": "ranged", "segments": [[8, 1]]}],
                    "reference_bonuses": {"ranged_hit_percent": 3}}
        self.assertEqual(self.points({}, {"hit_percent": 10}, scenario), 0)
        self.assertEqual(self.points({"hit_percent": 5}, {"hit_percent": 10}, scenario), 50)
        self.assertEqual(self.points({"hit_percent": 7}, {"hit_percent": 10}, scenario), 50)

    def test_background_scores_yield_without_changing_a_capped_temporary_effect(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 is unavailable")
        result = subprocess.run([lua, "-"], capture_output=True, encoding="utf-8", timeout=20, input=r'''
BigBiSList = {}
dofile("ForeverScoring.lua")
local owner, yields = nil, 0
BigBiSList.ForeverGearRating = {GetWorkCheckpoint = function()
    if coroutine.running() == owner then
        return function() yields = yields + 1; coroutine.yield("slice") end
    end
end}
local gear = {[1] = {stats = {hit_percent = 7.5}}, [13] = {id = 2, stats = {}, effect_rules = {
    {key = "accuracy", label = "Temporary accuracy", kind = "timed_stats", trigger = "use", duration = 20, cooldown = 300,
        stats = {hit_percent = 7}}}}}
local scenario = {hit_curves = {{channel = "ranged", segments = {{8, 1}}}},
    effect_expectations = {[2] = {accuracy = {uptime = .5}}}}
owner = coroutine.create(function()
    return BigBiSList.ForeverScoring.ScoreLoadout(gear, {hit_percent = 10}, {}, {}, scenario)
end)
local total
repeat
    local ok, value = coroutine.resume(owner)
    assert(ok, value)
    total = value
until coroutine.status(owner) == "dead"
-- The trinket adds only 0.5 useful hit at 50% uptime: 75 + 5 * 0.5.
assert(total == 77.5 and yields >= 2)
assert(BigBiSList.ForeverScoring.ScoreLoadout(gear, {hit_percent = 10}, {}, {}, scenario) == total)
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_published_hit_coefficients_have_unit_slope_at_reference_talents(self):
        for name in weight_review()["profiles"]:
            scenario = profile_scenario(name, "pre_raid")
            self.assertAlmostEqual(self.points({"hit_percent": .01}, {"hit_percent": 1}, scenario), .01,
                                   places=7, msg=name)

    def test_survival_weaving_keeps_melee_value_and_haste_uncertainty(self):
        profile = weight_review()["profiles"]["Hunter/Survival"]
        weights = profile["weights"]
        self.assertGreater(weights["dps"], 0)
        self.assertGreater(weights["strength"], 0)
        self.assertGreater(weights["expertise"], 0)
        self.assertGreater(weights["attack_power"], weights["ranged_attack_power"])
        self.assertTrue(any(alt.get("haste_percent", 0) < 0 for alt in profile["alternative_weights"]))
        self.assertEqual({curve["channel"] for curve in profile["hit_curves"]}, {"melee", "ranged"})

    def test_specific_spell_hit_and_hybrid_crit_are_counted_once(self):
        spell = {"crit_domain": "spell", "hit_curves": [{"channel": "spell", "segments": [[17, 1]]}]}
        self.assertEqual(self.points({"spell_hit_percent": 1}, {"hit_percent": 10}, spell), 10)
        hybrid = {"effect_benchmark": {"role": "melee"}, "crit_domain": "physical",
                  "crit_shares": {"physical": .7, "melee": .7, "spell": .3}}
        self.assertEqual(self.points({"melee_crit_percent": 1}, {"crit_percent": 10}, hybrid), 7)
        self.assertEqual(self.points({"spell_crit_percent": 1}, {"crit_percent": 10}, hybrid), 3)

    def test_rogue_hit_keeps_white_and_poison_value_after_special_cap(self):
        scenario = profile_scenario("Rogue/Combat", "pre_raid")
        weights = {"hit_percent": 10}
        values = [self.points({"hit_percent": n}, weights, scenario) for n in (0, 5, 6, 14, 15, 24, 25)]
        self.assertGreater(values[2], values[1])
        self.assertGreater(values[4], values[3])
        self.assertEqual(values[5], values[6])
        self.assertGreater(values[3] - values[2], values[5] - values[4])

    def test_reference_talents_adjust_coefficients_once(self):
        operation = {"entry": 1, "kind": "scale", "stats": ["strength"], "factors": [.1, .2]}
        scenario = {"reference_ranks": {"1": 2}}
        weights = {"strength": 2}
        self.assertEqual(self.points({"strength": 10}, weights, scenario), 20)
        self.assertEqual(self.points({"strength": 10}, weights, scenario, [operation], {1: 2}), 20)
        self.assertAlmostEqual(self.points({"strength": 10}, weights, scenario, [operation]), 20 / 1.2)

    def test_reference_weapon_talent_is_removed_when_the_equipment_condition_is_lost(self):
        rule = {"entry": 1, "kind": "scale", "stats": ["dps"], "factors": [.06], "condition": "two_hand"}
        scenario = {"reference_ranks": {"1": 1}}
        two = {16: {"slot": "Two Hand", "stats": {"dps": 20}}}
        one = {16: {"slot": "Main Hand", "stats": {"dps": 20}}}
        self.assertEqual(swap_score(two, {"dps": 1}, [rule], {1: 1}, scenario)[0], 20)
        self.assertAlmostEqual(swap_score(one, {"dps": 1}, [rule], {1: 1}, scenario)[0], 20 / 1.06)
        self.assertAlmostEqual(swap_score(two, {"dps": 1}, [rule], {}, scenario)[0], 20 / 1.06)

    def test_reference_inversion_preserves_scaling_before_conversion(self):
        operations = [{"entry": 1, "kind": "scale", "stats": ["intellect"], "factors": [.1]},
                      {"entry": 2, "kind": "convert", "from_stat": "intellect", "stats": ["spell_power"], "factors": [.6]}]
        weights = {"intellect": 1.21, "spell_power": 1}
        scenario = {"reference_ranks": {"1": 1, "2": 1}}
        gear = {1: {"stats": {"intellect": 10}}}
        for ranks, expected in (({1: 1, 2: 1}, 12.1), ({1: 1}, 5.5), ({2: 1}, 11), ({}, 5)):
            self.assertAlmostEqual(swap_score(gear, weights, operations, ranks, scenario)[0], expected)

    def test_alternative_benchmarks_do_not_make_useful_stats_harmful(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 is unavailable")
        result = subprocess.run([lua, "-"], capture_output=True, encoding="utf-8", timeout=20, input=r'''
dofile("DataForever.lua"); dofile("Config.lua"); dofile("ForeverScoring.lua")
local resto = BigBiSListData.character_scoring.profiles["Druid/Restoration"].scenarios.pre_raid
assert(resto.reference_ranks["129610"] == 0 and resto.reference_ranks["129618"] == 2)
assert(resto.weight_alternatives[1].mp5 == 0)
for name, profile in pairs(BigBiSListData.character_scoring.profiles) do
    local scenario = profile.scenarios.pre_raid
    local variants = {scenario.weights[1][3]}
    for _, changes in ipairs(scenario.weight_alternatives or {}) do
        local weights = {}
        for stat, value in pairs(variants[1]) do weights[stat] = value end
        for stat, value in pairs(changes) do weights[stat] = value end
        variants[#variants + 1] = weights
    end
    for _, weights in ipairs(variants) do
        for stat, coefficient in pairs(weights) do
            if coefficient >= 0 then
                local gear = {[1] = {stats = {[stat] = 1}},
                    [16] = {slot = "Two Hand", stats = {}}, [17] = {shield = true, stats = {}}}
                for _, ranks in ipairs({{}, scenario.reference_ranks}) do
                    local value = BigBiSList.ForeverScoring.ScoreLoadout(
                        gear, weights, profile.operations, ranks, scenario, nil, 60)
                    assert(value >= -0.000001, name .. "/" .. stat .. "=" .. value)
                end
            end
        end
    end
end
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tidal_focus_affects_both_attack_channels(self):
        operations = [{"entry": 1, "kind": "add", "stats": ["melee_hit_percent", "spell_hit_percent"],
                       "factors": [1, 2, 3, 4, 5]}]
        scenario = {"hit_curves": [{"channel": "melee", "segments": [[8, .7]]},
                                   {"channel": "spell", "segments": [[17, .3]]}]}
        weights = {"hit_percent": 10}
        self.assertAlmostEqual(self.points({"hit_percent": 6}, weights, scenario, operations, {1: 5}), 39)
        self.assertEqual(self.points({}, weights, scenario, operations, {1: 5}), 0)

    def test_expertise_counts_fractional_reduction_and_caps(self):
        scenario = {"caps": {"expertise": 6.5}, "reference_bonuses": {"expertise": 2}}
        self.assertAlmostEqual(self.points({"expertise_rating": 12}, {"expertise": 10}, scenario), 12)
        self.assertEqual(self.points({"expertise_rating": 50}, {"expertise": 10}, scenario), 45)
        self.assertEqual(self.points({"expertise_rating": 100}, {"expertise": 10}, scenario), 45)

    def test_front_expertise_drops_after_dodge_and_keeps_only_parry_value(self):
        scenario = {"expertise_curve": [[6.5, 1], [14, .5]]}
        weights = {"expertise": 10}
        self.assertEqual(self.points({"expertise": 6.5}, weights, scenario), 65)
        self.assertEqual(self.points({"expertise": 8.5}, weights, scenario), 75)
        self.assertEqual(self.points({"expertise": 14}, weights, scenario), 102.5)
        self.assertEqual(self.points({"expertise": 20}, weights, scenario), 102.5)
        scenario["reference_bonuses"] = {"expertise": 7}
        self.assertEqual(self.points({"expertise": 2}, weights, scenario), 10)
        self.assertEqual(profile_scenario("Warrior/Protection", "leveling")["expertise_curve"], [[5, 1]])

    def test_weapon_damage_from_effects_and_sets_counts_once(self):
        weapon = {"slot": "Main Hand", "stats": {"dps": 20, "weapon_speed": 2}, "set_id": 1}
        gloves = {"id": 2, "stats": {}, "effect_rules": [
            {"key": "flat", "label": "+2 weapon damage", "kind": "passive_stats", "stats": {"weapon_damage": 2}}]}
        scenario = {"effect_expectations": {"2": {"flat": {}}},
                    "sets": [{"set_id": 1, "pieces": 1, "stats": {"weapon_damage": 2}}]}
        score = swap_score({16: weapon, 10: gloves}, {"dps": 1}, [], {}, scenario)[0]
        self.assertEqual(score, 22)
        gloves["stats"]["weapon_damage"] = 2
        self.assertEqual(swap_score({16: weapon, 10: gloves}, {"dps": 1}, [], {}, scenario)[0], score)

    def test_published_directional_regressions_cover_all_profiles(self):
        profiles = weight_review()["profiles"]
        self.assertEqual(len(profiles), 28)
        rogue = profiles["Rogue/Combat"]["weights"]
        self.assertGreater(rogue["agility"], rogue["strength"])
        self.assertAlmostEqual(rogue["strength"] / rogue["attack_power"], 1.1, places=4)
        arms = profiles["Warrior/Arms"]["weights"]
        self.assertGreater(arms["dps"], arms["strength"] * 5)
        balance = profiles["Druid/Balance"]["weights"]
        self.assertAlmostEqual(balance["arcane_damage"] + balance["nature_damage"], balance["spell_power"], places=5)
        destro = profiles["Warlock/Destruction"]["weights"]
        self.assertGreater(destro["shadow_damage"], 0)
        self.assertAlmostEqual(destro["shadow_damage"] + destro["fire_damage"], destro["spell_power"], places=5)
        for name, profile in profiles.items():
            self.assertTrue(profile["priority_url"].startswith("https://"))
            self.assertTrue(profile["source_weights"]["source"])
            self.assertTrue(profile["hit_curves"])

    def test_healer_throughput_does_not_count_the_damage_line_on_healing_gear(self):
        for profile in weight_review()["profiles"].values():
            if profile["role"] == "healer":
                weights = profile["weights"]
                self.assertEqual(weights["spell_power"], weights["healing_power"])
                self.assertEqual(self.points({"healing_power": 24, "spell_damage": 8, "wand_dps": 50}, weights),
                                 self.points({"healing_power": 24}, weights))

    def test_current_short_fight_shawl_and_capped_benchmark_hit_stay_qualified(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 is unavailable")
        result = subprocess.run([lua, "-"], capture_output=True, encoding="utf-8", timeout=30, input=r'''
dofile("DataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
local model, scorer = BigBiSListData.character_scoring, BigBiSList.ForeverScoring
local profile = model.profiles["Priest/Discipline"]
local scenario = profile.scenarios.pre_raid
local weights = scenario.weights[1][3]
local before = {[3] = model.items.pre_raid["16695"]} -- Devout Mantle
local after = {[3] = model.items.pre_raid["19507"]} -- Inquisitor's Shawl
local function points(gear, values)
    return scorer.ScoreLoadout(gear, values, profile.operations, scenario.reference_ranks, scenario, 1, 60)
end
assert(points(after, weights) < points(before, weights))
local short = {}
for key, value in pairs(weights) do short[key] = value end
for key, value in pairs(scenario.weight_alternatives[1]) do short[key] = value end
-- +11 healing, -8 Intellect and -4 Stamina. The current short-fight
-- benchmark assigns no marginal value to Spirit in this setup.
assert(math.abs(points(after, short) - points(before, short)
    - (11 - 8 * .4 - 4 * .2)) < .000001)
assert(scorer:SwapDependsOnWeights(before, after, weights, profile.operations,
    scenario.reference_ranks, scenario, 1, 60))
local tank = model.profiles["Warrior/Protection"].scenarios.pre_raid
local primary, threat = tank.weights[1][3], {}
for key, value in pairs(primary) do threat[key] = value end
for key, value in pairs(tank.weight_alternatives[1]) do threat[key] = value end
local low, high = {[1]={stats={hit_percent=7.5}}}, {[1]={stats={hit_percent=8.5}}}
for _, values in ipairs({primary, threat}) do
    local gain = scorer.ScoreLoadout(high, values, {}, {}, tank, nil, 60)
        - scorer.ScoreLoadout(low, values, {}, {}, tank, nil, 60)
    assert(math.abs(gain - 2.5) < .000001, "Do not reuse a near-cap benchmark's small Hit derivative below the cap")
end
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_level_twenty_enhancement_recovery_changes_a_real_bracer_swap(self):
        from tools.forever_comparison import reference_profiles
        from tools.project import dataset_json
        bands = reference_profiles(dataset_json("forever", "leveling_rules"))["Shaman/Enhancement"]["leveling"]["weights"]
        weights = next(values for low, high, values in bands if low <= 20 <= high)
        items = {row["id"]: row for row in dataset_json("forever", "comparison_item_stats")["items"]}
        # Mindthrust Bracers and Wolf Bracers are both wearable at level 20.
        recovery, agility = items[1974], items[4794]
        def score(item, values):
            return swap_score({9: item}, values, [], {}, {}, level=20)[0]
        self.assertAlmostEqual(score(recovery, weights), 8.1)
        self.assertAlmostEqual(score(agility, weights), 4.2)
        without_recovery = {**weights, "mp5": 0}
        self.assertLess(score(recovery, without_recovery), score(agility, without_recovery))

    def test_lua_rating_units_caps_and_builds(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        code = r'''
BigBiSList = {}
dofile("ForeverScoring.lua")
local s = BigBiSList.ForeverScoring
local v = s.NormalizeStats({hit_rating=9,hit_percent=.9,expertise_rating=12,crit_rating=7})
assert(v.hit_percent == .9 and v.expertise == 1.2 and v.crit_percent == .5 and not v.hit_rating)
local model = {build=70959,supported_builds={71037}}
assert(s:IsBuildSupported(model,"71037") and s:IsBuildSupported(model,70959))
assert(not s:IsBuildSupported(model,71038) and not s:IsBuildSupported(model,nil))
local front={expertise_curve={{6.5,1},{14,.5}},reference_bonuses={expertise=7}}
assert(s.ScoreLoadout({[1]={stats={expertise=2}}},{expertise=10},{},{},front,nil,60)==10)
local weaponTalent={{entry=1,kind="scale",stats={"dps"},factors={.06},condition="two_hand"}}
local reference={reference_ranks={[1]=1}}
assert(s.ScoreLoadout({[16]={slot="Two Hand",stats={dps=20}}},{dps=1},weaponTalent,{[1]=1},reference)==20)
assert(math.abs(s.ScoreLoadout({[16]={slot="Main Hand",stats={dps=20}}},{dps=1},weaponTalent,{[1]=1},reference)-20/1.06)<1e-8)
local conversion={{entry=1,kind="scale",stats={"intellect"},factors={.1}},
    {entry=2,kind="convert",from_stat="intellect",stats={"spell_power"},factors={.6}}}
local converted=s.ScoreLoadout({[1]={stats={intellect=10}}},{intellect=1.21,spell_power=1},conversion,{[1]=1},
    {reference_ranks={[1]=1,[2]=1}})
assert(math.abs(converted-5.5)<1e-8)
local scenario = {reference_bonuses={ranged_hit_percent=3},
    hit_curves={{channel="ranged",segments={{8,1}}}}}
assert(s.ScoreLoadout({[1]={stats={}}},{hit_percent=10},{},{},scenario,nil,60)==0)
assert(s.ScoreLoadout({[1]={stats={hit_rating=70}}},{hit_percent=10},{},{},scenario,nil,60)==50)
local shield = {stats={expertise_rating=10,weapon_damage=1}}
assert(s.ScoreLoadout({[1]=shield},{expertise=10,dps=6},{},{},{},nil,60)>10)
local primary = {armor=1,stamina=1,attack_power=1}
local encounter = {weight_alternatives={{armor=0,stamina=0}}}
local worn, candidate = {[1]={stats={armor=10}}}, {[1]={stats={attack_power=5}}}
assert(s:SwapDependsOnWeights(worn,candidate,primary,{},{},encounter,nil,60))
local gear = {[16]={stats={dps=20,weapon_speed=2},set_id=1},[10]={id=2,stats={},
    effect_rules={{key="flat",label="+2 weapon damage",kind="passive_stats",stats={weapon_damage=2}}}}}
local withEffects = {effect_expectations={[2]={flat={}}},sets={{set_id=1,pieces=1,stats={weapon_damage=2}}}}
assert(s.ScoreLoadout(gear,{dps=1},{},{},withEffects,nil,60)==22)
gear[10].stats.weapon_damage=2
assert(s.ScoreLoadout(gear,{dps=1},{},{},withEffects,nil,60)==22)
'''
        result = subprocess.run([lua, "-"], input=code, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_target_compatibility_rejects_changed_mechanics_and_roll_budgets(self):
        from tools.forever_compatibility import supported_builds
        from tools.forever_scoring import read_model
        from tools.project import dataset_json
        _, snapshot = read_model()
        self.assertEqual(supported_builds(snapshot=snapshot), [71037])
        changed = copy.deepcopy(snapshot)
        changed["enchants"]["1891"]["stats"]["intellect"] += 1
        with self.assertRaisesRegex(ValueError, "compatibility"):
            supported_builds(snapshot=changed)
        catalog = dataset_json("forever", "guide_equipment")
        self.assertEqual(supported_builds(catalog=catalog), [71037])
        family = next(row for row in catalog["items"] if len(row) > 10 and row[10])
        family[10] += 1
        with self.assertRaisesRegex(ValueError, "compatibility"):
            supported_builds(catalog=catalog)

    def test_packaged_reference_prices_hotfixed_and_previously_zero_items(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        code = r'''
dofile("DataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")
local rating, scorer = BigBiSList.ForeverGearRating, BigBiSList.ForeverScoring
local function context(class, spec)
    return rating:GetGuideContext(class, spec, "PR", 60, "Human", "Alliance")
end
local frost = context("Mage", "Frost")
local whiteout, crackling = rating:GetPublishedFacts("19101"), rating:GetPublishedFacts("19102")
assert(whiteout.stats.stamina == 25 and whiteout.stats.intellect == 25 and whiteout.stats.spell_power == 74)
local first = rating:GetReferenceCandidate(frost, whiteout, "Two Hand").score
local second = rating:GetReferenceCandidate(frost, crackling, "Two Hand").score
assert(math.abs(first - second) < 0.000001)
assert(scorer.ScoreLoadout({whiteout}, {stamina=.2,intellect=.55,spell_power=1}, {}, {}, {}, nil, 60) == 92.75)
local fury = context("Warrior", "Fury")
local gloves = rating:GetPublishedFacts("14551")
local priced = rating:GetReferenceCandidate(fury, gloves, "Hands")
assert(priced.score > 0, "Edgemaster expertise and weapon damage must contribute")
local destro = context("Warlock", "Destruction")
local robe = rating:GetPublishedFacts("14106")
assert(robe.stats.shadow_damage > 0)
assert(rating:GetReferenceCandidate(destro, robe, "Chest").score > 1.4)
local hunter = BigBiSListData.character_scoring.profiles["Hunter/Marksmanship"].scenarios.pre_raid
local weights = hunter.weights[1][3]
local blackstone, painweaver = rating:GetPublishedFacts("17713"), rating:GetPublishedFacts("13098")
local function ring(item, hit)
    return scorer.ScoreLoadout({[5]={stats={hit_percent=hit}},[11]=item}, weights, {}, {}, hunter, nil, 60)
end
assert(ring(painweaver, 8) > ring(blackstone, 8))
assert(math.abs((ring(painweaver, 8)-ring(blackstone, 8)) - (ring(painweaver, 9.5)-ring(blackstone, 9.5))) < .000001)
local survival = BigBiSListData.character_scoring.profiles["Hunter/Survival"]
local weaving = survival.scenarios.pre_raid
assert(scorer:SwapDependsOnWeights({}, {[1]={stats={haste_percent=1}}}, weaving.weights[1][3],
    survival.operations, weaving.reference_ranks, weaving, nil, 60))
C_Item = {
    GetItemInfo = function() return "Rating fixture",nil,3,60,60 end,
    GetItemInfoInstant = function() return 990099,"Armor","Misc","INVTYPE_FINGER",nil,4,0 end,
    IsItemDataCachedByID = function() return true end,
    GetItemStats = function() return {ITEM_MOD_HIT_RATING_SHORT=9,ITEM_MOD_CRIT_RATING_SHORT=7,
        ITEM_MOD_EXPERTISE_RATING_SHORT=12} end,
}
C_TooltipInfo = {GetHyperlink = function() return {lines={
    {leftText="Equip: Improves your chance to hit by 0.9%."},
    {leftText="Equip: Improves your chance to get a critical strike by 0.5%."},
    {leftText="Equip: Reduces chance to be Dodged or Parried by 1.2%."},
    {leftText="Equip: +1 Weapon Damage."},
}} end}
local native = assert(rating:ReadNative(990099,"990099","item:990099"))
assert(native.stats.hit_percent==.9 and native.stats.crit_percent==.5 and native.stats.expertise==1.2)
assert(native.stats.weapon_damage==1 and not native.stats.hit_rating and #native.effects==0)
'''
        result = subprocess.run([lua, "-"], input=code, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

