import ast
import importlib.util
import re
import shutil
import struct
import subprocess
import sys
import unittest

from tools.project import ADDON_DIR


WIDGET_HARNESS = r'''
local function expect(value, message)
    if not value then error(message or "expectation failed", 2) end
end
local function equal(actual, expected, message)
    if actual ~= expected then
        error((message or "different values") .. ": " .. tostring(actual) .. " ~= " .. tostring(expected), 2)
    end
end
local function region()
    local self = { shown = true, width = 100, height = 0, points = {}, text = "" }
    function self:SetPoint(...) self.points[#self.points + 1] = {...} end
    function self:SetAllPoints(...) self.allPoints = {...} end
    function self:ClearAllPoints() self.points = {} end
    function self:SetWidth(value) self.width = value end
    function self:GetWidth() return self.width end
    function self:SetHeight(value) self.height = value end
    function self:GetHeight() return self.height end
    function self:SetSize(width, height) self.width, self.height = width, height end
    function self:SetTexture(value) self.texture = value end
    function self:SetTexCoord(...) self.coords = {...} end
    function self:SetColorTexture(...) self.color = {...} end
    function self:SetVertexColor(...) self.color = {...} end
    function self:SetTextColor(...) self.color = {...} end
    function self:SetBlendMode(value) self.blend = value end
    function self:SetText(value) self.text = value end
    function self:GetText() return self.text end
    function self:SetWordWrap(value) self.wrap = value end
    function self:SetNonSpaceWrap(value) self.nonSpaceWrap = value end
    function self:SetJustifyH(value) self.justify = value end
    function self:SetJustifyV(value) self.justifyV = value end
    function self:Show() self.shown = true end
    function self:Hide() self.shown = false end
    function self:IsShown() return self.shown end
    function self:GetStringHeight()
        local text = string.gsub(self.text, "|c%x%x%x%x%x%x%x%x", "")
        text = string.gsub(text, "|r", "")
        -- Count UTF-8 code points, rather than bytes, in the deterministic font stub.
        text = string.gsub(text, "[\128-\191]", "")
        local capacity, lines = math.max(1, math.floor(self.width / 6)), 0
        for line in string.gmatch(text .. "\n", "(.-)\n") do
            lines = lines + math.max(1, math.ceil(#line / capacity))
        end
        return lines * 12
    end
    return self
end
function CreateFrame(kind, name, parent)
    local self = region()
    self.kind, self.name, self.parent = kind, name, parent
    self.scripts, self.hooks, self.enabled = {}, {}, true
    function self:SetScript(event, callback) self.scripts[event] = callback end
    function self:GetScript(event) return self.scripts[event] end
    function self:HookScript(event, callback)
        self.hooks[event] = self.hooks[event] or {}
        table.insert(self.hooks[event], callback)
    end
    function self:Fire(event, ...)
        if self.scripts[event] then self.scripts[event](self, ...) end
        for _, callback in ipairs(self.hooks[event] or {}) do callback(self, ...) end
    end
    function self:SetEnabled(value)
        self.enabled = value
        self:Fire(value and "OnEnable" or "OnDisable")
    end
    function self:IsEnabled() return self.enabled end
    function self:EnableMouse(value) self.mouseEnabled = value end
    function self:RegisterForClicks(...) self.clicks = {...} end
    function self:SetBackdrop(value) self.backdrop = value end
    function self:SetBackdropColor(...) self.background = {...} end
    function self:SetBackdropBorderColor(...) self.borderColor = {...} end
    function self:CreateFontString() return region() end
    function self:CreateTexture() return region() end
    return self
end
GameTooltip = { lines = {}, shown = false }
function GameTooltip:SetOwner(owner) self.owner, self.lines = owner, {} end
function GameTooltip:IsOwned(owner) return self.owner == owner end
function GameTooltip:AddLine(text) table.insert(self.lines, text) end
function GameTooltip:Show() self.shown = true end
function GameTooltip:Hide() self.shown = false end
BigBiSList = {}
dofile("Widgets.lua")
local Widgets = BigBiSList.Widgets
'''


class WidgetRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = shutil.which("lua5.1") or shutil.which("lua")
        if cls.lua:
            version = subprocess.run([cls.lua, "-e", "io.write(_VERSION)"], capture_output=True, text=True)
            if version.returncode != 0 or version.stdout != "Lua 5.1":
                cls.lua = None

    def run_lua(self, body):
        if not self.lua:
            self.skipTest("Lua 5.1 is not available")
        result = subprocess.run([self.lua, "-"], input=WIDGET_HARNESS + body,
                                cwd=ADDON_DIR, capture_output=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_utility_icons_have_accessible_targets_and_preserve_toggle_state(self):
        self.run_lua(r'''
local button = Widgets:CreateUtilityButton(nil, "starOutline", 20, nil, "Add to Wishlist")
equal(button.kind, "Button", "utility control is a native button")
equal(button.width, 28, "minimum target width")
equal(button.height, 28, "minimum target height")
equal(button.icon.iconKey, "starOutline", "initial semantic icon")
local initialLeft = button.icon.coords[1]
button:SetSelected(true)
button:SetIcon("starFilled")
expect(button.icon.coords[1] ~= initialLeft, "filled state selects another atlas cell")
button:Fire("OnEnter")
expect(button.hovered and button.selected, "hover retains selection")
equal(button.borderColor[1], Widgets.Theme.accent[1], "selected border remains accented on hover")
button:Fire("OnLeave")
expect(button.selected and not button.hovered, "leaving preserves saved state")
equal(button.icon.color[1], Widgets.Theme.accent[1], "saved star remains visibly selected")
Widgets:SetIcon(button.icon, "missing-icon")
equal(button.icon.iconKey, "info", "unknown utility icon has a valid fallback")
''')

    def test_buttons_dispatch_once_and_handle_pressed_disabled_and_focus_states(self):
        self.run_lua(r'''
local clicks = 0
local button = Widgets:CreateTextButton(nil, "Action", 80, 28, function() clicks = clicks + 1 end)
button:Fire("OnMouseDown", "LeftButton")
expect(button.pressed, "mouse down paints pressed state")
button:Fire("OnMouseUp", "LeftButton")
expect(not button.pressed, "mouse up releases pressed state")
equal(clicks, 0, "mouse up does not duplicate native click dispatch")
button:Fire("OnClick", "LeftButton")
button:Fire("OnClick", "RightButton")
equal(clicks, 1, "left-click fires exactly once")
button:SetFocused(true)
expect(button.focusRing.shown, "keyboard focus has a separate visible marker")
button:SetEnabled(false)
button:Fire("OnMouseDown", "LeftButton")
button:Fire("OnClick", "LeftButton")
equal(clicks, 1, "disabled actions cannot run")
expect(not button.pressed and not button.focusRing.shown, "disabled control cannot look pressed or focused")
button:SetEnabled(true)
button:Fire("OnClick", "LeftButton")
equal(clicks, 2, "reenabling restores action")
button:Fire("OnHide")
expect(not button.hovered and not button.pressed and not button.focused, "hiding clears transient input states")
''')

    def test_tooltip_rebinding_composes_with_item_hover_without_duplicate_callbacks(self):
        self.run_lua(r'''
local button = Widgets:CreateIconButton(nil, 30)
button:Fire("OnSizeChanged", 24, 24)
equal(button.border.width, 24 * 1.8, "density changes resize the item hover glow")
local oldCalls, newCalls = 0, 0
Widgets:BindTooltip(button, function() oldCalls = oldCalls + 1 end)
Widgets:BindTooltip(button, function(self, tooltip)
    expect(self == button and tooltip == GameTooltip, "callback receives the bound control and tooltip")
    newCalls = newCalls + 1
    tooltip:AddLine("Current item")
end)
button:Fire("OnEnter")
equal(oldCalls, 0, "recycled tooltip discards old callback")
equal(newCalls, 1, "rebinding does not install additional hooks")
expect(button.border.shown and GameTooltip.shown, "item glow and tooltip appear together")
equal(GameTooltip.lines[1], "Current item", "tooltip shows current binding")
button:Fire("OnLeave")
expect(not button.border.shown and not GameTooltip.shown, "leave clears both affordances")
button:Fire("OnEnter")
GameTooltip:SetOwner({})
GameTooltip:Show()
button:Fire("OnHide")
expect(GameTooltip.shown, "hiding an old owner does not hide another control's tooltip")
Widgets:BindTooltip(button, nil)
button:Fire("OnEnter")
equal(newCalls, 2, "clearing the binding disables its tooltip callback")
''')

    def test_row_selection_survives_hover_and_resets_for_pool_reuse(self):
        self.run_lua(r'''
local row = Widgets:CreateItemRow(nil, 64)
equal(row.borderColor[4], 0, "rows form a continuous table surface")
expect(row.separator.shown, "subtle separator remains visible")
row:SetSelected(true)
row:Fire("OnEnter")
expect(row.selection.shown and row.selectionAccent.shown and row.highlight.shown, "selection and hover coexist")
row:Fire("OnLeave")
expect(row.selection.shown and not row.highlight.shown, "selection remains after the pointer leaves")
row:Fire("OnHide")
expect(not row.selected and not row.hovered and not row.selectionAccent.shown, "pooled row cannot retain stale interaction state")
''')

    def test_cell_text_is_bounded_and_full_content_survives_resize(self):
        self.run_lua(r'''
local label = region()
local text = "A long item source with a boss, a location and additional requirements"
local displayed, truncated = Widgets:SetCellText(label, text, 2, 14, 90)
expect(truncated and string.sub(displayed, -3) == "...", "overflow has a visible continuation")
equal(label.fullText, text, "full source remains available to tooltips and Details")
equal(label.height, 28, "cell cannot exceed its two-line allocation")
equal(label.justifyV, "MIDDLE", "bounded content is vertically centered")
expect(label:GetStringHeight() <= label.height, "displayed text fits inside the allocation")
Widgets:SetCellText(label, text, 2, 14, 600)
expect(not label.isTruncated, "wider layout recomputes truncation")
equal(label:GetText(), text, "resizing restores full text from caller input")
''')

    def test_opt_in_overflow_hides_bars_clamps_scroll_and_preserves_width(self):
        self.run_lua(r'''
local child = { width = 270, height = 420 }
function child:GetHeight() return self.height end
function child:SetWidth() error("overflow state must not change child width") end
local scroll = { child = child, height = 240, offset = 300, writes = 0 }
function scroll:GetHeight() return self.height end
function scroll:GetVerticalScroll() return self.offset end
function scroll:SetVerticalScroll(value) self.offset = value; self.writes = self.writes + 1 end
function scroll:SetWidth() error("overflow state must not change viewport width") end
local bar = { shown = true, enabled = true, value = 300, up = {}, down = {} }
function bar:SetMinMaxValues(low, high) self.minimum, self.maximum = low, high end
function bar:GetValue() return self.value end
function bar:SetValue(value) self.value = value end
function bar:SetEnabled(value) self.enabled = value end
function bar:Show() self.shown = true end
function bar:Hide() self.shown = false end
function bar.up:SetEnabled(value) self.enabled = value end
function bar.down:SetEnabled(value) self.enabled = value end
bar.ScrollUpButton, bar.ScrollDownButton = bar.up, bar.down
scroll.ScrollBar = bar
local overflow, maximum = Widgets:UpdateScrollOverflow(scroll)
expect(overflow and bar.shown and bar.enabled, "overflow retains enabled native scrollbar")
equal(maximum, 180, "overflow equals exact content minus viewport")
equal(scroll.offset, 180, "offset clamps after content shrinks")
equal(bar.value, 180, "thumb follows clamped offset")
expect(bar.up.enabled and not bar.down.enabled, "arrows respect bottom boundary")
local writes = scroll.writes
Widgets:UpdateScrollOverflow(scroll)
equal(scroll.writes, writes, "repeated refresh does not rewrite offset")
child.height = 240
overflow, maximum = Widgets:UpdateScrollOverflow(scroll)
expect(not overflow and not bar.shown and not bar.enabled, "exact fit hides and disables scrollbar")
equal(scroll.offset, 0, "no-overflow state resets stale offset")
equal(bar.value, 0, "no-overflow state resets stale thumb")
expect(not bar.up.enabled and not bar.down.enabled, "no-overflow arrows are disabled")
equal(child.width, 270, "scrollbar changes preserve content width")
Widgets:UpdateScrollOverflow(scroll, 480, 240)
expect(bar.shown and bar.enabled and not bar.up.enabled and bar.down.enabled, "new overflow restores native controls")
''')

    def test_overflow_supports_classic_named_bars_and_missing_optional_apis(self):
        self.run_lua(r'''
local scroll = { offset = -15 }
function scroll:GetName() return "BigBiSFilterScroll" end
function scroll:GetVerticalScroll() return self.offset end
function scroll:SetVerticalScroll(value) self.offset = value end
BigBiSFilterScrollScrollBar = { enabled = true, shown = true }
function BigBiSFilterScrollScrollBar:GetName() return "BigBiSFilterScrollScrollBar" end
function BigBiSFilterScrollScrollBar:Enable() self.enabled = true end
function BigBiSFilterScrollScrollBar:Disable() self.enabled = false end
function BigBiSFilterScrollScrollBar:Show() self.shown = true end
function BigBiSFilterScrollScrollBar:Hide() self.shown = false end
BigBiSFilterScrollScrollBarScrollUpButton = { Disable = function(self) self.disabled = true end }
BigBiSFilterScrollScrollBarScrollDownButton = { Enable = function(self) self.enabled = true end }
local overflow, maximum = Widgets:UpdateScrollOverflow(scroll, 360, 240)
expect(overflow and maximum == 120, "explicit geometry works without child/height APIs")
equal(scroll.offset, 0, "negative offset clamps to top")
expect(BigBiSFilterScrollScrollBarScrollUpButton.disabled, "classic named up arrow is found")
expect(BigBiSFilterScrollScrollBarScrollDownButton.enabled, "classic named down arrow is found")
Widgets:UpdateScrollOverflow(scroll, 100, 240)
expect(not BigBiSFilterScrollScrollBar.shown and not BigBiSFilterScrollScrollBar.enabled, "classic bar hides without modern SetEnabled")
local plainScroll = { GetVerticalScroll = function() return 0 end }
overflow, maximum = Widgets:UpdateScrollOverflow(plainScroll, 100, 40)
expect(overflow and maximum == 60, "missing optional bar APIs do not prevent layout")
overflow, maximum = Widgets:UpdateScrollOverflow(nil)
expect(not overflow and maximum == 0, "uncreated drawers are harmless")
''')

    def test_cell_truncation_does_not_split_utf8_or_color_sequences(self):
        self.run_lua(r'''
local label = region()
local text = "|cffa335eeÉpaulières enchantées de très longue réputation|r"
Widgets:SetCellText(label, text, 1, 14, 96)
expect(label.isTruncated, "fixture requires truncation")
expect(string.sub(label.displayedText, 1, 10) == "|cffa335ee", "color prefix is intact")
expect(string.sub(label.displayedText, -5) == "...|r", "truncated color is closed")
local position = 1
while position <= #label.displayedText do
    local byte = string.byte(label.displayedText, position)
    local length = byte >= 240 and 4 or (byte >= 224 and 3 or (byte >= 192 and 2 or 1))
    expect(byte < 128 or byte >= 192, "UTF-8 starts on a codepoint boundary")
    for offset = 1, length - 1 do
        local continuation = string.byte(label.displayedText, position + offset)
        expect(continuation and continuation >= 128 and continuation < 192, "UTF-8 continuation is intact")
    end
    position = position + length
end
equal(label.fullText, text, "formatted source is preserved")
''')


class UtilityAtlasTests(unittest.TestCase):
    def test_atlas_is_tbc_compatible_and_every_semantic_cell_has_padded_artwork(self):
        source = (ADDON_DIR / "tools" / "generate_ui_icons.py").read_text(encoding="utf-8")
        assignment = next(node for node in ast.parse(source).body
                          if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "ICON_KEYS"
                                  for target in node.targets))
        keys = ast.literal_eval(assignment.value)
        lua = (ADDON_DIR / "Widgets.lua").read_text(encoding="utf-8")
        lua_keys = re.findall(r'"([A-Za-z]+)"', re.search(r"local ICON_KEYS = \{(.*?)\}", lua, re.S).group(1))
        self.assertEqual(list(keys), lua_keys, "Lua texture coordinates must match the generated atlas")
        data = (ADDON_DIR / "assets" / "ui-icons.tga").read_bytes()
        header = struct.unpack("<BBBHHBHHHHBB", data[:18])
        self.assertEqual(header[2], 2, "TGA uses uncompressed true-color pixels")
        self.assertEqual(header[8:12], (256, 256, 32, 0x28))
        self.assertEqual(len(data), 18 + 256 * 256 * 4)
        for index, key in enumerate(keys):
            x0, y0 = index % 8 * 32, index // 8 * 32
            pixels = [(x, y) for y in range(32) for x in range(32)
                      if data[18 + ((y0 + y) * 256 + x0 + x) * 4 + 3]]
            self.assertTrue(pixels, f"{key} must not render as a blank icon")
            self.assertTrue(all(0 < x < 31 and 0 < y < 31 for x, y in pixels),
                            f"{key} needs transparent padding to prevent atlas bleeding")

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is needed to regenerate original UI icons")
    def test_committed_atlas_matches_deterministic_generator(self):
        result = subprocess.run([sys.executable, "tools/generate_ui_icons.py", "--check"],
                                cwd=ADDON_DIR, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
