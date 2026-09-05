from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.scrape_wowhead import import_entity_sources_from_snapshots
from tools.sources import source_is_phase_available


def captured(kind: str, entity_id: int) -> dict:
    paths = sorted((ROOT / "data/raw/wowhead/full_enchants").glob(f"*{kind}-{entity_id}-*.json"))
    observations = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    return max((snapshot for snapshot in observations if snapshot.get(kind + "_id") == entity_id),
               key=lambda snapshot: len(snapshot.get("normalized_sources", [])))


class EnchantAliasSourceTests(unittest.TestCase):
    def test_committed_effect_alias_retains_its_identity_and_actual_formula(self):
        linked, learned, formula = captured("spell", 46540), captured("spell", 27981), captured("item", 22560)
        self.assertFalse(linked.get("normalized_sources"))
        self.assertTrue(learned.get("normalized_sources"))
        snapshots = [linked, learned, formula]
        original = deepcopy(snapshots)
        row = {"id": 46540, "type": "spell", "name": linked["name"], "source_spell_id": 27981,
               "formula_item_ids": [22560]}
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            result = import_entity_sources_from_snapshots(snapshots, [row], "enchant_sources")
        records = {(record["type"], record["id"]): record for record in result["enchant_sources"]}
        enchant = records[("spell", 46540)]
        self.assertNotIn(("spell", 27981), records)
        self.assertEqual(enchant["source_url"], linked["url"])
        self.assertEqual(enchant["name"], linked["name"])
        teacher = next(source for source in enchant["sources"] if source.get("item_id") == 22560)
        self.assertTrue(teacher["recipe_sources"])
        self.assertEqual(teacher["recipe_sources"], records[("item", 22560)]["sources"])
        self.assertFalse(source_is_phase_available(teacher, "PR"))
        self.assertTrue(source_is_phase_available(teacher, "T4"))
        self.assertEqual(snapshots, original)

    def test_recipe_identity_resolves_without_recommendation_mapping_or_spell_relations(self):
        linked, learned, formula = captured("spell", 46540), captured("spell", 27981), captured("item", 22560)
        learned["normalized_sources"] = []
        self.assertIn(27981, formula["teaches_spell_ids"])
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            result = import_entity_sources_from_snapshots([linked, learned, formula],
                [{"id": 46540, "type": "spell", "name": linked["name"]}], "enchant_sources")
        enchant = next(record for record in result["enchant_sources"] if record["id"] == 46540)
        self.assertEqual(enchant["sources"][0]["item_id"], 22560)
        self.assertTrue(enchant["sources"][0]["recipe_sources"])

    def test_actual_spell_reviewed_window_survives_public_alias(self):
        linked, learned, formula = captured("spell", 46540), captured("spell", 27981), captured("item", 22560)
        window = {"id": "fixture-reviewed-source-window", "type": "source_rules", "target": {"spell_id": 27981},
                  "data": {"rules": [{"match": {}, "set": {"available_from_phase": "T6", "available_until_phase": "SWP"}}]}}
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[window]):
            result = import_entity_sources_from_snapshots([linked, learned, formula],
                [{"id": 46540, "type": "spell", "source_spell_id": 27981}], "enchant_sources")
        enchant = next(record for record in result["enchant_sources"] if record["id"] == 46540)
        for source in enchant["sources"]:
            self.assertFalse(source_is_phase_available(source, "T5"))
            self.assertTrue(source_is_phase_available(source, "T6"))
            self.assertTrue(source_is_phase_available(source, "ZA"))
            self.assertFalse(source_is_phase_available(source, "SWP"))

    def test_trainer_taught_alias_uses_captured_trainer_evidence(self):
        linked, learned = captured("spell", 46504), captured("spell", 33990)
        self.assertTrue(learned.get("normalized_sources"))
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            result = import_entity_sources_from_snapshots([linked, learned],
                [{"id": 46504, "type": "spell", "source_spell_id": 33990}], "enchant_sources")
        enchant = next(record for record in result["enchant_sources"] if record["id"] == 46504)
        self.assertEqual(enchant["sources"], learned["normalized_sources"])


if __name__ == "__main__":
    unittest.main()
