-- Virtual rows for the complete, pre-ranked Forever Guide.
local addon, UI = BigBiSList, BigBiSList.UI
local rating = addon.ForeverGearRating
if not rating then return end

local function any(values)
    for _, active in pairs(values or {}) do if active then return true end end
end

local function filtered(filters)
    if filters.search and filters.search ~= "" or filters.hideIgnored and next(filters.ignoredItems or {}) then return true end
    for _, name in ipairs({"sourceType", "zone", "cost", "vendor", "reputation", "ownedState", "binding", "boe",
        "recommendationCategory", "rankGroup", "longevity"}) do
        local value = filters[name]
        if value and value ~= "all" and value ~= "any" then return true end
    end
    for _, name in ipairs({"sourceTypes", "zones", "costs", "vendors", "reputations", "rankGroups"}) do
        if any(filters[name]) then return true end
    end
end

local function slotSelected(filters, slot)
    return not any(filters.slots) or filters.slots[slot]
        or slot == "Two Hand" and filters.slots["Main Hand"]
end

local function oneRow(context, filters, slot, ordinal, match)
    return addon:GetPackedGuideRow(context, slot, ordinal, filters, match)
end

local function append(bucket, row)
    bucket.rows[#bucket.rows + 1] = row
    bucket.positions[row.stat_identity] = #bucket.rows
end

local function locateAt(span, index)
    if not index or index < 1 or index > span.count then return end
    local top = span.top + span.rowHeight * (index - 1)
    return {top = top, bottom = top + span.rowHeight}
end

function UI:RequestPackedReach(context, filters)
    local player, owned = addon:GetTooltipPlayerContext(), self.currentOwned
    if not player or player.class ~= context.class or player.spec ~= context.spec or player.level ~= context.level or not owned then return end
    local current = self.packedReach
    if current and current.context == context and current.filters == filters and current.owned == owned and current.questRevision == self.questRevision
        and not (current.job and current.job.cancelled) then return current.result end
    local questItems = BigBiSListData.guide_index.quests or {}
    if self.questLogSignature == nil and self.QuestStateChanged then self:QuestStateChanged() end
    local prior = current and current.context == context and current.filters == filters and current.result
    local request = {context = context, filters = filters, owned = owned, questRevision = self.questRevision, result = prior}
    self.packedReach = request
    request.job = rating:QueueWork(1, function(checkpoint)
        local keys, rows = {}, {}
        for _, entry in ipairs(owned.gearCopies or {}) do
            checkpoint()
            if entry.state == "bag" then
                local key = rating:NormalizeLink(entry.item_id, entry.item_link) or tostring(entry.item_id)
                keys[key] = true
            end
        end
        local function addQuest(questId)
            for _, key in ipairs(questItems[questId] or {}) do keys[key] = true end
        end
        if self.activeQuestIds then
            for _, id in ipairs(self.activeQuestIds) do addQuest(id) end
        elseif C_QuestLog and C_QuestLog.IsOnQuest then
            for id in pairs(questItems) do
                checkpoint()
                local ok, active = pcall(C_QuestLog.IsOnQuest, id)
                if ok and addon.IsReadableValue(active) and active == true then addQuest(id) end
            end
        end
        local slots = rating:GetPackedGuide(context)
        for _, slot in ipairs(addon.slotOrder) do
            local info = slotSelected(filters, slot) and slots[slot]
            if info then
                for key in pairs(keys) do
                    checkpoint()
                    local ordinal = info.indices.lookup[key]
                    local row = ordinal and oneRow(context, filters, slot, ordinal, true)
                    if row then rows[#rows + 1] = row end
                end
            end
        end
        return self:GetWithinReach(rows) or {}
    end, function()
        return self.packedReach == request and self.frame and self.frame:IsShown() and self.currentFilterPayload == filters
            and self:GetViewKey() == "gearGuide"
    end, function(result)
        request.job, request.result = nil, result
        local function signature(groups)
            local values = {}
            for index, group in ipairs(groups or {}) do
                for _, action in ipairs(group) do
                    values[#values + 1] = table.concat({index, action.row.stat_identity, action.swap.delta,
                        action.quest and self:GetQuestStepText(action.quest) or ""}, "/")
                end
            end
            table.sort(values)
            return table.concat(values, "/")
        end
        if signature(prior) ~= signature(result) then self:ScheduleRefresh(nil, "gear within reach") end
    end)
    return prior
end

function UI:BuildPackedGuideModel(context, filters, title, query, defaultOrder, reach)
    local model = self:NewListRenderModel()
    model.packed, model.guideContext, model.guideFilters = true, context, filters
    local spans = {}
    local packed = rating:GetPackedGuide(context)
    local grouping = self:GetViewState().groupBy or "slot"
    local reversed = self:GetViewState().sort == "priority" and self:GetViewState().sortDirection == "desc"
    self:AddListRenderEntry(model, {kind = "note", text = title, height = 22})
    if query and query.pendingSort then
        self:AddListRenderEntry(model, {kind = "note", text = "Comparing upgrades…", height = 22})
    end
    if reach then self:AddWithinReach(model, nil, "guide", reach) end
    local function spanFor(slot, info, bucket)
        local count = bucket and #bucket.rows or info.count
        if count == 0 then return end
        if grouping == "slot" then
            self:AddListSection(model, slot, "leveling", nil, slot)
            if not model.activeSection.collapsed then self:AddGuideEquippedRows(model, slot) end
        end
        local cached, cachedCount = {}, 0
        local span = {key = slot, bucket = bucket, data = info}
        span.get = function(position)
            local key = reversed and count - position + 1 or position
            local row = cached[key]
            if row then return row end
            local member = bucket and bucket.rows[key]
            local ordinal = member and member.ordinal or rating:GetPackedBrowseOrdinal(info, context.level, key)
            row = ordinal and oneRow(context, filters, slot, ordinal, bucket ~= nil)
            if row then
                if cachedCount >= 64 then cached, cachedCount = {}, 0 end
                cached[key], cachedCount = row, cachedCount + 1
            end
            return row
        end
        self:AddListSpan(model, span, count)
        if span.top then spans[slot] = span end
        model.activeSection = nil
        if grouping == "slot" then self:AddListGap(model, 6) end
    end
    for _, slot in ipairs(addon.slotOrder) do
        local info = slotSelected(filters, slot) and packed[slot]
        local bucket = query and query.slots and query.slots[slot]
        if info and (bucket or defaultOrder) then spanFor(slot, info, bucket) end
    end
    local function parse(key)
        if key then return key:match("^item\031%d+\031([^\031]+)\031(.+)$") end
    end
    model.rebind = function(key)
        local slot, identity = parse(key)
        local span = spans[slot]
        if not span then return end
        if span.bucket then
            local position = span.bucket.positions[identity]
            return position and span.get(position)
        end
        local ordinal = span.data.indices.lookup[identity]
        return ordinal and oneRow(context, filters, slot, ordinal, false)
    end
    model.locate = function(navigation)
        local slot, key = parse(navigation.anchorKey)
        local section = spans[slot]
        if not section then return end
        if section.bucket and section.bucket.positions[key] then return locateAt(section, section.bucket.positions[key]) end
        if not section.bucket and navigation.anchorSpan and navigation.anchorSpan.data == section.data then
            return locateAt(section, navigation.anchorIndex)
        end
        -- When an item has gone, the closest position in the same slot survives.
        if navigation.anchorIndex then return locateAt(section, math.min(section.count, navigation.anchorIndex)) end
    end
    return model
end

function UI:RefreshPackedRows(itemId, quest)
    local model = self.renderModel
    if not (model and model.packed and self.frame and self.frame:IsShown()) then return false end
    local pending = {}
    for _, frame in ipairs(self.activeRenderFrames or {}) do
        local entry = frame.__bigBisBoundRenderEntry
        local data = entry and entry.data
        if data and ((itemId and data.item_id == itemId) or (quest and data.matched_access_option
            and data.matched_access_option.source_type == "quest")) then
            pending[#pending + 1] = {frame = frame, token = frame.bindToken, entry = entry}
        end
    end
    local details = self:IsInspectorVisible() and (quest or self.selectedItemId == itemId)
    if #pending == 0 and not details and not quest then return true end
    local function current() return self.renderModel == model and self.frame:IsShown() end
    rating:QueueWork(1, function(checkpoint)
        for _, row in ipairs(pending) do
            checkpoint()
            if row.frame.bindToken == row.token and self:IsCurrentRenderFrame(row.frame) then
                local entry = row.entry
                self:CreateDataRow(row.frame:GetParent(), -entry.top, entry.data, entry.mode, row.frame, entry.rowHeight)
            end
        end
        if details and current() and self:IsInspectorVisible() then
            self:RefreshDetails(self.selectedItemId, self.selectedItemData, self.selectedItemMode)
        end
    end, current)
    if quest and self.currentFilterPayload == model.guideFilters then
        self:RequestPackedReach(model.guideContext, model.guideFilters)
    end
    return true
end

function UI:RequestPackedGuideRows(context, filters, buildActivities, needsPersonalSort, onlyChanged)
    local state = self:GetViewState()
    local grouping = buildActivities and "activities" or (state.groupBy or "slot")
    local sortKey, direction = state.sort, state.sortDirection
    local identity = table.concat({"packed-guide", context.key, grouping, sortKey or "", direction or "",
        onlyChanged and "changed" or ""}, ":")
    local query = self:GetCachedViewQuery(identity, function() return {running = false} end)
    if query.job and query.job.cancelled then query.running, query.job = false, nil end
    if query.running or query.slots then return query end
    local cache = self.currentViewQueryCache
    local player = addon:GetTooltipPlayerContext()
    local owned = self.currentOwned
    local packed = rating:GetPackedGuide(context)
    local search = filters.search and filters.search:lower()
    local function current()
        return self.currentViewQueryCache == cache and cache[identity] == query
            and self.frame and self.frame:IsShown() and self:GetViewKey() == "gearGuide"
            and (buildActivities or state.sort == sortKey and state.sortDirection == direction)
    end
    query.running, query.pendingSort = true, needsPersonalSort
    query.job = rating:QueueWork(2, function(checkpoint)
        local result = {slots = {}, groups = {}}
        local verifiedOnly = buildActivities
        local evaluation = player and math.max(player.level, context.level)
        local personal = needsPersonalSort and player and player.spec and player.class == context.class
            and rating:GetContext(player.class, player.spec, evaluation == 60 and "PR" or "LEVELING", evaluation, owned)
        for _, slot in ipairs(addon.slotOrder) do
            local changed = context.catalog.changedSlots
            local data = (not onlyChanged or changed[slot]) and slotSelected(filters, slot) and packed[slot]
            if data then
                local bucket, ranked = {rows = {}, positions = {}}, {}
                rating:VisitPackedGuideOrdinals(data, context.level, search, verifiedOnly, function(ordinal)
                    local row = oneRow(context, filters, slot, ordinal, true)
                    if row then
                        if personal and row.stat_rank then
                            local item = row.stat_rank.item
                            if evaluation >= (item.level or 100) then
                                local swap = rating:GetOwnedOpportunity(personal, item, row.item_link, evaluation == player.level, true)
                                row.packedGain = rating:ReliableGain(swap)
                            end
                        end
                        if buildActivities then
                            ranked[#ranked + 1] = row
                        else
                            local sortValue
                            if sortKey and sortKey ~= "best_upgrade" and sortKey ~= "priority" and sortKey ~= "stat_rank" then
                                sortValue = self:GetDisplaySortValue(row, sortKey, "leveling")
                            end
                            ranked[#ranked + 1] = {ordinal = ordinal, stat_identity = row.stat_identity, name = row.name,
                                rank = row.stat_rank.rank, guide_order = row.guide_order, guide_route_level = row.guide_route_level,
                                packedGain = row.packedGain, sortValue = sortValue}
                        end
                    end
                end, checkpoint)
                -- Filtered searches arrive in ordinal order. Apply the selected display sort
                -- after the query has established the full set of matching rows.
                if onlyChanged or needsPersonalSort or search and search ~= "" or sortKey then
                    ranked = rating:SortInWork(ranked, function(a, b)
                        if needsPersonalSort and a.packedGain ~= b.packedGain then
                            if not a.packedGain or not b.packedGain then return a.packedGain ~= nil end
                            if direction == "asc" then return a.packedGain < b.packedGain end
                            return a.packedGain > b.packedGain
                        end
                        local av, bv = a.sortValue, b.sortValue
                        if av ~= bv then
                            if direction == "desc" then return av > bv end
                            return av < bv
                        end
                        if a.guide_order ~= b.guide_order then return a.guide_order < b.guide_order end
                        if a.guide_route_level ~= b.guide_route_level then
                            if a.guide_order == 3 then return a.guide_route_level > b.guide_route_level end
                            return a.guide_route_level < b.guide_route_level
                        end
                        local ar, br = a.rank or math.huge, b.rank or math.huge
                        if ar ~= br then
                            if sortKey == "stat_rank" and direction == "desc" then return ar > br end
                            return ar < br
                        end
                        if a.name ~= b.name then return a.name < b.name end
                        return a.stat_identity < b.stat_identity
                    end, checkpoint)
                end
                for _, row in ipairs(ranked) do checkpoint(); append(bucket, row) end
                result.slots[slot] = bucket
                result.groups[#result.groups + 1] = {slot = slot, items = bucket.rows}
            end
        end
        if buildActivities then
            result.activities = self:BuildLevelingActivities(result.groups, self:GetSelection(), context.level, filters, true, checkpoint)
            result.activities.context = context
        end
        return result
    end, current, function(result)
        query.running, query.pendingSort, query.job = false, nil, nil
        query.slots, query.groups, query.activities = result.slots, result.groups, result.activities
        self:ScheduleRefresh(nil, needsPersonalSort and "upgrade order ready" or "gear results ready")
    end)
    return query
end

function UI:RenderPackedGuide(context, filters, title)
    local state = self:GetViewState()
    local activity = self:IsLevelingActivityView()
    local personal = not activity and state.sort == "best_upgrade"
    local isFiltered = filtered(filters)
    local defaultOrder = not isFiltered and (not state.sort or state.sort == "priority" or state.sort == "stat_rank" and state.sortDirection ~= "desc")
    local changed = context.catalog.changedSlots and next(context.catalog.changedSlots)
    local needsQuery = activity or isFiltered or personal or not defaultOrder or changed
    local query = needsQuery and self:RequestPackedGuideRows(context, filters, activity, personal,
        defaultOrder and not (activity or personal) and changed)
    if activity and query and query.running and state.activitySort and state.activitySort ~= "most_loot" then
        query.pendingSort = true
    end
    local reach = self:RequestPackedReach(context, filters)
    if activity and query and query.activities then
        self:RenderLevelingActivities(query.groups, self:GetSelection(), context.level, filters,
            "No activities match this level and filters.", title, true, query.activities, reach)
        return
    end
    if query and not query.slots then
        if self.renderModel and self.renderModel.contextKey == self:GetNavigationContextKey() and not self.pendingNavigation then
            if query.pendingSort and self.resultCountText then
                self.resultCountText:SetText(self.renderModel.rowCount .. " results · Comparing upgrades…")
            end
            return
        end
        if isFiltered then
            if not self.renderModel or self.renderModel.contextKey ~= self:GetNavigationContextKey() then
                self:RenderEmpty(title .. "\n\nFinding gear…")
            end
            return
        end
    end
    local model = self:BuildPackedGuideModel(context, filters, title, query,
        defaultOrder or needsQuery and not isFiltered and not query.slots, reach)
    if model.rowCount == 0 and not activity then self:RenderEmpty(title .. "\n\nNo gear matches this level and filters."); return end
    self:RenderListModel(model)
end

function UI:GetPackedFilterAvailability(selection, phase, filters)
    local context = self:GetNavigationContextKey()
    local cached = self.lastPackedFacetContext == context and self.lastPackedFilterAvailability
        or {sourceTypes = {}, zones = {}, costs = {}, vendors = {}, reputations = {}, costLabels = {}, vendorLabels = {}}
    if self.facetWorker and self.facetWorker.cancelled then self.facetWorker = nil end
    if not self.filterDrawerOpen or self.facetWorker then return cached end
    local version = self.domainVersions and self.domainVersions.availability
    local function current()
        return self.frame and self.frame:IsShown() and self.filterDrawerOpen and self:GetNavigationContextKey() == context
            and (self.domainVersions and self.domainVersions.availability) == version
    end
    self.facetWorker = rating:QueueWork(2, function()
        return addon:GetFilterAvailabilitySnapshot(selection.class, selection.spec, phase, selection.tab, filters)
    end, current, function(snapshot)
        self.facetWorker = nil
        self.currentAvailabilitySnapshot, self.lastPackedFilterAvailability, self.lastPackedFacetContext = snapshot, snapshot, context
        for _, control in ipairs({self.sourceDropdown, self.zoneDropdown, self.costDropdown, self.vendorDropdown, self.reputationDropdown}) do
            if control.RefreshOpenMenu then control:RefreshOpenMenu() end
        end
    end)
    return cached
end
