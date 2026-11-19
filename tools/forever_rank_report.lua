assert(_VERSION == "Lua 5.1")
dofile("DataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")

local addon, data = BigBiSList, BigBiSListData
local phase = arg[1]
local supported
for _, entry in ipairs(data.phases) do
    if entry.key == phase then supported = true; break end
end
assert(supported, "Unknown Forever content phase " .. tostring(phase))
function addon:GetCurrentPhaseKey() return phase end

local race, faction
function UnitRace() return race, race end
function UnitFactionGroup() return faction end

local function report(class, spec, level, mode)
    local filters = { race = race, faction = faction }
    local groups = mode == "leveling" and addon:GetLevelingRows(class, spec, level, filters)
        or addon:GetPhaseRows(class, spec, "PR", filters)
    print("context", table.concat({ class, spec, race, faction, mode, tostring(level) }, "/"))
    for _, group in ipairs(groups) do
        for _, row in ipairs(group.items) do
            local rank = row.stat_rank or {}
            local source = row.matched_access_option or {}
            local origin = source.source or {}
            local band = mode == "pre_raid" and (row.guide_bis and "bis" or "reviewed")
                or (row.guide_alternate and "more" or "featured")
            print("row", group.slot, row.stat_identity or row.variant_id or row.item_id, band,
                rank.score and string.format("%.4f", rank.score) or "", rank.rank or "",
                source.source_type or "", origin.quest_id or origin.entity_id or "", addon:GetActivityGroup(row) or "")
        end
    end
end

local specs = {}
for key in pairs(data.stat_rank.profiles) do specs[#specs + 1] = key end
table.sort(specs)

if arg[2] == "coverage" then
    local rating = addon.ForeverGearRating
    local catalog = rating:GetCatalog(data.stat_rank)
    local slots, levels = {}, {}
    for slot in pairs(catalog.slots) do
        if slot ~= "One Hand" then slots[#slots + 1] = slot end
    end
    table.sort(slots)
    if arg[3] then
        for value in arg[3]:gmatch("%d+") do levels[#levels + 1] = tonumber(value) end
    else
        for level = 1, 60 do levels[#levels + 1] = level end
    end

    local poolScopes, emptyPools, rarity = 0, 0, {}
    local quality = { poor = 0, common = 1, uncommon = 2, rare = 3, epic = 4, legendary = 5 }
    local function itemQuality(item)
        if rarity[item.id] == nil then
            local meta = addon:GetItemMeta(item.id)
            rarity[item.id] = meta and quality[meta.quality] or false
        end
        return rarity[item.id]
    end

    local findings = {}
    local function note(scope, level, reason, item, score, peer)
        local key = table.concat({item.key, reason, peer and peer.item.key or ""}, "\t")
        local finding = findings[key]
        if not finding then finding = {count = 0}; findings[key] = finding end
        finding.count = finding.count + 1
        if not finding.example or (score and score > finding.score) then
            finding.score = score or -math.huge
            finding.example = {scope, level, score or "", peer and peer.score or ""}
        end
    end

    local function audit(class, spec, level, list)
        local filters = {race = race, faction = faction}
        local groups = list == "LEVELING" and addon:GetLevelingRows(class, spec, level, filters)
            or addon:GetPhaseRows(class, spec, "PR", filters)
        local shown = {}
        for _, group in ipairs(groups) do
            local byKey = {}
            for _, row in ipairs(group.items) do byKey[row.stat_identity or row.variant_id or tostring(row.item_id)] = true end
            shown[group.slot] = byKey
        end
        local context = rating:GetGuideContext(class, spec, list, level, race, faction)
        for _, slot in ipairs(slots) do
            local scope = table.concat({ class, spec, race, faction, list, slot }, "/")
            local pool, visible = rating:GetGuidePlacement(context, slot), shown[slot] or {}
            local best, higherRarity = nil, {}
            for _, entry in ipairs(pool.rows) do
                if entry.score and entry.score > 0 and rating:HasGuideRoleStats(context, entry.item, slot) then
                    best = best or entry
                    if entry.conditional and (visible[entry.item.key] or entry == best) then
                        note(scope, level, "unresolved_effect", entry.item, entry.score, nil)
                    end
                    local grade = itemQuality(entry.item)
                    if grade then
                        for lowerGrade = 0, grade - 1 do
                            local lower = higherRarity[lowerGrade]
                            if lower and lower.score > entry.score then
                                note(scope, level, "rarity_inversion", lower.item, lower.score, entry)
                                higherRarity[lowerGrade] = nil
                            end
                        end
                        if not higherRarity[grade] and entry.score >= best.score * 0.70 then higherRarity[grade] = entry end
                    end
                end
            end
            poolScopes = poolScopes + 1
            if not best then emptyPools = emptyPools + 1 end
            local threshold = best and best.score * 0.70 or 0
            local function check(item)
                local entry = pool.byVariant[item.key] or rating:GetReferenceCandidate(context, item, slot)
                if not (entry and entry.score and entry.score > 0 and entry.score + 1e-8 >= threshold
                    and not visible[item.key] and rating:HasGuideRoleStats(context, item, slot)) then return end
                if not pool.byVariant[item.key] then
                    local available, reason = addon:IsStatRankGuideItemAvailable(item.id, context)
                    note(scope, level, available and "rank_filter" or reason, item, entry.score, best)
                else
                    note(scope, level, "display_filter", item, entry.score, best)
                end
            end
            for _, item in ipairs(catalog.slots[slot] or {}) do check(item) end
            if slot == "Main Hand" or slot == "Off Hand" then
                for _, item in ipairs(catalog.slots["One Hand"] or {}) do check(item) end
            end
        end
    end

    local contexts = 0
    for _, key in ipairs(specs) do
        local class, spec = key:match("^([^/]+)/(.+)$")
        for _, persona in ipairs(data.leveling_availability_rules.races) do
            for _, allowed in ipairs(persona.classes) do
                if allowed == class then
                    race, faction = persona.name, persona.faction
                    for _, level in ipairs(levels) do
                        local list = level == 60 and "PR" or "LEVELING"
                        audit(class, spec, level, list)
                        contexts = contexts + 1
                    end
                    break
                end
            end
        end
    end
    local keys = {}
    for key in pairs(findings) do keys[#keys + 1] = key end
    table.sort(keys)
    print("coverage", contexts, poolScopes, emptyPools)
    for _, key in ipairs(keys) do print("finding", key, findings[key].count, unpack(findings[key].example)) end
    local ids = {}
    for _, item in pairs(catalog.items) do ids[item.id] = true end
    local sorted = {}
    for id in pairs(ids) do sorted[#sorted + 1] = id end
    table.sort(sorted)
    for _, id in ipairs(sorted) do print("catalog", id) end
    return
end

for _, key in ipairs(specs) do
    local class, spec = key:match("^([^/]+)/(.+)$")
    local persona
    for _, candidate in ipairs(data.leveling_availability_rules.races) do
        for _, allowed in ipairs(candidate.classes) do
            if allowed == class then persona = candidate; break end
        end
        if persona then break end
    end
    assert(persona, key .. " has no reviewed persona")
    race, faction = persona.name, persona.faction
    for _, band in ipairs(data.stat_rank.profiles[key].leveling.weights) do report(class, spec, band[2], "leveling") end
    report(class, spec, 60, "pre_raid")
end
race, faction = "Human", "Alliance"
report("Paladin", "Retribution", 48, "leveling")
