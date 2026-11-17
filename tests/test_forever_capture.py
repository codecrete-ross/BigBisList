"""Local captures are opt-in, bounded, anonymous evidence rather than approvals."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from test_addon_runtime_lua import find_lua51
from tools import forever_capture as capture
from tools.project import ADDON_DIR


BUILD = "1.60.1.70790"


def record(kind="tooltip", **fields):
    return {"kind": kind, "item_id": 71, "client_build": BUILD, "observed_at": "2026-11-05T06:40:00Z",
            "faction": "Alliance", **({"name": "Fixture Ring", "lines": ["Fixture Ring", "Finger", "+8 Stamina"]} if kind == "tooltip" else {}), **fields}


def document(*records):
    return {"version": 1, "flavor": "forever", "client_build": BUILD, "records": list(records)}


class CaptureImportTests(unittest.TestCase):
    def test_saved_variables_are_parsed_without_running_lua(self):
        text = 'BigBiSListDB = { ["forever"] = { capture = { version = 1, flavor = "forever", records = {}, }, }, }'
        self.assertEqual(capture.LuaDataReader(text).read()["BigBiSListDB"]["forever"]["capture"]["version"], 1)
        for malicious in ('BigBiSListDB = os.execute("bad")', 'BigBiSListDB = (function() return {} end)()',
                          'BigBiSListDB = { x = 1 } os.execute("bad")', 'BigBiSListDB = { x = 1, x = 2 }'):
            with self.subTest(text=malicious), self.assertRaises(ValueError):
                capture.LuaDataReader(malicious).read()

    def test_wrong_client_and_stale_or_mixed_build_are_rejected(self):
        base = document(record())
        for field, value in (("flavor", "anniversary"), ("client_build", "1.60.1.70755"), ("version", 2)):
            changed = {**base, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                capture.normalize_capture(changed, BUILD)
        with self.assertRaises(ValueError):
            capture.normalize_capture(document(record(client_build="1.60.1.70755")), BUILD)

    def test_repeated_observations_deduplicate_and_unknown_private_fields_are_dropped(self):
        row = record(account_name="private", character_name="private")
        later = {**row, "observed_at": "2026-11-05T06:50:00Z"}
        rows = capture.normalize_capture(document(row, later), BUILD)
        self.assertEqual(len(rows), 1)
        self.assertNotIn("private", json.dumps(rows))
        self.assertEqual(rows[0]["item_stats"]["stats"]["stamina"], 8)
        self.assertTrue(rows[0]["url"].startswith("capture://forever/"))

    def test_private_tooltip_text_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "private"):
            capture.normalize_capture(document(record(lines=["Fixture Ring", "Finger", "Made by Somebody"])), BUILD)

    def test_captured_recipes_and_items_named_like_slots_are_not_equipment(self):
        recipe = record(name="Plans: Arcanite Champion", lines=["Plans: Arcanite Champion", "Use: Teaches you how to make it.",
                        "Arcanite Champion", "Two-Hand", "Sword", "+20 Strength"])
        rows = capture.normalize_capture(document(recipe), BUILD)
        self.assertEqual(rows[0]["item_kind"], "recipe")
        self.assertNotIn("slot", rows[0]["item_stats"])
        self.assertNotIn("strength", rows[0]["item_stats"].get("stats", {}))
        rows = capture.normalize_capture(document(record(name="Relic", lines=["Relic", "This Item Begins a Quest"])), BUILD)
        self.assertIsNone(rows[0]["inventory_slot"])

    def test_ambiguous_loot_is_a_lead_and_player_position_never_becomes_a_pin(self):
        rows = capture.normalize_capture(document(record("loot", position={"map_id": 1453, "x": .3, "y": .4})), BUILD)
        self.assertEqual(rows[0]["relationships"], [])
        self.assertEqual(rows[0]["position_observation"]["kind"], "player")
        self.assertNotIn("destination", rows[0])

    def test_quest_and_vendor_observations_keep_faction_costs_and_exact_ids(self):
        rows = capture.normalize_capture(document(record("quest_reward", quest_id=7, choice=True),
            record("vendor", npc_id=8, price_copper=200, extended_cost=True, stock=0)), BUILD)
        edges = [r["relationships"][0] for r in rows]
        self.assertEqual({r["subject_id"] for r in edges}, {7, 8})
        self.assertTrue(all(r["observed_faction"] == "Alliance" for r in edges))
        self.assertTrue(all("side" not in r for r in edges), "observer faction does not establish exclusivity")
        vendor = next(r for r in edges if r["relation"] == "sells")
        self.assertTrue(vendor["extended_cost_unresolved"])
        self.assertEqual(vendor["stock"], 0)

    def test_import_preview_and_invalid_files_do_not_write_anything(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "SavedVariables"):
                capture.read_capture(Path(directory) / "unrelated.env")
            path = Path(directory) / "capture.json"
            path.write_text(json.dumps(document(record())), encoding="utf-8")
            with patch.object(capture, "load_json", return_value={"sources": []}), patch.object(
                capture, "write_text", side_effect=AssertionError("preview wrote files")
            ):
                result = capture.import_capture(path, BUILD, write=False)
                self.assertEqual(result["new_observations"], 1)
                self.assertFalse(result["written"])
                path.write_text(json.dumps(document(record(), record(client_build="wrong"))), encoding="utf-8")
                with self.assertRaises(ValueError):
                    capture.import_capture(path, BUILD, write=True)

    def test_invalid_numbers_timestamps_and_large_input_are_rejected(self):
        for changed in (record(item_id=True), record(observed_at="2026-11-05T06:40:00"),
                        record(position={"map_id":1453,"x":float("nan"),"y":.3})):
            with self.subTest(record=changed), self.assertRaises(ValueError):
                capture.normalize_capture(document(changed), BUILD)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            path.write_bytes(b" " * (8 * 1024 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, "8 MiB"):
                capture.read_capture(path)


class RecorderRuntimeTests(unittest.TestCase):
    def test_attribution_is_retained_through_compaction_and_display(self):
        from tools import generate_lua

        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        credit = {"credit":"Data from Everloot", "licence":"CC BY-SA 4.0", "licenceUrl":"https://creativecommons.org/licenses/by-sa/4.0/", "source":"https://everloot.app"}
        source = {"type":"drop", "attribution":[credit], "recipe_sources":[{"type":"drop", "attribution":[credit]}]}
        compact = generate_lua.compact_source(source)
        self.assertEqual(compact[generate_lua.SOURCE_SCHEMA.index("attribution")], [credit])
        script = r'''
BigBiSList = {}
dofile("DataIndex.lua")
local credit = {credit="Data from Everloot",licence="CC BY-SA 4.0",licenceUrl="https://creativecommons.org/licenses/by-sa/4.0/",source="https://everloot.app"}
local lines=BigBiSList:GetSourceAttributionLines({attribution={credit},recipe_sources={{attribution={credit}}}})
assert(#lines==1,"nested credits were duplicated")
assert(lines[1]:find("https://everloot.app",1,true),"provider link omitted")
assert(lines[1]:find("https://creativecommons.org/licenses/by-sa/4.0/",1,true),"licence link omitted")
'''
        result = subprocess.run([lua, "-"], input=script, text=True, capture_output=True, cwd=ADDON_DIR, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_recorder_is_opt_in_targeted_and_does_not_attribute_ambiguous_loot(self):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        script = r'''
BigBiSListDB = { forever = {} }
BigBiSList = { isForever=true }
function BigBiSList:EnsureDatabase() end
function BigBiSList:GetAccountDB() return BigBiSListDB.forever end
function GetBuildInfo() return "1.60.1", "70790" end
function UnitFactionGroup() return "Alliance" end
function date() return "2026-11-05T06:40:00Z" end
C_TooltipInfo = { GetHyperlink=function() return {lines={
    {leftText="Fixture Ring"},{leftText="Finger"},{leftText="+8 Stamina"},{leftText="Made by Somebody"}}} end }
function GetInstanceInfo() return "Fixture", "party", 1, "Normal", 5, nil, nil, 7 end
function GetNumLootItems() return 1 end
function GetLootSlotLink() return "item:71" end
function GetLootSourceInfo() return "Creature-0-1-2-3-1853-000000001", 1, "Creature-0-1-2-3-1854-000000002", 1 end
function GetQuestID() return 7 end
function GetNumQuestChoices() return 1 end
function GetNumQuestRewards() return 0 end
function GetQuestItemLink() return "item:71" end
dofile("tools/recorder/BigBiSList_Recorder/Targets.lua")
dofile("tools/recorder/BigBiSList_Recorder/Recorder.lua")
local recorder=BigBiSList.Recorder
recorder:ObserveItem("item:71")
assert(not BigBiSListDB.forever.capture,"capture started without opt-in")
assert(recorder:Enable({71}))
recorder:ObserveItem("item:72")
assert(#recorder.capture.records==0,"unrequested item was recorded")
recorder:ObserveItem("item:71")
recorder:ObserveItem("item:71")
assert(#recorder.capture.records==1,"duplicate tooltip")
assert(#recorder.capture.records[1].lines==3,"private creator text was captured")
recorder:Loot()
assert(#recorder.capture.records==2 and not recorder.capture.records[2].npc_id,"ambiguous loot attributed to an NPC")
recorder:QuestReward()
assert(recorder.capture.records[3].quest_id==7 and recorder.capture.records[3].choice)
recorder:Disable()
recorder:Record({kind="quest_reward",item_id=71,quest_id=8})
assert(#recorder.capture.records==3,"disabled recorder wrote data")
'''
        result = subprocess.run([lua, "-"], input=script, text=True, capture_output=True, cwd=ADDON_DIR, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
