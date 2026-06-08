local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or "BigBiSList"
BigBiSList.displayName = "Big BiS List"

local function addonMetadata(field)
    if C_AddOns and C_AddOns.GetAddOnMetadata then
        return C_AddOns.GetAddOnMetadata(BigBiSList.addonName, field)
    end
    if GetAddOnMetadata then
        return GetAddOnMetadata(BigBiSList.addonName, field)
    end
    return nil
end

local version = addonMetadata("Version")
if version == nil or version == "" or version == "@project-version@" then
    version = "0.7.0"
end
BigBiSList.version = version

local DEFAULTS_VERSION = 11
local DEFAULT_SELECTED_CLASS = "Druid"
local DEFAULT_SELECTED_SPEC = "Feral dps"

local PLAYER_CLASS_NAMES = {
    DRUID = DEFAULT_SELECTED_CLASS,
    HUNTER = "Hunter",
    MAGE = "Mage",
    PALADIN = "Paladin",
    PRIEST = "Priest",
    ROGUE = "Rogue",
    SHAMAN = "Shaman",
    WARLOCK = "Warlock",
    WARRIOR = "Warrior",
}

local TAB_NAME_ALIASES = {
    Phase = "By Slot",
    Gear = "Equipped",
    Planner = "Upgrades",
    Enhancements = "Enhance",
}

local function normalizeTabName(tabName)
    return TAB_NAME_ALIASES[tabName] or tabName
end

BigBiSList.defaults = {
    profile = {
        minimap = {
            hide = false,
            minimapPos = 225,
        },
        window = {
            point = "CENTER",
            relativePoint = "CENTER",
            x = 0,
            y = 0,
            width = 1160,
            height = 660,
            scale = 1,
            locked = false,
        },
        tooltips = {
            enabled = true,
            compact = true,
            selectedSpecFirst = true,
            showAllOnAlt = true,
            specFilters = {},
            specFiltersInitialized = false,
        },
    },
    char = {
        selectedClass = DEFAULT_SELECTED_CLASS,
        selectedSpec = DEFAULT_SELECTED_SPEC,
        selectedPhase = "PR",
        lastDetectedPhase = "PR",
        selectedTab = "Upgrades",
        selection = {
            class = DEFAULT_SELECTED_CLASS,
            spec = DEFAULT_SELECTED_SPEC,
            phase = "PR",
            tab = "Upgrades",
        },
        filters = {
            search = "",
            sourceType = "all",
            zone = "all",
            reputation = "all",
            rankGroup = "all",
            ownedState = "all",
            binding = "all",
            boe = "all",
            faction = "all",
            longevity = "all",
            slots = {},
        },
        bankCache = {
            scanned = false,
            updatedAt = "",
            items = {},
            links = {},
        },
        wishlist = {},
        ignoredItems = {},
    },
}

local function applyDefaults(target, defaults)
    for key, value in pairs(defaults) do
        if type(value) == "table" then
            if type(target[key]) ~= "table" then
                target[key] = {}
            end
            applyDefaults(target[key], value)
        elseif target[key] == nil then
            target[key] = value
        end
    end
end

local function migrateSelection(char)
    char.selection = char.selection or {}

    if char.selection.class == nil and char.selectedClass ~= nil then
        char.selection.class = char.selectedClass
    end
    if char.selection.spec == nil and char.selectedSpec ~= nil then
        char.selection.spec = char.selectedSpec
    end
    if char.selection.phase == nil and char.selectedPhase ~= nil then
        char.selection.phase = char.selectedPhase
    end
    if char.selection.tab == nil and char.selectedTab ~= nil then
        char.selection.tab = char.selectedTab
    end

    char.selection.tab = normalizeTabName(char.selection.tab)
    char.selectedTab = normalizeTabName(char.selectedTab)
end

local function migrateLegacyDefaults(char, previousVersion)
    if previousVersion ~= nil then
        return
    end

    if char.selection and char.selection.phase == "SWP" and char.selectedPhase == "SWP" then
        char.selection.phase = "PR"
        char.selectedPhase = "PR"
    end

    if char.selection then
        char.selection.tab = normalizeTabName(char.selection.tab)
    end
    char.selectedTab = normalizeTabName(char.selectedTab)
end

local function migrateMinimapSettings(db)
    local profile = db.profile or {}
    db.profile = profile

    if type(profile.minimap) ~= "table" then
        profile.minimap = {}
    end

    local minimap = profile.minimap
    if minimap.minimapPos == nil and minimap.angle ~= nil then
        minimap.minimapPos = minimap.angle
    end
    minimap.angle = nil

    if profile.showMinimap == false then
        minimap.hide = true
    end
    profile.showMinimap = nil
end

local function enableAllTooltipSpecFilters(tooltips, index)
    if type(tooltips.specFilters) ~= "table" then
        tooltips.specFilters = {}
    end

    for _, classData in ipairs(index.classes or {}) do
        local className = classData.name
        if className then
            if type(tooltips.specFilters[className]) ~= "table" then
                tooltips.specFilters[className] = {}
            end

            for _, specData in ipairs(classData.specs or {}) do
                local specName = specData.name
                if specName then
                    tooltips.specFilters[className][specName] = true
                end
            end
        end
    end

    tooltips.specFiltersInitialized = true
end

local function tooltipSpecFiltersMatchLegacyDruidDefault(tooltips, index)
    if type(tooltips.specFilters) ~= "table" or tooltips.specFiltersInitialized ~= true then
        return false
    end

    local sawSpec = false
    local sawDruidSpec = false

    for _, classData in ipairs(index.classes or {}) do
        local className = classData.name
        local classFilters = className and tooltips.specFilters[className] or nil

        for _, specData in ipairs(classData.specs or {}) do
            local specName = specData.name
            if className and specName then
                sawSpec = true

                if className == "Druid" then
                    sawDruidSpec = true
                    if type(classFilters) ~= "table" or classFilters[specName] ~= true then
                        return false
                    end
                elseif type(classFilters) == "table" and classFilters[specName] == true then
                    return false
                end
            end
        end
    end

    return sawSpec and sawDruidSpec
end

local function migrateTooltipSpecFilterDefaults(db, previousVersion)
    if previousVersion ~= nil and previousVersion >= 7 then
        return
    end

    if not BigBiSList.GetClassSpecIndex then
        return
    end

    local profile = db.profile or {}
    local tooltips = profile.tooltips
    if type(tooltips) ~= "table" then
        return
    end

    local index = BigBiSList:GetClassSpecIndex()
    if tooltipSpecFiltersMatchLegacyDruidDefault(tooltips, index) then
        enableAllTooltipSpecFilters(tooltips, index)
    end
end

local function migrateSplitDropSourceFilter(char, previousVersion)
    if previousVersion ~= nil and previousVersion >= 8 then
        return
    end

    local filters = char and char.filters
    if type(filters) ~= "table" then
        return
    end

    if filters.sourceType == "drop" then
        filters.sourceType = "all"
    end
    if type(filters.sourceTypes) == "table" then
        filters.sourceTypes.drop = nil
    end
end

local function playerClassFromToken(classToken)
    if type(classToken) ~= "string" then
        return nil
    end

    return PLAYER_CLASS_NAMES[classToken] or PLAYER_CLASS_NAMES[string.upper(classToken)]
end

local function normalizedSpecName(specName)
    if type(specName) ~= "string" then
        return nil
    end

    return string.lower(specName)
end

local function specsForClass(className)
    if not className or not BigBiSList.GetClassSpecIndex then
        return {}
    end

    return BigBiSList:GetClassSpecIndex().specsByClass[className] or {}
end

local function firstSpecNameForClass(className)
    local specs = specsForClass(className)
    if specs[1] then
        return specs[1].name
    end

    return nil
end

local function specNameForClass(className, specName)
    local normalized = normalizedSpecName(specName)
    if not normalized then
        return nil
    end

    for _, spec in ipairs(specsForClass(className)) do
        if normalizedSpecName(spec.name) == normalized then
            return spec.name
        end
    end

    return nil
end

function BigBiSList:DetectPlayerClass()
    if UnitClassBase then
        local ok, first, second = pcall(UnitClassBase, "player")
        if ok then
            local className = playerClassFromToken(first) or playerClassFromToken(second)
            if className then
                return className
            end
        end
    end

    if UnitClass then
        local ok, _, classToken = pcall(UnitClass, "player")
        if ok then
            return playerClassFromToken(classToken)
        end
    end

    return nil
end

function BigBiSList:DetectPlayerSpec(className)
    if not className or not GetNumTalentTabs or not GetTalentTabInfo then
        return nil
    end

    local ok, tabCount = pcall(GetNumTalentTabs)
    if not ok or type(tabCount) ~= "number" then
        return nil
    end

    local selectedTabName
    local selectedPoints = 0
    local selectedTie = false
    for tabIndex = 1, tabCount do
        local tabOk, first, second, third, fourth, fifth = pcall(GetTalentTabInfo, tabIndex)
        local tabName = type(first) == "string" and first or second
        local pointsSpent = type(third) == "number" and third or fifth
        if tabOk and type(tabName) == "string" and type(pointsSpent) == "number" then
            if pointsSpent > selectedPoints then
                selectedTabName = tabName
                selectedPoints = pointsSpent
                selectedTie = false
            elseif pointsSpent > 0 and pointsSpent == selectedPoints then
                selectedTie = true
            end
        end
    end

    if selectedTie then
        return nil
    end

    return specNameForClass(className, selectedTabName)
end

function BigBiSList:GetDetectedPlayerSelection()
    local className = self:DetectPlayerClass()
    if not className then
        return nil
    end

    return {
        class = className,
        spec = self:DetectPlayerSpec(className) or firstSpecNameForClass(className),
    }
end

local function selectionUsesBuiltInDefault(char)
    local selection = char and char.selection or {}
    local selectedClass = selection.class or (char and char.selectedClass)
    local selectedSpec = selection.spec or (char and char.selectedSpec)

    return (selectedClass == nil or selectedClass == DEFAULT_SELECTED_CLASS)
        and (selectedSpec == nil or selectedSpec == DEFAULT_SELECTED_SPEC)
end

local function applyDetectedDefaultSelection(char)
    if not char or not selectionUsesBuiltInDefault(char) then
        return
    end

    local detected = BigBiSList:GetDetectedPlayerSelection()
    if not detected or not detected.class then
        return
    end

    char.selection = char.selection or {}
    char.selection.class = detected.class
    char.selectedClass = detected.class

    if detected.spec then
        char.selection.spec = detected.spec
        char.selectedSpec = detected.spec
    end
end

local function ensureTooltipSpecFilters(db)
    local profile = db.profile or {}
    local tooltips = profile.tooltips or {}
    profile.tooltips = tooltips

    if type(tooltips.specFilters) ~= "table" then
        tooltips.specFilters = {}
    end

    if not BigBiSList.GetClassSpecIndex then
        return tooltips.specFilters
    end

    local index = BigBiSList:GetClassSpecIndex()
    local firstInitialization = tooltips.specFiltersInitialized ~= true

    for _, classData in ipairs(index.classes or {}) do
        local className = classData.name
        if className then
            if type(tooltips.specFilters[className]) ~= "table" then
                tooltips.specFilters[className] = {}
            end

            for _, specData in ipairs(classData.specs or {}) do
                local specName = specData.name
                if specName and (firstInitialization or tooltips.specFilters[className][specName] == nil) then
                    tooltips.specFilters[className][specName] = true
                end
            end
        end
    end

    tooltips.specFiltersInitialized = true
    return tooltips.specFilters
end

function BigBiSList:EnsureTooltipSpecFilters()
    if not BigBiSListDB or not BigBiSListDB.profile or not BigBiSListDB.profile.tooltips then
        return nil
    end

    return ensureTooltipSpecFilters(BigBiSListDB)
end

function BigBiSList:GetTooltipSpecFilterKey(specFilters)
    if type(specFilters) ~= "table" then
        return "all"
    end

    if not self.GetClassSpecIndex then
        return ""
    end

    local parts = {}
    local index = self:GetClassSpecIndex()
    for _, classData in ipairs(index.classes or {}) do
        local className = classData.name
        local classFilters = className and specFilters[className] or nil
        for _, specData in ipairs(classData.specs or {}) do
            local specName = specData.name
            if className and specName then
                table.insert(parts, className .. ":" .. specName .. "=" .. (type(classFilters) == "table" and classFilters[specName] == true and "1" or "0"))
            end
        end
    end

    return table.concat(parts, ";")
end

function BigBiSList:GetSelection()
    self:EnsureDatabase()
    return BigBiSListCharDB.selection
end

function BigBiSList:SetSelection(className, specName, phaseKey, tabName)
    self:EnsureDatabase()

    local selection = BigBiSListCharDB.selection
    if className then
        selection.class = className
        BigBiSListCharDB.selectedClass = className
    end
    if specName then
        selection.spec = specName
        BigBiSListCharDB.selectedSpec = specName
    end
    if phaseKey then
        selection.phase = phaseKey
        BigBiSListCharDB.selectedPhase = phaseKey
    end
    if tabName then
        selection.tab = normalizeTabName(tabName)
        BigBiSListCharDB.selectedTab = selection.tab
    end
end

function BigBiSList:GetCharacterDB()
    self:EnsureDatabase()
    return BigBiSListCharDB
end

function BigBiSList:EnsureDatabase()
    BigBiSListDB = BigBiSListDB or {}
    BigBiSListDB.profile = BigBiSListDB.profile or {}
    BigBiSListDB.char = nil
    BigBiSListCharDB = BigBiSListCharDB or {}

    local profilePreviousVersion = BigBiSListDB.profile.defaultsVersion
    local charPreviousVersion = BigBiSListCharDB.defaultsVersion

    migrateSelection(BigBiSListCharDB)
    migrateMinimapSettings(BigBiSListDB)
    applyDefaults(BigBiSListDB.profile, self.defaults.profile)
    applyDefaults(BigBiSListCharDB, self.defaults.char)
    migrateSelection(BigBiSListCharDB)
    migrateLegacyDefaults(BigBiSListCharDB, charPreviousVersion)
    migrateTooltipSpecFilterDefaults(BigBiSListDB, profilePreviousVersion)
    migrateSplitDropSourceFilter(BigBiSListCharDB, charPreviousVersion)
    applyDetectedDefaultSelection(BigBiSListCharDB)
    ensureTooltipSpecFilters(BigBiSListDB)

    BigBiSListCharDB.selectedClass = BigBiSListCharDB.selection.class
    BigBiSListCharDB.selectedSpec = BigBiSListCharDB.selection.spec
    BigBiSListCharDB.selectedPhase = BigBiSListCharDB.selection.phase
    BigBiSListCharDB.selectedTab = BigBiSListCharDB.selection.tab
    BigBiSListDB.profile.defaultsVersion = DEFAULTS_VERSION
    BigBiSListCharDB.defaultsVersion = DEFAULTS_VERSION

    return BigBiSListDB
end
