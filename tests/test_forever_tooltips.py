import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


FIXTURE = r'''
local H = dofile("tests/lua_ui_harness.lua")
local postItem
Enum = {TooltipDataType = {Item = 0}, BankType = {Character = 0, Account = 2}}
TooltipDataProcessor = {AddTooltipPostCall = function(kind, callback)
    assert(kind == Enum.TooltipDataType.Item)
    postItem = callback
end}
local ui = H.load("forever")
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
local level, group, detected = 47, 1, "Protection"
UnitLevel = function() return level end
UnitClassBase = function() return "PALADIN" end
UnitRace = function() return "Human", "Human" end
GetNumSpecGroups = function() return 2 end
C_SpecializationInfo = {GetActiveSpecGroup = function() return group end}
addon.DetectPlayerSpec = function() return detected end

local rows = {}
local function gear(id, name, slot, points, maximum, required, weapon)
    rows[tostring(id)] = {id, name, slot, required or 1, {stamina = points}, maximum, weapon}
end
gear(900001, "Stronger ring", "Ring", 8)
gear(900002, "Blood Ritual Ring", "Ring", 4)
gear(900003, "Bag ring", "Ring", 9)
gear(900004, "Bank ring", "Ring", 14)
gear(900005, "Future ring", "Ring", 100, nil, 55)
gear(900006, "Unique ring", "Ring", 11, 1)
gear(900007, "Worn sword", "One Hand", 8, nil, nil, "Sword")
gear(900008, "Worn off hand", "Off Hand", 5)
gear(900009, "Great sword", "Two Hand", 12, nil, nil, "Sword")
gear(900010, "Small sword", "One Hand", 6, nil, nil, "Sword")
gear(900011, "Off-hand weapon", "Off Hand", 5, nil, nil, "Sword")
gear(900012, "Empty-slot charm", "Trinket", 6)
gear(900013, "Lower ring", "Ring", 2)
local weights = {stamina = 1}
local slots = {"Ring", "Trinket", "Main Hand", "Off Hand", "Two Hand"}
local profile = {
    leveling = {slots = slots, weights = {{1, 59, weights}}, dual_wield_level = 20},
    pre_raid = {slots = slots, weights = weights, dual_wield = true,
        weapon_types = {"Sword"}, two_hand_weapon_types = {"Sword"}},
}
BigBiSListData.stat_rank = {
    version = "forever-stat-ranks-1",
    profiles = {["Paladin/Protection"] = profile, ["Paladin/Retribution"] = profile, ["Paladin/Holy"] = profile},
    common_slots = slots,
    equipment = {Paladin = {weapon_types = {"Sword"}, two_hand_weapon_types = {"Sword"}}},
    item_fields = {"id", "name", "slot", "level", "stats", "max_equipped", "weapon_subtype"},
    items = rows,
}
local colors = {
    [0] = {157, 157, 157}, {255, 255, 255}, {30, 255, 0}, {0, 112, 221}, {163, 53, 238}, {255, 128, 0},
}
GetItemQualityColor = function(quality)
    local color = colors[quality or 1]
    return color[1]/255, color[2]/255, color[3]/255
end

local function itemId(value)
    return tonumber(value) or tonumber(tostring(value):match("item:(%d+)"))
end
local function text(tooltip)
    return table.concat(tooltip.lines, "\n")
end
local function includes(tooltip, expected)
    assert(text(tooltip):find(expected, 1, true), "Expected " .. expected .. " in:\n" .. text(tooltip))
end
local function excludes(tooltip, unexpected)
    assert(not text(tooltip):find(unexpected, 1, true), "Unexpected " .. unexpected .. " in:\n" .. text(tooltip))
end
local function oneSection(tooltip)
    local _, count = text(tooltip):gsub("Big BiS List", "")
    assert(count == 1, text(tooltip))
end
local owner = CreateFrame("Button", nil, UIParent)
local nativeRequirements = {}
local function showNative(tooltip, link, getter, args)
    tooltip:SetOwner(owner, "ANCHOR_RIGHT")
    tooltip.rowColors = {}
    tooltip.nativeData = {id = itemId(link), hyperlink = link}
    tooltip.nativeInfo = {getterName = getter or "GetHyperlink", getterArgs = args or {link}}
    tooltip.hyperlink = nil
    tooltip.lines = {"Native name", "Native enchant", "Native source"}
    local requirement = nativeRequirements[itemId(link)]
    if requirement then
        tooltip.lines[#tooltip.lines + 1] = requirement
        tooltip.nativeData.lines = {{leftText = requirement}}
    end
    tooltip:Show()
    postItem(tooltip, tooltip.nativeData)
    postItem(tooltip, tooltip.nativeData)
end
for _, tooltip in ipairs({GameTooltip, ItemRefTooltip}) do
    local addLine = tooltip.AddLine
    tooltip.AddLine = function(self, line, ...)
        self.rowColors[line] = {...}
        addLine(self, line, ...)
    end
    tooltip.GetPrimaryTooltipInfo = function(self) return self.nativeInfo end
    tooltip.GetPrimaryTooltipData = function(self) return self.nativeData end
    tooltip.RefreshData = function(self)
        self.rebuilds = (self.rebuilds or 0) + 1
        showNative(self, self.nativeData.hyperlink, self.nativeInfo.getterName, self.nativeInfo.getterArgs)
    end
end
'''


class ForeverTooltipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def lua_run(self, code):
        if not self.lua:
            self.skipTest("Lua 5.1 is unavailable")
        process = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, encoding="utf-8", capture_output=True, timeout=90,
            input=FIXTURE + code + '\nassert(#H.errors == 0, table.concat(H.errors, "\\n"))\n',
        )
        self.assertEqual(process.returncode, 0, process.stderr or process.stdout)

    def test_one_sword_shows_the_players_swap_and_its_leveling_ranges(self):
        self.lua_run(r'''
profile.leveling.weights = {{1, 49, weights}, {50, 59, {stamina = 1, intellect = 1}}}
gear(900040, "Journey Sword", "Main Hand", 100, nil, 30, "Sword")
gear(900041, "Peer sword", "Main Hand", 102, nil, 30, "Sword")
gear(900042, "Stronger sword", "Main Hand", 116, nil, 34, "Sword")
gear(900043, "Late sword", "Main Hand", 150, nil, 38, "Sword")
rows["900040"][5].intellect = 48
rows["900007"][3] = "Main Hand"
H.equipped[16] = 900007
local tip = ItemRefTooltip
level = 22
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900040")
includes(tip, "Requires Level 30")
includes(tip, "Among the best at Level 30")
includes(tip, "Likely upgrade at Level 30\nEstimated +92.0 pts vs Worn sword at Level 30")
H.settle()
includes(tip, "Among the best at Levels 30–33")

level = 31
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900040")
includes(tip, "|t Major upgrade\n+92.0 pts vs Worn sword")
includes(tip, "Among the best at Levels 30–33")
excludes(tip, "Requires Level")

level = 38
H.equipped[16] = 900043
ui:Invalidate("ownership", "fixture level-up")
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900040")
includes(tip, "Downgrade\n-50.0 pts vs Late sword")
includes(tip, "Better options at Level 38")
includes(tip, "Among the best at Levels 50–59")
local current = rating:GetGuideContext("Paladin", "Protection", "LEVELING", 35, "Human", "Alliance")
local placement = rating:GetGuidePlacement(current, "Main Hand").byVariant["900040"]
local record = rating:GetLevelingRecord(rating:GetLevelingSummary(current), "Main Hand", "900040")
assert(#record.strength == 3 and record.strength[2].lastLevel == 37 and record.strength[3].firstLevel == 50)
local view = rating:LevelingPresentation({item = placement.item, placement = placement, record = record,
    swap = {delta = -50, replacements = {{name = "Late sword"}}}, playerLevel = 38, viewedLevel = 35, explicitPreview = true})
assert(view.today == "Downgrade at Level 38" and view.strength == "Strong at Level 35")
assert(rating:LevelingPresentationLines(view)[2] == "-50.0 pts vs Late sword")
assert(rating:EstimateSwapPoints(0) == "0.0 pts")
assert(rating:EstimateSwapPoints(0.02) == "+0.02 pts")
assert(rating:EstimateSwapPoints(-0.02) == "-0.02 pts")
assert(rating:EstimateSwapPoints(nil) == nil)
local quest = {type = "quest", quest_id = 9991, entity_name = "Sword quest", eligibility = {min_level = 32}}
local sourceLevel, sourceType = addon:GetLevelingSourceGate({
    option = {source = quest, source_type = "quest"},
    source_match = {source = quest},
})
local locked = rating:LevelingPresentation({item = placement.item, placement = placement, playerLevel = 22,
    sourceLevel = sourceLevel, sourceType = sourceType})
assert(locked.today == "Requires Level 30" and locked.acquisition == "Quest available at Level 32")

-- Keep the earlier sword on the same character. Replacing a stronger equipped
-- weapon with a weaker one changes its personal advice, including in a preview.
H.equipped[16] = 900007
ui:Invalidate("ownership", "sword-equipped")
local sword = {item_id = 900040, name = "Journey Sword", slot = "Main Hand", item_link = "item:900040",
    stat_identity = "900040", stat_rank = placement, class = "Paladin", spec = "Protection", phase = "LEVELING", leveling = true}
addon.GetLevelingRows = function() return {{slot = "Main Hand", items = {sword}}} end
addon.GetLevelingJourneyRows = function(_, _, _, _, _, _, current) return current end
ui:Open(); H.settle()
ui:SetClass("Paladin"); ui:SetSpec("Protection"); ui:SetContentMode("leveling"); ui:SetLevelingLevel(35); H.settle()
for _, mode in ipairs({"leveling", "wishlist", "comparison"}) do
    local same = assert(ui:GetLevelingGearView(sword, mode))
    assert(same.today == "Major upgrade at Level 38" and same.evidence == "+92.0 pts vs Worn sword", same.today)
end
ui:ShowInspectorFor(sword.item_id, sword, "leveling"); ui:SetInspectorVisible(true); H.settle()
local contents = ""
for _, block in ipairs(ui.detailsWidgetPools.text or {}) do
    if block:IsVisible() then contents = contents .. block.body:GetText() end
end
assert(contents:find("+92.0 pts vs Worn sword", 1, true), contents)
local origin = ui.selectedRowKey
assert(ui:OpenSlotComparison(sword, "leveling", true)); H.settle()
assert(ui.slotComparison.level == 35 and ui.slotComparison.reference.slotKey == "MainHand")
ui:CloseSlotComparison(); H.settle()
assert(ui.selectedRowKey == origin and ui.selectedItemData.item_id == sword.item_id)
showNative(tip, sword.item_link, "GetQuestItem", {"choice", 1})
includes(tip, "|t Major upgrade\n+92.0 pts vs Worn sword")
local modifiers = BigBiSListData.character_scoring
modifiers.enchants[9901] = {stamina = 3}
GetBuildInfo = function() return "Fixture", tostring(modifiers.build) end
local bagLink = "item:900040:9901"
GetContainerNumSlots = function(bag) return bag == 0 and 1 or 0 end
GetContainerItemID = function() return 900040 end
GetContainerItemLink = function() return bagLink end
ui:Invalidate("ownership", "sword-looted"); ui:Refresh(); H.settle()
showNative(tip, bagLink, "GetBagItem", {0, 1})
includes(tip, "Best you own for this slot")
includes(tip, "Equip now")
excludes(tip, "pts vs")
local inBags = assert(ui:GetLevelingGearView(sword, "leveling"))
assert(inBags.today == "Best you own for this slot at Level 38" and inBags.evidence == "Equip now", inBags.today)
assert(inBags.swap.equipSwap.delta == 95)
''')

    def test_verdict_thresholds_require_net_and_role_gains(self):
        self.lua_run(r'''
local function verdict(net, role, displaced)
    local swap = {delta = net, roleDelta = role, roleDisplaced = displaced, replacements = {{name = "Old ring"}}}
    return rating:LevelingPresentation({item = {level = 1}, playerLevel = 31, viewedLevel = 31, swap = swap})
end
assert(verdict(0.001, 0.001, 100).today == "Slight upgrade")
assert(verdict(0.001, 0.001, 100).evidence == "+0.001 pts vs Old ring")
assert(verdict(1.99, 8, 10).today == "Slight upgrade")
assert(verdict(8, 1.99, 10).today == "Slight upgrade")
assert(verdict(4.99, 8, 100).today == "Slight upgrade")
assert(verdict(2, 2, 40).today == "Upgrade")
assert(verdict(6, 5.99, 40).today == "Upgrade")
assert(verdict(14.99, 16, 100).today == "Upgrade")
assert(verdict(6, 6, 40).today == "Major upgrade")
assert(verdict(15, 15, 100).today == "Major upgrade")
assert(verdict(0, 0, 40).today == "Sidegrade")
local possible = rating:LevelingPresentation({item = {level = 1, effects = {"Chance on hit: deals additional damage."}},
    playerLevel = 31, swap = {conditional = true, delta = 2, replacements = {{name = "Old sword"}}}})
assert(possible.today == "Possible upgrade · Chance-on-hit effect unscored" and possible.tone == "uncertain")
''')

    def test_activities_sort_actual_and_forecast_owned_gains(self):
        self.lua_run(r'''
level = 22
local group = {slot = "Ring", items = {}}
local function pick(id, name, destination, score)
    gear(id, name, "Ring", score)
    local source = {type = "drop", zone = destination, entity_name = name, activity_zones = {destination}}
    local option = {source = source, source_type = "drop", zone = destination, is_primary = true, label = name}
    group.items[#group.items + 1] = {item_id = id, name = name, slot = "Ring", leveling = true, guide_order = 1,
        access_options = {option}, acquisition_display = {status = "ready", option = option, source_match = {source = source},
            activity_zone = destination}, matched_access_option = option}
end
H.equipped[11], H.equipped[12] = 900001, 900002
pick(900040, "Vault Band", "The Vault", 25)
pick(900041, "Miner's Band", "The Mine", 5)
pick(900042, "Foreman's Band", "The Mine", 5.01)
pick(900043, "Dusty Band", "The Mine", 1)
group.items[#group.items + 1] = group.items[3]
pick(900002, "Blood Ritual Ring", "The Mine", 4)
-- A known banked ring becomes the comparison only when the character can wear it.
gear(900044, "Banked band", "Ring", 22, nil, 35)
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links = true, {"item:900044", "item:900044"}
addon.GetLevelingRows = function() return {group} end
addon.GetLevelingJourneyRows = function(_, _, _, _, _, _, current) return current end
ui:Open(); H.settle()
ui:SetClass("Paladin"); ui:SetSpec("Protection"); ui:SetContentMode("leveling"); H.settle()
ui:SetLevelingLevel(22); H.settle()
ui:SelectGrouping("activity"); ui:Refresh()
local function activities()
    local actions, labels = {}, {}
    for _, entry in ipairs(ui.renderModel.entries) do
        if entry.kind == "action" then actions[#actions + 1] = entry
        elseif entry.kind == "note" then labels[#labels + 1] = entry.text end
    end
    return actions, table.concat(labels, "\n")
end
local pending = activities()
assert(pending[1].detail == "4 guide items · Comparing upgrades…", pending[1].detail)
assert(ui.sortDropdown:IsVisible() and ui:GetSortDropdownText() == "Most loot")
H.settle()
local result = activities()
assert(result[1].title == "The Mine" and result[1].detail == "4 guide items · 2 upgrade options", result[1].detail)
ui:SelectSort("best_upgrade"); H.settle()
result = activities()
assert(result[1].title == "The Vault" and result[1].detail:find("Vault Band (+21.0 pts)", 1, true), result[1].detail)
ui:SetLevelingActivity("The Mine"); H.settle()
ui:SelectSort("item"); H.settle()
ui:SetLevelingActivity(nil); H.settle()
assert(ui:GetSortDropdownText() == "Best upgrade" and ui:GetViewState().sort == "item")
ui:SelectSort("most_upgrades"); H.settle()
assert(activities()[1].title == "The Mine")
ui:SetLevelingLevel(35); H.settle()
ui:SelectSort("best_upgrade"); H.settle()
local forecasts, labels = activities()
assert(labels:find("Estimated at Level 35") and forecasts[1].detail:find("Vault Band (+3.0 pts)", 1, true), labels)
level = 38
addon:RefreshTooltipPlayerContext()
ui:Invalidate("ownership", "fixture-level-up")
ui:Refresh(); H.settle()
local current, note = activities()
assert(note:find("Upgrades for you at Level 38") and current[1].detail:find("+3.0 pts", 1, true), note)
''')

    def test_live_spec_blocks_show_full_details_and_approved_bis(self):
        self.lua_run(r'''
SlashCmdList = {}
addon.InitMinimapButton = function() end
assert(loadfile("Core.lua"))("BigBiSList")
local core = H.frames[#H.frames]
local onEvent = core:GetScript("OnEvent")
detected = nil
onEvent(core, "ADDON_LOADED", "BigBiSList")
addon:SetSelection("Druid", "Balance", "PR")
addon:SetSelectedLevelingLevel(14, true)
H.equipped[11], H.equipped[12] = 900001, 900002
local tip = GameTooltip
local levelSeen, roleSeen = nil, nil
addon.GetLevelingTooltipMatches = function(_, id, class, spec, current)
    levelSeen, roleSeen = current, spec
    return {{class = class, spec = spec or "Protection", phase = "LEVELING", slot = "Ring", leveling = true, level_label = "Guide fixture"}}
end
addon.GetGroupedLevelingTooltipMatches = addon.GetLevelingTooltipMatches
showNative(tip, "item:900003", "GetQuestItem", {"reward", 1})
includes(tip, "Spec previews")
includes(tip, "pts vs Blood Ritual Ring")
excludes(tip, "Equip now")
detected = "Protection"
onEvent(core, "PLAYER_TALENT_UPDATE"); H.settle()
excludes(tip, "Spec previews")
local protection = "Better options at Level 47"
includes(tip, "|t Upgrade\n+5.0 pts vs Blood Ritual Ring\n" .. protection)
excludes(tip, "Tier range")
local rgb = tip.rowColors.Protection
assert(rgb[1] == 0.93 and rgb[2] == 0.93 and rgb[3] == 0.96)
local rankColor = tip.rowColors[protection]
for component = 1, 3 do assert(rankColor[component] == rgb[component]) end
excludes(tip, "· Owned")
excludes(tip, "Small pools use slot placement for color")
excludes(tip, "(Off-spec)")
includes(tip, "Guide fixture")
excludes(tip, "Hold Alt")
assert(not addon.tooltipModifierFrame)
for index, line in ipairs(tip.lines) do
    if line == "Protection" or line == "Retribution" or line == "Holy" then
        assert(tip.lines[index - 1] == " ", "Each spec starts a separate block")
    end
end
assert(ui.frame == nil)
oneSection(tip)
local context = rating:GetContext("Paladin", "Protection", "LEVELING", 47, ui.currentOwned)
local before = context.lastTooltip.result
local scans = ui:GetPerformanceStats().ownershipBuilds
showNative(tip, "item:900003", "GetQuestItem", {"reward", 1})
assert(context.lastTooltip.result == before and ui:GetPerformanceStats().ownershipBuilds == scans)

H.modifiers.alt = true
local original = text(tip)
showNative(tip, "item:900003", "GetQuestItem", {"reward", 1})
assert(text(tip) == original, "Alt does not change the tooltip")
includes(tip, "Guide fixture")
assert(levelSeen == 47 and roleSeen == "Protection")
assert(tip.lines[2] == "Native enchant" and tip.lines[3] == "Native source")
oneSection(tip)
H.modifiers.alt = false
showNative(tip, "item:900003", "GetQuestItem", {"reward", 1})
assert(text(tip) == original)
includes(tip, "Guide fixture")

group, detected = 2, "Retribution"
onEvent(core, "ACTIVE_COMBAT_CONFIG_CHANGED"); H.settle()
local retri = assert(text(tip):find("\nRetribution\n", 1, true))
local prot = assert(text(tip):find("\nProtection\n", 1, true))
assert(retri < prot and prot < assert(text(tip):find("\nHoly\n", 1, true)))
group, detected = 1, "Protection"
onEvent(core, "ACTIVE_COMBAT_CONFIG_CHANGED"); H.settle()
excludes(tip, "(Off-spec)")
excludes(tip, "(Dual)")
assert(addon:GetCharacterDB().tooltipTalentSpecs[2] == "Retribution")
assert(text(tip):find("\nProtection\n", 1, true) < text(tip):find("\nRetribution\n", 1, true))
assert(text(tip):find("\nRetribution\n", 1, true) < text(tip):find("\nHoly\n", 1, true))

local events = addon.uiEventFrame
H.equipped[12] = 900013
events:GetScript("OnEvent")(events, "PLAYER_EQUIPMENT_CHANGED"); H.settle()
includes(tip, "|t Major upgrade\n+7.0 pts vs Lower ring")

showNative(tip, "item:900005", "GetMerchantItem", {1})
includes(tip, "Requires Level 55")
includes(tip, "Highest known score at Level 55")
includes(tip, "Estimated +98.0 pts vs Lower ring at Level 55")
addon.GetRecommendationHistory = function(_, id, class, spec, phase, slot)
    assert(class == "Paladin" and phase == "PR" and slot == "Ring")
    return {selected = {phase = phase, status = spec == "Protection" and "rated" or "conditional", rank_group = "bis"}}
end
level = 60
onEvent(core, "PLAYER_LEVEL_UP"); H.settle()
includes(tip, "|cffffd152Pre-Raid BiS|r  Protection")
local _, badges = text(tip):gsub("BiS|r", "")
assert(badges == 1)
includes(tip, "Pre-Raid · Top tier #1/7 at Lv 60 (100% of best)")
local topTier = tip.rowColors["|cffffd152Pre-Raid BiS|r  Protection"]
assert(topTier[1] == 1 and topTier[2] == 128/255 and topTier[3] == 0)
oneSection(tip)
showNative(tip, "item:900013", "GetInventoryItem", {"player", 12})
includes(tip, "Equipped")
includes(tip, "Best you own for this slot")
excludes(tip, "pts vs")

addon:GetAccountDB().profile.tooltips.enabled = false
showNative(ItemRefTooltip, "item:900003")
assert(#ItemRefTooltip.lines == 3)
''')

    def test_higher_level_tooltips_rank_at_first_eligible_level_and_forecast_the_swap(self):
        self.lua_run(r'''
profile.leveling.weights = {{1, 49, weights}, {50, 59, {stamina = 1, intellect = 5}}}
profile.pre_raid.weights = {stamina = 1, intellect = 10}
rows["900005"][5].intellect = 10
gear(900014, "Level 54 ring", "Ring", 200, nil, 54)
gear(900015, "Level 56 ring", "Ring", 300, nil, 56)
gear(900016, "Level 60 ring", "Ring", 150, nil, 60)
rows["900016"][5].intellect = 15
gear(900017, "Level 61 ring", "Ring", 1200, nil, 61)
slots[#slots + 1] = "Head"
local data = BigBiSListData.stat_rank
data.item_fields[#data.item_fields + 1] = "armor_type"
data.equipment.Paladin.armor_tiers = {{level = 1, types = {"Cloth"}}, {level = 40, types = {"Plate"}}}
gear(900018, "Level 30 plate helm", "Head", 30, nil, 30)
gear(900019, "Level 40 cloth helm", "Head", 40, nil, 40)
rows["900018"][8], rows["900019"][8] = "Plate", "Cloth"

H.equipped[11], H.equipped[12] = 900001, 900002
nativeRequirements[900005] = "|cffff2020Requires Level 55|r"
local tip = ItemRefTooltip
showNative(tip, "item:900005")
for _, spec in ipairs({"Protection", "Retribution"}) do
    local block = assert((text(tip) .. "\n \n"):match("\n" .. spec .. "\n(.-)\n \n"))
    assert(block:find("Likely upgrade at Level 55", 1, true) < block:find("Good option at Level 55", 1, true))
end
assert(tip.lines[4] == nativeRequirements[900005])
local _, requirements = text(tip):gsub("Requires Level 55", "")
assert(requirements == 1)
includes(tip, "Estimated +146.0 pts vs Blood Ritual Ring at Level 55")
oneSection(tip)

local live = rating:GetContext("Paladin", "Protection", "LEVELING", 47, ui.currentOwned)
local current = rating:GetPlacement(live, "Finger0", {"Ring"})
assert(current.count == 6 and not current.byVariant["900005"])
local candidate = rating:GetTooltipItem(900005, "item:900005")
local result = rating:CompareTooltipItem(live, candidate, true, nil, nil, { live = true })
assert(not result.delta and not result.placement.rank and not result.bis, "Acquisition assessment requires eligibility")
local forecast = rating:CompareTooltipItem(live, candidate, false, nil, false, {live = true, lookahead = true}).forecast
assert(forecast.level == 55 and forecast.delta == 146)
showNative(tip, "item:900005")
includes(tip, "Good option at Level 55")
H.settle()
includes(tip, "Good option at Level 55")
includes(tip, "Estimated +146.0 pts vs Blood Ritual Ring at Level 55")
assert(tip.lines[4] == nativeRequirements[900005])
oneSection(tip)

showNative(GameTooltip, "item:900016", "GetMerchantItem", {1})
includes(GameTooltip, "Pre-Raid · Top tier Tied #1/10 at Lv 60 (100% of best)")
includes(GameTooltip, "Likely upgrade at Level 60")
includes(GameTooltip, "Estimated +296.0 pts vs Blood Ritual Ring at Level 60")
showNative(GameTooltip, "item:900017", "GetMerchantItem", {1})
includes(GameTooltip, "Outside Pre-Raid rankings")
excludes(GameTooltip, "Likely upgrade")

level = 55
addon:RefreshTooltipPlayerContext()
showNative(GameTooltip, "item:900005", "GetMerchantItem", {1})
includes(GameTooltip, "Good option at Level 55")
includes(GameTooltip, "|t Major upgrade\n+146.0 pts vs Blood Ritual Ring")
excludes(GameTooltip, "Estimated +146.0 pts vs Blood Ritual Ring at Level 55")

level = 20
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900018")
includes(tip, "Requires Level 30")
includes(tip, "Can equip at Level 40")
includes(tip, "Good option at Level 40")
level = 35
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900018")
H.settle()
includes(tip, "Can equip at Level 40")
excludes(tip, "Requires Level 30")
includes(tip, "Good option at Levels 40–59")

level = 59
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900005")
includes(tip, "Better options at Level 59")
excludes(tip, "59–60")
''')

    def test_auction_forecast_includes_banked_gear_that_unlocks_at_the_same_level(self):
        self.lua_run(r'''
level = 49
slots[#slots + 1] = "Hands"
gear(900020, "Worn gloves", "Hands", 30, nil, 49)
gear(900021, "Gloves from the bank", "Hands", 39, nil, 50)
gear(900022, "Auction gloves", "Hands", 55.1, nil, 50)
gear(900023, "Equal gloves", "Hands", 39, nil, 50)
H.equipped[10] = 900020
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links = true, {"item:900021"}
local tip = GameTooltip
local settings = addon:GetAccountDB().profile.gearHighlights
for _, enabled in ipairs({true, false}) do
    settings.auction = enabled
    showNative(tip, "item:900022", "GetAuctionItem", {1})
    includes(tip, "Highest known score at Level 50")
    includes(tip, "Likely upgrade at Level 50\nEstimated +16.1 pts vs Gloves from the bank at Level 50")
    includes(tip, "Includes cached bank gear")
    showNative(tip, "item:900023", "GetAuctionItem", {1})
    includes(tip, "Likely sidegrade at Level 50")
    excludes(tip, "Likely upgrade")
end

local context = rating:GetContext("Paladin", "Protection", "LEVELING", level, ui.currentOwned)
local item = rating:GetTooltipItem(900022, "item:900022")
local assessment = rating:CompareTooltipItem(context, item, false, nil, true, {live = true})
assert(assessment.placement.status == "level" and assessment.delta == nil and not assessment.forecast)
local incomplete = rating:GetContext("Paladin", "Protection", "LEVELING", level, {equippedSlots = {}, bagsIncomplete = true})
local unavailable = rating:CompareTooltipItem(incomplete, item, false, nil, true, {lookahead = true})
assert(unavailable.placement.rank == 1 and unavailable.forecast.status == "unavailable" and not unavailable.forecast.delta)

showNative(tip, "item:900022", "GetAuctionItem", {1})
local protection = assert((text(tip) .. "\n \n"):match("\nProtection\n(.-)\n \n"))
local _, ranks = protection:gsub("Highest known score at Level 50", "")
assert(ranks == 1, protection)
excludes(tip, "Outdoor")
excludes(tip, "Dungeon")
''')

    def test_auction_forecast_waits_for_an_unknown_owned_equip_level(self):
        self.lua_run(r'''
level = 49
slots[#slots + 1] = "Hands"
gear(900020, "Worn gloves", "Hands", 30)
rows["900020"][4] = nil
gear(900021, "Auction gloves", "Hands", 46.1, nil, 50)
H.equipped[10] = 900020
local knownLevel, originalInfo, originalInstant = false, GetItemInfo, GetItemInfoInstant
GetItemInfo = function(value)
    if itemId(value) == 900020 then
        if knownLevel then return "Worn gloves", "item:900020", 2, 52, 49 end
        return nil
    end
    return originalInfo(value)
end
GetItemInfoInstant = function(value)
    if itemId(value) == 900020 then return 900020, "Armor", "Cloth", "INVTYPE_HAND", nil, 4, 1 end
    return originalInstant(value)
end
local tip = GameTooltip
showNative(tip, "item:900021", "GetAuctionItem", {1})
includes(tip, "Gear comparison unavailable at Level 50")
excludes(tip, " pts")
excludes(tip, "empty slot")
showNative(tip, "item:900020")
includes(tip, "Stats unavailable")
knownLevel = true
rating:InvalidateItem(900020)
showNative(tip, "item:900021", "GetAuctionItem", {1})
includes(tip, "Estimated +16.1 pts vs Worn gloves at Level 50")
''')

    def test_owned_comparison_matches_reformatted_links_without_proposing_an_extra_copy(self):
        self.lua_run(r'''
H.equipped[11], H.equipped[12] = 900001, 900002
local bagLink = "|cnIQ3:|Hitem:900003::::::::47:1486|h[Bag ring]|h|r"
C_Container = {
    GetContainerNumSlots = function(bag) return bag == 0 and 1 or 0 end,
    GetContainerItemID = function(bag) if bag == 0 then return 900003 end end,
    GetContainerItemLink = function(bag) if bag == 0 then return bagLink end end,
}
local context = rating:GetContext("Paladin", "Protection", "LEVELING", level, ui:GetOwnedSnapshot())
local item = rating:GetTooltipItem(900003, "item:900003")
local existing = rating:CompareTooltipItem(context, item, false, nil, false)
assert(existing.delta == 0 and existing.status == "best_owned", "The link refers to the ring already in the bag")
local extra = rating:CompareTooltipItem(context, item, false, nil, true)
assert(extra.delta == 1, "An auction listing can provide a second ring")
''')

    def test_tooltip_ranges_reuse_the_guide_summary_and_find_the_first_stronger_item(self):
        self.lua_run(r'''
slots[#slots + 1] = "Hands"
gear(900014, "Earlier gloves", "Hands", 100, nil, 47)
gear(900015, "Later gloves", "Hands", 103, nil, 49)
gear(900016, "Tied gloves", "Hands", 103, nil, 50)
for offset = 1, 13 do gear(900020 + offset, "Gloves " .. offset, "Hands", offset) end
H.equipped[10] = 900014
local tip = GameTooltip
showNative(tip, "item:900014")
includes(tip, "Highest known score at Level 47")
showNative(tip, "item:900015", "GetAuctionItem", {1})
includes(tip, "Highest known score at Level 49")
includes(tip, "Estimated +3.0 pts vs Earlier gloves at Level 49")
H.settle()
includes(tip, "Among the best at Levels 49–59")
assert(tip.rebuilds and #rating.levelingSummaryQueue == 0)

local context = rating:GetGuideContext("Paladin", "Protection", "LEVELING", 47, "Human", "Alliance")
local pool = rating:GetGuidePlacement(context, "Hands")
local leader = pool.byVariant["900014"]
local summary = rating:GetLevelingSummary(context)
local record = assert(rating:GetLevelingRecord(summary, "Hands", leader.item.key))
local range = assert(record.strength[1])
assert(range.firstLevel == 47 and range.lastLevel == 59)
local stronger = assert(rating:GetLevelingSuccessor(summary, leader))
assert(stronger.level == 49 and stronger.name == "Later gloves")

level = 50
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900014")
includes(tip, "Among the best at Levels 47–59")
showNative(tip, "item:900015")
includes(tip, "Tied for highest known score at Level 50")
''')

    def test_bank_snapshot_copy_counts_and_legal_weapon_and_ring_swaps(self):
        self.lua_run(r'''
gear(900019, "Loot ring", "Ring", 6)
local bankLinks = {"item:900004", "item:900004"}
local bags = {"item:900003"}
local bankReads, unreadable = 0, false
C_Bank = {FetchPurchasedBankTabIDs = function(bankType)
    assert(bankType == Enum.BankType.Character)
    bankReads = bankReads + 1
    return {20}
end}
C_Container = {
    GetContainerNumSlots = function(bag)
        if bag == 20 then return #bankLinks end
        return bag == 0 and #bags or 0
    end,
    GetContainerItemID = function(bag, slot)
        if bag == 20 and unreadable then error("Unavailable bank slot") end
        return bag == 20 and itemId(bankLinks[slot]) or (bag == 0 and itemId(bags[slot]) or nil)
    end,
    GetContainerItemLink = function(bag, slot)
        if bag == 20 then return bankLinks[slot] end
        if bag == 0 then return bags[slot] end
    end,
}
ItemLocation = {
    CreateFromBagAndSlot = function(_, bag, slot) return {bag = bag, slot = slot} end,
}
C_Item = {GetItemGUID = function(location)
    if location.bag == 20 then return "bank-" .. location.slot end
    if location.bag == 0 and location.slot == 2 then return "bank-1" end
end}
H.equipped[11], H.equipped[12] = 900001, 900002
H.equipped[16], H.equipped[17] = 900007, 900008
addon:InitUIEvents()
local frame = addon.uiEventFrame
local fire = frame:GetScript("OnEvent")
local tip = ItemRefTooltip
showNative(tip, "item:900019", "GetLootItem", {1})
includes(tip, "Downgrade\n-2.0 pts vs Stronger ring")
showNative(tip, "item:900003")
includes(tip, "In bags")
includes(tip, "Best you own for this slot")
excludes(tip, "In your best gear")
excludes(tip, ", Best you own for this slot")
excludes(tip, "Hold Alt")
excludes(tip, "includes bank gear")
assert(not ui:ScanBankItems() and bankReads == 0)

fire(frame, "BANKFRAME_OPENED"); H.settle()
includes(tip, "You own a stronger ring · Bank ring")
includes(tip, "Includes cached bank gear")
assert(tip.lines[2] == "Native enchant" and tip.lines[3] == "Native source")
showNative(tip, "item:900003")
local bank = addon:GetCharacterDB().bankCache
assert(bank.scanned and #bank.links == 2 and bankReads == 1)
unreadable, bankLinks = true, {"item:900006"}
fire(frame, "PLAYERBANKSLOTS_CHANGED"); H.settle()
assert(addon:GetCharacterDB().bankCache == bank)
includes(tip, "You own a stronger ring · Bank ring")
fire(frame, "BANKFRAME_CLOSED"); H.settle()
fire(frame, "BAG_UPDATE_DELAYED"); H.settle()
assert(bankReads == 2 and addon:GetCharacterDB().bankCache == bank)
includes(tip, "You own a stronger ring · Bank ring")
showNative(tip, "item:900004")
includes(tip, "In bank (last visit)")
bags[2] = "item:900004"
fire(frame, "BAG_UPDATE_DELAYED"); H.settle()
local count = 0
for _, entry in ipairs(ui.currentOwned.gearCopies) do if entry.item_id == 900004 then count = count + 1 end end
assert(count == 2, "One cached bank copy moved into a bag")
includes(tip, "In bags")

unreadable, bankLinks = false, {}
fire(frame, "BANKFRAME_OPENED"); H.settle()
assert(#addon:GetCharacterDB().bankCache.links == 0)
excludes(tip, "In bank (last visit)")
showNative(tip, "item:900009", "GetLootItem", {1})
includes(tip, "Downgrade\n-1.0 pts vs Worn sword + Worn off hand")
H.equipped[16], H.equipped[17] = 900009, nil
fire(frame, "PLAYER_EQUIPMENT_CHANGED"); H.settle()
showNative(tip, "item:900010", "GetMerchantItem", {1})
includes(tip, "Downgrade\n-6.0 pts vs Great sword")
showNative(tip, "item:900011")
includes(tip, "No legal swap")

H.equipped[11], H.equipped[12] = 900006, 900002
fire(frame, "PLAYER_EQUIPMENT_CHANGED"); H.settle()
showNative(tip, "item:900006", "GetLootItem", {1})
includes(tip, "Sidegrade\n0.0 pts vs Unique ring")
excludes(tip, "vs Blood Ritual Ring")
showNative(tip, "item:900012", "GetLootItem", {1})
includes(tip, "Fills your empty trinket slot")
oneSection(tip)
''')

    def test_tooltip_distinguishes_spec_restrictions_from_rank_scope(self):
        self.lua_run(r'''
gear(900014, "One-handed axe", "One Hand", 15, nil, nil, "Axe")
addon.ComparisonItemInScope = function(_, id) return id ~= 900013 end
local tip = GameTooltip
showNative(tip, "item:900014")
includes(tip, "No rank for this spec")
excludes(tip, "Est.")
showNative(tip, "item:900013")
includes(tip, "Protection\nOutside Leveling rankings")
excludes(tip, "Est.")
level = 60
addon:RefreshTooltipPlayerContext()
showNative(tip, "item:900013")
includes(tip, "Protection\nOutside Pre-Raid rankings")
excludes(tip, "Est.")
oneSection(tip)
''')

    def test_exact_link_stats_loading_and_projected_pool(self):
        self.lua_run(r'''
local id = 900020
local linkA = "item:900020:8:9:0:0:0:-7:504:47:0:0:0:1:700"
local linkB = "item:900020:8:9:0:0:0:-7:504:47:0:0:0:1:800"
assert(addon:GetItemVariantIdFromLink(linkA) == rating:NormalizeLink(id, linkA))
assert(addon:GetItemVariantIdFromLink(linkA) ~= addon:GetItemVariantIdFromLink(linkB))
local ready, callbacks, reads = false, {}, {}
local fallbackInfo, fallbackInstant = GetItemInfo, GetItemInfoInstant
GetItemInfo = function(value)
    if itemId(value) ~= id then return fallbackInfo(value) end
    if ready then return "Tuned ring", value, 3, 48, 44, "Armor", "Misc", 1, "INVTYPE_FINGER", "ring" end
end
GetItemInfoInstant = function(value)
    if itemId(value) == id then return id, "Armor", "Misc", "INVTYPE_FINGER", "ring", 4, 0 end
    return fallbackInstant(value)
end
C_Item = {
    IsItemDataCachedByID = function(item) return item ~= id or ready end,
    GetItemStats = function(link)
        assert(link:find(":0:0:0:0:0:-7:504", 1, true), link)
        local bonus = tonumber(link:match(":(%d+)$"))
        reads[bonus] = (reads[bonus] or 0) + 1
        return {ITEM_MOD_STAMINA_SHORT = bonus == 700 and 10 or 13}
    end,
}
Item = {CreateFromItemID = function(_, item)
    return {ContinueOnItemLoad = function(_, callback) callbacks[item] = callback end,
        GetItemName = function() return "Tuned ring" end}
end}
H.equipped[11], H.equipped[12] = 900001, 900002
local tip = GameTooltip
showNative(tip, "item:900003")
H.settle()
local rebuilds = tip.rebuilds or 0
showNative(tip, linkA)
includes(tip, "Waiting for item stats")
assert(callbacks[id] and not reads[700])
showNative(tip, "item:900003")
local original = text(tip)
ready = true
callbacks[id](); H.settle()
assert(text(tip) == original and (tip.rebuilds or 0) == rebuilds)
local context = rating:GetContext("Paladin", "Protection", "LEVELING", 47, ui.currentOwned)
local pool = rating:GetPlacement(context, "Finger1", {"Ring"})
local originalCount = #pool.rows
showNative(tip, linkA)
includes(tip, "Good option at Level 47")
includes(tip, "Possible upgrade\n+6.0 pts vs Blood Ritual Ring · Scored stats only")
assert(reads[700] == 1 and #pool.rows == originalCount)
showNative(tip, linkB)
includes(tip, "Possible upgrade\n+9.0 pts vs Blood Ritual Ring · Scored stats only")
assert(reads[800] == 1 and #pool.rows == originalCount)
showNative(tip, linkB)
assert(reads[800] == 1)
oneSection(tip)

tip:Hide()
addon:ScheduleItemTooltipRefresh()
H.settle()
assert((tip.rebuilds or 0) == rebuilds)

-- Loading while the same item stays under the cursor also uses the native source.
ready = false
rating:InvalidateItem(id)
rating.loadedItems[id] = nil
showNative(tip, linkA, "GetQuestItem", {"reward", 1})
includes(tip, "Waiting for item stats")
ready = true
callbacks[id](); H.settle()
includes(tip, "Possible upgrade\n+6.0 pts vs Blood Ritual Ring · Scored stats only")
-- The stat load can publish immediately; all visible spec ranges share one subsequent redraw.
assert(tip.rebuilds >= rebuilds + 1 and tip.rebuilds <= rebuilds + 2 and tip.lines[3] == "Native source")
oneSection(tip)

C_Item.GetItemStats = function() return {ITEM_MOD_STAMINA_SHORT = 9} end
C_TooltipInfo = {GetHyperlink = function() return {lines = {{leftText = "<Random enchantment>"}}} end}
rating:InvalidateItem(id)
showNative(tip, "item:900020")
includes(tip, "Stats unavailable")
excludes(tip, "Projected ·")
''')
