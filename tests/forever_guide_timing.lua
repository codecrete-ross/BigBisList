-- Run from the repository root with Lua 5.1. Each invocation starts with a fresh save.
local build, payload = assert(tonumber(arg[1]), "Expected a Forever build number"), arg[2] or "full"
local spec, density = arg[3] or "Retribution", arg[4] or "comfortable"
assert(payload == "full" or payload == "core", "Expected full or core")
assert(spec == "Retribution" or spec == "Protection")
assert(density == "comfortable" or density == "compact")
local H = dofile("tests/lua_ui_harness.lua")
GetBuildInfo = function() return "Forever", tostring(build) end
UnitClass = function() return "Paladin", "PALADIN" end
UnitClassBase = function() return "PALADIN" end
UnitRace = function() return "Human", "Human", 1 end
UnitFactionGroup = function() return "Alliance" end
UnitLevel = function() return 51 end
GetInventoryItemID = function(_, slot) if slot == 1 then return 10090 end end
GetInventoryItemLink = function(_, slot)
    if slot == 1 then return "item:10090::::::::50:1486::1:1:12723:1:28:5253:::::" end
end
if spec == "Protection" then
    local worn = {14919, 7673, 9476, 0, 10203, 276742, 10133, 10131, 14914, 9410,
        274642, 11118, 280766, 17774, 276737, 17705, 1203}
    local bonuses = {[14919]=12754, [10203]=12754, [10133]=12754, [10131]=12754, [14914]=12752, [9410]=13182, [11118]=13099}
    GetInventoryItemID = function(_, slot) return worn[slot] ~= 0 and worn[slot] or nil end
    GetInventoryItemLink = function(unit, slot)
        local id = GetInventoryItemID(unit, slot)
        if id then return "item:" .. id .. (bonuses[id] and ("::::::::51:1486::1:1:" .. bonuses[id]) or "") end
    end
end

local function milliseconds() return os.clock() * 1000 end
debugprofilestop = milliseconds
SlashCmdList = {}
strmatch = string.match
H.installMinimap()
local heap = collectgarbage("count")
local start = milliseconds()
local private = {}
for line in io.lines("BigBiSList_Camelot.toc") do
    local file = line:match("^%s*(.-%.lua)%s*$")
    if file and (payload == "full" or file ~= "GuideDataForever.lua" and file ~= "GuideRanksForever.lua") then
        assert(loadfile((file:gsub("\\", "/"))))("BigBiSList", private)
    end
end
local addon = BigBiSList
addon.DetectPlayerSpec = function() return spec end
H.fireEvent("ADDON_LOADED", "BigBiSList")
local loaded = milliseconds()
H.fireEvent("PLAYER_LOGIN")
H.fireEvent("PLAYER_ENTERING_WORLD", true, false)
local loginTime = milliseconds() - loaded
collectgarbage("collect")
local retained = (collectgarbage("count") - heap) / 1024
local ui = addon.UI
addon:SetSelection("Paladin", spec, "LEVELING", "Gear Guide")
addon:SetSelectedLevelingLevel(51, true)
local window = addon:GetAccountDB().profile.window
window.density = density
if spec == "Protection" then
    window.width, window.height = 1020, 790
    local bank = addon:GetCharacterDB().bankCache
    bank.scanned, bank.links, bank.locations = true, {"item:6829"}, {"20:1"}
end
if arg[5] == "details" then
    UIParent:SetSize(900, 500)
    window.width, window.height = 900, 500
end
assert(addon.loadTimeMs and addon.UI and addon.uiEventFrame, "The packaged addon did not initialize")

local function visibleRows()
    local count = 0
    for _, frame in ipairs(ui.activeRenderFrames or {}) do
        if frame:IsVisible() and frame.boundData and frame.boundData.stat_rank then count = count + 1 end
    end
    return count
end
local function tick() H.now = H.now + 1/60; H.tick() end
local function completePage()
    if not ui.frame:IsVisible() then assert(visibleRows() == 0); return end
    local display = assert(ui.guideDisplay, "Window became visible before its Guide page")
    local count = 0
    ui:VisitListEntries(ui.renderModel, display.offset, display.offset + display.height, function(entry)
        if entry.bottom > display.offset and entry.top < display.offset + display.height then
            count = count + 1
            local frame = assert(ui.activeRenderFrames[count], "Partial viewport")
            local bound = frame.__bigBisBoundRenderEntry
            assert(frame:IsVisible() and ui:IsCurrentRenderFrame(frame) and bound.top == entry.top and bound.kind == entry.kind)
            if entry.data then
                assert(frame.boundData.stat_identity == entry.data.stat_identity and frame.iconButton.itemId == entry.data.item_id)
            end
        end
    end)
    assert(count == #ui.activeRenderFrames, "Two frames own the same part of the page")
end
local first, viewport
ui:Open()
for frame = 1, 3000 do
    tick()
    completePage()
    if not first and visibleRows() > 0 then first = frame end
    if not viewport and ui:GetPerformanceStats().firstViewportMs then viewport = frame end
    if viewport and ui.guideDisplay.personal and not ui.guideStage
        and not ui.refreshScheduled and not ui.layoutScheduled and not ui.packedPaintPending then break end
end
assert(viewport and ui.renderModel.targetQuery.done, "The Guide did not finish personalizing")
assert(first == viewport, "Gear became visible in multiple paints")
local displayed, serial, bindings, pointed = ui.guideDisplay, ui.renderModelSerial, {}
for index, frame in ipairs(ui.activeRenderFrames) do
    bindings[index] = {frame = frame, token = frame.bindToken, top = frame:GetTop(), left = frame:GetLeft(),
        item = frame.iconButton and frame.iconButton.itemId}
    if not pointed and frame.boundData then pointed = frame end
end
assert(pointed); pointed:SetHovered(true)
for frame = 1, 930 do
    if frame == 901 then
        for _ = 1, 4 do
            for _, event in ipairs({"BAG_UPDATE_DELAYED", "QUEST_LOG_UPDATE", "UPDATE_FACTION", "SPELLS_CHANGED",
                "SKILL_LINES_CHANGED", "PLAYER_TALENT_UPDATE"}) do H.fireEvent(event) end
        end
    end
    tick()
    assert(ui.guideDisplay == displayed and ui.renderModelSerial == serial and pointed.hovered, "Idle Guide replaced its page or hover")
    for index, row in ipairs(ui.activeRenderFrames) do
        local fixed = bindings[index]
        assert(row == fixed.frame and row.bindToken == fixed.token and row:GetTop() == fixed.top and row:GetLeft() == fixed.left,
            "Idle row moved or rebound")
        assert((row.iconButton and row.iconButton.itemId) == fixed.item, "Idle click target changed")
    end
end
pointed:SetHovered(false)
ui:Close()
ui:Open()
assert(visibleRows() > 0, "Warm reopen lost its visible rows")
tick()
local button
for _, frame in ipairs(ui.activeRenderFrames) do
    if frame:IsVisible() and frame.iconButton and frame.boundData and frame.boundData.stat_rank then
        button = frame.iconButton
        break
    end
end
assert(button, "Warm Guide has no selectable item")
local hoverAt = milliseconds()
button:GetScript("OnEnter")(button)
local hoverTime = milliseconds() - hoverAt
button:GetScript("OnLeave")(button)
tick()
local detailsAt = milliseconds()
button:Click()
local detailsTime = milliseconds() - detailsAt
assert(ui.selectedItemData and ui.selectedItemData.matched_access_option, "Item click lost its route")
if arg[5] == "details" then
    assert(ui.frame:GetWidth() <= 900 and ui.frame:GetHeight() <= 500 and ui:IsInspectorVisible())
end
assert(#H.errors == 0, table.concat(H.errors, "\n"))
local stats, rating = ui:GetPerformanceStats(), addon.ForeverGearRating
assert((rating.fullPoolRequests or 0) == 0 and (rating.unindexedSummaryRequests or 0) == 0,
    "Opening, hovering, or selecting gear requested a full ranking")
print(string.format("%d %s %s %s: add-on load %.1f ms, login events %.1f ms, retained Lua heap %.1f MiB",
    build, payload, spec, density, loaded - start, loginTime, retained))
print(string.format("first row on frame %d, first viewport on frame %d (%.1f ms of harness time), warm reopen %.1f ms",
    first, viewport, stats.firstViewportMs, stats.warmOpenMs))
print(string.format("peak measured addon frame %.1f ms (%s), full ranking requests %d, unindexed level summaries %d",
    stats.worstFrame, stats.worstFrameWork or "unsampled", rating.fullPoolRequests or 0, rating.unindexedSummaryRequests or 0))
print(string.format("item hover %.1f ms, route click %.1f ms", hoverTime, detailsTime))
collectgarbage("collect")
print(string.format("retained after browsing %.1f MiB including simulated widgets", (collectgarbage("count") - heap) / 1024))
assert(first <= 3 and stats.firstViewportMs <= 50, "Complete first viewport exceeded 50 ms at 60 Hz")
assert(math.max(stats.worstFrame, hoverTime, detailsTime) <= 4, "Interaction exceeded the 4 ms frame budget")
