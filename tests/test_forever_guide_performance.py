"""Full-catalog acceptance for the packed Forever Gear Guide."""

import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


SETUP = r'''
local H = dofile("tests/lua_ui_harness.lua")
local level, worn = 49, 10090
local gothic = "item:10090::::::::50:1486::1:1:12723:1:28:5253:::::"
UnitClass = function() return "Paladin", "PALADIN" end
UnitClassBase = function() return "PALADIN" end
UnitRace = function() return "Human", "Human", 1 end
UnitFactionGroup = function() return "Alliance" end
UnitLevel = function() return level end
GetInventoryItemID = function(_, slot) if slot == 1 then return worn end end
GetInventoryItemLink = function(_, slot) if slot == 1 then return worn == 10090 and gothic or "item:" .. worn end end
local ui = H.load("forever", true)
local addon, rating = BigBiSList, BigBiSList.ForeverGearRating
addon.DetectPlayerSpec = function() return "Retribution" end
addon:RefreshTooltipPlayerContext()
local selection = ui:GetSelection()
selection.class, selection.spec, selection.mode, selection.phase, selection.tab =
    "Paladin", "Retribution", "leveling", "LEVELING", "Gear Guide"
addon:SetSelectedLevelingLevel(49, true)
'''


class ForeverGuidePerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()
        if not cls.lua:
            raise unittest.SkipTest("Lua 5.1 is unavailable")

    def lua_run(self, code: str):
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, timeout=120, encoding="utf-8",
                                capture_output=True, input=SETUP + code + "\nassert(#H.errors == 0, table.concat(H.errors, '\\n'))")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_cold_window_never_asks_for_full_pools_or_hidden_facets(self):
        self.lua_run(r'''
local queried = 0
local capture = addon.GetFilterAvailabilitySnapshot
function addon:GetFilterAvailabilitySnapshot(...)
    queried = queried + 1
    return capture(self, ...)
end
function addon:GetLevelingRows() error("Cold Guide must read the shipped pages") end
function rating:GetGuidePlacement() error("Cold Guide must use indexed rank lookups") end
function rating:VisitPackedGuideOrdinals() error("Filter menus must read target pages") end
addon:InitUIEvents()
ui:Open()
for tick = 1, 3 do H.now = H.now + 1/60; H.tick() end
local function rows()
    local result = 0
    for _, frame in ipairs(ui.activeRenderFrames or {}) do
        if frame:IsShown() and frame.boundData and frame.boundData.stat_rank then result = result + 1 end
    end
    return result
end
assert(rows() > 0 and queried == 0)
H.settle()
assert(ui.renderModel.rowCount > 0 and ui.renderModel.rowCount < 400 and #ui.renderModel.entries < 100)
ui:VisitListEntries(ui.renderModel, 0, math.huge, function(entry)
    local row = entry.data
    if row then
        assert(addon:IsGuideTargetRoute(row.matched_access_option))
        assert(row.targetVerdict.kind == "upgrade" or row.targetVerdict.kind == "utility")
    end
end)
ui.contentScroll:SetVerticalScroll(1200)
H.settle()
local position = ui:CaptureNavigationState()
assert(position.anchorKey and position.anchorSpan)
local serial = ui.renderModelSerial
local refreshes = ui:GetPerformanceStats().executedRefreshes
local frame = addon.uiEventFrame
for _ = 1, 12 do
    frame:GetScript("OnEvent")(frame, "BAG_UPDATE_DELAYED")
    frame:GetScript("OnEvent")(frame, "QUEST_LOG_UPDATE")
end
H.settle()
H.now = H.now + 60
H.tick()
assert(ui.renderModelSerial == serial and ui:GetPerformanceStats().executedRefreshes == refreshes)
assert(queried == 0)
ui:SetFilterDrawerOpen(true)
H.settle()
assert(queried == 1 and #(ui:GetFilterAvailabilitySnapshot().sourceTypes or {}) > 0)
for _, source in ipairs(ui:GetFilterAvailabilitySnapshot().sourceTypes) do assert(source ~= "trade") end
assert(ui.renderModelSerial == serial)
ui:SetFilterDrawerOpen(false)
worn = 7719
frame:GetScript("OnEvent")(frame, "PLAYER_EQUIPMENT_CHANGED", 1)
H.settle()
assert(ui.renderModelSerial > serial and ui:CaptureNavigationState().anchorKey == position.anchorKey)
assert(ui:CaptureNavigationState().anchorOffset == position.anchorOffset)
''')

    def test_cold_native_tooltip_and_exact_search_share_the_same_helm_rank(self):
        self.lua_run(r'''
function rating:GetGuidePlacement() error("A native hover must read its indexed rank") end
local tip = GameTooltip
tip:SetOwner(UIParent)
tip:SetHyperlink("item:7719")
tip:Show()
local cold = table.concat(tip.lines or {}, "\n")
assert(cold:find("Waiting for item stats", 1, true) and not cold:find("pts vs", 1, true), cold)
H.settle()
local lines = table.concat(tip.lines or {}, "\n")
assert(lines:find("Slight upgrade", 1, true) and lines:find("+2.1 pts vs Gothic Plate Helmet of the Gorilla", 1, true), lines)

local filters = ui:GetFilters("Gear Guide")
filters.slots, filters.search = { Head = true }, "Gothic Plate Helmet of the Gorilla"
ui:Open()
H.settle()
local candidate
ui:VisitListEntries(ui.renderModel, 0, math.huge, function(entry)
    if entry.data and entry.data.stat_identity == "10090:0:0:0:1:12723" then candidate = entry.data end
end)
assert(candidate and candidate.stat_rank.rank == 144 and candidate.stat_rank.total == 2810)
''')

    def test_level_51_targets_and_exact_lookup_use_best_owned_helm(self):
        self.lua_run(r'''
level = 51
addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
local bag
C_Container = {
    GetContainerNumSlots = function(id) return id == 0 and bag and 1 or 0 end,
    GetContainerItemID = function(id) return id == 0 and bag end,
    GetContainerItemLink = function(id) return id == 0 and bag and "item:" .. bag end,
}
addon:InitUIEvents()
ui:Open(); H.settle()
local function head() return assert(ui.renderModel.targetQuery.slots.Head) end
local function find(id)
    local bucket = head()
    return bucket.rows[bucket.positions[tostring(id)]]
end
local function advice(row)
    return table.concat(rating:LevelingPresentationLines(ui:GetLevelingGearView(row, "leveling")), "\n")
end
local function lookup(value)
    ui:SetFilter("search", value); H.settle()
end
local function bagsChanged()
    local f = addon.uiEventFrame
    f:GetScript("OnEvent")(f, "BAG_UPDATE_DELAYED"); H.settle()
end
assert(#head().rows == 4 and not find(6686) and not find(10574))
local herod = assert(find(7719))
assert(herod.stat_rank.rank == 143 and math.abs(herod.targetVerdict.gain - 2.1) < 0.001)
assert(advice(herod):find("+2.1 pts vs Gothic Plate Helmet of the Gorilla", 1, true))
lookup("Tusken Helm")
assert(#head().rows == 1 and advice(find(6686)):find("-6.5 pts vs Gothic Plate Helmet of the Gorilla", 1, true))
lookup("Corpseshroud")
assert(find(10574).lookupReason:find("Auction House", 1, true))
lookup(gothic)
assert(head().rows[1].stat_identity == "10090:0:0:0:1:12723")
lookup("")
bag = 9479; bagsChanged()
assert(not find(7719) and not find(9479), "The better bag helm is already owned")
lookup("item:7719")
assert(advice(find(7719)):find("pts vs Embrace of the Lycan", 1, true))
lookup("item:9479")
local winner = advice(find(9479))
assert(winner:find("Best you own for this slot", 1, true) and not winner:find("pts vs", 1, true), winner)
lookup("item:7719")
bag = nil
local bank = addon:GetCharacterDB().bankCache
bank.scanned, bank.links, bank.locations = true, {"item:9479"}, {"bank:1"}
bagsChanged()
assert(advice(find(7719)):find("pts vs Embrace of the Lycan", 1, true))
assert(find(7719).targetVerdict.swap.replacements[1].state == "bank")
lookup("")
assert(not find(7719))
ui:SetFilter("zones", {["Scarlet Monastery"] = true}); H.settle()
assert(not find(7719))
ui:GetViewState("Gear Guide").groupBy = "activity"
lookup("Tusken Helm")
assert(ui.renderModel.targetQuery.exact and advice(find(6686)):find("pts vs Embrace of the Lycan", 1, true))
''')

    def test_random_drop_is_one_target_and_wishlist_keeps_its_roll(self):
        self.lua_run(r'''
level, worn = 51, 6686
addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
-- Give two known exact rolls the same named drop route. Both beat the worn
-- Tusken Helm. The full reference scorer and the personal comparison stay live.
local keys = {}
local all = BigBiSListData.guide_index.slots.Head
local guide = rating:GetGuideContext("Paladin", "Retribution", "LEVELING", 51, "Human", "Alliance")
for ordinal, key in ipairs(all.keys) do
    local item = guide.catalog.items[key]
    if item.id == 10090 and (item.name:find("of the Gorilla", 1, true) or item.name:find("of the Bear", 1, true)) then
        keys[#keys+1] = ordinal
    end
end
assert(#keys == 2)
function rating:GetGuideTargetPage() return {count = #keys, at = function(i) return keys[i] end} end
local get = addon.GetPackedGuideRow
function addon:GetPackedGuideRow(ctx, slot, ordinal, filters, match, at)
    if filters._guideTarget then
        local row = get(self, ctx, slot, ordinal, {}, false, at)
        local herod = get(self, ctx, slot, all.lookup["7719"], filters, true, at)
        row.acquisition_display, row.matched_access_option = herod.acquisition_display, herod.matched_access_option
        return row
    end
    return get(self, ctx, slot, ordinal, filters, match, at)
end
ui:Open(); H.settle()
local b = ui.renderModel.targetQuery.slots.Head
assert(#b.rows == 1)
local row = b.rows[1]
assert(row.targetRoll and row.name:find(row.targetRoll, 1, true) and row.targetVerdict.gain > 0)
local other = all.keys[keys[1]] == row.stat_identity and all.keys[keys[2]] or all.keys[keys[1]]
ui:AddWishlist(row.item_id, row)
assert(ui:IsWishlisted(row) and not ui:IsWishlisted({item_id=10090, variant_id=other}))
ui:SetFilter("search", row.item_link); H.settle()
local exact = ui.renderModel.targetQuery.slots.Head.rows[1]
assert(exact.stat_identity == row.stat_identity and exact.stat_rank.rank == row.stat_rank.rank and ui:IsWishlisted(exact))
''')

    def test_empty_results_tiny_gains_and_reviewed_utility_loss(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
local helm = BigBiSListData.guide_index.slots.Head.lookup["6686"]
function rating:GetGuideTargetPage() return {count = 1, at = function() return helm end} end
ui:Open(); H.settle()
local model, query = ui.renderModel, ui.renderModel.targetQuery
assert(#query.slots.Head.rows == 0 and not query.unknown)
assert(model.entries[2].text:find("No known helm upgrades at Level 51", 1, true))
assert(model.entries[2].text:find("Gothic Plate Helmet of the Gorilla", 1, true))
local guide, owned, player = model.guideContext, ui.currentOwned, addon:GetTooltipPlayerContext()
local row = addon:GetPackedGuideRow(guide, "Head", helm, {}, false, 51)
local swap = {delta = 0.002}
rating.GetOwnedOpportunity = function() return swap end
local function verdict() return rating:GetGuideTargetVerdict(row, guide, player, owned) end
assert(verdict().kind == "upgrade" and verdict().gain == 0.002)
swap = {delta = 0}; assert(verdict().kind == "hidden")
swap = {status = "loading"}; assert(verdict().kind == "unknown")
local index = BigBiSListData.guide_index.slots.Trinket.lookup["744"]
row = addon:GetPackedGuideRow(guide, "Trinket", index, {}, false, 51)
swap = {delta = -4, slot = "Trinket", replacements = {{name = "Owned trinket"}}, definition = {label = "Trinket"}}
row.targetVerdict = verdict()
assert(row.targetVerdict.kind == "utility" and not row.targetVerdict.gain)
local view = ui:GetLevelingGearView(row, "leveling")
assert(view.today:find("On-use fire damage", 1, true) and view.evidence:find("-4.0 pts vs Owned trinket", 1, true))
''')

    def test_activity_counts_and_sorts_share_recommendations(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
ui:GetViewState("Gear Guide").groupBy = "activity"
ui:Open(); H.settle()
local function overview(sort)
    ui:SelectSort(sort); H.settle()
    local actions = {}
    for _, e in ipairs(ui.renderModel.entries) do
        if e.activityName then
            assert(e.activityName ~= "Razorfen Kraul" and e.activityName ~= "Trade / Auction House")
            actions[#actions + 1] = e
        end
    end
    local confirmed = 0
    for _, action in ipairs(actions) do
        if action.detail:find("upgrade option", 1, true) then confirmed = confirmed + 1
        else assert(action.detail:find("Some items couldn’t be compared", 1, true)) end
    end
    assert(confirmed == 4)
    return actions
end
assert(overview("most_loot")[1].title == "Scarlet Monastery")
local best = overview("best_upgrade")[1]
assert(best.title == "Zul'Farrak" and best.detail:find("Embrace of the Lycan (+15.1 pts)", 1, true))
assert(overview("most_upgrades")[1].title == "Zul'Farrak")
ui:SetFilter("slots", {}); H.settle()
local data = ui.renderModel.targetQuery.activities
local oneLarge, smaller
for _, a in ipairs(data.ordered) do
    local x = data.batch.totals[a]
    for _, b in ipairs(data.ordered) do
        local y = data.batch.totals[b]
        if x.bestGain > y.bestGain and y.upgrades > x.upgrades then oneLarge, smaller = a.name, b.name; break end
    end
    if oneLarge then break end
end
assert(oneLarge and smaller)
local function position(sort, name)
    ui:SelectSort(sort); H.settle()
    for i, e in ipairs(ui.renderModel.entries) do if e.activityName == name then return i end end
end
assert(position("best_upgrade", oneLarge) < position("best_upgrade", smaller))
assert(position("most_upgrades", smaller) < position("most_upgrades", oneLarge))
''')

    def test_preview_sources_and_conditional_outcomes(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
ui:GetFilters("Gear Guide").slots = {Head = true}
ui:Open(); H.settle()
local function herod()
    local b = ui.renderModel.targetQuery.slots.Head
    return assert(b.rows[b.positions["7719"]])
end
ui:SetLevelingLevel(55); H.settle()
local row = herod()
local text = table.concat(rating:LevelingPresentationLines(ui:GetLevelingGearView(row, "leveling")), "\n")
assert(row.targetVerdict.swap.forecast.level == 55 and text:find("Estimated at Level 55", 1, true))
assert(not text:find("Can equip at Level 55", 1, true))
ui:SetLevelingLevel(45); H.settle()
assert(herod().targetVerdict.level == 51 and herod().stat_rank.level == 45)
ui:SetFilter("search", "Earthen Silk Slippers"); H.settle()
local craft = assert(ui.renderModel.targetQuery.slots.Feet.rows[1])
assert(craft.matched_access_option.source_type == "crafted" and ui:GetSourceNextStep(craft):find("Tailoring", 1, true))
ui:SetFilter("search", "Fine Longbow"); H.settle()
local bow = assert(ui.renderModel.targetQuery.slots.Ranged.rows[1])
assert(bow.matched_access_option.source.entity_name == "Wallace the Blind")
ui:SetFilter("search", "Tenets of the Silver Hand"); H.settle()
local selfCraft = ui.renderModel.targetQuery.slots.Libram.rows[1]
assert(ui:GetSourceNextStep(selfCraft) == "Craft it yourself · Enchanting")
assert(not ui:GetLevelingGearView(selfCraft, "leveling").evidence, "An unscored effect has no point estimate")
ui:SetFilter("search", "Gnomish Universal Remote"); H.settle()
local remote = ui.renderModel.targetQuery.slots.Trinket.rows[1]
assert(ui:GetSourceNextStep(remote) == "Have it crafted · Engineering · Requires Engineering (125)")
ui:SetFilter("search", "Malignant Root"); H.settle()
local token = ui.renderModel.targetQuery.slots.Ring.rows[1]
assert(token.matched_access_option.source_type == "token_turnin" and token.acquisition_display.source_label == "Token turn-ins")
assert(ui:GetSourceNextStep(token) == "Turn in to Rethiel the Greenwarden · 1 Rotheap Innards")
local evaluate = ui.GetAccessEvaluation
function ui:GetAccessEvaluation()
    return {status="blocked", blockingRequirement={type="reputation", reputation="The Silverwing Sentinels", standing="Honored"}}
end
assert(ui:GetSourceNextStep(token):find("Honored", 1, true) and ui:GetSourceNextStep(token):find("Silverwing", 1, true))
ui.GetAccessEvaluation = evaluate
for _, kind in ipairs({"drop", "vendor", "pvp", "token_turnin", "quest", "crafted"}) do
    local route = {source_type = kind, source = {type = kind, entity_id = 81, entity_name = "Named source",
        zone = "Dungeon", profession = "Tailoring", quest_id = 22}}
    assert(addon:IsGuideTargetRoute(route))
end
assert(not addon:IsGuideTargetRoute({source_type = "world_drop", source = {entity_name = "World drop"}}))
assert(not addon:IsGuideTargetRoute({source_type = "drop", source = {entity_name = "One observed mob", zone = "Wetlands", world_drop = true}}))
assert(not addon:IsGuideTargetRoute({source_type = "trade", source = {entity_name = "Auction House"}}))
ui:SetFilter("search", ""); H.settle()
ui:SetSpec("Protection"); H.settle()
assert(not ui.renderModel.targetQuery.reference and ui.renderModel.targetQuery.context.spec == "Protection")
''')

    def test_search_can_find_future_targets_and_completed_quest_rewards(self):
        self.lua_run(r'''
level = 51; addon:RefreshTooltipPlayerContext()
local done = {}
C_QuestLog = {IsQuestFlaggedCompleted = function(id) return done[id] == true end,
    IsOnQuest = function() return false end}
addon:InitUIEvents()
ui:GetFilters("Gear Guide").slots = {Head = true}
ui:Open(); H.settle()
assert(not ui.renderModel.targetQuery.slots.Head.positions["16727"])
ui:SetFilter("search", "Lightforge"); H.settle()
local b = ui.renderModel.targetQuery.slots.Head
local helm = b.rows[b.positions["16727"]]
assert(helm and helm.guide_route_level > level and helm.targetVerdict.swap.forecast.level == helm.guide_route_level)
ui:SetFilter("slots", {Feet=true}); ui:SetFilter("search", ""); H.settle()
b = ui.renderModel.targetQuery.slots.Feet
assert(b.positions["10658"])
done[3370] = true
local f = addon.uiEventFrame
f:GetScript("OnEvent")(f, "QUEST_LOG_UPDATE"); H.settle()
assert(not ui.renderModel.targetQuery.slots.Feet.positions["10658"])
ui:SetFilter("search", "Quagmire Galoshes"); H.settle()
local known = ui.renderModel.targetQuery.slots.Feet.rows[1]
assert(known.lookupReason:find("Quest already completed", 1, true) and known.stat_rank.rank)
''')

    def test_packed_entry_matches_the_original_scorer_and_responds_to_new_stats(self):
        self.lua_run(r'''
for _, check in ipairs({
    {"Retribution", 22, "Head"}, {"Retribution", 31, "Head"}, {"Protection", 35, "Main Hand"},
    {"Retribution", 38, "Head"}, {"Retribution", 49, "Head"}, {"Protection", 49, "Chest"}, {"Protection", 60, "Head"},
}) do
    local spec, at, slot = unpack(check)
    local guide = rating:GetGuideContext("Paladin", spec, at == 60 and "PR" or "LEVELING", at, "Human", "Alliance")
    local original = rating:GetGuidePlacement(guide, slot)
    local data = assert(rating:GetPackedGuide(guide)[slot], spec .. " " .. at .. " " .. slot)
    local seen = {}
    for position = 1, data.count do
        local ordinal = rating:GetPackedBrowseOrdinal(data, at, position)
        assert(ordinal and not seen[ordinal], "packed view contains every variant once")
        seen[ordinal] = true
    end
    for _, old in ipairs(original.rows) do
        local entry = assert(rating:GetGuideEntry(guide, slot, old.item.key), old.item.name)
        for _, field in ipairs({"score", "rank", "total", "tied", "score_percent", "provisional", "source_unknown", "conditional"}) do
            assert(entry[field] == old[field], spec .. " " .. at .. " " .. old.item.name .. " " .. field
                .. " " .. tostring(entry[field]) .. " instead of " .. tostring(old[field]))
        end
    end
end
local guide = rating:GetGuideContext("Paladin", "Retribution", "LEVELING", 49, "Human", "Alliance")
local variant = "10090:0:0:0:1:12723"
local old = assert(rating:GetGuideEntry(guide, "Head", variant))
local new = {}
for field, value in pairs(old.item) do new[field] = value end
new.stats = {strength = 200}
guide.catalog.observed[variant] = new
guide.catalog.changedSlots, guide.catalog.observedVersion = {Head = true}, 1
local updated = assert(rating:GetGuideEntry(guide, "Head", variant))
assert(updated.rank == 1 and updated.total == old.total and updated.score > old.score)
assert(rating:GetGuideEntry(guide, "Head", "9479").rank == 2)
''')
