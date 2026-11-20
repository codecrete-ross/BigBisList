-- Check the shipped target pages against live eligibility at every access boundary.
assert(_VERSION == "Lua 5.1")
dofile("DataForever.lua")
dofile("GuideDataForever.lua")
dofile("Config.lua")
dofile("ForeverScoring.lua")
dofile("ForeverGearRating.lua")
dofile("DataIndex.lua")
dofile("ForeverGuide.lua")

local addon, data = BigBiSList, BigBiSListData
function addon:GetCurrentPhaseKey() return data.phases[1].key end
local rating = addon.ForeverGearRating
local catalog = rating:GetCatalog(data.stat_rank)
local items, seen = {}, {}
local ammunition = 0
local function include(id, reviewed)
    if seen[id] then return end
    seen[id] = true
    local item = catalog.items[tostring(id)]
    local levels, options = addon:GetGuideRouteTransitions(id)
    if reviewed then
        assert(item, "Missing item facts for " .. id)
        assert(options and #options > 0, "Missing routes for " .. id)
    end
    if options and #options > 0 then
        if item then
            items[#items + 1] = {id = id, item = item, levels = levels, options = options}
        else
            assert(addon:GetItemData(id).inventory_slot == "Ammo", "Missing equipment facts for sourced item " .. id)
            ammunition = ammunition + 1
        end
    end
end
for line in io.lines() do
    include(assert(tonumber(line)), true)
end
for id in pairs(data.runtime_indexes.items) do include(assert(tonumber(id)), false) end

local function pageIds(dataSlot, level, postings)
    local result = {all = {}, activities = {}}
    local page = rating:GetGuideTargetPage(dataSlot, level)
    if page then
        local function members(count, at)
            local ids = {}
            for index = 1, count do
                local key = dataSlot.indices.keys[at(index)]
                ids[tonumber(key:match("^%d+"))] = true
            end
            return ids
        end
        result.all = members(page.count, page.at)
        page.visitActivities(function(name, encoded, count, at)
            if not postings[encoded] then postings[encoded] = members(count, at) end
            result.activities[name] = postings[encoded]
        end)
    end
    return result
end

local contexts, checks, activities = 0, 0, 0
local function audit(class, spec, persona, mode)
    local first, last = 1, 59
    if mode == "PR" then first, last = 60, 60 end
    local levels, pages, postings = {}, {}, {}
    local function context(level)
        if not levels[level] then
            levels[level] = assert(rating:GetGuideContext(class, spec, mode, level, persona.name, persona.faction))
        end
        return levels[level]
    end
    local available = assert(rating:GetPackedGuide(context(first)), "Missing or stale published Forever Guide")
    for _, row in ipairs(items) do
        local item = row.item
        local slots = item.slot == "One Hand" and {"Main Hand", "Off Hand"} or {item.slot}
        for _, slot in ipairs(slots) do
            local low, high = rating:GetReferenceWindow(context(first), context(last), item, slot, context)
            if low then
                local function boundary(level)
                    if level < low or level > high then return end
                    local current = context(level)
                    if addon:IsStatRankGuideItemAvailable(row.id, current, row.options) then
                        local expected = addon:GetGuideTargetActivities(current, row.options)
                        if #expected == 0 then return end
                        pages[slot] = pages[slot] or {}
                        postings[slot] = postings[slot] or {}
                        local slotPages = pages[slot]
                        if not slotPages[level] then slotPages[level] = pageIds(available[slot], level, postings[slot]) end
                        local page = slotPages[level]
                        local function missing(name)
                            error(table.concat({"Missing packed route", row.id, class, spec, persona.name, mode, level, slot, name}, " / "))
                        end
                        if not page.all[row.id] then missing("all targets") end
                        checks = checks + 1
                        for _, name in ipairs(expected) do
                            if not (page.activities[name] and page.activities[name][row.id]) then missing(name) end
                            activities = activities + 1
                        end
                    end
                end
                boundary(low)
                if high ~= low then boundary(high) end
                for _, level in ipairs(row.levels) do
                    if level > low and level < high then boundary(level) end
                end
            end
        end
    end
    contexts = contexts + 1
end

for _, phase in ipairs(data.phases) do
    function addon:GetCurrentPhaseKey() return phase.key end
    addon.dataIndex = nil
    for name in pairs(data.stat_rank.profiles) do
        local class, spec = name:match("^([^/]+)/(.+)$")
        if not arg[1] or arg[1] == class then
            for _, persona in ipairs(data.leveling_availability_rules.races) do
                for _, allowed in ipairs(persona.classes) do
                    if allowed == class then
                        audit(class, spec, persona, "LEVELING")
                        audit(class, spec, persona, "PR")
                    end
                end
            end
        end
    end
end
assert(contexts > 0 and checks > 0, "No packed Guide contexts or routes checked")
print(string.format('{"items":%d,"ammunition":%d,"contexts":%d,"target_checks":%d,"activity_checks":%d}',
    #items, ammunition, contexts, checks, activities))
