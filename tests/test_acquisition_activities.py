"""Required activities and source-item origins remain distinct acquisition facts."""
from copy import deepcopy
import json
import subprocess
import unittest

from test_addon_runtime_lua import find_lua51
from tools.generate_lua import SCHEMAS, compact_record
from tools.phase_source_overrides import apply_source_rule_overrides
from tools.project import ADDON_DIR, canonical_json, lua_value


def token_origin(item_id, zone="Tempest Keep", rate=12, content="raid"):
    return {"type": "drop", "entity_id": 1000, "entity_name": "Fixture boss",
            "zone": zone, "content_type": content, "drop_percent": rate,
            "token_item_id": item_id, "token_name": "Token " + str(item_id), "token_count": 1}


def token_item(children):
    source = {"type": "token_turnin", "vendor_id": 2000, "entity_id": 2000,
              "entity_name": "Fixture vendor", "zone": "Shattrath City",
              "costs": [{"item_id": 201, "name": "Token 201", "amount": 1}],
              "token_sources": children}
    return {"id": 100, "name": "Fixture reward", "acquisition_phase": "PR",
            "sources": [source], "primary_source": deepcopy(source)}


class AcquisitionActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body, items=None):
        if not self.lua:
            self.skipTest("Lua 5.1 unavailable")
        script = "BigBiSList={}\nGetServerTime=function() return 1788700000 end\n"
        if items is None:
            script += 'dofile("Data.lua")\n'
        else:
            data = {"format": 2, "schemas": SCHEMAS, "classes": [],
                    "items": [compact_record(item, "item") for item in items]}
            script += "BigBiSListData=" + lua_value(data) + "\n"
        script += 'dofile("DataIndex.lua")\n' + body
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=script,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_reviewed_activity_override_is_narrow_and_source_backed(self):
        rule = next(rule for rule in canonical_json("overrides")["overrides"]
                    if rule["id"] == "quest-10704-required-dungeon-activities")
        evidence = json.loads((ADDON_DIR / rule["data"]["evidence_path"]).read_text())
        self.assertIn("How to Break Into the Arcatraz in The Botanica and The Mechanar", json.dumps(evidence))
        corrected = []
        for item in canonical_json("items")["items"]:
            self.assertEqual(apply_source_rule_overrides(item, [rule]), item)
            for source in item["sources"]:
                if source.get("quest_id") == 10704:
                    corrected.append(item["id"])
                    self.assertEqual(len(item["sources"]), 1)
                    self.assertEqual(source["activity_zones"], ["The Botanica", "The Mechanar"])
                    self.assertNotIn("zone", source)
                    self.assertEqual(item["acquisition_phase"], "PR")
        self.assertEqual(corrected, [31460, 31461, 31462, 31464])

    def test_earlier_quest_does_not_leak_into_raid_filter(self):
        self.run_lua(r'''
local function find(groups)
    for _, group in ipairs(groups) do for _, row in ipairs(group.items) do
        if row.item_id == 31464 then return row end
    end end
end
for _, phase in ipairs({"T4", "T5", "T6"}) do
    for _, earlier in ipairs({false, true}) do
        for _, filter in ipairs({{zone="Tempest Keep"}, {zones={["Tempest Keep"]=true}}}) do
            filter.includeEarlier, filter.upgradeMode = earlier, "all"
            assert(not find(BigBiSList:GetPhaseRows("Druid","Feral dps",phase,filter)))
            for _, row in ipairs(BigBiSList:GetPlannerRows("Druid","Feral dps",phase,filter)) do
                assert(row.item_id ~= 31464)
            end
        end
    end
end
for _, zone in ipairs({"The Botanica", "The Mechanar"}) do
    local filters = {zones={[zone]=true},includeEarlier=true}
    local row = find(BigBiSList:GetPhaseRows("Druid","Feral dps","T5",filters))
    assert(row and #BigBiSList:GetRowAccessOptions(row) == 1)
    assert(BigBiSList:GetActivityGroup(row) == zone)
    assert(row.acquisition_display.activity_zone == zone)
end
local row = find(BigBiSList:GetPhaseRows("Druid","Feral dps","T4",{}))
assert(row and BigBiSList:GetActivityGroup(row) == "The Botanica + The Mechanar")
local facets = BigBiSList:GetFilterAvailabilitySnapshot("Druid","Feral dps","T5","BiS List",
    {zone="Tempest Keep",includeEarlier=true})
for _, kind in ipairs(facets.sourceTypes) do assert(kind ~= "quest") end
local reward = {item_id=30017,item=BigBiSList:GetItemData(30017)}
assert(BigBiSList:RowMatchesFilters(reward,{zone="Tempest Keep"},"T5"),"raid quest starter remains a raid activity")
''')

    def test_same_boss_different_tokens_keep_independent_rates(self):
        self.run_lua(r'''
local option = BigBiSList:GetRowAccessOptions({item_id=100})[1]
assert(#option.source.token_sources == 2, "different tokens must not merge by boss ID")
local cards = BigBiSList:GetAccessOptionSourceItems(option,{phase="T5"})
assert(#cards == 2 and cards[1].item_id ~= cards[2].item_id)
assert(#cards[1].routes == 1 and #cards[2].routes == 1)
assert(cards[1].routes[1].rate_text == "12.0%")
assert(cards[2].routes[1].rate_text == "25.0%")
''', [token_item([token_origin(201), token_origin(202, rate=25)])])

    def test_source_and_location_cannot_match_different_dependencies(self):
        self.run_lua(r'''
local row = {item_id=100}
local option = BigBiSList:GetRowAccessOptions(row)[1]
assert(not BigBiSList:GetAccessOptionFilterMatch(option,{sourceType="raid_drop",zone="The Mechanar"},"T5"))
assert(not BigBiSList:RowMatchesFilters(row,{sourceTypes={raid_drop=true},zones={["The Mechanar"]=true}},"T5"))
local match = BigBiSList:GetAccessOptionFilterMatch(option,{sourceType="dungeon_drop",zone="The Mechanar"},"T5")
assert(match and match.dependency.token_item_id == 202 and match.activity_zone == "The Mechanar")
assert(BigBiSList:RowMatchesFilters(row,{sourceType="dungeon_drop",zone="The Mechanar"},"T5"))
local cards = BigBiSList:GetAccessOptionSourceItems(option,{phase="T5",filters={zone="The Mechanar"}})
assert(not cards[1].routes[1].matched and cards[2].routes[1].matched)
''', [token_item([token_origin(201), token_origin(202, "The Mechanar", 25, "dungeon")])])

    def test_same_token_keeps_available_and_future_origins(self):
        self.run_lua(r'''
local option = BigBiSList:GetRowAccessOptions({item_id=100})[1]
local cards = BigBiSList:GetAccessOptionSourceItems(option,{phase="T5"})
assert(#cards == 1 and #cards[1].routes == 2)
assert(cards[1].routes[1].available and not cards[1].routes[2].available)
assert(cards[1].routes[2].availability_label and cards[1].routes[2].acquisition_phase == "T6")
assert(not BigBiSList:GetAccessOptionFilterMatch(option,{zone="Hyjal Summit"},"T5"))
''', [token_item([token_origin(201), token_origin(201, "Hyjal Summit", 40)])])

    def test_nested_source_changes_do_not_reuse_cached_rates(self):
        first = token_item([token_origin(201)])
        second = token_item([token_origin(201, rate=33)])
        self.run_lua('local first=' + lua_value(first) + '\nlocal second=' + lua_value(second) + r'''
local a = BigBiSList:GetRowAccessOptions({item_id=100,item=first})[1]
local b = BigBiSList:GetRowAccessOptions({item_id=100,item=second})[1]
assert(a ~= b, "different source context must not share cached access options")
assert(BigBiSList:GetAccessOptionSourceItems(a,{phase="T5"})[1].routes[1].rate_text == "12.0%")
assert(BigBiSList:GetAccessOptionSourceItems(b,{phase="T5"})[1].routes[1].rate_text == "33.0%")
''', [])

    def test_shared_rate_formatter_guards_invalid_and_tiny_rates(self):
        self.run_lua(r'''
for _, value in ipairs({-1,101,math.huge,0/0,"unknown"}) do
    assert(BigBiSList:FormatSourceRate({drop_percent=value}) == nil)
end
assert(BigBiSList:FormatSourceRate({}) == nil)
assert(BigBiSList:FormatSourceRate({count=1,out_of=0}) == nil)
assert(BigBiSList:FormatSourceRate({count=4,out_of=2}) == nil)
assert(BigBiSList:FormatSourceRate({count=1,out_of=10000}) == "<0.1%")
assert(BigBiSList:FormatSourceRate({drop_percent=0.01}) == "<0.1%")
assert(BigBiSList:FormatSourceRate({drop_percent=0}) == "0.0%")
assert(BigBiSList:FormatSourceRate({drop_percent=100}) == "100.0%")
''', [])


if __name__ == "__main__":
    unittest.main()
