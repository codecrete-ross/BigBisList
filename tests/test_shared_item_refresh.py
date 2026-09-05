import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import scrape_wowhead as scraper
from tools.sources import source_is_phase_available


class SharedItemRefreshTests(unittest.TestCase):
    def test_item_fact_import_does_not_run_or_replace_ranking_imports(self):
        document = {"item_stats": [{"id": 1, "name": "Fixture"}]}
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            rankings = root / "leveling_recommendations.json"
            rankings.write_text('{"leveling_recommendations": ["unchanged"]}', encoding="utf-8")
            original = rankings.read_bytes()
            with patch.object(scraper, "CANONICAL_DIR", root), \
                 patch.object(scraper, "load_import_snapshots", return_value=[]), \
                 patch.object(scraper, "import_item_stats_from_snapshots", return_value=document), \
                 patch.object(scraper, "import_items_from_snapshots", side_effect=AssertionError("unrelated import")), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scraper.command_import(SimpleNamespace(input_dir=root, family="item_stats", dry_run=False)), 0)
            self.assertEqual(json.loads((root / "item_stats.json").read_text(encoding="utf-8")), document)
            self.assertEqual(rankings.read_bytes(), original)

    def test_shared_corpus_applies_reviewed_season_three_route_windows(self):
        source = {"type": "pvp", "entity_id": 18898, "entity_name": "Explodyne Fizzlespurt", "zone": "Nagrand"}
        snapshot = {"page_type": "item", "item_id": 33672, "name": "Vengeful Gladiator's Dragonhide Helm",
                    "normalized_sources": [source], "item_stats": {
                        "id": 33672, "name": "Vengeful Gladiator's Dragonhide Helm", "slot": "Head",
                        "quality": "epic", "stats": {"agility": 33}, "sources": [source]}}
        row = scraper.import_item_stats_from_snapshots([snapshot])["item_stats"][0]
        self.assertEqual(row["phase"], "T6")
        self.assertTrue(any(source_is_phase_available(route, "T6") for route in row["sources"]))
        self.assertFalse(any(source_is_phase_available(route, "T5") for route in row["sources"]))


if __name__ == "__main__":
    unittest.main()
