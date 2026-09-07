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
local SPEC_LABELS = { ["Feral dps"] = "Cat DPS", ["Feral tank"] = "Bear Tank" }
local SORT_LABELS = { recommendation = "Recommendations", item = "Item", source = "Source", owned = "Owned", comparison = "Compared with reference" }
local OWNED_ORDER = { equipped = 1, bag = 2, bags = 2, bank = 3 }

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
        origin = origin, rows = {}, entries = {}, contexts = {}, pinned = {}, contentHeight = 1,
        page = 1, scroll = 0, generation = 0, ownership = "all", sort = "recommendation", sortDirection = "asc" }
    local ok, openError = xpcall(function()
        self:CreateSlotComparisonFrame()
        widgets:CloseDropdownMenus()
        self:RenderSlotComparison(true)
    end, function(message) return tostring(message) end)
    if not ok then
        self.comparisonConstructing, self.comparisonLayoutActive = nil, nil
        self.comparisonRenderActive, self.comparisonRenderPending = nil, nil
        if self.comparisonBuildingFrame then
            self.comparisonBuildingFrame:Hide()
            self.comparisonBuildingFrame:ClearAllPoints()
            self.comparisonBuildingFrame:SetParent(nil)
            self.comparisonBuildingFrame, self.comparisonFrame, self.comparisonFrameReady = nil, nil, nil
        end
        self:CloseSlotComparison()
        error(openError, 0)
    end
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

function UI:GetComparisonSpecLabel(spec)
    return SPEC_LABELS[spec] or spec or "Specialization"
end

function UI:GetComparisonSortLabel()
    local state = self.slotComparison or {}
    local phase = state.sort and string.match(state.sort, "^phase:(.+)$")
    return phase and (addon:GetPhaseDisplayName(phase) .. " rating") or SORT_LABELS[state.sort] or SORT_LABELS.recommendation
end

function UI:SetComparisonSpec(spec)
    local state = self.slotComparison
    if not state or state.spec == spec then return false end
    local allowed = false
    for _, candidate in ipairs(addon:GetClassSpecIndex().specsByClass[state.class] or {}) do
        if (type(candidate) == "table" and candidate.name or candidate) == spec then allowed = true end
    end
    if not allowed then return false end
    state.spec, state.detailsOpen, state.selectedItemId, state.scroll = spec, false, nil, 0
    self:ClearSelectedRow()
    self.comparisonScroll:SetVerticalScroll(0)
    self:RefreshComparisonPool(true)
    self:ApplySlotComparisonLayout()
    return true
end

function UI:SetComparisonOwnership(scope)
    local state = self.slotComparison
    if not state or (scope ~= "all" and scope ~= "owned") or state.ownership == scope then return false end
    state.ownership = scope
    self:RebuildComparisonEntries()
    state.scroll = 0
    self.comparisonScroll:SetVerticalScroll(0)
    self:LayoutSlotComparison()
    return true
end

function UI:SetComparisonSort(key)
    local state = self.slotComparison
    if not state or (not SORT_LABELS[key] and not (key and string.match(key, "^phase:"))) then return false end
    if state.sort == key then state.sortDirection = state.sortDirection == "asc" and "desc" or "asc"
    else state.sort, state.sortDirection = key, "asc" end
    self:RebuildComparisonEntries()
    state.scroll = 0
    self.comparisonScroll:SetVerticalScroll(0)
    self:LayoutSlotComparison()
    return true
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
    if type(state.reference) == "table" and state.reference.slotKey or state.reference == nil then state.reference = rows.reference
    else state.reference = rows.reference and (rows.reference.slotKey and rows.reference or rows.reference.item_id) end
    state.pinned = {}
    for _, context in ipairs(state.contexts) do
        local pinned = { item_id = context.item_id, name = context.name, slot = state.slot, context = context, class = state.class, spec = state.spec, phase = state.phase,
            owned_state = "equipped", occupancy = context.occupancy, reference_context = context }
        if context.item_id then pinned.history = addon:GetRecommendationHistory(context.item_id, state.class, state.spec, state.phase, state.slot) end
        state.pinned[#state.pinned + 1] = pinned
    end
    if state.selectedItemId then
        local selected
        for _, row in ipairs(rows) do if row.item_id == state.selectedItemId then selected = row; break end end
        if selected then
            self.selectedItemData = selected
            self.detailsRenderSignature = nil
        else
            state.selectedItemId, state.detailsOpen = nil, false
            self:ClearSelectedRow()
        end
    end
    self:RebuildComparisonEntries()
end

local function ratingBasis(cell)
    if not cell or not cell.matched then return nil end
    local evidence = cell.rating_evidence or cell.evidence or {}
    local ordered = {}
    for _, value in ipairs(evidence) do ordered[#ordered + 1] = value end
    table.sort(ordered, function(a,b) return tostring(a.table_id or "") < tostring(b.table_id or "") end)
    if cell.status ~= "rated" then return nil end
    local first = ordered[1]
    if not first or not first.table_id or not tonumber(first.grade) then return nil end
    local grade = tonumber(first.grade)
    if grade < 1 or grade > 4 then return nil end
    for _, value in ipairs(ordered) do
        if type(value.conditions) == "table" and #value.conditions > 0
            or type(value.conditions) == "string" and value.conditions ~= ""
            or value.table_id == first.table_id and tonumber(value.grade) ~= grade then return nil end
    end
    return { key = tostring(first.table_id) .. ":" .. tostring(cell.phase), phase = cell.phase, grade = grade,
        source_url = first.source_url, heading = first.table_heading }
end

local function comparisonRowGroup(row, state)
    local comparison = row.comparison or {}
    if state.sort == "comparison" or not row.history then
        local first = comparison.evidence and comparison.evidence[1]
        local source = first and first.candidate or {}
        local basis = comparison.basis_key
        return { key = basis or (comparison.relation == "conditional" and "conditional" or "unranked"),
            priority = basis and (comparison.historical and 1 or 0) or 4, basis = basis, phase = comparison.phase,
            grade = supportedCandidateGrade(comparison), source_url = source.source_url,
            title = basis and ((comparison.historical and "Earlier evidence: " or "Shared guide: ") .. addon:GetPhaseDisplayName(comparison.phase)
                .. (source.table_heading and (" · " .. source.table_heading) or ""))
                or (comparison.relation == "conditional" and "Depends on setup" or "No shared rating") }
    end
    local history = row.history
    local requestedPhase = string.match(state.sort or "", "^phase:(.+)$")
    local cell, priority = requestedPhase and history.phases and history.phases[requestedPhase] or history.selected, 0
    if not requestedPhase and (not cell or not cell.matched) then
        cell, priority = history.latest_earlier, 1
        if not cell then
            priority = 2
            for _, future in ipairs(history.phase_cells or {}) do
                if future.matched and phaseIndex(future.phase) > phaseIndex(state.phase) then cell = future; break end
            end
        end
    end
    local basis = ratingBasis(cell)
    local prefix = requestedPhase and "" or priority == 1 and "Earlier recommendations: " or priority == 2 and "Future recommendations: " or "Recommendations: "
    if basis then
        return { key = prefix .. basis.key, basis = basis.key, phase = basis.phase, grade = basis.grade, priority = priority, future = not requestedPhase and priority == 2,
            title = prefix .. addon:GetPhaseDisplayName(basis.phase) .. (basis.heading and (" · " .. basis.heading) or ""), source_url = basis.source_url }
    end
    if cell and cell.matched then
        return { key = "conditional:" .. tostring(cell.phase), phase = cell.phase, priority = priority, conditional = true, future = not requestedPhase and priority == 2,
            title = prefix .. addon:GetPhaseDisplayName(cell.phase) .. " · Conditional recommendations" }
    end
    return { key = "unranked", priority = 4, title = requestedPhase and (addon:GetPhaseDisplayName(requestedPhase) .. " · No recorded rating") or "No recorded recommendation" }
end

function UI:RebuildComparisonEntries()
    local state = self.slotComparison
    if not state then return end
    local groups, ordered = {}, {}
    local ignored = addon:GetCharacterDB().ignoredItems
    local textSort = state.sort == "item" or state.sort == "source" or state.sort == "owned"
    local referenceKey = tostring(referenceId(state.reference)) .. ":" .. state.class .. ":" .. state.spec .. ":" .. state.phase .. ":" .. tostring(addon.CompareRecommendationItems)
    for _, row in ipairs(state.rows) do
        if not ignored[tostring(row.item_id)] and (state.ownership ~= "owned" or row.owned or row.owned_state and row.owned_state ~= "missing") then
        if row.comparisonReferenceKey ~= referenceKey then
            row.comparison = addon:CompareRecommendationItems(row.item_id, referenceId(state.reference), state.class, state.spec, state.phase, state.slot)
            row.comparisonReferenceKey = referenceKey
        end
        row.is_reference = row.item_id == referenceId(state.reference)
        local group = textSort and { key = "all", priority = 0 } or comparisonRowGroup(row, state)
        row.comparisonGrade = group.grade
        local key = group.key
        if not groups[key] then
            group.rows = {}; groups[key] = group; ordered[#ordered + 1] = group
        end
        groups[key].rows[#groups[key].rows + 1] = row
        end
    end
    table.sort(ordered, function(a, b)
        if a.priority ~= b.priority then return a.priority < b.priority end
        if phaseIndex(a.phase) ~= phaseIndex(b.phase) then
            if a.future and b.future then return phaseIndex(a.phase) < phaseIndex(b.phase) end
            return phaseIndex(a.phase) > phaseIndex(b.phase)
        end
        if (a.conditional == true) ~= (b.conditional == true) then return a.conditional ~= true end
        return a.key < b.key
    end)
    local entries, y = {}, 0
    local rowHeight = self:GetDensityMetrics()
    for _, group in ipairs(ordered) do
        table.sort(group.rows, function(a, b)
            local av, bv
            if state.sort == "item" then av,bv = string.lower(itemName(a)), string.lower(itemName(b))
            elseif state.sort == "owned" then av,bv = OWNED_ORDER[a.owned_state] or 4, OWNED_ORDER[b.owned_state] or 4
            elseif state.sort == "source" then
                local ad,bd = a.acquisition_display or {}, b.acquisition_display or {}
                av,bv = string.lower(ad.location_label or ad.source_summary or ad.source_label or ""), string.lower(bd.location_label or bd.source_summary or bd.source_label or "")
            end
            if av ~= nil and av ~= bv then return state.sortDirection == "desc" and av > bv or state.sortDirection ~= "desc" and av < bv end
            if group.basis then
                local ar, br = a.comparisonGrade, b.comparisonGrade
                if (ar ~= nil) ~= (br ~= nil) then return ar ~= nil end
                if ar and br and ar ~= br then return state.sortDirection == "desc" and ar > br or state.sortDirection ~= "desc" and ar < br end
            end
            if string.lower(itemName(a)) ~= string.lower(itemName(b)) then return string.lower(itemName(a)) < string.lower(itemName(b)) end
            return (a.item_id or 0) < (b.item_id or 0)
        end)
        if not textSort then
            entries[#entries + 1] = { kind = "section", title = group.title .. " (" .. #group.rows .. ")", basis = group.basis, source_url = group.source_url, top = y, height = 28 }
            y = y + 28
        end
        for _, row in ipairs(group.rows) do
            entries[#entries + 1] = { kind = "row", data = row, top = y, height = rowHeight }
            y = y + rowHeight
        end
    end
    if #entries == 0 then
        entries[1] = { kind = "empty", title = state.ownership == "owned" and "No owned gear is recorded for this slot. Choose All candidates to browse recommendations."
            or "No recorded recommendations or owned gear for this specialization and slot.", top = 0, height = 56 }
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
    if self.comparisonFrameReady or self.comparisonConstructing then return end
    self.comparisonConstructing = true
    local frame = widgets:CreatePanel(nil, self.body)
    frame:Hide()
    self.comparisonBuildingFrame = frame
    frame:SetAllPoints(self.body); frame:SetFrameLevel(self.body:GetFrameLevel() + 4)
    self.comparisonBackButton = widgets:CreateTextButton(frame, "Back to results", 120, 28, function() self:CloseSlotComparison() end)
    self.comparisonBackButton:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -6)
    self.comparisonTitle = label(frame); self.comparisonTitle:SetPoint("LEFT", self.comparisonBackButton, "RIGHT", 12, 0)
    self.comparisonScope = label(frame); self.comparisonScope:SetPoint("TOPLEFT", self.comparisonBackButton, "BOTTOMLEFT", 0, -6)
    self.comparisonReference = widgets:CreateDropdown("BigBiSListComparisonReference", frame, 240,
        function() return "Reference: " .. self:GetComparisonReferenceLabel(self.slotComparison and self.slotComparison.reference) end,
        function()
            local state, items = self.slotComparison, {}
            if not state then return items end
            for _, context in ipairs(state.contexts or {}) do items[#items + 1] = { value = context, text = self:GetComparisonReferenceLabel(context), checked = state.reference == context } end
            for _, row in ipairs(state.rows or {}) do
                if not addon:GetCharacterDB().ignoredItems[tostring(row.item_id)] then
                    items[#items + 1] = { value = row.item_id, text = itemName(row), checked = state.reference == row.item_id }
                end
            end
            return items
        end, function(value) self:SetComparisonReference(value) end)
    self.comparisonReference:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -58)
    self.comparisonSpec = widgets:CreateDropdown("BigBiSListComparisonSpec", frame, 160,
        function() return "Compare as: " .. self:GetComparisonSpecLabel(self.slotComparison and self.slotComparison.spec) end,
        function()
            local state, items = self.slotComparison, {}
            if state then
                for _, spec in ipairs(addon:GetClassSpecIndex().specsByClass[state.class] or {}) do
                    spec = type(spec) == "table" and spec.name or spec
                    items[#items + 1] = { value = spec, text = self:GetComparisonSpecLabel(spec), checked = spec == state.spec }
                end
            end
            return items
        end, function(value) self:SetComparisonSpec(value) end)
    self.comparisonOwnership = widgets:CreateDropdown("BigBiSListComparisonOwnership", frame, 124,
        function() return self.slotComparison and self.slotComparison.ownership == "owned" and "Owned gear" or "All candidates" end,
        function() return {
            { value = "all", text = "All candidates", checked = self.slotComparison and self.slotComparison.ownership == "all" },
            { value = "owned", text = "Owned gear", checked = self.slotComparison and self.slotComparison.ownership == "owned" },
        } end, function(value) self:SetComparisonOwnership(value) end)
    self.comparisonSort = widgets:CreateDropdown("BigBiSListComparisonSort", frame, 176,
        function() return "Sort: " .. self:GetComparisonSortLabel() end,
        function()
            local items, state = {}, self.slotComparison or {}
            for _, key in ipairs({ "recommendation", "item", "comparison", "source", "owned" }) do
                items[#items + 1] = { value = key, text = SORT_LABELS[key], checked = state.sort == key }
            end
            for _, phase in ipairs(addon:GetPhaseOrder()) do
                items[#items + 1] = { value = "phase:" .. phase, text = addon:GetPhaseDisplayName(phase) .. " rating", checked = state.sort == "phase:" .. phase }
            end
            return items
        end, function(value) self:SetComparisonSort(value) end)
    widgets:BindTooltip(self.comparisonSpec, "Compare recommendations for this specialization. Your character selection stays unchanged.")
    widgets:BindTooltip(self.comparisonOwnership, "Owned gear includes equipment, bags, and the last recorded bank contents.")
    self.comparisonPrev = widgets:CreateUtilityButton(frame, "chevronLeft", 28, function() self:ChangeComparisonPhasePage(-1) end, "Earlier phase columns")
    self.comparisonNext = widgets:CreateUtilityButton(frame, "chevronRight", 28, function() self:ChangeComparisonPhasePage(1) end, "Later phase columns")
    self.comparisonNext:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -10, -58)
    self.comparisonPrev:SetPoint("RIGHT", self.comparisonNext, "LEFT", -6, 0)
    self.comparisonPageLabel = label(frame); self.comparisonPageLabel:SetPoint("RIGHT", self.comparisonPrev, "LEFT", -8, 0)
    self.comparisonHeader = CreateFrame("Frame", nil, frame); self.comparisonHeader:SetHeight(32)
    self.comparisonHeader:SetPoint("TOPLEFT", frame, "TOPLEFT", 8, -96); self.comparisonHeader:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -28, -96)
    self.comparisonHeader.cells, self.comparisonHeader.buttons = {}, {}
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
    self.comparisonFrame, self.comparisonFrameReady = frame, true
    self.comparisonBuildingFrame, self.comparisonConstructing = nil, nil
end

function UI:ChangeComparisonPhasePage(delta)
    local state = self.slotComparison
    if not state then return end
    state.page = math.max(1, math.min(self.comparisonColumns.pages, state.page + delta))
    self:LayoutSlotComparison()
end

function UI:LayoutSlotComparison()
    local state = self.slotComparison
    if not state or not self.comparisonFrameReady or self.comparisonLayoutActive then return end
    self.comparisonLayoutActive = true
    if state.rowHeight ~= self:GetDensityMetrics() then self:RebuildComparisonEntries() end
    local width = math.max(320, self.comparisonFrame:GetWidth() - 36)
    local controls = { self.comparisonReference, self.comparisonSpec, self.comparisonOwnership, self.comparisonSort }
    local x, toolbarY = 8, 58
    for _, control in ipairs(controls) do
        if x > 8 and x + control:GetWidth() > width + 8 then x, toolbarY = 8, toolbarY + 36 end
        control:ClearAllPoints(); control:SetPoint("TOPLEFT", self.comparisonFrame, "TOPLEFT", x, -toolbarY)
        x = x + control:GetWidth() + 8
        control:Refresh()
    end
    self.comparisonNext:ClearAllPoints()
    self.comparisonNext:SetPoint("TOPRIGHT", self.comparisonFrame, "TOPRIGHT", -10, -6)
    self.comparisonHeader:ClearAllPoints()
    self.comparisonHeader:SetPoint("TOPLEFT", self.comparisonFrame, "TOPLEFT", 8, -toolbarY - 38)
    self.comparisonHeader:SetPoint("TOPRIGHT", self.comparisonFrame, "TOPRIGHT", -28, -toolbarY - 38)
    self.comparisonColumns = self:GetComparisonColumns(width)
    local columns, header = self.comparisonColumns, self.comparisonHeader
    local headings = { { text = "Item", column = columns.item, key = "item" }, { text = "Compared with reference", column = columns.evidence, key = "comparison" } }
    local live = addon:GetCurrentPhaseKey()
    for _, column in ipairs(columns.phases) do headings[#headings + 1] = { text = (PHASE_LABELS[column.phase] or column.phase) .. (column.phase == live and "\nLive" or ""), column = column, phase = column.phase, key = "phase:" .. column.phase } end
    headings[#headings + 1] = { text = "Source", column = columns.source, key = "source" }
    headings[#headings + 1] = { text = "Owned", column = columns.owned, key = "owned" }
    for _, text in ipairs(header.cells) do text:Hide() end
    for _, button in pairs(header.buttons) do button:Hide() end
    for index, heading in ipairs(headings) do
        local text = header.cells[index] or label(header); header.cells[index] = text
        local sorting = state.sort == heading.key
        setCell(text, heading.text, heading.column.x, heading.column.width - (sorting and 14 or 0), 32, 2)
        text:SetJustifyH(heading.phase and "CENTER" or "LEFT")
        local selected = heading.phase == state.phase
        text:SetTextColor(selected and .92 or .72, selected and .76 or .75, selected and .32 or .8, 1)
        local button = header.buttons[heading.key]
        if not button then
            button = CreateFrame("Button", nil, header); header.buttons[heading.key] = button
            button.sortIcon = button:CreateTexture(nil, "ARTWORK"); button.sortIcon:SetSize(12,12)
            button.sortIcon:SetPoint("RIGHT", button, "RIGHT", -1, 0)
            button:SetScript("OnClick", function(selfButton) UI:SetComparisonSort(selfButton.sortKey) end)
            button:SetScript("OnEnter", function(selfButton) if selfButton.text then selfButton.text:SetTextColor(.92,.76,.32,1) end end)
            button:SetScript("OnLeave", function(selfButton)
                if selfButton.text and selfButton.textColor then selfButton.text:SetTextColor(unpack(selfButton.textColor)) end
            end)
        end
        button.sortKey, button.text = heading.key, text
        button.textColor = { selected and .92 or .72, selected and .76 or .75, selected and .32 or .8, 1 }
        button:ClearAllPoints(); button:SetPoint("LEFT", header, "LEFT", heading.column.x, 0); button:SetSize(heading.column.width,32)
        widgets:SetIcon(button.sortIcon, state.sortDirection == "desc" and "sortDescending" or "sortAscending")
        button.sortIcon:SetShown(sorting); button:Show()
        widgets:BindTooltip(button, "Sort by " .. (heading.phase and (addon:GetPhaseDisplayName(heading.phase) .. " rating") or heading.text)
            .. ((heading.phase or heading.key == "comparison") and ". Ratings are ordered only within a shared guide table; unresolved entries follow." or ". Click again to reverse."))
    end
    self.comparisonTitle:SetText("Compare " .. state.slot)
    self.comparisonTitle:SetWidth(math.max(60,width - 132 - (columns.pages > 1 and 116 or 290)))
    widgets:SetCellText(self.comparisonScope, "All sources · " .. self:GetComparisonSpecLabel(state.spec) .. " · " .. state.slot .. " · Available through " .. addon:GetPhaseDisplayName(state.phase)
        .. " · " .. (state.ownership == "owned" and "Owned gear" or "All candidates"), 1, 12, width)
    self.comparisonScope:Show()
    self.comparisonReference:Refresh()
    self.comparisonPrev:SetShown(columns.pages > 1); self.comparisonNext:SetShown(columns.pages > 1)
    self.comparisonPrev:SetEnabled(state.page > 1); self.comparisonNext:SetEnabled(state.page < columns.pages)
    self.comparisonPageLabel:ClearAllPoints()
    if columns.pages > 1 then self.comparisonPageLabel:SetPoint("RIGHT", self.comparisonPrev, "LEFT", -8, 0)
    else self.comparisonPageLabel:SetPoint("TOPRIGHT", self.comparisonFrame, "TOPRIGHT", -10, -14) end
    self.comparisonPageLabel:SetText(columns.pages > 1 and (state.page .. " / " .. columns.pages) or "Gold: selected tier · Blue: live · Muted: future")
    widgets:BindTooltip(self.comparisonSort, self:GetComparisonSortLabel() .. (state.sortDirection == "desc" and " · Descending" or " · Ascending"))
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
    if not state or not self.comparisonFrameReady or not self.comparisonScroll or not self.comparisonColumns then return end
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
    if not state or not self.comparisonFrameReady then return false end
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
    if not self.slotComparison or self.comparisonConstructing then return end
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
    if state.detailsOpen and state.selectedItemId then
        self:RefreshDetails(state.selectedItemId, self.selectedItemData, "comparison")
    end
end
