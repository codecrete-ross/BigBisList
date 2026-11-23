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

local RATING_UNITS = {
    hit_rating = {"hit_percent", 10}, crit_rating = {"crit_percent", 14},
    haste_rating = {"haste_percent", 10}, expertise_rating = {"expertise", 10},
    defense_rating = {"defense", 1}, dodge_rating = {"dodge_percent", 12},
    parry_rating = {"parry_percent", 15}, block_rating = {"block_percent", 5},
    spell_hit_rating = {"spell_hit_percent", 10}, spell_crit_rating = {"spell_crit_percent", 14},
    spell_haste_rating = {"spell_haste_percent", 10},
    melee_hit_rating = {"melee_hit_percent", 10}, ranged_hit_rating = {"ranged_hit_percent", 10},
    melee_crit_rating = {"melee_crit_percent", 14}, ranged_crit_rating = {"ranged_crit_percent", 14},
    melee_haste_rating = {"melee_haste_percent", 10}, ranged_haste_rating = {"ranged_haste_percent", 10},
}

function Scoring.NormalizeStats(stats)
    local result = copy(stats or {})
    for rating, rule in pairs(RATING_UNITS) do
        if result[rating] then
            if result[rule[1]] == nil then result[rule[1]] = result[rating] / rule[2] end
            result[rating] = nil
        end
    end
    return result
end

function Scoring:IsBuildSupported(model, build)
    if not model or not readable(build) then return false end
    build = tonumber(build)
    if not build then return false end
    return build == model.build or contains(model.supported_builds, build)
end

local function marginalPoints(amount, bonus, curve)
    local total, previous = 0, 0
    for _, segment in ipairs(curve) do
        local cap = segment[1]
        total = total + (math.max(0, math.min(amount + bonus, cap) - previous)
            - math.max(0, math.min(bonus, cap) - previous)) * segment[2]
        previous = cap
    end
    return total
end

local function recordCap(evidence, channel, amount, cap)
    local prior = evidence.caps[channel]
    if prior then
        prior.minimum = math.min(prior.minimum, amount)
        prior.maximum = math.max(prior.maximum, amount)
    else
        evidence.caps[channel] = {cap = cap, minimum = amount, maximum = amount}
    end
end

local function hitPoints(stats, curves, level, talents, evidence)
    local total = 0
    for _, curve in ipairs(curves) do
        local amount = (stats.hit_percent or 0) + (stats[curve.channel .. "_hit_percent"] or 0)
        if curve.channel == "offhand" then amount = amount + (stats.melee_hit_percent or 0) end
        local bonus = (talents.hit_percent or 0) + (talents[curve.channel .. "_hit_percent"] or 0)
        if curve.channel == "offhand" then bonus = bonus + (talents.melee_hit_percent or 0) end
        local previous = 0
        for _, segment in ipairs(curve.segments) do
            local cap = segment[1]
            if level < 60 then
                local spell = curve.channel == "spell"
                cap = (spell and 4 or 5) + math.max(0, cap - (spell and 17 or 8))
            end
            total = total + (math.max(0, math.min(amount + bonus, cap) - previous)
                - math.max(0, math.min(bonus, cap) - previous)) * segment[2]
            previous = cap
        end
        if evidence and previous > 0 then recordCap(evidence, curve.channel .. "_hit_percent", amount + bonus, previous) end
    end
    return total
end

local function byId(values, identifier)
    return values and (values[identifier] or values[tostring(identifier)] or values[tonumber(identifier)])
end

local function addStats(total, stats, multiplier)
    for key, value in pairs(stats or {}) do
        total[key] = (total[key] or 0) + value * (multiplier or 1)
    end
end

local function addNormalizedStats(total, stats)
    for stat, value in pairs(stats or {}) do
        local rule = RATING_UNITS[stat]
        if not rule then
            total[stat] = (total[stat] or 0) + value
        elseif stats[rule[1]] == nil then
            total[rule[1]] = (total[rule[1]] or 0) + value / rule[2]
        end
    end
end

local function operationApplies(operation, rank, level, shield, twoHand)
    return rank > 0 and level >= (operation.min_level or 1) and level <= (operation.max_level or 60)
        and (not operation.condition or (operation.condition == "shield" and shield)
            or (operation.condition == "two_hand" and twoHand))
end

local function addSetBonus(stats, bonus, key, name, evidence)
    if not evidence then addStats(stats, bonus.stats); return end
    local identity = key .. ":" .. bonus.pieces
    if evidence.ignoreSets and evidence.ignoreSets[identity] then return end
    if evidence.sets then evidence.sets[identity] = {name = name, pieces = bonus.pieces} end
    addStats(stats, bonus.stats)
end

local function baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, bonusStats, breakdown, evidence)
    local stats, sets, explanations = {}, {}, {}
    local tooltipSets
    local shield = false
    local mainHand, offHand = loadout[16], loadout[17]
    local twoHand = mainHand and mainHand.slot == "Two Hand"
    local offhandDps = offHand and offHand.stats.dps or 0
    local offhandFactor = scenario.offhand_dps_factor or 1
    level = level or 60
    for _, item in pairs(loadout) do
        addNormalizedStats(stats, item.stats)
        shield = shield or item.shield
        if item.set_id then sets[item.set_id] = (sets[item.set_id] or 0) + 1 end
        if item.effect_set then
            local key = item.effect_set.key
            tooltipSets = tooltipSets or {}
            tooltipSets[key] = item
            sets[key] = (sets[key] or 0) + 1
        end
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
        if (sets[bonus.set_id] or 0) >= bonus.pieces then
            local model = evidence and BigBiSListData and BigBiSListData.character_scoring
            addSetBonus(stats, bonus, bonus.set_id, model and byId(model.set_names, bonus.set_id), evidence)
        end
    end
    if tooltipSets then
        for key, item in pairs(tooltipSets) do
            for _, bonus in ipairs(item.effect_set.bonuses) do
                if bonus.stats and sets[key] >= bonus.pieces then
                    local credited
                    if item.set_id then
                        for _, legacy in ipairs(scenario.sets or {}) do
                            if legacy.set_id == item.set_id and legacy.pieces == bonus.pieces then credited = true; break end
                        end
                    end
                    if not credited then addSetBonus(stats, bonus, key, item.effect_set.name, evidence) end
                end
            end
        end
    end
    if scenario.form_attack_period and level >= (scenario.form_min_level or 10) then
        stats.attack_power = (stats.attack_power or 0) + (stats.feral_attack_power or 0)
    end
    if stats.weapon_damage then
        local speed = stats.weapon_speed > 0 and stats.weapon_speed or scenario.isolated_swing_seconds or 2.6
        stats.dps = (stats.dps or 0) + stats.weapon_damage / speed
        local offSpeed = offHand and offHand.stats.weapon_speed
        if offSpeed and offSpeed > 0 then stats.dps = stats.dps + stats.weapon_damage / offSpeed * offhandFactor end
        local ranged = loadout[18]
        local benchmark = scenario.effect_benchmark
        if (ranged and ranged.stats.ranged_dps) or (benchmark and benchmark.role == "ranged") then
            local rangedSpeed = ranged and ranged.stats.weapon_speed or 2.8
            stats.ranged_dps = (stats.ranged_dps or 0) + stats.weapon_damage / rangedSpeed
        end
    end
    local bonusHit = bonusStats and bonusStats.spell_hit_percent
    if bonusHit and scenario.effect_benchmark then
        local outside = (stats.spell_hit_percent or 0) - bonusHit + (stats.hit_percent or 0)
        stats.spell_hit_percent = stats.spell_hit_percent - math.max(0, bonusHit - math.max(0, scenario.effect_benchmark.spell_hit_cap - outside))
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
    local role = scenario.effect_benchmark and scenario.effect_benchmark.role
    if not scenario.crit_shares and stats.melee_crit_percent and (role == "melee" or role == "tank") then
        local stat = specificCrit or "crit_percent"
        stats[stat] = (stats[stat] or 0) + stats.melee_crit_percent
    end
    if scenario.crit_shares then
        for channel, share in pairs(scenario.crit_shares) do
            stats.crit_percent = (stats.crit_percent or 0) + (stats[channel .. "_crit_percent"] or 0) * share
            stats.haste_percent = (stats.haste_percent or 0) + (stats[channel .. "_haste_percent"] or 0) * share
        end
    elseif specificCrit and not weights[specificCrit] then
        stats.crit_percent = (stats.crit_percent or 0) + (stats[specificCrit] or 0)
    end
    if not scenario.hit_curves and scenario.crit_domain == "spell" and not weights.spell_hit_percent then
        stats.hit_percent = (stats.hit_percent or 0) + (stats.spell_hit_percent or 0)
    end
    local talents = copy(scenario.reference_bonuses or {})
    local coefficients = weights
    if scenario.reference_ranks and #operations > 0 then
        coefficients = copy(weights)
        -- Published gear weights include the reference talent pipeline.
        -- Invert it on the coefficients, then apply the active pipeline to
        -- stats. This preserves interactions such as Intellect scaling before
        -- converting Intellect to spell power.
        for _, operation in ipairs(operations) do
            local rank = byId(scenario.reference_ranks, operation.entry) or 0
            if rank > 0 and level >= (operation.min_level or 1) and level <= (operation.max_level or 60) then
                local factor = operation.factors[rank] or 0
                if operation.kind == "convert" then
                    for _, stat in ipairs(operation.stats) do
                        coefficients[operation.from_stat] = (coefficients[operation.from_stat] or 0)
                            - factor * (coefficients[stat] or 0)
                    end
                elseif operation.kind == "scale" or operation.kind == "efficiency" then
                    for _, stat in ipairs(operation.stats) do
                        local value = coefficients[stat] or 0
                        coefficients[stat] = operation.kind == "scale" and value / (1 + factor) or value * (1 + factor)
                    end
                end
            end
        end
    end
    local function value(points)
        local total, caps = 0, points and evidence and evidence.caps and evidence
        for stat, weight in pairs(coefficients) do
            local contribution = 0
            if weight ~= 0 then
                local cap, bonus = (scenario.caps or {})[stat] or math.huge, talents[stat] or 0
                local amount = math.min((stats[stat] or 0) + bonus, cap) - math.min(bonus, cap)
                if stat == "hit_percent" and scenario.hit_curves then
                    amount = hitPoints(stats, scenario.hit_curves, level, talents, caps)
                elseif caps and cap < math.huge then
                    recordCap(caps, stat, (stats[stat] or 0) + bonus, cap)
                end
                if stat == "expertise" and scenario.expertise_curve then
                    amount = marginalPoints(stats[stat] or 0, bonus, scenario.expertise_curve)
                    if caps then recordCap(caps, stat, (stats[stat] or 0) + bonus, scenario.expertise_curve[#scenario.expertise_curve][1]) end
                end
                contribution = amount * weight
            end
            total = total + contribution
            if points then points[stat] = contribution end
        end
        return total
    end
    for _, operation in ipairs(operations) do
        local rank = byId(ranks, operation.entry) or 0
        local referenceRank = byId(scenario.reference_ranks, operation.entry) or 0
        local active = operationApplies(operation, rank, level, shield, twoHand)
        local referenced = referenceRank > 0 and level >= (operation.min_level or 1)
            and level <= (operation.max_level or 60)
        if active or referenced then
            local factor = active and operation.factors[rank] or 0
            local reference = referenced and operation.factors[referenceRank] or 0
            local before = value()
            for _, stat in ipairs(operation.stats) do
                local amount = stats[stat] or 0
                if operation.kind == "convert" then
                    stats[stat] = amount + (stats[operation.from_stat] or 0) * factor
                elseif operation.kind == "add" then
                    talents[stat] = (talents[stat] or 0) + factor - reference
                elseif operation.kind == "efficiency" then
                    stats[stat] = amount / (1 + factor)
                elseif operation.kind == "offhand_damage" then
                    stats[stat] = amount + offhandDps * offhandFactor * ((1 + factor) / (1 + reference) - 1)
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
    for channel, share in pairs(scenario.crit_shares or {}) do
        if share > 0 then
            channels[channel .. "_crit_percent"] = channels.crit_percent
            channels[channel .. "_haste_percent"] = channels.haste_percent
        end
    end
    for _, curve in ipairs(scenario.hit_curves or {}) do channels[curve.channel .. "_hit_percent"] = channels.hit_percent end
    if channels.dps or channels.ranged_dps then channels.weapon_damage = true end
    if scenario.form_attack_period and channels.attack_power then channels.feral_attack_power = true end
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
    if rule.kind == "situational" then return {} end
    if rule.kind == "passive_stats" then
        local stats = {}
        for key, value in pairs(rule.stats) do
            stats[key] = rule.requires_form and value or math.max(0, value - (loadout[position].stats[key] or 0))
        end
        return stats
    end
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
            if observation.benchmark and stats.health then
                stats.stamina, stats.health = (stats.stamina or 0) + stats.health / 10, nil
            end
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
            if observation.benchmark and stats.hp5 then
                stats.proc_hps, stats.hp5 = (stats.proc_hps or 0) + stats.hp5 / 5, nil
            end
            return stats
        elseif rule.kind == "extra_attack" then
            local weapon = loadout[observation.weapon_slot or position]
            local stats = weapon and weapon.stats
            local average = observation.benchmark and scenario.isolated_swing_damage or nil
            if stats and stats.weapon_min_damage and stats.weapon_max_damage then
                average = (stats.weapon_min_damage + stats.weapon_max_damage) / 2
                if observation.form_period and stats.weapon_speed then average = average * observation.form_period / stats.weapon_speed end
            end
            if not average or observation.damage_factor == nil then return nil end
            if observation.benchmark then
                if position == 17 then average = average * (scenario.offhand_dps_factor or 1) end
                return { proc_dps = average * rate * rule.count * observation.damage_factor / 60 }
            end
            return { dps = average * rate * rule.count * observation.damage_factor / 60 }
        elseif rule.kind == "damage" and observation.damage_factor ~= nil then
            local damage = rule.amount * rate * observation.damage_factor / 60
            return { proc_dps = damage, proc_hps = rule.leech and damage * observation.useful_fraction or nil }
        end
    end
end

local function benchmarkObservation(rule, scenario, position, useScale, level, loadout)
    local preset = scenario.effect_benchmark
    if not preset then return nil end
    if rule.kind == "situational" or rule.kind == "passive_stats" then
        return { benchmark = true, applicable = not rule.requires_form or (level or 60) >= (scenario.form_min_level or 61) }
    end
    if not rule.rates then return nil end
    local rate = rule.rates[preset.index]
    local form = (level or 60) >= (scenario.form_min_level or 61) and scenario.form_attack_period
    if rule.trigger == "block" then
        local shield = loadout[17]
        if not ((shield and (shield.shield or shield.armor_type == "Shield"))
            or (scenario.isolated_swing_seconds and not form)) then rate = 0 end
    end
    if rule.kind == "extra_attack" and rule.benchmark_chance then
        local weapon = loadout[position == 17 and 17 or 16]
        local period = form or (weapon and weapon.stats.weapon_speed) or scenario.isolated_swing_seconds
        if period then
            rate = 60 * preset.melee * rule.benchmark_chance / period
            rate = rate / (1 + rate * (rule.cooldown or 0) / 60)
        end
    end
    local scale = rule.use_lockout and useScale or 1
    local factor = (rule.school == "physical" or rule.kind == "extra_attack") and preset.physical
        or rule.school == "bleed" and 1 or preset.magic
    if rule.periodic then factor = factor * preset.periodic_fraction
    elseif rule.periodic_amount then factor = factor * (1 + rule.periodic_amount * preset.periodic_fraction / rule.amount) end
    return { benchmark = true, applicable = rate > 0, per_minute = rate * scale, damage_factor = factor,
        useful_fraction = preset.useful_healing, target_fraction = 1,
        uptime = rule.uptimes and rule.uptimes[preset.index] * scale,
        weapon_slot = rule.kind == "extra_attack" and (position == 17 and 17 or 16) or nil, form_period = form }
end

local function modeledStates(keys, timed)
    local edges, cursor = {}, 0
    for _, key in ipairs(keys) do
        local effect = timed[key]
        if not effect.estimated then return end
        effect.start = effect.rule.use_lockout and cursor or 0
        effect.finish = math.min(1, effect.start + effect.uptime)
        if effect.rule.use_lockout then cursor = effect.finish end
        edges[#edges + 1] = effect.start
        edges[#edges + 1] = effect.finish
    end
    table.sort(edges)
    local states = {}
    for index = 2, #edges do
        local left, right = edges[index - 1], edges[index]
        if right > left then
            local active = {}
            for _, key in ipairs(keys) do
                if timed[key].start <= left and left < timed[key].finish then active[#active + 1] = key end
            end
            states[#states + 1] = { active = active, fraction = right - left }
        end
    end
    return states
end

local function markEffect(applied, position, rule, observation)
    local row = applied[position] or {}
    applied[position] = row
    row[rule.label] = observation or true
    for _, alias in ipairs(rule.aliases or {}) do row[alias] = row[rule.label] end
end

local function setCoverage(loadout, scenario)
    local applied = {}
    local equipped = {}
    for _, item in pairs(loadout) do
        if item.set_id then equipped[item.set_id] = (equipped[item.set_id] or 0) + 1 end
        if item.effect_set then
            local key = item.effect_set.key
            equipped[key] = (equipped[key] or 0) + 1
        end
    end
    for position, item in pairs(loadout) do
        if item.effect_set then
            local covered = true
            for _, bonus in ipairs(item.effect_set.bonuses) do
                if bonus.pieces <= equipped[item.effect_set.key] and not (bonus.stats or bonus.situational) then covered = false; break end
            end
            if covered then applied[position] = { ["Set bonuses"] = true } end
        elseif item.set_id and item.set_bonuses and scenario.set_effect_spells then
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

function Scoring.ScoreLoadout(loadout, weights, operations, ranks, scenario, raceId, level, includeBreakdown, evidence)
    local rating = BigBiSList.ForeverGearRating
    local checkpoint = rating and rating:GetWorkCheckpoint()
    if checkpoint then checkpoint() end
    local applied = setCoverage(loadout, scenario)
    local breakdown = includeBreakdown and {} or nil
    local hasRules, budget = false, 0
    for _, item in pairs(loadout) do
        for _, rule in ipairs(item.effect_rules or {}) do
            hasRules = true
            if rule.use_lockout and rule.rates and scenario.effect_benchmark then
                budget = budget + rule.rates[scenario.effect_benchmark.index] * rule.use_lockout / 60
            end
        end
    end
    if not hasRules or not (scenario.effect_expectations or scenario.effect_benchmark) then
        local points, explanations, sets = baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, nil, breakdown, evidence)
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
                or benchmarkObservation(rule, scenario, position, 1 / math.max(1, budget), level, loadout)
            local stats, uptime = itemEffect(rule, observation, loadout, position, scenario)
            if observation and observation.applicable == false then
                markEffect(applied, position, rule, observation)
            elseif stats then
                local modeled = hasScoredChannel(stats, channels) or observation.benchmark
                local use = rule.trigger == "use"
                local scoped = observation.benchmark or not use or #useRules < 2 or observation.use_signature == useSignature
                if uptime then
                    local key = position .. ":" .. (item.key or item.variant_id or item.id) .. ":" .. rule.key
                    timedKeys[#timedKeys + 1] = key
                    timed[key] = { rule = rule, stats = stats, uptime = uptime, position = position, modeled = modeled,
                        estimated = observation.benchmark, observation = observation }
                    if use then timedUses = timedUses + 1 end
                    allScoped = allScoped and scoped
                elseif scoped then
                    addStats(flat, stats)
                    if modeled then
                        markEffect(applied, position, rule, observation)
                    end
                end
            end
        end
    end
    local total, explanations, sets = baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, flat, breakdown, evidence)
    local states
    if #timedKeys == 1 and allScoped then
        states = { { active = timedKeys, fraction = timed[timedKeys[1]].uptime } }
    elseif #timedKeys > 1 and (allScoped or timedUses == #useRules) then
        table.sort(timedKeys)
        states = (scenario.effect_state_observations or {})[table.concat(timedKeys, "|")]
            or modeledStates(timedKeys, timed)
    end
    if states then
        local baseline, baselineExplanations = total, copy(explanations)
        local baselineBreakdown = breakdown and copy(breakdown)
        for _, state in ipairs(states) do
            if checkpoint then checkpoint() end
            local stats = copy(flat)
            for _, key in ipairs(state.active) do addStats(stats, timed[key].stats) end
            local activeBreakdown = breakdown and {}
            local active, activeExplanations = baseLoadout(loadout, weights, operations, ranks, scenario, raceId, level, stats,
                activeBreakdown, evidence)
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
                markEffect(applied, effect.position, effect.rule, effect.observation)
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
        set_id = model and byId(model.item_sets, facts.id), set_bonuses = facts.set_bonuses, effect_set = facts.effect_set }
end

function Scoring:HasUnresolvedEffects(item, applied)
    if item and item.stats and ((item.stats.spell_penetration or 0) > 0 or (item.stats.armor_penetration or 0) > 0) then return true end
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
    if not model or (GetBuildInfo and not self:IsBuildSupported(model, build)) then return stats, true end

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

function Scoring:GetPreset(className, specName, mode)
    local model = BigBiSListData and BigBiSListData.character_scoring
    local profile = model and model.version == VERSION and model.profiles[className .. "/" .. specName]
    if not profile then return end
    return profile.scenarios[mode], profile
end

function Scoring:Invalidate()
    self.live = nil
    self.revision = (self.revision or 0) + 1
end

function Scoring:PlayerTalentsChanged()
    local class = BigBiSList:DetectPlayerClass()
    local spec = class and BigBiSList:DetectPlayerSpec(class)
    local level = BigBiSList:GetDetectedPlayerLevel()
    local model = BigBiSListData and BigBiSListData.character_scoring
    local _, build
    if GetBuildInfo then _, build = GetBuildInfo() end
    local key = tostring(class) .. "/" .. tostring(spec) .. "/" .. tostring(level)
    local profile = model and model.profiles and model.profiles[tostring(class) .. "/" .. tostring(spec)]
    if profile and self:IsBuildSupported(model, build) and level then
        local ok, ranks = pcall(readRanks, model, profile, level)
        if ok and ranks then
            local values = {}
            for _, id in ipairs(profile.entries) do values[#values + 1] = ranks[id] or 0 end
            key = key .. "/" .. table.concat(values, ",")
        end
    end
    local changed = key ~= self.talentSignature
    self.talentSignature = key
    return changed
end

function Scoring:GetContext(className, specName, mode, level, filters)
    local model = BigBiSListData and BigBiSListData.character_scoring
    if not model or model.version ~= VERSION then return nil end
    if mode == "leveling" and not (filters and filters.live) and BigBiSList.GetCharacterDB then
        local character = BigBiSList:GetCharacterDB()
        if character and character.leveling and character.leveling.manualLevel then return nil end
    end
    local key = className .. "/" .. specName
    local scenario, profile = self:GetPreset(className, specName, mode)
    if not profile or not GetBuildInfo or not UnitRace or not UnitLevel then return nil end
    if not scenario then return nil end
    local ok, result, status = pcall(function()
        local _, build = GetBuildInfo()
        local playerLevel = UnitLevel("player")
        local _, _, race = UnitRace("player")
        if not self:IsBuildSupported(model, build) or not readable(race) or not readable(playerLevel)
            or playerLevel ~= level or BigBiSList:DetectPlayerClass() ~= className then return nil end
        local actor = byId(scenario.personas, race)
        if not actor or actor[2] ~= BigBiSList:GetPlayerFactionName()
            or (filters and ((filters.race and filters.race ~= actor[1]) or (filters.faction and filters.faction ~= actor[2]))) then return nil end
        local stateKey = table.concat({key, mode, level, race}, ":")
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

function Scoring:SwapDependsOnWeights(before, after, weights, operations, ranks, scenario, race, level, ordinary, baselines)
    if not scenario.weight_alternatives then return false end
    ordinary = ordinary or Scoring.ScoreLoadout(after, weights, operations, ranks, scenario, race, level)
        - Scoring.ScoreLoadout(before, weights, operations, ranks, scenario, race, level)
    if ordinary == 0 then return false end
    for index, changes in ipairs(scenario.weight_alternatives) do
        local alternative = copy(weights)
        for stat, value in pairs(changes) do alternative[stat] = value end
        local baseline = baselines and baselines[index]
        if baseline == nil then
            baseline = Scoring.ScoreLoadout(before, alternative, operations, ranks, scenario, race, level)
            if baselines then baselines[index] = baseline end
        end
        local delta = Scoring.ScoreLoadout(after, alternative, operations, ranks, scenario, race, level) - baseline
        if ordinary * delta < -0.000001 then return true, delta end
    end
    return false
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
        and not state.scenario.hit_curves and not (state.scenario.caps and state.scenario.caps.hit_percent) then return true end
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
    if (target == 16 or target == 17) and not (state.scenario.form_attack_period and state.level >= (state.scenario.form_min_level or 10))
        and (state.weights.dps or 0) > 0 and #(state.profile.unresolved or {}) > 0 then
        -- An ordinary proc estimate already uses the affected weapon's swing
        -- period. Specific active talent interactions are checked above.
        local preset = state.scenario.effect_benchmark
        if preset then
            for _, piece in pairs({incoming, first, offHand}) do
                for _, rule in ipairs(piece and piece.effect_rules or {}) do
                    if rule.trigger == "weapon_hit" and rule.rates and rule.rates[preset.index] > 0 then return false end
                end
            end
        end
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
        if state.scenario.weight_alternatives then state.alternativeBaselines = {} end
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
    local delta = total - state.baseline
    local _, weightReversal = self:SwapDependsOnWeights(state.gear, proposal, state.weights,
        state.profile.operations, state.ranks, state.scenario, state.race, state.level, delta, state.alternativeBaselines)
    return {
        delta = delta,
        roleDelta = score(state, proposal, roleWeights) - state.roleBaseline,
        roleDisplaced = math.max(0, state.roleBaseline - score(state, without, roleWeights)),
        effects = swapEffects(state, effects, state.baselineEffects, sets, state.baselineSets),
        contributions = self:StatDifferences(state.baselineBreakdown, breakdown),
        conditional = conditional or weightReversal ~= nil or state.uncertain or incoming.uncertain
            or dependsOnUnmodeledCombat(state, incoming, target, slot),
        weightReversal = weightReversal,
        proposal = proposal,
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
