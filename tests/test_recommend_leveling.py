from copy import deepcopy
import unittest

from tools.project import canonical_json
from tools.recommend_leveling import (
    build_recommendation_documents,
    compact_adjacent_recommendation_ranges,
    recommendation_rows_for,
    racial_score_bonus,
)


class LevelingRecommendationTests(unittest.TestCase):
    def docs(self):
        return (
            {
                "item_stats": [
                    {
                        "id": 999101,
                        "name": "Shaarde the Greater",
                        "required_level": 64,
                        "item_level": 100,
                        "quality": "rare",
                        "binding": "bind_on_equip",
                        "boe": True,
                        "slot": "Two Hand",
                        "weapon_type": "Two Hand",
                        "weapon_subtype": "Sword",
                        "dps": 60,
                        "stats": {"strength": 10},
                        "source_bucket": "world_drop",
                        "source_summary": "World Drop",
                        "wowhead_url": "https://www.wowhead.com/tbc/item=999101/shaarde-the-greater",
                    },
                    {
                        "id": 999102,
                        "name": "Fixture Voidaxe",
                        "required_level": 64,
                        "item_level": 100,
                        "quality": "rare",
                        "binding": "bind_on_pickup",
                        "boe": False,
                        "slot": "Two Hand",
                        "weapon_type": "Two Hand",
                        "weapon_subtype": "Axe",
                        "dps": 62,
                        "stats": {"strength": 10},
                        "source_bucket": "quest",
                        "source_summary": "Quest: Fixture Arena",
                        "wowhead_url": "https://www.wowhead.com/tbc/item=999102/fixture-voidaxe",
                    },
                ]
            },
            {"item_variants": []},
            canonical_json("racial_modifiers"),
            canonical_json("scoring_profiles"),
        )

    def test_human_ret_paladin_level_64_considers_and_tags_shaarde(self):
        item_stats, item_variants, racials, profiles = self.docs()

        rows, audit = recommendation_rows_for(
            item_stats,
            item_variants,
            racials,
            profiles,
            class_name="Paladin",
            spec_name="Retribution",
            race="Human",
            level=64,
            slot="Two Hand",
            context="best_overall",
        )

        self.assertGreaterEqual(len(audit), 2)
        self.assertEqual(rows[0]["item_id"], 999101)
        self.assertEqual(rows[0]["reason_tags"], ["best_for_human", "best_overall", "human_sword_bonus"])

    def test_generated_documents_include_level_64_shaarde_checkpoint(self):
        item_stats, item_variants, racials, profiles = self.docs()
        profiles = deepcopy(profiles)
        profiles["runtime_contexts"] = ["best_overall"]
        profiles["spec_roles"] = {"Paladin/Retribution": "physical_dps"}

        documents = build_recommendation_documents(item_stats, item_variants, racials, profiles)
        rows = [
            row
            for row in documents["leveling_recommendations"]
            if row["class"] == "Paladin"
            and row["spec"] == "Retribution"
            and row["race"] == "Human"
            and row["item_id"] == 999101
        ]

        self.assertTrue(rows)
        self.assertTrue(any(row["level_min"] == 64 and "human_sword_bonus" in row["reason_tags"] for row in rows))

    def test_generated_documents_keep_racial_tag_when_selection_matches_baseline(self):
        item_stats, _item_variants, racials, profiles = self.docs()
        profiles = deepcopy(profiles)
        profiles["runtime_contexts"] = ["best_overall"]
        profiles["spec_roles"] = {"Paladin/Retribution": "physical_dps"}
        item_stats = {"item_stats": [deepcopy(item_stats["item_stats"][0])]}

        documents = build_recommendation_documents(item_stats, {"item_variants": []}, racials, profiles)
        rows = [
            row
            for row in documents["leveling_recommendations"]
            if row["class"] == "Paladin"
            and row["spec"] == "Retribution"
            and row["race"] == "Human"
            and row["item_id"] == 999101
        ]

        self.assertTrue(rows)
        self.assertTrue(any("human_sword_bonus" in row["reason_tags"] for row in rows))

    def test_compacts_adjacent_identical_recommendation_ranges(self):
        row = {
            "class": "Paladin",
            "spec": "Retribution",
            "race": "Human",
            "level_min": 64,
            "level_max": 64,
            "level_band": "58-70",
            "slot": "Two Hand",
            "item_id": 999101,
            "variant_id": None,
            "rank": 1,
            "context": "best_overall",
            "source_bucket": "dungeon_drop",
            "score": 100.0,
            "score_delta_pct": 0.0,
            "reason_tags": ["best_for_human", "best_overall", "human_sword_bonus"],
            "source_summary": "Drop: Mana-Tombs",
            "source_url": "https://www.wowhead.com/tbc/item=999101/shaarde-the-greater",
        }
        rows = [deepcopy(row), {**deepcopy(row), "level_min": 65, "level_max": 67}]

        compacted = compact_adjacent_recommendation_ranges(rows)

        self.assertEqual(len(compacted), 1)
        self.assertEqual(compacted[0]["level_min"], 64)
        self.assertEqual(compacted[0]["level_max"], 67)

    def test_orc_ret_paladin_prefers_close_axe_with_orc_bonus(self):
        item_stats, item_variants, racials, profiles = self.docs()

        rows, _audit = recommendation_rows_for(
            item_stats,
            item_variants,
            racials,
            profiles,
            class_name="Paladin",
            spec_name="Retribution",
            race="Orc",
            level=64,
            slot="Two Hand",
            context="best_overall",
        )

        self.assertEqual(rows[0]["item_id"], 999102)
        self.assertIn("orc_axe_bonus", rows[0]["reason_tags"])

    def test_paladin_recommendations_ignore_unusable_staffs(self):
        item_stats, item_variants, racials, profiles = self.docs()
        item_stats = deepcopy(item_stats)
        item_stats["item_stats"].append(
            {
                "id": 999103,
                "name": "Fixture Staff",
                "required_level": 64,
                "item_level": 100,
                "quality": "rare",
                "binding": "bind_on_pickup",
                "boe": False,
                "slot": "Two Hand",
                "weapon_type": "Two Hand",
                "weapon_subtype": "Staff",
                "dps": 200,
                "stats": {"attack_power": 500},
                "source_bucket": "quest",
                "source_summary": "Quest: Fixture Staff",
                "wowhead_url": "https://www.wowhead.com/tbc/item=999103/fixture-staff",
            }
        )

        rows, audit = recommendation_rows_for(
            item_stats,
            item_variants,
            racials,
            profiles,
            class_name="Paladin",
            spec_name="Retribution",
            race="Human",
            level=64,
            slot="Two Hand",
            context="best_overall",
        )

        self.assertNotIn(999103, {row["item_id"] for row in rows})
        self.assertNotIn(999103, {row["item_id"] for row in audit})

    def test_pre_70_leveling_recommendations_ignore_raid_drops(self):
        item_stats, item_variants, racials, profiles = self.docs()
        item_stats = deepcopy(item_stats)
        item_stats["item_stats"].append(
            {
                "id": 999104,
                "name": "Fixture Raid Hammer",
                "required_level": 60,
                "item_level": 100,
                "quality": "epic",
                "binding": "bind_on_pickup",
                "boe": False,
                "slot": "Two Hand",
                "weapon_type": "Two Hand",
                "weapon_subtype": "Mace",
                "dps": 200,
                "stats": {"strength": 200},
                "source_bucket": "raid_drop",
                "source_summary": "Drop: Fixture Raid",
                "wowhead_url": "https://www.wowhead.com/tbc/item=999104/fixture-raid-hammer",
            }
        )

        rows, audit = recommendation_rows_for(
            item_stats,
            item_variants,
            racials,
            profiles,
            class_name="Paladin",
            spec_name="Retribution",
            race="Human",
            level=64,
            slot="Two Hand",
            context="best_overall",
        )

        self.assertEqual(rows[0]["item_id"], 999101)
        self.assertNotIn(999104, {row["item_id"] for row in rows})
        self.assertNotIn(999104, {row["item_id"] for row in audit})

    def test_random_suffix_variants_are_scored_as_distinct_candidates(self):
        item_stats, _item_variants, racials, profiles = self.docs()
        item_variants = {
            "item_variants": [
                {
                    "item_id": 999101,
                    "random_suffix_id": 123,
                    "suffix_name": "of the Tiger",
                    "stat_delta": {"strength": 50, "agility": 20},
                    "source_url": "https://www.wowhead.com/tbc/item=999101/shaarde-the-greater?rand=123",
                }
            ]
        }

        rows, _audit = recommendation_rows_for(
            item_stats,
            item_variants,
            racials,
            profiles,
            class_name="Paladin",
            spec_name="Retribution",
            race="Human",
            level=64,
            slot="Two Hand",
            context="best_overall",
        )

        self.assertEqual(rows[0]["variant_id"], "999101:123")
        self.assertIn("suffix_winner", rows[0]["reason_tags"])
        self.assertIn(999101, {row["item_id"] for row in rows})

    def test_racial_modifier_contexts_cover_tbc_races(self):
        racials = canonical_json("racial_modifiers")
        weights = {
            "crit_percent": 1,
            "dodge_percent": 1,
            "expertise": 1,
            "health_percent": 1,
            "hit_percent": 1,
            "intellect_percent": 1,
            "spell_hit_percent": 1,
            "spirit_percent": 1,
        }
        fixtures = {
            "Blood Elf": ({"weapon_subtype": "Sword", "stats": {}}, "physical_dps"),
            "Draenei": ({"weapon_subtype": "Sword", "stats": {}}, "physical_dps"),
            "Dwarf": ({"weapon_subtype": "Gun", "stats": {}}, "physical_dps"),
            "Gnome": ({"weapon_subtype": "Sword", "stats": {"intellect": 10}}, "caster_dps"),
            "Human": ({"weapon_subtype": "Sword", "stats": {"spirit": 10}}, "physical_dps"),
            "Night Elf": ({"weapon_subtype": "Sword", "stats": {"dodge": 1}}, "tank"),
            "Orc": ({"weapon_subtype": "Axe", "stats": {}}, "physical_dps"),
            "Tauren": ({"weapon_subtype": "Sword", "stats": {"health": 100}}, "tank"),
            "Troll": ({"weapon_subtype": "Bow", "stats": {}}, "physical_dps"),
            "Undead": ({"weapon_subtype": "Sword", "stats": {}}, "physical_dps"),
        }

        for race, (item, role) in fixtures.items():
            with self.subTest(race=race):
                score, tags = racial_score_bonus(item, race, role, weights, racials)
                self.assertTrue(score > 0 or tags, (score, tags))


if __name__ == "__main__":
    unittest.main()
