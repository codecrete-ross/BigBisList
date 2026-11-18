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
    for index = 2, math.min(6, #fields) do fields[index] = "0" end
    local suffix = tonumber(fields[7]) or 0
    local extended = {}
    for index = 11, #fields do extended[#extended + 1] = fields[index] end
    while extended[#extended] == "0" or extended[#extended] == "" do table.remove(extended) end
    local key = tostring(id)
    if suffix ~= 0 then key = key .. ":" .. suffix end
    if #extended > 0 or (suffix ~= 0 and (tonumber(fields[8]) or 0) ~= 0) then
        key = key .. ":" .. (suffix ~= 0 and (fields[8] or "0") or "0") .. ":" .. table.concat(extended, ":")
    end
    return key, link:sub(1, first - 1) .. "item:" .. table.concat(fields, ":") .. link:sub(last + 1)
end

function rating:GetCatalog(data)
    if self.catalog and self.catalog.data == data then return self.catalog end
    local catalog = { data = data, items = {}, slots = {} }
    for key, row in pairs(data.items) do
        local item = { key = key }
        for index, field in ipairs(data.item_fields) do item[field] = row[index] end
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

local function readTooltip(link, stats, facts)
    local tooltip = call(C_TooltipInfo and C_TooltipInfo.GetHyperlink, link)
    if not readable(tooltip) or type(tooltip) ~= "table" or not readable(tooltip.lines) or type(tooltip.lines) ~= "table" then return end
    local locale = GetLocale and GetLocale()
    local english = locale == nil or locale == "enUS" or locale == "enGB"
    local spellPower, seenSpellPower = 0, {}
    for _, line in ipairs(tooltip.lines or {}) do
        if readable(line) and type(line) == "table" then
            for _, field in ipairs({ "leftText", "rightText" }) do
                local text = line[field]
                if readable(text) and type(text) == "string" and english then
                    text = text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
                    local dps = tonumber(text:match("^%(([%d.]+) damage per second%)$"))
                    local speed = tonumber(text:match("^Speed%s+([%d.]+)$"))
                    local armor = tonumber(text:match("^(%d+) Armor$"))
                    if dps and stats.dps == nil then stats.dps = dps end
                    if speed then stats.weapon_speed = speed end
                    if armor and stats.armor == nil then stats.armor = armor end
                    local classes, races = text:match("^Classes:%s*(.+)$"), text:match("^Races:%s*(.+)$")
                    if classes then facts.classes = restrictionNames(classes) end
                    if races then facts.races = restrictionNames(races) end
                    if text:match("^Use:") or text:match("^Chance on hit:") or text:match("^Equip:") then
                        local stat, amount
                        local label, number = text:match("^Equip: Improves your chance to (.+) by ([%d.]+)%%%.?$")
                        if label then
                            stat = ({ hit = "hit_percent", dodge = "dodge_percent", parry = "parry_percent",
                                block = "block_percent", ["get a critical strike"] = "crit_percent" })[label]
                            amount = tonumber(number)
                        end
                        local passive = tonumber(text:match("^Equip: Increases damage and healing done by magical spells and effects by up to (%d+)%s*%.?$")
                            or text:match("^Equip: Increases spell power by (%d+)%s*%.?$"))
                        if passive then
                            if not seenSpellPower[text] then
                                spellPower = spellPower + passive
                                seenSpellPower[text] = true
                            end
                        elseif stat and finite(amount) then stats[stat] = (stats[stat] or 0) + amount
                        else addEffect(facts.effects, text) end
                    end
                end
            end
        end
    end
    if spellPower > 0 and stats.spell_power == nil and stats.spell_damage == nil then
        stats.spell_power = spellPower
    end
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
    readTooltip(link, stats, facts)
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
    if next(stats) or #facts.effects > 0 then
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
end

local function resolveLink(self, context, entry)
    if not entry or not entry.item_id then return nil end
    local id, link = entry.item_id, entry.item_link
    local key, statLink = self:NormalizeLink(id, link)
    local base = context.catalog.items[tostring(id)]
    local facts = key and context.catalog.items[key] or (not link and base)
    if facts and facts.has_random_stats then facts = nil end
    local unavailable
    if not facts and statLink then facts, unavailable = self:ReadNative(id, key, statLink, base) end
    if unavailable == "loading" then context.pending[id] = true end
    if not facts then return nil, unavailable end
    return facts
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
    local inventory = { catalog = catalog, pending = {}, equipment = {}, byVariant = {}, copies = {}, unresolvedCopies = {} }
    local function read(entry, state)
        local facts, status = resolveLink(self, inventory, entry)
        local instance = { facts = facts, status = status, entry = entry, item_link = entry.item_link, state = state }
        if facts and instance.item_link then
            local other = inventory.byVariant[facts.key]
            if not other or (OWNED_ORDER[state] or 0) > (OWNED_ORDER[other.state] or 0) then
                inventory.byVariant[facts.key] = instance
            end
            inventory.copies[#inventory.copies + 1] = instance
        elseif state ~= "equipped" then
            local unresolved = unresolvedCopy(catalog, entry, status)
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

local function scoringContext(data, profile, className, spec, phase, level, phaseIndex, race, faction)
    local leveling = phase == "LEVELING"
    local policy = leveling and profile.leveling or profile.pre_raid
    local weights = policy.weights
    if leveling then
        for _, band in ipairs(policy.weights) do
            if level >= band[1] and level <= band[2] then weights = band[3]; break end
        end
    end
    return {
        class = className, spec = spec, phase = phase, level = level, race = race, faction = faction,
        leveling = leveling, policy = policy, weights = weights, equipment = data.equipment[className], role = profile.role,
        commonSlots = data.common_slots, feralPolicy = profile.leveling, feralDps = data.feral_uses_weapon_dps,
        phaseIndex = phaseIndex, inScope = {}, pools = {},
    }
end

function rating:GetContext(className, spec, phase, level, owned)
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
    local key = table.concat({className, spec, phase, level, livePhase, race or ""}, "\031")
    if self.contexts[key] then return self.contexts[key] end
    if not self.inventory then self.inventory = resolveInventory(self, self:GetCatalog(data), owned) end
    local inventory = self.inventory
    local context = scoringContext(data, profile, className, spec, phase, level, livePhase, race)
    context.owned, context.catalog, context.pending = owned, inventory.catalog, inventory.pending
    context.equipmentFacts, context.ownedFacts = inventory.equipment, inventory.byVariant
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
    if self.guideData ~= data then
        self.guideData, self.guideContexts = data, {}
    end
    for _, context in ipairs(self.guideContexts) do
        if context.key == key then return context end
    end
    local context = scoringContext(data, profile, className, spec, phase, level, phaseIndex, race, faction)
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

local function score(context, item, roleOnly)
    if not item or not next(item.stats) then return nil end
    local weights, feral = context.weights, context.feralPolicy
    local ignoreDps = not context.feralDps and feral.weapon_style == "feral"
        and feral.form_level and context.level >= feral.form_level
    local ignoreDefense = roleOnly and not (context.role == "tank" or context.spec == "Protection" or context.spec == "Feral tank")
    local total = 0
    for stat, value in pairs(item.stats) do
        if not (ignoreDps and stat == "dps") and not (ignoreDefense and DEFENSIVE_STATS[stat]) then
            total = total + value * (weights[stat] or 0)
        end
    end
    return math.floor(total * 10000 + 0.5) / 10000
end

local function resultFor(context, item, status)
    local points = score(context, item)
    if points == nil and not status then
        status = item and (item.utility and "utility" or (next(item.effects or {}) and "effect")) or "unavailable"
    end
    return { item = item, score = points, status = status, spec = context.spec, level = context.level, phase = context.phase }
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
        if context.guide then
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

local function slotPool(context, physical, slot, handType, gear, cacheKey)
    if context.pools[cacheKey] then return context.pools[cacheKey] end
    local equipped = gear[physical]
    local reference = equipped and equipped.facts
    local candidates, rows = {}, {}
    local function add(item, ownership)
        if handType and offHandType(item) ~= handType then return end
        if not usable(context, item, slot) or not legalSwap(context, item, physical, slot, gear)
            or not inScope(context, item) then return end
        local entry = resultFor(context, item)
        entry.ownership = ownership
        candidates[item.key] = entry
    end
    for _, item in ipairs(context.catalog.slots[slot] or {}) do add(item) end
    if slot == "Main Hand" or slot == "Off Hand" then
        for _, item in ipairs(context.catalog.slots["One Hand"] or {}) do add(item) end
    end
    for _, ownership in pairs(context.ownedFacts) do add(ownership.facts, ownership) end
    for _, entry in pairs(candidates) do rows[#rows + 1] = entry end
    table.sort(rows, function(a, b)
        if a.score ~= b.score then return (a.score or -math.huge) > (b.score or -math.huge) end
        if a.item.name ~= b.item.name then return a.item.name < b.item.name end
        return a.item.key < b.item.key
    end)
    local count, previous, rank = 0, nil, nil
    for _, entry in ipairs(rows) do
        if entry.score ~= nil then
            count = count + 1
            if entry.score ~= previous then previous, rank = entry.score, count end
            entry.rank = rank
        end
    end
    local bestScore = rows[1] and rows[1].score
    local tiers = placementTiers(rows, count, bestScore)
    for _, entry in ipairs(rows) do
        if entry.rank then
            entry.total = count
            if count > 1 and bestScore > 0 then setRankTier(entry, bestScore, tiers) end
        end
    end
    local placement = reference and candidates[reference.key]
        or (equipped and resultFor(context, reference, equipped.status))
    local pool = {rows = rows, reference = placement, slot = slot, byVariant = candidates, count = count, bestScore = bestScore}
    context.pools[cacheKey] = pool
    return pool
end

function rating:GetPlacement(context, physical, slots)
    if not context then return nil end
    local slot, handType = currentComparisonSlot(context, physical, slots)
    return slotPool(context, physical, slot, handType, context.equipmentFacts, physical)
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
    local remaining, outfit, best = {}, {}, 0
    remaining[#positions + 1] = 0
    for index = #positions, 1, -1 do
        remaining[index] = remaining[index + 1] + positions[index].choices[1].score
    end
    local function search(index, total)
        if total + remaining[index] <= best then return end
        local position = positions[index]
        if not position then best = total; return end
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
    return best
end

function rating:GetGearScore(context, definitions)
    if context.gearScore then return context.gearScore end
    local gear = context.equipmentFacts
    local unreadableSlots = context.owned.unreadableEquipmentSlots or {}
    local twoHand = hasTwoHander(context, gear) or (not gear.MainHand and not gear.OffHand
        and (context.policy.weapon_style == "two_hand"
            or (not contains(context.policy.slots, "Main Hand") and contains(context.policy.slots, "Two Hand"))))
    local positions, current, partial = {}, 0, 0
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
            local points = item and score(context, item)
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
            end
        end
    end
    local best = bestKnownOutfit(context, positions)
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
    if status == "loading" or (facts and (not facts.native or next(facts.stats) or #facts.effects > 0)) then
        self.tooltipItem = candidate
    else
        self.tooltipItem = nil
    end
    return candidate
end

function rating:IsUnresolvedVariant(itemId, key)
    local base = self.catalog and self.catalog.items[tostring(itemId)]
    return base and base.has_random_stats and key == tostring(itemId)
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
    local points = equipped.item_link and score(context, equipped.facts)
    if points == nil then
        result.delta = nil
        result.status = equipped.status == "loading" and "loading" or "unavailable"
        return
    end
    result.replacements[#result.replacements + 1] = referenceItem(equipped, label)
    if result.delta ~= nil then result.delta = result.delta - points end
    result.roleDisplaced = result.roleDisplaced + (score(context, equipped.facts, true) or 0)
end

local function wornSwap(context, group, item, points, wornSlot, physical)
    local gear = context.equipmentFacts
    local unreadableSlots = context.owned.unreadableEquipmentSlots or {}
    local best
    for _, definition in ipairs(group.definitions) do
        local slot = targetSlot(item, definition)
        local key = definition.key
        if (not physical or physical == key) and slot and usable(context, item, slot) and legalSwap(context, item, key, slot, gear) then
            local result = { definition = definition, slot = slot, gear = gear, delta = points, replacements = {},
                roleDisplaced = 0 }
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
            if result.delta ~= nil then result.roleDelta = score(context, item, true) - result.roleDisplaced end
            if not best or (result.delta ~= nil and (best.delta == nil or result.delta > best.delta)) then best = result end
        end
    end
    return best
end

function rating:GetGuideSwap(context, item, physical)
    if not context or not item then return nil end
    return wornSwap(context, groupFor(item), item, score(context, item), nil, physical)
end

local function insertionRank(context, item, result, placement)
    if placement.score == nil then return placement end
    local physical = result.definition.key
    local slot, gear = result.slot, result.gear
    local handType = slot == "Off Hand" and offHandType(item)
    local cacheKey
    if gear == context.equipmentFacts then
        local currentSlot, currentType = currentComparisonSlot(context, physical, result.definition.slots)
        if slot == currentSlot and handType == currentType then cacheKey = physical end
    end
    cacheKey = cacheKey or table.concat({
        result.poolKey or "worn", physical, slot, handType or "",
    }, "\031")
    local pool = slotPool(context, physical, slot, handType, gear, cacheKey)
    local known = pool.byVariant[item.key]
    if known then return known end
    local rank = 1
    for _, peer in ipairs(pool.rows) do
        if peer.score == nil or peer.score <= placement.score then break end
        rank = rank + 1
    end
    placement.rank, placement.total = rank, pool.count + 1
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

local EMPTY_CHOICE = { score = 0, order = math.huge }
local EMPTY_CHOICES = { EMPTY_CHOICE }

local function ownedOption(context, outside, definition, instance)
    local item = instance.facts
    local slot = targetSlot(item, definition)
    if not slot or not usable(context, item, slot) then return nil end
    local capacity = swapCapacity(item, definition.key, slot, outside)
    if capacity < 1 then return nil end
    return { instance = instance, slot = slot, score = score(context, item), capacity = capacity }
end

local function compatiblePair(first, second)
    if not first.instance or not second.instance then return true end
    if first.slot == "Two Hand" or first.instance == second.instance then return false end
    return not sharesUniqueLimit(first.instance.facts, second.instance.facts)
        or (first.capacity >= 2 and second.capacity >= 2)
end

local function bestLoadout(firstChoices, secondChoices)
    local best
    for _, first in ipairs(firstChoices) do
        if best and first.score + secondChoices[1].score <= best.score then break end
        for _, second in ipairs(secondChoices) do
            local total = first.score + second.score
            if best and total <= best.score then break end
            if compatiblePair(first, second) then
                best = { first, second, score = total }
                break
            end
        end
    end
    return best
end

local function ownedLoadout(context, group)
    local cached = context.ownedLoadouts[group.key]
    if cached then return cached end
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
            if option then
                if option.score ~= nil then
                    option.order = order
                    choices[#choices + 1] = option
                elseif not instance.facts.utility and not next(instance.facts.effects or {}) then
                    markUnresolved()
                end
            end
        end
        for _, copy in ipairs(context.unresolvedCopies) do
            local item = copy.item
            local slot = item and targetSlot(item, definition)
            if not item or (slot and (not item.level or (not item.excluded and item.level <= context.level
                and fitsEquipment(context, item, slot)))) then
                markUnresolved(copy.status)
            end
        end
        local worn = context.equipmentFacts[definition.key]
        if context.owned.unreadableEquipmentSlots and context.owned.unreadableEquipmentSlots[definition.key] then
            markUnresolved()
        elseif worn and (not worn.item_link or not worn.facts) then
            markUnresolved(worn.status)
        end
        choices[#choices + 1] = EMPTY_CHOICE
        table.sort(choices, function(a, b)
            if a.score ~= b.score then return a.score > b.score end
            return a.order < b.order
        end)
        options[index] = choices
    end
    options[2] = options[2] or EMPTY_CHOICES
    local state = { outside = outside, options = options, unresolved = unresolved, baseline = bestLoadout(options[1], options[2]) }
    context.ownedLoadouts[group.key] = state
    return state
end

local function ownedSwap(context, group, candidate, extraCopy, points)
    local state = ownedLoadout(context, group)
    local instance = not extraCopy and context.ownedFacts[candidate.key] or candidate
    if not instance.item_link then instance = candidate end
    local best, chosen, chosenIndex
    for index, definition in ipairs(group.definitions) do
        local option = ownedOption(context, state.outside, definition, instance)
        if option then
            -- A reviewed effect-only item still needs a legal target slot.
            option.score = points or 0
            local first = index == 1 and { option } or state.options[1]
            local second = index == 2 and { option } or state.options[2]
            local proposal = bestLoadout(first, second)
            if proposal and (not best or proposal.score > best.score) then
                best, chosen, chosenIndex = proposal, option, index
            end
        end
    end
    if not best then return nil end

    local other = best[3 - chosenIndex].instance
    local gear = copy(state.outside)
    local result = { definition = group.definitions[chosenIndex], slot = chosen.slot, gear = gear,
        poolKey = "owned:" .. (other and other.facts.key or ""), replacements = {},
        delta = points and best.score - state.baseline.score }
    for index, definition in ipairs(group.definitions) do
        local proposed = best[index].instance
        gear[definition.key] = proposed
        local previous = state.baseline[index].instance
        if (previous and previous.state == "bank") or (other and other.state == "bank") then result.bank = true end
        if previous and previous ~= best[1].instance and previous ~= best[2].instance then
            result.replacements[#result.replacements + 1] = referenceItem(previous, definition.label)
        end
        if previous == instance and result.delta == 0 then result.status = "best_owned" end
    end
    if state.unresolved then
        result.delta, result.status = nil, state.unresolved
    elseif candidate.facts.unique_group and next(context.owned.unreadableEquipmentSlots or {}) then
        result.delta, result.status = nil, "unavailable"
    elseif not result.status and not result.replacements[1] then
        result.status = "empty"
    end
    return result
end

local function assessTooltipItem(context, candidate, useWorn, wornSlot, extraCopy)
    local item = candidate.facts
    if item.level and item.level > context.level then
        return { placement = { status = "level", requiredLevel = item.level } }
    end
    if not inScope(context, item) then return { placement = { status = "out_of_scope", phase = context.phase } } end
    local group = groupFor(item)
    local firstSlot
    for _, definition in ipairs(group.definitions) do
        local slot = targetSlot(item, definition)
        if slot and usable(context, item, slot) then firstSlot = firstSlot or slot end
    end
    if not firstSlot then return { placement = { status = "incompatible" } } end
    local placement = resultFor(context, item)

    local result
    if useWorn then
        result = wornSwap(context, group, item, placement.score, wornSlot)
    else
        result = ownedSwap(context, group, candidate, extraCopy, placement.score)
    end
    if not result then return { placement = { status = "blocked" } } end
    result.placement = insertionRank(context, item, result, placement)
    return result
end

function rating:CompareTooltipItem(context, candidate, useWorn, wornSlot, extraCopy)
    local last = context.lastTooltip
    if last and last.candidate == candidate and last.useWorn == useWorn and last.wornSlot == wornSlot
        and last.extraCopy == extraCopy then return last.result end
    local result = assessTooltipItem(context, candidate, useWorn, wornSlot, extraCopy)
    local owned = context.ownedFacts[candidate.key]
    result.ownership = owned and owned.state
    if result.slot and context.phase ~= "LEVELING" and addon.IsConfirmedGearBiS then
        local id = candidate.entry.item_id
        local history = addon:GetRecommendationHistory(id, context.class, context.spec, context.phase, result.slot)
        result.bis = addon:IsConfirmedGearBiS(history, context.phase, id, candidate.key)
    end
    context.lastTooltip = { candidate = candidate, useWorn = useWorn, wornSlot = wornSlot, extraCopy = extraCopy, result = result }
    return result
end

function rating:RoundedGain(delta)
    if not finite(delta) then return nil end
    local points = math.floor(math.abs(delta) * 10 + 0.5) / 10
    return delta < 0 and -points or points
end

function rating:IsMeaningfulOwnedUpgrade(result)
    if not result.delta or result.delta <= 0 or not result.roleDelta then return false end
    if result.status == "empty" then return self:RoundedGain(result.roleDelta) >= 0.1 end
    return result.roleDelta >= math.max(2, (result.roleDisplaced or 0) * 0.05)
end

function rating:Label(entry, layout)
    if not entry then return "Stats unavailable" end
    if entry.rank and entry.total > 1 then
        local label = entry.tier and entry.tier.label or "Rank"
        if layout == "compact" then return string.format("%s #%d/%d", label, entry.rank, entry.total) end
        local separator = layout == "stacked" and "\n" or " · "
        return string.format("%s%s#%d / %d", label, separator, entry.rank, entry.total)
    end
    if entry.score ~= nil then return string.format("%.1f pts", entry.score) end
    if entry.status == "level" then return "Requires level " .. entry.requiredLevel end
    if entry.status == "out_of_scope" then
        return entry.phase == "LEVELING" and "Outside Leveling rankings" or "Outside Pre-Raid rankings"
    end
    return STATUS_LABELS[entry.status] or STATUS_LABELS.unavailable
end

function rating:ContextLabel(entry)
    local scope = entry.phase == "LEVELING" and ("Level " .. entry.level) or addon:GetPhaseDisplayName(entry.phase)
    return entry.spec .. " · " .. scope
end

function rating:DescriptionLines(entry)
    local lines = { self:Label(entry), self:ContextLabel(entry) }
    if entry.score_percent ~= nil then
        lines[3] = string.format("%d%% of the best known stat score", entry.score_percent)
    end
    if entry.placement_color then lines[#lines + 1] = "Color uses placement in this slot" end
    return lines
end
