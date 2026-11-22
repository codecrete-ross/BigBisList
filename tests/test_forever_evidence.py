"""Equipment identity, acquisition intake, and fail-closed evidence reviews."""
from copy import deepcopy
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import forever, forever_sources as sources, scrape_wowhead as scraper


ROOT = forever.WOWHEAD_ROOT


def tooltip(identifier=71, name="Fixture Ring", html="Finger<br>+8 Stamina"):
    row = scraper.parse_item_tooltip_endpoint(ROOT + f"item={identifier}", json.dumps({"name": name, "quality": 3, "tooltip": html}))
    row["flavor"] = "forever"
    return row


def approval(snapshot, *, side="Both"):
    url = snapshot["url"]
    review = {"reviewer": "fixture", "reviewed_at": "2026-11-04", "reason": "Fixture observation",
              "source_url": url, "client_build": "1.60.1.70790", "evidence_refs": [sources.evidence_ref(url, {url: snapshot})]}
    return {**review, "type": "verify_item", "item_id": snapshot["item_id"], "snapshot_url": url,
            "snapshot_digest": forever.snapshot_digest(snapshot),
            "sources": [{**review, "type": "quest", "quest_id": 7, "entity_name": "Fixture Quest", "side": side}]}


class ForeverEquipmentEvidenceTests(unittest.TestCase):
    def test_unique_weapon_limits_come_from_equipment_headers(self):
        for header in ['Unique','Unique-Equipped']:
            row=tooltip(name='Fixture Sword',html=f'Item Level 10<br>{header}<br>One-Hand<br>Sword')
            _,stats=forever.load_verified_items({row['url']:row},[approval(row)])
            self.assertEqual(stats[row['item_id']]['max_equipped'],1)
        row=tooltip(name='Unique Blade',html='Item Level 10<br>One-Hand<br>Sword')
        _,stats=forever.load_verified_items({row['url']:row},[approval(row)])
        self.assertNotIn('max_equipped',stats[row['item_id']])

    def test_live_acceptance_is_separate_from_source_review_and_bound_to_artifact(self):
        with TemporaryDirectory() as temporary:
            directory=Path(temporary)
            document={"status":"accepted","artifact_digest":"tested","reviewer":"fixture","reviewed_at":"2026-11-06",
                "client_build":"1.60.1.70790","source_url":ROOT+"guide/acceptance-fixture","reason":"Fixture live acceptance",
                "checks":{key:True for key in forever.LIVE_ACCEPTANCE_CHECKS},"performance":{"startup_ms":10,"first_open_ms":20}}
            builds_path=directory/"reviewed_builds.json"
            builds_path.write_text(json.dumps({"target_client":"1.60.1.71037"}),encoding="utf-8")
            path=directory/"live_acceptance.json"
            path.write_text(json.dumps(document),encoding="utf-8")
            with patch.object(forever,"FOREVER_CANONICAL_DIR",directory),patch.object(forever,"release_artifact_digest",return_value="tested"):
                self.assertIn("Gameplay acceptance must cover the configured target client build",forever.live_acceptance()["errors"])
                document["client_build"]="1.60.1.71037"
                path.write_text(json.dumps(document),encoding="utf-8")
                self.assertTrue(forever.live_acceptance()["ok"])
                document["checks"]["combat"]=False
                path.write_text(json.dumps(document),encoding="utf-8")
                self.assertFalse(forever.live_acceptance()["ok"])
            with patch.object(forever,"FOREVER_CANONICAL_DIR",directory),patch.object(forever,"release_artifact_digest",return_value="changed"):
                self.assertIn("Live acceptance does not cover the current Forever addon files",forever.live_acceptance()["errors"])

    def test_inline_rating_comments_and_spans_preserve_complete_effect_values(self):
        row=tooltip(html='Ranged<br>Bow<br>Requires Level 14<br><span class="q2">Equip: +<!--rtg38-->4 Attack Power.</span>')
        self.assertEqual(row["item_stats"]["stats"]["attack_power"],4)
        self.assertEqual(row["item_stats"]["equip_effects"],["Equip: +4 Attack Power."])
        row=tooltip(html='Neck<br><span class="q2">Equip: Increases healing done by up to <span><!--rtg41-->20</span> and damage done by up to <span><!--rtg42-->7</span> for all magical spells and effects.</span>')
        self.assertEqual(row["item_stats"]["stats"],{"healing_power":20,"spell_damage":7})
        self.assertEqual(row["item_stats"]["effect_stats"][0]["stats"],{"healing_power":20,"spell_damage":7})
        row=tooltip(html='Hands<br>Leather<br>Equip: Improves your chance to hit by <span><!--rtg31-->0.9</span>%.')
        self.assertEqual(row["item_stats"]["stats"]["hit_percent"],0.9)
        self.assertEqual(row["item_stats"]["effect_stats"][0]["type"],"passive")
        row=tooltip(html='Off Hand<br>Shield<br>200 Armor<br>12 Block')
        self.assertEqual(row["item_stats"]["stats"]["block_value"],12)
        ring = tooltip(html="Finger<br>+1 Armor")
        self.assertEqual(ring["item_stats"]["armor"], 1)
        shield = tooltip(html="Off Hand<br>Shield<br>200 Armor<br>+40 Armor")
        self.assertEqual(shield["item_stats"]["armor"], 240)
        row=tooltip(html='Ranged<br>Wand<table><tr><td>4 - 8 Arcane Damage</td><th>Speed 1.50</th></tr></table>(4.00 damage per second)')
        self.assertEqual(row["item_stats"]["weapon_speed"],1.5)
        self.assertEqual(row["item_stats"]["weapon_min_damage"],4)

    def test_set_bonuses_are_retained_without_counting_them_as_unconditional_stats(self):
        row=tooltip(html='Head<br>Plate<br>+15 Strength<br><span class="q2">Restores +<!--rtg46-->8 health per 5 sec.</span>'
            '<br><span class="q0"><span>(3) Set : <a href="/forever/spell=13198">+15 Strength.</a></span><br>'
            '<span>(5) Set : <a href="/forever/spell=450587">Chance on melee attack to heal.</a></span></span>')
        self.assertEqual(row["item_stats"]["stats"],{"strength":15,"hp5":8})
        self.assertEqual(row["item_stats"]["set_bonuses"][0],{"pieces":3,"text":"+15 Strength.","spell_id":13198})
        row=tooltip(html='Trinket<br>Equip: +<!--rtg38-->40 Attack Power for 10 sec. (1 Min Cooldown)')
        self.assertNotIn("attack_power",row["item_stats"].get("stats",{}))

    def test_target_and_location_bonuses_do_not_inflate_unconditional_stats(self):
        row=tooltip(html='Back<br>+5 Stamina<br>Equip: +4 Attack Power.<br>Equip: +6 Attack Power against Elementals.')
        self.assertEqual(row["item_stats"]["stats"],{"stamina":5,"attack_power":4})
        self.assertEqual(row["item_stats"]["effect_stats"][1]["type"],"target_specific")
        row=tooltip(html='Trinket<br>Equip: Increases damage and healing done by magical spells and effects by up to 8. This effect is tripled in Forest and Grassland areas.')
        self.assertEqual(row["item_stats"]["stats"],{"spell_power":8})
        row=tooltip(html='Trinket<br>Equip: Increases attack power by 45 against Undead.<br>Equip: Restores 8 mana per 5 sec while in combat.')
        self.assertFalse(row["item_stats"].get("stats"))
        row=tooltip(html='Trinket<br>Equip: Restores 5 mana per 5 sec.<br>Restores +8 health per 5 sec.')
        self.assertEqual(row["item_stats"]["stats"],{"mp5":5,"hp5":8})
        row=tooltip(html='Main Hand<br>Mace<br>Equip: Increases healing done by magical spells and effects by up to 68.')
        self.assertEqual(row["item_stats"]["stats"],{"healing_power":68})
        row=tooltip(html='Held In Off-hand<br>+7 Fire Resistance<br><span>(2) Set : +8 All Resistances</span>')
        self.assertEqual(row["item_stats"]["stats"],{"fire_resistance":7})

    def test_flat_dodge_wording_does_not_turn_conditional_dodge_into_a_stat(self):
        row = tooltip(html="Legs<br>Leather<br>Equip: Increases your chance to Dodge an attack by 2.0%.")
        self.assertEqual(row["item_stats"]["stats"], {"dodge_percent": 2.0})
        self.assertEqual(row["item_stats"]["effect_stats"][0]["type"], "passive")
        row = tooltip(html="Legs<br>Leather<br>Equip: Increases your chance to Dodge an attack by 2.0% while in combat.")
        self.assertNotIn("dodge_percent", row["item_stats"].get("stats", {}))
        self.assertEqual(row["item_stats"]["effect_stats"][0]["type"], "conditional")

    def test_observed_trade_rows_preserve_unknowns_and_do_not_set_item_eligibility(self):
        url="https://api.ahledger.com/v1/pricetable/forever.normal.alliance.us"
        row=sources.normalize_ahledger_pricetable(url,"AHL1|forever/normal/alliance/us|1793926741|2\n71:100:90:3:::::\n72:::0:::::\n",collected_at="fixture")
        self.assertEqual(row["observed_faction"],"Alliance")
        self.assertNotIn("side",row)
        self.assertIsNone(row["records"][0]["median_7d_copper"])
        self.assertEqual([edge["object_id"] for edge in row["relationships"]],[71])
        self.assertTrue(row["attribution"])
        self.assertIn(71,sources.route_leads({url:row}))
        for text in ("AHL1|forever/normal/alliance/us|1793926741|2\n71:100:90:3:::::\n",
                     "AHL1|tbc/normal/alliance/us|1793926741|0\n",
                     "AHL1|forever/normal/horde/us|1793926741|0\n",
                     "AHL1|forever/normal/alliance/us|1793926741|2\n71:100:90:3:::::\n71:100:90:3:::::\n"):
            with self.subTest(text=text),self.assertRaises(ValueError):
                sources.normalize_ahledger_pricetable(url,text,collected_at="fixture")
        empty=sources.normalize_ahledger_pricetable(url,"AHL1|forever/normal/alliance/us|1793926741|0\n",collected_at="fixture")
        self.assertFalse(empty["relationships"])

    def test_textual_quest_endpoints_do_not_require_unverified_coordinates(self):
        row = tooltip()
        review = approval(row)
        metadata = {k:v for k,v in review.items() if k in {"reviewer","reviewed_at","reason","source_url","client_build","evidence_refs"}}
        endpoint = {**metadata,"name":"Fixture quest giver","entity_id":71,"kind":"quest_start"}
        source = review["sources"][0]
        source["quest_steps"] = [{**metadata,"quest_id":7,"name":"Fixture quest","kind":"reward","start":endpoint}]
        self.assertTrue(forever.valid_source(source))
        self.assertFalse(forever.valid_destination(endpoint))
        # A partially supplied or invalid location must not silently become text-only.
        endpoint["x"] = 0.5
        self.assertFalse(forever.valid_source(source))

    def test_recipe_keeps_result_separate_from_recipe_identity(self):
        row = tooltip(12834, "Plans: Arcanite Champion", '<b>Plans: Arcanite Champion</b><br>Item Level 63<br>'
            'Requires Blacksmithing (300)<br>Use: <a href="/forever/spell=16990">Teaches you how to make it.</a><br>'
            '<span class="q3"><a href="/forever/item=12790">Arcanite Champion</a></span><br>'
            'Item Level 63<br>Two-Hand<br>Sword<br>+20 Strength<br>Requires Level 58')
        self.assertEqual(row["item_kind"], "recipe")
        self.assertNotIn("slot", row["item_stats"])
        self.assertNotIn("strength", row["item_stats"].get("stats", {}))
        self.assertEqual(row["teaches_spell_ids"], [16990])
        result = row["embedded_items"][0]
        self.assertEqual((result["item_id"], result["inventory_slot"]), (12790, "Two Hand"))
        self.assertEqual(result["item_stats"]["stats"]["strength"], 20)
        self.assertEqual(result["item_stats"]["required_level"], 58)

    def test_quest_starter_name_does_not_establish_a_relic_slot(self):
        row = tooltip(270865, "Titan Relic", '<b>Titan Relic</b><br>Item Level 1<br>'
            '<a href="/forever/quest=95810">This Item Begins a Quest</a>')
        self.assertIsNone(row["inventory_slot"])
        self.assertEqual(row["item_kind"], "quest_starter")
        self.assertEqual(row["linked_entities"][0]["id"], 95810)

    def test_relic_subtypes_enforce_class_eligibility(self):
        for kind, class_name in (("Idol", "Druid"), ("Totem", "Shaman"), ("Libram", "Paladin")):
            with self.subTest(kind=kind):
                row = tooltip(name="Fixture Relic", html=f"Relic<br>{kind}<br>Requires Level 60")
                self.assertEqual(row["inventory_slot"], kind)
                self.assertEqual(row["item_stats"]["restrictions"]["classes"], [class_name])

    def test_reprocessing_preserves_collection_time_and_reviewed_hidden_spells(self):
        row = tooltip()
        hidden_spells = {"spell_ids": [123], "evidence_refs": [{"evidence_id": "fixture", "content_digest": "fixture"}]}
        with TemporaryDirectory() as directory:
            path = Path(directory)
            scraper.write_snapshot({**row, "fetched_at": "2026-11-04T01:00:00Z", "observed_item_spells": hidden_spells}, path)
            cache = path / "html_cache"
            cache.mkdir()
            endpoint = "https://nether.wowhead.com/forever/tooltip/item/71"
            (cache / scraper.html_cache_name(endpoint)).write_text(json.dumps({"name": "Fixture Ring", "tooltip": "Finger"}), encoding="utf-8")
            with patch.object(scraper, "fetch_url", side_effect=AssertionError("cache reprocessing fetched the network")):
                scraper.fetch_forever_snapshot(row["url"], path, retries=0, delay=0, refresh=False, cached_only=True)
            saved = json.loads((path / scraper.snapshot_name(row["url"])).read_text(encoding="utf-8"))
            self.assertEqual(saved["fetched_at"], "2026-11-04T01:00:00Z")
            self.assertEqual(saved["observed_item_spells"], hidden_spells)


class ForeverSourceIntakeTests(unittest.TestCase):
    def test_discovery_deduplicates_entities_and_excludes_other_clients(self):
        page = {"page_type": "guide", "tables": [{"rows": [{"source_links": [
            {"href": ROOT + "npc=1853/gandling"}, {"href": ROOT + "npc=1853"},
            {"href": ROOT + "quest=7/quest"}, {"href": "https://www.wowhead.com/tbc/npc=1853"},
        ]}]}]}
        result = sources.discover_sources({ROOT + "guide/example": page}, {ROOT + "quest=7"})
        self.assertEqual([row["url"] for row in result], [ROOT + "npc=1853"])

    def test_discovery_preview_does_not_write_the_manifest(self):
        with patch.object(forever, "read_snapshots", return_value={}), patch.object(forever, "registered_urls", return_value=set()), patch.object(
            scraper, "dataset_json", return_value={"sources": []}
        ), patch.object(scraper, "write_text", side_effect=AssertionError("preview wrote files")), redirect_stdout(io.StringIO()):
            self.assertEqual(scraper.main(["discover-sources", "--flavor", "forever"]), 0)

    def test_entity_page_records_typed_edges_without_inventing_coordinates(self):
        html = '<title>Fixture Boss - NPC - WoW Forever</title><a href="/forever/item=99">Unrelated link</a>'
        html += 'new Listview({id: "drops", data: [{"id":71,"name":"Fixture Ring","count":3,"outof":10}]});'
        row = sources.parse_entity_html(ROOT + "npc=1853", html)
        self.assertEqual(len(row["relationships"]), 1)
        self.assertEqual(row["relationships"][0]["object_id"], 71)
        self.assertNotIn("destination", row)
        self.assertNotIn(99, [edge["object_id"] for edge in row["relationships"]])

    def test_provider_registry_rejects_cross_client_and_lookalike_hosts(self):
        att_blob = "https://api.github.com/repos/ATTWoWAddon/AllTheThings/git/blobs/" + "a" * 40
        hotfix = ("https://raw.githubusercontent.com/wowsims/gamedata/" + "a" * 40
                  + "/patches/1.60.1.70888/hotfix-112709%2B104/items.txt")
        item_export = "https://raw.githubusercontent.com/wowsims/gamedata/" + "a" * 40 + "/items/items.txt"
        eg_cache = ("https://raw.githubusercontent.com/JIVESCORP/eg-link-output-wowf/" + "a" * 40
                    + "/data/wowf/1.60.1.70862/quests.enUS.json")
        eg_turn_ins = eg_cache.replace("quests.enUS.json", "turn_ins.json")
        eg_loot = eg_cache.replace("quests.enUS.json", "loot.json").replace("70862", "70938")
        self.assertEqual(sources.source_provider(att_blob), "att")
        for url, provider in (
            ("https://us.forums.blizzard.com/en/wow/t/fishing-competition-bugged/2406677/4", "blizzard_forums"),
            ("https://guide.wow4ever.se/en/quests/97332", "eg_link"),
            (eg_cache, "eg_link"),
            (eg_cache + "#/quests/94411", "eg_link"),
            (eg_turn_ins + "#/quests/79442", "eg_link"),
            (eg_loot, "eg_link"),
            (eg_loot + "#/sources/npc:6168|group", "eg_link"),
            ("https://bindonforever.com/quest/79442", "bindonforever"),
            ("https://wow4ever.quest/en/library-books", "wow4ever_quest"),
            ("https://foreverchanges.pro/quest/99143/bottles-and-baubles", "foreverchanges"),
            ("https://foreverchanges.pro/rares", "foreverchanges"),
            ("https://forever-item-finder.pages.dev/data/index.json", "forever_item_finder"),
            ("https://forever-item-finder.pages.dev/api/finds?id=10780", "forever_item_finder"),
            ("https://azeroth.wiki/forever/dungeons/blackrock-depths", "azeroth_wiki"),
            ("https://theforeverera.com/en/quests/3369/", "foreverera"),
            ("https://forever.warcraftdb.com/api/data/node/quest/1101", "warcraftdb"),
            ("https://questing.wiki/wow-forever/quests/2904/", "questing_wiki"),
            ("https://www.60.tools/quests/96252-tarnished-treasures", "sixtytools"),
            ("https://www.method.gg/wow-forever/how-to-get-malignant-root-powerful-rare-ring-in-wow-forever", "method"),
            ("https://www.method.gg/wow-forever/how-to-get-to-all-starting-zones-in-wow-forever-and-best-starting-zones", "method"),
            ("https://www.method.gg/wow-forever/dungeons/razorfen-kraul", "method"),
            ("https://guide.wow4ever.se/en/npc/255887", "eg_link"),
            ("https://hearthproof.com/classes/hunter/leveling/", "hearthproof"),
            ("https://hearthproof.com/classes/rogue/leveling/", "hearthproof"),
            ("https://howtovideogame.com/wow-forever-learn-fishing-fast-night-elf/", "howtovideogame"),
            ("https://polestar.guide/guides/class/rogue/the-horn-of-xelthos", "polestar"),
            ("https://polestar.guide/guides/class/shaman/call-of-air-horde", "polestar"),
            ("https://daybreakforever.com/static/forever/datamine.json#/live_items/7", "daybreak"),
            ("https://daybreakforever.com/blog/molten-core-loot-at-level-30", "daybreak"),
            ("https://db.icy-veins.com/wow-forever/quests/26", "icyveins"),
            ("https://www.reddit.com/r/wowforever/comments/1xq5ze1/cant_get_the_aquatic_form_quest/", "reddit"),
            ("https://wowf.io/en/professions/fishing/ranks", "wowf"),
            ("https://warcraft.wiki.gg/wiki/Ancient_Heirloom", "warcraft_wiki"),
            ("https://warcraft.wiki.gg/wiki/Fishing_pole", "warcraft_wiki"),
            ("https://warcraft.wiki.gg/wiki/Forever_fishing_techniques", "warcraft_wiki"),
            ("https://warcraft.wiki.gg/wiki/Slydris", "warcraft_wiki"),
            ("https://www.wow-professions.com/forever/how-to-fish", "wow_professions"),
            ("https://wowforeverinfo.com/guides/wailing-caverns/", "wowforeverinfo"),
            ("https://wowforeverinfo.com/guides/razorfen-kraul/", "wowforeverinfo"),
            ("https://wowforeverguides.com/dungeons/upper-blackrock-spire", "wowforeverguides"),
            ("https://wowseer.gg/guides/fishing", "wowseer"),
            ("https://wowtbc.gg/warcraftforever/loot-tables/dungeons/the-drowned-city/", "wowtbc"),
            ("https://raw.githubusercontent.com/timbers-addons/timbers-field-guide/"
             "af77b439058ece15525b9447519e3fb2e37d0d43/CHANGELOG.md", "timbers_field_guide"),
            (hotfix, "wowsims_gamedata"),
            (item_export, "wowsims_gamedata"),
        ):
            self.assertEqual(sources.source_provider(url), provider)
        for url in ("https://www.wowhead.com/tbc/item=71", "https://everloot.app.evil.invalid/api/items",
                    "https://user:password@everloot.app/api/items", "http://everloot.app/api/items",
                    att_blob.replace("ATTWoWAddon", "unrelated"), att_blob[:-40] + "master",
                    "https://us.forums.blizzard.com/en/overwatch/t/fishing-competition-bugged/2406677/4",
                    "https://guide.wow4ever.se/en/other/97332", "https://guide.wow4ever.se/en/quests/0",
                    "https://guide.wow4ever.se/en/npc/255888",
                    eg_cache.replace("a" * 40, "main"), eg_cache.replace("/data/wowf/", "/data/wow_classic_beta/"),
                    eg_cache + "#/quests/0", eg_cache + "?ref=main",
                    eg_turn_ins, eg_turn_ins + "#/players/79442",
                    eg_loot + "#/sources/npc:0|group", eg_loot + "#/quests/6168",
                    eg_loot.replace("/data/wowf/", "/data/wow_classic_beta/") + "#/sources/npc:6168|group",
                    "https://bindonforever.com/quest/79442?preview=1", "https://wow4ever.quest/en/another-guide",
                    "https://foreverchanges.pro/admin/99143/bottles-and-baubles",
                    "https://forever-item-finder.pages.dev/api/finds?id=0",
                    "https://forever-item-finder.pages.dev/api/finds?id=10780&id=281686",
                    "https://forever-item-finder.pages.dev/api/finds?id=10780#source",
                    "https://forever-item-finder.pages.dev/data/index.json?build=70938",
                    "https://theforeverera.com/en/items/seen/shoulder/",
                    "https://classic.warcraftdb.com/api/data/node/quest/1101",
                    "https://forever.warcraftdb.com/api/data/node/quest/1101?preview=1",
                    "https://questing.wiki/wow-classic/quests/2904/",
                    "https://questing.wiki/wow-forever/quests/2904/?preview=1",
                    "https://www.60.tools/items/96252-tarnished-treasures",
                    "https://polestar.guide/guides/class/rogue/unrelated",
                    "https://azeroth.wiki/classic/dungeons/blackrock-depths",
                    "https://daybreakforever.com/static/forever/datamine.json#/refused_items/7",
                    "https://warcraft.wiki.gg/wiki/Another_Page",
                    "https://www.wow-professions.com/classic/fishing-trainers-classic-wow",
                    hotfix.replace("a" * 40, "HEAD"), hotfix.replace("1.60.1.70888", "2.5.5.70888"),
                    "https://db.icy-veins.com/wow-classic/quests/26",
                    "https://www.reddit.com/r/classicwow/comments/1xq5ze1/cant_get_the_aquatic_form_quest/",
                    "https://wowf.io/en/professions/fishing", "https://wowseer.gg/guides/unrelated",
                    "https://raw.githubusercontent.com/timbers-addons/timbers-field-guide/main/CHANGELOG.md",
                    "https://wowtbc.gg/classic/loot-tables/dungeons/"):
            self.assertIsNone(sources.source_provider(url))

    def test_provider_pagination_retains_credit_and_empty_is_valid(self):
        credit = {"credit": "Data from Everloot", "licence": "CC BY-SA 4.0", "licenceUrl": "https://creativecommons.org/licenses/by-sa/4.0/", "source": "https://everloot.app/database/drops"}
        url = "https://everloot.app/api/rollups/drops?limit=1"
        get = unittest.mock.Mock(side_effect=[{"rates": [{"itemId": 71}], "attribution": credit, "next": url + "&offset=1"},
                                               {"rates": [], "attribution": credit, "next": None}])
        row = sources.collect_everloot(url, get, collected_at="2026-11-04T01:00:00Z")
        self.assertEqual(len(row["records"]), 1)
        self.assertEqual(row["attribution"], [credit])
        self.assertEqual(get.call_count, 2)
        empty = sources.collect_everloot(url, lambda _: {"rates": [], "next": None}, collected_at="fixture")
        self.assertEqual(empty["records"], [])

    def test_unavailable_partial_and_uncredited_feeds_are_rejected(self):
        url = "https://everloot.app/api/rollups/drops"
        for page in ({"unreachable": True, "rates": []}, {"rates": [{"itemId": 71}]}, {"next": url}):
            with self.subTest(page=page), self.assertRaises(ValueError):
                sources.collect_everloot(url, lambda _: page, collected_at="fixture")
        with self.assertRaisesRegex(RuntimeError, "page failed"):
            sources.collect_everloot(url, unittest.mock.Mock(side_effect=[{"rates": [], "next": url + "?offset=1"}, RuntimeError("page failed")]), collected_at="fixture")


class ForeverReviewTests(unittest.TestCase):
    def test_conflicting_item_observations_require_an_explicit_review_resolution(self):
        row = tooltip()
        other = deepcopy(row)
        other["url"] += "/second-observation"
        other["item_stats"]["stats"]["stamina"] = 9
        snapshots = {row["url"]: row, other["url"]: other}
        review = approval(row)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            forever.load_verified_items(snapshots, [review])
        review["evidence_refs"].append(sources.evidence_ref(other["url"], snapshots))
        review["conflict_resolution"] = "Fixture reviewer selected the first observation after checking the target build."
        items, stats = forever.load_verified_items(snapshots, [review])
        self.assertEqual(stats[71]["stats"]["stamina"], 8)

    def test_available_alternatives_do_not_receive_a_bis_label(self):
        snapshot = tooltip()
        item_review = approval(snapshot)
        _, stats = forever.load_verified_items({snapshot["url"]: snapshot}, [item_review])
        profile = {"class": "Warrior", "spec": "Protection", "role": "tank", "slots": ["Ring"], "armor_types": ["Plate"], "weapon_types": ["Sword"]}
        document = {"profiles": [profile], "role_weights": {"tank": {"stamina": 2}}, "version": "fixture"}
        _, audit = forever.rank(stats, document, [], {})
        review = {**item_review, "type": "approve_ranking", "class": "Warrior", "spec": "Protection", "slot": "Ring",
                  "profile_version": "fixture", "candidate_digest": audit[0]["candidate_digest"], "item_ids": [71], "best_in_slot": False}
        lists, _ = forever.rank(stats, document, [review], {})
        self.assertEqual(lists[0]["items"][0]["rank_label"], "Alt")
        self.assertEqual(lists[0]["items"][0]["rank_group"], "ranked")

    def test_spell_tooltip_establishes_a_created_item_without_treating_reagents_as_outputs(self):
        row = sources.parse_entity_tooltip(ROOT + "spell=16990", json.dumps({"name":"Arcanite Champion", "tooltip":
            '<a href="/forever/item=12360">Arcanite Bar</a><span class="q3"><a href="/forever/item=12790">Arcanite Champion</a></span>'}))
        self.assertEqual([edge["object_id"] for edge in row["relationships"]], [12790])

    def test_guide_source_claims_keep_unavailability_and_relic_context(self):
        url = ROOT + "guide/example"
        row = {"url": url, "tables": [{"slot":"Idol", "rows":[{"item_id":71,"source_text":"Currently unobtainable",
                "source_links":[{"href":ROOT+"quest=7"}]}]}]}
        self.assertEqual(sources.guide_relationships(row)[0]["availability"], "unverified")
        with patch.object(forever,"dataset_json",return_value={"sources":[{"url":url,"data_family":"bis_lists","class":"Shaman","spec":"Restoration","status":"pending_live_review"}]}):
            observed = forever.guide_observations({url:row})
        self.assertIn(("Shaman","Restoration","Totem"), observed)

    def test_every_route_requires_explicit_faction_and_its_own_evidence(self):
        row = tooltip()
        review = approval(row)
        forever.load_verified_items({row["url"]: row}, [review])
        for missing in ("side", "evidence_refs", "reviewer", "quest_id"):
            invalid = deepcopy(review)
            invalid["sources"][0].pop(missing)
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                forever.load_verified_items({row["url"]: row}, [invalid])

    def test_evidence_ignores_collection_time_but_detects_changed_facts(self):
        row = tooltip()
        ref = sources.evidence_ref(row["url"], {row["url"]: row})
        changed_time = {**row, "fetched_at": "later"}
        self.assertEqual(ref, sources.evidence_ref(row["url"], {row["url"]: changed_time}))
        changed_facts = {**row, "name": "Changed"}
        with self.assertRaises(ValueError):
            sources.check_evidence_refs({"evidence_refs": [ref]}, sources.evidence_index({row["url"]: changed_facts}))

    def test_gap_report_remains_readable_with_stale_approvals_and_both_factions(self):
        row = tooltip()
        review = approval(row)
        row["name"] = "Changed after approval"
        profile = {"class": "Warrior", "spec": "Protection", "role": "tank", "slots": ["Ring"], "armor_types": ["Plate"], "weapon_types": ["Sword"]}
        document = {"profiles": [profile], "role_weights": {"tank": {"stamina": 2}}, "version": "fixture"}
        with patch.object(forever, "scoring_profiles", return_value=document), patch.object(forever, "dataset_json", side_effect=lambda f,n: {
            "overrides": {"overrides": [review]}, "scrape_manifest": {"sources": []}
        }[n]):
            report = forever.gaps({row["url"]: row})
        self.assertEqual(len(report["rows"]), 2)
        self.assertEqual({r["faction"] for r in report["rows"]}, {"Alliance", "Horde"})
        self.assertTrue(all("stale_review" in r["statuses"] for r in report["rows"]))
        self.assertTrue(report["review_issues"])
        self.assertEqual(report["summary"]["approved_items"], 0)
        self.assertEqual([r["item_id"] for r in report["provisional_items"]],[71])
        self.assertTrue(report["provisional_items"][0]["stale_review"])
        self.assertEqual(report["rows"][0]["provisional_candidates"][0]["item_id"],71)
        self.assertNotIn("route_leads",report["rows"][0]["provisional_candidates"][0])

    def test_route_attribution_survives_review_without_mutating_approval(self):
        row = tooltip()
        provider_url = "https://everloot.app/api/rollups/drops"
        credit = {"credit": "Data from Everloot", "licence": "CC BY-SA 4.0", "licenceUrl": "https://creativecommons.org/licenses/by-sa/4.0/", "source": "https://everloot.app"}
        feed = sources.normalize_everloot(provider_url, [{"rates": [], "attribution": credit}], collected_at="fixture")
        snapshots = {row["url"]: row, provider_url: feed}
        review = approval(row)
        review["sources"][0]["evidence_refs"].append(sources.evidence_ref(provider_url, snapshots))
        items, _ = forever.load_verified_items(snapshots, [review])
        self.assertEqual(items[71]["sources"][0]["attribution"], [credit])
        self.assertNotIn("attribution", review["sources"][0])


if __name__ == "__main__":
    unittest.main()
