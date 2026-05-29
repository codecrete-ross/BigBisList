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
            "local DEFAULTS_VERSION = 7",
            "window = {",
            "width = 1160",
            "minimap = {",
            "hide = false",
            "minimapPos = 225",
            "tooltips = {",
            "specFilters = {}",
            "specFiltersInitialized = false",
            "selection = {",
            'selectedPhase = "PR"',
            'selectedTab = "Upgrades"',
            'phase = "PR"',
            'tab = "Upgrades"',
            "filters = {",
            'reputation = "all"',
            "bankCache = {",
            "wishlist = {}",
            "ignoredItems = {}",
            "migrateLegacyDefaults",
            "normalizeTabName",
            "migrateMinimapSettings",
            "ensureTooltipSpecFilters",
            "EnsureTooltipSpecFilters",
            "GetTooltipSpecFilterKey",
            "migrateTooltipSpecFilterDefaults",
            "tooltipSpecFiltersMatchLegacyDruidDefault",
            "enableAllTooltipSpecFilters",
            "previousVersion ~= nil and previousVersion >= 7",
            "tooltips.specFilters[className][specName] = true",
        ]:
            self.assertIn(token, config)
        self.assertNotIn("local selectedClass = db.char and db.char.selection and db.char.selection.class", config)
        self.assertNotIn("firstInitialization and className == selectedClass or false", config)

    def test_public_ui_methods_exist(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        for method in ["OpenMainFrame", "CloseMainFrame", "ToggleMainFrame", "RefreshUI"]:
            self.assertIn(f"function BigBiSList:{method}()", ui)
        for method in ["GetDataIndex", "GetPhaseRows", "GetPlannerRows", "GetAvailableFilterSourceTypes", "GetDisplaySlotFilters", "GetItemBestUseForSpec", "GetEquippedGearRows"]:
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

        self.assertIn('{ "Upgrades", "By Slot", "Equipped", "Enhance", "Wishlist", "Settings" }', ui)
        self.assertIn('Phase = "By Slot"', ui)
        self.assertIn('Gear = "Equipped"', ui)
        self.assertIn('Planner = "Upgrades"', ui)
        self.assertIn('Enhancements = "Enhance"', ui)
        self.assertIn('Enhance = "Enhancements"', ui)
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
            'bank = "Bank"',
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
            "ACCESS_BADGE_LABELS",
            "GetAccessStatus",
            "EvaluateRequirement",
            "BuildAccessState",
            "Requirements",
            "Can get",
        ]:
            self.assertIn(token, ui)
        self.assertIn("CreateOwnershipBadge", ui)
        self.assertLess(ui.index("CreateOwnershipBadge"), ui.index("CreateAccessBadge"))
        self.assertIn("requirements = mergedRequirements", data_index)

    def test_rows_use_clear_columns_and_wrapped_text(self):
        ui = self.read_lua("UI.lua")
        widgets = self.read_lua("Widgets.lua")
        data_index = self.read_lua("DataIndex.lua")

        for token in [
            "CreateListColumnHeader",
            '"Tag"',
            '"Item"',
            '"Why"',
            '"Have"',
            '"Get"',
            "rowColumnLayout",
            "WHY_COLUMN_THRESHOLD",
            "CreateRankBadge",
            "GetRowOwnershipState",
            "data and data.ownership_label",
            "GetAccessBadgeLabel",
            "GetRowRecommendationText",
            "GetRowSubline",
            "MeasureTextHeight",
            "row:SetHeight(rowHeight)",
        ]:
            self.assertIn(token, ui)
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
            "recommendation_tier",
            "recommendation_summary",
            "plannerRecommendationTier",
        ]:
            self.assertIn(token, data_index)

        ownership_badge_body = ui.split("function UI:CreateOwnershipBadge", 1)[1].split("function UI:CreateAccessBadge", 1)[0]
        access_badge_body = ui.split("function UI:CreateAccessBadge", 1)[1].split("function UI:CreateRankBadge", 1)[0]
        self.assertNotIn('"Have: "', ownership_badge_body)
        self.assertNotIn('"Get: "', access_badge_body)

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
            '"Need prof"',
            '"Check reqs"',
        ]:
            self.assertIn(token, ui)
        self.assertIn("zone = source.zone", data_index)
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

    def test_enhance_rows_omit_redundant_tag_column(self):
        ui = self.read_lua("UI.lua")

        for token in [
            'rowColumnLayout(width, mode ~= "enhance")',
            "showRank = showRank",
            "if layout.showRank then",
            'CreateListColumnHeader(self.contentChild, yOffset, "enhance")',
            'if detailMode ~= "enhance" then',
        ]:
            self.assertIn(token, ui)
        self.assertIn('table.insert(labels, 1, { text = "Tag", column = layout.rank })', ui)

    def test_source_aware_access_options_are_indexed(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "buildAccessOptions",
            "splitRequirements",
            "sourceMatchesRequirement",
            "source.requirements",
            "access_options = buildAccessOptions",
            "zone = source.zone",
            "gemSourcesById",
            "enchantSourcesByKey",
            "enhancementSourceKey(entityType, enchant.id)",
            "forceSourceScopedEquip = entityType == \"spell\"",
        ]:
            self.assertIn(token, data_index)

    def test_enhance_consumable_alternatives_are_grouped(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")

        for token in [
            "CONSUMABLE_CATEGORY_LABELS",
            "consumable.relationship == \"or\"",
            "consumableCanGroupAlternatives",
            "item_ids = itemIds",
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

    def test_enhancement_rows_use_actionable_copy(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")

        for token in [
            "GEM_SOCKET_LABELS",
            "gemDetailLabel",
            "enchantDetailLabel",
            "enchantRecommendationSummary",
            'recommendation_summary = "Socket this gem"',
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
            "Farmable through alternate source",
            "EvaluateRequirementList",
            "EvaluateAccessOption",
            "GetAccessEvaluation",
            "data and data.access_options",
            "firstReadyEvaluation",
            "local flatEvaluation = self:EvaluateRequirementList",
        ]:
            self.assertIn(token, ui)
        self.assertLess(ui.index("data and data.access_options"), ui.index("local flatEvaluation = self:EvaluateRequirementList"))

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

    def test_current_gear_row_reserves_distinct_regions(self):
        ui = self.read_lua("UI.lua")
        body = ui.split("function UI:CreateGearSlotRow", 1)[1].split("function UI:RenderGearTab", 1)[0]
        self.assertIn("local badgeRightInset = 92", body)
        self.assertIn('slotLabel:SetPoint("TOPLEFT", row, "TOPLEFT", 8, -4)', body)
        self.assertIn('iconButton:SetPoint("TOPLEFT", slotLabel, "BOTTOMLEFT", 0, -2)', body)
        self.assertIn('nameText:SetPoint("TOPLEFT", iconButton, "TOPRIGHT", 8, 2)', body)
        self.assertIn('nameText:SetPoint("RIGHT", row, "RIGHT", -badgeRightInset, 0)', body)
        self.assertIn('detailText:SetPoint("RIGHT", row, "RIGHT", -badgeRightInset, 0)', body)
        self.assertNotIn('iconButton:SetPoint("BOTTOMLEFT"', body)
        self.assertLess(body.index("slotLabel:SetPoint"), body.index("iconButton:SetPoint"))

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
            "settings.selectedSpecFirst ~= false",
            "settings.compact and 4 or 8",
            "settings.showAllOnAlt and IsAltKeyDown",
            "local specFilters = settings.specFilters",
            "rawMatches = self:GetTooltipMatches",
            "groupedMatches = self:GetGroupedTooltipMatches",
            "showRaw = settings.showAllOnAlt and IsAltKeyDown",
            "matches = showRaw and rawMatches or groupedMatches",
            "rawDiffersFromGrouped",
            "self:GetTooltipSpecFilterKey(specFilters)",
        ]:
            self.assertIn(token, tooltip)
        self.assertIn("function BigBiSList:GetTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters)", data_index)
        self.assertIn("function BigBiSList:GetGroupedTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters)", data_index)
        self.assertIn("selectedSpecFirst = selectedSpecFirst ~= false", data_index)
        self.assertIn("tooltipSpecEnabled(specFilters, use.class, use.spec)", data_index)

        body = data_index.split("function BigBiSList:GetTooltipMatches", 1)[1].split("function BigBiSList:GetGroupedTooltipMatches", 1)[0]
        self.assertLess(body.index("tooltipSpecEnabled"), body.index("table.sort(matches"))
        self.assertLess(body.index("selectedSpecFirst = selectedSpecFirst ~= false"), body.index("table.sort(matches"))

    def test_tooltip_spec_filter_settings_are_rendered(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "function UI:SetTooltipSpecFilter",
            "function UI:SetTooltipClassSpecFilters",
            "function UI:SetAllTooltipSpecFilters",
            "function UI:GetTooltipSpecSelectionCount",
            "function UI:CreateSettingsActionHeader",
            "function UI:CreateSettingsClassHeader",
            "function UI:CreateTooltipSpecsHeader",
            '"General"',
            '"Tooltip Display"',
            '"Specs in Tooltips"',
            "tostring(selected) .. \"/\" .. tostring(total)",
            "tostring(selected) .. \"/\" .. tostring(total) .. \" selected\"",
            "self:SetAllTooltipSpecFilters(true)",
            "self:SetAllTooltipSpecFilters(false)",
            '"All"',
            '"None"',
            "BigBiSList:EnsureTooltipSpecFilters()",
            "profile.tooltips.specFilters",
            "for _, classData in ipairs(BigBiSList:GetDataIndex().classes or {})",
            "self:CreateSettingToggle(self.contentChild, yOffset, currentSpecName",
            "end, 14)",
        ]:
            self.assertIn(token, ui)
        self.assertNotIn("Tooltip Specs - ", ui)
        self.assertNotIn("Visible Specs", ui)

    def test_tooltip_grouping_builds_semantic_phase_summary(self):
        data_index = self.read_lua("DataIndex.lua")
        for token in [
            "TOOLTIP_SUMMARY_CHUNK_LIMIT = 3",
            "tooltipGroupKey",
            "tooltipRankShortLabel",
            "tooltipPhaseSummary",
            "buildTooltipGroupSummary",
            "group.phase_summary = buildTooltipGroupSummary(group)",
            "tooltip_grouped = true",
            'return "Alt"',
            'return "Nice-to-have"',
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
        ]:
            self.assertIn(token, data_index)
        self.assertNotIn('table.insert(zones, "Unknown")', data_index)
        self.assertNotIn('(row.zone or "Unknown")', data_index)
        for token in [
            "GetAvailableZoneValues",
            "ValidateZoneFilter",
            "IsZoneValueAvailable",
            "for _, zone in ipairs(self:GetAvailableZoneValues())",
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
        ]:
            self.assertIn(token, data_index)
        for token in [
            "GetAvailableSourceTypeValues",
            "ValidateSourceTypeFilter",
            "IsSourceTypeValueAvailable",
            "for _, sourceType in ipairs(self:GetAvailableSourceTypeValues())",
        ]:
            self.assertIn(token, ui)
        source_dropdown_body = ui.split("function UI:GetSourceDropdownItems()", 1)[1].split("function UI:GetZoneDropdownItems()", 1)[0]
        self.assertNotIn("BigBiSList:GetDataIndex().sourceTypes", source_dropdown_body)

    def test_availability_filters_include_runtime_filter_payloads(self):
        ui = self.read_lua("UI.lua")
        availability_body = ui.split("function UI:GetAvailabilityFilters()", 1)[1].split("function UI:GetAvailableSourceTypeValues()", 1)[0]
        for token in [
            "filters.ownedItems = self.currentOwned or self:BuildOwnedItems()",
            "filters.ignoredItems = BigBiSListDB.char.ignoredItems",
            "filters.hideIgnored = true",
        ]:
            self.assertIn(token, availability_body)

    def test_rank_filter_labels_are_clear(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "local RANK_FILTER_LABELS",
            'bis = "BiS only"',
            'ranked = "Alts only"',
            'situational = "Sidegrades"',
            'option = "Nice-to-have"',
            "rankFilterLabel(self:GetFilters().rankGroup)",
            '"Tag: " .. rankFilterLabel',
            '"Usefulness: " .. longevityFilterLabel',
        ]:
            self.assertIn(token, ui)
        self.assertNotIn('filters.rankGroup == "all" and "All" or filters.rankGroup', ui)
        self.assertNotIn('"Rank: " .. rankFilterLabel', ui)
        self.assertNotIn('"Longevity: " .. longevityFilterLabel', ui)

    def test_player_facing_recommendation_terms_are_tbc_friendly(self):
        runtime_text = self.read_lua("UI.lua") + self.read_lua("DataIndex.lua") + self.read_lua("Tooltip.lua")
        for token in [
            '"Best"',
            '"Ranked"',
            '"Situational"',
            '"Hard"',
            '"Backup"',
            '"Core"',
            '"High"',
            '"Useful"',
            '"Opportunistic"',
            '"Listed option"',
            '"No list match"',
            '"Rank meaning"',
            '"Prerequisites"',
            '"Timeline"',
        ]:
            self.assertNotIn(token, runtime_text)
        for token in [
            '"BiS"',
            '"Alt"',
            '"Sidegrade"',
            '"Hard Farm"',
            '"Nice-to-have"',
            '"Tag"',
            '"Tag meaning"',
            '"Phase value"',
            '"Source notes"',
        ]:
            self.assertIn(token, runtime_text)

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
            "sides = getSourceSides(item)",
            "sides = use.sides",
        ]:
            self.assertIn(token, data_index)

    def test_details_drawer_lists_access_paths(self):
        ui = self.read_lua("UI.lua")
        details_body = ui.split("function UI:RefreshDetails", 1)[1].split("function UI:RefreshControls", 1)[0]
        for token in [
            "GetAccessBlockingReason",
            "FormatAccessOptionRequirements",
            "FormatAccessOptions",
        ]:
            self.assertIn(token, ui)
        for token in [
            "Recommendation",
            "Tag meaning",
            "How to get",
            "Requirements",
            "Phase value",
            "Source notes",
        ]:
            self.assertIn(token, details_body)
        self.assertLess(details_body.index('"Recommendation"'), details_body.index('"Tag meaning"'))
        self.assertLess(details_body.index('"Tag meaning"'), details_body.index('"How to get"'))
        self.assertLess(details_body.index('"How to get"'), details_body.index('"Requirements"'))
        self.assertLess(details_body.index('"Requirements"'), details_body.index('"Phase value"'))
        self.assertLess(details_body.index('"Phase value"'), details_body.index('"Source notes", sourceSummary'))

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
