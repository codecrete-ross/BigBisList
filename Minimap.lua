local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local BROKER_NAME = "BigBiSList"
local DEFAULT_ICON = "Interface\\AddOns\\BigBiSList\\assets\\icon.tga"

local function showSettings()
    BigBiSList:SetSelection(nil, nil, nil, "Settings")
    BigBiSList:OpenMainFrame()
end

local function createBrokerObject(LDB)
    local existingObject = LDB:GetDataObjectByName(BROKER_NAME)
    if existingObject then
        return existingObject
    end

    return LDB:NewDataObject(BROKER_NAME, {
        type = "launcher",
        text = BigBiSList.displayName,
        icon = DEFAULT_ICON,
        OnClick = function(_, mouseButton)
            if mouseButton == "RightButton" then
                showSettings()
            else
                BigBiSList:ToggleMainFrame()
            end
        end,
        OnTooltipShow = function(tooltip)
            tooltip:AddLine(BigBiSList.displayName, 0.2, 1.0, 0.65)
            tooltip:AddLine("Left-click: open or close", 0.86, 0.86, 0.86)
            tooltip:AddLine("Right-click: settings", 0.86, 0.86, 0.86)
            tooltip:AddLine("Drag: move button", 0.62, 0.62, 0.66)
        end,
    })
end

function BigBiSList:RefreshMinimapButton()
    local LDBIcon = self.minimapIcon
    if not LDBIcon then
        return
    end

    self:EnsureDatabase()
    BigBiSListDB.profile.minimap.hide = BigBiSListDB.profile.minimap.hide == true
    LDBIcon:Refresh(BROKER_NAME, BigBiSListDB.profile.minimap)
    self.minimapButton = LDBIcon:GetMinimapButton(BROKER_NAME)
end

function BigBiSList:InitMinimapButton()
    if self.minimapIconRegistered or not Minimap or not LibStub then
        return
    end

    self:EnsureDatabase()

    local LDB = LibStub("LibDataBroker-1.1", true)
    local LDBIcon = LibStub("LibDBIcon-1.0", true)
    if not LDB or not LDBIcon then
        return
    end

    self.minimapDataObject = createBrokerObject(LDB)
    self.minimapIcon = LDBIcon

    if not LDBIcon:IsRegistered(BROKER_NAME) then
        LDBIcon:Register(BROKER_NAME, self.minimapDataObject, BigBiSListDB.profile.minimap)
    end

    self.minimapIconRegistered = true
    self:RefreshMinimapButton()
end
