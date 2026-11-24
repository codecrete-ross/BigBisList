"""Direct tier selection, live-state independence, and responsive context geometry."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


class UIPhaseSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body):
        if not self.lua:
            self.skipTest("Lua 5.1 is unavailable")
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, input=r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:Open(); H.settle()
local phases = { "PR", "T4", "T5", "T6", "ZA", "SWP" }
local labels = { "Pre-Raid", "Tier 4", "Tier 5", "Tier 6", "Zul'Aman", "Sunwell" }
local widths = { 68, 54, 54, 54, 68, 60 }
local function near(a, b, label)
    assert(math.abs(a-b) <= .6, label .. ": " .. tostring(a) .. " vs " .. tostring(b))
end
local function centerY(frame) return frame:GetBottom() + frame:GetHeight()/2 end
local function expectDisjoint(a, b, label)
    local overlaps = a:GetLeft() < b:GetRight()-.5 and a:GetRight() > b:GetLeft()+.5
        and a:GetBottom() < b:GetTop()-.5 and a:GetTop() > b:GetBottom()+.5
    assert(not overlaps, label .. " overlaps")
end
''' + body + r'''
assert(#H.errors == 0, table.concat(H.errors, "\n"))
''', capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_all_six_phases_are_direct_targets_with_bounded_centered_labels(self):
        self.run_lua(r'''
assert(#ui.phaseSelector.buttons == 6, "selector should expose all six phases")
local prior
for index, phase in ipairs(phases) do
    local button = ui.phaseButtons[phase]
    assert(button == ui.phaseSelector.buttons[index], "canonical phase order changed")
    assert(button:IsVisible() and button:IsEnabled(), phase .. " is inaccessible")
    assert(button.label:GetText() == labels[index], phase .. " label")
    near(button:GetHeight(), 28, phase .. " hit target height")
    assert(button:GetWidth() >= widths[index]-.5, phase .. " minimum width")
    assert(button:GetWidth() >= button.label:GetStringWidth()+16-.5, phase .. " text padding")
    near(centerY(button.label), centerY(button), phase .. " centered label")
    H.expectBounded(button, ui.phaseSelector, phase .. " button")
    H.expectBounded(button.label, button, phase .. " label")
    assert(button.liveCaption:GetTop() <= button:GetBottom()+.5, phase .. " live caption overlaps target")
    H.expectBounded(button.liveCaption, ui.phaseSelector, phase .. " reserved caption")
    if prior then near(button:GetLeft(), prior:GetRight(), phase .. " joined surface") end
    prior = button
end
near(ui.phaseSelector:GetHeight(), 40, "permanent caption strip")
''')

    def test_measured_label_growth_reflows_and_shrinks_context_without_query_work(self):
        self.run_lua(r'''
ui.frame:SetSize(1020,560); H.settle()
local button = ui.phaseButtons.SWP
local font, fontSize, flags = button.label:GetFont()
local oldWidth = ui.phaseSelector:GetWidth()
local builds = ui:GetPerformanceStats().queryBuilds
button.label:SetText("Sunwell Plateau")
button.label:SetFont(font, 24, flags)
ui:LayoutContextControls(); H.settle()
assert(button:GetWidth() >= button.label:GetStringWidth()+16-.5, "large font lost measured padding")
assert(ui.phaseSelector:GetWidth() > oldWidth, "long label did not grow selector")
near(ui.contextBar:GetHeight(), 96, "larger labels wrap context")
H.expectBounded(ui.phaseSelector, ui.contextBar, "grown selector")
for _, segment in ipairs(ui.phaseSelector.buttons) do
    H.expectBounded(segment, ui.phaseSelector, "grown segment")
    H.expectBounded(segment.label, segment, "grown segment label")
end
button.label:SetText("Sunwell")
button.label:SetFont(font, fontSize, flags)
ui:LayoutContextControls(); H.settle()
near(ui.phaseSelector:GetWidth(), oldWidth, "normal font restores selector width")
near(ui.contextBar:GetHeight(), 60, "normal font restores context line")
assert(ui:GetPerformanceStats().queryBuilds == builds, "measuring and reflowing rebuilt query")
''')

    def test_phase_clicks_select_once_and_repeated_clicks_preserve_navigation(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
local selectorWidth, contextHeight = ui.phaseSelector:GetWidth(), ui.contextBar:GetHeight()
local viewportHeight = ui.contentScroll:GetHeight()
for _, phase in ipairs(phases) do
    ui.phaseButtons[phase]:Click(); H.settle()
    assert(ui:GetSelection().phase == phase, phase .. " click selects wrong phase")
    near(ui.phaseSelector:GetWidth(), selectorWidth, phase .. " selection changed width")
    near(ui.contextBar:GetHeight(), contextHeight, phase .. " selection changed context height")
    near(ui.contentScroll:GetHeight(), viewportHeight, phase .. " selection changed viewport height")
    for _, other in ipairs(phases) do
        assert((ui.phaseButtons[other].selected == true) == (other == phase), phase .. " selected state")
    end
end
ui.phaseButtons.T4:Click(); H.settle()
local data
for _, entry in ipairs(ui.renderModel.entries) do
    if entry.kind == "row" then data = entry.data; break end
end
assert(data, "fixture needs a recommendation")
ui:ShowInspectorFor(data.item_id, data, "phase"); H.settle()
ui.contentScroll:SetVerticalScroll(150); H.settle()
ui.detailsScroll:SetVerticalScroll(math.min(35, ui.detailsScroll:GetVerticalScrollRange())); H.settle()
local key = ui.selectedRowKey
local offset, detailsOffset = ui.contentScroll:GetVerticalScroll(), ui.detailsScroll:GetVerticalScroll()
local model, builds = ui.renderModel, ui:GetPerformanceStats().queryBuilds
ui.phaseButtons.T4:Click(); H.settle()
assert(ui:GetPerformanceStats().queryBuilds == builds, "selected phase rebuilt query")
assert(ui.renderModel == model, "selected phase replaced model")
assert(ui.selectedRowKey == key, "selected phase cleared item selection")
near(ui.contentScroll:GetVerticalScroll(), offset, "selected phase list position")
near(ui.detailsScroll:GetVerticalScroll(), detailsOffset, "selected phase Details position")
''')

    def test_live_rollover_only_moves_caption_and_keeps_future_choices_enabled(self):
        self.run_lua(r'''
ui.phaseButtons.T4:Click(); H.settle()
local builds = ui:GetPerformanceStats().queryBuilds
local width, height = ui.phaseSelector:GetWidth(), ui.contextBar:GetHeight()
local viewport = ui.contentScroll:GetHeight()
local livePhase = "T5"
BigBiSList.GetCurrentPhaseKey = function() return livePhase end
for _, nextPhase in ipairs({ "T5", "T6", "ZA", "SWP" }) do
    livePhase = nextPhase
    ui.phaseSelector:Refresh(); ui:RefreshControls(); H.settle()
    for _, phase in ipairs(phases) do
        local button = ui.phaseButtons[phase]
        local showsLive = button.liveCaption:IsVisible() and button.liveCaption:GetText() == "Live"
        assert(showsLive == (phase == livePhase), phase .. " live state is coupled to selection")
        assert((button.selected == true) == (phase == "T4"), phase .. " rollover changed selection")
        assert(button:IsEnabled(), phase .. " manual browsing disabled")
    end
    assert(ui:GetSelection().phase == "T4", "rollover overwrote explicit phase")
    near(ui.phaseSelector:GetWidth(), width, "rollover selector width")
    near(ui.contextBar:GetHeight(), height, "rollover context height")
    near(ui.contentScroll:GetHeight(), viewport, "rollover viewport height")
end
assert(ui:GetPerformanceStats().queryBuilds == builds, "caption refresh rebuilt queries")
''')

    def test_segment_tooltips_compose_with_hover_press_selection_and_focus(self):
        self.run_lua(r'''
ui.phaseButtons.SWP:Click(); H.settle()
local button = ui.phaseButtons.SWP
local function fire(event, ...) button:GetScript(event)(button, ...) end
fire("OnEnter")
assert(button.hovered and button.selected, "hover erased persistent selection")
assert(GameTooltip:IsOwned(button) and GameTooltip:IsShown(), "segment tooltip was lost")
assert(table.concat(GameTooltip.lines, "\n"):find("Sunwell Plateau", 1, true), "abbreviated phase needs its full tooltip name")
fire("OnMouseDown", "LeftButton")
assert(button.pressed and button.selected, "press erased selection")
fire("OnMouseUp", "LeftButton")
assert(not button.pressed and button.hovered and button.selected, "release lost hover or selection")
button:SetFocused(true)
assert(button.focused and button.selected and button.focusRing:IsShown(), "focus state failed")
fire("OnLeave")
assert(not button.hovered and not button.pressed and button.selected, "leaving selected segment erased state")
assert(not GameTooltip:IsShown(), "segment tooltip remained after leaving")
button:SetEnabled(false); button:Click(); H.settle()
assert(button.disabled and not button.pressed and button.selected, "disabled segment lost state")
button:SetEnabled(true)
button:Hide()
assert(not button.hovered and not button.pressed and not button.focused, "hidden segment leaked interaction state")
button:Show(); ui.phaseSelector:Refresh(); H.settle()
assert(button.selected, "rebinding lost current phase")
''')

    def test_explicit_phase_survives_character_workspace_mode_and_settings_navigation(self):
        self.run_lua(r'''
ui.phaseButtons.ZA:Click(); H.settle()
ui:SetClass("Warrior"); H.settle()
assert(ui.useCharacterButton:IsEnabled(), "manual context needs Current Spec")
ui.useCharacterButton:Click(); H.settle()
assert(ui:GetSelection().phase == "ZA", "Current Spec reset explicit phase")
for _, tab in ipairs({ "Equipped", "Enhance", "Wishlist", "By Slot", "Upgrades" }) do
    ui:SetTab(tab); H.settle()
    assert(ui.phaseSelector:IsVisible(), tab .. " hides phase selector")
    assert(ui:GetSelection().phase == "ZA" and ui.phaseButtons.ZA.selected, tab .. " loses explicit phase")
end
ui.levelingModeButton:Click(); H.settle()
assert(not ui.phaseSelector:IsVisible(), "Leveling retains phase control")
assert(ui.levelControlContainer:IsVisible(), "Leveling controls are missing")
ui.endgameModeButton:Click(); H.settle()
assert(ui.phaseSelector:IsVisible() and not ui.levelControlContainer:IsVisible(), "Endgame control restoration")
assert(ui:GetSelection().phase == "ZA" and ui.phaseButtons.ZA.selected, "mode return loses explicit phase")
ui:OpenSettings(); H.settle()
assert(not ui.phaseSelector:IsVisible(), "Settings retains phase control")
ui:ReturnFromSettings(); H.settle()
assert(ui.phaseSelector:IsVisible() and ui.phaseButtons.ZA.selected, "Settings return loses explicit phase")
ui.levelingModeButton:Click(); H.settle()
local levelingTab = ui:GetSelection().tab
ui:OpenSettings(); H.settle()
assert(ui:GetSelection().tab == "Settings" and not ui.contextBar:IsVisible(), "Leveling Settings did not open")
assert(not ui.phaseSelector:IsVisible() and not ui.levelControlContainer:IsVisible(), "Leveling Settings retains context controls")
ui:ReturnFromSettings(); H.settle()
assert(ui:GetSelection().tab == levelingTab and ui.levelControlContainer:IsVisible(), "Leveling Settings return lost workspace")
assert(not ui.phaseSelector:IsVisible(), "Leveling Settings return exposes phase selector")
ui.endgameModeButton:Click(); H.settle()
assert(ui.phaseButtons.ZA.selected, "Leveling Settings roundtrip reset explicit phase")
local sortRefresh, groupRefresh = 0, 0
local oldSort, oldGroup = ui.sortDropdown.Refresh, ui.groupDropdown.Refresh
ui.sortDropdown.Refresh = function(self) sortRefresh = sortRefresh+1; return oldSort(self) end
ui.groupDropdown.Refresh = function(self) groupRefresh = groupRefresh+1; return oldGroup(self) end
ui:RefreshControls(); H.settle()
assert(sortRefresh > 0 and groupRefresh > 0, "removing phase dropdown truncated control refreshes")
''')

    def test_context_targets_fit_with_details_and_filters_at_supported_and_clamped_sizes(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
for _, size in ipairs({ {1020,560}, {1160,660}, {900,660} }) do
    UIParent:SetSize(size[1] == 900 and 900 or 1920, 1080)
    ui.frame:SetSize(size[1], size[2]); H.settle()
    for _, density in ipairs({ "comfortable", "compact" }) do
        BigBiSListDB.profile.window.density = density
        ui:Invalidate("layout", "phase-density-test"); ui:Refresh(); H.settle()
        for _, details in ipairs({ false, true }) do
            ui:SetInspectorVisible(details); H.settle()
            for _, filters in ipairs({ false, true }) do
                local viewport = ui.contentScroll:GetHeight()
                ui:SetFilterDrawerOpen(filters); H.settle()
                local label = size[1] .. "/" .. density .. "/" .. tostring(details) .. "/" .. tostring(filters)
                near(ui.contentScroll:GetHeight(), viewport, label .. " filter viewport")
                near(ui.contextBar:GetHeight(), size[1] == 900 and 96 or 60, label .. " context height")
                local controls = { ui.classDropdown, ui.specDropdown, ui.useCharacterButton, ui.endgameModeButton, ui.levelingModeButton }
                for _, button in ipairs(ui.phaseSelector.buttons) do controls[#controls+1] = button end
                for index, control in ipairs(controls) do
                    assert(control:IsVisible(), label .. " hidden control")
                    H.expectBounded(control, ui.contextBar, label .. " context control")
                    for other=index+1,#controls do expectDisjoint(control, controls[other], label .. " context controls") end
                end
                H.expectBounded(ui.phaseSelector, ui.contextBar, label .. " selector")
                near(centerY(ui.phaseButtons.PR), centerY(ui.levelingModeButton), label .. " mode and phase alignment")
                assert(ui.useCharacterButton:GetLeft() >= ui.specDropdown:GetRight(), label .. " Current Spec placement")
                if size[1] == 900 then
                    assert(ui.endgameModeButton:GetTop() < ui.useCharacterButton:GetBottom(), "narrow context did not wrap together")
                else
                    near(centerY(ui.useCharacterButton), centerY(ui.endgameModeButton), label .. " single context line")
                end
            end
        end
        ui:SetFilterDrawerOpen(false); ui:SetInspectorVisible(false); H.settle()
    end
end
''')

    def test_default_ungrouped_comfortable_list_keeps_seven_complete_rows(self):
        self.run_lua(r'''
ui.frame:SetSize(1160,660)
BigBiSListDB.profile.window.density = "comfortable"
ui:SetTab("By Slot"); ui:SelectGrouping("none"); ui:SetInspectorVisible(false)
ui:SetFilterDrawerOpen(false); ui:Refresh(); H.settle()
ui.contentScroll:SetVerticalScroll(0); H.settle()
local complete = 0
local viewport = ui.contentScroll:GetHeight()
for _, entry in ipairs(ui.renderModel.entries) do
    if entry.kind == "row" and entry.top >= 0 and entry.bottom <= viewport+.5 then complete = complete+1 end
end
assert(complete >= 7, "default list exposes only " .. complete .. " complete rows")
ui:SetFilterDrawerOpen(true); H.settle()
near(ui.contentScroll:GetHeight(), viewport, "filters preserve default list viewport")
''')


if __name__ == "__main__":
    unittest.main()
