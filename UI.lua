local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local UI = {}
BigBiSList.UI = UI

local function accountDB()
    if BigBiSList.isForever then return BigBiSList:GetAccountDB() end
    return BigBiSListDB
end

local LEVELING_PHASE_KEY = BigBiSList.levelingPhaseKey or "LEVELING"
local MAX_LEVELING_LEVEL = BigBiSList.maxLevelingLevel or 69
local ENDGAME_TAB_NAMES = BigBiSList.isForever and { "Upgrades", "By Slot", "Equipped", "Builds", "Wishlist" }
    or { "Upgrades", "By Slot", "Equipped", "Enhance", "Wishlist" }
local LEVELING_TAB_NAMES = { "Gear Guide", "Equipped", "Wishlist" }
local TAB_NAMES = { "Upgrades", "By Slot", "Gear Guide", "Equipped", "Enhance", "Wishlist", "Settings" }
if BigBiSList.isForever then
    table.insert(LEVELING_TAB_NAMES, 3, "Builds")
    table.insert(TAB_NAMES, 5, "Builds")
end
local TAB_NAME_ALIASES = {
    Phase = "By Slot",
    ["BiS List"] = "By Slot",
    Gear = "Equipped",
    ["My Gear"] = "Equipped",
    Planner = "Upgrades",
    Enhancements = "Enhance",
    Leveling = "Gear Guide",
}
local TAB_DISPLAY_LABELS = {
    ["By Slot"] = "BiS List",
    Equipped = "My Gear",
    Enhance = "Enhancements",
}
local MIN_WIDTH = 1020
local MIN_HEIGHT = 560
local DEFAULT_WIDTH = 1160
local DEFAULT_HEIGHT = 660
local DETAILS_WIDTH = 320
local CONTEXT_BAR_HEIGHT = 34
local TOOLBAR_HEIGHT = 34
local FILTER_DRAWER_HEIGHT = 104
local ROW_HEIGHT = 56
local RESIZE_SCREEN_MARGIN = 0
local COLUMN_HEADER_HEIGHT = 22
local COLUMN_GAP = 8
local RANK_COLUMN_WIDTH = 96
local HAVE_COLUMN_WIDTH = 96
local GET_COLUMN_WIDTH = 122
local ROW_HORIZONTAL_PADDING = 8
local ROW_VERTICAL_PADDING = 8
local ROW_ICON_SIZE = 32
local LIST_ROW_HEIGHT = 56
local LIST_ROW_GAP = 0
local LIST_SECTION_GAP = 6
local LIST_OVERSCAN_PIXELS = 120
local SEARCH_DEBOUNCE_SECONDS = 0.12
local LAYOUT_WIDTH_EPSILON = 0.5
local TABLE_WIDE_BREAKPOINT = 960

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

local OWNERSHIP_PRIORITY = {
    missing = 0,
    bank = 1,
    bag = 2,
    equipped = 3,
}

local ENHANCEMENT_LOCATION_SORT = {
    equipped = 1,
    bag = 2,
    bank = 3,
}

local EQUIP_LOCATION_ENHANCEMENT_SLOTS = {
    INVTYPE_HEAD = { "Head" },
    INVTYPE_SHOULDER = { "Shoulder" },
    INVTYPE_CLOAK = { "Back" },
    INVTYPE_CHEST = { "Chest" },
    INVTYPE_ROBE = { "Chest" },
    INVTYPE_WRIST = { "Wrist" },
    INVTYPE_HAND = { "Hands" },
    INVTYPE_WAIST = { "Waist" },
    INVTYPE_LEGS = { "Legs" },
    INVTYPE_FEET = { "Feet" },
    INVTYPE_FINGER = { "Ring" },
    INVTYPE_WEAPON = { "Main Hand", "Off Hand", "Dual Wield" },
    INVTYPE_WEAPONMAINHAND = { "Main Hand" },
    INVTYPE_WEAPONOFFHAND = { "Off Hand", "Dual Wield" },
    INVTYPE_2HWEAPON = { "Main Hand", "Two Hand" },
    INVTYPE_SHIELD = { "Off Hand" },
    INVTYPE_HOLDABLE = { "Off Hand" },
    INVTYPE_RANGED = { "Ranged" },
    INVTYPE_RANGEDRIGHT = { "Ranged" },
    INVTYPE_THROWN = { "Ranged" },
}

local EQUIP_LOCATION_SLOT_LABELS = {
    INVTYPE_HEAD = "Head",
    INVTYPE_SHOULDER = "Shoulder",
    INVTYPE_CLOAK = "Back",
    INVTYPE_CHEST = "Chest",
    INVTYPE_ROBE = "Chest",
    INVTYPE_WRIST = "Wrist",
    INVTYPE_HAND = "Hands",
    INVTYPE_WAIST = "Waist",
    INVTYPE_LEGS = "Legs",
    INVTYPE_FEET = "Feet",
    INVTYPE_FINGER = "Ring",
    INVTYPE_WEAPON = "Weapon",
    INVTYPE_WEAPONMAINHAND = "Main Hand",
    INVTYPE_WEAPONOFFHAND = "Off Hand",
    INVTYPE_2HWEAPON = "Two Hand",
    INVTYPE_SHIELD = "Off Hand",
    INVTYPE_HOLDABLE = "Off Hand",
    INVTYPE_RANGED = "Ranged",
    INVTYPE_RANGEDRIGHT = "Ranged",
    INVTYPE_THROWN = "Ranged",
}

local ACCESS_LABELS = {
    ready = "Available now",
    quest_completed = "Quest completed",
    ready_alternate = "Available through another source",
    future = "Future phase",
    needs_rep = "Reputation required",
    needs_profession = "Profession required",
    needs_recipe = "Recipe required",
    check_prereq = "Requirements",
    unknown = "Unknown",
}

local ACCESS_BADGE_LABELS = {
    ready = "Available",
    quest_completed = "Completed",
    ready_alternate = "Available",
    future = "Future",
    needs_rep = "Reputation",
    needs_profession = "Profession",
    needs_recipe = "Recipe",
    check_prereq = "Requirements",
    unknown = "Unknown",
}

local ACCESS_DETAIL_LABELS = {
    ready = "Available now",
    quest_completed = "Quest reward unavailable",
    ready_alternate = "Available through another source",
    future = "Future phase",
    needs_rep = "Reputation required",
    needs_profession = "Profession required",
    needs_recipe = "Recipe required",
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
    trainer = "Trainer",
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
    future = { 0.10, 0.16, 0.26, 0.96, 0.48, 0.70, 0.96, 1 },
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
    all = "All ranks",
    bis = "BiS only",
    ranked = BigBiSList.isForever and "Alternatives" or "Alts only",
    situational = "Sidegrades",
    pvp = "PvP only",
    unrealistic = "Hard to obtain",
    option = "Optional",
}
local RANK_FILTER_ORDER = { "all", "bis", "ranked", "situational", "pvp", "unrealistic", "option" }
local LEVELING_RANK_FILTER_LABELS = {
    all = "All recommendation categories",
    leveling_recommended = "Recommended",
    leveling_tank_pick = "Tank pick",
    leveling_damage_focused = "Damage-focused",
    leveling_healing_focused = "Healing-focused",
}
local LEVELING_RANK_FILTER_ORDER = { "all", "leveling_recommended", "leveling_tank_pick", "leveling_damage_focused", "leveling_healing_focused" }

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
    current = "Selected tier",
    future = "Later recommendations",
    long = "Beyond the next tier",
}
local LONGEVITY_FILTER_ORDER = { "all", "current", "future", "long" }

local UPGRADE_MODE_LABELS = {
    actual = "Upgrade candidates",
    candidates = "Upgrade candidates",
    higher_rated = "Higher guide rating",
    all = "All recommendations",
}
local UPGRADE_MODE_ORDER = { "candidates", "higher_rated", "all" }

local COST_FILTER_LABELS = {
    badge_justice = "Badge of Justice",
    arena_points = "Arena Points",
    honor_points = "Honor Points",
    battleground_marks = "Battleground Marks",
    tier_tokens = "Tier Tokens",
    sunmote = "Sunmote",
    other_turnins = "Other turn-ins",
}

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
    leveling = { 0.11, 0.22, 0.20, 0.96, 0.46, 0.86, 0.76, 1 },
}

local PLANNER_TIER_SECTIONS = {
    { key = "chase_first", title = "Best in slot now" },
    { key = "strong_targets", title = "Future best in slot" },
    { key = "useful_backups", title = "Alternatives" },
    { key = "only_if_easy", title = "Optional" },
}
local FOREVER_PLANNER_SECTION_TITLES = {
    ["Best in slot now"] = "Top targets",
    ["Future best in slot"] = "Plan ahead",
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

local function rankLabelIsGeneric(label)
    local normalized = lower(trim(label))
    return normalized == "" or normalized == "bis" or normalized == "best" or normalized == "best in slot"
end

local function bisVariantLabel(data)
    if not data or data.rank_group ~= "bis" then
        return nil
    end

    local label = lower(data.rank_label)
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

local function listContains(list, value)
    for _, item in ipairs(list or {}) do
        if item == value then
            return true
        end
    end
    return false
end

local function tableHasAnyEnabled(values)
    if type(values) ~= "table" then
        return false
    end

    for _, selected in pairs(values) do
        if selected then
            return true
        end
    end
    return false
end

local function selectedValuesCount(values)
    local count = 0
    if type(values) ~= "table" then
        return count
    end

    for _, selected in pairs(values) do
        if selected then
            count = count + 1
        end
    end
    return count
end

local function firstSelectedValue(values)
    if type(values) ~= "table" then
        return nil
    end

    for value, selected in pairs(values) do
        if selected then
            return value
        end
    end
    return nil
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
        local label = BigBiSList.isForever and BigBiSList:GetGuideRatingDisplay(data.display_rank_label) or data.display_rank_label
        return label, data.display_rank_kind or "backup"
    end

    if mode == "leveling" then
        return data and data.level_label or "Recommended", "leveling"
    elseif mode == "enhance" then
        return "Enhancement", "enhance"
    elseif mode == "wishlist" and data and data.priorityTier then
        return data.priorityTier, data.recommendation_tier or "only_if_easy"
    elseif not data then
        return "Optional", "backup"
    end

    local rank = tonumber(data.rank)
    if data.rank_group == "bis" then
        local variant = bisVariantLabel(data)
        return variant and ("BiS: " .. variant) or "BiS", "best"
    elseif data.rank_group == "ranked" then
        return BigBiSList.isForever and "Alternative" or "Alt", "ranked"
    elseif data.rank_group == "situational" then
        return "Sidegrade", "situational"
    elseif data.rank_group == "pvp" then
        return "PvP", "pvp"
    elseif data.rank_group == "unrealistic" then
        return "Hard", "hard"
    elseif rank and rank > 1 then
        return BigBiSList.isForever and "Alternative" or "Alt", "ranked"
    end

    return "Optional", "backup"
end

local function rankMeaning(data, mode)
    local label, kind = displayRankInfo(data, mode)
    if kind == "best" then
        if data and data.rank_label and not rankLabelIsGeneric(data.rank_label) and data.rank_label ~= label then
            return label .. ": " .. data.rank_label .. " source recommendation."
        end
        return label .. ": best-in-slot item for this slot and phase."
    elseif kind == "ranked" then
        return label .. ": ranked alternative below the best-in-slot choice."
    elseif kind == "situational" then
        return label .. ": useful for a specific fight, role, or gearing setup."
    elseif kind == "pvp" then
        return label .. ": PvP-sourced or PvP-focused item."
    elseif kind == "hard" then
        return label .. ": strong item with unusually difficult access."
    elseif kind == "chase_first" then
        return BigBiSList.isForever and (label .. " · Highest upgrade priority") or (label .. ": highest-priority available upgrade.")
    elseif kind == "strong_targets" then
        return BigBiSList.isForever and (label .. " · Priority from current and later guide ratings")
            or (label .. ": available now with later best-in-slot value.")
    elseif kind == "useful_backups" then
        return label .. ": worthwhile alt or sidegrade pickup."
    elseif kind == "enhance" then
        return label .. ": gem, enchant, or consumable recommendation."
    elseif kind == "leveling" then
        return label .. ": guide-backed leveling recommendation."
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

function UI:GetTableViewportWidth(parent, fallback)
    local width = self.contentScroll and self.contentScroll.GetWidth and self.contentScroll:GetWidth()
    if not width or width <= 1 then
        width = parent and parent.GetWidth and parent:GetWidth()
    end
    if not width or width <= 1 then
        width = fallback or 560
    end
    return math.max(260, width - 4)
end

local function columnDefinition(key, label, minWidth, preferredWidth, maxWidth, growWeight, options)
    local definition = {
        key = key,
        label = label,
        minWidth = minWidth,
        preferredWidth = preferredWidth,
        maxWidth = maxWidth,
        growWeight = growWeight or 0,
    }
    for optionKey, value in pairs(options or {}) do
        definition[optionKey] = value
    end
    return definition
end

local function fixedColumn(key, label, width, options)
    return columnDefinition(key, label, width, width, width, 0, options)
end

local TABLE_COLUMN_CONFIG = {}
for _, mode in ipairs({ "planner", "phase", "leveling", "enhance", "wishlist" }) do
    local valueKey = mode == "phase" and "rank" or (mode == "wishlist" and "expansion" or "value")
    local valueLabel = ({ phase = "Recommendation", planner = "Recommendation", wishlist = "Recommendation", leveling = "Level / benefit" })[mode] or "Benefit"
    if BigBiSList.isForever and (mode == "phase" or mode == "leveling") then
        valueKey, valueLabel = "stat_rank", "Stat rank"
    end
    TABLE_COLUMN_CONFIG[mode] = {
        wide = {
            columnDefinition("item", mode == "enhance" and "Enhancement" or "Item", 220, 300, 480, 8),
            columnDefinition(valueKey, valueLabel, 115, 160, 220, 3),
            columnDefinition("acquisition", "Source", 240, 350, 520, 7),
            fixedColumn("owned", mode == "enhance" and "Applied / owned" or "Owned", mode == "enhance" and 112 or 88),
            fixedColumn("action", "", 28),
        },
        compact = {
            columnDefinition("item", mode == "enhance" and "Enhancement" or "Item", 195, 280, 440, 8),
            columnDefinition(valueKey, valueLabel, 96, 136, 190, 3),
            columnDefinition("acquisition", "Source", 152, 220, 320, 5),
            fixedColumn("owned", mode == "enhance" and "Applied / owned" or "Owned", mode == "enhance" and 112 or 88),
            fixedColumn("action", "", 28),
        },
    }
end
function UI:GetViewColumnDefinitions(mode, compact)
    local config = TABLE_COLUMN_CONFIG[mode] or TABLE_COLUMN_CONFIG.phase
    return compact and config.compact or config.wide
end

local function growColumnWidths(columns, targetKey, remaining)
    while remaining > 0 do
        local active = {}
        local totalWeight = 0
        for _, column in ipairs(columns) do
            local target = tonumber(column[targetKey]) or column.width
            local capacity = math.max(0, target - column.width)
            local weight = math.max(0, tonumber(column.growWeight) or 0)
            if capacity > 0 and weight > 0 then
                local entry = {
                    column = column,
                    capacity = capacity,
                    weight = weight,
                }
                active[#active + 1] = entry
                totalWeight = totalWeight + weight
            end
        end
        if #active == 0 or totalWeight <= 0 then
            break
        end

        local granted = 0
        local cycleRemaining = remaining
        for _, entry in ipairs(active) do
            local exact = (cycleRemaining * entry.weight) / totalWeight
            local whole = math.floor(exact)
            entry.grant = math.min(entry.capacity, whole)
            granted = granted + entry.grant
        end

        local remainderPixels = remaining - granted
        for _, entry in ipairs(active) do
            if remainderPixels <= 0 then
                break
            elseif entry.grant < entry.capacity then
                entry.grant = entry.grant + 1
                granted = granted + 1
                remainderPixels = remainderPixels - 1
            end
        end
        if granted <= 0 then
            break
        end

        for _, entry in ipairs(active) do
            entry.column.width = entry.column.width + entry.grant
        end
        remaining = remaining - granted
    end
    return remaining
end

function UI:GetTableColumnLayout(width, mode, forceCompact)
    width = tonumber(width) or 760
    local usable = math.max(260, math.floor(width - (ROW_HORIZONTAL_PADDING * 2)))
    local compact = forceCompact or usable < TABLE_WIDE_BREAKPOINT
    local normalizedMode = TABLE_COLUMN_CONFIG[mode] and mode or "phase"
    local cacheKey = normalizedMode .. ":" .. (compact and "compact" or "wide")
    self.columnLayoutCache = self.columnLayoutCache or {}
    local cached = self.columnLayoutCache[cacheKey]
    if cached and cached.usableWidth == usable then
        return cached.layout
    end

    local definitions = self:GetViewColumnDefinitions(normalizedMode, compact)
    local columns = {}
    local minimumWidth = COLUMN_GAP * math.max(0, #definitions - 1)
    for _, definition in ipairs(definitions) do
        local column = {}
        for key, value in pairs(definition) do
            column[key] = value
        end
        column.width = column.minWidth
        columns[#columns + 1] = column
        minimumWidth = minimumWidth + column.width
    end

    local remaining = math.max(0, usable - minimumWidth)
    remaining = growColumnWidths(columns, "preferredWidth", remaining)
    remaining = growColumnWidths(columns, "maxWidth", remaining)

    local x = ROW_HORIZONTAL_PADDING
    local usedWidth = COLUMN_GAP * math.max(0, #columns - 1)
    local layout = {
        columns = columns,
        compact = compact,
        usableWidth = usable,
        signature = cacheKey .. ":" .. tostring(usable),
    }
    for _, column in ipairs(columns) do
        column.x = x
        layout[column.key] = column
        x = x + column.width + COLUMN_GAP
        usedWidth = usedWidth + column.width
    end
    layout.usedWidth = usedWidth
    layout.trailingWidth = math.max(0, usable - usedWidth)

    self.columnLayoutCache[cacheKey] = {
        usableWidth = usable,
        layout = layout,
    }
    return layout
end

local function getContainerNumSlotsSafe(bag)
    local ok, result
    if C_Container and C_Container.GetContainerNumSlots then
        ok, result = pcall(C_Container.GetContainerNumSlots, bag)
    elseif GetContainerNumSlots then
        ok, result = pcall(GetContainerNumSlots, bag)
    end
    if ok and BigBiSList.IsReadableValue(result) and type(result) == "number" and result >= 0 then
        return result, true
    end
    return 0, false
end

local function getContainerItemIDSafe(bag, slot)
    local ok, result
    if C_Container and C_Container.GetContainerItemID then
        ok, result = pcall(C_Container.GetContainerItemID, bag, slot)
        if ok and (not issecretvalue or not issecretvalue(result)) then
            return result, true
        end
    elseif GetContainerItemID then
        ok, result = pcall(GetContainerItemID, bag, slot)
        if ok and (not issecretvalue or not issecretvalue(result)) then
            return result, true
        end
    end
    return nil, false
end

local function getContainerItemLinkSafe(bag, slot)
    local ok, result
    if C_Container and C_Container.GetContainerItemLink then
        ok, result = pcall(C_Container.GetContainerItemLink, bag, slot)
        if ok and (not issecretvalue or not issecretvalue(result)) then
            return result, true
        end
    elseif GetContainerItemLink then
        ok, result = pcall(GetContainerItemLink, bag, slot)
        if ok and (not issecretvalue or not issecretvalue(result)) then
            return result, true
        end
    end
    return nil, false
end

local function ownedItemGUID(bag, slot)
    local api = C_Item and C_Item.GetItemGUID
    if not api or not ItemLocation then return nil end
    local ok, location
    if bag ~= nil and ItemLocation.CreateFromBagAndSlot then
        ok, location = pcall(ItemLocation.CreateFromBagAndSlot, ItemLocation, bag, slot)
    elseif bag == nil and ItemLocation.CreateFromEquipmentSlot then
        ok, location = pcall(ItemLocation.CreateFromEquipmentSlot, ItemLocation, slot)
    end
    if not ok then return nil end
    local hasGUID, guid = pcall(api, location)
    if hasGUID and BigBiSList.IsReadableValue(guid) and type(guid) == "string" and guid ~= "" then return guid end
end

function UI:GetStorageItemGUID(bag, slot)
    return ownedItemGUID(bag, slot)
end

local function getInventorySlotInfo(slotDefinition)
    local lookup = C_PaperDollInfo and C_PaperDollInfo.GetInventorySlotInfo or GetInventorySlotInfo
    if lookup and slotDefinition.inventorySlotName then
        local ok, slotId, texture = pcall(lookup, slotDefinition.inventorySlotName)
        if ok and BigBiSList.IsReadableValue(slotId) and type(slotId) == "number" then
            return slotId, BigBiSList.IsReadableValue(texture) and texture or nil
        end
    end
    return slotDefinition.inventorySlotId
end

local function getInventoryItemLinkSafe(slotId)
    if GetInventoryItemLink and slotId then
        local ok, itemLink = pcall(GetInventoryItemLink, "player", slotId)
        if ok and (not issecretvalue or not issecretvalue(itemLink)) then
            return itemLink
        end
    end
    return nil
end

function UI:GetItemInfo(itemId)
    local api = BigBiSList.isForever and C_Item and C_Item.GetItemInfo or GetItemInfo
    if not api then return nil end
    if not BigBiSList.isForever then return api(itemId) end
    local ok, name, link, quality, itemLevel, requiredLevel, className, subclassName, count, equipLocation, icon = pcall(api, itemId)
    if ok and BigBiSList.IsReadableValue(name) and BigBiSList.IsReadableValue(link)
        and BigBiSList.IsReadableValue(quality) and BigBiSList.IsReadableValue(equipLocation)
        and BigBiSList.IsReadableValue(icon) then
        return name, link, quality, itemLevel, requiredLevel, className, subclassName, count, equipLocation, icon
    end
end

local function getItemEquipLocation(itemId)
    local instant = BigBiSList.isForever and C_Item and C_Item.GetItemInfoInstant or GetItemInfoInstant
    if instant and itemId then
        local ok, _, _, _, equipLocation = pcall(instant, itemId)
        if ok and (not issecretvalue or not issecretvalue(equipLocation)) and equipLocation ~= nil then return equipLocation end
    end
    if itemId then
        local ok, _, _, _, _, _, _, _, _, equipLocation = pcall(UI.GetItemInfo, UI, itemId)
        if ok then return equipLocation end
    end
    return nil
end

local function parseItemLinkEnhancements(itemLink)
    local itemString = itemLink and string.match(itemLink, "item:([^|%]]+)")
    if not itemString then
        return nil
    end

    local fields = {}
    for field in string.gmatch(itemString .. ":", "([^:]*):") do
        table.insert(fields, field)
    end

    local parsed = {
        item_id = tonumber(fields[1]),
        enchant_id = tonumber(fields[2]),
        gem_ids = {},
    }
    if not parsed.item_id then
        return nil
    end
    if parsed.enchant_id == 0 then
        parsed.enchant_id = nil
    end
    for index = 3, 6 do
        local gemId = tonumber(fields[index])
        if gemId and gemId > 0 then
            table.insert(parsed.gem_ids, gemId)
        end
    end
    return parsed
end

local function itemNameFromLink(itemLink)
    return itemLink and string.match(itemLink, "%[([^%]]+)%]") or nil
end

local function enhancementSlotsContain(slots, slotName)
    if not slotName or slotName == "" then
        return true
    end

    for _, candidate in ipairs(slots or {}) do
        if candidate == slotName then
            return true
        end
    end
    return false
end

local function enhancementSlotsForEquipLocation(equipLocation)
    return EQUIP_LOCATION_ENHANCEMENT_SLOTS[equipLocation] or {}
end

local function slotLabelForEquipLocation(equipLocation)
    return EQUIP_LOCATION_SLOT_LABELS[equipLocation]
end

local function ownershipStateLabel(state)
    if state == "unknown" then return "Unknown" end
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

local function ownedFilterLabel(ownedState)
    return OWNED_FILTER_LABELS[ownedState or "all"] or ownershipStateLabel(ownedState)
end

local function boeFilterLabel(boe)
    return BOE_FILTER_LABELS[boe or "all"] or tostring(boe or "All binding")
end

local function longevityFilterLabel(longevity)
    return LONGEVITY_FILTER_LABELS[longevity or "all"] or tostring(longevity or "All usefulness")
end

local function upgradeModeLabel(upgradeMode)
    return UPGRADE_MODE_LABELS[upgradeMode or "candidates"] or tostring(upgradeMode or "Upgrade candidates")
end

local function upgradeComparisonText(data)
    if data and data.comparison and data.comparison.explanation then
        return data.comparison.explanation
    end
    if not data or not data.upgrade_state or data.upgrade_state == "not_upgrade" then
        return nil
    end

    local slotText = data.upgrade_compared_slot or data.slot or "slot"
    local comparedText
    if data.upgrade_compared_name then
        comparedText = data.upgrade_compared_name
        if data.upgrade_compared_rank_label and data.upgrade_compared_rank_label ~= "" then
            comparedText = comparedText .. " (" .. data.upgrade_compared_rank_label .. ")"
        end
        if data.upgrade_compared_state then
            comparedText = comparedText .. " in " .. ownershipStateLabel(data.upgrade_compared_state)
        end
    else
        comparedText = "empty " .. slotText
    end

    if data.upgrade_state == "owned_upgrade" then
        return "Owned upgrade over " .. comparedText
    end
    return "Upgrade over " .. comparedText
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

    -- A secondary profession can be present after an empty primary slot.
    local professionSlots = { GetProfessions() }
    for _, professionIndex in pairs(professionSlots) do
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
    if phaseKey == LEVELING_PHASE_KEY then
        return true
    end
    for _, key in ipairs(BigBiSList:GetPhaseOrder()) do
        if key == phaseKey then
            return true
        end
    end
    return false
end

local function phaseIndex(phaseKey)
    for index, key in ipairs(BigBiSList:GetPhaseOrder()) do
        if key == phaseKey then
            return index
        end
    end
    return 999
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
    return BigBiSList:GetCharacterDB().selection
end

-- Item presentation can browse a different role without changing character navigation.
function UI:GetItemContext()
    return self.slotComparison or self:GetSelection()
end

function UI:GetItemContextFilters()
    local comparison = self.slotComparison
    if comparison then
        if comparison.statRank then
            return { class = comparison.class, level = comparison.level, _leveling = comparison.phase == LEVELING_PHASE_KEY,
                race = BigBiSList:GetPlayerRaceName(), faction = BigBiSList:GetPlayerFactionName() }
        end
        return {}
    end
    return self:GetFilters()
end

local function copyStateValues(values)
    local result = {}
    for key, value in pairs(values or {}) do
        result[key] = type(value) == "table" and copyStateValues(value) or value
    end
    return result
end

function UI:GetFilters(viewName)
    if self:GetViewKey(viewName) == "settings" then
        viewName = self.settingsReturnTab or self.lastWorkspaceTab or (self:IsLevelingMode() and "Gear Guide" or "Upgrades")
    end
    local state = self:GetViewState(viewName)
    if type(state.filters) ~= "table" then
        local defaults = BigBiSList.defaults and BigBiSList.defaults.char and BigBiSList.defaults.char.filters
        state.filters = copyStateValues(defaults or BigBiSList:GetCharacterDB().filters)
        state.filters.includeEarlier = self:GetViewKey(viewName) == "upgrades"
    end
    if state.filters.includeEarlier == nil then state.filters.includeEarlier = self:GetViewKey(viewName) == "upgrades" end
    return state.filters
end

local function sortedKeys(values)
    local keys = {}
    for key in pairs(values or {}) do
        table.insert(keys, key)
    end
    table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
    return keys
end

function UI:IsLevelingMode()
    local selection = self:GetSelection() or {}
    return selection.mode == "leveling" or selection.phase == LEVELING_PHASE_KEY
end

function UI:GetEffectivePhaseKey()
    if BigBiSList.GetEffectivePhaseKey then
        return BigBiSList:GetEffectivePhaseKey(self:GetSelection())
    end
    return self:IsLevelingMode() and LEVELING_PHASE_KEY or (self:GetSelection().phase or "PR")
end

function UI:GetActiveTabNames()
    return self:IsLevelingMode() and LEVELING_TAB_NAMES or ENDGAME_TAB_NAMES
end

function UI:GetViewKey(tabName)
    tabName = normalizeTabName(tabName or (self:GetSelection() or {}).tab)
    if tabName == "Upgrades" then
        return "upgrades"
    elseif tabName == "By Slot" then
        return "bisList"
    elseif tabName == "Gear Guide" then
        return "gearGuide"
    elseif tabName == "Equipped" then
        return "myGear"
    elseif tabName == "Builds" then
        return "builds"
    elseif tabName == "Enhance" then
        return "enhancements"
    elseif tabName == "Wishlist" then
        return "wishlist"
    end
    return "settings"
end

function UI:GetViewState(tabName)
    local char = BigBiSList:GetCharacterDB()
    char.viewState = char.viewState or {}
    local key = self:GetViewKey(tabName)
    char.viewState[key] = char.viewState[key] or {}
    return char.viewState[key]
end

function UI:ViewSupportsFilters(tabName)
    tabName = normalizeTabName(tabName or (self:GetSelection() or {}).tab)
    return tabName == "Upgrades"
        or tabName == "By Slot"
        or tabName == "Gear Guide"
        or tabName == "Enhance"
        or tabName == "Wishlist"
end

function UI:ViewSupportsInspector(tabName)
    return normalizeTabName(tabName or (self:GetSelection() or {}).tab) ~= "Settings"
end

function UI:ValidateSelection()
    BigBiSList:EnsureDatabase()

    local index = BigBiSList:GetClassSpecIndex()
    local char = BigBiSList:GetCharacterDB()
    local selection = char.selection
    local className = selection.class
    local specName = selection.spec
    local phaseKey = selection.phase
    local tabName = normalizeTabName(selection.tab)
    local detectedPhase = BigBiSList.GetCurrentPhaseKey and BigBiSList:GetCurrentPhaseKey() or nil

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

    if not phaseExists(detectedPhase) then
        detectedPhase = "PR"
    end

    if phaseKey == LEVELING_PHASE_KEY and BigBiSList.supportsLeveling then
        selection.mode = "leveling"
        phaseKey = detectedPhase
    elseif not phaseExists(phaseKey) then
        phaseKey = detectedPhase
    end
    char.lastDetectedPhase = detectedPhase
    if BigBiSList.ApplyDetectedPlayerLevel then
        BigBiSList:ApplyDetectedPlayerLevel()
    end

    local activeTabs = (selection.mode == "leveling") and LEVELING_TAB_NAMES or ENDGAME_TAB_NAMES
    if tabName ~= "Settings" and not listContains(activeTabs, tabName) then
        tabName = (selection.mode == "leveling") and "Gear Guide" or "Upgrades"
    end

    BigBiSList:SetSelection(className, specName, phaseKey, tabName)
end

function UI:AddOwnedInventoryItem(owned, itemId, itemLink, location, slotDefinition, guid, sourceId)
    itemId = tonumber(itemId) or (itemLink and tonumber(itemLink:match("item:(%d+)")))
    if not itemId then return end
    if BigBiSList.isForever then
        owned.variants = owned.variants or {}
        owned.variantUnknownItems = owned.variantUnknownItems or {}
        local variantId = BigBiSList:GetItemVariantIdFromLink(itemLink)
        if variantId then
            local state = location == "bags" and "bag" or location
            if (OWNERSHIP_PRIORITY[state] or 0) > (OWNERSHIP_PRIORITY[owned.variants[variantId]] or 0) then
                owned.variants[variantId] = state
            end
        elseif not itemLink or (BigBiSList.ForeverGearRating and BigBiSList.ForeverGearRating:IsUnresolvedVariant(itemId)) then
            owned.variantUnknownItems[itemId] = true
        end
        if itemLink and BigBiSList.ForeverGearRating then
            owned.gearStatLinks = owned.gearStatLinks or {}
            local existing = owned.gearStatLinks[itemLink]
            if not existing or (location == "equipped" and existing.state ~= "equipped") then
                owned.gearStatLinks[itemLink] = {
                    item_id = itemId, item_link = itemLink, state = location == "bags" and "bag" or location,
                }
            end
        end
        if location == "bags" and owned.gearCopies then
            owned.gearCopies[#owned.gearCopies + 1] = {
                item_id = itemId, item_link = itemLink, state = "bag", guid = guid, sourceId = sourceId,
            }
        end
    end
    local item = BigBiSList.GetItemData and BigBiSList:GetItemData(itemId)
    local entry = owned.inventoryItems[itemId] or { item_id = itemId, locations = {} }
    owned.inventoryItems[itemId] = entry
    local ok, cachedName, cachedLink = pcall(UI.GetItemInfo, UI, itemId)
    if not ok then cachedName, cachedLink = nil, nil end
    local presentation = self.itemPresentationCache and self.itemPresentationCache[itemId]
    entry.item_link = entry.item_link or itemLink or cachedLink or (presentation and presentation.link)
    entry.name = entry.name or itemNameFromLink(itemLink) or cachedName or (presentation and presentation.name) or (item and item.name)
    entry.equip_location = getItemEquipLocation(itemId)
    entry.inventory_slot = item and item.inventory_slot or entry.inventory_slot
    entry.locations[location] = true
    if slotDefinition then
        entry.slots = entry.slots or {}
        for _, slot in ipairs(slotDefinition.slots or {}) do
            if not listContains(entry.slots, slot) then table.insert(entry.slots, slot) end
        end
    end
    if ((entry.equip_location == nil and not entry.inventory_slot) or not entry.name or not entry.item_link)
        and not (self.ownedItemMetadataResolved and self.ownedItemMetadataResolved[itemId]) then
        self.pendingItemLoads = self.pendingItemLoads or {}
        local pending = self.pendingItemLoads[itemId] or { subscribers = {} }
        self.pendingItemLoads[itemId] = pending
        pending.ownedMetadata = true
        self:RequestItemPresentation(itemId)
    end
end

function UI:BuildOwnedItems()
    self:CountPerformance("ownershipBuilds")
    local char = BigBiSList:GetCharacterDB()
    local bankCache = not BigBiSList.isForever and char.bankCache
    local statBank = BigBiSList.isForever and char.bankCache.scanned and char.bankCache

    local owned = {
        equippedSlots = {},
        unreadableEquipmentSlots = {},
        enhancementItems = {},
        inventoryItems = {},
        bankScanned = bankCache and bankCache.scanned or false,
        bankUpdatedAt = bankCache and bankCache.updatedAt or "",
        bankLinkCount = bankCache and bankCache.links and #bankCache.links or 0,
        gearCopies = BigBiSList.ForeverGearRating and {} or nil,
        inventoryIncomplete = BigBiSList.isForever and not GetInventoryItemID or false,
    }

    local function addEnhancedItem(itemLink, state, locationLabel, slotDefinition)
        local parsed = parseItemLinkEnhancements(itemLink)
        if not parsed then
            return
        end

        local equipLocation = getItemEquipLocation(parsed.item_id)
        local slots = slotDefinition and slotDefinition.slots or enhancementSlotsForEquipLocation(equipLocation)
        table.insert(owned.enhancementItems, {
            item_id = parsed.item_id,
            item_link = itemLink,
            enchant_id = parsed.enchant_id,
            gem_ids = parsed.gem_ids,
            state = state,
            location_label = locationLabel,
            slot = slotDefinition and slotDefinition.label or slotLabelForEquipLocation(equipLocation),
            slot_key = slotDefinition and slotDefinition.key or nil,
            slots = slots,
            equip_location = equipLocation,
        })
    end

    for _, slotDefinition in ipairs(BigBiSList:GetEquipmentSlotDefinitions()) do
        local slotId = getInventorySlotInfo(slotDefinition)
        local readable, itemId
        if GetInventoryItemID and slotId then
            local ok, value = pcall(GetInventoryItemID, "player", slotId)
            readable = ok and BigBiSList.IsReadableValue(value)
            if readable and type(value) == "number" and value > 0 then itemId = value end
        end
        local itemLink
        if itemId or not readable then itemLink = getInventoryItemLinkSafe(slotId) end
        if not readable and itemLink then itemId = tonumber(itemLink:match("item:(%d+)")) end
        if itemId then
            owned[itemId] = "equipped"
            owned.equippedSlots[slotDefinition.key] = {
                item_id = itemId,
                item_link = itemLink,
                slotId = slotId,
                slot = slotDefinition.label,
                guid = owned.gearCopies and ownedItemGUID(nil, slotId),
            }
            self:AddOwnedInventoryItem(owned, itemId, itemLink, "equipped", slotDefinition)
            addEnhancedItem(itemLink, "equipped", "Equipped", slotDefinition)

            if slotDefinition.key == "MainHand" and getItemEquipLocation(itemId) == "INVTYPE_2HWEAPON" then
                owned.equippedTwoHand = true
            end
        elseif not readable then
            owned.unreadableEquipmentSlots[slotDefinition.key] = true
            if BigBiSList.isForever then owned.inventoryIncomplete = true end
        end
    end

    for bag = 0, 4 do
        local numSlots, bagReadable = getContainerNumSlotsSafe(bag)
        if BigBiSList.isForever and not bagReadable then owned.bagsIncomplete = true end

        for slot = 1, numSlots do
            local itemId, slotReadable = getContainerItemIDSafe(bag, slot)
            local itemLink = getContainerItemLinkSafe(bag, slot)
            if BigBiSList.isForever and not itemId and itemLink then
                itemId = tonumber(itemLink:match("item:(%d+)"))
            end
            if BigBiSList.isForever and not slotReadable and not itemId then owned.bagsIncomplete = true end
            if itemId and not owned[itemId] then
                owned[itemId] = "bag"
            end
            local guid = owned.gearCopies and itemLink and ownedItemGUID(bag, slot)
            self:AddOwnedInventoryItem(owned, itemId, itemLink, "bags", nil, guid, bag .. ":" .. slot)
            addEnhancedItem(itemLink, "bag", "Bags")
        end
    end
    if owned.bagsIncomplete then owned.inventoryIncomplete = true end

    if bankCache and bankCache.items then
        for itemIdText in pairs(bankCache.items) do
            local itemId = tonumber(itemIdText)
            if itemId and not owned[itemId] then
                owned[itemId] = "bank"
            end
            self:AddOwnedInventoryItem(owned, itemId, nil, "bank")
        end
    end
    if bankCache and bankCache.links then
        for _, itemLink in ipairs(bankCache.links) do
            local parsed = parseItemLinkEnhancements(itemLink)
            self:AddOwnedInventoryItem(owned, parsed and parsed.item_id, itemLink, "bank")
            addEnhancedItem(itemLink, "bank", "Bank")
        end
    end

    if statBank and owned.gearCopies then
        -- A withdrawal can reach the bag snapshot before the next readable bank scan.
        local carried = {}
        for _, entry in pairs(owned.equippedSlots) do if entry.guid then carried[entry.guid] = true end end
        for _, entry in ipairs(owned.gearCopies) do if entry.guid then carried[entry.guid] = true end end
        for index, link in ipairs(statBank.links or {}) do
            local itemId = type(link) == "string" and tonumber(link:match("item:(%d+)"))
            local guid = statBank.guids and statBank.guids[index]
            if itemId and not (guid and carried[guid]) then
                owned.gearCopies[#owned.gearCopies + 1] = { item_id = itemId, item_link = link, state = "bank",
                    guid = guid, sourceId = statBank.locations and statBank.locations[index] }
            end
        end
    end

    return owned
end

function UI:GetOwnedSnapshot()
    local character = BigBiSList:GetCharacterDB()
    if self.ownedCharacter and self.ownedCharacter ~= character then self.currentOwned = nil end
    self.ownedCharacter = character
    self.currentOwned = self.currentOwned or self:BuildOwnedItems()
    return self.currentOwned
end

function UI:BuildAccessState()
    self:CountPerformance("accessBuilds")
    return {
        professions = collectProfessionState(),
        reputations = collectReputationState(),
        playerSide = getPlayerSide(),
        playerRace = BigBiSList.GetPlayerRaceName and BigBiSList:GetPlayerRaceName(),
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
    return not playerSide or not optionSide or optionSide == "Both" or optionSide == playerSide
end

local function optionHasZone(option, zone)
    if not option or not zone or zone == "" then
        return false
    end

    if option.zone == zone then
        return true
    end

    for _, optionZone in ipairs(option.zones or {}) do
        if optionZone == zone then
            return true
        end
    end

    return false
end

local function optionMatchesSourceFilter(option, sourceType)
    if not sourceType or sourceType == "all" then
        return true
    end

    return option
        and (option.source_filter_key == sourceType or option.source_type == sourceType)
end

local function optionMatchesAnySelectedSourceType(option, selectedSourceTypes)
    if not tableHasAnyEnabled(selectedSourceTypes) then
        return true
    end

    for sourceType, selected in pairs(selectedSourceTypes or {}) do
        if selected and optionMatchesSourceFilter(option, sourceType) then
            return true
        end
    end
    return false
end

local function optionMatchesZoneFilter(option, zone)
    if not zone or zone == "all" then
        return true
    end

    return optionHasZone(option, zone)
end

local function optionMatchesAnySelectedZone(option, selectedZones)
    if not tableHasAnyEnabled(selectedZones) then
        return true
    end

    for zone, selected in pairs(selectedZones or {}) do
        if selected and optionHasZone(option, zone) then
            return true
        end
    end
    return false
end

local function optionHasCost(option, costKey)
    if not option or not costKey or costKey == "" then
        return false
    end

    for _, optionCostKey in ipairs(option.cost_keys or {}) do
        if optionCostKey == costKey then
            return true
        end
    end
    return false
end

local function optionMatchesCostFilter(option, costKey)
    if not costKey or costKey == "all" then
        return true
    end
    return optionHasCost(option, costKey)
end

local function optionMatchesAnySelectedCost(option, selectedCosts)
    if not tableHasAnyEnabled(selectedCosts) then
        return true
    end

    for costKey, selected in pairs(selectedCosts or {}) do
        if selected and optionHasCost(option, costKey) then
            return true
        end
    end
    return false
end

local function optionHasVendor(option, vendorKey)
    if not option or not vendorKey or vendorKey == "" then
        return false
    end
    return option.vendor_key == vendorKey
end

local function optionMatchesVendorFilter(option, vendorKey)
    if not vendorKey or vendorKey == "all" then
        return true
    end
    return optionHasVendor(option, vendorKey)
end

local function optionMatchesAnySelectedVendor(option, selectedVendors)
    if not tableHasAnyEnabled(selectedVendors) then
        return true
    end

    for vendorKey, selected in pairs(selectedVendors or {}) do
        if selected and optionHasVendor(option, vendorKey) then
            return true
        end
    end
    return false
end

local function optionHasReputation(option, reputation)
    if not option or not reputation or reputation == "" then
        return false
    end

    for _, optionReputation in ipairs(option.reputations or {}) do
        if optionReputation == reputation then
            return true
        end
    end
    return false
end

local function optionMatchesReputationFilter(option, reputation)
    if not reputation or reputation == "all" then
        return true
    end
    return optionHasReputation(option, reputation)
end

local function optionMatchesAnySelectedReputation(option, selectedReputations)
    if not tableHasAnyEnabled(selectedReputations) then
        return true
    end

    for reputation, selected in pairs(selectedReputations or {}) do
        if selected and optionHasReputation(option, reputation) then
            return true
        end
    end
    return false
end

local function isReportedOnlyAccessOption(option)
    return type(option) == "table" and option.vendor_details_status == "reported_only"
end

local function optionIsPhaseAvailable(option, selectedPhaseIndex)
    if not selectedPhaseIndex then
        return true
    end
    if BigBiSList.IsAccessOptionPhaseAvailable then
        return BigBiSList:IsAccessOptionPhaseAvailable(option, selectedPhaseIndex)
    end
    return option and (option.acquisitionPhaseIndex or phaseIndex(option.acquisition_phase or "PR")) <= selectedPhaseIndex
end

local function optionMatchesActiveSourceContext(option, filters, selectedPhaseIndex, phaseKey)
    if not filters or isReportedOnlyAccessOption(option) then
        return false
    end

    local hasSourceFilter = filters.sourceType and filters.sourceType ~= "all"
        or tableHasAnyEnabled(filters.sourceTypes)
    local hasZoneFilter = filters.zone and filters.zone ~= "all"
        or tableHasAnyEnabled(filters.zones)
    local hasCostFilter = filters.cost and filters.cost ~= "all"
        or tableHasAnyEnabled(filters.costs)
    local hasVendorFilter = filters.vendor and filters.vendor ~= "all"
        or tableHasAnyEnabled(filters.vendors)
    local hasReputationFilter = filters.reputation and filters.reputation ~= "all"
        or tableHasAnyEnabled(filters.reputations)
    if not hasSourceFilter and not hasZoneFilter and not hasCostFilter and not hasVendorFilter and not hasReputationFilter then
        return false
    end

    if BigBiSList.GetAccessOptionFilterMatch then
        local phase = phaseKey or (BigBiSList:GetPhaseOrder() or {})[selectedPhaseIndex]
        return BigBiSList:GetAccessOptionFilterMatch(option, filters, phase) ~= nil
    end

    return optionIsPhaseAvailable(option, selectedPhaseIndex)
        and optionMatchesSourceFilter(option, filters.sourceType)
        and optionMatchesAnySelectedSourceType(option, filters.sourceTypes)
        and optionMatchesZoneFilter(option, filters.zone)
        and optionMatchesAnySelectedZone(option, filters.zones)
        and optionMatchesCostFilter(option, filters.cost)
        and optionMatchesAnySelectedCost(option, filters.costs)
        and optionMatchesVendorFilter(option, filters.vendor)
        and optionMatchesAnySelectedVendor(option, filters.vendors)
        and optionMatchesReputationFilter(option, filters.reputation)
        and optionMatchesAnySelectedReputation(option, filters.reputations)
end

function UI:EvaluateAccessOption(option, accessState)
    if BigBiSList.isForever and BigBiSList.AccessOptionMatchesCharacter then
        local selection = self:GetItemContext() or {}
        local leveling = self:IsLevelingMode()
        if not BigBiSList:AccessOptionMatchesCharacter(option, {
            faction = accessState.playerSide, race = accessState.playerRace, class = selection.class,
            level = leveling and (selection.level or BigBiSList:GetSelectedLevelingLevel()) or nil, _leveling = leveling,
        }) then return {status = "unavailable", option = option} end
        local source = option and option.source
        local quest = source and (source.quest_id or (source.entity_type == "quest" and source.entity_id))
        if quest and source.type == "quest" and source.repeatable ~= true and self.GetAcquisitionQuestState
            and self:GetAcquisitionQuestState(quest) == "Completed" then
            return {status = "quest_completed", option = option}
        end
    end
    local evaluation = self:EvaluateRequirementList(option and option.requirements, accessState)
    evaluation.option = option
    return evaluation
end

function UI:GetAccessEvaluation(data)
    local phaseKey = self.slotComparison and self.slotComparison.phase
        or (data and data.expansion_summary and data.content_phase) or self:GetEffectivePhaseKey()
    local selectedPhaseIndex = BigBiSList.GetAvailabilityPhaseIndex
        and BigBiSList:GetAvailabilityPhaseIndex(phaseKey) or phaseIndex(phaseKey)
    local progressionKey = tostring((BigBiSListData or {}).active_schedule) .. ":" .. tostring(phaseKey) .. ":" .. tostring(selectedPhaseIndex)
        .. ":" .. (self.slotComparison and "comparison" or "workspace")
    if self.currentAccessEvaluationContext ~= progressionKey then
        self.currentAccessEvaluationCache = {}
        self.currentAccessEvaluationContext = progressionKey
    end
    self.currentAccessEvaluationCache = self.currentAccessEvaluationCache or {}
    if data and self.currentAccessEvaluationCache[data] then
        return self.currentAccessEvaluationCache[data]
    end
    self.currentAccess = self.currentAccess or self:BuildAccessState()
    local accessState = self.currentAccess
    local filters = self:GetItemContextFilters()
    local options = data and BigBiSList:GetRowAccessOptions(data)
    local preferredOption = data and (data.matched_access_option or (data.acquisition_display and data.acquisition_display.option))

    if options and #options > 0 then
        local optionEvaluations = {}
        local primaryEvaluation
        local firstEvaluation
        local firstReadyEvaluation
        local contextEvaluation
        local preferredEvaluation

        for _, option in ipairs(options) do
            if optionMatchesPlayerSide(option, accessState) then
                local evaluation = self:EvaluateAccessOption(option, accessState)
                if not optionIsPhaseAvailable(option, selectedPhaseIndex) then
                    local nextPhase
                    if BigBiSList.GetAccessOptionNextAvailablePhase then
                        nextPhase = BigBiSList:GetAccessOptionNextAvailablePhase(option, selectedPhaseIndex)
                    elseif (option.acquisitionPhaseIndex or phaseIndex(option.acquisition_phase or "PR")) > selectedPhaseIndex then
                        nextPhase = option.acquisitionPhaseIndex or phaseIndex(option.acquisition_phase)
                    end
                    evaluation.status = nextPhase and "future" or "unavailable"
                end
                table.insert(optionEvaluations, evaluation)
                if preferredOption == option and data.acquisition_display and data.acquisition_display.status == "unknown" then
                    evaluation.status = "unknown"
                    preferredEvaluation = evaluation
                end

                local preRaidEligible = phaseKey ~= "PR" or not BigBiSList.IsPreRaidAccessOption
                    or BigBiSList:IsPreRaidAccessOption(option, selectedPhaseIndex)
                if not isReportedOnlyAccessOption(option) and evaluation.status ~= "unavailable" and preRaidEligible then
                    firstEvaluation = firstEvaluation or evaluation
                    if option.is_primary and not primaryEvaluation then
                        primaryEvaluation = evaluation
                    end
                    if evaluation.status == "ready" and not firstReadyEvaluation then
                        firstReadyEvaluation = evaluation
                    end
                    if preferredOption and option == preferredOption then
                        preferredEvaluation = evaluation
                    end
                    if optionMatchesActiveSourceContext(option, filters, selectedPhaseIndex, phaseKey) then
                        if not contextEvaluation
                            or (evaluation.status == "ready" and contextEvaluation.status ~= "ready") then
                            contextEvaluation = evaluation
                        end
                    end
                end
            end
        end

        local selectedEvaluation = primaryEvaluation or firstEvaluation
        local status = selectedEvaluation and selectedEvaluation.status or "unknown"
        local contextMatched = false

        if preferredEvaluation then
            selectedEvaluation = preferredEvaluation
            status = preferredEvaluation.status
            contextMatched = true
        elseif contextEvaluation then
            selectedEvaluation = contextEvaluation
            status = contextEvaluation.status
            if status == "ready" and contextEvaluation.option and not contextEvaluation.option.is_primary then
                status = "ready_alternate"
            end
            contextMatched = true
        elseif primaryEvaluation and primaryEvaluation.status == "ready" then
            selectedEvaluation = primaryEvaluation
            status = "ready"
        elseif firstReadyEvaluation then
            selectedEvaluation = firstReadyEvaluation
            status = (firstReadyEvaluation.option and firstReadyEvaluation.option.is_primary) and "ready" or "ready_alternate"
        end
        if status == "quest_completed" and firstReadyEvaluation then
            selectedEvaluation, status, contextMatched = firstReadyEvaluation, "ready_alternate", false
        end

        local future = preferredEvaluation and selectedEvaluation == preferredEvaluation
            and data.acquisition_display
            and data.acquisition_display.future == true
        if future then
            status = "future"
        elseif status == "ready" and selectedEvaluation and selectedEvaluation.option and not selectedEvaluation.option.is_primary then
            status = "ready_alternate"
        end

        local result = {
            status = status,
            optionEvaluation = selectedEvaluation,
            options = optionEvaluations,
            context_matched = contextMatched,
            future = future and true or false,
        }
        if data then self.currentAccessEvaluationCache[data] = result end
        return result
    end

    local flatEvaluation = self:EvaluateRequirementList(data and data.requirements, accessState)
    local result = {
        status = flatEvaluation.status,
        optionEvaluation = flatEvaluation,
    }
    if data then self.currentAccessEvaluationCache[data] = result end
    return result
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

function UI:GetAccessOptionDisplayText(option)
    if not option then
        return nil
    end

    if option.source_summary and option.source_summary ~= "" then
        return option.source_summary
    end
    return option.label
end

local SELLER_SOURCE_TYPES = {
    vendor = true,
    pvp = true,
    token_turnin = true,
}

local function isSellerAccessOption(option)
    if type(option) ~= "table" then
        return false
    end
    return option.is_vendor_purchase == true
        or SELLER_SOURCE_TYPES[option.source_type] == true
        or trim(option.vendor_label) ~= ""
end

local function sellerDetailKey(option)
    if not isSellerAccessOption(option) then
        return nil
    end

    local vendor = trim(option.vendor_key or option.vendor_label)
    local area = trim(option.location_area or option.zone)
    local cost = trim(option.cost_summary)
    return lower(vendor) .. "\031" .. lower(area) .. "\031" .. lower(cost)
end

function UI:GetSellerDetailLines(option, omitSourceItems)
    if BigBiSList.GetAccessOptionDetailFields then
        local fields = BigBiSList:GetAccessOptionDetailFields(option)
        if type(fields) == "table" and #fields > 0 then
            local lines = {}
            for _, field in ipairs(fields) do
                local value = trim(field.value)
                local note = trim(field.note)
                if note ~= "" and lower(note) ~= lower(value) then
                    value = value .. " - " .. note
                end
                if not omitSourceItems or (field.key ~= "token_source" and field.key ~= "quest_starter_source") then
                    table.insert(lines, tostring(field.label or field.key or "Detail") .. ": " .. value)
                end
            end
            return lines, option.vendor_details_status
        end
    end
    if not isSellerAccessOption(option) then
        return nil
    end

    local vendor = trim(option.vendor_label)
    local area = trim(option.location_area or option.zone)
    local locationNote = trim(option.location_note)
    local cost = trim(option.cost_summary)

    if locationNote ~= "" and lower(locationNote) ~= lower(area) then
        area = area ~= "" and (area .. " - " .. locationNote) or locationNote
    end

    -- A visible fallback is more honest than silently omitting an incomplete
    -- imported detail. Canonical validation should keep purchase routes complete.
    local missing = "Unavailable in committed source data"
    return {
        "Vendor: " .. (vendor ~= "" and vendor or missing),
        "Area: " .. (area ~= "" and area or missing),
        "Cost: " .. (cost ~= "" and cost or missing),
    }, option.vendor_details_status
end

local function dedupeSellerOptions(options, seen)
    local deduped = {}
    seen = seen or {}
    for _, option in ipairs(options or {}) do
        local key = sellerDetailKey(option)
        if key and not seen[key] then
            seen[key] = true
            table.insert(deduped, option)
        end
    end
    return deduped, seen
end

function UI:GetRowSellerDisplayGroups(data, selectedOption)
    local groups
    if BigBiSList.GetRowSellerGroups then
        local phaseKey = data and data.expansion_summary and data.content_phase or self:GetEffectivePhaseKey()
        groups = BigBiSList:GetRowSellerGroups(data, selectedOption, phaseKey)
    end
    groups = groups or {}

    local selected = groups.selected
    if not isSellerAccessOption(selected) then
        selected = isSellerAccessOption(selectedOption)
            and not isReportedOnlyAccessOption(selectedOption)
            and selectedOption
            or nil
    end

    local seen = {}
    local selectedKey = sellerDetailKey(selected)
    if selectedKey then
        seen[selectedKey] = true
    end
    local alternatives
    alternatives, seen = dedupeSellerOptions(groups.alternatives, seen)
    local reported
    reported = dedupeSellerOptions(groups.reported, seen)

    return {
        selected = selected,
        alternatives = alternatives,
        reported = reported,
    }
end

function UI:GetSelectedAcquisitionRoute(data)
    local access = self:GetAccessEvaluation(data)
    local option = access.optionEvaluation and access.optionEvaluation.option
    local sellerGroups = self:GetRowSellerDisplayGroups(data, option)
    return sellerGroups.selected or option, access, sellerGroups
end

function UI:FormatSellerOptions(options)
    local blocks = {}
    for _, option in ipairs(options or {}) do
        local lines = self:GetSellerDetailLines(option)
        if lines then
            table.insert(blocks, table.concat(lines, "\n"))
        end
    end
    return table.concat(blocks, "\n\n")
end

function UI:AddSelectedRouteTooltipLines(tooltip, data, evaluation)
    evaluation = evaluation or self:GetAccessEvaluation(data or {})
    local optionEvaluation = evaluation and evaluation.optionEvaluation
    local selectedOption = optionEvaluation and optionEvaluation.option
    local sellerGroups = self:GetRowSellerDisplayGroups(data, selectedOption)
    local displayOption = sellerGroups.selected or selectedOption

    tooltip:AddLine("Selected route", 1, 0.82, 0.28)
    local sellerLines = self:GetSellerDetailLines(displayOption)
    if sellerLines then
        for _, line in ipairs(sellerLines) do
            tooltip:AddLine(line, 0.62, 0.78, 0.94, true)
        end
    elseif displayOption then
        tooltip:AddLine("Source: " .. (self:GetAccessOptionDisplayText(displayOption) or displayOption.label or "Source"), 0.62, 0.78, 0.94, true)
    else
        tooltip:AddLine("Source details are not recorded.", 0.62, 0.62, 0.66, true)
    end

    if #sellerGroups.alternatives > 0 then
        tooltip:AddLine("Other sellers (" .. tostring(#sellerGroups.alternatives) .. ") - open the inspector to compare.", 0.62, 0.62, 0.66, true)
    end
    if #sellerGroups.reported > 0 then
        tooltip:AddLine("Additional reported sellers (" .. tostring(#sellerGroups.reported) .. ") - open the inspector to review.", 0.62, 0.62, 0.66, true)
    end

    return optionEvaluation, displayOption, sellerGroups
end

function UI:ShowAcquisitionTooltip(owner, data)
    local evaluation = self:GetAccessEvaluation(data or {})
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:AddLine("Acquisition", 1, 0.82, 0.28)
    GameTooltip:AddLine("Access: " .. accessStateLabel(evaluation.status), 0.86, 0.86, 0.86, true)

    local optionEvaluation = self:AddSelectedRouteTooltipLines(GameTooltip, data, evaluation)
    if optionEvaluation and optionEvaluation.status == "ready" and data and data.ready_access_detail and data.ready_access_detail ~= "" then
        GameTooltip:AddLine("Route note: " .. self:GetAccessHelpText(optionEvaluation, data), 0.62, 0.62, 0.66, true)
    end
    if evaluation.future and data and data.acquisition_display and data.acquisition_display.acquisition_phase then
        GameTooltip:AddLine("Available in " .. BigBiSList:GetPhaseDisplayName(data.acquisition_display.acquisition_phase), 0.48, 0.70, 0.96, true)
    end

    local requirementsText
    if optionEvaluation then
        requirementsText = self:FormatAccessOptionRequirements(optionEvaluation)
    elseif evaluation.options and #evaluation.options > 0 then
        requirementsText = self:FormatAccessOptions(evaluation)
    elseif data and data.requirements and #data.requirements > 0 then
        requirementsText = self:FormatRequirements(data)
    else
        requirementsText = "No known character requirements."
    end
    GameTooltip:AddLine("Requirements", 1, 0.82, 0.28)
    GameTooltip:AddLine(requirementsText, 0.62, 0.62, 0.66, true)
    GameTooltip:Show()
end

function UI:GetContextSourceSummary(data)
    local evaluation = self:GetAccessEvaluation(data)
    if evaluation then
        local optionEvaluation = evaluation.optionEvaluation
        local option = optionEvaluation and optionEvaluation.option
        local summary = self:GetAccessOptionDisplayText(option)
        if summary and summary ~= "" then
            return summary
        end
    end

    return data and data.source_summary
end

function UI:GetAccessBlockingReason(evaluation)
    if not evaluation then
        return "No access data available."
    end

    if evaluation.status == "ready" then
        return "Available now. Drops, vendors, auctions, groups, and services are not guaranteed."
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
    local char = BigBiSList:GetCharacterDB()
    local strict, tabs = BigBiSList.isForever, {}
    if strict then
        local characterBank = Enum and Enum.BankType and Enum.BankType.Character
        local fetch = C_Bank and C_Bank.FetchPurchasedBankTabIDs
        if not self.personalBankOpen or characterBank == nil or not fetch then return false end
        local ok, bankTabs = pcall(fetch, characterBank)
        if not ok or not BigBiSList.IsReadableValue(bankTabs) or type(bankTabs) ~= "table" then return false end
        tabs = bankTabs
    else
        tabs[1] = BANK_CONTAINER or -1
        local firstBankBag = (NUM_BAG_SLOTS or 4) + 1
        for bag = firstBankBag, firstBankBag + (NUM_BANKBAGSLOTS or 7) - 1 do
            tabs[#tabs + 1] = bag
        end
    end

    local cache = { items = {}, links = {} }
    if strict then cache.guids, cache.locations = {}, {} end
    for _, bag in ipairs(tabs) do
        if strict and (not BigBiSList.IsReadableValue(bag) or type(bag) ~= "number") then return false end
        local numSlots, slotsReadable = getContainerNumSlotsSafe(bag)
        if strict and not slotsReadable then return false end
        for slot = 1, numSlots do
            local itemId, idReadable = getContainerItemIDSafe(bag, slot)
            local itemLink, linkReadable = getContainerItemLinkSafe(bag, slot)
            if strict then
                local linkId = type(itemLink) == "string" and tonumber(itemLink:match("item:(%d+)"))
                if not idReadable or not linkReadable or (itemLink and not linkId) or (itemId and itemId ~= linkId) then
                    return false
                end
                itemId = linkId
            end
            if itemId then
                cache.items[tostring(itemId)] = true
            end
            if itemLink then
                table.insert(cache.links, itemLink)
                if strict then
                    cache.guids[#cache.links] = ownedItemGUID(bag, slot)
                    cache.locations[#cache.links] = bag .. ":" .. slot
                end
            end
        end
    end

    cache.scanned = true
    cache.updatedAt = date and date("%Y-%m-%d %H:%M") or "this session"
    char.bankCache = cache
    return true
end

local INVALIDATION_EXPANSION = {
    all = { "ownership", "access", "query", "availability", "layout", "details", "controls", "presentation" },
    ownership = { "ownership", "query", "availability", "details", "controls" },
    access = { "access", "query", "availability", "details", "controls" },
    query = { "query", "availability", "details", "controls" },
    availability = { "availability", "controls" },
    layout = { "layout" },
    details = { "details" },
    controls = { "controls" },
    presentation = { "presentation", "controls" },
}

function UI:GetPerformanceStats()
    self.performanceStats = self.performanceStats or {
        scheduledRefreshes = 0,
        executedRefreshes = 0,
        layoutPasses = 0,
        sizeEvents = 0,
        ownershipBuilds = 0,
        accessBuilds = 0,
        availabilityBuilds = 0,
        queryBuilds = 0,
        modelRows = 0,
        realizedEntries = 0,
        widgetsCreated = 0,
        itemLoadRequests = 0,
        itemLoadCallbacks = 0,
        detailsBuilds = 0,
        reasons = {},
    }
    return self.performanceStats
end

function UI:ResetPerformanceStats()
    self.performanceStats = nil
    self:GetPerformanceStats()
end

function UI:CountPerformance(key, amount, reason)
    local stats = self:GetPerformanceStats()
    stats[key] = (stats[key] or 0) + (amount or 1)
    if reason and reason ~= "" then
        stats.reasons[reason] = (stats.reasons[reason] or 0) + 1
    end
end

function UI:Invalidate(domains, reason)
    self.dirtyDomains = self.dirtyDomains or {}
    self.domainVersions = self.domainVersions or {}
    local requested = type(domains) == "table" and domains or { domains or "query" }
    local expanded = {}

    for _, domain in ipairs(requested) do
        for _, target in ipairs(INVALIDATION_EXPANSION[domain] or { domain }) do
            expanded[target] = true
        end
    end

    for domain in pairs(expanded) do
        self.dirtyDomains[domain] = true
        self.domainVersions[domain] = (self.domainVersions[domain] or 0) + 1
    end

    if expanded.ownership then
        self.currentOwned = nil
        self.currentEnhancementAppliedCache = nil
        if BigBiSList.AcquisitionHighlights then BigBiSList.AcquisitionHighlights:InvalidateStorage() end
    end
    if expanded.access then
        self.currentAccess = nil
    end
    if expanded.query or expanded.ownership or expanded.access then
        self.currentFilterPayload = nil
        self.currentAccessEvaluationCache = nil
        self.currentViewQueryCache = nil
    end
    if expanded.availability then
        self.currentAvailabilitySnapshot = nil
    end
    if reason then
        self.lastInvalidationReason = reason
    end
end

function UI:ClearTransientCaches(releaseRender)
    self:Invalidate("all", "legacy-cache-clear")
    if releaseRender and self.ReleaseRenderFrames then
        self:ReleaseRenderFrames()
        self.renderModel = nil
    end
end

function UI:GetAvailabilityFilters()
    local filters = {}
    for key, value in pairs(self:GetFilters() or {}) do
        filters[key] = value
    end
    local char = BigBiSList:GetCharacterDB()
    self.currentCharacterDB = char
    self.currentAccess = self.currentAccess or self:BuildAccessState()
    self:GetOwnedSnapshot()
    local accessState = self.currentAccess
    filters.faction = accessState and accessState.playerSide or "all"
    filters.race = accessState and accessState.playerRace
    filters.class = (self:GetSelection() or {}).class
    filters._leveling = self:IsLevelingMode()
    filters.level = BigBiSList.GetSelectedLevelingLevel and BigBiSList:GetSelectedLevelingLevel() or MAX_LEVELING_LEVEL
    filters.ownedItems = self.currentOwned
    filters.ignoredItems = char.ignoredItems
    filters.hideIgnored = true
    filters.wishlistItems = char.wishlist
    filters.endgamePhase = (self:GetSelection() or {}).phase
    local enhancementState = self:GetViewState("Enhance")
    local gearGuideState = self:GetViewState("Gear Guide")
    local wishlistState = self:GetViewState("Wishlist")
    filters.enhancementType = enhancementState.type or "all"
    filters.appliedState = enhancementState.appliedState or "all"
    filters.recommendationCategory = gearGuideState.recommendationCategory or "all"
    filters.wishlistRelevance = wishlistState.relevance or "all"
    filters.getEnhancementAppliedState = function(row)
        local summary = self:GetEnhancementAppliedSummary(row)
        return summary and summary.state ~= "missing" and summary.state ~= "not_applicable"
    end
    return self:SanitizeFilterPayloadForView(filters)
end

function UI:GetFilterAvailabilitySnapshot()
    if self.currentAvailabilitySnapshot then
        return self.currentAvailabilitySnapshot
    end

    local selection = self:GetSelection()
    local filters = self:GetAvailabilityFilters()
    local phaseKey = normalizeTabName(selection.tab) == "Wishlist" and selection.phase or self:GetEffectivePhaseKey()
    self:CountPerformance("availabilityBuilds")
    self.currentAvailabilitySnapshot = BigBiSList:GetFilterAvailabilitySnapshot(selection.class, selection.spec, phaseKey, selection.tab, filters)
    self.filterFacetLabelCache = self.filterFacetLabelCache or { costLabels = {}, vendorLabels = {} }
    for key, label in pairs(self.currentAvailabilitySnapshot.costLabels or {}) do
        self.filterFacetLabelCache.costLabels[key] = label
    end
    for key, label in pairs(self.currentAvailabilitySnapshot.vendorLabels or {}) do
        self.filterFacetLabelCache.vendorLabels[key] = label
    end
    return self.currentAvailabilitySnapshot
end

function UI:GetAvailableSourceTypeValues()
    return self:GetFilterAvailabilitySnapshot().sourceTypes or {}
end

function UI:GetAvailableZoneValues()
    return self:GetFilterAvailabilitySnapshot().zones or {}
end

function UI:GetAvailableCostValues()
    return self:GetFilterAvailabilitySnapshot().costs or {}
end

function UI:GetAvailableCostLabels()
    local labels = {}
    for key, label in pairs(COST_FILTER_LABELS) do
        labels[key] = label
    end
    for key, label in pairs(self:GetFilterAvailabilitySnapshot().costLabels or {}) do
        labels[key] = label
    end
    return labels
end

function UI:GetAvailableVendorValues()
    return self:GetFilterAvailabilitySnapshot().vendors or {}
end

function UI:GetAvailableVendorLabels()
    return self:GetFilterAvailabilitySnapshot().vendorLabels or {}
end

function UI:GetRememberedCostLabels(selectedValues)
    local labels = {}
    for key, label in pairs(COST_FILTER_LABELS) do
        labels[key] = label
    end
    for key, label in pairs(self.filterFacetLabelCache and self.filterFacetLabelCache.costLabels or {}) do
        labels[key] = label
    end
    for value, selected in pairs(selectedValues or {}) do
        if selected and not labels[value] then
            for key, label in pairs(self:GetAvailableCostLabels()) do
                labels[key] = label
            end
            break
        end
    end
    return labels
end

function UI:GetRememberedVendorLabels(selectedValues)
    local labels = {}
    for key, label in pairs(self.filterFacetLabelCache and self.filterFacetLabelCache.vendorLabels or {}) do
        labels[key] = label
    end
    for value, selected in pairs(selectedValues or {}) do
        if selected and not labels[value] then
            for key, label in pairs(self:GetAvailableVendorLabels()) do
                labels[key] = label
            end
            break
        end
    end
    return labels
end

function UI:GetAvailableReputationValues()
    return self:GetFilterAvailabilitySnapshot().reputations or {}
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
        self.currentAvailabilitySnapshot = nil
        return true
    end
    return false
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
        self.currentAvailabilitySnapshot = nil
        return true
    end
    return false
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
        self.currentAvailabilitySnapshot = nil
        return true
    end
    return false
end

function UI:BuildFilterPayload()
    local filters = self:GetFilters()
    local char = BigBiSList:GetCharacterDB()
    self.currentCharacterDB = char
    self.currentAccess = self.currentAccess or self:BuildAccessState()
    self:GetOwnedSnapshot()
    self.currentFilterPayload = {
        search = filters.search,
        sourceType = filters.sourceType,
        sourceTypes = filters.sourceTypes,
        zone = filters.zone,
        zones = filters.zones,
        cost = filters.cost,
        costs = filters.costs,
        vendor = filters.vendor,
        vendors = filters.vendors,
        reputation = filters.reputation,
        reputations = filters.reputations,
        rankGroup = filters.rankGroup,
        rankGroups = filters.rankGroups,
        ownedState = filters.ownedState,
        upgradeMode = filters.upgradeMode,
        includeEarlier = filters.includeEarlier,
        binding = filters.binding,
        boe = filters.boe,
        faction = self.currentAccess and self.currentAccess.playerSide or "all",
        race = self.currentAccess and self.currentAccess.playerRace,
        class = (self:GetSelection() or {}).class,
        _leveling = self:IsLevelingMode(),
        longevity = filters.longevity,
        level = BigBiSList.GetSelectedLevelingLevel and BigBiSList:GetSelectedLevelingLevel() or MAX_LEVELING_LEVEL,
        slots = filters.slots,
        ownedItems = self.currentOwned,
        ignoredItems = char.ignoredItems,
        hideIgnored = true,
        wishlistItems = char.wishlist,
        endgamePhase = (self:GetSelection() or {}).phase,
    }
    local enhancementState = self:GetViewState("Enhance")
    local gearGuideState = self:GetViewState("Gear Guide")
    local wishlistState = self:GetViewState("Wishlist")
    self.currentFilterPayload.enhancementType = enhancementState.type or "all"
    self.currentFilterPayload.appliedState = enhancementState.appliedState or "all"
    self.currentFilterPayload.recommendationCategory = gearGuideState.recommendationCategory or "all"
    self.currentFilterPayload.wishlistRelevance = wishlistState.relevance or "all"
    self.currentFilterPayload.getEnhancementAppliedState = function(row)
        local summary = self:GetEnhancementAppliedSummary(row)
        return summary and summary.state ~= "missing" and summary.state ~= "not_applicable"
    end
    self.currentFilterPayload = self:SanitizeFilterPayloadForView(self.currentFilterPayload)
    return self.currentFilterPayload
end

function UI:GetProgressionCacheKey()
    local livePhase = BigBiSList.GetCurrentPhaseKey and BigBiSList:GetCurrentPhaseKey() or "PR"
    local selectedPhase = BigBiSList.GetCharacterDB and (self:GetSelection() or {}).phase or nil
    return tostring((BigBiSListData or {}).active_schedule) .. ":" .. tostring(livePhase) .. ":" .. tostring(selectedPhase)
end

function UI:GetCachedViewQuery(cacheKey, builder)
    local progressionKey = self:GetProgressionCacheKey()
    if self.currentViewQueryContext ~= progressionKey then
        self.currentViewQueryCache = {}
        self.currentViewQueryContext = progressionKey
    end
    self.currentViewQueryCache = self.currentViewQueryCache or {}
    if self.currentViewQueryCache[cacheKey] ~= nil then
        return self.currentViewQueryCache[cacheKey]
    end
    self:CountPerformance("queryBuilds")
    local result = builder()
    self.currentViewQueryCache[cacheKey] = result
    return result
end

function UI:SanitizeFilterPayloadForView(payload)
    local tabName = normalizeTabName((self:GetSelection() or {}).tab)
    if tabName == "Enhance" then
        payload.rankGroup = "all"
        payload.rankGroups = {}
        payload.ownedState = "all"
        payload.upgradeMode = "all"
        payload.longevity = "all"
        payload.binding = "all"
        payload.boe = "all"
        payload.slots = {}
    elseif tabName == "Wishlist" then
        payload.upgradeMode = "all"
        payload.longevity = "all"
    elseif tabName == "Gear Guide" then
        payload.upgradeMode = "all"
        payload.longevity = "all"
        payload.rankGroup = payload.recommendationCategory or "all"
        payload.rankGroups = {}
    end
    return payload
end

function UI:SaveWindow()
    if not self.frame or not accountDB() then
        return
    end

    local window = accountDB().profile.window
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
    local window = accountDB().profile.window
    local minWidth, minHeight, maxWidth, maxHeight = self:GetResizeBounds()
    local width = clamp(window.width or DEFAULT_WIDTH, minWidth, maxWidth)
    local height = clamp(window.height or DEFAULT_HEIGHT, minHeight, maxHeight)

    self.frame:SetSize(width, height)
    self.frame:SetScale(window.scale or 1)
    self.frame:ClearAllPoints()
    self.frame:SetPoint(window.point or "CENTER", UIParent, window.relativePoint or "CENTER", window.x or 0, window.y or 0)
end

function UI:ResetWindowLayout()
    local window = accountDB().profile.window
    window.point = "CENTER"
    window.relativePoint = "CENTER"
    window.x = 0
    window.y = 0
    window.width = DEFAULT_WIDTH
    window.height = DEFAULT_HEIGHT
    window.scale = 1
    window.inspectorVisible = false
    self:RestoreWindow()
    self:ApplyResizeBounds()
    self:SetStatusMessage("Window layout reset")
    self.bodyLayoutSignature = nil
    self:Invalidate("layout", "window-reset")
    self:ScheduleLayoutRefresh("window-reset")
end

function UI:GetClassDropdownItems()
    local selection = self:GetSelection()
    local items = {}
    for _, className in ipairs(BigBiSList:GetClassSpecIndex().classNames) do
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
    local specs = BigBiSList:GetClassSpecIndex().specsByClass[selection.class] or {}
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

function UI:GetFacetDropdownItems(values, labels, selectedValues, clearText, emptyText)
    local items = {}
    if tableHasAnyEnabled(selectedValues) then
        table.insert(items, {
            value = "__clear",
            text = clearText or "Clear",
            notCheckable = true,
        })
    end

    if #(values or {}) == 0 then
        table.insert(items, {
            value = "__empty",
            text = emptyText or "No options",
            disabled = true,
            notCheckable = true,
        })
        return items
    end

    for _, value in ipairs(values or {}) do
        table.insert(items, {
            value = value,
            text = labels[value] or value,
            checked = type(selectedValues) == "table" and selectedValues[value] == true,
            isNotRadio = true,
            keepShownOnClick = true,
        })
    end
    return items
end

function UI:GetFacetDropdownText(allLabel, prefix, selectedValues, labels)
    local count = selectedValuesCount(selectedValues)
    if count == 0 then
        return allLabel
    elseif count == 1 then
        local value = firstSelectedValue(selectedValues)
        return prefix .. ": " .. (labels[value] or value)
    end
    return prefix .. ": " .. tostring(count)
end

function UI:GetSourceDropdownItems()
    local filters = self:GetFilters()
    return self:GetFacetDropdownItems(self:GetAvailableSourceTypeValues(), BigBiSList:GetSourceTypeLabels(), filters.sourceTypes, "Clear sources", "No source options")
end

function UI:GetSourceDropdownText()
    return self:GetFacetDropdownText("All sources", "Sources", self:GetFilters().sourceTypes, BigBiSList:GetSourceTypeLabels())
end

function UI:GetZoneDropdownItems()
    local filters = self:GetFilters()
    return self:GetFacetDropdownItems(self:GetAvailableZoneValues(), {}, filters.zones, "Clear zones", "No zone options")
end

function UI:GetZoneDropdownText()
    return self:GetFacetDropdownText("All zones", "Zones", self:GetFilters().zones, {})
end

function UI:GetCostDropdownItems()
    local filters = self:GetFilters()
    return self:GetFacetDropdownItems(self:GetAvailableCostValues(), self:GetAvailableCostLabels(), filters.costs, "Clear costs", "No cost options")
end

function UI:GetCostDropdownText()
    local selected = self:GetFilters().costs
    local labels = tableHasAnyEnabled(selected) and self:GetAvailableCostLabels() or COST_FILTER_LABELS
    return self:GetFacetDropdownText("All costs", "Costs", selected, labels)
end

function UI:GetVendorDropdownItems()
    local filters = self:GetFilters()
    return self:GetFacetDropdownItems(self:GetAvailableVendorValues(), self:GetAvailableVendorLabels(), filters.vendors, "Clear vendors", "No vendor options")
end

function UI:GetVendorDropdownText()
    local selected = self:GetFilters().vendors
    local labels = tableHasAnyEnabled(selected) and self:GetAvailableVendorLabels() or {}
    return self:GetFacetDropdownText("All vendors", "Vendors", selected, labels)
end

function UI:GetReputationDropdownItems()
    local filters = self:GetFilters()
    return self:GetFacetDropdownItems(self:GetAvailableReputationValues(), {}, filters.reputations, "Clear reps", "No rep options")
end

function UI:GetReputationDropdownText()
    return self:GetFacetDropdownText("All reps", "Reps", self:GetFilters().reputations, {})
end

function UI:GetRankFilterValuesAndLabels()
    if self:IsLevelingMode() then
        return LEVELING_RANK_FILTER_ORDER, LEVELING_RANK_FILTER_LABELS
    end
    return RANK_FILTER_ORDER, RANK_FILTER_LABELS
end

local selectedFacetKeys

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
    local order, labels = self:GetRankFilterValuesAndLabels()
    local values = {}
    for _, value in ipairs(order) do
        if value ~= "all" then
            table.insert(values, value)
        end
    end
    return self:GetFacetDropdownItems(values, labels, filters.rankGroups, "Clear ranks", "No rank options")
end

function UI:GetRankDropdownText()
    local _, labels = self:GetRankFilterValuesAndLabels()
    if self:IsLevelingMode() then
        local selectedLabels = {}
        for _, value in ipairs(selectedFacetKeys(self:GetFilters().rankGroups, labels)) do
            if labels[value] then
                table.insert(selectedLabels, labels[value])
            end
        end
        if #selectedLabels == 0 then
            return "All categories"
        elseif #selectedLabels == 1 then
            return "Category: " .. selectedLabels[1]
        end
        return "Categories: " .. tostring(#selectedLabels)
    end
    return self:GetFacetDropdownText("All ranks", "Ranks", self:GetFilters().rankGroups, labels)
end

function UI:GetRecommendationCategoryDropdownItems()
    local state = self:GetViewState("Gear Guide")
    local labels = { all = "All recommendation categories" }
    for key, label in pairs(LEVELING_RANK_FILTER_LABELS) do
        labels[key] = label
    end
    return filterDropdownItems(LEVELING_RANK_FILTER_ORDER, labels, state.recommendationCategory or "all")
end

function UI:GetRecommendationCategoryDropdownText()
    local value = self:GetViewState("Gear Guide").recommendationCategory or "all"
    return value == "all" and "All recommendation categories"
        or ("Category: " .. (LEVELING_RANK_FILTER_LABELS[value] or value))
end

function UI:GetOwnedDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(OWNED_FILTER_ORDER, OWNED_FILTER_LABELS, filters.ownedState or "all")
end

function UI:GetUpgradeModeDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(UPGRADE_MODE_ORDER, UPGRADE_MODE_LABELS, filters.upgradeMode == "actual" and "candidates" or (filters.upgradeMode or "candidates"))
end

function UI:GetBoeDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(BOE_FILTER_ORDER, BOE_FILTER_LABELS, filters.boe or "all")
end

function UI:GetLongevityDropdownItems()
    local filters = self:GetFilters()
    return filterDropdownItems(LONGEVITY_FILTER_ORDER, LONGEVITY_FILTER_LABELS, filters.longevity or "all")
end

function UI:GetSlotDropdownItems()
    local values = {}
    local labels = {}
    for _, slotFilter in ipairs(BigBiSList:GetDisplaySlotFilters()) do
        table.insert(values, slotFilter.key)
        labels[slotFilter.key] = slotFilter.label
    end
    return self:GetFacetDropdownItems(values, labels, self:GetFilters().slots, "Clear slots", "No slot options")
end

function UI:GetSlotDropdownText()
    return self:GetFacetDropdownText("All slots", "Slots", self:GetFilters().slots, self:GetSlotFilterLabels())
end

local SORT_LABELS = {
    stat_rank = "Stat rank",
    priority = "Pursuit priority",
    rank = "Guide rating",
    item = "Item name",
    slot = "Slot",
    value = "Value",
    source = "Source",
    location = "Location",
    owned = "Owned",
    expansion = "Expansion value",
    recommendation = "Recommendation",
}

function UI:GetSortOptions()
    local viewKey = self:GetViewKey()
    if viewKey == "upgrades" then
        return { "priority", "slot", "item", "source", "location", "owned" }
    elseif viewKey == "bisList" then
        if BigBiSList.isForever then return { "stat_rank", "item", "source", "location", "owned" } end
        return { "rank", "item", "source", "location", "owned" }
    elseif viewKey == "gearGuide" then
        if BigBiSList.isForever then return { "stat_rank", "slot", "item", "source", "location", "owned" } end
        return { "priority", "slot", "item", "source", "location", "owned" }
    elseif viewKey == "enhancements" then
        return { "recommendation", "item", "slot", "source", "owned" }
    elseif viewKey == "wishlist" then
        return { "priority", "item", "slot", "source", "location", "owned" }
    end
    return { "slot", "item" }
end

function UI:GetSortDropdownItems()
    local selected = self:GetViewState().sort or self:GetSortOptions()[1]
    local items = {}
    for _, value in ipairs(self:GetSortOptions()) do
        table.insert(items, {
            text = SORT_LABELS[value] or value,
            value = value,
            checked = selected == value,
        })
    end
    local state = self:GetViewState()
    table.insert(items, { text = state.sortDirection == "asc" and "Ascending" or "Descending", value = "__direction", notCheckable = true })
    return items
end

function UI:GetSortDropdownText()
    local state = self:GetViewState()
    local sortKey = state.sort or self:GetSortOptions()[1]
    return SORT_LABELS[sortKey] or sortKey
end

function UI:GetDefaultSortDirection(sortKey)
    local view = self:GetViewKey()
    if sortKey == "priority" and (view == "gearGuide" or view == "wishlist") then return "asc" end
    return (sortKey == "item" or sortKey == "slot" or sortKey == "source" or sortKey == "location"
        or sortKey == "rank" or sortKey == "recommendation" or sortKey == "stat_rank") and "asc" or "desc"
end

function UI:SelectSort(sortKey)
    local state = self:GetViewState()
    if sortKey == "__direction" then
        state.sortDirection = state.sortDirection == "asc" and "desc" or "asc"
        self:Invalidate("presentation", "sort"); self:ScheduleRefresh(nil, "sort"); return
    end
    if state.sort ~= sortKey then
        state.sort = sortKey
        state.sortDirection = self:GetDefaultSortDirection(sortKey)
    end
    self:Invalidate("presentation", "sort")
    self:ScheduleRefresh(nil, "sort")
end

function UI:IsLevelingActivityView()
    return BigBiSList.isForever and self:GetViewKey() == "gearGuide"
        and self:IsLevelingMode() and self:GetViewState().groupBy == "activity"
end

function UI:GetGroupingDropdownItems()
    local tab = self:GetSelection().tab
    local state = self:GetViewState()
    local values = (tab == "Upgrades") and { "priority", "activity", "none" }
        or ((tab == "Wishlist") and { "activity", "none" } or { "slot", "activity", "none" })
    local items = filterDropdownItems(values, { priority = "By priority", activity = "By activity", slot = "By slot", none = "Ungrouped" }, state.groupBy or (tab == "Upgrades" and "priority" or (tab == "Wishlist" and "none" or "slot")))
    if self:IsLevelingActivityView() and not self.levelingActivity then return items end
    items[#items+1] = { text = "Expand all sections", value = "expand", notCheckable = true }
    items[#items+1] = { text = "Collapse all sections", value = "collapse", notCheckable = true }
    for _, entry in ipairs(self.renderModel and self.renderModel.entries or {}) do
        if entry.kind == "section" then items[#items+1] = { text = "Jump to " .. entry.title, value = "jump:" .. entry.sectionKey, notCheckable = true } end
    end
    return items
end

function UI:SelectGrouping(value)
    if value == "expand" or value == "collapse" then
        local state = self:GetViewState()
        state.collapsedGroups = {}
        for _, entry in ipairs(self.renderModel and self.renderModel.entries or {}) do
            if entry.kind == "section" and (value == "collapse" or entry.defaultCollapsed) then
                state.collapsedGroups[entry.sectionKey] = value == "collapse"
            end
        end
        self:Invalidate("presentation", "group-collapse"); self:ScheduleRefresh(nil, "group-collapse")
    elseif string.sub(value, 1, 5) == "jump:" then
        local key = string.sub(value, 6)
        for _, entry in ipairs(self.renderModel and self.renderModel.entries or {}) do
            if entry.sectionKey == key then self.contentScroll:SetVerticalScroll(entry.top); break end
        end
    else self:SetViewStateValue(nil, "groupBy", value) end
end

function UI:GetEnhancementTypeDropdownItems()
    local state = self:GetViewState("Enhance")
    return filterDropdownItems(
        { "all", "gem", "enchant", "consumable" },
        { all = "All enhancements", gem = "Gems", enchant = "Enchants", consumable = "Consumables" },
        state.type or "all"
    )
end

function UI:GetEnhancementAppliedDropdownItems()
    local state = self:GetViewState("Enhance")
    return filterDropdownItems(
        { "all", "missing", "applied" },
        { all = "All applied states", missing = "Missing", applied = "Applied / owned" },
        state.appliedState or "all"
    )
end

function UI:GetWishlistRelevanceDropdownItems()
    local state = self:GetViewState("Wishlist")
    local className = (self:GetSelection() or {}).class or "class"
    return filterDropdownItems(
        { "all", "selected", "class" },
        { all = "All saved items", selected = "Selected spec", class = "Any " .. className .. " spec" },
        state.relevance or "all"
    )
end

function UI:GetRowKey(data, mode)
    if not data then return nil end
    local entityType = data.entity_type or (data.spell_id and "spell") or "item"
    local entityId = data.entity_id or data.spell_id or data.item_id
    if not entityId then return nil end
    return table.concat({ entityType, tostring(entityId), tostring(data.slot or data.slot_key or ""),
        tostring(data.stat_identity or data.variant_id or data.variant_label or data.rank_label or "") }, "\031")
end

function UI:GetNavigationContextKey()
    local selection = self:GetSelection() or {}
    local progression = self:IsLevelingMode()
        and (BigBiSList.GetSelectedLevelingLevel and BigBiSList:GetSelectedLevelingLevel() or MAX_LEVELING_LEVEL)
        or selection.phase
    local key = { self:GetViewKey(), tostring(selection.mode), tostring(selection.class), tostring(selection.spec), tostring(progression) }
    if self:IsLevelingActivityView() then
        key[#key + 1] = "activity"
        key[#key + 1] = self.levelingActivity or ""
    end
    return table.concat(key, "\031")
end

function UI:ClearSelectedRow()
    self.pendingDetailsRequest = nil
    self.selectedItemId = nil
    self.selectedItemData = nil
    self.selectedItemMode = nil
    self.selectedEntityType = nil
    self.selectedRowKey = nil
    if self.detailsScroll and self.detailsScroll.SetVerticalScroll then self.detailsScroll:SetVerticalScroll(0) end
end

function UI:CaptureNavigationState()
    local scroll = self.contentScroll
    local state = {
        scroll = scroll and scroll.GetVerticalScroll and scroll:GetVerticalScroll() or 0,
        selectedRowKey = self.selectedRowKey,
        detailsScroll = self.detailsScroll and self.detailsScroll.GetVerticalScroll and self.detailsScroll:GetVerticalScroll() or 0,
    }
    for _, entry in ipairs((self.renderModel and self.renderModel.entries) or {}) do
        if entry.kind == "row" and entry.bottom > state.scroll then
            state.anchorKey = self:GetRowKey(entry.data, entry.mode)
            state.anchorOffset = state.scroll - entry.top
            break
        end
    end
    self.navigationStates = self.navigationStates or {}
    self.navigationStates[self.renderedContextKey or self:GetNavigationContextKey()] = state
    return state
end

function UI:BeginNavigationChange(reason)
    if reason ~= "filter" then self:SetSlotPickerOpen(false) end
    if self.IsSlotComparisonOpen and self:IsSlotComparisonOpen() then self:CloseSlotComparison() end
    if not self.pendingNavigation then self:CaptureNavigationState() end
    local restore = reason == "tab" or reason == "content-mode" or reason == "activity-overview"
    self.pendingNavigation = { restore = restore, reset = not restore }
    if reason ~= "filter" then self:ClearSelectedRow() end
end

function UI:ApplyNavigationState(model, state)
    local scroll = self.contentScroll
    if not scroll or not scroll.SetVerticalScroll then return end
    local offset = state and state.scroll or 0
    if state and state.anchorKey then
        for _, entry in ipairs(model and model.entries or {}) do
            if entry.kind == "row" and self:GetRowKey(entry.data, entry.mode) == state.anchorKey then
                offset = entry.top + (state.anchorOffset or 0)
                break
            end
        end
    end
    local viewport = scroll.GetHeight and scroll:GetHeight() or 0
    local height = self.contentChild and self.contentChild.GetHeight and self.contentChild:GetHeight() or ((model and model.cursor or 0) + 62)
    scroll:SetVerticalScroll(clamp(offset, 0, math.max(0, height - viewport)))
end

function UI:ApplySettingsNavigation()
    if self.pendingNavigation or self.renderedContextKey ~= self:GetNavigationContextKey() then
        self:ApplyNavigationState(nil, { scroll = 0 })
        self.renderedContextKey = self:GetNavigationContextKey()
        self.pendingNavigation = nil
    end
end

function UI:ApplyEmptyNavigation()
    self:ClearSelectedRow()
    self:ApplyNavigationState(nil, { scroll = 0 })
    self.renderedContextKey = self:GetNavigationContextKey()
    self.pendingNavigation = nil
end

function UI:OpenSettings(section)
    local selection = self:GetSelection()
    if normalizeTabName(selection.tab) ~= "Settings" then self.settingsReturnTab = selection.tab end
    self.settingsSection = lower(section or self.settingsSection or "appearance")
    self:SetTab("Settings")
end

function UI:ReturnFromSettings()
    self:SetTab(self.settingsReturnTab or (self:IsLevelingMode() and "Gear Guide" or "Upgrades"))
end

function UI:SetViewStateValue(viewName, key, value)
    if key ~= "groupBy" then self:BeginNavigationChange("filter") end
    if key == "upgradeMode" or key == "usefulness" then
        self:GetFilters(viewName)[key == "usefulness" and "longevity" or key] = value
    else
        self:GetViewState(viewName)[key] = value
    end
    self:Invalidate(key == "groupBy" and "presentation" or "query", "view-state")
    self:ScheduleRefresh(nil, "view-state")
end

function UI:SetContentMode(mode)
    self:BeginNavigationChange("content-mode")
    if BigBiSList.SetContentMode then
        BigBiSList:SetContentMode(mode)
    else
        self:GetSelection().mode = mode
    end
    if BigBiSList.Widgets.CloseDropdownMenus then
        BigBiSList.Widgets:CloseDropdownMenus()
    end
    self:Invalidate("query", "content-mode")
    self:ScheduleRefresh(nil, "content-mode")
end

function UI:UseMyCharacter()
    self:BeginNavigationChange("character-context")
    if BigBiSList.ResetClassSpecAutoSelection then
        BigBiSList:ResetClassSpecAutoSelection()
    end
    if BigBiSList.ApplyDetectedPlayerSelection then
        BigBiSList:ApplyDetectedPlayerSelection()
    end
    if BigBiSList.ResetLevelAutoSelection then BigBiSList:ResetLevelAutoSelection() end
    self:SetStatusMessage("Now viewing your current character")
    self:Invalidate("query", "character-context")
    self:ScheduleRefresh(nil, "character-context")
end

function UI:SetInspectorVisible(visible)
    if not visible and self.slotComparison and self.slotComparison.detailsOpen then
        self:BackToSlotComparison()
        return
    end
    if BigBiSList.SetInspectorVisible then
        BigBiSList:SetInspectorVisible(visible)
    elseif accountDB() and accountDB().profile and accountDB().profile.window then
        accountDB().profile.window.inspectorVisible = visible and true or false
    end
    self:Invalidate({ "layout", "details" }, "inspector")
    if not visible and self.dirtyDomains then
        self.dirtyDomains.details = nil
    end
    -- Bind cached item presentation only after the inspector is actually visible.
    self:ApplyBodyLayout()
    self:ScheduleLayoutRefresh("inspector")
    if visible and self.selectedItemId then
        self:RefreshDetails(self.selectedItemId, self.selectedItemData, self.selectedItemMode)
    end
end

function UI:IsInspectorVisible()
    if self.IsSlotComparisonOpen and self:IsSlotComparisonOpen() then
        return self.slotComparison and self.slotComparison.detailsOpen == true
    end
    if not self:ViewSupportsInspector() then
        return false
    elseif BigBiSList.IsInspectorVisible then
        return BigBiSList:IsInspectorVisible()
    end
    local window = accountDB() and accountDB().profile and accountDB().profile.window
    return window and window.inspectorVisible == true
end

function UI:ShowInspectorFor(entityId, data, mode)
    if self.IsSlotComparisonOpen and self:IsSlotComparisonOpen() and not self.slotComparison.detailsOpen then
        self:ShowComparisonDetails(data)
        return
    end
    if not self:ViewSupportsInspector() then
        return
    end
    local rowKey = self:GetRowKey(data or { item_id = entityId }, mode)
    if rowKey ~= self.selectedRowKey and self.detailsScroll and self.detailsScroll.SetVerticalScroll then
        self.detailsScroll:SetVerticalScroll(0)
    end
    self.selectedRowKey = rowKey
    self.selectedItemId = entityId
    self.selectedItemData = data
    self.selectedItemMode = mode
    self.selectedEntityType = data and (data.entity_type or (data.spell_id and "spell")) or "item"
    if self.UpdateVirtualList then self:UpdateVirtualList(true) end
    if not self:IsInspectorVisible() then
        self:SetInspectorVisible(true)
    else
        self:RefreshDetails(entityId, data, mode)
    end
end

function UI:SetClass(className)
    self:BeginNavigationChange("class")
    BigBiSList:MarkClassSpecSelectionManual()
    local index = BigBiSList:GetDataIndex()
    local specs = index.specsByClass[className] or {}
    BigBiSList:SetSelection(className, firstSpecName(specs), nil, nil)
    self:Invalidate("query", "class")
    self:ScheduleRefresh(nil, "class")
end

function UI:SetSpec(specName)
    self:BeginNavigationChange("spec")
    BigBiSList:MarkClassSpecSelectionManual()
    BigBiSList:SetSelection(nil, specName, nil, nil)
    self:Invalidate("query", "spec")
    self:ScheduleRefresh(nil, "spec")
end

function UI:SetPhase(phaseKey)
    if phaseKey == self:GetSelection().phase then return end
    self:BeginNavigationChange("phase")
    BigBiSList:SetSelection(nil, nil, phaseKey, nil)
    self:Invalidate("query", "phase")
    self:ScheduleRefresh(nil, "phase")
end

function UI:SetLevelingLevel(level)
    self:BeginNavigationChange("level")
    if BigBiSList.SetSelectedLevelingLevel then
        BigBiSList:SetSelectedLevelingLevel(level, true)
    end
    self:Invalidate("query", "level")
    self:ScheduleRefresh(nil, "level")
end

function UI:GetGearScenarioSelection()
    local selection = self:GetSelection()
    local phase = self:IsLevelingMode() and "LEVELING" or selection.phase
    local level = phase == "LEVELING" and BigBiSList:GetSelectedLevelingLevel() or 60
    return selection.class, selection.spec, phase, level
end

function UI:SetGearScenario(scenario)
    local addon = BigBiSList
    local class, spec, phase, level = self:GetGearScenarioSelection()
    local rating = addon.ForeverGearRating
    if scenario == rating:GetScenario(class, spec, phase, level)
        or scenario ~= rating:GetScenario(class, spec, phase, level, scenario) then return end
    self:BeginNavigationChange("scenario")
    addon:SetGearScenario(class, spec, phase, scenario)
    if addon.ForeverScoring then addon.ForeverScoring:Invalidate() end
    if addon.AcquisitionHighlights then addon.AcquisitionHighlights:InvalidateStorage() end
    if addon.ScheduleItemTooltipRefresh then addon:ScheduleItemTooltipRefresh() end
    self:Invalidate("query", "scenario")
    self:ScheduleRefresh(nil, "scenario")
end

function UI:SetTab(tabName, reason)
    if normalizeTabName(tabName) == normalizeTabName(self:GetSelection().tab) then return end
    if normalizeTabName(self:GetSelection().tab) ~= "Settings" then
        self.lastWorkspaceTab = self:GetSelection().tab
        if normalizeTabName(tabName) == "Settings" then self.settingsReturnTab = self.lastWorkspaceTab end
    end
    self:BeginNavigationChange(reason or "tab")
    BigBiSList:SetSelection(nil, nil, nil, normalizeTabName(tabName))
    if BigBiSList.Widgets.CloseDropdownMenus then
        BigBiSList.Widgets:CloseDropdownMenus()
    end
    self:Invalidate("query", "tab")
    self:ScheduleRefresh(nil, "tab")
end

function UI:SetFilter(key, value)
    self:BeginNavigationChange("filter")
    if key == "slots" and self:GetViewKey() == "gearGuide" then self.levelingSlotReference = nil end
    local filters = self:GetFilters()
    filters[key] = value
    self:Invalidate("query", "filter")
    self:ScheduleRefresh(nil, "filter")
end

function UI:ToggleFacetFilter(tableKey, value, scalarKey)
    if value == "__empty" then
        return
    elseif value == "__clear" then
        self:ClearFacetFilter(tableKey, scalarKey)
        return
    end

    self:BeginNavigationChange("filter")
    local filters = self:GetFilters()
    filters[tableKey] = type(filters[tableKey]) == "table" and filters[tableKey] or {}
    filters[tableKey][value] = not filters[tableKey][value] or nil
    if scalarKey then
        filters[scalarKey] = "all"
    end
    self:Invalidate("query", "filter-facet")
    self:ScheduleRefresh(nil, "filter-facet")
end

function UI:ClearFacetFilter(tableKey, scalarKey)
    self:BeginNavigationChange("filter")
    local filters = self:GetFilters()
    filters[tableKey] = {}
    if scalarKey then
        filters[scalarKey] = "all"
    end
    self:Invalidate("query", "filter-facet-clear")
    self:ScheduleRefresh(nil, "filter-facet-clear")
end

function UI:ClearFacetValue(tableKey, value, scalarKey)
    self:BeginNavigationChange("filter")
    local filters = self:GetFilters()
    if type(filters[tableKey]) == "table" then
        filters[tableKey][value] = nil
    end
    if scalarKey then
        filters[scalarKey] = "all"
    end
    self:Invalidate("query", "filter-chip")
    self:ScheduleRefresh(nil, "filter-chip")
end

function UI:ToggleSlot(slotName)
    self:BeginNavigationChange("filter")
    if self:GetViewKey() == "gearGuide" then self.levelingSlotReference = nil end
    local filters = self:GetFilters()
    filters.slots = filters.slots or {}
    filters.slots[slotName] = not filters.slots[slotName] or nil
    self:Invalidate("query", "slot-filter")
    self:ScheduleRefresh(nil, "slot-filter")
end

function UI:ClearFilters()
    self:BeginNavigationChange("filter")
    local filters = self:GetFilters()
    filters.search = ""
    filters.sourceType = "all"
    filters.sourceTypes = {}
    filters.zone = "all"
    filters.zones = {}
    filters.cost = "all"
    filters.costs = {}
    filters.vendor = "all"
    filters.vendors = {}
    filters.reputation = "all"
    filters.reputations = {}
    filters.rankGroup = "all"
    filters.rankGroups = {}
    filters.ownedState = "all"
    filters.upgradeMode = "candidates"
    filters.includeEarlier = self:GetViewKey() == "upgrades"
    filters.binding = "all"
    filters.boe = "all"
    filters.faction = "all"
    filters.longevity = "all"
    filters.slots = {}

    local tabName = normalizeTabName((self:GetSelection() or {}).tab)
    if tabName == "Gear Guide" then
        self.levelingSlotReference = nil
        self:GetViewState("Gear Guide").recommendationCategory = "all"
    elseif tabName == "Enhance" then
        local state = self:GetViewState("Enhance")
        state.type = "all"
        state.appliedState = "all"
    elseif tabName == "Wishlist" then
        self:GetViewState("Wishlist").relevance = "all"
    end

    if self.searchBox then
        self.searchBox:SetText("")
        self.searchBox:ClearFocus()
    end

    self:SetFilterDrawerOpen(false)
    self:Invalidate("query", "clear-filters")
    self:ScheduleRefresh(nil, "clear-filters")
end

function UI:SetItemCollectionState(collectionName, itemId, value, message, reason)
    if not itemId then return end
    local char = BigBiSList:GetCharacterDB()
    local key = tostring(itemId)
    local previous = char[collectionName][key]
    if previous == value then return end
    local item = BigBiSList.GetItemData and BigBiSList:GetItemData(itemId)
    local name = item and item.name or ("Item " .. key)
    char[collectionName][key] = value
    self:SetStatusMessage(message .. name, {
        label = "Undo: " .. message .. name,
        callback = function() char[collectionName][key] = previous end,
    })
    self:Invalidate("query", reason)
    self:ScheduleRefresh(nil, reason)
end

function UI:UndoLastAction()
    local action = self.undoAction
    if not action then return false end
    if GetTime and GetTime() >= action.expiresAt then
        self.undoAction = nil
        if self.undoButton then self.undoButton:Hide() end
        return false
    end
    self.undoAction = nil
    action.callback()
    self:SetStatusMessage("Undone: " .. (action.message or "last action"))
    self:Invalidate("query", "undo")
    self:ScheduleRefresh(nil, "undo")
    return true
end

function UI:AddWishlist(itemId)
    self:SetItemCollectionState("wishlist", itemId, true, "Saved to Wishlist: ", "wishlist-add")
end

function UI:RemoveWishlist(itemId)
    self:SetItemCollectionState("wishlist", itemId, nil, "Removed from Wishlist: ", "wishlist-remove")
end

function UI:IgnoreItem(itemId)
    self:SetItemCollectionState("ignoredItems", itemId, true, "Hidden: ", "hide-item")
end

function UI:UnignoreItem(itemId)
    self:SetItemCollectionState("ignoredItems", itemId, nil, "Restored: ", "restore-item")
end

function UI:RestoreAllHiddenItems()
    local char = BigBiSList:GetCharacterDB()
    local previous = copyStateValues(char.ignoredItems)
    char.ignoredItems = {}
    self:SetStatusMessage("All hidden items restored", {
        label = "Undo restoring hidden items",
        callback = function() char.ignoredItems = previous end,
    })
    self:Invalidate("query", "restore-items")
    self:ScheduleRefresh(nil, "restore-items")
end

local function equippedLinkName(data, mode)
    local link = mode == "gear" and data and data.item_link
    return link and link:match("|h%[(.-)%]|h")
end

local function applyItemPresentation(button, itemId, bindToken, presentation)
    if not button or button.itemId ~= itemId or button.itemBindToken ~= bindToken then
        return
    end
    if button.IsVisible and not button:IsVisible() then
        return
    elseif not button.IsVisible and button.IsShown and not button:IsShown() then
        return
    end
    if presentation.texture then
        button.icon:SetTexture(presentation.texture)
    end
    if presentation.name and button.boundNameText then
        local label = button.boundNameText
        local name = equippedLinkName(button.detailData, button.detailMode) or presentation.name
        BigBiSList.Widgets:SetCellText(label, name, label.maxLines or 1, label.lineHeight or 14, label:GetWidth())
    end
    if presentation.link and not (button.detailData and button.detailData.item_link) then
        button.itemLink = presentation.link
    end
    if presentation.quality and button.boundNameText then
        local r, g, b = BigBiSList.Widgets:GetRankColor(presentation.quality)
        button.boundNameText:SetTextColor(r, g, b, 1)
    end
    if presentation.name and button.OnItemNameChanged then button:OnItemNameChanged() end
end

local function ensureEntityButtonScripts(button)
    if button.__bigBisEntityScripts then
        return
    end
    button.__bigBisEntityScripts = true
    BigBiSList.Widgets:BindTooltip(button, function(selfButton)
        GameTooltip:SetOwner(selfButton, "ANCHOR_RIGHT", 4, 0)
        if selfButton.entityType == "spell" then
            if selfButton.spellLink then
                GameTooltip:SetHyperlink(selfButton.spellLink)
            elseif GameTooltip.SetSpellByID then
                GameTooltip:SetSpellByID(selfButton.spellId)
            else
                GameTooltip:SetText(selfButton.boundFallbackName or ("Spell " .. tostring(selfButton.spellId)))
            end
        elseif selfButton.itemLink then
            GameTooltip:SetHyperlink(selfButton.itemLink)
        else
            GameTooltip:SetText(selfButton.boundFallbackName or ("Item " .. tostring(selfButton.itemId)))
        end
        GameTooltip:Show()
    end)
    button:SetScript("OnClick", function(selfButton, buttonName)
        UI:HandleEntityGesture(selfButton.detailData, selfButton.detailMode, buttonName, selfButton)
    end)
end

function UI:ResetEntityButton(button, nameText, fallbackName)
    button.itemBindToken = (button.itemBindToken or 0) + 1
    button.entityType = nil
    button.entityId = nil
    button.itemId = nil
    button.spellId = nil
    button.itemLink = nil
    button.spellLink = nil
    button.detailData = nil
    button.detailMode = nil
    button.boundNameText = nameText
    button.boundFallbackName = fallbackName or "Empty"
    button.icon:SetDesaturated(true)
    button.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
    safeSetText(nameText, button.boundFallbackName)
    if nameText then nameText.fullText = button.boundFallbackName end
end

function UI:SetItemButton(button, itemId, nameText, fallbackName, fallbackQuality, detailData, detailMode)
    button.itemBindToken = (button.itemBindToken or 0) + 1
    local bindToken = button.itemBindToken
    button.entityType = "item"
    button.entityId = itemId
    button.itemId = itemId
    button.spellId = nil
    button.itemLink = detailData and detailData.item_link or nil
    button.spellLink = nil
    button.detailData = detailData
    button.detailMode = detailMode
    button.boundNameText = nameText
    button.boundFallbackName = equippedLinkName(detailData, detailMode) or fallbackName or ("Item " .. tostring(itemId))
    button.icon:SetDesaturated(false)
    button.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")

    safeSetText(nameText, button.boundFallbackName)
    if nameText then nameText.fullText = button.boundFallbackName end
    if nameText then
        local r, g, b = itemQualityColor({ quality = fallbackQuality })
        nameText:SetTextColor(r, g, b, 1)
    end

    ensureEntityButtonScripts(button)

    self.itemPresentationCache = self.itemPresentationCache or {}
    self.pendingItemLoads = self.pendingItemLoads or {}
    local cached = self.itemPresentationCache[itemId]
    if cached and cached.loaded then
        applyItemPresentation(button, itemId, bindToken, cached)
        return
    end

    local itemName, itemLink, itemQuality, _, _, _, _, _, _, itemTexture = self:GetItemInfo(itemId)
    if itemName and itemTexture then
        cached = { name = itemName, link = itemLink, quality = itemQuality, texture = itemTexture, loaded = true }
        self.itemPresentationCache[itemId] = cached
        applyItemPresentation(button, itemId, bindToken, cached)
        return
    end

    local pending = self.pendingItemLoads[itemId]
    if not pending then
        pending = { subscribers = {} }
        self.pendingItemLoads[itemId] = pending
    end
    pending.subscribers[button] = bindToken
    self:RequestItemPresentation(itemId)
end

function UI:RequestItemPresentation(itemId)
    local pending = self.pendingItemLoads and self.pendingItemLoads[itemId]
    if not pending then return end
    if pending.requested or not (Item and Item.CreateFromItemID) then
        return
    end

    pending.requested = true
    self:CountPerformance("itemLoadRequests")
    local itemObject = Item:CreateFromItemID(itemId)
    itemObject:ContinueOnItemLoad(function()
        UI:CountPerformance("itemLoadCallbacks")
        local loadedName = itemObject.GetItemName and itemObject:GetItemName()
        local loadedLink = itemObject.GetItemLink and itemObject:GetItemLink()
        local loadedIcon = itemObject.GetItemIcon and itemObject:GetItemIcon()
        local _, _, loadedQuality = UI:GetItemInfo(itemId)
        local presentation = {
            name = loadedName,
            link = loadedLink,
            quality = loadedQuality,
            texture = loadedIcon,
            loaded = true,
        }
        UI.itemPresentationCache = UI.itemPresentationCache or {}
        UI.itemPresentationCache[itemId] = presentation
        local completed = UI.pendingItemLoads[itemId]
        UI.pendingItemLoads[itemId] = nil
        for subscriber, token in pairs(completed and completed.subscribers or {}) do
            applyItemPresentation(subscriber, itemId, token, presentation)
        end
        if completed and completed.statRating and BigBiSList.ForeverGearRating then
            BigBiSList.ForeverGearRating:InvalidateItem(itemId)
        end
        if completed and completed.ownedMetadata then
            UI.ownedItemMetadataResolved = UI.ownedItemMetadataResolved or {}
            UI.ownedItemMetadataResolved[itemId] = true
            UI:Invalidate("ownership", "owned-item-info")
            UI:ScheduleRefresh(nil, "owned-item-info")
        elseif completed and completed.statRating then
            UI:Invalidate("query", "gear-stats")
            UI:ScheduleRefresh(nil, "gear-stats")
        end
        if completed and (completed.statRating or completed.ownedMetadata) and BigBiSList.isForever
            and BigBiSList.ScheduleItemTooltipRefresh then
            BigBiSList:ScheduleItemTooltipRefresh(itemId)
        end
        if completed and completed.statRating and BigBiSList.AcquisitionHighlights then
            BigBiSList.AcquisitionHighlights:InvalidateStorage()
        end
    end)
end

function UI:QueueStatLoads(pending)
    for itemId in pairs(pending or {}) do
        self.pendingItemLoads = self.pendingItemLoads or {}
        local request = self.pendingItemLoads[itemId] or { subscribers = {} }
        self.pendingItemLoads[itemId] = request
        request.statRating = true
        self:RequestItemPresentation(itemId)
    end
end

function UI:SetSpellButton(button, spellId, nameText, fallbackName, detailData, detailMode)
    button.itemBindToken = (button.itemBindToken or 0) + 1
    button.entityType = "spell"
    button.entityId = spellId
    button.itemId = nil
    button.spellId = spellId
    button.itemLink = nil
    button.spellLink = nil
    button.detailData = detailData
    button.detailMode = detailMode
    button.boundFallbackName = fallbackName or ("Spell " .. tostring(spellId))
    button.boundNameText = nameText
    button.icon:SetDesaturated(false)
    button.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")

    safeSetText(nameText, button.boundFallbackName)
    if nameText then nameText.fullText = button.boundFallbackName end
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
            nameText.fullText = spellName
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

    ensureEntityButtonScripts(button)
end

local function enhancementEffectIdsContain(effectIds, effectId)
    local numericEffectId = tonumber(effectId)
    if not numericEffectId then
        return false
    end

    for _, candidate in ipairs(effectIds or {}) do
        if tonumber(candidate) == numericEffectId then
            return true
        end
    end
    return false
end

local function gemIdsContain(gemIds, gemId)
    local numericGemId = tonumber(gemId)
    if not numericGemId then
        return false
    end

    for _, candidate in ipairs(gemIds or {}) do
        if tonumber(candidate) == numericGemId then
            return true
        end
    end
    return false
end

local function slotMatchesEnhancement(instance, data)
    local matchSlot = data and data.match_slot
    if not matchSlot or matchSlot == "" then
        return true
    end

    if enhancementSlotsContain(instance and instance.slots, matchSlot) then
        return true
    end

    local equipLocation = instance and (instance.equip_location or getItemEquipLocation(instance.item_id))
    return enhancementSlotsContain(enhancementSlotsForEquipLocation(equipLocation), matchSlot)
end

local function enhancementInstanceItemName(instance)
    local itemName = itemNameFromLink(instance and instance.item_link)
    if itemName and itemName ~= "" then
        return itemName
    end

    if instance and instance.item_id then
        itemName = UI:GetItemInfo(instance.item_id)
        if itemName and itemName ~= "" then
            return itemName
        end
    end

    local item = instance and instance.item_id and BigBiSList.GetItemData and BigBiSList:GetItemData(instance.item_id)
    return (item and item.name) or ("Item " .. tostring(instance and instance.item_id or ""))
end

local function enhancementInstanceLine(instance)
    local location = instance and (instance.location_label or ownershipStateLabel(instance.state)) or "Item"
    local slot = instance and instance.slot
    if slot and slot ~= "" then
        return location .. " " .. slot .. ": " .. enhancementInstanceItemName(instance)
    end
    return location .. ": " .. enhancementInstanceItemName(instance)
end

local function sortEnhancementMatches(a, b)
    local aSort = ENHANCEMENT_LOCATION_SORT[a.state or "missing"] or 99
    local bSort = ENHANCEMENT_LOCATION_SORT[b.state or "missing"] or 99
    if aSort ~= bSort then
        return aSort < bSort
    end
    return enhancementInstanceItemName(a) < enhancementInstanceItemName(b)
end

local function enhancementAppliedLabel(state, stateCount, totalCount)
    local label = ownershipStateLabel(state)
    if stateCount and stateCount > 1 then
        return label .. " x" .. tostring(stateCount)
    elseif totalCount and totalCount > 1 then
        return label .. " +" .. tostring(totalCount - 1)
    end
    return label
end

function UI:GetEnhancementAppliedMatches(data)
    if not data or (data.enhancement_kind ~= "gem" and data.enhancement_kind ~= "enchant") then
        return {}
    end

    local owned = self:GetOwnedSnapshot()
    local matches = {}
    for _, instance in ipairs(owned.enhancementItems or {}) do
        if data.enhancement_kind == "gem" then
            if gemIdsContain(instance.gem_ids, data.gem_item_id or data.item_id) then
                table.insert(matches, instance)
            end
        elseif data.enhancement_kind == "enchant"
            and instance.enchant_id
            and enhancementEffectIdsContain(data.enchant_effect_ids, instance.enchant_id)
            and slotMatchesEnhancement(instance, data) then
            table.insert(matches, instance)
        end
    end

    table.sort(matches, sortEnhancementMatches)
    return matches
end

function UI:GetEnhancementAppliedSummary(data)
    local cacheKey = data and (data.enhancement_key
        or table.concat({ tostring(data.enhancement_kind or ""), tostring(data.item_id or data.spell_id or ""), tostring(data.enhancement_slot or data.slot or "") }, ":"))
    self.currentEnhancementAppliedCache = self.currentEnhancementAppliedCache or {}
    if cacheKey and self.currentEnhancementAppliedCache[cacheKey] then
        return self.currentEnhancementAppliedCache[cacheKey]
    end
    local matches = self:GetEnhancementAppliedMatches(data)
    local owned = self.currentOwned
    if #matches == 0 then
        local enhancementType = data and data.enhancement_kind == "gem" and "gem" or "enchant"
        local detail = "No matching applied " .. enhancementType .. " found on equipped gear or bags."
        if owned and (not owned.bankScanned or (owned.bankLinkCount or 0) == 0) then
            detail = detail .. " Open your bank once to include banked gear."
        end
        local summary = {
            state = "missing",
            label = "Not applied",
            title = "Applied",
            detail = detail,
        }
        if cacheKey then self.currentEnhancementAppliedCache[cacheKey] = summary end
        return summary
    end

    local bestState = matches[1].state or "missing"
    local stateCounts = {}
    for _, match in ipairs(matches) do
        local state = match.state or "missing"
        stateCounts[state] = (stateCounts[state] or 0) + 1
        if (OWNERSHIP_PRIORITY[state] or 0) > (OWNERSHIP_PRIORITY[bestState] or 0) then
            bestState = state
        end
    end

    local lines = {}
    for index, match in ipairs(matches) do
        if index > 5 then
            table.insert(lines, "+" .. tostring(#matches - 5) .. " more")
            break
        end
        table.insert(lines, enhancementInstanceLine(match))
    end

    local summary = {
        state = bestState,
        label = enhancementAppliedLabel(bestState, stateCounts[bestState], #matches),
        title = "Applied",
        detail = "Detected from equipped gear, bags, and your latest bank scan.",
        lines = lines,
    }
    if cacheKey then self.currentEnhancementAppliedCache[cacheKey] = summary end
    return summary
end

function UI:GetOwnershipState(itemId, itemIds)
    local bestState = itemId and self.currentOwned and self.currentOwned[itemId] or nil

    for _, candidateItemId in ipairs(itemIds or {}) do
        local candidateState = self.currentOwned and self.currentOwned[candidateItemId]
        if candidateState == "equipped" then
            return "equipped"
        elseif candidateState and (OWNERSHIP_PRIORITY[candidateState] or 0) > (OWNERSHIP_PRIORITY[bestState or "missing"] or 0) then
            bestState = candidateState
        end
    end

    return bestState or (self.currentOwned and self.currentOwned.inventoryIncomplete and "unknown") or "missing"
end

function UI:GetRowOwnershipState(data)
    if not data then
        return nil
    end
    if data.build_target then return data.owned_state end
    if BigBiSList.isForever and data.variant_id then
        local owned = self.currentOwned or {}
        return (owned.variants and owned.variants[data.variant_id])
            or ((owned.inventoryIncomplete or (owned.variantUnknownItems and owned.variantUnknownItems[data.item_id])) and "unknown")
            or "missing"
    end
    if data.enhancement_kind == "gem" or data.enhancement_kind == "enchant" then
        local summary = self:GetEnhancementAppliedSummary(data)
        data.ownership_label = summary.label
        data.ownership_title = summary.title
        data.ownership_detail = summary.detail
        data.ownership_lines = summary.lines
        return summary.state
    end
    if data.ownership_state == "missing" and self.currentOwned and self.currentOwned.inventoryIncomplete then
        return "unknown"
    end
    if data.ownership_state then
        return data.ownership_state
    end
    if data.item_id or data.item_ids then
        return self:GetOwnershipState(data.item_id, data.item_ids)
    end
    return nil
end

function UI:CreateOwnershipBadge(parent, state, data, badge)
    local widgets = BigBiSList.Widgets
    local color = OWNERSHIP_COLORS[state] or OWNERSHIP_COLORS.missing
    local label = data and data.ownership_label or ownershipStateLabel(state)
    local title = data and data.ownership_title or "Owned"
    if not badge then
        badge = widgets:CreateStatusBadge(parent, label, HAVE_COLUMN_WIDTH, 18, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })
        badge:EnableMouse(true)
        self:CountPerformance("widgetsCreated")
    end
    badge:SetParent(parent)
    badge.boundState = state
    badge.boundData = data
    badge.boundTitle = title
    badge.label:SetText(label)
    widgets:SetBackdrop(badge, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })

    if not badge.__bigBisOwnershipScripts then
        badge.__bigBisOwnershipScripts = true
        badge:SetScript("OnEnter", function(selfBadge)
        local boundData = selfBadge.boundData
        local boundState = selfBadge.boundState
        GameTooltip:SetOwner(selfBadge, "ANCHOR_RIGHT")
        GameTooltip:AddLine(selfBadge.boundTitle or "Owned", 1, 0.82, 0.28)
        GameTooltip:AddLine(selfBadge.label:GetText() or "", 0.86, 0.86, 0.86)
        for _, line in ipairs(boundData and boundData.ownership_lines or {}) do
            GameTooltip:AddLine(line, 0.62, 0.78, 0.94, true)
        end
        if boundData and boundData.ownership_detail and boundData.ownership_detail ~= "" then
            GameTooltip:AddLine(boundData.ownership_detail, 0.62, 0.62, 0.66, true)
        end
        if boundState == "bank" and UI.currentOwned and UI.currentOwned.bankUpdatedAt and UI.currentOwned.bankUpdatedAt ~= "" then
            GameTooltip:AddLine("Bank cache: " .. UI.currentOwned.bankUpdatedAt, 0.62, 0.62, 0.66)
        end
        GameTooltip:Show()
        end)
        badge:SetScript("OnLeave", function() GameTooltip:Hide() end)
    end

    return badge
end

function UI:CreateAccessBadge(parent, state, data, badge)
    local widgets = BigBiSList.Widgets
    local color = ACCESS_COLORS[state] or ACCESS_COLORS.unknown
    if not badge then
        badge = widgets:CreateStatusBadge(parent, "", GET_COLUMN_WIDTH, 18, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })
        badge:EnableMouse(true)
        self:CountPerformance("widgetsCreated")
    end
    badge:SetParent(parent)
    badge.boundState = state
    badge.boundData = data
    badge.label:SetText(self:GetAccessBadgeLabel(state, data))
    widgets:SetBackdrop(badge, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })

    if not badge.__bigBisAccessScripts then
        badge.__bigBisAccessScripts = true
        badge:SetScript("OnEnter", function(selfBadge)
            UI:ShowAcquisitionTooltip(selfBadge, selfBadge.boundData)
        end)
        badge:SetScript("OnLeave", function() GameTooltip:Hide() end)
    end

    return badge
end

function UI:CreateRankBadge(parent, labelText, kind, data, mode, badge)
    local widgets = BigBiSList.Widgets
    local color = RANK_COLORS[kind] or RANK_COLORS.backup
    if not badge then
        badge = widgets:CreateStatusBadge(parent, "", RANK_COLUMN_WIDTH, 18, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })
        badge:EnableMouse(true)
        self:CountPerformance("widgetsCreated")
    end
    badge:SetParent(parent)
    badge.boundData = data
    badge.boundMode = mode
    badge.label:SetText(labelText or "")
    widgets:SetBackdrop(badge, { color[1], color[2], color[3], color[4] }, { color[5], color[6], color[7], color[8] })

    if not badge.__bigBisRankScripts then
        badge.__bigBisRankScripts = true
        badge:SetScript("OnEnter", function(selfBadge)
        local data = selfBadge.boundData
        GameTooltip:SetOwner(selfBadge, "ANCHOR_RIGHT")
        GameTooltip:AddLine("Rank", 1, 0.82, 0.28)
        GameTooltip:AddLine(rankMeaning(data, selfBadge.boundMode), 0.86, 0.86, 0.86, true)
        local upgradeText = upgradeComparisonText(data)
        if upgradeText then
            GameTooltip:AddLine(upgradeText, 0.62, 0.78, 0.94, true)
        end
        GameTooltip:Show()
        end)
        badge:SetScript("OnLeave", function() GameTooltip:Hide() end)
    end

    return badge
end

function UI:GetRowRecommendationHistory(data)
    if not data or not data.item_id or data.leveling or self:IsLevelingMode() or not BigBiSList.GetRecommendationHistory then return nil end
    local selection = self:GetItemContext()
    return BigBiSList:GetRecommendationHistory(data.item_id, selection.class, selection.spec, selection.phase, data.slot)
end

function UI:GetHistoryRecommendationText(data)
    local history = self:GetRowRecommendationHistory(data)
    if not history then return BigBiSList:GetGuideRatingDisplay(data and data.rank_label) or "No guide data" end
    local cell = history.selected and history.selected.matched and history.selected or history.latest_earlier
    local label = cell and ((cell.phase_label or BigBiSList:GetPhaseDisplayName(cell.phase)) .. ": " .. cell.label)
        or (history.selected and history.selected.label) or "No guide data"
    if BigBiSList.isForever then label = BigBiSList:GetGuideRatingDisplay(label) end
    local future = history.future_summary
    return label .. (future and future.has_future and ("\n" .. future.text) or "")
end

function UI:GetRowRecommendationText(data, mode)
    if data and data.item_id and not data.leveling and not self:IsLevelingMode() and mode ~= "leveling" and mode ~= "enhance" and BigBiSList.GetRecommendationHistory then
        return self:GetHistoryRecommendationText(data)
    end
    if data and data.recommendation_summary and data.recommendation_summary ~= "" then
        return data.recommendation_summary
    end

    if mode == "planner" then
        return table.concat(data and data.reasons or {}, ", ")
    elseif mode == "leveling" then
        return data and (data.level_label or data.level_value_text) or "Leveling recommendation"
    elseif mode == "enhance" then
        return data and data.detail or "Enhancement"
    elseif mode == "wishlist" then
        return data and data.detail or "Saved item"
    elseif data and data.rank_label then
        return displayRankInfo(data, mode)
    end

    return "Optional"
end

function UI:SetViewSort(sortKey)
    local state = self:GetViewState()
    if state.sort == sortKey then
        state.sortDirection = state.sortDirection == "desc" and "asc" or "desc"
    else
        state.sort = sortKey
        state.sortDirection = self:GetDefaultSortDirection(sortKey)
    end
    self:Invalidate("presentation", "sort")
    self:ScheduleRefresh(nil, "sort")
end

function UI:GetRowAcquisitionDisplay(data)
    if data and data.acquisition_display then
        local display = data.acquisition_display
        local source = display.source_label or display.source or data.source_filter_label or data.source_type_label or "Unknown"
        local location = display.location_label or display.location or display.summary or data.source_summary or "—"
        if display.future and display.acquisition_phase then
            location = location .. "\nAvailable in " .. BigBiSList:GetPhaseDisplayName(display.acquisition_phase)
        elseif data.source_live_future and display.acquisition_phase then
            location = location .. "\nFuture content: " .. BigBiSList:GetPhaseDisplayName(display.acquisition_phase)
        end
        return source, location, display.status or (display.available and "ready" or "unknown")
    end
    local evaluation = self:GetAccessEvaluation(data or {})
    local optionEvaluation = evaluation and evaluation.optionEvaluation
    local option = optionEvaluation and optionEvaluation.option
    local source = accessSourceBadgeLabel(option)
        or (data and (data.source_filter_label or data.source_type_label))
        or "Unknown"
    local location = option and (option.source_summary or option.label)
        or (data and data.source_summary)
        or ""
    if option and option.cost_summary and option.cost_summary ~= "" and not string.find(location, option.cost_summary, 1, true) then
        location = location ~= "" and (location .. "\n" .. option.cost_summary) or option.cost_summary
    end
    if location == "" then
        location = "—"
    end
    return source, location, evaluation and evaluation.status or "unknown"
end

function UI:GetRowSlotDisplay(data)
    if data and data.slot_label and data.slot_label ~= "" then
        return data.slot_label
    end
    if data and type(data.slots) == "table" and #data.slots > 0 then
        return table.concat(data.slots, ", ")
    end
    return data and (data.for_label or data.slot or data.enhancement_slot or data.kind_label) or "—"
end

function UI:GetGearUsefulThrough(data)
    if not data or not data.item_id then
        return "—"
    end
    if data.leveling then
        if data.level_max then
            return "Level " .. tostring(data.level_max)
        end
        return data.level_label or "Leveling"
    end

    local selection = self:GetSelection()
    local latestPhase
    local latestIndex = 0
    for _, use in ipairs(BigBiSList:GetItemUses(data.item_id, selection.phase) or {}) do
        if use.class == selection.class and use.spec == selection.spec then
            local index = phaseOrderIndex(use.phase)
            if index > latestIndex and index < 999 then
                latestIndex = index
                latestPhase = use.phase
            end
        end
    end
    return latestPhase and BigBiSList:GetPhaseDisplayName(latestPhase) or "Not ranked"
end

function UI:GetWishlistExpansionText(data)
    if data and data.item_id and BigBiSList.GetRecommendationHistory and not self:IsLevelingMode() then
        return self:GetHistoryRecommendationText(data)
    end
    local rankings = data and (data.relevant_spec_rankings or data.spec_rankings) or {}
    local selected
    for _, ranking in ipairs(rankings) do if ranking.selected then selected = ranking; break end end
    if not selected then return data and data.not_ranked_label or "Not ranked for selected spec" end
    local matrix = selected.phases or selected.phase_rankings or selected.ranks_by_phase or {}
    local phase = data.selected_phase or self:GetSelection().phase
    local current = matrix[phase]
    local label = type(current) == "table" and (current.display_rank_label or current.short_label or current.label or current.rank_label) or current
    return label or "Not listed in selected tier"
end

local function createGridText(parent, column, text, color, template, label)
    label = label or parent:CreateFontString(nil, "OVERLAY", template or "GameFontNormalSmall")
    label:ClearAllPoints()
    label:SetPoint("TOPLEFT", parent, "TOPLEFT", column.x, -ROW_VERTICAL_PADDING)
    label:SetWidth(column.width)
    label:SetJustifyH(column.align or "LEFT")
    label:SetWordWrap(true)
    label:SetTextColor((color and color[1]) or 0.76, (color and color[2]) or 0.76, (color and color[3]) or 0.80, 1)
    label:SetText(text or "")
    label:Show()
    return label
end

function UI:CreateListColumnHeader(parent, yOffset, mode, header)
    local width = self:GetTableViewportWidth(parent, self.contentScroll and self.contentScroll:GetWidth() or 760)
    local layout = self:GetTableColumnLayout(width, mode)
    if not header then
        header = CreateFrame("Frame", nil, parent)
        header.columnButtons = {}
        header.__bigBisManaged = true
        self:CountPerformance("widgetsCreated")
    end
    header:SetParent(parent)
    header:Show()
    header:ClearAllPoints()
    header:SetHeight(COLUMN_HEADER_HEIGHT)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    header.columnLayout = layout

    header.columnButtons = header.columnButtons or {}
    for _, button in ipairs(header.columnButtons) do
        button:Hide()
    end

    local viewState = self:GetViewState()
    for index, column in ipairs(layout.columns) do
        local button = header.columnButtons[index]
        if not button then
            button = CreateFrame("Button", nil, header)
            local label = button:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
            label:SetPoint("TOPLEFT", button, "TOPLEFT", 0, 0)
            label:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -16, 0)
            label:SetWordWrap(false)
            button.label = label
            button.sortIcon = button:CreateTexture(nil, "ARTWORK")
            button.sortIcon:SetSize(12,12)
            button.sortIcon:SetPoint("RIGHT", button, "RIGHT", -1, 0)
            button:SetScript("OnClick", function(selfButton)
                if selfButton.sortable and selfButton.columnKey then
                    UI:SetViewSort(selfButton.columnKey)
                end
            end)
            button:SetScript("OnEnter", function(selfButton)
                if selfButton.sortable then
                    selfButton.label:SetTextColor(1, 0.82, 0.28, 1)
                end
            end)
            button:SetScript("OnLeave", function(selfButton)
                selfButton.label:SetTextColor(0.68, 0.68, 0.72, 1)
            end)
            header.columnButtons[index] = button
            self:CountPerformance("widgetsCreated")
        end
        button:Show()
        button:ClearAllPoints()
        button:SetPoint("TOPLEFT", header, "TOPLEFT", column.x, 0)
        button:SetSize(column.width, COLUMN_HEADER_HEIGHT)
        local label = button.label
        label:SetJustifyH(column.align or "LEFT")
        label:SetTextColor(0.68, 0.68, 0.72, 1)
        local sortKey = ({item="item", rank="rank", source="source", acquisition="source", location="location", owned="owned",
            expansion="priority"})[column.key]
        if column.key == "value" then sortKey = mode == "planner" and "priority" or (mode == "enhance" and "recommendation" or nil) end
        button.sortable = sortKey ~= nil
        button.columnKey = sortKey
        button.sortIcon:SetShown(sortKey ~= nil and viewState.sort == sortKey)
        if sortKey and viewState.sort == sortKey then
            BigBiSList.Widgets:SetIcon(button.sortIcon, viewState.sortDirection == "asc" and "sortAscending" or "sortDescending")
        end
        label:SetText(column.label)
    end

    return header, COLUMN_HEADER_HEIGHT
end

function UI:GetDensityMetrics()
    local compact = accountDB() and accountDB().profile.window.density == "compact"
    return compact and 40 or 56, compact and 24 or 32, compact and 1 or 2
end

function UI:HandleEntityGesture(data, mode, buttonName, owner)
    if not data then return end
    local id = data.entity_id or data.spell_id or data.item_id
    local link = data.item_link
    if data.item_id and not link then local _, itemLink = UI:GetItemInfo(data.item_id); link = itemLink end
    if data.spell_id and GetSpellLink then link = GetSpellLink(data.spell_id) end
    if buttonName == "RightButton" then self:ShowItemActionMenu(data, mode, owner); return end
    if buttonName ~= "LeftButton" then return end
    if IsShiftKeyDown and IsShiftKeyDown() and link and ChatEdit_InsertLink then ChatEdit_InsertLink(link)
    elseif IsControlKeyDown and IsControlKeyDown() and data.item_id and link and DressUpItemLink then DressUpItemLink(link)
    elseif id then self:ShowInspectorFor(id, data, mode) end
end

function UI:ShowItemActionMenu(data, mode, owner)
    if not data or not UIDropDownMenu_Initialize or not ToggleDropDownMenu then return end
    self.itemActionMenu = self.itemActionMenu or CreateFrame("Frame", "BigBiSListItemActionMenu", UIParent, "UIDropDownMenuTemplate")
    local itemId = data.item_id
    local items = {}
    local function add(text, callback) items[#items+1] = { text = text, callback = callback } end
    add("Open item reference", function()
        local link
        if data.spell_id and GetSpellLink then link = GetSpellLink(data.spell_id)
        elseif itemId then link = data.item_link or ("item:" .. tostring(itemId)) end
        if link and SetItemRef then SetItemRef(link:match("|H([^|]+)|h") or link, link, "LeftButton") end
    end)
    if itemId then
        local comparison = self.slotComparison
        if comparison and (not comparison.statRank or data.reference_context) then
            local target = BigBiSList.isForever and data.reference_context or itemId
            add(BigBiSList.isForever and "Compare to this" or "Use as reference", function() self:SetComparisonReference(target) end)
        end
        if not self.slotComparison and self.OpenSlotComparison and data.slot and mode ~= "leveling" and mode ~= "enhance" then
            add("Compare slot", function() self:OpenSlotComparison(data, mode) end)
        end
        local char = BigBiSList:GetCharacterDB()
        local saved = char.wishlist[tostring(itemId)]
        add(saved and "Remove from Wishlist" or "Add to Wishlist", function()
            if saved then self:RemoveWishlist(itemId) else self:AddWishlist(itemId) end
        end)
        local hidden = char.ignoredItems[tostring(itemId)]
        add(hidden and "Restore item" or "Hide item", function()
            if hidden then self:UnignoreItem(itemId) else self:IgnoreItem(itemId) end
        end)
    end
    UIDropDownMenu_Initialize(self.itemActionMenu, function()
        for _, entry in ipairs(items) do
            local info = UIDropDownMenu_CreateInfo()
            info.text = entry.text; info.notCheckable = true
            info.func = function() entry.callback(); BigBiSList.Widgets:CloseDropdownMenus() end
            UIDropDownMenu_AddButton(info)
        end
    end, "MENU")
    ToggleDropDownMenu(1, nil, self.itemActionMenu, owner or "cursor", 0, 0)
end

function UI:CreateDataRow(parent, yOffset, data, mode, row, fixedHeight)
    local widgets = BigBiSList.Widgets
    local densityHeight, iconSize, maxLines = self:GetDensityMetrics()
    local rowHeight = fixedHeight or densityHeight
    local entityType = data.entity_type or (data.spell_id and "spell") or "item"
    local entityId = data.entity_id or data.spell_id or data.item_id
    local width = self:GetTableViewportWidth(parent, self.contentScroll and self.contentScroll:GetWidth() or 760)
    local layout = self:GetTableColumnLayout(width, mode)
    if not row then
        row = widgets:CreateItemRow(parent, rowHeight)
        row.cells = {}; row.cellHovers = {}
        row.iconButton = widgets:CreateIconButton(row, iconSize)
        row.nameText = widgets:CreateWrappedLabel(row, "", "GameFontNormal")
        row.subText = widgets:CreateLabel(row, "", "GameFontNormalSmall")
        row.subText:SetTextColor(0.62, 0.62, 0.67)
        row.actionButton = widgets:CreateUtilityButton(row, "starOutline", 28, function(button)
            local bound = button.boundRow
            if bound and bound.boundData.item_id then
                local id = bound.boundData.item_id
                if BigBiSList:GetCharacterDB().wishlist[tostring(id)] then UI:RemoveWishlist(id) else UI:AddWishlist(id) end
            end
        end, function(button, tooltip)
            local bound = button.boundRow
            local saved = bound and bound.boundData.item_id and BigBiSList:GetCharacterDB().wishlist[tostring(bound.boundData.item_id)]
            tooltip:AddLine(saved and "Remove from Wishlist" or "Add to Wishlist")
        end)
        row.actionButton.boundRow = row
        row.iconButton:HookScript("OnEnter", function() row:SetHovered(true) end)
        row.iconButton:HookScript("OnLeave", function() row:SetHovered(false) end)
        row.actionButton:HookScript("OnEnter", function() row:SetHovered(true) end)
        row.actionButton:HookScript("OnLeave", function() row:SetHovered(false) end)
        row.statusIcon = row:CreateTexture(nil, "ARTWORK")
        row.statusIcon:SetSize(12,12)
        row:SetScript("OnMouseUp", function(bound, button) UI:HandleEntityGesture(bound.boundData, bound.boundMode, button, bound) end)
        row.__bigBisManaged = true
        self:CountPerformance("widgetsCreated", 5)
    end
    row:SetParent(parent); row:Show(); row:ClearAllPoints()
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    row:SetHeight(rowHeight)
    row.bindToken = (row.bindToken or 0) + 1
    row.boundData = data; row.boundMode = mode; row.boundEntityId = entityId
    row.itemId = data.item_id; row.entityType = entityType; row.entityId = entityId
    row.detailData = data; row.detailMode = mode; row.columnLayout = layout
    row:SetHovered(false)
    row:SetSelected(self.selectedRowKey ~= nil and self.selectedRowKey == self:GetRowKey(data, mode))
    for _, cell in pairs(row.cells) do cell:Hide() end
    for _, hover in pairs(row.cellHovers) do hover:Hide() end
    row.actionButton:Hide()
    row.statusIcon:Hide()
    local icon = row.iconButton
    icon:SetSize(iconSize, iconSize); icon:ClearAllPoints()
    icon:SetPoint("LEFT", row, "LEFT", layout.item.x, 0)
    local name = row.nameText
    name:ClearAllPoints()
    local nameWidth = math.max(60, layout.item.width - iconSize - 8)
    row.subText:ClearAllPoints()
    row.subText:SetPoint("TOPLEFT", name, "BOTTOMLEFT", 0, -2)
    row.subText:SetWidth(nameWidth)
    local slot = (mode == "phase" and (self:GetViewState().groupBy or "slot") == "slot") and "" or self:GetRowSlotDisplay(data)
    if mode == "leveling" and data.guide_note then slot = slot .. " · " .. data.guide_note end
    -- The secondary slot line has a reserved budget; item names never overlap it.
    local nameLines = slot ~= "" and 1 or maxLines
    local identityHeight = nameLines * 14 + (slot ~= "" and 14 or 0)
    name:SetPoint("TOPLEFT", row, "LEFT", layout.item.x + iconSize + 8, identityHeight / 2)
    name:SetWidth(nameWidth); name.maxLines = nameLines; name.lineHeight = 14
    if not entityId then
        self:ResetEntityButton(icon, name, data.disabledReason or data.name or "Empty")
    elseif entityType == "spell" then
        self:SetSpellButton(icon, data.spell_id or entityId, name, data.name, data, mode)
    else
        self:SetItemButton(icon, data.item_id, name, data.name, data.quality or (data.item and data.item.quality), data, mode)
    end
    widgets:SetCellText(name, name.fullText or data.name or "", nameLines, 14, nameWidth)
    widgets:SetCellText(row.subText, slot, 1, 12, nameWidth)
    row.subText:SetShown(slot ~= "")
    local source, location = self:GetRowAcquisitionDisplay(data)
    local function bindCell(key, text, color)
        local column = layout[key]
        if not column then return end
        local label = row.cells[key] or widgets:CreateWrappedLabel(row, "", "GameFontNormalSmall")
        row.cells[key] = label; label:Show(); label:ClearAllPoints()
        label:SetPoint("LEFT", row, "LEFT", column.x, 0)
        label:SetJustifyH(column.align or "LEFT")
        label:SetTextColor(unpack(color or {0.78, 0.79, 0.82}))
        widgets:SetCellText(label, text or "", maxLines, 13, column.width)
        local hover = row.cellHovers[key]
        if not hover then
            hover = CreateFrame("Frame", nil, row); hover:EnableMouse(true)
            hover:SetScript("OnMouseUp", function(_, button) UI:HandleEntityGesture(row.boundData, row.boundMode, button, row) end)
            hover:SetScript("OnEnter", function() row:SetHovered(true) end)
            hover:SetScript("OnLeave", function() row:SetHovered(false) end)
            widgets:BindTooltip(hover, function(frame, tooltip)
                if frame.cellKey == "source" or frame.cellKey == "location" or frame.cellKey == "acquisition" then
                    tooltip:AddLine(frame.label.fullText or "", 0.88, 0.88, 0.90, true)
                    UI:AddSelectedRouteTooltipLines(tooltip, row.boundData, UI:GetAccessEvaluation(row.boundData))
                elseif frame.cellKey == "rank" then
                    tooltip:AddLine(frame.label.fullText or "", 0.88,0.88,0.90,true)
                    tooltip:AddLine("Guide ratings describe their named tier and setup. Compare slot shows the supporting evidence.", 0.66,0.68,0.72,true)
                elseif frame.cellKey == "stat_rank" and row.boundData.stat_rank then
                    for _, line in ipairs(BigBiSList.ForeverGearRating:DescriptionLines(row.boundData.stat_rank)) do
                        tooltip:AddLine(line, 0.88, 0.88, 0.92, true)
                    end
                    if row.boundData.guide_note then tooltip:AddLine(row.boundData.guide_note, 0.88, 0.88, 0.92, true) end
                elseif frame.cellKey == "owned" then
                    tooltip:AddLine(frame.label.fullText or "", 0.88,0.88,0.90,true)
                    tooltip:AddLine(UI:GetBankStatusText(), 0.66,0.68,0.72,true)
                    for _, line in ipairs(row.boundData.ownership_lines or {}) do tooltip:AddLine(line, 0.82,0.84,0.88,true) end
                else
                    tooltip:AddLine(frame.label.fullText or "", 0.88, 0.88, 0.9, true)
                end
            end)
            row.cellHovers[key] = hover
        end
        hover.label = label; hover.cellKey = key
        hover:ClearAllPoints(); hover:SetPoint("TOPLEFT", row, "TOPLEFT", column.x, 0)
        hover:SetSize(column.width, rowHeight); hover:Show()
    end
    bindCell("rank", self:GetRowRecommendationText(data, mode))
    bindCell("value", self:GetRowRecommendationText(data, mode))
    if layout.stat_rank then
        local placement = data.stat_rank
        local tier = placement and placement.tier
        local text = placement and BigBiSList.ForeverGearRating:Label(placement, "compact")
        text = text or self:GetRowRecommendationText(data, mode)
        bindCell("stat_rank", data.guide_bis and ("BiS · " .. text) or text,
            data.guide_bis and {1, 0.82, 0.35} or tier and { widgets:GetRankColor(tier.quality) })
    end
    bindCell("expansion", self:GetWishlistExpansionText(data))
    bindCell("source", source, {0.70,0.77,0.84})
    bindCell("location", location, {0.65,0.67,0.72})
    bindCell("acquisition", source .. (location ~= "" and ((maxLines == 1 and " · " or "\n") .. location) or ""), {0.70,0.77,0.84})
    local state = self:GetRowOwnershipState(data)
    local statusLabel = data.ownership_label or ownershipStateLabel(state)
    bindCell("owned", statusLabel, state == "missing" and {0.58,0.60,0.64} or {0.66,0.79,0.70})
    if layout.owned then
        widgets:SetIcon(row.statusIcon, ({equipped="equipped", bag="bag", bank="bank", applied="check", service="info"})[state] or "minus")
        row.statusIcon:ClearAllPoints()
        row.statusIcon:SetPoint("LEFT", row, "LEFT", layout.owned.x, 0)
        row.statusIcon:SetVertexColor(0.64,0.70,0.68); row.statusIcon:Show()
        local label = row.cells.owned
        label:ClearAllPoints(); label:SetPoint("LEFT", row, "LEFT", layout.owned.x+17, 0)
        widgets:SetCellText(label, statusLabel, maxLines, 13, layout.owned.width-17)
    end
    if data.item_id and layout.action then
        row.actionButton:ClearAllPoints(); row.actionButton:SetPoint("LEFT", row, "LEFT", layout.action.x, 0)
        local saved = BigBiSList:GetCharacterDB().wishlist[tostring(data.item_id)] == true
        row.boundWishlistSaved = saved
        row.actionButton:SetIcon(saved and "starFilled" or "starOutline")
        row.actionButton:SetSelected(saved); row.actionButton:Show()
    end
    return row, rowHeight
end

function UI:CreateVirtualSectionHeader(parent, yOffset, text, header, entry)
    local widgets = BigBiSList.Widgets
    if not header then
        header = CreateFrame("Button", nil, parent)
        header:SetHeight(28)
        header.chevron = header:CreateTexture(nil, "ARTWORK")
        header.chevron:SetSize(12, 12); header.chevron:SetPoint("LEFT", header, "LEFT", 8, 0)
        header.label = widgets:CreateLabel(header, "", "GameFontNormalSmall")
        header.label:SetPoint("LEFT", header, "LEFT", 28, 0)
        header.label:SetPoint("RIGHT", header, "RIGHT", -8, 0)
        header:SetScript("OnClick", function(button)
            if not UI:IsCurrentRenderFrame(button) then return end
            local state = UI:GetViewState()
            state.collapsedGroups = state.collapsedGroups or {}
            state.collapsedGroups[button.sectionKey] = not button.__bigBisBoundRenderEntry.collapsed
            UI:Invalidate("presentation", "section-toggle"); UI:ScheduleRefresh(nil, "section-toggle")
        end)
        header.compareButton = widgets:CreateTextButton(header, "Compare slot", 98, 28, function(button)
            local owner = button:GetParent()
            if UI:IsCurrentRenderFrame(owner) and owner.compareSlot and UI.OpenSlotComparison then
                UI:OpenSlotComparison({ slot = owner.compareSlot }, "phase")
            end
        end)
        header.compareButton:SetPoint("RIGHT", header, "RIGHT", -4, 0)
        header.__bigBisManaged = true
        self:CountPerformance("widgetsCreated")
    end
    header:SetParent(parent); header:Show(); header:ClearAllPoints()
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    header.sectionKey = entry and entry.sectionKey or text
    header.compareSlot = entry and entry.compareSlot
    header.compareButton:SetShown(header.compareSlot ~= nil and self.OpenSlotComparison ~= nil)
    header.label:ClearAllPoints()
    header.label:SetPoint("LEFT", header, "LEFT", 28, 0)
    header.label:SetPoint("RIGHT", header, "RIGHT", header.compareSlot and -110 or -8, 0)
    header.__bigBisListRenderKind = "section"
    header.label:SetText(text .. "  (" .. tostring(entry and entry.count or 0) .. ")")
    widgets:SetIcon(header.chevron, entry and entry.collapsed and "chevronRight" or "chevronDown")
    return header, 28
end

function UI:GetRenderPool(kind)
    self.renderPools = self.renderPools or {}
    self.renderPools[kind] = self.renderPools[kind] or {}
    return self.renderPools[kind]
end

function UI:RunRenderTransaction(callback, deferUpdate)
    self.renderTransactionDepth = (self.renderTransactionDepth or 0) + 1
    local ok, result = xpcall(callback, function(message) return tostring(message) end)
    self.renderTransactionDepth = self.renderTransactionDepth - 1
    if not ok then
        self.virtualListUpdatePending = nil
        self.virtualListForcePending = nil
        error(result, 0)
    end
    if not deferUpdate and self.renderTransactionDepth == 0 and self.virtualListUpdatePending then
        -- Native scroll callbacks can run while a frame is being hidden or anchored.
        -- Drain once against the completed model, never against partially bound rows.
        local force = self.virtualListForcePending
        self.virtualListUpdatePending = nil
        self.virtualListForcePending = nil
        self:UpdateVirtualList(force)
    end
    return result
end

function UI:PoolRenderFrame(kind, frame)
    self.renderPoolMembership = self.renderPoolMembership or {}
    if self.renderPoolMembership[frame] then return end
    frame.__bigBisBoundRenderModel = nil
    frame.__bigBisBoundRenderEntry = nil
    frame.__bigBisBoundRenderSerial = nil
    frame.__bigBisListRenderKind = kind
    self.renderPoolMembership[frame] = kind
    table.insert(self:GetRenderPool(kind), frame)
end

function UI:AcquireRenderFrame(kind)
    local pool = self:GetRenderPool(kind)
    local frame = table.remove(pool)
    while frame and self.renderActiveMembership and self.renderActiveMembership[frame] do
        frame = table.remove(pool)
    end
    if frame and self.renderPoolMembership then self.renderPoolMembership[frame] = nil end
    return frame
end

function UI:TrackRenderFrame(kind, frame)
    if not frame then
        return
    end
    self.activeRenderFrames = self.activeRenderFrames or {}
    self.renderActiveMembership = self.renderActiveMembership or {}
    if self.renderActiveMembership[frame] then return end
    self.renderActiveMembership[frame] = true
    frame.__bigBisListRenderKind = kind
    frame.__bigBisBoundRenderModel = nil
    frame.__bigBisBoundRenderEntry = nil
    frame.__bigBisBoundRenderSerial = nil
    table.insert(self.activeRenderFrames, frame)
end

function UI:IsCurrentRenderFrame(frame)
    local model = self.renderModel
    return model and self.renderActiveMembership and self.renderActiveMembership[frame]
        and frame.__bigBisBoundRenderModel == model
        and frame.__bigBisBoundRenderSerial == self.renderModelSerial
        and (not model.contextKey or model.contextKey == self:GetNavigationContextKey())
end

function UI:ReleaseRenderFrames()
    self:RunRenderTransaction(function()
        local releasing = self.activeRenderFrames or {}
        self.activeRenderFrames = {}
        self.renderActiveMembership = {}
        self.renderRangeKey = nil
        for _, frame in ipairs(releasing) do
            frame.__bigBisBoundRenderModel = nil
            frame.__bigBisBoundRenderEntry = nil
            frame.__bigBisBoundRenderSerial = nil
            frame:Hide()
            frame:ClearAllPoints()
            self:PoolRenderFrame(frame.__bigBisListRenderKind or "row", frame)
        end
    end, true)
end

selectedFacetKeys = function(values, labels)
    local result = {}
    for value, selected in pairs(values or {}) do
        if selected then
            table.insert(result, value)
        end
    end
    table.sort(result, function(a, b)
        local aLabel = labels and labels[a] or a
        local bLabel = labels and labels[b] or b
        if aLabel ~= bLabel then
            return aLabel < bLabel
        end
        return tostring(a) < tostring(b)
    end)
    return result
end

local function estimatedChipWidth(label)
    return clamp((string.len(tostring(label or "")) * 6) + 24, 72, 178)
end

function UI:AddFacetChips(chips, tableKey, scalarKey, prefix, labels, strictLabels)
    for _, value in ipairs(selectedFacetKeys(self:GetFilters()[tableKey], labels)) do
        if strictLabels and not labels[value] then
            -- Skip rank selections that are not meaningful in this mode.
        else
            local label = labels[value] or value
            table.insert(chips, {
                label = prefix .. ": " .. label,
                clear = function()
                    self:ClearFacetValue(tableKey, value, scalarKey)
                end,
            })
        end
    end
end

function UI:GetSlotFilterLabels()
    local labels = {}
    for _, slotFilter in ipairs(BigBiSList:GetDisplaySlotFilters()) do
        labels[slotFilter.key] = slotFilter.label
    end
    return labels
end

function UI:GetActiveFilterChips()
    local filters = self:GetFilters()
    local chips = {}

    if filters.search and filters.search ~= "" then
        table.insert(chips, {
            label = "Search: " .. filters.search,
            clear = function()
                self:SetFilter("search", "")
                if self.searchBox then
                    self.searchBox:SetText("")
                    self.searchBox:ClearFocus()
                end
            end,
        })
    end

    local tabName = normalizeTabName((self:GetSelection() or {}).tab)
    local supportsItems = tabName == "Upgrades" or tabName == "By Slot" or tabName == "Wishlist"
    local supportsOwned = supportsItems or tabName == "Gear Guide"
    local supportsAcquisition = self:ViewSupportsFilters(tabName)

    if supportsOwned and filters.ownedState and filters.ownedState ~= "all" then
        table.insert(chips, { label = "Owned: " .. ownedFilterLabel(filters.ownedState), clear = function() self:SetFilter("ownedState", "all") end })
    end
    if tabName == "Upgrades" and filters.upgradeMode and filters.upgradeMode ~= "actual" and filters.upgradeMode ~= "candidates" then
        table.insert(chips, { label = "Targets: " .. upgradeModeLabel(filters.upgradeMode), clear = function() self:SetFilter("upgradeMode", "candidates") end })
    end
    if (tabName == "Upgrades" or tabName == "By Slot") and filters.includeEarlier ~= (tabName == "Upgrades") then
        table.insert(chips, { label = filters.includeEarlier and "Include earlier recommendations" or "Selected tier recommendations", clear = function() self:SetFilter("includeEarlier", tabName == "Upgrades") end })
    end
    if (supportsItems or tabName == "Gear Guide") and filters.boe and filters.boe ~= "all" then
        table.insert(chips, { label = "BoE: " .. boeFilterLabel(filters.boe), clear = function() self:SetFilter("boe", "all") end })
    end
    if tabName == "Upgrades" and filters.longevity and filters.longevity ~= "all" then
        table.insert(chips, { label = "Usefulness: " .. longevityFilterLabel(filters.longevity), clear = function() self:SetFilter("longevity", "all") end })
    end
    if (supportsItems or tabName == "Gear Guide") and filters.binding and filters.binding ~= "all" then
        table.insert(chips, { label = "Binding: " .. tostring(filters.binding), clear = function() self:SetFilter("binding", "all") end })
    end

    if supportsItems then
        self:AddFacetChips(chips, "rankGroups", "rankGroup", "Rank", RANK_FILTER_LABELS)
        self:AddFacetChips(chips, "slots", nil, "Slot", self:GetSlotFilterLabels())
    elseif tabName == "Gear Guide" then
        local category = self:GetViewState("Gear Guide").recommendationCategory or "all"
        if category ~= "all" then
            table.insert(chips, {
                label = "Category: " .. (LEVELING_RANK_FILTER_LABELS[category] or category),
                clear = function() self:SetViewStateValue("Gear Guide", "recommendationCategory", "all") end,
            })
        end
        self:AddFacetChips(chips, "slots", nil, "Slot", self:GetSlotFilterLabels())
    elseif tabName == "Enhance" then
        local state = self:GetViewState("Enhance")
        if state.type and state.type ~= "all" then
            table.insert(chips, { label = "Type: " .. tostring(state.type), clear = function() self:SetViewStateValue("Enhance", "type", "all") end })
        end
        if state.appliedState and state.appliedState ~= "all" then
            table.insert(chips, { label = "Applied: " .. tostring(state.appliedState), clear = function() self:SetViewStateValue("Enhance", "appliedState", "all") end })
        end
    end
    if tabName == "Wishlist" then
        local relevance = self:GetViewState("Wishlist").relevance or "all"
        if relevance ~= "all" then
            table.insert(chips, { label = "Relevance: " .. tostring(relevance), clear = function() self:SetViewStateValue("Wishlist", "relevance", "all") end })
        end
    end
    if supportsAcquisition then
        self:AddFacetChips(chips, "sourceTypes", "sourceType", "Source", BigBiSList:GetSourceTypeLabels())
        if tableHasAnyEnabled(filters.costs) then
            self:AddFacetChips(chips, "costs", "cost", "Cost", self:GetRememberedCostLabels(filters.costs))
        end
        if tableHasAnyEnabled(filters.vendors) then
            self:AddFacetChips(chips, "vendors", "vendor", "Vendor", self:GetRememberedVendorLabels(filters.vendors))
        end
        self:AddFacetChips(chips, "zones", "zone", "Zone", {})
        self:AddFacetChips(chips, "reputations", "reputation", "Reputation", {})
    end

    return chips
end

function UI:GetActiveFilterChipLayout(parent, chips)
    local layout = { height = 0, rows = 0, positions = {}, hidden = 0 }
    if #(chips or {}) == 0 then return layout end
    local width = contentWidth(parent, self.contentScroll and self.contentScroll:GetWidth() or 560)
    local x, limit = 4, math.max(80, width - 190)
    for index, chip in ipairs(chips) do
        local chipWidth = estimatedChipWidth(chip.label) + 28
        if x + chipWidth <= limit then
            layout.positions[index] = { x = x, y = 0, width = chipWidth, row = 1 }
            x = x + chipWidth + 6
        else layout.hidden = layout.hidden + 1 end
    end
    layout.rows = 1; layout.height = 28; layout.overflowX = x
    return layout
end

function UI:ActiveFilterBarHeight(chips)
    return self:GetActiveFilterChipLayout(self.contentRegion or self.contentChild, chips).height
end

function UI:NewListRenderModel()
    return {
        entries = {},
        cursor = 2,
        rowCount = 0,
    }
end

function UI:AddListRenderEntry(model, entry)
    entry.top = model.cursor
    entry.height = entry.height or 1
    entry.bottom = entry.top + entry.height
    table.insert(model.entries, entry)
    model.cursor = entry.bottom
end

function UI:AddListSection(model, title, mode, defaultCollapsed, savedTitle)
    model.columnMode = model.columnMode or mode
    local key = (mode or "list") .. ":" .. (savedTitle or title)
    local collapsed = (self:GetViewState().collapsedGroups or {})[key]
    if collapsed == nil then collapsed = defaultCollapsed end
    local entry = { kind = "section", title = title, sectionKey = key, count = 0, height = 28,
        collapsed = collapsed == true, defaultCollapsed = defaultCollapsed }
    model.activeSection = entry
    self:AddListRenderEntry(model, entry)
    return entry
end

function UI:AddListRow(model, data, mode)
    local rowHeight = self:GetDensityMetrics()
    model.rowCount = (model.rowCount or 0) + 1
    if model.activeSection then
        model.activeSection.count = model.activeSection.count + 1
        if model.activeSection.collapsed then return end
    end
    model.columnMode = model.columnMode or mode
    self:AddListRenderEntry(model, {
        kind = "row", data = data, mode = mode, height = rowHeight,
        rowHeight = rowHeight, sectionKey = model.activeSection and model.activeSection.sectionKey,
    })
end

function UI:AddGuideEquippedRows(model, slot)
    if self:GetFocusedBrowseSlot() or not self.currentOwned then return end
    local selection = self:GetSelection()
    local equipped = BigBiSList:GetEquipmentComparisonContexts(selection.class, selection.spec,
        self:GetEffectivePhaseKey(), self.currentOwned, slot)
    for _, data in ipairs(equipped) do
        if data.item_id then
            self:AddListRenderEntry(model, { kind = "action", title = "Equipped · " .. data.name,
                detail = data.slot, height = 28,
                activate = function() self:OpenSlotComparison(data, "gear", true) end })
        end
    end
end

function UI:AddGearGuideRows(model, rows, scope)
    local parent = model.activeSection
    local filters = self.currentFilterPayload or self:GetFilters()
    local alternates = {}
    for _, row in ipairs(rows) do
        if row.guide_alternate then alternates[#alternates + 1] = row end
    end
    if #alternates == 0 or #alternates == #rows or (filters.search or "") ~= "" or (parent and parent.collapsed) then
        for _, row in ipairs(rows) do self:AddListRow(model, row, "leveling") end
        return
    end
    for _, row in ipairs(rows) do
        if not row.guide_alternate then self:AddListRow(model, row, "leveling") end
    end
    if parent then parent.count = parent.count + #alternates end
    self:AddListSection(model, "More options", "leveling", true, "more:" .. scope)
    for _, row in ipairs(alternates) do self:AddListRow(model, row, "leveling") end
    model.activeSection = parent
end

function UI:RenderGroupedRows(rows, mode, groupBy, defaultTitle, notes)
    local model = self:NewListRenderModel()
    local guide = BigBiSList.isForever and mode == "leveling"
    if guide then self:AddWithinReach(model, rows, "guide") end
    for _, text in ipairs(notes or {}) do
        local width = math.max(200, ((self.contentChild and self.contentChild:GetWidth()) or 640) - 24)
        local height = 12 + 14 * math.ceil(#text / math.max(1, math.floor(width / 7)))
        self:AddListRenderEntry(model, { kind = "note", text = text, height = math.max(28, height) })
    end
    if groupBy == "none" then
        local sorted = self:SortDisplayRows(rows, mode)
        if guide then self:AddGearGuideRows(model, sorted, "all")
        else for _, row in ipairs(sorted) do self:AddListRow(model, row, mode) end end
    else
        local groups, order = {}, {}
        for _, row in ipairs(rows) do
            local title = defaultTitle
            if groupBy == "activity" or groupBy == "source" then
                title = BigBiSList:GetActivityGroup(row)
            elseif groupBy == "slot" then title = self:GetRowSlotDisplay(row)
            elseif groupBy == "priority" then
                for _, tier in ipairs(PLANNER_TIER_SECTIONS) do
                    if tier.key == (row.recommendation_tier or "only_if_easy") then title = tier.title; break end
                end
            end
            title = title or defaultTitle or "Items"
            if not groups[title] then groups[title] = {}; order[#order+1] = title end
            groups[title][#groups[title]+1] = row
        end
        if groupBy == "activity" or groupBy == "source" then table.sort(order) end
        for _, title in ipairs(order) do
            local displayed = groupBy == "priority" and BigBiSList.isForever and FOREVER_PLANNER_SECTION_TITLES[title] or title
            self:AddListSection(model, displayed, mode, nil, title)
            if groupBy == "slot" and mode ~= "leveling" then
                model.activeSection.compareSlot = groups[title][1] and groups[title][1].slot
            end
            if BigBiSList.isForever and groupBy == "slot" and not model.activeSection.collapsed
                and (mode == "leveling" or mode == "phase") then
                self:AddGuideEquippedRows(model, groups[title][1].slot)
            end
            local sorted = self:SortDisplayRows(groups[title], mode)
            if guide then self:AddGearGuideRows(model, sorted, "slot:" .. title)
            else for _, row in ipairs(sorted) do self:AddListRow(model, row, mode) end end
            self:AddListGap(model)
        end
    end
    self:RenderListModel(model)
end

function UI:AddListGap(model, height)
    self:AddListRenderEntry(model, {
        kind = "gap",
        height = height or LIST_SECTION_GAP,
    })
end

function UI:CreateActiveFilterBar(parent, yOffset, chips, height, frame)
    local widgets = BigBiSList.Widgets
    if not frame then
        frame = CreateFrame("Frame", nil, parent); frame.chipButtons = {}
        frame.clearButton = widgets:CreateTextButton(frame, "Clear all", 76, 28, function() UI:ClearFilters() end)
        frame.clearButton:SetPoint("RIGHT", frame, "RIGHT", -4, 0)
        frame.overflow = widgets:CreateTextButton(frame, "", 104, 28, function() UI:SetFilterDrawerOpen(true) end)
        widgets:BindTooltip(frame.overflow, function(_, tooltip)
            for _, chip in ipairs(UI:GetActiveFilterChips()) do tooltip:AddLine(chip.label, 0.86, 0.86, 0.90, true) end
        end)
        frame.__bigBisManaged = true
    end
    frame:SetParent(parent); frame:Show(); frame:SetHeight(28)
    if yOffset then
        frame:ClearAllPoints(); frame:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset); frame:SetPoint("RIGHT", parent, "RIGHT", 0, 0)
    end
    local layout = self:GetActiveFilterChipLayout(parent, chips)
    for _, chipFrame in ipairs(frame.chipButtons) do chipFrame:Hide() end
    for index, chip in ipairs(chips) do
        local position = layout.positions[index]
        if position then
            local chipFrame = frame.chipButtons[index]
            if not chipFrame then
                chipFrame = widgets:CreatePanel(nil, frame)
                chipFrame.label = widgets:CreateLabel(chipFrame, "")
                chipFrame.label:SetPoint("LEFT", chipFrame, "LEFT", 6, 0)
                chipFrame.clear = widgets:CreateUtilityButton(chipFrame, "clear", 28, function(button)
                    if button.chip and button.chip.clear then button.chip.clear() end
                end, "Remove filter")
                chipFrame.clear:SetPoint("RIGHT", chipFrame, "RIGHT", 0, 0)
                frame.chipButtons[index] = chipFrame
            end
            chipFrame:Show(); chipFrame:ClearAllPoints()
            chipFrame:SetPoint("TOPLEFT", frame, "TOPLEFT", position.x, 0); chipFrame:SetSize(position.width, 28)
            widgets:SetCellText(chipFrame.label, chip.label, 1, 13, position.width - 38)
            chipFrame.clear.chip = chip
        end
    end
    frame.overflow:ClearAllPoints(); frame.overflow:SetPoint("LEFT", frame, "LEFT", layout.overflowX or 4, 0)
    frame.overflow.label:SetText("+" .. layout.hidden .. " filters"); frame.overflow:SetShown(layout.hidden > 0)
    return frame
end

function UI:RefreshFixedActiveFilterBar()
    if not self.contentRegion or not self:ViewSupportsFilters() then
        if self.fixedActiveFilterBar then
            self.fixedActiveFilterBar:Hide()
        end
        self.fixedActiveFilterHeight = 0
        return 0
    end

    local chips = self:GetActiveFilterChips()
    local height = self:ActiveFilterBarHeight(chips)
    if height <= 0 then
        if self.fixedActiveFilterBar then
            self.fixedActiveFilterBar:Hide()
        end
        self.fixedActiveFilterHeight = 0
        return 0
    end

    self.fixedActiveFilterBar = self:CreateActiveFilterBar(
        self.contentRegion,
        nil,
        chips,
        height,
        self.fixedActiveFilterBar
    )
    if self.fixedActiveFilterBar.SetFrameLevel then
        local parentLevel = self.contentRegion.GetFrameLevel and self.contentRegion:GetFrameLevel() or 0
        self.fixedActiveFilterBar:SetFrameLevel(parentLevel + 3)
    end
    self.fixedActiveFilterHeight = height
    return height
end

function UI:RebindSelectedRowFromModel(model)
    if not self.selectedRowKey and self.selectedItemData then
        self.selectedRowKey = self:GetRowKey(self.selectedItemData, self.selectedItemMode)
    end
    if not self.selectedRowKey then
        if self.selectedItemId then self:ClearSelectedRow() end
        return
    end
    for _, entry in ipairs((model and model.entries) or {}) do
        local data = entry.kind == "row" and entry.data or nil
        if data and self:GetRowKey(data, entry.mode) == self.selectedRowKey then
            self.selectedItemId = data.entity_id or data.spell_id or data.item_id
            self.selectedItemData = data
            self.selectedItemMode = entry.mode
            self.selectedEntityType = data.entity_type or (data.spell_id and "spell") or "item"
            return
        end
    end
    self:ClearSelectedRow()
end

function UI:RenderListModel(model)
    self:RunRenderTransaction(function()
        for _, button in ipairs(self.emptyActions or {}) do button:Hide() end
        local contextKey = self:GetNavigationContextKey()
        local pending = self.pendingNavigation
        local navigation
        if pending then
            navigation = pending.restore and self.navigationStates and self.navigationStates[contextKey] or { scroll = 0 }
            if pending.restore then
                self:ClearSelectedRow()
                self.selectedRowKey = navigation and navigation.selectedRowKey
            end
        elseif not self.renderedContextKey or self.renderedContextKey == contextKey then
            navigation = self:CaptureNavigationState()
        else
            navigation = { scroll = 0 }
            self:ClearSelectedRow()
        end
        self.pendingNavigation = nil
        self.renderedContextKey = contextKey
        self:ReleaseRenderFrames()
        self.renderModel = model
        model.contextKey = contextKey
        self.hasRenderedContent = true
        self:RebindSelectedRowFromModel(model)
        self.renderModelSerial = (self.renderModelSerial or 0) + 1
        if self.contentStaticLayer then self.contentStaticLayer:Hide() end
        if self.emptyLabel then self.emptyLabel:Hide() end
        if self.contentListLayer then self.contentListLayer:Show() end
        if self.resultCountText then
            local count = model.rowCount or 0
            self.resultCountText:SetText(model.resultText or (tostring(count) .. (count == 1 and " result" or " results")))
        end
        self:CountPerformance("modelRows", model.rowCount or 0)
        self:SetContentHeight(-(model.cursor + 30))
        self:SetStickyHeaderMode(model.columnMode)
        self:ApplyNavigationState(model, navigation)
        if pending and pending.restore and self.selectedRowKey and self.detailsScroll and self.detailsScroll.SetVerticalScroll then
            self.detailsScroll:SetVerticalScroll(navigation and navigation.detailsScroll or 0)
        end
        self:UpdateVirtualList(true)
    end)
end

function UI:UpdateVirtualList(force)
    if (self.renderTransactionDepth or 0) > 0 then
        self.virtualListUpdatePending = true
        self.virtualListForcePending = self.virtualListForcePending or force
        return
    end
    force = force or self.virtualListForcePending
    self.virtualListUpdatePending = nil
    self.virtualListForcePending = nil
    local model = self.renderModel
    local scroll = self.contentScroll
    local child = self.contentListLayer or self.contentChild
    if not model or not scroll or not child then
        return
    end

    local scrollTop = scroll:GetVerticalScroll() or 0
    local viewportHeight = math.max(1, scroll:GetHeight() or 1)
    local minTop = math.max(0, scrollTop - LIST_OVERSCAN_PIXELS)
    local maxBottom = scrollTop + viewportHeight + LIST_OVERSCAN_PIXELS
    local width = self:GetTableViewportWidth(child, scroll:GetWidth() or 760)
    local columnLayout = self:GetTableColumnLayout(width, self.stickyHeaderMode or "phase")
    local compact = columnLayout.compact
    local rangeKey = table.concat({
        tostring(self.renderModelSerial or 0),
        tostring(math.floor(minTop / 20)),
        tostring(math.floor(maxBottom / 20)),
        columnLayout.signature,
    }, ":")
    if not force and self.renderRangeKey == rangeKey then
        return
    end

    self:RunRenderTransaction(function()
        self:ReleaseRenderFrames()
        self.renderRangeKey = rangeKey
        local realized = 0
        local childrenBefore = {}
        if child.GetChildren then
            for _, existingChild in ipairs({ child:GetChildren() }) do
                childrenBefore[existingChild] = true
            end
        end
        local bindingPoolKind
        local ok, bindError = xpcall(function()
            for _, entry in ipairs(model.entries or {}) do
                if entry.top > maxBottom then
                    break
                end
                if entry.kind ~= "gap" and entry.bottom >= minTop and entry.top <= maxBottom then
                    local poolKind = entry.nextAction and "planner-action" or entry.kind
                    if entry.kind == "row" and not entry.nextAction then
                        poolKind = entry.kind .. ":" .. tostring(entry.mode or "phase") .. ":" .. (compact and "compact" or "wide")
                    end
                    bindingPoolKind = poolKind
                    local frame = self:AcquireRenderFrame(poolKind)
                    local alreadyTracked = frame ~= nil
                    if alreadyTracked then
                        self:TrackRenderFrame(poolKind, frame)
                    end
                    if entry.nextAction then
                        frame = self:CreateNextUpgradeCard(child, -entry.top, entry.nextAction, frame, entry.rowHeight)
                    elseif entry.kind == "row" then
                        frame = self:CreateDataRow(child, -entry.top, entry.data, entry.mode, frame, entry.rowHeight)
                    elseif entry.kind == "section" then
                        frame = self:CreateVirtualSectionHeader(child, -entry.top, entry.title, frame, entry)
                    elseif entry.kind == "note" then
                        frame = self:CreateVirtualNote(child, -entry.top, entry.text, frame, entry.height)
                    elseif entry.kind == "action" then
                        frame = self:CreateVirtualListAction(child, -entry.top, entry, frame)
                    end
                    if frame then
                        if not alreadyTracked then
                            self:TrackRenderFrame(poolKind, frame)
                        end
                        frame.__bigBisBoundRenderModel = model
                        frame.__bigBisBoundRenderEntry = entry
                        frame.__bigBisBoundRenderSerial = self.renderModelSerial
                        realized = realized + 1
                    end
                    bindingPoolKind = nil
                end
            end
        end, function(message)
            return tostring(message)
        end)
        if not ok then
            self.renderRangeKey = nil
            local active = {}
            for _, frame in ipairs(self.activeRenderFrames or {}) do
                active[frame] = true
            end
            if child.GetChildren then
                for _, newChild in ipairs({ child:GetChildren() }) do
                    if not childrenBefore[newChild] and not active[newChild] then
                        if newChild.Hide then newChild:Hide() end
                        if newChild.ClearAllPoints then newChild:ClearAllPoints() end
                        if newChild.__bigBisManaged then
                            self:PoolRenderFrame(bindingPoolKind or newChild.__bigBisListRenderKind or "row", newChild)
                        end
                    end
                end
            end
            self:ReleaseRenderFrames()
            error(bindError, 0)
        end
        -- Recover any previously stranded managed child while preserving unrelated UI.
        if child.GetChildren then
            for _, frame in ipairs({ child:GetChildren() }) do
                if frame.__bigBisManaged and not (self.renderActiveMembership and self.renderActiveMembership[frame]) then
                    frame:Hide()
                    frame:ClearAllPoints()
                    self:PoolRenderFrame(frame.__bigBisListRenderKind or "row", frame)
                end
            end
        end
        self:CountPerformance("realizedEntries", realized)
    end)
end

function UI:RenderEmpty(message)
    self:ReleaseRenderFrames()
    self.renderModel = nil
    self.hasRenderedContent = true
    self:RebindSelectedRowFromModel(nil)
    self:SetStickyHeaderMode(nil)
    if self.contentListLayer then self.contentListLayer:Hide() end
    if self.contentStaticLayer then self.contentStaticLayer:Hide() end
    if self.emptyLabel then
        self.emptyLabel:SetText(message)
        self.emptyLabel:Show()
    end
    self:SetContentHeight(-48)
    self:ApplyEmptyNavigation()
    self.emptyActions = self.emptyActions or {}
    for _, button in ipairs(self.emptyActions) do button:Hide() end
    local actions = {}
    if #self:GetActiveFilterChips() > 0 then actions[#actions+1] = { "Clear filters", function() self:ClearFilters() end } end
    local tab = self:GetSelection().tab
    if tab == "Wishlist" then actions[#actions+1] = { "Browse items", function() self:SetTab(self:IsLevelingMode() and "Gear Guide" or "By Slot") end } end
    if tab == "Upgrades" and self:GetFilters().upgradeMode ~= "all" then
        actions[#actions+1] = { "Show all candidates", function() self:SetFilter("upgradeMode", "all") end }
    end
    if tableCount(BigBiSList:GetCharacterDB().ignoredItems or {}) > 0 then
        actions[#actions+1] = { "Hidden items", function() self.settingsSection = "hidden"; self:OpenSettings() end }
    end
    for index, action in ipairs(actions) do
        local button = self.emptyActions[index]
        if not button then
            button = BigBiSList.Widgets:CreateTextButton(self.contentChild, "", 156, 28, function(owner) owner.callback() end)
            self.emptyActions[index] = button
        end
        button.callback = action[2]; button.label:SetText(action[1]); button:ClearAllPoints()
        button:SetPoint("TOPLEFT", self.emptyLabel, "BOTTOMLEFT", (index-1)*164, -14); button:Show()
    end
    if self.resultCountText then
        self.resultCountText:SetText("0 results")
    end
end

function UI:SetStickyHeaderMode(mode)
    if not self.contentHeaderHost or not self.contentScroll then
        return
    end

    local geometryChanged = not self.stickyHeaderLayoutInitialized or self.stickyHeaderMode ~= mode
    self.stickyHeaderLayoutInitialized = true
    self.stickyHeaderMode = mode

    if mode then
        self.contentHeaderHost:Show()
        self.stickyColumnHeader = self:CreateListColumnHeader(self.contentHeaderHost, 0, mode, self.stickyColumnHeader)
    else
        self.contentHeaderHost:Hide()
    end

    if geometryChanged then
        self.contentScroll:ClearAllPoints()
        if mode then
            self.contentScroll:SetPoint("TOPLEFT", self.contentHeaderHost, "BOTTOMLEFT", 0, -4)
        else
            self.contentScroll:SetPoint("TOPLEFT", self.contentPanel, "TOPLEFT", 8, -8)
        end
        self.contentScroll:SetPoint("BOTTOMRIGHT", self.contentPanel, "BOTTOMRIGHT", -28, 8)
    end
end

function UI:SetContentHeight(yOffset)
    local minimum = self.contentScroll and self.contentScroll:GetHeight() or 1
    local height = math.max(math.abs(yOffset) + 32, minimum + 1)
    self.contentChild:SetHeight(height)
    if self.contentListLayer then self.contentListLayer:SetHeight(height) end
    if self.contentStaticLayer then self.contentStaticLayer:SetHeight(height) end
end

function UI:GetDisplaySortValue(row, sortKey, mode)
    if sortKey == "priority" then
        local defaultSort = row.default_sort or {}
        local base = row.priority or (defaultSort.relevance and (1000000 - (defaultSort.relevance * 100000 + (defaultSort.rank or 0)))) or 0
        return base + (mode == "planner" and (row.scenario_priority or 0) * 1000000 or 0)
    elseif sortKey == "rank" then
        local history = self:GetRowRecommendationHistory(row)
        local cell = history and (history.selected.matched and history.selected or history.latest_earlier)
        local evidence = cell and (cell.rating_evidence or cell.evidence) or row.guide_evidence or {}
        local basis, grade
        for _, entry in ipairs(evidence) do
            if not entry.grade or #(entry.conditions or {}) > 0 or (basis and basis ~= entry.table_id) then
                return "~unresolved"
            end
            basis, grade = entry.table_id, entry.grade
        end
        return basis and (tostring(cell and cell.phase or row.phase or "") .. ":" .. basis .. ":" .. tostring(grade)) or "~unresolved"
    elseif sortKey == "item" then
        return lower(row.name)
    elseif sortKey == "slot" then
        for index, slot in ipairs(BigBiSList:GetEquipmentSlotDefinitions()) do
            if row.slotKey == slot.key or row.slot == slot.label then return index end
            for _, name in ipairs(slot.slots or {}) do if name == row.slot then return index end end
        end
        return 999
    elseif sortKey == "value" or sortKey == "recommendation" then
        local order = row.default_sort or {}
        return tonumber(row.recommendation_order) or tonumber(order.rank) or tonumber(row.rank) or (row.context == "budget" and 2 or 1)
    elseif sortKey == "source" then
        local source = self:GetRowAcquisitionDisplay(row)
        return lower(source)
    elseif sortKey == "location" then
        local _, location = self:GetRowAcquisitionDisplay(row)
        return lower(location)
    elseif sortKey == "owned" then
        local order = { missing = 0, bank = 1, bag = 2, equipped = 3, applied = 3 }
        return order[self:GetRowOwnershipState(row) or "missing"] or 0
    elseif sortKey == "expansion" then
        return row.wishlist_rank_sort or 999999
    end
    return lower(row.name)
end

function UI:SortDisplayRows(rows, mode)
    -- Query results are cached across presentation-only changes. Sort a
    -- shallow presentation copy so choosing the default order can always
    -- return to the immutable DataIndex order without rebuilding the corpus.
    local sortedRows = {}
    local originalOrder = {}
    for index, row in ipairs(rows or {}) do
        sortedRows[index] = row
        originalOrder[row] = index
    end
    local state = self:GetViewState()
    local sortKey = state.sort
    if not sortKey then
        return sortedRows
    end
    local direction = state.sortDirection or "asc"
    if sortKey == "priority" and (mode == "leveling" or mode == "wishlist") then
        if direction == "desc" then
            for index = 1, math.floor(#sortedRows/2) do
                local other = #sortedRows-index+1
                sortedRows[index], sortedRows[other] = sortedRows[other], sortedRows[index]
            end
        end
        return sortedRows
    end
    table.sort(sortedRows, function(a, b)
        if sortKey == "stat_rank" then
            if a.slot ~= b.slot then
                local aSlot = self:GetDisplaySortValue(a, "slot", mode)
                local bSlot = self:GetDisplaySortValue(b, "slot", mode)
                if aSlot ~= bSlot then return aSlot < bSlot end
                return (a.slot or "") < (b.slot or "")
            end
            local aRank, bRank = a.stat_rank and a.stat_rank.rank, b.stat_rank and b.stat_rank.rank
            if aRank ~= bRank then
                if not aRank or not bRank then return aRank ~= nil end
                if direction == "desc" then return aRank > bRank end
                return aRank < bRank
            end
            if lower(a.name) ~= lower(b.name) then return lower(a.name) < lower(b.name) end
            return originalOrder[a] < originalOrder[b]
        end
        if mode == "phase" and (a.historical_only == true) ~= (b.historical_only == true) then
            return b.historical_only == true
        end
        local aValue = self:GetDisplaySortValue(a, sortKey, mode)
        local bValue = self:GetDisplaySortValue(b, sortKey, mode)
        if aValue ~= bValue then
            if direction == "desc" then
                return aValue > bValue
            end
            return aValue < bValue
        end
        if lower(a.name) ~= lower(b.name) then
            return lower(a.name) < lower(b.name)
        end
        return (originalOrder[a] or 0) < (originalOrder[b] or 0)
    end)
    return sortedRows
end

local function hasVerifiedLevelingRoute(row)
    local display = row.acquisition_display
    local option = display and display.option
    return option and option.source_type and option.source_type ~= "unknown"
        and not option.is_inferred_trade_option and display.status == "ready" and display.source_match ~= nil
end

function UI:GetWithinReach(rows)
    local selection, addon = self:GetSelection(), BigBiSList
    local rating = addon.ForeverGearRating
    local level = addon:GetSelectedLevelingLevel()
    local character = addon:GetCharacterDB()
    if not rating or not self.currentOwned or not self.GetAcquisitionQuestProgress
        or (character.leveling and character.leveling.manualLevel)
        or addon:DetectPlayerClass() ~= selection.class or addon:DetectPlayerSpec(selection.class) ~= selection.spec
        or addon:GetDetectedPlayerLevel() ~= level then return nil end
    local contexts = rating:GetScenarioContexts(selection.class, selection.spec, "LEVELING", level, self.currentOwned)
    local context = contexts[1]
    if not context then return nil end
    local bags, groups, seen = {}, { {}, {}, {} }, {}
    local physical = self:GetLevelingReferenceSlot()
    for _, copy in ipairs(context.ownedCopies) do
        if copy.state == "bag" then
            local key = copy.facts.key
            bags[key] = bags[key] or {}
            bags[key][#bags[key] + 1] = copy
        end
    end
    for _, row in ipairs(rows) do
        local facts = row.stat_rank and row.stat_rank.item
        if facts and not seen[facts.key] then
            local ownership = self:GetRowOwnershipState(row)
            local best
            for _, copy in ipairs(bags[facts.key] or {}) do
                local candidate = rating:GetTooltipItem(facts.id, copy.item_link)
                local upgrades = candidate and rating:GetScenarioUpgrades(contexts, candidate, true,
                    { physical = physical, slot = row.slot, skipPlacement = true })
                if upgrades and upgrades[1] then
                    local swap = upgrades[1].swap
                    if not best or #upgrades > #best.upgrades or (#upgrades == #best.upgrades and swap.delta > best.swap.delta) then
                        best = { row = row, swap = swap, link = copy.item_link, upgrades = upgrades }
                    end
                end
            end
            if best then
                seen[facts.key] = true
                groups[1][#groups[1] + 1] = best
            elseif ownership == "missing" and hasVerifiedLevelingRoute(row) then
                local display = row.acquisition_display
                local route, access = self:GetSelectedAcquisitionRoute(row)
                local source = route == display.option and route.source
                local questId = source and (source.quest_id or (source.entity_type == "quest" and source.entity_id))
                if questId and (access.status == "ready" or access.status == "ready_alternate" or access.status == "check_prereq") then
                    local nextQuest, progress = self:GetAcquisitionQuestProgress(source)
                    if #progress == 0 then
                        local state, turnIn = self:GetAcquisitionQuestState(questId)
                        nextQuest = { step = { quest_id = questId, name = source.entity_name }, state = state, turnIn = turnIn }
                    end
                    local candidate = { facts = facts, key = facts.key, entry = { item_id = facts.id } }
                    local upgrades = rating:GetScenarioUpgrades(contexts, candidate, false, { skipPlacement = true })
                    if nextQuest and nextQuest.step.quest_id == questId and nextQuest.state == "In progress"
                        and upgrades[1] then
                        local group = groups[nextQuest.turnIn == true and 2 or 3]
                        group[#group + 1] = { row = row, quest = nextQuest, swap = upgrades[1].swap, upgrades = upgrades,
                            choiceReward = source.reward_type == "choice" }
                        seen[facts.key] = true
                    end
                end
            end
        end
    end
    return groups
end

function UI:AddWithinReach(model, rows, scope)
    local groups = self:GetWithinReach(rows)
    if not groups then return end
    local titles = { "Equip from bags", "Ready to turn in", "Reward quest in progress" }
    local added
    for index, items in ipairs(groups) do
        if #items > 0 then
            if not added then self:AddListRenderEntry(model, { kind = "note", text = "Within reach", height = 24 }) end
            local section = self:AddListSection(model, titles[index], nil, added == true, "reach:" .. scope .. ":" .. index)
            section.count = #items
            added = true
            if not section.collapsed then
                table.sort(items, function(a, b)
                    local rating = BigBiSList.ForeverGearRating
                    local selected = rating:GetScenario(self:GetGearScenarioSelection())
                    local aSelected, bSelected = a.upgrades[1].scenario == selected, b.upgrades[1].scenario == selected
                    if aSelected ~= bSelected then return aSelected end
                    if a.swap.delta ~= b.swap.delta then return a.swap.delta > b.swap.delta end
                    if a.row.name ~= b.row.name then return a.row.name < b.row.name end
                    return a.row.stat_identity < b.row.stat_identity
                end)
                for _, item in ipairs(items) do
                    local row, swap, quest = item.row, item.swap, item.quest
                    local detail = quest and quest.step.name or swap.definition.label
                    local scenarios = BigBiSList.ForeverGearRating:UpgradeScenarioSummary(item.upgrades)
                    if item.choiceReward then detail = (detail or row.slot) .. " · Choice reward" end
                    self:AddListRenderEntry(model, { kind = "action", title = row.name, height = 30,
                        detail = (detail or row.slot) .. " · " .. scenarios .. string.format(" · Est. %+.1f pts", swap.delta),
                        activate = function()
                            local data = row
                            if item.link then
                                data = {}
                                for key, value in pairs(row) do data[key] = value end
                                data.item_link = item.link
                            end
                            self:ShowInspectorFor(data.item_id, data, "leveling")
                        end })
                end
            end
        end
    end
    model.activeSection = nil
    if added then self:AddListGap(model, 8) end
end

function UI:GetLevelingActivities(groups, selection, level, filters)
    return self:GetCachedViewQuery("leveling-activities:" .. level, function()
        local ordered, byName, counted, seen = {}, {}, {}, {}
        local aliases = {Deadmines = "The Deadmines", ["Trade/AH"] = "Trade / Auction House"}
        local function activityFor(row)
            local name = BigBiSList:GetActivityGroup(row)
            name = aliases[name] or name
            local activity = byName[name]
            if not activity then
                activity = {name = name, rows = {}, upcoming = {}, itemCount = 0, missingCount = 0}
                byName[name] = activity
                ordered[#ordered + 1] = activity
                counted[activity] = {}
            end
            return activity
        end

        for _, group in ipairs(groups) do
            for _, row in ipairs(group.items) do
                local activity = activityFor(row)
                local identity = row.variant_id or row.item_id
                local counts = counted[activity]
                activity.rows[#activity.rows + 1] = row
                if not counts[identity] then
                    activity.itemCount = activity.itemCount + 1
                    counts[identity] = "counted"
                end
                if counts[identity] ~= "missing" and hasVerifiedLevelingRoute(row) and self:GetRowOwnershipState(row) == "missing" then
                    activity.missingCount = activity.missingCount + 1
                    counts[identity] = "missing"
                end
                seen[identity] = true
            end
        end

        for nextLevel = level + 1, math.min(level + 3, MAX_LEVELING_LEVEL) do
            local nextGroups = BigBiSList:GetLevelingRows(selection.class, selection.spec, nextLevel, filters)
            for _, group in ipairs(nextGroups) do
                for _, row in ipairs(group.items) do
                    local identity = row.variant_id or row.item_id
                    if not seen[identity] then
                        local upcoming = activityFor(row).upcoming
                        upcoming[#upcoming + 1] = {row = row, level = nextLevel}
                        seen[identity] = true
                    end
                end
            end
        end

        table.sort(ordered, function(a, b)
            local currentA, currentB = a.itemCount > 0, b.itemCount > 0
            if currentA ~= currentB then return currentA end
            if a.missingCount ~= b.missingCount then return a.missingCount > b.missingCount end
            return lower(a.name) < lower(b.name)
        end)
        return {ordered = ordered, byName = byName}
    end)
end

function UI:GetLevelingQuestActions(rows, selection, level)
    local actions = {}
    if not self.GetAcquisitionQuestProgress or BigBiSList:DetectPlayerClass() ~= selection.class
        or BigBiSList:GetDetectedPlayerLevel() ~= level then return actions end

    local seen = {}
    for index, row in ipairs(rows) do
        local display = row.acquisition_display
        local source = display and display.option and display.option.source
        if source and source.quest_steps and #source.quest_steps > 0
            and hasVerifiedLevelingRoute(row) and self:GetRowOwnershipState(row) == "missing" then
            local route, access = self:GetSelectedAcquisitionRoute(row)
            if route == display.option
                and (access.status == "ready" or access.status == "ready_alternate" or access.status == "check_prereq") then
                local quest = self:GetAcquisitionQuestProgress(source)
                if quest and quest.destination and not seen[quest.step.quest_id] then
                    actions[#actions + 1] = {quest = quest, row = row, order = index}
                    seen[quest.step.quest_id] = true
                end
            end
        end
    end
    table.sort(actions, function(a, b)
        local turnInA, turnInB = a.quest.turnIn == true, b.quest.turnIn == true
        if turnInA ~= turnInB then return turnInA end
        return a.order < b.order
    end)
    return actions
end

function UI:SetLevelingActivity(name)
    if not self:IsLevelingActivityView() or self.levelingActivity == name then return end
    self:BeginNavigationChange(name and "activity" or "activity-overview")
    self.levelingActivity = name
    self:Invalidate("presentation", "leveling-activity")
    self:ScheduleRefresh(nil, "leveling-activity")
end

function UI:RenderLevelingActivities(groups, selection, level, filters, emptyText)
    local activities = self:GetLevelingActivities(groups, selection, level, filters)
    local activity = activities.byName[self.levelingActivity]
    if self.levelingActivity and not activity then
        self.levelingActivity = nil
        self:ApplyBodyLayout()
    end
    if #activities.ordered == 0 then self:RenderEmpty(emptyText); return end

    local model = self:NewListRenderModel()
    if not activity then
        local rows = {}
        for _, group in ipairs(groups) do for _, row in ipairs(group.items) do rows[#rows + 1] = row end end
        self:AddWithinReach(model, rows, "activities")
        for _, destination in ipairs(activities.ordered) do
            local name, count = destination.name, destination.itemCount
            local detail = count > 0 and (count .. (count == 1 and " item" or " items")
                .. " · " .. destination.missingCount .. " unowned with known sources")
                or ("Recommended at level " .. destination.upcoming[1].level)
            self:AddListRenderEntry(model, {kind = "action", title = name, detail = detail, height = 30,
                activate = function() self:SetLevelingActivity(name) end})
            self:AddListGap(model, 4)
        end
        model.rowCount = #activities.ordered
        model.resultText = model.rowCount .. (model.rowCount == 1 and " activity" or " activities")
        self:RenderListModel(model)
        return
    end

    local rows = self:SortDisplayRows(activity.rows, "leveling")
    self:AddWithinReach(model, rows, "activity:" .. activity.name)
    local actions = self:GetLevelingQuestActions(rows, selection, level)
    if #actions > 0 then
        self:AddListRenderEntry(model, {kind = "note", text = "Next quest steps", height = 22})
        for index = 1, math.min(3, #actions) do
            local quest, row = actions[index].quest, actions[index].row
            self:AddListRenderEntry(model, {kind = "action", title = (quest.turnIn and "Turn in " or "Pick up ") .. quest.step.name,
                detail = quest.destination.name, height = 30,
                activate = function() self:ShowInspectorFor(row.item_id, row, "leveling") end})
            self:AddListGap(model, 4)
        end
        self:AddListGap(model, 6)
    end
    self:AddGearGuideRows(model, rows, "activity:" .. activity.name)
    if #activity.upcoming > 0 then
        if #rows == 0 then model.resultText = #activity.upcoming .. " upcoming" end
        self:AddListGap(model)
        local section = self:AddListSection(model, "Next levels", nil, true, "Coming up")
        section.count = #activity.upcoming
        if not section.collapsed then
            for _, preview in ipairs(activity.upcoming) do
                local row = preview.row
                self:AddListRenderEntry(model, {kind = "note", height = 32,
                    text = "Level " .. preview.level .. " · " .. row.name .. " · " .. self:GetRowSlotDisplay(row)})
            end
        end
    end
    self:RenderListModel(model)
end

function UI:RenderLevelingTab()
    local selection = self:GetSelection()
    local filters = self.currentFilterPayload or self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems
    local level = BigBiSList:GetSelectedLevelingLevel()
    local groups = self:GetCachedViewQuery("leveling:" .. level, function() return BigBiSList:GetLevelingRows(selection.class, selection.spec, level, filters) end)
    local notes = {}
    if BigBiSList.isForever then
        local rules = (BigBiSListData or {}).leveling_availability_rules or {}
        local policy = (rules.spec_policies or {})[selection.class .. "/" .. selection.spec] or {}
        local seen = {}
        for _, slots in ipairs({rules.common_slots or {}, policy.slots or {}}) do
            for _, slot in ipairs(slots) do
                if not seen[slot] and (not filters.slots or next(filters.slots) == nil or filters.slots[slot]) then
                    seen[slot] = true
                    local availability = BigBiSList:GetLevelingSlotStatus(selection.class, selection.spec, level, slot, filters)
                    if availability.state == "no_useful_item" then notes[#notes+1] = slot .. ": " .. availability.reason end
                end
            end
        end
    end
    local emptyText = #notes > 0 and table.concat(notes, "\n\n") or "No gear matches this level and filters."
    if self:IsLevelingActivityView() then self:RenderLevelingActivities(groups, selection, level, filters, emptyText); return end
    local rows = {}
    for _, group in ipairs(groups) do for _, row in ipairs(group.items) do rows[#rows+1] = row end end
    if #rows == 0 then self:RenderEmpty(emptyText); return end
    self:RenderGroupedRows(rows, "leveling", self:GetViewState().groupBy or "slot", "Level " .. level, notes)
end

function UI:RenderPhaseTab()
    local selection = self:GetSelection()
    local filters = self.currentFilterPayload or self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems
    local groups = self:GetCachedViewQuery("phase", function() return BigBiSList:GetPhaseRows(selection.class, selection.spec, selection.phase, filters) end)
    local rows = {}
    for _, group in ipairs(groups) do for _, row in ipairs(group.items) do rows[#rows+1] = row end end
    if #rows == 0 then self:RenderEmpty("No recommendations match this phase and filters."); return end
    self:RenderGroupedRows(rows, "phase", self:GetViewState().groupBy or "slot", "BiS List")
end

function UI:GetNextUpgradeActions(rows)
    local actions, shown = {}, {}
    for _, row in ipairs(rows) do
        if row.higher_rated and self:GetRowOwnershipState(row) == "bag" and not shown[row.item_id] then
            actions[#actions + 1] = { data = row, reason = row.scenario_summary or UPGRADE_MODE_LABELS.higher_rated,
                source = OWNERSHIP_LABELS.bag }
            shown[row.item_id] = true
            if #actions == 3 then return actions end
        end
    end
    local livePhase = BigBiSList:GetCurrentPhaseKey()
    local liveIndex = BigBiSList:GetAvailabilityPhaseIndex(livePhase)
    for _, row in ipairs(rows) do
        if row.upgrade_candidate and row.hasCurrent and not shown[row.item_id] and self:GetRowOwnershipState(row) == "missing" then
            local route, access = self:GetSelectedAcquisitionRoute(row)
            if route and route.source_type ~= "unknown" and (access.status == "ready" or access.status == "ready_alternate")
                and not isReportedOnlyAccessOption(route) and optionIsPhaseAvailable(route, liveIndex) then
                local source = self:GetAccessOptionDisplayText(route) or accessSourceBadgeLabel(route) or ""
                local location = trim(route.location_area or route.zone)
                if location ~= "" and not lower(source):find(lower(location), 1, true) then
                    source = source ~= "" and (source .. " · " .. location) or location
                end
                actions[#actions + 1] = { data = row,
                    reason = row.scenario_summary or (row.reasons or {})[1] or row.rank_label, source = source }
                shown[row.item_id] = true
                if #actions == 3 then break end
            end
        end
    end
    return actions
end

function UI:CreateNextUpgradeCard(parent, yOffset, action, row, height)
    local widgets = BigBiSList.Widgets
    if not row then
        row = widgets:CreateItemRow(parent, height)
        row.iconButton = widgets:CreateIconButton(row, 34)
        row.nameText = widgets:CreateWrappedLabel(row, "", "GameFontNormal")
        row.reasonText = widgets:CreateLabel(row, "", "GameFontHighlightSmall")
        row.sourceText = widgets:CreateLabel(row, "", "GameFontHighlightSmall")
        row.sourceText:SetTextColor(0.66, 0.79, 0.86)
        row:SetScript("OnMouseUp", function(owner, mouse)
            if owner:IsVisible() then self:HandleEntityGesture(owner.boundData, "planner", mouse, owner) end
        end)
        row.__bigBisManaged = true
    end
    local data = action.data
    local width = self:GetTableViewportWidth(parent, 760)
    row:SetParent(parent)
    row:ClearAllPoints()
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetSize(width, height)
    row:Show()
    row.boundData, row.boundMode = data, "planner"
    row:SetSelected(self.selectedRowKey == self:GetRowKey(data, "planner") and self.selectedRowKey ~= nil)
    row:SetHovered(false)
    row.iconButton:SetPoint("LEFT", row, "LEFT", 10, 0)
    row.nameText:SetPoint("LEFT", row, "LEFT", 54, 14)
    row.reasonText:SetPoint("LEFT", row, "LEFT", 54, 0)
    row.sourceText:SetPoint("LEFT", row, "LEFT", 54, -14)
    local textWidth = math.max(1, width - 64)
    row.nameText:SetWidth(textWidth)
    self:SetItemButton(row.iconButton, data.item_id, row.nameText, data.name, data.item and data.item.quality, data, "planner")
    widgets:SetCellText(row.nameText, row.nameText.fullText or data.name, 1, 14, textWidth)
    local reason = action.reason and (data.slot .. " · " .. action.reason) or data.slot
    widgets:SetCellText(row.reasonText, reason, 1, 13, textWidth)
    widgets:SetCellText(row.sourceText, action.source, 1, 13, textWidth)
    return row
end

function UI:ToggleUpgradesView()
    self:BeginNavigationChange("filter")
    self.upgradesView = self.upgradesView == "list" and "actions" or "list"
    self:Invalidate("presentation", "upgrade-view")
    self:ScheduleRefresh(nil, "upgrade-view")
end

function UI:RenderPlannerTab()
    local selection = self:GetSelection()
    local filters = self.currentFilterPayload or self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems
    local rows = self:GetCachedViewQuery("planner", function() return BigBiSList:GetPlannerRows(selection.class, selection.spec, selection.phase, filters) end)
    if rows.statsPending then self:QueueStatLoads(rows.statsPending) end
    local actions = self:GetNextUpgradeActions(rows)
    local hasActions = #actions > 0
    if self.hasNextUpgradeActions ~= hasActions then
        self.hasNextUpgradeActions = hasActions
        self:LayoutPrimaryControls()
    end
    if hasActions and self.upgradesView ~= "list" then
        local model = self:NewListRenderModel()
        local height = self:GetDensityMetrics() == 40 and 54 or 64
        for _, action in ipairs(actions) do
            self:AddListRenderEntry(model, { kind = "row", data = action.data, mode = "planner", nextAction = action,
                height = height, rowHeight = height })
            self:AddListGap(model)
        end
        model.rowCount = #actions
        self:RenderListModel(model)
        return
    end
    if #rows == 0 then self:RenderEmpty("No upgrade candidates match your gear and filters."); return end
    self:RenderGroupedRows(rows, "planner", self:GetViewState().groupBy or "priority", "Upgrades")
end

local PAPER_DOLL = {
    left = { "Head", "Neck", "Shoulder", "Back", "Chest", "Wrist" },
    right = { "Hands", "Waist", "Legs", "Feet", "Finger0", "Finger1", "Trinket0", "Trinket1" },
    weapons = { "MainHand", "OffHand", "Ranged" },
    filters = { Finger0 = "Rings", Finger1 = "Rings", Trinket0 = "Trinkets", Trinket1 = "Trinkets",
        MainHand = "Main Hand", OffHand = "Off Hand", Ranged = "Ranged/Relic" },
}

local function createPaperDollButton(parent, definition, label)
    local widgets = BigBiSList.Widgets
    local button = widgets:CreateTextButton(parent, label, 124, 30)
    local _, texture = getInventorySlotInfo(definition)
    button.slotTexture = texture
    button.slotKey = definition.key
    button.iconButton = widgets:CreateIconButton(button, 26)
    button.iconButton:EnableMouse(false)
    button.iconButton:SetPoint("LEFT", button, "LEFT", 5, 0)
    button.iconButton.icon:SetTexture(texture)
    button.label:ClearAllPoints()
    button.label:SetJustifyH("LEFT")
    button.label:SetPoint("LEFT", button.iconButton, "RIGHT", 6, 0)
    button.label:SetPoint("RIGHT", button, "RIGHT", -4, 0)
    return button
end

local function layoutPaperDoll(host, buttons, sideWidth, weaponWidth, size, gap, top)
    for index, keys in ipairs({ PAPER_DOLL.left, PAPER_DOLL.right }) do
        local point = index == 1 and "TOPLEFT" or "TOPRIGHT"
        local row = 0
        for _, key in ipairs(keys) do
            local button = buttons[key]
            if button then
                button:ClearAllPoints()
                button:SetPoint(point, host, point, 0, -top - row * (size + gap))
                button:SetSize(sideWidth, size)
                button.iconButton:SetSize(size - 6, size - 6)
                row = row + 1
            end
        end
    end
    for index, key in ipairs(PAPER_DOLL.weapons) do
        local button = buttons[key]
        button:ClearAllPoints()
        button:SetPoint("BOTTOM", host, "BOTTOM", (index - 2) * (weaponWidth + gap), top)
        button:SetSize(weaponWidth, size)
        button.iconButton:SetSize(size - 6, size - 6)
    end
end

function UI:GetFocusedBrowseSlot()
    local view = self:GetViewKey()
    if view ~= "bisList" and view ~= "gearGuide" then return nil end
    local slot
    for key, enabled in pairs(self:GetFilters().slots or {}) do
        if enabled then
            if slot then return nil end
            slot = key
        end
    end
    return slot == "Ring" and "Rings" or (slot == "Trinket" and "Trinkets" or slot)
end

function UI:CreateSlotPicker()
    local widgets = BigBiSList.Widgets
    local overlay = CreateFrame("Frame", nil, self.body)
    overlay:SetAllPoints()
    overlay:SetFrameLevel(self.body:GetFrameLevel() + 12)
    local popup = widgets:CreatePanel(nil, overlay, { 0.055, 0.055, 0.068, 1 })
    popup:EnableMouse(true)
    popup.slots = {}
    popup.host = CreateFrame("Frame", nil, popup)
    popup.host:SetPoint("TOPLEFT", popup, "TOPLEFT", 10, -42)
    popup.host:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -10, 10)
    popup.allButton = widgets:CreateTextButton(popup, "All slots", 94, 26, function()
        self:SetFilter("slots", {})
    end)
    popup.allButton:SetPoint("TOPLEFT", popup, "TOPLEFT", 10, -8)
    local labels, added = self:GetSlotFilterLabels(), {}
    for _, definition in ipairs(BigBiSList:GetEquipmentSlotDefinitions()) do
        local key = PAPER_DOLL.filters[definition.key] or definition.key
        if not added[key] then
            local button = createPaperDollButton(popup.host, definition, labels[key] or definition.label)
            button.filterKey = key
            button:SetScript("OnClick", function(owner)
                if owner:IsVisible() then self:ToggleSlot(owner.filterKey) end
            end)
            popup.slots[definition.key] = button
            added[key] = true
        end
    end
    overlay.popup = popup
    overlay:Hide()
    self.slotPickerOverlay = overlay
end

function UI:LayoutSlotPicker()
    local overlay = self.slotPickerOverlay
    if not overlay or not overlay:IsShown() then return end
    local popup, button = overlay.popup, self.slotPickerButton
    local width, height = overlay:GetWidth(), overlay:GetHeight()
    if width < 180 or height < 128 then return end
    local popupWidth = math.min(366, width)
    local popupHeight = math.min(276, height)
    local left = clamp((button:GetLeft() or 0) - (overlay:GetLeft() or 0), 0, width - popupWidth)
    local top = clamp((overlay:GetTop() or 0) - (button:GetBottom() or 0) + 4, 0, height - popupHeight)
    popup:ClearAllPoints()
    popup:SetPoint("TOPLEFT", overlay, "TOPLEFT", left, -top)
    popup:SetSize(popupWidth, popupHeight)
    local slotHeight = math.min(28, math.floor((popupHeight - 52 - 6 * 4) / 7))
    local sideWidth = math.min(126, math.floor((popupWidth - 24) / 2))
    local weaponWidth = math.floor((popupWidth - 28) / 3)
    layoutPaperDoll(popup.host, popup.slots, sideWidth, weaponWidth, slotHeight, 4, 0)
end

function UI:RefreshSlotPickerSelection()
    local overlay = self.slotPickerOverlay
    if not overlay or not overlay:IsShown() then return end
    local filters = self:GetFilters()
    local popup = overlay.popup
    popup.allButton:SetSelected(not tableHasAnyEnabled(filters.slots))
    for _, button in pairs(popup.slots) do
        button:SetSelected(filters.slots and filters.slots[button.filterKey])
    end
end

function UI:SetSlotPickerOpen(open)
    if not open then
        if self.slotPickerOverlay then self.slotPickerOverlay:Hide() end
        if self.slotPickerButton then self.slotPickerButton:SetSelected(false) end
        return
    end
    if not self.slotPickerButton or not self.slotPickerButton:IsVisible() then return end
    if self.filterDrawerOpen then self:SetFilterDrawerOpen(false) end
    BigBiSList.Widgets:CloseDropdownMenus()
    if not self.slotPickerOverlay then self:CreateSlotPicker() end
    self.slotPickerOverlay:Show()
    self.slotPickerButton:SetSelected(true)
    self:RefreshSlotPickerSelection()
    self:LayoutSlotPicker()
end

function UI:CreateSlotContext(parent)
    local widgets = BigBiSList.Widgets
    local frame = widgets:CreatePanel(nil, parent)
    frame:SetHeight(34)
    frame.label = widgets:CreateLabel(frame, "Equipped")
    frame.label:SetPoint("LEFT", frame, "LEFT", 8, 0)
    frame.compareButton = widgets:CreateTextButton(frame, "Compare slot", 100, 26, function(button)
        if not button:IsVisible() then return end
        local data = frame.reference or frame.items[1].data
        if BigBiSList.isForever and data and data.slotKey then
            self:OpenSlotComparison(data, "gear", true)
        else
            self:OpenSlotComparison(frame.slot, "phase")
        end
    end)
    frame.compareButton:SetPoint("RIGHT", frame, "RIGHT", -4, 0)
    frame.items = {}
    for index = 1, 2 do
        local item = CreateFrame("Frame", nil, frame)
        item:SetHeight(28)
        item:EnableMouse(true)
        item.iconButton = widgets:CreateIconButton(item, 22)
        item.iconButton:EnableMouse(false)
        item.iconButton:SetPoint("LEFT")
        item.name = widgets:CreateLabel(item, "", "GameFontHighlightSmall")
        item.name:SetPoint("LEFT", item.iconButton, "RIGHT", 5, 0)
        widgets:BindTooltip(item, function(owner, tooltip)
            if owner.iconButton.itemLink then tooltip:SetHyperlink(owner.iconButton.itemLink)
            elseif owner.data then tooltip:SetText(owner.data.name) end
        end)
        frame.items[index] = item
    end
    frame:Hide()
    return frame
end

function UI:GetLevelingReferenceSlot()
    local reference = self.levelingSlotReference
    if not reference or self:GetViewKey() ~= "gearGuide" or not self:IsLevelingMode() then return nil end
    local slot = reference.slotKey
    if reference.character == BigBiSList:GetCharacterDB() and (PAPER_DOLL.filters[slot] or slot) == self:GetFocusedBrowseSlot() then
        return slot
    end
    self.levelingSlotReference = nil
end

function UI:RefreshSlotContext()
    local frame, slot = self.slotContextFrame, self:GetFocusedBrowseSlot()
    local referenceSlot = self:GetLevelingReferenceSlot()
    local selection = self:GetSelection()
    local contexts = slot and self.currentOwned
        and BigBiSList:GetEquipmentComparisonContexts(selection.class, selection.spec, self:GetEffectivePhaseKey(), self.currentOwned, referenceSlot or slot)
        or {}
    frame.reference = referenceSlot and contexts[1] or nil
    frame:SetShown(#contexts > 0)
    if #contexts == 0 then return false end
    frame.slot = slot
    frame.label:SetText(frame.reference and frame.reference.slot or "Equipped")
    local compare = (BigBiSList.isForever or not self:IsLevelingMode()) and self.OpenSlotComparison ~= nil
    frame.compareButton:SetShown(compare)
    local width = self.contentRegion:GetWidth()
    local labelWidth = math.max(68, math.ceil(frame.label:GetStringWidth()) + 17)
    local itemWidth = math.max(28, math.floor((width - labelWidth - 5 - (compare and 109 or 0)) / #contexts))
    for index, item in ipairs(frame.items) do
        local data = contexts[index]
        item.data = data
        item:SetShown(data ~= nil)
        if data then
            item:SetWidth(itemWidth)
            item:SetPoint("LEFT", frame, "LEFT", labelWidth + (index - 1) * itemWidth, 0)
            item.iconButton:SetShown(data.item_id ~= nil)
            if data.item_id then
                self:SetItemButton(item.iconButton, data.item_id, item.name, data.name, nil, data, "gear")
            else
                self:ResetEntityButton(item.iconButton, item.name, data.name)
                item.name:SetTextColor(0.76, 0.76, 0.80)
            end
            item.name:SetPoint("LEFT", item, "LEFT", data.item_id and 27 or 0, 0)
            BigBiSList.Widgets:SetCellText(item.name, item.name.fullText or data.name, 1, 13, math.max(1, itemWidth - (data.item_id and 33 or 6)))
        end
    end
    return true
end

function UI:FindGearSlotUpgrades(data)
    if not data or data.disabledReason then return end
    local target = self:IsLevelingMode() and "Gear Guide" or "Upgrades"
    local slot = PAPER_DOLL.filters[data.slotKey] or data.slotKey
    if target == "Upgrades" then
        self.upgradesView = "list"
    elseif BigBiSList.isForever then
        self.levelingActivity = nil
        self.levelingSlotReference = {slotKey = data.slotKey, character = BigBiSList:GetCharacterDB()}
    end
    self:GetFilters(target).slots = { [slot] = true }
    self:SetTab(target, "equipment-upgrades")
end

local function gearLabelWidth(label, text)
    label:SetWidth(0)
    label:SetWordWrap(false)
    label:SetText(text)
    return math.ceil(label:GetStringWidth()) + 2
end

local function layoutGearSlotText(button)
    local data = button.gearData
    if not data then return end
    local widgets = BigBiSList.Widgets
    local occupied = data.item_id ~= nil
    local width = math.max(1, button:GetWidth() - button.iconButton:GetWidth() - 15)
    local twoLines = button:GetHeight() >= 27 and width >= 24
    local nameHeight = math.min(14, button:GetHeight())
    local nameY = twoLines and 6.5 or 0
    local service, placement = BigBiSList.ForeverGearRating, data.stat_rank
    local rankColor = RANK_COLORS[data.display_rank_kind]
    local badge = button.guideBadge
    local nameWidth = width
    if badge then
        badge:SetShown(occupied and data.guide_badge ~= nil)
        if badge:IsShown() then
            local text = data.guide_badge
            local badgeWidth = gearLabelWidth(badge, text)
            local nameReserve = math.min(72, math.floor(width * 0.45))
            if not data.equipped_bis and not data.leveling and not data.historical_only and badgeWidth > width - nameReserve - 6 then
                text = "Guide note"
                badgeWidth = gearLabelWidth(badge, text)
            end
            badge:SetPoint("RIGHT", button, "RIGHT", -4, nameY)
            widgets:SetCellText(badge, text, 1, 12, math.min(badgeWidth, width))
            local color = widgets.Theme.bisGold
            if not data.equipped_bis and rankColor then
                badge:SetTextColor(rankColor[5], rankColor[6], rankColor[7])
            else
                badge:SetTextColor(unpack(color))
            end
            nameWidth = math.max(1, width - badgeWidth - 6)
        end
    end
    local name = button.itemName
    name:SetPoint("LEFT", button.iconButton, "RIGHT", 6, nameY)
    widgets:SetCellText(name, name.fullText or data.slot, 1, nameHeight, nameWidth)
    button.label:SetShown(twoLines and occupied)
    button.rating:SetShown(twoLines)
    button.stateIcon:SetShown(data.disabledReason ~= nil)
    local tier = twoLines and placement and placement.tier
    if not twoLines then return end

    local rating = data.overlay
    if occupied and badge and not data.build_target then
        rating = service:Label(placement)
    elseif occupied and data.bestUse then
        rating = data.display_rank_label or rating
    end
    if tier then
        button.rating:SetTextColor(widgets:GetRankColor(tier.quality))
    elseif not badge and occupied and rankColor and data.display_rank_kind ~= "missing" then
        button.rating:SetTextColor(rankColor[5], rankColor[6], rankColor[7])
    else
        button.rating:SetTextColor(unpack(placement and placement.rank and placement.total > 1 and widgets.Theme.text or widgets.Theme.muted))
    end
    local metaY = -(nameHeight + 1) / 2
    button.rating:ClearAllPoints()
    if occupied then
        local ratingWidth = gearLabelWidth(button.rating, rating)
        local ratingLimit = math.floor(width * 0.65)
        if badge then
            local slotWidth = gearLabelWidth(button.label, data.slot)
            local available = width - 6
            if placement and placement.rank and placement.total > 1 and ratingWidth > available - slotWidth then
                rating = service:Label(placement, "compact")
                ratingWidth = gearLabelWidth(button.rating, rating)
            end
            ratingLimit = available - math.min(slotWidth, 24)
            if placement and placement.score_percent and ratingWidth < available - slotWidth then
                local label = rating .. " · " .. placement.score_percent .. "%"
                local labelWidth = gearLabelWidth(button.rating, label)
                if labelWidth <= available - slotWidth then rating, ratingWidth = label, labelWidth end
            end
        end
        ratingWidth = math.max(1, math.min(ratingWidth, ratingLimit))
        button.rating:SetJustifyH("RIGHT")
        button.rating:SetPoint("RIGHT", button, "RIGHT", -4, metaY)
        widgets:SetCellText(button.rating, rating, 1, 12, ratingWidth)
        button.label:SetPoint("LEFT", button.iconButton, "RIGHT", 6, metaY)
        widgets:SetCellText(button.label, data.slot, 1, 12, width - ratingWidth - 6)
    else
        button.rating:SetJustifyH("LEFT")
        button.rating:SetPoint("LEFT", button.iconButton, "RIGHT", 6, metaY)
        widgets:SetCellText(button.rating, rating, 1, 12, width)
    end
end

local function layoutGearSummaryText(summary)
    local name, rating = summary.itemName, summary.rating
    name:SetHeight(0)
    name:SetText(name.fullText or "")
    name:SetHeight(math.max(14, name:GetStringHeight() or 0))
    local height = 8 + summary.slot:GetHeight() + 3 + name:GetHeight() + 8 + summary.findButton:GetHeight() + 8
    if rating:IsShown() then
        rating:SetHeight(0)
        rating:SetHeight(math.max(13, rating:GetStringHeight() or 0))
        height = height + 3 + rating:GetHeight()
    end
    if height ~= summary:GetHeight() then
        summary:SetHeight(height)
        UI:RefreshGearPreview()
    end
end

function UI:CreateGearWorkspace(parent, builds)
    local widgets = BigBiSList.Widgets
    local gear = CreateFrame("Frame", nil, parent)
    gear:SetPoint("TOPLEFT", parent, "TOPLEFT", 14, -12)
    gear:SetPoint("BOTTOMRIGHT", parent, "BOTTOMRIGHT", -14, 12)
    gear.isBuild = builds
    gear.slots = {}
    for _, definition in ipairs(BigBiSList:GetEquipmentSlotDefinitions()) do
        local button = createPaperDollButton(gear, definition, definition.label)
        button.label:ClearAllPoints()
        button.itemName = widgets:CreateWrappedLabel(button, "", "GameFontHighlight")
        button.rating = widgets:CreateLabel(button, "", "GameFontHighlightSmall")
        if BigBiSList.ForeverGearRating then
            button.guideBadge = widgets:CreateLabel(button, "", "GameFontHighlightSmall")
            button.guideBadge:SetJustifyH("RIGHT")
            button.guideBadge:Hide()
        end
        local stateIcon = button.iconButton:CreateTexture(nil, "OVERLAY")
        widgets:SetIcon(stateIcon, "warning")
        stateIcon:SetVertexColor(1, 0.76, 0.35)
        stateIcon:SetSize(14, 14)
        stateIcon:SetPoint("BOTTOMRIGHT", button.iconButton)
        stateIcon:Hide()
        button.stateIcon = stateIcon
        button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        button:SetScript("OnClick", function(owner, mouse)
            local data = owner.gearData
            if not data or not owner:IsVisible() then return end
            if builds then
                if data.item_id and mouse == "LeftButton" then
                    self.buildSlotKey = data.slotKey
                    for _, tile in pairs(gear.slots) do tile:SetSelected(tile == owner) end
                end
                if data.item_id then self:HandleEntityGesture(data, "build", mouse, owner) end
            elseif data.item_id and (mouse == "RightButton" or (IsShiftKeyDown and IsShiftKeyDown())
                or (IsControlKeyDown and IsControlKeyDown())) then
                self:HandleEntityGesture(data, "gear", mouse, owner)
            elseif mouse == "LeftButton" then
                self.gearSlotKey = data.slotKey
                self:RefreshGearSelection()
            end
        end)
        widgets:BindTooltip(button, function(owner, tooltip)
            local data = owner.gearData
            if not data then return end
            local link = owner.iconButton.itemLink
            if link then
                tooltip:SetHyperlink(link)
            else
                tooltip:SetText(data.slot, 1, 0.82, 0.28)
                if data.item_id then tooltip:AddLine(owner.itemName.fullText or data.name, 0.88, 0.88, 0.92, true) end
            end
            if data.stat_rank then
                local service = BigBiSList.ForeverGearRating
                for _, line in ipairs(service:DescriptionLines(data.stat_rank)) do
                    tooltip:AddLine(line, 0.88, 0.88, 0.92, true)
                end
            end
            if data.build_target then
                tooltip:AddLine(data.overlay, 0.88, 0.88, 0.92, true)
            elseif not data.stat_rank or data.bestUse then
                tooltip:AddLine(data.guide_note or data.recommendation_summary, 0.88, 0.88, 0.92, true)
            end
        end)
        gear.slots[definition.key] = button
    end

    if builds then
        self:CreateBuildSummary(gear)
        gear:Hide()
        return gear
    end

    local preview = CreateFrame("Frame", nil, gear)
    preview.name = widgets:CreateLabel(preview, "", "GameFontNormal")
    preview.name:SetPoint("TOP", preview)
    if BigBiSList.ForeverGearRating then
        preview.score = widgets:CreateLabel(preview, "", "GameFontHighlight")
        preview.score:SetPoint("BOTTOM", preview)
        preview.scoreTooltip = CreateFrame("Frame", nil, preview)
        preview.scoreTooltip:SetAllPoints(preview.score)
        preview.scoreTooltip:EnableMouse(true)
        widgets:BindTooltip(preview.scoreTooltip, function(_, tooltip)
            local data = gear.score
            tooltip:SetText("Gear score")
            tooltip:AddLine("Equipped stat points as a share of the best known legal outfit for this spec and weapon setup.", 1, 1, 1, true)
            if data then
                tooltip:AddLine(string.format("%.1f / %.1f stat points", data.score, data.best))
                if data.partial > 0 then
                    tooltip:AddLine(string.format("%d slots scored · %d unavailable", data.covered, data.partial))
                end
            end
        end)
    end
    preview.portrait = preview:CreateTexture(nil, "ARTWORK")
    preview.portrait:SetSize(68, 68)
    preview.portrait:SetPoint("CENTER", preview, "CENTER", 0, -5)
    preview.portrait:Hide()
    local ok, model = pcall(CreateFrame, "PlayerModel", nil, preview)
    if ok and model then
        model:SetPoint("TOPLEFT", preview, "TOPLEFT", 0, -20)
        model:SetPoint("BOTTOMRIGHT", preview, "BOTTOMRIGHT", 0, preview.score and 19 or 0)
        model:Hide()
        if model.SetUnit then
            model:EnableMouse(false)
            preview.model = model
        end
    end
    gear.preview = preview

    local summary = widgets:CreatePanel(nil, gear, { 0.075, 0.075, 0.088, 0.95 }, { 0.22, 0.22, 0.25, 1 })
    summary:SetHeight(92)
    summary.itemButton = widgets:CreateIconButton(summary, 16)
    summary.itemButton:EnableMouse(false)
    summary.itemButton:SetPoint("TOPRIGHT", summary, "TOPRIGHT", -8, -4)
    summary.itemButton.OnItemNameChanged = function()
        layoutGearSummaryText(summary)
    end
    summary.slot = widgets:CreateLabel(summary, "")
    summary.slot:SetTextColor(0.80, 0.75, 0.63)
    summary.slot:SetPoint("TOPLEFT", summary, "TOPLEFT", 10, -8)
    summary.itemName = widgets:CreateWrappedLabel(summary, "", "GameFontNormal")
    summary.itemName:SetPoint("TOPLEFT", summary.slot, "BOTTOMLEFT", 0, -3)
    summary.rating = widgets:CreateWrappedLabel(summary, "", "GameFontHighlightSmall")
    summary.rating:SetPoint("TOPLEFT", summary.itemName, "BOTTOMLEFT", 0, -3)
    if BigBiSList.ForeverGearRating then
        local compare = CreateFrame("Button", nil, summary)
        compare:SetPoint("TOPLEFT", summary.rating, "TOPLEFT")
        compare:SetPoint("BOTTOMRIGHT", summary.rating, "BOTTOMRIGHT")
        compare:RegisterForClicks("LeftButtonUp")
        compare:SetScript("OnClick", function(button)
            if button:IsVisible() and summary.gearData then self:OpenSlotComparison(summary.gearData, "gear", true) end
        end)
        widgets:BindTooltip(compare, function(_, tooltip)
            tooltip:SetText("Compare slot by stat rank")
            local data = summary.gearData
            local placement = data and data.stat_rank
            if placement then
                for _, line in ipairs(BigBiSList.ForeverGearRating:DescriptionLines(placement)) do
                    tooltip:AddLine(line, 0.88, 0.88, 0.92, true)
                end
            end
            if data and data.bestUse then
                tooltip:AddLine(data.guide_note or data.recommendation_summary, 0.88, 0.88, 0.92, true)
            end
        end)
        compare:Hide()
        summary.statCompare = compare
    end
    summary.findButton = widgets:CreateTextButton(summary, "Find upgrades", 110, 24, function(button)
        if button:IsVisible() then self:FindGearSlotUpgrades(summary.gearData) end
    end)
    summary.findButton:SetPoint("BOTTOMLEFT", summary, "BOTTOMLEFT", 10, 8)
    summary.detailsButton = widgets:CreateTextButton(summary, "Details", 68, 24, function(button)
        local data = summary.gearData
        if button:IsVisible() and data and data.item_id then self:ShowInspectorFor(data.item_id, data, "gear") end
    end)
    summary.detailsButton:SetPoint("LEFT", summary.findButton, "RIGHT", 6, 0)
    summary:Hide()
    gear.summary = summary
    gear:Hide()
    return gear
end

function UI:RefreshGearPreview()
    local preview = self.gearFrame.preview
    local useModel = preview.model and preview:GetHeight() >= 158 and preview:GetWidth() >= 150
    local hasModel = false
    if useModel then
        preview.model:Show()
        local ok, result = pcall(preview.model.SetUnit, preview.model, "player")
        hasModel = ok and result ~= false
    end
    if preview.model then preview.model:SetShown(hasModel) end
    local ok = false
    if not hasModel and SetPortraitTexture and preview:GetHeight() >= 84 then
        ok = pcall(SetPortraitTexture, preview.portrait, "player")
    end
    preview.portrait:SetShown(ok)
    preview.name:SetText(UnitName and UnitName("player") or "")
    if preview.score then
        local score = self.gearFrame.score
        preview.score:SetText(score and score.percent and ("Gear score · " .. score.percent .. "%"
            .. (score.partial > 0 and " · Partial" or "")) or "Gear score unavailable")
        if score and score.tier then
            preview.score:SetTextColor(BigBiSList.Widgets:GetRankColor(score.tier.quality))
        else
            preview.score:SetTextColor(unpack(BigBiSList.Widgets.Theme.muted))
        end
    end
end

function UI:LayoutGearWorkspace(workspace)
    local gear = workspace or self.gearFrame
    if not gear or not gear:IsVisible() then return end
    local width, height = gear:GetWidth(), gear:GetHeight()
    if width <= 0 or height <= 0 then return end
    local density = self:GetDensityMetrics()
    local signature = table.concat({ width, height, density }, ":")
    if gear.layoutSignature == signature then return end
    gear.layoutSignature = signature
    local gap = height >= 350 and 5 or 3
    local rows = #PAPER_DOLL.right + 1
    local size = math.max(8, math.min(density == 40 and 32 or 42, math.floor((height - rows * gap) / rows)))
    local top = math.max(0, math.floor((height - rows * size - rows * gap) / 2))
    local centerWidth = math.min(clamp(math.floor(width * 0.30), 204, 326), math.floor(width / 2))
    local sideWidth = math.max(1, math.floor((width - centerWidth - 24) / 2))
    local weaponWidth = math.max(1, math.floor((width - 2 * gap) / 3))
    layoutPaperDoll(gear, gear.slots, sideWidth, weaponWidth, size, gap, top)
    for _, button in pairs(gear.slots) do layoutGearSlotText(button) end
    if gear.isBuild then
        local summary = gear.summary
        summary:SetWidth(centerWidth)
        summary:SetPoint("TOP", gear, "TOP", 0, -top)
        summary:SetPoint("BOTTOM", gear, "BOTTOM", 0, top + size + 10)
        self:LayoutBuildSummary(gear)
        return true
    end

    local summary, preview = gear.summary, gear.preview
    summary:SetWidth(centerWidth)
    summary:SetPoint("BOTTOM", gear, "BOTTOM", 0, top + size + 10)
    summary.itemName:SetWidth(math.max(1, centerWidth - 20))
    summary.rating:SetWidth(math.max(1, centerWidth - 20))
    local actionsWidth = math.max(2, centerWidth - 26)
    local findWidth = math.min(110, math.floor(actionsWidth * 0.62))
    summary.findButton:SetWidth(findWidth)
    summary.detailsButton:SetWidth(math.min(68, actionsWidth - findWidth))
    preview:SetWidth(math.min(292, centerWidth))
    preview:SetPoint("TOP", gear, "TOP", 0, -top)
    preview:SetPoint("BOTTOM", summary, "TOP", 0, 8)
    self:RefreshGearPreview()
    return true
end

function UI:RefreshGearSelection()
    local gear = self.gearFrame
    local summary = gear.summary
    local selected = gear.slots[self.gearSlotKey]
    local data = selected and selected.gearData
    summary.gearData = data
    summary:SetShown(data ~= nil)
    if summary.statCompare then summary.statCompare:SetShown(data ~= nil and data.stat_rank ~= nil) end
    for _, button in pairs(gear.slots) do button:SetSelected(button == selected) end
    if data then
        summary.slot:SetText(data.slot)
        summary.itemButton:SetShown(data.item_id ~= nil)
        if data.stat_rank then
            local service = BigBiSList.ForeverGearRating
            local placement = data.stat_rank
            local label = service:Label(placement) .. " ›"
            if placement.score_percent then label = label .. " · " .. placement.score_percent .. "% of best" end
            label = label .. "\n" .. service:ContextLabel(placement)
            if data.bestUse then label = label .. "\n" .. data.recommendation_summary end
            summary.rating:SetText(label)
            summary.rating:SetTextColor(0.58, 0.81, 0.96)
        else
            summary.rating:SetText(data.recommendation_summary)
            summary.rating:SetTextColor(1, 1, 1)
        end
        summary.rating:SetShown(data.item_id ~= nil)
        if data.item_id then
            self:SetItemButton(summary.itemButton, data.item_id, summary.itemName, data.name, data.item and data.item.quality, data, "gear")
        else
            self:ResetEntityButton(summary.itemButton, summary.itemName, data.recommendation_summary)
            summary.itemName:SetTextColor(0.88, 0.88, 0.92)
        end
        layoutGearSummaryText(summary)
        summary.findButton:SetEnabled(not data.disabledReason)
        summary.detailsButton:SetShown(data.item_id ~= nil)
    end
    if self:IsInspectorVisible() and not self.slotComparison and self.selectedItemData ~= data then
        if data and data.item_id then
            self:ShowInspectorFor(data.item_id, data, "gear")
        else
            self:ClearSelectedRow()
            self:RefreshDetails()
        end
    end
end

function UI:CreateBuildSummary(gear)
    local widgets = BigBiSList.Widgets
    local summary = CreateFrame("Frame", nil, gear)
    gear.summary = summary
    summary.selector = widgets:CreateDropdown(nil, summary, 140, function()
        return gear.build and gear.build.name or ""
    end, function()
        local items = {}
        for _, build in ipairs(gear.builds or {}) do
            items[#items + 1] = { text = build.name, value = build.id, checked = build == gear.build }
        end
        return items
    end, function(id)
        self.buildPreview = { mode = self:GetSelection().mode, id = id }
        self.buildSlotKey = nil
        self:Invalidate("presentation", "build-selection")
        self:ScheduleRefresh(nil, "build-selection")
    end)
    summary.selector:SetPoint("TOP", summary, "TOP", 0, 4)
    summary.title = widgets:CreateLabel(summary, "", "GameFontNormal")
    summary.title:SetPoint("TOP", summary.selector, "BOTTOM", 0, -2)
    summary.notes = widgets:CreateWrappedLabel(summary, "", "GameFontHighlightSmall")
    summary.notes:SetPoint("TOPLEFT", summary, "TOPLEFT", 8, -55)
    local notesHover = CreateFrame("Frame", nil, summary)
    notesHover:SetPoint("TOPLEFT", summary.notes, "TOPLEFT")
    notesHover:SetPoint("BOTTOMRIGHT", summary.notes, "BOTTOMRIGHT")
    notesHover:EnableMouse(true)
    widgets:BindTooltip(notesHover, function(_, tooltip)
        if not gear.build then return end
        tooltip:SetText(gear.build.name)
        for _, line in ipairs({ gear.build.goal, gear.build.talents, gear.build.requirements, gear.build.source_name }) do
            tooltip:AddLine(line, 0.88, 0.88, 0.92, true)
        end
    end)
    summary.track = widgets:CreateTextButton(summary, "Track build", 100, 24, function()
        if not gear.build then return end
        local char, mode = BigBiSList:GetCharacterDB(), self:GetSelection().mode
        char.trackedBuilds = char.trackedBuilds or {}
        char.trackedBuilds[mode] = char.trackedBuilds[mode] ~= gear.build.id and gear.build.id or nil
        self:Invalidate("presentation", "build-track")
        self:ScheduleRefresh(nil, "build-track")
    end)
    summary.track:SetPoint("BOTTOMLEFT", summary, "BOTTOMLEFT", 8, 0)
    summary.progress = widgets:CreateLabel(summary, "", "GameFontHighlightSmall")
    summary.progress:SetPoint("LEFT", summary.track, "RIGHT", 8, 0)
    summary.source = CreateFrame("EditBox", nil, summary, "InputBoxTemplate")
    summary.source:SetAutoFocus(false)
    summary.source:SetHeight(20)
    summary.source:SetPoint("BOTTOMLEFT", summary.track, "TOPLEFT", 5, 8)
    summary.source:SetPoint("BOTTOMRIGHT", summary, "BOTTOMRIGHT", -8, 32)
    summary.source:SetScript("OnEditFocusGained", function(box) box:HighlightText() end)
    summary.source:SetScript("OnEscapePressed", function(box) box:ClearFocus() end)
    summary.source:SetScript("OnTextChanged", function(box, userInput)
        if userInput and gear.build then box:SetText(gear.build.source_url); box:HighlightText() end
    end)
    widgets:BindTooltip(summary.source, function(_, tooltip)
        if gear.build then tooltip:SetText(gear.build.source_name); tooltip:AddLine("Select the link to copy it.") end
    end)
    gear.empty = widgets:CreateWrappedLabel(gear, "No reviewed builds for this spec and level or phase.", "GameFontHighlight")
    gear.empty:SetPoint("CENTER")
    gear.empty:SetWidth(250)
end

function UI:LayoutBuildSummary(gear)
    if not gear.build then return end
    local summary = gear.summary
    local lines = math.max(1, math.floor((summary:GetHeight() - 112) / 13))
    BigBiSList.Widgets:SetCellText(summary.notes, summary.notes.fullText or "", lines, 13, math.max(1, summary:GetWidth() - 16))
end

function UI:GetBuildWorkspaceRows(gear, selection, filters)
    local level, phase = filters.level, self:GetEffectivePhaseKey()
    gear.builds = BigBiSList:GetReviewedBuilds(selection.class, selection.spec, phase, level)
    local char, preview = BigBiSList:GetCharacterDB(), self.buildPreview
    local tracked = char.trackedBuilds and char.trackedBuilds[selection.mode]
    local wanted = preview and preview.mode == selection.mode and preview.id or tracked
    local build = gear.builds[1]
    for _, candidate in ipairs(gear.builds) do
        if candidate.id == wanted then build = candidate; break end
    end
    gear.build = build
    if not build then return {} end
    return BigBiSList:GetBuildGearRows(build, self.currentOwned, phase)
end

function UI:UpdateBuildSummary(gear, rows)
    local build, summary = gear.build, gear.summary
    summary:SetShown(build ~= nil)
    gear.empty:SetShown(not build)
    if not build then return end
    local char, mode = BigBiSList:GetCharacterDB(), self:GetSelection().mode
    local tracked = char.trackedBuilds and char.trackedBuilds[mode] == build.id
    summary.track.label:SetText(tracked and "Untrack build" or "Track build")
    summary.track:SetSelected(tracked)
    summary.progress:SetText(string.format("%d/%d owned", rows.owned, rows.total))
    summary.selector:Refresh()
    summary.title:SetText((build.phase == LEVELING_PHASE_KEY and ("Level " .. build.level_min .. "–" .. build.level_max)
        or BigBiSList:GetPhaseDisplayName(build.phase)) .. " · " .. (build.faction or build.spec))
    summary.notes.fullText = table.concat({build.goal, build.talents, build.requirements, build.source_name}, "\n\n")
    self:LayoutBuildSummary(gear)
    summary.source:SetText(build.source_url)
end

function UI:RenderGearTab()
    local selection = self:GetSelection()
    local filters = self.currentFilterPayload or self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems
    local inBuilds = self:GetViewKey() == "builds"
    local gear = inBuilds and self.buildFrame or self.gearFrame
    local rows
    if inBuilds then
        rows = self:GetBuildWorkspaceRows(gear, selection, filters)
    else
        rows = self:GetCachedViewQuery("gear", function()
            return BigBiSList:GetEquippedGearRows(selection.class, selection.spec, self:GetEffectivePhaseKey(), self.currentOwned, filters.level)
        end)
    end
    self:QueueStatLoads(rows.statsPending)
    self:RunRenderTransaction(function()
        self.renderModel = nil
        self:ReleaseRenderFrames()
        self.renderedContextKey = self:GetNavigationContextKey()
        self.pendingNavigation = nil
        self.hasRenderedContent = true
        self:SetStickyHeaderMode(nil)
        self.contentScroll:SetVerticalScroll(0)
        self.contentChild:SetHeight(math.max(1, self.contentScroll:GetHeight()))
        self.contentListLayer:Hide()
        self.contentStaticLayer:Hide()
        self.emptyLabel:Hide()
        for _, button in ipairs(self.emptyActions or {}) do button:Hide() end
        gear.score = rows.gearScore
        gear:SetShown(not self.inspectorExclusive)
        self.contentScroll:Hide()
        if inBuilds then
            self:UpdateBuildSummary(gear, rows)
            for _, button in pairs(gear.slots) do button:SetShown(gear.build ~= nil) end
        end
        for _, data in ipairs(rows) do
            local button = gear.slots[data.slotKey]
            button.gearData = data
            if inBuilds then button:SetSelected(self.buildSlotKey == data.slotKey) end
            BigBiSList.Widgets:SetEquippedBiS(button, data.equipped_bis)
            if data.item_id then
                self:SetItemButton(button.iconButton, data.item_id, button.itemName, data.name, data.item and data.item.quality, data, "gear")
            else
                self:ResetEntityButton(button.iconButton, button.itemName, data.slot)
                button.itemName:SetTextColor(0.75, 0.76, 0.81)
                if data.overlayKind ~= "unknown" then button.iconButton.icon:SetTexture(button.slotTexture) end
            end
            layoutGearSlotText(button)
        end
        local geometryChanged = self:LayoutGearWorkspace(gear)
        if inBuilds then return end
        self:RefreshGearSelection()
        if gear:IsVisible() and self.gearPreviewOwnership ~= self.currentOwned then
            self.gearPreviewOwnership = self.currentOwned
            if not geometryChanged then self:RefreshGearPreview() end
        end
    end)
end

function UI:RenderEnhanceTab()
    if self:IsLevelingMode() then
        self:RenderEmpty("Enhancements are endgame-focused. Switch to an endgame phase to view gems, enchants, and consumables.")
        return
    end

    local selection = self:GetSelection()
    local filters = self.currentFilterPayload or self:BuildFilterPayload()
    local sections = self:GetCachedViewQuery("enhance", function()
        return BigBiSList:GetEnhancementRows(selection.class, selection.spec, selection.phase, filters)
    end)
    self.currentOwned = filters.ownedItems
    local rendered = false
    local model = self:NewListRenderModel()

    for _, section in ipairs(sections) do
        if #section.rows > 0 then
            rendered = true
            local sectionRows = self:SortDisplayRows(section.rows, "enhance")
            self:AddListSection(model, section.title, "enhance")
            for _, rowData in ipairs(sectionRows) do
                self:AddListRow(model, rowData, "enhance")
            end
            self:AddListGap(model)
        end
    end

    if not rendered then
        self:RenderEmpty("No gems, enchants, or consumables found for this class, spec, and phase.")
        return
    end

    self:RenderListModel(model)
end

function UI:RenderWishlistTab()
    local selection = self:GetSelection()
    local wishlist = BigBiSList:GetCharacterDB().wishlist or {}
    local filters = self.currentFilterPayload or self:BuildFilterPayload()
    self.currentOwned = filters.ownedItems
    if tableCount(wishlist) == 0 then self:RenderEmpty("No saved items yet. Select a star beside an item to save it here."); return end
    local rows = self:GetCachedViewQuery("wishlist", function()
        return BigBiSList:GetWishlistRows(wishlist, selection.class, selection.spec, selection.phase, filters)
    end)
    if #rows == 0 then self:RenderEmpty("No saved items match the current filters."); return end
    self:RenderGroupedRows(rows, "wishlist", self:GetViewState().groupBy or "none", "Wishlist")
end

function UI:BeginSettingsRender()
    self.settingsWidgetPools = self.settingsWidgetPools or {}
    self.settingsWidgetUse = {}
    for _, pool in pairs(self.settingsWidgetPools) do
        for _, frame in ipairs(pool) do
            frame:Hide()
        end
    end
end

function UI:AcquireSettingsWidget(kind, parent, createWidget)
    self.settingsWidgetPools = self.settingsWidgetPools or {}
    self.settingsWidgetUse = self.settingsWidgetUse or {}
    local pool = self.settingsWidgetPools[kind] or {}
    self.settingsWidgetPools[kind] = pool
    local index = (self.settingsWidgetUse[kind] or 0) + 1
    self.settingsWidgetUse[kind] = index
    local frame = pool[index]
    if not frame then
        frame = createWidget(parent)
        frame.__bigBisManaged = true
        pool[index] = frame
        self:CountPerformance("widgetsCreated")
    elseif frame.GetParent and frame:GetParent() ~= parent then
        frame:SetParent(parent)
    end
    frame:Show()
    frame:ClearAllPoints()
    return frame
end

function UI:CreateSettingsSectionHeader(parent, text, yOffset)
    local header = self:AcquireSettingsWidget("section", parent, function(widgetParent)
        local created = CreateFrame("Frame", nil, widgetParent)
        created:SetHeight(34)
        local line = created:CreateTexture(nil, "ARTWORK")
        line:SetColorTexture(0.55, 0.55, 0.58, 0.45)
        line:SetHeight(1)
        line:SetPoint("BOTTOMLEFT", created, "BOTTOMLEFT", 0, 6)
        line:SetPoint("BOTTOMRIGHT", created, "BOTTOMRIGHT", 0, 6)
        local label = created:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        label:SetPoint("TOPLEFT", created, "TOPLEFT", 8, -2)
        label:SetTextColor(1, 0.82, 0.28, 1)
        created.label = label
        return created
    end)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    header.label:SetText(text)
    return header, 34
end

function UI:CreateVirtualNote(parent, yOffset, text, frame, height)
    if not frame then
        frame = CreateFrame("Frame", nil, parent)
        local label = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        label:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -4)
        label:SetPoint("RIGHT", frame, "RIGHT", -8, 0)
        label:SetJustifyH("LEFT")
        label:SetWordWrap(true)
        label:SetTextColor(0.62, 0.62, 0.66, 1)
        frame.label = label
        frame.__bigBisManaged = true
        self:CountPerformance("widgetsCreated")
    end
    frame:SetParent(parent)
    frame:Show()
    frame:ClearAllPoints()
    height = height or 28
    frame:SetHeight(height)
    frame:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    frame:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    frame.label:SetText(text or "")
    return frame, height
end

function UI:CreateVirtualListAction(parent, yOffset, entry, button)
    local widgets = BigBiSList.Widgets
    if not button then
        button = widgets:CreateTextButton(parent, "", 1, entry.height, function(owner)
            if owner:IsVisible() and self:IsCurrentRenderFrame(owner) then owner.__bigBisBoundRenderEntry.activate() end
        end)
        button.label:ClearAllPoints()
        button.label:SetPoint("LEFT", button, "LEFT", 10, 0)
        button.label:SetJustifyH("LEFT")
        button.detail = widgets:CreateLabel(button, "", "GameFontHighlightSmall")
        button.detail:SetJustifyH("RIGHT")
        button.detail:SetPoint("RIGHT", button, "RIGHT", -25, 0)
        button.detail:SetTextColor(0.70, 0.77, 0.84)
        local chevron = button:CreateTexture(nil, "ARTWORK")
        chevron:SetSize(12, 12)
        chevron:SetPoint("RIGHT", button, "RIGHT", -8, 0)
        widgets:SetIcon(chevron, "chevronRight")
        widgets:BindTooltip(button, function(owner, tooltip)
            local bound = owner.__bigBisBoundRenderEntry
            if bound then
                tooltip:AddLine(bound.title, 1, 0.82, 0.28, true)
                if bound.detail then tooltip:AddLine(bound.detail, 0.70, 0.77, 0.84, true) end
            end
        end)
        button.__bigBisManaged = true
        self:CountPerformance("widgetsCreated")
    end
    button:SetParent(parent)
    button:ClearAllPoints()
    button:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    local width = self:GetTableViewportWidth(parent, 560)
    button:SetSize(width, entry.height)
    button.detail:SetText(entry.detail or "")
    local detailWidth = entry.detail and math.min(width * 0.48, math.ceil(button.detail:GetStringWidth()) + 4) or 0
    widgets:SetCellText(button.detail, entry.detail, 1, 14, detailWidth)
    widgets:SetCellText(button.label, entry.title, 1, 14, width - 45 - detailWidth)
    button:Show()
    return button
end

function UI:CreateSettingToggle(parent, yOffset, labelText, getValue, setValue, leftInset)
    local widgets = BigBiSList.Widgets
    local row = self:AcquireSettingsWidget("toggle", parent, function(widgetParent)
        local created = widgets:CreateItemRow(widgetParent, 34)
        local check = CreateFrame("CheckButton", nil, created, "UICheckButtonTemplate")
        check:SetSize(28, 28); check:SetPoint("LEFT", created, "LEFT", 8, 0)
        check:SetScript("OnClick", function(button)
            local owner = button.settingRow
            owner.setValue(button:GetChecked() == true or button:GetChecked() == 1)
            button:SetChecked(owner.getValue())
        end)
        check.settingRow = created
        created.label = widgets:CreateLabel(created, "", "GameFontNormal")
        created.label:SetPoint("LEFT", check, "RIGHT", 6, 0)
        created.label:SetPoint("RIGHT", created, "RIGHT", -12, 0)
        created:SetScript("OnMouseUp", function(owner, button)
            if button == "LeftButton" then owner.setValue(not owner.getValue()); owner.button:SetChecked(owner.getValue()) end
        end)
        created.button = check
        return created
    end)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", leftInset or 0, yOffset)
    row:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    row.label:SetText(labelText); row.getValue = getValue; row.setValue = setValue
    row.button:SetChecked(getValue())
    return row, 34
end

function UI:CreateSettingAction(parent, yOffset, labelText, buttonText, onClick, leftInset)
    local widgets = BigBiSList.Widgets
    local row = self:AcquireSettingsWidget("action", parent, function(widgetParent)
        local created = widgets:CreateItemRow(widgetParent, 34)
        local label = created:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        label:SetPoint("LEFT", created, "LEFT", 10, 0)
        label:SetPoint("RIGHT", created, "RIGHT", -144, 0)
        label:SetJustifyH("LEFT")
        label:SetWordWrap(false)
        local button = widgets:CreateTextButton(created, "", 118, 22, function(selfButton)
            local settingRow = selfButton.settingRow
            if settingRow and settingRow.onClick then
                settingRow.onClick()
            end
        end)
        button:SetPoint("RIGHT", created, "RIGHT", -10, 0)
        button.settingRow = created
        created.label = label
        created.button = button
        return created
    end)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", leftInset or 0, yOffset)
    row:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    row.label:SetText(labelText or "")
    row.button.label:SetText(buttonText or "")
    row.onClick = onClick
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
    local specs = BigBiSList:GetClassSpecIndex().specsByClass[className] or {}
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

    for _, classData in ipairs(BigBiSList:GetClassSpecIndex().classes or {}) do
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
        for _, spec in ipairs(BigBiSList:GetClassSpecIndex().specsByClass[className] or {}) do
            if spec.name then
                countSpec(spec.name, classFilters)
            end
        end
    else
        for _, classData in ipairs(BigBiSList:GetClassSpecIndex().classes or {}) do
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
    local header = self:AcquireSettingsWidget("action-header", parent, function(widgetParent)
        local created = CreateFrame("Frame", nil, widgetParent)
        created:SetHeight(headerHeight)
        local line = created:CreateTexture(nil, "ARTWORK")
        line:SetColorTexture(0.55, 0.55, 0.58, 0.45)
        line:SetHeight(1)
        line:SetPoint("BOTTOMLEFT", created, "BOTTOMLEFT", 0, 6)
        line:SetPoint("BOTTOMRIGHT", created, "BOTTOMRIGHT", 0, 6)

        local noneButton = widgets:CreateTextButton(created, "None", 54, 22, function(selfButton)
            local owner = selfButton.settingsHeader
            if owner and owner.onNone then owner.onNone() end
        end)
        noneButton:SetPoint("RIGHT", created, "RIGHT", -8, 4)
        noneButton.settingsHeader = created

        local allButton = widgets:CreateTextButton(created, "All", 54, 22, function(selfButton)
            local owner = selfButton.settingsHeader
            if owner and owner.onAll then owner.onAll() end
        end)
        allButton:SetPoint("RIGHT", noneButton, "LEFT", -6, 0)
        allButton.settingsHeader = created

        local countLabel = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        countLabel:SetPoint("RIGHT", allButton, "LEFT", -10, 0)
        countLabel:SetWidth(96)
        countLabel:SetJustifyH("RIGHT")
        countLabel:SetWordWrap(false)
        countLabel:SetTextColor(0.62, 0.62, 0.66, 1)

        local label = created:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        label:SetPoint("LEFT", created, "LEFT", 8, 4)
        label:SetPoint("RIGHT", countLabel, "LEFT", -8, 0)
        label:SetJustifyH("LEFT")
        label:SetWordWrap(false)
        label:SetTextColor(1, 0.82, 0.28, 1)

        created.label = label
        created.countLabel = countLabel
        created.allButton = allButton
        created.noneButton = noneButton
        return created
    end)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    header.label:SetText(titleText)
    header.countLabel:SetText(countText or "")
    header.onAll = onAll
    header.onNone = onNone

    return header, headerHeight
end

function UI:CreateSettingsClassHeader(parent, yOffset, className)
    local selected, total = self:GetTooltipSpecSelectionCount(className)
    local profile = accountDB().profile.tooltips
    profile.collapsedClasses = profile.collapsedClasses or {}
    local collapsed = profile.collapsedClasses[className] ~= false
    local header, height = self:CreateSettingsActionHeader(parent, yOffset, className, tostring(selected) .. "/" .. tostring(total), function()
        self:SetTooltipClassSpecFilters(className, true)
        self:Invalidate("presentation", "tooltip-specs")
        self:ScheduleRefresh(nil, "tooltip-specs")
    end, function()
        self:SetTooltipClassSpecFilters(className, false)
        self:Invalidate("presentation", "tooltip-specs")
        self:ScheduleRefresh(nil, "tooltip-specs")
    end)
    if not header.classToggle then
        local toggle = CreateFrame("Button", nil, header)
        toggle:SetPoint("TOPLEFT", header, "TOPLEFT", 0, 0)
        toggle:SetPoint("BOTTOMRIGHT", header.countLabel, "BOTTOMLEFT", -8, 0)
        toggle:SetScript("OnClick", function(selfButton)
            local owner = selfButton.settingsHeader
            local activeProfile = accountDB().profile.tooltips
            activeProfile.collapsedClasses = activeProfile.collapsedClasses or {}
            activeProfile.collapsedClasses[owner.className] = not owner.classCollapsed
            UI:Invalidate("presentation", "tooltip-specs-collapse")
            UI:ScheduleRefresh(nil, "tooltip-specs-collapse")
        end)
        toggle.settingsHeader = header
        header.classToggle = toggle
    end
    header.className = className
    header.classCollapsed = collapsed
    header.disclosure = header.disclosure or header:CreateTexture(nil, "OVERLAY")
    header.disclosure:SetSize(12,12)
    header.disclosure:SetPoint("LEFT", header, "LEFT", 0, 0)
    BigBiSList.Widgets:SetIcon(header.disclosure, collapsed and "chevronRight" or "chevronDown")
    header.label:SetPoint("LEFT", header, "LEFT", 20, 0)
    return header, height, collapsed
end

function UI:CreateTooltipSpecsHeader(parent, yOffset)
    local selected, total = self:GetTooltipSpecSelectionCount()
    return self:CreateSettingsActionHeader(parent, yOffset, "Tooltip Specs", tostring(selected) .. "/" .. tostring(total) .. " selected", function()
        self:SetAllTooltipSpecFilters(true)
        self:Invalidate("presentation", "tooltip-specs-all")
        self:ScheduleRefresh(nil, "tooltip-specs-all")
    end, function()
        self:SetAllTooltipSpecFilters(false)
        self:Invalidate("presentation", "tooltip-specs-none")
        self:ScheduleRefresh(nil, "tooltip-specs-none")
    end)
end

function UI:RenderSettingsTab()
    self:ReleaseRenderFrames(); self.renderModel = nil; self.hasRenderedContent = true
    self:SetStickyHeaderMode(nil)
    if self.contentListLayer then self.contentListLayer:Hide() end
    if self.emptyLabel then self.emptyLabel:Hide() end
    for _, button in ipairs(self.emptyActions or {}) do button:Hide() end
    local parent = self.contentStaticLayer or self.contentChild
    parent:Show(); self:BeginSettingsRender()
    self.settingsSection = self.settingsSection or "appearance"
    local nav = self:AcquireSettingsWidget("navigation", parent, function(host)
        local frame = CreateFrame("Frame", nil, host); frame.buttons = {}
        local sections = {{"appearance","Appearance"},{"tooltips","Tooltips"},{"hidden","Hidden Items"}}
        if BigBiSList.AcquisitionHighlights then sections[#sections + 1] = {"gearhighlights", "Gear Highlights"} end
        for index, option in ipairs(sections) do
            local key = option[1]
            local button = BigBiSList.Widgets:CreateTextButton(frame, option[2], 128, 28, function()
                self.settingsSection = key
                self.contentScroll:SetVerticalScroll(0)
                self:Invalidate("presentation", "settings-section"); self:ScheduleRefresh(nil, "settings-section")
            end)
            button:SetPoint("LEFT", frame, "LEFT", (index-1)*134, 0)
            frame.buttons[key] = button
        end
        return frame
    end)
    nav:SetPoint("TOPLEFT", parent, "TOPLEFT", 8, -4); nav:SetPoint("RIGHT", parent, "RIGHT", -8, 0); nav:SetHeight(32)
    for key, button in pairs(nav.buttons) do button:SetSelected(key == self.settingsSection) end
    local y = -48
    local profile = accountDB().profile
    local function toggle(label, getter, setter, inset)
        local _, height = self:CreateSettingToggle(parent, y, label, getter, setter, inset)
        y = y - height - 4
    end
    local function action(label, text, callback)
        local _, height = self:CreateSettingAction(parent, y, label, text, callback)
        y = y - height - 4
    end
    if self.settingsSection == "appearance" then
        toggle("Show minimap button", function() return not profile.minimap.hide end, function(value)
            profile.minimap.hide = not value; if BigBiSList.RefreshMinimapButton then BigBiSList:RefreshMinimapButton() end
        end)
        toggle("Lock window position", function() return profile.window.locked end, function(value) profile.window.locked = value end)
        action("List density", profile.window.density == "compact" and "Compact" or "Comfortable", function()
            profile.window.density = profile.window.density == "compact" and "comfortable" or "compact"
            self:Invalidate("presentation", "density"); self:ScheduleRefresh(nil, "density")
        end)
        action("Restore default window size, position, scale, and details", "Reset layout", function() self:ResetWindowLayout() end)
    elseif self.settingsSection == "tooltips" then
        BigBiSList:EnsureTooltipSpecFilters()
        local tooltipSettings = {
            {"Show Big BiS List info in item tooltips", "enabled"},
            {"Show selected spec first in tooltips", "selectedSpecFirst"},
        }
        if not BigBiSList.isForever then
            table.insert(tooltipSettings, 2, {"Compact tooltip rows by default", "compact"})
            tooltipSettings[#tooltipSettings + 1] = {"ALT expands tooltip matches", "showAllOnAlt"}
        end
        for _, option in ipairs(tooltipSettings) do
            local key = option[2]
            toggle(option[1], function() return profile.tooltips[key] end, function(value) profile.tooltips[key] = value end)
        end
        local _, height = self:CreateTooltipSpecsHeader(parent, y); y = y - height - 8
        for _, classData in ipairs(BigBiSList:GetClassSpecIndex().classes or {}) do
            local className = classData.name
            local _, h, collapsed = self:CreateSettingsClassHeader(parent, y, className); y = y - h
            if not collapsed then
                for _, spec in ipairs(classData.specs or {}) do
                    local specName = spec.name
                    toggle(specName, function() return profile.tooltips.specFilters[className][specName] end,
                        function(value) self:SetTooltipSpecFilter(className, specName, value) end, 16)
                end
            end
        end
    elseif self.settingsSection == "gearhighlights" and BigBiSList.AcquisitionHighlights then
        local highlights = BigBiSList.AcquisitionHighlights
        for _, setting in ipairs(highlights.settings) do
            local key = setting[1]
            toggle(setting[2], function() return profile.gearHighlights[key] end, function(value)
                profile.gearHighlights[key] = value
                highlights:ScheduleRefresh()
            end)
        end
    else
        local hidden = {}
        for key, value in pairs(BigBiSList:GetCharacterDB().ignoredItems or {}) do
            if value then
                local id = tonumber(key)
                local item = id and BigBiSList:GetItemData(id)
                hidden[#hidden+1] = {id=id, name=item and item.name or ("Item " .. key)}
            end
        end
        table.sort(hidden, function(a,b) return lower(a.name) < lower(b.name) end)
        if #hidden == 0 then
            local note = self:AcquireSettingsWidget("hidden-empty", parent, function(host)
                local frame = CreateFrame("Frame", nil, host)
                frame.label = BigBiSList.Widgets:CreateLabel(frame, "No hidden items.")
                frame.label:SetAllPoints(); return frame
            end)
            note:SetPoint("TOPLEFT", parent, "TOPLEFT", 12, y); note:SetSize(300, 28); y = y - 36
        else
            action(tostring(#hidden) .. " hidden items", "Restore All", function() self:RestoreAllHiddenItems() end)
            for _, item in ipairs(hidden) do
                local id = item.id
                action(item.name, "Restore", function() self:UnignoreItem(id) end)
            end
        end
    end
    self:SetContentHeight(y)
    self:ApplySettingsNavigation()
end

function UI:FindPlannerContext(itemId, detailData)
    local selection = self:GetSelection()
    local wantedSlot = detailData and detailData.slot
    local fallback
    for _, entry in ipairs((self.renderModel and self.renderModel.entries) or {}) do
        local row = entry.kind == "row" and entry.data or nil
        if row and row.item_id == itemId then
            if not fallback then
                fallback = row
            end
            if not wantedSlot or row.slot == wantedSlot then
                return row
            end
        end
    end
    if fallback then
        return fallback
    end

    if self:IsLevelingMode() and BigBiSList.GetItemBestLevelingUseForSpec then
        local level = BigBiSList.GetSelectedLevelingLevel and BigBiSList:GetSelectedLevelingLevel() or MAX_LEVELING_LEVEL
        return BigBiSList:GetItemBestLevelingUseForSpec(itemId, selection.class, selection.spec, level)
    end
    if BigBiSList.GetItemBestUseForSpec then
        return BigBiSList:GetItemBestUseForSpec(itemId, selection.class, selection.spec, selection.phase)
    end
    return detailData
end

function UI:BeginDetailsRender()
    self.detailsWidgetPools = self.detailsWidgetPools or {}
    self.detailsWidgetUse = {}
    for _, pool in pairs(self.detailsWidgetPools) do
        for _, frame in ipairs(pool) do
            frame:Hide()
        end
    end
end

function UI:AcquireDetailsWidget(kind, parent, createWidget)
    self.detailsWidgetPools = self.detailsWidgetPools or {}
    self.detailsWidgetUse = self.detailsWidgetUse or {}
    local pool = self.detailsWidgetPools[kind] or {}
    self.detailsWidgetPools[kind] = pool
    local index = (self.detailsWidgetUse[kind] or 0) + 1
    self.detailsWidgetUse[kind] = index
    local frame = pool[index]
    if not frame then
        frame = createWidget(parent)
        frame.__bigBisManaged = true
        pool[index] = frame
        self:CountPerformance("widgetsCreated")
    elseif frame:GetParent() ~= parent then
        frame:SetParent(parent)
    end
    frame:Show()
    frame:ClearAllPoints()
    return frame
end

function UI:CreateDetailsTitle(parent, text, r, g, b)
    local frame = self:AcquireDetailsWidget("title", parent, function(widgetParent)
        local created = CreateFrame("Frame", nil, widgetParent)
        local label = created:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        label:SetPoint("TOPLEFT", created, "TOPLEFT", 0, 0)
        label:SetJustifyH("LEFT")
        label:SetWordWrap(true)
        created.label = label
        return created
    end)
    frame:SetPoint("TOPLEFT", parent, "TOPLEFT", 8, -8)
    frame:SetPoint("RIGHT", parent, "RIGHT", -8, 0)

    local label = frame.label
    label:SetWidth(math.max(120, (parent:GetWidth() or DETAILS_WIDTH) - 16))
    label:SetText(text or "")
    label:SetTextColor(r or 0.9, g or 0.9, b or 0.9, 1)

    frame:SetHeight(math.max(24, label:GetStringHeight() or 16))
    frame.contentHeight = frame:GetHeight() + 8
    return frame
end

function UI:CreateDetailsText(parent, anchor, titleText, bodyText, bodyR, bodyG, bodyB)
    local block = self:AcquireDetailsWidget("text", parent, function(widgetParent)
        local created = CreateFrame("Frame", nil, widgetParent)
        local title = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        title:SetPoint("TOPLEFT", created, "TOPLEFT", 0, 0)
        title:SetJustifyH("LEFT")
        title:SetWordWrap(false)
        title:SetTextColor(1, 0.82, 0.28, 1)
        local body = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        body:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -3)
        body:SetJustifyH("LEFT")
        body:SetWordWrap(true)
        created.title = title
        created.body = body
        return created
    end)
    block:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -12)
    block:SetPoint("RIGHT", parent, "RIGHT", -8, 0)

    local width = math.max(120, (parent:GetWidth() or DETAILS_WIDTH) - 16)
    local title = block.title
    title:SetWidth(width)
    title:SetText(titleText)

    local body = block.body
    body:SetWidth(width)
    body:SetTextColor(bodyR or 0.76, bodyG or 0.76, bodyB or 0.80, 1)
    body:SetText(bodyText or "")

    local titleHeight = math.max(13, title:GetStringHeight() or 13)
    local bodyHeight = math.max(13, body:GetStringHeight() or 13)
    block:SetHeight(titleHeight + 5 + bodyHeight)
    block.contentHeight = block:GetHeight() + 12
    return block
end

function UI:IsDetailsSectionExpanded(sectionKey, defaultExpanded)
    local saved = self.expandedSellerSections and self.expandedSellerSections[sectionKey]
    if saved ~= nil then return saved end
    return defaultExpanded ~= false
end

function UI:CreateDetailsCollapsibleText(parent, anchor, sectionKey, titleText, bodyText, entryCount, defaultExpanded)
    local block = self:AcquireDetailsWidget("collapsible", parent, function(widgetParent)
        local created = CreateFrame("Button", nil, widgetParent)
        created:EnableMouse(true)
        local disclosure = created:CreateTexture(nil, "ARTWORK")
        disclosure:SetSize(12, 12)
        disclosure:SetPoint("TOPLEFT", created, "TOPLEFT", 0, 0)
        local title = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        title:SetPoint("TOPLEFT", created, "TOPLEFT", 18, 0)
        title:SetJustifyH("LEFT")
        title:SetWordWrap(false)
        title:SetTextColor(1, 0.82, 0.28, 1)
        local body = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        body:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -5)
        body:SetJustifyH("LEFT")
        body:SetWordWrap(true)
        body:SetTextColor(0.76, 0.76, 0.80, 1)
        created.title = title
        created.body = body
        created.disclosure = disclosure
        created:SetScript("OnEnter", function(selfBlock)
            selfBlock.title:SetTextColor(1, 0.9, 0.48, 1)
        end)
        created:SetScript("OnLeave", function(selfBlock)
            selfBlock.title:SetTextColor(1, 0.82, 0.28, 1)
        end)
        created:SetScript("OnClick", function(selfBlock)
            if not selfBlock.sectionKey then
                return
            end
            UI.expandedSellerSections = UI.expandedSellerSections or {}
            UI.expandedSellerSections[selfBlock.sectionKey] = not UI:IsDetailsSectionExpanded(selfBlock.sectionKey, selfBlock.defaultExpanded)
            UI.detailsRenderSignature = nil
            UI:RefreshDetails(UI.selectedItemId, UI.selectedItemData, UI.selectedItemMode)
        end)
        return created
    end)
    block:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -12)
    block:SetPoint("RIGHT", parent, "RIGHT", -8, 0)

    local width = math.max(120, (parent:GetWidth() or DETAILS_WIDTH) - 16)
    local count = tonumber(entryCount) or 0
    for _, label in ipairs(block.matrixLabels or {}) do label:Hide() end
    for _, mark in pairs(block.matrixMarks or {}) do mark:Hide() end
    for _, target in pairs(block.matrixTargets or {}) do target:Hide() end
    local expanded = self:IsDetailsSectionExpanded(sectionKey, defaultExpanded)
    block.sectionKey, block.defaultExpanded = sectionKey, defaultExpanded
    block.title:SetWidth(width - 18)
    block.title:SetText(titleText .. (count > 0 and (" (" .. tostring(count) .. ")") or ""))
    BigBiSList.Widgets:SetIcon(block.disclosure, expanded and "chevronDown" or "chevronRight")
    block.body:SetWidth(width - 18)
    block.body:SetText(bodyText or "")

    local titleHeight = math.max(13, block.title:GetStringHeight() or 13)
    if expanded then
        block.body:Show()
        local bodyHeight = math.max(13, block.body:GetStringHeight() or 13)
        block:SetHeight(titleHeight + 7 + bodyHeight)
    else
        block.body:Hide()
        block:SetHeight(titleHeight)
    end
    block.contentHeight = block:GetHeight() + 12
    return block
end

function UI:RefreshDetailsHeader(entityId, entityType, itemId, data, mode, titleText, r, g, b)
    if not self.detailsHeader then return end
    local widgets = BigBiSList.Widgets
    local header = self:AcquireDetailsWidget("identity", self.detailsHeader, function(parent)
        local created = CreateFrame("Frame", nil, parent)
        local iconButton = CreateFrame("Button", nil, created)
        iconButton:SetSize(40, 40)
        iconButton:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        iconButton:SetPoint("LEFT", created, "LEFT", 0, 0)
        iconButton.icon = iconButton:CreateTexture(nil, "ARTWORK")
        iconButton.icon:SetAllPoints()
        iconButton.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        local name = created:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        name:SetJustifyH("LEFT")
        name:SetJustifyV("TOP")
        name:SetWordWrap(true)
        name.maxLines = 2
        name.lineHeight = 14
        local meta = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        meta:SetPoint("TOPLEFT", name, "BOTTOMLEFT", 0, -2)
        meta:SetJustifyH("LEFT")
        meta:SetWordWrap(false)
        meta:SetTextColor(0.68, 0.72, 0.78, 1)
        local menu = widgets:CreateUtilityButton(created, "menu", 28, function(button)
            if button.itemId then UI:ShowItemActionMenu(button.data, button.mode, button) end
        end, "Item actions")
        menu:SetPoint("RIGHT", created, "RIGHT", -30, 0)
        local star = widgets:CreateUtilityButton(created, "starOutline", 28, function(button)
            if not button.itemId then return end
            local character = BigBiSList:GetCharacterDB()
            if character.wishlist[tostring(button.itemId)] then
                UI:RemoveWishlist(button.itemId)
            else
                UI:AddWishlist(button.itemId)
            end
        end, "Add to wishlist")
        star:SetPoint("RIGHT", menu, "LEFT", -2, 0)
        created.iconButton, created.name, created.meta = iconButton, name, meta
        created.star, created.menu = star, menu
        return created
    end)
    header:SetPoint("TOPLEFT", self.detailsHeader, "TOPLEFT", 8, -8)
    header:SetPoint("BOTTOMRIGHT", self.detailsHeader, "BOTTOMRIGHT", -8, 8)
    local width = math.max(160, (self.detailsHeader:GetWidth() or DETAILS_WIDTH) - 16)
    local metadata = trim(data and self:GetRowSlotDisplay(data))
    if metadata == "—" then metadata = "" end
    local hasMetadata = metadata ~= ""
    local textWidth = math.max(1, width - 48 - (itemId and 88 or 30) - 8)
    header.name:ClearAllPoints()
    header.name:SetPoint("TOPLEFT", header, "LEFT", 48, hasMetadata and 21 or 14)
    header.name:SetWidth(textWidth)
    header.name:SetHeight(28)
    header.name:SetTextColor(r or 0.9, g or 0.9, b or 0.9, 1)
    header.name:SetText(titleText or "Details")
    widgets:SetCellText(header.meta, metadata, 1, 12, textWidth)
    header.meta:SetShown(hasMetadata)
    if entityType == "spell" then
        self:SetSpellButton(header.iconButton, entityId, header.name, titleText, data, mode)
    elseif itemId then
        self:SetItemButton(header.iconButton, itemId, header.name, titleText, data and data.quality, data, mode)
    end
    widgets:SetCellText(header.name, header.name.fullText or titleText or "Details", 2, 14, textWidth)
    for _, button in ipairs({ header.star, header.menu }) do
        button.itemId, button.data, button.mode = itemId, data or { item_id = itemId }, mode
        if itemId then button:Show() else button:Hide() end
    end
    if itemId then
        local wishlisted = not not BigBiSList:GetCharacterDB().wishlist[tostring(itemId)]
        widgets:SetIcon(header.star.icon, wishlisted and "starFilled" or "starOutline")
        if header.star.SetSelected then header.star:SetSelected(wishlisted) end
        widgets:BindTooltip(header.star, wishlisted and "Remove from wishlist" or "Add to wishlist")
    end
    self.detailsIdentity = header
end

function UI:CreateDetailsFields(parent, anchor, titleText, fields)
    local block = self:AcquireDetailsWidget("fields", parent, function(widgetParent)
        local created = CreateFrame("Frame", nil, widgetParent)
        created.title = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        created.title:SetPoint("TOPLEFT", created, "TOPLEFT", 0, 0)
        created.title:SetTextColor(1, 0.82, 0.28, 1)
        created.fields = {}
        return created
    end)
    block:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -12)
    block:SetPoint("RIGHT", parent, "RIGHT", -8, 0)
    block.title:SetText(titleText)
    local width = math.max(120, (parent:GetWidth() or DETAILS_WIDTH) - 16)
    local labelWidth = math.min(82, width * 0.3)
    local y = 23
    for _, pair in ipairs(block.fields) do pair.label:Hide(); pair.value:Hide() end
    for index, field in ipairs(fields or {}) do
        local pair = block.fields[index]
        if not pair then
            pair = { label = block:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall"), value = block:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall") }
            block.fields[index] = pair
        end
        for _, label in ipairs({ pair.label, pair.value }) do
            label:ClearAllPoints()
            label:SetJustifyH("LEFT")
            label:SetWordWrap(true)
            label:Show()
        end
        pair.label:SetPoint("TOPLEFT", block, "TOPLEFT", 0, -y)
        pair.label:SetWidth(labelWidth)
        pair.label:SetTextColor(0.62, 0.66, 0.72, 1)
        pair.label:SetText(field.label)
        pair.value:SetPoint("TOPLEFT", block, "TOPLEFT", labelWidth + 8, -y)
        pair.value:SetWidth(width - labelWidth - 8)
        pair.value:SetTextColor(0.82, 0.85, 0.9, 1)
        pair.value:SetText(field.value)
        y = y + math.max(14, pair.label:GetStringHeight() or 14, pair.value:GetStringHeight() or 14) + 7
    end
    block:SetHeight(y)
    block.contentHeight = y + 12
    return block
end

function UI:GetDetailsPhaseRankings(itemId, data)
    local selection = self:GetItemContext()
    local summary = BigBiSList.GetWishlistExpansionSummary
        and BigBiSList:GetWishlistExpansionSummary(itemId, selection.class, selection.spec, selection.phase)
    return (summary and summary.relevant_spec_rankings) or (data and (data.relevant_spec_rankings or data.spec_rankings)) or {}
end

function UI:GetDetailsEquipmentComparison(data)
    if not data or not data.item_id or not data.slot or data.leveling or self:IsLevelingMode() or not BigBiSList.GetEquipmentComparisonContexts then return {} end
    local selection = self:GetItemContext()
    local lines = {}
    if self.slotComparison and data.comparison then
        local prefix = BigBiSList.isForever and "Compare with " or "Compared with "
        appendText(lines, prefix .. self:GetComparisonReferenceLabel(self.slotComparison.reference))
        appendText(lines, data.comparison.explanation)
        for _, pair in ipairs(data.comparison.evidence or {}) do
            local candidate, reference = pair.candidate or {}, pair.reference or {}
            local candidateRating = BigBiSList:GetGuideRatingDisplay(candidate.original_rating) or "Unrated"
            local comparedRating = BigBiSList:GetGuideRatingDisplay(reference.original_rating) or "Unrated"
            appendText(lines, candidateRating .. " / " .. comparedRating)
            appendText(lines, type(candidate.conditions) == "table" and table.concat(candidate.conditions, ", ") or candidate.conditions)
            appendText(lines, candidate.source_url)
        end
        return lines
    end
    local contexts = BigBiSList:GetEquipmentComparisonContexts(selection.class, selection.spec, selection.phase, self.currentOwned, data.slot)
    for _, context in ipairs(contexts) do
        local position = context.slot or data.slot
        if context.occupancy == "blocked" then
            appendText(lines, position .. ": occupied by a two-handed weapon; compare the full weapon setup.")
        elseif context.occupancy == "empty" then
            appendText(lines, position .. ": Empty")
        elseif context.item_id then
            local comparison = BigBiSList:CompareRecommendationItems(data.item_id, context.item_id, selection.class, selection.spec, selection.phase, data.slot, context, data)
            appendText(lines, position .. ": " .. (context.name or ("Item " .. context.item_id)))
            appendText(lines, comparison.explanation)
        else
            appendText(lines, position .. ": equipment information is not available.")
        end
    end
    for _, alternative in ipairs(data.owned_alternatives or {}) do
        local item = BigBiSList.GetItemData and BigBiSList:GetItemData(alternative.item_id)
        local name = (UI:GetItemInfo(alternative.item_id)) or (item and item.name) or ("Item " .. alternative.item_id)
        appendText(lines, "Already owned: " .. name .. " (" .. ownershipStateLabel(alternative.state) .. ")")
        appendText(lines, alternative.comparison and alternative.comparison.explanation)
    end
    return lines
end

function UI:CreateDetailsHistory(parent, anchor, data, mode)
    local history = self:GetRowRecommendationHistory(data)
    if not history then return nil end
    local selection = self:GetItemContext()
    local live = BigBiSList:GetCurrentPhaseKey()
    local lines = {}
    for _, cell in ipairs(history.phase_cells or {}) do
        local prefix = cell.phase_label or BigBiSList:GetPhaseDisplayName(cell.phase)
        if cell.phase == selection.phase then prefix = prefix .. " (Target)" end
        if cell.phase == live then prefix = prefix .. " (Live)" end
        appendText(lines, prefix .. ": " .. cell.label)
    end
    appendText(lines, "Not listed means no recommendation is recorded; it does not mean the item becomes obsolete.")
    local key = "item:" .. data.item_id .. ":history:" .. selection.class .. ":" .. selection.spec .. ":" .. tostring(data.slot or "")
    return self:CreateDetailsCollapsibleText(parent, anchor, key, selection.spec .. " recommendations", table.concat(lines, "\n"), nil, false)
end

function UI:RefreshDetailsActions(data, mode)
    if not self.detailsActionStrip then return end
    local statRank = mode == "gear" and data and data.stat_rank ~= nil
    local visible = not self.slotComparison and self.OpenSlotComparison and data and data.item_id and data.slot
        and not data.spell_id and (statRank or (not self:IsLevelingMode() and mode ~= "leveling" and mode ~= "enhance"))
        and not data.enhancement_kind
    visible = visible and true or false
    local button = self.detailsCompareButton
    button.boundData, button.boundMode = visible and data or nil, visible and mode or nil
    button.statRank = statRank
    self.detailsActionStrip:SetShown(visible)
    if self.detailsActionsVisible ~= visible then
        self.detailsActionsVisible = visible
        self.detailsScroll:ClearAllPoints()
        self.detailsScroll:SetPoint("TOPLEFT", visible and self.detailsActionStrip or self.detailsHeader, "BOTTOMLEFT", 8, -4)
        self.detailsScroll:SetPoint("BOTTOMRIGHT", self.details, "BOTTOMRIGHT", -28, 8)
        self.detailsRenderSignature = nil
    end
end

function UI:CreateDetailsPhaseMatrix(parent, anchor, itemId, data, defaultExpanded)
    local rankings = self:GetDetailsPhaseRankings(itemId, data)
    if #rankings == 0 then return nil end
    local sectionKey = "item:" .. tostring(itemId) .. ":phase-matrix"
    local block = self:CreateDetailsCollapsibleText(parent, anchor, sectionKey, "Phase rankings", "", #rankings, defaultExpanded)
    block.matrixLabels = block.matrixLabels or {}
    block.matrixMarks = block.matrixMarks or {}
    block.matrixTargets = block.matrixTargets or {}
    for _, label in ipairs(block.matrixLabels) do label:Hide() end
    for _, mark in pairs(block.matrixMarks) do mark:Hide() end
    if not self:IsDetailsSectionExpanded(sectionKey, defaultExpanded) then return block end
    block.body:Hide()
    local selection = self:GetItemContext()
    local livePhase = BigBiSList.GetCurrentPhaseKey and BigBiSList:GetCurrentPhaseKey()
    local phases = BigBiSList:GetPhaseOrder()
    local allUses = BigBiSList.GetItemUses and BigBiSList:GetItemUses(itemId, selection.phase) or {}
    local width = math.max(180, (parent:GetWidth() or DETAILS_WIDTH) - 16)
    local specWidth = math.min(92, width * 0.3)
    local cellWidth = (width - specWidth) / math.max(1, #phases)
    local labelIndex = 0
    local function cell(text, x, y, cellSize, selected, tooltipText)
        labelIndex = labelIndex + 1
        local label = block.matrixLabels[labelIndex]
        if not label then label = block:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall"); block.matrixLabels[labelIndex] = label end
        label:ClearAllPoints()
        label:SetPoint("TOPLEFT", block, "TOPLEFT", x, -y)
        label:SetWidth(cellSize)
        label:SetJustifyH(x == 0 and "LEFT" or "CENTER")
        label:SetWordWrap(false)
        label:SetTextColor(selected and 1 or 0.76, selected and 0.84 or 0.8, selected and 0.4 or 0.88, 1)
        label:SetText(text)
        BigBiSList.Widgets:SetCellText(label, text, 1, 13, cellSize)
        label:Show()
        if tooltipText and tooltipText ~= "" then
            local target = block.matrixTargets[labelIndex]
            if not target then target = CreateFrame("Button", nil, block); block.matrixTargets[labelIndex] = target end
            target:ClearAllPoints()
            target:SetPoint("TOPLEFT", block, "TOPLEFT", x, -y + 2)
            target:SetSize(cellSize, 20)
            BigBiSList.Widgets:BindTooltip(target, tooltipText)
            target:Show()
        end
    end
    local phaseLabels = { PR = "Pre", T4 = "T4", T5 = "T5", T6 = "T6", ZA = "ZA", SWP = "SWP" }
    local matrixHeight = 25 + (#rankings + 1) * 22
    cell("Spec", 0, 25, specWidth, false)
    for index, phase in ipairs(phases) do
        local x = specWidth + (index - 1) * cellWidth
        cell(phaseLabels[phase] or phase, x, 25, cellWidth, phase == selection.phase)
        if phase == selection.phase or phase == livePhase then
            local mark = block.matrixMarks[index]
            if not mark then mark = block:CreateTexture(nil, "BACKGROUND"); block.matrixMarks[index] = mark end
            mark:ClearAllPoints()
            mark:SetPoint("TOPLEFT", block, "TOPLEFT", x + 1, -22)
            mark:SetSize(cellWidth - 2, phase == selection.phase and (matrixHeight - 22) or 2)
            mark:SetColorTexture(phase == selection.phase and 1 or 0.3, phase == selection.phase and 0.72 or 0.75, phase == selection.phase and 0.22 or 1, phase == selection.phase and 0.12 or 0.9)
            mark:Show()
        end
        if phase == livePhase and phase == selection.phase then
            local mark = block.matrixMarks[#phases + 1]
            if not mark then mark = block:CreateTexture(nil, "BACKGROUND"); block.matrixMarks[#phases + 1] = mark end
            mark:ClearAllPoints(); mark:SetPoint("TOPLEFT", block, "TOPLEFT", x + 1, -22)
            mark:SetSize(cellWidth - 2, 2); mark:SetColorTexture(0.3, 0.75, 1, 0.9); mark:Show()
        end
    end
    for rowIndex, ranking in ipairs(rankings) do
        cell(ranking.spec or ranking.spec_name or "Spec", 0, 25 + rowIndex * 22, specWidth, ranking.spec == selection.spec, ranking.spec or ranking.spec_name)
        local history = BigBiSList.GetRecommendationHistory and BigBiSList:GetRecommendationHistory(itemId, selection.class, ranking.spec, selection.phase, data and data.slot)
        for phaseIndex, phase in ipairs(phases) do
            local phaseCell = (ranking.phases or ranking.phase_rankings or {})[phase]
            local label = type(phaseCell) == "table" and (phaseCell.short_label or phaseCell.label) or phaseCell
            if history then label = history.phases[phase].label end
            local shortLabels = { ["Best in slot"] = "BiS", Alternative = "Alt", Optional = "Opt", ["Best (Alt)"] = "Alt" }
            local useLines, seen = {}, {}
            for _, use in ipairs(allUses) do
                if use.class == selection.class and use.spec == ranking.spec and use.phase == phase then
                    local useLabel = displayRankInfo(use)
                    local line = useLabel .. (use.slot and (" · " .. use.slot) or "")
                    if trim(use.context) ~= "" then line = line .. "\n" .. use.context end
                    if trim(use.source_note) ~= "" then line = line .. "\n" .. use.source_note end
                    if not seen[line] then table.insert(useLines, line); seen[line] = true end
                end
            end
            local tooltipText = (ranking.spec or "Spec") .. " · " .. BigBiSList:GetPhaseDisplayName(phase)
                .. "\n" .. (#useLines > 0 and table.concat(useLines, "\n\n") or (label or "Not ranked"))
            local display = shortLabels[label] or label or "—"
            if BigBiSList.isForever and label then
                display = label == "Best in slot" and "BiS" or BigBiSList:GetGuideRatingDisplay(label)
            end
            cell(display, specWidth + (phaseIndex - 1) * cellWidth, 25 + rowIndex * 22, cellWidth, false, tooltipText)
        end
    end
    cell("Gold: selected phase  ·  Blue line: live phase", 0, matrixHeight + 5, width, false)
    cell("Guide ratings depend on their tier and setup.", 0, matrixHeight + 21, width, false)
    block:SetHeight(matrixHeight + 38)
    block.contentHeight = block:GetHeight() + 12
    return block
end

function UI:FormatDetailsRoutes(options, context)
    local blocks = {}
    for _, option in ipairs(options or {}) do
        local hasCards = context and self.GetDetailsSourceItems and #self:GetDetailsSourceItems(option, context) > 0
        local lines = self:GetSellerDetailLines(option, hasCards) or {}
        if #lines == 0 then appendText(lines, self:GetAccessOptionDisplayText(option)) end
        if #(option.requirements or {}) > 0 then appendText(lines, self:FormatRequirements(option)) end
        if #lines > 0 then table.insert(blocks, table.concat(lines, "\n")) end
    end
    return table.concat(blocks, "\n\n")
end

function UI:BuildPhaseUseText(itemId)
    local selection = self:GetSelection()
    local uses = BigBiSList:GetItemUses(itemId, selection.phase)
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
        return "No expansion ranking for this setup."
    end

    return table.concat(parts, "\n")
end

function UI:ApplyDetailsScrollGeometry(contentHeight, viewportHeight)
    local scroll = self.detailsScroll
    local height = math.max(contentHeight or 0, viewportHeight)
    self.detailsContent:SetHeight(height)
    if scroll.UpdateScrollChildRect then scroll:UpdateScrollChildRect() end
    if scroll.GetVerticalScroll and scroll.SetVerticalScroll then
        local offset = tonumber((scroll:GetVerticalScroll())) or 0
        local clamped = math.max(0, math.min(offset, height - viewportHeight))
        if offset ~= clamped then scroll:SetVerticalScroll(clamped) end
    end
end

function UI:RefreshDetailsLayout()
    local request = self.pendingDetailsRequest
    if request then
        return self:RefreshDetails(request.itemId, request.data, request.mode)
    end
    return self:RefreshDetails(self.selectedItemId, self.selectedItemData, self.selectedItemMode)
end

function UI:RequestDetailsTierRange(data, mode)
    if not data.stat_rank_scope or (mode ~= "leveling" and mode ~= "comparison") then return nil end
    local detailsVersion = (self.domainVersions or {}).details
    local comparison = self.slotComparison
    return BigBiSList.ForeverGearRating:RequestTierRange(data.stat_rank, data.stat_rank_scope, {
        owner = self.details,
        isCurrent = function()
            return self.selectedItemData == data and self.selectedItemMode == mode and self.slotComparison == comparison
                and (self.domainVersions or {}).details == detailsVersion
                and self:IsInspectorVisible() and self.details:IsVisible()
        end,
        onReady = function()
            self:RefreshDetails(self.selectedItemId, data, mode)
        end,
    })
end

function UI:RefreshDetails(itemId, detailData, detailMode)
    if not self:IsInspectorVisible() or not self.detailsContent then
        return
    end
    self:RefreshDetailsActions(detailData, detailMode)

    local content = self.detailsContent
    self.pendingDetailsRequest = { itemId = itemId, data = detailData, mode = detailMode }
    local detailsWidth = self.detailsScroll and self.detailsScroll:GetWidth() or 0
    local detailsHeight = self.detailsScroll and self.detailsScroll:GetHeight() or 0
    -- Native frame geometry can settle after Show(), before its size event arrives.
    -- Keep the request pending rather than measuring and caching a zero-size body.
    if not detailsWidth or detailsWidth <= 0 or not detailsHeight or detailsHeight <= 0 then
        return
    end
    content:SetWidth(detailsWidth)
    local versions = self.domainVersions or {}
    local tierRange = detailData and self:RequestDetailsTierRange(detailData, detailMode)
    local signature = table.concat({
        tostring(itemId or "none"),
        tostring(detailMode or ""),
        tostring(detailData or ""),
        tostring(self:GetItemContext().class), tostring(self:GetItemContext().spec), tostring(self:GetItemContext().phase),
        tostring(versions.details or 0),
        tostring(math.floor((detailsWidth or 0) + 0.5)),
        tierRange and tostring(tierRange.lastLevel) or "",
    }, ":")
    if self.detailsRenderSignature == signature then
        self:ApplyDetailsScrollGeometry(self.detailsContentHeight, detailsHeight)
        self.pendingDetailsRequest = nil
        return
    end
    -- Only completed renders may be reused. A failure after the fixed header has
    -- been bound must leave the next layout pass free to rebuild the body.
    self.detailsRenderSignature = nil
    self:CountPerformance("detailsBuilds")
    if self.dirtyDomains then
        self.dirtyDomains.details = true
    end
    self:BeginDetailsRender()
    local function finish(contentHeight)
        self:ApplyDetailsScrollGeometry(contentHeight, detailsHeight)
        self.detailsContentHeight = contentHeight
        self.detailsRenderSignature = signature
        self.pendingDetailsRequest = nil
        if self.dirtyDomains then self.dirtyDomains.details = nil end
    end

    if not itemId then
        local emptyFrame = self:AcquireDetailsWidget("empty", content, function(widgetParent)
            local created = CreateFrame("Frame", nil, widgetParent)
            local label = created:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
            label:SetPoint("TOPLEFT", created, "TOPLEFT", 0, 0)
            label:SetPoint("RIGHT", created, "RIGHT", 0, 0)
            label:SetJustifyH("LEFT")
            label:SetWordWrap(true)
            label:SetTextColor(0.72, 0.72, 0.76, 1)
            created.label = label
            return created
        end)
        emptyFrame:SetPoint("TOPLEFT", content, "TOPLEFT", 8, -8)
        emptyFrame:SetPoint("RIGHT", content, "RIGHT", -8, 0)
        emptyFrame:SetHeight(72)
        local label = emptyFrame.label
        label:SetText("Select an item to see sources, phase usefulness, and wishlist actions.")
        finish(80)
        return
    end

    local entityType = detailData and (detailData.entity_type or (detailData.spell_id and "spell")) or self.selectedEntityType or "item"
    local entityId = detailData and (detailData.entity_id or detailData.spell_id or detailData.item_id) or itemId
    local detailItemId = entityType == "item" and ((detailData and detailData.item_id) or entityId) or nil

    self.selectedItemId = entityId
    self.selectedItemData = detailData
    self.selectedItemMode = detailMode
    self.selectedEntityType = entityType
    local index = BigBiSList:GetDataIndex()
    local item = detailItemId and index.itemsById[detailItemId] or nil
    local plannerContext = not self.slotComparison and detailItemId
        and (detailData and detailData.priority and detailData or self:FindPlannerContext(detailItemId, detailData)) or nil

    local titleQualityItem = item or (detailData and detailData.quality and { quality = detailData.quality }) or nil
    local r, g, b = itemQualityColor(titleQualityItem)
    if entityType == "spell" then
        r, g, b = 1, 0.82, 0.28
    end
    local titleText = (detailData and detailData.name) or (item and item.name) or ((entityType == "spell" and "Spell " or "Item ") .. tostring(entityId))
    self:RefreshDetailsHeader(entityId, entityType, detailItemId, detailData or item, detailMode, titleText, r, g, b)
    local anchor = self:AcquireDetailsWidget("start", content, function(parent) return CreateFrame("Frame", nil, parent) end)
    anchor:SetPoint("TOPLEFT", content, "TOPLEFT", 8, 4)
    anchor:SetSize(1, 1)
    local contentHeight = 5

    local recommendationLines = {}
    if not detailData or not detailData.stat_rank or detailData.bestUse or detailData.guide_note then
        appendText(recommendationLines, self:GetRowRecommendationText(detailData or plannerContext, detailMode))
    end
    if detailData and detailData.slot then
        local detailPhase = detailData.phase or (detailData.bestUse and detailData.bestUse.phase)
        local selectedPhase = detailPhase and BigBiSList:GetPhaseDisplayName(detailPhase) or BigBiSList:GetPhaseDisplayName(self:GetItemContext().phase)
        appendText(recommendationLines, selectedPhase .. " - " .. detailData.slot)
    end

    local ownershipState, ownershipText
    if detailData and (detailData.enhancement_kind == "gem" or detailData.enhancement_kind == "enchant") then
        local appliedSummary = self:GetEnhancementAppliedSummary(detailData)
        appendText(recommendationLines, "Applied: " .. appliedSummary.label)
        for _, line in ipairs(appliedSummary.lines or {}) do
            appendText(recommendationLines, line)
        end
        if appliedSummary.state == "missing" and appliedSummary.detail and appliedSummary.detail ~= "" then
            appendText(recommendationLines, appliedSummary.detail)
        end
    elseif detailItemId then
        ownershipState = detailData and detailData.stat_identity and detailData.owned_state
            or BigBiSList.isForever and detailData and detailData.variant_id and self:GetRowOwnershipState(detailData)
            or self:GetOwnershipState(detailItemId, detailData and detailData.item_ids)
        ownershipText = ownershipStateLabel(ownershipState)
        if ownershipState == "bank" and self.currentOwned and self.currentOwned.bankUpdatedAt and self.currentOwned.bankUpdatedAt ~= "" then
            ownershipText = ownershipText .. " - bank cache " .. self.currentOwned.bankUpdatedAt
        elseif ownershipState == "missing" and not BigBiSList.isForever and self.currentOwned and not self.currentOwned.bankScanned then
            ownershipText = ownershipText .. " - open your bank once to include banked items"
        end
        appendText(recommendationLines, ownershipText)
    elseif detailData and detailData.ownership_state then
        ownershipText = detailData.ownership_label or ownershipStateLabel(detailData.ownership_state)
        if detailData.ownership_detail and detailData.ownership_detail ~= "" then
            ownershipText = ownershipText .. " - " .. detailData.ownership_detail
        end
        appendText(recommendationLines, ownershipText)
    end
    appendText(recommendationLines, upgradeComparisonText(detailData or plannerContext))
    local scoringLabel = detailData and detailData.scoring_label
    if scoringLabel then
        appendText(recommendationLines, scoringLabel)
        if detailData.scoring_basis == "active_build" then
            appendText(recommendationLines, "Talent evidence from Blizzard client data via Wago Tools and EG Link (CC BY 4.0).")
        end
    end
    if detailItemId and detailMode ~= "leveling" and detailMode ~= "enhance" and not (detailData and detailData.stat_rank) then
        for _, line in ipairs(self:GetDetailsEquipmentComparison(detailData)) do appendText(recommendationLines, line) end
    end

    local accessData = detailData or item or {}
    local requirementData = (accessData and accessData.requirements and #accessData.requirements > 0) and accessData or item
    local displayOption, accessEvaluation, sellerGroups = self:GetSelectedAcquisitionRoute(accessData)
    local optionEvaluation = accessEvaluation.optionEvaluation
    local option = optionEvaluation and optionEvaluation.option
    if (detailMode == "leveling" or (detailData and detailData.leveling)) and detailData then
        appendText(recommendationLines, detailData.level_value_text)
        appendText(recommendationLines, detailData.guide_note)
        appendText(recommendationLines, detailData.section)
        if BigBiSList.ForeverScoring and not detailData.stat_rank then
            local reference = self:GetLevelingReferenceSlot() and (self.slotContextFrame.reference or {})
            appendText(recommendationLines, BigBiSList:GetLevelingEquipmentComparison(detailData, reference))
        end
    end
    local function appendRecommendation()
        local placement = detailData and detailData.stat_rank
        if placement then
            local service = BigBiSList.ForeverGearRating
            local lines = service:DescriptionLines(placement)
            lines[2] = "Default spec weights · " .. lines[2]
            if tierRange then appendText(lines, "Tier range · " .. service:TierRangeLabel(tierRange)) end
            if placement.rank and placement.total > 1 then appendText(lines, string.format("%.1f pts", placement.score)) end
            local comparison = self.slotComparison
            if comparison and comparison.statRank then
                appendText(lines, "Compare with " .. self:GetComparisonReferenceLabel(comparison.reference))
                appendText(lines, BigBiSList:GetGuideStatComparison(detailData, self.currentOwned, comparison.reference.slotKey))
            elseif detailMode == "leveling" or detailMode == "phase" then
                appendText(lines, BigBiSList:GetGuideStatComparison(detailData, self.currentOwned, self:GetLevelingReferenceSlot()))
            end
            local effects = placement.item and placement.item.effects
            if effects and #effects > 0 then
                appendText(lines, "Effects outside the stat score")
                for _, effect in ipairs(effects) do appendText(lines, effect) end
            end
            anchor = self:CreateDetailsText(content, anchor, "Stat rank", table.concat(lines, "\n"), 0.82, 0.88, 0.94)
            contentHeight = contentHeight + anchor.contentHeight
        end
        anchor = self:CreateDetailsText(content, anchor, "Recommendation", table.concat(recommendationLines, "\n"), 0.82, 0.86, 0.92)
        contentHeight = contentHeight + anchor.contentHeight
    end
    local owned = ownershipState == "equipped" or ownershipState == "bag" or ownershipState == "bank"
    if owned then appendRecommendation() end

    local sourceContext = { phase = self.slotComparison and self.slotComparison.phase or self:GetEffectivePhaseKey(), filters = self:GetItemContextFilters() }
    if BigBiSList.isForever and detailMode == "leveling" and self.currentFilterPayload then
        sourceContext.filters = self.currentFilterPayload
    end
    local sourceItems = self.CreateDetailsSourceItems and BigBiSList.GetAccessOptionSourceItems
        and BigBiSList:GetAccessOptionSourceItems(displayOption, sourceContext) or {}
    local routeFields = {}
    local fields = BigBiSList.GetAccessOptionDetailFields and BigBiSList:GetAccessOptionDetailFields(displayOption) or {}
    for _, field in ipairs(fields or {}) do
        local value = trim(field.value)
        if value ~= "" and not (#sourceItems > 0 and (field.key == "token_source" or field.key == "quest_starter_source")) then
            local note = trim(field.note)
            if note ~= "" and lower(note) ~= lower(value) then value = value .. "\n" .. note end
            table.insert(routeFields, { label = field.label or field.key or "Source", value = value })
        end
    end
    if #routeFields == 0 and displayOption then
        table.insert(routeFields, { label = "Source", value = self:GetAccessOptionDisplayText(displayOption) or displayOption.label or "Source" })
        if trim(displayOption.zone) ~= "" then table.insert(routeFields, { label = "Location", value = displayOption.zone }) end
        if trim(displayOption.cost_summary) ~= "" then table.insert(routeFields, { label = "Cost", value = displayOption.cost_summary }) end
    elseif #routeFields == 0 then
        table.insert(routeFields, { label = "Source", value = accessData.source_summary or "Source details are not recorded." })
    end
    if optionEvaluation and optionEvaluation.status == "ready" and accessData.ready_access_detail and accessData.ready_access_detail ~= "" then
        table.insert(routeFields, { label = "Route note", value = self:GetAccessHelpText(optionEvaluation, accessData) })
    end
    if accessEvaluation.future and accessData.acquisition_display and accessData.acquisition_display.acquisition_phase then
        table.insert(routeFields, { label = "Available", value = BigBiSList:GetPhaseDisplayName(accessData.acquisition_display.acquisition_phase) })
    end
    local prerequisitesText
    if optionEvaluation and optionEvaluation.option and #(optionEvaluation.option.requirements or {}) > 0 then
        prerequisitesText = self:FormatAccessOptionRequirements(optionEvaluation)
    elseif not option and requirementData and #(requirementData.requirements or {}) > 0 then
        prerequisitesText = self:FormatRequirements(requirementData)
    end
    if prerequisitesText and prerequisitesText ~= "" then
        table.insert(routeFields, { label = "Requires", value = prerequisitesText })
    end
    if accessEvaluation.status ~= "ready" and accessEvaluation.status ~= "ready_alternate" then
        table.insert(routeFields, { label = "Access", value = self:GetAccessBadgeLabel(accessEvaluation.status, accessData) })
    end
    anchor = self:CreateDetailsFields(content, anchor, "Selected route", routeFields)
    contentHeight = contentHeight + anchor.contentHeight
    if self.CreateAcquisitionSteps then
        local acquisitionHeight
        anchor, acquisitionHeight = self:CreateAcquisitionSteps(content, anchor, displayOption, accessEvaluation.status)
        contentHeight = contentHeight + acquisitionHeight
    end
    if self.CreateDetailsSourceItems then
        local cards = self:CreateDetailsSourceItems(content, anchor, displayOption,
            tostring(entityType) .. ":" .. tostring(entityId) .. ":selected-source", sourceContext)
        if cards then anchor = cards; contentHeight = contentHeight + cards.contentHeight end
    end

    if not owned then appendRecommendation() end
    if detailItemId and detailMode ~= "leveling" and detailMode ~= "enhance" then
        local history = self:CreateDetailsHistory(content, anchor, detailData, detailMode)
        if history then anchor = history; contentHeight = contentHeight + history.contentHeight end
    end

    local sellerSectionPrefix = tostring(entityType) .. ":" .. tostring(entityId) .. ":"
    if #sellerGroups.alternatives > 0 then
        if self.CreateDetailsSourceRoutes then
            local routes = {}
            for _, seller in ipairs(sellerGroups.alternatives) do
                routes[#routes + 1] = { option = seller, text = self:FormatDetailsRoutes({ seller }, sourceContext) }
            end
            anchor = self:CreateDetailsSourceRoutes(content, anchor, sellerSectionPrefix .. "other-sellers", "Other sellers", routes, sourceContext, false)
        else
            anchor = self:CreateDetailsCollapsibleText(content, anchor, sellerSectionPrefix .. "other-sellers", "Other sellers",
                self:FormatDetailsRoutes(sellerGroups.alternatives), #sellerGroups.alternatives, false)
        end
        contentHeight = contentHeight + anchor.contentHeight
    end
    if #sellerGroups.reported > 0 then
        if self.CreateDetailsSourceRoutes then
            local routes = {}
            for _, seller in ipairs(sellerGroups.reported) do
                routes[#routes + 1] = { option = seller, text = self:FormatDetailsRoutes({ seller }, sourceContext) }
            end
            anchor = self:CreateDetailsSourceRoutes(content, anchor, sellerSectionPrefix .. "reported-sellers", "Additional reported sellers", routes, sourceContext, false)
        else
            anchor = self:CreateDetailsCollapsibleText(content, anchor, sellerSectionPrefix .. "reported-sellers", "Additional reported sellers",
                self:FormatDetailsRoutes(sellerGroups.reported), #sellerGroups.reported, false)
        end
        contentHeight = contentHeight + anchor.contentHeight
    end

    local alternativeLines = {}
    local alternativeEntries = {}
    for _, alternative in ipairs(accessEvaluation.options or {}) do
        if alternative.option ~= option and not isSellerAccessOption(alternative.option) then
            local hasCards = self.GetDetailsSourceItems and #self:GetDetailsSourceItems(alternative.option, sourceContext) > 0
            local lines = self:GetSellerDetailLines(alternative.option, hasCards)
            local route = lines and table.concat(lines, "\n") or self:GetAccessOptionDisplayText(alternative.option)
            if route and route ~= "" then
                if #(alternative.option.requirements or {}) > 0 then
                    route = route .. "\n" .. self:FormatAccessOptionRequirements(alternative)
                end
                table.insert(alternativeLines, route)
                table.insert(alternativeEntries, { option = alternative.option, text = route })
            end
        end
    end
    if #alternativeLines > 0 then
        if self.CreateDetailsSourceRoutes then
            anchor = self:CreateDetailsSourceRoutes(content, anchor, sellerSectionPrefix .. "other-routes", "Other routes", alternativeEntries, sourceContext, false)
        else
            anchor = self:CreateDetailsCollapsibleText(content, anchor, sellerSectionPrefix .. "other-routes", "Other routes", table.concat(alternativeLines, "\n\n"), #alternativeLines, false)
        end
        contentHeight = contentHeight + anchor.contentHeight
    end

    local timelineLines = {}
    if plannerContext and plannerContext.priority then
        local score = tostring(plannerContext.priority or 0) .. "/100"
        appendText(timelineLines, "Pursuit priority: " .. score .. " (not item strength)")
        appendText(timelineLines, plannerContext.reasons and table.concat(plannerContext.reasons, "\n") or "No planner explanation available.")
    end

    if detailMode ~= "leveling" then
        local availabilityPhase = (detailData and detailData.acquisition_phase)
            or (plannerContext and plannerContext.acquisition_phase)
            or (item and item.acquisition_phase)
        if availabilityPhase then
            appendText(timelineLines, "Available in " .. BigBiSList:GetPhaseDisplayName(availabilityPhase))
        end

    end
    if #timelineLines > 0 then
        anchor = self:CreateDetailsCollapsibleText(content, anchor, sellerSectionPrefix .. "expansion-value", "Expansion value", table.concat(timelineLines, "\n"), nil, false)
        contentHeight = contentHeight + anchor.contentHeight
    end
    if detailItemId and detailMode ~= "leveling" then
        local matrix = self:CreateDetailsPhaseMatrix(content, anchor, detailItemId, detailData, false)
        if matrix then anchor = matrix; contentHeight = contentHeight + matrix.contentHeight end
    end

    local noteLines = {}
    appendText(noteLines, detailData and detailData.source_note)
    appendText(noteLines, detailData and (detailData.notes or detailData.note))
    appendText(noteLines, item and (item.notes or item.note))
    appendText(noteLines, detailData and detailData.source_url)
    if BigBiSList.GetSourceAttributionLines then
        for _, credit in ipairs(BigBiSList:GetSourceAttributionLines(displayOption and displayOption.source)) do appendText(noteLines, credit) end
    end
    if displayOption and displayOption.source_url ~= (detailData and detailData.source_url) then
        appendText(noteLines, displayOption.source_url)
    end
    if #noteLines > 0 then
        anchor = self:CreateDetailsCollapsibleText(content, anchor, sellerSectionPrefix .. "provenance", "Notes & provenance", table.concat(noteLines, "\n"), nil, false)
        contentHeight = contentHeight + anchor.contentHeight
    end

    contentHeight = contentHeight + 16
    finish(contentHeight)
end

function UI:RefreshControls()
    local selection = self:GetSelection()
    local filters = self:GetFilters()
    local leveling = self:IsLevelingMode()
    local settings = selection.tab == "Settings"
    for _, control in ipairs({ self.classDropdown, self.specDropdown, self.phaseSelector, self.sortDropdown, self.groupDropdown }) do
        if control and control.Refresh then control:Refresh() end
    end
    if self.scenarioDropdown then
        local rating = BigBiSList.ForeverGearRating
        self.scenarioDropdown:SetShown(#rating:GetScenarios(self:GetGearScenarioSelection()) > 1)
        self.scenarioDropdown:Refresh()
    end
    if self.searchBox and self.searchBox:GetText() ~= (filters.search or "") then self.searchBox:SetText(filters.search or "") end
    if self.searchPlaceholder then
        self.searchPlaceholder:SetText(selection.tab == "Enhance" and "Search enhancements" or "Search items or sources")
        self.searchPlaceholder:SetShown((filters.search or "") == "")
        self.searchClearButton:SetShown((filters.search or "") ~= "")
    end
    local r, g, b = classColor(selection.class)
    if self.accentBar then self.accentBar:SetColorTexture(r, g, b, 0.8) end
    self.summaryText:SetText(settings and "Settings" or "")
    self.settingsBackButton:SetShown(settings)
    self.settingsButton:SetSelected(settings)
    self.contextBar:SetShown(not settings)
    self:LayoutContextControls()
    if settings then self.contextBar:SetHeight(1) end
    self.tabBar:SetShown(not settings)
    self.tabBar:SetHeight(settings and 1 or 30)
    self.endgameModeButton:SetSelected(not leveling)
    self.levelingModeButton:SetSelected(leveling)
    self.levelingModeButton:SetShown(BigBiSList.supportsLeveling)
    self.endgameModeButton:SetShown(BigBiSList.supportsLeveling)
    self.phaseSelector:SetShown(not leveling)
    if self.targetTierLabel then self.targetTierLabel:SetShown(not leveling) end
    self.levelControlContainer:SetShown(leveling)
    local level = leveling and BigBiSList:GetSelectedLevelingLevel() or nil
    local character = BigBiSList:GetCharacterDB()
    local manualLevel = character.leveling and character.leveling.manualLevel
    if leveling then
        self.levelControlLabel:SetText("Level")
        if not self.levelInput:HasFocus() then self.levelInput:SetText(tostring(level)) end
        self.levelDownButton:SetEnabled(level > 1)
        self.levelUpButton:SetEnabled(level < MAX_LEVELING_LEVEL)
        self.levelCurrentButton:SetShown(manualLevel == true)
    end
    local detected = BigBiSList:GetDetectedPlayerSelection()
    local differs = detected and (detected.class ~= selection.class or detected.spec ~= selection.spec)
    self.useCharacterButton:Show()
    self.useCharacterButton:SetEnabled(BigBiSList.classSpecAutoSelectionActive == false or differs == true or (leveling and manualLevel == true))
    local previous
    for _, button in pairs(self.tabButtons) do button:Hide() end
    for _, name in ipairs(self:GetActiveTabNames()) do
        local button = self.tabButtons[name]
        if button then
            button:Show(); button:ClearAllPoints()
            button:SetPoint("LEFT", previous or self.tabBar, previous and "RIGHT" or "LEFT", previous and 6 or 0, 0)
            button:SetSelected(name == selection.tab)
            button.tabUnderline:SetShown(name == selection.tab)
            previous = button
        end
    end
    if self.filterToggleButton then
        local count = self:GetActiveFilterCount()
        self.filterToggleButton.label:SetText(count > 0 and ("Filters (" .. count .. ")") or "Filters")
        self.filterToggleButton:SetSelected(count > 0)
    end
    if not self.transientStatusMessage and self.statusText then self.statusText:SetText(self:GetBankStatusText()) end
    if self.undoButton then self.undoButton:SetShown(self.undoAction ~= nil) end
    self:ApplyBodyLayout()
end

function UI:SetStatusMessage(message, undoAction)
    self.transientStatusMessage = message
    self.undoAction = undoAction
    if undoAction then
        undoAction.expiresAt = (GetTime and GetTime() or 0) + 8
        undoAction.message = message
    end
    if self.undoButton then
        if undoAction then self.undoButton:Show() else self.undoButton:Hide() end
    end
    if self.statusText then
        self.statusText:SetText(message or "")
        self.statusText:SetTextColor(0.72, 0.88, 0.76, 1)
    end
    self.statusMessageSerial = (self.statusMessageSerial or 0) + 1
    local serial = self.statusMessageSerial
    if C_Timer and C_Timer.After then
        C_Timer.After(undoAction and 8 or 3, function()
            if self.statusMessageSerial == serial then
                self.transientStatusMessage = nil
                self.undoAction = nil
                if self.undoButton then self.undoButton:Hide() end
                if self.statusText then
                    self.statusText:SetTextColor(0.62, 0.62, 0.66, 1)
                    self.statusText:SetText(self.GetBankStatusText and self:GetBankStatusText() or "")
                end
            end
        end)
    end
end

function UI:ScheduleRefresh(delay, reason)
    if not self.frame then
        return
    end
    delay = tonumber(delay) or 0

    if delay > 0 then
        self.refreshDebounceSerial = (self.refreshDebounceSerial or 0) + 1
        local serial = self.refreshDebounceSerial
        local function finishDebounce()
            if serial == self.refreshDebounceSerial then
                self:ScheduleRefresh(0, reason or "debounced")
            end
        end
        if C_Timer and C_Timer.After then
            C_Timer.After(delay, finishDebounce)
        else
            finishDebounce()
        end
        return
    end

    -- Any immediate state change supersedes a pending trailing search refresh.
    self.refreshDebounceSerial = (self.refreshDebounceSerial or 0) + 1

    if self.refreshInProgress then
        self.refreshPending = true
        self.pendingRefreshReason = reason or self.pendingRefreshReason
        return
    end
    if self.refreshScheduled then
        return
    end

    self.refreshScheduled = true
    self:CountPerformance("scheduledRefreshes", 1, reason or "unspecified")
    local function refreshNow()
        self.refreshScheduled = false
        if self.frame and self.frame:IsShown() then
            self:Refresh(reason)
        end
    end

    if C_Timer and C_Timer.After then
        C_Timer.After(0, refreshNow)
    else
        refreshNow()
    end
end

function UI:ScheduleLayoutRefresh(reason)
    if not self.frame or self.layoutScheduled then
        return
    end
    if self.refreshInProgress or self.refreshScheduled then
        self.layoutPending = true
        return
    end

    self.layoutScheduled = true
    local function layoutNow()
        self.layoutScheduled = false
        if self.frame and self.frame:IsShown() then
            self:RefreshLayout(reason)
        end
    end
    if C_Timer and C_Timer.After then
        C_Timer.After(0, layoutNow)
    else
        layoutNow()
    end
end

function UI:RefreshLayout(reason)
    if not self.frame or not self.frame:IsShown() then
        return
    end
    self:CountPerformance("layoutPasses", 1, reason or "layout")
    self:ApplyBodyLayout()
    self:LayoutContextControls()
    if self.IsSlotComparisonOpen and self:IsSlotComparisonOpen() then
        self:RenderSlotComparison()
    elseif self.renderModel then
        self:SetStickyHeaderMode(self.stickyHeaderMode)
        self:UpdateVirtualList(true)
    end
    self:RefreshDetailsLayout()
    if self.dirtyDomains then
        self.dirtyDomains.layout = nil
    end
end

function UI:Refresh(reason)
    if not self.frame then
        return
    end
    if self.refreshInProgress then
        self.refreshPending = true
        return
    end

    self.refreshInProgress = true
    self:CountPerformance("executedRefreshes", 1, reason or self.lastInvalidationReason or "refresh")
    local ok, refreshError = xpcall(function()
        local dirtyAtStart = self.dirtyDomains or {}
        self.dirtyDomains = {}
        self:ValidateSelection()
        local tabName = normalizeTabName(self:GetSelection().tab)
        if tabName ~= "Settings" and not self.currentFilterPayload then
            self:BuildFilterPayload()
        end
        self:RefreshControls()

        if self.IsSlotComparisonOpen and self:IsSlotComparisonOpen() then
            self:RenderSlotComparison()
        elseif tabName == "Equipped" or tabName == "Builds" then
            self:RenderGearTab()
        elseif tabName == "Upgrades" then
            self:RenderPlannerTab()
        elseif tabName == "Enhance" then
            self:RenderEnhanceTab()
        elseif tabName == "Wishlist" then
            self:RenderWishlistTab()
        elseif tabName == "Settings" then
            self:RenderSettingsTab()
        elseif tabName == "Gear Guide" then
            self:RenderLevelingTab()
        elseif tabName == "By Slot" then
            self:RenderPhaseTab()
        else
            self:RenderPlannerTab()
        end

        if self:IsInspectorVisible() and (dirtyAtStart.details or self.selectedItemId) then
            self:RefreshDetails(self.selectedItemId, self.selectedItemData, self.selectedItemMode)
        end
    end, function(message)
        return tostring(message)
    end)
    self.refreshInProgress = false
    if not ok then
        self.refreshPending = false
        self.layoutPending = false
        self.pendingRefreshReason = nil
        self:Invalidate("query", "refresh-error")
        error(refreshError, 0)
    end

    local dirtyAfterRefresh = self.dirtyDomains or {}
    local needsLayout = self.layoutPending or dirtyAfterRefresh.layout
    local needsDataRefresh = self.refreshPending
        or dirtyAfterRefresh.ownership
        or dirtyAfterRefresh.access
        or dirtyAfterRefresh.query
        or dirtyAfterRefresh.availability
        or dirtyAfterRefresh.details
        or dirtyAfterRefresh.controls
        or dirtyAfterRefresh.presentation
    if needsLayout then
        self.layoutPending = false
        self:ScheduleLayoutRefresh("post-refresh")
    end
    if needsDataRefresh then
        local pendingReason = self.pendingRefreshReason or "post-refresh"
        self.refreshPending = false
        self.pendingRefreshReason = nil
        self:ScheduleRefresh(0, pendingReason)
    end
end

function UI:RunPerformanceSmoke()
    self.performanceSmokeSerial = (self.performanceSmokeSerial or 0) + 1
    local serial = self.performanceSmokeSerial
    self:ResetPerformanceStats()
    local startMemory = collectgarbage and collectgarbage("count") or 0
    local startTime = debugprofilestop and debugprofilestop() or 0

    if not self.frame or not self.frame:IsShown() then
        self:Open()
    end

    local function write(message)
        local text = "Big BiS List perf: " .. tostring(message)
        if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then
            DEFAULT_CHAT_FRAME:AddMessage(text)
        elseif print then
            print(text)
        end
    end

    if not (C_Timer and C_Timer.After) then
        local stats = self:GetPerformanceStats()
        write("timers unavailable; refreshes=" .. tostring(stats.executedRefreshes) .. ", realized=" .. tostring(stats.realizedEntries))
        return
    end

    write("warming for 0.5s, then sampling 10s idle")
    C_Timer.After(0.5, function()
        if serial ~= UI.performanceSmokeSerial then
            return
        end
        local warm = UI:GetPerformanceStats()
        local baseline = {
            refreshes = warm.executedRefreshes,
            layouts = warm.layoutPasses,
            ownership = warm.ownershipBuilds,
            access = warm.accessBuilds,
            availability = warm.availabilityBuilds,
            queries = warm.queryBuilds,
        }
        C_Timer.After(10, function()
            if serial ~= UI.performanceSmokeSerial then
                return
            end
            local stats = UI:GetPerformanceStats()
            local endMemory = collectgarbage and collectgarbage("count") or startMemory
            local elapsed = debugprofilestop and (debugprofilestop() - startTime) or 10500
            write(table.concat({
                "idle refreshes=" .. tostring(stats.executedRefreshes - baseline.refreshes),
                "layouts=" .. tostring(stats.layoutPasses - baseline.layouts),
                "data builds=" .. tostring((stats.ownershipBuilds - baseline.ownership) + (stats.accessBuilds - baseline.access) + (stats.availabilityBuilds - baseline.availability) + (stats.queryBuilds - baseline.queries)),
                "model rows=" .. tostring(stats.modelRows),
                "realized=" .. tostring(stats.realizedEntries),
                "widgets=" .. tostring(stats.widgetsCreated),
                "item loads=" .. tostring(stats.itemLoadRequests),
                "memory delta=" .. string.format("%.1f KB", endMemory - startMemory),
                "elapsed=" .. string.format("%.0f ms", elapsed),
            }, ", "))
        end)
    end)
end

function UI:CreateHeader(frame)
    local widgets = BigBiSList.Widgets
    self.accentBar = frame:CreateTexture(nil, "ARTWORK")
    self.accentBar:SetPoint("TOPLEFT", frame, "TOPLEFT", 1, -1)
    self.accentBar:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -1, -1)
    self.accentBar:SetHeight(2)
    local bar = CreateFrame("Frame", nil, frame)
    bar:SetHeight(32)
    bar:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, -2)
    bar:SetPoint("TOPRIGHT", frame, "TOPRIGHT", 0, -2)
    bar:EnableMouse(true)
    bar:RegisterForDrag("LeftButton")
    bar:SetScript("OnDragStart", function()
        if not accountDB().profile.window.locked then frame:StartMoving() end
    end)
    bar:SetScript("OnDragStop", function() frame:StopMovingOrSizing(); self:SaveWindow() end)
    local title = widgets:CreateLabel(bar, BigBiSList.displayName, "GameFontNormal")
    title:SetPoint("LEFT", bar, "LEFT", 14, 0)
    self.summaryText = widgets:CreateLabel(bar, "", "GameFontNormalSmall")
    self.summaryText:SetPoint("LEFT", title, "RIGHT", 18, 0)
    self.settingsButton = widgets:CreateUtilityButton(bar, "settings", 28, function() self:OpenSettings() end, "Settings")
    self.settingsButton:SetPoint("RIGHT", bar, "RIGHT", -36, 0)
    self.settingsBackButton = widgets:CreateTextButton(bar, "Back to gear", 110, 28, function() self:ReturnFromSettings() end)
    self.settingsBackButton:SetPoint("RIGHT", self.settingsButton, "LEFT", -8, 0)
    self.settingsBackButton:Hide()
    local close = widgets:CreateUtilityButton(bar, "clear", 28, function() BigBiSList:CloseMainFrame() end, "Close")
    close:SetPoint("RIGHT", bar, "RIGHT", -5, 0)
    self.titleBar = bar
end

function UI:CreateContextBar(frame)
    local widgets = BigBiSList.Widgets
    local bar = CreateFrame("Frame", nil, frame)
    bar:SetHeight(CONTEXT_BAR_HEIGHT)
    bar:SetPoint("TOPLEFT", self.titleBar, "BOTTOMLEFT", 12, -2)
    bar:SetPoint("TOPRIGHT", self.titleBar, "BOTTOMRIGHT", -12, -2)
    self.classDropdown = widgets:CreateDropdown("BigBiSListClassDropdown", bar, 112,
        function() return self:GetSelection().class or "Class" end,
        function() return self:GetClassDropdownItems() end, function(value) self:SetClass(value) end)
    self.classDropdown:SetPoint("LEFT", bar, "LEFT", -16, -2)
    self.specDropdown = widgets:CreateDropdown("BigBiSListSpecDropdown", bar, 130,
        function() return self:GetSelection().spec or "Spec" end,
        function() return self:GetSpecDropdownItems() end, function(value) self:SetSpec(value) end)
    self.specDropdown:SetPoint("LEFT", self.classDropdown, "RIGHT", -22, 0)
    self.endgameModeButton = widgets:CreateTextButton(bar, "Endgame", 78, 28, function() self:SetContentMode("endgame") end)
    self.endgameModeButton:SetPoint("LEFT", self.specDropdown, "RIGHT", 0, 2)
    self.levelingModeButton = widgets:CreateTextButton(bar, "Leveling", 78, 28, function() self:SetContentMode("leveling") end)
    self.levelingModeButton:SetPoint("LEFT", self.endgameModeButton, "RIGHT", 0, 0)
    self.useCharacterButton = widgets:CreateTextButton(bar, "Current Spec", 108, 28, function() self:UseMyCharacter() end)
    widgets:BindTooltip(self.useCharacterButton, "Return to your character's current class, specialization, and level.")
    local rating = BigBiSList.isForever and BigBiSList.ForeverGearRating
    if rating then
        self.scenarioDropdown = widgets:CreateDropdown("BigBiSListScenarioDropdown", bar, 102,
            function() return rating:ScenarioLabel(rating:GetScenario(self:GetGearScenarioSelection())) end,
            function()
                local class, spec, phase, level = self:GetGearScenarioSelection()
                local selected = rating:GetScenario(class, spec, phase, level)
                local options = {}
                for _, scenario in ipairs(rating:GetScenarios(class, spec, phase, level)) do
                    options[#options + 1] = { value = scenario, text = rating:ScenarioLabel(scenario), checked = scenario == selected }
                end
                return options
            end,
            function(value) self:SetGearScenario(value) end)
        widgets:BindTooltip(self.scenarioDropdown, "Choose the content used to rank gear.")
        self.scenarioDropdown:Hide()
    end
    self.contextBar = bar
end

function UI:CreatePhaseBar(frame)
    local widgets = BigBiSList.Widgets
    local host = CreateFrame("Frame", nil, self.contextBar)
    host:SetPoint("LEFT", self.levelingModeButton, "RIGHT", 10, 0)
    host:SetSize(280, 28)
    self.phaseBar = host
    self.phaseButtons = {}
    local widths = { PR = 68, T4 = 54, T5 = 54, T6 = 54, ZA = 68, SWP = 60 }
    local options = {}
    for _, phaseKey in ipairs(BigBiSList:GetPhaseOrder()) do
        local phase = phaseKey
        options[#options + 1] = {
            value = phase,
            text = phase == "SWP" and "Sunwell" or BigBiSList:GetPhaseDisplayName(phase),
            width = widths[phase] or 68,
            tooltip = function()
                local lines = { BigBiSList:GetPhaseDisplayName(phase) }
                if phase == "PR" then lines[#lines + 1] = "Pre-Raid recommendations follow live content." end
                if phase == self:GetSelection().phase then lines[#lines + 1] = "Selected for browsing." end
                if phase == BigBiSList:GetCurrentPhaseKey() then lines[#lines + 1] = "Live content." end
                return table.concat(lines, "\n")
            end,
        }
    end
    self.phaseSelector = widgets:CreateSegmentedControl(host, options, function(value) self:SetPhase(value) end)
    self.phaseSelector:SetPoint("TOPLEFT", host, "TOPLEFT", 0, 0)
    self.targetTierLabel = widgets:CreateLabel(host, "Target tier", "GameFontNormalSmall")
    self.targetTierLabel:SetPoint("BOTTOMLEFT", self.phaseSelector, "TOPLEFT", 0, 2)
    self.targetTierLabel:SetHeight(12)
    self.targetTierLabel:SetTextColor(0.62, 0.62, 0.66)
    for _, button in ipairs(self.phaseSelector.buttons) do
        button.liveCaption = button.caption
        self.phaseButtons[button.value] = button
    end
    self.phaseSelector.Refresh = function(control)
        control = control or self.phaseSelector
        control:SetSelectedValue(self:GetSelection().phase)
        local livePhase = BigBiSList:GetCurrentPhaseKey()
        for _, button in ipairs(control.buttons) do
            control:SetCaption(button.value, button.value == livePhase and "Live" or nil)
        end
    end
    self.phaseSelector:Refresh()
    local level = CreateFrame("Frame", nil, host)
    level:SetAllPoints()
    self.levelControlContainer = level
    self.levelControlLabel = widgets:CreateLabel(level, "Level", "GameFontNormalSmall")
    self.levelControlLabel:SetPoint("LEFT", level, "LEFT", 0, 0)
    self.levelDownButton = widgets:CreateUtilityButton(level, "chevronLeft", 28, function()
        self:SetLevelingLevel(BigBiSList:GetSelectedLevelingLevel() - 1)
    end, "Previous level")
    self.levelDownButton:SetPoint("LEFT", self.levelControlLabel, "RIGHT", 8, 0)
    self.levelInput = CreateFrame("EditBox", nil, level, "InputBoxTemplate")
    self.levelInput:SetSize(32, 24)
    self.levelInput:SetPoint("LEFT", self.levelDownButton, "RIGHT", 8, 0)
    self.levelInput:SetAutoFocus(false)
    self.levelInput:SetNumeric(true)
    self.levelInput:SetMaxLetters(2)
    self.levelInput:SetScript("OnEnterPressed", function(input)
        self:SetLevelingLevel(tonumber(input:GetText()) or BigBiSList:GetSelectedLevelingLevel())
        input:ClearFocus()
    end)
    self.levelInput:SetScript("OnEscapePressed", function(input)
        input:SetText(tostring(BigBiSList:GetSelectedLevelingLevel())); input:ClearFocus()
    end)
    self.levelInput:SetScript("OnEditFocusLost", function(input)
        local value = tonumber(input:GetText())
        if value and value ~= BigBiSList:GetSelectedLevelingLevel() then self:SetLevelingLevel(value) end
    end)
    self.levelUpButton = widgets:CreateUtilityButton(level, "chevronRight", 28, function()
        self:SetLevelingLevel(BigBiSList:GetSelectedLevelingLevel() + 1)
    end, "Next level")
    self.levelUpButton:SetPoint("LEFT", self.levelInput, "RIGHT", 6, 0)
    self.levelCurrentButton = widgets:CreateTextButton(level, "Current Level", 100, 28, function() self:UseMyCharacter() end)
    self.levelCurrentButton:SetPoint("LEFT", self.levelUpButton, "RIGHT", 6, 0)
end

function UI:LayoutContextControls()
    if not self.contextBar or not self.phaseBar then return end
    local bar = self.contextBar
    local leveling = self:IsLevelingMode()
    local phaseWidth = self.phaseSelector:Layout()
    self.phaseBar:SetSize(leveling and 280 or phaseWidth, leveling and 28 or 40)
    local controls = { self.classDropdown, self.specDropdown, self.useCharacterButton }
    if self.scenarioDropdown and self.scenarioDropdown:IsShown() then controls[#controls + 1] = self.scenarioDropdown end
    local x = 0
    for _, control in ipairs(controls) do
        control:ClearAllPoints()
        control:SetPoint("TOPLEFT", bar, "TOPLEFT", x, -(CONTEXT_BAR_HEIGHT - control:GetHeight()) / 2)
        x = x + control:GetWidth() + 8
    end
    local modeWidth = BigBiSList.supportsLeveling and (self.endgameModeButton:GetWidth() + self.levelingModeButton:GetWidth()) or 0
    local remainingWidth = modeWidth + 10 + self.phaseBar:GetWidth()
    local wrapped = x + 4 + remainingWidth > (bar:GetWidth() or MIN_WIDTH - 24)
    local headingHeight = leveling and 0 or 14
    if not wrapped and headingHeight > 0 then
        x = 0
        for _, control in ipairs(controls) do
            control:ClearAllPoints()
            control:SetPoint("TOPLEFT", bar, "TOPLEFT", x, -headingHeight - (CONTEXT_BAR_HEIGHT - control:GetHeight()) / 2)
            x = x + control:GetWidth() + 8
        end
    end
    local rowTop = (wrapped and CONTEXT_BAR_HEIGHT + 2 or 0) + headingHeight
    local modeX = wrapped and 0 or x + 4
    self.endgameModeButton:ClearAllPoints()
    self.endgameModeButton:SetPoint("TOPLEFT", bar, "TOPLEFT", modeX, -rowTop - 3)
    self.levelingModeButton:ClearAllPoints()
    self.levelingModeButton:SetPoint("LEFT", self.endgameModeButton, "RIGHT", 0, 0)
    self.phaseBar:ClearAllPoints()
    if not BigBiSList.supportsLeveling then
        self.phaseBar:SetPoint("TOPLEFT", bar, "TOPLEFT", modeX, -rowTop - 3)
    else
        self.phaseBar:SetPoint("TOPLEFT", self.levelingModeButton, "TOPRIGHT", 10, 0)
    end
    local height = wrapped and CONTEXT_BAR_HEIGHT * 2 + 2 or CONTEXT_BAR_HEIGHT
    bar:SetHeight(self:GetSelection().tab == "Settings" and 1 or height + (leveling and 0 or 12) + headingHeight)
end

function UI:CreateTabBar(frame)
    local widgets = BigBiSList.Widgets
    local bar = CreateFrame("Frame", nil, frame)
    bar:SetPoint("TOPLEFT", self.contextBar, "BOTTOMLEFT", 0, -4)
    bar:SetPoint("TOPRIGHT", self.contextBar, "BOTTOMRIGHT", 0, -4)
    bar:SetHeight(30)
    self.tabBar = bar
    self.tabButtons = {}
    for _, tabName in ipairs(TAB_NAMES) do
        if tabName ~= "Settings" then
            local name = tabName
            local button = widgets:CreateTextButton(bar, TAB_DISPLAY_LABELS[name] or name, name == "Enhance" and 124 or 104, 28,
                function() self:SetTab(name) end)
            button.tabUnderline = button:CreateTexture(nil, "OVERLAY")
            button.tabUnderline:SetColorTexture(0.88, 0.72, 0.24, 1)
            button.tabUnderline:SetPoint("BOTTOMLEFT", button, "BOTTOMLEFT", 8, 0)
            button.tabUnderline:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -8, 0)
            button.tabUnderline:SetHeight(2)
            self.tabButtons[name] = button
        end
    end
end

function UI:SetFilterDrawerOpen(open)
    self.filterDrawerOpen = open and true or false
    if self.filterToggleButton then
        self.filterToggleButton:SetSelected(self:GetActiveFilterCount() > 0)
    end
    if not self.filterDrawerOpen and self.filterDrawer then self.filterDrawer:Hide() end
    self.bodyLayoutSignature = nil
    if not self.filterDrawerOpen and BigBiSList.Widgets.CloseDropdownMenus then
        BigBiSList.Widgets:CloseDropdownMenus()
    end
    self:Invalidate("layout", "filter-drawer")
    self:ScheduleLayoutRefresh("filter-drawer")
end

function UI:GetActiveFilterCount()
    return #self:GetActiveFilterChips()
end

function UI:CreateListToolbar(parent)
    local widgets = BigBiSList.Widgets
    local toolbar = CreateFrame("Frame", nil, parent)
    toolbar:SetHeight(TOOLBAR_HEIGHT)
    toolbar:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, 0)
    toolbar:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, 0)
    local search = widgets:CreatePanel(nil, toolbar)
    search:SetSize(172, 28)
    search:SetPoint("LEFT", toolbar, "LEFT", 4, 0)
    self.searchFrame = search
    local icon = search:CreateTexture(nil, "ARTWORK")
    icon:SetSize(14, 14); icon:SetPoint("LEFT", search, "LEFT", 8, 0)
    widgets:SetIcon(icon, "search")
    local input = CreateFrame("EditBox", "BigBiSListSearchBox", search)
    input:SetPoint("LEFT", search, "LEFT", 30, 0)
    input:SetPoint("RIGHT", search, "RIGHT", -30, 0)
    input:SetHeight(24); input:SetAutoFocus(false); input:SetMaxLetters(96)
    input:SetFontObject("GameFontHighlightSmall")
    self.searchBox = input
    self.searchPlaceholder = widgets:CreateLabel(search, "Search items or sources")
    self.searchPlaceholder:SetPoint("LEFT", input, "LEFT", 0, 0)
    self.searchPlaceholder:SetTextColor(0.56, 0.56, 0.60)
    self.searchPlaceholder:SetWidth(135)
    local function clearSearch()
        self:BeginNavigationChange("filter")
        self:GetFilters().search = ""
        input:SetText(""); input:ClearFocus()
        self:Invalidate("query", "search-clear"); self:ScheduleRefresh(nil, "search-clear")
    end
    self.searchClearButton = widgets:CreateUtilityButton(search, "clear", 28, clearSearch, "Clear search")
    self.searchClearButton:SetPoint("RIGHT", search, "RIGHT", 0, 0)
    input:SetScript("OnTextChanged", function(edit, user)
        self.searchPlaceholder:SetShown(edit:GetText() == "")
        self.searchClearButton:SetShown(edit:GetText() ~= "")
        if user then
            self:BeginNavigationChange("filter")
            self:GetFilters().search = trim(edit:GetText())
            self:Invalidate("query", "search"); self:ScheduleRefresh(SEARCH_DEBOUNCE_SECONDS, "search")
        end
    end)
    input:SetScript("OnEscapePressed", clearSearch)
    input:SetScript("OnEnterPressed", function(edit) edit:ClearFocus() end)
    self.filterToggleButton = widgets:CreateTextButton(toolbar, "Filters", 86, 28, function() self:SetFilterDrawerOpen(not self.filterDrawerOpen) end)
    self.filterToggleButton:SetPoint("LEFT", search, "RIGHT", 6, 0)
    self.sortDropdown = widgets:CreateDropdown("BigBiSListSortDropdown", toolbar, 104,
        function() return self:GetSortDropdownText() end, function() return self:GetSortDropdownItems() end,
        function(value) self:SelectSort(value) end)
    self.sortDropdown:SetPoint("LEFT", self.filterToggleButton, "RIGHT", -12, -2)
    self.inspectorToggleButton = widgets:CreateUtilityButton(toolbar, "details", 28,
        function() self:SetInspectorVisible(not self:IsInspectorVisible()) end, "Show or hide item details")
    self.inspectorToggleButton:SetPoint("RIGHT", toolbar, "RIGHT", -4, 0)
    self.resultCountText = widgets:CreateLabel(toolbar, "0 results")
    self.resultCountText:SetPoint("RIGHT", self.inspectorToggleButton, "LEFT", -8, 0)
    self.resultCountText:SetWidth(72)
    self.listToolbar = toolbar
    self.slotPickerButton = widgets:CreateTextButton(toolbar, "All slots", 112, 28, function()
        self:SetSlotPickerOpen(not (self.slotPickerOverlay and self.slotPickerOverlay:IsShown()))
    end)
    self.slotPickerButton:Hide()
    self.upgradesViewButton = widgets:CreateTextButton(toolbar, "Browse items", 116, 28, function()
        self:ToggleUpgradesView()
    end)
    self.upgradesViewButton:Hide()
    self.earlierCheckbox = widgets:CreateCheckbox(toolbar, "Include earlier recommendations", 224, function(value)
        self:SetFilter("includeEarlier", value)
    end)
    widgets:BindTooltip(self.earlierCheckbox, "Include recommendations from earlier guides that are obtainable through the target tier. Their ratings always identify the guide tier.")
    self.earlierCheckbox:Hide()
end

function UI:LayoutPrimaryControls()
    if not self.listToolbar or not self.groupDropdown then return end
    local tab = self:GetSelection().tab
    local controls = { self.upgradeModeDropdown, self.groupDropdown, self.wishlistRelevanceDropdown }
    for _, control in ipairs(controls) do control:Hide() end
    if self.earlierCheckbox then self.earlierCheckbox:Hide() end
    for _, button in ipairs(self.enhancementSwitchButtons or {}) do button:Hide() end
    local switchUpgradesView = tab == "Upgrades" and self.hasNextUpgradeActions
    local showingActions = switchUpgradesView and self.upgradesView ~= "list"
    local sortVisible = not showingActions and not (self:IsLevelingActivityView() and not self.levelingActivity)
    local groupVisible = (tab == "Upgrades" and not showingActions) or tab == "By Slot" or tab == "Wishlist" or tab == "Gear Guide"
    local primary = tab == "Upgrades" and self.upgradeModeDropdown or (tab == "Wishlist" and self.wishlistRelevanceDropdown)
    local rowHeight, rowGap, gap = TOOLBAR_HEIGHT, 2, 8
    local width = self.contentRegion:GetWidth() or 720
    local function place(control, x, row)
        control:ClearAllPoints()
        control:SetPoint("TOPLEFT", self.listToolbar, "TOPLEFT", x, -(row or 0) * (rowHeight + rowGap) - (rowHeight - control:GetHeight()) / 2)
    end
    local x = 4
    local browseSlots = tab == "By Slot" or tab == "Gear Guide"
    self.slotPickerButton:SetShown(browseSlots)
    if browseSlots then
        local focused = self:GetFocusedBrowseSlot()
        self.slotPickerButton.label:SetText(focused or self:GetSlotDropdownText())
        self:RefreshSlotPickerSelection()
        place(self.slotPickerButton, x, 0)
        x = x + self.slotPickerButton:GetWidth() + gap
    end
    self.upgradesViewButton:SetShown(switchUpgradesView)
    if switchUpgradesView then
        self.upgradesViewButton.label:SetText(self.upgradesView == "list" and "Available now" or "Browse items")
        place(self.upgradesViewButton, x, 0)
        x = x + self.upgradesViewButton:GetWidth() + gap
    end
    self.sortDropdown:SetShown(sortVisible)
    for _, control in ipairs({ self.searchFrame, self.filterToggleButton, sortVisible and self.sortDropdown or nil }) do
        place(control, x, 0)
        x = x + control:GetWidth() + gap
    end
    place(self.inspectorToggleButton, width - 32, 0)
    local optional = {}
    if groupVisible then
        self.groupDropdown:SetParent(self.listToolbar)
        self.groupDropdown:Show(); self.groupDropdown:Refresh()
        optional[#optional + 1] = self.groupDropdown
    end
    if primary then
        primary:SetParent(self.listToolbar)
        primary:Show(); primary:Refresh()
        optional[#optional + 1] = primary
    end
    if self.earlierCheckbox and ((tab == "Upgrades" and not showingActions) or tab == "By Slot") then
        self.earlierCheckbox:SetChecked(self:GetFilters().includeEarlier == true)
        self.earlierCheckbox:Show()
        optional[#optional + 1] = self.earlierCheckbox
    end
    if tab == "Enhance" then
        self.enhancementSwitchButtons = self.enhancementSwitchButtons or {}
        local options = { {"all", "All", 34}, {"gem", "Gems", 45}, {"enchant", "Enchants", 65}, {"consumable", "Consumables", 88} }
        for index, option in ipairs(options) do
            local button = self.enhancementSwitchButtons[index]
            if not button then
                local key = option[1]
                button = BigBiSList.Widgets:CreateTextButton(self.listToolbar, option[2], option[3], 28,
                    function() self:SetViewStateValue("Enhance", "type", key) end)
                self.enhancementSwitchButtons[index] = button
            end
            button:SetSelected(self:GetViewState("Enhance").type == option[1]); button:Show()
            optional[#optional + 1] = button
        end
    end
    local optionalWidth = 0
    for _, control in ipairs(optional) do optionalWidth = optionalWidth + control:GetWidth() + gap end
    local wrapped = #optional > 0 and x + optionalWidth > width - 32
    local optionalX = wrapped and 4 or x
    local optionalRow = wrapped and 1 or 0
    for _, control in ipairs(optional) do
        if optionalX > 4 and optionalX + control:GetWidth() > width - (optionalRow == 0 and 32 or 4) then
            optionalX = 4
            optionalRow = optionalRow + 1
        end
        place(control, optionalX, optionalRow)
        optionalX = optionalX + control:GetWidth() + gap
    end
    self.listToolbar:SetHeight(rowHeight * (optionalRow + 1) + rowGap * optionalRow)
    local firstRowEnd = wrapped and x or optionalX
    self.resultCountText:SetShown(width >= 900 and firstRowEnd + 80 <= width - 32)
end

function UI:CreateFilterDrawer(parent)
    local widgets = BigBiSList.Widgets
    local overlay = widgets:CreatePanel(nil, parent, { 0.045, 0.045, 0.052, 1 }, { 0.30, 0.30, 0.34, 1 })
    overlay:SetFrameLevel((parent:GetFrameLevel() or 0) + 45)
    overlay:EnableMouse(true)
    overlay:SetPoint("TOPRIGHT", self.listToolbar, "BOTTOMRIGHT", -4, -4)
    overlay:SetSize(354, 300)
    local close = widgets:CreateUtilityButton(overlay, "clear", 28, function() self:SetFilterDrawerOpen(false) end, "Close filters")
    close:SetPoint("TOPRIGHT", overlay, "TOPRIGHT", -4, -4)
    local scroll, drawer = widgets:CreateScrollFrame("BigBiSListFilterScroll", overlay)
    scroll:SetPoint("TOPLEFT", overlay, "TOPLEFT", 6, -38)
    scroll:SetPoint("BOTTOMRIGHT", overlay, "BOTTOMRIGHT", -28, 8)
    self.filterDrawer = overlay
    self.filterDrawerContent = drawer
    self.filterDrawerScroll = scroll
    local function updateOverflow()
        widgets:UpdateScrollOverflow(scroll)
    end
    scroll:HookScript("OnSizeChanged", updateOverflow)
    scroll:HookScript("OnScrollRangeChanged", updateOverflow)
    scroll:HookScript("OnVerticalScroll", updateOverflow)

    self.filterItemHeader = drawer:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    self.filterItemHeader:SetTextColor(1, 0.82, 0.28, 1)
    self.filterItemHeader:SetText("Item")
    self.filterAcquisitionHeader = drawer:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    self.filterAcquisitionHeader:SetTextColor(1, 0.82, 0.28, 1)
    self.filterAcquisitionHeader:SetText("Acquisition")

    local function dropdown(name, getText, getItems, onSelect)
        return widgets:CreateDropdown(name, drawer, 132, getText, getItems, onSelect)
    end

    self.upgradeModeDropdown = dropdown("BigBiSListUpgradeModeDropdown",
        function() return upgradeModeLabel(self:GetFilters("Upgrades").upgradeMode) end,
        function() return self:GetUpgradeModeDropdownItems() end,
        function(value)
            self:SetFilter("upgradeMode", value)
        end)
    self.ownedDropdown = dropdown("BigBiSListOwnedDropdown",
        function() return "Owned: " .. ownedFilterLabel(self:GetFilters().ownedState) end,
        function() return self:GetOwnedDropdownItems() end,
        function(value) self:SetFilter("ownedState", value) end)
    self.rankDropdown = dropdown("BigBiSListRankDropdown",
        function() return self:GetRankDropdownText() end,
        function() return self:GetRankDropdownItems() end,
        function(value) self:ToggleFacetFilter("rankGroups", value, "rankGroup") end)
    self.longevityDropdown = dropdown("BigBiSListLongevityDropdown",
        function() return "When useful: " .. longevityFilterLabel(self:GetFilters().longevity) end,
        function() return self:GetLongevityDropdownItems() end,
        function(value)
            self:SetFilter("longevity", value)
        end)
    self.boeDropdown = dropdown("BigBiSListBoeDropdown",
        function() return "Binding: " .. boeFilterLabel(self:GetFilters().boe) end,
        function() return self:GetBoeDropdownItems() end,
        function(value) self:SetFilter("boe", value) end)
    self.slotDropdown = dropdown("BigBiSListSlotDropdown",
        function() return self:GetSlotDropdownText() end,
        function() return self:GetSlotDropdownItems() end,
        function(value) self:ToggleFacetFilter("slots", value) end)

    self.sourceDropdown = dropdown("BigBiSListSourceDropdown",
        function() return self:GetSourceDropdownText() end,
        function() return self:GetSourceDropdownItems() end,
        function(value) self:ToggleFacetFilter("sourceTypes", value, "sourceType") end)
    self.costDropdown = dropdown("BigBiSListCostDropdown",
        function() return self:GetCostDropdownText() end,
        function() return self:GetCostDropdownItems() end,
        function(value) self:ToggleFacetFilter("costs", value, "cost") end)
    self.vendorDropdown = dropdown("BigBiSListVendorDropdown",
        function() return self:GetVendorDropdownText() end,
        function() return self:GetVendorDropdownItems() end,
        function(value) self:ToggleFacetFilter("vendors", value, "vendor") end)
    self.zoneDropdown = dropdown("BigBiSListZoneDropdown",
        function() return self:GetZoneDropdownText() end,
        function() return self:GetZoneDropdownItems() end,
        function(value) self:ToggleFacetFilter("zones", value, "zone") end)
    self.reputationDropdown = dropdown("BigBiSListReputationDropdown",
        function() return self:GetReputationDropdownText() end,
        function() return self:GetReputationDropdownItems() end,
        function(value) self:ToggleFacetFilter("reputations", value, "reputation") end)

    self.groupDropdown = dropdown("BigBiSListGroupDropdown",
        function()
            local tab = self:GetSelection().tab
            local value = self:GetViewState().groupBy or (tab == "Upgrades" and "priority" or (tab == "Wishlist" and "none" or "slot"))
            return ({ slot = "By slot", source = "By activity", activity = "By activity", priority = "By priority", none = "Ungrouped" })[value]
        end,
        function() return self:GetGroupingDropdownItems() end,
        function(value) self:SelectGrouping(value) end)
    self.recommendationCategoryDropdown = dropdown("BigBiSListRecommendationCategoryDropdown",
        function() return self:GetRecommendationCategoryDropdownText() end,
        function() return self:GetRecommendationCategoryDropdownItems() end,
        function(value) self:SetViewStateValue("Gear Guide", "recommendationCategory", value) end)
    self.enhancementTypeDropdown = dropdown("BigBiSListEnhancementTypeDropdown",
        function()
            local value = self:GetViewState("Enhance").type or "all"
            return ({ all = "All enhancements", gem = "Gems", enchant = "Enchants", consumable = "Consumables" })[value]
        end,
        function() return self:GetEnhancementTypeDropdownItems() end,
        function(value) self:SetViewStateValue("Enhance", "type", value) end)
    self.enhancementAppliedDropdown = dropdown("BigBiSListEnhancementAppliedDropdown",
        function()
            local value = self:GetViewState("Enhance").appliedState or "all"
            return ({ all = "All applied states", missing = "Not applied", applied = "Applied / owned" })[value]
        end,
        function() return self:GetEnhancementAppliedDropdownItems() end,
        function(value) self:SetViewStateValue("Enhance", "appliedState", value) end)
    self.wishlistRelevanceDropdown = dropdown("BigBiSListWishlistRelevanceDropdown",
        function()
            local value = self:GetViewState("Wishlist").relevance or "all"
            return ({ all = "All saved items", selected = "Selected spec", class = "Any class spec" })[value]
        end,
        function() return self:GetWishlistRelevanceDropdownItems() end,
        function(value) self:SetViewStateValue("Wishlist", "relevance", value) end)

    self.filterDrawerControls = {
        upgrade = self.upgradeModeDropdown,
        owned = self.ownedDropdown,
        rank = self.rankDropdown,
        usefulness = self.longevityDropdown,
        boe = self.boeDropdown,
        slot = self.slotDropdown,
        source = self.sourceDropdown,
        cost = self.costDropdown,
        vendor = self.vendorDropdown,
        zone = self.zoneDropdown,
        reputation = self.reputationDropdown,
        group = self.groupDropdown,
        recommendationCategory = self.recommendationCategoryDropdown,
        enhancementType = self.enhancementTypeDropdown,
        enhancementApplied = self.enhancementAppliedDropdown,
        wishlistRelevance = self.wishlistRelevanceDropdown,
    }

    self.clearFiltersButton = widgets:CreateTextButton(overlay, "Clear filters", 104, 28, function()
        self:ClearFilters()
    end)
    self.clearFiltersButton:SetPoint("TOPLEFT", overlay, "TOPLEFT", 8, -4)
end

function UI:GetVisibleFilterControlKeys()
    local tabName = normalizeTabName((self:GetSelection() or {}).tab)
    if tabName == "Upgrades" then
        return { "upgrade", "owned", "rank", "usefulness", "boe", "slot", "source", "cost", "vendor", "zone", "reputation" }
    elseif tabName == "By Slot" then
        return { "owned", "rank", "boe", "slot", "source", "cost", "vendor", "zone", "reputation" }
    elseif tabName == "Gear Guide" then
        return { "group", "recommendationCategory", "owned", "boe", "slot", "source", "cost", "vendor", "zone", "reputation" }
    elseif tabName == "Enhance" then
        return { "enhancementType", "enhancementApplied", "source", "cost", "vendor", "zone", "reputation" }
    elseif tabName == "Wishlist" then
        return { "wishlistRelevance", "owned", "rank", "boe", "slot", "source", "cost", "vendor", "zone", "reputation" }
    end
    return {}
end

function UI:RefreshFilterDrawer(forceLayout)
    if not self.filterDrawer then return end
    local keys = self:GetVisibleFilterControlKeys()
    local desired = {}
    for _, key in ipairs(keys) do desired[key] = true end
    local primary = { upgrade = true, group = true, wishlistRelevance = true, enhancementType = true }
    local removedControl = false
    for key, control in pairs(self.filterDrawerControls or {}) do
        if not desired[key] and not primary[key] and control:IsShown() then
            control:Hide(); removedControl = true
        end
    end
    if removedControl then BigBiSList.Widgets:CloseDropdownMenus() end
    self.enhancementTypeDropdown:Hide()
    self.visibleFilterControlKeys = desired
    local host = self.filterDrawerContent
    local acquisitionKeys = { source = true, cost = true, vendor = true, zone = true, reputation = true }
    local itemKeys, acquisition = {}, {}
    for _, key in ipairs(keys) do
        if not primary[key] then table.insert(acquisitionKeys[key] and acquisition or itemKeys, key) end
    end
    local y = 8
    local function layoutGroup(group, header)
        header:SetParent(host); header:ClearAllPoints()
        header:SetPoint("TOPLEFT", host, "TOPLEFT", 10, -y)
        header:SetShown(#group > 0)
        if #group == 0 then return end
        y = y + 24
        for index, key in ipairs(group) do
            local control = self.filterDrawerControls[key]
            control:SetParent(host); control:ClearAllPoints()
            control:SetPoint("TOPLEFT", host, "TOPLEFT", -6, -y - (index-1)*36)
            if UIDropDownMenu_SetWidth then UIDropDownMenu_SetWidth(control, 270) end
            control:Show(); control:Refresh()
        end
        y = y + #group*36 + 12
    end
    layoutGroup(itemKeys, self.filterItemHeader)
    layoutGroup(acquisition, self.filterAcquisitionHeader)
    host:SetHeight(y + 8)
    self:LayoutPrimaryControls()
    -- The scroll viewport consumes 38px above and 8px below its content.
    self.filterDrawer:SetHeight(math.min(host:GetHeight() + 46, math.max(160, (self.body:GetHeight() or 400) - (self.listToolbar:GetHeight() or TOOLBAR_HEIGHT) - 8)))
    BigBiSList.Widgets:UpdateScrollOverflow(self.filterDrawerScroll)
end

function UI:CreateBody(frame)
    local widgets = BigBiSList.Widgets
    local body = CreateFrame("Frame", nil, frame)
    body:SetPoint("TOPLEFT", self.tabBar, "BOTTOMLEFT", 0, -4)
    body:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -12, 34)
    body:SetScript("OnSizeChanged", function()
        if self.frame and self.frame:IsShown() then self:ScheduleLayoutRefresh("body-size") end
    end)

    local details = widgets:CreatePanel(nil, body, { 0.055, 0.055, 0.065, 0.94 }, { 0.18, 0.18, 0.20, 1 })
    details:SetWidth(DETAILS_WIDTH)
    details:SetPoint("TOPRIGHT", body, "TOPRIGHT", 0, 0)
    details:SetPoint("BOTTOMRIGHT", body, "BOTTOMRIGHT", 0, 0)

    local detailsTitle = details:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    detailsTitle:SetPoint("TOPLEFT", details, "TOPLEFT", 10, -10)
    detailsTitle:SetText("Details")

    self.detailsHeader = CreateFrame("Frame", nil, details)
    self.detailsHeader:SetPoint("TOPLEFT", details, "TOPLEFT", 0, 0)
    self.detailsHeader:SetPoint("TOPRIGHT", details, "TOPRIGHT", 0, 0)
    self.detailsHeader:SetHeight(76)
    detailsTitle:Hide()
    local closeDetails = widgets:CreateUtilityButton(details, "clear", 28, function()
        self:SetInspectorVisible(false)
    end, "Close details")
    closeDetails:SetPoint("RIGHT", self.detailsHeader, "RIGHT", -6, 0)
    self.detailsCloseButton = closeDetails
    self.detailsBackButton = widgets:CreateTextButton(details, "Back to list", 110, 28, function()
        self:SetInspectorVisible(false)
    end)
    self.detailsBackButton:SetPoint("TOPLEFT", details, "TOPLEFT", 8, -4)
    self.detailsBackButton:Hide()

    local detailsScroll, detailsContent = widgets:CreateScrollFrame("BigBiSListDetailsScroll", details)
    detailsScroll:SetPoint("TOPLEFT", self.detailsHeader, "BOTTOMLEFT", 8, -4)
    detailsScroll:SetPoint("BOTTOMRIGHT", details, "BOTTOMRIGHT", -28, 8)
    self.details = details
    self.detailsScroll = detailsScroll
    self.detailsContent = detailsContent
    self.detailsActionStrip = CreateFrame("Frame", nil, details)
    self.detailsActionStrip:SetPoint("TOPLEFT", self.detailsHeader, "BOTTOMLEFT", 0, 0)
    self.detailsActionStrip:SetPoint("TOPRIGHT", self.detailsHeader, "BOTTOMRIGHT", 0, 0)
    self.detailsActionStrip:SetHeight(36)
    self.detailsCompareButton = widgets:CreateTextButton(self.detailsActionStrip, "Compare slot", 112, 28, function(button)
        if button.boundData then self:OpenSlotComparison(button.boundData, button.boundMode, button.statRank) end
    end)
    self.detailsCompareButton:SetPoint("TOPLEFT", self.detailsActionStrip, "TOPLEFT", 8, -4)
    self.detailsActionStrip:Hide()
    detailsScroll:HookScript("OnSizeChanged", function()
        if self.frame and self.frame:IsShown() then self:RefreshDetailsLayout() end
    end)

    local contentRegion = CreateFrame("Frame", nil, body)
    contentRegion:SetPoint("TOPLEFT", body, "TOPLEFT", 0, 0)
    contentRegion:SetPoint("BOTTOMLEFT", body, "BOTTOMLEFT", 0, 0)
    contentRegion:SetPoint("RIGHT", details, "LEFT", -8, 0)

    self:CreateListToolbar(contentRegion)
    self:CreateFilterDrawer(contentRegion)

    local contentPanel = widgets:CreatePanel(nil, body, { 0.035, 0.035, 0.042, 0.94 }, { 0.15, 0.15, 0.17, 1 })
    contentPanel:SetParent(contentRegion)
    contentPanel:SetFrameLevel((contentRegion:GetFrameLevel() or 0) + 1)
    contentPanel:SetPoint("TOPLEFT", self.listToolbar, "BOTTOMLEFT", 0, -4)
    contentPanel:SetPoint("BOTTOMRIGHT", contentRegion, "BOTTOMRIGHT", 0, 0)

    local contentHeaderHost = CreateFrame("Frame", nil, contentPanel)
    contentHeaderHost:SetHeight(COLUMN_HEADER_HEIGHT)
    contentHeaderHost:SetPoint("TOPLEFT", contentPanel, "TOPLEFT", 8, -8)
    contentHeaderHost:SetPoint("TOPRIGHT", contentPanel, "TOPRIGHT", -28, -8)
    contentHeaderHost:Hide()
    self.contentHeaderHost = contentHeaderHost

    self.contentScroll, self.contentChild = widgets:CreateScrollFrame("BigBiSListContentScroll", contentPanel)
    self.contentScroll:SetPoint("TOPLEFT", contentPanel, "TOPLEFT", 8, -8)
    self.contentScroll:SetPoint("BOTTOMRIGHT", contentPanel, "BOTTOMRIGHT", -28, 8)
    self.contentScroll:HookScript("OnVerticalScroll", function()
        self:UpdateVirtualList()
    end)
    self.contentScroll:SetScript("OnSizeChanged", function(scroll, width, height)
        self:CountPerformance("sizeEvents")
        self.contentChild:SetWidth(width)
        local previousWidth = self.lastContentWidth
        local previousHeight = self.lastContentHeight
        self.lastContentWidth = width
        self.lastContentHeight = height
        local widthChanged = not previousWidth or math.abs(width - previousWidth) > LAYOUT_WIDTH_EPSILON
        local heightChanged = height and previousHeight and math.abs(height - previousHeight) > LAYOUT_WIDTH_EPSILON
        if self.frame and self.frame:IsShown() and widthChanged then
            self:Invalidate("layout", "content-width")
            self:ScheduleLayoutRefresh("content-width")
        elseif self.frame and self.frame:IsShown() and heightChanged then
            -- Height-only changes affect only which pooled rows are visible.
            -- Realize the newly exposed viewport without touching data state.
            self:UpdateVirtualList()
        end
    end)

    self.contentListLayer = CreateFrame("Frame", nil, self.contentChild)
    self.contentListLayer:SetPoint("TOPLEFT", self.contentChild, "TOPLEFT", 0, 0)
    self.contentListLayer:SetPoint("TOPRIGHT", self.contentChild, "TOPRIGHT", 0, 0)
    self.contentListLayer:SetHeight(1)

    self.contentStaticLayer = CreateFrame("Frame", nil, self.contentChild)
    self.contentStaticLayer:SetPoint("TOPLEFT", self.contentChild, "TOPLEFT", 0, 0)
    self.contentStaticLayer:SetPoint("TOPRIGHT", self.contentChild, "TOPRIGHT", 0, 0)
    self.contentStaticLayer:SetHeight(1)
    self.contentStaticLayer:Hide()
    self.gearFrame = self:CreateGearWorkspace(contentPanel)
    if BigBiSList.isForever then self.buildFrame = self:CreateGearWorkspace(contentPanel, true) end
    self.slotContextFrame = self:CreateSlotContext(contentRegion)
    if BigBiSList.isForever then
        local activityBar = CreateFrame("Frame", nil, contentRegion)
        activityBar:SetHeight(28)
        activityBar.back = widgets:CreateTextButton(activityBar, "All activities", 106, 28, function()
            self:SetLevelingActivity(nil)
        end)
        activityBar.back:SetPoint("LEFT")
        activityBar.title = widgets:CreateLabel(activityBar, "", "GameFontNormal")
        activityBar.title:SetPoint("LEFT", activityBar.back, "RIGHT", 12, 0)
        activityBar:Hide()
        self.levelingActivityBar = activityBar
    end

    self.emptyLabel = self.contentChild:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    self.emptyLabel:SetPoint("TOPLEFT", self.contentChild, "TOPLEFT", 8, -12)
    self.emptyLabel:SetPoint("RIGHT", self.contentChild, "RIGHT", -8, 0)
    self.emptyLabel:SetJustifyH("LEFT")
    self.emptyLabel:SetWordWrap(true)
    self.emptyLabel:SetTextColor(0.72, 0.72, 0.76, 1)
    self.emptyLabel:Hide()

    self.body = body
    self.contentRegion = contentRegion
    self.contentPanel = contentPanel
    self.filterDrawerOpen = false
    self:ApplyBodyLayout()
    self:SetStickyHeaderMode(nil)
end

function UI:GetBodyGeometry(width, inspectorVisible, chipHeight, supportsFilters)
    local docked = inspectorVisible and width >= MIN_WIDTH - 24
    local exclusive = inspectorVisible and not docked
    return { docked = docked, exclusive = exclusive, detailsWidth = exclusive and width or DETAILS_WIDTH,
        listWidth = width - (docked and DETAILS_WIDTH + 8 or 0),
        top = (supportsFilters and TOOLBAR_HEIGHT + 4 or 0) + (chipHeight > 0 and chipHeight + 4 or 0) }
end

function UI:ApplyBodyLayout()
    if not self.body or not self.contentRegion or not self.contentPanel then return end
    if self.ApplySlotComparisonLayout and self:ApplySlotComparisonLayout() then return end
    local supportsFilters = self:ViewSupportsFilters()
    local showInspector = self:IsInspectorVisible()
    local geometry = self:GetBodyGeometry(self.body:GetWidth() or DEFAULT_WIDTH - 24, showInspector, 0, supportsFilters)
    self.inspectorDocked = geometry.docked
    self.inspectorExclusive = geometry.exclusive
    self.details:SetShown(showInspector)
    self.details:SetWidth(geometry.detailsWidth)
    self.details:SetFrameLevel((self.body:GetFrameLevel() or 0) + 4)
    self.details:EnableMouse(true)
    self.detailsBackButton:SetShown(geometry.exclusive)
    self.contentRegion:SetShown(not geometry.exclusive)
    local signature = tostring(geometry.docked) .. ":" .. tostring(geometry.exclusive) .. ":" .. tostring(showInspector) .. ":" .. tostring(supportsFilters)
    if self.bodyLayoutSignature ~= signature then
        self.bodyLayoutSignature = signature
        self.detailsHeader:ClearAllPoints()
        self.detailsHeader:SetPoint("TOPLEFT", self.details, "TOPLEFT", 0, geometry.exclusive and -36 or 0)
        self.detailsHeader:SetPoint("TOPRIGHT", self.details, "TOPRIGHT", 0, geometry.exclusive and -36 or 0)
        self.contentRegion:ClearAllPoints()
        self.contentRegion:SetPoint("TOPLEFT", self.body, "TOPLEFT", 0, 0)
        self.contentRegion:SetPoint("BOTTOMLEFT", self.body, "BOTTOMLEFT", 0, 0)
        self.contentRegion:SetPoint("RIGHT", geometry.docked and self.details or self.body, geometry.docked and "LEFT" or "RIGHT", geometry.docked and -8 or 0, 0)
    end
    self.listToolbar:SetShown(supportsFilters)
    self.filterDrawer:SetShown(supportsFilters and self.filterDrawerOpen == true)
    self:RefreshFilterDrawer()
    local activeHeight = supportsFilters and self:RefreshFixedActiveFilterBar() or 0
    if self.fixedActiveFilterBar then
        self.fixedActiveFilterBar:SetShown(activeHeight > 0)
        self.fixedActiveFilterBar:ClearAllPoints()
        self.fixedActiveFilterBar:SetPoint("TOPLEFT", self.listToolbar, "BOTTOMLEFT", 0, -2)
        self.fixedActiveFilterBar:SetPoint("TOPRIGHT", self.listToolbar, "BOTTOMRIGHT", 0, -2)
    end
    local top = supportsFilters and (activeHeight > 0 and self.fixedActiveFilterBar or self.listToolbar) or self.contentRegion
    if self:RefreshSlotContext() then
        self.slotContextFrame:SetPoint("TOPLEFT", top, "BOTTOMLEFT", 0, -4)
        self.slotContextFrame:SetPoint("TOPRIGHT", top, "BOTTOMRIGHT", 0, -4)
        top = self.slotContextFrame
    end
    if self.levelingActivityBar then
        local bar = self.levelingActivityBar
        local activity = self:IsLevelingActivityView() and self.levelingActivity or nil
        bar:SetShown(activity ~= nil)
        if activity then
            bar:SetPoint("TOPLEFT", top, "BOTTOMLEFT", 0, -4)
            bar:SetPoint("TOPRIGHT", top, "BOTTOMRIGHT", 0, -4)
            BigBiSList.Widgets:SetCellText(bar.title, activity, 1, 15, self.contentRegion:GetWidth() - bar.back:GetWidth() - 16)
            top = bar
        end
    end
    if self.contentTopAnchor ~= top then
        self.contentTopAnchor = top
        self.contentPanel:ClearAllPoints()
        self.contentPanel:SetPoint("TOPLEFT", top, supportsFilters and "BOTTOMLEFT" or "TOPLEFT", 0, supportsFilters and -4 or 0)
        self.contentPanel:SetPoint("BOTTOMRIGHT", self.contentRegion, "BOTTOMRIGHT", 0, 0)
    end
    local viewKey = self:GetViewKey()
    local showGear, showBuilds = viewKey == "myGear", viewKey == "builds"
    self.detailsBackButton.label:SetText(showBuilds and "Builds" or (showGear and TAB_DISPLAY_LABELS.Equipped or "Back to list"))
    local workspace = showBuilds and self.buildFrame or self.gearFrame
    local gearWasShown = workspace:IsShown()
    self.gearFrame:SetShown(showGear and not geometry.exclusive)
    if self.buildFrame then self.buildFrame:SetShown(showBuilds and not geometry.exclusive) end
    self.contentScroll:SetShown(not showGear and not showBuilds)
    if showGear or showBuilds then
        self.contentChild:SetHeight(math.max(1, self.contentScroll:GetHeight()))
        if not gearWasShown and workspace:IsShown() and not self.refreshInProgress then
            self:Invalidate("presentation", "gear-show")
            self:ScheduleRefresh(nil, "gear-show")
        end
        if self:LayoutGearWorkspace(workspace) and showGear then self:RefreshGearSelection() end
    end
    self:LayoutSlotPicker()
    self.inspectorToggleButton:SetSelected(showInspector)
end

function UI:GetBankStatusText()
    if BigBiSList.isForever then return "Ownership uses equipped gear and bags" end
    local owned = self.currentOwned
    if not owned or not owned.bankScanned then return "Bank not checked · Open your bank to include stored gear" end
    return "Bank cache · " .. ((owned.bankUpdatedAt and owned.bankUpdatedAt ~= "") and owned.bankUpdatedAt or "Scanned")
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

    self.undoButton = widgets:CreateTextButton(status, "Undo", 60, 24, function() self:UndoLastAction() end)
    self.undoButton:SetPoint("RIGHT", status, "RIGHT", -32, 0)
    self.undoButton:Hide()
    self.statusText:SetPoint("RIGHT", status, "RIGHT", -104, 0)

    local resize = CreateFrame("Button", nil, status)
    resize:SetSize(16, 16)
    resize:SetPoint("RIGHT", status, "RIGHT", -7, 0)
    resize:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    resize:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
    resize:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
    resize:SetScript("OnMouseDown", function(_, buttonName)
        if buttonName == "LeftButton" and not accountDB().profile.window.locked then
            self:ApplyResizeBounds()
            frame:StartSizing("BOTTOMRIGHT")
        end
    end)
    resize:SetScript("OnMouseUp", function()
        frame:StopMovingOrSizing()
        self:SaveWindow()
        self.bodyLayoutSignature = nil
        self:Invalidate("layout", "resize-finished")
        self:ScheduleLayoutRefresh("resize-finished")
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
    self:CreateContextBar(frame)
    self:CreatePhaseBar(frame)
    self:CreateTabBar(frame)
    self:CreateBody(frame)
    self:CreateStatusBar(frame)
    self:Invalidate("all", "frame-create")

    frame:SetScript("OnHide", function()
        self:SaveWindow()
        self:SetSlotPickerOpen(false)
        self:ReleaseRenderFrames()
        if BigBiSList.Widgets.CloseDropdownMenus then
            BigBiSList.Widgets:CloseDropdownMenus()
        end
    end)
    frame:SetScript("OnShow", function()
        self:ApplyResizeBounds()
    end)

    return frame
end

function UI:Open()
    if not self.frame then
        self:CreateMainFrame()
    end

    self:ApplyResizeBounds()
    self.frame:Show()
    if self.currentViewQueryContext ~= self:GetProgressionCacheKey() then
        self:Invalidate("query", "progression-changed")
    end
    local dirty = self.dirtyDomains or {}
    local dataDirty = dirty.ownership or dirty.access or dirty.query or dirty.availability or dirty.details or dirty.controls or dirty.presentation
    if not self.hasRenderedContent or dataDirty then
        self:ScheduleRefresh(nil, "open")
    else
        self:RefreshControls()
        if dirty.layout then
            self:RefreshLayout("open")
        elseif self:GetViewKey() == "myGear" or self:GetViewKey() == "builds" then
            self:RenderGearTab()
        else
            self:UpdateVirtualList(true)
        end
    end
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

function BigBiSList:RefreshUI(domains, reason)
    if self.UI then
        self.UI:Invalidate(domains or "query", reason or "external")
    end
    if self.UI and self.UI.frame and self.UI.frame:IsShown() then
        self.UI:ScheduleRefresh(nil, reason or "external")
    end
end

function BigBiSList:InitUIEvents()
    if self.uiEventFrame then
        return
    end

    local frame = CreateFrame("Frame")
    local function registerEventSafe(eventName)
        pcall(frame.RegisterEvent, frame, eventName)
    end
    registerEventSafe("PLAYER_EQUIPMENT_CHANGED")
    registerEventSafe("BAG_UPDATE_DELAYED")
    registerEventSafe("PLAYER_ENTERING_WORLD")
    registerEventSafe("BANKFRAME_OPENED")
    registerEventSafe("PLAYERBANKSLOTS_CHANGED")
    registerEventSafe("UPDATE_FACTION")
    registerEventSafe("SKILL_LINES_CHANGED")
    registerEventSafe("SPELLS_CHANGED")
    if self.isForever then
        registerEventSafe("QUEST_LOG_UPDATE")
        registerEventSafe("BANKFRAME_CLOSED")
        registerEventSafe("BANK_TABS_CHANGED")
        registerEventSafe("PLAYER_INTERACTION_MANAGER_FRAME_SHOW")
        registerEventSafe("PLAYER_INTERACTION_MANAGER_FRAME_HIDE")
    end
    frame:SetScript("OnEvent", function(_, event, interaction)
        if event == "QUEST_LOG_UPDATE" then
            self.UI.currentAccessEvaluationCache = nil
            self:RefreshUI("details", event)
            return
        end
        if self.ForeverScoring and (event == "PLAYER_EQUIPMENT_CHANGED" or event == "SPELLS_CHANGED") then
            self.ForeverScoring:Invalidate()
            self:RefreshUI("query", event)
        end
        if self.isForever then
            if event == "PLAYER_INTERACTION_MANAGER_FRAME_SHOW" or event == "PLAYER_INTERACTION_MANAGER_FRAME_HIDE" then
                local banker = Enum and Enum.PlayerInteractionType and Enum.PlayerInteractionType.Banker
                if not banker or not self.IsReadableValue(interaction) or interaction ~= banker then return end
                event = event == "PLAYER_INTERACTION_MANAGER_FRAME_SHOW" and "BANKFRAME_OPENED" or "BANKFRAME_CLOSED"
            end
            if event == "BANKFRAME_OPENED" then
                self.UI.personalBankOpen = true
            elseif event == "BANKFRAME_CLOSED" or event == "PLAYER_ENTERING_WORLD" then
                self.UI.personalBankOpen = false
            end
            if self.UI.personalBankOpen and (event == "BANKFRAME_OPENED" or event == "PLAYERBANKSLOTS_CHANGED"
                or event == "BAG_UPDATE_DELAYED" or event == "BANK_TABS_CHANGED") then
                self.UI:ScanBankItems()
            end
        elseif event == "BANKFRAME_OPENED" or event == "PLAYERBANKSLOTS_CHANGED"
            or (event == "BAG_UPDATE_DELAYED" and BankFrame and BankFrame:IsShown()) then
            self.UI:ScanBankItems()
        end
        if event == "PLAYER_ENTERING_WORLD" then
            self:RefreshUI("all", event)
        elseif event == "UPDATE_FACTION" or event == "SKILL_LINES_CHANGED" or event == "SPELLS_CHANGED" then
            self:RefreshUI("access", event)
        else
            self:RefreshUI("ownership", event)
        end
        if self.isForever and self.ScheduleItemTooltipRefresh then self:ScheduleItemTooltipRefresh() end
    end)
    self.uiEventFrame = frame
end
