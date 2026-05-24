-- BIS-TBC: Modern BiS List UI
-- Custom frame implementation (no AceGUI dependency)

local selectedClass = nil
local selectedSpec = nil
local selectedPhase = nil
local selectedClassIndex = nil
local selectedSpecIndex = nil
local selectedPhaseIndex = nil
local selectedSourceFilterIndex = 1
local selectedZoneIndex = 1
local selectedTab = "Items"
local searchText = ""
local customEditMode = false
local selectedSlotFilter = {} -- set of slot names, empty = show all
local farmExcludedZones = {} -- zone names to hide on Farm tab

local mainFrame = nil
local scrollChild = nil
local scrollFrame = nil
local contentRows = {}
local itemCache = {}

local phases = { "Pre-Raid", "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5" }
local phaseKeys = { "PR", "T4", "T5", "T6", "ZA", "SWP" }

local sourceFilters = { "All", "Drop", "Vendor", "Quest", "Crafted", "PvP" }

-- Forward declarations
local onClassChanged, onSpecChanged, onPhaseChanged, onSourceFilterChanged, onZoneChanged
local renderContent, renderGems, renderEnchants, renderConsumables, renderCustomList, renderFarm, renderCredits, clearContent, switchTab
local showUpgradePanel, hideUpgradePanel, addGlowToIcon

-- Rank glow configuration (gold #1, silver #2, bronze #3)
local RANK_GLOW = {
    [1] = { r = 1.0, g = 0.82, b = 0, duration = 0.8, minAlpha = 0.5, maxAlpha = 1.0 },
    [2] = { r = 0.75, g = 0.75, b = 0.78, duration = 1.2, minAlpha = 0.4, maxAlpha = 0.85 },
    [3] = { r = 0.80, g = 0.50, b = 0.20, duration = 1.6, minAlpha = 0.3, maxAlpha = 0.7 },
}

-- Tab-specific UI elements
local tabButtons = {}
local zoneDropdown, searchBox, searchBoxFrame
local itemsTabControls = {}
local levelingPanel, levelingStatsText, levelingSuffixesText
local editButton
local farmFilterButton, farmFilterMenu
local slotPanel, slotButtons, rangedSlotButton

-- Categorize a source string into a filter category
local function getSourceCategory(source)
    if not source or source == "" then return "Drop" end
    if source:find("^Vendor") then return "Vendor" end
    if source:find("^Quest") then return "Quest" end
    if source:find("^Crafted") then return "Crafted" end
    if source == "PvP" then return "PvP" end
    return "Drop"
end

-- Extract zone name from source string (e.g. "Prince Malchezaar - Karazhan" -> "Karazhan")
local function getSourceZone(source)
    if not source or source == "" then return nil end
    local zone = source:match(" %- (.+)$")
    if zone then return zone end
    if source:find("^Zone drop %- ") then return source:match("^Zone drop %- (.+)$") end
    return nil
end

local function getItemSource(itemId)
    if BISTBC_sources and BISTBC_sources[itemId] then
        return BISTBC_sources[itemId].source or "Unknown"
    end
    return ""
end

local function getItemName(itemId)
    if BISTBC_sources and BISTBC_sources[itemId] then
        return BISTBC_sources[itemId].name
    end
    return nil
end

local function getItemDropRate(itemId)
    if BISTBC_sources and BISTBC_sources[itemId] then
        return BISTBC_sources[itemId].drop
    end
    return nil
end

local function getItemTokenId(itemId)
    if BISTBC_sources and BISTBC_sources[itemId] then
        return BISTBC_sources[itemId].token_id, BISTBC_sources[itemId].token_count
    end
    return nil, nil
end

-- Wowhead currency IDs that aren't real in-game items
local function getPvpCurrencyIcon(tokenId)
    if tokenId == 1900 then
        return "Interface\\PVPFrame\\PVP-ArenaPoints-Icon"
    elseif tokenId == 1901 then
        local _, faction = UnitFactionGroup("player")
        return "Interface\\PVPFrame\\PVP-Currency-" .. (faction or "Alliance")
    end
end

-- Build sorted zone list from current spec/phase items
local zoneList = { "All" }
local function buildZoneFilters()
    wipe(zoneList)
    zoneList[1] = "All"
    selectedZoneIndex = 1

    if not selectedClass or not selectedSpec or not selectedPhaseIndex then return end
    local phaseKey = phaseKeys[selectedPhaseIndex]
    local bislists = BISTBC_bislists and BISTBC_bislists[selectedClass]
    if not bislists then return end
    local specData = bislists[selectedSpec]
    if not specData then return end
    local slots = specData[phaseKey]
    if not slots then return end

    local zones = {}
    for _, slot in ipairs(slots) do
        for rank = 1, 5 do
            local itemEntry = slot[rank]
            if itemEntry then
                local itemId = type(itemEntry) == "table" and itemEntry.id or itemEntry
                if itemId and itemId > 0 then
                    local sourceStr = getItemSource(itemId)
                    local zone = getSourceZone(sourceStr)
                    if zone and not zones[zone] then
                        zones[zone] = true
                    end
                end
            end
        end
    end

    local sorted = {}
    for zone in pairs(zones) do
        table.insert(sorted, zone)
    end
    table.sort(sorted)
    for _, zone in ipairs(sorted) do
        table.insert(zoneList, zone)
    end
end

-- ============================================================================
-- Leveling data: stat priorities and recommended suffixes per class/spec
-- ============================================================================

local LEVELING_DATA = {
    ["Druid"] = {
        ["Balance"]      = { stats = "Spell Hit > Spell Power > Spell Crit > Spell Haste",       suffixes = "of the Invoker, of the Sorcerer, of [School] Wrath" },
        ["Feral tank"]   = { stats = "Def + Resil > Armor / Stamina > Expertise / Hit > Agility", suffixes = "of the Beast, of the Bandit, of the Monkey" },
        ["Feral dps"]    = { stats = "Agility > Hit Rating > Expertise > Strength",               suffixes = "of the Bandit, of the Monkey, of the Soldier" },
        ["Restoration"]  = { stats = "Healing Power > Spirit > Intellect > MP5",                   suffixes = "of the Hierophant, of Healing, of the Physician" },
    },
    ["Hunter"] = {
        ["Beast mastery"] = { stats = "Hit Rating > Agility > Crit Rating > Attack Power", suffixes = "of the Bandit, of the Falcon, of Agility" },
        ["Marksmanship"]  = { stats = "Hit Rating > Agility > Crit Rating > Attack Power", suffixes = "of the Bandit, of the Falcon, of Agility" },
        ["Survival"]      = { stats = "Hit Rating > Agility > Crit Rating > Attack Power", suffixes = "of Agility, of the Bandit, of the Falcon" },
    },
    ["Mage"] = {
        ["Arcane"] = { stats = "Spell Hit > Spell Power > Spell Haste > Spell Crit", suffixes = "of the Sorcerer, of the Invoker, of [School] Wrath" },
        ["Fire"]   = { stats = "Spell Hit > Spell Power > Spell Haste > Spell Crit", suffixes = "of the Sorcerer, of the Invoker, of [School] Wrath" },
        ["Frost"]  = { stats = "Spell Hit > Spell Power > Spell Haste > Spell Crit", suffixes = "of the Sorcerer, of the Invoker, of [School] Wrath" },
    },
    ["Paladin"] = {
        ["Holy"]        = { stats = "Healing Power > Intellect > Spell Crit > MP5",          suffixes = "of the Physician, of the Hierophant, of Healing" },
        ["Protection"]  = { stats = "Defense (490) > Stamina > Spell Power > Avoidance",     suffixes = "of the Champion, of the Sorcerer, of Stamina" },
        ["Retribution"] = { stats = "Expertise (6.5%) > Hit (9%) > Strength > Crit Rating",  suffixes = "of the Soldier, of the Bandit, of Strength" },
    },
    ["Priest"] = {
        ["Holy"]   = { stats = "Healing Power > Spirit > Intellect > MP5",    suffixes = "of the Prophet, of the Physician, of Healing" },
        ["Shadow"] = { stats = "Spell Power > Intellect > Spell Crit",        suffixes = "of the Invoker, of Shadow Wrath, of the Prophet" },
    },
    ["Rogue"] = {
        ["Assassination"] = { stats = "Hit Rating > Expertise > Agility > Strength / AP", suffixes = "of the Bandit, of the Monkey, of the Soldier" },
        ["Combat"]        = { stats = "Hit Rating > Expertise > Agility > Strength / AP", suffixes = "of the Bandit, of the Monkey, of the Soldier" },
        ["Subtlety"]      = { stats = "Hit Rating > Expertise > Agility > Strength / AP", suffixes = "of the Bandit, of the Monkey, of the Soldier" },
    },
    ["Shaman"] = {
        ["Elemental"]   = { stats = "Spell Hit > Spell Power > Spell Crit > Intellect",       suffixes = "of the Invoker, of the Sorcerer, of Nature's Wrath" },
        ["Enhancement"] = { stats = "Hit Rating > Expertise > Strength > Crit / Agility",     suffixes = "of the Bandit, of the Soldier, of Strength" },
        ["Restoration"] = { stats = "Healing Power > MP5 > Intellect > Spell Haste",          suffixes = "of the Physician, of Healing, of the Hierophant" },
    },
    ["Warlock"] = {
        ["Affliction"]        = { stats = "Spell Hit > Spell Haste > Spell Power > Spell Crit", suffixes = "of the Sorcerer, of [School] Wrath, of the Invoker" },
        ["Demonology"]        = { stats = "Spell Hit > Spell Haste > Spell Power > Spell Crit", suffixes = "of the Sorcerer, of [School] Wrath, of the Invoker" },
        ["Destruction"]       = { stats = "Spell Hit > Spell Haste > Spell Power > Spell Crit", suffixes = "of the Sorcerer, of [School] Wrath, of the Invoker" },
        ["Destruction fire"]  = { stats = "Spell Hit > Spell Haste > Spell Power > Spell Crit", suffixes = "of the Sorcerer, of [School] Wrath, of the Invoker" },
    },
    ["Warrior"] = {
        ["Arms"]       = { stats = "Hit (9%) > Expertise (6.5%) > Crit Rating > Strength",   suffixes = "of the Soldier, of the Bandit, of Strength" },
        ["Fury"]       = { stats = "Hit (9%) > Expertise (6.5%) > Crit Rating > Strength",   suffixes = "of the Soldier, of the Bandit, of Strength" },
        ["Protection"] = { stats = "Defense (490) > Stamina > Expertise > Avoidance",         suffixes = "of the Champion, of Defense, of the Bear" },
    },
}

-- Class colors (standard WoW)
local CLASS_COLORS = {
    ["Druid"]   = { r = 1.00, g = 0.49, b = 0.04 },
    ["Hunter"]  = { r = 0.67, g = 0.83, b = 0.45 },
    ["Mage"]    = { r = 0.25, g = 0.78, b = 0.92 },
    ["Paladin"] = { r = 0.96, g = 0.55, b = 0.73 },
    ["Priest"]  = { r = 1.00, g = 1.00, b = 1.00 },
    ["Rogue"]   = { r = 1.00, g = 0.96, b = 0.41 },
    ["Shaman"]  = { r = 0.00, g = 0.44, b = 0.87 },
    ["Warlock"] = { r = 0.53, g = 0.53, b = 0.93 },
    ["Warrior"] = { r = 0.78, g = 0.61, b = 0.43 },
}

-- Slot display order
local SLOT_ORDER = {
    "Head", "Neck", "Shoulder", "Back", "Chest", "Wrist",
    "Hands", "Waist", "Legs", "Feet", "Ring", "Trinket",
    "Main Hand", "Off Hand", "Two Hand", "Dual Wield", "Ranged", "Idol", "Totem", "Libram", "Relic"
}

-- Enchant slot display order
local ENCHANT_SLOT_ORDER = {
    "Head", "Shoulder", "Back", "Chest", "Wrist", "Hands",
    "Waist", "Legs", "Feet", "Ring", "Main Hand", "Off Hand",
    "Two Hand", "Ranged/Relic", "Shoulder~Legs"
}

-- ============================================================================
-- Utility functions
-- ============================================================================

local function getClassColor(className)
    local c = CLASS_COLORS[className]
    if c then return c.r, c.g, c.b end
    return 1, 0.82, 0
end

-- Build a set of item IDs the player currently owns (equipped + bags + bank)
local ownedItems = {}
local function buildOwnedItems()
    wipe(ownedItems)
    for slot = 1, 19 do
        local id = GetInventoryItemID("player", slot)
        if id then ownedItems[id] = "equipped" end
    end
    for bag = 0, 4 do
        local numSlots = 0
        if C_Container and C_Container.GetContainerNumSlots then
            numSlots = C_Container.GetContainerNumSlots(bag) or 0
        elseif GetContainerNumSlots then
            numSlots = GetContainerNumSlots(bag) or 0
        end
        for slot = 1, numSlots do
            local id
            if C_Container and C_Container.GetContainerItemID then
                id = C_Container.GetContainerItemID(bag, slot)
            elseif GetContainerItemID then
                id = GetContainerItemID(bag, slot)
            end
            if id then ownedItems[id] = ownedItems[id] or "bag" end
        end
    end
end

-- Check if item name matches search pattern
local function matchesSearch(itemId)
    if not searchText or searchText == "" then return true end
    local name = getItemName(itemId)
    if not name then
        local _, link = GetItemInfo(itemId)
        if link then name = link:match("%[(.-)%]") end
    end
    if not name then return true end -- show items we can't check yet
    local pattern = searchText:lower():gsub("%s+", ".*")
    return name:lower():find(pattern) ~= nil
end

-- ============================================================================
-- Frame creation helpers
-- ============================================================================

local function createBackdropFrame(name, parent, r, g, b, a, edgeR, edgeG, edgeB, edgeA)
    local f = CreateFrame("Frame", name, parent, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    f:SetBackdropColor(r or 0.06, g or 0.06, b or 0.06, a or 0.95)
    f:SetBackdropBorderColor(edgeR or 0.25, edgeG or 0.25, edgeB or 0.25, edgeA or 1)
    return f
end

-- ============================================================================
-- Custom flat dropdown (matches tab button style)
-- ============================================================================

local activeDropdownMenu = nil -- track currently open menu to close on outside click

local dropdownCount = 0
local function createDropdown(parent, width, items, selectedIndex, onChange)
    dropdownCount = dropdownCount + 1

    local btn = createBackdropFrame("BISTBCDropdown" .. dropdownCount, parent, 0.10, 0.10, 0.10, 0.9, 0.25, 0.25, 0.25, 1)
    btn:SetSize(width + 24, 22)
    btn:EnableMouse(true)

    local label = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", btn, "LEFT", 8, 0)
    label:SetPoint("RIGHT", btn, "RIGHT", -16, 0)
    label:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    label:SetTextColor(0.85, 0.85, 0.85, 1)
    label:SetJustifyH("LEFT")
    label:SetWordWrap(false)

    local arrow = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    arrow:SetPoint("RIGHT", btn, "RIGHT", -5, 0)
    arrow:SetFont("Fonts\\FRIZQT__.TTF", 9, "")
    arrow:SetTextColor(0.5, 0.5, 0.5, 1)
    arrow:SetText("\226\150\188") -- down triangle

    -- Store state on the button
    btn.items = items
    btn.selectedIndex = selectedIndex or 1
    btn.onChange = onChange
    btn.label = label

    if items[btn.selectedIndex] then
        label:SetText(items[btn.selectedIndex])
    end

    -- Dropdown menu frame (created once, reused)
    local menu = createBackdropFrame(nil, UIParent, 0.08, 0.08, 0.08, 0.97, 0.30, 0.30, 0.30, 1)
    menu:SetFrameStrata("FULLSCREEN_DIALOG")
    menu:SetClampedToScreen(true)
    menu:Hide()
    btn.menu = menu

    local function buildMenu()
        -- Clear old children
        for _, child in ipairs({menu:GetChildren()}) do
            child:Hide()
            child:SetParent(nil)
        end

        local rowH = 20
        local menuWidth = btn:GetWidth()
        local totalH = #btn.items * rowH + 4

        menu:SetSize(menuWidth, totalH)

        local point, _, relPoint, x, y = btn:GetPoint()
        menu:ClearAllPoints()
        menu:SetPoint("TOPLEFT", btn, "BOTTOMLEFT", 0, -2)

        for i, itemText in ipairs(btn.items) do
            local row = CreateFrame("Frame", nil, menu)
            row:SetSize(menuWidth - 2, rowH)
            row:SetPoint("TOPLEFT", menu, "TOPLEFT", 1, -((i - 1) * rowH + 2))
            row:EnableMouse(true)

            local rowLabel = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
            rowLabel:SetPoint("LEFT", row, "LEFT", 8, 0)
            rowLabel:SetPoint("RIGHT", row, "RIGHT", -8, 0)
            rowLabel:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
            rowLabel:SetJustifyH("LEFT")
            rowLabel:SetWordWrap(false)
            rowLabel:SetText(itemText)

            if i == btn.selectedIndex then
                rowLabel:SetTextColor(1, 0.82, 0, 1)
                local selBg = row:CreateTexture(nil, "BACKGROUND")
                selBg:SetAllPoints()
                selBg:SetColorTexture(0.20, 0.20, 0.22, 0.8)
            else
                rowLabel:SetTextColor(0.80, 0.80, 0.80, 1)
            end

            local highlight = row:CreateTexture(nil, "BACKGROUND", nil, 1)
            highlight:SetAllPoints()
            highlight:SetColorTexture(1, 1, 1, 0.08)
            highlight:Hide()

            row:SetScript("OnEnter", function() highlight:Show() end)
            row:SetScript("OnLeave", function() highlight:Hide() end)
            row:SetScript("OnMouseUp", function(self, button)
                if button == "LeftButton" then
                    btn.selectedIndex = i
                    label:SetText(itemText)
                    menu:Hide()
                    activeDropdownMenu = nil
                    if btn.onChange then btn.onChange(i) end
                end
            end)
        end
    end

    btn:SetScript("OnMouseUp", function(self, button)
        if button == "LeftButton" then
            if menu:IsShown() then
                menu:Hide()
                activeDropdownMenu = nil
            else
                -- Close any other open dropdown
                if activeDropdownMenu and activeDropdownMenu ~= menu then
                    activeDropdownMenu:Hide()
                end
                buildMenu()
                menu:Show()
                activeDropdownMenu = menu
            end
        end
    end)

    btn:SetScript("OnEnter", function(self)
        self:SetBackdropColor(0.15, 0.15, 0.15, 0.9)
    end)
    btn:SetScript("OnLeave", function(self)
        self:SetBackdropColor(0.10, 0.10, 0.10, 0.9)
    end)

    return btn
end

-- Reinitialize a dropdown with new items
local function reinitDropdown(dropdown, items, selectedIndex, onChange)
    dropdown.items = items
    dropdown.selectedIndex = selectedIndex or 1
    if onChange then dropdown.onChange = onChange end
    if items[dropdown.selectedIndex] then
        dropdown.label:SetText(items[dropdown.selectedIndex])
    end
    if dropdown.menu and dropdown.menu:IsShown() then
        dropdown.menu:Hide()
        activeDropdownMenu = nil
    end
end

-- ============================================================================
-- Tab button creation
-- ============================================================================

local function createTabButton(parent, text, xOffset, onClick)
    local btn = createBackdropFrame(nil, parent, 0.10, 0.10, 0.10, 0.9, 0.25, 0.25, 0.25, 1)
    btn:SetSize(68, 22)
    btn:SetPoint("TOPLEFT", parent, "TOPLEFT", xOffset, 0)
    btn:EnableMouse(true)

    local label = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("CENTER", btn, "CENTER", 0, 0)
    label:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    label:SetTextColor(0.7, 0.7, 0.7, 1)
    label:SetText(text)
    btn.label = label

    btn:SetScript("OnMouseUp", function(self, button)
        if button == "LeftButton" then onClick() end
    end)

    btn:SetScript("OnEnter", function(self)
        if self.isActive then return end
        self:SetBackdropColor(0.15, 0.15, 0.15, 0.9)
    end)
    btn:SetScript("OnLeave", function(self)
        if self.isActive then return end
        self:SetBackdropColor(0.10, 0.10, 0.10, 0.9)
    end)

    btn.SetActive = function(self, active)
        self.isActive = active
        if active then
            self:SetBackdropColor(0.20, 0.20, 0.22, 1)
            self:SetBackdropBorderColor(0.8, 0.65, 0, 0.8)
            self.label:SetTextColor(1, 0.82, 0, 1)
        else
            self:SetBackdropColor(0.10, 0.10, 0.10, 0.9)
            self:SetBackdropBorderColor(0.25, 0.25, 0.25, 1)
            self.label:SetTextColor(0.7, 0.7, 0.7, 1)
        end
    end

    return btn
end

-- ============================================================================
-- Paper doll slot panel
-- ============================================================================

-- Slot icon textures (empty slot icons from WoW)
local SLOT_TEXTURES = {
    ["Head"]      = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Head",
    ["Neck"]      = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Neck",
    ["Shoulder"]  = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Shoulder",
    ["Back"]      = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Chest",
    ["Chest"]     = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Chest",
    ["Wrist"]     = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Wrists",
    ["Hands"]     = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Hands",
    ["Waist"]     = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Waist",
    ["Legs"]      = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Legs",
    ["Feet"]      = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Feet",
    ["Ring"]      = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Finger",
    ["Trinket"]   = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Trinket",
    ["Main Hand"] = "Interface\\PaperDoll\\UI-PaperDoll-Slot-MainHand",
    ["Off Hand"]  = "Interface\\PaperDoll\\UI-PaperDoll-Slot-SecondaryHand",
    ["Two Hand"]   = "Interface\\PaperDoll\\UI-PaperDoll-Slot-MainHand",
    ["Dual Wield"] = "Interface\\PaperDoll\\UI-PaperDoll-Slot-MainHand",
    ["Ranged"]    = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Ranged",
    ["Idol"]      = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Relic",
    ["Totem"]     = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Relic",
    ["Libram"]    = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Relic",
    ["Relic"]     = "Interface\\PaperDoll\\UI-PaperDoll-Slot-Relic",
}

-- Paper doll layout: left column, right column, bottom row
local PAPERDOLL_LEFT  = { "Head", "Neck", "Shoulder", "Back", "Chest", "Wrist" }
local PAPERDOLL_RIGHT = { "Hands", "Waist", "Legs", "Feet", "Ring", "Trinket" }
local PAPERDOLL_BOTTOM = { "Main Hand", "Off Hand" }

-- Class-specific relic slots (classes that don't use ranged weapons)
local CLASS_RELIC_SLOT = {
    ["Druid"]   = "Idol",
    ["Paladin"] = "Libram",
    ["Shaman"]  = "Totem",
}

local SLOT_SIZE = 30
local SLOT_GAP = 2

local function createSlotButton(parent, slotName, x, y)
    local btn = CreateFrame("Button", nil, parent)
    btn:SetSize(SLOT_SIZE, SLOT_SIZE)
    btn:SetPoint("TOPLEFT", parent, "TOPLEFT", x, -y)

    -- Background
    local bg = btn:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    bg:SetColorTexture(0.08, 0.08, 0.08, 0.9)

    -- Slot icon
    local icon = btn:CreateTexture(nil, "ARTWORK")
    icon:SetSize(SLOT_SIZE - 4, SLOT_SIZE - 4)
    icon:SetPoint("CENTER")
    icon:SetTexture(SLOT_TEXTURES[slotName] or "Interface\\PaperDoll\\UI-PaperDoll-Slot-Bag")
    icon:SetDesaturated(true)
    icon:SetAlpha(0.5)

    -- Border (highlight when selected)
    local border = btn:CreateTexture(nil, "OVERLAY")
    border:SetPoint("TOPLEFT", -1, 1)
    border:SetPoint("BOTTOMRIGHT", 1, -1)
    border:SetColorTexture(0.8, 0.65, 0, 0.8)
    border:Hide()

    -- Hover highlight
    local highlight = btn:CreateTexture(nil, "HIGHLIGHT")
    highlight:SetAllPoints()
    highlight:SetColorTexture(1, 1, 1, 0.15)

    btn.icon = icon
    btn.border = border
    btn.slotName = slotName
    btn.defaultTexture = SLOT_TEXTURES[slotName] or "Interface\\PaperDoll\\UI-PaperDoll-Slot-Bag"

    local function updateSlotVisuals()
        for _, sbtn in pairs(slotButtons) do
            if selectedSlotFilter[sbtn.slotName] then
                sbtn.border:Show()
                sbtn.icon:SetDesaturated(false)
                sbtn.icon:SetAlpha(1)
            else
                sbtn.border:Hide()
                sbtn.icon:SetDesaturated(true)
                sbtn.icon:SetAlpha(0.5)
            end
        end
    end

    btn:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    btn:SetScript("OnClick", function(self, button)
        if button == "RightButton" then
            -- Remove from filter
            selectedSlotFilter[self.slotName] = nil
        elseif IsShiftKeyDown() then
            -- Toggle add to filter
            if selectedSlotFilter[self.slotName] then
                selectedSlotFilter[self.slotName] = nil
            else
                selectedSlotFilter[self.slotName] = true
            end
        else
            -- Solo select: if already the only one selected, deselect all
            if selectedSlotFilter[self.slotName] and next(selectedSlotFilter) == self.slotName and next(selectedSlotFilter, self.slotName) == nil then
                wipe(selectedSlotFilter)
            else
                wipe(selectedSlotFilter)
                selectedSlotFilter[self.slotName] = true
            end
        end
        updateSlotVisuals()
        renderContent()
    end)

    btn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(self.slotName, 1, 0.82, 0)
        if self.bisRank then
            local config = RANK_GLOW[self.bisRank]
            if config then
                GameTooltip:AddLine("BiS #" .. self.bisRank, config.r, config.g, config.b)
            else
                GameTooltip:AddLine("BiS #" .. self.bisRank, 0.5, 0.5, 0.5)
            end
        end
        GameTooltip:Show()
        -- Show upgrade panel if equipped item is ranked #2+
        if self.bisSlotData and self.bisRank and self.bisRank > 1 then
            showUpgradePanel(self.bisSlotData, self.bisRank)
        else
            hideUpgradePanel()
        end
    end)
    btn:SetScript("OnLeave", function(self)
        GameTooltip:Hide()
        hideUpgradePanel()
    end)

    return btn
end

local function createPaperDollPanel(parent)
    slotPanel = createBackdropFrame(nil, parent, 0.06, 0.06, 0.06, 0.8, 0.18, 0.18, 0.18, 0.6)
    local panelWidth = SLOT_SIZE * 2 + SLOT_GAP * 3
    slotPanel:SetSize(panelWidth, 1) -- height set dynamically

    slotButtons = {}

    local yOff = SLOT_GAP

    -- Left column
    for i, slotName in ipairs(PAPERDOLL_LEFT) do
        local btn = createSlotButton(slotPanel, slotName, SLOT_GAP, yOff)
        slotButtons[slotName] = btn
        yOff = yOff + SLOT_SIZE + SLOT_GAP
    end

    -- Right column
    yOff = SLOT_GAP
    for i, slotName in ipairs(PAPERDOLL_RIGHT) do
        local btn = createSlotButton(slotPanel, slotName, SLOT_SIZE + SLOT_GAP * 2, yOff)
        slotButtons[slotName] = btn
        yOff = yOff + SLOT_SIZE + SLOT_GAP
    end

    -- Bottom row (centered)
    local bottomY = (#PAPERDOLL_LEFT) * (SLOT_SIZE + SLOT_GAP) + SLOT_GAP
    local bottomCount = #PAPERDOLL_BOTTOM
    local bottomWidth = bottomCount * SLOT_SIZE + (bottomCount - 1) * SLOT_GAP
    local bottomStartX = math.floor((panelWidth - bottomWidth) / 2)

    for i, slotName in ipairs(PAPERDOLL_BOTTOM) do
        local btn = createSlotButton(slotPanel, slotName, bottomStartX + (i - 1) * (SLOT_SIZE + SLOT_GAP), bottomY)
        slotButtons[slotName] = btn
    end

    -- Ranged/Relic slot centered below weapons
    local relicY = bottomY + SLOT_SIZE + SLOT_GAP
    local relicX = math.floor((panelWidth - SLOT_SIZE) / 2)
    local relicBtn = createSlotButton(slotPanel, "Ranged", relicX, relicY)
    slotButtons["Ranged"] = relicBtn
    rangedSlotButton = relicBtn

    local totalH = relicY + SLOT_SIZE + SLOT_GAP
    slotPanel:SetSize(panelWidth, totalH)

    return slotPanel
end

-- Update paper doll ranged/relic slot based on selected class
local function updatePaperDollSlots()
    if not rangedSlotButton then return end

    local newSlot = "Ranged"
    if selectedClass and CLASS_RELIC_SLOT[selectedClass] then
        newSlot = CLASS_RELIC_SLOT[selectedClass]
    end

    local oldSlot = rangedSlotButton.slotName
    if oldSlot ~= newSlot then
        slotButtons[oldSlot] = nil
        rangedSlotButton.slotName = newSlot
        slotButtons[newSlot] = rangedSlotButton
        rangedSlotButton.defaultTexture = SLOT_TEXTURES[newSlot] or "Interface\\PaperDoll\\UI-PaperDoll-Slot-Relic"

        if selectedSlotFilter[oldSlot] then
            selectedSlotFilter[oldSlot] = nil
            rangedSlotButton.border:Hide()
        end
    end
end

-- Update paper doll icons with equipped BIS item icons + rank glow
local paperDollGlows = {}

local function updatePaperDollIcons()
    if not slotButtons then return end

    updatePaperDollSlots()

    -- Remove old glow frames
    for _, glowFrame in ipairs(paperDollGlows) do
        glowFrame:Hide()
        glowFrame:SetParent(nil)
    end
    wipe(paperDollGlows)

    -- Reset all to default textures and clear slot data
    for sName, btn in pairs(slotButtons) do
        btn.icon:SetTexture(btn.defaultTexture or SLOT_TEXTURES[sName])
        btn.icon:SetTexCoord(0, 1, 0, 1)
        btn.bisRank = nil
        btn.bisSlotData = nil
        if not next(selectedSlotFilter) or selectedSlotFilter[sName] then
            btn.icon:SetDesaturated(false)
            btn.icon:SetAlpha(1)
        else
            btn.icon:SetDesaturated(true)
            btn.icon:SetAlpha(0.5)
        end
    end

    -- Find equipped BIS items and show their icons
    buildOwnedItems()

    if not selectedClass or not selectedSpec or not selectedPhaseIndex then return end

    local phaseKey = phaseKeys[selectedPhaseIndex]
    local bislists = BISTBC_bislists and BISTBC_bislists[selectedClass]
    if not bislists then return end
    local specData = bislists[selectedSpec]
    if not specData then return end
    local slots = specData[phaseKey]
    if not slots then return end

    for _, slot in ipairs(slots) do
        -- Map "Two Hand" / "Dual Wield" data to the Main Hand paper doll button
        local pdSlotName = (slot.slot_name == "Two Hand" or slot.slot_name == "Dual Wield") and "Main Hand" or slot.slot_name
        local btn = slotButtons[pdSlotName]
        if btn then
            btn.bisSlotData = slot -- store for upgrade panel on hover
            for rank = 1, 5 do
                local itemEntry = slot[rank]
                if itemEntry then
                    local itemId = type(itemEntry) == "table" and itemEntry.id or itemEntry
                    if itemId and itemId > 0 and ownedItems[itemId] == "equipped" then
                        btn.bisRank = rank -- store equipped rank
                        local item = Item:CreateFromItemID(itemId)
                        item:ContinueOnItemLoad(function()
                            local itemIcon = item:GetItemIcon()
                            if itemIcon and btn.icon then
                                btn.icon:SetTexture(itemIcon)
                                btn.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
                                if selectedSlotFilter[btn.slotName] or not next(selectedSlotFilter) then
                                    btn.icon:SetDesaturated(false)
                                    btn.icon:SetAlpha(1)
                                end
                            end
                        end)

                        -- Add animated glow for top 3 ranks
                        if rank <= 3 then
                            local glowFrame = addGlowToIcon(btn, btn.icon, rank)
                            if glowFrame then
                                table.insert(paperDollGlows, glowFrame)
                            end
                        end

                        break -- use highest-ranked equipped BIS item
                    end
                end
            end
        end
    end
end

-- ============================================================================
-- Item row creation
-- ============================================================================

local ROW_HEIGHT = 28
local ICON_SIZE = 24

-- ============================================================================
-- Rank glow animation system
-- ============================================================================

local glowAnimations = {}
local glowTimer = CreateFrame("Frame")
glowTimer:SetScript("OnUpdate", function(self, elapsed)
    local t = GetTime()
    local active = false
    for i = #glowAnimations, 1, -1 do
        local info = glowAnimations[i]
        if not info.frame:IsVisible() then
            table.remove(glowAnimations, i)
        else
            active = true
            local progress = ((t - info.startTime) % info.duration) / info.duration
            local alpha = info.minAlpha + (info.maxAlpha - info.minAlpha) * (0.5 + 0.5 * math.cos(progress * 2 * math.pi))
            info.frame:SetAlpha(alpha)
        end
    end
    if not active then
        self:Hide()
    end
end)
glowTimer:Hide()

addGlowToIcon = function(parentFrame, anchorRegion, rank)
    local config = RANK_GLOW[rank]
    if not config then return nil end

    local glowFrame = CreateFrame("Frame", nil, parentFrame)
    glowFrame:SetPoint("CENTER", anchorRegion, "CENTER", 0, 0)
    glowFrame:SetSize(ICON_SIZE * 2, ICON_SIZE * 2)
    glowFrame:SetFrameLevel(parentFrame:GetFrameLevel() + 2)

    local glowTex = glowFrame:CreateTexture(nil, "OVERLAY")
    glowTex:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    glowTex:SetBlendMode("ADD")
    glowTex:SetAllPoints()
    glowTex:SetVertexColor(config.r, config.g, config.b)

    table.insert(glowAnimations, {
        frame = glowFrame,
        startTime = GetTime(),
        duration = config.duration,
        minAlpha = config.minAlpha,
        maxAlpha = config.maxAlpha,
    })
    glowTimer:Show()

    return glowFrame
end

local function createSlotHeader(parent, slotName, yOffset)
    local header = CreateFrame("Frame", nil, parent)
    header:SetSize(parent:GetWidth(), 24)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)

    local line = header:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(0.8, 0.65, 0, 0.6)
    line:SetSize(parent:GetWidth() - 20, 1)
    line:SetPoint("TOPLEFT", header, "TOPLEFT", 10, -2)

    local text = header:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    text:SetPoint("TOPLEFT", header, "TOPLEFT", 12, -6)
    text:SetFont("Fonts\\FRIZQT__.TTF", 13, "OUTLINE")
    text:SetTextColor(1, 0.82, 0, 1)
    text:SetText(slotName)

    return header, 24
end

-- ============================================================================
-- Upgrade popup panel (shown when hovering items ranked #2+)
-- ============================================================================

local upgradePanel = CreateFrame("Frame", "BISTBCUpgradePanel", UIParent, BackdropTemplateMixin and "BackdropTemplate" or nil)
upgradePanel:SetBackdrop({
    bgFile = "Interface\\Buttons\\WHITE8x8",
    edgeFile = "Interface\\Buttons\\WHITE8x8",
    edgeSize = 1,
})
upgradePanel:SetBackdropColor(0.05, 0.05, 0.05, 0.94)
upgradePanel:SetBackdropBorderColor(0.25, 0.25, 0.25, 1)
upgradePanel:SetFrameStrata("TOOLTIP")
upgradePanel:SetClampedToScreen(true)
upgradePanel:Hide()

local upgradePanelTitle = upgradePanel:CreateFontString(nil, "OVERLAY", "GameFontNormal")
upgradePanelTitle:SetPoint("TOPLEFT", upgradePanel, "TOPLEFT", 10, -8)
upgradePanelTitle:SetFont("Fonts\\FRIZQT__.TTF", 12, "OUTLINE")
upgradePanelTitle:SetTextColor(1, 0.82, 0, 1)
upgradePanelTitle:SetText("Upgrades")

-- Pre-create 3 upgrade rows
local upgradeRows = {}
for i = 1, 3 do
    local row = CreateFrame("Frame", nil, upgradePanel)
    row:SetSize(300, ROW_HEIGHT)
    row:SetPoint("TOPLEFT", upgradePanel, "TOPLEFT", 4, -(24 + (i - 1) * ROW_HEIGHT))
    row:EnableMouse(true)

    local iconFrame = CreateFrame("Button", nil, row)
    iconFrame:SetSize(ICON_SIZE, ICON_SIZE)
    iconFrame:SetPoint("LEFT", row, "LEFT", 6, 0)

    local icon = iconFrame:CreateTexture(nil, "ARTWORK")
    icon:SetAllPoints()
    icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)

    -- Glow holder for upgrade icon
    local glowHolder = CreateFrame("Frame", nil, row)
    glowHolder:SetPoint("CENTER", iconFrame, "CENTER", 0, 0)
    glowHolder:SetSize(ICON_SIZE * 2, ICON_SIZE * 2)
    glowHolder:SetFrameLevel(row:GetFrameLevel() + 2)

    local glowTex = glowHolder:CreateTexture(nil, "OVERLAY")
    glowTex:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    glowTex:SetBlendMode("ADD")
    glowTex:SetAllPoints()
    glowHolder:Hide()

    local rankText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    rankText:SetPoint("LEFT", iconFrame, "RIGHT", 4, 0)
    rankText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    rankText:SetWidth(20)

    local nameText = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    nameText:SetPoint("LEFT", rankText, "RIGHT", 2, 0)
    nameText:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    nameText:SetJustifyH("LEFT")
    nameText:SetWidth(170)
    nameText:SetWordWrap(false)

    local sourceText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    sourceText:SetPoint("RIGHT", row, "RIGHT", -6, 0)
    sourceText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    sourceText:SetTextColor(0.55, 0.55, 0.55, 1)
    sourceText:SetJustifyH("RIGHT")
    sourceText:SetWidth(120)
    sourceText:SetWordWrap(false)

    upgradeRows[i] = {
        frame = row,
        iconFrame = iconFrame,
        icon = icon,
        glowHolder = glowHolder,
        glowTex = glowTex,
        rankText = rankText,
        nameText = nameText,
        sourceText = sourceText,
    }
end

local upgradePanelGlows = {}

showUpgradePanel = function(slotData, currentRank)
    local numUpgrades = math.min(currentRank - 1, 3)
    if numUpgrades <= 0 then
        upgradePanel:Hide()
        return
    end

    -- Clear old upgrade panel glows
    for _, info in ipairs(upgradePanelGlows) do
        info.frame:Hide()
    end
    wipe(upgradePanelGlows)

    for i = 1, 3 do
        upgradeRows[i].frame:Hide()
    end

    local shown = 0
    for upgradeRank = 1, numUpgrades do
        local itemEntry = slotData[upgradeRank]
        if itemEntry then
            local itemId = type(itemEntry) == "table" and itemEntry.id or itemEntry
            if itemId and itemId > 0 then
                shown = shown + 1
                local rowInfo = upgradeRows[shown]
                rowInfo.frame:Show()

                -- Rank text + glow color
                local glowConfig = RANK_GLOW[upgradeRank]
                rowInfo.rankText:SetText("#" .. upgradeRank)
                if glowConfig then
                    rowInfo.rankText:SetTextColor(glowConfig.r, glowConfig.g, glowConfig.b, 1)
                    rowInfo.glowHolder:Show()
                    rowInfo.glowTex:SetVertexColor(glowConfig.r, glowConfig.g, glowConfig.b)
                    local glowInfo = {
                        frame = rowInfo.glowHolder,
                        startTime = GetTime(),
                        duration = glowConfig.duration,
                        minAlpha = glowConfig.minAlpha,
                        maxAlpha = glowConfig.maxAlpha,
                    }
                    table.insert(glowAnimations, glowInfo)
                    table.insert(upgradePanelGlows, glowInfo)
                    glowTimer:Show()
                else
                    rowInfo.rankText:SetTextColor(0.5, 0.5, 0.5, 1)
                    rowInfo.glowHolder:Hide()
                end

                -- Source
                local sourceStr = getItemSource(itemId)
                rowInfo.sourceText:SetText(sourceStr)

                -- Load item async
                local capturedRow = rowInfo
                local item = Item:CreateFromItemID(itemId)
                item:ContinueOnItemLoad(function()
                    capturedRow.icon:SetTexture(item:GetItemIcon())
                    local name = item:GetItemName()
                    capturedRow.nameText:SetText(name)
                    local _, _, quality = GetItemInfo(itemId)
                    if quality then
                        local r, g, b = GetItemQualityColor(quality)
                        capturedRow.nameText:SetTextColor(r, g, b)
                    end
                    -- Tooltip + shift-click on icon
                    local itemLink = item:GetItemLink()
                    capturedRow.iconFrame:SetScript("OnEnter", function(self)
                        GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
                        if itemLink then GameTooltip:SetHyperlink(itemLink) end
                        GameTooltip:Show()
                    end)
                    capturedRow.iconFrame:SetScript("OnLeave", function(self)
                        GameTooltip:Hide()
                    end)
                    capturedRow.iconFrame:SetScript("OnClick", function(self, button)
                        if button == "LeftButton" and itemLink then
                            if IsShiftKeyDown() then
                                ChatEdit_InsertLink(itemLink)
                            else
                                SetItemRef(itemLink, itemLink, "LeftButton")
                            end
                        end
                    end)
                    capturedRow.frame:SetScript("OnMouseUp", function(self, button)
                        if button == "LeftButton" and itemLink then
                            if IsShiftKeyDown() then
                                ChatEdit_InsertLink(itemLink)
                            else
                                SetItemRef(itemLink, itemLink, "LeftButton")
                            end
                        end
                    end)
                end)
            end
        end
    end

    if shown > 0 then
        upgradePanel:SetSize(310, 28 + shown * ROW_HEIGHT)
        upgradePanel:ClearAllPoints()
        upgradePanel:SetPoint("TOPLEFT", GameTooltip, "TOPRIGHT", 4, 0)
        upgradePanel:Show()
    else
        upgradePanel:Hide()
    end
end

hideUpgradePanel = function()
    upgradePanel:Hide()
    for _, info in ipairs(upgradePanelGlows) do
        info.frame:Hide()
    end
    wipe(upgradePanelGlows)
end

local function createItemRow(parent, rank, itemId, source, yOffset, rowIndex, slotData)
    local row = CreateFrame("Frame", nil, parent)
    row:SetSize(parent:GetWidth(), ROW_HEIGHT)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)

    local bg = row:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    if rowIndex % 2 == 0 then
        bg:SetColorTexture(0.12, 0.12, 0.12, 0.6)
    else
        bg:SetColorTexture(0.08, 0.08, 0.08, 0.4)
    end

    local highlight = row:CreateTexture(nil, "BACKGROUND", nil, 1)
    highlight:SetAllPoints()
    highlight:SetColorTexture(1, 1, 1, 0.06)
    highlight:Hide()

    row:EnableMouse(true)
    row:SetScript("OnEnter", function(self) highlight:Show() end)
    row:SetScript("OnLeave", function(self) highlight:Hide() end)

    -- Rank number (colored gold/silver/bronze for top 3)
    local rankText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    rankText:SetPoint("LEFT", row, "LEFT", 14, 0)
    rankText:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    rankText:SetText("#" .. rank)
    rankText:SetWidth(24)
    local glowConfig = RANK_GLOW[rank]
    if glowConfig then
        rankText:SetTextColor(glowConfig.r, glowConfig.g, glowConfig.b, 1)
    else
        rankText:SetTextColor(0.5, 0.5, 0.5, 1)
    end

    -- Item icon
    local iconFrame = CreateFrame("Button", nil, row)
    iconFrame:SetSize(ICON_SIZE, ICON_SIZE)
    iconFrame:SetPoint("LEFT", row, "LEFT", 40, 0)

    local iconTexture = iconFrame:CreateTexture(nil, "ARTWORK")
    iconTexture:SetAllPoints()
    iconTexture:SetTexCoord(0.08, 0.92, 0.08, 0.92)

    -- Item name
    local nameText = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    nameText:SetPoint("LEFT", iconFrame, "RIGHT", 6, 0)
    nameText:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    nameText:SetJustifyH("LEFT")
    nameText:SetWidth(260)
    nameText:SetWordWrap(false)

    -- Source text (far right)
    local sourceText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    sourceText:SetPoint("RIGHT", row, "RIGHT", -10, 0)
    sourceText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    sourceText:SetTextColor(0.55, 0.55, 0.55, 1)
    sourceText:SetJustifyH("RIGHT")
    sourceText:SetWidth(190)
    sourceText:SetWordWrap(false)

    local sourceStr = source or getItemSource(itemId)
    sourceText:SetText(sourceStr)

    -- Drop rate / token icon column (between name and source)
    local dropRate = getItemDropRate(itemId)
    local tokenId, tokenCount = getItemTokenId(itemId)
    local dropText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    dropText:SetPoint("RIGHT", sourceText, "LEFT", -6, 0)
    dropText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    dropText:SetJustifyH("RIGHT")
    dropText:SetWidth(38)
    dropText:SetWordWrap(false)
    local dbChar = BISTBCAddon.db and BISTBCAddon.db.char
    if tokenId and (not dbChar or dbChar.show_drop_rates ~= false) then
        -- Show token icon
        dropText:SetText("")
        local tokenBtn = CreateFrame("Button", nil, row)
        tokenBtn:SetSize(20, 20)
        tokenBtn:SetPoint("RIGHT", sourceText, "LEFT", -8, 0)
        local tokenIcon = tokenBtn:CreateTexture(nil, "ARTWORK")
        tokenIcon:SetAllPoints()
        tokenIcon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        if tokenCount and tokenCount > 1 then
            local countText = tokenBtn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
            countText:SetPoint("BOTTOMRIGHT", tokenBtn, "BOTTOMRIGHT", 0, 0)
            countText:SetFont("Fonts\\FRIZQT__.TTF", 9, "OUTLINE")
            countText:SetTextColor(1, 1, 1, 1)
            countText:SetText(tokenCount)
        end
        local pvpIcon = getPvpCurrencyIcon(tokenId)
        if pvpIcon then
            -- PvP currency: use static texture, no tooltip
            tokenIcon:SetTexture(pvpIcon)
            tokenBtn:SetScript("OnEnter", function(self)
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
                if tokenId == 1900 then
                    GameTooltip:SetText("Arena Points")
                else
                    GameTooltip:SetText("Honor Points")
                end
                GameTooltip:Show()
                highlight:Show()
            end)
            tokenBtn:SetScript("OnLeave", function(self)
                GameTooltip:Hide()
                highlight:Hide()
            end)
        else
            -- Real item token (tier tokens, badges, etc.)
            local tokenItem = Item:CreateFromItemID(tokenId)
            tokenItem:ContinueOnItemLoad(function()
                tokenIcon:SetTexture(tokenItem:GetItemIcon())
                local tokenLink = tokenItem:GetItemLink()
                tokenBtn:SetScript("OnEnter", function(self)
                    GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
                    if tokenLink then
                        GameTooltip:SetHyperlink(tokenLink)
                    end
                    GameTooltip:Show()
                    highlight:Show()
                end)
                tokenBtn:SetScript("OnLeave", function(self)
                    GameTooltip:Hide()
                    highlight:Hide()
                end)
            end)
        end
    elseif dropRate and (not dbChar or dbChar.show_drop_rates ~= false) then
        dropText:SetText(dropRate .. "%")
        dropText:SetTextColor(0.53, 0.67, 0.80, 1)
    else
        dropText:SetText("")
    end

    -- Owned indicator
    local owned = ownedItems[itemId]
    if owned and (not dbChar or dbChar.show_owned_marks ~= false) then
        local ownedText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        ownedText:SetPoint("RIGHT", dropText, "LEFT", -4, 0)
        ownedText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
        if owned == "equipped" then
            ownedText:SetText("|cff00ff00E|r")
            ownedText:SetTextColor(0, 1, 0, 1)
        else
            ownedText:SetText("|cffffff00B|r")
            ownedText:SetTextColor(1, 1, 0, 1)
        end
    end

    -- Load item data async
    if itemId and itemId > 0 then
        local item = Item:CreateFromItemID(itemId)
        itemCache[itemId] = item

        item:ContinueOnItemLoad(function()
            local itemName = item:GetItemName()
            local itemLink = item:GetItemLink()
            local itemIcon = item:GetItemIcon()
            local _, _, itemQuality = GetItemInfo(itemId)

            iconTexture:SetTexture(itemIcon)
            nameText:SetText(itemName)

            if itemQuality then
                local r, g, b = GetItemQualityColor(itemQuality)
                nameText:SetTextColor(r, g, b, 1)
            end

            iconFrame:SetScript("OnEnter", function(self)
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
                GameTooltip:SetHyperlink(itemLink)
                GameTooltip:Show()
                highlight:Show()
            end)
            iconFrame:SetScript("OnLeave", function(self)
                GameTooltip:Hide()
                highlight:Hide()
            end)

            iconFrame:SetScript("OnClick", function(self, button)
                if button == "LeftButton" then
                    if IsShiftKeyDown() then
                        ChatEdit_InsertLink(itemLink)
                    else
                        SetItemRef(itemLink, itemLink, "LeftButton")
                    end
                end
            end)
        end)

        row:SetScript("OnEnter", function(self)
            highlight:Show()
            if item:GetItemLink() then
                GameTooltip:SetOwner(iconFrame, "ANCHOR_RIGHT", 4, 0)
                GameTooltip:SetHyperlink(item:GetItemLink())
                GameTooltip:Show()
            end
        end)
        row:SetScript("OnLeave", function(self)
            highlight:Hide()
            GameTooltip:Hide()
        end)
        row:EnableMouse(true)
        row:SetScript("OnMouseUp", function(self, button)
            if button == "LeftButton" and item:GetItemLink() then
                if IsShiftKeyDown() then
                    ChatEdit_InsertLink(item:GetItemLink())
                else
                    SetItemRef(item:GetItemLink(), item:GetItemLink(), "LeftButton")
                end
            end
        end)
    else
        nameText:SetText("|cff666666Empty|r")
    end

    return row, ROW_HEIGHT
end

-- Create a row for enchants (shows enchant name via spell or item tooltip)
local function createEnchantRow(parent, enchantId, slot, yOffset, rowIndex)
    local row = CreateFrame("Frame", nil, parent)
    row:SetSize(parent:GetWidth(), ROW_HEIGHT)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)

    local bg = row:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    if rowIndex % 2 == 0 then
        bg:SetColorTexture(0.12, 0.12, 0.12, 0.6)
    else
        bg:SetColorTexture(0.08, 0.08, 0.08, 0.4)
    end

    local highlight = row:CreateTexture(nil, "BACKGROUND", nil, 1)
    highlight:SetAllPoints()
    highlight:SetColorTexture(1, 1, 1, 0.06)
    highlight:Hide()

    row:EnableMouse(true)
    row:SetScript("OnEnter", function(self) highlight:Show() end)
    row:SetScript("OnLeave", function(self) highlight:Hide() end)

    -- Icon
    local iconFrame = CreateFrame("Button", nil, row)
    iconFrame:SetSize(ICON_SIZE, ICON_SIZE)
    iconFrame:SetPoint("LEFT", row, "LEFT", 14, 0)

    local iconTexture = iconFrame:CreateTexture(nil, "ARTWORK")
    iconTexture:SetAllPoints()
    iconTexture:SetTexCoord(0.08, 0.92, 0.08, 0.92)

    -- Enchant name
    local nameText = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    nameText:SetPoint("LEFT", iconFrame, "RIGHT", 6, 0)
    nameText:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    nameText:SetJustifyH("LEFT")
    nameText:SetWidth(320)
    nameText:SetWordWrap(false)

    -- Source text
    local sourceText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    sourceText:SetPoint("RIGHT", row, "RIGHT", -14, 0)
    sourceText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    sourceText:SetTextColor(0.55, 0.55, 0.55, 1)
    sourceText:SetJustifyH("RIGHT")
    sourceText:SetWidth(200)
    sourceText:SetWordWrap(false)

    -- Try to load from enchantsources
    local enchSrc = BISTBC_enchantsources and BISTBC_enchantsources[enchantId]
    if enchSrc then
        nameText:SetText(enchSrc.name)
        nameText:SetTextColor(0.0, 0.8, 0.0, 1)
        local srcStr = enchSrc.source or ""
        if enchSrc.location and enchSrc.location ~= "" then
            srcStr = srcStr .. " - " .. enchSrc.location
        end
        sourceText:SetText(srcStr)

        -- Load icon based on enchant type
        local enchType = enchSrc.type or "spell"
        if enchType == "item" then
            local enchItem = Item:CreateFromItemID(enchantId)
            enchItem:ContinueOnItemLoad(function()
                iconTexture:SetTexture(enchItem:GetItemIcon())
            end)
        else
            local texId = tonumber(enchSrc.texture)
            if texId and texId > 0 and texId < 99999 then
                local texItem = Item:CreateFromItemID(texId)
                texItem:ContinueOnItemLoad(function()
                    iconTexture:SetTexture(texItem:GetItemIcon())
                end)
            else
                local spellIcon
                if C_Spell and C_Spell.GetSpellInfo then
                    local info = C_Spell.GetSpellInfo(enchantId)
                    spellIcon = info and info.iconID
                else
                    local _, _, icon = GetSpellInfo(enchantId)
                    spellIcon = icon
                end
                if spellIcon then
                    iconTexture:SetTexture(spellIcon)
                end
            end
        end

        -- Tooltip for enchantsources entries
        local enchType = enchSrc.type or "spell"
        local function showEnchTooltip(anchor)
            GameTooltip:SetOwner(anchor, "ANCHOR_RIGHT", 4, 0)
            local linkType = enchType == "item" and "item" or "spell"
            local ok = pcall(function() GameTooltip:SetHyperlink(linkType .. ":" .. enchantId) end)
            if not ok or not GameTooltip:IsShown() then
                GameTooltip:AddLine(enchSrc.name, 0, 0.8, 0)
                if srcStr ~= "" then
                    GameTooltip:AddLine(srcStr, 0.55, 0.55, 0.55)
                end
                GameTooltip:Show()
            end
        end
        iconFrame:SetScript("OnEnter", function(self)
            showEnchTooltip(self)
            highlight:Show()
        end)
        iconFrame:SetScript("OnLeave", function(self)
            GameTooltip:Hide()
            highlight:Hide()
        end)
        row:SetScript("OnEnter", function(self)
            highlight:Show()
            showEnchTooltip(iconFrame)
        end)
        row:SetScript("OnLeave", function(self)
            highlight:Hide()
            GameTooltip:Hide()
        end)
    end

    -- Only try loading as item if we don't have enchantsources data
    -- (some enchant IDs collide with unrelated Blizzard test items)
    if not enchSrc then
        local item = Item:CreateFromItemID(enchantId)
        itemCache[enchantId] = item
        item:ContinueOnItemLoad(function()
            local itemLink = item:GetItemLink()
            local itemIcon = item:GetItemIcon()
            local itemName = item:GetItemName()
            local _, _, itemQuality = GetItemInfo(enchantId)

            if itemIcon then iconTexture:SetTexture(itemIcon) end
            if itemName then
                nameText:SetText(itemName)
                if itemQuality then
                    local r, g, b = GetItemQualityColor(itemQuality)
                    nameText:SetTextColor(r, g, b, 1)
                end
            end

            if itemLink then
                iconFrame:SetScript("OnEnter", function(self)
                    GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
                    GameTooltip:SetHyperlink(itemLink)
                    GameTooltip:Show()
                    highlight:Show()
                end)
                iconFrame:SetScript("OnLeave", function(self)
                    GameTooltip:Hide()
                    highlight:Hide()
                end)
                row:SetScript("OnEnter", function(self)
                    highlight:Show()
                    GameTooltip:SetOwner(iconFrame, "ANCHOR_RIGHT", 4, 0)
                    GameTooltip:SetHyperlink(itemLink)
                    GameTooltip:Show()
                end)
                row:SetScript("OnLeave", function(self)
                    highlight:Hide()
                    GameTooltip:Hide()
                end)
            end
        end)
    end

    return row, ROW_HEIGHT
end

-- ============================================================================
-- Content rendering
-- ============================================================================

clearContent = function()
    for _, row in ipairs(contentRows) do
        row:Hide()
        row:SetParent(nil)
    end
    wipe(contentRows)
    wipe(itemCache)
    hideUpgradePanel()
end

-- Render Items tab
renderContent = function()
    clearContent()
    buildOwnedItems()

    if not selectedClass or not selectedSpec or not selectedPhase then return end

    local phaseKey = phaseKeys[selectedPhaseIndex]
    local bislists = BISTBC_bislists and BISTBC_bislists[selectedClass]
    if not bislists then return end

    local specData = bislists[selectedSpec]
    if not specData then return end

    local slots = specData[phaseKey]
    if not slots then return end

    local yOffset = -4
    local globalRowIndex = 0
    local activeFilter = sourceFilters[selectedSourceFilterIndex]
    local activeZone = zoneList[selectedZoneIndex] or "All"

    for _, slot in ipairs(slots) do
        -- Apply slot filter from paper doll ("Two Hand" / "Dual Wield" map to "Main Hand" button)
        local filterSlot = (slot.slot_name == "Two Hand" or slot.slot_name == "Dual Wield") and "Main Hand" or slot.slot_name
        if next(selectedSlotFilter) and not selectedSlotFilter[filterSlot] then
            -- skip this slot
        else

        local header, headerHeight = createSlotHeader(scrollChild, slot.slot_name, yOffset)
        table.insert(contentRows, header)
        yOffset = yOffset - headerHeight

        local slotHasItems = false

        for rank = 1, 5 do
            local itemEntry = slot[rank]
            if itemEntry then
                local itemId, source
                if type(itemEntry) == "table" then
                    itemId = itemEntry.id
                    source = itemEntry.source
                else
                    itemId = itemEntry
                    source = nil
                end

                if itemId and itemId > 0 then
                    local sourceStr = source or getItemSource(itemId)

                    -- Apply source filter
                    local passSource = (activeFilter == "All" or getSourceCategory(sourceStr) == activeFilter)

                    -- Apply zone filter
                    local passZone = true
                    if activeZone ~= "All" then
                        local zone = getSourceZone(sourceStr)
                        passZone = (zone == activeZone)
                    end

                    -- Apply search filter
                    local passSearch = matchesSearch(itemId)

                    if passSource and passZone and passSearch then
                        slotHasItems = true
                        globalRowIndex = globalRowIndex + 1
                        local row, rowHeight = createItemRow(scrollChild, rank, itemId, source, yOffset, globalRowIndex, slot)
                        table.insert(contentRows, row)
                        yOffset = yOffset - rowHeight
                    end
                end
            end
        end

        if not slotHasItems then
            contentRows[#contentRows]:Hide()
            table.remove(contentRows)
            yOffset = yOffset + 24
        else
            yOffset = yOffset - 6
        end

        end -- slot filter else
    end

    scrollChild:SetHeight(math.abs(yOffset) + 20)
end

-- Render Gems tab
renderGems = function()
    clearContent()

    if not selectedClass or not selectedSpec or not selectedPhaseIndex then return end

    local gemsData = BISTBC_gems and BISTBC_gems[selectedClass] and BISTBC_gems[selectedClass][selectedSpec]
    if not gemsData then
        scrollChild:SetHeight(40)
        return
    end

    local phaseKey = phaseKeys[selectedPhaseIndex]
    local phaseIdx = selectedPhaseIndex - 1 -- LBIS phases are 0-indexed

    -- Collect gems up to current phase
    local metaGems = {}
    local normalGems = {}
    for _, gem in ipairs(gemsData) do
        -- Check if gem phase is <= selected phase
        local gemPhaseIdx = 0
        for pi, pk in ipairs(phaseKeys) do
            if pk == gem.phase then gemPhaseIdx = pi - 1; break end
        end
        if gemPhaseIdx <= phaseIdx then
            if gem.meta then
                table.insert(metaGems, gem)
            else
                table.insert(normalGems, gem)
            end
        end
    end

    local yOffset = -4
    local globalRowIndex = 0

    -- Meta gems section
    if #metaGems > 0 then
        local header, headerHeight = createSlotHeader(scrollChild, "Meta Gems", yOffset)
        table.insert(contentRows, header)
        yOffset = yOffset - headerHeight

        for i, gem in ipairs(metaGems) do
            globalRowIndex = globalRowIndex + 1
            local source = ""
            if BISTBC_gemsources and BISTBC_gemsources[gem.id] then
                local gs = BISTBC_gemsources[gem.id]
                source = gs.source or ""
                if gs.location and gs.location ~= "" then
                    source = source .. " - " .. gs.location
                end
            end
            local row, rowHeight = createItemRow(scrollChild, i, gem.id, source, yOffset, globalRowIndex)
            table.insert(contentRows, row)
            yOffset = yOffset - rowHeight
        end
        yOffset = yOffset - 6
    end

    -- Normal gems section
    if #normalGems > 0 then
        local header, headerHeight = createSlotHeader(scrollChild, "Gems", yOffset)
        table.insert(contentRows, header)
        yOffset = yOffset - headerHeight

        for i, gem in ipairs(normalGems) do
            globalRowIndex = globalRowIndex + 1
            local source = ""
            if BISTBC_gemsources and BISTBC_gemsources[gem.id] then
                local gs = BISTBC_gemsources[gem.id]
                source = gs.source or ""
                if gs.location and gs.location ~= "" then
                    source = source .. " - " .. gs.location
                end
            end
            local row, rowHeight = createItemRow(scrollChild, i, gem.id, source, yOffset, globalRowIndex)
            table.insert(contentRows, row)
            yOffset = yOffset - rowHeight
        end
        yOffset = yOffset - 6
    end

    scrollChild:SetHeight(math.abs(yOffset) + 20)
end

-- Render Enchants tab
renderEnchants = function()
    clearContent()

    if not selectedClass or not selectedSpec or not selectedPhaseIndex then return end

    local enchantsData = BISTBC_enchants and BISTBC_enchants[selectedClass] and BISTBC_enchants[selectedClass][selectedSpec]
    if not enchantsData then
        scrollChild:SetHeight(40)
        return
    end

    local phaseIdx = selectedPhaseIndex - 1

    -- Group enchants by slot, filtered by phase
    local bySlot = {}
    for _, ench in ipairs(enchantsData) do
        local enchPhaseIdx = 0
        for pi, pk in ipairs(phaseKeys) do
            if pk == ench.phase then enchPhaseIdx = pi - 1; break end
        end
        if enchPhaseIdx <= phaseIdx then
            local slot = ench.slot:gsub("~", " / ")
            if not bySlot[slot] then bySlot[slot] = {} end
            table.insert(bySlot[slot], ench)
        end
    end

    -- Build ordered slot list
    local orderedSlots = {}
    local slotIndex = {}
    for i, s in ipairs(ENCHANT_SLOT_ORDER) do
        slotIndex[s:gsub("~", " / ")] = i
    end
    for slot in pairs(bySlot) do
        table.insert(orderedSlots, slot)
    end
    table.sort(orderedSlots, function(a, b)
        return (slotIndex[a] or 99) < (slotIndex[b] or 99)
    end)

    local yOffset = -4
    local globalRowIndex = 0

    for _, slot in ipairs(orderedSlots) do
        local enchants = bySlot[slot]
        local header, headerHeight = createSlotHeader(scrollChild, slot, yOffset)
        table.insert(contentRows, header)
        yOffset = yOffset - headerHeight

        for _, ench in ipairs(enchants) do
            globalRowIndex = globalRowIndex + 1
            local row, rowHeight = createEnchantRow(scrollChild, ench.id, slot, yOffset, globalRowIndex)
            table.insert(contentRows, row)
            yOffset = yOffset - rowHeight
        end
        yOffset = yOffset - 6
    end

    scrollChild:SetHeight(math.abs(yOffset) + 20)
end

-- Helper: get or create custom list storage for current spec
local function getCustomListStorage()
    local db = BISTBCAddon.db and BISTBCAddon.db.char
    if not db then return nil end
    if not db.custom_lists then db.custom_lists = {} end
    local listKey = selectedClass .. "|" .. selectedSpec
    if not db.custom_lists[listKey] then db.custom_lists[listKey] = {} end
    return db.custom_lists[listKey]
end

-- Create an item row with edit controls (delete, move up/down)
local function createEditableItemRow(parent, rank, itemId, slotName, totalInSlot, yOffset, rowIndex)
    local row = CreateFrame("Frame", nil, parent)
    row:SetSize(parent:GetWidth(), ROW_HEIGHT)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)

    local bg = row:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    if rowIndex % 2 == 0 then
        bg:SetColorTexture(0.12, 0.12, 0.12, 0.6)
    else
        bg:SetColorTexture(0.08, 0.08, 0.08, 0.4)
    end

    -- Delete button
    local delBtn = CreateFrame("Button", nil, row)
    delBtn:SetSize(16, 16)
    delBtn:SetPoint("LEFT", row, "LEFT", 8, 0)
    delBtn:SetNormalFontObject("GameFontNormalSmall")
    local delText = delBtn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    delText:SetPoint("CENTER")
    delText:SetFont("Fonts\\FRIZQT__.TTF", 12, "OUTLINE")
    delText:SetTextColor(0.9, 0.2, 0.2, 1)
    delText:SetText("X")
    delBtn:SetScript("OnClick", function()
        local storage = getCustomListStorage()
        if storage and storage[slotName] then
            table.remove(storage[slotName], rank)
            if #storage[slotName] == 0 then storage[slotName] = nil end
            renderCustomList()
        end
    end)
    delBtn:SetScript("OnEnter", function(self)
        delText:SetTextColor(1, 0.3, 0.3, 1)
    end)
    delBtn:SetScript("OnLeave", function(self)
        delText:SetTextColor(0.9, 0.2, 0.2, 1)
    end)

    -- Move up button
    local upBtn = CreateFrame("Button", nil, row)
    upBtn:SetSize(14, 14)
    upBtn:SetPoint("LEFT", delBtn, "RIGHT", 4, 0)
    local upText = upBtn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    upText:SetPoint("CENTER")
    upText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    if rank > 1 then
        upText:SetTextColor(0.7, 0.7, 0.7, 1)
        upText:SetText("\226\150\178") -- up triangle
        upBtn:SetScript("OnClick", function()
            local storage = getCustomListStorage()
            if storage and storage[slotName] and rank > 1 then
                storage[slotName][rank], storage[slotName][rank - 1] = storage[slotName][rank - 1], storage[slotName][rank]
                renderCustomList()
            end
        end)
    else
        upText:SetTextColor(0.3, 0.3, 0.3, 1)
        upText:SetText("\226\150\178")
    end

    -- Move down button
    local downBtn = CreateFrame("Button", nil, row)
    downBtn:SetSize(14, 14)
    downBtn:SetPoint("LEFT", upBtn, "RIGHT", 2, 0)
    local downText = downBtn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    downText:SetPoint("CENTER")
    downText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    if rank < totalInSlot then
        downText:SetTextColor(0.7, 0.7, 0.7, 1)
        downText:SetText("\226\150\188") -- down triangle
        downBtn:SetScript("OnClick", function()
            local storage = getCustomListStorage()
            if storage and storage[slotName] and rank < #storage[slotName] then
                storage[slotName][rank], storage[slotName][rank + 1] = storage[slotName][rank + 1], storage[slotName][rank]
                renderCustomList()
            end
        end)
    else
        downText:SetTextColor(0.3, 0.3, 0.3, 1)
        downText:SetText("\226\150\188")
    end

    -- Item icon
    local iconFrame = CreateFrame("Button", nil, row)
    iconFrame:SetSize(ICON_SIZE, ICON_SIZE)
    iconFrame:SetPoint("LEFT", downBtn, "RIGHT", 8, 0)

    local iconTexture = iconFrame:CreateTexture(nil, "ARTWORK")
    iconTexture:SetAllPoints()
    iconTexture:SetTexCoord(0.08, 0.92, 0.08, 0.92)

    -- Item name
    local nameText = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    nameText:SetPoint("LEFT", iconFrame, "RIGHT", 6, 0)
    nameText:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    nameText:SetJustifyH("LEFT")
    nameText:SetWidth(260)
    nameText:SetWordWrap(false)

    -- Source text
    local sourceText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    sourceText:SetPoint("RIGHT", row, "RIGHT", -14, 0)
    sourceText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    sourceText:SetTextColor(0.55, 0.55, 0.55, 1)
    sourceText:SetJustifyH("RIGHT")
    sourceText:SetWidth(200)
    sourceText:SetWordWrap(false)

    local sourceStr = getItemSource(itemId)
    sourceText:SetText(sourceStr)

    -- Load item data async
    if itemId and itemId > 0 then
        local item = Item:CreateFromItemID(itemId)
        itemCache[itemId] = item
        item:ContinueOnItemLoad(function()
            local itemName = item:GetItemName()
            local itemLink = item:GetItemLink()
            local itemIcon = item:GetItemIcon()
            local _, _, itemQuality = GetItemInfo(itemId)
            iconTexture:SetTexture(itemIcon)
            nameText:SetText(itemName)
            if itemQuality then
                local r, g, b = GetItemQualityColor(itemQuality)
                nameText:SetTextColor(r, g, b, 1)
            end
            iconFrame:SetScript("OnEnter", function(self)
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
                GameTooltip:SetHyperlink(itemLink)
                GameTooltip:Show()
            end)
            iconFrame:SetScript("OnLeave", function(self)
                GameTooltip:Hide()
            end)
        end)
    end

    return row, ROW_HEIGHT
end

-- Create "Add Item" input row for a slot in edit mode
local function createAddItemRow(parent, slotName, yOffset)
    local row = CreateFrame("Frame", nil, parent)
    row:SetSize(parent:GetWidth(), ROW_HEIGHT)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)

    local bg = row:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    bg:SetColorTexture(0.10, 0.12, 0.10, 0.5)

    local label = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", row, "LEFT", 14, 0)
    label:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    label:SetTextColor(0.5, 0.7, 0.5, 1)
    label:SetText("Add item ID:")

    local editBox = CreateFrame("EditBox", nil, row, "InputBoxTemplate")
    editBox:SetSize(100, 18)
    editBox:SetPoint("LEFT", label, "RIGHT", 6, 0)
    editBox:SetAutoFocus(false)
    editBox:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    editBox:SetMaxLetters(10)
    editBox:SetNumeric(true)

    local addBtn = CreateFrame("Button", nil, row)
    addBtn:SetSize(40, 18)
    addBtn:SetPoint("LEFT", editBox, "RIGHT", 6, 0)
    local addBtnBg = createBackdropFrame(nil, addBtn, 0.15, 0.25, 0.15, 0.9, 0.3, 0.5, 0.3, 1)
    addBtnBg:SetAllPoints()
    addBtnBg:SetFrameLevel(addBtn:GetFrameLevel())
    local addLabel = addBtn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    addLabel:SetPoint("CENTER")
    addLabel:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    addLabel:SetTextColor(0.5, 0.9, 0.5, 1)
    addLabel:SetText("Add")

    local function doAdd()
        local idText = strtrim(editBox:GetText())
        local id = tonumber(idText)
        if not id or id <= 0 then return end
        local storage = getCustomListStorage()
        if not storage[slotName] then storage[slotName] = {} end
        if #storage[slotName] >= 6 then
            print("|cffff6666BIS-TBC:|r Max 6 items per slot.")
            return
        end
        table.insert(storage[slotName], { id = id })
        editBox:SetText("")
        renderCustomList()
    end

    addBtn:SetScript("OnClick", doAdd)
    editBox:SetScript("OnEnterPressed", function(self) doAdd(); self:ClearFocus() end)
    editBox:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)

    return row, ROW_HEIGHT
end

-- Render Consumables tab
renderConsumables = function()
    clearContent()
    if not selectedClass or not selectedSpec then return end
    if not scrollChild then return end

    local data = BISTBC_consumables and BISTBC_consumables[selectedClass]
    if not data then return end
    local specData = data[selectedSpec]
    if not specData then return end

    local yOffset = -4
    local globalRowIndex = 0

    for _, entry in ipairs(specData) do
        local category = entry.category
        local items = entry.items
        if items and #items > 0 then
            local header, headerHeight = createSlotHeader(scrollChild, category, yOffset)
            table.insert(contentRows, header)
            yOffset = yOffset - headerHeight

            for _, itemId in ipairs(items) do
                if itemId and itemId > 0 then
                    globalRowIndex = globalRowIndex + 1

                    local row = CreateFrame("Frame", nil, scrollChild)
                    row:SetSize(scrollChild:GetWidth(), ROW_HEIGHT)
                    row:SetPoint("TOPLEFT", scrollChild, "TOPLEFT", 0, yOffset)

                    local bg = row:CreateTexture(nil, "BACKGROUND")
                    bg:SetAllPoints()
                    if globalRowIndex % 2 == 0 then
                        bg:SetColorTexture(0.12, 0.12, 0.12, 0.6)
                    else
                        bg:SetColorTexture(0.08, 0.08, 0.08, 0.4)
                    end

                    local highlight = row:CreateTexture(nil, "BACKGROUND", nil, 1)
                    highlight:SetAllPoints()
                    highlight:SetColorTexture(1, 1, 1, 0.06)
                    highlight:Hide()
                    row:EnableMouse(true)
                    row:SetScript("OnEnter", function() highlight:Show() end)
                    row:SetScript("OnLeave", function() highlight:Hide() end)

                    local iconFrame = CreateFrame("Button", nil, row)
                    iconFrame:SetSize(ICON_SIZE, ICON_SIZE)
                    iconFrame:SetPoint("LEFT", row, "LEFT", 14, 0)
                    local iconTexture = iconFrame:CreateTexture(nil, "ARTWORK")
                    iconTexture:SetAllPoints()
                    iconTexture:SetTexCoord(0.08, 0.92, 0.08, 0.92)

                    local nameText = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
                    nameText:SetPoint("LEFT", iconFrame, "RIGHT", 6, 0)
                    nameText:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
                    nameText:SetJustifyH("LEFT")
                    nameText:SetWidth(400)
                    nameText:SetWordWrap(false)
                    nameText:SetTextColor(0.0, 0.8, 0.0, 1)

                    -- Load item info asynchronously
                    local item = Item:CreateFromItemID(itemId)
                    item:ContinueOnItemLoad(function()
                        nameText:SetText(item:GetItemName())
                        iconTexture:SetTexture(item:GetItemIcon())
                        local qualityColor = item:GetItemQualityColor()
                        if qualityColor then
                            nameText:SetTextColor(qualityColor.r, qualityColor.g, qualityColor.b, 1)
                        end
                    end)

                    -- Tooltip
                    iconFrame:SetScript("OnEnter", function(self)
                        GameTooltip:SetOwner(self, "ANCHOR_RIGHT", 4, 0)
                        GameTooltip:SetItemByID(itemId)
                        GameTooltip:Show()
                        highlight:Show()
                    end)
                    iconFrame:SetScript("OnLeave", function()
                        GameTooltip:Hide()
                        highlight:Hide()
                    end)
                    row:SetScript("OnEnter", function()
                        GameTooltip:SetOwner(iconFrame, "ANCHOR_RIGHT", 4, 0)
                        GameTooltip:SetItemByID(itemId)
                        GameTooltip:Show()
                        highlight:Show()
                    end)
                    row:SetScript("OnLeave", function()
                        GameTooltip:Hide()
                        highlight:Hide()
                    end)

                    table.insert(contentRows, row)
                    yOffset = yOffset - ROW_HEIGHT
                end
            end
            yOffset = yOffset - 6
        end
    end

    scrollChild:SetHeight(math.abs(yOffset) + 20)
end

-- Render Custom List tab
renderCustomList = function()
    clearContent()
    buildOwnedItems()

    if not selectedClass or not selectedSpec then
        scrollChild:SetHeight(40)
        return
    end

    local db = BISTBCAddon.db and BISTBCAddon.db.char
    if not db then return end
    if not db.custom_lists then db.custom_lists = {} end

    local listKey = selectedClass .. "|" .. selectedSpec
    local customList = db.custom_lists[listKey]

    local yOffset = -4
    local globalRowIndex = 0
    local hasAnyItems = false

    if customEditMode then
        -- Edit mode: show all slots with add/remove/reorder controls
        for _, slotName in ipairs(SLOT_ORDER) do
            local header, headerHeight = createSlotHeader(scrollChild, slotName, yOffset)
            table.insert(contentRows, header)
            yOffset = yOffset - headerHeight

            local slotItems = customList and customList[slotName]
            if slotItems then
                local total = #slotItems
                for rank, entry in ipairs(slotItems) do
                    if entry.id and entry.id > 0 then
                        hasAnyItems = true
                        globalRowIndex = globalRowIndex + 1
                        local row, rowHeight = createEditableItemRow(scrollChild, rank, entry.id, slotName, total, yOffset, globalRowIndex)
                        table.insert(contentRows, row)
                        yOffset = yOffset - rowHeight
                    end
                end
            end

            -- Add item input row
            local addRow, addHeight = createAddItemRow(scrollChild, slotName, yOffset)
            table.insert(contentRows, addRow)
            yOffset = yOffset - addHeight - 6
        end
    else
        -- View mode: only show slots that have items
        for _, slotName in ipairs(SLOT_ORDER) do
            local slotItems = customList and customList[slotName]
            if slotItems and #slotItems > 0 then
                local header, headerHeight = createSlotHeader(scrollChild, slotName, yOffset)
                table.insert(contentRows, header)
                yOffset = yOffset - headerHeight

                for rank, entry in ipairs(slotItems) do
                    if entry.id and entry.id > 0 then
                        hasAnyItems = true
                        globalRowIndex = globalRowIndex + 1
                        local row, rowHeight = createItemRow(scrollChild, rank, entry.id, nil, yOffset, globalRowIndex)
                        table.insert(contentRows, row)
                        yOffset = yOffset - rowHeight
                    end
                end
                yOffset = yOffset - 6
            end
        end

        if not hasAnyItems then
            local msgFrame = CreateFrame("Frame", nil, scrollChild)
            msgFrame:SetSize(scrollChild:GetWidth(), 40)
            msgFrame:SetPoint("TOPLEFT", scrollChild, "TOPLEFT", 0, 0)
            local msg = msgFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
            msg:SetPoint("CENTER", msgFrame, "CENTER", 0, 0)
            msg:SetFont("Fonts\\FRIZQT__.TTF", 12, "")
            msg:SetTextColor(0.5, 0.5, 0.5, 1)
            msg:SetText("No custom items. Click Edit to add items.")
            table.insert(contentRows, msgFrame)
            yOffset = -60
        end
    end

    scrollChild:SetHeight(math.abs(yOffset) + 20)
end

-- ============================================================================
-- Tab switching
-- ============================================================================

-- ============================================================================
-- Data persistence
-- ============================================================================

local function saveData()
    BISTBCAddon.db.char.class_index = selectedClassIndex
    BISTBCAddon.db.char.spec_index = selectedSpecIndex
    BISTBCAddon.db.char.phase_index = selectedPhaseIndex
end

local function loadData()
    selectedClassIndex = BISTBCAddon.db.char.class_index
    selectedSpecIndex = BISTBCAddon.db.char.spec_index
    selectedPhaseIndex = BISTBCAddon.db.char.phase_index

    if selectedClassIndex and BISTBC_classes[selectedClassIndex] then
        selectedClass = BISTBC_classes[selectedClassIndex].name
    end
    if selectedClass and selectedSpecIndex and BISTBC_classes[selectedClassIndex] then
        selectedSpec = BISTBC_classes[selectedClassIndex].specs[selectedSpecIndex]
    end
    if selectedPhaseIndex then
        selectedPhase = phases[selectedPhaseIndex]
    end
end

-- ============================================================================
-- Main frame helpers (need to be before switchTab/onChange handlers)
-- ============================================================================

local classDropdown, specDropdown, phaseDropdown, sourceFilterDropdown
local accentBar

local function updateAccentBar()
    if accentBar and selectedClass then
        local r, g, b = getClassColor(selectedClass)
        accentBar:SetColorTexture(r, g, b, 0.8)
    end
end

local function updateLevelingInfo()
    if not levelingPanel then return end
    if selectedTab ~= "Items" then levelingPanel:Hide(); return end
    if selectedClass and selectedSpec and LEVELING_DATA[selectedClass] and LEVELING_DATA[selectedClass][selectedSpec] then
        local data = LEVELING_DATA[selectedClass][selectedSpec]
        levelingStatsText:SetText("|cff8899aaStat Priority:|r  " .. data.stats)
        levelingSuffixesText:SetText("|cff8899aaSuffixes:|r  " .. data.suffixes)
        levelingPanel:Show()
    else
        levelingPanel:Hide()
    end
end

local function updateStatusText()
    if mainFrame and mainFrame.statusText then
        if selectedClass and selectedSpec and selectedPhase then
            mainFrame.statusText:SetText(selectedClass .. " - " .. selectedSpec .. " - " .. selectedPhase)
        else
            mainFrame.statusText:SetText("Select class, spec, and phase")
        end
    end
end

-- ============================================================================
-- Farm tab
-- ============================================================================

renderFarm = function()
    clearContent()
    buildOwnedItems()

    if not selectedClass or not selectedSpec or not selectedPhase then return end
    if not scrollChild then return end

    local phaseKey = phaseKeys[selectedPhaseIndex]
    local bislists = BISTBC_bislists and BISTBC_bislists[selectedClass]
    if not bislists then return end
    local specData = bislists[selectedSpec]
    if not specData then return end
    local slots = specData[phaseKey]
    if not slots then return end

    -- Collect missing items grouped by zone
    local groups = {}
    local groupOrder = {}

    for _, slot in ipairs(slots) do
        -- Find best rank the player already owns for this slot
        local bestOwnedRank = nil
        for r = 1, 5 do
            local entry = slot[r]
            if entry then
                local id = type(entry) == "table" and entry.id or entry
                if id and id > 0 and ownedItems[id] then
                    bestOwnedRank = r
                    break  -- ranks are ordered, first owned = best
                end
            end
        end

        for rank = 1, 5 do
            -- Skip items ranked worse than what we already own
            if bestOwnedRank and rank >= bestOwnedRank then break end

            local itemEntry = slot[rank]
            if itemEntry then
                local itemId, source
                if type(itemEntry) == "table" then
                    itemId = itemEntry.id
                    source = itemEntry.source
                else
                    itemId = itemEntry
                    source = nil
                end

                if itemId and itemId > 0 and not ownedItems[itemId] then
                    local sourceStr = source or getItemSource(itemId)
                    local zone = getSourceZone(sourceStr)
                    local category = getSourceCategory(sourceStr)

                    -- For vendor items with a token, use the token's drop source and zone
                    if not zone and category == "Vendor" and BISTBC_sources and BISTBC_sources[itemId] then
                        local tokenId = BISTBC_sources[itemId].token_id
                        if tokenId and BISTBC_sources[tokenId] then
                            local tokenSource = BISTBC_sources[tokenId].source
                            zone = getSourceZone(tokenSource)
                            if zone then
                                sourceStr = tokenSource
                            end
                        end
                    end

                    local groupName
                    if zone then
                        groupName = zone
                    elseif category == "Vendor" or category == "PvP" then
                        groupName = "Vendor / PvP"
                    elseif category == "Quest" then
                        groupName = "Quest Rewards"
                    elseif category == "Crafted" then
                        groupName = "Crafted"
                    else
                        groupName = "Other"
                    end

                    if not groups[groupName] then
                        groups[groupName] = {}
                        table.insert(groupOrder, groupName)
                    end

                    local alreadyAdded = false
                    for _, existing in ipairs(groups[groupName]) do
                        if existing.itemId == itemId then
                            alreadyAdded = true
                            break
                        end
                    end
                    if not alreadyAdded then
                        table.insert(groups[groupName], {
                            rank = rank,
                            itemId = itemId,
                            source = sourceStr,
                            slotName = slot.slot_name,
                            slot = slot,
                        })
                    end
                end
            end
        end
    end

    -- Sort: zone groups alphabetically first, non-zone groups at end
    local nonZoneGroups = { ["Vendor / PvP"] = true, ["Quest Rewards"] = true, ["Crafted"] = true, ["Other"] = true }
    table.sort(groupOrder, function(a, b)
        local aNonZone = nonZoneGroups[a] or false
        local bNonZone = nonZoneGroups[b] or false
        if aNonZone ~= bNonZone then return not aNonZone end
        return a < b
    end)

    -- Update farm filter menu with current zones
    if farmFilterMenu then
        farmFilterMenu.zoneList = groupOrder
    end

    -- Check if nothing is missing (before zone filter)
    local totalMissing = 0
    for _, items in pairs(groups) do
        totalMissing = totalMissing + #items
    end

    if totalMissing == 0 then
        local msg = scrollChild:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        msg:SetPoint("TOP", scrollChild, "TOP", 0, -40)
        msg:SetFont("Fonts\\FRIZQT__.TTF", 14, "")
        msg:SetTextColor(0.4, 1, 0.4, 1)
        msg:SetText("You have all BiS items for this phase!")
        table.insert(contentRows, msg)
        scrollChild:SetHeight(100)
        return
    end

    local yOffset = -4
    local globalRowIndex = 0

    for _, groupName in ipairs(groupOrder) do
        -- Skip zones the user has excluded
        if farmExcludedZones[groupName] then
            -- skip
        else
        local items = groups[groupName]
        if items and #items > 0 then
            -- Sort items within group by rank (#1 first)
            table.sort(items, function(a, b)
                return a.rank < b.rank
            end)

            -- Group header with count
            local headerText = groupName .. "  (" .. #items .. " item" .. (#items > 1 and "s" or "") .. " needed)"
            local header, headerHeight = createSlotHeader(scrollChild, headerText, yOffset)
            table.insert(contentRows, header)
            yOffset = yOffset - headerHeight

            for _, item in ipairs(items) do
                globalRowIndex = globalRowIndex + 1
                local row, rowHeight = createItemRow(scrollChild, item.rank, item.itemId, item.source, yOffset, globalRowIndex, item.slot)
                table.insert(contentRows, row)
                yOffset = yOffset - rowHeight
            end

            yOffset = yOffset - 6
        end
        end -- farmExcludedZones else
    end

    scrollChild:SetHeight(math.abs(yOffset) + 20)
end

-- ============================================================================
-- Credits tab
-- ============================================================================

renderCredits = function()
    clearContent()
    if not scrollChild then return end

    local THANKS = {
        "Ghostofyotei",
        "Visanty",
        "Polarul",
        "Ferenar",
    }

    local yOffset = -20

    -- Header
    local title = scrollChild:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    title:SetPoint("TOP", scrollChild, "TOP", 0, yOffset)
    title:SetFont("Fonts\\FRIZQT__.TTF", 16, "")
    title:SetTextColor(1, 0.82, 0, 1)
    title:SetText("Special Thanks")
    table.insert(contentRows, title)
    yOffset = yOffset - 30

    -- Names
    for _, name in ipairs(THANKS) do
        local entry = scrollChild:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        entry:SetPoint("TOP", scrollChild, "TOP", 0, yOffset)
        entry:SetFont("Fonts\\FRIZQT__.TTF", 12, "")
        entry:SetTextColor(0.9, 0.9, 0.9, 1)
        entry:SetText(name)
        table.insert(contentRows, entry)
        yOffset = yOffset - 18
    end

    scrollChild:SetHeight(math.abs(yOffset))
end

local function refreshCurrentTab()
    if selectedTab == "Items" then
        buildZoneFilters()
        if zoneDropdown then
            reinitDropdown(zoneDropdown, zoneList, selectedZoneIndex, onZoneChanged)
        end
        renderContent()
    elseif selectedTab == "Gems" then
        renderGems()
    elseif selectedTab == "Enchants" then
        renderEnchants()
    elseif selectedTab == "Cons." then
        renderConsumables()
    elseif selectedTab == "Custom" then
        renderCustomList()
    elseif selectedTab == "Farm" then
        renderFarm()
    end
end

-- ============================================================================
-- Tab switching & onChange handlers
-- ============================================================================

switchTab = function(tabName)
    selectedTab = tabName

    -- Update tab button visuals
    for name, btn in pairs(tabButtons) do
        btn:SetActive(name == tabName)
    end

    -- Show/hide tab-specific controls
    local isItems = (tabName == "Items")
    local isCustom = (tabName == "Custom")

    if levelingPanel then
        if isItems then
            updateLevelingInfo()
        else
            levelingPanel:Hide()
        end
    end

    -- Show/hide items-only controls
    for _, ctrl in ipairs(itemsTabControls) do
        if isItems then ctrl:Show() else ctrl:Hide() end
    end

    -- Show search box only on Items tab
    if searchBoxFrame then
        if isItems then searchBoxFrame:Show() else searchBoxFrame:Hide() end
    end

    -- Show slot panel only on Items tab (and if enabled in settings)
    local showPaperdoll = not BISTBCAddon.db or not BISTBCAddon.db.char or BISTBCAddon.db.char.show_paperdoll ~= false
    if slotPanel then
        if isItems and showPaperdoll then
            slotPanel:Show()
            updatePaperDollIcons()
        else
            slotPanel:Hide()
        end
    end

    -- Reset slot filter when leaving Items tab
    if not isItems then
        wipe(selectedSlotFilter)
        if slotButtons then
            for _, sbtn in pairs(slotButtons) do
                sbtn.border:Hide()
                sbtn.icon:SetDesaturated(true)
                sbtn.icon:SetAlpha(0.5)
            end
        end
    end

    -- Show edit button only on Custom tab
    if editButton then
        if isCustom then editButton:Show() else editButton:Hide() end
    end

    -- Show farm filter button only on Farm tab
    local isFarm = (tabName == "Farm")
    if farmFilterButton then
        if isFarm then farmFilterButton:Show() else farmFilterButton:Hide() end
    end
    if farmFilterMenu and not isFarm then
        farmFilterMenu:Hide()
    end

    -- Reset edit mode when leaving Custom tab
    if not isCustom then customEditMode = false end

    -- Render appropriate content
    if tabName == "Items" then
        renderContent()
    elseif tabName == "Gems" then
        renderGems()
    elseif tabName == "Enchants" then
        renderEnchants()
    elseif tabName == "Cons." then
        renderConsumables()
    elseif tabName == "Custom" then
        renderCustomList()
    elseif tabName == "Farm" then
        renderFarm()
    elseif tabName == "Credits" then
        renderCredits()
    end
end

onClassChanged = function(index)
    selectedClassIndex = index
    selectedClass = BISTBC_classes[index].name
    selectedSpecIndex = 1
    selectedSpec = BISTBC_classes[index].specs[1]
    updateAccentBar()

    local specNames = {}
    for _, specName in ipairs(BISTBC_classes[index].specs) do
        table.insert(specNames, specName)
    end
    reinitDropdown(specDropdown, specNames, 1, onSpecChanged)

    saveData()
    updateStatusText()
    updateLevelingInfo()
    updatePaperDollIcons()
    refreshCurrentTab()
end

onSpecChanged = function(index)
    selectedSpecIndex = index
    if selectedClassIndex and BISTBC_classes[selectedClassIndex] then
        selectedSpec = BISTBC_classes[selectedClassIndex].specs[index]
    end
    saveData()
    updateStatusText()
    updateLevelingInfo()
    updatePaperDollIcons()
    refreshCurrentTab()
end

onPhaseChanged = function(index)
    selectedPhaseIndex = index
    selectedPhase = phases[index]
    saveData()
    updateStatusText()
    updatePaperDollIcons()
    refreshCurrentTab()
end

onSourceFilterChanged = function(index)
    selectedSourceFilterIndex = index
    renderContent()
end

onZoneChanged = function(index)
    selectedZoneIndex = index
    renderContent()
end

local function buildClassNames()
    local names = {}
    for _, classData in ipairs(BISTBC_classes) do
        table.insert(names, classData.name)
    end
    return names
end

local function buildSpecNames(classIndex)
    local names = {}
    if classIndex and BISTBC_classes[classIndex] then
        for _, specName in ipairs(BISTBC_classes[classIndex].specs) do
            table.insert(names, specName)
        end
    end
    return names
end

function BISTBCAddon:createMainFrame()
    if mainFrame then
        mainFrame:Hide()
        mainFrame = nil
        return
    end

    -- Reset tab-specific state
    wipe(tabButtons)
    wipe(itemsTabControls)
    searchBoxFrame = nil

    -- Main frame
    mainFrame = createBackdropFrame("BISTBCMainFrame", UIParent, 0.05, 0.05, 0.05, 0.94, 0.2, 0.2, 0.2, 1)
    mainFrame:SetSize(680, 560)
    mainFrame:SetPoint("CENTER")
    mainFrame:SetMovable(true)
    mainFrame:EnableMouse(true)
    mainFrame:SetClampedToScreen(true)
    mainFrame:SetFrameStrata("DIALOG")
    mainFrame:SetToplevel(true)
    mainFrame:SetResizable(true)
    mainFrame:SetResizeBounds(500, 400, 1200, 900)

    table.insert(UISpecialFrames, "BISTBCMainFrame")

    -- Resize grip (bottom-right corner)
    local resizeBtn = CreateFrame("Button", nil, mainFrame)
    resizeBtn:SetSize(16, 16)
    resizeBtn:SetPoint("BOTTOMRIGHT", mainFrame, "BOTTOMRIGHT", -2, 2)
    resizeBtn:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    resizeBtn:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
    resizeBtn:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
    resizeBtn:SetScript("OnMouseDown", function(self, button)
        if button == "LeftButton" then
            mainFrame:StartSizing("BOTTOMRIGHT")
        end
    end)
    resizeBtn:SetScript("OnMouseUp", function(self, button)
        mainFrame:StopMovingOrSizing()
        if scrollChild then
            scrollChild:SetWidth(scrollFrame:GetWidth())
        end
        refreshCurrentTab()
    end)

    -- Class-colored accent bar
    accentBar = mainFrame:CreateTexture(nil, "ARTWORK")
    accentBar:SetSize(678, 3)
    accentBar:SetPoint("TOPLEFT", mainFrame, "TOPLEFT", 1, -1)
    accentBar:SetPoint("TOPRIGHT", mainFrame, "TOPRIGHT", -1, -1)
    accentBar:SetColorTexture(1, 0.82, 0, 0.8)
    updateAccentBar()

    -- Title bar (draggable)
    local titleBar = CreateFrame("Frame", nil, mainFrame)
    titleBar:SetHeight(32)
    titleBar:SetPoint("TOPLEFT", mainFrame, "TOPLEFT", 0, -3)
    titleBar:SetPoint("TOPRIGHT", mainFrame, "TOPRIGHT", 0, -3)
    titleBar:EnableMouse(true)
    titleBar:RegisterForDrag("LeftButton")
    titleBar:SetScript("OnDragStart", function() mainFrame:StartMoving() end)
    titleBar:SetScript("OnDragStop", function() mainFrame:StopMovingOrSizing() end)

    local titleText = titleBar:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    titleText:SetPoint("LEFT", titleBar, "LEFT", 14, 0)
    titleText:SetFont("Fonts\\FRIZQT__.TTF", 13, "")
    titleText:SetTextColor(0.9, 0.9, 0.9, 1)
    titleText:SetText(BISTBCAddon.AddonNameAndVersion)

    local closeBtn = CreateFrame("Button", nil, titleBar, "UIPanelCloseButton")
    closeBtn:SetPoint("TOPRIGHT", mainFrame, "TOPRIGHT", -2, -2)
    closeBtn:SetScript("OnClick", function()
        mainFrame:Hide()
        mainFrame = nil
    end)

    -- Credits link on title bar
    local creditsBtn = CreateFrame("Button", nil, titleBar)
    creditsBtn:SetSize(50, 20)
    creditsBtn:SetPoint("RIGHT", closeBtn, "LEFT", -4, 0)
    local creditsLabel = creditsBtn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    creditsLabel:SetAllPoints()
    creditsLabel:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    creditsLabel:SetTextColor(0.5, 0.5, 0.5, 1)
    creditsLabel:SetText("Credits")
    creditsBtn:SetScript("OnEnter", function() creditsLabel:SetTextColor(1, 0.82, 0, 1) end)
    creditsBtn:SetScript("OnLeave", function()
        if selectedTab ~= "Credits" then creditsLabel:SetTextColor(0.5, 0.5, 0.5, 1) end
    end)
    creditsBtn:SetScript("OnClick", function()
        if selectedTab == "Credits" then
            switchTab("Items")
            creditsLabel:SetTextColor(0.5, 0.5, 0.5, 1)
        else
            switchTab("Credits")
            creditsLabel:SetTextColor(1, 0.82, 0, 1)
        end
    end)

    -- Dropdown area
    local dropdownArea = CreateFrame("Frame", nil, mainFrame)
    dropdownArea:SetHeight(40)
    dropdownArea:SetPoint("LEFT", mainFrame, "LEFT", 10, 0)
    dropdownArea:SetPoint("RIGHT", mainFrame, "RIGHT", -10, 0)
    dropdownArea:SetPoint("TOP", titleBar, "BOTTOM", 0, 0)

    local classNames = buildClassNames()
    classDropdown = createDropdown(dropdownArea, 90, classNames, selectedClassIndex, onClassChanged)
    classDropdown:SetPoint("TOPLEFT", dropdownArea, "TOPLEFT", 10, -9)

    local specNames = buildSpecNames(selectedClassIndex)
    specDropdown = createDropdown(dropdownArea, 120, specNames, selectedSpecIndex, onSpecChanged)
    specDropdown:SetPoint("LEFT", classDropdown, "RIGHT", 6, 0)

    phaseDropdown = createDropdown(dropdownArea, 70, phases, selectedPhaseIndex, onPhaseChanged)
    phaseDropdown:SetPoint("LEFT", specDropdown, "RIGHT", 6, 0)

    -- Source filter (Items tab only)
    sourceFilterDropdown = createDropdown(dropdownArea, 60, sourceFilters, selectedSourceFilterIndex, onSourceFilterChanged)
    sourceFilterDropdown:SetPoint("LEFT", phaseDropdown, "RIGHT", 6, 0)
    table.insert(itemsTabControls, sourceFilterDropdown)

    -- Zone filter (Items tab only)
    buildZoneFilters()
    zoneDropdown = createDropdown(dropdownArea, 80, zoneList, selectedZoneIndex, onZoneChanged)
    zoneDropdown:SetPoint("LEFT", sourceFilterDropdown, "RIGHT", 6, 0)
    table.insert(itemsTabControls, zoneDropdown)

    -- Separator line below dropdowns
    local sepLine = mainFrame:CreateTexture(nil, "ARTWORK")
    sepLine:SetColorTexture(0.25, 0.25, 0.25, 0.8)
    sepLine:SetHeight(1)
    sepLine:SetPoint("TOPLEFT", dropdownArea, "BOTTOMLEFT", 0, -2)
    sepLine:SetPoint("TOPRIGHT", dropdownArea, "BOTTOMRIGHT", 0, -2)

    -- Tab bar
    local tabBar = CreateFrame("Frame", nil, mainFrame)
    tabBar:SetHeight(24)
    tabBar:SetPoint("LEFT", mainFrame, "LEFT", 12, 0)
    tabBar:SetPoint("RIGHT", mainFrame, "RIGHT", -12, 0)
    tabBar:SetPoint("TOP", sepLine, "BOTTOM", 0, -3)

    local tabNames = { "Items", "Gems", "Enchants", "Cons.", "Custom", "Farm" }
    local xOff = 10
    for _, tName in ipairs(tabNames) do
        local btn = createTabButton(tabBar, tName, xOff, function() switchTab(tName) end)
        tabButtons[tName] = btn
        xOff = xOff + 72
    end

    -- Edit button (Custom tab only)
    editButton = createBackdropFrame(nil, tabBar, 0.12, 0.15, 0.12, 0.9, 0.3, 0.5, 0.3, 1)
    editButton:SetSize(50, 22)
    editButton:SetPoint("RIGHT", tabBar, "RIGHT", -10, 0)
    editButton:EnableMouse(true)
    local editLabel = editButton:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    editLabel:SetPoint("CENTER")
    editLabel:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    editLabel:SetTextColor(0.5, 0.9, 0.5, 1)
    editLabel:SetText("Edit")
    editButton.label = editLabel
    editButton:SetScript("OnMouseUp", function(self, button)
        if button == "LeftButton" then
            customEditMode = not customEditMode
            if customEditMode then
                self:SetBackdropColor(0.20, 0.25, 0.20, 1)
                self:SetBackdropBorderColor(0.4, 0.8, 0.4, 1)
                editLabel:SetTextColor(0.4, 1, 0.4, 1)
                editLabel:SetText("Done")
            else
                self:SetBackdropColor(0.12, 0.15, 0.12, 0.9)
                self:SetBackdropBorderColor(0.3, 0.5, 0.3, 1)
                editLabel:SetTextColor(0.5, 0.9, 0.5, 1)
                editLabel:SetText("Edit")
            end
            renderCustomList()
        end
    end)
    editButton:SetScript("OnEnter", function(self)
        self:SetBackdropColor(0.18, 0.22, 0.18, 1)
    end)
    editButton:SetScript("OnLeave", function(self)
        if customEditMode then
            self:SetBackdropColor(0.20, 0.25, 0.20, 1)
        else
            self:SetBackdropColor(0.12, 0.15, 0.12, 0.9)
        end
    end)
    editButton:Hide() -- Only visible on Custom tab

    -- Farm zone filter button (Farm tab only)
    farmFilterButton = createBackdropFrame(nil, tabBar, 0.12, 0.12, 0.15, 0.9, 0.3, 0.3, 0.5, 1)
    farmFilterButton:SetSize(60, 22)
    farmFilterButton:SetPoint("RIGHT", tabBar, "RIGHT", -10, 0)
    farmFilterButton:EnableMouse(true)
    local farmFilterLabel = farmFilterButton:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    farmFilterLabel:SetPoint("CENTER")
    farmFilterLabel:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    farmFilterLabel:SetTextColor(0.7, 0.7, 0.9, 1)
    farmFilterLabel:SetText("Zones \226\150\188")

    -- Farm filter multi-check menu
    farmFilterMenu = createBackdropFrame(nil, UIParent, 0.08, 0.08, 0.08, 0.97, 0.30, 0.30, 0.30, 1)
    farmFilterMenu:SetFrameStrata("FULLSCREEN_DIALOG")
    farmFilterMenu:SetClampedToScreen(true)
    farmFilterMenu:Hide()
    farmFilterMenu.zoneList = {}

    local function buildFarmFilterMenu()
        for _, child in ipairs({farmFilterMenu:GetChildren()}) do
            child:Hide()
            child:SetParent(nil)
        end

        local zones = farmFilterMenu.zoneList or {}
        if #zones == 0 then
            farmFilterMenu:Hide()
            return
        end

        local rowH = 20
        local menuWidth = 180

        -- Check if all zones are currently visible
        local allVisible = true
        for _, z in ipairs(zones) do
            if farmExcludedZones[z] then allVisible = false; break end
        end

        local totalH = (#zones + 1) * rowH + 6  -- +1 for toggle all row, +6 for separator

        farmFilterMenu:SetSize(menuWidth, totalH)
        farmFilterMenu:ClearAllPoints()
        farmFilterMenu:SetPoint("TOPRIGHT", farmFilterButton, "BOTTOMRIGHT", 0, -2)

        -- Toggle All row
        local toggleRow = CreateFrame("Frame", nil, farmFilterMenu)
        toggleRow:SetSize(menuWidth - 2, rowH)
        toggleRow:SetPoint("TOPLEFT", farmFilterMenu, "TOPLEFT", 1, -2)
        toggleRow:EnableMouse(true)

        local toggleLabel = toggleRow:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        toggleLabel:SetPoint("LEFT", toggleRow, "LEFT", 8, 0)
        toggleLabel:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
        toggleLabel:SetJustifyH("LEFT")
        if allVisible then
            toggleLabel:SetText("Deselect All")
            toggleLabel:SetTextColor(1, 0.5, 0.5, 1)
        else
            toggleLabel:SetText("Select All")
            toggleLabel:SetTextColor(0.5, 1, 0.5, 1)
        end

        local toggleHighlight = toggleRow:CreateTexture(nil, "BACKGROUND", nil, 1)
        toggleHighlight:SetAllPoints()
        toggleHighlight:SetColorTexture(1, 1, 1, 0.08)
        toggleHighlight:Hide()
        toggleRow:SetScript("OnEnter", function() toggleHighlight:Show() end)
        toggleRow:SetScript("OnLeave", function() toggleHighlight:Hide() end)
        toggleRow:SetScript("OnMouseUp", function(_, button)
            if button == "LeftButton" then
                if allVisible then
                    for _, z in ipairs(zones) do
                        farmExcludedZones[z] = true
                    end
                else
                    wipe(farmExcludedZones)
                end
                buildFarmFilterMenu()
                renderFarm()
            end
        end)

        -- Separator line
        local sep = farmFilterMenu:CreateTexture(nil, "ARTWORK")
        sep:SetColorTexture(0.3, 0.3, 0.3, 0.8)
        sep:SetHeight(1)
        sep:SetPoint("TOPLEFT", toggleRow, "BOTTOMLEFT", 4, -1)
        sep:SetPoint("TOPRIGHT", toggleRow, "BOTTOMRIGHT", -4, -1)

        local yStart = rowH + 4  -- after toggle row + separator

        for i, zoneName in ipairs(zones) do
            local row = CreateFrame("Frame", nil, farmFilterMenu)
            row:SetSize(menuWidth - 2, rowH)
            row:SetPoint("TOPLEFT", farmFilterMenu, "TOPLEFT", 1, -(yStart + (i - 1) * rowH))
            row:EnableMouse(true)

            local isChecked = not farmExcludedZones[zoneName]

            local checkMark = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
            checkMark:SetPoint("LEFT", row, "LEFT", 6, 0)
            checkMark:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
            if isChecked then
                checkMark:SetText("\226\156\148")  -- checkmark
                checkMark:SetTextColor(0.4, 1, 0.4, 1)
            else
                checkMark:SetText(" ")
                checkMark:SetTextColor(0.5, 0.5, 0.5, 1)
            end

            local rowLabel = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
            rowLabel:SetPoint("LEFT", checkMark, "RIGHT", 4, 0)
            rowLabel:SetPoint("RIGHT", row, "RIGHT", -8, 0)
            rowLabel:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
            rowLabel:SetJustifyH("LEFT")
            rowLabel:SetWordWrap(false)
            rowLabel:SetText(zoneName)
            if isChecked then
                rowLabel:SetTextColor(0.85, 0.85, 0.85, 1)
            else
                rowLabel:SetTextColor(0.4, 0.4, 0.4, 1)
            end

            local highlight = row:CreateTexture(nil, "BACKGROUND", nil, 1)
            highlight:SetAllPoints()
            highlight:SetColorTexture(1, 1, 1, 0.08)
            highlight:Hide()

            row:SetScript("OnEnter", function() highlight:Show() end)
            row:SetScript("OnLeave", function() highlight:Hide() end)
            row:SetScript("OnMouseUp", function(_, button)
                if button == "LeftButton" then
                    farmExcludedZones[zoneName] = not farmExcludedZones[zoneName] or nil
                    buildFarmFilterMenu()
                    renderFarm()
                end
            end)
        end
    end

    farmFilterButton:SetScript("OnMouseUp", function(_, button)
        if button == "LeftButton" then
            if farmFilterMenu:IsShown() then
                farmFilterMenu:Hide()
            else
                if activeDropdownMenu and activeDropdownMenu ~= farmFilterMenu then
                    activeDropdownMenu:Hide()
                end
                buildFarmFilterMenu()
                farmFilterMenu:Show()
                activeDropdownMenu = farmFilterMenu
            end
        end
    end)
    farmFilterButton:SetScript("OnEnter", function(self)
        self:SetBackdropColor(0.16, 0.16, 0.20, 0.9)
    end)
    farmFilterButton:SetScript("OnLeave", function(self)
        self:SetBackdropColor(0.12, 0.12, 0.15, 0.9)
    end)
    farmFilterButton:Hide() -- Only visible on Farm tab

    -- Search box (Items tab only)
    searchBoxFrame = CreateFrame("Frame", nil, mainFrame)
    searchBoxFrame:SetSize(200, 22)
    searchBoxFrame:SetPoint("RIGHT", tabBar, "RIGHT", -10, 0)

    local searchEB = CreateFrame("EditBox", "BISTBCSearchBox", searchBoxFrame, "InputBoxTemplate")
    searchEB:SetSize(190, 20)
    searchEB:SetPoint("RIGHT", searchBoxFrame, "RIGHT", -4, 0)
    searchEB:SetAutoFocus(false)
    searchEB:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    searchEB:SetMaxLetters(40)

    local searchLabel = searchBoxFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    searchLabel:SetPoint("RIGHT", searchEB, "LEFT", -4, 0)
    searchLabel:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    searchLabel:SetTextColor(0.6, 0.6, 0.6, 1)
    searchLabel:SetText("Search:")

    local debounceTimer = nil
    searchEB:SetScript("OnTextChanged", function(self, isUserInput)
        if not isUserInput then return end
        if debounceTimer then debounceTimer:Cancel() end
        debounceTimer = C_Timer.NewTimer(0.25, function()
            searchText = strtrim(self:GetText())
            renderContent()
        end)
    end)
    searchEB:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    searchEB:SetScript("OnEnterPressed", function(self) self:ClearFocus() end)
    searchBox = searchEB

    -- Separator below tabs
    local sepLine2 = mainFrame:CreateTexture(nil, "ARTWORK")
    sepLine2:SetColorTexture(0.25, 0.25, 0.25, 0.8)
    sepLine2:SetHeight(1)
    sepLine2:SetPoint("TOPLEFT", tabBar, "BOTTOMLEFT", 0, -3)
    sepLine2:SetPoint("TOPRIGHT", tabBar, "BOTTOMRIGHT", 0, -3)

    -- Leveling info panel (Items tab only)
    levelingPanel = createBackdropFrame(nil, mainFrame, 0.08, 0.08, 0.10, 0.85, 0.15, 0.15, 0.20, 0.6)
    levelingPanel:SetHeight(36)
    levelingPanel:SetPoint("LEFT", mainFrame, "LEFT", 12, 0)
    levelingPanel:SetPoint("RIGHT", mainFrame, "RIGHT", -12, 0)
    levelingPanel:SetPoint("TOP", sepLine2, "BOTTOM", 0, -3)

    levelingStatsText = levelingPanel:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    levelingStatsText:SetPoint("TOPLEFT", levelingPanel, "TOPLEFT", 8, -4)
    levelingStatsText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    levelingStatsText:SetTextColor(0.85, 0.85, 0.85, 1)
    levelingStatsText:SetJustifyH("LEFT")
    levelingStatsText:SetWidth(640)

    levelingSuffixesText = levelingPanel:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    levelingSuffixesText:SetPoint("TOPLEFT", levelingStatsText, "BOTTOMLEFT", 0, -3)
    levelingSuffixesText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    levelingSuffixesText:SetTextColor(0.7, 0.85, 0.55, 1)
    levelingSuffixesText:SetJustifyH("LEFT")
    levelingSuffixesText:SetWidth(640)

    levelingPanel:Hide()
    updateLevelingInfo()

    -- Separator below leveling panel
    local sepLine3 = mainFrame:CreateTexture(nil, "ARTWORK")
    sepLine3:SetColorTexture(0.25, 0.25, 0.25, 0.8)
    sepLine3:SetHeight(1)
    sepLine3:SetPoint("LEFT", mainFrame, "LEFT", 12, 0)
    sepLine3:SetPoint("RIGHT", mainFrame, "RIGHT", -12, 0)
    sepLine3:SetPoint("TOP", levelingPanel, "BOTTOM", 0, -3)

    -- Paper doll slot panel (left side, Items tab only)
    createPaperDollPanel(mainFrame)
    slotPanel:SetPoint("TOPLEFT", sepLine3, "BOTTOMLEFT", 4, -4)

    -- Scroll frame for content (offset to the right to make room for slot panel)
    local slotPanelWidth = slotPanel:GetWidth() + 6
    scrollFrame = CreateFrame("ScrollFrame", "BISTBCScrollFrame", mainFrame, "UIPanelScrollFrameTemplate")
    scrollFrame:SetPoint("TOPLEFT", sepLine3, "BOTTOMLEFT", slotPanelWidth, -4)
    scrollFrame:SetPoint("BOTTOMRIGHT", mainFrame, "BOTTOMRIGHT", -26, 30)

    local scrollBar = scrollFrame.ScrollBar or _G["BISTBCScrollFrameScrollBar"]
    if scrollBar then
        scrollBar:SetPoint("TOPLEFT", scrollFrame, "TOPRIGHT", 4, -16)
        scrollBar:SetPoint("BOTTOMLEFT", scrollFrame, "BOTTOMRIGHT", 4, 16)
    end

    scrollChild = CreateFrame("Frame", nil, scrollFrame)
    scrollChild:SetSize(scrollFrame:GetWidth(), 1)
    scrollFrame:SetScrollChild(scrollChild)

    scrollFrame:SetScript("OnSizeChanged", function(self, width, height)
        scrollChild:SetWidth(width)
    end)

    -- Status bar
    local statusBar = createBackdropFrame(nil, mainFrame, 0.08, 0.08, 0.08, 0.9, 0.2, 0.2, 0.2, 0.8)
    statusBar:SetHeight(24)
    statusBar:SetPoint("BOTTOMLEFT", mainFrame, "BOTTOMLEFT", 1, 1)
    statusBar:SetPoint("BOTTOMRIGHT", mainFrame, "BOTTOMRIGHT", -1, 1)

    local statusText = statusBar:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    statusText:SetPoint("LEFT", statusBar, "LEFT", 10, 0)
    statusText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    statusText:SetTextColor(0.6, 0.6, 0.6, 1)
    mainFrame.statusText = statusText
    updateStatusText()

    -- Close dropdown menus when clicking the scroll area or main frame background
    local clickCatcher = CreateFrame("Frame", nil, mainFrame)
    clickCatcher:SetAllPoints(scrollFrame)
    clickCatcher:SetFrameLevel(scrollFrame:GetFrameLevel())
    clickCatcher:EnableMouse(false)
    mainFrame:HookScript("OnMouseUp", function()
        if activeDropdownMenu then
            activeDropdownMenu:Hide()
            activeDropdownMenu = nil
        end
    end)

    -- Activate initial tab
    switchTab(selectedTab)
end

-- ============================================================================
-- Initialization
-- ============================================================================

function BISTBCAddon:initBislists()
    loadData()
    LibStub("AceConsole-3.0"):RegisterChatCommand("bistbc", function()
        BISTBCAddon:createMainFrame()
    end, persist)
end
