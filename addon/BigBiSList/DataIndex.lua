local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local PHASE_ORDER = { "PR", "T4", "T5", "T6", "ZA", "SWP" }
local PHASE_DISPLAY = {
    PR = "Pre-Raid",
    T4 = "Phase 1",
    T5 = "Phase 2",
    T6 = "Phase 3",
    ZA = "Phase 4",
    SWP = "Phase 5",
}

local SLOT_ORDER = {
    "Head", "Neck", "Shoulder", "Back", "Chest", "Wrist",
    "Hands", "Waist", "Legs", "Feet", "Ring", "Trinket",
    "Main Hand", "Off Hand", "Two Hand", "Dual Wield",
    "Ranged", "Idol", "Totem", "Libram", "Relic",
}

local SOURCE_TYPE_LABELS = {
    all = "All sources",
    drop = "Drops",
    quest = "Quests",
    vendor = "Vendors",
    crafted = "Crafted",
    pvp = "PvP",
    token_turnin = "Token turn-ins",
    world_drop = "World drops",
    unknown = "Unknown",
}

local RANK_GROUP_ORDER = {
    bis = 1,
    situational = 2,
    option = 3,
}

BigBiSList.phaseOrder = PHASE_ORDER
BigBiSList.phaseDisplay = PHASE_DISPLAY
BigBiSList.slotOrder = SLOT_ORDER

local function lower(value)
    return string.lower(tostring(value or ""))
end

local function containsText(value, search)
    if not search or search == "" then
        return true
    end
    return string.find(lower(value), lower(search), 1, true) ~= nil
end

local function tableHasAnyEnabled(values)
    if type(values) ~= "table" then
        return false
    end

    for _, value in pairs(values) do
        if value then
            return true
        end
    end
    return false
end

local function addUnique(list, seen, value)
    if value == nil or value == "" or seen[value] then
        return
    end
    seen[value] = true
    table.insert(list, value)
end

local function sortedKeys(values)
    local result = {}
    for key in pairs(values) do
        table.insert(result, key)
    end
    table.sort(result)
    return result
end

local function phaseIndex(phaseKey)
    for index, key in ipairs(PHASE_ORDER) do
        if key == phaseKey then
            return index
        end
    end
    return 999
end

local function slotIndex(slotName)
    for index, name in ipairs(SLOT_ORDER) do
        if name == slotName then
            return index
        end
    end
    return 999
end

local function ensurePath(root, key)
    root[key] = root[key] or {}
    return root[key]
end

local function getPrimarySource(item)
    if not item then
        return nil
    end
    if item.primary_source then
        return item.primary_source
    end
    if item.sources and item.sources[1] then
        return item.sources[1]
    end
    return nil
end

local function getSourceType(item)
    local source = getPrimarySource(item)
    if source and source.type then
        return source.type
    end
    return "unknown"
end

local function getSourceZone(item)
    local source = getPrimarySource(item)
    if source and source.zone and source.zone ~= "" then
        return source.zone
    end
    return nil
end

local function getSourceSide(item)
    local source = getPrimarySource(item)
    if source and source.side and source.side ~= "" then
        return source.side
    end
    return nil
end

local function getItemName(itemId, item)
    if item and item.name and item.name ~= "" then
        return item.name
    end
    return "Item " .. tostring(itemId)
end

local function buildUse(index, className, specName, phaseKey, slotEntry, itemEntry)
    local itemId = itemEntry.item_id
    local item = index.itemsById[itemId]
    local sourceType = getSourceType(item)
    local zone = getSourceZone(item)

    return {
        class = className,
        spec = specName,
        phase = phaseKey,
        phaseIndex = phaseIndex(phaseKey),
        slot = slotEntry.slot,
        item_id = itemId,
        item = item,
        name = getItemName(itemId, item),
        rank = itemEntry.rank,
        rank_label = itemEntry.rank_label or "Option",
        rank_group = itemEntry.rank_group or "option",
        context = itemEntry.context or "standard",
        note = itemEntry.note,
        source_url = slotEntry.source_url,
        source_summary = item and item.source_summary or "",
        source_type = sourceType,
        source_type_label = SOURCE_TYPE_LABELS[sourceType] or sourceType,
        zone = zone,
        side = getSourceSide(item),
        binding = item and item.binding or "unknown",
        boe = item and item.boe,
        quality = item and item.quality,
    }
end

local function includeByFilter(row, filters)
    filters = filters or {}

    if filters.hideIgnored and filters.ignoredItems and filters.ignoredItems[tostring(row.item_id)] then
        return false
    end

    if filters.search and filters.search ~= "" then
        local found = containsText(row.name, filters.search)
            or containsText(row.slot, filters.search)
            or containsText(row.source_summary, filters.search)
            or containsText(row.rank_label, filters.search)
        if not found then
            return false
        end
    end

    if filters.slots and tableHasAnyEnabled(filters.slots) and not filters.slots[row.slot] then
        return false
    end

    if filters.sourceType and filters.sourceType ~= "all" and row.source_type ~= filters.sourceType then
        return false
    end
    if tableHasAnyEnabled(filters.sourceTypes) and not filters.sourceTypes[row.source_type] then
        return false
    end

    if filters.zone and filters.zone ~= "all" and (row.zone or "Unknown") ~= filters.zone then
        return false
    end
    if tableHasAnyEnabled(filters.zones) and not filters.zones[row.zone or "Unknown"] then
        return false
    end

    if filters.rankGroup and filters.rankGroup ~= "all" and row.rank_group ~= filters.rankGroup then
        return false
    end
    if tableHasAnyEnabled(filters.rankGroups) and not filters.rankGroups[row.rank_group] then
        return false
    end

    local owned = filters.ownedItems and filters.ownedItems[row.item_id]
    if filters.ownedState == "owned" and not owned then
        return false
    elseif filters.ownedState == "missing" and owned then
        return false
    elseif filters.ownedState == "equipped" and owned ~= "equipped" then
        return false
    elseif filters.ownedState == "bag" and owned ~= "bag" then
        return false
    end

    if filters.binding and filters.binding ~= "all" and row.binding ~= filters.binding then
        return false
    end

    if filters.boe == "boe" and row.boe ~= true then
        return false
    elseif filters.boe == "not_boe" and row.boe == true then
        return false
    end

    if filters.faction and filters.faction ~= "all" and row.side and row.side ~= filters.faction then
        return false
    end

    return true
end

local function sortUses(a, b)
    local aRank = RANK_GROUP_ORDER[a.rank_group] or 50
    local bRank = RANK_GROUP_ORDER[b.rank_group] or 50
    if aRank ~= bRank then
        return aRank < bRank
    end
    if (a.rank or 999) ~= (b.rank or 999) then
        return (a.rank or 999) < (b.rank or 999)
    end
    return lower(a.name) < lower(b.name)
end

local function addPlannerReason(reasons, seen, text)
    if not seen[text] then
        seen[text] = true
        table.insert(reasons, text)
    end
end

local function plannerTier(score)
    if score >= 75 then
        return "Core"
    elseif score >= 55 then
        return "High"
    elseif score >= 30 then
        return "Useful"
    end
    return "Opportunistic"
end

local function scorePlannerGroup(group, selectedPhaseKey)
    local selectedIndex = phaseIndex(selectedPhaseKey)
    local score = 0
    local hasCurrent = false
    local hasCurrentBis = false
    local firstFutureBis
    local futureBisCount = 0
    local futureOptionCount = 0
    local lastUsefulIndex = 0
    local reasons = {}
    local reasonSeen = {}

    for _, use in ipairs(group.uses) do
        if use.phaseIndex > lastUsefulIndex and use.phaseIndex < 999 then
            lastUsefulIndex = use.phaseIndex
        end

        if use.phase == selectedPhaseKey then
            hasCurrent = true
            if use.rank_group == "bis" then
                hasCurrentBis = true
            end
        elseif use.phaseIndex > selectedIndex then
            if use.rank_group == "bis" then
                futureBisCount = futureBisCount + 1
                if not firstFutureBis or use.phaseIndex < firstFutureBis then
                    firstFutureBis = use.phaseIndex
                end
            else
                futureOptionCount = futureOptionCount + 1
            end
        end
    end

    if hasCurrentBis then
        score = score + 60
        addPlannerReason(reasons, reasonSeen, "BiS now")
    elseif hasCurrent then
        score = score + 30
        addPlannerReason(reasons, reasonSeen, "Option now")
    elseif firstFutureBis then
        score = score + 35
        addPlannerReason(reasons, reasonSeen, "Future BiS " .. (PHASE_DISPLAY[PHASE_ORDER[firstFutureBis]] or "future phase"))
    end

    score = score + (futureBisCount * 8)
    score = score + (futureOptionCount * 4)

    if futureBisCount > 0 then
        addPlannerReason(reasons, reasonSeen, tostring(futureBisCount) .. " future BiS")
    end
    if futureOptionCount > 0 then
        addPlannerReason(reasons, reasonSeen, tostring(futureOptionCount) .. " future options")
    end

    if lastUsefulIndex > selectedIndex then
        if lastUsefulIndex >= selectedIndex + 2 then
            score = score + 10
        else
            score = score + 5
        end
        addPlannerReason(reasons, reasonSeen, "Useful through " .. (PHASE_DISPLAY[PHASE_ORDER[lastUsefulIndex]] or "future phase"))
    end

    if score > 100 then
        score = 100
    end

    group.priority = score
    group.priorityTier = plannerTier(score)
    group.reasons = reasons
    group.hasCurrent = hasCurrent
    group.hasCurrentBis = hasCurrentBis
    group.lastUsefulPhase = PHASE_ORDER[lastUsefulIndex] or group.bestUse.phase
    group.lastUsefulLabel = PHASE_DISPLAY[group.lastUsefulPhase] or group.lastUsefulPhase
end

function BigBiSList:GetPhaseDisplayName(phaseKey)
    return PHASE_DISPLAY[phaseKey] or tostring(phaseKey or "")
end

function BigBiSList:GetPhaseOrder()
    return PHASE_ORDER
end

function BigBiSList:GetSlotOrder()
    return SLOT_ORDER
end

function BigBiSList:GetSourceTypeLabels()
    return SOURCE_TYPE_LABELS
end

function BigBiSList:GetDataIndex()
    if self.dataIndex then
        return self.dataIndex
    end

    local data = BigBiSListData or {}
    local index = {
        itemsById = {},
        classes = data.classes or {},
        classNames = {},
        specsByClass = {},
        phaseOrder = PHASE_ORDER,
        phaseDisplay = PHASE_DISPLAY,
        sourceTypes = {},
        zones = {},
        lists = {},
        usesByItemId = {},
        enhancement = {
            gems = data.gems or {},
            enchants = data.enchants or {},
            consumables = data.consumables or {},
        },
    }

    local sourceSeen = {}
    local zoneSeen = {}

    for _, item in ipairs(data.items or {}) do
        index.itemsById[item.id] = item
        addUnique(index.sourceTypes, sourceSeen, getSourceType(item))
        addUnique(index.zones, zoneSeen, getSourceZone(item) or "Unknown")
    end

    table.sort(index.sourceTypes)
    table.sort(index.zones)

    for _, classData in ipairs(index.classes) do
        table.insert(index.classNames, classData.name)
        index.specsByClass[classData.name] = classData.specs or {}
    end

    for _, classData in ipairs(data.bis_lists or {}) do
        local className = classData["class"]
        local classLists = ensurePath(index.lists, className)

        for _, specData in ipairs(classData.specs or {}) do
            local specName = specData.spec
            local specLists = ensurePath(classLists, specName)

            for _, phaseData in ipairs(specData.phases or {}) do
                local phaseKey = phaseData.phase
                specLists[phaseKey] = specLists[phaseKey] or {}

                for _, slotEntry in ipairs(phaseData.slots or {}) do
                    table.insert(specLists[phaseKey], slotEntry)

                    for _, itemEntry in ipairs(slotEntry.items or {}) do
                        if itemEntry.item_id then
                            local use = buildUse(index, className, specName, phaseKey, slotEntry, itemEntry)
                            index.usesByItemId[use.item_id] = index.usesByItemId[use.item_id] or {}
                            table.insert(index.usesByItemId[use.item_id], use)
                        end
                    end
                end
            end
        end
    end

    for _, uses in pairs(index.usesByItemId) do
        table.sort(uses, function(a, b)
            if a.class ~= b.class then
                return a.class < b.class
            end
            if a.spec ~= b.spec then
                return a.spec < b.spec
            end
            if a.phaseIndex ~= b.phaseIndex then
                return a.phaseIndex < b.phaseIndex
            end
            return sortUses(a, b)
        end)
    end

    self.dataIndex = index
    return index
end

function BigBiSList:GetItemData(itemId)
    return self:GetDataIndex().itemsById[itemId]
end

function BigBiSList:GetPhaseRows(className, specName, phaseKey, filters)
    local index = self:GetDataIndex()
    local phaseLists = index.lists[className]
        and index.lists[className][specName]
        and index.lists[className][specName][phaseKey]
    local grouped = {}
    local seenBySlot = {}

    if not phaseLists then
        return {}
    end

    for _, slotEntry in ipairs(phaseLists) do
        local slotName = slotEntry.slot
        grouped[slotName] = grouped[slotName] or { slot = slotName, items = {} }
        seenBySlot[slotName] = seenBySlot[slotName] or {}

        for _, itemEntry in ipairs(slotEntry.items or {}) do
            if itemEntry.item_id then
                local use = buildUse(index, className, specName, phaseKey, slotEntry, itemEntry)
                local key = tostring(use.item_id) .. ":" .. tostring(use.rank_group) .. ":" .. tostring(use.context)
                if not seenBySlot[slotName][key] and includeByFilter(use, filters) then
                    seenBySlot[slotName][key] = true
                    table.insert(grouped[slotName].items, use)
                end
            end
        end
    end

    local rows = {}
    for _, slotName in ipairs(SLOT_ORDER) do
        if grouped[slotName] and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, sortUses)
            table.insert(rows, grouped[slotName])
        end
    end

    for _, slotName in ipairs(sortedKeys(grouped)) do
        if slotIndex(slotName) == 999 and #grouped[slotName].items > 0 then
            table.sort(grouped[slotName].items, sortUses)
            table.insert(rows, grouped[slotName])
        end
    end

    return rows
end

function BigBiSList:GetPlannerRows(className, specName, selectedPhaseKey, filters)
    local index = self:GetDataIndex()
    local groups = {}
    local selectedIndex = phaseIndex(selectedPhaseKey)

    for itemId, uses in pairs(index.usesByItemId) do
        for _, use in ipairs(uses) do
            if use.class == className and use.spec == specName then
                local groupKey = tostring(itemId) .. ":" .. use.slot
                local group = groups[groupKey]
                if not group then
                    group = {
                        item_id = itemId,
                        item = use.item,
                        name = use.name,
                        slot = use.slot,
                        source_summary = use.source_summary,
                        source_type = use.source_type,
                        source_type_label = use.source_type_label,
                        zone = use.zone,
                        binding = use.binding,
                        boe = use.boe,
                        side = use.side,
                        uses = {},
                        phases = {},
                        bestUse = use,
                    }
                    groups[groupKey] = group
                end

                table.insert(group.uses, use)
                group.phases[use.phase] = group.phases[use.phase] or {}
                table.insert(group.phases[use.phase], use)

                if sortUses(use, group.bestUse) then
                    group.bestUse = use
                end
            end
        end
    end

    local rows = {}
    for _, group in pairs(groups) do
        table.sort(group.uses, function(a, b)
            if a.phaseIndex ~= b.phaseIndex then
                return a.phaseIndex < b.phaseIndex
            end
            return sortUses(a, b)
        end)

        scorePlannerGroup(group, selectedPhaseKey)
        group.rank_group = group.bestUse and group.bestUse.rank_group or "option"
        group.rank_label = group.bestUse and group.bestUse.rank_label or "Option"

        if group.priority > 0 and includeByFilter(group, filters) then
            if filters and filters.longevity == "current" and not group.hasCurrent then
                -- excluded below
            elseif filters and filters.longevity == "future" and group.lastUsefulPhase == selectedPhaseKey then
                -- excluded below
            elseif filters and filters.longevity == "long" and phaseIndex(group.lastUsefulPhase) < selectedIndex + 2 then
                -- excluded below
            else
                table.insert(rows, group)
            end
        end
    end

    table.sort(rows, function(a, b)
        if a.priority ~= b.priority then
            return a.priority > b.priority
        end
        if slotIndex(a.slot) ~= slotIndex(b.slot) then
            return slotIndex(a.slot) < slotIndex(b.slot)
        end
        return lower(a.name) < lower(b.name)
    end)

    return rows
end

function BigBiSList:GetEnhancementRows(className, specName, phaseKey)
    local index = self:GetDataIndex()
    local sections = {
        { title = "Gems", rows = {} },
        { title = "Enchants", rows = {} },
        { title = "Consumables", rows = {} },
    }

    for _, gem in ipairs(index.enhancement.gems or {}) do
        if gem["class"] == className and gem.spec == specName and gem.phase == phaseKey then
            table.insert(sections[1].rows, {
                item_id = gem.id,
                name = gem.name,
                detail = (gem.socket_category or "gem") .. (gem.meta and " meta" or ""),
                source_summary = gem.source_summary or "",
            })
        end
    end

    for _, enchant in ipairs(index.enhancement.enchants or {}) do
        if enchant["class"] == className and enchant.spec == specName and enchant.phase == phaseKey then
            table.insert(sections[2].rows, {
                item_id = enchant.id,
                name = enchant.name,
                detail = enchant.slot or "Enchant",
                source_summary = enchant.source_summary or "",
            })
        end
    end

    for _, consumable in ipairs(index.enhancement.consumables or {}) do
        if consumable["class"] == className and consumable.spec == specName and consumable.phase == phaseKey then
            for itemIndex, itemId in ipairs(consumable.items or {}) do
                local item = index.itemsById[itemId]
                local sourceSummary = consumable.source_summaries and consumable.source_summaries[tostring(itemId)] or ""
                table.insert(sections[3].rows, {
                    item_id = itemId,
                    name = consumable.item_names and consumable.item_names[itemIndex] or getItemName(itemId, item),
                    detail = consumable.category_label or consumable.category or "Consumable",
                    source_summary = sourceSummary,
                })
            end
        end
    end

    return sections
end

function BigBiSList:GetTooltipMatches(itemId, selectedClass, selectedSpec)
    local uses = self:GetDataIndex().usesByItemId[itemId] or {}
    local matches = {}

    for _, use in ipairs(uses) do
        table.insert(matches, use)
    end

    table.sort(matches, function(a, b)
        local aSelected = (a.class == selectedClass and a.spec == selectedSpec) and 1 or 0
        local bSelected = (b.class == selectedClass and b.spec == selectedSpec) and 1 or 0
        if aSelected ~= bSelected then
            return aSelected > bSelected
        end
        if a.phaseIndex ~= b.phaseIndex then
            return a.phaseIndex < b.phaseIndex
        end
        if a.class ~= b.class then
            return a.class < b.class
        end
        if a.spec ~= b.spec then
            return a.spec < b.spec
        end
        return slotIndex(a.slot) < slotIndex(b.slot)
    end)

    return matches
end
