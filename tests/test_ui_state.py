import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LUA = shutil.which("lua5.1") or shutil.which("lua")
if not LUA:
    candidate = Path(r"C:\Program Files (x86)\Lua\5.1\lua.exe")
    LUA = str(candidate) if candidate.exists() else None

BOOTSTRAP = r'''
BigBiSList = { Widgets = {} }
BigBiSListData = {}
dofile("Config.lua")
dofile("UI.lua")
local UI = BigBiSList.UI
function UI:ScheduleRefresh() end
function UI:ScheduleLayoutRefresh() end
function UI:BuildOwnedItems() return {} end
function UI:BuildAccessState() return {} end
function BigBiSList:GetSourceTypeLabels() return {} end
function BigBiSList:GetDisplaySlotFilters() return {} end
local function equal(actual, expected, label)
    assert(actual == expected, (label or "value") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end
local function scrollFrame(height)
    return {
        value = 0,
        GetVerticalScroll = function(self) return self.value end,
        SetVerticalScroll = function(self, value) self.value = value end,
        GetHeight = function() return height end,
    }
end
local function prepareList()
    UI.contentScroll = scrollFrame(200)
    UI.detailsScroll = scrollFrame(200)
    UI.contentChild = {
        height = 700,
        GetHeight = function(self) return self.height end,
        SetHeight = function(self, value) self.height = value end,
    }
    function UI:ReleaseRenderFrames() end
    function UI:SetStickyHeaderMode() end
    function UI:UpdateVirtualList() end
    function UI:RefreshDetails() end
end
local function modelFor(rows, shift)
    local entries = {}
    for index, row in ipairs(rows) do
        local top = 2 + (index - 1) * 80 + (shift or 0)
        entries[index] = { kind = "row", data = row, mode = "phase", top = top, bottom = top + 80 }
    end
    return { entries = entries, cursor = 700 + (shift or 0), rowCount = #rows, columnMode = "phase" }
end
'''


@unittest.skipUnless(LUA, "Lua is unavailable")
class UIStateTests(unittest.TestCase):
    def run_lua(self, body):
        result = subprocess.run(
            [LUA, "-"], input=BOOTSTRAP + body, cwd=ROOT,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_migration_preserves_effective_filters_and_isolates_workspaces(self):
        self.run_lua(r'''
BigBiSListDB = { profile = { defaultsVersion = 16 } }
BigBiSListCharDB = {
    defaultsVersion = 16,
    filters = { search = "badge", sourceTypes = { vendor = true }, upgradeMode = "all", longevity = "short" },
    viewState = { upgrades = { upgradeMode = "actual", usefulness = "long", sort = "source" } },
    wishlist = { ["10"] = true }, ignoredItems = { ["20"] = true },
}
BigBiSList:EnsureDatabase()
equal(BigBiSListCharDB.defaultsVersion, 17, "new schema")
local upgrades, bis = UI:GetFilters("Upgrades"), UI:GetFilters("By Slot")
equal(upgrades.upgradeMode, "actual", "effective upgrade mode")
equal(upgrades.longevity, "long", "effective usefulness")
equal(upgrades.search, "badge", "search survives")
equal(UI:GetViewState("Upgrades").upgradeMode, nil, "duplicate state removed")
equal(UI:GetViewState("Upgrades").sort, "source", "sort survives")
upgrades.sourceTypes.vendor = nil
upgrades.search = "new search"
assert(bis.sourceTypes.vendor, "facet tables must be independent")
equal(bis.search, "badge", "other view search")
assert(BigBiSListCharDB.wishlist["10"] and BigBiSListCharDB.ignoredItems["20"], "membership survives")
dofile("Config.lua")
BigBiSList:EnsureDatabase()
equal(UI:GetFilters("Upgrades").search, "new search", "repeat initialization preserves filters")
''')

    def test_removing_chips_removes_the_effective_query_filters(self):
        self.run_lua(r'''
BigBiSList:EnsureDatabase()
UI:SetFilter("upgradeMode", "all")
UI:SetFilter("longevity", "long")
local chips = UI:GetActiveFilterChips()
equal(#chips, 2, "nondefault chips")
for _, chip in ipairs(chips) do chip.clear() end
equal(#UI:GetActiveFilterChips(), 0, "removed chips")
local payload = UI:BuildFilterPayload()
equal(payload.upgradeMode, "actual", "upgrade filter really resets")
equal(payload.longevity, "all", "usefulness filter really resets")
UI:SetFilter("search", "helm")
UI:SetTab("Wishlist")
equal(UI:GetFilters().search, "", "search does not leak")
UI:SetFilter("search", "ring")
UI:ClearFilters()
equal(UI:GetFilters("Upgrades").search, "helm", "reset is local")
''')

    def test_tab_return_and_passive_refresh_restore_row_anchors(self):
        self.run_lua(r'''
BigBiSList:EnsureDatabase()
prepareList()
local rows = { {item_id=1,slot="Head"}, {item_id=2,slot="Chest"}, {item_id=3,slot="Legs"} }
UI:RenderListModel(modelFor(rows))
UI.contentScroll:SetVerticalScroll(100)
UI:ShowInspectorFor(2, rows[2], "phase")
UI.detailsScroll:SetVerticalScroll(45)
UI:SetTab("Wishlist")
UI:RenderListModel(modelFor({{item_id=4,slot="Ring"}}))
equal(UI.contentScroll.value, 0, "new view starts at top")
equal(UI.selectedItemId, nil, "selection does not leak")
UI:SetTab("Upgrades")
UI:RenderListModel(modelFor(rows))
equal(UI.contentScroll.value, 100, "view position restored")
equal(UI.selectedItemId, 2, "view selection restored")
equal(UI.detailsScroll.value, 45, "same details position restored")
UI:RenderListModel(modelFor(rows, 80))
equal(UI.contentScroll.value, 180, "passive refresh preserves visible row offset")
UI:SetFilter("search", "chest")
UI:RenderListModel(modelFor({rows[2]}))
equal(UI.contentScroll.value, 0, "changed query starts at top")
equal(UI.selectedItemId, 2, "still-relevant selection survives")
UI:SetPhase("T4")
UI:RenderListModel(modelFor(rows))
equal(UI.contentScroll.value, 0, "new progression starts at top")
equal(UI.selectedItemId, nil, "new context clears selection")
''')

    def test_selection_distinguishes_entity_slot_and_variant(self):
        self.run_lua(r'''
BigBiSList:EnsureDatabase()
prepareList()
local item = { item_id=7, slot="Ring", variant_id="a" }
local variant = { item_id=7, slot="Ring", variant_id="b" }
local slot = { item_id=7, slot="Trinket", variant_id="a" }
local spell = { spell_id=7, slot="Ring", variant_id="a" }
assert(UI:GetRowKey(item) ~= UI:GetRowKey(variant))
assert(UI:GetRowKey(item) ~= UI:GetRowKey(slot))
assert(UI:GetRowKey(item) ~= UI:GetRowKey(spell))
UI:ShowInspectorFor(7, item, "phase")
UI.detailsScroll:SetVerticalScroll(80)
UI:ShowInspectorFor(7, item, "phase")
equal(UI.detailsScroll.value, 80, "same row preserves details scroll")
UI:ShowInspectorFor(7, variant, "phase")
equal(UI.detailsScroll.value, 0, "new variant starts details at top")
UI:RebindSelectedRowFromModel(modelFor({item, slot, spell}))
equal(UI.selectedItemId, nil, "missing variant does not bind another row")
equal(UI.selectedRowKey, nil, "missing selection clears highlight")
''')

    def test_settings_returns_to_workspace_and_empty_results_finish_navigation(self):
        self.run_lua(r'''
BigBiSList:EnsureDatabase()
prepareList()
local rows = {{item_id=1,slot="Head"}, {item_id=2,slot="Chest"}}
UI:SetTab("By Slot")
UI:RenderListModel(modelFor(rows))
UI:GetFilters().search = "helm"
UI.contentScroll:SetVerticalScroll(90)
UI:OpenSettings("Hidden Items")
equal(UI:GetSelection().tab, "Settings", "settings opens")
equal(UI:GetFilters().search, "helm", "settings uses safe context filters")
UI:ApplySettingsNavigation()
equal(UI.contentScroll.value, 0, "settings starts at top")
UI:ReturnFromSettings()
UI:RenderListModel(modelFor(rows))
equal(UI:GetSelection().tab, "By Slot", "workspace restored")
equal(UI.contentScroll.value, 90, "workspace scroll restored")
UI:SetFilter("search", "no match")
UI:ApplyEmptyNavigation()
equal(UI.pendingNavigation, nil, "empty results commit transition")
equal(UI.contentScroll.value, 0, "empty results start at top")
''')

    def test_item_actions_are_named_reversible_and_expire(self):
        self.run_lua(r'''
BigBiSList:EnsureDatabase()
local now, timers = 100, {}
function GetTime() return now end
C_Timer = { After = function(delay, callback) timers[#timers+1] = {delay=delay,callback=callback} end }
function BigBiSList:GetItemData(id) return {name="Test Helm"} end
UI.undoButton = {shown=false, Show=function(self) self.shown=true end, Hide=function(self) self.shown=false end}
UI:IgnoreItem(10)
assert(string.find(UI.transientStatusMessage, "Test Helm", 1, true))
assert(BigBiSListCharDB.ignoredItems["10"] and UI.undoButton.shown)
equal(timers[#timers].delay, 8, "undo availability")
assert(UI:UndoLastAction())
equal(BigBiSListCharDB.ignoredItems["10"], nil, "hide undone")
assert(not UI.undoButton.shown)
UI:AddWishlist(10)
assert(UI:UndoLastAction())
equal(BigBiSListCharDB.wishlist["10"], nil, "save undone")
UI:IgnoreItem(10)
local expiry = timers[#timers].callback
now = now + 8
assert(not UI:UndoLastAction(), "expired action cannot run")
expiry()
assert(BigBiSListCharDB.ignoredItems["10"], "expiry does not change item")
equal(UI.undoAction, nil, "expired action cleared")
''')

    def test_current_character_restores_automatic_level(self):
        self.run_lua(r'''
function UnitLevel() return 42 end
BigBiSList:EnsureDatabase()
BigBiSList:SetSelectedLevelingLevel(60, true)
equal(BigBiSList:GetSelectedLevelingLevel(), 60, "manual level")
UI:UseMyCharacter()
equal(BigBiSList:GetSelectedLevelingLevel(), 42, "current character level")
assert(not BigBiSListCharDB.leveling.manualLevel)
function UnitLevel() return 43 end
equal(BigBiSList:GetSelectedLevelingLevel(), 43, "automatic tracking resumes")
''')


if __name__ == "__main__":
    unittest.main()
