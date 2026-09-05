import shutil
import subprocess
import unittest
from pathlib import Path

from tools.project import ADDON_DIR


def find_lua51() -> str | None:
    candidates = [
        shutil.which("lua"),
        shutil.which("lua5.1"),
        Path(r"C:\Program Files (x86)\Lua\5.1\lua.exe"),
        Path(r"C:\Program Files\Lua\5.1\lua.exe"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        executable = str(candidate)
        try:
            result = subprocess.run(
                [executable, "-e", "io.write(_VERSION)"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and result.stdout.strip() == "Lua 5.1":
            return executable
    return None


LUA_ASSERTIONS = r'''
local function expect(value, label)
    if not value then
        error(label or "expectation failed", 2)
    end
end

local function equal(actual, expected, label)
    if actual ~= expected then
        error((label or "values differ")
            .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual), 2)
    end
end

local function contains(values, wanted)
    for _, value in ipairs(values or {}) do
        if value == wanted then
            return true
        end
    end
    return false
end
'''


class AddonLuaRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body: str):
        if not self.lua:
            self.skipTest("Lua 5.1 is not available")
        result = subprocess.run(
            [self.lua, "-"],
            cwd=ADDON_DIR,
            input=LUA_ASSERTIONS + "\n" + body,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_dropdown_uses_full_field_click_target_and_preserves_native_anchors(self):
        self.run_lua(r'''
BigBiSList = {}
UIParent = {}
UIDROPDOWNMENU_MAXLEVELS = 2

local createdFrames = {}
local nativeClicks = 0
local toggleCalls = {}
local initializer
local addedButtons = {}
local displayedText
local nativeGeometryWrite = false
local provideNativeButtons = false

local function makeFrame(kind, name, parent)
    local frame = {
        kind = kind,
        name = name,
        parent = parent,
        children = {},
        scripts = {},
        points = {},
        frameLevel = 5,
        frameStrata = "MEDIUM",
        clamped = false,
        mouseEnabled = false,
        shown = true,
        enabled = true,
        scale = 0.85,
        geometryMutations = {
            parent = 0,
            clamp = 0,
            clearPoints = 0,
            setPoint = 0,
            scale = 0,
        },
    }
    if type(parent) == "table" and parent.children then
        table.insert(parent.children, frame)
    end
    table.insert(createdFrames, frame)

    function frame:GetName() return self.name end
    function frame:GetParent() return self.parent end
    function frame:SetParent(value)
        if self.trackGeometry and not nativeGeometryWrite then
            self.geometryMutations.parent = self.geometryMutations.parent + 1
        end
        self.parent = value
    end
    function frame:GetChildren() return unpack(self.children) end
    function frame:SetAllPoints(value) self.allPoints = value or true end
    function frame:ClearAllPoints()
        if self.trackGeometry and not nativeGeometryWrite then
            self.geometryMutations.clearPoints = self.geometryMutations.clearPoints + 1
        end
        self.points = {}
    end
    function frame:SetPoint(...)
        if self.trackGeometry and not nativeGeometryWrite then
            self.geometryMutations.setPoint = self.geometryMutations.setPoint + 1
        end
        table.insert(self.points, { ... })
    end
    function frame:GetPoint(index)
        local point = self.points[index or 1]
        if point then
            return unpack(point)
        end
    end
    function frame:SetSize(width, height) self.width, self.height = width, height end
    function frame:SetWidth(width) self.width = width end
    function frame:SetHeight(height) self.height = height end
    function frame:GetWidth() return self.width or 0 end
    function frame:GetHeight() return self.height or 0 end
    function frame:SetFrameStrata(value) self.frameStrata = value end
    function frame:GetFrameStrata() return self.frameStrata end
    function frame:GetFrameLevel() return self.frameLevel end
    function frame:SetFrameLevel(value) self.frameLevel = value end
    function frame:SetClampedToScreen(value)
        if self.trackGeometry and not nativeGeometryWrite then
            self.geometryMutations.clamp = self.geometryMutations.clamp + 1
        end
        self.clamped = value
    end
    function frame:IsClampedToScreen() return self.clamped end
    function frame:SetScale(value)
        if self.trackGeometry and not nativeGeometryWrite then
            self.geometryMutations.scale = self.geometryMutations.scale + 1
        end
        self.scale = value
    end
    function frame:GetScale() return self.scale end
    function frame:EnableMouse(value) self.mouseEnabled = value end
    function frame:IsMouseEnabled() return self.mouseEnabled end
    function frame:RegisterForClicks(...) self.registeredClicks = { ... } end
    function frame:SetScript(event, callback) self.scripts[event] = callback end
    function frame:GetScript(event) return self.scripts[event] end
    function frame:HookScript(event, callback)
        local previous = self.scripts[event]
        self.scripts[event] = function(...)
            if previous then previous(...) end
            callback(...)
        end
    end
    function frame:Click()
        if self.scripts.OnClick then self.scripts.OnClick(self, "LeftButton") end
    end
    function frame:IsEnabled() return self.enabled end
    function frame:Show()
        self.shown = true
        if self.scripts.OnShow then self.scripts.OnShow(self) end
    end
    function frame:Hide()
        self.shown = false
        if self.scripts.OnHide then self.scripts.OnHide(self) end
    end
    function frame:IsShown() return self.shown end

    return frame
end

DropDownList1 = makeFrame("Frame", "DropDownList1", {})
DropDownList2 = makeFrame("Frame", "DropDownList2", {})
DropDownList1.shown = false
DropDownList2.shown = false
DropDownList1.trackGeometry = true
DropDownList2.trackGeometry = true

local function positionRootList(dropdown)
    nativeGeometryWrite = true
    DropDownList1:ClearAllPoints()
    DropDownList1:SetPoint("TOPLEFT", dropdown, "BOTTOMLEFT", 0, 0)
    DropDownList1.resolvedX = dropdown.mockX
    nativeGeometryWrite = false
end

local function toggleNativeDropdown(dropdown)
    if DropDownList1:IsShown() and DropDownList1.dropdown == dropdown then
        DropDownList1:Hide()
        UIDROPDOWNMENU_OPEN_MENU = nil
        return
    end
    if DropDownList1:IsShown() then
        DropDownList1:Hide()
    end
    DropDownList1.dropdown = dropdown
    UIDROPDOWNMENU_OPEN_MENU = dropdown
    positionRootList(dropdown)
    DropDownList1:Show()
end

function CreateFrame(kind, name, parent, template)
    local frame = makeFrame(kind, name, parent)
    frame.template = template
    if template == "UIDropDownMenuTemplate" and provideNativeButtons then
        local nativeButton = makeFrame("Button", name .. "Button", frame)
        nativeButton:SetScript("OnClick", function()
            nativeClicks = nativeClicks + 1
            toggleNativeDropdown(frame)
        end)
        _G[name .. "Button"] = nativeButton
    end
    return frame
end

function UIDropDownMenu_SetWidth(frame, width) frame:SetWidth(width + 40) end
function UIDropDownMenu_SetText(_, value) displayedText = value end
function UIDropDownMenu_Initialize(_, callback) initializer = callback end
function UIDropDownMenu_CreateInfo() return {} end
function UIDropDownMenu_AddButton(info) table.insert(addedButtons, info) end
function ToggleDropDownMenu(...)
    local level, value, dropdown, anchorName, xOffset, yOffset = ...
    table.insert(toggleCalls, {
        count = select("#", ...),
        level = level,
        value = value,
        dropdown = dropdown,
        anchorName = anchorName,
        xOffset = xOffset,
        yOffset = yOffset,
    })
    toggleNativeDropdown(dropdown)
end
C_Timer = { After = function(_, callback) callback() end }

dofile("Widgets.lua")

local function expectNoGeometryMutations(frame, label)
    for mutation, count in pairs(frame.geometryMutations) do
        equal(count, 0, label .. " does not mutate " .. mutation)
    end
end

local selectedValue
local selectedItem
local firstParent = makeFrame("Frame", "FirstParent", nil)
local dropdown = BigBiSList.Widgets:CreateDropdown(
    "RuntimeDropdown",
    firstParent,
    132,
    function() return "Current value" end,
    function()
        return {
            {
                text = "First",
                value = "first",
                checked = true,
                isNotRadio = true,
                keepShownOnClick = true,
                notCheckable = false,
                disabled = false,
            },
            {
                text = "Second",
                value = "second",
                checked = false,
                isNotRadio = false,
                keepShownOnClick = false,
                notCheckable = true,
                disabled = true,
            },
        }
    end,
    function(value, item)
        selectedValue = value
        selectedItem = item
    end
)
dropdown.mockX = 120
dropdown:SetPoint("TOPLEFT", firstParent, "TOPLEFT", 120, -40)
local dropdownInitializer = initializer

expect(dropdown.clickCover, "shared dropdown exposes its full-field click target")
expect(dropdown.clickCover.allPoints == dropdown, "click target covers the complete field")
expect(dropdown.clickCover.mouseEnabled, "click target accepts mouse input")
equal(dropdown.clickCover.registeredClicks[1], "LeftButtonUp", "click target registration")
expect(not dropdown.nativeButton, "primary path works without a native arrow button")

local listParent = DropDownList1.parent
local listClamp = DropDownList1.clamped
local listScale = DropDownList1.scale
dropdown.clickCover:Click()
equal(#toggleCalls, 1, "full-field click uses the native toggle API")
equal(toggleCalls[1].count, 3, "native toggle receives exactly three arguments")
equal(toggleCalls[1].level, 1, "native toggle menu level")
equal(toggleCalls[1].value, nil, "native toggle menu value")
equal(toggleCalls[1].dropdown, dropdown, "native toggle owner")
equal(toggleCalls[1].anchorName, nil, "native toggle does not override the anchor")
equal(toggleCalls[1].xOffset, nil, "native toggle does not override the x offset")
equal(toggleCalls[1].yOffset, nil, "native toggle does not override the y offset")
equal(#DropDownList1.points, 1, "native positioning leaves one current root anchor")
local point, relativeTo, relativePoint, xOffset, yOffset = DropDownList1:GetPoint(1)
equal(point, "TOPLEFT", "native root anchor point")
equal(relativeTo, dropdown, "root list anchors to its dropdown owner")
equal(relativePoint, "BOTTOMLEFT", "native root relative point")
equal(xOffset, 0, "native root x offset")
equal(yOffset, 0, "native root y offset")
equal(DropDownList1.resolvedX, 120, "native root anchor resolves from the first owner")
equal(DropDownList1.parent, listParent, "popup parent remains native-owned")
equal(DropDownList1.clamped, listClamp, "popup clamp state remains native-owned")
equal(DropDownList1.scale, listScale, "popup scale remains native-owned")
expectNoGeometryMutations(DropDownList1, "root popup preparation")
equal(DropDownList1.frameStrata, "FULLSCREEN_DIALOG", "open dropdown list strata")
expect(DropDownList1.frameLevel >= 1001, "open dropdown list elevation")
equal(DropDownList2.frameStrata, "MEDIUM", "hidden nested list is not globally elevated")

local nestedAnchor = makeFrame("Button", "NestedAnchor", dropdown)
local nestedParent = DropDownList2.parent
local nestedClamp = DropDownList2.clamped
local nestedScale = DropDownList2.scale
nativeGeometryWrite = true
DropDownList2:ClearAllPoints()
DropDownList2:SetPoint("TOPLEFT", nestedAnchor, "TOPRIGHT", 4, 0)
nativeGeometryWrite = false
DropDownList2.dropdown = dropdown
DropDownList2:Show()
equal(DropDownList2.frameStrata, "FULLSCREEN_DIALOG", "nested BBL list elevates when it opens")
expect(DropDownList2.frameLevel >= 1002, "nested BBL list elevation")
local nestedPoint, nestedRelativeTo, nestedRelativePoint = DropDownList2:GetPoint(1)
equal(nestedPoint, "TOPLEFT", "nested native anchor point")
equal(nestedRelativeTo, nestedAnchor, "nested list keeps its native owner anchor")
equal(nestedRelativePoint, "TOPRIGHT", "nested native relative point")
equal(DropDownList2.parent, nestedParent, "nested popup parent remains native-owned")
equal(DropDownList2.clamped, nestedClamp, "nested popup clamp remains native-owned")
equal(DropDownList2.scale, nestedScale, "nested popup scale remains native-owned")
expectNoGeometryMutations(DropDownList2, "nested popup preparation")
DropDownList2:Hide()

dropdown.clickCover:Click()
equal(#toggleCalls, 2, "second full-field click still uses the native toggle")
expect(not DropDownList1:IsShown(), "second full-field click closes the menu")
equal(DropDownList1.frameStrata, "MEDIUM", "closed shared list is not re-elevated by deferred preparation")
dropdown.clickCover:Click()
expect(DropDownList1:IsShown(), "full-field click can reopen the menu")

dropdownInitializer(dropdown, 1)
equal(#addedButtons, 2, "all menu entries are initialized")
for key, expected in pairs({
    text = "Second",
    value = "second",
    checked = false,
    isNotRadio = false,
    keepShownOnClick = false,
    notCheckable = true,
    disabled = true,
}) do
    equal(addedButtons[2][key], expected, "forwarded field " .. key)
end
addedButtons[1].func()
equal(selectedValue, "first", "entry callback keeps its own value")
equal(selectedItem.text, "First", "entry callback keeps its own item")
equal(displayedText, "Current value", "selection refreshes dropdown text")
expect(DropDownList1:IsShown(), "multi-select callback leaves the menu open")

provideNativeButtons = true
local secondParent = makeFrame("Frame", "SecondParent", nil)
local secondDropdown = BigBiSList.Widgets:CreateDropdown(
    "SecondRuntimeDropdown",
    secondParent,
    132,
    function() return "Second value" end,
    function() return {} end,
    function() end
)
secondDropdown.mockX = 640
secondDropdown:SetPoint("TOPLEFT", secondParent, "TOPLEFT", 640, -80)
secondDropdown.clickCover:Click()
equal(#toggleCalls, 4, "second dropdown opens through the native toggle API")
equal(toggleCalls[4].count, 3, "second dropdown toggle receives exactly three arguments")
equal(toggleCalls[4].dropdown, secondDropdown, "second toggle uses the current dropdown owner")
equal(toggleCalls[4].anchorName, nil, "second toggle has no custom anchor")
equal(nativeClicks, 0, "native arrow is not used while the toggle API is available")
equal(#DropDownList1.points, 1, "second open replaces the shared list anchor")
local secondPoint, secondRelativeTo, secondRelativePoint = DropDownList1:GetPoint(1)
equal(secondPoint, "TOPLEFT", "second native anchor point")
equal(secondRelativeTo, secondDropdown, "shared list reanchors to the second dropdown")
equal(secondRelativePoint, "BOTTOMLEFT", "second native relative point")
equal(DropDownList1.resolvedX, 640, "shared list resolves from the second owner")
expectNoGeometryMutations(DropDownList1, "second root popup preparation")

DropDownList1:Hide()
local unrelatedOwner = makeFrame("Frame", "UnrelatedDropdown", nil)
unrelatedOwner.mockX = 900
toggleNativeDropdown(unrelatedOwner)
local unrelatedPoint, unrelatedRelativeTo = DropDownList1:GetPoint(1)
equal(unrelatedPoint, "TOPLEFT", "unrelated popup keeps its native point")
equal(unrelatedRelativeTo, unrelatedOwner, "unrelated popup keeps its native owner")
equal(DropDownList1.frameStrata, "MEDIUM", "unrelated dropdown keeps its native strata")
equal(DropDownList1.frameLevel, 5, "unrelated dropdown keeps its native level")
equal(DropDownList1.parent, listParent, "unrelated dropdown keeps its native parent")
equal(DropDownList1.clamped, listClamp, "unrelated dropdown keeps its native clamp state")
equal(DropDownList1.scale, listScale, "unrelated dropdown keeps its native scale")
expectNoGeometryMutations(DropDownList1, "unrelated popup handling")

DropDownList1:Hide()
local nativeToggle = ToggleDropDownMenu
ToggleDropDownMenu = nil
secondDropdown.clickCover:Click()
equal(nativeClicks, 1, "native arrow click is used only when the toggle API is unavailable")
expect(DropDownList1:IsShown(), "native arrow fallback opens the menu")
local fallbackPoint, fallbackRelativeTo = DropDownList1:GetPoint(1)
equal(fallbackPoint, "TOPLEFT", "native arrow fallback point")
equal(fallbackRelativeTo, secondDropdown, "native arrow fallback anchors to its dropdown")
expectNoGeometryMutations(DropDownList1, "native arrow fallback preparation")
ToggleDropDownMenu = nativeToggle

DropDownList1.dropdown = secondDropdown
DropDownList1:Show()
DropDownList2.dropdown = secondDropdown
DropDownList2:Show()
expect(BigBiSList.Widgets:CloseDropdownMenus(), "fallback reports that dropdown lists were closed")
expect(not DropDownList1:IsShown(), "first dropdown list closes")
expect(not DropDownList2:IsShown(), "second dropdown list closes")
''')

    def test_ui_invalidation_keeps_layout_work_separate_from_data_domains(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local owned = { marker = "owned" }
local access = { marker = "access" }
local payload = { marker = "query" }
local availability = { marker = "availability" }
UI.currentOwned = owned
UI.currentAccess = access
UI.currentFilterPayload = payload
UI.currentAvailabilitySnapshot = availability

UI:Invalidate("layout", "runtime-layout-test")
equal(UI.currentOwned, owned, "layout keeps ownership cache")
equal(UI.currentAccess, access, "layout keeps access cache")
equal(UI.currentFilterPayload, payload, "layout keeps query payload")
equal(UI.currentAvailabilitySnapshot, availability, "layout keeps availability cache")
expect(UI.dirtyDomains.layout, "layout domain is dirty")
expect(not UI.dirtyDomains.query, "layout does not dirty query data")

local queryCache = { phase = { "cached rows" } }
UI.currentViewQueryCache = queryCache
UI:Invalidate("presentation", "runtime-presentation-test")
equal(UI.currentOwned, owned, "presentation keeps ownership cache")
equal(UI.currentAccess, access, "presentation keeps access cache")
equal(UI.currentFilterPayload, payload, "presentation keeps query payload")
equal(UI.currentAvailabilitySnapshot, availability, "presentation keeps filter availability")
equal(UI.currentViewQueryCache, queryCache, "presentation keeps the row corpus")
expect(UI.dirtyDomains.presentation, "presentation domain is dirty")

UI:Invalidate("ownership", "runtime-ownership-test")
equal(UI.currentOwned, nil, "ownership invalidation clears owned cache")
equal(UI.currentAccess, access, "ownership invalidation keeps independent access cache")
equal(UI.currentFilterPayload, nil, "ownership invalidation clears dependent query payload")
equal(UI.currentAvailabilitySnapshot, nil, "ownership invalidation clears dependent availability")
equal(UI.currentViewQueryCache, nil, "ownership invalidation clears dependent row corpus")
expect(UI.dirtyDomains.ownership, "ownership domain is dirty")
expect(UI.dirtyDomains.query, "ownership dirties query domain")
expect(UI.dirtyDomains.details, "ownership dirties details domain")
equal(UI.lastInvalidationReason, "runtime-ownership-test", "invalidation reason is retained")
''')

    def test_presentation_sort_does_not_mutate_the_cached_query_order(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local state = { sort = "item", sortDirection = "asc" }
UI.GetViewState = function() return state end
local cachedRows = {
    { name = "Zulu", priority = 10 },
    { name = "Alpha", priority = 5 },
}

local itemRows = UI:SortDisplayRows(cachedRows, "planner")
equal(itemRows[1].name, "Alpha", "item sort applies to presentation copy")
equal(cachedRows[1].name, "Zulu", "cached query order remains immutable")

state.sort = "priority"
local priorityRows = UI:SortDisplayRows(cachedRows, "planner")
equal(priorityRows[1].name, "Zulu", "default sort restores DataIndex order")
expect(priorityRows ~= cachedRows, "default ordering also uses a presentation copy")
''')

    def test_access_evaluation_uses_the_rows_matching_future_acquisition_path(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
UI.currentAccess = {
    playerSide = "Alliance",
    reputations = {},
    professions = {},
    knownSpells = {},
    knownItems = {},
}
UI.GetFilters = function()
    return { sourceTypes = { raid_drop = true } }
end
UI.GetEffectivePhaseKey = function() return "PR" end
BigBiSList.GetPhaseOrder = function() return { "PR", "T4", "T5", "T6", "ZA", "SWP" } end
BigBiSList.GetRowAccessOptions = function(_, row) return row.access_options end

local primary = {
    is_primary = true,
    source_type = "dungeon_drop",
    source_filter_key = "dungeon_drop",
    acquisition_phase = "PR",
    requirements = {},
}
local matchedFuture = {
    source_type = "raid_drop",
    source_filter_key = "raid_drop",
    acquisition_phase = "T4",
    requirements = {},
}
local row = {
    access_options = { primary, matchedFuture },
    matched_access_option = matchedFuture,
    acquisition_display = {
        option = matchedFuture,
        future = true,
        acquisition_phase = "T4",
    },
}
local evaluation = UI:GetAccessEvaluation(row)
equal(evaluation.optionEvaluation.option, matchedFuture, "inspector preserves the grid's matched acquisition option")
equal(evaluation.status, "future", "future matched source is not presented as available now")
expect(evaluation.context_matched, "matched grid path is reported as the active context")

UI.GetFilters = function() return { sourceTypes = { vendor = true } } end
local reported = {
    is_primary = true,
    is_vendor_purchase = true,
    source_type = "vendor",
    source_filter_key = "vendor",
    vendor_details_status = "reported_only",
    vendor_key = "fixture-reported",
    vendor_label = "Reported Seller",
    location_area = "Nagrand",
    acquisition_phase = "PR",
    requirements = {},
}
local reportedRow = { access_options = { reported }, matched_access_option = reported }
local reportedEvaluation = UI:GetAccessEvaluation(reportedRow)
equal(reportedEvaluation.status, "unknown", "reported-only route is never presented as ready")
equal(reportedEvaluation.optionEvaluation, nil, "reported-only route is not selected")

BigBiSList.GetRowSellerGroups = function()
    return { selected = nil, alternatives = {}, reported = { reported } }
end
local sellerGroups = UI:GetRowSellerDisplayGroups(reportedRow, reported)
equal(sellerGroups.selected, nil, "reported-only seller stays out of the selected route")
equal(#sellerGroups.reported, 1, "reported-only seller remains available in reported details")
''')

    def test_selected_row_rebinding_distinguishes_item_and_spell_id_collisions(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local oldSpell = { entity_type = "spell", entity_id = 27981, spell_id = 27981, name = "Sunfire" }
local cloak = { entity_type = "item", entity_id = 27981, item_id = 27981, name = "Sethekk Oracle Cloak" }
local freshSpell = { entity_type = "spell", entity_id = 27981, spell_id = 27981, name = "Sunfire (fresh)" }
UI.selectedItemId = 27981
UI.selectedEntityType = "spell"
UI.selectedItemData = oldSpell
UI.selectedItemMode = "enhance"
UI:RebindSelectedRowFromModel({
    entries = {
        { kind = "row", mode = "phase", data = cloak },
        { kind = "row", mode = "enhance", data = freshSpell },
    },
})
equal(UI.selectedItemData, freshSpell, "selection rebinds to the same entity type")
equal(UI.selectedItemMode, "enhance", "selection preserves the matching row mode")
equal(UI.selectedEntityType, "spell", "item ID collision cannot change selected entity type")
''')

    def test_flexible_column_layouts_are_bounded_deterministic_and_cached(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local modes = { "planner", "phase", "leveling", "enhance", "wishlist", "gear" }
local expectedColumns = {
    planner = {
        wide = {
            { "item", "Item", 170, 260, 420, 8 }, { "slot", "Slot", 72, 88, 112, 2 },
            { "value", "Value", 126, 170, 240, 4 }, { "source", "Source", 108, 128, 168, 2 },
            { "location", "Location", 150, 210, 300, 6 }, { "owned", "Owned", 86, 86, 86, 0 },
            { "action", "Wishlist", 58, 58, 58, 0 },
        },
        compact = {
            { "item", "Item", 140, 220, 340, 8 }, { "slot", "Slot", 64, 82, 100, 2 },
            { "value", "Value", 96, 145, 210, 4 }, { "acquisition", "Acquisition", 145, 230, 330, 6 },
            { "owned", "Owned", 80, 80, 80, 0 }, { "action", "Wishlist", 58, 58, 58, 0 },
        },
    },
    phase = {
        wide = {
            { "rank", "Rank", 92, 104, 128, 2 }, { "item", "Item", 190, 300, 460, 8 },
            { "source", "Source", 108, 128, 168, 2 }, { "location", "Location", 150, 220, 320, 6 },
            { "owned", "Owned", 86, 86, 86, 0 }, { "action", "Wishlist", 58, 58, 58, 0 },
        },
        compact = {
            { "rank", "Rank", 76, 94, 116, 2 }, { "item", "Item", 145, 250, 400, 8 },
            { "acquisition", "Acquisition", 145, 250, 360, 6 }, { "owned", "Owned", 80, 80, 80, 0 },
            { "action", "Wishlist", 58, 58, 58, 0 },
        },
    },
    leveling = {
        wide = {
            { "item", "Item", 170, 260, 420, 8 }, { "slot", "Slot", 72, 88, 112, 2 },
            { "value", "Level / Value", 128, 176, 250, 4 }, { "source", "Source", 108, 128, 168, 2 },
            { "location", "Location", 140, 210, 300, 6 }, { "owned", "Owned", 86, 86, 86, 0 },
            { "action", "Wishlist", 58, 58, 58, 0 },
        },
        compact = {
            { "item", "Item", 140, 220, 340, 8 }, { "slot", "Slot", 64, 82, 100, 2 },
            { "value", "Level / Value", 104, 155, 220, 4 }, { "acquisition", "Acquisition", 145, 230, 330, 6 },
            { "owned", "Owned", 80, 80, 80, 0 }, { "action", "Wishlist", 58, 58, 58, 0 },
        },
    },
    enhance = {
        wide = {
            { "item", "Enhancement", 180, 260, 420, 8 }, { "slot", "For", 96, 116, 144, 2 },
            { "value", "Recommendation", 140, 190, 270, 5 }, { "owned", "Applied / Owned", 104, 104, 104, 0 },
            { "source", "Source", 108, 128, 168, 2 }, { "access", "Access", 116, 140, 176, 3 },
        },
        compact = {
            { "item", "Enhancement", 145, 230, 360, 8 }, { "slot", "For", 72, 102, 130, 2 },
            { "value", "Recommendation", 108, 170, 240, 5 }, { "owned", "Applied / Owned", 104, 104, 104, 0 },
            { "acquisition", "Source / Access", 150, 240, 340, 6 },
        },
    },
    wishlist = {
        wide = {
            { "item", "Item", 140, 220, 340, 6 }, { "slot", "Slots", 68, 90, 120, 2 },
            { "expansion", "Expansion Ranking", 260, 340, 500, 10 }, { "source", "Source", 96, 116, 156, 2 },
            { "location", "Location", 112, 180, 280, 6 }, { "owned", "Owned", 80, 80, 80, 0 },
            { "action", "Remove", 58, 58, 58, 0 },
        },
        compact = {
            { "item", "Item", 105, 180, 280, 6 }, { "slot", "Slots", 56, 80, 105, 2 },
            { "expansion", "Expansion Ranking", 230, 330, 480, 10 },
            { "acquisition", "Acquisition", 115, 190, 290, 6 }, { "action", "Remove", 58, 58, 58, 0 },
        },
    },
    gear = {
        wide = {
            { "slot", "Slot", 106, 120, 150, 2 }, { "item", "Equipped Item", 260, 420, 620, 8 },
            { "currentRank", "Current Rank", 170, 220, 300, 4 },
            { "usefulThrough", "Useful Through", 150, 180, 220, 3 },
        },
        compact = {
            { "slot", "Slot", 72, 100, 126, 2 }, { "item", "Equipped Item", 165, 300, 480, 8 },
            { "currentRank", "Current Rank", 105, 180, 260, 4 },
            { "usefulThrough", "Useful Through", 96, 145, 190, 3 },
        },
    },
}

for _, mode in ipairs(modes) do
    for _, shape in ipairs({ "wide", "compact" }) do
        local definitions = UI:GetViewColumnDefinitions(mode, shape == "compact")
        local expected = expectedColumns[mode][shape]
        equal(#definitions, #expected, mode .. " " .. shape .. " configured column count")
        for index, values in ipairs(expected) do
            local definition = definitions[index]
            equal(definition.key, values[1], mode .. " " .. shape .. " key " .. tostring(index))
            equal(definition.label, values[2], mode .. " " .. shape .. " label " .. tostring(index))
            equal(definition.minWidth, values[3], mode .. " " .. shape .. " minimum " .. definition.key)
            equal(definition.preferredWidth, values[4], mode .. " " .. shape .. " preferred " .. definition.key)
            equal(definition.maxWidth, values[5], mode .. " " .. shape .. " maximum " .. definition.key)
            equal(definition.growWeight, values[6], mode .. " " .. shape .. " weight " .. definition.key)
        end
    end
end
expect(UI:GetViewColumnDefinitions("wishlist", true)[1].ownershipInline,
    "compact Wishlist keeps ownership in the Item column")

local fractionalLayout = UI:GetTableColumnLayout(1016.75, "planner", true)
equal(fractionalLayout.usableWidth, 1000, "fractional viewport widths round down")
expect(fractionalLayout.usedWidth <= fractionalLayout.usableWidth, "fractional widths cannot overshoot the viewport")

local function totalFor(definitions, widthKey)
    local total = 8 * math.max(0, #definitions - 1)
    for _, definition in ipairs(definitions) do
        total = total + definition[widthKey]
    end
    return total
end

local function expectTargetWidths(layout, definitions, widthKey, label)
    for index, definition in ipairs(definitions) do
        equal(layout.columns[index].width, definition[widthKey], label .. " " .. definition.key)
    end
end

local function validateLayout(mode, compact, layout, label)
    local definitions = UI:GetViewColumnDefinitions(mode, compact)
    equal(layout.compact, compact, label .. " shape")
    equal(#layout.columns, #definitions, label .. " column count")
    local expectedX = 8
    local usedWidth = 8 * math.max(0, #definitions - 1)
    for index, definition in ipairs(definitions) do
        local column = layout.columns[index]
        equal(column.key, definition.key, label .. " key " .. tostring(index))
        equal(layout[column.key], column, label .. " keyed column " .. definition.key)
        equal(column.x, expectedX, label .. " x " .. definition.key)
        equal(column.width, math.floor(column.width), label .. " integer width " .. definition.key)
        expect(column.width >= definition.minWidth, label .. " respects minimum " .. definition.key)
        expect(column.width <= definition.maxWidth, label .. " respects maximum " .. definition.key)
        expectedX = expectedX + column.width + 8
        usedWidth = usedWidth + column.width
    end
    equal(layout.usedWidth, usedWidth, label .. " used width")
    equal(layout.trailingWidth, math.max(0, layout.usableWidth - usedWidth), label .. " trailing width")
    expect(usedWidth <= layout.usableWidth, label .. " fits usable width")
end

for _, mode in ipairs(modes) do
    for _, shape in ipairs({ { compact = false }, { compact = true } }) do
        local definitions = UI:GetViewColumnDefinitions(mode, shape.compact)
        for _, definition in ipairs(definitions) do
            expect(type(definition.minWidth) == "number", mode .. " minimum is configured")
            expect(type(definition.preferredWidth) == "number", mode .. " preferred width is configured")
            expect(type(definition.maxWidth) == "number", mode .. " maximum is configured")
            expect(type(definition.growWeight) == "number", mode .. " growth weight is configured")
            expect(definition.minWidth <= definition.preferredWidth, mode .. " minimum <= preferred")
            expect(definition.preferredWidth <= definition.maxWidth, mode .. " preferred <= maximum")
            expect(definition.growWeight >= 0, mode .. " growth weight is nonnegative")
            if definition.growWeight == 0 then
                equal(definition.minWidth, definition.preferredWidth, mode .. " fixed preferred width")
                equal(definition.preferredWidth, definition.maxWidth, mode .. " fixed maximum width")
            end
        end
    end

    local compactDefinitions = UI:GetViewColumnDefinitions(mode, true)
    local compactMinimum = totalFor(compactDefinitions, "minWidth")
    local compactPreferred = totalFor(compactDefinitions, "preferredWidth")
    local compactMaximum = totalFor(compactDefinitions, "maxWidth")
    expect(compactMinimum + 16 <= 662, mode .. " compact minima and row padding fit the supported narrow viewport")

    local supportedMinimumLayout = UI:GetTableColumnLayout(662, mode, true)
    validateLayout(mode, true, supportedMinimumLayout, mode .. " supported minimum viewport")

    local minimumLayout = UI:GetTableColumnLayout(compactMinimum + 16, mode, true)
    validateLayout(mode, true, minimumLayout, mode .. " exact minimum")
    expectTargetWidths(minimumLayout, compactDefinitions, "minWidth", mode .. " exact minimum")

    local preferredLayout = UI:GetTableColumnLayout(compactPreferred + 16, mode, true)
    validateLayout(mode, true, preferredLayout, mode .. " exact preferred")
    expectTargetWidths(preferredLayout, compactDefinitions, "preferredWidth", mode .. " exact preferred")

    local maximumLayout = UI:GetTableColumnLayout(compactMaximum + 16, mode, true)
    validateLayout(mode, true, maximumLayout, mode .. " exact maximum")
    expectTargetWidths(maximumLayout, compactDefinitions, "maxWidth", mode .. " exact maximum")

    local overMaximum = UI:GetTableColumnLayout(compactMaximum + 216, mode, true)
    validateLayout(mode, true, overMaximum, mode .. " over maximum")
    expectTargetWidths(overMaximum, compactDefinitions, "maxWidth", mode .. " capped maximum")
    equal(overMaximum.trailingWidth, 200, mode .. " leaves a trailing gutter after all caps")
    equal(UI:GetTableColumnLayout(compactMaximum + 216, mode, true), overMaximum, mode .. " identical layout is cached")

    local onePixelLayout = UI:GetTableColumnLayout(compactMinimum + 17, mode, true)
    local allocated = 0
    for index, definition in ipairs(compactDefinitions) do
        allocated = allocated + (onePixelLayout.columns[index].width - definition.minWidth)
    end
    equal(allocated, 1, mode .. " residual pixel is allocated exactly once")
    local widths = {}
    for index, column in ipairs(onePixelLayout.columns) do widths[index] = column.width end
    UI.columnLayoutCache[mode .. ":compact"] = nil
    local repeatedPixelLayout = UI:GetTableColumnLayout(compactMinimum + 17, mode, true)
    for index, width in ipairs(widths) do
        equal(repeatedPixelLayout.columns[index].width, width, mode .. " residual rounding is deterministic")
    end

    local weightTotal = 0
    for _, definition in ipairs(compactDefinitions) do
        weightTotal = weightTotal + definition.growWeight
    end
    local weightedLayout = UI:GetTableColumnLayout(compactMinimum + 16 + weightTotal, mode, true)
    for index, definition in ipairs(compactDefinitions) do
        equal(weightedLayout.columns[index].width, definition.minWidth + definition.growWeight,
            mode .. " applies configured growth weight to " .. definition.key)
    end

    local firstGrowableIndex
    for index, definition in ipairs(compactDefinitions) do
        if definition.growWeight > 0 and not firstGrowableIndex then
            firstGrowableIndex = index
        end
    end
    local preferredPlusOne = UI:GetTableColumnLayout(compactPreferred + 17, mode, true)
    for index, definition in ipairs(compactDefinitions) do
        local expectedWidth = definition.preferredWidth + (index == firstGrowableIndex and 1 or 0)
        equal(preferredPlusOne.columns[index].width, expectedWidth,
            mode .. " finishes preferred growth before left-to-right maximum growth " .. definition.key)
        equal(definition.width, nil, mode .. " definition width remains immutable " .. definition.key)
        equal(definition.x, nil, mode .. " definition position remains immutable " .. definition.key)
    end

    local autoCompact = UI:GetTableColumnLayout(956, mode, false)
    expect(autoCompact.compact, mode .. " uses compact columns below the breakpoint")
    local forcedCompact = UI:GetTableColumnLayout(1096, mode, true)
    expect(forcedCompact.compact, mode .. " inspector forces compact columns")

    local boundaryWide = UI:GetTableColumnLayout(1056, mode, false)
    local defaultWide = UI:GetTableColumnLayout(1096, mode, false)
    local maximumWide = UI:GetTableColumnLayout(1896, mode, false)
    validateLayout(mode, false, boundaryWide, mode .. " boundary wide")
    validateLayout(mode, false, defaultWide, mode .. " default wide")
    validateLayout(mode, false, maximumWide, mode .. " maximum wide")
    equal(boundaryWide.usedWidth, boundaryWide.usableWidth, mode .. " boundary width is fully allocated")
    equal(defaultWide.usedWidth, defaultWide.usableWidth, mode .. " default width is fully allocated")

    local growingColumns = 0
    local anyBeyondPreferred = false
    local wideDefinitions = UI:GetViewColumnDefinitions(mode, false)
    for index, definition in ipairs(wideDefinitions) do
        local boundaryColumn = boundaryWide.columns[index]
        local defaultColumn = defaultWide.columns[index]
        local maximumColumn = maximumWide.columns[index]
        expect(defaultColumn.width >= boundaryColumn.width, mode .. " grows monotonically to default " .. definition.key)
        expect(maximumColumn.width >= defaultColumn.width, mode .. " grows monotonically to maximum " .. definition.key)
        if definition.growWeight > 0 and defaultColumn.width > definition.minWidth then
            growingColumns = growingColumns + 1
        end
        if definition.growWeight > 0 and defaultColumn.width > definition.preferredWidth then
            anyBeyondPreferred = true
        end
        equal(maximumColumn.width, definition.maxWidth, mode .. " reaches wide maximum " .. definition.key)
    end
    expect(growingColumns >= 2, mode .. " grows multiple semantic columns")
    if anyBeyondPreferred then
        for index, definition in ipairs(wideDefinitions) do
            if definition.growWeight > 0 then
                expect(defaultWide.columns[index].width >= definition.preferredWidth, mode .. " completes preferred stage before maximum stage")
            end
        end
    end
    expect(maximumWide.trailingWidth > 0, mode .. " maximum-width layout keeps a trailing gutter")
end

local owned = { marker = "owned" }
local access = { marker = "access" }
local availability = { marker = "availability" }
local query = { marker = "query" }
local payload = { marker = "payload" }
local model = { marker = "model", entries = { { top = 1, bottom = 2 } } }
UI.currentOwned = owned
UI.currentAccess = access
UI.currentAvailabilitySnapshot = availability
UI.currentViewQueryCache = query
UI.currentFilterPayload = payload
UI.renderModel = model
UI.renderModelSerial = 77
UI.columnLayoutCache = {}
for width = 678, 1896, 11 do
    for _, mode in ipairs(modes) do
        UI:GetTableColumnLayout(width, mode, false)
        UI:GetTableColumnLayout(width, mode, true)
    end
end
local cacheEntries = 0
for _ in pairs(UI.columnLayoutCache) do cacheEntries = cacheEntries + 1 end
expect(cacheEntries <= 12, "column cache is bounded by mode and shape")
local cachedPlanner = UI:GetTableColumnLayout(1096, "planner", false)
equal(UI:GetTableColumnLayout(1096, "planner", false), cachedPlanner, "same mode and width reuse cached layout")
local entriesBeforeReplacement = cacheEntries
expect(UI:GetTableColumnLayout(1100, "planner", false) ~= cachedPlanner, "new width replaces cached layout")
cacheEntries = 0
for _ in pairs(UI.columnLayoutCache) do cacheEntries = cacheEntries + 1 end
equal(cacheEntries, entriesBeforeReplacement, "replacement does not grow the cache")
for index = 1, 30 do
    UI:GetTableColumnLayout(1096, "unknown-" .. tostring(index), false)
end
cacheEntries = 0
for _ in pairs(UI.columnLayoutCache) do cacheEntries = cacheEntries + 1 end
equal(cacheEntries, entriesBeforeReplacement, "unknown modes share the phase cache entry")
equal(UI.currentOwned, owned, "column layout keeps ownership cache")
equal(UI.currentAccess, access, "column layout keeps access cache")
equal(UI.currentAvailabilitySnapshot, availability, "column layout keeps availability cache")
equal(UI.currentViewQueryCache, query, "column layout keeps query cache")
equal(UI.currentFilterPayload, payload, "column layout keeps filter payload")
equal(UI.renderModel, model, "column layout keeps render model")
equal(UI.renderModelSerial, 77, "column layout keeps model serial")
equal(UI.renderModel.entries[1].top, 1, "column layout keeps model row top")
equal(UI.renderModel.entries[1].bottom, 2, "column layout keeps model row bottom")
''')

    def test_header_rows_badges_actions_and_hover_share_resolved_geometry(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local function frame(parent, width, height)
    local value = {
        parent = parent,
        width = width or 0,
        height = height or 0,
        points = {},
        scripts = {},
        shown = true,
        frameLevel = 1,
    }
    function value:GetParent() return self.parent end
    function value:SetParent(newParent) self.parent = newParent end
    function value:Show() self.shown = true end
    function value:Hide() self.shown = false end
    function value:IsShown() return self.shown end
    function value:ClearAllPoints() self.points = {} end
    function value:SetPoint(...) table.insert(self.points, { ... }) end
    function value:SetAllPoints(...) self.allPoints = { ... } end
    function value:SetSize(newWidth, newHeight) self.width, self.height = newWidth, newHeight end
    function value:SetWidth(newWidth) self.width = newWidth end
    function value:SetHeight(newHeight) self.height = newHeight end
    function value:GetWidth() return self.width end
    function value:GetHeight() return self.height end
    function value:GetFrameLevel() return self.frameLevel end
    function value:SetFrameLevel(newLevel) self.frameLevel = newLevel end
    function value:EnableMouse(enabled) self.mouseEnabled = enabled end
    function value:SetScript(event, callback) self.scripts[event] = callback end
    function value:GetScript(event) return self.scripts[event] end
    function value:SetWordWrap(enabled) self.wordWrap = enabled end
    function value:SetJustifyH(justify) self.justify = justify end
    function value:SetTextColor(...) self.textColor = { ... } end
    function value:SetText(text) self.text = text end
    function value:CreateFontString()
        return frame(self)
    end
    return value
end

CreateFrame = function(_, _, parent) return frame(parent) end
BigBiSList.Widgets = {
    CreateItemRow = function(_, parent, height)
        local row = frame(parent, 0, height)
        row.highlight = frame(row)
        return row
    end,
    CreateIconButton = function(_, parent, size)
        return frame(parent, size, size)
    end,
    CreateWrappedLabel = function(_, parent, text)
        local label = frame(parent)
        label:SetText(text)
        return label
    end,
    CreateLabel = function(_, parent, text)
        local label = frame(parent)
        label:SetText(text)
        return label
    end,
    CreateTextButton = function(_, parent, text, width, height, callback)
        local button = frame(parent, width, height)
        button.label = frame(button)
        button.label:SetText(text)
        button:SetScript("OnClick", callback)
        return button
    end,
}

local inspectorVisible = false
UI.contentScroll = frame(nil, 1096, 500)
UI.GetViewState = function() return {} end
UI.IsInspectorVisible = function() return inspectorVisible end
UI.CountPerformance = function() end
UI.GetRowSlotDisplay = function() return "Head" end
UI.GetRowRecommendationText = function() return "Best in slot" end
UI.GetWishlistExpansionText = function() return "PR BiS" end
UI.GetGearUsefulThrough = function() return "Phase 5" end
UI.GetRowOwnershipState = function() return "missing" end
UI.GetRowAcquisitionDisplay = function() return "Raid", "Long Boss Name", "ready" end
UI.ShowAcquisitionTooltip = function() end
UI.SetItemButton = function(_, _, _, nameText, name) nameText:SetText(name) end
UI.CreateRankBadge = function(_, parent, _, _, _, _, existing) return existing or frame(parent) end
UI.CreateOwnershipBadge = function(_, parent, _, _, existing) return existing or frame(parent) end
UI.CreateAccessBadge = function(_, parent, _, _, existing) return existing or frame(parent) end
BigBiSList.GetItemData = function() return {} end
BigBiSList.GetCharacterDB = function() return { wishlist = {} } end

local narrowParent = frame(nil, 320, 500)
equal(UI:GetTableViewportWidth(narrowParent, 400), 1092, "canonical width comes from the live scroll frame")
narrowParent.width = 1800
equal(UI:GetTableViewportWidth(narrowParent, 400), 1092, "header and row parent widths cannot diverge the table")

local function pointX(widget)
    for _, point in ipairs(widget.points or {}) do
        if point[1] == "TOPLEFT" then
            return point[4]
        end
    end
end

local function expectGeometry(widget, column, label)
    expect(widget, label .. " exists")
    equal(pointX(widget), column.x, label .. " x")
    equal(widget.width, column.width, label .. " width")
end

local modes = { "planner", "phase", "leveling", "enhance", "wishlist", "gear" }
for _, compact in ipairs({ false, true }) do
    inspectorVisible = compact
    for _, mode in ipairs(modes) do
        local parent = frame(nil, compact and 430 or 1600, 500)
        local header = UI:CreateListColumnHeader(parent, 0, mode)
        local row = UI:CreateDataRow(parent, 0, {
            item_id = 12345,
            entity_type = "item",
            name = "An Item With A Long Name",
            rank_group = "bis",
            item = {},
        }, mode, nil, 74)
        local layout = header.columnLayout
        equal(row.columnLayout, layout, mode .. " " .. tostring(compact) .. " header and row share cached layout")

        for index, column in ipairs(layout.columns) do
            expectGeometry(header.columnButtons[index], column, mode .. " header " .. column.key)
            if column.key == "item" then
                equal(pointX(row.iconButton), column.x, mode .. " item icon x")
            elseif column.key == "rank" then
                expectGeometry(row.rankBadge, column, mode .. " rank badge")
            elseif column.key == "owned" then
                expectGeometry(row.ownershipBadge, column, mode .. " ownership badge")
            elseif column.key == "access" then
                expectGeometry(row.accessBadge, column, mode .. " access badge")
            elseif column.key == "action" then
                expectGeometry(row.actionButton, column, mode .. " action")
            else
                expectGeometry(row.cells[column.key], column, mode .. " cell " .. column.key)
            end
        end

        local sourceColumn = layout.acquisition or layout.source
        if sourceColumn then
            local lastSourceColumn = layout.location or sourceColumn
            equal(pointX(row.sourceHover), sourceColumn.x, mode .. " acquisition hover x")
            equal(row.sourceHover.width,
                (lastSourceColumn.x + lastSourceColumn.width) - sourceColumn.x,
                mode .. " acquisition hover spans resolved source columns")
        end
    end
end
''')

    def test_layout_only_resize_rebinds_viewport_without_rebuilding_data(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local scrollWidth = 1096
local inspectorVisible = false
local created = 0
local bound = 0
local performance = {}

local function pooledFrame()
    local value = {}
    function value:Hide() self.hidden = true end
    function value:ClearAllPoints() self.cleared = true end
    return value
end

local model = {
    entries = {
        { kind = "row", top = 0, bottom = 46, rowHeight = 46, mode = "planner", data = { id = 1 } },
        { kind = "row", top = 50, bottom = 96, rowHeight = 46, mode = "planner", data = { id = 2 } },
        { kind = "row", top = 100, bottom = 146, rowHeight = 46, mode = "planner", data = { id = 3 } },
    },
}
local owned = { marker = "owned" }
local access = { marker = "access" }
local availability = { marker = "availability" }
local query = { marker = "query" }
local payload = { marker = "payload" }

UI.frame = { IsShown = function() return true end }
UI.renderModel = model
UI.renderModelSerial = 9
UI.stickyHeaderMode = "planner"
UI.contentScroll = {
    GetVerticalScroll = function() return 0 end,
    GetHeight = function() return 180 end,
    GetWidth = function() return scrollWidth end,
}
UI.contentListLayer = {}
UI.contentChild = UI.contentListLayer
UI.currentOwned = owned
UI.currentAccess = access
UI.currentAvailabilitySnapshot = availability
UI.currentViewQueryCache = query
UI.currentFilterPayload = payload
UI.IsInspectorVisible = function() return inspectorVisible end
UI.ApplyBodyLayout = function() end
UI.SetStickyHeaderMode = function(self, mode)
    self.stickyHeaderMode = mode
    self.lastHeaderLayout = self:GetTableColumnLayout(self:GetTableViewportWidth(self.contentListLayer, scrollWidth), mode, inspectorVisible)
end
UI.CountPerformance = function(_, key, amount)
    performance[key] = (performance[key] or 0) + (amount or 1)
end
UI.CreateDataRow = function(_, _, _, _, _, reusable)
    bound = bound + 1
    if not reusable then
        created = created + 1
        reusable = pooledFrame()
    end
    return reusable
end
UI.BuildOwnedItems = function() error("layout must not rebuild ownership") end
UI.BuildAccessState = function() error("layout must not rebuild access") end
UI.BuildFilterPayload = function() error("layout must not rebuild filters") end
UI.BuildViewQuery = function() error("layout must not rebuild queries") end

UI:RefreshLayout("initial")
equal(created, 3, "initial wide viewport creates one widget per visible row")
equal(bound, 3, "initial wide viewport binds visible rows")
local initialRange = UI.renderRangeKey
UI:UpdateVirtualList(false)
equal(bound, 3, "unchanged viewport geometry does not rebind")

UI:Invalidate("layout", "wider")
scrollWidth = 1200
UI:RefreshLayout("wider")
expect(UI.renderRangeKey ~= initialRange, "width change updates the viewport geometry signature")
equal(created, 3, "wide resize reuses the warmed wide row pool")
equal(bound, 6, "wide resize rebinds visible rows")

inspectorVisible = true
UI:Invalidate("layout", "inspector-open")
UI:RefreshLayout("inspector-open")
equal(created, 6, "first compact shape creates one compact widget set")
equal(bound, 9, "inspector transition rebinds compact rows")
expect(UI.lastHeaderLayout.compact, "inspector forces the compact header shape")

inspectorVisible = false
UI:Invalidate("layout", "inspector-close")
UI:RefreshLayout("inspector-close")
equal(created, 6, "returning to wide shape reuses the warmed pool")
equal(bound, 12, "returning to wide shape rebinds rows")
expect(not UI.lastHeaderLayout.compact, "closing inspector restores the wide header shape")

equal(UI.renderModel, model, "layout refresh keeps render model identity")
equal(UI.renderModelSerial, 9, "layout refresh keeps model serial")
equal(model.entries[1].top, 0, "layout refresh keeps row top bounds")
equal(model.entries[3].bottom, 146, "layout refresh keeps row bottom bounds")
equal(UI.currentOwned, owned, "layout refresh keeps ownership cache")
equal(UI.currentAccess, access, "layout refresh keeps access cache")
equal(UI.currentAvailabilitySnapshot, availability, "layout refresh keeps availability cache")
equal(UI.currentViewQueryCache, query, "layout refresh keeps query corpus")
equal(UI.currentFilterPayload, payload, "layout refresh keeps filter payload")
equal(performance.ownershipBuilds, nil, "layout path records no ownership builds")
equal(performance.accessBuilds, nil, "layout path records no access builds")
equal(performance.availabilityBuilds, nil, "layout path records no availability builds")
equal(performance.dataBuilds, nil, "layout path records no data builds")
''')

    def test_sticky_header_and_body_layout_are_geometry_idempotent(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local function fakeFrame(height)
    local frame = {
        clearCount = 0,
        pointCount = 0,
        showCount = 0,
        hideCount = 0,
        height = height or 100,
    }
    function frame:ClearAllPoints() self.clearCount = self.clearCount + 1 end
    function frame:SetPoint(...) self.pointCount = self.pointCount + 1 end
    function frame:Show() self.showCount = self.showCount + 1 end
    function frame:Hide() self.hideCount = self.hideCount + 1 end
    function frame:GetHeight() return self.height end
    return frame
end

UI.contentHeaderHost = fakeFrame()
UI.contentScroll = fakeFrame()
UI.contentPanel = fakeFrame()
UI.CreateListColumnHeader = function(_, _, _, _, header)
    return header or fakeFrame(), 22
end

UI:SetStickyHeaderMode("planner")
local stickyClears = UI.contentScroll.clearCount
UI:SetStickyHeaderMode("planner")
equal(UI.contentScroll.clearCount, stickyClears, "same sticky mode does not re-anchor scroll frame")
UI:SetStickyHeaderMode(nil)
equal(UI.contentScroll.clearCount, stickyClears + 1, "sticky mode transition updates geometry once")
UI:SetStickyHeaderMode(nil)
equal(UI.contentScroll.clearCount, stickyClears + 1, "same collapsed mode remains idempotent")

local inspectorVisible = false
UI.body = fakeFrame()
UI.details = fakeFrame()
UI.contentRegion = fakeFrame()
UI.contentPanel = fakeFrame()
UI.listToolbar = fakeFrame()
UI.filterDrawer = fakeFrame(140)
UI.filterDrawerOpen = false
UI.inspectorToggleButton = { label = { SetText = function() end } }
UI.ViewSupportsFilters = function() return true end
UI.IsInspectorVisible = function() return inspectorVisible end
UI.RefreshFilterDrawer = function() error("closed drawer should not be rebuilt") end
UI.GetActiveFilterChips = function() return {} end

UI:ApplyBodyLayout()
local regionClears = UI.contentRegion.clearCount
local panelClears = UI.contentPanel.clearCount
UI:ApplyBodyLayout()
equal(UI.contentRegion.clearCount, regionClears, "same body state does not re-anchor content region")
equal(UI.contentPanel.clearCount, panelClears, "same body state does not re-anchor content panel")

inspectorVisible = true
UI:ApplyBodyLayout()
equal(UI.contentRegion.clearCount, regionClears + 1, "inspector transition updates region once")
equal(UI.contentPanel.clearCount, panelClears + 1, "inspector transition updates panel once")
UI:ApplyBodyLayout()
equal(UI.contentRegion.clearCount, regionClears + 1, "stable inspector state stays idempotent")
equal(UI.contentPanel.clearCount, panelClears + 1, "stable inspector panel stays idempotent")
''')

    def test_column_header_and_active_filters_are_fixed_outside_the_scroll_model(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local model = UI:NewListRenderModel()
UI:AddListSection(model, "First", "phase")
UI:AddListRow(model, { item_id = 1 }, "phase")
UI:AddListSection(model, "Second", "phase")
UI:AddListRow(model, { item_id = 2 }, "phase")

equal(model.columnMode, "phase", "model records one fixed grid-header mode")
local sections, columns, filters = 0, 0, 0
for _, entry in ipairs(model.entries) do
    if entry.kind == "section" then sections = sections + 1 end
    if entry.kind == "columns" then columns = columns + 1 end
    if entry.kind == "filters" then filters = filters + 1 end
end
equal(sections, 2, "group headings remain in the virtual list")
equal(columns, 0, "column headers are not duplicated in the virtual list")
equal(filters, 0, "active filters are not part of the scrolling model")

UI.contentRegion = { GetWidth = function() return 400 end }
UI.contentChild = { GetWidth = function() return 220 end }
UI.contentScroll = { GetWidth = function() return 220 end }
local boundaryChips = { { label = "abcdefghij" }, { label = "abcdefghij" } }
local chipLayout = UI:GetActiveFilterChipLayout(UI.contentRegion, boundaryChips)
equal(chipLayout.rows, 1, "fixed bar wrapping uses the fixed container width")
equal(chipLayout.height, 54, "one rendered chip row has one-row height")
equal(UI:ActiveFilterBarHeight(boundaryChips), chipLayout.height, "measured and rendered chip layouts share one calculation")
equal(chipLayout.positions[1].y, chipLayout.positions[2].y, "boundary chips render on the measured row")

local function frame()
    local value = { points = {}, shown = false }
    function value:ClearAllPoints() self.points = {} end
    function value:SetPoint(...) table.insert(self.points, { ... }) end
    function value:Show() self.shown = true end
    function value:Hide() self.shown = false end
    return value
end

UI.body = frame()
UI.details = frame()
UI.contentRegion = frame()
UI.contentPanel = frame()
UI.listToolbar = frame()
UI.filterDrawer = frame()
UI.fixedActiveFilterBar = frame()
UI.inspectorToggleButton = { label = { SetText = function() end } }
UI.filterDrawerOpen = false
UI.ViewSupportsFilters = function() return true end
UI.IsInspectorVisible = function() return false end
UI.RefreshFixedActiveFilterBar = function() return 54 end

UI:ApplyBodyLayout()
expect(UI.fixedActiveFilterBar.shown, "active-filter bar is fixed and visible")
equal(UI.fixedActiveFilterBar.points[1][2], UI.listToolbar, "active filters anchor below the toolbar")
equal(UI.fixedActiveFilterBar.points[1][3], "BOTTOMLEFT", "active filters use the toolbar bottom edge")
equal(UI.contentPanel.points[1][2], UI.fixedActiveFilterBar, "grid anchors below active filters")
equal(UI.contentPanel.points[1][3], "BOTTOMLEFT", "grid starts after the fixed filter bar")
''')

    def test_full_and_layout_refresh_schedulers_coalesce_without_reentry(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local timers = {}
C_Timer = {
    After = function(_, callback)
        table.insert(timers, callback)
    end,
}
UI.frame = { IsShown = function() return true end }
UI.CountPerformance = function() end

local fullRefreshes = 0
local layoutRefreshes = 0
UI.Refresh = function() fullRefreshes = fullRefreshes + 1 end
UI.RefreshLayout = function() layoutRefreshes = layoutRefreshes + 1 end

UI:ScheduleRefresh(0, "first")
UI:ScheduleRefresh(0, "duplicate")
equal(#timers, 1, "full refresh requests coalesce")
table.remove(timers, 1)()
equal(fullRefreshes, 1, "one coalesced full refresh executes")

UI:ScheduleLayoutRefresh("first-layout")
UI:ScheduleLayoutRefresh("duplicate-layout")
equal(#timers, 1, "layout refresh requests coalesce")
table.remove(timers, 1)()
equal(layoutRefreshes, 1, "one coalesced layout refresh executes")
equal(fullRefreshes, 1, "layout work does not execute a full refresh")

UI.refreshInProgress = true
UI:ScheduleRefresh(0, "during-refresh")
expect(UI.refreshPending, "refresh requested during refresh is marked pending")
equal(#timers, 0, "refresh is never entered recursively")
UI:ScheduleLayoutRefresh("layout-during-refresh")
expect(UI.layoutPending, "layout requested during refresh is marked pending")
equal(#timers, 0, "layout work is never entered recursively")
''')

    def test_refresh_guard_is_released_after_a_renderer_error(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
UI.frame = { IsShown = function() return true end }
UI.CountPerformance = function() end
UI.GetSelection = function() return { tab = "Settings" } end
UI.RefreshControls = function() end
UI.IsInspectorVisible = function() return false end
UI.ValidateSelection = function() error("intentional renderer setup failure") end

local firstOk = pcall(function() UI:Refresh("error-test") end)
expect(not firstOk, "refresh propagates renderer errors")
expect(not UI.refreshInProgress, "refresh guard is always released after an error")
expect(UI.dirtyDomains.query, "failed refresh remains query-dirty for a later retry")

local rendered = 0
UI.ValidateSelection = function() end
UI.RenderSettingsTab = function() rendered = rendered + 1 end
local retryOk = pcall(function() UI:Refresh("retry-test") end)
expect(retryOk, "a later refresh can retry after an error")
equal(rendered, 1, "retry reaches the renderer once")
expect(not UI.refreshInProgress, "successful retry leaves the guard clear")
''')

    def test_virtual_list_realizes_only_viewport_and_overscan_entries(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local scrollTop = 0
local realized = {}
local releases = 0
UI.renderModelSerial = 1
UI.renderModel = {
    entries = {
        { kind = "row", top = 0, bottom = 50, height = 50, rowHeight = 46, mode = "phase", data = { id = 1 } },
        { kind = "row", top = 100, bottom = 150, height = 50, rowHeight = 46, mode = "phase", data = { id = 2 } },
        { kind = "row", top = 240, bottom = 290, height = 50, rowHeight = 46, mode = "phase", data = { id = 3 } },
        { kind = "row", top = 500, bottom = 550, height = 50, rowHeight = 46, mode = "phase", data = { id = 4 } },
    },
}
UI.contentScroll = {
    GetVerticalScroll = function() return scrollTop end,
    GetHeight = function() return 100 end,
    GetWidth = function() return 760 end,
}
UI.contentListLayer = { GetWidth = function() return 760 end }
UI.contentChild = UI.contentListLayer
UI.stickyHeaderMode = "phase"
UI.IsInspectorVisible = function() return false end
UI.ReleaseRenderFrames = function() releases = releases + 1 end
UI.AcquireRenderFrame = function() return {} end
UI.TrackRenderFrame = function() end
UI.CountPerformance = function() end
UI.CreateDataRow = function(_, _, _, data, _, frame)
    table.insert(realized, data.id)
    return frame
end

UI:UpdateVirtualList(true)
equal(table.concat(realized, ","), "1,2", "initial viewport uses 120px overscan without rendering distant rows")
equal(releases, 1, "first viewport realizes once")

UI:UpdateVirtualList(false)
equal(table.concat(realized, ","), "1,2", "unchanged viewport does no row work")
equal(releases, 1, "unchanged viewport does not recycle frames")

scrollTop = 400
realized = {}
UI:UpdateVirtualList(false)
equal(table.concat(realized, ","), "3,4", "scrolling realizes the new viewport and overscan only")
equal(releases, 2, "scrolling updates viewport without a full model rebuild")
''')

    def test_virtual_widget_pool_plateaus_after_a_500_row_scroll(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local scrollTop = 0
local created = 0
local maximumActive = 0
local entries = {}
for index = 1, 500 do
    local top = (index - 1) * 50
    table.insert(entries, {
        kind = "row",
        top = top,
        bottom = top + 46,
        height = 50,
        rowHeight = 46,
        mode = index % 2 == 0 and "phase" or "planner",
        data = { id = index },
    })
end

UI.renderModelSerial = 1
UI.renderModel = { entries = entries }
UI.contentScroll = {
    GetVerticalScroll = function() return scrollTop end,
    GetHeight = function() return 100 end,
    GetWidth = function() return 760 end,
}
UI.contentListLayer = { GetWidth = function() return 760 end }
UI.contentChild = UI.contentListLayer
UI.stickyHeaderMode = "phase"
UI.IsInspectorVisible = function() return false end
UI.CountPerformance = function() end

local function bind(_, _, _, _, _, frame)
    if not frame then
        created = created + 1
        frame = {}
        function frame:Hide() end
        function frame:ClearAllPoints() end
    end
    return frame
end
UI.CreateDataRow = bind

local function sweep(first, last, step)
    for offset = first, last, step do
        scrollTop = offset
        UI:UpdateVirtualList(false)
        maximumActive = math.max(maximumActive, #(UI.activeRenderFrames or {}))
    end
end

sweep(0, 24900, 100)
local warmCreated = created
sweep(24900, 0, -100)
equal(created, warmCreated, "repeated scrolling reuses the warmed row pools")
expect(maximumActive <= 10, "viewport realization stays bounded by viewport plus 120px overscan")
expect(warmCreated <= 20, "separate row-shape pools remain bounded")
''')

    def test_failed_virtual_bind_hides_and_recovers_the_new_widget(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local children = {}
local failedFrame
UI.renderModelSerial = 1
UI.renderModel = {
    entries = {
        { kind = "row", top = 0, bottom = 46, height = 50, rowHeight = 46, mode = "phase", data = {} },
    },
}
UI.contentScroll = {
    GetVerticalScroll = function() return 0 end,
    GetHeight = function() return 100 end,
    GetWidth = function() return 760 end,
}
UI.contentListLayer = {
    GetWidth = function() return 760 end,
    GetChildren = function() return unpack(children) end,
}
UI.contentChild = UI.contentListLayer
UI.stickyHeaderMode = "phase"
UI.IsInspectorVisible = function() return false end
UI.CountPerformance = function() end
local bindCalls = 0
UI.CreateDataRow = function(_, _, _, _, _, frame)
    bindCalls = bindCalls + 1
    if bindCalls == 1 then
        failedFrame = { __bigBisManaged = true, hidden = false }
        function failedFrame:Hide() self.hidden = true end
        function failedFrame:ClearAllPoints() self.cleared = true end
        table.insert(children, failedFrame)
        error("intentional virtual bind failure")
    end
    frame.hidden = false
    return frame
end

local ok = pcall(function() UI:UpdateVirtualList(true) end)
expect(not ok, "virtual bind errors still propagate")
expect(failedFrame.hidden, "failed widget is hidden immediately")
expect(failedFrame.cleared, "failed widget anchors are cleared")
equal(#(UI.activeRenderFrames or {}), 0, "failed widget is not left active")
local recovered = #UI:GetRenderPool("row:phase:wide") + #UI:GetRenderPool("row:phase:compact")
equal(recovered, 1, "fully initialized failed widget returns to its shape pool")
equal(UI.renderRangeKey, nil, "failed bind does not commit the viewport range")
UI:UpdateVirtualList()
equal(bindCalls, 2, "same-range retry rebinds after a transient error")
equal(#(UI.activeRenderFrames or {}), 1, "same-range retry realizes the recovered widget")
''')

    def test_filter_drawer_does_not_hide_still_applicable_dropdowns(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local closedMenus = 0
BigBiSList.Widgets = {
    CloseDropdownMenus = function() closedMenus = closedMenus + 1 end,
}

local function layoutObject(shown, width)
    local object = {
        shown = shown,
        width = width or 760,
        hideCount = 0,
        showCount = 0,
        refreshCount = 0,
    }
    function object:IsShown() return self.shown end
    function object:Show() self.shown = true; self.showCount = self.showCount + 1 end
    function object:Hide() self.shown = false; self.hideCount = self.hideCount + 1 end
    function object:ClearAllPoints() end
    function object:SetPoint(...) end
    function object:SetHeight(value) self.height = value end
    function object:GetHeight() return self.height or 0 end
    function object:GetWidth() return self.width end
    function object:Refresh() self.refreshCount = self.refreshCount + 1 end
    return object
end

local source = layoutObject(true)
local obsolete = layoutObject(true)
UI.filterDrawer = layoutObject(true, 760)
UI.filterDrawerControls = { source = source, obsolete = obsolete }
UI.filterItemHeader = layoutObject(false)
UI.filterAcquisitionHeader = layoutObject(false)
UI.clearFiltersButton = layoutObject(true)
UI.GetVisibleFilterControlKeys = function() return { "source" } end

UI:RefreshFilterDrawer()
equal(source.hideCount, 0, "applicable dropdown is never hidden during layout")
equal(source.refreshCount, 1, "applicable dropdown is refreshed")
equal(obsolete.hideCount, 1, "newly inapplicable dropdown is hidden once")
equal(closedMenus, 1, "open menu is closed only when a control is removed")

UI:RefreshFilterDrawer()
equal(source.hideCount, 0, "no-op drawer refresh preserves dropdown owner visibility")
equal(obsolete.hideCount, 1, "already hidden control is not hidden again")
equal(closedMenus, 1, "no-op drawer refresh does not close menus")
''')

    def test_item_loads_are_shared_and_stale_row_bindings_are_ignored(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("UI.lua")

local UI = BigBiSList.UI
local loaded = {}
local callbacks = {}
local createCounts = {}

function GetItemInfo(itemId)
    if not loaded[itemId] then
        return nil
    end
    return "Loaded " .. tostring(itemId), "item:" .. tostring(itemId), 4, nil, nil, nil, nil, nil, nil, "Icon" .. tostring(itemId)
end
function GetItemQualityColor() return 0.5, 0.6, 0.7 end
Item = {}
function Item:CreateFromItemID(itemId)
    createCounts[itemId] = (createCounts[itemId] or 0) + 1
    local item = {}
    function item:ContinueOnItemLoad(callback) callbacks[itemId] = callback end
    function item:GetItemName() return "Loaded " .. tostring(itemId) end
    function item:GetItemLink() return "item:" .. tostring(itemId) end
    function item:GetItemIcon() return "Icon" .. tostring(itemId) end
    return item
end

local function fakeButton()
    local button = { scripts = {}, icon = {} }
    function button.icon:SetDesaturated(value) self.desaturated = value end
    function button.icon:SetTexture(value) self.texture = value end
    function button:SetScript(event, callback) self.scripts[event] = callback end
    return button
end
local function fakeText()
    local label = {}
    function label:SetText(value) self.text = value end
    function label:SetTextColor(...) self.color = { ... } end
    return label
end

local firstButton, firstText = fakeButton(), fakeText()
local secondButton, secondText = fakeButton(), fakeText()
UI:SetItemButton(firstButton, 100, firstText, "Fallback 100", 2, {}, "phase")
UI:SetItemButton(secondButton, 100, secondText, "Fallback 100", 2, {}, "phase")
equal(createCounts[100], 1, "concurrent rows share one item load request")

UI:SetItemButton(firstButton, 200, firstText, "Fallback 200", 2, {}, "phase")
equal(createCounts[200], 1, "new item starts one load request")
loaded[100] = true
callbacks[100]()
equal(firstText.text, "Fallback 200", "late callback cannot overwrite a recycled row")
equal(firstButton.icon.texture, "Interface\\Icons\\INV_Misc_QuestionMark", "late callback cannot overwrite recycled icon")
equal(secondText.text, "Loaded 100", "still-bound row receives shared item data")
equal(secondButton.icon.texture, "Icon100", "still-bound row receives shared icon")

loaded[200] = true
callbacks[200]()
equal(firstText.text, "Loaded 200", "current binding receives its item data")
equal(firstButton.icon.texture, "Icon200", "current binding receives its icon")

UI:SetSpellButton(firstButton, 300, firstText, "Fallback Spell 300", {}, "enhance")
equal(firstText.text, "Fallback Spell 300", "item-to-spell reuse replaces the pooled item fallback")
equal(firstButton.entityType, "spell", "pooled entity scripts dispatch the current entity type")
UI:SetItemButton(firstButton, 200, firstText, "Fallback 200", 2, {}, "phase")
equal(firstText.text, "Loaded 200", "spell-to-item reuse binds cached item presentation immediately")
equal(firstButton.entityType, "item", "pooled entity scripts return to item dispatch")

local inspectorCalls = 0
UI.ShowInspectorFor = function() inspectorCalls = inspectorCalls + 1 end
local tokenBeforeEmpty = firstButton.itemBindToken
UI:ResetEntityButton(firstButton, firstText, "Empty")
equal(firstButton.itemBindToken, tokenBeforeEmpty + 1, "empty binding invalidates pending item callbacks")
equal(firstButton.entityType, nil, "empty binding clears entity type")
equal(firstButton.entityId, nil, "empty binding clears entity id")
equal(firstButton.itemLink, nil, "empty binding clears item link")
equal(firstButton.spellLink, nil, "empty binding clears spell link")
equal(firstButton.detailData, nil, "empty binding clears inspector data")
equal(firstText.text, "Empty", "empty binding replaces the pooled entity name")
firstButton.scripts.OnClick(firstButton, "RightButton")
equal(inspectorCalls, 0, "empty pooled icon cannot open the previous inspector")
''')

    def test_v16_defaults_expose_mode_view_and_inspector_state(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("Config.lua")
BigBiSListDB = nil
BigBiSListCharDB = nil
BigBiSList:EnsureDatabase()

equal(BigBiSListDB.profile.defaultsVersion, 16, "profile defaults version")
equal(BigBiSListCharDB.defaultsVersion, 16, "character defaults version")
equal(BigBiSList:GetContentMode(), "endgame", "default content mode")
equal(BigBiSList:GetSelection().phase, "PR", "stored endgame phase")
equal(BigBiSList:GetEffectivePhaseKey(), "PR", "effective endgame phase")
equal(BigBiSList:GetSelection().lastTabs.endgame, "Upgrades", "default endgame tab")
equal(BigBiSList:GetSelection().lastTabs.leveling, "Gear Guide", "default leveling tab")
equal(BigBiSList:GetViewState("BiS List").groupBy, "slot", "BiS grouping")
equal(BigBiSList:GetViewState("Gear Guide").groupBy, "slot", "guide grouping")
equal(BigBiSList:GetViewState("Wishlist").sort, "priority", "wishlist sort")
expect(not BigBiSList:IsInspectorVisible(), "inspector defaults collapsed")

BigBiSList:SetInspectorVisible(true)
expect(BigBiSList:IsInspectorVisible(), "inspector visibility is persisted")
''')

    def test_legacy_leveling_selection_migrates_without_losing_membership_or_filters(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("Config.lua")
BigBiSListDB = {
    profile = {
        defaultsVersion = 15,
        window = { inspectorVisible = false },
    },
}
BigBiSListCharDB = {
    defaultsVersion = 15,
    selectedClass = "Hunter",
    selectedSpec = "Survival",
    selectedPhase = "LEVELING",
    selectedTab = "Wishlist",
    lastDetectedPhase = "T5",
    selection = {
        class = "Hunter",
        spec = "Survival",
        phase = "LEVELING",
        endgamePhase = "SWP",
        tab = "Wishlist",
    },
    leveling = {
        selectedLevel = 42,
        lastDetectedLevel = 42,
        manualLevel = true,
    },
    filters = {
        search = "badge",
        sourceTypes = { vendor = true },
        upgradeMode = "all",
        longevity = "long",
    },
    wishlist = { ["29121"] = true },
    ignoredItems = { ["31332"] = true },
}

BigBiSList:EnsureDatabase()
local selection = BigBiSList:GetSelection()
equal(selection.mode, "leveling", "legacy mode")
equal(selection.phase, "SWP", "recovered endgame phase")
expect(selection.phase ~= "LEVELING", "LEVELING is not stored as the phase")
equal(selection.tab, "Wishlist", "legacy leveling tab")
equal(selection.lastTabs.leveling, "Wishlist", "remembered leveling tab")
equal(BigBiSList:GetEffectivePhaseKey(), "LEVELING", "effective leveling data phase")
equal(BigBiSList:GetSelectedLevelingLevel(), 42, "manual leveling level")
equal(BigBiSListCharDB.filters.search, "badge", "search survives")
expect(BigBiSListCharDB.filters.sourceTypes.vendor, "faceted filter survives")
expect(BigBiSListCharDB.wishlist["29121"], "wishlist membership survives")
expect(BigBiSListCharDB.ignoredItems["31332"], "hidden membership survives")
equal(BigBiSList:GetViewState("Upgrades").upgradeMode, "all", "upgrade mode migrates")
equal(BigBiSList:GetViewState("Upgrades").usefulness, "long", "usefulness migrates")
expect(not BigBiSList:IsInspectorVisible(), "inspector preference survives")

BigBiSList:SetContentMode("endgame")
equal(selection.tab, "Upgrades", "endgame default tab")
equal(BigBiSList:GetEffectivePhaseKey(), "SWP", "restored endgame data phase")
BigBiSList:SetSelection(nil, nil, "SWP", "BiS List")
equal(selection.tab, "By Slot", "display tab aliases remain stable internally")
BigBiSList:SetContentMode("leveling")
equal(selection.tab, "Wishlist", "leveling tab restored")
BigBiSList:SetSelection(nil, nil, nil, "My Gear")
equal(selection.tab, "Equipped", "My Gear alias")
BigBiSList:SetContentMode("endgame")
equal(selection.tab, "By Slot", "endgame tab restored")
BigBiSList:SetContentMode("leveling")
equal(selection.tab, "Equipped", "updated leveling tab restored")
equal(BigBiSList:GetEffectivePhaseKey(), "LEVELING", "mode switch keeps effective key")
''')

    def test_legacy_tabs_are_normalized_for_leveling_mode(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("Config.lua")

local function migratedTab(tabName)
    BigBiSListDB = { profile = { defaultsVersion = 15 } }
    BigBiSListCharDB = {
        defaultsVersion = 15,
        selectedPhase = "LEVELING",
        selectedTab = tabName,
        lastDetectedPhase = "T4",
        selection = {
            phase = "LEVELING",
            endgamePhase = "T4",
            tab = tabName,
        },
    }
    BigBiSList:EnsureDatabase()
    return BigBiSList:GetSelection().tab
end

equal(migratedTab("Upgrades"), "Gear Guide", "upgrades becomes guide")
equal(migratedTab("By Slot"), "Gear Guide", "BiS list becomes guide")
equal(migratedTab("Enhance"), "Gear Guide", "enhancements becomes guide")
equal(migratedTab("Wishlist"), "Wishlist", "wishlist remains available")
equal(migratedTab("Equipped"), "Equipped", "gear remains available")
equal(migratedTab("Settings"), "Settings", "settings remains available")
''')

    def test_vendor_routes_merge_format_classify_and_group_for_the_inspector(self):
        self.run_lua(r'''
BigBiSList = {}
BigBiSListData = {
    classes = {},
    phases = {},
    items = {
        {
            id = 900001,
            name = "Acquisition Model Fixture",
            quality = "rare",
            primary_source = {
                type = "vendor",
                entity_id = 12,
                vendor_id = 12,
                entity_name = "Reported Seller",
                zone = "Nagrand",
                price_copper = 0,
                source_url = "https://example.invalid/item=900001",
            },
            sources = {
                {
                    type = "vendor",
                    entity_id = 10,
                    vendor_id = 10,
                    entity_name = "Portable Provisioner",
                    source_url = "https://example.invalid/item=900001",
                },
                {
                    type = "vendor",
                    entity_id = 10,
                    vendor_id = 10,
                    entity_name = "Portable Provisioner",
                    location_area = "Portable",
                    location_note = "Deploy the field vendor before buying.",
                    price_copper = 800000,
                    purchase_quantity = 200,
                    side = "Alliance",
                    source_url = "https://example.invalid/item=900001",
                    requirements = {
                        { type = "reputation", reputation = "Fixture Faction", standing = "Revered" },
                    },
                },
                {
                    type = "token_turnin",
                    entity_id = 11,
                    vendor_id = 11,
                    entity_name = "Inscriber Saalyn",
                    zone = "Shattrath City",
                    costs = {
                        { amount = 8, item_id = 29735, name = "Holy Dust" },
                    },
                    token_sources = {
                        {
                            type = "drop",
                            entity_name = "Fixture Boss",
                            zone = "Karazhan",
                            drop_percent = 25,
                            token_item_id = 29735,
                            token_name = "Holy Dust",
                        },
                    },
                    source_url = "https://example.invalid/item=900001",
                },
            },
        },
        {
            id = 900003,
            name = "Reported-Only Fixture",
            quality = "rare",
            primary_source = {
                type = "vendor",
                entity_id = 13,
                vendor_id = 13,
                entity_name = "Only Reported Seller",
                zone = "Nagrand",
                source_url = "https://example.invalid/item=900003",
            },
            sources = {},
        },
    },
    item_fallbacks = {},
    bis_lists = {},
    leveling_gear = {},
    leveling_recommendations = {},
    gems = {},
    gem_sources = {},
    enchants = {},
    enchant_sources = {},
    enchant_effects = {},
    consumables = {},
}
dofile("DataIndex.lua")

local row = { item_id = 900001 }
local options = BigBiSList:GetRowAccessOptions(row)
equal(#options, 3, "duplicate seller records merge into one route")

local byVendor = {}
for _, option in ipairs(options) do
    byVendor[option.vendor_key] = option
end

local portable = byVendor["10"]
local inscription = byVendor["11"]
local reported = byVendor["12"]
expect(portable and inscription and reported, "all distinct seller routes remain")
equal(portable.vendor_label, "Portable Provisioner", "vendor label")
equal(portable.location_area, "Portable", "structured location area")
equal(portable.location_note, "Deploy the field vendor before buying.", "optional location note")
equal(portable.cost_summary, "80g per 200", "copper bundle price formatting")
equal(portable.vendor_details_status, "complete", "complete coin route")
equal(#portable.requirements, 1, "richer duplicate requirements merge")
expect(portable.is_primary, "complete route replaces an incomplete reported primary")

equal(inscription.location_area, "Shattrath City", "legacy zone is the effective area")
equal(inscription.cost_summary, "8 Holy Dust", "turn-in cost formatting")
equal(inscription.vendor_details_status, "complete", "complete turn-in route")
equal(reported.vendor_details_status, "reported_only", "zero or absent price is reported only")
equal(reported.cost_summary, "", "zero is not presented as a real purchase price")
expect(not reported.is_primary, "reported-only route cannot win primary scoring")

local fields = BigBiSList:GetAccessOptionDetailFields(portable)
equal(#fields, 5, "seller details include separate faction and reputation provenance")
equal(fields[1].label, "Vendor", "vendor field label")
equal(fields[1].value, "Portable Provisioner", "vendor field value")
equal(fields[2].label, "Area", "area field label")
equal(fields[2].value, "Portable", "area field value")
equal(fields[2].note, "Deploy the field vendor before buying.", "area note stays separate")
equal(fields[3].label, "Cost", "cost field label")
equal(fields[3].value, "80g per 200", "cost field value")
equal(fields[4].label, "Faction", "faction provenance label")
equal(fields[4].value, "Alliance", "faction provenance value")
equal(fields[5].label, "Reputation", "reputation provenance label")
equal(fields[5].value, "Revered with Fixture Faction", "reputation provenance value")

local inscriptionFields = BigBiSList:GetAccessOptionDetailFields(inscription)
equal(inscriptionFields[4].label, "Token source", "token provenance is a separate line")
expect(string.find(inscriptionFields[4].value, "Fixture Boss (Karazhan) 25.0%", 1, true), "token provenance value")
equal(inscriptionFields[5].label, "Availability", "future seller availability is explicit")
expect(inscriptionFields[5].value ~= "", "future seller availability has a phase label")

local reportedFields = BigBiSList:GetAccessOptionDetailFields(reported)
equal(reportedFields[3].value, "Unavailable in committed source data", "reported-only cost is explicitly unavailable")

local groups = BigBiSList:GetRowSellerGroups(row, portable)
equal(groups.selected.vendor_key, "10", "selected complete seller")
equal(#groups.alternatives, 1, "other complete sellers")
equal(groups.alternatives[1].vendor_key, "11", "complete alternative seller")
equal(#groups.reported, 1, "reported sellers are preserved separately")
equal(groups.reported[1].vendor_key, "12", "reported seller provenance")

local vendorMatch = BigBiSList:GetMatchingRowAccessOption(
    row, { sourceTypes = { vendor = true } }, "PR", false
)
equal(vendorMatch.vendor_key, "10", "vendor filter prefers a complete route")
equal(
    BigBiSList:GetMatchingRowAccessOption(row, { vendor = "12" }, "PR", false),
    nil,
    "reported-only seller is excluded from vendor filtering"
)
equal(
    BigBiSList:GetMatchingRowAccessOption({ item_id = 900003 }, {}, "PR", false),
    nil,
    "reported-only seller is never selected without filters"
)

local reportedAvailability = BigBiSList:GetFilterAvailabilitySnapshot(
    "Druid", "Feral dps", "PR", "Wishlist",
    { wishlistItems = { ["900003"] = true } }
)
expect(not contains(reportedAvailability.sourceTypes, "vendor"), "reported-only seller cannot advertise a dead Vendor facet")
equal(#reportedAvailability.vendors, 0, "reported-only seller cannot advertise a vendor choice")
''')

    def test_committed_glyph_and_inscription_vendor_details_reach_runtime(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("Data.lua")
dofile("DataIndex.lua")

local function seller(itemId, vendorName)
    for _, option in ipairs(BigBiSList:GetRowAccessOptions({ item_id = itemId }) or {}) do
        if option.vendor_label == vendorName and option.vendor_details_status == "complete" then
            return option
        end
    end
    error("missing complete committed seller " .. tostring(vendorName) .. " for " .. tostring(itemId))
end

local ferocity = seller(29192, "Fedryen Swiftspear")
equal(ferocity.location_area, "Zangarmarsh", "Glyph of Ferocity area")
equal(ferocity.cost_summary, "80g", "Glyph of Ferocity price")

local power = seller(29191, "Almaador")
equal(power.location_area, "Shattrath City", "Glyph of Power area")
equal(power.cost_summary, "85g", "Glyph of Power price")

local discipline = seller(28886, "Inscriber Saalyn")
equal(discipline.location_area, "Shattrath City", "Greater Inscription of Discipline area")
equal(discipline.cost_summary, "8 Holy Dust", "Greater Inscription of Discipline turn-in cost")
''')

    def test_compact_leveling_fallbacks_supply_runtime_vendor_routes(self):
        self.run_lua(r'''
BigBiSList = {}
BigBiSListData = {
    format = 2,
    classes = {},
    phases = {},
    schemas = {
        item = { "id" },
        item_fallback = {
            "id", "name", "quality", "source_summary", "wowhead_url",
            "acquisition_phase", "primary_source", "sources", "requirements",
        },
        source = {
            "type", "entity_id", "entity_name", "source_url", "zone",
            "location_area", "location_note", "content_type", "confidence",
            "count", "out_of", "drop_percent", "vendor_id", "price_copper",
            "purchase_quantity", "costs", "token_sources", "quest_id",
            "spell_id", "profession", "requirements",
        },
        cost = { "amount", "name", "currency_id", "item_id" },
        requirement = { "type", "scope", "raw_text" },
        leveling_recommendation = {
            "class", "spec", "race", "level_min", "level_max", "level_band",
            "slot", "item_id", "variant_id", "rank", "context", "source_bucket",
            "score", "score_delta_pct", "reason_tags", "source_summary",
            "source_url", "requirements",
        },
    },
    items = {},
    item_fallbacks = {
        {
            [1] = 900002,
            [2] = "Fallback Vendor Item",
            [3] = "rare",
            [4] = "Vendor: Fallback Quartermaster",
            [5] = "https://example.invalid/item=900002",
            [6] = "PR",
            [7] = {
                [1] = "vendor", [2] = 500, [3] = "Fallback Quartermaster",
                [4] = "https://example.invalid/item=900002", [6] = "Hellfire Peninsula",
                [7] = "Inside the inn.", [13] = 500, [14] = 27000, [15] = 1,
            },
            [8] = {
                {
                    [1] = "vendor", [2] = 500, [3] = "Fallback Quartermaster",
                    [4] = "https://example.invalid/item=900002", [6] = "Hellfire Peninsula",
                    [7] = "Inside the inn.", [13] = 500, [14] = 27000, [15] = 1,
                },
            },
        },
    },
    leveling_recommendations = {
        {
            [1] = "Druid", [2] = "Feral dps", [3] = "*", [4] = 1, [5] = 69,
            [6] = "1-69", [7] = "Head", [8] = 900002, [9] = "base", [10] = 1,
            [11] = "standard", [12] = "vendor", [13] = 100,
            [15] = { "best_easy_source" }, [16] = "Vendor fallback fixture",
        },
    },
    uses = {},
    leveling_gear = {},
    gem_sources = {},
    enchant_sources = {},
    enchant_effects = {},
    gems = {},
    enchants = {},
    consumables = {},
}
dofile("DataIndex.lua")

local groups = BigBiSList:GetLevelingRows("Druid", "Feral dps", 30, { race = "Night Elf" })
equal(#groups, 1, "fallback-backed leveling slot")
equal(#groups[1].items, 1, "fallback-backed leveling row")
local row = groups[1].items[1]
equal(row.name, "Fallback Vendor Item", "fallback name is consumed")
expect(row.item ~= nil, "fallback record becomes the runtime acquisition item")
equal(row.item.id, 900002, "fallback item id")

local options = BigBiSList:GetRowAccessOptions(row)
equal(#options, 1, "fallback seller route is inflated")
equal(options[1].vendor_label, "Fallback Quartermaster", "fallback vendor")
equal(options[1].location_area, "Hellfire Peninsula", "fallback area")
equal(options[1].location_note, "Inside the inn.", "fallback location note")
equal(options[1].cost_summary, "2g 70s", "fallback copper price")
equal(options[1].vendor_details_status, "complete", "fallback route is complete")
''')

    def test_wishlist_summary_is_expansion_wide_and_class_scoped(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("Data.lua")
dofile("DataIndex.lua")

local hunter = BigBiSList:GetWishlistExpansionSummary(29121, "Hunter", "Survival")
equal(#hunter.phase_order, 6, "all endgame phases")
equal(hunter.spec_rankings[1].spec, "Survival", "selected spec first")
expect(hunter.spec_rankings[1].selected, "selected marker")
equal(#hunter.spec_rankings[1].phase_cells, 6, "six phase cells")
equal(#hunter.relevant_spec_rankings, 3, "all relevant Hunter specs")
expect(contains(hunter.slots, "Main Hand"), "main hand slot")
expect(contains(hunter.slots, "Off Hand"), "off hand slot")
expect(contains(hunter.slots, "Dual Wield"), "dual wield slot")
equal(hunter.not_ranked_label, nil, "relevant item has no fallback label")

local blinkstrike = BigBiSList:GetWishlistExpansionSummary(31332, "Warrior", "Fury")
local phaseOne = blinkstrike.selected_spec_ranking.phases.T4
equal(phaseOne.short_label, "BiS", "strongest same-phase rank wins")
equal(phaseOne.rank_group, "bis", "strongest rank group")

local foreign = BigBiSList:GetWishlistExpansionSummary(29021, "Mage", "Arcane")
equal(#foreign.relevant_spec_rankings, 0, "foreign class has no relevant specs")
expect(not foreign.class_relevant, "foreign item is not class relevant")
equal(foreign.not_ranked_label, "Not ranked for Mage", "foreign fallback is class scoped")
equal(foreign.best_use, nil, "another class use is never displayed")
''')

    def test_wishlist_rows_sort_and_keep_filtered_acquisition_paths_consistent(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("Data.lua")
dofile("DataIndex.lua")
BigBiSList.GetCurrentPhaseKey = function() return "T4" end

local rows = BigBiSList:GetWishlistRows(
    { ["29121"] = true, ["34196"] = true, ["29021"] = true },
    "Hunter",
    "Survival",
    "PR",
    { ownedItems = { ["29121"] = "bag" } }
)
equal(#rows, 3, "wishlist rows")
equal(rows[1].item_id, 34196, "missing relevant item first")
equal(rows[2].item_id, 29021, "missing unranked item next")
equal(rows[3].item_id, 29121, "owned item last")
expect(rows[1].source_future, "future selected-phase source")
expect(rows[1].source_live_future, "future live-phase source")
expect(not rows[3].source_future, "current source available")
equal(rows[1].selected_phase, "PR", "selected phase marker")
equal(rows[1].live_phase, "T4", "live phase marker")

local pvpRows = BigBiSList:GetWishlistRows(
    { ["28127"] = true }, "Druid", "Feral dps", "PR",
    { sourceTypes = { pvp = true } }
)
equal(#pvpRows, 1, "PvP path result")
equal(pvpRows[1].matched_access_option.source_filter_key, "pvp", "matched PvP path")
equal(pvpRows[1].acquisition_display.source_label, "PvP", "PvP source display")
equal(pvpRows[1].matched_access_option.vendor_details_status, "complete", "PvP path has complete seller details")
equal(pvpRows[1].matched_access_option.location_area, "Alterac Valley", "PvP path uses a committed area")
expect(string.find(pvpRows[1].acquisition_display.location_label, "Captain Dirgehammer", 1, true), "complete PvP location display")

local vendorRows = BigBiSList:GetWishlistRows(
    { ["28127"] = true }, "Druid", "Feral dps", "PR",
    { sourceTypes = { vendor = true } }
)
equal(#vendorRows, 0, "unpriced vendor reports are not purchasable filter results")

local allianceRows = BigBiSList:GetWishlistRows(
    { ["28041"] = true }, "Druid", "Feral dps", "PR",
    { faction = "Alliance" }
)
equal(#allianceRows, 1, "faction-scoped wishlist result")
equal(allianceRows[1].matched_access_option.side, "Alliance", "grid acquisition path respects player faction")
expect(string.find(allianceRows[1].acquisition_display.location_label, "Overlord", 1, true), "Alliance quest location display")

local neutralPhaseItemPresent = false
for _, group in ipairs(BigBiSList:GetPhaseRows("Warrior", "Arms", "PR", { faction = "Alliance" })) do
    for _, row in ipairs(group.items or {}) do
        if row.item_id == 31462 then
            neutralPhaseItemPresent = true
        end
    end
end
expect(neutralPhaseItemPresent, "faction context preserves neutral phase rows")

local availability = BigBiSList:GetFilterAvailabilitySnapshot(
    "Druid", "Feral dps", "PR", "Wishlist",
    { wishlistItems = { ["28127"] = true, ["24250"] = true } }
)
expect(contains(availability.sourceTypes, "pvp"), "wishlist PvP availability")
expect(not contains(availability.sourceTypes, "vendor"), "reported-only wishlist vendors are not advertised")
expect(contains(availability.sourceTypes, "crafted"), "wishlist crafted availability")
expect(#availability.zones > 0, "wishlist zone availability")
expect(#availability.vendors > 0, "wishlist vendor options")
for _, label in pairs(availability.vendorLabels or {}) do
    expect(label ~= "Explodyne Fizzlespurt", "reported-only vendor is excluded from availability")
end

local shared = { sourceTypes = { vendor = true }, upgradeMode = "all" }
local plannerRows = BigBiSList:GetPlannerRows("Druid", "Feral dps", "PR", shared)
expect(#plannerRows > 0, "planner vendor rows")
for _, row in ipairs(plannerRows) do
    local option = BigBiSList:GetMatchingRowAccessOption(row, shared, "PR", false)
    expect(option and option.source_filter_key == "vendor", "planner uses matching vendor path")
end
local phaseCount = 0
for _, group in ipairs(BigBiSList:GetPhaseRows("Druid", "Feral dps", "PR", shared)) do
    for _, row in ipairs(group.items or {}) do
        phaseCount = phaseCount + 1
        local option = BigBiSList:GetMatchingRowAccessOption(row, shared, "PR", false)
        expect(option and option.source_filter_key == "vendor", "BiS list uses matching vendor path")
    end
end
expect(phaseCount > 0, "BiS list vendor rows")
''')

    def test_tier_six_phase_boundary_uses_the_official_launch_epoch(self):
        self.run_lua(r'''
BigBiSList = {}
BigBiSListData = {
    classes = {},
    phases = {
        { key = "PR", name = "Pre-Raid", starts_at_epoch = 0 },
        { key = "T4", name = "Tier 4", starts_at_epoch = 1771542000 },
        { key = "T5", name = "Tier 5", starts_at_epoch = 1778796000 },
        { key = "T6", name = "Tier 6", starts_at_epoch = 1787868000 },
        { key = "ZA", name = "Zul'Aman" },
        { key = "SWP", name = "Sunwell Plateau" },
    },
    items = {},
    item_fallbacks = {},
    bis_lists = {},
    leveling_gear = {},
    leveling_recommendations = {},
    gems = {},
    gem_sources = {},
    enchants = {},
    enchant_sources = {},
    enchant_effects = {},
    consumables = {},
}
dofile("DataIndex.lua")

equal(BigBiSList:GetCurrentPhaseKey(1787867999), "T5", "one second before Tier 6 launch")
equal(BigBiSList:GetCurrentPhaseKey(1787868000), "T6", "exactly at Tier 6 launch")
''')

    def test_enhancement_rows_support_type_applied_and_availability_filters(self):
        self.run_lua(r'''
BigBiSList = {}
dofile("Data.lua")
dofile("DataIndex.lua")

local gems = BigBiSList:GetEnhancementRows(
    "Druid", "Feral dps", "PR", { enhancementType = "gem" }
)
expect(#gems[1].rows > 0, "gem rows")
equal(#gems[2].rows, 0, "enchant rows filtered")
equal(#gems[3].rows, 0, "consumable rows filtered")
for _, row in ipairs(gems[1].rows) do
    equal(row.enhancement_kind, "gem", "enhancement type")
end

local function appliedResolver(row)
    return row.item_id == 24028
end
local applied = BigBiSList:GetEnhancementRows(
    "Druid", "Feral dps", "PR",
    {
        enhancementType = "gem",
        appliedState = "applied",
        getEnhancementAppliedState = appliedResolver,
    }
)
equal(#applied[1].rows, 1, "one applied gem")
equal(applied[1].rows[1].item_id, 24028, "applied gem id")
equal(applied[1].rows[1].applied_state, "applied", "applied state")

local missing = BigBiSList:GetEnhancementRows(
    "Druid", "Feral dps", "PR",
    {
        enhancementType = "gem",
        appliedState = "missing",
        getEnhancementAppliedState = appliedResolver,
    }
)
equal(#missing[1].rows, #gems[1].rows - 1, "remaining gems are missing")
for _, row in ipairs(missing[1].rows) do
    equal(row.applied_state, "missing", "missing applied state")
end

local consumables = BigBiSList:GetEnhancementRows(
    "Druid", "Feral dps", "PR", { enhancementType = "consumable" }
)
expect(#consumables[3].rows > 0, "consumable rows")
local allianceConsumables = BigBiSList:GetEnhancementRows(
    "Druid", "Feral dps", "PR",
    { enhancementType = "consumable", faction = "Alliance" }
)
equal(
    #allianceConsumables[3].rows,
    #consumables[3].rows,
    "faction context preserves neutral consumables with eligible access paths"
)
local ownedConsumableId = consumables[3].rows[1].item_id
local ownedConsumables = BigBiSList:GetEnhancementRows(
    "Druid", "Feral dps", "PR",
    {
        enhancementType = "consumable",
        appliedState = "applied",
        ownedItems = { [tostring(ownedConsumableId)] = "bag" },
    }
)
equal(#ownedConsumables[3].rows, 1, "Applied / owned includes the owned consumable")
equal(ownedConsumables[3].rows[1].item_id, ownedConsumableId, "owned consumable id")
local missingConsumables = BigBiSList:GetEnhancementRows(
    "Druid", "Feral dps", "PR",
    {
        enhancementType = "consumable",
        appliedState = "missing",
        ownedItems = { [tostring(ownedConsumableId)] = "bag" },
    }
)
equal(#missingConsumables[3].rows, #consumables[3].rows - 1, "Missing excludes the owned consumable")

local availability = BigBiSList:GetFilterAvailabilitySnapshot(
    "Druid", "Feral dps", "PR", "Enhance",
    { enhancementType = "gem", getEnhancementAppliedState = appliedResolver }
)
equal(#availability.sourceTypes, 2, "type-scoped enhancement availability")
expect(contains(availability.sourceTypes, "crafted"), "gem crafting availability")
expect(contains(availability.sourceTypes, "trade"), "verified gem purchase availability")
''')


if __name__ == "__main__":
    unittest.main()
