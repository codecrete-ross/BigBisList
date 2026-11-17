local BigBiSList = _G.BigBiSList
local Scoring = {}
BigBiSList.ForeverScoring = Scoring

local VERSION = "forever-character-scoring-1"
local SLOTS = {
    Head = {1}, Neck = {2}, Shoulder = {3}, Chest = {5}, Waist = {6},
    Legs = {7}, Feet = {8}, Wrist = {9}, Hands = {10}, Ring = {11, 12},
    Trinket = {13, 14}, Back = {15}, ["Main Hand"] = {16}, ["Two Hand"] = {16},
    ["Off Hand"] = {17}, Ranged = {18}, Idol = {18}, Libram = {18}, Totem = {18},
}
local LIVE_STATS = {
    ITEM_MOD_STRENGTH_SHORT = "strength", ITEM_MOD_AGILITY_SHORT = "agility",
    ITEM_MOD_STAMINA_SHORT = "stamina", ITEM_MOD_INTELLECT_SHORT = "intellect",
    ITEM_MOD_SPIRIT_SHORT = "spirit", ITEM_MOD_ATTACK_POWER_SHORT = "attack_power",
    ITEM_MOD_RANGED_ATTACK_POWER_SHORT = "ranged_attack_power", ITEM_MOD_SPELL_POWER_SHORT = "spell_power",
    ITEM_MOD_SPELL_DAMAGE_DONE_SHORT = "spell_damage", ITEM_MOD_SPELL_HEALING_DONE_SHORT = "healing_power",
    ITEM_MOD_MANA_REGENERATION_SHORT = "mp5", ITEM_MOD_ARMOR_SHORT = "armor", RESISTANCE0_NAME = "armor",
    ITEM_MOD_BLOCK_VALUE_SHORT = "block_value", ITEM_MOD_DEFENSE_SKILL_RATING_SHORT = "defense",
    ITEM_MOD_DAMAGE_PER_SECOND_SHORT = "dps",
}

local function readable(value)
    return not BigBiSList.IsReadableValue or BigBiSList.IsReadableValue(value)
end

local function contains(values, target)
    for _, value in ipairs(values or {}) do
        if value == target then return true end
    end
    return false
end

local function copy(values)
    local result = {}
    for key, value in pairs(values) do result[key] = value end
    return result
end

local function byId(values, identifier)
    return values and (values[identifier] or values[tostring(identifier)])
end

local function addStats(total, stats, multiplier)
    for key, value in pairs(stats or {}) do
        total[key] = (total[key] or 0) + value * (multiplier or 1)
    end
end

function Scoring.ScoreLoadout(loadout, weights, operations, ranks, scenario, raceId)
    local stats, sets, explanations = {}, {}, {}
    local shield = false
    for _, item in pairs(loadout) do
        addStats(stats, item.stats)
        shield = shield or item.shield
        if item.set_id then sets[item.set_id] = (sets[item.set_id] or 0) + 1 end
        for _, proc in ipairs(item.procs or {}) do
            local events = (scenario.events_per_minute or {})[proc.trigger] or 0
            local rate = math.min(events * proc.chance, proc.max_per_minute or events)
            addStats(stats, proc.stats, math.min(1, rate * proc.duration / 60))
        end
    end
    for _, bonus in ipairs(scenario.sets or {}) do
        if (sets[bonus.set_id] or 0) >= bonus.pieces then addStats(stats, bonus.stats) end
    end
    for _, racial in ipairs(scenario.racial_scaling or {}) do
        if racial.race_id == raceId then
            stats[racial.stat] = (stats[racial.stat] or 0) * racial.multiplier
        end
    end
    for _, conversion in ipairs(scenario.conversions or {}) do
        if conversion.condition ~= "shield" or shield then
            stats[conversion.stat] = (stats[conversion.stat] or 0) + (stats[conversion.from_stat] or 0) * conversion.factor
        end
    end
    local function value()
        local total = 0
        for stat, weight in pairs(weights) do
            total = total + math.min(stats[stat] or 0, (scenario.caps or {})[stat] or math.huge) * weight
        end
        return total
    end
    for _, operation in ipairs(operations) do
        local rank = byId(ranks, operation.entry)
        if rank > 0 and (operation.condition ~= "shield" or shield) then
            local factor = operation.factors[rank]
            local before = value()
            for _, stat in ipairs(operation.stats) do
                local amount = stats[stat] or 0
                if operation.kind == "convert" then
                    stats[stat] = amount + (stats[operation.from_stat] or 0) * factor
                elseif operation.kind == "efficiency" then
                    stats[stat] = amount / (1 + factor)
                else
                    stats[stat] = amount * (1 + factor)
                end
            end
            explanations[operation.entry] = (explanations[operation.entry] or 0) + value() - before
        end
    end
    return value(), explanations
end

local function itemIdentity(itemId, link)
    if not link then return tostring(itemId), nil end
    if not readable(link) or type(link) ~= "string" then return nil end
    local payload = link:match("item:([%-:%d]+)")
    if not payload then return nil end
    local fields = {}
    for field in (payload .. ":"):gmatch("(.-):") do fields[#fields + 1] = field end
    if tonumber(fields[1]) ~= itemId then return nil end
    local suffix = tonumber(fields[7]) or 0
    return suffix ~= 0 and (itemId .. ":" .. suffix) or tostring(itemId), tonumber(fields[2])
end

local function itemKey(item)
    return item.variant_id or tostring(item.id)
end

local function readRanks(model, profile)
    if not C_ClassTalents or not C_ClassTalents.GetActiveConfigID or not C_Traits
        or not C_Traits.GetConfigInfo or not C_Traits.GetNodeInfo or not C_Traits.GetDefinitionInfo then return nil end
    local configId = C_ClassTalents.GetActiveConfigID()
    if not readable(configId) or type(configId) ~= "number" or configId <= 0 then return nil end
    local config = C_Traits.GetConfigInfo(configId)
    if not readable(config) or type(config) ~= "table" or type(config.treeIDs) ~= "table" then return nil end
    local ranks = {}
    for _, entry in ipairs(profile.entries) do
        local trait = byId(model.traits, entry)
        if not contains(config.treeIDs, trait.tree_id) then return nil end
        local node = C_Traits.GetNodeInfo(configId, trait.node_id)
        local definition = C_Traits.GetDefinitionInfo(trait.definition_id)
        if not readable(node) or type(node) ~= "table" or not contains(node.entryIDs, entry)
            or not readable(definition) or type(definition) ~= "table" or not readable(definition.spellID)
            or definition.spellID ~= trait.spell_id then return nil end
        local active = node.activeEntry
        if not readable(active) then return nil end
        if active and (not readable(active.entryID) or not readable(active.rank)) then return nil end
        local rank = active and active.entryID == entry and active.rank
        if rank == nil or rank == false then
            if active and active.entryID == entry then return nil end
            rank = 0
        end
        if not readable(rank) or type(rank) ~= "number" or rank ~= math.floor(rank) or rank < 0 or rank > trait.max_rank then return nil end
        ranks[entry] = rank
    end
    return ranks
end

local function nativeItem(itemId, link, inventorySlot)
    local getStats = C_Item and C_Item.GetItemStats or GetItemStats
    local getInfo = C_Item and C_Item.GetItemInfoInstant or GetItemInfoInstant
    if not getStats or not getInfo then return nil end
    local _, _, _, equipLocation, _, classId, subclassId = getInfo(link)
    local values = getStats(link)
    if not readable(values) or type(values) ~= "table" or not readable(equipLocation)
        or type(equipLocation) ~= "string" or equipLocation == "" then return nil end
    local stats = {}
    for key, value in pairs(values) do
        if not readable(value) or type(value) ~= "number" then return nil end
        if LIVE_STATS[key] then stats[LIVE_STATS[key]] = value end
    end
    if classId == 2 and (inventorySlot == 16 or inventorySlot == 17) and not stats.dps then return nil end
    if classId == 2 and inventorySlot == 18 and stats.dps then
        local dpsStat = subclassId == 19 and "wand_dps" or "ranged_dps"
        stats[dpsStat], stats.dps = stats.dps, nil
    end
    return { id = itemId, stats = stats, slot = equipLocation == "INVTYPE_2HWEAPON" and "Two Hand" or nil,
        shield = equipLocation == "INVTYPE_SHIELD", weapon_subtype = classId == 2 and "Weapon" or nil }
end

local function readEquipment(model, mode)
    if not GetInventoryItemID or not GetInventoryItemLink then return nil end
    local gear = {}
    for slot = 1, 18 do
        if slot ~= 4 then
            local itemId = GetInventoryItemID("player", slot)
            if not readable(itemId) then return nil end
            if itemId then
                local link = GetInventoryItemLink("player", slot)
                if not readable(link) or type(link) ~= "string" then return nil end
                local key, enchant = itemIdentity(itemId, link)
                if not key then return nil end
                local otherMode = mode == "leveling" and "pre_raid" or "leveling"
                local item = model.items[mode][key] or model.items[otherMode][key]
                if not item and key == tostring(itemId) then
                    item = nativeItem(itemId, link, slot)
                    if item then item.set_id = byId(model.item_sets, itemId) end
                end
                if not item then return nil end
                if enchant and enchant > 0 then
                    local enchantStats = byId(model.enchants, enchant)
                    if not enchantStats then return nil end
                    item = copy(item)
                    item.stats = copy(item.stats)
                    addStats(item.stats, enchantStats)
                end
                gear[slot] = item
            end
        end
    end
    return gear
end

local function acquireContext(model, profile, scenario, mode, level, raceId)
    local weights
    for _, band in ipairs(scenario.weights) do
        if level >= band[1] and level <= band[2] then weights = band[3] break end
    end
    if not weights then return nil end
    local ranks = readRanks(model, profile)
    local gear = ranks and readEquipment(model, mode)
    if not gear then return nil end
    local scenarioForScore = scenario
    if profile.ability and ranks[profile.ability.entry] > 0 and scenario.judgement_per_minute then
        local ability = model.triggers[tostring(profile.ability.spell)]
        if ability then
            scenarioForScore = copy(scenario)
            scenarioForScore.events_per_minute = copy(scenario.events_per_minute or {})
            for _, trigger in ipairs(ability.activates) do
                scenarioForScore.events_per_minute[trigger] = (scenarioForScore.events_per_minute[trigger] or 0) + scenario.judgement_per_minute
            end
        end
    end
    return { gear = gear, ranks = ranks, weights = weights, scenario = scenarioForScore, race = raceId, level = level,
        items = model.items[mode], profile = profile, slots = {} }
end

function Scoring:Invalidate()
    self.live = nil
    self.revision = (self.revision or 0) + 1
end

function Scoring:GetContext(className, specName, mode, level, filters)
    local model = BigBiSListData and BigBiSListData.character_scoring
    if not model or model.version ~= VERSION then return nil end
    if mode == "leveling" and BigBiSList.GetCharacterDB then
        local character = BigBiSList:GetCharacterDB()
        if character and character.leveling and character.leveling.manualLevel then return nil end
    end
    local key = className .. "/" .. specName
    local profile = model.profiles[key]
    if not profile or not GetBuildInfo or not UnitRace or not UnitLevel then return nil end
    local scenario = profile.scenarios[mode]
    if not scenario then return nil end
    local ok, result = pcall(function()
        local _, build = GetBuildInfo()
        local playerLevel = UnitLevel("player")
        local _, _, race = UnitRace("player")
        if not readable(build) or tonumber(build) ~= model.build or not readable(race) or not readable(playerLevel)
            or playerLevel ~= level or BigBiSList:DetectPlayerClass() ~= className then return nil end
        local actor = byId(scenario.personas, race)
        if not actor or actor[2] ~= BigBiSList:GetPlayerFactionName()
            or (filters and ((filters.race and filters.race ~= actor[1]) or (filters.faction and filters.faction ~= actor[2]))) then return nil end
        local stateKey = key .. ":" .. mode .. ":" .. level .. ":" .. race
        if self.live and self.live.key == stateKey then return self.live.context end
        if BigBiSList:DetectPlayerSpec(className) ~= specName then
            return nil
        end
        local context = acquireContext(model, profile, scenario, mode, level, race)
        if context then
            context.raceName, context.faction, context.mode = actor[1], actor[2], mode
            self.live = {key = stateKey, context = context}
        end
        return context
    end)
    if ok then return result end
end

local function score(state, gear)
    return Scoring.ScoreLoadout(gear, state.weights, state.profile.operations, state.ranks, state.scenario, state.race)
end

local function replace(state, gear, target, item, slot)
    if item.required_level and item.required_level > state.level then return nil end
    for index, worn in pairs(gear) do
        if index ~= target and not (slot == "Two Hand" and index == 17)
            and ((item.max_equipped == 1 and worn.id == item.id) or (item.unique_group and worn.unique_group == item.unique_group)) then
            return nil
        end
    end
    local result = copy(gear)
    result[target] = item
    if slot == "Two Hand" then
        result[17] = nil
    elseif slot == "Off Hand" then
        if result[16] and result[16].slot == "Two Hand" then return nil end
        if item.weapon_subtype and item.requires_dual_wield ~= false
            and (not state.scenario.dual_wield_level or state.level < state.scenario.dual_wield_level) then return nil end
    end
    return result
end

function Scoring:RankSlot(state, slot)
    if not slot then return { all = {}, selected = {}, byIdentity = {} } end
    if state.slots[slot] then return state.slots[slot] end
    local result = { all = {}, selected = {}, byIdentity = {} }
    state.slots[slot] = result
    local slots = SLOTS[slot]
    if not slots then return result end
    -- Compare every candidate to the same legal baseline, even when two rings
    -- or trinkets can be replaced in different inventory slots.
    local base, baseEffects
    for _, target in ipairs(slots) do
        local outside = copy(state.gear)
        outside[target] = nil
        if slot == "Two Hand" then outside[17] = nil end
        local total, effects = score(state, outside)
        if base == nil or total > base then base, baseEffects = total, effects end
    end
    for _, row in ipairs(state.scenario.pools[slot] or {}) do
        local item = state.items[row[1]]
        for _, window in ipairs(byId(row[2], state.race) or {}) do
            if window[1] <= state.level and state.level <= window[2] then
                local target, total, effects
                for _, inventorySlot in ipairs(slots) do
                    local loadout = replace(state, state.gear, inventorySlot, item, slot)
                    if loadout then
                        local value, contributions = score(state, loadout)
                        if total == nil or value > total then
                            target, total, effects = inventorySlot, value, contributions
                        end
                    end
                end
                if target then
                    local difference = {}
                    for _, operation in ipairs(state.profile.operations) do
                        local entry = operation.entry
                        local delta = (effects[entry] or 0) - (baseEffects[entry] or 0)
                        if math.abs(delta) >= 0.0001 then difference[entry] = delta end
                    end
                    result.all[#result.all + 1] = { item = item, score = math.floor((total - base) * 10000 + 0.5) / 10000,
                        effects = difference, target = target, total = total }
                end
                break
            end
        end
    end
    table.sort(result.all, function(a, b)
        if a.score ~= b.score then return a.score > b.score end
        if a.item.item_level ~= b.item.item_level then return a.item.item_level > b.item.item_level end
        if a.item.name ~= b.item.name then return a.item.name < b.item.name end
        if a.item.id ~= b.item.id then return a.item.id < b.item.id end
        return (a.item.variant_id or "") < (b.item.variant_id or "")
    end)
    local best = result.all[1] and result.all[1].score or 0
    for rank, row in ipairs(result.all) do
        row.rank = rank
        result.byIdentity[itemKey(row.item)] = row
        if rank <= 3 or (best > 0 and row.score > 0 and row.score >= best * 0.95) then
            result.selected[#result.selected + 1] = row
        end
    end
    return result
end

function Scoring:Compare(state, slot, candidateId, referenceId, options)
    local scores = self:RankSlot(state, slot)
    local candidateKey = options and options.candidateVariant or tostring(candidateId)
    local candidate = scores.byIdentity[candidateKey]
    if not candidate then return nil end
    local equippedSlot = options and options.inventorySlotId
    local target = equippedSlot or candidate.target
    if not contains(SLOTS[slot], target) then return nil end
    local referenceLink = options and options.item_link
    local referenceKey = itemIdentity(referenceId, referenceLink)
    if not referenceKey then return nil end
    local worn = state.gear[target]
    local referenceItem
    if worn and worn.id == referenceId and (not referenceLink or itemKey(worn) == referenceKey) then
        if itemKey(worn) == candidateKey then return 0, {} end
        referenceItem = worn
    elseif not equippedSlot then
        local reference = scores.byIdentity[referenceKey]
        referenceItem = reference and reference.item
    end
    if not referenceItem then return nil end
    local referenceSlot = slot
    if target == 16 then
        referenceSlot = referenceItem.slot == "Two Hand" and "Two Hand" or "Main Hand"
    end
    local other = replace(state, state.gear, target, referenceItem, referenceSlot)
    if not other then return nil end
    local replacement = replace(state, state.gear, target, candidate.item, slot)
    if not replacement then return nil, nil, "illegal_swap" end
    local baseline, baselineEffects = score(state, other)
    local overall, effects = score(state, replacement)
    local explanation = {}
    for _, effect in ipairs(state.profile.operations) do
        local difference = (effects[effect.entry] or 0) - (baselineEffects[effect.entry] or 0)
        if math.abs(difference) >= 0.0001 then
            explanation[#explanation + 1] = effect.name .. " (" .. string.format("%+.2f", difference) .. ")"
        end
    end
    return overall - baseline, explanation
end

function Scoring:EffectLabel(state, row)
    local names = {}
    for _, effect in ipairs(state.profile.operations) do
        if row.effects[effect.entry] then names[#names + 1] = effect.name end
    end
    return #names > 0 and ("Active build: " .. table.concat(names, ", ")) or "Active build"
end
