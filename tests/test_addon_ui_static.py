import re
import unittest

from tools.project import ADDON_DIR


class AddonUIStaticTests(unittest.TestCase):
    def read_lua(self, name: str) -> str:
        return (ADDON_DIR / name).read_text(encoding="utf-8")

    def test_user_facing_name_remains_spaced(self):
        self.assertIn('BigBiSList.displayName = "Big BiS List"', self.read_lua("Config.lua"))
        self.assertIn("Big BiS List", self.read_lua("UI.lua"))
        self.assertIn("Big BiS List", self.read_lua("Tooltip.lua"))
        self.assertIn("BigBiSList.displayName", self.read_lua("Minimap.lua"))

    def test_phase_display_labels_are_phase_based(self):
        data_index = self.read_lua("DataIndex.lua")
        expected = {
            "PR": "Pre-Raid",
            "T4": "Phase 1",
            "T5": "Phase 2",
            "T6": "Phase 3",
            "ZA": "Phase 4",
            "SWP": "Phase 5",
        }
        for key, label in expected.items():
            self.assertRegex(data_index, rf"{key}\s*=\s*\"{re.escape(label)}\"")

        ui_text = self.read_lua("UI.lua") + self.read_lua("Tooltip.lua")
        self.assertNotIn("Tier 4", ui_text)
        self.assertNotIn("Tier 5", ui_text)
        self.assertNotIn("Tier 6", ui_text)

    def test_saved_variable_defaults_cover_ui_state(self):
        config = self.read_lua("Config.lua")
        for token in [
            "local DEFAULTS_VERSION = 3",
            "window = {",
            "showMinimap = true",
            "minimap = {",
            "tooltips = {",
            "selection = {",
            'selectedPhase = "PR"',
            'phase = "PR"',
            "filters = {",
            "bankCache = {",
            "wishlist = {}",
            "ignoredItems = {}",
            "migrateLegacyDefaults",
        ]:
            self.assertIn(token, config)

    def test_public_ui_methods_exist(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        for method in ["OpenMainFrame", "CloseMainFrame", "ToggleMainFrame", "RefreshUI"]:
            self.assertIn(f"function BigBiSList:{method}()", ui)
        for method in ["GetDataIndex", "GetPhaseRows", "GetPlannerRows", "GetDisplaySlotFilters", "GetItemBestUseForSpec", "GetEquippedGearRows"]:
            self.assertIn(f"function BigBiSList:{method}", data_index)
        self.assertIn("function BigBiSList:SetSelection", self.read_lua("Config.lua"))

    def test_slot_filters_are_equipment_facing(self):
        data_index = self.read_lua("DataIndex.lua")
        display_block = data_index.split("local DISPLAY_SLOT_FILTERS = {", 1)[1].split("local DISPLAY_SLOT_FILTER_MAP", 1)[0]

        for label in [
            'label = "Rings"',
            'label = "Trinkets"',
            'label = "Main Hand"',
            'label = "Off Hand"',
            'label = "Ranged/Relic"',
        ]:
            self.assertIn(label, display_block)

        self.assertNotIn('key = "Two Hand"', display_block)
        self.assertNotIn('key = "Dual Wield"', display_block)
        self.assertNotIn('key = "Idol"', display_block)
        self.assertIn('slots = { "Main Hand", "Two Hand", "Dual Wield" }', display_block)
        self.assertIn('slots = { "Off Hand", "Dual Wield" }', display_block)
        self.assertIn('slots = { "Ranged", "Idol", "Totem", "Libram", "Relic" }', display_block)

    def test_gear_tab_uses_real_equipment_slots(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        self.assertIn('{ "Phase", "Gear", "Planner", "Enhance", "Wishlist", "Settings" }', ui)
        self.assertIn("function UI:RenderGearTab()", ui)
        self.assertIn("function UI:CreateGearSlotRow", ui)
        self.assertIn('label = "Finger 1"', data_index)
        self.assertIn('label = "Finger 2"', data_index)
        self.assertIn('label = "Trinket 1"', data_index)
        self.assertIn('label = "Trinket 2"', data_index)
        self.assertIn('label = "Ranged/Relic"', data_index)
        self.assertNotIn('label = "Two Hand"', data_index)
        self.assertNotIn('label = "Dual Wield"', data_index)

    def test_ownership_badges_and_bank_cache_are_supported(self):
        ui = self.read_lua("UI.lua")
        config = self.read_lua("Config.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            "CreateOwnershipBadge",
            "OWNERSHIP_LABELS",
            "BANKFRAME_OPENED",
            "PLAYERBANKSLOTS_CHANGED",
            "ScanBankItems",
            'filters.ownedState = "bank"',
        ]:
            self.assertIn(token, ui)
        self.assertIn("bankCache = {", config)
        self.assertIn('elseif filters.ownedState == "bank"', data_index)

    def test_details_drawer_uses_measured_blocks(self):
        ui = self.read_lua("UI.lua")
        self.assertIn("CreateDetailsTitle", ui)
        self.assertIn("GetStringHeight", ui)
        self.assertNotIn("estimatedLines", ui)
        self.assertNotIn("string.len(tostring(bodyText", ui)

    def test_planner_scoring_matches_v1_weights(self):
        data_index = self.read_lua("DataIndex.lua")
        for snippet in [
            "score = score + 60",
            "score = score + 30",
            "score = score + 35",
            "futureBisCount * 8",
            "futureOptionCount * 4",
            "score = score + 10",
            "score = score + 5",
            "if score > 100 then",
        ]:
            self.assertIn(snippet, data_index)

    def test_esc_closable_frame_is_registered(self):
        ui = self.read_lua("UI.lua")
        self.assertIn('"BigBiSListMainFrame"', ui)
        self.assertIn("UISpecialFrames", ui)
        self.assertIn("OnEscapePressed", ui)

    def test_minimap_button_is_native_and_toggleable(self):
        minimap = self.read_lua("Minimap.lua")
        ui = self.read_lua("UI.lua")
        core = self.read_lua("Core.lua")
        for token in [
            '"BigBiSListMinimapButton"',
            "Interface\\\\Icons\\\\INV_Misc_QuestionMark",
            "RegisterForDrag",
            "ToggleMainFrame",
            "RefreshMinimapButton",
            "profile.showMinimap",
        ]:
            self.assertIn(token, minimap)
        self.assertIn("Show minimap button", ui)
        self.assertIn("InitMinimapButton", core)
