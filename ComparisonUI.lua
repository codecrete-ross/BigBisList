local addonName = ...
local addon = BigBiSList
local UI = addon.UI
local widgets = addon.Widgets

local PHASE_LABELS = { PR = "Pre", T4 = "T4", T5 = "T5", T6 = "T6", ZA = "ZA", SWP = "SWP" }
local RELATION_LABELS = {
    higher = "Higher guide rating", same_rating = "Same guide rating", lower = "Lower guide rating",
    conditional = "Depends on setup", unranked = "Not directly comparable",
}
local SELECTION_FIELDS = { "selectedRowKey", "selectedItemId", "selectedItemData", "selectedItemMode", "selectedEntityType" }

local function supportedCandidateGrade(comparison)
    if not comparison or not comparison.basis_key then return nil end
    local grade
    for _, pair in ipairs(comparison.evidence or {}) do
        local candidate = pair.candidate or {}
        local value = tonumber(candidate.grade)
        if not value or value < 1 or value > 4 or (grade and grade ~= value)
            or (type(candidate.conditions) == "table" and #candidate.conditions > 0)
            or (type(candidate.conditions) == "string" and candidate.conditions ~= "") then return nil end
        grade = value
    end
    return grade
end

local function itemName(row)
    return row and (row.name or (row.item_id and ("Item " .. tostring(row.item_id)))) or "Empty slot"
end

local function referenceId(reference)
    return type(reference) == "table" and reference.item_id or tonumber(reference)
end

local function phaseIndex(phase)
    for index, value in ipairs(addon:GetPhaseOrder()) do if value == phase then return index end end
    return 0
end

local function comparisonSlot(data)
    local slot = type(data) == "string" and data or (data.slot or data.slot_key or data.slotKey)
    for _, filter in ipairs(addon:GetDisplaySlotFilters()) do
        if slot == filter.key or slot == filter.label then return filter.key end
    end
    for _, definition in ipairs(addon:GetEquipmentSlotDefinitions()) do
        if slot == definition.key or slot == definition.label or (type(data) == "table" and data.slotKey == definition.key) then
            return definition.slots[1]
        end
    end
    return slot
end

local function label(parent)
    local text = widgets:CreateLabel(parent, "", "GameFontNormalSmall")
    text:SetJustifyV("MIDDLE")
    return text
end

local function setCell(text, value, x, width, height, lines)
    text:ClearAllPoints()
    text:SetPoint("LEFT", text:GetParent(), "LEFT", x, 0)
    widgets:SetCellText(text, value or "", lines or 2, 12, math.max(1, width))
    text:SetJustifyV("MIDDLE")
    text:Show()
end

local function evidenceTooltip(row)
    local comparison = row.comparison or {}
    local lines = { comparison.explanation or RELATION_LABELS[comparison.relation] or RELATION_LABELS.unranked }
    for _, pair in ipairs(comparison.evidence or {}) do
        local candidate, reference = pair.candidate or {}, pair.reference or {}
        if candidate.original_rating then lines[#lines + 1] = "Candidate: " .. tostring(candidate.original_rating) end
        if reference.original_rating then lines[#lines + 1] = "Reference: " .. tostring(reference.original_rating) end
        if type(candidate.conditions) == "table" and #candidate.conditions > 0 then lines[#lines + 1] = table.concat(candidate.conditions, "; ")
        elseif type(candidate.conditions) == "string" and candidate.conditions ~= "" then lines[#lines + 1] = candidate.conditions end
        if candidate.source_url then lines[#lines + 1] = candidate.source_url end
    end
    return table.concat(lines, "\n")
end

function UI:IsSlotComparisonOpen()
    return self.slotComparison ~= nil
end

function UI:GetComparisonReferenceLabel(reference)
    if type(reference) == "table" then
        local position = reference.slot or reference.slot_label or "Equipped"
        if reference.occupancy == "blocked" then return position .. ": occupied by two-handed weapon" end
        if not reference.item_id then return position .. ": empty" end
        return position .. ": " .. itemName(reference)
    end
    for _, row in ipairs(self.slotComparison and self.slotComparison.rows or {}) do
        if row.item_id == referenceId(reference) then return itemName(row) end
    end
    return reference and ("Item " .. tostring(reference)) or "Empty slot"
end

function UI:OpenSlotComparison(data, mode)
    if self:IsLevelingMode() or not data then return false end
    local slot = comparisonSlot(data)
    if not slot then return false end
    if self.slotComparison then self:CloseSlotComparison() end
    local selection = self:GetSelection()
    local origin = { scroll = self.contentScroll:GetVerticalScroll(), detailsScroll = self.detailsScroll:GetVerticalScroll(),
        inspectorVisible = self:IsInspectorVisible(), mode = mode }
    for _, key in ipairs(SELECTION_FIELDS) do origin[key] = self[key] end
    self.slotComparison = { slot = slot, class = selection.class, spec = selection.spec, phase = selection.phase,
        origin = origin, rows = {}, entries = {}, page = 1, scroll = 0, generation = 0 }
    self:CreateSlotComparisonFrame()
    widgets:CloseDropdownMenus()
    self:RenderSlotComparison(true)
    return true
end

function UI:CloseSlotComparison()
    local state = self.slotComparison
    if not state then return false end
    self.slotComparison = nil
    if self.comparisonFrame then self.comparisonFrame:Hide() end
    for _, row in ipairs(self.comparisonActiveRows or {}) do
        row.comparisonData, row.comparisonGeneration = nil, nil
        self:ResetEntityButton(row.iconButton, row.nameText, "")
        row:Hide()
    end
    for _, row in ipairs(self.comparisonPinnedRows or {}) do
        row.comparisonData, row.comparisonGeneration, row.referenceButton.reference = nil, nil, nil
        self:ResetEntityButton(row.iconButton, nil, "")
        row:Hide()
    end
    local origin = state.origin
    for _, key in ipairs(SELECTION_FIELDS) do self[key] = origin[key] end
    self.detailsRenderSignature, self.bodyLayoutSignature = nil, nil
    self.detailsBackButton.label:SetText("Back to list")
    self.detailsBackButton:SetWidth(110)
    self:ApplyBodyLayout()
    self.contentScroll:SetVerticalScroll(origin.scroll or 0)
    self:UpdateVirtualList(true)
    if origin.inspectorVisible and self.selectedItemId then
        self:RefreshDetails(self.selectedItemId, self.selectedItemData, self.selectedItemMode)
        self.detailsScroll:SetVerticalScroll(math.min(origin.detailsScroll or 0, self.detailsScroll:GetVerticalScrollRange()))
    end
    if state.originNeedsRefresh then self:ScheduleRefresh(nil, "comparison-return") end
    return true
end

function UI:ShowComparisonDetails(data)
    local state = self.slotComparison
    if not state or not data or not data.item_id then return end
    local key = self:GetRowKey(data, "comparison")
    if self.selectedRowKey ~= key then self.detailsScroll:SetVerticalScroll(0) end
    state.detailsOpen, state.selectedItemId = true, data.item_id
    state.scroll = self.comparisonScroll:GetVerticalScroll()
    self.selectedRowKey, self.selectedItemId, self.selectedItemData = key, data.item_id, data
    self.selectedItemMode, self.selectedEntityType = "comparison", "item"
    self.detailsRenderSignature = nil
    self:ApplySlotComparisonLayout()
    self:RefreshDetails(data.item_id, data, "comparison")
end

function UI:BackToSlotComparison()
    local state = self.slotComparison
    if not state or not state.detailsOpen then return false end
    state.detailsOpen = false
    self:ApplySlotComparisonLayout()
    self.comparisonScroll:SetVerticalScroll(state.scroll or 0)
    self:UpdateComparisonVirtualList()
    return true
end

function UI:SetComparisonReference(reference)
    local state = self.slotComparison
    if not state then return end
    local matched
    if type(reference) == "table" then
        for _, context in ipairs(state.contexts) do if context.slotKey == reference.slotKey then matched = context; break end end
    else
        for _, row in ipairs(state.rows) do
            if row.item_id == tonumber(reference) and not addon:GetCharacterDB().ignoredItems[tostring(row.item_id)] then matched = row.item_id; break end
        end
    end
    if matched == nil then return false end
    reference = matched
    state.reference = reference
    self:RebuildComparisonEntries()
    self:LayoutSlotComparison()
end

function UI:RefreshComparisonPool(force)
    local state = self.slotComparison
    if not state then return end
    local signature = table.concat({ state.class, state.spec, state.phase, state.slot,
        tostring(addon:GetDataIndex(state.phase)), tostring(BigBiSListData), tostring(self.currentOwned) }, "\031")
    if not force and state.poolSignature == signature then return end
    local rows = addon:GetSlotComparisonRows(state.class, state.spec, state.phase, state.slot, self.currentOwned, state.reference)
    if state.poolSignature then state.originNeedsRefresh = true end
    state.rows, state.contexts, state.poolSignature = rows, rows.contexts or {}, signature
    if state.reference == nil then state.reference = state.contexts[1] or rows.reference end
    if type(state.reference) == "table" then
        for _, context in ipairs(state.contexts) do if context.slotKey == state.reference.slotKey then state.reference = context; break end end
    end
    state.pinned = {}
    for _, context in ipairs(state.contexts) do
        local pinned = { item_id = context.item_id, name = context.name, slot = state.slot, context = context,
            owned_state = "equipped", occupancy = context.occupancy, reference_context = context }
        if context.item_id then pinned.history = addon:GetRecommendationHistory(context.item_id, state.class, state.spec, state.phase, state.slot) end
        state.pinned[#state.pinned + 1] = pinned
    end
    self:RebuildComparisonEntries()
end

function UI:RebuildComparisonEntries()
    local state = self.slotComparison
    if not state then return end
    local groups, ordered = {}, {}
    local ignored = addon:GetCharacterDB().ignoredItems
    for _, row in ipairs(state.rows) do
        if not ignored[tostring(row.item_id)] then
        row.comparison = addon:CompareRecommendationItems(row.item_id, referenceId(state.reference), state.class, state.spec, state.phase, state.slot)
        row.is_reference = row.item_id == referenceId(state.reference)
        local comparison = row.comparison or {}
        row.comparisonGrade = supportedCandidateGrade(comparison)
        local basis = comparison.basis_key
        local key = basis or (comparison.relation == "conditional" and "conditional" or "unranked")
        if not groups[key] then
            local pair = comparison.evidence and comparison.evidence[1]
            local source = pair and pair.candidate or {}
            local title = basis and ((comparison.historical and "Earlier evidence: " or "Shared guide: ") .. addon:GetPhaseDisplayName(comparison.phase)
                .. (source.table_heading and (" · " .. source.table_heading) or ""))
                or (key == "conditional" and "Depends on setup" or "No shared rating")
            groups[key] = { key = key, title = title, phase = comparison.phase, basis = basis, source_url = source.source_url, rows = {} }
            ordered[#ordered + 1] = groups[key]
        end
        groups[key].rows[#groups[key].rows + 1] = row
        end
    end
    table.sort(ordered, function(a, b)
        if (a.basis ~= nil) ~= (b.basis ~= nil) then return a.basis ~= nil end
        if phaseIndex(a.phase) ~= phaseIndex(b.phase) then return phaseIndex(a.phase) > phaseIndex(b.phase) end
        return a.key < b.key
    end)
    local entries, y = {}, 0
    local rowHeight = self:GetDensityMetrics()
    for _, group in ipairs(ordered) do
        table.sort(group.rows, function(a, b)
            if group.basis then
                local ar, br = a.comparisonGrade, b.comparisonGrade
                if (ar ~= nil) ~= (br ~= nil) then return ar ~= nil end
                if ar and br and ar ~= br then return ar < br end
            end
            if string.lower(itemName(a)) ~= string.lower(itemName(b)) then return string.lower(itemName(a)) < string.lower(itemName(b)) end
            return (a.item_id or 0) < (b.item_id or 0)
        end)
        entries[#entries + 1] = { kind = "section", title = group.title .. " (" .. #group.rows .. ")", basis = group.basis, source_url = group.source_url, top = y, height = 28 }
        y = y + 28
        for _, row in ipairs(group.rows) do
            entries[#entries + 1] = { kind = "row", data = row, top = y, height = rowHeight }
            y = y + rowHeight
        end
    end
    if #entries == 0 then
        entries[1] = { kind = "empty", title = "No recorded recommendations for this specialization and slot.", top = 0, height = 56 }
        y = 56
    end
    state.entries, state.contentHeight = entries, math.max(1, y)
    state.rowHeight = rowHeight
    state.generation = state.generation + 1
end

function UI:GetComparisonColumns(width)
    local state = self.slotComparison
    width = math.max(320, width)
    local narrow = width < 940
    local itemWidth, evidenceWidth, sourceWidth = narrow and 150 or 200, narrow and 125 or 150, narrow and 110 or 155
    local ownedWidth, actionWidth, gap = 58, 28, 6
    if width < 650 then itemWidth, evidenceWidth, sourceWidth, ownedWidth = 130, 100, 75, 50 end
    local phases, others = addon:GetPhaseOrder(), {}
    local available = width - itemWidth - evidenceWidth - sourceWidth - ownedWidth - actionWidth - gap * 5
    local capacity = math.max(2, math.min(#phases, math.floor(available / 42), narrow and 3 or 6))
    local visible, pages = {}, 1
    if capacity >= #phases then
        for _, phase in ipairs(phases) do visible[#visible + 1] = phase end
        state.page = 1
    else
        for _, phase in ipairs(phases) do if phase ~= state.phase then others[#others + 1] = phase end end
        pages = math.ceil(#others / (capacity - 1))
        state.page = math.max(1, math.min(pages, state.page or 1))
        local included = { [state.phase] = true }
        for index = (state.page - 1) * (capacity - 1) + 1, math.min(#others, state.page * (capacity - 1)) do included[others[index]] = true end
        for _, phase in ipairs(phases) do if included[phase] then visible[#visible + 1] = phase end end
    end
    local cellWidth = math.max(30, math.floor(available / #visible))
    local columns = { item = { x = 0, width = itemWidth }, evidence = { x = itemWidth + gap, width = evidenceWidth }, phases = {} }
    local x = itemWidth + evidenceWidth + gap * 2
    for _, phase in ipairs(visible) do columns.phases[#columns.phases + 1] = { phase = phase, x = x, width = cellWidth }; x = x + cellWidth end
    columns.source = { x = x + gap, width = sourceWidth }
    columns.owned = { x = columns.source.x + sourceWidth + gap, width = ownedWidth }
    columns.action = { x = columns.owned.x + ownedWidth + gap, width = actionWidth }
    columns.pages, columns.visiblePhases, columns.width = pages, visible, width
    return columns
end

function UI:CreateComparisonRow(parent)
    local row = widgets:CreateItemRow(parent, 56)
    row.nameText, row.metaText, row.evidenceText, row.sourceText, row.ownedText, row.sectionText = label(row), label(row), label(row), label(row), label(row), label(row)
    row.iconButton = widgets:CreateIconButton(row, 32)
    row.iconButton:HookScript("OnEnter", function() row:SetHovered(true) end)
    row.iconButton:HookScript("OnLeave", function() row:SetHovered(false) end)
    row.sourceTarget = CreateFrame("Button", nil, row)
    row.sourceTarget:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    function row.sourceTarget:SetHovered(hovered) self:GetParent():SetHovered(hovered) end
    row.sourceTarget:SetScript("OnClick", function(button, mouse) UI:HandleEntityGesture(button:GetParent().comparisonData, "comparison", mouse, button) end)
    row.phaseCells, row.phaseMarks, row.phaseLiveMarks = {}, {}, {}
    row.referenceButton = widgets:CreateTextButton(row, "Use as reference", 122, 28, function(button)
        if button.reference then UI:SetComparisonReference(button.reference) end
    end)
    row.star = widgets:CreateUtilityButton(row, "starOutline", 28, function(button)
        local data = button:GetParent().comparisonData
        if not data or not data.item_id then return end
        if addon:GetCharacterDB().wishlist[tostring(data.item_id)] then UI:RemoveWishlist(data.item_id) else UI:AddWishlist(data.item_id) end
    end, "Save item to Wishlist")
    row:SetScript("OnMouseUp", function(selfRow, buttonName)
        if not selfRow.comparisonData or not UI.slotComparison or selfRow.comparisonGeneration ~= UI.slotComparison.generation then return end
        UI:HandleEntityGesture(selfRow.comparisonData, "comparison", buttonName, selfRow)
    end)
    return row
end

function UI:BindComparisonRow(row, entry, pinned)
    local state, columns = self.slotComparison, self.comparisonColumns
    if row.comparisonData ~= entry.data or row.comparisonKind ~= entry.kind then
        local owner = GameTooltip and GameTooltip.GetOwner and GameTooltip:GetOwner()
        while owner do
            if owner == row then GameTooltip:Hide(); break end
            owner = owner.GetParent and owner:GetParent()
        end
        row:SetHovered(false); row.iconButton:SetHovered(false)
        row.star:SetHovered(false); row.star:SetFocused(false)
        row.referenceButton:SetHovered(false); row.referenceButton:SetFocused(false)
    end
    row:Show()
    row:SetHeight(entry.height)
    row:SetWidth(columns.width)
    row.comparisonData, row.comparisonGeneration = entry.data, state.generation
    row.comparisonKind = entry.kind
    for _, text in ipairs({ row.nameText, row.metaText, row.evidenceText, row.sourceText, row.ownedText, row.sectionText }) do text:Hide() end
    for _, cell in ipairs(row.phaseCells) do cell:Hide() end
    for _, mark in ipairs(row.phaseMarks) do mark:Hide() end
    for _, mark in ipairs(row.phaseLiveMarks) do mark:Hide() end
    row.iconButton:Hide(); row.star:Hide(); row.referenceButton:Hide(); row.sourceTarget:Hide()
    row:SetSelected(entry.data and entry.data.item_id == referenceId(state.reference))
    if entry.kind == "section" or entry.kind == "empty" then
        setCell(row.sectionText, entry.title, 6, columns.width - 12, entry.height, 1)
        row.sectionText:SetTextColor(entry.kind == "empty" and .72 or .92, .76, entry.kind == "empty" and .8 or .32, 1)
        widgets:BindTooltip(row, entry.basis and (entry.title .. "\nRatings in this group share a source table and phase.\n" .. (entry.source_url or "")) or entry.title)
        self:ResetEntityButton(row.iconButton, nil, "")
        return
    end
    local data = entry.data
    local _, iconSize, lines = self:GetDensityMetrics()
    row.iconButton:SetSize(iconSize, iconSize); row.iconButton:ClearAllPoints()
    row.iconButton:SetPoint("LEFT", row, "LEFT", 4, 0); row.iconButton:Show()
    row.nameText:ClearAllPoints(); row.nameText:SetPoint("LEFT", row, "LEFT", iconSize + 12, pinned and 7 or 0)
    widgets:SetCellText(row.nameText, itemName(data), pinned and 1 or lines, 12, columns.item.width - iconSize - 16)
    row.nameText:Show()
    if data.item_id then self:SetItemButton(row.iconButton, data.item_id, row.nameText, itemName(data), data.item and data.item.quality, data, "comparison")
    else self:ResetEntityButton(row.iconButton, row.nameText, data.occupancy == "blocked" and "Two-handed weapon" or "Empty slot") end
    if pinned then
        setCell(row.metaText, data.context.slot or data.context.slot_label or "Equipped", iconSize + 12, columns.item.width - iconSize - 16, entry.height, 1)
        row.metaText:SetPoint("LEFT", row, "LEFT", iconSize + 12, -8)
        row.referenceButton:ClearAllPoints(); row.referenceButton:SetPoint("LEFT", row, "LEFT", columns.evidence.x, 0)
        row.referenceButton.reference = data.reference_context
        local selected = type(state.reference) == "table" and state.reference.slotKey == data.context.slotKey
        row.referenceButton.label:SetText(selected and "Reference" or "Use as reference")
        row.referenceButton:SetSelected(selected); row.referenceButton:SetWidth(columns.evidence.width); row.referenceButton:Show()
    else
        local comparison = data.comparison or {}
        local comparisonText = RELATION_LABELS[comparison.relation] or RELATION_LABELS.unranked
        if data.is_reference then comparisonText = "Reference item" end
        if comparison.historical and comparison.phase then comparisonText = comparisonText .. "\n" .. addon:GetPhaseDisplayName(comparison.phase) .. " guide" end
        setCell(row.evidenceText, comparisonText, columns.evidence.x, columns.evidence.width, entry.height, lines)
        widgets:BindTooltip(row, evidenceTooltip(data))
    end
    local live = addon:GetCurrentPhaseKey()
    for index, column in ipairs(columns.phases) do
        local target = row.phaseCells[index]
        if not target then
            target = CreateFrame("Button", nil, row); target.text = label(target); row.phaseCells[index] = target
            function target:SetHovered(hovered) self:GetParent():SetHovered(hovered) end
            target:RegisterForClicks("LeftButtonUp", "RightButtonUp")
            target:SetScript("OnClick", function(button, mouse) UI:HandleEntityGesture(button:GetParent().comparisonData, "comparison", mouse, button) end)
        end
        target:ClearAllPoints(); target:SetPoint("LEFT", row, "LEFT", column.x, 0); target:SetSize(column.width, entry.height)
        local cell = data.history and data.history.phases and data.history.phases[column.phase]
        local text = cell and cell.label or "No guide"
        if cell and cell.status == "not_listed" then text = "Not listed" elseif cell and cell.status == "no_guide" then text = "No guide" elseif cell and cell.status == "conditional" then text = "Depends on setup" end
        setCell(target.text, text, 3, column.width - 6, entry.height, lines)
        target.text:SetJustifyH("CENTER")
        local future = phaseIndex(column.phase) > addon:GetAvailabilityPhaseIndex(state.phase)
        target.text:SetTextColor(future and .59 or .83, future and .61 or .85, future and .65 or .89, 1)
        local description = addon:GetPhaseDisplayName(column.phase) .. "\n" .. text
        if text == "Not listed" then description = description .. "\nNot listed in the available guide. This does not mean the item is obsolete."
        elseif text == "No guide" then description = description .. "\nNo comparable guide coverage is recorded." end
        for _, evidence in ipairs(cell and cell.evidence or {}) do
            if evidence.original_rating then description = description .. "\n" .. tostring(evidence.original_rating) end
            if type(evidence.conditions) == "table" and #evidence.conditions > 0 then description = description .. "\n" .. table.concat(evidence.conditions, "; ") end
            if evidence.source_url then description = description .. "\n" .. evidence.source_url end
        end
        widgets:BindTooltip(target, description); target:Show()
        local mark = row.phaseMarks[index]
        if not mark then mark = row:CreateTexture(nil, "BACKGROUND"); row.phaseMarks[index] = mark end
        mark:ClearAllPoints(); mark:SetPoint("TOPLEFT", row, "TOPLEFT", column.x, 0)
        mark:SetSize(column.width, entry.height)
        mark:SetColorTexture(.92, .76, .32, .10)
        mark:SetShown(column.phase == state.phase)
        local liveMark = row.phaseLiveMarks[index]
        if not liveMark then liveMark = row:CreateTexture(nil, "OVERLAY"); row.phaseLiveMarks[index] = liveMark end
        liveMark:ClearAllPoints(); liveMark:SetPoint("TOPLEFT", row, "TOPLEFT", column.x, 0)
        liveMark:SetSize(column.width, 1); liveMark:SetColorTexture(.3, .7, .96, .7)
        liveMark:SetShown(column.phase == live)
    end
    local display = data.acquisition_display or {}
    local sourceText = pinned and "Equipped" or (display.location_label or display.source_summary or display.source_label or "Source not recorded")
    setCell(row.sourceText, sourceText, columns.source.x, columns.source.width, entry.height, lines)
    row.sourceTarget:ClearAllPoints(); row.sourceTarget:SetPoint("LEFT", row, "LEFT", columns.source.x, 0)
    row.sourceTarget:SetSize(columns.source.width, entry.height)
    local sourceTooltip = pinned and self:GetComparisonReferenceLabel(data.context) or ((display.source_label or "Source") .. "\n" .. sourceText)
    if display.option and display.option.cost_summary and display.option.cost_summary ~= "" then sourceTooltip = sourceTooltip .. "\n" .. display.option.cost_summary end
    widgets:BindTooltip(row.sourceTarget, sourceTooltip); row.sourceTarget:Show()
    local owned = data.owned_state
    setCell(row.ownedText, owned == "equipped" and "Equipped" or owned == "bank" and "Bank" or owned == "bag" and "Bags" or "Not owned", columns.owned.x, columns.owned.width, entry.height, lines)
    if data.item_id then
        row.star:ClearAllPoints(); row.star:SetPoint("LEFT", row, "LEFT", columns.action.x, 0)
        local saved = addon:GetCharacterDB().wishlist[tostring(data.item_id)]
        widgets:SetIcon(row.star.icon, saved and "starFilled" or "starOutline"); row.star:SetSelected(saved == true); row.star:Show()
    end
end

function UI:CreateSlotComparisonFrame()
    if self.comparisonFrame then return end
    local frame = widgets:CreatePanel(nil, self.body)
    frame:SetAllPoints(self.body); frame:SetFrameLevel(self.body:GetFrameLevel() + 4)
    self.comparisonFrame = frame
    self.comparisonBackButton = widgets:CreateTextButton(frame, "Back to results", 120, 28, function() self:CloseSlotComparison() end)
    self.comparisonBackButton:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -6)
    self.comparisonTitle = label(frame); self.comparisonTitle:SetPoint("LEFT", self.comparisonBackButton, "RIGHT", 12, 0)
    self.comparisonScope = label(frame); self.comparisonScope:SetPoint("TOPLEFT", self.comparisonBackButton, "BOTTOMLEFT", 0, -6)
    self.comparisonReference = widgets:CreateDropdown("BigBiSListComparisonReference", frame, 240,
        function() return "Reference: " .. self:GetComparisonReferenceLabel(self.slotComparison and self.slotComparison.reference) end,
        function()
            local state, items = self.slotComparison, {}
            if not state then return items end
            for _, context in ipairs(state.contexts) do items[#items + 1] = { value = context, text = self:GetComparisonReferenceLabel(context), checked = state.reference == context } end
            for _, row in ipairs(state.rows) do
                if not addon:GetCharacterDB().ignoredItems[tostring(row.item_id)] then
                    items[#items + 1] = { value = row.item_id, text = itemName(row), checked = state.reference == row.item_id }
                end
            end
            return items
        end, function(value) self:SetComparisonReference(value) end)
    self.comparisonReference:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -58)
    self.comparisonPrev = widgets:CreateUtilityButton(frame, "chevronLeft", 28, function() self:ChangeComparisonPhasePage(-1) end, "Earlier phase columns")
    self.comparisonNext = widgets:CreateUtilityButton(frame, "chevronRight", 28, function() self:ChangeComparisonPhasePage(1) end, "Later phase columns")
    self.comparisonNext:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -10, -58)
    self.comparisonPrev:SetPoint("RIGHT", self.comparisonNext, "LEFT", -6, 0)
    self.comparisonPageLabel = label(frame); self.comparisonPageLabel:SetPoint("RIGHT", self.comparisonPrev, "LEFT", -8, 0)
    self.comparisonHeader = CreateFrame("Frame", nil, frame); self.comparisonHeader:SetHeight(32)
    self.comparisonHeader:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -96); self.comparisonHeader:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -28, -96)
    self.comparisonHeader.cells = {}
    self.comparisonPinned = CreateFrame("Frame", nil, frame)
    self.comparisonPinned:SetPoint("TOPLEFT", self.comparisonHeader, "BOTTOMLEFT", 0, 0)
    self.comparisonPinned:SetPoint("TOPRIGHT", self.comparisonHeader, "BOTTOMRIGHT", 0, 0)
    self.comparisonPinnedRows = {}
    self.comparisonScroll, self.comparisonChild = widgets:CreateScrollFrame("BigBiSListComparisonScroll", frame)
    self.comparisonScroll:SetPoint("TOPLEFT", self.comparisonPinned, "BOTTOMLEFT", 0, -4)
    self.comparisonScroll:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -28, 8)
    self.comparisonScroll:HookScript("OnVerticalScroll", function() self:UpdateComparisonVirtualList() end)
    self.comparisonScroll:HookScript("OnSizeChanged", function() if self.slotComparison then self:LayoutSlotComparison() end end)
    self.comparisonActiveRows = {}
end

function UI:ChangeComparisonPhasePage(delta)
    local state = self.slotComparison
    if not state then return end
    state.page = math.max(1, math.min(self.comparisonColumns.pages, state.page + delta))
    self:LayoutSlotComparison()
end

function UI:LayoutSlotComparison()
    local state = self.slotComparison
    if not state or not self.comparisonFrame or self.comparisonLayoutActive then return end
    self.comparisonLayoutActive = true
    if state.rowHeight ~= self:GetDensityMetrics() then self:RebuildComparisonEntries() end
    local width = math.max(320, self.comparisonFrame:GetWidth() - 36)
    local stackedPager = self.comparisonFrame:GetWidth() < 760
    self.comparisonNext:ClearAllPoints()
    self.comparisonNext:SetPoint("TOPRIGHT", self.comparisonFrame, "TOPRIGHT", -10, stackedPager and -94 or -58)
    self.comparisonHeader:ClearAllPoints()
    self.comparisonHeader:SetPoint("TOPLEFT", self.comparisonFrame, "TOPLEFT", 8, stackedPager and -132 or -96)
    self.comparisonHeader:SetPoint("TOPRIGHT", self.comparisonFrame, "TOPRIGHT", -28, stackedPager and -132 or -96)
    self.comparisonColumns = self:GetComparisonColumns(width)
    local columns, header = self.comparisonColumns, self.comparisonHeader
    local headings = { { text = "Item", column = columns.item }, { text = "Compared with reference", column = columns.evidence } }
    local live = addon:GetCurrentPhaseKey()
    for _, column in ipairs(columns.phases) do headings[#headings + 1] = { text = (PHASE_LABELS[column.phase] or column.phase) .. (column.phase == live and "\nLive" or ""), column = column, phase = column.phase } end
    headings[#headings + 1] = { text = "Source", column = columns.source }
    headings[#headings + 1] = { text = "Owned", column = columns.owned }
    for _, text in ipairs(header.cells) do text:Hide() end
    for index, heading in ipairs(headings) do
        local text = header.cells[index] or label(header); header.cells[index] = text
        setCell(text, heading.text, heading.column.x, heading.column.width, 32, 2)
        text:SetJustifyH(heading.phase and "CENTER" or "LEFT")
        local selected = heading.phase == state.phase
        text:SetTextColor(selected and .92 or .72, selected and .76 or .75, selected and .32 or .8, 1)
    end
    self.comparisonTitle:SetText("Compare " .. state.slot)
    widgets:SetCellText(self.comparisonScope, "All sources for " .. state.spec .. " · " .. state.slot .. " · Available through " .. addon:GetPhaseDisplayName(state.phase), 1, 12, width)
    self.comparisonScope:Show()
    self.comparisonReference:Refresh()
    self.comparisonPrev:SetShown(columns.pages > 1); self.comparisonNext:SetShown(columns.pages > 1)
    self.comparisonPrev:SetEnabled(state.page > 1); self.comparisonNext:SetEnabled(state.page < columns.pages)
    self.comparisonPageLabel:SetText(columns.pages > 1 and (state.page .. " / " .. columns.pages .. " · selected tier stays visible") or "Gold: selected tier · Blue: live · Muted: future")
    local rowHeight = self:GetDensityMetrics()
    self.comparisonPinned:SetHeight(#state.pinned * rowHeight)
    for _, row in ipairs(self.comparisonPinnedRows) do
        row.comparisonData, row.comparisonGeneration, row.referenceButton.reference = nil, nil, nil
        row:Hide()
    end
    for index, data in ipairs(state.pinned) do
        local row = self.comparisonPinnedRows[index] or self:CreateComparisonRow(self.comparisonPinned)
        self.comparisonPinnedRows[index] = row
        row:ClearAllPoints(); row:SetPoint("TOPLEFT", self.comparisonPinned, "TOPLEFT", 0, -(index - 1) * rowHeight)
        self:BindComparisonRow(row, { kind = "row", data = data, height = rowHeight }, true); row:Show()
    end
    self.comparisonChild:SetWidth(width); self.comparisonChild:SetHeight(state.contentHeight)
    widgets:UpdateScrollOverflow(self.comparisonScroll)
    self.comparisonLayoutActive = false
    self:UpdateComparisonVirtualList()
end

function UI:UpdateComparisonVirtualList()
    local state = self.slotComparison
    if not state or not self.comparisonScroll or not self.comparisonColumns then return end
    if self.comparisonRenderActive then self.comparisonRenderPending = true; return end
    self.comparisonRenderActive = true
    repeat
        self.comparisonRenderPending = false
        local offset, height = self.comparisonScroll:GetVerticalScroll(), self.comparisonScroll:GetHeight()
        state.scroll = offset
        local active = 0
        for _, entry in ipairs(state.entries) do
            if entry.top + entry.height >= offset and entry.top <= offset + height then
                active = active + 1
                local row = self.comparisonActiveRows[active] or self:CreateComparisonRow(self.comparisonChild)
                self.comparisonActiveRows[active] = row
                row:ClearAllPoints(); row:SetPoint("TOPLEFT", self.comparisonChild, "TOPLEFT", 0, -entry.top)
                self:BindComparisonRow(row, entry); row:Show()
            end
        end
        for index = active + 1, #self.comparisonActiveRows do
            local row = self.comparisonActiveRows[index]
            row.comparisonData, row.comparisonGeneration = nil, nil
            self:ResetEntityButton(row.iconButton, nil, ""); row:Hide()
        end
    until not self.comparisonRenderPending
    self.comparisonRenderActive = false
end

function UI:ApplySlotComparisonLayout()
    local state = self.slotComparison
    if not state then return false end
    self.contentRegion:Hide(); self.filterDrawer:Hide()
    if self.fixedActiveFilterBar then self.fixedActiveFilterBar:Hide() end
    self.comparisonFrame:SetShown(not state.detailsOpen)
    self.details:SetShown(state.detailsOpen == true)
    if state.detailsOpen then
        self.inspectorDocked, self.inspectorExclusive = false, true
        self.details:SetWidth(self.body:GetWidth())
        self.details:SetFrameLevel(self.body:GetFrameLevel() + 6)
        self.detailsHeader:ClearAllPoints()
        self.detailsHeader:SetPoint("TOPLEFT", self.details, "TOPLEFT", 0, -36)
        self.detailsHeader:SetPoint("TOPRIGHT", self.details, "TOPRIGHT", 0, -36)
        self.detailsBackButton.label:SetText("Back to comparison"); self.detailsBackButton:SetWidth(154); self.detailsBackButton:Show()
    else
        self:LayoutSlotComparison()
    end
    return true
end

function UI:RenderSlotComparison(force)
    if not self.slotComparison then return end
    self:CreateSlotComparisonFrame()
    self:RefreshComparisonPool(force)
    local state, hiddenKeys = self.slotComparison, {}
    local ignored = addon:GetCharacterDB().ignoredItems
    for key, hidden in pairs(ignored) do if hidden then hiddenKeys[#hiddenKeys + 1] = tostring(key) end end
    table.sort(hiddenKeys)
    local signature = table.concat(hiddenKeys, ":")
    if state.hiddenSignature ~= signature then
        if state.hiddenSignature then state.originNeedsRefresh = true end
        state.hiddenSignature = signature
        local equipped = {}
        for _, context in ipairs(state.contexts) do if context.item_id then equipped[context.item_id] = context end end
        local current = referenceId(state.reference)
        if current and ignored[tostring(current)] then state.reference = equipped[current] or state.contexts[1] end
        if state.detailsOpen and ignored[tostring(state.selectedItemId)] and not equipped[state.selectedItemId] then
            self:BackToSlotComparison()
            state.selectedItemId = nil
            self:ClearSelectedRow()
        end
        local originalItem = state.origin.selectedItemId
        if originalItem and ignored[tostring(originalItem)] and not equipped[originalItem] then
            for _, key in ipairs(SELECTION_FIELDS) do state.origin[key] = nil end
        end
        self:RebuildComparisonEntries()
    end
    self:ApplySlotComparisonLayout()
end
