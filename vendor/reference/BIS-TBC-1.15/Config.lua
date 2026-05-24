local AceConfigDialog = LibStub("AceConfigDialog-3.0")

local db_defaults = {
    char = {
        class_index = 1,
        spec_index = 1,
        phase_index = 1,
        filter_specs = {},
        highlight_spec = {},
        minimap = { hide = false },
        custom_lists = {},
        -- Display options
        show_tooltip_bis = true,
        show_drop_rates = true,
        show_owned_marks = true,
        show_paperdoll = true,
        compact_tooltip = false,
        show_drop_alerts = true,
    }
}

local configTable = {
    type = "group",
    args = {
        display_header = {
            name = "Display",
            type = "header",
            order = 1,
        },
        show_tooltip_bis = {
            name = "Show BiS info in tooltips",
            desc = "Adds BiS ranking information to item tooltips when hovering items",
            type = "toggle",
            order = 2,
            width = "full",
            set = function(info, val) BISTBCAddon.db.char.show_tooltip_bis = val end,
            get = function(info) return BISTBCAddon.db.char.show_tooltip_bis end,
        },
        show_drop_rates = {
            name = "Show drop rates",
            desc = "Display drop rate percentages in the items list",
            type = "toggle",
            order = 3,
            width = "full",
            set = function(info, val) BISTBCAddon.db.char.show_drop_rates = val end,
            get = function(info) return BISTBCAddon.db.char.show_drop_rates end,
        },
        show_owned_marks = {
            name = "Show owned item markers",
            desc = "Mark items you have equipped (E) or in bags (B)",
            type = "toggle",
            order = 4,
            width = "full",
            set = function(info, val) BISTBCAddon.db.char.show_owned_marks = val end,
            get = function(info) return BISTBCAddon.db.char.show_owned_marks end,
        },
        show_paperdoll = {
            name = "Show slot filter panel",
            desc = "Display the paper doll slot filter on the left side of the Items tab",
            type = "toggle",
            order = 5,
            width = "full",
            set = function(info, val) BISTBCAddon.db.char.show_paperdoll = val end,
            get = function(info) return BISTBCAddon.db.char.show_paperdoll end,
        },
        show_drop_alerts = {
            name = "Show BiS drop alerts",
            desc = "Display a popup and chat message when a BiS item drops for your spec",
            type = "toggle",
            order = 6,
            width = "full",
            set = function(info, val) BISTBCAddon.db.char.show_drop_alerts = val end,
            get = function(info) return BISTBCAddon.db.char.show_drop_alerts end,
        },
        tooltip_header = {
            name = "Tooltip Filtering",
            type = "header",
            order = 10,
        },
        compact_tooltip = {
            name = "Compact tooltip mode",
            desc = "Hide class name headers and show only spec icons in tooltips",
            type = "toggle",
            order = 11,
            width = "full",
            set = function(info, val) BISTBCAddon.db.char.compact_tooltip = val end,
            get = function(info) return BISTBCAddon.db.char.compact_tooltip end,
        },
        filter_specs = {
            name = "Visible specs",
            desc = "Uncheck specs to hide them from item tooltips",
            type = "multiselect",
            order = 12,
            values = nil,
            set = function(info, key, val)
                local ci, si = strsplit(":", key)
                ci = tonumber(ci)
                si = tonumber(si)
                local class_name = BISTBC_classes[ci].name
                local spec_name = BISTBC_classes[ci].specs[si]
                BISTBCAddon.db.char.filter_specs[class_name][spec_name] = val
            end,
            get = function(info, key)
                local ci, si = strsplit(":", key)
                ci = tonumber(ci)
                si = tonumber(si)
                local class_name = BISTBC_classes[ci].name
                local spec_name = BISTBC_classes[ci].specs[si]
                if (not BISTBCAddon.db.char.filter_specs[class_name]) then
                    BISTBCAddon.db.char.filter_specs[class_name] = {}
                end
                if (BISTBCAddon.db.char.filter_specs[class_name][spec_name] == nil) then
                    BISTBCAddon.db.char.filter_specs[class_name][spec_name] = true
                end
                return BISTBCAddon.db.char.filter_specs[class_name][spec_name]
            end
        },
        highlight_spec = {
            name = "Highlight spec",
            desc = "Highlight a specific spec in green in item tooltips",
            type = "multiselect",
            order = 13,
            values = nil,
            set = function(info, key, val)
                if val then
                    local ci, si = strsplit(":", key)
                    ci = tonumber(ci)
                    si = tonumber(si)
                    local class_name = BISTBC_classes[ci].name
                    local spec_name = BISTBC_classes[ci].specs[si]
                    BISTBCAddon.db.char.highlight_spec = {
                        key = key,
                        class_name = class_name,
                        spec_name = spec_name
                    }
                else
                    BISTBCAddon.db.char.highlight_spec = {}
                end
            end,
            get = function(info, key)
                return BISTBCAddon.db.char.highlight_spec.key == key
            end
        },
    }
}

local function buildFilterSpecOptions()
    local filter_specs_options = {}
    for ci, class in ipairs(BISTBC_classes) do
        for si, spec in ipairs(BISTBC_classes[ci].specs) do
            local option_val = "|T" .. BISTBC_spec_icons[class.name][spec] .. ":16|t " .. class.name .. " " .. spec
            local option_key = ci .. ":" .. si
            filter_specs_options[option_key] = option_val
        end
    end
    configTable.args.filter_specs.values = filter_specs_options
    configTable.args.highlight_spec.values = filter_specs_options
end

function BISTBCAddon:openConfigDialog()
    if Settings and Settings.OpenToCategory then
        Settings.OpenToCategory(BISTBCAddon.AceAddonName)
    elseif InterfaceOptionsFrame_OpenToCategory then
        InterfaceOptionsFrame_OpenToCategory(BISTBCAddon.AceAddonName)
        InterfaceOptionsFrame_OpenToCategory(BISTBCAddon.AceAddonName)
    end
end

function BISTBCAddon:initConfig()
    BISTBCAddon.db = LibStub("AceDB-3.0"):New("BISTBCDB", db_defaults, true)

    buildFilterSpecOptions()
    LibStub("AceConfig-3.0"):RegisterOptionsTable(BISTBCAddon.AceAddonName, configTable)
    AceConfigDialog:AddToBlizOptions(BISTBCAddon.AceAddonName, BISTBCAddon.AceAddonName)
end
