"""Regression coverage for native callbacks during pooled list realization."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


BOOTSTRAP = r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:Open()
H.settle()
local function assertOwnership(label)
    local owned, active, entries = {}, {}, {}
    for _, entry in ipairs(ui.renderModel and ui.renderModel.entries or {}) do entries[entry] = true end
    for _, frame in ipairs(ui.activeRenderFrames or {}) do
        assert(not owned[frame], label .. ": duplicate active frame")
        owned[frame], active[frame] = "active", true
        assert(frame:IsShown(), label .. ": active frame is hidden")
        assert(ui:IsCurrentRenderFrame(frame), label .. ": stale active binding")
        assert(entries[frame.__bigBisBoundRenderEntry], label .. ": active frame belongs to another model")
        assert(not ui.renderPoolMembership[frame], label .. ": active frame remains pooled")
    end
    for kind, pool in pairs(ui.renderPools or {}) do
        for _, frame in ipairs(pool) do
            assert(not owned[frame], label .. ": duplicate ownership in " .. kind)
            owned[frame] = kind
            assert(not frame:IsShown(), label .. ": pooled frame is shown")
            assert(ui.renderPoolMembership[frame] == kind, label .. ": missing pool ownership")
            assert(not frame.__bigBisBoundRenderModel, label .. ": pooled frame retains its model")
        end
    end
    for _, frame in ipairs(H.frames) do
        if frame:GetParent() == ui.contentListLayer and frame.__bigBisManaged then
            assert(owned[frame], label .. ": orphan managed child")
            assert(not frame:IsShown() or active[frame], label .. ": visible orphan managed child")
        end
    end
    assert((ui.renderTransactionDepth or 0) == 0, label .. ": transaction did not finish")
    assert(#H.errors == 0, table.concat(H.errors, "\n"))
end
'''


class UIRenderTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, script):
        if not self.lua:
            self.skipTest("Lua 5.1 is not available")
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, input=BOOTSTRAP + script,
            capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_scroll_during_release_cannot_leak_a_section_into_my_gear(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
ui.contentScroll:SetVerticalScroll(400); H.settle()
local first, fired = ui.activeRenderFrames[1], false
first:HookScript("OnHide", function()
    if fired then return end
    fired = true
    ui.contentScroll:SetVerticalScroll(0)
end)
ui:SetTab("Equipped"); H.settle()
assert(fired, "regression did not exercise the reentrant native callback")
assertOwnership("My Gear after reentrant release")
for _, frame in ipairs(ui.activeRenderFrames) do
    assert(frame.__bigBisBoundRenderEntry.kind == "row", "foreign section remains in My Gear")
    assert(frame.boundMode == "gear", "foreign recommendation remains in My Gear")
end
''')

    def test_scroll_during_binding_uses_latest_viewport_without_rebuilding_query(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
local bind = ui.CreateDataRow
local binding, maximumDepth, depth = false, 0, 0
local queries = ui:GetPerformanceStats().queryBuilds
ui.CreateDataRow = function(self, ...)
    depth = depth + 1; maximumDepth = math.max(maximumDepth, depth)
    if not binding then
        binding = true
        self.contentScroll:SetVerticalScroll(500)
        self.contentScroll:SetVerticalScroll(700)
    end
    local frame, height = bind(self, ...)
    depth = depth - 1
    return frame, height
end
ui:UpdateVirtualList(true); H.settle()
assert(maximumDepth == 1, "row binding was reentered")
assert(ui.contentScroll:GetVerticalScroll() == 700, "latest scroll position was lost")
assert(ui:GetPerformanceStats().queryBuilds == queries, "scroll triggered a data-query rebuild")
for _, frame in ipairs(ui.activeRenderFrames) do
    local entry = frame.__bigBisBoundRenderEntry
    assert(entry.bottom >= 580, "old viewport row remained realized")
end
assertOwnership("latest viewport after reentrant binding")
''')

    def test_stale_section_click_does_not_mutate_another_workspace(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
local old
for _, frame in ipairs(ui.activeRenderFrames) do
    if frame.__bigBisBoundRenderEntry.kind == "section" then old = frame; break end
end
assert(old, "missing section fixture")
local key = old.sectionKey
ui:SetTab("Equipped"); H.settle()
ui.contentScroll:SetVerticalScroll(120); H.settle()
local before = ui.contentScroll:GetVerticalScroll()
old:Click(); H.settle()
assert(not (ui:GetViewState().collapsedGroups or {})[key], "stale click changed current workspace state")
assert(ui.contentScroll:GetVerticalScroll() == before, "stale click moved the current viewport")
assertOwnership("after stale section click")
ui:SetTab("By Slot"); H.settle()
local current
for _, frame in ipairs(ui.activeRenderFrames) do
    if frame.__bigBisBoundRenderEntry.kind == "section" then current = frame; break end
end
assert(current, "missing current section")
local currentKey = current.sectionKey
current:Click(); H.settle()
assert(ui:GetViewState().collapsedGroups[currentKey], "current section no longer collapses")
assertOwnership("after current section click")
''')

    def test_multi_workspace_transitions_keep_unique_pool_ownership(self):
        self.run_lua(r'''
for _, density in ipairs({ "comfortable", "compact" }) do
    BigBiSListDB.profile.window.density = density
    for _, tab in ipairs({ "By Slot", "Equipped", "Enhance", "Upgrades", "Equipped", "By Slot" }) do
        local frame = ui.activeRenderFrames[1]
        local fired = false
        if frame then
            frame:HookScript("OnHide", function()
                if fired then return end
                fired = true
                ui.contentScroll:SetVerticalScroll(0)
            end)
        end
        ui:SetTab(tab); H.settle()
        ui.contentScroll:SetVerticalScroll(ui.contentScroll:GetVerticalScrollRange()); H.settle()
        assertOwnership(density .. "/" .. tab .. " bottom")
        ui.contentScroll:SetVerticalScroll(0); H.settle()
        assertOwnership(density .. "/" .. tab .. " top")
    end
end
''')

    def test_successful_realization_recovers_a_stranded_managed_section(self):
        self.run_lua(r'''
ui:SetTab("Equipped"); H.settle()
local stale = ui:CreateVirtualSectionHeader(ui.contentListLayer, -400, "Stranded section", nil, { sectionKey="old", count=1 })
local unrelated = CreateFrame("Frame", nil, ui.contentListLayer)
ui:UpdateVirtualList(true); H.settle()
assert(not stale:IsShown(), "stranded section remains visible")
assert(unrelated:IsShown(), "recovery hid an unrelated child")
assertOwnership("after orphan recovery")
''')


if __name__ == "__main__":
    unittest.main()
