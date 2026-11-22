-- Build the immutable Forever reference ranks with the client scorer.
assert(_VERSION == "Lua 5.1")
local className, output, dataPath = assert(arg[1]), assert(arg[2]), assert(arg[3])
dofile(dataPath)
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")

local addon, data = BigBiSList, BigBiSListData
local rating, source = addon.ForeverGearRating, data.stat_rank
GetBuildInfo = function() return "Forever", source.roll_build end
local catalog = rating:GetCatalog(source)
local out = assert(io.open(output, "wb"))
local write = function(...) assert(out:write(...)) end
local digits = {}
for number = 0, 63 do digits[number] = string.char(48 + number) end
local function pack(number, width)
    local result = {}
    for offset = width, 1, -1 do
        result[offset] = digits[number % 64]
        number = math.floor(number / 64)
    end
    assert(number == 0, "Guide index integer overflow")
    return table.concat(result)
end
local function quote(value) return string.format("%q", value) end

local strings, unwritten, stringCount = {}, {}, 0
local function store(value)
    local id = strings[value]
    if id then return id end
    stringCount = stringCount + 1
    strings[value] = stringCount
    unwritten[#unwritten + 1] = quote(value)
    return stringCount
end

local function flush()
    local first = stringCount - #unwritten
    -- Each function has its own Lua 5.1 constant table.
    for start = 1, #unwritten, 1024 do
        write("(function(a)\n")
        for index = start, math.min(start + 1023, #unwritten) do
            write("a[", first + index, "]=", unwritten[index], "\n")
        end
        write("end)(archive.strings);\n")
    end
    unwritten = {}
end

local routeTransitions = {}
local activities, activityIds = {}, {}
local routeHints, routeHintIds = {}, {}
local function storeHints(hints)
    local values, seen = {}, {}
    for _, hint in ipairs(hints) do
        local fields = {}
        for i, value in ipairs(hint) do fields[i] = type(value) == "number" and tostring(value) or quote(value) end
        local literal = "{" .. table.concat(fields, ",") .. "}"
        local id = routeHintIds[literal]
        if not id then id = #routeHints + 1; routeHintIds[literal], routeHints[id] = id, literal end
        if not seen[id] then values[#values + 1], seen[id] = pack(id, 3), true end
    end
    return store(table.concat(values))
end
local function routes(item)
    local known = routeTransitions[item.id]
    if not known then
        local levels, options = addon:GetGuideRouteTransitions(item.id)
        known = { levels = levels, options = options }
        routeTransitions[item.id] = known
    end
    return known
end

local universes = {}
local function universe(slot)
    if universes[slot] then return universes[slot] end
    local items, seen = {}, {}
    local function add(key)
        if seen[key] then return end
        seen[key] = true
        local item = assert(catalog.items[key])
        if not item.roll_group or not item.has_random_stats then
            items[#items + 1] = item
        end
    end
    local function addSlot(kind)
        for _, key in ipairs(catalog.slots[kind] or {}) do
            local base = catalog.items[key]
            if base.has_random_stats and base.roll_group then
                for _, bonus in ipairs(source.roll_groups[base.roll_group]) do
                    add(key .. ":0:0:0:1:" .. bonus)
                end
            else
                add(key)
            end
        end
    end
    addSlot(slot)
    if slot == "Main Hand" or slot == "Off Hand" then addSlot("One Hand") end
    table.sort(items, function(a, b)
        if a.name ~= b.name then return a.name < b.name end
        return a.key < b.key
    end)
    universes[slot] = items
    return items
end

local slotKeys = {}
for _, slot in ipairs(addon.slotOrder) do
    if #universe(slot) > 0 then slotKeys[#slotKeys + 1] = slot end
end
if className == "catalog" then
    local signature = data.runtime_indexes and data.runtime_indexes.guide_signature
    write("BigBiSListData.guide_index = {version=4, signature=", signature and quote(signature) or "nil",
        ", data=BigBiSListData.stat_rank, slots={}, classes={}, quests={}}\n")
    -- This gate depends on the published routes and phase, independently of the player's gear.
    local preRaidIndex = addon:GetAvailabilityPhaseIndex("PR")
    local blocked = {}
    local idField = assert(addon:GetDataIndex().schemaPositions.item.id)
    for _, record in ipairs(data.items) do
        local id = assert(record[idField])
        if not addon:ComparisonItemInScope(id, "PR", preRaidIndex) then blocked[#blocked + 1] = id end
    end
    table.sort(blocked)
    write("BigBiSListData.guide_index.preRaidScope={items=BigBiSListData.items,phaseIndex=", preRaidIndex, ",blocked={")
    for _, id in ipairs(blocked) do write("[", id, "]=true,") end
    write("}}\n")
    local questItems = {}
    for _, slot in ipairs(slotKeys) do
        local keys, lookup, search = {}, {}, {}
        for ordinal, item in ipairs(universe(slot)) do
            keys[ordinal] = quote(item.key)
            lookup[#lookup + 1] = "[" .. keys[ordinal] .. "]=" .. ordinal
            local name, seen = item.name:lower(), {}
            local function indexText(text)
                for offset = 1, #text - 2 do
                    local word = text:sub(offset, offset + 2)
                    -- Split only on whole bytes in ASCII, which is also the client's case-folding.
                    if not seen[word] and not word:find("[\128-\255]") then
                        seen[word] = true
                        local hits = search[word] or {}
                        local tail = hits[#hits]
                        if tail and tail[2] == ordinal - 1 then tail[2] = ordinal
                        else hits[#hits + 1] = {ordinal, ordinal} end
                        search[word] = hits
                    end
                end
            end
            indexText(name)
            indexText(slot:lower())
            for _, option in ipairs(routes(item).options or {}) do
                for _, key in ipairs({"source_summary", "zone", "label", "vendor_label", "source_filter_label", "cost_summary"}) do
                    if type(option[key]) == "string" then indexText(option[key]:lower()) end
                end
                for _, field in ipairs({"reputations", "cost_labels"}) do
                    for _, value in ipairs(option[field] or {}) do
                        if type(value) == "string" then indexText(value:lower()) end
                    end
                end
                local function quest(id)
                    id = tonumber(id)
                    if not id then return end
                    questItems[id] = questItems[id] or {}
                    questItems[id][item.key] = true
                end
                local source = option.source or {}
                quest(source.quest_id or source.type == "quest" and source.entity_id)
                for _, step in ipairs(source.quest_steps or {}) do quest(step.quest_id) end
            end
        end
        local words = {}
        for word in pairs(search) do words[#words + 1] = word end
        table.sort(words)
        write("do\nlocal slot={keys={", table.concat(keys, ","), "}, lookup={", table.concat(lookup, ","), "}, search={}}\n")
        for _, word in ipairs(words) do
            local ranges = {}
            for _, range in ipairs(search[word]) do
                ranges[#ranges + 1] = pack(range[1], 3)
                ranges[#ranges + 1] = pack(range[2], 3)
            end
            write("slot.search[", quote(word), "]=", quote(table.concat(ranges)), "\n")
        end
        write("BigBiSListData.guide_index.slots[", quote(slot), "]=slot\nend\n")
    end
    local quests = {}
    for id in pairs(questItems) do quests[#quests + 1] = id end
    table.sort(quests)
    for _, id in ipairs(quests) do
        local keys = {}
        for key in pairs(questItems[id]) do keys[#keys + 1] = quote(key) end
        table.sort(keys)
        write("BigBiSListData.guide_index.quests[", id, "]={", table.concat(keys, ","), "}\n")
    end
    out:close()
    return
end

write("do\nlocal archive={strings={},profiles={}}\n")
write("BigBiSListData.guide_index.classes[", quote(className), "]=archive\n")

local function intervals(contexts, id, routeCache, first, last)
    local known = routeCache[id]
    if known then return known end
    local route, result = routes({id = id}), {}
    local function add(level, final)
        local verified, reason = addon:IsStatRankGuideItemAvailable(id, contexts[level], route.options)
        if verified or reason == "missing_item_record" or reason == "unverified_route" then
            local ids, methods, hints = {}, {}, {}
            if verified then
                local names
                names, methods, hints = addon:GetGuideTargetActivities(contexts[level], route.options)
                for _, name in ipairs(names) do
                    if not activityIds[name] then
                        activities[#activities + 1] = name
                        activityIds[name] = #activities
                    end
                    ids[#ids + 1] = activityIds[name]
                end
            end
            result[#result + 1] = { level, final, verified, ids, methods, storeHints(hints) }
        end
    end
    if first == last then
        add(first, last)
    else
        for index, level in ipairs(route.levels) do
            add(level, (route.levels[index + 1] or last + 1) - 1)
        end
    end
    routeCache[id] = result
    return result
end

local function extend(ranges, level, grade)
    local last = ranges[#ranges]
    if last and last[2] == level - 1 and last[3] == grade then
        last[2] = level
    else
        ranges[#ranges + 1] = {level, level, grade}
    end
end

local function rangesAt(ranges, level)
    for _, range in ipairs(ranges) do
        if level <= range[2] then return range end
    end
    return ranges[#ranges]
end

local function packRanges(record)
    local data = {}
    for column, ranges in ipairs({record.ranked, record.verified, record.recommended, record.strength, record.leading}) do
        data[#data + 1] = digits[#ranges]
        for _, range in ipairs(ranges) do
            data[#data + 1] = digits[range[1]]
            data[#data + 1] = digits[range[2]]
            if column == 4 then data[#data + 1] = digits[range[3]] end
        end
    end
    return table.concat(data)
end

local function pages(order)
    local refs, buckets, page, count, bucketCount = {}, {}, {}, 0, 0
    local function finish()
        bucketCount = bucketCount + #page
        refs[#refs + 1] = pack(bucketCount, 3) .. pack(store(table.concat(page)), 4)
        page = {}
    end
    local function finishBucket()
        if #page > 0 then finish() end
        count = count + bucketCount
        buckets[#buckets + 1] = pack(count, 3) .. pack(store(table.concat(refs)), 4)
        refs, bucketCount = {}, 0
    end
    local prior
    for _, value in ipairs(order) do
        local bucket = math.floor(value / 17179869184)
        if prior and bucket ~= prior then finishBucket() end
        prior = bucket
        local ordinal = value % 131072
        page[#page + 1] = pack(ordinal, 3)
        -- Stable boundaries let adjacent levels share pages after insertions.
        if #page >= 96 or (#page >= 8 and (ordinal * 8191) % 29 == 0) then finish() end
    end
    if prior then finishBucket() end
    return store(table.concat(buckets))
end

local function sparseOrder(positions, limit)
    local masks, prefixes, mask, place, count = {}, {}, 0, 1, 0
    for position = 1, limit do
        if positions[position] then mask, count = mask + place, count + 1 end
        place = place * 2
        if place == 4096 or position == limit then
            masks[#masks + 1] = pack(mask, 2)
            mask, place = 0, 1
            if #masks % 5 == 0 then prefixes[#prefixes + 1] = pack(count, 3) end
        end
    end
    return store(table.concat(masks)), store(table.concat(prefixes)), count
end

local scoreOrders = {}
local function scoreOrder(slot, contexts, items, low, high)
    local context = contexts[low]
    local signature = { slot, context.spec, context.phase, low }
    for _, scaling in ipairs(context.referenceScenario.racial_scaling or {}) do
        if scaling.race_id == context.raceId then
            signature[#signature + 1] = scaling.stat .. "=" .. scaling.multiplier
        end
    end
    local key = table.concat(signature, "/")
    if scoreOrders[key] then return unpack(scoreOrders[key]) end
    local scores, effectPoints = {}, {}
    for ordinal, item in ipairs(items) do
        if rating:GetReferenceWindow(context, contexts[high], item, slot, function(level) return contexts[level] end, true) then
            local result = rating:GetUnfilteredReferenceEntry(context, item, slot)
            if result.score ~= nil then
                local effect = rating:ReferenceEffectPoints(context, item, slot, result.score)
                if effect and math.abs(effect) >= 0.00005 then
                    effectPoints[#effectPoints + 1] = pack(ordinal, 3) .. pack(math.floor(effect * 10000 + 0.5) + 2147483648, 6)
                end
                scores[#scores + 1] = { ordinal = ordinal, points = math.floor(result.score * 10000 + 0.5),
                    conditional = result.conditional and true or false }
            end
        end
    end
    table.sort(scores, function(a, b)
        if a.points ~= b.points then return a.points > b.points end
        return a.ordinal < b.ordinal
    end)
    local values, inverse, positions, groups = {}, {}, {}, {}
    local priorPoints
    for index, score in ipairs(scores) do
        local ordinal = score.ordinal
        values[index] = pack(ordinal + (score.conditional and 131072 or 0), 3)
        positions[ordinal] = index
        if score.points ~= priorPoints then
            if priorPoints then groups[#groups + 1] = pack(index - 1, 3) .. pack(priorPoints + 2147483648, 6) end
            priorPoints = score.points
        end
    end
    if priorPoints then groups[#groups + 1] = pack(#scores, 3) .. pack(priorPoints + 2147483648, 6) end
    local width = #scores < 4096 and 2 or 3
    for ordinal = 1, #items do inverse[ordinal] = pack(positions[ordinal] or 0, width) end
    local valuesRef, inverseRef, groupsRef = store(table.concat(values)), store(table.concat(inverse)), store(table.concat(groups))
    local saved = {scores, positions, valuesRef, inverseRef, groupsRef, width, store(table.concat(effectPoints))}
    scoreOrders[key] = saved
    return unpack(saved)
end

-- Keep the best reward for each distinct trip/cost, plus reviewed uses. A
-- normal page starts with competitive trips and the best of each acquisition
-- method. A dungeon filter can still address every reward through its posting.
local function pickPage(targets, records, items, state, level, fixedOnly)
    local trips, approaches, easiest, choices, picks = {}, {}, {}, {}, {}
    local best
    for _, value in ipairs(targets) do
        local ordinal = value % 131072
        local record, item = records[ordinal], items[ordinal]
        if not fixedOnly or source.items[item.key] then
            local pos = state.positions[ordinal]
            local points = pos and state.scores[pos].points or 0
            if points > 0 or record.reviewed then
                local distinct = record.reviewed or item.effect_rules or item.set_key
                for trip, route in pairs(record.methods[level]) do
                    local gate = easiest[route.family]
                    if not trips[trip] then
                        -- Retain candidates for a different personal baseline. The cold page
                        -- needs a distinct route or an easier requirement than the stronger pick.
                        choices[ordinal] = true
                        if not gate or route.level and route.level < gate then distinct = true end
                    end
                    if route.level and (not gate or route.level < gate) then easiest[route.family] = route.level end
                    if not approaches[route.method] or record.reviewed then picks[ordinal] = true end
                    trips[trip], approaches[route.method] = true, true
                end
                if distinct then choices[ordinal] = true end
                best = best or points
                if distinct and points >= best * 0.85 then picks[ordinal] = true end
            end
        end
    end
    local function members(set)
        local list = {}
        for _, value in ipairs(targets) do
            local ordinal = value % 131072
            if set[ordinal] then list[#list + 1] = pack(ordinal, 3) end
        end
        return pack(store(table.concat(list)), 4)
    end
    local hints = {}
    for _, value in ipairs(targets) do
        local ordinal = value % 131072
        if picks[ordinal] then hints[#hints + 1] = pack(records[ordinal].hints[level], 4) end
    end
    return members(picks) .. members(choices) .. pack(store(table.concat(hints)), 4)
end

local function buildSlot(slot, contexts, routeCache, first, last)
    local items, allowed, records, states = universe(slot), {}, {}, {}
    local function at(level) return contexts[level] end
    for ordinal, item in ipairs(items) do
        local low, high = rating:GetReferenceWindow(contexts[first], contexts[last], item, slot, at)
        if low then
            local record = {ordinal = ordinal, ranked = {}, verified = {}, recommended = {}, strength = {}, leading = {}, targets = {}}
            record.methods, record.hints = {}, {}
            if source.items[item.key] then
                record.fixed = {ranked = record.ranked, verified = record.verified, recommended = {}, leading = {}, strength = {}}
            end
            local timeline = intervals(contexts, item.id, routeCache, first, last)
            for _, interval in ipairs(timeline) do
                for level = math.max(low, interval[1]), math.min(high, interval[2]) do
                    extend(record.ranked, level)
                    if interval[3] then extend(record.verified, level) end
                    if #interval[4] > 0 then
                        record.targets[level], record.methods[level], record.hints[level] = interval[4], interval[5], interval[6]
                    end
                    record[level] = true
                end
            end
            if record.ranked[1] then
                record.reviewed = rating:GetReviewedGuideEffect(contexts[first], item) ~= nil
                records[ordinal] = record
                allowed[#allowed + 1] = record
            end
        end
    end
    if #allowed == 0 then return end
    local low = first
    while low <= last do
        local context = contexts[low]
        local high = low
        while high < last and contexts[high + 1].weights == context.weights do
            local form = context.feralPolicy.form_level
            if form and high + 1 == form then break end
            if slot == "Trinket" and contexts[high + 1].isolatedScenario.isolated_swing_damage
                ~= context.isolatedScenario.isolated_swing_damage then break end
            high = high + 1
        end
        local scores, positions, valueRef, inverseRef, groupRef, inverseWidth, effects = scoreOrder(slot, contexts, items, low, high)
        local unresolved = {}
        for _, record in ipairs(allowed) do
            if not positions[record.ordinal] and not items[record.ordinal].utility then
                unresolved[#unresolved + 1] = record
            end
        end
        for level = low, high do
            local count, rank, leader, conditional, best, previous = 0, 0, 0, {}, nil, nil
            local bitmap, prefix, mask, power = {}, {}, 0, 1
            local uncertain = false
            local fixed, fixedLeader, fixedTies, fixedUncertain = {}, nil, {}, false
            for position, score in ipairs(scores) do
                local record = records[score.ordinal]
                if record and record[level] then
                    local points = score.points
                    if record.fixed then
                        fixed[position] = true
                        fixedLeader = fixedLeader or position
                        local fixedBest = scores[fixedLeader].points
                        if points == fixedBest then extend(record.fixed.leading, level) end
                        local ratio = fixedBest > 0 and math.floor(points * 100 / fixedBest + 1e-9) or 0
                        if record.reviewed or points > 0 and ratio >= 70 then extend(record.fixed.recommended, level) end
                        if ratio >= 70 then
                            local strength = ratio >= 97 and 5 or ratio >= 85 and 4 or 3
                            extend(record.fixed.strength, level, strength + (score.conditional and 8 or 0))
                        end
                        if score.conditional then
                            fixedUncertain = true
                            if fixedTies.last ~= points then
                                fixedTies[#fixedTies + 1] = pack(points + 2147483648, 6)
                                fixedTies.last = points
                            end
                        end
                    end
                    count = count + 1
                    if not best then best, leader = points, position end
                    if previous ~= points then rank, previous = count, points end
                    record[level] = rank
                    mask = mask + power
                    if rank == 1 then extend(record.leading, level) end
                    if score.conditional then
                        uncertain = true
                        if conditional.last ~= points then
                            conditional[#conditional + 1] = pack(points + 2147483648, 6)
                            conditional.last = points
                        end
                    end
                    local percent = best > 0 and math.floor(points * 100 / best + 1e-9) or (rank == 1 and 100 or 0)
                    if record.reviewed or (points > 0 and percent >= 70) then extend(record.recommended, level) end
                    -- Handle the one-option case after counting the eligible pool.
                    if best > 0 and percent >= 70 then
                        local strength = percent >= 97 and 5 or percent >= 85 and 4 or 3
                        extend(record.strength, level, strength + (score.conditional and 8 or 0))
                    end
                end
                power = power * 2
                if power == 4096 or position == #scores then
                    bitmap[#bitmap + 1] = pack(mask, 2)
                    power, mask = 1, 0
                    if #bitmap % 5 == 0 then prefix[#prefix + 1] = pack(count, 3) end
                end
            end
            if not uncertain then
                for _, record in ipairs(unresolved) do
                    if record[level] then uncertain = true; break end
                end
            end
            if count == 1 then
                local strengths = records[scores[leader].ordinal].strength
                local tail = strengths[#strengths]
                if tail and tail[2] == level then
                    if tail[1] == level then strengths[#strengths] = nil else tail[2] = level - 1 end
                end
            end
            for _, record in ipairs(allowed) do
                if record.reviewed and record[level] == true then
                    extend(record.recommended, level)
                    if record.fixed then extend(record.fixed.recommended, level) end
                end
            end
            states[level] = { valueRef, inverseRef, store(table.concat(bitmap)), count, leader, uncertain and 1 or 0,
                store(table.concat(conditional)), groupRef, inverseWidth, store(table.concat(prefix)),
                best and best + 2147483648 or 2147483648 }
            states[level].positions, states[level].scoreCount = positions, #scores
            states[level].effects = effects
            states[level].scores = scores
            for _, record in ipairs(unresolved) do
                if record[level] and source.items[items[record.ordinal].key] then fixedUncertain = true; break end
            end
            local masks, prefixes, fixedCount = sparseOrder(fixed, #scores)
            if fixedCount == 1 then
                local strengths = records[scores[fixedLeader].ordinal].fixed.strength
                local tail = strengths[#strengths]
                if tail and tail[2] == level then
                    if tail[1] == level then strengths[#strengths] = nil else tail[2] = level - 1 end
                end
            end
            states[level].fixed = pack(masks, 4) .. pack(prefixes, 4) .. pack(fixedCount, 3)
                .. pack(fixedLeader or 0, 3) .. pack((fixedLeader and scores[fixedLeader].points or 0) + 2147483648, 6)
                .. pack(store(table.concat(fixedTies)), 4) .. pack(fixedUncertain and 1 or 0, 1)
        end
        low = high + 1
    end

    local recordRefs, fixedRefs, verified = {}, {}, {}
    for ordinal = 1, #items do
        local record = records[ordinal]
        recordRefs[ordinal] = pack(record and store(packRanges(record)) or 0, 4)
        fixedRefs[ordinal] = pack(record and record.fixed and store(packRanges(record.fixed)) or 0, 4)
        if record and record.verified[1] then verified[#verified + 1] = pack(ordinal, 3) end
    end
    local packedLevels, targetLevels, pickLevels, fixedLevels = {}, {}, {}, {}
    for level = first, last do
        local state, ordered = states[level], {}
        local lowerScored, lowerUnscored, targets, byActivity = {}, {}, {}, {}
        for _, record in ipairs(allowed) do
            if record.targets[level] then
                targets[#targets + 1] = record.ordinal + (type(record[level]) == "number" and record[level] or 131071) * 131072
                for _, id in ipairs(record.targets[level]) do
                    byActivity[id] = byActivity[id] or {}
                    byActivity[id][#byActivity[id] + 1] = pack(record.ordinal, 3)
                end
            end
            local recommended = record.recommended[1] ~= nil
            local range = rangesAt(recommended and record.recommended or record.ranked, level)
            local routeLevel, order = level, recommended and 1 or 4
            if range[1] > level then routeLevel, order = range[1], 2
            elseif range[2] < level then routeLevel, order = range[2], 3 end
            local rank = record[routeLevel]
            if not rank then
                local ranked = rangesAt(record.ranked, level)
                rank = record[level < ranked[1] and ranked[1] or ranked[2]]
            end
            if order == 4 then
                local position = state.positions[record.ordinal]
                if position then lowerScored[position] = true else lowerUnscored[record.ordinal] = true end
            else
                if order == 3 then routeLevel = 60 - routeLevel end
                ordered[#ordered + 1] = record.ordinal + (type(rank) == "number" and rank or 131071) * 131072
                    + routeLevel * 17179869184 + order * 1099511627776
            end
        end
        table.sort(ordered)
        state[#state + 1] = pages(ordered)
        state[13], state[14], state[15] = sparseOrder(lowerScored, state.scoreCount)
        state[16], state[17], state[18] = sparseOrder(lowerUnscored, #items)
        state[19] = #ordered
        state[20] = state.effects
        local packed = {}
        for index, number in ipairs(state) do packed[index] = pack(number, index == 11 and 6 or 4) end
        packedLevels[#packedLevels + 1] = table.concat(packed)
        table.sort(targets)
        pickLevels[#pickLevels + 1] = pickPage(targets, records, items, state, level, false)
            .. pickPage(targets, records, items, state, level, true)
        fixedLevels[#fixedLevels + 1] = state.fixed
        for n, value in ipairs(targets) do targets[n] = pack(value % 131072, 3) end
        local destinations = {}
        for id = 1, #activities do
            if byActivity[id] then
                destinations[#destinations + 1] = pack(id, 2) .. pack(store(table.concat(byActivity[id])), 4)
            end
        end
        targetLevels[#targetLevels + 1] = pack(store(table.concat(targets)), 4) .. pack(store(table.concat(destinations)), 4)
    end
    return { store(table.concat(recordRefs)), store(table.concat(verified)), store(table.concat(packedLevels)), #allowed,
        store(table.concat(targetLevels)), store(table.concat(pickLevels)), store(table.concat(fixedLevels)), store(table.concat(fixedRefs)) }
end

local specKeys = {}
for key in pairs(source.profiles) do
    if key:match("^([^/]+)/") == className then specKeys[#specKeys + 1] = key end
end
table.sort(specKeys)
local availabilityCache = {}
for _, phase in ipairs(data.phases) do
    function addon:GetCurrentPhaseKey() return phase.key end
    addon.dataIndex = nil
    for _, key in ipairs(specKeys) do
        local spec = key:match("/(.+)$")
        for _, persona in ipairs(data.leveling_availability_rules.races) do
            local legal = false
            for _, class in ipairs(persona.classes) do if class == className then legal = true end end
            if legal then
                local side = persona.name .. "/" .. persona.faction .. "/" .. phase.key
                local previous = availabilityCache[side] or {}
                availabilityCache[side] = previous
                local values = {}
                for _, mode in ipairs({"LEVELING", "PR"}) do
                    local first, last = 1, 59
                    if mode == "PR" then first, last = 60, 60 end
                    local contexts = {}
                    previous[mode] = previous[mode] or {}
                    for level = first, last do
                        contexts[level] = assert(rating:GetGuideContext(className, spec, mode, level, persona.name, persona.faction))
                    end
                    local encoded = {}
                    for _, slot in ipairs(slotKeys) do
                        local info = buildSlot(slot, contexts, previous[mode], first, last)
                        if info then encoded[#encoded + 1] = "[" .. quote(slot) .. "]={" .. table.concat(info, ",") .. "}" end
                    end
                    values[mode] = "{" .. table.concat(encoded, ",") .. "}"
                end
                flush()
                write("archive.profiles[", quote(spec .. "/" .. side), "]={LEVELING=", values.LEVELING, ",PR=", values.PR, "}\n")
                io.stderr:write(className, "/", spec, "/", persona.name, "/", persona.faction, "  ", stringCount, " strings\n")
                io.stderr:flush()
            end
        end
        scoreOrders = {}
    end
end
for id, name in ipairs(activities) do activities[id] = quote(name) end
write("archive.hints={", table.concat(routeHints, ","), "}\n")
write("archive.activities={", table.concat(activities, ","), "}\nend\n")
out:close()
