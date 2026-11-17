"""Prerequisite item cards keep reward Details and per-route source identities intact."""
import subprocess
import unittest

from tests.test_addon_runtime_lua import find_lua51
from tools.project import ADDON_DIR


class DetailsSourceUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = find_lua51()

    def run_lua(self, body):
        if not self.lua:
            self.skipTest("Lua 5.1 unavailable")
        result = subprocess.run([self.lua, "-"], cwd=ADDON_DIR, input=r'''
local H = dofile("tests/lua_ui_harness.lua")
local ui = H.load()
if not ui.CreateDetailsSourceItems then assert(loadfile("DetailsSources.lua"))("BigBiSList") end
local actualSourceItems,actualRefreshDetails=BigBiSList.GetAccessOptionSourceItems,ui.RefreshDetails
local function near(a,b,label) assert(math.abs(a-b)<.7,label..": "..a.." vs "..b) end
local panel=CreateFrame("Frame",nil,UIParent)
panel:SetSize(284,1400); panel:SetPoint("TOPLEFT",UIParent,"TOPLEFT",20,-20)
local anchor=CreateFrame("Frame",nil,panel)
anchor:SetSize(268,1); anchor:SetPoint("TOPLEFT",panel,"TOPLEFT",8,-8)
local context={phase="T5",filters={sourceType="raid"}}
BigBiSList.GetAccessOptionSourceItems=function(self,option,passedContext)
    assert(passedContext==context,"source context was replaced")
    return option.sourceItems or {}
end
local function origin(index,rate)
    return {key="origin"..index,entity_name="Boss "..index,zone="Raid "..index,
        source_type="raid",difficulty="Normal",rate_text=rate or "25%",
        available=true,matched=true,source_url="https://example.invalid/source/"..index}
end
local function item(id,routes)
    return {key="token:"..id,kind="token",item_id=id,name="Required item "..id,count=1,routes=routes or {origin(1)}}
end
local option={key="selected",sourceItems={item(80001)}}
local block
local function render()
    ui:BeginDetailsRender()
    block=ui:CreateDetailsSourceItems(panel,anchor,option,"reward:100:selected",context)
end
ui.RefreshDetails=function() render() end
local function revealSourceCard(id)
    local function findCard()
        for _, sourceBlock in ipairs(ui.detailsWidgetPools["source-items"] or {}) do
            for _, card in ipairs(sourceBlock.cards) do
                if card:IsVisible() and card.identity.itemId == id then return card, sourceBlock end
            end
        end
    end
    local card, sourceBlock = findCard()
    if card then return card, sourceBlock end
    for _, routes in ipairs(ui.detailsWidgetPools["source-routes"] or {}) do
        if routes:IsVisible() and not ui:IsDetailsSectionExpanded(routes.sectionKey, routes.defaultExpanded) then
            routes.header:Click(); H.settle()
            card, sourceBlock = findCard()
            if card then return card, sourceBlock end
        end
    end
end
''' + body + r'''
assert(#H.errors==0,table.concat(H.errors,"\n"))
''', capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_distinct_same_name_prerequisites_keep_rates_and_native_item_identity(self):
        self.run_lua(r'''
H.itemNames[32385]="Magtheridon's Head"; H.itemNames[32386]="Magtheridon's Head"
option.sourceItems={item(32385,{origin(1,"46.09%")}),item(32386,{origin(1,"41%")})}
option.sourceItems[1].kind="quest_starter"; option.sourceItems[2].kind="quest_starter"
render()
assert(#block.cards==2,"same-name source items were merged")
assert(block.cards[1].identity.itemId==32385 and block.cards[2].identity.itemId==32386)
assert(block.cards[1].originRows[1].rate:GetText()=="46.09%")
assert(block.cards[2].originRows[1].rate:GetText()=="41%")
block.cards[2].identity:GetScript("OnEnter")(block.cards[2].identity)
assert(GameTooltip.hyperlink=="item:32386","hover shows reward or wrong same-name prerequisite")
assert(block.cards[2].identity.hover:IsShown(),"native tooltip overwrote hover state")
block.cards[2].identity:GetScript("OnLeave")(block.cards[2].identity)
assert(not block.cards[2].identity.hover:IsShown())
''')

    def test_modifier_and_native_reference_clicks_preserve_reward_and_comparison(self):
        self.run_lua(r'''
ui.selectedItemId=100; ui.selectedItemData={item_id=100}; ui.selectedRowKey="reward-row"
ui.selectedItemMode="comparison"; ui.slotComparison={detailsOpen=true,reference=90001}
local selectedData,comparison=ui.selectedItemData,ui.slotComparison
ui.ShowInspectorFor=function() error("prerequisite click replaced reward Details") end
ui.ShowItemActionMenu=function() error("prerequisite got reward actions") end
render()
local identity=block.cards[1].identity
identity:Click(); assert(H.referenceLink=="item:80001","plain click missing native reference")
H.modifiers.shift=true; identity:Click(); H.modifiers.shift=false
assert(H.chatLink=="item:80001","Shift linked reward instead of prerequisite")
H.modifiers.control=true; identity:Click(); H.modifiers.control=false
assert(H.previewLink=="item:80001","Ctrl previewed reward instead of prerequisite")
H.referenceLink=nil; identity:Click("RightButton")
assert(H.referenceLink=="item:80001","right click must stay within native item reference")
assert(ui.selectedItemId==100 and ui.selectedItemData==selectedData and ui.selectedRowKey=="reward-row")
assert(ui.slotComparison==comparison and comparison.reference==90001 and comparison.detailsOpen)
''')

    def test_five_origin_paging_is_bounded_and_local_to_reward_route_and_item(self):
        self.run_lua(r'''
local origins={}; for index=1,160 do origins[index]=origin(index) end
option.sourceItems[1].routes=origins
render()
local card=block.cards[1]
assert(#card.originRows==5 and card.pageCount==32,"all source rows were realized")
assert(card.previous:IsShown() and not card.previous:IsEnabled() and card.next:IsEnabled())
local cardIdentity=card
card.next:Click()
card=block.cards[1]
assert(card==cardIdentity and #card.originRows==5,"paging grew the source pool")
assert(card.originRows[1].origin.key=="origin6")
assert(ui.detailsSourcePages[card.pageKey]==2 and card.previous:IsEnabled())
ui:BeginDetailsRender()
local other=ui:CreateDetailsSourceItems(panel,anchor,option,"reward:100:alternative",context)
assert(other.cards[1].originRows[1].origin.key=="origin1","page leaked across routes")
ui:BeginDetailsRender()
other=ui:CreateDetailsSourceItems(panel,anchor,option,"reward:101:selected",context)
assert(other.cards[1].originRows[1].origin.key=="origin1","page leaked across rewards")
render(); assert(block.cards[1].originRows[1].origin.key=="origin6","return lost original route page")
option.sourceItems[1].routes={origin(1)}; render()
card=block.cards[1]
assert(ui.detailsSourcePages[card.pageKey]==1,"shorter source list did not clamp obsolete page")
assert(not card.previous:IsShown() and not card.next:IsShown() and not card.pageLabel:IsShown())
for index=2,5 do assert(not card.originRows[index]:IsShown()) end
''')

    def test_alternative_cards_collapse_with_section_and_do_not_toggle_it(self):
        self.run_lua(r'''
local section
local entries={{key="a",option=option,text="Turn in the required item at the quest giver."},
    {key="b",option={sourceItems={item(80002)}},text="An alternative route."}}
local function renderSection()
    ui:BeginDetailsRender()
    section=ui:CreateDetailsSourceRoutes(panel,anchor,"reward:100:other-routes","Other routes",entries,context)
end
ui.RefreshDetails=renderSection
renderSection()
assert(ui:IsDetailsSectionExpanded(section.sectionKey),"new route sections must start expanded")
local sourceBlock=ui.detailsWidgetPools["source-items"][1]
local identity=sourceBlock.cards[1].identity
panel:Hide()
-- The game dispatches OnHide to still-shown descendants when a parent hides.
section:GetScript("OnHide")(section)
sourceBlock:GetScript("OnHide")(sourceBlock)
assert(section.sectionKey=="reward:100:other-routes" and identity.itemId==80001,"ancestor hide released cached route bindings")
panel:Show()
identity:Click()
assert(ui:IsDetailsSectionExpanded(section.sectionKey),"source item click collapsed its route")
section.header:Click()
assert(not ui:IsDetailsSectionExpanded(section.sectionKey) and section:GetHeight()==28)
assert(not sourceBlock:IsVisible() and not identity.itemId,"collapsed pooled source binding remained active")
H.referenceLink=nil; identity:GetScript("OnClick")(identity,"LeftButton")
assert(H.referenceLink==nil,"stale collapsed source control remained effective")
section.header:Click()
assert(ui:IsDetailsSectionExpanded(section.sectionKey) and sourceBlock:IsVisible())
assert(sourceBlock.cards[1].identity.itemId==80001,"expansion lost source binding")
''')

    def test_cold_cache_rebinding_cannot_replace_new_source_or_reward(self):
        self.run_lua(r'''
local callbacks={}
Item={CreateFromItemID=function(_,id)
    return {ContinueOnItemLoad=function(_,callback) callbacks[id]=callback end,
        GetItemName=function() return "Loaded "..id end,
        GetItemLink=function() return "item:"..id end,
        GetItemIcon=function() return "texture:"..id end}
end}
H.coldItems[80001]=true; H.coldItems[80002]=true
ui.selectedItemId=100
render()
local identity=block.cards[1].identity
identity:GetScript("OnEnter")(identity)
assert(GameTooltip.hyperlink=="item:80001","uncached prerequisite cannot be inspected")
option.sourceItems={item(80002)}; render()
assert(block.cards[1].identity==identity,"identity widget was not pooled")
callbacks[80001]()
assert(identity.itemId==80002 and not block.cards[1].name:GetText():find("Loaded 80001",1,true),"late old callback rebound pooled item")
callbacks[80002]()
assert(block.cards[1].name:GetText()=="Loaded 80002" and identity.itemLink=="item:80002")
assert(ui.selectedItemId==100,"source loading changed reward")
local token=identity.itemBindToken
ui:BeginDetailsRender()
assert(identity.itemId==nil and identity.itemBindToken>token and identity.__bigBisTooltip==nil)
H.referenceLink=nil; identity:GetScript("OnClick")(identity,"LeftButton")
assert(H.referenceLink==nil,"released source card still opened an item")
ui:SetSpellButton(identity,12,block.cards[1].name,"Spell",{spell_id=12},"enhance")
assert(not identity.itemId and identity.spellId==12,"pooled spell rebind kept source item")
option.sourceItems={item(80001)}; render()
assert(identity.itemId==80001 and not identity.spellId and not identity.spellLink,"source rebind retained spell")
''')

    def test_narrow_geometry_centers_identity_and_bounds_origin_cells(self):
        self.run_lua(r'''
H.itemNames[80001]=string.rep("A lengthy prerequisite name ",10)
option.sourceItems[1].count=15
option.sourceItems[1].routes={origin(1,"Unknown"),origin(2,"0%"),origin(3,"91.53%"),origin(4),origin(5),origin(6)}
option.sourceItems[1].routes[1].entity_name=string.rep("Long boss name ",10)
option.sourceItems[1].routes[1].available=false
option.sourceItems[1].routes[1].availability_label="Future: T6"
option.sourceItems[1].routes[1].matched=false
for _,width in ipairs({268,252,210}) do
    anchor:SetWidth(width); panel:SetWidth(width+16)
    render()
    local card=block.cards[1]
    H.expectBounded(card,block,"card")
    for _,node in ipairs({card.identity,card.role,card.sourceHeading,card.rateHeading,card.previous,card.next,card.pageLabel}) do
        H.expectBounded(node,card,"source card child")
    end
    for _,node in ipairs({card.identity.icon,card.name,card.quantity}) do H.expectBounded(node,card.identity,"identity content") end
    local _,cy=card.identity:GetCenter(); local _,iy=card.identity.icon:GetCenter(); local _,ny=card.name:GetCenter()
    near(cy,iy,"source icon center"); near(cy,ny,"source name block center")
    assert(card.identity:GetHeight()==44 and card.identity.icon:GetWidth()==28)
    assert(card.name.isTruncated and card.name:GetHeight()==26)
    assert(card.rateHeading:GetText()=="Recorded rate" and not card.rateHeading.isTruncated,"recorded rate heading was truncated")
    assert(card.rateHeading:GetBottom()>=card.originRows[1]:GetTop()+3,"recorded rate heading overlaps first source")
    local _,sourceHeadingY=card.sourceHeading:GetCenter(); local _,rateHeadingY=card.rateHeading:GetCenter()
    near(sourceHeadingY,rateHeadingY,"source column heading centers")
    for _,row in ipairs(card.originRows) do
        H.expectBounded(row,card,"source row")
        for _,cell in ipairs({row.name,row.detail,row.rate}) do H.expectBounded(cell,row,"source cell") end
        assert(row.rate:GetWidth()==64 and row.name:GetRight()<=row.rate:GetLeft()-7,"source/rate overlap")
    end
    assert(card.originRows[1].rate:GetText()=="Unknown" and card.originRows[2].rate:GetText()=="0%")
    card.originRows[1]:GetScript("OnEnter")(card.originRows[1])
    local full=table.concat(GameTooltip.lines,"\n")
    assert(full:find("Future: T6",1,true) and full:find("Outside current filters",1,true),"truncated origin loses availability context")
end
''')

    def test_chain_gate_label_and_no_source_items_are_explicit(self):
        self.run_lua(r'''
option.sourceItems[1].kind="quest_starter"
option.sourceItems[1].relationship="quest_chain_gate"
render(); assert(block.cards[1].role:GetText()=="Starts a required quest")
option.sourceItems={}; render()
assert(block==nil,"empty source metadata created a blank card")
assert(not ui.detailsWidgetPools["source-items"][1]:IsVisible())
''')

    def test_real_details_loads_route_cards_and_keeps_comparison_return_at_supported_sizes(self):
        self.run_lua(r'''
BigBiSList.GetAccessOptionSourceItems=actualSourceItems
ui.RefreshDetails=actualRefreshDetails
ui:Open(); H.settle(); ui:SetTab("By Slot"); ui:SetPhase("T6"); H.settle()
local reward={item_id=31039,slot="Head",name="Thunderheart Cover"}
for _,size in ipairs({{1020,560},{1160,660}}) do
    for _,density in ipairs({"comfortable","compact"}) do
        BigBiSListDB.profile.window.density=density
        ui.frame:SetSize(size[1],size[2]); H.settle()
        ui:ShowInspectorFor(reward.item_id,reward,"phase"); H.settle()
        local card=revealSourceCard(31096)
        assert(card,"real token source was not rendered through RefreshDetails")
        assert(card.originRows[1].rate:GetText()=="57.8%","reported token rate missing")
        H.expectBounded(card,ui.detailsContent,"real token card")
        H.expectHorizontalBounds(card,ui.detailsScroll,"real token horizontal bounds")
        card.identity:Click()
        assert(H.referenceLink=="item:31096" and ui.selectedItemId==31039)
    end
end
local starterReward={item_id=30007,slot="Neck",name="The Darkener's Grasp"}
ui:ShowInspectorFor(starterReward.item_id,starterReward,"phase"); H.settle()
local starter=revealSourceCard(32405)
assert(starter and starter.originRows[1].rate:GetText()=="91.5%","quest starter item/rate not rendered")
ui:ShowInspectorFor(reward.item_id,reward,"phase"); H.settle()
assert(ui:OpenSlotComparison(reward,"phase")); H.settle()
local comparison=ui.slotComparison
ui:ShowComparisonDetails(reward); H.settle()
local selectedKey,reference=ui.selectedRowKey,comparison.reference
local token=revealSourceCard(31096)
assert(token and ui.detailsBackButton.label:GetText()=="Back to comparison")
token.identity:Click()
assert(ui.slotComparison==comparison and comparison.detailsOpen and comparison.reference==reference)
assert(ui.selectedRowKey==selectedKey and ui.selectedItemId==31039,"native source click displaced comparison reward")
ui.detailsBackButton:Click(); H.settle()
assert(ui.comparisonFrame:IsVisible() and not comparison.detailsOpen,"prerequisite interaction broke Back to comparison")
''')

    def test_real_invalid_drop_rate_is_unknown_without_reformatting_data(self):
        self.run_lua(r'''
BigBiSList.GetAccessOptionSourceItems=actualSourceItems
option={source_identity="invalid-observation",source={type="quest",entity_name="Reward quest",quest_starter_sources={
    {type="drop",entity_name="Unknown boss",quest_starter_item_id=80001,drop_percent=-1,count=-1,out_of=10},
    {type="drop",entity_name="Known zero boss",quest_starter_item_id=80001,drop_percent=0},
}}}
context.filters={}
render()
local rates={}
for _,row in ipairs(block.cards[1].originRows) do rates[row.origin.entity_name]=row.rate:GetText() end
assert(rates["Unknown boss"]=="Unknown","negative sentinel appeared as a rate or blank")
assert(rates["Known zero boss"]=="0.0%","genuine zero was treated as unknown")
''')

    def test_native_ancestor_hide_and_main_window_reopen_preserve_cached_cards(self):
        self.run_lua(r'''
BigBiSList.GetAccessOptionSourceItems=actualSourceItems
ui.RefreshDetails=actualRefreshDetails
ui:Open(); H.settle(); ui:SetTab("By Slot"); ui:SetPhase("T6"); H.settle()
ui:ShowInspectorFor(31039,{item_id=31039,name="Thunderheart Cover",slot="Head"},"phase"); H.settle()
local card,source=revealSourceCard(31096)
assert(card and card.identity.itemId==31096 and card:IsVisible())
local signature=ui.detailsRenderSignature
ui:Close()
for _,frame in ipairs(H.frames) do
    if frame:IsShown() and not frame:IsVisible() and frame:GetScript("OnHide") then
        frame:GetScript("OnHide")(frame)
    end
end
assert(source:IsShown() and card:IsShown() and card.identity.itemId==31096,"ancestor hide invalidated cached prerequisite")
ui:Open(); H.settle()
assert(ui.detailsRenderSignature==signature,"ordinary reopen unexpectedly invalidated Details")
assert(source:IsVisible() and card:IsVisible() and card.identity.itemId==31096,"cached prerequisite vanished on reopen")
card.identity:Click(); assert(H.referenceLink=="item:31096" and ui.selectedItemId==31039)
ui:BeginDetailsRender()
assert(not source:IsShown() and not card.identity.itemId,"explicit pool release failed to clear source binding")
''')

    def test_comparison_access_ignores_origin_filters_and_does_not_reuse_workspace_cache(self):
        self.run_lua(r'''
BigBiSList.GetAccessOptionSourceItems=actualSourceItems
ui.RefreshDetails=actualRefreshDetails
ui:Open(); H.settle(); ui:SetTab("By Slot"); ui:SetPhase("T5"); H.settle()
local filters=ui:GetFilters(); filters.zones={Karazhan=true}; filters.sourceType="all"
local primary={source_type="drop",is_primary=true,source={type="drop",entity_name="Lady Vashj",zone="Serpentshrine Cavern"},requirements={},acquisition_phase="T5"}
local alternate={source_type="drop",source={type="drop",entity_name="Prince Malchezaar",zone="Karazhan"},requirements={},acquisition_phase="T4"}
local reward={item_id=990001,slot="Head"}
BigBiSList.GetRowAccessOptions=function() return {primary,alternate} end
ui.currentAccessEvaluationCache=nil
assert(ui:GetAccessEvaluation(reward).optionEvaluation.option==alternate,"workspace did not use its source context")
ui.slotComparison={class="Druid",spec="Balance",phase="T5"}
assert(next(ui:GetItemContextFilters())==nil)
assert(ui:GetAccessEvaluation(reward).optionEvaluation.option==primary,"comparison reused origin filters or cached workspace route")
ui.slotComparison=nil
assert(ui:GetAccessEvaluation(reward).optionEvaluation.option==alternate,"comparison route cache leaked back into workspace")
assert(ui:GetFilters()==filters and filters.zones.Karazhan,"comparison altered origin filters")
''')


if __name__ == "__main__":
    unittest.main()
