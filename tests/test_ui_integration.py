"""Assembled addon smoke tests in a simulated Lua 5.1 frame environment."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


class UIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, script):
        if not self.lua:
            self.skipTest("Lua 5.1 is not available")
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, input=script,
            capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_assembled_views_density_and_inspector_geometry(self):
        self.run_lua(r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:CreateMainFrame()
ui:Open()
H.settle()
local selection = ui:GetSelection()
selection.class, selection.spec, selection.phase = "Druid", "Feral dps", "T4"
local saved = BigBiSList:GetCharacterDB().wishlist
local seeded = 0
for _, entry in ipairs((ui.renderModel and ui.renderModel.entries) or {}) do
    if entry.kind == "row" and entry.data.item_id and seeded < 3 then
        saved[tostring(entry.data.item_id)] = true
        if seeded == 0 then H.equipped[1] = entry.data.item_id end
        seeded = seeded + 1
    end
end
assert(seeded > 0, "real canonical data produced no fixture items")
for _, size in ipairs({ { 1020, 560 }, { 1160, 660 } }) do
    ui.frame:SetSize(size[1], size[2])
    for _, density in ipairs({ "comfortable", "compact" }) do
        BigBiSListDB.profile.window.density = density
        for _, mode in ipairs({ "endgame", "leveling" }) do
            ui:SetContentMode(mode)
            H.settle()
            local tabs = mode == "endgame" and { "Upgrades", "By Slot", "Equipped", "Enhance", "Wishlist", "Settings" } or { "Gear Guide", "Equipped", "Wishlist", "Settings" }
            for _, tab in ipairs(tabs) do
                ui:SetTab(tab)
                ui:Invalidate("all", "integration")
                ui:Refresh("integration")
                H.settle()
                local label = size[1] .. "x" .. size[2] .. "/" .. density .. "/" .. mode .. "/" .. tab
                H.expectBounded(ui.body, ui.frame, label .. " body")
                H.expectBounded(ui.contentPanel, ui.body, label .. " content")
                assert(ui.contentScroll:GetWidth() > 0 and ui.contentScroll:GetHeight() > 0, label .. " has no content viewport")
                for _, entry in ipairs((ui.renderModel and ui.renderModel.entries) or {}) do
                    assert(entry.height >= 0, label .. " has negative row height")
                    if entry.kind == "row" and tab ~= "Equipped" then
                        assert(entry.height == (density == "compact" and 40 or 56), label .. " row density mismatch")
                    end
                end
                H.expectRowsBounded(ui, label)
                if tab ~= "Settings" then
                    local width = ui.contentPanel:GetWidth()
                    local viewportHeight = ui.contentScroll:GetHeight()
                    local queries = ui:GetPerformanceStats().queryBuilds
                    if size[1] == 1160 and density == "comfortable" and tab ~= "Equipped" then
                        assert(viewportHeight >= 7 * 56, label .. " cannot show seven complete rows")
                    end
                    assert(#(ui.activeRenderFrames or {}) <= math.ceil(viewportHeight / 28) + 8, label .. " realization is not bounded by the viewport")
                    ui:SetFilterDrawerOpen(true)
                    H.settle()
                    assert(math.abs(ui.contentPanel:GetWidth() - width) < 1, label .. " filters changed list width")
                    assert(math.abs(ui.contentScroll:GetHeight() - viewportHeight) < 1, label .. " filters changed viewport height")
                    assert(ui:GetPerformanceStats().queryBuilds == queries, label .. " opening filters rebuilt the data query")
                    H.expectBounded(ui.filterDrawer, ui.body, label .. " filter overlay")
                    local controls = {}
                    for _, control in pairs(ui.filterDrawerControls) do
                        if control:IsVisible() and control:GetParent() == ui.filterDrawerContent then
                            H.expectHorizontalBounds(control, ui.filterDrawer, label .. " advanced filter")
                            controls[#controls + 1] = control
                        end
                    end
                    table.sort(controls, function(a, b) return a:GetTop() > b:GetTop() end)
                    for index = 2, #controls do
                        assert(controls[index]:GetTop() <= controls[index - 1]:GetBottom() + 1, label .. " filter click targets overlap")
                    end
                    ui:SetFilterDrawerOpen(false)
                    H.settle()
                    local row
                    for _, entry in ipairs((ui.renderModel and ui.renderModel.entries) or {}) do if entry.kind == "row" and entry.data and entry.data.item_id then row = entry.data; break end end
                    if row then
                        ui:ShowInspectorFor(row.item_id, row, ui.renderModel.mode)
                        H.settle()
                        H.expectBounded(ui.details, ui.body, label .. " inspector")
                        H.expectBounded(ui.detailsHeader, ui.details, label .. " fixed identity")
                        assert(ui.detailsScroll:GetTop() <= ui.detailsHeader:GetBottom(), label .. " details scroll overlaps identity")
                        assert(ui.inspectorDocked and not ui.inspectorExclusive, label .. " inspector must dock at supported widths")
                        assert(ui.contentPanel:GetRight() <= ui.details:GetLeft() - 7, label .. " inspector obstructs the list")
                        H.expectRowsBounded(ui, label .. " with inspector")
                        local inspectorWidth, inspectorHeight = ui.contentPanel:GetWidth(), ui.contentScroll:GetHeight()
                        ui:SetFilterDrawerOpen(true)
                        H.settle()
                        H.expectBounded(ui.filterDrawer, ui.body, label .. " filters with inspector")
                        assert(math.abs(ui.contentPanel:GetWidth() - inspectorWidth) < 1 and math.abs(ui.contentScroll:GetHeight() - inspectorHeight) < 1, label .. " combined overlays changed the viewport")
                        ui:SetFilterDrawerOpen(false)
                        ui:SetInspectorVisible(false)
                        H.settle()
                    end
                end
            end
        end
    end
end
assert(#H.errors == 0, table.concat(H.errors, "\n"))
''')

    def test_cached_item_names_recover_width_and_cold_rebind_preserves_full_text(self):
        self.run_lua(r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:Open()
H.settle()
local parent = CreateFrame("Frame", nil, UIParent)
parent:SetSize(ui.contentScroll:GetWidth(), 100)
BigBiSListDB.profile.window.density = "compact"
local name = "Mantle of the Ancient Forest Guardian of the Emerald Dream"
H.itemNames[999991] = name
local data = { item_id = 999991, name = name, slot = "Shoulder", rank_group = "bis", rank_label = "BiS" }
local row = ui:CreateDataRow(parent, 0, data, "phase")
assert(row.nameText.fullText == name, "fresh item lost original name")
assert(row.nameText.isTruncated, "narrow row did not exercise truncation")
ui.frame:SetSize(1800, 660)
H.settle()
parent:SetWidth(ui.contentScroll:GetWidth())
ui:CreateDataRow(parent, 0, data, "phase", row)
assert(row.nameText.fullText == name, "cached item kept truncated source")
assert(row.nameText:GetText() == name, "name did not recover after widening: width " .. row.nameText:GetWidth() .. " text " .. row.nameText:GetText())
H.coldItems[999992] = true
local coldName = "Newly discovered item with a different uncached name"
ui:CreateDataRow(parent, 0, { item_id = 999992, name = coldName, slot = "Shoulder" }, "phase", row)
assert(row.nameText.fullText == coldName, "recycled row retained previous item's full text")
assert(row.iconButton.itemLink == nil, "recycled cold row retained previous link")
assert(row.iconButton.itemId == 999992, "recycled row retained previous item identity")
''')

    def test_actual_row_gestures_wishlist_undo_enhancements_and_tooltip(self):
        self.run_lua(r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:Open()
H.settle()
ui:SetTab("By Slot")
H.settle()
local row
for _, candidate in ipairs(ui.activeRenderFrames or {}) do
    if candidate.boundData and candidate.boundData.item_id then row = candidate; break end
end
assert(row, "canonical item rows were not realized")
local data, itemId = row.boundData, row.boundData.item_id
H.modifiers.shift = true
row.scripts.OnMouseUp(row, "LeftButton")
assert(H.chatLink == "item:" .. itemId, "Shift row click did not link item")
H.modifiers.shift, H.modifiers.control = false, true
row.scripts.OnMouseUp(row, "LeftButton")
assert(H.previewLink == "item:" .. itemId, "Control row click did not preview item")
H.modifiers.control = false
row.scripts.OnMouseUp(row, "RightButton")
assert(ui.itemActionMenu, "right click did not expose action menu")
assert(not BigBiSList:GetCharacterDB().wishlist[tostring(itemId)], "right click mutated wishlist")
row.actionButton:Click()
H.settle()
assert(BigBiSList:GetCharacterDB().wishlist[tostring(itemId)], "star did not save item")
assert(ui:UndoLastAction(), "wishlist change exposed no undo")
H.settle()
assert(not BigBiSList:GetCharacterDB().wishlist[tostring(itemId)], "undo did not restore wishlist")
ui:ShowInspectorFor(itemId, data, "phase")
H.settle()
local icon = ui.detailsIdentity.iconButton
icon.scripts.OnEnter(icon)
assert(GameTooltip.hyperlink == "item:" .. itemId, "header hover did not preserve native tooltip: expected " .. tostring(itemId) .. ", got " .. tostring(GameTooltip.hyperlink) .. ", icon " .. tostring(icon.itemLink) .. " errors " .. table.concat(H.errors, ";"))
H.modifiers.alt = true
BigBiSList.tooltipModifierFrame.scripts.OnEvent(nil, "MODIFIER_STATE_CHANGED", "LALT")
local headings = 0
for _, line in ipairs(GameTooltip.lines) do if line == "Big BiS List" then headings = headings + 1 end end
assert(headings == 1, "expanded tooltip duplicated or lost addon section")
assert(GameTooltip.lines[1] == "Native: item:" .. itemId, "native tooltip line changed")
H.modifiers.alt = false
BigBiSList.tooltipModifierFrame.scripts.OnEvent(nil, "MODIFIER_STATE_CHANGED", "LALT")
ui:SetInspectorVisible(false)
ui:SetTab("Enhance")
H.settle()
for _, kind in ipairs({ "gem", "enchant", "consumable" }) do
    ui:SetViewStateValue("Enhance", "type", kind)
    H.settle()
    H.expectRowsBounded(ui, "enhancement " .. kind)
    for _, entry in ipairs((ui.renderModel and ui.renderModel.entries) or {}) do
        if entry.kind == "row" then
            assert(entry.data.enhancement_kind == kind, "enhancement scope retained wrong kind")
            local id = entry.data.entity_id or entry.data.spell_id or entry.data.item_id
            ui:ShowInspectorFor(id, entry.data, "enhance")
            H.settle()
            if entry.data.entity_type == "spell" then
                assert(not ui.detailsIdentity.star:IsShown(), "spell exposes wishlist action")
            end
            ui:SetInspectorVisible(false)
            break
        end
    end
end
assert(#H.errors == 0, table.concat(H.errors, "\n"))
''')


if __name__ == "__main__":
    unittest.main()
