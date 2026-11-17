"""Character tracking resumes when manual selections match detected values."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


BOOTSTRAP = r'''
local H = dofile("tests/lua_ui_harness.lua")
local level, activeSpec, specAvailable = 42, "Arms", true
local specs = { "Arms", "Fury", "Protection" }
UnitLevel = function() return level end
UnitClassBase = function() return "WARRIOR" end
UnitClass = function() return "Warrior", "WARRIOR" end
GetNumTalentTabs = function() return specAvailable and #specs or 0 end
GetTalentTabInfo = function(index)
    local name = specs[index]
    return name, nil, name == activeSpec and 31 or 0
end
C_ClassTalents = { GetActiveConfigID = function() return specAvailable and 7 or nil end }
C_Traits = {
    GetConfigInfo = function() return { treeIDs = { 1117 } } end,
    GetGroupDisplayInfoByTreeID = function()
        local groups = {}
        for index, name in ipairs(specs) do
            groups[index] = { groupID = index, displayName = name }
        end
        return groups
    end,
    GetGroupCurrencyInfo = function()
        local groups = {}
        for index, name in ipairs(specs) do
            groups[index] = { traitNodeGroupID = index, currencyInfos = { { spent = name == activeSpec and 31 or 0 } } }
        end
        return groups
    end,
}
local ui = H.load("__FLAVOR__")
local addon = BigBiSList
local char = addon:GetCharacterDB()
addon:ResetClassSpecAutoSelection()
addon:ApplyDetectedPlayerSelection()
addon:SetContentMode("leveling")
ui:Open(); H.settle()
local function expectCurrentLevel()
    assert(char.leveling.manualLevel == false, "current level must resume tracking")
    assert(addon:GetSelectedLevelingLevel() == addon:GetDetectedPlayerLevel(), "current level is stale")
    assert(ui.levelControlLabel:GetText() == "Level", "current level is still labeled Preview")
    assert(not ui.levelCurrentButton:IsShown(), "current level still exposes a reset action")
end
local function expectCurrentCharacter()
    expectCurrentLevel()
    assert(addon.classSpecAutoSelectionActive ~= false, "current spec must resume tracking")
    assert(ui:GetSelection().class == "Warrior" and ui:GetSelection().spec == activeSpec, "current spec is stale")
    assert(not ui.useCharacterButton:IsEnabled(), "matching character still exposes an enabled reset")
end
local function expectPreview(selected)
    assert(char.leveling.manualLevel == true, "different level must remain a preview")
    assert(addon:GetSelectedLevelingLevel() == selected, "preview level was overwritten")
    assert(ui.levelControlLabel:GetText() == "Preview", "preview caption is missing")
    assert(ui.levelCurrentButton:IsShown(), "preview needs Current Level")
    assert(ui.useCharacterButton:IsEnabled(), "preview needs the character reset")
end
'''


class CharacterTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, script):
        if not self.lua:
            self.skipTest("Lua 5.1 is unavailable")
        for flavor in ("forever", "anniversary"):
            with self.subTest(flavor=flavor):
                result = subprocess.run(
                    [self.lua, "-"], cwd=ADDON_DIR,
                    input=BOOTSTRAP.replace("__FLAVOR__", flavor) + script + r'''
assert(#H.errors == 0, table.concat(H.errors, "\n"))
''', capture_output=True, encoding="utf-8", timeout=90,
                )
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_returning_to_current_level_with_arrows_or_entry_resumes_tracking(self):
        self.run_lua(r'''
expectCurrentCharacter()
ui.levelUpButton:Click(); H.settle(); expectPreview(43)
ui.levelDownButton:Click(); H.settle(); expectCurrentCharacter()
ui.levelDownButton:Click(); H.settle(); expectPreview(41)
ui.levelUpButton:Click(); H.settle(); expectCurrentCharacter()
for _, event in ipairs({ "OnEnterPressed", "OnEditFocusLost" }) do
    ui.levelUpButton:Click(); H.settle(); expectPreview(43)
    ui.levelInput:SetFocus()
    ui.levelInput:SetText("42")
    if event == "OnEditFocusLost" then ui.levelInput:ClearFocus() end
    ui.levelInput:GetScript(event)(ui.levelInput)
    H.settle(); expectCurrentCharacter()
end
for _ = 1, 3 do ui:Refresh(); H.settle(); expectCurrentCharacter() end
level = 43
assert(addon:ApplyDetectedPlayerLevel(), "level-up must update a resumed selection")
ui:RefreshControls(); H.settle(); expectCurrentCharacter()
''')

    def test_returning_to_current_spec_or_class_resumes_tracking(self):
        self.run_lua(r'''
ui:SetSpec("Fury"); H.settle()
assert(addon.classSpecAutoSelectionActive == false and ui.useCharacterButton:IsEnabled())
ui:SetSpec("Arms")
assert(addon.classSpecAutoSelectionActive == true, "manual return must immediately resume spec tracking")
H.settle(); expectCurrentCharacter()
ui:SetClass("Mage"); H.settle()
assert(addon.classSpecAutoSelectionActive == false and ui.useCharacterButton:IsEnabled())
ui:SetClass("Warrior"); H.settle()
if ui:GetSelection().spec ~= activeSpec then ui:SetSpec(activeSpec); H.settle() end
expectCurrentCharacter()
activeSpec = "Fury"
assert(addon:ApplyDetectedPlayerSelection(), "spec changes must update a resumed selection")
ui:RefreshControls(); H.settle(); expectCurrentCharacter()
ui:SetSpec(activeSpec); H.settle(); expectCurrentCharacter()
for _ = 1, 3 do
    assert(not addon:ApplyDetectedPlayerSelection(), "stable detection must not report another change")
    ui:Refresh(); H.settle(); expectCurrentCharacter()
end
''')

    def test_character_catching_up_resumes_spec_and_level_independently(self):
        self.run_lua(r'''
ui:SetSpec("Fury"); ui:SetLevelingLevel(43); H.settle()
expectPreview(43)
activeSpec = "Fury"
assert(addon:ApplyDetectedPlayerSelection(), "clearing only the spec override must report a change")
assert(addon.classSpecAutoSelectionActive == true and char.leveling.manualLevel == true)
ui:RefreshControls(); H.settle(); expectPreview(43)
activeSpec = "Protection"
assert(addon:ApplyDetectedPlayerSelection())
assert(ui:GetSelection().spec == "Protection" and char.leveling.manualLevel == true)
level = 43
char.leveling.lastDetectedLevel = level
assert(addon:ApplyDetectedPlayerLevel(), "clearing only the level override must report a change")
assert(not addon:ApplyDetectedPlayerLevel(), "stable level detection must not report another change")
ui:RefreshControls(); H.settle(); expectCurrentCharacter()
level, activeSpec = 44, "Arms"
assert(addon:ApplyDetectedPlayerLevel() and addon:ApplyDetectedPlayerSelection())
ui:RefreshControls(); H.settle(); expectCurrentCharacter()
''')

    def test_returning_one_setting_preserves_the_other_manual_override(self):
        self.run_lua(r'''
ui:SetSpec("Fury"); ui:SetLevelingLevel(43); H.settle()
ui:SetLevelingLevel(42); H.settle()
expectCurrentLevel()
assert(addon.classSpecAutoSelectionActive == false and ui:GetSelection().spec == "Fury")
assert(ui.useCharacterButton:IsEnabled(), "manual spec still needs a reset")
ui:SetLevelingLevel(43); ui:SetSpec("Arms"); H.settle()
assert(addon.classSpecAutoSelectionActive == true, "matching spec must resume independently")
expectPreview(43)
ui:SetLevelingLevel(42); H.settle(); expectCurrentCharacter()
''')

    def test_unavailable_detection_does_not_clear_manual_choices(self):
        self.run_lua(r'''
level, specAvailable = nil, false
ui:SetLevelingLevel(42)
ui:SetSpec("Fury")
local detected = addon:GetDetectedPlayerSelection()
assert(detected and not detected.specDetected, "fixture must exercise a fallback spec")
ui:SetSpec(detected.spec); H.settle()
assert(addon.classSpecAutoSelectionActive == false, "fallback spec must not resume tracking")
expectPreview(42)
for _ = 1, 3 do
    assert(not addon:ApplyDetectedPlayerSelection(), "unavailable spec must keep the manual choice")
    assert(not addon:ApplyDetectedPlayerLevel(), "unavailable level must keep the manual choice")
    ui:RefreshControls(); H.settle(); expectPreview(42)
    assert(addon.classSpecAutoSelectionActive == false)
end
level, specAvailable, activeSpec = 42, true, detected.spec
assert(addon:ApplyDetectedPlayerSelection() and addon:ApplyDetectedPlayerLevel())
ui:RefreshControls(); H.settle(); expectCurrentCharacter()
''')

    def test_current_level_comparison_uses_existing_normalized_bounds(self):
        self.run_lua(r'''
addon:SetSelectedLevelingLevel("42.9", true)
assert(char.leveling.manualLevel == false and addon:GetSelectedLevelingLevel() == 42)
level = 1
addon:SetSelectedLevelingLevel(0, true)
assert(char.leveling.manualLevel == false and addon:GetSelectedLevelingLevel() == 1)
level = addon.maxLevelingLevel + 1
addon:SetSelectedLevelingLevel(1000, true)
assert(char.leveling.manualLevel == false and addon:GetSelectedLevelingLevel() == addon.maxLevelingLevel)
ui:RefreshControls(); H.settle(); expectCurrentCharacter()
''')

    def test_controls_read_the_reconciled_level_in_the_same_refresh(self):
        self.run_lua(r'''
ui:SetLevelingLevel(43); H.settle(); expectPreview(43)
level = 43
ui:RefreshControls(); H.settle(); expectCurrentCharacter()
''')


if __name__ == "__main__":
    unittest.main()
