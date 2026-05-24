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

    def test_import_scaffolding_handles_all_non_gear_families_offline(self):
        url = "https://www.wowhead.com/tbc/guide/synthetic-druid-balance"
        html = """
        <html><head><title>Guide</title></head><body>
        <h3>Best Gems</h3>
        <table><tr><td>PR</td><td><a href="/tbc/item=34220/chaotic-skyfire-diamond">Chaotic Skyfire Diamond</a></td><td>Meta</td></tr></table>
        <h3>Best Enchants</h3>
        <table><tr><td>Head</td><td><a href="/tbc/spell=46540/enchant-weapon-sunfire">Enchant Weapon - Sunfire</a></td><td>PR</td></tr></table>
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
        self.assertEqual(enchants[0]["id"], 46540)
        self.assertEqual(enchants[0]["type"], "spell")
        self.assertEqual(consumables[0]["items"], [22861, 22866])
        self.assertEqual(leveling[0]["entities"][0]["id"], 16814)

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
