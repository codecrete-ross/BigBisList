local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local function itemIdFromLink(link)
    if not link then
        return nil
    end
    return tonumber(string.match(link, "item:(%d+)"))
end

local function lineForUse(use)
    local left = use.class .. " " .. use.spec
    if use.slot and use.slot ~= "" then
        left = left .. " - " .. use.slot
    end

    local right = BigBiSList:GetPhaseDisplayName(use.phase)
    if use.rank_label and use.rank_label ~= "" then
        right = right .. " " .. use.rank_label
    end

    return left, right
end

function BigBiSList:AddTooltipInfo(tooltip)
    self:EnsureDatabase()

    local settings = BigBiSListDB.profile.tooltips
    if not settings or settings.enabled == false then
        return
    end

    local _, link = tooltip:GetItem()
    local itemId = itemIdFromLink(link)
    if not itemId then
        return
    end

    local selection = BigBiSListDB.char.selection or {}
    local matches = self:GetTooltipMatches(itemId, selection.class, selection.spec)
    if #matches == 0 then
        return
    end

    local showAll = settings.showAllOnAlt and IsAltKeyDown and IsAltKeyDown()
    local maxRows = showAll and #matches or (settings.compact and 4 or 8)

    tooltip:AddLine(" ")
    tooltip:AddLine("Big BiS List", 0.2, 1.0, 0.65)

    for index = 1, math.min(#matches, maxRows) do
        local use = matches[index]
        local left, right = lineForUse(use)
        local selected = use.class == selection.class and use.spec == selection.spec
        if selected then
            tooltip:AddDoubleLine(left, right, 0.25, 1.0, 0.45, 0.25, 1.0, 0.45)
        else
            tooltip:AddDoubleLine(left, right, 1.0, 0.82, 0.28, 1.0, 0.82, 0.28)
        end
    end

    if #matches > maxRows and not showAll then
        tooltip:AddLine("Hold ALT to show all Big BiS List matches", 0.62, 0.62, 0.66)
    end
end

function BigBiSList:InitTooltip()
    if self.tooltipInitialized then
        return
    end

    if TooltipDataProcessor and Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip)
            BigBiSList:AddTooltipInfo(tooltip)
        end)
    else
        if GameTooltip then
            GameTooltip:HookScript("OnTooltipSetItem", function(tooltip)
                BigBiSList:AddTooltipInfo(tooltip)
            end)
        end
        if ItemRefTooltip then
            ItemRefTooltip:HookScript("OnTooltipSetItem", function(tooltip)
                BigBiSList:AddTooltipInfo(tooltip)
            end)
        end
    end

    self.tooltipInitialized = true
end
