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
            "local DEFAULTS_VERSION = 11",
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
            'lastDetectedPhase = "PR"',
            'selectedTab = "Upgrades"',
            'phase = "PR"',
            'tab = "Upgrades"',
            "filters = {",
            'reputation = "all"',
            "bankCache = {",
            "links = {}",
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

    def test_current_phase_detection_defaults_stale_selections(self):
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
            "phaseKey == char.lastDetectedPhase",
            "phaseKey = detectedPhase",
            "char.lastDetectedPhase = detectedPhase",
        ]:
            self.assertIn(token, validate_body)

    def test_public_ui_methods_exist(self):
        ui = self.read_lua("UI.lua")
        data_index = self.read_lua("DataIndex.lua")
        for method in ["OpenMainFrame", "CloseMainFrame", "ToggleMainFrame", "RefreshUI"]:
            self.assertIn(f"function BigBiSList:{method}()", ui)
        for method in ["GetDataIndex", "GetPhaseRows", "GetPlannerRows", "GetAvailableFilterSourceTypes", "GetFilterAvailabilitySnapshot", "GetItemMeta", "GetRowAccessOptions", "GetDisplaySlotFilters", "GetItemBestUseForSpec", "GetEquippedGearRows"]:
            self.assertIn(f"function BigBiSList:{method}", data_index)
        self.assertIn("function BigBiSList:SetSelection", self.read_lua("Config.lua"))

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
            'self:AddListSection(model, section.title, "enhance")',
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
            "function BigBiSList:GetRowAccessOptions(row)",
            "buildRowAccessOptions",
            "zone = source.zone",
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
            "function BigBiSList:GetItemMeta(itemId)",
            "buildItemMeta",
            "itemReputations",
            "rowReputationsWithMeta",
            "getItemPhaseMeta",
        ]:
            self.assertIn(token, data_index)

    def test_filter_availability_uses_one_snapshot(self):
        data_index = self.read_lua("DataIndex.lua")
        ui = self.read_lua("UI.lua")

        snapshot_body = data_index.split("function BigBiSList:GetFilterAvailabilitySnapshot", 1)[1].split("function BigBiSList:GetAvailableFilterSourceTypes", 1)[0]
        self.assertEqual(snapshot_body.count("collectAvailabilityRows"), 1)
        self.assertIn("cloneFiltersForAvailabilityRows", snapshot_body)
        self.assertIn("addSourceTypeFromRow", snapshot_body)
        self.assertIn("addZonesFromRow", snapshot_body)
        self.assertIn("addReputationsFromRow", snapshot_body)

        self.assertIn("function UI:GetFilterAvailabilitySnapshot()", ui)
        self.assertIn("self.currentAvailabilitySnapshot", ui)
        self.assertIn("BigBiSList:GetFilterAvailabilitySnapshot", ui)
        build_filter_body = ui.split("function UI:BuildFilterPayload()", 1)[1].split("function UI:SaveWindow", 1)[0]
        self.assertNotIn("GetPlannerRows", build_filter_body)
        self.assertNotIn("GetPhaseRows", build_filter_body)

    def test_first_open_schedules_one_refresh_after_frame_creation(self):
        ui = self.read_lua("UI.lua")
        create_body = ui.split("function UI:CreateMainFrame()", 1)[1].split("function UI:Open()", 1)[0]
        open_body = ui.split("function UI:Open()", 1)[1].split("function UI:Close()", 1)[0]

        self.assertNotIn("self:Refresh()", create_body)
        self.assertIn("self:ScheduleRefresh()", open_body)
        self.assertEqual(open_body.count("self:ScheduleRefresh()"), 1)

    def test_ui_refreshes_are_scheduled_and_virtualized(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "function UI:ScheduleRefresh(delay)",
            "C_Timer.After",
            "self:ScheduleRefresh(0.12)",
            "function UI:RenderListModel(model)",
            "function UI:UpdateVirtualList(force)",
            "function UI:ReleaseRenderFrames()",
            "LIST_OVERSCAN_ROWS",
            "self.renderPools",
            "self:AddListRow(model",
            "self:RenderListModel(model)",
        ]:
            self.assertIn(token, ui)

        for setter in ["SetClass", "SetSpec", "SetPhase", "SetTab", "SetFilter", "ToggleSlot", "ClearFilters"]:
            body = ui.split(f"function UI:{setter}", 1)[1].split("function UI:", 1)[0]
            self.assertIn("self:ScheduleRefresh()", body)

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
            'mode == "enhance" and "Status" or "Have"',
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
        ui = self.read_lua("UI.lua")
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
        self.assertIn("function UI:GetContextSourceSummary", ui)
        self.assertIn("self:GetContextSourceSummary(data)", ui)

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
            "local uses = self:GetTooltipUses(itemId)",
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
        self.assertIn("local selectedIndex = phaseIndex(phaseKey)", body)
        self.assertIn("use.acquisitionPhaseIndex <= selectedIndex", body)
        self.assertLess(body.index("local selectedIndex = phaseIndex(phaseKey)"), body.index("use.acquisitionPhaseIndex <= selectedIndex"))

    def test_source_aware_access_status_prefers_ready_options(self):
        ui = self.read_lua("UI.lua")
        for token in [
            "ready_alternate",
            "Farmable through alternate source",
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
            "UnitClassBase",
            "pcall(UnitClassBase, \"player\")",
            "pcall(UnitClass, \"player\")",
            "GetNumTalentTabs",
            "GetTalentTabInfo",
            "pcall(GetTalentTabInfo, tabIndex)",
            "exactSpecNameForClass",
            "return exactSpecNameForClass(className, selectedTabName)",
            "settings.selectedSpecFirst ~= false",
            "settings.compact and 4 or 8",
            "settings.showAllOnAlt and IsAltKeyDown",
            "local specFilters = settings.specFilters",
            "local priorityContext = getTooltipPriorityContext()",
            "rawMatches = self:GetTooltipMatches",
            "groupedMatches = self:GetGroupedTooltipMatches",
            "showExpanded = settings.showAllOnAlt and IsAltKeyDown",
            "matches = groupedMatches",
            "rawDiffersFromGrouped",
            "tostring(priorityContext and priorityContext.playerClass)",
            "tostring(priorityContext and priorityContext.playerSpec)",
            "self:GetTooltipSpecFilterKey(specFilters)",
        ]:
            self.assertIn(token, tooltip)
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
            "for _, classData in ipairs(BigBiSList:GetClassSpecIndex().classes or {})",
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
            'return "Nice-to-have"',
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
            "for _, sourceType in ipairs(self:GetAvailableSourceTypeValues())",
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
            "local selectedIndex = phaseIndex(phaseKey)",
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
            "filters.ownedItems = self.currentOwned or self:BuildOwnedItems()",
            "filters.ignoredItems = char.ignoredItems",
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
