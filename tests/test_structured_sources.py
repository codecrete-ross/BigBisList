import unittest
from types import SimpleNamespace

import tools.scrape_wowhead as scraper
from tools.project import canonical_json
from tools.scrape_wowhead import build_audit
from tools.sources import phase_rank, summarize_sources


class StructuredSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = {item["id"]: item for item in canonical_json("items")["items"]}

    def test_source_summary_is_derived_for_every_item(self):
        for item in self.items.values():
            self.assertEqual(item["source_summary"], summarize_sources(item["sources"]))

    def test_avian_heart_has_moroes_karazhan_source(self):
        item = self.items[28568]
        source = item["primary_source"]
        self.assertEqual(source["type"], "drop")
        self.assertEqual(source["entity_name"], "Moroes")
        self.assertEqual(source["zone"], "Karazhan")

    def test_avenger_keeps_both_faction_quest_sources(self):
        item = self.items[31025]
        quest_ids = {source["quest_id"] for source in item["sources"]}
        sides = {source["side"] for source in item["sources"]}
        self.assertEqual(quest_ids, {10744, 10745})
        self.assertEqual(sides, {"Alliance", "Horde"})
        self.assertEqual(item["source_summary"], "Quest: News of Victory +1")

    def test_pvp_idols_keep_multiple_vendors_and_costs(self):
        item = self.items[33946]
        self.assertGreaterEqual(len(item["sources"]), 2)
        cost_names = {cost["name"] for source in item["sources"] for cost in source.get("costs", [])}
        self.assertIn("Arena Points", cost_names)
        self.assertIn("Honor Points", cost_names)

    def test_acquisition_phase_covers_raid_and_pre_raid_edge_cases(self):
        gladiator = self.items[28137]
        self.assertEqual(gladiator["primary_source"]["type"], "pvp")
        self.assertEqual(gladiator["acquisition_phase"], "PR")
        self.assertTrue(gladiator["source_summary"].startswith("PvP: "))

        tier = self.items[31037]
        self.assertEqual(tier["primary_source"]["type"], "token_turnin")
        self.assertEqual(tier["acquisition_phase"], "T6")

        zulaman = self.items[33214]
        self.assertEqual(zulaman["primary_source"]["zone"], "Zul'Aman")
        self.assertEqual(zulaman["acquisition_phase"], "ZA")
        self.assertIn("Zul'Aman", zulaman["source_summary"])

        self.assertEqual(self.items[31461]["acquisition_phase"], "PR")
        self.assertEqual(self.items[29290]["acquisition_phase"], "T4")

    def test_bis_rows_do_not_reference_future_acquisitions(self):
        violations = []
        for row in canonical_json("bis_lists")["lists"]:
            row_phase = row["phase"]
            for entry in row["items"]:
                item = self.items[entry["item_id"]]
                acquisition_phase = item["acquisition_phase"]
                if phase_rank(acquisition_phase) > phase_rank(row_phase):
                    violations.append(
                        f"{row['class']}/{row['spec']}/{row_phase}/{row['slot']}: "
                        f"{entry['item_id']} {item['name']} acquires in {acquisition_phase}"
                    )
        self.assertEqual(violations, [])

    def test_source_summary_formats_key_source_types(self):
        self.assertEqual(
            summarize_sources(
                [
                    {
                        "type": "drop",
                        "entity_name": "Moroes",
                        "zone": "Karazhan",
                        "drop_percent": 16.74,
                        "confidence": "fixture",
                    }
                ]
            ),
            "Drop: Moroes (Karazhan) 16.7%",
        )
        self.assertEqual(
            summarize_sources(
                [
                    {
                        "type": "vendor",
                        "entity_name": "G'eras",
                        "costs": [{"amount": 20, "name": "Badge of Justice", "currency_id": 29434}],
                        "confidence": "fixture",
                    }
                ]
            ),
            "Vendor: G'eras (20 Badge of Justice)",
        )
        self.assertEqual(
            summarize_sources(
                [
                    {
                        "type": "pvp",
                        "entity_name": "Explodyne Fizzlespurt",
                        "costs": [{"amount": 370, "name": "Arena Points", "currency_id": 1900}],
                        "confidence": "fixture",
                    }
                ]
            ),
            "PvP: Explodyne Fizzlespurt (370 Arena Points)",
        )
        self.assertEqual(
            summarize_sources([{"type": "world_drop", "entity_name": "World Drop", "world_drop": True, "confidence": "fixture"}]),
            "World Drop",
        )
        self.assertEqual(
            summarize_sources(
                [
                    {
                        "type": "token_turnin",
                        "entity_name": "Tydormu",
                        "costs": [{"amount": 1, "name": "Helm of the Forgotten Protector", "item_id": 31095}],
                        "token_sources": [
                            {
                                "type": "drop",
                                "entity_name": "Archimonde",
                                "zone": "Hyjal Summit",
                                "drop_percent": 55.6,
                                "token_item_id": 31095,
                                "token_name": "Helm of the Forgotten Protector",
                                "token_count": 1,
                                "confidence": "fixture",
                            }
                        ],
                        "confidence": "fixture",
                    }
                ]
            ),
            "Token: Helm of the Forgotten Protector - Archimonde (Hyjal Summit) 55.6%",
        )

    def test_scrape_audit_passes_seed_structured_data(self):
        audit = build_audit()
        self.assertTrue(audit["ok"], audit["errors"])

    def test_scrape_audit_fails_unresolved_item_cost_vendor_source(self):
        audit = self._audit_with_fake_docs(
            items=[
                {
                    "id": 31037,
                    "sources": [
                        {
                            "type": "vendor",
                            "entity_name": "Tydormu",
                            "costs": [{"amount": 1, "name": "Helm of the Forgotten Protector", "item_id": 31095}],
                            "confidence": "fixture",
                        }
                    ],
                }
            ],
            bis_items=[{"item_id": 31037, "context": "standard"}],
        )
        self.assertFalse(audit["ok"])
        self.assertIn("BiS item 31037 has unresolved item-cost vendor source", audit["errors"])

    def test_scrape_audit_fails_bis_item_without_source(self):
        audit = self._audit_with_fake_docs(
            items=[{"id": 1, "sources": []}],
            bis_items=[{"item_id": 1, "context": "standard"}],
        )
        self.assertFalse(audit["ok"])
        self.assertIn("BiS item 1 has no structured acquisition source", audit["errors"])

    def test_scrape_audit_fails_duplicate_item_context(self):
        audit = self._audit_with_fake_docs(
            items=[
                {
                    "id": 1,
                    "sources": [{"type": "drop", "entity_name": "Moroes", "confidence": "fixture"}],
                }
            ],
            bis_items=[{"item_id": 1, "context": "standard"}, {"item_id": 1, "context": "standard"}],
        )
        self.assertFalse(audit["ok"])
        self.assertIn("Duplicate BiS item/context: 1/standard", audit["errors"])

    def test_snapshot_audit_fails_missing_item_snapshot(self):
        guide = {
            "parser_version": "fixture",
            "page_type": "guide",
            "url": "https://www.wowhead.com/tbc/guide/synthetic",
            "tables": [
                {
                    "slot": "Head",
                    "data_family": "bis_lists",
                    "rows": [
                        {
                            "item_id": 1,
                            "rank_label": "BiS",
                            "entities": [{"type": "item", "id": 1, "name": "Missing", "url": "https://www.wowhead.com/tbc/item=1"}],
                        }
                    ],
                }
            ],
        }
        audit = self._snapshot_audit_with_fake_docs([guide])
        self.assertFalse(audit["ok"])
        self.assertIn("Missing item snapshot for BiS item 1: https://www.wowhead.com/tbc/item=1", audit["errors"])

    def test_snapshot_audit_fails_unreviewed_unknown_source(self):
        guide = {
            "parser_version": "fixture",
            "page_type": "guide",
            "url": "https://www.wowhead.com/tbc/guide/synthetic",
            "tables": [
                {
                    "slot": "Head",
                    "data_family": "bis_lists",
                    "rows": [
                        {
                            "item_id": 1,
                            "rank_label": "BiS",
                            "entities": [{"type": "item", "id": 1, "name": "Unknown", "url": "https://www.wowhead.com/tbc/item=1"}],
                        }
                    ],
                }
            ],
        }
        item = {
            "parser_version": "fixture",
            "page_type": "item",
            "url": "https://www.wowhead.com/tbc/item=1",
            "item_id": 1,
            "name": "Unknown",
            "quality": "epic",
            "binding": "unknown",
            "boe": None,
            "normalized_sources": [{"type": "unknown", "entity_name": "Unknown", "confidence": "fixture", "source_url": "https://www.wowhead.com/tbc/item=1"}],
        }
        audit = self._snapshot_audit_with_fake_docs([guide, item])
        self.assertFalse(audit["ok"])
        self.assertIn("BiS item 1 has unreviewed unknown acquisition source", audit["errors"])

    def test_snapshot_audit_guide_only_passes_with_guide_rows(self):
        guide = {
            "parser_version": "fixture",
            "page_type": "guide",
            "url": "https://www.wowhead.com/tbc/guide/synthetic",
            "tables": [
                {
                    "slot": "Head",
                    "data_family": "bis_lists",
                    "rows": [
                        {
                            "item_id": 1,
                            "rank_label": "BiS",
                            "entities": [{"type": "item", "id": 1, "name": "Head", "url": "https://www.wowhead.com/tbc/item=1"}],
                        }
                    ],
                }
            ],
        }
        audit = self._snapshot_audit_with_fake_docs([guide], guide_only=True)
        self.assertTrue(audit["ok"], audit["errors"])

    def test_requirements_audit_flags_requirement_text_without_normalized_requirement(self):
        original_load_snapshots = scraper.load_snapshots
        guide = {
            "parser_version": "fixture",
            "page_type": "guide",
            "url": "https://www.wowhead.com/tbc/guide/synthetic",
            "tables": [
                {
                    "slot": "Head",
                    "data_family": "bis_lists",
                    "rows": [
                        {
                            "item_id": 1,
                            "entity_name": "Rep Helm",
                            "source_text": "Vendor: Nakodu - Requires Exalted with Lower City",
                            "entities": [{"type": "item", "id": 1, "name": "Rep Helm", "url": "https://www.wowhead.com/tbc/item=1"}],
                        }
                    ],
                }
            ],
        }
        scraper.load_snapshots = lambda _path: [guide]
        try:
            audit = scraper.build_requirements_audit(SimpleNamespace(), "bis_lists")
        finally:
            scraper.load_snapshots = original_load_snapshots
        self.assertFalse(audit["ok"])
        self.assertIn("Requirement-looking source text without normalized requirement", audit["errors"][0])

    def _audit_with_fake_docs(self, items, bis_items):
        original_validate = scraper.validate
        original_canonical_json = scraper.canonical_json

        def fake_canonical_json(name):
            if name == "items":
                return {"items": items}
            if name == "bis_lists":
                return {"lists": [{"items": bis_items}]}
            return original_canonical_json(name)

        scraper.validate = lambda: SimpleNamespace(errors=[], summary={})
        scraper.canonical_json = fake_canonical_json
        try:
            return scraper.build_audit()
        finally:
            scraper.validate = original_validate
            scraper.canonical_json = original_canonical_json

    def _snapshot_audit_with_fake_docs(self, snapshots, guide_only=False):
        original_load_snapshots = scraper.load_snapshots
        original_canonical_json = scraper.canonical_json
        original_manifest_sources_by_url = scraper.manifest_sources_by_url

        source = {
            "id": "synthetic",
            "url": "https://www.wowhead.com/tbc/guide/synthetic",
            "data_family": "bis_lists",
            "class": "Druid",
            "spec": "Balance",
            "phase": "SWP",
            "status": "fixture",
        }

        def fake_canonical_json(name):
            if name == "scrape_manifest":
                return {"sources": [source]}
            if name == "items":
                return {"items": []}
            if name == "overrides":
                return {"overrides": []}
            return original_canonical_json(name)

        scraper.load_snapshots = lambda _path: snapshots
        scraper.canonical_json = fake_canonical_json
        scraper.manifest_sources_by_url = lambda: {source["url"]: [source]}
        try:
            return scraper.build_snapshot_audit(SimpleNamespace(), "bis_lists", guide_only=guide_only)
        finally:
            scraper.load_snapshots = original_load_snapshots
            scraper.canonical_json = original_canonical_json
            scraper.manifest_sources_by_url = original_manifest_sources_by_url
