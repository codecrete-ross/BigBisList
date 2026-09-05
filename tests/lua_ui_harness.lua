-- A deterministic Lua 5.1 simulation of frame layout and native game APIs.
-- This exercises addon code; it does not render pixels or emulate the game client.
local H = { frames = {}, timers = {}, errors = {}, now = 0, epoch = 0, modifiers = {}, equipped = {}, itemNames = {}, coldItems = {} }
local methods = {}
local fractions = {
    TOPLEFT = { 0, 1 }, TOP = { .5, 1 }, TOPRIGHT = { 1, 1 },
    LEFT = { 0, .5 }, CENTER = { .5, .5 }, RIGHT = { 1, .5 },
    BOTTOMLEFT = { 0, 0 }, BOTTOM = { .5, 0 }, BOTTOMRIGHT = { 1, 0 },
}
local function changed() H.epoch = H.epoch + 1 end
local function plain(text)
    return (tostring(text or ""):gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""):gsub("|T.-|t", "XX"))
end
local function intrinsic(node)
    local longest, lines = 0, 0
    for line in (plain(node.text) .. "\n"):gmatch("(.-)\n") do
        longest = math.max(longest, #line * (node.fontSize or 12) * .51)
        lines = lines + 1
    end
    return longest, math.max(1, lines) * (node.fontSize or 12)
end
local function rect(node)
    if not node then return 0, 0, 0, 0 end
    if node.geometryEpoch == H.epoch then return unpack(node.geometry) end
    if node.resolving then return 0, 0, node.width or 0, node.height or 0 end
    node.resolving = true
    local px, py, pw, ph = 0, 0, 0, 0
    if node.parent then px, py, pw, ph = rect(node.parent) end
    local iw, ih = intrinsic(node)
    local width = node.width or (node.kind == "FontString" and iw) or 0
    local height = node.height or (node.kind == "FontString" and ih) or 0
    local constraints = { {}, {} }
    for _, point in ipairs(node.points) do
        local rx, ry, rw, rh = rect(point.relative)
        local own, relative = fractions[point.point], fractions[point.relativePoint]
        table.insert(constraints[1], { own[1], rx + rw * relative[1] + point.x })
        table.insert(constraints[2], { own[2], ry + rh * relative[2] + point.y })
    end
    local function solve(list, size, fallback, explicit)
        for _, first in ipairs(list) do
            for _, second in ipairs(list) do
                if first[1] ~= second[1] and (not explicit or math.abs(first[1] - second[1]) == 1) then
                    size = (second[2] - first[2]) / (second[1] - first[1])
                    return first[2] - first[1] * size, size
                end
            end
        end
        if list[1] then return list[1][2] - list[1][1] * size, size end
        return fallback, size
    end
    local x, y
    x, width = solve(constraints[1], width, px, node.width)
    y, height = solve(constraints[2], height, py, node.height)
    if #node.points == 0 and node.parent and node.parent.scrollChild == node then
        y = py + ph - height + (node.parent.verticalScroll or 0)
    end
    node.resolving = nil
    node.geometryEpoch, node.geometry = H.epoch, { x, y, width, height }
    return x, y, width, height
end
local function make(kind, name, parent)
    local node = setmetatable({ kind = kind, name = name, parent = parent, points = {}, scripts = {}, children = {}, regions = {}, shown = true, enabled = true }, { __index = methods })
    table.insert(H.frames, node)
    if parent then table.insert((kind == "FontString" or kind == "Texture") and parent.regions or parent.children, node) end
    if name then _G[name] = node end
    return node
end
function methods:GetName() return self.name end
function methods:GetParent() return self.parent end
function methods:SetParent(parent) self.parent = parent; changed() end
function methods:SetSize(width, height) self.width, self.height = width, height; changed() end
function methods:SetWidth(width) self.width = width; changed() end
function methods:SetHeight(height) self.height = height; changed() end
function methods:GetWidth() local _, _, width = rect(self); return width end
function methods:GetHeight() local _, _, _, height = rect(self); return height end
function methods:GetLeft() local x = rect(self); return x end
function methods:GetBottom() local _, y = rect(self); return y end
function methods:GetRight() return self:GetLeft() + self:GetWidth() end
function methods:GetTop() return self:GetBottom() + self:GetHeight() end
function methods:GetCenter() return self:GetLeft() + self:GetWidth() / 2, self:GetBottom() + self:GetHeight() / 2 end
function methods:ClearAllPoints() self.points = {}; changed() end
function methods:SetPoint(point, relative, relativePoint, x, y)
    if type(relative) == "number" then x, y, relative, relativePoint = relative, relativePoint, self.parent, point end
    relative = type(relative) == "string" and _G[relative] or relative or self.parent
    relativePoint = relativePoint or point
    local newPoint = { point = point, relative = relative, relativePoint = relativePoint, x = x or 0, y = y or 0 }
    for index, old in ipairs(self.points) do if old.point == point then self.points[index] = newPoint; changed(); return end end
    table.insert(self.points, newPoint); changed()
end
function methods:GetPoint(index) local p = self.points[index or 1]; if p then return p.point, p.relative, p.relativePoint, p.x, p.y end end
function methods:SetAllPoints(relative) self:ClearAllPoints(); self:SetPoint("TOPLEFT", relative or self.parent, "TOPLEFT"); self:SetPoint("BOTTOMRIGHT", relative or self.parent, "BOTTOMRIGHT") end
function methods:SetScript(event, callback) self.scripts[event] = callback end
function methods:GetScript(event) return self.scripts[event] end
function methods:HookScript(event, callback)
    local previous = self.scripts[event]
    self.scripts[event] = function(...) if previous then previous(...) end; callback(...) end
end
function methods:Show() local was = self.shown; self.shown = true; if not was and self.scripts.OnShow then self.scripts.OnShow(self) end end
function methods:Hide() local was = self.shown; self.shown = false; if was and self.scripts.OnHide then self.scripts.OnHide(self) end end
function methods:SetShown(shown) if shown then self:Show() else self:Hide() end end
function methods:IsShown() return self.shown end
function methods:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
function methods:CreateFontString(name) return make("FontString", name, self) end
function methods:CreateTexture(name) return make("Texture", name, self) end
function methods:GetChildren() return unpack(self.children) end
function methods:GetRegions() return unpack(self.regions) end
function methods:SetText(text)
    local different = self.text ~= tostring(text or "")
    self.text = tostring(text or ""); changed()
    if different and self.scripts.OnTextChanged then self.scripts.OnTextChanged(self, false) end
end
function methods:GetText() return self.text or "" end
function methods:GetStringWidth() return intrinsic(self) end
function methods:GetStringHeight()
    local width, height = intrinsic(self)
    if self.wordWrap ~= false and self:GetWidth() > 0 then height = math.max(height, math.ceil(width / self:GetWidth()) * (self.fontSize or 12)) end
    return height
end
function methods:SetFont(font, size, flags) self.font, self.fontSize, self.fontFlags = font, size, flags end
function methods:GetFont() return self.font or "Fonts\\FRIZQT__.TTF", self.fontSize or 12, self.fontFlags or "" end
function methods:SetWordWrap(wrap) self.wordWrap = wrap end
function methods:SetScale(scale) self.scale = scale end
function methods:GetScale() return self.scale or 1 end
function methods:GetEffectiveScale() return self:GetScale() * (self.parent and self.parent:GetEffectiveScale() or 1) end
function methods:SetFrameLevel(level) self.frameLevel = level end
function methods:GetFrameLevel() return self.frameLevel or (self.parent and self.parent:GetFrameLevel() + 1) or 0 end
function methods:SetFrameStrata(strata) self.strata = strata end
function methods:GetFrameStrata() return self.strata or "MEDIUM" end
function methods:Enable() self.enabled = true end
function methods:Disable() self.enabled = false end
function methods:SetEnabled(value) self.enabled = value end
function methods:IsEnabled() return self.enabled end
function methods:SetChecked(value) self.checked = value end
function methods:GetChecked() return self.checked end
function methods:SetValue(value) self.value = value; if self.scripts.OnValueChanged then self.scripts.OnValueChanged(self, value) end end
function methods:GetValue() return self.value or 0 end
function methods:SetMinMaxValues(minimum, maximum) self.minimum, self.maximum = minimum, maximum end
function methods:GetMinMaxValues() return self.minimum or 0, self.maximum or 1 end
function methods:SetScrollChild(child) self.scrollChild = child; changed() end
function methods:SetVerticalScroll(offset) self.verticalScroll = offset; changed(); if self.scripts.OnVerticalScroll then self.scripts.OnVerticalScroll(self, offset) end end
function methods:GetVerticalScroll() return self.verticalScroll or 0 end
function methods:GetVerticalScrollRange() return math.max(0, (self.scrollChild and self.scrollChild:GetHeight() or 0) - self:GetHeight()) end
function methods:HasFocus() return self.focused == true end
function methods:SetFocus() self.focused = true end
function methods:ClearFocus() self.focused = false end
function methods:Click(button) if self.scripts.OnClick then self.scripts.OnClick(self, button or "LeftButton") end end
function methods:SetTexture(texture) self.texture = texture end
function methods:GetTexture() return self.texture end
function methods:SetNormalTexture(texture) self.normalTexture = make("Texture", nil, self); self.normalTexture:SetTexture(texture) end
function methods:GetNormalTexture() return self.normalTexture end
function methods:SetHighlightTexture(texture) self.highlightTexture = make("Texture", nil, self); self.highlightTexture:SetTexture(texture) end
function methods:GetHighlightTexture() return self.highlightTexture end
function methods:SetPushedTexture(texture) self.pushedTexture = make("Texture", nil, self); self.pushedTexture:SetTexture(texture) end
function methods:GetPushedTexture() return self.pushedTexture end
function methods:SetClampedToScreen(value) self.clamped = value end
function methods:IsClampedToScreen() return self.clamped end
for _, name in ipairs({ "EnableMouse", "EnableMouseWheel", "RegisterForClicks", "RegisterEvent", "SetToplevel", "SetMovable", "SetResizable", "SetResizeBounds", "SetMinResize", "SetMaxResize", "RegisterForDrag", "StartMoving", "StartSizing", "StopMovingOrSizing", "SetBackdrop", "SetBackdropColor", "SetBackdropBorderColor", "SetTexCoord", "SetColorTexture", "SetVertexColor", "SetTextColor", "SetJustifyH", "SetJustifyV", "SetAlpha", "SetBlendMode", "SetDesaturated", "SetDrawLayer", "SetAutoFocus", "SetNumeric", "SetMaxLetters", "SetTextInsets", "SetMultiLine", "SetCursorPosition", "HighlightText", "SetValueStep", "SetObeyStepOnDrag", "SetOrientation", "SetThumbTexture", "SetHitRectInsets", "SetClipsChildren", "SetPropagateKeyboardInput", "EnableKeyboard", "SetFontObject", "SetDisabledFontObject", "SetNormalFontObject", "SetHighlightFontObject", "SetDisabledTexture", "SetButtonState", "SetAllPointsToParent", "SetMaxLines", "SetIndentedWordWrap" }) do
    methods[name] = function() end
end
CreateFrame = function(kind, name, parent, template)
    local node = make(kind, name, parent)
    if template and template:find("UIDropDownMenuTemplate", 1, true) then
        node:SetSize(160, 32)
        node.Button = make("Button", name and name .. "Button", node)
        node.Button:SetSize(24, 24)
        node.Button:SetPoint("RIGHT", node, "RIGHT")
        for _, suffix in ipairs({ "Left", "Middle", "Right", "Text" }) do make(suffix == "Text" and "FontString" or "Texture", name and name .. suffix, node) end
    elseif template and template:find("OptionsSliderTemplate", 1, true) then
        for _, suffix in ipairs({ "Text", "Low", "High" }) do node[suffix] = make("FontString", name and name .. suffix, node) end
    end
    return node
end
UIParent = make("Frame", "UIParent")
UIParent:SetSize(1920, 1080)
UISpecialFrames = {}
UIDROPDOWNMENU_MAXLEVELS = 2
UIDropDownMenu_SetWidth = function(frame, width) frame:SetWidth(width + 40) end
UIDropDownMenu_SetText = function(frame, text) frame.dropdownText = text end
UIDropDownMenu_Initialize = function(frame, callback) frame.initialize = callback end
UIDropDownMenu_CreateInfo = function() return {} end
UIDropDownMenu_AddButton = function() end
ToggleDropDownMenu = function(_, _, frame) if frame and frame.initialize then frame.initialize(frame, 1) end end
CloseDropDownMenus = function() end
hooksecurefunc = function() end
GetTime = function() return H.now end
GetServerTime = function() return 1788656400 end
time = function() return 1788656400 end
date = os.date
debugprofilestop = function() return H.now * 1000 end
C_Timer = { After = function(delay, callback) table.insert(H.timers, { at = H.now + delay, callback = callback }) end }
geterrorhandler = function() return function(err) table.insert(H.errors, tostring(err)) end end
UnitClass = function() return "Druid", "DRUID" end
UnitClassBase = function() return "DRUID" end
UnitName = function() return "Fixture" end
UnitLevel = function() return 70 end
UnitRace = function() return "Night Elf", "NightElf" end
UnitFactionGroup = function() return "Alliance" end
GetRealmName = function() return "Simulation" end
GetNumTalentTabs = function() return 0 end
GetNumFactions = function() return 0 end
GetNumSkillLines = function() return 0 end
GetContainerNumSlots = function() return 0 end
GetInventoryItemID = function(_, slot) return H.equipped[slot] end
GetInventoryItemLink = function(_, slot) return H.equipped[slot] and ("item:" .. H.equipped[slot]) end
GetItemInfo = function(id)
    id = tonumber(id) or tonumber(tostring(id):match("item:(%d+)"))
    if not id or H.coldItems[id] then return nil end
    local data = BigBiSList and BigBiSList.dataIndex and BigBiSList.dataIndex.itemsById[id]
    return H.itemNames[id] or (data and data.name) or ("Fixture item " .. id), "item:" .. id, 4, 100, 70, "Armor", "Leather", 1, "INVTYPE_HEAD", "Interface\\Icons\\INV_Misc_QuestionMark", 0
end
GetItemInfoInstant = function(id) return id, "Armor", "Leather", "INVTYPE_HEAD" end
GetItemQualityColor = function() return .64, .21, .93 end
GetSpellInfo = function(id) return "Fixture spell " .. tostring(id), nil, "Interface\\Icons\\INV_Misc_QuestionMark" end
GetSpellLink = function(id) return "spell:" .. tostring(id) end
GetScreenWidth = function() return UIParent:GetWidth() end
GetScreenHeight = function() return UIParent:GetHeight() end
IsShiftKeyDown = function() return H.modifiers.shift == true end
IsControlKeyDown = function() return H.modifiers.control == true end
IsAltKeyDown = function() return H.modifiers.alt == true end
ChatEdit_InsertLink = function(link) H.chatLink = link end
DressUpItemLink = function(link) H.previewLink = link end
SetItemRef = function(link) H.referenceLink = link end
DEFAULT_CHAT_FRAME = { AddMessage = function() end }
GameTooltip = make("GameTooltip", "GameTooltip")
ItemRefTooltip = make("GameTooltip", "ItemRefTooltip")
function methods:SetOwner(owner) self.owner = owner; self.lines = {}; if self.scripts.OnTooltipCleared then self.scripts.OnTooltipCleared(self) end end
function methods:GetOwner() return self.owner end
function methods:IsOwned(owner) return self.owner == owner end
function methods:AddLine(text) self.lines = self.lines or {}; table.insert(self.lines, text) end
function methods:AddDoubleLine(left, right) self:AddLine(left .. " " .. right) end
function methods:SetHyperlink(link)
    self.hyperlink = link; self.lines = { "Native: " .. link }
    if self.scripts.OnTooltipCleared then self.scripts.OnTooltipCleared(self) end
    if link:find("item:", 1, true) and self.scripts.OnTooltipSetItem then self.scripts.OnTooltipSetItem(self) end
end
function methods:SetItemByID(id) self:SetHyperlink("item:" .. tostring(id)) end
function methods:SetSpellByID(id) self:SetHyperlink("spell:" .. tostring(id)) end
function methods:GetItem() return "Fixture", self.hyperlink end
function methods:NumLines() return #(self.lines or {}) end
function H.settle()
    for pass = 1, 30 do
        local activity = false
        for _, node in ipairs(H.frames) do
            local width, height = node:GetWidth(), node:GetHeight()
            if node.lastWidth ~= width or node.lastHeight ~= height then
                node.lastWidth, node.lastHeight = width, height
                if node.scripts.OnSizeChanged then node.scripts.OnSizeChanged(node, width, height); activity = true end
            end
        end
        local pending = H.timers
        H.timers = {}
        for _, timer in ipairs(pending) do
            if timer.at <= H.now then timer.callback(); activity = true else table.insert(H.timers, timer) end
        end
        if not activity then return end
    end
    error("UI geometry or refresh timers did not settle after 30 passes")
end
function H.load()
    for _, file in ipairs({ "Data.lua", "Config.lua", "DataIndex.lua", "Widgets.lua", "UI.lua", "Tooltip.lua" }) do assert(loadfile(file))("BigBiSList") end
    BigBiSList:EnsureDatabase()
    BigBiSList:InitTooltip()
    return BigBiSList.UI
end
function H.rect(frame) return rect(frame) end
function H.expectBounded(frame, parent, label)
    local x, y, width, height = rect(frame)
    local px, py, pw, ph = rect(parent)
    assert(width >= -0.1 and height >= -0.1, label .. " has negative geometry")
    assert(x >= px - 1 and x + width <= px + pw + 1, label .. " exceeds horizontal bounds: " .. x .. "," .. width .. " vs " .. px .. "," .. pw)
    assert(y >= py - 1 and y + height <= py + ph + 1, label .. " exceeds vertical bounds")
end
function H.expectHorizontalBounds(frame, parent, label)
    local x, _, width = rect(frame)
    local px, _, pw = rect(parent)
    assert(x >= px - 1 and x + width <= px + pw + 1, label .. " exceeds horizontal bounds")
end
function H.expectRowsBounded(ui, label)
    for _, row in ipairs(ui.activeRenderFrames or {}) do
        H.expectBounded(row, ui.contentListLayer, label .. " realized row")
        if row.boundData then
            for _, name in ipairs({ "iconButton", "nameText", "subText", "rankText", "findButton", "actionButton" }) do
                if row[name] and row[name]:IsVisible() then H.expectBounded(row[name], row, label .. " " .. name) end
            end
            for name, cell in pairs(row.cells or {}) do
                if cell:IsVisible() then H.expectBounded(cell, row, label .. " " .. name .. " cell") end
            end
        end
    end
end
return H
