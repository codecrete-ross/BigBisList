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
dofile("DataIndex.lua")
dofile("UI.lua")
BigBiSList:EnsureDatabase()
local UI = BigBiSList.UI
function UI:ScheduleRefresh() end
function UI:ScheduleLayoutRefresh() end
local function equal(actual, expected, label)
    assert(actual == expected, (label or "value") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end
'''


@unittest.skipUnless(LUA, "Lua is unavailable")
class UIModelTests(unittest.TestCase):
    def run_lua(self, body):
        result = subprocess.run(
            [LUA, "-"], input=BOOTSTRAP + body, cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_activity_groups_use_only_the_selected_acquisition_route(self):
        self.run_lua(r'''
for _, kind in ipairs({"raid_drop", "dungeon_drop", "heroic_dungeon_drop", "quest"}) do
    local selected = { source_filter_key=kind, zone="The Slave Pens" }
    local alternative = { source_filter_key="raid_drop", zone="Karazhan" }
    local row = {
        acquisition_display={option=selected,source_label="Selected source"},
        matched_access_option=alternative, access_options={selected,alternative},
    }
    equal(BigBiSList:GetActivityGroup(row), "The Slave Pens", kind .. " selected route")
    equal(row.acquisition_display.option, selected, "grouping preserves route identity")
end
equal(BigBiSList:GetActivityGroup({matched_access_option={source_filter_key="raid_drop", zones={{name="Karazhan"}}}}), "Karazhan", "normalized zone table")
equal(BigBiSList:GetActivityGroup({}), "Other activities", "unknown source bucket")
''')

    def test_activity_groups_cover_trade_reputation_crafting_and_vendors(self):
        self.run_lua(r'''
local function group(option) return BigBiSList:GetActivityGroup({acquisition_display={option=option}}) end
equal(group({is_trade_option=true}), "Trade / Auction House", "trade")
equal(group({reputations={"The Sha'tar"},vendor_label="Almaador"}), "Reputation · The Sha'tar", "reputation before seller")
equal(group({requirements={{type="profession",profession="Tailoring"}}}), "Crafting · Tailoring", "profession")
equal(group({vendor_label="G'eras"}), "Vendor · G'eras", "currency vendor")
''')

    def test_density_and_collapsed_sections_keep_counts_without_unbounded_rows(self):
        self.run_lua(r'''
for _, density in ipairs({"comfortable", "compact"}) do
    BigBiSListDB.profile.window.density = density
    local rowHeight, iconSize, maxLines = UI:GetDensityMetrics()
    equal(rowHeight, density == "compact" and 40 or 56, "density height")
    assert(iconSize < rowHeight and maxLines <= 2, "bounded row content")
    UI:GetViewState().collapsedGroups = { ["wishlist:Hidden"] = true }
    local model = UI:NewListRenderModel()
    UI:AddListSection(model, "Hidden", "wishlist")
    UI:AddListRow(model, {item_id=1}, "wishlist")
    UI:AddListRow(model, {item_id=2}, "wishlist")
    equal(#model.entries, 1, "collapsed section contains no row entries")
    equal(model.entries[1].count, 2, "collapsed count includes its results")
    UI:AddListSection(model, "Visible", "wishlist")
    local data = {item_id=3,name=string.rep("Long name ",100),relevant_spec_rankings={}}
    for i=1,30 do data.relevant_spec_rankings[i]={rank="BiS"} end
    UI:AddListRow(model, data, "wishlist")
    equal(model.rowCount, 3, "result count includes collapsed and visible rows")
    equal(model.entries[2].count, 1, "visible section count")
    equal(model.entries[3].height, rowHeight, "long content never expands a list row")
end
''')

    def test_activity_grouping_sorts_groups_and_preserves_query_objects(self):
        self.run_lua(r'''
local state = UI:GetViewState()
state.sort, state.sortDirection = "rank", "asc"
local raid = {source_filter_key="raid_drop",zone="Karazhan"}
local dungeon = {source_filter_key="dungeon_drop",zone="The Slave Pens"}
local rows = {
    {item_id=1,name="Zulu",rank_group="ranked",rank=2,acquisition_display={option=dungeon}},
    {item_id=2,name="Beta",rank_group="ranked",rank=2,acquisition_display={option=raid}},
    {item_id=3,name="Gamma",rank_group="bis",rank=1,acquisition_display={option=raid}},
}
function UI:RenderListModel(model) self.lastModel=model end
UI:RenderGroupedRows(rows, "phase", "activity", "Items")
local model = UI.lastModel
equal(model.entries[1].title, "Karazhan", "activity titles are sorted")
equal(model.entries[1].count, 2, "activity group count")
equal(model.entries[2].data, rows[3], "best recommendation leads its activity")
equal(model.entries[3].data, rows[2], "alternative follows")
equal(rows[1].item_id, 1, "query order remains untouched")
equal(rows[3].acquisition_display.option, raid, "route remains untouched")
equal(model.rowCount, 3, "each item appears exactly once")
''')

    def test_inspector_geometry_preserves_minimum_list_width(self):
        self.run_lua(r'''
local minimum = UI:GetBodyGeometry(1020-24, true, 0, true)
assert(minimum.docked and not minimum.exclusive, "minimum window docks details")
equal(minimum.listWidth, 1020-24-328, "split reserves inspector width")
local default = UI:GetBodyGeometry(1160-24, true, 0, true)
assert(default.docked, "default window docks details")
assert(default.listWidth-36 >= 632, "docked list keeps enough space for compact columns")
local threshold
for width=900,1200 do
    local geometry = UI:GetBodyGeometry(width,true,0,true)
    if geometry.docked then threshold=width; break end
end
assert(threshold, "docking threshold exists within supported sizes")
equal(threshold,996,"exact supported docking boundary")
local below = UI:GetBodyGeometry(threshold-1,true,0,true)
assert(not below.docked and below.exclusive,"below minimum uses dedicated details")
equal(below.detailsWidth,threshold-1,"dedicated details uses full available width")
local chips = UI:GetBodyGeometry(1160-24,true,28,true)
equal(chips.listWidth,default.listWidth,"filter chips do not change horizontal layout")
assert(chips.top > default.top,"single chip row gets its own vertical budget")
equal(UI:GetBodyGeometry(1160-24,false,0,false).top,0,"equipment/settings reclaim toolbar height")
''')

    def test_default_recommendation_order_is_preserved_for_guide_and_wishlist(self):
        self.run_lua(r'''
for _, context in ipairs({{mode="leveling",tab="Gear Guide"},{mode="wishlist",tab="Wishlist"}}) do
    if context.mode == "leveling" then BigBiSList:SetContentMode("leveling") else BigBiSList:SetContentMode("endgame") end
    BigBiSList:SetSelection(nil,nil,nil,context.tab)
    local state = UI:GetViewState()
    state.sort, state.sortDirection = "item", "desc"
    UI:SelectSort("priority")
    equal(state.sortDirection,"asc",context.mode .. " default priority direction")
    -- The data layer has already ranked active level bands, or ownership/relevance/phase.
    local rows = {
        {item_id=1,name="Zulu",rank=1,level_min=40,level_max=69,default_sort={owned=0,relevance=0,rank=1,phase=1}},
        {item_id=2,name="Alpha",rank=2,level_min=20,level_max=39,default_sort={owned=1,relevance=2,rank=999,phase=4}},
    }
    local forward=UI:SortDisplayRows(rows,context.mode)
    equal(forward[1],rows[1],context.mode .. " native recommendation order")
    state.sortDirection="desc"
    equal(UI:SortDisplayRows(rows,context.mode)[1],rows[2],context.mode .. " reversed recommendation order")
    equal(rows[1].name,"Zulu",context.mode .. " source query remains immutable")
end
''')

    def test_slot_and_enhancement_orders_are_semantic(self):
        self.run_lua(r'''
local state=UI:GetViewState()
state.sort,state.sortDirection="slot","asc"
local rows={{item_id=1,name="A Boots",slot="Feet"},{item_id=2,name="Z Helm",slot="Head"}}
equal(UI:SortDisplayRows(rows,"phase")[1].item_id,2,"slot order follows equipment layout")
state.sort="recommendation"
rows={{item_id=1,name="A budget enchant",rank=2},{item_id=2,name="Z recommended enchant",rank=1}}
equal(UI:SortDisplayRows(rows,"enhance")[1].item_id,2,"recommendation order follows rank")
''')


if __name__ == "__main__":
    unittest.main()
