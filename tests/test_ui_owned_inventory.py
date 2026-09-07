"""Inventory capture and fixed inspector actions exercise the assembled client harness."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


class OwnedInventoryUITests(unittest.TestCase):
    def run_lua(self, body):
        lua = find_lua51()
        if not lua:
            self.skipTest("Lua 5.1 unavailable")
        result = subprocess.run([lua, "-"], cwd=ADDON_DIR, input=r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
ui:Open(); H.settle()
''' + body, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_snapshot_keeps_all_locations_and_equipment_metadata(self):
        self.run_lua(r'''
H.equipped[11], H.equipped[12] = 900001, 900001
GetItemInfoInstant = function(id)
    return id, "Armor", "Misc", ({[900001]="INVTYPE_FINGER",[900002]="INVTYPE_NECK",[900003]="INVTYPE_TRINKET",[900004]="INVTYPE_RELIC"})[id]
end
GetContainerNumSlots = function(bag) return bag == 0 and 4 or 0 end
GetContainerItemID = function(bag, slot) return 900000 + slot end
GetContainerItemLink = function(bag, slot) return "item:" .. (900000 + slot) end
BigBiSList:GetCharacterDB().bankCache = {scanned=true,updatedAt="yesterday",items={["900001"]=true},links={"item:900001"}}
local owned = ui:BuildOwnedItems()
assert(owned[900001] == "equipped", "flat ownership precedence changed")
local entry = owned.inventoryItems[900001]
assert(entry.locations.equipped and entry.locations.bags and entry.locations.bank, "lost a known location")
assert(owned.equippedSlots.Finger0.item_id == 900001 and owned.equippedSlots.Finger1.item_id == 900001, "duplicate physical occupancy lost")
assert(owned.inventoryItems[900002].equip_location == "INVTYPE_NECK", "neck metadata missing")
assert(owned.inventoryItems[900003].equip_location == "INVTYPE_TRINKET", "trinket metadata missing")
assert(owned.inventoryItems[900004].equip_location == "INVTYPE_RELIC", "relic metadata missing")
assert(owned.bankScanned and owned.bankUpdatedAt == "yesterday", "bank freshness changed")
''')

    def test_delayed_owned_metadata_coalesces_requests_and_refreshes(self):
        self.run_lua(r'''
local loaded, calls, callback = false, 0
GetItemInfoInstant = function(id) if loaded then return id, "Armor", "Misc", "INVTYPE_NECK" end end
GetItemInfo = function(id) if loaded then return "Later necklace", "item:"..id, 4, 70, 70, "Armor", "Misc", 1, "INVTYPE_NECK", "icon" end end
GetContainerNumSlots = function(bag) return bag == 0 and 2 or 0 end
GetContainerItemID = function() return 900009 end
GetContainerItemLink = function() return "item:900009" end
Item = {CreateFromItemID=function(_, id)
    calls = calls + 1
    return {ContinueOnItemLoad=function(_, fn) callback=fn end,
        GetItemName=function() return "Later necklace" end, GetItemLink=function() return "item:"..id end, GetItemIcon=function() return "icon" end}
end}
local first = ui:BuildOwnedItems()
assert(first.inventoryItems[900009] and not first.inventoryItems[900009].equip_location, "unresolved occupancy discarded")
ui:BuildOwnedItems()
assert(calls == 1, "duplicate metadata requests")
loaded = true; callback(); H.settle()
assert(ui.currentOwned.inventoryItems[900009].equip_location == "INVTYPE_NECK", "loaded item did not enter the next ownership snapshot")
assert(calls == 1, "metadata refresh loop")
''')

    def test_id_only_bank_items_use_cached_names_links_and_alphabetical_order(self):
        self.run_lua(r'''
H.itemNames[990001]="Zebra Helm"; H.itemNames[990002]="Alpha Helm"
BigBiSList:GetCharacterDB().bankCache={scanned=true,items={["990001"]=true,["990002"]=true},links={}}
local owned=ui:BuildOwnedItems()
assert(owned.inventoryItems[990001].name=="Zebra Helm" and owned.inventoryItems[990001].item_link=="item:990001","ID-only bank item missed cached metadata")
assert(owned.inventoryItems[990002].name=="Alpha Helm" and owned.inventoryItems[990002].item_link=="item:990002")
ui.currentOwned=owned
ui:OpenSlotComparison({slot="Head"}); ui:SetComparisonOwnership("owned"); ui:SetComparisonSort("item")
local rows={}
for _,entry in ipairs(ui.slotComparison.entries) do if entry.data then rows[#rows+1]=entry.data end end
assert(#rows==2 and rows[1].item_id==990002 and rows[2].item_id==990001,"visible item names and Item ordering disagree")
owned.inventoryItems[990001].name="Existing known name"
ui:AddOwnedInventoryItem(owned,990001,nil,"bank")
assert(owned.inventoryItems[990001].name=="Existing known name","cached lookup overwrote established metadata")
''')

    def test_compare_action_stays_fixed_and_clears_ineligible_bindings(self):
        self.run_lua(r'''
ui:SetTab("By Slot"); H.settle()
local data
for _, entry in ipairs(ui.renderModel.entries) do if entry.kind == "row" then data=entry.data; break end end
assert(data, "recommendation fixture")
ui:ShowInspectorFor(data.item_id, data, "phase"); H.settle()
local button = ui.detailsCompareButton
assert(button:IsVisible(), "fixed compare action hidden")
assert(ui.detailsActionStrip:GetHeight() == 36, "action strip height")
local top = button:GetTop()
ui.detailsScroll:SetVerticalScroll(math.max(0,ui.detailsContent:GetHeight()-ui.detailsScroll:GetHeight())); H.settle()
assert(button:GetTop() == top, "compare action scrolls with body")
H.expectBounded(button,ui.detailsActionStrip,"compare action")
assert(ui.detailsScroll:GetTop() <= ui.detailsActionStrip:GetBottom(), "body overlaps actions")
button:Click(); H.settle()
assert(ui:IsSlotComparisonOpen(), "fixed action did not open comparison")
ui:ShowComparisonDetails(ui.slotComparison.rows[1]); H.settle()
assert(not button:IsVisible() and not button.boundData, "comparison Details can restart comparison")
ui:CloseSlotComparison(); H.settle()
ui:ShowInspectorFor(123, {spell_id=123,entity_id=123,name="Spell"}, "enhance"); H.settle()
assert(not button:IsVisible() and not button.boundData, "spell retained compare binding")
''')

    def test_known_slot_still_loads_missing_bank_name_and_link(self):
        self.run_lua(r'''
H.coldItems[990003]=true
H.itemNames[990003]="Cache loaded helm"
BigBiSList:GetCharacterDB().bankCache={scanned=true,items={["990003"]=true},links={}}
local callback,calls
calls=0
Item={CreateFromItemID=function(_,id)
    calls=calls+1
    return {ContinueOnItemLoad=function(_,fn) callback=fn end,
        GetItemName=function() return "Cache loaded helm" end,
        GetItemLink=function() return "item:"..id end,
        GetItemIcon=function() return "loaded-icon" end}
end}
local first=ui:BuildOwnedItems()
assert(first.inventoryItems[990003].equip_location=="INVTYPE_HEAD" and not first.inventoryItems[990003].name)
assert(callback and calls==1,"known physical slot suppressed missing name/link request")
ui:BuildOwnedItems(); assert(calls==1,"name-only load was not coalesced")
H.coldItems[990003]=nil; callback(); H.settle()
local entry=ui.currentOwned.inventoryItems[990003]
assert(entry.name=="Cache loaded helm" and entry.item_link=="item:990003","name-only callback did not refresh the ownership snapshot")
assert(calls==1,"name-only metadata request loop")
''')


if __name__ == "__main__":
    unittest.main()
