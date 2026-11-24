"""Source-table evidence, historical recommendations, and physical equipment."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.generate_lua import SCHEMAS, compact_record
from tools.project import ADDON_DIR, lua_value


def use(item_id, phase, label="Good", grade=3, *, slot="Head", table_id=None,
        rating_phase=None, conditions=None, rank=1):
    return {
        "class": "Warrior", "spec": "Fury", "phase": phase, "slot": slot,
        "item_id": item_id, "rank_label": label, "rank_group": "bis" if "Best" in label else "ranked", "rank": rank,
        "source_url": f"https://example.invalid/{phase}",
        "guide_evidence": [{"table_id": table_id or f"fixture:{phase}:{slot}", "guide_phase": phase,
                            "rating_phase": rating_phase or phase, "original_rating": label, "grade": grade,
                            "conditions": conditions or [], "source_url": f"https://example.invalid/{phase}"}],
    }


class RecommendationComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, uses, body):
        if not self.lua:
            self.skipTest("Lua 5.1 is unavailable")
        items = [{"id": item_id, "name": f"Fixture {item_id}", "acquisition_phase": "PR",
                  "inventory_slot": "Head", "sources": [{"type": "quest", "quest_id": 1000+item_id,
                                                           "entity_name": "Fixture quest", "zone": "Fixture zone"}]}
                 for item_id in sorted({row["item_id"] for row in uses})]
        data = {"format": 2, "schemas": SCHEMAS, "classes": [{"name": "Warrior", "specs": [{"name": "Fury"}]}],
                "items": [compact_record(item, "item") for item in items],
                "uses": [compact_record(row, "use") for row in uses]}
        script = "BigBiSList={}\nBigBiSListData=" + lua_value(data) + r'''
dofile("DataIndex.lua")
local function equal(actual, expected, label)
    assert(actual == expected, (label or "value") .. ": " .. tostring(actual) .. " ~= " .. tostring(expected))
end
local function compare(a,b,phase,slot) return BigBiSList:CompareRecommendationItems(a,b,"Warrior","Fury",phase or "T6",slot or "Head") end
local function history(id,phase,slot) return BigBiSList:GetRecommendationHistory(id,"Warrior","Fury",phase or "T6",slot or "Head") end
local function planner(phase,owned,mode,earlier)
    return BigBiSList:GetPlannerRows("Warrior","Fury",phase,{ownedItems=owned or {},upgradeMode=mode or "candidates",includeEarlier=earlier})
end
local function byId(rows,id) for _,row in ipairs(rows) do if row.item_id==id then return row end end end
''' + body
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=script, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_only_shared_explicit_ratings_order_items_and_numeric_positions_do_not(self):
        self.run_lua([use(1,"T6","Great",2,rank=99), use(2,"T6","Good",3,rank=1),
                      use(3,"T6","Good",3,rank=999), use(4,"T6","Best",1,table_id="other"),
                      use(5,"T6","Best with set",None,conditions=["with set"])], r'''
equal(compare(1,2).relation,"higher","explicit grades win over row order")
equal(compare(2,1).relation,"lower","reverse comparison")
equal(compare(2,3).relation,"same_rating","same rating is not numeric position")
assert(compare(2,3).explanation:find("does not mean equal performance",1,true))
equal(compare(4,2).relation,"unranked","different tables cannot be ordered")
equal(compare(5,2).relation,"conditional","conditions need setup context")
equal(compare(1,1).relation,"same_rating","same item cannot be higher")
assert(compare(1,2).basis_key and #compare(1,2).evidence==1)
''')

    def test_selected_shared_phase_wins_then_latest_earlier_and_never_future(self):
        self.run_lua([use(1,"T4","Best",1), use(2,"T4","Good",3),
                      use(1,"T5","Good",3), use(2,"T5","Great",2),
                      use(3,"SWP","Best",1), use(4,"SWP","Good",3)], r'''
local current=compare(1,2,"T5")
equal(current.relation,"lower"); equal(current.phase,"T5"); assert(not current.historical)
local earlier=compare(1,2,"T6")
equal(earlier.relation,"lower"); equal(earlier.phase,"T5"); assert(earlier.historical)
assert(earlier.explanation:find("Historical Tier 5",1,true))
equal(compare(3,4,"T6").relation,"unranked","future cannot prove current upgrade")
''')

    def test_phase_qualified_rating_stays_historical_and_does_not_score_current_bis(self):
        self.run_lua([use(1,"T6","P2 Best",None,rating_phase="T5",conditions=["P2 Best"])], r'''
local h=history(1)
assert(not h.selected.matched)
equal(h.latest_earlier.phase,"T5")
equal(h.phases.T5.label,"P2 Best")
local row=byId(planner("T6",{},"all",true),1)
assert(row and row.historical_only)
equal(row.priority,0,"historical label cannot score as current BiS")
assert(not row.hasCurrent and not row.hasCurrentBis)
equal(#planner("T6",{},"all",false),0,"earlier toggle controls historical-only row")
''')

    def test_bis_earlier_rows_follow_current_variants_without_duplicate_targets(self):
        current_variant=use(1,"T6","Best with set",None,conditions=["with set"])
        current_variant["context"]="set"
        self.run_lua([use(1,"T6","Best",1),current_variant,use(1,"T5"),use(2,"T5"),use(3,"SWP")],r'''
local closed=BigBiSList:GetPhaseRows("Warrior","Fury","T6",{})
equal(#closed[1].items,2,"current variants retained")
local open=BigBiSList:GetPhaseRows("Warrior","Fury","T6",{includeEarlier=true})
equal(#open[1].items,3,"one additional earlier target")
equal(open[1].items[3].item_id,2)
assert(open[1].items[3].historical_only)
equal(open[1].items[3].recommendation_phase,"T5")
equal(open[1].items[1].item_id,1); equal(open[1].items[2].item_id,1)
''')

    def test_equipment_contexts_preserve_unknown_items_duplicate_pairs_and_blocked_offhand(self):
        self.run_lua([use(1,"T6",slot="Ring")],r'''
local owned={ [999]="equipped",[1]="equipped",equippedSlots={Head={item_id=999},Finger0={item_id=1},Finger1={item_id=1},MainHand={item_id=999}},equippedTwoHand=true }
local contexts=BigBiSList:GetEquipmentComparisonContexts("Warrior","Fury","T6",owned)
equal(#contexts,17,"all equipment positions")
equal(contexts[1].occupancy,"occupied"); equal(contexts[1].item_id,999); equal(contexts[1].use,nil)
local rings=BigBiSList:GetEquipmentComparisonContexts("Warrior","Fury","T6",owned,"Ring")
equal(#rings,2); equal(rings[1].item_id,1); equal(rings[2].item_id,1)
assert(rings[1].slotKey~=rings[2].slotKey)
local off=BigBiSList:GetEquipmentComparisonContexts("Warrior","Fury","T6",owned,"Off Hand")[1]
equal(off.occupancy,"blocked"); equal(off.blocked_by,"MainHand")
''')

    def test_candidates_keep_unresolved_occupancy_and_strict_mode_requires_supported_higher(self):
        self.run_lua([use(1,"T6","Great",2),use(2,"T6","Good",3),use(3,"T6","Best",1),use(2,"SWP")],r'''
local unknown={ [999]="equipped",equippedSlots={Head={item_id=999}} }
local row=byId(planner("T6",unknown),1)
assert(row and row.upgrade_candidate and not row.upgrade_compared_empty)
equal(row.upgrade_compared_item_id,999); equal(row.comparison.relation,"unranked")
equal(#planner("T6",unknown,"higher_rated"),0)
local good={ [2]="equipped",equippedSlots={Head={item_id=2}} }
assert(byId(planner("T6",good,"higher_rated"),1))
local best={ [3]="equipped",equippedSlots={Head={item_id=3}} }
assert(not byId(planner("T6",best),1),"known current lower item is not a candidate")
assert(byId(planner("T6",best),2),"later recommendation remains a target despite lower current rating")
assert(byId(planner("T6",best,"all"),1),"All retains lateral and lower recommendations")
assert(not byId(planner("T6",good),2),"equipped item does not infer a second-copy upgrade")
''')

    def test_bag_and_bank_notes_are_supported_pairwise_alternatives(self):
        self.run_lua([use(1,"T6","Best",1),use(2,"T6","Good",3),use(3,"T6","Great",2)],r'''
local owned={ [999]="equipped",["1"]="bag",[3]="bank",equippedSlots={Head={item_id=999}},bankScanned=false }
local row=byId(planner("T6",owned),2)
equal(#row.owned_alternatives,2)
equal(row.owned_alternatives[1].item_id,1); equal(row.owned_alternatives[1].state,"bag")
equal(row.owned_alternatives[2].item_id,3); equal(row.owned_alternatives[2].state,"bank")
for _,other in ipairs(row.owned_alternatives) do equal(other.comparison.relation,"higher") end
equal(owned.bankScanned,false,"comparison does not invent bank freshness")
''')

    def test_history_gaps_and_future_summary_are_shared_without_invented_continuity(self):
        self.run_lua([use(1,"T4","Best",1),use(1,"SWP","Good",3),use(2,"T5")],r'''
local h=history(1,"T5")
equal(h.selected.status,"not_listed"); equal(h.phases.T6.status,"no_guide")
equal(h.latest_earlier.phase,"T4"); equal(h.future_summary.phases[1],"SWP")
assert(h.future_summary.text:find("Also recommended in Sunwell Plateau",1,true))
assert(not h.future_summary.text:find("through",1,true))
equal(history(1,"T5"),h,"history is cached per progression context")
local wishlist=BigBiSList:GetWishlistExpansionSummary(1,"Warrior","Fury","T5")
equal(wishlist.future_summary.text,h.future_summary.text)
local tooltip=BigBiSList:GetGroupedTooltipMatches(1,"Warrior","Fury",true,nil,{selectedPhase="T5"},true)
equal(tooltip[1].future_summary.text,h.future_summary.text)
assert(not tooltip[1].phase_summary:find("T4-SWP",1,true),"gaps cannot become a continuous phase range")
''')

    def test_slot_comparison_keeps_unranked_reference_and_first_physical_empty_slot(self):
        self.run_lua([use(1,"T6",slot="Ring"),use(2,"T5",slot="Ring")],r'''
local owned={equippedSlots={Finger1={item_id=999}}}
local rows=BigBiSList:GetSlotComparisonRows("Warrior","Fury","T6","Ring",owned)
equal(rows.reference.slotKey,"Finger0"); equal(rows.reference.occupancy,"empty")
assert(byId(rows,999),"unranked equipped item retained in comparison list")
local explicit=BigBiSList:GetSlotComparisonRows("Warrior","Fury","T6","Ring",owned,999)
equal(explicit.reference.item_id,999); assert(byId(explicit,999).is_reference)
equal(byId(explicit,1).comparison.relation,"unranked")
''')

    def test_history_cache_has_a_bound_and_equipment_changes_do_not_rewrite_evidence(self):
        self.run_lua([use(1,"T6","Best",1),use(2,"T6","Good",3)],r'''
local first=history(1)
local owned={ [2]="equipped",equippedSlots={Head={item_id=2}} }
assert(byId(planner("T6",owned,"higher_rated"),1))
owned.equippedSlots.Head.item_id=1; owned[1]="equipped"; owned[2]=nil
assert(not byId(planner("T6",owned,"higher_rated"),1),"new equipment updates comparisons")
equal(history(1),first,"ownership does not replace stable guide evidence")
for id=1000,1950 do history(id) end
local index=BigBiSList:GetDataIndex("T6")
local count=0
for _ in pairs(index.recommendationHistoryCache) do count=count+1 end
assert(count<=900 and #index.recommendationHistoryOrder<=900,"history retention must stay bounded")
equal(history(1).selected.label,first.selected.label,"evicted history rehydrates deterministically")
''')


if __name__ == "__main__":
    unittest.main()
