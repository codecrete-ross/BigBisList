local addon = BigBiSList
local UI = addon.UI
local widgets = addon.Widgets

local PAGE_SIZE = 5
local IDENTITY_HEIGHT = 44
local ORIGIN_HEIGHT = 36
local ORIGIN_HEADER_HEIGHT = 22
local RATE_WIDTH = 64
local GAP = 8

local function text(value)
    return value == nil and "" or tostring(value)
end

local function append(lines, value)
    if value ~= nil and text(value) ~= "" then lines[#lines + 1] = text(value) end
end

local function label(parent)
    local result = widgets:CreateLabel(parent, "", "GameFontNormalSmall")
    result:SetJustifyH("LEFT")
    result:SetJustifyV("MIDDLE")
    return result
end

local function setLabel(target, value, width, lines, lineHeight)
    widgets:SetCellText(target, value or "", lines or 1, lineHeight or 12, math.max(1, width))
    target:SetJustifyH("LEFT")
    target:SetJustifyV("MIDDLE")
    target:Show()
end

local function sourceRole(item)
    if item.kind == "quest_starter" then
        return item.relationship == "quest_chain_gate" and "Starts a required quest" or "Quest starter"
    elseif item.kind == "recipe" then
        return "Recipe"
    end
    return "Token"
end

local function refreshDetails()
    UI.detailsRenderSignature = nil
    UI:RefreshDetails(UI.selectedItemId, UI.selectedItemData, UI.selectedItemMode)
end

local function prerequisiteGesture(button, buttonName)
    if not button.itemId or not button:IsVisible() then return end
    local link = button.itemLink or ("item:" .. tostring(button.itemId))
    if buttonName == "LeftButton" then
        if IsShiftKeyDown and IsShiftKeyDown() then
            if ChatEdit_InsertLink then ChatEdit_InsertLink(link) end
        elseif IsControlKeyDown and IsControlKeyDown() then
            if DressUpItemLink then DressUpItemLink(link) end
        elseif SetItemRef then
            SetItemRef(link, link, "LeftButton")
        end
    elseif buttonName == "RightButton" and SetItemRef then
        SetItemRef(link, link, "LeftButton")
    end
end

local function sourceTooltip(button)
    if not button.itemId or not button:IsVisible() then return end
    GameTooltip:SetOwner(button, "ANCHOR_RIGHT", 4, 0)
    GameTooltip:SetHyperlink(button.itemLink or ("item:" .. tostring(button.itemId)))
    GameTooltip:Show()
end

local function originDescription(origin)
    local source = origin.source or {}
    local details = {}
    if origin.available == false then
        append(details, origin.availability_label or "Unavailable in selected tier")
    elseif origin.availability_label then
        append(details, origin.availability_label)
    end
    if origin.matched == false then append(details, "Outside current filters") end
    append(details, origin.zone or source.zone or source.location_area)
    append(details, origin.difficulty or source.difficulty)
    return table.concat(details, " - ")
end

local function originRateText(origin)
    if origin.rate_text and origin.rate_text ~= "" then return origin.rate_text end
    local kind = origin.source_type or (origin.source and origin.source.type)
    return (kind == "drop" or kind == "world_drop") and "Unknown" or ""
end

local function originTooltip(origin)
    local source = origin.source or {}
    local lines = {}
    append(lines, origin.entity_name or source.entity_name or source.boss or source.name or "Source")
    append(lines, originDescription(origin))
    local rate = originRateText(origin)
    if rate ~= "" then append(lines, "Recorded drop rate: " .. rate) end
    for _, requirement in ipairs(origin.requirements or {}) do
        if type(requirement) == "string" then append(lines, requirement)
        elseif type(requirement) == "table" then append(lines, requirement.text or requirement.label or requirement.name) end
    end
    append(lines, origin.note or source.note or source.notes)
    append(lines, origin.source_url or source.source_url)
    if BigBiSList.GetSourceAttributionLines then
        for _, credit in ipairs(BigBiSList:GetSourceAttributionLines(source)) do append(lines, credit) end
    end
    return table.concat(lines, "\n")
end

local function resetCard(card)
    UI:ResetEntityButton(card.identity, card.name, "")
    card.identity:SetHovered(false)
    card.identity.__bigBisTooltip = nil
    card.sourceItem = nil
    card.pageKey = nil
    card.pageCount = nil
    for _, row in ipairs(card.originRows) do
        row.origin = nil
        row.__bigBisTooltip = nil
        row:Hide()
    end
    card.previous:Hide()
    card.next:Hide()
    card.pageLabel:Hide()
    card:Hide()
end

local function createOriginRow(parent)
    local row = CreateFrame("Frame", nil, parent)
    row:SetHeight(ORIGIN_HEIGHT)
    row:EnableMouse(true)
    row.name = label(row)
    row.detail = label(row)
    row.rate = label(row)
    row.separator = row:CreateTexture(nil, "BACKGROUND")
    row.separator:SetColorTexture(1, 1, 1, 0.06)
    row.separator:SetHeight(1)
    row.separator:SetPoint("BOTTOMLEFT", row, "BOTTOMLEFT", 0, 0)
    row.separator:SetPoint("BOTTOMRIGHT", row, "BOTTOMRIGHT", 0, 0)
    widgets:BindTooltip(row, function(selfRow)
        return selfRow.origin and originTooltip(selfRow.origin) or nil
    end)
    return row
end

local function createCard(parent)
    local card = CreateFrame("Frame", nil, parent)
    card.role = label(card)
    card.role:SetTextColor(0.62, 0.66, 0.72, 1)
    card.identity = CreateFrame("Button", nil, card)
    card.identity:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    card.identity:SetHeight(IDENTITY_HEIGHT)
    card.identity.icon = card.identity:CreateTexture(nil, "ARTWORK")
    card.identity.icon:SetSize(28, 28)
    card.identity.icon:SetPoint("LEFT", card.identity, "LEFT", 0, 0)
    card.identity.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    card.identity.hover = card.identity:CreateTexture(nil, "BACKGROUND")
    card.identity.hover:SetAllPoints(card.identity)
    card.identity.hover:SetColorTexture(1, 0.82, 0.28, 0.06)
    card.identity.hover:Hide()
    function card.identity:SetHovered(hovered) self.hover:SetShown(hovered == true) end
    card.name = label(card.identity)
    card.name:SetPoint("LEFT", card.identity, "LEFT", 36, 0)
    card.quantity = label(card.identity)
    card.quantity:SetPoint("RIGHT", card.identity, "RIGHT", 0, 0)
    card.sourceHeading = label(card)
    card.rateHeading = label(card)
    local font, _, flags = card.rateHeading:GetFont()
    if font then card.rateHeading:SetFont(font, 11, flags) end
    card.sourceHeading:SetTextColor(0.62, 0.66, 0.72, 1)
    card.rateHeading:SetTextColor(0.62, 0.66, 0.72, 1)
    card.originRows = {}
    card.previous = widgets:CreateUtilityButton(card, "chevronLeft", 28, function()
        UI:ChangeDetailsSourcePage(card, -1)
    end, "Previous sources")
    card.next = widgets:CreateUtilityButton(card, "chevronRight", 28, function()
        UI:ChangeDetailsSourcePage(card, 1)
    end, "Next sources")
    card.pageLabel = label(card)
    card.pageLabel:SetJustifyH("CENTER")
    return card
end

function UI:GetDetailsSourceItems(option, context)
    if not option or not addon.GetAccessOptionSourceItems then return {} end
    return addon:GetAccessOptionSourceItems(option, context) or {}
end

function UI:ChangeDetailsSourcePage(card, delta)
    if not card or not card:IsVisible() or not card.pageKey or not card.sourceItem then return end
    self.detailsSourcePages = self.detailsSourcePages or {}
    local page = self.detailsSourcePages[card.pageKey] or 1
    local nextPage = math.max(1, math.min(card.pageCount or 1, page + delta))
    if nextPage == page then return end
    self.detailsSourcePages[card.pageKey] = nextPage
    refreshDetails()
end

function UI:BindDetailsSourceCard(card, sourceItem, stateKey, width)
    card:Show()
    card.sourceItem = sourceItem
    card.pageKey = text(stateKey) .. ":" .. text(sourceItem.key or sourceItem.item_id)
    self.detailsSourcePages = self.detailsSourcePages or {}
    local origins = sourceItem.routes or {}
    card.pageCount = math.max(1, math.ceil(#origins / PAGE_SIZE))
    local page = math.max(1, math.min(card.pageCount, self.detailsSourcePages[card.pageKey] or 1))
    self.detailsSourcePages[card.pageKey] = page
    card:SetWidth(width)
    card.role:ClearAllPoints()
    card.role:SetPoint("TOPLEFT", card, "TOPLEFT", 0, 0)
    setLabel(card.role, sourceRole(sourceItem), width, 1, 12)
    card.identity:ClearAllPoints()
    card.identity:SetPoint("TOPLEFT", card, "TOPLEFT", 0, -14)
    card.identity:SetWidth(width)
    local quantity = tonumber(sourceItem.count)
    local quantityText = quantity and quantity > 1 and ("x" .. tostring(quantity)) or ""
    local quantityWidth = quantityText ~= "" and math.max(28, #quantityText * 7) or 0
    setLabel(card.quantity, quantityText, math.max(1, quantityWidth), 1, 12)
    card.quantity:SetShown(quantityWidth > 0)
    setLabel(card.name, sourceItem.name, width - 36 - (quantityWidth > 0 and quantityWidth + 4 or 0), 2, 13)
    self:SetItemButton(card.identity, sourceItem.item_id, card.name, sourceItem.name, nil, nil, nil)
    setLabel(card.name, card.name.fullText or sourceItem.name, width - 36 - (quantityWidth > 0 and quantityWidth + 4 or 0), 2, 13)
    card.identity:SetScript("OnClick", prerequisiteGesture)
    widgets:BindTooltip(card.identity, sourceTooltip)

    local y = 14 + IDENTITY_HEIGHT
    for _, row in ipairs(card.originRows) do row:Hide(); row.origin = nil; row.__bigBisTooltip = nil end
    card.sourceHeading:Hide()
    card.rateHeading:Hide()
    if #origins > 0 then
        card.sourceHeading:ClearAllPoints()
        card.sourceHeading:SetPoint("TOPLEFT", card, "TOPLEFT", 0, -y - (ORIGIN_HEADER_HEIGHT - 12) / 2)
        setLabel(card.sourceHeading, "Source", width - RATE_WIDTH - GAP, 1, 12)
        card.rateHeading:ClearAllPoints()
        card.rateHeading:SetPoint("TOPLEFT", card, "TOPLEFT", width - RATE_WIDTH, -y)
        setLabel(card.rateHeading, "Recorded rate", RATE_WIDTH, 2, 11)
        y = y + ORIGIN_HEADER_HEIGHT + 4
    end
    local startIndex = (page - 1) * PAGE_SIZE + 1
    for index = startIndex, math.min(#origins, startIndex + PAGE_SIZE - 1) do
        local realizedIndex = index - startIndex + 1
        local row = card.originRows[realizedIndex]
        if not row then row = createOriginRow(card); card.originRows[realizedIndex] = row end
        local origin = origins[index]
        local source = origin.source or {}
        row.origin = origin
        widgets:BindTooltip(row, function(selfRow) return selfRow.origin and originTooltip(selfRow.origin) or nil end)
        row:Show()
        row:ClearAllPoints()
        row:SetPoint("TOPLEFT", card, "TOPLEFT", 0, -y)
        row:SetWidth(width)
        local description = originDescription(origin)
        row.name:ClearAllPoints()
        row.name:SetPoint("LEFT", row, "LEFT", 0, description ~= "" and 7 or 0)
        setLabel(row.name, origin.entity_name or source.entity_name or source.boss or source.name or "Source", width - RATE_WIDTH - GAP, 1, 13)
        row.detail:ClearAllPoints()
        row.detail:SetPoint("LEFT", row, "LEFT", 0, -7)
        setLabel(row.detail, description, width - RATE_WIDTH - GAP, 1, 12)
        row.detail:SetShown(description ~= "")
        row.detail:SetTextColor(0.62, 0.66, 0.72, 1)
        row.name:SetTextColor(0.82, 0.85, 0.90, 1)
        row.rate:ClearAllPoints()
        row.rate:SetPoint("LEFT", row, "LEFT", width - RATE_WIDTH, 0)
        setLabel(row.rate, originRateText(origin), RATE_WIDTH, 1, 12)
        row.rate:SetTextColor(0.82, 0.85, 0.90, 1)
        y = y + ORIGIN_HEIGHT
    end
    local paged = card.pageCount > 1
    card.previous:SetShown(paged)
    card.next:SetShown(paged)
    card.pageLabel:SetShown(paged)
    if paged then
        y = y + 4
        card.previous:ClearAllPoints()
        card.previous:SetPoint("TOPLEFT", card, "TOPLEFT", 0, -y)
        card.next:ClearAllPoints()
        card.next:SetPoint("TOPRIGHT", card, "TOPRIGHT", 0, -y)
        card.previous:SetEnabled(page > 1)
        card.next:SetEnabled(page < card.pageCount)
        card.pageLabel:ClearAllPoints()
        card.pageLabel:SetPoint("TOPLEFT", card, "TOPLEFT", 36, -y)
        setLabel(card.pageLabel, tostring(page) .. " / " .. tostring(card.pageCount) .. " pages", width - 72, 2, 12)
        card.pageLabel:SetJustifyH("CENTER")
        card.pageLabel:SetHeight(28)
        y = y + 28
    end
    card:SetHeight(y)
    return y
end

function UI:CreateDetailsSourceItems(parent, anchor, option, stateKey, context)
    local items = self:GetDetailsSourceItems(option, context)
    if #items == 0 then return nil end
    local block = self:AcquireDetailsWidget("source-items", parent, function(widgetParent)
        local created = CreateFrame("Frame", nil, widgetParent)
        created.cards = {}
        created:SetScript("OnHide", function(selfBlock)
            -- Native OnHide also fires when an ancestor hides. Keep those
            -- cached cards ready for reopening; only explicit pool release
            -- invalidates their entity bindings.
            if selfBlock:IsShown() then return end
            for _, card in ipairs(selfBlock.cards) do resetCard(card) end
        end)
        return created
    end)
    block:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -GAP)
    local width = math.max(120, anchor:GetWidth() or ((parent:GetWidth() or 284) - 16))
    block:SetWidth(width)
    for _, card in ipairs(block.cards) do resetCard(card) end
    local y = 0
    local routeStateKey = text(stateKey) .. ":" .. text(option.source_identity or option.key or option.source or option)
    for index, sourceItem in ipairs(items) do
        local card = block.cards[index]
        if not card then card = createCard(block); block.cards[index] = card end
        card:ClearAllPoints()
        card:SetPoint("TOPLEFT", block, "TOPLEFT", 0, -y)
        y = y + self:BindDetailsSourceCard(card, sourceItem, routeStateKey, width) + GAP
    end
    block:SetHeight(math.max(1, y - GAP))
    block.contentHeight = block:GetHeight() + GAP
    return block
end

local function questFlag(method, questId)
    if type(method) ~= "function" then return nil end
    local ok, value = pcall(method, questId)
    if ok and BigBiSList.IsReadableValue(value) and type(value) == "boolean" then return value end
end

function UI:GetAcquisitionQuestState(questId)
    local log = C_QuestLog or {}
    local completed = questFlag(log.IsQuestFlaggedCompleted, questId)
    if completed then return "Completed", nil end
    local active = questFlag(log.IsOnQuest, questId)
    if active then return "In progress", questFlag(log.IsComplete, questId) end
    if completed == false and active == false then return "Not started", nil end
    return "Unknown", nil
end

function UI:GetAcquisitionQuestProgress(source)
    local progress, nextQuest = {}, nil
    local rewardId = source.type == "quest" and (source.quest_id or source.entity_id)
    local hasRewardStep = false
    local function addStep(step)
        if step.quest_id == rewardId and step.kind ~= "alternative" then hasRewardStep = true end
        local state, turnIn = self:GetAcquisitionQuestState(step.quest_id)
        local quest = {step = step, state = state, turnIn = turnIn}
        progress[#progress + 1] = quest
        if not nextQuest and step.kind ~= "alternative" and state ~= "Completed" then
            if state == "Not started" then quest.destination = step.start
            elseif turnIn then quest.destination = step.finish end
            nextQuest = quest
        end
    end
    for _, step in ipairs(source.quest_steps or {}) do addStep(step) end
    if BigBiSList.isForever and #progress > 0 and rewardId and not hasRewardStep then
        addStep({ quest_id = rewardId, name = source.entity_name, kind = "reward" })
    end
    return nextQuest, progress
end

local function canSetWaypoint(destination)
    if not destination or not C_Map or not C_Map.CanSetUserWaypointOnMap or not C_Map.SetUserWaypoint
        or not UiMapPoint or not UiMapPoint.CreateFromCoordinates then return false end
    if type(destination.map_id) ~= "number" or destination.map_id <= 0
        or type(destination.x) ~= "number" or destination.x < 0 or destination.x > 1
        or type(destination.y) ~= "number" or destination.y < 0 or destination.y > 1 then return false end
    local ok, canSet = pcall(C_Map.CanSetUserWaypointOnMap, destination.map_id)
    return ok and BigBiSList.IsReadableValue(canSet) and canSet == true
end

function UI:SetAcquisitionWaypoint(destination)
    if (InCombatLockdown and InCombatLockdown()) or not canSetWaypoint(destination) then return false end
    local ok, point = pcall(UiMapPoint.CreateFromCoordinates, destination.map_id, destination.x, destination.y)
    if not ok or not point then return false end
    local set, result = pcall(C_Map.SetUserWaypoint, point)
    return set and BigBiSList.IsReadableValue(result) and result ~= false
end

function UI:CreateAcquisitionSteps(parent, anchor, option, accessStatus)
    local source = option and option.source
    if not BigBiSList.isForever or not source then return anchor, 0 end

    local nextQuest, progress = self:GetAcquisitionQuestProgress(source)
    local lines = {}
    for _, quest in ipairs(progress) do
        local step = quest.step
        local prefix = step.kind == "alternative" and "Alternative: " or ""
        lines[#lines + 1] = prefix .. step.name .. " · " .. quest.state
        if step.start and step.start.name then lines[#lines + 1] = "Start: " .. step.start.name end
        if step.finish and step.finish.name then lines[#lines + 1] = "Turn in: " .. step.finish.name end
    end

    local height = 0
    local destination = #lines == 0 and source.destination or nil
    if nextQuest then
        destination = nextQuest.destination
        local summary = nextQuest.step.name .. " · " .. nextQuest.state
        if nextQuest.turnIn then
            summary = summary .. "\nTurn in" .. (destination and destination.name and (": " .. destination.name) or "")
        elseif destination and destination.name then
            summary = summary .. "\nStart: " .. destination.name
        end
        anchor = self:CreateDetailsText(parent, anchor, "Next quest", summary, 0.86, 0.90, 0.96)
        height = anchor.contentHeight
    end

    if accessStatus ~= "future" and accessStatus ~= "unavailable" and canSetWaypoint(destination) then
        local block = self:AcquireDetailsWidget("source-waypoint", parent, function(widgetParent)
            local created = CreateFrame("Frame", nil, widgetParent)
            created:SetSize(124, 24)
            created.button = widgets:CreateTextButton(created, "Set waypoint", 124, 24, function()
                if created:IsVisible() then UI:SetAcquisitionWaypoint(created.destination) end
            end)
            created.button:SetPoint("TOPLEFT")
            return created
        end)
        block.destination = destination
        block:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -GAP)
        block.contentHeight = 24 + GAP
        anchor, height = block, height + block.contentHeight
    end
    if #lines > 0 then
        anchor = self:CreateDetailsText(parent, anchor, "Quest steps", table.concat(lines, "\n"))
        height = height + anchor.contentHeight
    end
    return anchor, height
end

function UI:CreateDetailsSourceRoutes(parent, anchor, sectionKey, title, entries, context, defaultExpanded)
    if not entries or #entries == 0 then return nil end
    local block = self:AcquireDetailsWidget("source-routes", parent, function(widgetParent)
        local created = CreateFrame("Frame", nil, widgetParent)
        created.header = CreateFrame("Button", nil, created)
        created.header:SetSize(120, 28)
        created.header:RegisterForClicks("LeftButtonUp")
        created.header.label = label(created.header)
        created.header.label:SetTextColor(1, 0.82, 0.28, 1)
        created.header:SetScript("OnClick", function(_, buttonName)
            if buttonName ~= "LeftButton" then return end
            if not created.sectionKey or not created:IsVisible() then return end
            UI.expandedSellerSections = UI.expandedSellerSections or {}
            UI.expandedSellerSections[created.sectionKey] = not UI:IsDetailsSectionExpanded(created.sectionKey, created.defaultExpanded)
            refreshDetails()
        end)
        created.header:SetScript("OnEnter", function(selfHeader) selfHeader.label:SetTextColor(1, 0.9, 0.48, 1) end)
        created.header:SetScript("OnLeave", function(selfHeader) selfHeader.label:SetTextColor(1, 0.82, 0.28, 1) end)
        created.header:SetScript("OnHide", function(selfHeader) selfHeader.label:SetTextColor(1, 0.82, 0.28, 1) end)
        created.header.disclosure = created.header:CreateTexture(nil, "ARTWORK")
        created.header.disclosure:SetSize(12, 12)
        created.header.disclosure:SetPoint("LEFT", created.header, "LEFT", 0, 0)
        created.header.label:ClearAllPoints()
        created.header.label:SetPoint("LEFT", created.header, "LEFT", 18, 0)
        created.routeTexts = {}
        created:SetScript("OnHide", function(selfBlock)
            if not selfBlock:IsShown() then selfBlock.sectionKey = nil end
        end)
        return created
    end)
    block.sectionKey, block.defaultExpanded = sectionKey, defaultExpanded
    block:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", 0, -12)
    block:SetPoint("RIGHT", parent, "RIGHT", -8, 0)
    local width = math.max(120, (parent:GetWidth() or 284) - 16)
    block:SetWidth(width)
    block.header:SetPoint("TOPLEFT", block, "TOPLEFT", 0, 0)
    block.header:SetWidth(width)
    setLabel(block.header.label, title .. " (" .. tostring(#entries) .. ")", width - 18, 1, 12)
    local expanded = self:IsDetailsSectionExpanded(sectionKey, defaultExpanded)
    widgets:SetIcon(block.header.disclosure, expanded and "chevronDown" or "chevronRight")
    for _, routeText in ipairs(block.routeTexts) do routeText:Hide() end
    local y = 28
    if expanded then
        for index, entry in ipairs(entries) do
            local routeText = block.routeTexts[index]
            if not routeText then routeText = label(block); block.routeTexts[index] = routeText end
            routeText:Show()
            routeText:ClearAllPoints()
            routeText:SetPoint("TOPLEFT", block, "TOPLEFT", 0, -y)
            routeText:SetWidth(width)
            routeText:SetHeight(0)
            routeText:SetWordWrap(true)
            routeText:SetText(entry.text or "")
            routeText:SetJustifyV("TOP")
            local textHeight = math.max(1, routeText:GetStringHeight() or 12)
            routeText:SetHeight(textHeight)
            y = y + textHeight
            local sourceBlock = self:CreateDetailsSourceItems(block, routeText, entry.option, sectionKey .. ":" .. text(entry.key or (entry.option and (entry.option.source_identity or entry.option.key)) or index), context)
            if sourceBlock then y = y + sourceBlock.contentHeight end
            local _, acquisitionHeight = self:CreateAcquisitionSteps(block, sourceBlock or routeText, entry.option)
            y = y + acquisitionHeight
            y = y + 12
        end
    end
    block:SetHeight(y)
    block.contentHeight = y + 12
    return block
end
