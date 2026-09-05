local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local Widgets = {}
BigBiSList.Widgets = Widgets

Widgets.Theme = {
    surface = { 0.055, 0.055, 0.065, 0.96 },
    control = { 0.09, 0.09, 0.105, 0.96 },
    hover = { 0.15, 0.15, 0.17, 0.98 },
    pressed = { 0.065, 0.065, 0.075, 1 },
    selected = { 0.18, 0.15, 0.075, 0.98 },
    border = { 0.26, 0.26, 0.29, 1 },
    accent = { 0.92, 0.76, 0.32, 1 },
    text = { 0.90, 0.90, 0.92, 1 },
    muted = { 0.68, 0.68, 0.72, 1 },
    disabled = { 0.42, 0.42, 0.46, 1 },
}

-- This order is shared with tools/generate_ui_icons.py. Each glyph occupies a
-- padded 32px cell in the addon-owned 256px atlas; no client atlas API is needed.
local ICON_KEYS = {
    "search", "clear", "starOutline", "starFilled", "sortAscending", "sortDescending",
    "chevronLeft", "chevronRight", "chevronDown", "chevronUp", "settings", "filter",
    "details", "check", "bag", "bank", "equipped", "clock", "warning", "info",
    "plus", "minus", "restore", "hide", "menu",
}
local ICON_INDEX = {}
for index, key in ipairs(ICON_KEYS) do ICON_INDEX[key] = index - 1 end

function Widgets:SetIcon(texture, key)
    if not texture then return false end
    local known = ICON_INDEX[key] ~= nil
    local index = ICON_INDEX[key] or ICON_INDEX.info
    local column, row = index % 8, math.floor(index / 8)
    texture:SetTexture("Interface\\AddOns\\BigBiSList\\assets\\ui-icons.tga")
    texture:SetTexCoord(column / 8, (column + 1) / 8, row / 8, (row + 1) / 8)
    texture.iconKey = known and key or "info"
    return known
end

local function appendScript(frame, event, callback)
    if frame.HookScript then
        frame:HookScript(event, callback)
    else
        local previous = frame.GetScript and frame:GetScript(event)
        frame:SetScript(event, function(self, ...)
            if previous then previous(self, ...) end
            callback(self, ...)
        end)
    end
end

local function hideOwnedTooltip(frame)
    if GameTooltip and (not GameTooltip.IsOwned or GameTooltip:IsOwned(frame)) then
        GameTooltip:Hide()
    end
end

function Widgets:BindTooltip(frame, callback)
    frame.__bigBisTooltip = callback
    if frame.__bigBisTooltipBound then return end
    frame.__bigBisTooltipBound = true
    appendScript(frame, "OnEnter", function(self)
        if self.SetHovered then self:SetHovered(true) end
        local content = self.__bigBisTooltip
        if not content or not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        if type(content) == "function" then
            local text = content(self, GameTooltip)
            if type(text) == "string" then GameTooltip:AddLine(text, 0.90, 0.90, 0.92, true) end
        else
            GameTooltip:AddLine(tostring(content), 0.90, 0.90, 0.92, true)
        end
        GameTooltip:Show()
    end)
    appendScript(frame, "OnLeave", function(self)
        if self.SetHovered then self:SetHovered(false) end
        hideOwnedTooltip(self)
    end)
    appendScript(frame, "OnHide", function(self)
        if self.SetHovered then self:SetHovered(false) end
        hideOwnedTooltip(self)
    end)
end

local dropdownCounter = 0
local DROPDOWN_LIST_BASE_LEVEL = 1000

local function resolveDropdownOwner(owner)
    if type(owner) == "string" and _G then
        return _G[owner]
    end
    return owner
end

local function isBigBisDropdownOwner(owner)
    owner = resolveDropdownOwner(owner)
    return type(owner) == "table" and owner.__bigBisListDropdown == true
end

local function restoreDropdownList(listFrame)
    local state = listFrame and listFrame.__bigBisListDropdownState
    if not state then
        return
    end
    if state.strata and listFrame.SetFrameStrata then
        listFrame:SetFrameStrata(state.strata)
    end
    if state.level and listFrame.SetFrameLevel then
        listFrame:SetFrameLevel(state.level)
    end
    if state.mouseEnabled ~= nil and listFrame.EnableMouse then
        listFrame:EnableMouse(state.mouseEnabled)
    end
    listFrame.__bigBisListDropdownState = nil
end

local function prepareDropdownList(listFrame, listIndex, explicitOwner)
    if not listFrame then
        return
    end

    if listFrame.IsShown and not listFrame:IsShown() then
        restoreDropdownList(listFrame)
        return
    end

    local requestedOwner = resolveDropdownOwner(explicitOwner)
    local actualOwner = resolveDropdownOwner(listFrame.dropdown or (_G and _G.UIDROPDOWNMENU_OPEN_MENU))
    if requestedOwner and actualOwner and requestedOwner ~= actualOwner then
        restoreDropdownList(listFrame)
        return
    end
    local owner = actualOwner or requestedOwner
    if not isBigBisDropdownOwner(owner) then
        restoreDropdownList(listFrame)
        return
    end

    if not listFrame.__bigBisListDropdownState then
        local mouseEnabled
        if listFrame.IsMouseEnabled then
            mouseEnabled = listFrame:IsMouseEnabled()
        end
        listFrame.__bigBisListDropdownState = {
            strata = listFrame.GetFrameStrata and listFrame:GetFrameStrata() or nil,
            level = listFrame.GetFrameLevel and listFrame:GetFrameLevel() or nil,
            mouseEnabled = mouseEnabled,
        }
    end

    if listFrame.SetFrameStrata then
        listFrame:SetFrameStrata("FULLSCREEN_DIALOG")
    end
    local previousLevel = listFrame.GetFrameLevel and listFrame:GetFrameLevel() or 0
    if listFrame.SetFrameLevel then
        listFrame:SetFrameLevel(math.max(previousLevel or 0, DROPDOWN_LIST_BASE_LEVEL + (listIndex or 1)))
    end
    if listFrame.EnableMouse then
        listFrame:EnableMouse(true)
    end
end

local function installDropdownListHook(listFrame, listIndex)
    if not listFrame then
        return
    end
    if not listFrame.__bigBisListDropdownListHooked and listFrame.HookScript then
        listFrame.__bigBisListDropdownListHooked = true
        listFrame:HookScript("OnShow", function(shownList)
            prepareDropdownList(shownList, listIndex)
        end)
        listFrame:HookScript("OnHide", function(hiddenList)
            restoreDropdownList(hiddenList)
        end)
    end
end

local function prepareDropdownLists(owner)
    local maxLevels = tonumber(UIDROPDOWNMENU_MAXLEVELS) or 2
    maxLevels = math.max(2, maxLevels)
    for listIndex = 1, maxLevels do
        local listFrame = _G and _G["DropDownList" .. listIndex]
        installDropdownListHook(listFrame, listIndex)
        if owner then
            prepareDropdownList(listFrame, listIndex, owner)
        end
    end
end

local function restoreDropdownLists()
    local maxLevels = math.max(2, tonumber(UIDROPDOWNMENU_MAXLEVELS) or 2)
    for listIndex = 1, maxLevels do
        restoreDropdownList(_G and _G["DropDownList" .. listIndex])
    end
end

function Widgets:CloseDropdownMenus()
    if type(CloseDropDownMenus) == "function" then
        CloseDropDownMenus()
        restoreDropdownLists()
        return true
    end

    local closed = false
    local maxLevels = math.max(2, tonumber(UIDROPDOWNMENU_MAXLEVELS) or 2)
    for listIndex = 1, maxLevels do
        local listFrame = _G and _G["DropDownList" .. listIndex]
        if listFrame and listFrame.Hide then
            listFrame:Hide()
            closed = true
        end
    end
    restoreDropdownLists()
    return closed
end

local function setBackdrop(frame, bg, border)
    if not frame.SetBackdrop then
        return
    end

    frame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })

    bg = bg or { 0.04, 0.04, 0.05, 0.94 }
    border = border or { 0.22, 0.22, 0.24, 1 }
    frame:SetBackdropColor(bg[1], bg[2], bg[3], frame.__bigBisStatusBadge and math.min(bg[4] or 1, 0.20) or bg[4])
    frame:SetBackdropBorderColor(border[1], border[2], border[3], frame.__bigBisStatusBadge and 0 or border[4])
end

function Widgets:CreatePanel(name, parent, bg, border)
    local template = BackdropTemplateMixin and "BackdropTemplate" or nil
    local frame = CreateFrame("Frame", name, parent, template)
    setBackdrop(frame, bg, border)
    return frame
end

function Widgets:SetBackdrop(frame, bg, border)
    setBackdrop(frame, bg, border)
end

function Widgets:CreateLabel(parent, text, template)
    local label = parent:CreateFontString(nil, "OVERLAY", template or "GameFontNormalSmall")
    label:SetText(text or "")
    label:SetJustifyH("LEFT")
    label:SetWordWrap(false)
    return label
end

function Widgets:CreateWrappedLabel(parent, text, template)
    local label = parent:CreateFontString(nil, "OVERLAY", template or "GameFontNormalSmall")
    label:SetText(text or "")
    label:SetJustifyH("LEFT")
    label:SetWordWrap(true)
    return label
end

function Widgets:MeasureTextHeight(label, minimum)
    local height = minimum or 0
    if label and label.GetStringHeight then
        height = math.max(height, label:GetStringHeight() or 0)
    end
    return height
end

local function textTokens(text)
    local tokens, position = {}, 1
    while position <= #text do
        local rest = string.sub(text, position)
        local token = string.match(rest, "^|c%x%x%x%x%x%x%x%x")
            or string.match(rest, "^|H.-|h.-|h")
            or string.match(rest, "^|T.-|t")
            or string.match(rest, "^|r")
            or string.match(rest, "^||")
        if not token then
            local byte = string.byte(text, position)
            local length = byte >= 240 and 4 or (byte >= 224 and 3 or (byte >= 192 and 2 or 1))
            token = string.sub(text, position, position + length - 1)
        end
        tokens[#tokens + 1] = token
        position = position + #token
    end
    return tokens
end

function Widgets:SetCellText(label, text, maxLines, lineHeight, width)
    text = tostring(text or "")
    maxLines = math.max(1, math.floor(tonumber(maxLines) or 2))
    lineHeight = math.max(1, tonumber(lineHeight) or 14)
    if width then label:SetWidth(math.max(1, width)) end
    label:SetWordWrap(true)
    if label.SetJustifyV then label:SetJustifyV("MIDDLE") end
    if label.SetNonSpaceWrap then label:SetNonSpaceWrap(true) end
    label:SetHeight(0)
    local availableHeight = maxLines * lineHeight
    local function fits(value)
        label:SetText(value)
        return not label.GetStringHeight or (label:GetStringHeight() or 0) <= availableHeight + 0.1
    end
    local displayed, truncated = text, not fits(text)
    if truncated then
        local tokens = textTokens(text)
        local low, high, best = 0, #tokens, "..."
        local resetColor = string.find(text, "|c", 1, true) and "|r" or ""
        while low <= high do
            local middle = math.floor((low + high) / 2)
            local prefix = string.gsub(table.concat(tokens, "", 1, middle), "%s+$", "")
            local candidate = prefix .. "..." .. resetColor
            if fits(candidate) then
                best = candidate
                low = middle + 1
            else
                high = middle - 1
            end
        end
        displayed = best
    end
    label:SetText(displayed)
    label:SetHeight(availableHeight)
    label.fullText = text
    label.displayedText = displayed
    label.isTruncated = truncated
    label.maxLines = maxLines
    label.lineHeight = lineHeight
    return displayed, truncated
end

function Widgets:CreateStatusBadge(parent, text, width, height, bg, border)
    local badge = self:CreatePanel(nil, parent, bg, border)
    badge.__bigBisStatusBadge = true
    setBackdrop(badge, bg, border)
    badge:SetSize(width or 78, height or 18)

    local label = badge:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", badge, "LEFT", 4, 0)
    label:SetPoint("RIGHT", badge, "RIGHT", -4, 0)
    label:SetJustifyH("CENTER")
    label:SetWordWrap(false)
    label:SetText(text or "")
    badge.label = label

    function badge:SetIcon(key)
        if not self.icon then
            self.icon = self:CreateTexture(nil, "ARTWORK")
            self.icon:SetSize(14, 14)
            self.icon:SetPoint("LEFT", self, "LEFT", 3, 0)
        end
        label:ClearAllPoints()
        label:SetPoint("LEFT", self, "LEFT", key and 21 or 4, 0)
        label:SetPoint("RIGHT", self, "RIGHT", -4, 0)
        if key then
            Widgets:SetIcon(self.icon, key)
            self.icon:Show()
            label:SetJustifyH("LEFT")
        else
            self.icon:Hide()
            label:SetJustifyH("CENTER")
        end
    end
    function badge:SetTone(background, foreground)
        setBackdrop(self, background, foreground)
        if foreground then
            self.label:SetTextColor(foreground[1], foreground[2], foreground[3], 1)
            if self.icon then self.icon:SetVertexColor(foreground[1], foreground[2], foreground[3], 1) end
        end
    end

    return badge
end

local function paintButton(button)
    local theme = Widgets.Theme
    local disabled = button.disabled
    local background = disabled and theme.surface or (button.pressed and theme.pressed
        or (button.selected and theme.selected or (button.hovered and theme.hover or theme.control)))
    local border = (button.selected or button.focused) and theme.accent or theme.border
    if button.hovered and not button.selected and not button.focused then border = theme.muted end
    if disabled then border = theme.border end
    setBackdrop(button, background, border)
    local foreground = disabled and theme.disabled or (button.selected and theme.accent or theme.text)
    if button.label then button.label:SetTextColor(foreground[1], foreground[2], foreground[3], foreground[4]) end
    if button.icon then button.icon:SetVertexColor(foreground[1], foreground[2], foreground[3], foreground[4]) end
    if button.focusRing then
        if button.focused and not disabled then button.focusRing:Show() else button.focusRing:Hide() end
    end
end

function Widgets:CreateTextButton(parent, text, width, height, onClick)
    local template = BackdropTemplateMixin and "BackdropTemplate" or nil
    local button = CreateFrame("Button", nil, parent, template)
    button:SetSize(width or 80, height or 24)
    button:EnableMouse(true)
    button:RegisterForClicks("LeftButtonUp")

    local label = button:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", button, "LEFT", 6, 0)
    label:SetPoint("RIGHT", button, "RIGHT", -6, 0)
    label:SetJustifyH("CENTER")
    label:SetWordWrap(false)
    label:SetText(text or "")
    button.label = label
    button.focusRing = button:CreateTexture(nil, "OVERLAY")
    button.focusRing:SetColorTexture(0.96, 0.90, 0.68, 1)
    button.focusRing:SetHeight(2)
    button.focusRing:SetPoint("BOTTOMLEFT", button, "BOTTOMLEFT", 3, 3)
    button.focusRing:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -3, 3)
    button.focusRing:Hide()

    local nativeSetEnabled = button.SetEnabled
    function button:SetEnabled(enabled)
        self.disabled = not enabled
        if self.disabled then self.pressed = false end
        if nativeSetEnabled then nativeSetEnabled(self, not self.disabled) end
        paintButton(self)
    end
    function button:SetSelected(selected)
        self.selected = selected and true or false
        paintButton(self)
    end
    function button:SetHovered(hovered)
        self.hovered = hovered and true or false
        if not self.hovered then self.pressed = false end
        paintButton(self)
    end
    function button:SetFocused(focused)
        self.focused = focused and true or false
        paintButton(self)
    end
    button:SetScript("OnEnter", function(self)
        self:SetHovered(true)
    end)
    button:SetScript("OnLeave", function(self)
        self:SetHovered(false)
    end)
    button:SetScript("OnMouseDown", function(self, buttonName)
        self.pressed = buttonName == "LeftButton" and not self.disabled
        paintButton(self)
    end)
    button:SetScript("OnMouseUp", function(self)
        self.pressed = false
        paintButton(self)
    end)
    button:SetScript("OnClick", function(self, buttonName)
        if not self.disabled and buttonName == "LeftButton" and onClick then onClick(self, buttonName) end
    end)
    button:SetScript("OnDisable", function(self)
        self.disabled, self.pressed = true, false
        paintButton(self)
    end)
    button:SetScript("OnEnable", function(self)
        self.disabled = false
        paintButton(self)
    end)
    button:SetScript("OnHide", function(self)
        self.hovered, self.pressed, self.focused = false, false, false
        paintButton(self)
    end)
    paintButton(button)
    return button
end

function Widgets:CreateUtilityButton(parent, iconKey, size, onClick, tooltip)
    size = math.max(28, tonumber(size) or 28)
    local button = self:CreateTextButton(parent, "", size, size, onClick)
    button.label:Hide()
    button.icon = button:CreateTexture(nil, "ARTWORK")
    button.icon:SetSize(20, 20)
    button.icon:SetPoint("CENTER", button, "CENTER", 0, 0)
    function button:SetIcon(key)
        Widgets:SetIcon(self.icon, key)
        paintButton(self)
    end
    button:SetIcon(iconKey)
    self:BindTooltip(button, tooltip)
    return button
end

function Widgets:CreateIconButton(parent, size, onClick)
    local button = CreateFrame("Button", nil, parent)
    button:SetSize(size or 28, size or 28)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")

    local icon = button:CreateTexture(nil, "ARTWORK")
    icon:SetAllPoints()
    icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
    icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    button.icon = icon

    local border = button:CreateTexture(nil, "OVERLAY")
    border:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    border:SetBlendMode("ADD")
    border:SetPoint("CENTER")
    border:SetSize((size or 28) * 1.8, (size or 28) * 1.8)
    border:SetVertexColor(0.8, 0.8, 0.8, 0.35)
    border:Hide()
    button.border = border

    function button:SetHovered(hovered)
        self.hovered = hovered and true or false
        if self.hovered then self.border:Show() else self.border:Hide() end
    end
    button:SetScript("OnEnter", function(self)
        self:SetHovered(true)
    end)
    button:SetScript("OnLeave", function(self)
        self:SetHovered(false)
        hideOwnedTooltip(self)
    end)
    button:SetScript("OnHide", function(self)
        self:SetHovered(false)
        hideOwnedTooltip(self)
    end)
    button:SetScript("OnSizeChanged", function(self, width, height)
        self.border:SetSize((width or 28) * 1.8, (height or width or 28) * 1.8)
    end)
    button:SetScript("OnClick", function(self, buttonName)
        if onClick then
            onClick(self, buttonName)
        end
    end)

    return button
end

function Widgets:CreateDropdown(name, parent, width, getText, getItems, onSelect)
    dropdownCounter = dropdownCounter + 1
    local dropdownName = name or ("BigBiSListDropdown" .. dropdownCounter)
    local frame = CreateFrame("Frame", dropdownName, parent, "UIDropDownMenuTemplate")
    frame.__bigBisListDropdown = true
    UIDropDownMenu_SetWidth(frame, width or 120)

    local function refresh()
        UIDropDownMenu_SetText(frame, getText and getText() or "Select")
    end

    UIDropDownMenu_Initialize(frame, function(_, level)
        local items = getItems and getItems() or {}
        for _, item in ipairs(items) do
            local info = UIDropDownMenu_CreateInfo()
            info.text = item.text
            info.value = item.value
            info.checked = item.checked
            info.isNotRadio = item.isNotRadio
            info.keepShownOnClick = item.keepShownOnClick
            info.notCheckable = item.notCheckable
            info.disabled = item.disabled
            info.func = function()
                if onSelect then
                    onSelect(item.value, item)
                end
                refresh()
            end
            UIDropDownMenu_AddButton(info, level)
        end
    end)

    prepareDropdownLists()

    local nativeButton = _G and _G[dropdownName .. "Button"]
    local clickCover = CreateFrame("Button", nil, frame)
    clickCover:SetAllPoints(frame)
    clickCover:EnableMouse(true)
    clickCover:RegisterForClicks("LeftButtonUp")
    if clickCover.SetFrameLevel then
        local nativeLevel = nativeButton and nativeButton.GetFrameLevel and nativeButton:GetFrameLevel() or 0
        local frameLevel = frame.GetFrameLevel and frame:GetFrameLevel() or 0
        clickCover:SetFrameLevel(math.max(nativeLevel or 0, frameLevel or 0) + 1)
    end
    clickCover:SetScript("OnClick", function()
        if nativeButton and nativeButton.IsEnabled and not nativeButton:IsEnabled() then
            return
        end

        if type(ToggleDropDownMenu) == "function" then
            ToggleDropDownMenu(1, nil, frame)
        elseif nativeButton and nativeButton.Click then
            nativeButton:Click()
        end

        prepareDropdownLists(frame)
        if C_Timer and C_Timer.After then
            C_Timer.After(0, function()
                prepareDropdownLists(frame)
            end)
        end
    end)

    frame.nativeButton = nativeButton
    frame.clickCover = clickCover

    frame.Refresh = refresh
    refresh()
    return frame
end

function Widgets:CreateScrollFrame(name, parent)
    local scroll = CreateFrame("ScrollFrame", name, parent, "UIPanelScrollFrameTemplate")
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(1, 1)
    scroll:SetScrollChild(child)
    scroll.child = child

    scroll:SetScript("OnSizeChanged", function(self, width)
        child:SetWidth(width)
    end)

    return scroll, child
end

-- Opt-in for overlays whose chrome should disappear when all content fits.
-- Main list scroll frames keep their normal native scrollbar behavior.
function Widgets:UpdateScrollOverflow(scroll, contentHeight, viewportHeight)
    if not scroll then return false, 0 end
    local child = scroll.child or (scroll.GetScrollChild and scroll:GetScrollChild())
    contentHeight = tonumber(contentHeight) or (child and child.GetHeight and child:GetHeight()) or 0
    viewportHeight = tonumber(viewportHeight) or (scroll.GetHeight and scroll:GetHeight()) or 0
    local maximum = math.max(0, contentHeight - viewportHeight)
    local overflowing = maximum > 0
    local current = tonumber(scroll.GetVerticalScroll and scroll:GetVerticalScroll()) or 0
    local offset = math.min(maximum, math.max(0, current))
    if offset ~= current and scroll.SetVerticalScroll then scroll:SetVerticalScroll(offset) end

    local name = scroll.GetName and scroll:GetName()
    local bar = scroll.ScrollBar or scroll.scrollBar or (name and _G and _G[name .. "ScrollBar"])
    local function setEnabled(frame, enabled)
        if not frame then return end
        if frame.SetEnabled then frame:SetEnabled(enabled)
        elseif enabled and frame.Enable then frame:Enable()
        elseif not enabled and frame.Disable then frame:Disable() end
    end
    if bar then
        if bar.SetMinMaxValues then bar:SetMinMaxValues(0, maximum) end
        if bar.SetValue and (not bar.GetValue or bar:GetValue() ~= offset) then bar:SetValue(offset) end
        setEnabled(bar, overflowing)
        if overflowing then
            if bar.Show then bar:Show() end
        elseif bar.Hide then
            bar:Hide()
        end
        local barName = bar.GetName and bar:GetName()
        local up = bar.ScrollUpButton or scroll.ScrollUpButton
            or (barName and _G and _G[barName .. "ScrollUpButton"])
            or (name and _G and _G[name .. "ScrollUpButton"])
        local down = bar.ScrollDownButton or scroll.ScrollDownButton
            or (barName and _G and _G[barName .. "ScrollDownButton"])
            or (name and _G and _G[name .. "ScrollDownButton"])
        setEnabled(up, overflowing and offset > 0)
        setEnabled(down, overflowing and offset < maximum)
    end
    return overflowing, maximum
end

function Widgets:ClearChildren(parent)
    if not parent then
        return
    end

    local children = { parent:GetChildren() }
    for _, child in ipairs(children) do
        child:Hide()
        child:SetParent(nil)
    end

    local regions = { parent:GetRegions() }
    for _, region in ipairs(regions) do
        if region.Hide then
            region:Hide()
        end
    end
end

function Widgets:CreateSectionHeader(parent, text, yOffset)
    local header = CreateFrame("Frame", nil, parent)
    header:SetHeight(34)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)

    local line = header:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(0.55, 0.55, 0.58, 0.45)
    line:SetHeight(1)
    line:SetPoint("BOTTOMLEFT", header, "BOTTOMLEFT", 0, 6)
    line:SetPoint("BOTTOMRIGHT", header, "BOTTOMRIGHT", 0, 6)

    local label = header:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    label:SetPoint("TOPLEFT", header, "TOPLEFT", 8, -2)
    label:SetTextColor(1, 0.82, 0.28, 1)
    label:SetText(text)

    return header, 34
end

function Widgets:CreateItemRow(parent, height)
    local row = self:CreatePanel(nil, parent, Widgets.Theme.surface, { 0, 0, 0, 0 })
    row:SetHeight(height or 38)
    row:EnableMouse(true)

    local selection = row:CreateTexture(nil, "ARTWORK")
    selection:SetAllPoints()
    selection:SetColorTexture(0.88, 0.69, 0.22, 0.11)
    selection:Hide()
    row.selection = selection
    local accent = row:CreateTexture(nil, "OVERLAY")
    accent:SetPoint("TOPLEFT", row, "TOPLEFT", 0, 0)
    accent:SetPoint("BOTTOMLEFT", row, "BOTTOMLEFT", 0, 0)
    accent:SetWidth(2)
    accent:SetColorTexture(0.92, 0.76, 0.32, 1)
    accent:Hide()
    row.selectionAccent = accent

    local separator = row:CreateTexture(nil, "ARTWORK")
    separator:SetHeight(1)
    separator:SetPoint("BOTTOMLEFT", row, "BOTTOMLEFT", 0, 0)
    separator:SetPoint("BOTTOMRIGHT", row, "BOTTOMRIGHT", 0, 0)
    separator:SetColorTexture(0.25, 0.25, 0.29, 0.55)
    row.separator = separator

    local highlight = row:CreateTexture(nil, "ARTWORK")
    highlight:SetAllPoints()
    highlight:SetColorTexture(1, 1, 1, 0.055)
    highlight:Hide()
    row.highlight = highlight

    function row:SetSelected(selected)
        self.selected = selected and true or false
        if self.selected then
            self.selection:Show()
            self.selectionAccent:Show()
        else
            self.selection:Hide()
            self.selectionAccent:Hide()
        end
    end
    function row:SetHovered(hovered)
        self.hovered = hovered and true or false
        if self.hovered then self.highlight:Show() else self.highlight:Hide() end
    end
    row:SetScript("OnEnter", function(self)
        self:SetHovered(true)
    end)
    row:SetScript("OnLeave", function(self)
        self:SetHovered(false)
    end)
    row:SetScript("OnHide", function(self)
        self:SetHovered(false)
        self:SetSelected(false)
    end)

    return row
end
