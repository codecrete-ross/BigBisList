import unittest

from tools.project import canonical_json
from tools.validate_data import validate


class CanonicalDataTests(unittest.TestCase):
    def test_canonical_data_validates(self):
        result = validate()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.summary["classes"], 9)
        self.assertEqual(result.summary["specs"], 28)
        self.assertEqual(result.summary["coverage"], "scraped_snapshot")

    def test_feral_dps_phase_2_trinket_regressions(self):
        trinkets = []
        for row in canonical_json("bis_lists")["lists"]:
            if (
                row["class"] == "Druid"
                and row["spec"] == "Feral dps"
                and row["phase"] == "T5"
                and row["slot"] == "Trinket"
            ):
                trinkets.extend(row["items"])

        by_item_id = {entry["item_id"]: entry for entry in trinkets}

        self.assertEqual(by_item_id[29383]["rank_group"], "bis")
        self.assertEqual(by_item_id[29383]["rank_label"], "BiS")
        self.assertEqual(by_item_id[28034]["rank_group"], "option")
        self.assertEqual(by_item_id[28034]["rank_label"], "Close Second")

        all_rank_ids = {entry["item_id"] for entry in trinkets}
        bis_rank_ids = {
            entry["item_id"]
            for entry in trinkets
            if entry.get("rank_group") == "bis"
        }

        self.assertIn(29383, all_rank_ids)
        self.assertIn(28034, all_rank_ids)
        self.assertIn(29383, bis_rank_ids)
        self.assertNotIn(28034, bis_rank_ids)

    def test_canonical_items_do_not_have_unknown_primary_sources(self):
        unknown_source_items = [
            item["id"]
            for item in canonical_json("items")["items"]
            if item["primary_source"]["type"] == "unknown"
        ]
        self.assertEqual(unknown_source_items, [])
