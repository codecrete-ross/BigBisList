local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or "BigBiSList"
BigBiSList.displayName = "Big BiS List"
BigBiSList.version = "0.1.0"

local DEFAULTS_VERSION = 3

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

    BigBiSListDB.char.selectedClass = BigBiSListDB.char.selection.class
    BigBiSListDB.char.selectedSpec = BigBiSListDB.char.selection.spec
    BigBiSListDB.char.selectedPhase = BigBiSListDB.char.selection.phase
    BigBiSListDB.char.selectedTab = BigBiSListDB.char.selection.tab
    BigBiSListDB.profile.defaultsVersion = DEFAULTS_VERSION

    return BigBiSListDB
end
