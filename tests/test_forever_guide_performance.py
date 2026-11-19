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
'''


class ForeverGuidePerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()
        if not cls.lua:
            raise unittest.SkipTest("Lua 5.1 is unavailable")

    def lua_run(self, code: str):
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, timeout=120, encoding="utf-8",
                                capture_output=True, input=SETUP + code + "\nassert(#H.errors == 0, table.concat(H.errors, '\\n'))")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

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
addon:InitUIEvents()
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
assert(ui.renderModel.rowCount > 40000 and #ui.renderModel.entries < 100)
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
assert(ui.renderModelSerial == serial)
ui:SetFilterDrawerOpen(false)
worn = 7719
frame:GetScript("OnEvent")(frame, "PLAYER_EQUIPMENT_CHANGED", 1)
H.settle()
assert(ui.renderModelSerial > serial and ui:CaptureNavigationState().anchorKey == position.anchorKey)
assert(ui:CaptureNavigationState().anchorOffset == position.anchorOffset)
''')

    def test_cold_native_tooltip_and_exact_search_share_the_same_helm_rank(self):
        self.lua_run(r'''
function rating:GetGuidePlacement() error("A native hover must read its indexed rank") end
local tip = GameTooltip
tip:SetOwner(UIParent)
tip.hyperlink = "item:7719"
tip:Show()
addon:AddTooltipInfo(tip, { id = 7719, hyperlink = tip.hyperlink, getterName = "GetBagItem", getterArgs = {0, 1}, lines = {} })
local lines = table.concat(tip.lines or {}, "\n")
assert(lines:find("Slight upgrade", 1, true) and lines:find("+2.1 pts vs Gothic Plate Helmet of the Gorilla", 1, true), lines)

local filters = ui:GetFilters("Gear Guide")
filters.slots, filters.search = { Head = true }, "Gothic Plate Helmet of the Gorilla"
ui:Open()
H.settle()
local candidate
ui:VisitListEntries(ui.renderModel, 0, math.huge, function(entry)
    if entry.data and entry.data.stat_identity == "10090:0:0:0:1:12723" then candidate = entry.data end
end)
assert(candidate and candidate.stat_rank.rank == 144 and candidate.stat_rank.total == 2810)
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
local new = {}
for field, value in pairs(old.item) do new[field] = value end
new.stats = {strength = 200}
guide.catalog.observed[variant] = new
guide.catalog.changedSlots, guide.catalog.observedVersion = {Head = true}, 1
local updated = assert(rating:GetGuideEntry(guide, "Head", variant))
assert(updated.rank == 1 and updated.total == old.total and updated.score > old.score)
assert(rating:GetGuideEntry(guide, "Head", "9479").rank == 2)
''')
