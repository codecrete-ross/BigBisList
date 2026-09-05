import subprocess
import unittest

from tests.test_addon_runtime_lua import LUA_ASSERTIONS, find_lua51
from tools.project import ADDON_DIR


FRAME_STUB = r'''
local function frame(parent)
    local value = { parent = parent, shown = true, width = 304, height = 100, scripts = {} }
    function value:GetParent() return self.parent end
    function value:SetParent(parent) self.parent = parent end
    function value:Show() self.shown = true end
    function value:Hide() self.shown = false end
    function value:SetShown(shown) self.shown = shown end
    function value:IsShown() return self.shown end
    function value:SetWidth(width) self.width = width end
    function value:SetHeight(height) self.height = height end
    function value:SetSize(width, height) self.width, self.height = width, height end
    function value:GetWidth() return self.width end
    function value:GetHeight() return self.height end
    function value:SetPoint(...) self.point = { ... } end
    function value:ClearAllPoints() self.point = nil end
    function value:SetText(text) self.text = text end
    function value:GetStringHeight() return 14 end
    function value:SetScript(event, callback) self.scripts[event] = callback end
    function value:CreateFontString() return frame(self) end
    function value:CreateTexture() return frame(self) end
    return setmetatable(value, { __index = function(_, key)
        if string.match(key, "^[A-Z]") then return function() end end
    end })
end
CreateFrame = function(_, _, parent) return frame(parent) end
BigBiSList = { Widgets = {} }
function BigBiSList.Widgets:SetIcon(texture, key) texture.iconKey = key end
function BigBiSList.Widgets:BindTooltip(button, text) button.tooltip = text end
function BigBiSList.Widgets:SetCellText(label, text, lines, lineHeight, width)
    label:SetText(text); label:SetWidth(width); label:SetHeight(lines * lineHeight)
    label.maxLines, label.lineHeight, label.fullText = lines, lineHeight, text
end
function BigBiSList.Widgets:CreateUtilityButton(parent, key, size, callback, tooltip)
    local button = frame(parent)
    button.icon = frame(button)
    button.icon.iconKey = key
    button.scripts.OnClick = callback
    button.tooltip = tooltip
    return button
end
assert(loadfile("UI.lua"))()
local ui = BigBiSList.UI
ui.CountPerformance = function() end
ui.GetSelection = function() return { class = "Druid", spec = "Feral", phase = "T5" } end
ui.GetRowSlotDisplay = function(_, data) return data.slot or "" end
ui.SetItemButton = function(_, button, itemId) button.entityId = itemId; button.entityType = "item" end
ui.SetSpellButton = function(_, button, spellId) button.entityId = spellId; button.entityType = "spell" end
function BigBiSList:GetPhaseOrder() return { "PR", "T4", "T5", "T6", "ZA", "SWP" } end
function BigBiSList:GetCurrentPhaseKey() return "T4" end
function BigBiSList:GetPhaseDisplayName(phase) return phase end
local character = { wishlist = {}, ignoredItems = {} }
function BigBiSList:GetCharacterDB() return character end
'''

DETAILS_LAYOUT_STUB = FRAME_STUB + r'''
ui.detailsContent, ui.detailsScroll, ui.detailsHeader = frame(), frame(), frame()
ui.detailsContent:SetSize(1, 1)
ui.detailsScroll:SetSize(284, 400)
ui.detailsScroll.offset = 0
function ui.detailsScroll:GetVerticalScroll() return self.offset end
function ui.detailsScroll:SetVerticalScroll(value) self.offset = value end
ui.IsInspectorVisible = function() return true end
ui.FindPlannerContext = function() return nil end
ui.GetRowRecommendationText = function() return "Alternative" end
ui.GetOwnershipState = function() return "missing" end
ui.GetAccessBadgeLabel = function() return "Ready" end
ui.GetAccessEvaluation = function() return { status = "ready", options = {} } end
ui.GetRowSellerDisplayGroups = function() return { alternatives = {}, reported = {} } end
function BigBiSList:GetDataIndex()
    return { itemsById = { [101] = { name = "Cenarion Ward", quality = "epic" } } }
end
function BigBiSList:GetWishlistExpansionSummary() return { relevant_spec_rankings = {} } end
local data = { item_id = 101, slot = "Head", source_summary = "Dungeon boss" }
ui.dirtyDomains = { details = true }
'''


class DetailsRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, source):
        if not self.lua:
            self.skipTest("Lua 5.1 is not available")
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, input=LUA_ASSERTIONS + source,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_details_defer_unresolved_viewport_and_retry_with_measurable_anchor(self):
        self.run_lua(DETAILS_LAYOUT_STUB + r'''
local originalCreateFrame = CreateFrame
CreateFrame = function(...)
    local value = originalCreateFrame(...)
    value:SetSize(0, 0)
    return value
end
ui.detailsScroll:SetSize(0, 0)
ui:RefreshDetails(101, data, "phase")
equal(ui.detailsRenderSignature, nil, "unresolved native viewport is not cached")
expect(ui.pendingDetailsRequest and ui.pendingDetailsRequest.itemId == 101, "first-show request remains pending")
expect(not ui.detailsWidgetPools, "unresolved viewport is not used for body measurement")
ui.detailsScroll:SetSize(284, 400)
ui:RefreshDetailsLayout()
equal(ui.detailsContent:GetWidth(), 284, "scroll child width is synchronized before section measurement")
local start = ui.detailsWidgetPools.start[1]
-- Native geometry cannot supply a usable rectangle for an anchor with no extent.
local function nativeRect(value)
    if value:GetWidth() <= 0 or value:GetHeight() <= 0 then return nil end
    return { width = value:GetWidth(), height = value:GetHeight() }
end
expect(nativeRect(start), "first body anchor has positive width and height")
equal(ui.detailsWidgetPools.text[1].body:GetWidth(), 268, "body measurement uses current viewport")
equal(ui.detailsWidgetPools.text[1].title.text, "Recommendation", "recommendation body is built")
equal(ui.detailsWidgetPools.fields[1].title.text, "Selected route", "route body is built")
expect(ui.detailsRenderSignature, "completed body is cached")
equal(ui.pendingDetailsRequest, nil, "completed request is cleared")
equal(ui.dirtyDomains.details, nil, "completed details are clean")
''')

    def test_details_failed_body_render_is_retryable_after_identity_is_bound(self):
        self.run_lua(DETAILS_LAYOUT_STUB + r'''
local original = ui.CreateDetailsFields
ui.CreateDetailsFields = function() error("simulated late body failure") end
local ok = pcall(function() ui:RefreshDetails(101, data, "phase") end)
expect(not ok and ui.detailsIdentity, "failure occurred after fixed identity was bound")
equal(ui.detailsRenderSignature, nil, "partially rendered inspector is not cached")
expect(ui.pendingDetailsRequest, "failed render remains retryable")
expect(ui.dirtyDomains.details, "failed details stay dirty")
ui.CreateDetailsFields = original
ui:RefreshDetailsLayout()
expect(ui.detailsRenderSignature and not ui.pendingDetailsRequest, "same request succeeds on retry")
equal(ui.detailsWidgetPools.fields[1].fields[1].value.text, "Dungeon boss", "retry renders route details")
''')

    def test_details_preserve_valid_scroll_and_clamp_after_same_item_collapses(self):
        self.run_lua(DETAILS_LAYOUT_STUB + r'''
data.notes = "Long provenance"
ui.expandedSellerSections = { ["item:101:provenance"] = true }
ui:RefreshDetails(101, data, "phase")
local body = ui.detailsWidgetPools.collapsible[1].body
body.GetStringHeight = function() return 900 end
ui.detailsRenderSignature = nil
ui:RefreshDetails(101, data, "phase")
ui.detailsScroll:SetVerticalScroll(350)
ui:RefreshDetailsLayout()
equal(ui.detailsScroll:GetVerticalScroll(), 350, "cached same-item refresh preserves valid scroll")
ui.expandedSellerSections["item:101:provenance"] = false
ui.detailsRenderSignature = nil
ui:RefreshDetailsLayout()
equal(ui.detailsScroll:GetVerticalScroll(), 0, "collapsed short body cannot remain scrolled out of view")
equal(ui.detailsContent:GetHeight(), ui.detailsScroll:GetHeight(), "short body creates no artificial overflow")
ui.detailsScroll:SetSize(284, 600)
ui:RefreshDetailsLayout()
equal(ui.detailsContent:GetHeight(), 600, "cached content responds to viewport height changes")
''')

    def test_details_sections_start_expanded_and_remember_explicit_collapses(self):
        self.run_lua(FRAME_STUB + r'''
local parent, anchor = frame(), frame()
ui.RefreshDetails = function() end
local function section(key)
    ui:BeginDetailsRender()
    return ui:CreateDetailsCollapsibleText(parent, anchor, key, "Notes", "Evidence")
end
local block = section("item:101:provenance")
expect(block.body:IsShown(), "unvisited section starts expanded")
equal(block.disclosure.iconKey, "chevronDown")
block.scripts.OnClick(block)
block = section("item:101:provenance")
expect(not block.body:IsShown(), "first click collapses the default-open section")
equal(block.disclosure.iconKey, "chevronRight")
local other = section("item:102:provenance")
expect(other.body:IsShown(), "another item starts expanded when a pooled block is rebound")
block = section("item:101:provenance")
expect(not block.body:IsShown(), "returning preserves the user's explicit collapse")
block.scripts.OnClick(block)
block = section("item:101:provenance")
expect(block.body:IsShown(), "collapsed section can be expanded again")
''')

    def test_fixed_identity_actions_bind_current_item_and_exclude_spells(self):
        self.run_lua(FRAME_STUB + r'''
ui.detailsHeader = frame()
local added, removed, menuItem
ui.AddWishlist = function(_, id) added = id end
ui.RemoveWishlist = function(_, id) removed = id end
ui.ShowItemActionMenu = function(_, data) menuItem = data.item_id end
ui:BeginDetailsRender()
ui:RefreshDetailsHeader(101, "item", 101, { item_id = 101, slot = "Head" }, "phase", "First", 1, 1, 1)
local header = ui.detailsIdentity
equal(header:GetParent(), ui.detailsHeader, "identity belongs to fixed header")
header.star.scripts.OnClick(header.star)
header.menu.scripts.OnClick(header.menu)
equal(added, 101, "wishlist targets header item")
equal(menuItem, 101, "menu targets header item")
character.wishlist[102] = nil
character.wishlist["102"] = { addedAt = 1 }
ui:BeginDetailsRender()
ui:RefreshDetailsHeader(102, "item", 102, { item_id = 102 }, "phase", "Second")
equal(header, ui.detailsIdentity, "header is reused")
equal(header.star.icon.iconKey, "starFilled", "truthy wishlist records are selected")
header.star.scripts.OnClick(header.star)
equal(removed, 102, "reused actions target new entity")
ui:BeginDetailsRender()
ui:RefreshDetailsHeader(900, "spell", nil, { spell_id = 900 }, "enhance", "Enchant")
expect(not header.star:IsShown() and not header.menu:IsShown(), "spells expose no item actions")
equal(header.iconButton.entityType, "spell", "spell uses native spell presentation")
''')

    def test_identity_header_centers_actions_and_groups_slot_with_name(self):
        self.run_lua(r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:Open()
H.settle()
ui:SetTab("By Slot")
H.settle()
local data
for _, entry in ipairs(ui.renderModel.entries) do
    if entry.kind == "row" and entry.data.item_id then data = entry.data; break end
end
expect(data, "fixture has a selectable item")
ui:ShowInspectorFor(data.item_id, data, "phase")
H.settle()
local function near(actual, expected, message)
    expect(math.abs(actual - expected) < .1, message)
end
for _, width in ipairs({ 1020, 1160 }) do
    ui.frame:SetSize(width, 660)
    H.settle()
    local header = ui.detailsIdentity
    local center = select(2, ui.detailsHeader:GetCenter())
    equal(ui.detailsHeader:GetHeight(), 76, "identity header keeps fixed height")
    equal(header.iconButton:GetWidth(), 40, "identity uses a readable 40-pixel icon")
    for _, control in ipairs({ header.iconButton, header.star, header.menu, ui.detailsCloseButton }) do
        near(select(2, control:GetCenter()), center, "icon and all actions share the header centerline")
        H.expectBounded(control, ui.detailsHeader, "header control")
    end
    near(header.name:GetLeft(), header.iconButton:GetRight() + 8, "name begins beside icon")
    near(header.meta:GetLeft(), header.name:GetLeft(), "slot aligns with item name")
    near(header.meta:GetTop(), header.name:GetBottom() - 2, "slot follows item name with a small gap")
    near((header.name:GetTop() + header.meta:GetBottom()) / 2, center, "name and slot form one centered block")
    expect(header.name:GetRight() <= header.star:GetLeft() - 8, "item name reserves action spacing")
    expect(header.meta:GetRight() <= header.star:GetLeft() - 8, "slot reserves action spacing")
    H.expectBounded(header.name, ui.detailsHeader, "item name")
    H.expectBounded(header.meta, ui.detailsHeader, "slot")
end
local header = ui.detailsIdentity
ui:BeginDetailsRender()
ui:RefreshDetailsHeader(900, "spell", nil, { spell_id = 900 }, "enhance", "Enchant")
expect(not header.meta:IsShown(), "pooled header hides absent metadata")
near(select(2, header.name:GetCenter()), select(2, ui.detailsHeader:GetCenter()), "name-only header stays centered")
expect(not header.star:IsShown() and not header.menu:IsShown(), "spell header hides item actions")
ui:BeginDetailsRender()
ui:RefreshDetailsHeader(data.item_id, "item", data.item_id, data, "phase", data.name)
expect(header.meta:IsShown(), "pooled item header restores metadata")
expect(header.star:IsShown() and header.menu:IsShown(), "pooled item header restores actions")
''')

    def test_phase_matrix_aligns_cells_and_distinguishes_selected_from_live(self):
        self.run_lua(FRAME_STUB + r'''
function BigBiSList:GetWishlistExpansionSummary(itemId, class, spec, phase)
    equal(itemId, 101); equal(class, "Druid"); equal(spec, "Feral"); equal(phase, "T5")
    return { relevant_spec_rankings = {
        { spec = "Feral", phases = { T4 = { short_label = "BiS" }, T5 = { short_label = "Alt" } } },
        { spec = "Restoration", phases = { T4 = { short_label = "Alt" } } },
    } }
end
function BigBiSList:GetItemUses()
    return {
        { class = "Druid", spec = "Feral", phase = "T4", rank_group = "bis", rank_label = "BiS", slot = "Head", context = "Bear setup" },
        { class = "Druid", spec = "Feral", phase = "T4", rank_group = "alt", rank_label = "Alternative", slot = "Head", context = "Cat setup" },
    }
end
local parent, anchor = frame(), frame()
ui:BeginDetailsRender()
local matrix = ui:CreateDetailsPhaseMatrix(parent, anchor, 101, {})
equal(matrix.disclosure.iconKey, "chevronDown", "matrix starts expanded")
equal(matrix.matrixLabels[3].point[4], matrix.matrixLabels[10].point[4], "P1 and first spec cell align")
equal(matrix.matrixLabels[10].point[4], matrix.matrixLabels[17].point[4], "spec rows share a column")
equal(matrix.matrixMarks[2]:GetHeight(), 2, "live phase uses blue rule")
expect(matrix.matrixMarks[3]:GetHeight() > 2, "selected phase uses full column fill")
equal(matrix.matrixLabels[10].text, "BiS", "rank data remains visible")
expect(string.find(matrix.matrixTargets[10].tooltip, "Bear setup", 1, true), "best variant context remains available")
expect(string.find(matrix.matrixTargets[10].tooltip, "Cat setup", 1, true), "alternate variant context remains available")
ui.RefreshDetails = function() end
matrix.scripts.OnClick(matrix)
ui:BeginDetailsRender()
matrix = ui:CreateDetailsPhaseMatrix(parent, anchor, 101, {})
equal(matrix.disclosure.iconKey, "chevronRight", "matrix remains collapsible")
expect(not matrix.matrixLabels[10]:IsShown(), "collapsed matrix hides cells")
expect(not matrix.matrixTargets[10]:IsShown(), "collapsed matrix hides cell targets")
matrix.scripts.OnClick(matrix)
ui:BeginDetailsRender()
matrix = ui:CreateDetailsPhaseMatrix(parent, anchor, 101, {})
expect(matrix.matrixLabels[10]:IsShown(), "matrix can be expanded again")
ui:BeginDetailsRender()
local other = ui:CreateDetailsCollapsibleText(parent, anchor, "provenance", "Notes", "Evidence")
expect(not other.matrixLabels[3]:IsShown(), "pooled section does not retain matrix labels")
expect(not other.matrixMarks[2]:IsShown(), "pooled section does not retain matrix highlight")
expect(not other.matrixTargets[10]:IsShown(), "pooled section does not retain cell tooltip targets")
''')

    def test_details_preserve_route_requirements_and_omit_empty_sections(self):
        self.run_lua(FRAME_STUB + r'''
ui.detailsContent, ui.detailsScroll, ui.detailsHeader = frame(), frame(), frame()
ui.IsInspectorVisible = function() return true end
ui.FindPlannerContext = function() return nil end
ui.GetRowRecommendationText = function() return "Alternative" end
ui.GetOwnershipState = function() return "missing" end
ui.GetAccessBadgeLabel = function() return "Ready" end
ui.FormatAccessOptionRequirements = function() return "Exalted with Cenarion Expedition" end
ui.currentOwned = { bankScanned = true }
local selected = { source_type = "vendor", vendor_label = "Fedryen", requirements = { { type = "reputation" } } }
local alternative = { source_type = "drop", label = "Dungeon boss", requirements = {} }
ui.GetAccessEvaluation = function() return { status = "ready", optionEvaluation = { option = selected }, options = { { option = selected }, { option = alternative } } } end
ui.GetRowSellerDisplayGroups = function() return { selected = selected, alternatives = {}, reported = {} } end
ui.GetSellerDetailLines = function() return nil end
function BigBiSList:GetDataIndex() return { itemsById = { [101] = { name = "Cenarion Ward", quality = "epic" } } } end
function BigBiSList:GetAccessOptionDetailFields() return { { label = "Vendor", value = "Fedryen" }, { label = "Location", value = "Zangarmarsh" }, { label = "Cost", value = "20 gold" } } end
function BigBiSList:GetWishlistExpansionSummary() return { relevant_spec_rankings = {} } end
ui:RefreshDetails(101, { item_id = 101, slot = "Head" }, "phase")
local fields = ui.detailsWidgetPools.fields[1].fields
equal(fields[1].value.text, "Fedryen", "structured vendor preserved")
equal(fields[2].value.text, "Zangarmarsh", "structured location preserved")
equal(fields[3].value.text, "20 gold", "structured cost preserved")
equal(fields[4].value.text, "Exalted with Cenarion Expedition", "route requirements preserved")
equal(ui.detailsWidgetPools.collapsible[1].title.text, "Other routes (1)", "alternate drop route remains accessible")
for _, pool in pairs(ui.detailsWidgetPools) do
    for _, widget in ipairs(pool) do
        if widget.title and widget.title.text then
            expect(widget.title.text ~= "Notes & provenance", "empty provenance omitted")
            expect(widget.title.text ~= "Expansion value", "empty expansion omitted")
        end
    end
end
ui.detailsRenderSignature = nil
ui.GetAccessEvaluation = function() return { status = "blocked", optionEvaluation = { status = "blocked" } } end
ui.GetRowSellerDisplayGroups = function() return { alternatives = {}, reported = {} } end
ui.FormatRequirements = function() return "Requires Alchemy 350" end
ui:RefreshDetails(101, { item_id = 101, requirements = { { type = "profession" } } }, "phase")
equal(ui.detailsWidgetPools.fields[1].fields[4].value.text, "Requires Alchemy 350", "flat requirements survive absent route options")
''')

    def test_alt_refresh_rebuilds_native_tooltip_once_without_duplicate_sections(self):
        self.run_lua(r'''
local altDown = false
IsAltKeyDown = function() return altDown end
BigBiSList = {}
BigBiSListDB = { profile = { tooltips = { enabled = true, compact = true, showAllOnAlt = true } } }
function BigBiSList:EnsureDatabase() end
function BigBiSList:GetCharacterDB() return { selection = { class = "Druid", spec = "Feral", phase = "T4" } } end
function BigBiSList:GetPhaseDisplayName(phase) return phase end
function BigBiSList:GetTooltipSpecFilterKey() return "all" end
local matches = {}
for index = 1, 6 do matches[index] = { class = "Druid", spec = "Feral", phase = "T4", slot = "Head", rank_label = "BiS" } end
function BigBiSList:GetTooltipMatches() return matches end
function BigBiSList:GetGroupedTooltipMatches() return matches end
local function tooltip()
    local frame = { scripts = {}, lines = {}, rebuilds = 0, link = "item:101:123:456" }
    function frame:AddLine(text) table.insert(self.lines, text) end
    function frame:AddDoubleLine(left, right) table.insert(self.lines, left .. ":" .. right) end
    function frame:GetItem() return "Native item", self.link end
    function frame:HookScript(event, callback) self.scripts[event] = callback end
    function frame:IsShown() return true end
    function frame:Show() end
    function frame:SetHyperlink(link)
        equal(link, "item:101:123:456", "fallback retains exact item instance link")
        self.rebuilds = self.rebuilds + 1
        self.lines = { "Native item", "Native enchant", "Native socket" }
        self.scripts.OnTooltipCleared(self)
        self.scripts.OnTooltipSetItem(self)
    end
    return frame
end
GameTooltip, ItemRefTooltip = tooltip(), tooltip()
CreateFrame = function()
    return { RegisterEvent = function() end, SetScript = function(self, event, callback) self[event] = callback end }
end
assert(loadfile("Tooltip.lua"))()
BigBiSList:InitTooltip()
GameTooltip:SetHyperlink(GameTooltip.link)
local compactCount = #GameTooltip.lines
local function assertSingleSection()
    local headings = 0
    for _, line in ipairs(GameTooltip.lines) do if line == "Big BiS List" then headings = headings + 1 end end
    equal(headings, 1, "only one addon section")
    equal(GameTooltip.lines[1], "Native item", "native name retained")
    equal(GameTooltip.lines[2], "Native enchant", "native enchant retained")
    equal(GameTooltip.lines[3], "Native socket", "native socket retained")
end
assertSingleSection()
altDown = true
BigBiSList.tooltipModifierFrame.OnEvent(nil, "MODIFIER_STATE_CHANGED", "LALT")
expect(#GameTooltip.lines > compactCount, "Alt expands while item remains hovered")
assertSingleSection()
local refreshes = GameTooltip.rebuilds
BigBiSList.tooltipModifierFrame.OnEvent(nil, "MODIFIER_STATE_CHANGED", "RALT")
equal(GameTooltip.rebuilds, refreshes, "unchanged modifier state does not rebuild")
altDown = false
BigBiSList.tooltipModifierFrame.OnEvent(nil, "MODIFIER_STATE_CHANGED", "LALT")
equal(#GameTooltip.lines, compactCount, "release restores compact rows")
assertSingleSection()
local other = tooltip()
BigBiSList:AddTooltipInfo(other)
equal(#other.lines, 0, "unrelated tooltips remain untouched")
''')


if __name__ == "__main__":
    unittest.main()
