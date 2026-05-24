import unittest

from tools.validate_data import validate


class CanonicalDataTests(unittest.TestCase):
    def test_canonical_data_validates(self):
        result = validate()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.summary["classes"], 9)
        self.assertEqual(result.summary["specs"], 28)
        self.assertEqual(result.summary["coverage"], "scraped_snapshot")
