from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.progression_audit import build_progression_audit, main
from tools.project import PHASE_KEYS


class ProgressionAuditTests(unittest.TestCase):
    """Small normalized evidence trees exercise the same reviewed real items.

    The fixture uses Vindicator's Brand (an earlier Aldor item, not Season 3
    Vindicator gear), Delicate Living Ruby, Haste Potion, and the learned Agility
    enchant. Full committed snapshots test the alias importer separately.
    """
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.canonical = self.base / "canonical"
        self.raw = self.base / "raw"
        manifest = json.loads((ROOT / "data/canonical/scrape_manifest.json").read_text(encoding="utf-8"))
        self.registrations = [deepcopy(row) for row in manifest["sources"]
                              if row.get("class") == "Paladin" and row.get("spec") == "Retribution"
                              and (row.get("data_family") in {"bis_lists", "consumables"} or "gems" in row.get("data_families", []))]
        self.urls = {row.get("phase", row.get("data_family", "general")): row["url"] for row in self.registrations}
        self.write(self.canonical / "classes.json", {"classes": [{"name": "Paladin", "specs": [{"name": "Retribution"}]}]})
        self.write(self.canonical / "scrape_manifest.json", {"sources": self.registrations})
        self.records = {
            "bis_lists": {"lists": []}, "gems": {"gems": []}, "enchants": {"enchants": []},
            "consumables": {"consumables": []},
            "items": {"items": [
                {"id": 29124, "name": "Vindicator's Brand", "binding": "bind_on_pickup", "sources": [
                    {"type": "vendor", "entity_name": "Quartermaster Endarin", "zone": "Shattrath City"}]},
                {"id": 22838, "name": "Haste Potion", "sources": [{"type": "crafted", "profession": "Alchemy"}]},
            ]},
            "gem_sources": {"gem_sources": [{"id": 24028, "name": "Delicate Living Ruby", "sources": [
                {"type": "crafted", "profession": "Jewelcrafting"}]}]},
            "enchant_sources": {"enchant_sources": [
                {"id": 23800, "name": "Enchant Weapon - Agility", "type": "spell", "sources": [
                    {"type": "taught_by_item", "item_id": 19445}]},
                {"id": 19445, "type": "item", "name": "Formula: Enchant Weapon - Agility", "sources": [
                    {"type": "vendor", "entity_id": 11557, "entity_name": "Meilosh", "zone": "Felwood"}]},
            ]},
        }
        for phase in PHASE_KEYS:
            base = {"class": "Paladin", "spec": "Retribution", "phase": phase}
            if phase != "PR":
                self.records["bis_lists"]["lists"].append({**base, "slot": "Main Hand", "source_url": self.urls[phase],
                                                            "items": [{"item_id": 29124, "rank": 1}]})
            pr = {**base, "phase": "PR", "content_phase": phase, "slot": "Main Hand", "source_url": self.urls["PR"],
                  "items": [{"item_id": 29124, "rank": 1}]}
            if phase != "PR":
                pr["inherited_from_phase"] = "PR"
            self.records["bis_lists"]["lists"].append(pr)
            self.records["gems"]["gems"].append({**base, "id": 24028, "source_url": self.urls["general"]})
            self.records["enchants"]["enchants"].append({**base, "id": 23800, "type": "spell", "source_url": self.urls["general"]})
            self.records["consumables"]["consumables"].append({**base, "items": [22838], "source_url": self.urls["consumables"]})
        self.save_records()
        for phase in PHASE_KEYS:
            snapshot = self.guide(self.urls[phase], "bis_lists", 29124)
            if phase == "PR":
                snapshot["content_phase"] = "PR"
            self.write(self.raw / "full_bis" / (phase + ".json"), snapshot)
        general = self.guide(self.urls["general"], "gems", 24028)
        general["tables"].append({"data_family": "enchants", "rows": [{"spell_id": 23800}]})
        self.write(self.raw / "full_gems/general.json", general)
        self.write(self.raw / "full_consumables/general.json", self.guide(self.urls["consumables"], "consumables", 22838))
        self.refresh = {"content_phase": "T6", "guides": [
            {"url": url, "fetched_at": "2026-09-04T23:00:00+00:00", "ranking_changed": False, "baseline_ref": "0.12.3"}
            for url in sorted(set(self.urls.values()))], "dependencies": [], "failures": []}
        for kind, entity_id in (("item", 29124), ("item", 22838), ("item", 24028), ("spell", 23800)):
            url = f"https://www.wowhead.com/tbc/{kind}={entity_id}"
            self.refresh["dependencies"].append({"url": url, "fetch_method": "tooltip_endpoint", "acquisition_tables": False})
            old = {"page_type": kind, kind + "_id": entity_id, "url": url, "fetched_at": "2026-05-24T00:00:00+00:00",
                   "normalized_sources": [{"type": "crafted", "entity_name": "Committed earlier acquisition"}]}
            self.write(self.raw / "full_bis" / f"{kind}-{entity_id}.json", old)
            fresh = {**old, "fetched_at": "2026-09-04T23:00:00+00:00", "normalized_sources": [], "fetch_method": "tooltip_endpoint"}
            self.write(self.raw / "progression_items" / f"{kind}-{entity_id}.json", fresh)
        self.write(self.raw / "refresh_report.json", self.refresh)

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")

    def save_records(self):
        for family, document in self.records.items():
            self.write(self.canonical / (family + ".json"), document)

    @staticmethod
    def guide(url, family, item_id):
        return {"page_type": "guide", "url": url, "fetched_at": "2026-09-04T23:00:00+00:00",
                "tables": [{"data_family": family, "rows": [{"item_id": item_id}]}]}

    def audit(self):
        return build_progression_audit(self.canonical, self.raw, expected_spec_count=1,
                                       reviewed_sources={"unverified_price_item_ids": [33672]})

    def test_complete_matrix_and_inherited_paths_are_deterministic_and_honest(self):
        report = self.audit()
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["summary"]["coverage_context_count"], 24)
        self.assertEqual(report["summary"]["pre_raid_context_count"], 6)
        self.assertEqual(report["summary"]["pre_raid_status_counts"], {
            "verified_phase_path": 1, "inherited_earlier_verified_path": 5})
        self.assertEqual(report["summary"]["acquisition_status_counts"], {"tooltip_refreshed_with_retained_routes": 4})
        self.assertEqual(report["reviewed_source_limitations"]["unverified_price_item_ids"], [33672])
        for document in self.records.values():
            next(iter(document.values())).reverse()
        self.save_records()
        self.write(self.canonical / "scrape_manifest.json", {"sources": list(reversed(self.registrations))})
        self.assertEqual(report, self.audit())

    def test_unchanged_general_guide_is_not_a_phase_specific_refresh(self):
        report = self.audit()
        generic = [row for row in report["coverage"] if row["family"] != "bis_lists"]
        self.assertTrue(all(row["status"] == "general_guide_fallback" for row in generic))
        self.assertTrue(all(row["refresh_status"] == "refreshed_unchanged" for row in generic))
        phase_rows = [row for row in report["coverage"] if row["family"] == "bis_lists" and row["phase"] != "PR"]
        self.assertTrue(all(row["status"] == "refreshed_unchanged" for row in phase_rows))
        self.refresh["guides"][0]["ranking_changed"] = True
        self.write(self.raw / "refresh_report.json", self.refresh)
        self.assertTrue(any(row["refresh_status"] == "refreshed_changed" for row in self.audit()["coverage"]))

    def test_phase_gems_distinguish_eligible_guidance_and_later_unavailable_candidates(self):
        phase = {"page_type": "phase_gem_guide", "url": self.urls["T6"],
                 "bindings": [{"class": "Paladin", "spec": "Retribution", "phase": "T6"}],
                 "gem_guidance": [{"kind": "linked_prose", "gem_ids": [32194]}]}
        self.write(self.raw / "phase_gems/t6.json", phase)
        gem_source = {"id": 32194, "name": "Delicate Crimson Spinel", "tradeable": True,
                      "sources": [{"type": "crafted", "available_from_phase": "T6"}]}
        self.records["gem_sources"]["gem_sources"].append(gem_source)
        self.records["gems"]["gems"].append({"class": "Paladin", "spec": "Retribution", "phase": "T6", "id": 32194})
        self.save_records()
        row = next(row for row in self.audit()["coverage"] if row["family"] == "gems" and row["phase"] == "T6")
        self.assertEqual(row["status"], "refreshed_unchanged")
        self.assertEqual(row["available_phase_specific_gem_ids"], [32194])
        self.assertEqual(row["general_fallback_gem_ids"], [24028])
        phase["gem_guidance"][0]["gem_ids"] = [35761]
        self.write(self.raw / "phase_gems/t6.json", phase)
        self.records["gem_sources"]["gem_sources"].append({"id": 35761, "sources": [{"type": "vendor", "available_from_phase": "SWP"}]})
        self.save_records()
        row = next(row for row in self.audit()["coverage"] if row["family"] == "gems" and row["phase"] == "T6")
        self.assertEqual(row["status"], "phase_guidance_unavailable_general_fallback")
        self.assertEqual(row["available_phase_specific_gem_ids"], [])

    def test_missing_registered_family_and_parsed_evidence_fail_strict_audit(self):
        self.write(self.canonical / "scrape_manifest.json", {"sources": [row for row in self.registrations if row.get("data_family") != "consumables"]})
        report = self.audit()
        self.assertEqual(sum(error["code"] == "missing_registered_coverage" for error in report["errors"]), 6)
        self.write(self.raw / "full_gems/general.json", self.guide(self.urls["general"], "enchants", 23800))
        self.assertEqual(sum(error["code"] == "missing_ranking_evidence" for error in self.audit()["errors"]), 6)

    def test_phase_enchant_hook_preserves_partial_guidance_and_actual_formula_routes(self):
        phase = {"page_type": "phase_enchant_guide", "url": self.urls["T6"],
                 "bindings": [{"class": "Paladin", "spec": "Retribution", "phase": "T6"}],
                 "enchant_guidance": [{"kind": "gear_planner", "applications": [
                     {"slot": "Main Hand", "spell_id": 23800}, {"slot": "Head", "spell_id": 999999},
                 ]}]}
        self.write(self.raw / "phase_enchants/t6.json", phase)
        report = self.audit()
        row = next(row for row in report["coverage"] if row["family"] == "enchants" and row["phase"] == "T6")
        self.assertEqual(row["status"], "partial_phase_guidance_with_general_fallback")
        self.assertEqual(row["phase_enchant_guidance"]["verified_recommendations"], [["Main Hand", "spell", 23800]])
        self.assertEqual(row["phase_enchant_guidance"]["unmapped_application_spell_ids"], [999999])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["phase_enchants"]["acquisition_basis"], "effective_canonical_routes_and_committed_phase_guide_applications")

    def test_nearest_verified_inheritance_rejects_later_and_skipped_origins(self):
        newer = self.guide(self.urls["PR"], "bis_lists", 29124)
        newer.update(content_phase="T6", recommendation_status="verified_phase_update")
        self.write(self.raw / "full_bis/pr-t6.json", newer)
        report = self.audit()
        wrong = [error for error in report["errors"] if error["code"] == "invalid_pre_raid_inheritance"]
        self.assertEqual({error["content_phase"] for error in wrong}, {"T6", "ZA", "SWP"})
        newer["recommendation_status"] = "no_distinct_update"
        self.write(self.raw / "full_bis/pr-t6.json", newer)
        self.assertEqual(self.audit()["errors"], [])
        row = next(row for row in self.records["bis_lists"]["lists"] if row.get("content_phase") == "T5")
        row["inherited_from_phase"] = "T6"
        self.save_records()
        self.assertTrue(any(error["code"] == "invalid_pre_raid_inheritance" for error in self.audit()["errors"]))

    def test_frozen_pre_raid_identity_survives_a_changed_manifest_url(self):
        registration = next(row for row in self.registrations if row.get("phase") == "PR")
        historical = self.guide(self.urls["PR"], "bis_lists", 29124)
        historical.update(content_phase="PR", historical_pre_raid=True,
                          manifest_bindings=[deepcopy(registration)])
        self.write(self.raw / "full_bis/PR.json", historical)
        registration["url"] = "https://www.wowhead.com/tbc/guide/replacement-retribution-pre-raid"
        self.write(self.canonical / "scrape_manifest.json", {"sources": self.registrations})
        report = self.audit()
        self.assertEqual(report["errors"], [])
        coverage = next(row for row in report["coverage"] if row["family"] == "bis_lists" and row["phase"] == "PR")
        self.assertEqual(coverage["status"], "phase_scoped_pre_raid_paths")
        self.assertIn(self.urls["PR"], coverage["source_urls"])
        for row in report["pre_raid"]:
            self.assertEqual(row["source_urls"], [self.urls["PR"]])
            self.assertEqual(row["registered_source_urls"], [registration["url"]])
            self.assertEqual(row["snapshot_paths"], ["data/raw/wowhead/full_bis/PR.json"])

    def test_newest_verified_revision_replaces_old_lineage_and_history_is_inactive(self):
        older = self.guide(self.urls["PR"], "bis_lists", 22838)
        older.update(content_phase="PR", fetched_at="2026-05-24T00:00:00+00:00")
        self.write(self.raw / "full_bis/older-pr.json", older)
        superseded = {**older, "content_phase": "T6", "fetched_at": "2030-01-01T00:00:00+00:00"}
        self.write(self.raw / "full_bis/history/superseded-pr.json", superseded)
        rejected = {**older, "fetched_at": "2031-01-01T00:00:00+00:00", "recommendation_status": "unverified_phase"}
        self.write(self.raw / "full_bis/rejected-pr.json", rejected)
        report = self.audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(all(row["snapshot_paths"] == ["data/raw/wowhead/full_bis/PR.json"] for row in report["pre_raid"]))
        self.assertTrue(all({"content_phase": "PR", "status": "unverified_phase"} in row["refresh_observations"] for row in report["pre_raid"]))
        inherited = next(row for row in self.records["bis_lists"]["lists"] if row.get("content_phase") == "T6")
        inherited["items"].append({"item_id": 22838, "rank": 2})
        self.save_records()
        errors = self.audit()["errors"]
        self.assertEqual([(error["content_phase"], error["item_ids"]) for error in errors
                          if error["code"] == "invalid_pre_raid_lineage"], [("T6", [22838])])

    def test_split_shared_guide_selects_the_newest_revision_for_each_spec(self):
        second_spec = "Protection"
        cloned = [{**deepcopy(row), "id": row["id"] + "-protection", "spec": second_spec} for row in self.registrations]
        original = next(row for row in self.registrations if row.get("phase") == "PR")
        other = next(row for row in cloned if row.get("phase") == "PR")
        historical = self.guide(self.urls["PR"], "bis_lists", 29124)
        historical.update(content_phase="PR", fetched_at="2026-05-24T00:00:00+00:00",
                          historical_pre_raid=True, manifest_bindings=[deepcopy(original), deepcopy(other)])
        self.write(self.raw / "full_bis/PR.json", historical)
        original["url"] = "https://www.wowhead.com/tbc/guide/new-retribution-pre-raid"
        other["url"] = "https://www.wowhead.com/tbc/guide/new-protection-pre-raid"
        self.registrations.extend(cloned)
        self.write(self.canonical / "scrape_manifest.json", {"sources": self.registrations})
        self.write(self.canonical / "classes.json", {"classes": [{"name": "Paladin", "specs": [
            {"name": "Retribution"}, {"name": second_spec}]}]})
        for family, row_key in (("bis_lists", "lists"), ("gems", "gems"), ("enchants", "enchants"), ("consumables", "consumables")):
            rows = self.records[family][row_key]
            rows.extend([{**deepcopy(row), "spec": second_spec} for row in rows])
        for row in self.records["bis_lists"]["lists"]:
            if row["spec"] == "Retribution" and row["phase"] == "PR":
                row["items"] = [{"item_id": 22838, "rank": 1}]
                row["source_url"] = original["url"]
        self.save_records()
        newer = self.guide(original["url"], "bis_lists", 22838)
        newer["content_phase"] = "PR"
        self.write(self.raw / "full_bis/new-retribution-pr.json", newer)
        report = build_progression_audit(self.canonical, self.raw, expected_spec_count=2, reviewed_sources={})
        self.assertEqual(report["errors"], [])
        for row in report["pre_raid"]:
            expected = "PR.json" if row["spec"] == second_spec else "new-retribution-pr.json"
            self.assertEqual(row["snapshot_paths"], ["data/raw/wowhead/full_bis/" + expected])
        # The importer and audit must preserve the same split guide identities.
        from tools.scrape_wowhead import manifest_sources_for_snapshot, select_pre_raid_snapshots
        by_url = {}
        for registration in self.registrations:
            by_url.setdefault(registration["url"], []).append(registration)
        with patch("tools.scrape_wowhead.manifest_sources_by_url", return_value=by_url):
            selected = select_pre_raid_snapshots([historical, newer])
            imported = {binding["spec"]: snapshot["url"] for snapshot in selected
                        for binding in manifest_sources_for_snapshot(snapshot, "bis_lists")}
        audited = {row["spec"]: row["source_urls"][0] for row in report["pre_raid"]}
        self.assertEqual(imported, audited)

    def test_later_item_cannot_be_backfilled_into_an_inherited_snapshot(self):
        evidence = json.loads((ROOT / "data/raw/wowhead/phase_source_evidence/season3_pvp.json").read_text(encoding="utf-8"))
        helm = next(item for item in evidence["items"] if item["item_id"] == 33672)
        self.records["items"]["items"].append({"id": 33672, "name": helm["name"], "binding": "bind_on_pickup",
                                               "sources": [{"type": "pvp", "available_from_phase": helm["content_phase"]}]})
        row = next(row for row in self.records["bis_lists"]["lists"] if row.get("content_phase") == "T6")
        row["items"].append({"item_id": 33672, "rank": 2})
        self.save_records()
        errors = self.audit()["errors"]
        self.assertTrue(any(error["code"] == "invalid_pre_raid_lineage" and error["item_ids"] == [33672] for error in errors))
        self.assertFalse(any(error["code"] == "ineligible_pre_raid_routes" for error in errors))
        row["content_phase"] = "T5"
        self.save_records()
        self.assertTrue(any(error["code"] == "ineligible_pre_raid_routes" for error in self.audit()["errors"]))

    def test_unresolved_enchant_formula_is_missing_required_acquisition(self):
        spell = next(row for row in self.records["enchant_sources"]["enchant_sources"] if row["type"] == "spell")
        spell["sources"][0]["item_id"] = 999999
        self.save_records()
        report = self.audit()
        missing = [error for error in report["errors"] if error["code"] == "missing_acquisition_evidence"]
        self.assertEqual([error["entity_id"] for error in missing], [23800])

    def test_json_check_exit_status_is_driven_by_strict_errors(self):
        report = self.audit()
        with patch("tools.progression_audit.build_progression_audit", return_value=report), patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main(["--check", "--json"]), 0)
            self.assertEqual(json.loads(output.getvalue()), report)
        report["errors"] = [{"code": "fixture_missing_evidence"}]
        target = self.base / "report.json"
        with patch("tools.progression_audit.build_progression_audit", return_value=report):
            self.assertEqual(main(["--check", "--json", str(target)]), 1)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)


if __name__ == "__main__":
    unittest.main()
