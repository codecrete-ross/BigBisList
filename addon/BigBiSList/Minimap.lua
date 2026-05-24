local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local BUTTON_NAME = "BigBiSListMinimapButton"
local DEFAULT_ICON = "Interface\\Icons\\INV_Misc_QuestionMark"
local MINIMAP_RADIUS = 80

local function atan2(y, x)
    if math.atan2 then
        return math.atan2(y, x)
    end

    if x > 0 then
        return math.atan(y / x)
    elseif x < 0 and y >= 0 then
        return math.atan(y / x) + math.pi
    elseif x < 0 and y < 0 then
        return math.atan(y / x) - math.pi
    elseif y > 0 then
        return math.pi / 2
    elseif y < 0 then
        return -math.pi / 2
    end

    return 0
end

local function normalizeAngle(angle)
    angle = angle or 225
    while angle < 0 do
        angle = angle + 360
    end
    while angle >= 360 do
        angle = angle - 360
    end
    return angle
end

local function buttonSettings()
    BigBiSList:EnsureDatabase()
    BigBiSListDB.profile.minimap = BigBiSListDB.profile.minimap or {}
    BigBiSListDB.profile.minimap.angle = normalizeAngle(BigBiSListDB.profile.minimap.angle)
    return BigBiSListDB.profile.minimap
end

local function updateButtonPosition(button)
    local settings = buttonSettings()
    local radians = math.rad(settings.angle)
    local x = math.cos(radians) * MINIMAP_RADIUS
    local y = math.sin(radians) * MINIMAP_RADIUS

    button:ClearAllPoints()
    button:SetPoint("CENTER", Minimap, "CENTER", x, y)
end

local function updateAngleFromCursor(button)
    local mapX, mapY = Minimap:GetCenter()
    local cursorX, cursorY = GetCursorPosition()
    local scale = Minimap:GetEffectiveScale()

    cursorX = cursorX / scale
    cursorY = cursorY / scale

    local angle = math.deg(atan2(cursorY - mapY, cursorX - mapX))
    buttonSettings().angle = normalizeAngle(angle)
    updateButtonPosition(button)
end

local function stopDragging(button)
    button:SetScript("OnUpdate", nil)
    button.dragging = false
end

function BigBiSList:RefreshMinimapButton()
    if not self.minimapButton then
        return
    end

    if BigBiSListDB and BigBiSListDB.profile and BigBiSListDB.profile.showMinimap == false then
        self.minimapButton:Hide()
        return
    end

    updateButtonPosition(self.minimapButton)
    self.minimapButton:Show()
end

function BigBiSList:InitMinimapButton()
    if self.minimapButton or not Minimap then
        return
    end

    self:EnsureDatabase()

    local button = CreateFrame("Button", BUTTON_NAME, Minimap)
    button:SetSize(32, 32)
    button:SetFrameStrata("MEDIUM")
    button:SetClampedToScreen(true)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    button:RegisterForDrag("LeftButton")

    local border = button:CreateTexture(nil, "OVERLAY")
    border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    border:SetPoint("TOPLEFT", button, "TOPLEFT", 0, 0)
    border:SetSize(54, 54)

    local icon = button:CreateTexture(nil, "ARTWORK")
    icon:SetTexture(DEFAULT_ICON)
    icon:SetSize(20, 20)
    icon:SetPoint("CENTER", button, "CENTER", 0, 0)
    icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    button.icon = icon

    local highlight = button:CreateTexture(nil, "HIGHLIGHT")
    highlight:SetTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    highlight:SetAllPoints(button)
    highlight:SetBlendMode("ADD")

    button:SetScript("OnEnter", function(selfButton)
        GameTooltip:SetOwner(selfButton, "ANCHOR_LEFT")
        GameTooltip:AddLine(BigBiSList.displayName, 0.2, 1.0, 0.65)
        GameTooltip:AddLine("Left-click: open or close", 0.86, 0.86, 0.86)
        GameTooltip:AddLine("Right-click: settings", 0.86, 0.86, 0.86)
        GameTooltip:AddLine("Drag: move button", 0.62, 0.62, 0.66)
        GameTooltip:Show()
    end)
    button:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
    button:SetScript("OnClick", function(_, mouseButton)
        if mouseButton == "RightButton" then
            BigBiSList:SetSelection(nil, nil, nil, "Settings")
            BigBiSList:OpenMainFrame()
        else
            BigBiSList:ToggleMainFrame()
        end
    end)
    button:SetScript("OnDragStart", function(selfButton)
        selfButton.dragging = true
        selfButton:SetScript("OnUpdate", updateAngleFromCursor)
    end)
    button:SetScript("OnDragStop", stopDragging)
    button:SetScript("OnMouseUp", function(selfButton)
        if selfButton.dragging then
            stopDragging(selfButton)
        end
    end)

    self.minimapButton = button
    self:RefreshMinimapButton()
end
