local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local UI = {}
BigBiSList.UI = UI

local TAB_NAMES = { "Phase", "Planner", "Enhance", "Wishlist", "Settings" }
local MIN_WIDTH = 920
local MIN_HEIGHT = 560
local DEFAULT_WIDTH = 1040
local DEFAULT_HEIGHT = 660
local LEFT_RAIL_WIDTH = 190
local DETAILS_WIDTH = 270
local ROW_HEIGHT = 42

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

local function safeSetText(fontString, text)
    if fontString then
        fontString:SetText(text or "")
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
    local tabName = selection.tab

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
        tabName = "Phase"
    end

    BigBiSList:SetSelection(className, specName, phaseKey, tabName)
end

function UI:BuildOwnedItems()
    local owned = {}

    if GetInventoryItemID then
        for slot = 1, 19 do
            local itemId = GetInventoryItemID("player", slot)
            if itemId then
                owned[itemId] = "equipped"
            end
        end
    end

    for bag = 0, 4 do
        local numSlots = 0
        if C_Container and C_Container.GetContainerNumSlots then
            numSlots = C_Container.GetContainerNumSlots(bag) or 0
        elseif GetContainerNumSlots then
            numSlots = GetContainerNumSlots(bag) or 0
        end

        for slot = 1, numSlots do
            local itemId
            if C_Container and C_Container.GetContainerItemID then
                itemId = C_Container.GetContainerItemID(bag, slot)
            elseif GetContainerItemID then
                itemId = GetContainerItemID(bag, slot)
            end
            if itemId and not owned[itemId] then
                owned[itemId] = "bag"
            end
        end
    end

    return owned
end

function UI:BuildFilterPayload()
    local filters = self:GetFilters()
    return {
        search = filters.search,
        sourceType = filters.sourceType,
        zone = filters.zone,
        rankGroup = filters.rankGroup,
        ownedState = filters.ownedState,
        binding = filters.binding,
        boe = filters.boe,
        faction = filters.faction,
        longevity = filters.longevity,
        slots = filters.slots,
        ownedItems = self:BuildOwnedItems(),
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

function UI:RestoreWindow()
    local window = BigBiSListDB.profile.window
    local width = clamp(window.width or DEFAULT_WIDTH, MIN_WIDTH, 1400)
    local height = clamp(window.height or DEFAULT_HEIGHT, MIN_HEIGHT, 900)

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
    local labels = BigBiSList:GetSourceTypeLabels()
    local items = {
        { value = "all", text = labels.all, checked = filters.sourceType == "all" },
    }
    for _, sourceType in ipairs(BigBiSList:GetDataIndex().sourceTypes) do
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
    local items = {
        { value = "all", text = "All zones", checked = filters.zone == "all" },
    }
    for _, zone in ipairs(BigBiSList:GetDataIndex().zones) do
        table.insert(items, {
            value = zone,
            text = zone,
            checked = filters.zone == zone,
        })
    end
    return items
end

function UI:SetClass(className)
    local index = BigBiSList:GetDataIndex()
    local specs = index.specsByClass[className] or {}
    BigBiSList:SetSelection(className, firstSpecName(specs), nil, nil)
    self:Refresh()
end

function UI:SetSpec(specName)
    BigBiSList:SetSelection(nil, specName, nil, nil)
    self:Refresh()
end

function UI:SetPhase(phaseKey)
    BigBiSList:SetSelection(nil, nil, phaseKey, nil)
    self:Refresh()
end

function UI:SetTab(tabName)
    BigBiSList:SetSelection(nil, nil, nil, tabName)
    self:Refresh()
end

function UI:SetFilter(key, value)
    local filters = self:GetFilters()
    filters[key] = value
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

function UI:SetItemButton(button, itemId, nameText, fallbackName, fallbackQuality)
    button.itemId = itemId
    button.itemLink = nil
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
            UI:RefreshDetails(itemId)
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

function UI:CreateDataRow(parent, yOffset, data, mode)
    local widgets = BigBiSList.Widgets
    local row = widgets:CreateItemRow(parent, ROW_HEIGHT)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("RIGHT", parent, "RIGHT", -4, 0)
    row.itemId = data.item_id

    local iconButton = widgets:CreateIconButton(row, 30, function(_, buttonName)
        if buttonName == "RightButton" then
            self:RefreshDetails(data.item_id)
        end
    end)
    iconButton:SetPoint("LEFT", row, "LEFT", 8, 0)

    local nameText = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    nameText:SetPoint("TOPLEFT", iconButton, "TOPRIGHT", 8, -2)
    nameText:SetPoint("RIGHT", row, "RIGHT", -178, 0)
    nameText:SetJustifyH("LEFT")
    nameText:SetWordWrap(false)

    local detailText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    detailText:SetPoint("TOPLEFT", nameText, "BOTTOMLEFT", 0, -3)
    detailText:SetPoint("RIGHT", row, "RIGHT", -178, 0)
    detailText:SetJustifyH("LEFT")
    detailText:SetWordWrap(false)
    detailText:SetTextColor(0.68, 0.68, 0.72, 1)

    local rightText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    rightText:SetPoint("RIGHT", row, "RIGHT", -8, 7)
    rightText:SetWidth(158)
    rightText:SetJustifyH("RIGHT")
    rightText:SetWordWrap(false)
    rightText:SetTextColor(0.66, 0.78, 0.94, 1)

    local sourceText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    sourceText:SetPoint("RIGHT", row, "RIGHT", -8, -9)
    sourceText:SetWidth(158)
    sourceText:SetJustifyH("RIGHT")
    sourceText:SetWordWrap(false)
    sourceText:SetTextColor(0.54, 0.54, 0.58, 1)

    local item = data.item or BigBiSList:GetItemData(data.item_id)
    self:SetItemButton(iconButton, data.item_id, nameText, data.name, item and item.quality)

    if mode == "planner" then
        safeSetText(detailText, data.slot .. " - " .. data.priorityTier .. " - " .. table.concat(data.reasons or {}, ", "))
        safeSetText(rightText, tostring(data.priority or 0) .. "/100")
        safeSetText(sourceText, data.source_summary or "")
    elseif mode == "enhance" then
        safeSetText(detailText, data.detail or "")
        safeSetText(rightText, "Enhance")
        safeSetText(sourceText, data.source_summary or "")
    elseif mode == "wishlist" then
        safeSetText(detailText, data.detail or "")
        safeSetText(rightText, "Wishlisted")
        safeSetText(sourceText, data.source_summary or "")
    else
        local owned = self.currentOwned and self.currentOwned[data.item_id]
        local ownedText = owned == "equipped" and "Equipped - " or (owned == "bag" and "In bags - " or "")
        safeSetText(detailText, ownedText .. (data.rank_label or "Option") .. " - " .. (data.source_type_label or "Source"))
        safeSetText(rightText, data.slot or "")
        safeSetText(sourceText, data.source_summary or "")
    end

    row:SetScript("OnMouseUp", function(_, buttonName)
        if buttonName == "LeftButton" then
            self:RefreshDetails(data.item_id)
        elseif buttonName == "RightButton" then
            if BigBiSListDB.char.wishlist[tostring(data.item_id)] then
                self:RemoveWishlist(data.item_id)
            else
                self:AddWishlist(data.item_id)
            end
        end
    end)

    return row, ROW_HEIGHT
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
        self:RenderEmpty("No matching BiS rows. Clear filters or choose another phase.")
        return
    end

    local yOffset = -2
    for _, group in ipairs(groups) do
        local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, group.slot, yOffset)
        yOffset = yOffset - headerHeight

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
        self:RenderEmpty("No planner rows match the current filters.")
        return
    end

    local title = "Priority planner for " .. BigBiSList:GetPhaseDisplayName(selection.phase)
    local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, title, -2)
    local yOffset = -2 - headerHeight

    for _, rowData in ipairs(rows) do
        local row, rowHeight = self:CreateDataRow(self.contentChild, yOffset, rowData, "planner")
        yOffset = yOffset - rowHeight - 4
    end

    self:SetContentHeight(yOffset)
end

function UI:RenderEnhanceTab()
    local widgets = BigBiSList.Widgets
    local selection = self:GetSelection()
    local sections = BigBiSList:GetEnhancementRows(selection.class, selection.spec, selection.phase)
    local yOffset = -2
    local rendered = false

    for _, section in ipairs(sections) do
        if #section.rows > 0 then
            rendered = true
            local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, section.title, yOffset)
            yOffset = yOffset - headerHeight
            for _, rowData in ipairs(section.rows) do
                local row, rowHeight = self:CreateDataRow(self.contentChild, yOffset, rowData, "enhance")
                yOffset = yOffset - rowHeight - 4
            end
            yOffset = yOffset - 6
        end
    end

    if not rendered then
        self:RenderEmpty("No gems, enchants, or consumables are available for this selection yet.")
        return
    end

    self:SetContentHeight(yOffset)
end

function UI:RenderWishlistTab()
    local widgets = BigBiSList.Widgets
    local index = BigBiSList:GetDataIndex()
    local wishlist = BigBiSListDB.char.wishlist or {}
    local yOffset = -2

    if tableCount(wishlist) == 0 then
        self:RenderEmpty("No wishlist items yet. Right-click an item row or use the detail drawer to add one.")
        return
    end

    local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, "Wishlist", yOffset)
    yOffset = yOffset - headerHeight

    local ids = {}
    for key in pairs(wishlist) do
        table.insert(ids, tonumber(key) or key)
    end
    table.sort(ids, function(a, b)
        local itemA = index.itemsById[tonumber(a)]
        local itemB = index.itemsById[tonumber(b)]
        return lower(itemA and itemA.name or a) < lower(itemB and itemB.name or b)
    end)

    for _, itemId in ipairs(ids) do
        local item = index.itemsById[tonumber(itemId)]
        local uses = index.usesByItemId[tonumber(itemId)] or {}
        local bestUse = uses[1]
        local data = {
            item_id = tonumber(itemId),
            item = item,
            name = item and item.name or ("Item " .. tostring(itemId)),
            detail = bestUse and (bestUse.class .. " " .. bestUse.spec .. " - " .. bestUse.slot) or "Saved item",
            source_summary = item and item.source_summary or "",
        }
        local row, rowHeight = self:CreateDataRow(self.contentChild, yOffset, data, "wishlist")
        yOffset = yOffset - rowHeight - 4
    end

    self:SetContentHeight(yOffset)
end

function UI:CreateSettingToggle(parent, yOffset, labelText, getValue, setValue)
    local widgets = BigBiSList.Widgets
    local row = widgets:CreateItemRow(parent, 34)
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
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

function UI:RenderSettingsTab()
    local widgets = BigBiSList.Widgets
    local yOffset = -2
    local header, headerHeight = widgets:CreateSectionHeader(self.contentChild, "Settings", yOffset)
    yOffset = yOffset - headerHeight

    local profile = BigBiSListDB.profile
    local settings = {
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
        {
            label = "Lock window position",
            get = function() return profile.window.locked end,
            set = function(value) profile.window.locked = value end,
        },
    }

    for _, setting in ipairs(settings) do
        local row, rowHeight = self:CreateSettingToggle(self.contentChild, yOffset, setting.label, setting.get, setting.set)
        yOffset = yOffset - rowHeight - 4
    end

    self:SetContentHeight(yOffset)
end

function UI:RefreshDetails(itemId)
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
        return
    end

    self.selectedItemId = itemId
    local index = BigBiSList:GetDataIndex()
    local item = index.itemsById[itemId]
    local yOffset = -8

    local title = content:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    title:SetPoint("TOPLEFT", content, "TOPLEFT", 8, yOffset)
    title:SetPoint("RIGHT", content, "RIGHT", -8, 0)
    title:SetJustifyH("LEFT")
    title:SetWordWrap(true)
    title:SetText(item and item.name or ("Item " .. tostring(itemId)))
    local r, g, b = itemQualityColor(item)
    title:SetTextColor(r, g, b, 1)
    yOffset = yOffset - 38

    local source = content:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    source:SetPoint("TOPLEFT", content, "TOPLEFT", 8, yOffset)
    source:SetPoint("RIGHT", content, "RIGHT", -8, 0)
    source:SetJustifyH("LEFT")
    source:SetWordWrap(true)
    source:SetTextColor(0.76, 0.76, 0.80, 1)
    source:SetText(item and item.source_summary or "No source data")
    yOffset = yOffset - 46

    local uses = index.usesByItemId[itemId] or {}
    local phaseText = content:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    phaseText:SetPoint("TOPLEFT", content, "TOPLEFT", 8, yOffset)
    phaseText:SetPoint("RIGHT", content, "RIGHT", -8, 0)
    phaseText:SetJustifyH("LEFT")
    phaseText:SetWordWrap(true)

    local phases = {}
    for _, use in ipairs(uses) do
        phases[use.phase] = true
    end
    phaseText:SetText("Useful in: " .. (phaseLabelList(phases) ~= "" and phaseLabelList(phases) or "No known BiS list"))
    phaseText:SetTextColor(0.64, 0.78, 0.94, 1)
    yOffset = yOffset - 46

    local wishlistKey = tostring(itemId)
    local isWishlisted = BigBiSListDB.char.wishlist[wishlistKey]
    local wishlistButton = widgets:CreateTextButton(content, isWishlisted and "Remove wishlist" or "Add wishlist", 150, 24, function()
        if BigBiSListDB.char.wishlist[wishlistKey] then
            self:RemoveWishlist(itemId)
        else
            self:AddWishlist(itemId)
        end
        self:Refresh()
    end)
    wishlistButton:SetPoint("TOPLEFT", content, "TOPLEFT", 8, yOffset)

    local ignored = BigBiSListDB.char.ignoredItems[wishlistKey]
    local ignoreButton = widgets:CreateTextButton(content, ignored and "Unignore" or "Ignore", 86, 24, function()
        if BigBiSListDB.char.ignoredItems[wishlistKey] then
            self:UnignoreItem(itemId)
        else
            self:IgnoreItem(itemId)
        end
    end)
    ignoreButton:SetPoint("LEFT", wishlistButton, "RIGHT", 8, 0)
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

    for tabName, button in pairs(self.tabButtons or {}) do
        button:SetSelected(tabName == selection.tab)
    end

    for slotName, button in pairs(self.slotButtons or {}) do
        button:SetSelected(filters.slots and filters.slots[slotName])
    end

    self:RefreshFilterButtonLabels()
end

function UI:Refresh()
    if not self.frame then
        return
    end

    self:ValidateSelection()
    self:RefreshControls()

    BigBiSList.Widgets:ClearChildren(self.contentChild)
    self.contentChild:SetHeight(1)

    local tabName = self:GetSelection().tab
    if tabName == "Planner" then
        self:RenderPlannerTab()
    elseif tabName == "Enhance" then
        self:RenderEnhanceTab()
    elseif tabName == "Wishlist" then
        self:RenderWishlistTab()
    elseif tabName == "Settings" then
        self:RenderSettingsTab()
    else
        self:RenderPhaseTab()
    end

    self:RefreshDetails(self.selectedItemId)
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
        local button = widgets:CreateTextButton(tabBar, tabName, 86, 24, function()
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
    header:SetPoint("TOPLEFT", rail, "TOPLEFT", 10, -10)
    header:SetText("Filters")

    self.classDropdown = widgets:CreateDropdown("BigBiSListClassDropdown", rail, 130,
        function() return self:GetSelection().class or "Class" end,
        function() return self:GetClassDropdownItems() end,
        function(value) self:SetClass(value) end)
    self.classDropdown:SetPoint("TOPLEFT", rail, "TOPLEFT", -10, -34)

    self.specDropdown = widgets:CreateDropdown("BigBiSListSpecDropdown", rail, 130,
        function() return self:GetSelection().spec or "Spec" end,
        function() return self:GetSpecDropdownItems() end,
        function(value) self:SetSpec(value) end)
    self.specDropdown:SetPoint("TOPLEFT", self.classDropdown, "BOTTOMLEFT", 0, -2)

    local searchLabel = rail:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    searchLabel:SetPoint("TOPLEFT", self.specDropdown, "BOTTOMLEFT", 18, -8)
    searchLabel:SetTextColor(0.68, 0.68, 0.72, 1)
    searchLabel:SetText("Search")

    self.searchBox = CreateFrame("EditBox", "BigBiSListSearchBox", rail, "InputBoxTemplate")
    self.searchBox:SetSize(154, 22)
    self.searchBox:SetPoint("TOPLEFT", searchLabel, "BOTTOMLEFT", -4, -3)
    self.searchBox:SetAutoFocus(false)
    self.searchBox:SetMaxLetters(48)
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

    self.sourceDropdown = widgets:CreateDropdown("BigBiSListSourceDropdown", rail, 130,
        function()
            local value = self:GetFilters().sourceType or "all"
            return (BigBiSList:GetSourceTypeLabels()[value] or value)
        end,
        function() return self:GetSourceDropdownItems() end,
        function(value) self:SetFilter("sourceType", value) end)
    self.sourceDropdown:SetPoint("TOPLEFT", self.searchBox, "BOTTOMLEFT", -14, -8)

    self.zoneDropdown = widgets:CreateDropdown("BigBiSListZoneDropdown", rail, 130,
        function()
            local value = self:GetFilters().zone or "all"
            return value == "all" and "All zones" or value
        end,
        function() return self:GetZoneDropdownItems() end,
        function(value) self:SetFilter("zone", value) end)
    self.zoneDropdown:SetPoint("TOPLEFT", self.sourceDropdown, "BOTTOMLEFT", 0, -2)

    local rankButton = widgets:CreateTextButton(rail, "Rank: All", 154, 22, function()
        local filters = self:GetFilters()
        if filters.rankGroup == "all" then
            filters.rankGroup = "bis"
        elseif filters.rankGroup == "bis" then
            filters.rankGroup = "option"
        else
            filters.rankGroup = "all"
        end
        self:Refresh()
    end)
    rankButton:SetPoint("TOPLEFT", self.zoneDropdown, "BOTTOMLEFT", 18, -8)
    self.rankButton = rankButton

    local ownedButton = widgets:CreateTextButton(rail, "Owned: All", 154, 22, function()
        local filters = self:GetFilters()
        if filters.ownedState == "all" then
            filters.ownedState = "missing"
        elseif filters.ownedState == "missing" then
            filters.ownedState = "owned"
        else
            filters.ownedState = "all"
        end
        self:Refresh()
    end)
    ownedButton:SetPoint("TOPLEFT", rankButton, "BOTTOMLEFT", 0, -5)
    self.ownedButton = ownedButton

    local boeButton = widgets:CreateTextButton(rail, "BoE: All", 154, 22, function()
        local filters = self:GetFilters()
        if filters.boe == "all" then
            filters.boe = "boe"
        elseif filters.boe == "boe" then
            filters.boe = "not_boe"
        else
            filters.boe = "all"
        end
        self:Refresh()
    end)
    boeButton:SetPoint("TOPLEFT", ownedButton, "BOTTOMLEFT", 0, -5)
    self.boeButton = boeButton

    local longevityButton = widgets:CreateTextButton(rail, "Longevity: All", 154, 22, function()
        local filters = self:GetFilters()
        if filters.longevity == "all" then
            filters.longevity = "future"
        elseif filters.longevity == "future" then
            filters.longevity = "long"
        else
            filters.longevity = "all"
        end
        self:Refresh()
    end)
    longevityButton:SetPoint("TOPLEFT", boeButton, "BOTTOMLEFT", 0, -5)
    self.longevityButton = longevityButton

    local slotHeader = rail:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    slotHeader:SetPoint("TOPLEFT", longevityButton, "BOTTOMLEFT", 0, -12)
    slotHeader:SetTextColor(0.68, 0.68, 0.72, 1)
    slotHeader:SetText("Slots")

    local clearButton = widgets:CreateTextButton(rail, "Clear filters", 154, 24, function()
        self:ClearFilters()
    end)
    clearButton:SetPoint("BOTTOMLEFT", rail, "BOTTOMLEFT", 18, 10)

    local slotScroll, slotChild = widgets:CreateScrollFrame("BigBiSListSlotScroll", rail)
    slotScroll:SetPoint("TOPLEFT", slotHeader, "BOTTOMLEFT", -2, -4)
    slotScroll:SetPoint("BOTTOMRIGHT", clearButton, "TOPRIGHT", 20, 8)
    slotChild:SetWidth(160)

    self.slotButtons = {}
    local slotNames = BigBiSList:GetSlotOrder()
    for index, slotName in ipairs(slotNames) do
        local button = widgets:CreateTextButton(slotChild, slotName, 74, 20, function()
            self:ToggleSlot(slotName)
        end)
        local col = (index - 1) % 2
        local row = math.floor((index - 1) / 2)
        button:SetPoint("TOPLEFT", slotChild, "TOPLEFT", col * 80, -row * 23)
        self.slotButtons[slotName] = button
    end
    slotChild:SetHeight(math.ceil(#slotNames / 2) * 23 + 4)

    self.leftRail = rail
end

function UI:RefreshFilterButtonLabels()
    local filters = self:GetFilters()

    if self.rankButton then
        local label = filters.rankGroup == "all" and "All" or filters.rankGroup
        self.rankButton.label:SetText("Rank: " .. label)
    end
    if self.ownedButton then
        local label = filters.ownedState == "all" and "All" or filters.ownedState
        self.ownedButton.label:SetText("Owned: " .. label)
    end
    if self.boeButton then
        local label = filters.boe == "all" and "All" or filters.boe
        self.boeButton.label:SetText("BoE: " .. label)
    end
    if self.longevityButton then
        local label = filters.longevity == "all" and "All" or filters.longevity
        self.longevityButton.label:SetText("Longevity: " .. label)
    end
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

    local detailsContent = CreateFrame("Frame", nil, details)
    detailsContent:SetPoint("TOPLEFT", detailsTitle, "BOTTOMLEFT", -2, -8)
    detailsContent:SetPoint("BOTTOMRIGHT", details, "BOTTOMRIGHT", -8, 8)
    self.details = details
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

    if frame.SetResizeBounds then
        frame:SetResizeBounds(MIN_WIDTH, MIN_HEIGHT, 1400, 900)
    elseif frame.SetMinResize and frame.SetMaxResize then
        frame:SetMinResize(MIN_WIDTH, MIN_HEIGHT)
        frame:SetMaxResize(1400, 900)
    end

    ensureSpecialFrame("BigBiSListMainFrame")

    self.frame = frame
    self:RestoreWindow()
    self:CreateHeader(frame)
    self:CreatePhaseBar(frame)
    self:CreateTabBar(frame)
    self:CreateBody(frame)
    self:CreateStatusBar(frame)

    frame:SetScript("OnHide", function()
        self:SaveWindow()
    end)

    self:Refresh()
    return frame
end

function UI:Open()
    if not self.frame then
        self:CreateMainFrame()
    end

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
    frame:SetScript("OnEvent", function()
        self:RefreshUI()
    end)
    self.uiEventFrame = frame
end
