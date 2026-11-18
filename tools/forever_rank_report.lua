assert(_VERSION == "Lua 5.1")
dofile("DataForever.lua")
dofile("Config.lua")
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
