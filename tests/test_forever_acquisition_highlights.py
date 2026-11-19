"""Native acquisition highlights and frame recycling in the Lua UI harness."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


FIXTURE = r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load("forever")
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
local highlights = addon.AcquisitionHighlights
local publishedRanks = BigBiSListData.stat_rank
local level = 47
UnitClassBase = function() return "PALADIN" end
UnitRace = function() return "Human", "Human" end
UnitLevel = function() return level end
GetNumSpecGroups = function() return 2 end
C_SpecializationInfo = {GetActiveSpecGroup = function() return 1 end}
addon.DetectPlayerSpec = function()
    return "Protection", {{displayName = "Protection", icon = 10101}, {displayName = "Holy", icon = 20202}}
end
addon:GetCharacterDB().tooltipTalentSpecs[2] = "Holy"
addon.ComparisonItemInScope = function() return true end
Enum = {LootSlotType = {Item = 1, Money = 2, Currency = 3}}

local slots = {"Head", "Neck"}
local items = {}
local function item(id, slot, stamina, intellect)
    items[tostring(id)] = {id, "Fixture gear " .. id, slot, 1, {stamina = stamina, intellect = intellect}}
end
item(901001, "Head", 6, 0)
item(901002, "Head", 10, 0)
item(901003, "Head", 9, 0)
item(901004, "Head", 12, 0)
item(901005, "Head", 3, 20)
item(901006, "Head", 2, 0)
item(901007, "Neck", 8, 0)
local function profile(weights)
    return {leveling = {slots = slots, weights = {{1, 59, weights}}}, pre_raid = {slots = slots, weights = weights}}
end
BigBiSListData.stat_rank = {version = "forever-stat-ranks-1", equipment = {Paladin = {}},
    common_slots = slots, profiles = {["Paladin/Protection"] = profile({stamina = 1}), ["Paladin/Holy"] = profile({intellect = 1})},
    item_fields = {"id", "name", "slot", "level", "stats"}, items = items}
local function idOf(link)
    return tonumber(link) or tonumber(tostring(link):match("item:(%d+)"))
end
local function link(id)
    return id and ("item:" .. id)
end
local prices = {[901010] = 15, [901011] = 50}
local cold = {}
GetItemInfo = function(value)
    local id = idOf(value)
    if not id or cold[id] then return end
    local info = items[tostring(id)]
    local name = info and info[2] or "Item " .. id
    return name, link(id), 2, 1, 1, "Armor", "Misc", 1, "INVTYPE_HEAD", 0, prices[id] or 0
end
GetItemInfoInstant = function(value)
    local id = idOf(value)
    local info = items[tostring(id)]
    local slot = info and info[3]
    local equip = slot == "Neck" and "INVTYPE_NECK" or (info or id == 901020) and "INVTYPE_HEAD" or ""
    return id, "Armor", "Misc", equip, 0, 4, 0
end
C_Item = {GetItemInfo = GetItemInfo, GetItemInfoInstant = GetItemInfoInstant,
    IsItemDataCachedByID = function(id) return not cold[id] end,
    GetItemStats = function(value)
        local id = idOf(value)
        if id == 901020 and not cold[id] then return {ITEM_MOD_STAMINA_SHORT = 15} end
        if id == 901006 and tostring(value):find(":700", 1, true) then return {ITEM_MOD_STAMINA_SHORT = 14} end
    end}
local coldCallbacks = {}
Item = {CreateFromItemID = function(_, id)
    return {ContinueOnItemLoad = function(_, callback) coldCallbacks[id] = callback end}
end}
local colors = {[0] = {157, 157, 157}, {255, 255, 255}, {30, 255, 0}, {0, 112, 221}, {163, 53, 238}, {255, 128, 0}}
GetItemQualityColor = function(quality)
    local rgb = colors[quality or 1]
    return rgb[1]/255, rgb[2]/255, rgb[3]/255
end
H.equipped[1] = 901001
GetContainerNumSlots = function(bag) return bag == 0 and 1 or 0 end
GetContainerItemID = function() return 901002 end
GetContainerItemLink = function() return link(901002) end
hooksecurefunc = function(object, key, callback)
    if type(object) == "string" then object, key, callback = _G, object, key end
    local method = assert(object[key])
    object[key] = function(...)
        local results = {method(...)}
        callback(...)
        return unpack(results)
    end
end
local function row(parent, index, name)
    local button = CreateFrame("Button", name, parent)
    button:SetSize(175, 40)
    button.GetID = function(self) return self.slotIndex end
    button.slotIndex = index
    return button
end
local function bagView(contents)
    GetContainerNumSlots = function(bag) return bag == 0 and #contents or 0 end
    GetContainerItemLink = function(bag, slot) return bag == 0 and contents[slot] or nil end
    GetContainerItemID = function(bag, slot) return idOf(GetContainerItemLink(bag, slot)) end
    local panel, rows = CreateFrame("Frame", nil, UIParent), {}
    for index in ipairs(contents) do
        rows[index] = row(panel, index)
        rows[index].GetBagID = function() return 0 end
    end
    panel.EnumerateValidItems = function() return ipairs(rows) end
    panel.UpdateItems = function() end
    ContainerFrameUtil_EnumerateContainerFrames = function() return ipairs({panel}) end
    return panel, rows
end
local function scrollBox(rows)
    return {rows = rows, ForEachFrame = function(self, fn)
        for _, frame in ipairs(self.rows) do fn(frame) end
    end}
end
ScrollUtil = {
    AddInitializedFrameCallback = function(box, fn, owner) box.initRow = function(frame) fn(owner, frame) end end,
    AddReleasedFrameCallback = function(box, fn, owner) box.releaseRow = function(frame) fn(owner, frame) end end,
}
local function event(name, ...)
    local frame = highlights.eventFrame
    frame:GetScript("OnEvent")(frame, name, ...)
    H.settle()
end
local function mark(row, item)
    local _, displayed = highlights:GetTooltipOffer(row, idOf(item), type(item) == "string" and item or link(item))
    return displayed
end
local function showTip(row, item)
    GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
    GameTooltip:SetHyperlink(item)
    GameTooltip:Show()
    return table.concat(GameTooltip.lines, "\n")
end
'''


class AcquisitionHighlightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, script):
        if not self.lua:
            self.skipTest("Lua 5.1 is unavailable")
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, encoding="utf-8", capture_output=True, timeout=90,
            input=FIXTURE + script + '\nassert(#H.errors == 0, table.concat(H.errors, "\\n"))\n',
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_storage_refresh_slices_cold_work_and_reuses_results_after_non_gear_changes(self):
        self.run_lua(r'''
local contents = {link(901002), link(901006), link(901005)}
local panel, rows = bagView(contents)
local comparisons, elapsed = 0, 0
debugprofilestop = function()
    elapsed = elapsed + 0.002
    return elapsed
end
local compare = rating.GetStorageComparison
function rating:GetStorageComparison(...)
    comparisons, elapsed = comparisons + 1, elapsed + 2.1
    return compare(self, ...)
end
addon:InitUIEvents()
panel:Hide()
highlights:Initialize(); H.settle()
assert(comparisons == 0 and not addon.dataIndex, "hidden bags do no cold indexing or scoring")

panel:Show()
assert(not showTip(rows[1], contents[1]):find("Big BiS List", 1, true), "a cold hover returns the native tooltip")
assert(H.tick() and highlights.queued and not addon.dataIndex, "the cold index yields before publishing")
local syncIndex = addon:GetDataIndex()
local scoringFrames = 0
while highlights.queued do
    local before = comparisons
    assert(H.tick())
    if comparisons > before then
        scoringFrames = scoringFrames + 1
        assert(comparisons - before <= 2, "comparisons must yield within the frame budget")
    end
end
H.settle()
assert(scoringFrames > 1 and addon:GetDataIndex() == syncIndex and mark(rows[1], 901002))
assert(table.concat(GameTooltip.lines, "\n"):find("Big BiS List", 1, true), "the same hovered item gets its addon lines")
GameTooltip:Hide()

local original, priorComparisons = mark(rows[1], 901002).result, comparisons
panel:Hide(); panel:Show(); H.settle()
assert(comparisons == priorComparisons and mark(rows[1], 901002).result == original)
contents[2] = link(901006)
contents[4] = link(901099)
local junk = row(panel, 4)
junk.GetBagID = function() return 0 end
rows[4] = junk
panel:UpdateItems()
local inventory = addon.uiEventFrame
inventory:GetScript("OnEvent")(inventory, "BAG_UPDATE_DELAYED")
event("BAG_UPDATE_DELAYED")
assert(ui:GetOwnedSnapshot()[901099] == "bag", "the full ownership snapshot records non-gear additions")
assert(comparisons == priorComparisons and mark(rows[1], 901002).result == original)
assert(not mark(rows[2], 901006) and not mark(junk, 901099), "negative results and non-gear stay unmarked")
''')

    def test_storage_refresh_discards_a_cold_hover_and_stale_gear_when_a_slot_changes(self):
        self.run_lua(r'''
local contents = {link(901002), link(901006)}
local panel, rows = bagView(contents)
local elapsed = 0
debugprofilestop = function()
    elapsed = elapsed + 0.004
    return elapsed
end
addon:InitUIEvents()
panel:Hide()
highlights:Initialize(); H.settle()
panel:Show()
assert(not showTip(rows[1], contents[1]):find("Big BiS List", 1, true))
assert(H.tick() and highlights.queued)

contents[1], contents[2] = link(901004), link(901002)
panel:UpdateItems()
local inventory = addon.uiEventFrame
inventory:GetScript("OnEvent")(inventory, "BAG_UPDATE_DELAYED")
event("BAG_UPDATE_DELAYED")
assert(not table.concat(GameTooltip.lines, "\n"):find("Big BiS List", 1, true), "a tooltip for the old slot item stays unannotated")
assert(not mark(rows[1], 901002) and not mark(rows[2], 901002), "the older snapshot may not publish a winner")
assert(mark(rows[1], 901004).result.delta == 6)
assert(showTip(rows[1], contents[1]):find("+6.0 pts", 1, true))
''')

    def test_bags_and_personal_bank_mark_owned_upgrades_and_refresh_reused_slots(self):
        self.run_lua(r'''
local contents = {[0] = {link(901002), link(901005)}, [20] = {link(901004)}}
Enum.BankType = {Character = 1, Account = 2}
C_Bank = {FetchPurchasedBankTabIDs = function(kind) assert(kind == 1); return {20} end}
C_Container = {
    GetContainerNumSlots = function(bag) return contents[bag] and #contents[bag] or 0 end,
    GetContainerItemID = function(bag, slot) return contents[bag] and idOf(contents[bag][slot]) end,
    GetContainerItemLink = function(bag, slot) return contents[bag] and contents[bag][slot] end,
}
local bags, combined = CreateFrame("Frame", nil, UIParent), CreateFrame("Frame", nil, UIParent)
local first, second = row(bags, 1), row(combined, 2)
first.GetBagID, second.GetBagID = function() return 0 end, function() return 0 end
bags.EnumerateValidItems = function() return ipairs({first}) end
combined.EnumerateValidItems = function() return ipairs({second}) end
bags.UpdateItems, combined.UpdateItems = function() end, function() end
ContainerFrameUtil_EnumerateContainerFrames = function() return ipairs({bags, combined}) end
BankFrame = CreateFrame("Frame", nil, UIParent)
local panel = CreateFrame("Frame", nil, BankFrame)
BankFrame.BankPanel = panel
local bankItem = row(panel, 1)
bankItem.GetBankTabID, bankItem.GetContainerSlotID = function() return 20 end, function() return 1 end
local bankKind = 1
panel.GetActiveBankType = function() return bankKind end
panel.EnumerateValidItems = function() return next, {[bankItem] = true} end
panel.GenerateItemSlotsForSelectedTab, panel.RefreshAllItemsForSelectedTab = function() end, function() end
ui.personalBankOpen = true
assert(ui:ScanBankItems())
highlights:Initialize(); H.settle()
assert(not mark(first, 901002))
local offered = assert(mark(bankItem, 901004))
assert(offered.entry.owned and not offered.ownedBaseline and offered.result.delta == 6)
local badge
for _, child in ipairs(bankItem.children) do if child.border then badge = child end end
assert(badge and not badge.animation and not badge.glow and badge.icon:IsShown())
H.expectBounded(badge, bankItem, "bank badge")
for _, edge in ipairs(badge.border) do H.expectBounded(edge, badge, "bag badge border") end
assert(mark(second, 901005).spec.name == "Holy", "An owned off-spec upgrade compares with worn gear")
assert(mark(bankItem, 901004).result.delta == 6)
local tip = showTip(first, link(901002))
assert(tip:find("+4.0 pts", 1, true) and tip:find("Finger", 1, true) == nil)
assert(tip:find("Stronger option you own · Fixture gear 901004 · In bank (last visit)", 1, true))
assert(not tip:find("vs the best gear you own", 1, true))
ui.personalBankOpen = false
event("BANKFRAME_CLOSED")
assert(not mark(bankItem, 901004) and not mark(first, 901002))
ui.personalBankOpen = true
local getLink = C_Container.GetContainerItemLink
C_Container.GetContainerItemLink = function(bag, slot)
    if bag == 20 then error("Unreadable bank tab") end
    return getLink(bag, slot)
end
assert(not ui:ScanBankItems() and addon:GetCharacterDB().bankCache.locations[1] == "20:1")
highlights:ScheduleRefresh(); H.settle()
assert(not mark(first, 901002) and not mark(bankItem, 901004))
C_Container.GetContainerItemLink = getLink
highlights:ScheduleRefresh(); H.settle()
assert(mark(bankItem, 901004))
contents[0][1], contents[20][1] = contents[20][1], contents[0][1]
assert(ui:ScanBankItems())
ui:Invalidate("ownership", "withdraw-winner"); event("BAG_UPDATE_DELAYED")
assert(mark(first, 901004) and not mark(bankItem, 901002))
contents[0][1], contents[20][1] = contents[20][1], contents[0][1]
assert(ui:ScanBankItems())

H.equipped[1] = 901002
ui:Invalidate("ownership", "equip-from-bag"); event("BAG_UPDATE_DELAYED")
assert(not mark(first, 901002) and mark(bankItem, 901004).result.delta == 2)
contents[0][1] = "item:901006:0:0:0:0:0:0:0:47:0:0:0:1:700"
ui:Invalidate("ownership", "exact-variant-move"); bags:UpdateItems(); H.settle()
assert(not mark(first, 901002) and mark(first, contents[0][1]).result.delta == 4)

contents[0][1], cold[901020] = link(901020), true
ui:Invalidate("ownership", "cold-bag-item"); bags:UpdateItems(); H.settle()
assert(not mark(first, 901020) and not mark(bankItem, 901004) and coldCallbacks[901020])
cold[901020] = nil
coldCallbacks[901020](); H.settle()
assert(mark(first, 901020).result.delta == 5 and not mark(bankItem, 901004))

addon:GetAccountDB().profile.gearHighlights.bags = false
highlights:ScheduleRefresh(); H.settle()
assert(not mark(first, 901020) and not mark(bankItem, 901004))
contents[0][1] = link(901006)
ui:Invalidate("ownership", "bank-visible-winner"); event("BAG_UPDATE_DELAYED")
assert(mark(bankItem, 901004))
bankKind = 2
panel:GenerateItemSlotsForSelectedTab(); H.settle()
assert(not mark(bankItem, 901004), "The personal-bank adapter excludes account bank rows")
bankKind, ui.personalBankOpen = 1, false
event("BANKFRAME_CLOSED")
assert(not mark(bankItem, 901004))
''')

    def test_bags_choose_one_off_spec_belt_and_explain_close_alternatives(self):
        self.run_lua(r'''
slots[#slots + 1] = "Waist"
BigBiSListData.stat_rank.profiles["Paladin/Retribution"] = profile({strength = 1})
local active, group = "Retribution", 1
addon.DetectPlayerSpec = function()
    return active, {{displayName = "Retribution", icon = 10101}, {displayName = "Protection", icon = 20202}}
end
C_SpecializationInfo.GetActiveSpecGroup = function() return group end
addon:GetCharacterDB().tooltipTalentSpecs[2] = "Protection"
item(901031, "Waist", 6, 0)
item(901032, "Waist", 14, 0)
item(901033, "Waist", 11, 0)
item(901034, "Waist", 13, 0)
H.equipped[1], H.equipped[6] = nil, 901031
local panel, rows = bagView({link(901032), link(901033), link(901034)})

highlights:Initialize(); H.settle()
local best = assert(mark(rows[1], 901032))
assert(best.spec.name == "Protection" and best.result.delta == 8)
assert(not mark(rows[2], 901033) and not mark(rows[3], 901034))
local inferior = showTip(rows[2], link(901033))
assert(inferior:find("+5.0 pts", 1, true) and inferior:find("Stronger option you own · Fixture gear 901032 · In bags", 1, true))
local near = showTip(rows[3], link(901034))
assert(near:find("Sidegrade to Fixture gear 901032 · In bags", 1, true))

panel:Hide(); highlights:ScheduleRefresh(); H.settle(); panel:Show()
assert(mark(rows[1], 901032).result == best.result, "An unchanged native bag reopens with the same recommendation")
H.settle()
active, group = "Protection", 2
addon:RefreshTooltipPlayerContext(); highlights:InvalidateStorage(); H.settle()
assert(mark(rows[1], 901032).spec.role == "active" and not mark(rows[2], 901033))

level = 60
addon.GetRecommendationHistory = function(_, id, class, spec, phase)
    return {selected = {phase = phase, status = "rated", rank_group = id == 901033 and spec == "Protection" and "bis" or "option"}}
end
addon:RefreshTooltipPlayerContext(); highlights:InvalidateStorage(); H.settle()
assert(mark(rows[1], 901032) and not mark(rows[2], 901033), "Guide approval alone does not earn an owned-set badge")
''')

    def test_level_49_revenant_chest_uses_verified_passives_and_storage_comparison(self):
        self.run_lua(r'''
BigBiSListData.stat_rank = publishedRanks
level = 49
addon.DetectPlayerSpec = function()
    return "Retribution", {{displayName = "Retribution", icon = 10101}, {displayName = "Protection", icon = 20202}}
end
addon:GetCharacterDB().tooltipTalentSpecs[2] = "Protection"
local champion = "|cnIQ2:|Hitem:10128::::::::49:1486::1:1:12753:1:28:5238:::::|h[Revenant Chestplate of the Champion]|h|r"
local worn = "|cnIQ2:|Hitem:9966::::::::49:1486::1:1:12723:1:28:5255:::::|h[Embossed Plate Armor of the Gorilla]|h|r"
local golem = "|cnIQ3:|Hitem:274428::::::::49:1486::1::1:28:5253:::::|h[Dark Golem Breastplate]|h|r"
local mail = "|cnIQ3:|Hitem:9469::::::::49:1486::1::1:28:5255:::::|h[Gahz'rilla Scale Armor]|h|r"
local defenseOnly = "|Hitem:901061|h[Defense chest]|h"
local offense = "|Hitem:901062|h[Offense chest]|h"
local bankUpgrade = "|Hitem:901063|h[Bank upgrade]|h"
local defenseLine = "Equip: Increased Defense +5."
local fixtures = {
    [10128] = {link = champion, level = 49, armor = 515,
        stats = {ITEM_MOD_STAMINA_SHORT = 17, ITEM_MOD_STRENGTH_SHORT = 9}, lines = {defenseLine}},
    [9966] = {link = worn, level = 40, armor = 437,
        stats = {ITEM_MOD_INTELLECT_SHORT = 13, ITEM_MOD_STRENGTH_SHORT = 13}},
    [274428] = {link = golem, level = 39, armor = 471,
        stats = {ITEM_MOD_STAMINA_SHORT = 10, ITEM_MOD_STRENGTH_SHORT = 5},
        lines = {"Equip: Increases your chance to parry an attack by 1%."}},
    [9469] = {link = mail, level = 43, armor = 290, subclass = 3,
        stats = {ITEM_MOD_STAMINA_SHORT = 10, ITEM_MOD_SPIRIT_SHORT = 16},
        lines = {"Equip: Increases healing done by up to 33 and damage done by up to 11 for all magical spells and effects."}},
    [901061] = {link = defenseOnly, level = 40, armor = 437,
        stats = {ITEM_MOD_INTELLECT_SHORT = 13, ITEM_MOD_STRENGTH_SHORT = 13}, lines = {defenseLine}},
    [901062] = {link = offense, level = 40, armor = 400, stats = {ITEM_MOD_SPELL_POWER_SHORT = 11},
        lines = {"Equip: +20 Attack Power.", "Equip: Increases damage done by magical spells and effects by up to 11.",
            "Equip: Increases attack power by 30 when fighting Undead."}},
    [901063] = {link = bankUpgrade, level = 40, armor = 520, stats = {ITEM_MOD_STAMINA_SHORT = 30}},
}
GetItemInfo = function(value)
    local item = fixtures[idOf(value)]
    if item then return item.link:match("|h%[(.-)%]|h"), item.link, 2, 54, item.level end
end
GetItemInfoInstant = function(value)
    local id = idOf(value)
    local item = fixtures[id]
    if item then return id, "Armor", "Armor", "INVTYPE_CHEST", 1, 4, item.subclass or 4 end
end
C_Item.GetItemInfo, C_Item.GetItemInfoInstant = GetItemInfo, GetItemInfoInstant
C_Item.GetItemStats = function(value)
    local item = fixtures[idOf(value)]
    return item and item.stats
end
C_TooltipInfo = {GetHyperlink = function(value)
    local item = fixtures[idOf(value)]
    if not item then return end
    local lines = {{leftText = item.armor .. " Armor"}}
    for _, text in ipairs(item.lines or {}) do lines[#lines + 1] = {leftText = text} end
    return {lines = lines}
end}
H.equipped[1], H.equipped[5] = nil, 9966
GetInventoryItemLink = function(_, slot) if slot == 5 then return worn end end
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {mail}, {"20:1"}
local contents = {champion, golem}
local panel, rows = bagView(contents)
highlights:Initialize(); H.settle()
local function checkChampion()
    local winner = assert(mark(rows[1], champion))
    assert(winner.spec.name == "Protection" and not winner.result.conditional)
    assert(math.abs(winner.result.delta - 36.14) < 0.001, "Include the five Defense exactly once")
    assert(not mark(rows[2], golem), "Only the stronger Protection chest gets the spec icon")
end
checkChampion()
assert(rating:GetExactBaseFacts(10128, champion).stats.defense == 5)
local plain = champion:match("item:[%d:]+"):gsub(":49:1486:", ":50:1486:")
local tip = showTip(rows[1], plain)
assert(tip:find("+36.1 pts", 1, true) and tip:find("vs Embossed Plate Armor of the Gorilla", 1, true))
assert(tip:find("Recommended for Outdoor", 1, true) and not tip:find("Conditional", 1, true))
tip = showTip(rows[2], (golem:match("item:[%d:]+"):gsub("::1::1:", "::1:0:1:")))
assert(tip:find("Stronger option you own · Revenant Chestplate of the Champion · In bags", 1, true))
assert(not highlights:GetTooltipOffer(rows[1], 10128, plain:gsub("12753", "12723")))
assert(not highlights:GetTooltipOffer(rows[1], 10128, plain:gsub("item:10128::", "item:10128:1900:")))
assert(not highlights:GetTooltipOffer(rows[1], 10128, plain:gsub("item:10128:::", "item:10128::4001:")))
assert(not rating:SameExactItemLink(10128, "item:10128::::::-44", "item:10128::::::-45"))

local function refresh(id)
    if id then rating:InvalidateItem(id) end
    ui:Invalidate("ownership", "chest-replay"); panel:UpdateItems(); H.settle()
end
fixtures[10128].stats.ITEM_MOD_DEFENSE_SKILL_RATING_SHORT = 5
refresh(10128); checkChampion()
assert(rating:GetExactBaseFacts(10128, champion).stats.defense == 5)
local normalized = rating:GetExactBaseFacts(901062, offense)
assert(normalized.stats.attack_power == 20 and normalized.stats.spell_damage == 11 and not normalized.stats.spell_power)
assert(#normalized.effects == 1 and normalized.effects[1]:find("when fighting Undead", 1, true))

bank.links[1] = bankUpgrade
refresh()
assert(not mark(rows[1], champion))
tip = showTip(rows[1], plain)
assert(tip:find("Stronger option you own · Bank upgrade · In bank (last visit)", 1, true))
bank.links[1] = mail
fixtures[10128].lines[2] = "Use: Unleash a burst of Holy damage. (5 Min Cooldown)"
refresh(10128)
assert(not mark(rows[1], champion))
assert(showTip(rows[1], plain):find("Conditional", 1, true))

contents[1], contents[2] = defenseOnly, nil
refresh()
local winner = assert(mark(rows[1], defenseOnly))
assert(winner.spec.name == "Protection" and math.abs(winner.result.delta - 6.25) < 0.001)
local offer = assert(highlights:GetTooltipOffer(rows[1], 901061, defenseOnly))
assert(offer.assessments[1].spec.name == "Retribution" and not offer.assessments[1].storage.qualifies)
''')

    def test_storage_winners_obey_pair_legality_and_copy_ties(self):
        self.run_lua(r'''
for _, slot in ipairs({"Ring", "Trinket", "Main Hand", "Off Hand", "Two Hand"}) do slots[#slots + 1] = slot end
local data = BigBiSListData.stat_rank
for _, field in ipairs({"max_equipped", "weapon_subtype", "armor_type"}) do
    data.item_fields[#data.item_fields + 1] = field
end
data.equipment.Paladin.weapon_types = {"Sword"}
data.equipment.Paladin.two_hand_weapon_types = {"Sword"}
data.equipment.Paladin.armor_tiers = {{level = 1, types = {"Shield"}}}
item(901041, "Ring", 3, 0)
item(901042, "Ring", 4, 0)
item(901043, "Ring", 10, 0)
item(901044, "Ring", 15, 0)
items["901044"][6] = 1
item(901047, "Ring", 5, 0)
item(901045, "Trinket", 10, 0)
item(901046, "Trinket", 7, 0)
item(901051, "Two Hand", 8, 0)
item(901052, "One Hand", 12, 0)
item(901053, "Off Hand", 10, 0)
items["901051"][7], items["901052"][7], items["901053"][8] = "Sword", "Sword", "Shield"
H.equipped[11], H.equipped[12], H.equipped[16] = 901041, 901042, 901051
local links = {link(901043), link(901043), link(901043), link(901045), link(901046), link(901052), link(901053), link(901001)}
local panel, rows = bagView(links)
highlights:Initialize(); H.settle()
assert(mark(rows[1], 901043) and mark(rows[2], 901043) and not mark(rows[3], 901043))
assert(mark(rows[4], 901045) and mark(rows[5], 901046), "A legal pair may fill both trinket slots")
assert(not mark(rows[8], 901001), "An equipped copy wins a tie")
assert(mark(rows[6], 901052).result.delta == 14 and mark(rows[7], 901053).result.delta == 14)
assert(showTip(rows[7], link(901053)):find("Recommended for Outdoor · With Fixture gear 901052", 1, true))

links[1], links[2] = link(901044), link(901044)
ui:Invalidate("ownership", "unique-ring"); panel:UpdateItems(); H.settle()
assert(mark(rows[1], 901044) and not mark(rows[2], 901044) and mark(rows[3], 901043))
links[2], links[3] = link(901047), link(901047)
ui:Invalidate("ownership", "independent-cutoff"); panel:UpdateItems(); H.settle()
assert(mark(rows[1], 901044) and not mark(rows[2], 901047) and not mark(rows[3], 901047))
''')

    def test_storage_scenario_marks_only_meaningfully_distinct_winners(self):
        self.run_lua(r'''
addon:GetCharacterDB().tooltipTalentSpecs[2] = nil
local original = addon.ForeverScoring.GetPreset
addon.ForeverScoring.GetPreset = function(self, class, spec, mode, atLevel, scenario)
    if spec == "Protection" and mode == "leveling" and scenario == "dungeon" then
        return {weights = {{40, 59, {intellect = 1}}}}
    end
    return original(self, class, spec, mode, atLevel, scenario)
end
item(901031, "Head", 14, 8)
item(901032, "Head", 10, 14)
item(901033, "Head", 10, 9)
item(901034, "Head", 16, 16)
local links = {link(901031), link(901032)}
local panel, rows = bagView(links)
highlights:Initialize(); H.settle()
local main, alternate = assert(mark(rows[1], 901031)), assert(mark(rows[2], 901032))
assert(not main.alternate and main.scenario == "outdoor" and alternate.alternate and alternate.scenario == "dungeon")
local function badge(row)
    for _, child in ipairs(row.children) do if child.alternate then return child end end
end
assert(not badge(rows[1]).alternate:IsShown() and badge(rows[2]).alternate:IsShown())
H.expectBounded(badge(rows[2]).alternate, badge(rows[2]), "Alternate-use dot")
assert(showTip(rows[2], link(901032)):find("Recommended for Dungeon", 1, true))

links[2] = link(901033)
ui:Invalidate("ownership", "close-context-winner"); panel:UpdateItems(); H.settle()
assert(mark(rows[1], 901031) and not mark(rows[2], 901033))
links[2] = link(901034)
ui:Invalidate("ownership", "same-winner"); panel:UpdateItems(); H.settle()
assert(not mark(rows[1], 901031) and mark(rows[2], 901034) and not badge(rows[2]).alternate:IsShown())
local tip = showTip(rows[2], link(901034))
assert(tip:find("Recommended for Outdoor", 1, true) and tip:find("Recommended for Dungeon", 1, true))
''')

    def test_baganator_corner_uses_live_slots_and_clears_stale_or_disabled_items(self):
        self.run_lua(r'''
local contents = {[0] = {link(901002)}, [20] = {link(901004)}}
Enum.BankType = {Character = 1}
C_Bank = {FetchPurchasedBankTabIDs = function() return {20} end}
C_Container = {
    GetContainerNumSlots = function(bag) return contents[bag] and #contents[bag] or 0 end,
    GetContainerItemID = function(bag, slot) return contents[bag] and idOf(contents[bag][slot]) end,
    GetContainerItemLink = function(bag, slot) return contents[bag] and contents[bag][slot] end,
}
local plugin, active, refreshes = nil, true, 0
local button, widget, alternative, details
local drawing = false
local function freshDetails()
    local location = details.itemLocation
    return {itemLink = details.itemLink, itemLocation = location and {bagID = location.bagID, slotIndex = location.slotIndex}}
end
local function redraw(nextDetails)
    details = nextDetails
    button.BGR = details
    drawing = true
    widget:Hide()
    alternative:Hide()
    local visible = active and plugin.update(widget, details)
    if visible then widget:Show() else alternative:Show() end
    drawing = false
    assert(not (widget:IsVisible() and alternative:IsVisible()), "One corner has one visible widget")
    return visible
end
local savedLeft = {"big_bis_list", "junk", "item_level"}
local savedRight = {"forever_leveling_bis"}
BAGANATOR_CONFIG = {Profiles = {
    DEFAULT = {icon_top_left_corner_array = savedLeft, icon_top_right_corner_array = savedRight},
    Custom = {icon_top_left_corner_array = {"item_level"}, icon_bottom_left_corner_array = {"big_bis_list"}},
    Disabled = {icon_top_left_corner_array = {"item_level"}, icon_top_right_corner_array = {"forever_leveling_bis"}},
}}
Baganator = {Constants = {RefreshReason = {ItemWidgets = "widgets"}}, API = {
    RegisterCornerWidget = function(label, id, update, init, position)
        assert(label == "Big BiS List" and id == "big_bis_list" and position.corner == "top_right" and position.priority == 1)
        plugin = {update = update, init = init}
    end,
    IsCornerWidgetActive = function() return active end,
    RequestItemButtonsRefresh = function(reason)
        assert(reason[1] == "widgets")
        refreshes = refreshes + 1
        if widget then C_Timer.After(0, function() redraw(freshDetails()) end) end
    end,
}}
highlights:Initialize(); H.settle()
assert(plugin)
assert(table.concat(savedLeft, ",") == "junk,item_level")
assert(table.concat(savedRight, ",") == "big_bis_list,forever_leveling_bis")
assert(BAGANATOR_CONFIG.Profiles.Custom.icon_bottom_left_corner_array[1] == "big_bis_list")
assert(BAGANATOR_CONFIG.Profiles.Disabled.icon_top_right_corner_array[1] == "forever_leveling_bis")
assert(addon:GetAccountDB().profile.gearHighlights.baganatorCornerVersion == 1)
button = row(UIParent, 1)
button:SetSize(36, 36)
widget = plugin.init(button)
widget:SetPoint("TOPRIGHT", button, "TOPRIGHT", -2, -2)
alternative = CreateFrame("Frame", nil, button)
alternative:SetSize(15, 15)
alternative:SetPoint("TOPRIGHT", button, "TOPRIGHT", -2, -2)
local show, hide = widget.Show, widget.Hide
widget.Show = function(self) assert(drawing, "Baganator owns widget visibility"); show(self) end
widget.Hide = function(self) assert(drawing, "Baganator owns widget visibility"); hide(self) end
details = {itemLink = link(901002), itemLocation = {bagID = 0, slotIndex = 1}}
assert(not redraw(details)); H.settle()
assert(widget:IsShown() and not alternative:IsShown())
assert(not widget.animation and not widget.glow and widget.icon:IsShown() and not widget.bis:IsShown())
H.expectBounded(widget, button, "Baganator badge")
H.expectBounded(widget.icon, widget, "Baganator talent icon")
for _, edge in ipairs(widget.border) do H.expectBounded(edge, widget, "Baganator badge border") end
assert(mark(button, 901002).result.delta == 4 and mark(button, 901002).entry.widget == widget)
local initialRefreshes = refreshes
local cached = mark(button, 901002).result
local textureWrites, setTexture = 0, widget.icon.SetTexture
widget.icon.SetTexture = function(self, texture)
    textureWrites = textureWrites + 1
    setTexture(self, texture)
end
for index = 1, 8 do
    assert(redraw(freshDetails()))
    H.settle()
    assert(not highlights.queued and mark(button, 901002).result == cached)
end
local formatted = freshDetails()
formatted.itemLink = "|cnIQ3:|H" .. formatted.itemLink .. "|h[Fixture gear]|h|r"
assert(redraw(formatted), "The live slot and the corner widget can use different link wrappers")
assert(mark(button, formatted.itemLink).result == cached)
assert(not highlights:GetTooltipOffer(button, 901002, "item:901002:1900"))
assert(refreshes == initialRefreshes, "An unchanged Baganator row reuses its result")
button:Hide(); H.settle(); button:Show()
assert(redraw(freshDetails()), "A reopened bag gets the badge on its first draw")
H.settle()
assert(refreshes == initialRefreshes and mark(button, 901002).result == cached)
assert(textureWrites == 0, "An unchanged reopen reuses the rendered badge")

formatted.itemLink = "item:901002:1900"
assert(not redraw(formatted) and not mark(button, 901002), "A stale modifier must not bind a widget to the wrong copy")
formatted.itemLink = link(901002)
assert(redraw(formatted) and mark(button, 901002).result == cached)
local getGUID = ui.GetStorageItemGUID
ui.GetStorageItemGUID = function() return "current-physical-copy" end
formatted.guid = "previous-physical-copy"
assert(not redraw(formatted) and not mark(button, 901002))
formatted.guid = "current-physical-copy"
assert(redraw(formatted) and mark(button, 901002).result == cached)
ui.GetStorageItemGUID = getGUID
formatted.guid = nil

highlights.tooltipDirty = true
highlights:ScheduleRefresh(); H.settle()
assert(refreshes == initialRefreshes, "Tooltip-only updates do not redraw Baganator")

contents[0][1], details.itemLink = link(901006), link(901006)
ui:Invalidate("ownership", "baganator-recycle")
redraw(details); H.settle()
assert(not mark(button, 901002) and not mark(button, 901006) and not widget:IsShown())
details = {itemLink = link(901004), itemLocation = {bagID = 20, slotIndex = 1}}
button.BGR, ui.personalBankOpen = details, true
assert(ui:ScanBankItems())
ui:Invalidate("ownership", "bank-scan")
redraw(details); H.settle()
assert(mark(button, 901004).result.delta == 6)
details = {itemLink = link(901004)}
button.BGR = details
redraw(details); H.settle()
assert(not mark(button, 901004), "Cached rows without a current character location have no live equip mark")
initialRefreshes = refreshes
for index = 1, 3 do redraw(freshDetails()); H.settle() end
assert(refreshes == initialRefreshes and not highlights.queued, "Cached previews stay settled")

details = {itemLink = link(901002), itemLocation = {bagID = 0, slotIndex = 1}}
contents[0][1], button.BGR = link(901002), details
contents[20] = {}
assert(ui:ScanBankItems())
ui:Invalidate("ownership", "restore-baganator-item")
redraw(details); H.settle()
assert(mark(button, 901002))
level = 60
addon:RefreshTooltipPlayerContext()
addon.GetRecommendationHistory = function(_, id, class, spec, phase)
    return {selected = {phase = phase, status = "rated", rank_group = id == 901002 and spec == "Protection" and "bis" or "option"}}
end
highlights:InvalidateStorage(); H.settle()
assert(widget.bis:IsShown() and not widget.icon:IsShown())
local gold = addon.Widgets.Theme.bisGold
for _, edge in ipairs(widget.border) do
    for component = 1, 3 do assert(edge.colorTexture[component] == gold[component]) end
end
H.expectBounded(widget.bis, widget, "BiS badge text")
active = false
highlights:ScheduleRefresh(); H.settle()
assert(not mark(button, 901002) and not widget:IsShown())
active = true
redraw(details); H.settle()
assert(mark(button, 901002))
button:Hide()
assert(not mark(button, 901002) and not widget:IsVisible())
''')

    def test_reward_groups_approval_selection_and_sell_value(self):
        self.run_lua(r'''
local rewards = CreateFrame("Frame", nil, UIParent)
local first, second, fixed = row(rewards, 1), row(rewards, 2), row(rewards, 1)
first.type, second.type, fixed.type = "choice", "choice", "reward"
first.objectType, second.objectType, fixed.objectType = "item", "item", "item"
first.questID, second.questID, fixed.questID = 42, 42, 42
rewards.RewardButtons = {first, second, fixed}
QuestInfoFrame = {rewardsFrame = rewards}
local offers = {choice = {901003, 901004}, reward = {901005}}
local counts = {1, 1}
local function getReward(kind, index) return offers[kind][index] end
GetQuestItemLink = function(kind, index) return link(getReward(kind, index)) end
GetQuestItemInfo = function(kind, index)
    return "Item", 0, counts[index], 2, true, getReward(kind, index)
end
GetQuestLogItemLink = GetQuestItemLink
GetQuestLogChoiceInfo = function(index) return GetQuestItemInfo("choice", index) end
GetQuestLogRewardInfo = function(index) return GetQuestItemInfo("reward", index) end
QuestInfo_Display = function() end
QuestInfoItem_OnClick = function(selected)
    for _, reward in ipairs(rewards.RewardButtons) do reward.selected = reward == selected end
end
QuestInfoItem_IsSelected = function(reward) return reward.selected end
highlights:Initialize()
H.settle()
assert(not ui.frame)
assert(not mark(first, 901003))
assert(mark(second, 901004).outline and mark(second, 901004).result.delta == 2)
assert(mark(fixed, 901005).spec.role == "dual" and mark(fixed, 901005).ownedBaseline)
assert(showTip(second, link(901004)):find("Best choice for Protection", 1, true))
QuestInfoItem_OnClick(first); H.settle()
assert(mark(second, 901004).bestChoice and not mark(second, 901004).outline and first.selected)
first.selected = nil
QuestInfoFrame.questLog = true
offers.choice = {901005, 901006}
offers.reward = {901004}
QuestInfo_Display(); H.settle()
assert(mark(first, 901005).outline and mark(first, 901005).spec.name == "Holy")
assert(not mark(second, 901006) and mark(fixed, 901004).spec.name == "Protection")

offers.choice, counts = {901010, 901011}, {4, 1}
QuestInfo_Display(); H.settle()
assert(mark(fixed, 901004).spec.role == "active")
assert(not mark(first, 901010) and not mark(second, 901011))
assert(not showTip(first, link(901010)):find("Highest sell value", 1, true))

offers.reward = {901005}
QuestInfo_Display(); H.settle()
assert(mark(fixed, 901005).spec.role == "dual")
assert(not mark(first, 901010) and not mark(second, 901011))

offers.reward = {901006}
cold[901010] = true
QuestInfo_Display(); H.settle()
assert(not mark(first, 901010) and not mark(second, 901011) and coldCallbacks[901010])
cold[901010] = nil
coldCallbacks[901010](); H.settle()
assert(mark(first, 901010).sellValue == 60 and not mark(second, 901011))
local overlay = first:GetChildren()
assert(overlay.corner.symbol:IsVisible() and overlay.corner.symbol:GetTexture() == "Interface\\MoneyFrame\\UI-GoldIcon")
assert(showTip(first, link(901010)):find("Highest sell value", 1, true))

offers.choice[2] = 901004
QuestInfo_Display(); H.settle()
assert(mark(second, 901004).bestChoice and not mark(first, 901010) and not overlay:IsShown())

level = 60
addon.GetRecommendationHistory = function(_, id, class, spec, phase)
    if id == 901006 and spec == "Protection" then
        return {selected = {phase = phase, status = "rated", rank_group = "bis"}}
    end
    return {}
end
addon:RefreshTooltipPlayerContext()
counts, offers.choice = {1, 1}, {901006, 901004}
local getLink = GetQuestLogItemLink
local bonus = "item:901006:0:0:0:0:0:0:0:60:0:0:0:1:700"
QuestInfo_Display(); H.settle()
assert(mark(first, 901006).result.bis and not mark(first, 901006).bestChoice)
assert(mark(second, 901004).bestChoice)
assert(mark(first, 901006).gain < 0 and mark(second, 901004).gain > 0)
GetQuestLogItemLink = function(kind, index)
    if kind == "choice" and index == 1 then return bonus end
    return getLink(kind, index)
end
QuestInfo_Display(); H.settle()
assert(not mark(first, 901006) and not mark(first, bonus).result.bis)
assert(showTip(first, bonus):find("Protection", 1, true))
rewards:Hide(); H.settle()
assert(not mark(first, bonus))
''')

    def test_quest_choices_use_guaranteed_gear_and_keep_each_context_visible(self):
        self.run_lua(r'''
local rewards = CreateFrame("Frame", nil, UIParent)
local first, second, fixed = row(rewards, 1), row(rewards, 2), row(rewards, 1)
first.type, second.type, fixed.type = "choice", "choice", "reward"
for _, reward in ipairs({first, second, fixed}) do reward.objectType = "item"; reward.questID = 42 end
rewards.RewardButtons = {first, second, fixed}
QuestInfoFrame = {rewardsFrame = rewards}
local choices, guaranteed = {901004, 901005}, 901003
local original = addon.ForeverScoring.GetPreset
addon.ForeverScoring.GetPreset = function(self, class, spec, mode, atLevel, scenario)
    if spec == "Protection" and mode == "leveling" and scenario == "dungeon" then
        return { weights = {{40, 59, {intellect = 1}}} }
    end
    return original(self, class, spec, mode, atLevel, scenario)
end
local function rewardId(kind, index)
    if kind == "choice" then return choices[index] end
    return guaranteed
end
GetQuestItemLink = function(kind, index) return link(rewardId(kind, index)) end
GetQuestItemInfo = function(kind, index) return "Item", 0, 1, 2, true, rewardId(kind, index) end
QuestInfo_Display = function() end
highlights:Initialize(); H.settle()
assert(mark(first, 901004).scenario == "outdoor" and mark(first, 901004).result.delta == 2)
assert(mark(second, 901005).scenario == "dungeon" and mark(second, 901005).result.delta == 20)
local tip = showTip(second, link(901005))
assert(tip:find("Best choice for Protection in Dungeon", 1, true))
assert(tip:find("Best choice for Holy in Outdoor", 1, true))

guaranteed = 901004
QuestInfo_Display(); H.settle()
assert(not mark(first, 901004) and mark(second, 901005).bestChoice)
assert(showTip(first, link(901004)):find("with guaranteed rewards", 1, true))

choices, guaranteed = {901004, 901004}, 901003
QuestInfo_Display(); H.settle()
assert(mark(first, 901004) and not mark(first, 901004).bestChoice)
assert(mark(second, 901004) and not mark(second, 901004).bestChoice)
assert(showTip(first, link(901004)):find("Tied for best choice in Outdoor", 1, true))

choices = {901004, nil}
QuestInfo_Display(); H.settle()
assert(mark(first, 901004) and not mark(first, 901004).bestChoice)
assert(not showTip(first, link(901004)):find("Best choice", 1, true))

choices = {901004, 901005}
addon:SetGearScenario("Paladin", "Protection", "LEVELING", "dungeon")
assert(rating:GetScenario("Paladin", "Protection", "LEVELING", level) == "dungeon")
assert(rating:GetScenario("Paladin", "Protection", "PR", 60) == "pre_raid")
assert(rating:GetScenario("Paladin", "Holy", "LEVELING", level) == "outdoor")
QuestInfo_Display(); H.settle()
local offer = highlights:GetTooltipOffer(second, 901005, link(901005))
assert(offer.assessments[1].scenario == "dungeon" and offer.assessments[1].bestChoice)
''')

    def test_direct_loot_and_active_rolls_recycle_exact_bindings(self):
        self.run_lua(r'''
LootFrame = CreateFrame("Frame", nil, UIParent)
local lootRow = row(LootFrame, 1)
lootRow.GetSlotIndex = lootRow.GetID
lootRow.Item = row(lootRow, 1)
LootFrame.ScrollBox = scrollBox({lootRow})
local slots = {901003, 901006}
GetLootSlotLink = function(index) return link(slots[index]) end
GetLootSlotType = function() return Enum.LootSlotType.Item end
GetLootSlotInfo = function() return 0, "Item", 1, nil, 2, false, false, nil, false end

GroupLootContainer, GamepadGroupLootRollFrame = CreateFrame("Frame", nil, UIParent), CreateFrame("Frame", nil, UIParent)
local desktop, controller = row(GroupLootContainer, 1), row(GamepadGroupLootRollFrame, 1)
desktop.IconFrame, controller.IconFrame = row(desktop, 1), row(controller, 1)
GamepadGroupLootRollFrame.ScrollBox = scrollBox({controller})
local offers, time = {[84] = 901003, [85] = 901004, [86] = 901007}, {[84] = 1000, [85] = 1000, [86] = 1000}
local active = {84, 85, 86}
GetActiveLootRollIDs = function() return active end
GetLootRollTimeLeft = function(id) return time[id] end
C_TooltipInfo = {GetLootRollItem = function(id) return {id = offers[id], hyperlink = link(offers[id])} end}
GroupLootFrame_SetupItemDisplay = function(card)
    card.canNeed, card.canGreed = false, true
    return true
end
GroupLootFrame_OnHide = function(card) card.canNeed, card.canGreed = nil, nil end
highlights:Initialize()
desktop.rollID, controller.rollID = 84, 85
assert(GroupLootFrame_SetupItemDisplay(desktop) and GroupLootFrame_SetupItemDisplay(controller))
H.settle()
assert(mark(lootRow.Item, 901003).result.delta == 3)
assert(not mark(desktop, 901003))
assert(mark(controller.IconFrame, 901004).result.delta == 2 and mark(controller, 901004).ownedBaseline)
assert(not controller.canNeed and controller.canGreed)
local tip = showTip(controller.IconFrame, link(901004))
assert(tip:find("+2.0 pts", 1, true) and tip:find("vs the best gear you own", 1, true))

lootRow.slotIndex = 2
LootFrame.ScrollBox.initRow(lootRow); H.settle()
assert(not mark(lootRow, 901003) and not mark(lootRow, 901006))
controller.rollID = 86
GroupLootFrame_SetupItemDisplay(controller)
GamepadGroupLootRollFrame.ScrollBox.initRow(controller); H.settle()
assert(not mark(controller, 901004) and mark(controller, 901007).result.status == "empty")
active, time[86] = {84}, 0
event("CANCEL_LOOT_ROLL", 86)
assert(not mark(controller, 901007))

lootRow.slotIndex = 1
LootFrame.ScrollBox.initRow(lootRow); H.settle()
assert(mark(lootRow, 901003))
event("LOOT_SLOT_CLEARED", 1)
assert(not mark(lootRow, 901003))
LootFrame:Hide(); H.settle()
assert(not mark(lootRow, 901003))
''')

    def test_purchases_trade_mail_crafting_and_late_bank_scores(self):
        self.run_lua(r'''
MerchantFrame = CreateFrame("Frame", nil, UIParent)
MerchantFrame.selectedTab, MERCHANT_ITEMS_PER_PAGE = 1, 1
local vendor = row(MerchantFrame, 1, "MerchantItem1ItemButton")
vendor.hasItem = true
local stock, marketLinks = 1, {link(901004), link(901003)}
C_MerchantFrame = {GetItemInfo = function() return {isPurchasable = true, numAvailable = stock, isUsable = true} end}
GetMerchantItemLink = function(index) return marketLinks[index] end
MerchantFrame_Update = function() end

AuctionHouseFrame = CreateFrame("Frame", nil, UIParent)
local page = CreateFrame("Frame", nil, AuctionHouseFrame)
AuctionHouseFrame.ItemBuyFrame = page
local auction = row(page, 1)
auction.rowData = {auctionID = 93, containsOwnerItem = false, itemLink = link(901004)}
page.ItemList = {ScrollBox = scrollBox({auction})}

TradeFrame = CreateFrame("Frame", nil, UIParent)
local incoming = row(TradeFrame, 1, "TradeRecipientItem1ItemButton")
local service = row(TradeFrame, 7, "TradeRecipientItem7ItemButton")
TRADE_ENCHANT_SLOT = 7
local tradeItem = 901004
GetTradeTargetItemLink = function(index)
    return index == 1 and link(tradeItem) or index == 7 and link(901004)
end
TradeFrame_UpdateTargetItem = function() end

OpenMailFrame = CreateFrame("Frame", nil, UIParent)
InboxFrame = {openMailID = 1}
local attachment = row(OpenMailFrame, 1)
OpenMailFrame.OpenMailAttachments = {attachment}
OpenMailFrame.Update = function() end
GetInboxItemLink = function(mail) return mail == 1 and link(901004) or nil end

ProfessionsFrame = CreateFrame("Frame", nil, UIParent)
local form = CreateFrame("Frame", nil, ProfessionsFrame)
ProfessionsFrame.CraftingPage = {SchematicForm = form}
form.OutputIcon = row(form, 1)
form.recipeSchematic = {}
form.transaction = {GetRecipeID = function() return 77 end, CreateCraftingReagentInfoTbl = function() return {} end}
form.UpdateOutputItem = function() end
local learned = true
C_TradeSkillUI = {GetRecipeInfo = function() return {learned = learned} end,
    GetRecipeOutputItemData = function() return {hyperlink = link(901004)} end}
highlights:Initialize()
H.settle()
for _, tile in ipairs({vendor, auction, incoming, attachment, form.OutputIcon}) do
    local recommendation = assert(mark(tile, 901004))
    assert(recommendation.ownedBaseline and recommendation.result.delta == 2)
end
assert(not mark(service, 901004))

addon:GetAccountDB().profile.gearHighlights.vendor = false
highlights:ScheduleRefresh(); H.settle()
assert(not mark(vendor, 901004) and mark(auction, 901004))
addon:GetAccountDB().profile.gearHighlights.vendor = true
vendor.slotIndex = 2
MerchantFrame_Update(); H.settle()
assert(not mark(vendor, 901004) and not mark(vendor, 901003))
local vendorTip = showTip(vendor, link(901003))
assert(vendorTip:find("-1.0 pts|r vs the best gear you own", 1, true) and not vendorTip:find("+3.0 pts", 1, true))
vendor.slotIndex, MerchantFrame.selectedTab = 1, 2
MerchantFrame_Update(); H.settle()
assert(not mark(vendor, 901004))
MerchantFrame.selectedTab = 1
MerchantFrame_Update(); H.settle()
assert(mark(vendor, 901004))

auction.rowData = {auctionID = 95, containsOwnerItem = false, itemKey = {itemID = 901004}}
page.ItemList.ScrollBox.initRow(auction); H.settle()
assert(not mark(auction, 901004))
tradeItem, InboxFrame.openMailID, learned = 901003, 2, false
TradeFrame_UpdateTargetItem(1); OpenMailFrame:Update(); form:UpdateOutputItem(); H.settle()
assert(not mark(incoming, 901004) and not mark(incoming, 901003))
assert(not mark(attachment, 901004) and not mark(form.OutputIcon, 901004))

local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links = true, {link(901020)}
cold[901020] = true
ui:Invalidate("ownership", "cold-bank-test"); H.settle()
assert(not mark(vendor, 901004) and coldCallbacks[901020])
local context = rating:GetContext("Paladin", "Protection", "LEVELING", 47, ui:GetOwnedSnapshot())
local pending = rating:CompareTooltipItem(context, rating:GetTooltipItem(901004, link(901004)), false, nil, true)
assert(pending.delta == nil and pending.status == "loading")
local neck = rating:CompareTooltipItem(context, rating:GetTooltipItem(901007, link(901007)), false, nil, true)
assert(neck.delta == 8)
cold[901020] = nil
coldCallbacks[901020](); H.settle()
assert(not mark(vendor, 901004))
context = rating:GetContext("Paladin", "Protection", "LEVELING", 47, ui:GetOwnedSnapshot())
local resolved = rating:CompareTooltipItem(context, rating:GetTooltipItem(901004, link(901004)), false, nil, true)
assert(resolved.delta == -3 and resolved.bank)
''')
