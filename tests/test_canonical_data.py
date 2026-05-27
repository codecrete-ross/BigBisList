import unittest

from tools.project import canonical_json
from tools.reputations import CANONICAL_REPUTATIONS, normalize_reputation_names
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

    def iter_requirements(self):
        for family in ["items", "gems", "gem_sources", "enchants", "enchant_sources", "consumables"]:
            doc = canonical_json(family)
            stack = [doc]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    if value.get("type") in {"reputation", "faction_choice"}:
                        yield value
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)

    def test_reputation_requirements_use_canonical_names(self):
        allowed = set(CANONICAL_REPUTATIONS)
        seen = set()
        for requirement in self.iter_requirements():
            if requirement["type"] == "reputation":
                reputation = requirement["reputation"]
                self.assertIn(reputation, allowed)
                seen.add(reputation)
            elif requirement["type"] == "faction_choice":
                for choice in requirement["choices"]:
                    self.assertIn(choice, allowed)
                    seen.add(choice)

        self.assertEqual(seen, allowed)

    def test_reputation_aliases_normalize_and_split(self):
        cases = {
            "Scale of the Sands": ["The Scale of the Sands"],
            "the Scales of the Sand": ["The Scale of the Sands"],
            "Keepers of TIme": ["Keepers of Time"],
            "The Keepers of Time": ["Keepers of Time"],
            "The Shat'tar": ["The Sha'tar"],
            "The Kurenai": ["Kurenai"],
            "Classic - Cenarion Circle": ["Cenarion Circle"],
            "Honor Hold / Thrallmar": ["Honor Hold", "Thrallmar"],
            "Thrallmar / Honor Hold": ["Thrallmar", "Honor Hold"],
            "Honor Hold / Thrallmar (BoE": ["Honor Hold", "Thrallmar"],
            "The Mag'har / Kurenai": ["The Mag'har", "Kurenai"],
        }
        for raw, expected in cases.items():
            self.assertEqual(normalize_reputation_names(raw), expected)
