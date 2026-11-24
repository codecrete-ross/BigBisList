import unittest
from unittest.mock import patch

from tools.forever_guide_routes import collect, quest_routes
from tools.forever_route_intake import dungeon_page
from tools.project import dataset_json


class ForeverGuideRouteTests(unittest.TestCase):
    def test_quest_chain_intersects_personas_and_uses_highest_minimum(self):
        races = dataset_json("forever", "leveling_rules")["races"]
        alliance = (1 << 32) | 1
        facts = {"1": {"name": "Prerequisite", "level": 25, "races": alliance},
                 "2": {"name": "Reward", "level": 18, "classes": 1, "prerequisites": [1]}}
        source, = quest_routes(facts, races, {})(2, "choice", "https://www.wowhead.com/forever/quest=2")
        self.assertEqual("Alliance", source["side"])
        self.assertEqual({"classes": ["Warrior"], "races": ["Human", "Skyborne"], "min_level": 25}, source["eligibility"])
        self.assertEqual([(1, "prerequisite"), (2, "reward")], [(q["quest_id"], q["kind"]) for q in source["quest_steps"]])
        facts["1"]["gate"] = "quest starter access"
        self.assertIsNone(quest_routes(facts, races, {})(2, "choice", "https://www.wowhead.com/forever/quest=2"))

    def test_both_factions_with_one_skyborne_variant_keep_separate_eligibility(self):
        races = dataset_json("forever", "leveling_rules")["races"]
        q = {"1": {"name": "Reward", "level": 1, "races": 3 | (1 << 32)}}
        branches = quest_routes(q, races, {})(1, "guaranteed", "https://www.wowhead.com/forever/quest=1")
        self.assertEqual({b["side"]: b["eligibility"]["races"] for b in branches},
                         {"Alliance": ["Human", "Skyborne"], "Horde": ["Orc"]})

    def test_loot_pages_keep_encounters_and_separate_equipment_from_quest_items(self):
        page = ('<h1>Uldaman Loot and Bosses</h1><meta name="description" content="Uldaman (level 35 and up)">'
                '<section data-boss="Archaedas"><div class="ltit" data-s="weapon">'
                '<a class="ltinm" href="/item/9418-stoneslayer">Stoneslayer</a></div>'
                '<a href="/item/1-quest">Quest item</a></section><section data-boss="Trash">'
                '<div class="ltit" data-s="head"><a class="ltinm" href="/item/2-hat">Hat</a></div></section>')
        data = dungeon_page(page)
        self.assertEqual(data["groups"], {"Archaedas": [1, 9418], "Trash": [2]})
        self.assertEqual(data["equipment_ids"], [2, 9418])

    def test_catalog_has_same_item_alternate_routes_and_scoped_costs(self):
        groups = dataset_json("forever", "guide_routes")["routes"]
        def sources(i):
            return [g["source"] for g in groups if i in g["items"]]
        self.assertTrue(any(s.get("entity_name") == "Vharr" and s["side"] == "Horde" and s.get("price_copper", 0) > 0
                            for s in sources(2524)))
        self.assertTrue(any(s.get("spell_id") == 8766 and s["profession"] == "Tailoring" for s in sources(7052)))
        self.assertTrue(any(s.get("quest_id") == 1200 and s["reward_type"] == "choice" and s["side"] == "Alliance"
                            and "Skyborne" in s["eligibility"]["races"] for s in sources(7002)))
        self.assertTrue(any(s.get("zone") == "Gnomeregan" for s in sources(9449)))

    def test_an_existing_faction_route_does_not_hide_another_quest_branch(self):
        url = "https://www.wowhead.com/forever/quest=40"
        route = {"type": "quest", "quest_id": 40, "entity_name": "Reward", "source_url": url,
                 "eligibility": {"min_level": 20}, "side": "Alliance"}
        existing = [{"id": 1, "name": "Ring", "sources": [route]},
                    {"id": 2, "name": "Bracers", "sources": [route, {**route, "side": "Horde"}]}]
        equipment = {v["id"]: v for v in existing}
        snapshots = {url: {"relationships": [{"subject_id": 40, "subject_type": "quest", "relation": "reward_choice",
                      "object_id": 1, "object_type": "item", "confidence": "eg_link_observation"}]},
                     "context": {"url": "context", "page_type": "guide_route_context", "npcs": {}, "quests": {},
                                 "item_access": {}}}
        with patch("tools.forever_guide_routes.equipment_records", return_value=equipment):
            catalog, _ = collect(snapshots, {}, existing, [])
        self.assertEqual([([1], "Horde")], [(g["items"], g["source"]["side"]) for g in catalog["routes"]])
