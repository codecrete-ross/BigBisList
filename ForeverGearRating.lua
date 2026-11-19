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
    loading = "Loading stats", unavailable = "Stats unavailable", utility = "Utility", effect = "Effect only",
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

function rating:GetCatalog(data)
    if self.catalog and self.catalog.data == data then return self.catalog end
    local catalog = { data = data, items = {}, slots = {} }
    for key, row in pairs(data.items) do
        local item = { key = key }
        for index, field in ipairs(data.item_fields) do item[field] = row[index] end
        item.variant_link = data.variant_links and data.variant_links[key]
        catalog.items[key] = item
        local slot = item.slot
        catalog.slots[slot] = catalog.slots[slot] or {}
        table.insert(catalog.slots[slot], item)
    end
    self.catalog = catalog
    self.native = {}
    self.tooltipItem = nil
    return catalog
end

function rating:GetPublishedFacts(key)
    local data = model()
    return data and self:GetCatalog(data).items[key]
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
    if statLink and (not facts or not facts.level) then
        local native
        native, unavailable = self:ReadNative(id, key, statLink, base)
        if facts and native then
            facts = copy(facts)
            facts.level = native.level
        elseif not facts then
            facts = native
        end
    end
    if unavailable == "loading" then context.pending[id] = true end
    return facts, unavailable
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
    local inventory = { catalog = catalog, pending = {}, equipment = {}, byVariant = {}, bySource = {}, copies = {}, unresolvedCopies = {} }
    local function read(entry, state)
        local facts, status = resolveLink(self, inventory, entry)
        local instance = { facts = facts, status = status, entry = entry, item_link = entry.item_link, state = state }
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
            if unresolved then inventory.unresolvedCopies[#inventory.unresolvedCopies + 1] = unresolved end
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
        for _, entry in ipairs(owned.gearCopies) do read(entry, entry.state) end
    else
        for _, entry in pairs(owned.gearStatLinks or {}) do
            if entry.state ~= "equipped" then read(entry, entry.state) end
        end
    end
    return inventory
end

local SCENARIO_LABELS = { outdoor = "Outdoor", dungeon = "Dungeon", pre_raid = "Pre-Raid" }

function rating:GetScenarios(className, spec, phase, level)
    local mode = phase == "LEVELING" and "leveling" or "pre_raid"
    local default = mode == "leveling" and "outdoor" or "pre_raid"
    local scorer = addon.ForeverScoring
    if scorer and scorer.GetPreset and scorer:GetPreset(className, spec, mode, level, "dungeon") then
        return {default, "dungeon"}
    end
    return {default}
end

function rating:GetScenario(className, spec, phase, level, requested)
    local scenarios = self:GetScenarios(className, spec, phase, level)
    requested = requested or (addon.GetGearScenario and addon:GetGearScenario(className, spec, phase))
    return contains(scenarios, requested) and requested or scenarios[1]
end

function rating:GetScenarioContexts(className, spec, phase, level, owned)
    local result = {}
    local selected = self:GetScenario(className, spec, phase, level)
    local current = self:GetContext(className, spec, phase, level, owned, selected)
    if current then result[1] = current end
    for _, scenario in ipairs(self:GetScenarios(className, spec, phase, level)) do
        if scenario ~= selected then
            local context = self:GetContext(className, spec, phase, level, owned, scenario)
            if context then result[#result + 1] = context end
        end
    end
    return result
end

function rating:ScenarioLabel(key)
    return SCENARIO_LABELS[key]
end

local function scoringContext(data, profile, className, spec, phase, level, phaseIndex, race, faction, scenarioKey)
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
        and scorer:GetPreset(className, spec, leveling and "leveling" or "pre_raid", level, scenarioKey)
    if scenarioKey == "dungeon" and scenario then
        for _, band in ipairs(scenario.weights) do
            if level >= band[1] and level <= band[2] then weights = band[3]; break end
        end
    end
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
        scenario = scenarioKey, referenceScenario = scenario, raceId = raceId,
    }
end

local function contextAtLevel(context, phase, level, scenario)
    local data = context.catalog.data
    local profile = data.profiles[context.class .. "/" .. context.spec]
    local samePhase = phase == context.phase
    local phaseIndex = samePhase and context.phaseIndex or addon:GetAvailabilityPhaseIndex(phase)
    local projected = scoringContext(data, profile, context.class, context.spec, phase, level, phaseIndex,
        context.race, context.faction, rating:GetScenario(context.class, context.spec, phase, level,
            scenario or (samePhase and context.scenario or nil)))
    projected.catalog, projected.ownedFacts = context.catalog, context.ownedFacts
    projected.owned, projected.equipmentFacts, projected.guide = context.owned, context.equipmentFacts, context.guide
    projected.ownedCopies, projected.unresolvedCopies, projected.ownedLoadouts = context.ownedCopies, context.unresolvedCopies, {}
    -- Native source scope checks the content phase. Guide routes also depend on the level.
    if samePhase and not context.guide then projected.inScope = context.inScope end
    return projected
end

function rating:GetContext(className, spec, phase, level, owned, requested)
    local data = model()
    if not data or not owned then return nil end
    local profile = data.profiles[className .. "/" .. spec]
    if not profile then return nil end
    level = phase == "LEVELING" and level or 60
    local livePhase = addon:GetAvailabilityPhaseIndex(phase)
    if self.snapshot ~= owned or self.contextData ~= data then
        self.snapshot, self.contextData, self.contexts = owned, data, {}
        self.inventory = nil
    end
    self.contexts = self.contexts or {}
    local race = addon:GetPlayerRaceName()
    local faction = addon.GetPlayerFactionName and addon:GetPlayerFactionName()
    local scenario = self:GetScenario(className, spec, phase, level, requested)
    local key = table.concat({className, spec, phase, level, livePhase, race or "", faction or "", scenario}, "\031")
    if self.contexts[key] then return self.contexts[key] end
    if not self.inventory then self.inventory = resolveInventory(self, self:GetCatalog(data), owned) end
    local inventory = self.inventory
    local context = scoringContext(data, profile, className, spec, phase, level, livePhase, race, faction, scenario)
    context.owned, context.catalog, context.pending = owned, inventory.catalog, inventory.pending
    context.equipmentFacts, context.ownedFacts = inventory.equipment, inventory.byVariant
    context.storageCopies = inventory.bySource
    context.ownedCopies, context.unresolvedCopies, context.ownedLoadouts = inventory.copies, inventory.unresolvedCopies, {}
    self.contexts[key] = context
    return context
end

function rating:GetGuideContext(className, spec, phase, level, race, faction, requested)
    local data = model()
    local profile = data and data.profiles[className .. "/" .. spec]
    if not profile then return nil end
    level = phase == "LEVELING" and level or 60
    local phaseIndex = addon:GetAvailabilityPhaseIndex(phase)
    local scenario = self:GetScenario(className, spec, phase, level, requested)
    local key = table.concat({className, spec, phase, level, phaseIndex, race or "", faction or "", scenario}, "\031")
    if self.guideData ~= data then
        self.guideData, self.guideContexts = data, {}
    end
    for _, context in ipairs(self.guideContexts) do
        if context.key == key then return context end
    end
    local context = scoringContext(data, profile, className, spec, phase, level, phaseIndex, race, faction, scenario)
    context.key, context.catalog, context.guide = key, self:GetCatalog(data), true
    context.ownedFacts = {}
    self.guideContexts[#self.guideContexts + 1] = context
    if #self.guideContexts > 8 then table.remove(self.guideContexts, 1) end
    return context
end

local function fitsEquipment(context, item, slot)
    if item.slot ~= slot and not (item.slot == "One Hand" and (slot == "Main Hand" or slot == "Off Hand")) then return false end
    if not permitted(item.classes, context.class) or not permitted(item.races, context.race) then return false end
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
    if not stats then return nil end
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
        context.level, { live = live, race = context.race, faction = context.faction, scenario = context.scenario })
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
    local points, conditional = score(context, item, nil, nil, nil, slot)
    if points == nil and not status then
        status = item and (item.utility and "utility" or (next(item.effects or {}) and "effect")) or "unavailable"
    end
    return { item = item, score = points, status = status, spec = context.spec, level = context.level, phase = context.phase,
        scenario = context.scenario, slot = slot, conditional = conditional or (points == nil and hasUnscoredEffect(item)) }
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

local function inScope(context, item)
    local scoped = context.inScope[item.id]
    if scoped == nil then
        if context.guide and context.catalog.data.published_routes_only and addon.IsStatRankGuideItemAvailable then
            scoped = addon:IsStatRankGuideItemAvailable(item.id, context)
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

local function slotPool(context, physical, slot, handType, gear, cacheKey)
    if context.pools[cacheKey] then return context.pools[cacheKey] end
    local equipped = gear[physical]
    local reference = equipped and equipped.facts
    local candidates, rows = {}, {}
    local verified = context.catalog.data.published_routes_only and addon.IsStatRankGuideItemAvailable
    context.verifiedPeers = context.verifiedPeers or {}
    local function add(item, ownership)
        if handType and offHandType(item) ~= handType then return end
        if not usable(context, item, slot) or not legalSwap(context, item, physical, slot, gear)
            or not inScope(context, item) then return end
        if verified and not context.guide then
            local available = context.verifiedPeers[item.id]
            if available == nil then
                available = addon:IsStatRankGuideItemAvailable(item.id, context)
                context.verifiedPeers[item.id] = available
            end
            if not available then return end
        end
        local entry = resultFor(context, item, nil, slot)
        entry.setup_rank = not context.guide or nil
        entry.ownership = ownership
        candidates[item.key] = entry
    end
    for _, item in ipairs(context.catalog.slots[slot] or {}) do add(item) end
    if slot == "Main Hand" or slot == "Off Hand" then
        for _, item in ipairs(context.catalog.slots["One Hand"] or {}) do add(item) end
    end
    for key, ownership in pairs(context.ownedFacts) do
        if candidates[key] then candidates[key].ownership = ownership end
    end
    for _, entry in pairs(candidates) do rows[#rows + 1] = entry end
    table.sort(rows, function(a, b)
        if a.score ~= b.score then return (a.score or -math.huge) > (b.score or -math.huge) end
        if a.item.name ~= b.item.name then return a.item.name < b.item.name end
        return a.item.key < b.item.key
    end)
    local count, previous, rank = 0, nil, nil
    local ties, conditionalTies = {}, {}
    for _, entry in ipairs(rows) do
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
        if entry.rank then
            entry.total = count
            entry.tied = ties[entry.rank] > 1 or nil
            entry.conditional_tie = entry.tied and conditionalTies[entry.rank] or nil
            if count > 1 and bestScore > 0 then setRankTier(entry, bestScore, tiers) end
        end
    end
    local pool = { rows = rows, slot = slot, byVariant = candidates, count = count, bestScore = bestScore,
        scope = { context = context, key = cacheKey, physical = physical, slot = slot, handType = handType, gear = gear } }
    if equipped then
        local placement = resultFor(context, reference, equipped.status, slot)
        if placement.score ~= nil and reference then placement = rating:ProjectPlacement(reference, placement, pool) end
        pool.reference = placement
    end
    context.pools[cacheKey] = pool
    return pool
end

function rating:GetPlacement(context, physical, slots)
    if not context then return nil end
    local slot, handType = currentComparisonSlot(context, physical, slots)
    return slotPool(context, physical, slot, handType, context.equipmentFacts, physical)
end

function rating:GetComparisonCandidates(pool)
    local context, scope = pool.scope.context, pool.scope
    local rows, projected = {}, {}
    for _, entry in ipairs(pool.rows) do rows[#rows + 1] = entry end
    local function add(item, ownership)
        if not pool.byVariant[item.key] and not projected[item.key]
            and (not scope.handType or offHandType(item) == scope.handType)
            and usable(context, item, scope.slot) and legalSwap(context, item, scope.physical, scope.slot, scope.gear)
            and inScope(context, item) then
            local placement = pool.reference and pool.reference.item == item and pool.reference
                or resultFor(context, item, nil, scope.slot)
            placement.ownership = ownership
            if placement.score ~= nil then self:ProjectPlacement(item, placement, pool) end
            rows[#rows + 1] = placement
            projected[item.key] = true
        end
    end
    for _, ownership in pairs(context.ownedFacts) do add(ownership.facts, ownership) end
    if context.catalog.data.published_routes_only then
        for _, item in ipairs(context.catalog.slots[scope.slot] or {}) do add(item) end
        if scope.slot == "Main Hand" or scope.slot == "Off Hand" then
            for _, item in ipairs(context.catalog.slots["One Hand"] or {}) do add(item) end
        end
    end
    return rows
end

function rating:GetGuidePlacement(context, slot)
    return slotPool(context, slot, slot, nil, {}, slot)
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
    return { name = linkName or instance.facts.name, slot = slotLabel, state = instance.state }
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
            context.level, { live = scope.live, race = context.race, scenario = context.scenario })
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

function rating:GetGuideSwap(context, item, physical, slot, link, includeBreakdown)
    if not context or not item then return nil end
    return wornSwap(context, groupFor(item), item, link, nil, { physical = physical, slot = slot, breakdown = includeBreakdown })
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
        context.race, context.faction, context.scenario)
    local pool = rating:GetGuidePlacement(reference, slot)
    local known = pool.byVariant[item.key]
    if known then return known, pool.scope end
    local placement = resultFor(context, item, nil, slot)
    if placement.score == nil then return placement end
    return rating:ProjectPlacement(item, placement, pool), pool.scope
end

local function lookaheadPlacement(context, item, requestedScenario)
    local cap = addon.maxLevelingLevel + 1
    if item.level > cap then return { status = "out_of_scope", phase = "PR" } end
    if item.excluded or item.has_random_stats or not permitted(item.classes, context.class)
        or not permitted(item.races, context.race) then return { status = "incompatible" } end

    local group = groupFor(item)
    -- Proficiency can unlock after the item's required level.
    for level = math.max(item.level, context.level + 1), cap do
        local phase = level == cap and "PR" or "LEVELING"
        local scenario = rating:GetScenario(context.class, context.spec, phase, level,
            requestedScenario or (phase == context.phase and context.scenario or nil))
        local preview = context.tooltipLookahead
        if not preview or preview.level ~= level or preview.scenario ~= scenario then
            preview = contextAtLevel(context, phase, level, scenario)
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

local function placementAtLevel(scope, item, level)
    local context = contextAtLevel(scope.context, "LEVELING", level)
    -- Keep the anchor's physical slot and the other pieces in its comparison setup.
    local slot, physical, gear = scope.slot, scope.physical, scope.gear
    if context.scenario ~= scope.context.scenario or not usable(context, item, slot) or not legalSwap(context, item, physical, slot, gear)
        or not inScope(context, item) then return nil end
    local pool = slotPool(context, physical, slot, scope.handType, gear, scope.key)
    local placement = pool.byVariant[item.key]
    if not placement and not context.guide then
        placement = resultFor(context, item, nil, slot)
        if placement.score ~= nil then placement = rating:ProjectPlacement(item, placement, pool) end
    end
    return placement, pool.rows[1]
end

local function currentTierScope(context)
    return context.catalog.data == model() and context.phaseIndex == addon:GetAvailabilityPhaseIndex(context.phase)
end

local function nextTierRequest(queue)
    while queue[1] do
        local job = table.remove(queue, 1)
        if currentTierScope(job.scope.context) then
            for owner, watcher in pairs(job.watchers) do
                if not watcher.isCurrent() then job.watchers[owner] = nil end
            end
            if next(job.watchers) then return job end
        end
        job.cache.pending[job.key] = nil
    end
end

local function scheduleTierRanges(self)
    local queue = self.tierRangeQueue
    if self.tierRangeScheduled or not queue[1] then return end
    self.tierRangeScheduled = true
    C_Timer.After(0, function()
        self.tierRangeScheduled = nil
        local job = nextTierRequest(queue)
        if not job then return end
        local nextLevel = job.nextLevel
        job.nextLevel = nextLevel + 1
        local placement, leader = placementAtLevel(job.scope, job.item, nextLevel)
        if job.sameTier then
            job.sameTier = placement and placement.tier and placement.tier.quality == job.quality
            if job.sameTier then job.lastLevel = nextLevel end
        end
        if job.seekLeader and placement and placement.rank and placement.rank > 1 then
            job.stronger = { level = nextLevel, name = leader.item.name, conditional = leader.conditional or placement.conditional }
            job.seekLeader = nil
        end
        if not placement or (not job.sameTier and not job.seekLeader) or nextLevel == addon.maxLevelingLevel then
            local cache = job.cache
            cache.pending[job.key] = nil
            if #cache.order == 64 then cache.results[table.remove(cache.order, 1)] = nil end
            cache.order[#cache.order + 1] = job.key
            local range = { firstLevel = job.firstLevel, lastLevel = job.lastLevel, stronger = job.stronger }
            cache.results[job.key] = range
            for _, watcher in pairs(job.watchers) do
                if watcher.isCurrent() then watcher.onReady() end
            end
        else
            queue[#queue + 1] = job
        end
        scheduleTierRanges(self)
    end)
end

function rating:RequestTierRange(placement, scope, watcher)
    if not scope or not placement or not (placement.tier or placement.rank == 1) or placement.phase ~= "LEVELING"
        or not currentTierScope(scope.context) then return nil end
    local level = placement.level
    if level > addon.maxLevelingLevel then return nil end
    if level == addon.maxLevelingLevel then return { firstLevel = level, lastLevel = level } end

    local context = scope.context
    local cache = context.tierRanges
    if not cache then
        cache = { pending = {}, results = {}, order = {} }
        context.tierRanges = cache
    end
    local quality = placement.tier and placement.tier.quality
    local key = table.concat({ level, scope.key, placement.item.key, quality or "" }, "\031")
    if cache.results[key] then return cache.results[key] end
    if not (watcher and C_Timer and C_Timer.After) then return nil end

    local job = cache.pending[key]
    if not job then
        job = { cache = cache, key = key, scope = scope, item = placement.item, quality = quality,
            firstLevel = level, lastLevel = level, nextLevel = level + 1, sameTier = quality ~= nil,
            seekLeader = placement.rank == 1 and not placement.projected, watchers = {} }
        cache.pending[key] = job
        self.tierRangeQueue = self.tierRangeQueue or {}
        table.insert(self.tierRangeQueue, job)
    end
    job.watchers[watcher.owner] = watcher
    scheduleTierRanges(self)
    return nil, true
end

function rating:TierRangeLabel(range)
    local first, last = range.firstLevel, range.lastLevel
    return "Lv " .. first .. (last > first and ("–" .. last) or "")
end

local EMPTY_CHOICE = { score = 0, order = math.huge }
local EMPTY_CHOICES = { EMPTY_CHOICE }

local function ownedOption(context, outside, definition, instance)
    local item = instance.facts
    local slot = targetSlot(item, definition)
    if not slot or not usable(context, item, slot) then return nil end
    local capacity = swapCapacity(item, definition.key, slot, outside)
    if capacity < 1 then return nil end
    local stats, uncertain = swapStats(item, instance.item_link)
    local points, conditional = score(context, item, nil, nil, stats, slot)
    return { instance = instance, slot = slot, score = points, capacity = capacity,
        conditional = uncertain or conditional or (conditional == nil and hasUnscoredEffect(item)) }
end

local function compatiblePair(first, second)
    if not first.instance or not second.instance then return true end
    if first.slot == "Two Hand" or first.instance == second.instance then return false end
    return not sharesUniqueLimit(first.instance.facts, second.instance.facts)
        or (first.capacity >= 2 and second.capacity >= 2)
end

local function canImprove(score, best, prefer)
    return not best or score > best.score or (prefer and score == best.score)
end

local function bestLoadout(firstChoices, secondChoices, value, prefer)
    local best
    for _, first in ipairs(firstChoices) do
        if not value and not canImprove(first.score + secondChoices[1].score, best, prefer) then break end
        for _, second in ipairs(secondChoices) do
            local total = first.score + second.score
            if not value and not canImprove(total, best, prefer) then break end
            if compatiblePair(first, second) then
                local conditional
                if value then total, conditional = value(first, second) end
                local preference = prefer and ((first.preference or 0) + (second.preference or 0))
                if not best or total > best.score or (preference and total == best.score and preference > best.preference) then
                    best = { first, second, score = total, conditional = conditional, preference = preference }
                end
                if not value and not prefer then break end
            end
        end
    end
    return best
end

-- A group has at most two slots, so one copy in a higher priority wins a tie
-- against two lower-priority copies. Keeping an equipped copy in place wins first.
local STORAGE_PREFERENCE = { equipped = 9, bag = 3, bank = 1 }

local function ownedLoadout(context, group, storage)
    local key = storage and ("storage:" .. group.key) or group.key
    local revision = storage and addon.ForeverScoring and addon.ForeverScoring.revision
    local cached = context.ownedLoadouts[key]
    if cached and cached.revision == revision then return cached end
    local outside = copy(context.equipmentFacts)
    local options = {}
    local unresolved = context.owned.bagsIncomplete and "unavailable" or nil
    local function markUnresolved(status)
        if status == "loading" or not unresolved then unresolved = status or "unavailable" end
    end
    for _, definition in ipairs(group.definitions) do outside[definition.key] = nil end
    for index, definition in ipairs(group.definitions) do
        local choices = {}
        for order, instance in ipairs(context.ownedCopies) do
            local option = ownedOption(context, outside, definition, instance)
            if option and (not storage or inScope(context, instance.facts)) then
                if storage then
                    option.preference = instance == context.equipmentFacts[definition.key] and 27 or STORAGE_PREFERENCE[instance.state]
                end
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
            local item = copy.item
            local slot = item and targetSlot(item, definition)
            if not item or (slot and not item.excluded and (not item.level or item.level <= context.level)
                and fitsEquipment(context, item, slot)) then
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
        table.sort(choices, function(a, b)
            if a.score ~= b.score then return a.score > b.score end
            local first, second = a.preference or 0, b.preference or 0
            if first ~= second then return first > second end
            return a.order < b.order
        end)
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
        baseline = bestLoadout(options[1], options[2], value, storage), storage = storage }
    context.ownedLoadouts[key] = state
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
                    table.sort(complementary, function(a, b)
                        if a.score == b.score then return a.order < b.order end
                        return a.score > b.score
                    end)
                end
            end
            local first = index == 1 and { option } or complementary
            local second = index == 2 and { option } or complementary
            local proposal = bestLoadout(first, second, state.value, state.storage)
            if proposal and (not best or proposal.score > best.score
                or (state.storage and proposal.score == best.score and proposal.preference > best.preference)) then
                best, chosen, chosenIndex = proposal, option, index
            end
        end
    end
    return best, chosen, chosenIndex
end

local function ownedSwap(context, group, candidate, extraCopy, quantity)
    local state = ownedLoadout(context, group)
    local instance = candidate
    if not extraCopy then
        for _, owned in ipairs(context.ownedCopies) do
            if owned.facts.key == candidate.key
                and rating:SameExactItemLink(candidate.entry.item_id, owned.item_link, candidate.item_link) then
                instance = owned
                break
            end
        end
    end
    local best, chosen, chosenIndex = ownedProposal(context, group, state, instance, extraCopy and quantity)
    if not best then return nil end

    local other = best[3 - chosenIndex].instance
    local gear = copy(state.outside)
    local result = { definition = group.definitions[chosenIndex], slot = chosen.slot, gear = gear, replacements = {},
        delta = chosen.hasPoints and best.score - state.baseline.score, basis = context.activeBuild and "active" or "reference",
        conditional = best.conditional or state.baseline.conditional }
    for index, definition in ipairs(group.definitions) do
        local proposed = best[index].instance
        gear[definition.key] = proposed
        local previous = state.baseline[index].instance
        if not state.value then
            result.conditional = result.conditional or state.baseline[index].conditional or best[index].conditional
        end
        if (previous and previous.state == "bank") or (other and other.state == "bank") then result.bank = true end
        if previous and previous ~= best[1].instance and previous ~= best[2].instance then
            result.replacements[#result.replacements + 1] = referenceItem(previous, definition.label)
        end
        if previous == instance and result.delta == 0 then result.status = "best_owned" end
    end
    result.roleDelta, result.roleDisplaced = result.delta, 0
    if context.activeBuild and addon.ForeverScoring:HasUnmodeledSwap(context.activeBuild, candidate.facts,
        result.definition.inventorySlotId, result.slot) then result.conditional = true end
    if state.unresolved then
        result.delta, result.status = nil, state.unresolved
    elseif candidate.facts.unique_group and next(context.owned.unreadableEquipmentSlots or {}) then
        result.delta, result.status = nil, "unavailable"
    elseif not result.status and not result.replacements[1] then
        result.status = "empty"
    end
    return result
end

local function previewTooltipItem(context, candidate, extraCopy, options)
    local item = candidate.facts
    local placement, scope, preview = lookaheadPlacement(context.forecastBaseline or context, item, options.futureScenario)
    local result = { placement = placement, rankScope = scope, preview = true }
    if preview then
        local comparison = ownedSwap(preview, groupFor(item), candidate, extraCopy, options.quantity)
        result.forecast = comparison or { status = "blocked" }
        result.forecast.level, result.forecast.phase, result.forecast.scenario = preview.level, preview.phase, preview.scenario
    end
    return result
end

local function assessTooltipItem(context, candidate, useWorn, wornSlot, extraCopy, scope)
    local item = candidate.facts
    if not item.level then return { placement = { status = candidate.status or "unavailable" } } end
    if item.level > context.level then
        if scope.lookahead then return previewTooltipItem(context, candidate, extraCopy, scope) end
        return { placement = { status = "level" } }
    end
    if not inScope(context, item) then return { placement = { status = "out_of_scope", phase = context.phase } } end
    local group = groupFor(item)
    local slot = firstUsableSlot(context, group, item)
    if not slot then
        if scope.lookahead and context.leveling then
            return previewTooltipItem(context, candidate, extraCopy, scope)
        end
        return { placement = { status = "incompatible" } }
    end
    local result
    if useWorn then
        result = wornSwap(context, group, item, candidate.item_link, wornSlot, scope)
    else
        local build, missing = rating:WithCharacterBuild(context, scope.live)
        result = ownedSwap(build, group, candidate, extraCopy, scope.quantity)
        if result and missing then result.conditional = true end
    end
    if not result then
        if scope.skipPlacement then return { placement = { status = "blocked" } } end
        local placement, rankScope = referencePlacement(context, item, slot)
        return { placement = placement, rankScope = rankScope, status = "blocked" }
    end
    if scope.skipPlacement then
        result.placement = resultFor(context, item, nil, result.slot)
    else
        result.placement, result.rankScope = referencePlacement(context, item, result.slot)
    end
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
    local history = addon:GetRecommendationHistory(id, context.class, context.spec, context.phase, slot)
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
        and last.quantity == scope.quantity and last.futureScenario == scope.futureScenario
        and (last.lookahead == scope.lookahead or last.result.slot) then
        return last.result
    end
    local result = assessTooltipItem(context, candidate, useWorn, wornSlot, extraCopy, scope)
    local owned = context.ownedFacts[candidate.key]
    result.ownership = owned and owned.state
    result.bis = approvedBiS(context, candidate, result.slot)
    context.lastTooltip = { candidate = candidate, useWorn = useWorn, wornSlot = wornSlot, extraCopy = extraCopy,
        result = result, revision = revision, live = scope.live, physical = scope.physical, slot = scope.slot,
        lookahead = scope.lookahead, skipPlacement = scope.skipPlacement, quantity = scope.quantity, futureScenario = scope.futureScenario }
    return result
end

local function groupHas(choices, instance)
    return choices[1].instance == instance or choices[2].instance == instance
end

local function groupGear(group, state, choices)
    local gear = copy(state.outside)
    for index, definition in ipairs(group.definitions) do gear[definition.key] = choices[index].instance end
    return gear
end

local function storageSwap(context, group, state, before, after)
    local previous, proposed = groupGear(group, state, before), groupGear(group, state, after)
    local oldValue, oldUncertain = rating:ReferenceLoadout(context, previous)
    local newValue, newUncertain = rating:ReferenceLoadout(context, proposed)
    if oldValue == nil or newValue == nil then return { conditional = true } end
    local retained = copy(previous)
    local result = { delta = newValue - oldValue, replacements = {}, incoming = {}, gear = proposed,
        basis = context.activeBuild and "active" or "reference" }
    for index, definition in ipairs(group.definitions) do
        local old, new = before[index].instance, after[index].instance
        if old and not groupHas(after, old) then
            retained[definition.key] = nil
            result.replacements[#result.replacements + 1] = referenceItem(old, definition.label)
        end
        if new and not groupHas(before, new) then
            result.incoming[#result.incoming + 1] = referenceItem(new, definition.label)
        end
        if old ~= new or group.weapons then
            local id = definition.inventorySlotId
            result.conditional = result.conditional or oldUncertain[id] or newUncertain[id]
            if new and context.activeBuild then
                result.conditional = result.conditional or addon.ForeverScoring:HasUnmodeledSwap(
                    context.activeBuild, new.facts, id, after[index].slot)
            end
        end
    end
    local oldRole = rating:ReferenceLoadout(context, previous, true)
    result.roleDelta = rating:ReferenceLoadout(context, proposed, true) - oldRole
    result.roleDisplaced = math.max(0, oldRole - rating:ReferenceLoadout(context, retained, true))
    if #result.replacements == 0 then result.status = "empty" end
    return result
end

local function getStorageActions(context, group, state)
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
        local proposal = independent and (index == 1 and first or second) or best
        actions[best[index].instance] = { index = index, swap = storageSwap(context, group, state, worn, proposal) }
    end
    state.actions = actions
    return actions
end

local function alternateGain(context, group, state, primary)
    if state.alternate and state.alternate.primary == primary then return state.alternate end
    local preferred, missing = rating:WithCharacterBuild(primary, true)
    local first = ownedLoadout(preferred, group, true)
    local alternate = { primary = primary, first = first.baseline, ready = not missing and not first.unresolved }
    if alternate.ready then
        alternate.meaningful = rating:IsMeaningfulOwnedUpgrade(storageSwap(context, group, state, first.baseline, state.baseline))
    end
    state.alternate = alternate
    return alternate
end

local function storageComparison(context, group, state, instance, candidate, result, rankContext)
    local action = getStorageActions(context, group, state)[instance]
    if action and action.swap.delta then
        local swap, index = copy(action.swap), action.index
        swap.definition, swap.slot = group.definitions[index], state.baseline[index].slot
        swap.placement, swap.rankScope = referencePlacement(rankContext, candidate.facts, swap.slot)
        swap.ownership = instance.state
        swap.bis = approvedBiS(context, candidate, swap.slot)
        swap.effectNote = result.effectNote
        result = swap
    end
    local comparison = { result = result, winner = groupHas(state.baseline, instance) }
    if comparison.winner then
        comparison.qualifies = action ~= nil and rating:IsMeaningfulOwnedUpgrade(action.swap)
    else
        local proposal = ownedProposal(context, group, state, instance)
        if proposal then
            local gap = storageSwap(context, group, state, proposal, state.baseline)
            if not gap.conditional then
                comparison.stronger = gap.incoming
                comparison.sidegrade = not rating:IsMeaningfulOwnedUpgrade(gap)
            end
        end
    end
    return comparison
end

function rating:GetStorageComparison(context, candidate, sourceId, guid, primary)
    local instance = context.storageCopies[sourceId]
    if not instance or (guid and instance.entry.guid and instance.entry.guid ~= guid)
        or not self:SameExactItemLink(candidate.entry.item_id, instance.item_link, candidate.item_link) then
        return nil, false
    end
    local group = groupFor(candidate.facts)
    if #group.definitions == 0 then return nil, true end
    local build, missing = self:WithCharacterBuild(context, true)
    local state = ownedLoadout(build, group, true)
    state.comparisons = state.comparisons or {}
    local comparison = state.comparisons[instance]
    if not comparison then
        local result = self:CompareTooltipItem(context, candidate, true, nil, false, { live = true, lookahead = true })
        if result.preview or not inScope(context, candidate.facts) then
            comparison = { result = result }
        elseif state.unresolved or missing then
            comparison = { result = result, unavailable = state.unresolved or missing }
        else
            comparison = storageComparison(build, group, state, instance, candidate, result, context)
        end
        state.comparisons[instance] = comparison
    end
    if primary and comparison.qualifies then
        local alternate = alternateGain(build, group, state, primary)
        comparison = copy(comparison)
        comparison.alternate = not groupHas(alternate.first, instance)
        comparison.qualifies = alternate.ready and (not comparison.alternate or alternate.meaningful)
    end
    return comparison, not comparison.unavailable
end

function rating:GetScenarioUpgrades(contexts, candidate, owned, scope)
    local upgrades = {}
    for _, context in ipairs(contexts) do
        local swap = self:CompareTooltipItem(context, candidate, owned, nil, not owned, scope)
        if not swap.conditional and (owned and self:IsMeaningfulOwnedUpgrade(swap)
            or not owned and (self:RoundedGain(swap.delta) or 0) > 0) then
            upgrades[#upgrades + 1] = { scenario = context.scenario, swap = swap }
        end
    end
    return upgrades
end

function rating:UpgradeScenarioSummary(upgrades)
    local labels = {}
    for _, upgrade in ipairs(upgrades or {}) do labels[#labels + 1] = self:ScenarioLabel(upgrade.scenario) end
    return table.concat(labels, " / ")
end

function rating:WithGuaranteedRewards(context, rewards)
    if #rewards == 0 then return context end
    local combined = copy(context)
    combined.forecastBaseline = context
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

function rating:IsMeaningfulOwnedUpgrade(result)
    if result.conditional or not result.delta or result.delta <= 0 or not result.roleDelta then return false end
    if result.status == "empty" then return self:RoundedGain(result.roleDelta) >= 0.1 end
    return result.roleDelta >= math.max(2, (result.roleDisplaced or 0) * 0.05)
end

function rating:GetSwapBasisLabel(basis)
    return basis == "active" and "Your setup" or "Default spec weights"
end

function rating:Label(entry, layout, showProjection)
    if not entry then return "Stats unavailable" end
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
    local scenario = entry.scenario ~= "pre_raid" and self:ScenarioLabel(entry.scenario)
    return entry.spec .. " · " .. self:ScopeLabel(entry) .. (scenario and (" · " .. scenario) or "")
end

function rating:DescriptionLines(entry)
    local lines = { self:Label(entry), self:ContextLabel(entry) }
    if entry.score_percent ~= nil then
        lines[3] = string.format("%d%% of the best known stat score", entry.score_percent)
    end
    if entry.placement_color then lines[#lines + 1] = "Color uses placement in this slot" end
    if entry.setup_rank then lines[#lines + 1] = "Rank in this equipped setup" end
    if entry.projected then lines[#lines + 1] = "Projected placement among known gear" end
    if entry.conditional or entry.conditional_tie then lines[#lines + 1] = "Some item effects have an unverified value" end
    return lines
end
