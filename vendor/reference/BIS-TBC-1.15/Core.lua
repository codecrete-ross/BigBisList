BISTBCAddon = LibStub("AceAddon-3.0"):NewAddon("BIS-TBC")

function addMapIcon()

    local LDB = LibStub("LibDataBroker-1.1", true)
    local LDBIcon = LDB and LibStub("LibDBIcon-1.0", true)
    if LDB then
        local PC_MinimapBtn = LDB:NewDataObject("BIS-TBC", {
            type = "launcher",
			text = "BIS-TBC",
            icon = "Interface\\Icons\\INV_Jewelcrafting_LivingRuby_03",
            OnClick = function(_, button)
                if button == "LeftButton" then BISTBCAddon:createMainFrame() end
                if button == "RightButton" then BISTBCAddon:openConfigDialog() end
            end,
            OnTooltipShow = function(tt)
                tt:AddLine(BISTBCAddon.AddonNameAndVersion)
                tt:AddLine("|cffffff00Left click|r to open the BiS lists window")
                tt:AddLine("|cffffff00Right click|r to open addon configuration window")
            end,
        })
        if LDBIcon then
            LDBIcon:Register("BIS-TBC", PC_MinimapBtn, BISTBCAddon.db.char)
        end
    end
end

function BISTBCAddon:OnInitialize()
    BISTBCAddon.AceAddonName = "BIS-TBC"
    local tocVersion = C_AddOns and C_AddOns.GetAddOnMetadata("BIS-TBC", "Version") or GetAddOnMetadata("BIS-TBC", "Version") or "1.0"
    local tocTitle = (C_AddOns and C_AddOns.GetAddOnMetadata("BIS-TBC", "Title") or GetAddOnMetadata("BIS-TBC", "Title")) or "BIS-TBC"
    BISTBCAddon.AddonNameAndVersion = tocTitle .. " v" .. tocVersion
    BISTBCAddon:initConfig()
    addMapIcon()
    BISTBCAddon:initBislists()
    BISTBCAddon:initBisTooltip()
    BISTBCAddon:initDropAlerts()
end
