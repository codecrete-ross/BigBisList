local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local LEVELING_PHASE_KEY = "LEVELING"
local PHASE_ORDER = { "PR", "T4", "T5", "T6", "ZA", "SWP" }
local PHASE_DISPLAY = {
    LEVELING = "Leveling",
    PR = "Pre-Raid",
    T4 = "Tier 4",
    T5 = "Tier 5",
    T6 = "Tier 6",
    ZA = "Zul'Aman",
    SWP = "Sunwell Plateau",
}
for _, phase in ipairs((BigBiSListData or {}).phases or {}) do
    if PHASE_DISPLAY[phase.key] and type(phase.name) == "string" and phase.name ~= "" then
        PHASE_DISPLAY[phase.key] = phase.name
    end
end

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
    LEVELING = "Leveling",
    PR = "Pre",
    T4 = "T4",
    T5 = "T5",
    T6 = "T6",
    ZA = "ZA",
    SWP = "SWP",
}

local SOURCE_TYPE_LABELS = {
    all = "All sources",
    drop = "Drops",
    raid_drop = "Raid drops",
    heroic_dungeon_drop = "Heroic dungeon drops",
    dungeon_drop = "Dungeon drops",
    other_drop = "Other drops",
    quest = "Quests",
    vendor = "Vendors",
    crafted = "Crafted",
    trade = "Trade/AH",
    pvp = "PvP",
    token_turnin = "Token turn-ins",
    taught_by_item = "Formulae",
    trainer = "Profession trainers",
    world_drop = "World drops",
    unknown = "Unknown",
}

local SOURCE_FILTER_ORDER = {
    raid_drop = 1,
    heroic_dungeon_drop = 2,
    dungeon_drop = 3,
    other_drop = 4,
    quest = 10,
    vendor = 11,
    crafted = 12,
    trade = 13,
    pvp = 14,
    token_turnin = 15,
    taught_by_item = 16,
    trainer = 17,
    world_drop = 18,
    unknown = 99,
}

local FILTER_FACETS = {
    COST_FILTER_LABELS = {
        badge_justice = "Badge of Justice",
        arena_points = "Arena Points",
        honor_points = "Honor Points",
        battleground_marks = "Battleground Marks",
        tier_tokens = "Tier Tokens",
        sunmote = "Sunmote",
        other_turnins = "Other turn-ins",
    },
    COST_FILTER_ORDER = {
        badge_justice = 1,
        arena_points = 2,
        honor_points = 3,
        battleground_marks = 4,
        tier_tokens = 5,
        sunmote = 6,
        other_turnins = 20,
    },
    BATTLEGROUND_MARK_ITEM_IDS = {
        [20558] = true,
        [20559] = true,
        [20560] = true,
        [29024] = true,
    },
}

local SOURCE_FILTER_BY_CONTENT_TYPE = {
    raid = "raid_drop",
    heroic_dungeon = "heroic_dungeon_drop",
    dungeon = "dungeon_drop",
    other = "other_drop",
}

local RAID_ZONE_PHASE = {
    Karazhan = "T4",
    ["Gruul's Lair"] = "T4",
    ["Magtheridon's Lair"] = "T4",
    ["Serpentshrine Cavern"] = "T5",
    ["Tempest Keep"] = "T5",
    ["Hyjal Summit"] = "T6",
    ["Black Temple"] = "T6",
    ["Zul'Aman"] = "ZA",
    ["Sunwell Plateau"] = "SWP",
}

local ZONE_PHASE = {
    Karazhan = "T4",
    ["Gruul's Lair"] = "T4",
    ["Magtheridon's Lair"] = "T4",
    ["Serpentshrine Cavern"] = "T5",
    ["Tempest Keep"] = "T5",
    ["Hyjal Summit"] = "T6",
    ["Black Temple"] = "T6",
    ["Zul'Aman"] = "ZA",
    ["Sunwell Plateau"] = "SWP",
    ["Isle of Quel'Danas"] = "SWP",
}

local RAID_QUEST_PHASE_BY_ID = {
    [10725] = "T4",
    [10726] = "T4",
    [10727] = "T4",
    [10728] = "T4",
    [11031] = "T4",
    [11032] = "T4",
    [11033] = "T4",
    [11034] = "T4",
    [11007] = "T5",
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
    trainer = "Trainer",
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

FILTER_FACETS.WISHLIST_RANK_LABELS = {
    bis = "BiS",
    ranked = "Alt",
    situational = "Side",
    pvp = "PvP",
    unrealistic = "Hard",
    option = "Optional",
}

local ITEM_META_CACHE_LIMIT = 900
local ROW_ACCESS_CACHE_LIMIT = 900

BigBiSList.phaseOrder = PHASE_ORDER
BigBiSList.levelingPhaseKey = LEVELING_PHASE_KEY
BigBiSList.phaseDisplay = PHASE_DISPLAY
BigBiSList.slotOrder = SLOT_ORDER
BigBiSList.displaySlotFilters = DISPLAY_SLOT_FILTERS
BigBiSList.equipmentSlots = EQUIPMENT_SLOTS

local function lower(value)
    return string.lower(tostring(value or ""))
end

local function clampLevelingLevel(level)
    local maxLevel = BigBiSList.maxLevelingLevel or 69
    local numeric = tonumber(level) or maxLevel
    return math.max(1, math.min(maxLevel, math.floor(numeric)))
end

local function trim(value)
    return tostring(value or ""):gsub("^%s+", ""):gsub("%s+$", "")
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

local function schemaPositions(schemas, schemaName)
    local positions = {}
    local schema = schemas and schemas[schemaName] or nil
    for index, key in ipairs(schema or {}) do
        positions[key] = index
    end
    return positions
end

local function compactField(index, schemaName, record, key)
    if not index or not index.compact or type(record) ~= "table" then
        return record and record[key] or nil
    end

    local positions = index.schemaPositions and index.schemaPositions[schemaName]
    local position = positions and positions[key]
    return position and record[position] or nil
end

local inflateCompactRecord
local inflateCompactList

local function inflateCompactField(index, schemaName, key, value)
    if not index or not index.compact then
        return value
    end

    if schemaName == "item" or schemaName == "item_fallback" or schemaName == "source_record" then
        if key == "primary_source" then
            return inflateCompactRecord(index, "source", value)
        elseif key == "sources" then
            return inflateCompactList(index, "source", value)
        elseif key == "requirements" then
            return inflateCompactList(index, "requirement", value)
        end
    elseif schemaName == "source" then
        if key == "token_sources" or key == "quest_starter_sources" or key == "recipe_sources" then
            return inflateCompactList(index, "source", value)
        elseif key == "requirements" then
            return inflateCompactList(index, "requirement", value)
        elseif key == "costs" then
            return inflateCompactList(index, "cost", value)
        end
    elseif (schemaName == "use" or schemaName == "gem" or schemaName == "enchant" or schemaName == "consumable" or schemaName == "leveling_gear" or schemaName == "leveling_recommendation") and key == "requirements" then
        return inflateCompactList(index, "requirement", value)
    end

    return value
end

inflateCompactRecord = function(index, schemaName, record)
    if not index or not index.compact or type(record) ~= "table" then
        return record
    end

    local schema = index.schemas and index.schemas[schemaName] or nil
    local result = {}
    for position, key in ipairs(schema or {}) do
        local value = record[position]
        if value ~= nil then
            result[key] = inflateCompactField(index, schemaName, key, value)
        end
    end
    return result
end

inflateCompactList = function(index, schemaName, records)
    if type(records) ~= "table" then
        return nil
    end

    local result = {}
    for _, record in ipairs(records) do
        table.insert(result, inflateCompactRecord(index, schemaName, record))
    end
    return result
end

local function inflateUseRef(index, useRef)
    return inflateCompactRecord(index, "use", useRef)
end

local function getIndexedItem(index, itemId)
    itemId = tonumber(itemId)
    if not itemId then
        return nil
    end

    if not index or not index.compact then
        return index and index.itemsById and index.itemsById[itemId] or nil
    end

    index.itemCache = index.itemCache or {}
    if index.itemCache[itemId] == nil then
        index.itemCache[itemId] = inflateCompactRecord(index, "item", index.itemRecordsById[itemId])
    end
    return index.itemCache[itemId]
end

local function getIndexedItemFallback(index, itemId)
    itemId = tonumber(itemId)
    if not itemId or not index then
        return nil
    end

    if not index.compact then
        return index.itemFallbacksById and index.itemFallbacksById[itemId] or nil
    end

    index.itemFallbackCache = index.itemFallbackCache or {}
    if index.itemFallbackCache[itemId] == nil then
        index.itemFallbackCache[itemId] = inflateCompactRecord(
            index,
            "item_fallback",
            index.itemFallbackRecordsById and index.itemFallbackRecordsById[itemId]
        )
    end
    return index.itemFallbackCache[itemId]
end

function FILTER_FACETS.tableValueById(values, itemId)
    if type(values) ~= "table" or itemId == nil then
        return nil
    end

    local value = values[itemId]
    if value == nil then
        value = values[tostring(itemId)]
    end
    return value
end

local function addUseRef(bucket, key, useRef)
    if not key then
        return
    end
    bucket[key] = bucket[key] or {}
    table.insert(bucket[key], useRef)
end

local function ensureNestedUseBucket(root, className, specName, phaseKey)
    root[className] = root[className] or {}
    root[className][specName] = root[className][specName] or {}
    if not phaseKey then
        return root[className][specName]
    end
    root[className][specName][phaseKey] = root[className][specName][phaseKey] or {}
    return root[className][specName][phaseKey]
end

local function phaseIndex(phaseKey)
    for index, key in ipairs(PHASE_ORDER) do
        if key == phaseKey then
            return index
        end
    end
    return 999
end

local function earlierPhaseKey(a, b)
    if not a then
        return b
    elseif not b then
        return a
    elseif phaseIndex(a) <= phaseIndex(b) then
        return a
    end
    return b
end

local deriveSourceAcquisitionPhase

local function isConcreteRaidDrop(source)
    return type(source) == "table" and source.type == "drop" and RAID_ZONE_PHASE[source.zone] ~= nil
end

local function isWeakAmbiguousDrop(source)
    if type(source) ~= "table" or source.type ~= "drop" or isConcreteRaidDrop(source) then
        return false
    end

    local count = source.count
    local outOf = source.out_of
    if type(count) == "number" and type(outOf) == "number" then
        return count < 0 or outOf <= 0
    end

    return source.drop_percent == nil
end

local function sourcesForAcquisitionPhase(sources)
    if type(sources) ~= "table" then
        return {}
    end

    local hasConcreteRaidDrop = false
    for _, source in ipairs(sources) do
        if isConcreteRaidDrop(source) then
            hasConcreteRaidDrop = true
            break
        end
    end

    if not hasConcreteRaidDrop then
        return sources
    end

    local filtered = {}
    for _, source in ipairs(sources) do
        if type(source) == "table" and not isWeakAmbiguousDrop(source) then
            table.insert(filtered, source)
        end
    end

    if #filtered > 0 then
        return filtered
    end
    return sources
end

local function deriveSourcesAcquisitionPhase(sources)
    local selected
    for _, source in ipairs(sourcesForAcquisitionPhase(sources)) do
        if type(source) == "table" then
            selected = earlierPhaseKey(selected, deriveSourceAcquisitionPhase(source))
        end
    end
    return selected or "PR"
end

local function inferSourceAcquisitionPhase(source)
    if type(source) ~= "table" then
        return "PR"
    end

    local sourceType = source.type
    local zonePhase = ZONE_PHASE[source.zone]

    if sourceType == "token_turnin" then
        return deriveSourcesAcquisitionPhase(source.token_sources)
    elseif sourceType == "drop" then
        return zonePhase or "PR"
    elseif sourceType == "quest" then
        if type(source.quest_starter_sources) == "table" and #source.quest_starter_sources > 0 then
            return deriveSourcesAcquisitionPhase(source.quest_starter_sources)
        elseif type(source.quest_id) == "number" then
            return RAID_QUEST_PHASE_BY_ID[source.quest_id] or "PR"
        end
        return "PR"
    elseif sourceType == "crafted" or sourceType == "taught_by_item" then
        if type(source.recipe_sources) == "table" and #source.recipe_sources > 0 then
            return deriveSourcesAcquisitionPhase(source.recipe_sources)
        end
        return zonePhase or "PR"
    elseif sourceType == "vendor" and zonePhase then
        return zonePhase
    end

    return "PR"
end

deriveSourceAcquisitionPhase = function(source)
    local inferred = inferSourceAcquisitionPhase(source)
    if type(source) ~= "table" then return inferred end
    local zonePhase = source.type ~= "quest" and ZONE_PHASE[source.zone] or "PR"
    for _, candidate in ipairs({ zonePhase or "PR", source.available_from_phase or "PR" }) do
        if phaseIndex(candidate) > phaseIndex(inferred) then inferred = candidate end
    end
    return inferred
end

local function sourceZoneIsPhaseAvailable(zone, selectedPhaseIndex)
    if not selectedPhaseIndex then
        return true
    end
    return phaseIndex(ZONE_PHASE[zone] or "PR") <= selectedPhaseIndex
end

local function sourceIsPhaseAvailable(source, selectedPhaseIndex)
    if not selectedPhaseIndex then
        return true
    elseif type(source) ~= "table" then
        return false
    elseif phaseIndex(deriveSourceAcquisitionPhase(source)) > selectedPhaseIndex then
        return false
    elseif source.available_until_phase and selectedPhaseIndex >= phaseIndex(source.available_until_phase) then
        return false
    end
    for _, key in ipairs({ "token_sources", "quest_starter_sources", "recipe_sources" }) do
        if source[key] and #source[key] > 0 then
            local available = false
            for _, child in ipairs(source[key]) do
                if sourceIsPhaseAvailable(child, selectedPhaseIndex) then available = true; break end
            end
            if not available then return false end
        end
    end
    return true
end

local function addSourceZone(zones, seen, zone, selectedPhaseIndex)
    if zone and zone ~= "" and sourceZoneIsPhaseAvailable(zone, selectedPhaseIndex) then
        addUnique(zones, seen, zone)
    end
end

local sourceFilterKey

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

local function rowReputationsWithMeta(metaReputations, requirements)
    local reputations = {}
    local seen = {}
    for _, reputation in ipairs(metaReputations or {}) do
        addUnique(reputations, seen, reputation)
    end
    addReputationsFromRequirements(reputations, seen, requirements)
    table.sort(reputations)
    return reputations
end

local function putBoundedCache(cache, order, key, value, limit)
    if not cache[key] then
        table.insert(order, key)
        if #order > limit then
            cache[table.remove(order, 1)] = nil
        end
    end
    cache[key] = value
    return value
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

FILTER_FACETS.VENDOR_PURCHASE_SOURCE_TYPES = {
    vendor = true,
    pvp = true,
    token_turnin = true,
}

function FILTER_FACETS.isVendorPurchaseSource(source)
    return type(source) == "table" and FILTER_FACETS.VENDOR_PURCHASE_SOURCE_TYPES[source.type] == true
end

local function sourceIdentity(source)
    if type(source) ~= "table" then
        return nil
    end

    local sourceType = tostring(source.type or "unknown")
    local window = "|" .. tostring(source.available_from_phase or "") .. ":" .. tostring(source.available_until_phase or "")
    if FILTER_FACETS.VENDOR_PURCHASE_SOURCE_TYPES[sourceType] then
        local vendorId = source.vendor_id or source.entity_id
        if vendorId then
            return sourceType .. "|vendor:" .. tostring(vendorId) .. window
        end
    elseif source.quest_id then
        return sourceType .. "|quest:" .. tostring(source.quest_id) .. window
    elseif source.spell_id then
        return sourceType .. "|spell:" .. tostring(source.spell_id) .. window
    elseif source.item_id then
        return sourceType .. "|item:" .. tostring(source.item_id) .. window
    elseif source.entity_id then
        return sourceType .. "|entity:" .. tostring(source.entity_id) .. window
    end

    return table.concat({
        sourceType,
        tostring(source.source_url or ""),
        tostring(source.entity_name or ""),
        tostring(source.location_area or source.zone or ""),
    }, "|") .. window
end

function FILTER_FACETS.cloneTable(value, seen)
    if type(value) ~= "table" then
        return value
    end

    seen = seen or {}
    if seen[value] then
        return seen[value]
    end

    local result = {}
    seen[value] = result
    for key, child in pairs(value) do
        result[FILTER_FACETS.cloneTable(key, seen)] = FILTER_FACETS.cloneTable(child, seen)
    end
    return result
end

function FILTER_FACETS.isPlaceholderLabel(value)
    local label = lower(trim(value))
    return label == ""
        or label == "unknown"
        or label == "unknown vendor"
        or string.match(label, "^item %d+$") ~= nil
        or string.match(label, "^currency %d+$") ~= nil
end

function FILTER_FACETS.valueNeedsRicherReplacement(key, current, candidate)
    if candidate == nil or candidate == "" then
        return false
    elseif current == nil or current == "" then
        return true
    elseif key == "entity_name" or key == "name" or key == "token_name" then
        return FILTER_FACETS.isPlaceholderLabel(current) and not FILTER_FACETS.isPlaceholderLabel(candidate)
    elseif key == "price_copper" or key == "purchase_quantity" or key == "amount" then
        return (tonumber(current) or 0) <= 0 and (tonumber(candidate) or 0) > 0
    elseif key == "raw_source_text" then
        return string.len(tostring(candidate)) > string.len(tostring(current))
    end
    return false
end

function FILTER_FACETS.costIdentity(cost)
    if type(cost) ~= "table" then
        return nil
    elseif cost.currency_id then
        return "currency:" .. tostring(cost.currency_id)
    elseif cost.item_id then
        return "item:" .. tostring(cost.item_id)
    elseif cost.name and cost.name ~= "" then
        return "name:" .. lower(cost.name)
    end
    return "amount:" .. tostring(cost.amount or "")
end

function FILTER_FACETS.mergePlainRecord(target, candidate)
    for key, value in pairs(candidate or {}) do
        if type(value) ~= "table" and FILTER_FACETS.valueNeedsRicherReplacement(key, target[key], value) then
            target[key] = value
        elseif target[key] == nil then
            target[key] = FILTER_FACETS.cloneTable(value)
        end
    end
    return target
end

function FILTER_FACETS.mergeCostLists(target, candidate)
    target = target or {}
    local byIdentity = {}
    for _, cost in ipairs(target) do
        byIdentity[FILTER_FACETS.costIdentity(cost)] = cost
    end
    for _, cost in ipairs(candidate or {}) do
        local key = FILTER_FACETS.costIdentity(cost)
        local existing = key and byIdentity[key]
        if existing then
            FILTER_FACETS.mergePlainRecord(existing, cost)
        else
            local copied = FILTER_FACETS.cloneTable(cost)
            table.insert(target, copied)
            if key then
                byIdentity[key] = copied
            end
        end
    end
    return target
end

function FILTER_FACETS.mergeRequirementLists(target, candidate)
    target = target or {}
    local byIdentity = {}
    for _, requirement in ipairs(target) do
        byIdentity[requirementKey(requirement)] = requirement
    end
    for _, requirement in ipairs(candidate or {}) do
        local key = requirementKey(requirement)
        local existing = byIdentity[key]
        if existing then
            FILTER_FACETS.mergePlainRecord(existing, requirement)
        else
            local copied = FILTER_FACETS.cloneTable(requirement)
            table.insert(target, copied)
            byIdentity[key] = copied
        end
    end
    return target
end

function FILTER_FACETS.mergeSourceLists(target, candidate)
    target = target or {}
    local byIdentity = {}
    for _, source in ipairs(target) do
        byIdentity[sourceIdentity(source)] = source
    end
    for _, source in ipairs(candidate or {}) do
        local key = sourceIdentity(source)
        local existing = key and byIdentity[key]
        if existing then
            FILTER_FACETS.mergeSourceData(existing, source)
        else
            local copied = FILTER_FACETS.cloneTable(source)
            table.insert(target, copied)
            if key then
                byIdentity[key] = copied
            end
        end
    end
    return target
end

function FILTER_FACETS.mergeSourceData(target, candidate)
    target = target or {}
    for key, value in pairs(candidate or {}) do
        if key == "costs" then
            target.costs = FILTER_FACETS.mergeCostLists(target.costs, value)
        elseif key == "requirements" then
            target.requirements = FILTER_FACETS.mergeRequirementLists(target.requirements, value)
        elseif key == "token_sources" or key == "quest_starter_sources" or key == "recipe_sources" then
            target[key] = FILTER_FACETS.mergeSourceLists(target[key], value)
        elseif type(value) ~= "table" and FILTER_FACETS.valueNeedsRicherReplacement(key, target[key], value) then
            target[key] = value
        elseif target[key] == nil then
            target[key] = FILTER_FACETS.cloneTable(value)
        end
    end
    return target
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

local function formatDropPercent(source)
    local percent = tonumber(source and source.drop_percent)
    if not percent then
        return nil
    end
    return string.format("%.1f%%", percent)
end

local function sourceDropSummary(source)
    if type(source) ~= "table" then
        return nil
    end

    local text = source.entity_name
    if source.zone and source.zone ~= "" then
        text = text and (text .. " (" .. source.zone .. ")") or source.zone
    end

    local percent = formatDropPercent(source)
    if percent then
        text = text and (text .. " " .. percent) or percent
    end

    return text
end

function FILTER_FACETS.formatCopper(value)
    local copper = math.floor(tonumber(value) or 0)
    if copper <= 0 then
        return ""
    end

    local gold = math.floor(copper / 10000)
    local silver = math.floor((copper % 10000) / 100)
    local remainder = copper % 100
    local parts = {}
    if gold > 0 then
        table.insert(parts, tostring(gold) .. "g")
    end
    if silver > 0 then
        table.insert(parts, tostring(silver) .. "s")
    end
    if remainder > 0 then
        table.insert(parts, tostring(remainder) .. "c")
    end
    return table.concat(parts, " ")
end

function FILTER_FACETS.costDisplayName(source, cost)
    if type(cost) ~= "table" then
        return nil
    end

    local name = trim(cost.name)
    if not FILTER_FACETS.isPlaceholderLabel(name) then
        return name
    end

    local itemId = tonumber(cost.item_id)
    if itemId and tonumber(source and source.token_item_id) == itemId
        and not FILTER_FACETS.isPlaceholderLabel(source.token_name) then
        return trim(source.token_name)
    end
    for _, tokenSource in ipairs(source and source.token_sources or {}) do
        if itemId and tonumber(tokenSource.token_item_id) == itemId
            and not FILTER_FACETS.isPlaceholderLabel(tokenSource.token_name) then
            return trim(tokenSource.token_name)
        end
    end
    return nil
end

function FILTER_FACETS.sourceLocationArea(source)
    if type(source) ~= "table" then
        return nil
    end
    local area = trim(source.location_area or source.zone)
    if area == "" or lower(area) == "unknown" then
        return nil
    end
    return area
end

function FILTER_FACETS.sourceLocationNote(source)
    local note = trim(type(source) == "table" and source.location_note or nil)
    return note ~= "" and note or nil
end

function FILTER_FACETS.formatSourceCosts(source)
    local parts = {}
    local purchaseQuantity = tonumber(source and source.purchase_quantity)
    local priceCopper = tonumber(source and source.price_copper)
    if priceCopper and priceCopper > 0 then
        table.insert(parts, FILTER_FACETS.formatCopper(priceCopper))
    end

    for _, cost in ipairs(source and source.costs or {}) do
        local amount = tonumber(cost.amount)
        local name = FILTER_FACETS.costDisplayName(source, cost)
        if amount and amount > 0 and name then
            table.insert(parts, tostring(amount) .. " " .. name)
        end
    end
    local summary = table.concat(parts, " + ")
    if summary ~= "" and purchaseQuantity and purchaseQuantity > 1 then
        summary = summary .. " per " .. tostring(math.floor(purchaseQuantity))
    end
    return summary
end

function FILTER_FACETS.costFilterKey(cost)
    if type(cost) ~= "table" then
        return nil
    end

    local name = lower(cost.name)
    local currencyId = tonumber(cost.currency_id)
    local itemId = tonumber(cost.item_id)

    if currencyId == 29434 or name == "badge of justice" then
        return "badge_justice"
    elseif currencyId == 1900 or name == "arena points" then
        return "arena_points"
    elseif currencyId == 1901 or name == "honor points" then
        return "honor_points"
    elseif itemId == 34664 or name == "sunmote" then
        return "sunmote"
    elseif FILTER_FACETS.BATTLEGROUND_MARK_ITEM_IDS[itemId] or string.find(name, "mark of honor", 1, true) then
        return "battleground_marks"
    elseif itemId and (
        string.find(name, "fallen", 1, true)
        or string.find(name, "vanquished", 1, true)
        or string.find(name, "forgotten", 1, true)
    ) then
        return "tier_tokens"
    elseif itemId or name ~= "" then
        return "other_turnins"
    end

    return nil
end

function FILTER_FACETS.sourceCostKeys(source)
    local keys = {}
    local seen = {}
    for _, cost in ipairs(source and source.costs or {}) do
        addUnique(keys, seen, FILTER_FACETS.costFilterKey(cost))
    end
    table.sort(keys, function(a, b)
        local aOrder = FILTER_FACETS.COST_FILTER_ORDER[a] or 50
        local bOrder = FILTER_FACETS.COST_FILTER_ORDER[b] or 50
        if aOrder ~= bOrder then
            return aOrder < bOrder
        end
        return tostring(a) < tostring(b)
    end)
    return keys
end

function FILTER_FACETS.costLabelsForKeys(keys)
    local labels = {}
    for _, key in ipairs(keys or {}) do
        table.insert(labels, FILTER_FACETS.COST_FILTER_LABELS[key] or key)
    end
    return labels
end

function FILTER_FACETS.sourceVendorLabel(source)
    local sourceType = source and source.type
    if sourceType ~= "vendor" and sourceType ~= "pvp" and sourceType ~= "token_turnin" then
        return nil
    end

    local name = source.entity_name
    if name and name ~= "" then
        return name
    end
    return nil
end

function FILTER_FACETS.sourceVendorKey(source)
    local label = FILTER_FACETS.sourceVendorLabel(source)
    if not label then
        return nil
    end

    local vendorId = source.vendor_id or source.entity_id
    if vendorId then
        return tostring(vendorId)
    end
    return lower(label)
end

function FILTER_FACETS.sourceVendorDetailsStatus(source)
    if not FILTER_FACETS.isVendorPurchaseSource(source) then
        return "not_applicable", {}
    end

    local missing = {}
    if FILTER_FACETS.isPlaceholderLabel(FILTER_FACETS.sourceVendorLabel(source)) then
        table.insert(missing, "vendor")
    end
    if not FILTER_FACETS.sourceLocationArea(source) then
        table.insert(missing, "area")
    end
    if FILTER_FACETS.formatSourceCosts(source) == "" then
        table.insert(missing, "cost")
    end

    return #missing == 0 and "complete" or "reported_only", missing
end

function FILTER_FACETS.optionIsReportedOnly(option)
    return type(option) == "table" and option.vendor_details_status == "reported_only"
end

function FILTER_FACETS.optionIsCompleteRoute(option)
    return type(option) == "table" and not FILTER_FACETS.optionIsReportedOnly(option)
end

function FILTER_FACETS.promoteCompleteAccessOption(options)
    local primary
    local preferred
    for _, option in ipairs(options or {}) do
        if option.is_primary then
            primary = option
        end
        if not preferred and FILTER_FACETS.optionIsCompleteRoute(option) then
            preferred = option
        end
    end

    if primary and FILTER_FACETS.optionIsCompleteRoute(primary) then
        return primary
    elseif not preferred then
        return primary
    end

    for _, option in ipairs(options or {}) do
        option.is_primary = option == preferred
    end
    return preferred
end

function FILTER_FACETS.sourceCacheSignature(source)
    if type(source) ~= "table" then
        return ""
    end
    local parts = {
        sourceIdentity(source) or "",
        tostring(FILTER_FACETS.sourceLocationArea(source) or ""),
        tostring(FILTER_FACETS.sourceLocationNote(source) or ""),
        tostring(source.price_copper or ""),
        tostring(source.purchase_quantity or ""),
        FILTER_FACETS.formatSourceCosts(source),
        tostring(source.tradeable or false),
    }
    for _, key in ipairs({ "token_sources", "quest_starter_sources", "recipe_sources" }) do
        for _, child in ipairs(source[key] or {}) do
            table.insert(parts, key .. ":" .. FILTER_FACETS.sourceCacheSignature(child))
        end
    end
    return table.concat(parts, "~")
end

function FILTER_FACETS.accessOptionDetailFields(option)
    if type(option) ~= "table" then
        return {}
    end
    if option.source and option.source.type == "crafted" and option.source.recipe_sources then
        local fields = {{ key = "source", label = "Source", value = option.source_summary or option.label }}
        for _, recipeSource in ipairs(option.source.recipe_sources) do
            local recipeItem = recipeSource.item_id and BigBiSList.GetItemData and BigBiSList:GetItemData(recipeSource.item_id)
            local recipeName = recipeItem and recipeItem.name
            if not recipeName then
                for _, requirement in ipairs(option.requirements or {}) do
                    if requirement.type == "recipe_known" then recipeName = requirement.raw_text or requirement.spell_name; break end
                end
            end
            if recipeName then table.insert(fields, { key = "recipe", label = "Recipe", value = recipeName }) end
            local origin = sourceDropSummary(recipeSource)
            if origin then table.insert(fields, { key = "recipe_source", label = "Recipe source", value = origin }) end
            local recipeCost = FILTER_FACETS.formatSourceCosts(recipeSource)
            if recipeCost and recipeCost ~= "" then
                table.insert(fields, { key = "recipe_cost", label = "Recipe cost", value = recipeCost })
            end
            for _, requirement in ipairs(recipeSource.requirements or {}) do
                if requirement.type == "reputation" and requirement.reputation then
                    local standing = trim(requirement.standing)
                    table.insert(fields, { key = "recipe_reputation", label = "Recipe reputation",
                        value = standing ~= "" and (standing .. " with " .. requirement.reputation) or requirement.reputation })
                end
            end
        end
        return fields
    elseif not option.is_vendor_purchase then
        return {}
    end

    local vendor = option.vendor_label
    if FILTER_FACETS.isPlaceholderLabel(vendor) then
        vendor = "Unavailable in committed source data"
    end
    local area = option.location_area
    if not area or area == "" then
        area = "Unavailable in committed source data"
    end
    local cost = option.cost_summary
    if not cost or cost == "" then
        cost = "Unavailable in committed source data"
    end

    local fields = {
        { key = "vendor", label = "Vendor", value = vendor },
        { key = "area", label = "Area", value = area, note = option.location_note },
        { key = "cost", label = "Cost", value = cost },
    }

    if option.side == "Alliance" or option.side == "Horde" then
        table.insert(fields, { key = "faction", label = "Faction", value = option.side })
    end

    for _, requirement in ipairs(option.requirements or {}) do
        if requirement.type == "reputation" and requirement.reputation then
            local standing = trim(requirement.standing)
            local value = standing ~= ""
                and (standing .. " with " .. tostring(requirement.reputation))
                or tostring(requirement.reputation)
            table.insert(fields, { key = "reputation", label = "Reputation", value = value })
        elseif requirement.type == "faction_choice" and type(requirement.choices) == "table" and #requirement.choices > 0 then
            table.insert(fields, {
                key = "faction_choice",
                label = "Faction",
                value = table.concat(requirement.choices, " / "),
            })
        end
    end

    local source = option.source
    if source and source.type == "token_turnin" then
        local summaries = {}
        local seen = {}
        for _, tokenSource in ipairs(source.token_sources or {}) do
            local tokenName = trim(tokenSource.token_name)
            if FILTER_FACETS.isPlaceholderLabel(tokenName) then
                tokenName = ""
            end
            local origin = sourceDropSummary(tokenSource) or FILTER_FACETS.sourceLocationArea(tokenSource)
            local summary
            if tokenName ~= "" and origin and origin ~= "" then
                summary = tokenName .. " - " .. origin
            elseif tokenName ~= "" then
                summary = tokenName
            else
                summary = origin
            end
            local key = lower(summary)
            if summary and summary ~= "" and not seen[key] then
                seen[key] = true
                table.insert(summaries, summary)
            end
        end
        if #summaries > 0 then
            local value = summaries[1]
            if #summaries > 1 then
                value = value .. " (+" .. tostring(#summaries - 1) .. " more committed source"
                    .. (#summaries == 2 and ")" or "s)")
            end
            table.insert(fields, { key = "token_source", label = "Token source", value = value })
        end
    end

    local acquisitionPhase = option.acquisition_phase
    if acquisitionPhase and acquisitionPhase ~= "" and acquisitionPhase ~= "PR" and acquisitionPhase ~= "LEVELING" then
        local phaseLabel = BigBiSList.GetPhaseDisplayName
            and BigBiSList:GetPhaseDisplayName(acquisitionPhase)
            or tostring(acquisitionPhase)
        table.insert(fields, { key = "availability", label = "Availability", value = phaseLabel })
    end

    return fields
end

function FILTER_FACETS.accessOptionDetailSummary(option)
    local parts = {}
    for _, field in ipairs(FILTER_FACETS.accessOptionDetailFields(option)) do
        local value = field.value
        if field.note and field.note ~= "" then
            value = value .. " (" .. field.note .. ")"
        end
        table.insert(parts, field.label .. ": " .. value)
    end
    return table.concat(parts, " | ")
end

local function tokenCostName(source)
    for _, cost in ipairs(source and source.costs or {}) do
        if cost.item_id and cost.name and cost.name ~= "" then
            return cost.name
        end
    end

    local tokenSource = source and source.token_sources and source.token_sources[1]
    return tokenSource and tokenSource.token_name
end

local function sourceOptionSummary(source, fallbackLabel)
    local sourceType = source and source.type or "unknown"

    if sourceType == "token_turnin" then
        local text = "Token"
        local tokenName = tokenCostName(source)
        if tokenName and tokenName ~= "" then
            text = text .. ": " .. tokenName
        elseif fallbackLabel and fallbackLabel ~= "" then
            text = text .. ": " .. fallbackLabel
        end

        local tokenSources = source and source.token_sources or {}
        local firstTokenSource = tokenSources[1]
        local tokenSummary = sourceDropSummary(firstTokenSource)
        if tokenSummary and tokenSummary ~= "" then
            text = text .. " - " .. tokenSummary
        elseif source.entity_name and source.entity_name ~= "" then
            text = text .. " - Turn in: " .. source.entity_name
        end
        if #tokenSources > 1 then
            text = text .. " +" .. tostring(#tokenSources - 1)
        end
        return text
    elseif sourceType == "drop" or sourceType == "world_drop" then
        local dropSummary = sourceDropSummary(source)
        if dropSummary and dropSummary ~= "" then
            return (SOURCE_TYPE_PREFIXES[sourceType] or "Drop") .. ": " .. dropSummary
        end
    elseif sourceType == "vendor" or sourceType == "pvp" then
        local text = sourceLabel(source, fallbackLabel)
        local costs = FILTER_FACETS.formatSourceCosts(source)
        if costs ~= "" then
            text = text .. " (" .. costs .. ")"
        end
        return text
    end

    return sourceLabel(source, fallbackLabel)
end

local function sourceOptionZones(source)
    local zones = {}
    local seen = {}

    if type(source) ~= "table" then
        return zones
    end

    addSourceZone(zones, seen, FILTER_FACETS.sourceLocationArea(source))
    if source.type == "token_turnin" then
        for _, tokenSource in ipairs(source.token_sources or {}) do
            addSourceZone(zones, seen, FILTER_FACETS.sourceLocationArea(tokenSource))
        end
    elseif source.type == "quest" then
        for _, starterSource in ipairs(source.quest_starter_sources or {}) do
            addSourceZone(zones, seen, FILTER_FACETS.sourceLocationArea(starterSource))
        end
    end

    return zones
end

local function sourceOptionFilterKey(source)
    if sourceFilterKey then
        return sourceFilterKey(source)
    end
    return source and source.type or "unknown"
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
            source = FILTER_FACETS.cloneTable(source),
            fallbackLabel = fallbackLabel,
            extraRequirements = {},
            extraSeen = {},
        }
        seen[key] = input
        table.insert(inputs, input)
    else
        FILTER_FACETS.mergeSourceData(input.source, source)
        if (not input.fallbackLabel or input.fallbackLabel == "") and fallbackLabel and fallbackLabel ~= "" then
            input.fallbackLabel = fallbackLabel
        end
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

local function shouldAddTradeOption(item, inputs, options, sourceRecords)
    if options and options.alwaysTradeOption then
        return true, true
    end

    local hasCrafted = false
    for _, input in ipairs(inputs or {}) do
        if input.source and input.source.type == "crafted" then
            hasCrafted = true
            break
        end
    end

    if item and (item.tradeable == true or item.boe == true or item.binding == "bind_on_equip") then
        return true, true
    end
    if not isBindOnPickup(item) then
        for _, record in ipairs(sourceRecords or {}) do
            if record.tradeable == true or record.boe == true or record.binding == "bind_on_equip" then return true, true end
        end
    end

    return hasCrafted and not isBindOnPickup(item), false
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
        local filterKey = sourceOptionFilterKey(source)
        local acquisitionPhase = deriveSourceAcquisitionPhase(source)
        local costKeys = FILTER_FACETS.sourceCostKeys(source)
        local costSummary = FILTER_FACETS.formatSourceCosts(source)
        local locationArea = FILTER_FACETS.sourceLocationArea(source)
        local vendorStatus, vendorMissing = FILTER_FACETS.sourceVendorDetailsStatus(source)
        table.insert(accessOptions, {
            label = sourceLabel(source, input.fallbackLabel),
            source_type = source.type or "unknown",
            source_filter_key = filterKey,
            source_filter_label = SOURCE_TYPE_LABELS[filterKey] or filterKey,
            source_summary = sourceOptionSummary(source, input.fallbackLabel),
            cost_keys = costKeys,
            cost_labels = FILTER_FACETS.costLabelsForKeys(costKeys),
            cost_summary = costSummary,
            vendor_key = FILTER_FACETS.sourceVendorKey(source),
            vendor_label = FILTER_FACETS.sourceVendorLabel(source),
            location_area = locationArea,
            location_note = FILTER_FACETS.sourceLocationNote(source),
            vendor_details_status = vendorStatus,
            vendor_details_missing = vendorMissing,
            is_vendor_purchase = FILTER_FACETS.isVendorPurchaseSource(source),
            price_copper = tonumber(source.price_copper),
            purchase_quantity = tonumber(source.purchase_quantity),
            zone = locationArea,
            zones = sourceOptionZones(source),
            source_url = source.source_url or (item and item.wowhead_url),
            source_identity = sourceIdentity(source),
            source = source,
            side = source.side,
            acquisition_phase = acquisitionPhase,
            acquisitionPhaseIndex = phaseIndex(acquisitionPhase),
            requirements = requirements,
            reputations = reputationsFromRequirements(requirements),
            is_primary = input.isPrimary or false,
            is_trade_option = false,
        })
    end

    local addTradeOption, explicitTradeOption = shouldAddTradeOption(item, inputs, options, sourceRecords)
    if addTradeOption then
        local requirements = mergedRequirements(globalRequirements)
        local tradeSources = {}
        for _, input in ipairs(inputs) do
            table.insert(tradeSources, input.source)
        end
        local acquisitionPhase = deriveSourcesAcquisitionPhase(tradeSources)
        table.insert(accessOptions, {
            label = options.tradeLabel or "Trade/Auction House",
            source_type = "trade",
            source_filter_key = "trade",
            source_filter_label = SOURCE_TYPE_LABELS.trade,
            source_summary = options.tradeLabel or "Trade/Auction House",
            vendor_details_status = "not_applicable",
            vendor_details_missing = {},
            is_vendor_purchase = false,
            source_url = item and item.wowhead_url or (sourceRecords[1] and sourceRecords[1].source_url),
            acquisition_phase = acquisitionPhase,
            acquisitionPhaseIndex = phaseIndex(acquisitionPhase),
            trade_sources = tradeSources,
            requirements = requirements,
            reputations = reputationsFromRequirements(requirements),
            is_primary = false,
            is_trade_option = true,
            is_inferred_trade_option = not explicitTradeOption,
        })
    end

    FILTER_FACETS.promoteCompleteAccessOption(accessOptions)
    for _, option in ipairs(accessOptions) do
        option.detail_fields = FILTER_FACETS.accessOptionDetailFields(option)
        option.detail_summary = FILTER_FACETS.accessOptionDetailSummary(option)
    end
    return accessOptions
end

local function requirementsCacheKey(requirements)
    local keys = {}
    for _, requirement in ipairs(requirements or {}) do
        table.insert(keys, requirementKey(requirement))
    end
    table.sort(keys)
    return table.concat(keys, "||")
end

local function sourceRecordsCacheKey(sourceRecords)
    local keys = {}
    for _, record in ipairs(normalizeSourceRecords(sourceRecords)) do
        if type(record) == "table" then
            table.insert(keys, tostring(record.id or "record") .. ":" .. tostring(record.source_url or ""))
            table.insert(keys, tostring(record.tradeable or false) .. ":" .. tostring(record.boe) .. ":" .. tostring(record.binding or ""))
            if record.primary_source then
                table.insert(keys, FILTER_FACETS.sourceCacheSignature(record.primary_source))
            end
            for _, source in ipairs(record.sources or {}) do
                table.insert(keys, FILTER_FACETS.sourceCacheSignature(source))
            end
        end
    end
    table.sort(keys)
    return table.concat(keys, "||")
end

local function accessOptionsCacheKey(row, item, sourceRecords, rowRequirements, options)
    if row and row._access_cache_key then
        return row._access_cache_key
    end

    options = options or {}
    return table.concat({
        tostring((row and row.item_id) or (item and (item.id or item.item_id)) or ""),
        sourceRecordsCacheKey(sourceRecords),
        requirementsCacheKey(rowRequirements),
        tostring(options.entityType or "item"),
        tostring(options.forceSourceScopedEquip or false),
        tostring(options.alwaysTradeOption or false),
        tostring(options.tradeLabel or ""),
    }, "|")
end

local function buildRowAccessOptions(index, row)
    if type(row) ~= "table" then
        return nil
    elseif row.access_options then
        return row.access_options
    elseif row.bestUse then
        row.access_options = buildRowAccessOptions(index, row.bestUse)
        return row.access_options
    end

    local context = row._access_context or {}
    local item = context.item or row.item or (row.item_id and getIndexedItem(index, row.item_id))
    if not item and row.item_id then
        item = getIndexedItemFallback(index, row.item_id)
    end
    if not item and not context.sourceRecords then
        return nil
    end

    index.rowAccessCache = index.rowAccessCache or {}
    index.rowAccessCacheOrder = index.rowAccessCacheOrder or {}

    local sourceRecords = context.sourceRecords
    local requirements = context.requirements
    local options = context.options or { entityType = row.entity_type or "item" }
    local key = accessOptionsCacheKey(row, item, sourceRecords, requirements, options)
    local cached = index.rowAccessCache[key]
    if cached then
        row.access_options = cached
        return cached
    end

    local accessOptions = buildAccessOptions(item, sourceRecords, requirements, options)
    if accessOptions then
        putBoundedCache(index.rowAccessCache, index.rowAccessCacheOrder, key, accessOptions, ROW_ACCESS_CACHE_LIMIT)
    end
    row.access_options = accessOptions
    return accessOptions
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

local LEVELING_HELPERS = {}

LEVELING_HELPERS.reasonTagLabels = {
    best_overall = "Best Overall",
    best_survival = "Best Survival",
    best_hit = "Best Hit",
    best_easy_source = "Best Easy Source",
    boe = "BoE",
    dungeon = "Dungeon",
    easy_source = "Easy Source",
    hit = "Hit",
    survival = "Survival",
    near_equivalent = "Near Equivalent",
    suffix_winner = "Best Random Suffix",
    contextual_racial = "Racial Utility",
    draenei_hit_adjusted = "Draenei Hit Adjusted",
    draenei_spell_hit_adjusted = "Draenei Spell Hit Adjusted",
    dwarf_gun_bonus = "Dwarf Gun Bonus",
    gnome_intellect_bonus = "Gnome Intellect Bonus",
    human_mace_bonus = "Human Mace Bonus",
    human_spirit_bonus = "Human Spirit Bonus",
    human_sword_bonus = "Human Sword Bonus",
    night_elf_dodge_bonus = "Night Elf Dodge Bonus",
    orc_axe_bonus = "Orc Axe Bonus",
    tauren_health_bonus = "Tauren Health Bonus",
    troll_bow_bonus = "Troll Bow Bonus",
    troll_throwing_bonus = "Troll Throwing Bonus",
}

function LEVELING_HELPERS.reasonTagLabel(tag)
    tag = trim(tag or "")
    if tag == "" then
        return ""
    end

    local mapped = LEVELING_HELPERS.reasonTagLabels[tag]
    if mapped then
        return mapped
    end

    local race = tag:match("^best_for_(.+)$")
    if race then
        return "Best for " .. race:gsub("_", " "):gsub("%S+", function(token)
            return (token:gsub("^%l", string.upper))
        end)
    end

    return tag:gsub("_", " "):gsub("%S+", function(token)
        return (token:gsub("^%l", string.upper))
    end)
end

function LEVELING_HELPERS.categoryKey(label)
    local key = lower(label or "Recommended"):gsub("[^%w]+", "_"):gsub("^_+", ""):gsub("_+$", "")
    if key == "" then
        key = "recommended"
    end
    return "leveling_" .. key
end

function LEVELING_HELPERS.isCategoryKey(key)
    return type(key) == "string" and string.sub(key, 1, 9) == "leveling_"
end

local RACE_TOKEN_NAMES = {
    BloodElf = "Blood Elf",
    Draenei = "Draenei",
    Dwarf = "Dwarf",
    Gnome = "Gnome",
    Human = "Human",
    NightElf = "Night Elf",
    Orc = "Orc",
    Scourge = "Undead",
    Tauren = "Tauren",
    Troll = "Troll",
}

local function raceMatches(rowRace, selectedRace)
    if not rowRace or rowRace == "" or rowRace == "*" then
        return true
    elseif not selectedRace or selectedRace == "" or selectedRace == "*" then
        return false
    end
    return rowRace == selectedRace
end

local function levelingRecommendationGroupKey(row)
    if type(row) ~= "table" then
        return nil
    end

    return table.concat({
        tostring(row.level_min or ""),
        tostring(row.level_max or ""),
        tostring(row.slot or ""),
        tostring(row.context or ""),
    }, ":")
end

local function slotMatchesDisplayFilter(filterKey, rowSlot)
    local slots = DISPLAY_SLOT_FILTER_MAP[filterKey]
    if slots then
        return slotListContains(slots, rowSlot)
    end

    return filterKey == rowSlot
end

local function rowMatchesSelectedSlots(rowSlot, selectedSlots, rowSlots)
    if not tableHasAnyEnabled(selectedSlots) then
        return true
    end

    for filterKey, selected in pairs(selectedSlots or {}) do
        if selected then
            if slotMatchesDisplayFilter(filterKey, rowSlot) then
                return true
            end
            for _, candidateSlot in ipairs(rowSlots or {}) do
                if slotMatchesDisplayFilter(filterKey, candidateSlot) then
                    return true
                end
            end
        end
    end

    return false
end

local function rankLabelIsGeneric(label)
    local normalized = lower(trim(label))
    return normalized == "" or normalized == "bis" or normalized == "best" or normalized == "best in slot"
end

local function bisVariantLabel(use)
    if not use or use.rank_group ~= "bis" then
        return nil
    end

    local label = lower(use.rank_label)
    if rankLabelIsGeneric(label) then
        return nil
    elseif label:find("personal", 1, true) then
        return "Personal"
    elseif label:find("raid", 1, true) or label:find("group performance", 1, true) then
        return "Raid"
    elseif label:find("threat", 1, true) then
        return "Threat"
    elseif label:find("mitigation", 1, true) or label:find("mit skewed", 1, true) then
        return "Mit"
    elseif label:find("hit", 1, true) or label:find("6%", 1, true) or label:find("9%", 1, true) then
        return "Hit"
    elseif label:find("overall", 1, true) then
        return "Overall"
    elseif label:find("balanced", 1, true) then
        return "Balanced"
    elseif label:find("avoidance", 1, true) then
        return "Avoid"
    elseif label:find("defense", 1, true) or label:find("defensive", 1, true) then
        return "Defense"
    elseif label:find("stamina", 1, true) then
        return "Stam"
    elseif label:find("survivability", 1, true) then
        return "Survival"
    elseif label:find("main hand", 1, true) or string.find(label, "%f[%w]mh%f[%W]") then
        return "MH"
    elseif label:find("off hand", 1, true) or label:find("offhand", 1, true) or string.find(label, "%f[%w]oh%f[%W]") then
        return "OH"
    elseif label:find("dagger", 1, true) then
        return "Dagger"
    elseif label:find("crafted", 1, true) or label:find("crafting", 1, true) then
        return "Crafted"
    elseif label:find("haste", 1, true) then
        return "Haste"
    elseif label:find("set", 1, true) or string.find(label, "%d+p") then
        return "Set"
    elseif label:find("world boss", 1, true) then
        return "World"
    elseif label:find("pve", 1, true) then
        return "PvE"
    elseif label:find("aldor", 1, true) then
        return "Aldor"
    elseif label:find("scryer", 1, true) then
        return "Scryer"
    elseif label:find("alliance", 1, true) then
        return "Alliance"
    elseif label:find("horde", 1, true) then
        return "Horde"
    elseif label:find("demon", 1, true) or label:find("undead", 1, true) then
        return "Demons"
    elseif label:find("brutallus", 1, true) then
        return "Brutallus"
    elseif label:find("block", 1, true) then
        return "Block"
    end

    return nil
end

local function rankShortLabel(use)
    if not use then
        return "No match"
    elseif use.rank_group == "bis" then
        local variant = bisVariantLabel(use)
        return variant and ("BiS: " .. variant) or "BiS"
    elseif use.rank_group == "ranked" then
        return "Alt"
    elseif use.rank_group == "situational" then
        return "Sidegrade"
    elseif use.rank_group == "pvp" then
        return "PvP"
    elseif use.rank_group == "unrealistic" then
        return "Hard"
    end
    return "Optional"
end

local function displayRankInfo(use)
    if not use then
        return "No match", "missing"
    elseif use.display_rank_label then
        return use.display_rank_label, use.display_rank_kind or "backup"
    end

    local rank = tonumber(use.rank)
    if use.rank_group == "bis" then
        local variant = bisVariantLabel(use)
        return variant and ("BiS: " .. variant) or "BiS", "best"
    elseif use.rank_group == "ranked" then
        return "Alt", "ranked"
    elseif use.rank_group == "situational" then
        return "Sidegrade", "situational"
    elseif use.rank_group == "pvp" then
        return "PvP", "pvp"
    elseif use.rank_group == "unrealistic" then
        return "Hard", "hard"
    elseif rank and rank > 1 then
        return "Alt", "ranked"
    end

    return "Optional", "backup"
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
        if not rankLabelIsGeneric(use.rank_label) then
            return tostring(use.rank_label) .. " for " .. phaseLabel
        end
        return "BiS for " .. phaseLabel
    elseif use.rank_group == "ranked" then
        return "Alt for " .. phaseLabel
    elseif use.rank_group == "situational" then
        return "Sidegrade for a specific fight, role, or gearing setup"
    elseif use.rank_group == "pvp" then
        return "PvP option"
    elseif use.rank_group == "unrealistic" then
        return "Hard to obtain"
    end

    return "Optional alternative"
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

    local preferredIndex = BigBiSList:GetAvailabilityPhaseIndex(preferredPhaseKey)
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

local function isStrictUpgradeUse(candidate, current, preferredPhaseKey)
    if not candidate then
        return false
    elseif not current then
        return true
    elseif candidate.item_id and current.item_id and candidate.item_id == current.item_id then
        return false
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

    local candidateNumericRank = tonumber(candidate.rank) or 999
    local currentNumericRank = tonumber(current.rank) or 999
    if candidateNumericRank ~= currentNumericRank then
        return candidateNumericRank < currentNumericRank
    end

    local preferredIndex = BigBiSList:GetAvailabilityPhaseIndex(preferredPhaseKey)
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

    return false
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

local function betterSourceFilterKey(candidate, current)
    if not current then
        return candidate
    end

    local candidateOrder = SOURCE_FILTER_ORDER[candidate] or 50
    local currentOrder = SOURCE_FILTER_ORDER[current] or 50
    if candidateOrder < currentOrder then
        return candidate
    end
    return current
end

sourceFilterKey = function(source)
    if type(source) ~= "table" then
        return "unknown"
    end

    local sourceType = source.type or "unknown"
    if sourceType == "token_turnin" then
        local selected
        for _, tokenSource in ipairs(source.token_sources or {}) do
            selected = betterSourceFilterKey(sourceFilterKey(tokenSource), selected)
        end
        return selected or sourceType
    end

    if sourceType == "quest" and source.quest_starter_sources then
        local selected
        for _, starterSource in ipairs(source.quest_starter_sources or {}) do
            selected = betterSourceFilterKey(sourceFilterKey(starterSource), selected)
        end
        return selected or sourceType
    end

    if sourceType == "drop" or source.content_type then
        return SOURCE_FILTER_BY_CONTENT_TYPE[source.content_type] or "other_drop"
    end

    return sourceType
end

local function getSourceFilterKey(item)
    return sourceFilterKey(getPrimarySource(item))
end

local function addSourceFilterKey(sourceFilterKeys, seen, source, selectedPhaseIndex)
    if type(source) == "table" and sourceIsPhaseAvailable(source, selectedPhaseIndex) then
        addUnique(sourceFilterKeys, seen, sourceFilterKey(source))
    end
end

local function getSourceFilterKeys(item, selectedPhaseIndex)
    local sourceFilterKeys = {}
    local seen = {}

    if item then
        addSourceFilterKey(sourceFilterKeys, seen, item.primary_source, selectedPhaseIndex)
        for _, source in ipairs(item.sources or {}) do
            addSourceFilterKey(sourceFilterKeys, seen, source, selectedPhaseIndex)
        end
    end

    return sourceFilterKeys
end

local function sortSourceFilterKeys(a, b)
    local aOrder = SOURCE_FILTER_ORDER[a] or 50
    local bOrder = SOURCE_FILTER_ORDER[b] or 50
    if aOrder ~= bOrder then
        return aOrder < bOrder
    end
    return tostring(a) < tostring(b)
end

function FILTER_FACETS.sortCostFilterKeys(a, b)
    local aOrder = FILTER_FACETS.COST_FILTER_ORDER[a] or 50
    local bOrder = FILTER_FACETS.COST_FILTER_ORDER[b] or 50
    if aOrder ~= bOrder then
        return aOrder < bOrder
    end
    return tostring(a) < tostring(b)
end

local function getSourceZone(item)
    local source = getPrimarySource(item)
    return FILTER_FACETS.sourceLocationArea(source)
end

local function addZonesFromSource(zones, seen, source, includeDropZone, selectedPhaseIndex)
    if type(source) ~= "table" or not sourceIsPhaseAvailable(source, selectedPhaseIndex) then
        return
    end

    if source.type ~= "drop" or includeDropZone then
        addSourceZone(zones, seen, FILTER_FACETS.sourceLocationArea(source), selectedPhaseIndex)
    end

    if source.type == "token_turnin" then
        for _, tokenSource in ipairs(source.token_sources or {}) do
            addZonesFromSource(zones, seen, tokenSource, true, selectedPhaseIndex)
        end
    end

    if source.type == "quest" then
        for _, starterSource in ipairs(source.quest_starter_sources or {}) do
            addZonesFromSource(zones, seen, starterSource, true, selectedPhaseIndex)
        end
    end
end

local function getSourceZones(item, selectedPhaseIndex)
    local zones = {}
    local seen = {}

    if item then
        addZonesFromSource(zones, seen, item.primary_source, true, selectedPhaseIndex)
        for _, source in ipairs(item.sources or {}) do
            addZonesFromSource(zones, seen, source, false, selectedPhaseIndex)
        end
    end

    return zones
end

local function sourceHasZone(source, zone, includeDropZone, selectedPhaseIndex)
    if type(source) ~= "table" or not sourceIsPhaseAvailable(source, selectedPhaseIndex) then
        return false
    end

    if (source.type ~= "drop" or includeDropZone)
        and FILTER_FACETS.sourceLocationArea(source) == zone
        and sourceZoneIsPhaseAvailable(zone, selectedPhaseIndex) then
        return true
    end

    if source.type == "token_turnin" then
        for _, tokenSource in ipairs(source.token_sources or {}) do
            if sourceHasZone(tokenSource, zone, true, selectedPhaseIndex) then
                return true
            end
        end
    elseif source.type == "quest" then
        for _, starterSource in ipairs(source.quest_starter_sources or {}) do
            if sourceHasZone(starterSource, zone, true, selectedPhaseIndex) then
                return true
            end
        end
    end

    return false
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

local getItemName

local function addReputationsFromSource(reputations, seen, source)
    if type(source) ~= "table" then
        return
    end

    addReputationsFromRequirements(reputations, seen, source.requirements)

    if source.type == "token_turnin" then
        for _, tokenSource in ipairs(source.token_sources or {}) do
            addReputationsFromSource(reputations, seen, tokenSource)
        end
    elseif source.type == "quest" then
        for _, starterSource in ipairs(source.quest_starter_sources or {}) do
            addReputationsFromSource(reputations, seen, starterSource)
        end
    elseif source.type == "crafted" then
        for _, recipeSource in ipairs(source.recipe_sources or {}) do
            addReputationsFromSource(reputations, seen, recipeSource)
        end
    end
end

local function itemReputations(item)
    local reputations = {}
    local seen = {}
    addReputationsFromRequirements(reputations, seen, item and item.requirements)
    if item then
        addReputationsFromSource(reputations, seen, item.primary_source)
        for _, source in ipairs(item.sources or {}) do
            addReputationsFromSource(reputations, seen, source)
        end
    end
    table.sort(reputations)
    return reputations
end

local function buildItemMeta(index, itemId, item)
    local fallback = item or getIndexedItemFallback(index, itemId)
    local acquisitionItem = item or fallback
    local sourceType = getSourceType(acquisitionItem)
    local sourceFilter = getSourceFilterKey(acquisitionItem)
    local acquisitionPhase = getAcquisitionPhase(acquisitionItem)
    return {
        item_id = itemId,
        item = acquisitionItem,
        canonical_item = item,
        fallback_item = not item and fallback or nil,
        name = getItemName(itemId, item, fallback),
        source_summary = acquisitionItem and acquisitionItem.source_summary or "",
        source_type = sourceType,
        source_type_label = SOURCE_TYPE_LABELS[sourceType] or sourceType,
        source_filter_key = sourceFilter,
        source_filter_label = SOURCE_TYPE_LABELS[sourceFilter] or sourceFilter,
        source_filter_keys = getSourceFilterKeys(acquisitionItem),
        acquisition_phase = acquisitionPhase,
        acquisitionPhaseIndex = phaseIndex(acquisitionPhase),
        zone = getSourceZone(acquisitionItem),
        zones = getSourceZones(acquisitionItem),
        side = getSourceSide(acquisitionItem),
        sides = getSourceSides(acquisitionItem),
        binding = item and item.binding or "unknown",
        boe = item and item.boe,
        quality = (item and item.quality) or (fallback and fallback.quality),
        requirements = acquisitionItem and acquisitionItem.requirements,
        reputations = itemReputations(acquisitionItem),
        phase = {},
    }
end

local function getItemMetaFromIndex(index, itemId, item)
    itemId = tonumber(itemId)
    if not index or not itemId then
        return nil
    end

    index.itemMetaCache = index.itemMetaCache or {}
    index.itemMetaCacheOrder = index.itemMetaCacheOrder or {}
    local cached = index.itemMetaCache[itemId]
    if cached then
        return cached
    end

    item = item or getIndexedItem(index, itemId)
    return putBoundedCache(index.itemMetaCache, index.itemMetaCacheOrder, itemId, buildItemMeta(index, itemId, item), ITEM_META_CACHE_LIMIT)
end

local function getItemPhaseMeta(index, itemId, item, selectedPhaseIndex)
    local meta = getItemMetaFromIndex(index, itemId, item)
    if not meta or not selectedPhaseIndex then
        return meta
    end

    meta.phase[selectedPhaseIndex] = meta.phase[selectedPhaseIndex] or {
        source_filter_keys = getSourceFilterKeys(meta.item, selectedPhaseIndex),
        zones = getSourceZones(meta.item, selectedPhaseIndex),
    }
    return meta.phase[selectedPhaseIndex]
end

getItemName = function(itemId, item, fallback)
    if item and item.name and item.name ~= "" then
        return item.name
    elseif fallback and fallback.name and fallback.name ~= "" then
        return fallback.name
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

local ENHANCEMENT_READY_ACCESS_DETAILS = {
    ["Craft/AH"] = "Craft yourself or buy on the Auction House.",
    ["Drop/AH"] = "Farm the drop or buy on the Auction House.",
    ["Trade/AH"] = "Buy, trade, or check the Auction House.",
    Enchanter = "Find an enchanter or use your own profession.",
    Vendor = "Buy from the listed vendor.",
    PvP = "Buy from the PvP vendor.",
    ["Turn in"] = "Turn in the required token or currency.",
    Formula = "Learn or buy the listed formula.",
}

local function enhancementReadyAccessFromOptions(accessOptions)
    local hasCrafted
    local hasDrop
    local hasVendor
    local hasPvp
    local hasTokenTurnin
    local hasFormula
    local hasTrade

    for _, option in ipairs(accessOptions or {}) do
        local sourceType = option.source_type
        if FILTER_FACETS.optionIsReportedOnly(option) then
            -- Keep incomplete seller reports available to the inspector, but
            -- never present them as a ready acquisition route.
        elseif sourceType == "crafted" then
            hasCrafted = true
        elseif sourceType == "drop" or sourceType == "world_drop" then
            hasDrop = true
        elseif sourceType == "vendor" then
            hasVendor = true
        elseif sourceType == "pvp" then
            hasPvp = true
        elseif sourceType == "token_turnin" then
            hasTokenTurnin = true
        elseif sourceType == "taught_by_item" then
            hasFormula = true
        elseif sourceType == "trade" then
            hasTrade = true
        end
    end

    if hasCrafted then
        return "Craft/AH"
    elseif hasDrop then
        return "Drop/AH"
    elseif hasVendor then
        return "Vendor"
    elseif hasPvp then
        return "PvP"
    elseif hasTokenTurnin then
        return "Turn in"
    elseif hasFormula then
        return "Formula"
    elseif hasTrade then
        return "Trade/AH"
    end

    return nil
end

local function enhancementReadyAccessFromSummary(sourceSummary)
    local summary = lower(sourceSummary)
    if summary == "" then
        return nil
    elseif string.find(summary, "crafted:", 1, true) then
        return "Craft/AH"
    elseif string.find(summary, "drop:", 1, true) or string.find(summary, "contained in:", 1, true) then
        return "Drop/AH"
    elseif string.find(summary, "vendor:", 1, true) then
        return "Vendor"
    elseif string.find(summary, "pvp", 1, true) then
        return "PvP"
    end

    return nil
end

local CRAFTED_MARKET_CONSUMABLE_CATEGORIES = {
    battle_elixir = true,
    elixir = true,
    flask = true,
    food = true,
    guardian_elixir = true,
    potion = true,
    weapon_oil = true,
}

local function consumableReadyAccessOverride(consumable, itemIndex)
    local category = consumable and consumable.category
    if itemIndex and consumable and consumable.item_categories then
        category = consumable.item_categories[itemIndex] or category
    end

    if CRAFTED_MARKET_CONSUMABLE_CATEGORIES[category or ""] then
        return "Craft/AH"
    end

    return nil
end

local function applyEnhancementReadyAccess(row, accessOptions, sourceSummary, fallbackLabel, preferredLabel)
    local label = enhancementReadyAccessFromOptions(accessOptions)
        or preferredLabel
        or enhancementReadyAccessFromSummary(sourceSummary)
        or fallbackLabel
    if not label or label == "" then
        return
    end

    row.ready_access_label = label
    row.ready_access_detail = ENHANCEMENT_READY_ACCESS_DETAILS[label]
end

local function enhancementSourceKey(entityType, entityId)
    return tostring(entityType or "item") .. ":" .. tostring(entityId or "")
end

local function buildUse(index, className, specName, phaseKey, slotEntry, itemEntry)
    local useEntry = itemEntry
    local slotName
    local sourceUrl

    if not useEntry then
        useEntry = inflateUseRef(index, className)
        className = useEntry and useEntry["class"]
        specName = useEntry and useEntry.spec
        phaseKey = useEntry and useEntry.phase
        slotName = useEntry and useEntry.slot
        sourceUrl = useEntry and useEntry.source_url
    else
        slotName = slotEntry and slotEntry.slot
        sourceUrl = slotEntry and slotEntry.source_url
    end

    local itemId = useEntry and useEntry.item_id
    local item = getIndexedItem(index, itemId)
    local accessItem = item or getIndexedItemFallback(index, itemId)
    local meta = getItemMetaFromIndex(index, itemId, item) or {}
    local requirements = mergedRequirements(accessItem and accessItem.requirements, useEntry and useEntry.requirements)

    local row = {
        class = className,
        spec = specName,
        phase = phaseKey,
        phaseIndex = phaseIndex((useEntry and useEntry.content_phase) or (slotEntry and slotEntry.content_phase) or phaseKey),
        content_phase = (useEntry and useEntry.content_phase) or (slotEntry and slotEntry.content_phase),
        slot = slotName,
        item_id = itemId,
        item = accessItem,
        name = meta.name or getItemName(itemId, item),
        rank = useEntry and useEntry.rank,
        rank_label = (useEntry and useEntry.rank_label) or "Option",
        rank_group = (useEntry and useEntry.rank_group) or "option",
        context = (useEntry and useEntry.context) or "standard",
        note = useEntry and useEntry.note,
        source_url = sourceUrl,
        source_summary = meta.source_summary or "",
        source_type = meta.source_type or "unknown",
        source_type_label = meta.source_type_label or SOURCE_TYPE_LABELS.unknown,
        source_filter_key = meta.source_filter_key or "unknown",
        source_filter_label = meta.source_filter_label or SOURCE_TYPE_LABELS.unknown,
        source_filter_keys = meta.source_filter_keys or {},
        acquisition_phase = meta.acquisition_phase or "PR",
        acquisitionPhaseIndex = meta.acquisitionPhaseIndex or phaseIndex("PR"),
        zone = meta.zone,
        zones = meta.zones or {},
        side = meta.side,
        sides = meta.sides or {},
        binding = meta.binding or "unknown",
        boe = meta.boe,
        quality = meta.quality,
        requirements = requirements,
        reputations = rowReputationsWithMeta(meta.reputations, requirements),
        _access_context = {
            item = accessItem,
            requirements = useEntry and useEntry.requirements,
            options = { entityType = "item" },
        },
    }

    row.display_rank_label, row.display_rank_kind = displayRankInfo(row)
    row.recommendation_summary = recommendationSummary(row)
    return row
end

local function levelingValueText(row)
    if not row then
        return "No leveling recommendation available."
    end

    local specName = row.spec or "this spec"
    local levelMin = tonumber(row.level_min) or 1
    local levelMax = tonumber(row.level_max) or levelMin
    if levelMax > levelMin then
        return "Recommended for " .. specName .. " from level " .. tostring(levelMin) .. " to " .. tostring(levelMax)
    end
    return "Recommended for " .. specName .. " at level " .. tostring(levelMin)
end

function LEVELING_HELPERS.itemAllowsClass(index, entry)
    local restrictions = (index.dataSource or {}).item_class_restrictions or {}
    local classes = restrictions[entry.item_id] or restrictions[tostring(entry.item_id)]
    return type(classes) ~= "table" or #classes == 0 or slotListContains(classes, entry.class)
end

local function buildLevelingGearRow(index, levelingGearRef)
    local entry = inflateCompactRecord(index, "leveling_gear", levelingGearRef)
    if not entry or not LEVELING_HELPERS.itemAllowsClass(index, entry) then
        return nil
    end

    local itemId = entry.item_id
    local item = getIndexedItem(index, itemId)
    local accessItem = item or getIndexedItemFallback(index, itemId)
    local meta = getItemMetaFromIndex(index, itemId, item) or {}
    local requirements = mergedRequirements(accessItem and accessItem.requirements, entry.requirements)
    local levelMin = tonumber(entry.level_min) or 1
    local levelMax = tonumber(entry.level_max) or levelMin
    local levelLabel = entry.level_label or (levelMax > levelMin and ("Recommended from " .. tostring(levelMin) .. "-" .. tostring(levelMax)) or ("Recommended at " .. tostring(levelMin)))
    local categoryLabel = entry.category_label or "Recommended"
    local tooltipLevelLabel = levelMax > levelMin and ("Leveling " .. tostring(levelMin) .. "-" .. tostring(levelMax)) or ("Leveling " .. tostring(levelMin))

    local row = {
        class = entry.class,
        spec = entry.spec,
        phase = LEVELING_PHASE_KEY,
        phaseIndex = phaseIndex(LEVELING_PHASE_KEY),
        leveling = true,
        level_min = levelMin,
        level_max = levelMax,
        level_label = levelLabel,
        level_value_text = levelingValueText(entry),
        slot = entry.slot,
        item_id = itemId,
        item = accessItem,
        name = meta.name or getItemName(itemId, item),
        rank = entry.rank,
        rank_label = categoryLabel,
        rank_group = "option",
        category_label = categoryLabel,
        leveling_category_key = LEVELING_HELPERS.categoryKey(categoryLabel),
        tooltip_level_label = tooltipLevelLabel,
        section = entry.section,
        source_note = entry.source_note,
        source_url = entry.source_url,
        source_summary = meta.source_summary or "",
        source_type = meta.source_type or "unknown",
        source_type_label = meta.source_type_label or SOURCE_TYPE_LABELS.unknown,
        source_filter_key = meta.source_filter_key or "unknown",
        source_filter_label = meta.source_filter_label or SOURCE_TYPE_LABELS.unknown,
        source_filter_keys = meta.source_filter_keys or {},
        acquisition_phase = meta.acquisition_phase or "PR",
        acquisitionPhaseIndex = meta.acquisitionPhaseIndex or phaseIndex("PR"),
        zone = meta.zone,
        zones = meta.zones or {},
        side = meta.side,
        sides = meta.sides or {},
        binding = meta.binding or "unknown",
        boe = meta.boe,
        quality = meta.quality,
        requirements = requirements,
        reputations = rowReputationsWithMeta(meta.reputations, requirements),
        display_rank_label = levelLabel,
        display_rank_kind = "leveling",
        recommendation_summary = levelLabel,
        _access_context = {
            item = accessItem,
            requirements = entry.requirements,
            options = { entityType = "item" },
        },
    }

    return row
end

local function buildLevelingRecommendationRow(index, recommendationRef)
    local entry = inflateCompactRecord(index, "leveling_recommendation", recommendationRef)
    if not entry or not LEVELING_HELPERS.itemAllowsClass(index, entry) then
        return nil
    end

    local itemId = entry.item_id
    local item = getIndexedItem(index, itemId)
    local accessItem = item or getIndexedItemFallback(index, itemId)
    local meta = getItemMetaFromIndex(index, itemId, item) or {}
    local requirements = mergedRequirements(accessItem and accessItem.requirements, entry.requirements)
    local levelMin = tonumber(entry.level_min) or 1
    local levelMax = tonumber(entry.level_max) or levelMin
    local levelLabel = levelMax > levelMin and ("Recommended from " .. tostring(levelMin) .. "-" .. tostring(levelMax)) or ("Recommended at " .. tostring(levelMin))
    local reasonTags = entry.reason_tags or {}
    local primaryTag = reasonTags[1]
    local categoryLabel = primaryTag == "best_survival" and "Survival"
        or primaryTag == "best_hit" and "Hit"
        or primaryTag == "best_easy_source" and "Easy source"
        or "Recommended"
    local tooltipLevelLabel = levelMax > levelMin and ("Leveling " .. tostring(levelMin) .. "-" .. tostring(levelMax)) or ("Leveling " .. tostring(levelMin))
    local recommendationSummary = entry.source_summary or meta.source_summary or ""
    if primaryTag and primaryTag ~= "" then
        recommendationSummary = LEVELING_HELPERS.reasonTagLabel(primaryTag)
    elseif recommendationSummary == "" then
        recommendationSummary = levelLabel
    end

    local row = {
        class = entry.class,
        spec = entry.spec,
        race = entry.race,
        phase = LEVELING_PHASE_KEY,
        phaseIndex = phaseIndex(LEVELING_PHASE_KEY),
        leveling = true,
        computed_recommendation = true,
        level_min = levelMin,
        level_max = levelMax,
        level_band = entry.level_band,
        level_label = levelLabel,
        level_value_text = levelingValueText(entry),
        slot = entry.slot,
        item_id = itemId,
        variant_id = entry.variant_id,
        item = accessItem,
        name = meta.name or getItemName(itemId, item),
        rank = entry.rank,
        rank_label = categoryLabel,
        rank_group = "option",
        category_label = categoryLabel,
        leveling_category_key = LEVELING_HELPERS.categoryKey(categoryLabel),
        tooltip_level_label = tooltipLevelLabel,
        section = "Leveling recommendations",
        source_note = entry.source_summary or meta.source_summary or "",
        source_url = entry.source_url,
        source_summary = entry.source_summary or meta.source_summary or "",
        source_type = meta.source_type or "unknown",
        source_type_label = meta.source_type_label or SOURCE_TYPE_LABELS.unknown,
        source_filter_key = entry.source_bucket or meta.source_filter_key or "unknown",
        source_filter_label = SOURCE_TYPE_LABELS[entry.source_bucket or meta.source_filter_key or "unknown"] or SOURCE_TYPE_LABELS.unknown,
        source_filter_keys = meta.source_filter_keys or {},
        acquisition_phase = meta.acquisition_phase or "PR",
        acquisitionPhaseIndex = meta.acquisitionPhaseIndex or phaseIndex("PR"),
        zone = meta.zone,
        zones = meta.zones or {},
        side = meta.side,
        sides = meta.sides or {},
        binding = meta.binding or "unknown",
        boe = meta.boe,
        quality = meta.quality,
        requirements = requirements,
        reputations = rowReputationsWithMeta(meta.reputations, requirements),
        context = entry.context,
        score = entry.score,
        score_delta_pct = entry.score_delta_pct,
        reason_tags = reasonTags,
        display_rank_label = levelLabel,
        display_rank_kind = "leveling",
        recommendation_summary = recommendationSummary,
        _access_context = {
            item = accessItem,
            requirements = entry.requirements,
            options = { entityType = "item" },
        },
    }

    return row
end

function LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
    if not row then
        return false
    end

    local levelMin = tonumber(row.level_min) or 1
    local levelMax = tonumber(row.level_max) or levelMin
    return levelMin <= selectedLevel and selectedLevel <= levelMax
end

function LEVELING_HELPERS.sortForLevel(a, b, selectedLevel)
    local maxLevel = BigBiSList.maxLevelingLevel or 69
    local aActive = (a.level_max or maxLevel) >= selectedLevel
    local bActive = (b.level_max or maxLevel) >= selectedLevel
    if aActive ~= bActive then
        return aActive
    end
    if (a.level_min or 0) ~= (b.level_min or 0) then
        return (a.level_min or 0) > (b.level_min or 0)
    end
    if (a.level_max or 0) ~= (b.level_max or 0) then
        return (a.level_max or 0) > (b.level_max or 0)
    end
    if (a.rank or 999) ~= (b.rank or 999) then
        return (a.rank or 999) < (b.rank or 999)
    end
    return lower(a.name) < lower(b.name)
end

function LEVELING_HELPERS.isExactRace(row, selectedRace)
    return row
        and selectedRace
        and selectedRace ~= ""
        and selectedRace ~= "*"
        and row.race == selectedRace
end

function LEVELING_HELPERS.isGenericRace(row)
    return not row or not row.race or row.race == "" or row.race == "*"
end

function LEVELING_HELPERS.rowBeats(candidate, current, selectedRace, selectedLevel)
    if not candidate then
        return false
    elseif not current then
        return true
    end

    local candidateExactRace = LEVELING_HELPERS.isExactRace(candidate, selectedRace)
    local currentExactRace = LEVELING_HELPERS.isExactRace(current, selectedRace)
    if candidateExactRace ~= currentExactRace then
        return candidateExactRace
    end

    local candidateOptimized = candidate.computed_recommendation and true or false
    local currentOptimized = current.computed_recommendation and true or false
    if candidateOptimized ~= currentOptimized then
        return candidateOptimized
    end

    local candidateGeneric = LEVELING_HELPERS.isGenericRace(candidate)
    local currentGeneric = LEVELING_HELPERS.isGenericRace(current)
    if candidateGeneric ~= currentGeneric then
        return candidateGeneric
    end

    return LEVELING_HELPERS.sortForLevel(candidate, current, selectedLevel)
end

function LEVELING_HELPERS.addDisplayRow(grouped, seenBySlot, row, selectedRace, selectedLevel)
    if not row or not row.slot or not row.item_id then
        return
    end

    local slotName = row.slot
    grouped[slotName] = grouped[slotName] or { slot = slotName, items = {} }
    seenBySlot[slotName] = seenBySlot[slotName] or {}

    local key = tostring(row.item_id)
    local existingIndex = seenBySlot[slotName][key]
    if existingIndex then
        local current = grouped[slotName].items[existingIndex]
        if LEVELING_HELPERS.rowBeats(row, current, selectedRace, selectedLevel) then
            grouped[slotName].items[existingIndex] = row
        end
        return
    end

    table.insert(grouped[slotName].items, row)
    seenBySlot[slotName][key] = #grouped[slotName].items
end

function LEVELING_HELPERS.sortByNextLevel(a, b)
    if (a.level_min or 0) ~= (b.level_min or 0) then
        return (a.level_min or 0) < (b.level_min or 0)
    end
    if (a.level_max or 0) ~= (b.level_max or 0) then
        return (a.level_max or 0) < (b.level_max or 0)
    end
    if (a.rank or 999) ~= (b.rank or 999) then
        return (a.rank or 999) < (b.rank or 999)
    end
    return lower(a.name) < lower(b.name)
end

local function rowHasZone(row, zone, selectedPhaseIndex)
    if not row or not zone or zone == "" then
        return false
    end

    if row.item then
        if sourceHasZone(row.item.primary_source, zone, true, selectedPhaseIndex) then
            return true
        end
        for _, source in ipairs(row.item.sources or {}) do
            if sourceHasZone(source, zone, false, selectedPhaseIndex) then
                return true
            end
        end
        return false
    end

    if row.zone == zone and sourceZoneIsPhaseAvailable(zone, selectedPhaseIndex) then
        return true
    end

    for _, rowZone in ipairs(row.zones or {}) do
        if rowZone == zone and sourceZoneIsPhaseAvailable(rowZone, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

local function rowMatchesZoneFilter(row, zone, selectedPhaseIndex)
    if not zone or zone == "all" then
        return true
    end
    return rowHasZone(row, zone, selectedPhaseIndex)
end

local function rowMatchesAnySelectedZone(row, selectedZones, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedZones) then
        return true
    end

    for zone, selected in pairs(selectedZones or {}) do
        if selected and rowHasZone(row, zone, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

local function rowHasSourceFilterKey(row, sourceType, selectedPhaseIndex)
    if not row or not sourceType or sourceType == "" then
        return false
    end

    local phaseMeta = row.item and getItemPhaseMeta(BigBiSList:GetDataIndex(), row.item_id, row.item, selectedPhaseIndex) or nil
    local sourceFilterKeys = phaseMeta and phaseMeta.source_filter_keys or row.source_filter_keys
    for _, rowSourceType in ipairs(sourceFilterKeys or {}) do
        if rowSourceType == sourceType then
            return true
        end
    end

    if (not sourceFilterKeys or #sourceFilterKeys == 0)
        and (row.source_filter_key == sourceType or row.source_type == sourceType)
        and (row.acquisitionPhaseIndex or 999) <= (selectedPhaseIndex or 999) then
        return true
    end

    return false
end

local function rowMatchesSourceFilter(row, sourceType, selectedPhaseIndex)
    if not sourceType or sourceType == "all" then
        return true
    end
    return rowHasSourceFilterKey(row, sourceType, selectedPhaseIndex)
end

local function rowMatchesAnySelectedSourceType(row, selectedSourceTypes, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedSourceTypes) then
        return true
    end

    for sourceType, selected in pairs(selectedSourceTypes or {}) do
        if selected and rowHasSourceFilterKey(row, sourceType, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

local function accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    if type(option) ~= "table" then
        return false
    elseif not selectedPhaseIndex then
        return true
    elseif (option.acquisitionPhaseIndex or phaseIndex(option.acquisition_phase or "PR")) > selectedPhaseIndex then
        return false
    elseif option.zone and not (option.source and option.source.type == "quest")
        and not sourceZoneIsPhaseAvailable(option.zone, selectedPhaseIndex) then
        return false
    elseif option.source and not sourceIsPhaseAvailable(option.source, selectedPhaseIndex) then
        return false
    end
    if option.trade_sources and #option.trade_sources > 0 then
        for _, source in ipairs(option.trade_sources) do
            if sourceIsPhaseAvailable(source, selectedPhaseIndex) then return true end
        end
        return false
    end
    return true
end

local function optionHasZone(option, zone, selectedPhaseIndex)
    if not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) or not zone or zone == "" then
        return false
    end

    if option.zone == zone and sourceZoneIsPhaseAvailable(zone, selectedPhaseIndex) then
        return true
    end

    for _, optionZone in ipairs(option.zones or {}) do
        if optionZone == zone and sourceZoneIsPhaseAvailable(optionZone, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

local function optionMatchesZoneFilter(option, zone, selectedPhaseIndex)
    if not zone or zone == "all" then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end
    return optionHasZone(option, zone, selectedPhaseIndex)
end

local function optionMatchesAnySelectedZone(option, selectedZones, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedZones) then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end

    for zone, selected in pairs(selectedZones or {}) do
        if selected and optionHasZone(option, zone, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

local function optionMatchesSourceFilter(option, sourceType, selectedPhaseIndex)
    if not sourceType or sourceType == "all" then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end

    return not FILTER_FACETS.optionIsReportedOnly(option)
        and accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
        and (option.source_filter_key == sourceType or option.source_type == sourceType)
end

local function optionMatchesAnySelectedSourceType(option, selectedSourceTypes, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedSourceTypes) then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end

    for sourceType, selected in pairs(selectedSourceTypes or {}) do
        if selected and optionMatchesSourceFilter(option, sourceType, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

local requirementsHaveReputation

function FILTER_FACETS.optionHasCost(option, costKey, selectedPhaseIndex)
    if FILTER_FACETS.optionIsReportedOnly(option)
        or not accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
        or not costKey
        or costKey == "" then
        return false
    end

    for _, optionCostKey in ipairs(option.cost_keys or {}) do
        if optionCostKey == costKey then
            return true
        end
    end

    return false
end

function FILTER_FACETS.optionMatchesCostFilter(option, costKey, selectedPhaseIndex)
    if not costKey or costKey == "all" then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end
    return FILTER_FACETS.optionHasCost(option, costKey, selectedPhaseIndex)
end

function FILTER_FACETS.optionMatchesAnySelectedCost(option, selectedCosts, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedCosts) then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end

    for costKey, selected in pairs(selectedCosts or {}) do
        if selected and FILTER_FACETS.optionHasCost(option, costKey, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

function FILTER_FACETS.optionHasVendor(option, vendorKey, selectedPhaseIndex)
    if FILTER_FACETS.optionIsReportedOnly(option)
        or not accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
        or not vendorKey
        or vendorKey == "" then
        return false
    end
    return option.vendor_key == vendorKey
end

function FILTER_FACETS.optionMatchesVendorFilter(option, vendorKey, selectedPhaseIndex)
    if not vendorKey or vendorKey == "all" then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end
    return FILTER_FACETS.optionHasVendor(option, vendorKey, selectedPhaseIndex)
end

function FILTER_FACETS.optionMatchesAnySelectedVendor(option, selectedVendors, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedVendors) then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end

    for vendorKey, selected in pairs(selectedVendors or {}) do
        if selected and FILTER_FACETS.optionHasVendor(option, vendorKey, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

function FILTER_FACETS.optionHasReputation(option, reputation, selectedPhaseIndex)
    if not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) or not reputation or reputation == "" then
        return false
    end

    if requirementsHaveReputation(option.requirements, reputation) then
        return true
    end

    for _, optionReputation in ipairs(option.reputations or {}) do
        if optionReputation == reputation then
            return true
        end
    end

    return false
end

function FILTER_FACETS.optionMatchesReputationFilter(option, reputation, selectedPhaseIndex)
    if not reputation or reputation == "all" then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end
    return FILTER_FACETS.optionHasReputation(option, reputation, selectedPhaseIndex)
end

function FILTER_FACETS.optionMatchesAnySelectedReputation(option, selectedReputations, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedReputations) then
        return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
    end

    for reputation, selected in pairs(selectedReputations or {}) do
        if selected and FILTER_FACETS.optionHasReputation(option, reputation, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

local function hasActiveSourceContextFilter(filters)
    return (filters and filters.sourceType and filters.sourceType ~= "all")
        or tableHasAnyEnabled(filters and filters.sourceTypes)
        or (filters and filters.zone and filters.zone ~= "all")
        or tableHasAnyEnabled(filters and filters.zones)
        or (filters and filters.cost and filters.cost ~= "all")
        or tableHasAnyEnabled(filters and filters.costs)
        or (filters and filters.vendor and filters.vendor ~= "all")
        or tableHasAnyEnabled(filters and filters.vendors)
        or (filters and filters.reputation and filters.reputation ~= "all")
        or tableHasAnyEnabled(filters and filters.reputations)
end

function FILTER_FACETS.hasActiveOptionContextFilter(filters)
    return hasActiveSourceContextFilter(filters)
        or (filters and filters._pre_raid)
        or (filters and filters.faction and filters.faction ~= "all")
end

function FILTER_FACETS.optionMatchesFaction(option, faction)
    if not faction or faction == "all" then
        return true
    end
    local hasSide = false
    for _, side in ipairs(option and option.sides or {}) do
        hasSide = true
        if side == faction then
            return true
        end
    end
    if option and option.side then
        hasSide = true
        if option.side == faction then
            return true
        end
    end
    return not hasSide
end

local function optionMatchesSourceContext(option, filters, selectedPhaseIndex)
    return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
        and (not (filters and filters._pre_raid) or FILTER_FACETS.optionIsPreRaid(option, selectedPhaseIndex))
        and FILTER_FACETS.optionMatchesFaction(option, filters and filters.faction)
        and optionMatchesSourceFilter(option, filters and filters.sourceType, selectedPhaseIndex)
        and optionMatchesAnySelectedSourceType(option, filters and filters.sourceTypes, selectedPhaseIndex)
        and optionMatchesZoneFilter(option, filters and filters.zone, selectedPhaseIndex)
        and optionMatchesAnySelectedZone(option, filters and filters.zones, selectedPhaseIndex)
        and FILTER_FACETS.optionMatchesCostFilter(option, filters and filters.cost, selectedPhaseIndex)
        and FILTER_FACETS.optionMatchesAnySelectedCost(option, filters and filters.costs, selectedPhaseIndex)
        and FILTER_FACETS.optionMatchesVendorFilter(option, filters and filters.vendor, selectedPhaseIndex)
        and FILTER_FACETS.optionMatchesAnySelectedVendor(option, filters and filters.vendors, selectedPhaseIndex)
        and FILTER_FACETS.optionMatchesReputationFilter(option, filters and filters.reputation, selectedPhaseIndex)
        and FILTER_FACETS.optionMatchesAnySelectedReputation(option, filters and filters.reputations, selectedPhaseIndex)
end

local function rowHasAccessOptionMatchingFilterContext(row, filters, selectedPhaseIndex)
    if not FILTER_FACETS.hasActiveOptionContextFilter(filters) then
        return true
    end

    for _, option in ipairs(buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}) do
        if optionMatchesSourceContext(option, filters, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

requirementsHaveReputation = function(requirements, reputation)
    for _, requirement in ipairs(requirements or {}) do
        if type(requirement) == "table" and requirement.type == "reputation" and requirement.reputation == reputation then
            return true
        elseif type(requirement) == "table" and requirement.type == "faction_choice" then
            for _, choice in ipairs(requirement.choices or {}) do
                if choice == reputation then
                    return true
                end
            end
        end
    end
    return false
end

local function rowHasReputation(row, reputation, selectedPhaseIndex)
    if not row or not reputation or reputation == "" then
        return false
    end

    if requirementsHaveReputation(row.requirements, reputation) then
        return true
    end

    for _, rowReputation in ipairs(row.reputations or {}) do
        if rowReputation == reputation then
            return true
        end
    end

    return false
end

local function rowMatchesReputationFilter(row, reputation, selectedPhaseIndex)
    if not reputation or reputation == "all" then
        return true
    end
    return rowHasReputation(row, reputation, selectedPhaseIndex)
end

function FILTER_FACETS.rowMatchesAnySelectedReputation(row, selectedReputations, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedReputations) then
        return true
    end

    for reputation, selected in pairs(selectedReputations or {}) do
        if selected and rowHasReputation(row, reputation, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

function FILTER_FACETS.rowHasCost(row, costKey, selectedPhaseIndex)
    if not row or not costKey or costKey == "" then
        return false
    end

    for _, option in ipairs(buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}) do
        if FILTER_FACETS.optionHasCost(option, costKey, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

function FILTER_FACETS.rowMatchesCostFilter(row, costKey, selectedPhaseIndex)
    if not costKey or costKey == "all" then
        return true
    end
    return FILTER_FACETS.rowHasCost(row, costKey, selectedPhaseIndex)
end

function FILTER_FACETS.rowMatchesAnySelectedCost(row, selectedCosts, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedCosts) then
        return true
    end

    for costKey, selected in pairs(selectedCosts or {}) do
        if selected and FILTER_FACETS.rowHasCost(row, costKey, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

function FILTER_FACETS.rowHasVendor(row, vendorKey, selectedPhaseIndex)
    if not row or not vendorKey or vendorKey == "" then
        return false
    end

    for _, option in ipairs(buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}) do
        if FILTER_FACETS.optionHasVendor(option, vendorKey, selectedPhaseIndex) then
            return true
        end
    end

    return false
end

function FILTER_FACETS.rowMatchesVendorFilter(row, vendorKey, selectedPhaseIndex)
    if not vendorKey or vendorKey == "all" then
        return true
    end
    return FILTER_FACETS.rowHasVendor(row, vendorKey, selectedPhaseIndex)
end

function FILTER_FACETS.rowMatchesAnySelectedVendor(row, selectedVendors, selectedPhaseIndex)
    if not tableHasAnyEnabled(selectedVendors) then
        return true
    end

    for vendorKey, selected in pairs(selectedVendors or {}) do
        if selected and FILTER_FACETS.rowHasVendor(row, vendorKey, selectedPhaseIndex) then
            return true
        end
    end

    return false
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

function FILTER_FACETS.rowAccessOptionsContainText(row, search)
    if not search or search == "" then
        return true
    end

    for _, option in ipairs(buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}) do
        if containsText(option.label, search)
            or containsText(option.source_summary, search)
            or containsText(option.source_filter_label, search)
            or containsText(option.cost_summary, search)
            or containsText(option.vendor_label, search) then
            return true
        end

        for _, costLabel in ipairs(option.cost_labels or {}) do
            if containsText(costLabel, search) then
                return true
            end
        end

        for _, reputation in ipairs(option.reputations or {}) do
            if containsText(reputation, search) then
                return true
            end
        end
    end

    return false
end

local function includeByFilter(row, filters, selectedPhaseIndex)
    filters = filters or {}

    if selectedPhaseIndex then
        local options = buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}
        local available = #options == 0
        for _, option in ipairs(options) do
            if accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then available = true; break end
        end
        if not available then return false end
    end

    if filters._pre_raid then
        local eligible = false
        for _, option in ipairs(buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}) do
            if optionMatchesSourceContext(option, filters, selectedPhaseIndex) then eligible = true; break end
        end
        if not eligible then return false end
    end

    if filters.hideIgnored and filters.ignoredItems and filters.ignoredItems[tostring(row.item_id)] then
        return false
    end

    if filters.search and filters.search ~= "" then
        local found = containsText(row.name, filters.search)
            or containsText(row.slot, filters.search)
            or containsText(row.slot_label, filters.search)
            or containsText(row.detail, filters.search)
            or containsText(row.source_summary, filters.search)
            or containsText(row.rank_label, filters.search)
            or containsText(row.ranking_search_text, filters.search)
            or containsText(row.source_note, filters.search)
            or containsText(row.section, filters.search)
            or containsText(row.level_label, filters.search)
            or containsText(row.level_value_text, filters.search)
            or containsText(row.category_label, filters.search)
            or containsText(row.recommendation_summary, filters.search)
            or containsText(row.ready_access_label, filters.search)
            or FILTER_FACETS.rowAccessOptionsContainText(row, filters.search)
        if not found then
            return false
        end
    end

    if not rowMatchesSelectedSlots(row.slot, filters.slots, row.slots) then
        return false
    end

    if not rowMatchesSourceFilter(row, filters.sourceType, selectedPhaseIndex) then
        return false
    end
    if not rowMatchesAnySelectedSourceType(row, filters.sourceTypes, selectedPhaseIndex) then
        return false
    end
    if not rowMatchesZoneFilter(row, filters.zone, selectedPhaseIndex) then
        return false
    end
    if not rowMatchesAnySelectedZone(row, filters.zones, selectedPhaseIndex) then
        return false
    end
    if not FILTER_FACETS.rowMatchesCostFilter(row, filters.cost, selectedPhaseIndex) then
        return false
    end
    if not FILTER_FACETS.rowMatchesAnySelectedCost(row, filters.costs, selectedPhaseIndex) then
        return false
    end
    if not FILTER_FACETS.rowMatchesVendorFilter(row, filters.vendor, selectedPhaseIndex) then
        return false
    end
    if not FILTER_FACETS.rowMatchesAnySelectedVendor(row, filters.vendors, selectedPhaseIndex) then
        return false
    end
    -- Faction narrows which acquisition path is presented, but it must not
    -- make neutral rows (including rows with no structured access options)
    -- disappear from the corpus. Only explicit acquisition filters require a
    -- matching option at row-filter time.
    if hasActiveSourceContextFilter(filters) and not rowHasAccessOptionMatchingFilterContext(row, filters, selectedPhaseIndex) then
        return false
    end
    if not rowMatchesReputationFilter(row, filters.reputation, selectedPhaseIndex) then
        return false
    end
    if not FILTER_FACETS.rowMatchesAnySelectedReputation(row, filters.reputations, selectedPhaseIndex) then
        return false
    end

    if row.leveling then
        local categoryKey = row.leveling_category_key or LEVELING_HELPERS.categoryKey(row.category_label)
        if LEVELING_HELPERS.isCategoryKey(filters.rankGroup) and categoryKey ~= filters.rankGroup then
            return false
        end
        if tableHasAnyEnabled(filters.rankGroups) then
            local hasLevelingCategory = false
            local matchesLevelingCategory = false
            for key, selected in pairs(filters.rankGroups or {}) do
                if selected and LEVELING_HELPERS.isCategoryKey(key) then
                    hasLevelingCategory = true
                    if key == categoryKey then
                        matchesLevelingCategory = true
                    end
                end
            end
            if hasLevelingCategory and not matchesLevelingCategory then
                return false
            end
        end
    else
        if filters.rankGroup and filters.rankGroup ~= "all" and row.rank_group ~= filters.rankGroup then
            return false
        end
        if tableHasAnyEnabled(filters.rankGroups) and not filters.rankGroups[row.rank_group] then
            return false
        end
    end

    local owned = FILTER_FACETS.tableValueById(filters.ownedItems, row.item_id)
    if not owned then
        for _, candidateItemId in ipairs(row.item_ids or {}) do
            owned = FILTER_FACETS.tableValueById(filters.ownedItems, candidateItemId)
            if owned then
                break
            end
        end
    end
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

FILTER_FACETS.CLASSIC_RAID_ZONES = {
    ["Molten Core"] = true, ["Blackwing Lair"] = true, ["Zul'Gurub"] = true,
    ["Ruins of Ahn'Qiraj"] = true, ["Ahn'Qiraj"] = true, Naxxramas = true,
}

function FILTER_FACETS.sourceRequiresRaid(source, selectedPhaseIndex)
    if type(source) ~= "table" then return true end
    if source.tradeable then return false end
    local hasRecipeRoutes = source.type == "crafted" and source.recipe_sources and #source.recipe_sources > 0
    if (source.type ~= "quest" and not hasRecipeRoutes
        and (RAID_ZONE_PHASE[source.zone] or FILTER_FACETS.CLASSIC_RAID_ZONES[source.zone]))
        or (source.type ~= "quest" and source.type ~= "token_turnin" and not hasRecipeRoutes and source.content_type == "raid")
        or RAID_QUEST_PHASE_BY_ID[source.quest_id] then return true end
    for _, req in ipairs(source.requirements or {}) do
        if req.reputation == "The Scale of the Sands" or req.reputation == "Ashtongue Deathsworn" or req.reputation == "The Violet Eye" then return true end
    end
    for _, key in ipairs({ "token_sources", "quest_starter_sources", "recipe_sources" }) do
        local children = source[key]
        if children and #children > 0 then
            local allRaid = true
            for _, child in ipairs(children) do
                if sourceIsPhaseAvailable(child, selectedPhaseIndex)
                    and not FILTER_FACETS.sourceRequiresRaid(child, selectedPhaseIndex) then allRaid = false; break end
            end
            if allRaid then return true end
        end
    end
    return false
end

function FILTER_FACETS.optionIsPreRaid(option, selectedPhaseIndex)
    if not option then return false end
    local isTrade = option.is_trade_option or option.source_type == "trade"
    if isTrade and not option.is_inferred_trade_option then return true end
    if option.source_type == "unknown" then return false end
    for _, req in ipairs(option.requirements or {}) do
        if req.reputation == "The Scale of the Sands" or req.reputation == "Ashtongue Deathsworn" or req.reputation == "The Violet Eye" then return false end
    end
    if isTrade then
        -- Legacy craft hints do not prove that a raid-only reward can be traded.
        for _, source in ipairs(option.trade_sources or {}) do
            if sourceIsPhaseAvailable(source, selectedPhaseIndex)
                and not FILTER_FACETS.sourceRequiresRaid(source, selectedPhaseIndex) then return true end
        end
        return false
    end
    return not FILTER_FACETS.sourceRequiresRaid(option.source, selectedPhaseIndex)
end

function FILTER_FACETS.progressionFilters(filters, phaseKey)
    if phaseKey ~= "PR" then return filters end
    local scoped = {}
    for key, value in pairs(filters or {}) do scoped[key] = value end
    scoped._pre_raid = true
    return scoped
end

function FILTER_FACETS.primaryAccessOption(options)
    for _, option in ipairs(options or {}) do
        if option.is_primary and FILTER_FACETS.optionIsCompleteRoute(option) then
            return option
        end
    end
    for _, option in ipairs(options or {}) do
        if FILTER_FACETS.optionIsCompleteRoute(option) then
            return option
        end
    end
    for _, option in ipairs(options or {}) do
        if option.is_primary then
            return option
        end
    end
    return options and options[1] or nil
end

function BigBiSList:RowMatchesFilters(row, filters, phaseKey)
    local selectedPhaseIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil
    return includeByFilter(row, FILTER_FACETS.progressionFilters(filters, phaseKey), selectedPhaseIndex)
end

function FILTER_FACETS.nextAvailableOptionPhase(option, selectedPhaseIndex)
    for candidateIndex = selectedPhaseIndex or 1, #PHASE_ORDER do
        if accessOptionIsPhaseAvailable(option, candidateIndex) then return candidateIndex end
    end
    return nil
end

function BigBiSList:GetMatchingRowAccessOption(row, filters, phaseKey, includeFuture)
    local options = buildRowAccessOptions(self:GetDataIndex(), row) or {}
    local scopedFilters = FILTER_FACETS.progressionFilters(filters, phaseKey)
    local selectedPhaseIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil
    local primary = FILTER_FACETS.primaryAccessOption(options)
    local best, bestPhase
    for _, option in ipairs(options) do
        local candidatePhase = selectedPhaseIndex
        if includeFuture then
            candidatePhase = FILTER_FACETS.nextAvailableOptionPhase(option, selectedPhaseIndex)
        end
        if (not includeFuture or candidatePhase)
            and FILTER_FACETS.optionIsCompleteRoute(option)
            and optionMatchesSourceContext(option, scopedFilters, candidatePhase)
            and (not best or (candidatePhase or 0) < (bestPhase or 0)
                or (candidatePhase == bestPhase and option == primary)) then
            best, bestPhase = option, candidatePhase
        end
    end
    return best
end

function FILTER_FACETS.accessOptionLocationLabel(option)
    if not option then
        return ""
    elseif option.source_summary and option.source_summary ~= "" then
        return option.source_summary
    elseif option.vendor_label and option.vendor_label ~= "" then
        return option.vendor_label
    elseif option.zone and option.zone ~= "" then
        return option.zone
    end
    return option.label or ""
end

function BigBiSList:GetRowAcquisitionDisplay(row, filters, phaseKey, includeFutureMatches)
    local hasContextFilter = FILTER_FACETS.hasActiveOptionContextFilter(filters)
    local option = self:GetMatchingRowAccessOption(row, filters, phaseKey, false)
    local selectedPhaseIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil
    if not option and not hasActiveSourceContextFilter(filters) then
        local scopedFilters = FILTER_FACETS.progressionFilters(filters, phaseKey)
        for _, candidate in ipairs(buildRowAccessOptions(self:GetDataIndex(), row) or {}) do
            if FILTER_FACETS.optionIsReportedOnly(candidate)
                and optionMatchesSourceContext(candidate, scopedFilters, selectedPhaseIndex) then
                option = candidate
                break
            end
        end
    end
    if not option and (includeFutureMatches or not hasContextFilter) then
        option = self:GetMatchingRowAccessOption(row, filters, phaseKey, true)
    end
    local acquisitionPhase = option and option.acquisition_phase or row and row.acquisition_phase or "PR"
    local available = option and accessOptionIsPhaseAvailable(option, selectedPhaseIndex) or false
    local nextPhaseIndex = option and FILTER_FACETS.nextAvailableOptionPhase(option, selectedPhaseIndex) or nil
    local future = nextPhaseIndex ~= nil and selectedPhaseIndex ~= nil and nextPhaseIndex > selectedPhaseIndex
    if future then acquisitionPhase = PHASE_ORDER[nextPhaseIndex] end

    return {
        option = option,
        source_label = option and (option.source_filter_label or SOURCE_TYPE_LABELS[option.source_type])
            or (row and (row.source_filter_label or row.source_type_label))
            or SOURCE_TYPE_LABELS.unknown,
        location_label = option and FILTER_FACETS.accessOptionLocationLabel(option) or (row and row.source_summary) or "",
        source_summary = option and option.source_summary or (row and row.source_summary) or "",
        acquisition_phase = acquisitionPhase,
        acquisition_phase_index = phaseIndex(acquisitionPhase),
        available = available,
        future = future,
        status = available and (FILTER_FACETS.optionIsCompleteRoute(option) and "ready" or "unknown")
            or (future and "future" or "unavailable"),
    }
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
    return "Optional"
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
    local selectedIndex = BigBiSList:GetAvailabilityPhaseIndex(selectedPhaseKey)
    local score = 0
    local hasCurrent = false
    local hasCurrentBis = false
    local firstFutureBis
    local futureBisCount = 0
    local futureOptionCount = 0
    local futureBisPhases = {}
    local futureOptionPhases = {}
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
                futureBisPhases[use.phaseIndex] = true
                if not firstFutureBis or use.phaseIndex < firstFutureBis then
                    firstFutureBis = use.phaseIndex
                end
            else
                futureOptionCount = futureOptionCount + 1
                futureOptionPhases[use.phaseIndex] = true
            end
        end
    end

    if hasCurrentBis then
        score = score + 60
        addPlannerReason(reasons, reasonSeen, "Best in slot this phase")
    elseif hasCurrent then
        score = score + 30
        addPlannerReason(reasons, reasonSeen, "Alternative this phase")
    elseif firstFutureBis then
        score = score + 35
        addPlannerReason(reasons, reasonSeen, "Best in slot in " .. (PHASE_DISPLAY[PHASE_ORDER[firstFutureBis]] or "a later phase"))
    end

    score = score + (futureBisCount * 8)
    score = score + (futureOptionCount * 4)

    -- Recommendation variants still contribute to the score independently;
    -- presentation deduplicates phase recommendations instead of exposing use counts.
    for index, phase in ipairs(PHASE_ORDER) do
        local phaseLabel = PHASE_DISPLAY[phase] or phase
        if futureBisPhases[index] then
            addPlannerReason(reasons, reasonSeen, "Best in slot in " .. phaseLabel)
        end
        if futureOptionPhases[index] then
            addPlannerReason(reasons, reasonSeen, "Alternative in " .. phaseLabel)
        end
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

function BigBiSList:GetPlayerRaceName()
    if UnitRace then
        local ok, localizedName, raceToken = pcall(UnitRace, "player")
        if ok then
            return RACE_TOKEN_NAMES[raceToken] or localizedName
        end
    end
    return nil
end

function BigBiSList:GetEquipmentSlotDefinitions()
    return EQUIPMENT_SLOTS
end

function BigBiSList:GetPhaseShortName(phaseKey)
    return PHASE_SHORT_DISPLAY[phaseKey] or self:GetPhaseDisplayName(phaseKey)
end

local function currentServerTimestamp()
    if GetServerTime then
        local ok, timestamp = pcall(GetServerTime)
        if ok and type(timestamp) == "number" then
            return timestamp
        end
    end

    if time then
        local ok, timestamp = pcall(time)
        if ok and type(timestamp) == "number" then
            return timestamp
        end
    end

    return nil
end

local function getPhaseStartEpoch(phaseKey)
    local data = BigBiSListData or {}
    local schedule = data.phase_schedules and data.phase_schedules[data.active_schedule]
    for _, phase in ipairs((schedule and schedule.phase_starts) or data.phases or {}) do
        if phase.key == phaseKey and type(phase.starts_at_epoch) == "number" then
            return phase.starts_at_epoch
        end
    end

    if phaseKey == "PR" then
        return 0
    end

    return nil
end

function BigBiSList:GetCurrentPhaseKey(nowEpoch)
    local timestamp = tonumber(nowEpoch) or currentServerTimestamp()
    local currentPhase = "PR"
    if not timestamp then
        return currentPhase
    end

    for _, phaseKey in ipairs(PHASE_ORDER) do
        local startsAt = getPhaseStartEpoch(phaseKey)
        if startsAt and startsAt <= timestamp then
            currentPhase = phaseKey
        end
    end

    return currentPhase
end

function BigBiSList:GetProgressionContext(selectedPhase, nowEpoch)
    local contentPhase = selectedPhase == "PR" and self:GetCurrentPhaseKey(nowEpoch) or selectedPhase
    return {
        list_phase = selectedPhase,
        content_phase = contentPhase,
        content_phase_index = phaseIndex(contentPhase),
        pre_raid = selectedPhase == "PR",
        schedule_id = (BigBiSListData or {}).active_schedule,
    }
end

function BigBiSList:GetAvailabilityPhaseIndex(selectedPhase)
    return self:GetProgressionContext(selectedPhase).content_phase_index
end

function BigBiSList:IsAccessOptionPhaseAvailable(option, selectedPhaseIndex)
    return accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
end

function BigBiSList:GetAccessOptionNextAvailablePhase(option, selectedPhaseIndex)
    return FILTER_FACETS.nextAvailableOptionPhase(option, selectedPhaseIndex)
end

function BigBiSList:IsPreRaidAccessOption(option, selectedPhaseIndex)
    return FILTER_FACETS.optionIsPreRaid(option, selectedPhaseIndex)
end

function BigBiSList:GetSourceTypeLabels()
    return SOURCE_TYPE_LABELS
end

function BigBiSList:GetClassSpecIndex()
    if self.classSpecIndex then
        return self.classSpecIndex
    end

    local data = BigBiSListData or {}
    local index = {
        classes = data.classes or {},
        classNames = {},
        specsByClass = {},
    }

    for _, classData in ipairs(index.classes) do
        if classData.name then
            table.insert(index.classNames, classData.name)
            index.specsByClass[classData.name] = classData.specs or {}
        end
    end

    self.classSpecIndex = index
    return index
end

local function sortUseList(uses)
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

FILTER_FACETS.SHARED_PROGRESSION_INDEX_FIELDS = {
    "itemRecordsById", "itemFallbackRecordsById", "itemCache", "itemFallbackCache",
    "itemMetaCache", "itemMetaCacheOrder", "rowAccessCache", "rowAccessCacheOrder",
    "levelingGearRefsByItemId", "levelingGearRefsByClassSpec", "levelingGearCache",
    "levelingRecommendationRefsByItemId", "levelingRecommendationRefsByClassSpec",
    "levelingRecommendationCache", "enhancement",
}

function BigBiSList:GetDataIndex(selectedPhaseKey)
    local livePhase = self:GetCurrentPhaseKey()
    local scheduleId = (BigBiSListData or {}).active_schedule
    local contentPhase = selectedPhaseKey and self:GetProgressionContext(selectedPhaseKey).content_phase or livePhase
    if phaseIndex(contentPhase) == 999 then contentPhase = livePhase end
    if not self.dataIndex or self.dataIndex.livePhase ~= livePhase or self.dataIndex.scheduleId ~= scheduleId
        or self.dataIndex.dataSource ~= BigBiSListData then
        self.progressionIndexes = {}
        self.progressionIndexOrder = {}
        self.progressionBase = nil
    end
    if self.progressionIndexes and self.progressionIndexes[contentPhase] then
        self.dataIndex = self.progressionIndexes[contentPhase]
        return self.dataIndex
    end

    local data = BigBiSListData or {}
    local compact = data.format == 2
    local sharedBase = compact and self.progressionBase or nil
    local classSpecIndex = self:GetClassSpecIndex()
    local index = {
        dataSource = data,
        livePhase = livePhase,
        contentPhase = contentPhase,
        scheduleId = scheduleId,
        compact = compact,
        schemas = data.schemas or {},
        schemaPositions = {},
        itemRecordsById = {},
        itemFallbackRecordsById = {},
        itemCache = {},
        itemFallbackCache = {},
        itemMetaCache = {},
        itemMetaCacheOrder = {},
        rowAccessCache = {},
        rowAccessCacheOrder = {},
        itemUseCache = {},
        wishlistSummaryCache = {},
        levelingGearCache = {},
        levelingRecommendationCache = {},
        tooltipUseCache = {},
        itemsById = {},
        itemFallbacksById = {},
        classes = classSpecIndex.classes,
        classNames = classSpecIndex.classNames,
        specsByClass = classSpecIndex.specsByClass,
        phaseOrder = PHASE_ORDER,
        phaseDisplay = PHASE_DISPLAY,
        sourceTypes = compact and (data.source_types or {}) or {},
        zones = compact and (data.zones or {}) or {},
        lists = {},
        usesByItemId = {},
        tooltipUsesByItemId = {},
        useRefsByItemId = {},
        tooltipUseRefsByItemId = {},
        useRefsByClassSpec = {},
        useRefsByClassSpecPhase = {},
        levelingGearRefsByItemId = {},
        levelingGearRefsByClassSpec = {},
        levelingRecommendationRefsByItemId = {},
        levelingRecommendationRefsByClassSpec = {},
        enhancement = {
            gems = data.gems or {},
            gemSourcesById = {},
            enchants = data.enchants or {},
            enchantSourcesByKey = {},
            enchantEffectsByKey = {},
            consumables = data.consumables or {},
        },
    }

    for schemaName in pairs(index.schemas) do
        index.schemaPositions[schemaName] = schemaPositions(index.schemas, schemaName)
    end
    if sharedBase then
        for _, key in ipairs(FILTER_FACETS.SHARED_PROGRESSION_INDEX_FIELDS) do index[key] = sharedBase[key] end
    end

    if compact then
        if not sharedBase then
            for _, itemRecord in ipairs(data.items or {}) do
                local itemId = compactField(index, "item", itemRecord, "id")
                if itemId then
                    index.itemRecordsById[itemId] = itemRecord
                end
            end

            for _, itemFallbackRecord in ipairs(data.item_fallbacks or {}) do
                local itemId = compactField(index, "item_fallback", itemFallbackRecord, "id")
                if itemId then
                    index.itemFallbackRecordsById[itemId] = itemFallbackRecord
                end
            end
        end

        index.itemsById = setmetatable({}, {
            __index = function(_, itemId)
                return getIndexedItem(index, itemId)
            end,
        })

        index.usesByItemId = setmetatable({}, {
            __index = function(_, itemId)
                return BigBiSList:GetItemUses(itemId, index.contentPhase)
            end,
        })

        index.tooltipUsesByItemId = setmetatable({}, {
            __index = function(_, itemId)
                return BigBiSList:GetTooltipUses(itemId, index.contentPhase)
            end,
        })

        local tooltipAliasesByItemId = {}
        for _, aliasRecord in ipairs(data.tooltip_aliases or {}) do
            tooltipAliasesByItemId[aliasRecord[1]] = aliasRecord[2]
        end

        for _, useRef in ipairs(data.uses or {}) do
            local itemId = compactField(index, "use", useRef, "item_id")
            local className = compactField(index, "use", useRef, "class")
            local specName = compactField(index, "use", useRef, "spec")
            local phaseKey = compactField(index, "use", useRef, "phase")
            local useContentPhase = compactField(index, "use", useRef, "content_phase")

            if phaseKey ~= "PR" or not useContentPhase or useContentPhase == contentPhase then
                addUseRef(index.useRefsByItemId, itemId, useRef)
                addUseRef(index.tooltipUseRefsByItemId, itemId, useRef)
                for _, aliasItemId in ipairs(tooltipAliasesByItemId[itemId] or {}) do
                    addUseRef(index.tooltipUseRefsByItemId, aliasItemId, useRef)
                end

                table.insert(ensureNestedUseBucket(index.useRefsByClassSpec, className, specName), useRef)
                table.insert(ensureNestedUseBucket(index.useRefsByClassSpecPhase, className, specName, phaseKey), useRef)
            end
        end

        if not sharedBase then
            for _, levelingGearRef in ipairs(data.leveling_gear or {}) do
                local itemId = compactField(index, "leveling_gear", levelingGearRef, "item_id")
                local className = compactField(index, "leveling_gear", levelingGearRef, "class")
                local specName = compactField(index, "leveling_gear", levelingGearRef, "spec")
                addUseRef(index.levelingGearRefsByItemId, itemId, levelingGearRef)
                table.insert(ensureNestedUseBucket(index.levelingGearRefsByClassSpec, className, specName), levelingGearRef)
            end

            for _, recommendationRef in ipairs(data.leveling_recommendations or {}) do
                local itemId = compactField(index, "leveling_recommendation", recommendationRef, "item_id")
                local className = compactField(index, "leveling_recommendation", recommendationRef, "class")
                local specName = compactField(index, "leveling_recommendation", recommendationRef, "spec")
                addUseRef(index.levelingRecommendationRefsByItemId, itemId, recommendationRef)
                table.insert(ensureNestedUseBucket(index.levelingRecommendationRefsByClassSpec, className, specName), recommendationRef)
            end

            for _, sourceData in ipairs(data.gem_sources or {}) do
                index.enhancement.gemSourcesById[compactField(index, "source_record", sourceData, "id")] = sourceData
            end

            for _, sourceData in ipairs(data.enchant_sources or {}) do
                local key = enhancementSourceKey(compactField(index, "source_record", sourceData, "type") or "item", compactField(index, "source_record", sourceData, "id"))
                index.enhancement.enchantSourcesByKey[key] = index.enhancement.enchantSourcesByKey[key] or {}
                table.insert(index.enhancement.enchantSourcesByKey[key], sourceData)
            end

            for _, effectData in ipairs(data.enchant_effects or {}) do
                local key = enhancementSourceKey(compactField(index, "enchant_effect", effectData, "type") or "item", compactField(index, "enchant_effect", effectData, "id"))
                index.enhancement.enchantEffectsByKey[key] = effectData
            end
        end
    else
        local sourceSeen = {}
        local zoneSeen = {}

        for _, item in ipairs(data.items or {}) do
            index.itemsById[item.id] = item
            for _, sourceFilter in ipairs(getSourceFilterKeys(item)) do
                addUnique(index.sourceTypes, sourceSeen, sourceFilter)
            end
            for _, zone in ipairs(getSourceZones(item)) do
                addUnique(index.zones, zoneSeen, zone)
            end
        end

        for _, itemFallback in ipairs(data.item_fallbacks or {}) do
            index.itemFallbacksById[itemFallback.id] = itemFallback
        end

        for _, sourceData in ipairs(data.gem_sources or {}) do
            index.enhancement.gemSourcesById[sourceData.id] = sourceData
        end

        for _, sourceData in ipairs(data.enchant_sources or {}) do
            local key = enhancementSourceKey(sourceData.type or "item", sourceData.id)
            index.enhancement.enchantSourcesByKey[key] = index.enhancement.enchantSourcesByKey[key] or {}
            table.insert(index.enhancement.enchantSourcesByKey[key], sourceData)
        end

        for _, effectData in ipairs(data.enchant_effects or {}) do
            local key = enhancementSourceKey(effectData.type or "item", effectData.id)
            index.enhancement.enchantEffectsByKey[key] = effectData
        end

        table.sort(index.sourceTypes, sortSourceFilterKeys)
        table.sort(index.zones)

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
                        local useContentPhase = slotEntry.content_phase or phaseData.content_phase
                        if phaseKey ~= "PR" or not useContentPhase or useContentPhase == contentPhase then
                            local contextualSlot = slotEntry
                            if useContentPhase and not slotEntry.content_phase then
                                contextualSlot = {}
                                for key, value in pairs(slotEntry) do contextualSlot[key] = value end
                                contextualSlot.content_phase = useContentPhase
                            end
                            table.insert(specLists[phaseKey], slotEntry)

                            for _, itemEntry in ipairs(slotEntry.items or {}) do
                                if itemEntry.item_id then
                                    local use = buildUse(index, className, specName, phaseKey, contextualSlot, itemEntry)
                                    addUseRef(index.useRefsByItemId, use.item_id, use)
                                    addUseRef(index.tooltipUseRefsByItemId, use.item_id, use)
                                    for _, source in ipairs((use.item and use.item.sources) or {}) do
                                        for _, starterSource in ipairs(source.quest_starter_sources or {}) do
                                            addUseRef(index.tooltipUseRefsByItemId, tonumber(starterSource.quest_starter_item_id), use)
                                        end
                                    end
                                    table.insert(ensureNestedUseBucket(index.useRefsByClassSpec, className, specName), use)
                                    table.insert(ensureNestedUseBucket(index.useRefsByClassSpecPhase, className, specName, phaseKey), use)
                                end
                            end
                        end
                    end
                end
            end
        end

        for _, levelingGear in ipairs(data.leveling_gear or {}) do
            addUseRef(index.levelingGearRefsByItemId, levelingGear.item_id, levelingGear)
            table.insert(ensureNestedUseBucket(index.levelingGearRefsByClassSpec, levelingGear["class"], levelingGear.spec), levelingGear)
        end

        for _, recommendation in ipairs(data.leveling_recommendations or {}) do
            addUseRef(index.levelingRecommendationRefsByItemId, recommendation.item_id, recommendation)
            table.insert(ensureNestedUseBucket(index.levelingRecommendationRefsByClassSpec, recommendation["class"], recommendation.spec), recommendation)
        end

        index.usesByItemId = setmetatable({}, {
            __index = function(_, itemId)
                return BigBiSList:GetItemUses(itemId, index.contentPhase)
            end,
        })
        index.tooltipUsesByItemId = setmetatable({}, {
            __index = function(_, itemId)
                return BigBiSList:GetTooltipUses(itemId, index.contentPhase)
            end,
        })
    end

    self.dataIndex = index
    if compact and not sharedBase then
        self.progressionBase = {}
        for _, key in ipairs(FILTER_FACETS.SHARED_PROGRESSION_INDEX_FIELDS) do self.progressionBase[key] = index[key] end
    end
    self.progressionIndexes = self.progressionIndexes or {}
    self.progressionIndexOrder = self.progressionIndexOrder or {}
    putBoundedCache(self.progressionIndexes, self.progressionIndexOrder, contentPhase, index, 3)
    return index
end

function BigBiSList:GetItemData(itemId)
    return getIndexedItem(self:GetDataIndex(), itemId)
end

function BigBiSList:GetItemMeta(itemId)
    local index = self:GetDataIndex()
    return getItemMetaFromIndex(index, itemId)
end

function BigBiSList:GetRowAccessOptions(row)
    return buildRowAccessOptions(self:GetDataIndex(), row)
end

function BigBiSList:GetAccessOptionDetailFields(option)
    return FILTER_FACETS.accessOptionDetailFields(option)
end

function FILTER_FACETS.sameAccessOption(a, b)
    if a == b then
        return true
    elseif type(a) ~= "table" or type(b) ~= "table" then
        return false
    elseif a.source_identity and b.source_identity then
        return a.source_identity == b.source_identity
    end
    return a.source_type == b.source_type
        and a.vendor_key == b.vendor_key
        and a.location_area == b.location_area
        and a.cost_summary == b.cost_summary
end

function BigBiSList:GetRowSellerGroups(row, selectedOption, phaseKey)
    local groups = {
        selected = nil,
        alternatives = {},
        reported = {},
    }
    local complete = {}
    local selectedPhaseIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil

    for _, option in ipairs(self:GetRowAccessOptions(row) or {}) do
        if option.is_vendor_purchase
            and (not phaseKey or (accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
                and (phaseKey ~= "PR" or FILTER_FACETS.optionIsPreRaid(option, selectedPhaseIndex)))
                or FILTER_FACETS.sameAccessOption(option, selectedOption)) then
            if option.vendor_details_status == "complete" then
                table.insert(complete, option)
                if selectedOption and FILTER_FACETS.sameAccessOption(option, selectedOption) then
                    groups.selected = option
                end
            else
                table.insert(groups.reported, option)
            end
        end
    end

    if not selectedOption and not groups.selected then
        for _, option in ipairs(complete) do
            if option.is_primary then
                groups.selected = option
                break
            end
        end
        if not groups.selected and complete[1] then
            groups.selected = complete[1]
        end
    end

    for _, option in ipairs(complete) do
        if not FILTER_FACETS.sameAccessOption(option, groups.selected) then
            table.insert(groups.alternatives, option)
        end
    end
    return groups
end

function BigBiSList:GetItemUses(itemId, selectedPhaseKey)
    itemId = tonumber(itemId)
    if not itemId then
        return {}
    end

    local index = self:GetDataIndex(selectedPhaseKey)
    if index.itemUseCache[itemId] then
        return index.itemUseCache[itemId]
    end

    local uses = {}
    for _, useRef in ipairs(index.useRefsByItemId[itemId] or {}) do
        table.insert(uses, buildUse(index, useRef))
    end
    sortUseList(uses)
    index.itemUseCache[itemId] = uses
    return uses
end

function BigBiSList:GetTooltipUses(itemId, selectedPhaseKey)
    itemId = tonumber(itemId)
    if not itemId then
        return {}
    end

    local index = self:GetDataIndex(selectedPhaseKey)
    if index.tooltipUseCache[itemId] then
        return index.tooltipUseCache[itemId]
    end

    local uses = {}
    for _, useRef in ipairs(index.tooltipUseRefsByItemId[itemId] or {}) do
        table.insert(uses, buildUse(index, useRef))
    end
    sortUseList(uses)
    index.tooltipUseCache[itemId] = uses
    return uses
end

function FILTER_FACETS.classSpecName(specData)
    if type(specData) == "table" then
        return specData.name
    end
    return specData
end

function FILTER_FACETS.orderedClassSpecNames(index, className, selectedSpec)
    local names = {}
    local seen = {}

    if selectedSpec and selectedSpec ~= "" then
        for _, specData in ipairs(index.specsByClass[className] or {}) do
            if FILTER_FACETS.classSpecName(specData) == selectedSpec then
                addUnique(names, seen, selectedSpec)
                break
            end
        end
    end

    for _, specData in ipairs(index.specsByClass[className] or {}) do
        addUnique(names, seen, FILTER_FACETS.classSpecName(specData))
    end
    return names
end

function FILTER_FACETS.wishlistUseIsBetter(candidate, current)
    if not candidate then
        return false
    elseif not current then
        return true
    end

    local candidateRankOrder = RANK_GROUP_ORDER[candidate.rank_group] or 50
    local currentRankOrder = RANK_GROUP_ORDER[current.rank_group] or 50
    if candidateRankOrder ~= currentRankOrder then
        return candidateRankOrder < currentRankOrder
    end

    local candidateRank = tonumber(candidate.rank) or 999
    local currentRank = tonumber(current.rank) or 999
    if candidateRank ~= currentRank then
        return candidateRank < currentRank
    end
    if candidate.phaseIndex ~= current.phaseIndex then
        return candidate.phaseIndex < current.phaseIndex
    end

    local candidateSlot = slotIndex(candidate.slot)
    local currentSlot = slotIndex(current.slot)
    if candidateSlot ~= currentSlot then
        return candidateSlot < currentSlot
    end
    if lower(candidate.rank_label) ~= lower(current.rank_label) then
        return lower(candidate.rank_label) < lower(current.rank_label)
    end
    if lower(candidate.context) ~= lower(current.context) then
        return lower(candidate.context) < lower(current.context)
    end
    return tostring(candidate.source_url or "") < tostring(current.source_url or "")
end

function FILTER_FACETS.wishlistRankShortLabel(use)
    if not use then
        return "—"
    end
    return FILTER_FACETS.WISHLIST_RANK_LABELS[use.rank_group] or "Optional"
end

function FILTER_FACETS.buildWishlistSpecRanking(specName, selectedSpec, usesByPhase, classOrderIndex)
    local ranking = {
        spec = specName,
        selected = specName == selectedSpec,
        class_order_index = classOrderIndex,
        phases = {},
        phase_cells = {},
        relevant = false,
        best_rank_order = 999,
        best_numeric_rank = 999,
        earliest_phase_index = 999,
    }

    for phaseOrderIndex, phaseKey in ipairs(PHASE_ORDER) do
        local use = usesByPhase and usesByPhase[phaseKey] or nil
        local shortLabel = FILTER_FACETS.wishlistRankShortLabel(use)
        local cell = {
            phase = phaseKey,
            phase_index = phaseOrderIndex,
            phase_label = PHASE_DISPLAY[phaseKey],
            phase_short_label = PHASE_SHORT_DISPLAY[phaseKey],
            short_label = shortLabel,
            label = shortLabel,
            use = use,
            rank_group = use and use.rank_group or nil,
            rank = use and use.rank or nil,
            matched = use ~= nil,
        }
        ranking.phases[phaseKey] = cell
        table.insert(ranking.phase_cells, cell)

        if use then
            local rankOrder = RANK_GROUP_ORDER[use.rank_group] or 50
            ranking.relevant = true
            if rankOrder < ranking.best_rank_order
                or (rankOrder == ranking.best_rank_order and (tonumber(use.rank) or 999) < ranking.best_numeric_rank) then
                ranking.best_rank_order = rankOrder
                ranking.best_numeric_rank = tonumber(use.rank) or 999
            end
            if phaseOrderIndex < ranking.earliest_phase_index then
                ranking.earliest_phase_index = phaseOrderIndex
            end
            if FILTER_FACETS.wishlistUseIsBetter(use, ranking.best_use) then
                ranking.best_use = use
            end
        end
    end

    return ranking
end

function FILTER_FACETS.useMatchesProgressionContext(use, selectedPhaseKey)
    return use.phase ~= "PR" or not use.content_phase or not selectedPhaseKey or selectedPhaseKey == "PR"
        or phaseIndex(use.content_phase) <= BigBiSList:GetAvailabilityPhaseIndex(selectedPhaseKey)
end

function BigBiSList:GetWishlistExpansionSummary(itemId, className, selectedSpec, selectedPhaseKey)
    itemId = tonumber(itemId)
    if not itemId then
        return nil
    end

    local index = self:GetDataIndex(selectedPhaseKey)
    local cacheKey = table.concat({ tostring(itemId), tostring(className or ""), tostring(selectedSpec or ""), tostring(selectedPhaseKey or "") }, "|")
    if index.wishlistSummaryCache[cacheKey] then
        return index.wishlistSummaryCache[cacheKey]
    end

    local usesBySpecPhase = {}
    local slotSeen = {}
    local slots = {}
    local bestClassUse
    for _, use in ipairs(self:GetItemUses(itemId, selectedPhaseKey)) do
        if use.class == className and FILTER_FACETS.useMatchesProgressionContext(use, selectedPhaseKey) then
            local specPhases = ensurePath(usesBySpecPhase, use.spec)
            if FILTER_FACETS.wishlistUseIsBetter(use, specPhases[use.phase]) then
                specPhases[use.phase] = use
            end
            addUnique(slots, slotSeen, use.slot)
            if FILTER_FACETS.wishlistUseIsBetter(use, bestClassUse) then
                bestClassUse = use
            end
        end
    end

    table.sort(slots, function(a, b)
        local aIndex = slotIndex(a)
        local bIndex = slotIndex(b)
        if aIndex ~= bIndex then
            return aIndex < bIndex
        end
        return tostring(a) < tostring(b)
    end)

    local specRankings = {}
    local relevantSpecRankings = {}
    local selectedSpecRanking
    local bestRelevantUse
    local earliestPhaseIndex = 999
    local bestRankOrder = 999
    for displayIndex, specName in ipairs(FILTER_FACETS.orderedClassSpecNames(index, className, selectedSpec)) do
        local classOrderIndex = displayIndex
        for rawIndex, specData in ipairs(index.specsByClass[className] or {}) do
            if FILTER_FACETS.classSpecName(specData) == specName then
                classOrderIndex = rawIndex
                break
            end
        end

        local ranking = FILTER_FACETS.buildWishlistSpecRanking(specName, selectedSpec, usesBySpecPhase[specName], classOrderIndex)
        ranking.display_order_index = displayIndex
        table.insert(specRankings, ranking)
        if ranking.relevant then
            table.insert(relevantSpecRankings, ranking)
        end
        if ranking.selected then
            selectedSpecRanking = ranking
        end
    end

    local selectedRelevant = selectedSpecRanking and selectedSpecRanking.relevant or false
    local rankingPool = selectedRelevant and { selectedSpecRanking } or relevantSpecRankings
    for _, ranking in ipairs(rankingPool) do
        if ranking.best_rank_order < bestRankOrder then
            bestRankOrder = ranking.best_rank_order
        end
        if ranking.earliest_phase_index < earliestPhaseIndex then
            earliestPhaseIndex = ranking.earliest_phase_index
        end
        if FILTER_FACETS.wishlistUseIsBetter(ranking.best_use, bestRelevantUse) then
            bestRelevantUse = ranking.best_use
        end
    end

    local classRelevant = #relevantSpecRankings > 0
    local summary = {
        item_id = itemId,
        class = className,
        selected_spec = selectedSpec,
        phase_order = PHASE_ORDER,
        spec_rankings = specRankings,
        relevant_spec_rankings = relevantSpecRankings,
        selected_spec_ranking = selectedSpecRanking,
        selected_spec_relevant = selectedRelevant,
        class_relevant = classRelevant,
        slots = slots,
        slot_label = #slots > 0 and table.concat(slots, ", ") or "—",
        best_use = bestRelevantUse or bestClassUse,
        best_class_use = bestClassUse,
        best_rank_order = bestRankOrder,
        best_numeric_rank = bestRelevantUse and (tonumber(bestRelevantUse.rank) or 999) or 999,
        best_rank_sort = bestRelevantUse
            and (((RANK_GROUP_ORDER[bestRelevantUse.rank_group] or 50) * 1000) + (tonumber(bestRelevantUse.rank) or 999))
            or 999999,
        earliest_phase_index = earliestPhaseIndex,
        relevance_sort = selectedRelevant and 0 or (classRelevant and 1 or 2),
        not_ranked_label = not classRelevant and ("Not ranked for " .. tostring(className or "this class")) or nil,
    }

    local searchParts = { tostring(className or "") }
    for _, ranking in ipairs(specRankings) do
        if ranking.relevant then
            table.insert(searchParts, ranking.spec)
            for _, cell in ipairs(ranking.phase_cells) do
                if cell.matched then
                    table.insert(searchParts, cell.phase_label)
                    table.insert(searchParts, cell.short_label)
                end
            end
        end
    end
    summary.ranking_search_text = table.concat(searchParts, " ")

    index.wishlistSummaryCache[cacheKey] = summary
    return summary
end

function FILTER_FACETS.normalizeWishlistItemIds(wishlistItems)
    local itemIds = {}
    local seen = {}
    for key, value in pairs(wishlistItems or {}) do
        local itemId
        if (type(value) == "number" or type(value) == "string") and tonumber(value) then
            itemId = tonumber(value)
        elseif value then
            itemId = tonumber(key)
        end
        if itemId and not seen[itemId] then
            seen[itemId] = true
            table.insert(itemIds, itemId)
        end
    end
    table.sort(itemIds)
    return itemIds
end

function FILTER_FACETS.wishlistRowMatchesRelevance(row, filters)
    local relevance = filters and (filters.wishlistRelevance or filters.relevance)
    if not relevance or relevance == "all" then
        return true
    elseif relevance == "selected" or relevance == "selected_spec" then
        return row.selected_spec_relevant
    elseif relevance == "class" or relevance == "other_specs" then
        return row.class_relevant and (relevance ~= "other_specs" or not row.selected_spec_relevant)
    elseif relevance == "not_ranked" then
        return not row.class_relevant
    end
    return true
end

function FILTER_FACETS.wishlistDefaultSort(a, b)
    if a.wishlist_owned_sort ~= b.wishlist_owned_sort then
        return a.wishlist_owned_sort < b.wishlist_owned_sort
    end
    if a.wishlist_relevance_sort ~= b.wishlist_relevance_sort then
        return a.wishlist_relevance_sort < b.wishlist_relevance_sort
    end
    if a.wishlist_rank_sort ~= b.wishlist_rank_sort then
        return a.wishlist_rank_sort < b.wishlist_rank_sort
    end
    if a.wishlist_phase_sort ~= b.wishlist_phase_sort then
        return a.wishlist_phase_sort < b.wishlist_phase_sort
    end
    if lower(a.name) ~= lower(b.name) then
        return lower(a.name) < lower(b.name)
    end
    return (tonumber(a.item_id) or 0) < (tonumber(b.item_id) or 0)
end

function FILTER_FACETS.wishlistSortValue(row, sortKey)
    if sortKey == "item" or sortKey == "name" then
        return lower(row.name)
    elseif sortKey == "slot" or sortKey == "slots" then
        return lower(row.slot_label)
    elseif sortKey == "source" then
        return lower(row.acquisition_display and row.acquisition_display.source_label)
    elseif sortKey == "location" then
        return lower(row.acquisition_display and row.acquisition_display.location_label)
    elseif sortKey == "owned" then
        return row.wishlist_owned_sort
    end
    return nil
end

function FILTER_FACETS.sortWishlistRows(rows, filters)
    local sortKey = filters and (filters.wishlistSort or filters.sortKey)
    local descending = filters and (filters.sortDirection == "desc" or filters.sortDescending == true)
    table.sort(rows, function(a, b)
        local aValue = FILTER_FACETS.wishlistSortValue(a, sortKey)
        local bValue = FILTER_FACETS.wishlistSortValue(b, sortKey)
        if aValue ~= nil and bValue ~= nil and aValue ~= bValue then
            if descending then
                return aValue > bValue
            end
            return aValue < bValue
        end
        return FILTER_FACETS.wishlistDefaultSort(a, b)
    end)
end

function BigBiSList:GetWishlistRows(wishlistItems, className, selectedSpec, selectedPhaseKey, filters)
    filters = filters or {}
    local selectedPhase = phaseIndex(selectedPhaseKey) < 999 and selectedPhaseKey or (filters.endgamePhase or "PR")
    local index = self:GetDataIndex(selectedPhase)
    local context = self:GetProgressionContext(selectedPhase)
    local livePhase = self:GetCurrentPhaseKey()
    local rows = {}

    for _, itemId in ipairs(FILTER_FACETS.normalizeWishlistItemIds(wishlistItems)) do
        local item = getIndexedItem(index, itemId)
        local meta = getItemMetaFromIndex(index, itemId, item) or {}
        local summary = self:GetWishlistExpansionSummary(itemId, className, selectedSpec, selectedPhase)
        local bestUse = summary and summary.best_use or nil
        local ownedState = FILTER_FACETS.tableValueById(filters.ownedItems, itemId)
        local row = {
            item_id = itemId,
            item = item,
            name = meta.name or getItemName(itemId, item),
            class = className,
            spec = selectedSpec,
            phase = selectedPhase,
            phaseIndex = context.content_phase_index,
            content_phase = context.content_phase,
            selected_phase = selectedPhase,
            live_phase = livePhase,
            slots = summary and summary.slots or {},
            slot = summary and summary.slots[1] or nil,
            slot_label = summary and summary.slot_label or "—",
            spec_rankings = summary and summary.spec_rankings or {},
            relevant_spec_rankings = summary and summary.relevant_spec_rankings or {},
            selected_spec_ranking = summary and summary.selected_spec_ranking or nil,
            selected_spec_relevant = summary and summary.selected_spec_relevant or false,
            class_relevant = summary and summary.class_relevant or false,
            ranking_search_text = summary and summary.ranking_search_text or "",
            not_ranked_label = summary and summary.not_ranked_label or nil,
            expansion_summary = summary,
            bestUse = bestUse,
            rank = bestUse and bestUse.rank or nil,
            rank_label = bestUse and bestUse.rank_label or nil,
            rank_group = bestUse and bestUse.rank_group or nil,
            display_rank_label = bestUse and FILTER_FACETS.wishlistRankShortLabel(bestUse) or "—",
            display_rank_kind = bestUse and bestUse.display_rank_kind or "missing",
            recommendation_summary = summary and (summary.not_ranked_label or (bestUse and bestUse.recommendation_summary)) or nil,
            source_summary = meta.source_summary or "",
            source_type = meta.source_type or "unknown",
            source_type_label = meta.source_type_label or SOURCE_TYPE_LABELS.unknown,
            source_filter_key = meta.source_filter_key or "unknown",
            source_filter_label = meta.source_filter_label or SOURCE_TYPE_LABELS.unknown,
            source_filter_keys = meta.source_filter_keys or {},
            acquisition_phase = meta.acquisition_phase or "PR",
            acquisitionPhaseIndex = meta.acquisitionPhaseIndex or phaseIndex("PR"),
            zone = meta.zone,
            zones = meta.zones or {},
            side = meta.side,
            sides = meta.sides or {},
            binding = meta.binding or "unknown",
            boe = meta.boe,
            quality = meta.quality,
            requirements = bestUse and bestUse.requirements or meta.requirements,
            reputations = bestUse and bestUse.reputations or meta.reputations or {},
            owned = ownedState ~= nil and ownedState ~= false,
            ownership_state = ownedState,
            wishlist_owned_sort = (ownedState ~= nil and ownedState ~= false) and 1 or 0,
            wishlist_relevance_sort = summary and summary.relevance_sort or 2,
            wishlist_rank_sort = summary and summary.best_rank_sort or 999999,
            wishlist_phase_sort = summary and summary.earliest_phase_index or 999,
            _access_context = {
                item = item,
                options = { entityType = "item" },
            },
        }
        row.default_sort = {
            owned = row.wishlist_owned_sort,
            relevance = row.wishlist_relevance_sort,
            rank = row.wishlist_rank_sort,
            phase = row.wishlist_phase_sort,
            name = lower(row.name),
            item_id = itemId,
        }

        local filterPhaseIndex = hasActiveSourceContextFilter(filters) and context.content_phase_index or nil
        if includeByFilter(row, filters, filterPhaseIndex) and FILTER_FACETS.wishlistRowMatchesRelevance(row, filters) then
            row.acquisition_display = self:GetRowAcquisitionDisplay(row, filters, context.content_phase, true)
            row.matched_access_option = row.acquisition_display.option
            row.source_available = row.acquisition_display.available
            row.source_future = row.acquisition_display.future
            row.source_live_available = accessOptionIsPhaseAvailable(row.matched_access_option, phaseIndex(livePhase))
            local nextLivePhase = row.matched_access_option
                and FILTER_FACETS.nextAvailableOptionPhase(row.matched_access_option, phaseIndex(livePhase)) or nil
            row.source_live_future = nextLivePhase ~= nil and nextLivePhase > phaseIndex(livePhase)
            table.insert(rows, row)
        end
    end

    FILTER_FACETS.sortWishlistRows(rows, filters)
    return rows
end

function BigBiSList:GetItemLevelingUses(itemId)
    itemId = tonumber(itemId)
    if not itemId then
        return {}
    end

    local index = self:GetDataIndex()
    if index.levelingGearCache[itemId] then
        return index.levelingGearCache[itemId]
    end

    local rows = {}
    for _, levelingRef in ipairs(index.levelingGearRefsByItemId[itemId] or {}) do
        local row = buildLevelingGearRow(index, levelingRef)
        if row then
            table.insert(rows, row)
        end
    end
    for _, recommendationRef in ipairs(index.levelingRecommendationRefsByItemId[itemId] or {}) do
        local row = buildLevelingRecommendationRow(index, recommendationRef)
        if row then
            table.insert(rows, row)
        end
    end
    table.sort(rows, LEVELING_HELPERS.sortByNextLevel)
    index.levelingGearCache[itemId] = rows
    return rows
end

function BigBiSList:GetItemLevelingRecommendationUses(itemId, race)
    itemId = tonumber(itemId)
    if not itemId then
        return {}
    end

    local cacheKey = tostring(itemId) .. ":" .. tostring(race or "")
    local index = self:GetDataIndex()
    if index.levelingRecommendationCache[cacheKey] then
        return index.levelingRecommendationCache[cacheKey]
    end

    local rows = {}
    for _, recommendationRef in ipairs(index.levelingRecommendationRefsByItemId[itemId] or {}) do
        local row = buildLevelingRecommendationRow(index, recommendationRef)
        if row and raceMatches(row.race, race) then
            table.insert(rows, row)
        end
    end
    table.sort(rows, LEVELING_HELPERS.sortByNextLevel)
    index.levelingRecommendationCache[cacheKey] = rows
    return rows
end

function BigBiSList:GetItemBestUseForSpec(itemId, className, specName, preferredPhaseKey, allowedSlots)
    local uses = self:GetItemUses(itemId, preferredPhaseKey)
    local bestUse

    for _, use in ipairs(uses) do
        if use.class == className
            and use.spec == specName
            and FILTER_FACETS.useMatchesProgressionContext(use, preferredPhaseKey)
            and (not allowedSlots or slotListContains(allowedSlots, use.slot))
            and isBetterGearUse(use, bestUse, preferredPhaseKey) then
            bestUse = use
        end
    end

    return bestUse
end

function BigBiSList:GetItemBestLevelingUseForSpec(itemId, className, specName, level, allowedSlots, race)
    local selectedLevel = clampLevelingLevel(level)
    race = race or self:GetPlayerRaceName()
    local bestUse

    for _, row in ipairs(self:GetItemLevelingUses(itemId)) do
        if row.class == className
            and row.spec == specName
            and raceMatches(row.race, race)
            and LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
            and (not allowedSlots or slotListContains(allowedSlots, row.slot)) then
            if LEVELING_HELPERS.rowBeats(row, bestUse, race, selectedLevel) then
                bestUse = row
            end
        end
    end

    return bestUse
end

function BigBiSList:GetItemNextLevelingUseForSpec(itemId, className, specName, level, allowedSlots, race)
    local selectedLevel = clampLevelingLevel(level)
    race = race or self:GetPlayerRaceName()
    local matches = {}

    for _, row in ipairs(self:GetItemLevelingUses(itemId)) do
        if row.class == className
            and row.spec == specName
            and raceMatches(row.race, race)
            and (tonumber(row.level_min) or 1) > selectedLevel
            and (not allowedSlots or slotListContains(allowedSlots, row.slot)) then
            table.insert(matches, row)
        end
    end

    table.sort(matches, LEVELING_HELPERS.sortByNextLevel)
    return matches[1]
end

local function upgradeSlotCapacity(slotName)
    if slotName == "Ring" or slotName == "Trinket" then
        return 2
    end
    return 1
end

local function addOwnedUseContext(contextsBySlot, use, state)
    if not use or not use.slot then
        return
    end

    contextsBySlot[use.slot] = contextsBySlot[use.slot] or {}
    table.insert(contextsBySlot[use.slot], {
        use = use,
        item_id = use.item_id,
        name = use.name,
        state = state,
        slot = use.slot,
        rank_label = use.rank_label,
        rank_group = use.rank_group,
    })
end

local function addOwnedItemToUpgradeBaseline(addon, contextsBySlot, itemId, state, className, specName, preferredPhaseKey)
    itemId = tonumber(itemId)
    if not itemId or type(state) ~= "string" then
        return
    end

    local bestBySlot = {}
    for _, use in ipairs(addon:GetItemUses(itemId, preferredPhaseKey)) do
        if use.class == className
            and use.spec == specName
            and FILTER_FACETS.useMatchesProgressionContext(use, preferredPhaseKey)
            and isBetterGearUse(use, bestBySlot[use.slot], preferredPhaseKey) then
            bestBySlot[use.slot] = use
        end
    end

    for _, use in pairs(bestBySlot) do
        addOwnedUseContext(contextsBySlot, use, state)
    end
end

local function sortUpgradeBaseline(contextsBySlot, preferredPhaseKey)
    for _, contexts in pairs(contextsBySlot or {}) do
        table.sort(contexts, function(a, b)
            return isBetterGearUse(a.use, b.use, preferredPhaseKey)
        end)
    end
end

local function buildUpgradeBaselines(addon, className, specName, preferredPhaseKey, ownedItems)
    local baselines = {
        ownedBySlot = {},
        equippedBySlot = {},
    }

    for itemId, state in pairs(ownedItems or {}) do
        if type(state) == "string" then
            addOwnedItemToUpgradeBaseline(addon, baselines.ownedBySlot, itemId, state, className, specName, preferredPhaseKey)
            if state == "equipped" then
                addOwnedItemToUpgradeBaseline(addon, baselines.equippedBySlot, itemId, state, className, specName, preferredPhaseKey)
            end
        end
    end

    sortUpgradeBaseline(baselines.ownedBySlot, preferredPhaseKey)
    sortUpgradeBaseline(baselines.equippedBySlot, preferredPhaseKey)
    return baselines
end

local function bestPlannerUseForUpgrade(group, preferredPhaseKey)
    local bestUse
    for _, use in ipairs(group and group.uses or {}) do
        if isBetterGearUse(use, bestUse, preferredPhaseKey) then
            bestUse = use
        end
    end
    return bestUse or (group and group.bestUse)
end

local function upgradeComparisonContext(contextsBySlot, use)
    if not use then
        return nil
    end

    local contexts = contextsBySlot and contextsBySlot[use.slot] or nil
    local capacity = upgradeSlotCapacity(use.slot)
    if not contexts or #contexts < capacity then
        return nil
    end
    return contexts[capacity]
end

local function applyPlannerUpgradeMetadata(group, state, candidateUse, comparedContext)
    group.upgrade_state = state
    group.upgrade_candidate_rank_label = candidateUse and candidateUse.rank_label or nil
    group.upgrade_candidate_display_rank_label = candidateUse and rankShortLabel(candidateUse) or nil
    group.upgrade_candidate_phase = candidateUse and candidateUse.phase or nil
    group.upgrade_compared_slot = candidateUse and candidateUse.slot or group.slot
    group.upgrade_compared_empty = comparedContext == nil
    group.upgrade_compared_item_id = comparedContext and comparedContext.item_id or nil
    group.upgrade_compared_name = comparedContext and comparedContext.name or nil
    group.upgrade_compared_state = comparedContext and comparedContext.state or nil
    group.upgrade_compared_rank_label = comparedContext and comparedContext.rank_label or nil
    group.upgrade_compared_rank_group = comparedContext and comparedContext.rank_group or nil
end

local function annotatePlannerUpgradeGroup(group, filters, baselines, selectedPhaseKey)
    local candidateUse = bestPlannerUseForUpgrade(group, selectedPhaseKey)
    local ownedState = filters and filters.ownedItems and filters.ownedItems[group.item_id]
    local comparedContext

    if not candidateUse or ownedState == "equipped" then
        applyPlannerUpgradeMetadata(group, "not_upgrade", candidateUse, nil)
        return
    elseif ownedState == "bag" or ownedState == "bank" then
        comparedContext = upgradeComparisonContext(baselines.equippedBySlot, candidateUse)
        if isStrictUpgradeUse(candidateUse, comparedContext and comparedContext.use, selectedPhaseKey) then
            applyPlannerUpgradeMetadata(group, "owned_upgrade", candidateUse, comparedContext)
            return
        end
        applyPlannerUpgradeMetadata(group, "not_upgrade", candidateUse, comparedContext)
        return
    elseif ownedState then
        applyPlannerUpgradeMetadata(group, "not_upgrade", candidateUse, nil)
        return
    end

    comparedContext = upgradeComparisonContext(baselines.ownedBySlot, candidateUse)
    if isStrictUpgradeUse(candidateUse, comparedContext and comparedContext.use, selectedPhaseKey) then
        applyPlannerUpgradeMetadata(group, "missing_upgrade", candidateUse, comparedContext)
        return
    end

    applyPlannerUpgradeMetadata(group, "not_upgrade", candidateUse, comparedContext)
end

local function plannerGroupMatchesUpgradeMode(group, filters)
    if not filters or filters.upgradeMode ~= "actual" then
        return true
    elseif group.upgrade_state == "missing_upgrade" then
        return true
    elseif group.upgrade_state == "owned_upgrade" then
        return true
    end
    return false
end

-- Alternative routes do not multiply targets or activity counts.
function BigBiSList:GetActivityGroup(row)
    local display = row and row.acquisition_display or {}
    local option = display.option or (row and row.matched_access_option) or {}
    local kind = option.source_filter_key or option.source_type or (row and row.source_type) or "unknown"
    local zone = option.zone or (option.zones and option.zones[1])
    if type(zone) == "table" then zone = zone.name or zone.zone end
    if kind == "raid" or kind == "raid_drop" or kind == "dungeon" or kind == "dungeon_drop"
        or kind == "heroic_dungeon_drop" or kind == "drop" or kind == "quest" then
        return zone or display.source_label or "Other activities"
    end
    if option.is_trade_option then return "Trade / Auction House" end
    if option.reputations and #option.reputations > 0 then return "Reputation · " .. option.reputations[1] end
    for _, requirement in ipairs(option.requirements or {}) do
        if requirement.type == "profession" and requirement.profession then return "Crafting · " .. requirement.profession end
    end
    if option.vendor_label then return "Vendor · " .. option.vendor_label end
    return display.source_label or option.source_filter_label or "Other activities"
end

function BigBiSList:GetEquippedGearRows(className, specName, phaseKey, ownedItems, level)
    local rows = {}
    local equippedSlots = ownedItems and ownedItems.equippedSlots or {}
    local selectedLevel = clampLevelingLevel(level)
    local levelingMode = phaseKey == LEVELING_PHASE_KEY

    for _, slot in ipairs(EQUIPMENT_SLOTS) do
        local equipped = equippedSlots[slot.key]
        local itemId = equipped and equipped.item_id
        local item = itemId and self:GetItemData(itemId) or nil
        local bestUse = itemId and (levelingMode
            and self:GetItemBestLevelingUseForSpec(itemId, className, specName, selectedLevel, slot.slots)
            or self:GetItemBestUseForSpec(itemId, className, specName, phaseKey, slot.slots)) or nil
        local overlay = "Empty"
        local overlayKind = "empty"
        local disabledReason

        if itemId and bestUse and levelingMode then
            overlay = (bestUse.category_label and bestUse.category_label ~= "Recommended") and bestUse.category_label or "Leveling pick"
            overlayKind = "leveling"
        elseif itemId and bestUse then
            overlay = bestUse.rank_group == "bis" and "Best in slot" or "Alternative"
            overlayKind = bestUse.rank_group or "option"
        elseif itemId then
            overlay = "Not ranked"
            overlayKind = "missing"
        elseif slot.key == "OffHand" and ownedItems and ownedItems.equippedTwoHand then
            overlay = "2H equipped"
            overlayKind = "disabled"
            disabledReason = "Two-handed weapon equipped"
        end

        local displayRankLabel, displayRankKind = displayRankInfo(bestUse)
        local recommendation = "Empty slot"
        if itemId and bestUse and levelingMode then
            recommendation = bestUse.level_label or bestUse.level_value_text or "Leveling recommendation"
        elseif itemId and bestUse then
            recommendation = bestUse.rank_group == "bis" and "Best in slot" or "Alternative"
        elseif itemId then
            recommendation = "Not ranked"
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
            leveling = bestUse and bestUse.leveling or nil,
            level_min = bestUse and bestUse.level_min or nil,
            level_max = bestUse and bestUse.level_max or nil,
            level_label = bestUse and bestUse.level_label or nil,
            level_value_text = bestUse and bestUse.level_value_text or nil,
            category_label = bestUse and bestUse.category_label or nil,
            leveling_category_key = bestUse and bestUse.leveling_category_key or nil,
            section = bestUse and bestUse.section or nil,
            source_note = bestUse and bestUse.source_note or nil,
            phase = bestUse and bestUse.phase or nil,
            rank_label = bestUse and bestUse.rank_label or nil,
            rank_group = bestUse and bestUse.rank_group or nil,
            overlay = overlay,
            overlayKind = overlayKind,
            disabledReason = disabledReason,
            column = slot.column,
            dataSlots = slot.slots,
            requirements = mergedRequirements(bestUse and bestUse.requirements, item and item.requirements),
            _access_context = (levelingMode and bestUse and bestUse._access_context) or (bestUse and nil or {
                item = item,
                options = { entityType = "item" },
            }),
            display_rank_label = itemId and displayRankLabel or "Empty",
            display_rank_kind = itemId and displayRankKind or "missing",
            recommendation_summary = recommendation,
        })
    end

    return rows
end

function BigBiSList:GetPhaseRows(className, specName, phaseKey, filters)
    filters = FILTER_FACETS.progressionFilters(filters, phaseKey)
    local index = self:GetDataIndex(phaseKey)
    local useRefs = index.useRefsByClassSpecPhase[className]
        and index.useRefsByClassSpecPhase[className][specName]
        and index.useRefsByClassSpecPhase[className][specName][phaseKey]
    local grouped = {}
    local seenBySlot = {}
    local selectedIndex = self:GetAvailabilityPhaseIndex(phaseKey)

    if not useRefs then
        return {}
    end

    for _, useRef in ipairs(useRefs) do
        local use = buildUse(index, useRef)
        local slotName = use.slot
        grouped[slotName] = grouped[slotName] or { slot = slotName, items = {} }
        seenBySlot[slotName] = seenBySlot[slotName] or {}

        local key = tostring(use.item_id) .. ":" .. tostring(use.rank_group) .. ":" .. tostring(use.context)
        if use.acquisitionPhaseIndex <= selectedIndex and not seenBySlot[slotName][key] and includeByFilter(use, filters, selectedIndex) then
            use.acquisition_display = self:GetRowAcquisitionDisplay(use, filters, phaseKey)
            use.matched_access_option = use.acquisition_display.option
            seenBySlot[slotName][key] = true
            table.insert(grouped[slotName].items, use)
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

function BigBiSList:GetLevelingRows(className, specName, level, filters)
    local index = self:GetDataIndex()
    local selectedLevel = clampLevelingLevel(tonumber(level) or (filters and tonumber(filters.level)))
    local selectedRace = (filters and filters.race) or self:GetPlayerRaceName()
    local levelingRefs = index.levelingGearRefsByClassSpec[className]
        and index.levelingGearRefsByClassSpec[className][specName]
        or {}
    local recommendationRefs = index.levelingRecommendationRefsByClassSpec[className]
        and index.levelingRecommendationRefsByClassSpec[className][specName]
        or {}
    local grouped = {}
    local seenBySlot = {}
    local raceOverrideGroups = {}

    if selectedRace and selectedRace ~= "" then
        for _, recommendationRef in ipairs(recommendationRefs) do
            local row = buildLevelingRecommendationRow(index, recommendationRef)
            if row
                and row.race == selectedRace
                and LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
                and includeByFilter(row, filters, phaseIndex(LEVELING_PHASE_KEY)) then
                local groupKey = levelingRecommendationGroupKey(row)
                if groupKey then
                    raceOverrideGroups[groupKey] = true
                end
            end
        end
    end

    for _, recommendationRef in ipairs(recommendationRefs) do
        local row = buildLevelingRecommendationRow(index, recommendationRef)
        local includeRecommendation = row
            and raceMatches(row.race, selectedRace)
            and LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
            and includeByFilter(row, filters, phaseIndex(LEVELING_PHASE_KEY))

        if includeRecommendation then
            local groupKey = levelingRecommendationGroupKey(row)
            if row.race == "*" and groupKey and raceOverrideGroups[groupKey] then
                includeRecommendation = false
            end
        end

        if includeRecommendation then
            row.acquisition_display = self:GetRowAcquisitionDisplay(row, filters, LEVELING_PHASE_KEY)
            row.matched_access_option = row.acquisition_display.option
            LEVELING_HELPERS.addDisplayRow(grouped, seenBySlot, row, selectedRace, selectedLevel)
        end
    end

    for _, levelingRef in ipairs(levelingRefs) do
        local row = buildLevelingGearRow(index, levelingRef)
        if row and LEVELING_HELPERS.isAvailableAt(row, selectedLevel) and includeByFilter(row, filters, phaseIndex(LEVELING_PHASE_KEY)) then
            row.acquisition_display = self:GetRowAcquisitionDisplay(row, filters, LEVELING_PHASE_KEY)
            row.matched_access_option = row.acquisition_display.option
            LEVELING_HELPERS.addDisplayRow(grouped, seenBySlot, row, selectedRace, selectedLevel)
        end
    end

    local rows = {}
    for _, slotName in ipairs(SLOT_ORDER) do
        if grouped[slotName] and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, function(a, b)
                return LEVELING_HELPERS.sortForLevel(a, b, selectedLevel)
            end)
            table.insert(rows, grouped[slotName])
        end
    end

    for _, slotName in ipairs(sortedKeys(grouped)) do
        if slotIndex(slotName) == 999 and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, function(a, b)
                return LEVELING_HELPERS.sortForLevel(a, b, selectedLevel)
            end)
            table.insert(rows, grouped[slotName])
        end
    end

    return rows
end

function BigBiSList:GetPlannerRows(className, specName, selectedPhaseKey, filters)
    filters = FILTER_FACETS.progressionFilters(filters, selectedPhaseKey)
    local index = self:GetDataIndex(selectedPhaseKey)
    local groups = {}
    local selectedIndex = self:GetAvailabilityPhaseIndex(selectedPhaseKey)
    local upgradeBaselines = filters and filters.upgradeMode == "actual"
        and buildUpgradeBaselines(self, className, specName, selectedPhaseKey, filters.ownedItems)
        or nil
    local useRefs = index.useRefsByClassSpec[className]
        and index.useRefsByClassSpec[className][specName]
        or {}

    for _, useRef in ipairs(useRefs) do
        local use = buildUse(index, useRef)
        if FILTER_FACETS.useMatchesProgressionContext(use, selectedPhaseKey) then
            local itemId = use.item_id
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
                    source_filter_key = use.source_filter_key,
                    source_filter_label = use.source_filter_label,
                    source_filter_keys = use.source_filter_keys,
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

        if upgradeBaselines then
            annotatePlannerUpgradeGroup(group, filters, upgradeBaselines, selectedPhaseKey)
        end

        if group.priority > 0 and group.acquisitionPhaseIndex <= selectedIndex and includeByFilter(group, filters, selectedIndex) and plannerGroupMatchesUpgradeMode(group, filters) then
            if filters and filters.longevity == "current" and not group.hasCurrent then
                -- excluded below
            elseif filters and filters.longevity == "future" and phaseIndex(group.lastUsefulPhase) <= selectedIndex then
                -- excluded below
            elseif filters and filters.longevity == "long" and phaseIndex(group.lastUsefulPhase) < selectedIndex + 2 then
                -- excluded below
            else
                group.acquisition_display = self:GetRowAcquisitionDisplay(group, filters, selectedPhaseKey)
                group.matched_access_option = group.acquisition_display.option
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
    scopedFilters.reputations = nil
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

function FILTER_FACETS.cloneFiltersForCostOptions(filters)
    local scopedFilters = {}
    for key, value in pairs(filters or {}) do
        scopedFilters[key] = value
    end
    scopedFilters.cost = "all"
    scopedFilters.costs = nil
    return scopedFilters
end

function FILTER_FACETS.cloneFiltersForVendorOptions(filters)
    local scopedFilters = {}
    for key, value in pairs(filters or {}) do
        scopedFilters[key] = value
    end
    scopedFilters.vendor = "all"
    scopedFilters.vendors = nil
    return scopedFilters
end

function FILTER_FACETS.addSourceTypeFromOption(sourceTypes, seen, option, selectedPhaseIndex)
    if FILTER_FACETS.optionIsReportedOnly(option)
        or not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then
        return
    end

    addUnique(sourceTypes, seen, option.source_filter_key or option.source_type)
end

function FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, callback)
    if type(row) ~= "table" then
        return false, false
    end

    local options = buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}
    local matched = false
    for _, option in ipairs(options) do
        if optionMatchesSourceContext(option, filters, selectedPhaseIndex) then
            callback(option)
            matched = true
        end
    end
    return matched, #options > 0
end

function FILTER_FACETS.rowHasCompleteOptionForSourceType(row, sourceType, selectedPhaseIndex)
    for _, option in ipairs(buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}) do
        if not FILTER_FACETS.optionIsReportedOnly(option)
            and accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
            and (option.source_filter_key == sourceType or option.source_type == sourceType) then
            return true
        end
    end
    return false
end

local function addSourceTypeFromRow(sourceTypes, seen, row, filters, selectedPhaseIndex)
    if type(row) ~= "table" then
        return
    end

    if FILTER_FACETS.hasActiveOptionContextFilter(filters) then
        local matched, hasOptions = FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, function(option)
            FILTER_FACETS.addSourceTypeFromOption(sourceTypes, seen, option, selectedPhaseIndex)
        end)
        if matched or hasOptions or hasActiveSourceContextFilter(filters) then
            return
        end
    end

    local phaseMeta = row.item and getItemPhaseMeta(BigBiSList:GetDataIndex(), row.item_id, row.item, selectedPhaseIndex) or nil
    local sourceFilterKeys = phaseMeta and phaseMeta.source_filter_keys or row.source_filter_keys
    for _, sourceType in ipairs(sourceFilterKeys or {}) do
        local purchaseType = FILTER_FACETS.VENDOR_PURCHASE_SOURCE_TYPES[sourceType] == true
        if not purchaseType or FILTER_FACETS.rowHasCompleteOptionForSourceType(row, sourceType, selectedPhaseIndex) then
            addUnique(sourceTypes, seen, sourceType)
        end
    end
    if not sourceFilterKeys or #sourceFilterKeys == 0 then
        local sourceType = row.source_filter_key or row.source_type
        local purchaseType = FILTER_FACETS.VENDOR_PURCHASE_SOURCE_TYPES[sourceType] == true
        if not purchaseType or FILTER_FACETS.rowHasCompleteOptionForSourceType(row, sourceType, selectedPhaseIndex) then
            addUnique(sourceTypes, seen, sourceType)
        end
    end
end

local function addZonesFromOption(zones, seen, option, selectedPhaseIndex)
    if not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then
        return
    end

    addSourceZone(zones, seen, option.zone, selectedPhaseIndex)
    for _, zone in ipairs(option.zones or {}) do
        addSourceZone(zones, seen, zone, selectedPhaseIndex)
    end
end

local function addZonesFromRow(zones, seen, row, filters, selectedPhaseIndex)
    if type(row) ~= "table" then
        return
    end

    if FILTER_FACETS.hasActiveOptionContextFilter(filters) then
        local matched, hasOptions = FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, function(option)
            addZonesFromOption(zones, seen, option, selectedPhaseIndex)
        end)
        if matched or hasOptions or hasActiveSourceContextFilter(filters) then
            return
        end
    end

    if row.item then
        local phaseMeta = getItemPhaseMeta(BigBiSList:GetDataIndex(), row.item_id, row.item, selectedPhaseIndex)
        for _, zone in ipairs((phaseMeta and phaseMeta.zones) or getSourceZones(row.item, selectedPhaseIndex)) do
            addSourceZone(zones, seen, zone, selectedPhaseIndex)
        end
    else
        addSourceZone(zones, seen, row.zone, selectedPhaseIndex)
        for _, zone in ipairs(row.zones or {}) do
            addSourceZone(zones, seen, zone, selectedPhaseIndex)
        end
    end
end

function FILTER_FACETS.addCostFromOption(costs, labels, seen, option, selectedPhaseIndex)
    if FILTER_FACETS.optionIsReportedOnly(option)
        or not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then
        return
    end

    for _, costKey in ipairs(option.cost_keys or {}) do
        addUnique(costs, seen, costKey)
        labels[costKey] = FILTER_FACETS.COST_FILTER_LABELS[costKey] or costKey
    end
end

function FILTER_FACETS.addCostsFromRow(costs, labels, seen, row, filters, selectedPhaseIndex)
    if type(row) ~= "table" then
        return
    end

    FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, function(option)
        FILTER_FACETS.addCostFromOption(costs, labels, seen, option, selectedPhaseIndex)
    end)
end

function FILTER_FACETS.addVendorFromOption(vendors, labels, seen, option, selectedPhaseIndex)
    if FILTER_FACETS.optionIsReportedOnly(option)
        or not accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
        or not option.vendor_key then
        return
    end

    addUnique(vendors, seen, option.vendor_key)
    labels[option.vendor_key] = option.vendor_label or option.vendor_key
end

function FILTER_FACETS.addVendorsFromRow(vendors, labels, seen, row, filters, selectedPhaseIndex)
    if type(row) ~= "table" then
        return
    end

    FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, function(option)
        FILTER_FACETS.addVendorFromOption(vendors, labels, seen, option, selectedPhaseIndex)
    end)
end

function FILTER_FACETS.addReputationsFromOption(reputations, seen, option, selectedPhaseIndex)
    if not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then
        return
    end

    addReputationsFromRequirements(reputations, seen, option.requirements)
    for _, reputation in ipairs(option.reputations or {}) do
        addUnique(reputations, seen, reputation)
    end
end

local function addReputationsFromRow(reputations, seen, row, filters, selectedPhaseIndex)
    if type(row) ~= "table" then
        return
    end

    if FILTER_FACETS.hasActiveOptionContextFilter(filters) then
        local matched, hasOptions = FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, function(option)
            FILTER_FACETS.addReputationsFromOption(reputations, seen, option, selectedPhaseIndex)
        end)
        if matched or hasOptions or hasActiveSourceContextFilter(filters) then
            return
        end
    end

    if row.requirements then
        addReputationsFromRequirements(reputations, seen, row.requirements)
    end
    for _, reputation in ipairs(row.reputations or {}) do
        addUnique(reputations, seen, reputation)
    end
end

local function cloneFiltersForAvailabilityRows(filters)
    local scopedFilters = {}
    for key, value in pairs(filters or {}) do
        scopedFilters[key] = value
    end
    scopedFilters.sourceType = "all"
    scopedFilters.sourceTypes = nil
    scopedFilters.zone = "all"
    scopedFilters.zones = nil
    scopedFilters.cost = "all"
    scopedFilters.costs = nil
    scopedFilters.vendor = "all"
    scopedFilters.vendors = nil
    scopedFilters.reputation = "all"
    scopedFilters.reputations = nil
    return scopedFilters
end

local function collectAvailabilityRows(addon, className, specName, phaseKey, tabName, filters)
    local rows = {}
    if tabName == "Wishlist" then
        return addon:GetWishlistRows(
            filters and (filters.wishlistItems or filters.wishlist) or {},
            className,
            specName,
            phaseKey,
            filters
        )
    elseif tabName == "Enhance" or tabName == "Enhancements" then
        for _, section in ipairs(addon:GetEnhancementRows(className, specName, phaseKey, filters)) do
            for _, row in ipairs(section.rows or {}) do
                table.insert(rows, row)
            end
        end
        return rows
    end

    if phaseKey == LEVELING_PHASE_KEY then
        for _, group in ipairs(addon:GetLevelingRows(className, specName, filters and filters.level, filters)) do
            for _, row in ipairs(group.items or {}) do
                table.insert(rows, row)
            end
        end
        return rows
    end
    if tabName == "Planner" or tabName == "Upgrades" then
        return addon:GetPlannerRows(className, specName, phaseKey, filters)
    end

    for _, group in ipairs(addon:GetPhaseRows(className, specName, phaseKey, filters)) do
        for _, row in ipairs(group.items or {}) do
            table.insert(rows, row)
        end
    end
    return rows
end

function BigBiSList:GetFilterAvailabilitySnapshot(className, specName, phaseKey, tabName, filters)
    local availabilityPhaseKey = phaseKey
    if tabName == "Wishlist" and phaseKey == LEVELING_PHASE_KEY then
        availabilityPhaseKey = filters and (filters.endgamePhase or filters.selectedEndgamePhase) or "PR"
    end
    local selectedIndex = self:GetAvailabilityPhaseIndex(availabilityPhaseKey)
    if tabName ~= "Wishlist" then filters = FILTER_FACETS.progressionFilters(filters, availabilityPhaseKey) end
    local sourceTypes = {}
    local sourceSeen = {}
    local zones = {}
    local zoneSeen = {}
    local costs = {}
    local costSeen = {}
    local costLabels = {}
    local vendors = {}
    local vendorSeen = {}
    local vendorLabels = {}
    local reputations = {}
    local reputationSeen = {}
    local sourceScopedFilters = cloneFiltersForSourceTypeOptions(filters)
    local zoneScopedFilters = cloneFiltersForZoneOptions(filters)
    local costScopedFilters = FILTER_FACETS.cloneFiltersForCostOptions(filters)
    local vendorScopedFilters = FILTER_FACETS.cloneFiltersForVendorOptions(filters)
    local reputationScopedFilters = cloneFiltersForReputationOptions(filters)
    local rows = collectAvailabilityRows(self, className, specName, phaseKey, tabName, cloneFiltersForAvailabilityRows(filters))

    for _, row in ipairs(rows) do
        if includeByFilter(row, sourceScopedFilters, selectedIndex) then
            addSourceTypeFromRow(sourceTypes, sourceSeen, row, sourceScopedFilters, selectedIndex)
        end
        if includeByFilter(row, zoneScopedFilters, selectedIndex) then
            addZonesFromRow(zones, zoneSeen, row, zoneScopedFilters, selectedIndex)
        end
        if includeByFilter(row, costScopedFilters, selectedIndex) then
            FILTER_FACETS.addCostsFromRow(costs, costLabels, costSeen, row, costScopedFilters, selectedIndex)
        end
        if includeByFilter(row, vendorScopedFilters, selectedIndex) then
            FILTER_FACETS.addVendorsFromRow(vendors, vendorLabels, vendorSeen, row, vendorScopedFilters, selectedIndex)
        end
        if includeByFilter(row, reputationScopedFilters, selectedIndex) then
            addReputationsFromRow(reputations, reputationSeen, row, reputationScopedFilters, selectedIndex)
        end
    end

    table.sort(sourceTypes, sortSourceFilterKeys)
    table.sort(zones)
    table.sort(costs, FILTER_FACETS.sortCostFilterKeys)
    table.sort(vendors, function(a, b)
        local aLabel = vendorLabels[a] or a
        local bLabel = vendorLabels[b] or b
        if aLabel ~= bLabel then
            return aLabel < bLabel
        end
        return tostring(a) < tostring(b)
    end)
    table.sort(reputations)
    return {
        sourceTypes = sourceTypes,
        zones = zones,
        costs = costs,
        costLabels = costLabels,
        vendors = vendors,
        vendorLabels = vendorLabels,
        reputations = reputations,
    }
end

function BigBiSList:GetAvailableFilterSourceTypes(className, specName, phaseKey, tabName, filters)
    return self:GetFilterAvailabilitySnapshot(className, specName, phaseKey, tabName, filters).sourceTypes
end

function BigBiSList:GetAvailableFilterZones(className, specName, phaseKey, tabName, filters)
    return self:GetFilterAvailabilitySnapshot(className, specName, phaseKey, tabName, filters).zones
end

function BigBiSList:GetAvailableFilterCosts(className, specName, phaseKey, tabName, filters)
    return self:GetFilterAvailabilitySnapshot(className, specName, phaseKey, tabName, filters).costs
end

function BigBiSList:GetAvailableFilterVendors(className, specName, phaseKey, tabName, filters)
    return self:GetFilterAvailabilitySnapshot(className, specName, phaseKey, tabName, filters).vendors
end

function BigBiSList:GetAvailableFilterReputations(className, specName, phaseKey, tabName, filters)
    return self:GetFilterAvailabilitySnapshot(className, specName, phaseKey, tabName, filters).reputations
end

FILTER_FACETS.ENHANCEMENT_META_FIELDS = {
    "source_type",
    "source_type_label",
    "source_filter_key",
    "source_filter_label",
    "acquisition_phase",
    "acquisitionPhaseIndex",
    "zone",
    "side",
    "binding",
    "boe",
    "quality",
}

function FILTER_FACETS.applyItemMetaToEnhancementRow(index, row)
    if not row.item_id then
        return
    end

    local meta = getItemMetaFromIndex(index, row.item_id, row.item) or {}
    for _, field in ipairs(FILTER_FACETS.ENHANCEMENT_META_FIELDS) do
        if row[field] == nil then
            row[field] = meta[field]
        end
    end
    row.source_filter_keys = row.source_filter_keys or meta.source_filter_keys or {}
    row.zones = row.zones or meta.zones or {}
    row.sides = row.sides or meta.sides or {}
    row.requirements = mergedRequirements(row.requirements, meta.requirements)
    row.reputations = rowReputationsWithMeta(meta.reputations, row.requirements)
end

function FILTER_FACETS.annotateEnhancementAccessFacets(index, row)
    local sourceFilterKeys = {}
    local sourceSeen = {}
    local zones = {}
    local zoneSeen = {}
    local sides = {}
    local sideSeen = {}
    local reputations = {}
    local reputationSeen = {}
    local earliestAcquisitionPhase
    local options = buildRowAccessOptions(index, row) or {}
    local primary = FILTER_FACETS.primaryAccessOption(options)

    for _, sourceType in ipairs(row.source_filter_keys or {}) do
        addUnique(sourceFilterKeys, sourceSeen, sourceType)
    end
    for _, zone in ipairs(row.zones or {}) do
        addUnique(zones, zoneSeen, zone)
    end
    for _, side in ipairs(row.sides or {}) do
        addUnique(sides, sideSeen, side)
    end
    for _, reputation in ipairs(row.reputations or {}) do
        addUnique(reputations, reputationSeen, reputation)
    end

    for _, option in ipairs(options) do
        addUnique(sourceFilterKeys, sourceSeen, option.source_filter_key or option.source_type)
        addUnique(zones, zoneSeen, option.zone)
        for _, zone in ipairs(option.zones or {}) do
            addUnique(zones, zoneSeen, zone)
        end
        addUnique(sides, sideSeen, option.side)
        addReputationsFromRequirements(reputations, reputationSeen, option.requirements)
        for _, reputation in ipairs(option.reputations or {}) do
            addUnique(reputations, reputationSeen, reputation)
        end
        earliestAcquisitionPhase = earlierPhaseKey(earliestAcquisitionPhase, option.acquisition_phase)
    end

    table.sort(sourceFilterKeys, sortSourceFilterKeys)
    table.sort(zones)
    table.sort(sides)
    table.sort(reputations)
    row.source_filter_keys = sourceFilterKeys
    row.zones = zones
    row.sides = sides
    row.reputations = reputations
    if primary then
        row.source_type = primary.source_type or row.source_type
        row.source_type_label = SOURCE_TYPE_LABELS[row.source_type] or row.source_type_label
        row.source_filter_key = primary.source_filter_key or row.source_filter_key
        row.source_filter_label = primary.source_filter_label or row.source_filter_label
        row.zone = primary.zone or row.zone
        row.side = primary.side or row.side
    end
    row.acquisition_phase = earliestAcquisitionPhase or row.acquisition_phase or "PR"
    row.acquisitionPhaseIndex = phaseIndex(row.acquisition_phase)
end

function FILTER_FACETS.enhancementAppliedValue(row, filters)
    if row.enhancement_kind == "consumable" then
        local ownedItems = filters and filters.ownedItems
        local ownedValue = FILTER_FACETS.tableValueById(ownedItems, row.item_id or row.entity_id)
        if ownedValue == nil then
            for _, candidateItemId in ipairs(row.item_ids or {}) do
                ownedValue = FILTER_FACETS.tableValueById(ownedItems, candidateItemId)
                if ownedValue ~= nil then
                    break
                end
            end
        end
        return ownedValue ~= nil and ownedValue ~= false
    end

    local resolver = filters and filters.getEnhancementAppliedState
    if type(resolver) == "function" then
        local ok, value = pcall(resolver, row)
        if ok and value ~= nil then
            return value
        end
    end

    local values = filters and (
        filters.appliedEnhancements
        or filters.enhancementApplied
        or filters.appliedStateByKey
    )
    if type(values) ~= "table" then
        return false
    end

    local value = values[row.enhancement_key]
    if value == nil then
        value = values[enhancementSourceKey(row.entity_type, row.entity_id)]
    end
    if value == nil then
        value = FILTER_FACETS.tableValueById(values, row.item_id or row.entity_id)
    end
    return value
end

function FILTER_FACETS.enhancementValueIsApplied(value)
    if type(value) == "table" then
        if value.applied ~= nil then
            return value.applied and true or false
        elseif value.state ~= nil then
            return value.state == "applied" or value.state == "owned"
        end
        return next(value) ~= nil
    elseif type(value) == "string" then
        return value ~= "" and value ~= "missing" and value ~= "not_applied" and value ~= "false"
    end
    return value and true or false
end

function FILTER_FACETS.enhancementRowMatchesLocalFilters(row, filters)
    local kind = filters and (filters.enhancementType or filters.enhancementKind)
    if kind and kind ~= "all" and kind ~= row.enhancement_kind then
        return false
    end
    if tableHasAnyEnabled(filters and filters.enhancementTypes)
        and not filters.enhancementTypes[row.enhancement_kind] then
        return false
    end

    local appliedState = filters and filters.appliedState
    if appliedState == "owned" then
        appliedState = "applied"
    elseif appliedState == "not_applied" then
        appliedState = "missing"
    end
    if appliedState and appliedState ~= "all" and row.applied_state ~= appliedState then
        return false
    end
    return true
end

function FILTER_FACETS.cloneFiltersForEnhancementRows(filters)
    local scoped = {}
    for key, value in pairs(filters or {}) do
        scoped[key] = value
    end
    scoped.rankGroup = "all"
    scoped.rankGroups = nil
    scoped.wishlistRelevance = nil
    scoped.relevance = nil
    return scoped
end

function FILTER_FACETS.finishEnhancementRow(addon, index, row, phaseKey, filters)
    row.enhancement_key = table.concat({
        tostring(row.enhancement_kind or "enhancement"),
        tostring(row.entity_type or "item"),
        tostring(row.entity_id or row.item_id or ""),
    }, ":")
    FILTER_FACETS.applyItemMetaToEnhancementRow(index, row)
    FILTER_FACETS.annotateEnhancementAccessFacets(index, row)

    local appliedValue = FILTER_FACETS.enhancementAppliedValue(row, filters)
    if appliedValue == nil then
        row.applied_state = "not_applicable"
        row.applied = nil
    else
        row.applied = FILTER_FACETS.enhancementValueIsApplied(appliedValue)
        row.applied_state = row.applied and "applied" or "missing"
    end
    local ownedState = FILTER_FACETS.tableValueById(filters and filters.ownedItems, row.item_id)
    if not ownedState then
        for _, candidateItemId in ipairs(row.item_ids or {}) do
            ownedState = FILTER_FACETS.tableValueById(filters and filters.ownedItems, candidateItemId)
            if ownedState then
                break
            end
        end
    end
    row.owned = ownedState ~= nil and ownedState ~= false
    row.ownership_state = row.ownership_state or ownedState

    local scopedFilters = FILTER_FACETS.cloneFiltersForEnhancementRows(filters)
    if not FILTER_FACETS.enhancementRowMatchesLocalFilters(row, filters)
        or not includeByFilter(row, scopedFilters, addon:GetAvailabilityPhaseIndex(phaseKey)) then
        return nil
    end

    row.acquisition_display = addon:GetRowAcquisitionDisplay(row, filters, phaseKey)
    row.matched_access_option = row.acquisition_display.option
    return row
end

function BigBiSList:GetEnhancementRows(className, specName, phaseKey, filters)
    filters = FILTER_FACETS.progressionFilters(filters, phaseKey) or {}
    local recommendationPhase = self:GetProgressionContext(phaseKey).content_phase
    local index = self:GetDataIndex(phaseKey)
    local sections = {
        { title = "Gems", rows = {} },
        { title = "Enchants", rows = {} },
        { title = "Consumables", rows = {} },
    }

    for _, gemRecord in ipairs(index.enhancement.gems or {}) do
        local gem = inflateCompactRecord(index, "gem", gemRecord)
        if gem["class"] == className and gem.spec == specName and gem.phase == recommendationPhase then
            local item = getIndexedItem(index, gem.id)
            local sourceData = inflateCompactRecord(index, "source_record", index.enhancement.gemSourcesById[gem.id])
            local accessOptions = buildAccessOptions(item, sourceData, gem.requirements, { entityType = "item" })
            local row = {
                entity_type = "item",
                entity_id = gem.id,
                item_id = gem.id,
                item = item,
                name = gem.name,
                phase = phaseKey,
                content_phase = recommendationPhase,
                context = gem.context,
                detail = gemDetailLabel(gem),
                enhancement_kind = "gem",
                gem_item_id = gem.id,
                source_summary = gem.source_summary or "",
                requirements = mergedRequirements(gem.requirements, item and item.requirements),
                access_options = accessOptions,
                recommendation_summary = gem.context == "budget" and "Budget alternative" or "Socket this gem",
            }
            applyEnhancementReadyAccess(row, accessOptions, row.source_summary, "Craft/AH")
            row.for_label = row.detail
            row = FILTER_FACETS.finishEnhancementRow(self, index, row, phaseKey, filters)
            if row then
                table.insert(sections[1].rows, row)
            end
        end
    end

    for _, enchantRecord in ipairs(index.enhancement.enchants or {}) do
        local enchant = inflateCompactRecord(index, "enchant", enchantRecord)
        if enchant["class"] == className and enchant.spec == specName and enchant.phase == recommendationPhase then
            local entityType = enchant.type or "item"
            local sourceKey = enhancementSourceKey(entityType, enchant.id)
            local effectData = inflateCompactRecord(index, "enchant_effect", index.enhancement.enchantEffectsByKey[sourceKey])
            local row = {
                entity_type = entityType,
                entity_id = enchant.id,
                name = enchant.name,
                detail = enchantDetailLabel(enchant),
                enhancement_kind = "enchant",
                match_slot = enchant.slot,
                enchant_effect_ids = effectData and effectData.effect_ids or {},
                enchant_effect_source_spell_id = effectData and effectData.source_spell_id or nil,
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
                row.item = getIndexedItem(index, enchant.id)
            end

            row.requirements = mergedRequirements(enchant.requirements, row.item and row.item.requirements)
            row.access_options = buildAccessOptions(row.item, inflateCompactList(index, "source_record", index.enhancement.enchantSourcesByKey[sourceKey]), enchant.requirements, {
                entityType = entityType,
                forceSourceScopedEquip = entityType == "spell",
                alwaysTradeOption = entityType == "spell",
                tradeLabel = entityType == "spell" and "Trade enchant service" or "Trade/Auction House",
            })
            if entityType == "spell" then
                applyEnhancementReadyAccess(row, nil, nil, "Enchanter")
            else
                applyEnhancementReadyAccess(row, row.access_options, row.source_summary, "Trade/AH")
            end

            row.for_label = row.slot or row.detail
            row = FILTER_FACETS.finishEnhancementRow(self, index, row, phaseKey, filters)
            if row then
                table.insert(sections[2].rows, row)
            end
        end
    end

    for _, consumableRecord in ipairs(index.enhancement.consumables or {}) do
        local consumable = inflateCompactRecord(index, "consumable", consumableRecord)
        if consumable["class"] == className and consumable.spec == specName and consumable.phase == recommendationPhase then
            local itemIds = consumable.items or {}
            if consumableCanGroupAlternatives(consumable, itemIds) then
                local primaryItemId = itemIds[1]
                local primaryItem = getIndexedItem(index, primaryItemId)
                local sourceSummary = consumableSourceSummary(consumable, itemIds)
                local accessOptions = buildConsumableAccessOptions(index, itemIds)
                local row = {
                    entity_type = "item",
                    entity_id = primaryItemId,
                    item_id = primaryItemId,
                    item_ids = itemIds,
                    item = primaryItem,
                    name = consumableDisplayName(consumable, itemIds, index),
                    detail = consumableDetailLabel(consumable),
                    enhancement_kind = "consumable",
                    source_summary = sourceSummary,
                    access_options = accessOptions,
                    recommendation_summary = consumableRecommendationSummary(consumable, true),
                }
                applyEnhancementReadyAccess(row, accessOptions, sourceSummary, "Trade/AH", consumableReadyAccessOverride(consumable))
                row.for_label = row.detail
                row = FILTER_FACETS.finishEnhancementRow(self, index, row, phaseKey, filters)
                if row then
                    table.insert(sections[3].rows, row)
                end
            else
                for itemIndex, itemId in ipairs(itemIds) do
                    local item = getIndexedItem(index, itemId)
                    local sourceSummary = consumableSourceSummary(consumable, { itemId })
                    local accessOptions = buildAccessOptions(item, nil, consumable.requirements, { entityType = "item" })
                    local row = {
                        entity_type = "item",
                        entity_id = itemId,
                        item_id = itemId,
                        item = item,
                        name = consumable.item_names and consumable.item_names[itemIndex] or getItemName(itemId, item),
                        detail = consumableDetailLabel(consumable, itemIndex),
                        enhancement_kind = "consumable",
                        source_summary = sourceSummary,
                        requirements = mergedRequirements(consumable.requirements, item and item.requirements),
                        access_options = accessOptions,
                        recommendation_summary = consumableRecommendationSummary(consumable, false, itemIndex),
                    }
                    applyEnhancementReadyAccess(row, accessOptions, sourceSummary, "Trade/AH", consumableReadyAccessOverride(consumable, itemIndex))
                    row.for_label = row.detail
                    row = FILTER_FACETS.finishEnhancementRow(self, index, row, phaseKey, filters)
                    if row then
                        table.insert(sections[3].rows, row)
                    end
                end
            end
        end
    end

    return sections
end

local TOOLTIP_SUMMARY_CHUNK_LIMIT = 3

local function tooltipSlotGroup(use)
    local slot = use and use.slot or ""
    if slot == "Main Hand" or slot == "Off Hand" or slot == "Dual Wield" then
        return "Weapon"
    end

    return slot
end

local function addTooltipGroupSlot(group, slot)
    if not slot or slot == "" then
        return
    end

    group.slot_seen = group.slot_seen or {}
    group.slots = group.slots or {}
    if not group.slot_seen[slot] then
        group.slot_seen[slot] = true
        table.insert(group.slots, slot)
    end
end

local function buildTooltipGroupSlotLabel(group)
    local seen = group and group.slot_seen or {}
    if seen["Main Hand"] or seen["Off Hand"] or seen["Dual Wield"] then
        if seen["Dual Wield"] or (seen["Main Hand"] and seen["Off Hand"]) then
            return "Main/Off Hand"
        end
        if seen["Main Hand"] then
            return "Main Hand"
        end
        return "Off Hand"
    end

    return (group and group.slots and group.slots[1]) or (group and group.slot) or ""
end

local function tooltipGroupKey(use)
    return table.concat({
        tostring(use.class or ""),
        tostring(use.spec or ""),
        tostring(tooltipSlotGroup(use)),
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
    if use and use.leveling then
        return use.tooltip_level_label or use.level_label or "Leveling"
    end

    local phase = PHASE_SHORT_DISPLAY[use.phase] or PHASE_DISPLAY[use.phase] or tostring(use.phase or "")
    return phase .. " " .. tooltipRankShortLabel(use)
end

local function tooltipUseDedupeKey(itemId, use)
    return table.concat({
        tostring(itemId or use.item_id or ""),
        tostring(use.item_id or ""),
        tostring(use.class or ""),
        tostring(use.spec or ""),
        tostring(use.phase or ""),
        tostring(tooltipSlotGroup(use)),
        tostring(tooltipRankShortLabel(use)),
        tostring(use.level_min or ""),
        tostring(use.level_max or ""),
    }, "|")
end

function LEVELING_HELPERS.tooltipSummary(use)
    if not use then
        return "Leveling"
    end
    return use.tooltip_level_label or tooltipPhaseSummary(use)
end

function LEVELING_HELPERS.buildTooltipGroupSummary(group, expanded)
    local uses = {}
    local seen = {}
    for _, use in ipairs(group.uses or {}) do
        table.insert(uses, use)
    end
    table.sort(uses, LEVELING_HELPERS.sortByNextLevel)

    local parts = {}
    for _, use in ipairs(uses) do
        local label = LEVELING_HELPERS.tooltipSummary(use)
        if not seen[label] then
            seen[label] = true
            table.insert(parts, label)
        end
    end

    if not expanded and #parts > TOOLTIP_SUMMARY_CHUNK_LIMIT then
        local remaining = #parts - TOOLTIP_SUMMARY_CHUNK_LIMIT
        while #parts > TOOLTIP_SUMMARY_CHUNK_LIMIT do
            table.remove(parts)
        end
        table.insert(parts, "+" .. tostring(remaining))
    end

    return table.concat(parts, ", ")
end

function FILTER_FACETS.tooltipPhaseRangeSummary(segment)
    local startLabel = PHASE_SHORT_DISPLAY[segment.startPhase] or PHASE_DISPLAY[segment.startPhase] or tostring(segment.startPhase or "")
    local endLabel = PHASE_SHORT_DISPLAY[segment.endPhase] or PHASE_DISPLAY[segment.endPhase] or tostring(segment.endPhase or "")
    if segment.startPhase ~= segment.endPhase then
        startLabel = startLabel .. "-" .. endLabel
    end
    return startLabel .. " " .. segment.rankLabel
end

function FILTER_FACETS.buildTooltipPhaseSegments(group)
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

    local entries = {}
    for _, use in ipairs(uses) do
        local rankLabel = tooltipRankShortLabel(use)
        local key = tostring(use.phase or "") .. "|" .. rankLabel
        if not seen[key] then
            seen[key] = true
            table.insert(entries, {
                phase = use.phase,
                phaseIndex = use.phaseIndex or phaseIndex(use.phase),
                rankLabel = rankLabel,
            })
        end
    end

    local segments = {}
    for _, entry in ipairs(entries) do
        local previous = segments[#segments]
        if previous and previous.rankLabel == entry.rankLabel and entry.phaseIndex == previous.endIndex + 1 then
            previous.endPhase = entry.phase
            previous.endIndex = entry.phaseIndex
        else
            table.insert(segments, {
                startPhase = entry.phase,
                endPhase = entry.phase,
                startIndex = entry.phaseIndex,
                endIndex = entry.phaseIndex,
                rankLabel = entry.rankLabel,
            })
        end
    end

    return segments
end

function FILTER_FACETS.buildTooltipGroupSummary(group, expanded)
    if group and group.leveling then
        return LEVELING_HELPERS.buildTooltipGroupSummary(group, expanded)
    end

    local parts = {}
    for _, segment in ipairs(FILTER_FACETS.buildTooltipPhaseSegments(group)) do
        table.insert(parts, FILTER_FACETS.tooltipPhaseRangeSummary(segment))
    end

    if not expanded and #parts > TOOLTIP_SUMMARY_CHUNK_LIMIT then
        local remaining = #parts - TOOLTIP_SUMMARY_CHUNK_LIMIT
        while #parts > TOOLTIP_SUMMARY_CHUNK_LIMIT do
            table.remove(parts)
        end
        table.insert(parts, "+" .. tostring(remaining))
    end

    return table.concat(parts, ", ")
end

function FILTER_FACETS.tooltipSpecEnabled(specFilters, className, specName)
    if type(specFilters) ~= "table" then
        return true
    end

    local classFilters = specFilters[className]
    if type(classFilters) ~= "table" then
        return false
    end

    return classFilters[specName] == true
end

function BigBiSList:GetLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext)
    local selectedLevel = clampLevelingLevel(level)
    local matches = {}
    local seenMatches = {}
    local playerClass = type(priorityContext) == "table" and priorityContext.playerClass or nil
    local playerSpec = type(priorityContext) == "table" and priorityContext.playerSpec or nil
    selectedSpecFirst = selectedSpecFirst ~= false

    for _, use in ipairs(self:GetItemLevelingUses(itemId)) do
        if LEVELING_HELPERS.isAvailableAt(use, selectedLevel) and FILTER_FACETS.tooltipSpecEnabled(specFilters, use.class, use.spec) then
            local key = tooltipUseDedupeKey(itemId, use)
            if not seenMatches[key] then
                seenMatches[key] = true
                table.insert(matches, use)
            end
        end
    end

    table.sort(matches, function(a, b)
        if playerClass then
            local aPlayerClass = a.class == playerClass and 1 or 0
            local bPlayerClass = b.class == playerClass and 1 or 0
            if aPlayerClass ~= bPlayerClass then
                return aPlayerClass > bPlayerClass
            end

            if playerSpec then
                local aPlayerSpec = (a.class == playerClass and a.spec == playerSpec) and 1 or 0
                local bPlayerSpec = (b.class == playerClass and b.spec == playerSpec) and 1 or 0
                if aPlayerSpec ~= bPlayerSpec then
                    return aPlayerSpec > bPlayerSpec
                end
            end
        end
        if selectedSpecFirst then
            local aSelected = (a.class == selectedClass and a.spec == selectedSpec) and 1 or 0
            local bSelected = (b.class == selectedClass and b.spec == selectedSpec) and 1 or 0
            if aSelected ~= bSelected then
                return aSelected > bSelected
            end
        end
        if a.class ~= b.class then
            return a.class < b.class
        end
        if a.spec ~= b.spec then
            return a.spec < b.spec
        end
        if slotIndex(a.slot) ~= slotIndex(b.slot) then
            return slotIndex(a.slot) < slotIndex(b.slot)
        end
        return LEVELING_HELPERS.sortForLevel(a, b, selectedLevel)
    end)

    return matches
end

function BigBiSList:GetTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters, priorityContext)
    local selectedPhase = type(priorityContext) == "table" and priorityContext.selectedPhase or nil
    local uses = self:GetTooltipUses(itemId, selectedPhase)
    local matches = {}
    local seenMatches = {}
    local playerClass = type(priorityContext) == "table" and priorityContext.playerClass or nil
    local playerSpec = type(priorityContext) == "table" and priorityContext.playerSpec or nil
    selectedSpecFirst = selectedSpecFirst ~= false

    for _, use in ipairs(uses) do
        if FILTER_FACETS.tooltipSpecEnabled(specFilters, use.class, use.spec)
            and FILTER_FACETS.useMatchesProgressionContext(use, selectedPhase)
            and (use.phase ~= "PR" or includeByFilter(use, { _pre_raid = true },
                phaseIndex(use.content_phase or self:GetProgressionContext(selectedPhase or "PR").content_phase))) then
            local key = tooltipUseDedupeKey(itemId, use)
            if not seenMatches[key] then
                seenMatches[key] = true
                table.insert(matches, use)
            end
        end
    end

    table.sort(matches, function(a, b)
        if playerClass then
            local aPlayerClass = a.class == playerClass and 1 or 0
            local bPlayerClass = b.class == playerClass and 1 or 0
            if aPlayerClass ~= bPlayerClass then
                return aPlayerClass > bPlayerClass
            end

            if playerSpec then
                local aPlayerSpec = (a.class == playerClass and a.spec == playerSpec) and 1 or 0
                local bPlayerSpec = (b.class == playerClass and b.spec == playerSpec) and 1 or 0
                if aPlayerSpec ~= bPlayerSpec then
                    return aPlayerSpec > bPlayerSpec
                end
            end
        end
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

function BigBiSList:GetGroupedLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext, expanded)
    local rawMatches = self:GetLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext)
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
                slots = {},
                slot_seen = {},
                uses = {},
                leveling = true,
                tooltip_grouped = true,
            }
            groups[key] = group
            table.insert(groupedMatches, group)
        end
        addTooltipGroupSlot(group, use.slot)
        table.insert(group.uses, use)
    end

    for _, group in ipairs(groupedMatches) do
        group.slot = buildTooltipGroupSlotLabel(group)
        group.phase_summary = FILTER_FACETS.buildTooltipGroupSummary(group, expanded)
        group.slot_seen = nil
    end

    return groupedMatches
end

function BigBiSList:GetGroupedTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters, priorityContext, expanded)
    local rawMatches = self:GetTooltipMatches(itemId, selectedClass, selectedSpec, selectedSpecFirst, specFilters, priorityContext)
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
                slots = {},
                slot_seen = {},
                uses = {},
                tooltip_grouped = true,
            }
            groups[key] = group
            table.insert(groupedMatches, group)
        end
        addTooltipGroupSlot(group, use.slot)
        table.insert(group.uses, use)
    end

    for _, group in ipairs(groupedMatches) do
        group.slot = buildTooltipGroupSlotLabel(group)
        group.phase_summary = FILTER_FACETS.buildTooltipGroupSummary(group, expanded)
        group.slot_seen = nil
    end

    return groupedMatches
end
