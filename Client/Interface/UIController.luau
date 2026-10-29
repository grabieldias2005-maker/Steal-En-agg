--!strict
--[[
    UIController.luau
    Interfaz de usuario para Steal An Egg Tracker.
    Integra la librería Rayfield con soporte de Server Hopping directo mediante TeleportService.
]]

local TeleportService = game:GetService("TeleportService")
local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

local Config
local NetworkManager

local successConfig, resConfig = pcall(function() return require(script.Parent.Parent.Modules.Config) end)
Config = successConfig and resConfig or {
    RARITIES = {
        ["Common"] = { Rank = 1, Threshold = 0 },
        ["Uncommon"] = { Rank = 2, Threshold = 100 },
        ["Rare"] = { Rank = 3, Threshold = 500 },
        ["Epic"] = { Rank = 4, Threshold = 2000 },
        ["Legendary"] = { Rank = 5, Threshold = 10000 },
        ["Mythic"] = { Rank = 6, Threshold = 50000 },
        ["Secret"] = { Rank = 7, Threshold = 250000 }
    }
}

local successNet, resNet = pcall(function() return require(script.Parent.Parent.Modules.NetworkManager) end)
NetworkManager = successNet and resNet or nil

local UIController = {}
local currentSelectedRarity = "Rare"
local activeServerLabels = {}

-- Función para formatear números a cantidades legibles (1K, 1M, etc.)
local function formatNumber(val: number): string
    if val >= 1000000 then
        return string.format("%.1fM", val / 1000000)
    elseif val >= 1000 then
        return string.format("%.1fK", val / 1000)
    end
    return tostring(val)
end

-- Función para formatear el tiempo transcurrido / tiempo restante
local function formatTimeAgo(secondsAgo: number): string
    if secondsAgo < 60 then
        return string.format("hace %ds", secondsAgo)
    else
        return string.format("hace %dm", math.floor(secondsAgo / 60))
    end
end

--[[
    Ejecuta el teletransporte a la instancia de servidor especificada.
]]
function UIController.JoinServer(jobId: string, placeId: number?)
    local targetPlaceId = placeId or game.PlaceId
    if jobId == game.JobId then
        warn("[UIController] Ya te encuentras en este servidor.")
        return
    end

    print(string.format("[UIController] Iniciando Server Hop hacia JobId: %s...", jobId))
    pcall(function()
        TeleportService:TeleportToPlaceInstance(targetPlaceId, jobId, LocalPlayer)
    end)
end

--[[
    Inicializa la ventana de Rayfield y sus componentes.
]]
function UIController.Initialize()
    local Rayfield
    local rayfieldSuccess, rayfieldResult = pcall(function()
        return loadstring(game:HttpGet("https://sirius.software/rayfield"))()
    end)

    if not rayfieldSuccess or not rayfieldResult then
        warn("[UIController] No se pudo cargar Rayfield directamente desde URL externa. Se utilizará modo UI local o fallback.")
        return UIController.CreateCustomFallbackUI()
    end

    Rayfield = rayfieldResult

    local Window = Rayfield:CreateWindow({
        Name = "Steal An Egg Tracker 🥚",
        LoadingTitle = "Cargando Egg Tracker...",
        LoadingSubtitle = "por Antigravity",
        ConfigurationSaving = {
            Enabled = true,
            FolderName = "StealAnEggTracker",
            FileName = "Config"
        },
        KeySystem = false
    })

    local MainTab = Window:CreateTab("Servidores", 4483362458)
    local InfoSection = MainTab:CreateSection("Filtro y Rastreo")

    -- Dropdown de Rarezas
    local rarityOptions = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic", "Secret"}
    MainTab:CreateDropdown({
        Name = "Rareza Mínima Requerida",
        Options = rarityOptions,
        CurrentOption = "Rare",
        MultipleOptions = false,
        Flag = "RarityFilterDropdown",
        Callback = function(Option)
            currentSelectedRarity = type(Option) == "table" and Option[1] or Option
            UIController.RefreshServerList(MainTab)
        end
    })

    -- Botón de refresco manual
    MainTab:CreateButton({
        Name = "🔄 Actualizar Lista de Servidores",
        Callback = function()
            UIController.RefreshServerList(MainTab)
        end
    })

    local ServersSection = MainTab:CreateSection("Servidores Encontrados")

    -- Función interna para refrescar y renderizar elementos
    function UIController.RefreshServerList(tab)
        if not NetworkManager then return end

        local ok, data = NetworkManager.FetchServers(currentSelectedRarity, 15)
        if not ok or not data or #data == 0 then
            Rayfield:Notify({
                Title = "Búsqueda de Huevos",
                Content = "No se encontraron servidores con huevos " .. currentSelectedRarity .. " activos.",
                Duration = 4
            })
            return
        end

        for _, server in ipairs(data) do
            local secondsSinceUpdate = math.max(0, os.time() - (server.lastReportTime or os.time()))
            local titleText = string.format("🥚 %s | Valor: %s | %s",
                server.bestEggName or "Huevo Especial",
                formatNumber(server.highestValue or 0),
                formatTimeAgo(secondsSinceUpdate)
            )

            local descText = string.format("Región: %s | Huevos activos: %d | TTL: %ds",
                server.region or "Global",
                server.eggCount or 1,
                server.timeLeft or 180
            )

            tab:CreateButton({
                Name = titleText .. "  [Unirse]",
                Callback = function()
                    UIController.JoinServer(server.jobId, server.placeId)
                end
            })
        end
    end

    -- Cargar primera búsqueda
    task.spawn(function()
        task.wait(1)
        UIController.RefreshServerList(MainTab)
    end)

    print("[UIController] Interfaz Rayfield inicializada correctamente.")
end

--[[
    UI Fallback ligera en ScreenGui estándar si la librería externa no está disponible.
]]
function UIController.CreateCustomFallbackUI()
    local CoreGui = game:GetService("CoreGui")
    local screenGui = Instance.new("ScreenGui")
    screenGui.Name = "EggTrackerFallbackGui"
    screenGui.ResetOnSpawn = false

    local frame = Instance.new("Frame")
    frame.Size = UDim2.new(0, 320, 0, 400)
    frame.Position = UDim2.new(0.5, -160, 0.5, -200)
    frame.BackgroundColor3 = Color3.fromRGB(24, 24, 28)
    frame.BorderSizePixel = 0
    frame.Parent = screenGui

    local corner = Instance.new("UICorner")
    corner.CornerRadius = UDim.new(0, 8)
    corner.Parent = frame

    local title = Instance.new("TextLabel")
    title.Size = UDim2.new(1, 0, 0, 35)
    title.Text = "Steal An Egg Tracker (Custom UI)"
    title.TextColor3 = Color3.fromRGB(255, 255, 255)
    title.BackgroundColor3 = Color3.fromRGB(35, 35, 45)
    title.Font = Enum.Font.GothamBold
    title.TextSize = 14
    title.Parent = frame

    local scroll = Instance.new("ScrollingFrame")
    scroll.Size = UDim2.new(1, -20, 1, -55)
    scroll.Position = UDim2.new(0, 10, 0, 45)
    scroll.BackgroundTransparency = 1
    scroll.ScrollBarThickness = 4
    scroll.Parent = frame

    local listLayout = Instance.new("UIListLayout")
    listLayout.Padding = UDim.new(0, 6)
    listLayout.Parent = scroll

    pcall(function()
        screenGui.Parent = CoreGui
    end)
    if not screenGui.Parent then
        screenGui.Parent = LocalPlayer:WaitForChild("PlayerGui")
    end

    print("[UIController] Fallback UI creada.")
end

return UIController

