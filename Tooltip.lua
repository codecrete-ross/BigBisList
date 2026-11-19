local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local LEVELING_PHASE_KEY = BigBiSList.levelingPhaseKey or "LEVELING"

local function readable(value)
    if not issecretvalue or not issecretvalue(value) then return value end
end

local function checked(ok, ...)
    if ok then return ... end
end

local function call(method, ...)
    if type(method) == "function" then return checked(pcall(method, ...)) end
end

local function itemIdFromLink(link)
    if type(link) ~= "string" or (issecretvalue and issecretvalue(link)) then
        return nil
    end
    return tonumber(string.match(link, "item:(%d+)"))
end

local function itemIdFromTooltipData(data)
    if type(readable(data)) ~= "table" then
        return nil
    end

    local itemId = tonumber(readable(data.id) or readable(data.itemID) or readable(data.itemId))
    if itemId then
        return itemId
    end

    itemId = itemIdFromLink(readable(data.hyperlink) or readable(data.guid))
    if itemId then
        return itemId
    end

    if type(readable(data.lines)) == "table" then
        for _, line in ipairs(data.lines) do
            if type(readable(line)) == "table" then
                itemId = itemIdFromLink(readable(line.hyperlink) or readable(line.guid))
                if itemId then
                    return itemId
                end
            end
        end
    end

    return nil
end

local function itemIdFromTooltip(tooltip, tooltipData)
    tooltipData = readable(tooltipData) or readable(call(tooltip and tooltip.GetPrimaryTooltipData, tooltip))
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

local function itemLinkFromTooltip(tooltip, data, itemId, info)
    local _, link = call(tooltip.GetItem, tooltip)
    if itemIdFromLink(link) == itemId then return link end
    data = readable(data) or call(tooltip.GetPrimaryTooltipData, tooltip)
    if type(readable(data)) == "table" then
        link = readable(data.hyperlink)
        if itemIdFromLink(link) == itemId then return link end
    end
    link = call(tooltip.GetHyperlink, tooltip)
    if itemIdFromLink(link) == itemId then return link end
    local getter = info and readable(info.getterName)
    local args = info and readable(info.getterArgs)
    if type(args) ~= "table" then return nil end
    if getter == "GetHyperlink" then
        link = readable(args[1])
    elseif getter == "GetInventoryItem" then
        link = call(GetInventoryItemLink, readable(args[1]), readable(args[2]))
    elseif getter == "GetBagItem" then
        local getLink = C_Container and C_Container.GetContainerItemLink or GetContainerItemLink
        link = call(getLink, readable(args[1]), readable(args[2]))
    elseif getter == "GetQuestItem" then
        link = call(GetQuestItemLink, readable(args[1]), readable(args[2]))
    elseif getter == "GetQuestLogItem" then
        link = call(GetQuestLogItemLink, readable(args[1]), readable(args[2]))
    elseif getter == "GetLootItem" then
        link = call(GetLootSlotLink, readable(args[1]))
    elseif getter == "GetLootRollItem" then
        link = call(GetLootRollItemLink, readable(args[1]))
    elseif getter == "GetMerchantItem" then
        link = call(GetMerchantItemLink, readable(args[1]))
    elseif getter == "GetTradeTargetItem" then
        link = call(GetTradeTargetItemLink, readable(args[1]))
    elseif getter == "GetInboxItem" then
        link = call(GetInboxItemLink, readable(args[1]), readable(args[2]))
    end
    if itemIdFromLink(link) == itemId then return link end
end

local function primaryInfo(tooltip)
    local info = readable(call(tooltip.GetProcessingTooltipInfo, tooltip)) or readable(call(tooltip.GetPrimaryTooltipInfo, tooltip))
    if type(readable(info)) == "table" then return info end
end

local function clearTooltipRenderGuard(tooltip)
    tooltip.__bigBisListState = nil
end

local function shouldAnnotateTooltip(tooltip)
    if not tooltip or not tooltip.AddLine or not tooltip.AddDoubleLine or call(tooltip.IsForbidden, tooltip) then
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
    if not shouldAnnotateTooltip(tooltip) or tooltip.__bigBisListAnnotating then
        return
    end

    tooltip.__bigBisListAnnotating = true
    local ok, err = pcall(BigBiSList.AddTooltipInfo, BigBiSList, tooltip, tooltipData)
    tooltip.__bigBisListAnnotating = nil
    if not ok then
        reportTooltipError(err)
    end
end

local function addonTooltip(tooltip)
    if tooltip ~= GameTooltip then return false end
    local ui = BigBiSList.UI
    if not ui or not ui.frame then return false end
    local owner = readable(call(tooltip.GetOwner, tooltip))
    while owner do
        if owner == ui.frame or owner == ui.comparisonFrame or owner == ui.details then return true end
        owner = readable(call(owner.GetParent, owner))
    end
    return false
end

local function familiarTooltipText(value)
    local text = tostring(value or "")
    text = string.gsub(text, "No match", "Not ranked")
    text = string.gsub(text, "Hard Farm", "Hard")
    text = string.gsub(text, "Nice%-to%-have", "Optional")
    text = BigBiSList.isForever and BigBiSList:GetGuideRatingDisplay(text) or string.gsub(text, "%f[%a]Alt%f[%A]", "Alternative")
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

local function comparisonTooltipContext(tooltip)
    local ui = BigBiSList.UI
    local state = ui and ui.slotComparison
    if not state or tooltip ~= GameTooltip or not tooltip.GetOwner then return nil end
    local ok, owner = pcall(tooltip.GetOwner, tooltip)
    if not ok then return nil end
    -- Only addon-owned comparison surfaces inherit the local role. Native bag,
    -- equipment and item-reference tooltips continue using character settings.
    while owner do
        if owner == ui.comparisonFrame or (state.detailsOpen and owner == ui.details) then return state end
        owner = owner.GetParent and owner:GetParent()
    end
    return nil
end

local EXTRA_COPY_GETTERS = {
    GetLootItem = true, GetLootRollItem = true, GetMerchantItem = true, GetQuestItem = true, GetQuestLogItem = true,
    GetAuctionItem = true, GetTradeTargetItem = true, GetInboxItem = true, GetRecipeResultItem = true,
}
local OWNED_LABELS = { equipped = "Equipped", bag = "In bags", bank = "In bank (last visit)" }

local function tooltipStatBlock(addon, candidate, player, info, offer)
    local rating, ui = addon.ForeverGearRating, addon.UI
    local block = { rows = {}, pending = {} }
    if not candidate.facts or not candidate.facts.level then
        block.rows[1] = { spec = player.spec or "Gear", result = { placement = { status = candidate.status or "unavailable" } } }
        if candidate.status == "loading" then block.pending[candidate.entry.item_id] = true end
        return block
    end
    local getter = info and readable(info.getterName)
    local args = info and readable(info.getterArgs)
    local wornSlot = getter == "GetInventoryItem" and type(args) == "table"
        and readable(args[1]) == "player" and readable(args[2]) or nil
    local snapshot = ui:GetOwnedSnapshot()
    local offerAssessments = offer and offer.assessments or {}
    local inventoryPending
    for _, spec in ipairs(player.specs) do
        local context = rating:GetContext(player.class, spec.name, player.phase, player.level, snapshot)
        if context then
            inventoryPending = context.pending
            local assessment
            for _, existing in ipairs(offerAssessments) do
                if existing.spec.name == spec.name then
                    assessment = existing
                    break
                end
            end
            if not assessment and (#offerAssessments == 0 or offer.kind ~= "quest") then
                local worn = (spec.role == "active" or (offer and offer.owned)) and (not offer or offer.compareWorn)
                local result = rating:CompareTooltipItem(context, candidate, worn, worn and wornSlot or nil,
                    (offer and not offer.owned) or EXTRA_COPY_GETTERS[getter],
                    { live = true, lookahead = true, quantity = offer and offer.quantity })
                assessment = { result = result, ownedBaseline = not worn }
            end
            if assessment then
                block.rows[#block.rows + 1] = { spec = spec.name, result = assessment.result, assessment = assessment }
                block.ownership = block.ownership or assessment.result.ownership
            end
        end
    end
    for id in pairs(inventoryPending or {}) do block.pending[id] = true end
    for id, request in pairs(ui.pendingItemLoads or {}) do
        if request.ownedMetadata then block.pending[id] = true end
    end
    if #block.rows > 0 then return block end
end

local function colorText(text, r, g, b)
    return string.format("|cff%02x%02x%02x%s|r", math.floor(r * 255 + 0.5), math.floor(g * 255 + 0.5),
        math.floor(b * 255 + 0.5), text)
end

local function tooltipRank(result)
    local rating, placement = BigBiSList.ForeverGearRating, result.placement
    local label = rating:Label(placement, "compact")
    if placement.score ~= nil then
        label = label .. " at Lv " .. placement.level
        if placement.phase == "PR" then label = rating:ScopeLabel(placement) .. " · " .. label end
    end
    if placement.score_percent then label = label .. " (" .. placement.score_percent .. "% of best)" end
    return placement.projected and ("Projected · " .. label) or label
end

local function deltaText(delta)
    local points = math.abs(BigBiSList.ForeverGearRating:RoundedGain(delta) or 0)
    if points == 0 then return "0.0 pts" end
    if delta > 0 then return colorText(string.format("+%.1f pts", points), 0.3, 0.94, 0.58) end
    return colorText(string.format("-%.1f pts", points), 1, 0.51, 0.51)
end

local function replacementNames(result)
    local names = {}
    for _, item in ipairs(result.replacements) do
        names[#names + 1] = item.name .. " (" .. item.slot .. (item.state == "bank" and ", bank" or "") .. ")"
    end
    return table.concat(names, " + ")
end

local function swapText(result, ownedBaseline, guaranteed)
    local bank = result.bank and " (includes bank gear)" or ""
    if result.status == "equipped" then return "Equipped · " .. result.definition.label end
    if result.status == "loading" then return "Loading stats" end
    if result.status == "blocked" then return "No legal swap" end
    if result.status == "best_owned" then return "Best you own for this slot" .. bank end
    if result.delta == nil then return nil end
    local estimate = "Est. " .. deltaText(result.delta)
    if result.status == "empty" then
        return estimate .. " to fill an empty slot" .. bank
    end
    local baseline = estimate .. " vs the best gear you own" .. bank
    if guaranteed then baseline = baseline .. " with guaranteed rewards" end
    local replacements = replacementNames(result)
    if ownedBaseline then return replacements ~= "" and (baseline .. ", replacing " .. replacements) or baseline end
    return replacements ~= "" and (estimate .. " vs " .. replacements) or estimate
end

local function forecastText(forecast)
    local level = "At Lv " .. forecast.level .. " · "
    if forecast.delta == nil then
        return level .. (forecast.status == "loading" and "Loading owned item stats" or "Owned gear comparison unavailable")
    end
    local rating = BigBiSList.ForeverGearRating
    local estimate = "Est. " .. deltaText(forecast.delta)
    if forecast.delta ~= 0 and rating:RoundedGain(forecast.delta) == 0 then
        estimate = forecast.delta > 0 and "Est. gain below 0.1 pts" or "Est. loss below 0.1 pts"
    end
    local comparison
    if forecast.status == "best_owned" then comparison = "Best you own for this slot"
    elseif forecast.status == "empty" and #forecast.replacements == 0 then comparison = estimate .. " to fill an empty slot"
    elseif forecast.delta == 0 then comparison = forecast.conditional and "Same modeled score as best owned" or "Same score as best owned"
    else comparison = estimate .. " vs best owned" end
    local replacements = replacementNames(forecast)
    if replacements ~= "" then comparison = comparison .. ", replacing " .. replacements end
    if forecast.bank then comparison = comparison .. " · Includes cached bank gear" end
    return level .. comparison .. " · " .. rating:GetSwapBasisLabel(forecast.basis)
        .. (forecast.conditional and " · Conditional" or "")
end

local function storageText(comparison)
    if comparison.unavailable == "loading" then return "Loading owned item stats" end
    if comparison.unavailable then return "Owned gear comparison unavailable" end
    if comparison.qualifies then
        local text = "Recommended upgrade"
        local result = comparison.result
        for _, item in ipairs(result.incoming or {}) do
            if item.slot ~= result.definition.label then text = text .. " · With " .. item.name end
        end
        return text
    end
    if comparison.winner then return "Best you own for this slot" end
    if comparison.stronger and #comparison.stronger > 0 then
        local names = {}
        for _, item in ipairs(comparison.stronger) do
            local location = OWNED_LABELS[item.state]
            names[#names + 1] = item.name .. (location and (" · " .. location) or "")
        end
        return (comparison.sidegrade and "Sidegrade to " or "Stronger option you own · ") .. table.concat(names, " + ")
    end
end

local function renderSpecBlocks(tooltip, statBlock, matches, selection)
    local blocks, bySpec = {}, {}
    for _, row in ipairs(statBlock and statBlock.rows or {}) do
        row.class, row.matches = selection.class, {}
        blocks[#blocks + 1] = row
        bySpec[row.class .. "/" .. row.spec] = row
    end
    for _, match in ipairs(matches) do
        local key = match.class .. "/" .. match.spec
        local row = bySpec[key]
        if not row then
            row = { class = match.class, spec = match.spec, matches = {} }
            blocks[#blocks + 1] = row
            bySpec[key] = row
        end
        row.matches[#row.matches + 1] = match
    end
    local placementColor
    for _, row in ipairs(blocks) do
        tooltip:AddLine(" ")
        local spec = row.class == selection.class and row.spec or (row.class .. " " .. row.spec)
        local result = row.result
        local r, g, b = 0.93, 0.93, 0.96
        local tier = result and result.placement.tier
        if tier then r, g, b = BigBiSList.Widgets:GetRankColor(tier.quality) end
        if result and result.bis then spec = colorText("BiS", unpack(BigBiSList.Widgets.Theme.bisGold)) .. "  " .. spec end
        tooltip:AddLine(spec, r, g, b, true)
        if result then
            local comparison = row.assessment or row
            local rank = tooltipRank(result)
            if result.placement.conditional and not result.placement.conditional_tie then rank = rank .. " · Conditional" end
            tooltip:AddLine(rank, r, g, b, true)
            local extra = result.forecast and forecastText(result.forecast)
                or swapText(result, comparison.ownedBaseline, comparison.guaranteed)
            if extra then
                if result.delta ~= nil then
                    extra = BigBiSList.ForeverGearRating:GetSwapBasisLabel(result.basis) .. " · " .. extra
                    if result.conditional then extra = extra .. " · Conditional" end
                end
                tooltip:AddLine(extra, 0.86, 0.88, 0.91, true)
            end
            if result.conditional and not extra then
                tooltip:AddLine("Conditional · effect or comparison data is incomplete", 0.86, 0.88, 0.91, true)
            end
            if comparison.storage then
                local recommendation = storageText(comparison.storage)
                if recommendation then tooltip:AddLine(recommendation, 0.86, 0.88, 0.91, true) end
            end
            if comparison.bestChoice then
                tooltip:AddLine("Best choice for " .. row.spec, 0.86, 0.88, 0.91, true)
            elseif comparison.tiedChoice then
                tooltip:AddLine("Tied for best choice", 0.86, 0.88, 0.91, true)
            end
            if comparison.futureBiS then tooltip:AddLine("Pre-Raid Guide BiS", 0.86, 0.88, 0.91, true) end
            if result.effectNote then tooltip:AddLine(result.effectNote, 0.76, 0.8, 0.86, true) end
            if result.effectBreakEven then
                local estimate = string.format("%.1f full extra swings per minute to close the gap at tooltip weapon damage",
                    result.effectBreakEven)
                tooltip:AddLine(estimate, 0.76, 0.8, 0.86, true)
            end
            placementColor = placementColor or result.placement.placement_color
        end
        for _, match in ipairs(row.matches) do
            local _, summary = lineForTooltipMatch(match)
            if match.scoring_label and match.class == selection.class and match.spec == selection.spec then
                summary = summary .. " · " .. match.scoring_label
            end
            local slot = match.slot and match.slot ~= "" and (" · " .. match.slot) or ""
            local guide = match.leveling and "Gear Guide" or "BiS List"
            tooltip:AddLine(guide .. " · " .. summary .. slot, 0.76, 0.8, 0.86, true)
        end
    end
    if placementColor then tooltip:AddLine("Small pools use slot placement for color", 0.72, 0.77, 0.84, true) end
end

local function rebuildTooltip(tooltip, state)
    if not shouldAnnotateTooltip(tooltip) or not state or tooltip.__bigBisListState ~= state
        or tooltip.__bigBisListRefreshing then return end
    if tooltip.IsShown and not tooltip:IsShown() then return end
    local owner = readable(call(tooltip.GetOwner, tooltip))
    local info = primaryInfo(tooltip)
    local itemId = itemIdFromTooltip(tooltip)
    if owner ~= state.owner or itemId ~= state.itemId
        or itemLinkFromTooltip(tooltip, nil, itemId, info) ~= state.link then return end

    -- The native rebuild retains source-specific lines, position and the exact link.
    tooltip.__bigBisListRefreshing = true
    local function attempt(method, ...)
        return type(method) == "function" and pcall(method, ...) and tooltip.__bigBisListState ~= state
    end
    local refreshed = attempt(tooltip.RefreshData, tooltip)
        or (info and attempt(tooltip.RebuildFromTooltipInfo, tooltip))
        or (owner and attempt(owner.UpdateTooltip, owner))
    if not refreshed and state.link and (not BigBiSList.isForever or not info or readable(info.getterName) == "GetHyperlink") then
        refreshed = attempt(tooltip.SetHyperlink, tooltip, state.link)
    end
    if refreshed then
        addTooltipInfoSafely(tooltip)
        if tooltip.Show then tooltip:Show() end
    end
    tooltip.__bigBisListRefreshing = nil
end

local function refreshTooltipForModifier(tooltip)
    if not tooltip or not tooltip.__bigBisListState then return end
    local database = BigBiSList.isForever and BigBiSList:GetAccountDB() or BigBiSListDB
    local settings = database and database.profile and database.profile.tooltips
    if not settings or settings.enabled == false or not settings.showAllOnAlt then return end
    local expanded = not not (IsAltKeyDown and IsAltKeyDown())
    local state = tooltip.__bigBisListState
    if state.expanded ~= expanded then rebuildTooltip(tooltip, state) end
end

function BigBiSList:ScheduleItemTooltipRefresh(itemId)
    local queued = self.queuedItemTooltips
    for _, tooltip in pairs({ GameTooltip, ItemRefTooltip }) do
        local state = tooltip.__bigBisListState
        if state and (state.stats or state.acquisition) and (not itemId or state.pending[itemId]) then
            queued = queued or {}
            queued[tooltip] = state
        end
    end
    if not queued or self.queuedItemTooltips then return end
    self.queuedItemTooltips = queued
    local function refresh()
        self.queuedItemTooltips = nil
        for tooltip, state in pairs(queued) do rebuildTooltip(tooltip, state) end
    end
    if C_Timer and C_Timer.After then C_Timer.After(0, refresh) else refresh() end
end

local function prepareItemTooltip(self, tooltip, itemId, itemLink, owner, info, settings)
    local offer, mark
    if self.AcquisitionHighlights then offer, mark = self.AcquisitionHighlights:GetTooltipOffer(owner, itemId, itemLink) end
    local live, statBlock
    if self.ForeverGearRating and itemLink and self.UI and self.UI.GetOwnedSnapshot and not addonTooltip(tooltip) then
        local exactLink = offer and offer.owned and offer.link or itemLink
        local candidate = self.ForeverGearRating:GetTooltipItem(itemId, exactLink)
        live = candidate and self:GetTooltipPlayerContext()
        if live then statBlock = tooltipStatBlock(self, candidate, live, info, offer) end
    end
    local comparisonContext = comparisonTooltipContext(tooltip)
    local selection = comparisonContext or live or self:GetCharacterDB().selection or {}
    local effectivePhaseKey = comparisonContext and comparisonContext.phase
        or (live and live.phase) or (self.GetEffectivePhaseKey and self:GetEffectivePhaseKey(selection) or selection.phase)
    local levelingMode = effectivePhaseKey == LEVELING_PHASE_KEY
    local selectedLevel = levelingMode and ((live and live.level)
        or (comparisonContext and comparisonContext.level) or (self.GetSelectedLevelingLevel and self:GetSelectedLevelingLevel())) or nil
    local selectedSpecFirst = comparisonContext ~= nil or settings.selectedSpecFirst ~= false
    local specFilters = settings.specFilters
    local priorityContext = live and { playerClass = live.class, playerSpec = live.spec } or getTooltipPriorityContext()
    priorityContext = priorityContext or {}
    if comparisonContext then priorityContext.playerClass, priorityContext.playerSpec = selection.class, selection.spec end
    priorityContext.selectedPhase = effectivePhaseKey
    priorityContext.itemLink = itemLink

    local showExpanded = self.isForever or (settings.showAllOnAlt and IsAltKeyDown and IsAltKeyDown())
    local groupedMatches = {}
    local rawMatches = levelingMode
        and self:GetLevelingTooltipMatches(itemId, selection.class, selection.spec, selectedLevel, selectedSpecFirst, specFilters, priorityContext, itemLink)
        or self:GetTooltipMatches(itemId, selection.class, selection.spec, selectedSpecFirst, specFilters, priorityContext)
    if #rawMatches == 0 and not statBlock and not mark then return end
    if #rawMatches > 0 then
        groupedMatches = levelingMode
            and self:GetGroupedLevelingTooltipMatches(itemId, selection.class, selection.spec, selectedLevel, selectedSpecFirst, specFilters, priorityContext, showExpanded, itemLink)
            or self:GetGroupedTooltipMatches(itemId, selection.class, selection.spec, selectedSpecFirst, specFilters, priorityContext, showExpanded)
    end
    local matches = groupedMatches
    local maxRows = showExpanded and #matches or (settings.compact and 4 or 8)
    return {
        offer = offer, statBlock = statBlock, mark = mark, live = live, selection = selection,
        matches = matches, rawCount = #rawMatches, maxRows = maxRows, expanded = not not showExpanded,
    }
end

local function showItemTooltip(self, tooltip, itemId, itemLink, owner, settings, prepared)
    local offer, statBlock, mark = prepared.offer, prepared.statBlock, prepared.mark
    local live, selection, matches = prepared.live, prepared.selection, prepared.matches
    local showExpanded, maxRows = prepared.expanded, prepared.maxRows
    tooltip.__bigBisListState = { itemId = itemId, link = itemLink, owner = owner, acquisition = offer ~= nil,
        expanded = not not showExpanded, stats = statBlock ~= nil, pending = statBlock and statBlock.pending or {} }

    tooltip:AddLine(" ")
    local ownership = statBlock and OWNED_LABELS[statBlock.ownership]
    if ownership then
        tooltip:AddDoubleLine("Big BiS List", ownership, 1, 0.82, 0.28, 0.72, 0.77, 0.84)
    else
        tooltip:AddLine("Big BiS List", 1.0, 0.82, 0.28)
    end
    if mark and mark.sellValue then
        local money = readable(call(GetMoneyString, mark.sellValue))
        tooltip:AddLine(money and ("Highest sell value · " .. money) or "Highest sell value", 0.86, 0.88, 0.91, true)
    end
    if statBlock then
        if not live.spec and #statBlock.rows > 1 then tooltip:AddLine("Spec previews", 0.72, 0.77, 0.84) end
    end

    if self.isForever then
        renderSpecBlocks(tooltip, statBlock, matches, selection)
    else
        for index = 1, math.min(#matches, maxRows) do
            local match = matches[index]
            local left, right = lineForTooltipMatch(match)
            if match.scoring_label and match.class == selection.class and match.spec == selection.spec then
                right = right .. " · " .. match.scoring_label
            end
            local selected = match.class == selection.class and match.spec == selection.spec
            if selected then
                tooltip:AddDoubleLine(left, right, 1.0, 0.9, 0.62, 1.0, 0.9, 0.62)
            else
                tooltip:AddDoubleLine(left, right, 0.76, 0.8, 0.86, 0.76, 0.8, 0.86)
            end
        end
    end

    local rawDiffersFromGrouped = prepared.rawCount ~= #matches
    local hasHiddenRows = #matches > maxRows
    if not showExpanded and settings.showAllOnAlt and (statBlock or rawDiffersFromGrouped or hasHiddenRows) then
        tooltip:AddLine(statBlock and "Hold Alt for more details" or "Hold Alt for all rankings", 0.62, 0.66, 0.72)
    end
    if statBlock then self.UI:QueueStatLoads(statBlock.pending) end
end

function BigBiSList:AddTooltipInfo(tooltip, tooltipData)
    if not shouldAnnotateTooltip(tooltip) or tooltip.__bigBisListState then return end
    local database = self:EnsureDatabase() or (not self.isForever and BigBiSListDB)
    local settings = database and database.profile and database.profile.tooltips
    if not settings or settings.enabled == false then return end
    local itemId = itemIdFromTooltip(tooltip, tooltipData)
    if not itemId then return end
    local info = primaryInfo(tooltip)
    if info and readable(info.append) then return end
    local itemLink = itemLinkFromTooltip(tooltip, tooltipData, itemId, info)
    local owner = readable(call(tooltip.GetOwner, tooltip))
    local highlights = self.AcquisitionHighlights
    if highlights and itemLink and highlights:ShouldDeferStorageTooltip(owner, info and readable(info.getterName)) then
        local state = { itemId = itemId, link = itemLink, owner = owner }
        tooltip.__bigBisListState = state
        local function isCurrent()
            local currentInfo = primaryInfo(tooltip)
            return tooltip.__bigBisListState == state and shouldAnnotateTooltip(tooltip) and tooltip:IsShown()
                and readable(call(tooltip.GetOwner, tooltip)) == owner and itemIdFromTooltip(tooltip) == itemId
                and itemLinkFromTooltip(tooltip, nil, itemId, currentInfo) == itemLink
                and highlights:IsStorageTooltipCurrent(owner, itemId, itemLink,
                    currentInfo and readable(currentInfo.getterName), currentInfo and readable(currentInfo.getterArgs))
        end
        highlights:QueueStorageTooltip(tooltip, function()
            if not isCurrent() then
                if tooltip.__bigBisListState == state then tooltip.__bigBisListState = nil end
                return
            end
            local prepared = prepareItemTooltip(self, tooltip, itemId, itemLink, owner, primaryInfo(tooltip), settings)
            local checkpoint = highlights:GetCheckpoint()
            if checkpoint then checkpoint() end
            if isCurrent() then
                tooltip.__bigBisListState = nil
                if prepared and settings.enabled ~= false then
                    showItemTooltip(self, tooltip, itemId, itemLink, owner, settings, prepared)
                    if tooltip.Show then tooltip:Show() end
                end
            end
        end)
        return
    end
    local prepared = prepareItemTooltip(self, tooltip, itemId, itemLink, owner, info, settings)
    if prepared then showItemTooltip(self, tooltip, itemId, itemLink, owner, settings, prepared) end
end

local function hookTooltip(tooltip)
    if not tooltip or tooltip.__bigBisListHooked then
        return
    end
    tooltip.__bigBisListHooked = true
    -- Forever uses TooltipDataProcessor and no longer exposes the legacy item script.
    if not tooltip.HasScript or tooltip:HasScript("OnTooltipSetItem") then
        tooltip:HookScript("OnTooltipSetItem", function(hookedTooltip)
            addTooltipInfoSafely(hookedTooltip)
        end)
    end
    if not tooltip.HasScript or tooltip:HasScript("OnTooltipCleared") then
        tooltip:HookScript("OnTooltipCleared", clearTooltipRenderGuard)
    end
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

    if not self.isForever and CreateFrame then
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
