local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local PHASE_ORDER = { "PR", "T4", "T5", "T6", "ZA", "SWP" }
local PHASE_DISPLAY = {
    PR = "Pre-Raid",
    T4 = "Phase 1",
    T5 = "Phase 2",
    T6 = "Phase 3",
    ZA = "Phase 4",
    SWP = "Phase 5",
}

local SLOT_ORDER = {
    "Head", "Neck", "Shoulder", "Back", "Chest", "Wrist",
    "Hands", "Waist", "Legs", "Feet", "Ring", "Trinket",
    "Main Hand", "Off Hand", "Two Hand", "Dual Wield",
    "Ranged", "Ammo", "Quiver", "Idol", "Totem", "Libram", "Relic",
}

local DISPLAY_SLOT_FILTERS = {
    { key = "Head", label = "Head", slots = { "Head" } },
    { key = "Neck", label = "Neck", slots = { "Neck" } },
    { key = "Shoulder", label = "Shoulder", slots = { "Shoulder" } },
    { key = "Back", label = "Back", slots = { "Back" } },
    { key = "Chest", label = "Chest", slots = { "Chest" } },
    { key = "Wrist", label = "Wrist", slots = { "Wrist" } },
    { key = "Hands", label = "Hands", slots = { "Hands" } },
    { key = "Waist", label = "Waist", slots = { "Waist" } },
    { key = "Legs", label = "Legs", slots = { "Legs" } },
    { key = "Feet", label = "Feet", slots = { "Feet" } },
    { key = "Rings", label = "Rings", slots = { "Ring" } },
    { key = "Trinkets", label = "Trinkets", slots = { "Trinket" } },
    { key = "Main Hand", label = "Main Hand", slots = { "Main Hand", "Two Hand", "Dual Wield" } },
    { key = "Off Hand", label = "Off Hand", slots = { "Off Hand", "Dual Wield" } },
    { key = "Ranged/Relic", label = "Ranged/Relic", slots = { "Ranged", "Ammo", "Quiver", "Idol", "Totem", "Libram", "Relic" } },
}

local DISPLAY_SLOT_FILTER_MAP = {}
for _, filter in ipairs(DISPLAY_SLOT_FILTERS) do
    DISPLAY_SLOT_FILTER_MAP[filter.key] = filter.slots
end

local EQUIPMENT_SLOTS = {
    { key = "Head", label = "Head", inventorySlotId = 1, inventorySlotName = "HeadSlot", slots = { "Head" }, column = "left" },
    { key = "Neck", label = "Neck", inventorySlotId = 2, inventorySlotName = "NeckSlot", slots = { "Neck" }, column = "left" },
    { key = "Shoulder", label = "Shoulder", inventorySlotId = 3, inventorySlotName = "ShoulderSlot", slots = { "Shoulder" }, column = "left" },
    { key = "Back", label = "Back", inventorySlotId = 15, inventorySlotName = "BackSlot", slots = { "Back" }, column = "left" },
    { key = "Chest", label = "Chest", inventorySlotId = 5, inventorySlotName = "ChestSlot", slots = { "Chest" }, column = "left" },
    { key = "Wrist", label = "Wrist", inventorySlotId = 9, inventorySlotName = "WristSlot", slots = { "Wrist" }, column = "left" },
    { key = "Hands", label = "Hands", inventorySlotId = 10, inventorySlotName = "HandsSlot", slots = { "Hands" }, column = "left" },
    { key = "Waist", label = "Waist", inventorySlotId = 6, inventorySlotName = "WaistSlot", slots = { "Waist" }, column = "left" },
    { key = "Legs", label = "Legs", inventorySlotId = 7, inventorySlotName = "LegsSlot", slots = { "Legs" }, column = "left" },
    { key = "Feet", label = "Feet", inventorySlotId = 8, inventorySlotName = "FeetSlot", slots = { "Feet" }, column = "left" },
    { key = "Finger0", label = "Finger 1", inventorySlotId = 11, inventorySlotName = "Finger0Slot", slots = { "Ring" }, column = "right" },
    { key = "Finger1", label = "Finger 2", inventorySlotId = 12, inventorySlotName = "Finger1Slot", slots = { "Ring" }, column = "right" },
    { key = "Trinket0", label = "Trinket 1", inventorySlotId = 13, inventorySlotName = "Trinket0Slot", slots = { "Trinket" }, column = "right" },
    { key = "Trinket1", label = "Trinket 2", inventorySlotId = 14, inventorySlotName = "Trinket1Slot", slots = { "Trinket" }, column = "right" },
    { key = "MainHand", label = "Main Hand", inventorySlotId = 16, inventorySlotName = "MainHandSlot", slots = { "Main Hand", "Two Hand", "Dual Wield" }, column = "right" },
    { key = "OffHand", label = "Off Hand", inventorySlotId = 17, inventorySlotName = "SecondaryHandSlot", slots = { "Off Hand", "Dual Wield" }, column = "right" },
    { key = "Ranged", label = "Ranged/Relic", inventorySlotId = 18, inventorySlotName = "RangedSlot", slots = { "Ranged", "Idol", "Totem", "Libram", "Relic" }, column = "right" },
}

local PHASE_SHORT_DISPLAY = {
    PR = "Pre",
    T4 = "P1",
    T5 = "P2",
    T6 = "P3",
    ZA = "P4",
    SWP = "P5",
}

local SOURCE_TYPE_LABELS = {
    all = "All sources",
    drop = "Drops",
    quest = "Quests",
    vendor = "Vendors",
    crafted = "Crafted",
    trade = "Trade/AH",
    pvp = "PvP",
    token_turnin = "Token turn-ins",
    taught_by_item = "Formulae",
    world_drop = "World drops",
    unknown = "Unknown",
}

local SOURCE_TYPE_PREFIXES = {
    drop = "Drop",
    quest = "Quest",
    vendor = "Vendor",
    crafted = "Craft",
    trade = "Trade/AH",
    pvp = "PvP",
    token_turnin = "Token",
    taught_by_item = "Formula",
    world_drop = "World drop",
    unknown = "Source",
}

local CONSUMABLE_CATEGORY_LABELS = {
    battle_elixir = "Battle Elixir",
    guardian_elixir = "Guardian Elixir",
    elixir = "Elixir",
    flask = "Flask",
    potion = "Potion",
    food = "Food",
    weapon_oil = "Weapon Buff",
    scroll = "Scroll",
    drum = "Drum",
    utility = "Utility",
}

local GEM_SOCKET_LABELS = {
    red = "Red gem",
    yellow = "Yellow gem",
    blue = "Blue gem",
    orange = "Orange gem",
    purple = "Purple gem",
    green = "Green gem",
    prismatic = "Prismatic gem",
}

local RANK_GROUP_ORDER = {
    bis = 1,
    ranked = 2,
    situational = 3,
    pvp = 4,
    unrealistic = 5,
    option = 6,
}

BigBiSList.phaseOrder = PHASE_ORDER
BigBiSList.phaseDisplay = PHASE_DISPLAY
BigBiSList.slotOrder = SLOT_ORDER
BigBiSList.displaySlotFilters = DISPLAY_SLOT_FILTERS
BigBiSList.equipmentSlots = EQUIPMENT_SLOTS

local function lower(value)
    return string.lower(tostring(value or ""))
end

local function containsText(value, search)
    if not search or search == "" then
        return true
    end
    return string.find(lower(value), lower(search), 1, true) ~= nil
end

local function tableHasAnyEnabled(values)
    if type(values) ~= "table" then
        return false
    end

    for _, value in pairs(values) do
        if value then
            return true
        end
    end
    return false
end

local function addUnique(list, seen, value)
    if value == nil or value == "" or seen[value] then
        return
    end
    seen[value] = true
    table.insert(list, value)
end

local function addReputationsFromRequirement(reputations, seen, requirement)
    if type(requirement) ~= "table" then
        return
    elseif requirement.type == "reputation" then
        addUnique(reputations, seen, requirement.reputation)
    elseif requirement.type == "faction_choice" then
        for _, reputation in ipairs(requirement.choices or {}) do
            addUnique(reputations, seen, reputation)
        end
    end
end

local function addReputationsFromRequirements(reputations, seen, requirements)
    for _, requirement in ipairs(requirements or {}) do
        addReputationsFromRequirement(reputations, seen, requirement)
    end
end

local function reputationsFromRequirements(requirements)
    local reputations = {}
    local seen = {}
    addReputationsFromRequirements(reputations, seen, requirements)
    table.sort(reputations)
    return reputations
end

local function rowReputations(requirements, accessOptions)
    local reputations = {}
    local seen = {}
    addReputationsFromRequirements(reputations, seen, requirements)
    for _, option in ipairs(accessOptions or {}) do
        addReputationsFromRequirements(reputations, seen, option.requirements)
    end
    table.sort(reputations)
    return reputations
end

local function sortedKeys(values)
    local result = {}
    for key in pairs(values) do
        table.insert(result, key)
    end
    table.sort(result)
    return result
end

local function concatValues(values)
    if type(values) ~= "table" then
        return ""
    end
    local parts = {}
    for _, value in ipairs(values) do
        table.insert(parts, tostring(value))
    end
    return table.concat(parts, "/")
end

local function requirementKey(requirement)
    if type(requirement) ~= "table" then
        return tostring(requirement or "")
    end

    return table.concat({
        tostring(requirement.type or ""),
        tostring(requirement.scope or ""),
        tostring(requirement.confidence or ""),
        tostring(requirement.profession or ""),
        tostring(requirement.skill or ""),
        tostring(requirement.specialization or ""),
        tostring(requirement.reputation or ""),
        tostring(requirement.standing or ""),
        tostring(requirement.standing_rank or ""),
        tostring(requirement.spell_id or ""),
        tostring(requirement.spell_name or ""),
        concatValues(requirement.choices),
        tostring(requirement.raw_text or ""),
        tostring(requirement.source_url or ""),
    }, "|")
end

local function appendUniqueRequirement(result, seen, requirement)
    if type(requirement) ~= "table" then
        return
    end

    local key = requirementKey(requirement)
    if seen[key] then
        return
    end

    seen[key] = true
    table.insert(result, requirement)
end

local function appendRequirements(result, requirements, seen)
    for _, requirement in ipairs(requirements or {}) do
        if seen then
            appendUniqueRequirement(result, seen, requirement)
        else
            table.insert(result, requirement)
        end
    end
end

local function mergedRequirements(...)
    local result = {}
    local seen = {}
    for index = 1, select("#", ...) do
        appendRequirements(result, select(index, ...), seen)
    end
    if #result == 0 then
        return nil
    end
    return result
end

local function splitRequirements(globalRequirements, globalSeen, sourceRequirements, sourceSeen, requirements, options)
    options = options or {}

    for _, requirement in ipairs(requirements or {}) do
        local scope = requirement.scope
        local forceSourceScopedEquip = options.forceSourceScopedEquip
            and scope == "equip_or_use"
            and requirement.source_url
            and string.find(requirement.source_url, "/item=", 1, true)

        if (not forceSourceScopedEquip) and (not scope or scope == "" or scope == "equip_or_use") then
            appendUniqueRequirement(globalRequirements, globalSeen, requirement)
        else
            appendUniqueRequirement(sourceRequirements, sourceSeen, requirement)
        end
    end
end

local function sourceIdentity(source)
    if type(source) ~= "table" then
        return nil
    end

    return table.concat({
        tostring(source.type or ""),
        tostring(source.entity_id or ""),
        tostring(source.item_id or ""),
        tostring(source.spell_id or ""),
        tostring(source.quest_id or ""),
        tostring(source.vendor_id or ""),
        tostring(source.source_url or ""),
        tostring(source.entity_name or ""),
    }, "|")
end

local function idFromUrl(url, key)
    if not url then
        return nil
    end

    local value = string.match(url, key .. "=(%d+)")
    return value and tonumber(value) or nil
end

local function sourceMatchesRequirement(source, requirement)
    if type(source) ~= "table" or type(requirement) ~= "table" then
        return false
    end

    if requirement.source_url and source.source_url and requirement.source_url == source.source_url then
        return true
    end

    local requirementItemId = idFromUrl(requirement.source_url, "item")
    if requirementItemId and (source.item_id == requirementItemId or source.entity_id == requirementItemId) then
        return true
    end

    local requirementSpellId = idFromUrl(requirement.source_url, "spell")
    if requirementSpellId and (source.spell_id == requirementSpellId or source.entity_id == requirementSpellId) then
        return true
    end

    local scope = requirement.scope
    local sourceType = source.type or "unknown"

    if scope == "self_craft" or scope == "learn_recipe" or scope == "cast_enchant" then
        return sourceType == "crafted" or sourceType == "taught_by_item"
    elseif scope == "vendor_purchase" then
        return sourceType == "vendor" or sourceType == "token_turnin" or sourceType == "pvp"
    elseif scope == "quest_reward" then
        return sourceType == "quest"
    elseif scope == "source_access" then
        return true
    end

    return false
end

local function sourceLabel(source, fallbackLabel)
    local sourceType = source and source.type or "unknown"
    local prefix = SOURCE_TYPE_PREFIXES[sourceType] or SOURCE_TYPE_PREFIXES.unknown
    local name = source and (source.entity_name or source.profession)

    if sourceType == "crafted" and source and source.profession then
        name = source.profession
    end

    if name and name ~= "" then
        return prefix .. ": " .. name
    elseif fallbackLabel and fallbackLabel ~= "" then
        return prefix .. ": " .. fallbackLabel
    end

    return prefix
end

local function addSourceInput(inputs, seen, source, isPrimary, fallbackLabel)
    if type(source) ~= "table" then
        return nil
    end

    local key = sourceIdentity(source)
    if not key then
        return nil
    end

    local input = seen[key]
    if not input then
        input = {
            source = source,
            fallbackLabel = fallbackLabel,
            extraRequirements = {},
            extraSeen = {},
        }
        seen[key] = input
        table.insert(inputs, input)
    end

    if isPrimary then
        input.isPrimary = true
    end

    return input
end

local function addSourceRecordInputs(inputs, seen, record, primaryAssigned)
    if type(record) ~= "table" then
        return primaryAssigned
    end

    if record.primary_source then
        local input = addSourceInput(inputs, seen, record.primary_source, not primaryAssigned, record.name)
        if input and not primaryAssigned then
            primaryAssigned = true
        end
    end

    for sourceIndex, source in ipairs(record.sources or {}) do
        local input = addSourceInput(inputs, seen, source, sourceIndex == 1 and not primaryAssigned, record.name)
        if input and sourceIndex == 1 and not primaryAssigned then
            primaryAssigned = true
        end
    end

    return primaryAssigned
end

local function isBindOnPickup(item)
    return item and (item.binding == "bind_on_pickup" or item.boe == false)
end

local function shouldAddTradeOption(item, inputs, options)
    if options and options.alwaysTradeOption then
        return true
    end

    local hasCrafted = false
    for _, input in ipairs(inputs or {}) do
        if input.source and input.source.type == "crafted" then
            hasCrafted = true
            break
        end
    end

    if item and (item.boe == true or item.binding == "bind_on_equip") then
        return true
    end

    return hasCrafted and not isBindOnPickup(item)
end

local function normalizeSourceRecords(sourceRecords)
    if not sourceRecords then
        return {}
    end

    if sourceRecords.sources or sourceRecords.primary_source then
        return { sourceRecords }
    end

    return sourceRecords
end

local function buildAccessOptions(item, sourceRecords, rowRequirements, options)
    options = options or {}
    sourceRecords = normalizeSourceRecords(sourceRecords)

    local globalRequirements = {}
    local globalSeen = {}
    local sourceRequirements = {}
    local sourceSeen = {}
    local inputs = {}
    local inputSeen = {}
    local primaryAssigned = false

    if item then
        primaryAssigned = addSourceRecordInputs(inputs, inputSeen, item, primaryAssigned)
        splitRequirements(globalRequirements, globalSeen, sourceRequirements, sourceSeen, item.requirements, options)
    end

    for _, record in ipairs(sourceRecords) do
        primaryAssigned = addSourceRecordInputs(inputs, inputSeen, record, primaryAssigned)
        splitRequirements(globalRequirements, globalSeen, sourceRequirements, sourceSeen, record.requirements, options)
    end

    splitRequirements(globalRequirements, globalSeen, sourceRequirements, sourceSeen, rowRequirements, options)

    if #inputs == 0 then
        return nil
    end

    if not primaryAssigned and inputs[1] then
        inputs[1].isPrimary = true
    end

    for _, requirement in ipairs(sourceRequirements) do
        local matched = false
        for _, input in ipairs(inputs) do
            if sourceMatchesRequirement(input.source, requirement) then
                appendUniqueRequirement(input.extraRequirements, input.extraSeen, requirement)
                matched = true
            end
        end

        if not matched then
            for _, input in ipairs(inputs) do
                if input.isPrimary then
                    appendUniqueRequirement(input.extraRequirements, input.extraSeen, requirement)
                    matched = true
                    break
                end
            end
        end
    end

    local accessOptions = {}
    for _, input in ipairs(inputs) do
        local source = input.source
        local requirements = mergedRequirements(globalRequirements, source.requirements, input.extraRequirements)
        table.insert(accessOptions, {
            label = sourceLabel(source, input.fallbackLabel),
            source_type = source.type or "unknown",
            zone = source.zone,
            source_url = source.source_url or (item and item.wowhead_url),
            side = source.side,
            requirements = requirements,
            reputations = reputationsFromRequirements(requirements),
            is_primary = input.isPrimary or false,
            is_trade_option = false,
        })
    end

    if shouldAddTradeOption(item, inputs, options) then
        local requirements = mergedRequirements(globalRequirements)
        table.insert(accessOptions, {
            label = options.tradeLabel or "Trade/Auction House",
            source_type = "trade",
            source_url = item and item.wowhead_url or (sourceRecords[1] and sourceRecords[1].source_url),
            requirements = requirements,
            reputations = reputationsFromRequirements(requirements),
            is_primary = false,
            is_trade_option = true,
        })
    end

    return accessOptions
end

local function phaseIndex(phaseKey)
    for index, key in ipairs(PHASE_ORDER) do
        if key == phaseKey then
            return index
        end
    end
    return 999
end

local function slotIndex(slotName)
    for index, name in ipairs(SLOT_ORDER) do
        if name == slotName then
            return index
        end
    end
    return 999
end

local sortUses

local function slotListContains(slots, slotName)
    for _, value in ipairs(slots or {}) do
        if value == slotName then
            return true
        end
    end
    return false
end

local function slotMatchesDisplayFilter(filterKey, rowSlot)
    local slots = DISPLAY_SLOT_FILTER_MAP[filterKey]
    if slots then
        return slotListContains(slots, rowSlot)
    end

    return filterKey == rowSlot
end

local function rowMatchesSelectedSlots(rowSlot, selectedSlots)
    if not tableHasAnyEnabled(selectedSlots) then
        return true
    end

    for filterKey, selected in pairs(selectedSlots or {}) do
        if selected and slotMatchesDisplayFilter(filterKey, rowSlot) then
            return true
        end
    end

    return false
end

local function rankShortLabel(use)
    if not use then
        return "No match"
    elseif use.rank_group == "bis" then
        return "BiS"
    elseif use.rank_group == "ranked" then
        return "Alt"
    elseif use.rank_group == "situational" then
        return "Sidegrade"
    elseif use.rank_group == "pvp" then
        return "PvP"
    elseif use.rank_group == "unrealistic" then
        return "Hard Farm"
    end
    return "Nice-to-have"
end

local function displayRankInfo(use)
    if not use then
        return "No match", "missing"
    end

    local rank = tonumber(use.rank)
    if use.rank_group == "bis" then
        return "BiS", "best"
    elseif use.rank_group == "ranked" then
        return "Alt", "ranked"
    elseif use.rank_group == "situational" then
        return "Sidegrade", "situational"
    elseif use.rank_group == "pvp" then
        return "PvP", "pvp"
    elseif use.rank_group == "unrealistic" then
        return "Hard Farm", "hard"
    elseif rank and rank > 1 then
        return "Alt", "ranked"
    end

    return "Nice-to-have", "backup"
end

local function recommendationSummary(use)
    if not use then
        return "No recommendation available"
    end

    if use.note and use.note ~= "" then
        return use.note
    end

    local phaseLabel = PHASE_DISPLAY[use.phase] or tostring(use.phase or "this phase")
    if use.rank_group == "bis" then
        return "BiS for " .. phaseLabel
    elseif use.rank_group == "ranked" then
        return "Alt for " .. phaseLabel
    elseif use.rank_group == "situational" then
        return "Sidegrade for a specific fight, role, or gearing setup"
    elseif use.rank_group == "pvp" then
        return "PvP option"
    elseif use.rank_group == "unrealistic" then
        return "Hard Farm with unusual access"
    end

    return "Nice-to-have alternate"
end

local function isBetterGearUse(candidate, current, preferredPhaseKey)
    if not current then
        return true
    end

    local candidatePreferred = candidate.phase == preferredPhaseKey
    local currentPreferred = current.phase == preferredPhaseKey
    if candidatePreferred ~= currentPreferred then
        return candidatePreferred
    end

    local candidateRank = RANK_GROUP_ORDER[candidate.rank_group] or 50
    local currentRank = RANK_GROUP_ORDER[current.rank_group] or 50
    if candidateRank ~= currentRank then
        return candidateRank < currentRank
    end

    local preferredIndex = phaseIndex(preferredPhaseKey)
    local candidateFuture = candidate.phaseIndex >= preferredIndex
    local currentFuture = current.phaseIndex >= preferredIndex
    if candidateFuture ~= currentFuture then
        return candidateFuture
    end

    if candidate.phaseIndex ~= current.phaseIndex then
        if candidateFuture then
            return candidate.phaseIndex < current.phaseIndex
        end
        return candidate.phaseIndex > current.phaseIndex
    end

    return sortUses(candidate, current)
end

local function ensurePath(root, key)
    root[key] = root[key] or {}
    return root[key]
end

local function getPrimarySource(item)
    if not item then
        return nil
    end
    if item.primary_source then
        return item.primary_source
    end
    if item.sources and item.sources[1] then
        return item.sources[1]
    end
    return nil
end

local function getSourceType(item)
    local source = getPrimarySource(item)
    if source and source.type then
        return source.type
    end
    return "unknown"
end

local function getSourceZone(item)
    local source = getPrimarySource(item)
    if source and source.zone and source.zone ~= "" then
        return source.zone
    end
    return nil
end

local function addSourceZone(zones, seen, zone)
    if zone and zone ~= "" then
        addUnique(zones, seen, zone)
    end
end

local function addZonesFromSource(zones, seen, source, includeDropZone)
    if type(source) ~= "table" then
        return
    end

    if source.type ~= "drop" or includeDropZone then
        addSourceZone(zones, seen, source.zone)
    end

    if source.type == "token_turnin" then
        for _, tokenSource in ipairs(source.token_sources or {}) do
            addSourceZone(zones, seen, tokenSource.zone)
        end
    end
end

local function getSourceZones(item)
    local zones = {}
    local seen = {}

    if item then
        addZonesFromSource(zones, seen, item.primary_source, true)
        for _, source in ipairs(item.sources or {}) do
            addZonesFromSource(zones, seen, source, false)
        end
    end

    return zones
end

local function addSourceSide(sides, seen, side)
    if side == "Alliance" or side == "Horde" then
        addUnique(sides, seen, side)
    end
end

local function addSidesFromSource(sides, seen, source)
    if type(source) == "table" then
        addSourceSide(sides, seen, source.side)
    end
end

local function getSourceSides(item)
    local sides = {}
    local seen = {}

    if item then
        addSidesFromSource(sides, seen, item.primary_source)
        for _, source in ipairs(item.sources or {}) do
            addSidesFromSource(sides, seen, source)
        end
    end

    table.sort(sides)
    return sides
end

local function getAcquisitionPhase(item)
    return item and item.acquisition_phase or "PR"
end

local function getSourceSide(item)
    local source = getPrimarySource(item)
    if source and source.side and source.side ~= "" then
        return source.side
    end
    return nil
end

local function getItemName(itemId, item)
    if item and item.name and item.name ~= "" then
        return item.name
    end
    return "Item " .. tostring(itemId)
end

local function consumableCategoryLabel(category)
    return CONSUMABLE_CATEGORY_LABELS[category or ""] or tostring(category or "Consumable")
end

local function consumableDetailLabel(consumable, itemIndex)
    local category = consumable and consumable.category
    if itemIndex and consumable and consumable.item_categories then
        category = consumable.item_categories[itemIndex] or category
    end
    return consumableCategoryLabel(category)
end

local function gemDetailLabel(gem)
    if gem and gem.meta then
        return "Meta gem"
    end
    local socketCategory = lower(gem and gem.socket_category)
    return GEM_SOCKET_LABELS[socketCategory] or "Gem"
end

local function enchantDetailLabel(enchant)
    if enchant and enchant.slot and enchant.slot ~= "" then
        return enchant.slot .. " enchant"
    end
    return "Enchant"
end

local function enchantRecommendationSummary(enchant)
    if enchant and enchant.slot and enchant.slot ~= "" then
        return "Apply to " .. enchant.slot
    end
    return "Apply this enchant"
end

local function consumableRecommendationSummary(consumable, grouped, itemIndex)
    local detail = consumableDetailLabel(consumable, itemIndex)
    if grouped then
        return "Choose one " .. lower(detail)
    end
    if consumable and consumable.category == "flask" then
        return "Use one flask"
    end
    return "Bring for raid"
end

local function consumableCanGroupAlternatives(consumable, itemIds)
    if not consumable or consumable.relationship ~= "or" or #(itemIds or {}) <= 1 then
        return false
    end

    local firstCategory
    for itemIndex in ipairs(itemIds) do
        local category = consumable.item_categories and consumable.item_categories[itemIndex] or consumable.category
        if itemIndex == 1 then
            firstCategory = category
        elseif category ~= firstCategory then
            return false
        end
    end

    return true
end

local function consumableDisplayName(consumable, itemIds, index)
    if consumable and consumable.text and consumable.text ~= "" then
        return consumable.text
    end

    local names = {}
    for itemIndex, itemId in ipairs(itemIds or {}) do
        local item = index.itemsById[itemId]
        names[itemIndex] = consumable.item_names and consumable.item_names[itemIndex] or getItemName(itemId, item)
    end

    local separator = consumable and consumable.relationship == "or" and " or " or " and "
    return table.concat(names, separator)
end

local function consumableSourceSummary(consumable, itemIds)
    local summaries = {}
    local seen = {}
    for _, itemId in ipairs(itemIds or {}) do
        local summary = consumable.source_summaries and consumable.source_summaries[tostring(itemId)] or ""
        if summary ~= "" and not seen[summary] then
            seen[summary] = true
            table.insert(summaries, summary)
        end
    end
    return table.concat(summaries, " / ")
end

local function appendAccessOptions(result, options)
    for _, option in ipairs(options or {}) do
        table.insert(result, option)
    end
end

local function buildConsumableAccessOptions(index, itemIds)
    local accessOptions = {}
    for _, itemId in ipairs(itemIds or {}) do
        local item = index.itemsById[itemId]
        appendAccessOptions(accessOptions, buildAccessOptions(item, nil, nil, { entityType = "item" }))
    end
    if #accessOptions == 0 then
        return nil
    end
    return accessOptions
end

local function enhancementSourceKey(entityType, entityId)
    return tostring(entityType or "item") .. ":" .. tostring(entityId or "")
end

local function buildUse(index, className, specName, phaseKey, slotEntry, itemEntry)
    local itemId = itemEntry.item_id
    local item = index.itemsById[itemId]
    local sourceType = getSourceType(item)
    local zone = getSourceZone(item)
    local zones = getSourceZones(item)
    local sides = getSourceSides(item)
    local acquisitionPhase = getAcquisitionPhase(item)
    local requirements = mergedRequirements(item and item.requirements, itemEntry.requirements)
    local accessOptions = buildAccessOptions(item, nil, itemEntry.requirements, { entityType = "item" })

    local row = {
        class = className,
        spec = specName,
        phase = phaseKey,
        phaseIndex = phaseIndex(phaseKey),
        slot = slotEntry.slot,
        item_id = itemId,
        item = item,
        name = getItemName(itemId, item),
        rank = itemEntry.rank,
        rank_label = itemEntry.rank_label or "Option",
        rank_group = itemEntry.rank_group or "option",
        context = itemEntry.context or "standard",
        note = itemEntry.note,
        source_url = slotEntry.source_url,
        source_summary = item and item.source_summary or "",
        source_type = sourceType,
        source_type_label = SOURCE_TYPE_LABELS[sourceType] or sourceType,
        acquisition_phase = acquisitionPhase,
        acquisitionPhaseIndex = phaseIndex(acquisitionPhase),
        zone = zone,
        zones = zones,
        side = getSourceSide(item),
        sides = sides,
        binding = item and item.binding or "unknown",
        boe = item and item.boe,
        quality = item and item.quality,
        requirements = requirements,
        access_options = accessOptions,
        reputations = rowReputations(requirements, accessOptions),
    }

    row.display_rank_label, row.display_rank_kind = displayRankInfo(row)
    row.recommendation_summary = recommendationSummary(row)
    return row
end

local function rowHasZone(row, zone)
    if not row or not zone or zone == "" then
        return false
    end

    if row.zone == zone then
        return true
    end

    for _, rowZone in ipairs(row.zones or {}) do
        if rowZone == zone then
            return true
        end
    end

    return false
end

local function rowMatchesZoneFilter(row, zone)
    if not zone or zone == "all" then
        return true
    end
    return rowHasZone(row, zone)
end

local function rowMatchesAnySelectedZone(row, selectedZones)
    if not tableHasAnyEnabled(selectedZones) then
        return true
    end

    for zone, selected in pairs(selectedZones or {}) do
        if selected and rowHasZone(row, zone) then
            return true
        end
    end

    return false
end

local function rowHasReputation(row, reputation)
    if not row or not reputation or reputation == "" then
        return false
    end

    for _, rowReputation in ipairs(row.reputations or {}) do
        if rowReputation == reputation then
            return true
        end
    end

    return false
end

local function rowMatchesReputationFilter(row, reputation)
    if not reputation or reputation == "all" then
        return true
    end
    return rowHasReputation(row, reputation)
end

local function rowMatchesFactionFilter(row, faction)
    if not faction or faction == "all" then
        return true
    end

    local hasSide = false
    for _, side in ipairs(row.sides or {}) do
        hasSide = true
        if side == faction then
            return true
        end
    end

    if not hasSide and row.side then
        return row.side == faction
    end

    return not hasSide
end

local function includeByFilter(row, filters)
    filters = filters or {}

    if filters.hideIgnored and filters.ignoredItems and filters.ignoredItems[tostring(row.item_id)] then
        return false
    end

    if filters.search and filters.search ~= "" then
        local found = containsText(row.name, filters.search)
            or containsText(row.slot, filters.search)
            or containsText(row.source_summary, filters.search)
            or containsText(row.rank_label, filters.search)
        if not found then
            return false
        end
    end

    if not rowMatchesSelectedSlots(row.slot, filters.slots) then
        return false
    end

    if filters.sourceType and filters.sourceType ~= "all" and row.source_type ~= filters.sourceType then
        return false
    end
    if tableHasAnyEnabled(filters.sourceTypes) and not filters.sourceTypes[row.source_type] then
        return false
    end

    if not rowMatchesZoneFilter(row, filters.zone) then
        return false
    end
    if not rowMatchesAnySelectedZone(row, filters.zones) then
        return false
    end

    if not rowMatchesReputationFilter(row, filters.reputation) then
        return false
    end

    if filters.rankGroup and filters.rankGroup ~= "all" and row.rank_group ~= filters.rankGroup then
        return false
    end
    if tableHasAnyEnabled(filters.rankGroups) and not filters.rankGroups[row.rank_group] then
        return false
    end

    local owned = filters.ownedItems and filters.ownedItems[row.item_id]
    if filters.ownedState == "owned" and not owned then
        return false
    elseif filters.ownedState == "missing" and owned then
        return false
    elseif filters.ownedState == "equipped" and owned ~= "equipped" then
        return false
    elseif filters.ownedState == "bag" and owned ~= "bag" then
        return false
    elseif filters.ownedState == "bank" and owned ~= "bank" then
        return false
    end

    if filters.binding and filters.binding ~= "all" and row.binding ~= filters.binding then
        return false
    end

    if filters.boe == "boe" and row.boe ~= true then
        return false
    elseif filters.boe == "not_boe" and row.boe == true then
        return false
    end

    if not rowMatchesFactionFilter(row, filters.faction) then
        return false
    end

    return true
end

function sortUses(a, b)
    local aRank = RANK_GROUP_ORDER[a.rank_group] or 50
    local bRank = RANK_GROUP_ORDER[b.rank_group] or 50
    if aRank ~= bRank then
        return aRank < bRank
    end
    if (a.rank or 999) ~= (b.rank or 999) then
        return (a.rank or 999) < (b.rank or 999)
    end
    return lower(a.name) < lower(b.name)
end

local function addPlannerReason(reasons, seen, text)
    if not seen[text] then
        seen[text] = true
        table.insert(reasons, text)
    end
end

local function plannerTier(score)
    if score >= 75 then
        return "BiS Now"
    elseif score >= 55 then
        return "Future BiS"
    elseif score >= 30 then
        return "Alt"
    end
    return "Nice-to-have"
end

local function plannerRecommendationTier(score)
    if score >= 75 then
        return "chase_first"
    elseif score >= 55 then
        return "strong_targets"
    elseif score >= 30 then
        return "useful_backups"
    end
    return "only_if_easy"
end

local function scorePlannerGroup(group, selectedPhaseKey)
    local selectedIndex = phaseIndex(selectedPhaseKey)
    local score = 0
    local hasCurrent = false
    local hasCurrentBis = false
    local firstFutureBis
    local futureBisCount = 0
    local futureOptionCount = 0
    local lastUsefulIndex = 0
    local reasons = {}
    local reasonSeen = {}

    for _, use in ipairs(group.uses) do
        if use.phaseIndex > lastUsefulIndex and use.phaseIndex < 999 then
            lastUsefulIndex = use.phaseIndex
        end

        if use.phase == selectedPhaseKey then
            hasCurrent = true
            if use.rank_group == "bis" then
                hasCurrentBis = true
            end
        elseif use.phaseIndex > selectedIndex then
            if use.rank_group == "bis" then
                futureBisCount = futureBisCount + 1
                if not firstFutureBis or use.phaseIndex < firstFutureBis then
                    firstFutureBis = use.phaseIndex
                end
            else
                futureOptionCount = futureOptionCount + 1
            end
        end
    end

    if hasCurrentBis then
        score = score + 60
        addPlannerReason(reasons, reasonSeen, "BiS Now")
    elseif hasCurrent then
        score = score + 30
        addPlannerReason(reasons, reasonSeen, "Alt now")
    elseif firstFutureBis then
        score = score + 35
        addPlannerReason(reasons, reasonSeen, "Future BiS " .. (PHASE_DISPLAY[PHASE_ORDER[firstFutureBis]] or "future phase"))
    end

    score = score + (futureBisCount * 8)
    score = score + (futureOptionCount * 4)

    if futureBisCount > 0 then
        addPlannerReason(reasons, reasonSeen, tostring(futureBisCount) .. " future BiS")
    end
    if futureOptionCount > 0 then
        addPlannerReason(reasons, reasonSeen, tostring(futureOptionCount) .. " future alts")
    end

    if lastUsefulIndex > selectedIndex then
        if lastUsefulIndex >= selectedIndex + 2 then
            score = score + 10
        else
            score = score + 5
        end
        addPlannerReason(reasons, reasonSeen, "Listed through " .. (PHASE_DISPLAY[PHASE_ORDER[lastUsefulIndex]] or "future phase"))
    end

    if score > 100 then
        score = 100
    end

    group.priority = score
    group.priorityTier = plannerTier(score)
    group.recommendation_tier = plannerRecommendationTier(score)
    group.reasons = reasons
    group.hasCurrent = hasCurrent
    group.hasCurrentBis = hasCurrentBis
    group.lastUsefulPhase = PHASE_ORDER[lastUsefulIndex] or group.bestUse.phase
    group.lastUsefulLabel = PHASE_DISPLAY[group.lastUsefulPhase] or group.lastUsefulPhase
    group.recommendation_summary = reasons[1] or recommendationSummary(group.bestUse)
end

function BigBiSList:GetPhaseDisplayName(phaseKey)
    return PHASE_DISPLAY[phaseKey] or tostring(phaseKey or "")
end

function BigBiSList:GetPhaseOrder()
    return PHASE_ORDER
end

function BigBiSList:GetSlotOrder()
    return SLOT_ORDER
end

function BigBiSList:GetDisplaySlotFilters()
    return DISPLAY_SLOT_FILTERS
end

function BigBiSList:GetEquipmentSlotDefinitions()
    return EQUIPMENT_SLOTS
end

function BigBiSList:GetPhaseShortName(phaseKey)
    return PHASE_SHORT_DISPLAY[phaseKey] or self:GetPhaseDisplayName(phaseKey)
end

function BigBiSList:GetSourceTypeLabels()
    return SOURCE_TYPE_LABELS
end

function BigBiSList:GetDataIndex()
    if self.dataIndex then
        return self.dataIndex
    end

    local data = BigBiSListData or {}
    local index = {
        itemsById = {},
        classes = data.classes or {},
        classNames = {},
        specsByClass = {},
        phaseOrder = PHASE_ORDER,
        phaseDisplay = PHASE_DISPLAY,
        sourceTypes = {},
        zones = {},
        lists = {},
        usesByItemId = {},
        enhancement = {
            gems = data.gems or {},
            gemSourcesById = {},
            enchants = data.enchants or {},
            enchantSourcesByKey = {},
            consumables = data.consumables or {},
        },
    }

    local sourceSeen = {}
    local zoneSeen = {}

    for _, item in ipairs(data.items or {}) do
        index.itemsById[item.id] = item
        addUnique(index.sourceTypes, sourceSeen, getSourceType(item))
        for _, zone in ipairs(getSourceZones(item)) do
            addUnique(index.zones, zoneSeen, zone)
        end
    end

    for _, sourceData in ipairs(data.gem_sources or {}) do
        index.enhancement.gemSourcesById[sourceData.id] = sourceData
    end

    for _, sourceData in ipairs(data.enchant_sources or {}) do
        local key = enhancementSourceKey(sourceData.type or "item", sourceData.id)
        index.enhancement.enchantSourcesByKey[key] = index.enhancement.enchantSourcesByKey[key] or {}
        table.insert(index.enhancement.enchantSourcesByKey[key], sourceData)
    end

    table.sort(index.sourceTypes)
    table.sort(index.zones)

    for _, classData in ipairs(index.classes) do
        table.insert(index.classNames, classData.name)
        index.specsByClass[classData.name] = classData.specs or {}
    end

    for _, classData in ipairs(data.bis_lists or {}) do
        local className = classData["class"]
        local classLists = ensurePath(index.lists, className)

        for _, specData in ipairs(classData.specs or {}) do
            local specName = specData.spec
            local specLists = ensurePath(classLists, specName)

            for _, phaseData in ipairs(specData.phases or {}) do
                local phaseKey = phaseData.phase
                specLists[phaseKey] = specLists[phaseKey] or {}

                for _, slotEntry in ipairs(phaseData.slots or {}) do
                    table.insert(specLists[phaseKey], slotEntry)

                    for _, itemEntry in ipairs(slotEntry.items or {}) do
                        if itemEntry.item_id then
                            local use = buildUse(index, className, specName, phaseKey, slotEntry, itemEntry)
                            index.usesByItemId[use.item_id] = index.usesByItemId[use.item_id] or {}
                            table.insert(index.usesByItemId[use.item_id], use)
                        end
                    end
                end
            end
        end
    end

    for _, uses in pairs(index.usesByItemId) do
        table.sort(uses, function(a, b)
            if a.class ~= b.class then
                return a.class < b.class
            end
            if a.spec ~= b.spec then
                return a.spec < b.spec
            end
            if a.phaseIndex ~= b.phaseIndex then
                return a.phaseIndex < b.phaseIndex
            end
            return sortUses(a, b)
        end)
    end

    self.dataIndex = index
    return index
end

function BigBiSList:GetItemData(itemId)
    return self:GetDataIndex().itemsById[itemId]
end

function BigBiSList:GetItemBestUseForSpec(itemId, className, specName, preferredPhaseKey, allowedSlots)
    local uses = self:GetDataIndex().usesByItemId[itemId] or {}
    local bestUse

    for _, use in ipairs(uses) do
        if use.class == className
            and use.spec == specName
            and (not allowedSlots or slotListContains(allowedSlots, use.slot))
            and isBetterGearUse(use, bestUse, preferredPhaseKey) then
            bestUse = use
        end
    end

    return bestUse
end

function BigBiSList:GetEquippedGearRows(className, specName, phaseKey, ownedItems)
    local rows = {}
    local equippedSlots = ownedItems and ownedItems.equippedSlots or {}

    for _, slot in ipairs(EQUIPMENT_SLOTS) do
        local equipped = equippedSlots[slot.key]
        local itemId = equipped and equipped.item_id
        local item = itemId and self:GetItemData(itemId) or nil
        local bestUse = itemId and self:GetItemBestUseForSpec(itemId, className, specName, phaseKey, slot.slots) or nil
        local overlay = "Empty"
        local overlayKind = "empty"
        local disabledReason

        if itemId and bestUse then
            overlay = bestUse.rank_group == "bis" and "BiS match" or "Listed alt"
            overlayKind = bestUse.rank_group or "option"
        elseif itemId then
            overlay = "Off-list"
            overlayKind = "missing"
        elseif slot.key == "OffHand" and ownedItems and ownedItems.equippedTwoHand then
            overlay = "2H equipped"
            overlayKind = "disabled"
            disabledReason = "Two-handed weapon equipped"
        end

        local displayRankLabel, displayRankKind = displayRankInfo(bestUse)
        local recommendation = "Empty slot"
        if itemId and bestUse then
            recommendation = bestUse.rank_group == "bis" and "BiS match for selected spec" or "Listed alt for selected spec"
        elseif itemId then
            recommendation = "Off-list for selected spec"
        elseif disabledReason then
            recommendation = disabledReason
        end

        table.insert(rows, {
            slotKey = slot.key,
            slot = slot.label,
            inventorySlotId = slot.inventorySlotId,
            item_id = itemId,
            item = item,
            name = item and item.name or (itemId and ("Item " .. tostring(itemId)) or "Empty"),
            source_summary = item and item.source_summary or "",
            bestUse = bestUse,
            phase = bestUse and bestUse.phase or nil,
            rank_label = bestUse and bestUse.rank_label or nil,
            rank_group = bestUse and bestUse.rank_group or nil,
            overlay = overlay,
            overlayKind = overlayKind,
            disabledReason = disabledReason,
            column = slot.column,
            dataSlots = slot.slots,
            requirements = mergedRequirements(bestUse and bestUse.requirements, item and item.requirements),
            access_options = bestUse and bestUse.access_options or buildAccessOptions(item, nil, nil, { entityType = "item" }),
            display_rank_label = itemId and displayRankLabel or "Empty",
            display_rank_kind = itemId and displayRankKind or "missing",
            recommendation_summary = recommendation,
        })
    end

    return rows
end

function BigBiSList:GetPhaseRows(className, specName, phaseKey, filters)
    local index = self:GetDataIndex()
    local phaseLists = index.lists[className]
        and index.lists[className][specName]
        and index.lists[className][specName][phaseKey]
    local grouped = {}
    local seenBySlot = {}

    if not phaseLists then
        return {}
    end

    for _, slotEntry in ipairs(phaseLists) do
        local slotName = slotEntry.slot
        grouped[slotName] = grouped[slotName] or { slot = slotName, items = {} }
        seenBySlot[slotName] = seenBySlot[slotName] or {}

        for _, itemEntry in ipairs(slotEntry.items or {}) do
            if itemEntry.item_id then
                local use = buildUse(index, className, specName, phaseKey, slotEntry, itemEntry)
                local key = tostring(use.item_id) .. ":" .. tostring(use.rank_group) .. ":" .. tostring(use.context)
                if not seenBySlot[slotName][key] and includeByFilter(use, filters) then
                    seenBySlot[slotName][key] = true
                    table.insert(grouped[slotName].items, use)
                end
            end
        end
    end

    local rows = {}
    for _, slotName in ipairs(SLOT_ORDER) do
        if grouped[slotName] and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, sortUses)
            table.insert(rows, grouped[slotName])
        end
    end

    for _, slotName in ipairs(sortedKeys(grouped)) do
        if slotIndex(slotName) == 999 and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, sortUses)
            table.insert(rows, grouped[slotName])
        end
    end

    return rows
end

function BigBiSList:GetPlannerRows(className, specName, selectedPhaseKey, filters)
    local index = self:GetDataIndex()
    local groups = {}
    local selectedIndex = phaseIndex(selectedPhaseKey)

    for itemId, uses in pairs(index.usesByItemId) do
        for _, use in ipairs(uses) do
            if use.class == className and use.spec == specName then
                local groupKey = tostring(itemId) .. ":" .. use.slot
                local group = groups[groupKey]
                if not group then
                    group = {
                        item_id = itemId,
                        item = use.item,
                        name = use.name,
                        slot = use.slot,
                        source_summary = use.source_summary,
                        source_type = use.source_type,
                        source_type_label = use.source_type_label,
                        acquisition_phase = use.acquisition_phase,
                        acquisitionPhaseIndex = use.acquisitionPhaseIndex,
                        zone = use.zone,
                        zones = use.zones,
                        binding = use.binding,
                        boe = use.boe,
                        side = use.side,
                        sides = use.sides,
                        reputations = use.reputations,
                        requirements = use.requirements,
                        access_options = use.access_options,
                        uses = {},
                        phases = {},
                        bestUse = use,
                    }
                    groups[groupKey] = group
                end

                table.insert(group.uses, use)
                group.phases[use.phase] = group.phases[use.phase] or {}
                table.insert(group.phases[use.phase], use)

                if sortUses(use, group.bestUse) then
                    group.bestUse = use
                end
            end
        end
    end

    local rows = {}
    for _, group in pairs(groups) do
        table.sort(group.uses, function(a, b)
            if a.phaseIndex ~= b.phaseIndex then
                return a.phaseIndex < b.phaseIndex
            end
            return sortUses(a, b)
        end)

        scorePlannerGroup(group, selectedPhaseKey)
        group.rank_group = group.bestUse and group.bestUse.rank_group or "option"
        group.rank_label = group.bestUse and group.bestUse.rank_label or "Option"
        group.display_rank_label = group.priorityTier or "Priority"
        group.display_rank_kind = group.recommendation_tier or "only_if_easy"
        group.sides = group.bestUse and group.bestUse.sides or group.sides
        group.reputations = group.bestUse and group.bestUse.reputations or group.reputations
        group.requirements = group.bestUse and group.bestUse.requirements or group.requirements
        group.access_options = group.bestUse and group.bestUse.access_options or group.access_options

        if group.priority > 0 and group.acquisitionPhaseIndex <= selectedIndex and includeByFilter(group, filters) then
            if filters and filters.longevity == "current" and not group.hasCurrent then
                -- excluded below
            elseif filters and filters.longevity == "future" and group.lastUsefulPhase == selectedPhaseKey then
                -- excluded below
            elseif filters and filters.longevity == "long" and phaseIndex(group.lastUsefulPhase) < selectedIndex + 2 then
                -- excluded below
            else
                table.insert(rows, group)
            end
        end
    end

    table.sort(rows, function(a, b)
        if a.priority ~= b.priority then
            return a.priority > b.priority
        end
        if slotIndex(a.slot) ~= slotIndex(b.slot) then
            return slotIndex(a.slot) < slotIndex(b.slot)
        end
        return lower(a.name) < lower(b.name)
    end)

    return rows
end

local function cloneFiltersForZoneOptions(filters)
    local scopedFilters = {}
    for key, value in pairs(filters or {}) do
        scopedFilters[key] = value
    end
    scopedFilters.zone = "all"
    scopedFilters.zones = nil
    return scopedFilters
end

local function cloneFiltersForReputationOptions(filters)
    local scopedFilters = {}
    for key, value in pairs(filters or {}) do
        scopedFilters[key] = value
    end
    scopedFilters.reputation = "all"
    return scopedFilters
end

local function cloneFiltersForSourceTypeOptions(filters)
    local scopedFilters = {}
    for key, value in pairs(filters or {}) do
        scopedFilters[key] = value
    end
    scopedFilters.sourceType = "all"
    scopedFilters.sourceTypes = nil
    return scopedFilters
end

local function addSourceTypeFromRow(sourceTypes, seen, row)
    if type(row) ~= "table" then
        return
    end

    addUnique(sourceTypes, seen, row.source_type)
end

function BigBiSList:GetAvailableFilterSourceTypes(className, specName, phaseKey, tabName, filters)
    local sourceTypes = {}
    local seen = {}
    local scopedFilters = cloneFiltersForSourceTypeOptions(filters)

    if tabName == "Planner" or tabName == "Upgrades" then
        for _, row in ipairs(self:GetPlannerRows(className, specName, phaseKey, scopedFilters)) do
            addSourceTypeFromRow(sourceTypes, seen, row)
        end
    else
        for _, group in ipairs(self:GetPhaseRows(className, specName, phaseKey, scopedFilters)) do
            for _, row in ipairs(group.items or {}) do
                addSourceTypeFromRow(sourceTypes, seen, row)
            end
        end
    end

    table.sort(sourceTypes)
    return sourceTypes
end

local function addZonesFromRow(zones, seen, row)
    if type(row) ~= "table" then
        return
    end

    addSourceZone(zones, seen, row.zone)
    for _, zone in ipairs(row.zones or {}) do
        addSourceZone(zones, seen, zone)
    end
end

function BigBiSList:GetAvailableFilterZones(className, specName, phaseKey, tabName, filters)
    local zones = {}
    local seen = {}
    local scopedFilters = cloneFiltersForZoneOptions(filters)

    if tabName == "Planner" or tabName == "Upgrades" then
        for _, row in ipairs(self:GetPlannerRows(className, specName, phaseKey, scopedFilters)) do
            addZonesFromRow(zones, seen, row)
        end
    else
        for _, group in ipairs(self:GetPhaseRows(className, specName, phaseKey, scopedFilters)) do
            for _, row in ipairs(group.items or {}) do
                addZonesFromRow(zones, seen, row)
            end
        end
    end

    table.sort(zones)
    return zones
end

local function addReputationsFromRow(reputations, seen, row)
    if type(row) ~= "table" then
        return
    end

    for _, reputation in ipairs(row.reputations or {}) do
        addUnique(reputations, seen, reputation)
    end
end

function BigBiSList:GetAvailableFilterReputations(className, specName, phaseKey, tabName, filters)
    local reputations = {}
    local seen = {}
    local scopedFilters = cloneFiltersForReputationOptions(filters)

    if tabName == "Planner" or tabName == "Upgrades" then
        for _, row in ipairs(self:GetPlannerRows(className, specName, phaseKey, scopedFilters)) do
            addReputationsFromRow(reputations, seen, row)
        end
    else
        for _, group in ipairs(self:GetPhaseRows(className, specName, phaseKey, scopedFilters)) do
            for _, row in ipairs(group.items or {}) do
                addReputationsFromRow(reputations, seen, row)
            end
        end
    end

    table.sort(reputations)
    return reputations
end

function BigBiSList:GetEnhancementRows(className, specName, phaseKey)
    local index = self:GetDataIndex()
    local sections = {
        { title = "Gems", rows = {} },
        { title = "Enchants", rows = {} },
        { title = "Consumables", rows = {} },
    }

    for _, gem in ipairs(index.enhancement.gems or {}) do
        if gem["class"] == className and gem.spec == specName and gem.phase == phaseKey then
            local item = index.itemsById[gem.id]
            local sourceData = index.enhancement.gemSourcesById[gem.id]
            table.insert(sections[1].rows, {
                entity_type = "item",
                entity_id = gem.id,
                item_id = gem.id,
                item = item,
                name = gem.name,
                detail = gemDetailLabel(gem),
                source_summary = gem.source_summary or "",
                requirements = mergedRequirements(gem.requirements, item and item.requirements),
                access_options = buildAccessOptions(item, sourceData, gem.requirements, { entityType = "item" }),
                recommendation_summary = "Socket this gem",
            })
        end
    end

    for _, enchant in ipairs(index.enhancement.enchants or {}) do
        if enchant["class"] == className and enchant.spec == specName and enchant.phase == phaseKey then
            local entityType = enchant.type or "item"
            local row = {
                entity_type = entityType,
                entity_id = enchant.id,
                name = enchant.name,
                detail = enchantDetailLabel(enchant),
                source_summary = enchant.source_summary or "",
                slot = enchant.slot,
                recommendation_summary = enchantRecommendationSummary(enchant),
            }

            if entityType == "spell" then
                row.spell_id = enchant.id
                row.ownership_state = "service"
                row.ownership_label = "No item"
                row.ownership_detail = "Spell enchant; find an enchanter or use your own profession."
            else
                row.item_id = enchant.id
                row.item = index.itemsById[enchant.id]
            end

            row.requirements = mergedRequirements(enchant.requirements, row.item and row.item.requirements)
            row.access_options = buildAccessOptions(row.item, index.enhancement.enchantSourcesByKey[enhancementSourceKey(entityType, enchant.id)], enchant.requirements, {
                entityType = entityType,
                forceSourceScopedEquip = entityType == "spell",
                alwaysTradeOption = entityType == "spell",
                tradeLabel = entityType == "spell" and "Trade enchant service" or "Trade/Auction House",
            })

            table.insert(sections[2].rows, row)
        end
    end

    for _, consumable in ipairs(index.enhancement.consumables or {}) do
        if consumable["class"] == className and consumable.spec == specName and consumable.phase == phaseKey then
            local itemIds = consumable.items or {}
            if consumableCanGroupAlternatives(consumable, itemIds) then
                local primaryItemId = itemIds[1]
                local primaryItem = index.itemsById[primaryItemId]
                table.insert(sections[3].rows, {
                    entity_type = "item",
                    entity_id = primaryItemId,
                    item_id = primaryItemId,
                    item_ids = itemIds,
                    item = primaryItem,
                    name = consumableDisplayName(consumable, itemIds, index),
                    detail = consumableDetailLabel(consumable),
                    source_summary = consumableSourceSummary(consumable, itemIds),
                    access_options = buildConsumableAccessOptions(index, itemIds),
                    recommendation_summary = consumableRecommendationSummary(consumable, true),
                })
            else
                for itemIndex, itemId in ipairs(itemIds) do
                    local item = index.itemsById[itemId]
                    table.insert(sections[3].rows, {
                        entity_type = "item",
                        entity_id = itemId,
                        item_id = itemId,
                        item = item,
                        name = consumable.item_names and consumable.item_names[itemIndex] or getItemName(itemId, item),
                        detail = consumableDetailLabel(consumable, itemIndex),
                        source_summary = consumableSourceSummary(consumable, { itemId }),
                        requirements = mergedRequirements(consumable.requirements, item and item.requirements),
                        access_options = buildAccessOptions(item, nil, consumable.requirements, { entityType = "item" }),
                        recommendation_summary = consumableRecommendationSummary(consumable, false, itemIndex),
                    })
                end
            end
        end
    end

    return sections
end

local TOOLTIP_SUMMARY_CHUNK_LIMIT = 3

local function tooltipGroupKey(use)
    return table.concat({
        tostring(use.class or ""),
        tostring(use.spec or ""),
        tostring(use.slot or ""),
    }, "|")
end

local function tooltipRankShortLabel(use)
    local label = use and use.display_rank_label or ""
    if label ~= "" then
        return label
    end

    return rankShortLabel(use)
end

local function tooltipPhaseSummary(use)
    local phase = PHASE_SHORT_DISPLAY[use.phase] or PHASE_DISPLAY[use.phase] or tostring(use.phase or "")
    return phase .. " " .. tooltipRankShortLabel(use)
end

local function buildTooltipGroupSummary(group)
    local uses = {}
    local seen = {}
    for _, use in ipairs(group.uses or {}) do
        table.insert(uses, use)
    end
    table.sort(uses, function(a, b)
        if a.phaseIndex ~= b.phaseIndex then
            return a.phaseIndex < b.phaseIndex
        end
        return sortUses(a, b)
    end)

    local parts = {}
    for _, use in ipairs(uses) do
        local part = tooltipPhaseSummary(use)
        if not seen[part] then
            seen[part] = true
            table.insert(parts, part)
        end
    end

    if #parts > TOOLTIP_SUMMARY_CHUNK_LIMIT then
        local remaining = #parts - TOOLTIP_SUMMARY_CHUNK_LIMIT
        while #parts > TOOLTIP_SUMMARY_CHUNK_LIMIT do
            table.remove(parts)
        end
        table.insert(parts, "+" .. tostring(remaining))
    end

    return table.concat(parts, ", ")
end

local function tooltipSpecEnabled(specFilters, className, specName)
    if type(specFilters) ~= "table" then
        return true
    end

    local classFilters = specFilters[className]
    if type(classFilters) ~= "table" then
        return false
    end

    return classFilters[specName] == true
end

function BigBiSList:GetTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters)
    local uses = self:GetDataIndex().usesByItemId[itemId] or {}
    local matches = {}
    selectedSpecFirst = selectedSpecFirst ~= false

    for _, use in ipairs(uses) do
        if tooltipSpecEnabled(specFilters, use.class, use.spec) then
            table.insert(matches, use)
        end
    end

    table.sort(matches, function(a, b)
        if selectedSpecFirst then
            local aSelected = (a.class == selectedClass and a.spec == selectedSpec) and 1 or 0
            local bSelected = (b.class == selectedClass and b.spec == selectedSpec) and 1 or 0
            if aSelected ~= bSelected then
                return aSelected > bSelected
            end
        end
        if a.phaseIndex ~= b.phaseIndex then
            return a.phaseIndex < b.phaseIndex
        end
        if a.class ~= b.class then
            return a.class < b.class
        end
        if a.spec ~= b.spec then
            return a.spec < b.spec
        end
        return slotIndex(a.slot) < slotIndex(b.slot)
    end)

    return matches
end

function BigBiSList:GetGroupedTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters)
    local rawMatches = self:GetTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters)
    local groups = {}
    local groupedMatches = {}

    for _, use in ipairs(rawMatches) do
        local key = tooltipGroupKey(use)
        local group = groups[key]
        if not group then
            group = {
                class = use.class,
                spec = use.spec,
                slot = use.slot,
                uses = {},
                tooltip_grouped = true,
            }
            groups[key] = group
            table.insert(groupedMatches, group)
        end
        table.insert(group.uses, use)
    end

    for _, group in ipairs(groupedMatches) do
        group.phase_summary = buildTooltipGroupSummary(group)
    end

    return groupedMatches
end
