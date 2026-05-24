import unittest

from tools.manifest_coverage import build_manifest_coverage, expected_manifest_units, units_covered_by_source


class ManifestCoverageTests(unittest.TestCase):
    def test_expected_manifest_units_cover_every_static_data_family(self):
        units = expected_manifest_units()
        self.assertEqual(len(units), 842)
        self.assertEqual(sum(1 for unit in units if unit["data_family"] == "bis_lists"), 168)
        self.assertEqual(sum(1 for unit in units if unit["data_family"] == "gems"), 168)
        self.assertEqual(sum(1 for unit in units if unit["data_family"] == "classes"), 1)
        self.assertEqual(sum(1 for unit in units if unit["data_family"] == "phases"), 1)

    def test_current_manifest_reports_known_seed_level_gap_without_fetching(self):
        coverage = build_manifest_coverage(include_missing=False)
        self.assertFalse(coverage["ok"])
        self.assertEqual(coverage["expected_units"], 842)
        self.assertEqual(coverage["present_units"], 168)
        self.assertEqual(coverage["missing_units"], 674)
        self.assertEqual(coverage["by_family"]["bis_lists"]["present"], 168)
        self.assertEqual(coverage["by_family"]["bis_lists"]["missing"], 0)
        self.assertEqual(coverage["by_family"]["gems"]["missing"], 168)

    def test_manifest_coverage_can_be_filtered_to_bis_lists(self):
        coverage = build_manifest_coverage(include_missing=False, family_filter="bis_lists")
        self.assertTrue(coverage["ok"])
        self.assertEqual(coverage["family"], "bis_lists")
        self.assertEqual(coverage["expected_units"], 168)
        self.assertEqual(coverage["present_units"], 168)
        self.assertEqual(coverage["missing_units"], 0)

    def test_manifest_source_can_cover_multiple_phases_explicitly(self):
        source = {
            "id": "druid-balance-gems",
            "url": "https://www.wowhead.com/tbc/guide/example",
            "data_family": "gems",
            "class": "Druid",
            "spec": "Balance",
            "phases": ["PR", "T4", "T5", "T6", "ZA", "SWP"],
        }
        units = units_covered_by_source(source)
        self.assertEqual(len(units), 6)
        self.assertEqual({unit["phase"] for unit in units}, {"PR", "T4", "T5", "T6", "ZA", "SWP"})


if __name__ == "__main__":
    unittest.main()
