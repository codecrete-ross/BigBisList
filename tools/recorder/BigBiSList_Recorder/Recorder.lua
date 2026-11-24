-- Development-only, opt-in capture. No networking or new saved-variable globals.
local addon = BigBiSList
if not addon or not addon.isForever then return end
local recorder = addon.Recorder or {}
addon.Recorder = recorder

local function readable(value)
    return not issecretvalue or not issecretvalue(value)
end

local function call(fn, ...)
    if type(fn) ~= "function" then return end
    local ok, a, b, c, d, e, f, g, h = pcall(fn, ...)
    if not ok then return end
    for _, value in pairs({ a, b, c, d, e, f, g, h }) do
        if not readable(value) then return end
    end
    return a, b, c, d, e, f, g, h
end

local function build()
    local version, number = call(GetBuildInfo)
    if type(version) == "string" and version:match("^1%.60%.%d+$") and number then
        return version .. "." .. tostring(number)
    end
end

local function point()
    if not C_Map then return end
    local map = call(C_Map.GetBestMapForUnit, "player")
    local position = map and call(C_Map.GetPlayerMapPosition, map, "player")
    if not position or not position.GetXY then return end
    local x, y = call(position.GetXY, position)
    if type(x) == "number" and type(y) == "number" and x >= 0 and x <= 1 and y >= 0 and y <= 1 then
        return { map_id = map, x = x, y = y }
    end
end

local function npcId(guid)
    if type(guid) ~= "string" then return end
    return tonumber(guid:match("^Creature%-%d+%-%d+%-%d+%-%d+%-(%d+)%-"))
end

local function itemId(link)
    return type(link) == "string" and tonumber(link:match("item:(%d+)")) or nil
end

function recorder:Enable(ids)
    local client = build()
    if not client then return false, "Forever build unavailable" end
    ids = ids or self.targetIds
    if type(ids) ~= "table" or #ids == 0 then return false, "Explicit capture targets required" end
    addon:EnsureDatabase()
    local account = addon:GetAccountDB()
    local capture = account.capture
    if not capture or capture.client_build ~= client then
        if capture and #(capture.records or {}) > 0 then
            return false, "Import the previous build's captures before starting a new build"
        end
        capture = { version = 1, flavor = "forever", client_build = client, records = {} }
        account.capture = capture
    end
    self.targets, self.seen = {}, {}
    for _, identifier in ipairs(ids) do
        if type(identifier) == "number" and identifier > 0 then self.targets[identifier] = true end
    end
    self.capture, self.enabled = capture, true
    return true
end

function recorder:Disable()
    self.enabled = false
end

function recorder:Record(record)
    if not self.enabled or not self.capture or #self.capture.records >= 5000 then return end
    if record.kind ~= "entrance" and not self.targets[record.item_id] then return end
    local client, faction = build(), call(UnitFactionGroup, "player")
    if client ~= self.capture.client_build or (faction ~= "Alliance" and faction ~= "Horde") then return end
    local key = table.concat({ record.kind, tostring(record.item_id or 0), tostring(record.npc_id or 0),
        tostring(record.quest_id or 0), tostring(record.instance_id or 0), table.concat(record.lines or {}, "\031") }, ":")
    if self.seen[key] then return end
    self.seen[key] = true
    record.client_build, record.faction = client, faction
    record.observed_at = call(date, "!%Y-%m-%dT%H:%M:%SZ")
    if type(record.observed_at) ~= "string" then return end
    record.position = record.position or point()
    self.capture.records[#self.capture.records + 1] = record
end

function recorder:ObserveItem(link)
    local identifier = itemId(link)
    if not self.enabled or not self.targets[identifier] or not C_TooltipInfo then return end
    local data = call(C_TooltipInfo.GetHyperlink, link)
    if type(data) ~= "table" or type(data.lines) ~= "table" then return end
    local lines, name = {}, nil
    for _, line in ipairs(data.lines) do
        for _, field in ipairs({ "leftText", "rightText" }) do
            local text = line[field]
            if readable(text) and type(text) == "string" then
                text = text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
                if text ~= "" and not text:lower():find("made by", 1, true) and not text:lower():find("crafted by", 1, true) then
                    name = name or text
                    if #lines < 120 and #text <= 1000 then lines[#lines + 1] = text end
                end
            end
        end
    end
    if name then self:Record({ kind = "tooltip", item_id = identifier, name = name, lines = lines }) end
end

function recorder:Loot()
    local _, kind, difficulty, _, _, _, _, instance = call(GetInstanceInfo)
    for slot = 1, call(GetNumLootItems) or 0 do
        local link = call(GetLootSlotLink, slot)
        local guid, _, other = call(GetLootSourceInfo, slot)
        if link then
            self:ObserveItem(link)
            self:Record({ kind = "loot", item_id = itemId(link), npc_id = not other and npcId(guid) or nil,
                instance_id = instance, difficulty_id = difficulty })
        end
    end
end

function recorder:Merchant()
    local vendor = npcId(call(UnitGUID, "npc"))
    if not vendor then return end
    for index = 1, call(GetMerchantNumItems) or 0 do
        local link = call(GetMerchantItemLink, index)
        if link then
            local _, _, price, _, stock, _, extended = call(GetMerchantItemInfo, index)
            self:ObserveItem(link)
            self:Record({ kind = "vendor", item_id = itemId(link), npc_id = vendor,
                price_copper = price, stock = stock, extended_cost = not not extended })
        end
    end
end

function recorder:QuestReward()
    local quest = call(GetQuestID)
    if not quest then return end
    for _, group in ipairs({ { "choice", GetNumQuestChoices }, { "reward", GetNumQuestRewards } }) do
        for index = 1, call(group[2]) or 0 do
            local link = call(GetQuestItemLink, group[1], index)
            if link then
                self:ObserveItem(link)
                self:Record({ kind = "quest_reward", item_id = itemId(link), quest_id = quest, choice = group[1] == "choice" })
            end
        end
    end
end

if CreateFrame then
    local frame = CreateFrame("Frame")
    recorder.frame = frame
    for _, event in ipairs({ "LOOT_OPENED", "MERCHANT_SHOW", "QUEST_COMPLETE", "PLAYER_ENTERING_WORLD" }) do
        pcall(frame.RegisterEvent, frame, event)
    end
    frame:SetScript("OnEvent", function(_, event)
        if not recorder.enabled then return end
        if event == "LOOT_OPENED" then recorder:Loot()
        elseif event == "MERCHANT_SHOW" then recorder:Merchant()
        elseif event == "QUEST_COMPLETE" then recorder:QuestReward()
        elseif event == "PLAYER_ENTERING_WORLD" then
            local _, kind, _, _, _, _, _, instance = call(GetInstanceInfo)
            if kind == "none" then recorder.lastOutdoorPoint = point()
            elseif instance and recorder.lastOutdoorPoint then
                recorder:Record({ kind = "entrance", instance_id = instance, position = recorder.lastOutdoorPoint })
            end
        end
    end)
end

if TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall and Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item then
    pcall(TooltipDataProcessor.AddTooltipPostCall, Enum.TooltipDataType.Item, function(tooltip)
        if tooltip then
            local _, link = call(tooltip.GetItem, tooltip)
            if link then recorder:ObserveItem(link) end
        end
    end)
elseif GameTooltip and GameTooltip.HookScript then
    pcall(GameTooltip.HookScript, GameTooltip, "OnTooltipSetItem", function(tooltip)
        local _, link = call(tooltip.GetItem, tooltip)
        if link then recorder:ObserveItem(link) end
    end)
end
