local suite = DelroysSuiteCore
local targets = {
    { name = "AnoUI", names = {"AnoUI"}, command = "/anoui" },
    { name = "TSM", names = {"TradeSkillMaster"}, command = "/tsm" },
    { name = "Zygor", names = {"ZygorGuidesViewerForever", "ZygorGuidesViewerClassic", "ZygorGuidesViewer"}, command = "/zygor" },
    { name = "RestedXP", names = {"RXPGuides", "RestedXP"}, command = "/rxp" },
    { name = "RareScanner", names = {"RareScanner"}, command = "/rarescanner" },
    { name = "Questie", names = {"Questie"}, command = "/questie" },
}

local function handlerFor(command)
    local chosen
    for key, value in pairs(_G) do
        if type(value) == "string" and value:lower() == command and type(key) == "string" then
            local name = key:match("^SLASH_(.-)%d+$")
            local handler = name and SlashCmdList[name]
            if type(handler) == "function" then
                if chosen and chosen ~= handler then return nil end
                chosen = handler
            end
        end
    end
    return chosen
end

local function state(target)
    local installed
    for _, name in ipairs(target.names) do
        if C_AddOns.DoesAddOnExist(name) then
            installed = true
            local _, loaded = C_AddOns.IsAddOnLoaded(name)
            if loaded then return "Geladen", handlerFor(target.command) end
        end
    end
    return installed and "Installiert" or "Fehlt"
end

local rows, feedback = {}, nil
local function refresh()
    for index, target in ipairs(targets) do
        local label, handler = state(target)
        rows[index].label:SetText(target.name .. "  ·  " .. label)
        rows[index].action:SetShown(handler ~= nil)
    end
end

function suite.OpenIntegrations(parent)
    if not feedback then
        for index, target in ipairs(targets) do
            local y = -24 * (index - 1)
            local label = suite.Label(parent, "GameFontHighlightSmall", "", 0, y - 5)
            local action = suite.Button(parent, "Öffnen", 78, function()
                if InCombatLockdown() then
                    feedback:SetText("Nach dem Kampf erneut öffnen.")
                    return
                end
                local _, handler = state(target)
                if not handler or not pcall(handler, "", ChatFrame1EditBox) then
                    feedback:SetText("Der Einstieg ist nicht verfügbar.")
                else
                    parent:GetParent():Hide()
                end
            end)
            action:SetPoint("TOPRIGHT", -4, y)
            rows[index] = { label = label, action = action }
        end
        feedback = suite.Label(parent, "GameFontHighlightSmall", "", 0, -149)
    end
    feedback:SetText("")
    refresh()
end
