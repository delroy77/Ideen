local _, suite = ...
DelroysSuiteCore = suite
local addonName, moduleName = "DelroysSuite", "DelroysSuite_Integrations"
local db, frame, page, setup, check, hint, heading, integrationButton
local gesture, reloading

local function text(parent, font, value, x, y)
    local label = parent:CreateFontString(nil, "OVERLAY", font)
    label:SetPoint("TOPLEFT", x, y)
    label:SetText(value)
    return label
end

local function button(parent, value, width, click)
    local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    b:SetSize(width, 24)
    b:SetText(value)
    b:SetScript("OnClick", click)
    return b
end
suite.Button, suite.Label = button, text

local function number(value, fallback, lo, hi)
    if type(value) ~= "number" or value ~= value then return fallback end
    return math.max(lo, math.min(hi, value))
end

local function saveLayout()
    db.width, db.height = frame:GetSize()
    local x, y = frame:GetCenter()
    local px, py = UIParent:GetCenter()
    if x and y and px and py then db.x, db.y = x - px, y - py end
end

local function stop()
    if not gesture then return end
    gesture = nil
    frame:StopMovingOrSizing()
    frame:SetUserPlaced(false)
    saveLayout()
end

local function resizeBounds()
    local width, height = UIParent:GetSize()
    return math.min(350, width), math.min(260, height),
        math.min(1100, width), math.min(820, height)
end

local function restore()
    local minW, minH, maxW, maxH = resizeBounds()
    local w = number(db.width, math.min(470, maxW), minW, maxW)
    local h = number(db.height, math.min(330, maxH), minH, maxH)
    frame:SetResizeBounds(minW, minH, maxW, maxH)
    frame:SetSize(w, h)
    local maxX = math.max(0, (UIParent:GetWidth() - w) / 2)
    local maxY = math.max(0, (UIParent:GetHeight() - h) / 2)
    frame:ClearAllPoints()
    frame:SetPoint("CENTER", UIParent, "CENTER",
        number(db.x, 0, -maxX, maxX), number(db.y, 0, -maxY, maxY))
end

local function openIntegrations()
    if not db.integrations then
        heading:SetText("Integrationen sind deaktiviert. /dsuite setup")
        return
    end
    if not suite.OpenIntegrations then
        local ok, why = C_AddOns.LoadAddOn(moduleName)
        if not ok then
            heading:SetText("Modul nicht verfügbar: " .. tostring(why or "?"))
            return
        end
    end
    if not suite.OpenIntegrations then
        heading:SetText("Das Modul hat sich nicht registriert.")
        return
    end
    heading:SetText("")
    suite.OpenIntegrations(page)
end

local function buildWindow()
    frame = CreateFrame("Frame", "DelroysSuiteV1Window", UIParent)
    frame:Hide()
    frame:SetFrameStrata("DIALOG")
    frame:SetMovable(true)
    frame:SetResizable(true)
    frame:SetClampedToScreen(true)
    frame:SetScript("OnHide", stop)
    restore()
    UISpecialFrames[#UISpecialFrames + 1] = frame:GetName()

    local bg = frame:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    bg:SetColorTexture(.045, .055, .07, .98)
    local close = button(frame, "×", 30, function() frame:Hide() end)
    close:SetPoint("TOPRIGHT", -5, -5)

    local title = CreateFrame("Frame", nil, frame)
    title:SetPoint("TOPLEFT")
    title:SetPoint("TOPRIGHT", close, "TOPLEFT", -5, 5)
    title:SetHeight(34)
    title:EnableMouse(true)
    text(title, "GameFontNormalLarge", "Delroys Suite", 12, -8)
    title:SetScript("OnMouseDown", function(_, key)
        if key == "LeftButton" and not gesture then
            gesture = "move"
            frame:StartMoving()
        end
    end)
    title:SetScript("OnMouseUp", stop)

    local grip = CreateFrame("Frame", nil, frame)
    grip:SetSize(24, 24)
    grip:SetFrameLevel(frame:GetFrameLevel() + 8)
    grip:SetPoint("BOTTOMRIGHT", -2, 2)
    grip:EnableMouse(true)
    local art = grip:CreateTexture(nil, "ARTWORK")
    art:SetAllPoints()
    art:SetTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
    grip:SetScript("OnMouseDown", function(_, key)
        if key == "LeftButton" and not gesture then
            gesture = "size"
            frame:StartSizing("BOTTOMRIGHT")
        end
    end)
    grip:SetScript("OnMouseUp", stop)

    integrationButton = button(frame, "Integrationen", 118, openIntegrations)
    integrationButton:SetPoint("TOPLEFT", 12, -40)
    heading = text(frame, "GameFontHighlightSmall", "", 12, -74)
    heading:SetPoint("TOPRIGHT", -12, -74)
    heading:SetJustifyH("LEFT")
    page = CreateFrame("Frame", nil, frame)
    page:SetPoint("TOPLEFT", 12, -90)
    page:SetPoint("BOTTOMRIGHT", -12, 26)
end

local function showSetup()
    if reloading then return end
    if not frame then buildWindow() end
    frame:Show()
    page:Hide()
    heading:Hide()
    integrationButton:Hide()
    if setup then
        check:SetChecked(db.integrations ~= false and C_AddOns.DoesAddOnExist(moduleName))
        hint:SetText("")
        setup:Show()
        return
    end
    setup = CreateFrame("Frame", nil, frame)
    setup:SetPoint("TOPLEFT", 10, -38)
    setup:SetPoint("BOTTOMRIGHT", -10, 23)
    local title = text(setup, "GameFontNormal", "Ersteinrichtung", 2, 0)
    local explanation = text(setup, "GameFontHighlightSmall",
        "Wähle die Module dieser Version. Externe Add-ons bleiben optional.", 2, -24)
    explanation:SetPoint("TOPRIGHT", -2, -24)
    explanation:SetJustifyH("LEFT")
    check = CreateFrame("CheckButton", nil, setup, "UICheckButtonTemplate")
    check:SetPoint("TOPLEFT", 0, -53)
    local exists = C_AddOns.DoesAddOnExist(moduleName)
    check:SetChecked(exists and db.integrations ~= false)
    if not exists then check:Disable() end
    text(setup, "GameFontHighlight", "Integrationserkennung", 35, -63)
    hint = text(setup, "GameFontHighlightSmall", exists and "" or "Modul fehlt.", 2, -91)
    local confirm = button(setup, "Speichern und neu laden", 182, function(self)
        if reloading then return end
        if InCombatLockdown() then
            hint:SetText("Schließe die Einrichtung nach dem Kampf ab.")
            return
        end
        stop()
        saveLayout()
        db.integrations = check:GetChecked() == true
        db.setupComplete = true
        reloading = true
        self:Disable()
        hint:SetText("Gespeichert. Falls die UI offen bleibt, gib /reload ein.")
        pcall(C_UI.Reload)
    end)
    confirm:SetPoint("BOTTOMLEFT", 2, 2)
end

local function toggle()
    if not db or reloading then return end
    if not db.setupComplete then showSetup() return end
    if not frame then buildWindow() end
    frame:SetShown(not frame:IsShown())
end

local function createMinimapButton()
    if not Minimap then return end
    local coin = CreateFrame("Button", "DelroysSuiteV1Minimap", Minimap)
    coin:SetSize(26, 26)
    coin:SetPoint("BOTTOMLEFT", 10, 10)
    coin:SetFrameLevel(Minimap:GetFrameLevel() + 8)
    coin:SetNormalTexture("Interface\\Icons\\INV_Misc_Coin_01")
    coin:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    coin:SetScript("OnClick", toggle)
    coin:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:SetText("Delroys Suite")
        GameTooltip:Show()
    end)
    coin:SetScript("OnLeave", function() GameTooltip:Hide() end)
end

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("PLAYER_LOGOUT")
events:RegisterEvent("UI_SCALE_CHANGED")
events:SetScript("OnEvent", function(self, event, name)
    if event == "ADDON_LOADED" and name == addonName then
        DelroysSuiteDB = type(DelroysSuiteDB) == "table" and DelroysSuiteDB or {}
        db = DelroysSuiteDB
        self:UnregisterEvent("ADDON_LOADED")
    elseif event == "PLAYER_LOGIN" then
        createMinimapButton()
        if not db.setupComplete then showSetup() end
    elseif event == "PLAYER_LOGOUT" then
        stop()
    elseif event == "UI_SCALE_CHANGED" and frame and not gesture then
        restore()
    end
end)

SLASH_DELROYSSUITEVONE1 = "/dsuite"
SLASH_DELROYSSUITEVONE2 = "/delroysuite"
SlashCmdList.DELROYSSUITEVONE = function(input)
    local command = (input or ""):lower():match("^%s*(.-)%s*$")
    if not db then return end
    if command == "setup" then
        showSetup()
    elseif command == "center" then
        stop()
        db.x, db.y = 0, 0
        if frame then restore() end
    else
        toggle()
    end
end
