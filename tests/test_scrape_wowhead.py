import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import tools.scrape_wowhead as scraper
from tools.scrape_wowhead import parse_costs, parse_guide_html, parse_item_html, parse_spell_html


class WowheadScraperParserTests(unittest.TestCase):
    def test_guide_parser_extracts_malformed_bis_table_rows(self):
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best in Slot Idols for Restoration Druid in TBC Classic Phase 1</h3>
        <table><br />
          <tr><td><b>Rank</b></td><td><b>Item</b></td><td><b>Source</b></td></tr><br />
          <tr><td>BiS</td><br />
            <td><a href="/tbc/item=28568/idol-of-the-avian-heart">Idol of the Avian Heart</a></td><br />
            <td>Drop: <a href="/tbc/npc=15687/moroes">Moroes</a> (Karazhan)</td>
          </tr><br />
        </table>
        </body></html>
        """
        snapshot = parse_guide_html("https://www.wowhead.com/tbc/guide/example", html)
        self.assertEqual(snapshot["page_type"], "guide")
        self.assertEqual(snapshot["tables"][0]["slot"], "Idol")
        row = snapshot["tables"][0]["rows"][0]
        self.assertEqual(row["item_id"], 28568)
        self.assertEqual(row["rank_label"], "BiS")
        self.assertEqual(row["source_links"][0]["href"], "https://www.wowhead.com/tbc/npc=15687/moroes")

    def test_heroic_guide_source_text_enriches_drop_source_difficulty(self):
        guide = parse_guide_html(
            "https://www.wowhead.com/tbc/guide/example",
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Back Armor for Arms Warrior in TBC Classic Phase 1</h3>
            <table>
              <tr><td>Optional</td><td><a href="/tbc/item=28371/netherfury-cape">Netherfury Cape</a></td><td>Drop: <a href="/tbc/npc=17977/warp-splinter">Warp Splinter</a> (Heroic The Botanica)</td></tr>
            </table>
            </body></html>
            """,
        )
        source = {
            "type": "drop",
            "entity_id": 17977,
            "entity_name": "Warp Splinter",
            "zone": "The Botanica",
            "confidence": "fixture",
        }
        hints = scraper.guide_item_source_hints([guide])[28371]
        enriched = scraper.apply_source_hints_to_sources([source], hints)
        classified = scraper.classify_source(enriched[0])

        self.assertEqual(classified["zone"], "The Botanica")
        self.assertEqual(classified["difficulty"], "heroic")
        self.assertEqual(classified["content_type"], "heroic_dungeon")

    def test_guide_parser_does_not_import_nested_table_rows_under_parent_slot(self):
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best in Slot Feet Armor for Beast Mastery Hunter in TBC Classic Phase 4</h3>
        <table>
          <tr>
            <td>Best</td>
            <td><a href="/tbc/item=33222/quickstrider-moccasins">Quickstrider Moccasins</a></td>
            <td>Drop: Boss
              <table>
                <tr><td>Best</td><td><a href="/tbc/item=32260/choker-of-endless-nightmares">Choker of Endless Nightmares</a></td><td>Drop: Other Boss</td></tr>
              </table>
            </td>
          </tr>
        </table>
        </body></html>
        """
        snapshot = parse_guide_html("https://www.wowhead.com/tbc/guide/example", html)
        self.assertEqual(len(snapshot["tables"]), 1)
        self.assertEqual([row["item_id"] for row in snapshot["tables"][0]["rows"]], [33222])

    def test_guide_parser_classifies_weapon_offhand_and_ammo_headings(self):
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best in Slot Weapons for Elemental Shaman in TBC Classic Phase 4</h3>
        <table><tr><td>Best</td><td><a href="/tbc/item=33354/wubs-cursed-hexblade">Wub's Cursed Hexblade</a></td><td>Drop</td></tr></table>
        <h3>Best in Slot Off Hands and Shields for Holy Paladin in TBC Classic Pre-Raid</h3>
        <table><tr><td>BiS</td><td><a href="/tbc/item=29267/light-bearers-faith-shield">Light-Bearer's Faith Shield</a></td><td>Quest</td></tr></table>
        <h3>Quivers / Ammo Pouches for Beast Mastery Hunter DPS in TBC Classic Phase 1</h3>
        <table><tr><td>BiS</td><td><a href="/tbc/item=29143/clefthoof-hide-quiver">Clefthoof Hide Quiver</a></td><td>Vendor</td></tr></table>
        <h3>Ammunition for Beast Mastery Hunter DPS in TBC Classic Phase 1</h3>
        <table><tr><td>BiS</td><td><a href="/tbc/item=28056/blackflight-arrow">Blackflight Arrow</a></td><td>Vendor</td></tr></table>
        </body></html>
        """
        snapshot = parse_guide_html("https://www.wowhead.com/tbc/guide/example", html)
        self.assertEqual([table["slot"] for table in snapshot["tables"]], ["Weapon", "Off Hand", "Quiver", "Ammo"])
        self.assertTrue(all(table["data_family"] == "bis_lists" for table in snapshot["tables"]))

    def test_bis_import_derives_generic_weapon_slots_from_item_pages(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-weapons"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Weapons for Elemental Shaman in TBC Classic Phase 4</h3>
            <table>
              <tr><td>Best</td><td><a href="/tbc/item=33354/wubs-cursed-hexblade">Wub's Cursed Hexblade</a></td><td>Drop</td></tr>
              <tr><td>Option</td><td><a href="/tbc/item=32374/zhardoom-greatstaff-of-the-devourer">Zhar'doom</a></td><td>Drop</td></tr>
            </table>
            </body></html>
            """,
        )
        one_hand = parse_item_html(
            "https://www.wowhead.com/tbc/item=33354/wubs-cursed-hexblade",
            '<html><head><title>Wub - Item - TBC Classic</title><meta name="description" content="This epic weapon goes in the &quot;One-Hand&quot; slot."></head><body></body></html>',
        )
        two_hand = parse_item_html(
            "https://www.wowhead.com/tbc/item=32374/zhardoom-greatstaff-of-the-devourer",
            '<html><head><title>Zhar - Item - TBC Classic</title><meta name="description" content="This epic staff goes in the &quot;Two-Hand&quot; slot."></head><body></body></html>',
        )
        source = {"id": "synthetic", "url": guide_url, "data_family": "bis_lists", "class": "Shaman", "spec": "Elemental", "phase": "ZA"}
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            rows = scraper.import_bis_lists_from_snapshots([guide_snapshot, one_hand, two_hand])["lists"]
        finally:
            scraper.manifest_sources_by_url = original
        self.assertEqual({row["slot"] for row in rows}, {"Main Hand", "Two Hand"})

    def test_bis_import_dedupes_same_item_contexts_with_best_label(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-duplicates"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Two-Hand Weapons for Restoration Shaman in TBC Classic Phase 1</h3>
            <table>
              <tr><td>Option</td><td><a href="/tbc/item=28604/terestians-stranglestaff">Terestian's Stranglestaff</a></td><td>Drop</td></tr>
              <tr><td>Innervate</td><td><a href="/tbc/item=28604/terestians-stranglestaff">Terestian's Stranglestaff</a></td><td>Drop</td></tr>
            </table>
            <h3>Best in Slot Wrists for Feral Druid in TBC Classic Phase 1</h3>
            <table>
              <tr><td>Alternative (unrealistic)</td><td><a href="/tbc/item=30685/ravagers-wrist-wraps">Ravager's Wrist-Wraps</a></td><td>Drop</td></tr>
              <tr><td>Best (Unrealistic)</td><td><a href="/tbc/item=30685/ravagers-wrist-wraps">Ravager's Wrist-Wraps</a></td><td>Drop</td></tr>
            </table>
            </body></html>
            """,
        )
        source = {"id": "synthetic", "url": guide_url, "data_family": "bis_lists", "class": "Shaman", "spec": "Restoration", "phase": "T4"}
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            rows = scraper.import_bis_lists_from_snapshots([guide_snapshot])["lists"]
        finally:
            scraper.manifest_sources_by_url = original

        items_by_slot = {row["slot"]: row["items"] for row in rows}
        self.assertEqual(len(items_by_slot["Two Hand"]), 1)
        self.assertEqual(items_by_slot["Two Hand"][0]["rank_label"], "Innervate")
        self.assertEqual(len(items_by_slot["Wrist"]), 1)
        self.assertEqual(items_by_slot["Wrist"][0]["rank_label"], "Best (Unrealistic)")

    def test_rank_normalization_preserves_wowhead_best_as_top_rank(self):
        self.assertEqual(scraper.rank_group_from_label("Best"), "bis")
        self.assertEqual(scraper.rank_group_from_label("Best Threat"), "bis")
        self.assertEqual(scraper.rank_group_from_label("Best Mitigation"), "bis")
        self.assertEqual(scraper.rank_group_from_label("Best in slot"), "bis")
        self.assertEqual(scraper.rank_group_from_label("Best 6%"), "bis")
        self.assertEqual(scraper.rank_group_from_label("BiS (Raid DPS)"), "bis")
        self.assertEqual(scraper.rank_group_from_label("Best Until Tier 5"), "situational")
        self.assertEqual(scraper.rank_group_from_label("Near Best"), "option")
        self.assertEqual(scraper.rank_group_from_label("Best Alternative"), "option")
        self.assertEqual(scraper.rank_group_from_label("Best (Unrealistic)"), "unrealistic")
        self.assertEqual(scraper.rank_group_from_label("PvP"), "pvp")
        self.assertEqual(scraper.rank_group_from_label("Best Non PvP"), "bis")
        self.assertEqual(scraper.normalize_rank_group_value("situational_bis", "BiS (Group Performance)"), "bis")

    def test_bis_import_keeps_source_row_order_as_rank(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-best-variants"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Two-Hand Weapons for Feral Druid in TBC Classic Phase 2</h3>
            <table>
              <tr><td>Best Mitigation</td><td><a href="/tbc/item=30021/wildfury-greatstaff">Wildfury Greatstaff</a></td><td>Drop</td></tr>
              <tr><td>Best Threat</td><td><a href="/tbc/item=32014/merciless-gladiators-maul">Merciless Gladiator's Maul</a></td><td>Vendor</td></tr>
            </table>
            </body></html>
            """,
        )
        source = {"id": "synthetic", "url": guide_url, "data_family": "bis_lists", "class": "Druid", "spec": "Feral tank", "phase": "T5"}
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            row = scraper.import_bis_lists_from_snapshots([guide_snapshot])["lists"][0]
        finally:
            scraper.manifest_sources_by_url = original

        by_item_id = {item["item_id"]: item for item in row["items"]}
        self.assertEqual(by_item_id[30021]["rank_group"], "bis")
        self.assertEqual(by_item_id[30021]["context"], "mitigation")
        self.assertEqual(by_item_id[30021]["rank"], 1)
        self.assertEqual(by_item_id[32014]["rank_group"], "bis")
        self.assertEqual(by_item_id[32014]["context"], "threat")
        self.assertEqual(by_item_id[32014]["rank"], 2)

    def test_requirement_audit_ignores_leveling_rotation_verbs(self):
        self.assertFalse(scraper.requirement_looks_like_text("Renew may be used, but require reapplying Shadowform before pulling."))

    def test_item_parser_extracts_drop_vendor_quest_and_crafted_sources(self):
        html = """
        <html><head>
        <title>Idol of the Avian Heart - Item - TBC Classic</title>
        <meta name="description" content="This epic idol goes in the Relic slot.">
        </head><body>
        <script>
        g_items[28568].tooltip_enus = "<table><tr><td><b class=\\"q4\\">Idol of the Avian Heart</b><br>Binds when equipped</td></tr></table>";
        new Listview({ id: 'dropped-by', data: [{"id":15687,"name":"Moroes","location":[3457],"count":316,"outof":1888}], });
        new Listview({ id: 'sold-by', data: [{"id":18525,"name":"G'eras","location":[3703],"cost":[0,[],[[29434,20]]]}], });
        new Listview({ id: 'reward-from-q', data: [{"id":10744,"name":"News of Victory","category":3520,"side":1}], });
        new Listview({ id: 'created-by', data: [{"id":28030,"name":"Heavy Knothide Armor Kit","skill":"Leatherworking"}], });
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=28568/idol-of-the-avian-heart", html)
        self.assertEqual(snapshot["item_id"], 28568)
        self.assertEqual(snapshot["quality"], "epic")
        self.assertEqual(snapshot["binding"], "bind_on_equip")
        self.assertTrue(snapshot["boe"])
        by_type = {source["type"]: source for source in snapshot["normalized_sources"]}
        self.assertEqual(by_type["drop"]["entity_name"], "Moroes")
        self.assertEqual(by_type["drop"]["zone"], "Karazhan")
        self.assertEqual(by_type["drop"]["drop_percent"], 16.74)
        self.assertEqual(by_type["vendor"]["costs"][0]["name"], "Badge of Justice")
        self.assertEqual(by_type["quest"]["side"], "Alliance")
        self.assertEqual(by_type["crafted"]["profession"], "Leatherworking")

    def test_item_parser_attaches_recipe_source_zone_to_crafted_source(self):
        html = """
        <html><head>
        <title>Hard Khorium Band - Item - TBC Classic</title>
        <meta name="description" content="This epic ring goes in the Finger slot.">
        </head><body>
        <script>
        g_items[34361].tooltip_enus = "<table><tr><td><b class=\\"q4\\">Hard Khorium Band</b><br>Binds when equipped</td></tr></table>";
        new Listview({ id: 'created-by-spell', data: [{"id":46124,"name":"Hard Khorium Band","skill":"Jewelcrafting"}], });
        new Listview({ id: 'taught-by-item', data: [{"id":35200,"name":"Design: Hard Khorium Band","source":[2],"sourcemore":[{"z":4075}]}], });
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=34361/hard-khorium-band", html)
        source = snapshot["normalized_sources"][0]
        self.assertEqual(source["type"], "crafted")
        self.assertEqual(source["zone"], "Sunwell Plateau")
        self.assertEqual(source["recipe_sources"][0]["type"], "drop")
        self.assertEqual(source["recipe_sources"][0]["item_id"], 35200)
        self.assertEqual(source["recipe_sources"][0]["zone"], "Sunwell Plateau")

    def test_cost_parser_handles_flat_and_live_wowhead_shapes(self):
        self.assertEqual(parse_costs([0, [], [[29434, 20]]])[0]["currency_id"], 29434)
        live_shape_cost = parse_costs([[0, [], [[31095, 1]]]])[0]
        self.assertEqual(live_shape_cost["item_id"], 31095)
        self.assertEqual(live_shape_cost["amount"], 1)

    def test_item_parser_extracts_vendor_item_cost_tokens(self):
        html = """
        <html><head>
        <title>Thunderheart Helmet - Item - TBC Classic</title>
        <meta name="description" content="This epic leather armor goes in the Head slot.">
        </head><body>
        <script>
        new Listview({ id: 'sold-by', data: [{"id":23437,"name":"Tydormu","location":[3606],"cost":[[0,[],[[31095,1]]]]}], });
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=31037/thunderheart-helmet", html)
        source = snapshot["normalized_sources"][0]
        self.assertEqual(source["type"], "vendor")
        self.assertEqual(source["entity_name"], "Tydormu")
        self.assertEqual(source["zone"], "Hyjal Summit")
        self.assertEqual(source["costs"][0]["item_id"], 31095)
        self.assertEqual(source["costs"][0]["amount"], 1)

    def test_item_parser_extracts_binding_from_main_tooltip(self):
        html = """
        <html><head>
        <title>Thunderheart Helmet - Item - TBC Classic</title>
        <meta name="description" content="This epic leather armor goes in the Head slot.">
        </head><body>
        <script>
        g_items[31037].tooltip_enus = "<table><tr><td><b class=\\"q4\\">Thunderheart Helmet</b><br>Binds when picked up</td></tr></table>";
        g_items[31095].tooltip_enus = "<table><tr><td><b class=\\"q4\\">Helm of the Forgotten Protector</b><br>Binds when picked up</td></tr></table>";
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=31037/thunderheart-helmet", html)
        self.assertEqual(snapshot["binding"], "bind_on_pickup")
        self.assertFalse(snapshot["boe"])

    def test_item_parser_extracts_item_corpus_stats(self):
        html = """
        <html><head>
        <title>Fixture Sword - Item - TBC Classic</title>
        <meta name="description" content="This blue two-handed sword has an item level of 100. In the Two-Handed Swords category.">
        </head><body>
        <script>
        g_items[99901].tooltip_enus = "<table><tr><td><b class=\\"q3\\">Fixture Sword</b><br>Binds when equipped<br>Two-Hand Sword<br>189 - 284 Damage Speed 3.60<br>(65.7 damage per second)<br>+24 Strength<br>+18 Stamina<br>Requires Level 64<br>Classes: Paladin, Warrior<br>Red Socket<br>Blue Socket<br>Socket Bonus: +4 Strength<br>Equip: Increases your critical strike rating by 19.</td></tr></table>";
        new Listview({ id: 'dropped-by', data: [{"id":123,"name":"Fixture Boss","location":[3518],"count":10,"outof":100}], });
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=99901/fixture-sword", html)
        stats = snapshot["item_stats"]

        self.assertEqual(stats["required_level"], 64)
        self.assertEqual(stats["item_level"], 100)
        self.assertEqual(stats["slot"], "Two Hand")
        self.assertEqual(stats["weapon_type"], "Two Hand")
        self.assertEqual(stats["weapon_subtype"], "Sword")
        self.assertEqual(stats["weapon_speed"], 3.6)
        self.assertEqual(stats["weapon_min_damage"], 189)
        self.assertEqual(stats["weapon_max_damage"], 284)
        self.assertEqual(stats["dps"], 65.7)
        self.assertEqual(stats["stats"]["strength"], 24)
        self.assertEqual(stats["stats"]["stamina"], 18)
        self.assertEqual(stats["stats"]["crit_rating"], 19)
        self.assertEqual(stats["sockets"], ["red", "blue"])
        self.assertEqual(stats["socket_bonus"]["strength"], 4)
        self.assertEqual(stats["restrictions"]["classes"], ["Paladin", "Warrior"])
        self.assertEqual(stats["primary_source"]["type"], "drop")

    def test_item_parser_handles_split_wowhead_tooltip_fields(self):
        html = """
        <html><head>
        <title>Shaarde the Greater - Item - TBC Classic</title>
        <meta name="description" content="This blue two-handed sword has an item level of 97.">
        </head><body>
        <script>
        g_items[25944].tooltip_enus = "<table><tr><td><span>Item Level <!--ilvl-->97</span><br>Binds when picked up<table width=\\"100%\\"><tr><td>Two-Hand</td><th>Sword</th></tr></table><table width=\\"100%\\"><tr><td><span><!--dmg-->205 - 309 Damage</span></td><th>Speed <!--spd-->3.40</th></tr></table>(75.59 damage per second)<br><span>+34 Strength</span><br><span>+33 Stamina</span></td></tr></table><table><tr><td>Requires Level <!--rlvl-->64<br><span>Equip: Improves critical strike rating by <!--rtg32-->29.</span></td></tr></table>";
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=25944/shaarde-the-greater", html)
        stats = snapshot["item_stats"]

        self.assertEqual(stats["required_level"], 64)
        self.assertEqual(stats["item_level"], 97)
        self.assertEqual(stats["weapon_min_damage"], 205)
        self.assertEqual(stats["weapon_max_damage"], 309)
        self.assertEqual(stats["weapon_speed"], 3.4)
        self.assertEqual(stats["stats"]["crit_rating"], 29)

    def test_item_list_parser_discovers_listview_and_linked_items(self):
        html = """
        <html><head><title>Items</title></head><body>
        <script>
        new Listview({ id: 'items', data: [{"id":30311,"name":"Warp Slicer","level":100,"reqlevel":64}], });
        </script>
        <a href="/tbc/item=31331/fixture-link">Fixture Link</a>
        </body></html>
        """
        snapshot = scraper.parse_item_list_html("https://www.wowhead.com/tbc/items", html)
        refs = {ref["id"]: ref for ref in snapshot["item_refs"]}

        self.assertEqual(snapshot["page_type"], "item_list")
        self.assertIn(30311, refs)
        self.assertIn(31331, refs)
        self.assertEqual(refs[30311]["required_level"], 64)
        self.assertIn("https://www.wowhead.com/tbc/item=30311/warp-slicer", scraper.discover_item_urls([snapshot]))

    def test_item_list_parser_discovers_variable_backed_listview_rows(self):
        html = """
        <html><head><title>Items</title></head><body>
        <script>
        var listviewitems = [{"id":30311,"name":"Warp Slicer","level":100,"reqlevel":64,firstseenpatch: 0,popularity:42}];
        new Listview({template: 'item', id: 'items', data: listviewitems});
        new Listview({template: 'generic-model', id: 'itemsgallery', data: WH.cOr([], listviewitems)});
        </script>
        </body></html>
        """
        snapshot = scraper.parse_item_list_html("https://www.wowhead.com/tbc/items", html)
        refs = {ref["id"]: ref for ref in snapshot["item_refs"]}

        self.assertEqual(snapshot["summary"]["listviews"], ["items", "itemsgallery"])
        self.assertEqual(refs[30311]["name"], "Warp Slicer")
        self.assertEqual(refs[30311]["required_level"], 64)

    def test_item_list_parser_uses_wowhead_apostrophe_slugs(self):
        html = """
        <html><head><title>Items</title></head><body>
        <script>
        var listviewitems = [{"id":10142,"name":"High Councillor's Mantle","level":65,"reqlevel":60,"slot":3}];
        new Listview({template: 'item', id: 'items', data: listviewitems});
        </script>
        </body></html>
        """

        snapshot = scraper.parse_item_list_html("https://www.wowhead.com/tbc/items=4.1?filter=sl=3", html)

        self.assertEqual(snapshot["item_refs"][0]["url"], "https://www.wowhead.com/tbc/item=10142/high-councillors-mantle")

    def test_item_corpus_discovery_filters_non_equipment_and_high_level_rows(self):
        snapshot = {
            "page_type": "item_list",
            "item_refs": [
                {"id": 30311, "url": "https://www.wowhead.com/tbc/item=30311", "slot": 13, "required_level": 64},
                {"id": 1206, "url": "https://www.wowhead.com/tbc/item=1206", "slot": 0, "required_level": None},
                {"id": 34334, "url": "https://www.wowhead.com/tbc/item=34334", "slot": 15, "required_level": 70},
                {"id": 99999, "url": "https://www.wowhead.com/tbc/item=99999", "slot": 17, "required_level": 71},
                {"id": 88801, "url": "https://www.wowhead.com/tbc/item=88801", "slot": 12, "level": 141, "required_level": None},
                {"id": 88802, "url": "https://www.wowhead.com/tbc/item=88802", "slot": 12, "level": 20, "required_level": None},
            ],
        }

        self.assertEqual(
            scraper.discover_item_corpus_urls([snapshot]),
            [
                "https://www.wowhead.com/tbc/item=30311",
                "https://www.wowhead.com/tbc/item=34334",
                "https://www.wowhead.com/tbc/item=88802",
            ],
        )

    def test_item_list_parser_records_truncated_listview_metadata(self):
        html = """
        <html><head><title>Items</title></head><body>
        <script>
        var listviewitems = [{"id":30311,"name":"Warp Slicer","level":100,"reqlevel":64,"slot":13}];
        new Listview({template: 'item', id: 'items', note: "2,741 items found (1,000 displayed) - Try filtering your results", _truncated: 1, data: listviewitems});
        </script>
        </body></html>
        """

        snapshot = scraper.parse_item_list_html("https://www.wowhead.com/tbc/items=4.1", html)

        self.assertTrue(snapshot["summary"]["truncated"])
        self.assertEqual(snapshot["summary"]["total_items"], 2741)
        self.assertEqual(snapshot["summary"]["displayed_items"], 1000)

    def test_authoritative_item_corpus_discovery_includes_shaarde_without_seed(self):
        category_url = "https://www.wowhead.com/tbc/items/weapons/two-handed-swords"
        original_canonical_json = scraper.canonical_json
        scraper.canonical_json = lambda name: {
            "sources": [
                {
                    "id": "item-corpus",
                    "url": "https://www.wowhead.com/tbc/items",
                    "url_policy": "bootstrap_only",
                    "data_family": "item_corpus",
                    "discovery_urls": [category_url],
                }
            ]
        } if name == "scrape_manifest" else original_canonical_json(name)
        try:
            snapshot = {
                "url": category_url,
                "page_type": "item_list",
                "item_refs": [
                    {"id": 25944, "url": "https://www.wowhead.com/tbc/item=25944", "slot": 17, "level": 97, "required_level": 64},
                ],
            }

            self.assertEqual(scraper.item_corpus_manifest_item_ids(), set())
            self.assertEqual(
                scraper.discover_item_corpus_urls([snapshot], authoritative_only=True),
                ["https://www.wowhead.com/tbc/item=25944"],
            )
        finally:
            scraper.canonical_json = original_canonical_json

    def test_item_stats_import_uses_item_list_metadata_as_fallback(self):
        list_snapshot = scraper.parse_item_list_html(
            "https://www.wowhead.com/tbc/items=4.1?filter=sl=6",
            """
            <html><head><title>Items</title></head><body><script>
            var listviewitems = [{"id":21846,"name":"Spellfire Belt","level":105,"reqlevel":70,"quality":4,"slot":6}];
            new Listview({ id: 'items', data: listviewitems });
            </script></body></html>
            """,
        )
        item_snapshot = scraper.parse_item_html(
            "https://www.wowhead.com/tbc/item=21846",
            """
            <html><head><title>Spellfire Belt - Item - TBC Classic</title>
            <meta name="description" content="Spellfire Belt is a Cloth belt crafted by Tailors.">
            </head><body><script>
            g_items[21846].tooltip_enus = "<table><tr><td><b>Spellfire Belt</b><br>Waist<br>100 Armor<br>+18 Intellect</td></tr></table>";
            </script></body></html>
            """,
        )
        row = scraper.import_item_stats_from_snapshots([list_snapshot, item_snapshot])["item_stats"][0]

        self.assertEqual(row["required_level"], 70)
        self.assertEqual(row["item_level"], 105)
        self.assertEqual(row["quality"], "epic")
        self.assertEqual(row["slot"], "Waist")

    def test_item_stats_import_keeps_manifest_seed_items(self):
        original_canonical_json = scraper.canonical_json
        scraper.canonical_json = lambda name: {
            "sources": [
                {
                    "url": "https://www.wowhead.com/tbc/items",
                    "data_family": "item_corpus",
                    "seed_urls": ["https://www.wowhead.com/tbc/item=25944/shaarde-the-greater"],
                }
            ]
        } if name == "scrape_manifest" else original_canonical_json(name)
        try:
            list_snapshot = scraper.parse_item_list_html(
                "https://www.wowhead.com/tbc/items",
                """
                <html><head><title>Items</title></head><body><script>
                var listviewitems = [{"id":21846,"name":"Spellfire Belt","level":105,"reqlevel":70,"quality":4,"slot":6}];
                new Listview({ id: 'items', data: listviewitems });
                </script></body></html>
                """,
            )
            seed_snapshot = scraper.parse_item_html(
                "https://www.wowhead.com/tbc/item=25944/shaarde-the-greater",
                """
                <html><head><title>Shaarde the Greater - Item - TBC Classic</title>
                <meta name="description" content="This blue two-handed weapon has an item level of 97.">
                </head><body><script>
                g_items[25944].tooltip_enus = "<table><tr><td><b class=\\"q3\\">Shaarde the Greater</b><br>Binds when picked up<br>Two-Hand Sword<br>188 - 283 Damage Speed 3.40<br>(69.3 damage per second)<br>Requires Level 64</td></tr></table>";
                </script></body></html>
                """,
            )
            listed_snapshot = scraper.parse_item_html(
                "https://www.wowhead.com/tbc/item=21846/spellfire-belt",
                """
                <html><head><title>Spellfire Belt - Item - TBC Classic</title></head><body><script>
                g_items[21846].tooltip_enus = "<table><tr><td><b>Spellfire Belt</b><br>Waist<br>+18 Intellect</td></tr></table>";
                </script></body></html>
                """,
            )
            unlisted_snapshot = scraper.parse_item_html(
                "https://www.wowhead.com/tbc/item=99902/unlisted",
                """
                <html><head><title>Unlisted - Item - TBC Classic</title></head><body><script>
                g_items[99902].tooltip_enus = "<table><tr><td><b>Unlisted</b><br>Waist<br>+1 Strength</td></tr></table>";
                </script></body></html>
                """,
            )
            item_ids = {
                row["id"]
                for row in scraper.import_item_stats_from_snapshots([list_snapshot, seed_snapshot, listed_snapshot, unlisted_snapshot])["item_stats"]
            }

            self.assertEqual(scraper.item_corpus_manifest_item_ids(), {25944})
            self.assertEqual(set(scraper.manifest_urls("item_corpus")), {
                "https://www.wowhead.com/tbc/items",
                "https://www.wowhead.com/tbc/item=25944/shaarde-the-greater",
            })
            self.assertEqual(item_ids, {21846, 25944})
        finally:
            scraper.canonical_json = original_canonical_json

    def test_item_corpus_audit_requires_manifest_seed_item_snapshots(self):
        original_canonical_json = scraper.canonical_json
        scraper.canonical_json = lambda name: {
            "sources": [
                {
                    "url": "https://www.wowhead.com/tbc/items",
                    "data_family": "item_corpus",
                    "seed_urls": ["https://www.wowhead.com/tbc/item=25944/shaarde-the-greater"],
                }
            ]
        } if name == "scrape_manifest" else original_canonical_json(name)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                input_dir = Path(tmp)
                list_snapshot = scraper.parse_item_list_html(
                    "https://www.wowhead.com/tbc/items",
                    """
                    <html><head><title>Items</title></head><body><script>
                    var listviewitems = [{"id":21846,"name":"Spellfire Belt","level":105,"reqlevel":70,"quality":4,"slot":6}];
                    new Listview({ id: 'items', data: listviewitems });
                    </script></body></html>
                    """,
                )
                (input_dir / "items.json").write_text(json.dumps(list_snapshot), encoding="utf-8")

                audit = scraper.build_item_corpus_audit(input_dir)

            self.assertFalse(audit["ok"])
            self.assertIn(
                "Missing item page snapshot for corpus item 25944: https://www.wowhead.com/tbc/item=25944",
                audit["errors"],
            )
        finally:
            scraper.canonical_json = original_canonical_json

    def test_item_corpus_audit_rejects_truncated_authoritative_lists(self):
        category_url = "https://www.wowhead.com/tbc/items=4.1?filter=sl=6"
        original_canonical_json = scraper.canonical_json
        scraper.canonical_json = lambda name: {
            "sources": [
                {
                    "id": "item-corpus",
                    "url": "https://www.wowhead.com/tbc/items",
                    "url_policy": "bootstrap_only",
                    "data_family": "item_corpus",
                    "discovery_urls": [category_url],
                }
            ]
        } if name == "scrape_manifest" else original_canonical_json(name)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                input_dir = Path(tmp)
                snapshot = {
                    "parser_version": scraper.PARSER_VERSION,
                    "url": category_url,
                    "page_type": "item_list",
                    "item_refs": [
                        {"id": item_id, "url": f"https://www.wowhead.com/tbc/item={item_id}", "slot": 6, "level": 10, "required_level": 5}
                        for item_id in range(1, 1001)
                    ],
                    "summary": {"truncated": True, "displayed_items": 1000, "total_items": 2741},
                }
                (input_dir / "items.json").write_text(json.dumps(snapshot), encoding="utf-8")

                audit = scraper.build_item_corpus_audit(input_dir)

            self.assertFalse(audit["ok"])
            self.assertTrue(any("Truncated item list snapshot" in error for error in audit["errors"]))
        finally:
            scraper.canonical_json = original_canonical_json

    def test_bootstrap_item_list_cannot_satisfy_item_corpus_audit(self):
        original_canonical_json = scraper.canonical_json
        scraper.canonical_json = lambda name: {
            "sources": [
                {
                    "id": "item-corpus",
                    "url": "https://www.wowhead.com/tbc/items",
                    "url_policy": "bootstrap_only",
                    "data_family": "item_corpus",
                }
            ]
        } if name == "scrape_manifest" else original_canonical_json(name)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                input_dir = Path(tmp)
                list_snapshot = {
                    "parser_version": scraper.PARSER_VERSION,
                    "url": "https://www.wowhead.com/tbc/items",
                    "page_type": "item_list",
                    "item_refs": [
                        {"id": 25944, "url": "https://www.wowhead.com/tbc/item=25944", "slot": 17, "level": 97, "required_level": 64}
                    ],
                    "summary": {"truncated": True, "displayed_items": 1000, "total_items": 12000},
                }
                (input_dir / "items.json").write_text(json.dumps(list_snapshot), encoding="utf-8")

                audit = scraper.build_item_corpus_audit(input_dir)

            self.assertFalse(audit["ok"])
            self.assertIn("No authoritative item list snapshots found for item corpus", audit["errors"])
        finally:
            scraper.canonical_json = original_canonical_json

    def test_missing_only_item_corpus_fetch_uses_existing_list_snapshots(self):
        category_url = "https://www.wowhead.com/tbc/items/weapons/two-handed-swords"
        missing_url = "https://www.wowhead.com/tbc/item=25944"
        existing_url = "https://www.wowhead.com/tbc/item=30311"
        original_canonical_json = scraper.canonical_json
        original_fetch_url = scraper.fetch_url
        scraper.canonical_json = lambda name: {
            "sources": [
                {
                    "id": "item-corpus",
                    "url": "https://www.wowhead.com/tbc/items",
                    "url_policy": "bootstrap_only",
                    "data_family": "item_corpus",
                    "discovery_urls": [category_url],
                }
            ]
        } if name == "scrape_manifest" else original_canonical_json(name)
        fetched: list[str] = []
        scraper.fetch_url = lambda url, cache_dir, retries=3, delay=0.75: fetched.append(url) or """
            <html><head><title>Shaarde the Greater - Item - TBC Classic</title></head><body><script>
            g_items[25944].tooltip_enus = "<table><tr><td><b>Shaarde the Greater</b><br>Two-Hand Sword<br>Requires Level 64</td></tr></table>";
            </script></body></html>
        """
        try:
            with tempfile.TemporaryDirectory() as tmp:
                input_dir = Path(tmp)
                list_snapshot = {
                    "parser_version": scraper.PARSER_VERSION,
                    "url": category_url,
                    "page_type": "item_list",
                    "item_refs": [
                        {"id": 25944, "url": missing_url, "slot": 17, "level": 97, "required_level": 64},
                        {"id": 30311, "url": existing_url, "slot": 13, "level": 100, "required_level": 64},
                    ],
                    "summary": {"truncated": False},
                }
                bootstrap_snapshot = {
                    "parser_version": scraper.PARSER_VERSION,
                    "url": "https://www.wowhead.com/tbc/items",
                    "page_type": "item_list",
                    "item_refs": [],
                    "summary": {"truncated": True},
                }
                existing_snapshot = parse_item_html(
                    existing_url,
                    """
                    <html><head><title>Warp Slicer - Item - TBC Classic</title></head><body><script>
                    g_items[30311].tooltip_enus = "<table><tr><td><b>Warp Slicer</b><br>Main Hand Sword<br>Requires Level 64</td></tr></table>";
                    </script></body></html>
                    """,
                )
                (input_dir / "items.json").write_text(json.dumps(list_snapshot), encoding="utf-8")
                (input_dir / "bootstrap.json").write_text(json.dumps(bootstrap_snapshot), encoding="utf-8")
                (input_dir / "existing.json").write_text(json.dumps(existing_snapshot), encoding="utf-8")

                result = scraper.command_fetch(
                    SimpleNamespace(
                        output_dir=input_dir,
                        family="item_corpus",
                        url=None,
                        no_discover=False,
                        missing_only=True,
                        limit=1,
                        workers=1,
                        retries=1,
                        delay=0,
                    )
                )

            self.assertEqual(result, 0)
            self.assertEqual(fetched, [missing_url])
        finally:
            scraper.fetch_url = original_fetch_url
            scraper.canonical_json = original_canonical_json

    def test_guide_parser_classifies_non_gear_tables_and_entities(self):
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best Gems for Balance Druid</h3>
        <table>
          <tr><td>PR</td><td><a href="/tbc/item=34220/chaotic-skyfire-diamond">Chaotic Skyfire Diamond</a></td><td>Meta</td></tr>
        </table>
        <h3>Best Enchants for Balance Druid</h3>
        <table>
          <tr><td>Head</td><td><a href="/tbc/spell=46540/enchant-weapon-sunfire">Enchant Weapon - Sunfire</a></td><td>Phase 5</td></tr>
        </table>
        </body></html>
        """
        snapshot = parse_guide_html("https://www.wowhead.com/tbc/guide/example", html)
        self.assertEqual(snapshot["tables"][0]["data_family"], "gems")
        self.assertEqual(snapshot["tables"][0]["rows"][0]["entities"][0]["type"], "item")
        self.assertEqual(snapshot["tables"][1]["data_family"], "enchants")
        self.assertEqual(snapshot["tables"][1]["rows"][0]["entities"][0]["type"], "spell")
        self.assertEqual(snapshot["tables"][1]["rows"][0]["spell_id"], 46540)

    def test_guide_parser_uses_gatherer_names_for_empty_links(self):
        html = """
        <html><head><title>Guide</title></head><body>
        <script>
        WH.Gatherer.addData(6, 5, {"27924":{"name_enus":"Enchant Ring - Spellpower"}});
        </script>
        <h3>Best Enchants</h3>
        <table>
          <tr><td>Ring</td><td><a href="/tbc/spell=27924"></a></td></tr>
        </table>
        </body></html>
        """
        snapshot = parse_guide_html("https://www.wowhead.com/tbc/guide/example", html)
        row = snapshot["tables"][0]["rows"][0]
        self.assertEqual(row["entity_name"], "Enchant Ring - Spellpower")
        self.assertEqual(row["spell_name"], "Enchant Ring - Spellpower")

    def test_guide_parser_extracts_leveling_narrative_sections(self):
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Leveling Rotation Levels 10-20</h3>
        <p>At level 10, use <a href="/tbc/spell=16814/hurricane">Hurricane</a> when multiple enemies are stacked.</p>
        </body></html>
        """
        snapshot = parse_guide_html("https://www.wowhead.com/tbc/guide/leveling-example", html)
        section = snapshot["sections"][0]
        self.assertEqual(section["data_family"], "leveling")
        self.assertEqual(section["entries"][0]["level_range"], "10-20")
        self.assertEqual(section["entries"][0]["entities"][0]["id"], 16814)

    def test_spell_parser_extracts_spell_relationship_sources(self):
        html = """
        <html><head><title>Enchant Weapon - Sunfire - Spell - TBC Classic</title></head><body>
        <script>
        new Listview({ id: 'taught-by-item', data: [{"id":22562,"name":"Formula: Enchant Weapon - Sunfire"}], });
        </script>
        </body></html>
        """
        snapshot = parse_spell_html("https://www.wowhead.com/tbc/spell=46540/enchant-weapon-sunfire", html)
        self.assertEqual(snapshot["spell_id"], 46540)
        self.assertEqual(snapshot["normalized_sources"][0]["type"], "taught_by_item")
        self.assertEqual(snapshot["normalized_sources"][0]["item_id"], 22562)
        self.assertEqual(scraper.discover_related_source_urls([snapshot]), ["https://www.wowhead.com/tbc/item=22562"])

    def test_spell_parser_extracts_trainer_source_from_recipe_listview(self):
        html = """
        <html><head>
        <title>Enchant Bracer - Brawn - Spell - TBC Classic</title>
        <meta name="description" content="Permanently enchants bracers to increase Strength by 12.">
        </head><body>
        <script>
        new Listview({ id: 'recipes', data: [{"id":27899,"name":"Enchant Bracer - Brawn","skill":[333],"learnedat":305,"trainingcost":12500}], });
        </script>
        </body></html>
        """
        snapshot = parse_spell_html("https://www.wowhead.com/tbc/spell=27899/enchant-bracer-brawn", html)
        source = snapshot["normalized_sources"][0]
        self.assertEqual(source["type"], "trainer")
        self.assertEqual(source["entity_name"], "Enchanting Trainer")
        self.assertEqual(source["required_skill"], 305)
        requirement = snapshot["normalized_requirements"][0]
        self.assertEqual(requirement["type"], "profession")
        self.assertEqual(requirement["scope"], "learn_recipe")
        self.assertEqual(requirement["profession"], "Enchanting")
        self.assertEqual(requirement["skill"], 305)

    def test_requirement_parser_extracts_reputation_phrases(self):
        source_url = "https://www.wowhead.com/tbc/guide/example"
        requirements = scraper.extract_requirements_from_text(
            "Vendor: Okuno in Black Temple. Requires Exalted reputation with Ashtongue Deathsworn.",
            source_url,
            "vendor_purchase",
            "parsed_source_text",
        )
        self.assertEqual(requirements[0]["type"], "reputation")
        self.assertEqual(requirements[0]["reputation"], "Ashtongue Deathsworn")
        self.assertEqual(requirements[0]["standing"], "Exalted")

        requirements = scraper.extract_requirements_from_text(
            "Vendor: Fedryen Swiftspear when Revered with Cenarion Expedition",
            source_url,
            "vendor_purchase",
            "parsed_source_text",
        )
        self.assertEqual(requirements[0]["reputation"], "Cenarion Expedition")
        self.assertEqual(requirements[0]["standing"], "Revered")

        requirements = scraper.extract_requirements_from_text(
            "Vendor: Alurmi - Revered with Keepers of Time",
            source_url,
            "vendor_purchase",
            "parsed_source_text",
        )
        self.assertEqual(requirements[0]["type"], "reputation")
        self.assertEqual(requirements[0]["reputation"], "Keepers of Time")
        self.assertEqual(requirements[0]["standing"], "Revered")

        requirements = scraper.extract_requirements_from_text(
            "Quest: Champion's Covenant - Requires Exalted with the Scales of the Sand",
            source_url,
            "quest_reward",
            "parsed_source_text",
        )
        self.assertEqual(requirements[0]["reputation"], "The Scale of the Sands")

        requirements = scraper.extract_requirements_from_text(
            "Vendor: Logistics Officer Ulrike / Quartermaster Urgronn ( Honor Hold / Thrallmar Exalted)",
            source_url,
            "vendor_purchase",
            "parsed_source_text",
        )
        self.assertEqual([requirement["reputation"] for requirement in requirements], ["Honor Hold", "Thrallmar"])

        requirements = scraper.extract_requirements_from_text(
            "Quartermaster Enuril - The Scryers Exalted, Shattrath City",
            source_url,
            "vendor_purchase",
            "parsed_source_text",
        )
        self.assertEqual(requirements[0]["reputation"], "The Scryers")

        requirements = scraper.extract_requirements_from_text(
            "Greater Inscription of Vengeance Item Level 70 Requires Level 70 Requires The Aldor - Exalted Use: Permanently adds attack power.",
            source_url,
            "equip_or_use",
            "wowhead_item",
        )
        self.assertEqual(requirements[0]["type"], "reputation")
        self.assertEqual(requirements[0]["reputation"], "The Aldor")
        self.assertEqual(requirements[0]["standing"], "Exalted")
        self.assertEqual(requirements[0]["standing_rank"], 8)
        self.assertNotIn("faction_choice", {requirement["type"] for requirement in requirements})

        requirements = scraper.extract_requirements_from_text(
            "Requires The Scryers - Revered Equip: Improves spell hit rating.",
            source_url,
            "equip_or_use",
            "wowhead_item",
        )
        self.assertEqual(requirements[0]["type"], "reputation")
        self.assertEqual(requirements[0]["reputation"], "The Scryers")
        self.assertEqual(requirements[0]["standing"], "Revered")
        self.assertNotIn("faction_choice", {requirement["type"] for requirement in requirements})

        requirements = scraper.extract_requirements_from_text(
            "Formula: Enchant Chest - Exceptional Stats Requires Enchanting (345) Requires Honor Hold - Revered Use: Teaches you.",
            source_url,
            "equip_or_use",
            "wowhead_item",
        )
        self.assertIn(
            {
                "type": "reputation",
                "scope": "equip_or_use",
                "source_url": source_url,
                "raw_text": "Formula: Enchant Chest - Exceptional Stats Requires Enchanting (345) Requires Honor Hold - Revered Use: Teaches you.",
                "confidence": "wowhead_item",
                "reputation": "Honor Hold",
                "standing": "Revered",
                "standing_rank": 7,
            },
            requirements,
        )
        self.assertNotIn("Enchanting", [requirement.get("reputation") for requirement in requirements])

        requirements = scraper.extract_requirements_from_text(
            "Requires Level 70 Requires Shattered Sun Offensive - Exalted Equip: Your spells have a chance to call on the power of the Arcane if you're exalted with the Scryers, or the Light if you're exalted with the Aldor.",
            source_url,
            "equip_or_use",
            "wowhead_item",
        )
        self.assertEqual([requirement["reputation"] for requirement in requirements if requirement["type"] == "reputation"], ["Shattered Sun Offensive"])
        self.assertNotIn("faction_choice", {requirement["type"] for requirement in requirements})

    def test_row_requirements_normalize_committed_snapshot_reputation_aliases(self):
        requirements = scraper.row_requirements(
            {
                "normalized_requirements": [
                    {
                        "type": "reputation",
                        "reputation": "The Mag'har / Kurenai",
                        "standing": "Revered",
                        "standing_rank": 7,
                        "scope": "vendor_purchase",
                        "source_url": "https://www.wowhead.com/tbc/guide/example",
                        "confidence": "parsed_source_text",
                    }
                ]
            },
            "https://www.wowhead.com/tbc/guide/example",
        )
        self.assertEqual([requirement["reputation"] for requirement in requirements], ["The Mag'har", "Kurenai"])

    def test_snapshot_requirements_reparse_stale_faction_choice_standing(self):
        requirements = scraper.snapshot_requirements(
            {
                "normalized_requirements": [
                    {
                        "type": "faction_choice",
                        "choices": ["The Aldor"],
                        "raw_text": "Greater Inscription of Vengeance Item Level 70 Requires Level 70 Requires The Aldor - Exalted Use: Permanently adds attack power.",
                        "scope": "equip_or_use",
                        "source_url": "https://www.wowhead.com/tbc/item=28888/greater-inscription-of-vengeance",
                        "confidence": "wowhead_item",
                    }
                ]
            }
        )
        self.assertEqual(requirements[0]["type"], "reputation")
        self.assertEqual(requirements[0]["reputation"], "The Aldor")
        self.assertEqual(requirements[0]["standing_rank"], 8)

    def test_row_requirements_reparse_stale_unknown_text(self):
        requirements = scraper.row_requirements(
            {
                "source_text": "Vendor: Fedryen Swiftspear - Exalted with Cenarion Expedition",
                "normalized_requirements": [
                    {
                        "type": "unknown_text",
                        "raw_text": "Vendor: Fedryen Swiftspear - Exalted with Cenarion Expedition",
                        "scope": "vendor_purchase",
                        "source_url": "https://www.wowhead.com/tbc/guide/example",
                        "confidence": "parsed_source_text",
                    }
                ],
            },
            "https://www.wowhead.com/tbc/guide/example",
        )
        self.assertEqual(requirements[0]["type"], "reputation")
        self.assertEqual(requirements[0]["reputation"], "Cenarion Expedition")

    def test_caverns_of_time_zone_normalizes_known_location_440_vendors(self):
        self.assertEqual(scraper.first_zone_name({"id": 21643, "name": "Alurmi", "location": [440]}), "Caverns of Time")
        self.assertEqual(scraper.first_zone_name({"id": 19932, "name": "Andormu", "location": [440]}), "Caverns of Time")
        self.assertEqual(scraper.first_zone_name({"id": 99999, "name": "Tanaris NPC", "location": [440]}), "Tanaris")

    def test_tbc_dungeon_zone_ids_are_normalized(self):
        cases = {
            2366: "The Black Morass",
            2367: "Old Hillsbrad Foothills",
            3562: "Hellfire Ramparts",
            3713: "The Blood Furnace",
            3714: "The Shattered Halls",
            3715: "The Steamvault",
            3716: "The Underbog",
            3717: "The Slave Pens",
            3789: "Shadow Labyrinth",
            3790: "Auchenai Crypts",
            3791: "Sethekk Halls",
            3792: "Mana-Tombs",
            3847: "The Botanica",
            3848: "The Arcatraz",
            3849: "The Mechanar",
            4131: "Magisters' Terrace",
        }
        for zone_id, expected in cases.items():
            with self.subTest(zone_id=zone_id):
                self.assertEqual(scraper.first_zone_name({"id": 1, "location": [zone_id]}), expected)

    def test_load_snapshots_refreshes_normalized_sources_from_related_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "snapshot.json"
            path.write_text(
                json.dumps(
                    {
                        "parser_version": "fixture",
                        "url": "https://www.wowhead.com/tbc/item=27797/wastewalker-shoulderpads",
                        "page_type": "item",
                        "item_id": 27797,
                        "name": "Wastewalker Shoulderpads",
                        "related_tables": {
                            "dropped-by": [
                                {
                                    "id": 18478,
                                    "name": "Avatar of the Martyred",
                                    "location": [3790],
                                    "count": 14,
                                    "outof": 136,
                                }
                            ]
                        },
                        "normalized_sources": [
                            {
                                "type": "drop",
                                "entity_id": 18478,
                                "entity_name": "Avatar of the Martyred",
                                "source_url": "https://www.wowhead.com/tbc/item=27797/wastewalker-shoulderpads",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = scraper.load_snapshots(Path(tmpdir))[0]

        source = snapshot["normalized_sources"][0]
        self.assertEqual(source["entity_name"], "Avatar of the Martyred")
        self.assertEqual(source["zone"], "Auchenai Crypts")
        self.assertEqual(source["drop_percent"], 10.29)

    def test_item_parser_uses_caverns_of_time_for_known_vendors(self):
        html = """
        <html><head>
        <title>Continuum Blade - Item - TBC Classic</title>
        <meta name="description" content="This rare weapon goes in the One-Hand slot.">
        </head><body>
        <script>
        new Listview({ id: 'sold-by', data: [{"id":21643,"name":"Alurmi","location":[440]}], });
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=29185/continuum-blade", html)
        source = snapshot["normalized_sources"][0]
        self.assertEqual(source["entity_name"], "Alurmi")
        self.assertEqual(source["zone"], "Caverns of Time")

    def test_requirement_parser_extracts_faction_profession_and_specialization(self):
        source_url = "https://www.wowhead.com/tbc/guide/example"
        requirements = scraper.extract_requirements_from_text(
            "Vendor: Eldara Dawnrunner when Exalted with Shattered Sun Offensive and requires The Aldor",
            source_url,
            "vendor_purchase",
            "parsed_source_text",
        )
        self.assertIn("faction_choice", {requirement["type"] for requirement in requirements})
        choice = next(requirement for requirement in requirements if requirement["type"] == "faction_choice")
        self.assertEqual(choice["choices"], ["The Aldor"])

        requirements = scraper.extract_requirements_from_text(
            "Profession: Engineering - BoP only",
            source_url,
            "equip_or_use",
            "parsed_source_text",
        )
        self.assertEqual(requirements[0]["type"], "profession")
        self.assertEqual(requirements[0]["profession"], "Engineering")

        requirements = scraper.extract_requirements_from_text(
            "Crafted: Lionheart Champion - requires Master Swordsmithing",
            source_url,
            "self_craft",
            "parsed_source_text",
        )
        self.assertEqual(requirements[0]["type"], "profession_specialization")
        self.assertEqual(requirements[0]["specialization"], "Master Swordsmithing")

    def test_item_parser_extracts_equip_profession_requirement(self):
        html = """
        <html><head>
        <title>Goggles - Item - TBC Classic</title>
        <meta name="description" content="This epic armor goes in the Head slot.">
        </head><body>
        <script>
        g_items[1].tooltip_enus = "<table><tr><td><b class=\\"q4\\">Goggles</b><br>Requires Engineering (350)</td></tr></table>";
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=1/goggles", html)
        requirement = snapshot["normalized_requirements"][0]
        self.assertEqual(requirement["type"], "profession")
        self.assertEqual(requirement["scope"], "equip_or_use")
        self.assertEqual(requirement["skill"], 350)

    def test_guide_fallback_source_does_not_store_requirement_text_as_zone(self):
        source = scraper.guide_fallback_source(
            {
                "source_text": "Vendor: Nakodu - Requires Exalted with Lower City",
                "source_url": "https://www.wowhead.com/tbc/guide/example",
            }
        )
        self.assertNotIn("zone", source)
        self.assertEqual(source["requirements"][0]["reputation"], "Lower City")

    def test_bis_import_persists_guide_requirements(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-bis"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Head</h3>
            <table><tr>
              <td>BiS</td>
              <td><a href="/tbc/item=29191/glyph-of-power">Glyph of Power</a></td>
              <td>Vendor: Almaador - Requires Revered with The Sha'tar</td>
            </tr></table>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-bis",
            "url": guide_url,
            "data_family": "bis_lists",
            "class": "Druid",
            "spec": "Balance",
            "phase": "PR",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            imported = scraper.import_bis_lists_from_snapshots([guide_snapshot])
        finally:
            scraper.manifest_sources_by_url = original
        requirements = imported["lists"][0]["items"][0]["requirements"]
        self.assertEqual(requirements[0]["type"], "reputation")
        self.assertEqual(requirements[0]["source_url"], guide_url)

    def test_enchant_import_uses_sourced_spell_alias_by_name(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-enchants"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Enchants</h3>
            <table><tr><td>Chest</td><td><a href="/tbc/spell=46502/enchant-chest-exceptional-stats">Enchant Chest - Exceptional Stats</a></td></tr></table>
            </body></html>
            """,
        )
        anniversary_spell = parse_spell_html(
            "https://www.wowhead.com/tbc/spell=46502/enchant-chest-exceptional-stats",
            "<html><head><title>Enchant Chest - Exceptional Stats - Spell - TBC Classic</title></head><body></body></html>",
        )
        sourced_spell = parse_spell_html(
            "https://www.wowhead.com/tbc/spell=27960/enchant-chest-exceptional-stats",
            """
            <html><head><title>Enchant Chest - Exceptional Stats - Spell - TBC Classic</title></head><body>
            <script>
            new Listview({ id: 'taught-by-item', data: [{"id":22547,"name":"Formula: Enchant Chest - Exceptional Stats"}], });
            </script>
            </body></html>
            """,
        )
        formula_item = parse_item_html(
            "https://www.wowhead.com/tbc/item=22547/formula-enchant-chest-exceptional-stats",
            "<html><head><title>Formula: Enchant Chest - Exceptional Stats - Item - TBC Classic</title></head><body></body></html>",
        )
        source = {
            "id": "synthetic-enchants",
            "url": guide_url,
            "data_family": "enchants",
            "class": "Druid",
            "spec": "Balance",
            "phase": "PR",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            row = scraper.import_enchants_from_snapshots(
                [guide_snapshot, anniversary_spell, sourced_spell, formula_item],
                fallback_to_canonical=False,
            )["enchants"][0]
        finally:
            scraper.manifest_sources_by_url = original

        self.assertEqual(row["id"], 46502)
        self.assertEqual(row["source_spell_id"], 27960)
        self.assertEqual(row["formula_item_ids"], [22547])
        self.assertEqual(row["taught_by"][0]["item_id"], 22547)
        self.assertEqual(len(row["taught_by"]), 1)
        self.assertIn("recipe_known", {requirement["type"] for requirement in row["requirements"]})

    def test_enchant_import_maps_generic_weapon_and_shield_slots(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-enchants"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Enchants</h3>
            <table>
              <tr><td>Weapon</td><td><a href="/tbc/spell=27984/enchant-weapon-mongoose">Enchant Weapon - Mongoose</a></td></tr>
              <tr><td>Weapon</td><td><a href="/tbc/spell=27977/enchant-2h-weapon-major-agility">Enchant 2H Weapon - Major Agility</a></td></tr>
              <tr><td>Shield</td><td><a href="/tbc/spell=27945/enchant-shield-intellect">Enchant Shield - Intellect</a></td></tr>
            </table>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-enchants",
            "url": guide_url,
            "data_family": "enchants",
            "class": "Shaman",
            "spec": "Enhancement",
            "phase": "PR",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            rows = scraper.import_enchants_from_snapshots([guide_snapshot], fallback_to_canonical=False)["enchants"]
        finally:
            scraper.manifest_sources_by_url = original

        slots_by_id = {row["id"]: row["slot"] for row in rows}
        self.assertEqual(slots_by_id[27984], "Main Hand")
        self.assertEqual(slots_by_id[27977], "Two Hand")
        self.assertEqual(slots_by_id[27945], "Off Hand")

    def test_enchant_import_summarizes_spell_formula_sources(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-enchants"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Enchants</h3>
            <table><tr><td>Chest</td><td><a href="/tbc/spell=27960/enchant-chest-exceptional-stats">Enchant Chest - Exceptional Stats</a></td></tr></table>
            </body></html>
            """,
        )
        spell_snapshot = parse_spell_html(
            "https://www.wowhead.com/tbc/spell=27960/enchant-chest-exceptional-stats",
            """
            <html><head><title>Enchant Chest - Exceptional Stats - Spell - TBC Classic</title></head><body>
            <script>
            new Listview({ id: 'taught-by-item', data: [{"id":22547,"name":"Formula: Enchant Chest - Exceptional Stats"}], });
            </script>
            </body></html>
            """,
        )
        formula_item = parse_item_html(
            "https://www.wowhead.com/tbc/item=22547/formula-enchant-chest-exceptional-stats",
            """
            <html><head>
            <title>Formula: Enchant Chest - Exceptional Stats - Item - TBC Classic</title>
            <meta name="description" content="This enchanting formula is sold by a vendor.">
            </head><body>
            <script>
            new Listview({ id: 'sold-by', data: [{"id":17657,"name":"Logistics Officer Ulrike","location":[3483]}], });
            </script>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-enchants",
            "url": guide_url,
            "data_family": "enchants",
            "class": "Druid",
            "spec": "Feral dps",
            "phase": "PR",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            row = scraper.import_enchants_from_snapshots(
                [guide_snapshot, spell_snapshot, formula_item],
                fallback_to_canonical=False,
            )["enchants"][0]
        finally:
            scraper.manifest_sources_by_url = original

        self.assertEqual(row["source_summary"], "Vendor: Logistics Officer Ulrike (Hellfire Peninsula)")

    def test_feral_druid_dps_imports_all_wowhead_enchants(self):
        snapshot_path = next((scraper.RAW_WOWHEAD_DIR / "full_enchants").glob("*druid-feral-dps-enchants-gems*.json"))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        rows = scraper.import_enchants_from_snapshots([snapshot], fallback_to_canonical=False)["enchants"]
        pr_rows = [row for row in rows if row["phase"] == "PR"]

        self.assertEqual(
            [(row["slot"], row["type"], row["id"], row["name"]) for row in pr_rows],
            [
                ("Head", "item", 29192, "Glyph of Ferocity"),
                ("Shoulder", "item", 28888, "Greater Inscription of Vengeance"),
                ("Back", "spell", 34004, "Enchant Cloak - Greater Agility"),
                ("Chest", "spell", 46502, "Enchant Chest - Exceptional Stats"),
                ("Wrist", "spell", 34002, "Enchant Bracer - Assault"),
                ("Hands", "spell", 25080, "Enchant Gloves - Superior Agility"),
                ("Legs", "item", 29535, "Nethercobra Leg Armor"),
                ("Feet", "spell", 34007, "Enchant Boots - Cat's Swiftness"),
                ("Two Hand", "spell", 27977, "Enchant 2H Weapon - Major Agility"),
                ("Ring", "spell", 27927, "Enchant Ring - Stats"),
            ],
        )

    def test_enchant_audit_accepts_sourced_spell_alias_by_name(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-enchants"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Enchants</h3>
            <table><tr><td>Chest</td><td><a href="/tbc/spell=46502/enchant-chest-exceptional-stats">Enchant Chest - Exceptional Stats</a></td></tr></table>
            </body></html>
            """,
        )
        anniversary_spell = parse_spell_html(
            "https://www.wowhead.com/tbc/spell=46502/enchant-chest-exceptional-stats",
            "<html><head><title>Enchant Chest - Exceptional Stats - Spell - TBC Classic</title></head><body></body></html>",
        )
        sourced_spell = parse_spell_html(
            "https://www.wowhead.com/tbc/spell=27960/enchant-chest-exceptional-stats",
            """
            <html><head><title>Enchant Chest - Exceptional Stats - Spell - TBC Classic</title></head><body>
            <script>
            new Listview({ id: 'taught-by-item', data: [{"id":22547,"name":"Formula: Enchant Chest - Exceptional Stats"}], });
            </script>
            </body></html>
            """,
        )
        formula_item = parse_item_html(
            "https://www.wowhead.com/tbc/item=22547/formula-enchant-chest-exceptional-stats",
            """
            <html><head>
            <title>Formula: Enchant Chest - Exceptional Stats - Item - TBC Classic</title>
            <meta name="description" content="This enchanting formula is sold by a vendor.">
            </head><body>
            <script>
            new Listview({ id: 'sold-by', data: [{"id":17657,"name":"Logistics Officer Ulrike","location":[3483]}], });
            </script>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-enchants",
            "url": guide_url,
            "data_family": "enchants",
            "class": "Druid",
            "spec": "Balance",
            "phase": "PR",
        }
        original_manifest_urls = scraper.manifest_urls_for_family
        original_sources_by_url = scraper.manifest_sources_by_url
        scraper.manifest_urls_for_family = lambda family: {guide_url} if family == "enchants" else set()
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = scraper.Path(tmp)
                for snapshot in [guide_snapshot, anniversary_spell, sourced_spell, formula_item]:
                    scraper.write_snapshot(snapshot, tmp_path)
                audit = scraper.build_snapshot_audit(tmp_path, "enchants")
        finally:
            scraper.manifest_urls_for_family = original_manifest_urls
            scraper.manifest_sources_by_url = original_sources_by_url

        self.assertTrue(audit["ok"], audit["errors"])

    def test_import_scaffolding_handles_all_non_gear_families_offline(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-druid-balance"
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best Gems</h3>
        <table><tr><td>PR</td><td><a href="/tbc/item=34220/chaotic-skyfire-diamond">Chaotic Skyfire Diamond</a></td><td>Meta</td></tr></table>
        <h3>Best Enchants</h3>
        <table><tr><td>Head</td><td><a href="/tbc/spell=46540/enchant-weapon-sunfire">Enchant Weapon - Sunfire</a></td><td>PR</td></tr></table>
        <table><tr><td>Bracer</td><td><a href="/tbc/spell=46500/enchant-bracer-superior-healing">Enchant Bracer - Superior Healing</a></td><td>PR</td></tr></table>
        <table><tr><td>Gloves</td><td><a href="/tbc/spell=33999/major-healing">Major Healing</a></td><td>PR</td></tr></table>
        <h3>Consumables</h3>
        <table><tr><td>Flasks</td><td><a href="/tbc/item=22861/flask-of-blinding-light">Flask of Blinding Light</a> <a href="/tbc/item=22866/flask-of-pure-death">Flask of Pure Death</a></td></tr></table>
        <h3>Leveling Talents</h3>
        <table><tr><td>10-20</td><td><a href="/tbc/spell=16814/hurricane">Hurricane</a></td></tr></table>
        </body></html>
        """
        snapshot = parse_guide_html(url, html)
        source = {
            "id": "synthetic",
            "url": url,
            "data_families": ["gems", "enchants", "consumables", "leveling"],
            "class": "Druid",
            "spec": "Balance",
            "phases": ["PR"],
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {url: [source]}
        try:
            gems = scraper.import_gems_from_snapshots([snapshot])["gems"]
            enchants = scraper.import_enchants_from_snapshots([snapshot])["enchants"]
            consumables = scraper.import_consumables_from_snapshots([snapshot])["consumables"]
            leveling = scraper.import_leveling_from_snapshots([snapshot])["leveling"]
        finally:
            scraper.manifest_sources_by_url = original

        self.assertEqual(gems[0]["id"], 34220)
        self.assertTrue(gems[0]["meta"])
        self.assertEqual(gems[0]["socket_category"], "meta")
        self.assertEqual(gems[0]["context"], "standard")
        self.assertEqual(enchants[0]["id"], 46540)
        self.assertEqual(enchants[0]["type"], "spell")
        self.assertEqual(enchants[0]["context"], "standard")
        enchant_by_id = {row["id"]: row for row in enchants}
        self.assertEqual(enchant_by_id[46500]["slot"], "Wrist")
        self.assertEqual(enchant_by_id[33999]["slot"], "Hands")
        self.assertEqual(consumables[0]["category"], "flask")
        self.assertEqual(consumables[0]["items"], [22861, 22866])
        self.assertEqual(leveling[0]["entities"][0]["id"], 16814)

    def test_family_dry_run_reports_counts_for_files_that_would_change(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-leveling"
        guide_snapshot = parse_guide_html(
            url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Leveling Talents</h3>
            <table><tr><td>10-20</td><td><a href="/tbc/spell=123/test-spell">Test Spell</a></td></tr></table>
            </body></html>
            """,
        )
        spell_snapshot = parse_spell_html(
            "https://www.wowhead.com/tbc/spell=123/test-spell",
            "<html><head><title>Test Spell - Spell - TBC Classic</title></head><body></body></html>",
        )
        canonical_docs = {
            "bis_lists": {"coverage": "scraped_snapshot", "lists": []},
            "consumables": {"consumables": []},
            "enchants": {"enchants": [{"id": 123, "type": "spell"}]},
            "enchant_sources": {"enchant_sources": [{"id": index} for index in range(40)]},
            "gem_sources": {"gem_sources": []},
            "gems": {"gems": []},
            "items": {"items": []},
            "leveling": {"leveling": []},
            "leveling_gear": {"leveling_gear": []},
            "overrides": {"overrides": []},
            "scrape_manifest": {
                "sources": [
                    {
                        "id": "synthetic-leveling",
                        "url": url,
                        "data_family": "leveling",
                        "class": "Druid",
                        "spec": "Balance",
                        "phase": "PR",
                    }
                ]
            },
        }
        original_canonical_json = scraper.canonical_json
        scraper.canonical_json = lambda name: scraper.deepcopy(canonical_docs[name])
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = scraper.Path(tmp)
                for snapshot in [guide_snapshot, spell_snapshot]:
                    scraper.write_snapshot(snapshot, tmp_path)
                output = io.StringIO()
                args = SimpleNamespace(input_dir=tmp_path, family="leveling", dry_run=True)
                with contextlib.redirect_stdout(output):
                    exit_code = scraper.command_import(args)
        finally:
            scraper.canonical_json = original_canonical_json

        self.assertEqual(exit_code, 0)
        counts = json.loads(output.getvalue())
        self.assertEqual(counts["family"], "leveling")
        self.assertEqual(counts["leveling"], 1)
        self.assertEqual(counts["enchant_sources"], 40)

    def test_leveling_import_uses_narrative_sections_without_tables(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-leveling"
        snapshot = parse_guide_html(
            url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Leveling Talents Levels 20-30</h3>
            <p>Pick up <a href="/tbc/spell=16814/hurricane">Hurricane</a> for larger pulls.</p>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-leveling",
            "url": url,
            "data_family": "leveling",
            "class": "Druid",
            "spec": "Balance",
            "phase": "PR",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {url: [source]}
        try:
            rows = scraper.import_leveling_from_snapshots([snapshot], fallback_to_canonical=False)["leveling"]
        finally:
            scraper.manifest_sources_by_url = original

        self.assertEqual(rows[0]["section"], "Leveling Talents Levels 20-30")
        self.assertEqual(rows[0]["level_range"], "20-30")
        self.assertEqual(rows[0]["entities"][0]["type"], "spell")

    def test_leveling_import_formats_training_tables_without_pipe_artifacts(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-leveling"
        snapshot = parse_guide_html(
            url,
            """
            <html><head><title>Guide</title></head><body>
            <script>WH.Gatherer.addData(6, 5, {"26984":{"name_enus":"Wrath"}});</script>
            <h3>Mandatory Abilities to Train for Balance Druid</h3>
            <table><tr><td>61</td><td><a href="/tbc/spell=26984"></a></td><td>9</td></tr></table>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-leveling",
            "url": url,
            "data_family": "leveling",
            "class": "Druid",
            "spec": "Balance",
            "phase": "*",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {url: [source]}
        try:
            rows = scraper.import_leveling_from_snapshots([snapshot], fallback_to_canonical=False)["leveling"]
        finally:
            scraper.manifest_sources_by_url = original

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "Level 61: Train Wrath (Rank 9)")
        self.assertNotIn("phase", rows[0])
        self.assertEqual(rows[0]["entities"][0]["name"], "Wrath")

    def test_leveling_gear_imports_multi_item_rows_and_level_ranges(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-leveling-gear"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Leveling Weapons and Gear for Arcane Mage DPS in TBC Classic</h3>
            <table>
              <tr><td>18</td><td><a href="/tbc/item=6505/crescent-staff">Crescent Staff</a> / <a href="/tbc/item=2042/staff-of-westfall">Staff of Westfall</a></td><td>Dungeon / Quest</td></tr>
              <tr><td>59-60</td><td><a href="/tbc/item=31075/evokers-mark-of-the-redemption">Evoker's Mark of the Redemption</a></td><td>Quest in Shadowmoon Valley</td></tr>
            </table>
            </body></html>
            """,
        )
        crescent_staff = parse_item_html(
            "https://www.wowhead.com/tbc/item=6505/crescent-staff",
            '<html><head><title>Crescent Staff - Item - TBC Classic</title><meta name="description" content="This uncommon staff goes in the &quot;Two-Hand&quot; slot."></head><body></body></html>',
        )
        westfall_staff = parse_item_html(
            "https://www.wowhead.com/tbc/item=2042/staff-of-westfall",
            '<html><head><title>Staff of Westfall - Item - TBC Classic</title><meta name="description" content="This rare staff goes in the &quot;Two-Hand&quot; slot."></head><body></body></html>',
        )
        ring = parse_item_html(
            "https://www.wowhead.com/tbc/item=31075/evokers-mark-of-the-redemption",
            '<html><head><title>Evoker Ring - Item - TBC Classic</title><meta name="description" content="This rare ring goes in the &quot;Finger&quot; slot."></head><body></body></html>',
        )
        source = {"id": "synthetic-leveling-gear", "url": guide_url, "data_family": "leveling", "class": "Mage", "spec": "Arcane", "phases": "*"}
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            rows = scraper.import_leveling_gear_from_snapshots(
                [guide_snapshot, crescent_staff, westfall_staff, ring],
                fallback_to_canonical=False,
            )["leveling_gear"]
        finally:
            scraper.manifest_sources_by_url = original

        by_item = {row["item_id"]: row for row in rows}
        self.assertEqual(set(by_item), {6505, 2042, 31075})
        self.assertEqual(by_item[6505]["level_min"], 18)
        self.assertEqual(by_item[6505]["level_max"], 70)
        self.assertEqual(by_item[6505]["slot"], "Two Hand")
        self.assertEqual(by_item[2042]["source_note"], "Dungeon / Quest")
        self.assertEqual(by_item[31075]["level_min"], 59)
        self.assertEqual(by_item[31075]["level_max"], 60)
        self.assertEqual(by_item[31075]["slot"], "Ring")

    def test_consumables_import_uses_section_lists_without_tables(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-consumables"
        snapshot = parse_guide_html(
            url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Flask for Balance Druid DPS</h3>
            <ul><li><a href="/tbc/item=22861/flask-of-blinding-light">Flask of Blinding Light</a></li></ul>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-consumables",
            "url": url,
            "data_family": "consumables",
            "class": "Druid",
            "spec": "Balance",
            "phase": "PR",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {url: [source]}
        try:
            rows = scraper.import_consumables_from_snapshots([snapshot], fallback_to_canonical=False)["consumables"]
        finally:
            scraper.manifest_sources_by_url = original

        self.assertEqual(rows[0]["category"], "flask")
        self.assertEqual(rows[0]["items"], [22861])

    def test_consumables_import_preserves_checklist_relationships_and_item_categories(self):
        url = "https://www.wowhead.com/tbc/guide/classes/druid/feral/dps-consumables-raid-buffs-pve"
        guide_snapshot = parse_guide_html(
            url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Consumable Check List for Feral Druid DPS in TBC Classic</h3>
            <ul>
              <li><a href="/tbc/item=22831/elixir-of-major-agility">Elixir of Major Agility</a></li>
              <li><a href="/tbc/item=32067/elixir-of-draenic-wisdom">Elixir of Draenic Wisdom</a></li>
              <li><a href="/tbc/item=27659/warp-burger">Warp Burger</a> or <a href="/tbc/item=27664/grilled-mudfish">Grilled Mudfish</a></li>
              <li><a href="/tbc/item=20520/dark-rune">Dark Rune</a> / <a href="/tbc/item=12662/demonic-rune">Demonic Rune</a></li>
              <li><a href="/tbc/item=23827/super-sapper-charge">Super Sapper Charge</a> and <a href="/tbc/item=10646/goblin-sapper-charge">Goblin Sapper Charge</a></li>
            </ul>
            </body></html>
            """,
        )
        item_snapshots = [
            parse_item_html(
                "https://www.wowhead.com/tbc/item=22831/elixir-of-major-agility",
                """<html><head><title>Elixir of Major Agility - Item - TBC Classic</title>
                <meta name="description" content="Elixir of Major Agility is a level 66 battle elixir. In the Elixirs category."></head><body></body></html>""",
            ),
            parse_item_html(
                "https://www.wowhead.com/tbc/item=32067/elixir-of-draenic-wisdom",
                """<html><head><title>Elixir of Draenic Wisdom - Item - TBC Classic</title>
                <meta name="description" content="Elixir of Draenic Wisdom is a guardian elixir. In the Elixirs category."></head><body></body></html>""",
            ),
            parse_item_html(
                "https://www.wowhead.com/tbc/item=27659/warp-burger",
                """<html><head><title>Warp Burger - Item - TBC Classic</title>
                <meta name="description" content="It is crafted. In the Food &amp; Drinks category."></head><body></body></html>""",
            ),
            parse_item_html(
                "https://www.wowhead.com/tbc/item=27664/grilled-mudfish",
                """<html><head><title>Grilled Mudfish - Item - TBC Classic</title>
                <meta name="description" content="It is crafted. In the Food &amp; Drinks category."></head><body></body></html>""",
            ),
            parse_item_html(
                "https://www.wowhead.com/tbc/item=20520/dark-rune",
                """<html><head><title>Dark Rune - Item - TBC Classic</title>
                <meta name="description" content="Restores mana at the cost of life."></head><body></body></html>""",
            ),
            parse_item_html(
                "https://www.wowhead.com/tbc/item=12662/demonic-rune",
                """<html><head><title>Demonic Rune - Item - TBC Classic</title>
                <meta name="description" content="Restores mana at the cost of life."></head><body></body></html>""",
            ),
            parse_item_html(
                "https://www.wowhead.com/tbc/item=23827/super-sapper-charge",
                """<html><head><title>Super Sapper Charge - Item - TBC Classic</title>
                <meta name="description" content="Explodes to deal fire damage."></head><body></body></html>""",
            ),
            parse_item_html(
                "https://www.wowhead.com/tbc/item=10646/goblin-sapper-charge",
                """<html><head><title>Goblin Sapper Charge - Item - TBC Classic</title>
                <meta name="description" content="Explodes to deal fire damage."></head><body></body></html>""",
            ),
        ]
        source = {
            "id": "synthetic-feral-consumables",
            "url": url,
            "data_family": "consumables",
            "class": "Druid",
            "spec": "Feral dps",
            "phase": "T4",
        }
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {url: [source]}
        try:
            rows = scraper.import_consumables_from_snapshots([guide_snapshot, *item_snapshots], fallback_to_canonical=False)["consumables"]
        finally:
            scraper.manifest_sources_by_url = original

        by_items = {tuple(row["items"]): row for row in rows}
        self.assertEqual(by_items[(22831,)]["category"], "battle_elixir")
        self.assertEqual(by_items[(22831,)]["relationship"], "single")
        self.assertEqual(by_items[(32067,)]["category"], "guardian_elixir")
        self.assertEqual(by_items[(27659, 27664)]["category"], "food")
        self.assertEqual(by_items[(27659, 27664)]["relationship"], "or")
        self.assertEqual(by_items[(27659, 27664)]["text"], "Warp Burger or Grilled Mudfish")
        self.assertEqual(by_items[(20520, 12662)]["relationship"], "or")
        self.assertEqual(by_items[(23827, 10646)]["relationship"], "and")

    def test_non_gear_import_fans_out_shared_manifest_url_by_spec(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-shared-gems"
        snapshot = parse_guide_html(
            url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Red Gems</h3>
            <table><tr><td>Red Gem</td><td><a href="/tbc/item=24030/runed-living-ruby">Runed Living Ruby</a></td><td>Red</td></tr></table>
            </body></html>
            """,
        )
        sources = [
            {"id": "mage-arcane", "url": url, "data_family": "gems", "class": "Mage", "spec": "Arcane", "phase": "PR"},
            {"id": "mage-fire", "url": url, "data_family": "gems", "class": "Mage", "spec": "Fire", "phase": "PR"},
        ]
        original = scraper.manifest_sources_by_url
        scraper.manifest_sources_by_url = lambda: {url: sources}
        try:
            rows = scraper.import_gems_from_snapshots([snapshot], fallback_to_canonical=False)["gems"]
        finally:
            scraper.manifest_sources_by_url = original

        self.assertEqual({row["spec"] for row in rows}, {"Arcane", "Fire"})

    def test_snapshot_audit_non_gear_requires_linked_item_snapshots(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-gems"
        snapshot = parse_guide_html(
            url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best Meta Gems</h3>
            <table><tr><td>BiS</td><td><a href="/tbc/item=34220/chaotic-skyfire-diamond">Chaotic Skyfire Diamond</a></td><td>Meta</td></tr></table>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-gems",
            "url": url,
            "data_family": "gems",
            "class": "Druid",
            "spec": "Balance",
            "phase": "PR",
        }
        original_manifest_urls = scraper.manifest_urls_for_family
        original_sources_by_url = scraper.manifest_sources_by_url
        scraper.manifest_urls_for_family = lambda family: {url} if family == "gems" else set()
        scraper.manifest_sources_by_url = lambda: {url: [source]}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                scraper.write_snapshot(snapshot, scraper.Path(tmp))
                audit = scraper.build_snapshot_audit(scraper.Path(tmp), "gems")
        finally:
            scraper.manifest_urls_for_family = original_manifest_urls
            scraper.manifest_sources_by_url = original_sources_by_url

        self.assertFalse(audit["ok"])
        self.assertIn("Missing item snapshot for linked gems item 34220", "\n".join(audit["errors"]))

    def test_token_item_cost_urls_are_discovered_from_item_snapshots(self):
        html = """
        <html><head><title>Thunderheart Helmet - Item - TBC Classic</title></head><body>
        <script>
        new Listview({ id: 'sold-by', data: [{"id":23437,"name":"Tydormu","location":[3606],"cost":[[0,[],[[31095,1]]]]}], });
        </script>
        </body></html>
        """
        snapshot = parse_item_html("https://www.wowhead.com/tbc/item=31037/thunderheart-helmet", html)
        self.assertEqual(scraper.discover_token_item_urls([snapshot]), ["https://www.wowhead.com/tbc/item=31095"])

    def test_import_items_converts_vendor_item_cost_to_token_turnin(self):
        tier_url = "https://www.wowhead.com/tbc/item=31037/thunderheart-helmet"
        token_url = "https://www.wowhead.com/tbc/item=31095/helm-of-the-forgotten-protector"
        tier_html = """
        <html><head>
        <title>Thunderheart Helmet - Item - TBC Classic</title>
        <meta name="description" content="This epic leather armor goes in the Head slot.">
        </head><body>
        <script>
        new Listview({ id: 'sold-by', data: [{"id":23437,"name":"Tydormu","location":[3606],"cost":[[0,[],[[31095,1]]]]}], });
        </script>
        </body></html>
        """
        token_html = """
        <html><head>
        <title>Helm of the Forgotten Protector - Item - TBC Classic</title>
        <meta name="description" content="This epic armor token can be exchanged for tier pieces.">
        </head><body>
        <script>
        new Listview({ id: 'dropped-by', data: [{"id":17968,"name":"Archimonde","location":[3606],"count":556,"outof":1000}], });
        </script>
        </body></html>
        """
        tier_snapshot = parse_item_html(tier_url, tier_html)
        token_snapshot = parse_item_html(token_url, token_html)
        guide_snapshot = parse_guide_html(
            "https://www.wowhead.com/tbc/guide/synthetic-tier",
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Head Armor</h3>
            <table><tr><td>BiS</td><td><a href="/tbc/item=31037/thunderheart-helmet">Thunderheart Helmet</a></td><td>Vendor: Tydormu</td></tr></table>
            </body></html>
            """,
        )
        original = scraper.canonical_json

        def fake_canonical_json(name):
            if name == "items":
                return {
                    "items": [
                        {
                            "id": 31037,
                            "name": "Thunderheart Helmet",
                            "quality": "epic",
                            "wowhead_url": tier_url,
                            "sources": [],
                        }
                    ]
                }
            return original(name)

        scraper.canonical_json = fake_canonical_json
        try:
            item = scraper.import_items_from_snapshots([guide_snapshot, tier_snapshot, token_snapshot])["items"][0]
        finally:
            scraper.canonical_json = original

        source = item["primary_source"]
        self.assertEqual(source["type"], "token_turnin")
        self.assertEqual(source["entity_name"], "Tydormu")
        self.assertEqual(source["costs"][0]["name"], "Helm of the Forgotten Protector")
        self.assertEqual(source["token_sources"][0]["token_item_id"], 31095)
        self.assertEqual(source["token_sources"][0]["entity_name"], "Archimonde")
        self.assertEqual(item["source_summary"], "Token: Helm of the Forgotten Protector - Archimonde (Hyjal Summit) 55.6%")

    def test_import_items_attaches_reviewed_quest_starter_sources(self):
        reward_url = "https://www.wowhead.com/tbc/item=28791/ring-of-the-recalcitrant"
        starter_url = "https://www.wowhead.com/tbc/item=32385/magtheridons-head"
        reward_html = """
        <html><head>
        <title>Ring of the Recalcitrant - Item - TBC Classic</title>
        <meta name="description" content="This epic ring goes in the Finger slot. It is a quest reward.">
        </head><body>
        <script>
        new Listview({ id: 'reward-from-q', data: [{"id":11002,"name":"The Fall of Magtheridon","category":3483,"side":1}], });
        </script>
        </body></html>
        """
        starter_html = """
        <html><head>
        <title>Magtheridon's Head - Item - TBC Classic</title>
        <meta name="description" content="Magtheridon's Head is a quest item needed for The Fall of Magtheridon.">
        </head><body>
        <script>
        new Listview({ id: 'dropped-by', data: [{"id":17257,"name":"Magtheridon","location":[3836],"count":461,"outof":1000}], });
        </script>
        </body></html>
        """
        guide_snapshot = parse_guide_html(
            "https://www.wowhead.com/tbc/guide/synthetic-mag",
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Rings</h3>
            <table><tr><td>BiS</td><td><a href="/tbc/item=28791/ring-of-the-recalcitrant">Ring of the Recalcitrant</a></td><td>Quest</td></tr></table>
            </body></html>
            """,
        )
        reward_snapshot = parse_item_html(reward_url, reward_html)
        starter_snapshot = parse_item_html(starter_url, starter_html)
        original = scraper.canonical_json

        def fake_canonical_json(name):
            if name == "items":
                return {"items": []}
            if name == "overrides":
                return {
                    "overrides": [
                        {
                            "id": "quest-starter-mag",
                            "type": "quest_starter",
                            "target": {"quest_id": 11002},
                            "reason": "fixture",
                            "reviewer": "tester",
                            "reviewed_at": "2026-05-29",
                            "source_url": starter_url,
                            "data": {
                                "quest_ids": [11002],
                                "relationship": "direct_starter",
                                "reward_item_ids": [28791],
                                "starter_item_ids": [32385],
                            },
                        }
                    ]
                }
            return original(name)

        scraper.canonical_json = fake_canonical_json
        try:
            item = scraper.import_items_from_snapshots([guide_snapshot, reward_snapshot, starter_snapshot])["items"][0]
        finally:
            scraper.canonical_json = original

        source = item["primary_source"]
        starter_source = source["quest_starter_sources"][0]
        self.assertEqual(item["acquisition_phase"], "T4")
        self.assertEqual(source["content_type"], "raid")
        self.assertEqual(starter_source["quest_starter_item_id"], 32385)
        self.assertEqual(starter_source["entity_name"], "Magtheridon")
        self.assertEqual(item["source_summary"], "Quest: The Fall of Magtheridon via Magtheridon's Head - Magtheridon (Magtheridon's Lair) 46.1%")

    def test_import_items_can_seed_missing_reviewed_quest_starter_item(self):
        reward_url = "https://www.wowhead.com/tbc/item=21709/ring-of-the-fallen-god"
        starter_url = "https://www.wowhead.com/tbc/item=21221/eye-of-cthun"
        original = scraper.canonical_json

        def fake_canonical_json(name):
            if name == "items":
                return {
                    "items": [
                        {
                            "id": 21709,
                            "name": "Ring of the Fallen God",
                            "quality": "epic",
                            "binding": "bind_on_pickup",
                            "boe": False,
                            "wowhead_url": reward_url,
                            "sources": [
                                {
                                    "type": "quest",
                                    "entity_name": "The Savior of Kalimdor",
                                    "quest_id": 8802,
                                    "source_url": reward_url,
                                    "confidence": "fixture",
                                }
                            ],
                        }
                    ]
                }
            if name == "overrides":
                return {
                    "overrides": [
                        {
                            "id": "quest-starter-eye",
                            "type": "quest_starter",
                            "target": {"quest_id": 8802},
                            "reason": "fixture",
                            "reviewer": "tester",
                            "reviewed_at": "2026-05-29",
                            "source_url": starter_url,
                            "data": {
                                "quest_ids": [8802],
                                "relationship": "direct_starter",
                                "reward_item_ids": [21709],
                                "starter_item_ids": [21221],
                                "starter_items": [
                                    {
                                        "id": 21221,
                                        "name": "Eye of C'Thun",
                                        "quality": "epic",
                                        "binding": "bind_on_pickup",
                                        "boe": False,
                                        "wowhead_url": starter_url,
                                        "sources": [
                                            {
                                                "type": "drop",
                                                "entity_name": "C'Thun",
                                                "zone": "Ahn'Qiraj",
                                                "source_url": starter_url,
                                                "confidence": "fixture",
                                            }
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                }
            return original(name)

        scraper.canonical_json = fake_canonical_json
        try:
            imported = {item["id"]: item for item in scraper.import_items_from_snapshots([])["items"]}
        finally:
            scraper.canonical_json = original

        self.assertIn(21221, imported)
        self.assertEqual(imported[21221]["source_summary"], "Drop: C'Thun (Ahn'Qiraj)")
        self.assertEqual(imported[21709]["sources"][0]["quest_starter_sources"][0]["quest_starter_item_id"], 21221)

    def test_import_items_requires_quest_starter_drop_evidence(self):
        reward_url = "https://www.wowhead.com/tbc/item=21709/ring-of-the-fallen-god"
        starter_url = "https://www.wowhead.com/tbc/item=21221/eye-of-cthun"
        original = scraper.canonical_json

        def fake_canonical_json(name):
            if name == "items":
                return {
                    "items": [
                        {
                            "id": 21709,
                            "name": "Ring of the Fallen God",
                            "quality": "epic",
                            "binding": "bind_on_pickup",
                            "boe": False,
                            "wowhead_url": reward_url,
                            "sources": [
                                {
                                    "type": "quest",
                                    "entity_name": "The Savior of Kalimdor",
                                    "quest_id": 8802,
                                    "source_url": reward_url,
                                    "confidence": "fixture",
                                }
                            ],
                        }
                    ]
                }
            if name == "overrides":
                return {
                    "overrides": [
                        {
                            "id": "quest-starter-eye",
                            "type": "quest_starter",
                            "target": {"quest_id": 8802},
                            "reason": "fixture",
                            "reviewer": "tester",
                            "reviewed_at": "2026-05-29",
                            "source_url": starter_url,
                            "data": {
                                "quest_ids": [8802],
                                "relationship": "direct_starter",
                                "reward_item_ids": [21709],
                                "starter_item_ids": [21221],
                                "starter_items": [
                                    {
                                        "id": 21221,
                                        "name": "Eye of C'Thun",
                                        "quality": "epic",
                                        "binding": "bind_on_pickup",
                                        "boe": False,
                                        "wowhead_url": starter_url,
                                        "sources": [
                                            {
                                                "type": "vendor",
                                                "entity_name": "Not a Drop",
                                                "source_url": starter_url,
                                                "confidence": "fixture",
                                            }
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                }
            return original(name)

        scraper.canonical_json = fake_canonical_json
        try:
            imported = {item["id"]: item for item in scraper.import_items_from_snapshots([])["items"]}
        finally:
            scraper.canonical_json = original

        self.assertNotIn("quest_starter_sources", imported[21709]["sources"][0])

    def test_import_items_applies_reviewed_source_gap_override_last(self):
        url = "https://www.wowhead.com/tbc/item=99999/source-gap"
        item_html = """
        <html><head>
        <title>Source Gap - Item - TBC Classic</title>
        <meta name="description" content="This epic item has no related tables.">
        </head><body></body></html>
        """
        snapshot = parse_item_html(url, item_html)
        original = scraper.canonical_json

        def fake_canonical_json(name):
            if name == "items":
                return {
                    "items": [
                        {
                            "id": 99999,
                            "name": "Source Gap",
                            "quality": "epic",
                            "binding": "unknown",
                            "boe": None,
                            "wowhead_url": url,
                            "sources": [{"type": "drop", "entity_name": "Reviewed Boss", "confidence": "reviewed", "source_url": url}],
                        }
                    ]
                }
            if name == "overrides":
                return {
                    "overrides": [
                        {
                            "id": "source-gap",
                            "type": "source_gap",
                            "target": {"item_id": 99999},
                            "reason": "fixture",
                            "reviewer": "tester",
                            "reviewed_at": "2026-05-23",
                            "source_url": url,
                        }
                    ]
                }
            return original(name)

        scraper.canonical_json = fake_canonical_json
        try:
            item = scraper.import_items_from_snapshots([snapshot])["items"][0]
        finally:
            scraper.canonical_json = original

        self.assertEqual(item["sources"][0]["entity_name"], "Reviewed Boss")
        self.assertEqual(item["source_summary"], "Drop: Reviewed Boss")

    def test_import_bis_lists_applies_reviewed_context_override_last(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-context"
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best in Slot Idols</h3>
        <table><tr><td>BiS</td><td><a href="/tbc/item=1/idol">Idol</a></td><td>Drop: Boss</td></tr></table>
        </body></html>
        """
        snapshot = parse_guide_html(url, html)
        source = {"id": "synthetic", "url": url, "data_family": "bis_lists", "class": "Druid", "spec": "Balance", "phase": "SWP"}
        replacement = {
            "class": "Druid",
            "spec": "Balance",
            "phase": "SWP",
            "slot": "Idol",
            "source_url": url,
            "items": [{"item_id": 1, "rank_label": "BiS (raid DPS)", "rank_group": "situational_bis", "context": "raid_dps", "note": "Reviewed"}],
        }
        original = scraper.canonical_json
        original_sources_by_url = scraper.manifest_sources_by_url

        def fake_canonical_json(name):
            if name == "bis_lists":
                return {"coverage": "seed_audit", "lists": [replacement]}
            if name == "overrides":
                return {
                    "overrides": [
                        {
                            "id": "context",
                            "type": "bis_context",
                            "target": {"class": "Druid", "spec": "Balance", "phase": "SWP", "slot": "Idol"},
                            "reason": "fixture",
                            "reviewer": "tester",
                            "reviewed_at": "2026-05-23",
                            "source_url": url,
                        }
                    ]
                }
            return original(name)

        scraper.canonical_json = fake_canonical_json
        scraper.manifest_sources_by_url = lambda: {url: [source]}
        try:
            imported = scraper.apply_bis_overrides(scraper.import_bis_lists_from_snapshots([snapshot]))
        finally:
            scraper.canonical_json = original
            scraper.manifest_sources_by_url = original_sources_by_url

        self.assertEqual(imported["lists"][0]["items"][0]["context"], "raid_dps")
        self.assertEqual(imported["lists"][0]["items"][0]["note"], "Reviewed")

    def test_import_items_uses_guide_source_fallback_when_item_page_has_no_sources(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-crafted"
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best in Slot Waist Armor</h3>
        <table>
          <tr><td>BiS</td><td><a href="/tbc/item=30042/belt-of-natural-power">Belt of Natural Power</a></td><td>Profession: Leatherworking (BoE)</td></tr>
        </table>
        </body></html>
        """
        snapshot = parse_guide_html(url, html)
        original = scraper.canonical_json
        scraper.canonical_json = lambda name: {"items": []} if name == "items" else original(name)
        try:
            item = scraper.import_items_from_snapshots([snapshot])["items"][0]
        finally:
            scraper.canonical_json = original

        self.assertEqual(item["id"], 30042)
        self.assertEqual(item["sources"][0]["type"], "crafted")
        self.assertEqual(item["sources"][0]["profession"], "Leatherworking")
        self.assertEqual(item["source_summary"], "Crafted: Leatherworking")

    def test_boe_crafted_import_keeps_profession_on_craft_path_and_recipe_phase(self):
        guide_url = "https://www.wowhead.com/tbc/guide/synthetic-swp-bis"
        guide_snapshot = parse_guide_html(
            guide_url,
            """
            <html><head><title>Guide</title></head><body>
            <h3>Best in Slot Ring</h3>
            <table><tr>
              <td>Option</td>
              <td><a href="/tbc/item=34361/hard-khorium-band">Hard Khorium Band</a></td>
              <td>Profession: Jewelcrafting (BoP)</td>
            </tr></table>
            </body></html>
            """,
        )
        item_snapshot = parse_item_html(
            "https://www.wowhead.com/tbc/item=34361/hard-khorium-band",
            """
            <html><head>
            <title>Hard Khorium Band - Item - TBC Classic</title>
            <meta name="description" content="This epic ring goes in the Finger slot.">
            </head><body>
            <script>
            g_items[34361].tooltip_enus = "<table><tr><td><b class=\\"q4\\">Hard Khorium Band</b><br>Binds when equipped</td></tr></table>";
            new Listview({ id: 'created-by-spell', data: [{"id":46124,"name":"Hard Khorium Band","skill":"Jewelcrafting"}], });
            new Listview({ id: 'taught-by-item', data: [{"id":35200,"name":"Design: Hard Khorium Band","source":[2],"sourcemore":[{"z":4075}]}], });
            </script>
            </body></html>
            """,
        )
        source = {
            "id": "synthetic-swp-bis",
            "url": guide_url,
            "data_family": "bis_lists",
            "class": "Druid",
            "spec": "Feral dps",
            "phase": "SWP",
        }
        original = scraper.canonical_json
        original_sources_by_url = scraper.manifest_sources_by_url

        def fake_canonical_json(name):
            if name == "items":
                return {"items": []}
            if name == "bis_lists":
                return {"coverage": "fixture", "lists": []}
            return original(name)

        scraper.canonical_json = fake_canonical_json
        scraper.manifest_sources_by_url = lambda: {guide_url: [source]}
        try:
            item = scraper.import_items_from_snapshots([guide_snapshot, item_snapshot])["items"][0]
            bis_item = scraper.import_bis_lists_from_snapshots([guide_snapshot, item_snapshot])["lists"][0]["items"][0]
        finally:
            scraper.canonical_json = original
            scraper.manifest_sources_by_url = original_sources_by_url

        self.assertEqual(item["binding"], "bind_on_equip")
        self.assertEqual(item["acquisition_phase"], "SWP")
        self.assertEqual(item["sources"][0]["recipe_sources"][0]["zone"], "Sunwell Plateau")
        self.assertNotIn(
            ("profession", "equip_or_use", "Jewelcrafting"),
            {(requirement["type"], requirement["scope"], requirement.get("profession")) for requirement in item.get("requirements", [])},
        )
        self.assertIn(
            ("profession", "self_craft", "Jewelcrafting"),
            {(requirement["type"], requirement["scope"], requirement.get("profession")) for requirement in bis_item.get("requirements", [])},
        )
