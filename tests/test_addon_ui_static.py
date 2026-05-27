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
        self.assertIn('slots = { "Ranged", "Ammo", "Quiver", "Idol", "Totem", "Libram", "Relic" }', display_block)

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

    def test_access_badges_are_separate_from_ownership(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "CreateAccessBadge",
            "ACCESS_LABELS",
            "GetAccessStatus",
            "EvaluateRequirement",
            "BuildAccessState",
            "Requirements",
            "Prereq",
        ]:
            self.assertIn(token, ui)
        self.assertIn("CreateOwnershipBadge", ui)
        self.assertLess(ui.index("CreateOwnershipBadge"), ui.index("CreateAccessBadge"))
        self.assertIn("requirements = mergedRequirements", data_index)

    def test_source_aware_access_options_are_indexed(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "buildAccessOptions",
            "splitRequirements",
            "sourceMatchesRequirement",
            "source.requirements",
            "access_options = buildAccessOptions",
            "gemSourcesById",
            "enchantSourcesByKey",
            "enhancementSourceKey(entityType, enchant.id)",
            "forceSourceScopedEquip = entityType == \"spell\"",
        ]:
            self.assertIn(token, data_index)

    def test_trade_paths_are_explicit_access_options(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "shouldAddTradeOption",
            "Trade/Auction House",
            "Trade enchant service",
            "is_trade_option = true",
            "isBindOnPickup",
            "hasCrafted and not isBindOnPickup(item)",
        ]:
            self.assertIn(token, data_index)

    def test_token_turnin_raid_zones_feed_zone_filters(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "getSourceZones",
            "addZonesFromSource",
            'source.type == "token_turnin"',
            "source.token_sources",
            "includeDropZone",
            "rowMatchesZoneFilter",
            "rowMatchesAnySelectedZone",
            "zones = getSourceZones(item)",
            "zones = use.zones",
        ]:
            self.assertIn(token, data_index)
        self.assertLess(data_index.index("getSourceZones"), data_index.index("includeByFilter"))
        self.assertLess(data_index.index("rowMatchesZoneFilter"), data_index.index("includeByFilter"))

    def test_planner_filters_future_acquisition_phases(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "getAcquisitionPhase",
            "acquisition_phase = acquisitionPhase",
            "acquisitionPhaseIndex = phaseIndex(acquisitionPhase)",
            "acquisition_phase = use.acquisition_phase",
            "group.acquisitionPhaseIndex <= selectedIndex",
        ]:
            self.assertIn(token, data_index)
        self.assertLess(data_index.index("scorePlannerGroup"), data_index.index("group.acquisitionPhaseIndex <= selectedIndex"))

    def test_source_aware_access_status_prefers_ready_options(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "ready_alternate",
            "Ready via alternate source",
            "EvaluateRequirementList",
            "EvaluateAccessOption",
            "GetAccessEvaluation",
            "data and data.access_options",
            "firstReadyEvaluation",
            "local flatEvaluation = self:EvaluateRequirementList",
        ]:
            self.assertIn(token, ui)
        self.assertLess(ui.index("data and data.access_options"), ui.index("local flatEvaluation = self:EvaluateRequirementList"))

    def test_low_confidence_requirements_are_check_only(self):
        ui = self.read_lua("UI.lua")
        self.assertIn('requirement.confidence == "parsed_source_text"', ui)
        self.assertIn('requirement.type == "unknown_text"', ui)
        self.assertIn('elseif requirement.type == "source_access" then', ui)
        self.assertIn('return "check_prereq"', ui)
        evaluate_body = ui.split("function UI:EvaluateRequirement", 1)[1].split("function UI:GetAccessStatus", 1)[0]
        self.assertLess(evaluate_body.index("isLowConfidenceRequirement(requirement)"), evaluate_body.index('requirement.type == "reputation"'))

    def test_details_drawer_lists_access_paths(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "GetAccessBlockingReason",
            "FormatAccessOptionRequirements",
            "FormatAccessOptions",
            "Best access path",
            "Other ways to acquire",
            "Ownership",
            "Prereq",
        ]:
            self.assertIn(token, ui)
        self.assertLess(ui.index('"Ownership"'), ui.index('"Prereq"'))
        self.assertLess(ui.index('"Prereq"'), ui.index('"Best access path"'))
        self.assertLess(ui.index('"Best access path"'), ui.index('"Other ways to acquire"'))

    def test_enhance_spell_rows_are_not_rendered_as_items(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            "entity_type = entityType",
            "row.spell_id = enchant.id",
            "row.item_id = enchant.id",
        ]:
            self.assertIn(token, data_index)

        for token in [
            "function UI:SetSpellButton",
            "button.spellId = spellId",
            "GameTooltip:SetSpellByID",
            'entityType == "spell"',
            "self:SetSpellButton(iconButton",
        ]:
            self.assertIn(token, ui)

        spell_button_index = ui.index("self:SetSpellButton(iconButton")
        item_button_index = ui.index("self:SetItemButton(iconButton, data.item_id")
        self.assertLess(spell_button_index, item_button_index)

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
