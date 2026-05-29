local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local UI = {}
BigBiSList.UI = UI

local TAB_NAMES = { "Upgrades", "By Slot", "Equipped", "Enhance", "Wishlist", "Settings" }
local TAB_NAME_ALIASES = {
    Phase = "By Slot",
    Gear = "Equipped",
    Planner = "Upgrades",
    Enhancements = "Enhance",
}
local TAB_DISPLAY_LABELS = {
    Enhance = "Enhancements",
}
local MIN_WIDTH = 1020
local MIN_HEIGHT = 560
local DEFAULT_WIDTH = 1160
local DEFAULT_HEIGHT = 660
local LEFT_RAIL_WIDTH = 220
local LEFT_RAIL_INSET = 18
local LEFT_CONTROL_WIDTH = 184
local LEFT_DROPDOWN_WIDTH = 160
local LEFT_DROPDOWN_X = LEFT_RAIL_INSET - 16
local LEFT_SLOT_BUTTON_WIDTH = 88
local LEFT_SLOT_GAP = 8
local LEFT_SLOT_ROW_HEIGHT = 24
local DETAILS_WIDTH = 270
local ROW_HEIGHT = 58
local GEAR_ROW_HEIGHT = 50
local RESIZE_SCREEN_MARGIN = 0
local COLUMN_HEADER_HEIGHT = 22
local COLUMN_GAP = 8
local RANK_COLUMN_WIDTH = 96
local HAVE_COLUMN_WIDTH = 96
local GET_COLUMN_WIDTH = 122
local WHY_COLUMN_MIN_WIDTH = 112
local WHY_COLUMN_MAX_WIDTH = 150
local WHY_COLUMN_THRESHOLD = 590
local ROW_HORIZONTAL_PADDING = 8
local ROW_VERTICAL_PADDING = 8
local ROW_ICON_SIZE = 30

local OWNERSHIP_LABELS = {
    equipped = "Equipped",
    bag = "Bags",
    bank = "Bank",
    service = "No item",
    missing = "Missing",
}

local OWNERSHIP_COLORS = {
    equipped = { 0.16, 0.38, 0.18, 0.96, 0.46, 0.95, 0.48, 1 },
    bag = { 0.11, 0.23, 0.38, 0.96, 0.45, 0.68, 0.98, 1 },
    bank = { 0.28, 0.21, 0.10, 0.96, 0.96, 0.72, 0.34, 1 },
    service = { 0.23, 0.18, 0.36, 0.96, 0.74, 0.60, 0.98, 1 },
    missing = { 0.22, 0.12, 0.12, 0.96, 0.92, 0.48, 0.48, 1 },
}

local ACCESS_LABELS = {
    ready = "Farmable",
    ready_alternate = "Farmable through alternate source",
    needs_rep = "Need rep",
    needs_profession = "Need prof",
    needs_recipe = "Need recipe",
    check_prereq = "Check reqs",
    unknown = "Unknown",
}

local ACCESS_BADGE_LABELS = {
    ready = "Farmable",
    ready_alternate = "Farmable",
    needs_rep = "Need rep",
    needs_profession = "Need prof",
    needs_recipe = "Need recipe",
    check_prereq = "Check reqs",
    unknown = "Unknown",
}

local ACCESS_DETAIL_LABELS = {
    ready = "Farmable",
    ready_alternate = "Farmable through alternate source",
    needs_rep = "Rep gated",
    needs_profession = "Profession gated",
    needs_recipe = "Recipe gated",
    check_prereq = "Check requirements",
    unknown = "Unknown",
}

local ACCESS_SOURCE_BADGE_LABELS = {
    crafted = "Craft",
    quest = "Quest",
    vendor = "Vendor",
    trade = "Trade/AH",
    pvp = "PvP",
    token_turnin = "Turn in",
    taught_by_item = "Formula",
    world_drop = "World drop",
    unknown = "Source",
}

local RAID_DROP_ZONES = {
    ["ahn'qiraj"] = true,
    ["black temple"] = true,
    ["blackwing lair"] = true,
    ["gruul's lair"] = true,
    ["hyjal summit"] = true,
    ["karazhan"] = true,
    ["magtheridon's lair"] = true,
    ["molten core"] = true,
    ["naxxramas"] = true,
    ["onyxia's lair"] = true,
    ["serpentshrine cavern"] = true,
    ["sunwell plateau"] = true,
    ["tempest keep"] = true,
    ["zul'aman"] = true,
    ["zul'gurub"] = true,
}

local DUNGEON_DROP_ZONES = {
    ["auchenai crypts"] = true,
    ["blackrock depths"] = true,
    ["blackrock spire"] = true,
    ["dire maul"] = true,
    ["hellfire ramparts"] = true,
    ["magisters' terrace"] = true,
    ["mana-tombs"] = true,
    ["old hillsbrad foothills"] = true,
    ["sethekk halls"] = true,
    ["shadow labyrinth"] = true,
    ["stratholme"] = true,
    ["the arcatraz"] = true,
    ["the black morass"] = true,
    ["the blood furnace"] = true,
    ["the botanica"] = true,
    ["the mechanar"] = true,
    ["the shattered halls"] = true,
    ["the slave pens"] = true,
    ["the steamvault"] = true,
    ["the underbog"] = true,
}

local ACCESS_COLORS = {
    ready = { 0.12, 0.24, 0.14, 0.96, 0.46, 0.95, 0.48, 1 },
    ready_alternate = { 0.12, 0.24, 0.14, 0.96, 0.46, 0.95, 0.48, 1 },
    needs_rep = { 0.30, 0.20, 0.08, 0.96, 0.96, 0.72, 0.34, 1 },
    needs_profession = { 0.26, 0.13, 0.13, 0.96, 0.94, 0.48, 0.48, 1 },
    needs_recipe = { 0.26, 0.13, 0.13, 0.96, 0.94, 0.48, 0.48, 1 },
    check_prereq = { 0.16, 0.18, 0.24, 0.96, 0.66, 0.78, 0.94, 1 },
    unknown = { 0.16, 0.16, 0.18, 0.96, 0.62, 0.62, 0.66, 1 },
}

local REPUTATION_STANDINGS = {
    Hated = 1,
    Hostile = 2,
    Unfriendly = 3,
    Neutral = 4,
    Friendly = 5,
    Honored = 6,
    Revered = 7,
    Exalted = 8,
}

local CLASS_COLORS = {
    Druid = { 1.00, 0.49, 0.04 },
    Hunter = { 0.67, 0.83, 0.45 },
    Mage = { 0.25, 0.78, 0.92 },
    Paladin = { 0.96, 0.55, 0.73 },
    Priest = { 1.00, 1.00, 1.00 },
    Rogue = { 1.00, 0.96, 0.41 },
    Shaman = { 0.00, 0.44, 0.87 },
    Warlock = { 0.53, 0.53, 0.93 },
    Warrior = { 0.78, 0.61, 0.43 },
}

local QUALITY_COLORS = {
    poor = { 0.62, 0.62, 0.62 },
    common = { 1.00, 1.00, 1.00 },
    uncommon = { 0.12, 1.00, 0.00 },
    rare = { 0.00, 0.44, 0.87 },
    epic = { 0.64, 0.21, 0.93 },
    legendary = { 1.00, 0.50, 0.00 },
}

local RANK_FILTER_LABELS = {
    all = "All tags",
    bis = "BiS only",
    ranked = "Alts only",
    situational = "Sidegrades",
    pvp = "PvP only",
    unrealistic = "Hard Farms",
    option = "Nice-to-have",
}
local RANK_FILTER_ORDER = { "all", "bis", "ranked", "situational", "pvp", "unrealistic", "option" }

local OWNED_FILTER_LABELS = {
    all = "All ownership",
    missing = "Missing",
    owned = "Owned",
    equipped = "Equipped",
    bag = "Bags",
    bank = "Bank",
}
local OWNED_FILTER_ORDER = { "all", "missing", "owned", "equipped", "bag", "bank" }

local BOE_FILTER_LABELS = {
    all = "All binding",
    boe = "BoE only",
    not_boe = "Not BoE",
}
local BOE_FILTER_ORDER = { "all", "boe", "not_boe" }

local LONGEVITY_FILTER_LABELS = {
    all = "All usefulness",
    current = "Current",
    future = "Future value",
    long = "Long-term",
}
local LONGEVITY_FILTER_ORDER = { "all", "current", "future", "long" }

local RANK_COLORS = {
    best = { 0.18, 0.15, 0.06, 0.96, 0.92, 0.76, 0.28, 1 },
    ranked = { 0.10, 0.18, 0.30, 0.96, 0.46, 0.68, 0.98, 1 },
    situational = { 0.18, 0.12, 0.28, 0.96, 0.76, 0.56, 0.98, 1 },
    pvp = { 0.12, 0.18, 0.30, 0.96, 0.56, 0.72, 1.00, 1 },
    hard = { 0.28, 0.12, 0.12, 0.96, 0.94, 0.48, 0.48, 1 },
    backup = { 0.14, 0.14, 0.16, 0.96, 0.58, 0.58, 0.64, 1 },
    chase_first = { 0.16, 0.26, 0.14, 0.96, 0.54, 0.92, 0.46, 1 },
    strong_targets = { 0.11, 0.22, 0.34, 0.96, 0.48, 0.72, 0.96, 1 },
    useful_backups = { 0.24, 0.18, 0.08, 0.96, 0.92, 0.72, 0.34, 1 },
    only_if_easy = { 0.14, 0.14, 0.16, 0.96, 0.58, 0.58, 0.64, 1 },
    missing = { 0.12, 0.12, 0.14, 0.92, 0.34, 0.34, 0.38, 1 },
    enhance = { 0.10, 0.18, 0.24, 0.96, 0.54, 0.82, 0.88, 1 },
}

local PLANNER_TIER_SECTIONS = {
    { key = "chase_first", title = "BiS Now" },
    { key = "strong_targets", title = "Future BiS" },
    { key = "useful_backups", title = "Alt / Sidegrade" },
    { key = "only_if_easy", title = "Nice-to-have" },
}

local function clamp(value, minValue, maxValue)
    if value < minValue then
        return minValue
    elseif value > maxValue then
        return maxValue
    end
    return value
end

local function lower(value)
    return string.lower(tostring(value or ""))
end

local function trim(value)
    return tostring(value or ""):gsub("^%s+", ""):gsub("%s+$", "")
end

local function listContains(list, value)
    for _, item in ipairs(list or {}) do
        if item == value then
            return true
        end
    end
    return false
end

local function normalizeTabName(tabName)
    return TAB_NAME_ALIASES[tabName] or tabName
end

local function safeSetText(fontString, text)
    if fontString then
        fontString:SetText(text or "")
    end
end

local function appendText(parts, text)
    text = trim(text)
    if text ~= "" then
        table.insert(parts, text)
    end
end

local function joinText(parts, separator)
    local cleaned = {}
    for _, text in ipairs(parts or {}) do
        appendText(cleaned, text)
    end
    return table.concat(cleaned, separator or " - ")
end

local function classColor(className)
    local color = CLASS_COLORS[className]
    if color then
        return color[1], color[2], color[3]
    end
    return 1, 0.82, 0.28
end

local function itemQualityColor(item)
    local color = item and QUALITY_COLORS[item.quality]
    if color then
        return color[1], color[2], color[3]
    end
    return 0.9, 0.9, 0.9
end

local function displayRankInfo(data, mode)
    if data and data.display_rank_label then
        return data.display_rank_label, data.display_rank_kind or "backup"
    end

    if mode == "enhance" then
        return "Enhancement", "enhance"
    elseif mode == "wishlist" and data and data.priorityTier then
        return data.priorityTier, data.recommendation_tier or "only_if_easy"
    elseif not data then
        return "Nice-to-have", "backup"
    end

    local rank = tonumber(data.rank)
    if data.rank_group == "bis" then
        return "BiS", "best"
    elseif data.rank_group == "ranked" then
        return "Alt", "ranked"
    elseif data.rank_group == "situational" then
        return "Sidegrade", "situational"
    elseif data.rank_group == "pvp" then
        return "PvP", "pvp"
    elseif data.rank_group == "unrealistic" then
        return "Hard Farm", "hard"
    elseif rank and rank > 1 then
        return "Alt", "ranked"
    end

    return "Nice-to-have", "backup"
end

local function rankMeaning(data, mode)
    local label, kind = displayRankInfo(data, mode)
    if kind == "best" then
        return label .. ": best-in-slot item for this slot and phase."
    elseif kind == "ranked" then
        return label .. ": listed alternative below BiS."
    elseif kind == "situational" then
        return label .. ": useful for a specific fight, role, or gearing setup."
    elseif kind == "pvp" then
        return label .. ": PvP-sourced or PvP-focused item."
    elseif kind == "hard" then
        return label .. ": strong item with unusually difficult access."
    elseif kind == "chase_first" then
        return label .. ": highest-priority farmable upgrade."
    elseif kind == "strong_targets" then
        return label .. ": farmable now with later BiS value."
    elseif kind == "useful_backups" then
        return label .. ": worthwhile alt or sidegrade pickup."
    elseif kind == "enhance" then
        return label .. ": gem, enchant, or consumable recommendation."
    elseif kind == "missing" then
        return label .. ": no equipped item or no matching recommendation."
    end

    return label .. ": optional pickup when better targets are not available."
end

local function contentWidth(parent, fallback)
    local width = parent and parent.GetWidth and parent:GetWidth()
    if not width or width <= 1 then
        width = fallback or 560
    end
    return math.max(260, width - 4)
end

local function rowColumnLayout(width, showRank)
    if showRank == nil then
        showRank = true
    end

    local usable = math.max(260, width - (ROW_HORIZONTAL_PADDING * 2))
    local showWhy = usable >= WHY_COLUMN_THRESHOLD
    local whyWidth = 0

    if showWhy then
        whyWidth = clamp(math.floor(usable * 0.22), WHY_COLUMN_MIN_WIDTH, WHY_COLUMN_MAX_WIDTH)
    end

    local function fixedWidthFor(includeWhy)
        local columnCount = 3
        local fixedWidth = HAVE_COLUMN_WIDTH + GET_COLUMN_WIDTH
        if showRank then
            columnCount = columnCount + 1
            fixedWidth = fixedWidth + RANK_COLUMN_WIDTH
        end
        if includeWhy then
            columnCount = columnCount + 1
            fixedWidth = fixedWidth + whyWidth
        end
        return fixedWidth + (COLUMN_GAP * math.max(0, columnCount - 1))
    end

    local fixedWidth = fixedWidthFor(showWhy)
    local itemWidth = usable - fixedWidth
    if showWhy and itemWidth < 190 then
        showWhy = false
        whyWidth = 0
        fixedWidth = fixedWidthFor(false)
        itemWidth = usable - fixedWidth
    end

    itemWidth = math.max(130, itemWidth)

    local x = ROW_HORIZONTAL_PADDING
    local layout = {
        showWhy = showWhy,
        showRank = showRank,
    }

    if showRank then
        layout.rank = { x = x, width = RANK_COLUMN_WIDTH }
        x = x + RANK_COLUMN_WIDTH + COLUMN_GAP
    end

    layout.item = { x = x, width = itemWidth }
    x = x + itemWidth + COLUMN_GAP

    if showWhy then
        layout.why = { x = x, width = whyWidth }
        x = x + whyWidth + COLUMN_GAP
    end

    layout.have = { x = x, width = HAVE_COLUMN_WIDTH }
    x = x + HAVE_COLUMN_WIDTH + COLUMN_GAP
    layout.get = { x = x, width = GET_COLUMN_WIDTH }
    return layout
end

local function getContainerNumSlotsSafe(bag)
    local ok, result
    if C_Container and C_Container.GetContainerNumSlots then
        ok, result = pcall(C_Container.GetContainerNumSlots, bag)
        if ok then
            return result or 0
        end
    elseif GetContainerNumSlots then
        ok, result = pcall(GetContainerNumSlots, bag)
        if ok then
            return result or 0
        end
    end
    return 0
end

local function getContainerItemIDSafe(bag, slot)
    local ok, result
    if C_Container and C_Container.GetContainerItemID then
        ok, result = pcall(C_Container.GetContainerItemID, bag, slot)
        if ok then
            return result
        end
    elseif GetContainerItemID then
        ok, result = pcall(GetContainerItemID, bag, slot)
        if ok then
            return result
        end
    end
    return nil
end

local function getInventorySlotId(slotDefinition)
    if GetInventorySlotInfo and slotDefinition.inventorySlotName then
        local slotId = GetInventorySlotInfo(slotDefinition.inventorySlotName)
        if slotId then
            return slotId
        end
    end
    return slotDefinition.inventorySlotId
end

local function getItemEquipLocation(itemId)
    if GetItemInfoInstant and itemId then
        local _, _, _, equipLocation = GetItemInfoInstant(itemId)
        return equipLocation
    end
    return nil
end

local function ownershipStateLabel(state)
    return OWNERSHIP_LABELS[state or "missing"] or OWNERSHIP_LABELS.missing
end

local function accessStateLabel(state)
    return ACCESS_LABELS[state or "unknown"] or ACCESS_LABELS.unknown
end

local function accessDetailLabel(state)
    return ACCESS_DETAIL_LABELS[state or "unknown"] or ACCESS_DETAIL_LABELS.unknown
end

local function accessSourceBadgeLabel(option)
    if not option then
        return nil
    end

    local sourceType = option.source_type or "unknown"
    if sourceType == "drop" then
        local zone = lower(option.zone)
        if RAID_DROP_ZONES[zone] then
            return "Raid drop"
        elseif DUNGEON_DROP_ZONES[zone] then
            return "Dungeon drop"
        end
        return "Drop"
    elseif sourceType == "trade" and option.label == "Trade enchant service" then
        return "Enchanter"
    end

    return ACCESS_SOURCE_BADGE_LABELS[sourceType] or ACCESS_SOURCE_BADGE_LABELS.unknown
end

local function rankFilterLabel(rankGroup)
    return RANK_FILTER_LABELS[rankGroup or "all"] or tostring(rankGroup or "All")
end

local function ownedFilterLabel(ownedState)
    return OWNED_FILTER_LABELS[ownedState or "all"] or ownershipStateLabel(ownedState)
end

local function boeFilterLabel(boe)
    return BOE_FILTER_LABELS[boe or "all"] or tostring(boe or "All binding")
end

local function longevityFilterLabel(longevity)
    return LONGEVITY_FILTER_LABELS[longevity or "all"] or tostring(longevity or "All usefulness")
end

local function requirementSummary(requirement)
    if not requirement then
        return "Unknown prerequisite"
    elseif requirement.type == "reputation" then
        return (requirement.standing or "Required") .. " with " .. (requirement.reputation or "unknown faction")
    elseif requirement.type == "profession" then
        local text = requirement.profession or "Profession"
        if requirement.skill then
            text = text .. " " .. tostring(requirement.skill)
        end
        return text
    elseif requirement.type == "profession_specialization" then
        return requirement.specialization or "Profession specialization"
    elseif requirement.type == "recipe_known" then
        return "Known recipe: " .. (requirement.spell_name or ("Spell " .. tostring(requirement.spell_id or "")))
    elseif requirement.type == "faction_choice" then
        return "Faction choice: " .. table.concat(requirement.choices or {}, " / ")
    elseif requirement.raw_text and requirement.raw_text ~= "" then
        return requirement.raw_text
    end
    return requirement.type or "Prerequisite"
end

local function requirementLineKey(state, requirement)
    return accessStateLabel(state) .. " - " .. requirementSummary(requirement)
end

local function appendRequirementLine(lines, seen, state, requirement)
    local key = requirementLineKey(state, requirement)
    if seen[key] then
        return
    end
    seen[key] = true
    table.insert(lines, key)
end

local function isCheckOnlyRequirement(requirement)
    if not requirement then
        return false
    elseif requirement.type == "unknown_text" or requirement.type == "source_access" then
        return true
    elseif requirement.type == "reputation" then
        return trim(requirement.reputation) == "" or not (tonumber(requirement.standing_rank) or REPUTATION_STANDINGS[requirement.standing or ""])
    elseif requirement.type == "profession" then
        return trim(requirement.profession) == ""
    elseif requirement.type == "recipe_known" then
        return not tonumber(requirement.spell_id)
    elseif requirement.type == "faction_choice" then
        return not requirement.choices or #requirement.choices == 0
    end
    return false
end

local function isBlockingAccessState(state)
    return state == "needs_recipe" or state == "needs_profession" or state == "needs_rep"
end

local FACTION_NAME_ALIASES = {
    ["classic - cenarion circle"] = "Cenarion Circle",
    ["keepers of time"] = "Keepers of Time",
    ["the keepers of time"] = "Keepers of Time",
    ["kurenai"] = "Kurenai",
    ["the kurenai"] = "Kurenai",
    ["scale of the sands"] = "The Scale of the Sands",
    ["the scale of the sands"] = "The Scale of the Sands",
    ["the scales of the sand"] = "The Scale of the Sands",
    ["mag'har"] = "The Mag'har",
    ["the mag'har"] = "The Mag'har",
    ["the maghar"] = "The Mag'har",
    ["the shat'tar"] = "The Sha'tar",
}

local function splitFactionNames(factionName)
    local names = {}
    for part in string.gmatch(tostring(factionName or ""), "[^/]+") do
        local name = trim(part)
        if name ~= "" then
            table.insert(names, name)
        end
    end
    return names
end

local function cacheReputationStanding(accessState, factionName, standing)
    if not accessState or not factionName or not standing then
        return
    end
    accessState.reputations = accessState.reputations or {}
    accessState.reputations[lower(factionName)] = tonumber(standing)
end

local function getSingleFactionStandingRank(factionName, accessState)
    if not factionName or factionName == "" then
        return nil
    end

    local lookupNames = { trim(factionName) }
    local alias = FACTION_NAME_ALIASES[lower(factionName)]
    if alias and alias ~= lookupNames[1] then
        table.insert(lookupNames, alias)
    end

    if accessState and accessState.reputations then
        for _, name in ipairs(lookupNames) do
            local standing = accessState.reputations[lower(name)]
            if standing then
                return standing
            end
        end
    end

    if C_Reputation and C_Reputation.GetFactionDataByName then
        for _, name in ipairs(lookupNames) do
            local ok, data = pcall(C_Reputation.GetFactionDataByName, name)
            if ok and data then
                local standing = data.reaction or data.standingID
                cacheReputationStanding(accessState, name, standing)
                if data.name then
                    cacheReputationStanding(accessState, data.name, standing)
                end
                return standing
            end
        end
    end

    if GetFactionInfoByName then
        for _, name in ipairs(lookupNames) do
            local ok, _, _, standing = pcall(GetFactionInfoByName, name)
            if ok and standing then
                cacheReputationStanding(accessState, name, standing)
                return standing
            end
        end
    end

    if GetNumFactions and GetFactionInfo then
        local okCount, factionCount = pcall(GetNumFactions)
        if okCount then
            for index = 1, factionCount do
                local okInfo, name, _, standing = pcall(GetFactionInfo, index)
                if okInfo and name then
                    cacheReputationStanding(accessState, name, standing)
                    for _, lookupName in ipairs(lookupNames) do
                        if name == lookupName then
                            return standing
                        end
                    end
                end
            end
        end
    end

    return nil
end

local function getFactionStandingRank(factionName, accessState)
    local bestStanding
    for _, name in ipairs(splitFactionNames(factionName)) do
        local standing = getSingleFactionStandingRank(name, accessState)
        if standing and (not bestStanding or standing > bestStanding) then
            bestStanding = standing
        end
    end
    return bestStanding
end

local function collectReputationState()
    local reputations = {}
    local accessState = { reputations = reputations }

    if GetNumFactions and GetFactionInfo then
        local okCount, factionCount = pcall(GetNumFactions)
        if okCount then
            for index = 1, factionCount do
                local okInfo, name, _, standing = pcall(GetFactionInfo, index)
                if okInfo and name and name ~= "" then
                    cacheReputationStanding(accessState, name, standing)
                end
            end
        end
    end

    return reputations
end

local function getPlayerSide()
    if UnitFactionGroup then
        local ok, side = pcall(UnitFactionGroup, "player")
        if ok and (side == "Alliance" or side == "Horde") then
            return side
        end
    end
    return nil
end

local function collectProfessionState()
    local professions = {}
    if not GetProfessions or not GetProfessionInfo then
        return professions
    end

    local professionSlots = { GetProfessions() }
    for _, professionIndex in ipairs(professionSlots) do
        if professionIndex then
            local name, _, rank = GetProfessionInfo(professionIndex)
            if name and name ~= "" then
                professions[lower(name)] = {
                    name = name,
                    skill = rank or 0,
                }
            end
        end
    end
    return professions
end

local function isSpellKnownSafe(spellId)
    if not spellId then
        return false
    end
    if IsSpellKnown then
        local ok, known = pcall(IsSpellKnown, spellId)
        if ok and known then
            return true
        end
    end
    if IsPlayerSpell then
        local ok, known = pcall(IsPlayerSpell, spellId)
        if ok and known then
            return true
        end
    end
    return false
end

local function ensureSpecialFrame(frameName)
    if not UISpecialFrames then
        return
    end
    if not listContains(UISpecialFrames, frameName) then
        table.insert(UISpecialFrames, frameName)
    end
end

local function tableCount(values)
    local count = 0
    for _ in pairs(values or {}) do
        count = count + 1
    end
    return count
end

local function firstSpecName(specs)
    if specs and specs[1] then
        return specs[1].name
    end
    return nil
end

local function phaseExists(phaseKey)
    for _, key in ipairs(BigBiSList:GetPhaseOrder()) do
        if key == phaseKey then
            return true
        end
    end
    return false
end

local function phaseLabelList(phases)
    local labels = {}
    for _, phaseKey in ipairs(BigBiSList:GetPhaseOrder()) do
        if phases and phases[phaseKey] then
            table.insert(labels, BigBiSList:GetPhaseDisplayName(phaseKey))
        end
    end
    return table.concat(labels, ", ")
end

function UI:GetSelection()
    BigBiSList:EnsureDatabase()
    return BigBiSListDB.char.selection
end

function UI:GetFilters()
    BigBiSList:EnsureDatabase()
    return BigBiSListDB.char.filters
end

function UI:ValidateSelection()
    BigBiSList:EnsureDatabase()

    local index = BigBiSList:GetDataIndex()
    local selection = BigBiSListDB.char.selection
    local className = selection.class
    local specName = selection.spec
    local phaseKey = selection.phase
    local tabName = normalizeTabName(selection.tab)

    if not index.specsByClass[className] then
        className = index.classNames[1]
    end

    local specs = index.specsByClass[className] or {}
    local specFound = false
    for _, spec in ipairs(specs) do
        if spec.name == specName then
            specFound = true
            break
        end
    end
    if not specFound then
        specName = firstSpecName(specs)
    end

    if not phaseExists(phaseKey) then
        phaseKey = "PR"
    end

    if not listContains(TAB_NAMES, tabName) then
        tabName = "Upgrades"
    end

    BigBiSList:SetSelection(className, specName, phaseKey, tabName)
end

function UI:BuildOwnedItems()
    BigBiSList:EnsureDatabase()

    local owned = {
        equippedSlots = {},
        bankScanned = BigBiSListDB.char.bankCache and BigBiSListDB.char.bankCache.scanned or false,
        bankUpdatedAt = BigBiSListDB.char.bankCache and BigBiSListDB.char.bankCache.updatedAt or "",
    }

    if GetInventoryItemID then
        for _, slotDefinition in ipairs(BigBiSList:GetEquipmentSlotDefinitions()) do
            local slotId = getInventorySlotId(slotDefinition)
            local itemId = slotId and GetInventoryItemID("player", slotId)
            if itemId then
                owned[itemId] = "equipped"
                owned.equippedSlots[slotDefinition.key] = {
                    item_id = itemId,
                    slotId = slotId,
                    slot = slotDefinition.label,
                }

                if slotDefinition.key == "MainHand" and getItemEquipLocation(itemId) == "INVTYPE_2HWEAPON" then
                    owned.equippedTwoHand = true
                end
            end
        end
    end

    for bag = 0, 4 do
        local numSlots = getContainerNumSlotsSafe(bag)

        for slot = 1, numSlots do
            local itemId = getContainerItemIDSafe(bag, slot)
            if itemId and not owned[itemId] then
                owned[itemId] = "bag"
            end
        end
    end

    local bankCache = BigBiSListDB.char.bankCache
    if bankCache and bankCache.items then
        for itemIdText in pairs(bankCache.items) do
            local itemId = tonumber(itemIdText)
            if itemId and not owned[itemId] then
                owned[itemId] = "bank"
            end
        end
    end

    return owned
end

function UI:BuildAccessState()
    return {
        professions = collectProfessionState(),
        reputations = collectReputationState(),
        playerSide = getPlayerSide(),
    }
end

function UI:EvaluateRequirement(requirement, accessState)
    if not requirement then
        return "unknown"
    end

    accessState = accessState or self.currentAccess or self:BuildAccessState()

    if isCheckOnlyRequirement(requirement) then
        return "check_prereq"
    end

    if requirement.type == "reputation" then
        local requiredRank = tonumber(requirement.standing_rank) or REPUTATION_STANDINGS[requirement.standing or ""] or 0
        local currentRank = getFactionStandingRank(requirement.reputation, accessState)
        if not currentRank then
            return "unknown"
        elseif currentRank < requiredRank then
            return "needs_rep"
        end
        return "ready"
    elseif requirement.type == "profession" then
        local profession = accessState.professions and accessState.professions[lower(requirement.profession)]
        local requiredSkill = tonumber(requirement.skill) or 0
        if not profession or (profession.skill or 0) < requiredSkill then
            return "needs_profession"
        end
        return "ready"
    elseif requirement.type == "profession_specialization" then
        local profession = accessState.professions and accessState.professions[lower(requirement.profession)]
        if not profession then
            return "needs_profession"
        end
        return "check_prereq"
    elseif requirement.type == "recipe_known" then
        if not isSpellKnownSafe(requirement.spell_id) then
            return "needs_recipe"
        end
        return "ready"
    elseif requirement.type == "faction_choice" then
        for _, faction in ipairs(requirement.choices or {}) do
            local standing = getFactionStandingRank(faction, accessState)
            if standing and standing > 4 then
                return "ready"
            end
        end
        return "needs_rep"
    elseif requirement.type == "source_access" then
        return "check_prereq"
    end

    return "unknown"
end

function UI:GetAccessStatus(data)
    return self:GetAccessEvaluation(data).status
end

function UI:EvaluateRequirementList(requirements, accessState)
    accessState = accessState or self.currentAccess or self:BuildAccessState()

    if not requirements or #requirements == 0 then
        return { status = "ready" }
    end

    local firstBlockerState
    local firstBlockerRequirement
    local firstCheckRequirement
    local firstUnknownRequirement

    for _, requirement in ipairs(requirements) do
        local state = self:EvaluateRequirement(requirement, accessState)
        if isBlockingAccessState(state) and not firstBlockerState then
            firstBlockerState = state
            firstBlockerRequirement = requirement
        elseif state == "check_prereq" then
            firstCheckRequirement = firstCheckRequirement or requirement
        elseif state == "unknown" then
            firstUnknownRequirement = firstUnknownRequirement or requirement
        end
    end

    if firstBlockerState then
        return {
            status = firstBlockerState,
            blockingRequirement = firstBlockerRequirement,
        }
    elseif firstCheckRequirement then
        return {
            status = "check_prereq",
            checkRequirement = firstCheckRequirement,
        }
    elseif firstUnknownRequirement then
        return {
            status = "unknown",
            unknownRequirement = firstUnknownRequirement,
        }
    end

    return { status = "ready" }
end

local function optionMatchesPlayerSide(option, accessState)
    local playerSide = accessState and accessState.playerSide
    local optionSide = option and option.side
    return not playerSide or not optionSide or optionSide == playerSide
end

function UI:EvaluateAccessOption(option, accessState)
    local evaluation = self:EvaluateRequirementList(option and option.requirements, accessState)
    evaluation.option = option
    return evaluation
end

function UI:GetAccessEvaluation(data)
    local accessState = self.currentAccess or self:BuildAccessState()
    local options = data and data.access_options

    if options and #options > 0 then
        local optionEvaluations = {}
        local primaryEvaluation
        local firstEvaluation
        local firstReadyEvaluation

        for _, option in ipairs(options) do
            if optionMatchesPlayerSide(option, accessState) then
                local evaluation = self:EvaluateAccessOption(option, accessState)
                table.insert(optionEvaluations, evaluation)

                firstEvaluation = firstEvaluation or evaluation
                if option.is_primary and not primaryEvaluation then
                    primaryEvaluation = evaluation
                end
                if evaluation.status == "ready" and not firstReadyEvaluation then
                    firstReadyEvaluation = evaluation
                end
            end
        end

        local selectedEvaluation = primaryEvaluation or firstEvaluation
        local status = selectedEvaluation and selectedEvaluation.status or "unknown"

        if primaryEvaluation and primaryEvaluation.status == "ready" then
            selectedEvaluation = primaryEvaluation
            status = "ready"
        elseif firstReadyEvaluation then
            selectedEvaluation = firstReadyEvaluation
            status = (firstReadyEvaluation.option and firstReadyEvaluation.option.is_primary) and "ready" or "ready_alternate"
        end

        return {
            status = status,
            optionEvaluation = selectedEvaluation,
            options = optionEvaluations,
        }
    end

    local flatEvaluation = self:EvaluateRequirementList(data and data.requirements, accessState)
    return {
        status = flatEvaluation.status,
        optionEvaluation = flatEvaluation,
    }
end

function UI:GetAccessBadgeLabel(state, data)
    if state == "ready" or state == "ready_alternate" then
        if data and data.ready_access_label and data.ready_access_label ~= "" then
            return data.ready_access_label
        end

        local evaluation = self:GetAccessEvaluation(data)
        local optionEvaluation = evaluation and evaluation.optionEvaluation
        local option = optionEvaluation and optionEvaluation.option
        return accessSourceBadgeLabel(option) or ACCESS_BADGE_LABELS[state] or ACCESS_BADGE_LABELS.unknown
    end

    return ACCESS_BADGE_LABELS[state] or ACCESS_BADGE_LABELS.unknown
end

function UI:GetAccessHelpText(evaluation, data)
    if evaluation and evaluation.status == "ready" and data and data.ready_access_detail and data.ready_access_detail ~= "" then
        return data.ready_access_detail
    end

    return self:GetAccessBlockingReason(evaluation)
end

function UI:GetAccessBlockingReason(evaluation)
    if not evaluation then
        return "No access data available."
    end

    if evaluation.status == "ready" then
        return "Farmable now. Drops, vendors, auctions, groups, and services are not guaranteed."
    elseif evaluation.blockingRequirement then
        return accessDetailLabel(evaluation.status) .. " - " .. requirementSummary(evaluation.blockingRequirement)
    elseif evaluation.checkRequirement then
        return "Check requirements - " .. requirementSummary(evaluation.checkRequirement)
    elseif evaluation.unknownRequirement then
        return "Unknown - " .. requirementSummary(evaluation.unknownRequirement)
    end

    return accessDetailLabel(evaluation.status)
end

function UI:FormatRequirements(data)
    local requirements = data and data.requirements
    if not requirements or #requirements == 0 then
        return "No known character requirements."
    end

    local lines = {}
    local seen = {}
    local accessState = self.currentAccess or self:BuildAccessState()
    for _, requirement in ipairs(requirements) do
        local state = self:EvaluateRequirement(requirement, accessState)
        appendRequirementLine(lines, seen, state, requirement)
    end
    return table.concat(lines, "\n")
end

function UI:FormatAccessOptionRequirements(optionEvaluation)
    local option = optionEvaluation and optionEvaluation.option
    local requirements = option and option.requirements
    if not requirements or #requirements == 0 then
        return "No known character requirements."
    end

    local lines = {}
    local seen = {}
    local accessState = self.currentAccess or self:BuildAccessState()
    for _, requirement in ipairs(requirements) do
        local state = self:EvaluateRequirement(requirement, accessState)
        appendRequirementLine(lines, seen, state, requirement)
    end
    return table.concat(lines, "\n")
end

function UI:FormatAccessOptions(accessEvaluation)
    local lines = {}
    local seen = {}
    for _, optionEvaluation in ipairs(accessEvaluation and accessEvaluation.options or {}) do
        local text = trim(self:FormatAccessOptionRequirements(optionEvaluation))
        if text ~= "" and not seen[text] then
            seen[text] = true
            table.insert(lines, text)
        end
    end

    if #lines == 0 then
        return "No known character requirements."
    end

    return table.concat(lines, "\n")
end

function UI:ScanBankItems()
    BigBiSList:EnsureDatabase()

    local cache = BigBiSListDB.char.bankCache
    cache.items = {}

    local function addContainerItems(bag)
        local numSlots = getContainerNumSlotsSafe(bag)
        for slot = 1, numSlots do
            local itemId = getContainerItemIDSafe(bag, slot)
            if itemId then
                cache.items[tostring(itemId)] = true
            end
        end
    end

    addContainerItems(BANK_CONTAINER or -1)

    local firstBankBag = (NUM_BAG_SLOTS or 4) + 1
    local lastBankBag = firstBankBag + (NUM_BANKBAGSLOTS or 7) - 1
    for bag = firstBankBag, lastBankBag do
        addContainerItems(bag)
    end

    cache.scanned = true
    cache.updatedAt = date and date("%Y-%m-%d %H:%M") or "this session"
end

function UI:GetAvailabilityFilters()
    local filters = {}
    for key, value in pairs(self:GetFilters() or {}) do
        filters[key] = value
    end
    local accessState = self.currentAccess or self:BuildAccessState()
    filters.faction = accessState and accessState.playerSide or "all"
    filters.ownedItems = self.currentOwned or self:BuildOwnedItems()
    filters.ignoredItems = BigBiSListDB.char.ignoredItems
    filters.hideIgnored = true
    return filters
end

function UI:GetAvailableSourceTypeValues()
    local selection = self:GetSelection()
    local filters = self:GetAvailabilityFilters()
    return BigBiSList:GetAvailableFilterSourceTypes(selection.class, selection.spec, selection.phase, selection.tab, filters)
end

function UI:GetAvailableZoneValues()
    local selection = self:GetSelection()
    local filters = self:GetAvailabilityFilters()
    return BigBiSList:GetAvailableFilterZones(selection.class, selection.spec, selection.phase, selection.tab, filters)
end

function UI:GetAvailableReputationValues()
    local selection = self:GetSelection()
    local filters = self:GetAvailabilityFilters()
    return BigBiSList:GetAvailableFilterReputations(selection.class, selection.spec, selection.phase, selection.tab, filters)
end

function UI:IsSourceTypeValueAvailable(sourceType)
    if not sourceType or sourceType == "all" then
        return true
    end

    for _, availableSourceType in ipairs(self:GetAvailableSourceTypeValues()) do
        if availableSourceType == sourceType then
            return true
        end
    end
    return false
end

function UI:ValidateSourceTypeFilter()
    local filters = self:GetFilters()
    if filters.sourceType and filters.sourceType ~= "all" and not self:IsSourceTypeValueAvailable(filters.sourceType) then
        filters.sourceType = "all"
    end
end

function UI:IsZoneValueAvailable(zone)
    if not zone or zone == "all" then
        return true
    end

    for _, availableZone in ipairs(self:GetAvailableZoneValues()) do
        if availableZone == zone then
            return true
        end
    end
    return false
end

function UI:ValidateZoneFilter()
    local filters = self:GetFilters()
    if filters.zone and filters.zone ~= "all" and not self:IsZoneValueAvailable(filters.zone) then
        filters.zone = "all"
    end
end

function UI:IsReputationValueAvailable(reputation)
    if not reputation or reputation == "all" then
        return true
    end

    for _, availableReputation in ipairs(self:GetAvailableReputationValues()) do
        if availableReputation == reputation then
            return true
        end
    end
    return false
end

function UI:ValidateReputationFilter()
    local filters = self:GetFilters()
    if filters.reputation and filters.reputation ~= "all" and not self:IsReputationValueAvailable(filters.reputation) then
        filters.reputation = "all"
    end
end

function UI:BuildFilterPayload()
    local filters = self:GetFilters()
    self.currentAccess = self:BuildAccessState()
    self.currentOwned = self:BuildOwnedItems()
    self:ValidateSourceTypeFilter()
    self:ValidateZoneFilter()
    self:ValidateReputationFilter()
    return {
        search = filters.search,
        sourceType = filters.sourceType,
        zone = filters.zone,
        reputation = filters.reputation,
        rankGroup = filters.rankGroup,
        ownedState = filters.ownedState,
        binding = filters.binding,
        boe = filters.boe,
        faction = self.currentAccess and self.currentAccess.playerSide or "all",
        longevity = filters.longevity,
        slots = filters.slots,
        ownedItems = self.currentOwned,
        ignoredItems = BigBiSListDB.char.ignoredItems,
        hideIgnored = true,
    }
end

function UI:SaveWindow()
    if not self.frame or not BigBiSListDB then
        return
    end

    local window = BigBiSListDB.profile.window
    local point, _, relativePoint, x, y = self.frame:GetPoint(1)
    window.point = point or "CENTER"
    window.relativePoint = relativePoint or "CENTER"
    window.x = x or 0
    window.y = y or 0
    window.width = self.frame:GetWidth()
    window.height = self.frame:GetHeight()
    window.scale = self.frame:GetScale()
end

function UI:GetResizeBounds()
    local parent = self.frame and self.frame.GetParent and self.frame:GetParent() or UIParent
    local parentWidth = parent and parent.GetWidth and parent:GetWidth()
    local parentHeight = parent and parent.GetHeight and parent:GetHeight()

    if (not parentWidth or parentWidth <= 0) and GetScreenWidth then
        parentWidth = GetScreenWidth()
    end
    if (not parentHeight or parentHeight <= 0) and GetScreenHeight then
        parentHeight = GetScreenHeight()
    end

    local maxWidth = math.floor((parentWidth or DEFAULT_WIDTH) - RESIZE_SCREEN_MARGIN)
    local maxHeight = math.floor((parentHeight or DEFAULT_HEIGHT) - RESIZE_SCREEN_MARGIN)
    maxWidth = math.max(1, maxWidth)
    maxHeight = math.max(1, maxHeight)

    local minWidth = math.min(MIN_WIDTH, maxWidth)
    local minHeight = math.min(MIN_HEIGHT, maxHeight)
    return minWidth, minHeight, maxWidth, maxHeight
end

function UI:ApplyResizeBounds()
    if not self.frame then
        return
    end

    local minWidth, minHeight, maxWidth, maxHeight = self:GetResizeBounds()
    if self.frame.SetResizeBounds then
        self.frame:SetResizeBounds(minWidth, minHeight, maxWidth, maxHeight)
    else
        if self.frame.SetMinResize then
            self.frame:SetMinResize(minWidth, minHeight)
        end
        if self.frame.SetMaxResize then
            self.frame:SetMaxResize(maxWidth, maxHeight)
        end
    end
end

function UI:RestoreWindow()
    local window = BigBiSListDB.profile.window
    local minWidth, minHeight, maxWidth, maxHeight = self:GetResizeBounds()
    local width = clamp(window.width or DEFAULT_WIDTH, minWidth, maxWidth)
    local height = clamp(window.height or DEFAULT_HEIGHT, minHeight, maxHeight)

    self.frame:SetSize(width, height)
    self.frame:SetScale(window.scale or 1)
    self.frame:ClearAllPoints()
    self.frame:SetPoint(window.point or "CENTER", UIParent, window.relativePoint or "CENTER", window.x or 0, window.y or 0)
end

function UI:GetClassDropdownItems()
    local selection = self:GetSelection()
    local items = {}
    for _, className in ipairs(BigBiSList:GetDataIndex().classNames) do
        table.insert(items, {
            value = className,
            text = className,
            checked = className == selection.class,
        })
    end
    return items
end

function UI:GetSpecDropdownItems()
    local selection = self:GetSelection()
    local specs = BigBiSList:GetDataIndex().specsByClass[selection.class] or {}
    local items = {}
    for _, spec in ipairs(specs) do
        table.insert(items, {
            value = spec.name,
            text = spec.name,
            checked = spec.name == selection.spec,
        })
    end
    return items
end

function UI:GetSourceDropdownItems()
    local filters = self:GetFilters()
    self:ValidateSourceTypeFilter()
    local labels = BigBiSList:GetSourceTypeLabels()
    local items = {
        { value = "all", text = labels.all, checked = filters.sourceType == "all" },
    }
    for _, sourceType in ipairs(self:GetAvailableSourceTypeValues()) do
        table.insert(items, {
            value = sourceType,
            text = labels[sourceType] or sourceType,
            checked = filters.sourceType == sourceType,
        })
    end
    return items
end

function UI:GetZoneDropdownItems()
    local filters = self:GetFilters()
    self:ValidateZoneFilter()
    local items = {
        { value = "all", text = "All zones", checked = filters.zone == "all" },
    }
    for _, zone in ipairs(self:GetAvailableZoneValues()) do
        table.insert(items, {
            value = zone,
            text = zone,
            checked = filters.zone == zone,
        })
    end
    return items
end

function UI:GetReputationDropdownItems()
    local filters = self:GetFilters()
    self:ValidateReputationFilter()
    local items = {
        { value = "all", text = "All reps", checked = filters.reputation == "all" },
    }
    for _, reputation in ipairs(self:GetAvailableReputationValues()) do
        table.insert(items, {
            value = reputation,
            text = reputation,
            checked = filters.reputation == reputation,
        })
    end
    return items
end

local function filterDropdownItems(values, labels, selectedValue)
    local items = {}
    for _, value in ipairs(values) do
        table.insert(items, {
            value = value,
            text = labels[value] or value,
            checked = selectedValue == value,
        })
    end
    return items
end

function UI:GetRankDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(RANK_FILTER_ORDER, RANK_FILTER_LABELS, filters.rankGroup or "all")
end

function UI:GetOwnedDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(OWNED_FILTER_ORDER, OWNED_FILTER_LABELS, filters.ownedState or "all")
end

function UI:GetBoeDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(BOE_FILTER_ORDER, BOE_FILTER_LABELS, filters.boe or "all")
end

function UI:GetLongevityDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(LONGEVITY_FILTER_ORDER, LONGEVITY_FILTER_LABELS, filters.longevity or "all")
end

function UI:SetClass(className)
    local index = BigBiSList:GetDataIndex()
    local specs = index.specsByClass[className] or {}
    BigBiSList:SetSelection(className, firstSpecName(specs), nil, nil)
    self:ValidateZoneFilter()
    self:ValidateReputationFilter()
    self:Refresh()
end

function UI:SetSpec(specName)
    BigBiSList:SetSelection(nil, specName, nil, nil)
    self:ValidateSourceTypeFilter()
    self:ValidateZoneFilter()
    self:ValidateReputationFilter()
    self:Refresh()
end

function UI:SetPhase(phaseKey)
    BigBiSList:SetSelection(nil, nil, phaseKey, nil)
    self:ValidateSourceTypeFilter()
    self:ValidateZoneFilter()
    self:ValidateReputationFilter()
    self:Refresh()
end

function UI:SetTab(tabName)
    BigBiSList:SetSelection(nil, nil, nil, normalizeTabName(tabName))
    self:ValidateSourceTypeFilter()
    self:ValidateZoneFilter()
    self:ValidateReputationFilter()
    self:Refresh()
end

function UI:SetFilter(key, value)
    local filters = self:GetFilters()
    filters[key] = value
    if key == "sourceType" or key == "zone" or key == "reputation" then
        self:ValidateSourceTypeFilter()
        self:ValidateZoneFilter()
        self:ValidateReputationFilter()
    end
    self:Refresh()
end

function UI:ToggleSlot(slotName)
    local filters = self:GetFilters()
    filters.slots = filters.slots or {}
    filters.slots[slotName] = not filters.slots[slotName] or nil
    self:Refresh()
end

function UI:ClearFilters()
    local filters = self:GetFilters()
    filters.search = ""
    filters.sourceType = "all"
    filters.zone = "all"
    filters.reputation = "all"
    filters.rankGroup = "all"
    filters.ownedState = "all"
    filters.binding = "all"
    filters.boe = "all"
    filters.faction = "all"
    filters.longevity = "all"
    filters.slots = {}

    if self.searchBox then
        self.searchBox:SetText("")
        self.searchBox:ClearFocus()
    end

    self:Refresh()
end

function UI:AddWishlist(itemId)
    BigBiSList:EnsureDatabase()
    BigBiSListDB.char.wishlist[tostring(itemId)] = true
    self:RefreshDetails(itemId)
end

function UI:RemoveWishlist(itemId)
    BigBiSList:EnsureDatabase()
    BigBiSListDB.char.wishlist[tostring(itemId)] = nil
    self:Refresh()
end

function UI:IgnoreItem(itemId)
    BigBiSList:EnsureDatabase()
    BigBiSListDB.char.ignoredItems[tostring(itemId)] = true
    self:Refresh()
end

function UI:UnignoreItem(itemId)
    BigBiSList:EnsureDatabase()
    BigBiSListDB.char.ignoredItems[tostring(itemId)] = nil
    self:Refresh()
end

function UI:SetItemButton(button, itemId, nameText, fallbackName, fallbackQuality, detailData, detailMode)
    button.entityType = "item"
    button.entityId = itemId
    button.itemId = itemId
    button.spellId = nil
    button.itemLink = nil
    button.spellLink = nil
    button.detailData = detailData
    button.detailMode = detailMode
    button.icon:SetDesaturated(false)
    button.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")

    safeSetText(nameText, fallbackName or ("Item " .. tostring(itemId)))
    if nameText then
        local r, g, b = itemQualityColor({ quality = fallbackQuality })
        nameText:SetTextColor(r, g, b, 1)
    end

    local function applyItemInfo(itemName, itemLink, itemQuality, itemTexture)
        if button.itemId ~= itemId then
            return
        end

        if itemTexture then
            button.icon:SetTexture(itemTexture)
        end
        if itemName and nameText then
            nameText:SetText(itemName)
        end
        if itemLink then
            button.itemLink = itemLink
        end
        if itemQuality and nameText and GetItemQualityColor then
            local r, g, b = GetItemQualityColor(itemQuality)
            nameText:SetTextColor(r, g, b, 1)
        end
    end

    if GetItemInfo then
        local itemName, itemLink, itemQuality, _, _, _, _, _, _, itemTexture = GetItemInfo(itemId)
        applyItemInfo(itemName, itemLink, itemQuality, itemTexture)
    end

    if Item and Item.CreateFromItemID then
        local item = Item:CreateFromItemID(itemId)
        item:ContinueOnItemLoad(function()
            local itemName = item.GetItemName and item:GetItemName()
            local itemLink = item.GetItemLink and item:GetItemLink()
            local itemIcon = item.GetItemIcon and item:GetItemIcon()
            local _, _, itemQuality = GetItemInfo and GetItemInfo(itemId)
            applyItemInfo(itemName, itemLink, itemQuality, itemIcon)
        end)
    end

    button:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
        if self.itemLink then
            GameTooltip:SetHyperlink(self.itemLink)
        else
            GameTooltip:SetText(fallbackName or ("Item " .. tostring(itemId)))
        end
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
    button:SetScript("OnClick", function(self, buttonName)
        if buttonName == "RightButton" then
            UI:RefreshDetails(itemId, self.detailData, self.detailMode)
            return
        end

        if self.itemLink then
            if IsShiftKeyDown and IsShiftKeyDown() and ChatEdit_InsertLink then
                ChatEdit_InsertLink(self.itemLink)
            elseif IsControlKeyDown and IsControlKeyDown() and DressUpItemLink then
                DressUpItemLink(self.itemLink)
            elseif SetItemRef then
                SetItemRef(self.itemLink, self.itemLink, "LeftButton")
            end
        end
    end)
end

function UI:SetSpellButton(button, spellId, nameText, fallbackName, detailData, detailMode)
    button.entityType = "spell"
    button.entityId = spellId
    button.itemId = nil
    button.spellId = spellId
    button.itemLink = nil
    button.spellLink = nil
    button.detailData = detailData
    button.detailMode = detailMode
    button.icon:SetDesaturated(false)
    button.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")

    safeSetText(nameText, fallbackName or ("Spell " .. tostring(spellId)))
    if nameText then
        nameText:SetTextColor(1, 0.82, 0.28, 1)
    end

    local function applySpellInfo(spellName, spellLink, spellTexture)
        if button.spellId ~= spellId then
            return
        end

        if spellTexture then
            button.icon:SetTexture(spellTexture)
        end
        if spellName and nameText then
            nameText:SetText(spellName)
        end
        if spellLink then
            button.spellLink = spellLink
        end
    end

    local spellName, spellTexture
    if C_Spell and C_Spell.GetSpellInfo then
        local ok, info = pcall(C_Spell.GetSpellInfo, spellId)
        if ok and type(info) == "table" then
            spellName = info.name
            spellTexture = info.iconID
        elseif ok and type(info) == "string" then
            spellName = info
        end
    end
    if GetSpellInfo and (not spellName or not spellTexture) then
        local ok, name, _, icon = pcall(GetSpellInfo, spellId)
        if ok then
            spellName = spellName or name
            spellTexture = spellTexture or icon
        end
    end
    if C_Spell and C_Spell.GetSpellTexture and not spellTexture then
        local ok, icon = pcall(C_Spell.GetSpellTexture, spellId)
        if ok then
            spellTexture = icon
        end
    end
    if GetSpellTexture and not spellTexture then
        local ok, icon = pcall(GetSpellTexture, spellId)
        if ok then
            spellTexture = icon
        end
    end

    local spellLink
    if C_Spell and C_Spell.GetSpellLink then
        local ok, link = pcall(C_Spell.GetSpellLink, spellId)
        if ok then
            spellLink = link
        end
    end
    if GetSpellLink and not spellLink then
        local ok, link = pcall(GetSpellLink, spellId)
        if ok then
            spellLink = link
        end
    end
    applySpellInfo(spellName, spellLink, spellTexture)

    button:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
        if self.spellLink then
            GameTooltip:SetHyperlink(self.spellLink)
        elseif GameTooltip.SetSpellByID then
            GameTooltip:SetSpellByID(spellId)
        else
            GameTooltip:SetText(fallbackName or ("Spell " .. tostring(spellId)))
        end
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
    button:SetScript("OnClick", function(self, buttonName)
        if buttonName == "RightButton" then
            UI:RefreshDetails(spellId, self.detailData, self.detailMode)
            return
        end

        if self.spellLink then
            if IsShiftKeyDown and IsShiftKeyDown() and ChatEdit_InsertLink then
                ChatEdit_InsertLink(self.spellLink)
            elseif SetItemRef then
                SetItemRef(self.spellLink, self.spellLink, "LeftButton")
            end
        end
    end)
end

function UI:GetOwnershipState(itemId, itemIds)
    local priority = { missing = 0, bank = 1, bag = 2, equipped = 3 }
    local bestState = itemId and self.currentOwned and self.currentOwned[itemId] or nil

    for _, candidateItemId in ipairs(itemIds or {}) do
        local candidateState = self.currentOwned and self.currentOwned[candidateItemId]
        if candidateState == "equipped" then
            return "equipped"
        elseif candidateState and (priority[candidateState] or 0) > (priority[bestState or "missing"] or 0) then
            bestState = candidateState
        end
    end

    return bestState or "missing"
end

function UI:GetRowOwnershipState(data)
    if not data then
        return nil
    end
    if data.ownership_state then
        return data.ownership_state
    end
    if data.item_id or data.item_ids then
        return self:GetOwnershipState(data.item_id, data.item_ids)
    end
    return nil
end

function UI:CreateOwnershipBadge(parent, state, data)
    local widgets = BigBiSList.Widgets
    local color = OWNERSHIP_COLORS[state] or OWNERSHIP_COLORS.missing
    local label = data and data.ownership_label or ownershipStateLabel(state)
    local badge = widgets:CreateStatusBadge(parent, label, HAVE_COLUMN_WIDTH, 18, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })
    badge:EnableMouse(true)

    badge:SetScript("OnEnter", function(selfBadge)
        GameTooltip:SetOwner(selfBadge, "ANCHOR_RIGHT")
        GameTooltip:AddLine("Have", 1, 0.82, 0.28)
        GameTooltip:AddLine(label, 0.86, 0.86, 0.86)
        if data and data.ownership_detail and data.ownership_detail ~= "" then
            GameTooltip:AddLine(data.ownership_detail, 0.62, 0.62, 0.66, true)
        end
        if state == "bank" and self.currentOwned and self.currentOwned.bankUpdatedAt and self.currentOwned.bankUpdatedAt ~= "" then
            GameTooltip:AddLine("Bank cache: " .. self.currentOwned.bankUpdatedAt, 0.62, 0.62, 0.66)
        end
        GameTooltip:Show()
    end)
    badge:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    return badge
end

function UI:CreateAccessBadge(parent, state, data)
    local widgets = BigBiSList.Widgets
    local color = ACCESS_COLORS[state] or ACCESS_COLORS.unknown
    local badge = widgets:CreateStatusBadge(parent, self:GetAccessBadgeLabel(state, data), GET_COLUMN_WIDTH, 18, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })
    badge:EnableMouse(true)

    badge:SetScript("OnEnter", function(selfBadge)
        local evaluation = UI:GetAccessEvaluation(data)
        local optionEvaluation = evaluation.optionEvaluation
        local option = optionEvaluation and optionEvaluation.option
        GameTooltip:SetOwner(selfBadge, "ANCHOR_RIGHT")
        GameTooltip:AddLine("Can get", 1, 0.82, 0.28)
        GameTooltip:AddLine(accessStateLabel(evaluation.status), 0.86, 0.86, 0.86)
        if option then
            GameTooltip:AddLine("How to get: " .. (option.label or "Source"), 0.62, 0.78, 0.94, true)
            GameTooltip:AddLine(UI:GetAccessHelpText(optionEvaluation, data), 0.62, 0.62, 0.66, true)
        elseif data and data.ready_access_detail and evaluation.status == "ready" then
            GameTooltip:AddLine(data.ready_access_detail, 0.62, 0.62, 0.66, true)
        elseif data and data.requirements and #data.requirements > 0 then
            for _, requirement in ipairs(data.requirements) do
                GameTooltip:AddLine(requirementSummary(requirement), 0.62, 0.62, 0.66, true)
            end
        else
            GameTooltip:AddLine("No known character requirements.", 0.62, 0.62, 0.66, true)
        end
        GameTooltip:Show()
    end)
    badge:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    return badge
end

function UI:CreateRankBadge(parent, labelText, kind, data, mode)
    local widgets = BigBiSList.Widgets
    local color = RANK_COLORS[kind] or RANK_COLORS.backup
    local badge = widgets:CreateStatusBadge(parent, labelText, RANK_COLUMN_WIDTH, 18, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })
    badge:EnableMouse(true)

    badge:SetScript("OnEnter", function(selfBadge)
        GameTooltip:SetOwner(selfBadge, "ANCHOR_RIGHT")
        GameTooltip:AddLine("Tag", 1, 0.82, 0.28)
        GameTooltip:AddLine(rankMeaning(data, mode), 0.86, 0.86, 0.86, true)
        GameTooltip:Show()
    end)
    badge:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)

    return badge
end

function UI:GetRowRecommendationText(data, mode)
    if data and data.recommendation_summary and data.recommendation_summary ~= "" then
        return data.recommendation_summary
    end

    if mode == "planner" then
        return table.concat(data and data.reasons or {}, ", ")
    elseif mode == "enhance" then
        return data and data.detail or "Enhancement"
    elseif mode == "wishlist" then
        return data and data.detail or "Saved item"
    elseif data and data.rank_label then
        return displayRankInfo(data, mode)
    end

    return "Nice-to-have"
end

function UI:GetRowSubline(data, mode, includeWhy)
    local parts = {}

    if includeWhy then
        appendText(parts, self:GetRowRecommendationText(data, mode))
    end

    if mode == "planner" then
        appendText(parts, data and data.slot)
        appendText(parts, data and data.source_summary)
    elseif mode == "enhance" then
        appendText(parts, data and data.detail)
        appendText(parts, data and data.source_summary)
    elseif mode == "wishlist" then
        appendText(parts, data and data.detail)
        appendText(parts, data and data.source_summary)
    else
        appendText(parts, data and data.source_type_label)
        appendText(parts, data and data.source_summary)
    end

    return joinText(parts, " - ")
end

function UI:CreateListColumnHeader(parent, yOffset, mode)
    local width = contentWidth(parent, self.contentScroll and self.contentScroll:GetWidth() or 560)
    local layout = rowColumnLayout(width, mode ~= "enhance")
    local header = CreateFrame("Frame", nil, parent)
    header:SetHeight(COLUMN_HEADER_HEIGHT)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)

    local labels = {
        { text = layout.showWhy and "Item" or "Item / Why", column = layout.item },
        { text = "Have", column = layout.have },
        { text = "Get", column = layout.get },
    }
    if layout.showRank then
        table.insert(labels, 1, { text = "Tag", column = layout.rank })
    end
    if layout.showWhy then
        local whyIndex = layout.showRank and 3 or 2
        table.insert(labels, whyIndex, { text = "Why", column = layout.why })
    end

    for _, entry in ipairs(labels) do
        local label = header:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        label:SetPoint("TOPLEFT", header, "TOPLEFT", entry.column.x, -2)
        label:SetWidth(entry.column.width)
        local justify = (entry.text == "Have" or entry.text == "Get") and "CENTER" or "LEFT"
        label:SetJustifyH(justify)
        label:SetWordWrap(false)
        label:SetTextColor(0.62, 0.62, 0.66, 1)
        label:SetText(entry.text)
    end

    return header, COLUMN_HEADER_HEIGHT
end

function UI:CreateDataRow(parent, yOffset, data, mode)
    local widgets = BigBiSList.Widgets
    local entityType = data.entity_type or (data.spell_id and "spell") or "item"
    local entityId = data.entity_id or data.spell_id or data.item_id
    local width = contentWidth(parent, self.contentScroll and self.contentScroll:GetWidth() or 560)
    local layout = rowColumnLayout(width, mode ~= "enhance")
    local row = widgets:CreateItemRow(parent, ROW_HEIGHT)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    row.itemId = data.item_id
    row.entityType = entityType
    row.entityId = entityId
    row.detailData = data
    row.detailMode = mode

    if layout.showRank then
        local rankLabel, rankKind = displayRankInfo(data, mode)
        local rankBadge = self:CreateRankBadge(row, rankLabel, rankKind, data, mode)
        rankBadge:SetPoint("TOPLEFT", row, "TOPLEFT", layout.rank.x, -ROW_VERTICAL_PADDING)
    end

    local iconButton = widgets:CreateIconButton(row, 30, function(_, buttonName)
        if buttonName == "RightButton" then
            self:RefreshDetails(entityId, data, mode)
        end
    end)
    iconButton:SetPoint("TOPLEFT", row, "TOPLEFT", layout.item.x, -ROW_VERTICAL_PADDING)

    local nameText = widgets:CreateWrappedLabel(row, "", "GameFontNormal")
    nameText:SetPoint("TOPLEFT", iconButton, "TOPRIGHT", 8, -2)
    nameText:SetWidth(math.max(90, layout.item.width - ROW_ICON_SIZE - 8))
    nameText:SetJustifyH("LEFT")

    local detailText = widgets:CreateWrappedLabel(row, "", "GameFontNormalSmall")
    detailText:SetPoint("TOPLEFT", nameText, "BOTTOMLEFT", 0, -3)
    detailText:SetWidth(math.max(90, layout.item.width - ROW_ICON_SIZE - 8))
    detailText:SetJustifyH("LEFT")
    detailText:SetTextColor(0.68, 0.68, 0.72, 1)

    local whyText
    if layout.showWhy then
        whyText = widgets:CreateWrappedLabel(row, "", "GameFontNormalSmall")
        whyText:SetPoint("TOPLEFT", row, "TOPLEFT", layout.why.x, -ROW_VERTICAL_PADDING)
        whyText:SetWidth(layout.why.width)
        whyText:SetTextColor(0.76, 0.76, 0.80, 1)
    end

    local ownershipState = self:GetRowOwnershipState(data)
    if ownershipState then
        local ownershipBadge = self:CreateOwnershipBadge(row, ownershipState, data)
        ownershipBadge:SetPoint("TOPLEFT", row, "TOPLEFT", layout.have.x, -ROW_VERTICAL_PADDING)
    end

    local accessState = self:GetAccessStatus(data)
    local accessBadge = self:CreateAccessBadge(row, accessState, data)
    accessBadge:SetPoint("TOPLEFT", row, "TOPLEFT", layout.get.x, -ROW_VERTICAL_PADDING)

    local item = data.item or (data.item_id and BigBiSList:GetItemData(data.item_id))
    if entityType == "spell" then
        self:SetSpellButton(iconButton, data.spell_id or entityId, nameText, data.name, data, mode)
    else
        self:SetItemButton(iconButton, data.item_id, nameText, data.name, item and item.quality, data, mode)
    end

    safeSetText(detailText, self:GetRowSubline(data, mode, not layout.showWhy))
    if whyText then
        safeSetText(whyText, self:GetRowRecommendationText(data, mode))
    end

    local itemTextHeight = widgets:MeasureTextHeight(nameText, 14) + 3 + widgets:MeasureTextHeight(detailText, 12)
    local whyHeight = whyText and widgets:MeasureTextHeight(whyText, 14) or 0
    local rowHeight = math.max(ROW_HEIGHT, ROW_ICON_SIZE + (ROW_VERTICAL_PADDING * 2), itemTextHeight + (ROW_VERTICAL_PADDING * 2), whyHeight + (ROW_VERTICAL_PADDING * 2))
    row:SetHeight(rowHeight)

    row:SetScript("OnMouseUp", function(_, buttonName)
        if buttonName == "LeftButton" then
            self:RefreshDetails(entityId, data, mode)
        elseif buttonName == "RightButton" then
            if not data.item_id then
                self:RefreshDetails(entityId, data, mode)
            elseif BigBiSListDB.char.wishlist[tostring(data.item_id)] then
                self:RemoveWishlist(data.item_id)
            else
                self:AddWishlist(data.item_id)
            end
        end
    end)

    return row, rowHeight
end

function UI:RenderEmpty(message)
    local child = self.contentChild
    local label = child:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    label:SetPoint("TOPLEFT", child, "TOPLEFT", 8, -12)
    label:SetPoint("RIGHT", child, "RIGHT", -8, 0)
    label:SetJustifyH("LEFT")
    label:SetWordWrap(true)
    label:SetTextColor(0.72, 0.72, 0.76, 1)
    label:SetText(message)
    child:SetHeight(80)
end

function UI:SetContentHeight(yOffset)
    local minimum = self.contentScroll and self.contentScroll:GetHeight() or 1
    self.contentChild:SetHeight(math.max(math.abs(yOffset) + 32, minimum + 1))
end

function UI:RenderPhaseTab()
    local widgets = BigBiSList.Widgets
    local selection = self:GetSelection()
    local filters = self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems

    local groups = BigBiSList:GetPhaseRows(selection.class, selection.spec, selection.phase, filters)
    if #groups == 0 then
        self:RenderEmpty("No matching slot rows. Clear filters or choose another phase.")
        return
    end

    local yOffset = -2
    for _, group in ipairs(groups) do
        local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, group.slot, yOffset)
        yOffset = yOffset - headerHeight
        local _, columnHeaderHeight = self:CreateListColumnHeader(self.contentChild, yOffset, "phase")
        yOffset = yOffset - columnHeaderHeight

        for _, item in ipairs(group.items) do
            local row, rowHeight = self:CreateDataRow(self.contentChild, yOffset, item, "phase")
            yOffset = yOffset - rowHeight - 4
        end

        yOffset = yOffset - 6
    end

    self:SetContentHeight(yOffset)
end

function UI:RenderPlannerTab()
    local widgets = BigBiSList.Widgets
    local selection = self:GetSelection()
    local filters = self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems

    local rows = BigBiSList:GetPlannerRows(selection.class, selection.spec, selection.phase, filters)
    if #rows == 0 then
        self:RenderEmpty("No upgrade rows match the current filters.")
        return
    end

    local rowsByTier = {}
    for _, section in ipairs(PLANNER_TIER_SECTIONS) do
        rowsByTier[section.key] = {}
    end
    for _, rowData in ipairs(rows) do
        local tier = rowData.recommendation_tier or "only_if_easy"
        rowsByTier[tier] = rowsByTier[tier] or {}
        table.insert(rowsByTier[tier], rowData)
    end

    local yOffset = -2
    for _, section in ipairs(PLANNER_TIER_SECTIONS) do
        local sectionRows = rowsByTier[section.key] or {}
        if #sectionRows > 0 then
            local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, section.title, yOffset)
            yOffset = yOffset - headerHeight
            local _, columnHeaderHeight = self:CreateListColumnHeader(self.contentChild, yOffset, "planner")
            yOffset = yOffset - columnHeaderHeight

            for _, rowData in ipairs(sectionRows) do
                local row, rowHeight = self:CreateDataRow(self.contentChild, yOffset, rowData, "planner")
                yOffset = yOffset - rowHeight - 4
            end

            yOffset = yOffset - 6
        end
    end

    self:SetContentHeight(yOffset)
end

function UI:CreateGearOverlay(parent, text, kind)
    local widgets = BigBiSList.Widgets
    local color = OWNERSHIP_COLORS.missing
    if kind == "bis" then
        color = { 0.16, 0.14, 0.07, 0.96, 0.88, 0.72, 0.24, 1 }
    elseif kind == "ranked" or kind == "situational" or kind == "option" or kind == "pvp" then
        color = { 0.11, 0.23, 0.38, 0.96, 0.45, 0.68, 0.98, 1 }
    elseif kind == "unrealistic" or kind == "missing" then
        color = { 0.22, 0.12, 0.12, 0.96, 0.92, 0.48, 0.48, 1 }
    elseif kind == "empty" or kind == "disabled" then
        color = { 0.12, 0.12, 0.14, 0.92, 0.34, 0.34, 0.38, 1 }
    end

    local badge = widgets:CreatePanel(nil, parent, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })
    badge:SetSize(78, 18)

    local label = badge:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", badge, "LEFT", 4, 0)
    label:SetPoint("RIGHT", badge, "RIGHT", -4, 0)
    label:SetJustifyH("CENTER")
    label:SetWordWrap(false)
    label:SetText(text or "")
    badge.label = label

    return badge
end

function UI:CreateGearSlotRow(parent, rowData, xOffset, yOffset, width)
    local widgets = BigBiSList.Widgets
    local badgeRightInset = 92
    local row = widgets:CreateItemRow(parent, GEAR_ROW_HEIGHT)
    row:SetSize(width, GEAR_ROW_HEIGHT)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", xOffset, yOffset)
    row.itemId = rowData.item_id
    row.detailData = rowData
    row.detailMode = "gear"

    local slotLabel = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    slotLabel:SetPoint("TOPLEFT", row, "TOPLEFT", 8, -4)
    slotLabel:SetPoint("RIGHT", row, "RIGHT", -badgeRightInset, 0)
    slotLabel:SetJustifyH("LEFT")
    slotLabel:SetWordWrap(false)
    slotLabel:SetTextColor(1, 0.82, 0.28, 1)
    slotLabel:SetText(rowData.slot)

    local overlay = self:CreateGearOverlay(row, rowData.overlay, rowData.overlayKind)
    overlay:SetPoint("TOPRIGHT", row, "TOPRIGHT", -8, -6)

    local iconButton = widgets:CreateIconButton(row, 30, function()
        if rowData.item_id then
            self:RefreshDetails(rowData.item_id, rowData, "gear")
        end
    end)
    iconButton:SetPoint("TOPLEFT", slotLabel, "BOTTOMLEFT", 0, -2)

    local nameText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    nameText:SetPoint("TOPLEFT", iconButton, "TOPRIGHT", 8, 2)
    nameText:SetPoint("RIGHT", row, "RIGHT", -badgeRightInset, 0)
    nameText:SetJustifyH("LEFT")
    nameText:SetWordWrap(false)

    local detailText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    detailText:SetPoint("TOPLEFT", nameText, "BOTTOMLEFT", 0, -2)
    detailText:SetPoint("RIGHT", row, "RIGHT", -badgeRightInset, 0)
    detailText:SetJustifyH("LEFT")
    detailText:SetWordWrap(false)
    detailText:SetTextColor(0.68, 0.68, 0.72, 1)

    if rowData.item_id then
        local item = rowData.item or BigBiSList:GetItemData(rowData.item_id)
        self:SetItemButton(iconButton, rowData.item_id, nameText, rowData.name, item and item.quality, rowData, "gear")
        local detail = rowData.bestUse
            and (BigBiSList:GetPhaseDisplayName(rowData.bestUse.phase) .. " - " .. displayRankInfo(rowData.bestUse) .. " - " .. rowData.bestUse.slot)
            or "No BiS match for selected spec"
        detailText:SetText(detail)
    else
        iconButton.icon:SetDesaturated(true)
        nameText:SetText(rowData.disabledReason or "Empty")
        nameText:SetTextColor(0.62, 0.62, 0.66, 1)
        detailText:SetText(rowData.disabledReason or "No item equipped")
    end

    row:SetScript("OnMouseUp", function(_, buttonName)
        if buttonName == "LeftButton" and rowData.item_id then
            self:RefreshDetails(rowData.item_id, rowData, "gear")
        end
    end)

    return row, GEAR_ROW_HEIGHT
end

function UI:RenderGearTab()
    local widgets = BigBiSList.Widgets
    local selection = self:GetSelection()
    local filters = self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems

    local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, "Current Gear", -2)
    local startY = -2 - headerHeight
    local availableWidth = self.contentScroll and self.contentScroll:GetWidth() or 560
    availableWidth = math.max(260, availableWidth - 8)
    local columnGap = 10
    local twoColumns = availableWidth >= 500
    local columnWidth = twoColumns and math.floor((availableWidth - columnGap) / 2) or availableWidth
    local leftY = startY
    local rightY = startY

    local rows = BigBiSList:GetEquippedGearRows(selection.class, selection.spec, selection.phase, self.currentOwned)
    for _, rowData in ipairs(rows) do
        if twoColumns and rowData.column == "right" then
            self:CreateGearSlotRow(self.contentChild, rowData, columnWidth + columnGap, rightY, columnWidth)
            rightY = rightY - GEAR_ROW_HEIGHT - 6
        else
            self:CreateGearSlotRow(self.contentChild, rowData, 0, leftY, columnWidth)
            leftY = leftY - GEAR_ROW_HEIGHT - 6
        end
    end

    local bankText = self.currentOwned.bankScanned
        and ("Bank cache: " .. (self.currentOwned.bankUpdatedAt ~= "" and self.currentOwned.bankUpdatedAt or "scanned"))
        or "Bank cache: open your bank once to include banked items."
    local note = self.contentChild:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    note:SetPoint("TOPLEFT", self.contentChild, "TOPLEFT", 0, math.min(leftY, rightY) - 4)
    note:SetPoint("RIGHT", self.contentChild, "RIGHT", -8, 0)
    note:SetJustifyH("LEFT")
    note:SetTextColor(0.62, 0.62, 0.66, 1)
    note:SetText(bankText)

    self:SetContentHeight(math.min(leftY, rightY) - 28)
end

function UI:RenderEnhanceTab()
    local widgets = BigBiSList.Widgets
    local selection = self:GetSelection()
    local sections = BigBiSList:GetEnhancementRows(selection.class, selection.spec, selection.phase)
    self.currentOwned = self:BuildOwnedItems()
    local yOffset = -2
    local rendered = false

    for _, section in ipairs(sections) do
        if #section.rows > 0 then
            rendered = true
            local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, section.title, yOffset)
            yOffset = yOffset - headerHeight
            local _, columnHeaderHeight = self:CreateListColumnHeader(self.contentChild, yOffset, "enhance")
            yOffset = yOffset - columnHeaderHeight
            for _, rowData in ipairs(section.rows) do
                local row, rowHeight = self:CreateDataRow(self.contentChild, yOffset, rowData, "enhance")
                yOffset = yOffset - rowHeight - 4
            end
            yOffset = yOffset - 6
        end
    end

    if not rendered then
        self:RenderEmpty("No gems, enchants, or consumables found for this class, spec, and phase.")
        return
    end

    self:SetContentHeight(yOffset)
end

function UI:RenderWishlistTab()
    local widgets = BigBiSList.Widgets
    local index = BigBiSList:GetDataIndex()
    local wishlist = BigBiSListDB.char.wishlist or {}
    self.currentOwned = self:BuildOwnedItems()
    local yOffset = -2

    if tableCount(wishlist) == 0 then
        self:RenderEmpty("No wishlist items yet. Right-click an item row or use the detail drawer to add one.")
        return
    end

    local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, "Wishlist", yOffset)
    yOffset = yOffset - headerHeight
    local _, columnHeaderHeight = self:CreateListColumnHeader(self.contentChild, yOffset, "wishlist")
    yOffset = yOffset - columnHeaderHeight

    local selection = self:GetSelection()
    local plannerByItem = {}
    for _, plannerRow in ipairs(BigBiSList:GetPlannerRows(selection.class, selection.spec, selection.phase, {})) do
        local current = plannerByItem[plannerRow.item_id]
        if not current or (plannerRow.priority or 0) > (current.priority or 0) then
            plannerByItem[plannerRow.item_id] = plannerRow
        end
    end

    local rows = {}
    for key in pairs(wishlist) do
        local itemId = tonumber(key) or key
        local item = index.itemsById[tonumber(itemId)]
        local uses = index.usesByItemId[tonumber(itemId)] or {}
        local bestUse = uses[1]
        local plannerContext = plannerByItem[tonumber(itemId)]
        table.insert(rows, {
            item_id = tonumber(itemId),
            item = item,
            name = item and item.name or ("Item " .. tostring(itemId)),
            detail = bestUse and (bestUse.class .. " " .. bestUse.spec .. " - " .. bestUse.slot) or "Saved item",
            source_summary = item and item.source_summary or "",
            requirements = item and item.requirements,
            access_options = (plannerContext and plannerContext.access_options) or (bestUse and bestUse.access_options),
            priority = plannerContext and plannerContext.priority or 0,
            priorityTier = plannerContext and plannerContext.priorityTier,
            recommendation_tier = plannerContext and plannerContext.recommendation_tier,
            recommendation_summary = plannerContext and plannerContext.recommendation_summary,
            display_rank_label = plannerContext and plannerContext.display_rank_label,
            display_rank_kind = plannerContext and plannerContext.display_rank_kind,
        })
    end
    table.sort(rows, function(a, b)
        if (a.priority or 0) ~= (b.priority or 0) then
            return (a.priority or 0) > (b.priority or 0)
        end
        return lower(a.name) < lower(b.name)
    end)

    for _, data in ipairs(rows) do
        local row, rowHeight = self:CreateDataRow(self.contentChild, yOffset, data, "wishlist")
        yOffset = yOffset - rowHeight - 4
    end

    self:SetContentHeight(yOffset)
end

function UI:CreateSettingToggle(parent, yOffset, labelText, getValue, setValue, leftInset)
    local widgets = BigBiSList.Widgets
    local row = widgets:CreateItemRow(parent, 34)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", leftInset or 0, yOffset)
    row:SetPoint("RIGHT", parent, "RIGHT", -4, 0)

    local label = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    label:SetPoint("LEFT", row, "LEFT", 10, 0)
    label:SetPoint("RIGHT", row, "RIGHT", -120, 0)
    label:SetJustifyH("LEFT")
    label:SetWordWrap(false)
    label:SetText(labelText)

    local button = widgets:CreateTextButton(row, getValue() and "On" or "Off", 72, 22, function(selfButton)
        setValue(not getValue())
        selfButton.label:SetText(getValue() and "On" or "Off")
        selfButton:SetSelected(getValue())
    end)
    button:SetPoint("RIGHT", row, "RIGHT", -10, 0)
    button:SetSelected(getValue())

    return row, 34
end

function UI:SetTooltipSpecFilter(className, specName, enabled)
    local filters = BigBiSList:EnsureTooltipSpecFilters()
    if not filters or not className or not specName then
        return
    end

    filters[className] = filters[className] or {}
    filters[className][specName] = enabled and true or false
end

function UI:SetTooltipClassSpecFilters(className, enabled)
    local filters = BigBiSList:EnsureTooltipSpecFilters()
    local specs = BigBiSList:GetDataIndex().specsByClass[className] or {}
    if not filters or not className then
        return
    end

    filters[className] = filters[className] or {}
    for _, spec in ipairs(specs) do
        if spec.name then
            filters[className][spec.name] = enabled and true or false
        end
    end
end

function UI:SetAllTooltipSpecFilters(enabled)
    local filters = BigBiSList:EnsureTooltipSpecFilters()
    if not filters then
        return
    end

    for _, classData in ipairs(BigBiSList:GetDataIndex().classes or {}) do
        if classData.name then
            self:SetTooltipClassSpecFilters(classData.name, enabled)
        end
    end
end

function UI:GetTooltipSpecSelectionCount(className)
    local filters = BigBiSList:EnsureTooltipSpecFilters() or {}
    local selected = 0
    local total = 0

    local function countSpec(specName, classFilters)
        total = total + 1
        if type(classFilters) == "table" and classFilters[specName] == true then
            selected = selected + 1
        end
    end

    if className then
        local classFilters = filters[className]
        for _, spec in ipairs(BigBiSList:GetDataIndex().specsByClass[className] or {}) do
            if spec.name then
                countSpec(spec.name, classFilters)
            end
        end
    else
        for _, classData in ipairs(BigBiSList:GetDataIndex().classes or {}) do
            local currentClassName = classData.name
            local classFilters = currentClassName and filters[currentClassName] or nil
            for _, spec in ipairs(classData.specs or {}) do
                if spec.name then
                    countSpec(spec.name, classFilters)
                end
            end
        end
    end

    return selected, total
end

function UI:CreateSettingsActionHeader(parent, yOffset, titleText, countText, onAll, onNone)
    local widgets = BigBiSList.Widgets
    local headerHeight = 34
    local header = CreateFrame("Frame", nil, parent)
    header:SetHeight(headerHeight)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)

    local line = header:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(0.55, 0.55, 0.58, 0.45)
    line:SetHeight(1)
    line:SetPoint("BOTTOMLEFT", header, "BOTTOMLEFT", 0, 6)
    line:SetPoint("BOTTOMRIGHT", header, "BOTTOMRIGHT", 0, 6)

    local noneButton = widgets:CreateTextButton(header, "None", 54, 22, function()
        if onNone then
            onNone()
        end
    end)
    noneButton:SetPoint("RIGHT", header, "RIGHT", -8, 4)

    local allButton = widgets:CreateTextButton(header, "All", 54, 22, function()
        if onAll then
            onAll()
        end
    end)
    allButton:SetPoint("RIGHT", noneButton, "LEFT", -6, 0)

    local countLabel = header:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    countLabel:SetPoint("RIGHT", allButton, "LEFT", -10, 0)
    countLabel:SetWidth(96)
    countLabel:SetJustifyH("RIGHT")
    countLabel:SetWordWrap(false)
    countLabel:SetTextColor(0.62, 0.62, 0.66, 1)
    countLabel:SetText(countText or "")

    local label = header:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    label:SetPoint("LEFT", header, "LEFT", 8, 4)
    label:SetPoint("RIGHT", countLabel, "LEFT", -8, 0)
    label:SetJustifyH("LEFT")
    label:SetWordWrap(false)
    label:SetTextColor(1, 0.82, 0.28, 1)
    label:SetText(titleText)

    return header, headerHeight
end

function UI:CreateSettingsClassHeader(parent, yOffset, className)
    local selected, total = self:GetTooltipSpecSelectionCount(className)
    return self:CreateSettingsActionHeader(parent, yOffset, className, tostring(selected) .. "/" .. tostring(total), function()
        self:SetTooltipClassSpecFilters(className, true)
        self:Refresh()
    end, function()
        self:SetTooltipClassSpecFilters(className, false)
        self:Refresh()
    end)
end

function UI:CreateTooltipSpecsHeader(parent, yOffset)
    local selected, total = self:GetTooltipSpecSelectionCount()
    return self:CreateSettingsActionHeader(parent, yOffset, "Specs in Tooltips", tostring(selected) .. "/" .. tostring(total) .. " selected", function()
        self:SetAllTooltipSpecFilters(true)
        self:Refresh()
    end, function()
        self:SetAllTooltipSpecFilters(false)
        self:Refresh()
    end)
end

function UI:RenderSettingsTab()
    local widgets = BigBiSList.Widgets
    local yOffset = -2
    local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, "Settings", yOffset)
    yOffset = yOffset - headerHeight

    local profile = BigBiSListDB.profile
    BigBiSList:EnsureTooltipSpecFilters()
    local generalSettings = {
        {
            label = "Show minimap button",
            get = function() return not profile.minimap.hide end,
            set = function(value)
                profile.minimap.hide = not value
                if BigBiSList.RefreshMinimapButton then
                    BigBiSList:RefreshMinimapButton()
                end
            end,
        },
        {
            label = "Lock window position",
            get = function() return profile.window.locked end,
            set = function(value) profile.window.locked = value end,
        },
    }
    local tooltipSettings = {
        {
            label = "Show Big BiS List info in item tooltips",
            get = function() return profile.tooltips.enabled end,
            set = function(value) profile.tooltips.enabled = value end,
        },
        {
            label = "Compact tooltip rows by default",
            get = function() return profile.tooltips.compact end,
            set = function(value) profile.tooltips.compact = value end,
        },
        {
            label = "Show selected spec first in tooltips",
            get = function() return profile.tooltips.selectedSpecFirst end,
            set = function(value) profile.tooltips.selectedSpecFirst = value end,
        },
        {
            label = "ALT expands tooltip matches",
            get = function() return profile.tooltips.showAllOnAlt end,
            set = function(value) profile.tooltips.showAllOnAlt = value end,
        },
    }

    local _, generalHeaderHeight = widgets:CreateSectionHeader(self.contentChild, "General", yOffset)
    yOffset = yOffset - generalHeaderHeight
    for _, setting in ipairs(generalSettings) do
        local row, rowHeight = self:CreateSettingToggle(self.contentChild, yOffset, setting.label, setting.get, setting.set)
        yOffset = yOffset - rowHeight - 4
    end

    yOffset = yOffset - 8
    local _, tooltipHeaderHeight = widgets:CreateSectionHeader(self.contentChild, "Tooltip Display", yOffset)
    yOffset = yOffset - tooltipHeaderHeight
    for _, setting in ipairs(tooltipSettings) do
        local row, rowHeight = self:CreateSettingToggle(self.contentChild, yOffset, setting.label, setting.get, setting.set)
        yOffset = yOffset - rowHeight - 4
    end

    local _, tooltipSpecsHeaderHeight = self:CreateTooltipSpecsHeader(self.contentChild, yOffset)
    yOffset = yOffset - tooltipSpecsHeaderHeight

    local specFilters = profile.tooltips.specFilters or {}
    for _, classData in ipairs(BigBiSList:GetDataIndex().classes or {}) do
        local className = classData.name
        if className then
            local currentClassName = className
            local _, classHeaderHeight = self:CreateSettingsClassHeader(self.contentChild, yOffset, currentClassName)
            yOffset = yOffset - classHeaderHeight

            for _, specData in ipairs(classData.specs or {}) do
                local specName = specData.name
                if specName then
                    local currentSpecName = specName
                    local row, rowHeight = self:CreateSettingToggle(self.contentChild, yOffset, currentSpecName, function()
                        return type(specFilters[currentClassName]) == "table" and specFilters[currentClassName][currentSpecName] == true
                    end, function(value)
                        self:SetTooltipSpecFilter(currentClassName, currentSpecName, value)
                    end, 14)
                    yOffset = yOffset - rowHeight - 4
                end
            end
            yOffset = yOffset - 4
        end
    end

    self:SetContentHeight(yOffset)
end

function UI:FindPlannerContext(itemId, detailData)
    local selection = self:GetSelection()
    local wantedSlot = detailData and detailData.slot
    local plannerRows = BigBiSList:GetPlannerRows(selection.class, selection.spec, selection.phase, {})

    for _, row in ipairs(plannerRows) do
        if row.item_id == itemId and (not wantedSlot or row.slot == wantedSlot) then
            return row
        end
    end

    for _, row in ipairs(plannerRows) do
        if row.item_id == itemId then
            return row
        end
    end

    return nil
end

function UI:CreateDetailsTitle(parent, text, r, g, b)
    local frame = CreateFrame("Frame", nil, parent)
    frame:SetPoint("TOPLEFT", parent, "TOPLEFT", 8, -8)
    frame:SetPoint("RIGHT", parent, "RIGHT", -8, 0)

    local label = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    label:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
    label:SetWidth(math.max(120, (parent:GetWidth() or DETAILS_WIDTH) - 16))
    label:SetJustifyH("LEFT")
    label:SetWordWrap(true)
    label:SetText(text or "")
    label:SetTextColor(r or 0.9, g or 0.9, b or 0.9, 1)

    frame:SetHeight(math.max(24, label:GetStringHeight() or 16))
    frame.contentHeight = frame:GetHeight() + 8
    return frame
end

function UI:CreateDetailsText(parent, anchor, titleText, bodyText, bodyR, bodyG, bodyB)
    local block = CreateFrame("Frame", nil, parent)
    block:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -12)
    block:SetPoint("RIGHT", parent, "RIGHT", -8, 0)

    local width = math.max(120, (parent:GetWidth() or DETAILS_WIDTH) - 16)
    local title = block:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    title:SetPoint("TOPLEFT", block, "TOPLEFT", 0, 0)
    title:SetWidth(width)
    title:SetJustifyH("LEFT")
    title:SetWordWrap(false)
    title:SetTextColor(1, 0.82, 0.28, 1)
    title:SetText(titleText)

    local body = block:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    body:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -3)
    body:SetWidth(width)
    body:SetJustifyH("LEFT")
    body:SetWordWrap(true)
    body:SetTextColor(bodyR or 0.76, bodyG or 0.76, bodyB or 0.80, 1)
    body:SetText(bodyText or "")

    local titleHeight = math.max(13, title:GetStringHeight() or 13)
    local bodyHeight = math.max(13, body:GetStringHeight() or 13)
    block:SetHeight(titleHeight + 5 + bodyHeight)
    block.contentHeight = block:GetHeight() + 12
    return block
end

function UI:BuildPhaseUseText(itemId)
    local selection = self:GetSelection()
    local uses = BigBiSList:GetDataIndex().usesByItemId[itemId] or {}
    local parts = {}

    for _, phaseKey in ipairs(BigBiSList:GetPhaseOrder()) do
        local bestUse
        for _, use in ipairs(uses) do
            if use.class == selection.class and use.spec == selection.spec and use.phase == phaseKey then
                if not bestUse or (use.rank_group == "bis" and bestUse.rank_group ~= "bis") then
                    bestUse = use
                end
            end
        end

        if bestUse then
            local tagLabel = displayRankInfo(bestUse)
            table.insert(parts, BigBiSList:GetPhaseDisplayName(phaseKey) .. " " .. tagLabel .. " " .. bestUse.slot)
        end
    end

    if #parts == 0 then
        return "No known use for the current class/spec."
    end

    return table.concat(parts, "\n")
end

function UI:RefreshDetails(itemId, detailData, detailMode)
    local widgets = BigBiSList.Widgets
    local content = self.detailsContent
    widgets:ClearChildren(content)

    if not itemId then
        local label = content:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        label:SetPoint("TOPLEFT", content, "TOPLEFT", 8, -8)
        label:SetPoint("RIGHT", content, "RIGHT", -8, 0)
        label:SetJustifyH("LEFT")
        label:SetWordWrap(true)
        label:SetTextColor(0.72, 0.72, 0.76, 1)
        label:SetText("Select an item to see sources, phase usefulness, and wishlist actions.")
        local minimum = self.detailsScroll and self.detailsScroll:GetHeight() or 1
        content:SetHeight(math.max(80, minimum + 1))
        return
    end

    local entityType = detailData and (detailData.entity_type or (detailData.spell_id and "spell")) or "item"
    local entityId = detailData and (detailData.entity_id or detailData.spell_id or detailData.item_id) or itemId
    local detailItemId = detailData and detailData.item_id or (entityType == "item" and entityId or nil)

    self.selectedItemId = entityId
    self.selectedItemData = detailData
    self.selectedItemMode = detailMode
    local index = BigBiSList:GetDataIndex()
    local item = detailItemId and index.itemsById[detailItemId] or nil
    local plannerContext = detailItemId and (detailData and detailData.priority and detailData or self:FindPlannerContext(detailItemId, detailData)) or nil

    local r, g, b = itemQualityColor(item)
    if entityType == "spell" then
        r, g, b = 1, 0.82, 0.28
    end
    local titleText = (detailData and detailData.name) or (item and item.name) or ((entityType == "spell" and "Spell " or "Item ") .. tostring(entityId))
    local anchor = self:CreateDetailsTitle(content, titleText, r, g, b)
    local contentHeight = anchor.contentHeight or 32

    local recommendationLines = {}
    appendText(recommendationLines, self:GetRowRecommendationText(detailData or plannerContext, detailMode))
    if detailData and detailData.slot then
        local detailPhase = detailData.phase or (detailData.bestUse and detailData.bestUse.phase)
        local selectedPhase = detailPhase and BigBiSList:GetPhaseDisplayName(detailPhase) or BigBiSList:GetPhaseDisplayName(self:GetSelection().phase)
        appendText(recommendationLines, selectedPhase .. " - " .. detailData.slot)
    end

    local ownershipText
    if detailItemId then
        local ownershipState = self:GetOwnershipState(detailItemId, detailData and detailData.item_ids)
        ownershipText = ownershipStateLabel(ownershipState)
        if ownershipState == "bank" and self.currentOwned and self.currentOwned.bankUpdatedAt and self.currentOwned.bankUpdatedAt ~= "" then
            ownershipText = ownershipText .. " - bank cache " .. self.currentOwned.bankUpdatedAt
        elseif ownershipState == "missing" and self.currentOwned and not self.currentOwned.bankScanned then
            ownershipText = ownershipText .. " - open your bank once to include banked items"
        end
        appendText(recommendationLines, "Have: " .. ownershipText)
    elseif detailData and detailData.ownership_state then
        ownershipText = detailData.ownership_label or ownershipStateLabel(detailData.ownership_state)
        if detailData.ownership_detail and detailData.ownership_detail ~= "" then
            ownershipText = ownershipText .. " - " .. detailData.ownership_detail
        end
        appendText(recommendationLines, "Have: " .. ownershipText)
    end

    local accessData = detailData or item or {}
    local requirementData = (accessData and accessData.requirements and #accessData.requirements > 0) and accessData or item
    local accessEvaluation = self:GetAccessEvaluation(accessData)
    appendText(recommendationLines, "Get: " .. self:GetAccessBadgeLabel(accessEvaluation.status, accessData))
    anchor = self:CreateDetailsText(content, anchor, "Recommendation", table.concat(recommendationLines, "\n"), 0.82, 0.86, 0.92)
    contentHeight = contentHeight + anchor.contentHeight

    if detailMode ~= "enhance" then
        anchor = self:CreateDetailsText(content, anchor, "Tag meaning", rankMeaning(detailData or plannerContext, detailMode), 0.76, 0.76, 0.80)
        contentHeight = contentHeight + anchor.contentHeight
    end

    local optionEvaluation = accessEvaluation.optionEvaluation
    local option = optionEvaluation and optionEvaluation.option
    local bestPathText
    if option then
        bestPathText = option.label or "Source"
        if optionEvaluation and (optionEvaluation.status ~= "ready" or (accessData and accessData.ready_access_detail and accessData.ready_access_detail ~= "")) then
            bestPathText = bestPathText .. "\n" .. self:GetAccessHelpText(optionEvaluation, accessData)
        end
    elseif accessData and accessData.ready_access_detail and accessEvaluation.status == "ready" then
        bestPathText = accessData.ready_access_detail
    else
        bestPathText = self:GetAccessHelpText(optionEvaluation, accessData)
    end
    anchor = self:CreateDetailsText(content, anchor, "How to get", bestPathText, 0.76, 0.76, 0.80)
    contentHeight = contentHeight + anchor.contentHeight

    local prerequisitesText
    if optionEvaluation then
        prerequisitesText = self:FormatAccessOptionRequirements(optionEvaluation)
    elseif accessEvaluation.options and #accessEvaluation.options > 0 then
        prerequisitesText = self:FormatAccessOptions(accessEvaluation)
    elseif requirementData and requirementData.requirements and #requirementData.requirements > 0 then
        prerequisitesText = self:FormatRequirements(requirementData)
    else
        prerequisitesText = "No known character requirements."
    end
    anchor = self:CreateDetailsText(content, anchor, "Requirements", prerequisitesText, 0.76, 0.76, 0.80)
    contentHeight = contentHeight + anchor.contentHeight

    local timelineLines = {}
    if plannerContext then
        local score = tostring(plannerContext.priority or 0) .. "/100"
        local tier = plannerContext.priorityTier or "Priority"
        appendText(timelineLines, tier .. " - " .. score)
        appendText(timelineLines, plannerContext.reasons and table.concat(plannerContext.reasons, "\n") or "No planner explanation available.")
        if plannerContext.lastUsefulLabel then
            appendText(timelineLines, "Listed through " .. plannerContext.lastUsefulLabel)
        end
    end

    local availabilityPhase = (detailData and detailData.acquisition_phase)
        or (plannerContext and plannerContext.acquisition_phase)
        or (item and item.acquisition_phase)
    if availabilityPhase then
        appendText(timelineLines, "Available in " .. BigBiSList:GetPhaseDisplayName(availabilityPhase))
    end

    if detailItemId then
        appendText(timelineLines, self:BuildPhaseUseText(detailItemId))
    end
    if #timelineLines > 0 then
        anchor = self:CreateDetailsText(content, anchor, "Phase value", table.concat(timelineLines, "\n"), 0.64, 0.78, 0.94)
        contentHeight = contentHeight + anchor.contentHeight
    end

    local sourceSummary = detailData and detailData.source_summary
    if not sourceSummary or sourceSummary == "" then
        sourceSummary = item and item.source_summary
    end
    if not sourceSummary or sourceSummary == "" then
        sourceSummary = "No source data"
    end
    anchor = self:CreateDetailsText(content, anchor, "Source notes", sourceSummary, 0.76, 0.76, 0.80)
    contentHeight = contentHeight + anchor.contentHeight

    if not detailItemId then
        contentHeight = contentHeight + 16
        local minimum = self.detailsScroll and self.detailsScroll:GetHeight() or 1
        content:SetHeight(math.max(contentHeight, minimum + 1))
        return
    end

    local wishlistKey = tostring(detailItemId)
    local isWishlisted = BigBiSListDB.char.wishlist[wishlistKey]
    local actionRow = CreateFrame("Frame", nil, content)
    actionRow:SetHeight(24)
    actionRow:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -14)
    actionRow:SetPoint("RIGHT", content, "RIGHT", -8, 0)

    local wishlistButton = widgets:CreateTextButton(actionRow, isWishlisted and "Remove wishlist" or "Add wishlist", 132, 24, function()
        if BigBiSListDB.char.wishlist[wishlistKey] then
            self:RemoveWishlist(detailItemId)
        else
            self:AddWishlist(detailItemId)
        end
        self:Refresh()
    end)
    wishlistButton:SetPoint("LEFT", actionRow, "LEFT", 0, 0)

    local ignored = BigBiSListDB.char.ignoredItems[wishlistKey]
    local ignoreButton = widgets:CreateTextButton(actionRow, ignored and "Unignore" or "Ignore", 78, 24, function()
        if BigBiSListDB.char.ignoredItems[wishlistKey] then
            self:UnignoreItem(detailItemId)
        else
            self:IgnoreItem(detailItemId)
        end
    end)
    ignoreButton:SetPoint("LEFT", wishlistButton, "RIGHT", 8, 0)

    contentHeight = contentHeight + 14 + 24 + 16
    local minimum = self.detailsScroll and self.detailsScroll:GetHeight() or 1
    content:SetHeight(math.max(contentHeight, minimum + 1))
end

function UI:RefreshControls()
    local selection = self:GetSelection()
    local filters = self:GetFilters()

    if self.classDropdown then
        self.classDropdown:Refresh()
    end
    if self.specDropdown then
        self.specDropdown:Refresh()
    end
    if self.sourceDropdown then
        self.sourceDropdown:Refresh()
    end
    if self.zoneDropdown then
        self.zoneDropdown:Refresh()
    end
    if self.reputationDropdown then
        self.reputationDropdown:Refresh()
    end
    if self.rankDropdown then
        self.rankDropdown:Refresh()
    end
    if self.ownedDropdown then
        self.ownedDropdown:Refresh()
    end
    if self.boeDropdown then
        self.boeDropdown:Refresh()
    end
    if self.longevityDropdown then
        self.longevityDropdown:Refresh()
    end
    if self.searchBox and self.searchBox:GetText() ~= (filters.search or "") then
        self.searchBox:SetText(filters.search or "")
    end

    local r, g, b = classColor(selection.class)
    if self.accentBar then
        self.accentBar:SetColorTexture(r, g, b, 0.92)
    end

    safeSetText(self.summaryText, selection.class .. " " .. selection.spec .. " - " .. BigBiSList:GetPhaseDisplayName(selection.phase))
    safeSetText(self.statusText, selection.class .. " / " .. selection.spec .. " / " .. BigBiSList:GetPhaseDisplayName(selection.phase))

    for phaseKey, button in pairs(self.phaseButtons or {}) do
        button:SetSelected(phaseKey == selection.phase)
    end

    local selectedTab = normalizeTabName(selection.tab)
    for tabName, button in pairs(self.tabButtons or {}) do
        button:SetSelected(tabName == selectedTab)
    end

    for slotName, button in pairs(self.slotButtons or {}) do
        button:SetSelected(filters.slots and filters.slots[slotName])
    end

end

function UI:Refresh()
    if not self.frame then
        return
    end

    self:ValidateSelection()
    self:ValidateZoneFilter()
    self:ValidateReputationFilter()
    self:RefreshControls()
    self.currentOwned = self:BuildOwnedItems()
    self.currentAccess = self:BuildAccessState()

    BigBiSList.Widgets:ClearChildren(self.contentChild)
    self.contentChild:SetHeight(1)

    local tabName = normalizeTabName(self:GetSelection().tab)
    if tabName == "Equipped" then
        self:RenderGearTab()
    elseif tabName == "Upgrades" then
        self:RenderPlannerTab()
    elseif tabName == "Enhance" then
        self:RenderEnhanceTab()
    elseif tabName == "Wishlist" then
        self:RenderWishlistTab()
    elseif tabName == "Settings" then
        self:RenderSettingsTab()
    elseif tabName == "By Slot" then
        self:RenderPhaseTab()
    else
        self:RenderPlannerTab()
    end

    self:RefreshDetails(self.selectedItemId, self.selectedItemData, self.selectedItemMode)
end

function UI:CreateHeader(frame)
    local widgets = BigBiSList.Widgets

    self.accentBar = frame:CreateTexture(nil, "ARTWORK")
    self.accentBar:SetPoint("TOPLEFT", frame, "TOPLEFT", 1, -1)
    self.accentBar:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -1, -1)
    self.accentBar:SetHeight(3)

    local titleBar = CreateFrame("Frame", nil, frame)
    titleBar:SetHeight(38)
    titleBar:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, -3)
    titleBar:SetPoint("TOPRIGHT", frame, "TOPRIGHT", 0, -3)
    titleBar:EnableMouse(true)
    titleBar:RegisterForDrag("LeftButton")
    titleBar:SetScript("OnDragStart", function()
        if not BigBiSListDB.profile.window.locked then
            frame:StartMoving()
        end
    end)
    titleBar:SetScript("OnDragStop", function()
        frame:StopMovingOrSizing()
        self:SaveWindow()
    end)

    local title = titleBar:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    title:SetPoint("LEFT", titleBar, "LEFT", 14, 0)
    title:SetText(BigBiSList.displayName)

    self.summaryText = titleBar:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    self.summaryText:SetPoint("LEFT", title, "RIGHT", 16, -1)
    self.summaryText:SetPoint("RIGHT", titleBar, "RIGHT", -80, 0)
    self.summaryText:SetJustifyH("LEFT")
    self.summaryText:SetWordWrap(false)
    self.summaryText:SetTextColor(0.68, 0.68, 0.72, 1)

    local closeButton = CreateFrame("Button", nil, titleBar, "UIPanelCloseButton")
    closeButton:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -2, -2)
    closeButton:SetScript("OnClick", function()
        BigBiSList:CloseMainFrame()
    end)

    self.titleBar = titleBar
end

function UI:CreatePhaseBar(frame)
    local widgets = BigBiSList.Widgets
    local phaseBar = CreateFrame("Frame", nil, frame)
    phaseBar:SetHeight(34)
    phaseBar:SetPoint("TOPLEFT", self.titleBar, "BOTTOMLEFT", 12, -4)
    phaseBar:SetPoint("TOPRIGHT", self.titleBar, "BOTTOMRIGHT", -12, -4)

    self.phaseButtons = {}
    local previous
    for _, phaseKey in ipairs(BigBiSList:GetPhaseOrder()) do
        local button = widgets:CreateTextButton(phaseBar, BigBiSList:GetPhaseDisplayName(phaseKey), 96, 24, function()
            self:SetPhase(phaseKey)
        end)
        if previous then
            button:SetPoint("LEFT", previous, "RIGHT", 6, 0)
        else
            button:SetPoint("LEFT", phaseBar, "LEFT", 0, 0)
        end
        self.phaseButtons[phaseKey] = button
        previous = button
    end

    self.phaseBar = phaseBar
end

function UI:CreateTabBar(frame)
    local widgets = BigBiSList.Widgets
    local tabBar = CreateFrame("Frame", nil, frame)
    tabBar:SetHeight(30)
    tabBar:SetPoint("TOPLEFT", self.phaseBar, "BOTTOMLEFT", 0, -2)
    tabBar:SetPoint("TOPRIGHT", self.phaseBar, "BOTTOMRIGHT", 0, -2)

    self.tabButtons = {}
    local previous
    for _, tabName in ipairs(TAB_NAMES) do
        local button = widgets:CreateTextButton(tabBar, TAB_DISPLAY_LABELS[tabName] or tabName, 100, 24, function()
            self:SetTab(tabName)
        end)
        if previous then
            button:SetPoint("LEFT", previous, "RIGHT", 6, 0)
        else
            button:SetPoint("LEFT", tabBar, "LEFT", 0, 0)
        end
        self.tabButtons[tabName] = button
        previous = button
    end

    self.tabBar = tabBar
end

function UI:CreateLeftRail(body)
    local widgets = BigBiSList.Widgets
    local rail = widgets:CreatePanel(nil, body, { 0.055, 0.055, 0.065, 0.94 }, { 0.18, 0.18, 0.20, 1 })
    rail:SetWidth(LEFT_RAIL_WIDTH)
    rail:SetPoint("TOPLEFT", body, "TOPLEFT", 0, 0)
    rail:SetPoint("BOTTOMLEFT", body, "BOTTOMLEFT", 0, 0)

    local header = rail:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    header:SetPoint("TOPLEFT", rail, "TOPLEFT", LEFT_RAIL_INSET, -10)
    header:SetText("Filters")

    self.classDropdown = widgets:CreateDropdown("BigBiSListClassDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function() return self:GetSelection().class or "Class" end,
        function() return self:GetClassDropdownItems() end,
        function(value) self:SetClass(value) end)
    self.classDropdown:SetPoint("TOPLEFT", rail, "TOPLEFT", LEFT_DROPDOWN_X, -42)

    self.specDropdown = widgets:CreateDropdown("BigBiSListSpecDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function() return self:GetSelection().spec or "Spec" end,
        function() return self:GetSpecDropdownItems() end,
        function(value) self:SetSpec(value) end)
    self.specDropdown:SetPoint("TOPLEFT", self.classDropdown, "BOTTOMLEFT", 0, -4)

    local searchLabel = rail:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    searchLabel:SetPoint("TOPLEFT", self.specDropdown, "BOTTOMLEFT", LEFT_RAIL_INSET - LEFT_DROPDOWN_X, -12)
    searchLabel:SetTextColor(0.68, 0.68, 0.72, 1)
    searchLabel:SetText("Search")

    local searchFrame = widgets:CreatePanel(nil, rail, { 0.030, 0.040, 0.040, 0.95 }, { 0.42, 0.42, 0.48, 1 })
    searchFrame:SetSize(LEFT_CONTROL_WIDTH, 24)
    searchFrame:SetPoint("TOPLEFT", searchLabel, "BOTTOMLEFT", 0, -5)

    self.searchBox = CreateFrame("EditBox", "BigBiSListSearchBox", searchFrame)
    self.searchBox:SetPoint("LEFT", searchFrame, "LEFT", 8, 0)
    self.searchBox:SetPoint("RIGHT", searchFrame, "RIGHT", -8, 0)
    self.searchBox:SetHeight(20)
    self.searchBox:SetAutoFocus(false)
    self.searchBox:SetMaxLetters(48)
    self.searchBox:SetFontObject("GameFontHighlightSmall")
    self.searchBox:SetScript("OnTextChanged", function(editBox, isUserInput)
        if isUserInput then
            self:GetFilters().search = trim(editBox:GetText())
            self:Refresh()
        end
    end)
    self.searchBox:SetScript("OnEscapePressed", function(editBox)
        if editBox:GetText() ~= "" then
            editBox:SetText("")
            self:GetFilters().search = ""
            self:Refresh()
        end
        editBox:ClearFocus()
    end)
    self.searchBox:SetScript("OnEnterPressed", function(editBox)
        editBox:ClearFocus()
    end)

    self.sourceDropdown = widgets:CreateDropdown("BigBiSListSourceDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function()
            local value = self:GetFilters().sourceType or "all"
            return (BigBiSList:GetSourceTypeLabels()[value] or value)
        end,
        function() return self:GetSourceDropdownItems() end,
        function(value) self:SetFilter("sourceType", value) end)
    self.sourceDropdown:SetPoint("TOPLEFT", searchFrame, "BOTTOMLEFT", LEFT_DROPDOWN_X - LEFT_RAIL_INSET, -10)

    self.zoneDropdown = widgets:CreateDropdown("BigBiSListZoneDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function()
            local value = self:GetFilters().zone or "all"
            return value == "all" and "All zones" or value
        end,
        function() return self:GetZoneDropdownItems() end,
        function(value) self:SetFilter("zone", value) end)
    self.zoneDropdown:SetPoint("TOPLEFT", self.sourceDropdown, "BOTTOMLEFT", 0, -4)

    self.reputationDropdown = widgets:CreateDropdown("BigBiSListReputationDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function()
            local value = self:GetFilters().reputation or "all"
            return value == "all" and "All reps" or value
        end,
        function() return self:GetReputationDropdownItems() end,
        function(value) self:SetFilter("reputation", value) end)
    self.reputationDropdown:SetPoint("TOPLEFT", self.zoneDropdown, "BOTTOMLEFT", 0, -4)

    self.rankDropdown = widgets:CreateDropdown("BigBiSListRankDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function()
            return "Tag: " .. rankFilterLabel(self:GetFilters().rankGroup)
        end,
        function() return self:GetRankDropdownItems() end,
        function(value) self:SetFilter("rankGroup", value) end)
    self.rankDropdown:SetPoint("TOPLEFT", self.reputationDropdown, "BOTTOMLEFT", 0, -8)

    self.ownedDropdown = widgets:CreateDropdown("BigBiSListOwnedDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function()
            return "Owned: " .. ownedFilterLabel(self:GetFilters().ownedState)
        end,
        function() return self:GetOwnedDropdownItems() end,
        function(value) self:SetFilter("ownedState", value) end)
    self.ownedDropdown:SetPoint("TOPLEFT", self.rankDropdown, "BOTTOMLEFT", 0, -4)

    self.boeDropdown = widgets:CreateDropdown("BigBiSListBoeDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function()
            return "BoE: " .. boeFilterLabel(self:GetFilters().boe)
        end,
        function() return self:GetBoeDropdownItems() end,
        function(value) self:SetFilter("boe", value) end)
    self.boeDropdown:SetPoint("TOPLEFT", self.ownedDropdown, "BOTTOMLEFT", 0, -4)

    self.longevityDropdown = widgets:CreateDropdown("BigBiSListLongevityDropdown", rail, LEFT_DROPDOWN_WIDTH,
        function()
            return "Usefulness: " .. longevityFilterLabel(self:GetFilters().longevity)
        end,
        function() return self:GetLongevityDropdownItems() end,
        function(value) self:SetFilter("longevity", value) end)
    self.longevityDropdown:SetPoint("TOPLEFT", self.boeDropdown, "BOTTOMLEFT", 0, -4)

    local slotHeader = rail:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    slotHeader:SetPoint("TOPLEFT", self.longevityDropdown, "BOTTOMLEFT", LEFT_RAIL_INSET - LEFT_DROPDOWN_X, -16)
    slotHeader:SetTextColor(0.68, 0.68, 0.72, 1)
    slotHeader:SetText("Slots")

    local clearButton = widgets:CreateTextButton(rail, "Clear filters", LEFT_CONTROL_WIDTH, 24, function()
        self:ClearFilters()
    end)
    clearButton:SetPoint("BOTTOMLEFT", rail, "BOTTOMLEFT", LEFT_RAIL_INSET, 10)

    local slotsScroll = CreateFrame("ScrollFrame", "BigBiSListSlotScroll", rail)
    slotsScroll:SetPoint("TOPLEFT", slotHeader, "BOTTOMLEFT", 0, -8)
    slotsScroll:SetPoint("BOTTOMRIGHT", clearButton, "TOPRIGHT", 0, 8)
    slotsScroll:EnableMouseWheel(true)
    slotsScroll:SetScript("OnMouseWheel", function(scroll, delta)
        local maxScroll = scroll:GetVerticalScrollRange() or 0
        local nextScroll = (scroll:GetVerticalScroll() or 0) - (delta * LEFT_SLOT_ROW_HEIGHT)
        scroll:SetVerticalScroll(clamp(nextScroll, 0, maxScroll))
    end)

    local slotsContent = CreateFrame("Frame", nil, slotsScroll)
    slotsContent:SetWidth(LEFT_CONTROL_WIDTH)
    slotsContent:SetHeight(1)
    slotsScroll:SetScrollChild(slotsContent)

    self.slotButtons = {}
    local slotFilters = BigBiSList:GetDisplaySlotFilters()
    for index, slotFilter in ipairs(slotFilters) do
        local button = widgets:CreateTextButton(slotsContent, slotFilter.label, LEFT_SLOT_BUTTON_WIDTH, 20, function()
            self:ToggleSlot(slotFilter.key)
        end)
        local col = (index - 1) % 2
        local row = math.floor((index - 1) / 2)
        button:SetPoint("TOPLEFT", slotsContent, "TOPLEFT", col * (LEFT_SLOT_BUTTON_WIDTH + LEFT_SLOT_GAP), -row * LEFT_SLOT_ROW_HEIGHT)
        self.slotButtons[slotFilter.key] = button
    end
    slotsContent:SetHeight(math.max(1, math.ceil(#slotFilters / 2) * LEFT_SLOT_ROW_HEIGHT))

    self.leftRail = rail
    self.slotsScroll = slotsScroll
end

function UI:CreateBody(frame)
    local widgets = BigBiSList.Widgets
    local body = CreateFrame("Frame", nil, frame)
    body:SetPoint("TOPLEFT", self.tabBar, "BOTTOMLEFT", 0, -4)
    body:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -12, 34)

    self:CreateLeftRail(body)

    local details = widgets:CreatePanel(nil, body, { 0.055, 0.055, 0.065, 0.94 }, { 0.18, 0.18, 0.20, 1 })
    details:SetWidth(DETAILS_WIDTH)
    details:SetPoint("TOPRIGHT", body, "TOPRIGHT", 0, 0)
    details:SetPoint("BOTTOMRIGHT", body, "BOTTOMRIGHT", 0, 0)

    local detailsTitle = details:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    detailsTitle:SetPoint("TOPLEFT", details, "TOPLEFT", 10, -10)
    detailsTitle:SetText("Details")

    local detailsScroll, detailsContent = widgets:CreateScrollFrame("BigBiSListDetailsScroll", details)
    detailsScroll:SetPoint("TOPLEFT", detailsTitle, "BOTTOMLEFT", -2, -8)
    detailsScroll:SetPoint("BOTTOMRIGHT", details, "BOTTOMRIGHT", -28, 8)
    self.details = details
    self.detailsScroll = detailsScroll
    self.detailsContent = detailsContent

    local contentPanel = widgets:CreatePanel(nil, body, { 0.035, 0.035, 0.042, 0.94 }, { 0.15, 0.15, 0.17, 1 })
    contentPanel:SetPoint("TOPLEFT", self.leftRail, "TOPRIGHT", 8, 0)
    contentPanel:SetPoint("BOTTOMRIGHT", details, "BOTTOMLEFT", -8, 0)

    self.contentScroll, self.contentChild = widgets:CreateScrollFrame("BigBiSListContentScroll", contentPanel)
    self.contentScroll:SetPoint("TOPLEFT", contentPanel, "TOPLEFT", 8, -8)
    self.contentScroll:SetPoint("BOTTOMRIGHT", contentPanel, "BOTTOMRIGHT", -28, 8)

    self.body = body
end

function UI:CreateStatusBar(frame)
    local widgets = BigBiSList.Widgets
    local status = widgets:CreatePanel(nil, frame, { 0.060, 0.060, 0.068, 0.95 }, { 0.18, 0.18, 0.20, 1 })
    status:SetHeight(26)
    status:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 1, 1)
    status:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -1, 1)

    self.statusText = status:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    self.statusText:SetPoint("LEFT", status, "LEFT", 10, 0)
    self.statusText:SetPoint("RIGHT", status, "RIGHT", -34, 0)
    self.statusText:SetJustifyH("LEFT")
    self.statusText:SetTextColor(0.62, 0.62, 0.66, 1)

    local resize = CreateFrame("Button", nil, status)
    resize:SetSize(16, 16)
    resize:SetPoint("RIGHT", status, "RIGHT", -7, 0)
    resize:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    resize:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
    resize:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
    resize:SetScript("OnMouseDown", function(_, buttonName)
        if buttonName == "LeftButton" and not BigBiSListDB.profile.window.locked then
            self:ApplyResizeBounds()
            frame:StartSizing("BOTTOMRIGHT")
        end
    end)
    resize:SetScript("OnMouseUp", function()
        frame:StopMovingOrSizing()
        self:SaveWindow()
        self:Refresh()
    end)
end

function UI:CreateMainFrame()
    BigBiSList:EnsureDatabase()
    self:ValidateSelection()

    local widgets = BigBiSList.Widgets
    local frame = widgets:CreatePanel("BigBiSListMainFrame", UIParent, { 0.035, 0.035, 0.042, 0.98 }, { 0.20, 0.20, 0.22, 1 })
    frame:SetFrameStrata("DIALOG")
    frame:SetToplevel(true)
    frame:SetMovable(true)
    frame:SetResizable(true)
    frame:EnableMouse(true)
    frame:SetClampedToScreen(true)

    ensureSpecialFrame("BigBiSListMainFrame")

    self.frame = frame
    self:ApplyResizeBounds()
    self:RestoreWindow()
    self:CreateHeader(frame)
    self:CreatePhaseBar(frame)
    self:CreateTabBar(frame)
    self:CreateBody(frame)
    self:CreateStatusBar(frame)

    frame:SetScript("OnHide", function()
        self:SaveWindow()
    end)
    frame:SetScript("OnShow", function()
        self:ApplyResizeBounds()
    end)

    self:Refresh()
    return frame
end

function UI:Open()
    if not self.frame then
        self:CreateMainFrame()
    end

    self:ApplyResizeBounds()
    self.frame:Show()
    self:Refresh()
end

function UI:Close()
    if self.frame then
        self:SaveWindow()
        self.frame:Hide()
    end
end

function BigBiSList:OpenMainFrame()
    self.UI:Open()
end

function BigBiSList:CloseMainFrame()
    self.UI:Close()
end

function BigBiSList:ToggleMainFrame()
    if self.UI.frame and self.UI.frame:IsShown() then
        self:CloseMainFrame()
    else
        self:OpenMainFrame()
    end
end

function BigBiSList:RefreshUI()
    if self.UI and self.UI.frame and self.UI.frame:IsShown() then
        self.UI:Refresh()
    end
end

function BigBiSList:InitUIEvents()
    if self.uiEventFrame then
        return
    end

    local frame = CreateFrame("Frame")
    frame:RegisterEvent("PLAYER_EQUIPMENT_CHANGED")
    frame:RegisterEvent("BAG_UPDATE_DELAYED")
    frame:RegisterEvent("PLAYER_ENTERING_WORLD")
    frame:RegisterEvent("BANKFRAME_OPENED")
    frame:RegisterEvent("PLAYERBANKSLOTS_CHANGED")
    frame:SetScript("OnEvent", function(_, event)
        if event == "BANKFRAME_OPENED"
            or event == "PLAYERBANKSLOTS_CHANGED"
            or (event == "BAG_UPDATE_DELAYED" and BankFrame and BankFrame:IsShown()) then
            self.UI:ScanBankItems()
        end
        self:RefreshUI()
    end)
    self.uiEventFrame = frame
end
