import copy
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.forever_comparison import comparison_document, comparison_facts, compile_comparison_data
from tools.forever_scoring import compile_model, pack_item, read_model, review_issues, scoring_audit, swap_score
from tools.generate_lua import lua_value
from tools.project import ADDON_DIR, dataset_json


class ForeverScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.snapshot = read_model()
        cls.runtime, cls.bindings = compile_model(cls.model, cls.snapshot)
        cls.lua = find_lua51()

    def lua_run(self, code):
        if not self.lua:
            self.skipTest("Lua 5.1 executable unavailable")
        result = subprocess.run([self.lua, "-"], input=code, cwd=ADDON_DIR, encoding="utf-8",
                                capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_rank_facts_and_reviewed_contexts(self):
        self.assertEqual(self.snapshot["client_build"], "1.60.1.70959")
        self.assertEqual(self.snapshot["ability_triggers"]["20425"]["activates"], ["melee_on_hit"])
        self.assertEqual(self.snapshot["enchants"]["1891"]["stats"]["intellect"], 4)
        self.assertEqual([row["value"] for row in self.snapshot["traits"]["137880"]["effects"][0]["ranks"]],
                         [12, 24, 36, 48, 60])
        self.assertEqual([row["value"] for row in self.snapshot["traits"]["129415"]["effects"][0]["ranks"]],
                         [33, 66, 100])
        mental_quickness = self.snapshot["traits"]["129404"]
        self.assertEqual(mental_quickness["spell_id"], 30812)
        self.assertEqual([[rank["value"] for rank in effect["ranks"]] for effect in mental_quickness["effects"]],
                         [[15, 30], [15, 30]])
        audit = scoring_audit()
        self.assertTrue(audit["ok"], audit["issues"])
        self.assertIn("Paladin/Protection", audit["scoring_profiles"])
        self.assertEqual(len(audit["scoring_profiles"]), 5)
        self.assertEqual(len(audit["scoring_profiles"]) + len(audit["reference_profiles"]), 28)
        self.assertEqual(len(self.bindings), 10)

    def test_new_client_approval_requires_the_compared_equipment_rules(self):
        rules = dataset_json("forever", "leveling_rules")
        rules["class_equipment"]["Paladin"]["armor_tiers"][0]["types"].append("Plate")
        with self.assertRaisesRegex(ValueError, "current equipment comparison"):
            compile_model(self.model, self.snapshot, {"leveling_rules": rules})

    def test_reference_catalog_requires_consistent_equipment_facts(self):
        tooltip = {"id": 100, "name": "Charm", "slot": "Trinket", "required_level": 20,
                   "stats": {"stamina": 8}, "parse_confidence": "tooltip", "use_effects": ["Use: A burst of light."]}
        observations = {}
        for url, item in (("one", tooltip), ("two", {**tooltip, "stats": {"stamina": 9}})):
            observations[url] = {"page_type": "item", "item_id": 100, "item_kind": "equipment", "item_stats": item}
        self.assertEqual(comparison_document(observations)["items"], [])
        imported = comparison_document({"one": observations["one"]})["items"][0]
        self.assertEqual(imported["stats"], {"stamina": 8.0})
        self.assertEqual(imported["effects"], ["Use: A burst of light."])
        self.assertEqual(imported["evidence"]["url"], "one")
        self.assertIsNone(comparison_facts({**tooltip, "stats": {"stamina": "8"}}))
        self.assertIsNone(comparison_facts({**tooltip, "slot": "Main Hand"}))
        self.assertIsNone(comparison_facts({**tooltip, "stats": {"stamina": True}}))
        compiled = compile_comparison_data([])
        self.assertEqual(len(compiled["profiles"]), 28)
        self.assertGreater(len(compiled["items"]), 3500)
        self.assertTrue(compiled["items"]["11122"][compiled["item_fields"].index("utility")])

    def test_stat_ranks_share_ties_and_respect_the_other_slot(self):
        self.lua_run(r'''
BigBiSList = {
    GetPlayerRaceName = function() return "Human" end,
    GetAvailabilityPhaseIndex = function() return 1 end,
    ComparisonItemInScope = function(_, id) return id ~= 105 end,
}
local weights = {stamina = 1, dodge_percent = 4}
BigBiSListData = {stat_rank = {
    version = "forever-stat-ranks-1", equipment = {Paladin = {}}, common_slots = {"Ring"},
    profiles = {["Paladin/Protection"] = {leveling = {slots = {}, weights = {{1, 59, weights}}}}},
    item_fields = {"id", "name", "slot", "level", "stats", "max_equipped", "unique_group", "classes", "effects"},
    items = {
        ["100"] = {100, "Worn", "Ring", 40, {stamina = 8}},
        ["101"] = {101, "Tied", "Ring", 40, {stamina = 8}},
        ["102"] = {102, "Unique", "Ring", 40, {stamina = 12}, 1, "Test"},
        ["103"] = {103, "Similar unique", "Ring", 40, {stamina = 15}, 1, "Test"},
        ["104"] = {104, "Too high", "Ring", 59, {stamina = 22}},
        ["105"] = {105, "Future", "Ring", 40, {stamina = 20}},
        ["106"] = {106, "Other class", "Ring", 40, {stamina = 21}, nil, nil, {"Warrior"}},
        ["107"] = {107, "Low", "Ring", 40, {stamina = 2}, nil, nil, nil, {"Use: Some effect"}},
    },
}}
dofile("ForeverGearRating.lua")
local service = BigBiSList.ForeverGearRating
local worn = {item_id = 100, item_link = "item:100"}
local unique = {item_id = 102, item_link = "item:102"}
local link = "item:109:567:888:0:0:0:-3:99:47:0:0:0:1:77"
GetItemInfo = function() return "Real suffix", nil, 2, 45, 40 end
GetItemInfoInstant = function() return 109, "Armor", "Misc", "INVTYPE_FINGER", nil, 4, 0 end
GetItemStats = function(actual)
    assert(actual == "item:109:0:0:0:0:0:-3:99:47:0:0:0:1:77")
    return {ITEM_MOD_STAMINA_SHORT = 4, ITEM_MOD_DODGE_RATING_SHORT = 12}
end
C_TooltipInfo = {GetHyperlink = function() return {lines = {
    {leftText = "Equip: Improves your chance to dodge by 1%."},
    {leftText = "Use: Restores a resource."},
}} end}
local owned = {equippedSlots = {Finger0 = worn, Finger1 = unique}, gearStatLinks = {
    [link] = {item_id = 109, item_link = link, state = "bag"},
}}
local context = service:GetContext("Paladin", "Protection", "LEVELING", 47, owned)
local pool = service:GetPlacement(context, "Finger0", {"Ring"})
assert(service:GetPlacement(context, "Finger0", {"Ring"}) == pool)
assert(pool.reference.rank == 1 and pool.reference.total == 4)
assert(pool.rows[1].rank == 1 and pool.rows[2].rank == 1 and pool.rows[3].rank == 1 and pool.rows[4].rank == 4)
local rolled
for _, entry in ipairs(pool.rows) do if entry.item.id == 109 then rolled = entry end end
assert(rolled.score == 8 and rolled.item.effects[1] == "Use: Restores a resource.")
assert(service:GetPlacement(context, "Finger1", {"Ring"}).rows[1].item.id == 103)
local slots = { {key = "Finger0", slots = {"Ring"}}, {key = "Finger1", slots = {"Ring"}} }
local outfit = service:GetGearScore(context, slots)
assert(outfit.score == 20 and outfit.best == 23 and outfit.percent == 86 and outfit.covered == 2)
assert(outfit.tier.label == "Near best" and service:GetGearScore(context, slots) == outfit)
local unknown = service:GetContext("Paladin", "Protection", "LEVELING", 47,
    {equippedSlots = {Finger0 = worn}, unreadableEquipmentSlots = {Finger1 = true}})
local partial = service:GetGearScore(unknown, slots)
assert(partial.partial == 1 and partial.covered == 1 and partial.best == 15 and partial.score == 8)
local preview = service:GetContext("Paladin", "Protection", "LEVELING", 59, owned)
assert(service:GetPlacement(preview, "Finger0", {"Ring"}).rows[1].item.id == 104)
''')

    def test_retribution_ring_swap_scores_passive_spell_power_and_filters_sidegrades(self):
        self.lua_run(r'''
BigBiSList = {
    GetPlayerRaceName = function() return "Human" end,
    GetAvailabilityPhaseIndex = function() return 1 end,
    GetEquipmentSlotDefinitions = function()
        return {
            {key = "Finger0", inventorySlotId = 11, label = "Finger 1", slots = {"Ring"}},
            {key = "Finger1", inventorySlotId = 12, label = "Finger 2", slots = {"Ring"}},
        }
    end,
}
BigBiSListData = {stat_rank = {
    version = "forever-stat-ranks-1", equipment = {Paladin = {}}, common_slots = {"Ring"},
    profiles = {["Paladin/Retribution"] = {role = "damage", leveling = {slots = {}, weights = {
        {1, 59, {stamina = 0.2, spell_power = 0.65, intellect = 0.5}},
    }}}},
    item_fields = {"id", "name", "slot", "level", "stats"},
    items = {["274642"] = {274642, "Blood Ritual Ring", "Ring", 43, {stamina = 13, defense = 3}}},
}}
local nativeSpellPower
GetItemInfo = function() return "Purified Ring", "item:270081", 3, 44, 0 end
GetItemInfoInstant = function() return 270081, "Armor", "Miscellaneous", "INVTYPE_FINGER", nil, 4, 0 end
GetItemStats = function() return {ITEM_MOD_INTELLECT_SHORT = 12, ITEM_MOD_SPELL_POWER_SHORT = nativeSpellPower} end
local effect = "Equip: Increases damage and healing done by magical spells and effects by up to 5."
C_TooltipInfo = {GetHyperlink = function() return {lines = {{leftText = effect}, {leftText = effect}}} end}
dofile("ForeverGearRating.lua")
local rating = BigBiSList.ForeverGearRating
local owned = {equippedSlots = {Finger1 = {item_id = 270081, item_link = "item:270081"}}}
local blood = rating:GetPublishedFacts("274642")
local function verifySwap()
    local context = rating:GetContext("Paladin", "Retribution", "LEVELING", 48, owned)
    local comparison = rating:GetGuideSwap(context, blood, "Finger1")
    assert(math.abs(comparison.delta + 6.65) < 0.001 and comparison.roleDelta == -9.25)
    assert(not rating:IsMeaningfulOwnedUpgrade(comparison))
end
verifySwap()
nativeSpellPower = 5
rating:InvalidateItem(270081)
verifySwap()
assert(not rating:IsMeaningfulOwnedUpgrade({delta = 3, roleDelta = 1, roleDisplaced = 10}))
assert(not rating:IsMeaningfulOwnedUpgrade({delta = 4, roleDelta = 4, roleDisplaced = 100}))
assert(rating:IsMeaningfulOwnedUpgrade({delta = 5, roleDelta = 5, roleDisplaced = 100}))
assert(rating:IsMeaningfulOwnedUpgrade({delta = 0.06, roleDelta = 0.06, status = "empty"}))
''')

    def test_stat_rank_tiers_use_the_best_legal_score_and_inclusive_cutoffs(self):
        self.lua_run(r'''
BigBiSList = {
    GetPlayerRaceName = function() return "Human" end,
    GetAvailabilityPhaseIndex = function() return 1 end,
}
local items = {}
local cases = {
    {13.25, 100, "Top tier", 5}, {13.25, 100, "Top tier", 5},
    {12.8525, 97, "Top tier", 5}, {12.8524, 96, "Near best", 4},
    {11.2625, 85, "Near best", 4}, {11.2624, 84, "Strong", 3},
    {9.275, 70, "Strong", 3}, {9.2749, 69, "Solid", 2},
    {6.625, 50, "Solid", 2}, {6.6249, 49, "Modest", 1},
    {3.3125, 25, "Modest", 1}, {3.3124, 24, "Low", 0},
    {0, 0, "Low", 0},
}
for index, case in ipairs(cases) do
    items[tostring(index)] = {index, "Item " .. index, "Head", 30, {stamina = case[1]}}
end
items["20"] = {20, "Future item", "Head", 50, {stamina = 250}}
items["21"] = {21, "Only option", "Neck", 30, {stamina = 5}}
items["22"] = {22, "Zero score", "Back", 30, {stamina = 0}}
items["23"] = {23, "Negative score", "Back", 30, {stamina = -2}}
items["24"] = {24, "Utility", "Trinket", 30, {}, nil, true}
items["25"] = {25, "Effect", "Trinket", 30, {}, {"Use: A burst of light."}}
BigBiSListData = {stat_rank = {
    version = "forever-stat-ranks-1", equipment = {Paladin = {}},
    common_slots = {"Head", "Neck", "Back", "Trinket"},
    profiles = {["Paladin/Protection"] = {leveling = {slots = {}, weights = {{1, 59, {stamina = 1}}}}}},
    item_fields = {"id", "name", "slot", "level", "stats", "effects", "utility"}, items = items,
}}
dofile("ForeverGearRating.lua")
local rating = BigBiSList.ForeverGearRating
local context = rating:GetContext("Paladin", "Protection", "LEVELING", 47, {equippedSlots = {}})
local head = rating:GetPlacement(context, "Head", {"Head"})
for _, entry in ipairs(head.rows) do
    local case = cases[entry.item.id]
    assert(entry.score_percent == case[2] and entry.tier.label == case[3] and entry.tier.quality == case[4])
    assert(entry.total == #cases and entry.rank == (entry.item.id <= 2 and 1 or entry.item.id))
end
assert(rating:Label(head.rows[1]) == "Top tier · #1 / 13")
assert(rating:Label(head.rows[1], "compact") == "Top tier #1/13")
assert(rating:Label(head.rows[1], "stacked") == "Top tier\n#1 / 13")
local summary = rating:DescriptionLines(head.rows[7])
assert(summary[1] == "Strong · #7 / 13" and summary[2] == "Protection · Level 47")
assert(summary[3] == "70% of the best known stat score")
local only = rating:GetPlacement(context, "Neck", {"Neck"}).rows[1]
assert(not only.tier and not only.score_percent and rating:Label(only) == "5.0 pts")
for _, entry in ipairs(rating:GetPlacement(context, "Back", {"Back"}).rows) do
    assert(not entry.tier and not entry.score_percent and rating:Label(entry):find("Rank", 1, true))
end
for _, entry in ipairs(rating:GetPlacement(context, "Trinket0", {"Trinket"}).rows) do
    assert(not entry.tier and not entry.score_percent)
    assert(rating:Label(entry) == (entry.item.id == 24 and "Utility" or "Effect only"))
end
assert(rating:Label({status = "loading"}) == "Loading stats")
assert(rating:Label(nil) == "Stats unavailable")
''')

    def test_small_pools_spread_colors_and_keep_measured_placements(self):
        self.lua_run(r'''
BigBiSList = {
    GetPlayerRaceName = function() return "Human" end,
    GetAvailabilityPhaseIndex = function() return 1 end,
    GetEquipmentSlotDefinitions = function() return {{key = "Neck", label = "Neck", slots = {"Neck"}}} end,
}
local items = {}
local function add(slot, scores)
    for index, score in ipairs(scores) do
        local id = slot .. index
        items[id] = {id, id, slot, 1, {stamina = score}}
    end
end
add("Head", {100, 98, 96, 94, 92, 90})
add("Chest", {100, 99.75, 99.75, 99, 80, 20})
add("Hands", {100, 98, 96, 94, 92, 90, 88})
add("Neck", {100, 98, 96, 94, 90})
add("Back", {2, 1.95})
BigBiSListData = {stat_rank = {
    version = "forever-stat-ranks-1", equipment = {Paladin = {}},
    common_slots = {"Head", "Chest", "Hands", "Neck", "Back"},
    profiles = {["Paladin/Protection"] = {leveling = {slots = {}, weights = {{1, 59, {stamina = 1}}}}}},
    item_fields = {"id", "name", "slot", "level", "stats"}, items = items,
}}
dofile("ForeverGearRating.lua")
local rating = BigBiSList.ForeverGearRating
local context = rating:GetContext("Paladin", "Protection", "LEVELING", 47, {})
local function pool(slot) return rating:GetPlacement(context, slot, {slot}) end
for index, row in ipairs(pool("Head").rows) do
    assert(row.tier.quality == 6 - index and row.placement_color)
    assert(row.rank == index and row.total == 6 and row.score_percent == 102 - 2 * index)
end
local rows = pool("Chest").rows
assert(rows[1].tier == rows[2].tier and rows[2].tier == rows[3].tier)
assert(rows[2].rank == 2 and rows[3].rank == 2 and rows[4].rank == 4)
assert(rows[1].tier ~= rows[4].tier and rows[2].score_percent == 99)
assert(pool("Back").rows[2].tier.quality == 5 and pool("Back").rows[2].score_percent == 97)
assert(not pool("Hands").rows[2].placement_color and pool("Hands").rows[2].tier.quality == 5)
local neck = pool("Neck")
local projected = rating:CompareTooltipItem(context, {key = "new necklace", item_link = "item:9990",
    facts = {key = "new necklace", id = 9990, slot = "Neck", level = 1, stats = {stamina = 92}},
    entry = {item_id = 9990}}, true)
assert(projected.placement.rank == 5 and projected.placement.total == 6 and projected.placement.tier.quality == 1)
assert(projected.placement.score_percent == 92 and projected.placement.placement_color)
assert(pool("Neck") == neck and neck.count == 5 and not neck.byVariant["new necklace"])
assert(rating:DescriptionLines(projected.placement)[4] == "Color uses placement in this slot")
''')

    def test_changed_mechanics_reopen_approvals(self):
        updated = copy.deepcopy(self.snapshot)
        updated["traits"]["137880"]["effects"][0]["ranks"][0]["value"] = 15
        _, bindings = compile_model(self.model, updated)
        changed = {key for key in self.bindings if self.bindings[key] != bindings[key]}
        self.assertEqual(changed, {"Paladin/Retribution/leveling", "Paladin/Retribution/pre_raid"})
        self.assertTrue(review_issues(self.model, updated, bindings))

    def test_python_and_lua_share_loadout_fixtures(self):
        ret = self.runtime["profiles"]["Paladin/Retribution"]["operations"]
        enhancement = self.runtime["profiles"]["Shaman/Enhancement"]["operations"]
        warrior = self.runtime["profiles"]["Warrior/Protection"]["operations"]
        item = {"stats": {"intellect": 10}}
        enhancement_weights = {"intellect": 0.5, "attack_power": 1, "spell_damage": 1, "healing_power": 0.5}
        enhancement_ranks = {129416: 5, 129415: 2}
        support = {"stats": {"intellect": 20}, "set_id": 14}
        other = {"stats": {"intellect": 20, "hit_percent": 1}, "set_id": 14, "procs": [
            {"trigger": "melee_on_hit", "chance": 0.25, "duration": 6, "stats": {"attack_power": 40}}]}
        fixtures = [
            ([item], {"intellect": 0.5, "spell_damage": 1}, ret, {137880: 0}, {}, 5),
            ([item], {"intellect": 0.5, "spell_damage": 1}, ret, {137880: 2}, {}, 7.4),
            ([item], enhancement_weights, enhancement, {**enhancement_ranks, 129404: 0}, {}, 12.76),
            ([item], enhancement_weights, enhancement, {**enhancement_ranks, 129404: 1}, {}, 15.235),
            ([item], enhancement_weights, enhancement, {**enhancement_ranks, 129404: 2}, {}, 17.71),
            ([{"stats": {"dps": 10}}, {"stats": {}, "shield": True}], {"dps": 1},
             warrior, {137848: 3}, {}, 12),
            ([{"stats": {"dps": 10}}], {"dps": 1}, warrior, {137848: 3}, {}, 10),
            ([support, other], {"attack_power": 1, "spell_damage": 1, "hit_percent": 5}, ret, {137880: 5},
             {"caps": {"hit_percent": 2}, "events_per_minute": {"melee_on_hit": 12},
              "sets": [{"set_id": 14, "pieces": 2, "stats": {"hit_percent": 2}}]}, 46),
        ]
        for loadout, weights, operations, ranks, scenario, expected in fixtures:
            actual, _ = swap_score(loadout, weights, operations, ranks, scenario)
            self.assertAlmostEqual(actual, expected)
        self.lua_run("local fixtures = " + lua_value([list(case) for case in fixtures]) + r'''
BigBiSList = {}
dofile("ForeverScoring.lua")
for _, case in ipairs(fixtures) do
    local value = BigBiSList.ForeverScoring.ScoreLoadout(case[1], case[2], case[3], case[4], case[5])
    assert(math.abs(value - case[6]) < 1e-8, value)
end
''')

    def test_ranged_damage_is_separate_from_scalable_melee_damage(self):
        bow = pack_item({"id": 1, "name": "Bow", "slot": "Ranged", "weapon_subtype": "Bow", "dps": 30})
        wand = pack_item({"id": 2, "name": "Wand", "slot": "Ranged", "weapon_subtype": "Wand", "dps": 20})
        self.assertEqual(bow["stats"], {"ranged_dps": 30})
        self.assertEqual(wand["stats"], {"wand_dps": 20})
        sword, shield = {"stats": {"dps": 10}}, {"stats": {}, "shield": True}
        weights = {"dps": 3}
        operations = self.runtime["profiles"]["Warrior/Protection"]["operations"]
        ranks = {137848: 3}
        base, _ = swap_score([sword, shield], weights, operations, ranks, {})
        ranged, _ = swap_score([sword, shield, bow], weights, operations, ranks, {})
        self.assertEqual(base, ranged)

    def test_shield_benchmark_hit_cap_and_flat_set_and_racial_bonus(self):
        warrior = self.runtime["profiles"]["Warrior/Protection"]
        scenario = warrior["scenarios"]["pre_raid"]
        weights = scenario["weights"][0][2]
        pieces = [self.runtime["items"]["pre_raid"][str(item)] for item in (16731, 16733, 16734)]
        carried = [{"stats": {"hit_percent": 7.5}, "shield": True}, *pieces[:2]]
        third = pieces[2]
        measured = []
        for hit in (0, 1, 2):
            loadout = [*carried, third, {"stats": {"hit_percent": hit, "attack_power": 14, "spirit": 10}}]
            score, _ = swap_score(loadout, weights, warrior["operations"], {137848: 3}, scenario, race_id=1)
            measured.append((loadout, score))
        self.assertAlmostEqual(measured[1][1] - measured[0][1], 2.5)
        self.assertAlmostEqual(measured[2][1], measured[1][1])
        self.assertGreater(swap_score([*pieces, {"stats": {}, "shield": True}], weights, warrior["operations"],
                                      {137848: 3}, scenario)[0],
                           swap_score([*pieces[:2], {"stats": third["stats"]}, {"stats": {}, "shield": True}],
                                      weights, warrior["operations"], {137848: 3}, scenario)[0])
        racial = {"racial_scaling": scenario["racial_scaling"]}
        spirit = [{"stats": {"spirit": 10}}]
        self.assertAlmostEqual(swap_score(spirit, {"spirit": 1}, [], {}, racial, race_id=1)[0], 11)
        self.assertAlmostEqual(swap_score(spirit, {"spirit": 1}, [], {}, racial, race_id=2)[0], 10)
        self.lua_run("local fixture = " + lua_value([measured[1][0], weights, warrior["operations"], {137848: 3},
                                                     scenario, measured[1][1], racial]) + r'''
BigBiSList = {}
dofile("ForeverScoring.lua")
local score = BigBiSList.ForeverScoring.ScoreLoadout
assert(math.abs(score(fixture[1], fixture[2], fixture[3], fixture[4], fixture[5], 1) - fixture[6]) < 1e-8)
assert(score({{stats = {spirit = 10}}}, {spirit = 1}, {}, {}, fixture[7], 1) == 11)
assert(score({{stats = {spirit = 10}}}, {spirit = 1}, {}, {}, fixture[7], 2) == 10)
''')

    def test_ring_ranks_use_one_baseline_and_choose_a_legal_swap(self):
        self.lua_run(r'''
BigBiSList = {}
dofile("ForeverScoring.lua")
dofile("DataIndex.lua")
local scoring = BigBiSList.ForeverScoring
local worn = {id = 1, name = "Worn unique", item_level = 1, unique_group = "unique", stats = {stamina = 10}}
local weak = {id = 2, name = "Worn weak", item_level = 1, stats = {stamina = 2}}
local upgrade = {id = 3, name = "Upgrade", item_level = 1, stats = {stamina = 8}}
local alternative = {id = 4, name = "Shared group", item_level = 1, unique_group = "unique", stats = {stamina = 12}}
local access = {[1] = {{1, 59}}}
local state = {gear = {[11] = worn, [12] = weak}, weights = {stamina = 1}, ranks = {},
    race = 1, level = 42, items = {worn, weak, upgrade, alternative}, profile = {operations = {}},
    scenario = {pools = {Ring = {{1, access}, {2, access}, {3, access}, {4, access}}}}, slots = {}}
local ranked = scoring:RankSlot(state, "Ring")
assert(ranked.selected[1].item.id == 3 and ranked.selected[1].target == 12)
assert(ranked.byIdentity["1"].score == 2)
assert(ranked.byIdentity["4"].target == 11 and ranked.byIdentity["4"].score == 4)
assert(scoring:Compare(state, "Ring", 3, 2) == 6)
function scoring:GetContext() return state end
local function compare(id, reference, inventorySlot)
    return BigBiSList:CompareRecommendationItems(id, reference, "Paladin", "Retribution", "PR", "Ring",
        {inventorySlotId = inventorySlot, item_link = "item:" .. reference .. ":0"})
end
assert(compare(3, 1, 11).score_delta == -2)
assert(compare(3, 2, 12).score_delta == 6)
assert(compare(4, 2, 12).relation == "unranked")

local suffix = {id = 3, variant_id = "3:-9", name = "Upgrade of Stamina", item_level = 1, stats = {stamina = 11}}
state.items[suffix.variant_id] = suffix
table.insert(state.scenario.pools.Ring, {suffix.variant_id, access})
state.slots = {}
local row = {class = "Paladin", spec = "Retribution", slot = "Ring", level_min = 42,
    item_id = 3, variant_id = suffix.variant_id, scoring_basis = "active_build"}
assert(BigBiSList:GetLevelingEquipmentComparison(row) == "Compared with equipped gear +9.00")
assert(BigBiSList:GetLevelingEquipmentComparison(row, {slot = "Finger 1", inventorySlotId = 11,
    item_id = 1, item_link = "item:1:0"}) == "Compared with Finger 1 +1.00")
assert(BigBiSList:GetLevelingEquipmentComparison(row, {slot = "Finger 2", inventorySlotId = 12,
    item_id = 2, item_link = "item:2:0"}) == "Compared with Finger 2 +9.00")
assert(not BigBiSList:GetLevelingEquipmentComparison(row, {slot = "Finger 2", inventorySlotId = 12,
    item_id = 2, item_link = "item:2:0:0:0:0:0:-9"}), "comparison must match the equipped suffix")
assert(not BigBiSList:GetLevelingEquipmentComparison(row, {slot = "Finger 2", inventorySlotId = 12}),
    "an empty pin must not fall back to another slot")
''')

    def test_rank_reversal_eligibility_preview_and_equipment_pair(self):
        self.lua_run(r'''
BigBiSList = {DetectPlayerClass = function() return "Paladin" end,
    DetectPlayerSpec = function() return "Retribution" end,
    GetPlayerFactionName = function() return "Horde" end}
local character = {leveling = {}}
function BigBiSList:GetCharacterDB() return character end
local level, build, rank, config, faction = 44, "70938", 0, 8, "Horde"
function GetBuildInfo() return "1.60.1", build end
function UnitLevel() return level end
function UnitRace() return "Skyborne", "Skyborne", 96 end
C_ClassTalents = {GetActiveConfigID = function() return config end}
C_Traits = {
    GetConfigInfo = function() return {treeIDs = {1}} end,
    GetNodeInfo = function() return {entryIDs = {10}, activeEntry = {entryID = 10, rank = rank}} end,
    GetDefinitionInfo = function() return {spellID = 30} end,
}
function GetInventoryItemID(_, slot) return slot == 16 and 11 or slot == 17 and 12 or nil end
local suffix
function GetInventoryItemLink(_, slot)
    if slot == 16 and suffix then return "item:11:0:0:0:0:0:" .. suffix end
    return "item:" .. (slot == 16 and 11 or 12) .. ":0"
end
local items = {}
local function item(id, stats, slot, shield)
    items[tostring(id)] = { id = id, name = tostring(id), stats = stats, item_level = 1, slot = slot, shield = shield }
end
item(1, {strength = 10}, "Ring")
item(2, {strength = 9}, "Ring")
item(3, {strength = 8}, "Ring")
item(4, {intellect = 10}, "Ring")
item(5, {strength = 100}, "Ring")
item(6, {strength = 100}, "Ring")
item(11, {strength = 10}, "One Hand")
item(12, {strength = 10}, "Off Hand", true)
item(13, {strength = 18}, "Two Hand")
local horde = {[96] = {{1, 59}}}
local alliance = {[95] = {{1, 59}}}
local scenario = {personas = {[96] = {"Skyborne", faction}},
    weights = {{1, 59, {intellect = 0.5, strength = 1, spell_damage = 1}}},
    pools = {
        Ring = {{"1",horde},{"2",horde},{"3",horde},{"4",horde},{"5",alliance},{"6",{[96] = {{45,59}}}}},
        ["Two Hand"] = {{"13",horde}},
    }}
BigBiSListData = {character_scoring = {version = "forever-character-scoring-1", build = 70938,
    items = {leveling = items, pre_raid = {}}, traits = {[10] = {node_id = 20, definition_id = 21,
        max_rank = 5, spell_id = 30, tree_id = 1}},
    profiles = {["Paladin/Retribution"] = {entries = {10}, scenarios = {leveling = scenario},
        operations = {{entry = 10, kind = "convert", from_stat = "intellect", stats = {"spell_damage"},
            factors = {0.12,0.24,0.36,0.48,0.60}, name = "Champion of the Light"}}}}}}
dofile("ForeverScoring.lua")
local scoring = BigBiSList.ForeverScoring
local function context(expectedLevel) return scoring:GetContext("Paladin", "Retribution", "leveling", expectedLevel or level) end
local initial = context()
local before = scoring:RankSlot(initial, "Ring")
assert(#before.all == 4 and before.selected[1].item.id == 1 and #before.selected == 3)
assert(before.all[4].item.id == 4)
rank = 5
assert(context() == initial)
scoring:Invalidate()
local state = context()
assert(state ~= initial)
local revised = scoring:RankSlot(state, "Ring")
assert(revised.selected[1].item.id == 4 and revised.selected[1].effects[10] > 0)
local delta = scoring:Compare(state, "Two Hand", 13, 11)
assert(delta == -2, delta)
character.leveling.manualLevel = true
assert(not context())
character.leveling.manualLevel = false
assert(not context(45))
build = "70939"
assert(not context())
build = "70938"
C_Item = {
    GetItemStats = function() return {ITEM_MOD_DAMAGE_PER_SECOND_SHORT = 15} end,
    GetItemInfoInstant = function() return 11, "Weapon", "Sword", "INVTYPE_WEAPON", 1, 2, 7 end,
}
suffix = -9
scoring:Invalidate()
assert(not context())
suffix = nil
rank = nil
scoring:Invalidate()
assert(not context())
''')

    def test_populated_guide_is_stable_and_live_comparisons_remain_available(self):
        self.lua_run(r'''
dofile("DataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")
local reviewedBuild = tostring(BigBiSListData.character_scoring.build)
local build, rank, level = reviewedBuild, 3, 44
function GetBuildInfo() return "1.60.1", build end
function UnitLevel() return level end
function UnitRace() return "Human", "Human", 1 end
function UnitFactionGroup() return "Alliance" end
function UnitClass() return "Paladin", "PALADIN" end
function GetInventoryItemID() return nil end
function GetInventoryItemLink() return nil end
C_ClassTalents = {GetActiveConfigID = function() return 1 end}
C_Traits = {
    GetConfigInfo = function() return {treeIDs = {1100}} end,
    GetGroupDisplayInfoByTreeID = function() return {{groupID = 1, displayName = "Retribution"}} end,
    GetGroupCurrencyInfo = function() return {{traitNodeGroupID = 1, currencyInfos = {{spent = 31}}}} end,
    GetNodeInfo = function(_, node)
        local trait = node == 110882 and 137880 or 130425
        return {entryIDs = {trait}, activeEntry = {entryID = trait, rank = node == 110882 and rank or 1}}
    end,
    GetDefinitionInfo = function(id)
        return {spellID = id == 142634 and 1311084 or 20375}
    end,
}
local addon = BigBiSList
local gear = addon:GetLevelingRows("Paladin", "Retribution", 44, {})
assert(#gear > 10)
local scoring = assert(addon.ForeverScoring:GetContext("Paladin", "Retribution", "leveling", 44))
assert(#addon.ForeverScoring:RankSlot(scoring, "Head").selected > 0)
build = tostring(tonumber(reviewedBuild) + 1)
local fallback = addon:GetLevelingRows("Paladin", "Retribution", 44, {})
assert(#fallback == #gear and fallback[1].items[1].item_id == gear[1].items[1].item_id)
assert(fallback[1].items[1].stat_rank == gear[1].items[1].stat_rank)
local shoulder
for _, group in ipairs(addon:GetLevelingRows("Paladin", "Retribution", 48, {slots = {Shoulder = true}})) do
    for _, row in ipairs(group.items) do
        if row.item_id == 9476 then shoulder = row end
    end
end
assert(shoulder and shoulder.stat_rank.rank and shoulder.matched_access_option.source.entity_id == 7267)
local guideContext = addon.ForeverGearRating:GetGuideContext("Paladin", "Retribution", "LEVELING", 48, "Human", "Alliance")
local pool = addon.ForeverGearRating:GetGuidePlacement(guideContext, "Shoulder")
assert(pool.byVariant["9476"].score > pool.byVariant["9411"].score)
assert(guideContext.weights.intellect == 0.5 and guideContext.weights.spell_power == 0.65)
build, level = reviewedBuild, 60
local phaseRows = addon:GetPhaseRows("Paladin", "Retribution", "PR", {})
assert(#phaseRows > 10 and not phaseRows[1].items[1].scoring_basis)
local plannerRows = addon:GetPlannerRows("Paladin", "Retribution", "PR", {})
assert(#plannerRows > 0 and not plannerRows[1].bestUse.scoring_basis)
level = 14
local early = addon:GetLevelingRows("Warrior", "Arms", 14, {race = "Human", faction = "Alliance"})
assert(#early >= 13)
assert(addon:GetLevelingSlotStatus("Warrior", "Arms", 14, "Shoulder",
    {race = "Human", faction = "Alliance"}).state == "unreviewed")

level = 42
local ranks = {[130026] = 0, [141292] = 0, [130354] = 0, [137872] = 0}
local nodes, definitions = {}, {}
local function setTalentTree(tree, spec)
    nodes, definitions = {}, {}
    for entry, trait in pairs(BigBiSListData.character_scoring.traits) do
        if ranks[tonumber(entry)] then
            nodes[trait.node_id] = tonumber(entry)
            definitions[trait.definition_id] = trait.spell_id
        end
    end
    C_Traits.GetConfigInfo = function() return {treeIDs = {tree}} end
    C_Traits.GetGroupDisplayInfoByTreeID = function() return {{groupID = 1, displayName = spec}} end
    C_Traits.GetNodeInfo = function(_, node)
        local entry = assert(nodes[node])
        local active = ranks[entry] > 0 and {entryID = entry, rank = ranks[entry]} or nil
        return {entryIDs = {entry}, activeEntry = active}
    end
    C_Traits.GetDefinitionInfo = function(id) return {spellID = definitions[id]} end
    addon.ForeverScoring:Invalidate()
end
setTalentTree(1100, "Protection")
local function firstHeadPick()
    local context = assert(addon.ForeverScoring:GetContext("Paladin", "Protection", "leveling", 42))
    return addon.ForeverScoring:RankSlot(context, "Head").selected[1].item.id
end
assert(firstHeadPick() == 287011) -- Guise of Battle
ranks[130354] = 2
addon.ForeverScoring:Invalidate()
assert(firstHeadPick() == 10763) -- Icemetal Barbute

function UnitClass() return "Shaman", "SHAMAN" end
function UnitRace() return "Orc", "Orc", 2 end
function UnitFactionGroup() return "Horde" end
ranks = {[129416] = 5, [129415] = 3, [129404] = 0}
setTalentTree(1082, "Enhancement")
local function thirdWristPick()
    local context = assert(addon.ForeverScoring:GetContext("Shaman", "Enhancement", "leveling", 42))
    return addon.ForeverScoring:RankSlot(context, "Wrist").selected[3].item.id
end
assert(thirdWristPick() == 2868) -- Patterned Bronze Bracers
ranks[129404] = 2
addon.ForeverScoring:Invalidate()
assert(thirdWristPick() == 4796) -- Owl Bracers
''')
