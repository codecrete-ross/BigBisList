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

function BigBiSList:TooltipHasLevelRequirement(tooltip, level, tooltipData)
    if not level then return false end
    local text = call(string.format, ITEM_MIN_LEVEL or "Requires Level %d", level) or ("Requires Level " .. level)
    local function matches(value)
        value = readable(value)
        return type(value) == "string" and value:find(text, 1, true) ~= nil
    end
    local data = readable(tooltipData) or readable(call(tooltip.GetPrimaryTooltipData, tooltip))
    for _, line in ipairs(type(data) == "table" and readable(data.lines) or {}) do
        if type(readable(line)) == "table" and matches(line.leftText) then return true end
    end
    if tooltip.GetRegions then
        for _, region in ipairs({ call(tooltip.GetRegions, tooltip) }) do
            if matches(call(region.GetText, region)) then return true end
        end
    end
    return false
end

local function tooltipLevelingView(addon, tooltip, tooltipData, context, candidate, assessment, spec, offer)
    local rating = addon.ForeverGearRating
    local result, item = assessment.result, candidate.facts
    local placement = result.placement
    local leveling = (context.leveling and placement.phase ~= "PR") or placement.phase == LEVELING_PHASE_KEY
    local slot = placement.slot or item.slot
    local summary, record
    if slot and item.level <= addon.maxLevelingLevel and rating:GetPublishedFacts(item.key) then
        local guide = rating:GetGuideContext(context.class, context.spec, LEVELING_PHASE_KEY,
            math.min(context.level, addon.maxLevelingLevel), context.race, context.faction)
        summary = rating:GetLevelingSummary(guide)
        record = rating:GetLevelingRecord(summary, slot, item.key)
    end
    local viewed = placement.level or context.level
    local sourceLevel, sourceType
    local first = record and record.ranked[1]
    local routeLevel = first and first.firstLevel or placement.level
    if routeLevel and context.leveling and routeLevel > context.level then
        local access = addon:GetRowAcquisitionDisplay({ item_id = item.id }, { class = context.class, race = context.race,
            faction = context.faction, level = routeLevel, _leveling = true }, LEVELING_PHASE_KEY, false, true)
        sourceLevel, sourceType = addon:GetLevelingSourceGate(access)
    end
    if leveling and not placement.phase then
        placement = rating:LevelingPlacementAt(record, viewed)
            or {phase = LEVELING_PHASE_KEY, level = viewed, status = placement.status}
    end
    local view = rating:LevelingPresentation({ item = item, placement = placement, record = record,
        swap = result, playerLevel = context.level, sourceLevel = sourceLevel, sourceType = sourceType,
        ownedBaseline = true, ownership = offer and (offer.owned and result.ownership or "offered"),
        activeSpec = spec.role == "active", spec = spec.name, chooseReward = assessment.bestChoice and spec.role == "active"
            and offer and offer.turnIn, nativeRequirement = addon:TooltipHasLevelRequirement(tooltip, item.level, tooltipData) })
    return view, summary, slot
end

local function tooltipStatBlock(addon, candidate, player, info, offer, tooltip, tooltipData, deadline, compact)
    local rating, ui = addon.ForeverGearRating, addon.UI
    local block = { rows = {}, pending = {} }
    if candidate.status == "loading" or not candidate.facts or not candidate.facts.level then
        block.rows[1] = { spec = player.spec or "Gear", result = { placement = { status = candidate.status or "unavailable" } } }
        if candidate.status == "loading" then block.pending[candidate.entry.item_id] = true end
        return block
    end
    local getter = info and readable(info.getterName)
    local args = info and readable(info.getterArgs)
    local storageId, equippedKey
    if offer and offer.owned then
        storageId = offer.sourceId
    elseif getter == "GetBagItem" and type(args) == "table" then
        local bag, index = readable(args[1]), readable(args[2])
        if type(bag) == "number" and type(index) == "number" then storageId = bag .. ":" .. index end
    elseif getter == "GetInventoryItem" and type(args) == "table" and readable(args[1]) == "player" then
        local slot = readable(args[2])
        for _, definition in ipairs(addon:GetEquipmentSlotDefinitions()) do
            if definition.inventorySlotId == slot then equippedKey = definition.key; break end
        end
    end
    local snapshot = ui.GetTooltipOwnedSnapshot and ui:GetTooltipOwnedSnapshot() or ui:GetOwnedSnapshot()
    local offerAssessments = offer and offer.assessments or {}
    local inventoryPending
    local function addSpec(spec)
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
                local result
                if storageId and not snapshot.equippedOnly then
                    result = rating:GetStorageComparison(context, candidate, storageId, offer and offer.guid)
                elseif equippedKey then
                    local held = context.equipmentFacts[equippedKey]
                    if held and held.facts and rating:SameExactItemLink(candidate.entry.item_id, candidate.item_link, held.item_link) then
                        result = rating:GetHeldComparison(context, held)
                    end
                end
                local extraCopy = EXTRA_COPY_GETTERS[getter]
                if offer then extraCopy = not offer.owned end
                assessment = { result = result or rating:CompareTooltipItem(context, candidate, false, nil, extraCopy,
                    { live = true, lookahead = true, quantity = offer and offer.quantity }) }
            end
            if assessment then
                local view, summary, slot = tooltipLevelingView(addon, tooltip, tooltipData, context, candidate, assessment, spec, offer)
                block.rows[#block.rows + 1] = { spec = spec.name, activeSpec = spec.role == "active", result = assessment.result, assessment = assessment,
                    view = view, summary = summary, summarySlot = slot, item = candidate.facts, context = context }
                block.ownership = block.ownership or assessment.result.ownership
            end
        end
    end
    for index, spec in ipairs(player.specs) do
        if snapshot.equippedOnly and #block.rows > 0 then break end
        local first = block.rows[1]
        if first and ((deadline and debugprofilestop() >= deadline)
            or (compact and first.activeSpec and rating:SwapExplanationPending(first.result))) then
            block.finishSpecs = function(checkpoint)
                for remaining = index, #player.specs do
                    checkpoint()
                    addSpec(player.specs[remaining])
                end
                for id in pairs(inventoryPending or {}) do block.pending[id] = true end
            end
            break
        end
        addSpec(spec)
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

local function compactSpecLine(row)
    local result, assessment, view = row.result, row.assessment or {}, row.view or {}
    if not result then
        local match = row.matches[1]
        return match and ("Guide pick · " .. (match.slot or match.spec))
    end
    local evaluated = result.forecast or result
    local reason = BigBiSList.Widgets:DecisionReason(row.item, result)
    local verdict = view.today
    if assessment.tiedChoice then verdict, reason = "Tied reward", "equal to another choice"
    elseif assessment.bestChoice then verdict = result.forecast and ("Best reward at level " .. evaluated.level) or "Best reward"
    elseif evaluated.status == "loading" or result.placement.status == "loading" then verdict = "Waiting for item stats"
    elseif result.forecast and evaluated.delta then
        local keep = evaluated.ownership == "bank" or evaluated.ownership == "bag" or result.ownership == "bank" or result.ownership == "bag"
        if evaluated.delta > 0 or evaluated.status == "best_owned" and keep then
            verdict = evaluated.conditional and "Possible upgrade" or keep and "Keep" or "Likely upgrade"
            verdict = verdict .. (verdict == "Keep" and " for level " or " at level ") .. evaluated.level
        else
            verdict = (evaluated.conditional and "Depends on your setup" or evaluated.delta < 0 and "Likely downgrade" or "Likely sidegrade")
                .. " at level " .. evaluated.level
        end
    elseif evaluated.status == "best_owned" and not evaluated.conditional then
        if evaluated.equipSwap and not row.activeSpec then verdict = "Keep for " .. row.spec
        elseif evaluated.equipNow then verdict = "Equip now"
        elseif evaluated.equipSwap and evaluated.ownership == "bank" then verdict = "Get from bank"
        elseif evaluated.ownership == "equipped" then verdict = "Keep equipped"
        elseif evaluated.ownership == "bank" then verdict = "Keep in bank"
        else verdict = "Keep" end
    elseif result.bis and not verdict then verdict = "Guide BiS"
    elseif not result.forecast and evaluated.conditional then verdict = (evaluated.delta or 0) > 0 and "Possible upgrade" or "Depends on your setup"
    elseif evaluated.status == "empty" then verdict = "Upgrade"
    elseif evaluated.delta == 0 and evaluated.status ~= "best_owned" then verdict = "Sidegrade"
    elseif evaluated.delta and evaluated.delta < 0 then verdict = "Downgrade"
    end
    verdict = verdict or view.requirement or BigBiSList.ForeverGearRating:Label(result.placement, "compact")
    local suffix = " for " .. row.spec
    if verdict ~= "Keep" .. suffix and verdict:sub(-#suffix) == suffix then verdict = verdict:sub(1, -#suffix - 1) end
    local summary
    if row.activeSpec and not assessment.tiedChoice then
        local action = evaluated.equipSwap
        if action and not result.forecast and action.roleDelta and action.replacements[1] then
            local names = {}
            for _, old in ipairs(action.replacements) do names[#names + 1] = old.name end
            local grade = BigBiSList.ForeverGearRating:UpgradeSize(action)
            if grade then reason = grade .. " over " .. table.concat(names, " + ") end
        end
        summary = BigBiSList.Widgets:SwapDecisionSummary(row.item, result)
        if summary == reason or (reason and summary == "Gains " .. reason:gsub("^%+", "") .. ".") then summary = nil end
    elseif not row.activeSpec and not assessment.tiedChoice and evaluated.replacements and evaluated.replacements[1] then
        local names = {}
        for _, old in ipairs(evaluated.replacements) do
            local location = old.state == "bag" and " in your bags" or old.state == "bank" and " in your bank" or " equipped"
            names[#names + 1] = old.name .. location
        end
        reason = "vs. " .. table.concat(names, " + ")
    end
    local separator = reason and reason:sub(1, 4) == "vs. " and " " or " · "
    return verdict .. (reason and (separator .. reason) or ""), view.tone, summary
end

local function addSwapExplanation(tooltip, row, labelSpec)
    local result, widgets = row.result, BigBiSList.Widgets
    local lines = widgets:SwapExplanationLines(result, nil, true) or {}
    local summary = widgets:SwapDecisionSummary(row.item, result)
    local effects = BigBiSList.ForeverGearRating:EffectComparisonLines(result, true) or {}
    if labelSpec and (#lines > 0 or #effects > 0) then tooltip:AddLine(row.spec, 0.93, 0.93, 0.96, true) end
    if summary then
        for _, line in ipairs(lines) do if line == summary then summary = nil; break end end
        if summary then tooltip:AddLine(summary, 0.88, 0.89, 0.91, true) end
    end
    for _, line in ipairs(lines) do tooltip:AddLine(line, 0.83, 0.85, 0.88, true) end
    for _, line in ipairs(effects) do tooltip:AddLine(line, 0.76, 0.8, 0.86, true) end
end

local function renderSpecBlocks(tooltip, statBlock, matches, selection, expanded, explanations)
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
    if not expanded then
        for _, row in ipairs(blocks) do
            local decision, tone, summary = compactSpecLine(row)
            local r, g, b = BigBiSList.Widgets:GearAdviceColor(tone)
            local spec = row.class == selection.class and row.spec or row.class .. " " .. row.spec
            if decision then tooltip:AddLine(spec .. " — " .. decision, r, g, b, true) end
            if summary then tooltip:AddLine(summary, 0.88, 0.89, 0.91, true) end
        end
        return
    end
    for _, row in ipairs(blocks) do
        tooltip:AddLine(" ")
        local spec = row.class == selection.class and row.spec or (row.class .. " " .. row.spec)
        local result = row.result
        local r, g, b = 0.93, 0.93, 0.96
        local tier = result and result.placement.tier
        if row.view and row.view.grade and row.view.grade > 0 then
            r, g, b = BigBiSList.Widgets:GetRankColor(row.view.grade)
        elseif tier and (not row.view or result.placement.phase == "PR") then
            r, g, b = BigBiSList.Widgets:GetRankColor(tier.quality)
        end
        if result and result.bis then
            local title = result.placement.phase == "PR" and "Pre-Raid BiS" or "BiS"
            spec = colorText(title, unpack(BigBiSList.Widgets.Theme.bisGold)) .. "  " .. spec
        end
        tooltip:AddLine(spec, r, g, b, true)
        if result then
            local comparison = row.assessment or row
            if row.view then
                local view = row.view
                if result.placement.phase == "PR" then
                    view.rank = tooltipRank(result)
                    view.strength = view.rank
                end
                BigBiSList.Widgets:AddGearAdviceLines(tooltip, BigBiSList.ForeverGearRating, view)
                if result.placement.phase == "PR" then placementColor = result.placement.placement_color or placementColor end
                if comparison.guaranteed then tooltip:AddLine("Compared with guaranteed rewards", 0.76, 0.8, 0.86, true) end
                if result.bank or (result.forecast and result.forecast.bank) then
                    tooltip:AddLine("Includes cached bank gear", 0.76, 0.8, 0.86, true)
                end
                local setup = (result.forecast or result).weaponSetup
                if setup then
                    local names = {}
                    for _, piece in ipairs(setup) do
                        names[#names + 1] = piece.name .. (piece.state == "bank" and " (bank)" or "")
                    end
                    tooltip:AddLine("Best owned setup · " .. table.concat(names, " + "), 0.83, 0.85, 0.88, true)
                end
            else
                local rank = tooltipRank(result)
                if result.placement.conditional and not result.placement.conditional_tie then rank = rank .. " · Conditional" end
                tooltip:AddLine(rank, r, g, b, true)
                if result.conditional then tooltip:AddLine("Some item effects have an unverified value", 0.86, 0.88, 0.91, true) end
                placementColor = placementColor or result.placement.placement_color
            end
            if comparison.bestChoice and not (row.view and row.view.action and row.view.action:find("Choose this reward", 1, true)) then
                tooltip:AddLine("Best choice for " .. row.spec, 0.86, 0.88, 0.91, true)
            elseif comparison.tiedChoice then
                tooltip:AddLine("Tied for best choice", 0.86, 0.88, 0.91, true)
            end
            if comparison.futureBiS then tooltip:AddLine("Pre-Raid Guide BiS", 0.86, 0.88, 0.91, true) end
            if BigBiSList.ForeverGearRating:SwapExplanationPending(result, true) then
                explanations[#explanations + 1] = row
            else addSwapExplanation(tooltip, row) end
            if result.effectNote then tooltip:AddLine(result.effectNote, 0.76, 0.8, 0.86, true) end
            if result.effectBreakEven then
                local estimate = string.format("%.1f full extra swings per minute to close the gap at tooltip weapon damage",
                    result.effectBreakEven)
                tooltip:AddLine(estimate, 0.76, 0.8, 0.86, true)
            end
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

local function tooltipStillMatches(tooltip, state)
    if not shouldAnnotateTooltip(tooltip) or not state or tooltip.__bigBisListState ~= state
        or tooltip.__bigBisListRefreshing then return end
    if tooltip.IsShown and not tooltip:IsShown() then return end
    local owner = readable(call(tooltip.GetOwner, tooltip))
    local info = primaryInfo(tooltip)
    local itemId = itemIdFromTooltip(tooltip)
    if owner ~= state.owner or itemId ~= state.itemId
        or itemLinkFromTooltip(tooltip, nil, itemId, info) ~= state.link then return end
    if state.bag ~= nil then
        local args = info and readable(info.getterArgs)
        if not args or readable(info.getterName) ~= "GetBagItem" or readable(args[1]) ~= state.bag
            or readable(args[2]) ~= state.bagSlot then return end
    end
    local highlights = BigBiSList.AcquisitionHighlights
    if highlights and (state.bag ~= nil or state.storageOffer)
        and not highlights:IsStorageTooltipCurrent(owner, itemId, state.link, info and readable(info.getterName),
            info and readable(info.getterArgs)) then return end
    return true, owner, info
end

local function rebuildTooltip(tooltip, state)
    local matches, owner, info = tooltipStillMatches(tooltip, state)
    if not matches then return end
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
    local expanded = (BigBiSList.isForever and settings.compact == false) or not not (IsAltKeyDown and IsAltKeyDown())
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

local function prepareItemTooltip(self, tooltip, itemId, itemLink, owner, info, settings, tooltipData, deadline)
    local offer, mark
    if self.AcquisitionHighlights then offer, mark = self.AcquisitionHighlights:GetTooltipOffer(owner, itemId, itemLink) end
    local live, statBlock
    local showExpanded = self.isForever and settings.compact == false or (settings.showAllOnAlt and IsAltKeyDown and IsAltKeyDown())
    local comparisonContext = comparisonTooltipContext(tooltip)
    local row = owner and (owner.detailData or owner.gearData)
    local rowVerdict = row and row.item_id == itemId and (row.targetVerdict or row.stat_swap or row.gearSwap)
    if self.ForeverGearRating and itemLink and self.UI and self.UI.GetOwnedSnapshot and not comparisonContext and not rowVerdict then
        live = self:GetTooltipPlayerContext()
        if live and addonTooltip(tooltip) and self.UI:GetSelection().class ~= live.class then live = nil end
        local exactLink = offer and offer.owned and offer.link or itemLink
        local candidate = live and self.ForeverGearRating:GetTooltipItem(itemId, exactLink)
        if candidate then statBlock = tooltipStatBlock(self, candidate, live, info, offer, tooltip, tooltipData, deadline, not showExpanded) else live = nil end
    end
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

    local groupedMatches = {}
    local first = statBlock and statBlock.rows[1]
    local rawMatches
    if levelingMode and first and first.summary and first.summary.packed then
        rawMatches = {}
    else
        rawMatches = levelingMode
            and self:GetLevelingTooltipMatches(itemId, selection.class, selection.spec, selectedLevel, selectedSpecFirst, specFilters, priorityContext, itemLink)
            or self:GetTooltipMatches(itemId, selection.class, selection.spec, selectedSpecFirst, specFilters, priorityContext)
    end
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
        expanded = not not showExpanded, stats = statBlock ~= nil, storageOffer = offer and offer.owned,
        pending = statBlock and statBlock.pending or {} }
    local info = primaryInfo(tooltip)
    local args = info and readable(info.getterArgs)
    if info and readable(info.getterName) == "GetBagItem" and type(args) == "table" then
        tooltip.__bigBisListState.bag, tooltip.__bigBisListState.bagSlot = readable(args[1]), readable(args[2])
    end

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

    local explanations = {}
    if self.isForever then
        renderSpecBlocks(tooltip, statBlock, matches, selection, showExpanded, explanations)
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
        tooltip:AddLine(statBlock and "Hold Alt for spec details and scores" or "Hold Alt for all rankings", 0.62, 0.66, 0.72)
    end
    if statBlock then
        self.UI:QueueStatLoads(statBlock.pending)
        local state = tooltip.__bigBisListState
        local rating = self.ForeverGearRating
        local finish = statBlock.finishSpecs
        local pending = #explanations > 0
        local first = statBlock.rows[1]
        local activeFirst = not showExpanded and first and first.activeSpec and rating:SwapExplanationPending(first.result)
        pending = pending or activeFirst
        local function waitingForRanges()
            for _, row in ipairs(statBlock.rows) do
                if row.summary and not row.summary.packed and not row.summary.slots[row.summarySlot] then return true end
            end
            return false
        end
        if finish or pending then
            local revision = self.ForeverScoring.revision
            local ownership = self.UI.domainVersions and self.UI.domainVersions.ownership
            local function current()
                return tooltip.__bigBisListState == state and tooltip:IsShown() and self:GetTooltipPlayerContext() == live
                    and revision == self.ForeverScoring.revision
                    and ownership == (self.UI.domainVersions and self.UI.domainVersions.ownership)
            end
            rating:QueueWork(0, function(checkpoint)
                -- Publish the active reason on this hover before starting the
                -- secondary specs. The native rebuild resumes the same block.
                if activeFirst then rating:GetSwapExplanation(first.result); return end
                if finish then
                    finish(checkpoint)
                    statBlock.finishSpecs = nil
                end
                if showExpanded then
                    for _, row in ipairs(statBlock.rows) do
                        checkpoint()
                        rating:GetSwapExplanation(row.result)
                        rating:EffectComparisonLines(row.result)
                    end
                end
            end, current, function()
                if current() then
                    -- A core-only tooltip will rebuild for the level ranges.
                    -- Supply the expanded evidence while that work finishes.
                    if showExpanded and not finish and waitingForRanges() then
                        if not tooltipStillMatches(tooltip, state) then return end
                        for _, row in ipairs(explanations) do
                            addSwapExplanation(tooltip, row, #statBlock.rows > 1)
                        end
                        tooltip:Show()
                        return
                    end
                    tooltip.__bigBisPrepared = {state = state, result = prepared}
                    rebuildTooltip(tooltip, state)
                    tooltip.__bigBisPrepared = nil
                end
            end)
        end
        local function rangesReady()
            if waitingForRanges() then return end
            rebuildTooltip(tooltip, state)
        end
        for _, row in ipairs(statBlock.rows) do
            if row.summary then
                self.ForeverGearRating:RequestLevelingSummary(row.summary, { row.summarySlot }, {
                    owner = tooltip,
                    isCurrent = function()
                        return tooltip.__bigBisListState == state and (not tooltip.IsShown or tooltip:IsShown())
                            and self:GetTooltipPlayerContext() == live
                    end,
                    onReady = rangesReady,
                })
            end
        end
    end
end

function BigBiSList:AddTooltipInfo(tooltip, tooltipData)
    if not shouldAnnotateTooltip(tooltip) or tooltip.__bigBisListState then return end
    local start = debugprofilestop and debugprofilestop()
    local database = self:EnsureDatabase() or (not self.isForever and BigBiSListDB)
    local settings = database and database.profile and database.profile.tooltips
    if not settings or settings.enabled == false then return end
    local itemId = itemIdFromTooltip(tooltip, tooltipData)
    if not itemId then return end
    local info = primaryInfo(tooltip)
    if info and readable(info.append) then return end
    local itemLink = itemLinkFromTooltip(tooltip, tooltipData, itemId, info)
    local owner = readable(call(tooltip.GetOwner, tooltip))
    local ready = tooltip.__bigBisPrepared
    if ready and ready.state.itemId == itemId and ready.state.link == itemLink and ready.state.owner == owner then
        showItemTooltip(self, tooltip, itemId, itemLink, owner, settings, ready.result)
        return
    end
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
    local deadline = start and C_Timer and C_Timer.After and start + 1
    local prepared = prepareItemTooltip(self, tooltip, itemId, itemLink, owner, info, settings, tooltipData, deadline)
    if prepared then showItemTooltip(self, tooltip, itemId, itemLink, owner, settings, prepared) end
    if start and self.UI and self.UI.RecordAddonTime then self.UI:RecordAddonTime("tooltip", debugprofilestop() - start) end
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
