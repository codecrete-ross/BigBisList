import unittest

from tools.reference_counts import EXPECTED_BASELINE, baseline_matches, collect_counts


class ReferenceCountTests(unittest.TestCase):
    def test_reference_counts_match_key_baseline(self):
        counts = collect_counts()
        self.assertIs(counts["available"], True)
        self.assertEqual(counts["toc_version"], "1.15")
        for key, value in EXPECTED_BASELINE.items():
            self.assertEqual(counts[key], value)
        self.assertTrue(baseline_matches(counts))
