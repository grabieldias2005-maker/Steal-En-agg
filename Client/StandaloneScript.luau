--[[
    ===================================================================
    STEAL AN EGG TRACKER & HUNTER - ESPECIALIZADO EN AreaEggSlotsClient
    ===================================================================
    - Motor reactivo especializado en Workspace.AreaEggSlotsClient.
    - Detecta huevos que se mantienen, rotan y actualizan por tiempo en cada slot.
    - Auto-Actualización de ESP en vivo cuando el huevo de un slot cambia o mejora.
    - Parser numérico inteligente: Soporta formatos del juego ("633.000 M", "15.200 M", "1.080 B", K/M/B/T).
    - Auto-TP Opcional: Teletransporte automático al detectar huevos Legendarios, Míticos o Secretos.
    - Teleport Manual: Botón de TP instantáneo a cada slot o al huevo más valioso del servidor.
    - Server Hopping: Telemetría al backend y cambio rápido a servidores con mejores huevos.
    - 100% compatible con loadstring(game:HttpGet(...))()
    ===================================================================
]]

-- ========================================================
-- 0. CONTROL DE INSTANCIAS (ANTI-DUPLICADOS & CLEANUP)
-- ========================================================
local getgenv = getgenv or function() return _G end
local genv = getgenv()

if genv._STEAL_AN_EGG_TRACKER_UNLOAD then
    pcall(genv._STEAL_AN_EGG_TRACKER_UNLOAD)
end

local cleanupCallbacks = {}
local function registerCleanup(fn)
    table.insert(cleanupCallbacks, fn)
end

genv._STEAL_AN_EGG_TRACKER_LOADED = true
genv._STEAL_AN_EGG_TRACKER_UNLOAD = function()
    for _, fn in ipairs(cleanupCallbacks) do
        pcall(fn)
    end
    table.clear(cleanupCallbacks)
    genv._STEAL_AN_EGG_TRACKER_LOADED = false
    print("[Tracker] Script previo descargado limpiamente.")
end

-- ========================================================
-- 1. CONFIGURACIÓN Y DEPENDENCIAS
-- ========================================================
local HttpService = game:GetService("HttpService")
local TeleportService = game:GetService("TeleportService")
local Workspace = game:GetService("Workspace")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

local userConfig = genv.EggTrackerConfig or _G.EggTrackerConfig or {}

local CONFIG = {
    BACKEND_URL = userConfig.BACKEND_URL or "http://localhost:3000",
    ENDPOINTS = {
        REPORT = (userConfig.ENDPOINTS and userConfig.ENDPOINTS.REPORT) or "/api/eggs/report",
        SEARCH = (userConfig.ENDPOINTS and userConfig.ENDPOINTS.SEARCH) or "/api/eggs/search"
    },
    REPORT_COOLDOWN = userConfig.REPORT_COOLDOWN or 3,
    MIN_REPORT_RARITY = userConfig.MIN_REPORT_RARITY or "Rare",
    PRIMARY_CONTAINER = "AreaEggSlotsClient",
    SECONDARY_FOLDERS = {"Eggs", "PlacedEggRenders", "HalloweenEggHolders", "Stands", "Plots"},
    RARITIES = {
        ["Common"]    = { Threshold = 0,         Rank = 1, Color = Color3.fromRGB(180, 180, 180) },
        ["Uncommon"]  = { Threshold = 100,       Rank = 2, Color = Color3.fromRGB(100, 255, 100) },
        ["Rare"]      = { Threshold = 500,       Rank = 3, Color = Color3.fromRGB(80, 160, 255) },
        ["Epic"]      = { Threshold = 2000,      Rank = 4, Color = Color3.fromRGB(180, 80, 255) },
        ["Legendary"] = { Threshold = 10000,     Rank = 5, Color = Color3.fromRGB(255, 170, 0) },
        ["Mythic"]    = { Threshold = 50000,     Rank = 6, Color = Color3.fromRGB(255, 60, 80) },
        ["Secret"]    = { Threshold = 250000,    Rank = 7, Color = Color3.fromRGB(0, 255, 230) }
    },
    PROPERTY_ALIASES = userConfig.PROPERTY_ALIASES or {
        Rarity = {"Rarity", "EggRarity", "Tier", "EggTier", "RarityTag"},
        Value  = {"Value", "EggValue", "Price", "Multiplier", "Points", "Cost", "Money"},
        Name   = {"EggName", "ItemName", "Title", "Name"},
        Timer  = {"TimeLeft", "Timer", "Time", "Cooldown", "Respawn", "SecondsLeft"}
    }
}

-- ========================================================
-- 2. PARSER NUMÉRICO INTELIGENTE (K, M, B, T, ETC.)
-- ========================================================
local function parseFormattedNumber(val)
    if type(val) == "number" then return val end
    if type(val) ~= "string" then return 0 end

    local str = val:gsub("[$%s]", "")
    if str == "" then return 0 end

    local multiplier = 1
    local upper = string.upper(str)

    if upper:find("QI") then multiplier = 1e18; str = upper:gsub("QI", "")
    elseif upper:find("QA") then multiplier = 1e15; str = upper:gsub("QA", "")
    elseif upper:find("T") then multiplier = 1e12; str = upper:gsub("T", "")
    elseif upper:find("B") then multiplier = 1e9; str = upper:gsub("B", "")
    elseif upper:find("M") then multiplier = 1e6; str = upper:gsub("M", "")
    elseif upper:find("K") then multiplier = 1e3; str = upper:gsub("K", "")
    end

    str = str:gsub(",", ".")
    local num = tonumber(str)
    if num then
        return num * multiplier
    end
    return 0
end

local function formatNumber(val)
    if not val or val == 0 then return "0" end
    if val >= 1e12 then return string.format("%.2fT", val / 1e12) end
    if val >= 1e9 then return string.format("%.2fB", val / 1e9) end
    if val >= 1e6 then return string.format("%.2fM", val / 1e6) end
    if val >= 1e3 then return string.format("%.1fK", val / 1e3) end
    return tostring(math.floor(val))
end

-- ========================================================
-- 3. COMUNICACIÓN HTTP
-- ========================================================
local function getRequestFunc()
    local env = (getfenv and getfenv()) or {}
    local req = genv.request 
        or genv.http_request 
        or (genv.syn and genv.syn.request) 
        or (genv.fluxus and genv.fluxus.request)
        or (genv.http and genv.http.request)
        or env.request 
        or env.http_request 
        or (env.syn and env.syn.request) 
        or (env.fluxus and env.fluxus.request)
        or (typeof(request) == "function" and request)
        or (typeof(http_request) == "function" and http_request)

    if req then
        return function(opts)
            return req({
                Url = opts.Url,
                Method = opts.Method or "GET",
                Headers = opts.Headers or {},
                Body = opts.Body
            })
        end
    end

    return function(opts)
        local res = HttpService:RequestAsync({
            Url = opts.Url,
            Method = opts.Method or "GET",
            Headers = opts.Headers or {},
            Body = opts.Body
        })
        return { StatusCode = res.StatusCode, Body = res.Body }
    end
end

local doRequest = getRequestFunc()

local function sendHttpRequest(url, method, body)
    local headers = { ["Content-Type"] = "application/json" }
    local encoded = body and (type(body) == "string" and body or HttpService:JSONEncode(body)) or nil
    local success, res = pcall(function()
        return doRequest({ Url = url, Method = method, Headers = headers, Body = encoded })
    end)
    if not success then return false, tostring(res) end
    local code = res.StatusCode or res.status or 0
    if code >= 200 and code < 300 then
        local rawBody = res.Body or res.body
        local okJson, decoded = pcall(function() return HttpService:JSONDecode(rawBody) end)
        return true, okJson and decoded or rawBody
    end
    return false, "HTTP " .. tostring(code)
end

-- Cola de reportes al Backend
local pendingReportQueue = {}
local isFlushingQueue = false
local lastReportTime = 0

local function flushReportQueue()
    isFlushingQueue = false
    if #pendingReportQueue == 0 then return end

    local now = os.time()
    if now - lastReportTime < CONFIG.REPORT_COOLDOWN then
        task.wait(CONFIG.REPORT_COOLDOWN - (now - lastReportTime))
    end
    lastReportTime = os.time()

    local eggsToSend = pendingReportQueue
    pendingReportQueue = {}

    local serverRegion = "Global"
    pcall(function()
        if game.ServerRegion then serverRegion = tostring(game.ServerRegion) end
    end)

    local payload = {
        placeId = game.PlaceId,
        jobId = game.JobId ~= "" and game.JobId or "dev-test-job-id",
        serverRegion = serverRegion,
        reportTimestamp = os.time(),
        eggs = eggsToSend
    }

    task.spawn(function()
        local endpoint = CONFIG.BACKEND_URL .. CONFIG.ENDPOINTS.REPORT
        sendHttpRequest(endpoint, "POST", payload)
    end)
end

local function queueEggForReport(eggData)
    table.insert(pendingReportQueue, {
        id = eggData.id,
        name = eggData.name,
        rarity = eggData.rarity,
        value = eggData.value,
        spawnTime = eggData.spawnTime
    })
    if not isFlushingQueue then
        isFlushingQueue = true
        task.delay(CONFIG.REPORT_COOLDOWN, flushReportQueue)
    end
end

-- ========================================================
-- 4. EXTRACCIÓN DINÁMICA DE PROPIEDADES EN SLOTS
-- ========================================================
local function extractProperty(instance, aliases)
    if not instance then return nil end
    for _, alias in ipairs(aliases) do
        local attr = instance:GetAttribute(alias)
        if attr ~= nil then return attr end
    end
    for _, alias in ipairs(aliases) do
        local child = instance:FindFirstChild(alias)
        if child and child:IsA("ValueBase") then return child.Value end
    end
    for _, desc in ipairs(instance:GetDescendants()) do
        if desc:IsA("TextLabel") then
            for _, alias in ipairs(aliases) do
                if string.find(string.lower(desc.Name), string.lower(alias)) then
                    return desc.Text
                end
            end
        end
    end
    return nil
end

local function extractSlotEggData(slot)
    if not slot or not slot.Parent then return nil end
    if Players:GetPlayerFromCharacter(slot) then return nil end

    -- El slot puede tener un modelo de huevo como hijo o ser el modelo en sí
    local eggInstance = slot:FindFirstChild("Egg") 
        or slot:FindFirstChildWhichIsA("Model") 
        or slot:FindFirstChildWhichIsA("BasePart") 
        or slot

    -- Buscar parte física central para CFrame y ESP
    local rootPart = nil
    if eggInstance:IsA("BasePart") then
        rootPart = eggInstance
    elseif eggInstance:IsA("Model") then
        rootPart = eggInstance.PrimaryPart or eggInstance:FindFirstChildWhichIsA("BasePart")
    end
    if not rootPart and slot:IsA("BasePart") then
        rootPart = slot
    elseif not rootPart then
        rootPart = slot:FindFirstChildWhichIsA("BasePart", true)
    end
    if not rootPart then return nil end

    -- Extraer Nombre
    local name = extractProperty(eggInstance, CONFIG.PROPERTY_ALIASES.Name)
        or extractProperty(slot, CONFIG.PROPERTY_ALIASES.Name)

    if not name or name == "" or name == "Egg" or name == "Model" or name == "Hitbox" then
        if eggInstance ~= slot and eggInstance.Name ~= "Egg" and eggInstance.Name ~= "Model" and eggInstance.Name ~= "Hitbox" then
            name = eggInstance.Name
        else
            name = slot.Name
        end
    end

    -- Extraer Rareza
    local rarity = extractProperty(eggInstance, CONFIG.PROPERTY_ALIASES.Rarity) 
        or extractProperty(slot, CONFIG.PROPERTY_ALIASES.Rarity)

    if not rarity or type(rarity) ~= "string" then
        local found = "Common"
        for rName, _ in pairs(CONFIG.RARITIES) do
            if string.find(string.lower(name), string.lower(rName)) then
                found = rName
                break
            end
        end
        rarity = found
    end

    -- Extraer Valor
    local rawVal = extractProperty(eggInstance, CONFIG.PROPERTY_ALIASES.Value) 
        or extractProperty(slot, CONFIG.PROPERTY_ALIASES.Value)
    local val = parseFormattedNumber(rawVal)
    if val == 0 and CONFIG.RARITIES[rarity] then
        val = CONFIG.RARITIES[rarity].Threshold
    end

    -- Extraer Tiempo restante si el slot muestra contador
    local timeLeft = extractProperty(eggInstance, CONFIG.PROPERTY_ALIASES.Timer) 
        or extractProperty(slot, CONFIG.PROPERTY_ALIASES.Timer)

    return {
        id = slot:GetAttribute("SlotID") or slot:GetAttribute("EggID") or slot:GetFullName(),
        slotName = slot.Name,
        name = name,
        rarity = rarity,
        value = val,
        timeLeft = timeLeft and tostring(timeLeft) or nil,
        instance = eggInstance,
        slotInstance = slot,
        rootPart = rootPart,
        spawnTime = os.time()
    }
end

-- ========================================================
-- 5. SISTEMA ESP VISUAL REACTIVO
-- ========================================================
local activeTrackedSlots = {} -- [slotInstance] = { data = ..., esp = ..., hash = ... }
local espEnabled = true
local autoTpEnabled = false
local autoTpMinRarity = "Legendary"
local rayfieldInstance = nil

local function createOrUpdateESP(slotItem)
    local eggItem = slotItem.data
    if not eggItem or not eggItem.rootPart or not eggItem.rootPart.Parent then return end

    local color = (CONFIG.RARITIES[eggItem.rarity] and CONFIG.RARITIES[eggItem.rarity].Color) or Color3.fromRGB(255, 255, 255)

    local bb = slotItem.esp
    if not bb or not bb.Parent then
        bb = Instance.new("BillboardGui")
        bb.Name = "EggSlotESP"
        bb.Adornee = eggItem.rootPart
        bb.Size = UDim2.new(0, 160, 0, 52)
        bb.StudsOffset = Vector3.new(0, 4, 0)
        bb.AlwaysOnTop = true
        bb.Enabled = espEnabled

        local mainFrame = Instance.new("Frame")
        mainFrame.Name = "MainFrame"
        mainFrame.Size = UDim2.new(1, 0, 1, 0)
        mainFrame.BackgroundColor3 = Color3.fromRGB(15, 15, 20)
        mainFrame.BackgroundTransparency = 0.3
        mainFrame.BorderSizePixel = 0
        mainFrame.Parent = bb

        local uicorner = Instance.new("UICorner")
        uicorner.CornerRadius = UDim.new(0, 6)
        uicorner.Parent = mainFrame

        local uistroke = Instance.new("UIStroke")
        uistroke.Name = "Stroke"
        uistroke.Color = color
        uistroke.Thickness = 1.8
        uistroke.Parent = mainFrame

        local title = Instance.new("TextLabel")
        title.Name = "Title"
        title.Size = UDim2.new(1, 0, 0.48, 0)
        title.BackgroundTransparency = 1
        title.TextColor3 = color
        title.TextScaled = true
        title.Font = Enum.Font.GothamBold
        title.Parent = mainFrame

        local subTitle = Instance.new("TextLabel")
        subTitle.Name = "SubTitle"
        subTitle.Position = UDim2.new(0, 0, 0.48, 0)
        subTitle.Size = UDim2.new(1, 0, 0.48, 0)
        subTitle.BackgroundTransparency = 1
        subTitle.TextColor3 = Color3.fromRGB(240, 240, 240)
        subTitle.TextScaled = true
        subTitle.Font = Enum.Font.Gotham
        subTitle.Parent = mainFrame

        local parentTarget = (pcall(function() return game:GetService("CoreGui") end) and game:GetService("CoreGui")) or Workspace
        bb.Parent = parentTarget
        slotItem.esp = bb
    end

    -- Actualizar adornee por si el modelo cambió
    bb.Adornee = eggItem.rootPart

    local frame = bb:FindFirstChild("MainFrame")
    if frame then
        local stroke = frame:FindFirstChild("Stroke")
        if stroke then stroke.Color = color end

        local title = frame:FindFirstChild("Title")
        if title then
            title.Text = string.format("🥚 %s", eggItem.name)
            title.TextColor3 = color
        end

        local subTitle = frame:FindFirstChild("SubTitle")
        if subTitle then
            local timerText = eggItem.timeLeft and string.format(" ⏳%s", eggItem.timeLeft) or ""
            subTitle.Text = string.format("[%s] %s pts%s", eggItem.rarity, formatNumber(eggItem.value), timerText)
        end
    end
end

local function setESPVisible(visible)
    espEnabled = visible
    for _, item in pairs(activeTrackedSlots) do
        if item.esp then
            item.esp.Enabled = visible
        end
    end
end

-- ========================================================
-- 6. TELEPORT AL HUEVO / SLOT
-- ========================================================
local function teleportPlayerTo(cframe)
    local char = LocalPlayer.Character or LocalPlayer.CharacterAdded:Wait()
    local root = char:FindFirstChild("HumanoidRootPart") or char:FindFirstChild("Torso")
    if root then
        root.CFrame = cframe + Vector3.new(0, 3.5, 0)
        print("[Tracker] Teletransportado a posición del huevo.")
    end
end

local function teleportToSlot(slotInstance)
    local item = activeTrackedSlots[slotInstance]
    if item and item.data and item.data.rootPart then
        teleportPlayerTo(item.data.rootPart.CFrame)
    else
        warn("[Tracker] El slot no tiene huevo activo en este momento.")
    end
end

local function teleportToBestEgg()
    local best = nil
    local maxVal = -1
    for _, item in pairs(activeTrackedSlots) do
        if item.data and item.data.value > maxVal and item.data.rootPart then
            maxVal = item.data.value
            best = item
        end
    end
    if best and best.data.rootPart then
        teleportPlayerTo(best.data.rootPart.CFrame)
        print(string.format("[Tracker] TP al mejor huevo: %s (%s)", best.data.name, formatNumber(best.data.value)))
    else
        warn("[Tracker] No hay huevos activos disponibles.")
    end
end

local function checkAutoTeleport(eggData)
    if not autoTpEnabled or not eggData or not eggData.rootPart then return end
    local eggRank = (CONFIG.RARITIES[eggData.rarity] and CONFIG.RARITIES[eggData.rarity].Rank) or 1
    local reqRank = (CONFIG.RARITIES[autoTpMinRarity] and CONFIG.RARITIES[autoTpMinRarity].Rank) or 5

    if eggRank >= reqRank then
        print(string.format("[Tracker] [AUTO-TP] Huevo de alta rareza detectado: %s [%s]", eggData.name, eggData.rarity))
        teleportPlayerTo(eggData.rootPart.CFrame)
        if rayfieldInstance then
            rayfieldInstance:Notify({
                Title = "⚡ AUTO-TP ACTIVADO",
                Content = string.format("Teletransportado a: %s [%s]", eggData.name, eggData.rarity),
                Duration = 4
            })
        end
    end
end

-- ========================================================
-- 7. MOTOR DE DETECCIÓN Y ACTUALIZACIÓN EN VIVO (SLOTS)
-- ========================================================
local function processSlot(slot)
    if not slot or not slot.Parent then return end

    local data = extractSlotEggData(slot)
    if not data or not data.rootPart then
        -- Slot vacío o sin huevo activo
        if activeTrackedSlots[slot] then
            if activeTrackedSlots[slot].esp then
                pcall(function() activeTrackedSlots[slot].esp:Destroy() end)
            end
            activeTrackedSlots[slot] = nil
        end
        return
    end

    -- Hash de estado para detectar si el huevo se actualizó por tiempo
    local stateHash = string.format("%s_%s_%s", data.name, data.rarity, tostring(data.value))

    local existing = activeTrackedSlots[slot]
    if existing then
        if existing.hash ~= stateHash then
            -- ¡EL HUEVO EN ESTE SLOT CAMBIÓ POR TIEMPO!
            local oldName = existing.data.name
            existing.data = data
            existing.hash = stateHash
            createOrUpdateESP(existing)

            print(string.format("[Tracker] 🔄 Huevo rotó en slot '%s': %s -> %s [%s] (%s pts)",
                slot.Name, oldName, data.name, data.rarity, formatNumber(data.value)))

            -- Reportar al backend
            local minReq = (CONFIG.RARITIES[CONFIG.MIN_REPORT_RARITY] and CONFIG.RARITIES[CONFIG.MIN_REPORT_RARITY].Threshold) or 500
            if data.value >= minReq then
                queueEggForReport(data)
            end

            -- Revisar si dispara Auto-TP
            checkAutoTeleport(data)
        else
            -- Si el timer cambió, refrescar el texto
            if existing.data.timeLeft ~= data.timeLeft then
                existing.data.timeLeft = data.timeLeft
                createOrUpdateESP(existing)
            end
        end
    else
        -- Nuevo huevo registrado en el slot
        local item = { data = data, esp = nil, hash = stateHash }
        activeTrackedSlots[slot] = item
        createOrUpdateESP(item)

        local minReq = (CONFIG.RARITIES[CONFIG.MIN_REPORT_RARITY] and CONFIG.RARITIES[CONFIG.MIN_REPORT_RARITY].Threshold) or 500
        if data.value >= minReq then
            queueEggForReport(data)
        end

        checkAutoTeleport(data)
    end
end

local function hookSlotReactively(slot)
    if not slot then return end

    -- 1. Escuchar cambios de atributos (el juego suele actualizar Rarity, Value o EggName por atributos)
    local attrConn = slot.AttributeChanged:Connect(function()
        task.defer(function() processSlot(slot) end)
    end)
    registerCleanup(function() attrConn:Disconnect() end)

    -- 2. Escuchar si un nuevo modelo de huevo entra al slot
    local childAddConn = slot.ChildAdded:Connect(function()
        task.defer(function() processSlot(slot) end)
    end)
    registerCleanup(function() childAddConn:Disconnect() end)

    local childRemConn = slot.ChildRemoved:Connect(function()
        task.defer(function() processSlot(slot) end)
    end)
    registerCleanup(function() childRemConn:Disconnect() end)

    -- 3. Escuchar cambios de textos/valores en los descendientes del slot
    for _, desc in ipairs(slot:GetDescendants()) do
        if desc:IsA("ValueBase") then
            local valConn = desc.Changed:Connect(function() task.defer(function() processSlot(slot) end) end)
            registerCleanup(function() valConn:Disconnect() end)
        elseif desc:IsA("TextLabel") then
            local txtConn = desc:GetPropertyChangedSignal("Text"):Connect(function() task.defer(function() processSlot(slot) end) end)
            registerCleanup(function() txtConn:Disconnect() end)
        end
    end

    local descAddConn = slot.DescendantAdded:Connect(function(desc)
        if desc:IsA("ValueBase") then
            local valConn = desc.Changed:Connect(function() task.defer(function() processSlot(slot) end) end)
            registerCleanup(function() valConn:Disconnect() end)
        elseif desc:IsA("TextLabel") then
            local txtConn = desc:GetPropertyChangedSignal("Text"):Connect(function() task.defer(function() processSlot(slot) end) end)
            registerCleanup(function() txtConn:Disconnect() end)
        end
        processSlot(slot)
    end)
    registerCleanup(function() descAddConn:Disconnect() end)

    -- Proceso inicial
    processSlot(slot)
end

local function monitorAreaSlots()
    local areaSlotsFolder = Workspace:FindFirstChild(CONFIG.PRIMARY_CONTAINER)
    if not areaSlotsFolder then
        print(string.format("[Tracker] Esperando que aparezca %s en Workspace...", CONFIG.PRIMARY_CONTAINER))
        areaSlotsFolder = Workspace:WaitForChild(CONFIG.PRIMARY_CONTAINER, 10)
    end

    if areaSlotsFolder then
        print(string.format("[Tracker] ✅ Conectado exitosamente a: %s", CONFIG.PRIMARY_CONTAINER))

        -- Conectar a cada slot hijo existente
        for _, slot in ipairs(areaSlotsFolder:GetChildren()) do
            hookSlotReactively(slot)
            -- Si hay slots anidados por zona (ej: AreaEggSlotsClient -> Zona1 -> Slot)
            for _, subSlot in ipairs(slot:GetChildren()) do
                if subSlot:IsA("Model") or subSlot:IsA("Folder") or subSlot:IsA("BasePart") then
                    hookSlotReactively(subSlot)
                end
            end
        end

        -- Escuchar si se agregan nuevos slots dinámicamente
        local folderChildAdded = areaSlotsFolder.ChildAdded:Connect(function(child)
            hookSlotReactively(child)
        end)
        registerCleanup(function() folderChildAdded:Disconnect() end)
    else
        warn(string.format("[Tracker] No se encontró %s tras 10s. Monitoreando alternativas...", CONFIG.PRIMARY_CONTAINER))
    end

    -- Bucle suave de comprobación por tiempo (para slots cuyos temporizadores rotan internamente)
    task.spawn(function()
        while genv._STEAL_AN_EGG_TRACKER_LOADED do
            task.wait(1.5) -- Comprobación cada 1.5s
            local folder = Workspace:FindFirstChild(CONFIG.PRIMARY_CONTAINER)
            if folder then
                for _, slot in ipairs(folder:GetChildren()) do
                    processSlot(slot)
                    for _, subSlot in ipairs(slot:GetChildren()) do
                        if subSlot:IsA("Model") or subSlot:IsA("Folder") or subSlot:IsA("BasePart") then
                            processSlot(subSlot)
                        end
                    end
                end
            end
        end
    end)

    -- Monitorear también carpetas secundarias por compatibilidad
    for _, secName in ipairs(CONFIG.SECONDARY_FOLDERS) do
        local secFolder = Workspace:FindFirstChild(secName)
        if secFolder then
            for _, item in ipairs(secFolder:GetChildren()) do
                processSlot(item)
            end
            local secConn = secFolder.ChildAdded:Connect(function(child)
                task.defer(function() processSlot(child) end)
            end)
            registerCleanup(function() secConn:Disconnect() end)
        end
    end
end

-- ========================================================
-- 8. INTERFAZ GRÁFICA RAYFIELD MODERNA
-- ========================================================
local function loadRayfield()
    local ok, res = pcall(function()
        return loadstring(game:HttpGet("https://sirius.software/rayfield"))()
    end)
    if ok and res then return res end

    local ok2, res2 = pcall(function()
        return loadstring(game:HttpGet("https://raw.githubusercontent.com/SiriusSoftworks/Rayfield/main/source.lua"))()
    end)
    if ok2 and res2 then return res2 end

    return nil
end

local function joinServer(jobId, placeId)
    local pId = placeId or game.PlaceId
    if jobId == game.JobId then
        warn("[Tracker] Ya estás en este servidor.")
        return
    end
    print("[Tracker] Teletransportando al servidor: " .. tostring(jobId))
    TeleportService:TeleportToPlaceInstance(pId, jobId, LocalPlayer)
end

local function startUI()
    local Rayfield = loadRayfield()
    if not Rayfield then
        warn("[Tracker] Error al inicializar Rayfield UI.")
        return
    end
    rayfieldInstance = Rayfield

    registerCleanup(function()
        pcall(function()
            if Rayfield.Destroy then Rayfield:Destroy() end
        end)
    end)

    local Window = Rayfield:CreateWindow({
        Name = "Steal An Egg Tracker 🥚",
        LoadingTitle = "AreaEggSlotsClient Hunter",
        LoadingSubtitle = "Seguimiento y Rotación en Tiempo Real",
        ConfigurationSaving = { Enabled = false },
        KeySystem = false
    })

    -- PESTAÑA 1: SLOTS EN VIVO (AreaEggSlotsClient)
    local LocalTab = Window:CreateTab("Slots de Área", 4483362458)
    LocalTab:CreateSection("Herramientas de Recolección Rápida")

    LocalTab:CreateToggle({
        Name = "👁️ Activar ESP en Slots",
        CurrentValue = espEnabled,
        Flag = "EggESPFlag",
        Callback = function(val)
            setESPVisible(val)
        end
    })

    LocalTab:CreateToggle({
        Name = "⚡ AUTO-TP al Huevo cuando Spawnee",
        CurrentValue = autoTpEnabled,
        Flag = "AutoTPToggleFlag",
        Callback = function(val)
            autoTpEnabled = val
            print("[Tracker] Auto-TP: " .. tostring(val))
        end
    })

    LocalTab:CreateDropdown({
        Name = "Rareza Mínima para AUTO-TP",
        Options = {"Rare", "Epic", "Legendary", "Mythic", "Secret"},
        CurrentOption = autoTpMinRarity,
        MultipleOptions = false,
        Flag = "AutoTPMinRarityFlag",
        Callback = function(opt)
            autoTpMinRarity = type(opt) == "table" and opt[1] or opt
        end
    })

    LocalTab:CreateButton({
        Name = "⚡ TP al Huevo Más Valioso del Servidor",
        Callback = teleportToBestEgg
    })

    LocalTab:CreateSection("Huevos Activos por Slot")

    local function refreshSlotButtons()
        local list = {}
        for slotInst, item in pairs(activeTrackedSlots) do
            if slotInst.Parent and item.data then
                table.insert(list, item)
            end
        end
        table.sort(list, function(a, b) return a.data.value > b.data.value end)

        if #list == 0 then
            Rayfield:Notify({
                Title = "Slots de Área",
                Content = "No hay huevos activos detectados en este momento.",
                Duration = 2
            })
            return
        end

        for i = 1, math.min(#list, 12) do
            local item = list[i]
            local timerTxt = item.data.timeLeft and string.format(" [%s]", item.data.timeLeft) or ""
            local label = string.format("🥚 %s | %s pts [%s]%s -> [TP]",
                item.data.name, formatNumber(item.data.value), item.data.rarity, timerTxt)

            LocalTab:CreateButton({
                Name = label,
                Callback = function()
                    teleportToSlot(item.data.slotInstance)
                end
            })
        end
    end

    LocalTab:CreateButton({
        Name = "🔄 Refrescar Lista de Slots",
        Callback = refreshSlotButtons
    })

    -- PESTAÑA 2: SERVER HOPPING (BACKEND CENTRAL)
    local HopTab = Window:CreateTab("Server Hopping", 4483362458)
    HopTab:CreateSection("Filtro de Servidores Remotos")

    local hopRarity = CONFIG.MIN_REPORT_RARITY

    HopTab:CreateDropdown({
        Name = "Rareza Mínima",
        Options = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic", "Secret"},
        CurrentOption = hopRarity,
        MultipleOptions = false,
        Flag = "HopRaritySelectFlag",
        Callback = function(opt)
            hopRarity = type(opt) == "table" and opt[1] or opt
        end
    })

    HopTab:CreateSection("Servidores Activos en Backend")

    local function refreshHopList()
        local url = string.format("%s%s?minRarity=%s&limit=12",
            CONFIG.BACKEND_URL, CONFIG.ENDPOINTS.SEARCH, hopRarity)
        local ok, data = sendHttpRequest(url, "GET", nil)
        if not ok or not data or #data == 0 then
            Rayfield:Notify({
                Title = "Server Hopping",
                Content = "No hay servidores registrados con rareza: " .. hopRarity,
                Duration = 3
            })
            return
        end

        for _, srv in ipairs(data) do
            local name = srv.bestEggName or "Huevo"
            local valText = formatNumber(srv.highestValue or 0)
            local ttl = srv.timeLeft or 180
            local btnText = string.format("🌐 %s | %s pts | %ds [Unirse]", name, valText, ttl)

            HopTab:CreateButton({
                Name = btnText,
                Callback = function()
                    joinServer(srv.jobId, srv.placeId)
                end
            })
        end

        Rayfield:Notify({
            Title = "Servidores Encontrados",
            Content = string.format("%d servidores con huevos valiosos encontrados.", #data),
            Duration = 3
        })
    end

    HopTab:CreateButton({
        Name = "🔄 Buscar Servidores Ahora",
        Callback = refreshHopList
    })

    -- Carga inicial tras 1.5s
    task.spawn(function()
        task.wait(1.5)
        refreshSlotButtons()
    end)
end

-- ========================================================
-- 9. INICIALIZACIÓN
-- ========================================================
task.spawn(monitorAreaSlots)
task.spawn(startUI)

print("=====================================================")
print("🥚 AreaEggSlotsClient TRACKER & HUNTER ACTIVO")
print("🔄 Monitoreando slots y rotación por tiempo en vivo")
print("=====================================================")
