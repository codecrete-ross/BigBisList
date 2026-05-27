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
    version = "0.1.0"
end
BigBiSList.version = version

local DEFAULTS_VERSION = 4

BigBiSList.defaults = {
    profile = {
        showMinimap = true,
        minimap = {
            angle = 225,
        },
        window = {
            point = "CENTER",
            relativePoint = "CENTER",
            x = 0,
            y = 0,
            width = 1040,
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
        selectedTab = "Phase",
        selection = {
            class = "Druid",
            spec = "Feral dps",
            phase = "PR",
            tab = "Phase",
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
    local selectedClass = db.char and db.char.selection and db.char.selection.class

    for _, classData in ipairs(index.classes or {}) do
        local className = classData.name
        if className then
            if type(tooltips.specFilters[className]) ~= "table" then
                tooltips.specFilters[className] = {}
            end

            for _, specData in ipairs(classData.specs or {}) do
                local specName = specData.name
                if specName and (firstInitialization or tooltips.specFilters[className][specName] == nil) then
                    tooltips.specFilters[className][specName] = firstInitialization and className == selectedClass or false
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
        selection.tab = tabName
        BigBiSListDB.char.selectedTab = tabName
    end
end

function BigBiSList:EnsureDatabase()
    BigBiSListDB = BigBiSListDB or {}
    BigBiSListDB.profile = BigBiSListDB.profile or {}
    BigBiSListDB.char = BigBiSListDB.char or {}

    local previousVersion = BigBiSListDB.profile.defaultsVersion

    migrateSelection(BigBiSListDB.char)
    applyDefaults(BigBiSListDB, self.defaults)
    migrateSelection(BigBiSListDB.char)
    migrateLegacyDefaults(BigBiSListDB, previousVersion)
    ensureTooltipSpecFilters(BigBiSListDB)

    BigBiSListDB.char.selectedClass = BigBiSListDB.char.selection.class
    BigBiSListDB.char.selectedSpec = BigBiSListDB.char.selection.spec
    BigBiSListDB.char.selectedPhase = BigBiSListDB.char.selection.phase
    BigBiSListDB.char.selectedTab = BigBiSListDB.char.selection.tab
    BigBiSListDB.profile.defaultsVersion = DEFAULTS_VERSION

    return BigBiSListDB
end
