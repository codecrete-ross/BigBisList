from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from test_addon_runtime_lua import find_lua51
from tools import forever, generate_lua, scrape_wowhead, validate_data
from tools.forever_sources import evidence_ref
from tools.project import ADDON_DIR


class ForeverPipelineTests(unittest.TestCase):
    def test_flavor_is_required_and_invalid_flavors_are_rejected(self):
        for command, args in (
            (generate_lua.main, ["--check"]),
            (validate_data.main, ["--json"]),
            (scrape_wowhead.main, ["import", "--dry-run"]),
            (scrape_wowhead.main, ["discover-items"]),
            (scrape_wowhead.main, ["discover-sources"]),
            (scrape_wowhead.main, ["gaps", "--json"]),
            (scrape_wowhead.main, ["coverage", "--strict"]),
        ):
            for extra in ([], ["--flavor", "classic"]):
                with self.subTest(command=command.__module__, args=extra), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        command(args + extra)
                    self.assertEqual(error.exception.code, 2)

    def test_discovery_registers_each_forever_item_id_once(self):
        root = forever.WOWHEAD_ROOT
        snapshots = {root + "guide/example": {"page_type": "guide", "tables": [{"rows": [
            {"item_id": 21, "item_url": root + "item=21/example"},
            {"item_id": 21},
            {"item_id": 22, "item_url": "https://www.wowhead.com/tbc/item=22/example"},
            {"item_id": 23, "item_url": root + "item=23/example"},
        ]}]}}
        self.assertEqual(scrape_wowhead.forever_item_seeds(snapshots, {root + "item=23/registered"}), [root + "item=21"])

    def test_fetch_continues_after_failure_and_saves_forever_tooltip(self):
        root = forever.WOWHEAD_ROOT
        failed, item = root + "guide/a", root + "item=21"
        tooltip_url = "https://nether.wowhead.com/forever/tooltip/item/21"
        tooltip = json.dumps({"name": "Fixture Ring", "quality": 3, "tooltip": "<div>Finger<br>+8 Stamina</div>"})
        with TemporaryDirectory() as directory, patch.object(forever, "registered_urls", return_value={failed, item}), patch.object(
            scrape_wowhead, "fetch_url", side_effect=[RuntimeError("HTTP Error 503"), RuntimeError("HTTP Error 403"), tooltip]
        ) as fetch, redirect_stdout(io.StringIO()) as output:
            status = scrape_wowhead.main(["fetch", "--flavor", "forever", "--output-dir", directory])
            snapshot = json.loads((Path(directory) / scrape_wowhead.snapshot_name(item)).read_text(encoding="utf-8"))
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue()), {"fetched": 1, "failures": {failed: "HTTP Error 503"}})
        self.assertEqual(fetch.call_args.args[0], tooltip_url)
        self.assertEqual(snapshot["tooltip_url"], tooltip_url)
        self.assertEqual(snapshot["flavor"], "forever")

    def test_snapshot_paths_cannot_cross_flavors(self):
        for flavor, path in (("forever", "data/raw/wowhead"), ("anniversary", "data/raw/wowhead/forever")):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                scrape_wowhead.main(["import", "--flavor", flavor, "--input-dir", path, "--dry-run"])
            self.assertEqual(error.exception.code, 2)

    def test_reviews_are_bound_to_item_snapshot_and_scoring_inputs(self):
        url = forever.WOWHEAD_ROOT + "item=71/example"
        snapshot = {
            "page_type": "item", "name": "Fixture Ring", "item_id": 71, "quality": "rare",
            "item_stats": {"parse_confidence": "tooltip", "slot": "Ring", "stats": {"stamina": 8}},
        }
        evidence = {
            "reviewer": "test", "reviewed_at": "2026-11-05", "client_build": "1.60.1.70790",
            "source_url": url, "reason": "Fixture evidence",
            "evidence_refs": [evidence_ref(url, {url: snapshot})],
        }
        verification = {
            **evidence, "type": "verify_item", "snapshot_url": url, "item_id": 71,
            "snapshot_digest": forever.snapshot_digest(snapshot),
            "sources": [{**evidence, "type": "quest", "quest_id": 7, "entity_name": "Fixture Quest", "side": "Alliance"}],
        }
        self.assertEqual(forever.load_verified_items({url: snapshot}, []), ({}, {}))
        _, stats = forever.load_verified_items({url: snapshot}, [verification])
        with self.assertRaisesRegex(ValueError, "Invalid Forever item review"):
            forever.load_verified_items({url: {**snapshot, "name": "Changed"}}, [verification])

        profile = {
            "class": "Warrior", "spec": "Protection", "role": "tank", "slots": ["Ring"],
            "armor_types": ["Plate"], "weapon_types": ["Sword"],
        }
        profiles = {"profiles": [profile], "role_weights": {"tank": {"stamina": 2}}, "version": "fixture"}
        lists, audit = forever.rank(stats, profiles, [], {})
        self.assertEqual(lists, [])
        self.assertEqual(audit[0]["candidates"], [{"item_id": 71, "score": 16}])
        review = {
            **evidence, "type": "approve_ranking", "class": "Warrior", "spec": "Protection",
            "slot": "Ring", "item_ids": [71], "profile_version": "fixture", "candidate_digest": audit[0]["candidate_digest"],
        }
        lists, _ = forever.rank(stats, profiles, [review], {})
        self.assertEqual(lists[0]["items"], [{"item_id": 71, "rank": 1, "rank_group": "bis", "rank_label": "BiS"}])
        with self.assertRaisesRegex(ValueError, "Invalid Forever ranking review"):
            forever.rank(stats, {**profiles, "role_weights": {"tank": {"stamina": 3}}}, [review], {})

    def test_coverage_requires_a_usable_route_on_each_faction(self):
        profile = {"class": "Warrior", "spec": "Protection", "slots": ["Ring"]}
        items = {"items": [{"id": 71, "sources": [
            {"type": "quest", "side": "Alliance"},
            {"type": "quest", "side": "Horde", "eligibility": {"min_level": 30, "classes": ["Shaman"]}},
        ]}]}
        lists = {"lists": [{"class": "Warrior", "spec": "Protection", "slot": "Ring", "items": [{"item_id": 71}]}]}
        with patch.object(forever, "scoring_profiles", return_value={"profiles": [profile]}), patch.object(
            forever, "dataset_json", side_effect=lambda flavor, name: {"items": items, "bis_lists": lists}[name]
        ):
            report = forever.coverage()
        self.assertFalse(report["ok"])
        self.assertEqual([row["faction"] for row in report["missing"]], ["Horde"])

    def test_pre_raid_rank_applies_class_and_level_gates_before_scoring(self):
        profiles = {"profiles": [{
            "class": "Warrior", "spec": "Protection", "slots": ["Ring"], "role": "tank",
        }], "role_weights": {"tank": {"stamina": 1}}, "version": "fixture"}
        vendor = {"type": "vendor", "side": "Both"}
        stats = {
            71: {"slot": "Ring", "stats": {"stamina": 3}, "sources": [vendor]},
            72: {"slot": "Ring", "stats": {"stamina": 20}, "sources": [{
                **vendor, "token_sources": [{
                    "type": "quest", "side": "Both", "eligibility": {"min_level": 30, "classes": ["Shaman"]},
                }],
            }]},
            73: {"slot": "Ring", "stats": {"stamina": 30}, "sources": [{
                **vendor, "eligibility": {"min_level": 1, "max_level": 19},
            }]},
        }
        _, audit = forever.rank(stats, profiles, [], {})
        self.assertEqual(audit[0]["candidates"], [{"item_id": 71, "score": 3}])

    def test_ranged_weapon_damage_never_becomes_melee_weapon_damage(self):
        for subtype, stat in [("Bow", "ranged_dps"), ("Crossbow", "ranged_dps"), ("Gun", "ranged_dps"),
                              ("Thrown", "ranged_dps"), ("Wand", "wand_dps")]:
            with self.subTest(subtype=subtype):
                item = {"weapon_subtype": subtype, "dps": 20, "stats": {"agility": 2}}
                self.assertEqual(forever.score(item, {"dps": 5, "agility": 1}), 2)
                self.assertEqual(forever.score(item, {stat: 5, "agility": 1}), 102)

    def test_one_handed_training_does_not_allow_two_handed_weapons(self):
        profile={"class":"Mage","weapon_types":["Dagger","Sword","Staff","Wand"],
                 "two_hand_weapon_types":["Staff"],"armor_types":["Cloth"]}
        claymore={"slot":"Two Hand","weapon_subtype":"Sword"}
        staff={"slot":"Two Hand","weapon_subtype":"Staff"}
        self.assertFalse(forever.eligible(claymore,profile,"Two Hand",require_source=False))
        self.assertTrue(forever.eligible(staff,profile,"Two Hand",require_source=False))

    def test_route_validation_rejects_invalid_points_and_raid_sources(self):
        point = {
            "kind": "entrance", "map_id": 1453, "x": 0, "y": 0.5, "entity_id": 4,
            "reviewer": "test", "reviewed_at": "2026-11-05", "client_build": "1.60.1.70790",
            "source_url": forever.WOWHEAD_ROOT + "zone=4", "reason": "Fixture entrance",
        }
        source = {"type": "drop", "side": "Both", "content_type": "dungeon", "entity_name": "Fixture Boss", "destination": point}
        self.assertTrue(forever.valid_source(source))
        self.assertFalse(forever.valid_source({**source, "content_type": "raid"}))
        self.assertFalse(forever.valid_source({**source, "destination": {**point, "x": 50}}))
        self.assertFalse(forever.valid_source({**source, "destination": {**point, "source_url": "https://www.wowhead.com/tbc/zone=4"}}))

    def test_forever_tooltip_preserves_unified_percent_stats(self):
        row = scrape_wowhead.parse_item_stats(
            forever.WOWHEAD_ROOT + "item=71/example", 71, "Fixture Ring", "",
            ["+6 Stamina", "Equip: Improves your chance to hit by 1.0%.", "Equip: +20 Attack Power."],
            "Finger", "rare", "bind_on_pickup", False, [],
        )
        self.assertEqual(row["stats"], {"stamina": 6, "hit_percent": 1, "attack_power": 20})

    def test_forever_tooltip_reads_separate_armor_and_effect_fields(self):
        url = forever.WOWHEAD_ROOT + "item=71"
        for tooltip, expected in (
            ("Head<br>Plate<br>565 Armor<br>Equip: Improves your chance to get a critical strike by <span>2.0%</span>.",
             ("Head", "Plate", {"crit_percent": 2})),
            ("Off Hand<br>Shield<br>1994 Armor<br>Equip: Increased Defense +<span>8.</span>",
             ("Off Hand", "Shield", {"defense": 8})),
        ):
            with self.subTest(expected=expected):
                payload = json.dumps({"name": "Fixture Armor", "quality": 3, "tooltip": tooltip})
                snapshot = scrape_wowhead.parse_item_tooltip_endpoint(url, payload)
                stats = snapshot["item_stats"]
                self.assertEqual((snapshot["inventory_slot"], stats["armor_type"], stats["stats"]), expected)

    def test_forever_tooltip_retains_explicit_drop_evidence(self):
        url = forever.WOWHEAD_ROOT + "item=71"
        payload = json.dumps({"name": "Fixture Ring", "quality": 3, "tooltip": (
            '<div>Finger</div><div class="whtt-extra whtt-droppedby">Dropped by: Fixture Boss</div>'
            '<div class="whtt-extra whtt-dropchance">Drop Chance: 12.50%</div>'
        )})
        snapshot = scrape_wowhead.parse_item_tooltip_endpoint(url, payload)
        self.assertEqual(snapshot["normalized_sources"], [{
            "type": "drop", "entity_name": "Fixture Boss", "drop_percent": 12.5,
            "source_url": url, "confidence": "wowhead_tooltip",
        }])
        self.assertEqual(forever.load_verified_items({url: snapshot}, []), ({}, {}))

    def test_forever_tooltip_identifies_a_toy_outside_the_equipment_slots(self):
        url = forever.WOWHEAD_ROOT + "item=1973"
        payload = json.dumps({"name": "Fixture Toy", "quality": 3, "tooltip": (
            '<b>Fixture Toy</b><br>Binds when used<br><span class="toycolor">Toy</span>'
            '<br>Requires Level 54<br><span class="q2">Use: Changes your appearance.</span>'
        )})
        snapshot = scrape_wowhead.parse_item_tooltip_endpoint(url, payload)
        self.assertEqual(snapshot["item_kind"], "non_equipment")
        self.assertIsNone(snapshot["inventory_slot"])

    def test_forever_tooltip_retains_fishing_skill_requirement(self):
        url = forever.WOWHEAD_ROOT + "item=19972"
        payload = json.dumps({"name": "Lucky Fishing Hat", "quality": 2, "tooltip": (
            'Head<br>Cloth<br>43 Armor<br>+15 Stamina<br>Requires <a href="/forever/skill=356">Fishing</a> (1)'
        )})
        snapshot = scrape_wowhead.parse_item_tooltip_endpoint(url, payload)
        requirement, = snapshot["normalized_requirements"]
        self.assertEqual((requirement["type"], requirement["scope"], requirement["profession"], requirement["skill"]),
                         ("profession", "equip_or_use", "Fishing", 1))
        self.assertNotIn("required_level", snapshot["item_stats"])
        self.assertEqual(scrape_wowhead.extract_profession_requirements(
            "Requires Fishing Pole", url, "equip_or_use", "wowhead_item"), [])

    def test_generated_forever_manifest_loads_only_its_own_dataset(self):
        toc = (ADDON_DIR / "BigBiSList_Camelot.toc").read_text(encoding="utf-8")
        self.assertIn("## Interface: 16001", toc)
        self.assertIn("\nDataForever.lua\n", toc)
        self.assertNotIn("\nData.lua\n", toc)
        for entry in toc.splitlines():
            if entry and not entry.startswith("#"):
                self.assertTrue(ADDON_DIR.joinpath(*entry.split("\\")).is_file(), entry)
        self.assertEqual(
            (ADDON_DIR / "DataForever.lua").read_text(encoding="utf-8"),
            generate_lua.render_lua("forever"),
        )


class ForeverRuntimeTests(unittest.TestCase):
    def test_shared_routes_and_faction_alternatives_reach_the_player_views(self):
        lua = find_lua51()
        if lua is None:
            self.skipTest("Lua 5.1 executable is unavailable")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
UnitRace = function() return "Localized Human", "Human" end
UnitClass = function() return "Warrior", "WARRIOR" end
UnitLevel = function() return 14 end
dofile(arg[1])
if arg[2] == "fixture" then
    local function compact(schema, record)
        local result = {}
        for index, key in ipairs(BigBiSListData.schemas[schema]) do result[index] = record[key] end
        return result
    end
    local function route(side)
        local questID = ({Both = 7, Alliance = 8, Horde = 9})[side or ""] or 10
        return compact("source", {type = "quest", quest_id = questID, entity_name = "Fixture quest",
            zone = side or "Legacy neutral", content_type = "quest", side = side})
    end
    BigBiSListData.items, BigBiSListData.uses = {}, {}
    local sources = {{route("Both")}, {route("Alliance")}, {route("Horde")},
        {route("Alliance"), route("Both")}, {route(nil)}}
    for index, routes in ipairs(sources) do
        local id = 500 + index
        BigBiSListData.items[index] = compact("item", {id = id, name = "Fixture ring " .. id,
            inventory_slot = "Ring", binding = "bop", boe = false, acquisition_phase = "PR",
            primary_source = routes[1], sources = routes})
        BigBiSListData.uses[index] = compact("use", {class = "Warrior", spec = "Protection", phase = "PR",
            slot = "Ring", item_id = id, rank = index, rank_group = "ranked", rank_label = "Alt"})
    end
end
for _, file in ipairs({"Config.lua", "DataIndex.lua", "Widgets.lua", "UI.lua"}) do
    assert(loadfile(file))("BigBiSList")
end
local addon, ui = BigBiSList, BigBiSList.UI
addon:SetContentMode("endgame")
addon:SetSelection("Warrior", "Protection", "PR", "By Slot")
assert(addon:GetPlayerRaceName() == "Human", "race lookup should use the stable Human token")
local function flatten(groups)
    local result = {}
    for _, group in ipairs(groups) do
        for _, row in ipairs(group.items) do result[#result + 1] = row end
    end
    return result
end
local function verify(rows, faction)
    local seen = {}
    for _, row in ipairs(rows) do
        assert(not seen[row.item_id], "each eligible item should appear once")
        seen[row.item_id] = true
        assert(row.item_id ~= (faction == "Alliance" and 503 or 502), "opposing faction item must be excluded")
        local option = row.matched_access_option or row.acquisition_display.option
        assert(option and (not option.side or option.side == "Both" or option.side == faction),
            "displayed acquisition route must match the player's faction")
        local access = ui:GetAccessEvaluation(row)
        assert(access.status == "ready" or access.status == "ready_alternate", "eligible route should pass access evaluation")
    end
    for _, id in ipairs({501, faction == "Alliance" and 502 or 503, 504, 505}) do
        assert(seen[id], "eligible shared or faction route is missing: " .. id)
    end
    assert(#rows == 4, "exactly the four obtainable fixture items should remain")
end
for _, faction in ipairs({"Alliance", "Horde"}) do
    UnitFactionGroup = function() return faction end
    ui.currentAccess = ui:BuildAccessState()
    ui.currentAccessEvaluationCache = nil
    assert(ui.currentAccess.playerSide == faction, "access state should use the game faction")
    local filters = {faction = faction, upgradeMode = "all"}
    local rows = flatten(addon:GetPhaseRows("Warrior", "Protection", "PR", filters))
    if arg[2] == "fixture" then
        verify(rows, faction)
        verify(addon:GetPlannerRows("Warrior", "Protection", "PR", filters), faction)
        verify(addon:GetWishlistRows({["501"]=true, ["502"]=true, ["503"]=true, ["504"]=true, ["505"]=true},
            "Warrior", "Protection", "PR", filters), faction)
        if addon.isForever then
            verify(flatten(addon:GetPhaseRows("Warrior", "Protection", "PR", {})), faction)
            verify(addon:GetPlannerRows("Warrior", "Protection", "PR", {}), faction)
            verify(addon:GetWishlistRows({["501"]=true, ["502"]=true, ["503"]=true, ["504"]=true, ["505"]=true},
                "Warrior", "Protection", "PR", {}), faction)
            local excluded=faction=="Alliance" and 503 or 502
            assert(not addon:GetItemBestUseForSpec(excluded,"Warrior","Protection","PR"),"comparison used an opposing-faction recommendation")
            assert(#addon:GetTooltipMatches(excluded,"Warrior","Protection",true)==0,"tooltip used an opposing-faction recommendation")
        end
    else
        local unfiltered = flatten(addon:GetPhaseRows("Warrior", "Protection", "PR", {}))
        assert(#rows > 0 and #rows == #unfiltered, "published shared Forever recommendations must survive faction filtering")
    end
end
assert(#H.errors == 0, table.concat(H.errors, "\n"))
'''
        for payload, mode in (("DataForever.lua", "published"), ("DataForever.lua", "fixture"), ("Data.lua", "fixture")):
            with self.subTest(payload=payload, mode=mode):
                result = subprocess.run([lua, "-", payload, mode], cwd=ADDON_DIR, input=script, text=True,
                                        capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_both_manifests_boot_from_their_complete_load_lists(self):
        lua = find_lua51()
        if lua is None:
            self.skipTest("Lua 5.1 executable is unavailable")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
local toc, expectedFlavor, collectorTiming = arg[1], arg[2], arg[3]
strmatch = string.match
local tooltipCallbacks = {}
if expectedFlavor == "forever" then
    Enum = { TooltipDataType = { Item = 0 } }
    TooltipDataProcessor = { AddTooltipPostCall = function(kind, callback)
        assert(kind == Enum.TooltipDataType.Item)
        tooltipCallbacks[#tooltipCallbacks + 1] = callback
    end }
    for _, tooltip in ipairs({GameTooltip, ItemRefTooltip}) do
        local hookScript = tooltip.HookScript
        function tooltip:HasScript(event) return event ~= "OnTooltipSetItem" end
        function tooltip:HookScript(event, callback)
            assert(self:HasScript(event), self:GetName() .. " does not support " .. event)
            return hookScript(self, event, callback)
        end
    end
end
local createFrame = CreateFrame
local function noop() end
CreateFrame = function(...)
    local frame = createFrame(...)
    frame.events = {}
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:UnregisterEvent(event) self.events[event] = nil end
    if frame:GetName() == "LibDBIcon10_BigBiSList" then
        local createTexture = frame.CreateTexture
        function frame:CreateTexture(...)
            local texture = createTexture(self, ...)
            function texture:GetVertexColor() return 1, 1, 1 end
            return texture
        end
        function frame:CreateAnimationGroup()
            return {
                SetToFinalAlpha = noop,
                CreateAnimation = function()
                    return {SetOrder = noop, SetDuration = noop, SetFromAlpha = noop,
                        SetToAlpha = noop, SetStartDelay = noop}
                end,
            }
        end
    end
    return frame
end
Minimap = CreateFrame("Frame", "Minimap", UIParent)
Minimap:SetSize(140, 140)
local function fire(event, ...)
    for _, frame in ipairs(H.frames) do
        local callback = frame:GetScript("OnEvent")
        if frame.events and frame.events[event] and callback then callback(frame, event, ...) end
    end
end
SlashCmdList = {}
local lines = {}
DEFAULT_CHAT_FRAME.AddMessage = function(_, line) lines[#lines + 1] = line end
for line in io.lines(toc) do
    local entry = line:match("^%s*(.-)%s*$")
    if entry ~= "" and entry:sub(1, 1) ~= "#" then
        assert(loadfile((entry:gsub("\\", "/"))))("BigBiSList")
    end
end
local bag
local function startCollector()
    -- Leatrix collects existing buttons and subscribes to LibDBIcon_IconCreated.
    bag = CreateFrame("Frame", nil, UIParent)
    bag:Hide()
    local library = LibStub("LibDBIcon-1.0")
    local function collect(_, button)
        if button.db and not button.db.hide then
            button:Hide()
            button:SetScript("OnShow", function()
                if not bag:IsShown() then button:Hide() end
            end)
        end
    end
    for _, name in ipairs(library:GetButtonList()) do
        collect(nil, library:GetMinimapButton(name))
    end
    library.RegisterCallback(bag, "LibDBIcon_IconCreated", collect)
end
if collectorTiming == "before" then startCollector() end
fire("ADDON_LOADED", "BigBiSList")
if collectorTiming == "after" then startCollector() end
fire("PLAYER_LOGIN")
assert(BigBiSList.flavor == expectedFlavor)
assert(BigBiSList.minimapButton, "bundled launcher should initialize")
assert(BigBiSList.tooltipInitialized, "tooltip setup must finish before launcher registration")
if bag then
    local library = LibStub("LibDBIcon-1.0")
    local button = library:GetMinimapButton("BigBiSList")
    assert(button == BigBiSList.minimapButton and not button.db.hide, "collector should find the enabled launcher")
    assert(not button:IsShown(), "collector should hide the launcher while collapsed")
    bag:Show()
    button:SetParent(bag)
    button:ClearAllPoints()
    button:SetPoint("TOPLEFT", bag, "TOPLEFT")
    library:Show("BigBiSList")
    assert(button:IsVisible(), "launcher should appear in the expanded collection")
    local clicks, settings = 0, 0
    local toggle, open, ui = BigBiSList.ToggleMainFrame, BigBiSList.OpenMainFrame, BigBiSList.UI
    BigBiSList.ToggleMainFrame = function() clicks = clicks + 1 end
    BigBiSList.OpenMainFrame = function() clicks = clicks + 1 end
    BigBiSList.UI = {OpenSettings = function() settings = settings + 1 end}
    button:Click("LeftButton")
    button:Click("RightButton")
    assert(clicks == 2 and settings == 1, "collected launcher should retain both click actions")
    BigBiSList.ToggleMainFrame, BigBiSList.OpenMainFrame, BigBiSList.UI = toggle, open, ui
    bag:Hide()
    assert(not button:IsVisible() and not button.db.hide, "collapsing the collection must not disable the launcher")
end
if expectedFlavor == "forever" then
    assert(#tooltipCallbacks == 1, "Forever should register its item tooltip post-call once")
    BigBiSList:InitTooltip()
    assert(#tooltipCallbacks == 1, "repeated setup should not duplicate tooltip callbacks")
    local observedTooltip, observedData
    BigBiSList.AddTooltipInfo = function(_, tooltip, data)
        observedTooltip, observedData = tooltip, data
    end
    local data = {id = 501}
    tooltipCallbacks[1](GameTooltip, data)
    assert(observedTooltip == GameTooltip and observedData == data, "modern item tooltips should reach the addon")
end
assert(BigBiSList:GetCharacterDB().selection.class == "Druid")
SlashCmdList.BIGBISLIST("status")
SlashCmdList.BIGBISLISTTEST("")
SlashCmdList.BIGBISLIST("")
H.settle()
assert(BigBiSList.UI.frame:IsShown(), "slash command should open the addon")
assert(table.concat(lines, "\n"):find("Smoke test passed", 1, true), "smoke command should finish")
assert(#H.errors == 0, table.concat(H.errors, "\n"))
'''
        for toc, flavor in (("BigBiSList.toc", "anniversary"), ("BigBiSList_Camelot.toc", "forever")):
            for collector in ("none", "before", "after"):
                with self.subTest(flavor=flavor, collector=collector):
                    result = subprocess.run(
                        [lua, "-", toc, flavor, collector], cwd=ADDON_DIR, input=script, text=True,
                        capture_output=True, timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_forever_state_quest_steps_and_explicit_waypoint(self):
        lua = find_lua51()
        if lua is None:
            self.skipTest("Lua 5.1 executable is unavailable")
        script = r'''
local H = dofile("tests/lua_ui_harness.lua")
BigBiSListDB = { profile = { sentinel = "anniversary" } }
BigBiSListCharDB = { wishlist = { [123] = true } }
dofile("DataForever.lua")
local function compact(schema, record)
    local result = {}
    for index, key in ipairs(BigBiSListData.schemas[schema]) do result[index] = record[key] end
    return result
end
local boss = compact("source", { type = "drop", content_type = "dungeon", entity_name = "Fixture Boss",
    zone = "Fixture Dungeon", destination = { map_id = 1453, x = 0.43, y = 0.51 } })
BigBiSListData.items = { compact("item", { id = 501, name = "Fixture Ring", inventory_slot = "Ring",
    acquisition_phase = "PR", primary_source = boss, sources = { boss } }) }
BigBiSListData.uses = { compact("use", { class = "Warrior", spec = "Protection", phase = "PR", slot = "Ring",
    item_id = 501, rank = 1, rank_group = "bis", rank_label = "BiS" }) }
for _, file in ipairs({ "Config.lua", "DataIndex.lua", "Widgets.lua", "UI.lua", "DetailsSources.lua", "ComparisonUI.lua" }) do
    assert(loadfile(file))("BigBiSList")
end
local addon = BigBiSList
local ui = addon.UI
local char = addon:GetCharacterDB()
assert(addon.isForever and addon.maxLevelingLevel == 59)
assert(addon:GetAccountDB() == BigBiSListDB.forever and char == BigBiSListCharDB.forever)
assert(BigBiSListDB.profile.sentinel == "anniversary" and BigBiSListCharDB.wishlist[123])
assert(not char.wishlist[123] and #addon:GetPhaseOrder() == 1 and addon:GetPhaseOrder()[1] == "PR")
assert(addon:SetContentMode("leveling"))
assert(addon:GetContentMode() == "leveling")
addon:SetContentMode("endgame")
assert(#ui:GetActiveTabNames() == 4)
assert(addon:GetCurrentPhaseKey() == "PR")
local talentPoints = { {traitNodeGroupID = 11670, currencyInfos = {{spent = 16}}} }
C_ClassTalents = {GetActiveConfigID = function() return 7 end}
C_Traits = {
    GetConfigInfo = function(id) assert(id == 7); return {treeIDs = {1117}} end,
    GetGroupDisplayInfoByTreeID = function(id)
        assert(id == 1117)
        return {{groupID = 11650, displayName = "Arms"}, {groupID = 11657, displayName = "Fury"},
            {groupID = 11670, displayName = "Protection"}}
    end,
    GetGroupCurrencyInfo = function(config, groups)
        assert(config == 7 and #groups == 3)
        return talentPoints
    end,
}
assert(addon:DetectPlayerSpec("Warrior") == "Protection")
talentPoints[2] = {traitNodeGroupID = 11650, currencyInfos = {{spent = 16}}}
assert(addon:DetectPlayerSpec("Warrior") == nil, "a tie must leave the player's selection in control")
talentPoints[2].currencyInfos[1].spent = 17
assert(addon:DetectPlayerSpec("Warrior") == "Arms")
assert(addon:GetItemData(501).sources[1].destination.map_id == 1453)
local rows = addon:GetPhaseRows("Warrior", "Protection", "PR", {})
assert(#rows == 1 and #rows[1].items == 1 and rows[1].items[1].item_id == 501,
    "approved item should appear in the shared BiS view")
GetInventoryItemID = function(_, slot) return slot == 16 and 500 or nil end
C_Container = {
    GetContainerNumSlots = function(bag) return bag == 0 and 1 or 0 end,
    GetContainerItemID = function() return 501 end,
    GetContainerItemLink = function() return "item:501" end,
}
C_Item = {
    GetItemInfo = function(id) return "Fixture " .. id, "item:" .. id, 3, 60, 60 end,
    GetItemInfoInstant = function(id) return id, nil, nil, "INVTYPE_2HWEAPON" end,
}
ui.currentOwned = ui:BuildOwnedItems()
assert(ui.currentOwned[500] == "equipped" and ui.currentOwned[501] == "bag")
assert(ui.currentOwned.equippedTwoHand and ui:GetItemInfo(500) == "Fixture 500")
C_Container.GetContainerNumSlots = function() error("restricted") end
ui.currentOwned = ui:BuildOwnedItems()
assert(ui:GetOwnershipState(501) == "unknown" and ui:GetOwnershipState(500) == "equipped")
addon:SetSelection("Warrior", "Protection", "PR", "By Slot")
ui:Open()
H.settle()
assert(ui.frame:IsShown() and ui.phaseBar:IsShown() and ui.levelingModeButton:IsShown())

local location = { map_id = 1453, x = 0.43, y = 0.51 }
local finish = { map_id = 1453, x = 0.62, y = 0.50 }
local state, waypoints, combat, lastPoint = "not-started", 0, false
C_QuestLog = {
    IsQuestFlaggedCompleted = function(id) return id == 10 and state == "done" end,
    IsOnQuest = function(id) return id == 10 and (state == "active" or state == "ready") end,
    IsComplete = function(id) return id == 10 and state == "ready" end,
}
C_Map = {
    CanSetUserWaypointOnMap = function(id) return id == 1453 end,
    SetUserWaypoint = function(point) assert(point[1] == 1453); lastPoint = point; waypoints = waypoints + 1; return true end,
}
UiMapPoint = { CreateFromCoordinates = function(...) return {...} end }
InCombatLockdown = function() return combat end
local source = { quest_steps = {
    { quest_id = 9, name = "Alternative chain", kind = "alternative" },
    { quest_id = 10, name = "First step", kind = "prerequisite", start = location, finish = finish },
    { quest_id = 11, name = "Reward", kind = "reward" },
} }
local parent = CreateFrame("Frame", nil, UIParent)
parent:SetSize(300, 400)
local anchor = CreateFrame("Frame", nil, parent)
anchor:SetSize(284, 20)
local function renderSteps(accessStatus)
    ui:BeginDetailsRender()
    local chain, height = ui:CreateAcquisitionSteps(parent, anchor, {source = source}, accessStatus)
    local waypoint = ui.detailsWidgetPools["source-waypoint"] and ui.detailsWidgetPools["source-waypoint"][1]
    return chain, waypoint and waypoint:IsShown() and waypoint or nil, height
end
local chain, startBlock, height = renderSteps()
local nextQuest = ui.detailsWidgetPools.text[1]
assert(nextQuest.title:GetText() == "Next quest" and nextQuest.body:GetText():find("First step", 1, true))
assert(chain.title:GetText() == "Quest steps" and chain.body:GetText():find("Alternative chain", 1, true))
assert(startBlock.destination == location and nextQuest:GetBottom() > startBlock:GetTop() and startBlock:GetBottom() > chain:GetTop(),
    "the waypoint action belongs between the next quest and the full chain")
assert(height > 24 and waypoints == 0, "render must not replace an existing waypoint")
combat = true
assert(not ui:SetAcquisitionWaypoint(location) and waypoints == 0)
combat = false
local canSet = C_Map.CanSetUserWaypointOnMap
C_Map.CanSetUserWaypointOnMap = function() return true end
assert(not ui:SetAcquisitionWaypoint({name = "Textual quest giver", entity_id = 71, kind = "quest_start"}) and waypoints == 0,
    "textual quest endpoints must never enable a waypoint")
C_Map.CanSetUserWaypointOnMap = canSet
assert(ui:SetAcquisitionWaypoint(location) and waypoints == 1 and lastPoint[2] == 0.43)
state = "active"
assert(ui:GetAcquisitionQuestState(10) == "In progress")
local _, activeBlock = renderSteps()
assert(not activeBlock, "an active quest with no verified current point should keep its text only")
state = "ready"
local _, readyBlock = renderSteps()
assert(readyBlock.button and readyBlock.destination == finish and waypoints == 1)
readyBlock.button:GetScript("OnClick")(readyBlock.button, "LeftButton")
assert(waypoints == 2 and lastPoint[2] == 0.62, "the explicit action should use the turn-in point")
state = "done"
assert(ui:GetAcquisitionQuestState(10) == "Completed")
local _, futureBlock = renderSteps("future")
assert(not futureBlock, "future routes should not offer a waypoint")
local vendorBlock = ui:CreateAcquisitionSteps(parent, anchor, {source = {type = "vendor", destination = location}})
assert(vendorBlock.button and vendorBlock.destination == location and waypoints == 2)
C_QuestLog = nil
assert(ui:GetAcquisitionQuestState(10) == "Unknown")
assert(ui:CreateAcquisitionSteps(parent, anchor, {source = {}}) == anchor)
'''
        result = subprocess.run([lua, "-"], cwd=ADDON_DIR, input=script, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
