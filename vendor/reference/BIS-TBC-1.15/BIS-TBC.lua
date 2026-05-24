local eventFrame = CreateFrame("Frame", nil, UIParent)

local PHASE_NAMES = { "Pre-Raid", "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5" }

local SPEC_ABBREV = {
    ["Protection"] = "Prot", ["Retribution"] = "Ret", ["Holy"] = "Holy",
    ["Beast mastery"] = "BM", ["Marksmanship"] = "MM", ["Survival"] = "Surv",
    ["Arcane"] = "Arc", ["Fire"] = "Fire", ["Frost"] = "Frost",
    ["Affliction"] = "Affli", ["Demonology"] = "Demo", ["Destruction"] = "Destro",
    ["Destruction fire"] = "DestF",
    ["Assassination"] = "Assa", ["Combat"] = "Combat", ["Subtlety"] = "Sub",
    ["Arms"] = "Arms", ["Fury"] = "Fury",
    ["Elemental"] = "Ele", ["Enhancement"] = "Enh", ["Restoration"] = "Resto",
    ["Balance"] = "Bala", ["Feral dps"] = "Feral", ["Feral tank"] = "Bear",
    ["Shadow"] = "Shadow",
}

local function specHighlighted(class_name, spec_name)
    return (BISTBCAddon.db.char.highlight_spec.spec_name == spec_name
            and BISTBCAddon.db.char.highlight_spec.class_name == class_name)
end

local function specFiltered(class_name, spec_name)
    if specHighlighted(class_name, spec_name) then
        return false
    end
    if IsAltKeyDown() then
        return false
    end
    if BISTBCAddon.db.char.filter_specs[class_name] then
        return not BISTBCAddon.db.char.filter_specs[class_name][spec_name]
    end
    return false
end

local function classNamesFiltered()
    if BISTBCAddon.db.char.compact_tooltip then
        return true
    end
end

local function getFilteredItem(item)
    local filtered_item = {}
    for ki, spec in ipairs(item) do
        local class_name = spec.class_name
        local spec_name = spec.spec_name
        if (not specFiltered(class_name, spec_name)) then
            table.insert(filtered_item, spec)
        end
    end
    return filtered_item
end

-- Convert ranks format "1 / 3 / 5 / 7 / 7 / -" to verbose "#1 Pre-Raid, #3 Phase 1"
local function formatRanks(ranks_str)
    local parts = { strsplit("/", ranks_str) }
    local result = {}
    for i, rank in ipairs(parts) do
        rank = strtrim(rank)
        if rank ~= "-" and rank ~= "" then
            local phase = PHASE_NAMES[i] or ("Phase " .. i)
            table.insert(result, "#" .. rank .. " " .. phase)
        end
    end
    if #result == 0 then
        return ""
    end
    return table.concat(result, ", ")
end

-- Convert ranks format "1 / 3 / - / 5 / - / -" to compact "1/3/-/5/-/-"
local function formatRanksCompact(ranks_str)
    local parts = { strsplit("/", ranks_str) }
    local result = {}
    for i, rank in ipairs(parts) do
        rank = strtrim(rank)
        if rank == "" then rank = "-" end
        table.insert(result, rank)
    end
    return table.concat(result, "/")
end

local function printSpecLine(tooltip, slot, class_name, spec_name)
    local slot_name = slot.name
    local slot_ranks = slot.ranks
    local prefix = "   "
    if BISTBCAddon.db.char.compact_tooltip then
        prefix = ""
    end
    local left_text = prefix .. "|T" .. BISTBC_spec_icons[class_name][spec_name] .. ":14|t " .. spec_name
    if (slot_name == "off hand" or slot_name == "main hand") then
        left_text = left_text .. " (" .. slot_name .. ")"
    end

    -- Format ranks in new style
    local right_text = formatRanks(slot_ranks)

    local color_r = 1
    local color_g = 0.8
    local color_b = 0
    if specHighlighted(class_name, spec_name) then
        color_r = 0.074
        color_g = 0.964
        color_b = 0.129
    end
    tooltip:AddDoubleLine(left_text, right_text,
            color_r, color_g, color_b,
            color_r, color_g, color_b)
end

local function printClassName(tooltip, class_name)
    tooltip:AddLine(class_name, 1, 0.8, 0)
end

local function OnGameTooltipSetItem(tooltip)
    if not BISTBCAddon.db.char.show_tooltip_bis then return end
    local _, link = tooltip:GetItem();

    if link == nil then
        return ;
    end

    local _, itemId, _, _, _, _, _, _, _, _, _, _, _, _ = strsplit(":", link)

    itemId = tonumber(itemId);
    if BISTBC_items[itemId] == nil then
        return ;
    end
    local item = BISTBC_items[itemId]
    local specs_count = #item
    item = getFilteredItem(item)
    if #item == 0 then return end

    local isCompact = BISTBCAddon.db.char.compact_tooltip

    if isCompact then
        -- Compact mode: "BiS: ClassName SpecAbbr ranks | SpecAbbr ranks"
        -- Group by class
        local classes = {}
        local classOrder = {}
        for _, spec in ipairs(item) do
            local cn = spec.class_name
            if not classes[cn] then
                classes[cn] = {}
                table.insert(classOrder, cn)
            end
            for _, slot in ipairs(spec.slots) do
                local abbr = SPEC_ABBREV[spec.spec_name] or spec.spec_name
                local ranks = formatRanksCompact(slot.ranks)
                local suffix = ""
                if slot.name == "off hand" or slot.name == "main hand" then
                    suffix = " " .. slot.name:sub(1,2):upper()
                end
                local highlighted = specHighlighted(cn, spec.spec_name)
                table.insert(classes[cn], {
                    text = abbr .. suffix .. " " .. ranks,
                    highlighted = highlighted,
                })
            end
        end

        local firstLine = true
        for _, cn in ipairs(classOrder) do
            local specs = classes[cn]
            -- Build spec entries for this class
            local parts = {}
            local anyHighlighted = false
            for _, s in ipairs(specs) do
                if s.highlighted then anyHighlighted = true end
                table.insert(parts, s.text)
            end
            local specText = table.concat(parts, " | ")
            local prefix = firstLine and "BiS: " or "     "
            local left = prefix .. cn
            local color_r, color_g, color_b = 1, 0.8, 0
            if anyHighlighted then
                color_r, color_g, color_b = 0.074, 0.964, 0.129
            end
            tooltip:AddDoubleLine(left, specText,
                color_r, color_g, color_b, color_r, color_g, color_b)
            firstLine = false
        end
    else
        -- Normal mode: verbose with class headers and spec icons
        tooltip:AddLine("BiS for:", 1, 1, 0)
        local previous_class = nil
        for _, spec in ipairs(item) do
            local class_name = spec.class_name
            local spec_name = spec.spec_name
            for _, slot in ipairs(spec.slots) do
                if not (previous_class == class_name) then
                    printClassName(tooltip, class_name)
                    previous_class = class_name
                end
                printSpecLine(tooltip, slot, class_name, spec_name)
            end
        end
    end

    if #item ~= specs_count then
        if #item > 0 then
            tooltip:AddLine(" ", 1, 1, 0)
        end
        tooltip:AddLine("Hold ALT to disable spec filtering", 0.6, 0.6, 0.6)
    end
end

-- ============================================================================
-- BiS Drop Alert System
-- ============================================================================

local PHASE_KEYS = { "PR", "T4", "T5", "T6", "ZA", "SWP" }

local RANK_GLOW_COLORS = {
    [1] = { r = 1.0, g = 0.82, b = 0 },
    [2] = { r = 0.75, g = 0.75, b = 0.78 },
    [3] = { r = 0.80, g = 0.50, b = 0.20 },
}

local function isItemEquipped(itemId)
    for slot = 1, 19 do
        local id = GetInventoryItemID("player", slot)
        if id == itemId then return true end
    end
    return false
end

local function findBisRank(itemId)
    local db = BISTBCAddon.db and BISTBCAddon.db.char
    if not db or not db.class_index or not db.phase_index then return nil end

    local classInfo = BISTBC_classes[db.class_index]
    if not classInfo then return nil end
    local className = classInfo.name
    local specName = classInfo.specs[db.spec_index]
    if not specName then return nil end

    local phaseKey = PHASE_KEYS[db.phase_index]
    if not phaseKey then return nil end

    local bislists = BISTBC_bislists and BISTBC_bislists[className]
    if not bislists then return nil end
    local specData = bislists[specName]
    if not specData then return nil end
    local slots = specData[phaseKey]
    if not slots then return nil end

    for _, slot in ipairs(slots) do
        for rank = 1, 5 do
            local itemEntry = slot[rank]
            if itemEntry then
                local id = type(itemEntry) == "table" and itemEntry.id or itemEntry
                if id == itemId then
                    return rank, slot.slot_name
                end
            end
        end
    end
    return nil
end

-- Drop alert popup frame (created once, reused)
local dropAlertFrame = nil

local function createDropAlertFrame()
    local f = CreateFrame("Frame", "BISTBCDropAlert", UIParent, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f:SetSize(320, 72)
    f:SetPoint("TOP", UIParent, "TOP", 0, -120)
    f:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    f:SetBackdropColor(0.05, 0.05, 0.05, 0.92)
    f:SetBackdropBorderColor(0.8, 0.65, 0, 0.9)
    f:SetFrameStrata("FULLSCREEN_DIALOG")
    f:SetClampedToScreen(true)
    f:Hide()

    -- "BIS DROP" header
    local header = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    header:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -6)
    header:SetFont("Fonts\\FRIZQT__.TTF", 9, "OUTLINE")
    header:SetTextColor(1, 0.82, 0, 0.8)
    header:SetText("BIS DROP")

    -- Item icon
    local iconFrame = CreateFrame("Frame", nil, f)
    iconFrame:SetSize(36, 36)
    iconFrame:SetPoint("LEFT", f, "LEFT", 10, -4)

    local icon = iconFrame:CreateTexture(nil, "ARTWORK")
    icon:SetAllPoints()
    icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    f.icon = icon

    -- Glow around icon
    local glowFrame = CreateFrame("Frame", nil, f)
    glowFrame:SetPoint("CENTER", iconFrame, "CENTER", 0, 0)
    glowFrame:SetSize(72, 72)
    glowFrame:SetFrameLevel(f:GetFrameLevel() + 2)

    local glowTex = glowFrame:CreateTexture(nil, "OVERLAY")
    glowTex:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
    glowTex:SetBlendMode("ADD")
    glowTex:SetAllPoints()
    f.glowFrame = glowFrame
    f.glowTex = glowTex

    -- Item name
    local nameText = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    nameText:SetPoint("TOPLEFT", iconFrame, "TOPRIGHT", 8, 0)
    nameText:SetPoint("RIGHT", f, "RIGHT", -10, 0)
    nameText:SetFont("Fonts\\FRIZQT__.TTF", 13, "")
    nameText:SetJustifyH("LEFT")
    nameText:SetWordWrap(false)
    f.nameText = nameText

    -- Rank + slot
    local rankText = f:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    rankText:SetPoint("TOPLEFT", nameText, "BOTTOMLEFT", 0, -2)
    rankText:SetFont("Fonts\\FRIZQT__.TTF", 11, "")
    f.rankText = rankText

    -- Source
    local sourceText = f:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    sourceText:SetPoint("TOPLEFT", rankText, "BOTTOMLEFT", 0, -1)
    sourceText:SetFont("Fonts\\FRIZQT__.TTF", 10, "")
    sourceText:SetTextColor(0.55, 0.55, 0.55, 1)
    f.sourceText = sourceText

    -- Glow animation via OnUpdate
    f.glowStartTime = 0
    f.glowDuration = 0.8
    f.glowMin = 0.5
    f.glowMax = 1.0
    glowFrame:SetScript("OnUpdate", function(self, elapsed)
        local t = GetTime()
        local progress = ((t - f.glowStartTime) % f.glowDuration) / f.glowDuration
        local alpha = f.glowMin + (f.glowMax - f.glowMin) * (0.5 + 0.5 * math.cos(progress * 2 * math.pi))
        self:SetAlpha(alpha)
    end)

    return f
end

local function showDropAlert(itemId, rank, slotName)
    if not dropAlertFrame then
        dropAlertFrame = createDropAlertFrame()
    end
    local f = dropAlertFrame

    -- Set glow color based on rank
    local color = RANK_GLOW_COLORS[rank]
    if color then
        f.glowTex:SetVertexColor(color.r, color.g, color.b)
        f:SetBackdropBorderColor(color.r, color.g, color.b, 0.9)
        f.rankText:SetTextColor(color.r, color.g, color.b, 1)
        f.glowDuration = rank == 1 and 0.8 or (rank == 2 and 1.2 or 1.6)
        f.glowMin = rank == 1 and 0.5 or (rank == 2 and 0.4 or 0.3)
        f.glowMax = rank == 1 and 1.0 or (rank == 2 and 0.85 or 0.7)
    else
        f.glowTex:SetVertexColor(1, 0.82, 0)
        f:SetBackdropBorderColor(0.8, 0.65, 0, 0.9)
        f.rankText:SetTextColor(1, 0.82, 0, 1)
    end
    f.glowStartTime = GetTime()
    f.glowFrame:Show()

    -- Rank + slot text
    f.rankText:SetText("BiS #" .. rank .. " — " .. slotName)

    -- Source
    local sourceStr = ""
    if BISTBC_sources and BISTBC_sources[itemId] then
        sourceStr = BISTBC_sources[itemId].source or ""
    end
    f.sourceText:SetText(sourceStr)

    -- Load item data
    local item = Item:CreateFromItemID(itemId)
    item:ContinueOnItemLoad(function()
        f.icon:SetTexture(item:GetItemIcon())
        f.nameText:SetText(item:GetItemName())
        local _, _, quality = GetItemInfo(itemId)
        if quality then
            local r, g, b = GetItemQualityColor(quality)
            f.nameText:SetTextColor(r, g, b, 1)
        end
    end)

    -- Show with fade in
    f:SetAlpha(0)
    f:Show()
    UIFrameFadeIn(f, 0.3, 0, 1)

    -- Schedule fade out after 5 seconds
    C_Timer.After(5, function()
        UIFrameFadeOut(f, 0.5, 1, 0)
        C_Timer.After(0.5, function()
            f:Hide()
            f.glowFrame:Hide()
        end)
    end)
end

local function sendChatAlert(itemId, rank, slotName)
    local item = Item:CreateFromItemID(itemId)
    item:ContinueOnItemLoad(function()
        local itemLink = item:GetItemLink()
        local color = RANK_GLOW_COLORS[rank]
        local rankColor = "|cffFFD100"
        if color then
            rankColor = string.format("|cff%02x%02x%02x", color.r * 255, color.g * 255, color.b * 255)
        end
        local msg = "|cffFFD100[BIS-TBC]|r " .. (itemLink or "Item") .. " — " .. rankColor .. "BiS #" .. rank .. "|r " .. slotName
        DEFAULT_CHAT_FRAME:AddMessage(msg)
    end)
end

local lootFrame = CreateFrame("Frame")

local function onLootEvent(self, event, msg)
    if not BISTBCAddon.db or not BISTBCAddon.db.char or not BISTBCAddon.db.char.show_drop_alerts then return end

    -- Parse item ID from loot message
    local itemId = msg and msg:match("|Hitem:(%d+):")
    itemId = tonumber(itemId)
    if not itemId then return end

    -- Skip if already equipped
    if isItemEquipped(itemId) then return end

    -- Check if it's a BiS item for current spec/phase
    local rank, slotName = findBisRank(itemId)
    if not rank then return end

    showDropAlert(itemId, rank, slotName)
    sendChatAlert(itemId, rank, slotName)
end

function BISTBCAddon:testDropAlert()
    local db = BISTBCAddon.db and BISTBCAddon.db.char
    if not db or not db.class_index or not db.phase_index then
        DEFAULT_CHAT_FRAME:AddMessage("|cffFFD100[BIS-TBC]|r Select a class/spec/phase first.")
        return
    end

    local classInfo = BISTBC_classes[db.class_index]
    if not classInfo then return end
    local className = classInfo.name
    local specName = classInfo.specs[db.spec_index]
    if not specName then return end
    local phaseKey = PHASE_KEYS[db.phase_index]

    local bislists = BISTBC_bislists and BISTBC_bislists[className]
    if not bislists then return end
    local specData = bislists[specName]
    if not specData then return end
    local slots = specData[phaseKey]
    if not slots then return end

    -- Pick a random rank 1-3 item
    local candidates = {}
    for _, slot in ipairs(slots) do
        for rank = 1, 3 do
            local itemEntry = slot[rank]
            if itemEntry then
                local id = type(itemEntry) == "table" and itemEntry.id or itemEntry
                if id and id > 0 then
                    table.insert(candidates, { id = id, rank = rank, slot = slot.slot_name })
                end
            end
        end
    end

    if #candidates == 0 then
        DEFAULT_CHAT_FRAME:AddMessage("|cffFFD100[BIS-TBC]|r No BiS items found for current spec/phase.")
        return
    end

    local pick = candidates[math.random(#candidates)]
    showDropAlert(pick.id, pick.rank, pick.slot)
    sendChatAlert(pick.id, pick.rank, pick.slot)
end

function BISTBCAddon:initDropAlerts()
    lootFrame:RegisterEvent("CHAT_MSG_LOOT")
    lootFrame:SetScript("OnEvent", onLootEvent)

    LibStub("AceConsole-3.0"):RegisterChatCommand("bistbctest", function()
        BISTBCAddon:testDropAlert()
    end)
end

function BISTBCAddon:initBisTooltip()
    -- Hook into native tooltip using TooltipDataProcessor (modern API) or HookScript (fallback)
    if TooltipDataProcessor then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip)
            OnGameTooltipSetItem(tooltip)
        end)
    else
        GameTooltip:HookScript("OnTooltipSetItem", OnGameTooltipSetItem)
        ItemRefTooltip:HookScript("OnTooltipSetItem", OnGameTooltipSetItem)
    end

    eventFrame:RegisterEvent("MODIFIER_STATE_CHANGED")
    eventFrame:SetScript("OnEvent", function(_, _, e_key, _, _)
        if GameTooltip:GetOwner() then
            if GameTooltip:GetOwner().hasItem then
                return
            end

            if e_key == "RALT" or e_key == "LALT" then
                local _, link = GameTooltip:GetItem()
                if link then
                    GameTooltip:SetHyperlink("|cff9d9d9d|Hitem:3299::::::::20:257::::::|h[Fractured Canine]|h|r")
                    GameTooltip:SetHyperlink(link)
                end
            end
        end
    end)
end
