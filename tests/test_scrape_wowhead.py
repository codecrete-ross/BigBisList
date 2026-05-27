import contextlib
import io
import json
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
        self.assertEqual(scraper.rank_group_from_label("Best Until Tier 5"), "situational")
        self.assertEqual(scraper.rank_group_from_label("PvP"), "pvp")
        self.assertEqual(scraper.normalize_rank_group_value("situational_bis", "BiS (Group Performance)"), "situational")

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

    def test_requirement_parser_extracts_faction_profession_and_specialization(self):
        source_url = "https://www.wowhead.com/tbc/guide/example"
        requirements = scraper.extract_requirements_from_text(
            "Vendor: Eldara Dawnrunner when Exalted with Shattered Sun Offensive and requires The Aldor",
            source_url,
            "vendor_purchase",
            "parsed_source_text",
        )
        self.assertIn("faction_choice", {requirement["type"] for requirement in requirements})

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

        self.assertEqual(row["source_summary"], "Vendor: Logistics Officer Ulrike")

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
