from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from phase_source_overrides import (  # noqa: E402
    EVIDENCE_DIR,
    apply_source_rule_overrides,
    potion_purchase_overrides,
    reviewed_source_overrides,
    source_review_audit,
)
from sources import item_has_pre_raid_route, source_is_phase_available  # noqa: E402


class PhaseSourceOverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = reviewed_source_overrides()
        cls.evidence = json.loads((EVIDENCE_DIR / "season3_pvp.json").read_text(encoding="utf-8"))

    def test_mark_purchases_append_without_restricting_crafting_or_use(self):
        for item_id in (22838, 22839):
            item = {"id": item_id, "acquisition_phase": "PR", "sources": [
                {"type": "crafted", "profession": "Alchemy", "entity_name": "Alchemy"},
            ]}
            original = deepcopy(item)
            result = apply_source_rule_overrides(item, self.records)
            self.assertEqual(item, original)
            self.assertEqual(result["sources"][0], original["sources"][0])
            self.assertEqual(result["acquisition_phase"], "PR")
            self.assertNotIn("requirements", result)
            vendors = [source for source in result["sources"] if source["type"] == "vendor"]
            self.assertEqual({source["vendor_id"] for source in vendors}, {23483, 23484})
            for source in vendors:
                self.assertEqual(source["purchase_quantity"], 10)
                self.assertEqual(source["costs"], [{"item_id": 32897, "name": "Mark of the Illidari", "amount": 1}])
                self.assertFalse(source_is_phase_available(source, "T5"))
                self.assertTrue(source_is_phase_available(source, "T6"))
                self.assertEqual(len(source["requirements"]), 3)
                self.assertTrue(all(requirement["standing_rank"] == 8 for requirement in source["requirements"]))
                self.assertTrue(all(requirement["scope"] == "vendor_purchase" for requirement in source["requirements"]))
                expected_side = "The Scryers" if source["vendor_id"] == 23483 else "The Aldor"
                self.assertEqual({requirement["reputation"] for requirement in source["requirements"]},
                                 {"The Sha'tar", "Cenarion Expedition", expected_side})
            self.assertEqual(apply_source_rule_overrides(result, self.records), result)

    def _vengeful_helm(self):
        evidence = next(item for item in self.evidence["items"] if item["item_id"] == 33672)
        sources = [{"type": "pvp", "entity_id": variant["vendor_id"], "entity_name": variant["vendor_name"],
                    "zone": variant["zone"], "costs": variant["costs"]}
                   for variant in evidence["observed_price_variants"]]
        sources.append({
            "type": "token_turnin", "entity_name": "Soryn", "zone": "Isle of Quel'Danas",
            "costs": [{"item_id": 31096, "name": "Helm of the Forgotten Vanquisher", "amount": 1}],
            "token_sources": [{"type": "drop", "entity_name": "Archimonde", "zone": "Hyjal Summit"}],
        })
        return {"id": 33672, "binding": "bind_on_pickup", "boe": False, "acquisition_phase": "PR", "sources": sources}

    def test_season3_pvp_requires_t6_and_undated_discounts_do_not_leak(self):
        original = self._vengeful_helm()
        self.assertEqual({cost["amount"] for source in original["sources"] if source["type"] == "pvp"
                          for cost in source["costs"]}, {620, 1245, 1550})
        result = apply_source_rule_overrides(original, self.records)
        self.assertEqual(result["acquisition_phase"], "T6")
        self.assertFalse(item_has_pre_raid_route(result, "T5"))
        self.assertTrue(item_has_pre_raid_route(result, "T6"))
        for source in result["sources"]:
            if source["type"] == "pvp":
                self.assertNotIn("costs", source)
                self.assertTrue(source_is_phase_available(source, "T6"))
        self.assertEqual(apply_source_rule_overrides(result, self.records), result)

    def test_raid_token_exchanges_wait_for_the_seller_even_when_token_exists(self):
        result = apply_source_rule_overrides(self._vengeful_helm(), self.records)
        token = next(source for source in result["sources"] if source["type"] == "token_turnin")
        self.assertFalse(source_is_phase_available(token, "T6"))
        self.assertFalse(source_is_phase_available(token, "ZA"))
        self.assertTrue(source_is_phase_available(token, "SWP"))
        only_token = {**result, "sources": [token]}
        self.assertFalse(item_has_pre_raid_route(only_token, "SWP"))
        self.assertEqual(token["costs"][0]["amount"], 1)

    def test_named_content_override_wins_over_inconsistent_phase_number(self):
        ring = next(item for item in self.evidence["items"] if item["item_id"] == 33919)
        self.assertEqual(ring["item_observation"]["reported_phase"], 4)
        self.assertEqual(ring["content_phase"], "T6")
        result = apply_source_rule_overrides({"id": 33919, "sources": [{"type": "pvp", "entity_name": "Brave Stonehide"}]}, self.records)
        self.assertTrue(source_is_phase_available(result["sources"][0], "T6"))
        self.assertEqual(result["sources"][0]["costs"], [
            {"currency_id": 1901, "name": "Honor Points", "amount": 12695},
            {"item_id": 20560, "name": "Alterac Valley Mark of Honor", "amount": 5},
        ])
        later_neck = apply_source_rule_overrides({"id": 35319, "sources": [{"type": "pvp"}]}, self.records)
        self.assertFalse(source_is_phase_available(later_neck["sources"][0], "T6"))
        self.assertTrue(source_is_phase_available(later_neck["sources"][0], "ZA"))

    def test_unrelated_vindicator_reputation_items_are_unchanged(self):
        for item_id in (29124, 29127):
            item = {"id": item_id, "name": "Vindicator's Brand", "sources": [{"type": "vendor", "entity_name": "Quartermaster Endarin"}]}
            self.assertEqual(apply_source_rule_overrides(item, self.records), item)

    def test_nested_windows_survive_item_and_spell_source_records(self):
        entity = {"id": 99, "sources": [{"type": "crafted", "recipe_sources": [{
            "type": "vendor", "zone": "Isle of Quel'Danas", "available_from_phase": "SWP",
        }, {"type": "vendor", "zone": "Shattrath City", "available_from_phase": "T6", "available_until_phase": "SWP"}]}]}
        override = {"id": "test-reviewed-recipe-window", "type": "source_rules", "target": {"spell_id": 99}, "data": {"rules": [{
            "match": {"type": "vendor"}, "set": {"available_from_phase": "T5"}, "recursive": True,
        }]}}
        self.assertEqual(apply_source_rule_overrides(entity, [override], entity_kind="item"), entity)
        result = apply_source_rule_overrides(entity, [override], entity_kind="spell")
        recipes = result["sources"][0]["recipe_sources"]
        self.assertEqual(recipes[0]["available_from_phase"], "SWP")
        self.assertEqual(recipes[1]["available_from_phase"], "T6")
        self.assertEqual(recipes[1]["available_until_phase"], "SWP")
        self.assertTrue(source_is_phase_available(recipes[1], "ZA"))
        self.assertFalse(source_is_phase_available(recipes[1], "SWP"))

    def test_old_reputation_recipe_vendors_wait_for_the_new_recipe(self):
        evidence = json.loads((EVIDENCE_DIR / "profession_phase3.json").read_text(encoding="utf-8"))
        for recipe in evidence["recipes"]:
            if not recipe.get("reputation"):
                continue
            original = {"id": recipe["item_id"], "sources": [{
                "type": "vendor", "entity_name": recipe.get("vendor_name", "Reputation Quartermaster"),
                "zone": recipe.get("vendor_zone", "Shattrath City"),
            }]}
            result = apply_source_rule_overrides(original, self.records)
            source = result["sources"][0]
            self.assertFalse(source_is_phase_available(source, "T5"), recipe["name"])
            self.assertTrue(source_is_phase_available(source, "T6"), recipe["name"])
            self.assertEqual(source["requirements"][0]["reputation"], recipe["reputation"])
            self.assertNotIn("requirements", result)
            self.assertEqual(apply_source_rule_overrides(result, self.records), result)
            source["requirements"][0]["confidence"] = "reviewed_override"
            repaired = apply_source_rule_overrides(result, self.records)
            self.assertEqual(repaired["sources"][0]["requirements"][0]["confidence"], "manual_review")
        ring_enchant = {"id": 27927, "sources": [{"type": "crafted", "recipe_sources": [{
            "type": "vendor", "item_id": 22538, "zone": "Shattrath City", "entity_name": "Nakodu",
        }]}]}
        result = apply_source_rule_overrides(ring_enchant, self.records, entity_kind="spell")
        self.assertFalse(source_is_phase_available(result["sources"][0], "T5"))
        self.assertTrue(source_is_phase_available(result["sources"][0], "T6"))
        self.assertEqual(result["sources"][0]["recipe_sources"][0]["requirements"][0]["standing"], "Honored")

    def test_purchased_raid_patterns_enable_personal_crafting_without_unbinding_shoulders(self):
        evidence = json.loads((EVIDENCE_DIR / "profession_phase3.json").read_text(encoding="utf-8"))
        for recipe in evidence["recipes"]:
            if not recipe.get("raid_pattern"):
                continue
            original = {"id": recipe["product_id"], "binding": recipe["product_binding"],
                        "boe": recipe["product_binding"] == "bind_on_equip", "sources": [{
                            "type": "crafted", "zone": "Black Temple", "recipe_sources": [{
                                "type": "drop", "item_id": recipe["item_id"], "entity_name": recipe["name"],
                                "zone": "Black Temple",
                            }],
                        }]}
            result = apply_source_rule_overrides(original, self.records)
            self.assertFalse(item_has_pre_raid_route(result, "T5"), recipe["name"])
            self.assertTrue(item_has_pre_raid_route(result, "T6"), recipe["name"])
            self.assertNotIn("tradeable", result)
            self.assertNotIn("tradeable", result["sources"][0])
            self.assertEqual(result["binding"], original["binding"])
            pattern = result["sources"][0]["recipe_sources"][0]
            self.assertEqual(pattern.get("tradeable", False), recipe["binding"] == "unbound")
        token = {"id": 999, "sources": [{"type": "token_turnin", "token_sources": [
            {"type": "drop", "item_id": 32755, "zone": "Black Temple"},
        ]}]}
        result = apply_source_rule_overrides(token, self.records)
        self.assertNotIn("tradeable", result["sources"][0]["token_sources"][0])

    def test_chromatic_wonder_and_new_ammunition_do_not_use_earlier_seller_unlocks(self):
        flask = {"id": 33208, "sources": [{"type": "crafted", "recipe_sources": [{
            "type": "vendor", "item_id": 33209, "entity_name": "Apprentice Darius", "zone": "Deadwind Pass",
        }]}]}
        result = apply_source_rule_overrides(flask, self.records)
        self.assertFalse(item_has_pre_raid_route(result, "T5"))
        self.assertTrue(item_has_pre_raid_route(result, "T6"))
        for item_id in (31735, 31737, 34581, 34582):
            result = apply_source_rule_overrides({"id": item_id, "sources": [{"type": "vendor", "zone": "Shattrath City"}]}, self.records)
            self.assertFalse(source_is_phase_available(result["sources"][0], "T5"))
            self.assertTrue(source_is_phase_available(result["sources"][0], "T6"))
            self.assertFalse(item_has_pre_raid_route(result, "T6"))

    def test_reviewed_entity_tradeability_preserves_binding_and_identity(self):
        entity = {"id": 32194, "name": "Delicate Crimson Spinel", "binding": "unbound", "boe": False,
                  "sources": [{"type": "crafted", "available_from_phase": "T6"}]}
        override = {"id": "test-unbound-cut", "type": "source_rules", "target": {"item_id": 32194},
                    "data": {"set_fields": {"tradeable": True}}}
        result = apply_source_rule_overrides(entity, [override])
        self.assertTrue(result["tradeable"])
        self.assertEqual(result["binding"], "unbound")
        self.assertFalse(result["boe"])
        self.assertEqual(result["id"], entity["id"])
        self.assertEqual(apply_source_rule_overrides(result, [override]), result)
        invalid = {**override, "data": {"set_fields": {"id": 42}}}
        with self.assertRaises(ValueError):
            apply_source_rule_overrides(entity, [invalid])

    def test_reviewed_unbound_enhancements_keep_their_recipe_phase_gates(self):
        evidence = json.loads((EVIDENCE_DIR / "tradeable_enhancements.json").read_text(encoding="utf-8"))
        self.assertEqual({item["item_id"] for item in evidence["items"]}, {23766, 25896, 25897})
        for fact in evidence["items"]:
            self.assertNotIn("Binds when", fact["complete_tooltip"])
            item = {"id": fact["item_id"], "binding": "unknown", "boe": None, "sources": [
                {"type": "crafted", "recipe_sources": [{"type": "drop", "zone": "Karazhan", "content_type": "raid"}]}]}
            self.assertFalse(item_has_pre_raid_route(item, "T4"))
            result = apply_source_rule_overrides(item, self.records)
            self.assertTrue(result["tradeable"])
            self.assertEqual(result["binding"], "unknown")
            self.assertIsNone(result["boe"])
            self.assertFalse(item_has_pre_raid_route(result, "PR"))
            self.assertTrue(item_has_pre_raid_route(result, "T4"))
            self.assertEqual(result["sources"], item["sources"])

    def test_audit_distinguishes_withheld_prices_from_verified_evidence(self):
        audit = source_review_audit()
        self.assertIn(33672, audit["unverified_price_item_ids"])
        self.assertIn(33919, audit["verified_price_item_ids"])
        self.assertTrue(audit["quarantined_price_variants"])
        self.assertEqual(len(potion_purchase_overrides()), 2)
        self.assertEqual(self.records, reviewed_source_overrides())


if __name__ == "__main__":
    unittest.main()
