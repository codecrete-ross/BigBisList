local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local function printLine(message)
    if DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cff33ff99Big BiS List|r: " .. message)
    end
end

local function clockMilliseconds()
    if debugprofilestop then
        return debugprofilestop()
    elseif os and os.clock then
        return os.clock() * 1000
    end
    return nil
end

local function timingLabel(startMs)
    local nowMs = clockMilliseconds()
    if startMs and nowMs then
        return string.format("%.1f ms", nowMs - startMs)
    end
    return "completed"
end

local function timeSmokeStep(label, callback)
    local startMs = clockMilliseconds()
    local result = callback()
    printLine("Timing " .. label .. ": " .. timingLabel(startMs) .. ".")
    return result
end

function BigBiSList:GetDataSummary()
    local data = BigBiSListData or {}
    local classes = data.classes or {}
    local phases = data.phases or {}
    local items = data.items or {}
    local listCount = data.meta and data.meta.slot_list_count or 0
    local levelingGearCount = data.meta and data.meta.leveling_gear_count or #(data.leveling_gear or {})
    local levelingRecommendationCount = data.meta and data.meta.leveling_recommendation_count or #(data.leveling_recommendations or {})

    if listCount == 0 and data.bis_lists then
        for _, classData in ipairs(data.bis_lists) do
            for _, specData in ipairs(classData.specs or {}) do
                for _, phaseData in ipairs(specData.phases or {}) do
                    listCount = listCount + #(phaseData.slots or {})
                end
            end
        end
    end

    return string.format("%d classes, %d phases, %d items, %d slot lists, %d guide leveling rows, %d computed leveling recommendations", #classes, #phases, #items, listCount, levelingGearCount, levelingRecommendationCount)
end

function BigBiSList:ShowStatus()
    printLine(self.displayName .. " " .. self.version .. " loaded.")
    printLine("Data seed: " .. self:GetDataSummary() .. ".")
end

function BigBiSList:RunSmokeTest()
    self:EnsureDatabase()
    printLine("Smoke test passed. Saved variable BigBiSListDB is initialized.")
    local selection = self:GetCharacterDB().selection
    printLine("Current selection: " .. selection.class .. " / " .. selection.spec .. " / " .. self:GetPhaseDisplayName(selection.phase) .. ".")
    self:RunTimingSmokeTest(selection)
end

function BigBiSList:RunTimingSmokeTest(selection)
    selection = selection or self:GetCharacterDB().selection
    local filters = {
        sourceType = "all",
        zone = "all",
        reputation = "all",
        rankGroup = "all",
        ownedState = "all",
        binding = "all",
        boe = "all",
        faction = "all",
        longevity = "all",
        slots = {},
        ownedItems = {},
        ignoredItems = {},
        hideIgnored = true,
    }

    timeSmokeStep("GetDataIndex", function()
        return self:GetDataIndex()
    end)
    if selection.phase == self.levelingPhaseKey then
        filters.level = self.GetSelectedLevelingLevel and self:GetSelectedLevelingLevel() or (self.maxLevelingLevel or 69)
        timeSmokeStep("leveling rows", function()
            return self:GetLevelingRows(selection.class, selection.spec, filters.level, filters)
        end)
    else
        timeSmokeStep("planner rows", function()
            return self:GetPlannerRows(selection.class, selection.spec, selection.phase, filters)
        end)
        timeSmokeStep("phase rows", function()
            return self:GetPhaseRows(selection.class, selection.spec, selection.phase, filters)
        end)
    end
    timeSmokeStep("filter availability", function()
        return self:GetFilterAvailabilitySnapshot(selection.class, selection.spec, selection.phase, selection.tab, filters)
    end)
    timeSmokeStep("repeated cached calls", function()
        for _ = 1, 3 do
            self:GetDataIndex()
            if selection.phase == self.levelingPhaseKey then
                self:GetLevelingRows(selection.class, selection.spec, filters.level, filters)
            else
                self:GetPlannerRows(selection.class, selection.spec, selection.phase, filters)
                self:GetPhaseRows(selection.class, selection.spec, selection.phase, filters)
            end
            self:GetFilterAvailabilitySnapshot(selection.class, selection.spec, selection.phase, selection.tab, filters)
        end
    end)
end

local function handleSlashCommand(input)
    input = string.lower((input or ""):gsub("^%s+", ""):gsub("%s+$", ""))

    if input == "test" then
        BigBiSList:RunSmokeTest()
        return
    end

    if input == "status" then
        BigBiSList:ShowStatus()
        return
    end

    if input == "settings" or input == "config" then
        BigBiSList:SetSelection(nil, nil, nil, "Settings")
        BigBiSList:OpenMainFrame()
        return
    end

    BigBiSList:ToggleMainFrame()
end

local addonInitialized = false

local function retryDetectedPlayerSelection()
    if not addonInitialized or not BigBiSList.ApplyDetectedPlayerSelection then
        return
    end

    local changed = BigBiSList:ApplyDetectedPlayerSelection()
    if BigBiSList.ApplyDetectedPlayerLevel and BigBiSList:ApplyDetectedPlayerLevel() then
        changed = true
    end

    if changed then
        BigBiSList:RefreshUI()
    end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("PLAYER_TALENT_UPDATE")
frame:RegisterEvent("CHARACTER_POINTS_CHANGED")
frame:RegisterEvent("PLAYER_LEVEL_UP")
frame:SetScript("OnEvent", function(_, event, loadedAddon)
    if event == "PLAYER_LOGIN"
        or event == "PLAYER_ENTERING_WORLD"
        or event == "PLAYER_TALENT_UPDATE"
        or event == "CHARACTER_POINTS_CHANGED"
        or event == "PLAYER_LEVEL_UP" then
        retryDetectedPlayerSelection()
        return
    end

    if event ~= "ADDON_LOADED" or loadedAddon ~= BigBiSList.addonName then
        return
    end

    BigBiSList:EnsureDatabase()
    BigBiSList:ResetClassSpecAutoSelection()
    BigBiSList:InitUIEvents()
    BigBiSList:InitTooltip()
    BigBiSList:InitMinimapButton()
    addonInitialized = true
    retryDetectedPlayerSelection()
    printLine("loaded. Use /bbl or /bigbis.")
end)

SLASH_BIGBISLIST1 = "/bigbis"
SLASH_BIGBISLIST2 = "/bbl"
SlashCmdList.BIGBISLIST = handleSlashCommand

SLASH_BIGBISLISTTEST1 = "/bbltest"
SlashCmdList.BIGBISLISTTEST = function()
    BigBiSList:RunSmokeTest()
end
