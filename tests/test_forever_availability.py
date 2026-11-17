from copy import deepcopy
import json
import subprocess
import unittest
from unittest.mock import patch

from tools import forever, forever_availability as availability, forever_leveling as leveling, forever_sources as sources
from tools import generate_lua
from tools.project import ADDON_DIR, lua_value
from test_forever_leveling import fixture
from test_addon_runtime_lua import find_lua51


def inventory_fixture():
    snapshots, docs = fixture()
    rules, profiles, _, _, reviews = docs
    for item in reviews["items"]:
        snap = snapshots[item["snapshot_url"]]
        snap["item_stats"]["required_level"] = 10
        item["snapshot_digest"] = forever.snapshot_digest(snap)
        refs = [sources.evidence_ref(item["snapshot_url"], snapshots)]
        item["evidence_refs"] = refs
        item["sources"][0]["evidence_refs"] = refs
    document = {"version": availability.INVENTORY_VERSION, "client_build": "1.60.1.70790",
                "source_reviews": [], "decisions": [],
                "target_ranges": [{"slot": "Ring", "level_min": 1, "level_max": 9}]}
    reviews["availability"] = document
    for kind, url in [("client_metadata", "https://wago.tools/db2/ItemSparse/csv?build=1.60.1.70790"),
                      ("ahledger_catalog", "https://ahledger.com/api/catalog?class=armor"),
                      ("wowhead_listing", "https://www.wowhead.com/forever/items/armor/slot:11")]:
        records = [{"item_id": identifier, "name": f"Ring {identifier}", "slot": "Ring", "required_level": 10}
                   for identifier in range(71, 76)]
        snapshots[url] = {"url": url, "flavor": "forever", "page_type": "catalog", "catalog_kind": kind,
                          "client_build": document["client_build"], "records": records,
                          "catalog_coverage": {"slots": ["Ring"], "inventory_types": [11], "level_min": 1,
                              "level_max": 59, "qualities": list(range(8)), "total": 5, "complete": True}}
        document["source_reviews"].append({**profiles["review"], "source_url": url, "kind": kind,
            "record_count": 5, "evidence_refs": [sources.evidence_ref(url, snapshots)]})
    return snapshots, docs


def run_fixture(snapshots, docs, diagnostic=False):
    with patch.object(leveling, "inputs", return_value=docs), patch.object(leveling, "roster", return_value={("Warrior", "Arms")}):
        return leveling.generate(snapshots, diagnostic=diagnostic)


def approve(draft, docs, *, approve_empty=True):
    for row in draft["leveling_audit"]["rows"]:
        if not approve_empty and not row["candidate_item_ids"]:
            continue
        review = {**docs[1]["review"], **{key:row[key] for key in (
            "class", "spec", "slot", "faction", "race_id", "level_min", "level_max", "candidate_digest")},
            "profile_version": docs[1]["version"], "rules_version": docs[0]["version"],
            "item_ids": row["candidate_item_ids"]}
        if not row["candidate_item_ids"]:
            review.update(disposition="no_eligible_item", availability_digest=row["availability"]["availability_digest"],
                          display_reason="Useful rings require level 10 or higher.")
        docs[4]["rankings"].append(review)


class AvailabilityTests(unittest.TestCase):
    def test_current_client_and_hotfix_metadata_establish_equipment_restrictions(self):
        build = "1.60.1.70938"
        old_build = "1.60.1.70888"
        old_url = f"https://wago.tools/db2/ItemSparse/csv?build={old_build}"
        current_url = f"https://wago.tools/db2/ItemSparse/csv?build={build}"
        cache_url = "https://storage.googleapis.com/raidbots-static/wow%2F70938%2FenUS%2FDBCache-example.bin"
        snapshots = {
            old_url: {"page_type": "catalog", "catalog_kind": "client_metadata", "client_build": old_build,
                      "records": [{"item_id": 71, "slot": "Ring", "required_level": 10},
                                  {"item_id": 72, "slot": "Ring", "required_level": 10}]},
            current_url: {"page_type": "catalog", "catalog_kind": "client_metadata", "client_build": build,
                          "records": [{"item_id": 71, "slot": "Ring", "required_level": 1},
                                      {"item_id": 73, "slot": "Ring", "required_level": 10}]},
            cache_url: {"page_type": "catalog", "catalog_kind": "client_hotfix", "client_build": build,
                        "records": [{"item_id": 74, "slot": "Ring", "required_level": 10}]},
        }
        rules = {"review": {"client_build": build}}
        document = {"version": availability.INVENTORY_VERSION, "client_build": build}
        inventory = availability.build_inventory(snapshots, document, rules, forever.evidence_index(snapshots))
        candidates = {row["item_id"]: row for row in inventory["candidates"]}
        self.assertEqual(set(candidates), {71, 72, 73, 74})
        profile = {"class": "Warrior", "spec": "Arms"}
        persona = {"id": 1, "name": "Human", "faction": "Alliance"}
        outcomes = {item_id: availability.automatic_exclusion(row, profile, persona, "Ring", 1, 3, rules)
                    for item_id, row in candidates.items()}
        self.assertEqual(outcomes, {71: None, 72: None, 73: "equip_minimum", 74: "equip_minimum"})
        self.assertEqual(sources.source_provider(cache_url), "raidbots")
        self.assertIsNone(sources.source_provider("https://storage.googleapis.com/other-project/DBCache-example.bin"))

    def test_catalog_off_hand_candidate_keeps_exact_main_hand_tooltip(self):
        catalog_url = "https://ahledger.com/api/catalog?class=weapon"
        item_url = "https://www.wowhead.com/forever/item=10625"
        snapshots = {
            catalog_url: {"url": catalog_url, "flavor": "forever", "page_type": "catalog",
                          "catalog_kind": "ahledger_catalog", "records": [{"item_id": 10625, "slot": "WEAPON"}]},
            item_url: {"url": item_url, "flavor": "forever", "page_type": "item", "item_id": 10625,
                       "item_kind": "equipment", "item_stats": {"slot": "Main Hand", "required_level": 44}},
        }
        inventory = availability.build_inventory(snapshots, {}, {}, forever.evidence_index(snapshots))
        candidate = inventory["candidates"][0]
        self.assertEqual(candidate["slots"], ["Off Hand"])
        profile = {"class": "Rogue", "spec": "Combat"}
        persona = {"id": 1, "name": "Human", "faction": "Alliance"}
        self.assertEqual(availability.automatic_exclusion(candidate, profile, persona, "Off Hand", 1, 4, {}),
                         "equip_minimum")
        self.assertEqual(availability.automatic_exclusion(candidate, profile, persona, "Off Hand", 44, 44, {}),
                         "other_slot")
        candidate["observations"].append({"kind": "client_metadata", "slot": "Off Hand", "required_level": 1})
        self.assertIsNone(availability.automatic_exclusion(candidate, profile, persona, "Off Hand", 1, 4, {}))

    def test_main_hand_client_record_can_resolve_an_unrevealed_off_hand_candidate(self):
        build = "1.60.1.70888"
        client = availability.normalize_client_catalog({
            "Item": "ID,InventoryType,ClassID,SubclassID\n22942,21,2,4\n23056,21,2,4\n",
            "ItemSparse": "ID,RequiredLevel,AllowableClass\n1,1,-1\n",
            "ItemSearchName": "ID,RequiredLevel,AllowableClass\n1,1,-1\n",
        }, build, collected_at="2026-11-12T00:00:00Z")
        client_url = client["url"]
        catalog_url = "https://ahledger.com/api/catalog?class=weapon"
        snapshots = {client_url: client, catalog_url: {
            "url": catalog_url, "flavor": "forever", "page_type": "catalog", "catalog_kind": "ahledger_catalog",
            "records": [{"item_id": 22942, "slot": "WEAPON"}],
        }}
        profile = {"class": "Rogue", "spec": "Combat"}
        persona = {"id": 1, "name": "Human", "faction": "Alliance"}
        document = {"version": availability.INVENTORY_VERSION, "client_build": build}

        def exclusion():
            inventory = availability.build_inventory(snapshots, document, {}, forever.evidence_index(snapshots))
            self.assertEqual([row["item_id"] for row in inventory["candidates"]], [22942])
            return availability.automatic_exclusion(inventory["candidates"][0], profile, persona, "Off Hand", 1, 4, {})

        self.assertEqual(client["records"][0]["slot"], "Main Hand")
        self.assertIsNone(client["records"][0]["required_level"])
        self.assertNotIn(21, availability.COVERAGE_TYPES["Off Hand"])
        self.assertEqual(exclusion(), "other_slot")
        document["client_build"] = "1.60.1.70889"
        self.assertIsNone(exclusion())
        document["client_build"] = build
        item_url = "https://www.wowhead.com/forever/item=22942"
        snapshots[item_url] = {"url": item_url, "flavor": "forever", "page_type": "item", "item_id": 22942,
                               "item_kind": "equipment", "item_stats": {"slot": "One Hand", "required_level": 1}}
        self.assertIsNone(exclusion())

    def test_client_off_hand_weapons_and_held_items_have_different_equipment_rules(self):
        build = "1.60.1.70888"
        client = availability.normalize_client_catalog({
            "Item": ("ID,InventoryType,ClassID,SubclassID\n"
                     "12747,22,2,14\n270429,22,2,9\n16768,23,4,0\n280317,23,2,14\n"),
            "ItemSparse": "ID,RequiredLevel,AllowableClass,Flags_2\n12747,1,-1,0\n270429,1,-1,524288\n",
            "ItemSearchName": "ID,RequiredLevel,AllowableClass\n1,1,-1\n",
        }, build, collected_at="2026-11-12T00:00:00Z")
        snapshots = {client["url"]: client}
        rules = {
            "review": {"client_build": build},
            "class_equipment": {"Rogue": {"weapon_types": ["Dagger"]}},
            "spec_policies": {"Rogue/Combat": {"dual_wield_level": 10}},
        }
        document = {"version": availability.INVENTORY_VERSION, "client_build": build}
        inventory = availability.build_inventory(snapshots, document, rules, forever.evidence_index(snapshots))
        candidates = {row["item_id"]: row for row in inventory["candidates"]}
        profile = {"class": "Rogue", "spec": "Combat"}
        persona = {"id": 1, "name": "Human", "faction": "Alliance"}

        ordinary = candidates[12747]
        self.assertTrue(ordinary["observations"][0]["requires_dual_wield"])
        self.assertEqual(availability.automatic_exclusion(ordinary, profile, persona, "Off Hand", 1, 4, rules),
                         "equipment_rule")
        self.assertIsNone(availability.automatic_exclusion(ordinary, profile, persona, "Off Hand", 10, 10, rules))

        override = candidates[270429]
        self.assertFalse(override["observations"][0]["requires_dual_wield"])
        self.assertEqual(override["observations"][0]["weapon_subtype"], "Warglaive")
        self.assertEqual(availability.automatic_exclusion(override, profile, persona, "Off Hand", 1, 4, rules),
                         "equipment_rule")
        rules["class_equipment"]["Rogue"]["weapon_types"].append("Warglaive")
        self.assertIsNone(availability.automatic_exclusion(override, profile, persona, "Off Hand", 1, 4, rules))
        for identifier in (16768, 280317):
            with self.subTest(item_id=identifier):
                self.assertNotIn("weapon_subtype", candidates[identifier]["observations"][0])
                self.assertIsNone(availability.automatic_exclusion(candidates[identifier], profile, persona,
                                                                    "Off Hand", 1, 4, rules))

    def test_exact_server_equip_requirement_applies_only_to_the_reviewed_build(self):
        url = "https://foreverchanges.pro/item/280454/manaflare-mantle"
        build = "1.60.1.70888"
        html = f"""
          <p class="it-beta">Confirmed in game. Sent by Blizzard's server to players.</p>
          <div class="it-tip it-labelled">
            <div class="it-label">Classic Era 1.15.9.69722</div>
            <div class="it-body"><div class="it-plain">Requires Level 1</div></div>
          </div>
          <div class="it-tip it-labelled">
            <div class="it-label">Forever {build}</div>
            <div class="it-name">Manaflare Mantle</div><span class="it-itemid">item 280454</span>
            <div class="it-body">
              <div class="it-plain"><span>Shoulder</span><span>Cloth</span></div>
              <div class="it-plain">Requires Level 60</div>
            </div>
          </div>
        """
        snap = sources.normalize_foreverchanges_requirement(url, html, collected_at="2026-11-11T00:00:00Z")
        self.assertEqual(snap["records"], [{"item_id": 280454, "name": "Manaflare Mantle", "slot": "Shoulder",
                                            "required_level": 60}])
        self.assertEqual(snap["attribution"][0]["source"], url)
        ring_url = "https://foreverchanges.pro/item/276073/band-of-the-damned"
        ring_html = (html.replace("Manaflare Mantle", "Band of the Damned").replace("280454", "276073")
                     .replace("<span>Shoulder</span><span>Cloth</span>", "Finger")
                     .replace("Requires Level 60", "Requires Level 56"))
        ring = sources.normalize_foreverchanges_requirement(ring_url, ring_html, collected_at="2026-11-12T20:30:00Z")
        self.assertEqual(ring["records"], [{"item_id": 276073, "name": "Band of the Damned", "slot": "Ring",
                                            "required_level": 56}])
        with self.assertRaisesRegex(ValueError, "observed on the Forever server"):
            sources.normalize_foreverchanges_requirement(url, html.replace("Sent by Blizzard's server to players", "Datamined"),
                                                         collected_at="2026-11-11T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "item ID"):
            sources.normalize_foreverchanges_requirement(url.replace("280454", "280455"), html,
                                                         collected_at="2026-11-11T00:00:00Z")

        snapshots = {url: snap}
        candidate = availability.build_inventory(snapshots, {}, {}, forever.evidence_index(snapshots))["candidates"][0]
        profile = {"class": "Warrior", "spec": "Arms"}
        persona = {"id": 1, "name": "Human", "faction": "Alliance"}
        rules = {"review": {"client_build": build}}
        self.assertEqual(availability.automatic_exclusion(candidate, profile, persona, "Shoulder", 1, 14, rules),
                         "equip_minimum")
        self.assertIsNone(availability.automatic_exclusion(candidate, profile, persona, "Shoulder", 1, 14,
                                                           {"review": {"client_build": "1.60.1.70889"}}))
        candidate["observations"].append({"kind": "item", "required_level": 1, "slot": "Shoulder"})
        self.assertIsNone(availability.automatic_exclusion(candidate, profile, persona, "Shoulder", 1, 14, rules))

    def test_complete_inventory_publishes_reviewed_empty_intervals(self):
        snapshots, docs = inventory_fixture()
        draft = run_fixture(snapshots, docs)
        self.assertTrue(draft["leveling_candidate_audit"]["candidates"])
        early = [row for row in draft["leveling_audit"]["rows"] if row["level_max"] < 10]
        self.assertTrue(all(row["availability"]["complete"] and not row["availability"]["unresolved_item_ids"] for row in early))
        self.assertEqual({row["status"] for row in early}, {"pending_empty_slot_review"})
        approve(draft, docs)
        catalog = "https://www.wowhead.com/forever/items/armor/slot:11"
        for review in docs[4]["rankings"]:
            if review.get("disposition") == "no_eligible_item":
                review.update(source_url=catalog, evidence_refs=[sources.evidence_ref(catalog, snapshots)])
        result = run_fixture(snapshots, docs)
        self.assertTrue(result["coverage"]["ok"])
        self.assertEqual(len(result["leveling_availability"]["leveling_availability"]), 2)
        self.assertEqual(result["coverage"]["summary"]["approved_empty_combinations"], 18)
        self.assertEqual({row["status"] for row in result["leveling_audit"]["rows"] if row["level_max"] < 10},
                         {"no_useful_item"})
        self.assertTrue(all(row["level_min"] >= 10 for row in result["leveling_recommendations"]["leveling_recommendations"]))

    def test_approved_gear_covers_levels_without_an_absence_catalog(self):
        snapshots, docs = fixture()
        docs[4]["availability"] = {"require_complete_inventory": True,
                                   "version": availability.INVENTORY_VERSION, "client_build": "1.60.1.70790"}
        approve(run_fixture(snapshots, docs), docs)
        coverage = run_fixture(snapshots, docs)["coverage"]
        self.assertTrue(coverage["ok"])
        self.assertFalse(coverage["summary"]["availability_inventory_complete"])

    def test_unreviewed_availability_reports_the_first_reviewed_gear_level(self):
        snapshots, docs = inventory_fixture()
        docs[4]["availability"]["source_reviews"].clear()
        url = forever.WOWHEAD_ROOT + "item=999"
        snapshots[url] = {"url": url, "flavor": "forever", "page_type": "item", "item_id": 999,
                          "item_stats": {"slot": "Ring", "required_level": 1, "restrictions": {"races": ["Orc"]}}}
        approve(run_fixture(snapshots, docs), docs, approve_empty=False)
        coverage = run_fixture(snapshots, docs)["coverage"]
        self.assertFalse(coverage["ok"])
        self.assertEqual(coverage["summary"]["status_counts"], {"unreviewed_availability": 18})
        self.assertEqual(coverage["summary"]["availability_review_combinations"], 18)
        self.assertEqual(coverage["summary"]["pending_ranking_combinations"], 0)
        self.assertEqual(coverage["summary"]["availability_review_ranges"], [
            {"slot": "Ring", "faction": faction, "status": "unreviewed_availability", "level_min": 1, "level_max": 9,
             "first_recommended_level": 10, "combinations_per_level": 1, "inventory_complete": False,
             "unresolved_candidate_count": count} for faction, count in [("Alliance", 0), ("Horde", 1)]])

    def test_arbitrary_exhaustive_flag_cannot_replace_catalogs(self):
        snapshots, docs = inventory_fixture()
        draft = run_fixture(snapshots, docs)
        approve(draft, docs)
        docs[4]["availability"]["source_reviews"] = []
        url = "https://www.wowhead.com/forever/guide/unsubstantiated-absence"
        snapshots[url] = {"url":url, "flavor":"forever", "page_type":"guide", "exhaustive_eligibility":True,
                          "eligibility_scopes":[{"class":"Warrior","spec":"Arms","faction":"Alliance","race_id":1,
                                                 "slot":"Ring","level_min":1,"level_max":9}]}
        for row in docs[4]["rankings"]:
            row["absence_evidence_refs"] = [sources.evidence_ref(url, snapshots)]
        with self.assertRaisesRegex(ValueError, "exhaustive eligibility"):
            run_fixture(snapshots, docs)

    def test_new_unapproved_candidate_invalidates_empty_slot_approval(self):
        snapshots, docs = inventory_fixture()
        approve(run_fixture(snapshots, docs), docs)
        url = "https://www.wowhead.com/forever/item=999"
        snapshots[url] = {"url": url, "flavor": "forever", "page_type": "item", "item_id": 999,
                          "item_stats": {"id": 999, "slot": "Ring", "required_level": 1, "stats": {"stamina": 1}}}
        with self.assertRaisesRegex(ValueError, "exhaustive eligibility"):
            run_fixture(snapshots, docs)
        report = run_fixture(snapshots, docs, diagnostic=True)["coverage"]
        self.assertFalse(report["ok"])
        self.assertTrue(any(999 in row.get("availability", {}).get("unresolved_item_ids", []) for row in report["rows"]))

    def test_new_excluded_candidate_still_changes_absence_digest(self):
        snapshots, docs = inventory_fixture()
        approve(run_fixture(snapshots, docs), docs)
        url = "https://www.wowhead.com/forever/item=999"
        snapshots[url] = {"url": url, "flavor": "forever", "page_type": "item", "item_id": 999,
                          "item_stats": {"id": 999, "slot": "Ring", "required_level": 50}}
        with self.assertRaisesRegex(ValueError, "Stale empty-slot"):
            run_fixture(snapshots, docs)

    def test_new_acquisition_evidence_invalidates_absence_before_any_gear_approval(self):
        snapshots, docs = inventory_fixture()
        approve(run_fixture(snapshots, docs), docs)
        url="https://www.wowhead.com/forever/item=999"
        snapshots[url]={"url":url,"flavor":"forever","page_type":"item","item_id":999,
                        "item_kind":"quest_starter","item_stats":{"required_level":1}}
        with self.assertRaisesRegex(ValueError,"Stale empty-slot"):
            run_fixture(snapshots,docs)

    def test_partial_or_single_quality_listing_cannot_prove_absence(self):
        snapshots, docs = inventory_fixture()
        url = docs[4]["availability"]["source_reviews"][-1]["source_url"]
        for change in ({"total": 6}, {"truncated": True}, {"qualities": [1]}):
            with self.subTest(change=change):
                current = deepcopy(snapshots)
                current[url]["catalog_coverage"].update(change)
                review = docs[4]["availability"]["source_reviews"][-1]
                old = review["evidence_refs"]
                review["evidence_refs"] = [sources.evidence_ref(url, current)]
                result = run_fixture(current, docs, diagnostic=True)
                self.assertFalse(result["coverage"]["summary"]["availability_inventory_complete"])
                review["evidence_refs"] = old

    def test_restriction_race_bits_above_32_are_exact(self):
        candidate = {"slots": ["Ring"], "observations": [{"kind": "client_metadata", "race_mask": 1 << 32}]}
        profile = {"class": "Warrior", "spec": "Arms"}
        self.assertIsNone(availability.automatic_exclusion(candidate, profile, {"id":95,"name":"Skyborne"}, "Ring",1,9,{}))
        self.assertEqual(availability.automatic_exclusion(candidate, profile, {"id":96,"name":"Skyborne"}, "Ring",1,9,{}),"race_restriction")

    def test_conflicting_equip_levels_remain_unresolved(self):
        candidate = {"slots":["Head"], "observations":[{"kind":"item","required_level":1}, {"kind":"client_metadata","required_level":15}]}
        self.assertIsNone(availability.automatic_exclusion(candidate,{"class":"Warrior","spec":"Arms"},{"id":1,"name":"Human"},"Head",1,9,{}))

    def test_relic_subtype_is_not_rejected_as_generic_relic(self):
        candidate={"slots":["Idol"],"observations":[{"kind":"client_metadata","slot":"Relic","armor_type":"Idol"}]}
        rules={"class_equipment":{"Druid":{"special_slots":["Idol"],"armor_tiers":[{"level":1,"types":["Leather"]}],"weapon_types":[]}},
               "spec_policies":{"Druid/Balance":{}}}
        self.assertIsNone(availability.automatic_exclusion(candidate,{"class":"Druid","spec":"Balance"},{"id":4,"name":"Night Elf"},"Idol",1,9,rules))

    def test_conflicting_class_evidence_cannot_exclude_a_candidate(self):
        candidate={"slots":["Ring"],"observations":[{"kind":"item","restrictions":{"classes":["Warrior"]}},
                                                        {"kind":"client_metadata","class_mask":1<<7}]}
        self.assertIsNone(availability.automatic_exclusion(candidate,{"class":"Warrior","spec":"Arms"},{"id":1,"name":"Human"},"Ring",1,9,{}))

    def test_unrevealed_client_row_does_not_override_a_tooltip_class_requirement(self):
        client = {"kind": "client_metadata", "required_level": None, "class_mask": -1}
        item = {"kind": "item", "restrictions": {"classes": ["Druid"]}}
        candidate = {"slots": ["Shoulder"], "observations": [client, item]}
        profile = {"class": "Warrior", "spec": "Arms"}
        persona = {"id": 1, "name": "Human"}

        self.assertEqual(availability.automatic_exclusion(candidate, profile, persona, "Shoulder", 1, 14, {}),
                         "class_restriction")
        client["required_level"] = 0
        self.assertIsNone(availability.automatic_exclusion(candidate, profile, persona, "Shoulder", 1, 14, {}))

    def test_statless_armor_is_not_a_cosmetic_exclusion(self):
        self.assertTrue(availability.useful_effect({"item_stats":{"armor":2}}))
        self.assertTrue(availability.useful_effect({"description":"Use: Gives a useful effect."}))
        self.assertFalse(availability.useful_effect({"item_stats":{},"description":"A decorative ring."}))
        self.assertTrue(availability.useful_effect({"item_stats":{},"description":"Finger +2,500 Health"}))

    def test_unknown_weapon_proficiency_does_not_bypass_a_verified_dual_wield_gate(self):
        candidate={"slots":["Off Hand"],"observations":[{"kind":"item","slot":"One Hand"}]}
        profile={"class":"Rogue","spec":"Combat"}
        rules={"spec_policies":{"Rogue/Combat":{"dual_wield_level":5}}}
        self.assertEqual(availability.automatic_exclusion(candidate,profile,{"id":1,"name":"Human"},"Off Hand",1,4,rules),"equipment_rule")
        self.assertIsNone(availability.automatic_exclusion(candidate,profile,{"id":1,"name":"Human"},"Off Hand",5,9,rules))
        candidate["observations"].append({"kind":"item","slot":"Off Hand"})
        self.assertIsNone(availability.automatic_exclusion(candidate,profile,{"id":1,"name":"Human"},"Off Hand",1,4,rules))

    def test_profession_caps_use_reviewed_racial_values_and_equipment_requirements(self):
        candidate={"observations":[{"kind":"item","requirements":[{"type":"profession","scope":"equip_or_use",
                    "profession":"Engineering","skill":85}]}]}
        rules=[{"profession":"Engineering","ranks":[{"min_level":1,"max_skill":75},{"min_level":10,"max_skill":150}],
                "skill_bonus_by_race":{"1":0,"7":15}}]
        self.assertEqual(availability.profession_exclusion(candidate,{"id":1},9,rules),"profession_minimum")
        self.assertIsNone(availability.profession_exclusion(candidate,{"id":7},9,rules))
        self.assertIsNone(availability.profession_exclusion(candidate,{"id":95},9,rules))
        self.assertIsNone(availability.profession_exclusion(candidate,{"id":1},10,rules))
        candidate["observations"].append({"kind":"item","requirements":[]})
        self.assertIsNone(availability.profession_exclusion(candidate,{"id":1},9,rules))
        candidate["observations"]=candidate["observations"][:1]
        candidate["observations"][0]["requirements"][0]["scope"]="self_craft"
        self.assertIsNone(availability.profession_exclusion(candidate,{"id":1},9,rules))

    def test_listing_count_and_filter_scope_are_validated(self):
        html = '<p>2 items found</p><script>new Listview({id:"items",data:[{"id":71,"name":"Ring"}]});</script>'
        listing = availability.normalize_item_listing("https://www.wowhead.com/forever/items/armor/slot:11",html,collected_at="now")
        self.assertFalse(listing["catalog_coverage"]["complete"])
        self.assertTrue(listing["catalog_coverage"]["truncated"])
        with self.assertRaisesRegex(ValueError,"Filtered listing"):
            availability.normalize_item_listing("https://www.wowhead.com/forever/items/armor/slot:11/min-req-level:5",html,collected_at="now")
        with self.assertRaisesRegex(ValueError,"actual item listing"):
            availability.normalize_item_listing("https://www.wowhead.com/forever/items/armor/slot:11","<h1>No results</h1>",collected_at="now")

    def test_listing_uses_script_count_and_rejects_capped_or_conflicting_counts(self):
        url = "https://www.wowhead.com/forever/items/armor/slot:11"
        html = ('<script>new Listview({id:"items",note:"1 items found (1 displayed)",'
                'data:[{"id":71,"name":"Ring"}]});</script>')
        coverage = availability.normalize_item_listing(url, html, collected_at="now")["catalog_coverage"]
        self.assertTrue(coverage["complete"])
        capped = html.replace('data:', '_truncated: 1, data:')
        coverage = availability.normalize_item_listing(url, capped, collected_at="now")["catalog_coverage"]
        self.assertTrue(coverage["truncated"])
        self.assertFalse(coverage["complete"])
        conflicting = html + "<p>1 - 1 of 2</p>"
        coverage = availability.normalize_item_listing(url, conflicting, collected_at="now")["catalog_coverage"]
        self.assertFalse(coverage["complete"])
        cap_size = json.dumps([{"id": identifier} for identifier in range(1, 1001)])
        at_cap = f'<p>1–50 of 1,000</p><script>new Listview({{id:"items",data:{cap_size}}});</script>'
        coverage = availability.normalize_item_listing(url, at_cap, collected_at="now")["catalog_coverage"]
        self.assertTrue(coverage["truncated"])
        self.assertFalse(coverage["complete"])

    def test_required_level_listing_cannot_attest_unknown_requirements(self):
        url = "https://www.wowhead.com/forever/items/armor/slot:11/max-req-level:3"
        html = '<p>1 item found</p><script>new Listview({id:"items",data:[{"id":71,"name":"Ring"}]});</script>'
        listing = availability.normalize_item_listing(url, html, collected_at="now")
        self.assertEqual(listing["records"][0]["item_id"], 71)
        self.assertIsNone(listing["records"][0]["required_level"])
        self.assertFalse(listing["catalog_coverage"]["complete"])
        encoded_url = "https://www.wowhead.com/forever/items/armor/slot%3A11/max-req-level%3A3"
        self.assertFalse(availability.normalize_item_listing(encoded_url, html, collected_at="now")["catalog_coverage"]["complete"])
        with self.assertRaisesRegex(ValueError, "Filtered listing"):
            availability.normalize_item_listing(url.replace("/max-req-level:3", "/slot:3"), html, collected_at="now")

        snapshots, docs = inventory_fixture()
        review = docs[4]["availability"]["source_reviews"][-1]
        older = snapshots.pop(review["source_url"])
        snapshots[url] = {**older, "url": url}
        review.update(source_url=url, evidence_refs=[sources.evidence_ref(url, snapshots)])
        inventory = availability.build_inventory(snapshots, docs[4]["availability"], docs[0], forever.evidence_index(snapshots))
        self.assertFalse(availability.complete_for(inventory, "Ring", 1, 3))
        self.assertEqual(inventory["source_issues"][0]["source_url"], url)

    def test_wrong_build_and_stale_catalog_reviews_cannot_certify_inventory(self):
        snapshots, docs = inventory_fixture()
        url = docs[4]["availability"]["source_reviews"][0]["source_url"]
        for change in ({"client_build":"1.60.1.70450"}, {"records":[]}):
            with self.subTest(change=change):
                current = deepcopy(snapshots)
                current[url].update(change)
                inventory = availability.build_inventory(current, docs[4]["availability"], docs[0], forever.evidence_index(current))
                self.assertTrue(inventory["source_issues"])
                self.assertFalse(availability.complete_for(inventory,"Ring",1,9))

    def test_unused_stale_candidate_approval_still_rejects_import_but_reports_remain_readable(self):
        snapshots, docs = inventory_fixture()
        docs[4]["availability"]["decisions"] = [{**docs[1]["review"],"item_id":71,
            "candidate_digest":"old","exclusion":"acquisition_minimum","minimum_level":10,"all_routes_reviewed":True}]
        with self.assertRaisesRegex(ValueError,"Stale availability"):
            run_fixture(snapshots,docs)
        report=run_fixture(snapshots,docs,diagnostic=True)["coverage"]
        self.assertFalse(report["ok"])
        self.assertTrue(any(row.get("kind")=="availability" for row in report["review_issues"]))

    def test_acquisition_exclusions_require_real_routes_and_apply_their_actual_gates(self):
        snapshots,docs=inventory_fixture()
        url="https://www.wowhead.com/forever/item=999"
        snapshots[url]={"url":url,"flavor":"forever","page_type":"item","item_id":999,
                        "item_stats":{"slot":"Ring","required_level":1}}
        records=forever.evidence_index(snapshots)
        document=docs[4]["availability"]
        inventory=availability.build_inventory(snapshots,document,docs[0],records)
        candidate=next(row for row in inventory["candidates"] if row["item_id"]==999)
        decision={**docs[1]["review"],"item_id":999,"candidate_digest":candidate["candidate_digest"],
                  "exclusion":"acquisition_minimum","minimum_level":20,"all_routes_reviewed":True,
                  "acquisition_evidence_digest":inventory["acquisition_evidence_digest"]}
        with self.assertRaisesRegex(ValueError,"explicit reviewed dependency routes"):
            availability.validate_exclusion_routes(decision,records,snapshots)
        decision["routes"]=[deepcopy(docs[4]["items"][0]["sources"][0])]
        document["decisions"]=[decision]
        def check():
            return availability.review_scope(inventory,document,{"class":"Warrior","spec":"Arms"},docs[0]["races"][0],"Ring",1,9,docs[0],records,snapshots)
        self.assertIn(999,check()["unresolved_item_ids"])
        self.assertTrue(check()["review_issues"])
        decision["routes"][0]["eligibility"]["min_level"]=20
        self.assertNotIn(999,check()["unresolved_item_ids"])

    def test_item_acquisition_exclusion_tracks_new_routes_for_the_same_item(self):
        snapshots, docs = inventory_fixture()
        document = docs[4]["availability"]
        item_url = "https://www.wowhead.com/forever/item=999"
        snapshots[item_url] = {"url": item_url, "page_type": "item", "item_id": 999,
                               "item_stats": {"slot": "Ring", "required_level": 1}}

        def add_quest(quest_id, item_id):
            url = f"https://www.wowhead.com/forever/quest={quest_id}"
            snapshots[url] = {"url": url, "page_type": "quest", "relationships": [
                {"relation": "rewards", "subject_type": "quest", "subject_id": quest_id,
                 "object_type": "item", "object_id": item_id, "source_url": url}]}

        add_quest(901, 999)
        records = forever.evidence_index(snapshots)
        initial = availability.build_inventory(snapshots, document, docs[0], records)
        candidate = next(row for row in initial["candidates"] if row["item_id"] == 999)
        route = deepcopy(docs[4]["items"][0]["sources"][0])
        route["quest_id"] = 901
        route["eligibility"]["min_level"] = 20
        quest_ref = sources.evidence_ref("https://www.wowhead.com/forever/quest=901", snapshots)
        route["evidence_refs"].append(quest_ref)
        document["decisions"] = [{**docs[1]["review"], "item_id": 999, "exclusion": "acquisition_minimum",
                                 "minimum_level": 20, "all_routes_reviewed": True, "routes": [route],
                                 "candidate_digest": candidate["candidate_digest"],
                                 "item_acquisition_digest": availability.item_acquisition_digests(snapshots, records)[999]}]

        add_quest(902, 71)
        records = forever.evidence_index(snapshots)
        refreshed = availability.build_inventory(snapshots, document, docs[0], records)
        self.assertNotEqual(initial["inventory_digest"], refreshed["inventory_digest"])
        self.assertFalse(refreshed["decision_issues"])
        scope = {"class": "Warrior", "spec": "Arms"}
        persona = docs[0]["races"][0]
        result = availability.review_scope(refreshed, document, scope, persona, "Ring", 1, 9, docs[0], records, snapshots)
        self.assertNotIn(999, result["unresolved_item_ids"])

        add_quest(903, 999)
        records = forever.evidence_index(snapshots)
        changed = availability.build_inventory(snapshots, document, docs[0], records)
        self.assertEqual(changed["decision_issues"], [{"item_id": 999, "reason": "Stale acquisition availability decision"}])
        result = availability.review_scope(changed, document, scope, persona, "Ring", 1, 9, docs[0], records, snapshots)
        self.assertIn(999, result["unresolved_item_ids"])

    def test_decision_for_another_spec_or_unreferenced_source_does_not_exclude(self):
        snapshots, docs = inventory_fixture()
        document = docs[4]["availability"]
        identifier = 999
        url = "https://www.wowhead.com/forever/item=999"
        snapshots[url] = {"url":url,"flavor":"forever","page_type":"item","item_id":identifier,
                          "item_stats":{"slot":"Ring","parse_confidence":"tooltip_endpoint"},"description":"A purely decorative ring."}
        records = forever.evidence_index(snapshots)
        inventory = availability.build_inventory(snapshots,document,docs[0],records)
        candidate = next(row for row in inventory["candidates"] if row["item_id"]==identifier)
        decision = {**docs[1]["review"],"source_url":url,"item_id":identifier,"exclusion":"not_useful",
                    "candidate_digest":candidate["candidate_digest"],"scope":{"spec":"Protection"},
                    "evidence_refs":[sources.evidence_ref(url,snapshots)]}
        document["decisions"]=[decision]
        def check():
            return availability.review_scope(inventory,document,{"class":"Warrior","spec":"Arms"},docs[0]["races"][0],"Ring",1,9,docs[0],records,snapshots)
        self.assertIn(identifier,check()["unresolved_item_ids"])
        decision["scope"]={}
        self.assertNotIn(identifier,check()["unresolved_item_ids"])
        decision["evidence_refs"]=docs[1]["review"]["evidence_refs"]
        self.assertTrue(check()["review_issues"])
        self.assertIn(identifier,check()["unresolved_item_ids"])

    def test_unavailable_evidence_is_bound_to_its_faction_and_routes(self):
        snapshots, docs = inventory_fixture()
        rules, document = docs[0], docs[4]["availability"]
        item_url = "https://www.wowhead.com/forever/item=999"
        snapshots[item_url] = {"url": item_url, "page_type": "item", "item_id": 999,
                               "item_stats": {"slot": "Ring", "required_level": 1}}
        evidence_url = item_url + "#availability"
        snapshots[evidence_url] = {"url": evidence_url, "page_type": "reference",
                                   "unavailable_item_ids": [999], "unavailable_scope": {"faction": "Horde"}}
        records = forever.evidence_index(snapshots)
        inventory = availability.build_inventory(snapshots, document, rules, records)
        candidate = next(row for row in inventory["candidates"] if row["item_id"] == 999)
        document["decisions"] = [{**docs[1]["review"], "source_url": evidence_url, "item_id": 999,
                                  "exclusion": "unavailable", "candidate_digest": candidate["candidate_digest"],
                                  "item_acquisition_digest": availability.EMPTY_SUPPORT_DIGEST,
                                  "evidence_refs": [sources.evidence_ref(evidence_url, snapshots)]}]
        profile = {"class": "Warrior", "spec": "Arms"}
        alliance = {"id": 1, "name": "Human", "faction": "Alliance"}
        horde = {"id": 2, "name": "Orc", "faction": "Horde"}
        for persona, available in ((alliance, True), (horde, False)):
            with self.subTest(faction=persona["faction"]):
                result = availability.review_scope(inventory, document, profile, persona, "Ring", 1, 3,
                                                   rules, records, snapshots)
                self.assertEqual(999 in result["unresolved_item_ids"], available)

        quest_url = "https://www.wowhead.com/forever/quest=901"
        snapshots[quest_url] = {"url": quest_url, "page_type": "quest", "relationships": [
            {"relation": "rewards", "subject_type": "quest", "subject_id": 901,
             "object_type": "item", "object_id": 999, "source_url": quest_url}]}
        updated = availability.build_inventory(snapshots, document, rules, forever.evidence_index(snapshots))
        self.assertEqual(updated["decision_issues"], [{"item_id": 999, "reason": "Stale acquisition availability decision"}])

    def test_non_gearing_effect_exclusion_requires_exact_current_effect_evidence(self):
        snapshots, docs = inventory_fixture()
        rules, document = docs[0], docs[4]["availability"]
        item_url = "https://www.wowhead.com/forever/item=999"
        effect_url = "https://wago.tools/db2/SpellEffect/csv?build=1.60.1.70790#/rows/1"
        effect = "Use: Show a shower of rose petals."
        item = {"url": item_url, "page_type": "item", "item_kind": "equipment", "item_id": 999,
                "description": f"Bouquet Held In Off-hand {effect}",
                "item_stats": {"slot": "Off Hand", "parse_confidence": "tooltip_endpoint", "use_effects": [effect]},
                "linked_entities": [{"type": "spell", "id": 33}]}
        evidence = {"url": effect_url, "page_type": "reference", "client_build": document["client_build"],
                    "reviewed_item_effects": [{"item_id": 999, "reviewed_spell_ids": [33], "tooltip_effects": [effect],
                                               "gearing_benefit": False, "finding": "The spell only displays rose petals."}]}
        snapshots.update({item_url: item, effect_url: evidence})
        profile = {"class": "Warrior", "spec": "Arms"}
        persona = docs[0]["races"][0]

        def review():
            records = forever.evidence_index(snapshots)
            inventory = availability.build_inventory(snapshots, document, rules, records)
            candidate = next(row for row in inventory["candidates"] if row["item_id"] == 999)
            document["decisions"] = [{**docs[1]["review"], "source_url": item_url, "item_id": 999,
                "exclusion": "non_gearing_effect", "candidate_digest": candidate["candidate_digest"],
                "evidence_refs": [sources.evidence_ref(url, snapshots) for url in (item_url, effect_url)]}]
            inventory = availability.build_inventory(snapshots, document, rules, records)
            result = availability.review_scope(inventory, document, profile, persona, "Off Hand", 1, 4, rules,
                                               records, snapshots)
            document["decisions"] = []
            return inventory["decision_issues"], result["unresolved_item_ids"]

        self.assertEqual(review(), ([], []))
        new_url = item_url + "/bouquet"
        snapshots[new_url] = {**deepcopy(item), "url": new_url}
        snapshots[new_url]["item_stats"]["use_effects"].append("Use: Restore health.")
        issues, unresolved = review()
        self.assertIn("unreviewed effect", issues[0]["reason"])
        self.assertEqual(unresolved, [999])
        snapshots.pop(new_url)
        evidence["client_build"] = "1.60.1.70789"
        issues, unresolved = review()
        self.assertIn("current review", issues[0]["reason"])
        self.assertEqual(unresolved, [999])

    def test_hidden_effect_needs_observation_and_spell_review(self):
        snapshots, docs = inventory_fixture()
        rules, document = docs[0], docs[4]["availability"]
        item_url = "https://www.wowhead.com/forever/item=999"
        observation_url = "https://www.wowhead.com/forever/guide/fixture-secret"
        effect_url = "https://wago.tools/db2/SpellEffect/csv?build=1.60.1.70790#/items/999"
        snapshots[observation_url] = {"url": observation_url, "page_type": "reference",
                                     "reviewed_page_facts": {"item_id": 999, "reveals_quest_npcs": True}}
        item = {"url": item_url, "page_type": "item", "item_kind": "equipment", "item_id": 999,
                "description": "Secret Ring Item Level 1 Finger",
                "item_stats": {"slot": "Ring", "parse_confidence": "tooltip_endpoint"},
                "observed_item_spells": {"spell_ids": [33], "evidence_refs": [sources.evidence_ref(observation_url, snapshots)]}}
        effect = {"url": effect_url, "page_type": "reference", "client_build": document["client_build"],
                  "reviewed_item_effects": [{"item_id": 999, "reviewed_spell_ids": [33], "tooltip_effects": [],
                                             "gearing_benefit": False, "finding": "Reveals a quest NPC."}]}
        snapshots.update({item_url: item, effect_url: effect})
        self.assertTrue(availability.useful_effect(item))
        records = forever.evidence_index(snapshots)
        inventory = availability.build_inventory(snapshots, document, rules, records)
        candidate = next(row for row in inventory["candidates"] if row["item_id"] == 999)
        document["decisions"] = [{**docs[1]["review"], "source_url": item_url, "item_id": 999,
            "exclusion": "non_gearing_effect", "candidate_digest": candidate["candidate_digest"],
            "evidence_refs": [sources.evidence_ref(url, snapshots) for url in (item_url, effect_url, observation_url)]}]
        inventory = availability.build_inventory(snapshots, document, rules, records)
        result = availability.review_scope(inventory, document, {"class": "Warrior", "spec": "Arms"},
                                           rules["races"][0], "Ring", 1, 3, rules, records, snapshots)
        self.assertEqual(inventory["decision_issues"], [])
        self.assertEqual(result["unresolved_item_ids"], [])

        document["decisions"][0]["evidence_refs"].pop()
        inventory = availability.build_inventory(snapshots, document, rules, records)
        self.assertIn("Stale, missing, or duplicate Forever evidence", inventory["decision_issues"][0]["reason"])

    def test_captured_stat_suffix_blocks_a_cosmetic_exclusion(self):
        snapshots, docs = inventory_fixture()
        rules, document = docs[0], docs[4]["availability"]
        url = "https://www.wowhead.com/forever/item=999"
        snapshots[url] = {"url": url, "page_type": "item", "item_id": 999,
                          "item_stats": {"slot": "Ring", "parse_confidence": "tooltip_endpoint"},
                          "description": "Restored Ring Item Level 1 Finger"}
        records = forever.evidence_index(snapshots)
        inventory = availability.build_inventory(snapshots, document, rules, records)
        base = next(row for row in inventory["candidates"] if row["item_id"] == 999)
        decision = {**docs[1]["review"], "source_url": url, "item_id": 999,
                    "exclusion": "not_useful", "candidate_digest": base["candidate_digest"],
                    "evidence_refs": [sources.evidence_ref(url, snapshots)]}
        document["decisions"] = [decision]

        variant_url = url + "?bonus=12721"
        snapshots[variant_url] = {"url": variant_url, "page_type": "reference",
                                  "confidence": "variant_tooltip_endpoint",
                                  "variant_facts": {"item_id": 999, "slot": "Ring", "bonus_id": 12721,
                                                    "suffix": "of the Monkey", "stats": {"agility": 1, "stamina": 1}}}
        records = forever.evidence_index(snapshots)
        inventory = availability.build_inventory(snapshots, document, rules, records)
        self.assertEqual(inventory["decision_issues"][0]["reason"], "Stale availability candidate decision")
        self.assertEqual(inventory["useful_variant_ids"], [999])

        updated = next(row for row in inventory["candidates"] if row["item_id"] == 999)
        decision["candidate_digest"] = updated["candidate_digest"]
        inventory = availability.build_inventory(snapshots, document, rules, records)
        self.assertEqual(inventory["decision_issues"][0]["reason"], "A captured variant has gameplay stats or effects")
        scope = availability.review_scope(inventory, document, {"class": "Warrior", "spec": "Arms"},
                                          rules["races"][0], "Ring", 1, 9, rules, records, snapshots,
                                          excluded_items={999: {"snapshot_url": url}})
        self.assertIn(999, scope["unresolved_item_ids"])

    def test_client_union_preserves_unknowns_and_exact_search_race_masks(self):
        tables={"Item":"ID,InventoryType,ClassID,SubclassID\n1,1,4,1\n2,11,4,0\n3,3,4,1\n",
                "ItemSparse":"ID,RequiredLevel,AllowableClass\n1,0,-1\n",
                "ItemSearchName":"ID,RequiredLevel,AllowableClass,AllowableRaces_0,AllowableRaces_1\n2,40,-1,0,2\n"}
        catalog=availability.normalize_client_catalog(tables,"1.60.1.70790",collected_at="fixture")
        self.assertEqual([r["item_id"] for r in catalog["records"]],[1,2,3])
        self.assertEqual(catalog["records"][0]["required_level"],0)
        self.assertEqual(catalog["records"][0]["class_mask"],-1)
        self.assertEqual(catalog["records"][1]["required_level"],40)
        self.assertEqual(catalog["records"][1]["race_mask"],1<<33)
        self.assertIsNone(catalog["records"][2]["required_level"])
        self.assertNotIn("class_mask",catalog["records"][2])
        tables["ItemSparse"] += "1,10,-1\n"
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            availability.normalize_client_catalog(tables,"1.60.1.70790",collected_at="fixture")

    def test_quest_starter_gate_cannot_be_replaced_by_old_guide_minimum(self):
        snapshots,docs=fixture()
        url="https://www.wowhead.com/forever/item=10441"
        snapshots[url]={"url":url,"page_type":"item","item_id":10441,"item_kind":"quest_starter",
                        "item_stats":{"required_level":15},"linked_entities":[{"type":"quest","id":6981}]}
        route=docs[4]["items"][0]["sources"][0]
        route.update(quest_id=6981)
        route["evidence_refs"].append(sources.evidence_ref(url,snapshots))
        route["eligibility"]["min_level"]=10
        with self.assertRaisesRegex(ValueError,"quest starter's required level"):
            run_fixture(snapshots,docs)
        route["eligibility"]["min_level"]=15
        result=run_fixture(snapshots,docs)
        self.assertTrue(all(71 not in row["candidate_item_ids"] for row in result["leveling_audit"]["rows"] if row["level_max"]<15))
        self.assertTrue(any(71 in row["candidate_item_ids"] for row in result["leveling_audit"]["rows"] if row["level_min"]>=15))

    def test_starter_without_tooltip_level_requires_matching_bound_client_gate(self):
        snapshots, _ = fixture()
        url = "https://www.wowhead.com/forever/item=259893"
        client_url = "https://wago.tools/db2/ItemSparse/csv?build=1.60.1.70888#corpsefeeder-starter"
        linked_quest = {"type": "quest", "id": 93574}
        snapshots[url] = {"url": url, "page_type": "item", "item_id": 259893, "item_kind": "quest_starter",
                          "item_stats": {}, "linked_entities": [linked_quest]}
        route = {"type": "quest", "quest_id": 93574, "eligibility": {"min_level": 35},
                 "evidence_refs": [sources.evidence_ref(url, snapshots)]}
        with self.assertRaisesRegex(ValueError, "unambiguous current item"):
            leveling.validate_starter_gates(route, snapshots)

        gate = {**snapshots[url], "url": client_url, "page_type": "reference", "item_stats": {"required_level": 1}}
        snapshots[client_url] = gate
        with self.assertRaisesRegex(ValueError, "must bind the starter item evidence"):
            leveling.validate_starter_gates(route, snapshots)
        route["evidence_refs"].append(sources.evidence_ref(client_url, snapshots))
        leveling.validate_starter_gates(route, snapshots)

        gate["linked_entities"] = [{"type": "quest", "id": 99999}]
        with self.assertRaisesRegex(ValueError, "unambiguous current item"):
            leveling.validate_starter_gates(route, snapshots)
        gate["linked_entities"] = [linked_quest]
        snapshots[url]["item_stats"]["required_level"] = 36
        with self.assertRaisesRegex(ValueError, "unambiguous current item"):
            leveling.validate_starter_gates(route, snapshots)

    def test_filtered_provider_pages_preserve_scope_and_reject_changing_snapshots(self):
        url="https://everloot.app/api/corpus/public?kinds=quest&limit=1"
        pages=[{"records":[],"offset":0,"limit":1,"total":0,"next":None,"dataAsOf":"a","kinds":["quest"]}]
        normalized=sources.collect_everloot(url,lambda _:pages[0],collected_at="fixture")
        self.assertEqual(normalized["collection_scope"]["kinds"],"quest")
        self.assertEqual(len(normalized["page_digests"]),1)
        pages[0].update(total=1,next=url+"&offset=1")
        pages.append({**pages[0],"offset":0,"total":0,"next":None,"dataAsOf":"b"})
        with self.assertRaisesRegex(ValueError,"snapshot changed"):
            sources.normalize_everloot(url,pages,collected_at="fixture")
        with self.assertRaisesRegex(ValueError,"pagination URL"):
            sources.collect_everloot(url,lambda _:{"records":[],"next":"https://everloot.app/api/corpus/public?limit=1"},collected_at="fixture")
        with self.assertRaisesRegex(RuntimeError,"429.*Retry-After"):
            sources.collect_everloot(url,unittest.mock.Mock(side_effect=RuntimeError("429 Retry-After: 60")),collected_at="fixture")

    def test_generated_empty_proof_reaches_runtime_and_level14_human_gear(self):
        snapshots,docs=inventory_fixture()
        approve(run_fixture(snapshots,docs),docs)
        result=run_fixture(snapshots,docs)
        lua=find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        payload={"format":2,"meta":{"flavor":"forever","supports_leveling":True},
                 "classes":[{"name":"Warrior","specs":["Arms"]}],"phases":[],
                 "schemas":{**generate_lua.SCHEMAS,"leveling_availability":generate_lua.LEVELING_AVAILABILITY_SCHEMA,
                            "leveling_recommendation":generate_lua.LEVELING_RECOMMENDATION_SCHEMA+["faction","race_id","variant_name","random_suffix_id"]},
                 "leveling_availability_rules":{key:docs[0][key] for key in ("common_slots","races","spec_policies")},
                 "leveling_availability":generate_lua.compact_list(result["leveling_availability"]["leveling_availability"],"leveling_availability"),
                 "leveling_recommendations":generate_lua.compact_list(result["leveling_recommendations"]["leveling_recommendations"],"leveling_recommendation")}
        script="dofile('tests/lua_ui_harness.lua')\nBigBiSListData="+lua_value(payload)+r'''
UnitRace=function() return 'Human','Human',1 end
UnitFactionGroup=function() return 'Alliance' end
for _,file in ipairs({'Config.lua','DataIndex.lua'}) do assert(loadfile(file))('BigBiSList') end
local a=BigBiSList
assert(a:GetLevelingSlotStatus('Warrior','Arms',9,'Ring',{}).state=='no_useful_item')
assert(a:GetLevelingSlotStatus('Warrior','Arms',14,'Ring',{}).state=='recommended')
assert(a:GetLevelingSlotStatus('Warrior','Arms',14,'Ring',{race='Orc',faction='Alliance'}).state=='unreviewed')
BigBiSListData.meta.flavor='anniversary'; a.isForever=false
assert(a:GetLevelingSlotStatus('Warrior','Arms',9,'Ring',{}).state=='not_applicable')
'''
        process=subprocess.run([lua,"-"],input=script,text=True,capture_output=True,cwd=ADDON_DIR,timeout=30)
        self.assertEqual(process.returncode,0,process.stdout+process.stderr)

    def test_runtime_reports_reviewed_empty_slots_and_preserves_gear_queries(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        script = r'''
local H=dofile('tests/lua_ui_harness.lua')
UnitRace=function() return 'Human','Human',1 end
UnitFactionGroup=function() return 'Alliance' end
UnitLevel=function() return 5 end
BigBiSListData={format=2,meta={flavor='forever',supports_leveling=true},classes={{name='Warrior',specs={'Arms'}}},phases={{key='PR',name='Pre-Raid'}},
 schemas={leveling_availability={'class','spec','faction','race_id','slot','level_min','level_max','state','reason'}},
 leveling_availability_rules={common_slots={'Ring'},spec_policies={['Warrior/Arms']={slots={}}},races={
 {id=1,name='Human',faction='Alliance',classes={'Warrior'}},{id=2,name='Orc',faction='Horde',classes={'Warrior'}}}},
 leveling_availability={{'Warrior','Arms','Alliance',1,'Ring',1,9,'no_useful_item','Useful rings require level 10 or higher.'}}}
for _,file in ipairs({'Config.lua','DataIndex.lua','Widgets.lua','UI.lua'}) do assert(loadfile(file))('BigBiSList') end
local a=BigBiSList
assert(a:GetLevelingSlotStatus('Warrior','Arms',5,'Ring',{}).state=='no_useful_item')
assert(a:GetLevelingSlotStatus('Warrior','Arms',5,'Ring',{race='Orc',faction='Horde'}).state=='unreviewed')
assert(a:GetLevelingSlotStatus('Warrior','Arms',5,'Ring',{race='Human',faction='Horde'}).state=='unreviewed')
assert(a:GetLevelingSlotStatus('Warrior','Arms',5,'Ring',{race='Human',faction='Neutral'}).state=='unreviewed')
assert(a:GetLevelingSlotStatus('Warrior','Arms',5,'Trinket',{}).state=='not_applicable')
assert(a:GetLevelingSlotStatus('Warrior','Arms',60,'Ring',{}).state=='not_applicable')
assert(#a:GetLevelingRows('Warrior','Arms',5,{})==0)
local ui=a.UI
ui.GetSelection=function() return {class='Warrior',spec='Arms'} end
ui.GetCachedViewQuery=function(_,_,fn) return fn() end
ui.GetViewState=function() return {} end
ui.currentFilterPayload={}
local message
ui.RenderEmpty=function(_,value) message=value end
ui:RenderLevelingTab()
assert(message and message:find('Useful rings require level 10',1,true),'reviewed explanation was lost in the Leveling UI')
assert(#H.errors==0,table.concat(H.errors,'\n'))
'''
        result = subprocess.run([lua,"-"],input=script,text=True,capture_output=True,cwd=ADDON_DIR,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == "__main__":
    unittest.main()
