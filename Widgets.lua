local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local Widgets = {}
BigBiSList.Widgets = Widgets

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
    frame:SetBackdropColor(bg[1], bg[2], bg[3], bg[4])
    frame:SetBackdropBorderColor(border[1], border[2], border[3], border[4])
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

function Widgets:CreateStatusBadge(parent, text, width, height, bg, border)
    local badge = self:CreatePanel(nil, parent, bg, border)
    badge:SetSize(width or 78, height or 18)

    local label = badge:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", badge, "LEFT", 4, 0)
    label:SetPoint("RIGHT", badge, "RIGHT", -4, 0)
    label:SetJustifyH("CENTER")
    label:SetWordWrap(false)
    label:SetText(text or "")
    badge.label = label

    return badge
end

function Widgets:CreateTextButton(parent, text, width, height, onClick)
    local button = self:CreatePanel(nil, parent, { 0.10, 0.10, 0.12, 0.95 }, { 0.26, 0.26, 0.30, 1 })
    button:SetSize(width or 80, height or 24)
    button:EnableMouse(true)

    local label = button:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", button, "LEFT", 6, 0)
    label:SetPoint("RIGHT", button, "RIGHT", -6, 0)
    label:SetJustifyH("CENTER")
    label:SetWordWrap(false)
    label:SetText(text or "")
    button.label = label

    button:SetScript("OnEnter", function(self)
        setBackdrop(self, { 0.15, 0.15, 0.18, 0.98 }, { 0.40, 0.40, 0.46, 1 })
    end)
    button:SetScript("OnLeave", function(self)
        if self.selected then
            setBackdrop(self, { 0.16, 0.14, 0.07, 0.98 }, { 0.88, 0.72, 0.24, 1 })
        else
            setBackdrop(self, { 0.10, 0.10, 0.12, 0.95 }, { 0.26, 0.26, 0.30, 1 })
        end
    end)
    button:SetScript("OnMouseUp", function(self, buttonName)
        if buttonName == "LeftButton" and onClick then
            onClick(self)
        end
    end)

    function button:SetSelected(selected)
        self.selected = selected and true or false
        if self.selected then
            setBackdrop(self, { 0.16, 0.14, 0.07, 0.98 }, { 0.88, 0.72, 0.24, 1 })
            self.label:SetTextColor(1, 0.86, 0.36, 1)
        else
            setBackdrop(self, { 0.10, 0.10, 0.12, 0.95 }, { 0.26, 0.26, 0.30, 1 })
            self.label:SetTextColor(0.88, 0.88, 0.88, 1)
        end
    end

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

    button:SetScript("OnEnter", function(self)
        self.border:Show()
    end)
    button:SetScript("OnLeave", function(self)
        self.border:Hide()
        GameTooltip:Hide()
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
    local row = self:CreatePanel(nil, parent, { 0.075, 0.075, 0.085, 0.90 }, { 0.18, 0.18, 0.20, 0.85 })
    row:SetHeight(height or 38)
    row:EnableMouse(true)

    local highlight = row:CreateTexture(nil, "BACKGROUND")
    highlight:SetAllPoints()
    highlight:SetColorTexture(1, 1, 1, 0.055)
    highlight:Hide()
    row.highlight = highlight

    row:SetScript("OnEnter", function(self)
        self.highlight:Show()
    end)
    row:SetScript("OnLeave", function(self)
        self.highlight:Hide()
    end)

    return row
end
