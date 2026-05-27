local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local function itemIdFromLink(link)
    if not link then
        return nil
    end
    return tonumber(string.match(link, "item:(%d+)"))
end

local function itemIdFromTooltipData(data)
    if type(data) ~= "table" then
        return nil
    end

    local itemId = tonumber(data.id or data.itemID or data.itemId)
    if itemId then
        return itemId
    end

    itemId = itemIdFromLink(data.hyperlink or data.guid)
    if itemId then
        return itemId
    end

    if type(data.lines) == "table" then
        for _, line in ipairs(data.lines) do
            if type(line) == "table" then
                itemId = itemIdFromLink(line.hyperlink or line.guid)
                if itemId then
                    return itemId
                end
            end
        end
    end

    return nil
end

local function itemIdFromTooltip(tooltip, tooltipData)
    local itemId = itemIdFromTooltipData(tooltipData)
    if itemId then
        return itemId
    end

    if tooltip and tooltip.GetItem then
        local ok, _, link = pcall(tooltip.GetItem, tooltip)
        if ok then
            itemId = itemIdFromLink(link)
            if itemId then
                return itemId
            end
        end
    end

    if tooltip and tooltip.GetHyperlink then
        local ok, link = pcall(tooltip.GetHyperlink, tooltip)
        if ok then
            itemId = itemIdFromLink(link)
            if itemId then
                return itemId
            end
        end
    end

    if tooltip and tooltip.GetTooltipData then
        local ok, data = pcall(tooltip.GetTooltipData, tooltip)
        if ok then
            return itemIdFromTooltipData(data)
        end
    end

    return nil
end

local function clearTooltipRenderGuard(tooltip)
    if tooltip then
        tooltip.__bigBisListRenderKey = nil
    end
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

function BigBiSList:AddTooltipInfo(tooltip, tooltipData)
    self:EnsureDatabase()

    local settings = BigBiSListDB.profile.tooltips
    if not settings or settings.enabled == false then
        return
    end

    local itemId = itemIdFromTooltip(tooltip, tooltipData)
    if not itemId then
        return
    end

    local selection = BigBiSListDB.char.selection or {}
    local matches = self:GetTooltipMatches(itemId, selection.class, selection.spec, settings.selectedSpecFirst ~= false)
    if #matches == 0 then
        return
    end

    local showAll = settings.showAllOnAlt and IsAltKeyDown and IsAltKeyDown()
    local maxRows = showAll and #matches or (settings.compact and 4 or 8)
    local renderKey = table.concat({
        tostring(itemId),
        tostring(settings.compact),
        tostring(settings.selectedSpecFirst),
        tostring(settings.showAllOnAlt),
        tostring(showAll),
    }, ":")
    if tooltip.__bigBisListRenderKey == renderKey then
        return
    end
    tooltip.__bigBisListRenderKey = renderKey

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

    if #matches > maxRows and not showAll and settings.showAllOnAlt then
        tooltip:AddLine("Hold ALT to show all Big BiS List matches", 0.62, 0.62, 0.66)
    end
end

local function hookTooltip(tooltip)
    if not tooltip or tooltip.__bigBisListHooked then
        return
    end
    tooltip.__bigBisListHooked = true
    tooltip:HookScript("OnTooltipSetItem", function(hookedTooltip)
        BigBiSList:AddTooltipInfo(hookedTooltip)
    end)
    tooltip:HookScript("OnTooltipCleared", clearTooltipRenderGuard)
end

function BigBiSList:InitTooltip()
    if self.tooltipInitialized then
        return
    end

    if TooltipDataProcessor and Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip, tooltipData)
            BigBiSList:AddTooltipInfo(tooltip, tooltipData)
        end)
    end

    hookTooltip(GameTooltip)
    hookTooltip(ItemRefTooltip)

    self.tooltipInitialized = true
end
