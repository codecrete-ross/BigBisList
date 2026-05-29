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

local function shouldAnnotateTooltip(tooltip)
    if not tooltip or not tooltip.AddLine or not tooltip.AddDoubleLine then
        return false
    end

    return tooltip == GameTooltip or tooltip == ItemRefTooltip
end

local function reportTooltipError(err)
    local handler = geterrorhandler and geterrorhandler()
    if handler then
        pcall(handler, err)
    end
end

local function addTooltipInfoSafely(tooltip, tooltipData)
    if not shouldAnnotateTooltip(tooltip) then
        return
    end

    local ok, err = pcall(BigBiSList.AddTooltipInfo, BigBiSList, tooltip, tooltipData)
    if not ok then
        reportTooltipError(err)
    end
end

local function lineForTooltipMatch(match)
    local left = match.class .. " " .. match.spec
    if match.slot and match.slot ~= "" then
        left = left .. " - " .. match.slot
    end

    if match.tooltip_grouped then
        return left, match.phase_summary or ""
    end

    local right = BigBiSList:GetPhaseDisplayName(match.phase)
    local tagLabel = match.display_rank_label or match.rank_label
    if tagLabel and tagLabel ~= "" then
        right = right .. " " .. tagLabel
    end

    return left, right
end

function BigBiSList:AddTooltipInfo(tooltip, tooltipData)
    if not shouldAnnotateTooltip(tooltip) then
        return
    end

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
    local selectedSpecFirst = settings.selectedSpecFirst ~= false
    local specFilters = settings.specFilters
    local rawMatches = self:GetTooltipMatches(itemId, selection.class, selection.spec, selectedSpecFirst, specFilters)
    if #rawMatches == 0 then
        return
    end
    local groupedMatches = self:GetGroupedTooltipMatches(itemId, selection.class, selection.spec, selectedSpecFirst, specFilters)

    local showRaw = settings.showAllOnAlt and IsAltKeyDown and IsAltKeyDown()
    local matches = showRaw and rawMatches or groupedMatches
    local maxRows = showRaw and #matches or (settings.compact and 4 or 8)
    local renderKey = table.concat({
        tostring(itemId),
        tostring(settings.compact),
        tostring(settings.selectedSpecFirst),
        tostring(settings.showAllOnAlt),
        tostring(showRaw),
        tostring(selection.class),
        tostring(selection.spec),
        self:GetTooltipSpecFilterKey(specFilters),
    }, ":")
    if tooltip.__bigBisListRenderKey == renderKey then
        return
    end
    tooltip.__bigBisListRenderKey = renderKey

    tooltip:AddLine(" ")
    tooltip:AddLine("Big BiS List", 0.2, 1.0, 0.65)

    for index = 1, math.min(#matches, maxRows) do
        local match = matches[index]
        local left, right = lineForTooltipMatch(match)
        local selected = match.class == selection.class and match.spec == selection.spec
        if selected then
            tooltip:AddDoubleLine(left, right, 0.25, 1.0, 0.45, 0.25, 1.0, 0.45)
        else
            tooltip:AddDoubleLine(left, right, 1.0, 0.82, 0.28, 1.0, 0.82, 0.28)
        end
    end

    local rawDiffersFromGrouped = #rawMatches ~= #groupedMatches
    local hasHiddenRows = #matches > maxRows
    if not showRaw and settings.showAllOnAlt and (rawDiffersFromGrouped or hasHiddenRows) then
        tooltip:AddLine("Hold ALT to show all Big BiS List matches", 0.62, 0.62, 0.66)
    end
end

local function hookTooltip(tooltip)
    if not tooltip or tooltip.__bigBisListHooked then
        return
    end
    tooltip.__bigBisListHooked = true
    tooltip:HookScript("OnTooltipSetItem", function(hookedTooltip)
        addTooltipInfoSafely(hookedTooltip)
    end)
    tooltip:HookScript("OnTooltipCleared", clearTooltipRenderGuard)
end

function BigBiSList:InitTooltip()
    if self.tooltipInitialized then
        return
    end

    if TooltipDataProcessor and Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip, tooltipData)
            addTooltipInfoSafely(tooltip, tooltipData)
        end)
    end

    hookTooltip(GameTooltip)
    hookTooltip(ItemRefTooltip)

    self.tooltipInitialized = true
end
