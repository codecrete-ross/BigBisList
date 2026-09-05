import json
from copy import deepcopy
from pathlib import Path
import unittest

from tools.progression import current_phase, expand_pre_raid_paths, classify_pre_raid_refresh, resolve_source_content
from tools.project import canonical_json, PHASE_KEYS, RAW_WOWHEAD_DIR
from tools.scrape_wowhead import item_snapshots_by_id, snapshot_name
from tools.sources import item_has_pre_raid_route, source_is_phase_available, derive_source_acquisition_phase


class ProgressionDataTests(unittest.TestCase):
    def test_replacement_schedule_replays_the_same_content_paths(self):
        definitions = canonical_json("phases")
        self.assertEqual(current_phase(definitions, 1787867999), "T5")
        self.assertEqual(current_phase(definitions, 1787868000), "T6")
        replacement = deepcopy(definitions)
        replacement["active_schedule"] = "future_cycle"
        replacement["schedules"]["future_cycle"] = {"phase_starts": [
            {"key": "PR", "starts_at_epoch": 0}, {"key": "T4", "starts_at_epoch": 100},
            {"key": "T5", "starts_at_epoch": 200}, {"key": "T6", "starts_at_epoch": 300},
        ]}
        self.assertEqual(current_phase(replacement, 299), "T5")
        self.assertEqual(current_phase(replacement, 300), "T6")
        self.assertEqual(replacement["phases"], definitions["phases"])

    def test_source_terminology_cannot_move_black_temple_into_zulaman(self):
        definitions = canonical_json("phases")
        self.assertEqual(resolve_source_content("Black Temple phase 4", definitions), "T6")
        self.assertEqual(resolve_source_content("Phase 4", definitions, "wowhead_classic"), "ZA")
        self.assertEqual(resolve_source_content("Phase 4", definitions, "anniversary_2026"), "SWP")
        self.assertEqual(resolve_source_content("Phase 3.5", definitions, "anniversary_2026"), "ZA")
        self.assertIsNone(resolve_source_content("Phase 4", definitions, "unknown_cycle"))

    def test_historical_snapshot_survives_a_mutable_guide_refresh(self):
        url = "https://www.wowhead.com/tbc/guide/classes/hunter/marksmanship/dps-bis-gear-pve-pre-raid"
        path = RAW_WOWHEAD_DIR / "full_bis" / snapshot_name(url)
        historical = json.loads(path.with_stem(path.stem + "--pr-PR").read_text(encoding="utf-8"))
        current = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(historical["content_phase"], "PR")
        self.assertEqual(current["content_phase"], "T6")
        self.assertNotEqual(historical["tables"], current["tables"])
        self.assertEqual(classify_pre_raid_refresh(current, historical, "T6")["recommendation_status"], "verified_phase_update")
        self.assertEqual(classify_pre_raid_refresh(historical, historical, "T6")["recommendation_status"], "no_distinct_update")

    def test_pre_raid_refresh_uses_source_terminology_and_named_content(self):
        previous = {"content_phase": "PR", "tables": []}
        snapshot = {"tables": [{"heading": "Phase 4 Pre-Raid equipment"}]}
        self.assertEqual(classify_pre_raid_refresh(snapshot, previous, "ZA")["recommendation_status"], "verified_phase_update")
        self.assertEqual(classify_pre_raid_refresh(snapshot, previous, "SWP", terminology="anniversary_2026")["recommendation_status"], "verified_phase_update")
        self.assertEqual(classify_pre_raid_refresh(snapshot, previous, "ZA", terminology="anniversary_2026")["recommendation_status"], "unverified_phase")
        snapshot["content_terminology"] = "anniversary_2026"
        self.assertEqual(classify_pre_raid_refresh(snapshot, previous, "SWP")["recommendation_status"], "verified_phase_update")
        snapshot["tables"][0]["heading"] = "Black Temple Phase 4 Pre-Raid equipment"
        self.assertEqual(classify_pre_raid_refresh(snapshot, previous, "T6")["recommendation_status"], "verified_phase_update")
        self.assertEqual(classify_pre_raid_refresh(snapshot, previous, "SWP")["recommendation_status"], "unverified_phase")

    def test_pre_raid_refresh_supports_replacement_numbering_without_relabeling_archives(self):
        definitions = deepcopy(canonical_json("phases"))
        definitions["source_phase_numbers"]["future_cycle"] = {"7": "T6", "1": "PR"}
        historical = {"content_phase": "PR", "tables": []}
        current = {"tables": [{"heading": "Phase 7 Pre-Raid equipment"}]}
        self.assertEqual(classify_pre_raid_refresh(current, historical, "T6", definitions, "future_cycle")["recommendation_status"], "verified_phase_update")
        self.assertEqual(classify_pre_raid_refresh(current, historical, "T6", definitions, "unknown_cycle")["recommendation_status"], "unverified_phase")
        current["tables"][0]["heading"] = "Phase 1 Pre-Raid equipment"
        # An archived launch path retains its explicit PR metadata. A new
        # publisher's phase-one meaning must come from that source's mapping.
        self.assertEqual(classify_pre_raid_refresh(current, historical, "PR", definitions, "future_cycle")["recommendation_status"], "verified_phase_update")
        self.assertEqual(classify_pre_raid_refresh(current, historical, "PR")["recommendation_status"], "unverified_phase")
        self.assertEqual(historical, {"content_phase": "PR", "tables": []})

    def test_conflicting_named_content_cannot_verify_a_pre_raid_refresh(self):
        previous = {"content_phase": "PR", "tables": []}
        current = {"tables": [{"heading": "Phase 3 Black Temple and Sunwell Pre-Raid equipment"}]}
        self.assertEqual(classify_pre_raid_refresh(current, previous, "T6")["recommendation_status"], "unverified_phase")

    def test_inheritance_never_backfills_from_a_later_list(self):
        def row(phase, item):
            return {"class": "Mage", "spec": "Fire", "phase": "PR", "content_phase": phase,
                    "slot": "Head", "source_url": "https://www.wowhead.com/tbc/guide/example",
                    "items": [{"item_id": item, "rank": 1}]}
        items = {1: {"sources": [{"type": "quest"}]},
                 2: {"sources": [{"type": "vendor", "available_from_phase": "T6"}]}}
        paths = expand_pre_raid_paths([row("PR", 1), row("T6", 2)], items)
        by_phase = {path["content_phase"]: path for path in paths}
        self.assertEqual(by_phase["T5"]["items"][0]["item_id"], 1)
        self.assertEqual(by_phase["T5"]["inherited_from_phase"], "PR")
        self.assertEqual(by_phase["T6"]["items"][0]["item_id"], 2)
        self.assertEqual(by_phase["SWP"]["inherited_from_phase"], "T6")
        self.assertEqual(expand_pre_raid_paths(paths, items), paths)
        with self.assertRaisesRegex(ValueError, "No earlier Pre-Raid evidence"):
            expand_pre_raid_paths([row("T6", 2)], items)

    def test_exclusive_source_windows_and_seller_unlocks(self):
        route = {"type": "pvp", "available_from_phase": "T6", "available_until_phase": "ZA"}
        self.assertFalse(source_is_phase_available(route, "T5"))
        self.assertTrue(source_is_phase_available(route, "T6"))
        self.assertFalse(source_is_phase_available(route, "ZA"))
        exchange = {"type": "token_turnin", "zone": "Isle of Quel'Danas",
                    "token_sources": [{"type": "drop", "zone": "Black Temple"}]}
        self.assertEqual(derive_source_acquisition_phase(exchange), "SWP")
        self.assertFalse(source_is_phase_available(exchange, "T6"))
        self.assertTrue(source_is_phase_available(exchange, "SWP"))

    def test_pre_raid_means_no_personal_raid_participation(self):
        drop = {"type": "drop", "zone": "Black Temple"}
        self.assertFalse(item_has_pre_raid_route({"binding": "bind_on_pickup", "sources": [drop]}, "T6"))
        self.assertTrue(item_has_pre_raid_route({"boe": True, "sources": [drop]}, "T6"))
        self.assertFalse(item_has_pre_raid_route({"boe": True, "sources": [drop]}, "T5"))
        self.assertFalse(item_has_pre_raid_route({"sources": [{"type": "token_turnin", "token_sources": [drop]}]}, "T6"))
        shoulder = {"sources": [{"type": "crafted", "zone": "Black Temple", "recipe_sources": [
            {"type": "drop", "zone": "Black Temple", "tradeable": True}]}]}
        self.assertTrue(item_has_pre_raid_route(shoulder, "T6"))
        self.assertFalse(item_has_pre_raid_route(shoulder, "T5"))
        # The dungeon quest hub may share a raid's zone label.
        self.assertTrue(item_has_pre_raid_route({"sources": [{"type": "quest", "zone": "Tempest Keep", "quest_id": 10704}]}, "PR"))

    def test_later_nonraid_token_route_does_not_unlock_earlier_path(self):
        item = {"sources": [{"type": "token_turnin", "token_sources": [
            {"type": "drop", "zone": "Karazhan"},
            {"type": "vendor", "available_from_phase": "ZA"},
        ]}]}
        self.assertFalse(item_has_pre_raid_route(item, "T6"))
        self.assertTrue(item_has_pre_raid_route(item, "ZA"))

    def test_sparse_new_snapshot_preserves_richer_old_sources(self):
        old = {"page_type": "item", "item_id": 33672, "name": "Old name", "fetched_at": "2021-01-01",
               "normalized_sources": [{"type": "pvp", "entity_id": 1, "costs": [{"amount": 1550, "name": "Arena Points"}]}],
               "item_stats": {"stats": {"agility": 33}}}
        new = {"page_type": "item", "item_id": 33672, "name": "Vengeful Gladiator's Dragonhide Helm",
               "fetched_at": "2026-09-04", "normalized_sources": [], "item_stats": {}}
        merged = item_snapshots_by_id([old, new])[33672]
        self.assertEqual(merged["name"], new["name"])
        self.assertEqual(merged["normalized_sources"], old["normalized_sources"])
        self.assertEqual(merged["item_stats"], old["item_stats"])
        self.assertEqual(merged, item_snapshots_by_id([new, old])[33672])


if __name__ == "__main__":
    unittest.main()
