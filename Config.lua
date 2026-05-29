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
    version = "0.2.0"
end
BigBiSList.version = version

local DEFAULTS_VERSION = 8

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
        selectedClass = "Druid",
        selectedSpec = "Feral dps",
        selectedPhase = "PR",
        selectedTab = "Upgrades",
        selection = {
            class = "Druid",
            spec = "Feral dps",
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

local function migrateLegacyDefaults(db, previousVersion)
    if previousVersion ~= nil then
        return
    end

    local char = db.char
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

    if not BigBiSList.GetDataIndex then
        return
    end

    local profile = db.profile or {}
    local tooltips = profile.tooltips
    if type(tooltips) ~= "table" then
        return
    end

    local index = BigBiSList:GetDataIndex()
    if tooltipSpecFiltersMatchLegacyDruidDefault(tooltips, index) then
        enableAllTooltipSpecFilters(tooltips, index)
    end
end

local function migrateSplitDropSourceFilter(db, previousVersion)
    if previousVersion ~= nil and previousVersion >= 8 then
        return
    end

    local filters = db.char and db.char.filters
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

local function ensureTooltipSpecFilters(db)
    local profile = db.profile or {}
    local tooltips = profile.tooltips or {}
    profile.tooltips = tooltips

    if type(tooltips.specFilters) ~= "table" then
        tooltips.specFilters = {}
    end

    if not BigBiSList.GetDataIndex then
        return tooltips.specFilters
    end

    local index = BigBiSList:GetDataIndex()
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

    if not self.GetDataIndex then
        return ""
    end

    local parts = {}
    local index = self:GetDataIndex()
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
    return BigBiSListDB.char.selection
end

function BigBiSList:SetSelection(className, specName, phaseKey, tabName)
    self:EnsureDatabase()

    local selection = BigBiSListDB.char.selection
    if className then
        selection.class = className
        BigBiSListDB.char.selectedClass = className
    end
    if specName then
        selection.spec = specName
        BigBiSListDB.char.selectedSpec = specName
    end
    if phaseKey then
        selection.phase = phaseKey
        BigBiSListDB.char.selectedPhase = phaseKey
    end
    if tabName then
        selection.tab = normalizeTabName(tabName)
        BigBiSListDB.char.selectedTab = selection.tab
    end
end

function BigBiSList:EnsureDatabase()
    BigBiSListDB = BigBiSListDB or {}
    BigBiSListDB.profile = BigBiSListDB.profile or {}
    BigBiSListDB.char = BigBiSListDB.char or {}

    local previousVersion = BigBiSListDB.profile.defaultsVersion

    migrateSelection(BigBiSListDB.char)
    migrateMinimapSettings(BigBiSListDB)
    applyDefaults(BigBiSListDB, self.defaults)
    migrateSelection(BigBiSListDB.char)
    migrateLegacyDefaults(BigBiSListDB, previousVersion)
    migrateTooltipSpecFilterDefaults(BigBiSListDB, previousVersion)
    migrateSplitDropSourceFilter(BigBiSListDB, previousVersion)
    ensureTooltipSpecFilters(BigBiSListDB)

    BigBiSListDB.char.selectedClass = BigBiSListDB.char.selection.class
    BigBiSListDB.char.selectedSpec = BigBiSListDB.char.selection.spec
    BigBiSListDB.char.selectedPhase = BigBiSListDB.char.selection.phase
    BigBiSListDB.char.selectedTab = BigBiSListDB.char.selection.tab
    BigBiSListDB.profile.defaultsVersion = DEFAULTS_VERSION

    return BigBiSListDB
end
