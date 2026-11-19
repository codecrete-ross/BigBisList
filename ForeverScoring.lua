local BigBiSList = _G.BigBiSList
local Scoring = {}
BigBiSList.ForeverScoring = Scoring

local VERSION = "forever-character-scoring-1"
local SLOTS = {
    Head = {1}, Neck = {2}, Shoulder = {3}, Chest = {5}, Waist = {6},
    Legs = {7}, Feet = {8}, Wrist = {9}, Hands = {10}, Ring = {11, 12},
    Trinket = {13, 14}, Back = {15}, ["Main Hand"] = {16}, ["Two Hand"] = {16},
    ["Off Hand"] = {17}, Ranged = {18}, Idol = {18}, Libram = {18}, Totem = {18}, Relic = {18},
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
    return values and (values[identifier] or values[tostring(identifier)] or values[tonumber(identifier)])
end

local function addStats(total, stats, multiplier)
    for key, value in pairs(stats or {}) do
        total[key] = (total[key] or 0) + value * (multiplier or 1)
    end
end

local function operationApplies(operation, rank, level, shield, twoHand)
    return rank > 0 and level >= (operation.min_level or 1) and level <= (operation.max_level or 60)
        and (not operation.condition or (operation.condition == "shield" and shield)
            or (operation.condition == "two_hand" and twoHand))
end

local function baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, bonusStats, breakdown)
    local stats, sets, explanations = {}, {}, {}
    local shield = false
    local mainHand, offHand = loadout[16], loadout[17]
    local twoHand = mainHand and mainHand.slot == "Two Hand"
    local offhandDps = offHand and offHand.stats.dps or 0
    local offhandFactor = scenario.offhand_dps_factor or 1
    level = level or 60
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
    stats.dps = (stats.dps or 0) - offhandDps * (1 - offhandFactor)
    stats.weapon_speed = mainHand and mainHand.stats.weapon_speed or 0
    addStats(stats, bonusStats)
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
    local specificCrit = scenario.crit_domain == "spell" and "spell_crit_percent"
        or scenario.crit_domain == "physical" and "physical_crit_percent"
    if specificCrit and not weights[specificCrit] then
        stats.crit_percent = (stats.crit_percent or 0) + (stats[specificCrit] or 0)
    end
    if scenario.crit_domain == "spell" and not weights.spell_hit_percent then
        stats.hit_percent = (stats.hit_percent or 0) + (stats.spell_hit_percent or 0)
    end
    local function value(points)
        local total = 0
        for stat, weight in pairs(weights) do
            local contribution = math.min(stats[stat] or 0, (scenario.caps or {})[stat] or math.huge) * weight
            total = total + contribution
            if points then points[stat] = contribution end
        end
        return total
    end
    for _, operation in ipairs(operations) do
        local rank = byId(ranks, operation.entry) or 0
        if operationApplies(operation, rank, level, shield, twoHand) then
            local factor = operation.factors[rank]
            local before = value()
            for _, stat in ipairs(operation.stats) do
                local amount = stats[stat] or 0
                if operation.kind == "convert" then
                    stats[stat] = amount + (stats[operation.from_stat] or 0) * factor
                elseif operation.kind == "efficiency" then
                    stats[stat] = amount / (1 + factor)
                elseif operation.kind == "offhand_damage" then
                    stats[stat] = amount + offhandDps * offhandFactor * factor
                else
                    stats[stat] = amount * (1 + factor)
                end
            end
            explanations[operation.entry] = (explanations[operation.entry] or 0) + value() - before
        end
    end
    return value(breakdown), explanations, sets
end

-- Follow the same conversions in reverse to identify which effect outputs can
-- affect the final score. A cap can legitimately reduce a modeled gain to zero.
local function scoredChannels(loadout, weights, operations, ranks, scenario, level)
    local channels, shield = {}, false
    for stat, weight in pairs(weights) do if weight ~= 0 then channels[stat] = true end end
    for _, item in pairs(loadout) do shield = shield or item.shield end
    local twoHand = loadout[16] and loadout[16].slot == "Two Hand"
    for index = #operations, 1, -1 do
        local rule = operations[index]
        if rule.kind == "convert" and operationApplies(rule, byId(ranks, rule.entry) or 0, level or 60, shield, twoHand) then
            for _, stat in ipairs(rule.stats) do
                if channels[stat] then channels[rule.from_stat] = true; break end
            end
        end
    end
    local crit = scenario.crit_domain == "spell" and "spell_crit_percent"
        or scenario.crit_domain == "physical" and "physical_crit_percent"
    if crit and not weights[crit] then channels[crit] = channels.crit_percent end
    if scenario.crit_domain == "spell" and not weights.spell_hit_percent then channels.spell_hit_percent = channels.hit_percent end
    local conversions = scenario.conversions or {}
    for index = #conversions, 1, -1 do
        local rule = conversions[index]
        if channels[rule.stat] and (rule.condition ~= "shield" or shield) then channels[rule.from_stat] = true end
    end
    return channels
end

local function hasScoredChannel(stats, channels)
    for stat in pairs(stats) do if channels[stat] then return true end end
    return false
end

local function expectedActivations(rule, observation, loadout, position)
    local rate = observation.per_minute
    if observation.uses and observation.seconds and observation.seconds > 0 then
        rate = 60 * observation.uses / observation.seconds
    elseif not rate and observation.events_per_minute then
        local chance = rule.chance
        local weapon = loadout[position]
        local speed = weapon and weapon.stats.weapon_speed
        if rule.ppm and speed then chance = math.min(1, rule.ppm * speed / 60) end
        if chance then
            rate = observation.events_per_minute * chance
            if (rule.cooldown or 0) > 0 then
                if observation.cooldown_model ~= "poisson" then return nil end
                rate = rate / (1 + rate * rule.cooldown / 60)
            end
        end
    end
    return rate
end

local function itemEffect(rule, observation, loadout, position, scenario)
    if not observation then return nil end
    if observation.applicable == false then return {} end
    if rule.kind == "timed_stats" then
        if rule.requires_target_fraction and observation.target_fraction == nil then return nil end
        local uptime = observation.uptime
        if uptime == nil and (rule.cooldown or 0) >= rule.duration then
            local rate = expectedActivations(rule, observation, loadout, position)
            uptime = rate and math.min(1, rate * rule.duration / 60)
        end
        if uptime ~= nil then
            local multiplier = ((rule.terrain_multiplier or {})[scenario.terrain] or 1)
                * ((rule.target_multiplier or {})[scenario.target_family] or 1)
            local stats = {}
            addStats(stats, rule.stats, multiplier)
            return stats, uptime * (observation.target_fraction or 1)
        end
    elseif rule.kind == "mana_cost" then
        if observation.mana_per_minute then return { mp5 = observation.mana_per_minute * rule.fraction / 12 } end
    else
        local rate = expectedActivations(rule, observation, loadout, position)
        if rate == nil then return nil end
        if rule.kind == "instant" then
            if observation.useful_fraction == nil then return nil end
            local scale = (rule.terrain_multiplier or {})[scenario.terrain] or 1
            local stats = {}
            addStats(stats, rule.amounts, rate * scale * observation.useful_fraction / 60)
            return stats
        elseif rule.kind == "extra_attack" then
            local weapon = loadout[observation.weapon_slot or position]
            local stats = weapon and weapon.stats
            if not stats or not stats.weapon_min_damage or not stats.weapon_max_damage
                or observation.damage_factor == nil then return nil end
            local average = (stats.weapon_min_damage + stats.weapon_max_damage) / 2
            return { dps = average * rate * rule.count * observation.damage_factor / 60 }
        elseif rule.kind == "damage" and observation.damage_factor ~= nil then
            return { proc_dps = rule.amount * rate * observation.damage_factor / 60 }
        end
    end
end

local function setCoverage(loadout, scenario)
    local applied = {}
    if not scenario.set_effect_spells then return applied end
    local equipped = {}
    for _, item in pairs(loadout) do
        if item.set_id then equipped[item.set_id] = (equipped[item.set_id] or 0) + 1 end
    end
    for position, item in pairs(loadout) do
        if item.set_id and item.set_bonuses then
            local covered = true
            for _, bonus in ipairs(item.set_bonuses) do
                if bonus.pieces <= equipped[item.set_id] and not byId(scenario.set_effect_spells, bonus.spell_id) then
                    covered = false
                    break
                end
            end
            if covered then applied[position] = { ["Set bonuses"] = true } end
        end
    end
    return applied
end

function Scoring.ScoreLoadout(loadout, weights, operations, ranks, scenario, raceId, level, includeBreakdown)
    local applied = setCoverage(loadout, scenario)
    local breakdown = includeBreakdown and {} or nil
    if not scenario.effect_expectations then
        local points, explanations, sets = baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, nil, breakdown)
        return points, explanations, applied, sets, breakdown
    end
    local flat, timed, timedKeys = {}, {}, {}
    local channels = scoredChannels(loadout, weights, operations, ranks, scenario, level)
    local useRules = {}
    for position, item in pairs(loadout) do
        for _, rule in ipairs(item.effect_rules or {}) do
            if rule.trigger == "use" then
                useRules[#useRules + 1] = position .. ":" .. (item.key or item.variant_id or item.id) .. ":" .. rule.key
            end
        end
    end
    table.sort(useRules)
    local useSignature, timedUses, allScoped = table.concat(useRules, "|"), 0, true
    for position = 1, 18 do
        local item = loadout[position]
        local expectations = item and byId(scenario.effect_expectations, item.key or item.variant_id or item.id)
        for _, rule in ipairs(item and item.effect_rules or {}) do
            local observation = expectations and expectations[rule.key]
            local stats, uptime = itemEffect(rule, observation, loadout, position, scenario)
            if observation and observation.applicable == false then
                applied[position] = applied[position] or {}
                applied[position][rule.label] = true
            elseif stats then
                local modeled = hasScoredChannel(stats, channels)
                local use = rule.trigger == "use"
                local scoped = not use or #useRules < 2 or observation.use_signature == useSignature
                if uptime then
                    local key = position .. ":" .. (item.key or item.variant_id or item.id) .. ":" .. rule.key
                    timedKeys[#timedKeys + 1] = key
                    timed[key] = { rule = rule, stats = stats, uptime = uptime, position = position, modeled = modeled }
                    if use then timedUses = timedUses + 1 end
                    allScoped = allScoped and scoped
                elseif scoped then
                    addStats(flat, stats)
                    if modeled then
                        applied[position] = applied[position] or {}
                        applied[position][rule.label] = true
                    end
                end
            end
        end
    end
    local total, explanations, sets = baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, flat, breakdown)
    local states
    if #timedKeys == 1 and allScoped then
        states = { { active = timedKeys, fraction = timed[timedKeys[1]].uptime } }
    elseif #timedKeys > 1 and (allScoped or timedUses == #useRules) then
        table.sort(timedKeys)
        states = (scenario.effect_state_observations or {})[table.concat(timedKeys, "|")]
    end
    if states then
        local baseline, baselineExplanations = total, copy(explanations)
        local baselineBreakdown = breakdown and copy(breakdown)
        for _, state in ipairs(states) do
            local stats = copy(flat)
            for _, key in ipairs(state.active) do addStats(stats, timed[key].stats) end
            local activeBreakdown = breakdown and {}
            local active, activeExplanations = baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, stats,
                activeBreakdown)
            total = total + (active - baseline) * state.fraction
            for id, value in pairs(activeExplanations) do
                explanations[id] = (explanations[id] or 0) + (value - (baselineExplanations[id] or 0)) * state.fraction
            end
            if breakdown then
                for stat, points in pairs(activeBreakdown) do
                    breakdown[stat] = breakdown[stat] + (points - baselineBreakdown[stat]) * state.fraction
                end
            end
        end
        for _, effect in pairs(timed) do
            if effect.modeled then
                applied[effect.position] = applied[effect.position] or {}
                applied[effect.position][effect.rule.label] = true
            end
        end
    end
    return total, explanations, applied, sets, breakdown
end

function Scoring:StatDifferences(before, after)
    if not before or not after then return nil end
    local changes = {}
    for stat, points in pairs(after) do changes[stat] = points - (before[stat] or 0) end
    return changes
end

function Scoring:ReferenceItem(facts, stats)
    local model = BigBiSListData and BigBiSListData.character_scoring
    return { id = facts.id, key = facts.key or facts.variant_id, stats = stats, slot = facts.slot,
        shield = facts.armor_type == "Shield", effect_rules = facts.effect_rules, effects = facts.effects,
        unreadable_effects = facts.unreadable_effects, utility = facts.utility,
        set_id = model and byId(model.item_sets, facts.id), set_bonuses = facts.set_bonuses }
end

function Scoring:HasUnresolvedEffects(item, applied)
    if not item or item.utility then return false end
    if item.unreadable_effects then return true end
    for _, label in ipairs(item.effects or {}) do
        if not (applied and applied[label]) then return true end
    end
    return false
end

local function itemIdentity(itemId, link)
    if not link then return tostring(itemId), nil end
    if not readable(link) or type(link) ~= "string" then return nil end
    local rating = BigBiSList.ForeverGearRating
    if rating then
        local key, _, fields = rating:NormalizeLink(itemId, link)
        return key, fields
    end
    local payload = link:match("item:([%-:%d]+)")
    if not payload then return nil end
    local fields = {}
    for field in (payload .. ":"):gmatch("(.-):") do fields[#fields + 1] = field end
    if tonumber(fields[1]) ~= itemId then return nil end
    local suffix = tonumber(fields[7]) or 0
    return suffix ~= 0 and (itemId .. ":" .. suffix) or tostring(itemId), fields
end

local function itemKey(item)
    return item.key or item.variant_id or tostring(item.id)
end

function Scoring:GetExactStats(itemId, stats, link)
    if not link then return stats end
    local identity, fields = itemIdentity(itemId, link)
    if not fields then return stats, true end
    local hasModifiers = false
    for index = 2, 6 do
        if (tonumber(fields[index]) or 0) ~= 0 then hasModifiers = true; break end
    end
    if not hasModifiers then return stats end
    local model = BigBiSListData and BigBiSListData.character_scoring
    local _, build
    if GetBuildInfo then _, build = GetBuildInfo() end
    if not model or (GetBuildInfo and (not readable(build) or tonumber(build) ~= model.build)) then return stats, true end

    local total, uncertain, socketed = copy(stats or {}), false, false
    for index = 2, 6 do
        local id = tonumber(fields[index]) or 0
        if id ~= 0 then
            local modifier = byId(index == 2 and model.enchants or model.gems, id)
            if modifier then addStats(total, modifier)
            else uncertain = true end
            if index > 2 then socketed = true end
        end
    end
    if socketed then
        local signature = identity .. ":" .. string.format("%d:%d:%d:%d", tonumber(fields[3]) or 0,
            tonumber(fields[4]) or 0, tonumber(fields[5]) or 0, tonumber(fields[6]) or 0)
        local bonus = byId(model.socket_bonuses, signature)
        if bonus then addStats(total, bonus)
        else uncertain = true end
    end
    return total, uncertain
end

local function readRanks(model, profile, level)
    if level < 10 then return {} end
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

local function swapItem(model, mode, id, link, facts)
    local key = link and itemIdentity(id, link) or facts and itemKey(facts)
    if not key or (facts and itemKey(facts) ~= key) then return nil end
    local otherMode = mode == "leveling" and "pre_raid" or "leveling"
    local known = model.items[mode][key] or model.items[otherMode][key]
    local rating = BigBiSList.ForeverGearRating
    if not facts and rating then facts = rating:GetExactBaseFacts(id, link) end
    if not facts and not known then return nil end
    local item = copy(known or facts or {})
    for field, value in pairs(facts or {}) do item[field] = value end
    item.key, item.link = key, link
    item.shield = item.armor_type == "Shield" or item.shield
    item.set_id = item.set_id or byId(model.item_sets, id)
    item.stats, item.uncertain = Scoring:GetExactStats(id, item.stats, link)
    item.uncertain = item.uncertain or item.unreadable_effects
    if not item.stats or (item.weapon_subtype and (item.slot == "Main Hand" or item.slot == "Two Hand"
        or item.slot == "One Hand") and not item.stats.dps) then return nil end
    return item
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
                local item = swapItem(model, mode, itemId, link)
                if not item then return nil end
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
    local ranks = readRanks(model, profile, level)
    local gear = ranks and readEquipment(model, mode)
    if not gear then return nil, ranks and "equipment" or "talents" end
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
        items = model.items[mode], profile = profile, slots = {}, model = model }
end

function Scoring:GetPreset(className, specName, mode, level, scenarioKey)
    local model = BigBiSListData and BigBiSListData.character_scoring
    local profile = model and model.version == VERSION and model.profiles[className .. "/" .. specName]
    if not profile then return end
    local base = profile.scenarios[mode]
    if scenarioKey == "dungeon" then
        local dungeon = profile.dungeon and profile.dungeon[mode]
        if base and dungeon and level and level >= dungeon.min_level and level <= dungeon.max_level then
            profile.dungeonContexts = profile.dungeonContexts or {}
            if not profile.dungeonContexts[mode] then
                local merged = copy(base)
                for _, field in ipairs({ "caps", "conversions", "effect_expectations", "effect_state_observations",
                    "terrain", "target_family" }) do merged[field] = nil end
                for key, value in pairs(dungeon) do merged[key] = value end
                profile.dungeonContexts[mode] = merged
            end
            return profile.dungeonContexts[mode], profile
        end
        return
    end
    return base, profile
end

function Scoring:Invalidate()
    self.live = nil
    self.revision = (self.revision or 0) + 1
end

function Scoring:GetContext(className, specName, mode, level, filters)
    local model = BigBiSListData and BigBiSListData.character_scoring
    if not model or model.version ~= VERSION then return nil end
    if mode == "leveling" and not (filters and filters.live) and BigBiSList.GetCharacterDB then
        local character = BigBiSList:GetCharacterDB()
        if character and character.leveling and character.leveling.manualLevel then return nil end
    end
    local key = className .. "/" .. specName
    local scenarioKey = filters and filters.scenario
    local scenario, profile = self:GetPreset(className, specName, mode, level, scenarioKey)
    if not profile or not GetBuildInfo or not UnitRace or not UnitLevel then return nil end
    if not scenario then return nil end
    local ok, result, status = pcall(function()
        local _, build = GetBuildInfo()
        local playerLevel = UnitLevel("player")
        local _, _, race = UnitRace("player")
        if not readable(build) or tonumber(build) ~= model.build or not readable(race) or not readable(playerLevel)
            or playerLevel ~= level or BigBiSList:DetectPlayerClass() ~= className then return nil end
        local actor = byId(scenario.personas, race)
        if not actor or actor[2] ~= BigBiSList:GetPlayerFactionName()
            or (filters and ((filters.race and filters.race ~= actor[1]) or (filters.faction and filters.faction ~= actor[2]))) then return nil end
        local stateKey = table.concat({key, mode, level, race, scenarioKey or "default"}, ":")
        if BigBiSList:DetectPlayerSpec(className) ~= specName then
            return nil
        end
        self.live = self.live or {}
        if self.live[stateKey] then return self.live[stateKey] end
        local context, missing = acquireContext(model, profile, scenario, mode, level, race)
        if context then
            context.raceName, context.faction, context.mode = actor[1], actor[2], mode
            self.live[stateKey] = context
        end
        return context, missing
    end)
    if ok then return result, status end
end

local function score(state, gear, weights, includeBreakdown)
    return Scoring.ScoreLoadout(gear, weights or state.weights, state.profile.operations, state.ranks,
        state.scenario, state.race, state.level, includeBreakdown)
end

local function withSwap(gear, target, item, slot)
    local result = copy(gear)
    result[target] = item
    if slot == "Two Hand" then result[17] = nil end
    return result
end

local function replace(state, gear, target, item, slot)
    if item.required_level and item.required_level > state.level then return nil end
    local limit, copies = item.max_equipped, 0
    for index, worn in pairs(gear) do
        if index ~= target and not (slot == "Two Hand" and index == 17)
            and (worn.id == item.id or (item.unique_group and worn.unique_group == item.unique_group)) then
            copies = copies + 1
            if worn.max_equipped then limit = math.min(limit or worn.max_equipped, worn.max_equipped) end
        end
    end
    limit = limit or (item.unique_group and 1)
    if limit and copies >= limit then return nil end
    if slot == "Off Hand" then
        if gear[16] and gear[16].slot == "Two Hand" then return nil end
        if item.weapon_subtype and item.requires_dual_wield ~= false
            and (not state.scenario.dual_wield_level or state.level < state.scenario.dual_wield_level) then return nil end
    end
    return withSwap(gear, target, item, slot)
end

local function swapEffects(state, effects, baselineEffects, sets, baselineSets)
    local explanation, seen = {}, {}
    for _, effect in ipairs(state.profile.operations) do
        local difference = (effects[effect.entry] or 0) - (baselineEffects[effect.entry] or 0)
        if not seen[effect.entry] and math.abs(difference) >= 0.0001 then
            explanation[#explanation + 1] = effect.name .. " (" .. string.format("%+.2f", difference) .. ")"
            seen[effect.entry] = true
        end
    end
    local names = state.model and state.model.set_names
    for _, bonus in ipairs(names and state.scenario.sets or {}) do
        local name = byId(names, bonus.set_id)
        local before = (baselineSets[bonus.set_id] or 0) >= bonus.pieces
        local after = (sets[bonus.set_id] or 0) >= bonus.pieces
        if name and before ~= after then
            explanation[#explanation + 1] = string.format("%d-piece %s bonus %s", bonus.pieces, name, after and "gained" or "lost")
        end
    end
    return explanation
end

-- Nominal chance on a qualified attack. Effective stacks and casts depend on the encounter.
function Scoring.WeaponProcChance(trigger, rank, weapon)
    local ppm = trigger and trigger.ppm[rank]
    local speed = weapon and weapon.stats.weapon_speed
    if ppm and speed then return math.min(1, ppm * speed / 60) end
end

local function dependsOnUnmodeledCombat(state, incoming, target, slot)
    local first = state.gear[target]
    local offHand = slot == "Two Hand" and state.gear[17]
    local hit = incoming.stats.hit_percent or 0
    local wornHit = (first and first.stats.hit_percent or 0) + (offHand and offHand.stats.hit_percent or 0)
    if hit ~= wornHit and (state.weights.hit_percent or 0) > 0
        and not (state.scenario.caps and state.scenario.caps.hit_percent) then return true end
    local proc = state.profile.weapon_speed_proc
    local rank = proc and byId(state.ranks, proc.entry)
    local trigger = rank and rank > 0 and byId(state.model.triggers, proc.spell)
    if trigger and target == trigger.speed_slot
        and Scoring.WeaponProcChance(trigger, rank, incoming) ~= Scoring.WeaponProcChance(trigger, rank, first) then return true end
    for _, rule in ipairs(state.profile.uncertainty or {}) do
        local applies = not rule.entries
        for _, entry in ipairs(rule.entries or {}) do
            if (byId(state.ranks, entry) or 0) > 0 then applies = true; break end
        end
        if applies then
            for _, stat in ipairs(rule.stats) do
                if stat == "weapon_subtype" and incoming.weapon_subtype ~= (first and first.weapon_subtype) then return true end
                local gain = (incoming.stats[stat] or 0) - (first and first.stats[stat] or 0)
                    - (offHand and offHand.stats[stat] or 0)
                if math.abs(gain) > 0.0001 then return true end
            end
        end
    end
    if (target == 16 or target == 17) and not (state.scenario.form_attack_period and state.level >= 10)
        and (state.weights.dps or 0) > 0 and #(state.profile.unresolved or {}) > 0 then
        return incoming.stats.weapon_speed ~= (first and first.stats.weapon_speed or nil)
            or (offHand and offHand.stats.weapon_speed ~= nil)
    end
    return false
end

-- The rating service has already checked equipment and physical copy legality.
function Scoring:HasUnmodeledSwap(state, facts, target, slot)
    return dependsOnUnmodeledCombat(state, facts, target, slot)
end

function Scoring:EvaluateSwap(state, facts, link, target, slot, roleWeights, includeBreakdown)
    local incoming = swapItem(state.model, state.mode, facts.id, link, facts)
    if not incoming or not contains(SLOTS[slot], target) then return nil end
    local proposal = replace(state, state.gear, target, incoming, slot)
    if not proposal then return nil end
    if state.baseline == nil or (includeBreakdown and not state.baselineBreakdown) then
        state.baseline, state.baselineEffects, state.baselineItemEffects, state.baselineSets, state.baselineBreakdown =
            score(state, state.gear, nil, includeBreakdown)
        state.roleBaseline = score(state, state.gear, roleWeights)
        for _, worn in pairs(state.gear) do
            if worn.uncertain then state.uncertain = true; break end
        end
    end
    local total, effects, applied, sets, breakdown = score(state, proposal, nil, includeBreakdown)
    local conditional = false
    for position = 1, 18 do
        local before, after = state.gear[position], proposal[position]
        local old = state.baselineItemEffects and state.baselineItemEffects[position]
        local new = applied and applied[position]
        if (before ~= after or position == 16 or position == 17)
            and (self:HasUnresolvedEffects(before, old) or self:HasUnresolvedEffects(after, new)) then
            conditional = true
        end
    end
    local without = withSwap(state.gear, target, nil, slot)
    return {
        delta = total - state.baseline,
        roleDelta = score(state, proposal, roleWeights) - state.roleBaseline,
        roleDisplaced = math.max(0, state.roleBaseline - score(state, without, roleWeights)),
        effects = swapEffects(state, effects, state.baselineEffects, sets, state.baselineSets),
        contributions = self:StatDifferences(state.baselineBreakdown, breakdown),
        conditional = conditional or state.uncertain or incoming.uncertain or dependsOnUnmodeledCombat(state, incoming, target, slot),
    }
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
        local access = type(row[2]) == "table" and row[2] or byId(state.model and state.model.access_windows, row[2])
        for _, window in ipairs(byId(access, state.race) or {}) do
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
    local baseline, baselineEffects, _, baselineSets = score(state, other)
    local overall, effects, _, sets = score(state, replacement)
    return overall - baseline, swapEffects(state, effects, baselineEffects, sets, baselineSets)
end
