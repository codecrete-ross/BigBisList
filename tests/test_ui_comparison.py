"""The full-width comparison workspace uses the assembled UI navigation hooks."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


class ComparisonUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body):
        if not self.lua:
            self.skipTest("Lua 5.1 unavailable")
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
if not ui.OpenSlotComparison then assert(loadfile("ComparisonUI.lua"))("BigBiSList") end
ui:Open(); H.settle()
local function near(a,b,label) assert(math.abs(a-b)<.7,label..": "..a.." vs "..b) end
local function firstData()
    for _, entry in ipairs(ui.renderModel.entries) do if entry.kind=="row" and entry.data.item_id then return entry.data end end
end
''' + body + r'''
assert(#H.errors==0,table.concat(H.errors,"\n"))
''', capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_real_hooks_restore_results_and_details_without_changing_filters(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
local data = firstData(); assert(data,"fixture item")
ui:ShowInspectorFor(data.item_id,data,"phase"); H.settle()
ui.contentScroll:SetVerticalScroll(140); H.settle()
local offset, selected, model = ui.contentScroll:GetVerticalScroll(),ui.selectedRowKey,ui.renderModel
local filters = ui:GetFilters()
local initialSource = filters.sourceType
assert(ui:OpenSlotComparison(data,"phase")); H.settle()
assert(ui.comparisonFrame:IsVisible() and not ui.contentRegion:IsVisible(),"comparison must own the full content view")
assert(not ui.details:IsVisible(),"comparison retains docked Details")
assert(ui.renderModel==model,"opening comparison replaced origin model")
assert(ui:GetFilters()==filters and filters.sourceType==initialSource,"comparison changed origin filters")
local candidate = ui.slotComparison.rows[1]; assert(candidate,"comparison candidates")
ui:ShowInspectorFor(candidate.item_id,candidate,"comparison"); H.settle()
assert(ui.slotComparison.detailsOpen and ui.details:IsVisible(),"comparison Details did not open")
assert(ui.detailsBackButton.label:GetText()=="Back to comparison","missing comparison return")
assert(not ui.comparisonFrame:IsVisible(),"Details must have a dedicated content view")
ui.detailsBackButton:Click(); H.settle()
assert(not ui.slotComparison.detailsOpen and ui.comparisonFrame:IsVisible(),"Back to comparison failed")
ui.comparisonBackButton:Click(); H.settle()
assert(not ui:IsSlotComparisonOpen() and ui.contentRegion:IsVisible(),"Back to results failed")
assert(ui.renderModel==model and ui.selectedRowKey==selected,"origin row selection/model lost")
near(ui.contentScroll:GetVerticalScroll(),offset,"origin scroll")
assert(ui.details:IsVisible(),"origin Details state lost")
''')

    def test_physical_equipped_references_keep_duplicates_unknowns_and_empty_first(self):
        self.run_lua(r'''
ui.currentOwned = {equippedSlots={Finger0={item_id=999001},Finger1={item_id=999001}}}
ui:OpenSlotComparison({slot="Ring"}); H.settle()
local state = ui.slotComparison
assert(#state.pinned==2,"duplicate equipped items collapsed into one physical slot")
assert(state.reference.slotKey=="Finger0","default reference is not first physical slot")
assert(state.pinned[1].item_id==999001 and state.pinned[2].item_id==999001,"unknown equipped item lost identity")
assert(ui:GetComparisonReferenceLabel(state.reference):find("Finger 1",1,true),"reference exposes internal slot key")
assert(not ui:GetComparisonReferenceLabel(state.reference):find("Finger0",1,true),"reference exposes internal key")
ui.comparisonPinnedRows[2].referenceButton:Click(); H.settle()
assert(state.reference.slotKey=="Finger1","paired slot cannot become reference")
ui:CloseSlotComparison()
ui.currentOwned = {equippedSlots={Finger1={item_id=999002}}}
ui:OpenSlotComparison({slot="Ring"}); H.settle()
assert(ui.slotComparison.reference.slotKey=="Finger0" and not ui.slotComparison.reference.item_id,"empty first slot was silently replaced with second")
ui:CloseSlotComparison()
ui.currentOwned = {equippedSlots={MainHand={item_id=999003}},equippedTwoHand=true}
ui:OpenSlotComparison({slot="Off Hand"}); H.settle()
assert(ui.slotComparison.reference.occupancy=="blocked","two-handed occupancy lost")
assert(ui:GetComparisonReferenceLabel(ui.slotComparison.reference):find("two-handed",1,true),"blocked slot described as empty")
''')

    def test_reference_resize_and_paging_reuse_pool_and_keep_scroll(self):
        self.run_lua(r'''
local builds = 0
local original = BigBiSList.GetSlotComparisonRows
BigBiSList.GetSlotComparisonRows = function(self,...) builds=builds+1; return original(self,...) end
ui:OpenSlotComparison({slot="Ring"}); H.settle()
assert(builds==1,"initial comparison rebuilt its pool")
ui.comparisonScroll:SetVerticalScroll(math.min(100,ui.comparisonScroll:GetVerticalScrollRange())); H.settle()
local offset = ui.comparisonScroll:GetVerticalScroll()
local candidate = ui.slotComparison.rows[#ui.slotComparison.rows]
assert(candidate,"ring candidates missing")
ui:SetComparisonReference(candidate.item_id); H.settle()
assert(ui.slotComparison.reference==candidate.item_id,"candidate reference ignored")
near(ui.comparisonScroll:GetVerticalScroll(),math.min(offset,ui.comparisonScroll:GetVerticalScrollRange()),"reference scroll")
ui.frame:SetSize(900,660); H.settle()
ui:ChangeComparisonPhasePage(1); H.settle()
assert(builds==1,"presentation change rebuilt candidate pool")
''')

    def test_geometry_pagination_and_virtualization_in_both_densities(self):
        self.run_lua(r'''
ui:OpenSlotComparison({slot="Ring"}); H.settle()
for _, size in ipairs({{1020,560},{1160,660},{900,660},{700,660},{560,660}}) do
    UIParent:SetSize(size[1]<1020 and size[1] or 1920,1080)
    ui.frame:SetSize(size[1],size[2]); H.settle()
    for _, density in ipairs({"comfortable","compact"}) do
        BigBiSListDB.profile.window.density=density
        ui:RenderSlotComparison(); H.settle()
        local columns,state=ui.comparisonColumns,ui.slotComparison
        H.expectBounded(ui.comparisonFrame,ui.body,"comparison body")
        H.expectBounded(ui.comparisonScroll,ui.comparisonFrame,"comparison viewport")
        assert(columns.action.x+columns.action.width<=columns.width+.7,"final action column overflows")
        if size[1]>=1020 then assert(#columns.phases==6,"supported width hides phases") end
        for page=1,columns.pages do
            state.page=page; ui:LayoutSlotComparison(); H.settle()
            local target=false
            for _, column in ipairs(ui.comparisonColumns.phases) do if column.phase==state.phase then target=true end end
            assert(target,"phase pagination dropped selected tier")
        end
        local shown=0
        for _, row in ipairs(ui.comparisonActiveRows) do
            if row:IsShown() then
                shown=shown+1
                H.expectBounded(row,ui.comparisonChild,"comparison realized row")
                if row.comparisonData then
                    assert(row:GetHeight()==(density=="compact" and 40 or 56),"density did not reflow entries")
                    for _, cell in ipairs(row.phaseCells) do if cell:IsVisible() then H.expectBounded(cell,row,"phase cell") end end
                    H.expectBounded(row.star,row,"wishlist star")
                end
            end
        end
        assert(shown<=math.ceil(ui.comparisonScroll:GetHeight()/28)+2,"comparison realizes all candidate rows")
    end
end
''')

    def test_groups_have_explicit_evidence_and_stable_non_numeric_ties(self):
        self.run_lua(r'''
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
state.rows={{item_id=900003,name="Zulu"},{item_id=900002,name="Alpha"},{item_id=900001,name="Alpha"}}
BigBiSList.CompareRecommendationItems=function(_,candidate)
    return {relation="higher",phase="T4",historical=true,basis_key="guide-a:T4",explanation="Same guide table",evidence={{candidate={original_rating="BiS",source_url="https://example.invalid/guide",table_heading="Head rankings"},reference={original_rating="Alternative"}}}}
end
ui:RebuildComparisonEntries()
assert(state.entries[1].kind=="section" and state.entries[1].title:find("Tier 4",1,true),"basis phase is not visible")
assert(state.entries[2].data.item_id==900001 and state.entries[3].data.item_id==900002 and state.entries[4].data.item_id==900003,"equal-evidence rows lack stable name/id order")
BigBiSList.CompareRecommendationItems=function() return {relation="unranked",explanation="No shared table"} end
ui:RebuildComparisonEntries()
assert(state.entries[1].title:find("No shared rating",1,true),"unresolved rows claim a rank")
''')

    def test_supported_grades_sort_within_the_same_source_basis_before_names(self):
        self.run_lua(r'''
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
state.rows={{item_id=900001,name="Great Alpha"},{item_id=900002,name="Best Zebra"},{item_id=900003,name="Good Reference"},{item_id=900004,name="Great Alpha"}}
local grades={ [900001]=2,[900002]=1,[900003]=3,[900004]=2 }
BigBiSList.CompareRecommendationItems=function(_,candidate)
    return {relation=candidate==900003 and "same_rating" or "higher",phase="T4",historical=true,basis_key="shared-head-table:T4",
        evidence={{candidate={grade=grades[candidate],conditions={}},reference={grade=3,conditions={}}}}}
end
ui:RebuildComparisonEntries()
assert(state.entries[2].data.item_id==900002,"Best must precede Great even when its name sorts later")
assert(state.entries[3].data.item_id==900001 and state.entries[4].data.item_id==900004,"equal grades must retain stable name/item-id ordering")
assert(state.entries[5].data.item_id==900003,"Good must follow supported Best/Great ratings from the same table")
''')

    def test_context_navigation_exits_comparison_without_leaking_selection(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
ui:OpenSlotComparison({slot="Head"}); H.settle()
ui:SetTab("Wishlist"); H.settle()
assert(not ui:IsSlotComparisonOpen(),"workspace switch kept comparison active")
assert(ui:GetSelection().tab=="Wishlist" and not ui.comparisonFrame:IsVisible(),"workspace navigation blocked")
ui:OpenSlotComparison({slot="Head"}); H.settle()
ui:SetPhase(ui:GetSelection().phase=="T4" and "T5" or "T4"); H.settle()
assert(not ui:IsSlotComparisonOpen(),"target-tier change retained stale comparison context")
''')

    def test_hide_undo_updates_comparison_without_rebuilding_its_pool(self):
        self.run_lua(r'''
local builds=0
local original=BigBiSList.GetSlotComparisonRows
BigBiSList.GetSlotComparisonRows=function(self,...) builds=builds+1; return original(self,...) end
ui:OpenSlotComparison({slot="Ring"}); H.settle()
local data=ui.slotComparison.rows[1]; assert(data,"candidate fixture")
ui:SetComparisonReference(data.item_id)
ui:ShowComparisonDetails(data); H.settle()
ui:IgnoreItem(data.item_id); H.settle()
local state=ui.slotComparison
assert(not state.detailsOpen and ui.comparisonFrame:IsVisible(),"hiding current details did not return to comparison")
assert(type(state.reference)=="table" and state.reference.slotKey==state.contexts[1].slotKey,"hidden reference did not return to physical first")
for _,entry in ipairs(state.entries) do assert(not entry.data or entry.data.item_id~=data.item_id,"hidden candidate still displayed") end
assert(ui.undoAction,"hide must retain existing Undo")
ui:UndoLastAction(); H.settle()
local found=false
for _,entry in ipairs(state.entries) do if entry.data and entry.data.item_id==data.item_id then found=true end end
assert(found,"Undo did not restore candidate")
assert(builds==1,"Hide/Undo rebuilt source candidate pool")
''')

    def test_modifier_clicks_stars_reference_validation_and_recycled_controls(self):
        self.run_lua(r'''
ui:OpenSlotComparison({slot="Ring"}); H.settle()
local row
for _,frame in ipairs(ui.comparisonActiveRows) do if frame.comparisonData then row=frame; break end end
assert(row,"visible comparison item")
local id=row.comparisonData.item_id
H.modifiers.shift=true; row.iconButton:Click(); H.modifiers.shift=false
assert(H.chatLink=="item:"..id and not ui.slotComparison.detailsOpen,"Shift-click must only link")
H.modifiers.control=true; row.iconButton:Click(); H.modifiers.control=false
assert(H.previewLink=="item:"..id and not ui.slotComparison.detailsOpen,"Ctrl-click must only preview")
row.star:Click(); H.settle()
assert(BigBiSList:GetCharacterDB().wishlist[tostring(id)],"comparison star did not save membership")
local previous=ui.slotComparison.reference
assert(ui:SetComparisonReference(99999999)==false and ui.slotComparison.reference==previous,"foreign candidate accepted as reference")
local stale=ui.comparisonPinnedRows[2].referenceButton
ui:CloseSlotComparison(); ui:OpenSlotComparison({slot="Head"}); H.settle()
local current=ui.slotComparison.reference
stale:Click(); H.settle()
assert(ui.slotComparison.reference==current,"recycled paired-slot reference changed another slot")
ui:BindComparisonRow(row,{kind="section",title="No shared rating",height=28})
row.iconButton:Click(); row.star:Click(); H.settle()
assert(not ui.slotComparison.detailsOpen,"released item controls retain click bindings")
''')


if __name__ == "__main__":
    unittest.main()
