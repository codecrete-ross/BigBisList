import base64
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.phase_gems import (
    build_phase_gem_audit,
    decode_tbc_planner,
    import_phase_gems,
    item_gem_color,
    normalize_phase_gem_guide,
    reviewed_gem_items,
    reviewed_gem_source_overrides,
)


EVIDENCE = Path(__file__).resolve().parents[1] / "data/raw/wowhead/phase_gems"


def evidence_for(fragment):
    for path in sorted(EVIDENCE.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if fragment in row.get("url", "") and row.get("page_type") == "phase_gem_guide":
            return row
    raise AssertionError(f"Missing committed phase gem evidence: {fragment}")


def item(item_id, name, quality="epic", phase="T6"):
    return {"page_type": "item", "item_id": item_id, "name": name, "quality": quality,
            "url": f"https://www.wowhead.com/tbc/item={item_id}", "fetched_at": "2026-09-04T00:00:00Z",
            "normalized_sources": [{"type": "crafted", "entity_name": name, "available_from_phase": phase}]}


class PhaseGemTests(unittest.TestCase):
    def test_published_balance_loadout_decodes_only_its_gem_fields(self):
        evidence = evidence_for("balance-druid-dps-bt-hyjal")
        planner = next(row for row in evidence["gem_guidance"] if row["kind"] == "gear_planner")
        decoded = decode_tbc_planner(planner["planner"])
        self.assertEqual(decoded, planner["decoded"])
        self.assertEqual(decoded["level"], 70)
        gems = {gem["item_id"] for slot in decoded["slots"] for gem in slot.get("gems", [])}
        self.assertEqual(gems, {32196, 32215, 32218, 34220})
        self.assertNotIn(31040, gems)  # Tier 6 helm is equipment, not a gem.

    def test_every_committed_planner_roundtrips_and_accepts_hunter_ammunition(self):
        ammo = False
        count = 0
        for path in EVIDENCE.glob("*.json"):
            evidence = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(evidence.get("parse_errors"), evidence.get("url"))
            for row in evidence.get("gem_guidance", []):
                if row["kind"] == "gear_planner":
                    decoded = decode_tbc_planner(row["planner"])
                    self.assertEqual(decoded, row["decoded"])
                    ammo = ammo or any(slot["slot"] == 0 for slot in decoded["slots"])
                    count += 1
        self.assertGreater(count, 80)
        self.assertTrue(ammo)

    def test_unsupported_and_truncated_planners_fail_explicitly(self):
        for payload in (bytes([4, 70, 0]), bytes([3, 70, 0, 1, 64, 125])):
            token = base64.urlsafe_b64encode(payload).decode().rstrip("=")
            with self.assertRaises(ValueError):
                decode_tbc_planner("druid/night-elf/" + token)

    def test_prose_is_scoped_to_article_and_preserves_current_phase(self):
        html = '<div class="guide-content"><noscript><b>Gemming:</b> Use <a href="/tbc/item=32194/delicate-crimson-spinel">Delicate Crimson Spinel</a>.<br><br></noscript></div><div class="comments"><a href="/tbc/item=32196/runed-crimson-spinel">Runed Crimson Spinel</a></div>'
        snapshot = {"url": "https://www.wowhead.com/tbc/guide/example", "fetched_at": "2026-09-04", "content_phase": "T6"}
        result = normalize_phase_gem_guide(snapshot, html, [{"class": "Druid", "spec": "Feral tank", "phase": "PR"}])
        self.assertEqual(result["bindings"], [{"class": "Druid", "spec": "Feral tank", "phase": "T6"}])
        self.assertEqual(result["gem_guidance"][0]["gem_ids"], [32194])

    def test_epic_recommendation_keeps_earlier_rare_path_and_budget_alternative(self):
        evidence = evidence_for("feral-druid-tank-bt-hyjal")
        base = {"gems": [{"class": "Druid", "spec": "Feral tank", "phase": phase, "id": 24028,
                          "name": "Delicate Living Ruby", "socket_color": "red", "socket_category": "red",
                          "quality": 3, "meta": False, "context": "standard"} for phase in ("PR", "T4", "T5", "T6", "ZA")]}
        before = deepcopy(base)
        snapshots = [evidence, item(32194, "Delicate Crimson Spinel"), item(24028, "Delicate Living Ruby", "rare", "PR")]
        rows = import_phase_gems(snapshots, base)["gems"]
        self.assertEqual(base, before)
        self.assertEqual([r["phase"] for r in rows if r["id"] == 32194], ["T6"])
        self.assertEqual(next(r for r in rows if r["id"] == 24028 and r["phase"] == "T6")["context"], "budget")
        self.assertEqual(next(r for r in rows if r["id"] == 24028 and r["phase"] == "T5")["context"], "standard")

    def test_missing_phase_and_acquisition_are_not_counted_as_refresh(self):
        evidence = evidence_for("feral-druid-tank-bt-hyjal")
        base = {"gems": [{"class": "Druid", "spec": "Feral tank", "phase": phase} for phase in ("T5", "T6")]}
        audit = build_phase_gem_audit([evidence], base)
        self.assertFalse(audit["complete_phase_guidance"])
        self.assertEqual(audit["coverage"][0]["status"], "general_guide_fallback")
        self.assertEqual(audit["coverage"][1]["status"], "missing_acquisition_evidence")
        self.assertIn(32194, audit["missing_item_ids"])

    def test_later_recipe_does_not_enter_an_earlier_recommendation(self):
        evidence = {"page_type": "phase_gem_guide", "url": "https://www.wowhead.com/tbc/guide/example",
                    "bindings": [{"class": "Paladin", "spec": "Holy", "phase": "T6"}],
                    "gem_guidance": [{"kind": "gear_planner", "gem_ids": [35761]}]}
        self.assertEqual(import_phase_gems([evidence, item(35761, "Quick Lionseye", phase="SWP")], {"gems": []}), {"gems": []})

    def test_special_gems_use_verified_socket_text_and_keep_profession_requirement(self):
        gem = item(33131, "Crimson Sun")
        gem["description"] = 'Crimson Sun Requires Jewelcrafting (360) "Matches a Red Socket."'
        gem["normalized_requirements"] = [{"type": "profession", "profession": "Jewelcrafting", "scope": "equip_or_use", "skill": 360}]
        self.assertEqual(item_gem_color(gem), "red")
        evidence = {"page_type": "phase_gem_guide", "url": "https://www.wowhead.com/tbc/guide/example",
                    "bindings": [{"class": "Hunter", "spec": "Beast Mastery", "phase": "T6"}],
                    "gem_guidance": [{"kind": "gear_planner", "gem_ids": [33131]}]}
        row = import_phase_gems([evidence, gem], {"gems": []})["gems"][0]
        self.assertEqual(row["context"], "jewelcrafting")
        self.assertEqual(row["requirements"], gem["normalized_requirements"])

    def test_unchanged_pr_article_cannot_claim_verified_phase3_gem_evidence(self):
        evidence = deepcopy(evidence_for("feral-druid-tank-bt-hyjal"))
        evidence["recommendation_status"] = "no_distinct_update"
        base = {"gems": [{"class": "Druid", "spec": "Feral tank", "phase": "T6"}]}
        audit = build_phase_gem_audit([evidence], base)
        self.assertEqual(audit["coverage"][0]["status"], "general_guide_fallback")
        self.assertEqual(audit["unverified_guide_updates"][0]["status"], "no_distinct_update")

    def test_reviewed_epic_cuts_keep_recipe_gates_and_later_haste_unlock(self):
        from tools.sources import source_is_phase_available
        snapshots = [item(32194, "Delicate Crimson Spinel"), item(32212, "Shifting Shadowsong Amethyst"), item(35761, "Quick Lionseye")]
        for snapshot in snapshots:
            snapshot["normalized_sources"] = []
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=reviewed_gem_source_overrides()):
            items = reviewed_gem_items(snapshots)
        delicate = items[32194]["normalized_sources"][0]
        self.assertFalse(source_is_phase_available(delicate, "T5"))
        self.assertTrue(source_is_phase_available(delicate, "T6"))
        self.assertEqual(delicate["recipe_sources"][0]["vendor_id"], 23437)
        self.assertEqual(delicate["recipe_sources"][0]["requirements"][0]["standing"], "Friendly")
        shifting = items[32212]["normalized_sources"][0]
        self.assertEqual(shifting["recipe_sources"][0]["type"], "drop")
        self.assertEqual(shifting["recipe_sources"][0]["zone"], "Hyjal Summit")
        quick = items[35761]["normalized_sources"][0]
        self.assertFalse(source_is_phase_available(quick, "T6"))
        self.assertTrue(source_is_phase_available(quick, "SWP"))

    def test_supplemental_sources_preserve_bound_heroic_and_profession_gems(self):
        from tools.scrape_wowhead import snapshot_name
        from tools.sources import source_content_type, source_is_phase_available
        ids = [23118, 24032, 24036, 24048, 24051, 24052, 24062, 25898,
               28119, 28120, 28362, 28363, 30549, 30550, 30555, 30556,
               30582, 30602, 30604, 31861, 33131, 33143, 33782, 34831,
               35488, 35501, 35707, 38547]
        snapshots = [json.loads((EVIDENCE / snapshot_name(f"https://www.wowhead.com/tbc/item={i}")).read_text()) for i in ids]
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=reviewed_gem_source_overrides()):
            items = reviewed_gem_items(snapshots)
        for item_id in ids:
            self.assertTrue(items[item_id]["normalized_sources"], item_id)
        heroic = items[30549]
        self.assertEqual(heroic["binding"], "bind_on_pickup")
        self.assertFalse(heroic.get("tradeable"))
        self.assertEqual(source_content_type(heroic["normalized_sources"][0]), "heroic_dungeon")
        self.assertTrue(source_is_phase_available(heroic["normalized_sources"][0], "PR"))
        crimson = items[33131]
        self.assertFalse(crimson.get("tradeable"))
        recipe = crimson["normalized_sources"][0]["recipe_sources"][0]
        self.assertEqual(recipe["requirements"][0]["reputation"], "The Consortium")
        self.assertEqual(recipe["requirements"][0]["standing"], "Revered")
        self.assertTrue(any(r.get("skill") == 360 and r.get("scope") == "equip_or_use"
                            for r in crimson["normalized_requirements"]))
        self.assertTrue(items[34831]["tradeable"])
        self.assertFalse(items[38547].get("tradeable"))

    def test_later_bound_quest_gem_and_sso_cuts_are_unavailable_candidates(self):
        from tools.scrape_wowhead import snapshot_name
        ids = [35488, 35501, 35707]
        snapshots = [json.loads((EVIDENCE / snapshot_name(f"https://www.wowhead.com/tbc/item={i}")).read_text()) for i in ids]
        evidence = {"page_type": "phase_gem_guide", "url": "https://www.wowhead.com/tbc/guide/example",
                    "bindings": [{"class": "Paladin", "spec": "Protection", "phase": "T6"}],
                    "gem_guidance": [{"kind": "gear_planner", "gem_ids": ids}]}
        with patch("tools.scrape_wowhead.reviewed_overrides", return_value=reviewed_gem_source_overrides()):
            rows = import_phase_gems([evidence, *snapshots], {"gems": []})
            audit = build_phase_gem_audit([evidence, *snapshots], {"gems": [{"class": "Paladin", "spec": "Protection", "phase": "T6"}]})
            items = reviewed_gem_items(snapshots)
        self.assertEqual(rows, {"gems": []})
        self.assertEqual(audit["coverage"][0]["phase_unavailable_gem_ids"], ids)
        self.assertEqual(audit["coverage"][0]["status"], "phase_guidance_unavailable")
        self.assertFalse(audit["complete_phase_guidance"])
        self.assertFalse(audit["missing_item_ids"])
        eternal = items[35501]["normalized_sources"][0]
        self.assertEqual(eternal["requirements"][0]["skill"], 370)
        self.assertEqual(eternal["recipe_sources"][0]["requirements"][0]["reputation"], "Shattered Sun Offensive")

    def test_recipe_binding_is_not_inherited_from_the_taught_bound_cut(self):
        from tools.scrape_wowhead import snapshot_name
        for item_id in (33156, 33158):
            recipe = json.loads((EVIDENCE / snapshot_name(f"https://www.wowhead.com/tbc/item={item_id}")).read_text())
            self.assertEqual(recipe["binding"], "bind_on_pickup")
            self.assertFalse(any(r.get("scope") == "equip_or_use" for r in recipe["normalized_requirements"]))


if __name__ == "__main__":
    unittest.main()
