-- Random access to the reference rankings shipped with Forever.
local addon = BigBiSList
local rating = addon.ForeverGearRating
if not rating then return end

local bundle, source = BigBiSListData.guide_index, BigBiSListData.runtime_indexes
local INDEX_VERSION = 4
if bundle and not (bundle.version == INDEX_VERSION and source and source.guide_signature and bundle.signature == source.guide_signature) then
    BigBiSListData.guide_index = nil
end

local BYTE_OFFSET, RECORD_WIDTH, BLOCK_SIZE, ARCHIVE_CHUNK_SIZE = 48, 82, 420, 32768
local POINT_ZERO = 2147483648
local powers, bitCounts = {}, {[0] = 0}
for index = 0, 12 do powers[index] = 2 ^ index end
for value = 1, 63 do bitCounts[value] = bitCounts[math.floor(value / 2)] + value % 2 end

local function read(text, offset, width)
    local value = 0
    for index = offset, offset + width - 1 do
        value = value * 64 + text:byte(index) - BYTE_OFFSET
    end
    return value
end

local function archiveArray(chunks, offsets)
    if not offsets then return chunks end
    return setmetatable({}, { __index = function(_, index)
        local low = read(offsets, (index - 1) * 5 + 1, 5)
        local high = read(offsets, index * 5 + 1, 5)
        local chunkIndex = math.floor(low / ARCHIVE_CHUNK_SIZE) + 1
        local start = low % ARCHIVE_CHUNK_SIZE + 1
        local length = high - low
        if length == 0 then return "" end
        local head = chunks[chunkIndex]
        if start + length - 1 <= #head then return head:sub(start, start + length - 1) end
        head = head:sub(start)
        return head .. chunks[chunkIndex + 1]:sub(1, length - #head)
    end })
end

local function block(archive, id)
    local cache = archive.decoded
    if not cache then
        cache = { data = {}, order = {}, next = 1 }
        archive.decoded = cache
    end
    local text = cache.data[id]
    if text then return text end
    local encoded = archive.blocks[id]
    local start = 1
    local marker = encoded:find("~", start, true)
    if not marker then return encoded end
    local decoded = ""
    repeat
        decoded = decoded .. encoded:sub(start, marker - 1)
        local distance, length = read(encoded, marker + 1, 2), read(encoded, marker + 3, 1) + 4
        local pattern = decoded:sub(#decoded - distance + 1)
        local repeats = math.ceil(length / #pattern)
        decoded = decoded .. pattern:rep(repeats):sub(1, length)
        start = marker + 4
        marker = encoded:find("~", start, true)
    until not marker
    text = decoded .. encoded:sub(start)
    local position = cache.next
    local previous = cache.order[position]
    if previous then cache.data[previous] = nil end
    cache.order[position], cache.data[id] = id, text
    cache.next = position % 256 + 1
    return text
end

local function size(text)
    return text:byte(1) == 126 and read(text, 2, 4) or #text
end

local function packedRead(archive, text, offset, width)
    if text:byte(1) ~= 126 then return read(text, offset, width) end
    local zero = offset - 1
    local index, within = math.floor(zero / BLOCK_SIZE), zero % BLOCK_SIZE + 1
    local chunk = block(archive, read(text, 6 + 4 * index, 4))
    if within + width - 1 <= #chunk then return read(chunk, within, width) end
    local head = chunk:sub(within)
    local tail = block(archive, read(text, 10 + 4 * index, 4))
    return read(head .. tail:sub(1, width - #head), 1, width)
end

local function lowerBound(count, value, at)
    local lo, hi = 1, count + 1
    while lo < hi do
        local mid = math.floor((lo + hi) / 2)
        if at(mid) < value then lo = mid + 1 else hi = mid end
    end
    return lo
end

local function choice(archive, directory, index)
    local position = lowerBound(size(directory) / 7, index, function(position)
        return packedRead(archive, directory, (position - 1) * 7 + 1, 3)
    end)
    local offset = (position - 1) * 7
    local prior = position > 1 and packedRead(archive, directory, offset - 6, 3) or 0
    return archive.strings[packedRead(archive, directory, offset + 4, 4)], index - prior
end

local function profile(context, phase)
    local bundle = BigBiSListData.guide_index
    if not bundle or bundle.version ~= INDEX_VERSION or bundle.data ~= context.catalog.data then return end
    local archive = bundle.classes[context.class]
    if not archive or not context.race or not context.faction then return end
    if not archive.open then
        archive.open = true
        archive.strings = archiveArray(archive.strings, archive.stringsOffsets)
        archive.blocks = archiveArray(archive.blocks, archive.blocksOffsets)
    end
    local key = context.spec .. "/" .. context.race .. "/" .. context.faction .. "/" .. (addon.phaseOrder[context.phaseIndex] or "")
    local spec = archive.profiles[key]
    local page = spec and spec[phase or context.phase]
    if page then return bundle, archive, page end
end

local function dataset(context, slot, phase)
    local bundle, archive, spec = profile(context, phase)
    if not spec then return end
    local indices = bundle.slots[slot]
    local slotInfo = spec[slot]
    if not (indices and slotInfo) then return false end
    local fixedRanks = not context.catalog.rollBuildMatches and slotInfo[8]
    return { archive = archive, indices = indices, ranges = archive.strings[fixedRanks or slotInfo[1]],
        verified = archive.strings[slotInfo[2]], states = archive.strings[slotInfo[3]], count = slotInfo[4],
        targets = archive.strings[slotInfo[5]], picks = archive.strings[slotInfo[6]],
        fixed = not context.catalog.rollBuildMatches and archive.strings[slotInfo[7]],
        first = (phase or context.phase) == "LEVELING" and 1 or 60, slot = slot }
end

function rating:GetGuideTargetPage(data, level, selection)
    if data and data.core then
        local list = data.members
        return {count = #list, at = function(i) return list[i] end, visitActivities = function() end}
    end
    if not data or not data.targets then return end
    local offset = (level - data.first) * 8 + 1
    local archive = data.archive
    local members, routes
    if selection then
        local start = (level - data.first) * 24 + (data.fixed and 12 or 0) + 1
        members = archive.strings[packedRead(archive, data.picks, start + (selection == "candidates" and 4 or 0), 4)]
        if selection == "picks" then
            local hints = archive.strings[packedRead(archive, data.picks, start + 8, 4)]
            routes = function(index, accept)
                local ids = archive.strings[packedRead(archive, hints, (index - 1) * 4 + 1, 4)]
                local market
                for pos = 1, size(ids), 3 do
                    local hint = archive.hints[packedRead(archive, ids, pos, 3)]
                    if accept(hint) then
                        if hint[6] == "" then return hint end
                        market = market or hint
                    end
                end
                return market
            end
        end
    else
        members = archive.strings[packedRead(archive, data.targets, offset, 4)]
    end
    return {count = size(members) / 3, route = routes, at = function(index)
        return packedRead(archive, members, (index - 1) * 3 + 1, 3)
    end, visitActivities = function(visit)
        local activities = archive.strings[packedRead(archive, data.targets, offset + 4, 4)]
        for pos = 1, size(activities), 6 do
            local id = packedRead(archive, activities, pos, 2)
            local items = archive.strings[packedRead(archive, activities, pos + 2, 4)]
            visit(archive.activities[id], items, size(items) / 3, function(i)
                return packedRead(archive, items, (i - 1) * 3 + 1, 3)
            end)
        end
    end}
end

-- The postings cover item, slot, source, vendor, cost and reputation text.
local function searchRanges(indices, lower)
    local hits
    for offset = 1, #lower - 2 do
        local token = lower:sub(offset, offset + 2)
        if not token:find("[\128-\255]") then
            local matches = indices.search[token]
            if not matches then return "" end
            if not hits or #matches < #hits then hits = matches end
        end
    end
    return hits
end

function rating:GuideSearchPredicate(indices, search)
    if indices.core then return end
    local hits = searchRanges(indices, search:lower())
    if not hits then return end
    local count = #hits / 6
    return function(ordinal)
        local index = lowerBound(count, ordinal, function(i) return read(hits, (i - 1) * 6 + 4, 3) end)
        return index <= count and read(hits, (index - 1) * 6 + 1, 3) <= ordinal
    end
end

function rating:FindGuideItem(context, indices, search, owned, slot)
    local id = tonumber(search:match("item:(%d+)"))
    if id then
        local key = self:NormalizeLink(id, search)
        return key and indices.lookup[key], key
    end
    if search == "" then return end
    local lower = search:lower()
    for _, worn in pairs(owned and owned.equippedSlots or {}) do
        local key = self:NormalizeLink(worn.item_id, worn.item_link) or tostring(worn.item_id)
        local ordinal = indices.lookup[key]
        local item = ordinal and (context.catalog.observed[key] or context.catalog.items[key])
        if item and item.name:lower() == lower then return ordinal, key, worn.item_link end
    end
    if source and source.guide_core and source.guide_core.items == context.catalog.data.items then
        local names = source.guide_core.names
        local function named(name)
            local i = lowerBound(#names, name, function(pos) return context.catalog.items[names[pos]].name:lower() end)
            local closest, closestLevel, fallback
            while i <= #names do
                local key, item = names[i], context.catalog.items[names[i]]
                if item.name:lower() ~= name then break end
                if indices.lookup[key] or item.has_random_stats and (item.slot == slot or item.slot == "One Hand" and slot == "Main Hand") then
                    fallback = fallback or key
                    if not item.excluded then
                        local record = self:GetPackedLevelingRecord(context, slot, key, true)
                        local range = record and self:LevelingRangeAt(record.verified, context.level)
                        if range and context.level >= range.firstLevel and context.level <= range.lastLevel then return key end
                        if range and range.firstLevel > context.level and (not closestLevel or range.firstLevel < closestLevel) then
                            closest, closestLevel = key, range.firstLevel
                        end
                    end
                end
                i = i + 1
            end
            return closest or fallback
        end
        local key = named(lower)
        if not key then
            for bonus, template in pairs(context.catalog.data.roll_templates or {}) do
                local suffix = " " .. template[1]:lower()
                if lower:sub(-#suffix) == suffix then
                    local base = named(lower:sub(1, -#suffix - 1))
                    local exact = base and (base .. ":0:0:0:1:" .. bonus)
                    if exact and context.catalog.items[exact] then key = exact; break end
                end
            end
        end
        return key and indices.lookup[key], key
    end
    local hits = searchRanges(indices, lower)
    if not hits then return end
    local checkpoint = self:GetWorkCheckpoint()
    local fallbackOrdinal, fallbackKey
    for pos = 1, #hits, 6 do
        for ordinal = read(hits, pos, 3), read(hits, pos + 3, 3) do
            if checkpoint then checkpoint() end
            local key = indices.keys[ordinal]
            local item = context.catalog.items[key]
            if item.name:lower() == lower then
                if not slot or not item.excluded and self:GetPackedGuideEntry(context, slot, key) then return ordinal, key end
                if not fallbackKey then fallbackOrdinal, fallbackKey = ordinal, key end
            end
            if item.variant_id then
                local base = context.catalog.items[tostring(item.id)]
                if base and base.name:lower() == lower and not fallbackKey then fallbackKey = base.key end
            end
        end
    end
    return fallbackOrdinal, fallbackKey
end

local function coreSlots(context)
    local core = source and source.guide_core
    if not core or core.data ~= context.catalog.data or core.items ~= core.data.items then return end
    local profileKey = table.concat({context.class, context.spec, context.race or "", context.faction or ""}, "/")
    local levels = core.profiles[profileKey]
    if not levels then return end
    local slots = {}
    for _, slot in ipairs(addon.slotOrder) do
        local name = slot
        local identities = setmetatable({}, {__index = function(_, key)
            local item = type(key) == "string" and context.catalog.items[key]
            if item and (item.slot == name or item.slot == "One Hand" and (name == "Main Hand" or name == "Off Hand")) then return key end
        end})
        slots[slot] = {core = true, slot = slot, members = {}, ranges = {}, indices = {core = true, keys = identities, lookup = identities}}
    end
    local function add(slot, key, low, high)
        local group = slots[slot]
        if group and not group.ranges[key] then
            group.members[#group.members + 1] = key
            group.count = #group.members
            group.ranges[key] = {firstLevel = low, lastLevel = high}
        end
    end
    if context.leveling then
        local function field(ref, name)
            local col = source.recommendation_columns[name]
            return col[3][read(col[2], (ref - 1) * col[1] + 1, col[1])]
        end
        for _, ref in ipairs(core.pages[levels[context.level]] or {}) do
            add(field(ref, "slot"), tostring(field(ref, "item_id")), field(ref, "level_min"), field(ref, "level_max"))
        end
    else
        local index = addon:GetDataIndex()
        local class = index.useRefsByClassSpecPhase[context.class] or {}
        local refs = (class[context.spec] or {})[context.phase] or {}
        local fields = index.schemaPositions.use
        for _, ref in ipairs(refs) do
            local row = BigBiSListData.uses[ref]
            add(row[fields.slot], tostring(row[fields.item_id]), context.level, context.level)
        end
    end
    context.coreGuide = true
    return slots
end

function rating:GetPackedGuide(context)
    if not context then return end
    local bundle = profile(context)
    if not context.packedGuide then
        context.packedGuide = bundle and setmetatable({}, { __index = function(slots, slot)
            local data = dataset(context, slot)
            rawset(slots, slot, data)
            return data
        end }) or coreSlots(context)
    end
    return context.packedGuide
end

local function state(data, level)
    local archive = data.archive
    local offset = (level - data.first) * RECORD_WIDTH
    local function field(index, width)
        local address = (index - 1) * 4 + (index <= 11 and 1 or 3)
        return packedRead(archive, data.states, offset + address, width or 4)
    end
    local current = {
        order = archive.strings[field(1)], inverse = archive.strings[field(2)], masks = archive.strings[field(3)],
        count = field(4), leader = field(5), unresolved = field(6) == 1, conditional = archive.strings[field(7)],
        groups = archive.strings[field(8)], inverseWidth = field(9), prefixes = archive.strings[field(10)], effects = archive.strings[field(20)],
        best = (field(11, 6) - POINT_ZERO) / 10000, browse = archive.strings[field(12)], featuredCount = field(19),
        low = {masks = archive.strings[field(13)], prefixes = archive.strings[field(14)], count = field(15)},
        unscored = {masks = archive.strings[field(16)], prefixes = archive.strings[field(17)], count = field(18)},
    }
    if data.fixed then
        local base = (level - data.first) * 25
        local function get(at, width) return packedRead(archive, data.fixed, base + at, width) end
        current.masks, current.prefixes = archive.strings[get(1, 4)], archive.strings[get(5, 4)]
        current.count, current.leader = get(9, 3), get(12, 3)
        current.best = (get(15, 6) - POINT_ZERO) / 10000
        current.conditional, current.unresolved = archive.strings[get(21, 4)], get(25, 1) == 1
    end
    return current
end

local function countBits(mask)
    return bitCounts[mask % 64] + bitCounts[math.floor(mask / 64)]
end

local function before(archive, levelState, position)
    local index = position - 1
    local blockNumber, boundary = math.floor(index / 12), index % 12
    local group = math.floor(blockNumber / 5)
    local count = group > 0 and packedRead(archive, levelState.prefixes, (group - 1) * 3 + 1, 3) or 0
    for offset = group * 5, blockNumber - 1 do
        count = count + countBits(packedRead(archive, levelState.masks, offset * 2 + 1, 2))
    end
    if boundary > 0 then
        count = count + countBits(packedRead(archive, levelState.masks, blockNumber * 2 + 1, 2) % powers[boundary])
    end
    return count
end

local function recordText(data, ordinal)
    local ref = packedRead(data.archive, data.ranges, (ordinal - 1) * 4 + 1, 4)
    return ref > 0 and data.archive.strings[ref] or nil
end

local function readRanges(data, ordinal, upto)
    local text = recordText(data, ordinal)
    if not text then return end
    -- A record is small and is kept in one chunk.
    if text:byte(1) == 126 then text = block(data.archive, read(text, 6, 4)) end
    local lists, offset = {}, 1
    for column = 1, upto or 5 do
        local count = text:byte(offset) - BYTE_OFFSET
        offset = offset + 1
        local ranges = {}
        lists[column] = ranges
        for index = 1, count do
            local first, last = text:byte(offset, offset + 1)
            local range = {firstLevel = first - BYTE_OFFSET, lastLevel = last - BYTE_OFFSET}
            offset = offset + 2
            if column == 4 then
                local strength = text:byte(offset) - BYTE_OFFSET
                range.grade, range.estimated = strength % 8, strength >= 8 or nil
                offset = offset + 1
            end
            ranges[index] = range
        end
    end
    return unpack(lists)
end

local function inside(ranges, level)
    local range = rating:LevelingRangeAt(ranges, level)
    return range and range.firstLevel <= level and range.lastLevel >= level
end

local function resolve(data, context, ordinal, level, verified)
    local archive = data.archive
    local levelState
    if level == context.level then
        data.current = data.current or state(data, level)
        levelState = data.current
    else
        levelState = state(data, level)
    end
    local width = levelState.inverseWidth
    local position = packedRead(archive, levelState.inverse, (ordinal - 1) * width + 1, width)
    local key = data.indices.keys[ordinal]
    local item = context.catalog.items[key]
    local entry = { item = item, slot = data.slot, level = level, phase = context.phase, spec = context.spec,
        effectContext = item.effect_rules and context, source_unknown = not verified or nil }
    if position == 0 then
        local fallback = rating:GetUnfilteredReferenceEntry(context, item, data.slot)
        entry.status, entry.conditional = fallback.status, fallback.conditional
        return entry
    end
    local function endpoint(group) return packedRead(archive, levelState.groups, (group - 1) * 9 + 1, 3) end
    local band = lowerBound(size(levelState.groups) / 9, position, endpoint)
    local first = band == 1 and 1 or endpoint(band - 1) + 1
    local last = endpoint(band)
    local score = packedRead(archive, levelState.groups, (band - 1) * 9 + 4, 6)
    local rank = before(archive, levelState, first) + 1
    local ties = before(archive, levelState, last + 1) - rank + 1
    entry.rank, entry.total, entry.score = rank, levelState.count, (score - POINT_ZERO) / 10000
    if item.effect_rules then
        local effects = levelState.effects
        local count = size(effects) / 9
        local function at(i) return packedRead(archive, effects, (i - 1) * 9 + 1, 3) end
        local i = lowerBound(count, ordinal, at)
        entry.effectPoints = i <= count and at(i) == ordinal and (packedRead(archive, effects, (i - 1) * 9 + 4, 6) - POINT_ZERO) / 10000 or 0
    end
    entry.tied = ties > 1 or nil
    entry.conditional = packedRead(archive, levelState.order, (position - 1) * 3 + 1, 3) >= 131072
    if entry.tied and size(levelState.conditional) > 0 then
        local function at(index) return -packedRead(archive, levelState.conditional, (index - 1) * 6 + 1, 6) end
        local n = size(levelState.conditional) / 6
        local index = lowerBound(n, -score, at)
        entry.conditional_tie = index <= n and at(index) == -score or nil
    end
    entry.provisional = rank == 1 and (levelState.unresolved or entry.source_unknown) or nil
    if levelState.count > 1 and levelState.count <= 12 and levelState.best > 0 and levelState.tiers == nil then
        local rows, n = {}, size(levelState.order) / 3
        for index = 1, levelState.count do
            local ordinalPosition = lowerBound(n, index, function(pos) return before(archive, levelState, pos + 1) end)
            local group = lowerBound(size(levelState.groups) / 9, ordinalPosition, endpoint)
            rows[index] = {score = (packedRead(archive, levelState.groups, (group - 1) * 9 + 4, 6) - POINT_ZERO) / 10000}
        end
        levelState.tiers = rating:GetPackedRankTiers(rows, levelState.count, levelState.best) or false
    end
    rating:ApplyPackedRankTier(entry, levelState.best, levelState.tiers)
    return entry
end

local function baseEntry(data, context, ordinal, level)
    if not ordinal then return end
    if data.fixed and not context.catalog.data.items[data.indices.keys[ordinal]] then return end
    local ranked, verified = readRanges(data, ordinal, 2)
    if inside(ranked, level) then return resolve(data, context, ordinal, level, inside(verified, level)) end
end

local function scoreAt(archive, levelState, position)
    local group = lowerBound(size(levelState.groups) / 9, position, function(index)
        return packedRead(archive, levelState.groups, (index - 1) * 9 + 1, 3)
    end)
    return (packedRead(archive, levelState.groups, (group - 1) * 9 + 4, 6) - POINT_ZERO) / 10000
end

local function liveChanges(data, context, level)
    local catalog = context.catalog
    if not (catalog.changedSlots and catalog.changedSlots[data.slot]) then return end
    data.liveLevels = data.liveLevels or {}
    local current = data.liveLevels[level]
    if current and current.revision == catalog.observedVersion then return current end
    local evaluated = level == context.level and context or rating:GetGuideContext(
        context.class, context.spec, context.phase, level, context.race, context.faction)
    local levelState = state(data, level)
    local changes = {revision = catalog.observedVersion, state = levelState, changes = {}, total = levelState.count,
        best = levelState.best, unresolved = levelState.unresolved}
    for key, item in pairs(catalog.observed) do
        if item.slot == data.slot or item.slot == "One Hand" and (data.slot == "Main Hand" or data.slot == "Off Hand") then
            local old = baseEntry(data, evaluated, data.indices.lookup[key], level)
            local new = rating:GetReferenceCandidate(evaluated, item, data.slot)
            if new then
                local verified, reason = addon:IsStatRankGuideItemAvailable(item.id, evaluated)
                if verified or reason == "unverified_route" or reason == "missing_item_record" then
                    new.source_unknown = not verified or nil
                else
                    new = nil
                end
            end
            if old or new then
                changes.changes[key] = {before = old, after = new}
                if old and old.score ~= nil then changes.total = changes.total - 1 end
                if new and new.score ~= nil then changes.total = changes.total + 1 end
                if new and not new.item.utility then
                    changes.unresolved = changes.unresolved or new.score == nil or new.conditional
                end
            end
        end
    end
    if next(changes.changes) then
        local best
        for index = 1, levelState.count do
            local position = lowerBound(size(levelState.order) / 3, index, function(pos)
                return before(data.archive, levelState, pos + 1)
            end)
            local ordinal = packedRead(data.archive, levelState.order, (position - 1) * 3 + 1, 3) % 131072
            if not changes.changes[data.indices.keys[ordinal]] then
                best = scoreAt(data.archive, levelState, position)
                break
            end
        end
        for _, diff in pairs(changes.changes) do
            local score = diff.after and diff.after.score
            if score and (not best or score > best) then best = score end
        end
        changes.best = best
    end
    data.liveLevels[level] = changes
    return changes
end

local function updatedEntry(data, context, key, level)
    local changes = liveChanges(data, context, level)
    local diff = changes and changes.changes[key]
    local entry
    if diff then
        if not diff.after then return end
        entry = {}
        for field, value in pairs(diff.after) do entry[field] = value end
    else
        entry = baseEntry(data, context, data.indices.lookup[key], level)
    end
    if not entry or entry.score == nil or not changes or not next(changes.changes) then return entry end
    local archive, levelState, score = data.archive, changes.state, entry.score
    local points = math.floor(score * 10000 + 0.5) + POINT_ZERO
    local groupCount = size(levelState.groups) / 9
    local function groupScore(index) return -packedRead(archive, levelState.groups, (index - 1) * 9 + 4, 6) end
    local group = lowerBound(groupCount, -points, groupScore)
    local function endPosition(index) return packedRead(archive, levelState.groups, (index - 1) * 9 + 1, 3) end
    local higher = group == 1 and 0 or before(archive, levelState, endPosition(group - 1) + 1)
    local tied = group <= groupCount and groupScore(group) == -points
        and before(archive, levelState, endPosition(group) + 1) - higher or 0
    local conditional = entry.conditional_tie or entry.conditional
    for _, change in pairs(changes.changes) do
        local old, new = change.before and change.before.score, change.after and change.after.score
        if old then
            if old > score then higher = higher - 1 elseif old == score then tied = tied - 1 end
        end
        if new then
            if new > score then higher = higher + 1
            elseif new == score then tied = tied + 1; conditional = conditional or change.after.conditional end
        end
    end
    entry.rank, entry.total, entry.tied = higher + 1, changes.total, tied > 1 or nil
    entry.provisional = entry.rank == 1 and (entry.source_unknown or changes.unresolved) or nil
    entry.conditional_tie = entry.tied and conditional or nil
    entry.score_percent, entry.tier, entry.placement_color = nil, nil, nil
    if changes.best then rating:ApplyPackedRankTier(entry, changes.best) end
    return entry
end

function rating:PackedLevelEntries(context, slot, level, callback)
    local slots = self:GetPackedGuide(context)
    local data = slots and slots[slot]
    if not data then return end
    if data.core then
        for _, key in ipairs(data.members) do
            local entry = self:GetPackedGuideEntry(context, slot, key, level)
            if entry then callback(entry) end
        end
        return
    end
    local levelState = state(data, level)
    for position = 1, size(levelState.order) / 3 do
        local mask = packedRead(data.archive, levelState.masks, math.floor((position - 1) / 12) * 2 + 1, 2)
        if math.floor(mask / powers[(position - 1) % 12]) % 2 == 1 then
            local ordinal = packedRead(data.archive, levelState.order, (position - 1) * 3 + 1, 3) % 131072
            local _, verified = readRanges(data, ordinal, 2)
            callback(resolve(data, context, ordinal, level, inside(verified, level)))
        end
    end
end

function rating:GetPackedScoredChoices(context, slot)
    local slots = self:GetPackedGuide(context)
    if not slots then return end
    local data = slots[slot]
    if not data then return false end
    if data.core then
        local rows = self:GetBrowsePlacements(context, slot)
        local i = 0
        return function()
            i = i + 1
            local row = rows[i]
            if row and row.score and row.score > 0 then return row end
        end
    end
    local levelState = state(data, context.level)
    local archive = data.archive
    local sizeInOrder = size(levelState.order) / 3
    local index = 0
    return function()
        index = index + 1
        if index > levelState.count then return end
        local position = lowerBound(sizeInOrder, index, function(at) return before(archive, levelState, at + 1) end)
        local score = scoreAt(archive, levelState, position)
        if score <= 0 then return end
        local ordinal = packedRead(archive, levelState.order, (position - 1) * 3 + 1, 3) % 131072
        return {item = context.catalog.items[data.indices.keys[ordinal]], score = score, slot = slot}
    end
end

function rating:GetPackedGuideEntry(context, slot, key, level)
    local slots = self:GetPackedGuide(context)
    if not slots then return nil, false end
    local data = slots[slot]
    if not data then return nil, true end
    if data.core then
        local item = context.catalog.observed[key] or context.catalog.items[key]
        if not item then return nil, true end
        local entry = self:GetReferenceCandidate(context, item, slot)
        if entry then
            local verified = addon:IsStatRankGuideItemAvailable(item.id, context)
            entry.source_unknown = not verified or nil
        end
        return entry, true
    end
    return updatedEntry(data, context, key, level or context.level), true
end

function rating:GetBrowsePlacements(context, slot, owned)
    local slots = self:GetPackedGuide(context)
    if not slots then return end
    local data, rows, seen = slots[slot], {}, {}
    if not data then return rows end
    local function add(key)
        if not seen[key] then
            seen[key] = true
            local entry = self:GetPackedGuideEntry(context, slot, key)
            if entry then rows[#rows + 1] = entry end
        end
    end
    local page = self:GetGuideTargetPage(data, context.level, owned and "candidates" or "picks")
    for i = 1, page.count do add(data.indices.keys[page.at(i)]) end
    for key in pairs(owned or {}) do
        if data.indices.lookup[key] or context.catalog.observed[key] then add(key) end
    end
    table.sort(rows, function(a, b)
        if a.score ~= b.score then return (a.score or -math.huge) > (b.score or -math.huge) end
        return a.item.key < b.item.key
    end)
    return rows
end

function rating:GetPackedBrowseOrdinal(data, level, index)
    if data.core then return data.members[index] end
    if index < 1 or index > data.count then return end
    data.current = data.current or state(data, level)
    local current = data.current
    if index > current.featuredCount then
        index = index - current.featuredCount
        local positions = current.low
        if index > positions.count then index, positions = index - positions.count, current.unscored end
        local count = positions == current.low and size(current.order) / 3 or #data.indices.keys
        local position = lowerBound(count, index, function(value) return before(data.archive, positions, value + 1) end)
        if positions == current.unscored then return position end
        return packedRead(data.archive, current.order, (position - 1) * 3 + 1, 3) % 131072
    end
    local directory, position = choice(data.archive, current.browse, index)
    local page, row = choice(data.archive, directory, position)
    return packedRead(data.archive, page, (row - 1) * 3 + 1, 3)
end

function rating:VisitPackedGuideOrdinals(data, level, search, verifiedOnly, visit, checkpoint)
    if data.core then
        for _, key in ipairs(data.members) do if checkpoint then checkpoint() end; visit(key) end
    elseif verifiedOnly then
        for offset = 1, size(data.verified), 3 do
            if checkpoint then checkpoint() end
            visit(packedRead(data.archive, data.verified, offset, 3))
        end
    elseif search and #search >= 3 and not search:sub(1, 3):find("[\128-\255]") then
        local matches = data.indices.search[search:sub(1, 3)] or ""
        for offset = 1, #matches, 6 do
            for ordinal = read(matches, offset, 3), read(matches, offset + 3, 3) do
                if checkpoint then checkpoint() end
                if recordText(data, ordinal) then visit(ordinal) end
            end
        end
    else
        for index = 1, data.count do
            if checkpoint then checkpoint() end
            visit(self:GetPackedBrowseOrdinal(data, level, index))
        end
    end
end

function rating:GetPackedLevelingRecord(context, slot, key, cheap)
    local slots = self:GetPackedGuide(context)
    if not slots then return nil, false end
    local data = slots[slot]
    local ordinal = data and data.indices.lookup[key]
    if not ordinal then return nil, true end
    if data.core then
        local range = data.ranges[key]
        if not range then return nil, true end
        local item = context.catalog.items[key]
        return {ranked = {range}, verified = {range}, recommended = {range}, strength = {}, leading = {},
            item = item, slot = slot, context = context, data = data, ordinal = key,
            note = self:GetReviewedGuideEffect(context, item)}, true
    end
    if data.fixed and not context.catalog.data.items[key] then return nil, true end
    local ranked, verified, recommended, strength, leading = readRanges(data, ordinal)
    if not ranked then return nil, true end
    local item = context.catalog.items[key]
    local record = { ranked = ranked, recommended = recommended, strength = strength, leading = leading,
        item = item, slot = slot, verified = verified, ordinal = ordinal, data = data, context = context,
        note = self:GetReviewedGuideEffect(context, item) }
    if not cheap then
        for _, range in ipairs(ranked) do
            range.firstEntry = resolve(data, context, ordinal, range.firstLevel, inside(verified, range.firstLevel))
            range.lastEntry = range.firstLevel == range.lastLevel and range.firstEntry
                or resolve(data, context, ordinal, range.lastLevel, inside(verified, range.lastLevel))
        end
    end
    return record, true
end

function rating:GetPackedLevelingSuccessor(record, placement)
    local leading = self:LevelingRangeAt(record.leading, placement.level)
    if not leading or leading.firstLevel > placement.level or leading.lastLevel < placement.level then return end
    for level = leading.lastLevel + 1, addon.maxLevelingLevel do
        if inside(record.ranked, level) and not inside(record.leading, level) then
            local data = record.data
            local levelState = state(data, level)
            if levelState.leader > 0 then
                local flagged = packedRead(data.archive, levelState.order, (levelState.leader - 1) * 3 + 1, 3)
                local key = data.indices.keys[flagged % 131072]
                local item = record.context.catalog.items[key]
                return {level = level, name = item.name, conditional = flagged >= 131072 or placement.conditional}
            end
        end
    end
end

function rating:PackedGuideRowInfo(context, slot, ordinal, targetLevel)
    local slots = self:GetPackedGuide(context)
    local data = slots and slots[slot]
    if not data then return end
    local key = data.indices.keys[ordinal]
    local record = self:GetPackedLevelingRecord(context, slot, key, true)
    if not record then return end
    local level = targetLevel or context.level
    local range = self:LevelingRangeAt(record.recommended[1] and record.recommended or record.ranked, level)
    local routeLevel, order = level, record.recommended[1] and 1 or 4
    if range.firstLevel > level then routeLevel, order = range.firstLevel, 2
    elseif range.lastLevel < level then routeLevel, order = range.lastLevel, 3 end
    local eligible = self:LevelingRangeAt(record.ranked, level)
    local evaluation = math.min(eligible.lastLevel, math.max(eligible.firstLevel, level))
    if targetLevel then
        routeLevel, order = evaluation, evaluation > context.level and 2 or evaluation < context.level and 3 or 1
    end
    local placement = self:GetPackedGuideEntry(context, slot, key, evaluation)
    if not placement then return end
    return record, placement, routeLevel, order, evaluation == level
end

-- Save plain, reproducible comparisons only. Runtime gear, frames and effect
-- traces contain references to the whole outfit and must stay in this session.
local function opportunityCache(context, missing)
    local owned, catalog = context.owned, context.catalog
    if missing or not source or not source.guide_signature or not owned or owned.equippedOnly
        or owned.bagsIncomplete or owned.inventoryIncomplete or next(context.pending or {})
        or not rating.inventory or context.equipmentFacts ~= rating.inventory.equipment
        or next(context.unresolvedCopies or {}) then return end
    if context.savedOpportunities and context.savedRevision == catalog.observedVersion then return context.savedOpportunities end
    -- An exact roll or enchant can change the baseline even when its item ID stays the same.
    local liveFacts = {}
    for _, copy in ipairs(context.ownedCopies or {}) do
        local item = copy.facts
        if item and (item.native or item.nativeFacts or catalog.observed[item.key]) then
            if item.stats_unavailable or item.unreadable_effects then return end
            local values = {item.key, tostring(item.level), tostring(item.unique_group), tostring(item.max_equipped)}
            for stat, value in pairs(item.stats or {}) do values[#values + 1] = stat .. "=" .. value end
            for _, effect in ipairs(item.effects or {}) do values[#values + 1] = effect end
            table.sort(values)
            liveFacts[#liveFacts + 1] = table.concat(values, "|")
        end
    end
    table.sort(liveFacts)
    context.savedRevision = catalog.observedVersion
    local talents = {}
    for id, rank in pairs(context.activeBuild and context.activeBuild.ranks or {}) do
        talents[#talents + 1] = tostring(id) .. "=" .. tostring(rank)
    end
    table.sort(talents)
    local _, build
    if GetBuildInfo then _, build = GetBuildInfo() end
    local generation = BigBiSListData.guide_index and BigBiSListData.guide_index.generation or source.guide_signature
    local signature = table.concat({generation, tostring(build or ""), context.class, context.spec,
        context.race or "", context.faction or "", context.phase, context.phaseIndex, context.level,
        context.activeBuild and "active" or "reference", table.concat(talents, ","), rating:GetGearSnapshotKey(owned),
        table.concat(liveFacts, "\030")}, "\029")
    local db = addon:GetCharacterDB()
    local saved = db.guideComparisons
    if type(saved) ~= "table" or saved.version ~= 2 or type(saved.sets) ~= "table" then
        saved = {version = 2, sets = {}}
        db.guideComparisons = saved
    end
    for _, entry in ipairs(saved.sets) do
        if entry.signature == signature then context.savedOpportunities = entry; return entry end
    end
    if #saved.sets >= 3 then table.remove(saved.sets, 1) end
    local entry = {signature = signature, values = {}, order = {}, next = 1}
    saved.sets[#saved.sets + 1], context.savedOpportunities = entry, entry
    return entry
end

function rating:ReadSavedOpportunity(context, item, key, missing)
    if item.native or not context.catalog.data.items[item.key] then return end
    local cache = opportunityCache(context, missing)
    local value = cache and cache.values[key]
    if not value then return end
    local definition
    for _, def in ipairs(addon:GetEquipmentSlotDefinitions()) do if def.key == value.physical then definition = def; break end end
    if not definition then return end
    local result = {definition = definition, slot = value.slot, delta = value.delta, basis = value.basis,
        roleDelta = value.roleDelta, roleDisplaced = value.roleDisplaced, status = value.status, bank = value.bank,
        weaponSetup = value.weaponSetup, replacements = {}}
    for _, entry in ipairs(value.displaced) do
        local owned = context.ownedFacts[entry.key]
        if entry.link and (not owned or owned.state ~= entry.state or owned.item_link ~= entry.link) then
            owned = nil
            for _, instance in ipairs(context.ownedCopies) do
                if instance.key == entry.key and instance.state == entry.state and instance.item_link == entry.link then
                    owned = instance
                    break
                end
            end
            if not owned then return end
        end
        local facts = owned and owned.facts or context.catalog.items[entry.key]
        if not facts then return end
        result.replacements[#result.replacements + 1] = {key = entry.key, slot = entry.slot, state = entry.state, name = entry.name, facts = facts, item_link = entry.link}
    end
    return result
end

function rating:SaveOpportunity(context, item, key, result, missing)
    if type(result.delta) ~= "number" or not result.definition or result.effectTrace or result.conditional
        or result.estimatedEffects or item.native or not context.catalog.data.items[item.key] then return end
    local cache = opportunityCache(context, missing)
    if not cache then return end
    local displaced = {}
    for i, entry in ipairs(result.replacements) do
        if not entry.facts then return end
        displaced[i] = {key = entry.key, name = entry.name, slot = entry.slot, state = entry.state, link = entry.item_link}
    end
    if not cache.values[key] then
        local prior = cache.order[cache.next]
        if prior then cache.values[prior] = nil end
        cache.order[cache.next], cache.next = key, cache.next % 256 + 1
    end
    cache.values[key] = {physical = result.definition.key, slot = result.slot, delta = result.delta,
        roleDelta = result.roleDelta, roleDisplaced = result.roleDisplaced, basis = result.basis,
        status = result.status, bank = result.bank, weaponSetup = result.weaponSetup, displaced = displaced}
end
