from copy import deepcopy
import unittest

from tools.project import canonical_json
from tools.recommend_leveling import (
    build_recommendation_documents,
    candidate_score,
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

    def fixture_one_hand_weapon(self, item_id=990001, stats=None):
        return {
            "id": item_id,
            "name": "Fixture One-Hand Mace",
            "required_level": 1,
            "slot": "One Hand",
            "weapon_type": "One Hand",
            "weapon_subtype": "Mace",
            "dps": 20,
            "stats": stats or {"strength": 20},
            "source_bucket": "quest",
            "source_summary": "Quest: Fixture",
            "wowhead_url": f"https://www.wowhead.com/tbc/item={item_id}/fixture-one-hand-mace",
        }

    def fixture_two_hand_weapon(self, item_id=990002, subtype="Mace", stats=None):
        return {
            "id": item_id,
            "name": "Fixture Two-Hand Weapon",
            "required_level": 1,
            "slot": "Two Hand",
            "weapon_type": "Two Hand",
            "weapon_subtype": subtype,
            "dps": 30,
            "stats": stats or {"strength": 20},
            "source_bucket": "quest",
            "source_summary": "Quest: Fixture",
            "wowhead_url": f"https://www.wowhead.com/tbc/item={item_id}/fixture-two-hand-weapon",
        }

    def fixture_offhand(self, item_id=990003):
        return {
            "id": item_id,
            "name": "Fixture Held Off-hand",
            "required_level": 1,
            "slot": "Off Hand",
            "weapon_type": "One Hand",
            "stats": {"intellect": 20, "spell_power": 20},
            "source_bucket": "quest",
            "source_summary": "Quest: Fixture",
            "wowhead_url": f"https://www.wowhead.com/tbc/item={item_id}/fixture-held-offhand",
        }

    def fixture_shield(self, item_id=990004):
        return {
            "id": item_id,
            "name": "Fixture Shield",
            "required_level": 1,
            "slot": "Off Hand",
            "armor_type": "Shield",
            "armor": 500,
            "stats": {"stamina": 20, "defense_rating": 20},
            "source_bucket": "quest",
            "source_summary": "Quest: Fixture",
            "wowhead_url": f"https://www.wowhead.com/tbc/item={item_id}/fixture-shield",
        }

    def fixture_ammo(self, item_id=990005, slot="Ammo"):
        return {
            "id": item_id,
            "name": f"Fixture {slot}",
            "required_level": 1,
            "slot": slot,
            "stats": {"agility": 1},
            "source_bucket": "vendor",
            "source_summary": "Vendor: Fixture",
            "wowhead_url": f"https://www.wowhead.com/tbc/item={item_id}/fixture-ammo",
        }

    def fixture_relic(self, name, item_id=990006):
        return {
            "id": item_id,
            "name": name,
            "required_level": 1,
            "slot": "Relic",
            "stats": {"stamina": 1},
            "source_bucket": "quest",
            "source_summary": "Quest: Fixture",
            "wowhead_url": f"https://www.wowhead.com/tbc/item={item_id}/fixture-relic",
        }

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

    def test_generated_documents_do_not_emit_level_70_recommendations(self):
        item_stats, item_variants, racials, profiles = self.docs()
        profiles = deepcopy(profiles)
        profiles["runtime_contexts"] = ["best_overall"]
        profiles["spec_roles"] = {"Paladin/Retribution": "physical_dps"}
        item_stats = deepcopy(item_stats)
        item_stats["item_stats"].append(
            {
                "id": 30316,
                "name": "Devastation",
                "required_level": 70,
                "item_level": 175,
                "quality": "legendary",
                "binding": "bind_on_pickup",
                "boe": False,
                "slot": "Two Hand",
                "weapon_type": "Two Hand",
                "weapon_subtype": "Axe",
                "dps": 500,
                "stats": {"strength": 500},
                "source_bucket": "raid_drop",
                "source_summary": "Drop: Devastation (Tempest Keep)",
                "wowhead_url": "https://www.wowhead.com/tbc/item=30316/devastation",
            }
        )

        documents = build_recommendation_documents(item_stats, item_variants, racials, profiles)
        rows = documents["leveling_recommendations"]
        audit_rows = documents["recommendation_audit"]["rows"]

        self.assertTrue(rows)
        self.assertTrue(all(row["level_max"] <= 69 for row in rows))
        self.assertNotIn(30316, {row["item_id"] for row in rows})
        self.assertNotIn(30316, {row["item_id"] for row in audit_rows})

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
            "level_band": "58-69",
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

    def test_ret_paladin_best_overall_ignores_one_hand_form_only_mace(self):
        item_stats, item_variants, racials, profiles = self.docs()
        item_stats = {
            "item_stats": [
                {
                    "id": 21268,
                    "name": "Blessed Qiraji War Hammer",
                    "required_level": 60,
                    "item_level": 79,
                    "quality": "epic",
                    "binding": "bind_on_pickup",
                    "boe": False,
                    "slot": "One Hand",
                    "weapon_type": "One Hand",
                    "weapon_subtype": "Mace",
                    "dps": 60.71,
                    "armor": 70,
                    "stats": {"strength": 10, "stamina": 12, "defense_rating": 12},
                    "effect_stats": [
                        {
                            "type": "form_only",
                            "stats": {"attack_power": 337},
                            "raw_text": "Equip: Increases attack power by 337 in Cat, Bear, Dire Bear, and Moonkin forms only.",
                        }
                    ],
                    "source_bucket": "quest",
                    "source_summary": "Quest: Imperial Qiraji Regalia",
                    "wowhead_url": "https://www.wowhead.com/tbc/item=21268/blessed-qiraji-war-hammer",
                }
            ]
        }

        rows, audit = recommendation_rows_for(
            item_stats,
            item_variants,
            racials,
            profiles,
            class_name="Paladin",
            spec_name="Retribution",
            race="Human",
            level=64,
            slot="Main Hand",
            context="best_overall",
        )

        self.assertEqual(rows, [])
        self.assertNotIn(21268, {row["item_id"] for row in audit})

    def test_two_hand_physical_specs_reject_one_hand_best_overall_main_hand(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        one_hand = self.fixture_one_hand_weapon(stats={"strength": 999})

        for class_name, spec_name, race in [("Paladin", "Retribution", "Human"), ("Warrior", "Arms", "Human")]:
            with self.subTest(class_name=class_name, spec_name=spec_name):
                self.assertIsNone(candidate_score(one_hand, class_name, spec_name, race, 64, "Main Hand", "best_overall", profiles, racials))

    def test_dual_wield_specs_reject_two_hand_best_overall_after_dual_wield_level(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        one_hand = self.fixture_one_hand_weapon()
        two_hand = self.fixture_two_hand_weapon(subtype="Mace")

        for class_name, spec_name, race, level in [
            ("Warrior", "Fury", "Human", 64),
            ("Rogue", "Combat", "Human", 64),
            ("Shaman", "Enhancement", "Orc", 64),
        ]:
            with self.subTest(class_name=class_name, spec_name=spec_name):
                self.assertIsNotNone(candidate_score(one_hand, class_name, spec_name, race, level, "Main Hand", "best_overall", profiles, racials))
                self.assertIsNotNone(candidate_score(one_hand, class_name, spec_name, race, level, "Off Hand", "best_overall", profiles, racials))
                self.assertIsNone(candidate_score(two_hand, class_name, spec_name, race, level, "Two Hand", "best_overall", profiles, racials))

    def test_enhancement_before_dual_wield_level_keeps_two_hand_and_no_one_hand_offhand(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        one_hand = self.fixture_one_hand_weapon()
        two_hand = self.fixture_two_hand_weapon(subtype="Mace")

        self.assertIsNone(candidate_score(one_hand, "Shaman", "Enhancement", "Orc", 39, "Off Hand", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(two_hand, "Shaman", "Enhancement", "Orc", 39, "Two Hand", "best_overall", profiles, racials))

    def test_protection_specs_require_one_hand_main_hand_and_shield_offhand(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        one_hand = self.fixture_one_hand_weapon()
        two_hand = self.fixture_two_hand_weapon(subtype="Mace")
        offhand = self.fixture_offhand()
        shield = self.fixture_shield()

        for class_name, spec_name in [("Paladin", "Protection"), ("Warrior", "Protection")]:
            with self.subTest(class_name=class_name, spec_name=spec_name):
                self.assertIsNotNone(candidate_score(one_hand, class_name, spec_name, "Human", 64, "Main Hand", "best_overall", profiles, racials))
                self.assertIsNone(candidate_score(two_hand, class_name, spec_name, "Human", 64, "Two Hand", "best_overall", profiles, racials))
                self.assertIsNone(candidate_score(offhand, class_name, spec_name, "Human", 64, "Off Hand", "best_overall", profiles, racials))
                self.assertIsNotNone(candidate_score(shield, class_name, spec_name, "Human", 64, "Off Hand", "best_overall", profiles, racials))

    def test_feral_druid_allows_one_hand_feral_weapon_main_hand_not_offhand(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        feral_mace = self.fixture_one_hand_weapon(
            21268,
            stats={"strength": 10, "stamina": 12, "defense_rating": 12},
        )
        feral_mace["effect_stats"] = [{"type": "form_only", "stats": {"attack_power": 337}}]

        main_hand = candidate_score(feral_mace, "Druid", "Feral dps", "*", 64, "Main Hand", "best_overall", profiles, racials)
        off_hand = candidate_score(feral_mace, "Druid", "Feral dps", "*", 64, "Off Hand", "best_overall", profiles, racials)

        self.assertIsNotNone(main_hand)
        self.assertEqual(main_hand["stats"]["attack_power"], 337)
        self.assertIsNone(off_hand)

    def test_caster_and_healer_weapon_styles_still_allow_staff_one_hand_and_offhand(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        staff = self.fixture_two_hand_weapon(subtype="Staff", stats={"intellect": 20, "spell_power": 20})
        dagger = {
            **self.fixture_one_hand_weapon(stats={"intellect": 20, "spell_power": 20}),
            "weapon_subtype": "Dagger",
        }
        offhand = self.fixture_offhand()
        shield = self.fixture_shield()

        self.assertIsNotNone(candidate_score(staff, "Priest", "Shadow", "Human", 64, "Two Hand", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(dagger, "Priest", "Shadow", "Human", 64, "Main Hand", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(offhand, "Priest", "Shadow", "Human", 64, "Off Hand", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(shield, "Shaman", "Restoration", "Orc", 64, "Off Hand", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(dagger, "Priest", "Shadow", "Human", 64, "Off Hand", "best_overall", profiles, racials))

    def test_ammo_recommendations_require_ranged_ammo_class_access(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        ammo = self.fixture_ammo()

        self.assertIsNotNone(candidate_score(ammo, "Hunter", "Beast mastery", "Dwarf", 20, "Ammo", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(ammo, "Rogue", "Combat", "Human", 20, "Ammo", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(ammo, "Warrior", "Arms", "Human", 20, "Ammo", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(ammo, "Mage", "Fire", "Gnome", 20, "Ammo", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(ammo, "Paladin", "Retribution", "Human", 20, "Ammo", "best_overall", profiles, racials))

    def test_quiver_recommendations_are_hunter_only(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        quiver = self.fixture_ammo(slot="Quiver")

        self.assertIsNotNone(candidate_score(quiver, "Hunter", "Marksmanship", "Dwarf", 20, "Quiver", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(quiver, "Rogue", "Combat", "Human", 20, "Quiver", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(quiver, "Warrior", "Arms", "Human", 20, "Quiver", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(quiver, "Mage", "Fire", "Gnome", 20, "Quiver", "best_overall", profiles, racials))

    def test_relic_recommendations_require_class_relic_type(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        idol = self.fixture_relic("Fixture Idol of the Wild", 990006)
        libram = self.fixture_relic("Fixture Libram of Justice", 990007)
        tome = self.fixture_relic("Fixture Tome of the Lightbringer", 990008)
        totem = self.fixture_relic("Fixture Totem of Storms", 990009)
        ambiguous = self.fixture_relic("Fixture Relic Hunter Belt", 990010)

        self.assertIsNotNone(candidate_score(idol, "Druid", "Feral dps", "*", 64, "Relic", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(idol, "Paladin", "Retribution", "Human", 64, "Relic", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(libram, "Paladin", "Retribution", "Human", 64, "Relic", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(tome, "Paladin", "Protection", "Human", 64, "Relic", "best_overall", profiles, racials))
        self.assertIsNotNone(candidate_score(totem, "Shaman", "Enhancement", "Orc", 64, "Relic", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(totem, "Druid", "Balance", "*", 64, "Relic", "best_overall", profiles, racials))
        self.assertIsNone(candidate_score(ambiguous, "Druid", "Balance", "*", 64, "Relic", "best_overall", profiles, racials))

    def test_generated_recommendation_documents_do_not_emit_one_hand_slot(self):
        _item_stats, item_variants, racials, profiles = self.docs()
        profiles = deepcopy(profiles)
        profiles["runtime_contexts"] = ["best_overall"]
        profiles["spec_roles"] = {"Rogue/Combat": "physical_dps", "Paladin/Retribution": "physical_dps", "Druid/Feral dps": "physical_dps"}
        item_stats = {
            "item_stats": [
                self.fixture_one_hand_weapon(21268, stats={"strength": 10}),
                self.fixture_two_hand_weapon(990010, subtype="Mace"),
            ]
        }

        documents = build_recommendation_documents(item_stats, item_variants, racials, profiles)
        rows = documents["leveling_recommendations"]

        self.assertNotIn("One Hand", {row["slot"] for row in rows})
        self.assertNotIn(21268, {row["item_id"] for row in rows if row["class"] == "Paladin" and row["spec"] == "Retribution"})
        self.assertNotIn(21268, {row["item_id"] for row in rows if row["class"] == "Druid" and row["spec"] == "Feral dps" and row["slot"] == "Off Hand"})

    def test_generated_documents_keep_ammo_for_ranged_classes_only(self):
        _item_stats, item_variants, racials, profiles = self.docs()
        profiles = deepcopy(profiles)
        profiles["runtime_contexts"] = ["best_overall"]
        profiles["spec_roles"] = {
            "Hunter/Beast mastery": "physical_dps",
            "Rogue/Combat": "physical_dps",
            "Warrior/Arms": "physical_dps",
            "Mage/Fire": "caster_dps",
        }
        item_stats = {
            "item_stats": [
                self.fixture_ammo(990011),
                {
                    **self.fixture_two_hand_weapon(990012, subtype="Staff", stats={"intellect": 20, "spell_power": 20}),
                    "required_level": 1,
                },
            ]
        }

        documents = build_recommendation_documents(item_stats, item_variants, racials, profiles)
        ammo_classes = {
            row["class"]
            for row in documents["leveling_recommendations"]
            if row["slot"] == "Ammo"
        }

        self.assertEqual(ammo_classes, {"Hunter", "Rogue", "Warrior"})

    def test_form_only_attack_power_scores_only_for_feral_druids(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        mace = {
            "id": 21268,
            "name": "Blessed Qiraji War Hammer",
            "required_level": 60,
            "slot": "One Hand",
            "weapon_type": "One Hand",
            "weapon_subtype": "Mace",
            "dps": 60.71,
            "stats": {"strength": 10, "stamina": 12, "defense_rating": 12},
            "effect_stats": [
                {
                    "type": "form_only",
                    "stats": {"attack_power": 337},
                    "raw_text": "Equip: Increases attack power by 337 in Cat, Bear, Dire Bear, and Moonkin forms only.",
                }
            ],
            "source_bucket": "quest",
        }

        paladin = candidate_score(
            mace,
            "Paladin",
            "Retribution",
            "Human",
            64,
            "Main Hand",
            "hit",
            profiles,
            racials,
        )
        druid = candidate_score(
            mace,
            "Druid",
            "Feral dps",
            "*",
            64,
            "Main Hand",
            "best_overall",
            profiles,
            racials,
        )

        self.assertIsNotNone(paladin)
        self.assertNotIn("attack_power", paladin["stats"])
        self.assertIn("dps", paladin["stats"])
        self.assertIsNotNone(druid)
        self.assertEqual(druid["stats"]["attack_power"], 337)
        self.assertNotIn("dps", druid["stats"])

    def test_off_hand_one_hand_weapons_require_dual_wield_access(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        offhand_mace = {
            "id": 999105,
            "name": "Fixture Offhand Mace",
            "required_level": 1,
            "slot": "One Hand",
            "weapon_type": "One Hand",
            "weapon_subtype": "Mace",
            "dps": 20,
            "stats": {"strength": 10},
            "source_bucket": "quest",
        }

        self.assertIsNone(candidate_score(offhand_mace, "Paladin", "Retribution", "Human", 64, "Off Hand", "hit", profiles, racials))
        self.assertIsNone(candidate_score(offhand_mace, "Rogue", "Combat", "Human", 9, "Off Hand", "hit", profiles, racials))
        self.assertIsNotNone(candidate_score(offhand_mace, "Rogue", "Combat", "Human", 10, "Off Hand", "hit", profiles, racials))
        self.assertIsNone(candidate_score(offhand_mace, "Shaman", "Enhancement", "Orc", 39, "Off Hand", "hit", profiles, racials))
        self.assertIsNotNone(candidate_score(offhand_mace, "Shaman", "Enhancement", "Orc", 40, "Off Hand", "hit", profiles, racials))
        self.assertIsNone(candidate_score(offhand_mace, "Shaman", "Elemental", "Orc", 70, "Off Hand", "hit", profiles, racials))

    def test_armor_recommendations_respect_class_and_level_proficiencies(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        plate_chest = {
            "id": 999106,
            "name": "Fixture Plate Chest",
            "required_level": 1,
            "slot": "Chest",
            "armor_type": "Plate",
            "armor": 500,
            "stats": {"strength": 20, "stamina": 20},
            "source_bucket": "quest",
        }

        self.assertIsNone(candidate_score(plate_chest, "Druid", "Feral dps", "*", 60, "Chest", "hit", profiles, racials))
        self.assertIsNone(candidate_score(plate_chest, "Paladin", "Retribution", "Human", 39, "Chest", "hit", profiles, racials))
        self.assertIsNotNone(candidate_score(plate_chest, "Paladin", "Retribution", "Human", 40, "Chest", "hit", profiles, racials))

    def test_expertise_rating_and_hunter_ranged_attack_power_are_scored(self):
        _item_stats, _item_variants, racials, profiles = self.docs()
        expertise_ring = {
            "id": 999107,
            "name": "Fixture Expertise Ring",
            "required_level": 1,
            "slot": "Ring",
            "stats": {"expertise_rating": 3.94},
            "source_bucket": "quest",
        }
        hunter_bow = {
            "id": 999108,
            "name": "Fixture Hunter Bow",
            "required_level": 1,
            "slot": "Ranged",
            "weapon_type": "Ranged",
            "weapon_subtype": "Bow",
            "stats": {"ranged_attack_power": 20},
            "source_bucket": "quest",
        }

        expertise = candidate_score(expertise_ring, "Paladin", "Retribution", "Human", 64, "Ring", "hit", profiles, racials)
        hunter = candidate_score(hunter_bow, "Hunter", "Marksmanship", "Dwarf", 64, "Ranged", "hit", profiles, racials)

        self.assertIsNotNone(expertise)
        self.assertAlmostEqual(expertise["stats"]["expertise"], 1.0)
        self.assertGreater(expertise["score"], 0)
        self.assertIsNotNone(hunter)
        self.assertEqual(hunter["stats"]["attack_power"], 20)
        self.assertGreater(hunter["score"], 0)

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

    def test_level_70_requests_are_clamped_and_do_not_emit_devastation(self):
        item_stats, item_variants, racials, profiles = self.docs()
        item_stats = deepcopy(item_stats)
        item_stats["item_stats"].append(
            {
                "id": 30316,
                "name": "Devastation",
                "required_level": 70,
                "item_level": 175,
                "quality": "legendary",
                "binding": "bind_on_pickup",
                "boe": False,
                "slot": "Two Hand",
                "weapon_type": "Two Hand",
                "weapon_subtype": "Axe",
                "dps": 500,
                "stats": {"strength": 500},
                "source_bucket": "raid_drop",
                "source_summary": "Drop: Devastation (Tempest Keep)",
                "wowhead_url": "https://www.wowhead.com/tbc/item=30316/devastation",
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
            level=70,
            slot="Two Hand",
            context="best_overall",
        )

        self.assertTrue(rows)
        self.assertLessEqual(max(row["level_max"] for row in rows), 69)
        self.assertNotIn(30316, {row["item_id"] for row in rows})
        self.assertNotIn(30316, {row["item_id"] for row in audit})

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
