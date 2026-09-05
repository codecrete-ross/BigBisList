"""Geometry and interaction contracts for the in-game UI regression pass."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


class UILayoutRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body):
        if not self.lua:
            self.skipTest("Lua 5.1 is unavailable")
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:Open(); H.settle()
local function near(a, b, label)
    assert(math.abs(a-b) <= 0.6, label .. ": " .. tostring(a) .. " vs " .. tostring(b))
end
local function centerY(frame) return frame:GetBottom() + frame:GetHeight()/2 end
''' + body, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_rows_and_toolbar_fit_the_docked_workspace_and_are_centered(self):
        self.run_lua(r'''
local saved = BigBiSList:GetCharacterDB().wishlist
for _, entry in ipairs(ui.renderModel.entries) do
    if entry.kind == "row" and entry.data.item_id then
        saved[tostring(entry.data.item_id)] = true
        H.equipped[1] = entry.data.item_id
        break
    end
end
for _, size in ipairs({{1020,560}, {1160,660}}) do
    ui.frame:SetSize(size[1],size[2])
    for _, density in ipairs({"comfortable", "compact"}) do
        BigBiSListDB.profile.window.density = density
        for _, tab in ipairs({"By Slot", "Upgrades", "Wishlist", "Enhance", "Equipped"}) do
            ui:SetTab(tab); ui:Invalidate("all", "layout-test"); ui:Refresh(); H.settle()
            ui:SetInspectorVisible(true); H.settle()
            local label = size[1] .. "/" .. density .. "/" .. tab
            assert(ui.contentPanel:GetRight() + 7 <= ui.details:GetLeft(), label .. " inspector overlap")
            H.expectRowsBounded(ui, label)
            for _, row in ipairs(ui.activeRenderFrames) do
                if row.boundData then
                    local mid = centerY(row)
                    near(centerY(row.iconButton), mid, label .. " icon center")
                    if row.boundMode == "gear" then
                        near(centerY(row.findButton), mid, label .. " equipment action center")
                        near((row.slotText:GetTop()+row.rankText:GetBottom())/2, mid, label .. " equipment text center")
                    else
                        local lastText = row.subText:IsShown() and row.subText or row.nameText
                        near((row.nameText:GetTop()+lastText:GetBottom())/2, mid, label .. " item identity center")
                        near(centerY(row.statusIcon), mid, label .. " status symbol center")
                        for key, cell in pairs(row.cells) do
                            if cell:IsShown() then near(centerY(cell), mid, label .. " " .. key .. " center") end
                        end
                        if row.actionButton:IsShown() then near(centerY(row.actionButton), mid, label .. " star center") end
                        assert(row.columnLayout.acquisition and row.columnLayout.acquisition.label == "Source", label .. " combined Source is missing")
                        assert(not row.columnLayout.source and not row.columnLayout.location, label .. " duplicate source columns")
                    end
                end
            end
            if ui.listToolbar:IsVisible() then
                local controls = {}
                for _, control in ipairs({ui.searchFrame, ui.filterToggleButton, ui.sortDropdown, ui.groupDropdown, ui.upgradeModeDropdown, ui.wishlistRelevanceDropdown, ui.inspectorToggleButton}) do
                    if control:IsVisible() and control:GetParent() == ui.listToolbar then controls[#controls+1] = control end
                end
                for _, control in ipairs(ui.enhancementSwitchButtons or {}) do if control:IsVisible() then controls[#controls+1] = control end end
                for i, control in ipairs(controls) do
                    H.expectBounded(control, ui.listToolbar, label .. " toolbar control")
                    for j=i+1,#controls do
                        local other = controls[j]
                        local overlaps = control:GetLeft() < other:GetRight()-0.5 and control:GetRight() > other:GetLeft()+0.5
                            and control:GetBottom() < other:GetTop()-0.5 and control:GetTop() > other:GetBottom()+0.5
                        assert(not overlaps, label .. " toolbar hit targets overlap")
                    end
                end
            end
            ui:SetInspectorVisible(false); H.settle()
        end
    end
end
assert(#H.errors == 0, table.concat(H.errors,"\n"))
''')

    def test_filter_scrollbar_exists_only_for_actual_overflow(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); ui.frame:SetSize(1160,900); H.settle()
local scroll = ui.filterDrawerScroll
scroll.ScrollBar = CreateFrame("Slider", nil, scroll)
local listHeight = ui.contentScroll:GetHeight()
ui:SetFilterDrawerOpen(true); H.settle()
near(ui.contentScroll:GetHeight(), listHeight, "opening filters preserves viewport")
near(scroll:GetVerticalScrollRange(), 0, "fitting filters have zero range")
assert(not scroll.ScrollBar:IsShown() and not scroll.ScrollBar:IsEnabled(), "fitting filters retain scrollbar")
ui.frame:SetHeight(560); H.settle()
assert(scroll:GetVerticalScrollRange() > 2, "constrained filters should genuinely overflow")
assert(scroll.ScrollBar:IsShown() and scroll.ScrollBar:IsEnabled(), "overflowing filters have no scrollbar")
scroll:SetVerticalScroll(30); H.settle()
assert(scroll:GetVerticalScroll() == 30, "genuine overflow cannot scroll")
ui.frame:SetHeight(900); H.settle()
near(scroll:GetVerticalScroll(), 0, "expanding filters clamps old offset")
near(scroll:GetVerticalScrollRange(), 0, "expanded filters have zero range")
assert(not scroll.ScrollBar:IsShown(), "expanded filters retain obsolete scrollbar")
''')

    def test_screen_clamped_details_returns_to_the_same_list_and_selection(self):
        self.run_lua(r'''
UIParent:SetSize(900,900); ui.frame:SetSize(900,660); ui:SetTab("By Slot"); H.settle()
local data
for _, entry in ipairs(ui.renderModel.entries) do if entry.kind == "row" then data=entry.data; break end end
ui.contentScroll:SetVerticalScroll(180); H.settle()
local offset = ui.contentScroll:GetVerticalScroll()
local builds = ui:GetPerformanceStats().queryBuilds
ui:ShowInspectorFor(data.item_id,data,"phase"); H.settle()
assert(ui.inspectorExclusive and not ui.inspectorDocked, "below-minimum Details should be a dedicated view")
assert(not ui.contentRegion:IsVisible() and ui.detailsBackButton:IsVisible(), "dedicated Details exposes hidden list")
H.expectBounded(ui.details, ui.body, "dedicated Details")
H.expectBounded(ui.phaseBar, ui.contextBar, "wrapped context")
local key = ui.selectedRowKey
ui.detailsBackButton:Click(); H.settle()
assert(ui.contentRegion:IsVisible() and not ui.details:IsShown(), "Back to list failed")
near(ui.contentScroll:GetVerticalScroll(), offset, "Back to list scroll position")
assert(ui.selectedRowKey == key, "Back to list lost selection")
assert(ui:GetPerformanceStats().queryBuilds == builds, "Details navigation rebuilt list query")
assert(ui.useCharacterButton.label:GetText() == "Current Spec", "character action label")
assert(ui.levelCurrentButton.label:GetText() == "Current Level", "level action label")
assert(ui.useCharacterButton:GetLeft() >= ui.specDropdown:GetRight(), "Current Spec is detached from spec selector")
''')


if __name__ == "__main__":
    unittest.main()
