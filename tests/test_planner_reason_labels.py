"""Planner wording changes must leave recommendation scores and uses intact."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


BOOTSTRAP = r'''
BigBiSList = {}
BigBiSListData = { phases = {
    {key="T4", name="Phase 1"}, {key="T5", name="Phase 2"},
    {key="T6", name="Phase 3"}, {key="ZA", name="Phase 4"},
    {key="SWP", name="Phase 5"},
} }
dofile("DataIndex.lua")
local phaseIndices = { LEVELING=0, PR=1, T4=2, T5=3, T6=4, ZA=5, SWP=6 }
function BigBiSList:GetAvailabilityPhaseIndex(phase) return phaseIndices[phase] end
local score
for index=1,100 do
    local name, value = debug.getupvalue(BigBiSList.GetPlannerRows, index)
    if name == "scorePlannerGroup" then score = value; break end
    if not name then break end
end
assert(score, "planner scoring closure is unavailable")
local function use(phase, rank)
    return { phase=phase, phaseIndex=phaseIndices[phase], rank_group=rank or "ranked" }
end
local function group(uses, selected)
    local result = { uses=uses, bestUse=uses[1] }
    score(result, selected or "T4")
    return result
end
local function equal(actual, expected)
    assert(actual == expected, "expected " .. tostring(expected) .. ", got " .. tostring(actual))
end
local function hasReason(result, text)
    for _, reason in ipairs(result.reasons) do if reason == text then return true end end
    return false
end
local function readableReasons(result)
    local seen = {}
    for _, reason in ipairs(result.reasons) do
        assert(not seen[reason], "duplicate phase explanation: " .. reason)
        seen[reason] = true
        assert(not reason:find("alts", 1, true), "unexplained shorthand: " .. reason)
        assert(not reason:find("future BiS", 1, true), "raw future count: " .. reason)
        assert(not reason:match("^%d+ "), "raw use count: " .. reason)
    end
    equal(result.recommendation_summary, result.reasons[1])
end
'''


class PlannerReasonLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, script):
        if not self.lua:
            self.skipTest("Lua 5.1 is not available")
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, input=BOOTSTRAP + script,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_current_and_future_primary_reasons_use_plain_phase_names(self):
        self.run_lua(r'''
local currentBis = group({ use("T4", "bis") })
equal(currentBis.recommendation_summary, "Best in slot this phase")
equal(currentBis.priority, 60)
local currentAlternative = group({ use("T4") })
equal(currentAlternative.recommendation_summary, "Alternative this phase")
equal(currentAlternative.priority, 30)
local futureBis = group({ use("T5", "bis") })
equal(futureBis.recommendation_summary, "Best in slot in Phase 2")
equal(futureBis.priority, 48)
local futureAlternative = group({ use("T5") })
equal(futureAlternative.recommendation_summary, "Alternative in Phase 2")
equal(futureAlternative.priority, 9)
for _, result in ipairs({ currentBis, currentAlternative, futureBis, futureAlternative }) do readableReasons(result) end
''')

    def test_duplicate_variants_keep_score_contributions_but_deduplicate_phase_text(self):
        self.run_lua(r'''
local uses = { use("T5"), use("T5"), use("T6"), use("SWP") }
local result = group(uses)
equal(result.priority, 26) -- Four original alternative uses * 4, plus ten longevity points.
equal(result.recommendation_summary, "Alternative in Phase 2")
equal(result.reasons[2], "Alternative in Phase 3")
equal(result.reasons[3], "Alternative in Phase 5")
equal(result.reasons[4], "Listed through Phase 5")
equal(#result.reasons, 4)
equal(#result.uses, 4)
equal(result.uses, uses)
equal(result.lastUsefulPhase, "SWP")
equal(result.recommendation_tier, "only_if_easy")
readableReasons(result)
local single = group({ uses[1], uses[3], uses[4] })
equal(result.priority - single.priority, 4)
equal(table.concat(result.reasons, "\n"), table.concat(single.reasons, "\n"))
''')

    def test_mixed_and_duplicate_bis_uses_preserve_numeric_priority_and_tiers(self):
        self.run_lua(r'''
local current = group({ use("T4", "bis"), use("T5", "bis"), use("T5", "bis"), use("T6"), use("T6"), use("T6") })
equal(current.priority, 98)
equal(current.priorityTier, "BiS Now")
equal(current.recommendation_tier, "chase_first")
equal(current.recommendation_summary, "Best in slot this phase")
assert(hasReason(current, "Best in slot in Phase 2"))
assert(hasReason(current, "Alternative in Phase 3"))
readableReasons(current)
local future = group({ use("T5", "bis"), use("T5", "bis"), use("T6", "bis"), use("T6"), use("T6") })
equal(future.priority, 77)
equal(future.recommendation_summary, "Best in slot in Phase 2")
assert(hasReason(future, "Best in slot in Phase 3"))
assert(hasReason(future, "Alternative in Phase 3"))
readableReasons(future)
local saturated = group({ use("T4", "bis"), use("T5", "bis"), use("T5", "bis"), use("T5", "bis"), use("T6", "bis"), use("T6", "bis") })
equal(saturated.priority, 100)
readableReasons(saturated)
''')

    def test_pre_raid_keeps_its_existing_display_label(self):
        self.run_lua(r'''
local result = group({ use("PR") }, "LEVELING")
equal(result.recommendation_summary, "Alternative in Pre-Raid")
equal(result.priority, 9)
readableReasons(result)
''')


if __name__ == "__main__":
    unittest.main()
