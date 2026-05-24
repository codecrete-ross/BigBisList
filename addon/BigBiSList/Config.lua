local addonName = ...

BigBiSList = BigBiSList or {}
BigBiSList.addonName = addonName or "BigBiSList"
BigBiSList.displayName = "Big BiS List"
BigBiSList.version = "0.1.0"

BigBiSList.defaults = {
    profile = {
        tooltipMode = "normal",
        showMinimap = true,
    },
    char = {
        selectedClass = "Druid",
        selectedSpec = "Feral dps",
        selectedPhase = "SWP",
    },
}

function BigBiSList:EnsureDatabase()
    BigBiSListDB = BigBiSListDB or {}
    BigBiSListDB.profile = BigBiSListDB.profile or {}
    BigBiSListDB.char = BigBiSListDB.char or {}

    for key, value in pairs(self.defaults.profile) do
        if BigBiSListDB.profile[key] == nil then
            BigBiSListDB.profile[key] = value
        end
    end

    for key, value in pairs(self.defaults.char) do
        if BigBiSListDB.char[key] == nil then
            BigBiSListDB.char[key] = value
        end
    end
end

