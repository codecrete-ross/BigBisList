local addon = BigBiSList
local rating, ui, widgets = addon.ForeverGearRating, addon.UI, addon.Widgets
local highlights = {
    settings = {
        { "quest", "Quest rewards" }, { "vendor", "Vendors" }, { "loot", "Loot windows" },
        { "roll", "Group loot rolls" }, { "auction", "Auction House" }, { "trade", "Incoming trades" },
        { "mail", "Mail attachments" }, { "crafting", "Crafting outputs" },
        { "bags", "Gear in bags" }, { "bank", "Gear in your bank" }, { "animate", "Animate gear highlights" },
    },
}
addon.AcquisitionHighlights = highlights

local marks = {}
local offers = {}
local overlays = setmetatable({}, { __mode = "k" })
local watchedFrames = setmetatable({}, { __mode = "k" })
local watchedScrollBoxes = setmetatable({}, { __mode = "k" })
local rollCards = setmetatable({}, { __mode = "k" })
local storagePanels = setmetatable({}, { __mode = "k" })
local baganatorItems = setmetatable({}, { __mode = "k" })
local baganatorCache = {}
local BAGANATOR_WIDGET_ID = "big_bis_list"
local lootSlotsCleared = {}
local hooked = {}
local NEUTRAL = { 0.72, 0.77, 0.84 }
local GOLD_COIN = "Interface\\MoneyFrame\\UI-GoldIcon"

local function checked(ok, ...)
    if ok then return ... end
end

local function call(api, ...)
    if type(api) == "function" then return checked(pcall(api, ...)) end
end

local function read(value, wantedType)
    if addon.IsReadableValue(value) and type(value) == wantedType then return value end
end

local function shown(frame)
    return frame and read(call(frame.IsVisible or frame.IsShown, frame), "boolean") == true
        and read(call(frame.IsForbidden, frame), "boolean") ~= true
end

local function itemIdFromLink(link)
    return link and tonumber(link:match("item:(%d+)"))
end

local function getInfoLink(data)
    if not read(data, "table") then return end
    local link = read(data.hyperlink, "string")
    if not link and read(data.guid, "string") then
        link = read(call(C_Item and C_Item.GetItemLinkByGUID, data.guid), "string")
    end
    return link, read(data.id, "number")
end

local function clearMark(row, forget, quiet)
    local overlay = overlays[row]
    if overlay and overlay.managed and marks[row] and not quiet then highlights.baganatorDirty = true end
    if offers[row] or marks[row] then highlights.tooltipDirty = true end
    offers[row] = nil
    marks[row] = nil
    if not overlay then return end
    if forget then overlay.visualKey = nil end
    if overlay.managed then return end
    if overlay.animation and overlay.animation:IsPlaying() then overlay.animation:Stop() end
    overlay:Hide()
end

local function clearKind(kind, forget, sourceId)
    for row, entry in pairs(offers) do
        if entry.kind == kind and (sourceId == nil or entry.sourceId == sourceId) then clearMark(row, forget) end
    end
end

local function watchFrame(frame, kind)
    if not frame or not frame.HookScript or watchedFrames[frame] then return end
    watchedFrames[frame] = true
    frame:HookScript("OnShow", function() highlights:ScheduleRefresh() end)
    frame:HookScript("OnHide", function() clearKind(kind, true); highlights:ScheduleRefresh() end)
end

local function watchScrollBox(scrollBox)
    if not scrollBox or not ScrollUtil or watchedScrollBoxes[scrollBox] then return end
    if not ScrollUtil.AddInitializedFrameCallback or not ScrollUtil.AddReleasedFrameCallback then return end
    watchedScrollBoxes[scrollBox] = true
    local function onReuse(_, frame)
        clearMark(frame, true)
        highlights:ScheduleRefresh()
    end
    ScrollUtil.AddInitializedFrameCallback(scrollBox, onReuse, highlights)
    ScrollUtil.AddReleasedFrameCallback(scrollBox, function(owner, frame)
        rollCards[frame] = nil
        onReuse(owner, frame)
    end, highlights)
end

local function addItem(items, entry, link, id)
    entry.link = read(link, "string")
    entry.itemId = itemIdFromLink(entry.link) or read(id, "number")
    if entry.itemId and entry.itemId <= 0 then entry.itemId = nil end
    if not itemIdFromLink(entry.link) then entry.link = nil end
    entry.compareWorn = entry.owned or entry.kind == "quest" or entry.kind == "loot"
    if entry.link or entry.kind == "quest" or entry.itemId then items[#items + 1] = entry end
end

local function questRewardInfo(questLog, kind, index)
    if not questLog then return call(GetQuestItemInfo, kind, index) end
    local getter = kind == "choice" and GetQuestLogChoiceInfo or GetQuestLogRewardInfo
    return call(getter, index)
end

local function collectQuest(items)
    local info = QuestInfoFrame
    local panel = info and info.rewardsFrame
    watchFrame(panel, "quest")
    if not shown(panel) then return end
    local questLog = read(info.questLog, "boolean") == true
    local questId = questLog and call(C_QuestLog and C_QuestLog.GetSelectedQuest) or call(GetQuestID)
    local getLink = questLog and GetQuestLogItemLink or GetQuestItemLink
    for _, row in ipairs(panel.RewardButtons or {}) do
        local kind = read(row.type, "string")
        if shown(row) and read(row.objectType, "string") == "item" and (kind == "choice" or kind == "reward") then
            local index = read(call(row.GetID, row), "number")
            if index and index > 0 then
                local _, _, quantity, _, _, id = questRewardInfo(questLog, kind, index)
                local source = tostring(read(row.questID, "number") or read(questId, "number") or "") .. ":" .. kind .. ":" .. index
                local selected = kind == "choice" and (call(QuestInfoItem_IsSelected, row) == true)
                addItem(items, { kind = "quest", row = row, icon = row.Icon, sourceId = source,
                    group = kind, order = index, selected = selected,
                    quantity = read(quantity, "number") }, call(getLink, kind, index), id)
            end
        end
    end
end

local function collectVendor(items)
    local panel = MerchantFrame
    watchFrame(panel, "vendor")
    if not shown(panel) or read(panel.selectedTab, "number") ~= 1 then return end
    for index = 1, read(MERCHANT_ITEMS_PER_PAGE, "number") or 0 do
        local row = _G["MerchantItem" .. index .. "ItemButton"]
        if shown(row) and read(row.hasItem, "boolean") == true then
            local id = read(call(row.GetID, row), "number")
            local info = id and read(call(C_MerchantFrame and C_MerchantFrame.GetItemInfo, id), "table")
            if info and read(info.isPurchasable, "boolean") == true and read(info.numAvailable, "number") ~= 0
                and read(info.isUsable, "boolean") ~= false and not read(info.currencyID, "number") then
                addItem(items, { kind = "vendor", row = row, sourceId = id }, call(GetMerchantItemLink, id), info.itemID)
            end
        end
    end
end

local function collectLoot(items)
    local panel = LootFrame
    watchFrame(panel, "loot")
    if not shown(panel) then return end
    local box = panel.ScrollBox
    watchScrollBox(box)
    if not (box and box.ForEachFrame and Enum and Enum.LootSlotType) then return end
    box:ForEachFrame(function(row)
        local slot = shown(row) and read(call(row.GetSlotIndex, row), "number")
        if slot and slot > 0 and not lootSlotsCleared[slot]
            and read(call(GetLootSlotType, slot), "number") == Enum.LootSlotType.Item then
            local _, _, _, _, _, locked = call(GetLootSlotInfo, slot)
            if addon.IsReadableValue(locked) and not locked then
                addItem(items, { kind = "loot", row = row, icon = row.Item, sourceId = slot }, call(GetLootSlotLink, slot))
            end
        end
    end)
end

local function collectRolls(items)
    watchFrame(GroupLootContainer, "roll")
    watchFrame(GamepadGroupLootRollFrame, "roll")
    watchScrollBox(GamepadGroupLootRollFrame and GamepadGroupLootRollFrame.ScrollBox)
    local active = read(call(GetActiveLootRollIDs), "table")
    local byId = {}
    for _, value in ipairs(active or {}) do
        local id = read(value, "number")
        if id then byId[id] = true end
    end
    for row in pairs(rollCards) do
        local id = shown(row) and read(row.rollID, "number")
        local remaining = id and read(call(GetLootRollTimeLeft, id), "number")
        local available = read(row.canNeed, "boolean") == true or read(row.canGreed, "boolean") == true
            or read(row.canTransmog, "boolean") == true
        if remaining and remaining > 0 and available and (not active or byId[id]) then
            local link = read(call(GetLootRollItemLink, id), "string")
            local itemId
            if not itemIdFromLink(link) then
                link, itemId = getInfoLink(call(C_TooltipInfo and C_TooltipInfo.GetLootRollItem, id))
            end
            addItem(items, { kind = "roll", row = row, icon = row.IconFrame, sourceId = id }, link, itemId)
        end
    end
end

local function collectAuctions(items)
    local panel = AuctionHouseFrame and AuctionHouseFrame.ItemBuyFrame
    watchFrame(panel, "auction")
    if not shown(panel) then return end
    local box = panel.ItemList and panel.ItemList.ScrollBox
    watchScrollBox(box)
    if not (box and box.ForEachFrame) then return end
    box:ForEachFrame(function(row)
        local data = shown(row) and read(row.rowData, "table")
        local id = data and read(data.auctionID, "number")
        if id and id > 0 and read(data.containsOwnerItem, "boolean") == false then
            addItem(items, { kind = "auction", row = row, sourceId = id }, data.itemLink)
        end
    end)
end

local function collectTrade(items)
    watchFrame(TradeFrame, "trade")
    if not shown(TradeFrame) then return end
    for index = 1, (read(TRADE_ENCHANT_SLOT, "number") or 7) - 1 do
        local row = _G["TradeRecipientItem" .. index .. "ItemButton"]
        if shown(row) then
            local link = call(GetTradeTargetItemLink, index)
            addItem(items, { kind = "trade", row = row, sourceId = index }, link)
        end
    end
end

local function collectMail(items)
    local panel = OpenMailFrame
    watchFrame(panel, "mail")
    local id = shown(panel) and InboxFrame and read(InboxFrame.openMailID, "number")
    if not id or id < 1 then return end
    for index, row in ipairs(panel.OpenMailAttachments or {}) do
        if shown(row) then
            local link = read(call(GetInboxItemLink, id, index), "string")
            local itemId
            if not itemIdFromLink(link) then
                link, itemId = getInfoLink(call(C_TooltipInfo and C_TooltipInfo.GetInboxItem, id, index))
            end
            addItem(items, { kind = "mail", row = row, sourceId = id .. ":" .. index }, link, itemId)
        end
    end
end

local function craftingForm()
    local page = ProfessionsFrame and ProfessionsFrame.CraftingPage
    return page and page.SchematicForm
end

local function collectCrafting(items)
    local form = craftingForm()
    watchFrame(form, "crafting")
    if not (shown(form) and shown(form.OutputIcon) and C_TradeSkillUI and form.transaction) then return end
    local transaction = form.transaction
    local id = read(call(transaction.GetRecipeID, transaction), "number")
    local info = id and read(call(C_TradeSkillUI.GetRecipeInfo, id), "table")
    local schematic = read(form.recipeSchematic, "table")
    if not info or read(info.learned, "boolean") ~= true or not schematic
        or read(schematic.isRecraft, "boolean") == true or read(info.supportsQualities, "boolean") == true
        or read(schematic.hasCraftingOperationInfo, "boolean") == true or read(form.isInspection, "boolean") == true
        or read(call(C_TradeSkillUI.IsTradeSkillLinked), "boolean") == true then return end
    local reagents = read(call(transaction.CreateCraftingReagentInfoTbl, transaction), "table")
    local allocatedItem = call(transaction.GetAllocationItemGUID, transaction)
    if not reagents or not addon.IsReadableValue(allocatedItem) or allocatedItem then return end
    local link = getInfoLink(call(C_TradeSkillUI.GetRecipeOutputItemData, id, reagents))
    local itemId = itemIdFromLink(link)
    if itemId then
        addItem(items, { kind = "crafting", row = form.OutputIcon, sourceId = id }, link)
    end
end

local function storageLink(bag, slot)
    return read(call(C_Container and C_Container.GetContainerItemLink or GetContainerItemLink, bag, slot), "string")
end

local function storagePosition(row, kind)
    if kind == "bank" then
        return read(call(row.GetBankTabID, row), "number"), read(call(row.GetContainerSlotID, row), "number")
    end
    return read(call(row.GetBagID, row), "number"), read(call(row.GetID, row), "number")
end

local function storageContextMatches(entry)
    return entry.ownedSnapshot == ui.currentOwned and entry.player == addon:GetTooltipPlayerContext()
        and entry.revision == (addon.ForeverScoring and addon.ForeverScoring.revision)
end

local function storageGUIDMatches(first, second)
    return not first or not second or first == second
end

local function storageBindingMatches(entry, bag, slot)
    if not bag or not slot or entry.sourceId ~= bag .. ":" .. slot or not storageContextMatches(entry) then return false end
    if entry.kind == "bank" and not ui.personalBankOpen then return false end
    return rating:SameExactItemLink(entry.itemId, entry.link, storageLink(bag, slot))
        and storageGUIDMatches(entry.guid, entry.guid and ui:GetStorageItemGUID(bag, slot))
end

local function watchStoragePanel(panel, kind)
    if not panel or not panel.HookScript or storagePanels[panel] then return end
    storagePanels[panel] = true
    local function refreshBindings()
        local bankType = Enum and Enum.BankType and Enum.BankType.Character
        local validPanel = kind ~= "bank" or (bankType ~= nil and call(panel.GetActiveBankType, panel) == bankType)
        for row, entry in pairs(offers) do
            if entry.kind == kind and not entry.widget and shown(row) then
                local bag, slot = storagePosition(row, kind)
                if not validPanel or not storageBindingMatches(entry, bag, slot) then
                    clearMark(row, true)
                end
            end
        end
        highlights:ScheduleRefresh()
    end
    panel:HookScript("OnShow", refreshBindings)
    for _, method in ipairs({ "UpdateItems", "GenerateItemSlotsForSelectedTab", "RefreshAllItemsForSelectedTab" }) do
        if type(panel[method]) == "function" then
            hooksecurefunc(panel, method, refreshBindings)
        end
    end
end

local function collectStorage(items, settings)
    local bankTabs = {}
    local bankType = Enum and Enum.BankType and Enum.BankType.Character
    if bankType ~= nil then
        for _, tab in ipairs(read(call(C_Bank and C_Bank.FetchPurchasedBankTabIDs, bankType), "table") or {}) do
            if read(tab, "number") then bankTabs[tab] = true end
        end
    end
    local lastBag = read(NUM_TOTAL_BAG_FRAMES, "number") or read(NUM_BAG_SLOTS, "number") or 4
    local function add(row, bag, slot, expectedLink, widget, expectedGUID)
        if not shown(row) or not bag or not slot or slot < 1 then return end
        local kind = bankTabs[bag] and "bank" or (bag >= 0 and bag <= lastBag and "bags")
        if not kind or settings[kind] == false then return end
        if kind == "bank" and not ui.personalBankOpen then return end
        local link = storageLink(bag, slot)
        if not link or (expectedLink and not rating:SameExactItemLink(itemIdFromLink(link), link, expectedLink)) then return end
        local guid = ui:GetStorageItemGUID(bag, slot)
        if not storageGUIDMatches(guid, expectedGUID) then return end
        addItem(items, { kind = kind, row = row, sourceId = bag .. ":" .. slot,
            guid = guid or expectedGUID, owned = true, widget = widget }, link)
    end
    if type(ContainerFrameUtil_EnumerateContainerFrames) == "function" then
        for _, panel in ContainerFrameUtil_EnumerateContainerFrames() do
            watchStoragePanel(panel, "bags")
            if shown(panel) and panel.EnumerateValidItems then
                for _, row in panel:EnumerateValidItems() do
                    local bag, slot = storagePosition(row, "bags")
                    add(row, bag, slot)
                end
            end
        end
    end
    local panel = BankFrame and BankFrame.BankPanel or BankPanel
    watchStoragePanel(panel, "bank")
    if shown(panel) and bankType ~= nil and call(panel.GetActiveBankType, panel) == bankType and panel.EnumerateValidItems then
        for row in panel:EnumerateValidItems() do
            local bag, slot = storagePosition(row, "bank")
            add(row, bag, slot)
        end
    end
    local api = Baganator and Baganator.API
    local active = api and call(api.IsCornerWidgetActive, BAGANATOR_WIDGET_ID) ~= false
    for row, entry in pairs(baganatorItems) do
        entry.active = active
        if active then
            local location = read(entry.details.itemLocation, "table")
            if location and row.BGR == entry.details then
                local bag, slot = read(location.bagID, "number"), read(location.slotIndex, "number")
                add(row, bag, slot, read(entry.details.itemLink, "string"), entry.widget, read(entry.details.guid, "string"))
            end
        end
    end
end

local collectors = { quest = collectQuest, vendor = collectVendor, loot = collectLoot, roll = collectRolls,
    auction = collectAuctions, trade = collectTrade, mail = collectMail, crafting = collectCrafting }

local function unresolved(result)
    return result.status == "loading" or result.status == "unavailable"
end

local function rewardItem(batch, entry)
    local id = entry.itemId
    if not entry.link then
        if id and not (rating.loadedItems and rating.loadedItems[id]) then batch.pending[id] = true end
        return nil, false
    end
    local item = batch.items[entry.link]
    if not item then
        local candidate, status = rating:GetTooltipItem(id, entry.link)
        item = { candidate = candidate, status = status }
        batch.items[entry.link] = item
    end
    local candidate, status = item.candidate, item.status
    if status == "loading" or (candidate and candidate.status == "loading") then batch.pending[id] = true end
    if not candidate then return nil, status == nil end
    if not candidate.facts then return nil, false end
    return candidate, true
end

local function assess(batch, entry, evaluation)
    local candidate, exact = rewardItem(batch, entry)
    if not candidate or not evaluation then return nil, exact and evaluation ~= nil end
    local id, spec, context = entry.itemId, evaluation.spec, evaluation.context
    if entry.kind == "crafting" and rating:IsUnresolvedVariant(id, candidate.key) then return nil, false end
    if context.owned.variantUnknownItems and context.owned.variantUnknownItems[id] then return nil, false end
    local quest = entry.kind == "quest"
    local worn = not quest and spec.role == "active" and entry.compareWorn
    local key = table.concat({ spec.name, context.scenario or "", tostring(worn), entry.link }, "\031")
    local cached = not quest and batch.swaps[key]
    if cached then return cached.mark, cached.ready, cached.assessment end

    local result = rating:CompareTooltipItem(context, candidate, worn, nil, true,
        { live = true, lookahead = quest, quantity = quest and entry.quantity or nil })
    local ready = not unresolved(result) and not unresolved(result.placement)
    local gain = rating:RoundedGain(result.delta) or 0
    local qualifies = not result.conditional and gain > 0
    local assessment = { spec = spec, scenario = context.scenario, result = result, gain = gain,
        ownedBaseline = not worn, guaranteed = evaluation.guaranteed }
    if quest then
        local slot = result.slot or result.placement.item and result.placement.item.slot
        if context.leveling and slot and addon.IsConfirmedGearBiS then
            local history = addon:GetRecommendationHistory(id, context.class, spec.name, "PR", slot)
            if addon:IsConfirmedGearBiS(history, "PR", id, candidate.key) then
                assessment.futureBiS = true
            end
        end
        local noteworthy = result.conditional or result.preview or result.bis
            or assessment.futureBiS or result.placement.status == "effect" or result.placement.status == "utility"
        return ready and (qualifies or noteworthy) and assessment or nil, ready, assessment
    end
    local mark
    if ready and (qualifies or result.bis) then
        local extraGain = gain
        if result.ownership and worn then
            local owned = rating:CompareTooltipItem(context, candidate, false, nil, true)
            ready = not unresolved(owned)
            extraGain = not owned.conditional and rating:RoundedGain(owned.delta) or 0
        end
        if ready and (not result.ownership or extraGain > 0) then
            mark = assessment
        end
    end
    batch.swaps[key] = { mark = mark, ready = ready, assessment = assessment }
    return mark, ready, assessment
end

local function exactMark(mark, entry)
    local copy = {}
    for key, value in pairs(mark) do copy[key] = value end
    copy.entry = entry
    return copy
end

local function rankOffers(batch, entry)
    local primary, ready, assessments = nil, #batch.contexts > 0, {}
    for _, evaluation in ipairs(batch.contexts) do
        local mark, resolved, assessment = assess(batch, entry, evaluation)
        ready = ready and resolved
        primary = primary or mark
        if assessment then assessments[#assessments + 1] = assessment end
    end
    if primary then
        primary = exactMark(primary, entry)
        primary.assessments = assessments
    end
    return primary, ready
end

local function rankStorage(batch, entry)
    local candidate, exact = rewardItem(batch, entry)
    if not candidate then return nil, exact end
    local primary, ready, assessments, signature = nil, #batch.contexts > 0, {}, {}
    for _, evaluation in ipairs(batch.contexts) do
        local context, spec = evaluation.context, evaluation.spec
        local comparison, resolved = rating:GetStorageComparison(context, candidate, entry.sourceId, entry.guid, evaluation.primary)
        ready = ready and resolved
        if comparison then
            local result = comparison.result
            local assessment = { spec = spec, scenario = context.scenario, result = result, storage = comparison,
                alternate = comparison.alternate }
            assessments[#assessments + 1] = assessment
            if resolved and comparison.qualifies then primary = primary or assessment end
            signature[#signature + 1] = table.concat({ spec.name, context.scenario, tostring(result.delta),
                tostring(result.conditional), tostring(result.placement.rank), tostring(result.placement.total),
                tostring(comparison.qualifies), tostring(comparison.alternate), tostring(comparison.sidegrade),
                tostring(comparison.unavailable) }, "\031")
            for _, item in ipairs(comparison.stronger or {}) do
                signature[#signature + 1] = item.name .. "\031" .. tostring(item.state)
            end
        end
    end
    entry.assessments, entry.assessmentKey = assessments, table.concat(signature, "\030")
    return primary and exactMark(primary, entry), ready
end

local function rankRewards(batch, rewards, evaluation, rows, ready, allowBest)
    local bestGain, best = 0, {}
    for _, entry in ipairs(rewards) do
        local mark, resolved, assessment = assess(batch, entry, evaluation)
        if assessment then
            rows[entry.row][#rows[entry.row] + 1] = assessment
            if not ready then assessment.result = setmetatable({ conditional = true }, { __index = assessment.result }) end
        end
        if mark then
            mark.show = true
            local result = mark.result
            if result.conditional or result.preview or result.placement.status == "effect"
                or result.placement.status == "utility" then resolved = false end
            if not result.conditional and mark.gain > 0 then
                if mark.gain > bestGain then bestGain, best = mark.gain, {} end
                if mark.gain == bestGain then best[#best + 1] = mark end
            end
        end
        if not resolved then evaluation.unresolved = true end
    end
    if allowBest and ready and not evaluation.unresolved then
        for _, mark in ipairs(best) do mark.bestChoice = #best == 1; mark.tiedChoice = #best > 1 end
    end
end

local function highestSellValue(batch, entries)
    local best
    for _, entry in ipairs(entries) do
        local getter = C_Item and C_Item.GetItemInfo or GetItemInfo
        local price = read(select(11, call(getter, entry.link)), "number")
        if not price or not entry.quantity or entry.quantity < 1 then
            local id = entry.itemId
            if not price and id and not (rating.loadedItems and rating.loadedItems[id]) then batch.pending[id] = true end
            return nil
        end
        local value = price * entry.quantity
        if value > 0 and (not best or value > best.sellValue) then best = { entry = entry, sellValue = value } end
    end
    return best
end

local function recordMark(mark, visualKey, immediate)
    local entry, result = mark.entry, mark.result
    local row = entry.row
    local previous = marks[row]
    if entry.widget and not immediate and (not previous or previous.visualKey ~= visualKey) then highlights.baganatorDirty = true end
    local placement = result and result.placement or {}
    local textKey = table.concat({ visualKey, tostring(mark.sellValue), tostring(mark.bestChoice),
        tostring(result and result.delta), tostring(result and result.bank), tostring(placement.rank), tostring(placement.total),
        tostring(placement.score_percent), tostring(placement.placement_color), mark.spec and mark.spec.name or "" }, "\031")
    textKey = textKey .. (entry.assessmentKey or "")
    if not previous or previous.textKey ~= textKey then highlights.tooltipDirty = true end
    mark.visualKey, mark.textKey = visualKey, textKey
    marks[row] = mark
end

local function newStorageBadge(row)
    local badge = CreateFrame("Frame", nil, row)
    badge:EnableMouse(false)
    badge:SetSize(20, 16)
    badge.background = badge:CreateTexture(nil, "BACKGROUND")
    badge.background:SetAllPoints()
    badge.icon = badge:CreateTexture(nil, "ARTWORK")
    badge.icon:SetSize(14, 14)
    badge.icon:SetPoint("CENTER")
    badge.bis = badge:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    badge.bis:SetAllPoints()
    badge.bis:SetJustifyH("CENTER")
    badge.bis:SetJustifyV("MIDDLE")
    badge.bis:SetText("BiS")
    badge.bis:SetTextColor(unpack(widgets.Theme.bisGold))
    badge.alternate = badge:CreateTexture(nil, "OVERLAY")
    badge.alternate:SetSize(3, 3)
    badge.alternate:SetPoint("BOTTOMRIGHT", badge, "BOTTOMRIGHT", -2, 2)
    badge.alternate:SetColorTexture(0.94, 0.94, 0.98, 1)
    badge.alternate:Hide()
    badge.border = {}
    for _, side in ipairs({ "TOP", "BOTTOM", "LEFT", "RIGHT" }) do
        local edge = badge:CreateTexture(nil, "OVERLAY")
        if side == "TOP" or side == "BOTTOM" then
            edge:SetPoint(side .. "LEFT")
            edge:SetPoint(side .. "RIGHT")
            edge:SetHeight(1)
        else
            edge:SetPoint("TOP" .. side)
            edge:SetPoint("BOTTOM" .. side)
            edge:SetWidth(1)
        end
        badge.border[#badge.border + 1] = edge
    end
    badge:Hide()
    return badge
end

local function displayStorage(mark, r, g, b, immediate)
    local entry, result = mark.entry, mark.result
    local badge = overlays[entry.row]
    if not badge then
        badge = newStorageBadge(entry.row)
        badge:SetPoint("TOPRIGHT", entry.row, "TOPRIGHT", -1, -1)
        badge:SetFrameLevel((entry.row:GetFrameLevel() or 0) + 3)
        overlays[entry.row] = badge
    end
    local bis = result.bis == true
    local icon = mark.spec and mark.spec.icon
    local alternate = mark.alternate == true
    if bis then r, g, b = unpack(widgets.Theme.bisGold) end
    local visualKey = table.concat({ entry.kind, entry.sourceId, tostring(icon), tostring(bis), tostring(alternate), r, g, b }, "\031")
    if badge.visualKey == visualKey then
        if not badge.managed then badge:Show() end
        recordMark(mark, visualKey, immediate)
        return
    end
    badge.visualKey = visualKey
    if icon then
        badge.icon:SetTexture(icon)
        badge.icon:SetVertexColor(1, 1, 1)
    else
        widgets:SetIcon(badge.icon, "sortAscending")
        badge.icon:SetVertexColor(r, g, b)
    end
    badge.icon:SetShown(not bis)
    badge.bis:SetShown(bis)
    badge.alternate:SetShown(alternate)
    if bis then
        badge.background:SetColorTexture(r * 0.15, g * 0.15, b * 0.15, 0.95)
    else
        badge.background:SetColorTexture(0.05, 0.05, 0.06, 0.9)
    end
    for _, edge in ipairs(badge.border) do edge:SetColorTexture(r, g, b, 1) end
    if not badge.managed then badge:Show() end
    recordMark(mark, visualKey, immediate)
end

local function newOverlay(row)
    local overlay = CreateFrame("Frame", nil, row)
    overlay:EnableMouse(false)
    overlay:SetAllPoints(row)
    local corner = CreateFrame("Frame", nil, overlay)
    corner:EnableMouse(false)
    corner:SetSize(15, 15)
    corner.background = corner:CreateTexture(nil, "BACKGROUND")
    corner.background:SetAllPoints()
    corner.background:SetColorTexture(0.05, 0.05, 0.06, 0.88)
    corner.accent = corner:CreateTexture(nil, "OVERLAY")
    corner.accent:SetPoint("BOTTOMLEFT")
    corner.accent:SetPoint("BOTTOMRIGHT")
    corner.accent:SetHeight(2)
    corner.symbol = corner:CreateTexture(nil, "ARTWORK")
    corner.symbol:SetPoint("TOPLEFT", 1, -1)
    corner.symbol:SetPoint("BOTTOMRIGHT", -1, 2)
    corner.arrow = corner:CreateTexture(nil, "OVERLAY")
    corner.arrow:SetAllPoints(corner.symbol)
    widgets:SetIcon(corner.arrow, "sortAscending")
    overlay.corner = corner

    overlay.glow = overlay:CreateTexture(nil, "ARTWORK")
    overlay.glow:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    overlay.glow:SetDesaturated(true)
    overlay.glow:SetBlendMode("ADD")
    overlay.glow:SetSize(29, 29)
    overlay.glow:SetPoint("CENTER", corner)
    overlay.bis = overlay:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    overlay.bis:SetPoint("TOPLEFT", corner, "BOTTOMLEFT", 0, -1)
    overlay.bis:SetText("BiS")
    overlay.bis:SetTextColor(unpack(widgets.Theme.bisGold))
    overlay.edges = {}
    for _, side in ipairs({ "TOP", "BOTTOM", "LEFT", "RIGHT" }) do
        local edge = overlay:CreateTexture(nil, "OVERLAY")
        if side == "TOP" or side == "BOTTOM" then
            local y = side == "TOP" and -1 or 1
            edge:SetPoint(side .. "LEFT", 1, y)
            edge:SetPoint(side .. "RIGHT", -1, y)
            edge:SetHeight(1)
        else
            local x = side == "LEFT" and 1 or -1
            edge:SetPoint("TOP" .. side, x, -1)
            edge:SetPoint("BOTTOM" .. side, x, 1)
            edge:SetWidth(1)
        end
        overlay.edges[#overlay.edges + 1] = edge
    end
    if corner.arrow.CreateAnimationGroup then
        local animation = corner.arrow:CreateAnimationGroup()
        local rise = animation:CreateAnimation("Translation")
        rise:SetOffset(0, 4)
        rise:SetDuration(0.45)
        local fade = animation:CreateAnimation("Alpha")
        fade:SetFromAlpha(1)
        fade:SetToAlpha(0)
        fade:SetDuration(0.45)
        animation:SetScript("OnFinished", function()
            corner.arrow:Hide()
            corner.symbol:Show()
        end)
        overlay.animation = animation
    end
    overlay:Hide()
    return overlay
end

local function display(mark, animate, immediate)
    local entry, result = mark.entry, mark.result
    local row, spec = entry.row, mark.spec
    local tier = result and result.placement and result.placement.tier
    local bis = result and result.bis == true and (entry.kind ~= "quest" or mark.bestChoice)
    local r, g, b = unpack(NEUTRAL)
    if tier then r, g, b = widgets:GetRankColor(tier.quality) end
    if entry.owned then displayStorage(mark, r, g, b, immediate); return end
    local overlay = overlays[row]
    if not overlay then overlay = newOverlay(row); overlays[row] = overlay end
    overlay:SetFrameLevel((row:GetFrameLevel() or 0) + 3)
    local corner = overlay.corner
    corner:ClearAllPoints()
    if entry.kind == "auction" then
        corner:SetPoint("LEFT", row, "LEFT", 0, 0)
    else
        corner:SetPoint("TOPLEFT", entry.icon or row, "TOPLEFT", 1, -1)
    end
    corner.accent:SetColorTexture(r, g, b, 1)
    corner.arrow:SetVertexColor(r, g, b)
    overlay.glow:SetVertexColor(r, g, b, 0.55)
    overlay.glow:SetShown(not mark.sellValue)
    overlay.bis:SetShown(bis)
    for _, edge in ipairs(overlay.edges) do
        edge:SetColorTexture(r, g, b, 0.95)
        edge:SetShown(mark.outline == true)
    end

    local icon = mark.sellValue and GOLD_COIN or spec and spec.icon
    local visualKey = table.concat({ entry.kind, entry.sourceId, entry.link, tostring(icon), tostring(bis),
        tostring(tier and tier.quality), tostring(mark.gain and mark.gain > 0), tostring(animate) }, "\031")
    local wasShown = overlay:IsShown()
    overlay:Show()
    if overlay.visualKey ~= visualKey or not wasShown then
        local fresh = overlay.visualKey ~= visualKey
        overlay.visualKey = visualKey
        if overlay.animation and overlay.animation:IsPlaying() then overlay.animation:Stop() end
        corner.symbol:SetTexture(icon)
        corner.symbol:SetShown(icon ~= nil)
        corner.arrow:SetShown(not icon and (mark.gain or 0) > 0)
        if fresh and icon and (mark.gain or 0) > 0 and animate and overlay.animation then
            corner.arrow:Show()
            corner.symbol:Hide()
            overlay.animation:Play()
        end
    end
    recordMark(mark, visualKey)
end

local function refresh()
    local settings = addon:GetAccountDB().profile.gearHighlights
    local items, results, currentOffers = {}, {}, {}
    for _, setting in ipairs(highlights.settings) do
        local kind = setting[1]
        local collect = collectors[kind]
        if collect and settings[kind] ~= false then collect(items) end
    end
    collectStorage(items, settings)
    if #items > 0 then
        local player = addon:GetTooltipPlayerContext()
        local batch = { contexts = {}, items = {}, swaps = {}, pending = {}, player = player }
        if player and player.spec then
            local owned = ui:GetOwnedSnapshot()
            batch.owned = owned
            for _, spec in ipairs(player.specs) do
                if spec.role == "active" or spec.role == "dual" then
                    local contexts = rating:GetScenarioContexts(player.class, spec.name, player.phase, player.level, owned)
                    for index, context in ipairs(contexts) do
                        batch.contexts[#batch.contexts + 1] = { spec = spec, context = context, primary = index > 1 and contexts[1] or nil }
                        for id in pairs(context.pending) do batch.pending[id] = true end
                    end
                end
            end
        end

        local rewards = { choice = {}, reward = {} }
        for _, entry in ipairs(items) do
            if entry.link then
                local previous = offers[entry.row]
                if not previous or previous.link ~= entry.link or previous.sourceId ~= entry.sourceId
                    or previous.kind ~= entry.kind then highlights.tooltipDirty = true end
                currentOffers[entry.row] = entry
            end
            if entry.group then
                local group = rewards[entry.group]
                group[#group + 1] = entry
            elseif entry.owned then
                entry.player, entry.ownedSnapshot = batch.player, batch.owned
                entry.revision = addon.ForeverScoring and addon.ForeverScoring.revision
                local mark, ready = rankStorage(batch, entry)
                local previous = offers[entry.row]
                if not previous or previous.assessmentKey ~= entry.assessmentKey then highlights.tooltipDirty = true end
                if entry.widget then
                    baganatorCache[entry.sourceId] = ready and { kind = entry.kind, link = entry.link, guid = entry.guid,
                        mark = mark, assessments = entry.assessments, assessmentKey = entry.assessmentKey,
                        player = entry.player, ownedSnapshot = entry.ownedSnapshot, revision = entry.revision } or nil
                end
                if mark then results[entry.row] = mark end
            else
                local mark = rankOffers(batch, entry)
                if mark then entry.assessments, results[entry.row] = mark.assessments, mark end
            end
        end
        local guaranteed, fixedReady, selected = {}, true, false
        for _, entry in ipairs(rewards.reward) do
            local candidate, ready = rewardItem(batch, entry)
            if candidate and entry.quantity and entry.quantity >= 1 then
                guaranteed[#guaranteed + 1] = { candidate = candidate, quantity = entry.quantity }
            elseif candidate or not ready then
                fixedReady = false
            end
        end
        local rows, canSuggestSale = {}, fixedReady and #batch.contexts > 0
        for _, kind in ipairs({ "reward", "choice" }) do
            table.sort(rewards[kind], function(a, b) return a.order < b.order end)
            for _, entry in ipairs(rewards[kind]) do
                rows[entry.row] = {}
                selected = selected or entry.selected
            end
        end
        if next(rows) then
            for _, evaluation in ipairs(batch.contexts) do
                rankRewards(batch, rewards.reward, evaluation, rows, true, false)
                local build = rating:WithCharacterBuild(evaluation.context, true)
                local choice = { spec = evaluation.spec, context = rating:WithGuaranteedRewards(build, guaranteed),
                    guaranteed = #guaranteed > 0 }
                rankRewards(batch, rewards.choice, choice, rows, fixedReady, #rewards.choice > 1)
                canSuggestSale = canSuggestSale and not evaluation.unresolved and not choice.unresolved
            end
            for _, kind in ipairs({ "reward", "choice" }) do
                for _, entry in ipairs(rewards[kind]) do
                    entry.assessments = rows[entry.row]
                    local primary, bestChoice
                    local signature = {}
                    for _, assessment in ipairs(entry.assessments) do
                        if assessment.show then primary = primary or assessment end
                        bestChoice = bestChoice or assessment.bestChoice
                        signature[#signature + 1] = table.concat({assessment.spec.name, assessment.scenario or "",
                            assessment.gain, tostring(assessment.result.conditional), tostring(assessment.bestChoice),
                            tostring(assessment.tiedChoice), tostring(assessment.futureBiS),
                            tostring(assessment.result.placement.status)}, "\031")
                    end
                    entry.assessmentKey = table.concat(signature, "\030")
                    local previous = offers[entry.row]
                    if not previous or previous.assessmentKey ~= entry.assessmentKey then highlights.tooltipDirty = true end
                    if primary then
                        local mark = exactMark(primary, entry)
                        mark.assessments, mark.bestChoice = entry.assessments, bestChoice
                        mark.outline = kind == "choice" and #rewards.choice > 1 and not selected and bestChoice
                        results[entry.row], canSuggestSale = mark, false
                    end
                end
            end
            if canSuggestSale and #rewards.choice > 1 then
                local sale = highestSellValue(batch, rewards.choice)
                if sale then sale.outline = not selected; results[sale.entry.row] = sale end
            end
        end
        ui:QueueStatLoads(batch.pending)
        highlights.pendingItems = batch.pending
    else
        highlights.pendingItems = nil
    end
    for row, entry in pairs(offers) do
        if not currentOffers[row] and entry.kind == "bags" and not entry.widget and not shown(row)
            and settings.bags ~= false and storageContextMatches(entry) then
            -- The parent hides its badge. Keep the binding for a synchronous reopen.
            currentOffers[row] = entry
        elseif not currentOffers[row] or (marks[row] and not results[row]) then
            clearMark(row, true)
        end
    end
    offers = currentOffers
    for _, mark in pairs(results) do display(mark, settings.animate ~= false) end
    if highlights.tooltipDirty then
        highlights.tooltipDirty = nil
        addon:ScheduleItemTooltipRefresh()
    end
    if highlights.baganatorDirty then
        highlights.baganatorDirty = nil
        local api = Baganator and Baganator.API
        if hooked.baganator and api and api.RequestItemButtonsRefresh then
            local reasons = Baganator.Constants and Baganator.Constants.RefreshReason
            api.RequestItemButtonsRefresh(reasons and { reasons.ItemWidgets } or nil)
        end
    end
end

function highlights:ScheduleRefresh()
    if not self.eventFrame or self.queued then return end
    self.queued = true
    C_Timer.After(0, function()
        self.queued = nil
        refresh()
    end)
end

function highlights:InvalidateStorage()
    baganatorCache = {}
    self:ScheduleRefresh()
end

function highlights:GetTooltipOffer(owner, itemId, link)
    while owner do
        local entry = offers[owner]
        if entry and shown(owner) and entry.itemId == itemId and link then
            if entry.owned then
                if rating:SameExactItemLink(itemId, link, entry.link) then
                    local bag, slot
                    if entry.widget then
                        local state = baganatorItems[owner]
                        if state and state.details == owner.BGR then bag, slot = state.bag, state.slot end
                    else
                        bag, slot = storagePosition(owner, entry.kind)
                    end
                    if storageBindingMatches(entry, bag, slot) then return entry, marks[owner] end
                    self:ScheduleRefresh()
                end
            elseif entry.link == link or rating:NormalizeLink(itemId, link) == rating:NormalizeLink(itemId, entry.link) then
                return entry, marks[owner]
            end
        end
        owner = call(owner.GetParent, owner)
    end
end

local function hookGlobal(name, callback)
    if not hooked[name] and type(_G[name]) == "function" then
        hooksecurefunc(name, callback)
        hooked[name] = true
    end
end

local function onUpdated(kind)
    return function() clearKind(kind); highlights:ScheduleRefresh() end
end

local function migrateBaganatorCorner()
    -- Baganator applies each widget's default corner once per profile.
    local settings = addon:GetAccountDB().profile.gearHighlights
    local config = read(BAGANATOR_CONFIG, "table")
    local profiles = config and read(config.Profiles, "table")
    if settings.baganatorCornerVersion == 1 or not profiles then return end
    for _, profile in pairs(profiles) do
        local left = read(profile.icon_top_left_corner_array, "table") or {}
        local moved = false
        for index = #left, 1, -1 do
            if left[index] == BAGANATOR_WIDGET_ID then
                table.remove(left, index)
                moved = true
            end
        end
        if moved then
            local right = read(profile.icon_top_right_corner_array, "table") or {}
            for index = #right, 1, -1 do
                if right[index] == BAGANATOR_WIDGET_ID then table.remove(right, index) end
            end
            table.insert(right, 1, BAGANATOR_WIDGET_ID)
            profile.icon_top_right_corner_array = right
        end
    end
    settings.baganatorCornerVersion = 1
end

local function hookBaganator()
    local api = Baganator and Baganator.API
    if hooked.baganator or not api or not api.RegisterCornerWidget then return end
    hooked.baganator = true
    migrateBaganatorCorner()
    api.RegisterCornerWidget("Big BiS List", BAGANATOR_WIDGET_ID, function(widget, details)
        local row = widget.itemButton
        if not read(details, "table") then clearMark(row, true); baganatorItems[row] = nil; return false end
        local previous = baganatorItems[row]
        local link = read(details.itemLink, "string")
        local location = read(details.itemLocation, "table")
        local bag = location and read(location.bagID, "number")
        local slot = location and read(location.slotIndex, "number")
        local live = bag and slot and storageLink(bag, slot)
        local itemId = itemIdFromLink(live)
        local shownGUID = read(details.guid, "string")
        local guid = itemId and ui:GetStorageItemGUID(bag, slot)
        if not rating:SameExactItemLink(itemId, live, link) or not storageGUIDMatches(guid, shownGUID) then
            clearMark(row, true, true)
            baganatorItems[row] = nil
            return false
        end
        guid = guid or shownGUID
        -- A redraw creates new metadata tables for the same physical item.
        local changed = not previous or previous.bag ~= bag or previous.slot ~= slot or previous.active == false
            or not rating:SameExactItemLink(itemId, previous.link, live) or not storageGUIDMatches(previous.guid, guid)
        baganatorItems[row] = { details = details, link = live, bag = bag, slot = slot, guid = guid, widget = widget, active = true }
        local sourceId = bag .. ":" .. slot
        local cached = baganatorCache[sourceId]
        local settings = addon:GetAccountDB().profile.gearHighlights
        if cached and rating:SameExactItemLink(itemId, cached.link, live) and settings[cached.kind] ~= false
            and storageGUIDMatches(guid, cached.guid)
            and storageContextMatches(cached)
            and (cached.kind ~= "bank" or ui.personalBankOpen) then
            local entries = {}
            addItem(entries, {kind = cached.kind, row = row, sourceId = sourceId, guid = guid, owned = true, widget = widget,
                assessments = cached.assessments, assessmentKey = cached.assessmentKey,
                player = cached.player, ownedSnapshot = cached.ownedSnapshot, revision = cached.revision }, live)
            local entry = entries[1]
            if entry then
                offers[row] = entry
                if cached.mark then display(exactMark(cached.mark, entry), false, true)
                else clearMark(row, true, true); offers[row] = entry end
                return cached.mark ~= nil
            end
        end
        if changed or marks[row] then
            clearMark(row, true, true)
            highlights:ScheduleRefresh()
        end
        return marks[row] ~= nil
    end, function(row)
        local widget = newStorageBadge(row)
        widget.itemButton = row
        widget.managed = true
        overlays[row] = widget
        row:HookScript("OnHide", function()
            clearMark(row, false, true)
            baganatorItems[row] = nil
        end)
        return widget
    end, { corner = "top_right", priority = 1 })
end

local function hookPanels()
    hookBaganator()
    hookGlobal("QuestInfo_Display", onUpdated("quest"))
    hookGlobal("QuestInfo_ShowRewards", onUpdated("quest"))
    hookGlobal("QuestInfoItem_OnClick", function() highlights:ScheduleRefresh() end)
    hookGlobal("MerchantFrame_Update", onUpdated("vendor"))
    hookGlobal("TradeFrame_UpdateTargetItem", onUpdated("trade"))
    hookGlobal("GroupLootFrame_SetupItemDisplay", function(row)
        rollCards[row] = true
        clearMark(row)
        highlights:ScheduleRefresh()
    end)
    hookGlobal("GroupLootFrame_OnHide", function(row) rollCards[row] = nil; clearMark(row, true) end)
    if OpenMailFrame and OpenMailFrame.Update and not hooked.mail then
        hooksecurefunc(OpenMailFrame, "Update", onUpdated("mail"))
        hooked.mail = true
    end
    local form = craftingForm()
    if form and form.UpdateOutputItem and not hooked.crafting then
        hooksecurefunc(form, "UpdateOutputItem", onUpdated("crafting"))
        hooked.crafting = true
    end
end

function highlights:Initialize()
    if self.eventFrame or not (hooksecurefunc and C_Timer and C_Timer.After) then return end
    local frame = CreateFrame("Frame")
    self.eventFrame = frame
    for _, event in ipairs({ "ADDON_LOADED", "PLAYER_ENTERING_WORLD", "QUEST_ITEM_UPDATE", "QUEST_FINISHED",
        "MERCHANT_SHOW", "MERCHANT_UPDATE", "MERCHANT_CLOSED", "LOOT_OPENED", "LOOT_CLOSED",
        "LOOT_SLOT_CHANGED", "LOOT_SLOT_CLEARED", "START_LOOT_ROLL", "CANCEL_LOOT_ROLL", "CANCEL_ALL_LOOT_ROLLS",
        "AUCTION_HOUSE_SHOW", "AUCTION_HOUSE_CLOSED", "ITEM_SEARCH_RESULTS_UPDATED", "ITEM_SEARCH_RESULTS_ADDED", "BIDS_UPDATED",
        "TRADE_SHOW", "TRADE_CLOSED", "MAIL_SHOW", "MAIL_CLOSED", "MAIL_INBOX_UPDATE",
        "BAG_UPDATE_DELAYED", "BAG_CONTAINER_UPDATE", "BANKFRAME_OPENED", "BANKFRAME_CLOSED", "BANK_TABS_CHANGED",
        "TRADE_SKILL_SHOW", "TRADE_SKILL_CLOSE", "GET_ITEM_INFO_RECEIVED" }) do
        pcall(frame.RegisterEvent, frame, event)
    end
    frame:SetScript("OnEvent", function(_, event, id)
        if event == "ADDON_LOADED" or event == "PLAYER_ENTERING_WORLD" then
            hookPanels()
        elseif event == "LOOT_SLOT_CHANGED" or event == "LOOT_SLOT_CLEARED" then
            local slot = read(id, "number")
            if slot then lootSlotsCleared[slot] = event == "LOOT_SLOT_CLEARED" or nil end
            clearKind("loot", true, slot)
        elseif event == "CANCEL_LOOT_ROLL" or event == "CANCEL_ALL_LOOT_ROLLS" then
            local rollId = read(id, "number")
            for row in pairs(rollCards) do
                if event == "CANCEL_ALL_LOOT_ROLLS" or (rollId and read(row.rollID, "number") == rollId) then
                    rollCards[row] = nil
                    clearMark(row, true)
                end
            end
        elseif event == "LOOT_OPENED" or event == "LOOT_CLOSED" then
            lootSlotsCleared = {}
            clearKind("loot", true)
        elseif event == "GET_ITEM_INFO_RECEIVED" then
            if not (self.pendingItems and self.pendingItems[read(id, "number")]) then return end
            self:InvalidateStorage()
        elseif event == "BAG_UPDATE_DELAYED" or event == "BANK_TABS_CHANGED" then
            self:InvalidateStorage()
        end
        self:ScheduleRefresh()
    end)
    hookPanels()
    self:ScheduleRefresh()
end
