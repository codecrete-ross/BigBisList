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
highlights:Initialize(); H.settle()
local offered = assert(mark(first, 901002))
assert(offered.entry.owned and not offered.ownedBaseline and offered.result.delta == 4)
local badge
for _, child in ipairs(first.children) do if child.border then badge = child end end
assert(badge and not badge.animation and not badge.glow and badge.icon:IsShown())
H.expectBounded(badge, first, "bag badge")
for _, edge in ipairs(badge.border) do H.expectBounded(edge, badge, "bag badge border") end
assert(mark(second, 901005).spec.name == "Holy", "An owned off-spec upgrade compares with worn gear")
assert(mark(bankItem, 901004).result.delta == 6)
local tip = showTip(first, link(901002))
assert(tip:find("+4.0 pts", 1, true) and tip:find("Finger", 1, true) == nil)
assert(not tip:find("vs the best gear you own", 1, true))

H.equipped[1] = 901002
ui:Invalidate("ownership", "equip-from-bag"); event("BAG_UPDATE_DELAYED")
assert(not mark(first, 901002) and mark(bankItem, 901004).result.delta == 2)
contents[0][1] = "item:901006:0:0:0:0:0:0:0:47:0:0:0:1:700"
ui:Invalidate("ownership", "exact-variant-move"); bags:UpdateItems(); H.settle()
assert(not mark(first, 901002) and mark(first, contents[0][1]).result.delta == 4)

contents[0][1], cold[901020] = link(901020), true
ui:Invalidate("ownership", "cold-bag-item"); bags:UpdateItems(); H.settle()
assert(not mark(first, 901020) and coldCallbacks[901020])
cold[901020] = nil
coldCallbacks[901020](); H.settle()
assert(mark(first, 901020).result.delta == 5)

addon:GetAccountDB().profile.gearHighlights.bags = false
highlights:ScheduleRefresh(); H.settle()
assert(not mark(first, 901020) and mark(bankItem, 901004))
bankKind = 2
panel:GenerateItemSlotsForSelectedTab(); H.settle()
assert(not mark(bankItem, 901004), "The personal-bank adapter excludes account bank rows")
bankKind, ui.personalBankOpen = 1, false
event("BANKFRAME_CLOSED")
assert(not mark(bankItem, 901004))
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
for index = 1, 8 do
    assert(redraw(freshDetails()))
    H.settle()
    assert(not highlights.queued and mark(button, 901002).result == cached)
end
assert(refreshes == initialRefreshes, "An unchanged Baganator row reuses its result")
button:Hide(); H.settle(); button:Show()
assert(redraw(freshDetails()), "A reopened bag gets the badge on its first draw")
H.settle()
assert(refreshes == initialRefreshes and mark(button, 901002).result == cached)

highlights.tooltipDirty = true
highlights:ScheduleRefresh(); H.settle()
assert(refreshes == initialRefreshes, "Tooltip-only updates do not redraw Baganator")

contents[0][1], details.itemLink = link(901006), link(901006)
ui:Invalidate("ownership", "baganator-recycle")
redraw(details); H.settle()
assert(not mark(button, 901002) and not mark(button, 901006) and not widget:IsShown())
details = {itemLink = link(901004), itemLocation = {bagID = 20, slotIndex = 1}}
button.BGR, ui.personalBankOpen = details, true
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
ui:Invalidate("ownership", "restore-baganator-item")
redraw(details); H.settle()
assert(mark(button, 901002))
local compare = rating.CompareTooltipItem
rating.CompareTooltipItem = function(self, ...)
    local assessment = compare(self, ...)
    assessment.bis = true
    return assessment
end
highlights:ScheduleRefresh(); H.settle()
assert(widget.bis:IsShown() and not widget.icon:IsShown())
local gold = addon.Widgets.Theme.bisGold
for _, edge in ipairs(widget.border) do
    for component = 1, 3 do assert(edge.colorTexture[component] == gold[component]) end
end
H.expectBounded(widget.bis, widget, "BiS badge text")
rating.CompareTooltipItem = compare
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
assert(mark(first, 901003).result.delta == 3 and not mark(first, 901003).ownedBaseline)
assert(mark(second, 901004).outline and mark(second, 901004).result.delta == 6)
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
cold[901010] = true
QuestInfo_Display(); H.settle()
assert(not mark(first, 901010) and not mark(second, 901011) and coldCallbacks[901010])
cold[901010] = nil
coldCallbacks[901010](); H.settle()
assert(mark(first, 901010).sellValue == 60 and not mark(second, 901011))
assert(showTip(first, link(901010)):find("Highest sell value", 1, true))

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
assert(mark(first, 901006).result.bis and mark(first, 901006).bestChoice)
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
