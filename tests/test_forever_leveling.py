from copy import deepcopy
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import forever, forever_leveling as leveling, forever_sources as sources, generate_lua, scrape_wowhead as scraper
from tools.recommend_leveling import recommendation_rows_for_items, select_recommendations, effective_stats, racial_score_bonus, rules_allow_equipment
from tools.project import ADDON_DIR, dataset_json
from test_addon_runtime_lua import find_lua51


def fixture():
    guide_url = forever.WOWHEAD_ROOT + "guide/leveling-fixture"
    snapshots = {guide_url: {"url": guide_url, "flavor": "forever", "page_type": "guide", "tables": []}}
    review = {"reviewer": "fixture", "reviewed_at": "2026-11-05", "client_build": "1.60.1.70790",
              "reason": "Fixture review", "source_url": guide_url,
              "evidence_refs": [sources.evidence_ref(guide_url, snapshots)]}
    rules = {"flavor": "forever", "version": "fixture-1", "max_level": 59, "status": "reviewed", "review": review,
             "level_bands": [["1-19", 1, 19], ["20-39", 20, 39], ["40-59", 40, 59]], "common_slots": ["Ring"],
             "class_equipment": {"Warrior": {"armor_tiers": [{"level": 1, "types": ["Mail"]}], "weapon_types": ["Sword"]}},
             "spec_policies": {"Warrior/Arms": {"slots": [], "weapon_style": "any"}},
             "races": [{"id": 1, "name": "Human", "faction": "Alliance", "classes": ["Warrior"]},
                       {"id": 2, "name": "Orc", "faction": "Horde", "classes": ["Warrior"]}]}
    profiles = {"version": "fixture-1", "status": "reviewed", "review": review, "runtime_contexts": ["best_overall"],
                "spec_roles": {"Warrior/Arms": "physical_dps"}, "role_defaults": {"physical_dps": {"stamina": 1}}, "profiles": []}
    racials = {"status": "reviewed", "review": review, "racial_modifiers": []}
    reviews = {"items": [], "rankings": []}
    for identifier, side, stamina in [(71, "Both", 1), (72, "Alliance", 2), (73, "Horde", 50), (74, "Horde", 49), (75, "Horde", 48)]:
        url = forever.WOWHEAD_ROOT + f"item={identifier}"
        snapshot = {"url": url, "flavor": "forever", "page_type": "item", "name": f"Ring {identifier}", "item_id": identifier,
                    "item_stats": {"id": identifier, "slot": "Ring", "required_level": 1, "item_level": 1,
                                   "parse_confidence": "tooltip_endpoint", "stats": {"stamina": stamina}}}
        snapshots[url] = snapshot
        support = {**review, "source_url": url, "evidence_refs": [sources.evidence_ref(url, snapshots)]}
        route = {**support, "type": "quest", "quest_id": identifier, "entity_name": "Fixture quest", "side": side,
                 "eligibility": {"min_level": 1}}
        reviews["items"].append({**support, "type": "verify_item", "item_id": identifier, "snapshot_url": url,
                                 "snapshot_digest": forever.snapshot_digest(snapshot), "sources": [route]})
    return snapshots, (rules, profiles, racials, {"item_variants": []}, reviews)


class ForeverLevelingTests(unittest.TestCase):
    def test_reviewed_vanity_exclusions_preserve_facts_and_use_real_alternatives(self):
        snapshots,docs=fixture()
        review=next(r for r in docs[4]['items'] if r['item_id']==72)
        review.update(recommendation_excluded=True,exclusion_reason='Fixture cosmetic ring supplies no combat benefit.')
        draft=self.run_fixture(snapshots,docs)
        self.assertIn(72,draft['items'])
        self.assertTrue(all(72 not in r['candidate_item_ids'] for r in draft['leveling_audit']['rows']))
        self.assertTrue(any(71 in r['candidate_item_ids'] for r in draft['leveling_audit']['rows']))
        review.pop('exclusion_reason')
        with self.assertRaisesRegex(ValueError,'explicit reviewed reason'):
            self.run_fixture(snapshots,docs)

    def test_unique_equipped_pair_is_filtered_before_offhand_rank_truncation(self):
        snapshots,docs=fixture()
        docs[0]['common_slots']=[]
        docs[0]['spec_policies']['Warrior/Arms']={'slots':['Main Hand','Off Hand'],'weapon_style':'dual_wield','dual_wield_level':1}
        for review in docs[4]['items']:
            snap=snapshots[review['snapshot_url']]
            snap['item_stats'].update(slot='One Hand',weapon_subtype='Sword')
            if review['item_id'] in [72,73]:snap['description']='Fixture weapon Item Level 10 Binds when picked up Unique-Equipped One-Hand Sword'
            review['snapshot_digest']=forever.snapshot_digest(snap)
            refs=[sources.evidence_ref(review['snapshot_url'],snapshots)]
            review['evidence_refs']=refs;review['sources'][0]['evidence_refs']=refs
        draft=self.run_fixture(snapshots,docs)
        for row in draft['leveling_audit']['rows']:
            if row['slot']=='Off Hand' and row['faction']=='Horde':
                self.assertEqual(row['paired_main_hand_item_id'],73)
                self.assertEqual([r['item_id'] for r in row['candidate_choices']],[74,75,71])

    def test_offhand_review_tracks_mainhand_only_facts_and_preferred_identity(self):
        snapshots,docs=fixture()
        docs[0]['common_slots']=[]
        docs[0]['spec_policies']['Warrior/Arms']={'slots':['Main Hand','Off Hand'],'weapon_style':'dual_wield','dual_wield_level':1}
        for review in docs[4]['items']:
            snap=snapshots[review['snapshot_url']]
            snap['item_stats'].update(slot='Main Hand' if review['item_id'] in [72,73] else 'One Hand',weapon_subtype='Sword')
            review['snapshot_digest']=forever.snapshot_digest(snap)
            refs=[sources.evidence_ref(review['snapshot_url'],snapshots)]
            review['evidence_refs']=refs
            review['sources'][0]['evidence_refs']=refs
        draft=self.run_fixture(snapshots,docs)
        for row in draft['leveling_audit']['rows']:
            review={**docs[1]['review'],**{k:row[k] for k in ['class','spec','slot','faction','race_id','level_min','level_max','candidate_digest']},
                    'choices':row['candidate_choices'],'profile_version':docs[1]['version'],'rules_version':docs[0]['version']}
            if row.get('paired_candidate_digest'):
                main=next(r for r in draft['leveling_audit']['rows'] if r['slot']=='Main Hand' and r['race_id']==row['race_id'] and r['level_min']<=row['level_min']<=r['level_max'])
                review.update(paired_main_hand_digest=row['paired_candidate_digest'],paired_main_hand_item_id=main['candidate_choices'][0]['item_id'])
            docs[4]['rankings'].append(review)
        self.assertTrue(self.run_fixture(snapshots,docs)['coverage']['ok'])
        url=forever.WOWHEAD_ROOT+'item=72'
        snapshots[url]['item_stats']['stats']['stamina']=20
        item_review=next(r for r in docs[4]['items'] if r['item_id']==72)
        item_review['snapshot_digest']=forever.snapshot_digest(snapshots[url])
        refs=[sources.evidence_ref(url,snapshots)]
        item_review['evidence_refs']=refs;item_review['sources'][0]['evidence_refs']=refs
        report=self.run_fixture(snapshots,docs,diagnostic=True)
        self.assertTrue(any(r.get('slot')=='Off Hand' and r['reason']=='Stale leveling ranking approval' for r in report['coverage']['review_issues']))
        # Changing an approved main-hand preference also changes the reviewed pair,
        # even when its obtainable candidate set is unchanged.
        for review in docs[4]['rankings']:
            if review['slot']=='Main Hand' and review['faction']=='Horde':review['choices'].reverse()
        report=self.run_fixture(snapshots,docs,diagnostic=True)
        self.assertTrue(any(r['reason']=='Stale paired main-hand approval' for r in report['coverage']['review_issues']))
        for review in docs[4]['rankings']:
            if review['slot']=='Main Hand' and review['faction']=='Horde':review['choices']='malformed'
        self.assertTrue(self.run_fixture(snapshots,docs,diagnostic=True)['coverage']['review_issues'])

    def test_grouped_race_approvals_validate_each_personas_candidate_set(self):
        snapshots,docs=fixture()
        docs[0]['races'].append({'id':3,'name':'Dwarf','faction':'Alliance','classes':['Warrior']})
        self.approve(self.run_fixture(snapshots,docs),docs)
        grouped={}
        for review in docs[4]['rankings']:
            key=forever.digest({k:v for k,v in review.items() if k!='race_id'})
            row=grouped.setdefault(key,{k:v for k,v in review.items() if k!='race_id'})
            row.setdefault('race_ids',[]).append(review['race_id'])
        docs[4]['rankings']=list(grouped.values())
        self.assertTrue(self.run_fixture(snapshots,docs)['coverage']['ok'])
        alliance=next(r for r in docs[4]['rankings'] if r['faction']=='Alliance')
        self.assertEqual(set(alliance['race_ids']),{1,3})
        alliance['race_ids'].append(2)
        with self.assertRaisesRegex(ValueError,'unsupported persona'):
            self.run_fixture(snapshots,docs)

    def test_weapon_configuration_slot_ranges_have_no_phantom_coverage_requirements(self):
        snapshots, docs = fixture()
        rules = docs[0]
        policy = rules["spec_policies"]["Warrior/Arms"]
        rules["common_slots"] = []
        policy.update(slots=["Ring"],slot_min_levels={"Ring":10},slot_max_levels={"Ring":19})
        result = self.run_fixture(snapshots,docs)
        for row in result["leveling_audit"]["rows"]:
            self.assertGreaterEqual(row["level_min"],10)
            self.assertLessEqual(row["level_max"],19)
        self.assertFalse(rules_allow_equipment({"slot":"Ring"},"Warrior","Arms",20,"Ring",rules))

    def test_forever_hunter_ranks_weapon_dps_and_does_not_double_count_ranged_power(self):
        rules = {"max_level":59, "level_bands":[["1-59",1,59]],
                 "class_equipment":{"Hunter":{"armor_tiers":[{"level":1,"types":["Leather"]}],"weapon_types":["Bow"]}},
                 "spec_policies":{"Hunter/Marksmanship":{"weapon_style":"any"}}}
        profiles = {"spec_roles":{"Hunter/Marksmanship":"ranged"},
                    "role_defaults":{"ranged":{"ranged_dps":6,"ranged_attack_power":1,"attack_power":0.6}}}
        common = {"required_level":1,"slot":"Ranged","weapon_subtype":"Bow","name":"Bow"}
        items = [{**common,"id":1,"dps":2,"stats":{"ranged_attack_power":5}},
                 {**common,"id":2,"dps":10}]
        rows, _ = recommendation_rows_for_items(items, {"racial_modifiers":[]}, profiles,
            class_name="Hunter",spec_name="Marksmanship",race="Human",level=14,slot="Ranged",rules=rules,faction="Alliance")
        self.assertEqual([row["item_id"] for row in rows],[2,1])
        stats = effective_stats(items[0],"Hunter","Marksmanship","ranged","Ranged",rules=rules,level=14)
        self.assertEqual(stats["ranged_dps"],2)
        self.assertNotIn("attack_power",stats)
        rogue_stats=effective_stats(items[0],"Rogue","Combat","melee","Ranged",rules=rules,level=14)
        self.assertNotIn("dps",rogue_stats,"ranged weapon DPS must not count as Rogue melee weapon DPS")
        self.assertEqual(rogue_stats["ranged_dps"],2)

    def test_forever_feral_weapon_dps_is_preserved_after_form_unlock(self):
        item = {"dps":30,"stats":{"strength":5},"effect_stats":[{"type":"form_only","stats":{"attack_power":10}}]}
        rules = {"feral_uses_weapon_dps":True,"spec_policies":{"Druid/Feral dps":{"form_level":10}}}
        stats = effective_stats(item,"Druid","Feral dps","melee","Two Hand",rules=rules,level=20)
        self.assertEqual(stats["dps"],30)
        self.assertEqual(stats["attack_power"],10)
        self.assertNotIn("dps",effective_stats(item,"Druid","Feral dps","physical_dps","Two Hand"))

    def test_assassination_dagger_policy_preserves_its_ranged_options(self):
        rules={"class_equipment":{"Rogue":{"armor_tiers":[{"level":1,"types":["Leather"]}],"weapon_types":["Dagger","Axe","Bow"]}},
               "spec_policies":{"Rogue/Assassination":{"dual_wield_level":10,"slot_weapon_types":{"Main Hand":["Dagger"],"Off Hand":["Dagger"]}}}}
        for slot in ["Main Hand","Off Hand"]:
            self.assertFalse(rules_allow_equipment({"slot":"One Hand","weapon_subtype":"Axe"},"Rogue","Assassination",30,slot,rules))
            self.assertTrue(rules_allow_equipment({"slot":"One Hand","weapon_subtype":"Dagger"},"Rogue","Assassination",30,slot,rules))
        self.assertTrue(rules_allow_equipment({"slot":"Ranged","weapon_subtype":"Bow"},"Rogue","Assassination",30,"Ranged",rules))

    def test_weapon_training_distinguishes_one_and_two_handed_types(self):
        rules={"class_equipment":{"Mage":{"armor_tiers":[{"level":1,"types":["Cloth"]}],
                "weapon_types":["Dagger","Staff","Sword","Wand"],"two_hand_weapon_types":["Staff"]}},
               "spec_policies":{"Mage/Frost":{}}}
        self.assertFalse(rules_allow_equipment({"slot":"Two Hand","weapon_subtype":"Sword"},"Mage","Frost",14,"Two Hand",rules))
        self.assertTrue(rules_allow_equipment({"slot":"Two Hand","weapon_subtype":"Staff"},"Mage","Frost",14,"Two Hand",rules))
        self.assertTrue(rules_allow_equipment({"slot":"One Hand","weapon_subtype":"Sword"},"Mage","Frost",14,"Main Hand",rules))

    def test_leveling_only_import_refreshes_shared_evidence_without_changing_pre_raid(self):
        snapshots, _ = fixture()
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            sentinel = directory/"items.json"
            sentinel.write_text('{"items":[{"id":999}]}',encoding="utf-8")
            with patch.object(forever,"read_snapshots",return_value=snapshots), patch.object(
                forever,"FOREVER_CANONICAL_DIR",directory), patch.object(leveling,"documents",return_value={"leveling_gear":{"leveling_gear":[]}}), patch.object(
                sources,"enrich_retry_metadata",return_value=0):
                report=forever.import_snapshots(directory,dry_run=False,family="leveling")
            self.assertEqual(report["evidence"],len(snapshots))
            self.assertTrue((directory/"evidence.json").is_file())
            self.assertEqual(sentinel.read_text(encoding="utf-8"),'{"items":[{"id":999}]}')

    def run_fixture(self, snapshots, docs, diagnostic=False):
        with patch.object(leveling, "inputs", return_value=docs), patch.object(leveling, "roster", return_value={("Warrior", "Arms")}):
            return leveling.generate(snapshots, diagnostic=diagnostic)

    def approve(self, result, docs):
        rules, profiles, _, _, reviews = docs
        for row in result["leveling_audit"]["rows"]:
            reviews["rankings"].append({**profiles["review"], **{k: row[k] for k in (
                "class", "spec", "slot", "faction", "race_id", "level_min", "level_max", "candidate_digest")},
                "profile_version": profiles["version"], "rules_version": rules["version"], "item_ids": row["candidate_item_ids"]})

    def test_filtering_precedes_rank_truncation_and_covers_every_level(self):
        snapshots, docs = fixture()
        draft = self.run_fixture(snapshots, docs)
        alliance = [row for row in draft["leveling_audit"]["rows"] if row["faction"] == "Alliance"]
        self.assertTrue(all([choice["item_id"] for choice in row["candidate_choices"]] == [72, 71] for row in alliance))
        self.assertFalse(draft["leveling_recommendations"]["leveling_recommendations"])
        self.approve(draft, docs)
        result = self.run_fixture(snapshots, docs)
        self.assertTrue(result["coverage"]["ok"])
        for faction in ("Alliance", "Horde"):
            for level in range(1, 60):
                self.assertTrue(any(r["faction"] == faction and r["level_min"] <= level <= r["level_max"]
                                    for r in result["leveling_recommendations"]["leveling_recommendations"]))
        self.assertEqual(result, self.run_fixture(snapshots, docs), "import must be deterministic")

    def test_stale_approvals_reject_import_but_keep_the_gap_report_readable(self):
        snapshots, docs = fixture()
        self.approve(self.run_fixture(snapshots, docs), docs)
        docs[1]["role_defaults"]["physical_dps"]["stamina"] = 2
        with self.assertRaisesRegex(ValueError, "Stale leveling ranking"):
            self.run_fixture(snapshots, docs)
        result = self.run_fixture(snapshots, docs, diagnostic=True)
        self.assertTrue(result["leveling_audit"]["review_issues"])
        self.assertFalse(result["coverage"]["ok"])
        self.assertFalse(result["leveling_recommendations"]["leveling_recommendations"])

    def test_weight_revision_reopens_rankings_and_uses_the_reviewed_coefficient(self):
        snapshots, docs = fixture()
        original = self.run_fixture(snapshots, docs)
        self.approve(original, docs)
        profiles = docs[1]
        profiles["weight_revisions"] = {
            "Warrior/Arms": {"version": "fixture-2", "review": profiles["review"], "weights": {"stamina": 2}},
        }
        revised = self.run_fixture(snapshots, docs, diagnostic=True)
        before, after = original["leveling_audit"]["rows"][0], revised["leveling_audit"]["rows"][0]
        self.assertNotEqual(before["candidate_digest"], after["candidate_digest"])
        self.assertEqual(after["status"], "stale_review")
        self.assertEqual(after["eligible_candidate_count"], before["eligible_candidate_count"])
        self.assertEqual(after["candidate_scores"][0]["score"], before["candidate_scores"][0]["score"] * 2)
        with self.assertRaisesRegex(ValueError, "Stale leveling ranking"):
            self.run_fixture(snapshots, docs)

    def test_forever_tooltip_keeps_on_use_power_out_of_permanent_stats(self):
        lines = [
            "Fixture Helm", "Head", "Mail", "213 Armor", "+16 Stamina",
            "Equip: Increases damage and healing done by magical spells and effects by up to 7.",
            "Use: Increases damage and healing done by magical spells and effects by up to 150 for 20 sec.",
        ]
        item = scraper.parse_item_stats("https://www.wowhead.com/forever/item=100", 100, "Fixture Helm",
                                        " ".join(lines), lines, "Head", "rare", "bind_on_pickup", False, [])
        self.assertEqual(item["stats"], {"stamina": 16, "spell_power": 7})
        self.assertEqual([effect["type"] for effect in item["effect_stats"]], ["passive", "use"])

    def test_route_level_race_class_and_each_dependency_family(self):
        source = {"side": "Both", "eligibility": {"min_level": 14, "races": ["Human"], "classes": ["Warrior"]}}
        self.assertFalse(leveling.route_allows(source, "Alliance", "Human", "Warrior", 13))
        self.assertTrue(leveling.route_allows(source, "Alliance", "Human", "Warrior", 14))
        source["eligibility"]["max_level"] = 14
        self.assertFalse(leveling.route_allows(source, "Alliance", "Human", "Warrior", 15))
        source["eligibility"].pop("max_level")
        self.assertFalse(leveling.route_allows(source, "Alliance", "Night Elf", "Warrior", 14))
        self.assertFalse(leveling.route_allows(source, "Alliance", "Human", "Mage", 14))
        source["quest_starter_sources"] = [{"side": "Horde", "eligibility": {"min_level": 1}}]
        self.assertFalse(leveling.route_allows(source, "Alliance", "Human", "Warrior", 14))
        source["quest_starter_sources"].append({"side": "Both", "eligibility": {"min_level": 15}})
        self.assertTrue(leveling.route_allows(source, "Alliance", "Human", "Warrior", 15))
        source["recipe_sources"] = [{"side": "Horde", "eligibility": {"min_level": 1}}]
        self.assertFalse(leveling.route_allows(source, "Alliance", "Human", "Warrior", 15))

    def test_unknown_levels_and_zero_score_starter_items(self):
        snapshots, docs = fixture()
        docs[1]["role_defaults"] = {"physical_dps": {}}
        result = self.run_fixture(snapshots, docs)
        self.assertTrue(result["leveling_audit"]["rows"][0]["candidate_item_ids"])
        scored = [{"score": 0, "item": {"id": i, "item_level": i, "name": str(i)}} for i in range(1, 9)]
        self.assertEqual([r["item"]["id"] for r in select_recommendations(scored, rules=docs[0])], [8, 7, 6])
        unknown = {"id": 999, "slot": "Ring", "sources": [{"side": "Both", "eligibility": {"min_level": 1}}]}
        self.assertIsNone(leveling.eligible_item(unknown, {"class":"Warrior", "spec":"Arms"}, docs[0]["races"][0], 14, "Ring", docs[0]))

    def test_large_forever_race_masks_and_unsupported_tbc_equipment(self):
        self.assertTrue(leveling.mask_has(4294967373, 32))
        self.assertFalse(leveling.mask_has(4294967373, 33))
        self.assertTrue(leveling.mask_has(8589934770, 33))
        _, docs = fixture()
        item = {"id": 1, "slot": "Chest", "armor_type": "Plate", "required_level": 1}
        rows, _ = recommendation_rows_for_items([item], docs[2], docs[1], class_name="Warrior", spec_name="Arms",
                                                race="Human", level=50, slot="Chest", rules=docs[0])
        self.assertFalse(rows, "a TBC level-40 plate unlock must not leak into explicit Forever rules")

    def test_feral_form_effects_start_at_the_verified_form_unlock(self):
        item = {"dps": 10, "effect_stats": [{"type":"form_only","stats":{"attack_power":40}}]}
        rules = {"spec_policies":{"Druid/Feral dps":{"form_level":10}}}
        before = effective_stats(item,"Druid","Feral dps","physical_dps","Two Hand",rules=rules,level=9)
        after = effective_stats(item,"Druid","Feral dps","physical_dps","Two Hand",rules=rules,level=10)
        self.assertEqual(before,{"dps":10})
        self.assertEqual(after,{"attack_power":40})

    def test_missing_route_eligibility_and_unreviewed_effects_fail_closed(self):
        snapshots, docs = fixture()
        docs[4]["items"][0]["sources"][0].pop("eligibility")
        with self.assertRaisesRegex(ValueError, "eligibility"):
            self.run_fixture(snapshots, docs)
        result = self.run_fixture(snapshots, docs, diagnostic=True)
        self.assertTrue(result["leveling_audit"]["review_issues"])
        snapshots, docs = fixture()
        url = docs[4]["items"][0]["snapshot_url"]
        snapshots[url]["item_stats"]["equip_effects"] = ["Unvalued proc"]
        review = docs[4]["items"][0]
        review["snapshot_digest"] = forever.snapshot_digest(snapshots[url])
        review["evidence_refs"] = [sources.evidence_ref(url,snapshots)]
        review["sources"][0]["evidence_refs"] = review["evidence_refs"]
        with self.assertRaisesRegex(ValueError,"effects require explicit review"):
            self.run_fixture(snapshots,docs)

    def test_suffix_approvals_identify_the_actual_roll(self):
        snapshots, docs = fixture()
        docs[3]["item_variants"] = [{**docs[1]["review"], "item_id":71, "random_suffix_id":suffix,
                                     "suffix_name":f"of Fixture {suffix}",
                                     "stat_delta":{"stamina":bonus}} for suffix,bonus in ((1,100),(-2,99))]
        docs[4]["items"][0]["variant_only"] = True
        result = self.run_fixture(snapshots,docs)
        self.approve(result,docs)
        with self.assertRaisesRegex(ValueError,"variant-aware"):
            self.run_fixture(snapshots,docs)
        for approval, row in zip(docs[4]["rankings"],result["leveling_audit"]["rows"]):
            approval.pop("item_ids")
            approval["choices"] = row["candidate_choices"]
        published=self.run_fixture(snapshots,docs)["leveling_recommendations"]["leveling_recommendations"]
        self.assertTrue(any(row.get("variant_id")=="71:1" and row["rank"]==1 for row in published))
        self.assertTrue(any(row.get("random_suffix_id")==-2 and row.get("variant_name") for row in published))

    def test_unknown_data_cannot_be_approved_as_no_eligible_gear(self):
        snapshots, docs = fixture()
        docs[4]["items"] = []
        result = self.run_fixture(snapshots,docs)
        self.approve(result,docs)
        for row in docs[4]["rankings"]:
            row["disposition"]="no_eligible_item"
            row["absence_evidence_refs"]=row["evidence_refs"]
        with self.assertRaisesRegex(ValueError,"exhaustive eligibility"):
            self.run_fixture(snapshots,docs)

    def test_absence_evidence_must_cover_the_exact_persona_slot_and_levels(self):
        scope = {"class":"Warrior", "spec":"Arms", "faction":"Alliance", "race_id":1,
                 "slot":"Ring", "level_min":1, "level_max":10}
        evidence = {"exhaustive_eligibility":True, "eligibility_scopes":[scope]}
        profile = {"class":"Warrior", "spec":"Arms"}
        persona = {"faction":"Alliance", "id":1}
        self.assertTrue(leveling.absence_covers(evidence,profile,persona,"Ring",1,10))
        self.assertFalse(leveling.absence_covers(evidence,profile,persona,"Head",1,10))
        self.assertFalse(leveling.absence_covers(evidence,profile,persona,"Ring",1,11))
        self.assertFalse(leveling.absence_covers(evidence,profile,{"faction":"Horde","id":2},"Ring",1,10))

    def test_racial_faction_context_and_weapon_training_breakpoints(self):
        effects = {"racial_modifiers":[{"race":"Skyborne","type":"numeric","faction":side,
            "modifier":{"stat":"stamina","value":value}} for side,value in (("Alliance",2),("Horde",9))]}
        self.assertEqual(racial_score_bonus({},"Skyborne","tank",{"stamina":1},effects,
            faction="Alliance",level=14,rules={})[0],2)
        self.assertEqual(racial_score_bonus({},"Skyborne","tank",{"stamina":1},effects,
            faction="Horde",level=14,rules={})[0],9)
        _, docs = fixture()
        rules = docs[0]
        rules["class_equipment"]["Warrior"]["two_hand_weapon_types"] = ["Sword"]
        rules["class_equipment"]["Warrior"]["weapon_unlocks"] = [
            {"weapon_subtype":"Sword","slots":["Two Hand"],"min_level":20,"specs":["Arms"]}]
        item = {"slot":"Two Hand","weapon_subtype":"Sword"}
        self.assertFalse(rules_allow_equipment(item,"Warrior","Arms",19,"Two Hand",rules))
        self.assertTrue(rules_allow_equipment(item,"Warrior","Arms",20,"Two Hand",rules))

    def test_forever_druids_can_train_two_handed_polearms_at_twenty(self):
        rules = dataset_json("forever", "leveling_rules")
        polearm = {"slot": "Two Hand", "weapon_subtype": "Polearm"}
        for profile in forever.scoring_profiles()["profiles"]:
            if profile["class"] != "Druid":
                continue
            spec = profile["spec"]
            with self.subTest(spec=spec):
                self.assertFalse(rules_allow_equipment(polearm, "Druid", spec, 19, "Two Hand", rules))
                self.assertTrue(rules_allow_equipment(polearm, "Druid", spec, 20, "Two Hand", rules))
                self.assertTrue(forever.eligible(polearm, profile, "Two Hand", require_source=False))

    def test_approvals_cannot_drop_required_alternatives_and_diagnostics_survive_bad_variants(self):
        snapshots, docs = fixture()
        result = self.run_fixture(snapshots,docs)
        self.approve(result,docs)
        docs[4]["rankings"][0]["item_ids"] = docs[4]["rankings"][0]["item_ids"][:1]
        with self.assertRaisesRegex(ValueError,"obtainable candidates"):
            self.run_fixture(snapshots,docs)
        self.assertTrue(self.run_fixture(snapshots,docs,diagnostic=True)["leveling_audit"]["review_issues"])
        docs[3]["item_variants"] = [None]
        self.assertFalse(self.run_fixture(snapshots,docs,diagnostic=True)["coverage"]["ok"])

    def test_shared_pre_raid_items_retain_leveling_route_restrictions(self):
        old = {"type":"drop","side":"Both"}
        current = {"type":"quest","side":"Alliance","eligibility":{"min_level":14,"races":["Human"]}}
        merged = generate_lua.merge_forever_leveling_rows(
            [{"id":71,"name":"Ring","sources":[old]}],
            [{"id":71,"name":"Ring","sources":[current]}])
        self.assertEqual(merged[0]["sources"],[current,old])
        self.assertEqual(merged[0]["primary_source"],current)
        with self.assertRaisesRegex(ValueError,"Conflicting approved"):
            generate_lua.merge_forever_leveling_rows([{"id":71,"stats":{"stamina":1}}],
                                                     [{"id":71,"stats":{"stamina":2}}])
        old_quest = {"type":"quest","quest_id":7,"side":"Both"}
        new_quest = {**old_quest,"eligibility":{"min_level":14,"classes":["Warrior"]}}
        merged = generate_lua.merge_forever_leveling_rows([{"id":71,"sources":[old_quest]}],
                                                         [{"id":71,"sources":[new_quest]}])
        self.assertEqual(merged[0]["sources"],[new_quest],"an older unrestricted route must not bypass reviewed gates")
        with self.assertRaisesRegex(ValueError,"route eligibility"):
            generate_lua.merge_forever_leveling_rows([{"id":71,"sources":[new_quest]}],
                [{"id":71,"sources":[{**new_quest,"eligibility":{"min_level":10,"classes":["Warrior"]}}]}])
        with self.assertRaisesRegex(ValueError,"route eligibility"):
            generate_lua.merge_forever_leveling_rows([{"id":71,"sources":[old_quest]}],
                [{"id":71,"sources":[{**new_quest,"side":"Alliance"}]}])

    def test_distinct_faction_trade_markets_are_independent_acquisition_routes(self):
        alliance={"type":"trade","item_id":71,"side":"Alliance","source_url":"https://ahledger.com/alliance",
                  "market_observation":{"market":"forever/normal/alliance/us"}}
        horde={"type":"trade","item_id":71,"side":"Horde","source_url":"https://ahledger.com/horde",
               "market_observation":{"market":"forever/normal/horde/us"}}
        merged=generate_lua.merge_forever_leveling_rows([],[{"id":71,"sources":[alliance,horde]}])
        merged=generate_lua.merge_forever_leveling_rows(merged,[{"id":71,"sources":[alliance,horde]}])
        self.assertEqual(merged[0]["sources"],[alliance,horde])
        with self.assertRaisesRegex(ValueError,"route eligibility"):
            generate_lua.merge_forever_leveling_rows(merged,[{"id":71,"sources":[{**alliance,"side":"Horde"}]}])

    def test_shared_reward_quest_retains_independent_faction_prerequisites(self):
        def branch(side,minimum,prerequisites):
            return {"type":"quest","quest_id":2701,"side":side,"eligibility":{"min_level":minimum},
                    "quest_steps":[{"quest_id":i,"kind":"prerequisite"} for i in prerequisites]
                        +[{"quest_id":2701,"kind":"reward"}]}
        alliance=branch("Alliance",50,[2783,2801,2681,2702])
        horde=branch("Horde",45,[2784,2621,2622,2623,2801,2681,2702])
        original=[{"id":10659,"sources":[alliance,horde]}]
        merged=generate_lua.merge_forever_leveling_rows(original,deepcopy(original))
        self.assertEqual(merged[0]["sources"],[alliance,horde])
        self.assertEqual([r["eligibility"]["min_level"] for r in merged[0]["sources"]],[50,45])
        for changed in ({**alliance,"side":"Horde"}, {**alliance,"eligibility":{"min_level":45}}):
            with self.assertRaisesRegex(ValueError,"route eligibility"):
                generate_lua.merge_forever_leveling_rows(original,[{"id":10659,"sources":[changed]}])
        with self.assertRaisesRegex(ValueError,"Ambiguous.*quest branch"):
            generate_lua.merge_forever_leveling_rows(original,[{"id":10659,"sources":[
                {"type":"quest","quest_id":2701,"side":"Both","eligibility":{"min_level":1}}]}])

    def test_shared_craft_keeps_faction_recipe_vendors_and_rejects_conflicting_gates(self):
        def route(side,vendor):
            return {"type":"crafted","spell_id":1249006,"profession":"Enchanting","side":side,
                    "eligibility":{"min_level":20,"classes":["Paladin"]},
                    "recipe_sources":[{"type":"vendor","vendor_id":vendor,"item_id":249494,"side":side,
                                       "eligibility":{"min_level":20},"requirements":[
                                           {"type":"reputation","scope":"learn_recipe","reputation":side+" commerce",
                                            "standing":"Friendly","standing_rank":5}]}]}
        alliance,horde=route("Alliance",256732),route("Horde",248199)
        original=[{"id":249396,"sources":[alliance,horde]}]
        merged=generate_lua.merge_forever_leveling_rows(original,deepcopy(original))
        self.assertEqual(merged[0]["sources"],[alliance,horde])
        for field,value in [("side","Horde"),("eligibility",{"min_level":1})]:
            changed=deepcopy(alliance)
            changed["recipe_sources"][0][field]=value
            with self.assertRaisesRegex(ValueError,"route eligibility"):
                generate_lua.merge_forever_leveling_rows(original,[{"id":249396,"sources":[changed]}])
        for requirement in ([],[{"type":"reputation","scope":"learn_recipe","reputation":"Alliance commerce",
                                 "standing":"Honored","standing_rank":6}]):
            changed=deepcopy(alliance)
            changed["recipe_sources"][0]["requirements"]=requirement
            with self.assertRaisesRegex(ValueError,"route requirements"):
                generate_lua.merge_forever_leveling_rows(original,[{"id":249396,"sources":[changed]}])
        unrestricted={k:v for k,v in alliance.items() if k!="recipe_sources"}
        with self.assertRaisesRegex(ValueError,"Ambiguous.*recipe access"):
            generate_lua.merge_forever_leveling_rows(original,[{"id":249396,"sources":[unrestricted]}])

    def test_guide_gear_uses_reviewed_intervals_and_keeps_faction_context(self):
        url = forever.WOWHEAD_ROOT+"guide/fixture"
        snapshots = {url:{"tables":[{"rows":[{"item_id":71,"source_text":"Fixture quest","level_min":10,"level_max":20}]}]}}
        manifest = {"sources":[{"url":url,"data_family":"leveling","class":"Warrior","spec":"Arms"}]}
        selected = {"class":"Warrior","spec":"Arms","race":"Human","race_id":1,"faction":"Alliance",
                    "slot":"Ring","item_id":71,"rank":1,"level_min":14,"level_max":25}
        rows = leveling.guide_gear([selected],snapshots,manifest)
        self.assertEqual((rows[0]["level_min"],rows[0]["level_max"]),(14,20))
        self.assertEqual(rows[0]["faction"],"Alliance")
        encoded = generate_lua.compact_record(rows[0],"leveling_gear")
        self.assertEqual(encoded[-3:],["Human","Alliance",1])


class ProviderLevelingTests(unittest.TestCase):
    def test_batched_retries_preserve_attributed_metadata_and_attempt_history(self):
        url = forever.WOWHEAD_ROOT+"item=71"
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory/"retry_ledger.json"
            path.write_text(json.dumps({"flavor":"forever","catalog_attribution":{"source_url":"https://ahledger.com/data"},
                "entries":[{"url":url,"name":"Original metadata","last_attempt_at":"2026-11-01T00:00:00Z",
                    "last_error":"old 404","status":"pending","metadata_sources":["https://ahledger.com/data"]}]}))
            with patch.object(sources,"FOREVER_CANONICAL_DIR",directory):
                sources.record_attempts([(url,"new 404"),(forever.WOWHEAD_ROOT+"quest=7",None)])
            stored = json.loads(path.read_text())
            row = next(x for x in stored["entries"] if x["url"]==url)
            self.assertEqual(row["name"],"Original metadata")
            self.assertEqual(row["metadata_sources"],["https://ahledger.com/data"])
            self.assertEqual([attempt["error"] for attempt in row["history"]],["old 404","new 404"])
            self.assertEqual(stored["catalog_attribution"]["source_url"],"https://ahledger.com/data")
            catalog_url = "https://ahledger.com/api/catalog?class=armor"
            snapshot = sources.normalize_ahledger(catalog_url,{"rows":[[71,"Observed name","COMMON","Cloth",1,1,"icon","CHEST"]]},collected_at="fixture")
            with patch.object(sources,"FOREVER_CANONICAL_DIR",directory):
                self.assertEqual(sources.enrich_retry_metadata({catalog_url:snapshot}),1)
                self.assertEqual(sources.enrich_retry_metadata({catalog_url:snapshot}),0)
            enriched = next(x for x in json.loads(path.read_text())["entries"] if x["url"]==url)
            self.assertEqual(enriched["history"],row["history"])
            self.assertEqual(enriched["metadata_observations"][0]["confidence"],"catalog_metadata")
            self.assertTrue(enriched["metadata_observations"][0]["attribution"])
            self.assertNotIn("item_stats",enriched["metadata_observations"][0])

    def test_partial_duplicate_and_empty_paginated_feeds(self):
        page = {"offset":0,"limit":1,"total":2,"records":[{}],"next":"https://everloot.app/api/corpus/public?offset=1"}
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            sources.validate_everloot_pages([page])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            sources.validate_everloot_pages([page,{**page,"next":None}])
        sources.validate_everloot_pages([page,{**page,"offset":1,"next":None}])
        sources.validate_everloot_pages([{"offset":0,"limit":500,"total":0,"records":[],"next":None}])

    def test_guide_body_changes_invalidate_evidence_even_without_gear_table_changes(self):
        url = forever.WOWHEAD_ROOT+"guide/fixture"
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.object(scraper,"fetch_url",return_value="<title>Fixture guide</title><p>Strength first</p>"):
                scraper.fetch_forever_snapshot(url,directory,retries=0,delay=0,refresh=True)
            first = json.loads((directory/scraper.snapshot_name(url)).read_text())
            ref = sources.evidence_ref(url,{url:first})
            with patch.object(scraper,"fetch_url",return_value="<title>Fixture guide</title><p>Agility first</p>"):
                scraper.fetch_forever_snapshot(url,directory,retries=0,delay=0,refresh=True)
            second = json.loads((directory/scraper.snapshot_name(url)).read_text())
            self.assertEqual(first["tables"],second["tables"])
            with self.assertRaisesRegex(ValueError,"Stale"):
                sources.check_evidence_refs({"evidence_refs":[ref]},sources.evidence_index({url:second}))

    def test_questiedb_raw_race_masks_retain_high_bits_and_remain_leads(self):
        url = "https://raw.githubusercontent.com/Questie/QuestieDB/"+"a"*40+"/data/Forever/foreverQuestDB.lua"
        payload = 'QuestieDB.questData = [[return {[7]={"Fixture",nil,nil,10,15,8589934770,1}}]]'
        row = sources.normalize_questiedb_leads(url,payload,collected_at="fixture")
        self.assertEqual(row["records"][0]["required_races_mask_lead"],8589934770)
        self.assertTrue(leveling.mask_has(row["records"][0]["required_races_mask_lead"],33))
        self.assertFalse(row["corrections_applied"])
        self.assertEqual(row["confidence"],"questiedb_raw_lead")

    def test_discovery_includes_inline_class_quest_links(self):
        url = forever.WOWHEAD_ROOT+"guide/fixture"
        snapshots = {url:{"page_type":"guide","linked_entities":[
            {"url":forever.WOWHEAD_ROOT+"quest=7","type":"quest","id":7}]}}
        self.assertEqual(sources.discover_sources(snapshots,set())[0]["entity_type"],"quest")

    def test_observed_edges_keep_attribution_but_not_uploader_identifiers(self):
        credit = {"credit":"Data from Everloot", "licence":"CC BY-SA 4.0", "licenceUrl":"https://creativecommons.org/licenses/by-sa/4.0/", "source":"https://everloot.app"}
        row = sources.normalize_everloot("https://everloot.app/api/edges", [{"gameData":None, "attribution":credit,
            "edges":[{"fromKind":"item", "fromId":71, "rel":"dropped_by", "toKind":"npc", "toId":7,
                      "evidence":"observed", "installs":3, "installId":"private"}]}], collected_at="fixture")
        self.assertEqual(row["relationships"][0]["subject_id"], 7)
        self.assertNotIn("installId", json.dumps(row))
        self.assertEqual(row["attribution"], [credit])
        self.assertNotIn("side", row["relationships"][0])

    def test_ahledger_catalog_is_metadata_not_acquisition_or_stats(self):
        row = sources.normalize_ahledger("https://ahledger.com/api/catalog?class=armor",
            {"rows":[[71,"Fixture","COMMON","Cloth",1,1,"icon","CHEST"]]}, collected_at="fixture")
        self.assertEqual(row["confidence"], "catalog_metadata")
        self.assertFalse(row["relationships"])
        self.assertNotIn("item_stats", row)
        self.assertTrue(row["attribution"])

    def test_observed_rppvp_market_keeps_its_faction_and_rejects_a_different_venue(self):
        url="https://api.ahledger.com/v1/pricetable/forever.rppvp.horde.eu"
        table="AHL1|forever/rppvp/horde/eu|1794000522|1\n71:20:18:2:20:20:18:20:0\n"
        snapshot=sources.normalize_ahledger_pricetable(url,table,collected_at="fixture")
        self.assertEqual(snapshot["observed_faction"],"Horde")
        self.assertEqual(snapshot["relationships"][0]["subject_id"],"forever/rppvp/horde/eu")
        with self.assertRaisesRegex(ValueError,"another market"):
            sources.normalize_ahledger_pricetable(url.replace("horde","alliance"),table,collected_at="fixture")

    def test_item_price_requires_an_exact_market_item_and_positive_listing(self):
        url = "https://api.ahledger.com/v1/prices/forever.pvp.horde.us/71?range=7d"
        latest = {"observedAt": "2026-11-10T12:00:00.000Z", "quantity": 2, "minBuyout": 18}
        payload = {"market": "forever.pvp.horde.us", "item": {"id": 71}, "latest": latest}
        snapshot = sources.normalize_ahledger_item_price(url, payload, collected_at="fixture")
        self.assertEqual(snapshot["observed_faction"], "Horde")
        self.assertEqual(snapshot["observed_at"], "2026-11-10T12:00:00+00:00")
        self.assertEqual(snapshot["relationships"][0]["object_id"], 71)
        self.assertTrue(snapshot["attribution"])
        for invalid in (url.replace("horde", "alliance"), url.replace("/71?", "/72?")):
            with self.assertRaisesRegex(ValueError, "another item or market"):
                sources.normalize_ahledger_item_price(invalid, payload, collected_at="fixture")
        for no_listing in (None, {**latest, "quantity": 0}, {**latest, "minBuyout": None}):
            self.assertFalse(sources.normalize_ahledger_item_price(
                url, {**payload, "latest": no_listing}, collected_at="fixture")["relationships"])

    def test_everloot_client_recipe_links_remain_metadata_without_acquisition_approval(self):
        url="https://everloot.app/api/edges/client-layer"
        payload={"schema":"everloot.client-layer/2","build":{"version":"1.60.1.70790"},"credit":"Game data Blizzard",
                 "items":[[71,4,0,11,1]],"edges":[["item",71,"created_by","spell",7]]}
        snapshot=sources.collect_everloot(url,lambda _:payload,collected_at="fixture")
        self.assertEqual(snapshot["relationships"][0]["subject_id"],7)
        self.assertEqual(snapshot["confidence"],"client_metadata_only")
        review={**fixture()[1][1]["review"],"source_url":url,"type":"crafted","spell_id":7,"side":"Both",
                "evidence_refs":[sources.evidence_ref(url,{url:snapshot})]}
        with self.assertRaisesRegex(ValueError,"not only metadata"):
            forever.validate_route_review(review,forever.evidence_index({url:snapshot}))

    def test_observed_quest_level_is_never_promoted_to_minimum_acceptance_level(self):
        text="# AHledger: public export\n## Quests (1)\n- Fixture | 20 | Zone | Giver | Fixture Ring (choice) | - | 100 | https://ahledger.com/wow-forever/quests/7-fixture"
        row=sources.normalize_ahledger_text("https://ahledger.com/llms-full.txt",text,
            [{"item_id":71,"name":"Fixture Ring"}],collected_at="fixture")
        self.assertEqual(row["relationships"][0]["object_id"],71)
        self.assertEqual(row["records"][0]["observed_quest_level"],20)
        self.assertNotIn("min_level",row["records"][0])
        self.assertNotIn("side",row["relationships"][0])

    def test_dungeon_guide_legend_establishes_minimum_not_recommended_level(self):
        html='<p>Minimum level to pick up that quest</p><table><tr><td>Quest</td><td>Level</td></tr><tr><td><a href="/forever/quest=7">Fixture</a></td><td>9</td></tr></table>'
        url=forever.WOWHEAD_ROOT+"guide/dungeons/every-dungeon-quest-location"
        self.assertEqual(sources.guide_quest_facts(html,url)[0]["min_level"],9)
        self.assertFalse(sources.guide_quest_facts(html.replace("Minimum level to pick up that quest","Recommended level"),url))


class ForeverLevelingRuntimeTests(unittest.TestCase):
    def test_published_leveling_payload_serves_real_character_contexts(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
local level, race, raceID, side, className = 14, "Human", 1, "Alliance", "Warrior"
UnitLevel = function() return level end
UnitRace = function() return race, race, raceID end
UnitFactionGroup = function() return side end
UnitClass = function() return className, string.upper(className) end
dofile("DataForever.lua")
for _, file in ipairs({"Config.lua","DataIndex.lua","Widgets.lua","UI.lua","DetailsSources.lua","Tooltip.lua"}) do
    assert(loadfile(file))("BigBiSList")
end
local addon = BigBiSList
assert(addon:GetContentMode()=="leveling")
GetProfessions = function() return nil, nil, nil, 4 end
GetProfessionInfo = function(index)
    assert(index == 4)
    return "Fishing", nil, 75
end
assert(addon.UI:BuildAccessState().professions.fishing.skill==75,"secondary skill was skipped after empty profession slots")
local function rowsFor(spec)
    local groups=addon:GetLevelingRows(className,spec,level,{race=race,faction=side})
    local items={}
    for _,group in ipairs(groups) do
        for _,row in ipairs(group.items) do
            local option=row.matched_access_option or row.acquisition_display.option
            assert(option,"published leveling item is missing its acquisition route")
            assert(option.side=="Both" or option.side==side,"opposing faction route leaked")
            assert(addon:AccessOptionMatchesCharacter(option, {
                faction=side, race=race, class=className, level=level, _leveling=true,
            }), "ineligible route displayed")
            items[row.item_id]=row
        end
    end
    return groups,items
end
local function assertLinedFishingRoute(items,spec)
    local hat=assert(items[19972],"shared fishing hat recommendation is missing")
    assert(addon:GetLevelingSlotStatus(className,spec,level,"Head").state=="recommended")
    local route=hat.matched_access_option.source
    assert(route.side=="Both" and route.quest_id==8221 and route.eligibility.min_level==1,
        "the shared fishing route has the wrong scope or quest")
    assert(route.quest_steps[1].quest_id==8221 and not route.quest_steps[2],
        "the helper's line quest should not appear as a prerequisite for the recipient")
end
local groups,items=rowsFor("Arms")
assert(#groups>0 and items[4778],"published level-14 Human Arms weapon is missing")
assert(#addon:GetLevelingTooltipMatches(4778,"Warrior","Arms",14,true)>0)
assert(items[4368],"profession-gated Human headgear alternative is missing")
assert(items[277204] or items[277203],"reviewed shared library necklace is missing")
assert(items[286737] and not items[281268],"Human cannot use the shared Alliance starter ring")
local earlyShoulder=addon:GetLevelingSlotStatus("Warrior","Arms",14,"Shoulder")
assert(earlyShoulder.state=="unreviewed" or earlyShoulder.state=="no_useful_item", "unavailable shoulder slot displayed gear")
assert(earlyShoulder.next_verified_level==15 and not items[10657], "the Glowing Shard level gate was ignored")
for _,persona in ipairs({{"Human",1,"Alliance"},{"Orc",2,"Horde"}}) do
    race,raceID,side,level=persona[1],persona[2],persona[3],15
    groups,items=rowsFor("Arms")
    local mantle=assert(items[10657],"the level-15 Talbar Mantle recommendation is missing")
    assert(mantle.matched_access_option.source.eligibility.min_level==15)
    level=34
    groups,items=rowsFor("Arms")
    assert(not items[271811],"the carapace starter bypassed the quest pickup minimum")
    level=35
    groups,items=rowsFor("Arms")
    local spaulders=assert(items[271811],"the shared Corpsefeeder reward is missing").matched_access_option.source
    assert(spaulders.side=="Both" and spaulders.quest_id==93574 and spaulders.eligibility.min_level==35)
    assert(spaulders.quest_starter_item_id==259893 and spaulders.quest_starter_sources[1].entity_id==253394)
end
race,raceID,side="Human",1,"Alliance"
level=9
groups,items=rowsFor("Arms")
assert(not items[4368],"buying goggles bypassed the Engineering rank level gate")
assert(not items[4381],"self-crafting trinket bypassed the Engineering rank level gate")
level=10
groups,items=rowsFor("Arms")
assert(items[4381],"reviewed schematic trade and self-craft trinket route is missing")
level=4
groups,items=rowsFor("Arms")
assert(not items[286737],"Rime's Wrath prerequisite minimum was ignored")
assertLinedFishingRoute(items,"Arms")
level=5
groups,items=rowsFor("Arms")
assert(items[286737],"shared Alliance ring is incorrectly restricted to Dwarves")
assert(items[19972] and addon:GetLevelingSlotStatus("Warrior","Arms",5,"Head").state=="recommended",
    "reviewed level-five Alliance headgear is missing")
for _,persona in ipairs({{"Dwarf",3},{"Gnome",7},{"Night Elf",4},{"Skyborne",95}}) do
    race,raceID,level=persona[1],persona[2],3
    groups,items=rowsFor("Arms")
    assertLinedFishingRoute(items,"Arms")
    level=4
    groups,items=rowsFor("Arms")
    assert(items[19972] and addon:GetLevelingSlotStatus("Warrior","Arms",4,"Head").state=="recommended",
        "reviewed level-four fishing route is missing")
    local fishingRoute=items[19972].matched_access_option.source
    assert(fishingRoute.side=="Alliance" and fishingRoute.quest_id==8221 and fishingRoute.quest_steps[1].quest_id==99143,
        "fishing preparation route is missing")
end
race,raceID="Human",1
level=1
groups,items=rowsFor("Arms")
assertLinedFishingRoute(items,"Arms")
assert(items[260802] and items[260802].score==0,"commissioned level-one Alliance trinket is missing")
assert(addon:GetLevelingSlotStatus("Warrior","Arms",1,"Trinket").state=="recommended")
local mortarOption=items[260802].matched_access_option or items[260802].acquisition_display.option
assert(mortarOption.side=="Alliance" and mortarOption.source.type=="crafted","wrong level-one Alliance trinket route")
level=14
className="Mage"
groups,items=rowsFor("Frost")
assert(items[11288],"published Human wand is missing")
assert(not items[1198],"one-handed sword training permitted a two-handed sword")
race,raceID,level="Gnome",7,43
groups,items=rowsFor("Frost")
assert(not items[276904],"Shimmerwine Spirits bypassed the quest's acquisition minimum")
level=44
groups,items=rowsFor("Frost")
local shimmerRoute=assert(items[276904],"reviewed Shimmerwine Spirits is missing").matched_access_option.source
assert(shimmerRoute.side=="Alliance" and shimmerRoute.quest_id==96609 and shimmerRoute.eligibility.min_level==44)
race,raceID,side="Troll",8,"Horde"
groups,items=rowsFor("Frost")
assert(not items[276904],"the Alliance Shimmerwine Spirits route leaked to Horde")
race,raceID,side="Human",1,"Alliance"
level=4
groups,items=rowsFor("Frost")
assert(not items[15925],"an earlier purchase route bypassed the off-hand equip level")
level=5
groups,items=rowsFor("Frost")
assert(items[15925],"reviewed level-five Alliance off-hand is missing")
race,raceID,side,level="Orc",2,"Horde",32
groups,items=rowsFor("Frost")
assert(items[4373],"reviewed Horde engineering headgear is missing")
level=4
groups,items=rowsFor("Frost")
assert(items[281268] and items[281268].score==0,"eligible zero-score starter ring is missing")
assert(not items[286737] and not items[4381],"Alliance ring or schematic route leaked to Horde")
assert(not items[15925],"Horde off-hand equip level was ignored")
assertLinedFishingRoute(items,"Frost")
assert(items[260802],"reviewed Horde trinket is missing below level five")
level=5
groups,items=rowsFor("Frost")
assert(items[15925],"reviewed Horde market alternative is missing at level five")
assert(items[19972],"reviewed level-five Horde headgear is missing")
level=3
groups,items=rowsFor("Frost")
assert(not items[281268],"Forgotten Loa Idols minimum was ignored")
level=1
groups,items=rowsFor("Frost")
assertLinedFishingRoute(items,"Frost")
level=8
groups,items=rowsFor("Frost")
assert(not items[286745],"a trade route bypassed Furlfeather Ring's level requirement")
level=9
groups,items=rowsFor("Frost")
local furlfeather=assert(items[286745],"the reviewed Horde Furlfeather Ring is missing")
assert(furlfeather.matched_access_option.source.type=="trade" and furlfeather.matched_access_option.source.side=="Horde")
race,raceID,side,level,className="Human",1,"Alliance",30,"Hunter"
groups,items=rowsFor("Survival")
local main,off
for _,group in ipairs(groups) do
    if group.slot=="Main Hand" then main=group.items[1] end
    if group.slot=="Off Hand" then off=group.items[1] end
    assert(not group.items[1].computed_recommendation or group.items[1].rank==1,"range compaction displaced the approved leading choice")
end
assert(main and off and not (main.item_id==6692 and off.item_id==6692),"preferred pair duplicates a Unique-Equipped weapon")
race,raceID,side,level,className="Dwarf",3,"Alliance",14,"Shaman"
groups,items=rowsFor("Restoration")
assert(items[263412],"reviewed Dwarf class-quest relic is missing")
level=9
groups,items=rowsFor("Restoration")
assert(not items[263412],"class-quest acquisition minimum was ignored")
race,raceID,side,level="Skyborne",96,"Horde",14
groups,items=rowsFor("Restoration")
assert(items[263412],"the independently reviewed Skyborne Call of Fire route is missing")
level=4
groups,items=rowsFor("Restoration")
assert(not items[263412],"the conflicting earlier Skyborne reward lead became an approved route")
race,raceID,side,className,level="Human",1,"Alliance","Mage",39
groups,items=rowsFor("Frost")
assert(not items[744],"Sweet Amber's acquisition gate was ignored")
level=40
groups,items=rowsFor("Frost")
assert(items[744] and not items[19120],"Alliance quest alternative was displaced by a Horde trinket")
level=49
groups,items=rowsFor("Frost")
assert(not items[10659],"Alliance entry prerequisite level was ignored")
level=50
groups,items=rowsFor("Frost")
assert(items[10659],"Alliance reward-chain alternative is missing")
race,raceID,side,level="Orc",2,"Horde",44
groups,items=rowsFor("Frost")
assert(not items[744] and not items[10659] and not items[19120],"opposing or premature quest route leaked")
level=45
groups,items=rowsFor("Frost")
assert(items[10659] and not items[19120],"Horde's independent chain minimum was lost")
level=46
groups,items=rowsFor("Frost")
assert(items[19120],"reviewed Horde trinket is missing at its quest acceptance level")
race,raceID,side,className,level="Night Elf",4,"Alliance","Druid",15
groups,items=rowsFor("Balance")
assert(not items[263411],"Aquatic Form level gate was ignored")
level=16
groups,items=rowsFor("Balance")
assert(items[263411],"prepared Night Elf Aquatic Form relic route is missing")
assert(items[263411].matched_access_option.source.eligibility.races[1]=="Night Elf")
race,raceID,side="Tauren",6,"Horde"
groups,items=rowsFor("Balance")
assert(items[263411],"prepared Tauren Aquatic Form relic route is missing")
assert(items[263411].matched_access_option.source.quest_id==31)
race,raceID,side,level="Skyborne",95,"Alliance",15
groups,items=rowsFor("Balance")
assert(not items[263411],"Skyborne Aquatic Form level gate was ignored")
level=16
groups,items=rowsFor("Balance")
assert(items[263411],"prepared Alliance Skyborne Aquatic Form relic route is missing")
local skyborneRoute=items[263411].matched_access_option.source
assert(skyborneRoute.quest_id==5061 and skyborneRoute.eligibility.races[1]=="Skyborne",
    "shared Alliance quest routes were merged")
raceID,side,level=96,"Horde",15
groups,items=rowsFor("Balance")
assert(not items[263411],"Windshaper Skyborne Aquatic Form level gate was ignored")
level=16
groups,items=rowsFor("Balance")
assert(items[263411],"prepared Windshaper Skyborne Aquatic Form relic route is missing")
local windshaperRoute=items[263411].matched_access_option.source
assert(windshaperRoute.quest_id==31 and windshaperRoute.eligibility.races[1]=="Skyborne",
    "shared Horde quest routes were merged")
assert(windshaperRoute.quest_steps[1].quest_id==6126 and windshaperRoute.quest_steps[9].quest_id==31,
    "the Windshaper quest preparation or final turn-in is missing")
race,raceID,side,className,level="Human",1,"Alliance","Warrior",60
addon:SetContentMode("endgame")
local preRaidItems={}
for _,group in ipairs(addon:GetPhaseRows("Warrior","Protection","PR",{})) do
    for _,row in ipairs(group.items) do preRaidItems[row.item_id]=row end
end
assert(preRaidItems[273840] and not preRaidItems[19120],"reviewed Alliance offensive trinket alternative is missing or faction filtering failed")
assert(#H.errors==0,table.concat(H.errors,"\n"))
'''
        result=subprocess.run([lua,"-"],cwd=ADDON_DIR,input=script,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)

    def test_suffix_choices_stay_distinct_and_only_the_owned_roll_matches(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
UnitLevel=function() return 14 end
UnitRace=function() return "Human","Human",1 end
-- FIXTURE_DATA
local function compact(schema,record)
    local result={}
    for index,key in ipairs(BigBiSListData.schemas[schema]) do result[index]=record[key] end
    return result
end
local source=compact("source",{type="quest",side="Both",quest_id=7,entity_name="Shared quest",eligibility={min_level=1}})
-- The synthetic variants exercise recommendation rows without a stat-ranking catalog.
BigBiSListData.stat_rank=nil
BigBiSListData.items={compact("item",{id=71,name="Ring",inventory_slot="Ring",acquisition_phase="PR",sources={source},primary_source=source})}
BigBiSListData.item_eligibility={["71"]={min_level=1}}
BigBiSListData.leveling_recommendations={}
for rank,suffix in ipairs({1,-2}) do
    BigBiSListData.leveling_recommendations[rank]=compact("leveling_recommendation",{class="Warrior",spec="Arms",race="Human",race_id=1,
        faction="Alliance",level_min=1,level_max=59,slot="Ring",item_id=71,rank=rank,variant_id="71:"..suffix,
        random_suffix_id=suffix,variant_name=rank==1 and "Ring of the Bear" or "Ring of the Owl"})
end
for _,file in ipairs({"Config.lua","ForeverGearRating.lua","DataIndex.lua","Widgets.lua","UI.lua","DetailsSources.lua","ComparisonUI.lua","Tooltip.lua"}) do
    assert(loadfile(file))("BigBiSList")
end
local addon,ui=BigBiSList,BigBiSList.UI
addon:EnsureDatabase()
addon:SetSelection("Warrior","Arms","LEVELING","Gear Guide")
local bear="item:71:0:0:0:0:0:1:0"
local owl="item:71:0:0:0:0:0:-2:0"
local rows=addon:GetLevelingRows("Warrior","Arms",14,{})
assert(#rows==1 and #rows[1].items==2 and rows[1].items[1].name=="Ring of the Bear")
ui.currentOwned={inventoryItems={}}
ui:AddOwnedInventoryItem(ui.currentOwned,71,bear,"bags")
assert(ui:GetRowOwnershipState(rows[1].items[1])=="bag", "the owned Bear suffix did not match")
assert(ui:GetRowOwnershipState(rows[1].items[2])=="missing", "the unowned Owl suffix matched")
local owned=addon:GetLevelingRows("Warrior","Arms",14,{ownedItems=ui.currentOwned,ownedState="owned"})
assert(#owned==1 and #owned[1].items==1 and owned[1].items[1].variant_id=="71:1")
assert(not addon:GetItemBestLevelingUseForSpec(71,"Warrior","Arms",14))
assert(addon:GetItemBestLevelingUseForSpec(71,"Warrior","Arms",14,nil,nil,owl).variant_id=="71:-2")
assert(#addon:GetLevelingTooltipMatches(71,"Warrior","Arms",14,true,nil,nil,bear)==1)
assert(#addon:GetLevelingTooltipMatches(71,"Warrior","Arms",14,true,nil,nil,"item:71:0:0:0:0:0:0:0")==0)
assert(#addon:GetLevelingTooltipMatches(71,"Warrior","Arms",14,true)==0)
assert(#H.errors==0,table.concat(H.errors,"\n"))
'''.replace("-- FIXTURE_DATA",generate_lua.render_lua("forever"))
        result = subprocess.run([lua,"-"],cwd=ADDON_DIR,input=script,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)

    def test_mode_migration_waits_for_character_level_and_preserves_manual_preview(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
UnitLevel = function() return nil end
-- FIXTURE_DATA
BigBiSListCharDB = {forever={leveling={manualLevel=true,selectedLevel=12}}}
assert(loadfile("Config.lua"))("BigBiSList")
assert(loadfile("DataIndex.lua"))("BigBiSList")
local addon=BigBiSList
local char=addon:GetCharacterDB()
assert(not char.foreverLevelingMigrated)
UnitLevel = function() return 14 end
assert(addon:GetContentMode()=="leveling")
assert(char.foreverLevelingMigrated and char.leveling.manualLevel and char.leveling.selectedLevel==12)
addon:SetContentMode("endgame")
UnitLevel = function() return 15 end
assert(addon:GetContentMode()=="endgame")
BigBiSListCharDB.forever={leveling={manualLevel=true,selectedLevel=12}}
UnitLevel = function() return 60 end
assert(addon:GetContentMode()=="endgame")
assert(addon:GetCharacterDB().foreverLevelingMigrated and addon:GetSelectedLevelingLevel()==12)
local option={source={side="Both",eligibility={min_level=50}}}
local filters={faction="Alliance",race="Human",class="Warrior",level=12,_leveling=false}
assert(addon:AccessOptionMatchesCharacter(option,filters),"manual leveling preview must not hide level-60 routes")
filters._leveling=true
assert(not addon:AccessOptionMatchesCharacter(option,filters))
'''.replace("-- FIXTURE_DATA",generate_lua.render_lua("forever"))
        result = subprocess.run([lua,"-"],cwd=ADDON_DIR,input=script,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)

    def test_populated_generated_payload_loads_through_the_forever_manifest(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        snapshots, docs = fixture()
        with patch.object(leveling,"inputs",return_value=docs), patch.object(leveling,"roster",return_value={("Warrior","Arms")}):
            draft = leveling.generate(snapshots)
            for row in draft["leveling_audit"]["rows"]:
                docs[4]["rankings"].append({**docs[1]["review"], **{key:row[key] for key in (
                    "class","spec","slot","faction","race_id","level_min","level_max","candidate_digest")},
                    "profile_version":docs[1]["version"],"rules_version":docs[0]["version"],"choices":row["candidate_choices"]})
            result = leveling.generate(snapshots)
        for collection in ("items", "item_stats"):
            for item in result[collection].values():
                item["quality"] = "uncommon"
                if collection == "item_stats":
                    item["stats"]["strength"] = item["stats"]["stamina"]
        overlay = {"items":{"items":[]}, "item_stats":{"item_stats":[]}, "bis_lists":{"lists":[]},
                   "leveling_items":{"items":list(result["items"].values())},
                   "leveling_item_stats":{"item_stats":list(result["item_stats"].values())},
                   "leveling_gear":result["leveling_gear"], "leveling_recommendations":result["leveling_recommendations"]}
        actual = generate_lua.dataset_json
        with patch.object(generate_lua,"dataset_json",side_effect=lambda flavor,name: overlay[name] if name in overlay else actual(flavor,name)):
            payload = generate_lua.render_lua("forever")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
local side = "Alliance"
UnitFactionGroup = function() return side end
UnitRace = function() if side=="Alliance" then return "Human","Human",1 else return "Orc","Orc",2 end end
UnitLevel = function() return 14 end
UnitClass = function() return "Warrior","WARRIOR" end
strmatch = string.match
SlashCmdList = {}
local createFrame = CreateFrame
local function noop() end
CreateFrame = function(...)
    local frame = createFrame(...)
    frame.events = {}
    function frame:RegisterEvent(event) self.events[event]=true end
    function frame:UnregisterEvent(event) self.events[event]=nil end
    if frame:GetName()=="LibDBIcon10_BigBiSList" then
        local createTexture = frame.CreateTexture
        function frame:CreateTexture(...)
            local texture = createTexture(self,...)
            function texture:GetVertexColor() return 1,1,1 end
            return texture
        end
        function frame:CreateAnimationGroup()
            return {SetToFinalAlpha=noop,CreateAnimation=function()
                return {SetOrder=noop,SetDuration=noop,SetFromAlpha=noop,SetToAlpha=noop,SetStartDelay=noop}
            end}
        end
    end
    return frame
end
Minimap = CreateFrame("Frame","Minimap",UIParent)
Minimap:SetSize(140,140)
for line in io.lines("BigBiSList_Camelot.toc") do
    local entry=line:match("^%s*(.-)%s*$")
    if entry=="DataForever.lua" then
        assert(loadfile(arg[1]))("BigBiSList")
    elseif entry~="" and entry:sub(1,1)~="#" then
        assert(loadfile((entry:gsub("\\","/"))))("BigBiSList")
    end
end
local function fire(event,...)
    for _,frame in ipairs(H.frames) do
        if frame.events and frame.events[event] and frame:GetScript("OnEvent") then frame:GetScript("OnEvent")(frame,event,...) end
    end
end
fire("ADDON_LOADED","BigBiSList")
fire("PLAYER_LOGIN")
local addon = BigBiSList
assert(addon:GetContentMode()=="leveling" and addon.minimapButton)
addon:SetSelection("Warrior","Arms","LEVELING","Gear Guide")
addon.UI:Open()
H.settle()
local rows=addon:GetLevelingRows("Warrior","Arms",14,{})
assert(#rows==1 and #rows[1].items==1 and rows[1].items[1].item_id==72,
    "generated eligibility keys and the stat floor must resolve for the Human player")
assert(addon:GetItemBestLevelingUseForSpec(72,"Warrior","Arms",14))
assert(#addon:GetLevelingTooltipMatches(72,"Warrior","Arms",14,true)>0)
side="Horde"
rows=addon:GetLevelingRows("Warrior","Arms",14,{})
assert(#rows==1 and #rows[1].items==3)
for _,row in ipairs(rows[1].items) do assert(row.item_id>=73) end
assert(#addon:GetLevelingTooltipMatches(72,"Warrior","Arms",14,true)==0)
assert(#H.errors==0,table.concat(H.errors,"\n"))
'''
        with TemporaryDirectory() as temporary:
            fixture_payload = Path(temporary) / "DataForever.lua"
            fixture_payload.write_text(payload, encoding="utf-8")
            result = subprocess.run([lua, "-", str(fixture_payload)], cwd=ADDON_DIR, input=script,
                                    text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)

    def test_human_level_14_migration_queries_comparisons_and_tooltips(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
UnitLevel = function() return 14 end
UnitRace = function() return "Human", "Human", 1 end
UnitClass = function() return "Warrior", "WARRIOR" end
dofile("DataForever.lua")
BigBiSListData.meta.supports_leveling = true
local function compact(schema, record)
    local result = {}
    for index, key in ipairs(BigBiSListData.schemas[schema]) do result[index] = record[key] end
    return result
end
local source = compact("source", {type="quest", quest_id=7, entity_name="Alliance quest", side="Alliance", eligibility={min_level=14}})
BigBiSListData.items = {compact("item", {id=71, name="Leveling ring", inventory_slot="Ring", acquisition_phase="PR", primary_source=source, sources={source}})}
BigBiSListData.item_eligibility = {["71"]={min_level=1, classes={"Warrior"}, races={}}}
BigBiSListData.leveling_recommendations = {compact("leveling_recommendation", {class="Warrior",spec="Arms",race="Human",race_id=1,
    faction="Alliance",level_min=14,level_max=59,level_band="1-19",slot="Ring",item_id=71,rank=1,context="best_overall",score=1})}
BigBiSListDB = {profile={sentinel=true}, forever={profile={minimap={hide=false}}}}
BigBiSListCharDB = {wishlist={[99]=true},forever={wishlist={[71]=true},ignoredItems={[72]=true},leveling={manualLevel=true,selectedLevel=14}}}
for _, file in ipairs({"Config.lua","DataIndex.lua","Widgets.lua","UI.lua","DetailsSources.lua","ComparisonUI.lua","Tooltip.lua"}) do assert(loadfile(file))("BigBiSList") end
local addon, ui = BigBiSList, BigBiSList.UI
local char = addon:GetCharacterDB()
assert(addon:GetContentMode()=="leveling" and char.foreverLevelingMigrated)
assert(char.wishlist[71] and char.ignoredItems[72] and char.leveling.manualLevel and BigBiSListCharDB.wishlist[99])
addon:SetSelection("Warrior","Arms","PR","Gear Guide")
local rows=addon:GetLevelingRows("Warrior","Arms",14,{})
assert(#rows==1 and rows[1].items[1].item_id==71)
assert(#addon:GetLevelingRows("Warrior","Arms",13,{})==0)
assert(addon:GetItemBestLevelingUseForSpec(71,"Warrior","Arms",14).item_id==71)
assert(#addon:GetLevelingTooltipMatches(71,"Warrior","Arms",14,true)==1)
UnitFactionGroup=function() return "Horde" end
assert(#addon:GetLevelingRows("Warrior","Arms",14,{})==0)
assert(#addon:GetLevelingTooltipMatches(71,"Warrior","Arms",14,true)==0)
UnitFactionGroup=function() return "Alliance" end
addon:SetContentMode("endgame")
char.foreverLevelingMigrated=nil
char.defaultsVersion=0
addon:EnsureDatabase()
assert(addon:GetContentMode()=="endgame", "explicit mode selection must survive migration")
assert(#H.errors==0,table.concat(H.errors,"\n"))
'''
        script = script.replace('dofile("DataForever.lua")', generate_lua.render_lua("forever"))
        result = subprocess.run([lua,"-"], cwd=ADDON_DIR, input=script, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
