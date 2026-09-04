local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or "BigBiSList"
BigBiSList.displayName = "Big BiS List"
BigBiSList.maxLevelingLevel = 69

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
    version = "0.12.3"
end
BigBiSList.version = version

local DEFAULTS_VERSION = 16
local DEFAULT_SELECTED_CLASS = "Druid"
local DEFAULT_SELECTED_SPEC = "Feral dps"
local MAX_LEVELING_LEVEL = BigBiSList.maxLevelingLevel
local LEVELING_PHASE_KEY = BigBiSList.levelingPhaseKey or "LEVELING"
local DEFAULT_ENDGAME_PHASE_KEY = "PR"
local DEFAULT_CONTENT_MODE = "endgame"

local CONTENT_MODES = {
    endgame = true,
    leveling = true,
}

local ENDGAME_PHASE_KEYS = {
    PR = true,
    T4 = true,
    T5 = true,
    T6 = true,
    ZA = true,
    SWP = true,
}

local MODE_DEFAULT_TABS = {
    endgame = "Upgrades",
    leveling = "Gear Guide",
}

local MODE_TABS = {
    endgame = {
        Upgrades = true,
        ["By Slot"] = true,
        Equipped = true,
        Enhance = true,
        Wishlist = true,
        Settings = true,
    },
    leveling = {
        ["Gear Guide"] = true,
        Equipped = true,
        Wishlist = true,
        Settings = true,
    },
}

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

local SPEC_NAME_ALIASES = {
    Druid = {
        ["feral combat"] = DEFAULT_SELECTED_SPEC,
    },
}

local TAB_NAME_ALIASES = {
    Phase = "By Slot",
    Gear = "Equipped",
    Planner = "Upgrades",
    Enhancements = "Enhance",
    ["BiS List"] = "By Slot",
    ["My Gear"] = "Equipped",
    Leveling = "Gear Guide",
}

local function normalizeTabName(tabName)
    return TAB_NAME_ALIASES[tabName] or tabName
end

local function normalizeContentMode(mode)
    if CONTENT_MODES[mode] then
        return mode
    end
    return DEFAULT_CONTENT_MODE
end

local function isEndgamePhaseKey(phaseKey)
    return ENDGAME_PHASE_KEYS[phaseKey] == true
end

local function tabIsValidForMode(tabName, mode)
    local normalizedMode = normalizeContentMode(mode)
    local normalizedTab = normalizeTabName(tabName)
    return MODE_TABS[normalizedMode][normalizedTab] == true
end

local function levelingTabFromLegacyTab(tabName)
    local normalizedTab = normalizeTabName(tabName)
    if tabIsValidForMode(normalizedTab, "leveling") then
        return normalizedTab
    end
    if normalizedTab == "Upgrades" or normalizedTab == "By Slot" or normalizedTab == "Enhance" then
        return MODE_DEFAULT_TABS.leveling
    end
    return nil
end

local VIEW_STATE_KEY_ALIASES = {
    upgrades = "upgrades",
    Upgrades = "upgrades",
    planner = "upgrades",
    Planner = "upgrades",
    bisList = "bisList",
    ["BiS List"] = "bisList",
    ["By Slot"] = "bisList",
    Phase = "bisList",
    gearGuide = "gearGuide",
    ["Gear Guide"] = "gearGuide",
    Leveling = "gearGuide",
    myGear = "myGear",
    ["My Gear"] = "myGear",
    Equipped = "myGear",
    Gear = "myGear",
    enhancements = "enhancements",
    Enhancements = "enhancements",
    Enhance = "enhancements",
    wishlist = "wishlist",
    Wishlist = "wishlist",
}

local function normalizeViewStateKey(viewName)
    return VIEW_STATE_KEY_ALIASES[viewName]
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
            inspectorVisible = false,
        },
        tooltips = {
            enabled = true,
            compact = true,
            selectedSpecFirst = true,
            showAllOnAlt = true,
            specFilters = {},
            specFiltersInitialized = false,
            collapsedClasses = {},
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
            phase = DEFAULT_ENDGAME_PHASE_KEY,
            mode = DEFAULT_CONTENT_MODE,
            tab = "Upgrades",
            lastTabs = {
                endgame = "Upgrades",
                leveling = "Gear Guide",
            },
        },
        leveling = {
            selectedLevel = MAX_LEVELING_LEVEL,
            lastDetectedLevel = 0,
            manualLevel = false,
        },
        filters = {
            search = "",
            sourceType = "all",
            sourceTypes = {},
            zone = "all",
            zones = {},
            cost = "all",
            costs = {},
            vendor = "all",
            vendors = {},
            reputation = "all",
            reputations = {},
            rankGroup = "all",
            rankGroups = {},
            ownedState = "all",
            upgradeMode = "actual",
            binding = "all",
            boe = "all",
            faction = "all",
            longevity = "all",
            slots = {},
        },
        viewState = {
            upgrades = {
                sort = "priority",
                sortDirection = "desc",
                upgradeMode = "actual",
                usefulness = "all",
            },
            bisList = {
                sort = "rank",
                sortDirection = "asc",
                groupBy = "slot",
            },
            gearGuide = {
                sort = "priority",
                sortDirection = "asc",
                groupBy = "slot",
                recommendationCategory = "all",
            },
            myGear = {
                sort = "slot",
                sortDirection = "asc",
            },
            enhancements = {
                sort = "recommendation",
                sortDirection = "asc",
                type = "all",
                appliedState = "all",
            },
            wishlist = {
                sort = "priority",
                sortDirection = "asc",
                relevance = "all",
            },
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

local function recoverEndgamePhase(char)
    local selection = char.selection or {}
    if isEndgamePhaseKey(selection.phase) then
        return selection.phase
    end
    if isEndgamePhaseKey(selection.endgamePhase) then
        return selection.endgamePhase
    end
    if isEndgamePhaseKey(char.selectedPhase) then
        return char.selectedPhase
    end
    if isEndgamePhaseKey(char.lastDetectedPhase) then
        return char.lastDetectedPhase
    end
    return DEFAULT_ENDGAME_PHASE_KEY
end

local function normalizeContentModeState(char)
    char.selection = char.selection or {}
    local selection = char.selection
    local legacyLevelingPhase = selection.phase == LEVELING_PHASE_KEY or char.selectedPhase == LEVELING_PHASE_KEY
    local mode = legacyLevelingPhase and "leveling" or normalizeContentMode(selection.mode)
    local activeTab = normalizeTabName(selection.tab or char.selectedTab)

    if type(selection.lastTabs) ~= "table" then
        selection.lastTabs = {}
    end

    local endgameTab = normalizeTabName(selection.lastTabs.endgame)
    if not tabIsValidForMode(endgameTab, "endgame") then
        endgameTab = MODE_DEFAULT_TABS.endgame
    end

    local levelingTab = levelingTabFromLegacyTab(selection.lastTabs.leveling)
    if not levelingTab then
        levelingTab = MODE_DEFAULT_TABS.leveling
    end

    if mode == "leveling" then
        activeTab = levelingTabFromLegacyTab(activeTab)
        if activeTab then
            levelingTab = activeTab
        end
    elseif tabIsValidForMode(activeTab, "endgame") then
        endgameTab = activeTab
    end

    selection.phase = recoverEndgamePhase(char)
    selection.endgamePhase = nil
    selection.mode = mode
    selection.lastTabs.endgame = endgameTab
    selection.lastTabs.leveling = levelingTab
    selection.tab = selection.lastTabs[mode]
end

local function migrateViewState(char, previousVersion)
    if previousVersion ~= nil and previousVersion >= 16 then
        return
    end

    local filters = char.filters
    local upgrades = char.viewState and char.viewState.upgrades
    if type(filters) ~= "table" or type(upgrades) ~= "table" then
        return
    end

    if filters.upgradeMode ~= nil then
        upgrades.upgradeMode = filters.upgradeMode
    end
    if filters.longevity ~= nil then
        upgrades.usefulness = filters.longevity
    end
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

local function ensureFacetTable(filters, tableKey)
    if type(filters[tableKey]) ~= "table" then
        filters[tableKey] = {}
    end
    return filters[tableKey]
end

local function migrateScalarFacetFilter(filters, scalarKey, tableKey)
    local selectedValue = filters[scalarKey]
    local selectedValues = ensureFacetTable(filters, tableKey)

    if selectedValue ~= nil and selectedValue ~= "all" and selectedValue ~= "" then
        selectedValues[selectedValue] = true
    end
    filters[scalarKey] = "all"
end

local function migrateFacetedFilters(char, previousVersion)
    if previousVersion ~= nil and previousVersion >= 12 then
        return
    end

    local filters = char and char.filters
    if type(filters) ~= "table" then
        return
    end

    migrateScalarFacetFilter(filters, "sourceType", "sourceTypes")
    migrateScalarFacetFilter(filters, "zone", "zones")
    migrateScalarFacetFilter(filters, "cost", "costs")
    migrateScalarFacetFilter(filters, "vendor", "vendors")
    migrateScalarFacetFilter(filters, "reputation", "reputations")
    migrateScalarFacetFilter(filters, "rankGroup", "rankGroups")
end

local clampLevel

local function migrateLevelingLevel(char)
    if type(char.leveling) ~= "table" then
        return
    end

    if char.leveling.selectedLevel ~= nil then
        char.leveling.selectedLevel = clampLevel(char.leveling.selectedLevel) or MAX_LEVELING_LEVEL
    end
    if char.leveling.lastDetectedLevel ~= nil then
        char.leveling.lastDetectedLevel = clampLevel(char.leveling.lastDetectedLevel) or 0
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

    local alias = SPEC_NAME_ALIASES[className] and SPEC_NAME_ALIASES[className][normalized]
    if alias then
        for _, spec in ipairs(specsForClass(className)) do
            if spec.name == alias then
                return spec.name
            end
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

    local detectedSpec = self:DetectPlayerSpec(className)

    return {
        class = className,
        spec = detectedSpec or firstSpecNameForClass(className),
        specDetected = detectedSpec ~= nil,
    }
end

function clampLevel(value)
    local level = tonumber(value)
    if not level then
        return nil
    end
    level = math.floor(level)
    if level < 1 then
        return 1
    elseif level > MAX_LEVELING_LEVEL then
        return MAX_LEVELING_LEVEL
    end
    return level
end

function BigBiSList:GetDetectedPlayerLevel()
    if UnitLevel then
        local ok, level = pcall(UnitLevel, "player")
        if ok then
            return clampLevel(level)
        end
    end
    return nil
end

function BigBiSList:ApplyDetectedPlayerLevel()
    self:EnsureDatabase()

    local char = BigBiSListCharDB
    char.leveling = char.leveling or {}
    local detectedLevel = self:GetDetectedPlayerLevel()
    if not detectedLevel then
        detectedLevel = clampLevel(char.leveling.selectedLevel) or MAX_LEVELING_LEVEL
    end

    local selectedLevel = clampLevel(char.leveling.selectedLevel)
    local changed = false
    if char.leveling.manualLevel ~= true and selectedLevel ~= detectedLevel then
        char.leveling.selectedLevel = detectedLevel
        changed = true
    elseif not selectedLevel then
        char.leveling.selectedLevel = detectedLevel
        changed = true
    end

    if char.leveling.lastDetectedLevel ~= detectedLevel then
        char.leveling.lastDetectedLevel = detectedLevel
        changed = true
    end

    return changed
end

function BigBiSList:GetSelectedLevelingLevel()
    self:EnsureDatabase()
    self:ApplyDetectedPlayerLevel()
    return clampLevel(BigBiSListCharDB.leveling and BigBiSListCharDB.leveling.selectedLevel) or MAX_LEVELING_LEVEL
end

function BigBiSList:SetSelectedLevelingLevel(level, manual)
    self:EnsureDatabase()
    BigBiSListCharDB.leveling = BigBiSListCharDB.leveling or {}
    BigBiSListCharDB.leveling.selectedLevel = clampLevel(level) or MAX_LEVELING_LEVEL
    if manual then
        BigBiSListCharDB.leveling.manualLevel = true
    end
end

local function syncSelectionAliases(char)
    char.selectedClass = char.selection.class
    char.selectedSpec = char.selection.spec
    char.selectedPhase = char.selection.phase
    char.selectedTab = char.selection.tab
end

local function setContentModeOnChar(char, requestedMode)
    normalizeContentModeState(char)

    local selection = char.selection
    local currentMode = selection.mode
    local targetMode = normalizeContentMode(requestedMode)
    local currentTab = normalizeTabName(selection.tab)
    if tabIsValidForMode(currentTab, currentMode) then
        selection.lastTabs[currentMode] = currentTab
    end

    selection.mode = targetMode
    selection.tab = selection.lastTabs[targetMode] or MODE_DEFAULT_TABS[targetMode]
end

local function applyDetectedPlayerSelection(char)
    if not char or BigBiSList.classSpecAutoSelectionActive == false then
        return false
    end

    local detected = BigBiSList:GetDetectedPlayerSelection()
    if not detected or not detected.class then
        return false
    end

    char.selection = char.selection or {}
    local changed = char.selection.class ~= detected.class
        or (detected.spec ~= nil and char.selection.spec ~= detected.spec)

    char.selection.class = detected.class
    char.selectedClass = detected.class

    if detected.spec then
        char.selection.spec = detected.spec
        char.selectedSpec = detected.spec
    end

    return changed
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

function BigBiSList:MarkClassSpecSelectionManual()
    self.classSpecAutoSelectionActive = false
end

function BigBiSList:ResetClassSpecAutoSelection()
    self.classSpecAutoSelectionActive = true
end

function BigBiSList:ApplyDetectedPlayerSelection()
    self:EnsureDatabase()

    local changed = applyDetectedPlayerSelection(BigBiSListCharDB)
    if changed then
        syncSelectionAliases(BigBiSListCharDB)
    end

    return changed
end

function BigBiSList:ApplyDetectedDefaultSelection()
    return self:ApplyDetectedPlayerSelection()
end

function BigBiSList:GetSelection()
    self:EnsureDatabase()
    return BigBiSListCharDB.selection
end

function BigBiSList:GetContentMode()
    self:EnsureDatabase()
    return BigBiSListCharDB.selection.mode
end

function BigBiSList:SetContentMode(mode)
    self:EnsureDatabase()

    if not CONTENT_MODES[mode] then
        return false
    end

    local selection = BigBiSListCharDB.selection
    local previousMode = selection.mode
    local previousTab = selection.tab
    setContentModeOnChar(BigBiSListCharDB, mode)
    syncSelectionAliases(BigBiSListCharDB)

    return selection.mode ~= previousMode or selection.tab ~= previousTab
end

function BigBiSList:GetEffectivePhaseKey(selection)
    if selection == nil then
        self:EnsureDatabase()
        selection = BigBiSListCharDB.selection
    end

    if selection.mode == "leveling" or selection.phase == LEVELING_PHASE_KEY then
        return LEVELING_PHASE_KEY
    end
    if isEndgamePhaseKey(selection.phase) then
        return selection.phase
    end
    return DEFAULT_ENDGAME_PHASE_KEY
end

function BigBiSList:GetViewState(viewName)
    self:EnsureDatabase()

    if viewName == nil then
        viewName = BigBiSListCharDB.selection.tab
    end
    local viewKey = normalizeViewStateKey(viewName)
    return viewKey and BigBiSListCharDB.viewState[viewKey] or nil
end

function BigBiSList:IsInspectorVisible()
    self:EnsureDatabase()
    return BigBiSListDB.profile.window.inspectorVisible == true
end

function BigBiSList:SetInspectorVisible(visible)
    self:EnsureDatabase()
    BigBiSListDB.profile.window.inspectorVisible = visible ~= false
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
        if phaseKey == LEVELING_PHASE_KEY then
            setContentModeOnChar(BigBiSListCharDB, "leveling")
        elseif isEndgamePhaseKey(phaseKey) then
            selection.phase = phaseKey
        end
    end
    if tabName then
        local normalizedTab = normalizeTabName(tabName)
        if tabIsValidForMode(normalizedTab, selection.mode) then
            selection.tab = normalizedTab
            selection.lastTabs[selection.mode] = normalizedTab
        end
    end

    syncSelectionAliases(BigBiSListCharDB)
end

function BigBiSList:GetCharacterDB()
    self:EnsureDatabase()
    return BigBiSListCharDB
end

local initializedAccountDB
local initializedProfileDB
local initializedCharacterDB

local function databaseInitializationIsCurrent(addon)
    local accountDB = BigBiSListDB
    local profileDB = type(accountDB) == "table" and accountDB.profile or nil
    local characterDB = BigBiSListCharDB

    if accountDB ~= initializedAccountDB
        or profileDB ~= initializedProfileDB
        or characterDB ~= initializedCharacterDB then
        return false
    end
    if type(profileDB) ~= "table"
        or type(characterDB) ~= "table"
        or profileDB.defaultsVersion ~= DEFAULTS_VERSION
        or characterDB.defaultsVersion ~= DEFAULTS_VERSION
        or accountDB.char ~= nil then
        return false
    end

    local tooltips = profileDB.tooltips
    if addon.GetClassSpecIndex
        and (type(tooltips) ~= "table" or tooltips.specFiltersInitialized ~= true) then
        return false
    end
    return true
end

function BigBiSList:EnsureDatabase()
    local accountDB = BigBiSListDB
    if databaseInitializationIsCurrent(self) then
        return accountDB
    end

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
    normalizeContentModeState(BigBiSListCharDB)
    migrateViewState(BigBiSListCharDB, charPreviousVersion)
    migrateTooltipSpecFilterDefaults(BigBiSListDB, profilePreviousVersion)
    migrateSplitDropSourceFilter(BigBiSListCharDB, charPreviousVersion)
    migrateFacetedFilters(BigBiSListCharDB, charPreviousVersion)
    migrateLevelingLevel(BigBiSListCharDB)
    BigBiSListCharDB.manualClassSpecSelection = nil
    ensureTooltipSpecFilters(BigBiSListDB)

    syncSelectionAliases(BigBiSListCharDB)
    BigBiSListDB.profile.defaultsVersion = DEFAULTS_VERSION
    BigBiSListCharDB.defaultsVersion = DEFAULTS_VERSION

    initializedAccountDB = BigBiSListDB
    initializedProfileDB = BigBiSListDB.profile
    initializedCharacterDB = BigBiSListCharDB

    return BigBiSListDB
end
