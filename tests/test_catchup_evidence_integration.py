"""Evidence integration regressions across planner and equipment surfaces."""
from copy import deepcopy
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.generate_lua import SCHEMAS, build_uses, compact_record
from tools.project import ADDON_DIR, lua_value


def fixture_use(item_id, phase="T5", label="Best", grade=1):
    return {"class": "Warrior", "spec": "Fury", "phase": phase, "slot": "Head",
            "source_url": "https://example.invalid/guide", "item_id": item_id,
            "rank_label": label, "rank_group": "bis", "rank": 1, "context": "standard",
            "guide_evidence": [{"table_id": "fixture:table", "guide_phase": phase,
                                "rating_phase": phase, "original_rating": label, "grade": grade,
                                "conditions": [], "source_url": "https://example.invalid/guide"}]}


class CatchupEvidenceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body, uses=None):
        if not self.lua:
            self.skipTest("Lua 5.1 unavailable")
        script = "BigBiSList={}\nGetServerTime=function() return 1788700000 end\n"
        if uses is None:
            script += 'dofile("Data.lua")\n'
        else:
            items = [{"id": item_id, "name": "Fixture " + str(item_id), "acquisition_phase": "PR",
                      "sources": [{"type": "quest", "quest_id": 1000 + item_id,
                                   "entity_name": "Fixture quest", "zone": "Fixture zone"}]}
                     for item_id in sorted({use["item_id"] for use in uses})]
            pool = []
            rows = [{"class": use["class"], "spec": use["spec"], "phase": use["phase"], "slot": use["slot"],
                     "source_url": use["source_url"], "items": [use]} for use in uses]
            data = {"format": 2, "schemas": SCHEMAS,
                    "classes": [{"name": "Warrior", "specs": [{"name": "Fury"}]}],
                    "items": [compact_record(item, "item") for item in items],
                    "uses": build_uses(rows, pool), "guide_evidence": pool}
            script += "BigBiSListData=" + lua_value(data) + "\n"
        script += 'dofile("DataIndex.lua")\n' + body
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=script,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_bis_rows_keep_optional_filter_argument(self):
        self.run_lua(r'''
local rows = BigBiSList:GetPhaseRows("Warrior", "Fury", "T5")
assert(#rows == 1 and #rows[1].items == 1, "omitted filters should use default BiS scope")
''', [fixture_use(1)])

    def test_historical_planner_rows_keep_optional_filter_argument(self):
        self.run_lua(r'''
local rows = BigBiSList:GetPlannerRows("Warrior", "Fury", "T6")
assert(#rows == 1 and rows[1].historical_only, "omitted filters should include historical candidates")
''', [fixture_use(1)])

    def test_ambiguous_source_occurrences_do_not_multiply_pursuit_score(self):
        use = fixture_use(1)
        second = deepcopy(use["guide_evidence"][0])
        second["table_id"] = "fixture:other-table"
        use["guide_evidence"].append(second)
        self.run_lua(r'''
local rows = BigBiSList:GetPlannerRows("Warrior", "Fury", "T4", {upgradeMode="all"})
assert(#rows == 1)
assert(rows[1].priority == 48, "one future BiS use must retain priority48, got " .. rows[1].priority)
local history = BigBiSList:GetRecommendationHistory(1,"Warrior","Fury","T4","Head")
assert(#history.phases.T5.evidence == 2, "both possible source tables must remain inspectable")
''', [use])

    def test_unavailable_future_item_is_not_added_by_historical_label(self):
        self.run_lua(r'''
local rows = BigBiSList:GetPlannerRows("Warrior", "Fury", "T4", {upgradeMode="all",includeEarlier=true})
for _, row in ipairs(rows) do
    assert(row.item_id ~= 29995, "Tempest Keep item cannot be available in T4")
end
''')

    def test_my_gear_does_not_promote_historical_best_to_current_bis(self):
        self.run_lua(r'''
local owned = { [29995]="equipped", equippedSlots={Legs={item_id=29995}} }
local rows = BigBiSList:GetEquippedGearRows("Warrior","Fury","T6",owned)
local found
for _, row in ipairs(rows) do if row.item_id == 29995 then found=row end end
assert(found, "equipped item stays visible")
assert(found.recommendation_summary ~= "Best in slot", "P2 Best cannot become current Best in slot in My Gear")
''')

    def test_current_metadata_pool_retains_distinct_real_source_tables(self):
        self.run_lua(r'''
local result = BigBiSList:CompareRecommendationItems(30977,30898,"Warrior","Fury","T6","Legs")
assert(result.relation == "unranked", "Great row2 and Good row1 are different source tables")
local first = BigBiSList:GetRecommendationHistory(30977,"Warrior","Fury","T6","Legs")
assert(first.phases.T6.evidence[1].grade == 2, "pooled explicit Great grade is decoded")
''')

    def test_retrospective_best_mention_does_not_conflict_with_original_phase_rating(self):
        self.run_lua(r'''
local history = BigBiSList:GetRecommendationHistory(29995,"Warrior","Fury","T5","Legs")
assert(history.selected.status == "rated", "T6 P2 Best confirms, rather than conflicts with, the T5 Best rating")
assert(history.selected.rank_group == "bis", "direct T5 Best remains an unconditional rating")
assert(history.selected.label ~= "Depends on setup", "a historical phase qualifier is not a different setup")
''')

    def test_direct_phase_comparison_wins_over_retrospective_pair(self):
        better, lesser = fixture_use(1), fixture_use(2, label="Good", grade=3)
        past_better = fixture_use(1, "T6", "P2 Best", None)
        past_lesser = fixture_use(2, "T6", "P2 Good", None)
        for use in (past_better, past_lesser):
            use["guide_evidence"][0].update(table_id="fixture:later-table", rating_phase="T5",
                                           conditions=[use["rank_label"]])
        self.run_lua(r'''
local result = BigBiSList:CompareRecommendationItems(1,2,"Warrior","Fury","T5","Head")
assert(result.relation == "higher", "retrospective mentions cannot invalidate a shared explicit T5 comparison")
''', [better, lesser, past_better, past_lesser])


if __name__ == "__main__":
    unittest.main()
