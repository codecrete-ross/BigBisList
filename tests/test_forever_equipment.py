from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import forever_guide_index
from tools.forever_comparison import comparison_document
from tools.forever_equipment import fidelity_errors, published_rank_matches
from tools.forever_equipment_refresh import EquipmentRefresh, TOOLTIPS
from tools.forever_equipment_sources import _wowsims_item, client_armor
from tools.forever_refresh_http import RefreshHTTP, Unavailable
from tools.forever_sources import WOWHEAD_ROOT, route_leads
from tools.project import lua_value


BUILD = "1.60.1.70959"
CATALOG = {"client_build": BUILD, "fields": ["id", "name", "slot", "level"],
           "items": [[60, "Layered Tunic", "Chest", 1], [9418, "Stoneslayer", "Two Hand", 44]]}
TUNIC = {"id": 60, "name": "Layered Tunic", "slot": "Chest", "armor_type": "Leather",
         "armor": 33, "parse_confidence": "tooltip_endpoint"}
SWORD = {"id": 9418, "name": "Stoneslayer", "slot": "Two Hand", "weapon_subtype": "Sword", "required_level": 44,
         "dps": 42.69, "weapon_min_damage": 133, "weapon_max_damage": 200, "weapon_speed": 3.9}


def observation(url, item, *, exact=False, provider="wowhead", client_build=None):
    return {"url": url, "flavor": "forever", "provider": provider, "client_build": client_build,
            "page_type": "equipment_facts", "confidence": "forever_tooltip" if exact else "client_equipment_export",
            "items": [item]}


class ForeverEquipmentTests(unittest.TestCase):
    def document(self, snapshots):
        with patch("tools.forever_comparison.dataset_json", return_value={"review": {"client_build": BUILD}}):
            return comparison_document(snapshots, CATALOG)

    def test_partial_tooltips_cannot_erase_verified_fields(self):
        first, second = TOOLTIPS + "60#first", TOOLTIPS + "60#second"
        recorded = observation(first, {**TUNIC, "equip_effects": ["Use: Move faster."]}, exact=True)
        later = observation(second, {key: value for key, value in TUNIC.items() if key != "armor"}, exact=True)
        snapshots = {first: recorded, second: later}
        report = self.document(snapshots)
        self.assertEqual(report, self.document(dict(reversed(list(snapshots.items())))))
        self.assertEqual(report["items"][0]["stats"], {"armor": 33})
        self.assertEqual(report["items"][0]["effects"], ["Use: Move faster."])
        self.assertNotIn("level", report["items"][0])
        packed = {"item_fields": ["id", "stats"], "items": {"60": [60, {}]}}
        self.assertTrue(any(f["field"] == "armor" for f in fidelity_errors(report, [], packed)))

    def test_weapon_range_is_independent_of_attributes_and_build(self):
        url = "https://raw.githubusercontent.com/wowsims/gamedata/example/items/items.txt"
        row = _wowsims_item(9418, "Stoneslayer", {"item": "rare, Sword, two-hand", "level": "ilvl 49, requires level 44",
                                                 "weapon": "133 - 200 damage, speed 3.90, 42.7 dps"})
        self.assertEqual(row["stats"], {})
        snapshot = observation(url, row, provider="wowsims_gamedata", client_build="1.60.1.70938")
        self.assertEqual(self.document({url: snapshot})["items"], [])
        snapshot["client_build"] = BUILD
        facts = self.document({url: snapshot})["items"][0]
        self.assertTrue(facts["attributes_known"])
        self.assertEqual(facts["stats"]["dps"], 42.69)

    def test_equipment_identity_survives_irrelevant_tooltip_text(self):
        url = TOOLTIPS + "60"
        ring = {"id": 60, "name": "Deprecated Ring", "slot": "Ring", "weapon_subtype": "Dagger", "stats": {"stamina": 10}}
        facts = self.document({url: observation(url, ring, exact=True)})["items"][0]
        self.assertNotIn("weapon_subtype", facts)
        self.assertEqual(facts["stats"], {"stamina": 10.0})

    def test_partial_exact_weapon_does_not_resolve_disputed_bulk_damage(self):
        exact, export, scan = TOOLTIPS + "9418", "https://example.test/export", "https://example.test/scan"
        partial = {key: value for key, value in SWORD.items() if key not in {"dps", "weapon_min_damage", "weapon_max_damage"}}
        snapshot = observation(scan, {"id": 9418, "slot": "Two Hand", "stats": {"dps": 50}}, provider="libitemdb")
        document = self.document({exact: observation(exact, partial, exact=True),
                                  export: observation(export, SWORD, provider="wowsims_gamedata", client_build=BUILD),
                                  scan: snapshot})
        self.assertEqual(document["items"][0]["stats"], {"weapon_speed": 3.9})
        self.assertEqual(document["conflicts"], [{"id": 9418, "field": "weapon", "sources": [export, scan], "needs_tooltip": True}])

    def test_scoped_routes_reach_guide_audit_without_changing_leveling_leads(self):
        url = "https://example.test/loot#gear-guide"
        snapshots = {url: {"page_type": "equipment_routes", "relationships": [
            {"subject_type": "npc", "subject_id": 2748, "relation": "drops", "object_type": "item", "object_id": 9418}]}}
        self.assertEqual(route_leads(snapshots), {})
        lead, = route_leads(snapshots, include_guide=True)[9418]
        self.assertEqual(lead["subject_id"], 2748)

    def test_build_armor_uses_the_exact_item_quality_modifier(self):
        tables = {"ItemSparse": b"ID,InventoryType,ItemLevel,OverallQualityID,Display_lang,QualityModifier\n18168,14,70,4,Force Reactive Disk,80\n",
                  "ItemArmorTotal": b"ItemLevel\n70\n", "ItemArmorQuality": b"ID\n70\n", "ArmorLocation": b"ID\n14\n",
                  "ItemArmorShield": b"ItemLevel,Quality_4\n70,2468\n"}
        equipment = {18168: {"id": 18168, "name": "Force Reactive Disk", "slot": "Off Hand", "item_level": 70,
                              "quality": "epic", "armor_type": "Shield"}}
        snapshot = client_armor(tables, equipment, BUILD, "https://example.test", "2026-11-19")
        self.assertEqual(snapshot["items"][0]["armor"], 2548)

    def test_older_tooltip_recovers_bonus_armor_from_the_preserved_text(self):
        url = TOOLTIPS + "60"
        old = {**TUNIC, "description": "Layered Tunic Chest Leather 33 Armor +12 Armor Equip: Adds +99 Armor."}
        facts = self.document({url: observation(url, old, exact=True)})["items"][0]
        self.assertEqual(facts["stats"]["armor"], 45)
        self.assertEqual(facts["armor_base"], 33)

    def test_target_client_tooltip_can_supply_armor_without_changing_guide_source_build(self):
        url = "capture://forever/" + "9" * 64
        item = {**TUNIC, "armor": 45, "description": "Chest Leather 33 Armor +12 Armor"}
        exact = observation(url, item, exact=True, provider="local_capture", client_build="1.60.1.71037")
        self.assertEqual(self.document({url: exact})["items"][0]["stats"]["armor"], 45)
        exact["client_build"] = "1.60.1.70000"
        self.assertEqual(self.document({url: exact})["items"], [])

    def test_normalized_stat_row_must_match_the_shipped_lua(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "DataForever.lua"
            packed = {"items": {"60": [60, {"armor": 33}]}}
            output.write_text('BigBiSListData = {\n    ["stat_rank"] = ' + lua_value(packed, 4) + ",\n}\n", encoding="utf-8")
            self.assertTrue(published_rank_matches(packed, output))
            self.assertFalse(published_rank_matches({"items": {"60": [60, {"armor": 3}]}}, output))

    def test_guide_release_verification_compares_the_rebuilt_bytes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "GuideDataForever.lua"
            payload.write_bytes(b"expected\n")
            continuation = root / forever_guide_index.CONTINUATION
            continuation.write_bytes(b"ranks\n")

            def rebuild(_lua, *, output):
                output.write_bytes(b"expected\n")
                output.with_name(continuation.name).write_bytes(b"ranks\n")

            with (patch.object(forever_guide_index, "ROOT", root), patch.object(forever_guide_index, "OUTPUT", payload),
                  patch.object(forever_guide_index, "check_index", return_value=True),
                  patch.object(forever_guide_index, "compile_index", side_effect=rebuild)):
                self.assertTrue(forever_guide_index.verify_index("lua"))
                continuation.write_bytes(b"wrong class rankings\n")
                self.assertFalse(forever_guide_index.verify_index("lua"))
                continuation.write_bytes(b"ranks\n")
                payload.write_bytes(b"changed with a valid header\n")
                self.assertFalse(forever_guide_index.verify_index("lua"))

    def test_old_404_is_retried_outside_the_leveling_queue(self):
        item_url = WOWHEAD_ROOT + "item=9418"
        url = TOOLTIPS + "9418"
        now = datetime(2026, 11, 18, tzinfo=timezone.utc)
        cycles = []
        with TemporaryDirectory() as directory:
            http = RefreshHTTP(Path(directory), online=True, user_agent="test", now=lambda: now)
            refresh = SimpleNamespace(http=http, original={}, snapshots={}, staged={}, previous_staged={}, ledger={item_url: {"url": item_url,
                "status": "pending", "last_attempt_at": "2026-11-06T00:00:00+00:00"}})
            with (patch("tools.forever_equipment_refresh.reviewed_equipment", return_value=([], [])),
                  patch("tools.forever_equipment_refresh.dataset_json", return_value={"items": []})):
                runner = EquipmentRefresh(refresh, CATALOG, None)

            def report(document, **_):
                complete = any("weapon_max_damage" in row["stats"] for row in document["items"])
                return {"items": {"9418": {"id": 9418, "missing": [] if complete else ["weapon"],
                                            "acquisition": "missing"}}, "rolls": {}, "counts": {}, "conflict_groups": [], "bulk_sources": {},
                        "fidelity_errors": []}

            def collect(identifier, cycle):
                self.assertEqual(identifier, 9418)
                cycles.append(cycle)
                if len(cycles) == 1:
                    raise Unavailable("HTTP 404", status=404)
                item = dict(SWORD)
                if len(cycles) == 2:
                    item.pop("weapon_max_damage")
                refresh.snapshots[url] = observation(url, item, exact=True)
                return True

            with (patch.object(runner, "_document", side_effect=lambda: self.document(refresh.snapshots)),
                  patch.object(runner, "_report", side_effect=report), patch.object(runner, "_refresh_tooltip", side_effect=collect)):
                runner.collect_exact()
                self.assertEqual(runner.lookups[url]["status"], "pending")
                now += timedelta(days=7)
                result = runner.collect_exact()
                self.assertEqual(runner.lookups[url]["status"], "collected")
                self.assertEqual(result["items"]["9418"]["missing"], ["weapon"])
                last_attempt = now.isoformat()
                now += timedelta(days=7)
                result = runner.collect_exact()
                self.assertEqual(cycles[-1], last_attempt)
                self.assertEqual(result["items"]["9418"]["missing"], [])
