"""Owned comparison candidates remain separate from recommendation evidence."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tests.test_recommendation_comparison import use
from tools.generate_lua import SCHEMAS, compact_record
from tools.project import ADDON_DIR, lua_value


class OwnedComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body, *, uses=None, items=None):
        if not self.lua:
            self.skipTest("Lua 5.1 unavailable")
        uses = uses or []
        by_id = {
            row["item_id"]: {
                "id": row["item_id"], "name": f"Recommendation {row['item_id']}",
                "inventory_slot": row["slot"], "acquisition_phase": "PR",
                "sources": [{"type": "quest", "quest_id": 1000 + row["item_id"],
                             "entity_name": "Fixture quest", "zone": "Fixture zone"}],
            }
            for row in uses
        }
        by_id.update({item["id"]: item for item in items or []})
        data = {
            "format": 2, "schemas": SCHEMAS,
            "classes": [
                {"name": "Warrior", "specs": [{"name": "Fury"}]},
                {"name": "Druid", "specs": [{"name": "Feral dps"}, {"name": "Feral tank"}]},
            ],
            "items": [compact_record(by_id[item_id], "item") for item_id in sorted(by_id)],
            "uses": [compact_record(row, "use") for row in uses],
        }
        script = "BigBiSList={}\nBigBiSListData=" + lua_value(data) + r'''
dofile("DataIndex.lua")
local function equal(actual,expected,label)
    assert(actual==expected,(label or "value")..": "..tostring(actual).." ~= "..tostring(expected))
end
local function byId(rows,id)
    for _,row in ipairs(rows) do if row.item_id==id then return row end end
end
local function rowsFor(slot,owned,reference)
    return BigBiSList:GetSlotComparisonRows("Warrior","Fury","T6",slot,owned,reference)
end
''' + body
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=script,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_unranked_bag_and_bank_items_are_candidates_without_invented_ratings(self):
        self.run_lua(r'''
local owned={
    [901]="bag",["902"]="bank",bankScanned=false,
    equippedSlots={Head={item_id=999}},
    inventoryItems={
        [901]={item_id=901,item_link="item:901",name="Bag helm",equip_location="INVTYPE_HEAD",locations={bags=true}},
        [902]={item_id=902,item_link="item:902",name="Bank helm",inventory_slot="Head",locations={bank=true}},
    },
}
local rows=rowsFor("Head",owned)
for _,id in ipairs({901,902,999}) do
    local row=byId(rows,id); assert(row,"owned item missing: "..id)
    assert(not row.bestUse and not row.history.selected.matched,"ownership invented a recommendation")
    if id~=999 then equal(row.comparison.relation,"unranked","unranked ownership cannot prove an upgrade") end
    assert(row.comparison.relation~="higher","unranked ownership cannot prove an upgrade")
end
equal(byId(rows,901).owned_state,"bag")
equal(byId(rows,902).owned_state,"bank")
equal(byId(rows,901).name,"Bag helm","uncatalogued name comes from inventory metadata")
equal(byId(rows,901).item_link,"item:901","uncatalogued item keeps its hover link")
assert(byId(rows,1),"recommendations remain in the comparison pool")
equal(owned.bankScanned,false,"comparison must not claim bank freshness")
''', uses=[use(1, "T6", "Best", 1)])

    def test_slot_compatibility_handles_rings_necks_relics_and_weapon_hands(self):
        self.run_lua(r'''
local owned={inventoryItems={}}
local function add(id,location,slot)
    owned[id]="bag"
    owned.inventoryItems[id]={item_id=id,equip_location=location,inventory_slot=slot,locations={bags=true}}
end
add(901,"INVTYPE_FINGER"); add(902,"INVTYPE_NECK"); add(903,"INVTYPE_RELIC")
add(904,"INVTYPE_WEAPON"); add(905,"INVTYPE_WEAPONMAINHAND")
add(906,"INVTYPE_WEAPONOFFHAND"); add(907,"INVTYPE_2HWEAPON")
add(908,"INVTYPE_SHIELD"); add(909,nil,"Trinket")
local rings=rowsFor("Finger0",owned)
assert(byId(rings,901) and not byId(rings,902),"physical ring alias must use ring compatibility")
assert(byId(rowsFor("Neck",owned),902),"neck items cannot depend on enhancement slots")
assert(byId(rowsFor("Relic",owned),903),"relic ownership must retain its equipment slot")
assert(byId(rowsFor("Trinket1",owned),909),"physical trinket alias must accept a canonical slot")
local main=rowsFor("Main Hand",owned)
assert(byId(main,904) and byId(main,905) and byId(main,907),"main hand compatible weapons missing")
assert(not byId(main,906) and not byId(main,908),"off-hand-only items leaked into main hand")
local off=rowsFor("Off Hand",owned)
assert(byId(off,904) and byId(off,906) and byId(off,908),"off hand compatible items missing")
assert(not byId(off,905) and not byId(off,907),"main-hand-only weapons leaked into off hand")
''')

    def test_missing_slot_metadata_defers_item_until_known_without_guessing_from_name(self):
        self.run_lua(r'''
local owned={
    [901]="bag",[902]="bank",[903]="bag",
    inventoryItems={
        [901]={item_id=901,name="Mighty Helmet",locations={bags=true}},
        [902]={item_id=902,locations={bank=true}},
        [903]={item_id=903,locations={bags=true}},
    },
}
local cold=rowsFor("Head",owned)
assert(not byId(cold,901) and not byId(cold,902),"unknown slot metadata cannot be inferred from names or ownership")
assert(byId(cold,903),"canonical slot metadata should make a known owned item usable")
owned.inventoryItems[901].equip_location="INVTYPE_HEAD"
local loaded=rowsFor("Head",owned)
assert(byId(loaded,901),"late item metadata did not add the now-compatible item")
assert(not byId(loaded,902),"unresolved bank metadata gained an invented slot")
''', items=[{"id": 903, "name": "Catalogued helm", "inventory_slot": "Head"}])

    def test_duplicate_physical_slots_remain_pinned_while_item_candidates_are_unique(self):
        self.run_lua(r'''
local owned={
    [901]="equipped",
    equippedSlots={Finger0={item_id=901},Finger1={item_id=901}},
    inventoryItems={[901]={item_id=901,equip_location="INVTYPE_FINGER",count=3,locations={equipped=true,bags=true,bank=true}}},
}
local rows=rowsFor("Ring",owned)
equal(#rows.contexts,2,"paired equipment positions must stay distinct")
equal(rows.contexts[1].item_id,901); equal(rows.contexts[2].item_id,901)
assert(rows.contexts[1].slotKey~=rows.contexts[2].slotKey,"physical identities collapsed")
local count=0
for _,row in ipairs(rows) do if row.item_id==901 then count=count+1 end end
equal(count,1,"one candidate per item regardless of copy count or location count")
equal(rows.reference.slotKey,"Finger0","default reference retains first physical position")
equal(byId(rows,901).owned_state,"equipped","equipped state wins when other copies are stored")
''')

    def test_stale_unowned_reference_falls_back_but_valid_owned_reference_is_retained(self):
        self.run_lua(r'''
local owned={
    [901]="bag",equippedSlots={Head={item_id=999}},
    inventoryItems={[901]={item_id=901,equip_location="INVTYPE_HEAD",locations={bags=true}}},
}
local valid=rowsFor("Head",owned,901)
equal(valid.reference.item_id,901,"owned unranked item can be the reference")
assert(byId(valid,901).is_reference)
owned[901]=nil; owned.inventoryItems[901]=nil
for _,reference in ipairs({901,{item_id=901,occupancy="occupied"}}) do
    local stale=rowsFor("Head",owned,reference)
    assert(not byId(stale,901),"obsolete nonowned unranked reference was injected")
    equal(stale.reference.slotKey,"Head","stale reference must restore physical default")
    equal(stale.reference.item_id,999)
end
local recommended=rowsFor("Head",owned,1)
equal(recommended.reference.item_id,1,"still-recommended nonowned reference remains valid")
assert(byId(recommended,1).is_reference)
''', uses=[use(1, "T6")])

    def test_ownership_refresh_removes_unranked_candidates_but_preserves_recommendations(self):
        self.run_lua(r'''
local owned={
    [901]="bag",[1]="bank",
    inventoryItems={
        [901]={item_id=901,equip_location="INVTYPE_HEAD",locations={bags=true}},
        [1]={item_id=1,equip_location="INVTYPE_HEAD",locations={bank=true}},
    },
}
assert(byId(rowsFor("Head",owned),901),"initial owned candidate missing")
owned[901]=nil; owned.inventoryItems[901]=nil
owned[1]=nil; owned.inventoryItems[1]=nil
local refreshed=rowsFor("Head",owned)
assert(not byId(refreshed,901),"lost ownership left an unrelated unranked candidate")
assert(byId(refreshed,1),"lost ownership removed a legitimate recommendation")
assert(not byId(refreshed,1).owned_state,"lost ownership remained visible on recommendation")
''', uses=[use(1, "T6")])

    def test_owned_candidates_are_not_hidden_by_recommendation_phase_availability(self):
        self.run_lua(r'''
local owned={
    [901]="bank",inventoryItems={[901]={item_id=901,equip_location="INVTYPE_HEAD",locations={bank=true}}},
}
local rows=rowsFor("Head",owned)
local row=byId(rows,901); assert(row,"recorded ownership must remain comparable even outside source availability")
equal(row.owned_state,"bank")
assert(not row.history.selected.matched,"future availability invented a selected-phase grade")
equal(row.comparison.relation,"unranked")
''', uses=[use(901, "SWP", "Best", 1)], items=[{
            "id": 901, "name": "Future helm", "inventory_slot": "Head", "acquisition_phase": "SWP",
            "sources": [{"type": "drop", "entity_id": 1001, "entity_name": "Future boss",
                         "zone": "Future raid", "available_from_phase": "SWP"}],
        }])

    def test_feral_roles_use_their_own_guide_evidence_and_keep_shared_owned_items(self):
        cat = use(1, "T6", "Best", 1)
        cat.update({"class": "Druid", "spec": "Feral dps"})
        bear = use(2, "T6", "Best", 1)
        bear.update({"class": "Druid", "spec": "Feral tank"})
        self.run_lua(r'''
local owned={
    [901]="bag",inventoryItems={[901]={item_id=901,equip_location="INVTYPE_HEAD",locations={bags=true}}},
}
local cat=BigBiSList:GetSlotComparisonRows("Druid","Feral dps","T6","Head",owned)
local bear=BigBiSList:GetSlotComparisonRows("Druid","Feral tank","T6","Head",owned)
assert(byId(cat,1) and not byId(cat,2),"Cat comparison used Bear recommendations")
assert(byId(bear,2) and not byId(bear,1),"Bear comparison used Cat recommendations")
assert(byId(cat,901) and byId(bear,901),"local role changes must retain compatible owned equipment")
equal(byId(cat,901).spec,"Feral dps"); equal(byId(bear,901).spec,"Feral tank")
assert(not byId(cat,901).history.selected.matched and not byId(bear,901).history.selected.matched)
equal(byId(cat,1).history.selected.label,"Best")
equal(byId(bear,2).history.selected.label,"Best")
''', uses=[cat, bear])

    def test_explicit_other_spec_reference_requires_available_same_class_slot_evidence(self):
        def druid(item_id, phase, *, spec="Feral dps", slot="Head"):
            row = use(item_id, phase, "Best", 1, slot=slot)
            row.update({"class": "Druid", "spec": spec})
            return row

        self.run_lua(r'''
local owned={equippedSlots={Head={item_id=999}}}
local ordinary=BigBiSList:GetSlotComparisonRows("Druid","Feral tank","T6","Head",owned)
assert(not byId(ordinary,1) and not byId(ordinary,3) and not byId(ordinary,4),"other-spec references must not enter the normal candidate pool")
for _,reference in ipairs({1,{item_id=3,occupancy="occupied"},4}) do
    local id=type(reference)=="table" and reference.item_id or reference
    local rows=BigBiSList:GetSlotComparisonRows("Druid","Feral tank","T6","Head",owned,reference)
    equal(rows.reference.item_id,id,"supported previous-spec reference was discarded")
    local row=byId(rows,id); assert(row and row.is_reference,"preserved reference is inaccessible")
    assert(not row.bestUse and not row.history.selected.matched,"other-spec evidence became a Bear recommendation")
    equal(#(row.comparison.evidence or {}),0,"future or other-spec guide evidence became an immediate comparison proof")
end
for _,id in ipairs({5,6,7,901}) do
    local rows=BigBiSList:GetSlotComparisonRows("Druid","Feral tank","T6","Head",owned,id)
    assert(not byId(rows,id),"unsupported reference was injected: "..id)
    equal(rows.reference.slotKey,"Head","invalid reference must restore physical position")
    equal(rows.reference.item_id,999)
end
''', uses=[druid(1, "T6"), druid(2, "T6", spec="Feral tank"), druid(3, "T5"),
           druid(4, "SWP"), use(5, "T6"), druid(6, "T6", slot="Neck"), druid(7, "T5")],
           items=[{"id": 7, "name": "Unavailable previous-spec helm", "inventory_slot": "Head",
                   "acquisition_phase": "SWP", "sources": [{"type": "drop", "entity_id": 1001,
                   "entity_name": "Future boss", "zone": "Future raid", "available_from_phase": "SWP"}]}])


class OwnedComparisonUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body):
        if not self.lua:
            self.skipTest("Lua 5.1 unavailable")
        script = r'''
local H=dofile("tests/lua_ui_harness.lua")
local ui=H.load()
ui:Open(); H.settle()
local function equal(a,b,label) assert(a==b,(label or "value")..": "..tostring(a).." ~= "..tostring(b)) end
local function ids(state)
    local result={}
    for _,entry in ipairs(state.entries) do if entry.data and entry.data.item_id then result[#result+1]=entry.data.item_id end end
    return table.concat(result,",")
end
local function position(state,id)
    for i,entry in ipairs(state.entries) do if entry.data and entry.data.item_id==id then return i end end
end
local function menu(dropdown)
    local items={}
    local previous=UIDropDownMenu_AddButton
    UIDropDownMenu_AddButton=function(info) items[#items+1]=info end
    dropdown.initialize(dropdown,1)
    UIDropDownMenu_AddButton=previous
    return items
end
local function rated(id,name,phase,grade,owned,source)
    local phases,cells={},{}
    for _,p in ipairs(BigBiSList:GetPhaseOrder()) do
        local cell={phase=p,matched=false,status="no_guide",evidence={},rating_evidence={}}
        if p==phase then
            local evidence={table_id="fixture:"..p,guide_phase=p,rating_phase=p,grade=grade,conditions={},
                original_rating=grade==1 and "Best" or "Good",source_url="https://example.invalid/"..p,table_heading="Head"}
            cell.matched=true; cell.status="rated"; cell.label=evidence.original_rating
            cell.evidence={evidence}; cell.rating_evidence={evidence}; cell.direct_evidence={evidence}
        end
        phases[p]=cell; cells[#cells+1]=cell
    end
    local history={selected=phases.T6,phases=phases,phase_cells=cells,latest_earlier=phase=="T5" and phases.T5 or nil,
        future_summary={has_future=phase=="SWP",phases=phase=="SWP" and {"SWP"} or {}}}
    return {item_id=id,name=name,slot="Head",history=history,recommendation_history=history,owned_state=owned,
        acquisition_display={source_label=source,location_label=source,source_summary=source}}
end
''' + body + r'''
assert(#H.errors==0,table.concat(H.errors,"\n"))
'''
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=script,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_compare_as_feral_roles_stays_local_and_details_use_the_same_context(self):
        self.run_lua(r'''
ui:SetClass("Druid"); ui:SetSpec("Feral dps"); ui:SetPhase("T6"); H.settle()
local selection,filters=ui:GetSelection(),ui:GetFilters()
local globalClass,globalSpec,globalPhase=selection.class,selection.spec,selection.phase
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
local labels={}
for _,item in ipairs(menu(ui.comparisonSpec)) do labels[item.value]=item.text end
assert(labels["Feral dps"] and labels["Feral dps"]:find("Cat DPS",1,true),"Cat role label is unclear")
assert(labels["Feral tank"] and labels["Feral tank"]:find("Bear Tank",1,true),"Bear role label is unclear")
ui:SetComparisonSpec("Feral tank"); H.settle()
equal(state.spec,"Feral tank","comparison role did not switch")
equal(ui:GetSelection().class,globalClass); equal(ui:GetSelection().spec,globalSpec); equal(ui:GetSelection().phase,globalPhase)
equal(ui:GetFilters(),filters,"local role replaced origin filters")
equal(ui:GetItemContext().spec,"Feral tank","item context ignored local comparison role")
assert(#state.rows>0,"Bear comparison has no recommendation candidates")
local candidate=state.rows[1]
ui:ShowComparisonDetails(candidate); H.settle()
equal(ui:GetItemContext().spec,"Feral tank","Details reverted to the origin spec")
ui:BackToSlotComparison(); ui:SetComparisonSpec("Feral dps"); H.settle()
equal(ui:GetItemContext().spec,"Feral dps")
ui:CloseSlotComparison(); H.settle()
equal(ui:GetItemContext().spec,globalSpec,"comparison role escaped into origin context")
''')

    def test_owned_gear_scope_filters_visible_rows_without_rebuilding_candidates(self):
        self.run_lua(r'''
ui.currentOwned={
    [999001]="bag",[999002]="bank",bankScanned=false,
    inventoryItems={
        [999001]={item_id=999001,name="Bag helm",equip_location="INVTYPE_HEAD",locations={bags=true}},
        [999002]={item_id=999002,name="Bank helm",equip_location="INVTYPE_HEAD",locations={bank=true}},
    },
}
local builds=0
local original=BigBiSList.GetSlotComparisonRows
BigBiSList.GetSlotComparisonRows=function(self,...) builds=builds+1; return original(self,...) end
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
equal(state.ownership,"all"); equal(state.sort,"recommendation","recommendations must be the default sort")
local all=ids(state)
assert(position(state,999001) and position(state,999002),"owned candidates missing before filtering")
local foundLabel=false
for _,item in ipairs(menu(ui.comparisonOwnership)) do if item.value=="owned" and item.text=="Owned gear" then foundLabel=true end end
assert(foundLabel,"owned-only scope needs the agreed player-facing label")
ui:SetComparisonOwnership("owned"); H.settle()
assert(position(state,999001) and position(state,999002),"owned scope dropped bags or bank")
for _,entry in ipairs(state.entries) do
    if entry.data then assert(entry.data.owned_state,"owned scope retained an unowned recommendation") end
end
equal(builds,1,"ownership scope rebuilt recommendation candidates")
ui:SetComparisonOwnership("all"); H.settle()
equal(ids(state),all,"returning to All changed recommendation order")
equal(builds,1)
''')

    def test_tooltip_context_is_local_only_for_comparison_and_its_details(self):
        self.run_lua(r'''
ui:SetClass("Druid"); ui:SetSpec("Feral dps"); ui:SetPhase("T6"); H.settle()
ui:OpenSlotComparison({slot="Head"}); H.settle()
ui:SetComparisonSpec("Feral tank"); H.settle()
local state=ui.slotComparison
equal(state.spec,"Feral tank")
local recorded
BigBiSList.GetTooltipMatches=function(_,id,class,spec,first,filters,priority)
    recorded={class=class,spec=spec,phase=priority.selectedPhase,prioritySpec=priority.playerSpec}
    return {{class=class,spec=spec,phase="T6",slot="Head",rank_label="Good"}}
end
BigBiSList.GetGroupedTooltipMatches=function(_,id,class,spec)
    return {{class=class,spec=spec,phase="T6",slot="Head",rank_label="Good"}}
end
local function hover(tooltip,owner,expected,label)
    recorded=nil
    tooltip:SetOwner(owner,"ANCHOR_RIGHT"); tooltip:SetHyperlink("item:999001")
    assert(recorded,label.." did not request tooltip annotations")
    equal(recorded.class,"Druid",label.." class")
    equal(recorded.spec,expected,label.." spec")
    equal(recorded.phase,"T6",label.." phase")
    assert(table.concat(tooltip.lines,"\n"):find("Druid "..expected,1,true),label.." rendered another role")
end
local comparisonOwner=CreateFrame("Button",nil,CreateFrame("Frame",nil,ui.comparisonFrame))
hover(GameTooltip,comparisonOwner,"Feral tank","comparison descendant")
equal(recorded.prioritySpec,"Feral tank","local role should be the tooltip priority")
ui:ShowComparisonDetails(state.rows[1]); H.settle()
local detailOwner=CreateFrame("Button",nil,CreateFrame("Frame",nil,ui.details))
hover(GameTooltip,detailOwner,"Feral tank","comparison Details descendant")
local bagOwner=CreateFrame("Button",nil,UIParent)
hover(GameTooltip,bagOwner,"Feral dps","native bag while comparison Details is open")
hover(ItemRefTooltip,comparisonOwner,"Feral dps","native item reference")
ui:CloseSlotComparison(); H.settle()
hover(GameTooltip,comparisonOwner,"Feral dps","closed comparison")
''')

    def test_owned_snapshot_refresh_updates_selected_details_and_removes_lost_unranked_selection(self):
        self.run_lua(r'''
local function snapshot(location,name)
    return {[999001]=location,inventoryItems={[999001]={item_id=999001,name=name,item_link="item:999001",
        equip_location="INVTYPE_HEAD",locations={[location=="bag" and "bags" or "bank"]=true}}}}
end
ui.currentOwned=snapshot("bag","Original owned helm")
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
local candidate
for _,row in ipairs(state.rows) do if row.item_id==999001 then candidate=row; break end end
assert(candidate,"owned selection fixture missing")
ui:SetComparisonReference(999001); ui:ShowComparisonDetails(candidate); H.settle()
ui.currentOwned=snapshot("bank","Updated owned helm")
ui:RenderSlotComparison(true); H.settle()
assert(state.detailsOpen,"ownership update unexpectedly closed a still-owned selected item")
equal(state.selectedItemId,999001)
assert(ui.selectedItemData~=candidate,"Details retained obsolete row data after ownership refresh")
equal(ui.selectedItemData.owned_state,"bank","Details retained old bag ownership")
equal(ui.selectedItemData.name,"Updated owned helm","Details retained obsolete inventory metadata")
ui.currentOwned={}
ui:RenderSlotComparison(true); H.settle()
assert(not state.detailsOpen and ui.comparisonFrame:IsVisible(),"lost unranked selection did not return to comparison")
assert(not state.selectedItemId and not ui.selectedItemId,"lost unranked item retained active selection")
assert(not position(state,999001),"lost owned item remained a candidate")
equal(type(state.reference),"table"); equal(state.reference.slotKey,"Head","lost reference did not restore physical default")
''')

    def test_default_recommendation_order_uses_history_and_is_stable_when_reference_changes(self):
        self.run_lua(r'''
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
state.rows={rated(900001,"Alpha Good","T6",3),rated(900002,"Zulu Best","T6",1),
    rated(900003,"Earlier","T5",1),rated(900004,"Future","SWP",1),rated(900005,"Unknown")}
BigBiSList.CompareRecommendationItems=function() return {relation="unranked",explanation="No shared table",evidence={}} end
ui:RebuildComparisonEntries()
equal(ids(state),"900002,900001,900003,900004,900005","Recommendations must prioritize supported current, earlier, future, then unrecorded evidence")
local order=ids(state)
ui:SetComparisonReference(900001); H.settle()
equal(ids(state),order,"changing the reference reordered Recommendations")
ui:SetComparisonReference(900005); H.settle()
equal(ids(state),order,"an unranked reference changed recommendation order")
''')

    def test_current_conditional_recommendations_precede_earlier_and_nearest_future_tiers(self):
        self.run_lua(r'''
ui:SetPhase("T6"); H.settle()
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
local conditional=rated(900002,"Current with set","T6",1)
conditional.history.selected.status="conditional"
conditional.history.selected.label="Best with set"
conditional.history.selected.rating_evidence[1].conditions={"with set"}
local za=rated(900004,"Next tier","ZA",1)
za.history.future_summary={has_future=true,phases={"ZA"}}
state.rows={rated(900006,"Unrecorded"),rated(900005,"Later future","SWP",1),
    rated(900003,"Earlier","T5",1),conditional,za,rated(900001,"Current rated","T6",2)}
BigBiSList.CompareRecommendationItems=function() return {relation="unranked",evidence={}} end
ui:RebuildComparisonEntries()
equal(ids(state),"900001,900002,900003,900004,900005,900006",
    "current setup-dependent evidence must stay current; upcoming tiers should precede more distant ones")
''')

    def test_comparison_scope_discloses_all_sources_without_changing_origin_filters(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
local filters=ui:GetFilters()
filters.sourceType="dungeon_drop"; filters.sourceTypes={dungeon_drop=true}
filters.zone="Fixture dungeon"; filters.zones={["Fixture dungeon"]=true}
ui:OpenSlotComparison({slot="Head"}); H.settle()
assert(ui.comparisonScope:GetText():find("All sources",1,true),"comparison does not disclose that source filters are broadened")
ui:SetComparisonOwnership("owned"); H.settle()
assert(ui.comparisonScope:GetText():find("All sources",1,true),"Owned gear scope obscured acquisition scope")
equal(ui:GetFilters(),filters)
equal(filters.sourceType,"dungeon_drop"); equal(filters.zone,"Fixture dungeon")
assert(filters.sourceTypes.dungeon_drop and filters.zones["Fixture dungeon"],"comparison mutated effective origin source filters")
ui:CloseSlotComparison(); H.settle()
equal(ui:GetFilters(),filters); equal(filters.sourceType,"dungeon_drop"); equal(filters.zone,"Fixture dungeon")
''')

    def test_local_spec_change_keeps_phase_page_and_selected_nonowned_previous_spec_reference(self):
        self.run_lua(r'''
ui:SetClass("Druid"); ui:SetSpec("Feral dps"); ui:SetPhase("T6"); H.settle()
ui.currentOwned={}
ui:OpenSlotComparison({slot="Neck"}); H.settle()
local state=ui.slotComparison
local bearIds={}
for _,row in ipairs(BigBiSList:GetSlotComparisonRows("Druid","Feral tank","T6","Neck",{})) do bearIds[row.item_id]=true end
local reference
for _,row in ipairs(state.rows) do if not bearIds[row.item_id] then reference=row.item_id; break end end
assert(reference,"committed Cat neck recommendations need a non-Bear reference fixture")
ui:SetComparisonReference(reference); H.settle()
UIParent:SetSize(560,1080); ui.frame:SetSize(560,660); H.settle()
assert(ui.comparisonColumns.pages>1,"narrow comparison must exercise phase pagination")
ui:ChangeComparisonPhasePage(1); H.settle()
local page=state.page; assert(page>1,"phase page fixture did not advance")
ui:SetComparisonSpec("Feral tank"); H.settle()
equal(state.page,page,"local spec change reset phase pagination")
local selected=type(state.reference)=="table" and state.reference.item_id or state.reference
equal(selected,reference,"changing role discarded explicitly chosen previous-role equipment")
local row
for _,candidate in ipairs(state.rows) do if candidate.item_id==reference then row=candidate; break end end
assert(row and row.is_reference,"preserved nonowned reference cannot be inspected")
assert(not row.owned_state and not row.history.selected.matched,"retained reference invented Bear ownership or rating")
equal(ui:GetSelection().spec,"Feral dps","local comparison role changed character browsing")
''')

    def test_item_source_and_owned_headings_sort_the_entire_visible_list(self):
        self.run_lua(r'''
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
state.rows={rated(900001,"Charlie","T6",1,"bank","Alpha"),rated(900002,"Alpha","T5",1,"bag","Zulu"),rated(900003,"Bravo",nil,nil,nil,"Middle")}
BigBiSList.CompareRecommendationItems=function() return {relation="unranked",evidence={}} end
ui:RebuildComparisonEntries(); ui:LayoutSlotComparison(); H.settle()
ui.comparisonHeader.buttons.item:Click(); H.settle()
equal(state.sort,"item"); equal(ids(state),"900002,900003,900001","Item sort must span recommendation groups")
ui.comparisonHeader.buttons.item:Click(); H.settle()
equal(ids(state),"900001,900003,900002","Item sort direction did not reverse")
ui.comparisonHeader.buttons.source:Click(); H.settle()
equal(state.sort,"source"); equal(ids(state),"900001,900003,900002","Source sort must use acquisition text across the list")
ui.comparisonHeader.buttons.source:Click(); H.settle()
equal(ids(state),"900002,900003,900001","Source direction did not reverse")
ui.comparisonHeader.buttons.owned:Click(); H.settle()
equal(state.sort,"owned")
local first=ids(state)
ui.comparisonHeader.buttons.owned:Click(); H.settle()
assert(ids(state)~=first,"Owned heading direction had no effect")
''')

    def test_sort_and_ownership_reset_scroll_while_reference_changes_keep_position_and_sort(self):
        self.run_lua(r'''
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
state.rows={}
for i=1,80 do state.rows[i]=rated(900000+i,string.format("Candidate %03d",i),"T6",2,i<=20 and "bag" or nil) end
BigBiSList.CompareRecommendationItems=function() return {relation="unranked",evidence={}} end
ui:RebuildComparisonEntries(); ui:LayoutSlotComparison(); H.settle()
ui:SetComparisonReference(900055)
ui:ShowComparisonDetails(state.rows[2]); H.settle()
ui:BackToSlotComparison(); H.settle()
equal(state.selectedItemId,900002)
assert(ui.comparisonScroll:GetVerticalScrollRange()>200,"fixture list must actually scroll")
ui.comparisonScroll:SetVerticalScroll(180); H.settle()
ui:SetComparisonSort("item"); H.settle()
equal(ui.comparisonScroll:GetVerticalScroll(),0,"changing sort must show the start of the new order")
equal(state.reference,900055); equal(state.selectedItemId,900002); equal(ui.selectedItemId,900002)
ui.comparisonScroll:SetVerticalScroll(160); H.settle()
ui:SetComparisonOwnership("owned"); H.settle()
equal(ui.comparisonScroll:GetVerticalScroll(),0,"changing ownership scope must show its first result")
equal(state.reference,900055,"ownership scope discarded a selected comparison reference")
equal(state.selectedItemId,900002); equal(ui.selectedItemId,900002)
ui.comparisonScroll:SetVerticalScroll(120); H.settle()
local offset,sort,direction=ui.comparisonScroll:GetVerticalScroll(),state.sort,state.sortDirection
ui:SetComparisonReference(900006); H.settle()
equal(ui.comparisonScroll:GetVerticalScroll(),offset,"reference-only comparison lost list position")
equal(state.sort,sort); equal(state.sortDirection,direction); equal(state.selectedItemId,900002)
ui:SetComparisonSort("item"); H.settle()
equal(ui.comparisonScroll:GetVerticalScroll(),0,"reversing sort direction must reset list position")
equal(state.reference,900006); equal(state.selectedItemId,900002)
''')

    def test_phase_and_comparison_sort_reverse_supported_grades_with_unknowns_last(self):
        self.run_lua(r'''
ui:SetPhase("T6"); H.settle()
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
state.rows={rated(900001,"Alpha Good","T6",3),rated(900002,"Zulu Best","T6",1),rated(900003,"Unknown")}
BigBiSList.CompareRecommendationItems=function(_,id)
    if id==900003 then return {relation="unranked",evidence={}} end
    return {relation="higher",phase="T6",basis_key="fixture:T6",evidence={{
        candidate={grade=id==900002 and 1 or 3,table_id="fixture:T6",conditions={}},
        reference={grade=4,table_id="fixture:T6",conditions={}},
    }}}
end
ui:RebuildComparisonEntries(); ui:LayoutSlotComparison(); H.settle()
ui.comparisonHeader.buttons["phase:T6"]:Click(); H.settle()
equal(state.sort,"phase:T6"); equal(ids(state),"900002,900001,900003")
ui.comparisonHeader.buttons["phase:T6"]:Click(); H.settle()
equal(ids(state),"900001,900002,900003","phase sort should reverse supported grades while unresolved remains last")
ui.comparisonHeader.buttons.comparison:Click(); H.settle()
equal(state.sort,"comparison"); equal(ids(state),"900002,900001,900003")
ui.comparisonHeader.buttons.comparison:Click(); H.settle()
equal(ids(state),"900001,900002,900003","comparison direction did not reverse supported evidence")
''')

    def test_comparison_toolbar_controls_stay_disjoint_and_phase_sort_survives_paging(self):
        self.run_lua(r'''
ui:SetClass("Druid"); ui:SetSpec("Feral dps"); ui:SetPhase("T6"); H.settle()
ui:OpenSlotComparison({slot="Head"}); H.settle()
local state=ui.slotComparison
ui:SetComparisonSort("phase:PR"); H.settle()
for _,size in ipairs({{1020,560},{1160,660},{900,660}}) do
    UIParent:SetSize(size[1]<1020 and size[1] or 1920,1080)
    ui.frame:SetSize(size[1],size[2]); H.settle()
    for _,density in ipairs({"comfortable","compact"}) do
        BigBiSListDB.profile.window.density=density
        ui:RenderSlotComparison(); H.settle()
        local controls={ui.comparisonReference,ui.comparisonSpec,ui.comparisonOwnership,ui.comparisonSort}
        assert(#controls==4,"comparison toolbar is incomplete")
        for i,a in ipairs(controls) do
            assert(a:IsVisible(),"comparison control is inaccessible")
            H.expectBounded(a.clickCover or a,ui.comparisonFrame,"comparison toolbar control")
            assert(a:GetBottom()>=ui.comparisonHeader:GetTop()-.7,"control overlaps column headings")
            for j,b in ipairs(controls) do
                if j>i then
                    local ax,ay,aw,ah=H.rect(a.clickCover or a)
                    local bx,by,bw,bh=H.rect(b.clickCover or b)
                    assert(ax+aw<=bx+.7 or bx+bw<=ax+.7 or ay+ah<=by+.7 or by+bh<=ay+.7,"comparison controls overlap")
                end
            end
        end
    end
end
UIParent:SetSize(560,1080); ui.frame:SetSize(560,660); H.settle()
state.page=ui.comparisonColumns.pages; ui:LayoutSlotComparison(); H.settle()
equal(state.sort,"phase:PR","pagination discarded selected phase sort")
local checked=false
for _,item in ipairs(menu(ui.comparisonSort)) do if item.value=="phase:PR" and item.checked then checked=true end end
assert(checked,"paged-out phase sort is no longer visible as selected in Sort")
''')


if __name__ == "__main__":
    unittest.main()
