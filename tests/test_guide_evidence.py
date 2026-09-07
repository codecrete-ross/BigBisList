"""Guide comparisons use explicit labels, never source table enumeration."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tools.generate_lua import SCHEMAS, build_uses
from tools.guide_evidence import (committed_guide_snapshots, enrich_document,
                                 table_evidence, validate_evidence)
from tools.project import canonical_json
from tools.scrape_wowhead import import_bis_lists_from_snapshots


URL = "https://www.wowhead.com/tbc/guide/evidence-fixture"


def fixture(labels=("Best", "Great", "Good"), *, phase="T6", heading="Best in Slot Leg Armor"):
    source = {"class": "Warrior", "spec": "Fury", "phase": phase, "data_family": "bis_lists"}
    table = {"data_family": "bis_lists", "slot": "Legs", "heading": heading,
             "rows": [{"item_id": 100 + index, "rank_label": label} for index, label in enumerate(labels)]}
    snapshot = {"page_type": "guide", "url": URL, "tables": [table], "fetched_at": "2026-01-01"}
    document = {"coverage": "fixture", "lists": [
        {"class": "Warrior", "spec": "Fury", "phase": phase, "slot": "Legs", "source_url": URL,
         "items": [{"item_id": row["item_id"], "rank_label": row["rank_label"], "rank": 900 - index,
                    "rank_group": "option", "context": "standard", "note": "Reviewed wording"}
                   for index, row in enumerate(table["rows"])]}]}
    return source, snapshot, document


class GuideEvidenceTests(unittest.TestCase):
    def test_only_explicit_unconditional_labels_have_grades(self):
        _, snapshot, _ = fixture()
        table = snapshot["tables"][0]
        for label, grade in [("BiS", 1), ("Best", 1), ("Best in slot", 1), ("Great", 2),
                             ("Good", 3), ("Mediocre", 4), (" Great ", 2),
                             ("Best Overall", None), ("Best Threat", None), ("Option", None),
                             ("Best PvP", None), ("45 Stamina", None), ("2nd Best", None),
                             ("Great (4 set)", None), ("Best Until Tier 6", None)]:
            with self.subTest(label=label):
                evidence = table_evidence(snapshot, table, 1, {"rank_label": label}, "T6", "Legs")
                self.assertEqual(evidence.get("grade"), grade)
                self.assertEqual(evidence["original_rating"], label)
                self.assertEqual(bool(evidence["conditions"]), grade is None)
                self.assertEqual(validate_evidence([evidence], label, URL), [])

    def test_historical_rating_phase_uses_source_terminology(self):
        _, snapshot, _ = fixture()
        table = snapshot["tables"][0]
        for label, terminology, expected in [("P2 Best", "wowhead_classic", "T5"),
                                              ("P4 BIS", "wowhead_classic", "ZA"),
                                              ("P4 BIS", "anniversary_2026", "SWP"),
                                              ("Tier 5 Best", "wowhead_classic", "T5"),
                                              ("Best Until Tier 6", "wowhead_classic", "T4"),
                                              ("Best Pre-raid", "wowhead_classic", "PR"),
                                              ("P9 Best", "wowhead_classic", None)]:
            evidence = table_evidence(snapshot, table, 1, {"rank_label": label}, "T4", "Legs",
                                      terminology=terminology)
            self.assertEqual(evidence.get("rating_phase"), expected)
            self.assertNotIn("grade", evidence)

    def test_source_row_position_never_controls_grade(self):
        _, snapshot, _ = fixture(("Great", "Good", "Great"))
        table = snapshot["tables"][0]
        values = [table_evidence(snapshot, table, 1, row, "T6", "Legs") for row in table["rows"]]
        self.assertEqual([value["grade"] for value in values], [2, 3, 2])
        self.assertEqual(len({value["table_id"] for value in values}), 1)

    def test_duplicate_heading_tables_have_distinct_comparison_identity(self):
        _, snapshot, _ = fixture()
        table = snapshot["tables"][0]
        first = table_evidence(snapshot, table, 1, table["rows"][0], "T6", "Legs")
        second = table_evidence(snapshot, table, 2, table["rows"][0], "T6", "Legs")
        self.assertNotEqual(first["table_id"], second["table_id"])
        later_fetch = deepcopy(snapshot)
        later_fetch["fetched_at"] = "2026-09-01"
        self.assertEqual(first["table_id"], table_evidence(
            later_fetch, table, 1, table["rows"][0], "T6", "Legs")["table_id"])
        changed = deepcopy(table)
        changed["rows"][1]["rank_label"] = "Mediocre"
        self.assertNotEqual(first["table_id"], table_evidence(
            snapshot, changed, 1, changed["rows"][0], "T6", "Legs")["table_id"])

    def test_setup_specific_table_does_not_create_unconditional_grade(self):
        _, snapshot, _ = fixture(heading="Best in Slot Threat Gear")
        table = snapshot["tables"][0]
        result = table_evidence(snapshot, table, 1, table["rows"][0], "T6", "Legs")
        self.assertNotIn("grade", result)
        self.assertEqual(result["conditions"], [table["heading"]])

    def test_backfill_changes_only_evidence_and_preserves_multiple_matches(self):
        source, snapshot, document = fixture()
        snapshot["tables"].append(deepcopy(snapshot["tables"][0]))
        original = deepcopy(document)
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            enriched, counts = enrich_document(document, [snapshot])
        self.assertEqual(document, original)
        self.assertEqual(counts["multiple_matches"], 3)
        for row in enriched["lists"]:
            for entry in row["items"]:
                self.assertEqual(len(entry.pop("guide_evidence")), 2)
        self.assertEqual(enriched, original)

    def test_unmatched_reviewed_labels_are_not_replaced_or_inferred(self):
        source, snapshot, document = fixture()
        document["lists"][0]["items"][0]["rank_label"] = "Reviewed setup recommendation"
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            enriched, counts = enrich_document(document, [snapshot])
        self.assertNotIn("guide_evidence", enriched["lists"][0]["items"][0])
        self.assertEqual(counts["unresolved"], 1)

    def test_reviewed_setup_context_survives_a_generic_source_label(self):
        source, snapshot, document = fixture()
        document["lists"][0]["items"][0].update(context="party_buff", note="Party-wide aura benefit")
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            enriched, _ = enrich_document(document, [snapshot])
        evidence = enriched["lists"][0]["items"][0]["guide_evidence"][0]
        self.assertNotIn("grade", evidence)
        self.assertEqual(evidence["conditions"], ["Party-wide aura benefit"])

    def test_unverified_snapshot_cannot_supply_comparison_evidence(self):
        source, snapshot, document = fixture()
        snapshot["recommendation_status"] = "unverified_phase"
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            enriched, counts = enrich_document(document, [snapshot])
        self.assertEqual(enriched, document)
        self.assertEqual(counts["unresolved"], 3)

    def test_inherited_pre_raid_retains_original_verified_context(self):
        source, snapshot, document = fixture(phase="PR")
        snapshot["content_phase"] = "T4"
        document["lists"][0].update(content_phase="T6", inherited_from_phase="T4")
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            enriched, _ = enrich_document(document, [snapshot])
        evidence = enriched["lists"][0]["items"][0]["guide_evidence"][0]
        self.assertEqual((evidence["guide_phase"], evidence["rating_phase"], evidence["content_phase"]),
                         ("PR", "PR", "T4"))
        later = deepcopy(snapshot)
        later["content_phase"] = "T6"
        later_evidence = table_evidence(later, later["tables"][0], 1, later["tables"][0]["rows"][0], "PR", "Legs")
        self.assertNotEqual(evidence["table_id"], later_evidence["table_id"])

    def test_normal_import_carries_evidence_without_changing_enumeration(self):
        source, snapshot, _ = fixture(("Great", "Good"))
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            imported = import_bis_lists_from_snapshots([snapshot])
        entries = imported["lists"][0]["items"]
        self.assertEqual([entry["rank"] for entry in entries], [1, 2])
        self.assertEqual([entry["guide_evidence"][0]["grade"] for entry in entries], [2, 3])

    def test_compact_use_schema_preserves_nested_evidence(self):
        source, snapshot, document = fixture()
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            enriched, _ = enrich_document(document, [snapshot])
        use = dict(zip(SCHEMAS["use"], build_uses(enriched["lists"])[0]))
        evidence = dict(zip(SCHEMAS["guide_evidence"], use["guide_evidence"][0]))
        self.assertEqual(evidence, enriched["lists"][0]["items"][0]["guide_evidence"][0] | {"content_phase": None})

    def test_generated_pool_deduplicates_evidence_without_merging_tables(self):
        source, snapshot, document = fixture(("Best", "Best", "Good"))
        snapshot["tables"].append(deepcopy(snapshot["tables"][0]))
        with patch("tools.scrape_wowhead.manifest_sources_for_snapshot", return_value=[source]):
            enriched, _ = enrich_document(document, [snapshot])
        pool = []
        uses = [dict(zip(SCHEMAS["use"], use)) for use in build_uses(enriched["lists"], pool)]
        self.assertEqual(len(pool), 4)
        self.assertEqual(uses[0]["guide_evidence"], uses[1]["guide_evidence"])
        self.assertNotEqual(uses[0]["guide_evidence"], uses[2]["guide_evidence"])
        for source_use, generated_use in zip(enriched["lists"][0]["items"], uses):
            decoded = [dict(zip(SCHEMAS["guide_evidence"], pool[key - 1]))
                       for key in generated_use["guide_evidence"]]
            for entry in decoded:
                entry.pop("content_phase", None)
            self.assertEqual(decoded, source_use["guide_evidence"])

    def test_validator_rejects_fabricated_grade_or_modified_provenance(self):
        _, snapshot, _ = fixture()
        table = snapshot["tables"][0]
        evidence = table_evidence(snapshot, table, 1, {"rank_label": "Option"}, "T6", "Legs")
        evidence["grade"] = 2
        self.assertTrue(validate_evidence([evidence], "Option", URL))
        evidence.pop("grade")
        self.assertTrue(validate_evidence([evidence], "Great", URL))
        self.assertTrue(validate_evidence([evidence], "Option", URL + "/wrong"))


class CommittedGuideEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = canonical_json("bis_lists")
        cls.enriched, cls.counts = enrich_document(cls.original, committed_guide_snapshots())

    def use(self, item_id, phase):
        return next(entry for row in self.enriched["lists"]
                    if (row["class"], row["spec"], row["phase"]) == ("Warrior", "Fury", phase)
                    for entry in row["items"] if entry["item_id"] == item_id)

    def test_committed_great_row_two_is_not_compared_with_good_row_one(self):
        great = self.use(30977, "T6")
        good = self.use(30898, "T6")
        self.assertEqual((great["rank"], good["rank"]), (2, 1))
        self.assertEqual((great["guide_evidence"][0]["grade"], good["guide_evidence"][0]["grade"]), (2, 3))
        self.assertTrue({e["table_id"] for e in great["guide_evidence"]}.isdisjoint(
            {e["table_id"] for e in good["guide_evidence"]}))

    def test_committed_historical_best_remains_historical(self):
        use = self.use(29995, "T6")
        evidence = use["guide_evidence"][0]
        self.assertEqual((use["rank_label"], evidence["original_rating"]), ("P2 Best", "P2 Best"))
        self.assertEqual((evidence["guide_phase"], evidence["rating_phase"]), ("T6", "T5"))
        self.assertNotIn("grade", evidence)

    def test_backfill_preserves_complete_canonical_recommendations(self):
        before, after = deepcopy(self.original), deepcopy(self.enriched)
        for document in (before, after):
            for row in document["lists"]:
                for entry in row["items"]:
                    entry.pop("guide_evidence", None)
        self.assertEqual(before, after)
        self.assertGreater(self.counts["with_evidence"], 27000)
        self.assertGreater(self.counts["unresolved"], 0)


if __name__ == "__main__":
    unittest.main()
