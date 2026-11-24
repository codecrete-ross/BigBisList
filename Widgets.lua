local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local Widgets = {}
BigBiSList.Widgets = Widgets

Widgets.Theme = {
    surface = { 0.055, 0.055, 0.065, 0.96 },
    control = { 0.09, 0.09, 0.105, 0.96 },
    hover = { 0.15, 0.15, 0.17, 0.98 },
    pressed = { 0.065, 0.065, 0.075, 1 },
    selected = { 0.18, 0.15, 0.075, 0.98 },
    border = { 0.26, 0.26, 0.29, 1 },
    accent = { 0.92, 0.76, 0.32, 1 },
    bisGold = { 1, 0.82, 0.32, 1 },
    text = { 0.90, 0.90, 0.92, 1 },
    muted = { 0.68, 0.68, 0.72, 1 },
    status = { 0.62, 0.62, 0.66, 1 },
    disabled = { 0.42, 0.42, 0.46, 1 },
}
if BigBiSList.isForever then
    Widgets.Theme.text = { 0.97, 0.96, 0.92, 1 }
    Widgets.Theme.muted = { 0.78, 0.81, 0.86, 1 }
    Widgets.Theme.status = Widgets.Theme.muted
    Widgets.Theme.accent = { 1, 0.82, 0.28, 1 }
end

-- This order is shared with tools/generate_ui_icons.py. Each glyph occupies a
-- padded 32px cell in the addon-owned 256px atlas; no client atlas API is needed.
local ICON_KEYS = {
    "search", "clear", "starOutline", "starFilled", "sortAscending", "sortDescending",
    "chevronLeft", "chevronRight", "chevronDown", "chevronUp", "settings", "filter",
    "details", "check", "bag", "bank", "equipped", "clock", "warning", "info",
    "plus", "minus", "restore", "hide", "menu", "upgradeArrow",
}
local ICON_INDEX = {}
for index, key in ipairs(ICON_KEYS) do ICON_INDEX[key] = index - 1 end

function Widgets:SetIcon(texture, key)
    if not texture then return false end
    local known = ICON_INDEX[key] ~= nil
    local index = ICON_INDEX[key] or ICON_INDEX.info
    local column, row = index % 8, math.floor(index / 8)
    texture:SetTexture("Interface\\AddOns\\BigBiSList\\assets\\ui-icons.tga")
    texture:SetTexCoord(column / 8, (column + 1) / 8, row / 8, (row + 1) / 8)
    texture.iconKey = known and key or "info"
    return known
end

function Widgets:GearAdviceColor(tone)
    if tone == "gain" then return 0.40, 0.96, 0.59 end
    if tone == "future" then return 0.62, 0.81, 1 end
    if tone == "uncertain" then return 1, 0.80, 0.38 end
    if tone == "loss" then return 0.92, 0.66, 0.63 end
    return 0.83, 0.85, 0.88
end

function Widgets:GearIconText(key, text)
    local index = ICON_INDEX[key]
    if not index or not text then return text end
    local x, y = index % 8 * 32, math.floor(index / 8) * 32
    return string.format("|TInterface\\AddOns\\BigBiSList\\assets\\ui-icons.tga:13:13:0:0:256:256:%d:%d:%d:%d|t %s",
        x, x + 32, y, y + 32, text)
end

function Widgets:GearAdviceText(view)
    local icon = view.tone == "gain" and "upgradeArrow" or view.tone == "future" and "clock"
    return self:GearIconText(icon, view.today)
end

local gearStats = {
    stamina = {"Stamina", "health", "Stam"}, strength = {"Strength", "strength", "Str"},
    agility = {"Agility", "agility", "Agi"}, intellect = {"Intellect", "intellect", "Int"},
    spirit = {"Spirit", "spirit"}, healing_power = {"Healing Power", "healing"},
    spell_power = {"Spell Power", "spell power", "SP"}, spell_damage = {"Spell Damage", "spell damage"},
    dps = {"Weapon DPS", "weapon DPS", "DPS"}, ranged_dps = {"Ranged DPS", "ranged DPS"}, wand_dps = {"Wand DPS", "wand DPS"},
    attack_power = {"Attack Power", "AP"}, ranged_attack_power = {"Ranged Attack Power", "ranged AP", "RAP"},
    mp5 = {"Mana per 5 sec", "mana regen", "MP5"}, hp5 = {"Health per 5 sec", "health regen", "HP5"},
    expertise = {"Expertise", "expertise"}, proc_dps = {"Damage procs", "proc damage"}, proc_hps = {"Healing and absorbs", "proc healing"},
    defense = {"Defense", "defense", "Def"}, block_value = {"Block Value", "block value", "BV"},
}

local function swapStatName(stat, style)
    local names = gearStats[stat]
    if names then return names[style] or names[2] or names[1] end
    local name = stat:gsub("_percent$", ""):gsub("_", " ")
    return style == 1 and name:gsub("%f[%a]%l", string.upper) or name
end

local function scoredChanges(explanation)
    if explanation.statChanges then return explanation.statChanges end
    local stats, included = {}, {}
    local function add(stat)
        if included[stat] or stat == "weapon_min_damage" or stat == "weapon_max_damage" or stat == "weapon_speed" then return end
        included[stat] = true
        local amount, points = explanation.raw[stat] or 0, explanation.points[stat] or 0
        if math.abs(amount) >= 0.000001 or math.abs(points) >= 0.000001 then
            stats[#stats + 1] = {stat = stat, amount = amount, points = points, scored = explanation.points[stat] ~= nil}
        end
    end
    for stat in pairs(explanation.raw) do add(stat) end
    for stat in pairs(explanation.points) do add(stat) end
    table.sort(stats, function(a, b)
        if math.abs(a.points) ~= math.abs(b.points) then return math.abs(a.points) > math.abs(b.points) end
        return a.stat < b.stat
    end)
    explanation.statChanges = stats
    return stats
end

local function tradeoff(explanation, delta)
    local gains, losses, totalGains, totalLosses = {}, {}, 0, 0
    for _, change in ipairs(scoredChanges(explanation)) do
        local points = change.points
        if points > 0.000001 then
            gains[#gains + 1], totalGains = change, totalGains + points
        elseif points < -0.000001 then
            losses[#losses + 1], totalLosses = change, totalLosses - points
        end
    end
    local winning, opposing = gains, totalLosses
    if delta < 0 then winning, opposing = losses, totalGains end
    local more = #winning > 1 and math.abs(winning[1].points) <= opposing
    return gains, losses, more
end

local function mechanicReason(explanation, delta)
    local mechanic = explanation.mechanic
    if not mechanic then return explanation.cap end
    local featured
    for _, change in ipairs(mechanic.changes) do
        if change.gained == (delta > 0) then
            if featured then return mechanic.kind == "set" and "Set bonuses tip the swap" or "Item effects tip the swap" end
            featured = change
        end
    end
    if not featured then return end
    if mechanic.kind == "set" then return (featured.gained and "Completes " or "Breaks ") .. featured.name, "Set bonus tips the swap" end
    if featured.retained then return featured.name .. " tips the swap", "Item effect tips the swap" end
    return (featured.gained and "Gains " or "Loses ") .. featured.name, "Item effect tips the swap"
end

local function numberText(amount, signed)
    if math.abs(amount) < 0.001 and amount ~= 0 then return (amount < 0 and "−" or signed and "+" or "") .. "<0.001" end
    local text = string.format("%.3f", math.abs(amount)):gsub("0+$", ""):gsub("%.$", "")
    return (amount < 0 and "−" or signed and amount > 0 and "+" or "") .. text
end

local function statAmount(change, signed)
    local pct = (change.stat:find("_percent$", 1) or change.stat == "expertise") and "%" or ""
    return numberText(signed and change.amount or math.abs(change.amount), signed) .. pct .. " " .. swapStatName(change.stat, 1)
end

local function joinBenefits(changes, first, last)
    local names = {}
    for index = first, math.min(last, #changes) do
        local change = changes[index]
        if change.amount * change.points <= 0 then return end
        names[#names + 1] = statAmount(change, false)
    end
    if #names > 1 then
        local lastName = table.remove(names)
        names[#names] = names[#names] .. " and " .. lastName
    end
    return table.concat(names, ", ")
end

function Widgets:SwapDecisionSummary(item, swap)
    local result = swap and (swap.forecast or swap)
    if result and result.status == "best_owned" then
        if result.conditional then return self:DecisionReason(item, result) end
        result = result.equipSwap
    end
    if not result or result.delta == nil then return end
    if result.conditional then return self:DecisionReason(item, result) end
    local evidence = BigBiSList.ForeverGearRating:GetSwapExplanation(result, true)
    if not evidence then return end
    local mechanic = mechanicReason(evidence, result.delta)
    if mechanic then return mechanic end
    if result.delta == 0 then return "Both setups score equally." end
    local gains, losses = tradeoff(evidence, result.delta)
    local gain, loss = gains[1], losses[1]
    if not gain or not loss then
        local changes = gain and gains or losses
        local text = joinBenefits(changes, 1, 3)
        if text and text ~= "" then return (gain and "Gains " or "Gives up ") .. text .. "." end
        return
    end
    local gained, lost = joinBenefits(gains, 1, 3), joinBenefits(losses, 1, 2)
    if not gained or not lost then return end
    -- Explain a close trade in the same units as the item tooltip. Use the
    -- contribution ratio only to choose words, never to decide the winner.
    if result.delta > 0 and #gains > 1 and #gains <= 4 and #losses <= 2
        and gain.points >= -loss.points * 0.8 and gain.points <= -loss.points then
        local rest = joinBenefits(gains, 2, 4)
        if rest then
            local extraLoss = losses[2] and (", even with " .. statAmount(losses[2], false) .. " lost") or ""
            local verb = #gains == 2 and " puts" or " put"
            return statAmount(gain, false) .. " nearly offsets losing " .. statAmount(loss, false)
                .. ". The extra " .. rest .. verb .. " the swap ahead" .. extraLoss .. "."
        end
    end
    if #gains > 3 or #losses > 2 then return "Gains include " .. gained .. ". Losses include " .. lost .. "." end
    if result.delta > 0 then return "Gaining " .. gained .. " outweighs losing " .. lost .. "." end
    return "Losing " .. lost .. " outweighs gaining " .. gained .. "."
end

local function ordinal(rank)
    local last = rank % 10
    local suffix = rank % 100 >= 11 and rank % 100 <= 13 and "th"
        or last == 1 and "st" or last == 2 and "nd" or last == 3 and "rd" or "th"
    return rank .. suffix
end

-- My Gear asks what to do with a physical slot. The Guide rank describes
-- the published pool and can coexist with any personal equip decision.
function Widgets:EquippedAdvice(data, view, spec, player)
    local rating, placement = BigBiSList.ForeverGearRating, data.stat_rank
    local swap, action = data.gearSwap, data.gearAction
    view.swap, view.evidence = swap, nil
    local scoped = player and player.spec ~= spec and (" for " .. spec) or ""
    local today, compact, why
    if action then
        local incoming, bank = {}, false
        for _, piece in ipairs(action.incoming) do
            bank = bank or piece.state == "bank"
            incoming[#incoming + 1] = piece.name .. (piece.state == "bank" and " from bank" or " from bags")
        end
        today = (bank and "Get " or "Equip ") .. table.concat(incoming, " + ") .. scoped
        compact = bank and "Get from bank" or "Equip from bags"
        view.swap, view.tone = action, "gain"
    elseif data.disabledReason then today = data.disabledReason
    elseif not data.item_id then today = data.overlay or "Empty slot"
    elseif not data.gearRated and not placement then today, compact = "Checking your gear…", "Checking gear"
    elseif swap and swap.blocker then
        today, compact = rating:GuideItemDependency(swap, data), "Check item"
    elseif swap and swap.conditional then
        why = self:DecisionReason(placement and placement.item, swap)
        if data.gearEffect and (not why or why == "depends on the fight") then why = data.gearEffect end
        today, compact = "Compare for " .. spec, "Compare"
        view.tone = "uncertain"
    elseif swap and (swap.status == "best_owned" or swap.status == "equipped" or swap.delta == 0) then
        today, compact = "Keep equipped" .. scoped, "Keep equipped"
        if swap.status == "best_owned" then
            local kind = placement and placement.item and placement.item.armor_type == "Shield" and "shield"
                or swap.slot == "Neck" and "neck" or swap.slot == "Hands" and "gloves"
            why = kind and ("Best " .. kind .. " you own for " .. spec .. ".")
                or ("Part of your best owned setup for " .. spec .. ".")
        elseif swap.delta == 0 then why = "Both setups score equally." end
    elseif swap and swap.delta and swap.delta < 0 then
        today, compact = "Compare owned gear", "Compare"
        why = self:DecisionReason(placement and placement.item, swap)
    else
        today = placement and placement.rank and ("Guide preview for " .. spec)
            or (placement and rating:Label(placement, "compact")) or "Gear comparison unavailable"
    end
    view.today, view.action, view.tileAction, view.comparisonDetail = today, today, compact, why
    if swap and placement and player and placement.level and player.level ~= placement.level then
        view.personalScope = "Owned comparison at level " .. player.level .. "."
    end
    if placement and placement.rank then
        local scope = rating:ScopeLabel(placement)
        view.strength = scope .. " Guide · " .. (placement.tied and "Tied for " or "") .. ordinal(placement.rank)
        view.compact = "Guide #" .. placement.rank
        if placement.projected or placement.conditional or placement.conditional_tie then
            view.rankNote = placement.projected and "Guide rank estimated from this item's observed stats."
                or "Unverified item effects can change this Guide rank."
        end
    elseif placement then
        view.strength = rating:Label(placement, nil, true)
    end
    return view
end

function Widgets:DecisionReason(item, swap)
    local result = swap and (swap.forecast or swap)
    if not result then return end
    if result.status == "loading" or result.status == "unavailable" then
        return result.blocker and result.blocker.name
    end
    local rating = BigBiSList.ForeverGearRating
    local explanation = rating and rating.GetSwapExplanation and rating:GetSwapExplanation(result, true)
    if result.conditional then
        local reversal = rating and rating.WeightReversalReason and rating:WeightReversalReason(result)
        if reversal then return reversal end
        if result.unscoredHolyBlock then return "Holy damage on block" end
        if explanation and explanation.unknown and explanation.unknown[1] then
            return "Unpriced effect · " .. explanation.unknown[1], "Unpriced effect"
        end
        if result.buildUnavailable then return "uses default spec weights" end
        if result.estimatedEffects then return "depends on effect uptime" end
        return "depends on the fight"
    end
    if result.status == "empty" then return "fills an empty slot" end
    if result.status == "best_owned" then
        if result.equipSwap then
            local names = {}
            for _, old in ipairs(result.equipSwap.replacements or {}) do names[#names + 1] = old.name end
            return names[1] and ("replaces " .. table.concat(names, " + ")) or "fills an empty slot"
        end
        if item and item.armor_type == "Shield" then return "Best shield you own" end
        return "Best you own for this slot"
    end
    if result.delta == 0 then return "same score" end
    if explanation then
        local reason, short = mechanicReason(explanation, result.delta)
        if reason then return reason, short end
    end
    local previous = result.replacements or {}
    if (result.delta or 0) < 0 and result.weaponSetup and (#previous > 1 or previous[1] and previous[1].facts and
        (previous[1].facts.slot == "Two Hand") ~= (item and item.slot == "Two Hand")) then
        local names = {}
        for _, piece in ipairs(result.weaponSetup) do names[#names + 1] = piece.name end
        return "your setup uses " .. table.concat(names, " + ")
    end
    if (result.delta or 0) < 0 and previous[1] and (previous[1].state == "bank" or previous[1].state == "bag") then
        return previous[1].name .. (previous[1].state == "bank" and " in your bank" or " in your bags")
    end
    if explanation then
        local gains, losses, extra = tradeoff(explanation, result.delta)
        local win, lose = gains[1], losses[1]
        local more = win and swapStatName(win.stat, 2)
        local less = lose and swapStatName(lose.stat, 2)
        local gainText = win and ("+" .. swapStatName(win.stat, 3))
        local lossText = lose and ("−" .. swapStatName(lose.stat, 3))
        if extra then
            if result.delta > 0 then
                more = more .. " and " .. swapStatName(gains[2].stat, 2)
                gainText = gainText .. " +" .. swapStatName(gains[2].stat, 3)
            else
                less = less .. " and " .. swapStatName(losses[2].stat, 2)
                lossText = lossText .. " −" .. swapStatName(losses[2].stat, 3)
            end
        end
        if more and less then return "More " .. more .. ", less " .. less, gainText .. " / " .. lossText end
        if more then return win.amount > 0 and statAmount(win, true) or ("More " .. more), gainText end
        if less then return "Less " .. less, lossText end
    end
    if result.estimatedEffects then return "includes an estimated effect" end
    if (result.delta or 0) < 0 and previous[1] then return previous[1].name .. " is stronger" end
end

function Widgets:SwapExplanationLines(swap, selected, detail)
    local result = swap and (swap.forecast or swap)
    if result and result.status == "best_owned" then result = result.equipSwap end
    if not result or result.delta == nil or not result.replacements then return end
    local trace = result.comparisonTrace
    local rating = BigBiSList.ForeverGearRating
    local evidence = rating:GetSwapExplanation(result, true)
    local lines, names = {}, {}
    for _, old in ipairs(result.replacements) do
        local slot = selected and old.slot and (" (" .. old.slot .. ")") or ""
        names[#names + 1] = old.name .. slot .. (old.state == "bank" and " (bank)" or old.state == "bag" and " (bags)" or "")
    end
    local reference = selected and "Selected reference" or trace and trace.reference == "equipped" and "Equipped" or "Best owned"
    local basis = rating:GetSwapBasisLabel(result.basis)
    if result.conditional then basis = basis .. " · Conditional" end
    lines[1] = reference .. " · " .. (names[1] and table.concat(names, " + ") or "Empty slot")
    local level = trace and (" · Lv " .. trace.context.level) or ""
    lines[2] = basis .. level .. " · " .. numberText(result.delta, true) .. " score points"
    local reversal, why = rating:WeightReversalReason(result)
    if reversal then
        lines[#lines + 1] = reversal .. " · " .. numberText(result.weightReversal, true) .. " score points"
        if why then lines[#lines + 1] = why end
    end
    if result.estimatedEffects then lines[#lines + 1] = "Includes estimated item effects" end
    if detail then
        for _, effect in ipairs(result.effects or {}) do
            local shown
            for _, change in ipairs(evidence and evidence.sets or {}) do
                if effect == change.name .. (change.gained and " gained" or " lost") then shown = true; break end
            end
            if not shown then
                lines[#lines + 1] = effect:gsub(" %(([+-][%d.]+)%)$", " (%1 score points)")
            end
        end
    end
    if not evidence then return lines end
    local reason = mechanicReason(evidence, result.delta)
    if reason then lines[#lines + 1] = reason end
    for _, change in ipairs(evidence.sets) do
        local label = (change.gained and "Completes " or "Breaks ") .. change.name
        if label ~= reason then lines[#lines + 1] = label end
    end
    for _, effect in ipairs(evidence.unknown or {}) do lines[#lines + 1] = "Unpriced effect · " .. effect end
    if detail then
        for _, change in ipairs(scoredChanges(evidence)) do
            local amount, points = change.amount, change.points
            if math.abs(amount) < 0.000001 then amount = 0 end
            if math.abs(points) < 0.000001 then points = 0 end
            local stat = amount ~= 0 and statAmount(change, true) or swapStatName(change.stat, 1) .. " contribution"
            if amount * points < 0 then
                lines[#lines + 1] = stat
                stat = swapStatName(change.stat, 1) .. " contribution"
            end
            lines[#lines + 1] = change.scored and (stat .. " (" .. numberText(points, true) .. " score points)") or stat
        end
    else
        local add, remove = {}, {}
        for _, change in ipairs(scoredChanges(evidence)) do
            if math.abs(change.amount) >= 0.000001 then
                local parts = change.amount > 0 and add or remove
                parts[#parts + 1] = statAmount(change, false)
            end
        end
        if #add > 0 then lines[#lines + 1] = "Gains " .. table.concat(add, ", ") end
        if #remove > 0 then lines[#lines + 1] = "Gives up " .. table.concat(remove, ", ") end
        local gains, losses, extra = tradeoff(evidence, result.delta)
        local winners = result.delta > 0 and gains or losses
        if extra and not reason then
            local names = {}
            for index = 2, #winners do
                if index <= 3 then names[#names + 1] = swapStatName(winners[index].stat, 1) end
            end
            lines[#lines + 1] = table.concat(names, " and ") .. (result.delta > 0 and " help tip the swap." or " also weigh against the swap.")
        end
    end
    return lines
end

function Widgets:AddGearAdviceLines(tooltip, service, view, spec, summary)
    local verdict = self:GearAdviceText(view)
    for _, line in ipairs(service:LevelingPresentationLines(view, true)) do
        local r, g, b = 0.83, 0.85, 0.88
        if line == verdict then
            r, g, b = self:GearAdviceColor(view.tone)
            if spec then line = spec .. " — " .. line end
        elseif line == view.strength then
            if view.grade and view.grade > 0 then r, g, b = self:GetRankColor(view.grade)
            else r, g, b = 0.93, 0.93, 0.96 end
        end
        if not summary or line ~= view.evidence then tooltip:AddLine(line, r, g, b, true) end
    end
end

local function appendScript(frame, event, callback)
    if frame.HookScript then
        frame:HookScript(event, callback)
    else
        local previous = frame.GetScript and frame:GetScript(event)
        frame:SetScript(event, function(self, ...)
            if previous then previous(self, ...) end
            callback(self, ...)
        end)
    end
end

local function hideOwnedTooltip(frame)
    if GameTooltip and (not GameTooltip.IsOwned or GameTooltip:IsOwned(frame)) then
        GameTooltip:Hide()
    end
end

function Widgets:BindTooltip(frame, callback)
    frame.__bigBisTooltip = callback
    if frame.__bigBisTooltipBound then return end
    frame.__bigBisTooltipBound = true
    appendScript(frame, "OnEnter", function(self)
        if self.SetHovered then self:SetHovered(true) end
        Widgets:ShowBoundTooltip(self)
    end)
    appendScript(frame, "OnLeave", function(self)
        if self.SetHovered then self:SetHovered(false) end
        hideOwnedTooltip(self)
    end)
    appendScript(frame, "OnHide", function(self)
        if self.SetHovered then self:SetHovered(false) end
        hideOwnedTooltip(self)
    end)
end

function Widgets:ShowBoundTooltip(owner)
    local content = owner.__bigBisTooltip
    if not content or not GameTooltip then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    local text = content
    if type(content) == "function" then text = content(owner, GameTooltip) end
    if type(text) == "string" then GameTooltip:AddLine(text, 0.90, 0.90, 0.92, true) end
    GameTooltip:Show()
end

local dropdownCounter = 0
local DROPDOWN_LIST_BASE_LEVEL = 1000

local function resolveDropdownOwner(owner)
    if type(owner) == "string" and _G then
        return _G[owner]
    end
    return owner
end

local function isBigBisDropdownOwner(owner)
    owner = resolveDropdownOwner(owner)
    return type(owner) == "table" and owner.__bigBisListDropdown == true
end

local function restoreDropdownList(listFrame)
    local state = listFrame and listFrame.__bigBisListDropdownState
    if not state then
        return
    end
    if state.strata and listFrame.SetFrameStrata then
        listFrame:SetFrameStrata(state.strata)
    end
    if state.level and listFrame.SetFrameLevel then
        listFrame:SetFrameLevel(state.level)
    end
    if state.mouseEnabled ~= nil and listFrame.EnableMouse then
        listFrame:EnableMouse(state.mouseEnabled)
    end
    listFrame.__bigBisListDropdownState = nil
end

local function prepareDropdownList(listFrame, listIndex, explicitOwner)
    if not listFrame then
        return
    end

    if listFrame.IsShown and not listFrame:IsShown() then
        restoreDropdownList(listFrame)
        return
    end

    local requestedOwner = resolveDropdownOwner(explicitOwner)
    local actualOwner = resolveDropdownOwner(listFrame.dropdown or (_G and _G.UIDROPDOWNMENU_OPEN_MENU))
    if requestedOwner and actualOwner and requestedOwner ~= actualOwner then
        restoreDropdownList(listFrame)
        return
    end
    local owner = actualOwner or requestedOwner
    if not isBigBisDropdownOwner(owner) then
        restoreDropdownList(listFrame)
        return
    end

    if not listFrame.__bigBisListDropdownState then
        local mouseEnabled
        if listFrame.IsMouseEnabled then
            mouseEnabled = listFrame:IsMouseEnabled()
        end
        listFrame.__bigBisListDropdownState = {
            strata = listFrame.GetFrameStrata and listFrame:GetFrameStrata() or nil,
            level = listFrame.GetFrameLevel and listFrame:GetFrameLevel() or nil,
            mouseEnabled = mouseEnabled,
        }
    end

    if listFrame.SetFrameStrata then
        listFrame:SetFrameStrata("FULLSCREEN_DIALOG")
    end
    local previousLevel = listFrame.GetFrameLevel and listFrame:GetFrameLevel() or 0
    if listFrame.SetFrameLevel then
        listFrame:SetFrameLevel(math.max(previousLevel or 0, DROPDOWN_LIST_BASE_LEVEL + (listIndex or 1)))
    end
    if listFrame.EnableMouse then
        listFrame:EnableMouse(true)
    end
end

local function installDropdownListHook(listFrame, listIndex)
    if not listFrame then
        return
    end
    if not listFrame.__bigBisListDropdownListHooked and listFrame.HookScript then
        listFrame.__bigBisListDropdownListHooked = true
        listFrame:HookScript("OnShow", function(shownList)
            prepareDropdownList(shownList, listIndex)
        end)
        listFrame:HookScript("OnHide", function(hiddenList)
            restoreDropdownList(hiddenList)
        end)
    end
end

local function prepareDropdownLists(owner)
    local maxLevels = tonumber(UIDROPDOWNMENU_MAXLEVELS) or 2
    maxLevels = math.max(2, maxLevels)
    for listIndex = 1, maxLevels do
        local listFrame = _G and _G["DropDownList" .. listIndex]
        installDropdownListHook(listFrame, listIndex)
        if owner then
            prepareDropdownList(listFrame, listIndex, owner)
        end
    end
end

local function restoreDropdownLists()
    local maxLevels = math.max(2, tonumber(UIDROPDOWNMENU_MAXLEVELS) or 2)
    for listIndex = 1, maxLevels do
        restoreDropdownList(_G and _G["DropDownList" .. listIndex])
    end
end

function Widgets:CloseDropdownMenus()
    if type(CloseDropDownMenus) == "function" then
        CloseDropDownMenus()
        restoreDropdownLists()
        return true
    end

    local closed = false
    local maxLevels = math.max(2, tonumber(UIDROPDOWNMENU_MAXLEVELS) or 2)
    for listIndex = 1, maxLevels do
        local listFrame = _G and _G["DropDownList" .. listIndex]
        if listFrame and listFrame.Hide then
            listFrame:Hide()
            closed = true
        end
    end
    restoreDropdownLists()
    return closed
end

local function setBackdrop(frame, bg, border)
    if frame.nativePanel or not frame.SetBackdrop then
        return
    end

    frame:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })

    bg = bg or { 0.04, 0.04, 0.05, 0.94 }
    border = border or { 0.22, 0.22, 0.24, 1 }
    frame:SetBackdropColor(bg[1], bg[2], bg[3], frame.__bigBisStatusBadge and math.min(bg[4] or 1, 0.20) or bg[4])
    frame:SetBackdropBorderColor(border[1], border[2], border[3], frame.__bigBisStatusBadge and 0 or border[4])
end

function Widgets:CreatePanel(name, parent, bg, border, nativeTemplate)
    if BigBiSList.isForever and nativeTemplate then
        local ok, native = pcall(CreateFrame, "Frame", name, parent, nativeTemplate)
        if ok and native then native.nativePanel = true; return native end
    end
    local template = BackdropTemplateMixin and "BackdropTemplate" or nil
    local frame = CreateFrame("Frame", name, parent, template)
    setBackdrop(frame, bg, border)
    return frame
end

function Widgets:SetBackdrop(frame, bg, border)
    setBackdrop(frame, bg, border)
end

function Widgets:CreateLabel(parent, text, template)
    local label = parent:CreateFontString(nil, "OVERLAY", template or "GameFontNormalSmall")
    label:SetText(text or "")
    label:SetJustifyH("LEFT")
    label:SetWordWrap(false)
    return label
end

function Widgets:CreateCheckbox(parent, text, width, onChange)
    local button = CreateFrame("CheckButton", nil, parent, "UICheckButtonTemplate")
    button:SetSize(width or 220, 28)
    for _, getter in ipairs({ "GetNormalTexture", "GetPushedTexture", "GetHighlightTexture", "GetCheckedTexture" }) do
        local texture = button[getter] and button[getter](button)
        if texture then
            texture:ClearAllPoints()
            texture:SetPoint("LEFT", button, "LEFT", 0, 0)
            texture:SetSize(28, 28)
        end
    end
    button.label = self:CreateLabel(button, text)
    button.label:SetPoint("LEFT", button, "LEFT", 30, 0)
    button.label:SetPoint("RIGHT", button, "RIGHT", -2, 0)
    button:SetScript("OnClick", function(control)
        if onChange then onChange(control:GetChecked() == true or control:GetChecked() == 1) end
    end)
    return button
end

function Widgets:CreateWrappedLabel(parent, text, template)
    local label = parent:CreateFontString(nil, "OVERLAY", template or "GameFontNormalSmall")
    label:SetText(text or "")
    label:SetJustifyH("LEFT")
    label:SetWordWrap(true)
    return label
end

function Widgets:MeasureTextHeight(label, minimum)
    local height = minimum or 0
    if label and label.GetStringHeight then
        height = math.max(height, label:GetStringHeight() or 0)
    end
    return height
end

local function textTokens(text)
    local tokens, position = {}, 1
    while position <= #text do
        local rest = string.sub(text, position)
        local token = string.match(rest, "^|c%x%x%x%x%x%x%x%x")
            or string.match(rest, "^|H.-|h.-|h")
            or string.match(rest, "^|T.-|t")
            or string.match(rest, "^|r")
            or string.match(rest, "^||")
        if not token then
            local byte = string.byte(text, position)
            local length = byte >= 240 and 4 or (byte >= 224 and 3 or (byte >= 192 and 2 or 1))
            token = string.sub(text, position, position + length - 1)
        end
        tokens[#tokens + 1] = token
        position = position + #token
    end
    return tokens
end

function Widgets:SetCellText(label, text, maxLines, lineHeight, width)
    text = tostring(text or "")
    maxLines = math.max(1, math.floor(tonumber(maxLines) or 2))
    lineHeight = math.max(1, tonumber(lineHeight) or 14)
    if width then label:SetWidth(math.max(1, width)) end
    label:SetWordWrap(true)
    if label.SetJustifyV then label:SetJustifyV("MIDDLE") end
    if label.SetNonSpaceWrap then label:SetNonSpaceWrap(true) end
    -- Guide picks have fixed-height columns and full text on hover. Let the
    -- font string clip to its bounds without measuring and reflowing each word.
    if label.guideBounds then
        label:SetHeight(maxLines * lineHeight)
        label:SetText(text)
        label.fullText, label.displayedText, label.isTruncated = text, text, false
        label.maxLines, label.lineHeight = maxLines, lineHeight
        return text, false
    end
    label:SetHeight(0)
    local availableHeight = maxLines * lineHeight
    local function fits(value)
        label:SetText(value)
        return not label.GetStringHeight or (label:GetStringHeight() or 0) <= availableHeight + 0.1
    end
    local displayed, truncated = text, not fits(text)
    if truncated then
        local tokens = textTokens(text)
        local low, high, best = 0, #tokens, "..."
        local resetColor = string.find(text, "|c", 1, true) and "|r" or ""
        while low <= high do
            local middle = math.floor((low + high) / 2)
            local prefix = string.gsub(table.concat(tokens, "", 1, middle), "%s+$", "")
            local candidate = prefix .. "..." .. resetColor
            if fits(candidate) then
                best = candidate
                low = middle + 1
            else
                high = middle - 1
            end
        end
        displayed = best
    end
    label:SetText(displayed)
    label:SetHeight(availableHeight)
    label.fullText = text
    label.displayedText = displayed
    label.isTruncated = truncated
    label.maxLines = maxLines
    label.lineHeight = lineHeight
    return displayed, truncated
end

local QUALITY_COLORS = {
    [0] = { 0x9d, 0x9d, 0x9d }, { 0xff, 0xff, 0xff }, { 0x1e, 0xff, 0x00 },
    { 0x00, 0x70, 0xdd }, { 0xa3, 0x35, 0xee }, { 0xff, 0x80, 0x00 },
}

function Widgets:GetRankColor(quality)
    local getColor = GetItemQualityColor or (C_Item and C_Item.GetItemQualityColor)
    local r, g, b
    if getColor then r, g, b = getColor(quality) end
    if r then return r, g, b end
    local fallback = QUALITY_COLORS[quality]
    return fallback[1] / 255, fallback[2] / 255, fallback[3] / 255
end

function Widgets:SetEquippedBiS(frame, active)
    local highlight = frame.bisHighlight
    if not highlight then
        if not active then return end
        local gold = self.Theme.bisGold
        local fill = frame:CreateTexture(nil, "ARTWORK", nil, -2)
        fill:SetPoint("TOPLEFT", frame, "TOPLEFT", 2, -2)
        fill:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -2, 2)
        fill:SetColorTexture(gold[1], gold[2], gold[3], 0.12)
        highlight = { fill }
        for _, side in ipairs({ "TOP", "BOTTOM" }) do
            local y = side == "TOP" and -2 or 2
            local edge = frame:CreateTexture(nil, "OVERLAY")
            edge:SetPoint(side .. "LEFT", frame, side .. "LEFT", 2, y)
            edge:SetPoint(side .. "RIGHT", frame, side .. "RIGHT", -2, y)
            edge:SetHeight(1)
            edge:SetColorTexture(unpack(gold))
            highlight[#highlight + 1] = edge
        end
        for _, side in ipairs({ "LEFT", "RIGHT" }) do
            local x = side == "LEFT" and 2 or -2
            local edge = frame:CreateTexture(nil, "OVERLAY")
            edge:SetPoint("TOP" .. side, frame, "TOP" .. side, x, -2)
            edge:SetPoint("BOTTOM" .. side, frame, "BOTTOM" .. side, x, 2)
            edge:SetWidth(1)
            edge:SetColorTexture(unpack(gold))
            highlight[#highlight + 1] = edge
        end
        frame.bisHighlight = highlight
    end
    for _, texture in ipairs(highlight) do texture:SetShown(active == true) end
end

function Widgets:CreateStatusBadge(parent, text, width, height, bg, border)
    local badge = self:CreatePanel(nil, parent, bg, border)
    badge.__bigBisStatusBadge = true
    setBackdrop(badge, bg, border)
    badge:SetSize(width or 78, height or 18)

    local label = badge:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:SetPoint("LEFT", badge, "LEFT", 4, 0)
    label:SetPoint("RIGHT", badge, "RIGHT", -4, 0)
    label:SetJustifyH("CENTER")
    label:SetWordWrap(false)
    label:SetText(text or "")
    badge.label = label

    function badge:SetIcon(key)
        if not self.icon then
            self.icon = self:CreateTexture(nil, "ARTWORK")
            self.icon:SetSize(14, 14)
            self.icon:SetPoint("LEFT", self, "LEFT", 3, 0)
        end
        label:ClearAllPoints()
        label:SetPoint("LEFT", self, "LEFT", key and 21 or 4, 0)
        label:SetPoint("RIGHT", self, "RIGHT", -4, 0)
        if key then
            Widgets:SetIcon(self.icon, key)
            self.icon:Show()
            label:SetJustifyH("LEFT")
        else
            self.icon:Hide()
            label:SetJustifyH("CENTER")
        end
    end
    function badge:SetTone(background, foreground)
        setBackdrop(self, background, foreground)
        if foreground then
            self.label:SetTextColor(foreground[1], foreground[2], foreground[3], 1)
            if self.icon then self.icon:SetVertexColor(foreground[1], foreground[2], foreground[3], 1) end
        end
    end

    return badge
end

local function paintButton(button)
    local theme = Widgets.Theme
    local disabled = button.disabled
    local background = disabled and theme.surface or (button.pressed and theme.pressed
        or (button.selected and theme.selected or (button.hovered and theme.hover or theme.control)))
    local border = (button.selected or button.focused) and theme.accent or theme.border
    if button.hovered and not button.selected and not button.focused then border = theme.muted end
    if disabled then border = theme.border end
    if button.segmentEdges then
        setBackdrop(button, background, { 0, 0, 0, 0 })
        for side, edge in pairs(button.segmentEdges) do
            edge:SetColorTexture(border[1], border[2], border[3], border[4])
            edge:SetShown(button.selected or button.focused or side == "top" or side == "bottom"
                or (side == "left" and button.segmentFirst) or (side == "right" and button.segmentLast))
        end
        if button.segmentDivider then button.segmentDivider:SetShown(not button.selected and not button.focused) end
    else
        setBackdrop(button, background, border)
    end
    local foreground = disabled and theme.disabled or (button.selected and theme.accent or theme.text)
    if button.label then button.label:SetTextColor(foreground[1], foreground[2], foreground[3], foreground[4]) end
    if button.icon then button.icon:SetVertexColor(foreground[1], foreground[2], foreground[3], foreground[4]) end
    if button.focusRing then
        if button.focused and not disabled then button.focusRing:Show() else button.focusRing:Hide() end
    end
end

function Widgets:CreateTextButton(parent, text, width, height, onClick)
    local button
    if BigBiSList.isForever then
        local ok, native = pcall(CreateFrame, "Button", nil, parent, "UIPanelButtonTemplate")
        if ok and native then button = native; button.nativePanel = true end
    end
    button = button or CreateFrame("Button", nil, parent, BackdropTemplateMixin and "BackdropTemplate" or nil)
    button:SetSize(width or 80, height or 24)
    button:EnableMouse(true)
    button:RegisterForClicks("LeftButtonUp")

    local label = button.GetFontString and button:GetFontString() or button:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    label:ClearAllPoints()
    label:SetPoint("LEFT", button, "LEFT", 6, 0)
    label:SetPoint("RIGHT", button, "RIGHT", -6, 0)
    label:SetJustifyH("CENTER")
    label:SetWordWrap(false)
    label:SetText(text or "")
    button.label = label
    button.focusRing = button:CreateTexture(nil, "OVERLAY")
    button.focusRing:SetColorTexture(0.96, 0.90, 0.68, 1)
    button.focusRing:SetHeight(2)
    button.focusRing:SetPoint("BOTTOMLEFT", button, "BOTTOMLEFT", 3, 3)
    button.focusRing:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -3, 3)
    button.focusRing:Hide()

    local nativeSetEnabled = button.SetEnabled
    function button:SetEnabled(enabled)
        self.disabled = not enabled
        if self.disabled then self.pressed = false end
        if nativeSetEnabled then nativeSetEnabled(self, not self.disabled) end
        paintButton(self)
    end
    function button:SetSelected(selected)
        self.selected = selected and true or false
        paintButton(self)
    end
    function button:SetHovered(hovered)
        self.hovered = hovered and true or false
        if not self.hovered then self.pressed = false end
        paintButton(self)
    end
    function button:SetFocused(focused)
        self.focused = focused and true or false
        paintButton(self)
    end
    button:SetScript("OnEnter", function(self)
        self:SetHovered(true)
    end)
    button:SetScript("OnLeave", function(self)
        self:SetHovered(false)
    end)
    button:SetScript("OnMouseDown", function(self, buttonName)
        self.pressed = buttonName == "LeftButton" and not self.disabled
        paintButton(self)
    end)
    button:SetScript("OnMouseUp", function(self)
        self.pressed = false
        paintButton(self)
    end)
    button:SetScript("OnClick", function(self, buttonName)
        if not self.disabled and buttonName == "LeftButton" and onClick then onClick(self, buttonName) end
    end)
    button:SetScript("OnDisable", function(self)
        self.disabled, self.pressed = true, false
        paintButton(self)
    end)
    button:SetScript("OnEnable", function(self)
        self.disabled = false
        paintButton(self)
    end)
    button:SetScript("OnHide", function(self)
        self.hovered, self.pressed, self.focused = false, false, false
        paintButton(self)
    end)
    paintButton(button)
    return button
end

function Widgets:CreateSegmentedControl(parent, options, onSelect)
    local control = CreateFrame("Frame", nil, parent)
    control:SetHeight(40) -- 28px target, 2px gap, and a reserved 10px caption.
    local measurement = control:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    measurement:Hide()
    control.buttons = {}
    control.buttonsByValue = {}
    for index, option in ipairs(options or {}) do
        local value = option.value
        local button = self:CreateTextButton(control, option.text, option.width, 28, function()
            if onSelect then onSelect(value) end
        end)
        button.value, button.minimumWidth = value, option.width or 28
        button.segmentFirst, button.segmentLast = index == 1, index == #options
        button.label:ClearAllPoints()
        button.label:SetPoint("TOPLEFT", button, "TOPLEFT", 8, 0)
        button.label:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", -8, 0)
        button.label:SetJustifyV("MIDDLE")
        button.segmentEdges = {}
        for _, side in ipairs({ "top", "bottom", "left", "right" }) do
            local edge = button:CreateTexture(nil, "OVERLAY")
            if side == "top" or side == "bottom" then
                local point = side == "top" and "TOP" or "BOTTOM"
                edge:SetPoint(point .. "LEFT", button, point .. "LEFT", 0, 0)
                edge:SetPoint(point .. "RIGHT", button, point .. "RIGHT", 0, 0)
                edge:SetHeight(1)
            else
                local point = side == "left" and "LEFT" or "RIGHT"
                edge:SetPoint("TOP" .. point, button, "TOP" .. point, 0, 0)
                edge:SetPoint("BOTTOM" .. point, button, "BOTTOM" .. point, 0, 0)
                edge:SetWidth(1)
            end
            button.segmentEdges[side] = edge
        end
        if index > 1 then
            button.segmentDivider = button:CreateTexture(nil, "ARTWORK")
            button.segmentDivider:SetPoint("LEFT", button, "LEFT", 0, 0)
            button.segmentDivider:SetSize(1, 16)
            button.segmentDivider:SetColorTexture(unpack(self.Theme.border))
        end
        local caption = control:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        local font, _, flags = caption:GetFont()
        if font then caption:SetFont(font, 10, flags) end
        caption:SetPoint("TOPLEFT", button, "BOTTOMLEFT", 0, -2)
        caption:SetPoint("TOPRIGHT", button, "BOTTOMRIGHT", 0, -2)
        caption:SetHeight(10)
        caption:SetJustifyH("CENTER")
        caption:SetJustifyV("MIDDLE")
        caption:SetWordWrap(false)
        caption:SetTextColor(0.48, 0.70, 0.96, 1)
        caption:Hide()
        button.caption = caption
        if option.tooltip then self:BindTooltip(button, option.tooltip) end
        control.buttons[index], control.buttonsByValue[value] = button, button
        paintButton(button)
    end
    function control:Layout()
        local x = 0
        for _, button in ipairs(self.buttons) do
            local font, size, flags = button.label:GetFont()
            if font then measurement:SetFont(font, size, flags) end
            measurement:SetText(button.label:GetText() or "")
            local textWidth = measurement:GetStringWidth() or 0
            local width = math.max(28, button.minimumWidth, math.ceil(textWidth) + 16)
            if button:GetWidth() ~= width then button:SetWidth(width) end
            button:ClearAllPoints()
            button:SetPoint("TOPLEFT", self, "TOPLEFT", x, 0)
            x = x + width
        end
        if self:GetWidth() ~= x then self:SetWidth(x) end
        return x
    end
    function control:SetSelectedValue(value)
        for _, button in ipairs(self.buttons) do button:SetSelected(button.value == value) end
    end
    function control:SetCaption(value, text)
        local button = self.buttonsByValue[value]
        if button then
            button.caption:SetText(text or "")
            button.caption:SetShown(text ~= nil and text ~= "")
        end
    end
    control:Layout()
    return control
end

function Widgets:CreateUtilityButton(parent, iconKey, size, onClick, tooltip)
    size = math.max(28, tonumber(size) or 28)
    local button = self:CreateTextButton(parent, "", size, size, onClick)
    button.label:Hide()
    button.icon = button:CreateTexture(nil, "ARTWORK")
    button.icon:SetSize(20, 20)
    button.icon:SetPoint("CENTER", button, "CENTER", 0, 0)
    function button:SetIcon(key)
        Widgets:SetIcon(self.icon, key)
        paintButton(self)
    end
    button:SetIcon(iconKey)
    self:BindTooltip(button, tooltip)
    return button
end

function Widgets:CreateIconButton(parent, size, onClick)
    local button = CreateFrame("Button", nil, parent)
    button:SetSize(size or 28, size or 28)
    button:RegisterForClicks("LeftButtonUp", "RightButtonUp")

    local icon = button:CreateTexture(nil, "ARTWORK")
    icon:SetAllPoints()
    icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
    icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    button.icon = icon

    local border = button:CreateTexture(nil, "OVERLAY")
    border:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    border:SetBlendMode("ADD")
    border:SetPoint("CENTER")
    border:SetSize((size or 28) * 1.8, (size or 28) * 1.8)
    border:SetVertexColor(0.8, 0.8, 0.8, 0.35)
    border:Hide()
    button.border = border

    function button:SetHovered(hovered)
        self.hovered = hovered and true or false
        if self.hovered then self.border:Show() else self.border:Hide() end
    end
    button:SetScript("OnEnter", function(self)
        self:SetHovered(true)
    end)
    button:SetScript("OnLeave", function(self)
        self:SetHovered(false)
        hideOwnedTooltip(self)
    end)
    button:SetScript("OnHide", function(self)
        self:SetHovered(false)
        hideOwnedTooltip(self)
    end)
    button:SetScript("OnSizeChanged", function(self, width, height)
        self.border:SetSize((width or 28) * 1.8, (height or width or 28) * 1.8)
    end)
    button:SetScript("OnClick", function(self, buttonName)
        if onClick then
            onClick(self, buttonName)
        end
    end)

    return button
end

function Widgets:CreateDropdown(name, parent, width, getText, getItems, onSelect)
    dropdownCounter = dropdownCounter + 1
    local dropdownName = name or ("BigBiSListDropdown" .. dropdownCounter)
    local frame = CreateFrame("Frame", dropdownName, parent, "UIDropDownMenuTemplate")
    frame.__bigBisListDropdown = true
    UIDropDownMenu_SetWidth(frame, width or 120)

    local function refresh()
        UIDropDownMenu_SetText(frame, getText and getText() or "Select")
    end

    -- The template calls the initializer at registration, before any menu is open.
    local installing = true
    UIDropDownMenu_Initialize(frame, function(_, level)
        if installing then return end
        local items = getItems and getItems() or {}
        for _, item in ipairs(items) do
            local info = UIDropDownMenu_CreateInfo()
            info.text = item.text
            info.value = item.value
            info.checked = item.checked
            info.isNotRadio = item.isNotRadio
            info.keepShownOnClick = item.keepShownOnClick
            info.notCheckable = item.notCheckable
            info.disabled = item.disabled
            info.func = function()
                if onSelect then
                    onSelect(item.value, item)
                end
                refresh()
            end
            UIDropDownMenu_AddButton(info, level)
        end
    end)
    installing = false

    prepareDropdownLists()

    local nativeButton = _G and _G[dropdownName .. "Button"]
    local clickCover = CreateFrame("Button", nil, frame)
    clickCover:SetAllPoints(frame)
    clickCover:EnableMouse(true)
    clickCover:RegisterForClicks("LeftButtonUp")
    -- Keep native outside-click dismissal from closing the menu before OnClick.
    function clickCover:HandlesGlobalMouseEvent(buttonName, event)
        return event == "GLOBAL_MOUSE_DOWN" and buttonName == "LeftButton"
    end
    if clickCover.SetFrameLevel then
        local nativeLevel = nativeButton and nativeButton.GetFrameLevel and nativeButton:GetFrameLevel() or 0
        local frameLevel = frame.GetFrameLevel and frame:GetFrameLevel() or 0
        clickCover:SetFrameLevel(math.max(nativeLevel or 0, frameLevel or 0) + 1)
    end
    clickCover:SetScript("OnClick", function()
        if nativeButton and nativeButton.IsEnabled and not nativeButton:IsEnabled() then
            return
        end

        if type(ToggleDropDownMenu) == "function" then
            ToggleDropDownMenu(1, nil, frame)
        elseif nativeButton and nativeButton.Click then
            nativeButton:Click()
        end

        prepareDropdownLists(frame)
        if C_Timer and C_Timer.After then
            C_Timer.After(0, function()
                prepareDropdownLists(frame)
            end)
        end
    end)

    frame.nativeButton = nativeButton
    frame.clickCover = clickCover
    function frame:RefreshOpenMenu()
        local list = _G and _G.DropDownList1
        if _G and _G.UIDROPDOWNMENU_OPEN_MENU == self and list and list:IsShown() and ToggleDropDownMenu then
            ToggleDropDownMenu(1, nil, self)
            ToggleDropDownMenu(1, nil, self)
            prepareDropdownLists(self)
        end
    end

    frame.Refresh = refresh
    refresh()
    return frame
end

function Widgets:CreateScrollFrame(name, parent)
    local scroll = CreateFrame("ScrollFrame", name, parent, "UIPanelScrollFrameTemplate")
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(1, 1)
    scroll:SetScrollChild(child)
    scroll.child = child

    scroll:SetScript("OnSizeChanged", function(self, width)
        child:SetWidth(width)
    end)

    return scroll, child
end

-- Opt-in for overlays whose chrome should disappear when all content fits.
-- Main list scroll frames keep their normal native scrollbar behavior.
function Widgets:UpdateScrollOverflow(scroll, contentHeight, viewportHeight)
    if not scroll then return false, 0 end
    local child = scroll.child or (scroll.GetScrollChild and scroll:GetScrollChild())
    contentHeight = tonumber(contentHeight) or (child and child.GetHeight and child:GetHeight()) or 0
    viewportHeight = tonumber(viewportHeight) or (scroll.GetHeight and scroll:GetHeight()) or 0
    local maximum = math.max(0, contentHeight - viewportHeight)
    local overflowing = maximum > 0
    local current = tonumber(scroll.GetVerticalScroll and scroll:GetVerticalScroll()) or 0
    local offset = math.min(maximum, math.max(0, current))
    if offset ~= current and scroll.SetVerticalScroll then scroll:SetVerticalScroll(offset) end

    local name = scroll.GetName and scroll:GetName()
    local bar = scroll.ScrollBar or scroll.scrollBar or (name and _G and _G[name .. "ScrollBar"])
    local function setEnabled(frame, enabled)
        if not frame then return end
        if frame.SetEnabled then frame:SetEnabled(enabled)
        elseif enabled and frame.Enable then frame:Enable()
        elseif not enabled and frame.Disable then frame:Disable() end
    end
    if bar then
        if bar.SetMinMaxValues then bar:SetMinMaxValues(0, maximum) end
        if bar.SetValue and (not bar.GetValue or bar:GetValue() ~= offset) then bar:SetValue(offset) end
        setEnabled(bar, overflowing)
        if overflowing then
            if bar.Show then bar:Show() end
        elseif bar.Hide then
            bar:Hide()
        end
        local barName = bar.GetName and bar:GetName()
        local up = bar.ScrollUpButton or scroll.ScrollUpButton
            or (barName and _G and _G[barName .. "ScrollUpButton"])
            or (name and _G and _G[name .. "ScrollUpButton"])
        local down = bar.ScrollDownButton or scroll.ScrollDownButton
            or (barName and _G and _G[barName .. "ScrollDownButton"])
            or (name and _G and _G[name .. "ScrollDownButton"])
        setEnabled(up, overflowing and offset > 0)
        setEnabled(down, overflowing and offset < maximum)
    end
    return overflowing, maximum
end

function Widgets:ClearChildren(parent)
    if not parent then
        return
    end

    local children = { parent:GetChildren() }
    for _, child in ipairs(children) do
        child:Hide()
        child:SetParent(nil)
    end

    local regions = { parent:GetRegions() }
    for _, region in ipairs(regions) do
        if region.Hide then
            region:Hide()
        end
    end
end

function Widgets:CreateSectionHeader(parent, text, yOffset)
    local header = CreateFrame("Frame", nil, parent)
    header:SetHeight(34)
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("RIGHT", parent, "RIGHT", -4, 0)

    local line = header:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(0.55, 0.55, 0.58, 0.45)
    line:SetHeight(1)
    line:SetPoint("BOTTOMLEFT", header, "BOTTOMLEFT", 0, 6)
    line:SetPoint("BOTTOMRIGHT", header, "BOTTOMRIGHT", 0, 6)

    local label = header:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    label:SetPoint("TOPLEFT", header, "TOPLEFT", 8, -2)
    label:SetTextColor(1, 0.82, 0.28, 1)
    label:SetText(text)

    return header, 34
end

function Widgets:CreateItemRow(parent, height)
    local row = self:CreatePanel(nil, parent, Widgets.Theme.surface, { 0, 0, 0, 0 })
    row:SetHeight(height or 38)
    row:EnableMouse(true)

    local selection = row:CreateTexture(nil, "ARTWORK")
    selection:SetAllPoints()
    selection:SetColorTexture(0.88, 0.69, 0.22, 0.11)
    selection:Hide()
    row.selection = selection
    local accent = row:CreateTexture(nil, "OVERLAY")
    accent:SetPoint("TOPLEFT", row, "TOPLEFT", 0, 0)
    accent:SetPoint("BOTTOMLEFT", row, "BOTTOMLEFT", 0, 0)
    accent:SetWidth(2)
    accent:SetColorTexture(0.92, 0.76, 0.32, 1)
    accent:Hide()
    row.selectionAccent = accent

    local separator = row:CreateTexture(nil, "ARTWORK")
    separator:SetHeight(1)
    separator:SetPoint("BOTTOMLEFT", row, "BOTTOMLEFT", 0, 0)
    separator:SetPoint("BOTTOMRIGHT", row, "BOTTOMRIGHT", 0, 0)
    separator:SetColorTexture(0.25, 0.25, 0.29, 0.55)
    row.separator = separator

    local highlight = row:CreateTexture(nil, "ARTWORK")
    highlight:SetAllPoints()
    highlight:SetColorTexture(1, 1, 1, 0.055)
    highlight:Hide()
    row.highlight = highlight

    function row:SetSelected(selected)
        self.selected = selected and true or false
        if self.selected then
            self.selection:Show()
            self.selectionAccent:Show()
        else
            self.selection:Hide()
            self.selectionAccent:Hide()
        end
    end
    function row:SetHovered(hovered)
        self.hovered = hovered and true or false
        if self.hovered then self.highlight:Show() else self.highlight:Hide() end
    end
    row:SetScript("OnEnter", function(self)
        self:SetHovered(true)
    end)
    row:SetScript("OnLeave", function(self)
        self:SetHovered(false)
    end)
    row:SetScript("OnHide", function(self)
        self:SetHovered(false)
        self:SetSelected(false)
    end)

    return row
end
