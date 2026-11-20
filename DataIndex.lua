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
if BigBiSList.isForever then
    PHASE_ORDER = {}
    PHASE_DISPLAY = { LEVELING = "Leveling" }
    for _, phase in ipairs(BigBiSListData.phases or {}) do
        PHASE_ORDER[#PHASE_ORDER + 1] = phase.key
        PHASE_DISPLAY[phase.key] = phase.name
    end
end
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

-- Evidence and physical occupancy are independent from list presentation order.
local RECOMMENDATION = {}

local SOURCE_FILTER_BY_CONTENT_TYPE = {
    raid = "raid_drop",
    heroic_dungeon = "heroic_dungeon_drop",
    dungeon = "dungeon_drop",
    other = "other_drop",
}

local RAID_ZONE_PHASE = not BigBiSList.isForever and {
    Karazhan = "T4",
    ["Gruul's Lair"] = "T4",
    ["Magtheridon's Lair"] = "T4",
    ["Serpentshrine Cavern"] = "T5",
    ["Tempest Keep"] = "T5",
    ["Hyjal Summit"] = "T6",
    ["Black Temple"] = "T6",
    ["Zul'Aman"] = "ZA",
    ["Sunwell Plateau"] = "SWP",
} or {}

local ZONE_PHASE = not BigBiSList.isForever and {
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
} or {}

local RAID_QUEST_PHASE_BY_ID = not BigBiSList.isForever and {
    [10725] = "T4",
    [10726] = "T4",
    [10727] = "T4",
    [10728] = "T4",
    [11031] = "T4",
    [11032] = "T4",
    [11033] = "T4",
    [11034] = "T4",
    [11007] = "T5",
} or {}

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
    if schemaName == "use" and type(record) == "number" then record = index.dataSource.uses[record] end
    if schemaName == "leveling_recommendation" and type(record) == "number" then
        local columns = index.dataSource.runtime_indexes and index.dataSource.runtime_indexes.recommendation_columns
        if columns then
            local column = columns[key]
            if not column then return nil end
            local width, values, dictionary = column[1], column[2], column[3]
            local offset = (record - 1) * width + 1
            local value = 0
            for position = offset, offset + width - 1 do value = value * 64 + values:byte(position) - 48 end
            return dictionary[value]
        end
        record = index.dataSource.leveling_recommendations[record]
    end
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
    elseif schemaName == "use" and key == "guide_evidence" then
        local result = {}
        index.guideEvidenceCache = index.guideEvidenceCache or {}
        for _, reference in ipairs(value or {}) do
            if type(reference) == "number" then
                local evidence = index.guideEvidenceCache[reference]
                if not evidence then
                    evidence = inflateCompactRecord(index, "guide_evidence", (index.dataSource.guide_evidence or {})[reference])
                    index.guideEvidenceCache[reference] = evidence
                end
                if evidence then result[#result + 1] = evidence end
            elseif type(reference) == "table" then
                result[#result + 1] = reference.table_id and reference or inflateCompactRecord(index, "guide_evidence", reference)
            end
        end
        return result
    elseif (schemaName == "use" or schemaName == "gem" or schemaName == "enchant" or schemaName == "consumable" or schemaName == "leveling_gear" or schemaName == "leveling_recommendation") and key == "requirements" then
        return inflateCompactList(index, "requirement", value)
    end

    return value
end

inflateCompactRecord = function(index, schemaName, record)
    if schemaName == "leveling_recommendation" and type(record) == "number" then
        local result = {}
        for _, key in ipairs(index.schemas[schemaName] or {}) do
            result[key] = inflateCompactField(index, schemaName, key, compactField(index, schemaName, record, key))
        end
        return result
    end
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
    if type(useRef) == "number" then useRef = index.dataSource.uses[useRef] end
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

function BigBiSList:GetItemVariantIdFromLink(itemLink)
    if type(itemLink) ~= "string" or not self.IsReadableValue(itemLink) then return nil end
    local itemId = tonumber(itemLink:match("item:(%d+)"))
    local rating = self.ForeverGearRating
    if not rating or not itemId then return nil end
    local key, _, _, exactRoll = rating:NormalizeLink(itemId, itemLink)
    if key and key ~= tostring(itemId) and (exactRoll or not rating:IsUnresolvedVariant(itemId)) then return key end
end

function FILTER_FACETS.rowOwnedState(ownedItems, row)
    if BigBiSList.isForever and row.variant_id then
        return ownedItems and ownedItems.variants and ownedItems.variants[row.variant_id]
    end
    local owned = FILTER_FACETS.tableValueById(ownedItems, row.item_id)
    if not owned then
        for _, itemId in ipairs(row.item_ids or {}) do
            owned = FILTER_FACETS.tableValueById(ownedItems, itemId)
            if owned then break end
        end
    end
    return owned
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
    -- A boss can supply several different prerequisites, or have different
    -- normal/heroic observations. Those records must never enrich one another.
    window = window .. "|" .. table.concat({
        tostring(source.token_item_id or ""), tostring(source.token_count or ""),
        tostring(source.quest_starter_item_id or ""), tostring(source.quest_starter_relationship or ""),
        tostring(source.item_id or ""), tostring(source.difficulty or ""),
        tostring(source.type == "drop" and (source.location_area or source.zone) or ""),
        tostring(source.type == "drop" and source.content_type or ""),
    }, ":")
    if BigBiSList.isForever then
        local point = source.destination or {}
        local eligibility = source.eligibility or {}
        -- A shared quest ID can represent distinct reviewed access routes.
        window = window .. "|" .. table.concat({
            tostring(source.side or ""), tostring(point.kind or ""), tostring(point.entity_id or ""),
            tostring(point.map_id or ""), tostring(point.x or ""), tostring(point.y or ""),
            tostring(eligibility.min_level or ""), tostring(eligibility.max_level or ""),
            concatValues(eligibility.races), concatValues(eligibility.classes),
            tostring(source.market_observation and source.market_observation.market or ""),
        }, ":")
    end
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
    if type(source) ~= "table" then return nil end
    local percent = tonumber(source.drop_percent)
    if source.drop_percent == nil then
        local count, total = tonumber(source.count), tonumber(source.out_of)
        if count and total and count == count and total == total
            and count >= 0 and total > 0 and total < math.huge and count <= total then
            percent = count / total * 100
        end
    end
    if not percent or percent ~= percent or percent < 0 or percent > 100 then return nil end
    if percent > 0 and percent < 0.1 then return "<0.1%" end
    return string.format("%.1f%%", percent)
end

function BigBiSList:FormatSourceRate(source)
    return formatDropPercent(source)
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

function FILTER_FACETS.optionIsVerifiedGuideRoute(option)
    -- Forever's recorded trade sources carry the faction and market evidence.
    -- The generic trade option only describes the item's binding.
    return FILTER_FACETS.optionIsCompleteRoute(option) and option.source_type ~= "unknown"
        and not option.is_inferred_trade_option and (not BigBiSList.isForever or not option.is_trade_option)
end

-- An observed market sale proves availability, but gives the player no farm target.
function BigBiSList:IsGuideTargetRoute(option)
    if not FILTER_FACETS.optionIsVerifiedGuideRoute(option) then return false end
    local source = option.source or {}
    local kind = option.source_type
    if kind == "drop" then
        local name = lower(source.entity_name)
        return name ~= "" and name ~= "world drop" and name ~= "world drops" and name ~= "unknown"
            and not source.world_drop and source.content_type ~= "world_drop"
            and (source.zone ~= nil or source.content_type == "dungeon" or source.content_type == "heroic_dungeon")
    end
    if kind == "quest" then return (source.quest_id or source.entity_id) ~= nil end
    if kind == "crafted" then return (source.spell_id or source.profession) ~= nil end
    if kind == "vendor" or kind == "pvp" or kind == "token_turnin" then
        return (source.entity_id or source.entity_name or option.vendor_label) ~= nil
    end
    return false
end

function BigBiSList:GetGuideMarket(faction)
    local region = ({[1] = "us", [3] = "eu", [5] = "cn"})[GetCurrentRegion and GetCurrentRegion() or 0]
    local realm = GetRealmName and GetRealmName()
    faction = lower(faction)
    if not (region and realm and (faction == "alliance" or faction == "horde")) then return false end
    local kind = lower(realm):gsub("[^a-z]", "")
    if kind == "pve" then kind = "normal" end
    if kind == "normal" or kind == "pvp" or kind == "rp" or kind == "rppvp" then
        return "forever/" .. kind .. "/" .. faction .. "/" .. region
    end
    return false
end

function BigBiSList:IsGuideMarketRoute(option, market)
    if not FILTER_FACETS.optionIsVerifiedGuideRoute(option) or option.source_type ~= "trade" then return false end
    local observed = option.source and option.source.market_observation
    return observed and type(observed.market) == "string" and (market == nil or observed.market == market) or false
end

local function matchesGuideTarget(addon, option, filters)
    return not filters or not filters._guideTarget or addon:IsGuideTargetRoute(option)
        or addon:IsGuideMarketRoute(option, filters._guideMarket or false)
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
        tostring(source.drop_percent or ""), tostring(source.count or ""), tostring(source.out_of or ""),
        tostring(source.entity_name or ""), tostring(source.token_name or ""),
        tostring(source.quest_starter_name or ""), tostring(source.source_url or ""),
        table.concat(source.activity_zones or {}, "\031"),
    }
    for _, requirement in ipairs(source.requirements or {}) do
        table.insert(parts, requirementKey(requirement))
    end
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
    for _, zone in ipairs(source.activity_zones or {}) do addSourceZone(zones, seen, zone) end
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
            activity_zones = source.activity_zones,
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
        sourceRecordsCacheKey(item and { item }),
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

function BigBiSList:GetGuideRatingDisplay(label)
    if not self.isForever or type(label) ~= "string" then return label end
    return (label:gsub("Best %(Alt%)", "Alternative")
        :gsub("%f[%a]Alt%f[%A]", "Alternative"):gsub("%f[%a]Opt%f[%A]", "Optional"))
end

local function rankShortLabel(use)
    if not use then
        return "No match"
    elseif use.rank_group == "bis" then
        local variant = bisVariantLabel(use)
        return variant and ("BiS: " .. variant) or "BiS"
    elseif use.rank_group == "ranked" then
        return BigBiSList:GetGuideRatingDisplay("Alt")
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
        return BigBiSList:GetGuideRatingDisplay(use.display_rank_label), use.display_rank_kind or "backup"
    end

    local rank = tonumber(use.rank)
    if use.rank_group == "bis" then
        local variant = bisVariantLabel(use)
        return variant and ("BiS: " .. variant) or "BiS", "best"
    elseif use.rank_group == "ranked" then
        return BigBiSList:GetGuideRatingDisplay("Alt"), "ranked"
    elseif use.rank_group == "situational" then
        return "Sidegrade", "situational"
    elseif use.rank_group == "pvp" then
        return "PvP", "pvp"
    elseif use.rank_group == "unrealistic" then
        return "Hard", "hard"
    elseif rank and rank > 1 then
        return BigBiSList:GetGuideRatingDisplay("Alt"), "ranked"
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
        return BigBiSList:GetGuideRatingDisplay("Alt") .. " for " .. phaseLabel
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
        local hasDependencies = false
        for _, key in ipairs({ "token_sources", "quest_starter_sources" }) do
            for _, child in ipairs(source[key] or {}) do
                hasDependencies = true
                addSourceFilterKey(sourceFilterKeys, seen, child, selectedPhaseIndex)
            end
        end
        if not hasDependencies then addUnique(sourceFilterKeys, seen, sourceFilterKey(source)) end
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
        for _, zone in ipairs(source.activity_zones or {}) do addSourceZone(zones, seen, zone, selectedPhaseIndex) end
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
    for _, activityZone in ipairs(source.activity_zones or {}) do
        if activityZone == zone and sourceZoneIsPhaseAvailable(zone, selectedPhaseIndex) then return true end
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
    if side == "Alliance" or side == "Horde" or side == "Both" then
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
        variant_id = useEntry and useEntry.variant_id,
        item = accessItem,
        name = meta.name or getItemName(itemId, item),
        rank = useEntry and useEntry.rank,
        rank_label = (useEntry and useEntry.rank_label) or "Option",
        rank_group = (useEntry and useEntry.rank_group) or "option",
        context = (useEntry and useEntry.context) or "standard",
        note = useEntry and useEntry.note,
        source_url = sourceUrl,
        guide_evidence = useEntry and useEntry.guide_evidence or {},
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
        race = entry.race,
        faction = entry.faction,
        race_id = entry.race_id,
        variant_id = entry.variant_id,
        random_suffix_id = entry.random_suffix_id,
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
        name = entry.variant_name or meta.name or getItemName(itemId, item),
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
    local entry = type(recommendationRef) == "table" and recommendationRef.item_id and recommendationRef
        or inflateCompactRecord(index, "leveling_recommendation", recommendationRef)
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
        faction = entry.faction,
        race_id = entry.race_id,
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
        random_suffix_id = entry.random_suffix_id,
        item = accessItem,
        name = entry.variant_name or meta.name or getItemName(itemId, item),
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

function LEVELING_HELPERS.scoringContext(className, specName, mode, level, filters)
    local scoring = BigBiSList.ForeverScoring
    if not scoring or not className or not specName or not level then return nil end
    return scoring:GetContext(className, specName, mode, level, filters)
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
    if BigBiSList.isForever and aActive and bActive
        and a.computed_recommendation and b.computed_recommendation
        and (a.rank or 999) ~= (b.rank or 999) then
        return (a.rank or 999) < (b.rank or 999)
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

    local key = tostring(row.item_id) .. (BigBiSList.isForever and row.variant_id and (":" .. row.variant_id) or "")
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
        if side == "Both" or side == faction then
            return true
        end
    end
    if option and option.side then
        hasSide = true
        if option.side == "Both" or option.side == faction then
            return true
        end
    end
    return not hasSide
end

function FILTER_FACETS.eligibilityMatchesCharacter(eligibility, filters, allowUnknownMinimum)
    if type(eligibility) ~= "table" then return allowUnknownMinimum or not (BigBiSList.isForever and filters._leveling) end
    local level = filters._leveling and filters.level
        or (BigBiSList.isForever and ((BigBiSList.maxLevelingLevel or 59) + 1))
    local minimum = tonumber(eligibility.min_level)
    if level and (minimum and minimum > level or not minimum and not allowUnknownMinimum) then return false end
    if level and eligibility.max_level and eligibility.max_level < level then return false end
    local function matches(values, selected)
        if not values or #values == 0 then return true end
        if not selected then return false end
        for _, value in ipairs(values) do if value == selected then return true end end
        return false
    end
    return matches(eligibility.races, filters.race) and matches(eligibility.classes, filters.class)
end

function BigBiSList:AccessOptionMatchesCharacter(option, filters)
    filters = filters or {}
    local function allows(source, depth)
        if not source or depth > 32 then return false end
        if not FILTER_FACETS.optionMatchesFaction(source, filters.faction)
            or not FILTER_FACETS.eligibilityMatchesCharacter(source.eligibility, filters) then return false end
        for _, key in ipairs({"token_sources", "quest_starter_sources", "recipe_sources"}) do
            if source[key] and #source[key] > 0 then
                local found = false
                for _, child in ipairs(source[key]) do if allows(child, depth + 1) then found = true; break end end
                if not found then return false end
            end
        end
        return true
    end
    if option.source then return allows(option.source, 1) end
    return FILTER_FACETS.optionMatchesFaction(option, filters.faction)
        and FILTER_FACETS.eligibilityMatchesCharacter(option.eligibility, filters)
end

function FILTER_FACETS.optionSourcePaths(option)
    if option._source_paths then return option._source_paths end
    local paths = {}
    local function visit(source, nodes, dependency)
        local path = {}
        for _, node in ipairs(nodes) do path[#path + 1] = node end
        path[#path + 1] = source
        local hasChildren = false
        for _, key in ipairs({ "token_sources", "quest_starter_sources" }) do
            for _, child in ipairs(source[key] or {}) do
                hasChildren = true
                visit(child, path, dependency or child)
            end
        end
        if not hasChildren then paths[#paths + 1] = { nodes = path, source = source, dependency = dependency } end
    end
    if option.source then visit(option.source, {}, nil) end
    option._source_paths = paths
    return paths
end

function FILTER_FACETS.optionPathContext(option, selectedPhaseIndex)
    local cached = option._path_context
    if cached and cached.phase == selectedPhaseIndex then return cached end
    local context = {phase = selectedPhaseIndex, paths = {}, unfiltered = {}}
    local paths = FILTER_FACETS.optionSourcePaths(option)
    if #paths == 0 then paths = {{ nodes = {}, source = nil }} end
    for _, path in ipairs(paths) do
        local candidate = {}
        for key, value in pairs(option) do
            if string.sub(key, 1, 1) ~= "_" then candidate[key] = value end
        end
        local zones, zoneSeen, activities, activitySeen = {}, {}, {}, {}
        local requirements, available = option.requirements or {}, true
        for _, node in ipairs(path.nodes) do
            if not sourceIsPhaseAvailable(node, selectedPhaseIndex) then available = false end
            addSourceZone(zones, zoneSeen, FILTER_FACETS.sourceLocationArea(node), selectedPhaseIndex)
            for _, zone in ipairs(node.activity_zones or {}) do
                addSourceZone(zones, zoneSeen, zone, selectedPhaseIndex)
                addSourceZone(activities, activitySeen, zone, selectedPhaseIndex)
            end
            if node.requirements and #node.requirements > 0 then requirements = mergedRequirements(requirements, node.requirements) end
        end
        if #path.nodes > 0 then
            candidate.source, candidate.zone, candidate.zones = path.source, nil, zones
            candidate.source_filter_key = sourceFilterKey(path.source)
            candidate.requirements, candidate.reputations = requirements, reputationsFromRequirements(requirements)
        else
            zones = option.zones or (option.zone and { option.zone }) or {}
            activities = option.activity_zones or {}
        end
        local match = { option = option, source = path.source or option.source,
            dependency = path.dependency, activity_zones = activities,
            zones = zones, source_filter_key = candidate.source_filter_key }
        context.paths[#context.paths + 1] = {candidate = candidate, path = path, available = available, match = match}
        if available then context.unfiltered[#context.unfiltered + 1] = match end
    end
    -- Keep only the latest progression context; presentation refreshes reuse
    -- these paths without an unbounded cache of filter combinations.
    option._path_context = context
    return context
end

function FILTER_FACETS.accessOptionFilterMatches(option, filters, selectedPhaseIndex)
    if not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then return {} end
    filters = filters or {}
    if not BigBiSList:AccessOptionMatchesCharacter(option, filters) then return {} end
    local context = FILTER_FACETS.optionPathContext(option, selectedPhaseIndex)
    local leveling = BigBiSList.isForever and filters._leveling
    if not leveling and not FILTER_FACETS.hasActiveOptionContextFilter(filters) then return context.unfiltered end
    local matches = {}
    for _, prepared in ipairs(context.paths) do
        local candidate, path = prepared.candidate, prepared.path
        local zones, activities = prepared.match.zones, prepared.match.activity_zones
        local eligiblePath = true
        if leveling then
            for _, source in ipairs(path.nodes) do
                if not FILTER_FACETS.optionMatchesFaction(source, filters.faction)
                    or not FILTER_FACETS.eligibilityMatchesCharacter(source.eligibility, filters) then
                    eligiblePath = false
                    break
                end
            end
        end
        local function sourceMatches(value)
            if not value or value == "all" then return true end
            if FILTER_FACETS.optionIsReportedOnly(option) then return false end
            return value == option.source_type or value == candidate.source_filter_key
                or (path.source and value == path.source.type)
        end
        local sourceTypesMatch = not tableHasAnyEnabled(filters.sourceTypes)
        for key, selected in pairs(filters.sourceTypes or {}) do
            if selected and sourceMatches(key) then sourceTypesMatch = true; break end
        end
        if prepared.available and eligiblePath and sourceMatches(filters.sourceType) and sourceTypesMatch
            and (not filters._pre_raid or FILTER_FACETS.optionIsPreRaid(candidate, selectedPhaseIndex))
            and FILTER_FACETS.optionMatchesFaction(candidate, filters.faction)
            and optionMatchesZoneFilter(candidate, filters.zone, selectedPhaseIndex)
            and optionMatchesAnySelectedZone(candidate, filters.zones, selectedPhaseIndex)
            and FILTER_FACETS.optionMatchesCostFilter(candidate, filters.cost, selectedPhaseIndex)
            and FILTER_FACETS.optionMatchesAnySelectedCost(candidate, filters.costs, selectedPhaseIndex)
            and FILTER_FACETS.optionMatchesVendorFilter(candidate, filters.vendor, selectedPhaseIndex)
            and FILTER_FACETS.optionMatchesAnySelectedVendor(candidate, filters.vendors, selectedPhaseIndex)
            and FILTER_FACETS.optionMatchesReputationFilter(candidate, filters.reputation, selectedPhaseIndex)
            and FILTER_FACETS.optionMatchesAnySelectedReputation(candidate, filters.reputations, selectedPhaseIndex) then
            local matchedZone
            for _, zone in ipairs(zones) do
                if zone == filters.zone or (filters.zones and filters.zones[zone]) then matchedZone = zone; break end
            end
            matches[#matches + 1] = { option = option, source = path.source or option.source,
                dependency = path.dependency, activity_zone = matchedZone, activity_zones = activities,
                zones = zones, source_filter_key = candidate.source_filter_key }
        end
    end
    return matches
end

local function optionMatchesSourceContext(option, filters, selectedPhaseIndex)
    return FILTER_FACETS.accessOptionFilterMatches(option, filters, selectedPhaseIndex)[1] ~= nil
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
        if side == "Both" or side == faction then
            return true
        end
    end

    if not hasSide and row.side then
        return row.side == "Both" or row.side == faction
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
    if row.faction and filters.faction and filters.faction ~= "all"
        and row.faction ~= "Both" and row.faction ~= filters.faction then return false end
    if BigBiSList.isForever and filters._leveling then
        if not raceMatches(row.race, filters.race) then return false end
        local eligibilityById = BigBiSListData.item_eligibility or {}
        local eligibility = eligibilityById[row.item_id] or eligibilityById[tostring(row.item_id)]
        if not FILTER_FACETS.eligibilityMatchesCharacter(eligibility, filters, row.stat_rank ~= nil) then return false end
    end

    if selectedPhaseIndex then
        local options = buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}
        local available = #options == 0
        for _, option in ipairs(options) do
            if accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then available = true; break end
        end
        if not available then return false end
    end

    if filters._pre_raid and not row.guide_source_unknown then
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

    local structuredOptions = buildRowAccessOptions(BigBiSList:GetDataIndex(), row)
    if not structuredOptions or #structuredOptions == 0 then
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

    local owned = FILTER_FACETS.rowOwnedState(filters.ownedItems, row)
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

function FILTER_FACETS.progressionFilters(filters, phaseKey, className)
    if phaseKey ~= "PR" then return filters end
    local scoped = {}
    for key, value in pairs(filters or {}) do scoped[key] = value end
    scoped._pre_raid = true
    if BigBiSList.isForever then
        scoped.faction = scoped.faction or BigBiSList:GetPlayerFactionName()
        scoped.race = scoped.race or BigBiSList:GetPlayerRaceName()
        scoped.class = scoped.class or className
    end
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
    return includeByFilter(row, FILTER_FACETS.progressionFilters(filters, phaseKey, row and row.class), selectedPhaseIndex)
end

function FILTER_FACETS.nextAvailableOptionPhase(option, selectedPhaseIndex)
    for candidateIndex = selectedPhaseIndex or 1, #PHASE_ORDER do
        if accessOptionIsPhaseAvailable(option, candidateIndex) then return candidateIndex end
    end
    return nil
end

function BigBiSList:GetMatchingRowAccessOption(row, filters, phaseKey, includeFuture, verifiedOnly)
    local options = buildRowAccessOptions(self:GetDataIndex(), row) or {}
    local scopedFilters = FILTER_FACETS.progressionFilters(filters, phaseKey, row and row.class)
    local selectedPhaseIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil
    local primary = FILTER_FACETS.primaryAccessOption(options)
    local best, bestPhase
    for _, option in ipairs(options) do
        local candidatePhase = selectedPhaseIndex
        if includeFuture then
            candidatePhase = FILTER_FACETS.nextAvailableOptionPhase(option, selectedPhaseIndex)
        end
        local preferred = option == primary
        if best and filters and filters._guideTarget then
            local trade, bestTrade = option.source_type == "trade", best.source_type == "trade"
            if trade ~= bestTrade then preferred = not trade end
        end
        if (not includeFuture or candidatePhase)
            and FILTER_FACETS.optionIsCompleteRoute(option)
            and (not verifiedOnly or FILTER_FACETS.optionIsVerifiedGuideRoute(option))
            and matchesGuideTarget(self, option, filters)
            and (not filters or not filters._questAvailable or filters._questAvailable(option))
            and optionMatchesSourceContext(option, scopedFilters, candidatePhase)
            and (not best or (candidatePhase or 0) < (bestPhase or 0)
                or (candidatePhase == bestPhase and preferred)) then
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

function BigBiSList:GetRowAcquisitionDisplay(row, filters, phaseKey, includeFutureMatches, verifiedOnly)
    if row and row.guide_source_unknown then
        return { status = "unknown", source_label = "Source unknown", source_summary = "Source unknown" }
    end
    local hasContextFilter = FILTER_FACETS.hasActiveOptionContextFilter(filters)
    local option = self:GetMatchingRowAccessOption(row, filters, phaseKey, false, verifiedOnly)
    if not option and includeFutureMatches and verifiedOnly then
        option = self:GetMatchingRowAccessOption(row, filters, phaseKey, true, true)
    end
    local selectedPhaseIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil
    if not option and not verifiedOnly and not hasActiveSourceContextFilter(filters) then
        local scopedFilters = FILTER_FACETS.progressionFilters(filters, phaseKey, row and row.class)
        for _, candidate in ipairs(buildRowAccessOptions(self:GetDataIndex(), row) or {}) do
            if FILTER_FACETS.optionIsReportedOnly(candidate)
                and optionMatchesSourceContext(candidate, scopedFilters, selectedPhaseIndex) then
                option = candidate
                break
            end
        end
    end
    if not option and not verifiedOnly and (includeFutureMatches or not hasContextFilter) then
        option = self:GetMatchingRowAccessOption(row, filters, phaseKey, true)
    end
    local acquisitionPhase = option and option.acquisition_phase or row and row.acquisition_phase or "PR"
    local available = option and accessOptionIsPhaseAvailable(option, selectedPhaseIndex) or false
    local nextPhaseIndex = option and FILTER_FACETS.nextAvailableOptionPhase(option, selectedPhaseIndex) or nil
    local future = nextPhaseIndex ~= nil and selectedPhaseIndex ~= nil and nextPhaseIndex > selectedPhaseIndex
    if future then acquisitionPhase = PHASE_ORDER[nextPhaseIndex] end
    local sourceMatch = option and FILTER_FACETS.accessOptionFilterMatches(option,
        FILTER_FACETS.progressionFilters(filters, phaseKey, row and row.class), future and nextPhaseIndex or selectedPhaseIndex)[1]

    return {
        option = option,
        source_match = sourceMatch,
        matched_dependency = sourceMatch and sourceMatch.dependency,
        activity_zone = sourceMatch and sourceMatch.activity_zone,
        activity_zones = sourceMatch and sourceMatch.activity_zones,
        source_label = option and filters and filters._guideTarget and option.source_filter_key == "trade" and SOURCE_TYPE_LABELS[option.source_type]
            or option and (option.source_filter_label or SOURCE_TYPE_LABELS[option.source_type])
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
        return BigBiSList.isForever and "Top targets" or "BiS Now"
    elseif score >= 55 then
        return BigBiSList.isForever and "Plan ahead" or "Future BiS"
    elseif score >= 30 then
        return BigBiSList:GetGuideRatingDisplay("Alt")
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

function RECOMMENDATION.facts(use)
    local facts = {}
    for _, evidence in ipairs(use and use.guide_evidence or {}) do
        local ratingPhase = evidence.rating_phase or evidence.guide_phase or use.phase
        if PHASE_DISPLAY[ratingPhase] then
            facts[#facts + 1] = { phase = ratingPhase, phaseIndex = phaseIndex(ratingPhase == "PR" and (evidence.content_phase or use.content_phase or "PR") or ratingPhase),
                rank_group = evidence.grade == 1 and #(evidence.conditions or {}) == 0 and "bis" or "ranked", evidence = evidence }
        end
    end
    if #facts == 0 and use then
        local label = use.rank_label or ""
        local exactBest = label == "Best" or label == "BiS" or label == "Best in slot" or label == "Best-in-slot"
        -- Forever's compact Pre-Raid rows carry the approval in rank_group.
        local approvedBest = BigBiSList.isForever and use.rank_group == "bis"
        facts[1] = { phase = use.phase, phaseIndex = use.phaseIndex or phaseIndex(use.phase),
            rank_group = (approvedBest or exactBest) and "bis" or "ranked",
            evidence = { guide_phase = use.phase, rating_phase = use.phase, original_rating = label ~= "" and label or "Recommended",
                grade = approvedBest and 1 or nil, conditions = {}, source_url = use.source_url, content_phase = use.content_phase } }
    end
    return facts
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
    local directPhases = {}
    for _, originalUse in ipairs(group.uses) do
        for _, fact in ipairs(RECOMMENDATION.facts(originalUse)) do
            if fact.evidence.guide_phase == fact.phase then directPhases[fact.phase] = true end
        end
    end

    for _, originalUse in ipairs(group.uses) do
      local scoreSeen = {}
      for _, use in ipairs(RECOMMENDATION.facts(originalUse)) do
        local factKey = tostring(use.phase) .. ":" .. use.rank_group
        if not scoreSeen[factKey] and (not directPhases[use.phase] or use.evidence.guide_phase == use.phase) then
        scoreSeen[factKey] = true
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
        addPlannerReason(reasons, reasonSeen, "Also recommended in " .. (PHASE_DISPLAY[PHASE_ORDER[lastUsefulIndex]] or "a later phase"))
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
        local ok, localizedName, raceToken, raceID = pcall(UnitRace, "player")
        if ok then
            if self.isForever and (raceID == 95 or raceID == 96) then return "Skyborne" end
            return RACE_TOKEN_NAMES[raceToken] or localizedName
        end
    end
    return nil
end

function BigBiSList:GetPlayerFactionName()
    if UnitFactionGroup then
        local ok, faction = pcall(UnitFactionGroup, "player")
        if ok and (faction == "Alliance" or faction == "Horde") then return faction end
    end
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
    local usesLivePhase = selectedPhase == "PR" or (self.isForever and selectedPhase == LEVELING_PHASE_KEY)
    local contentPhase = usesLivePhase and self:GetCurrentPhaseKey(nowEpoch) or selectedPhase
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

function BigBiSList:GetAccessOptionFilterMatch(option, filters, phaseKey)
    local selectedIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil
    return FILTER_FACETS.accessOptionFilterMatches(option, FILTER_FACETS.progressionFilters(filters, phaseKey), selectedIndex)[1]
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
    "levelingRecommendationCache", "enhancement", "guideEvidenceCache",
}

function BigBiSList:GetDataIndex(selectedPhaseKey)
    local checkpoint = self.ForeverGearRating and self.ForeverGearRating:GetWorkCheckpoint()
    local livePhase = self:GetCurrentPhaseKey()
    local scheduleId = (BigBiSListData or {}).active_schedule
    local contentPhase = selectedPhaseKey and self:GetProgressionContext(selectedPhaseKey).content_phase or livePhase
    if phaseIndex(contentPhase) == 999 then contentPhase = livePhase end
    local previousIndex = self.dataIndex
    local indexIsCurrent = previousIndex and previousIndex.livePhase == livePhase and previousIndex.scheduleId == scheduleId
        and previousIndex.dataSource == BigBiSListData
    if indexIsCurrent and self.progressionIndexes and self.progressionIndexes[contentPhase] then
        self.dataIndex = self.progressionIndexes[contentPhase]
        return self.dataIndex
    end

    local data = BigBiSListData or {}
    local compact = data.format == 2
    local sharedBase = indexIsCurrent and compact and self.progressionBase or nil
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
        guideEvidenceCache = {},
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
        local generated = data.runtime_indexes
        if not sharedBase then
            local function byId(field, schema, records, positions)
                if positions then
                    index[field] = setmetatable({}, { __index = function(_, id)
                        local position = positions[tostring(id)]
                        return position and records[position]
                    end })
                else
                    for _, record in ipairs(records or {}) do
                        if checkpoint then checkpoint() end
                        local id = compactField(index, schema, record, "id")
                        if id then index[field][id] = record end
                    end
                end
            end
            byId("itemRecordsById", "item", data.items, generated and generated.item_records == data.items and generated.items)
            byId("itemFallbackRecordsById", "item_fallback", data.item_fallbacks,
                generated and generated.fallback_records == data.item_fallbacks and generated.item_fallbacks)
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

        local generatedUses = generated and generated.uses_by_phase
            and generated.use_records == data.uses and generated.uses_by_phase[contentPhase]
        if generatedUses then
            local function byNumber(records)
                return setmetatable({}, { __index = function(_, id) return records[tostring(id)] end })
            end
            index.useRefsByItemId, index.tooltipUseRefsByItemId = byNumber(generatedUses[1]), byNumber(generatedUses[2])
            index.useRefsByClassSpec, index.useRefsByClassSpecPhase = generatedUses[3], generatedUses[4]
        else
            local tooltipAliasesByItemId = {}
            for _, aliasRecord in ipairs(data.tooltip_aliases or {}) do
                if checkpoint then checkpoint() end
                tooltipAliasesByItemId[aliasRecord[1]] = aliasRecord[2]
            end

            for _, useRef in ipairs(data.uses or {}) do
                if checkpoint then checkpoint() end
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
        end

        if not sharedBase then
            for _, levelingGearRef in ipairs(data.leveling_gear or {}) do
                if checkpoint then checkpoint() end
                local itemId = compactField(index, "leveling_gear", levelingGearRef, "item_id")
                local className = compactField(index, "leveling_gear", levelingGearRef, "class")
                local specName = compactField(index, "leveling_gear", levelingGearRef, "spec")
                addUseRef(index.levelingGearRefsByItemId, itemId, levelingGearRef)
                table.insert(ensureNestedUseBucket(index.levelingGearRefsByClassSpec, className, specName), levelingGearRef)
            end

            if generated and generated.leveling_records == data.leveling_recommendations then
                index.levelingRecommendationRefsByClassSpec = generated.leveling_by_profile
                index.levelingRecommendationRefsByItemId = setmetatable({}, { __index = function(_, id)
                    return generated.leveling_by_item[tostring(id)]
                end })
            else
                for _, recommendationRef in ipairs(data.leveling_recommendations or {}) do
                    if checkpoint then checkpoint() end
                    local itemId = compactField(index, "leveling_recommendation", recommendationRef, "item_id")
                    local className = compactField(index, "leveling_recommendation", recommendationRef, "class")
                    local specName = compactField(index, "leveling_recommendation", recommendationRef, "spec")
                    addUseRef(index.levelingRecommendationRefsByItemId, itemId, recommendationRef)
                    table.insert(ensureNestedUseBucket(index.levelingRecommendationRefsByClassSpec, className, specName), recommendationRef)
                end
            end

            for _, sourceData in ipairs(data.gem_sources or {}) do
                if checkpoint then checkpoint() end
                index.enhancement.gemSourcesById[compactField(index, "source_record", sourceData, "id")] = sourceData
            end

            for _, sourceData in ipairs(data.enchant_sources or {}) do
                if checkpoint then checkpoint() end
                local key = enhancementSourceKey(compactField(index, "source_record", sourceData, "type") or "item", compactField(index, "source_record", sourceData, "id"))
                index.enhancement.enchantSourcesByKey[key] = index.enhancement.enchantSourcesByKey[key] or {}
                table.insert(index.enhancement.enchantSourcesByKey[key], sourceData)
            end

            for _, effectData in ipairs(data.enchant_effects or {}) do
                if checkpoint then checkpoint() end
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

    if checkpoint then
        checkpoint()
        if self.dataIndex ~= previousIndex or BigBiSListData ~= data or self:GetCurrentPhaseKey() ~= livePhase then
            return self:GetDataIndex(selectedPhaseKey)
        end
    end
    if not indexIsCurrent then
        self.progressionIndexes = {}
        self.progressionIndexOrder = {}
        self.progressionBase = nil
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

function BigBiSList:ComparisonItemInScope(itemId, phase, selectedIndex)
    local item = self:GetItemData(itemId)
    if not item then return true end
    local known = false
    for _, option in ipairs(self:GetRowAccessOptions({ item_id = itemId, item = item }) or {}) do
        if option.source_type ~= "unknown" and not option.is_inferred_trade_option and FILTER_FACETS.optionIsCompleteRoute(option) then
            known = true
            if accessOptionIsPhaseAvailable(option, selectedIndex)
                and ((phase ~= "PR" and phase ~= LEVELING_PHASE_KEY) or FILTER_FACETS.optionIsPreRaid(option, selectedIndex)) then
                return true
            end
        end
    end
    return not known
end

function BigBiSList:IsStatRankGuideItemAvailable(itemId, context, knownOptions)
    if not context.guideEligibility then
        context.guideEligibility = FILTER_FACETS.progressionFilters({
            class = context.class, race = context.race, faction = context.faction,
            level = context.level, _leveling = context.leveling,
        }, context.phase, context.class)
    end
    local filters = context.guideEligibility
    local eligibilityById = BigBiSListData.item_eligibility or {}
    local eligibility = FILTER_FACETS.tableValueById(eligibilityById, itemId)
    if not FILTER_FACETS.eligibilityMatchesCharacter(eligibility, filters, true) then
        return false, "character_restriction"
    end
    local item = knownOptions == nil and self:GetItemData(itemId)
    if not item and not knownOptions then return false, "missing_item_record" end
    local verified, nextPhase
    for _, option in ipairs(knownOptions or self:GetRowAccessOptions({ item_id = itemId, item = item }) or {}) do
        if FILTER_FACETS.optionIsVerifiedGuideRoute(option) then
            verified = true
            if #FILTER_FACETS.accessOptionFilterMatches(option, filters, context.phaseIndex) > 0 then return true end
            local later = FILTER_FACETS.nextAvailableOptionPhase(option, context.phaseIndex)
            if later and later > context.phaseIndex and (not nextPhase or later < nextPhase)
                and #FILTER_FACETS.accessOptionFilterMatches(option, filters, later) > 0 then nextPhase = later end
        end
    end
    if nextPhase then return false, "future_phase", PHASE_ORDER[nextPhase] end
    return false, verified and "route_out_of_scope" or "unverified_route"
end

-- Inputs shared by the offline compiler and the live route matcher.
function BigBiSList:GetGuideTargetActivities(context, options)
    local names = {}
    for _, option in ipairs(options or {}) do
        local market = self:IsGuideMarketRoute(option)
        if market or self:IsGuideTargetRoute(option) then
            for _, match in ipairs(FILTER_FACETS.accessOptionFilterMatches(option, context.guideEligibility, context.phaseIndex)) do
                local display = {option = option, source_match = match, activity_zone = match.activity_zone,
                    activity_zones = match.activity_zones, source_label = option.source_filter_label}
                names[market and "Auction House" or self:GetActivityGroup({acquisition_display = display})] = true
            end
        end
    end
    local sorted = {}
    for name in pairs(names) do sorted[#sorted + 1] = name end
    table.sort(sorted)
    return sorted
end

function BigBiSList:GetGuideRouteTransitions(itemId)
    local marks, levels = {}, {}
    local function add(level)
        level = tonumber(level)
        if level and level >= 1 and level <= 59 and not marks[level] then
            marks[level] = true
            levels[#levels + 1] = level
        end
    end
    local function requirement(eligibility)
        if not eligibility then return end
        add(eligibility.min_level)
        if eligibility.max_level then add(eligibility.max_level + 1) end
    end
    add(1)
    requirement(FILTER_FACETS.tableValueById(BigBiSListData.item_eligibility or {}, itemId))
    local item = self:GetItemData(itemId)
    local options = item and {}
    if item then
        for _, option in ipairs(self:GetRowAccessOptions({ item_id = itemId, item = item }) or {}) do
            if FILTER_FACETS.optionIsVerifiedGuideRoute(option) then
                options[#options + 1] = option
                requirement(option.eligibility)
                for _, path in ipairs(FILTER_FACETS.optionSourcePaths(option)) do
                    for _, node in ipairs(path.nodes) do requirement(node.eligibility) end
                end
            end
        end
    end
    table.sort(levels)
    return levels, options or false
end

function BigBiSList:GetAccessOptionDetailFields(option)
    return FILTER_FACETS.accessOptionDetailFields(option)
end

function BigBiSList:GetSourceAttributionLines(source)
    local lines, seen = {}, {}
    local function visit(value)
        if type(value) ~= "table" then return end
        for _, credit in ipairs(value.attribution or {}) do
            if type(credit) == "table" and type(credit.credit) == "string" then
                local text = credit.credit
                if type(credit.source) == "string" and not string.find(text, credit.source, 1, true) then
                    text = text .. "\n" .. credit.source
                end
                if type(credit.licenceUrl) == "string" and not string.find(text, credit.licenceUrl, 1, true) then
                    text = text .. "\n" .. credit.licenceUrl
                end
                if not seen[text] then seen[text] = true; lines[#lines + 1] = text end
            end
        end
        for _, key in ipairs({ "recipe_sources", "quest_starter_sources", "token_sources" }) do
            for _, child in ipairs(value[key] or {}) do visit(child) end
        end
    end
    visit(source)
    return lines
end

-- Required items are identities; their independently observed origins are
-- routes. Sharing a boss does not make two tokens the same required item.
function BigBiSList:GetAccessOptionSourceItems(option, context)
    if type(option) ~= "table" or type(option.source) ~= "table" then return {} end
    if type(context) == "string" then context = {phase = context} end
    context = context or {}
    local phaseKey, filters = context.phase, context.filters or {}
    local selectedIndex = phaseKey and self:GetAvailabilityPhaseIndex(phaseKey) or nil
    local matches = FILTER_FACETS.accessOptionFilterMatches(option,
        FILTER_FACETS.progressionFilters(filters, phaseKey), selectedIndex)
    local matchedSources = {}
    for _, match in ipairs(matches) do
        if match.source then matchedSources[match.source] = true end
        if match.dependency then matchedSources[match.dependency] = true end
    end
    local results, groups = {}, {}
    local function visit(parent)
        for _, family in ipairs({
            {key = "token_sources", kind = "token", id = "token_item_id", name = "token_name"},
            {key = "quest_starter_sources", kind = "quest_starter", id = "quest_starter_item_id", name = "quest_starter_name"},
            {key = "recipe_sources", kind = "recipe", id = "item_id", name = "recipe_name"},
        }) do
            for _, source in ipairs(parent[family.key] or {}) do
                local itemId = tonumber(source[family.id])
                if itemId and itemId > 0 then
                    local relationship = source.quest_starter_relationship
                    local key = family.kind .. ":" .. itemId .. ":" .. tostring(relationship or "")
                    local group = groups[key]
                    local count = family.kind == "token" and (tonumber(source.token_count) or 1) or 1
                    if not group then
                        local item = self:GetItemData(itemId)
                        group = {key = key, kind = family.kind, item_id = itemId, item = item,
                            name = item and item.name or source[family.name] or ("Item " .. itemId),
                            count = count, relationship = relationship, routes = {},
                            source_url = source.token_source_url or source.quest_starter_source_url or source.source_url,
                            _route_keys = {}}
                        groups[key], results[#results + 1] = group, group
                    elseif group.count ~= count then group.count = nil end
                    local routeKey = FILTER_FACETS.sourceCacheSignature(source)
                    if not group._route_keys[routeKey] then
                        group._route_keys[routeKey] = true
                        local acquisitionPhase = deriveSourceAcquisitionPhase(source)
                        local available = accessOptionIsPhaseAvailable(option, selectedIndex)
                            and sourceIsPhaseAvailable(source, selectedIndex)
                            and (phaseKey ~= "PR" or not FILTER_FACETS.sourceRequiresRaid(source, selectedIndex))
                        local availabilityLabel
                        if not available then
                            if selectedIndex and phaseIndex(acquisitionPhase) > selectedIndex then
                                availabilityLabel = "Available in " .. self:GetPhaseDisplayName(acquisitionPhase)
                            elseif source.available_until_phase and selectedIndex
                                and selectedIndex >= phaseIndex(source.available_until_phase) then
                                availabilityLabel = "No longer available"
                            else availabilityLabel = "Unavailable in selected tier" end
                        end
                        group.routes[#group.routes + 1] = {key = routeKey, source = source,
                            entity_name = source.entity_name, zone = FILTER_FACETS.sourceLocationArea(source),
                            activity_zones = source.activity_zones, source_type = source.type,
                            difficulty = source.difficulty, rate_text = formatDropPercent(source),
                            available = available, availability_label = availabilityLabel,
                            acquisition_phase = acquisitionPhase, requirements = source.requirements or {},
                            count = count, matched = available and (matchedSources[source] == true
                                or (family.kind == "recipe" and #matches > 0)),
                            source_url = source.source_url, note = source.location_note or source.raw_source_text}
                    end
                end
                visit(source)
            end
        end
    end
    visit(option.source)
    for _, group in ipairs(results) do
        group._route_keys = nil
        table.sort(group.routes, function(a, b)
            if a.matched ~= b.matched then return a.matched end
            if a.available ~= b.available then return a.available end
            return a.key < b.key
        end)
    end
    return results
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

function RECOMMENDATION.coverage(index, className, specName)
    index.recommendationCoverage = index.recommendationCoverage or {}
    local key = tostring(className) .. "\031" .. tostring(specName)
    if index.recommendationCoverage[key] then return index.recommendationCoverage[key] end
    local coverage = {}
    for _, ref in ipairs(index.useRefsByClassSpec[className] and index.useRefsByClassSpec[className][specName] or {}) do
        local phase = compactField(index, "use", ref, "phase")
        local slot = compactField(index, "use", ref, "slot")
        coverage[phase] = coverage[phase] or {}
        coverage[phase][slot] = true
    end
    index.recommendationCoverage[key] = coverage
    return coverage
end

function RECOMMENDATION.slots(slotName)
    if not slotName then return nil end
    for _, definition in ipairs(EQUIPMENT_SLOTS) do
        if definition.key == slotName or definition.label == slotName then return definition.slots end
    end
    return DISPLAY_SLOT_FILTER_MAP[slotName] or { slotName }
end

function RECOMMENDATION.useFitsContext(addon, use, targetPhase)
    return FILTER_FACETS.useMatchesProgressionContext(use, targetPhase)
        and (use.phase ~= "PR" or includeByFilter(use, FILTER_FACETS.progressionFilters({}, "PR", use.class),
            use.content_phase and phaseIndex(use.content_phase) or addon:GetAvailabilityPhaseIndex(targetPhase)))
end

function BigBiSList:GetRecommendationHistory(itemId, className, specName, targetPhase, slot, variantId)
    itemId = tonumber(itemId)
    targetPhase = targetPhase or self:GetCurrentPhaseKey()
    local index = self:GetDataIndex(targetPhase)
    index.recommendationHistoryCache = index.recommendationHistoryCache or {}
    index.recommendationHistoryOrder = index.recommendationHistoryOrder or {}
    local key = table.concat({ tostring(itemId), tostring(className), tostring(specName), targetPhase, tostring(slot or ""), tostring(variantId or "") }, "\031")
    if index.recommendationHistoryCache[key] then return index.recommendationHistoryCache[key] end
    local history = { item_id = itemId, class = className, spec = specName, slot = slot, target_phase = targetPhase, phase_cells = {}, phases = {} }
    local coverage = RECOMMENDATION.coverage(index, className, specName)
    for _, phase in ipairs(PHASE_ORDER) do
        local covered = coverage[phase] and not slot
        for _, candidateSlot in ipairs(RECOMMENDATION.slots(slot) or {}) do
            if coverage[phase] and coverage[phase][candidateSlot] then covered = true end
        end
        local cell = { phase = phase, phase_label = PHASE_DISPLAY[phase], phase_short_label = PHASE_SHORT_DISPLAY[phase],
            phase_index = phaseIndex(phase), status = covered and "not_listed" or "no_guide", matched = false, uses = {}, evidence = {}, direct_evidence = {} }
        history.phases[phase] = cell
        history.phase_cells[#history.phase_cells + 1] = cell
    end
    for _, use in ipairs(self:GetItemUses(itemId, targetPhase)) do
        if use.class == className and use.spec == specName and (not variantId or (use.variant_id or tostring(itemId)) == variantId)
            and (not slot or slotListContains(RECOMMENDATION.slots(slot), use.slot))
            and RECOMMENDATION.useFitsContext(self, use, targetPhase) then
            for _, fact in ipairs(RECOMMENDATION.facts(use)) do
                local cell = history.phases[fact.phase]
                if cell then
                    cell.matched = true
                    cell.uses[#cell.uses + 1] = use
                    cell.evidence[#cell.evidence + 1] = fact.evidence
                    cell.use = cell.use or use
                    if fact.evidence.guide_phase == fact.phase then
                        cell.direct_evidence[#cell.direct_evidence + 1] = fact.evidence
                        cell.direct_use = cell.direct_use or use
                    end
                    cell.rank_group = fact.rank_group
                end
            end
        end
    end
    local targetIndex = phaseIndex(targetPhase)
    local future = { text = "No later recommendation listed", phases = {}, has_future = false }
    for _, cell in ipairs(history.phase_cells) do
        cell.rating_evidence = #cell.direct_evidence > 0 and cell.direct_evidence or cell.evidence
        cell.use = cell.direct_use or cell.use
        local labels, seen, conditional, grades = {}, {}, false, {}
        for _, evidence in ipairs(cell.rating_evidence) do
            local label = evidence.original_rating or "Recommended"
            if not seen[label] then labels[#labels + 1] = label; seen[label] = true end
            if #(evidence.conditions or {}) > 0 or not evidence.grade then conditional = true end
            if evidence.grade then grades[evidence.grade] = true end
        end
        if cell.matched then
            local gradeCount = 0
            for _ in pairs(grades) do gradeCount = gradeCount + 1 end
            local conflicting = gradeCount > 1 or (#labels > 1 and conditional)
            cell.status = (conditional or conflicting) and "conditional" or "rated"
            cell.rank_group = cell.status == "rated" and grades[1] and gradeCount == 1 and "bis" or "ranked"
            cell.labels = labels
            cell.label = conflicting and "Depends on setup" or table.concat(labels, " / ")
            if cell.phase_index < targetIndex then history.latest_earlier = cell end
            if cell.phase_index > self:GetAvailabilityPhaseIndex(targetPhase) then
                future.phases[#future.phases + 1] = cell.phase
                future.furthest_phase = cell.phase
                future.has_future = true
            end
        else
            cell.label = cell.status == "no_guide" and "No guide data" or "Not listed"
        end
        cell.short_label = cell.label
    end
    if future.has_future then
        local names = {}
        for _, phase in ipairs(future.phases) do names[#names + 1] = (PHASE_DISPLAY[phase] or phase) .. ": " .. history.phases[phase].label end
        future.text = "Also recommended in " .. table.concat(names, "; ")
    end
    history.selected = history.phases[targetPhase]
    history.best_use = history.selected and history.selected.use or history.latest_earlier and history.latest_earlier.use
    history.future_summary = future
    return putBoundedCache(index.recommendationHistoryCache, index.recommendationHistoryOrder, key, history, ITEM_META_CACHE_LIMIT)
end

function BigBiSList:IsConfirmedGearBiS(history, phase, itemId, variantKey)
    local selected = history and history.selected
    if not (selected and selected.phase == phase and selected.status == "rated" and selected.rank_group == "bis") then return false end
    local approvedVariant = selected.use and selected.use.variant_id or tostring(itemId)
    return variantKey ~= nil and variantKey == approvedVariant
end

function RECOMMENDATION.gearNote(cell, summary)
    local lines, seen = { summary }, {}
    local function add(condition)
        if type(condition) == "string" and condition ~= "" and not seen[condition] then
            seen[condition] = true
            lines[#lines + 1] = condition
        end
    end
    for _, evidence in ipairs(cell.rating_evidence or cell.evidence or {}) do
        if type(evidence.conditions) == "table" then
            for _, condition in ipairs(evidence.conditions) do add(condition) end
        else
            add(evidence.conditions)
        end
    end
    return table.concat(lines, "\n")
end

function RECOMMENDATION.gearSummary(cell)
    return BigBiSList:GetPhaseDisplayName(cell.phase) .. " · " .. BigBiSList:GetGuideRatingDisplay(cell.label)
end

function RECOMMENDATION.gearBadge(cell, phase, confirmedBiS)
    if confirmedBiS then return "BiS" end
    if cell.phase ~= phase then return "Earlier phase" end
    local label = BigBiSList:GetGuideRatingDisplay(cell.label)
    return (label == "BiS" or label == "Best in slot") and "Guide note" or label
end

function BigBiSList:CompareRecommendationItems(candidateId, referenceId, className, specName, targetPhase, slot, referenceContext, candidateRow)
    candidateId, referenceId = tonumber(candidateId), tonumber(referenceId)
    targetPhase = targetPhase or self:GetCurrentPhaseKey()
    local rating = self.ForeverGearRating
    local result = { candidate_id = candidateId, reference_id = referenceId, relation = "unranked", historical = false,
        evidence = {}, explanation = "No shared guide rating is available for this comparison." }
    if not candidateId or not referenceId then
        result.explanation = referenceId and "No candidate selected." or "No equipped reference item."
        return result
    end
    if rating and referenceContext and referenceContext.ownedSnapshot and referenceContext.slotKey and targetPhase == "PR" then
        local link = candidateRow and candidateRow.item_link
        local key = candidateRow and (candidateRow.stat_identity or candidateRow.variant_id) or tostring(candidateId)
        local facts
        if link then facts = rating:GetExactBaseFacts(candidateId, link)
        else facts = rating:GetPublishedFacts(key) end
        local context = rating:GetContext(className, specName, targetPhase, 60, referenceContext.ownedSnapshot)
        local swap = rating:GetGuideSwap(context, facts, referenceContext.slotKey, slot, link)
        if swap and swap.delta ~= nil then
            local delta = swap.delta
            result.relation = swap.conditional and "unranked"
                or (delta > 0.0001 and "higher" or (delta < -0.0001 and "lower" or "same_rating"))
            result.phase, result.basis_key, result.score_delta = targetPhase,
                swap.basis == "active" and "active_build" or "reference_stats", delta
            result.explanation = LEVELING_HELPERS.formatSwap(rating, swap)
            return result
        end
    end
    if candidateId == referenceId then
        result.relation, result.explanation = "same_rating", "Same item."
        return result
    end
    local state = not rating and targetPhase == "PR" and LEVELING_HELPERS.scoringContext(className, specName, "pre_raid", 60)
    if state then
        local delta, effects, failure = self.ForeverScoring:Compare(state, slot, candidateId, referenceId, referenceContext)
        if delta then
            result.relation = delta > 0.0001 and "higher" or (delta < -0.0001 and "lower" or "same_rating")
            result.phase, result.basis_key, result.score_delta = targetPhase, "active_build", delta
            result.explanation = "Your setup · " .. string.format("%+.2f", delta)
            if #effects > 0 then result.explanation = result.explanation .. " · " .. table.concat(effects, ", ") end
            return result
        end
        if failure == "illegal_swap" then return result end
    end
    local candidate = self:GetRecommendationHistory(candidateId, className, specName, targetPhase, slot)
    local reference = self:GetRecommendationHistory(referenceId, className, specName, targetPhase, slot)
    for phaseOrder = phaseIndex(targetPhase), 1, -1 do
        local phase = PHASE_ORDER[phaseOrder]
        local candidateCell, referenceCell = candidate.phases[phase], reference.phases[phase]
        local evidencePairs, directions, conditional, basis = {}, {}, false, nil
        for _, a in ipairs(candidateCell and candidateCell.rating_evidence or {}) do
            for _, b in ipairs(referenceCell and referenceCell.rating_evidence or {}) do
                if a.table_id and a.table_id == b.table_id and a.rating_phase == b.rating_phase
                    and a.guide_phase == b.guide_phase and a.content_phase == b.content_phase then
                    evidencePairs[#evidencePairs + 1] = { candidate = a, reference = b }
                    local pairBasis = a.table_id .. ":" .. tostring(a.rating_phase)
                    if basis and basis ~= pairBasis then conditional = true end
                    basis = basis or pairBasis
                    if a.grade and b.grade and #(a.conditions or {}) == 0 and #(b.conditions or {}) == 0 then
                        directions[a.grade < b.grade and "higher" or (a.grade > b.grade and "lower" or "same_rating")] = true
                    else conditional = true end
                end
            end
        end
        if #evidencePairs > 0 then
            local relation, count
            count = 0
            for value in pairs(directions) do relation = value; count = count + 1 end
            result.relation = (conditional or count ~= 1) and "conditional" or relation
            result.phase, result.historical, result.evidence = phase, phase ~= targetPhase, evidencePairs
            result.basis_key = not conditional and count == 1 and basis or nil
            local scope = (result.historical and "Historical " or "") .. (PHASE_DISPLAY[phase] or phase) .. " guide: "
            local meanings = { higher = "rated higher in the same source table.", lower = "rated lower in the same source table.",
                same_rating = "same guide rating; this does not mean equal performance.", conditional = "comparison depends on setup or conflicting source conditions." }
            result.explanation = scope .. meanings[result.relation]
            return result
        end
    end
    return result
end

function BigBiSList:GetWishlistExpansionSummary(itemId, className, selectedSpec, selectedPhaseKey, variantId)
    itemId = tonumber(itemId)
    if not itemId then
        return nil
    end

    local index = self:GetDataIndex(selectedPhaseKey)
    local cacheKey = table.concat({ tostring(itemId), tostring(className or ""), tostring(selectedSpec or ""), tostring(selectedPhaseKey or ""), tostring(variantId or "") }, "|")
    if index.wishlistSummaryCache[cacheKey] then
        return index.wishlistSummaryCache[cacheKey]
    end

    local usesBySpecPhase = {}
    local slotSeen = {}
    local slots = {}
    local bestClassUse
    for _, use in ipairs(self:GetItemUses(itemId, selectedPhaseKey)) do
        if use.class == className and (not variantId or (use.variant_id or tostring(itemId)) == variantId)
            and FILTER_FACETS.useMatchesProgressionContext(use, selectedPhaseKey) then
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
        local history = self:GetRecommendationHistory(itemId, className, specName, selectedPhaseKey, nil, variantId)
        ranking.history, ranking.future_summary = history, history.future_summary
        ranking.phases, ranking.phase_cells = history.phases, history.phase_cells
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
        recommendation_history = selectedSpecRanking and selectedSpecRanking.history,
        future_summary = selectedSpecRanking and selectedSpecRanking.future_summary,
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

function BigBiSList:GetWishlistKey(itemId, row)
    if self.isForever and row and not row.wishlist_any then
        return tostring(self:GetItemVariantIdFromLink(row.item_link) or row.variant_id or itemId)
    end
    return tostring(itemId)
end

function BigBiSList:NormalizeWishlistVariants(wishlist)
    if not self.isForever or not wishlist or self.normalizedWishlist == wishlist then return end
    local changes = {}
    for key, saved in pairs(wishlist) do
        if type(saved) == "table" and saved.variant_id and saved.item_link then
            local exact = self:GetItemVariantIdFromLink(saved.item_link)
            if exact and key ~= exact then changes[key] = exact end
        end
    end
    for old, exact in pairs(changes) do
        local saved = wishlist[old]
        saved.variant_id = exact
        wishlist[exact], wishlist[old] = wishlist[exact] or saved, nil
    end
    self.normalizedWishlist = wishlist
end

function FILTER_FACETS.wishlistEntries(wishlistItems)
    BigBiSList:NormalizeWishlistVariants(wishlistItems)
    local entries, seen = {}, {}
    for key, value in pairs(wishlistItems or {}) do
        local saved = type(value) == "table" and value.item_id and value
        local id = saved and tonumber(saved.item_id) or tonumber(value) or (value and tonumber(key))
        if id then
            local identity = saved and saved.variant_id or tostring(id)
            if not seen[identity] then
                entries[#entries + 1] = saved or {item_id = id}
                seen[identity] = true
            end
        end
    end
    table.sort(entries, function(a, b)
        if a.item_id ~= b.item_id then return a.item_id < b.item_id end
        return (a.variant_id or "") < (b.variant_id or "")
    end)
    return entries
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
    if self.isForever then filters = FILTER_FACETS.progressionFilters(filters, selectedPhase, className) or filters end
    local index = self:GetDataIndex(selectedPhase)
    local context = self:GetProgressionContext(selectedPhase)
    local livePhase = self:GetCurrentPhaseKey()
    local browseFilters = filters
    if self.isForever then
        browseFilters = {}
        for key, value in pairs(filters) do browseFilters[key] = value end
        -- A star stays visible before its equip level and before a route is known.
        browseFilters._leveling, browseFilters._pre_raid = nil, nil
    end
    local rows = {}

    for _, saved in ipairs(FILTER_FACETS.wishlistEntries(wishlistItems)) do
        local itemId = saved.item_id
        local item = getIndexedItem(index, itemId)
        local meta = getItemMetaFromIndex(index, itemId, item) or {}
        local summary = self:GetWishlistExpansionSummary(itemId, className, selectedSpec, selectedPhase, saved.variant_id)
        local bestUse = summary and summary.best_use or nil
        local ownedState = FILTER_FACETS.rowOwnedState(filters.ownedItems, saved)
        local facts = self.ForeverGearRating and self.ForeverGearRating:GetPublishedFacts(saved.variant_id or tostring(itemId))
        local row = {
            item_id = itemId, variant_id = saved.variant_id, wishlist_any = self.isForever and not saved.variant_id,
            item_link = saved.item_link or (facts and facts.variant_link),
            item = item,
            name = saved.name or (facts and facts.name) or meta.name or getItemName(itemId, item),
            class = className,
            spec = selectedSpec,
            phase = selectedPhase,
            phaseIndex = context.content_phase_index,
            content_phase = context.content_phase,
            selected_phase = selectedPhase,
            live_phase = livePhase,
            slots = summary and summary.slots or {},
            slot = saved.slot or (facts and facts.slot) or (summary and summary.slots[1]),
            slot_label = saved.slot or (facts and facts.slot) or (summary and summary.slot_label) or "—",
            spec_rankings = summary and summary.spec_rankings or {},
            relevant_spec_rankings = summary and summary.relevant_spec_rankings or {},
            selected_spec_ranking = summary and summary.selected_spec_ranking or nil,
            selected_spec_relevant = summary and summary.selected_spec_relevant or false,
            class_relevant = summary and summary.class_relevant or false,
            ranking_search_text = summary and summary.ranking_search_text or "",
            not_ranked_label = summary and summary.not_ranked_label or nil,
            expansion_summary = summary,
            recommendation_history = summary and summary.recommendation_history,
            future_summary = summary and summary.future_summary,
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
        if includeByFilter(row, browseFilters, filterPhaseIndex) and FILTER_FACETS.wishlistRowMatchesRelevance(row, filters) then
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
    local cacheKey = self.isForever and (tostring(itemId) .. ":" .. tostring(self:GetPlayerRaceName()) .. ":" .. tostring(self:GetPlayerFactionName())) or itemId
    if index.levelingGearCache[cacheKey] then
        return index.levelingGearCache[cacheKey]
    end

    local rows = {}
    for _, levelingRef in ipairs(index.levelingGearRefsByItemId[itemId] or {}) do
        local row = buildLevelingGearRow(index, levelingRef)
        if row and (not self.isForever or (raceMatches(row.race, self:GetPlayerRaceName())
            and (not row.faction or row.faction == "Both" or row.faction == self:GetPlayerFactionName()))) then
            table.insert(rows, row)
        end
    end
    for _, recommendationRef in ipairs(index.levelingRecommendationRefsByItemId[itemId] or {}) do
        local row = buildLevelingRecommendationRow(index, recommendationRef)
        if row and (not self.isForever or (raceMatches(row.race, self:GetPlayerRaceName())
            and (not row.faction or row.faction == "Both" or row.faction == self:GetPlayerFactionName()))) then
            table.insert(rows, row)
        end
    end
    table.sort(rows, LEVELING_HELPERS.sortByNextLevel)
    index.levelingGearCache[cacheKey] = rows
    return rows
end

function BigBiSList:GetItemLevelingRecommendationUses(itemId, race)
    itemId = tonumber(itemId)
    if not itemId then
        return {}
    end

    local faction = self.isForever and self:GetPlayerFactionName()
    local cacheKey = tostring(itemId) .. ":" .. tostring(race or "") .. (self.isForever and (":" .. tostring(faction)) or "")
    local index = self:GetDataIndex()
    if index.levelingRecommendationCache[cacheKey] then
        return index.levelingRecommendationCache[cacheKey]
    end

    local rows = {}
    for _, recommendationRef in ipairs(index.levelingRecommendationRefsByItemId[itemId] or {}) do
        local row = buildLevelingRecommendationRow(index, recommendationRef)
        if row and raceMatches(row.race, race) and (not self.isForever or not row.faction or row.faction == "Both" or row.faction == faction) then
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
            and (not self.isForever or RECOMMENDATION.useFitsContext(self, use, preferredPhaseKey))
            and (not allowedSlots or slotListContains(allowedSlots, use.slot))
            and isBetterGearUse(use, bestUse, preferredPhaseKey) then
            bestUse = use
        end
    end

    return bestUse
end

function BigBiSList:GetItemBestLevelingUseForSpec(itemId, className, specName, level, allowedSlots, race, itemLink)
    local selectedLevel = clampLevelingLevel(level)
    race = race or self:GetPlayerRaceName()
    local bestUse

    for _, row in ipairs(self:GetItemLevelingUses(itemId)) do
        if row.class == className
            and row.spec == specName
            and raceMatches(row.race, race)
            and (not self.isForever or not row.variant_id or row.variant_id == self:GetItemVariantIdFromLink(itemLink))
            and LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
            and (not allowedSlots or slotListContains(allowedSlots, row.slot)) then
            if LEVELING_HELPERS.rowBeats(row, bestUse, race, selectedLevel) then
                bestUse = row
            end
        end
    end

    return bestUse
end

function LEVELING_HELPERS.gearRecommendationText(use, specName)
    local text = "Gear Guide recommends this for " .. (use.spec or specName)
    local first, last = use.level_min, use.level_max
    if first and last and last > first then
        return text .. " at levels " .. first .. "–" .. last
    elseif first then
        return text .. " at level " .. first
    end
    return text
end

function BigBiSList:GetLevelingEquipmentComparison(row, reference)
    if not row or not row.scoring_basis then return nil end
    local state = LEVELING_HELPERS.scoringContext(row.class, row.spec, "leveling", row.level_min)
    if not state then return nil end
    local scoring = self.ForeverScoring
    local options = {candidateVariant = row.variant_id}
    local referenceId, referenceLabel
    if reference then
        if not reference.item_id or not reference.item_link or not reference.inventorySlotId then return nil end
        referenceId, referenceLabel = reference.item_id, reference.slot or "equipped gear"
        options.inventorySlotId, options.item_link = reference.inventorySlotId, reference.item_link
    else
        local rank = scoring:RankSlot(state, row.slot).byIdentity[row.variant_id or tostring(row.item_id)]
        local equipped = rank and state.gear[rank.target]
        if not equipped then return nil end
        referenceId, referenceLabel = equipped.id, "equipped gear"
    end
    local delta, effects = scoring:Compare(state, row.slot, row.item_id, referenceId, options)
    if delta then
        local difference = "Compared with " .. referenceLabel .. " " .. string.format("%+.2f", delta)
        if #effects > 0 then difference = difference .. " · " .. table.concat(effects, ", ") end
        return difference
    end
end

function BigBiSList:GetItemNextLevelingUseForSpec(itemId, className, specName, level, allowedSlots, race, itemLink)
    local selectedLevel = clampLevelingLevel(level)
    race = race or self:GetPlayerRaceName()
    local matches = {}

    for _, row in ipairs(self:GetItemLevelingUses(itemId)) do
        if row.class == className
            and row.spec == specName
            and raceMatches(row.race, race)
            and (not self.isForever or not row.variant_id or row.variant_id == self:GetItemVariantIdFromLink(itemLink))
            and (tonumber(row.level_min) or 1) > selectedLevel
            and (not allowedSlots or slotListContains(allowedSlots, row.slot)) then
            table.insert(matches, row)
        end
    end

    table.sort(matches, LEVELING_HELPERS.sortByNextLevel)
    return matches[1]
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
        contexts = addon:GetEquipmentComparisonContexts(className, specName, preferredPhaseKey, ownedItems),
        ownedItems = ownedItems or {}, class = className, spec = specName,
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
    local candidateUse = group.bestUse
    local ownedState = FILTER_FACETS.tableValueById(baselines.ownedItems, group.item_id)
    local contexts = {}
    for _, context in ipairs(baselines.contexts) do
        if slotListContains(context.dataSlots, group.slot) then contexts[#contexts + 1] = context end
    end
    group.equipment_contexts, group.comparisons = contexts, {}
    local reference, chosen, unresolved, empty = contexts[1], nil, false, false
    for _, context in ipairs(contexts) do
        if context.occupancy == "empty" then empty = true
        elseif context.occupancy == "unknown" then unresolved = true
        elseif context.occupancy == "occupied" then
            local comparison = BigBiSList:CompareRecommendationItems(group.item_id, context.item_id, baselines.class, baselines.spec, selectedPhaseKey, group.slot, context)
            comparison.reference_context = context
            group.comparisons[#group.comparisons + 1] = comparison
            if not chosen or comparison.relation == "higher" then chosen, reference = comparison, context end
            if comparison.relation == "unranked" or comparison.relation == "conditional" or comparison.historical then unresolved = true end
        end
    end
    if #contexts == 0 then unresolved = true end
    local blocked = #contexts > 0
    for _, context in ipairs(contexts) do if context.occupancy ~= "blocked" then blocked = false end end
    local higher = chosen and chosen.relation == "higher" or false
    local history = group.recommendation_history
    local future = history and history.future_summary.has_future or false
    local candidate = not blocked and ownedState ~= "equipped" and (higher or unresolved or empty or future)
    group.comparison = chosen or { relation = "unranked", historical = false, evidence = {},
        explanation = blocked and "A two-handed weapon occupies this equipment position." or (empty and "This equipment position is empty." or "No equipped comparison is available.") }
    group.higher_rated, group.upgrade_candidate = higher and ownedState ~= "equipped", candidate
    group.owned_alternatives = {}
    for _, ownedContext in ipairs(baselines.ownedBySlot[group.slot] or {}) do
        local itemId, state = ownedContext.item_id, ownedContext.state
        if (state == "bag" or state == "bank") and itemId ~= group.item_id then
            local comparison = BigBiSList:CompareRecommendationItems(itemId, group.item_id, baselines.class, baselines.spec, selectedPhaseKey, group.slot)
            if comparison.relation == "higher" then
                group.owned_alternatives[#group.owned_alternatives + 1] = { item_id = itemId, state = state, comparison = comparison }
            end
        end
    end
    table.sort(group.owned_alternatives, function(a, b) return a.item_id < b.item_id end)
    local state = candidate and ((ownedState == "bag" or ownedState == "bank") and "owned_upgrade" or "missing_upgrade") or "not_upgrade"
    applyPlannerUpgradeMetadata(group, state, candidateUse, reference)
    group.upgrade_compared_empty = reference and reference.occupancy == "empty" or false
end

local function plannerGroupMatchesUpgradeMode(group, filters)
    local mode = filters and filters.upgradeMode or "candidates"
    if mode == "all" then return true end
    if mode == "higher_rated" then return group.higher_rated == true end
    return group.upgrade_candidate == true
end

function BigBiSList:GetEquipmentComparisonContexts(className, specName, targetPhase, ownedItems, slotName)
    local contexts = {}
    local equipped = ownedItems and ownedItems.equippedSlots or {}
    local physicalKey
    for _, definition in ipairs(EQUIPMENT_SLOTS) do
        if slotName == definition.key or slotName == definition.label then physicalKey = definition.key; break end
    end
    for _, definition in ipairs(EQUIPMENT_SLOTS) do
        local matches = not slotName or physicalKey == definition.key
        if not physicalKey then
            for _, accepted in ipairs(RECOMMENDATION.slots(slotName) or {}) do
                if slotListContains(definition.slots, accepted) then matches = true end
            end
        end
        if matches then
            local entry = equipped[definition.key]
            local itemId = entry and tonumber(entry.item_id)
            local item = itemId and self:GetItemData(itemId)
            local metadata = itemId and FILTER_FACETS.tableValueById(ownedItems and ownedItems.inventoryItems, itemId)
            local linkName = self.isForever and entry and entry.item_link and entry.item_link:match("|h%[(.-)%]|h")
            local blocked = not itemId and definition.key == "OffHand" and ownedItems and ownedItems.equippedTwoHand
            local unknown = not itemId and ownedItems and ownedItems.unreadableEquipmentSlots
                and ownedItems.unreadableEquipmentSlots[definition.key]
            local occupancy = itemId and "occupied" or (blocked and "blocked" or (unknown and "unknown" or "empty"))
            local use = itemId and self:GetItemBestUseForSpec(itemId, className, specName, targetPhase, definition.slots)
            local history = itemId and self.isForever and targetPhase ~= LEVELING_PHASE_KEY
                and self:GetRecommendationHistory(itemId, className, specName, targetPhase, definition.key)
            local variantKey = history and self.ForeverGearRating and self.ForeverGearRating:NormalizeLink(itemId, entry.item_link)
            contexts[#contexts + 1] = { slotKey = definition.key, slot = definition.label, dataSlots = definition.slots,
                inventorySlotId = entry and entry.slotId or definition.inventorySlotId, item_id = itemId,
                item_link = entry and entry.item_link, ownedSnapshot = self.isForever and ownedItems or nil,
                name = itemId and (linkName or (metadata and metadata.name) or getItemName(itemId, item))
                    or (blocked and "Two-handed weapon equipped"
                        or (unknown and (self.isForever and "Item data unavailable" or "Unknown") or "Empty " .. definition.label)),
                occupancy = occupancy, blocked_by = blocked and "MainHand" or nil,
                state = itemId and "equipped" or nil, use = use, bestUse = use, history = history,
                equipped_bis = self:IsConfirmedGearBiS(history, targetPhase, itemId, variantKey),
                rank_label = use and use.rank_label, rank_group = use and use.rank_group }
        end
    end
    return contexts
end

-- Inventory metadata is transient: it describes physical compatibility, never
-- an inferred recommendation or performance rating for the selected spec.
RECOMMENDATION.inventorySlots = {
    INVTYPE_HEAD = "Head", INVTYPE_NECK = "Neck", INVTYPE_SHOULDER = "Shoulder",
    INVTYPE_CLOAK = "Back", INVTYPE_CHEST = "Chest", INVTYPE_ROBE = "Chest",
    INVTYPE_WRIST = "Wrist", INVTYPE_HAND = "Hands", INVTYPE_WAIST = "Waist",
    INVTYPE_LEGS = "Legs", INVTYPE_FEET = "Feet", INVTYPE_FINGER = "Ring",
    INVTYPE_TRINKET = "Trinket", INVTYPE_WEAPONMAINHAND = "Main Hand",
    INVTYPE_WEAPONOFFHAND = "Off Hand", INVTYPE_SHIELD = "Off Hand",
    INVTYPE_HOLDABLE = "Off Hand", INVTYPE_2HWEAPON = "Two Hand",
    INVTYPE_WEAPON = "One Hand", INVTYPE_RANGED = "Ranged", INVTYPE_RANGEDRIGHT = "Ranged",
    INVTYPE_THROWN = "Ranged", INVTYPE_RELIC = "Relic", INVTYPE_AMMO = "Ammo",
    INVTYPE_QUIVER = "Quiver",
}

function RECOMMENDATION.ownedInventoryState(ownedItems, itemId, metadata)
    local state = FILTER_FACETS.tableValueById(ownedItems, itemId)
    if state and state ~= "missing" then return state == "bags" and "bag" or state end
    local locations = metadata and metadata.locations or {}
    return locations.equipped and "equipped" or locations.bags and "bag" or locations.bank and "bank" or nil
end

function RECOMMENDATION.inventoryFitsSlot(metadata, item, slotName, className)
    local inventorySlot = metadata and RECOMMENDATION.inventorySlots[metadata.equip_location]
        or (metadata and metadata.inventory_slot) or (item and item.inventory_slot)
    if not inventorySlot then return false end
    local slots = { inventorySlot }
    if inventorySlot == "One Hand" then
        slots = { "Main Hand" }
        if className == "Warrior" or className == "Rogue" or className == "Hunter" or className == "Shaman" then
            slots[#slots + 1] = "Off Hand"
        end
    elseif inventorySlot == "Relic" then
        slots = { "Relic", className == "Druid" and "Idol" or className == "Shaman" and "Totem" or className == "Paladin" and "Libram" or "Relic" }
    end
    for _, accepted in ipairs(RECOMMENDATION.slots(slotName) or {}) do
        if slotListContains(slots, accepted) then return true end
    end
    return false
end

function BigBiSList:GetSlotComparisonRows(className, specName, targetPhase, slotName, ownedItems, reference)
    local contexts = self:GetEquipmentComparisonContexts(className, specName, targetPhase, ownedItems, slotName)
    local requestedId = type(reference) == "table" and reference.item_id or tonumber(reference)
    local physicalReference
    if type(reference) == "table" and reference.slotKey then
        for _, context in ipairs(contexts) do if context.slotKey == reference.slotKey then physicalReference = context; break end end
    end
    local rows, seen = {}, {}
    rows.contexts, rows.target_phase, rows.slot = contexts, targetPhase, slotName
    local index = self:GetDataIndex(targetPhase)
    local selectedIndex = self:GetAvailabilityPhaseIndex(targetPhase)
    local inventory = ownedItems and ownedItems.inventoryItems or {}
    local function add(itemId, use, physical)
        if seen[itemId] then
            if physical then seen[itemId].owned_state = "equipped"; seen[itemId].owned = true end
            return
        end
        local item = self:GetItemData(itemId)
        local metadata = FILTER_FACETS.tableValueById(inventory, itemId)
        local ownedState = physical and "equipped" or RECOMMENDATION.ownedInventoryState(ownedItems, itemId, metadata)
        local row = { item_id = itemId, name = metadata and metadata.name or getItemName(itemId, item), item = item,
            item_link = metadata and metadata.item_link, slot = use and use.slot or slotName,
            class = className, spec = specName, phase = targetPhase, bestUse = use, owned = ownedState ~= nil,
            owned_state = ownedState, inventory_item = metadata, owned_locations = metadata and metadata.locations }
        row.history = self:GetRecommendationHistory(itemId, className, specName, targetPhase, use and use.slot or slotName)
        row.recommendation_history = row.history
        row.acquisition_display = self:GetRowAcquisitionDisplay(use or row, {}, targetPhase)
        rows[#rows + 1], seen[itemId] = row, row
    end
    local comparisonRefs = index.useRefsByClassSpec[className] and index.useRefsByClassSpec[className][specName]
    for _, ref in ipairs(comparisonRefs or {}) do
        local use = buildUse(index, ref)
        local matches = slotListContains(RECOMMENDATION.slots(slotName), use.slot)
        if matches and RECOMMENDATION.useFitsContext(self, use, targetPhase) and includeByFilter(use, FILTER_FACETS.progressionFilters({}, targetPhase), selectedIndex) then
            add(use.item_id, use)
        end
    end
    for _, context in ipairs(contexts) do if context.item_id then add(context.item_id, context.use, true) end end
    local ownedIds = {}
    for key, state in pairs(ownedItems or {}) do
        local itemId = tonumber(key)
        if itemId and state and state ~= "missing" then ownedIds[itemId] = true end
    end
    for key, metadata in pairs(inventory) do
        local itemId = tonumber(key)
        if itemId and RECOMMENDATION.ownedInventoryState(ownedItems, itemId, metadata) then ownedIds[itemId] = true end
    end
    for itemId in pairs(ownedIds) do
        if not seen[itemId] then
            local metadata, item = FILTER_FACETS.tableValueById(inventory, itemId), self:GetItemData(itemId)
            if RECOMMENDATION.inventoryFitsSlot(metadata, item, slotName, className) then
                add(itemId, self:GetItemBestUseForSpec(itemId, className, specName, targetPhase, RECOMMENDATION.slots(slotName)))
            end
        end
    end
    -- A reference chosen under another local role remains useful as a reference.
    -- It needs recorded, available evidence for this class and slot; a removed
    -- unranked inventory item cannot reappear merely because its ID was selected.
    if requestedId and not seen[requestedId] then
        for _, ref in ipairs(index.useRefsByItemId[requestedId] or {}) do
            local use = buildUse(index, ref)
            if use.class == className and slotListContains(RECOMMENDATION.slots(slotName), use.slot)
                and RECOMMENDATION.useFitsContext(self, use, targetPhase)
                and includeByFilter(use, FILTER_FACETS.progressionFilters({}, targetPhase), selectedIndex) then
                add(requestedId, nil)
                break
            end
        end
    end
    reference = physicalReference or (requestedId and seen[requestedId] and { item_id = requestedId, occupancy = "occupied" }) or contexts[1]
    rows.reference = reference
    for _, row in ipairs(rows) do
        row.is_reference = reference and row.item_id == reference.item_id or false
        row.comparison = self:CompareRecommendationItems(row.item_id, reference and reference.item_id, className, specName, targetPhase, row.slot, reference)
    end
    table.sort(rows, function(a, b)
        if lower(a.name) ~= lower(b.name) then return lower(a.name) < lower(b.name) end
        return a.item_id < b.item_id
    end)
    return rows
end

-- Alternative routes do not multiply targets or activity counts.
function BigBiSList:GetActivityGroup(row)
    local display = row and row.acquisition_display or {}
    local option = display.option or (row and row.matched_access_option) or {}
    if display.activity_zone then return display.activity_zone end
    local activities = display.activity_zones or option.activity_zones
    if activities and #activities > 0 then return table.concat(activities, " + ") end
    local kind = option.source_filter_key or option.source_type or (row and row.source_type) or "unknown"
    local matchedSource = display.source_match and display.source_match.source
    local zone = matchedSource and FILTER_FACETS.sourceLocationArea(matchedSource)
        or option.zone or (option.zones and option.zones[1])
    if type(zone) == "table" then zone = zone.name or zone.zone end
    if kind == "raid" or kind == "raid_drop" or kind == "dungeon" or kind == "dungeon_drop"
        or kind == "heroic_dungeon_drop" or kind == "drop" or kind == "quest" then
        return zone or display.source_label or "Other activities"
    end
    if self:IsGuideMarketRoute(option) then return "Auction House" end
    if option.is_trade_option then return "Trade / Auction House" end
    if option.reputations and #option.reputations > 0 then return "Reputation · " .. option.reputations[1] end
    for _, requirement in ipairs(option.requirements or {}) do
        if requirement.type == "profession" and requirement.profession then return "Crafting · " .. requirement.profession end
    end
    if option.vendor_label then return "Vendor · " .. option.vendor_label end
    return display.source_label or option.source_filter_label or "Other activities"
end

-- Keep the route that places each item in a dungeon, so opening Details uses that same source.
function BigBiSList:GetLevelingActivityRows(row, filters, level)
    if row.guide_source_unknown or row.future_phase then return {} end
    local result = {row}
    local seen = {[self:GetActivityGroup(row)] = true}
    local scoped = {}
    for key, value in pairs(filters or {}) do scoped[key] = value end
    scoped._leveling, scoped.level = true, row.guide_route_level or level
    local phase = self:GetAvailabilityPhaseIndex(LEVELING_PHASE_KEY)
    FILTER_FACETS.addMatchingOptionsFromRow(row, scoped, phase, function(option, match)
        if not FILTER_FACETS.optionIsVerifiedGuideRoute(option) then return end
        if not matchesGuideTarget(self, option, scoped) then return end
        if scoped._guideTarget and option.source_type == "trade"
            and row.matched_access_option and row.matched_access_option.source_type ~= "trade" then return end
        if scoped._questAvailable and not scoped._questAvailable(option) then return end
        local primary = row.acquisition_display
        if primary and primary.option == option and primary.source_match == match then return end
        local display = {option = option, source_match = match, activity_zone = match.activity_zone,
            activity_zones = match.activity_zones, source_label = option.source_filter_label or SOURCE_TYPE_LABELS[option.source_type]}
        local activity = self:GetActivityGroup({acquisition_display = display})
        if seen[activity] then return end
        seen[activity] = true
        local alternate = {}
        for field, value in pairs(row) do alternate[field] = value end
        alternate.access_options, alternate.matched_access_option = {option}, option
        local access = self:GetRowAcquisitionDisplay(alternate, scoped, LEVELING_PHASE_KEY, false, true)
        access.source_match, access.matched_dependency = match, match.dependency
        access.activity_zone, access.activity_zones = match.activity_zone, match.activity_zones
        alternate.acquisition_display = access
        result[#result + 1] = alternate
    end)
    return result
end

function BigBiSList:GetStatRankComparisonRows(className, specName, phase, level, owned, physical)
    local service = self.ForeverGearRating
    local scoring = service and service:GetContext(className, specName, phase, clampLevelingLevel(level), owned)
    if not scoring then return {} end
    local definition
    for _, slot in ipairs(EQUIPMENT_SLOTS) do
        if slot.key == physical then definition = slot; break end
    end
    if not definition then return {} end
    local contexts = self:GetEquipmentComparisonContexts(className, specName, phase, owned, definition.slots[1])
    local pool = service:GetPlacement(scoring, physical, definition.slots)
    local rows = { contexts = contexts, statsPending = scoring.pending, slot = pool.slot, swapBasis = "reference" }
    local leveling = phase == LEVELING_PHASE_KEY
    local guide = service:GetGuideContext(className, specName, phase, scoring.level, scoring.race, scoring.faction)
    local referencePool = service:GetGuidePlacement(guide, pool.slot)
    for _, context in ipairs(contexts) do
        local ranked = service:GetPlacement(scoring, context.slotKey, context.dataSlots)
        local entry = ranked.reference
        context.stat_rank = entry and entry.item and referencePool.byVariant[entry.item.key] or entry
        context.stat_rank_scope = referencePool.scope
        context.stat_identity = entry and entry.item and entry.item.key
        local linkName = context.item_link and context.item_link:match("|h%[(.-)%]|h")
        local exact = entry and entry.item
        context.name = linkName or (exact and exact.native and exact.name) or context.name
        if leveling and context.item_id then
            local use = self:GetItemBestLevelingUseForSpec(context.item_id, className, specName, scoring.level,
                context.dataSlots, scoring.race, context.item_link)
            if use then
                context.stat_guide_badge = "Recommended"
                context.guide_note = LEVELING_HELPERS.gearRecommendationText(use, specName)
            end
        elseif context.history then
            local history = context.history
            local cell = history.selected and history.selected.matched and history.selected or history.latest_earlier
            if cell then
                context.stat_guide_badge = RECOMMENDATION.gearBadge(cell, phase, context.equipped_bis)
                context.guide_note = RECOMMENDATION.gearNote(cell, RECOMMENDATION.gearSummary(cell))
            end
        end
        if context.slotKey == physical then rows.reference = context end
    end
    local filters = {
        class = className, level = scoring.level, _leveling = leveling, race = scoring.race,
        faction = self:GetPlayerFactionName(),
    }
    local checkpoint = service:GetWorkCheckpoint()
    for _, entry in ipairs(service:GetComparisonCandidates(pool)) do
        if checkpoint then checkpoint() end
        local facts = entry.item
        local item, ownership = self:GetItemData(facts.id), entry.ownership
        local link = ownership and ownership.item_link or facts.variant_link
        local use, badge, activeUse, guideNote
        if item then
            if leveling then
                use = self:GetItemBestLevelingUseForSpec(facts.id, className, specName, scoring.level, {pool.slot}, scoring.race, link)
                if use then
                    badge = "Recommended"
                    guideNote = LEVELING_HELPERS.gearRecommendationText(use, specName)
                end
            else
                local history = self:GetRecommendationHistory(facts.id, className, specName, phase, pool.slot)
                local selected = history.selected
                local cell = selected and selected.matched and selected or history.latest_earlier
                if selected and selected.matched then use = selected.use end
                if cell then
                    badge = RECOMMENDATION.gearBadge(cell, phase, self:IsConfirmedGearBiS(history, phase, facts.id, facts.key))
                    guideNote = RECOMMENDATION.gearNote(cell, RECOMMENDATION.gearSummary(cell))
                end
            end
        end
        if use and use.scoring_basis == "active_build" then activeUse = use end
        local data = {
            item_id = facts.id, item_link = link, name = link and link:match("|h%[(.-)%]|h") or facts.name, item = item,
            variant_id = facts.variant_id, stat_identity = facts.key, stat_rank = referencePool.byVariant[facts.key] or entry,
            stat_guide_badge = badge, stat_rank_scope = referencePool.scope, guide_source_unknown = entry.source_unknown,
            slot = pool.slot, class = className, spec = specName, phase = phase, leveling = leveling,
            level_min = scoring.level, bestUse = use, scoring_basis = activeUse and activeUse.scoring_basis,
            scoring_label = activeUse and activeUse.scoring_label, level_label = use and use.level_label,
            guide_note = guideNote, recommendation_summary = leveling and guideNote or nil,
            owned = ownership ~= nil, owned_state = ownership and ownership.state or "missing",
            is_reference = pool.reference and entry == pool.reference or false,
        }
        local display = item and self:GetRowAcquisitionDisplay(use or data, filters, phase)
        if not display or not display.option or display.option.source_type == "unknown" or display.status == "unknown" then
            display = { source_label = "Source unknown", location_label = "Source unknown" }
            data.source_summary = "Source unknown"
        end
        data.acquisition_display, data.matched_access_option = display, display.option
        if not data.is_reference then
            data.stat_swap = service:GetGuideSwap(scoring, facts, physical, pool.slot, link)
            if data.stat_swap and data.stat_swap.basis == "active" then rows.swapBasis = "active" end
        end
        rows[#rows + 1] = data
    end
    return rows
end

function LEVELING_HELPERS.swapContributionText(contributions)
    local stats, names = {}, { dps = "Weapon DPS", ranged_dps = "Ranged DPS", wand_dps = "Wand DPS",
        mp5 = "Mana per 5 sec", hp5 = "Health per 5 sec", proc_dps = "Damage procs" }
    for stat, points in pairs(contributions or {}) do
        if math.abs(points) >= 0.05 then stats[#stats + 1] = { stat = stat, points = points } end
    end
    table.sort(stats, function(a, b)
        local first, second = math.abs(a.points), math.abs(b.points)
        return first > second or (first == second and a.stat < b.stat)
    end)
    local labels, gains, losses = {}, 0, 0
    for _, stat in ipairs(stats) do
        if (stat.points > 0 and gains < 2) or (stat.points < 0 and losses < 2) then
            local name = names[stat.stat] or stat.stat:gsub("_percent$", " chance"):gsub("_", " "):gsub("%f[%a]%l", string.upper)
            labels[#labels + 1] = string.format("%+.1f %s", stat.points, name)
            if stat.points > 0 then gains = gains + 1 else losses = losses + 1 end
        end
        if gains == 2 and losses == 2 then break end
    end
    return #labels > 0 and ("Largest changes · " .. table.concat(labels, " · ")) or nil
end

function LEVELING_HELPERS.formatSwap(service, swap, points)
    if not swap or swap.delta == nil then return nil end
    local replaced = {}
    for _, item in ipairs(swap.replacements) do replaced[#replaced + 1] = item.name .. " (" .. item.slot .. ")" end
    local label = service:GetSwapBasisLabel(swap.basis)
    if swap.conditional then label = label .. " · Conditional" end
    local contributions = LEVELING_HELPERS.swapContributionText(points or swap.contributions)
    return label .. " · " .. service:EstimateSwapPoints(swap.delta)
        .. (#replaced > 0 and (" vs " .. table.concat(replaced, " + ")) or (" · " .. swap.definition.label))
        .. (contributions and ("\n" .. contributions) or "")
        .. (swap.effects and #swap.effects > 0 and ("\n" .. table.concat(swap.effects, ", ")) or "")
end

function BigBiSList:GetGuideStatComparison(row, owned, physical)
    local service, placement = self.ForeverGearRating, row.stat_rank
    if not service or not placement or not owned then return nil end
    local swap = row.stat_swap
    local contributions
    if (not swap or not swap.contributions) and not row.is_reference then
        local context = service:GetContext(row.class, row.spec, row.phase, placement.level, owned)
        local traced = service:GetGuideSwap(context, placement.item, physical, row.slot, row.item_link, true)
        if not swap then swap = traced
        elseif traced and traced.delta and swap.delta and traced.basis == swap.basis and math.abs(traced.delta - swap.delta) < 0.0001 then
            contributions = traced.contributions
        end
    end
    return LEVELING_HELPERS.formatSwap(service, swap, contributions)
end

function BigBiSList:GetEquippedGearRows(className, specName, phaseKey, ownedItems, level, identityOnly)
    local rows = {}
    local equippedSlots = ownedItems and ownedItems.equippedSlots or {}
    local selectedLevel = clampLevelingLevel(level)
    local levelingMode = phaseKey == LEVELING_PHASE_KEY
    local service = self.ForeverGearRating
    local checkpoint = not identityOnly and service and service:GetWorkCheckpoint()

    for _, slot in ipairs(EQUIPMENT_SLOTS) do
        if checkpoint then checkpoint() end
        local equipped = equippedSlots[slot.key]
        local itemId = equipped and equipped.item_id
        local item = itemId and self:GetItemData(itemId) or nil
        local metadata = itemId and FILTER_FACETS.tableValueById(ownedItems.inventoryItems, itemId)
        local unknown = not itemId and ownedItems and ownedItems.unreadableEquipmentSlots
            and ownedItems.unreadableEquipmentSlots[slot.key]
        local bestUse = not identityOnly and itemId and levelingMode
            and self:GetItemBestLevelingUseForSpec(itemId, className, specName, selectedLevel, slot.slots, nil, equipped.item_link)
            or nil
        local history = not identityOnly and itemId and not levelingMode
            and self:GetRecommendationHistory(itemId, className, specName, phaseKey, slot.key)
        local ratingCell = history and (history.selected and history.selected.matched and history.selected or history.latest_earlier)
        local historical = ratingCell and ratingCell.phase ~= phaseKey or false
        if not levelingMode then
            bestUse = ratingCell and ratingCell.use or nil
            if bestUse then
                local original = bestUse
                bestUse = {}
                for key, value in pairs(original) do bestUse[key] = value end
                bestUse.guide_phase, bestUse.phase = original.phase, ratingCell.phase
                bestUse.rank_label = ratingCell.label
                bestUse.rank_group = not historical and ratingCell.rank_group or "ranked"
                bestUse.display_rank_label = historical and ((PHASE_SHORT_DISPLAY[ratingCell.phase] or ratingCell.phase) .. " " .. ratingCell.label) or ratingCell.label
                bestUse.display_rank_kind = historical and "backup" or (ratingCell.rank_group == "bis" and "best" or "ranked")
                bestUse.recommendation_summary = (PHASE_DISPLAY[ratingCell.phase] or ratingCell.phase) .. ": " .. ratingCell.label
            end
        end
        local overlay = "Empty"
        local overlayKind = "empty"
        local disabledReason

        if itemId and bestUse and levelingMode then
            overlay = (bestUse.category_label and bestUse.category_label ~= "Recommended") and bestUse.category_label
                or (self.isForever and "Recommended" or "Leveling pick")
            overlayKind = "leveling"
        elseif itemId and bestUse then
            overlay = historical and "Earlier recommendation" or (bestUse.rank_group == "bis" and "Best in slot" or ratingCell.label)
            overlayKind = historical and "option" or bestUse.rank_group or "option"
        elseif itemId then
            overlay = "Not ranked"
            overlayKind = "missing"
        elseif slot.key == "OffHand" and ownedItems and ownedItems.equippedTwoHand then
            overlayKind = "disabled"
            disabledReason = "Two-handed weapon equipped"
            overlay = self.isForever and disabledReason or "2H equipped"
        elseif unknown then
            overlay = self.isForever and "Item data unavailable" or "Unknown"
            overlayKind = "unknown"
        end

        local displayRankLabel, displayRankKind = displayRankInfo(bestUse)
        local variantKey = history and service and service:NormalizeLink(itemId, equipped.item_link)
        local equippedBiS = self.isForever and self:IsConfirmedGearBiS(history, phaseKey, itemId, variantKey)
        local recommendation, guideNote, guideBadge = "Empty slot"
        if itemId and bestUse and levelingMode then
            recommendation = self.isForever and LEVELING_HELPERS.gearRecommendationText(bestUse, specName)
                or bestUse.level_label or bestUse.level_value_text or "Leveling recommendation"
            if self.isForever then guideBadge = "Recommended" end
        elseif itemId and bestUse then
            if self.isForever then
                guideBadge = RECOMMENDATION.gearBadge(ratingCell, phaseKey, equippedBiS)
                recommendation = RECOMMENDATION.gearSummary(ratingCell)
                guideNote = RECOMMENDATION.gearNote(ratingCell, recommendation)
            else
                recommendation = (PHASE_DISPLAY[ratingCell.phase] or ratingCell.phase) .. ": " .. ratingCell.label
            end
        elseif itemId then
            recommendation = "Not ranked"
        elseif disabledReason then
            recommendation = disabledReason
        elseif unknown then
            recommendation = overlay
        end

        table.insert(rows, {
            slotKey = slot.key,
            slot = slot.label,
            inventorySlotId = equipped and equipped.slotId or slot.inventorySlotId,
            item_id = itemId,
            item_link = equipped and equipped.item_link,
            item = item,
            name = metadata and metadata.name or (item and item.name)
                or (itemId and ("Item " .. tostring(itemId)) or overlay),
            source_summary = item and item.source_summary or "",
            bestUse = bestUse,
            recommendation_history = history,
            history = history,
            future_summary = history and history.future_summary,
            historical_only = historical,
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
            equipped_bis = equippedBiS,
            usesGearRating = service ~= nil,
            recommendation_summary = recommendation,
            guide_badge = guideBadge,
            guide_note = guideNote,
        })
    end

    return rows
end

function LEVELING_HELPERS.statGuideContext(addon, className, specName, phase, level, filters)
    local rating = addon.ForeverGearRating
    if not rating then return nil end
    return rating:GetGuideContext(className, specName, phase, level,
        filters.race or addon:GetPlayerRaceName(), filters.faction or addon:GetPlayerFactionName())
end

function LEVELING_HELPERS.attachPhasePlacements(addon, grouped, context)
    if not context then return end
    local rating = addon.ForeverGearRating
    for slot, group in pairs(grouped) do
        local pool = rating:GetGuidePlacement(context, slot)
        for _, row in ipairs(group.items) do
            local key = row.variant_id or tostring(row.item_id)
            row.stat_rank, row.stat_identity = pool.byVariant[key], key
            if row.stat_rank then row.item_link = row.item_link or row.stat_rank.item.variant_link end
            row.guide_bis = addon:IsConfirmedGearBiS(row.history, context.phase, row.item_id, key)
        end
    end
end

function BigBiSList:GetStatRankGuideChoices(context, pool, checkpoint)
    context.guideChoices = context.guideChoices or {}
    local slot = pool.slot
    local cached = context.guideChoices[slot]
    if cached then return cached end
    local rating, choices = self.ForeverGearRating, {}
    for _, entry in ipairs(pool.rows) do
        if checkpoint then checkpoint() end
        local effect = rating:GetReviewedGuideEffect(context, entry.item)
        local percent = entry.score_percent or (entry.rank == 1 and 100) or 0
        choices[entry.item.key] = { score = entry.score, effect = effect,
            recommended = effect or (entry.score and entry.score > 0 and percent >= 70),
            alternate = percent < 85 }
    end
    context.guideChoices[slot] = choices
    return choices
end

function LEVELING_HELPERS.guideCandidate(index, entry, context, preferred, choice)
    local item = entry.item
    local row = preferred
    if not row and entry.source_unknown then
        local indexed = getIndexedItem(index, item.id)
        local meta = indexed and getItemMetaFromIndex(index, item.id, indexed) or {}
        row = { class = context.class, spec = context.spec, phase = context.phase, slot = entry.slot,
            name = item.name, item_id = item.id, variant_id = item.variant_id, leveling = context.leveling,
            quality = item.quality or meta.quality, boe = meta.boe, rank_group = "option", guide_source_unknown = true,
            level_min = entry.level, level_max = entry.level, source_summary = "Source unknown",
            source_filter_label = "Source unknown", source_type = "unknown" }
    elseif not row then
        row = buildLevelingRecommendationRow(index, { class = context.class, spec = context.spec,
            item_id = item.id, slot = entry.slot, level_min = entry.level, level_max = entry.level,
            variant_id = item.variant_id, variant_name = item.name })
    end
    if not row then return nil end
    if not preferred then
        row.computed_recommendation, row.section = nil, nil
        row.level_label, row.level_value_text, row.display_rank_label, row.tooltip_level_label = nil, nil, nil, nil
        row.category_label, row.leveling_category_key, row.recommendation_summary = nil, nil, nil
    end
    row.stat_rank, row.stat_identity = entry, item.key
    row.future_phase = entry.future_phase
    row.item_link = row.item_link or item.variant_link
    row.guide_source_unknown = entry.source_unknown
    row.guide_note = choice.effect
    row.guide_alternate = choice.alternate
    return row
end

function LEVELING_HELPERS.buildGuideCandidates(addon, index, grouped, context, slots)
    local rating, groups = addon.ForeverGearRating, {}
    local checkpoint = rating:GetWorkCheckpoint()
    for _, slot in ipairs(slots or SLOT_ORDER) do
        local pool = rating:GetGuidePlacement(context, slot)
        local preferred, rows = {}, {}
        local choices = addon:GetStatRankGuideChoices(context, pool)
        for _, row in ipairs(grouped[slot] and grouped[slot].items or {}) do
            preferred[row.variant_id or tostring(row.item_id)] = row
        end
        for _, entry in ipairs(pool.rows) do
            if checkpoint then checkpoint() end
            local key = entry.item.key
            local choice = choices[key]
            local row = choice and LEVELING_HELPERS.guideCandidate(index, entry, context, preferred[key], choice)
            if row then
                row.stat_rank_scope = pool.scope
                rows[#rows + 1] = row
            end
        end
        for _, entry in ipairs(pool.upcoming) do
            local row = LEVELING_HELPERS.guideCandidate(index, entry, context, nil, {})
            if row then rows[#rows + 1] = row end
        end
        if #rows > 0 then groups[#groups + 1] = { slot = slot, items = rows } end
    end
    return groups
end

function LEVELING_HELPERS.filterGuideCandidates(addon, context, filters)
    local groups = {}
    local checkpoint = addon.ForeverGearRating:GetWorkCheckpoint()
    for _, slot in ipairs(SLOT_ORDER) do
        local rows = {}
        if rowMatchesSelectedSlots(slot, filters.slots) then
            local group = context.guideCandidates[slot]
            if group == nil then
                group = LEVELING_HELPERS.buildGuideCandidates(addon, context.guideIndex, context.preferredRows, context, {slot})[1] or false
                context.guideCandidates[slot] = group
            end
            for _, candidate in ipairs(group and group.items or {}) do
                if checkpoint then checkpoint() end
                if not (candidate.guide_source_unknown and (filters._verifiedOnly or hasActiveSourceContextFilter(filters)))
                    and includeByFilter(candidate, filters, candidate.future_phase and phaseIndex(candidate.future_phase) or context.phaseIndex) then
                    local access = addon:GetRowAcquisitionDisplay(candidate, filters, context.phase, candidate.future_phase ~= nil, true)
                    if (candidate.guide_source_unknown and not hasActiveSourceContextFilter(filters))
                        or ((access.status == "ready" or candidate.future_phase and access.future) and access.source_match) then
                        local row = {}
                        for key, value in pairs(candidate) do row[key] = value end
                        row.acquisition_display, row.matched_access_option = access, access.option
                        rows[#rows + 1] = row
                    end
                end
            end
        end
        if #rows > 0 then groups[#groups + 1] = { slot = slot, items = rows } end
    end
    table.sort(groups, function(a, b) return slotIndex(a.slot) < slotIndex(b.slot) end)
    return groups
end

function BigBiSList:GetLevelingGuideSummary(className, specName, level, filters, watcher)
    local context = self.isForever and LEVELING_HELPERS.statGuideContext(self, className, specName, LEVELING_PHASE_KEY, level, filters)
    if not context then return nil end
    local rating = self.ForeverGearRating
    local summary = rating:GetLevelingSummary(context)
    local slots = {}
    for _, slot in ipairs(rating:LevelingGuideSlots(context, SLOT_ORDER)) do
        if rowMatchesSelectedSlots(slot, filters and filters.slots) then slots[#slots + 1] = slot end
    end
    rating:RequestLevelingSummary(summary, slots, watcher)
    return summary
end

-- Match routes at the relevant level without narrowing the reference score pool.
function LEVELING_HELPERS.journeyAccess(addon, row, ranges, context, filters)
    local scoped = {}
    for key, value in pairs(filters) do scoped[key] = value end
    scoped.class, scoped.race, scoped.faction, scoped._leveling = context.class, context.race, context.faction, true
    scoped.level = ranges[1].firstLevel
    if row.guide_source_unknown and hasActiveSourceContextFilter(scoped) then return nil end
    if not includeByFilter(row, scoped, context.phaseIndex) then return nil end
    local function atLevel(level, order)
        scoped.level = level
        local access = addon:GetRowAcquisitionDisplay(row, scoped, context.phase, false, true)
        if row.guide_source_unknown or (access.status == "ready" and access.source_match) then return access, level, order end
    end
    for _, range in ipairs(ranges) do
        for level = math.max(range.firstLevel, context.level), range.lastLevel do
            local access, match, order = atLevel(level, level == context.level and 1 or 2)
            if access then return access, match, order end
        end
    end
    for i = #ranges, 1, -1 do
        local range = ranges[i]
        for level = math.min(range.lastLevel, context.level - 1), range.firstLevel, -1 do
            local access, match, order = atLevel(level, 3)
            if access then return access, match, order end
        end
    end
end

function BigBiSList:GetPackedGuideRow(context, slot, ordinal, filters, match, targetLevel)
    local rating = self.ForeverGearRating
    local checkpoint = rating:GetWorkCheckpoint()
    local record, entry, routeLevel, order, available = rating:PackedGuideRowInfo(context, slot, ordinal, targetLevel)
    if not record then return end
    if checkpoint then checkpoint() end
    if entry.source_unknown and (filters._verifiedOnly or hasActiveSourceContextFilter(filters)) then return end
    local index = self:GetDataIndex()
    local preferred
    if match and (LEVELING_HELPERS.isCategoryKey(filters.rankGroup) or tableHasAnyEnabled(filters.rankGroups)) then
        local schema = "leveling_recommendation"
        for _, ref in ipairs(index.levelingRecommendationRefsByItemId[entry.item.id] or {}) do
            local function value(field) return compactField(index, schema, ref, field) end
            if value("class") == context.class and value("spec") == context.spec and value("slot") == slot
                and raceMatches(value("race"), context.race) and value("faction") == context.faction
                and value("variant_id") == entry.item.variant_id
                and routeLevel >= (value("level_min") or 1) and routeLevel <= (value("level_max") or 59) then
                local row = buildLevelingRecommendationRow(index, ref)
                if row and (row.leveling_category_key == filters.rankGroup
                    or filters.rankGroups and filters.rankGroups[row.leveling_category_key]) then
                    preferred = row
                    break
                end
            end
        end
    end
    local row = LEVELING_HELPERS.guideCandidate(index, entry, context, preferred, {effect = record.note})
    if not row then return end
    if checkpoint then checkpoint() end
    local access
    local scoped = filters
    if routeLevel ~= context.level or filters.class ~= context.class then
        scoped = {}
        for key, value in pairs(filters) do scoped[key] = value end
        scoped.class, scoped.level, scoped.race, scoped.faction, scoped._leveling =
            context.class, routeLevel, context.race, context.faction, true
    end
    if match and not includeByFilter(row, scoped, context.phaseIndex) then return end
    if checkpoint then checkpoint() end
    if match and not targetLevel and not entry.source_unknown and hasActiveSourceContextFilter(scoped) then
        local ranges = record.recommended[1] and record.recommended or record.ranked
        local candidate, level, position = LEVELING_HELPERS.journeyAccess(self, row, ranges, context, filters)
        if not candidate then return end
        access, routeLevel, order = candidate, level, position == 1 and not record.recommended[1] and 4 or position
    else
        access = self:GetRowAcquisitionDisplay(row, scoped, context.phase, false, true)
    end
    if match and not entry.source_unknown and access.status ~= "ready" then return end
    row.acquisition_display, row.matched_access_option = access, access.option
    row.guide_order, row.guide_route_level, row.guide_available_now = order, routeLevel, available
    row.guide_levels = record.recommended
    row.guide_record = record
    return row
end

function BigBiSList:GetLevelingJourneyRows(className, specName, level, filters, summary, currentGroups)
    if not summary then return currentGroups end
    if summary.packed then
        local groups, context = {}, summary.context
        local rating = self.ForeverGearRating
        local checkpoint = rating:GetWorkCheckpoint()
        for _, slot in ipairs(SLOT_ORDER) do
            local data = rowMatchesSelectedSlots(slot, filters.slots) and summary.slots[slot]
            if data then
                local rows = {}
                rating:VisitPackedGuideOrdinals(data, level, filters.search, filters._verifiedOnly, function(ordinal)
                    local candidate = self:GetPackedGuideRow(context, slot, ordinal, filters, true)
                    if candidate then rows[#rows + 1] = candidate end
                end, checkpoint)
                if #rows > 0 then groups[#groups + 1] = {slot = slot, items = rows} end
            end
        end
        return groups
    end
    if not next(summary.slots) then return currentGroups end
    local index, rating = self:GetDataIndex(), self.ForeverGearRating
    local context = LEVELING_HELPERS.statGuideContext(self, className, specName, LEVELING_PHASE_KEY, level, filters)
    local groups, bySlot = {}, {}
    local checkpoint = rating:GetWorkCheckpoint()
    for _, group in ipairs(currentGroups) do
        if not group.slot then return currentGroups end
        bySlot[group.slot] = group.items
    end
    for _, slot in ipairs(SLOT_ORDER) do
        local slotSummary = summary.slots[slot]
        local rows = bySlot[slot] or {}
        if slotSummary and rowMatchesSelectedSlots(slot, filters.slots) then
            rows = {}
            local current = {}
            for _, row in ipairs(bySlot[slot] or {}) do
                if row.stat_identity then current[row.stat_identity] = row end
            end
            local pool = rating:GetGuidePlacement(context, slot)
            for key, later in pairs(slotSummary.upcoming or {}) do
                if not slotSummary.items[key] then
                    local row = current[key] or LEVELING_HELPERS.guideCandidate(index, later, context, nil, {})
                    local scoped = {}
                    for field, value in pairs(filters) do scoped[field] = value end
                    scoped.level = math.max(level, later.level)
                    if row and includeByFilter(row, scoped, phaseIndex(later.future_phase)) then
                        local access = self:GetRowAcquisitionDisplay(row, scoped, context.phase, true, true)
                        if access.future and access.source_match then
                            row.guide_order, row.guide_route_level = 2, scoped.level
                            row.acquisition_display, row.matched_access_option = access, access.option
                            rows[#rows + 1] = row
                        end
                    end
                end
            end
            for key, record in pairs(slotSummary.items) do
                if checkpoint then checkpoint() end
                local row, access, routeLevel, order
                local ranges = record.recommended[1] and record.recommended or record.ranked
                local useful = rating:LevelingRangeAt(ranges, level)
                if current[key] and useful and level >= useful.firstLevel and level <= useful.lastLevel then
                    row = {}
                    for field, value in pairs(current[key]) do row[field] = value end
                    access, routeLevel, order = row.acquisition_display, level, 1
                elseif ranges[1] then
                    local placement = rating:LevelingPlacementAt(record, level, pool.byVariant[key])
                    row = LEVELING_HELPERS.guideCandidate(index, placement, context, nil, { effect = record.note })
                    if row then access, routeLevel, order = LEVELING_HELPERS.journeyAccess(self, row, ranges, context, filters) end
                end
                if access then
                    row.acquisition_display, row.matched_access_option = access, access.option
                    row.guide_order, row.guide_route_level = (not record.recommended[1] and order == 1) and 4 or order, routeLevel
                    row.guide_available_now = current[key] ~= nil
                    if current[key] then row.acquisition_display, row.matched_access_option = current[key].acquisition_display, current[key].matched_access_option end
                    row.guide_levels = record.recommended
                    rows[#rows + 1] = row
                end
            end
            table.sort(rows, function(a, b)
                if a.guide_order ~= b.guide_order then return a.guide_order < b.guide_order end
                if a.guide_route_level ~= b.guide_route_level then
                    if a.guide_order == 3 then return a.guide_route_level > b.guide_route_level end
                    return a.guide_route_level < b.guide_route_level
                end
                local aRank, bRank = a.stat_rank.rank or math.huge, b.stat_rank.rank or math.huge
                if aRank ~= bRank then return aRank < bRank end
                if a.name ~= b.name then return a.name < b.name end
                return a.stat_identity < b.stat_identity
            end)
        end
        if #rows > 0 then groups[#groups + 1] = { slot = slot, items = rows } end
    end
    return groups
end

function BigBiSList:GetLevelingSourceGate(access)
    local option = access and access.option
    local match = access and access.source_match
    if not option or not match or not FILTER_FACETS.optionIsVerifiedGuideRoute(option) then return nil end
    local level
    for _, path in ipairs(FILTER_FACETS.optionSourcePaths(option)) do
        if path.source == match.source and path.dependency == match.dependency then
            local minimum = 1
            for _, source in ipairs(path.nodes) do
                local gate = source.eligibility and tonumber(source.eligibility.min_level)
                if not gate then minimum = nil; break end
                minimum = math.max(minimum, gate)
            end
            if minimum and (not level or minimum < level) then level = minimum end
        end
    end
    return level, option.source_type
end

function LEVELING_HELPERS.addPhaseGuideAlternatives(addon, index, grouped, context, filters)
    if context.phaseGuideIndex ~= index then
        context.phaseGuideCandidates = LEVELING_HELPERS.buildGuideCandidates(addon, index, {}, context)
        context.phaseGuideIndex = index
    end
    for _, group in ipairs(context.phaseGuideCandidates) do
        local target = grouped[group.slot] or { slot = group.slot, items = {} }
        local seen = {}
        for _, row in ipairs(target.items) do seen[row.variant_id or tostring(row.item_id)] = true end
        for _, reference in ipairs(group.items) do
            if not seen[reference.stat_identity] then
                local candidate = {}
                for key, value in pairs(reference) do candidate[key] = value end
                candidate.phase, candidate.leveling = context.phase, nil
                candidate.category, candidate.category_label, candidate.leveling_category_key = nil, nil, nil
                candidate.rank_group = "option"
                if includeByFilter(candidate, filters, context.phaseIndex) then
                    local display = addon:GetRowAcquisitionDisplay(candidate, filters, context.phase, false, true)
                    if (candidate.guide_source_unknown and not hasActiveSourceContextFilter(filters))
                        or (display.status == "ready" and display.source_match) then
                        local history = addon:GetRecommendationHistory(candidate.item_id, context.class, context.spec, context.phase, group.slot)
                        candidate.history, candidate.recommendation_history = history, history
                        candidate.acquisition_display, candidate.matched_access_option = display, display.option
                        candidate.scoring_label = "Reference ranking"
                        target.items[#target.items + 1] = candidate
                    end
                end
            end
        end
        if #target.items > 0 then grouped[group.slot] = target end
    end
end

function BigBiSList:GetPhaseRows(className, specName, phaseKey, filters)
    filters = FILTER_FACETS.progressionFilters(filters, phaseKey, className) or {}
    local index = self:GetDataIndex(phaseKey)
    local useRefs = index.useRefsByClassSpecPhase[className]
        and index.useRefsByClassSpecPhase[className][specName]
        and index.useRefsByClassSpecPhase[className][specName][phaseKey]
    local grouped = {}
    local seenBySlot = {}
    local selectedItems = {}
    local selectedIndex = self:GetAvailabilityPhaseIndex(phaseKey)
    local statGuide = self.isForever and LEVELING_HELPERS.statGuideContext(self, className, specName, phaseKey, 60, filters)

    for _, ref in ipairs(useRefs or {}) do
        local use = buildUse(index, ref)
        local slotName = use.slot
        grouped[slotName] = grouped[slotName] or { slot = slotName, items = {} }
        seenBySlot[slotName] = seenBySlot[slotName] or {}
        selectedItems[slotName] = selectedItems[slotName] or {}
        local history = self:GetRecommendationHistory(use.item_id, className, specName, phaseKey, slotName)
        local matchesPhase = false
        for _, fact in ipairs(RECOMMENDATION.facts(use)) do if fact.phase == phaseKey then matchesPhase = true end end
        if matchesPhase then selectedItems[slotName][use.item_id] = true end
        local key = tostring(use.item_id) .. ":" .. tostring(use.rank_group) .. ":" .. tostring(use.context)
        if matchesPhase and use.acquisitionPhaseIndex <= selectedIndex and not seenBySlot[slotName][key] and includeByFilter(use, filters, selectedIndex) then
            use.recommendation_history, use.history, use.future_summary = history, history, history.future_summary
            use.recommendation_phase = phaseKey
            use.acquisition_display = self:GetRowAcquisitionDisplay(use, filters, phaseKey)
            use.matched_access_option = use.acquisition_display.option
            seenBySlot[slotName][key] = true
            table.insert(grouped[slotName].items, use)
        end
    end

    if filters.includeEarlier and phaseKey ~= "PR" then
        local seen = {}
        for _, ref in ipairs(index.useRefsByClassSpec[className] and index.useRefsByClassSpec[className][specName] or {}) do
            local candidate = buildUse(index, ref)
            local slotName, itemId = candidate.slot, candidate.item_id
            local itemKey = tostring(itemId) .. "\031" .. slotName
            if not seen[itemKey] and not (selectedItems[slotName] and selectedItems[slotName][itemId]) then
                seen[itemKey] = true
                local history = self:GetRecommendationHistory(itemId, className, specName, phaseKey, slotName)
                local cell = history.latest_earlier
                if cell and cell.use then
                    local use = {}
                    for key, value in pairs(cell.use) do use[key] = value end
                    if includeByFilter(use, filters, selectedIndex) then
                        use.earlier_recommendation, use.historical_only, use.recommendation_phase = true, true, cell.phase
                        use.recommendation_history, use.history, use.future_summary = history, history, history.future_summary
                        use.acquisition_display = self:GetRowAcquisitionDisplay(use, filters, phaseKey)
                        use.matched_access_option = use.acquisition_display.option
                        grouped[slotName] = grouped[slotName] or { slot = slotName, items = {} }
                        grouped[slotName].items[#grouped[slotName].items + 1] = use
                    end
                end
            end
        end
    end

    LEVELING_HELPERS.attachPhasePlacements(self, grouped, statGuide)
    if statGuide and phaseKey == "PR" then
        LEVELING_HELPERS.addPhaseGuideAlternatives(self, index, grouped, statGuide, filters)
    end

    local function sortPhaseRows(a, b)
        if (a.earlier_recommendation == true) ~= (b.earlier_recommendation == true) then return not a.earlier_recommendation end
        if a.earlier_recommendation then
            if a.recommendation_phase ~= b.recommendation_phase then return phaseIndex(a.recommendation_phase) > phaseIndex(b.recommendation_phase) end
            if lower(a.name) ~= lower(b.name) then return lower(a.name) < lower(b.name) end
            return a.item_id < b.item_id
        end
        if statGuide then
            local aRank = a.stat_rank and a.stat_rank.rank or math.huge
            local bRank = b.stat_rank and b.stat_rank.rank or math.huge
            if aRank ~= bRank then return aRank < bRank end
        end
        return sortUses(a, b)
    end

    local rows = {}
    for _, slotName in ipairs(SLOT_ORDER) do
        if grouped[slotName] and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, sortPhaseRows)
            table.insert(rows, grouped[slotName])
        end
    end

    for _, slotName in ipairs(sortedKeys(grouped)) do
        if slotIndex(slotName) == 999 and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, sortPhaseRows)
            table.insert(rows, grouped[slotName])
        end
    end

    return rows
end

function BigBiSList:GetLevelingSlotStatus(className, specName, level, slot, context)
    local function status(state, reason, nextLevel)
        return { state = state, reason = reason, next_verified_level = nextLevel }
    end
    if not self.isForever then return status("not_applicable", "Availability review applies to Forever leveling.") end
    level = tonumber(level)
    if not level or level ~= math.floor(level) then return status("unreviewed", "Choose a valid character level.") end
    if level < 1 or level > 59 then return status("not_applicable", "Leveling recommendations cover levels 1-59.") end
    local data = BigBiSListData or {}
    local rules = data.leveling_availability_rules or {}
    local policy = (rules.spec_policies or {})[tostring(className) .. "/" .. tostring(specName)]
    if not policy then return status("unreviewed", "This character's equipment eligibility is not reviewed.") end
    context = context or {}
    local faction = context.faction
    if faction == nil then faction = self:GetPlayerFactionName() end
    local raceName = context.race or (not context.race_id and self:GetPlayerRaceName())
    local persona
    for _, candidate in ipairs(rules.races or {}) do
        if candidate.faction == faction and (not context.race_id or candidate.id == context.race_id)
            and (not raceName or candidate.name == raceName) then
            for _, allowedClass in ipairs(candidate.classes or {}) do
                if allowedClass == className then persona = candidate; break end
            end
        end
    end
    if not persona then return status("unreviewed", "This character's race and faction eligibility is not reviewed.") end
    local applicable = false
    for _, allowedSlot in ipairs(rules.common_slots or {}) do if allowedSlot == slot then applicable = true end end
    for _, allowedSlot in ipairs(policy.slots or {}) do if allowedSlot == slot then applicable = true end end
    if not applicable then return status("not_applicable", "This slot is not used by the selected specialization.") end
    local minimum = (policy.slot_min_levels or {})[slot] or 1
    local maximum = (policy.slot_max_levels or {})[slot] or 59
    if level < minimum or level > maximum then return status("not_applicable", "This equipment configuration is not available at this level.") end
    local index = self:GetDataIndex()
    local refs = (index.levelingRecommendationRefsByClassSpec[className] or {})[specName] or {}
    local recommended, nextLevel = false, nil
    for _, ref in ipairs(refs) do
        if compactField(index, "leveling_recommendation", ref, "slot") == slot
            and compactField(index, "leveling_recommendation", ref, "faction") == faction
            and compactField(index, "leveling_recommendation", ref, "race_id") == persona.id then
            local lo = compactField(index, "leveling_recommendation", ref, "level_min")
            local hi = compactField(index, "leveling_recommendation", ref, "level_max")
            if lo and hi and lo <= level and level <= hi then recommended = true end
            if lo and lo > level and (not nextLevel or lo < nextLevel) then nextLevel = lo end
        end
    end
    local explanation
    for _, ref in ipairs(data.leveling_availability or {}) do
        if compactField(index, "leveling_availability", ref, "class") == className
            and compactField(index, "leveling_availability", ref, "spec") == specName
            and compactField(index, "leveling_availability", ref, "faction") == faction
            and compactField(index, "leveling_availability", ref, "race_id") == persona.id
            and compactField(index, "leveling_availability", ref, "slot") == slot then
            local lo = compactField(index, "leveling_availability", ref, "level_min")
            local hi = compactField(index, "leveling_availability", ref, "level_max")
            if lo and hi and lo <= level and level <= hi then
                if explanation then return status("unreviewed", "Gear availability has conflicting reviews.") end
                if compactField(index, "leveling_availability", ref, "state") == "no_useful_item" then
                    explanation = compactField(index, "leveling_availability", ref, "reason")
                end
            end
        end
    end
    if recommended and explanation then return status("unreviewed", "Gear availability has conflicting reviews.") end
    if recommended then return status("recommended", "Reviewed gear recommendations are available.", nextLevel) end
    if explanation then return status("no_useful_item", explanation, nextLevel) end
    return status("unreviewed", "Gear availability at this level is still under review.", nextLevel)
end

function BigBiSList:GetLevelingRows(className, specName, level, filters)
    if BigBiSList.isForever then
        local copy = {}
        for key, value in pairs(filters or {}) do copy[key] = value end
        copy.faction = copy.faction or self:GetPlayerFactionName()
        copy.race = copy.race or self:GetPlayerRaceName()
        copy.class, copy.level, copy._leveling = className, level, true
        filters = copy
    end
    local index = self:GetDataIndex()
    local selectedLevel = clampLevelingLevel(tonumber(level) or (filters and tonumber(filters.level)))
    local guide = self.isForever and LEVELING_HELPERS.statGuideContext(self, className, specName, LEVELING_PHASE_KEY, selectedLevel, filters)
    local displayFilters = filters
    if guide then
        displayFilters.level = selectedLevel
        if guide.guideIndex == index and guide.guideCandidates then
            return LEVELING_HELPERS.filterGuideCandidates(self, guide, displayFilters)
        end
        filters = { class = className, level = selectedLevel, race = guide.race, faction = guide.faction, _leveling = true }
    end
    local availabilityIndex = self:GetAvailabilityPhaseIndex(LEVELING_PHASE_KEY)
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

    -- The Forever catalog can carry thousands of reviewed ranges per spec.
    -- Reject other races and levels before loading row metadata and sources.
    local function matchesGuideContext(schema, ref, exactRace)
        if not guide then return true end
        local race = compactField(index, schema, ref, "race")
        if (exactRace and race ~= selectedRace) or not raceMatches(race, selectedRace) then return false end
        local first = tonumber(compactField(index, schema, ref, "level_min")) or 1
        local last = tonumber(compactField(index, schema, ref, "level_max")) or first
        return first <= selectedLevel and selectedLevel <= last
    end

    if selectedRace and selectedRace ~= "" then
        for _, recommendationRef in ipairs(recommendationRefs) do
            local row = matchesGuideContext("leveling_recommendation", recommendationRef, true)
                and buildLevelingRecommendationRow(index, recommendationRef)
            if row
                and row.race == selectedRace
                and LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
                and includeByFilter(row, filters, availabilityIndex) then
                local groupKey = levelingRecommendationGroupKey(row)
                if groupKey then
                    raceOverrideGroups[groupKey] = true
                end
            end
        end
    end

    for _, recommendationRef in ipairs(recommendationRefs) do
        local row = matchesGuideContext("leveling_recommendation", recommendationRef)
            and buildLevelingRecommendationRow(index, recommendationRef)
        local includeRecommendation = row
            and raceMatches(row.race, selectedRace)
            and LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
            and includeByFilter(row, filters, availabilityIndex)

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
        local row = matchesGuideContext("leveling_gear", levelingRef)
            and buildLevelingGearRow(index, levelingRef)
        if row and LEVELING_HELPERS.isAvailableAt(row, selectedLevel)
            and includeByFilter(row, filters, availabilityIndex) then
            row.acquisition_display = self:GetRowAcquisitionDisplay(row, filters, LEVELING_PHASE_KEY)
            row.matched_access_option = row.acquisition_display.option
            LEVELING_HELPERS.addDisplayRow(grouped, seenBySlot, row, selectedRace, selectedLevel)
        end
    end

    if guide then
        guide.guideCandidates, guide.preferredRows, guide.guideIndex = {}, grouped, index
        return LEVELING_HELPERS.filterGuideCandidates(self, guide, displayFilters)
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

function LEVELING_HELPERS.applyForeverPlannerComparison(rating, context, row, item)
    if not item then return end
    local held = context.ownedFacts[item.key]
    local swap = held and rating:GetHeldComparison(context, held)
        or rating:GetOwnedOpportunity(context, item, row.item_link or item.variant_link, true)
    row.class, row.spec = context.class, context.spec
    row.planner_swap, row.owned_state = swap, held and held.state or "missing"
    local upgrade = swap ~= nil and (swap.equipSwap ~= nil or rating:ReliableGain(swap) ~= nil)
    row.upgrade_candidate, row.higher_rated = upgrade, upgrade
    return upgrade
end

function LEVELING_HELPERS.addReferencePlannerUpgrades(addon, rows, index, context, filters)
    if not context then return end
    local rating = addon.ForeverGearRating
    local className, specName, phase = context.class, context.spec, context.phase
    local guide = LEVELING_HELPERS.statGuideContext(addon, className, specName, phase, 60, filters)
    if not guide then return end
    local seen = {}
    for _, row in ipairs(rows) do seen[row.slot .. ":" .. (row.variant_id or tostring(row.item_id))] = row end
    for _, slot in ipairs(SLOT_ORDER) do
        for _, placement in ipairs(rating:GetGuidePlacement(guide, slot).rows) do
            local item = placement.item
            local key = slot .. ":" .. item.key
            local held = context.ownedFacts[item.key]
            local row = seen[key] or ((held or not placement.source_unknown) and buildLevelingRecommendationRow(index, {
                class = className, spec = specName, item_id = item.id, slot = slot,
                level_min = 60, level_max = 60, variant_id = item.variant_id, variant_name = item.name,
            }))
            if row then
                if not seen[key] then
                    row.phase, row.leveling, row.computed_recommendation = phase, nil, nil
                    row.category_label, row.level_label, row.leveling_category_key = nil, nil, nil
                    row.rank_group = "option"
                end
                local access = addon:GetRowAcquisitionDisplay(row, filters, phase, false, true)
                if (held or access.option) and includeByFilter(row, filters, guide.phaseIndex)
                    and (row.upgrade_candidate or LEVELING_HELPERS.applyForeverPlannerComparison(rating, context, row, item)) then
                    row.reference_upgrade, row.hasCurrent = true, true
                    row.stat_rank, row.stat_identity = placement, item.key
                    if not seen[key] then
                        row.acquisition_display, row.matched_access_option = access, access.option
                        row.display_rank_label, row.rank_label = rating:Label(placement, "compact"), "Reference ranking"
                        row.display_rank_kind, row.priority = "alternative", 0
                        rows[#rows + 1], seen[key] = row, row
                    end
                end
            end
        end
    end
end

function BigBiSList:GetPlannerRows(className, specName, selectedPhaseKey, filters)
    filters = FILTER_FACETS.progressionFilters(filters, selectedPhaseKey, className) or {}
    local index = self:GetDataIndex(selectedPhaseKey)
    local groups = {}
    local selectedIndex = self:GetAvailabilityPhaseIndex(selectedPhaseKey)
    local upgradeBaselines = not self.isForever and buildUpgradeBaselines(self, className, specName, selectedPhaseKey, filters.ownedItems)
    local rating = self.isForever and self.ForeverGearRating
    local personal
    if rating and filters.ownedItems and selectedPhaseKey == "PR" and self:DetectPlayerClass() == className then
        local ok, level = pcall(UnitLevel, "player")
        if ok and self.IsReadableValue(level) and level == 60 then
            personal = rating:GetContext(className, specName, selectedPhaseKey, level, filters.ownedItems)
        end
    end
    local useRefs = index.useRefsByClassSpec[className]
        and index.useRefsByClassSpec[className][specName]
        or {}

    for _, ref in ipairs(useRefs) do
        local use = buildUse(index, ref)
        if RECOMMENDATION.useFitsContext(self, use, selectedPhaseKey) then
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

    local rows = {statsPending = personal and personal.pending}
    for _, group in pairs(groups) do
        table.sort(group.uses, function(a, b)
            if a.phaseIndex ~= b.phaseIndex then
                return a.phaseIndex < b.phaseIndex
            end
            return sortUses(a, b)
        end)

        local history = self:GetRecommendationHistory(group.item_id, className, specName, selectedPhaseKey, group.slot)
        group.recommendation_history, group.history, group.future_summary = history, history, history.future_summary
        group.bestUse = group.bestUse.scoring_basis and group.bestUse or history.best_use or group.bestUse
        group.scoring_label = group.bestUse.scoring_label
        group.historical_only = not (history.selected and history.selected.matched) and not history.future_summary.has_future and history.latest_earlier ~= nil
        group.earlier_recommendation = group.historical_only
        group.recommendation_phase = history.selected and history.selected.matched and selectedPhaseKey or history.latest_earlier and history.latest_earlier.phase
        scorePlannerGroup(group, selectedPhaseKey)
        local ratingCell = history.selected and history.selected.matched and history.selected or history.latest_earlier
        group.rank_group = group.bestUse.scoring_basis and group.bestUse.rank_group or ratingCell and ratingCell.rank_group or "option"
        group.rank_label = group.bestUse and group.bestUse.rank_label or "Option"
        group.display_rank_label = group.priorityTier or "Priority"
        group.display_rank_kind = group.recommendation_tier or "only_if_easy"
        group.sides = group.bestUse and group.bestUse.sides or group.sides
        group.reputations = group.bestUse and group.bestUse.reputations or group.reputations
        group.requirements = group.bestUse and group.bestUse.requirements or group.requirements

        if upgradeBaselines then
            annotatePlannerUpgradeGroup(group, filters, upgradeBaselines, selectedPhaseKey)
        elseif personal then
            LEVELING_HELPERS.applyForeverPlannerComparison(rating, personal, group, rating:GetRowItem(group))
        end

        local eligibleHistory = group.historical_only and filters.includeEarlier ~= false
        local matchesMode = (self.isForever and not personal) or plannerGroupMatchesUpgradeMode(group, filters)
        if (group.priority > 0 or eligibleHistory) and group.acquisitionPhaseIndex <= selectedIndex and includeByFilter(group, filters, selectedIndex) and matchesMode then
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

    LEVELING_HELPERS.addReferencePlannerUpgrades(self, rows, index, personal, filters)
    table.sort(rows, function(a, b)
        if a.reference_upgrade ~= b.reference_upgrade then
            return a.reference_upgrade == true
        end
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

function FILTER_FACETS.addSourceTypeFromOption(sourceTypes, seen, option, selectedPhaseIndex, match)
    if FILTER_FACETS.optionIsReportedOnly(option)
        or not accessOptionIsPhaseAvailable(option, selectedPhaseIndex) then
        return
    end

    addUnique(sourceTypes, seen, match and match.source_filter_key or option.source_filter_key or option.source_type)
end

function FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, callback)
    if type(row) ~= "table" then
        return false, false
    end

    local options = buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}
    local matched = false
    for _, option in ipairs(options) do
        if matchesGuideTarget(BigBiSList, option, filters)
            and (not filters or not filters._questAvailable or filters._questAvailable(option)) then
            for _, match in ipairs(FILTER_FACETS.accessOptionFilterMatches(option, filters, selectedPhaseIndex)) do
                callback(option, match)
                matched = true
            end
        end
    end
    return matched, #options > 0
end

function FILTER_FACETS.rowHasCompleteOptionForSourceType(row, sourceType, selectedPhaseIndex)
    for _, option in ipairs(buildRowAccessOptions(BigBiSList:GetDataIndex(), row) or {}) do
        if not FILTER_FACETS.optionIsReportedOnly(option)
            and accessOptionIsPhaseAvailable(option, selectedPhaseIndex)
            and optionMatchesSourceContext(option, {sourceType = sourceType}, selectedPhaseIndex) then
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
        local matched, hasOptions = FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, function(option, match)
            if filters._guideTarget and match.source_filter_key == "trade" then
                addUnique(sourceTypes, seen, option.source_type)
            else
                FILTER_FACETS.addSourceTypeFromOption(sourceTypes, seen, option, selectedPhaseIndex, match)
                if filters._guideTarget and option.source_type == "token_turnin" then addUnique(sourceTypes, seen, option.source_type) end
            end
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
        local matched, hasOptions = FILTER_FACETS.addMatchingOptionsFromRow(row, filters, selectedPhaseIndex, function(option, match)
            if match then
                for _, zone in ipairs(match.zones) do addSourceZone(zones, seen, zone, selectedPhaseIndex) end
            else addZonesFromOption(zones, seen, option, selectedPhaseIndex) end
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
        local level = clampLevelingLevel(filters and filters.level)
        local summary = addon.isForever and tabName == "Gear Guide"
            and addon:GetLevelingGuideSummary(className, specName, level, filters or {})
        local groups
        if summary and summary.packed then
            filters._verifiedOnly = true
            groups = addon:GetLevelingJourneyRows(className, specName, level, filters, summary, {})
        else
            groups = addon:GetLevelingRows(className, specName, level, filters)
            if summary then groups = addon:GetLevelingJourneyRows(className, specName, level, filters, summary, groups) end
        end
        for _, group in ipairs(groups) do
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

function BigBiSList:GetFilterAvailabilitySnapshot(className, specName, phaseKey, tabName, filters, visitTargets)
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
    local baseFilters = cloneFiltersForAvailabilityRows(filters)
    local rows = not visitTargets and collectAvailabilityRows(self, className, specName, phaseKey, tabName, baseFilters) or {}

    local function collectFacets(row, level)
        if level then
            sourceScopedFilters.level, zoneScopedFilters.level, costScopedFilters.level = level, level, level
            vendorScopedFilters.level, reputationScopedFilters.level = level, level
        end
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
    if visitTargets then visitTargets(baseFilters, collectFacets) end
    local checkpoint = self.ForeverGearRating and self.ForeverGearRating:GetWorkCheckpoint()
    for _, row in ipairs(rows) do
        if checkpoint then checkpoint() end
        local ranges = row.guide_levels
        if ranges then
            local levels = {}
            for _, range in ipairs(ranges) do levels[range.firstLevel] = true end
            -- A route can first match when its last prerequisite becomes available.
            for _, option in ipairs(self:GetRowAccessOptions(row)) do
                if FILTER_FACETS.optionIsVerifiedGuideRoute(option) then
                    for _, path in ipairs(FILTER_FACETS.optionSourcePaths(option)) do
                        for _, source in ipairs(path.nodes) do
                            local minimum = source.eligibility and source.eligibility.min_level
                            if minimum then
                                for _, range in ipairs(ranges) do
                                    if minimum >= range.firstLevel and minimum <= range.lastLevel then
                                        levels[minimum] = true
                                    end
                                end
                            end
                        end
                    end
                end
            end
            for level in pairs(levels) do collectFacets(row, level) end
        else
            collectFacets(row, filters and filters.level)
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
    local ownedState = FILTER_FACETS.rowOwnedState(filters and filters.ownedItems, row)
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
    filters = FILTER_FACETS.progressionFilters(filters, phaseKey, className) or {}
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
    if group and group.recommendation_history then
        for _, cell in ipairs(group.recommendation_history.phase_cells) do
            if cell.matched then parts[#parts + 1] = (PHASE_SHORT_DISPLAY[cell.phase] or cell.phase_label) .. " " .. cell.label end
        end
    else
        for _, segment in ipairs(FILTER_FACETS.buildTooltipPhaseSegments(group)) do
            table.insert(parts, FILTER_FACETS.tooltipPhaseRangeSummary(segment))
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

function BigBiSList:GetLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext, itemLink)
    local selectedLevel = clampLevelingLevel(level)
    local matches = {}
    local seenMatches = {}
    local playerClass = type(priorityContext) == "table" and priorityContext.playerClass or nil
    local playerSpec = type(priorityContext) == "table" and priorityContext.playerSpec or nil
    selectedSpecFirst = selectedSpecFirst ~= false
    for _, use in ipairs(self:GetItemLevelingUses(itemId)) do
        if LEVELING_HELPERS.isAvailableAt(use, selectedLevel) and FILTER_FACETS.tooltipSpecEnabled(specFilters, use.class, use.spec)
            and (not self.isForever or not use.variant_id or use.variant_id == self:GetItemVariantIdFromLink(itemLink)) then
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
            and (use.phase ~= "PR" or includeByFilter(use, FILTER_FACETS.progressionFilters({}, "PR", use.class),
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

function BigBiSList:GetGroupedLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext, expanded, itemLink)
    local rawMatches = self:GetLevelingTooltipMatches(itemId, selectedClass, selectedSpec, level, selectedSpecFirst, specFilters, priorityContext, itemLink)
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
        if self.ForeverScoring then group.scoring_label = group.uses[1].scoring_label end
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
        local historyItem = group.uses[1] and group.uses[1].item_id or itemId
        group.recommendation_history = self:GetRecommendationHistory(historyItem, group.class, group.spec,
            type(priorityContext) == "table" and priorityContext.selectedPhase or self:GetCurrentPhaseKey(),
            #group.slots == 1 and group.slots[1] or nil)
        group.future_summary = group.recommendation_history.future_summary
        group.phase_summary = FILTER_FACETS.buildTooltipGroupSummary(group, expanded)
        if self.ForeverScoring then group.scoring_label = group.uses[1].scoring_label end
        group.slot_seen = nil
    end

    return groupedMatches
end
