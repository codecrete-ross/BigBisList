-- Browse personally useful targets. Exact lookups share the full reference ranking.
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

-- Stored gear competes within one legal slot group. A worn change can also change
-- another slot's set bonuses, caps or talent conversions, so score that setup afresh.
function UI:GetGuideStorageChanges(previous, owned)
    local model = self.renderModel
    local query = model and model.targetQuery
    if not query or not query.done or query.owned ~= previous or previous.bagsIncomplete ~= owned.bagsIncomplete
        or previous.inventoryIncomplete ~= owned.inventoryIncomplete then return end
    for _, def in ipairs(addon:GetEquipmentSlotDefinitions()) do
        local old, new = previous.equippedSlots[def.key], owned.equippedSlots[def.key]
        if (old and old.item_link) ~= (new and new.item_link) or (old and old.item_id) ~= (new and new.item_id)
            or previous.unreadableEquipmentSlots[def.key] ~= owned.unreadableEquipmentSlots[def.key] then return end
    end
    local counts, changed = {}, {}
    local checkpoint = rating:GetWorkCheckpoint()
    local function count(snapshot, sign)
        for _, entry in ipairs(snapshot.gearCopies or {}) do
            if checkpoint then checkpoint() end
            local key = table.concat({entry.state, entry.item_id, entry.item_link or ""}, "\031")
            local record = counts[key] or {id = entry.item_id, count = 0}
            counts[key], record.count = record, record.count + sign
        end
    end
    count(previous, -1)
    count(owned, 1)
    for _, record in pairs(counts) do
        if checkpoint then checkpoint() end
        if record.count ~= 0 then
            local item = model.guideContext.catalog.items[tostring(record.id)]
            if not item then return end
            local slot = item.slot
            if slot == "Two Hand" or slot == "One Hand" or slot == "Main Hand" or slot == "Off Hand" then
                changed["Two Hand"], changed["Main Hand"], changed["Off Hand"] = true, true, true
            else changed[slot] = true end
        end
    end
    return {query = query, changed = changed, owned = owned}
end

function UI:RequestPackedReach(context, filters)
    local player, owned = addon:GetTooltipPlayerContext(), self.currentOwned
    if not player or player.class ~= context.class or player.level ~= context.level or not owned then return end
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

local guideExplanation = "Compares equipped gear, bags, and your last readable bank scan. Reviewed utility shows what the item does for your spec."
local slotNouns = { Head = "helm", Shoulder = "shoulder", Feet = "boot", Hands = "glove", Legs = "leg",
    ["Two Hand"] = "two-handed weapon", ["Main Hand"] = "main-hand", ["Off Hand"] = "off-hand" }

function UI:BuildPackedGuideModel(context, filters, title, query, reach)
    local model = self:NewListRenderModel()
    model.packed, model.guideContext, model.guideFilters = true, context, filters
    local spans, empty = {}, {}
    self:AddListRenderEntry(model, {kind = "note", text = title, height = 22, tooltip = guideExplanation})
    if query.lookupReason then self:AddListRenderEntry(model, {kind = "note", text = query.lookupReason, height = 24}) end
    if reach then self:AddWithinReach(model, nil, "guide", reach) end
    local grouped = (self:GetViewState().groupBy or "slot") == "slot"
    for _, slot in ipairs(addon.slotOrder) do
        local bucket = query.slots[slot]
        if bucket and #bucket.rows > 0 then
            if grouped then self:AddListSection(model, slot, "leveling", nil, slot) end
            local span = {key = slot, bucket = bucket, get = function(i) return bucket.rows[i] end}
            self:AddListSpan(model, span, #bucket.rows)
            if span.top then spans[slot] = span end
            model.activeSection = nil
            if grouped then self:AddListGap(model, 6) end
        elseif bucket and query.done and not query.search and not query.reference then
            local notice
            if bucket.unknown then notice = slot .. " · Some items couldn’t be compared"
            elseif filtered(filters) then notice = "No upgrades match these filters · " .. slot
            else notice = "No known " .. (slotNouns[slot] or slot:lower()) .. " upgrades at Level " .. context.level end
            if bucket.best and bucket.best ~= "" then notice = notice .. " · Best owned · " .. bucket.best end
            empty[#empty + 1] = notice
        end
    end
    if #empty > 0 then
        local section = #empty > 1 and model.rowCount > 0 and self:AddListSection(model, "Other slots", nil, true, "guide-empty-slots")
        if section then section.count = #empty end
        if not section or not section.collapsed then
            for _, notice in ipairs(empty) do self:AddListRenderEntry(model, {kind = "note", text = notice, height = 28}) end
        end
        model.activeSection = nil
    end
    if not query.done or (query.unknown and model.rowCount > 0) or (model.rowCount == 0 and #empty == 0) then
        local message = not query.done and "Comparing gear…" or query.unknown and "Some items couldn’t be compared"
            or "No gear matches this level and filters."
        self:AddListRenderEntry(model, {kind = "note", text = message, height = 22})
    end
    local function parse(key)
        if key then return key:match("^item\031%d+\031([^\031]+)\031(.+)$") end
    end
    model.rebind = function(key)
        local slot, identity = parse(key)
        local bucket = query.slots[slot]
        local found = bucket and bucket.rows[bucket.positions[identity]]
        if not found and self.selectedItemData and self:IsInspectorVisible() and query.owned == self.currentOwned
            and self.selectedItemData.targetVerdict and self.selectedItemData.stat_identity == identity then
            local copy = {}
            for k, v in pairs(self.selectedItemData) do copy[k] = v end
            copy.targetVerdict = rating:GetGuideTargetVerdict(copy, context, addon:GetTooltipPlayerContext(), self.currentOwned, copy.exactLookup)
            found = copy
        end
        return found
    end
    model.locate = function(navigation)
        local slot, key = parse(navigation.anchorKey)
        local span = spans[slot]
        if not span and slot then
            local first
            for index, name in ipairs(addon.slotOrder) do if name == slot then first = index; break end end
            for distance = 1, first and #addon.slotOrder or 0 do
                span = spans[addon.slotOrder[first + distance]]
                if span then return locateAt(span, 1) end
                span = spans[addon.slotOrder[first - distance]]
                if span then return locateAt(span, span.count) end
            end
        end
        if not span then return end
        local position = span.bucket.positions[key]
        if position then return locateAt(span, position) end
        if navigation.anchorIndex then return locateAt(span, math.min(span.count, navigation.anchorIndex)) end
    end
    return model
end

function UI:RefreshPackedRows(itemId, quest)
    local model = self.renderModel
    if not (model and model.packed and self.frame and self.frame:IsShown()) then return false end
    if model.targetQuery then
        local changed, bundle = {}, BigBiSListData.guide_index
        local function mark(key)
            for slot, indices in pairs(bundle.slots) do
                if indices.lookup[key] then changed[slot] = true end
            end
        end
        if itemId then
            local facts = model.guideContext.catalog.items[tostring(itemId)]
            if facts then
                if facts.slot == "One Hand" then changed["Main Hand"], changed["Off Hand"] = true, true
                else changed[facts.slot] = true end
            end
        end
        for id in pairs(quest and self.changedGuideQuests or {}) do
            for _, key in ipairs(bundle.quests[id] or {}) do mark(key) end
        end
        if next(changed) then
            local pending = self.targetRetry
            if pending and pending.query == model.targetQuery then
                for slot in pairs(pending.changed) do changed[slot] = true end
            end
            self.targetRetry = {query = model.targetQuery, changed = changed, filters = model.guideFilters}
            self.targetRevision = (self.targetRevision or 0) + 1
            local reason = quest and "quest targets" or "item stats ready"
            self:Invalidate("availability", reason)
            self.facetWorker = nil
            self:ScheduleRefresh(nil, reason)
            return true
        end
    end
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

local function newBucket()
    return {rows = {}, positions = {}, rewards = {}}
end

local function questAvailable(option)
    local source = option.source
    if source and source.type == "quest" and not source.repeatable then
        local id = source.quest_id or source.entity_id
        return not id or UI:GetAcquisitionQuestState(id) ~= "Completed"
    end
    return true
end

local function rewardKey(row, context)
    local base = context.catalog.items[tostring(row.item_id)]
    if base and base.has_random_stats then
        if row.name ~= base.name then row.targetRoll = row.name:sub(#base.name + 2) end
        return tostring(row.item_id)
    end
    return row.stat_identity
end

local function visible(verdict)
    return verdict.kind == "upgrade" or verdict.kind == "utility" or verdict.kind == "reference"
end

local function visitTargets(context, data, filters, search, player, owned, checkpoint, visit)
    local seen = {}
    -- The shipped page already applies slot, class, race, faction, level and phase.
    -- The live access check still handles finished quests and alternative routes.
    local matchFilters = filtered(filters) == true
    local matches = search and rating:GuideSearchPredicate(data.indices, search)
    local last = search and addon.maxLevelingLevel or context.level
    for level = context.level, last do
        local page = rating:GetGuideTargetPage(data, level)
        for index = 1, page and page.count or 0 do
            checkpoint()
            local ordinal = page.at(index)
            if not seen[ordinal] and (not matches or matches(ordinal)) then
                local row = addon:GetPackedGuideRow(context, data.slot, ordinal, filters, matchFilters, level)
                local access = row and row.acquisition_display
                if access and access.status == "ready" and access.source_match then
                    seen[ordinal] = true
                    checkpoint()
                    row.targetVerdict = rating:GetGuideTargetVerdict(row, context, player, owned)
                    visit(row, level)
                end
            end
        end
    end
end

local function better(row, old)
    if not old then return true end
    local a, b = row.targetVerdict.gain, old.targetVerdict.gain
    if a ~= b then return a ~= nil and (b == nil or a > b) end
    return (row.stat_rank.rank or math.huge) < (old.stat_rank.rank or math.huge)
end

local function keep(bucket, row, key)
    local index = bucket.rewards[key]
    if index then
        if better(row, bucket.rows[index]) then
            bucket.positions[bucket.rows[index].stat_identity] = nil
            bucket.rows[index], bucket.positions[row.stat_identity] = row, index
        end
    else
        append(bucket, row)
        bucket.rewards[key] = #bucket.rows
    end
end

local function activityEntry(activities, name)
    if name == "Deadmines" then name = "The Deadmines" end
    local dest = activities.byName[name]
    if not dest then
        dest = newBucket()
        dest.name, dest.items, dest.itemCount, dest.upcoming = name, {}, 0, {}
        activities.byName[name] = dest
        activities.ordered[#activities.ordered + 1] = dest
    end
    return dest
end

local function activityLoot(dest, key)
    if not dest.items[key] then dest.items[key], dest.itemCount = true, dest.itemCount + 1 end
end

local function finishActivities(query, player, context, checkpoint)
    local activities = query.activities
    for _, slot in ipairs(addon.slotOrder) do
        local bucket = query.slots[slot]
        for _, part in ipairs(bucket and bucket.activities.ordered or {}) do
            local dest = activityEntry(activities, part.name)
            for key in pairs(part.items) do checkpoint(); activityLoot(dest, key) end
            for _, row in ipairs(part.rows) do checkpoint(); keep(dest, row, rewardKey(row, context)) end
            dest.unknown = dest.unknown or part.unknown
        end
    end
    local batch = {totals = {}, playerLevel = player and player.level, spec = context.spec}
    local kept = {}
    for _, dest in ipairs(activities.ordered) do
        if #dest.rows > 0 or dest.unknown then
            kept[#kept + 1] = dest
            local total = {upgrades = 0, bestGain = 0, unknown = dest.unknown, unconfirmed = #dest.rows == 0}
            for _, row in ipairs(dest.rows) do
                checkpoint()
                local gain = row.targetVerdict.gain
                if gain then
                    total.upgrades = total.upgrades + 1
                    if gain > total.bestGain or gain == total.bestGain and row.name < total.bestName then
                        total.bestName, total.bestGain = row.name, gain
                    end
                end
            end
            batch.totals[dest] = total
        else activities.byName[dest.name] = nil end
    end
    activities.ordered, activities.batch = kept, batch
    activities.reference, activities.unknown = query.reference, query.unknown
end

local function targetSort(ui, rows, state, checkpoint)
    local sort, direction = state.sort, state.sortDirection
    return rating:SortInWork(rows, function(a, b)
        if a.guide_route_level ~= b.guide_route_level then return a.guide_route_level < b.guide_route_level end
        if sort == "best_upgrade" then
            local left, right = a.targetVerdict.gain, b.targetVerdict.gain
            if left ~= right then
                if not left or not right then return left ~= nil end
                if direction == "asc" then return left < right end
                return left > right
            end
        elseif sort and sort ~= "priority" and sort ~= "stat_rank" then
            local left, right = ui:GetDisplaySortValue(a, sort, "leveling"), ui:GetDisplaySortValue(b, sort, "leveling")
            if left ~= right then
                if direction == "desc" then return left > right end
                return left < right
            end
        end
        local left, right = a.stat_rank.rank or math.huge, b.stat_rank.rank or math.huge
        if left ~= right then
            if (sort == "priority" or sort == "stat_rank") and direction == "desc" then return left > right end
            return left < right
        end
        if a.name ~= b.name then return a.name < b.name end
        return a.stat_identity < b.stat_identity
    end, checkpoint)
end

local function exactLookup(context, slot, ordinal, key, search, filters, player, owned)
    local id = tonumber(search:match("item:(%d+)"))
    local native = id and rating:GetTooltipItem(id, search)
    local item = native and native.facts or context.catalog.items[key]
    if not item then return end
    local lookup = {class = context.class, level = context.level, race = context.race, faction = context.faction, _leveling = true}
    local row = ordinal and addon:GetPackedGuideRow(context, slot, ordinal, lookup, false, context.level)
    if not row then
        row = {item_id = item.id, variant_id = item.variant_id, item_link = item.variant_link, name = item.name,
            class = context.class, spec = context.spec, slot = slot, stat_identity = key, leveling = true,
            guide_route_level = math.max(context.level, item.level or 0),
            stat_rank = rating:GetPackedGuideEntry(context, slot, key, context.level) or
                {item = item, slot = slot, spec = context.spec, level = context.level, phase = "LEVELING",
                status = item.has_random_stats and "unavailable" or "incompatible"}}
        row.acquisition_display = addon:GetRowAcquisitionDisplay(row, lookup, "LEVELING", true, true)
        row.matched_access_option = row.acquisition_display.option
    end
    if search:find("item:", 1, true) then row.item_link = search end
    row.exactLookup = true
    row.targetVerdict = rating:GetGuideTargetVerdict(row, context, player, owned, true)
    lookup._guideTarget = true
    lookup.level = row.guide_route_level or context.level
    local display = addon:GetRowAcquisitionDisplay(row, lookup, "LEVELING", true, true)
    local later, hasTarget
    if not display.option then
        local levels, options = addon:GetGuideRouteTransitions(item.id)
        for _, option in ipairs(options or {}) do
            if addon:IsGuideTargetRoute(option) then hasTarget = true; break end
        end
        if hasTarget then
            for _, at in ipairs(levels) do
                if at > lookup.level then
                    lookup.level = at
                    display = addon:GetRowAcquisitionDisplay(row, lookup, "LEVELING", true, true)
                    if display.option then later = at; break end
                end
            end
        end
    end
    if display.option then row.acquisition_display, row.matched_access_option = display, display.option end
    lookup.level, lookup._questAvailable = context.level, filters._questAvailable
    local route = addon:GetMatchingRowAccessOption(row, lookup, "LEVELING", false, true)
    if item.has_random_stats then row.lookupReason = "Look up the exact roll to compare its stats."
    elseif not route then
        local option = row.matched_access_option
        local source = option and option.source
        row.lookupReason = source and source.type == "quest" and not questAvailable(option)
                and ("Quest already completed · " .. (source.entity_name or row.name))
            or later and ((source and source.type == "quest" and "Quest available at Level " or "Available at Level ") .. later)
            or not hasTarget and option and option.source_type == "trade" and "Only known source · Trade or Auction House"
            or option and option.source_type == "world_drop" and "World drop · No known farming spot"
            or row.guide_route_level > context.level and ("Available at Level " .. row.guide_route_level)
            or row.stat_rank.status == "incompatible" and "No ranking for this spec at this level" or "No available farming route at this level"
    elseif row.targetVerdict.kind == "hidden" and row.targetVerdict.swap.status ~= "best_owned" then
        row.lookupReason = "Gear you own is as good or better."
    end
    return row
end

function UI:RequestPackedGuideRows(context, filters, activity)
    local state = self:GetViewState()
    local key = table.concat({"targets", context.key, activity and "activities" or "items", state.sort or "", state.sortDirection or "",
        self.targetRevision or 0, context.catalog.observedVersion or 0}, "/")
    local query = self:GetCachedViewQuery(key, function() return {slots = {}} end)
    if query.done or query.job and not query.job.cancelled then return query end
    local cache, player, owned = self.currentViewQueryCache, addon:GetTooltipPlayerContext(), self.currentOwned
    local packed = rating:GetPackedGuide(context)
    local scoped = {}
    for k, v in pairs(filters) do scoped[k] = v end
    scoped._guideTarget, scoped.class, scoped.race, scoped.faction = true, context.class, context.race, context.faction
    query.reference = not player or player.class ~= context.class
    if not query.reference then scoped._questAvailable = questAvailable end
    local search = (filters.search or ""):match("^%s*(.-)%s*$")
    query.search = search ~= "" and search or nil
    scoped.search = query.search
    query.activities = activity and {ordered = {}, byName = {}, context = context, targets = true}
    query.context, query.sort, query.direction, query.owned = context, state.sort, state.sortDirection, owned
    local retry = self.targetRetry
    if retry and (not retry.query.done or retry.query.context ~= context or query.search or
        retry.query.activities and not activity or activity and not retry.query.activities or retry.query.sort ~= state.sort
        or retry.query.direction ~= state.sortDirection or retry.filters ~= filters and retry.owned ~= owned) then retry = nil end
    self.targetRetry = nil
    local function current()
        return self.currentViewQueryCache == cache and cache[key] == query and self.frame and self.frame:IsShown()
            and self:GetViewKey() == "gearGuide" and self:IsLevelingActivityView() == activity
            and state.sort == query.sort and state.sortDirection == query.direction
            and self.targetRevision == query.revision
    end
    query.revision = self.targetRevision
    local priming = not self.renderModel or not self.renderModel.targetQuery
    local function publishFirst()
        if not query.first then
            query.first = true
            if not priming then
                if self.renderModel and self.renderModel.targetQuery == query and self.renderModel.paintTargets then
                    self:UpdateVirtualList(true)
                else self:ScheduleRefresh(nil, "first gear targets") end
            end
        end
    end
    query.job = rating:QueueWork(1, function(checkpoint)
        -- A cold overview can publish all destination loot counts from the shipped pages.
        if activity and not filtered(filters) then
            local preview = {ordered = {}, byName = {}, context = context, targets = true, pending = true}
            for _, slot in ipairs(addon.slotOrder) do
                local data = slotSelected(filters, slot) and packed[slot]
                local page = data and rating:GetGuideTargetPage(data, context.level)
                if page then page.visitActivities(function(name, _, count, at)
                    local dest = activityEntry(preview, name)
                    for i = 1, count do
                        checkpoint()
                        local key = data.indices.keys[at(i)]
                        activityLoot(dest, key:match("^%d+") or key)
                    end
                end) end
            end
            query.preview = preview
            if #preview.ordered > 0 then publishFirst() end
        end
        local hasExact = false
        local lookupId = tonumber(search:match("item:(%d+)"))
        local native = lookupId and rating:GetTooltipItem(lookupId, search)
        for _, slot in ipairs(addon.slotOrder) do
            local indices = BigBiSListData.guide_index.slots[slot]
            if indices and query.search then
                local ordinal, identity = rating:FindGuideItem(context, indices, search)
                local found = identity and (native and native.facts or context.catalog.items[identity])
                if ordinal or found and (found.slot == slot or found.slot == "One Hand" and slot == "Main Hand") then
                    local row = exactLookup(context, slot, ordinal, identity, search, scoped, player, owned)
                    if row then
                        local bucket = newBucket()
                        append(bucket, row)
                        query.slots[slot] = bucket
                        query.lookupReason = row.lookupReason or query.lookupReason
                        hasExact = true
                    end
                end
            end
        end
        if hasExact then query.exact = true; return end
        for _, slot in ipairs(addon.slotOrder) do
            local data = slotSelected(filters, slot) and packed[slot]
            if data and retry and not retry.changed[slot] and retry.query.slots[slot] then
                query.slots[slot] = retry.query.slots[slot]
                query.unknown = query.unknown or query.slots[slot].unknown
            elseif data then
                local bucket = newBucket()
                if activity then bucket.activities = {ordered = {}, byName = {}} end
                query.slots[slot] = bucket
                visitTargets(context, data, scoped, query.search, player, owned, checkpoint, function(row, level)
                    local verdict, reward = row.targetVerdict, rewardKey(row, context)
                    if visible(verdict) then
                        local new = not bucket.rewards[reward]
                        keep(bucket, row, reward)
                        if not activity and new then
                            publishFirst()
                            query.visibleCount = (query.visibleCount or 0) + 1
                            if query.visibleCount == 6 then self:ScheduleRefresh(nil, "visible gear targets") end
                        end
                    elseif verdict.kind == "unknown" then
                        bucket.unknown, query.unknown = true, true
                        local comparison = verdict.swap and (verdict.swap.forecast or verdict.swap)
                        if comparison and comparison.status == "loading" and not (rating.loadedItems or {})[row.item_id] then
                            self:QueueStatLoads({[row.item_id] = true})
                        end
                    end
                    if activity then
                        checkpoint()
                        for _, routed in ipairs(addon:GetLevelingActivityRows(row, scoped, level)) do
                            checkpoint()
                            local dest = activityEntry(bucket.activities, addon:GetActivityGroup(routed))
                            activityLoot(dest, reward)
                            if visible(verdict) then keep(dest, routed, reward)
                            elseif verdict.kind == "unknown" then dest.unknown = true end
                        end
                    end
                end)
                bucket.rows = targetSort(self, bucket.rows, state, checkpoint)
                for index, row in ipairs(bucket.rows) do bucket.positions[row.stat_identity] = index end
                if not activity and not query.reference and not query.search and not bucket.rows[1] then
                    local level = math.max(context.level, player.level)
                    local personal = rating:GetContext(context.class, context.spec, level == 60 and "PR" or "LEVELING", level, owned)
                    bucket.best = rating:GetGuideOwnedNames(personal, slot, level == player.level)
                end
            end
        end
        if activity then finishActivities(query, player, context, checkpoint) end
    end, current, function()
        query.done, query.job = true, nil
        if not priming then self:ScheduleRefresh(nil, "gear targets ready") end
    end, priming)
    priming = false
    return query
end

function UI:RenderPackedGuide(context, filters, title)
    local activity = self:IsLevelingActivityView() == true
    local query = self:RequestPackedGuideRows(context, filters, activity)
    local reach = not query.search and self:RequestPackedReach(context, filters)
    if query.exact then title = title .. " · Exact item lookup" end
    if query.reference then title = title .. " · Reference gear for " .. context.spec
    elseif not query.exact then title = title .. " · Sidegrades and downgrades hidden" end
    local existing = self.renderModel
    if not query.done and existing and existing.targetQuery ~= query and existing.targetQuery and (existing.rowCount or 0) > 0
        and existing.contextKey == self:GetNavigationContextKey() and not self.pendingNavigation then
        if self.resultCountText then self.resultCountText:SetText("Comparing gear…") end
        return
    end
    local function paintTargets()
        if query.first and self.currentFilterPayload == filters and self:GetViewKey() == "gearGuide"
            and self:IsLevelingActivityView() == activity then
            self:RenderLevelingTab()
            return true
        end
    end
    if activity and not query.exact then
        local activities = query.done and query.activities or query.preview
        if activities and #activities.ordered > 0 then
            self:RenderLevelingActivities({}, self:GetSelection(), context.level, filters, "No activities offer an upgrade at this level.",
                title, true, activities, reach)
            if self.renderModel then self.renderModel.targetQuery = query end
        else
            local model = self:NewListRenderModel()
            model.packed, model.guideContext, model.guideFilters, model.targetQuery = true, context, filters, query
            if not query.first and not query.done then model.paintTargets = paintTargets end
            self:AddListRenderEntry(model, {kind = "note", text = title, height = 22, tooltip = guideExplanation})
            if reach then self:AddWithinReach(model, nil, "activities", reach) end
            local message = not query.done and "Comparing gear…" or query.reference and "No matching activities"
                or ("No known upgrades from activities at Level " .. context.level)
            self:AddListRenderEntry(model, {kind = "note", height = 28, text = message})
            self:RenderListModel(model)
        end
        return
    end
    local model = self:BuildPackedGuideModel(context, filters, title, query, reach)
    model.targetQuery = query
    if not query.first and not query.done then model.paintTargets = paintTargets end
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
    self.facetWorker = rating:QueueWork(2, function(checkpoint)
        local guide = self.renderModel and self.renderModel.guideContext
        if not guide or guide.class ~= selection.class or guide.spec ~= selection.spec or guide.level ~= filters.level then
            guide = rating:GetGuideContext(selection.class, selection.spec, phase, filters.level, filters.race, filters.faction)
        end
        local slots = guide and rating:GetPackedGuide(guide)
        if not slots then return addon:GetFilterAvailabilitySnapshot(selection.class, selection.spec, phase, selection.tab, filters) end
        local player, scoped = addon:GetTooltipPlayerContext(), {}
        for key, value in pairs(filters) do scoped[key] = value end
        scoped.class, scoped.race, scoped.faction, scoped._guideTarget = guide.class, guide.race, guide.faction, true
        if player and player.class == guide.class then scoped._questAvailable = questAvailable end
        local function visit(base, collect)
            local search = base.search and base.search ~= "" and base.search
            for _, slot in ipairs(addon.slotOrder) do
                if slotSelected(base, slot) and slots[slot] then
                    visitTargets(guide, slots[slot], base, search, player, self.currentOwned, checkpoint, function(row, level)
                        if visible(row.targetVerdict) then collect(row, level) end
                    end)
                end
            end
        end
        return addon:GetFilterAvailabilitySnapshot(selection.class, selection.spec, phase, selection.tab, scoped, visit)
    end, current, function(snapshot)
        self.facetWorker = nil
        self.currentAvailabilitySnapshot, self.lastPackedFilterAvailability, self.lastPackedFacetContext = snapshot, snapshot, context
        for _, control in ipairs({self.sourceDropdown, self.zoneDropdown, self.costDropdown, self.vendorDropdown, self.reputationDropdown}) do
            if control.RefreshOpenMenu then control:RefreshOpenMenu() end
        end
    end)
    return cached
end
