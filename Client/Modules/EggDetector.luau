--!strict
--[[
    EggDetector.luau
    Módulo especializado en inspección, monitoreo reactivo y extracción
    de datos de huevos generados en "Steal An Egg".
]]

local Workspace = game:GetService("Workspace")
local HttpService = game:GetService("HttpService")

-- Referencia a Config (compatible con require dinámico)
local Config
local success, result = pcall(function()
    return require(script.Parent.Config)
end)
if success and result then
    Config = result
else
    -- Fallback si se carga de forma standalone
    Config = {
        RARITIES = {
            ["Common"] = { Threshold = 0, Rank = 1 },
            ["Uncommon"] = { Threshold = 100, Rank = 2 },
            ["Rare"] = { Threshold = 500, Rank = 3 },
            ["Epic"] = { Threshold = 2000, Rank = 4 },
            ["Legendary"] = { Threshold = 10000, Rank = 5 },
            ["Mythic"] = { Threshold = 50000, Rank = 6 },
            ["Secret"] = { Threshold = 250000, Rank = 7 }
        },
        MIN_REPORT_RARITY = "Rare",
        EGG_FOLDER_CANDIDATES = {"Eggs", "SpawnedEggs", "MapEggs", "DroppedEggs"},
        PROPERTY_ALIASES = {
            Rarity = {"Rarity", "EggRarity", "Tier"},
            Value = {"Value", "EggValue", "Price", "Multiplier"},
            Name = {"EggName", "ItemName", "Name"}
        }
    }
end

local EggDetector = {}
EggDetector.__index = EggDetector

-- Registro de instancias procesadas y sus hashes de estado (para detectar rotaciones por tiempo)
local trackedEggs: { [Instance]: boolean } = {}
local slotStates: { [Instance]: string } = {}
local activeConnections: { [string]: RBXScriptConnection } = {}

--[[
    Localiza de manera inteligente el contenedor de huevos.
    Prioriza AreaEggSlotsClient donde los huevos se mantienen y actualizan con el tiempo.
]]
function EggDetector.FindEggContainer(): Instance
    -- 1. Priorizar contenedor primario de slots
    local primaryName = Config.PRIMARY_SLOT_CONTAINER or "AreaEggSlotsClient"
    local primary = Workspace:FindFirstChild(primaryName)
    if primary and (primary:IsA("Folder") or primary:IsA("Model")) then
        print(string.format("[EggDetector] Contenedor de slots prioritario encontrado: %s", primary:GetFullName()))
        return primary
    end

    -- 2. Búsqueda por candidatos conocidos
    for _, folderName in ipairs(Config.EGG_FOLDER_CANDIDATES) do
        local direct = Workspace:FindFirstChild(folderName)
        if direct and (direct:IsA("Folder") or direct:IsA("Model")) then
            print(string.format("[EggDetector] Contenedor encontrado por nombre: %s", direct:GetFullName()))
            return direct
        end
    end

    -- 2. Inspección por patrones en descendientes
    for _, desc in ipairs(Workspace:GetChildren()) do
        if desc:IsA("Folder") or desc:IsA("Configuration") or desc:IsA("Model") then
            local lowerName = string.lower(desc.Name)
            if string.find(lowerName, "egg") or string.find(lowerName, "drop") or string.find(lowerName, "spawn") then
                print(string.format("[EggDetector] Contenedor inferido por coincidencia parcial: %s", desc:GetFullName()))
                return desc
            end
        end
    end

    warn("[EggDetector] No se localizó carpeta específica; usando Workspace como raíz de observación.")
    return Workspace
end

--[[
    Extrae un valor buscando en Atributos de Roblox, ValueObjects hijos, o nombres de propiedades.
]]
local function readProperty(instance: Instance, aliasGroup: {string}): any
    -- Primero verificar Attributes nativos (Roblox Attributes)
    for _, alias in ipairs(aliasGroup) do
        local attr = instance:GetAttribute(alias)
        if attr ~= nil then
            return attr
        end
    end

    -- Luego verificar ValueObjects hijos (StringValue, NumberValue, IntValue, etc.)
    for _, alias in ipairs(aliasGroup) do
        local childVal = instance:FindFirstChild(alias)
        if childVal and childVal:IsA("ValueBase") then
            return (childVal :: any).Value
        end
    end

    -- Verificar TextLabel dentro de BillboardGui (muy común para mostrar rareza en juegos)
    for _, desc in ipairs(instance:GetDescendants()) do
        if desc:IsA("TextLabel") then
            for _, alias in ipairs(aliasGroup) do
                if string.find(string.lower(desc.Name), string.lower(alias)) then
                    return desc.Text
                end
            end
        end
    end

    return nil
end

local function parseFormattedNumber(val: any): number
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

--[[
    Extrae la información normalizada de un modelo o parte que represente un huevo.
]]
function EggDetector.ExtractData(instance: Instance): any
    if not (instance:IsA("Model") or instance:IsA("BasePart")) then
        return nil
    end

    -- Determinar Nombre
    local eggName = readProperty(instance, Config.PROPERTY_ALIASES.Name) or instance.Name

    -- Determinar Rareza
    local rarity = readProperty(instance, Config.PROPERTY_ALIASES.Rarity)
    if not rarity or type(rarity) ~= "string" then
        -- Inferir rareza del nombre si contiene la palabra (ej: "Legendary Dragon")
        local foundRarity = "Common"
        for rName, _ in pairs(Config.RARITIES) do
            if string.find(string.lower(eggName), string.lower(rName)) then
                foundRarity = rName
                break
            end
        end
        rarity = foundRarity
    end

    -- Determinar Valor / Multiplicador con parser de formato K/M/B
    local rawValue = readProperty(instance, Config.PROPERTY_ALIASES.Value)
    local value = parseFormattedNumber(rawValue)
    if value == 0 and Config.RARITIES[rarity] then
        value = Config.RARITIES[rarity].Threshold
    end

    -- Determinar Posición espacial
    local position = Vector3.zero
    if instance:IsA("Model") then
        local primary = instance.PrimaryPart or instance:FindFirstChildWhichIsA("BasePart")
        if primary then
            position = primary.Position
        end
    elseif instance:IsA("BasePart") then
        position = instance.Position
    end

    -- Comprobar si cumple con el umbral mínimo para telemetría
    local minRarityConfig = Config.RARITIES[Config.MIN_REPORT_RARITY]
    local minThreshold = minRarityConfig and minRarityConfig.Threshold or 500
    if value < minThreshold and (Config.RARITIES[rarity] and Config.RARITIES[rarity].Threshold < minThreshold) then
        return nil
    end

    return {
        id = instance:GetAttribute("EggID") or HttpService:GenerateGUID(false),
        name = eggName,
        rarity = rarity,
        value = value,
        spawnTime = os.time(),
        instance = instance,
        position = { x = position.X, y = position.Y, z = position.Z }
    }
end

--[[
    Inicia la observación activa con soporte para slots que actualizan huevos por tiempo.
]]
function EggDetector.StartMonitoring(customFolder: Instance?, onEggSpawned: (any) -> ())
    local container = customFolder or EggDetector.FindEggContainer()

    local function checkSlot(slot: Instance)
        if not slot.Parent then return end
        local data = EggDetector.ExtractData(slot)
        if not data then
            slotStates[slot] = nil
            return
        end

        local stateHash = string.format("%s_%s_%s", data.name, data.rarity, tostring(data.value))
        if slotStates[slot] ~= stateHash then
            -- El huevo cambió o rotó en el slot
            slotStates[slot] = stateHash
            trackedEggs[slot] = true
            onEggSpawned(data)
        end
    end

    -- 1. Escanear slots existentes y escuchar cambios de atributos/hijos
    for _, child in ipairs(container:GetChildren()) do
        checkSlot(child)
        child.AttributeChanged:Connect(function()
            task.defer(function() checkSlot(child) end)
        end)
    end

    -- 2. Conexión reactiva a nuevos slots o hijos
    if activeConnections["ChildAdded"] then
        activeConnections["ChildAdded"]:Disconnect()
    end

    activeConnections["ChildAdded"] = container.ChildAdded:Connect(function(child)
        task.defer(function()
            checkSlot(child)
            child.AttributeChanged:Connect(function()
                task.defer(function() checkSlot(child) end)
            end)
        end)
    end)

    -- 3. Limpiar referencias cuando un slot sea removido
    if activeConnections["ChildRemoved"] then
        activeConnections["ChildRemoved"]:Disconnect()
    end

    activeConnections["ChildRemoved"] = container.ChildRemoved:Connect(function(child)
        slotStates[child] = nil
        trackedEggs[child] = nil
    end)

    -- 4. Bucle suave de verificación de tiempo (para temporizadores internos del juego)
    task.spawn(function()
        while container.Parent do
            task.wait(1.5)
            for _, child in ipairs(container:GetChildren()) do
                checkSlot(child)
            end
        end
    end)

    print("[EggDetector] Monitoreo iniciado exitosamente en: " .. container.Name)
end

--[[
    Detiene todas las conexiones de monitoreo activas.
]]
function EggDetector.StopMonitoring()
    for key, conn in pairs(activeConnections) do
        conn:Disconnect()
        activeConnections[key] = nil
    end
    table.clear(trackedEggs)
    print("[EggDetector] Monitoreo detenido.")
end

return EggDetector

