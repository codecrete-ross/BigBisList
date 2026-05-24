local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or BigBiSList.addonName or "BigBiSList"

local function printLine(message)
    if DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cff33ff99Big BiS List|r: " .. message)
    end
end

function BigBiSList:GetDataSummary()
    local data = BigBiSListData or {}
    local classes = data.classes or {}
    local phases = data.phases or {}
    local items = data.items or {}
    local listCount = 0

    if data.bis_lists then
        for _, classData in ipairs(data.bis_lists) do
            for _, specData in ipairs(classData.specs or {}) do
                for _, phaseData in ipairs(specData.phases or {}) do
                    listCount = listCount + #(phaseData.slots or {})
                end
            end
        end
    end

    return string.format("%d classes, %d phases, %d items, %d slot lists", #classes, #phases, #items, listCount)
end

function BigBiSList:ShowStatus()
    printLine(self.displayName .. " " .. self.version .. " loaded.")
    printLine("Data seed: " .. self:GetDataSummary() .. ".")
end

function BigBiSList:RunSmokeTest()
    self:EnsureDatabase()
    printLine("Smoke test passed. Saved variable BigBiSListDB is initialized.")
    printLine("Current selection: " .. BigBiSListDB.char.selectedClass .. " / " .. BigBiSListDB.char.selectedSpec .. " / " .. BigBiSListDB.char.selectedPhase .. ".")
end

local function handleSlashCommand(input)
    input = string.lower(input or "")

    if input == "test" then
        BigBiSList:RunSmokeTest()
        return
    end

    BigBiSList:ShowStatus()
    printLine("Commands: /bbl, /bigbis, /bbltest.")
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", function(_, event, loadedAddon)
    if event ~= "ADDON_LOADED" or loadedAddon ~= BigBiSList.addonName then
        return
    end

    BigBiSList:EnsureDatabase()
    printLine("loaded. Use /bbl or /bigbis.")
end)

SLASH_BIGBISLIST1 = "/bigbis"
SLASH_BIGBISLIST2 = "/bbl"
SlashCmdList.BIGBISLIST = handleSlashCommand

SLASH_BIGBISLISTTEST1 = "/bbltest"
SlashCmdList.BIGBISLISTTEST = function()
    BigBiSList:RunSmokeTest()
end

