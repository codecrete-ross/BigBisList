import re
import shutil
import subprocess
import unittest

from tools.project import ADDON_DIR


class AddonUIStaticTests(unittest.TestCase):
    def read_lua(self, name: str) -> str:
        return (ADDON_DIR / name).read_text(encoding="utf-8")

    def require_tokens(self, source, tokens):
        for token in tokens:
            self.assertTrue(token in source, f"Missing Lua contract: {token}")

    def ui_function(self, name):
        source = self.read_lua("UI.lua")
        marker = f"function UI:{name}("
        self.assertTrue(marker in source, f"Missing UI method: {name}")
        return source.split(marker, 1)[1].split("\nfunction ", 1)[0]

    def test_runtime_lua_files_compile_with_lua51(self):
        luac = shutil.which("luac")
        if not luac:
            self.skipTest("luac is not available")
        lua_files = [
            "Config.lua",
            "Core.lua",
            "Data.lua",
            "DataIndex.lua",
            "Widgets.lua",
            "UI.lua",
            "Tooltip.lua",
            "Minimap.lua",
        ]
        result = subprocess.run(
            [luac, "-p", *(str(ADDON_DIR / name) for name in lua_files)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_user_facing_name_remains_spaced(self):
        self.assertIn('BigBiSList.displayName = "Big BiS List"', self.read_lua("Config.lua"))
        self.assertIn("Big BiS List", self.read_lua("UI.lua"))
        self.assertIn("Big BiS List", self.read_lua("Tooltip.lua"))
        self.assertIn("BigBiSList.displayName", self.read_lua("Minimap.lua"))

    def test_phase_display_labels_use_stable_content_names(self):
        data_index = self.read_lua("DataIndex.lua")
        expected = {
            "PR": "Pre-Raid",
            "T4": "Tier 4",
            "T5": "Tier 5",
            "T6": "Tier 6",
            "ZA": "Zul'Aman",
            "SWP": "Sunwell Plateau",
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
            "BigBiSList.maxLevelingLevel = 69",
            "local DEFAULTS_VERSION = 17",
            "local MAX_LEVELING_LEVEL = BigBiSList.maxLevelingLevel",
            "window = {",
            "width = 1160",
            "inspectorVisible = false",
            "minimap = {",
            "hide = false",
            "minimapPos = 225",
            "tooltips = {",
            "specFilters = {}",
            "specFiltersInitialized = false",
            "selection = {",
            'selectedPhase = "PR"',
            'lastDetectedPhase = "PR"',
            'selectedTab = "Upgrades"',
            'phase = "PR"',
            'mode = DEFAULT_CONTENT_MODE',
            'tab = "Upgrades"',
            "lastTabs = {",
            'endgame = "Upgrades"',
            'leveling = "Gear Guide"',
            "leveling = {",
            "selectedLevel = MAX_LEVELING_LEVEL",
            "lastDetectedLevel = 0",
            "manualLevel = false",
            "filters = {",
            "sourceTypes = {}",
            "zones = {}",
            'cost = "all"',
            "costs = {}",
            'vendor = "all"',
            "vendors = {}",
            'reputation = "all"',
            "reputations = {}",
            "rankGroups = {}",
            'upgradeMode = "actual"',
            "bankCache = {",
            "links = {}",
            "wishlist = {}",
            "ignoredItems = {}",
            "viewState = {",
            "bisList = {",
            "gearGuide = {",
            "myGear = {",
            "enhancements = {",
            "wishlist = {",
            "migrateLegacyDefaults",
            "normalizeTabName",
            "normalizeContentModeState",
            "migrateViewState",
            "migrateMinimapSettings",
            "migrateFacetedFilters",
            "migrateLevelingLevel",
            "ensureTooltipSpecFilters",
            "EnsureTooltipSpecFilters",
            "GetTooltipSpecFilterKey",
            "migrateTooltipSpecFilterDefaults",
            "tooltipSpecFiltersMatchLegacyDruidDefault",
            "enableAllTooltipSpecFilters",
            "previousVersion ~= nil and previousVersion >= 7",
            "tooltips.specFilters[className][specName] = true",
            "function BigBiSList:GetContentMode()",
            "function BigBiSList:SetContentMode(mode)",
            "function BigBiSList:GetEffectivePhaseKey(selection)",
            "function BigBiSList:GetViewState(viewName)",
            "function BigBiSList:IsInspectorVisible()",
            "function BigBiSList:SetInspectorVisible(visible)",
            "migrateWorkspaceFilters",
            "state.filters = copyFilterValues",
        ]:
            self.assertIn(token, config)
        self.assertNotIn("local selectedClass = db.char and db.char.selection and db.char.selection.class", config)
        self.assertNotIn("firstInitialization and className == selectedClass or false", config)

    def test_current_phase_detection_preserves_valid_selections(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")

        for token in [
            "function BigBiSList:GetCurrentPhaseKey(nowEpoch)",
            "currentServerTimestamp",
            "pcall(GetServerTime)",
            "pcall(time)",
            "getPhaseStartEpoch",
            "starts_at_epoch",
            "currentPhase = phaseKey",
        ]:
            self.assertIn(token, data_index)

        validate_body = ui.split("function UI:ValidateSelection", 1)[1].split("function UI:BuildOwnedItems", 1)[0]
        for token in [
            "local detectedPhase = BigBiSList.GetCurrentPhaseKey and BigBiSList:GetCurrentPhaseKey() or nil",
            "not phaseExists(phaseKey)",
            "phaseKey = detectedPhase",
            "char.lastDetectedPhase = detectedPhase",
        ]:
            self.assertIn(token, validate_body)
        self.assertNotIn("phaseKey == char.lastDetectedPhase", validate_body)

    def test_player_selection_detection_is_load_time_context(self):
        config = self.read_lua("Config.lua")
        for token in [
            'local DEFAULT_SELECTED_CLASS = "Druid"',
            'local DEFAULT_SELECTED_SPEC = "Feral dps"',
            "local PLAYER_CLASS_NAMES = {",
            "DRUID = DEFAULT_SELECTED_CLASS",
            'HUNTER = "Hunter"',
            "function BigBiSList:DetectPlayerClass()",
            'pcall(UnitClassBase, "player")',
            'pcall(UnitClass, "player")',
            "function BigBiSList:DetectPlayerSpec(className)",
            "pcall(GetNumTalentTabs)",
            "pcall(GetTalentTabInfo, tabIndex)",
            "specNameForClass(className, selectedTabName)",
            "local SPEC_NAME_ALIASES = {",
            '["feral combat"] = DEFAULT_SELECTED_SPEC',
            "function BigBiSList:GetDetectedPlayerSelection()",
            "local detectedSpec = self:DetectPlayerSpec(className)",
            "firstSpecNameForClass(className)",
            "specDetected = detectedSpec ~= nil",
            "local function syncSelectionAliases(char)",
            "local function applyDetectedPlayerSelection(char)",
            "BigBiSList.classSpecAutoSelectionActive == false",
            "char.selection.class = detected.class",
            "char.selection.spec = detected.spec",
            "return changed",
            "function BigBiSList:MarkClassSpecSelectionManual()",
            "self.classSpecAutoSelectionActive = false",
            "function BigBiSList:ResetClassSpecAutoSelection()",
            "self.classSpecAutoSelectionActive = true",
            "function BigBiSList:ApplyDetectedPlayerSelection()",
            "applyDetectedPlayerSelection(BigBiSListCharDB)",
            "syncSelectionAliases(BigBiSListCharDB)",
            "BigBiSListCharDB.manualClassSpecSelection = nil",
            "selectedClass = DEFAULT_SELECTED_CLASS",
            "selectedSpec = DEFAULT_SELECTED_SPEC",
            "class = DEFAULT_SELECTED_CLASS",
            "spec = DEFAULT_SELECTED_SPEC",
        ]:
            self.assertIn(token, config)
        self.assertNotIn("selectionUsesBuiltInDefault", config)
        self.assertNotIn("hasSavedClassSpecSelection", config)
        self.assertNotIn("hadSavedClassSpecSelection", config)

        defaults_body = config.split("BigBiSList.defaults = {", 1)[1].split("local function applyDefaults", 1)[0]
        self.assertNotIn("manualClassSpecSelection", defaults_body)

        ensure_body = config.split("function BigBiSList:EnsureDatabase()", 1)[1].split("return BigBiSListDB", 1)[0]
        self.assertIn("syncSelectionAliases(BigBiSListCharDB)", ensure_body)
        self.assertIn("BigBiSListCharDB.manualClassSpecSelection = nil", ensure_body)
        self.assertNotIn("applyDetectedPlayerSelection", ensure_body)

        apply_body = config.split("function BigBiSList:ApplyDetectedPlayerSelection()", 1)[1].split("function BigBiSList:ApplyDetectedDefaultSelection", 1)[0]
        self.assertIn("self:EnsureDatabase()", apply_body)
        self.assertIn("applyDetectedPlayerSelection(BigBiSListCharDB)", apply_body)
        self.assertIn("syncSelectionAliases(BigBiSListCharDB)", apply_body)
        self.assertIn("return changed", apply_body)
        self.assertIn("return self:ApplyDetectedPlayerSelection()", config)

    def test_manual_class_spec_dropdown_selection_stops_auto_detection(self):
        ui = self.read_lua("UI.lua")
        set_class_body = ui.split("function UI:SetClass(className)", 1)[1].split("function UI:SetSpec", 1)[0]
        set_spec_body = ui.split("function UI:SetSpec(specName)", 1)[1].split("function UI:SetPhase", 1)[0]

        self.assertIn("BigBiSList:MarkClassSpecSelectionManual()", set_class_body)
        self.assertIn("BigBiSList:MarkClassSpecSelectionManual()", set_spec_body)
        self.assertLess(set_class_body.index("BigBiSList:MarkClassSpecSelectionManual()"), set_class_body.index("BigBiSList:SetSelection"))
        self.assertLess(set_spec_body.index("BigBiSList:MarkClassSpecSelectionManual()"), set_spec_body.index("BigBiSList:SetSelection"))

    def test_context_header_exposes_mode_character_and_live_phase_controls(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "function UI:CreateContextBar(frame)",
            'widgets:CreateTextButton(bar, "Endgame"',
            'widgets:CreateTextButton(bar, "Leveling"',
            "BigBiSListClassDropdown",
            "BigBiSListSpecDropdown",
            "BigBiSListPhaseDropdown",
            'widgets:CreateTextButton(bar, "Current Spec"',
            "function UI:UseMyCharacter()",
            "BigBiSList:ResetClassSpecAutoSelection()",
            "BigBiSList:ApplyDetectedPlayerSelection()",
            "phase == BigBiSList:GetCurrentPhaseKey()",
        ]:
            self.assertIn(token, ui)
        phase_bar = self.ui_function("CreatePhaseBar")
        self.require_tokens(phase_bar, ["Live", "BigBiSList:GetPhaseOrder()", "self:SetPhase(value)"])
        self.assertNotIn('CreateTextButton(phaseBar, phaseLabel', phase_bar)
        context_layout = self.ui_function("LayoutContextControls")
        self.assertIn("{ self.classDropdown, self.specDropdown, self.useCharacterButton }", context_layout)
        header = self.ui_function("CreateHeader")
        self.require_tokens(header, ['CreateUtilityButton(bar, "settings"', "self:OpenSettings()", "self:ReturnFromSettings()"])

    def test_leveling_level_defaults_to_player_level_and_persists_manual_controls(self):
        config = self.read_lua("Config.lua")
        ui = self.read_lua("UI.lua")
        core = self.read_lua("Core.lua")

        for token in [
            "function BigBiSList:GetDetectedPlayerLevel()",
            'pcall(UnitLevel, "player")',
            "function BigBiSList:ApplyDetectedPlayerLevel()",
            "char.leveling.manualLevel ~= true",
            "function BigBiSList:GetSelectedLevelingLevel()",
            "function BigBiSList:SetSelectedLevelingLevel(level, manual)",
            "return MAX_LEVELING_LEVEL",
            "migrateLevelingLevel(BigBiSListCharDB)",
            "BigBiSListCharDB.leveling.manualLevel = true",
        ]:
            self.assertIn(token, config)

        self.require_tokens(ui, [
            'local LEVELING_PHASE_KEY = BigBiSList.levelingPhaseKey or "LEVELING"',
            'local MAX_LEVELING_LEVEL = BigBiSList.maxLevelingLevel or 69',
            'self.levelInput = CreateFrame("EditBox"',
            'CreateUtilityButton(level, "chevronLeft"',
            'CreateUtilityButton(level, "chevronRight"',
            'self.levelInput:SetNumeric(true)',
            'self.levelInput:SetMaxLetters(2)',
            'self.levelInput:SetScript("OnEnterPressed"',
            'self.levelInput:SetScript("OnEscapePressed"',
            'self.levelInput:SetScript("OnEditFocusLost"',
            'self.levelInput:SetText(tostring(level))',
            'BigBiSList:SetSelectedLevelingLevel(level, true)',
        ])
        level_setter = config.split("function BigBiSList:SetSelectedLevelingLevel(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("clampLevel(level)", level_setter)
        level_input = self.ui_function("CreatePhaseBar")
        focus_commit = level_input.split('self.levelInput:SetScript("OnEditFocusLost"', 1)[1].split("end)", 1)[0]
        self.require_tokens(focus_commit, ['tonumber(input:GetText())', 'self:SetLevelingLevel(value)'])

        self.assertNotIn("BigBiSListLevelSlider", ui)
        self.assertNotIn("CreateFrame(\"Slider\"", ui)

        self.assertIn('frame:RegisterEvent("PLAYER_LEVEL_UP")', core)
        self.assertIn("BigBiSList:ApplyDetectedPlayerLevel()", core)

    def test_core_retries_player_selection_detection_after_login(self):
        core = self.read_lua("Core.lua")
        for token in [
            "local function retryDetectedPlayerSelection()",
            "not addonInitialized",
            "BigBiSList.ApplyDetectedPlayerSelection",
            "BigBiSList:ApplyDetectedPlayerSelection()",
            "BigBiSList:RefreshUI()",
            'frame:RegisterEvent("PLAYER_LOGIN")',
            'frame:RegisterEvent("PLAYER_ENTERING_WORLD")',
            'frame:RegisterEvent("PLAYER_TALENT_UPDATE")',
            'frame:RegisterEvent("CHARACTER_POINTS_CHANGED")',
            'or event == "PLAYER_TALENT_UPDATE"',
            'or event == "CHARACTER_POINTS_CHANGED"',
            "BigBiSList:ResetClassSpecAutoSelection()",
            "addonInitialized = true",
            "retryDetectedPlayerSelection()",
        ]:
            self.assertIn(token, core)

    def test_public_ui_methods_exist(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        for method in ["OpenMainFrame", "CloseMainFrame", "ToggleMainFrame"]:
            self.assertIn(f"function BigBiSList:{method}()", ui)
        self.assertIn("function BigBiSList:RefreshUI(", ui)
        for method in ["GetDataIndex", "GetPhaseRows", "GetLevelingRows", "GetPlannerRows", "GetAvailableFilterSourceTypes", "GetAvailableFilterCosts", "GetAvailableFilterVendors", "GetFilterAvailabilitySnapshot", "GetItemMeta", "GetRowAccessOptions", "GetDisplaySlotFilters", "GetItemBestUseForSpec", "GetItemBestLevelingUseForSpec", "GetItemNextLevelingUseForSpec", "GetLevelingTooltipMatches", "GetGroupedLevelingTooltipMatches", "GetEquippedGearRows", "GetWishlistExpansionSummary", "GetWishlistRows", "GetMatchingRowAccessOption", "GetRowAcquisitionDisplay", "GetEnhancementRows"]:
            self.assertIn(f"function BigBiSList:{method}", data_index)
        config = self.read_lua("Config.lua")
        for method in ["SetSelection", "GetContentMode", "SetContentMode", "GetEffectivePhaseKey", "GetViewState", "IsInspectorVisible", "SetInspectorVisible"]:
            self.assertIn(f"function BigBiSList:{method}", config)

    def test_leveling_is_a_content_mode_with_an_internal_data_phase(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            'local LEVELING_PHASE_KEY = "LEVELING"',
            "local maxLevel = BigBiSList.maxLevelingLevel or 69",
            "BigBiSList.levelingPhaseKey = LEVELING_PHASE_KEY",
            "function BigBiSList:GetLevelingRows",
            "local function clampLevelingLevel(level)",
            "index.levelingGearRefsByClassSpec",
            "index.levelingGearRefsByItemId",
            "return levelMin <= selectedLevel and selectedLevel <= levelMax",
            'phaseKey == LEVELING_PHASE_KEY',
        ]:
            self.assertIn(token, data_index)

        for token in [
            "function UI:RenderLevelingTab()",
            "BigBiSList:GetLevelingRows(selection.class, selection.spec, level, filters)",
            'local ENDGAME_TAB_NAMES = { "Upgrades", "By Slot", "Equipped", "Enhance", "Wishlist" }',
            'local LEVELING_TAB_NAMES = { "Gear Guide", "Equipped", "Wishlist" }',
            "function UI:IsLevelingMode()",
            "function UI:GetEffectivePhaseKey()",
            "function UI:GetActiveTabNames()",
            "function UI:SetContentMode(mode)",
            'self:SetContentMode("endgame")',
            'self:SetContentMode("leveling")',
            'elseif tabName == "Gear Guide" then',
            "self:RenderLevelingTab()",
            "self.levelControlContainer:SetShown(leveling)",
            "button:Hide()",
        ]:
            self.assertIn(token, ui)

    def test_wishlist_uses_expansion_wide_data_rows(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        body = ui.split("function UI:RenderWishlistTab()", 1)[1].split("function UI:CreateSettingToggle", 1)[0]
        for token in [
            "BigBiSList:GetWishlistRows(wishlist, selection.class, selection.spec, selection.phase, filters)",
            'self:RenderGroupedRows(rows, "wishlist", self:GetViewState().groupBy or "none", "Wishlist")',
        ]:
            self.assertIn(token, body)
        self.assertIn("function UI:GetWishlistExpansionText(data)", ui)
        for token in [
            "function BigBiSList:GetWishlistExpansionSummary",
            "relevant_spec_rankings",
            "selected_spec_ranking",
            "phase_cells",
            "not_ranked_label",
            "Not ranked for ",
            "function BigBiSList:GetWishlistRows",
            "matched_access_option",
            "source_live_future",
        ]:
            self.assertIn(token, data_index)
        self.assertNotIn("GetItemNextLevelingUseForSpec", body)

    def test_status_summary_reports_leveling_recommendation_counts(self):
        core = self.read_lua("Core.lua")
        for token in [
            "local levelingGearCount = data.meta and data.meta.leveling_gear_count or #(data.leveling_gear or {})",
            "local levelingRecommendationCount = data.meta and data.meta.leveling_recommendation_count or #(data.leveling_recommendations or {})",
            '"%d classes, %d phases, %d items, %d slot lists, %d guide leveling rows, %d computed leveling recommendations"',
        ]:
            self.assertIn(token, core)

    def test_ensure_database_does_not_trigger_full_indexing(self):
        config = self.read_lua("Config.lua")
        ensure_body = config.split("function BigBiSList:EnsureDatabase()", 1)[1].split("function", 1)[0]
        self.assertNotIn("GetDataIndex", ensure_body)

        core = self.read_lua("Core.lua")
        addon_loaded_body = core.split('frame:SetScript("OnEvent"', 1)[1].split("SLASH_BIGBISLIST1", 1)[0]
        self.assertIn("BigBiSList:EnsureDatabase()", addon_loaded_body)
        self.assertNotIn("GetDataIndex", addon_loaded_body)

    def test_plain_lua_timing_smoke_output_exists(self):
        core = self.read_lua("Core.lua")
        for token in [
            "function BigBiSList:RunTimingSmokeTest(selection)",
            "clockMilliseconds",
            "debugprofilestop",
            "os.clock",
            'timeSmokeStep("GetDataIndex"',
            'timeSmokeStep("planner rows"',
            'timeSmokeStep("phase rows"',
            'timeSmokeStep("filter availability"',
            'timeSmokeStep("repeated cached calls"',
        ]:
            self.assertIn(token, core)

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

        self.assertIn('local ENDGAME_TAB_NAMES = { "Upgrades", "By Slot", "Equipped", "Enhance", "Wishlist" }', ui)
        self.assertIn('local LEVELING_TAB_NAMES = { "Gear Guide", "Equipped", "Wishlist" }', ui)
        self.assertIn('Phase = "By Slot"', ui)
        self.assertIn('Gear = "Equipped"', ui)
        self.assertIn('Planner = "Upgrades"', ui)
        self.assertIn('Enhancements = "Enhance"', ui)
        self.assertIn('Enhance = "Enhancements"', ui)
        self.assertIn('["By Slot"] = "BiS List"', ui)
        self.assertIn('Equipped = "My Gear"', ui)
        self.assertIn("function UI:RenderGearTab()", ui)
        self.require_tokens(self.ui_function("RenderGearTab"), ['row.column == "right"', 'columnIndex=column', 'mode="gear"'])
        self.require_tokens(ui, [
            'mode == "gear" and "currentRank"',
            'gear = "Current rank"',
            'self:GetRowSlotDisplay(data)',
            'data.recommendation_summary or data.overlay or "Not ranked"',
            'self:CreateDetailsPhaseMatrix(',
        ])
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
            "getContainerItemLinkSafe",
            "getInventoryItemLinkSafe",
            "enhancementItems = {}",
            "cache.links = {}",
            "table.insert(cache.links, itemLink)",
            'bank = "Bank"',
        ]:
            self.assertIn(token, ui)
        self.assertIn("bankCache = {", config)
        self.assertIn("links = {}", config)
        self.assertIn('elseif filters.ownedState == "bank"', data_index)

    def test_access_badges_are_separate_from_ownership(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "CreateAccessBadge",
            "ACCESS_LABELS",
            "ACCESS_BADGE_LABELS",
            "GetAccessStatus",
            "EvaluateRequirement",
            "BuildAccessState",
            "Requirements",
            "Access",
        ]:
            self.assertIn(token, ui)
        self.assertIn("CreateOwnershipBadge", ui)
        self.assertLess(ui.index("CreateOwnershipBadge"), ui.index("CreateAccessBadge"))
        self.assertIn("requirements = mergedRequirements", data_index)

    def test_views_use_formal_responsive_columns_and_wrapped_text(self):
        ui = self.read_lua("UI.lua")
        widgets = self.read_lua("Widgets.lua")
        data_index = self.read_lua("DataIndex.lua")

        self.require_tokens(ui, [
            "function UI:GetTableViewportWidth(parent, fallback)",
            "function UI:GetViewColumnDefinitions(mode, compact)",
            "function UI:GetTableColumnLayout(width, mode, forceCompact)",
            "TABLE_WIDE_BREAKPOINT",
            "minWidth = minWidth",
            "preferredWidth = preferredWidth",
            "maxWidth = maxWidth",
            "growWeight = growWeight or 0",
            "growColumnWidths",
            "header.columnLayout = layout",
            "row.columnLayout = layout",
            "CreateListColumnHeader",
            'columnDefinition("item", mode == "enhance" and "Enhancement" or "Item"',
            'columnDefinition(valueKey, valueLabel',
            'columnDefinition("acquisition", "Source"',
            'fixedColumn("owned", mode == "enhance" and "Applied / owned" or "Owned"',
            'fixedColumn("action", "", 28)',
            "GetRowOwnershipState",
            "GetRowRecommendationText",
            "row:SetHeight(rowHeight)",
            "UI:SetViewSort(selfButton.columnKey)",
            'row.actionButton:SetIcon(saved and "starFilled" or "starOutline")',
            'row:SetSelected(',
            'widgets:SetCellText(',
        ])
        self.assertNotIn('columnDefinition("source",', ui)
        self.assertNotIn('columnDefinition("location",', ui)
        for token in [
            "CreateWrappedLabel",
            "CreateStatusBadge",
            "MeasureTextHeight",
            "label:SetWordWrap(true)",
        ]:
            self.assertIn(token, widgets)
        for token in [
            "display_rank_label",
            "display_rank_kind",
            "bisVariantLabel",
            'return variant and ("BiS: " .. variant) or "BiS", "best"',
            'return tostring(use.rank_label) .. " for " .. phaseLabel',
            "recommendation_tier",
            "recommendation_summary",
            "plannerRecommendationTier",
        ]:
            self.assertIn(token, data_index)

        self.assertIn('bindCell("acquisition", source .. (location ~= "" and ((maxLines == 1 and " · " or "\\n") .. location) or "")', ui)
        self.assertNotIn("definition.flex", ui)
        self.assertNotIn("extra / math.max(1, flexCount)", ui)
        header = self.ui_function("CreateListColumnHeader")
        self.require_tokens(header, [
            'button.sortIcon = button:CreateTexture(',
            'button.sortIcon:SetShown(sortKey ~= nil and viewState.sort == sortKey)',
            'BigBiSList.Widgets:SetIcon(button.sortIcon, viewState.sortDirection == "asc" and "sortAscending" or "sortDescending")',
        ])
        self.assertNotIn('" ^"', header)
        self.assertNotIn('" v"', header)

    def test_column_headers_are_kept_visible_while_lists_scroll(self):
        ui = self.read_lua("UI.lua")
        self.assertIn("function UI:SetStickyHeaderMode(mode)", ui)
        sticky_body = ui.split("function UI:SetStickyHeaderMode(mode)", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("self.contentHeaderHost", sticky_body)
        self.assertIn("CreateListColumnHeader", sticky_body)
        self.assertIn('self.contentScroll:SetPoint("TOPLEFT", self.contentHeaderHost, "BOTTOMLEFT"', sticky_body)
        section_body = ui.split("function UI:AddListSection", 1)[1].split("function UI:AddListRow", 1)[0]
        self.assertIn("model.columnMode", section_body)
        self.assertNotIn('kind = "columns"', section_body)
        viewport_body = ui.split("function UI:UpdateVirtualList", 1)[1].split("function UI:RenderEmpty", 1)[0]
        self.assertNotIn('entry.kind == "columns"', viewport_body)
        self.assertNotIn('entry.kind == "filters"', viewport_body)

    def test_active_filter_chips_are_fixed_above_the_grid(self):
        ui = self.read_lua("UI.lua")
        self.assertIn("function UI:RefreshFixedActiveFilterBar()", ui)
        self.assertIn("function UI:GetActiveFilterChipLayout(parent, chips)", ui)
        height_body = ui.split("function UI:ActiveFilterBarHeight", 1)[1].split("function UI:", 1)[0]
        render_body = ui.split("function UI:CreateActiveFilterBar", 1)[1].split("function UI:", 1)[0]
        self.assertIn("GetActiveFilterChipLayout", height_body)
        self.assertIn("GetActiveFilterChipLayout", render_body)
        layout_body = ui.split("function UI:ApplyBodyLayout()", 1)[1].split("function UI:CreateStatusBar", 1)[0]
        self.assertIn("self:RefreshFixedActiveFilterBar()", layout_body)
        self.assertIn('self.fixedActiveFilterBar:SetPoint("TOPLEFT"', layout_body)
        self.require_tokens(layout_body, [
            'local top = supportsFilters and (activeHeight > 0 and self.fixedActiveFilterBar or self.listToolbar)',
            'self.contentPanel:SetPoint("TOPLEFT", top, supportsFilters and "BOTTOMLEFT" or "TOPLEFT"',
        ])
        for renderer in ["RenderLevelingTab", "RenderPhaseTab", "RenderPlannerTab", "RenderEnhanceTab", "RenderWishlistTab"]:
            body = ui.split(f"function UI:{renderer}", 1)[1].split("function UI:", 1)[0]
            self.assertNotIn("AddActiveFilterBar", body)

    def test_get_badges_use_source_path_labels(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            "ACCESS_SOURCE_BADGE_LABELS",
            "RAID_DROP_ZONES",
            "DUNGEON_DROP_ZONES",
            "accessSourceBadgeLabel",
            "GetAccessBadgeLabel",
            "GetAccessHelpText",
            '"Raid drop"',
            '"Dungeon drop"',
            '"Trade/AH"',
            '"Enchanter"',
            '"Turn in"',
            'needs_profession = "Profession required"',
            'needs_recipe = "Recipe required"',
            'check_prereq = "Requirements"',
        ]:
            self.assertIn(token, ui)
        self.assertIn("zone = locationArea", data_index)
        self.assertNotIn('"Alt ready"', ui)

    def test_enhancement_access_badges_use_practical_paths(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            "ENHANCEMENT_READY_ACCESS_DETAILS",
            "CRAFTED_MARKET_CONSUMABLE_CATEGORIES",
            "enhancementReadyAccessFromOptions",
            "enhancementReadyAccessFromSummary",
            "consumableReadyAccessOverride",
            "applyEnhancementReadyAccess",
            '["Craft/AH"] = "Craft yourself or buy on the Auction House."',
            '["Drop/AH"] = "Farm the drop or buy on the Auction House."',
            '["Trade/AH"] = "Buy, trade, or check the Auction House."',
            "flask = true",
            "battle_elixir = true",
            "guardian_elixir = true",
            "weapon_oil = true",
            'applyEnhancementReadyAccess(row, accessOptions, row.source_summary, "Craft/AH")',
            'applyEnhancementReadyAccess(row, nil, nil, "Enchanter")',
            'applyEnhancementReadyAccess(row, accessOptions, sourceSummary, "Trade/AH", consumableReadyAccessOverride',
            "preferredLabel",
            "ready_access_label = label",
            "ready_access_detail = ENHANCEMENT_READY_ACCESS_DETAILS[label]",
        ]:
            self.assertIn(token, data_index)

        for token in [
            "data.ready_access_label",
            "data.ready_access_detail",
            "GetAccessHelpText(optionEvaluation, data)",
            "GetAccessHelpText(optionEvaluation, accessData)",
        ]:
            self.assertIn(token, ui)

        get_badge_body = ui.split("function UI:GetAccessBadgeLabel", 1)[1].split("function UI:GetAccessHelpText", 1)[0]
        self.assertLess(get_badge_body.index('state == "ready"'), get_badge_body.index("data.ready_access_label"))

    def test_enhancement_grid_has_view_specific_columns(self):
        ui = self.read_lua("UI.lua")

        for token in [
            'columnDefinition("item", mode == "enhance" and "Enhancement" or "Item"',
            'columnDefinition(valueKey, valueLabel',
            'fixedColumn("owned", mode == "enhance" and "Applied / owned" or "Owned"',
            'columnDefinition("acquisition", "Source"',
            'self:AddListSection(model, section.title, "enhance")',
            'self:AddListRow(model, rowData, "enhance")',
        ]:
            self.assertIn(token, ui)

    def test_source_aware_access_options_are_indexed(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "buildAccessOptions",
            "splitRequirements",
            "sourceMatchesRequirement",
            "source.requirements",
            "function BigBiSList:GetRowAccessOptions(row)",
            "buildRowAccessOptions",
            "zone = locationArea",
            "source_filter_key = filterKey",
            "source_filter_keys = meta.source_filter_keys",
            "source_summary = sourceOptionSummary",
            "zones = sourceOptionZones(source)",
            "rowHasAccessOptionMatchingFilterContext",
            "gemSourcesById",
            "enchantSourcesByKey",
            "enchantEffectsByKey",
            "data.enchant_effects",
            "enhancementSourceKey(entityType, enchant.id)",
            "forceSourceScopedEquip = entityType == \"spell\"",
        ]:
            self.assertIn(token, data_index)

    def test_planner_phase_access_options_are_lazy(self):
        data_index = self.read_lua("DataIndex.lua")
        build_use_body = data_index.split("local function buildUse", 1)[1].split("local function rowHasZone", 1)[0]

        self.assertIn("_access_context", build_use_body)
        self.assertIn("getItemMetaFromIndex", build_use_body)
        self.assertNotIn("buildAccessOptions", build_use_body)
        self.assertNotIn("access_options =", build_use_body)
        self.assertIn("rowAccessCache", data_index)
        self.assertIn("function BigBiSList:GetRowAccessOptions(row)", data_index)

    def test_item_metadata_cache_feeds_lightweight_rows(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "ITEM_META_CACHE_LIMIT",
            "itemMetaCache",
            "itemFallbackRecordsById",
            "itemFallbackCache",
            "function BigBiSList:GetItemMeta(itemId)",
            "buildItemMeta",
            "itemReputations",
            "rowReputationsWithMeta",
            "getItemPhaseMeta",
        ]:
            self.assertIn(token, data_index)

    def test_item_button_uses_row_quality_before_client_cache(self):
        ui = self.read_lua("UI.lua")

        self.require_tokens(self.ui_function("CreateDataRow"), [
            "self:SetItemButton(icon, data.item_id, name, data.name, data.quality or (data.item and data.item.quality), data, mode)",
        ])
        self.assertIn("local titleQualityItem = item or (detailData and detailData.quality and { quality = detailData.quality }) or nil", ui)
        self.assertIn("local r, g, b = itemQualityColor(titleQualityItem)", ui)

    def test_filter_availability_uses_one_snapshot(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")

        snapshot_body = data_index.split("function BigBiSList:GetFilterAvailabilitySnapshot", 1)[1].split("function BigBiSList:GetAvailableFilterSourceTypes", 1)[0]
        self.assertEqual(snapshot_body.count("collectAvailabilityRows"), 1)
        self.assertIn("cloneFiltersForAvailabilityRows", snapshot_body)
        self.assertIn("addSourceTypeFromRow", snapshot_body)
        self.assertIn("addZonesFromRow", snapshot_body)
        self.assertIn("addReputationsFromRow", snapshot_body)

        collect_body = data_index.split("local function collectAvailabilityRows", 1)[1].split("function BigBiSList:GetFilterAvailabilitySnapshot", 1)[0]
        for token in [
            'if tabName == "Wishlist" then',
            "addon:GetWishlistRows(",
            'elseif tabName == "Enhance" or tabName == "Enhancements" then',
            "addon:GetEnhancementRows(className, specName, phaseKey, filters)",
            "addon:GetLevelingRows(className, specName, filters and filters.level, filters)",
            "addon:GetPlannerRows(className, specName, phaseKey, filters)",
            "addon:GetPhaseRows(className, specName, phaseKey, filters)",
        ]:
            self.assertIn(token, collect_body)

        self.assertIn("function UI:GetFilterAvailabilitySnapshot()", ui)
        self.assertIn("self.currentAvailabilitySnapshot", ui)
        self.assertIn("BigBiSList:GetFilterAvailabilitySnapshot", ui)
        build_filter_body = ui.split("function UI:BuildFilterPayload()", 1)[1].split("function UI:SaveWindow", 1)[0]
        self.assertNotIn("GetPlannerRows", build_filter_body)
        self.assertNotIn("GetPhaseRows", build_filter_body)
        self.assertNotIn("currentFilterPayload.wishlistSort", build_filter_body)
        self.assertNotIn("currentFilterPayload.sortDirection", build_filter_body)

    def test_first_open_schedules_one_refresh_after_frame_creation(self):
        ui = self.read_lua("UI.lua")
        create_body = ui.split("function UI:CreateMainFrame()", 1)[1].split("function UI:Open()", 1)[0]
        open_body = ui.split("function UI:Open()", 1)[1].split("function UI:Close()", 1)[0]

        self.assertNotIn("self:Refresh()", create_body)
        self.assertIn('self:ScheduleRefresh(nil, "open")', open_body)
        self.assertEqual(open_body.count("self:ScheduleRefresh("), 1)

    def test_ui_refreshes_are_invalidated_scheduled_and_virtualized(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "function UI:Invalidate(domains, reason)",
            "self.dirtyDomains",
            "function UI:ScheduleLayoutRefresh",
            "function UI:ScheduleRefresh(",
            "C_Timer.After",
            "local SEARCH_DEBOUNCE_SECONDS = 0.12",
            "self:ScheduleRefresh(SEARCH_DEBOUNCE_SECONDS",
            "function UI:RenderListModel(model)",
            "function UI:UpdateVirtualList(force)",
            "function UI:ReleaseRenderFrames()",
            "self.renderPools",
            "self:AddListRow(model",
            "self:RenderListModel(model)",
        ]:
            self.assertIn(token, ui)
        self.assertRegex(ui, r"(?i)overscan[a-z_]*\s*=\s*120")

        render_body = ui.split("function UI:RenderListModel(model)", 1)[1].split("function UI:UpdateVirtualList", 1)[0]
        self.assertIn("self:UpdateVirtualList(true)", render_body)
        self.assertNotIn("for _, entry in ipairs(model.entries) do", render_body)
        self.assertNotIn("self:CreateDataRow(", render_body)

        update_body = ui.split("function UI:UpdateVirtualList", 1)[1].split("function UI:RenderEmpty", 1)[0]
        self.assertIn("for _, entry in ipairs", update_body)
        self.assertIn("self:CreateDataRow(", update_body)
        self.assertIn("LIST_OVERSCAN_PIXELS", update_body)
        self.assertIn("scroll:GetVerticalScroll()", update_body)
        self.assertIn("scroll:GetHeight()", update_body)

        create_body = ui.split("function UI:CreateBody(frame)", 1)[1].split("function UI:CreateStatusBar", 1)[0]
        self.assertIn('HookScript("OnVerticalScroll"', create_body)
        vertical_scroll_body = create_body.split('HookScript("OnVerticalScroll"', 1)[1].split("end)", 1)[0]
        self.assertIn("self:UpdateVirtualList", vertical_scroll_body)
        self.assertNotIn("ScheduleRefresh", vertical_scroll_body)

        size_changed_body = create_body.split('self.contentScroll:SetScript("OnSizeChanged"', 1)[1].split("end)", 1)[0]
        self.assertIn("self:ScheduleLayoutRefresh", size_changed_body)
        self.assertIn("self:UpdateVirtualList", size_changed_body)
        self.assertNotIn("self:ScheduleRefresh", size_changed_body)
        self.assertRegex(size_changed_body, r"width\s*[-~=<>]+\s*self\.[A-Za-z0-9_]*[Ww]idth|self\.[A-Za-z0-9_]*[Ww]idth\s*[-~=<>]+\s*width")

        for setter in ["SetClass", "SetSpec", "SetPhase", "SetTab", "SetFilter", "ToggleSlot", "ClearFilters"]:
            body = ui.split(f"function UI:{setter}", 1)[1].split("function UI:", 1)[0]
            self.assertTrue(
                "self:Invalidate(" in body or "self:ClearTransientCaches(" in body,
                f"{setter} must invalidate cached state",
            )
            self.assertIn("self:ScheduleRefresh(", body)

    def test_ui_refresh_guards_layout_and_reuses_managed_row_widgets(self):
        ui = self.read_lua("UI.lua")

        refresh_body = ui.split("function UI:Refresh(", 1)[1].split("function UI:CreateHeader", 1)[0]
        self.assertIn("self.refreshInProgress", refresh_body)
        self.assertRegex(refresh_body, r"if\s+self\.refreshInProgress\s+then")
        self.assertRegex(
            refresh_body,
            r"if\s+self:IsInspectorVisible\(\)[^\n]*then\s*\n\s*self:RefreshDetails",
        )

        sticky_body = ui.split("function UI:SetStickyHeaderMode(mode)", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("geometryChanged", sticky_body)
        self.assertIn("if geometryChanged then", sticky_body)

        body_layout = ui.split("function UI:ApplyBodyLayout()", 1)[1].split("function UI:CreateStatusBar", 1)[0]
        self.assertRegex(body_layout, r"self\.[A-Za-z0-9_]*[Ll]ayout[A-Za-z0-9_]*")
        self.assertRegex(body_layout, r"if\s+self\.[A-Za-z0-9_]*[Ll]ayout[A-Za-z0-9_]*\s*~?=")

        row_body = ui.split("function UI:CreateDataRow", 1)[1].split("function UI:CreateVirtualSectionHeader", 1)[0]
        self.assertNotIn("ClearChildren(row)", row_body)
        self.assertRegex(
            row_body,
            r"self:(?:Ensure|Acquire|Bind|Initialize)[A-Za-z0-9_]*Row|row\.[A-Za-z0-9_]*(?:widgets|managed|cells)",
        )

    def test_item_loads_are_deduped_and_reused_rows_reject_stale_callbacks(self):
        ui = self.read_lua("UI.lua")
        item_body = ui.split("local function applyItemPresentation", 1)[1].split("function UI:SetSpellButton", 1)[0]

        self.assertRegex(ui, r"self\.[A-Za-z0-9_]*[Ii]tem[Ll]oad[A-Za-z0-9_]*\s*=\s*self\.[A-Za-z0-9_]*[Ii]tem[Ll]oad[A-Za-z0-9_]*\s+or\s+\{")
        self.assertRegex(item_body, r"[Bb]ind(?:Token|Generation)|[Rr]ow(?:Token|Generation)")
        self.assertRegex(item_body, r"button\.[A-Za-z0-9_]*(?:[Tt]oken|[Gg]eneration)\s*~=")
        self.assertIn("Item:CreateFromItemID", item_body)

    def test_ui_performance_smoke_reports_refresh_and_realization_counts(self):
        core = self.read_lua("Core.lua")
        ui = self.read_lua("UI.lua")

        self.assertIn('if input == "perf" then', core)
        self.assertIn("ui:RunPerformanceSmoke()", core)
        self.assertIn("function UI:RunPerformanceSmoke()", ui)
        smoke_body = ui.split("function UI:RunPerformanceSmoke()", 1)[1].split("\nfunction ", 1)[0]
        for token in [
            "executedRefreshes",
            "layoutPasses",
            "modelRows",
            "realizedEntries",
            "widgetsCreated",
            "itemLoadRequests",
        ]:
            self.assertIn(token, smoke_body)

    def test_enhance_consumable_alternatives_are_grouped(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")

        for token in [
            "CONSUMABLE_CATEGORY_LABELS",
            "consumable.relationship == \"or\"",
            "consumableCanGroupAlternatives",
            "item_ids = itemIds",
            'enhancement_kind = "consumable"',
            "buildConsumableAccessOptions",
            "consumableDisplayName",
            "consumableDetailLabel",
            "consumableRecommendationSummary",
            "Choose one",
            "Bring for raid",
        ]:
            self.assertIn(token, data_index)
        self.assertLess(
            data_index.index("consumableCanGroupAlternatives"),
            data_index.index("for itemIndex, itemId in ipairs(itemIds)"),
        )

        self.assertIn("function UI:GetOwnershipState(itemId, itemIds)", ui)
        self.assertIn("for _, candidateItemId in ipairs(itemIds or {})", ui)
        self.assertIn("self:GetOwnershipState(data.item_id, data.item_ids)", ui)

    def test_enhance_tracks_applied_gems_and_enchants_from_item_links(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        data_lua = self.read_lua("Data.lua")

        for token in [
            "parseItemLinkEnhancements",
            "getContainerItemLinkSafe",
            "getInventoryItemLinkSafe",
            "enchant_id = tonumber(fields[2])",
            "gem_ids = {}",
            "enhancementEffectIdsContain",
            "gemIdsContain",
            "slotMatchesEnhancement",
            "GetEnhancementAppliedMatches",
            "GetEnhancementAppliedSummary",
            'title = "Applied"',
            '"Applied: " .. appliedSummary.label',
            'fixedColumn("owned", mode == "enhance" and "Applied / owned" or "Owned"',
            "table.insert(cache.links, itemLink)",
        ]:
            self.assertIn(token, ui)

        for token in [
            "enchantEffectsByKey",
            "data.enchant_effects",
            'enhancement_kind = "gem"',
            "gem_item_id = gem.id",
            'enhancement_kind = "enchant"',
            "match_slot = enchant.slot",
            "enchant_effect_ids = effectData and effectData.effect_ids or {}",
            "enchant_effect_source_spell_id",
        ]:
            self.assertIn(token, data_index)

        self.assertIn('["enchant_effects"] = {', data_lua)

    def test_enhancement_rows_use_actionable_copy(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")

        for token in [
            "GEM_SOCKET_LABELS",
            "gemDetailLabel",
            "enchantDetailLabel",
            "enchantRecommendationSummary",
            'gem.context == "budget" and "Budget alternative" or "Socket this gem"',
            "recommendation_summary = enchantRecommendationSummary(enchant)",
            "recommendation_summary = consumableRecommendationSummary",
            'ownership_state = "service"',
            'ownership_label = "No item"',
            "find an enchanter",
        ]:
            self.assertIn(token, data_index)
        self.assertIn('service = "No item"', ui)
        self.assertIn("No gems, enchants, or consumables found for this class, spec, and phase.", ui)

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
        ui = self.read_lua("UI.lua")
        for token in [
            "getSourceZones",
            "addZonesFromSource",
            'source.type == "token_turnin"',
            "source.token_sources",
            "includeDropZone",
            "rowMatchesZoneFilter",
            "rowMatchesAnySelectedZone",
            "zones = getSourceZones(acquisitionItem)",
            "zones = use.zones",
            "optionMatchesSourceContext",
            "optionMatchesSourceFilter",
            "optionMatchesZoneFilter",
            "accessOptionIsPhaseAvailable",
            "sourceOptionFilterKey",
        ]:
            self.assertIn(token, data_index)
        self.assertLess(data_index.index("getSourceZones"), data_index.index("includeByFilter"))
        self.assertLess(data_index.index("rowMatchesZoneFilter"), data_index.index("includeByFilter"))
        self.assertIn("optionMatchesActiveSourceContext", ui)
        self.assertIn("context_matched = contextMatched", ui)
        self.assertIn("function UI:GetRowAcquisitionDisplay(data)", ui)
        self.assertIn("if data and data.acquisition_display then", ui)
        self.assertIn("display.source_label", ui)
        self.assertIn("display.location_label", ui)

    def test_bis_variant_labels_feed_badges_details_and_tooltips(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        tooltip = self.read_lua("Tooltip.lua")

        for token in [
            "bisVariantLabel",
            'return "Threat"',
            'return "Mit"',
            'return "Hit"',
            'return "Raid"',
            'return "Personal"',
            'data.rank_label ~= label',
            '" source recommendation."',
        ]:
            self.assertIn(token, ui)

        for token in [
            "bisVariantLabel",
            'return "Threat"',
            'return "Mit"',
            'return "Hit"',
            'return "Raid"',
            'return "Personal"',
            'rankShortLabel(use)',
            "tooltipRankShortLabel",
        ]:
            self.assertIn(token, data_index)

        self.assertIn("match.display_rank_label or match.rank_label", tooltip)

    def test_quest_starter_sources_feed_filters_search_and_tooltip_aliases(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "quest_starter_sources",
            "quest_starter_item_id",
            "data.tooltip_aliases",
            "tooltipUseRefsByItemId",
            "GetTooltipUses",
            'sourceType == "quest"',
            "starterSource in ipairs(source.quest_starter_sources or {})",
            "local uses = self:GetTooltipUses(itemId, selectedPhase)",
        ]:
            self.assertIn(token, data_index)
        self.assertLess(data_index.index("tooltipUseRefsByItemId"), data_index.index("function BigBiSList:GetTooltipMatches"))
        self.assertLess(data_index.index("function BigBiSList:GetTooltipUses"), data_index.index("function BigBiSList:GetTooltipMatches"))

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

    def test_phase_rows_filter_future_acquisition_phases(self):
        data_index = self.read_lua("DataIndex.lua")
        body = data_index.split("function BigBiSList:GetPhaseRows", 1)[1].split("function BigBiSList:GetPlannerRows", 1)[0]
        self.assertIn("local selectedIndex = self:GetAvailabilityPhaseIndex(phaseKey)", body)
        self.assertIn("use.acquisitionPhaseIndex <= selectedIndex", body)
        self.assertLess(body.index("local selectedIndex = self:GetAvailabilityPhaseIndex(phaseKey)"), body.index("use.acquisitionPhaseIndex <= selectedIndex"))

    def test_source_aware_access_status_prefers_ready_options(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "ready_alternate",
            "Available through another source",
            "EvaluateRequirementList",
            "EvaluateAccessOption",
            "GetAccessEvaluation",
            "BigBiSList:GetRowAccessOptions(data)",
            "firstReadyEvaluation",
            "local flatEvaluation = self:EvaluateRequirementList",
        ]:
            self.assertIn(token, ui)
        self.assertLess(ui.index("BigBiSList:GetRowAccessOptions(data)"), ui.index("local flatEvaluation = self:EvaluateRequirementList"))

    def test_typed_parsed_requirements_are_actionable(self):
        ui = self.read_lua("UI.lua")
        self.assertIn("local function isCheckOnlyRequirement", ui)
        self.assertIn('requirement.type == "unknown_text"', ui)
        self.assertIn('elseif requirement.type == "source_access" then', ui)
        self.assertIn('return "check_prereq"', ui)
        self.assertIn("reputations = collectReputationState()", ui)
        self.assertIn("local function splitFactionNames", ui)
        self.assertIn("getFactionStandingRank(requirement.reputation, accessState)", ui)
        self.assertIn("getFactionStandingRank(faction, accessState)", ui)
        self.assertNotIn('requirement.confidence == "parsed_source_text"', ui)
        evaluate_body = ui.split("function UI:EvaluateRequirement", 1)[1].split("function UI:GetAccessStatus", 1)[0]
        self.assertLess(evaluate_body.index('requirement.type == "reputation"'), evaluate_body.index('requirement.type == "source_access"'))

    def test_details_prereq_lines_are_deduped(self):
        ui = self.read_lua("UI.lua")
        self.assertIn("appendRequirementLine", ui)
        self.assertIn("requirementLineKey", ui)
        self.assertIn("local seen = {}", ui)
        self.assertIn("appendRequirementLine(lines, seen, state, requirement)", ui)

    def test_current_gear_pairs_equipment_slots_and_uses_virtualized_cards(self):
        ui = self.read_lua("UI.lua")
        config_body = ui.split("local TABLE_COLUMN_CONFIG =", 1)[1].split("function UI:GetViewColumnDefinitions", 1)[0]
        self.require_tokens(config_body, [
            'mode == "gear" and "currentRank"',
            'gear = "Current rank"',
            'columnDefinition("item",',
            'columnDefinition(valueKey, valueLabel,',
        ])
        self.require_tokens(self.ui_function("CreateDataRow"), [
            'self:GetRowSlotDisplay(data)',
            'row.subText',
            'bindCell("currentRank", data.recommendation_summary or data.overlay or "Not ranked")',
        ])
        self.require_tokens(self.ui_function("RenderGearTab"), [
            'row.column == "right"', 'columnIndex=column', 'model.cursor = top + height',
        ])
        self.require_tokens(self.ui_function("UpdateVirtualList"), ['if entry.columnIndex then', 'self:CreateGearCard('])
        self.assertNotIn("function UI:CreateGearSlotRow", ui)

    def test_leveling_equipped_uses_leveling_recommendations(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            "function BigBiSList:GetItemBestLevelingUseForSpec",
            "self:GetItemBestLevelingUseForSpec(itemId, className, specName, selectedLevel, slot.slots)",
            "overlay = (bestUse.category_label and bestUse.category_label ~= \"Recommended\") and bestUse.category_label or \"Leveling pick\"",
            "level_value_text = bestUse and bestUse.level_value_text or nil",
            "display_rank_kind = itemId and displayRankKind or \"missing\"",
        ]:
            self.assertIn(token, data_index)

        for token in [
            "BigBiSList:GetEquippedGearRows(selection.class, selection.spec, self:GetEffectivePhaseKey(), self.currentOwned, filters.level)",
            'self:CreateGearCard(',
            "row.detailMode = mode",
            "UI:HandleEntityGesture(bound.boundData, bound.boundMode, button, bound)",
            '(detailMode == "leveling" or (detailData and detailData.leveling))',
        ]:
            self.assertIn(token, ui)

    def test_leveling_rows_merge_duplicate_items_after_race_filtering(self):
        data_index = self.read_lua("DataIndex.lua")
        leveling_body = data_index.split("function BigBiSList:GetLevelingRows", 1)[1].split("function BigBiSList:GetPlannerRows", 1)[0]

        for token in [
            "function LEVELING_HELPERS.rowBeats",
            "function LEVELING_HELPERS.addDisplayRow",
            "LEVELING_HELPERS.isExactRace(candidate, selectedRace)",
            "candidate.computed_recommendation",
            "LEVELING_HELPERS.addDisplayRow(grouped, seenBySlot, row, selectedRace, selectedLevel)",
        ]:
            self.assertIn(token, data_index)

        self.assertNotIn("tostring(row.level_min) .. \":\" .. tostring(row.level_max)", leveling_body)
        self.assertNotIn("tostring(row.source_note or \"\")", leveling_body)

    def test_unknown_race_matches_only_generic_leveling_recommendations(self):
        data_index = self.read_lua("DataIndex.lua")
        race_body = data_index.split("local function raceMatches", 1)[1].split("local function levelingRecommendationGroupKey", 1)[0]

        self.assertIn('rowRace == "*" then', race_body)
        self.assertIn('elseif not selectedRace or selectedRace == "" or selectedRace == "*" then', race_body)
        self.assertIn("return false", race_body)

    def test_tooltip_settings_drive_rendering(self):
        tooltip = self.read_lua("Tooltip.lua")
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "itemIdFromTooltipData",
            "itemIdFromTooltip(tooltip, tooltipData)",
            "__bigBisListRenderKey",
            "OnTooltipCleared",
            "shouldAnnotateTooltip",
            "tooltip == GameTooltip or tooltip == ItemRefTooltip",
            "addTooltipInfoSafely",
            "pcall(BigBiSList.AddTooltipInfo",
            "reportTooltipError",
            "pcall(handler, err)",
            "not BigBiSList.DetectPlayerClass",
            "BigBiSList:DetectPlayerClass()",
            "BigBiSList:DetectPlayerSpec(playerClass)",
            "settings.selectedSpecFirst ~= false",
            "settings.compact and 4 or 8",
            "settings.showAllOnAlt and IsAltKeyDown",
            "local specFilters = settings.specFilters",
            "local priorityContext = getTooltipPriorityContext()",
            "local effectivePhaseKey = self.GetEffectivePhaseKey and self:GetEffectivePhaseKey(selection) or selection.phase",
            "local levelingMode = effectivePhaseKey == LEVELING_PHASE_KEY",
            "self:GetLevelingTooltipMatches",
            "self:GetGroupedLevelingTooltipMatches",
            "self:GetTooltipMatches",
            "self:GetGroupedTooltipMatches",
            "showExpanded = settings.showAllOnAlt and IsAltKeyDown",
            "matches = groupedMatches",
            "rawDiffersFromGrouped",
            "tostring(effectivePhaseKey)",
            "tostring(selectedLevel)",
            "tostring(priorityContext and priorityContext.playerClass)",
            "tostring(priorityContext and priorityContext.playerSpec)",
            "self:GetTooltipSpecFilterKey(specFilters)",
        ]:
            self.assertIn(token, tooltip)
        self.assertNotIn("local PLAYER_CLASS_NAMES", tooltip)
        self.assertNotIn("pcall(UnitClassBase", tooltip)
        self.assertNotIn("pcall(GetTalentTabInfo", tooltip)
        self.assertIn("function BigBiSList:GetLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext)", data_index)
        self.assertIn("function BigBiSList:GetGroupedLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext, expanded)", data_index)
        self.assertIn("use.tooltip_level_label or use.level_label or \"Leveling\"", data_index)
        self.assertIn("if group and group.leveling then", data_index)
        self.assertIn("function BigBiSList:GetTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters, priorityContext)", data_index)
        self.assertIn("function BigBiSList:GetGroupedTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters, priorityContext, expanded)", data_index)
        self.assertIn('local playerClass = type(priorityContext) == "table" and priorityContext.playerClass or nil', data_index)
        self.assertIn('local playerSpec = type(priorityContext) == "table" and priorityContext.playerSpec or nil', data_index)
        self.assertIn("local aPlayerClass = a.class == playerClass and 1 or 0", data_index)
        self.assertIn("local aPlayerSpec = (a.class == playerClass and a.spec == playerSpec) and 1 or 0", data_index)
        self.assertIn("self:GetTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters, priorityContext)", data_index)
        self.assertIn("selectedSpecFirst = selectedSpecFirst ~= false", data_index)
        self.assertIn("tooltipSpecEnabled(specFilters, use.class, use.spec)", data_index)

        body = data_index.split("function BigBiSList:GetTooltipMatches", 1)[1].split("function BigBiSList:GetGroupedTooltipMatches", 1)[0]
        self.assertLess(body.index("tooltipSpecEnabled"), body.index("table.sort(matches"))
        self.assertLess(body.index("aPlayerClass"), body.index("aSelected"))
        self.assertLess(body.index("aPlayerSpec"), body.index("aSelected"))
        self.assertLess(body.index("selectedSpecFirst = selectedSpecFirst ~= false"), body.index("table.sort(matches"))

    def test_settings_sections_tooltip_groups_and_hidden_item_recovery_are_rendered(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "function UI:SetTooltipSpecFilter",
            "function UI:SetTooltipClassSpecFilters",
            "function UI:SetAllTooltipSpecFilters",
            "function UI:GetTooltipSpecSelectionCount",
            "function UI:CreateSettingsActionHeader",
            "function UI:CreateSettingsClassHeader",
            "function UI:CreateTooltipSpecsHeader",
            '"Appearance"',
            '"Tooltips"',
            '"Tooltip Specs"',
            '"Hidden Items"',
            "tostring(selected) .. \"/\" .. tostring(total)",
            "tostring(selected) .. \"/\" .. tostring(total) .. \" selected\"",
            "self:SetAllTooltipSpecFilters(true)",
            "self:SetAllTooltipSpecFilters(false)",
            '"All"',
            '"None"',
            "BigBiSList:EnsureTooltipSpecFilters()",
            "profile.tooltips.specFilters",
            "for _, classData in ipairs(BigBiSList:GetClassSpecIndex().classes or {})",
            "function UI:RestoreAllHiddenItems()",
            '"Restore All"',
            '"Restore"',
            "ignoredItems",
            "ResetWindowLayout",
        ]:
            self.assertIn(token, ui)
        settings_body = self.ui_function("RenderSettingsTab")
        self.assertIn("CreateSettingsClassHeader", settings_body)
        self.assertIn("profile.collapsedClasses", ui)
        self.assertIn("if not collapsed then", settings_body)
        self.require_tokens(settings_body, ['self.settingsSection == "appearance"', 'self.settingsSection == "tooltips"', 'profile.window.density'])

    def test_tooltip_grouping_builds_semantic_phase_summary(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "TOOLTIP_SUMMARY_CHUNK_LIMIT = 3",
            "tooltipGroupKey",
            "tooltipSlotGroup",
            "tooltipUseDedupeKey",
            "tooltipRankShortLabel",
            "tooltipPhaseSummary",
            "tooltipPhaseRangeSummary",
            "buildTooltipPhaseSegments",
            "buildTooltipGroupSummary",
            "buildTooltipGroupSlotLabel",
            "buildTooltipGroupSummary(group, expanded)",
            "tooltip_grouped = true",
            'return "Alt"',
            'return "Optional"',
            'return "Main/Off Hand"',
        ]:
            self.assertIn(token, data_index)

    def test_zone_filter_options_are_context_aware(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")
        for token in [
            "GetAvailableFilterZones",
            "cloneFiltersForZoneOptions",
            'scopedFilters.zone = "all"',
            "scopedFilters.zones = nil",
            "addZonesFromRow",
            "sourceZoneIsPhaseAvailable",
            "getItemPhaseMeta",
        ]:
            self.assertIn(token, data_index)
        self.assertNotIn('table.insert(zones, "Unknown")', data_index)
        self.assertNotIn('(row.zone or "Unknown")', data_index)
        for token in [
            "GetAvailableZoneValues",
            "ValidateZoneFilter",
            "IsZoneValueAvailable",
            "GetFacetDropdownItems(self:GetAvailableZoneValues()",
            'ToggleFacetFilter("zones", value, "zone")',
        ]:
            self.assertIn(token, ui)
        self.assertNotIn("BigBiSList:GetDataIndex().zones", ui)
        zone_dropdown_body = ui.split("function UI:GetZoneDropdownItems()", 1)[1].split("function UI:SetClass", 1)[0]
        self.assertNotIn("Unknown", zone_dropdown_body)
        self.assertNotIn("unknown", zone_dropdown_body)

    def test_reputation_filter_options_are_context_aware(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")
        for token in [
            "GetAvailableFilterReputations",
            "cloneFiltersForReputationOptions",
            'scopedFilters.reputation = "all"',
            "addReputationsFromRow",
            "rowMatchesReputationFilter",
            "rowReputationsWithMeta",
        ]:
            self.assertIn(token, data_index)
        for token in [
            "GetAvailableReputationValues",
            "ValidateReputationFilter",
            "IsReputationValueAvailable",
            "GetReputationDropdownItems",
            "BigBiSListReputationDropdown",
        ]:
            self.assertIn(token, ui)

    def test_source_filter_options_are_context_aware(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")
        for token in [
            "GetAvailableFilterSourceTypes",
            "cloneFiltersForSourceTypeOptions",
            'scopedFilters.sourceType = "all"',
            "scopedFilters.sourceTypes = nil",
            "addSourceTypeFromRow",
            "source_filter_key",
            "SOURCE_FILTER_BY_CONTENT_TYPE",
            "raid_drop",
            "heroic_dungeon_drop",
            "dungeon_drop",
            "other_drop",
            "getItemPhaseMeta",
            "rowMatchesSourceFilter(row, filters.sourceType, selectedPhaseIndex)",
        ]:
            self.assertIn(token, data_index)
        for token in [
            "GetAvailableSourceTypeValues",
            "ValidateSourceTypeFilter",
            "IsSourceTypeValueAvailable",
            "GetFacetDropdownItems(self:GetAvailableSourceTypeValues()",
            'ToggleFacetFilter("sourceTypes", value, "sourceType")',
        ]:
            self.assertIn(token, ui)
        source_dropdown_body = ui.split("function UI:GetSourceDropdownItems()", 1)[1].split("function UI:GetZoneDropdownItems()", 1)[0]
        self.assertNotIn("BigBiSList:GetDataIndex().sourceTypes", source_dropdown_body)

    def test_filter_options_are_phase_aware(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "RAID_ZONE_PHASE",
            "ZONE_PHASE",
            "[\"Isle of Quel'Danas\"] = \"SWP\"",
            "RAID_QUEST_PHASE_BY_ID",
            "deriveSourceAcquisitionPhase",
            "sourcesForAcquisitionPhase",
            "isWeakAmbiguousDrop",
            "sourceIsPhaseAvailable",
            "sourceZoneIsPhaseAvailable",
            "source.token_sources",
            "source.quest_starter_sources",
            "source.recipe_sources",
            "acquisition_phase = acquisitionPhase",
            "includeByFilter(use, filters, selectedIndex)",
            "includeByFilter(group, filters, selectedIndex)",
            "local selectedIndex = self:GetAvailabilityPhaseIndex(phaseKey)",
        ]:
            self.assertIn(token, data_index)
        self.assertLess(data_index.index("deriveSourceAcquisitionPhase"), data_index.index("function BigBiSList:GetPhaseRows"))
        self.assertLess(data_index.index("sourceZoneIsPhaseAvailable"), data_index.index("addZonesFromRow"))

    def test_legacy_drop_source_filter_is_reset(self):
        config = self.read_lua("Config.lua")
        for token in [
            "migrateSplitDropSourceFilter",
            'filters.sourceType == "drop"',
            'filters.sourceType = "all"',
            "filters.sourceTypes.drop = nil",
        ]:
            self.assertIn(token, config)

    def test_availability_filters_include_runtime_filter_payloads(self):
        ui = self.read_lua("UI.lua")
        availability_body = ui.split("function UI:GetAvailabilityFilters()", 1)[1].split("function UI:GetAvailableSourceTypeValues()", 1)[0]
        for token in [
            "self.currentOwned = self.currentOwned or self:BuildOwnedItems()",
            "filters.ownedItems = self.currentOwned",
            "filters.ignoredItems = char.ignoredItems",
            "filters.hideIgnored = true",
            "filters.wishlistItems = char.wishlist",
            "filters.endgamePhase = (self:GetSelection() or {}).phase",
            "filters.enhancementType = enhancementState.type or \"all\"",
            "filters.appliedState = enhancementState.appliedState or \"all\"",
            "filters.wishlistRelevance = wishlistState.relevance or \"all\"",
            "filters.getEnhancementAppliedState = function(row)",
            "return self:SanitizeFilterPayloadForView(filters)",
        ]:
            self.assertIn(token, availability_body)

    def test_filter_payloads_keep_shared_state_dormant_and_reset_local_state(self):
        ui = self.read_lua("UI.lua")
        sanitize_body = ui.split("function UI:SanitizeFilterPayloadForView(payload)", 1)[1].split("function UI:SaveWindow", 1)[0]
        for token in [
            'tabName == "Enhance"',
            'tabName == "Wishlist"',
            'tabName == "Gear Guide"',
            'self.currentFilterPayload.enhancementType',
            'self.currentFilterPayload.appliedState',
            'self.currentFilterPayload.wishlistRelevance',
            'self.currentFilterPayload.recommendationCategory',
        ]:
            self.assertIn(token, ui)
        self.assertNotIn("self:GetFilters()", sanitize_body)

        chips_body = ui.split("function UI:GetActiveFilterChips()", 1)[1].split("function UI:ActiveFilterBarHeight", 1)[0]
        for token in [
            'local tabName = normalizeTabName((self:GetSelection() or {}).tab)',
            'local supportsItems = tabName == "Upgrades" or tabName == "By Slot" or tabName == "Wishlist"',
            "local supportsAcquisition = self:ViewSupportsFilters(tabName)",
            'if tabName == "Upgrades"',
            'elseif tabName == "Gear Guide"',
            'elseif tabName == "Enhance"',
            'if tabName == "Wishlist"',
            "if supportsAcquisition then",
        ]:
            self.assertIn(token, chips_body)
        self.assertIn('"Rank"', chips_body)
        self.assertNotIn('"Tag"', chips_body)

        clear_body = self.ui_function("ClearFilters")
        for token in [
            'self:GetViewState("Gear Guide")',
            'self:GetViewState("Enhance")',
            'self:GetViewState("Wishlist")',
            'filters.upgradeMode = "actual"',
            'filters.longevity = "all"',
            'recommendationCategory = "all"',
            'type = "all"',
            'appliedState = "all"',
            'relevance = "all"',
        ]:
            self.assertIn(token, clear_body)
        self.require_tokens(self.ui_function("GetFilters"), ['self:GetViewState(viewName)', 'return state.filters'])
        self.assertNotIn("BigBiSList:GetCharacterDB().filters", clear_body)

    def test_filter_drawer_groups_item_and_acquisition_controls(self):
        ui = self.read_lua("UI.lua")
        drawer_body = ui.split("function UI:CreateFilterDrawer(parent)", 1)[1].split("function UI:GetVisibleFilterControlKeys", 1)[0]
        self.assertIn('SetText("Item")', drawer_body)
        self.assertIn('SetText("Acquisition")', drawer_body)
        self.assertIn('"Clear filters"', drawer_body)

    def test_rank_filter_labels_are_clear(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "local RANK_FILTER_LABELS",
            "local LEVELING_RANK_FILTER_LABELS",
            'bis = "BiS only"',
            'ranked = "Alts only"',
            'situational = "Sidegrades"',
            'option = "Optional"',
            'leveling_recommended = "Recommended"',
            'leveling_tank_pick = "Tank pick"',
            'leveling_damage_focused = "Damage-focused"',
            'leveling_healing_focused = "Healing-focused"',
            "GetRankDropdownText",
            "function UI:GetRankFilterValuesAndLabels()",
            '"Usefulness: " .. longevityFilterLabel',
        ]:
            self.assertIn(token, ui)
        self.assertNotIn('filters.rankGroup == "all" and "All" or filters.rankGroup', ui)
        self.assertNotIn('"Rank: " .. rankFilterLabel', ui)
        self.assertNotIn('"Longevity: " .. longevityFilterLabel', ui)

    def test_leveling_rank_dropdown_helper_is_forward_declared(self):
        ui = self.read_lua("UI.lua")
        self.assertLess(ui.index("local selectedFacetKeys"), ui.index("function UI:GetRankDropdownText()"))
        self.assertGreater(ui.index("selectedFacetKeys = function"), ui.index("function UI:GetRankDropdownText()"))

    def test_filter_drawer_controls_are_view_capability_aware(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            "containsText(row.source_note, filters.search)",
            "containsText(row.section, filters.search)",
            "containsText(row.level_label, filters.search)",
            "containsText(row.level_value_text, filters.search)",
            "containsText(row.category_label, filters.search)",
            "LEVELING_HELPERS.isCategoryKey(filters.rankGroup)",
            "LEVELING_HELPERS.isCategoryKey(key)",
        ]:
            self.assertIn(token, data_index)

        for token in [
            "function UI:ViewSupportsFilters(tabName)",
            "function UI:CreateListToolbar(parent)",
            "function UI:CreateFilterDrawer(parent)",
            "function UI:GetVisibleFilterControlKeys()",
            'if tabName == "Upgrades" then',
            'elseif tabName == "By Slot" then',
            'elseif tabName == "Gear Guide" then',
            'elseif tabName == "Enhance" then',
            'elseif tabName == "Wishlist" then',
            'return { "enhancementType", "enhancementApplied", "source", "cost", "vendor", "zone", "reputation" }',
            'return { "wishlistRelevance", "owned", "rank", "boe", "slot", "source", "cost", "vendor", "zone", "reputation" }',
            "return {}",
            "self.listToolbar:SetShown(supportsFilters)",
            "self.filterDrawer:SetShown(supportsFilters and self.filterDrawerOpen == true)",
            '"Filters (" .. count .. ")"',
            'label = "Search: " .. filters.search',
            "self:ClearFilters()",
        ]:
            self.assertIn(token, ui)

        create_body = ui.split("function UI:CreateBody(frame)", 1)[1].split("function UI:ApplyBodyLayout", 1)[0]
        self.assertIn("self:CreateListToolbar(contentRegion)", create_body)
        self.assertIn("self:CreateFilterDrawer(contentRegion)", create_body)
        self.assertNotIn("self:CreateLeftRail", create_body)

    def test_player_facing_recommendation_terms_are_tbc_friendly(self):
        runtime_text = self.read_lua("UI.lua") + self.read_lua("DataIndex.lua") + self.read_lua("Tooltip.lua")
        banned_literals = [
            '"BiS match',
            '"Listed alt',
            '"Off-list',
            '"Actual upgrades"',
            '"All targets"',
            '"Farmable',
            '"Need rep',
            '"Need prof',
            '"Need recipe',
            '"Tag meaning"',
            '"Have: "',
            '"Get: "',
            '"Ignore"',
            '"Unignore"',
        ]
        for token in banned_literals:
            self.assertNotIn(token.lower(), runtime_text.lower())
        for token in [
            '"Best in slot"',
            '"Alternative"',
            '"Not ranked"',
            '"Owned"',
            '"Access: "',
            '"Rank"',
            '"Benefit"',
            '"Available now"',
            '"Reputation required"',
            '"Profession required"',
            '"Recipe required"',
            '"Upgrades only"',
            '"All recommendations"',
            '"Hide item"',
        ]:
            self.assertIn(token, runtime_text)

    def test_leveling_recommendation_tags_are_cased_for_display(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "function LEVELING_HELPERS.reasonTagLabel(tag)",
            'best_overall = "Best Overall"',
            'best_easy_source = "Best Easy Source"',
            'human_sword_bonus = "Human Sword Bonus"',
            'night_elf_dodge_bonus = "Night Elf Dodge Bonus"',
            'return "Best for " .. race:gsub("_", " "):gsub("%S+", function(token)',
            "recommendationSummary = LEVELING_HELPERS.reasonTagLabel(primaryTag)",
        ]:
            self.assertIn(token, data_index)
        self.assertNotIn('recommendationSummary = primaryTag:gsub("_", " ")', data_index)

    def test_scalar_filters_use_dropdowns_not_cycle_buttons(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "BigBiSListRankDropdown",
            "BigBiSListOwnedDropdown",
            "BigBiSListBoeDropdown",
            "BigBiSListLongevityDropdown",
            "GetRankDropdownItems",
            "GetOwnedDropdownItems",
            "GetBoeDropdownItems",
            "GetLongevityDropdownItems",
        ]:
            self.assertIn(token, ui)
        for token in [
            "rankCycle",
            "rankButton",
            "ownedButton",
            "boeButton",
            "longevityButton",
            "RefreshFilterButtonLabels",
        ]:
            self.assertNotIn(token, ui)

    def test_faction_side_filter_is_automatic(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "UnitFactionGroup",
            "playerSide = getPlayerSide()",
            "optionMatchesPlayerSide",
            "faction = self.currentAccess and self.currentAccess.playerSide or \"all\"",
        ]:
            self.assertIn(token, ui)
        for token in [
            "getSourceSides",
            "rowMatchesFactionFilter",
            "sides = getSourceSides(acquisitionItem)",
            "sides = use.sides",
        ]:
            self.assertIn(token, data_index)

    def test_inspector_uses_task_focused_sections_and_lists_access_paths(self):
        ui = self.read_lua("UI.lua")
        details_body = self.ui_function("RefreshDetails")
        for token in [
            "GetAccessBlockingReason",
            "FormatAccessOptionRequirements",
            "FormatAccessOptions",
        ]:
            self.assertIn(token, ui)
        for token in [
            "Recommendation",
            "Selected route",
            "Other sellers",
            "Additional reported sellers",
            'label = "Requires"',
            "Expansion value",
            "Notes & provenance",
        ]:
            self.assertIn(token, details_body)
        self.assertLess(details_body.index('"Recommendation"'), details_body.index('"Selected route"'))
        self.assertLess(details_body.index('"Selected route"'), details_body.index('"Other sellers"'))
        self.assertLess(details_body.index('"Other sellers"'), details_body.index('"Additional reported sellers"'))
        self.assertLess(details_body.index('label = "Requires"'), details_body.index('"Selected route"'))
        self.assertLess(details_body.index('"Additional reported sellers"'), details_body.index('"Expansion value"'))
        self.assertLess(details_body.index('"Expansion value"'), details_body.index('"Notes & provenance"'))
        self.require_tokens(details_body, [
            "self:RefreshDetailsHeader(",
            "self:CreateDetailsFields(",
            "self:CreateDetailsCollapsibleText(",
            "self:CreateDetailsPhaseMatrix(",
        ])
        header = self.ui_function("RefreshDetailsHeader")
        self.require_tokens(header, ["starOutline", "starFilled", "self:SetItemButton(", "self:SetSpellButton("])
        for old_heading in ["Tag meaning", "How to get", "Phase value", "Source notes"]:
            self.assertNotIn(f'"{old_heading}"', details_body)

    def test_vendor_purchase_details_share_hover_and_inspector_rendering(self):
        ui = self.read_lua("UI.lua")
        tooltip = self.read_lua("Tooltip.lua")

        for token in [
            "function UI:GetSellerDetailLines(option)",
            "BigBiSList:GetAccessOptionDetailFields(option)",
            "option.is_vendor_purchase == true",
            '"Vendor: "',
            '"Area: "',
            '"Cost: "',
            "option.location_area or option.zone",
            "option.location_note",
            "option.cost_summary",
            "option.vendor_details_status",
            "isReportedOnlyAccessOption",
            'local missing = "Unavailable in committed source data"',
            "function UI:GetRowSellerDisplayGroups(data, selectedOption)",
            "BigBiSList:GetRowSellerGroups(data, selectedOption, phaseKey)",
            "dedupeSellerOptions",
            "function UI:ShowAcquisitionTooltip(owner, data)",
            "UI:ShowAcquisitionTooltip(selfBadge, selfBadge.boundData)",
            "row.cellHovers",
            "UI:AddSelectedRouteTooltipLines(tooltip, row.boundData, UI:GetAccessEvaluation(row.boundData))",
            "function UI:CreateDetailsCollapsibleText",
            "expandedSellerSections",
        ]:
            self.assertIn(token, ui)

        self.assertNotIn("GetSellerCompactDisplay", ui)
        self.assertNotIn("GetSellerDetailLines", tooltip)
        self.assertNotIn("GetRowSellerGroups", tooltip)

    def test_inspector_visibility_is_persisted_and_settings_take_full_width(self):
        config = self.read_lua("Config.lua")
        ui = self.read_lua("UI.lua")
        for token in [
            "inspectorVisible = false",
            "function BigBiSList:IsInspectorVisible()",
            "function BigBiSList:SetInspectorVisible(visible)",
        ]:
            self.assertIn(token, config)
        for token in [
            "function UI:ViewSupportsInspector(tabName)",
            'normalizeTabName(tabName or (self:GetSelection() or {}).tab) ~= "Settings"',
            "function UI:SetInspectorVisible(visible)",
            "function UI:ShowInspectorFor(entityId, data, mode)",
            "self:SetInspectorVisible(true)",
            "self.details:SetShown(showInspector)",
            "self:GetBodyGeometry(",
            'geometry.docked and self.details or self.body',
        ]:
            self.assertIn(token, ui)

    def test_hiding_items_preserves_wishlist_membership_and_reports_feedback(self):
        hide_body = self.ui_function("IgnoreItem")
        restore_body = self.ui_function("UnignoreItem")
        restore_all_body = self.ui_function("RestoreAllHiddenItems")
        self.assertIn('self:SetItemCollectionState("ignoredItems", itemId, true, "Hidden: ", "hide-item")', hide_body)
        self.assertNotIn("wishlist", hide_body)
        self.assertIn('self:SetItemCollectionState("ignoredItems", itemId, nil, "Restored: ", "restore-item")', restore_body)
        self.assertIn("ignoredItems = {}", restore_all_body)
        self.assertIn("All hidden items restored", restore_all_body)
        mutation = self.ui_function("SetItemCollectionState")
        self.require_tokens(mutation, [
            "local previous = char[collectionName][key]",
            "char[collectionName][key] = value",
            "message .. name",
            "callback = function() char[collectionName][key] = previous end",
        ])
        self.assertNotIn("char.wishlist", mutation)
        self.require_tokens(self.ui_function("UndoLastAction"), ["action.expiresAt", "action.callback()", 'self:Invalidate("query", "undo")'])

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
            "self:SetSpellButton(icon,",
        ]:
            self.assertIn(token, ui)

        row_body = self.ui_function("CreateDataRow")
        spell_button_index = row_body.index("self:SetSpellButton(icon,")
        item_button_index = row_body.index("self:SetItemButton(icon, data.item_id")
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

    def test_upgrades_tab_defaults_to_actual_upgrade_filtering(self):
        config = self.read_lua("Config.lua")
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            'upgradeMode = "actual"',
            "BigBiSListUpgradeModeDropdown",
            "GetUpgradeModeDropdownItems",
            'return upgradeModeLabel(self:GetFilters("Upgrades").upgradeMode)',
            "upgradeMode = filters.upgradeMode",
            'filters.upgradeMode = "actual"',
            "upgradeComparisonText",
            "GameTooltip:AddLine(upgradeText",
        ]:
            self.assertIn(token, config + ui)

        for token in [
            "includeOwnedUpgrades",
            "BigBiSListOwnedUpgradeDropdown",
            "GetOwnedUpgradeDropdownItems",
            "ownedUpgradeLabel",
        ]:
            self.assertNotIn(token, config + ui)

        for token in [
            "local function isStrictUpgradeUse",
            "candidate.item_id == current.item_id",
            "local function upgradeSlotCapacity",
            'slotName == "Ring" or slotName == "Trinket"',
            "ownedBySlot = {}",
            "equippedBySlot = {}",
            "buildUpgradeBaselines(self, className, specName, selectedPhaseKey, filters.ownedItems)",
            "group.upgrade_state = state",
            '"missing_upgrade"',
            '"owned_upgrade"',
            '"not_upgrade"',
            'ownedState == "equipped"',
            'ownedState == "bag" or ownedState == "bank"',
            "upgradeComparisonContext(baselines.equippedBySlot, candidateUse)",
            "upgradeComparisonContext(baselines.ownedBySlot, candidateUse)",
            "group.upgrade_state == \"owned_upgrade\"",
            "plannerGroupMatchesUpgradeMode(group, filters)",
        ]:
            self.assertIn(token, data_index)

        planner_body = data_index.split("function BigBiSList:GetPlannerRows", 1)[1].split("local function cloneFiltersForZoneOptions", 1)[0]
        self.assertLess(planner_body.index("annotatePlannerUpgradeGroup"), planner_body.index("plannerGroupMatchesUpgradeMode"))
        self.assertIn('filters and filters.upgradeMode == "actual"', planner_body)
        self.assertIn("and plannerGroupMatchesUpgradeMode(group, filters)", planner_body)

    def test_esc_closable_frame_is_registered(self):
        ui = self.read_lua("UI.lua")
        self.assertIn('"BigBiSListMainFrame"', ui)
        self.assertIn("UISpecialFrames", ui)
        self.assertIn("OnEscapePressed", ui)

    def test_minimap_button_is_broker_based_and_toggleable(self):
        minimap = self.read_lua("Minimap.lua")
        ui = self.read_lua("UI.lua")
        core = self.read_lua("Core.lua")
        for token in [
            "Interface\\\\AddOns\\\\BigBiSList\\\\assets\\\\icon.tga",
            'LibStub("LibDataBroker-1.1", true)',
            'LibStub("LibDBIcon-1.0", true)',
            "NewDataObject",
            'type = "launcher"',
            "LDBIcon:Register",
            "LDBIcon:Refresh",
            "GetMinimapButton",
            "ToggleMainFrame",
            "RefreshMinimapButton",
            "profile.minimap.hide",
        ]:
            self.assertIn(token, minimap)
        self.assertIn("Show minimap button", ui)
        self.assertIn("profile.minimap.hide", ui)
        self.assertIn("InitMinimapButton", core)
