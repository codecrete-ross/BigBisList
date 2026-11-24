"""Full-catalog acceptance for the packed Forever Gear Guide."""

import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


SETUP = r'''
local H = dofile("tests/lua_ui_harness.lua")
local level, worn = 49, 10090
local gothic = "item:10090::::::::50:1486::1:1:12723:1:28:5253:::::"
UnitClass = function() return "Paladin", "PALADIN" end
UnitClassBase = function() return "PALADIN" end
UnitRace = function() return "Human", "Human", 1 end
UnitFactionGroup = function() return "Alliance" end
UnitLevel = function() return level end
GetInventoryItemID = function(_, slot) if slot == 1 then return worn end end
GetInventoryItemLink = function(_, slot) if slot == 1 then return worn == 10090 and gothic or "item:" .. worn end end
local ui = H.load("forever", true)
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
addon.DetectPlayerSpec = function() return "Retribution" end
addon:RefreshTooltipPlayerContext()
local selection = ui:GetSelection()
selection.class, selection.spec, selection.mode, selection.phase, selection.tab =
    "Paladin", "Retribution", "leveling", "LEVELING", "Gear Guide"
addon:SetSelectedLevelingLevel(49, true)
local function applyListUpdate()
    if ui.updateGuideButton and ui.updateGuideButton:IsVisible() then ui.updateGuideButton:Click(); H.settle() end
end
'''


class ForeverGuidePerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()
        if not cls.lua:
            raise unittest.SkipTest("Lua 5.1 is unavailable")

    def lua_run(self, code: str, setup=SETUP):
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, timeout=120, encoding="utf-8",
                                capture_output=True, input=setup + code + "\nassert(#H.errors == 0, table.concat(H.errors, '\\n'))")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_background_work_waits_for_a_new_frame_after_spending_its_budget(self):
        self.lua_run(r'''
local ran = false
debugprofilestop = function() return 10 end
local stats = ui:GetPerformanceStats()
stats.timingFrame, stats.frameTime = H.now, 2
rating:QueueWork(1, function() ran = true end, function() return true end)
H.tick(); H.tick()
assert(not ran, "A second callback reused the exhausted frame budget")
H.now = H.now + 1/60; H.tick()
assert(ran, "Background work did not resume on the next frame")
''')

    def test_first_page_survives_client_patches_and_index_loss(self):
        for build, index in ((70959, "shipped"), (71037, "shipped"), (71037, "missing"), (71037, "incompatible"), (71037, "partial")):
            with self.subTest(build=build, index=index):
                loader = f'GetBuildInfo = function() return "Forever", "{build}" end\n'
                if index == "incompatible":
                    loader += '''local load = dofile
dofile = function(file)
    local result = load(file)
    if file == "GuideDataForever.lua" then BigBiSListData.guide_index.signature = "old data" end
    return result
end
'''
                loader += 'local ui = H.load("forever", ' + ("false" if index == "missing" else "true") + ')'
                if index == "partial":
                    loader += '\nBigBiSListData.guide_index.classes.Paladin = nil'
                setup = SETUP.replace('local ui = H.load("forever", true)', loader)
                self.lua_run(r'''
function addon:GetLevelingRows() error("Opened the entire catalog") end
function rating:GetGuidePlacement() error("Rebuilt a full ranking") end
local inventory = ui.BuildOwnedItems
local scans = 0
function ui:BuildOwnedItems(equippedOnly)
    assert(not equippedOnly, "Built a partial inventory")
    scans = scans + 1
    return inventory(self, equippedOnly)
end
local function tick() H.now = H.now + 1/60; H.tick() end
local function visible()
    local count, row = 0
    for _, frame in ipairs(ui.activeRenderFrames or {}) do
        if frame:IsVisible() and frame.boundData and frame.boundData.stat_rank then
            count, row = count + 1, row or frame
        end
    end
    return count, row
end
addon:InitUIEvents()
H.usePaladinReferenceTalents("Retribution")
ui:PrepareRememberedWorkspace()
assert(scans == 1 and not ui.frame:IsVisible())
ui:Open()
for i = 1, 3 do tick() end
local count, first = visible()
assert(count >= 3 and ui.renderModel.rowCount >= count, "Cold page lacks actionable rows")
assert(scans == 1 and ui.renderModel.targetQuery.done)
assert(not ui.gearFrame, "Opening the Guide constructed the My Gear paper doll")
assert(ui:GetPerformanceStats().firstViewportMs and ui:GetPerformanceStats().firstViewportMs <= 50.01,
    "The visible page must bind within three 60 Hz frames")
assert(first.boundData.acquisition_display.status == "ready" and ui:GetSourceNextStep(first.boundData))
first.iconButton:Click(); tick()
assert(ui.selectedItemData and ui.selectedItemData.item_id == first.boundData.item_id)
assert(ui.selectedItemData.matched_access_option.source)
ui:SetInspectorVisible(false)
H.settle(); ui:Close(); ui:Open(); tick()
assert(visible() > 0)
local _, reopened = visible()
reopened.iconButton:GetScript("OnEnter")(reopened.iconButton); H.settle()
local help = table.concat(GameTooltip.lines, "\n"):lower()
assert(help:find("upgrade", 1, true) or help:find("compare", 1, true) or help:find("guide pick", 1, true)
    or help:find("fills your empty", 1, true)
    or reopened.boundData.targetVerdict.kind == "utility" and #GameTooltip.lines >= 2, help)
reopened.iconButton:GetScript("OnLeave")(reopened.iconButton)
ui:SetFilter("search", "item:7719"); H.settle()
assert(ui.renderModel.targetQuery.exact and ui.renderModel.rowCount == 1)
ui:SetFilter("search", ""); level = 51
ui:SetLevelingLevel(51); H.settle()
assert(visible() > 0 and ui.renderModel.guideContext.level == 51)
assert((rating.fullPoolRequests or 0) == 0 and (rating.unindexedSummaryRequests or 0) == 0)
''', setup)

    def test_core_route_preparation_finishes_before_showing_click_targets(self):
        setup = SETUP.replace('H.load("forever", true)', 'H.load("forever", false)')
        self.lua_run(r'''
level = 51
addon.DetectPlayerSpec = function() return "Protection" end
addon:SetSelection("Paladin", "Protection", "LEVELING", "Gear Guide")
addon:RefreshTooltipPlayerContext(); addon:SetSelectedLevelingLevel(51, true)
local spent, prepare = 0, addon.GetRowAcquisitionDisplay
debugprofilestop = function() return H.now * 1000 + spent end
function addon:GetRowAcquisitionDisplay(...)
    if ui.openingGuide then spent = spent + 0.7 end
    return prepare(self, ...)
end
ui:PrepareRememberedWorkspace()
assert(not ui.frame:IsVisible() and ui.renderModel.targetQuery.done)
ui:Open()
assert(ui.frame:IsVisible() and ui.guideDisplay and #ui.activeRenderFrames > 0)
assert(not ui.currentOwned.equippedOnly and ui:GetPerformanceStats().firstViewportMs <= 4)
''', setup)

    def test_collapsing_or_closing_the_first_page_finishes_the_inventory_snapshot(self):
        for opening in ("collapsed", "closed"):
            with self.subTest(opening=opening):
                self.lua_run('local opening = "' + opening + '"\n' + r'''
if opening == "collapsed" then
    local groups = {}
    ui:GetViewState().collapsedGroups = groups
    for _, slot in ipairs(addon.slotOrder) do groups["leveling:" .. slot] = true end
    groups["leveling:guide-market"] = true
end
addon:InitUIEvents()
ui:Open()
if opening == "closed" then
    H.now = H.now + 1/60; H.tick(); ui:Close(); H.settle(); ui:Open()
end
H.settle()
assert(ui.currentOwned and not ui.currentOwned.equippedOnly, "Guide never finished checking the bags")
assert(not ui.guideInventoryWaiting and ui.renderModel.targetQuery.done)
ui:SelectGrouping("collapse"); H.settle()
for _, frame in ipairs(ui.activeRenderFrames) do assert(not frame.boundData) end
ui:SelectGrouping("expand"); H.settle()
local gear = false
for _, frame in ipairs(ui.activeRenderFrames) do gear = gear or frame.boundData end
assert(gear, "Expanding the sections did not restore the clickable picks")
''')

    def test_first_open_and_bank_change_keep_the_item_under_the_pointer(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext(); addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {Head=true}
addon:InitUIEvents()
ui:PrepareRememberedWorkspace()
assert(not ui.frame:IsVisible())
ui:Open()
local first, picked, visible, bindings
for i=1,900 do
    H.now = H.now + 1/60; H.tick()
    if ui.frame:IsVisible() then
        local wanted = 0
        local viewport = ui.contentScroll:GetHeight()
        ui:VisitListEntries(ui.renderModel, 0, viewport, function(entry)
            if entry.top < viewport and entry.bottom > 0 then wanted = wanted + 1 end
        end)
        assert(#ui.activeRenderFrames == wanted)
        if not first then
            first, visible, bindings = i, ui.guideDisplay, {}
            for index, f in ipairs(ui.activeRenderFrames) do
                bindings[index] = f.bindToken
                if f.boundData and not picked then picked = f end
            end
            assert(picked); picked:SetHovered(true)
        else
            assert(ui.guideDisplay == visible and ui.contentScroll:GetVerticalScroll() == 0)
            for index, f in ipairs(ui.activeRenderFrames) do assert(f.bindToken == bindings[index]) end
        end
    end
end
assert(first and first <= 3)
local key, token = picked.boundData.stat_identity, picked.bindToken
function rating:GetOwnedOpportunity() return {delta=-2, replacements={}} end
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:9479"}, {"20:1"}
H.fireEvent("BAG_UPDATE_DELAYED"); H.settle()
assert(ui.pendingGuideModel and ui.updateGuideButton:IsVisible(), "An automatic swap displaced the pointer")
assert(ui.guideDisplay == visible and picked:IsVisible() and picked.hovered and picked.bindToken == token)
assert(picked.boundData.stat_identity == key and picked.boundData.targetVerdict.swap.delta == -2)
picked.iconButton:Click()
assert(ui.selectedItemData.stat_identity == key and ui:GetSourceNextStep(ui.selectedItemData))
applyListUpdate()
assert(not ui.updateGuideButton:IsShown() and ui.renderModel.targetQuery.done and ui.renderModel.rowCount == 0)
''')

    def test_supported_client_uses_verified_gothic_roll_and_banked_upgrade(self):
        setup = SETUP.replace('local ui = H.load', 'GetBuildInfo = function() return "Forever", "71037" end\nlocal ui = H.load')
        self.lua_run(r'''
level = 51
local traits = BigBiSListData.character_scoring.traits
local nodes, definitions = {}, {}
for entry, trait in pairs(traits) do
    nodes[trait.node_id], definitions[trait.definition_id] = tonumber(entry), trait.spell_id
end
C_ClassTalents = {GetActiveConfigID = function() return 1 end}
C_Traits = {
    GetConfigInfo = function() return {treeIDs = {1100}} end,
    GetNodeInfo = function(_, node) return {entryIDs = {assert(nodes[node])}} end,
    GetDefinitionInfo = function(id) return {spellID = definitions[id]} end,
}
local info, instant = GetItemInfo, GetItemInfoInstant
local function gothicLink(value) return type(value) == "string" and value:find("item:10090:", 1, true) end
GetItemInfo = function(value)
    if gothicLink(value) then return "Gothic Plate Helmet of the Gorilla", gothic, 2, 47, 41, "Armor", "Plate", 1, "INVTYPE_HEAD", 1 end
    return info(value)
end
GetItemInfoInstant = function(value)
    if gothicLink(value) then return 10090, "Armor", "Plate", "INVTYPE_HEAD", 1, 4, 4 end
    return instant(value)
end
C_Item = {GetItemInfo = GetItemInfo, GetItemInfoInstant = GetItemInfoInstant, GetItemStats = function(link)
    if gothicLink(link) then return {RESISTANCE0_NAME=362, ITEM_MOD_STRENGTH_SHORT=13, ITEM_MOD_INTELLECT_SHORT=13} end
end}
C_TooltipInfo = {GetHyperlink = function(link)
    if gothicLink(link) then return {lines={{leftText="362 Armor"}}} end
end}
addon:RefreshTooltipPlayerContext()
addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {Head=true}
addon:InitUIEvents(); ui:Open(); H.settle()
local function bucket() return ui.renderModel.targetQuery.slots.Head end
local exact = rating:NormalizeLink(10090, gothic)
local seen = assert(rating:GetPublishedFacts(exact))
assert(seen.stats.strength == 13 and ui.renderModel.guideContext.catalog.rollBuildMatches)
local expected = {["Embrace of the Lycan"]=true, ["Raging Berserker's Helm"]=true,
    ["Icemetal Barbute"]=true, ["Undying Headdress"]=true}
for _, row in ipairs(bucket().rows) do
    assert(expected[row.name] and row.targetVerdict.kind == "upgrade" and addon:IsGuideTargetRoute(row.matched_access_option), row.name)
    expected[row.name] = nil
end
assert(not next(expected), "A known obtainable helm upgrade disappeared")
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:9479"}, {"bank:1"}
local frame = addon.uiEventFrame
frame:GetScript("OnEvent")(frame, "BAG_UPDATE_DELAYED"); H.settle()
assert(ui.updateGuideButton:IsVisible() and bucket().positions["9479"])
applyListUpdate()
assert(not bucket().positions["9479"])
ui:SetFilter("search","item:7719"); H.settle()
local row = assert(bucket().rows[1])
assert(row.targetVerdict.swap.replacements[1].state == "bank" and row.lookupReason)
C_ClassTalents, C_Traits = nil, nil
-- This UI harness omits Core's talent event handler.
addon.ForeverScoring:Invalidate()
addon:RefreshTooltipPlayerContext()
addon:RefreshUI("query", "talents unavailable"); H.settle()
applyListUpdate()
row = assert(bucket().rows[1])
assert(row.targetVerdict.swap.buildUnavailable == "talents" and row.targetVerdict.swap.conditional
    and not row.targetVerdict.meaningful)
''', setup)

    def test_packed_pre_raid_scope_matches_every_published_item(self):
        self.lua_run(r"""
local bundle = BigBiSListData.guide_index
local scope = assert(bundle.preRaidScope)
local expected, phase = {}, addon:GetAvailabilityPhaseIndex("PR")
assert(scope.items == BigBiSListData.items and scope.phaseIndex == phase)
bundle.preRaidScope = nil
for key in pairs(BigBiSListData.runtime_indexes.items) do
    local id = assert(tonumber(key))
    expected[id] = addon:ComparisonItemInScope(id, "PR", phase)
end
assert(next(expected))
bundle.preRaidScope = scope
local lookup = addon.GetItemData
addon.GetItemData = function() error("The indexed Pre-Raid comparison rebuilt acquisition routes") end
for id, result in pairs(expected) do
    assert(addon:ComparisonItemInScope(id, "PR", phase) == result, id)
end
assert(addon:ComparisonItemInScope(9999999, "PR", phase))
addon.GetItemData = lookup
""")

    def test_retired_home_and_settings_preserve_workspace_and_saved_gear(self):
        self.lua_run(r'''
for _, mode in ipairs({"leveling","endgame"}) do
    local char = addon:GetCharacterDB()
    char.selection.mode, char.selection.tab, char.selectedTab = mode, "Home", "Home"
    char.selection.phase, char.selectedPhase = "PR","PR"
    char.selection.lastTabs = {endgame="Wishlist", leveling="Wishlist"}
    char.foreverModeSelected, char.foreverLevelingMigrated = true,true
    char.defaultsVersion = nil
    char.wishlist["9479"] = {item_id=9479}
    char.bankCache.links = {"item:6829"}
    ui:GetFilters("Gear Guide").search = "Lightforge"
    char = addon:GetCharacterDB()
    assert(char.selection.tab == (mode == "leveling" and "Gear Guide" or "Upgrades"))
    assert(char.selection.lastTabs[mode == "leveling" and "endgame" or "leveling"] == "Wishlist")
    assert(char.wishlist["9479"].item_id == 9479 and char.bankCache.links[1] == "item:6829")
    assert(ui:GetFilters("Gear Guide").search == "Lightforge")
    for _,tab in ipairs(ui:GetActiveTabNames()) do assert(tab ~= "Home") end
end
local char = addon:GetCharacterDB()
char.selection.mode, char.selection.phase, char.selection.tab = "endgame", "PR", "Wishlist"
char.selectedPhase, char.selectedTab = "PR", "Wishlist"
char.selection.lastTabs.leveling, char.defaultsVersion = "Home", nil
char = addon:GetCharacterDB()
assert(char.selection.tab == "Wishlist" and char.selection.lastTabs.leveling == "Gear Guide")
ui:Open(); H.settle(); ui:SetTab("Wishlist"); H.settle()
ui:OpenSettings(); H.settle()
assert(ui:GetSelection().tab == "Settings" and addon:GetCharacterDB().selection.tab == "Wishlist")
ui:ReturnFromSettings(); H.settle(); assert(ui:GetSelection().tab == "Wishlist")
''')

    def test_native_chrome_and_nested_comparison_returns(self):
        layouts = ((native, density, width, height)
                   for native in (True, False)
                   for density in ("comfortable", "compact")
                   for width, height in ((900, 500), (1020, 790)))
        for native, density, width, height in layouts:
            with self.subTest(native=native, density=density, width=width):
                self.lua_run(f'''
H.noPortraitTemplate = {str(not native).lower()}
UIParent:SetSize({width},{height})
local window = addon:GetAccountDB().profile.window
window.width,window.height,window.density = {width},{height},"{density}"
''' + r'''
ui:Open(); H.settle()
local frame = ui.frame
if frame.TitleContainer then
    assert(frame.TitleContainer.TitleText:GetText() == addon.displayName)
    assert(frame.CloseButton:GetParent() == frame and frame.TitleContainer:GetScript("OnDragStart"))
    assert(ui.settingsButton:GetTop() <= frame.TitleContainer:GetBottom())
    assert(ui.classDropdown:GetTop() <= frame.PortraitContainer.portrait:GetBottom())
else assert(ui.titleBar:GetScript("OnDragStart")) end
ui:SetFilter("slots",{Head=true}); H.settle()
ui.slotContextFrame.compareButton:Click(); H.settle()
local comp = assert(ui.slotComparison)
assert(ui.comparisonBackButton.label:GetText() == "Back to Gear Guide")
ui:SetComparisonSort("item"); H.settle()
local cmpScroll = math.min(120,ui.comparisonScroll:GetVerticalScrollRange())
assert(cmpScroll > 0)
ui.comparisonScroll:SetVerticalScroll(cmpScroll); H.settle()
local reference = comp.reference
local row = assert(comp.rows[2])
ui:ShowComparisonDetails(row); H.settle()
local scroll = math.min(50,ui.detailsScroll:GetVerticalScrollRange())
ui.detailsScroll:SetVerticalScroll(scroll)
ui.settingsButton:Click(); H.settle()
assert(ui.settingsPanel:IsVisible() and not ui.details:IsVisible() and ui.settingsBackButton.label:GetText()=="Back to Details")
assert(addon:GetCharacterDB().selection.lastTabs.leveling=="Gear Guide")
ui.settingsBackButton:Click(); H.settle()
assert(ui.slotComparison==comp and comp.sort=="item" and ui.selectedItemId==row.item_id and ui.details:IsVisible())
assert(ui.detailsScroll:GetVerticalScroll()==scroll)
ui.detailsBackButton:Click(); H.settle()
assert(not comp.detailsOpen and ui.comparisonFrame:IsVisible() and comp.reference == reference)
assert(ui.comparisonScroll:GetVerticalScroll() == cmpScroll)
ui.comparisonBackButton:Click(); H.settle()
assert(not ui.slotComparison and ui.contentRegion:IsVisible() and ui:GetFocusedBrowseSlot()=="Head")
ui.slotContextFrame.compareButton:Click(); H.settle(); assert(ui.slotComparison)
ui.tabButtons["Gear Guide"]:Click(); H.settle()
assert(not ui.slotComparison and ui.contentRegion:IsVisible() and ui:GetFocusedBrowseSlot()=="Head")
if frame.CloseButton then frame.CloseButton:Click(); assert(not frame:IsShown()) end
''')

    def test_item_details_and_endgame_back_restore_the_selected_row(self):
        self.lua_run(r"""
level = 60
addon:SetContentMode("endgame"); addon:SetSelection("Paladin", "Retribution", "PR", "By Slot")
ui:Open(); H.settle()
assert(ui.renderModel and ui.renderModel.endgame and ui.renderModel.complete)
local listOffset = math.min(240, ui.contentScroll:GetVerticalScrollRange())
assert(listOffset > 0)
ui.contentScroll:SetVerticalScroll(listOffset); H.settle()
local frame
for _, row in ipairs(ui.activeRenderFrames) do if row.boundData then frame = row; break end end
assert(frame and frame.iconButton.itemId == frame.boundData.item_id)
local id, scroll = frame.boundData.item_id, ui.contentScroll:GetVerticalScroll()
frame.iconButton:Click(); H.settle()
assert(ui.details:IsVisible() and ui.detailsCompareButton:IsVisible() and ui.selectedItemId == id)
ui.detailsCompareButton:Click(); H.settle()
assert(ui.comparisonBackButton:IsVisible() and ui.comparisonBackButton.label:GetText() == "Back to Details")
ui.comparisonBackButton:Click(); H.settle()
assert(ui.details:IsVisible() and ui.selectedItemId == id and ui.contentScroll:GetVerticalScroll() == scroll)
local compareAction, addMenuButton = nil, UIDropDownMenu_AddButton
UIDropDownMenu_AddButton = function(info) if info.text == "Compare slot" then compareAction = info.func end end
ui.detailsIdentity.menu:Click()
UIDropDownMenu_AddButton = addMenuButton
assert(compareAction)(); H.settle()
assert(ui.comparisonBackButton.label:GetText() == "Back to Details")
ui.comparisonBackButton:Click(); H.settle()
assert(ui.details:IsVisible() and ui.selectedItemId == id and ui.contentScroll:GetVerticalScroll() == scroll)
ui.tabButtons["By Slot"]:Click(); H.settle()
assert(not ui.slotComparison and ui.contentRegion:IsVisible())
ui:SetTab("Upgrades"); H.tick(); ui:SetTab("Wishlist"); H.settle()
assert(ui:GetViewKey() == "wishlist" and not (ui.renderModel and ui.renderModel.endgame))
ui:SetTab("Upgrades"); ui:SetFilter("search", "nosuchforeveritem"); H.settle()
assert(ui.emptyLabel:IsVisible() and not ui.guideStage)
ui:SetTab("Equipped"); H.settle()
assert(ui:GetViewKey() == "myGear")
ui.settingsButton:Click(); H.settle(); ui.settingsBackButton:Click(); H.settle()
assert(ui:GetViewKey() == "myGear" and addon:GetCharacterDB().selection.tab == "Equipped")
""")

    def test_endgame_first_page_keeps_its_hovered_click_target_during_updates(self):
        self.lua_run(r"""
level = 60
addon:SetContentMode("endgame"); addon:SetSelection("Paladin", "Retribution", "PR", "Upgrades")
ui:Open()
local pointed
for i = 1, 12 do
    H.now = H.now + 1/60; H.tick()
    if ui.renderModel and ui.renderModel.endgame and not ui.renderModel.complete then
        for _, row in ipairs(ui.activeRenderFrames) do if row.boundData then pointed = row; break end end
        if pointed then pointed:SetHovered(true); break end
    end
end
assert(pointed)
local id, top, token = pointed.iconButton.itemId, pointed:GetTop(), pointed.bindToken
H.settle()
assert(ui.updateGuideButton:IsVisible() and ui.pendingGuideModel.complete)
assert(pointed:IsVisible() and pointed.hovered and ui:IsCurrentRenderFrame(pointed))
assert(pointed.iconButton.itemId == id and pointed:GetTop() == top and pointed.bindToken == token)
pointed:SetHovered(false); ui.updateGuideButton:Click(); H.settle()
assert(ui.renderModel.complete and not ui.updateGuideButton:IsShown())
""")

    def test_saved_comparisons_survive_reload_and_change_with_the_bank(self):
        self.lua_run(r'''
level, worn = 51, 7719
local function profile(a)
    a.DetectPlayerSpec = function() return "Retribution" end
    a:RefreshTooltipPlayerContext()
    local bank = a:GetCharacterDB().bankCache
    bank.scanned = true
    bank.links, bank.locations = bank.links or {}, bank.locations or {}
    return bank
end
local function inspect(a)
    local service = a.ForeverGearRating
    local owned = a.UI:GetOwnedSnapshot()
    local context = service:GetContext("Paladin", "Retribution", "LEVELING", level, owned)
    local item = context.catalog.items["9479"]
    local result = service:GetOwnedOpportunity(context, item, "item:9479", false)
    assert(service:GetSwapExplanation(result))
    return result, a.Widgets:DecisionReason(item, result, context)
end
profile(addon)
addon:GetCharacterDB().guideComparisons = {version = 2, sets = {{signature = "old"}}}
local first, firstReason = inspect(addon)
assert(first and firstReason)
local cache = assert(addon:GetCharacterDB().guideComparisons)
assert(first.delta and cache.version == 3 and #cache.sets == 1 and #cache.sets[1].order > 0)
BigBiSList, BigBiSListData = nil, nil
ui = H.load("forever", true)
addon, rating = BigBiSList, BigBiSList.ForeverGearRating
profile(addon)
local read, hits = rating.ReadSavedOpportunity, 0
function rating:ReadSavedOpportunity(...)
    local result = read(self, ...)
    if result then hits = hits + 1 end
    return result
end
local second, secondReason = inspect(addon)
assert(second.delta == first.delta and hits == 1 and second.replacements[1].key == first.replacements[1].key)
assert(second.status == first.status and secondReason == firstReason)
for _, key in ipairs({"name", "slot", "state", "item_link"}) do
    assert(second.replacements[1][key] == first.replacements[1][key], key)
end
local bank = addon:GetCharacterDB().bankCache
bank.links, bank.locations = {"item:9479"}, {"bank:1"}
ui:Invalidate("ownership", "bank visit")
local banked = assert(inspect(addon))
assert(hits == 1 and (banked.status == "best_owned" or banked.delta == 0))
assert(#addon:GetCharacterDB().guideComparisons.sets == 2)
''')

    def test_defender_gloves_explain_the_same_swap_in_rows_hover_and_details(self):
        self.lua_run(r'''
level, worn = 51, 9640
addon.DetectPlayerSpec = function() return "Protection" end
addon:SetSelection("Paladin", "Protection", "LEVELING", "Gear Guide")
addon:SetSelectedLevelingLevel(level, true)
addon:RefreshTooltipPlayerContext()
local vice = assert(rating:GetPublishedFacts("9640:0:0:0:1:13027"))
local templar = assert(rating:GetPublishedFacts("10165:0:0:0:1:12754"))
local gloves = vice
GetInventoryItemID = function(_, slot) return slot == 10 and gloves.id or nil end
GetInventoryItemLink = function(_, slot) return slot == 10 and gloves.variant_link or nil end
local widgets = addon.Widgets
local function expect(text, part) assert(text:find(part, 1, true), text .. " missing " .. part) end
local function replay(from, to, points, grade, armor)
    local owned = {equippedSlots={Hands={item_id=from.id,item_link=from.variant_link}}}
    local ctx = rating:GetContext("Paladin", "Protection", "LEVELING", level, owned)
    for _, result in ipairs({assert(rating:GetGuideSwap(ctx, to, "Hands", "Hands", to.variant_link)),
        assert(rating:GetOwnedOpportunity(ctx, to, to.variant_link, false))}) do
        local changes = assert(rating:GetSwapExplanation(result))
        assert(math.abs(result.delta - points) < .000001 and changes.raw.armor == armor)
        if grade then
            assert(rating:UpgradeSize(result) == grade)
            assert(widgets:DecisionReason(to, result) == "More health and spell power, less AP")
        end
        local summary = table.concat(widgets:SwapExplanationLines(result), "\n")
        expect(summary, from.name)
        local detail = table.concat(widgets:SwapExplanationLines(result, true, true), "\n")
        expect(detail, "Selected reference · " .. from.name)
        expect(detail, points > 0 and "−14 Attack Power (−4.2 score points)" or "+14 Attack Power (+4.2 score points)")
        expect(detail, (armor < 0 and "−" or "+") .. math.abs(armor) .. " Armor")
    end
end
replay(vice, templar, 4.05, "Upgrade", 10)
replay(templar, vice, -4.05, nil, -10)
ui:GetFilters("Gear Guide").slots = {Hands = true}
ui:GetFilters("Gear Guide").search = templar.variant_link
addon:InitUIEvents()
ui:Open(); H.settle(); applyListUpdate()
local function row()
    for _, frame in ipairs(ui.activeRenderFrames) do
        if frame.boundData and frame.boundData.stat_identity == templar.key then return frame end
    end
    error("The exact roll has no visible row")
end
local first = row()
expect(first.subText.fullText, "Upgrade · More health and spell power, less AP")
local window = addon:GetAccountDB().profile.window
for _, dimensions in ipairs({{900,500},{1020,790}}) do
    for _, density in ipairs({"comfortable","compact"}) do
        window.width, window.height, window.density = dimensions[1], dimensions[2], density
        UIParent:SetSize(dimensions[1], dimensions[2])
        ui.frame:SetSize(dimensions[1], dimensions[2])
        ui:Invalidate("layout", "test gear advice width")
        ui:ScheduleRefresh(nil, "test gear advice width"); H.settle(); applyListUpdate()
        first = row()
        expect(first.subText.fullText, "Upgrade")
        local readable = first.subText.displayedText
        assert(readable:find("less AP", 1, true) or readable:find("−AP", 1, true), readable)
        H.expectBounded(first.subText, first, "Gear advice")
    end
end
first.iconButton:GetScript("OnEnter")(first.iconButton)
H.settle()
local hover = table.concat(GameTooltip.lines, "\n")
expect(hover, "Upgrade over Vice Grips of the Defender")
expect(hover, "losing 14 Attack Power")
expect(hover, "2 Spell Power, 1 Defense and 10 Armor")
assert(not hover:find("score points", 1, true))
local oldRead = rating.ReadNative
function rating:ReadNative(id, key, link, base)
    if id == 9640 then
        return {id=id, name=vice.name, level=vice.level, slot="Hands", armor_type="Plate",
            stats={armor=330, stamina=11, spell_power=5, defense=4, attack_power=14}, effects={}}
    end
    return oldRead(self,id,key,link,base)
end
rating:InvalidateItem(9640)
replay(vice, templar, 3.09, "Slight upgrade", -2)
-- Simulate the candidate and baseline being republished while the pointer stays
-- on the same row and its tooltip. Its item link and click target must survive.
local token, top = first.bindToken, first:GetTop()
local refreshed = {}
for key, value in pairs(first.boundData) do refreshed[key] = value end
local ctx = rating:GetContext("Paladin", "Protection", "LEVELING", level,
    {equippedSlots={Hands={item_id=vice.id,item_link=vice.variant_link}}})
refreshed.targetVerdict = {kind="upgrade", swap=rating:GetOwnedOpportunity(ctx, templar, templar.variant_link, false)}
ui:UpdateGuideRowAdvice(first, refreshed); H.settle()
assert(first.bindToken == token and first:GetTop() == top and first.iconButton.itemId == templar.id)
assert(GameTooltip:GetOwner() == first.iconButton)
expect(table.concat(GameTooltip.lines, "\n"), "2 less Armor")
expect(first.subText.fullText, "Slight upgrade")
first.iconButton:GetScript("OnLeave")(first.iconButton)
first.iconButton:Click(); H.settle()
assert(ui.selectedItemId == templar.id and ui:IsInspectorVisible())
local function visibleDetails()
    local lines = {}
    for _, frame in ipairs({ui.detailsContent:GetChildren()}) do
        if frame:IsVisible() then
            for _, label in ipairs({frame:GetRegions()}) do
                if label.GetText and label:IsVisible() and label:GetText() then lines[#lines + 1] = label:GetText() end
            end
        end
    end
    return table.concat(lines, "\n")
end
expect(visibleDetails(), "Slight upgrade over Vice Grips of the Defender")
local section = "calculation:" .. templar.key
local getExpanded = ui.IsDetailsSectionExpanded
function ui:IsDetailsSectionExpanded(key, default)
    if key == section then return true end
    return getExpanded(self, key, default)
end
ui.detailsRenderSignature = nil
ui:RefreshDetails(templar.id, ui.selectedItemData, ui.selectedItemMode); H.settle()
expect(visibleDetails(), "Best owned · Vice Grips of the Defender")
expect(visibleDetails(), "−14 Attack Power (−4.2 score points)")
expect(visibleDetails(), "−2 Armor (−0.16 score points)")
assert(ui:OpenSlotComparison(ui.selectedItemData, "leveling", true))
H.settle()
local selected
for _, candidate in ipairs(ui.slotComparison.rows) do
    if candidate.stat_swap and candidate.stat_swap.comparisonTrace and candidate.stat_swap.delta ~= 0 then
        selected = candidate
        break
    end
end
assert(selected and ui.slotComparison.reference.slotKey == "Hands")
assert(selected.stat_swap.comparisonTrace.before.Hands.facts.key == vice.key)
section = "calculation:" .. selected.stat_identity
local original = rating.GetGuideSwap
function rating:GetGuideSwap() error("Details must use the selected comparison's verdict") end
ui:ShowComparisonDetails(selected); H.settle()
rating.GetGuideSwap = original
expect(visibleDetails(), "Selected reference · Vice Grips of the Defender")
expect(visibleDetails(), " score points)")
''')

    def test_swap_explanations_identify_encounters_caps_sets_and_uncertain_effects(self):
        self.lua_run(r'''
local widgets = addon.Widgets
local function contains(text, part) assert(text:find(part, 1, true), text .. " missing " .. part) end
local shawl = assert(rating:GetPublishedFacts("19507"))
local mantle = assert(rating:GetPublishedFacts("16695"))
local function priest(before, after)
    local owned = {equippedSlots={Shoulder={item_id=before.id,item_link="item:"..before.id}}}
    local ctx = assert(rating:GetContext("Priest", "Discipline", "PR", 60, owned))
    local equipped = assert(rating:GetGuideSwap(ctx, after, "Shoulder", "Shoulder", "item:"..after.id))
    local best = assert(rating:GetOwnedOpportunity(ctx, after, "item:"..after.id, false))
    assert(equipped.conditional and best.conditional and equipped.weightReversal == best.weightReversal)
    assert(equipped.delta * equipped.weightReversal < 0)
    assert(not rating:ReliableGain(best))
    contains(widgets:DecisionReason(after, best), "Short fights")
    contains(widgets:SwapDecisionSummary(after, best), "Short fights")
    contains(table.concat(widgets:SwapExplanationLines(best), "\n"), "healing output")
end
priest(shawl, mantle)
priest(mantle, shawl)

local blackstone, painweaver = rating:GetPublishedFacts("17713"), rating:GetPublishedFacts("13098")
local hunter = rating:GetContext("Hunter", "Marksmanship", "PR", 60,
    {equippedSlots={Finger1={item_id=blackstone.id,item_link="item:17713"}}})
hunter.equipmentFacts.Head = {entry={item_id=90001},facts={id=90001,stats={hit_percent=8}}}
local ring = assert(rating:GetGuideSwap(hunter, painweaver, "Finger1", "Ring", "item:13098"))
local caps = assert(rating:GetSwapExplanation(ring))
assert(ring.delta > 0 and caps.raw.hit_percent == -1 and math.abs(caps.points.hit_percent) < .000001)
contains(widgets:DecisionReason(painweaver, ring), "ranged Hit cap")
contains(widgets:SwapDecisionSummary(painweaver, ring), "ranged Hit cap")
contains(table.concat(widgets:SwapExplanationLines(ring, true, true), "\n"), "−1% Hit (0 score points)")
local partial = rating:GetContext("Hunter", "Marksmanship", "PR", 60,
    {equippedSlots={Finger1={item_id=blackstone.id,item_link="item:17713"}}})
partial.equipmentFacts.Head = {entry={item_id=90001},facts={id=90001,stats={hit_percent=7.5}}}
local partialSwap = assert(rating:GetGuideSwap(partial, painweaver, "Finger1", "Ring", "item:13098"))
assert(partialSwap.delta > 0 and rating:GetSwapExplanation(partialSwap))
contains(widgets:DecisionReason(painweaver, partialSwap), "Some ranged Hit is above the cap")

local set = {key="tested",name="Practice Armor",bonuses={{pieces=2,stats={stamina=10}}}}
local function gloves(id, stats)
    return {id=id,key=tostring(id),name="Gloves " .. id,slot="Hands",level=41,armor_type="Plate",stats=stats}
end
local ordinary, matched = gloves(90004,{stamina=4}), gloves(90005,{stamina=1})
matched.effect_set, matched.effects = set, {"Set bonuses"}
local function swap(from,to)
    local context = rating:GetContext("Paladin", "Protection", "LEVELING", 51, {})
    context.equipmentFacts.Hands = {entry={item_id=from.id},facts=from,item_link="item:"..from.id}
    context.equipmentFacts.Chest = {entry={item_id=90006},facts={id=90006,stats={},effect_set=set}}
    local swap = assert(rating:GetGuideSwap(context, to, "Hands", "Hands"))
    assert(rating:GetSwapExplanation(swap))
    return swap
end
local gained, lost = swap(ordinary,matched), swap(matched,ordinary)
assert(gained.delta == 14 and lost.delta == -14)
assert(widgets:DecisionReason(matched,gained) == "Completes 2-piece Practice Armor bonus")
assert(widgets:SwapDecisionSummary(matched,gained) == "Completes 2-piece Practice Armor bonus")
assert(widgets:DecisionReason(ordinary,lost) == "Breaks 2-piece Practice Armor bonus")
local unpriced = gloves(90007,{stamina=8})
unpriced.effects = {"Use: Ward off flame."}
local risk = swap(ordinary,unpriced)
assert(risk.conditional and not rating:ReliableGain(risk))
contains(widgets:DecisionReason(unpriced,risk), "Ward off flame")
contains(widgets:SwapDecisionSummary(unpriced,risk), "Ward off flame")
local tie = swap(ordinary,gloves(90008,{stamina=4}))
assert(tie.delta == 0 and widgets:DecisionReason(nil,tie) == "same score")
assert(widgets:SwapDecisionSummary(nil,tie) == "Both setups score equally.")
local special = gloves(90009,{stamina=1})
special.effects = {"Equip: Stalwart."}
special.effect_rules = {{key="stalwart",label=special.effects[1],spell_name="Stalwart",kind="passive_stats",stats={stamina=8}}}
local priced = swap(ordinary,special)
assert(priced.delta == 8 and not priced.conditional)
assert(widgets:DecisionReason(special,priced) == "Gains Stalwart")
assert(widgets:SwapDecisionSummary(special,priced) == "Gains Stalwart")
''')

    def test_banked_sword_and_exact_roll_agree_across_wishlist_details_and_scoring(self):
        self.lua_run(r'''
level, worn = 51, 7719
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:6829", gothic}, {"20:1", "20:2"}
local owned = ui:GetOwnedSnapshot()
local ctx = rating:GetContext("Paladin", "Protection", "LEVELING", level, owned)
assert(ctx.ownedFacts["6829"].state == "bank")
local exact = rating:NormalizeLink(10090, gothic)
local stars = {["6829"]=true, [exact]={item_id=10090, variant_id=exact, item_link=gothic}}
local saved = addon:GetWishlistRows(stars, "Paladin", "Protection", "LEVELING", {ownedItems=owned})
assert(#saved == 2)
for _, row in ipairs(saved) do assert(row.owned and row.ownership_state == "bank" and ui:GetRowOwnershipState(row) == "bank") end
assert(ui:GetRowOwnershipState({item_id=10090, variant_id=exact.."9"}) == "missing")
assert(owned.bankScanned and ui:GetOwnershipState(6829) == "bank")
''')

    def test_equipped_aegis_keeps_its_banked_partner_and_verdict_after_reload(self):
        self.lua_run(r'''
level = 51
local weapons = {[16]=17705, [17]=1203}
GetInventoryItemID = function(_, slot) return weapons[slot] end
GetInventoryItemLink = function(_, slot) if weapons[slot] then return "item:" .. weapons[slot] end end
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:6829"}, {"20:1"}
local function verify(a)
    a.DetectPlayerSpec = function() return "Protection" end
    a:RefreshTooltipPlayerContext()
    local service = a.ForeverGearRating
    local ctx = service:GetContext("Paladin", "Protection", "LEVELING", level, a.UI:GetOwnedSnapshot())
    local shield = assert(ctx.ownedFacts["1203"])
    local verdict = service:GetHeldComparison(ctx, shield)
    assert(verdict.status == "best_owned" and verdict.delta == 0 and verdict.ownership == "equipped")
    assert(a.Widgets:DecisionReason(shield.facts, verdict, ctx) == "Best shield you own")
    local main, off = unpack(verdict.weaponSetup)
    assert(main.name == "Sword of Serenity" and main.state == "bank")
    assert(off.name == "Aegis of Stormwind" and off.state == "equipped")
    local swap = assert(service:GetOwnedOpportunity(ctx, ctx.equipmentFacts.MainHand.facts, "item:17705", false))
    local trace = assert(swap.comparisonTrace)
    assert(trace.before.MainHand.state == "bank" and trace.before.OffHand == trace.after.OffHand)
    assert(trace.before.OffHand.facts.id == 1203 and service:GetSwapExplanation(swap))
    assert(table.concat(a.Widgets:SwapExplanationLines(swap), "\n"):find("Sword of Serenity (bank)", 1, true))
end
verify(addon)
BigBiSList, BigBiSListData = nil, nil
H.load("forever", true)
verify(BigBiSList)
''')

    def test_rounded_zero_pick_stays_out_of_dungeon_and_partial_search(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext(); addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {Head=true}
local ordinal = BigBiSListData.guide_index.slots.Head.lookup["6686"]
function rating:GetGuideTargetPage() return {count=1, at=function() return ordinal end} end
function rating:GetOwnedOpportunity() return {delta=0.002} end
ui:Open(); H.settle()
local function head() return ui.renderModel.targetQuery.slots.Head end
assert(#head().rows == 0)
ui:SetFilter("zones", {["Razorfen Kraul"]=true}); H.settle(); assert(#head().rows == 0)
ui:SetFilter("zones", {}); ui:SetFilter("search", "Tuske"); H.settle(); assert(#head().rows == 0)
ui:SetFilter("search", "item:6686"); H.settle()
local helm = head().rows[1]
assert(helm.exactLookup and helm.targetVerdict.gain == 0.002 and helm.lookupReason:find("too small", 1, true))
''')

    def test_long_scroll_commits_one_clickable_page_and_keeps_the_last_requested_offset(self):
        self.lua_run(r'''
local window = addon:GetAccountDB().profile.window
window.width, window.height, window.density = 1020, 790, "comfortable"
ui:Open(); H.settle()
local previous = ui.guideDisplay
local first = ui.activeRenderFrames[1]
local screenTop = first:GetTop()
local spent, bind = 0, ui.BindListEntry
debugprofilestop = function() return H.now * 1000 + spent end
function ui:BindListEntry(...)
    spent = spent + 1.2
    return bind(self, ...)
end
ui.contentScroll:SetVerticalScroll(920)
ui.contentScroll:SetVerticalScroll(1650)
local function check()
    local page = ui.guideDisplay
    local index = 0
    ui:VisitListEntries(ui.renderModel, page.offset, page.offset+page.height, function(e)
        if e.bottom > page.offset and e.top < page.offset+page.height then
            index = index + 1
            local f = assert(ui.activeRenderFrames[index])
            assert(f:IsVisible() and ui:IsCurrentRenderFrame(f) and f.__bigBisBoundRenderEntry.top == e.top)
            if e.data then assert(f.iconButton.itemId == e.data.item_id and f.boundData.stat_identity == e.data.stat_identity) end
        end
    end)
    assert(index == #ui.activeRenderFrames)
    if page == previous then assert(math.abs(first:GetTop() - screenTop) < 0.5, "The previous page moved before its replacement was ready") end
end
for i=1,60 do
    check()
    if not ui.guideStage and ui.guideDisplay.offset == 1650 then break end
    spent = 0; H.now = H.now+1/60; H.tick()
end
check(); assert(ui.guideDisplay.offset == 1650)
local target
for _, frame in ipairs(ui.activeRenderFrames) do if frame.boundData then target = frame; break end end
assert(target); target.iconButton:Click()
assert(ui.selectedItemData.stat_identity == target.boundData.stat_identity and ui:GetSourceNextStep(ui.selectedItemData))
''')

    def test_stoneslayer_proc_changes_the_packed_rank_and_owned_upgrade(self):
        self.lua_run(r'''
GetItemInfo, GetItemStats, GetItemInfoInstant, C_Item, C_TooltipInfo = nil, nil, nil, nil, nil
local context = assert(rating:GetGuideContext("Paladin", "Retribution", "LEVELING", 51, "Human", "Alliance"))
local candidate = assert(rating:GetTooltipItem(9418, "item:9418"))
local sword = assert(candidate.facts)
assert(sword.level == 44 and sword.stats.dps == 42.69 and sword.stats.weapon_speed == 3.9)
assert(sword.stats.weapon_min_damage == 133 and sword.stats.weapon_max_damage == 200 and sword.stats.strength == nil)
assert(sword.effects[1]:find("196 Physical damage", 1, true))
local entry = rating:GetUnfilteredReferenceEntry(context, sword, "Two Hand")
local scorer = addon.ForeverScoring
local calculate = scorer.ScoreLoadout
scorer.ScoreLoadout = function() error("A packed reference lookup performed combat scoring") end
local packed = assert(rating:GetPackedGuideEntry(context, "Two Hand", "9418"))
local mace = assert(rating:GetPackedGuideEntry(context, "Two Hand", "7723"))
scorer.ScoreLoadout = calculate
assert(entry.score == packed.score and not entry.conditional and packed.rank < mace.rank)
assert(math.abs(packed.effectPoints - 9.7183) < 0.0001 and mace.score == 217.7)
local withoutProc = {}
for field, value in pairs(sword) do withoutProc[field] = value end
withoutProc.effects, withoutProc.effect_rules = {}, nil
assert(rating:GetUnfilteredReferenceEntry(context, withoutProc, "Two Hand").score == 213.45)
level = 51
local owned = {equippedSlots = {MainHand = {item_id = 7723, item_link = "item:7723"}}}
local personal = rating:GetContext("Paladin", "Retribution", "LEVELING", level, owned)
local row = {item_id = 9418, item_link = "item:9418", slot = "Two Hand", stat_rank = packed}
local verdict = rating:GetGuideTargetVerdict(row, context, {class = "Paladin", level = 51}, owned)
assert(verdict.kind == "upgrade" and math.abs(verdict.gain - 5.468333) < 0.0001)
local swap = rating:GetGuideSwap(personal, sword, "MainHand", "Two Hand", "item:9418")
assert(math.abs(swap.delta - verdict.gain) < 0.0001 and swap.estimatedEffects)
local lines = rating:EffectComparisonLines(swap)
local text = table.concat(lines, "\n")
for _, term in ipairs({"Stoneslayer", "+9.72 score points from item effects",
    "Strength of Stone", "0.85 procs/min", "weapon damage estimate", "above 0.37 procs/min", "588 against Earth Elementals"}) do
    assert(text:find(term, 1, true), text)
end
assert(lines == rating:EffectComparisonLines(swap))
GetInventoryItemID = function(_, slot) if slot == 16 then return 7723 end end
GetInventoryItemLink = function(_, slot) if slot == 16 then return "item:7723" end end
scorer:Invalidate()
addon:RefreshTooltipPlayerContext()
addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {["Two Hand"] = true}
ui:Open(); H.settle()
local bucket = ui.renderModel.targetQuery.slots["Two Hand"]
ui:SetFilter("zones", {Uldaman=true}); H.settle()
bucket = ui.renderModel.targetQuery.slots["Two Hand"]
local listed = assert(bucket.rows[bucket.positions["9418"]], "A useful pickup should appear when browsing its dungeon")
assert(listed.targetVerdict.kind == "upgrade" and listed.matched_access_option.source.entity_name == "Archaedas")
assert(listed.guideSpecialty:find("Earth Elementals", 1, true))
local tunic = assert(rating:GetTooltipItem(60, "item:60"))
assert(tunic.facts.stats.armor == 33)
''')

    def test_retribution_weapon_hover_explains_the_actual_swap_in_two_lines(self):
        setup = SETUP.replace('local ui = H.load', 'GetBuildInfo = function() return "Forever", "71037" end\nlocal ui = H.load')
        self.lua_run(r'''
level = 55
UIParent:SetSize(900, 500)
addon:GetAccountDB().profile.window.width, addon:GetAccountDB().profile.window.height = 900, 500
GetInventoryItemID = function(_, slot) if slot == 16 then return 9372 end end
GetInventoryItemLink = function(_, slot) if slot == 16 then return "item:9372" end end
H.itemNames[9372] = "Sul'thraze the Lasher"
H.usePaladinReferenceTalents("Retribution")
addon:SetSelectedLevelingLevel(level, true)
addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {["Main Hand"] = true}
ui:Open(); H.settle()
local owned = ui.currentOwned
local guide = rating:GetGuideContext("Paladin", "Retribution", "LEVELING", level, "Human", "Alliance")
local player = addon:GetTooltipPlayerContext()
local expected = {[280056]="Flameslash Crescent", [18324]="Waveslicer", [276732]="Alcaz Willcrusher"}
local font = UIParent:CreateFontString(nil, "OVERLAY", "GameTooltipText")
local function wrappedLines(lines)
    local total = 0
    for index = 2, #lines do
        local line = ""
        total = total + 1
        for word in lines[index]:gmatch("%S+") do
            local nextLine = line == "" and word or (line .. " " .. word)
            font:SetText(nextLine)
            if line ~= "" and font:GetStringWidth() > 245 then
                total, line = total + 1, word
            else line = nextLine end
        end
    end
    return total
end
for id, name in pairs(expected) do
    local item = assert(rating:GetPublishedFacts(tostring(id)))
    local row = {item_id=id, item_link="item:" .. id, class="Paladin", spec="Retribution", name=name, slot="Two Hand",
        stat_rank=rating:GetPackedGuideEntry(guide, "Two Hand", tostring(id))}
    row.targetVerdict = rating:GetGuideTargetVerdict(row, guide, player, owned, true)
    local swap = assert(row.targetVerdict.swap)
    local reference = next(swap.replacements or {}) and swap.replacements[1].name
    assert(reference == "Sul'thraze the Lasher", reference)
    assert(not swap.blocker)
    local owner = CreateFrame("Button", nil, UIParent)
    IsAltKeyDown = function() return false end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:AddLine("Blizzard's weapon tooltip")
    ui:AddLevelingGearTooltip(GameTooltip, row, "leveling")
    assert(#GameTooltip.lines <= 3 and GameTooltip.lines[1] == "Blizzard's weapon tooltip")
    local shown = table.concat(GameTooltip.lines, "\n")
    assert(shown:find(reference, 1, true), shown)
    for _, internal in ipairs({"Unpriced", "score points", "1294430", "description unavailable"}) do
        assert(not shown:find(internal, 1, true), shown)
    end
    if id == 280056 then assert(shown:find("Hit",1,true) or shown:find("Trolls",1,true),shown) end
    IsAltKeyDown = function() return true end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    ui:AddLevelingGearTooltip(GameTooltip, row, "leveling")
    assert(table.concat(GameTooltip.lines, "\n"):find("score points", 1, true))
    if swap.conditional then
        local bucket = ui.renderModel.targetQuery.slots["Two Hand"]
        assert(not (bucket and bucket.positions[tostring(id)]), "Unconfirmed swap in default targets")
    end
    ui:SetFilter("search", name); H.settle()
    local icon
    for _, frame in ipairs(ui.activeRenderFrames) do
        if frame.boundData and frame.boundData.item_id == id then icon = frame.iconButton; break end
    end
    assert(icon and icon:IsVisible(), name)
    IsAltKeyDown = function() return false end
    icon:GetScript("OnEnter")(icon)
    assert(GameTooltip:GetOwner() == icon and #GameTooltip.lines <= 3 and wrappedLines(GameTooltip.lines) <= 4,
        table.concat(GameTooltip.lines, "\n"))
    assert(table.concat(GameTooltip.lines, "\n"):find(reference, 1, true))
    IsAltKeyDown = function() return true end
    H.fireEvent("MODIFIER_STATE_CHANGED", "LALT", 1)
    assert(table.concat(GameTooltip.lines, "\n"):find("score points", 1, true))
    icon:GetScript("OnLeave")(icon)
    icon:Click(); H.settle()
    assert(ui.selectedItemData and ui.selectedItemData.item_id == id)
    local detail = ""
    for _, block in ipairs(ui.detailsWidgetPools.text or {}) do
        if block:IsVisible() then detail = detail .. block.body:GetText() end
    end
    assert(detail:find(reference, 1, true) and not detail:find("score points", 1, true), detail)
    assert(ui:OpenSlotComparison(ui.selectedItemData, "leveling", true)); H.settle()
    assert(ui.slotComparison.reference.name == reference and ui.slotComparison.reference.item_id == 9372,
        ui:GetComparisonReferenceLabel(ui.slotComparison.reference))
    ui:CloseSlotComparison(); H.settle()
    assert(ui.selectedItemData and ui.selectedItemData.item_id == id)
    ui:SetInspectorVisible(false); H.settle()
    ui:SetFilter("search", ""); H.settle()
end

local bagged
C_Container = {
    GetContainerNumSlots = function(bag) return bag == 0 and 1 or 0 end,
    GetContainerItemID = function() return bagged end,
    GetContainerItemLink = function() return "item:" .. bagged end,
}
function GameTooltip:GetPrimaryTooltipInfo() return {getterName = "GetBagItem", getterArgs = {0, 1}} end
local bagButton = CreateFrame("Button", nil, UIParent)
for id, name in pairs(expected) do
    bagged = id
    GameTooltip:Hide()
    ui:Invalidate("ownership", "bagged weapon")
    ui:GetOwnedSnapshot()
    IsAltKeyDown = function() return false end
    GameTooltip:SetOwner(bagButton, "ANCHOR_RIGHT")
    GameTooltip:SetHyperlink("item:" .. id)
    GameTooltip:Show()
    H.settle()
    local tip = table.concat(GameTooltip.lines, "\n")
    assert(tip:find("Retribution — ", 1, true), tip)
    assert(tip:find("Sul'thraze the Lasher", 1, true), tip)
    assert(not tip:find("score points", 1, true) and not tip:find("Unpriced", 1, true), tip)
    if id == 280056 then assert(tip:find("Gains 1.5% Hit and 1% Crit", 1, true), tip) end
    if id == 18324 then assert(tip:find("Nature damage on hit", 1, true), tip) end
    if id == 276732 then assert(tip:find("Downgrade", 1, true), tip) end
end
''', setup=setup)

    def test_recovered_dungeon_gear_reaches_leveling_and_pre_raid_at_equip_level(self):
        self.lua_run(r'''
local function onPage(spec, mode, level, slot, id)
    local context = assert(rating:GetGuideContext("Paladin", spec, mode, level, "Human", "Alliance"))
    local data = rating:GetPackedGuide(context)[slot]
    local page = rating:GetGuideTargetPage(data, level)
    for index = 1, page and page.count or 0 do
        if data.indices.keys[page.at(index)] == tostring(id) then return true end
    end
    return false
end
local shield = assert(rating:GetTooltipItem(274652, "item:274652").facts)
assert(shield.stats.armor == 1676 and shield.stats.block_value == 27 and shield.stats.spell_power == 14)
assert(not onPage("Protection", "LEVELING", 42, "Off Hand", 274652))
assert(onPage("Protection", "LEVELING", 43, "Off Hand", 274652))
assert(onPage("Protection", "PR", 60, "Off Hand", 274652))
local _, options = addon:GetGuideRouteTransitions(274652)
local source = options[1].source
assert(source.entity_name == "Hydromancer Velratha" and source.zone == "Zul'Farrak")
assert(onPage("Holy", "LEVELING", 28, "Feet", 286987))
''')

    def test_cold_window_never_asks_for_full_pools_or_hidden_facets(self):
        self.lua_run(r'''
local queried = 0
local capture = addon.GetFilterAvailabilitySnapshot
function addon:GetFilterAvailabilitySnapshot(...)
    queried = queried + 1
    return capture(self, ...)
end
function addon:GetLevelingRows() error("Cold Guide must read the shipped pages") end
function rating:GetGuidePlacement() error("Cold Guide must use indexed rank lookups") end
function rating:VisitPackedGuideOrdinals() error("Filter menus must read target pages") end
addon:InitUIEvents()
ui:PrepareRememberedWorkspace()
ui:Open()
for tick = 1, 3 do H.now = H.now + 1/60; H.tick() end
local function rows()
    local result = 0
    for _, frame in ipairs(ui.activeRenderFrames or {}) do
        if frame:IsShown() and frame.boundData and frame.boundData.stat_rank then result = result + 1 end
    end
    return result
end
assert(rows() > 0 and queried == 0)
H.settle()
assert(ui.renderModel.rowCount > #ui.renderModel.entries and #ui.renderModel.entries < 100)
assert(#ui.activeRenderFrames <= 24, "Only the visible page should own row frames")
ui:VisitListEntries(ui.renderModel, 0, math.huge, function(entry)
    local row = entry.data
    if row then
        assert(addon:IsGuideTargetRoute(row.matched_access_option))
        assert(row.targetVerdict.kind == "upgrade" or row.targetVerdict.kind == "utility"
            or row.targetVerdict.kind == "situational")
    end
end)
ui.contentScroll:SetVerticalScroll(1200)
H.settle()
local position = ui:CaptureNavigationState()
assert(position.anchorKey and position.anchorSpan)
local serial = ui.renderModelSerial
local refreshes = ui:GetPerformanceStats().executedRefreshes
local frame = addon.uiEventFrame
for _ = 1, 12 do
    frame:GetScript("OnEvent")(frame, "BAG_UPDATE_DELAYED")
    frame:GetScript("OnEvent")(frame, "QUEST_LOG_UPDATE")
end
H.settle()
H.now = H.now + 60
H.tick()
assert(ui.renderModelSerial == serial and ui:GetPerformanceStats().executedRefreshes == refreshes)
assert(queried == 0)
ui:SetFilterDrawerOpen(true)
H.settle()
assert(queried == 1 and #(ui:GetFilterAvailabilitySnapshot().sourceTypes or {}) > 0)
for _, source in ipairs(ui:GetFilterAvailabilitySnapshot().sourceTypes) do assert(source ~= "trade") end
assert(ui.renderModelSerial == serial)
ui:SetFilterDrawerOpen(false)
worn = 7719
frame:GetScript("OnEvent")(frame, "PLAYER_EQUIPMENT_CHANGED", 1)
H.settle()
assert(ui.renderModelSerial == serial and ui.updateGuideButton:IsVisible())
applyListUpdate()
assert(ui.renderModelSerial > serial and ui:CaptureNavigationState().anchorKey == position.anchorKey)
assert(ui:CaptureNavigationState().anchorOffset == position.anchorOffset)
''')

    def test_cold_native_tooltip_and_exact_search_share_the_same_helm_rank(self):
        self.lua_run(r'''
local referencePlacement = rating.GetGuidePlacement
function rating:GetGuidePlacement() error("A native hover must read its indexed rank") end
local tip = GameTooltip
H.modifiers.alt = true
tip:SetOwner(UIParent)
tip:SetHyperlink("item:7719")
tip:Show()
local cold = table.concat(tip.lines or {}, "\n")
assert(cold:find("Slight upgrade", 1, true) and cold:find("Gothic Plate Helmet of the Gorilla", 1, true), cold)
H.settle()
local lines = table.concat(tip.lines or {}, "\n")
assert(lines:find("Slight upgrade", 1, true) and lines:find("+2.1 pts vs Gothic Plate Helmet of the Gorilla", 1, true), lines)

local filters = ui:GetFilters("Gear Guide")
filters.slots, filters.search = { Head = true }, "Gothic Plate Helmet of the Gorilla"
ui:Open()
H.settle()
local candidate
local key = "10090:0:0:0:1:12723"
ui:VisitListEntries(ui.renderModel, 0, math.huge, function(entry)
    if entry.data and entry.data.stat_identity == key then candidate = entry.data end
end)
local guide = rating:GetGuideContext("Paladin", "Retribution", "LEVELING", 49, "Human", "Alliance")
local expected = assert(referencePlacement(rating, guide, "Head").byVariant[key])
assert(candidate and candidate.stat_rank.rank == expected.rank and candidate.stat_rank.total == expected.total)
''')

    def test_my_gear_binds_both_level_51_outfits_with_finished_advice(self):
        for spec in ("Retribution", "Protection"):
            with self.subTest(spec=spec):
                self.lua_run("local spec = " + repr(spec) + "\n" + r'''
level = 51
local retribution = {10090, 276740, 9476, 0, 276739, 274653, 11882, 275003, 270102, 9640,
    270081, 11118, 280766, 17774, 274612, 7723}
local protection = {14919, 7673, 9476, 0, 10203, 276742, 10133, 10131, 14914, 9410,
    274642, 11118, 280766, 17774, 276737, 17705, 1203}
local outfit = spec == "Retribution" and retribution or protection
local bonuses = {[10090]=12723, [9640]=13023, [11118]=13099, [14919]=12754, [10203]=12754, [10133]=12754,
    [10131]=12754, [14914]=12752, [9410]=13182}
GetInventoryItemID = function(_, slot) return outfit[slot] ~= 0 and outfit[slot] or nil end
GetInventoryItemLink = function(unit, slot)
    local id = GetInventoryItemID(unit, slot)
    if id then return "item:" .. id .. (bonuses[id] and ("::::::::51:1486::1:1:" .. bonuses[id]) or "") end
end
local oldInstant = GetItemInfoInstant
GetItemInfoInstant = function(value)
    local id = tonumber(value) or tonumber(tostring(value):match("item:(%d+)"))
    if id == 7723 then return id, "Weapon", "Mace", "INVTYPE_2HWEAPON", nil, 2, 5 end
    if id == 1203 then return id, "Armor", "Shield", "INVTYPE_SHIELD", nil, 4, 6 end
    return oldInstant(value)
end
addon.DetectPlayerSpec = function() return spec end
addon:RefreshTooltipPlayerContext()
selection.spec = spec
addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {Head = true}
local calls = 0
local build = rating.GetGearScore
function rating:GetGearScore(...)
    calls = calls + 1
    return build(self, ...)
end
function rating:GetPlacement() error("My Gear must not build a full slot pool") end
function rating:GetGuidePlacement() error("My Gear must use indexed ranks") end
addon:InitUIEvents()
ui:Open(); H.settle()
ui:SetTab("My Gear")
H.now = H.now + 1/60; H.tick()
local gear = ui.gearFrame
assert(gear:IsVisible() and gear.slots.Head.gearData.item_id == outfit[1])
assert(gear.slots.MainHand.gearData.item_id == outfit[16] and gear.ratingRequest.ready and calls == 1)
assert((gear.slots.OffHand.gearData.disabledReason ~= nil) == (spec == "Retribution"))
H.settle()
assert(gear.score and gear.score.percent and gear.slots.Head.gearData.stat_rank.rank)
local completed, count = gear.ratingRequest, calls
ui:SetTab("Gear Guide"); H.settle()
ui:SetTab("My Gear"); H.settle()
assert(gear.ratingRequest == completed and calls == count)
local frame = addon.uiEventFrame
outfit[1], outfit[2] = 7719, 7722
frame:GetScript("OnEvent")(frame, "PLAYER_EQUIPMENT_CHANGED", 1)
H.settle()
assert(gear.ratingRequest ~= completed and gear.slots.Head.gearData.item_id == 7719)
local current = gear.ratingRequest
ui:SetSpec(spec == "Protection" and "Retribution" or "Protection")
H.tick()
local abandoned = gear.ratingRequest
assert(abandoned ~= current and abandoned.ready)
ui:SetSpec(spec); H.settle()
assert(gear.ratingRequest == current and gear.slots.Head.gearData.stat_rank.spec == spec)
''')

    def test_my_gear_reuses_verified_equipped_verdicts_and_bank_swaps_after_reload(self):
        self.lua_run(r'''
level, worn = 55, 7673
GetBuildInfo = function() return "Forever", "71037" end
GetInventoryItemID = function(_, slot) return slot == 2 and worn or slot == 1 and 6686 or nil end
GetInventoryItemLink = function(_, slot)
    local id = GetInventoryItemID(_, slot)
    return id and "item:" .. id
end
H.usePaladinReferenceTalents("Protection")
local function setup(a)
    a.DetectPlayerSpec = function() return "Protection" end
    a:RefreshTooltipPlayerContext()
    a:SetSelection("Paladin", "Protection", "LEVELING", "Equipped")
    a:SetSelectedLevelingLevel(level, true)
end
setup(addon)
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:9479"}, {"20:1"}
ui:PrepareRememberedWorkspace()
local old = assert(ui.gearFrame.slots.Neck.gearData.gearAdvice.today)
assert(old == "Keep equipped")
local head = ui.gearFrame.slots.Head.gearData
assert(head.gearAdvice.today == "Get Embrace of the Lycan from bank", head.gearAdvice.today)
local gain = head.gearAction.delta
local function reload()
    BigBiSList, BigBiSListData = nil, nil
    ui = H.load("forever", true)
    addon, rating = BigBiSList, BigBiSList.ForeverGearRating
    setup(addon)
end
reload()
local compute, calls = rating.GetLiveLevelingSwap, 0
function rating:GetLiveLevelingSwap(...)
    calls = calls + 1
    return compute(self, ...)
end
ui:PrepareRememberedWorkspace(); ui:Open()
assert(ui.gearFrame.slots.Neck.gearData.gearAdvice.today == old and calls == 0)
local restored = ui.gearFrame.slots.Head.gearData.gearAction
assert(restored.delta == gain and restored.incoming[1].state == "bank")
assert(restored.replacements[1].item_link == "item:6686" and rating:GetSwapExplanation(restored, true))
reload()
worn = 10711
compute = rating.GetLiveLevelingSwap
function rating:GetLiveLevelingSwap(...)
    calls = calls + 1
    return compute(self, ...)
end
ui:PrepareRememberedWorkspace(); ui:Open()
assert(ui.gearFrame.slots.Neck.gearData.item_id == 10711 and calls == 2,
    "A different loadout must recompute the owned swap against the new stats")
''')

    def test_open_and_reopen_keep_the_prepared_level_preview(self):
        self.lua_run(r'''
addon:SetSelectedLevelingLevel(55, true)
ui:PrepareRememberedWorkspace()
local model = assert(ui.renderModel)
assert(model.guideContext.level == 55)
for _ = 1, 2 do
    ui:Open()
    assert(ui.renderModel == model and addon:GetSelectedLevelingLevel() == 55)
    H.settle()
    assert(ui.renderModel == model)
    ui:Close()
end
''')

    def test_cyclopean_band_and_exact_name_lookup_for_the_equipped_id(self):
        self.lua_run(r'''
level = 51
addon:RefreshTooltipPlayerContext()
local links = {[3] = "item:9476::::::::51:1486::1::1:28:5255",
    [11] = "item:274642", [12] = "item:11118::::::::51:1486::1:1:13099", [16] = "item:7723"}
GetInventoryItemLink = function(_, slot) return links[slot] end
GetInventoryItemID = function(_, slot) return links[slot] and tonumber(links[slot]:match("item:(%d+)")) end
ui:GetFilters("Gear Guide").slots = {Ring = true}
selection.spec = "Protection"
addon:SetSelectedLevelingLevel(51, true)
ui:Open(); H.settle()
local query = ui.renderModel.targetQuery
local ring = query.slots.Ring.rows[query.slots.Ring.positions["11824"]]
assert(ring and ring.targetVerdict.gain > 0 and ring.matched_access_option.source.entity_id == 9030)
assert(ring.matched_access_option.zone == "Blackrock Depths")
for _, exact in ipairs({{"Big Bad Pauldrons", "Shoulder", 9476}, {"Mograine's Might", "Two Hand", 7723}}) do
    ui:SetFilter("search", exact[1]); H.settle()
    local found = ui.renderModel.targetQuery.slots[exact[2]].rows[1]
    assert(found.item_id == exact[3] and found.item_link == links[exact[3] == 9476 and 3 or 16])
end
''')

    def test_selected_gear_slot_names_the_item_and_next_action(self):
        self.lua_run(r'''
level, worn = 51, 6686
addon:RefreshTooltipPlayerContext()
addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {Head = true}
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:9479"}, {"bank:1"}
local bag
C_Container = {
    GetContainerNumSlots = function(id) return id == 0 and bag and 1 or 0 end,
    GetContainerItemID = function() return bag end,
    GetContainerItemLink = function() return bag and ("item:" .. bag) end,
}
addon:InitUIEvents()
ui:Open(); H.settle()
ui:SetTab("My Gear"); H.settle()
ui.gearFrame.slots.Head:Click(); H.settle()
local summary = ui.gearFrame.summary
assert(summary.rating:GetText():find("Get Embrace of the Lycan from bank", 1, true))
local events = addon.uiEventFrame
bank.links, bag = {}, 9479
events:GetScript("OnEvent")(events, "BAG_UPDATE_DELAYED"); H.settle()
assert(summary.rating:GetText():find("Equip Embrace of the Lycan", 1, true))
bag = nil
events:GetScript("OnEvent")(events, "BAG_UPDATE_DELAYED"); H.settle()
assert(summary.rating:GetText():find("Embrace of the Lycan · Drops from Chief Ukorz Sandscalp", 1, true))
''')

    def test_open_equipped_details_follow_the_selected_slot_and_finished_rating(self):
        for width, height in ((900, 500), (1020, 790)):
            for density in ("compact", "comfortable"):
                with self.subTest(size=(width, height), density=density):
                    setup = SETUP.replace('local ui = H.load', 'GetBuildInfo = function() return "Forever", "71037" end\nlocal ui = H.load')
                    self.lua_run(f'local width, height, density = {width}, {height}, "{density}"\n' + r'''
level = 55
addon.DetectPlayerSpec = function() return "Protection" end
H.usePaladinReferenceTalents("Protection")
local vice = assert(rating:GetPublishedFacts("9640:0:0:0:1:13027"))
local templar = assert(rating:GetPublishedFacts("10165:0:0:0:1:12754"))
local slots = {[2]=7673, [10]=vice.id}
H.itemNames[7673], H.itemNames[vice.id] = "Talvash's Enhancing Necklace", vice.name
GetInventoryItemID = function(_, slot) return slots[slot] end
GetInventoryItemLink = function(_, slot) return slot == 10 and vice.variant_link or (slots[slot] and "item:" .. slots[slot]) end
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {templar.variant_link}, {"20:1"}
addon:RefreshTooltipPlayerContext()
addon:SetSelection("Paladin", "Protection", "LEVELING", "Equipped")
addon:SetSelectedLevelingLevel(level, true)
local window = addon:GetAccountDB().profile.window
window.width, window.height, window.density = width, height, density
UIParent:SetSize(width, height)
addon:InitUIEvents(); ui:Open()
for i=1,3 do
    if ui.gearFrame and ui.gearFrame.slots.Neck.gearData then break end
    H.now = H.now + 1/60; H.tick()
end
local gear = assert(ui.gearFrame)
local neck, hands = gear.slots.Neck, gear.slots.Hands
local function visibleDetails()
    local lines = {}
    for _, frame in ipairs({ui.detailsContent:GetChildren()}) do
        if frame:IsVisible() then
            for _, label in ipairs({frame:GetRegions()}) do
                if label.GetText and label:IsVisible() and label:GetText() then lines[#lines+1]=label:GetText() end
            end
        end
    end
    return table.concat(lines, "\n")
end
local function has(text, part) assert(text:find(part,1,true), text .. " missing " .. part) end
local function lacks(text, part) assert(not text:find(part,1,true), text) end
neck:Click(); gear.summary.detailsButton:Click()
assert(neck.gearData.gearRated and ui.selectedItemData == neck.gearData)
local why = visibleDetails()
has(why,"Keep equipped"); has(why,"Best neck you own for Protection.")
has(why,"Level 55 Guide · Tied for 9th of 1086"); has(why,"67% of the top item's score")
lacks(why,"Pre-Raid"); lacks(why,"Not ranked"); lacks(why,"How to get it")
has(gear.summary.rating:GetText(),"Level 55 Guide · Tied for 9th")
has(neck.label.displayedText, "Keep"); assert(not neck.label.isTruncated)
has(gear.preview.score:GetText(), "% of best known outfit")
local builds = ui:GetPerformanceStats().detailsBuilds
local prepared = gear.ratingRequest
H.fireEvent("PLAYER_EQUIPMENT_CHANGED", 2)
H.fireEvent("BAG_UPDATE_DELAYED")
for i=1,30 do
    H.now = H.now + 1/60; H.tick()
    assert(visibleDetails() == why and ui.selectedItemData == neck.gearData)
    assert(ui:GetPerformanceStats().detailsBuilds == builds)
end
local getInstant = GetItemInfoInstant
GetItemInfoInstant = function(item)
    if item == 117 or item == "item:117" then return 117, "Consumable", "Food", "" end
    return getInstant(item)
end
H.itemNames[117] = "Tough Jerky"
C_Container = {GetContainerNumSlots = function(bag) return bag == 0 and 1 or 0 end,
    GetContainerItemID = function() return 117 end, GetContainerItemLink = function() return "item:117" end}
H.fireEvent("BAG_UPDATE_DELAYED"); H.settle()
assert(ui.currentOwned[117] == "bag" and gear.ratingRequest == prepared)
assert(ui:GetPerformanceStats().detailsBuilds == builds and visibleDetails() == why)
ui:SetInspectorVisible(false); H.settle()
hands:Click(); gear.summary.detailsButton:Click()
has(visibleDetails(),"Get Templar Gauntlets of the Defender from bank")
has(visibleDetails(),"Equipped · Vice Grips of the Defender")
has(visibleDetails(),"losing 14 Attack Power")
assert(not hands.label.isTruncated and hands.label.displayedText:match("^Get"))
-- Select another slot while the new bank snapshot is prepared off screen.
ui:SetInspectorVisible(false); H.settle()
bank.links, bank.locations = {}, {}
H.fireEvent("BAG_UPDATE_DELAYED")
hands:Click(); gear.summary.detailsButton:Click()
ui:SetInspectorVisible(false); neck:Click(); gear.summary.detailsButton:Click()
H.settle()
assert(ui.selectedItemData == neck.gearData)
has(visibleDetails(),"Best neck you own"); lacks(visibleDetails(),"Vice Grips"); lacks(visibleDetails(),"Templar")
''', setup=setup)

    def test_documented_auction_house_targets_follow_the_players_market(self):
        self.lua_run(r'''
level, worn = 51, 6686
addon:RefreshTooltipPlayerContext()
addon:SetSelectedLevelingLevel(51, true)
local region, faction = 3, "Alliance"
GetRealmName = function() return "Normal" end
GetCurrentRegion = function() return region end
UnitFactionGroup = function() return faction end
ui:GetFilters("Gear Guide").slots = {Head = true}
local score = rating.GetOwnedOpportunity
function rating:GetOwnedOpportunity(context, item, ...)
    if item.id == 287011 or item.id == 10574 or item.id == 1930 then return {delta = 4, roleDelta = 4, roleDisplaced = 10} end
    return score(self, context, item, ...)
end
ui:Open(); H.settle()
local function head() return ui.renderModel.targetQuery.slots.Head end
local function guise()
    local bucket = head().market
    return bucket and bucket.rows[bucket.positions["287011"]]
end
local row = assert(guise())
assert(not head().positions["287011"] and row.targetVerdict.gain == 4)
local shroud = assert(head().rows[head().positions["10574"]])
assert(shroud.matched_access_option.source.zone == "Razorfen Downs")
assert(not head().market.positions["10574"])
assert(ui:GetSourceNextStep(row) == "Check AH")
assert(row.matched_access_option.source.market_observation.market == "forever/normal/alliance/eu")
assert(not addon:IsGuideMarketRoute(row.matched_access_option, "forever/normal/horde/eu"))
assert(not addon:IsGuideMarketRoute({source_type = "trade", is_inferred_trade_option = true,
    source = row.matched_access_option.source}))
region = 1
ui:Invalidate("query", "market"); ui:ScheduleRefresh(); H.settle()
applyListUpdate()
assert(not guise())
ui:SetFilter("slots", {Back = true}); H.settle()
ui:SetFilter("search", "item:1930"); H.settle()
local back = ui.renderModel.targetQuery.slots.Back
local cloak = assert(back.rows[back.positions["1930"]])
assert(cloak.matched_access_option.source_type == "drop")
assert(not back.market or not back.market.positions["1930"])
local buying
for _, evaluation in ipairs(ui:GetAccessEvaluation(cloak).options) do
    if evaluation.option.source_type == "trade" then buying = evaluation.option end
end
assert(addon:IsGuideMarketRoute(buying, "forever/normal/alliance/us"))
ui:SetFilter("search", ""); H.settle()
ui:SetFilter("sourceTypes", {trade = true}); H.settle()
local market = ui.renderModel.targetQuery.slots.Back.market
assert(market and #market.rows > 0)
for _, pick in ipairs(market.rows) do assert(addon:IsGuideMarketRoute(pick.matched_access_option, "forever/normal/alliance/us")) end
ui:SetFilter("search", "item:1930"); H.settle()
local searched = ui.renderModel.targetQuery.slots.Back.rows[1]
assert(searched.item_id == 1930 and addon:IsGuideMarketRoute(searched.matched_access_option, "forever/normal/alliance/us"))
''')

    def test_packed_benchmark_and_effect_language_cover_all_profiles(self):
        self.lua_run(r'''
local checked = 0
for key, profile in pairs(BigBiSListData.stat_rank.profiles) do
    local class, spec = key:match("^([^/]+)/(.+)$")
    local preset = addon.ForeverScoring:GetPreset(class, spec, "leveling")
    local _, actor = next(preset.personas)
    local context = assert(rating:GetGuideContext(class, spec, "LEVELING", 51, actor[1], actor[2]))
    local read = assert(rating:GetPackedScoredChoices(context, "Ring"))
    local previous = math.huge
    for _ = 1, 3 do
        local choice = assert(read())
        local entry = assert(rating:GetPackedGuideEntry(context, "Ring", choice.item.key))
        assert(choice.score == entry.score and choice.score <= previous and not choice.item.excluded)
        previous = choice.score
    end
    local aoe = {effects = {"Use: Deals Fire damage to all enemies in front of you."}}
    assert(rating:GetGearPurpose(context, aoe) == "AoE")
    local proc = {effects = {"Chance on hit: Grants an extra attack."}}
    assert(rating:GetGearPurpose(context, proc) == (profile.role == "tank" and "Threat" or "DPS"))
    checked = checked + 1
end
assert(checked == 28)
''')

    def test_waiting_on_an_equipped_or_banked_item_retries_that_item(self):
        self.lua_run(r'''
level = 51
addon:RefreshTooltipPlayerContext()
addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {Head = true}
local id, name = 901077, "Late helm"
local ready, waiting, requested = false, nil, 0
local originalInfo, originalInstant = GetItemInfo, GetItemInfoInstant
local function itemID(value) return tonumber(value) or tonumber(tostring(value):match("item:(%d+)")) end
GetItemInfo = function(value)
    if itemID(value) ~= id then return originalInfo(value) end
    if ready then return name, "item:" .. id, 3, 51, 42, "Armor", "Plate", 1, "INVTYPE_HEAD", "icon" end
end
GetItemInfoInstant = function(value)
    if itemID(value) == id then return id, "Armor", "Plate", "INVTYPE_HEAD", "icon", 4, 4 end
    return originalInstant(value)
end
C_Item = {
    IsItemDataCachedByID = function(item) return item ~= id or ready end,
    GetItemStats = function(link) if itemID(link) == id and ready then return {ITEM_MOD_STRENGTH_SHORT = 1} end end,
}
Item = {CreateFromItemID = function(_, item)
    assert(item == id)
    requested = requested + 1
    return {ContinueOnItemLoad = function(_, callback) waiting = callback end}
end}
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:" .. id}, {"bank:1"}
addon:InitUIEvents()
ui:Open(); H.settle()
local function head() return ui.renderModel.targetQuery.slots.Head end
assert(requested == 1 and head().pending[id] and head().comparisonDetail)
assert(not head().positions["9479"], "An item compared against unreadable bank gear showed as an upgrade")
ready = true; waiting(); H.settle()
applyListUpdate()
assert(not head().pending and head().positions["9479"])
bank.links, worn, id, ready = {}, 901078, 901078, false
local events = addon.uiEventFrame
events:GetScript("OnEvent")(events, "PLAYER_EQUIPMENT_CHANGED", 1); H.settle()
applyListUpdate()
assert(requested == 2 and head().pending[id] and head().comparisonDetail:find("Can't compare ", 1, true))
ready = true; waiting(); H.settle()
applyListUpdate()
assert(not head().pending and head().positions["9479"])
''')

    def test_level_51_targets_and_exact_lookup_use_best_owned_helm(self):
        self.lua_run(r'''
level = 51
addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
local bag
C_Container = {
    GetContainerNumSlots = function(id) return id == 0 and bag and 1 or 0 end,
    GetContainerItemID = function(id) return id == 0 and bag end,
    GetContainerItemLink = function(id) return id == 0 and bag and "item:" .. bag end,
}
addon:InitUIEvents()
ui:Open(); H.settle()
local function head() return assert(ui.renderModel.targetQuery.slots.Head) end
local function find(id)
    local bucket = head()
    return bucket.rows[bucket.positions[tostring(id)]]
end
local function advice(row)
    return table.concat(rating:LevelingPresentationLines(ui:GetLevelingGearView(row, "leveling")), "\n")
end
local function lookup(value)
    ui:SetFilter("search", value); H.settle()
end
local function bagsChanged()
    local f = addon.uiEventFrame
    f:GetScript("OnEvent")(f, "BAG_UPDATE_DELAYED"); H.settle()
    applyListUpdate()
end
assert(find(9479) and #head().rows < 20)
for _, row in ipairs(head().rows) do assert(addon:IsGuideTargetRoute(row.matched_access_option)) end
assert(not find(6686) and not find(10574))
ui:SetFilter("zones", {["Scarlet Monastery"] = true}); H.settle()
local herod = assert(find(7719))
assert(herod.stat_rank.rank and math.abs(herod.targetVerdict.gain - 2.1) < 0.001)
assert(advice(herod):find("+2.1 pts vs Gothic Plate Helmet of the Gorilla", 1, true))
ui:SetFilter("zones", {}); H.settle()
lookup("Tusken Helm")
assert(#head().rows == 1 and advice(find(6686)):find("-6.5 pts vs Gothic Plate Helmet of the Gorilla", 1, true))
lookup("Guise of Battle")
assert(find(287011).lookupReason:find("Auction House", 1, true))
lookup(gothic)
assert(head().rows[1].stat_identity == "10090:0:0:0:1:12723")
lookup("")
bag = 9479; bagsChanged()
assert(not find(7719) and not find(9479), "The better bag helm is already owned")
lookup("item:7719")
assert(advice(find(7719)):find("pts vs Embrace of the Lycan", 1, true))
lookup("item:9479")
local winner = advice(find(9479))
assert(winner:find("Best you own for this slot", 1, true) and not winner:find("pts vs", 1, true), winner)
lookup("item:7719")
bag = nil
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:9479"}, {"bank:1"}
bagsChanged()
assert(advice(find(7719)):find("pts vs Embrace of the Lycan", 1, true))
assert(find(7719).targetVerdict.swap.replacements[1].state == "bank")
lookup("")
assert(not find(7719))
ui:SetFilter("zones", {["Scarlet Monastery"] = true}); H.settle()
assert(not find(7719))
ui:GetViewState("Gear Guide").groupBy = "activity"
lookup("Tusken Helm")
assert(ui.renderModel.targetQuery.exact and advice(find(6686)):find("pts vs Embrace of the Lycan", 1, true))
''')

    def test_random_drop_is_one_target_and_wishlist_keeps_its_roll(self):
        self.lua_run(r'''
level, worn = 51, 6686
addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
-- Give two known exact rolls the same named drop route. Both beat the worn
-- Tusken Helm. The full reference scorer and the personal comparison stay live.
local keys = {}
local all = BigBiSListData.guide_index.slots.Head
local guide = rating:GetGuideContext("Paladin", "Retribution", "LEVELING", 51, "Human", "Alliance")
for ordinal, key in ipairs(all.keys) do
    local item = guide.catalog.items[key]
    if item.id == 10090 and (item.name:find("of the Gorilla", 1, true) or item.name:find("of the Bear", 1, true)) then
        keys[#keys+1] = ordinal
    end
end
assert(#keys == 2)
function rating:GetGuideTargetPage() return {count = #keys, at = function(i) return keys[i] end} end
local get = addon.GetPackedGuideRow
function addon:GetPackedGuideRow(ctx, slot, ordinal, filters, match, at)
    if filters._guideTarget then
        local row = get(self, ctx, slot, ordinal, {}, false, at)
        local herod = get(self, ctx, slot, all.lookup["7719"], filters, true, at)
        row.acquisition_display, row.matched_access_option = herod.acquisition_display, herod.matched_access_option
        return row
    end
    return get(self, ctx, slot, ordinal, filters, match, at)
end
ui:Open(); H.settle()
local b = ui.renderModel.targetQuery.slots.Head
assert(#b.rows == 1)
local row = b.rows[1]
assert(row.targetRoll and row.name:find(row.targetRoll, 1, true) and row.targetVerdict.gain > 0)
local other = all.keys[keys[1]] == row.stat_identity and all.keys[keys[2]] or all.keys[keys[1]]
ui:AddWishlist(row.item_id, row)
assert(ui:IsWishlisted(row) and not ui:IsWishlisted({item_id=10090, variant_id=other}))
ui:SetFilter("search", row.item_link); H.settle()
local exact = ui.renderModel.targetQuery.slots.Head.rows[1]
assert(exact.stat_identity == row.stat_identity and exact.stat_rank.rank == row.stat_rank.rank and ui:IsWishlisted(exact))
''')

    def test_empty_results_tiny_gains_and_reviewed_utility_loss(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
local helm = BigBiSListData.guide_index.slots.Head.lookup["6686"]
function rating:GetGuideTargetPage() return {count = 1, at = function() return helm end} end
ui:Open(); H.settle()
local model, query = ui.renderModel, ui.renderModel.targetQuery
assert(#query.slots.Head.rows == 0 and not query.unknown)
assert(model.entries[2].text:find("No confirmed Head upgrade at level 51", 1, true))
assert(model.entries[2].text:find("Gothic Plate Helmet of the Gorilla", 1, true))
local guide, owned, player = model.guideContext, ui.currentOwned, addon:GetTooltipPlayerContext()
local row = addon:GetPackedGuideRow(guide, "Head", helm, {}, false, 51)
local swap = {delta = 0.002}
rating.GetOwnedOpportunity = function() return swap end
local function verdict() return rating:GetGuideTargetVerdict(row, guide, player, owned) end
assert(verdict().kind == "upgrade" and verdict().gain == 0.002)
ui.lastUnfilteredGuide = nil
local function coldSlotTarget() return ui:FindBestGearGuideTarget(guide, {"Head"}, player, owned, function() end) end
assert(not coldSlotTarget(), "My Gear recommended a trip for a rounded-zero gain")
swap = {delta = 5}; assert(coldSlotTarget().item_id == 6686)
swap = {delta = 0}; assert(verdict().kind == "hidden")
swap = {status = "loading", blocker = {name = "Bank helm"}, pending = {[901001] = true}}
local waiting = verdict()
assert(waiting.kind == "loading" and waiting.pending[901001] and waiting.detail == "Can't compare Bank helm yet")
swap = {delta = 0.3, conditional = true}
assert(verdict().kind == "situational" and not verdict().gain)
local index = BigBiSListData.guide_index.slots.Trinket.lookup["744"]
row = addon:GetPackedGuideRow(guide, "Trinket", index, {}, false, 51)
swap = {delta = -4, slot = "Trinket", replacements = {{name = "Owned trinket"}}, definition = {label = "Trinket"}}
row.targetVerdict = verdict()
assert(row.targetVerdict.kind == "utility" and not row.targetVerdict.gain)
local view = ui:GetLevelingGearView(row, "leveling")
assert(view.today == "AoE" and view.comparisonDetail:find("On-use fire damage", 1, true))
assert(view.evidence:find("-4.0 pts vs Owned trinket", 1, true))
''')

    def test_dungeon_keeps_an_earlier_pick_and_hides_a_weaker_later_one(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
addon:SetSelectedLevelingLevel(51, true)
ui:GetFilters("Gear Guide").slots = {Head = true}
local examples = {[9479]={gain=12, gate=43}, [7719]={gain=11, gate=35}, [10763]={gain=11, gate=45}}
local ids = {9479, 7719, 10763}
local indices = BigBiSListData.guide_index.slots.Head.lookup
function rating:GetGuideTargetPage() return {count=#ids, at=function(i) return indices[tostring(ids[i])] end} end
local original, verdict = addon.GetPackedGuideRow, rating.GetGuideTargetVerdict
function addon:GetPackedGuideRow(...)
    local row = original(self, ...)
    local example = row and examples[row.item_id]
    if example then
        local option = row.matched_access_option
        row.acquisition_display.activity_zone = "Same dungeon"
        row.acquisition_display.testGate = example.gate
        assert(option.source_type == "drop")
    end
    return row
end
local gate = addon.GetLevelingSourceGate
function addon:GetLevelingSourceGate(display)
    if display and display.testGate then return display.testGate end
    return gate(self, display)
end
function rating:GetGuideTargetVerdict(row, ...)
    local value = verdict(self, row, ...)
    local example = examples[row.item_id]
    if example then value.gain, value.kind, value.purpose, value.meaningful = example.gain, "upgrade", nil, true end
    return value
end
ui:Open(); H.settle()
local bucket = ui.renderModel.targetQuery.slots.Head
assert(bucket.positions["9479"] and bucket.positions["7719"] and not bucket.positions["10763"])
assert(bucket.exclusions["10763"]:find("Embrace of the Lycan", 1, true))
examples[10763].gain = 12
ui:Invalidate("query", "equal dungeon rewards"); ui:Refresh(); H.settle()
assert(ui.renderModel.targetQuery.slots.Head.exclusions["10763"] == "Same gain from this activity · Embrace of the Lycan")
''')

    def test_activity_counts_and_sorts_share_recommendations(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
ui:GetViewState("Gear Guide").groupBy = "activity"
ui:Open(); H.settle()
local function overview(sort)
    ui:SelectSort(sort); H.settle()
    local actions = {}
    for _, e in ipairs(ui.renderModel.entries) do
        if e.activityName then
            assert(e.activityName ~= "Razorfen Kraul" and e.activityName ~= "Trade / Auction House")
            actions[#actions + 1] = e
        end
    end
    local confirmed = 0
    for _, action in ipairs(actions) do
        if action.detail:find("upgrade option", 1, true) then confirmed = confirmed + 1
        else assert(action.detail:find("situational", 1, true) or action.detail:find("Stats unavailable", 1, true)
            or action.detail:find("Check ", 1, true) or action.detail:find("Waiting for ", 1, true)) end
    end
    local expected = 0
    for _, total in pairs(ui.renderModel.targetQuery.activities.batch.totals) do
        if total.upgrades > 0 then expected = expected + 1 end
    end
    assert(confirmed == expected and confirmed > 0)
    return actions
end
local largest = overview("most_loot")[1]
local byName = ui.renderModel.targetQuery.activities.byName
for _, activity in pairs(byName) do assert(activity.itemCount <= byName[largest.activityName].itemCount) end
local best = overview("best_upgrade")[1]
assert(best.title == "Zul'Farrak" and best.detail:find("Embrace of the Lycan (+15.1 pts)", 1, true))
assert(overview("most_upgrades")[1].title == "Zul'Farrak")
ui:SetFilter("slots", {}); H.settle()
local data = ui.renderModel.targetQuery.activities
local oneLarge, smaller
for _, a in ipairs(data.ordered) do
    local x = data.batch.totals[a]
    for _, b in ipairs(data.ordered) do
        local y = data.batch.totals[b]
        if x.bestGain > y.bestGain and y.upgrades > x.upgrades then oneLarge, smaller = a.name, b.name; break end
    end
    if oneLarge then break end
end
assert(oneLarge and smaller)
local function position(sort, name)
    ui:SelectSort(sort); H.settle()
    for i, e in ipairs(ui.renderModel.entries) do if e.activityName == name then return i end end
end
assert(position("best_upgrade", oneLarge) < position("best_upgrade", smaller))
assert(position("most_upgrades", smaller) < position("most_upgrades", oneLarge))
''')

    def test_preview_sources_and_conditional_outcomes(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
ui:Open(); H.settle()
local function herod()
    local b = ui.renderModel.targetQuery.slots.Head
    return assert(b.rows[b.positions["7719"]])
end
ui:SetLevelingLevel(55); H.settle()
ui:SetFilter("search", "item:7719"); H.settle()
local row = herod()
local text = table.concat(rating:LevelingPresentationLines(ui:GetLevelingGearView(row, "leveling")), "\n")
assert(row.targetVerdict.swap.forecast.level == 55 and text:find("Estimated at Level 55", 1, true))
assert(not text:find("Can equip at Level 55", 1, true))
ui:SetLevelingLevel(45); H.settle()
assert(herod().targetVerdict.level == 51 and herod().stat_rank.level == 45)
ui:SetFilter("search", "Earthen Silk Slippers"); H.settle()
local craft = assert(ui.renderModel.targetQuery.slots.Feet.rows[1])
assert(craft.matched_access_option.source_type == "crafted" and ui:GetSourceNextStep(craft):find("Tailoring", 1, true))
ui:SetFilter("search", "Fine Longbow"); H.settle()
local bow = assert(ui.renderModel.targetQuery.slots.Ranged.rows[1])
assert(bow.matched_access_option.source.entity_name == "Wallace the Blind")
ui:SetFilter("search", "Tenets of the Silver Hand"); H.settle()
local selfCraft = ui.renderModel.targetQuery.slots.Libram.rows[1]
assert(ui:GetSourceNextStep(selfCraft) == "Craft it yourself · Enchanting")
assert(not ui:GetLevelingGearView(selfCraft, "leveling").evidence, "An unscored effect has no point estimate")
ui:SetFilter("search", "Gnomish Universal Remote"); H.settle()
local remote = ui.renderModel.targetQuery.slots.Trinket.rows[1]
assert(ui:GetSourceNextStep(remote) == "Have it crafted · Engineering · Requires Engineering (125)")
ui:SetFilter("search", "Malignant Root"); H.settle()
local token = ui.renderModel.targetQuery.slots.Ring.rows[1]
assert(token.matched_access_option.source_type == "token_turnin" and token.acquisition_display.source_label == "Token turn-ins")
assert(ui:GetSourceNextStep(token) == "Turn in to Rethiel the Greenwarden · 1 Rotheap Innards")
local evaluate = ui.GetAccessEvaluation
function ui:GetAccessEvaluation()
    return {status="blocked", blockingRequirement={type="reputation", reputation="The Silverwing Sentinels", standing="Honored"}}
end
assert(ui:GetSourceNextStep(token):find("Honored", 1, true) and ui:GetSourceNextStep(token):find("Silverwing", 1, true))
ui.GetAccessEvaluation = evaluate
for _, kind in ipairs({"drop", "vendor", "pvp", "token_turnin", "quest", "crafted"}) do
    local route = {source_type = kind, source = {type = kind, entity_id = 81, entity_name = "Named source",
        zone = "Dungeon", profession = "Tailoring", quest_id = 22}}
    assert(addon:IsGuideTargetRoute(route))
end
assert(not addon:IsGuideTargetRoute({source_type = "world_drop", source = {entity_name = "World drop"}}))
assert(not addon:IsGuideTargetRoute({source_type = "drop", source = {entity_name = "One observed mob", zone = "Wetlands", world_drop = true}}))
assert(not addon:IsGuideTargetRoute({source_type = "trade", source = {entity_name = "Auction House"}}))
ui:SetFilter("search", ""); H.settle()
ui:SetSpec("Protection"); H.settle()
assert(not ui.renderModel.targetQuery.reference and ui.renderModel.targetQuery.context.spec == "Protection")
''')

    def test_search_can_find_future_targets_and_completed_quest_rewards(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
local done = {}
C_QuestLog = {IsQuestFlaggedCompleted = function(id) return done[id] == true end,
    IsOnQuest = function() return false end}
addon:InitUIEvents()
ui:GetFilters("Gear Guide").slots = {Head = true}
ui:Open(); H.settle()
assert(not ui.renderModel.targetQuery.slots.Head.positions["16727"])
ui:SetFilter("search", "Lightforge"); H.settle()
local b = ui.renderModel.targetQuery.slots.Head
local helm = b.rows[b.positions["16727"]]
assert(helm and helm.guide_route_level > level and helm.targetVerdict.swap.forecast.level == helm.guide_route_level)
ui:SetFilter("slots", {Feet=true}); ui:SetFilter("search", ""); H.settle()
b = ui.renderModel.targetQuery.slots.Feet
assert(b.positions["10658"])
done[3370] = true
local f = addon.uiEventFrame
f:GetScript("OnEvent")(f, "QUEST_LOG_UPDATE"); H.settle()
applyListUpdate()
assert(not ui.renderModel.targetQuery.slots.Feet.positions["10658"])
ui:SetFilter("search", "Quagmire Galoshes"); H.settle()
local known = ui.renderModel.targetQuery.slots.Feet.rows[1]
assert(known.lookupReason:find("Quest already completed", 1, true) and known.stat_rank.rank)
''')

    def test_packed_entry_matches_the_original_scorer_and_responds_to_new_stats(self):
        self.lua_run(r'''
for _, check in ipairs({
    {"Retribution", 22, "Head"}, {"Retribution", 31, "Head"}, {"Protection", 35, "Main Hand"},
    {"Retribution", 38, "Head"}, {"Retribution", 49, "Head"}, {"Protection", 49, "Chest"}, {"Protection", 60, "Head"},
}) do
    local spec, at, slot = unpack(check)
    local guide = rating:GetGuideContext("Paladin", spec, at == 60 and "PR" or "LEVELING", at, "Human", "Alliance")
    local original = rating:GetGuidePlacement(guide, slot)
    local data = assert(rating:GetPackedGuide(guide)[slot], spec .. " " .. at .. " " .. slot)
    local seen = {}
    for position = 1, data.count do
        local ordinal = rating:GetPackedBrowseOrdinal(data, at, position)
        assert(ordinal and not seen[ordinal], "packed view contains every variant once")
        seen[ordinal] = true
    end
    for _, old in ipairs(original.rows) do
        local entry = assert(rating:GetGuideEntry(guide, slot, old.item.key), old.item.name)
        for _, field in ipairs({"score", "rank", "total", "tied", "score_percent", "provisional", "source_unknown", "conditional"}) do
            assert(entry[field] == old[field], spec .. " " .. at .. " " .. old.item.name .. " " .. field
                .. " " .. tostring(entry[field]) .. " instead of " .. tostring(old[field]))
        end
    end
end
local guide = rating:GetGuideContext("Paladin", "Retribution", "LEVELING", 49, "Human", "Alliance")
local variant = "10090:0:0:0:1:12723"
local old = assert(rating:GetGuideEntry(guide, "Head", variant))
local peerRank = assert(rating:GetGuideEntry(guide, "Head", "9479").rank)
assert(old.rank > peerRank)
local new = {}
for field, value in pairs(old.item) do new[field] = value end
new.stats = {strength = 200}
guide.catalog.observed[variant] = new
guide.catalog.changedSlots, guide.catalog.observedVersion = {Head = true}, 1
local updated = assert(rating:GetGuideEntry(guide, "Head", variant))
assert(updated.rank == 1 and updated.total == old.total and updated.score > old.score)
assert(rating:GetGuideEntry(guide, "Head", "9479").rank == peerRank + 1)
''')
