local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local LEVELING_PHASE_KEY = BigBiSList.levelingPhaseKey or "LEVELING"

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
        tooltip.__bigBisListItemId = nil
        tooltip.__bigBisListExpanded = nil
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

local function getTooltipPriorityContext()
    if not BigBiSList.DetectPlayerClass then
        return nil
    end

    local playerClass = BigBiSList:DetectPlayerClass()
    if not playerClass then
        return nil
    end

    return {
        playerClass = playerClass,
        playerSpec = BigBiSList.DetectPlayerSpec and BigBiSList:DetectPlayerSpec(playerClass) or nil,
    }
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

local function familiarTooltipText(value)
    local text = tostring(value or "")
    text = string.gsub(text, "No match", "Not ranked")
    text = string.gsub(text, "Hard Farm", "Hard")
    text = string.gsub(text, "Nice%-to%-have", "Optional")
    text = string.gsub(text, "%f[%a]Alt%f[%A]", "Alternative")
    return (string.gsub(string.gsub(text, "^%s+", ""), "%s+$", ""))
end

local function lineForTooltipMatch(match)
    local left = match.class .. " " .. match.spec
    if match.slot and match.slot ~= "" then
        left = left .. " - " .. match.slot
    end

    if match.tooltip_grouped then
        return left, familiarTooltipText(match.phase_summary)
    end

    local right = BigBiSList:GetPhaseDisplayName(match.phase)
    if match.leveling then
        right = match.tooltip_level_label or match.level_label or "Leveling"
    end
    local tagLabel = match.display_rank_label or match.rank_label
    if not match.leveling and tagLabel and tagLabel ~= "" then
        right = right .. " " .. familiarTooltipText(tagLabel)
    end

    return left, right
end

-- Rebuild through the tooltip's native source; never clear or copy native lines.
-- The normal item hooks reattach our section after that rebuild.
local function refreshTooltipForModifier(tooltip)
    if not shouldAnnotateTooltip(tooltip) or tooltip.__bigBisListRefreshing then return end
    if tooltip.IsShown and not tooltip:IsShown() then return end
    local itemId = itemIdFromTooltip(tooltip)
    if not itemId or not tooltip.__bigBisListRenderKey then return end
    local settings = BigBiSListDB and BigBiSListDB.profile and BigBiSListDB.profile.tooltips
    if not settings or settings.enabled == false or not settings.showAllOnAlt then return end
    local expanded = not not (IsAltKeyDown and IsAltKeyDown())
    if tooltip.__bigBisListExpanded == expanded then return end

    tooltip.__bigBisListRefreshing = true
    local refreshed = false
    if tooltip.RefreshData then
        refreshed = pcall(tooltip.RefreshData, tooltip)
    elseif tooltip.GetOwner then
        local ok, owner = pcall(tooltip.GetOwner, tooltip)
        if ok and owner and type(owner.UpdateTooltip) == "function" then
            refreshed = pcall(owner.UpdateTooltip, owner)
        end
    end
    -- Classic tooltips do not always expose RefreshData/UpdateTooltip. The exact
    -- hyperlink retains enchant/gem/instance information when that fallback runs.
    if not refreshed and tooltip.GetItem and tooltip.SetHyperlink then
        local ok, _, link = pcall(tooltip.GetItem, tooltip)
        if ok and link and itemIdFromLink(link) == itemId then
            refreshed = pcall(tooltip.SetHyperlink, tooltip, link)
        end
    end
    if refreshed then
        addTooltipInfoSafely(tooltip)
        if tooltip.Show then tooltip:Show() end
    end
    tooltip.__bigBisListRefreshing = nil
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

    local selection = self:GetCharacterDB().selection or {}
    local effectivePhaseKey = self.GetEffectivePhaseKey and self:GetEffectivePhaseKey(selection) or selection.phase
    local levelingMode = effectivePhaseKey == LEVELING_PHASE_KEY
    local selectedLevel = levelingMode and self.GetSelectedLevelingLevel and self:GetSelectedLevelingLevel() or nil
    local selectedSpecFirst = settings.selectedSpecFirst ~= false
    local specFilters = settings.specFilters
    local priorityContext = getTooltipPriorityContext()
    priorityContext = priorityContext or {}
    priorityContext.selectedPhase = effectivePhaseKey
    local rawMatches = levelingMode
        and self:GetLevelingTooltipMatches(itemId, selection.class, selection.spec, selectedLevel, selectedSpecFirst, specFilters, priorityContext)
        or self:GetTooltipMatches(itemId, selection.class, selection.spec, selectedSpecFirst, specFilters, priorityContext)
    if #rawMatches == 0 then
        return
    end

    local showExpanded = settings.showAllOnAlt and IsAltKeyDown and IsAltKeyDown()
    local groupedMatches = levelingMode
        and self:GetGroupedLevelingTooltipMatches(itemId, selection.class, selection.spec, selectedLevel, selectedSpecFirst, specFilters, priorityContext, showExpanded)
        or self:GetGroupedTooltipMatches(itemId, selection.class, selection.spec, selectedSpecFirst, specFilters, priorityContext, showExpanded)
    local matches = groupedMatches
    local maxRows = showExpanded and #matches or (settings.compact and 4 or 8)
    local renderKey = table.concat({
        tostring(itemId),
        tostring(settings.compact),
        tostring(settings.selectedSpecFirst),
        tostring(settings.showAllOnAlt),
        tostring(showExpanded),
        tostring(selection.class),
        tostring(selection.spec),
        tostring(effectivePhaseKey),
        tostring((BigBiSListData or {}).active_schedule),
        tostring(self.GetCurrentPhaseKey and self:GetCurrentPhaseKey()),
        tostring(selectedLevel),
        tostring(priorityContext and priorityContext.playerClass),
        tostring(priorityContext and priorityContext.playerSpec),
        self:GetTooltipSpecFilterKey(specFilters),
    }, ":")
    if tooltip.__bigBisListRenderKey == renderKey then
        return
    end
    if tooltip.__bigBisListRenderKey then
        refreshTooltipForModifier(tooltip)
        return
    end
    tooltip.__bigBisListRenderKey = renderKey
    tooltip.__bigBisListItemId = itemId
    tooltip.__bigBisListExpanded = not not showExpanded

    tooltip:AddLine(" ")
    tooltip:AddLine("Big BiS List", 1.0, 0.82, 0.28)

    for index = 1, math.min(#matches, maxRows) do
        local match = matches[index]
        local left, right = lineForTooltipMatch(match)
        local selected = match.class == selection.class and match.spec == selection.spec
        if selected then
            tooltip:AddDoubleLine(left, right, 1.0, 0.9, 0.62, 1.0, 0.9, 0.62)
        else
            tooltip:AddDoubleLine(left, right, 0.76, 0.8, 0.86, 0.76, 0.8, 0.86)
        end
    end

    local rawDiffersFromGrouped = #rawMatches ~= #groupedMatches
    local hasHiddenRows = #matches > maxRows
    if not showExpanded and settings.showAllOnAlt and (rawDiffersFromGrouped or hasHiddenRows) then
        tooltip:AddLine("Hold Alt for all rankings", 0.62, 0.66, 0.72)
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

    if TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall and Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip, tooltipData)
            addTooltipInfoSafely(tooltip, tooltipData)
        end)
    end

    hookTooltip(GameTooltip)
    hookTooltip(ItemRefTooltip)

    if CreateFrame then
        local modifierFrame = CreateFrame("Frame")
        modifierFrame:RegisterEvent("MODIFIER_STATE_CHANGED")
        modifierFrame:SetScript("OnEvent", function(_, _, key)
            if key == "LALT" or key == "RALT" or key == "ALT" then
                refreshTooltipForModifier(GameTooltip)
                refreshTooltipForModifier(ItemRefTooltip)
            end
        end)
        self.tooltipModifierFrame = modifierFrame
    end

    self.tooltipInitialized = true
end
