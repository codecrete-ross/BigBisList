"""Gearing workflows exercised through the addon frames."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


class GearWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, script):
        if not self.lua:
            self.skipTest("Lua 5.1 is unavailable")
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR,
            input=r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load("forever")
''' + script + r'''
assert(#H.errors == 0, table.concat(H.errors, "\n"))
''',
            capture_output=True, encoding="utf-8", timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_paper_doll_fits_and_tracks_physical_slots_and_item_links(self):
        self.run_lua(r'''
H.equipped[11], H.equipped[12], H.equipped[13], H.equipped[14] = 990001, 990001, 990003, 990003
H.equipped[16] = 990004
local longName = "Runed Band of the Long-Forgotten Highborne"
H.itemNames[990001] = longName
local readId, readLink = GetInventoryItemID, GetInventoryItemLink
GetInventoryItemID = function(unit, slot)
    if slot == 9 then error("unreadable equipment") end
    return readId(unit, slot)
end
GetInventoryItemLink = function(unit, slot)
    local link = readLink(unit, slot)
    if link then return link .. ":0:" .. slot end
end
GetItemInfoInstant = function(id)
    return id, "Armor", "Misc", id == 990004 and "INVTYPE_2HWEAPON" or "INVTYPE_FINGER"
end
SetPortraitTexture = function(texture, unit) texture:SetTexture("portrait:" .. unit) end
ui:Open(); H.settle(); ui:SetTab("Equipped"); H.settle()
local gear = ui.gearFrame
gear.slots.Finger1:Click(); H.settle()
local function verifySlots()
    assert(not ui.contentScroll:IsVisible() and ui.contentScroll:GetVerticalScrollRange() == 0)
    local shown = {}
    for key, button in pairs(gear.slots) do
        assert(button:IsVisible() and button:IsEnabled(), key .. " is unavailable")
        H.expectBounded(button, gear, key)
        H.expectBounded(button.iconButton, button, key .. " icon")
        H.expectBounded(button.itemName, button, key .. " name")
        assert(button.rating:IsVisible(), key .. " missing second line")
        H.expectBounded(button.rating, button, key .. " rating or state")
        assert(button.itemName:GetBottom() >= button.rating:GetTop(), key .. " overlapping text")
        if button.gearData.item_id then
            H.expectBounded(button.label, button, key .. " physical slot")
            assert(button.label:GetRight() < button.rating:GetLeft(), key .. " overlapping slot and rating")
        else
            assert(not button.rating.isTruncated, key .. " slot state clipped: " .. button.rating.fullText)
        end
        for _, other in ipairs(shown) do
            assert(button:GetLeft() >= other:GetRight() or button:GetRight() <= other:GetLeft()
                or button:GetTop() <= other:GetBottom() or button:GetBottom() >= other:GetTop(),
                key .. " overlaps " .. other.slotKey)
        end
        shown[#shown + 1] = button
    end
    assert(#shown == 17 and gear.slots.Head:GetLeft() < gear.slots.Hands:GetLeft())
    assert(gear.slots.MainHand:GetTop() < gear.slots.Trinket1:GetBottom())
    assert(gear.slots.MainHand:GetWidth() == gear.slots.OffHand:GetWidth()
        and gear.slots.MainHand:GetWidth() == gear.slots.Ranged:GetWidth())
    if gear.summary:IsVisible() then
        H.expectBounded(gear.summary, gear, "selected slot")
        H.expectBounded(gear.summary.itemName, gear.summary, "selected name")
        H.expectBounded(gear.summary.findButton, gear.summary, "Find upgrades")
        assert(gear.summary.itemName:GetBottom() > gear.summary.findButton:GetTop())
    end
end
for _, size in ipairs({{1020, 560}, {1160, 660}}) do
    ui.frame:SetSize(size[1], size[2]); H.settle()
    for _, density in ipairs({"compact", "comfortable"}) do
        BigBiSList:GetAccountDB().profile.window.density = density
        ui:SetInspectorVisible(false); H.settle(); verifySlots()
        ui:SetInspectorVisible(true); H.settle(); verifySlots()
        if size[1] == 1020 then
            assert(gear.slots.Head:GetWidth() == 206 and gear.summary:GetWidth() == 204)
            assert(gear.slots.Finger1.itemName.isTruncated and gear.summary.itemName:GetText() == longName)
        end
    end
end
ui:SetInspectorVisible(false); H.settle()
assert(gear.slots.Finger1.itemName:GetText() == longName, "resizing should recover a truncated name")
ui:SetInspectorVisible(true); H.settle()
assert(gear.preview.portrait:IsVisible(), "native portrait fallback missing")
assert(gear.slots.Head.gearData.overlayKind == "empty")
assert(gear.slots.Wrist.gearData.overlayKind == "unknown")
assert(gear.slots.Head.itemName:GetText() == "Head" and gear.slots.Head.rating:GetText() == "Empty")
assert(gear.slots.Wrist.rating:GetText() == "Item data unavailable")
assert(gear.slots.OffHand.rating:GetText() == "Two-handed weapon equipped")
assert(gear.slots.OffHand.gearData.disabledReason and gear.slots.OffHand.stateIcon:IsVisible())
assert(gear.slots.Trinket0.iconButton.itemLink ~= gear.slots.Trinket1.iconButton.itemLink)
assert(gear.slots.Trinket0.label:GetText() == "Trinket 1" and gear.slots.Trinket1.label:GetText() == "Trinket 2")
assert(gear.slots.Finger0.label:GetText() == "Finger 1" and gear.slots.Finger1.label:GetText() == "Finger 2")
assert(gear.slots.Finger0.itemName.fullText == longName and gear.slots.Finger1.itemName.fullText == longName)
gear.slots.OffHand:Click(); H.settle()
assert(not gear.summary.findButton:IsEnabled() and not gear.summary.detailsButton:IsShown())
gear.slots.Finger0:Click(); gear.slots.Finger1:Click(); H.settle()
assert(gear.slots.Finger1.selected and not gear.slots.Finger0.selected)
assert(ui.selectedItemData.slotKey == "Finger1")
gear.slots.Finger1:GetScript("OnEnter")(gear.slots.Finger1)
assert(GameTooltip.hyperlink == "item:990001:0:12")
H.modifiers.shift = true; gear.slots.Finger1:Click(); H.modifiers.shift = false
H.modifiers.control = true; gear.slots.Finger1:Click(); H.modifiers.control = false
assert(H.chatLink == "item:990001:0:12" and H.previewLink == H.chatLink)
assert(ui:OpenSlotComparison(ui.selectedItemData, "gear")); H.settle()
assert(ui.slotComparison.reference.slotKey == "Finger1")
local compareAction, addMenuButton = nil, UIDropDownMenu_AddButton
UIDropDownMenu_AddButton = function(info)
    if info.text == "Compare to this" then compareAction = info.func end
end
ui:ShowItemActionMenu(ui.slotComparison.pinned[1], "comparison", ui.comparisonPinnedRows[1])
UIDropDownMenu_AddButton = addMenuButton
assert(compareAction, "The other equipped ring should offer Compare to this")
compareAction(); H.settle()
assert(ui.slotComparison.reference.slotKey == "Finger0" and ui.slotComparison.reference.item_link == "item:990001:0:11")
ui:CloseSlotComparison(); H.settle()
assert(gear.slots.Finger1.selected and ui.selectedItemData.slotKey == "Finger1")

local pending = {}
Item = {CreateFromItemID = function(_, id)
    return {ContinueOnItemLoad = function(_, callback) pending[id] = callback end,
        GetItemName = function() return id == 990002 and "New ring" or "Stale ring" end,
        GetItemLink = function() return "item:" .. id end, GetItemIcon = function() return "new-ring" end}
end}
H.equipped[12], H.coldItems[990006] = 990006, true
ui:Invalidate("ownership", "equipment-swap"); ui:Refresh(); H.settle()
H.equipped[12], H.coldItems[990002] = 990002, true
ui:Invalidate("ownership", "equipment-swap"); ui:Refresh(); H.settle()
assert(ui.selectedItemId == 990002 and gear.slots.Finger1.selected)
pending[990006]()
assert(gear.summary.itemName:GetText() == "Item 990002" and gear.slots.Finger1.itemName:GetText() == "Item 990002")
pending[990002]()
assert(gear.summary.itemName:GetText() == "New ring")
assert(gear.slots.Finger1.itemName:GetText() == "New ring" and gear.slots.Finger0.itemName.fullText == longName)
assert(gear.slots.Finger1.iconButton.itemLink == "item:990002:0:12")

ui:SetInspectorVisible(false)
UIParent:SetSize(900, 500); ui.frame:SetSize(900, 500); H.settle(); verifySlots()
gear.summary.detailsButton:Click(); H.settle()
assert(ui.inspectorExclusive and ui.details:IsVisible())
ui.detailsBackButton:Click(); H.settle(); verifySlots()
assert(gear.slots.Finger1.selected and gear.summary.detailsButton:IsVisible())
''')

    def test_same_item_id_can_show_different_equipped_names(self):
        self.run_lua(r'''
H.equipped[11], H.equipped[12] = 990009, 990009
H.itemNames[990009] = "Runed Band"
local itemInfo = GetItemInfo
local raritySlots = {1, 2, 3, 5, 9, 10}
local colors = {
    [0] = {157/255, 157/255, 157/255}, {1, 1, 1}, {30/255, 1, 0},
    {0, 112/255, 221/255}, {163/255, 53/255, 238/255}, {1, 128/255, 0},
}
for index, slot in ipairs(raritySlots) do H.equipped[slot] = 990010 + index end
C_Item = {
    GetItemInfo = function(value)
        local id = tonumber(value) or tonumber(tostring(value):match("item:(%d+)"))
        if id and id >= 990011 and id <= 990016 then
            return "Quality " .. (id - 990011), "item:" .. id, id - 990011, 50, 1, "Armor", "Plate", 1, "INVTYPE_HEAD", "icon"
        end
        return itemInfo(value)
    end,
    GetItemQualityColor = function(quality) return unpack(colors[quality]) end,
}
GetItemQualityColor = nil
GetInventoryItemLink = function(_, slot)
    if slot == 11 then return "|cff1eff00|Hitem:990009:0:1|h[Runed Band of the Bear]|h|r" end
    if slot == 12 then return "|cff1eff00|Hitem:990009:0:2|h[Runed Band of the Eagle]|h|r" end
    return H.equipped[slot] and "item:" .. H.equipped[slot]
end
ui:Open(); H.settle(); ui:SetTab("Equipped"); H.settle()
local gear = ui.gearFrame
for index, key in ipairs({"Head", "Neck", "Shoulder", "Chest", "Wrist", "Hands"}) do
    local tile = gear.slots[key]
    for component = 1, 3 do
        assert(tile.itemName.textColor[component] == colors[index - 1][component], key .. " has the wrong item rarity")
    end
    tile:Click(); H.settle()
    for component = 1, 3 do
        assert(gear.summary.itemName.textColor[component] == colors[index - 1][component], key .. " summary has the wrong item rarity")
    end
end
assert(gear.slots.Finger0.itemName:GetText() == "Runed Band of the Bear")
assert(gear.slots.Finger1.itemName:GetText() == "Runed Band of the Eagle")
assert(ui.itemPresentationCache[990009].name == "Runed Band")
gear.slots.Finger1:Click(); H.settle()
assert(gear.summary.itemName:GetText() == "Runed Band of the Eagle")
''')

    def test_equipped_ratings_show_selected_guide_context(self):
        self.run_lua(r'''
UnitRace = function() return "Human", "Human" end
H.equipped[1], H.equipped[2], H.equipped[3], H.equipped[5] = 16731, 990012, 16733, 990013
local originalUses = BigBiSList.GetItemUses
function BigBiSList:GetItemUses(id, phase)
    local uses = originalUses(self, id, phase)
    if id ~= 16731 and id ~= 16733 then return uses end
    local fixture = {}
    for _, use in ipairs(uses) do
        if use.class == "Paladin" and use.spec == "Protection" and use.phase == "PR" then
            local copy = {}
            for key, value in pairs(use) do copy[key] = value end
            copy.rank_group, copy.rank_label = "bis", "BiS"
            if id == 16733 then
                copy.guide_evidence = {{grade = 1, guide_phase = "PR", original_rating = "Best in slot with the full set",
                    conditions = {"With set bonus"}}}
            end
            use = copy
        end
        fixture[#fixture + 1] = use
    end
    return fixture
end
local originalHistory = BigBiSList.GetRecommendationHistory
function BigBiSList:GetRecommendationHistory(id, class, spec, phase, slot)
    local history = originalHistory(self, id, class, spec, phase, slot)
    if id == 990012 then
        return setmetatable({selected = {matched = false}, latest_earlier = {
            matched = true, phase = "T4", label = "Alt", rank_group = "ranked", status = "conditional",
            rating_evidence = {{conditions = {"With a shield"}}}, use = {phase = "T4"}}},
            {__index = history})
    elseif id == 990013 then
        return setmetatable({selected = {matched = true, phase = phase, label = "Opt",
            rank_group = "ranked", status = "rated", use = {phase = phase}}}, {__index = history})
    end
    return history
end
local originalLeveling = BigBiSList.GetItemBestLevelingUseForSpec
function BigBiSList:GetItemBestLevelingUseForSpec(id, ...)
    if id == 16731 then
        return {leveling = true, level_min = 14, level_max = 27, level_label = "Recommended from 14-27",
            tooltip_level_label = "Leveling 14-27", display_rank_label = "Recommended from 14-27", display_rank_kind = "leveling"}
    end
    return originalLeveling(self, id, ...)
end
local realInfo, realInstant, realColor = GetItemInfo, GetItemInfoInstant, GetItemQualityColor
local function fixtureId(value)
    return tonumber(value) or tonumber(tostring(value):match("item:(%d+)"))
end
local realLink = GetInventoryItemLink
GetInventoryItemLink = function(unit, slot)
    if slot == 3 then return "item:16733:0:0:0:0:0:-3" end
    return realLink(unit, slot)
end
GetItemInfo = function(value)
    if fixtureId(value) == 16733 then return "Fixture shoulder", "item:16733", 3, 50, 40 end
    return realInfo(value)
end
GetItemInfoInstant = function(value)
    if fixtureId(value) == 16733 then return 16733, "Armor", "Plate", "INVTYPE_SHOULDER", "icon", 4, 4 end
    return realInstant(value)
end
GetItemStats = function(value)
    if fixtureId(value) == 16733 then return {ITEM_MOD_STAMINA_SHORT = 900} end
end
GetItemQualityColor = function(quality)
    if quality == 5 then return 1, 128/255, 0 end
    return realColor(quality)
end

ui:Open(); H.settle(); ui:SetClass("Paladin"); H.settle(); ui:SetSpec("Protection"); H.settle()
ui:SetTab("Equipped"); H.settle()
local slots = ui.gearFrame.slots
local head, shoulder = slots.Head, slots.Shoulder
local function goldVisible(row)
    return row.bisHighlight and row.bisHighlight[1]:IsVisible()
end
local function hover(row)
    row:GetScript("OnEnter")(row)
    return table.concat(GameTooltip.lines, "\n")
end
assert(head.gearData.history.selected.status == "rated" and head.gearData.history.selected.rank_group == "bis")
assert(head.guideBadge:GetText() == "BiS" and head.guideBadge:IsVisible() and goldVisible(head))
assert(head.rating:GetText():find("#", 1, true))
assert(slots.Neck.guideBadge:GetText() == "Earlier phase" and not goldVisible(slots.Neck))
local earlier = hover(slots.Neck)
assert(earlier:find(BigBiSList:GetPhaseDisplayName("T4") .. " · Alternative", 1, true))
assert(earlier:find("With a shield", 1, true))
assert(slots.Chest.guideBadge:GetText() == "Optional" and not goldVisible(slots.Chest))
assert(slots.Chest.rating:GetText() == "Stats unavailable")
assert(shoulder.gearData.history.selected.status == "conditional" and not goldVisible(shoulder))
assert(shoulder.rating:GetText():find("Top tier", 1, true))
assert(shoulder.rating.textColor[2] == 128/255)
shoulder:Click(); H.settle()
assert(shoulder.selected and not goldVisible(shoulder))
ui:SetInspectorVisible(true); H.settle()
assert(shoulder.guideBadge:GetText() == "Guide note" and not shoulder.guideBadge.isTruncated)
local conditional = hover(shoulder)
assert(conditional:find("Best in slot with the full set", 1, true) and conditional:find("With set bonus", 1, true))
ui:SetInspectorVisible(false); H.settle()
head:Click(); H.settle()
assert(head.selected and goldVisible(head))
assert(head.bisHighlight[2].colorTexture[2] == BigBiSList.Widgets.Theme.bisGold[2])
for _, region in ipairs(head.bisHighlight) do H.expectBounded(region, head, "BiS inset") end
ui.gearFrame.summary.statCompare:Click(); H.settle()
local pinned = ui.comparisonPinnedRows[1]
assert(pinned.selected and pinned.selectionAccent:IsShown() and goldVisible(pinned))
assert(pinned.metaText:GetText():find("BiS", 1, true))
H.equipped[1] = 16727
ui:Invalidate("ownership", "equipment-swap"); ui:Refresh(); H.settle()
assert(pinned.comparisonData.item_id == 16727 and not goldVisible(pinned))
ui:CloseSlotComparison(); H.settle()
assert(head.selected and not goldVisible(head))
H.equipped[1] = 16731
ui:Invalidate("ownership", "equipment-swap"); ui:Refresh(); H.settle()
assert(goldVisible(head))
ui:SetSpec("Holy"); H.settle()
assert(not goldVisible(head))
ui:SetSpec("Protection"); H.settle()
assert(goldVisible(head))
ui:SetContentMode("leveling"); H.settle()
ui:SetTab("Equipped"); H.settle()
assert(head.guideBadge:GetText() == "Recommended" and head.guideBadge:IsVisible() and not goldVisible(head))
assert(slots.Chest.rating:GetText() == "Stats unavailable")
head:Click()
local recommendation = "Gear Guide recommends this for Protection at levels 14–27"
assert(ui.gearFrame.summary.rating:GetText():find(recommendation, 1, true))
assert(hover(head):find(recommendation, 1, true))
''')

    def test_protection_loadout_shows_stats_and_opens_exact_slot_comparison(self):
        self.run_lua(r'''
local addon = BigBiSList
UnitClass = function() return "Paladin", "PALADIN" end
UnitClassBase = function() return "PALADIN" end
UnitRace = function() return "Human", "Human" end
UnitLevel = function() return 47 end

-- The game API fixtures reproduce the screenshot's slots and links. Stats on
-- the fixture-only items exercise rendering and identity, not real tooltips.
local gear = {
    [1] = {"Krol'dok Warplate Helmet", "HEAD", 4, 4},
    [2] = {"Triune Amulet", "NECK", 4, 0, 7722},
    [3] = {"Big Bad Pauldrons", "SHOULDER", 4, 4},
    [5] = {"Dark Golem Breastplate", "CHEST", 4, 4},
    [6] = {"Bloodforged Belt of Magic", "WAIST", 4, 4, nil, 602},
    [7] = {"Revenant Leggings of the Defender", "LEGS", 4, 4, nil, 603},
    [8] = {"Worgbinder's Treads", "FEET", 4, 4},
    [9] = {"Tyrant's Armguards", "WRIST", 4, 4},
    [10] = {"Cragfists of the Knight", "HAND", 4, 4, 9410, 601},
    [11] = {"Purified Ring", "FINGER", 4, 0},
    [12] = {"Blood Ritual Ring", "FINGER", 4, 0, 274642},
    [13] = {"The Desert Rose", "TRINKET", 4, 0, 274648},
    [14] = {"Carrot on a Stick", "TRINKET", 4, 0, 11122},
    [15] = {"Waterlogged Burial Shroud", "CLOAK", 4, 0},
    [16] = {"Sword of Serenity", "WEAPON", 2, 7},
    [17] = {"Wall of Water", "SHIELD", 4, 6},
}
local links, items = {}, {}
local function itemLink(id, name, bonus)
    local payload = "item:" .. id
    if bonus then payload = payload .. ":999:50:0:0:0:0:0:47:0:0:0:1:" .. bonus end
    return "|cff1eff00|H" .. payload .. "|h[" .. name .. "]|h|r"
end
for slot, item in pairs(gear) do
    local id = item[5] or 990200 + slot
    H.equipped[slot], items[id] = id, item
    links[slot] = itemLink(id, item[1], item[6])
end
local bagId, bagBonus = H.equipped[11], 777
local bagLink = itemLink(bagId, "Purified Ring of Stamina", bagBonus)
GetInventoryItemLink = function(_, slot) return links[slot] end
GetContainerNumSlots = function(bag) return bag == 0 and 1 or 0 end
GetContainerItemID = function() return bagId end
GetContainerItemLink = function() return bagLink end
local function fixtureId(value)
    return tonumber(value) or tonumber(tostring(value):match("item:(%d+)"))
end
local fallbackItemInfo, fallbackInstant = GetItemInfo, GetItemInfoInstant
GetItemInfo = function(value)
    local item = items[fixtureId(value)]
    if not item then return fallbackItemInfo(value) end
    local name = tostring(value):match("|h%[(.-)%]|h") or item[1]
    return name, value, 2, 47, 41, "Item", "Subtype", 1, "INVTYPE_" .. item[2], "icon"
end
GetItemInfoInstant = function(value)
    local id = fixtureId(value)
    local item = items[id]
    if not item then return fallbackInstant(value) end
    return id, "Item", "Subtype", "INVTYPE_" .. item[2], "icon", item[3], item[4]
end
local bonusReads = {}
C_Item = {GetItemStats = function(link)
    local item = items[fixtureId(link)]
    if not item then return end
    local payload = link:match("item:([%d:%-]+)")
    local bonus = tonumber(payload and payload:match(":(%d+)$") or "")
    if bonus then
        assert(link:find(":0:0:0:0:0:0:0:47:0:0:0:1:", 1, true), link)
        bonusReads[bonus] = true
    end
    local stats = {ITEM_MOD_STAMINA_SHORT = bonus and (bonus % 50 + 2) or 12}
    if item[3] == 2 then stats.ITEM_MOD_DAMAGE_PER_SECOND_SHORT = 31 end
    if item[3] == 4 and item[4] ~= 0 then stats.RESISTANCE0_NAME = 250 end
    return stats
end}

ui:Open(); H.settle()
ui:SetClass("Paladin"); H.settle()
ui:SetSpec("Protection"); H.settle()
ui:SetContentMode("leveling"); H.settle()
ui:SetTab("Equipped"); H.settle()
local slots = ui.gearFrame.slots
for _, key in ipairs({"Head", "Shoulder", "Back", "Chest", "Wrist", "Hands", "Waist", "Legs", "Feet",
        "Finger0", "Finger1", "MainHand", "OffHand"}) do
    local tile = slots[key]
    assert(tile.gearData.stat_rank.rank and tile.rating:GetText():match("#%d+%s*/%s*%d+"), key .. " " .. tile.rating:GetText())
end
assert(bonusReads[601] and bonusReads[602] and bonusReads[603] and bonusReads[bagBonus])
assert(slots.Neck.gearData.bestUse and slots.Neck.guideBadge:GetText() == "Recommended" and slots.Neck.guideBadge:IsVisible())
local recommendation = "Gear Guide recommends this for Protection at levels 40–59"
slots.Neck:Click(); H.settle()
assert(ui.gearFrame.summary.rating:GetText():find(recommendation, 1, true))
ui.gearFrame.summary.statCompare:Click(); H.settle()
local neck = ui.comparisonPinnedRows[1]
assert(ui.comparisonReference.dropdownText == "Compare with Triune Amulet (Neck)")
assert(neck.metaText:GetText() == "Neck · Recommended")
neck:GetScript("OnEnter")(neck)
assert(table.concat(GameTooltip.lines, "\n"):find(recommendation, 1, true))
ui:CloseSlotComparison(); H.settle()
assert(slots.Trinket0.rating:GetText() == "Effect only")
assert(slots.Trinket1.rating:GetText() == "Utility")
assert(not slots.Trinket1.rating.rankStripe)
slots.Trinket1:Click(); ui.gearFrame.summary.detailsButton:Click(); H.settle()
local shownEffect
for _, block in ipairs(ui.detailsWidgetPools.text or {}) do
    if block:IsVisible() and block.body:GetText():find("Increases mount speed", 1, true) then shownEffect = true end
end
assert(shownEffect)

local function verifyGear()
    assert(not ui.contentScroll:IsVisible())
    local count = 0
    for key, tile in pairs(slots) do
        count = count + 1
        assert(tile:IsVisible() and tile:IsEnabled(), key)
        H.expectBounded(tile, ui.gearFrame, key)
        H.expectBounded(tile.rating, tile, key .. " rank")
        local placement = tile.gearData.stat_rank
        if placement and placement.rank and placement.total > 1 then
            assert(not tile.rating.isTruncated, key .. " rank clipped: " .. tile.rating.fullText)
            local service = addon.ForeverGearRating
            assert(tile.rating:GetText() == service:Label(placement) or tile.rating:GetText() == service:Label(placement, "compact"),
                key .. " has the wrong rank: " .. tile.rating:GetText())
            if placement.tier then
                local color = {addon.Widgets:GetRankColor(placement.tier.quality)}
                for component = 1, 3 do assert(tile.rating.textColor[component] == color[component]) end
            end
            assert(not tile.rating.rankStripe)
        end
        if tile.guideBadge:IsVisible() then
            H.expectBounded(tile.guideBadge, tile, key .. " guide badge")
            assert(not tile.guideBadge.isTruncated, key .. " guide badge clipped")
            assert(tile.itemName:GetRight() < tile.guideBadge:GetLeft(), key .. " guide badge overlaps item name")
        end
    end
    assert(count == 17)
end
local function verifyComparison()
    local columns, state = ui.comparisonColumns, ui.slotComparison
    assert(columns.source.x + columns.source.width < columns.owned.x)
    for _, row in ipairs(ui.comparisonPinnedRows) do
        local placement = row.comparisonData.stat_rank
        assert(row.rankText:GetText() == addon.ForeverGearRating:Label(placement, columns.rank.stacked and "stacked" or nil))
        assert(not row.rankText.isTruncated and row.rankText:GetRight() < columns.evidence.x + row:GetLeft())
        assert(not row.rankText.rankStripe)
        H.expectBounded(row.rankText, row, "pinned rank")
    end
    assert(state.reference.slotKey == "Finger1" and state.reference.item_link == links[12])
    assert(ui.comparisonScope:GetText():find("Default spec weights", 1, true))
    assert(ui.comparisonPinnedRows[1].referenceButton.label:GetText() == "Compare to this")
end
for _, size in ipairs({{1020, 560}, {1160, 660}, {900, 500}}) do
    UIParent:SetSize(size[1], size[2])
    ui.frame:SetSize(size[1], size[2]); H.settle()
    for _, density in ipairs({"compact", "comfortable"}) do
        addon:GetAccountDB().profile.window.density = density
        ui:SetInspectorVisible(false); H.settle()
        slots.Finger1:Click(); H.settle()
        verifyGear()
        ui.gearFrame.summary.detailsButton:Click(); H.settle()
        if size[1] == 900 then
            assert(ui.inspectorExclusive and ui.details:IsVisible())
            ui.detailsBackButton:Click(); H.settle()
        end
        verifyGear()
        assert(ui.gearFrame.summary.rating:GetText():find("Protection · Level 47", 1, true))
        ui:SetInspectorVisible(false); H.settle()
        ui.gearFrame.summary.statCompare:Click(); H.settle()
        local state, shown = ui.slotComparison
        assert(state.statRank and state.sort == "stat_rank" and #state.rows > 5)
        assert(ui.comparisonColumns.rank.stacked == (size[1] == 900))
        verifyComparison()
        ui.comparisonPinnedRows[2]:GetScript("OnEnter")(ui.comparisonPinnedRows[2])
        assert(table.concat(GameTooltip.lines, "\n"):find("of the best known stat score", 1, true))
        for _, row in ipairs(state.rows) do
            if row.item_link == bagLink then shown = row; break end
        end
        assert(shown and shown.stat_delta and shown.acquisition_display.location_label == "Source unverified")
        local placement = shown.stat_rank
        ui:SetComparisonOwnership("owned"); H.settle()
        ui:SetComparisonSort("item"); H.settle()
        for _, entry in ipairs(state.entries) do
            assert(entry.kind ~= "row" or entry.data.owned)
            if entry.data == shown then assert(entry.data.stat_rank == placement) end
        end
        ui:ShowComparisonDetails(shown); H.settle()
        assert(ui.selectedItemData.item_link == bagLink and ui.details:IsVisible() and ui.inspectorExclusive)
        local explained
        for _, block in ipairs(ui.detailsWidgetPools.text or {}) do
            local text = block.body:GetText()
            if block:IsVisible() and text:find("of the best known stat score", 1, true)
                and text:find(addon.ForeverGearRating:Label(placement), 1, true)
                and text:find("Default spec weights", 1, true)
                and text:find("Compare with Blood Ritual Ring (Finger 2)", 1, true) then explained = true end
        end
        assert(explained, "Details should explain the same stat rank")
        ui:BackToSlotComparison(); H.settle()
        verifyComparison()
        ui.comparisonBackButton:Click(); H.settle()
        assert(not ui.slotComparison and slots.Finger1.selected)
        verifyGear()
    end
end

ui:SetContentMode("endgame"); H.settle(); ui:SetTab("Equipped"); H.settle()
slots.OffHand:Click(); ui.gearFrame.summary.statCompare:Click(); H.settle()
assert(ui.slotComparison.statRank and ui.slotComparison.level == 60 and ui.slotComparison.reference.slotKey == "OffHand")
assert(#ui.slotComparison.rows > 1)
for _, item in ipairs(ui.slotComparison.rows) do assert(item.stat_rank.item.armor_type == "Shield") end
''')

    def test_find_upgrades_and_slot_picker_use_existing_filters(self):
        self.run_lua(r'''
H.equipped[11], H.equipped[12], H.equipped[13], H.equipped[14] = 990001, 990001, 990003, 990003
local readLink = GetInventoryItemLink
GetInventoryItemLink = function(unit, slot)
    local link = readLink(unit, slot)
    return link and (link .. ":0:" .. slot)
end
ui:Open(); H.settle()
ui:GetFilters("Upgrades").search = "existing search"
ui:GetFilters("Upgrades").ownedState = "missing"
ui:SetTab("Equipped"); H.settle()
ui.gearFrame.slots.Finger1:Click()
ui.gearFrame.summary.findButton:Click(); H.settle()
assert(ui:GetSelection().tab == "Upgrades" and ui.upgradesView == "list")
local filters = ui:GetFilters()
assert(filters.slots.Rings and filters.search == "existing search" and filters.ownedState == "missing")
ui:SetTab("Equipped"); H.settle()
assert(ui.gearFrame.slots.Finger1.selected)
ui:SetContentMode("leveling"); H.settle()
ui:SetTab("Equipped"); H.settle()
ui:GetFilters("Gear Guide").boe = "boe"
ui:GetViewState("Gear Guide").groupBy = "activity"
ui.levelingActivity = "Previous destination"
ui.gearFrame.summary.findButton:Click(); H.settle()
assert(ui:GetSelection().tab == "Gear Guide" and ui:GetFilters().slots.Rings and ui:GetFilters().boe == "boe")
assert(ui:IsLevelingActivityView() and not ui.levelingActivity and ui.contentScroll:GetVerticalScroll() == 0)
assert(ui.slotContextFrame.items[1].data.slotKey == "Finger1" and not ui.slotContextFrame.items[2]:IsShown())
assert(ui.slotContextFrame.label:GetText() == "Finger 2" and ui.slotContextFrame.items[1].iconButton.itemLink == "item:990001:0:12")
assert(not ui.slotContextFrame.compareButton:IsShown())
H.equipped[12] = 990002
BigBiSList:InitUIEvents()
BigBiSList.uiEventFrame:GetScript("OnEvent")(BigBiSList.uiEventFrame, "PLAYER_EQUIPMENT_CHANGED"); H.settle()
assert(ui.slotContextFrame.items[1].iconButton.itemLink == "item:990002:0:12")
ui.slotPickerButton:Click(); H.settle()
local popup = ui.slotPickerOverlay.popup
assert(popup:IsVisible() and popup.slots.Finger0.selected and not popup.slots.Finger1)
H.expectBounded(popup, ui.body, "slot picker")
popup.allButton:Click(); H.settle()
assert(popup:IsVisible() and popup.allButton.selected and not popup.slots.Finger0.selected)
assert(not next(ui:GetFilters().slots) and not ui.levelingSlotReference)
popup.slots.Finger0:Click(); H.settle()
assert(ui.slotContextFrame.items[1].data.slotKey == "Finger0" and ui.slotContextFrame.items[2].data.slotKey == "Finger1")
popup.slots.Finger0:Click(); H.settle()
assert(popup:IsVisible() and popup.allButton.selected and not next(ui:GetFilters().slots))
popup.slots.Head:Click(); popup.slots.Feet:Click(); H.settle()
assert(not ui.slotContextFrame:IsVisible() and ui:GetFilters().slots.Head and ui:GetFilters().slots.Feet)
assert(popup:IsVisible() and popup.slots.Head.selected and popup.slots.Feet.selected)
popup.slots.OffHand:Click(); H.settle()
assert(popup:IsVisible() and popup.slots.OffHand.selected and popup.slots.Head.selected and popup.slots.Feet.selected)
assert(ui:GetFilters().slots["Off Hand"] and not ui:GetFocusedBrowseSlot())
assert(ui:GetFilters().boe == "boe")
popup.slots.Head:Click(); H.settle()
assert(popup:IsVisible() and not popup.slots.Head.selected and popup.slots.OffHand.selected and popup.slots.Feet.selected)
assert(not ui:GetFilters().slots.Head and ui:GetFilters().slots["Off Hand"] and ui:GetFilters().slots.Feet)
ui.slotPickerButton:Click(); H.settle()
assert(not popup:IsVisible() and not ui.slotPickerButton.selected and ui:GetFilters().slots.Feet)
ui.slotPickerButton:Click(); H.settle()
assert(popup:IsVisible() and popup.slots.OffHand.selected and popup.slots.Feet.selected)
popup.allButton:Click(); H.settle()
assert(popup:IsVisible() and popup.allButton.selected and not next(ui:GetFilters().slots))

ui:SetTab("Equipped"); H.settle()
ui.gearFrame.slots.Trinket1:Click(); ui.gearFrame.summary.findButton:Click(); H.settle()
assert(ui:GetFilters().slots.Trinkets and ui.slotContextFrame.items[1].data.slotKey == "Trinket1")
assert(ui.slotContextFrame.items[1].iconButton.itemLink == "item:990003:0:14")
ui:ClearFilters(); H.settle()
assert(not ui.levelingSlotReference and not ui.slotContextFrame:IsShown())
''')

    def test_late_stats_refresh_the_current_equipped_item_after_swapping(self):
        self.run_lua(r'''
local first, second = 990441, 990442
H.equipped[1] = first
H.coldItems[first], H.coldItems[second] = true, true
local callbacks, statsCalls = {}, {}
local function itemId(value)
    return tonumber(value) or tonumber(tostring(value):match("item:(%d+)"))
end
GetItemInfo = function(value)
    local id = itemId(value)
    if H.coldItems[id] then return end
    return "New headpiece " .. tostring(id), "item:" .. id, 2, 50, 42, "Armor", "Leather", 1, "INVTYPE_HEAD", "icon"
end
GetItemInfoInstant = function(value)
    return itemId(value), "Armor", "Leather", "INVTYPE_HEAD", "icon", 4, 2
end
C_Item = {
    GetItemInfo = GetItemInfo,
    GetItemQualityColor = function(quality)
        if quality == 2 then return 30/255, 1, 0 end
        return .64, .21, .93
    end,
    IsItemDataCachedByID = function(id) return not H.coldItems[id] end,
    GetItemStats = function(link)
        local id = itemId(link)
        statsCalls[id] = (statsCalls[id] or 0) + 1
        if not H.coldItems[id] then
            return {ITEM_MOD_STAMINA_SHORT = id == first and 50 or 10, RESISTANCE0_NAME = 140}
        end
    end,
}
GetItemQualityColor = nil
Item = {CreateFromItemID = function(_, id)
    return {
        ContinueOnItemLoad = function(_, done) callbacks[id] = done end,
        GetItemName = function() return GetItemInfo(id) end,
        GetItemLink = function() return "item:" .. id end,
        GetItemIcon = function() return "icon" end,
    }
end}
ui:Open(); H.settle(); ui:SetContentMode("leveling"); H.settle(); ui:SetTab("Equipped"); H.settle()
local tile = ui.gearFrame.slots.Head
assert(tile.gearData.stat_rank.status == "loading" and callbacks[first])
assert(tile.rating:GetText() == "Loading stats" and not tile.rating.rankStripe)
tile:Click(); H.settle()
H.equipped[1] = second
ui:Invalidate("ownership"); ui:Refresh(); H.settle()
assert(tile.gearData.item_id == second and callbacks[second])
H.coldItems[first] = nil
callbacks[first](); H.settle()
assert(tile.gearData.item_id == second and tile.gearData.stat_rank.status == "loading")
H.coldItems[second] = nil
callbacks[second](); H.settle()
assert(tile.gearData.stat_rank.item.id == second and tile.gearData.stat_rank.rank)
assert(not tile.rating.rankStripe and tile.rating.textColor)
assert(tile.itemName.textColor[1] == 30/255 and tile.itemName.textColor[2] == 1)
assert(ui.gearFrame.summary.itemName.textColor[1] == 30/255)
assert(ui.gearFrame.summary.gearData == tile.gearData)
local reads = statsCalls[second]
ui.frame:SetSize(1160, 660); H.settle()
assert(statsCalls[second] == reads, "resizing should reuse the resolved item")
''')

    def test_upgrades_and_details_share_the_selected_route(self):
        self.run_lua(r'''
local function candidate(id, status, route, higher)
    return {item_id = id, name = "Item " .. id, slot = "Head", priority = 100, hasCurrent = true,
        upgrade_candidate = true, higher_rated = higher, reasons = {"Alternative this phase"},
        access = {status = status, optionEvaluation = route and {option = route, status = status}, options = {}}}
end
local live = {label = "Keeper", zone = "Live Dungeon", source_type = "drop"}
local future = {label = "Future boss", zone = "Future Dungeon", source_type = "drop"}
local bag = candidate(990051, "unknown", nil, true)
local available = candidate(990052, "ready", live)
local upcoming = candidate(990053, "ready", future)
local unknown = candidate(990054, "unknown", live)
local higher = candidate(990055, "ready_alternate", live)
available.recommendation_tier, upcoming.recommendation_tier = "chase_first", "strong_targets"
local rows = {upcoming, available, available, unknown, higher, bag}
GetContainerNumSlots = function(bagId) return bagId == 0 and 1 or 0 end
GetContainerItemID = function() return bag.item_id end
BigBiSList.GetPlannerRows = function() return rows end
BigBiSList.IsAccessOptionPhaseAvailable = function(_, option) return option ~= future end
ui.GetAccessEvaluation = function(_, row) return row.access or {status = "unknown", options = {}} end
ui:Open(); H.settle(); ui:SetTab("Upgrades"); H.settle()
local active = ui.activeRenderFrames
assert(#active == 3 and active[1].boundData == bag and active[2].boundData == available and active[3].boundData == higher)
assert(active[1].sourceText:GetText() == "Bags" and active[2].sourceText:GetText():find("Live Dungeon", 1, true))
assert(not ui.sortDropdown:IsVisible() and not ui.groupDropdown:IsVisible())
active[2].iconButton:Click(); H.settle()
local fields, recommendation = ui.detailsWidgetPools.fields[1], ui.detailsWidgetPools.text[1]
assert(fields:GetBottom() > recommendation:GetTop() and fields.fields[1].value:GetText() == "Keeper")
ui.activeRenderFrames[1].iconButton:Click(); H.settle()
assert(recommendation:GetBottom() > fields:GetTop(), "owned item should lead with comparison and ownership")
local queryBuilds = ui:GetPerformanceStats().queryBuilds
ui:GetViewState().collapsedGroups = { ["planner:Future best in slot"] = true }
ui.upgradesViewButton:Click(); H.settle()
assert(ui.renderModel.columnMode == "planner" and ui:GetPerformanceStats().queryBuilds == queryBuilds)
assert(ui.sortDropdown:IsVisible() and ui.groupDropdown:IsVisible())
local headings = {}
for _, entry in ipairs(ui.renderModel.entries) do
    if entry.kind == "section" then headings[entry.title] = entry end
end
assert(headings["Top targets"].sectionKey == "planner:Best in slot now")
assert(headings["Plan ahead"].collapsed and headings["Plan ahead"].sectionKey == "planner:Future best in slot")
ui.upgradesViewButton:Click(); H.settle()
assert(ui.activeRenderFrames[1].boundData == bag)
rows = {upcoming, unknown}
ui:Invalidate("query", "unavailable-actions"); ui:Refresh(); H.settle()
assert(ui.renderModel.columnMode == "planner" and not ui.upgradesViewButton:IsVisible())
''')

    def test_leveling_activity_counts_routes_and_previews_filtered_levels(self):
        self.run_lua(r'''
local addon, addonData = BigBiSList, BigBiSListData
UnitLevel = function() return 56 end
H.equipped[11], H.equipped[13] = 990201, 990203
GetInventoryItemLink = function(_, slot) return slot == 11 and "item:990201:0:0:0:0:0:-8" or nil end

local function drop(name, zone, level)
    return {type = "drop", content_type = "dungeon", entity_name = name, zone = zone,
        activity_zones = {zone}, eligibility = {min_level = level or 1}}
end
local wrong = drop("Level gated boss", "Other Cellar", 59)
local matched = drop("Champion", "Trial Halls")
wrong.quest_starter_item_id, matched.quest_starter_item_id = 990190, 990191
wrong.quest_starter_name, matched.quest_starter_name = "Sealed Orders", "Champion's Orders"
local function route(source, primary)
    return {source = source, zone = source.zone, source_type = source.type, is_primary = primary, label = source.entity_name}
end
local compound = route({type = "quest", zone = "Quest City", entity_name = "Champion's Reward",
    quest_starter_sources = {wrong, matched}, eligibility = {min_level = 1}}, true)
local alternate = route(drop("Alternate boss", "Alternate Halls"), false)
local function pick(id, name, variant, firstLevel, options, slot)
    addonData.item_eligibility[id] = {min_level = firstLevel}
    return {item_id = id, name = "Trial " .. name, variant_id = variant, slot = slot or "Ring",
        leveling = true, level_min = firstLevel, level_label = "Recommended at level " .. firstLevel, access_options = options}
end
local function inHalls(name, zone)
    return {route(drop(name, zone or "Trial Halls"), true)}
end
local displayed = {
    pick(990201, "Band of Stamina", "990201:-7", 56, {compound, alternate}),
    pick(990201, "Duplicate band", "990201:-7", 56, {compound, alternate}),
    pick(990201, "Band of Power", "990201:-8", 56, {compound, alternate}),
    pick(990203, "Unknown ownership", "990203:-7", 56, inHalls("Champion")),
    pick(990204, "Rumor", nil, 56, {route({type = "unknown", eligibility = {min_level = 1}}, true)}),
    pick(990205, "Future band", nil, 57, inHalls("Champion")),
    pick(990206, "Miner's Ring", nil, 57, inHalls("Miner", "Deadmines")),
    pick(990207, "Foreman's Ring", nil, 58, inHalls("Foreman", "The Deadmines")),
    pick(990208, "Wrong slot", nil, 58, inHalls("Champion"), "Head"),
    pick(990209, "Wrong name", nil, 58, inHalls("Champion")),
    pick(990210, "Future phase", nil, 56, inHalls("Champion", "Unreleased Halls")),
}
displayed[10].name = "Unrelated band"
displayed[11].access_options[1].acquisitionPhaseIndex = 2
local queried = {}
function addon:GetLevelingRows(class, spec, level, filters)
    queried[level] = true
    local scoped = {}
    for key, value in pairs(filters or {}) do scoped[key] = value end
    scoped.class, scoped.level, scoped._leveling = class, level, true
    local rows = {}
    for _, item in ipairs(displayed) do
        if item.level_min <= level and self:RowMatchesFilters(item, scoped, "LEVELING") then
            local row = {}
            for key, value in pairs(item) do row[key] = value end
            row.acquisition_display = self:GetRowAcquisitionDisplay(row, scoped, "LEVELING")
            row.matched_access_option = row.acquisition_display.option
            rows[#rows + 1] = row
        end
    end
    return {{items = rows}}
end

ui:Open(); H.settle(); ui:SetContentMode("leveling"); H.settle()
ui:SetFilter("search", "Trial"); ui:SetFilter("slots", {Rings = true}); H.settle()
assert(ui:GetViewState().groupBy == "slot" and not queried[57])
ui:SelectGrouping("activity"); H.settle()
local function entries(kind)
    local matches = {}
    for _, entry in ipairs(ui.renderModel.entries) do if entry.kind == kind then matches[#matches + 1] = entry end end
    return matches
end
local function clickTitle(title)
    for _, button in ipairs(ui.activeRenderFrames) do
        local entry = button.__bigBisBoundRenderEntry
        if entry.title == title then button:Click(); H.settle(); return end
    end
    error("Missing activity " .. title)
end
local actions = entries("action")
assert(#actions == 3 and actions[1].title == "Trial Halls" and actions[1].detail == "3 items · 1 unowned with known sources")
assert(actions[2].title == "Unknown" and actions[2].detail == "1 item · 0 unowned with known sources")
assert(actions[3].title == "The Deadmines" and actions[3].detail == "Recommended at level 57")
assert(queried[56] and queried[57] and queried[58] and queried[59] and not queried[60])

local builds = ui:GetPerformanceStats().queryBuilds
clickTitle("The Deadmines")
local preview = entries("section")[1]
assert(preview.title == "Next levels" and preview.sectionKey == "list:Coming up")
assert(preview.collapsed and preview.count == 2 and #entries("note") == 0)
clickTitle("Next levels")
assert(ui:GetViewState().collapsedGroups["list:Coming up"] == false)
local notes = entries("note")
assert(#notes == 2 and notes[1].text == "Level 57 · Trial Miner's Ring · Ring")
assert(notes[2].text == "Level 58 · Trial Foreman's Ring · Ring")
ui.levelingActivityBar.back:Click(); H.settle()
clickTitle("Trial Halls")
assert(ui:GetPerformanceStats().queryBuilds == builds and #entries("row") == 4)
assert(entries("row")[1].data.acquisition_display.matched_dependency == matched)

ui:SetFilter("sourceTypes", {dungeon_drop = true}); ui:SetFilter("zones", {["Trial Halls"] = true})
ui:SetFilter("ownedState", "missing"); H.settle()
assert(ui.levelingActivity == "Trial Halls" and #entries("row") == 3 and entries("section")[1].count == 1)
ui:SetFilter("zones", {["Other Cellar"] = true}); H.settle()
actions = entries("action")
assert(not ui.levelingActivity and #actions == 1 and actions[1].detail == "Recommended at level 59")
queried = {}
ui:SetLevelingLevel(59); H.settle()
assert(queried[59] and not queried[60] and entries("action")[1].detail == "1 item · 1 unowned with known sources")
ui:SetFilter("search", "no matching item"); H.settle()
assert(ui.emptyLabel:IsVisible() and not ui.levelingActivityBar:IsShown())
''')

    def test_leveling_run_keeps_quest_progress_slot_and_scroll_through_details(self):
        self.run_lua(r'''
local addon = BigBiSList
UnitLevel = function() return 42 end
H.equipped[11], H.equipped[12] = 990001, 990001
GetInventoryItemLink = function(_, slot) return H.equipped[slot] and ("item:" .. H.equipped[slot] .. ":0:" .. slot) end
local destination = {map_id = 1453, x = 0.40, y = 0.62, name = "Quartermaster"}
local function quest(id, name, kind, start)
    return {quest_id = id, name = name, kind = kind or "reward", start = start or {name = "Scout"}, finish = destination}
end
local orders = {quest(100, "Optional detour", "alternative"), quest(101, "First trial", "prerequisite"),
    quest(102, "Orders", "prerequisite"), quest(103, "Second trial")}
local report, extra, more = {quest(104, "Report")}, {quest(105, "Supplies")}, {quest(106, "Dispatch")}
local state = {[101] = "done", [104] = "ready"}
C_QuestLog = {
    IsQuestFlaggedCompleted = function(id) if state[id] ~= "unknown" then return state[id] == "done" end end,
    IsOnQuest = function(id) return state[id] == "active" or state[id] == "ready" end,
    IsComplete = function(id) return state[id] == "ready" end,
}
local waypoints, combat = {}, false
InCombatLockdown = function() return combat end
UiMapPoint = {CreateFromCoordinates = function(...) return {...} end}
C_Map = {CanSetUserWaypointOnMap = function(id) return id == 1453 end,
    SetUserWaypoint = function(point) waypoints[#waypoints + 1] = point end}

local area = "Trial Halls"
local rows = {}
for index = 1, 21 do
    local steps = ({orders, orders, report, extra, more})[index]
    local source = {type = steps and "quest" or "drop", zone = area, entity_name = "Trial source " .. index,
        eligibility = {min_level = 1}, quest_steps = steps}
    local option = {source = source, source_type = source.type, zone = area, label = source.entity_name, is_primary = true}
    rows[index] = {item_id = 990220 + index, name = "Trial Band " .. index, slot = "Ring", leveling = true,
        level_min = 42, level_label = "Recommended at level 42", access_options = {option}}
end
function addon:GetLevelingRows(class, spec, level, filters)
    local scoped = {class = class, faction = "Alliance", race = "Night Elf", level = level, _leveling = true}
    local picks = {}
    for _, row in ipairs(rows) do
        local pick = {}
        for key, value in pairs(row) do pick[key] = value end
        pick.acquisition_display = self:GetRowAcquisitionDisplay(pick, scoped, "LEVELING")
        pick.matched_access_option = pick.acquisition_display.option
        picks[#picks + 1] = pick
    end
    return {{items = picks}}
end
local comparisonReference
local compare = addon.GetLevelingEquipmentComparison
function addon:GetLevelingEquipmentComparison(row, reference)
    comparisonReference = reference
    return compare(self, row, reference)
end
local function questActions()
    local actions = {}
    for _, entry in ipairs(ui.renderModel.entries) do if entry.kind == "action" then actions[#actions + 1] = entry.title end end
    return table.concat(actions, " / ")
end
local function click(title)
    ui.contentScroll:SetVerticalScroll(0)
    for _, button in ipairs(ui.activeRenderFrames) do
        if button.__bigBisBoundRenderEntry.title == title then button:Click(); H.settle(); return end
    end
    error("Missing action " .. title)
end
local function questChanged()
    local events = addon.uiEventFrame
    events:GetScript("OnEvent")(events, "QUEST_LOG_UPDATE"); H.settle()
end
local function waypoint()
    for _, block in ipairs(ui.detailsWidgetPools["source-waypoint"] or {}) do if block:IsVisible() then return block end end
end

ui:Open(); H.settle(); addon:InitUIEvents()
ui:SetContentMode("leveling"); H.settle(); ui:SetTab("Equipped"); H.settle()
ui.gearFrame.slots.Finger1:Click(); ui.gearFrame.summary.findButton:Click(); H.settle()
ui:SelectGrouping("activity"); H.settle(); click(area)
assert(questActions() == "Turn in Report / Pick up Orders / Pick up Supplies")
click("Turn in Report")
assert(ui.selectedItemId == rows[3].item_id and comparisonReference.inventorySlotId == 12)
assert(comparisonReference.item_link == "item:990001:0:12")
assert(ui.detailsWidgetPools.fields[1].fields[1].value:GetText() == "Trial source 3")
assert(waypoint().destination == destination and #waypoints == 0)
combat = true; waypoint().button:Click(); assert(#waypoints == 0)
combat = false; waypoint().button:Click(); assert(#waypoints == 1 and waypoints[1][3] == 0.62)

local builds = ui:GetPerformanceStats().queryBuilds
state[104], state[102] = "done", "active"; questChanged()
assert(questActions() == "Pick up Supplies / Pick up Dispatch")
state[102] = "ready"; questChanged()
assert(questActions():find("Turn in Orders", 1, true) == 1)
state[102] = "done"; questChanged()
assert(questActions():find("Pick up Second trial", 1, true) == 1)
state[102] = "unknown"; questChanged()
assert(questActions() == "Pick up Supplies / Pick up Dispatch" and ui:GetPerformanceStats().queryBuilds == builds)
click("Pick up Supplies")
assert(ui.selectedItemId == rows[4].item_id and not waypoint(), "named endpoints require verified coordinates for map actions")

local function checkLayout()
    local bar = ui.levelingActivityBar
    H.expectBounded(bar, ui.contentRegion, "activity bar")
    H.expectBounded(bar.back, bar, "All activities")
    H.expectBounded(bar.title, bar, "activity title")
    assert(bar:IsVisible() and bar.back:IsEnabled() and bar:GetBottom() > ui.contentPanel:GetTop())
    assert(ui.stickyHeaderMode == "leveling" and ui.contentHeaderHost:IsVisible())
    H.expectRowsBounded(ui, "activity")
    for _, frame in ipairs(ui.activeRenderFrames) do
        if frame.__bigBisBoundRenderEntry.kind == "action" then
            H.expectBounded(frame.label, frame, "quest action label")
            H.expectBounded(frame.detail, frame, "quest endpoint label")
            assert(frame.label:GetRight() < frame.detail:GetLeft())
        end
    end
end
for _, size in ipairs({{1020, 560}, {1160, 660}}) do
    ui.frame:SetSize(size[1], size[2]); H.settle()
    for _, density in ipairs({"compact", "comfortable"}) do
        addon:GetAccountDB().profile.window.density = density
        ui:Invalidate("presentation", "test-density"); ui:Refresh(); H.settle()
        ui:SetInspectorVisible(false); H.settle(); checkLayout()
        ui:SetInspectorVisible(true); H.settle(); checkLayout()
        assert(ui.inspectorDocked and ui.levelingActivity == area and ui:GetPerformanceStats().queryBuilds == builds)
    end
end
ui:SetInspectorVisible(false); H.settle()
UIParent:SetSize(900, 500); ui.frame:SetSize(900, 500); H.settle(); checkLayout()
ui.contentScroll:SetVerticalScroll(162)
for _, frame in ipairs(ui.activeRenderFrames) do
    local entry = frame.__bigBisBoundRenderEntry
    if entry.kind == "row" and entry.top >= 162 then frame.iconButton:Click(); break end
end
H.settle()
assert(ui.inspectorExclusive and ui.details:IsVisible() and ui:GetPerformanceStats().queryBuilds == builds)
ui.detailsBackButton:Click(); H.settle(); checkLayout()
assert(ui.levelingActivity == area and ui.contentScroll:GetVerticalScroll() == 162 and ui:GetLevelingReferenceSlot() == "Finger1")
ui:SetLevelingLevel(43); H.settle()
assert(ui.levelingActivity == area and questActions() == "" and ui.renderModel.rowCount == #rows)
''')


if __name__ == "__main__":
    unittest.main()
