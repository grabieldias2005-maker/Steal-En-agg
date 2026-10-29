--!strict
--[[
    Config.luau
    Configuración central para Steal An Egg Tracker.
    Actualizado con la jerarquía real del juego (Workspace: Eggs, PlacedEggRenders, HalloweenEggHolders, etc.)
]]

local Config = {}

-- URLs de conexión con el backend central
Config.BACKEND_URL = "http://localhost:3000"
Config.ENDPOINTS = {
    REPORT = "/api/eggs/report",
    SEARCH = "/api/eggs/search"
}

-- Intervalos y control de tráfico (en segundos)
Config.NETWORK = {
    REPORT_COOLDOWN = 3,       -- Intervalo mínimo entre envíos para no saturar
    POLL_INTERVAL = 10,        -- Intervalo de refresco
    REQUEST_TIMEOUT = 10
}

-- Escala de Rarezas con valores de corte y colores
Config.RARITIES = {
    ["Common"]    = { Threshold = 0,         Rank = 1, Color = Color3.fromRGB(180, 180, 180) },
    ["Uncommon"]  = { Threshold = 100,       Rank = 2, Color = Color3.fromRGB(100, 255, 100) },
    ["Rare"]      = { Threshold = 500,       Rank = 3, Color = Color3.fromRGB(80, 160, 255) },
    ["Epic"]      = { Threshold = 2000,      Rank = 4, Color = Color3.fromRGB(180, 80, 255) },
    ["Legendary"] = { Threshold = 10000,     Rank = 5, Color = Color3.fromRGB(255, 170, 0) },
    ["Mythic"]    = { Threshold = 50000,     Rank = 6, Color = Color3.fromRGB(255, 60, 80) },
    ["Secret"]    = { Threshold = 250000,    Rank = 7, Color = Color3.fromRGB(0, 255, 230) }
}

-- Filtro mínimo para telemetría
Config.MIN_REPORT_RARITY = "Rare"

-- Contenedor principal donde los huevos se mantienen y actualizan con el tiempo
Config.PRIMARY_SLOT_CONTAINER = "AreaEggSlotsClient"

-- Carpetas de huevos en Workspace (orden de prioridad)
Config.EGG_FOLDER_CANDIDATES = {
    "AreaEggSlotsClient",       -- Principal: slots de huevos por área con actualización por tiempo
    "Eggs",                     -- Carpeta general
    "PlacedEggRenders",         -- Renderizado de huevos colocados en el mapa
    "HalloweenEggHolders",      -- Evento de Halloween / holders especiales
    "Stands",                   -- Stands donde los jugadores guardan/muestran huevos
    "Plots",                    -- Parcelas de jugadores
    "SpawnedEggs",              -- Compatibilidad
    "MapEggs",
    "DroppedEggs"
}

-- Propiedades y atributos utilizados para extraer datos
Config.PROPERTY_ALIASES = {
    Rarity = {"Rarity", "EggRarity", "Tier", "EggTier", "RarityTag"},
    Value  = {"Value", "EggValue", "Price", "Multiplier", "Points", "Cost", "Money"},
    Name   = {"EggName", "ItemName", "Title", "Name"},
    Timer  = {"TimeLeft", "Timer", "Time", "Cooldown", "Respawn", "SecondsLeft"}
}

return Config
