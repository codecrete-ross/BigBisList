local addon = BigBiSList
local rating = {}
addon.ForeverGearRating = rating

local VERSION = "forever-stat-ranks-1"
local SLOT_BY_LOCATION = {
    INVTYPE_HEAD = "Head", INVTYPE_NECK = "Neck", INVTYPE_SHOULDER = "Shoulder", INVTYPE_CLOAK = "Back",
    INVTYPE_CHEST = "Chest", INVTYPE_ROBE = "Chest", INVTYPE_WRIST = "Wrist", INVTYPE_HAND = "Hands",
    INVTYPE_WAIST = "Waist", INVTYPE_LEGS = "Legs", INVTYPE_FEET = "Feet", INVTYPE_FINGER = "Ring",
    INVTYPE_TRINKET = "Trinket", INVTYPE_WEAPON = "One Hand", INVTYPE_WEAPONMAINHAND = "Main Hand",
    INVTYPE_WEAPONOFFHAND = "Off Hand", INVTYPE_SHIELD = "Off Hand", INVTYPE_HOLDABLE = "Off Hand",
    INVTYPE_2HWEAPON = "Two Hand", INVTYPE_RANGED = "Ranged", INVTYPE_RANGEDRIGHT = "Ranged", INVTYPE_THROWN = "Ranged",
    INVTYPE_RELIC = "Relic",
}
local ARMOR_TYPES = { [1] = "Cloth", [2] = "Leather", [3] = "Mail", [4] = "Plate", [6] = "Shield" }
local WEAPON_TYPES = {
    [0] = "Axe", [1] = "Axe", [2] = "Bow", [3] = "Gun", [4] = "Mace", [5] = "Mace", [6] = "Polearm",
    [7] = "Sword", [8] = "Sword", [10] = "Staff", [13] = "Fist Weapon", [15] = "Dagger", [16] = "Thrown",
    [18] = "Crossbow", [19] = "Wand",
}
local RELIC_TYPES = { [7] = "Libram", [8] = "Idol", [9] = "Totem" }
local RELIC_SLOTS = { Libram = true, Idol = true, Totem = true, Relic = true }
local SHIELD_CLASSES = { Paladin = true, Shaman = true, Warrior = true }
local RANGED_WEAPONS = { Bow = true, Crossbow = true, Gun = true, Thrown = true }
local STATS = {
    ITEM_MOD_STRENGTH_SHORT = "strength", ITEM_MOD_AGILITY_SHORT = "agility", ITEM_MOD_STAMINA_SHORT = "stamina",
    ITEM_MOD_INTELLECT_SHORT = "intellect", ITEM_MOD_SPIRIT_SHORT = "spirit", ITEM_MOD_ATTACK_POWER_SHORT = "attack_power",
    ITEM_MOD_RANGED_ATTACK_POWER_SHORT = "ranged_attack_power", ITEM_MOD_SPELL_POWER_SHORT = "spell_power",
    ITEM_MOD_SPELL_DAMAGE_DONE_SHORT = "spell_damage", ITEM_MOD_SPELL_HEALING_DONE_SHORT = "healing_power",
    ITEM_MOD_MANA_REGENERATION_SHORT = "mp5", ITEM_MOD_POWER_REGEN0_SHORT = "mp5", ITEM_MOD_HEALTH_REGEN_SHORT = "hp5",
    ITEM_MOD_ARMOR_SHORT = "armor", RESISTANCE0_NAME = "armor", ITEM_MOD_BLOCK_VALUE_SHORT = "block_value",
    ITEM_MOD_DEFENSE_SKILL_RATING_SHORT = "defense", ITEM_MOD_DAMAGE_PER_SECOND_SHORT = "dps",
    ITEM_MOD_ARCANE_DAMAGE_DONE_SHORT = "arcane_damage", ITEM_MOD_FIRE_DAMAGE_DONE_SHORT = "fire_damage",
    ITEM_MOD_FROST_DAMAGE_DONE_SHORT = "frost_damage", ITEM_MOD_HOLY_DAMAGE_DONE_SHORT = "holy_damage",
    ITEM_MOD_NATURE_DAMAGE_DONE_SHORT = "nature_damage", ITEM_MOD_SHADOW_DAMAGE_DONE_SHORT = "shadow_damage",
    RESISTANCE2_NAME = "fire_resistance", RESISTANCE3_NAME = "nature_resistance", RESISTANCE4_NAME = "frost_resistance",
    RESISTANCE5_NAME = "shadow_resistance", RESISTANCE6_NAME = "arcane_resistance",
}
local STATUS_LABELS = {
    loading = "Waiting for item stats", unavailable = "Stats unavailable", utility = "Utility", effect = "Effect only",
    incompatible = "No rank for this spec", blocked = "No legal swap",
}
local OWNED_ORDER = { equipped = 3, bag = 2, bank = 1 }
local DEFENSIVE_STATS = {
    stamina = true, armor = true, defense = true, block_value = true, block_percent = true,
    dodge = true, dodge_percent = true, parry = true, parry_percent = true, hp5 = true,
    arcane_resistance = true, fire_resistance = true, frost_resistance = true,
    nature_resistance = true, shadow_resistance = true,
}
local RANK_TIERS = {
    { minimum = 97, quality = 5, label = "Top tier" },
    { minimum = 85, quality = 4, label = "Near best" },
    { minimum = 70, quality = 3, label = "Strong" },
    { minimum = 50, quality = 2, label = "Solid" },
    { minimum = 25, quality = 1, label = "Modest" },
    { minimum = -math.huge, quality = 0, label = "Low" },
}

local function readable(value)
    return not addon.IsReadableValue or addon.IsReadableValue(value)
end

local function finite(value)
    return readable(value) and type(value) == "number" and value == value and math.abs(value) < math.huge
end

local function checked(ok, ...)
    if ok then return ... end
end

local function call(api, ...)
    if type(api) == "function" then return checked(pcall(api, ...)) end
end

local function contains(values, wanted)
    for _, value in ipairs(values or {}) do
        if value == wanted then return true end
    end
    return false
end

local function permitted(values, wanted)
    return not values or #values == 0 or contains(values, wanted)
end

local function copy(values)
    local result = {}
    for key, value in pairs(values or {}) do result[key] = value end
    return result
end

local function sameValues(left, right)
    for key, value in pairs(left or {}) do if not right or right[key] ~= value then return false end end
    for key in pairs(right or {}) do if not left or left[key] == nil then return false end end
    return true
end

local function model()
    local data = BigBiSListData and BigBiSListData.stat_rank
    return data and data.version == VERSION and data or nil
end

-- The client still receives the variant's full payload. Only the enchant and
-- socket fields are zeroed for base gear comparisons.
function rating:NormalizeLink(id, link)
    if not readable(link) or type(link) ~= "string" then return nil end
    local first, last, payload = link:find("item:([%d:%-]+)")
    if not payload then return nil end
    local fields = {}
    for value in (payload .. ":"):gmatch("([^:]*):") do fields[#fields + 1] = value end
    if tonumber(fields[1]) ~= id then return nil end
    local modFields = { fields[1], fields[2], fields[3], fields[4], fields[5], fields[6] }
    for index = 2, math.min(6, #fields) do fields[index] = "0" end
    local suffix = tonumber(fields[7]) or 0
    local suffixParameter = suffix < 0 and (tonumber(fields[8]) or 0) or 0
    local bonusCount = tonumber(fields[13]) or 0
    if bonusCount < 0 or (bonusCount > 0 and #fields < 13 + bonusCount) then return nil end
    for index = 14, 13 + bonusCount do
        if (tonumber(fields[index]) or 0) <= 0 then return nil end
    end
    local extended = {}
    for index = 11, #fields do extended[#extended + 1] = tostring(tonumber(fields[index]) or 0) end
    while extended[#extended] == "0" do table.remove(extended) end
    local key = tostring(id)
    if suffix ~= 0 then key = key .. ":" .. suffix end
    if #extended > 0 or suffixParameter ~= 0 then
        key = key .. ":" .. suffixParameter .. ":" .. table.concat(extended, ":")
    end
    -- Drop provenance only for a published suffix. Extra bonuses, upgrades and
    -- unknown modifiers retain their full identity.
    if suffix == 0 and bonusCount == 1 and (tonumber(fields[11]) or 0) == 0 then
        local modifiers = tonumber(fields[15]) or 0
        if modifiers == 0 or (modifiers == 1 and tonumber(fields[16]) == 28) then
            local lastField = modifiers == 0 and 15 or 17
            local plain = true
            for index = lastField + 1, #fields do
                if (tonumber(fields[index]) or 0) ~= 0 then plain = false; break end
            end
            local simple = tostring(id) .. ":0:0:0:1:" .. fields[14]
            local published = plain and simple ~= key and self:GetPublishedFacts(simple)
            if published and published.stats and not published.stats_unavailable then key = simple end
        end
    end
    return key, link:sub(1, first - 1) .. "item:" .. table.concat(fields, ":") .. link:sub(last + 1), modFields,
        suffix ~= 0 or bonusCount > 0
end

local function exactLinkKey(self, id, link)
    local variant, _, fields = self:NormalizeLink(id, link)
    if not variant then return nil end
    local parts = {}
    for value in (variant .. ":"):gmatch("([^:]*):") do parts[#parts + 1] = tonumber(value) or 0 end
    for index = 2, 6 do parts[#parts + 1] = tonumber(fields[index]) or 0 end
    return table.concat(parts, ":")
end

function rating:SameExactItemLink(id, first, second)
    if not (id and readable(first) and type(first) == "string" and readable(second) and type(second) == "string") then
        return false
    end
    if first == second then return true end
    local key = exactLinkKey(self, id, first)
    return key ~= nil and key == exactLinkKey(self, id, second)
end

function rating:IsPotentialGear(id, link)
    local data = model()
    if data and data.items[tostring(id)] then return true end
    local instant = C_Item and C_Item.GetItemInfoInstant or GetItemInfoInstant
    local _, _, _, location = call(instant, link or id)
    return not readable(location) or type(location) ~= "string" or SLOT_BY_LOCATION[location] ~= nil
end

function rating:GetGearSnapshotKey(owned)
    if owned.gearSnapshotKey then return owned.gearSnapshotKey end
    local checkpoint = self:GetWorkCheckpoint()
    local equipment = {}
    local function fingerprint(entry, location)
        local id, link = entry.item_id, entry.item_link
        return table.concat({ location or "", id, exactLinkKey(self, id, link) or link or "", entry.guid or "" }, "\031")
    end
    for slot, entry in pairs(owned.equippedSlots or {}) do equipment[#equipment + 1] = fingerprint(entry, slot) end
    for slot in pairs(owned.unreadableEquipmentSlots or {}) do equipment[#equipment + 1] = slot .. "\031?" end
    table.sort(equipment)
    local parts = { tostring(owned.equippedTwoHand), tostring(owned.bagsIncomplete), table.concat(equipment, "\030") }
    for _, entry in ipairs(owned.gearCopies or {}) do
        if checkpoint then checkpoint() end
        if not entry.item_link or self:IsPotentialGear(entry.item_id, entry.item_link) then
            parts[#parts + 1] = fingerprint(entry, entry.state .. ":" .. (entry.sourceId or ""))
        end
    end
    owned.gearSnapshotKey = table.concat(parts, "\030")
    return owned.gearSnapshotKey
end

function rating:GetWorkCheckpoint()
    if self.work and coroutine.running() == self.work.thread then return self.work.checkpoint end
    if self.guideWorker and coroutine.running() == self.guideWorker then return self.guideCheckpoint end
    if self.opportunityWorker and coroutine.running() == self.opportunityWorker then return self.opportunityCheckpoint end
    return addon.AcquisitionHighlights and addon.AcquisitionHighlights:GetCheckpoint()
end

local function runWorkSlice(self, job, start)
    job.started, job.steps = start, 0
    self.work = job
    local ok, result = coroutine.resume(job.thread, job.checkpoint)
    self.work = nil
    if not ok then
        job.cancelled = true
        if geterrorhandler then geterrorhandler()(result) else error(result) end
    elseif coroutine.status(job.thread) == "dead" then
        if job.onReady then job.onReady(result) end
    elseif job.isCurrent() then
        return true
    else job.cancelled = true end
end

function rating:QueueWork(priority, build, isCurrent, onReady, firstSlice)
    local job = { priority = priority, thread = coroutine.create(build), isCurrent = isCurrent, onReady = onReady }
    job.checkpoint = function()
        job.steps = job.steps + 1
        if job.steps >= (job.started and 4096 or 128)
            or (job.started and debugprofilestop() >= job.started + 1) then coroutine.yield() end
    end
    self.workQueue = self.workQueue or {}
    local queue = self.workQueue
    if firstSlice and not self.work then
        local start = debugprofilestop and debugprofilestop()
        if not runWorkSlice(self, job, start) then return job end
    end
    queue[#queue + 1] = job
    if self.workScheduled then return job end
    local function run()
        self.workScheduled = nil
        local start = debugprofilestop and debugprofilestop()
        for index = #queue, 1, -1 do
            if not queue[index].isCurrent() then table.remove(queue, index).cancelled = true end
        end
        local first
        for index, nextJob in ipairs(queue) do
            if not first or nextJob.priority < queue[first].priority then first = index end
        end
        local stats = addon.UI and addon.UI.performanceStats
        local frame = GetTime and GetTime()
        local busy = start and stats and stats.timingFrame == frame and stats.frameTime >= 2
            and self.deferredWorkFrame ~= frame
        if busy then self.deferredWorkFrame = frame end
        local current = not busy and first and table.remove(queue, first)
        if current then
            if runWorkSlice(self, current, start) then queue[#queue + 1] = current end
        end
        if start and addon.UI and addon.UI.RecordAddonTime then addon.UI:RecordAddonTime("background", debugprofilestop() - start) end
        if #queue > 0 and not self.workScheduled then
            self.workScheduled = true
            C_Timer.After(0, run)
        end
    end
    self.workScheduled = true
    C_Timer.After(0, run)
    return job
end

function rating:SortInWork(values, less, checkpoint)
    if #values <= 48 or not checkpoint then table.sort(values, less); return values end
    local ordered, width = {}, 48
    for first = 1, #values, width do
        local run = {}
        local last = math.min(first + width - 1, #values)
        for index = first, last do run[#run + 1] = values[index] end
        table.sort(run, less)
        for index, value in ipairs(run) do ordered[first + index - 1] = value end
        checkpoint()
    end
    local destination = values
    while width < #ordered do
        for start = 1, #ordered, width * 2 do
            local middle, finish = math.min(start + width, #ordered + 1), math.min(start + width * 2, #ordered + 1)
            local left, right = start, middle
            for index = start, finish - 1 do
                if left < middle and (right == finish or not less(ordered[right], ordered[left])) then
                    destination[index], left = ordered[left], left + 1
                else
                    destination[index], right = ordered[right], right + 1
                end
                checkpoint()
            end
        end
        ordered, destination, width = destination, ordered, width * 2
    end
    return ordered
end

function rating:GetCatalog(data)
    if self.catalog and self.catalog.data == data then return self.catalog end
    local checkpoint = rating:GetWorkCheckpoint()
    local _, build = call(GetBuildInfo)
    local slotKeys = data.slot_key_items == data.items and data.slot_keys
    local catalog = { data = data, slots = slotKeys or {}, families = {}, observed = {},
        rollBuildMatches = not data.roll_build or not tonumber(build) or tonumber(build) == data.roll_build }
    if not slotKeys then
        for key, row in pairs(data.items) do
            if checkpoint then checkpoint() end
            local slot = row[3]
            catalog.slots[slot] = catalog.slots[slot] or {}
            table.insert(catalog.slots[slot], key)
        end
    end
    catalog.items = setmetatable({}, { __index = function(items, key)
        local row = data.items[key]
        local item = { key = key }
        if row then
            for index, field in ipairs(data.item_fields) do item[field] = row[index] end
            item.variant_link = data.variant_links and data.variant_links[key]
        else
            local id, suffix = key:match("^(%d+):0:0:0:1:(%d+)$")
            local base = id and items[id]
            local group = base and base.roll_group and data.roll_groups[base.roll_group]
            if not group or not contains(group, tonumber(suffix)) then return end
            local template = data.roll_templates[suffix]
            local physical = base.stats and (base.stats.dps or base.stats.ranged_dps or base.stats.wand_dps
                or (base.armor_type == "Shield" and base.stats.block_value))
            local stats = catalog.rollBuildMatches and base.roll_budget and template[2] and (base.roll_complete or physical) and copy(base.stats)
            if stats then
                stats.armor = stats.armor or base.roll_armor
                for stat, basis in pairs(template[2]) do
                    stats[stat] = (stats[stat] or 0) + math.floor(base.roll_budget * basis / 10000 + 0.5)
                end
            end
            item = copy(base)
            item.key, item.variant_id, item.has_random_stats = key, key, nil
            item.stats, item.stats_unavailable = stats, not stats or nil
            item.name = base.name .. " " .. template[1]
            item.variant_link = "item:" .. id .. "::::::::::::1:" .. suffix
        end
        rawset(items, key, item)
        return item
    end })
    if checkpoint then checkpoint() end
    if self.catalog and self.catalog.data == data then return self.catalog end
    self.catalog = catalog
    self.native = {}
    self.tooltipItem = nil
    return catalog
end

local function visitSlot(catalog, slot, eligibleFamily, visit, checkpoint)
    for _, key in ipairs(catalog.slots[slot] or {}) do
        if checkpoint then checkpoint() end
        local base = catalog.items[key]
        if not base.roll_group then
            visit(base)
        elseif eligibleFamily(base) then
            local family = catalog.families[key]
            if not family then
                family = {}
                for _, suffix in ipairs(catalog.data.roll_groups[base.roll_group]) do
                    local exact = key .. ":0:0:0:1:" .. suffix
                    -- Explicitly reviewed rolls also have their own inventory row.
                    if not catalog.data.items[exact] then family[#family + 1] = catalog.items[exact] end
                end
                catalog.families[key] = family
            end
            for _, variant in ipairs(family) do visit(variant) end
        end
    end
end

function rating:GetPublishedFacts(key)
    local data = model()
    local catalog = data and self:GetCatalog(data)
    return catalog and (catalog.observed[key] or catalog.items[key])
end

local function addEffect(effects, line)
    if not contains(effects, line) then effects[#effects + 1] = line end
end

local function restrictionNames(text)
    local names = {}
    for name in text:gmatch("[^,]+") do names[#names + 1] = name:match("^%s*(.-)%s*$") end
    return names
end

local TOOLTIP_CHANCES = { hit = "hit_percent", dodge = "dodge_percent", parry = "parry_percent",
    block = "block_percent", ["get a critical strike"] = "crit_percent", ["dodge an attack"] = "dodge_percent",
    ["parry an attack"] = "parry_percent", ["block an attack"] = "block_percent",
    ["get a critical strike with spells"] = "spell_crit_percent",
    ["get a critical strike with melee and ranged attacks"] = "physical_crit_percent" }
local TOOLTIP_SCHOOLS = { Arcane = "arcane_damage", Fire = "fire_damage", Frost = "frost_damage",
    Holy = "holy_damage", Nature = "nature_damage", Shadow = "shadow_damage" }
local TOOLTIP_REGENERATION = { mana = "mp5", health = "hp5" }

local function readFlatPassiveStat(text, rules)
    text = text:lower():match("^%s*(.-)%s*$"):gsub("%.$", "")
    for _, rule in ipairs(rules or {}) do
        local prefix, suffix, stat = unpack(rule)
        local last = #text - #suffix
        if text:sub(1, #prefix) == prefix and text:sub(last + 1) == suffix then
            local amount = text:sub(#prefix + 1, last):match("^%s*(%d+)%s*$")
            if amount then return stat, tonumber(amount) end
        end
    end
end

local function readPassiveStats(text, stats, flatRules)
    local flat, value = readFlatPassiveStat(text, flatRules)
    if flat then
        stats[flat] = (stats[flat] or 0) + value
        return true
    end
    local healing, damage = text:match("^Equip: Increases healing done by up to (%d+) and damage done by up to (%d+) for all magical spells and effects%.?$")
    if healing then
        stats.healing_power = (stats.healing_power or 0) + tonumber(healing)
        stats.spell_damage = (stats.spell_damage or 0) + tonumber(damage)
        return true
    end
    local chance, amount = text:match("^Equip: Improves your chance to (.+) by ([%d.]+)%%%.?$")
    if not chance then chance, amount = text:match("^Equip: Increases your chance to (.+) by ([%d.]+)%%%.?$") end
    local stat = chance and TOOLTIP_CHANCES[chance:lower()]
    if not stat then
        amount = text:match("^Equip: Increases damage and healing done by magical spells and effects by up to (%d+)%s*%.?$")
            or text:match("^Equip: Increases spell power by (%d+)%s*%.?$")
        stat = "spell_power"
    end
    if not amount then
        amount = text:match("^Equip: Increases healing done by magical spells and effects by up to (%d+)%s*%.?$")
        stat = "healing_power"
    end
    if not amount then
        local school, value = text:match("^Equip: Increases damage done by (%a+) spells and effects by up to (%d+)%s*%.?$")
        stat = TOOLTIP_SCHOOLS[school]
        amount = stat and value
    end
    if not amount then
        local value, resource = text:match("^Equip: Restores %+?(%d+) (%a+) per 5 sec%.?$")
        stat = TOOLTIP_REGENERATION[resource]
        amount = stat and value
    end
    amount = tonumber(amount)
    if not amount then return false end
    stats[stat] = (stats[stat] or 0) + amount
    return true
end

local function readTooltip(link, stats, facts)
    local tooltip = call(C_TooltipInfo and C_TooltipInfo.GetHyperlink, link)
    if not readable(tooltip) or type(tooltip) ~= "table" or not readable(tooltip.lines) or type(tooltip.lines) ~= "table" then return end
    local locale = GetLocale and GetLocale()
    local english = locale == nil or locale == "enUS" or locale == "enGB"
    local data = model()
    local flatRules = data and data.flat_passive_stats
    local passive, seenEffects = {}, {}
    for _, line in ipairs(tooltip.lines or {}) do
        if readable(line) and type(line) == "table" then
            for _, field in ipairs({ "leftText", "rightText" }) do
                local text = line[field]
                if readable(text) and type(text) == "string" and english then
                    text = text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
                    local label = text:lower()
                    if label == "random enchantment" or label == "<random enchantment>" then facts.has_random_stats = true end
                    local dps = tonumber(text:match("^%(([%d.]+) damage per second%)$"))
                    local speed = tonumber(text:match("^Speed%s+([%d.]+)$"))
                    local armor = tonumber(text:match("^(%d+) Armor$"))
                    local block = tonumber(text:match("^(%d+) Block$") or text:match("^(%d+) Block Value$"))
                    local weaponLow, weaponHigh = text:match("^(%d+)%s*%-%s*(%d+) Damage$")
                    local weaponFlat = tonumber(text:match("^(%d+) Damage$"))
                    if weaponLow or weaponFlat then
                        stats.weapon_min_damage = tonumber(weaponLow) or weaponFlat
                        stats.weapon_max_damage = tonumber(weaponHigh) or weaponFlat
                    end
                    if dps and stats.dps == nil then stats.dps = dps end
                    if speed then stats.weapon_speed = speed end
                    if armor and stats.armor == nil then stats.armor = armor end
                    if block and facts.armor_type == "Shield" and stats.block_value == nil then stats.block_value = block end
                    local classes, races = text:match("^Classes:%s*(.+)$"), text:match("^Races:%s*(.+)$")
                    if classes then facts.classes = restrictionNames(classes) end
                    if races then facts.races = restrictionNames(races) end
                    if not seenEffects[text] and (text:match("^Use:") or text:match("^Chance on hit:") or text:match("^Equip:")) then
                        seenEffects[text] = true
                        if not readPassiveStats(text, passive, flatRules) then addEffect(facts.effects, text) end
                    end
                end
            end
        end
    end
    if passive.spell_damage and stats.spell_power == passive.spell_damage and not passive.spell_power then
        stats.spell_power = nil
    elseif stats.spell_damage ~= nil and stats.spell_power == nil and passive.spell_damage == nil then
        passive.spell_power = nil
    end
    for stat, value in pairs(passive) do
        if stats[stat] == nil then stats[stat] = value end
    end
    return true
end

function rating:ReadNative(id, key, link, base)
    local cache = self.native[id]
    if cache and cache[key] and cache[key].statLink == link then return cache[key] end
    local api = C_Item or {}
    local name, _, _, _, level = call(api.GetItemInfo or GetItemInfo, link)
    local _, _, _, location, _, class, subclass = call(api.GetItemInfoInstant or GetItemInfoInstant, link)
    local slot = readable(location) and SLOT_BY_LOCATION[location]
    local cached = call(api.IsItemDataCachedByID, id)
    local pending = not (self.loadedItems and self.loadedItems[id]) and Item and Item.CreateFromItemID
        and readable(cached) and (cached == false or (cached == nil and readable(name) and name == nil))
    if slot == "Relic" and finite(subclass) then slot = RELIC_TYPES[subclass] or slot end
    if not slot or not readable(name) or type(name) ~= "string" or not finite(level) then
        return nil, pending and "loading" or "unavailable"
    end
    if not finite(class) or not finite(subclass) then return nil, "unavailable" end

    local stats = {}
    local native = call(api.GetItemStats or GetItemStats, link)
    if pending and (not readable(native) or type(native) ~= "table" or next(native) == nil) then
        return nil, "loading"
    end
    if readable(native) and type(native) == "table" then
        for stat, value in pairs(native) do
            local normalized = readable(stat) and STATS[stat]
            if normalized and finite(value) then stats[normalized] = math.max(stats[normalized] or value, value) end
        end
    end
    local facts = {
        id = id, key = key, name = name, slot = slot, level = level, stats = stats, effects = {},
        armor_type = class == 4 and ARMOR_TYPES[subclass] or nil,
        weapon_subtype = class == 2 and WEAPON_TYPES[subclass] or nil,
        native = true, statLink = link,
    }
    if not readTooltip(link, stats, facts) and C_TooltipInfo and C_TooltipInfo.GetHyperlink then
        if pending then return nil, "loading" end
        facts.unreadable_effects = true
    end
    if facts.has_random_stats then return nil, "unavailable" end
    local weapon = facts.weapon_subtype
    if stats.dps and slot == "Ranged" then
        if weapon == "Wand" then stats.wand_dps, stats.dps = stats.dps, nil
        elseif RANGED_WEAPONS[weapon] then stats.ranged_dps, stats.dps = stats.dps, nil end
    end
    if base then
        facts.classes, facts.races = base.classes or facts.classes, base.races or facts.races
        facts.max_equipped, facts.unique_group = base.max_equipped, base.unique_group
        facts.requires_dual_wield, facts.excluded = base.requires_dual_wield, base.excluded
        facts.utility = base.utility
        if key == base.key then facts.effect_rules = base.effect_rules end
        for _, effect in ipairs(base.effects or {}) do addEffect(facts.effects, effect) end
    elseif #facts.effects == 0 then
        local spell = call(api.GetItemSpell or GetItemSpell, link)
        if readable(spell) and spell then addEffect(facts.effects, "Item spell") end
    end
    local unique, group, _, limit = call(api.GetItemUniquenessByID, id)
    if readable(unique) and unique == true then facts.max_equipped = facts.max_equipped or 1 end
    if readable(group) and type(group) == "string" and group ~= "" and finite(limit) and limit > 0 then
        facts.unique_group, facts.max_equipped = group, limit
    end
    if not facts.unreadable_effects and (next(stats) or #facts.effects > 0) then
        self.native[id] = cache or {}
        self.native[id][key] = facts
    end
    return facts
end

function rating:InvalidateItem(id)
    self.loadedItems = self.loadedItems or {}
    self.loadedItems[id] = true
    if self.native then self.native[id] = nil end
    if self.catalog and not BigBiSListData.guide_index then
        for key, facts in pairs(self.catalog.observed) do
            if facts.id == id then
                self.catalog.observed[key] = nil
                self.guideData, self.levelingSummaryData = nil, nil
            end
        end
    end
    self.contexts, self.inventory = nil, nil
    if self.tooltipItem and self.tooltipItem.entry.item_id == id then self.tooltipItem = nil end
    if addon.ForeverScoring then addon.ForeverScoring:Invalidate() end
end

local function resolveLink(self, context, entry)
    if not entry or not entry.item_id then return nil end
    local id, link = entry.item_id, entry.item_link
    local key, statLink, _, exactRoll = self:NormalizeLink(id, link)
    local base = context.catalog.items[tostring(id)]
    if base and base.has_random_stats and not exactRoll then return nil, "unavailable" end
    local facts = key and context.catalog.items[key] or (not link and base)
    if facts and facts.has_random_stats then facts = nil end
    local unavailable
    local checkRoll = facts and facts.roll_group and facts.variant_id
    if statLink and (checkRoll or not facts or facts.stats_unavailable or not facts.level) then
        local native
        native, unavailable = self:ReadNative(id, key, statLink, base)
        if native and (checkRoll or not facts or facts.stats_unavailable) and next(native.stats or {}) then
            -- Keep the readable exact item in the same slot pool on the next
            -- refresh. A later unreadable link never erases observed facts.
            local seen = context.catalog.observed[key]
            local old = seen and seen.nativeFacts
            if not old or (old ~= native and (old.level ~= native.level or old.name ~= native.name
                or old.unreadable_effects ~= native.unreadable_effects or old.max_equipped ~= native.max_equipped
                or old.unique_group ~= native.unique_group or not sameValues(old.stats, native.stats)
                or not sameValues(old.effects, native.effects) or not sameValues(old.classes, native.classes)
                or not sameValues(old.races, native.races))) then
                local observed = copy(facts)
                for field, value in pairs(native) do observed[field] = value end
                observed.stats = copy(facts and facts.stats)
                for stat, value in pairs(native.stats) do observed.stats[stat] = value end
                observed.nativeFacts, observed.stats_unavailable = native, nil
                observed.variant_id = (facts and facts.variant_id) or (key ~= tostring(id) and key or nil)
                observed.variant_link = (facts and facts.variant_link) or link
                if BigBiSListData.guide_index and facts and not facts.stats_unavailable and
                    observed.level == facts.level and observed.slot == facts.slot and observed.name == facts.name
                    and observed.unreadable_effects == facts.unreadable_effects
                    and observed.max_equipped == facts.max_equipped and observed.unique_group == facts.unique_group
                    and sameValues(facts.stats, observed.stats) and sameValues(facts.effects, observed.effects)
                    and sameValues(facts.classes, observed.classes) and sameValues(facts.races, observed.races) then
                    return facts
                end
                context.catalog.observed[key] = observed
                if BigBiSListData.guide_index then
                    context.catalog.observedVersion = (context.catalog.observedVersion or 0) + 1
                    context.catalog.changedSlots = context.catalog.changedSlots or {}
                    context.catalog.changedSlots[observed.slot] = true
                    if observed.slot == "One Hand" then
                        context.catalog.changedSlots["Main Hand"], context.catalog.changedSlots["Off Hand"] = true, true
                    end
                else
                    self.guideData, self.levelingSummaryData = nil, nil
                end
                self.contexts, self.inventory = nil, nil
                if not self.observedRefresh and addon.UI and addon.UI.frame and addon.UI.frame:IsShown()
                    and C_Timer and C_Timer.After then
                    self.observedRefresh = true
                    C_Timer.After(0, function()
                        self.observedRefresh = nil
                        addon:RefreshUI("query", "item stats available")
                        if addon.ScheduleItemTooltipRefresh then addon:ScheduleItemTooltipRefresh() end
                    end)
                end
            end
            facts = context.catalog.observed[key]
        elseif facts and facts.stats_unavailable then
            facts = nil
        elseif facts and native then
            facts = copy(facts)
            facts.level = native.level
        elseif not facts then
            facts = native
        end
    end
    if unavailable == "loading" then context.pending[id] = true end
    return facts or (key and context.catalog.observed[key]), unavailable
end

function rating:GetExactBaseFacts(id, link)
    local data = model()
    if data then return resolveLink(self, { catalog = self:GetCatalog(data), pending = {} }, { item_id = id, item_link = link }) end
end

local function unresolvedCopy(catalog, entry, status)
    local base = catalog.items[tostring(entry.item_id)]
    if base then return { item = base, status = status or "unavailable" } end
    local instant = C_Item and C_Item.GetItemInfoInstant or GetItemInfoInstant
    local _, _, _, location, _, _, subclass = call(instant, entry.item_link or entry.item_id)
    if readable(location) and type(location) == "string" then
        local slot = SLOT_BY_LOCATION[location]
        if not slot then return nil end
        if slot == "Relic" and finite(subclass) then slot = RELIC_TYPES[subclass] or slot end
        return { item = { slot = slot }, status = status or "unavailable" }
    end
    return { status = status or "unavailable" }
end

local function resolveInventory(self, catalog, owned)
    local checkpoint = rating:GetWorkCheckpoint()
    local inventory = { catalog = catalog, pending = {}, equipment = {}, byVariant = {}, bySource = {}, copies = {}, unresolvedCopies = {} }
    local function read(entry, state)
        if checkpoint then checkpoint() end
        local facts, status = resolveLink(self, inventory, entry)
        local instance = { facts = facts, key = facts and facts.key, status = status,
            entry = entry, item_link = entry.item_link, state = state }
        if facts and instance.item_link then
            local other = inventory.byVariant[facts.key]
            if not other or (OWNED_ORDER[state] or 0) > (OWNED_ORDER[other.state] or 0) then
                inventory.byVariant[facts.key] = instance
            end
            inventory.copies[#inventory.copies + 1] = instance
            if entry.sourceId then inventory.bySource[entry.sourceId] = instance end
        end
        if state ~= "equipped" and (not facts or not instance.item_link or not facts.level) then
            local unresolved = facts and { item = facts, status = status } or unresolvedCopy(catalog, entry, status)
            if unresolved then
                unresolved.state = state
                inventory.unresolvedCopies[#inventory.unresolvedCopies + 1] = unresolved
            end
        end
        return instance
    end
    for _, definition in ipairs(addon.GetEquipmentSlotDefinitions and addon:GetEquipmentSlotDefinitions() or {}) do
        local entry = owned.equippedSlots and owned.equippedSlots[definition.key]
        if entry then inventory.equipment[definition.key] = read(entry, "equipped") end
    end
    for key, entry in pairs(owned.equippedSlots or {}) do
        if not inventory.equipment[key] then inventory.equipment[key] = read(entry, "equipped") end
    end
    if owned.gearCopies then
        for _, entry in ipairs(owned.gearCopies) do
            if checkpoint then checkpoint() end
            if not entry.item_link or self:IsPotentialGear(entry.item_id, entry.item_link) then read(entry, entry.state) end
        end
    else
        for _, entry in pairs(owned.gearStatLinks or {}) do
            if entry.state ~= "equipped" then read(entry, entry.state) end
        end
    end
    return inventory
end

local function scoringContext(data, profile, className, spec, phase, level, phaseIndex, race, faction)
    local leveling = phase == "LEVELING"
    local policy = leveling and profile.leveling or profile.pre_raid
    local weights = policy.weights
    if leveling then
        for _, band in ipairs(policy.weights) do
            if level >= band[1] and level <= band[2] then weights = band[3]; break end
        end
    end
    local scorer = addon.ForeverScoring
    local scenario = scorer and scorer.GetPreset
        and scorer:GetPreset(className, spec, leveling and "leveling" or "pre_raid")
    scenario = copy(scenario)
    scenario.crit_domain = (profile.role == "caster" or profile.role == "healer") and "spell"
        or (profile.role == "ranged" or profile.role == "melee") and "physical"
    local raceId
    for identifier, actor in pairs(scenario.personas or {}) do
        if actor[1] == race and actor[2] == faction then raceId = tonumber(identifier); break end
    end
    return {
        class = className, spec = spec, phase = phase, level = level, race = race, faction = faction,
        leveling = leveling, policy = policy, weights = weights, equipment = data.equipment[className], role = profile.role,
        commonSlots = data.common_slots, feralPolicy = profile.leveling, feralDps = data.feral_uses_weapon_dps,
        phaseIndex = phaseIndex, inScope = {}, pools = {},
        referenceScenario = scenario, raceId = raceId,
    }
end

local function contextAtLevel(context, phase, level)
    local data = context.catalog.data
    local profile = data.profiles[context.class .. "/" .. context.spec]
    local samePhase = phase == context.phase
    local phaseIndex = samePhase and context.phaseIndex or addon:GetAvailabilityPhaseIndex(phase)
    local projected = scoringContext(data, profile, context.class, context.spec, phase, level, phaseIndex,
        context.race, context.faction)
    projected.catalog, projected.ownedFacts = context.catalog, context.ownedFacts
    projected.owned, projected.equipmentFacts, projected.guide = context.owned, context.equipmentFacts, context.guide
    projected.ownedCopies, projected.unresolvedCopies, projected.ownedLoadouts = context.ownedCopies, context.unresolvedCopies, {}
    -- Native source scope checks the content phase. Guide routes also depend on the level.
    if samePhase and not context.guide then projected.inScope = context.inScope end
    return projected
end

function rating:GetContext(className, spec, phase, level, owned)
    local data = model()
    if not data or not owned then return nil end
    local profile = data.profiles[className .. "/" .. spec]
    if not profile then return nil end
    level = phase == "LEVELING" and level or 60
    local livePhase = addon:GetAvailabilityPhaseIndex(phase)
    local race = addon:GetPlayerRaceName()
    local faction = addon.GetPlayerFactionName and addon:GetPlayerFactionName()
    local key = table.concat({className, spec, phase, level, livePhase, race or "", faction or ""}, "\031")
    local matches = self.snapshot == owned and self.contextData == data
    local cached = matches and self.contexts and self.contexts[key]
    if cached then return cached end
    local inventory = matches and self.inventory or resolveInventory(self, self:GetCatalog(data), owned)
    if self.snapshot ~= owned or self.contextData ~= data or not self.inventory then
        self.snapshot, self.contextData, self.inventory, self.contexts = owned, data, inventory, {}
    else
        inventory = self.inventory
        if self.contexts[key] then return self.contexts[key] end
    end
    local context = scoringContext(data, profile, className, spec, phase, level, livePhase, race, faction)
    context.owned, context.catalog, context.pending = owned, inventory.catalog, inventory.pending
    context.equipmentFacts, context.ownedFacts = inventory.equipment, inventory.byVariant
    context.storageCopies = inventory.bySource
    context.ownedCopies, context.unresolvedCopies, context.ownedLoadouts = inventory.copies, inventory.unresolvedCopies, {}
    self.contexts[key] = context
    return context
end

function rating:GetGuideContext(className, spec, phase, level, race, faction)
    local data = model()
    local profile = data and data.profiles[className .. "/" .. spec]
    if not profile then return nil end
    level = phase == "LEVELING" and level or 60
    local phaseIndex = addon:GetAvailabilityPhaseIndex(phase)
    local key = table.concat({className, spec, phase, level, phaseIndex, race or "", faction or ""}, "\031")
    if self.guideData == data then
        for _, context in ipairs(self.guideContexts) do
            if context.key == key then return context end
        end
    end
    local catalog = self:GetCatalog(data)
    if self.guideData ~= data then
        self.guideData, self.guideContexts = data, {}
    else
        for _, context in ipairs(self.guideContexts) do
            if context.key == key then return context end
        end
    end
    local context = scoringContext(data, profile, className, spec, phase, level, phaseIndex, race, faction)
    context.key, context.catalog, context.guide = key, catalog, true
    context.ownedFacts = {}
    self.guideContexts[#self.guideContexts + 1] = context
    if #self.guideContexts > 8 then table.remove(self.guideContexts, 1) end
    return context
end

local function fitsEquipment(context, item, slot, anyRace)
    if item.slot ~= slot and not (item.slot == "One Hand" and (slot == "Main Hand" or slot == "Off Hand")) then return false end
    if not permitted(item.classes, context.class) or (not anyRace and (not permitted(item.races, context.race)
        or not permitted(item.race_ids, context.raceId))) then return false end
    local policy, weapon, armor = context.policy, item.weapon_subtype, item.armor_type
    if not permitted(policy.slot_weapon_types and policy.slot_weapon_types[slot], weapon) and weapon then return false end
    if not context.leveling then
        return contains(policy.slots, slot)
            and (not armor or contains(policy.armor_types, armor)
                or (armor == "Shield" and SHIELD_CLASSES[context.class]))
            and (not weapon or contains(policy.weapon_types, weapon))
            and (slot ~= "Two Hand" or not weapon or contains(policy.two_hand_weapon_types, weapon))
            and (slot ~= "Off Hand" or (not policy.require_shield or armor == "Shield")
                and (not weapon or item.requires_dual_wield == false or policy.dual_wield))
    end
    if not (contains(context.commonSlots, slot) or contains(policy.slots, slot)) then return false end
    if context.level < ((policy.slot_min_levels or {})[slot] or 1)
        or context.level > ((policy.slot_max_levels or {})[slot] or 59) then return false end
    local equipment = context.equipment
    if armor then
        local allowed
        for _, tier in ipairs(equipment.armor_tiers or {}) do
            if context.level >= tier.level and contains(tier.types, armor) then allowed = true; break end
        end
        if not allowed then return false end
    end
    if weapon and not contains(equipment.weapon_types, weapon) then return false end
    if slot == "Two Hand" and weapon and not contains(equipment.two_hand_weapon_types, weapon) then return false end
    if RELIC_SLOTS[slot] then
        if not contains(equipment.special_slots, slot) then return false end
    end
    local locked = false
    for _, unlock in ipairs(equipment.weapon_unlocks or {}) do
        if unlock.weapon_subtype == weapon and contains(unlock.slots, item.slot) then
            locked = true
            if context.level >= unlock.min_level and permitted(unlock.specs, context.spec) then locked = false; break end
        end
    end
    if locked then return false end
    local style, dualLevel = policy.weapon_style, policy.dual_wield_level
    if slot == "Off Hand" and weapon and item.requires_dual_wield ~= false
        and (not dualLevel or context.level < dualLevel) then return false end
    if style == "shield" and (slot == "Two Hand" or (slot == "Off Hand" and armor ~= "Shield")) then return false end
    if style == "two_hand" and (slot == "Main Hand" or slot == "Off Hand") then return false end
    if style == "feral" and slot == "Off Hand" and weapon then return false end
    return not (style == "dual_wield" and slot == "Two Hand" and dualLevel and context.level >= dualLevel)
end

local function offHandType(item)
    return item.armor_type == "Shield" and "shield" or (item.weapon_subtype and "weapon" or "held")
end

local function sharesUniqueLimit(item, equipped)
    return item.id == equipped.id
        or (item.unique_group and equipped.unique_group and string.lower(item.unique_group) == string.lower(equipped.unique_group))
end

local function swapCapacity(item, physical, slot, gear)
    local count, limit = 0, item.max_equipped or (item.unique_group and 1)
    for key, other in pairs(gear) do
        if key ~= physical and not (slot == "Two Hand" and key == "OffHand") then
            local equipped = other.facts
            if item.id == other.entry.item_id or (equipped and sharesUniqueLimit(item, equipped)) then
                count = count + 1
                local otherLimit = equipped and equipped.max_equipped
                if otherLimit then limit = math.min(limit or otherLimit, otherLimit) end
            end
        end
    end
    limit = limit or (item.unique_group and 1)
    return limit and limit - count or math.huge
end

local function hasTwoHander(context, gear)
    local main = gear.MainHand
    return (main and main.facts and main.facts.slot == "Two Hand")
        or (gear == context.equipmentFacts and context.owned.equippedTwoHand)
end

local function legalSwap(context, item, physical, slot, gear)
    return (slot ~= "Off Hand" or not hasTwoHander(context, gear))
        and swapCapacity(item, physical, slot, gear) > 0
end

local function isTank(context)
    return context.role == "tank" or context.spec == "Protection" or context.spec == "Feral tank"
end

function rating:ReferenceWeights(context, roleOnly, guide)
    local weights, feral = context.weights, context.feralPolicy
    local ignoreDps = not context.feralDps and feral.weapon_style == "feral"
        and feral.form_level and context.level >= feral.form_level
    local ignoreDefense = roleOnly and not isTank(context)
    local ignoreRecovery = guide and context.role ~= "healer" and not isTank(context)
    if not (ignoreDps or ignoreDefense or ignoreRecovery) then return weights end
    local result = copy(weights)
    for stat in pairs(weights) do
        if (ignoreDps and stat == "dps") or (ignoreDefense and DEFENSIVE_STATS[stat])
            or (ignoreRecovery and (stat == "spirit" or stat == "mp5")) then result[stat] = nil end
    end
    return result
end

local function score(context, item, roleOnly, guide, stats, slot)
    stats = stats or (item and item.stats)
    if not stats or item.stats_unavailable then return nil end
    local weights = rating:ReferenceWeights(context, roleOnly, guide)
    local scorer = addon.ForeverScoring
    slot = slot or item.slot
    if scorer and scorer.ReferenceItem then
        local position = (slot == "Main Hand" or slot == "One Hand" or slot == "Two Hand") and 16
            or slot == "Off Hand" and 17 or slot == "Ranged" and 18 or 1
        local scoringItem = scorer:ReferenceItem(item, stats)
        local points, _, applied = scorer.ScoreLoadout({[position] = scoringItem}, weights, {}, {},
            context.referenceScenario, context.raceId, context.level)
        local known = applied and applied[position]
        if not next(stats) and not known then return nil end
        return math.floor(points * 10000 + 0.5) / 10000, scorer:HasUnresolvedEffects(scoringItem, known)
    end
    if not next(stats) then return nil end
    local total = 0
    for stat, value in pairs(stats) do
        if not (stat == "weapon_speed" and (slot == "Ranged" or slot == "Off Hand")) then
            total = total + value * (weights[stat] or 0)
        end
    end
    return math.floor(total * 10000 + 0.5) / 10000
end

local function swapStats(item, link)
    if not item then return nil end
    local scoring = addon.ForeverScoring
    if scoring and link then return scoring:GetExactStats(item.id, item.stats, link) end
    return item.stats
end

local function hasUnscoredEffect(item)
    return item and not item.utility and (item.unreadable_effects or next(item.effects or {}) ~= nil)
end

function rating:ReferenceLoadout(context, gear, roleOnly, includeBreakdown)
    local scorer = addon.ForeverScoring
    if not (scorer and scorer.ReferenceItem) then return nil end
    local loadout, uncertain = {}, {}
    for _, definition in ipairs(addon:GetEquipmentSlotDefinitions()) do
        local instance = gear[definition.key]
        if instance and instance.facts then
            local stats, unknown = swapStats(instance.facts, instance.item_link)
            if stats then
                local position = definition.inventorySlotId
                loadout[position] = scorer:ReferenceItem(instance.facts, stats)
                uncertain[position] = unknown
            end
        end
    end
    local active = context.activeBuild
    local operations = active and active.profile.operations or {}
    local ranks = active and active.ranks or {}
    local total, _, applied, _, breakdown = scorer.ScoreLoadout(loadout, self:ReferenceWeights(context, roleOnly), operations,
        ranks, context.referenceScenario, context.raceId, context.level, includeBreakdown)
    for position, item in pairs(loadout) do
        uncertain[position] = uncertain[position] or scorer:HasUnresolvedEffects(item, applied and applied[position])
    end
    return total, uncertain, loadout, breakdown
end

function rating:WithCharacterBuild(context, live)
    if context.activeBuild then return context end
    local scorer = addon.ForeverScoring
    if not (scorer and scorer.ReferenceItem and (context.leveling or context.phase == "PR")) then return context end
    local active, missing = scorer:GetContext(context.class, context.spec, context.leveling and "leveling" or "pre_raid",
        context.level, { live = live, race = context.race, faction = context.faction })
    if not active then return context, missing end
    local recorded = context.ownedBuild
    if recorded and recorded.activeBuild == active then return recorded end
    local derived = copy(context)
    derived.activeBuild, derived.weights = active, active.weights
    derived.referenceScenario, derived.raceId = active.scenario, active.race
    derived.ownedLoadouts, derived.lastTooltip, derived.ownedBuild = {}, nil, nil
    context.ownedBuild = derived
    return derived
end

function rating:HasGuideRoleStats(context, item, slot)
    return (score(context, item, true, true, nil, slot) or 0) > 0
end

function rating:GetReviewedGuideEffect(context, item)
    local data = model()
    local review = data and (data.guide_effects or {})[item.key]
    if review and (contains(review.roles, context.role) or contains(review.specs, context.class .. "/" .. context.spec)) then
        return review.note
    end
end

local function resultFor(context, item, status, slot)
    -- Reference loadouts have no talent ranks. Identical weight bands can
    -- share the item score; equip levels and routes still vary at each level.
    local cache = context.referenceScores
    if not cache and context.catalog then
        local catalog = context.catalog
        catalog.scoreBands = catalog.scoreBands or {}
        local key = table.concat({context.class, context.spec, context.phase, context.race or "", tostring(context.weights)}, "/")
        cache = catalog.scoreBands[key]
        if not cache then
            catalog.scoreBandOrder = catalog.scoreBandOrder or {}
            if #catalog.scoreBandOrder >= 12 then catalog.scoreBands[table.remove(catalog.scoreBandOrder, 1)] = nil end
            cache = {}
            catalog.scoreBands[key] = cache
            table.insert(catalog.scoreBandOrder, key)
        end
        context.referenceScores = cache
    end
    local points, conditional
    if item then
        local byItem = cache and cache[slot]
        if cache and not byItem then byItem = {}; cache[slot] = byItem end
        local known = byItem and byItem[item]
        if known then points, conditional = known[1], known[2]
        else
            points, conditional = score(context, item, nil, nil, nil, slot)
            if byItem then byItem[item] = { points, conditional } end
        end
    end
    if points == nil and not status then
        status = item and (item.utility and "utility" or (next(item.effects or {}) and "effect")) or "unavailable"
    end
    return { item = item, score = points, status = status, spec = context.spec, level = context.level, phase = context.phase,
        slot = slot, conditional = conditional or (points == nil and hasUnscoredEffect(item)) }
end

local function scorePercent(score, bestScore)
    -- Allow for floating-point noise at an exact whole-percent boundary.
    return math.floor(score * 100 / bestScore + 1e-9)
end

local function scoreGapTier(percent)
    for _, tier in ipairs(RANK_TIERS) do
        if percent >= tier.minimum then return tier end
    end
end

local function placementTiers(rows, count, bestScore)
    if count < 2 or count > 12 or bestScore <= 0 then return nil end
    local minimumGap = math.max(0.1, bestScore * 0.01)
    local bands, bandByScore = {}, {}
    for index = 1, count do
        local points = rows[index].score
        local leader = bands[#bands]
        if not leader or leader - points + 1e-9 >= minimumGap then
            bands[#bands + 1] = points
            if #bands > #RANK_TIERS then return nil end
        end
        bandByScore[points] = #bands
    end

    local top = RANK_TIERS[1].quality
    local bottom = math.min(scoreGapTier(scorePercent(bands[#bands], bestScore)).quality, #RANK_TIERS - #bands)
    local tiers = {}
    for points, band in pairs(bandByScore) do
        local quality = top
        if #bands > 1 then quality = math.floor(top - (top - bottom) * (band - 1) / (#bands - 1) + 0.5) end
        tiers[points] = RANK_TIERS[top + 1 - quality]
    end
    return tiers
end

local function setRankTier(entry, bestScore, tiers)
    entry.score_percent = scorePercent(entry.score, bestScore)
    entry.tier = tiers and tiers[entry.score] or scoreGapTier(entry.score_percent)
    entry.placement_color = tiers ~= nil or nil
end

rating.GetPackedRankTiers = function(_, ...) return placementTiers(...) end

function rating:ApplyPackedRankTier(entry, bestScore, tiers)
    if entry.total > 1 and bestScore > 0 then setRankTier(entry, bestScore, tiers or nil) end
end

local function currentComparisonSlot(context, physical, slots)
    local equipped = context.equipmentFacts[physical]
    local reference = equipped and equipped.facts
    local slot = slots[1]
    if physical == "MainHand" and (context.owned.equippedTwoHand or (reference and reference.slot == "Two Hand")) then
        slot = "Two Hand"
    elseif physical == "Ranged" and reference and contains(slots, reference.slot) then
        slot = reference.slot
    end
    local handType = slot == "Off Hand" and reference and offHandType(reference)
    return slot, handType
end

local function guideAccess(context, id)
    if not addon.IsStatRankGuideItemAvailable then return "unverified_route" end
    context.guideAccess = context.guideAccess or {}
    local access = context.guideAccess[id]
    if access == nil then
        local available, reason, phase = addon:IsStatRankGuideItemAvailable(id, context)
        access = available and "verified" or reason or "unverified_route"
        context.guideAccess[id] = access
        if phase then
            context.futurePhases = context.futurePhases or {}
            context.futurePhases[id] = phase
        end
    end
    return access
end

local function inScope(context, item)
    local scoped = context.inScope[item.id]
    if scoped == nil then
        if context.guide then
            local access = guideAccess(context, item.id)
            scoped = access == "verified" or access == "unverified_route" or access == "missing_item_record"
        else
            scoped = not addon.ComparisonItemInScope or addon:ComparisonItemInScope(item.id, context.phase, context.phaseIndex)
        end
        context.inScope[item.id] = scoped
    end
    return scoped
end

local function usable(context, item, slot)
    return not item.excluded and not item.has_random_stats and item.level and item.level <= context.level
        and fitsEquipment(context, item, slot)
end

function rating:GetReferenceCandidate(context, item, slot)
    if usable(context, item, slot) then return resultFor(context, item, nil, slot) end
end

-- The offline index uses the same score and compatibility rules as a live pool.
function rating:GetReferenceWindow(firstContext, lastContext, item, slot, contextAt, anyRace)
    local first = math.max(firstContext.level, item.level or 100)
    local last = lastContext.level
    if firstContext.leveling then
        local policy = firstContext.policy
        last = math.min(last, (policy.slot_max_levels or {})[slot] or last)
        if slot == "Two Hand" and policy.weapon_style == "dual_wield" and policy.dual_wield_level then
            last = math.min(last, policy.dual_wield_level - 1)
        end
    end
    if item.excluded or first > last or not fitsEquipment(contextAt(last), item, slot, anyRace) then return end
    local low, high = first, last
    while low < high do
        local middle = math.floor((low + high) / 2)
        if fitsEquipment(contextAt(middle), item, slot, anyRace) then high = middle else low = middle + 1 end
    end
    return low, last
end

function rating:GetUnfilteredReferenceEntry(context, item, slot)
    if item.has_random_stats then
        return { status = "unavailable", item = item }
    end
    return resultFor(context, item, nil, slot)
end

local function slotPool(context, physical, slot, handType, gear, cacheKey, checkpoint)
    if context.pools[cacheKey] then return context.pools[cacheKey] end
    checkpoint = checkpoint or rating:GetWorkCheckpoint()
    local equipped = gear[physical]
    local reference = equipped and equipped.facts
    local candidates, rows, upcoming = {}, {}, {}
    local unresolved, eligible = false, {}
    local function add(item, ownership)
        if checkpoint then checkpoint() end
        item = context.catalog.observed[item.key] or item
        if handType and offHandType(item) ~= handType then return end
        local family = item.roll_group and item.id or item
        local fits = eligible[family]
        if fits == nil then
            fits = usable(context, item, slot) and legalSwap(context, item, physical, slot, gear)
            eligible[family] = fits or false
        end
        if not fits then
            if item.has_random_stats and not item.roll_group and item.level and item.level <= context.level
                and fitsEquipment(context, item, slot) and inScope(context, item) and not item.excluded then
                unresolved = true
                candidates[item.key] = { item = item, status = "unavailable", spec = context.spec, level = context.level,
                    phase = context.phase, slot = slot, source_unknown = guideAccess(context, item.id) ~= "verified" }
            end
            return
        end
        local access = guideAccess(context, item.id)
        if access == "future_phase" then
            if context.guide then
                upcoming[#upcoming + 1] = { item = item, level = context.level, spec = context.spec, slot = slot,
                    phase = context.phase, status = access, future_phase = context.futurePhases[item.id] }
            end
            return
        end
        if access == "character_restriction" or access == "route_out_of_scope" or not inScope(context, item) then return end
        local entry = resultFor(context, item, nil, slot)
        entry.source_unknown = access ~= "verified" or nil
        entry.setup_rank = not context.guide or nil
        entry.ownership = ownership
        if not item.utility and (not entry.score or entry.conditional) then unresolved = true end
        candidates[item.key] = entry
    end
    local function eligibleFamily(base)
        if base.excluded or not base.level or base.level > context.level or not fitsEquipment(context, base, slot)
            or (handType and offHandType(base) ~= handType) or not legalSwap(context, base, physical, slot, gear) then return false end
        local access = guideAccess(context, base.id)
        if access == "route_out_of_scope" or access == "character_restriction" then return false end
        eligible[base.id] = true
        return true
    end
    visitSlot(context.catalog, slot, eligibleFamily, add, checkpoint)
    if slot == "Main Hand" or slot == "Off Hand" then
        visitSlot(context.catalog, "One Hand", eligibleFamily, add, checkpoint)
    end
    for key, item in pairs(context.catalog.observed) do
        if not candidates[key] then add(item) end
    end
    for key, ownership in pairs(context.ownedFacts) do
        if candidates[key] then candidates[key].ownership = ownership else add(ownership.facts, ownership) end
    end
    for _, entry in pairs(candidates) do
        if checkpoint then checkpoint() end
        rows[#rows + 1] = entry
    end
    if checkpoint then checkpoint() end
    table.sort(rows, function(a, b)
        if a.score ~= b.score then return (a.score or -math.huge) > (b.score or -math.huge) end
        if a.item.name ~= b.item.name then return a.item.name < b.item.name end
        return a.item.key < b.item.key
    end)
    local count, previous, rank = 0, nil, nil
    local ties, conditionalTies = {}, {}
    for _, entry in ipairs(rows) do
        if checkpoint then checkpoint() end
        if entry.score ~= nil then
            count = count + 1
            if entry.score ~= previous then previous, rank = entry.score, count end
            entry.rank = rank
            ties[rank] = (ties[rank] or 0) + 1
            if entry.conditional then conditionalTies[rank] = true end
        end
    end
    local bestScore = rows[1] and rows[1].score
    local tiers = placementTiers(rows, count, bestScore)
    for _, entry in ipairs(rows) do
        if checkpoint then checkpoint() end
        if entry.rank then
            entry.provisional = entry.rank == 1 and (unresolved or entry.source_unknown) or nil
            entry.total = count
            entry.tied = ties[entry.rank] > 1 or nil
            entry.conditional_tie = entry.tied and conditionalTies[entry.rank] or nil
            if count > 1 and bestScore > 0 then setRankTier(entry, bestScore, tiers) end
        end
    end
    local pool = { rows = rows, upcoming = upcoming, slot = slot, byVariant = candidates, count = count, bestScore = bestScore,
        scope = { context = context, key = cacheKey, physical = physical, slot = slot, handType = handType, gear = gear } }
    if equipped then
        local placement = resultFor(context, reference, equipped.status, slot)
        if placement.score ~= nil and reference then placement = rating:ProjectPlacement(reference, placement, pool) end
        pool.reference = placement
    end
    if checkpoint then checkpoint() end
    context.pools[cacheKey] = context.pools[cacheKey] or pool
    return context.pools[cacheKey]
end

function rating:GetPlacement(context, physical, slots)
    if not context then return nil end
    local slot, handType = currentComparisonSlot(context, physical, slots)
    return slotPool(context, physical, slot, handType, context.equipmentFacts, physical)
end

function rating:GetComparisonCandidates(pool)
    if pool.comparisonRows then return pool.comparisonRows end
    local context = pool.scope.context
    local guide = context.leveling and self:GetGuideContext(context.class, context.spec, context.phase, context.level,
        context.race, context.faction)
    local summary = guide and self:GetLevelingSummary(guide)
    local ranges = summary and summary.slots[pool.slot]
    if not ranges then return pool.rows end
    local checkpoint = self:GetWorkCheckpoint()
    local rows = {}
    for _, entry in ipairs(pool.rows) do rows[#rows + 1] = entry end
    local function add(key, record)
        if checkpoint then checkpoint() end
        local item = record.item
        if not pool.byVariant[key] and usable(context, item, pool.slot)
            and legalSwap(context, item, pool.scope.physical, pool.slot, pool.scope.gear) then
            local other = self:LevelingPlacementAt(record, context.level)
            if other and other.level ~= context.level then rows[#rows + 1] = other end
        end
    end
    if summary.packed then
        self:VisitPackedGuideOrdinals(ranges, context.level, nil, false, function(ordinal)
            local key = ranges.indices.keys[ordinal]
            if not pool.byVariant[key] then
                local record = self:GetPackedLevelingRecord(guide, pool.slot, key, true)
                if record then add(key, record) end
            end
        end, checkpoint)
    else
        for key, record in pairs(ranges.items) do add(key, record) end
    end
    pool.comparisonRows = rows
    return rows
end

function rating:GetGuidePlacement(context, slot, checkpoint)
    return slotPool(context, slot, slot, nil, {}, slot, checkpoint)
end

function rating:GetGuideEntry(context, slot, key)
    local entry, indexed
    if self.GetPackedGuideEntry then
        entry, indexed = self:GetPackedGuideEntry(context, slot, key)
    end
    if indexed then return entry, nil, true end
    local pool = self:GetGuidePlacement(context, slot)
    return pool.byVariant[key], pool
end

local function levelingGrade(entry)
    if not entry or not entry.rank or entry.score == nil then return nil end
    if entry.total == 1 then return 0 end
    local percent = entry.score_percent
    if not percent then return 0 end
    if percent >= 97 then return 5 end
    if percent >= 85 then return 4 end
    if percent >= 70 then return 3 end
    return 0
end

local function extendLevelRange(ranges, level, grade, estimated)
    local last = ranges[#ranges]
    if not last or last.lastLevel ~= level - 1 or last.grade ~= grade or last.estimated ~= estimated then
        last = { firstLevel = level, grade = grade, estimated = estimated }
        ranges[#ranges + 1] = last
    end
    last.lastLevel = level
    return last
end

local function summarizeGuideSlot(context, slot, summary, checkpoint)
    local pool = rating:GetGuidePlacement(context, slot, checkpoint)
    local choices = addon:GetStatRankGuideChoices(context, pool, checkpoint)
    local level = context.level
    local leader = pool.rows[1]
    for _, entry in ipairs(pool.upcoming) do
        summary.upcoming = summary.upcoming or {}
        if not summary.upcoming[entry.item.key] then summary.upcoming[entry.item.key] = entry end
    end
    if leader and leader.rank == 1 then summary.leaders[level] = leader end
    for _, entry in ipairs(pool.rows) do
        checkpoint()
        local key = entry.item.key
        local choice = choices[key]
        local record = summary.items[key]
        if not record then
            record = { ranked = {}, strength = {}, recommended = {}, leading = {}, item = entry.item, slot = slot }
            summary.items[key] = record
        end
        if entry.rank or choice then
            local ranked = extendLevelRange(record.ranked, level)
            ranked.firstEntry = ranked.firstEntry or entry
            ranked.lastEntry = entry
        end
        local grade = levelingGrade(entry)
        if grade and grade >= 3 then extendLevelRange(record.strength, level, grade, entry.conditional) end
        if entry.rank == 1 then extendLevelRange(record.leading, level) end
        if choice and choice.recommended then
            record.note = choice.effect or record.note
            extendLevelRange(record.recommended, level)
        end
    end
end

local function requestedSlots(summary)
    local slots = {}
    for owner, request in pairs(summary.watchers) do
        if not request.watcher.isCurrent() then
            summary.watchers[owner] = nil
        else
            for _, slot in ipairs(request.slots) do
                if not summary.slots[slot] then slots[slot] = true end
            end
        end
    end
    return slots
end

local function scheduleLevelingSummaries(self)
    local queue = self.levelingSummaryQueue
    if not queue or not queue[1] or self.levelingSummaryScheduled then return end
    self.levelingSummaryScheduled = true
    C_Timer.After(0, function()
        self.levelingSummaryScheduled = nil
        local summary = queue[1]
        if queue ~= self.levelingSummaryQueue or not summary then
            scheduleLevelingSummaries(self)
            return
        end
        if summary.context.catalog.data ~= model()
            or summary.context.phaseIndex ~= addon:GetAvailabilityPhaseIndex("LEVELING") then
            summary.watchers = {}
        end
        local slots = requestedSlots(summary)
        if not next(slots) then
            summary.queued, summary.worker = nil, nil
            table.remove(queue, 1)
            scheduleLevelingSummaries(self)
            return
        end
        if not summary.worker then
            local results = {}
            for slot in pairs(slots) do results[slot] = { items = {}, leaders = {} } end
            summary.worker = coroutine.create(function()
                local function checkpoint()
                    summary.steps = summary.steps + 1
                    if summary.steps >= 65536 or (summary.deadline and summary.steps % 16 == 0 and debugprofilestop() >= summary.deadline) then
                        coroutine.yield()
                    end
                end
                for level = 1, addon.maxLevelingLevel do
                    local context = level == summary.context.level and summary.context
                        or contextAtLevel(summary.context, "LEVELING", level)
                    for slot, result in pairs(results) do
                        summarizeGuideSlot(context, slot, result, checkpoint)
                    end
                end
                return results
            end)
        end

        summary.steps = 0
        summary.deadline = debugprofilestop and debugprofilestop() + 4
        local ok, results = coroutine.resume(summary.worker)
        if not ok or coroutine.status(summary.worker) == "dead" then
            summary.worker = nil
            if ok then
                for slot, result in pairs(results) do summary.slots[slot] = result end
                summary.revision = summary.revision + 1
                local ready = {}
                for owner, request in pairs(summary.watchers) do
                    local complete = true
                    for _, slot in ipairs(request.slots) do
                        if not summary.slots[slot] then complete = false; break end
                    end
                    if complete then
                        summary.watchers[owner] = nil
                        ready[#ready + 1] = request.watcher
                    end
                end
                for _, watcher in ipairs(ready) do
                    if watcher.isCurrent() then watcher.onReady() end
                end
            else
                summary.queued = nil
                table.remove(queue, 1)
                scheduleLevelingSummaries(self)
                error(results)
            end
        end
        scheduleLevelingSummaries(self)
    end)
end

function rating:GetLevelingSummary(context)
    if not context or not context.leveling then return nil end
    local packed = self.GetPackedGuide and self:GetPackedGuide(context)
    if packed then
        context.packedSummary = context.packedSummary or { context = context, slots = packed, revision = 1, packed = true }
        return context.packedSummary
    end
    local data, phase = context.catalog.data, context.phaseIndex
    if self.levelingSummaryData ~= data or self.levelingSummaryPhase ~= phase then
        self.levelingSummaryData, self.levelingSummaryPhase = data, phase
        self.levelingSummaries, self.levelingSummaryQueue = {}, {}
    end
    local summaries = self.levelingSummaries
    for _, summary in ipairs(summaries) do
        local other = summary.context
        if other.class == context.class and other.spec == context.spec
            and other.race == context.race and other.faction == context.faction then return summary end
    end
    if #summaries >= 4 then
        for index, summary in ipairs(summaries) do
            if not summary.queued then table.remove(summaries, index); break end
        end
    end
    local summary = { context = context, slots = {}, watchers = {}, revision = 0 }
    summaries[#summaries + 1] = summary
    return summary
end

function rating:LevelingGuideSlots(context, order)
    local slots = {}
    for _, slot in ipairs(order) do
        if contains(context.commonSlots, slot) or contains(context.policy.slots, slot) then slots[#slots + 1] = slot end
    end
    return slots
end

function rating:RequestLevelingSummary(summary, slots, watcher)
    if not summary or summary.packed or not watcher or not (C_Timer and C_Timer.After) then return end
    for _, slot in ipairs(slots) do
        if not summary.slots[slot] then
            summary.watchers[watcher.owner] = { slots = slots, watcher = watcher }
            if not summary.queued then
                summary.queued = true
                local queue = self.levelingSummaryQueue
                queue[#queue + 1] = summary
            end
            scheduleLevelingSummaries(self)
            return
        end
    end
end

-- Select a current range, the next one, or the latest past one, in that order.
function rating:LevelingRangeAt(ranges, level)
    for _, range in ipairs(ranges or {}) do
        if range.lastLevel >= level then return range end
    end
    return ranges and ranges[#ranges]
end

function rating:LevelingPlacementAt(record, level, current)
    if current and (current.rank or not record) then return current end
    local range = record and self:LevelingRangeAt(record.ranked, level)
    if not range then return current end
    if record.data then
        local evaluated = math.min(range.lastLevel, math.max(range.firstLevel, level))
        return self:GetPackedGuideEntry(record.context, record.slot, record.item.key, evaluated)
    end
    if level > range.lastLevel then return range.lastEntry end
    if level < range.firstLevel or not current then return range.firstEntry end
    return current
end

function rating:GetLevelingRecord(summary, slot, key)
    if summary and summary.packed then return self:GetPackedLevelingRecord(summary.context, slot, key, true) end
    local data = summary and summary.slots[slot]
    return data and data.items[key]
end

function rating:GetLevelingSuccessor(summary, placement)
    if not placement or placement.rank ~= 1 or placement.phase ~= "LEVELING" then return nil end
    if summary and summary.packed then
        local record = self:GetLevelingRecord(summary, placement.slot, placement.item.key)
        return record and self:GetPackedLevelingSuccessor(record, placement) or nil
    end
    local data = summary and summary.slots[placement.slot]
    local record = data and data.items[placement.item.key]
    local leading = record and self:LevelingRangeAt(record.leading, placement.level)
    if not leading or placement.level < leading.firstLevel or placement.level > leading.lastLevel then return nil end
    for level = leading.lastLevel + 1, addon.maxLevelingLevel do
        local eligible = self:LevelingRangeAt(record.ranked, level)
        local nextLead = self:LevelingRangeAt(record.leading, level)
        local leader = data.leaders[level]
        if eligible and level >= eligible.firstLevel and level <= eligible.lastLevel and leader
            and (not nextLead or level < nextLead.firstLevel or level > nextLead.lastLevel) then
            return { level = level, name = leader.item.name, conditional = leader.conditional or placement.conditional }
        end
    end
end

local function benchmarkChoices(context, definition, slots, handType)
    local choices = {}
    for _, slot in ipairs(slots) do
        local pool = slotPool(context, definition.key, slot, handType, {}, "outfit:" .. definition.key .. ":" .. slot)
        for _, entry in ipairs(pool.rows) do
            if entry.score and entry.score > 0 then choices[#choices + 1] = entry end
        end
    end
    table.sort(choices, function(a, b) return a.score > b.score end)
    return choices
end

local function bestKnownOutfit(context, positions)
    local remaining, outfit, best, bestOutfit = {}, {}, 0, {}
    remaining[#positions + 1] = 0
    for index = #positions, 1, -1 do
        remaining[index] = remaining[index + 1] + positions[index].choices[1].score
    end
    local function search(index, total)
        if total + remaining[index] <= best then return end
        local position = positions[index]
        if not position then best, bestOutfit = total, copy(outfit); return end
        for _, choice in ipairs(position.choices) do
            if total + choice.score + remaining[index + 1] <= best then break end
            local item = choice.item
            if legalSwap(context, item, position.key, position.slot, outfit) then
                outfit[position.key] = { facts = item, entry = { item_id = item.id } }
                search(index + 1, total + choice.score)
                outfit[position.key] = nil
            end
        end
        search(index + 1, total)
    end
    search(1, 0)
    return best, bestOutfit
end

function rating:GetGearScore(context, definitions)
    if context.gearScore then return context.gearScore end
    local gear = context.equipmentFacts
    local unreadableSlots = context.owned.unreadableEquipmentSlots or {}
    local twoHand = hasTwoHander(context, gear) or (not gear.MainHand and not gear.OffHand
        and (context.policy.weapon_style == "two_hand"
            or (not contains(context.policy.slots, "Main Hand") and contains(context.policy.slots, "Two Hand"))))
    local positions, currentGear, current, partial = {}, {}, 0, 0
    for _, definition in ipairs(definitions) do
        local key = definition.key
        if not (twoHand and key == "OffHand") then
            local worn = gear[key]
            local item = worn and worn.facts
            local slots = definition.slots
            if key == "MainHand" then slots = { twoHand and "Two Hand" or "Main Hand" } end
            if key == "Ranged" and item and contains(slots, item.slot) then slots = { item.slot } end
            local handType = key == "OffHand" and item and offHandType(item)
            local choices = benchmarkChoices(context, definition, slots, handType)
            local points = item and score(context, item, nil, nil, nil, slots[1])
            local unavailable = unreadableSlots[key] or (worn and not (points or (item and (item.utility or next(item.effects or {})))))
            if item and not unavailable then
                local wearSlot = item.slot
                if wearSlot == "One Hand" then wearSlot = key == "OffHand" and "Off Hand" or "Main Hand" end
                unavailable = not contains(slots, wearSlot) or not usable(context, item, wearSlot) or not inScope(context, item)
            end
            if unavailable then
                partial = partial + 1
            elseif #choices > 0 then
                positions[#positions + 1] = { key = key, slot = slots[1], choices = choices }
                current = current + (points or 0)
                currentGear[key] = worn
            end
        end
    end
    local best, bestOutfit = bestKnownOutfit(context, positions)
    current = self:ReferenceLoadout(context, currentGear) or current
    best = self:ReferenceLoadout(context, bestOutfit) or best
    local percent = best > 0 and scorePercent(math.min(current, best), best) or nil
    local result = { score = current, best = best, percent = percent, tier = percent and scoreGapTier(percent),
        covered = #positions, partial = partial }
    context.gearScore = result
    return result
end

function rating:GetTooltipItem(itemId, link)
    local data = model()
    if not data then return nil end
    local catalog = self:GetCatalog(data)
    local previous = self.tooltipItem
    if previous and previous.item_link == link and previous.entry.item_id == itemId then return previous end
    local key = self:NormalizeLink(itemId, link)
    if not key then return nil end
    if not catalog.items[key] and not catalog.items[tostring(itemId)] then
        local instant = C_Item and C_Item.GetItemInfoInstant or GetItemInfoInstant
        local _, _, _, location = call(instant, link)
        if not readable(location) or type(location) ~= "string" then
            local loaded = self.loadedItems and self.loadedItems[itemId]
            return nil, not loaded and Item and Item.CreateFromItemID and "loading" or "unavailable"
        end
        if not SLOT_BY_LOCATION[location] then return nil end
    end
    local entry = { item_id = itemId, item_link = link }
    local facts, status = resolveLink(self, { catalog = catalog, pending = {} }, entry)
    local candidate = { facts = facts, status = status, entry = entry, item_link = link, key = key }
    if status == "loading" or (facts and facts.level and not facts.unreadable_effects
        and (not facts.native or next(facts.stats) or #facts.effects > 0)) then
        self.tooltipItem = candidate
    else
        self.tooltipItem = nil
    end
    return candidate
end

function rating:IsUnresolvedVariant(itemId, key)
    local base = self:GetPublishedFacts(tostring(itemId))
    return base and base.has_random_stats and (not key or key == tostring(itemId))
end

local function targetSlot(item, definition)
    if item.slot == "One Hand" then
        if definition.key == "MainHand" then return "Main Hand" end
        if definition.key == "OffHand" then return "Off Hand" end
    elseif contains(definition.slots, item.slot) then
        return item.slot
    end
end

local equipmentGroups = {}
local function groupFor(item)
    local slot = item.slot
    local weapons = slot == "One Hand" or slot == "Main Hand" or slot == "Off Hand" or slot == "Two Hand"
    local key = weapons and "Weapons" or (RELIC_SLOTS[slot] and "Ranged" or slot)
    if not equipmentGroups[key] then
        local group = { key = key, definitions = {}, weapons = weapons }
        for _, definition in ipairs(addon:GetEquipmentSlotDefinitions()) do
            if (weapons and (definition.key == "MainHand" or definition.key == "OffHand"))
                or (not weapons and targetSlot(item, definition)) then
                group.definitions[#group.definitions + 1] = definition
            end
        end
        equipmentGroups[key] = group
    end
    return equipmentGroups[key]
end

local function referenceItem(instance, slotLabel)
    local linkName = instance.item_link and instance.item_link:match("|h%[(.-)%]|h")
    return { name = linkName or instance.facts.name, slot = slotLabel, state = instance.state, key = instance.facts.key,
        facts = instance.facts }
end

local function wornReplacement(context, result, key, label)
    local equipped = context.equipmentFacts[key]
    if not equipped then
        if context.owned.unreadableEquipmentSlots and context.owned.unreadableEquipmentSlots[key] then
            result.delta = nil
            result.status = "unavailable"
        end
        return
    end
    local stats, uncertain = swapStats(equipped.facts, equipped.item_link)
    local points = equipped.item_link and score(context, equipped.facts, nil, nil, stats)
    if points == nil and equipped.item_link and equipped.facts
        and (equipped.facts.utility or hasUnscoredEffect(equipped.facts)) then points = 0 end
    if points == nil then
        result.delta = nil
        result.status = equipped.status == "loading" and "loading" or "unavailable"
        return
    end
    result.replacements[#result.replacements + 1] = referenceItem(equipped, label)
    if result.delta ~= nil then result.delta = result.delta - points end
    result.roleDisplaced = result.roleDisplaced + (score(context, equipped.facts, true, nil, stats) or 0)
    result.conditional = result.conditional or uncertain or hasUnscoredEffect(equipped.facts)
end

local function wornSwap(context, group, item, link, wornSlot, scope)
    local gear = context.equipmentFacts
    local unreadableSlots = context.owned.unreadableEquipmentSlots or {}
    local stats, uncertain = swapStats(item, link)
    local points = score(context, item, nil, nil, stats)
    local rolePoints = score(context, item, true, nil, stats)
    local scorer, live, missing = addon.ForeverScoring
    if scorer and (context.leveling or context.phase == "PR") then
        live, missing = scorer:GetContext(context.class, context.spec, context.leveling and "leveling" or "pre_raid",
            context.level, { live = scope.live, race = context.race })
    end
    if live and not live.comparisonRoleWeights then
        live.comparisonRoleWeights = copy(live.weights)
        if not isTank(context) then
            for stat in pairs(DEFENSIVE_STATS) do live.comparisonRoleWeights[stat] = nil end
        end
    end
    local best, bestLive, incompleteLive
    if not context.wornReference or (scope.breakdown and not context.wornReference.breakdown) then
        local baseline, conditional, _, breakdown = rating:ReferenceLoadout(context, gear, nil, scope.breakdown)
        context.wornReference = { total = baseline, conditional = conditional,
            role = baseline and rating:ReferenceLoadout(context, gear, true), breakdown = breakdown }
    end
    for _, definition in ipairs(group.definitions) do
        local slot = targetSlot(item, definition)
        local key = definition.key
        if (not scope.physical or scope.physical == key) and slot and (not scope.slot or scope.slot == slot)
            and usable(context, item, slot) and legalSwap(context, item, key, slot, gear) then
            local result = { definition = definition, slot = slot, gear = gear, delta = points, replacements = {},
                roleDisplaced = 0, basis = "reference", conditional = uncertain or hasUnscoredEffect(item) }
            local worn = gear[key]
            if definition.inventorySlotId == wornSlot and worn and worn.facts and worn.facts.key == item.key then
                result.delta, result.status = nil, "equipped"
                return result
            end
            wornReplacement(context, result, key, definition.label)
            if slot == "Two Hand" then
                wornReplacement(context, result, "OffHand", "Off Hand")
            elseif slot == "Off Hand" and ((gear.MainHand and not gear.MainHand.facts)
                or unreadableSlots.MainHand) then
                result.delta, result.status = nil, gear.MainHand and gear.MainHand.status or "unavailable"
            end
            if item.unique_group and next(unreadableSlots) then result.delta, result.status = nil, result.status or "unavailable" end
            if item.max_equipped and #group.definitions == 2 then
                local otherKey = group.definitions[1].key == key and group.definitions[2].key or group.definitions[1].key
                if unreadableSlots[otherKey] then result.delta, result.status = nil, result.status or "unavailable" end
            end
            if result.delta ~= nil and not result.replacements[1] then result.status = "empty" end
            if result.delta ~= nil then
                local proposal, without = copy(gear), copy(gear)
                proposal[key], without[key] = { facts = item, item_link = link }, nil
                if slot == "Two Hand" then proposal.OffHand, without.OffHand = nil, nil end
                local reference = context.wornReference
                local baseline, before = reference.total, reference.conditional
                if baseline then
                    local total, after, _, breakdown = rating:ReferenceLoadout(context, proposal, nil, scope.breakdown)
                    local roleBaseline = reference.role
                    result.delta = total - baseline
                    if scope.breakdown then result.contributions = scorer:StatDifferences(reference.breakdown, breakdown) end
                    result.roleDelta = rating:ReferenceLoadout(context, proposal, true) - roleBaseline
                    result.roleDisplaced = math.max(0, roleBaseline - rating:ReferenceLoadout(context, without, true))
                    local position = definition.inventorySlotId
                    result.conditional = before[position] or after[position]
                        or (group.weapons and (before[16] or before[17] or after[16] or after[17]))
                else
                    result.roleDelta = (rolePoints or 0) - result.roleDisplaced
                end
            end
            if not best or (result.delta ~= nil and (best.delta == nil or result.delta > best.delta)) then best = result end
            if live then
                local evaluation = not result.status or result.status == "empty"
                evaluation = evaluation and scorer:EvaluateSwap(live, item, link, definition.inventorySlotId, slot,
                    live.comparisonRoleWeights, scope.breakdown)
                if evaluation then
                    local active = copy(result)
                    active.basis = "active"
                    active.delta, active.effects = evaluation.delta, evaluation.effects
                    active.contributions = evaluation.contributions
                    active.roleDelta, active.roleDisplaced = evaluation.roleDelta, evaluation.roleDisplaced
                    active.conditional = evaluation.conditional
                    if not bestLive or active.delta > bestLive.delta then bestLive = active end
                else
                    incompleteLive = true
                end
            end
        end
    end
    if bestLive and not incompleteLive then return bestLive end
    if best and (missing or incompleteLive) then best.conditional = true end
    return best
end

local function explainBlockEffect(context, result, item)
    if not result or not result.conditional or result.unscoredHolyBlock ~= nil then return end
    local function unscored(piece)
        for _, rule in ipairs(piece and piece.effect_rules or {}) do
            if rule.trigger == "block" and rule.school == "holy" then
                local scorer, scenario = addon.ForeverScoring, context.referenceScenario
                if not scorer or not scenario.effect_expectations then return true end
                local shield = scorer:ReferenceItem(piece, piece.stats or {})
                local build = context.activeBuild
                local _, _, applied = scorer.ScoreLoadout({[17] = shield}, rating:ReferenceWeights(context),
                    build and build.profile.operations or {}, build and build.ranks or {}, scenario, context.raceId, context.level)
                if not (applied[17] and applied[17][rule.label]) then return true end
            end
        end
    end
    result.unscoredHolyBlock = unscored(item) or false
    for _, old in ipairs(result.replacements or {}) do
        if unscored(old.facts) then result.unscoredHolyBlock = true; break end
    end
end

function rating:GetGuideSwap(context, item, physical, slot, link, includeBreakdown)
    if not context or not item then return nil end
    local result = wornSwap(context, groupFor(item), item, link, nil, { physical = physical, slot = slot, breakdown = includeBreakdown })
    explainBlockEffect(context, result, item)
    return result
end

function rating:ProjectPlacement(item, placement, pool)
    local known = pool.byVariant[item.key]
    if known then return known end
    local rank, tied, uncertain = 1, false, placement.conditional
    for _, peer in ipairs(pool.rows) do
        if peer.score == nil or peer.score < placement.score then break end
        if peer.score > placement.score then
            rank = rank + 1
        else
            tied, uncertain = true, uncertain or peer.conditional
        end
    end
    placement.rank, placement.total = rank, pool.count + 1
    placement.tied = tied or nil
    placement.conditional_tie = tied and uncertain or nil
    placement.projected = true
    placement.setup_rank = not pool.scope.context.guide or nil
    local best = math.max(pool.bestScore or -math.huge, placement.score)
    if placement.total > 1 and best > 0 then
        local tiers
        if placement.total <= 12 then
            local projected = {}
            for index = 1, pool.count do projected[index] = pool.rows[index] end
            table.insert(projected, rank, placement)
            tiers = placementTiers(projected, placement.total, best)
        end
        setRankTier(placement, best, tiers)
    end
    return placement
end

local function firstUsableSlot(context, group, item)
    for _, definition in ipairs(group.definitions) do
        local slot = targetSlot(item, definition)
        if slot and usable(context, item, slot) then return slot end
    end
end

local function referencePlacement(context, item, slot)
    local reference = rating:GetGuideContext(context.class, context.spec, context.phase, context.level,
        context.race, context.faction)
    local known, pool, indexed = rating:GetGuideEntry(reference, slot, item.key)
    if known then return known, pool and pool.scope end
    local access = guideAccess(reference, item.id)
    if access == "future_phase" then
        return { item = item, slot = slot, phase = context.phase, level = context.level, status = access,
            future_phase = reference.futurePhases[item.id] }
    end
    if access == "route_out_of_scope" or access == "character_restriction" then
        if reference.leveling then
            local records = rating:GetLevelingSummary(reference)
            local entry = rating:LevelingPlacementAt(rating:GetLevelingRecord(records, slot, item.key), context.level)
            if entry then return entry end
            if indexed then return { item = item, slot = slot, phase = context.phase, level = context.level, status = "out_of_scope" } end
            local function at(level)
                local other = contextAtLevel(reference, "LEVELING", level)
                if usable(other, item, slot) and inScope(other, item) then
                    local peers = rating:GetGuidePlacement(other, slot)
                    return peers.byVariant[item.key], peers.scope
                end
            end
            for level = math.max(context.level + 1, item.level), addon.maxLevelingLevel or 59 do
                local entry, scope = at(level)
                if entry then return entry, scope end
            end
            for level = context.level - 1, math.max(1, item.level), -1 do
                local entry, scope = at(level)
                if entry then return entry, scope end
            end
        end
        return { item = item, slot = slot, phase = context.phase, level = context.level, status = "out_of_scope" }
    end
    local placement = resultFor(context, item, nil, slot)
    if placement.score == nil then return placement end
    if indexed then return placement end
    return rating:ProjectPlacement(item, placement, pool), pool.scope
end

local function lookaheadPlacement(context, item)
    local cap = addon.maxLevelingLevel + 1
    if item.level > cap then return { status = "out_of_scope", phase = "PR" } end
    if item.excluded or item.has_random_stats or not permitted(item.classes, context.class)
        or not permitted(item.races, context.race) then return { status = "incompatible" } end

    local group = groupFor(item)
    local checkpoint = rating:GetWorkCheckpoint()
    -- Proficiency can unlock after the item's required level.
    for level = math.max(item.level, context.level + 1), cap do
        if checkpoint then checkpoint() end
        local phase = level == cap and "PR" or "LEVELING"
        local preview = context.tooltipLookahead
        if not preview or preview.level ~= level then
            preview = contextAtLevel(context, phase, level)
        end
        local slot = firstUsableSlot(preview, group, item)
        if slot then
            context.tooltipLookahead = preview
            if not inScope(preview, item) then return { status = "out_of_scope", phase = preview.phase }, nil, preview end
            local placement, scope = referencePlacement(preview, item, slot)
            return placement, scope, preview
        end
    end
    return { status = "incompatible" }
end

local EMPTY_CHOICE = { score = 0, order = math.huge }
local EMPTY_CHOICES = { EMPTY_CHOICE }

-- One copy in a higher priority wins a tie against two lower-priority copies.
local OWNED_PREFERENCE = { equipped = 9, bag = 3, bank = 1 }

local function ownedOption(context, outside, definition, instance)
    local item = instance.facts
    local slot = targetSlot(item, definition)
    if not slot or not usable(context, item, slot) then return nil end
    local capacity = swapCapacity(item, definition.key, slot, outside)
    if capacity < 1 then return nil end
    local stats, uncertain = swapStats(item, instance.item_link)
    local points, conditional = score(context, item, nil, nil, stats, slot)
    return { instance = instance, slot = slot, score = points, capacity = capacity,
        preference = instance == context.equipmentFacts[definition.key] and 27 or OWNED_PREFERENCE[instance.state],
        conditional = uncertain or conditional or (conditional == nil and hasUnscoredEffect(item)) }
end

local function compatiblePair(first, second)
    if not second.instance then return true end
    if not first.instance then
        local offHand = second.instance.facts
        return not offHand.weapon_subtype or offHand.requires_dual_wield == false
    end
    if first.slot == "Two Hand" or first.instance == second.instance then return false end
    return not sharesUniqueLimit(first.instance.facts, second.instance.facts)
        or (first.capacity >= 2 and second.capacity >= 2)
end

local function compareOwnedOptions(a, b)
    if a.score ~= b.score then return a.score > b.score end
    local first, second = a.preference or 0, b.preference or 0
    if first ~= second then return first > second end
    return a.order < b.order
end

local function bestLoadout(firstChoices, secondChoices, value)
    local checkpoint = rating:GetWorkCheckpoint()
    local best
    for _, first in ipairs(firstChoices) do
        if not value and best and first.score + secondChoices[1].score < best.score then break end
        for _, second in ipairs(secondChoices) do
            if checkpoint then checkpoint() end
            local total = first.score + second.score
            if not value and best and total < best.score then break end
            if compatiblePair(first, second) then
                local conditional
                if value then total, conditional = value(first, second) end
                local preference = (first.preference or 0) + (second.preference or 0)
                if not best or total > best.score or (total == best.score and preference > best.preference) then
                    best = { first, second, score = total, conditional = conditional, preference = preference }
                end
                if not value then break end
            end
        end
    end
    return best
end

local function ownedLoadout(context, group)
    local revision = addon.ForeverScoring and addon.ForeverScoring.revision
    local cached = context.ownedLoadouts[group.key]
    if cached and cached.revision == revision then return cached end
    local checkpoint = rating:GetWorkCheckpoint()
    local outside = copy(context.equipmentFacts)
    local options = {}
    local unresolved = context.owned.equippedOnly and "loading" or context.owned.bagsIncomplete and "unavailable" or nil
    local function markUnresolved(status)
        if status == "loading" or not unresolved then unresolved = status or "unavailable" end
    end
    for _, definition in ipairs(group.definitions) do outside[definition.key] = nil end
    for index, definition in ipairs(group.definitions) do
        local choices = {}
        for order, instance in ipairs(context.ownedCopies) do
            if checkpoint then checkpoint() end
            local option = ownedOption(context, outside, definition, instance)
            if option then
                if option.score ~= nil then
                    option.order = order
                    choices[#choices + 1] = option
                elseif instance.facts.utility or next(instance.facts.effects or {}) then
                    option.order, option.score = order, 0
                    choices[#choices + 1] = option
                else
                    markUnresolved()
                end
            end
        end
        for _, copy in ipairs(context.unresolvedCopies) do
            if checkpoint then checkpoint() end
            local item = copy.item
            local slot = item and targetSlot(item, definition)
            if not item or (slot and not item.excluded
                and (not item.level or item.level <= context.level) and fitsEquipment(context, item, slot)) then
                markUnresolved(copy.status)
            end
        end
        local worn = context.equipmentFacts[definition.key]
        if context.owned.unreadableEquipmentSlots and context.owned.unreadableEquipmentSlots[definition.key] then
            markUnresolved()
        elseif worn and (not worn.item_link or not worn.facts or not worn.facts.level) then
            markUnresolved(worn.status)
        end
        choices[#choices + 1] = EMPTY_CHOICE
        table.sort(choices, compareOwnedOptions)
        options[index] = choices
    end
    options[2] = options[2] or EMPTY_CHOICES
    local scenario, scorer = context.referenceScenario, addon.ForeverScoring
    local value
    if scorer and scorer.ReferenceItem
        and (context.activeBuild or scenario.sets or scenario.caps or scenario.conversions or scenario.effect_expectations) then
        local gear = copy(outside)
        value = function(first, second)
            gear[group.definitions[1].key] = first.instance
            if group.definitions[2] then gear[group.definitions[2].key] = second.instance end
            local total, uncertain = rating:ReferenceLoadout(context, gear)
            local conditional
            for _, definition in ipairs(group.definitions) do
                conditional = conditional or uncertain[definition.inventorySlotId]
            end
            return total, conditional
        end
    end
    local state = { outside = outside, options = options, unresolved = unresolved, value = value, revision = revision,
        baseline = bestLoadout(options[1], options[2], value) }
    context.ownedLoadouts[group.key] = state
    return state
end

local function ownedProposal(context, group, state, instance, quantity)
    local best, chosen, chosenIndex
    for index, definition in ipairs(group.definitions) do
        local option = ownedOption(context, state.outside, definition, instance)
        if option then
            -- A reviewed effect-only item still needs a legal target slot.
            option.hasPoints = option.score ~= nil
            option.score = option.score or 0
            local complementary = state.options[3 - index]
            local other = group.definitions[3 - index]
            if other and quantity and quantity > 1 then
                local extra = ownedOption(context, state.outside, other, copy(instance))
                if extra and extra.score then
                    complementary = {}
                    for _, choice in ipairs(state.options[3 - index]) do complementary[#complementary + 1] = choice end
                    complementary[#complementary + 1] = extra
                    extra.order = #complementary
                    table.sort(complementary, compareOwnedOptions)
                end
            end
            local first = index == 1 and { option } or complementary
            local second = index == 2 and { option } or complementary
            local proposal = bestLoadout(first, second, state.value)
            if proposal and (not best or proposal.score > best.score
                or (proposal.score == best.score and proposal.preference > best.preference)) then
                best, chosen, chosenIndex = proposal, option, index
            end
        end
    end
    return best, chosen, chosenIndex
end

local function groupHas(choices, instance)
    return choices[1].instance == instance or choices[2].instance == instance
end

local function groupGear(group, state, choices)
    local gear = copy(state.outside)
    for index, definition in ipairs(group.definitions) do gear[definition.key] = choices[index].instance end
    return gear
end

local function roleScore(context, gear)
    local total = rating:ReferenceLoadout(context, gear, true)
    if total then return total end
    total = 0
    for _, instance in pairs(gear) do
        if instance.facts then
            local stats = swapStats(instance.facts, instance.item_link)
            total = total + (score(context, instance.facts, true, nil, stats) or 0)
        end
    end
    return total
end

local function setRoleChange(context, result, previous, retained)
    local before = roleScore(context, previous)
    result.roleDelta = roleScore(context, result.gear) - before
    result.roleDisplaced = math.max(0, before - roleScore(context, retained))
end

local function findOwnedCopy(context, candidate)
    local preferred = context.ownedFacts[candidate.key]
    if not preferred or not candidate.item_link then return preferred end
    for _, instance in ipairs(context.ownedCopies) do
        if instance.key == candidate.key
            and rating:SameExactItemLink(candidate.entry.item_id, instance.item_link, candidate.item_link) then
            return instance
        end
    end
end

local function equipSwap(context, group, state, worn, proposal, index)
    local previous, proposed = groupGear(group, state, worn), groupGear(group, state, proposal)
    local oldValue, oldUncertain = rating:ReferenceLoadout(context, previous)
    local newValue, newUncertain = rating:ReferenceLoadout(context, proposed)
    if oldValue == nil or newValue == nil or newValue <= oldValue then return nil end
    local result = { delta = newValue - oldValue, definition = group.definitions[index], incoming = {} }
    for position, definition in ipairs(group.definitions) do
        local old, new = worn[position].instance, proposal[position].instance
        if new and not groupHas(worn, new) then
            result.incoming[#result.incoming + 1] = referenceItem(new, definition.label)
        end
        if old ~= new or group.weapons then
            local id = definition.inventorySlotId
            result.conditional = result.conditional or oldUncertain[id] or newUncertain[id]
            if new and context.activeBuild then
                result.conditional = result.conditional or addon.ForeverScoring:HasUnmodeledSwap(
                    context.activeBuild, new.facts, id, proposal[position].slot)
            end
        end
    end
    if rating:ReliableGain(result) then return result end
end

local function getEquipActions(context, group, state)
    if state.actions then return state.actions end
    local worn, actions, changes = { EMPTY_CHOICE, EMPTY_CHOICE }, {}, {}
    for index, definition in ipairs(group.definitions) do
        local instance = context.equipmentFacts[definition.key]
        if instance and instance.facts then
            local slot = targetSlot(instance.facts, definition)
            worn[index] = { instance = instance, slot = slot,
                capacity = swapCapacity(instance.facts, definition.key, slot, state.outside) }
        end
    end
    local best = state.baseline
    for index, choice in ipairs(best) do
        if choice.instance and not groupHas(worn, choice.instance) then changes[#changes + 1] = index end
    end
    local first, second = { best[1], worn[2] }, { worn[1], best[2] }
    local independent = #changes == 2 and compatiblePair(first[1], first[2]) and compatiblePair(second[1], second[2])
    for _, index in ipairs(changes) do
        local action = independent and equipSwap(context, group, state, worn, index == 1 and first or second, index)
        actions[best[index].instance] = action or equipSwap(context, group, state, worn, best, index)
    end
    state.actions = actions
    return actions
end

local function ownedSwap(context, group, candidate, quantity, held)
    local state = ownedLoadout(context, group)
    local instance = held or candidate
    local best, chosen, chosenIndex = ownedProposal(context, group, state, instance, quantity)
    if not best then return nil end
    local baseline = state.baseline
    local previousGear = groupGear(group, state, baseline)
    local retained = copy(previousGear)
    local other = best[3 - chosenIndex].instance
    local gear = copy(state.outside)
    local result = { definition = group.definitions[chosenIndex], slot = chosen.slot, gear = gear, replacements = {},
        delta = chosen.hasPoints and (best.score - baseline.score) or nil, basis = context.activeBuild and "active" or "reference",
        conditional = best.conditional or baseline.conditional, ownership = held and held.state or nil }
    for index, definition in ipairs(group.definitions) do
        local proposed = best[index].instance
        gear[definition.key] = proposed
        local previous = baseline[index].instance
        if not state.value then
            result.conditional = result.conditional or baseline[index].conditional or best[index].conditional
        end
        if (previous and previous.state == "bank") or (other and other.state == "bank") then result.bank = true end
        if previous and not groupHas(best, previous) then
            retained[definition.key] = nil
            result.replacements[#result.replacements + 1] = referenceItem(previous, definition.label)
        end
    end
    if result.delta and result.delta > 0 and not state.unresolved then setRoleChange(context, result, previousGear, retained) end
    if context.activeBuild and addon.ForeverScoring:HasUnmodeledSwap(context.activeBuild, candidate.facts,
        result.definition.inventorySlotId, result.slot) then result.conditional = true end
    if state.unresolved then
        result.delta, result.status = nil, state.unresolved
    elseif candidate.facts.unique_group and next(context.owned.unreadableEquipmentSlots or {}) then
        result.delta, result.status = nil, "unavailable"
    elseif held and groupHas(baseline, held) then
        result.status = "best_owned"
        if not result.conditional and (held.state == "bag" or held.state == "bank") then
            local action = getEquipActions(context, group, state)[held]
            if action then
                result.equipSwap, result.equipNow = action, held.state == "bag"
                for _, partner in ipairs(action.incoming) do
                    if partner.state == "bank" then result.equipNow = false end
                end
            end
        end
    elseif not result.replacements[1] then
        result.status = "empty"
    end
    return result
end

local function previewTooltipItem(context, candidate, quantity, held)
    local item = candidate.facts
    local placement, scope, preview = lookaheadPlacement(context, item)
    local result = { placement = placement, rankScope = scope, preview = true }
    if preview and (placement.status ~= "out_of_scope" or held) then
        local comparison = ownedSwap(preview, groupFor(item), candidate, quantity, held)
        result.forecast = comparison or { status = "blocked" }
        result.forecast.level, result.forecast.phase = preview.level, preview.phase
        explainBlockEffect(preview, result.forecast, item)
    end
    return result
end

local function assessTooltipItem(context, candidate, useWorn, wornSlot, extraCopy, scope)
    local item = candidate.facts
    if not item.level then return { placement = { status = candidate.status or "unavailable" } } end
    local held = scope.ownedCopy or (not useWorn and not extraCopy and findOwnedCopy(context, candidate))
    local quantity = extraCopy and scope.quantity
    if item.level > context.level then
        if scope.lookahead then return previewTooltipItem(context, candidate, quantity, held) end
        return { placement = { status = "level" } }
    end
    local inGuide = inScope(context, item)
    local outside = not inGuide and { status = "out_of_scope", phase = context.phase }
    if outside and not held then return { placement = outside } end
    local group = groupFor(item)
    local slot = firstUsableSlot(context, group, item)
    if not slot then
        if scope.lookahead and context.leveling then
            return previewTooltipItem(context, candidate, quantity, held)
        end
        return { placement = { status = "incompatible" } }
    end
    local result
    if useWorn then
        result = wornSwap(context, group, item, candidate.item_link, wornSlot, scope)
    else
        local build, missing = rating:WithCharacterBuild(context, scope.live)
        result = ownedSwap(build, group, candidate, quantity, held)
        if result and missing then
            result.conditional = true
            result.buildUnavailable = missing
            result.equipSwap, result.equipNow = nil, nil
        end
    end
    if not result then
        if scope.skipPlacement then return { placement = { status = "blocked" } } end
        if outside then return {placement = outside, status = "blocked"} end
        local placement, rankScope = referencePlacement(context, item, slot)
        return { placement = placement, rankScope = rankScope, status = "blocked" }
    end
    if outside then
        result.placement = outside
    elseif scope.skipPlacement then
        result.placement = resultFor(context, item, nil, result.slot)
    else
        result.placement, result.rankScope = referencePlacement(context, item, result.slot)
    end
    explainBlockEffect(context, result, item)
    result.effectNote = rating:GetReviewedGuideEffect(context, item)
        or (result.conditional and hasUnscoredEffect(item) and "Some item effects have an unverified value")
    if result.conditional and result.basis == "reference" and result.delta and result.delta < 0
        and (result.slot == "Main Hand" or result.slot == "Two Hand") and #(item.effect_rules or {}) == 1
        and item.effect_rules[1].kind == "extra_attack" then
        local low, high = item.stats.weapon_min_damage, item.stats.weapon_max_damage
        local weight = rating:ReferenceWeights(context).dps
        if low and high and low + high > 0 and weight and weight > 0 then
            result.effectBreakEven = -result.delta * 120 / ((low + high) * weight)
        end
    end
    return result
end

local function approvedBiS(context, candidate, slot)
    if not slot or context.phase == "LEVELING" or not addon.IsConfirmedGearBiS then return false end
    local id = candidate.entry.item_id
    local history = addon:GetRecommendationHistory(id, context.class, context.spec, context.phase, slot, candidate.key)
    return addon:IsConfirmedGearBiS(history, context.phase, id, candidate.key)
end

function rating:CompareTooltipItem(context, candidate, useWorn, wornSlot, extraCopy, scope)
    scope = scope or {}
    local scorer = addon.ForeverScoring
    local revision = scorer and scorer.revision
    local last = context.lastTooltip
    if last and last.candidate == candidate and last.useWorn == useWorn and last.wornSlot == wornSlot
        and last.extraCopy == extraCopy and last.revision == revision and last.live == scope.live
        and last.physical == scope.physical and last.slot == scope.slot
        and last.skipPlacement == scope.skipPlacement
        and last.quantity == scope.quantity and last.ownedCopy == scope.ownedCopy
        and (last.lookahead == scope.lookahead or last.result.slot) then
        return last.result
    end
    local result = assessTooltipItem(context, candidate, useWorn, wornSlot, extraCopy, scope)
    local owned = scope.ownedCopy or context.ownedFacts[candidate.key]
    result.ownership = result.ownership or (owned and owned.state)
    result.bis = approvedBiS(context, candidate, result.slot)
    context.lastTooltip = { candidate = candidate, useWorn = useWorn, wornSlot = wornSlot, extraCopy = extraCopy,
        result = result, revision = revision, live = scope.live, physical = scope.physical, slot = scope.slot,
        lookahead = scope.lookahead, skipPlacement = scope.skipPlacement, quantity = scope.quantity, ownedCopy = scope.ownedCopy }
    return result
end

function rating:GetStorageComparison(context, candidate, sourceId, guid)
    local instance = context.storageCopies[sourceId]
    if not instance or (guid and instance.entry.guid and instance.entry.guid ~= guid)
        or not self:SameExactItemLink(candidate.entry.item_id, instance.item_link, candidate.item_link) then return nil end
    return self:GetHeldComparison(context, instance)
end

function rating:GetHeldComparison(context, instance)
    local revision = addon.ForeverScoring and addon.ForeverScoring.revision
    if not context.heldComparisons or context.heldRevision ~= revision then
        context.heldComparisons, context.heldRevision = {}, revision
    end
    local result = context.heldComparisons[instance]
    if not result then
        result = self:CompareTooltipItem(context, instance, false, nil, false,
            { live = true, lookahead = true, ownedCopy = instance })
        context.heldComparisons[instance] = result
    end
    return result
end

function rating:GetQualifyingUpgrade(context, candidate, owned, scope)
    local swap = self:CompareTooltipItem(context, candidate, owned, nil, not owned, scope)
    if self:ReliableGain(swap) then
        return swap
    end
end

function rating:WithGuaranteedRewards(context, rewards)
    if #rewards == 0 then return context end
    local combined = copy(context)
    combined.tooltipLookahead, combined.opportunities, combined.ownedBuild = nil, nil, nil
    combined.ownedCopies, combined.ownedLoadouts, combined.lastTooltip = {}, {}, nil
    combined.equipmentFacts, combined.pools = copy(context.equipmentFacts), {}
    for _, instance in ipairs(context.ownedCopies) do
        combined.ownedCopies[#combined.ownedCopies + 1] = instance
    end
    local groups, seen = {}, {}
    for _, reward in ipairs(rewards) do
        local candidate = reward.candidate
        local group = groupFor(candidate.facts)
        if #group.definitions > 0 and not seen[group.key] then
            groups[#groups + 1], seen[group.key] = group, true
        end
        for _ = 1, math.min(2, reward.quantity) do
            combined.ownedCopies[#combined.ownedCopies + 1] = {
                facts = candidate.facts, item_link = candidate.item_link, entry = candidate.entry, state = "reward",
            }
        end
    end
    table.sort(groups, function(a, b) return a.definitions[1].inventorySlotId < b.definitions[1].inventorySlotId end)
    for _, group in ipairs(groups) do
        local fitted = ownedLoadout(combined, group)
        for index, definition in ipairs(group.definitions) do
            combined.equipmentFacts[definition.key] = fitted.baseline[index].instance
        end
    end
    combined.ownedLoadouts = {}
    return combined
end

function rating:RoundedGain(delta)
    if not finite(delta) then return nil end
    local points = math.floor(math.abs(delta) * 10 + 0.5) / 10
    return delta < 0 and -points or points
end

function rating:ReliableGain(swap)
    if swap and not swap.conditional and finite(swap.delta) and swap.delta > 0 then return swap.delta end
end

function rating:EstimateSwapPoints(delta)
    local points = self:RoundedGain(delta)
    if points == nil then return nil end
    if delta == 0 then return "0.0 pts" end
    if math.abs(delta) >= 0.1 then return string.format("%+.1f pts", points) end
    if math.abs(delta) < 0.001 then return delta > 0 and "+<0.001 pts" or "-<0.001 pts" end
    local precise = string.format("%+.3f", delta):gsub("0+$", "")
    return precise .. " pts"
end

function rating:UpgradeSize(swap)
    if not self:ReliableGain(swap) then return nil end
    if not swap.roleDelta or not swap.roleDisplaced then return "Slight upgrade" end
    local gain = math.min(swap.delta, swap.roleDelta)
    if gain >= math.max(6, swap.roleDisplaced * 0.15) then return "Major upgrade" end
    if gain >= math.max(2, swap.roleDisplaced * 0.05) then return "Upgrade" end
    return "Slight upgrade"
end

function rating:IsMeaningfulOwnedUpgrade(result)
    if not self:ReliableGain(result) or not result.roleDelta then return false end
    if result.status == "empty" then return self:RoundedGain(result.roleDelta) >= 0.1 end
    return math.min(result.delta, result.roleDelta) >= math.max(2, (result.roleDisplaced or 0) * 0.05)
end

function rating:GetSwapBasisLabel(basis)
    return basis == "active" and "Your setup" or "Default spec weights"
end

function rating:Label(entry, layout, showProjection)
    if not entry then return "Stats unavailable" end
    if entry.future_phase then return "Available with " .. addon:GetPhaseDisplayName(entry.future_phase) end
    local projected = showProjection and entry.projected
    if entry.rank and entry.total > 1 then
        local label = projected and "Projected" or (entry.tier and entry.tier.label or "Rank")
        local prefix = entry.conditional_tie and "Estimated tie " or (entry.tied and "Tied " or "")
        local position = prefix .. "#" .. entry.rank
        if layout == "compact" then return string.format("%s %s/%d", label, position, entry.total) end
        local separator = layout == "stacked" and "\n" or " · "
        return string.format("%s%s%s / %d", label, separator, position, entry.total)
    end
    if entry.score ~= nil then return string.format("%s%.1f pts", projected and "Projected · " or "", entry.score) end
    if entry.status == "out_of_scope" then
        return entry.phase == "LEVELING" and "Outside Leveling rankings" or "Outside Pre-Raid rankings"
    end
    return STATUS_LABELS[entry.status] or STATUS_LABELS.unavailable
end

function rating:ScopeLabel(entry)
    return entry.phase == "LEVELING" and ("Level " .. entry.level) or addon:GetPhaseDisplayName(entry.phase)
end

function rating:ContextLabel(entry)
    return entry.spec .. " · " .. self:ScopeLabel(entry)
end

function rating:DescriptionLines(entry)
    local exact = self:Label(entry)
    if entry.phase == "LEVELING" and entry.rank then
        exact = (entry.tied and "Tied " or "") .. "Rank #" .. entry.rank .. " of " .. entry.total
    end
    local lines = { exact, self:ContextLabel(entry) }
    if entry.score_percent ~= nil then
        lines[3] = string.format("%d%% of the best known stat score", entry.score_percent)
    end
    if entry.placement_color and entry.phase ~= "LEVELING" then lines[#lines + 1] = "Color uses placement in this slot" end
    if entry.setup_rank then lines[#lines + 1] = "Rank in this equipped setup" end
    if entry.projected then lines[#lines + 1] = "Projected placement among known gear" end
    if entry.conditional or entry.conditional_tie then lines[#lines + 1] = "Some item effects have an unverified value" end
    return lines
end

function rating:GetRowItem(row)
    if not row then return nil end
    local item = row.stat_rank and row.stat_rank.item
    if item and item.stats_unavailable and not item.has_random_stats then
        local exact = row.item_link or item.variant_link or ("item:" .. item.id)
        local loaded = self:GetTooltipItem(item.id, exact)
        if loaded and loaded.facts then return loaded.facts end
        if loaded and loaded.status == "loading" then return nil, "loading" end
    end
    if item and (not item.has_random_stats or row.stat_rank.status == "unavailable") then return item end
    if not row.item_id then return nil end
    local key = row.variant_id or self:NormalizeLink(row.item_id, row.item_link) or tostring(row.item_id)
    local facts = self:GetPublishedFacts(key)
    if facts and not facts.has_random_stats then return facts end
    if row.item_link and not self:IsUnresolvedVariant(row.item_id, key) then
        local candidate, status = self:GetTooltipItem(row.item_id, row.item_link)
        return candidate and candidate.facts, candidate and candidate.status or status
    end
end

-- Activity totals compare an additional copy with the best legal gear already owned.
function rating:GetOwnedOpportunity(context, item, link, live)
    if not context or not item or not item.level or item.level > context.level then return nil end
    local group = groupFor(item)
    if not inScope(context, item) or not firstUsableSlot(context, group, item) then return nil end
    local build, missing = self:WithCharacterBuild(context, live)
    if missing then return nil, "unavailable" end
    local revision = addon.ForeverScoring and addon.ForeverScoring.revision
    if build.opportunityRevision ~= revision then build.opportunities, build.opportunityRevision = nil, revision end
    build.opportunities = build.opportunities or {}
    local key = item.key .. "\031" .. (link or "")
    local result = build.opportunities[key]
    if not result then
        result = ownedSwap(build, group, {facts = item, key = item.key, entry = {item_id = item.id}, item_link = link})
            or {status = "blocked"}
        build.opportunities[key] = result
    end
    return result, result.status
end

-- Membership, points, and the named comparison travel together into every Guide view.
function rating:GetGuideTargetVerdict(row, guide, player, owned, inspecting)
    local evaluated = math.max(guide.level, row.guide_route_level or 0, player and player.level or 0)
    local item, pending = self:GetRowItem(row)
    local note = item and self:GetReviewedGuideEffect(guide, item)
    if not player or player.class ~= guide.class then
        local entry = row.stat_rank or {}
        local pick = note or entry.rank == 1 or (entry.score_percent or 0) >= 70
        return {kind = pick and (note and "utility" or "reference") or "hidden", reference = true, note = note}
    end
    local personal = owned and self:GetContext(guide.class, guide.spec, evaluated >= 60 and "PR" or "LEVELING", evaluated, owned)
    local swap, status
    if personal and item then
        local instance = inspecting and findOwnedCopy(personal, { key = item.key, entry = {item_id = item.id},
            item_link = row.item_link })
        if instance then
            swap = self:GetHeldComparison(personal, instance)
            status = swap.status
        else
            swap, status = self:GetOwnedOpportunity(personal, item, row.item_link, evaluated == player.level)
        end
    end
    local gain = self:ReliableGain(swap)
    local held = personal and item and personal.ownedFacts[item.key]
    local kind
    if gain then kind = "upgrade"
    elseif note and not held then kind = "utility"
    elseif status == "blocked" or swap and not swap.conditional and (finite(swap.delta) or status == "best_owned") then kind = "hidden"
    else kind = "unknown" end
    local result = swap or {status = pending or status or "unavailable"}
    local proficiencyLevel
    if evaluated > player.level then
        if personal and item then
            local function atLevel(level)
                return self:GetContext(guide.class, guide.spec, level == 60 and "PR" or "LEVELING", level, owned)
            end
            proficiencyLevel = self:GetReferenceWindow(atLevel(player.level), personal, item, row.slot, atLevel)
        end
        result = copy(result)
        result.level = evaluated
        result = {forecast = result}
    end
    return {kind = kind, swap = result, gain = gain, note = note, level = evaluated,
        proficiencyLevel = proficiencyLevel, owned = held}
end

function rating:GetGuideOwnedNames(context, slot, live)
    if not context then return end
    local build, missing = self:WithCharacterBuild(context, live)
    if missing then return end
    local group = groupFor({slot = slot})
    if #group.definitions == 0 then return end
    local state = ownedLoadout(build, group)
    if state.unresolved then return end
    local names = {}
    for i, definition in ipairs(group.definitions) do
        local instance = state.baseline[i].instance
        if instance then names[#names + 1] = referenceItem(instance, definition.label).name end
    end
    return table.concat(names, " + ")
end

function rating:GetLiveLevelingSwap(item, link, owned, physical, player, equipped, exact)
    if not player or not player.spec or not item then return nil end
    if item.stats_unavailable or item.has_random_stats then return { status = "unavailable" } end
    local context = self:GetContext(player.class, player.spec, player.phase, player.level, owned)
    if not context then return nil end
    local revision = addon.ForeverScoring and addon.ForeverScoring.revision
    if context.liveLevelingRevision ~= revision then
        context.liveLevelingRevision, context.liveLevelingSwaps = revision, {}
    end
    context.liveLevelingSwaps = context.liveLevelingSwaps or {}
    local key = table.concat({ item.key, link or "", physical or "", tostring(equipped == true), tostring(exact == true) }, "\031")
    local result = context.liveLevelingSwaps[key]
    if result then return result end
    local candidate = { facts = item, key = item.key, item_link = link, entry = {item_id = item.id} }
    local held = equipped and physical and context.equipmentFacts[physical]
    if not held or held.key ~= item.key or (link and not self:SameExactItemLink(item.id, held.item_link, link)) then
        held = findOwnedCopy(context, candidate) or (not exact and context.ownedFacts[item.key])
    end
    result = held and self:GetHeldComparison(context, held) or self:CompareTooltipItem(context, candidate, false, nil, true,
        { live = true, lookahead = true, skipPlacement = true })
    context.liveLevelingSwaps[key] = result
    return result
end

local LEVELING_GRADES = { [5] = "Among the best", [4] = "Strong", [3] = "Good option" }
local COMPACT_GRADES = { [5] = "Top", [4] = "Strong", [3] = "Good", [0] = "Weaker" }
local SOURCE_GATES = { quest = "Quest available", dungeon = "Dungeon available", vendor = "Vendor available",
    crafting = "Craftable", drop = "Can drop" }

local function atLevels(first, last)
    if last and last > first then return " at Levels " .. first .. "–" .. last end
    return " at Level " .. first
end

function rating:GetLevelingCue(result)
    if not result then return nil end
    local placement, forecast = result.placement, result.forecast
    local grade
    if placement and placement.phase == "LEVELING" then grade = levelingGrade(placement) end
    if forecast and not result.conditional and forecast.level <= addon.maxLevelingLevel + 1
        and (forecast.equipSwap or self:ReliableGain(forecast)) then
        return grade, forecast.level
    end
    return grade
end

function rating:LevelingRangeText(range)
    local grade = LEVELING_GRADES[range.grade]
    return (range.estimated and "Estimated · " or "") .. grade .. atLevels(range.firstLevel, range.lastLevel)
end

local function levelingRankText(placement)
    if not placement then return nil end
    local grade = levelingGrade(placement)
    local level = placement.level
    if not grade then
        if placement.future_phase then return "Available with " .. addon:GetPhaseDisplayName(placement.future_phase) end
        if placement.status == "out_of_scope" then return "Outside Leveling rankings" end
        return STATUS_LABELS[placement.status] or "Gear comparison unavailable"
    end
    local label
    if placement.total == 1 then
        label = "Only ranked option"
    elseif placement.rank == 1 then
        if placement.provisional or placement.projected then
            label = placement.tied and "Tied for highest known score" or "Highest known score"
        else
            label = placement.tied and "Tied for best" or "Best in Slot"
        end
    else
        label = LEVELING_GRADES[grade] or "Better options"
    end
    if placement.conditional or placement.conditional_tie or placement.projected then label = "Estimated · " .. label end
    return label .. atLevels(level), grade
end

local function itemNames(items)
    local names = {}
    for _, item in ipairs(items or {}) do names[#names + 1] = item.name end
    return table.concat(names, " + ")
end

local function gearVerdict(self, input, view)
    local swap = input.swap or {}
    local forecast = swap.forecast
    local result = forecast or swap
    local ownership = input.ownership or swap.ownership
    local ownedBaseline = input.ownedBaseline or forecast
    local names = itemNames(result.replacements)
    local slot = (result.slot or (result.definition and result.definition.label) or "gear"):lower()
    local delta = result.delta
    local suffix = forecast and atLevels(result.level) or ""
    local previewing = input.playerLevel and input.viewedLevel and input.playerLevel ~= input.viewedLevel
    local conditional = result.conditional or swap.conditional
    local status = result.status
    if status == "loading" or status == "unavailable" or status == "blocked" then
        view.today = (status == "loading" and "Waiting for item stats" or status == "blocked" and "No legal swap"
            or (input.item and (input.item.stats_unavailable or input.item.has_random_stats)) and "Stats unavailable"
            or "Gear comparison unavailable") .. suffix
        view.tone = "unknown"
        return
    end
    if status == "equipped" then
        view.today = result.definition and ("Equipped · " .. result.definition.label) or "Equipped"
        return
    end

    local winner = status == "best_owned"
    if not winner and not finite(delta) then return end
    local gain = self:ReliableGain(result)
    local points
    if not winner then
        points = self:EstimateSwapPoints(delta)
        local baseline = names ~= "" and names or (status == "empty" and ("an empty " .. slot .. " slot")
            or ownedBaseline and "your best owned gear" or "your equipped gear")
        view.evidence = (forecast and "Estimated " or "") .. points .. " vs " .. baseline .. suffix
    end
    if winner then
        view.today = (conditional and "Depends on your setup" or "Best you own for this slot") .. suffix
        if conditional then view.tone = "uncertain"
        elseif forecast then view.tone = "future"
        elseif result.equipNow and input.activeSpec ~= false then
            view.evidence, view.evidenceGain = "Equip now", true
            local partners = {}
            for _, piece in ipairs(result.equipSwap.incoming) do
                if piece.slot ~= result.equipSwap.definition.label then partners[#partners + 1] = piece.name end
            end
            if #partners > 0 then view.evidence = view.evidence .. " · With " .. table.concat(partners, " + ") end
        end
    elseif conditional then
        view.today = delta > 0 and "Possible upgrade" or "Depends on your setup"
        local item = input.item
        if result.unscoredHolyBlock then view.today = view.today .. " · Holy damage on block unscored" end
        for _, effect in ipairs(item and item.effects or {}) do
            if type(effect) == "string" and effect:lower():find("chance on hit", 1, true) then
                view.today = view.today .. " · Chance-on-hit effect unscored"
                break
            end
        end
        view.today = view.today .. suffix
        view.evidence = view.evidence .. " · Scored stats only"
        view.tone = "uncertain"
    elseif forecast then
        view.tone = "future"
        if gain then
            view.futureLevel = result.level
            view.today = (ownership == "bag" or ownership == "bank") and ("Keep for Level " .. result.level)
                or ("Likely upgrade" .. suffix)
        else view.today = (delta < 0 and "Likely downgrade" or "Likely sidegrade") .. suffix end
    elseif gain then
        view.tone, view.gain = "gain", gain
        local label = self:UpgradeSize(result)
        if status == "empty" then label = "Fills your empty " .. slot .. " slot" end
        if input.chooseReward then label = "Choose this reward · " .. label end
        view.today = label
    elseif delta < 0 then
        view.today, view.tone = "Downgrade", "loss"
        for _, other in ipairs(result.replacements or {}) do
            if ownedBaseline and (other.state == "bag" or other.state == "bank") then
                local kind = result.slot == "Ring" and "ring" or result.slot == "Trinket" and "trinket" or "option"
                view.today = "You own a stronger " .. kind .. " · " .. other.name
                break
            end
        end
    else
        view.today = "Sidegrade"
    end
    if not winner and input.activeSpec == false and input.spec then view.today = view.today .. " for " .. input.spec end
    if previewing and not forecast then view.today = view.today .. atLevels(input.playerLevel) end
    if forecast then
        view.forecast, view.forecastPoints, view.forecastLevel = view.today, points, result.level
    else
        view.todayPoints, view.todayLevel = points, input.playerLevel
    end
end

function rating:LevelingPresentation(input)
    local item, placement, swap, playerLevel = input.item, input.placement, input.swap, input.playerLevel
    local record = input.record
    local view = { sourceUnknown = placement and placement.source_unknown }
    if placement and placement.phase == "LEVELING" then
        view.rank, view.grade = levelingRankText(placement)
    end
    local evaluated = placement and placement.phase == "LEVELING" and placement.level or input.viewedLevel or playerLevel
    local range = evaluated and record and self:LevelingRangeAt(record.strength, evaluated)
    if range then
        view.range = self:LevelingRangeText(range)
        view.compactRange = "Lv " .. range.firstLevel
            .. (range.lastLevel > range.firstLevel and ("–" .. range.lastLevel) or "")
            .. " " .. (range.estimated and "Est. " or "") .. COMPACT_GRADES[range.grade]
        if view.range == view.rank then view.range = nil end
    end
    local minimum = item and item.level
    local forecast = swap and swap.forecast
    if minimum and playerLevel and minimum > playerLevel and not input.nativeRequirement then
        view.requirement = "Requires Level " .. minimum
    end
    local unlock = input.proficiencyLevel or (not input.guideForecast and forecast and forecast.level)
    if unlock and minimum and unlock > math.max(playerLevel or 0, minimum) then
        local proficiency = "Can equip at Level " .. unlock
        view.requirement = view.requirement and (view.requirement .. " · " .. proficiency) or proficiency
    end
    if input.sourceLevel and input.sourceLevel > (minimum or 0)
        and (input.sourceLevel > (playerLevel or 0) or input.sourceLevel > (input.viewedLevel or playerLevel or 0)) then
        view.acquisition = (SOURCE_GATES[input.sourceType] or "Source available") .. atLevels(input.sourceLevel)
    end
    gearVerdict(self, input, view)
    if input.personalSpec and view.today then view.today = view.today .. " · " .. input.personalSpec end
    view.swap = swap
    view.action = view.today
    view.today = view.today or view.requirement
    if not view.today and playerLevel and not forecast and item and item.level and item.level <= playerLevel then
        local status = placement and placement.status
        view.today = item.stats_unavailable and "Stats unavailable" or status == "incompatible" and "No comparison for this spec" or "Gear comparison unavailable"
        if status == "out_of_scope" then view.today = nil end
    end
    if placement and placement.phase == "PR" then
        view.rank = self:Label(placement, nil, true)
        if placement.rank or placement.score then view.rank = view.rank .. " · Pre-Raid" end
        view.compact = self:Label(placement, "compact", true)
    end
    view.strength = view.rank or view.range
    if view.grade then
        local label = COMPACT_GRADES[view.grade]
        if placement.total == 1 then label = "Only option"
        elseif placement.rank == 1 then
            label = (placement.provisional or placement.projected) and (placement.tied and "Tied highest" or "Highest known")
                or (placement.tied and "Tied best" or "Best in Slot")
        end
        if placement.conditional or placement.conditional_tie or placement.projected then label = "Est. " .. label end
        view.compact = "Lv " .. placement.level .. " " .. label
    end
    if range and view.rank and placement and placement.rank ~= 1 and range.grade == view.grade
        and range.firstLevel <= evaluated and range.lastLevel >= evaluated and not input.explicitPreview
        and (not input.viewedLevel or input.viewedLevel == evaluated) then
        view.strength = self:LevelingRangeText(range)
        view.compact = view.compactRange
    end
    return view
end

function rating:LevelingPresentationLines(view)
    local lines = {}
    local function add(text)
        if text then lines[#lines + 1] = text end
    end
    local widgets = addon.Widgets
    add(widgets and widgets:GearAdviceText(view) or view.today)
    add(widgets and widgets:GearIconText(view.evidenceGain and "upgradeArrow", view.evidence) or view.evidence)
    if view.requirement ~= view.today then add(view.requirement) end
    if view.strength ~= view.today then add(view.strength) end
    if view.range ~= view.strength then add(view.range) end
    add(view.acquisition)
    add(view.lookupReason)
    if view.sourceUnknown then add("Source unknown") end
    return lines
end
