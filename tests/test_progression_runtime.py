"""Progression regressions using committed item evidence and simulated schedules.

The small recommendation matrix and source-window variants below are scenarios,
not additional ranking or vendor-price claims for the shipping data set.
"""
from copy import deepcopy
import json
import subprocess
import unittest

from tools.generate_lua import SCHEMAS, compact_record
from tools.project import ADDON_DIR, canonical_json, lua_value
from tools.sources import PHASE_ORDER, item_has_pre_raid_route, source_is_phase_available
from test_addon_runtime_lua import LUA_ASSERTIONS, find_lua51


class ProgressionRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()
        cls.items = {item["id"]: item for item in canonical_json("items")["items"]}

    def run_lua(self, body, data=None):
        if not self.lua:
            self.skipTest("Lua 5.1 is not available")
        setup = "BigBiSList = {}\n"
        if data is not None:
            setup += "BigBiSListData = " + lua_value(data) + "\n"
        result = subprocess.run(
            [self.lua, "-"], cwd=ADDON_DIR, input=LUA_ASSERTIONS + setup + body,
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_all_canonical_source_windows_agree_with_python(self):
        records = []
        seen = set()
        for family in ("items", "gem_sources", "enchant_sources"):
            for collection in canonical_json(family).values():
                if not isinstance(collection, list):
                    continue
                for record in collection:
                    for source in record.get("sources", []):
                        fingerprint = json.dumps(source, sort_keys=True)
                        if fingerprint in seen:
                            continue
                        seen.add(fingerprint)
                        records.append({
                            "label": f"{family}:{record.get('id', record.get('spell_id'))}",
                            "source": source,
                            "expected": [source_is_phase_available(source, phase) for phase in PHASE_ORDER],
                        })
        self.assertTrue(records)
        # Bound each Lua process independently so future evidence growth does
        # not turn the full-data release gate into an unbounded fixture load.
        for offset in range(0, len(records), 1024):
            with self.subTest(batch=offset // 1024):
                self.run_lua('dofile("DataIndex.lua")\nlocal records = '
                             + lua_value(records[offset:offset + 1024]) + r'''
for _, record in ipairs(records) do
    for index, phase in ipairs(BigBiSList:GetPhaseOrder()) do
        equal(BigBiSList:IsAccessOptionPhaseAvailable({source=record.source}, index),
            record.expected[index], record.label .. " source availability in " .. phase)
    end
end
''', {})

    def test_all_canonical_pre_raid_item_routes_agree_with_python(self):
        items = list(self.items.values())
        for offset in range(0, len(items), 512):
            batch = items[offset:offset + 512]
            data = {"format": 2, "schemas": SCHEMAS, "classes": [],
                    "items": [compact_record(item, "item") for item in batch]}
            expected = {item["id"]: [item_has_pre_raid_route(item, phase) for phase in PHASE_ORDER]
                        for item in batch}
            with self.subTest(batch=offset // 512):
                self.run_lua('dofile("DataIndex.lua")\nlocal expected = ' + lua_value(expected) + r'''
local live = "PR"
BigBiSList.GetCurrentPhaseKey = function() return live end
for index, phase in ipairs(BigBiSList:GetPhaseOrder()) do
    live = phase
    for itemId, matrix in pairs(expected) do
        local row = {item_id=itemId, item=BigBiSList:GetItemData(itemId)}
        equal(BigBiSList:RowMatchesFilters(row, {}, "PR"), matrix[index],
            "item " .. itemId .. " Pre-Raid eligibility in " .. phase)
    end
end
''', data)

    def test_legacy_craft_trade_hint_does_not_prove_a_pre_raid_route(self):
        unknown = deepcopy(self.items[23766])
        unknown.update(id=900010, binding="unknown", boe=None)
        unknown.pop("tradeable", None)
        verified = deepcopy(unknown)
        verified.update(id=900011, tradeable=True)
        data = {"format": 2, "schemas": SCHEMAS, "classes": [],
                "items": [compact_record(item, "item") for item in (unknown, verified)]}
        self.run_lua(r'''
dofile("DataIndex.lua")
BigBiSList.GetCurrentPhaseKey = function() return "T6" end
local unknown = {item_id=900010, item=BigBiSList:GetItemData(900010)}
local verified = {item_id=900011, item=BigBiSList:GetItemData(900011)}
expect(not BigBiSList:RowMatchesFilters(unknown, {}, "PR"), "unknown binding cannot bypass a raid-only recipe")
expect(BigBiSList:RowMatchesFilters(verified, {}, "PR"), "explicit tradeability permits buying the finished item")
expect(BigBiSList:RowMatchesFilters(unknown, {}, "T6"), "raid-tier acquisition remains available")
local legacyTrade
for _, option in ipairs(BigBiSList:GetRowAccessOptions(unknown)) do
    if option.source_type == "trade" then legacyTrade = option end
end
expect(legacyTrade and legacyTrade.is_inferred_trade_option, "existing crafted market hint remains distinguishable")
expect(not BigBiSList:IsPreRaidAccessOption(legacyTrade, 4), "market hint alone is not personal raid exemption")
''', data)

    def test_refreshed_class_facts_filter_archived_leveling_rows_without_reranking(self):
        item_ids = (22589, 22630, 22632, 27922, 27924)
        restrictions = {}
        for item_id in item_ids:
            path = next((ADDON_DIR / "data/raw/wowhead/progression_items").glob(f"*item-{item_id}-*json"))
            evidence = json.loads(path.read_text(encoding="utf-8"))
            restrictions[item_id] = evidence["item_stats"]["restrictions"]["classes"]
        recommendations = [row for row in canonical_json("leveling_recommendations")["leveling_recommendations"]
                           if row["item_id"] in item_ids]
        allowed = [row for row in recommendations if row["class"] in restrictions[row["item_id"]]]
        self.assertEqual(len(recommendations) - len(allowed), 25, "committed archived rows made ineligible by refreshed facts")
        expected = {item_id: [row for row in allowed if row["item_id"] == item_id] for item_id in item_ids}
        # Both ingestion paths need the same fact check. These two guide rows
        # isolate that path while the computed rows remain exact committed data.
        guide_rows = [{"class": class_name, "spec": spec_name, "item_id": 22589,
                       "level_min": 60, "level_max": 69, "slot": "Two Hand", "rank": 3}
                      for class_name, spec_name in (("Mage", "Arcane"), ("Druid", "Balance"))]
        for compact in (True, False):
            data = {"classes": canonical_json("classes")["classes"],
                    "items": [deepcopy(self.items[item_id]) for item_id in item_ids],
                    "item_class_restrictions": restrictions,
                    "leveling_recommendations": deepcopy(recommendations), "leveling_gear": deepcopy(guide_rows)}
            if compact:
                data.update(format=2, schemas=SCHEMAS)
                for field, schema in (("items", "item"), ("leveling_recommendations", "leveling_recommendation"),
                                      ("leveling_gear", "leveling_gear")):
                    data[field] = [compact_record(row, schema) for row in data[field]]
            with self.subTest(compact=compact):
                self.run_lua('local expected = ' + lua_value(expected) + r'''
dofile("DataIndex.lua")
local originalCount = #BigBiSListData.leveling_recommendations
for itemId, archived in pairs(expected) do
    local uses = BigBiSList:GetItemLevelingRecommendationUses(itemId)
    equal(#uses, #archived, "eligible archived rows for item " .. itemId)
    for _, use in ipairs(uses) do
        expect(contains(BigBiSListData.item_class_restrictions[itemId], use.class), "class can equip item")
        local exact
        for _, row in ipairs(archived) do
            if row.class == use.class and row.spec == use.spec and row.race == use.race
                and row.level_min == use.level_min and row.level_max == use.level_max
                and row.rank == use.rank and row.score == use.score and row.context == use.context then exact = true end
        end
        expect(exact, "eligible ranks and scores remain unchanged")
    end
end
equal(#BigBiSList:GetItemLevelingUses(22589), #expected["22589"] + 1, "guide and computed paths apply the same restriction")
equal(BigBiSList:GetItemBestLevelingUseForSpec(22589, "Druid", "Balance", 60), nil, "wrong-class item cannot be an owned baseline")
equal(BigBiSList:GetItemNextLevelingUseForSpec(22589, "Druid", "Balance", 59), nil, "wrong-class item cannot be a future upgrade")
expect(BigBiSList:GetItemBestLevelingUseForSpec(22589, "Mage", "Arcane", 60), "Mage keeps its Atiesh recommendation")
for _, use in ipairs(BigBiSList:GetLevelingTooltipMatches(22589, "Druid", "Balance", 60)) do
    equal(use.class, "Mage", "tooltip only reports an eligible class")
end
for _, group in ipairs(BigBiSList:GetLevelingRows("Druid", "Balance", 62, {})) do
    for _, row in ipairs(group.items) do
        expect(contains(BigBiSListData.item_class_restrictions[tostring(row.item_id)], "Druid"), "leveling list rejects wrong-class item")
    end
end
equal(#BigBiSListData.leveling_recommendations, originalCount, "archived ranking records are untouched")
BigBiSListData.item_class_restrictions = nil
BigBiSList.dataIndex = nil
expect(#BigBiSList:GetItemLevelingRecommendationUses(22589) > #expected["22589"], "older generated data without restrictions stays compatible")
''', data)

    def fixture(self, compact=True):
        phases = canonical_json("phases")
        data = {
            "classes": [{"name": "Warrior", "specs": [{"name": "Fury"}]}],
            "phases": phases["phases"],
            "active_schedule": phases["active_schedule"],
            "phase_schedules": phases["schedules"],
            "items": [deepcopy(self.items[key]) for key in (31462, 31332, 28568, 24028, 24030)],
            "gems": [],
        }
        uses = []
        for phase in PHASE_ORDER:
            modern = phase in ("T6", "ZA", "SWP")
            uses.append({"class": "Warrior", "spec": "Fury", "phase": "PR", "content_phase": phase,
                         "slot": "Main Hand" if modern else "Waist", "item_id": 31332 if modern else 31462,
                         "rank": 1, "rank_group": "bis", "rank_label": "Best"})
            # A malformed imported PR raid reward must still fail the runtime route guard.
            uses.append({"class": "Warrior", "spec": "Fury", "phase": "PR", "content_phase": phase,
                         "slot": "Idol", "item_id": 28568, "rank": 1, "rank_group": "bis"})
            data["gems"].append({"class": "Warrior", "spec": "Fury", "phase": phase,
                                 "id": 24030 if modern else 24028,
                                 "name": self.items[24030 if modern else 24028]["name"], "socket": "red"})
        uses.append({"class": "Warrior", "spec": "Fury", "phase": "T4", "slot": "Waist",
                     "item_id": 31462, "rank": 1, "rank_group": "bis"})
        if compact:
            data.update({"format": 2, "schemas": SCHEMAS,
                         "uses": [compact_record(use, "use") for use in uses],
                         "items": [compact_record(item, "item") for item in data["items"]],
                         "gems": [compact_record(gem, "gem") for gem in data["gems"]]})
        else:
            data["bis_lists"] = [{"class": "Warrior", "specs": [{"spec": "Fury", "phases": [
                {"phase": use["phase"], "content_phase": use.get("content_phase"), "slots": [
                    {"slot": use["slot"], "items": [{key: value for key, value in use.items()
                                                    if key not in ("class", "spec", "phase", "content_phase", "slot")}]}]}
                for use in uses
            ]}]}]
        return data

    def test_live_pr_context_rolls_over_and_replacement_schedule_restores_history(self):
        for compact in (True, False):
            with self.subTest(compact=compact):
                self.run_lua(r'''
local now = 1787867999
GetServerTime = function() return now end
dofile("DataIndex.lua")
equal(BigBiSList:GetCurrentPhaseKey(), "T5", "one second before launch")
local before = BigBiSList:GetDataIndex()
local rows = BigBiSList:GetPhaseRows("Warrior", "Fury", "PR", {})
equal(#rows, 1, "raid-only reward is excluded")
equal(rows[1].items[1].item_id, 31462, "earlier PR path")
equal(rows[1].items[1].content_phase, "T5", "inherited path retains context")
equal(BigBiSList:GetEnhancementRows("Warrior", "Fury", "PR", {})[1].rows[1].item_id, 24028, "earlier gem context")
now = 1787868000
equal(BigBiSList:GetCurrentPhaseKey(), "T6", "launch boundary")
expect(BigBiSList:GetDataIndex() ~= before, "index invalidates at launch")
rows = BigBiSList:GetPhaseRows("Warrior", "Fury", "PR", {})
equal(rows[1].items[1].item_id, 31332, "live catch-up path")
equal(rows[1].items[1].content_phase, "T6", "live PR context")
local planner = BigBiSList:GetPlannerRows("Warrior", "Fury", "PR", { upgradeMode = "all" })
equal(#planner, 1, "only current PR target scores")
equal(planner[1].priority, 60, "past phases do not count as future upgrades")
equal(planner[1].matched_access_option.acquisition_phase, "PR", "earlier route stays usable")
local gems = BigBiSList:GetEnhancementRows("Warrior", "Fury", "PR", {})[1].rows
equal(gems[1].item_id, 24030, "enhancements follow live phase")
equal(#BigBiSList:GetTooltipMatches(31332, "Warrior", "Fury"), 1, "tooltip gets current PR path")
equal(#BigBiSList:GetTooltipMatches(31332, "Warrior", "Fury", true, nil, {selectedPhase="T4"}), 0, "manual tier does not inherit later PR tooltip rank")
equal(BigBiSList:GetItemBestUseForSpec(31332, "Warrior", "Fury", "T4"), nil, "later PR cannot become an earlier-tier upgrade baseline")
equal(#BigBiSList:GetPlannerRows("Warrior", "Fury", "T4", {upgradeMode="all"}), 1, "manual tier excludes later PR-only target")
local historic = BigBiSList:GetWishlistExpansionSummary(31462, "Warrior", "Fury", "T4")
expect(historic.selected_spec_ranking.phases.PR.matched, "manual Tier 4 retains its historical PR path")
equal(historic.selected_spec_ranking.phases.PR.use.content_phase, "T4", "historical PR context is explicit")
local historicalTooltip = BigBiSList:GetTooltipMatches(31462, "Warrior", "Fury", true, nil, {selectedPhase="T4"})
equal(#historicalTooltip, 2, "manual tier tooltip includes historical PR and raid rankings")
local earlyIndex = BigBiSList:GetDataIndex("T4")
BigBiSList:GetDataIndex("T6")
equal(BigBiSList:GetDataIndex("T4"), earlyIndex, "context index is reused across view queries")
local saved = BigBiSList:GetWishlistRows({["31332"]=true}, "Warrior", "Fury", "T4", {})
equal(#saved, 1, "saved item is retained")
expect(not saved[1].selected_spec_ranking.phases.PR.matched, "earlier tier gets no later PR ranking")
saved = BigBiSList:GetWishlistRows({["31332"]=true}, "Warrior", "Fury", "PR", {})
expect(saved[1].selected_spec_ranking.phases.PR.matched, "wishlist live PR ranking")
equal(saved[1].content_phase, "T6", "wishlist source context")
equal(#BigBiSList:GetPhaseOrder(), 6, "no extra player phase selector")
local liveIndex = BigBiSList:GetDataIndex()
BigBiSListData.phase_schedules.next_cycle = {phase_starts={
    {key="PR", starts_at_epoch=0}, {key="T4", starts_at_epoch=now+100},
    {key="T5", starts_at_epoch=now+200}, {key="T6", starts_at_epoch=now+300},
}}
BigBiSListData.active_schedule = "next_cycle"
equal(BigBiSList:GetCurrentPhaseKey(), "PR", "replacement schedule restarts progression")
expect(BigBiSList:GetDataIndex() ~= liveIndex, "replacement schedule invalidates caches")
rows = BigBiSList:GetPhaseRows("Warrior", "Fury", "PR", {})
equal(rows[1].items[1].item_id, 31462, "original early path survives refresh and replay")
equal(#BigBiSList:GetTooltipMatches(31332, "Warrior", "Fury"), 0, "old tooltip index cannot survive replacement schedule")
now = now + 300
equal(BigBiSList:GetPhaseRows("Warrior", "Fury", "PR", {})[1].items[1].item_id, 31332, "replayed Tier 6 path")
equal(BigBiSList:GetCurrentPhaseKey(now + 100000000), "T6", "unannounced dates remain unset")
for _, phase in ipairs(BigBiSList:GetPhaseOrder()) do BigBiSList:GetDataIndex(phase) end
local indexCount = 0
for _ in pairs(BigBiSList.progressionIndexes) do indexCount = indexCount + 1 end
expect(indexCount <= 3, "historical context index cache stays bounded")
''', self.fixture(compact))

    def test_content_labels_follow_generated_definitions_not_source_phase_numbers(self):
        data = self.fixture()
        next(phase for phase in data["phases"] if phase["key"] == "T6")["name"] = "Tier 6: Black Temple and Hyjal"
        data["source_phase_numbers"] = {"anniversary": {"3.5": "ZA", "4": "SWP"},
                                        "classic": {"4": "ZA", "5": "SWP"}}
        self.run_lua(r'''
dofile("DataIndex.lua")
equal(BigBiSList:GetPhaseDisplayName("T6"), "Tier 6: Black Temple and Hyjal", "generated definition supplies display name")
equal(BigBiSList:GetPhaseDisplayName("ZA"), "Zul'Aman", "ZA never inherits ambiguous Phase 4 label")
equal(BigBiSList:GetPhaseDisplayName("SWP"), "Sunwell Plateau", "Sunwell name survives differing source numbering")
equal(BigBiSList:GetPhaseShortName("T6"), "T6", "tier abbreviation is stable")
equal(BigBiSList:GetPhaseShortName("ZA"), "ZA", "ZA abbreviation is stable")
equal(BigBiSList:GetPhaseShortName("SWP"), "SWP", "Sunwell abbreviation is stable")
local summary = BigBiSList:GetWishlistExpansionSummary(31462, "Warrior", "Fury", "T4")
equal(summary.selected_spec_ranking.phases.ZA.phase_label, "Zul'Aman", "Wishlist uses content name")
equal(summary.selected_spec_ranking.phases.SWP.phase_short_label, "SWP", "Wishlist uses stable abbreviation")
BigBiSListData.active_schedule = "another_cycle"
equal(BigBiSList:GetDataIndex("SWP").phaseDisplay.T6, "Tier 6: Black Temple and Hyjal", "schedule changes do not rewrite tier definitions")
''', data)

    def test_source_windows_seller_unlocks_and_discount_routes_are_phase_scoped(self):
        item = deepcopy(self.items[33672])
        evidence_path = next((ADDON_DIR / "data/raw/wowhead/pilot").glob("*item-33672-*json"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))["normalized_sources"]
        # Historical reported prices exercise runtime windows; reviewed shipping
        # overrides may deliberately omit prices whose Anniversary date is unknown.
        full = deepcopy(next(source for source in evidence if source.get("vendor_id", source.get("entity_id")) == 18898))
        discounted = deepcopy(next(source for source in evidence if source.get("vendor_id", source.get("entity_id")) == 27721))
        exchange = deepcopy(next(source for source in item["sources"] if source.get("vendor_id") == 26092))
        full.update(available_from_phase="T6", available_until_phase="ZA")
        discounted.update(available_from_phase="ZA", available_until_phase="SWP")
        item.update(sources=[full, discounted, exchange], primary_source=discounted, acquisition_phase="T6")
        data = self.fixture()
        data["items"] = [compact_record(item, "item")]
        data["uses"] = [compact_record({"class": "Warrior", "spec": "Fury", "phase": phase,
                                      "slot": "Head", "item_id": item["id"], "rank_group": "bis", "rank": 1}, "use")
                        for phase in PHASE_ORDER if phase != "PR"]
        self.run_lua(r'''
dofile("DataIndex.lua")
local row = {item_id=33672, item=BigBiSList:GetItemData(33672)}
local options = BigBiSList:GetRowAccessOptions(row)
equal(#options, 3, "distinct vendor windows survive generation and merging")
local t5 = BigBiSList:GetRowAcquisitionDisplay(row, {}, "T5", true)
expect(t5.future and not t5.available, "Season 3 route is future in Tier 5")
equal(t5.acquisition_phase, "T6", "next real availability")
local t6 = BigBiSList:GetRowAcquisitionDisplay(row, {}, "T6")
equal(t6.option.vendor_key, "18898", "later primary discount cannot win in Tier 6")
equal(t6.option.source.costs[1].amount, 1550, "correct full price")
local za = BigBiSList:GetRowAcquisitionDisplay(row, {}, "ZA")
equal(za.option.vendor_key, "27721", "exclusive boundary selects discounted seller")
equal(za.option.source.costs[1].amount, 1245, "discount fixture price")
local swp = BigBiSList:GetRowAcquisitionDisplay(row, {}, "SWP")
equal(swp.option.vendor_key, "26092", "Isle seller unlock gates earlier tier token")
local expired = BigBiSList:GetRowAcquisitionDisplay(row, {vendors={["18898"]=true}}, "ZA", true)
expect(not expired.available and not expired.future, "expired purchase cannot be described as upcoming")
equal(expired.status, "unavailable", "expired purchase status")
equal(#BigBiSList:GetPhaseRows("Warrior", "Fury", "T5", {}), 0, "Season 3 is absent in earlier By Slot")
local facets = BigBiSList:GetFilterAvailabilitySnapshot("Warrior", "Fury", "T6", "By Slot", {})
expect(contains(facets.vendors, "18898"), "current seller filter")
expect(not contains(facets.vendors, "27721"), "later discount omitted from filters")
expect(not contains(facets.vendors, "26092"), "later token exchange omitted from filters")
local sellers = BigBiSList:GetRowSellerGroups(row, t6.option, "T6")
equal(#sellers.alternatives, 0, "inspector hides later discounts and exchanges")
equal(sellers.selected.vendor_key, "18898", "inspector preserves current seller")
local wishlist = BigBiSList:GetWishlistRows({["33672"]=true}, "Warrior", "Fury", "T6", {})
equal(wishlist[1].matched_access_option.vendor_key, "18898", "Wishlist agrees with By Slot")
''', data)

    def test_owned_upgrade_baseline_uses_the_selected_historical_context(self):
        data = self.fixture()
        data["items"].append(compact_record(self.items[29121], "item"))
        data["uses"] = [compact_record(use, "use") for use in [
            {"class": "Warrior", "spec": "Fury", "phase": "T5", "slot": "Main Hand",
             "item_id": 29121, "rank_group": "option", "rank": 2},
            {"class": "Warrior", "spec": "Fury", "phase": "PR", "content_phase": "T6", "slot": "Main Hand",
             "item_id": 31332, "rank_group": "bis", "rank": 1},
        ]]
        self.run_lua(r'''
GetServerTime = function() return 1787868000 end
dofile("DataIndex.lua")
local rows = BigBiSList:GetPlannerRows("Warrior", "Fury", "T4", {
    upgradeMode="actual", ownedItems={["31332"]="bag"},
})
equal(#rows, 1, "later PR rank cannot suppress an earlier progression upgrade")
equal(rows[1].item_id, 29121, "historical progression candidate remains visible")
equal(rows[1].upgrade_state, "missing_upgrade", "baseline uses historical recommendation context")
''', data)

    def test_python_lua_agree_on_source_boundaries_and_personal_raid_routes(self):
        samples = [deepcopy(self.items[key]) for key in (31462, 31332, 28568, 33672, 24028)]
        # Replay actual raid-drop evidence with tradeability changed to isolate personal participation.
        trade = deepcopy(self.items[28568])
        trade.update(id=900001, boe=True, binding="bind_on_equip")
        samples.append(trade)
        unbound = deepcopy(trade)
        unbound.update(id=900005, boe=None, binding="unknown", tradeable=True)
        samples.append(unbound)
        # A token exchange with a later non-raid alternative must remain raid-only until that alternative opens.
        token = deepcopy(self.items[33672])
        token.update(id=900002)
        source = deepcopy(next(source for source in token["sources"] if source.get("vendor_id") == 26092))
        source.update(zone="Shattrath City", location_area="Shattrath City")
        alternative = deepcopy(self.items[31462]["sources"][0])
        alternative["available_from_phase"] = "SWP"
        source["token_sources"].append(alternative)
        token.update(sources=[source], primary_source=source)
        samples.append(token)
        expired = deepcopy(self.items[31462])
        expired.update(id=900003)
        expired["sources"][0].update(available_from_phase="T5", available_until_phase="ZA")
        expired["primary_source"] = expired["sources"][0]
        samples.append(expired)
        craft = deepcopy(self.items[24028])
        craft.update(id=900004, binding="bind_on_pickup", boe=False)
        recipe = deepcopy(self.items[28568]["sources"][0])
        recipe.update(available_from_phase="T6", tradeable=True)
        craft["sources"][0].update(zone="Black Temple", content_type="raid", recipe_sources=[recipe])
        craft["primary_source"] = craft["sources"][0]
        samples.append(craft)
        expected_items = {item["id"]: [item_has_pre_raid_route(item, phase) for phase in PHASE_ORDER] for item in samples}
        sources = [source for item in samples for source in item["sources"]]
        expected_sources = [[source_is_phase_available(source, phase) for phase in PHASE_ORDER] for source in sources]
        data = self.fixture()
        data["items"] = [compact_record(item, "item") for item in samples]
        data["uses"] = []
        self.run_lua("local expectedItems = " + lua_value(expected_items)
                     + "\nlocal sources = " + lua_value(sources)
                     + "\nlocal expectedSources = " + lua_value(expected_sources) + r'''
dofile("DataIndex.lua")
local live = "PR"
BigBiSList.GetCurrentPhaseKey = function() return live end
for phaseIndex, phase in ipairs(BigBiSList:GetPhaseOrder()) do
    live = phase
    for sourceIndex, source in ipairs(sources) do
        local actual = BigBiSList:IsAccessOptionPhaseAvailable({source=source}, phaseIndex)
        equal(actual, expectedSources[sourceIndex][phaseIndex], "Python/Lua source " .. sourceIndex .. " phase " .. phase)
    end
    for itemId, expected in pairs(expectedItems) do
        local item = BigBiSList:GetItemData(itemId)
        local actual = BigBiSList:RowMatchesFilters({item_id=itemId, item=item}, {}, "PR")
        equal(actual, expected[phaseIndex], "Python/Lua PR item " .. itemId .. " phase " .. phase)
    end
end
''', data)

    def test_current_unpriced_season_three_seller_is_not_replaced_by_future_exchange(self):
        item = deepcopy(self.items[33672])
        seller = deepcopy(next(source for source in item["sources"] if source.get("vendor_id") == 18898))
        seller.pop("costs", None)
        seller.pop("price_copper", None)
        seller["available_from_phase"] = "T6"
        exchange = deepcopy(next(source for source in item["sources"] if source.get("vendor_id") == 26092))
        item.update(sources=[seller, exchange], primary_source=exchange, acquisition_phase="T6")
        data = self.fixture()
        data["items"] = [compact_record(item, "item")]
        data["uses"] = []
        self.run_lua(r'''
dofile("DataIndex.lua")
dofile("UI.lua")
local row = {item_id=33672, item=BigBiSList:GetItemData(33672)}
row.acquisition_display = BigBiSList:GetRowAcquisitionDisplay(row, {}, "T6")
row.matched_access_option = row.acquisition_display.option
equal(row.matched_access_option.vendor_key, "18898", "current reported seller takes precedence")
equal(row.acquisition_display.acquisition_phase, "T6", "Season 3 item availability is accurate")
expect(row.acquisition_display.available and not row.acquisition_display.future, "known release is separate from unknown price")
equal(row.acquisition_display.status, "unknown", "withheld price is not a ready purchase")
equal(BigBiSList:GetMatchingRowAccessOption(row, {vendors={["18898"]=true}}, "T6"), nil, "reported seller stays out of purchasable filters")
local UI = BigBiSList.UI
UI.currentAccess = {}
UI.GetFilters = function() return {} end
UI.GetEffectivePhaseKey = function() return "T6" end
UI.EvaluateRequirementList = function() return {status="ready", requirements={}} end
local access = UI:GetAccessEvaluation(row)
equal(access.status, "unknown", "inspector preserves unknown purchase detail")
equal(access.optionEvaluation.option, row.matched_access_option, "inspector and row agree")
''', data)

    def test_epic_and_budget_gems_keep_recipe_gates_off_purchase_routes(self):
        from tools.phase_gems import import_phase_gems, reviewed_gem_items
        from tools.scrape_wowhead import load_snapshots

        snapshots = load_snapshots(ADDON_DIR / "data/raw/wowhead/phase_gems")
        reviewed = reviewed_gem_items(snapshots)
        gems = import_phase_gems(snapshots, canonical_json("gems"))["gems"]
        selected_gems = [gem for gem in gems if
                         (gem["class"] == "Druid" and gem["spec"] == "Feral tank"
                          and gem["phase"] in ("T5", "T6") and gem["id"] in (24028, 32194))
                         or (gem["class"] == "Hunter" and gem["spec"] == "Beast mastery"
                             and gem["phase"] == "T6" and gem["id"] == 33131)]
        items = [deepcopy(self.items[24028])]
        for item_id in (32194, 33131):
            evidence = reviewed[item_id]
            items.append({"id": item_id, "name": evidence["name"], "binding": evidence["binding"],
                          "boe": evidence.get("boe"), "tradeable": evidence.get("tradeable"),
                          "quality": evidence["quality"], "requirements": evidence.get("normalized_requirements", []),
                          "sources": evidence["normalized_sources"], "primary_source": evidence["normalized_sources"][0]})
        data = self.fixture()
        data["classes"] = [{"name": "Druid", "specs": [{"name": "Feral tank"}]},
                           {"name": "Hunter", "specs": [{"name": "Beast mastery"}]}]
        data["items"] = [compact_record(item, "item") for item in items]
        data["uses"] = []
        data["gems"] = [compact_record(gem, "gem") for gem in selected_gems]
        self.run_lua(r'''
local now = 1787867999
GetServerTime = function() return now end
dofile("DataIndex.lua")
dofile("UI.lua")
local early = BigBiSList:GetEnhancementRows("Druid", "Feral tank", "PR", {})[1].rows
equal(#early, 1, "Tier 5 gem recommendations")
equal(early[1].item_id, 24028, "rare gem is the earlier recommendation")
equal(early[1].context, "standard", "earlier guidance is not relabeled as budget")
now = 1787868000
local rows = BigBiSList:GetEnhancementRows("Druid", "Feral tank", "PR", {})[1].rows
equal(#rows, 2, "Tier 6 includes verified epic and rare alternative")
local epic, budget
for _, row in ipairs(rows) do
    if row.item_id == 32194 then epic = row else budget = row end
end
equal(budget.context, "budget", "rare alternative has explicit budget context")
equal(budget.recommendation_summary, "Budget alternative", "budget role uses existing recommendation presentation")
equal(epic.content_phase, "T6", "epic recommendation follows live context")
equal(epic.matched_access_option.source_type, "trade", "Pre-Raid can buy a cut without personal raid participation")
equal(#(epic.matched_access_option.requirements or {}), 0, "buying a cut requires neither Jewelcrafting nor raid reputation")
local crafted
for _, option in ipairs(BigBiSList:GetRowAccessOptions(epic)) do
    expect(not BigBiSList:IsAccessOptionPhaseAvailable(option, 3), "all epic acquisition routes stay gated before Tier 6")
    if option.source_type == "crafted" then crafted = option end
end
expect(crafted, "personal crafting route is retained")
equal(crafted.source.recipe_sources[1].item_id, 32277, "verified epic recipe")
equal(crafted.source.recipe_sources[1].vendor_id, 23437, "verified Indormi recipe seller")
equal(crafted.source.recipe_sources[1].requirements[1].standing, "Friendly", "recipe reputation standing")
local skill
for _, requirement in ipairs(crafted.requirements) do
    if requirement.type == "profession" then skill = requirement.skill end
end
equal(skill, 375, "Jewelcrafting craft skill survives generation")
local details = BigBiSList.UI:GetSellerDetailLines(crafted)
local text = table.concat(details, "\n")
expect(string.find(text, "Indormi", 1, true), "existing inspector details show recipe seller")
expect(string.find(text, "Friendly with The Scale of the Sands", 1, true), "existing inspector details show recipe reputation")
equal(BigBiSList.UI:GetSellerDetailLines(epic.matched_access_option), nil, "recipe requirements are absent from the purchased-cut route")
local hunter = BigBiSList:GetEnhancementRows("Hunter", "Beast mastery", "T6", {})[1].rows
equal(#hunter, 1, "verified profession-specific gem")
local useSkill
for _, requirement in ipairs(hunter[1].requirements) do
    if requirement.type == "profession" and requirement.scope == "equip_or_use" then useSkill = requirement.skill end
end
equal(useSkill, 360, "Jewelcrafter-only use requirement survives compact gem schema")
for _, option in ipairs(BigBiSList:GetRowAccessOptions(hunter[1])) do
    expect(not option.is_trade_option, "bound Jewelcrafter-only gem cannot gain an AH route")
end
''', data)

    def test_saved_selections_ownership_and_query_caches_survive_progression(self):
        self.run_lua(r'''
local live = "T5"
dofile("Config.lua")
dofile("DataIndex.lua")
dofile("UI.lua")
BigBiSList.GetCurrentPhaseKey = function() return live end
BigBiSList:EnsureDatabase()
local char = BigBiSList:GetCharacterDB()
char.selection.class, char.selection.spec = "Warrior", "Fury"
char.selection.mode, char.selection.tab, char.selection.phase = "endgame", "By Slot", "PR"
char.lastDetectedPhase = "PR"
char.wishlist["31332"] = true
char.bankCache.links = {"item:31332"}
local UI = BigBiSList.UI
UI:ValidateSelection()
equal(char.selection.phase, "PR", "PR selection remains stable while content follows live phase")
equal(BigBiSList:GetProgressionContext(char.selection.phase).content_phase, "T5", "saved PR resolves live")
char.selection.phase, char.lastDetectedPhase = "T5", "T5"
live = "T6"
UI:ValidateSelection()
equal(char.selection.phase, "T5", "manual tier equal to last live tier is preserved")
expect(char.wishlist["31332"], "wishlist retained")
equal(char.bankCache.links[1], "item:31332", "bank ownership retained")
local count = 0
local function query() count=count+1; return {count=count} end
local first = UI:GetCachedViewQuery("phase", query)
equal(UI:GetCachedViewQuery("phase", query), first, "stable context reuses query")
live = "ZA"
expect(UI:GetCachedViewQuery("phase", query) ~= first, "live transition invalidates UI query")
BigBiSListData.active_schedule = "replacement"
UI:GetCachedViewQuery("phase", query)
equal(count, 3, "schedule replacement invalidates even at same content phase")
char.selection.phase = "T4"
UI:GetCachedViewQuery("phase", query)
equal(count, 4, "manual tier context cannot reuse another tier's rows")
''', self.fixture())
