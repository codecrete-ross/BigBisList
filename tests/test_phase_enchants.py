from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.phase_enchants import build_phase_enchant_audit, import_phase_enchants, normalize_phase_enchant_guide, reviewed_enchant_effects
from tools.phase_gems import decode_tbc_planner


EVIDENCE = Path(__file__).resolve().parents[1] / "data/raw/wowhead/phase_enchants"


def guidance(phase="T6", spell_id=42620):
    return {"page_type": "phase_enchant_guide", "url": "https://www.wowhead.com/tbc/guide/example",
            "bindings": [{"class": "Hunter", "spec": "Beast Mastery", "phase": phase}],
            "enchant_guidance": [{"kind": "gear_planner", "applications": [{"slot": "Main Hand", "spell_id": spell_id}]}]}


def spell():
    return {"page_type": "spell", "spell_id": 42620, "name": "Enchant Weapon - Greater Agility",
            "url": "https://www.wowhead.com/tbc/spell=42620", "fetched_at": "2026-09-05",
            "normalized_sources": [{"type": "taught_by_item", "item_id": 33165}]}


def formula():
    return {"page_type": "item", "item_id": 33165, "name": "Formula: Enchant Weapon - Greater Agility",
            "url": "https://www.wowhead.com/tbc/item=33165", "fetched_at": "2026-09-05", "teaches_spell_ids": [42620],
            "normalized_sources": [{"type": "vendor", "entity_name": "Apprentice Darius", "available_from_phase": "T6"}],
            "normalized_requirements": [{"type": "profession", "profession": "Enchanting", "skill": 350,
                                          "scope": "learn_recipe"}]}


class PhaseEnchantTests(unittest.TestCase):
    def test_published_planner_applications_are_spell_ids_and_roundtrip(self):
        count = 0
        greater_agility = 0
        two_hand = 0
        for path in EVIDENCE.glob("*.json"):
            evidence = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(evidence.get("parse_errors"))
            for row in evidence.get("enchant_guidance", []):
                if row["kind"] != "gear_planner":
                    continue
                decoded = decode_tbc_planner(row["planner"])
                applications = {(s["item_id"], s["enchant_id"]) for s in decoded["slots"] if s.get("enchant_id")}
                for enchant in row["applications"]:
                    self.assertIn((enchant["equipment_item_id"], enchant["spell_id"]), applications)
                    if enchant["spell_id"] == 35452:
                        self.assertEqual(enchant["entity"], {"type": "item", "id": 29192, "name": "Glyph of Ferocity"})
                    greater_agility += enchant["spell_id"] == 42620
                    two_hand += enchant["slot"] == "Two Hand"
                    count += 1
        self.assertGreater(count, 1000)
        self.assertGreater(greater_agility, 10)
        self.assertGreater(two_hand, 10)

    def test_current_hunter_prose_recommends_both_dual_wield_slots(self):
        snapshot = {"url": "https://www.wowhead.com/tbc/guide/example", "fetched_at": "2026-09-05", "content_phase": "T6"}
        markup = '[h4]Dual-Wield Weapons[/h4]\n\nRe-enchant it with [spell=42620].'
        result = normalize_phase_enchant_guide(snapshot, "WH.markup.printHtml(" + json.dumps(markup) + ")",
                    [{"class": "Hunter", "spec": "Beast Mastery", "phase": "PR"}], [], {})
        self.assertEqual(result["bindings"][0]["phase"], "T6")
        self.assertEqual({r["applications"][0]["slot"] for r in result["enchant_guidance"]}, {"Main Hand", "Off Hand"})

    def test_greater_agility_appears_only_in_verified_available_phase(self):
        base = {"enchants": [{"class": "Hunter", "spec": "Beast Mastery", "phase": p, "slot": "Main Hand",
                              "id": 23800, "type": "spell", "name": "Agility", "context": "standard"} for p in ("T5", "T6")]}
        previous = deepcopy(base)
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            result = import_phase_enchants([guidance("T5"), guidance(), spell(), formula()], base)
        self.assertEqual(base, previous)
        new = [row for row in result["enchants"] if row["id"] == 42620]
        self.assertEqual([row["phase"] for row in new], ["T6"])
        self.assertEqual(new[0]["formula_item_ids"], [33165])
        self.assertTrue(any(req.get("skill") == 350 and req["scope"] == "learn_recipe" for req in new[0]["requirements"]))
        self.assertEqual(len([row for row in result["enchants"] if row["id"] == 23800]), 2)

    def test_unknown_application_spell_is_not_invented_as_an_enchant(self):
        unknown = {**spell(), "spell_id": 35439, "name": "Glyph of the Defender"}
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            result = import_phase_enchants([guidance(spell_id=35439), unknown], {"enchants": []})
            audit = build_phase_enchant_audit([guidance(spell_id=35439), unknown],
                         {"enchants": [{"class": "Hunter", "spec": "Beast Mastery", "phase": "T6"}]})
        self.assertEqual(result, {"enchants": []})
        self.assertEqual(audit["coverage"][0]["unmapped_application_spell_ids"], [35439])
        self.assertFalse(audit["complete_phase_guidance"])

    def test_unverified_current_pr_heading_keeps_general_fallback(self):
        evidence = {**guidance(), "recommendation_status": "no_distinct_update"}
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            result = import_phase_enchants([evidence, spell(), formula()], {"enchants": []})
        self.assertEqual(result, {"enchants": []})

    def test_formula_source_window_is_reported_separately_from_missing_sources(self):
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            audit = build_phase_enchant_audit([guidance("T5"), spell(), formula()],
                         {"enchants": [{"class": "Hunter", "spec": "Beast Mastery", "phase": "T5"}]})
        self.assertEqual(audit["coverage"][0]["phase_unavailable_entities"], [["spell", 42620]])
        self.assertEqual(audit["coverage"][0]["missing_acquisition_entities"], [])

    def test_applied_enchant_ids_come_from_reviewed_spell_effects(self):
        effects = reviewed_enchant_effects()
        self.assertEqual({row["id"]: row["effect_ids"] for row in effects},
                         {27911: [2617], 33990: [1144], 42620: [3222], 42974: [3225]})
        self.assertTrue(all(row["source_spell_id"] == row["id"] for row in effects))
        effects[0]["effect_ids"].append(0)
        self.assertNotIn(0, reviewed_enchant_effects()[0]["effect_ids"])

    def test_application_alias_uses_the_verified_crafting_spell_recipe(self):
        evidence = guidance(spell_id=46502)
        application = evidence["enchant_guidance"][0]["applications"][0]
        application.update(slot="Chest", entity={"type": "spell", "id": 46502, "name": "Enchant Chest - Exceptional Stats"})
        alias = {**spell(), "spell_id": 46502, "name": "Enchant Chest - Exceptional Stats", "normalized_sources": []}
        recipe_spell = {**spell(), "spell_id": 27960, "name": "Enchant Chest - Exceptional Stats",
                        "normalized_sources": [{"type": "taught_by_item", "item_id": 22547}]}
        recipe_item = {**formula(), "item_id": 22547, "name": "Formula: Enchant Chest - Exceptional Stats", "teaches_spell_ids": [27960]}
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            row = import_phase_enchants([evidence, alias, recipe_spell, recipe_item], {"enchants": []})["enchants"][0]
        self.assertEqual(row["id"], 46502)
        self.assertEqual(row["source_spell_id"], 27960)
        self.assertEqual(row["formula_item_ids"], [22547])

    def test_phase_evidence_contains_greater_agility_spell_dependency(self):
        from tools.scrape_wowhead import load_snapshots
        snapshots = load_snapshots(EVIDENCE)
        current_spell = next(row for row in snapshots if row.get("page_type") == "spell" and row.get("spell_id") == 42620)
        self.assertEqual(current_spell["fetch_method"], "tooltip_endpoint")
        self.assertIn("historical_source_evidence", current_spell)
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=[]):
            rows = import_phase_enchants([*snapshots, formula()], {"enchants": []})["enchants"]
        available = [row for row in rows if row["id"] == 42620]
        self.assertTrue(any(row["phase"] == "T6" for row in available))
        self.assertFalse(any(row["phase"] in ("PR", "T4", "T5") for row in available))


if __name__ == "__main__":
    unittest.main()
