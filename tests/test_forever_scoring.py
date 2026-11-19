import copy
import subprocess
import unittest
from unittest.mock import patch

from tests.test_addon_runtime_lua import find_lua51
from tools.forever_comparison import comparison_document, comparison_facts, compile_comparison_data
from tools.forever_item_effects import effect_rule
from tools.forever_scoring import compile_model, pack_item, read_model, refresh_review_scope, review_issues, scoring_audit, swap_score
from tools.generate_lua import lua_value
from tools.project import ADDON_DIR, dataset_json
from tools.recommend_leveling import materialized_items, roll_identity


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
        self.assertEqual(self.snapshot["ability_triggers"]["408498"]["ppm"], [6, 7, 8, 9, 10])
        self.assertEqual(self.snapshot["ability_triggers"]["408498"]["speed_slot"], 16)
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
        self.assertEqual(len(audit["scoring_profiles"]), 28)
        self.assertEqual(audit["reference_profiles"], [])
        self.assertEqual(len(self.bindings), 56)
        release = scoring_audit(strict=True, lua=self.lua)
        self.assertEqual(release["required_contexts"], 56)
        self.assertEqual(release["missing_contexts"], [])
        if self.lua:
            self.assertTrue(release["ok"], release["issues"])
            self.assertEqual(release["issues"], [])
            self.assertEqual(len(release["validated_contexts"]), 56)

    def test_new_client_approval_requires_the_compared_equipment_rules(self):
        rules = dataset_json("forever", "leveling_rules")
        rules["class_equipment"]["Paladin"]["armor_tiers"][0]["types"].append("Plate")
        with self.assertRaisesRegex(ValueError, "current equipment comparison"):
            compile_model(self.model, self.snapshot, {"leveling_rules": rules})

    def test_pinned_form_and_physical_weapon_contributions(self):
        two_hand = self.runtime["profiles"]["Warrior/Arms"]["operations"]
        offhand = self.runtime["profiles"]["Rogue/Combat"]["operations"]
        feral = self.runtime["profiles"]["Druid/Feral dps"]["operations"]
        melee = {"dps": 1, "weapon_speed": 2}
        pair = {16: {"stats": {"dps": 24, "weapon_speed": 2.6}, "slot": "Main Hand"},
                17: {"stats": {"dps": 18, "weapon_speed": 1.8}},
                18: {"stats": {"ranged_dps": 41, "weapon_speed": 3.0}}}
        two = {16: {"stats": {"dps": 32, "weapon_speed": 3.6}, "slot": "Two Hand"}, 18: pair[18]}
        feral_gear = {1: {"stats": {"strength": 10, "stamina": 10}}}
        cases = [
            (pair, melee, offhand, {141297: 1}, {"offhand_dps_factor": 0.5}, 60, 40.45),
            (pair, melee, two_hand, {130678: 3}, {"offhand_dps_factor": 0.5}, 60, 38.2),
            (two, melee, two_hand, {130678: 3}, {"offhand_dps_factor": 0.5}, 60, 41.12),
            (feral_gear, {"strength": 1, "stamina": 1}, feral, {129618: 5}, {}, 19, 22),
            (feral_gear, {"strength": 1, "stamina": 1}, feral, {129618: 5}, {}, 20, 21),
        ]
        for gear, weights, operations, ranks, scenario, level, expected in cases:
            ranks = {**dict.fromkeys((row["entry"] for row in operations), 0), **ranks}
            self.assertAlmostEqual(swap_score(gear, weights, operations, ranks, scenario, level=level)[0], expected)
        self.lua_run("BigBiSList = {}\ndofile('ForeverScoring.lua')\nlocal cases = " + lua_value([list(case) for case in cases]) + r'''
local scoring = BigBiSList.ForeverScoring
for _, case in ipairs(cases) do
    local gear = {}
    for index, item in pairs(case[1]) do gear[tonumber(index)] = item end
    local points = scoring.ScoreLoadout(gear, case[2], case[3], case[4], case[5], nil, case[6])
    assert(math.abs(points - case[7]) < 0.0001)
end
local trigger = {ppm = {6, 7, 8, 9, 10}, speed_slot = 16}
local slow, fast = {stats = {weapon_speed = 3.6}}, {stats = {weapon_speed = 2}}
assert(math.abs(scoring.WeaponProcChance(trigger, 5, slow) - 0.60) < 0.0001)
assert(math.abs(scoring.WeaponProcChance(trigger, 5, fast) - 1 / 3) < 0.0001)
assert(math.abs(scoring.WeaponProcChance(trigger, 1, slow) - 0.36) < 0.0001)
assert(scoring.WeaponProcChance(trigger, 0, slow) == nil)
''')

    def test_refresh_reports_the_reviewed_contexts_using_changed_items(self):
        report = refresh_review_scope({9411, 99999999}, [])
        self.assertEqual(report["changed_item_ids"], [9411, 99999999])
        self.assertIn(9411, report["existing_contexts_to_recheck"]["Paladin/Retribution/leveling"])
        self.assertNotIn(99999999, report["existing_contexts_to_recheck"]["Paladin/Retribution/leveling"])

    def test_full_guide_scores_worn_and_unowned_exact_paladin_items(self):
        self.lua_run(r'''
local H = dofile("tests/lua_ui_harness.lua")
H.load("forever")
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
local function guide(spec, level)
    return rating:GetGuideContext("Paladin", spec, level == 60 and "PR" or "LEVELING", level, "Human", "Alliance")
end
local profiles = 0
for key, profile in pairs(BigBiSListData.stat_rank.profiles) do
    profiles = profiles + 1
    local personal = BigBiSListData.character_scoring.profiles[key].scenarios
    local function same(weights, actual)
        for stat, value in pairs(weights) do assert(actual[stat] == value, key .. "/" .. stat) end
        for stat, value in pairs(actual) do assert(weights[stat] == value, key .. "/" .. stat) end
    end
    for index, band in ipairs(profile.leveling.weights) do
        local other = personal.leveling.weights[index]
        assert(band[1] == other[1] and band[2] == other[2])
        same(band[3], other[3])
    end
    same(profile.pre_raid.weights, personal.pre_raid.weights[1][3])
end
assert(profiles == 28)
local pool = rating:GetGuidePlacement(guide("Retribution", 49), "Head")
local raging = assert(pool.byVariant["7719"])
assert(not pool.byVariant["22005"] and not pool.byVariant["22091"])
assert(not pool.byVariant["9479"].source_unknown and addon:GetItemData(9479).primary_source.entity_name == "Chief Ukorz Sandscalp")
local late = rating:GetGuidePlacement(guide("Retribution", 58), "Head")
assert(late.byVariant["22091"] and not late.byVariant["22005"])
local rogue = rating:GetGuideContext("Rogue","Combat","LEVELING",58,"Human","Alliance")
assert(rating:GetGuidePlacement(rogue,"Head").byVariant["22005"])
local questSource = addon:GetItemData(22091).primary_source
assert(questSource.eligibility.min_level == 58 and questSource.quest_id == 9002)
local complete, active = {}, {}
C_QuestLog = {IsQuestFlaggedCompleted=function(id) return complete[id] or false end,
    IsOnQuest=function(id) return active[id] or false end,IsComplete=function(id) return active[id] or false end}
local function nextStep() return addon.UI:GetQuestStepText(addon.UI:GetAcquisitionQuestProgress(questSource)) end
assert(nextStep() == "Requires Back to the Beginning")
complete[8997] = true
assert(nextStep() == "Pick up Saving the Best for Last")
active[9002] = true
assert(nextStep() == "Turn in Saving the Best for Last")
for _, id in ipairs({9479, 8142, 17767, 10008}) do
    local helm = assert(pool.byVariant[tostring(id)])
    assert(helm.rank < raging.rank and helm.total == raging.total)
end
local link = "item:10090::::::::50:1486::1:1:12723:1:28:5253:::::"
local key = rating:NormalizeLink(10090, link)
local helm = assert(pool.byVariant[key])
assert(helm.item.name == "Gothic Plate Helmet of the Gorilla" and helm.item.stats.armor == 362)
assert(helm.item.stats.strength == 13 and helm.item.stats.intellect == 13)
local groups = addon:GetLevelingRows("Paladin", "Retribution", 49, {search = helm.item.name,
    slots = {Head = true}, race = "Human", faction = "Alliance"})
assert(#groups == 1 and #groups[1].items == 1)
local row = groups[1].items[1]
assert(row.stat_rank == helm and row.variant_id == key and row.acquisition_display.source_label == "Source unknown")
assert(#addon:GetLevelingActivityRows(row, {}, 49) == 0)
UnitRace = function() return "Human","Human",1 end
UnitFactionGroup = function() return "Alliance" end
UnitLevel = function() return 49 end
local player = {class="Paladin",spec="Retribution",phase="LEVELING",level=49}
local owned = {equippedSlots={Head={item_id=10090,item_link=link}},gearCopies={}}
local swap = rating:GetLiveLevelingSwap(raging.item, "item:7719", owned, "Head", player, false)
local verdict = rating:LevelingPresentation({item=raging.item,swap=swap,viewedLevel=49,playerLevel=49})
assert(verdict.today == "Slight upgrade" and verdict.evidence == "+2.1 pts vs Gothic Plate Helmet of the Gorilla")
local legacy = {["10090:0:0:1:1:12723:1:28:5253"]={item_id=10090,variant_id="old",item_link=link},["10090"]=true}
addon:NormalizeWishlistVariants(legacy)
assert(legacy[key].variant_id == key and legacy["10090"] and not legacy["10090:0:0:1:1:12723:1:28:5253"])
local prot = guide("Protection", 49)
local function score(id, suffix)
    local facts = rating:GetPublishedFacts(id .. ":0:0:0:1:" .. suffix)
    return rating:GetReferenceCandidate(prot, facts, "Chest").score
end
for _, pair in ipairs({{10086,79.88,83.98}, {14915,87.93,91.88}, {10128,88.65,92.60}}) do
    assert(score(pair[1], 12753) == pair[2] and score(pair[1], 12754) == pair[3])
end
local circlet = rating:GetPublishedFacts("253959")
local at60 = guide("Protection", 60)
assert(rating:GetReferenceCandidate(at60, circlet, "Head").score == 34.9)
local arrow = addon.Widgets:GearAdviceText({today = "Slight upgrade", tone = "gain"})
local clock = addon.Widgets:GearAdviceText({today = "Keep for Level 50", tone = "future"})
assert(arrow:match("^|T.-ui%-icons%.tga:.-|t Slight upgrade$") and clock:match("^|T.-|t Keep for Level 50$"))
assert(arrow:match(":256:256:(.-)|t") ~= clock:match(":256:256:(.-)|t"))
''')

    def test_guide_lead_requires_obtainable_gear_and_resolved_contenders(self):
        self.lua_run(r'''
BigBiSList = {GetAvailabilityPhaseIndex = function() return 1 end,
    IsStatRankGuideItemAvailable = function(_, id) return id ~= 4, id == 4 and "unverified_route" end}
local rows = {["1"]={1,"Leader","Head",1,{stamina=10}}, ["2"]={2,"Peer","Head",1,{stamina=9}}}
local data = {version="forever-stat-ranks-1", items=rows,
    item_fields={"id","name","slot","level","stats","stats_unavailable"},
    equipment={Paladin={}}, common_slots={"Head"}, profiles={["Paladin/Protection"]={
    leveling={slots={"Head"},weights={{1,59,{stamina=1}}}}}}}
BigBiSListData={stat_rank=data}
dofile("ForeverGearRating.lua")
local r=BigBiSList.ForeverGearRating
local function label(id)
    r.catalog, r.guideData = nil,nil
    local context=r:GetGuideContext("Paladin","Protection","LEVELING",49,"Human","Alliance")
    local p=r:GetGuidePlacement(context,"Head")
    local e=assert(p.byVariant[tostring(id)])
    return r:LevelingPresentation({placement=e, item=e.item, viewedLevel=49}).rank
end
assert(label(1)=="Best in Slot at Level 49")
rows["2"][5].stamina=10
assert(label(1)=="Tied for best at Level 49" and label(2)=="Tied for best at Level 49")
rows["2"]=nil
assert(label(1)=="Only ranked option at Level 49")
rows["4"]={4,"Unverified","Head",1,{stamina=11}}
assert(label(4)=="Highest known score at Level 49")
rows["4"][5].stamina=8
rows["3"]={3,"Pending","Head",1,nil,true}
assert(label(1)=="Highest known score at Level 49" and label(3)=="Stats unavailable")
''')

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
        compiled = compile_comparison_data(dataset_json("forever", "leveling_item_stats")["item_stats"])
        self.assertEqual(len(compiled["profiles"]), 28)
        self.assertGreater(len(compiled["items"]), 3500)
        self.assertTrue(compiled["items"]["11122"][compiled["item_fields"].index("utility")])
        self.assertIn("744", compiled["guide_effects"])

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
for _, entry in ipairs(service:GetComparisonCandidates(pool)) do if entry.item.id == 109 then rolled = entry end end
assert(rolled.score == 8 and rolled.item.effects[1] == "Use: Restores a resource.")
assert(not rolled.projected and rolled.rank == 1 and rolled.total == pool.reference.total)
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
assert(rating:Label(head.rows[1]) == "Top tier · Tied #1 / 13")
assert(rating:Label(head.rows[1], "compact") == "Top tier Tied #1/13")
assert(rating:Label(head.rows[1], "stacked") == "Top tier\nTied #1 / 13")
local summary = rating:DescriptionLines(head.rows[7])
assert(summary[1] == "Rank #7 of 13" and summary[2] == "Protection · Level 47")
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
assert(rating:Label({status = "loading"}) == "Waiting for item stats")
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
local publicGrade = rating:LevelingPresentation({placement = projected.placement})
assert(publicGrade.grade == 4 and publicGrade.rank == "Estimated · Strong at Level 47")
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

    def test_exact_item_effects_use_attacks_and_weight_capped_active_states(self):
        attack = effect_rule("Chance on hit: Grants an extra attack on your next swing.")
        hit = effect_rule("Use: Increases your Spell Hit chance by 7% for 20 sec. (5 Min Cooldown)")
        equipment = {
            16: {"id": 17705, "slot": "One Hand", "stats": {"dps": 35.19, "weapon_min_damage": 66, "weapon_max_damage": 124},
                 "effect_rules": [attack]},
            13: {"id": 13968, "stats": {"spell_hit_percent": 9}, "effect_rules": [hit]},
            14: {"id": 80000, "stats": {}, "effect_rules": [hit]},
        }
        attack_key, hit_key = attack["key"], hit["key"]
        weights = {"dps": 3, "spell_hit_percent": 10}
        scenario = {"caps": {"spell_hit_percent": 10}, "effect_expectations": {
            "17705": {attack_key: {"per_minute": 2, "damage_factor": 0.5}},
            "13968": {hit_key: {"uptime": 0.20}},
            "80000": {hit_key: {"uptime": 0.20}},
        }}
        eye, other = f"13:13968:{hit_key}", f"14:80000:{hit_key}"
        signature = f"{eye}|{other}"
        joint = {**scenario, "effect_state_observations": {
            signature: [{"active": [eye, other], "fraction": 0.1},
                        {"active": [eye], "fraction": 0.1}, {"active": [other], "fraction": 0.1}],
        }}
        no_pair = {slot: item for slot, item in equipment.items() if slot != 14}
        changed_identity = {**no_pair, 16: {**equipment[16], "variant_id": "17705:123"}}
        cases = [(equipment, {}, 195.57), (equipment, scenario, 200.32), (no_pair, scenario, 202.32),
                 (equipment, joint, 203.32), (changed_identity, scenario, 197.57)]
        for loadout, assumptions, expected in cases:
            self.assertAlmostEqual(swap_score(loadout, weights, [], {}, assumptions)[0], expected)
        self.lua_run('''
BigBiSList = {}
dofile("ForeverScoring.lua")
local score = BigBiSList.ForeverScoring.ScoreLoadout
''' + f"local cases = {lua_value([[loadout, settings, expected] for loadout, settings, expected in cases])}\n"
            + f"local weights = {lua_value(weights)}\n" + '''
for _, case in ipairs(cases) do
    local gear = {}
    for position, item in pairs(case[1]) do gear[tonumber(position)] = item end
    local total = score(gear, weights, {}, {}, case[2])
    assert(math.abs(total - case[3]) < 1e-8, tostring(total))
end
''')

    def test_reviewed_swords_and_effect_trinkets_in_runtime_guide(self):
        self.lua_run(r'''
local H = dofile("tests/lua_ui_harness.lua")
H.load("forever")
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
local function pool(class, spec, level, faction, race, slot)
    local phase = level < 60 and "LEVELING" or "PR"
    return rating:GetGuidePlacement(rating:GetGuideContext(class, spec, phase, level, race, faction), slot).byVariant
end
assert(not pool("Paladin", "Protection", 44, "Alliance", "Human", "Main Hand")["17705"])
local weapons = pool("Paladin", "Protection", 49, "Alliance", "Human", "Main Hand")
assert(weapons["6829"] and weapons["17705"] and weapons["17705"].conditional)
assert(weapons["17705"].item.effect_rules[1].kind == "extra_attack")
assert(not pool("Warrior", "Protection", 49, "Horde", "Orc", "Main Hand")["6829"])
local tank = pool("Paladin", "Protection", 60, "Alliance", "Human", "Trinket")
assert(tank["13966"].item.stats.dodge_percent == 1 and tank["13966"].score > 0)
local caster = pool("Mage", "Fire", 60, "Alliance", "Human", "Trinket")
assert(caster["13968"].item.stats.spell_crit_percent == 1 and caster["13968"].score > 0)
assert(#H.errors == 0, table.concat(H.errors, "\n"))
''')

    def test_damage_proc_needs_a_scored_channel_and_breakdown_includes_the_modeled_points(self):
        label = "Equip: Deals 13 to 15 Holy damage every time you block."
        rule = effect_rule(label)
        self.assertEqual((rule["trigger"], rule["chance"], rule["amount"], rule["school"]), ("block", 1, 14, "holy"))
        shield = {"id": 7726, "shield": True, "stats": {"armor": 1548}, "effect_rules": [rule], "effects": [label]}
        scenario = {"effect_expectations": {"7726": {rule["key"]: {"events_per_minute": 12, "damage_factor": 1}}}}
        cases = [({"armor": 0.08}, scenario, 123.84, True),
                 ({"armor": 0.08, "proc_dps": 2}, scenario, 129.44, False),
                 ({"armor": 0.08}, {"effect_expectations": {"7726": {rule["key"]: {"applicable": False}}}}, 123.84, False)]
        for weights, assumptions, expected, _ in cases:
            points = {}
            total, _ = swap_score({17: shield}, weights, [], {}, assumptions, breakdown=points)
            self.assertAlmostEqual(total, expected)
            self.assertAlmostEqual(sum(points.values()), expected)
        self.lua_run(f'local shield, cases = {lua_value(shield)}, {lua_value([list(case) for case in cases])}\n' + r'''
BigBiSList = {}
dofile("ForeverScoring.lua")
local scoring = BigBiSList.ForeverScoring
for _, case in ipairs(cases) do
    local total, _, applied, _, points = scoring.ScoreLoadout({[17] = shield}, case[1], {}, {}, case[2], nil, 49, true)
    assert(math.abs(total - case[3]) < 0.0001)
    assert(math.abs(points.armor + (points.proc_dps or 0) - total) < 0.0001)
    assert(scoring:HasUnresolvedEffects(shield, applied[17]) == case[4])
end
''')

    def test_guide_includes_poor_starter_gear_and_compares_against_an_unindexed_equipped_shield(self):
        self.lua_run(r'''
local H = dofile("tests/lua_ui_harness.lua")
H.load("forever")
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
function UnitRace() return "Human", "Human" end
function UnitFactionGroup() return "Alliance" end
local filters = { race = "Human", faction = "Alliance" }
local rows = addon:GetLevelingRows("Paladin", "Protection", 1, filters)
local vest
for _, group in ipairs(rows) do
    for _, row in ipairs(group.items) do if row.item_id == 2656 then vest = row end end
end
assert(vest and vest.quality == "poor" and vest.stat_rank.rank and vest.stat_rank.total >= 2)
local link = "|cffffffff|Hitem:274652|h[Wall of Water]|h|r"
local getInfo, instant = GetItemInfo, GetItemInfoInstant
function GetItemInfo(value)
    if value == link then return "Wall of Water", link, 3, 48, 43 end
    return getInfo(value)
end
function GetItemInfoInstant(value)
    if value == link then return 274652, "Armor", "Shield", "INVTYPE_SHIELD", nil, 4, 6 end
    return instant(value)
end
C_Item = {GetItemStats = function() return {RESISTANCE0_NAME = 1676, ITEM_MOD_SPELL_POWER_SHORT = 14,
    ITEM_MOD_MANA_REGENERATION_SHORT = 3} end}
C_TooltipInfo = {GetHyperlink = function() return {lines = {{leftText = "27 Block"}}} end}
local owned = { equippedSlots = {OffHand = {item_id = 274652, item_link = link}} }
local baseline = addon:GetEquipmentComparisonContexts("Paladin", "Protection", "LEVELING", owned, "OffHand")[1]
assert(baseline.name == "Wall of Water" and baseline.occupancy == "occupied")
for _, level in ipairs({39, 43, 49, 60}) do
    local phase = level == 60 and "PR" or "LEVELING"
    local guide = rating:GetGuideContext("Paladin", "Protection", phase, level, "Human", "Alliance")
    local pool = rating:GetGuidePlacement(guide, "Off Hand")
    local scarlet = assert(pool.byVariant["7726"])
    assert(scarlet.conditional)
    local stormwind = rating:GetPublishedFacts("1203")
    local match = rating:GetReferenceCandidate(guide, stormwind, "Off Hand")
    if level < 49 then assert(not match)
    else assert(match and match.score > scarlet.score) end
    if level >= 43 then
        local live = rating:GetContext("Paladin", "Protection", phase, level, owned)
        local worn = rating:GetPlacement(live, "OffHand", {"Off Hand"}).reference
        assert(worn.item.name == "Wall of Water" and worn.item.stats.block_value == 27)
        local swap = rating:GetGuideSwap(live, scarlet.item, "OffHand", "Off Hand", nil, true)
        assert(swap.conditional and swap.replacements[1].name == "Wall of Water" and swap.delta < 0)
        local advice = rating:LevelingPresentation({item=scarlet.item,swap=swap,playerLevel=level,viewedLevel=level})
        assert(advice.today:find("Holy damage on block unscored", 1, true))
        local reverse = rating:GetContext("Paladin", "Protection", phase, level,
            {equippedSlots={OffHand={item_id=7726,item_link="item:7726"}}})
        local gain = rating:GetGuideSwap(reverse, worn.item, "OffHand", "Off Hand", link)
        local alternative = rating:LevelingPresentation({item=worn.item,swap=gain,playerLevel=level,viewedLevel=level})
        assert(gain.delta > 0 and alternative.today:find("Possible upgrade · Holy damage on block unscored", 1, true))
        local summed = 0
        for _, points in pairs(swap.contributions) do summed = summed + points end
        assert(math.abs(summed - swap.delta) < 0.0001)
    end
end
''')

    def test_pre_raid_uses_the_verified_market_faction_for_guide_ranks(self):
        self.lua_run(r'''
local H = dofile("tests/lua_ui_harness.lua")
H.load("forever")
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
local function signet(race, faction)
    local guide = rating:GetGuideContext("Druid", "Feral tank", "PR", 60, race, faction)
    return rating:GetGuidePlacement(guide, "Ring").byVariant["2246"]
end
assert(signet("Night Elf", "Alliance"), "The reviewed Alliance market should qualify")
assert(not signet("Tauren", "Horde"), "Binding alone should not publish a Horde trade route")
''')

    def test_modern_rolls_use_exact_keys_and_keep_prophet_damage_and_healing_separate(self):
        base = {"id": 9288, "name": "Field Plate Girdle", "slot": "Waist", "armor_type": "Plate",
                "required_level": 40, "stats": {"armor": 169}, "variant_only": True}
        rolls = [{"item_id": 9288, "bonus_fields": [0, 0, 1, 12749], "suffix_name": "of the Prophet",
                  "stat_delta": {"intellect": 9, "spirit": 5, "healing_power": 8, "spell_damage": 3}},
                 {"item_id": 9288, "bonus_fields": [0, 0, 1, 12727], "suffix_name": "of the Tiger",
                  "stat_delta": {"strength": 8, "agility": 8}}]
        def document(flavor, family):
            return {"item_variants": rolls} if family == "item_variants" else dataset_json(flavor, family)

        with patch("tools.forever_comparison.dataset_json", side_effect=document):
            data = compile_comparison_data([base])
        data["items"] = {key: row for key, row in data["items"].items() if key.split(":")[0] == "9288"}
        # Exercise the two separately reviewed links in a controlled family.
        group = data["items"]["9288"][data["item_fields"].index("roll_group")]
        data["roll_groups"][group - 1] = [12727, 12749]
        (prophet, prophet_link), (tiger, tiger_link) = map(roll_identity, rolls)
        self.assertEqual(prophet, "9288:0:0:0:1:12749")
        self.lua_run(f'BigBiSListData = {{stat_rank = {lua_value(data)}}}\n'
                     + f'local prophet, prophetLink, tiger, tigerLink = {lua_value(prophet)}, {lua_value(prophet_link)}, '
                     + f'{lua_value(tiger)}, {lua_value(tiger_link)}\n' + r'''
BigBiSList = { GetAvailabilityPhaseIndex = function() return 1 end,
    IsStatRankGuideItemAvailable = function() return true end }
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
local rating = BigBiSList.ForeverGearRating
assert(rating:NormalizeLink(9288, prophetLink) == prophet)
assert(rating:NormalizeLink(9288, tigerLink) == tiger)
assert(rating:NormalizeLink(9288, "item:9288:90:7:0:0:0:0:91:49:0:0:0:1:12749:0") == prophet)
assert(rating:NormalizeLink(9288, "item:9288:0:0:0:0:0:0:0:0:0:0:0:2:12749") == nil)
assert(rating:GetTooltipItem(9288, "item:9288::::::::::::").status == "unavailable")
local function pool(spec)
    local context = rating:GetGuideContext("Paladin", spec, "LEVELING", 49, "Human", "Alliance")
    return rating:GetGuidePlacement(context, "Waist")
end
local protection = pool("Protection")
assert(protection.count == 2 and protection.rows[1].item.key == tiger)
assert(math.abs(protection.byVariant[prophet].score - 22.27) < 0.001)
assert(protection.byVariant[prophet].item.stats.healing_power == 8 and protection.byVariant[prophet].item.stats.spell_damage == 3)
assert(protection.byVariant[prophet].item.variant_link == prophetLink)
assert(pool("Holy").rows[1].item.key == prophet)

local scaled = prophetLink .. ":1:42:17"
C_Item = {
    GetItemInfo = function(link) return "Field Plate Girdle of the Prophet", link, 2, 41, 40 end,
    GetItemInfoInstant = function() return 9288, "Armor", "Plate", "INVTYPE_WAIST", nil, 4, 4 end,
    GetItemStats = function() return {ITEM_MOD_INTELLECT_SHORT = 9, ITEM_MOD_SPIRIT_SHORT = 5,
        ITEM_MOD_SPELL_POWER_SHORT = 3, RESISTANCE0_NAME = 169} end,
}
C_TooltipInfo = {GetHyperlink = function() return {lines = {
    {leftText = "Equip: Increases healing done by up to 8 and damage done by up to 3 for all magical spells and effects."},
}} end}
local observed = rating:GetTooltipItem(9288, scaled).facts
assert(observed.key ~= prophet and observed.native)
assert(observed.stats.healing_power == 8 and observed.stats.spell_damage == 3 and not observed.stats.spell_power)
local placement = rating:GetReferenceCandidate(protection.scope.context, observed, "Waist")
local projected = rating:ProjectPlacement(observed, placement, protection)
assert(projected.projected and projected.tied and projected.score == protection.byVariant[prophet].score)
assert(protection.count == 2 and protection.byVariant[prophet].rank == 2 and not protection.byVariant[prophet].tied)
assert(protection.byVariant[tiger].rank == 1)
''')

    def test_verified_rolls_preserve_scaled_physical_stats_and_equip_level(self):
        base = {"id": 71, "name": "Fixture Sword", "slot": "One Hand", "weapon_subtype": "Sword",
                "required_level": 49, "item_level": 54, "dps": 30, "armor": 50,
                "weapon_min_damage": 45, "weapon_max_damage": 75, "weapon_speed": 2}
        roll = {"item_id": 71, "bonus_fields": [0, 0, 1, 11, 1, 2, 5], "suffix_name": "of the Fixture",
                "required_level": 50, "item_level": 55, "stat_delta": {"armor": 7, "weapon_min_damage": 6},
                "stats": {"dps": 38, "weapon_max_damage": 101}}
        item = materialized_items([base], [roll])[-1]
        facts = comparison_facts(item)
        self.assertEqual((item["item_level"], facts["level"]), (55, 50))
        self.assertEqual(facts["stats"], {"armor": 57, "dps": 38, "weapon_speed": 2,
                                          "weapon_min_damage": 51, "weapon_max_damage": 101})

    def test_dungeon_presets_are_rejected_by_forever_compiler(self):
        model = copy.deepcopy(self.model)
        key = "Paladin/Protection"
        model["profiles"][key]["dungeon"] = {"leveling": {"weights": {"stamina": 1.8}}}
        with self.assertRaisesRegex(ValueError, f"Dungeon scoring presets have been retired for {key}"):
            compile_model(model, self.snapshot)

    def test_overall_leveling_reference_keeps_tank_gear_tradeoffs(self):
        self.lua_run(r'''
dofile("DataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
function addon:GetCurrentPhaseKey() return "PR" end

local cases = {
    -- Crested Heater Shield and Battered Viking Shield
    {"Paladin", "Protection", "Human", "Off Hand", "2451", "9403", 137.26, 129.36},
    -- Platemail Leggings and Mighty Chain Pants
    {"Warrior", "Protection", "Human", "Legs", "8093", "4800", 31.92, 26.40},
    -- Grimlok's Charge and Ironshod Bludgeon
    {"Druid", "Feral tank", "Night Elf", "Two Hand", "9416", "9408", 115.895, 102.20},
}
for _, case in ipairs(cases) do
    local class, spec, race, slot, firstId, secondId, firstScore, secondScore = unpack(case)
    local context = rating:GetGuideContext(class, spec, "LEVELING", 49, race, "Alliance")
    local pool = rating:GetGuidePlacement(context, slot)
    local first, second = assert(pool.byVariant[firstId]), assert(pool.byVariant[secondId])
    assert(first.rank < second.rank and not first.conditional and not second.conditional)
    assert(math.abs(first.score - firstScore) < 1e-6 and math.abs(second.score - secondScore) < 1e-6)
end

local bear = rating:GetGuideContext("Druid", "Feral tank", "LEVELING", 10, "Night Elf", "Alliance")
local weights = rating:ReferenceWeights(bear, true, true)
assert(weights.armor > 0 and weights.stamina > 0 and weights.dps > 0)
assert(weights.block_value == 0 and weights.parry_percent == 0)
local caster = rating:GetGuideContext("Druid", "Feral tank", "LEVELING", 9, "Night Elf", "Alliance")
assert(caster.weights.armor == 0 and caster.weights.dps == 0 and caster.weights.spell_damage > 0)
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

    def test_swap_explains_verified_set_thresholds_and_talent_contributions(self):
        names = self.runtime["set_names"]
        self.assertEqual(names[188], "Lightforge Armor")
        self.lua_run("local setNames = " + lua_value(names) + r'''
BigBiSList = {}
dofile("ForeverScoring.lua")
local scoring = BigBiSList.ForeverScoring
local model = {set_names = setNames, items = {leveling = {}, pre_raid = {}}}
local weights = {intellect = 0.5, spell_power = 1}
local ordinary = {id = 3, slot = "Legs", stats = {intellect = 6}}
local lightforge = {id = 4, slot = "Legs", stats = {intellect = 10}, set_id = 188}
local alternate = {id = 5, slot = "Legs", stats = {intellect = 10}}
local function setup(legs)
    return {model = model, mode = "leveling", level = 49, weights = weights, ranks = {[10] = 5},
        gear = {[1] = {id = 1, stats = {}, set_id = 188}, [3] = {id = 2, stats = {}, set_id = 188}, [7] = legs},
        scenario = {sets = {{set_id = 188, pieces = 3, stats = {spell_power = 18}}}, effect_expectations = {}},
        profile = {operations = {{entry = 10, kind = "convert", from_stat = "intellect", stats = {"spell_power"},
            factors = {0.12, 0.24, 0.36, 0.48, 0.60}, name = "Champion of the Light"}}}}
end

local first = setup(ordinary)
local gained = scoring:EvaluateSwap(first, lightforge, nil, 7, "Legs", weights)
assert(math.abs(gained.delta - 22.4) < 1e-8)
assert(gained.effects[1] == "Champion of the Light (+2.40)")
assert(gained.effects[2] == "3-piece Lightforge Armor bonus gained")
local noChange = scoring:EvaluateSwap(first, alternate, nil, 7, "Legs", weights)
assert(math.abs(noChange.delta - 4.4) < 1e-8 and #noChange.effects == 1)

local lost = scoring:EvaluateSwap(setup(lightforge), ordinary, nil, 7, "Legs", weights)
assert(math.abs(lost.delta + 22.4) < 1e-8)
assert(lost.effects[1] == "Champion of the Light (-2.40)")
assert(lost.effects[2] == "3-piece Lightforge Armor bonus lost")
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
local initialNodes, initialDefinitions = {}, {}
for entry, trait in pairs(BigBiSListData.character_scoring.traits) do
    initialNodes[trait.node_id] = tonumber(entry)
    initialDefinitions[trait.definition_id] = trait.spell_id
end
C_ClassTalents = {GetActiveConfigID = function() return 1 end}
C_Traits = {
    GetConfigInfo = function() return {treeIDs = {1100}} end,
    GetGroupDisplayInfoByTreeID = function() return {{groupID = 1, displayName = "Retribution"}} end,
    GetGroupCurrencyInfo = function() return {{traitNodeGroupID = 1, currencyInfos = {{spent = 31}}}} end,
    GetNodeInfo = function(_, node)
        local entry = assert(initialNodes[node])
        local selected = entry == 137880 and rank or (entry == 130425 and 1 or 0)
        return {entryIDs = {entry}, activeEntry = selected > 0 and {entryID = entry, rank = selected} or nil}
    end,
    GetDefinitionInfo = function(id) return {spellID = initialDefinitions[id]} end,
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
assert(#early > 0)
for _, group in ipairs(early) do for _, row in ipairs(group.items) do assert(row.stat_rank.item.level <= 14) end end
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
ranks = {[129416] = 5, [129415] = 3, [129404] = 0, [129401] = 0}
setTalentTree(1082, "Enhancement")
local function thirdWristPick()
    local context = assert(addon.ForeverScoring:GetContext("Shaman", "Enhancement", "leveling", 42))
    return addon.ForeverScoring:RankSlot(context, "Wrist").selected[3].item.id
end
assert(thirdWristPick() == 2868) -- Patterned Bronze Bracers
ranks[129404] = 2
addon.ForeverScoring:Invalidate()
assert(thirdWristPick() == 4796) -- Owl Bracers

function UnitClass() return "Druid", "DRUID" end
function UnitRace() return "Night Elf", "NightElf", 4 end
function UnitFactionGroup() return "Alliance" end
ranks = {[129571] = 0, [129582] = 0, [129610] = 0, [129618] = 3}
setTalentTree(1089, "Feral Combat")
addon:SetSelection("Druid", "Feral tank")
assert(addon:DetectPlayerSpec("Druid") == "Feral tank")
assert(addon.ForeverScoring:GetContext("Druid", "Feral tank", "leveling", 42))
addon:SetSelection("Druid", "Feral dps")
assert(addon:DetectPlayerSpec("Druid") == "Feral dps")
assert(addon.ForeverScoring:GetContext("Druid", "Feral dps", "leveling", 42))
''')

    def test_guide_keeps_all_qualified_variants_and_filters_after_selection(self):
        self.lua_run(r'''
dofile("DataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")
function UnitLevel() return 48 end
function UnitRace() return "Human", "Human", 1 end
function UnitFactionGroup() return "Alliance" end
local addon = BigBiSList
local function guide(terms)
    return addon:GetLevelingRows("Paladin", "Retribution", 48, terms or {})
end
local groups, count, effect = {}, 0, {}
for _, group in ipairs(guide()) do
    local names, featured = {}, 0
    for _, row in ipairs(group.items) do
        assert(row.guide_source_unknown or row.acquisition_display.status == "ready")
        assert(not row.matched_access_option or not row.matched_access_option.is_inferred_trade_option)
        assert(row.stat_rank.rank or row.stat_rank.status)
        assert(not names[row.stat_identity], "duplicate exact variant")
        names[row.stat_identity] = row
        if not row.guide_alternate then featured = featured + 1 end
        if row.guide_note then effect[row.item_id] = row end
        count = count + 1
    end
    groups[group.slot] = { items = group.items, featured = featured, names = names }
end
assert(count > 1000 and groups.Head.featured > 0 and #groups.Shoulder.items > 7)
assert(groups.Shoulder.names["9476"] and groups.Shoulder.names["9411"])
assert(not (groups.Trinket.names["274152"] and groups.Trinket.names["274152"].guide_note), "only reviewed utility gets an endorsement")
assert(effect[744] and effect[249442], "reviewed effects remain discoverable")
local alternate
for _, row in ipairs(groups.Shoulder.items) do
    if row.guide_alternate and row.variant_id then alternate = row; break end
end
assert(alternate)
local matching = guide({search = alternate.name, slots = {Shoulder = true}})
assert(#matching == 1 and matching[1].items[1].stat_identity == alternate.stat_identity)
assert(matching[1].items[1].guide_alternate, "search must preserve the unfiltered threshold")
assert(#guide({search = "Canvas Shoulderpads"}) == 1)
for _, group in ipairs(addon:GetPhaseRows("Paladin", "Retribution", "PR", {})) do
    for _, row in ipairs(group.items) do assert(row.guide_source_unknown or row.history or row.recommendation_history) end
end
''')

    def test_live_swap_counts_passive_tooltip_stats_and_exact_modifiers(self):
        self.lua_run(r'''
dofile("DataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")
local addon, model = BigBiSList, BigBiSListData.character_scoring
local rating, scoring = addon.ForeverGearRating, addon.ForeverScoring
local wornId, candidateId = 990001, 990002
local wornLink = "item:990001:1891:0:0:0:0:0:0:48:1:0:0:1:9999"
local candidateLink = "item:990002:0:0:0:0:0:0"
function GetBuildInfo() return "1.60.1", model.build end
function UnitLevel() return 48 end
function UnitRace() return "Human", "Human", 1 end
function UnitFactionGroup() return "Alliance" end
function GetInventoryItemID(_, slot) if slot == 12 then return wornId end end
function GetInventoryItemLink(_, slot) if slot == 12 then return wornLink end end
addon.DetectPlayerClass = function() return "Paladin" end
addon.DetectPlayerSpec = function() return "Retribution" end
local rank = 5
local nodes, definitions = {}, {}
for entry, trait in pairs(model.traits) do
    nodes[trait.node_id] = tonumber(entry)
    definitions[trait.definition_id] = trait.spell_id
end
C_ClassTalents = { GetActiveConfigID = function() return 1 end }
C_Traits = {
    GetConfigInfo = function() return {treeIDs = {1100}} end,
    GetNodeInfo = function(_, node)
        local entry = assert(nodes[node])
        return { entryIDs = {entry}, activeEntry = entry == 137880 and {entryID = entry, rank = rank} or nil }
    end,
    GetDefinitionInfo = function(id) return {spellID = definitions[id]} end,
}
C_Item = {
    GetItemInfo = function(link) return link:find("990001") and "Purified Ring fixture" or "Ironspine fixture", nil, 3, 44, 0 end,
    GetItemInfoInstant = function() return nil, nil, nil, "INVTYPE_FINGER", nil, 4, 0 end,
    GetItemStats = function(link)
        return link:find("990001") and {ITEM_MOD_INTELLECT_SHORT = 12}
            or {ITEM_MOD_STRENGTH_SHORT = 18, ITEM_MOD_AGILITY_SHORT = 6}
    end,
}
C_TooltipInfo = { GetHyperlink = function(link)
    if link:find("990001") then return {lines = {{leftText = "Equip: Increases spell power by 5."}}} end
    return {lines = {{leftText = "Ironspine fixture"}}}
end }
local owned = {equippedSlots = {Finger1 = {item_id = wornId, item_link = wornLink}}}
local context = rating:GetContext("Paladin", "Retribution", "LEVELING", 48, owned)
local candidate = rating:GetTooltipItem(candidateId, candidateLink)
local base = context.equipmentFacts.Finger1.facts
assert(base.stats.spell_power == 5 and base.stats.intellect == 12 and base.key == "990001:0:0:0:1:9999")
local swap = rating:CompareTooltipItem(context, candidate, true, nil, true, { physical = "Finger1" })
-- The enchant gives four to all primary stats. Human Spirit applies to its
-- Spirit component, and Champion adds 9.6 damage from the enchanted Intellect.
assert(swap.basis == "active" and not swap.conditional)
local expected = (18-4)*1.6 + (6-4)*1.2 - 4*0.2 - 4.4*0.15 - 16*0.5 - (5 + 9.6)*0.65
assert(math.abs(swap.delta - expected) < 1e-7, swap.delta)
rank = 0
scoring:Invalidate()
local untalented = rating:CompareTooltipItem(context, candidate, true, nil, true, { physical = "Finger1" })
assert(math.abs(untalented.delta - swap.delta - 9.6*0.65) < 1e-7)
local unknown = rating:GetTooltipItem(candidateId, "item:990002:918273:0:0:0:0:0")
local uncertain = rating:CompareTooltipItem(context, unknown, true, nil, true, { physical = "Finger1" })
assert(uncertain.delta > 0 and uncertain.conditional and not rating:IsMeaningfulOwnedUpgrade(uncertain))
model.gems, model.socket_bonuses = {[9000] = {agility = 3}}, {["990002:9000:0:0:0"] = {agility = 1}}
local exact, incomplete = scoring:GetExactStats(candidateId, candidate.facts.stats, "item:990002:0:9000:0:0:0:0")
assert(not incomplete and exact.agility == 10 and candidate.facts.stats.agility == 6)
function UnitLevel() return 60 end
scoring:Invalidate()
local endgame = rating:GetContext("Paladin", "Retribution", "PR", 60, owned)
local live = rating:CompareTooltipItem(endgame, candidate, true, nil, true, { physical = "Finger1" })
local details = addon:CompareRecommendationItems(candidateId, wornId, "Paladin", "Retribution", "PR", "Ring",
    {ownedSnapshot = owned, slotKey = "Finger1", item_link = wornLink}, {item_link = candidateLink})
assert(details.basis_key == "active_build" and details.score_delta == live.delta)
''')
