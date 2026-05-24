local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or "BigBiSList"
BigBiSList.displayName = "Big BiS List"
BigBiSList.version = "0.1.0"

BigBiSList.defaults = {
    profile = {
        showMinimap = true,
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
        selectedPhase = "SWP",
        selectedTab = "Phase",
        selection = {
            class = "Druid",
            spec = "Feral dps",
            phase = "SWP",
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

    migrateSelection(BigBiSListDB.char)
    applyDefaults(BigBiSListDB, self.defaults)
    migrateSelection(BigBiSListDB.char)

    BigBiSListDB.char.selectedClass = BigBiSListDB.char.selection.class
    BigBiSListDB.char.selectedSpec = BigBiSListDB.char.selection.spec
    BigBiSListDB.char.selectedPhase = BigBiSListDB.char.selection.phase
    BigBiSListDB.char.selectedTab = BigBiSListDB.char.selection.tab

    return BigBiSListDB
end
