-- Browse personally useful targets. Exact lookups share the full reference ranking.
local addon, UI = BigBiSList, BigBiSList.UI
local rating = addon.ForeverGearRating
if not rating then return end

function UI:HasIndexedGear()
    local core = (BigBiSListData.runtime_indexes or {}).guide_core
    local bundle = BigBiSListData.guide_index
    return bundle and bundle.data == BigBiSListData.stat_rank or core and core.data == BigBiSListData.stat_rank and core.items == core.data.items
end

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

local function focusedRoute(filters)
    return filters.search and filters.search ~= "" or any(filters.zones) or any(filters.vendors)
        or filters.zone and filters.zone ~= "all" or filters.vendor and filters.vendor ~= "all"
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

-- Most stored gear competes within one slot group. Worn gear, set pieces and
-- shared equip limits can affect another slot's best legal setup.
function UI:GetGuideStorageChanges(previous, owned)
    local model = self.pendingGuideModel or self.renderModel
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
            local sets = BigBiSListData.character_scoring and BigBiSListData.character_scoring.item_sets
            if not item or item.set_key or item.unique_group or sets and (sets[record.id] or sets[tostring(record.id)]) then return end
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
    if not player or player.class ~= context.class or player.level ~= context.level or not owned or owned.equippedOnly then return end
    local current = self.packedReach
    if current and current.context == context and current.filters == filters and current.owned == owned and current.questRevision == self.questRevision
        and not (current.job and current.job.cancelled) then return current.result end
    local questItems = (BigBiSListData.guide_index or {}).quests
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
        if questItems and self.activeQuestIds then
            for _, id in ipairs(self.activeQuestIds) do addQuest(id) end
        elseif questItems and C_QuestLog and C_QuestLog.IsOnQuest then
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
                if not questItems and info.core then
                    for _, key in ipairs(info.members) do keys[key] = true end
                end
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
        if signature(prior) == signature(result) then request.result = prior end
        if request.result ~= prior or request.awaitingGuide then self:ScheduleRefresh(nil, "gear within reach") end
    end)
    return prior
end

local guideExplanation = "Compares equipped gear, bags, and your last readable bank scan. Catalog rank includes gear with unverified sources."
local slotNouns = { Head = "helm", Shoulder = "shoulder", Feet = "boot", Hands = "glove", Legs = "leg",
    ["Two Hand"] = "two-handed weapon", ["Main Hand"] = "main-hand", ["Off Hand"] = "off-hand" }

function UI:BuildPackedGuideModel(context, filters, title, query, reach)
    local model = self:NewListRenderModel()
    model.packed, model.guideContext, model.guideFilters = true, context, filters
    local spans, marketSpans, empty = {}, {}, {}
    local slots = query.previewSlots or query.slots
    model.guideSlots = slots
    self:AddListRenderEntry(model, {kind = "note", text = title, height = 22, tooltip = guideExplanation})
    if query.lookupReason then self:AddListRenderEntry(model, {kind = "note", text = query.lookupReason, height = 24}) end
    if reach then self:AddWithinReach(model, nil, "guide", reach) end
    local grouped = (self:GetViewState().groupBy or "slot") == "slot"
    for _, slot in ipairs(addon.slotOrder) do
        local bucket = slots[slot]
        if bucket and #bucket.rows > 0 then
            if grouped then self:AddListSection(model, slot, "leveling", nil, slot) end
            local span = {key = slot, bucket = bucket, get = function(i) return bucket.rows[i] end}
            self:AddListSpan(model, span, #bucket.rows)
            if span.top then spans[slot] = span end
            model.activeSection = nil
            if grouped then self:AddListGap(model, 6) end
            if bucket.comparisonDetail and query.done then
                self:AddListRenderEntry(model, {kind = "note", text = bucket.comparisonDetail, height = 22})
            end
        elseif bucket and not (bucket.market and #bucket.market.rows > 0)
            and query.done and not query.search and not query.reference then
            local notice
            if bucket.comparisonDetail then notice = slot .. " · " .. bucket.comparisonDetail
            elseif filtered(filters) then notice = "No upgrades match these filters · " .. slot
            else notice = "No known " .. (slotNouns[slot] or slot:lower()) .. " upgrades at Level " .. context.level end
            if bucket.best and bucket.best ~= "" then notice = notice .. " · Best owned · " .. bucket.best end
            empty[#empty + 1] = notice
        end
    end
    local marketSection
    for _, slot in ipairs(addon.slotOrder) do
        local bucket = slots[slot]
        local market = bucket and bucket.market
        if market and #market.rows > 0 then
            if not marketSection then marketSection = self:AddListSection(model, "Auction House", "leveling", false, "guide-market") end
            local span = {key = "market:" .. slot, bucket = market, get = function(i) return market.rows[i] end}
            self:AddListSpan(model, span, #market.rows)
            if span.top then marketSpans[slot] = span end
        end
    end
    model.activeSection = nil
    if #empty > 0 then
        local section = #empty > 1 and model.rowCount > 0 and self:AddListSection(model, "Other slots", nil, true, "guide-empty-slots")
        if section then section.count = #empty end
        if not section or not section.collapsed then
            for _, notice in ipairs(empty) do self:AddListRenderEntry(model, {kind = "note", text = notice, height = 28}) end
        end
        model.activeSection = nil
    end
    if model.rowCount == 0 and #empty == 0 then
        local message = query.comparisonDetail or "No obtainable gear matches these filters."
        self:AddListRenderEntry(model, {kind = "note", text = message, height = 22})
    end
    local function parse(key)
        if key then return key:match("^item\031%d+\031([^\031]+)\031(.+)$") end
    end
    model.rebind = function(key)
        local slot, identity = parse(key)
        local bucket = slots[slot]
        local found = bucket and bucket.rows[bucket.positions[identity]]
        local market = bucket and bucket.market
        found = found or market and market.rows[market.positions[identity]]
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
        local market = marketSpans[slot]
        local span = market and market.bucket.positions[key] and market or spans[slot]
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
        if navigation.anchorIndex then
            local old = navigation.anchorSpan
            for distance = 1, old and old.bucket and old.count or 0 do
                local after = old.bucket.rows[navigation.anchorIndex + distance]
                local before = old.bucket.rows[navigation.anchorIndex - distance]
                local found = after and span.bucket.positions[after.stat_identity] or before and span.bucket.positions[before.stat_identity]
                if found then return locateAt(span, found) end
            end
            return locateAt(span, math.min(span.count, navigation.anchorIndex))
        end
    end
    return model
end

function UI:RefreshPackedRows(itemId, quest)
    local model = self.pendingGuideModel or self.renderModel
    if not (model and model.packed and self.frame and self.frame:IsShown()) then return false end
    if model.endgame then return false end
    if model.targetQuery then
        local changed, bundle = {}, BigBiSListData.guide_index
        local function mark(key)
            for slot, indices in pairs(bundle and bundle.slots or {}) do
                if indices.lookup[key] then changed[slot] = true end
            end
        end
        if itemId then
            for slot, bucket in pairs(model.targetQuery.slots) do
                if bucket.pending and bucket.pending[itemId] then changed[slot] = true end
            end
        end
        for id in pairs(quest and self.changedGuideQuests or {}) do
            for _, key in ipairs(bundle and bundle.quests[id] or {}) do mark(key) end
            if not bundle then for slot in pairs(model.targetQuery.slots) do changed[slot] = true end end
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
        if itemId then return true end
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

local function targetBucket(bucket, row, market)
    if not addon:IsGuideMarketRoute(row.matched_access_option, market) then return bucket end
    bucket.market = bucket.market or newBucket()
    return bucket.market
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
    return verdict.kind == "upgrade" or verdict.kind == "utility" or verdict.kind == "reference" or verdict.kind == "situational"
end

local function visitTargets(context, data, filters, search, player, owned, checkpoint, visit)
    local seen = {}
    -- The shipped page already applies slot, class, race, faction, level and phase.
    -- The live access check still handles finished quests and alternative routes.
    local matchFilters = filtered(filters) == true
    local matches = search and rating:GuideSearchPredicate(data.indices, search)
    local last = search and context.leveling and not data.core and addon.maxLevelingLevel or context.level
    local focused = search or matchFilters
    for level = context.level, last do
        local page = rating:GetGuideTargetPage(data, level, not focused and "candidates" or nil)
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

local function comparisonValue(row)
    local verdict = row.targetVerdict
    local swap = verdict.swap and (verdict.swap.forecast or verdict.swap)
    return verdict.gain or swap and swap.delta or row.stat_rank.score or 0
end

-- Within the same activity and requirements, a weaker reward only earns a
-- separate trip if it opens earlier. Unknown gates stay with their named source.
local function selectTargets(bucket, focused, context, checkpoint)
    local trips, approaches, gates, bestGain, strongest = {}, {}, {}, nil, nil
    local bestScore = 0
    for _, row in ipairs(bucket.rows) do
        checkpoint()
        local verdict, route = row.targetVerdict, row.matched_access_option
        local source = route and route.source or {}
        local state, ready
        if source.type == "quest" then state, ready = UI:GetAcquisitionQuestState(source.quest_id or source.entity_id) end
        row.immediate = verdict.owned and verdict.owned.state == "bag" or state == "In progress" and ready
        local gain = verdict.gain
        bestScore = math.max(bestScore, row.stat_rank.score or 0)
        if gain and (not bestGain or gain > bestGain) then bestGain, strongest = gain, row end
        local gate = addon:GetLevelingSourceGate(row.acquisition_display)
        gates[row] = gate
        local method = route and route.source_type or ""
        if gain and (not approaches[method] or gain > approaches[method].targetVerdict.gain) then approaches[method] = row end
        local item = row.stat_rank.item
        for _, rule in ipairs(item and item.effect_rules or {}) do
            if rule.bonus_targets and (rule.bonus_multiplier or 0) > 1 then
                row.guideSpecialty = "Bonus damage against " .. rule.bonus_targets
                break
            end
        end
        local specific = not gate or next(route and route.requirements or {}) or next(source.dependencies or {})
        local trip = table.concat({addon:GetActivityGroup(row) or "", method,
            route and route.cost_summary or "", table.concat(route and route.reputations or {}, ","),
            specific and (source.entity_name or row.name) or "", row.guideSpecialty or verdict.purpose or verdict.kind}, "\031")
        local group = trips[trip] or {}
        trips[trip], group[#group + 1] = group, row
    end
    local choices, superseded = {}, {}
    for _, group in pairs(trips) do
        local ordered = rating:SortInWork(group, function(a, b)
            local left, right = gates[a] or 0, gates[b] or 0
            if left ~= right then return left < right end
            left, right = comparisonValue(a), comparisonValue(b)
            if left ~= right then return left > right end
            return a.stat_identity < b.stat_identity
        end, checkpoint)
        local best
        for _, row in ipairs(ordered) do
            checkpoint()
            if not best or comparisonValue(row) > comparisonValue(best) then
                choices[row], best = true, row
            else superseded[row] = best end
        end
    end
    local rows, positions, rewards = {}, {}, {}
    for _, row in ipairs(bucket.rows) do
        checkpoint()
        local verdict = row.targetVerdict
        local method = (row.matched_access_option or {}).source_type
        local competitive = (row.stat_rank.score or 0) >= bestScore * 0.85 or verdict.gain and verdict.gain >= (bestGain or 0) * 0.85
        local earlier = strongest and gates[strongest] and gates[row] and gates[row] < gates[strongest]
        local practical = row == approaches[method] or earlier or competitive and verdict.meaningful
        local gain = verdict.gain and rating:RoundedGain(verdict.gain) > 0 and practical
        local namedUse = row.guideSpecialty and verdict.kind == "upgrade"
            or verdict.kind == "utility" and (verdict.note or verdict.purpose)
            or verdict.kind == "situational" and verdict.purpose and comparisonValue(row) >= 2 and (focused or competitive)
        local waiting = verdict.kind == "loading" or verdict.kind == "unavailable"
        if row.immediate or choices[row] and (gain or namedUse or verdict.reference and competitive or waiting and (focused or competitive)) then
            rows[#rows + 1] = row
            positions[row.stat_identity], rewards[rewardKey(row, context)] = #rows, #rows
        elseif verdict.gain then
            bucket.exclusions = bucket.exclusions or {}
            local alternative = superseded[row] or strongest
            bucket.exclusions[row.stat_identity] = rating:RoundedGain(verdict.gain) == 0 and "The gain is too small to pursue."
                or superseded[row] and comparisonValue(alternative) == comparisonValue(row) and ("Same gain from this activity · " .. alternative.name)
                or alternative and ("Stronger target · " .. alternative.name) or "A stronger reward comes from this activity."
        end
    end
    bucket.rows, bucket.positions, bucket.rewards = rows, positions, rewards
end

local function better(row, old)
    if not old then return true end
    local a, b = row.targetVerdict.gain, old.targetVerdict.gain
    if a ~= b then return a ~= nil and (b == nil or a > b) end
    local first = row.targetVerdict.swap
    local second = old.targetVerdict.swap
    local left = first and (first.forecast or first).delta
    local right = second and (second.forecast or second).delta
    if left and right and left ~= right then return left > right end
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
            for _, row in ipairs(part.rows) do
                checkpoint()
                local key = rewardKey(row, context)
                activityLoot(dest, key)
                keep(dest, row, key)
            end
            dest.comparisonDetail = dest.comparisonDetail or part.comparisonDetail
        end
    end
    local batch = {totals = {}, playerLevel = player and player.level, spec = context.spec}
    local kept = {}
    for _, dest in ipairs(activities.ordered) do
        if #dest.rows > 0 or dest.comparisonDetail then
            kept[#kept + 1] = dest
            local total = {upgrades = 0, bestGain = 0, situational = 0, comparisonDetail = dest.comparisonDetail}
            for _, row in ipairs(dest.rows) do
                checkpoint()
                local gain = row.targetVerdict.gain
                if gain then
                    total.upgrades = total.upgrades + 1
                    if not total.bestName or gain > total.bestGain or gain == total.bestGain and row.name < total.bestName then
                        total.bestName, total.bestGain = row.name, gain
                    end
                elseif row.targetVerdict.kind == "utility" or row.targetVerdict.kind == "situational" then
                    total.situational = total.situational + 1
                end
            end
            total.unconfirmed = total.upgrades == 0
            batch.totals[dest] = total
        else activities.byName[dest.name] = nil end
    end
    activities.ordered, activities.batch = kept, batch
    activities.reference = query.reference
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

function UI:FindBestGearGuideTarget(context, slots, player, owned, checkpoint)
    local packed = rating:GetPackedGuide(context)
    if not packed then return end
    local filters = {
        _guideTarget = true, _guideMarket = addon:GetGuideMarket(context.faction), _questAvailable = questAvailable,
        class = context.class, race = context.race, faction = context.faction, level = context.level,
        _leveling = context.leveling, hideIgnored = true, ignoredItems = addon:GetCharacterDB().ignoredItems,
    }
    local query = self.lastUnfilteredGuide
    if query and (query.context.key ~= context.key or query.owned ~= owned or query.questRevision ~= self.questRevision
        or query.catalogRevision ~= context.catalog.observedVersion) then query = nil end
    local best
    local function consider(row)
        local kind = row.targetVerdict.kind
        if (kind == "upgrade" or kind == "situational" or kind == "utility") and better(row, best) then best = row end
    end
    for _, slot in ipairs(slots) do
        local bucket = query and query.slots[slot]
        if not bucket and packed[slot] then
            bucket = newBucket()
            visitTargets(context, packed[slot], filters, nil, player, owned, checkpoint, function(row)
                if visible(row.targetVerdict) then keep(targetBucket(bucket, row, filters._guideMarket), row, rewardKey(row, context)) end
            end)
            selectTargets(bucket, false, context, checkpoint)
            if bucket.market then selectTargets(bucket.market, false, context, checkpoint) end
        end
        if bucket then
            for _, row in ipairs(bucket.rows) do checkpoint(); consider(row) end
            for _, row in ipairs(bucket.market and bucket.market.rows or {}) do checkpoint(); consider(row) end
        end
    end
    return best
end

local function exactLookup(context, slot, ordinal, key, search, filters, player, owned, wornLink)
    local id = tonumber(search:match("item:(%d+)"))
    local native = id and rating:GetTooltipItem(id, search)
    local item = native and native.facts or context.catalog.items[key]
    if not item then return end
    local lookup = {class = context.class, level = context.level, race = context.race, faction = context.faction, _leveling = true}
    for _, field in ipairs({"sourceType", "sourceTypes", "zone", "zones", "vendor", "vendors", "cost", "costs", "reputation", "reputations"}) do
        lookup[field] = filters[field]
    end
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
    if wornLink or id then row.item_link = wornLink or search end
    row.exactLookup = true
    row.targetVerdict = rating:GetGuideTargetVerdict(row, context, player, owned, true)
    lookup._guideTarget, lookup._guideMarket = true, filters._guideMarket
    lookup.level = row.guide_route_level or context.level
    local display = addon:GetRowAcquisitionDisplay(row, lookup, "LEVELING", true, true)
    local later, hasTarget
    if not display.option then
        local levels, options = addon:GetGuideRouteTransitions(item.id)
        for _, option in ipairs(options or {}) do
            if addon:IsGuideTargetRoute(option) or addon:IsGuideMarketRoute(option, filters._guideMarket or false) then
                hasTarget = true; break
            end
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
    elseif row.targetVerdict.kind == "hidden" and (row.targetVerdict.swap or {}).status ~= "best_owned" then
        row.lookupReason = "Gear you own is as good or better."
    else
        local last = UI.lastGuideSelection
        local bucket = last and last.context.key == context.key and last.owned == owned and last.questRevision == UI.questRevision and last.slots[slot]
        local excluded = bucket and bucket.exclusions and bucket.exclusions[key]
        if row.targetVerdict.gain and rating:RoundedGain(row.targetVerdict.gain) == 0
            and not (row.targetVerdict.owned and row.targetVerdict.owned.state == "bag") then
            row.lookupReason = "The gain is too small to make a trip for this item."
        elseif excluded then row.lookupReason = excluded
        elseif row.targetVerdict.swap and row.targetVerdict.swap.status == "best_owned" then row.lookupReason = "Already one of your best owned items."
        elseif bucket and not bucket.positions[key] and not (bucket.market and bucket.market.positions[key]) then
            local best = bucket.rows[1]
            row.lookupReason = best and ("Another target for this slot · " .. best.name) or "No personal upgrade confirmed."
        elseif not bucket and row.targetVerdict.kind == "upgrade" and not row.targetVerdict.meaningful then
            row.lookupReason = "Small gain · Worth checking if you can claim it now."
        end
    end
    return row
end

-- The core archive already restricts each pick to its spec, race and level.
-- A reviewed, unrestricted normal-dungeon drop needs only its published access level.
local function coreDropHint(context, item)
    if not context.leveling or not item.level or item.level > context.level then return end
    local record = addon:GetItemData(item.id)
    local route = record and record.primary_source
    if not route or route.type ~= "drop" or route.content_type ~= "dungeon" or route.confidence ~= "reviewed"
        or route.available_from_phase ~= "PR" or route.available_until_phase or route.side ~= "Both"
        or not route.entity_name or not route.zone or next(record.requirements or {}) or next(route.requirements or {})
        or next(route.dependencies or {}) then return end
    for key, value in pairs(route.eligibility or {}) do
        if key == "min_level" then
            if value > context.level then return end
        elseif key ~= "basis" then return end
    end
    local eligibility = BigBiSListData.item_eligibility
    local gate = eligibility and (eligibility[item.id] or eligibility[tostring(item.id)])
    if gate and ((gate.min_level or 0) > context.level or next(gate.races or {}) or next(gate.classes or {})) then return end
    return {route.zone, "drop", route.entity_name, route.zone, 0, "", 0, "", route.entity_type or ""}
end

local routeVerbs = {drop = "Drops from ", quest = "Quest reward · ", vendor = "Buy from ", pvp = "Buy from ", token_turnin = "Turn in to "}

local function previewRows(context, packed, filters, activity, checkpoint, limit)
    local slots, count = {}, 0
    local destinations = activity and {ordered = {}, byName = {}, context = context, targets = true, pending = true}
    local match = filtered(filters) == true
    local function available(hint)
        return (hint[6] == "" or hint[6] == filters._guideMarket)
            and (not filters._questAvailable or hint[5] == 0 or hint[7] == 1 or UI:GetAcquisitionQuestState(hint[5]) ~= "Completed")
    end
    for _, slot in ipairs(addon.slotOrder) do
        local data = slotSelected(filters, slot) and packed[slot]
        local page = data and rating:GetGuideTargetPage(data, context.level, "picks")
        for i = 1, page and page.count or 0 do
            if checkpoint then checkpoint() end
            local ordinal = page.at(i)
            local key = data.indices.keys[ordinal]
            local item = context.catalog.items[key]
            local row
            if match then
                row = addon:GetPackedGuideRow(context, slot, ordinal, filters, true, context.level)
            elseif item then
                local hint = page.route and page.route(i, available) or data.core and coreDropHint(context, item)
                if hint or not page.route then
                    row = {item_id = item.id, item_link = item.variant_link, variant_id = item.variant_id, name = item.name,
                        quality = item.quality, slot = slot, class = context.class, spec = context.spec, phase = context.phase,
                        leveling = context.leveling, stat_identity = key, guide_route_level = context.level, guide_available_now = true,
                        stat_rank = {item = item, level = context.level, slot = slot, spec = context.spec, phase = context.phase}}
                    if hint then
                        local source = {type = hint[2], entity_name = hint[3], zone = hint[4], quest_id = hint[5] ~= 0 and hint[5],
                            profession = hint[8] ~= "" and hint[8], entity_type = hint[9]}
                        local option = {source = source, source_type = hint[2], zone = hint[4], is_primary = true}
                        local action = routeVerbs[source.type]
                        if source.type == "drop" and (source.entity_type == "gameobject" or source.entity_type == "object") then action = "Loot " end
                        row.previewActivity, row.previewMarket = hint[1], hint[6] ~= ""
                        row.previewNext = row.previewMarket and "Check Auction House" or action and action .. hint[3]
                            or source.type == "crafted" and ("Craft · " .. (source.profession or hint[3])) or hint[3]
                        row.acquisition_display = {option = option, status = "ready", available = true,
                            source_match = {activity_zone = hint[1]}, activity_zone = hint[1], source_label = row.previewNext,
                            location_label = hint[1], source_summary = hint[3]}
                    else
                        row.acquisition_display = addon:GetRowAcquisitionDisplay(row, filters, context.phase, false, true)
                    end
                    row.matched_access_option = row.acquisition_display.option
                end
            end
            if row and row.acquisition_display.status == "ready" and row.acquisition_display.source_match then
                row.guidePreview, row.guideOrdinal = context, ordinal
                row.guideFilters = filters
                row.targetVerdict = {kind = "reference", reference = true}
                local bucket = slots[slot] or newBucket()
                slots[slot] = bucket
                local market = row.previewMarket or not row.previewActivity and addon:IsGuideMarketRoute(row.matched_access_option, filters._guideMarket)
                if market then bucket.market = bucket.market or newBucket(); bucket = bucket.market end
                local identity = rewardKey(row, context)
                keep(bucket, row, identity)
                count = count + 1
                if limit and count >= limit then return slots end
                if destinations and not market then
                    local dest = activityEntry(destinations, row.previewActivity or addon:GetActivityGroup(row))
                    activityLoot(dest, identity)
                    keep(dest, row, identity)
                end
            end
        end
    end
    return slots, destinations
end

-- Show routed Pre-Raid reference picks while the unchanged personal queries finish.
-- A preview never claims a gain before the comparison has actually run.
function UI:RenderEndgamePage(mode, selection, filters)
    if selection.phase ~= "PR" or not self:HasIndexedGear() or not (C_Timer and C_Timer.After) then return false end
    local context = rating:GetGuideContext(selection.class, selection.spec, selection.phase, 60,
        filters.race or addon:GetPlayerRaceName(), filters.faction or addon:GetPlayerFactionName())
    local packed = context and rating:GetPackedGuide(context)
    if not packed then return false end
    local request = self:GetCachedViewQuery("endgame-" .. mode, function() return {} end)
    local presentation = self.domainVersions and self.domainVersions.presentation or 0
    local view = mode == "planner" and "upgrades" or "bisList"
    local function current()
        return self.currentFilterPayload == filters and self.frame:IsShown() and not self.settingsSelection
            and self:GetViewKey() == view
            and self.domainVersions.presentation == presentation and not self.slotComparison
    end
    if request.presentation ~= presentation or request.questRevision ~= self.questRevision then
        if request.job then request.job.cancelled = true end
        request.model, request.job = nil, nil
        request.presentation, request.questRevision = presentation, self.questRevision
    end
    if not request.preview and not self.pendingNavigation and self.guideDisplay and self.renderModel
        and self.renderModel.endgame and self.renderModel.contextKey == self:GetNavigationContextKey()
        and self.guideDisplay.intent == (self.guideRequestSerial or 0) then
        request.preview = self.renderModel
    end
    if not request.preview then
        local model = self:NewListRenderModel()
        model.packed, model.endgame, model.guideContext = true, true, context
        local heading = mode == "planner" and "Pre-Raid targets · Comparing your gear" or "Pre-Raid gear"
        self:AddListRenderEntry(model, {kind = "note", text = heading, height = 22})
        if not filtered(filters) then
            local scoped = {}
            for k, v in pairs(filters) do scoped[k] = v end
            scoped._guideMarket, scoped._questAvailable = addon:GetGuideMarket(context.faction), questAvailable
            local rowHeight = self:GetDensityMetrics()
            local visible = math.ceil(self.contentScroll:GetHeight() / rowHeight) + 2
            local slots = previewRows(context, packed, scoped, false, nil, math.max(6, visible))
            for _, slot in ipairs(addon.slotOrder) do
                local bucket = slots[slot]
                for _, row in ipairs(bucket and bucket.rows or {}) do self:AddListRow(model, row, "leveling") end
                for _, row in ipairs(bucket and bucket.market and bucket.market.rows or {}) do self:AddListRow(model, row, "leveling") end
            end
        end
        request.preview = model
    end
    if request.job and request.job.cancelled then request.job = nil end
    if not request.model and not request.job and not filters.ownedItems.equippedOnly then
        local job
        job = rating:QueueWork(1, function(checkpoint)
            local rows = request.rows
            if not rows then
                if mode == "planner" then rows = addon:GetPlannerRows(selection.class, selection.spec, selection.phase, filters)
                else
                    rows = {}
                    for _, group in ipairs(addon:GetPhaseRows(selection.class, selection.spec, selection.phase, filters)) do
                        checkpoint()
                        for _, row in ipairs(group.items) do rows[#rows + 1] = row end
                    end
                end
                request.rows = rows
            end
            local model
            if mode == "planner" then
                local actions = self:GetNextUpgradeActions(rows)
                model = self:BuildPlannerModel(rows, actions)
                model.hasActions = #actions > 0
            else model = self:BuildGroupedModel(rows, "phase", self:GetViewState().groupBy or "slot", "BiS List") end
            model.packed, model.endgame, model.complete = true, true, true
            return model
        end, function() return request.job == job and current() end, function(model)
            request.job, request.model = nil, model
            self:ScheduleRefresh(nil, "endgame rows ready")
        end)
        request.job = job
    end
    local model = request.model or request.preview
    if request.model then
        if mode == "planner" then
            self:SetUpgradeActionsAvailable(model.hasActions)
            if request.rows.statsPending then self:QueueStatLoads(request.rows.statsPending) end
        end
        if model.rowCount == 0 then
            model.emptyMessage = mode == "planner" and "No upgrade candidates match your gear and filters."
                or "No recommendations match this phase and filters."
        end
    end
    if model ~= self.renderModel and not (self.guideStage and self.guideStage.model == model) then self:RenderListModel(model) end
    return true
end

function UI:ResolveGuidePreview(row)
    local context = row.guidePreview
    local filters = {}
    for key, value in pairs(row.guideFilters or self.currentFilterPayload or self:BuildFilterPayload()) do filters[key] = value end
    filters._guideTarget, filters.level = true, context.level
    filters.class, filters.race, filters.faction = context.class, context.race, context.faction
    filters._guideMarket = addon:GetGuideMarket(context.faction)
    local player = addon:GetTooltipPlayerContext()
    if player and player.class == context.class then filters._questAvailable = questAvailable end
    local full = addon:GetPackedGuideRow(context, row.slot, row.guideOrdinal, filters, false, context.level)
    if full then
        local advertised = row.matched_access_option and row.matched_access_option.source
        local actual = full.matched_access_option and full.matched_access_option.source
        if advertised and actual and (advertised.entity_name ~= actual.entity_name or advertised.type ~= actual.type) then
            local display = row.acquisition_display
            for _, route in ipairs(addon:GetLevelingActivityRows(full, filters, context.level)) do
                local option = route.matched_access_option and route.matched_access_option.source
                if option and option.entity_name == advertised.entity_name and option.type == advertised.type then
                    display = route.acquisition_display
                    break
                end
            end
            full.acquisition_display, full.matched_access_option = display, display.option
        end
        full.targetVerdict = rating:GetGuideTargetVerdict(full, context, player, self.currentOwned)
        return full
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
    scoped.level, scoped._leveling = context.level, context.leveling
    scoped._guideMarket = addon:GetGuideMarket(context.faction)
    query.reference = not player or player.class ~= context.class
    if not query.reference then scoped._questAvailable = questAvailable end
    local search = (filters.search or ""):match("^%s*(.-)%s*$")
    query.search = search ~= "" and search or nil
    scoped.search = query.search
    query.activities = activity and {ordered = {}, byName = {}, context = context, targets = true}
    query.context, query.sort, query.direction, query.owned = context, state.sort, state.sortDirection, owned
    query.questRevision, query.catalogRevision = self.questRevision, context.catalog.observedVersion
    local retry = self.targetRetry
    if retry and (not retry.query.done or retry.query.context ~= context or query.search or
        retry.query.activities and not activity or activity and not retry.query.activities or retry.query.sort ~= state.sort
        or retry.query.direction ~= state.sortDirection or retry.filters ~= filters and retry.owned ~= owned) then retry = nil end
    self.targetRetry = nil
    if not query.search then
        local previous = self.renderModel and self.renderModel.targetQuery
        local unfiltered = not activity and not filtered(scoped) and not any(scoped.slots)
        if unfiltered and previous and previous.openingMarket == scoped._guideMarket and previous.previewSlots
            and previous.openingAccess == self.currentAccess and previous.context == context
            and previous.questRevision == query.questRevision and previous.catalogRevision == query.catalogRevision
            and previous.reference == query.reference then
            query.previewSlots, query.previewThread = previous.previewSlots, nil
        elseif self.openingGuide and self.refreshStartedAt and C_Timer and C_Timer.After then
            if not query.previewThread then
                query.previewThread = coroutine.create(function(deadline)
                    local function checkpoint()
                        if debugprofilestop() >= deadline then deadline = coroutine.yield() end
                    end
                    return previewRows(context, packed, scoped, activity, checkpoint)
                end)
            end
            local ok, slots, destinations = coroutine.resume(query.previewThread, self.refreshStartedAt + 2.5)
            if not ok then query.previewThread = nil; error(slots, 0) end
            if not slots then self.refreshPending = true; return query end
            query.previewSlots, query.preview, query.previewThread = slots, destinations, nil
        else
            query.previewThread = nil
            query.previewSlots, query.preview = previewRows(context, packed, scoped, activity)
        end
        query.first = true
        if owned and owned.equippedOnly and not query.reference then
            if unfiltered then query.openingMarket, query.openingAccess = scoped._guideMarket, self.currentAccess end
            return query
        end
    end
    local function current()
        return self.currentViewQueryCache == cache and cache[key] == query and self.frame and (self.frame:IsShown() or self.openingGuide)
            and self:GetViewKey() == "gearGuide" and self:IsLevelingActivityView() == activity
            and state.sort == query.sort and state.sortDirection == query.direction
            and self.targetRevision == query.revision
    end
    query.revision = self.targetRevision
    local priming = not self.renderModel or not self.renderModel.targetQuery
    query.job = rating:QueueWork(1, function(checkpoint)
        local hasExact = false
        local lookupId = tonumber(search:match("item:(%d+)"))
        local native = lookupId and rating:GetTooltipItem(lookupId, search)
        for _, slot in ipairs(addon.slotOrder) do
            local indices = query.search and (packed[slot] and packed[slot].indices
                or ((BigBiSListData.guide_index or {}).slots or {})[slot])
            if indices and query.search then
                local ordinal, identity, link = rating:FindGuideItem(context, indices, search, owned, slot)
                local found = identity and (native and native.facts or context.catalog.items[identity])
                if ordinal or found and (found.slot == slot or found.slot == "One Hand" and slot == "Main Hand") then
                    local row = exactLookup(context, slot, ordinal, identity, search, scoped, player, owned, link)
                    if row then
                        local bucket = newBucket()
                        bucket.pending = row.targetVerdict.pending
                        self:QueueStatLoads(bucket.pending)
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
                query.comparisonDetail = query.comparisonDetail or query.slots[slot].comparisonDetail
            elseif data then
                local bucket = newBucket()
                if activity then bucket.activities = {ordered = {}, byName = {}} end
                query.slots[slot] = bucket
                visitTargets(context, data, scoped, query.search, player, owned, checkpoint, function(row, level)
                    local verdict, reward = row.targetVerdict, rewardKey(row, context)
                    local waiting = verdict.kind == "loading" or verdict.kind == "unavailable"
                    if waiting then
                        bucket.comparisonDetail = bucket.comparisonDetail or verdict.detail
                        query.comparisonDetail = query.comparisonDetail or verdict.detail
                    end
                    local seed = query.previewSlots and query.previewSlots[slot]
                    if visible(verdict) or waiting and (query.search or seed and seed.positions[row.stat_identity]) then
                        local destination = targetBucket(bucket, row, scoped._guideMarket)
                        keep(destination, row, reward)
                    end
                    if verdict.pending and next(verdict.pending) then
                        bucket.pending = bucket.pending or {}
                        for id in pairs(verdict.pending) do bucket.pending[id] = true end
                    end
                    if activity then
                        checkpoint()
                        for _, routed in ipairs(addon:GetLevelingActivityRows(row, scoped, level)) do
                            checkpoint()
                            local dest = activityEntry(bucket.activities, addon:GetActivityGroup(routed))
                            if visible(verdict) then keep(dest, routed, reward)
                            elseif verdict.kind == "loading" or verdict.kind == "unavailable" then
                                dest.comparisonDetail = dest.comparisonDetail or verdict.detail
                            end
                        end
                    end
                end)
                selectTargets(bucket, focusedRoute(scoped), context, checkpoint)
                bucket.rows = targetSort(self, bucket.rows, state, checkpoint)
                for index, row in ipairs(bucket.rows) do bucket.positions[row.stat_identity] = index end
                if bucket.market then
                    local market = bucket.market
                    selectTargets(market, focusedRoute(scoped), context, checkpoint)
                    market.rows = targetSort(self, market.rows, state, checkpoint)
                    for index, row in ipairs(market.rows) do market.positions[row.stat_identity] = index end
                end
                self:QueueStatLoads(bucket.pending)
                for _, dest in ipairs(bucket.activities and bucket.activities.ordered or {}) do selectTargets(dest, true, context, checkpoint) end
                if not activity and not query.reference and not query.search and not bucket.rows[1] then
                    local level = math.max(context.level, player.level)
                    local personal = rating:GetContext(context.class, context.spec, level == 60 and "PR" or "LEVELING", level, owned)
                    bucket.best = rating:GetGuideOwnedNames(personal, slot, level == player.level)
                end
            end
        end
        if activity then finishActivities(query, player, context, checkpoint) end
    end, current, function()
        query.done, query.first, query.job, query.previewSlots = true, true, nil, nil
        if not filtered(filters) and not query.reference and not activity then
            self.lastGuideSelection = query
            if not any(filters.slots) then self.lastUnfilteredGuide = query end
        end
        if not priming then self:ScheduleRefresh(nil, "gear targets ready") end
    end, priming and query.search ~= nil)
    priming = false
    return query
end

local function pageEntryKey(entry)
    if entry.data then
        local data = entry.data
        return (entry.sectionKey or "") .. "/" .. (data.slot or "") .. "/" .. (data.stat_identity or tostring(data.item_id))
    end
    if entry.activityName then return "activity/" .. entry.activityName end
    return entry.sectionKey or entry.title or entry.text or entry.kind
end

local function sameGuideOrder(old, new)
    if old.rowCount ~= new.rowCount or #old.entries ~= #new.entries then return false end
    for index, entry in ipairs(old.entries) do
        local nextEntry = new.entries[index]
        if entry.kind ~= nextEntry.kind or entry.height ~= nextEntry.height then return false end
        if entry.kind == "span" then
            if entry.key ~= nextEntry.key or entry.count ~= nextEntry.count then return false end
            for i = 1, entry.count do
                if entry.get(i).stat_identity ~= nextEntry.get(i).stat_identity then return false end
            end
        elseif entry.kind ~= "note" and pageEntryKey(entry) ~= pageEntryKey(nextEntry) then return false end
    end
    return true
end

function UI:CancelGuideStage()
    local page = self.guideStage
    if not page then return end
    self.guideStage = nil
    for _, frame in ipairs(page.prepared) do
        frame:Hide()
        frame:ClearAllPoints()
        self:PoolRenderFrame(frame.__bigBisListRenderKind, frame)
    end
end

function UI:ResetGuidePublication()
    self:CancelGuideStage()
    self.guideRequestSerial = (self.guideRequestSerial or 0) + 1
    self.pendingGuideModel, self.guidePersonalized, self.lastGuideRender = nil, nil, nil
    if self.updateGuideButton then self.updateGuideButton:Hide() end
end

-- Keep the position and mouse owner. Only the item's evidence changes while
-- a newer list waits for the player in the footer.
function UI:UpdateGuideRowAdvice(frame, data, context)
    local view = self:GetLevelingGearView(data, "leveling")
    if not view then return end
    local text = addon.Widgets:GearAdviceText(view) or ""
    if data.targetVerdict and data.targetVerdict.kind == "upgrade" then
        local reason = addon.Widgets:DecisionReason(data.stat_rank and data.stat_rank.item, data.targetVerdict.swap, context)
        if reason then text = text .. " · " .. reason end
    end
    frame.boundData, frame.detailData, frame.iconButton.detailData = data, data, data
    frame.__bigBisBoundRenderEntry.data = data
    frame.subText:SetTextColor(addon.Widgets:GearAdviceColor(view.tone))
    addon.Widgets:SetCellText(frame.subText, text, 1, 12, frame.subText:GetWidth())
    frame.subText:SetShown(text ~= "")
    local rank = frame.cells.stat_rank
    if rank then addon.Widgets:SetCellText(rank, view.strength or self:GetRowRecommendationText(data, "leveling") or "", 2, 13, rank:GetWidth()) end
    local route = frame.cells.acquisition
    if route then
        local step = self:GetSourceNextStep(data)
        local zone = data.matched_access_option and data.matched_access_option.zone
        if step and zone and zone ~= "" and not step:find(zone, 1, true) then step = step .. "\n" .. zone end
        addon.Widgets:SetCellText(route, step or view.acquisition or "", 2, 13, route:GetWidth())
    end
    self:UpdateRowOwnership(frame, data)
end

local function holdGuidePage(ui, model)
    if ui.pendingGuideModel == model then return end
    ui.pendingGuideModel = model
    ui.updateGuideButton:Show()
    if model.endgame then return end
    local display = ui.renderModel
    local function current() return ui.pendingGuideModel == model and ui.renderModel == display end
    rating:QueueWork(1, function(checkpoint)
        local overrides = {}
        display.rowUpdates = overrides
        ui:VisitListEntries(display, 0, math.huge, function(entry)
            checkpoint()
            local old = entry.data
            if not old or not old.stat_identity then return end
            local bucket = model.guideSlots and model.guideSlots[old.slot]
            local fresh = bucket and bucket.rows[bucket.positions[old.stat_identity]]
            if not fresh and bucket and bucket.market then fresh = bucket.market.rows[bucket.market.positions[old.stat_identity]] end
            if not fresh then
                fresh = {}
                for k, v in pairs(old) do fresh[k] = v end
                if fresh.guidePreview then fresh = ui:ResolveGuidePreview(fresh) end
                fresh.targetVerdict = rating:GetGuideTargetVerdict(fresh, model.guideContext, addon:GetTooltipPlayerContext(), ui.currentOwned)
            end
            overrides[old] = fresh
            for _, frame in ipairs(ui.activeRenderFrames or {}) do
                if frame.boundData and frame.boundData.stat_identity == old.stat_identity and frame.boundData.slot == old.slot then
                    ui:UpdateGuideRowAdvice(frame, fresh, model.guideContext)
                end
            end
            if ui.selectedItemData and ui.selectedItemData.stat_identity == old.stat_identity then
                ui.selectedItemData = fresh
                if ui:IsInspectorVisible() then ui:RefreshDetails(fresh.item_id, fresh, ui.selectedItemMode) end
            end
        end)
    end, current)
end

local function hoveredGuideEntry(ui)
    for _, frame in ipairs(ui.activeRenderFrames or {}) do
        local entry = frame.__bigBisBoundRenderEntry
        if entry and (entry.data or entry.activityName or entry.nextAction) and frame:IsVisible()
            and (frame.hovered or frame.IsMouseOver and frame:IsMouseOver()) then return frame, entry end
    end
end

local function wouldMovePointer(ui, page)
    local frame, old = hoveredGuideEntry(ui)
    if not frame then return false end
    local point = old.top - ui.guideDisplay.offset
    for _, entry in ipairs(page.entries) do
        if pageEntryKey(entry) == pageEntryKey(old) and math.abs(entry.top - page.offset - point) < 0.5 then return false end
    end
    return true
end

local function anchorListLayer(ui, offset)
    if offset == (ui.guideLayerOffset or 0) then return end
    ui.guideLayerOffset = offset
    local layer = ui.contentListLayer
    layer:ClearAllPoints()
    layer:SetPoint("TOPLEFT", ui.contentChild, "TOPLEFT", 0, offset)
    layer:SetPoint("TOPRIGHT", ui.contentChild, "TOPRIGHT", 0, offset)
end

local function viewportHeight(ui, model)
    local height = ui.contentScroll:GetHeight()
    if model.columnMode and not ui.stickyHeaderMode then return height - ui.contentHeaderHost:GetHeight() - 4 end
    if not model.columnMode and ui.stickyHeaderMode then return height + ui.contentHeaderHost:GetHeight() + 4 end
    return height
end

function UI:QueueGuidePage(model, apply, scrollOnly)
    local old, display = self.renderModel, self.guideDisplay
    local contextKey = self:GetNavigationContextKey()
    local intent = scrollOnly and display and display.intent or self.guideRequestSerial or 0
    local committed = not self.pendingNavigation and display and old and display.intent == intent and old.contextKey == contextKey
    local personal = model.targetQuery and model.targetQuery.done == true and self:GetViewKey() == "gearGuide"
    local updateFacts = not scrollOnly and not apply and committed and self.guidePersonalized and personal
    if updateFacts then
        if not sameGuideOrder(old, model) then
            self:CancelGuideStage()
            holdGuidePage(self, model)
            return
        end
    end
    local nativeOffset = self.contentScroll:GetVerticalScroll() or 0
    local nav = {scroll = nativeOffset}
    if not scrollOnly then
        local pending = self.pendingNavigation
        if pending then nav = pending.restore and self.navigationStates and self.navigationStates[contextKey] or {scroll = 0}
        elseif display and old.contextKey == contextKey then nav = self:CaptureNavigationState()
        else nav.scroll = 0 end
    end
    if not display then self:SetStickyHeaderMode(model.columnMode) end
    local offset = self:GetNavigationOffset(model, nav)
    local height, width = viewportHeight(self, model), self:GetTableViewportWidth(self.contentListLayer)
    local layout = self:GetTableColumnLayout(width, model.columnMode or "phase")
    local page = {model = model, navigation = nav, offset = offset, nativeOffset = nativeOffset, height = height,
        width = width, layout = layout, intent = intent, entries = {}, prepared = {}, frames = {}, claimed = {}, index = 1,
        automatic = committed and (personal or model.endgame and model.complete) and old ~= model and not apply and not scrollOnly,
        personal = personal, scrollOnly = scrollOnly, updateFacts = updateFacts}
    self:VisitListEntries(model, offset, offset + height, function(entry)
        if entry.bottom > offset and entry.top < offset + height then
            if entry.data and model.rowUpdates then entry.data = model.rowUpdates[entry.data] or entry.data end
            page.entries[#page.entries + 1] = entry
        end
    end)
    self:CancelGuideStage()
    if page.automatic and wouldMovePointer(self, page) then holdGuidePage(self, model); return end
    if not scrollOnly then
        self.pendingGuideModel = nil
        if self.updateGuideButton then self.updateGuideButton:Hide() end
    end
    self.guideStage = page
    if self.guidePainting then self:ScheduleGuidePaint() else self:PaintGuidePage() end
end

function UI:ScheduleGuidePaint()
    if self.packedPaintPending then return end
    self.packedPaintPending = true
    if C_Timer and C_Timer.After then
        C_Timer.After(0, function()
            self.packedPaintPending = nil
            if self.guideStage then self:PaintGuidePage() end
        end)
    end
end

function UI:PaintGuidePage()
    if self.guidePainting or self.publishingGuide then return end
    self.guidePainting = true
    local ok, message = pcall(self.PaintGuideSlice, self)
    self.guidePainting = nil
    if not ok then
        self.publishingGuide = nil
        self:CancelGuideStage()
        if self.guideStagingLayer then
            for _, child in ipairs({self.guideStagingLayer:GetChildren()}) do
                if child:GetParent() == self.guideStagingLayer then
                    child:Hide()
                    if child.__bigBisManaged then self:PoolRenderFrame(child.__bigBisListRenderKind or "row", child) end
                end
            end
        end
        error(message, 0)
    end
    if self.packedPaintPending and not (C_Timer and C_Timer.After) then
        self.packedPaintPending = nil
        if self.guideStage then self:PaintGuidePage() end
    end
end

function UI:PaintGuideSlice()
    if self.publishingGuide or not (self.frame:IsShown() or self.openingGuide) then return end
    local page, display = self.guideStage, self.guideDisplay
    if display and display.selected ~= self.selectedRowKey then
        display.selected = self.selectedRowKey
        for _, frame in ipairs(self.activeRenderFrames or {}) do
            if frame.boundData and frame.SetSelected then
                frame:SetSelected(self.selectedRowKey ~= nil and self:GetRowKey(frame.boundData, frame.boundMode) == self.selectedRowKey)
            end
        end
    end
    local scroll = self.contentScroll
    local offset = scroll:GetVerticalScroll() or 0
    local height = page and viewportHeight(self, page.model) or scroll:GetHeight()
    local width = self:GetTableViewportWidth(self.contentListLayer)
    if display then anchorListLayer(self, display.offset - offset) end
    if page and (page.nativeOffset ~= offset or page.width ~= width or page.height ~= height) then
        return self:QueueGuidePage(page.model, false, page.scrollOnly)
    elseif not page then
        if display and (display.offset ~= offset or display.width ~= width or display.height ~= height) then
            return self:QueueGuidePage(self.renderModel, false, true)
        end
        return
    end
    if not self.guideStagingLayer then
        self.guideStagingLayer = CreateFrame("Frame", nil, self.contentChild)
        self.guideStagingLayer:SetAllPoints(self.contentListLayer)
        self.guideStagingLayer:Hide()
    end
    local host, start = self.guideStagingLayer, debugprofilestop and debugprofilestop()
    local stats = self:GetPerformanceStats()
    local frameTime = GetTime and GetTime()
    local spent = stats.timingFrame == frameTime and stats.frameTime or 0
    if self.refreshStartedAt and start then spent = spent + start - self.refreshStartedAt end
    local paintBudget = page.model.endgame and 2 or 3
    while page.index <= #page.entries do
        if C_Timer and C_Timer.After and start and spent + debugprofilestop() - start >= paintBudget then break end
        local entry = page.entries[page.index]
        local key = pageEntryKey(entry)
        local prior = display and display.byKey[key]
        local reused = prior and prior.__bigBisBoundRenderEntry
        if reused then
            local same = reused == entry or entry.data and (reused.data == entry.data or page.updateFacts)
                or entry.kind == "note" and entry.text == reused.text and entry.tooltip == reused.tooltip
                or entry.kind == "section" and reused.collapsed == entry.collapsed and reused.count == entry.count
                or entry.activityName and entry.detail == reused.detail
            if page.claimed[prior] or not same or display.layout.signature ~= page.layout.signature
                or reused.height ~= entry.height or reused.top ~= entry.top then prior = nil end
        end
        local frame = prior
        if prior then
            page.claimed[prior] = true
            if page.updateFacts and entry.data and prior.boundData ~= entry.data then self:UpdateGuideRowAdvice(prior, entry.data, page.model.guideContext) end
        else
            local kind = entry.nextAction and "planner-action" or entry.kind
            if kind == "row" then kind = "row:" .. entry.mode .. (page.layout.compact and ":compact" or ":wide") end
            frame = self:AcquireRenderFrame(kind)
            frame = self:BindListEntry(host, entry, frame, entry.mode == page.model.columnMode and page.layout)
            frame.__bigBisListRenderKind = kind
            page.prepared[#page.prepared + 1] = frame
        end
        page.frames[page.index], page.index = frame, page.index + 1
    end
    if self.guideStage ~= page then return end
    if scroll:GetVerticalScroll() ~= page.nativeOffset then
        self:QueueGuidePage(page.model, false, page.scrollOnly)
    elseif page.index > #page.entries then
        if (display or page.model.endgame) and start and C_Timer and C_Timer.After
            and spent + debugprofilestop() - start >= paintBudget and not page.commitDeferred then
            page.commitDeferred = true
            self:ScheduleGuidePaint()
        elseif page.automatic and wouldMovePointer(self, page) then
            self:CancelGuideStage()
            holdGuidePage(self, page.model)
        else self:PublishGuidePage(page) end
    else self:ScheduleGuidePaint() end
    if start and not self.refreshInProgress then self:RecordAddonTime("visible rows", debugprofilestop() - start) end
end

function UI:PublishGuidePage(page)
    if page.model.emptyMessage then
        self:CancelGuideStage()
        self:RenderEmpty(page.model.emptyMessage)
        return
    end
    self.publishingGuide = page
    self.guideStage = nil
    local model, old = page.model, self.activeRenderFrames or {}
    if not page.scrollOnly then self:RenderListModel(model) end
    anchorListLayer(self, 0)
    local members, byKey = {}, {}
    local pointed, oldEntry = hoveredGuideEntry(self)
    for index, frame in ipairs(page.frames) do
        local entry = page.entries[index]
        if pointed and entry.data and oldEntry.data and not entry.nextAction and entry.data.stat_identity
            and pageEntryKey(entry) == pageEntryKey(oldEntry) and pointed ~= frame
            and pointed.__bigBisListRenderKind == frame.__bigBisListRenderKind then
            frame:Hide()
            self:PoolRenderFrame(frame.__bigBisListRenderKind, frame)
            frame = self:CreateDataRow(self.contentListLayer, -entry.top, entry.data, entry.mode, pointed, entry.rowHeight, true, page.layout)
            page.frames[index] = frame
        elseif frame:GetParent() ~= self.contentListLayer then frame:SetParent(self.contentListLayer) end
        frame.__bigBisBoundRenderModel, frame.__bigBisBoundRenderEntry = model, entry
        frame.__bigBisBoundRenderSerial = self.renderModelSerial
        if frame.boundData and frame.SetSelected then
            frame:SetSelected(self.selectedRowKey ~= nil and self:GetRowKey(frame.boundData, frame.boundMode) == self.selectedRowKey)
        end
        members[frame], byKey[pageEntryKey(entry)] = true, frame
    end
    for _, frame in ipairs(old) do
        if not members[frame] then
            frame:Hide()
            frame:ClearAllPoints()
            self:PoolRenderFrame(frame.__bigBisListRenderKind, frame)
        end
    end
    self.activeRenderFrames, self.renderActiveMembership = page.frames, members
    page.selected = self.selectedRowKey
    page.byKey, page.prepared, page.claimed, page.navigation = byKey, nil, nil, nil
    self.guideDisplay, self.publishingGuide = page, nil
    if page.personal and not page.scrollOnly then self.guidePersonalized = true end
    if self.openingGuide then self.openingGuide = nil; self.frame:Show() end
    if self.viewportStarted then
        local stats = self:GetPerformanceStats()
        stats.firstViewportMs = debugprofilestop() - self.viewportStarted
        stats.firstRowsMs = stats.firstViewportMs
        self.viewportStarted, self.firstRowsStarted = nil, nil
    end
    self:CountPerformance("realizedEntries", #page.frames)
    self:StartGuideInventory()
end

function UI:RenderPackedGuide(context, filters, title)
    local activity = self:IsLevelingActivityView() == true
    local query = self:RequestPackedGuideRows(context, filters, activity)
    if query.previewThread then return end
    local reach = not query.search and self:RequestPackedReach(context, filters)
    local existing = self.renderModel
    local request = self.packedReach
    if not query.search and query.done and existing and existing.packed and request and request.job
        and request.context == context and request.filters == filters and request.owned == self.currentOwned then
        request.awaitingGuide = true
        return
    end
    if not query.done and existing and existing.packed and existing.contextKey == self:GetNavigationContextKey()
        and (not query.previewSlots or self.guideDisplay and self.guideDisplay.intent == (self.guideRequestSerial or 0)) then
        return
    end
    local density = self:GetDensityMetrics()
    local last = self.lastGuideRender
    if last and last.query == query and last.done == query.done and last.reach == reach and last.density == density then return end
    self.lastGuideRender = {query = query, done = query.done, reach = reach, density = density}
    if query.exact then title = title .. " · Exact item lookup" end
    if not query.exact then title = title .. ((query.previewSlots or query.reference) and " · Guide picks for " or " · Targets for ") .. context.spec end
    if activity and not query.exact then
        local activities = query.done and query.activities or query.preview
        if activities and #activities.ordered > 0 then
            self:RenderLevelingActivities({}, self:GetSelection(), context.level, filters, "No activities offer an upgrade at this level.",
                title, true, activities, reach, query)
        else
            local model = self:NewListRenderModel()
            model.packed, model.guideContext, model.guideFilters, model.targetQuery = true, context, filters, query
            self:AddListRenderEntry(model, {kind = "note", text = title, height = 22, tooltip = guideExplanation})
            if reach then self:AddWithinReach(model, nil, "activities", reach) end
            local message = not query.done and "Comparing gear…" or query.reference and "No matching activities"
                or query.comparisonDetail
                or ("No known upgrades from activities at Level " .. context.level)
            self:AddListRenderEntry(model, {kind = "note", height = 28, text = message})
            self:RenderListModel(model)
        end
        return
    end
    local model = self:BuildPackedGuideModel(context, filters, title, query, reach)
    model.targetQuery = query
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
        scoped._guideMarket = addon:GetGuideMarket(guide.faction)
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
