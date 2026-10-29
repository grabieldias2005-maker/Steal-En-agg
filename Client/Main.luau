--!strict
--[[
    Main.luau
    Punto de entrada para el cliente en Roblox Studio o LocalScript.
    Inicia la detección de huevos, sincroniza con el NetworkManager y levanta la UI.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

local function safeRequire(modulePath: Instance): any
    local ok, mod = pcall(function()
        return require(modulePath)
    end)
    if not ok then
        warn("[Main] Error al cargar módulo: " .. tostring(modulePath.Name) .. " -> " .. tostring(mod))
        return nil
    end
    return mod
end

-- Cargar módulos desde su jerarquía (o delegar a Standalone si se ejecutó con loadstring)
local scriptParent = (pcall(function() return script.Parent end) and script and script.Parent) or nil
local ModulesFolder = scriptParent and scriptParent:FindFirstChild("Modules")
local InterfaceFolder = scriptParent and scriptParent:FindFirstChild("Interface")

if not ModulesFolder then
    warn("[Main] Modules no encontrados en la jerarquía. Detectada ejecución vía loadstring/executor.")
    warn("[Main] Cargando versión monolítica StandaloneScript...")
    local okStandalone, res = pcall(function()
        return loadstring(game:HttpGet("https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/Client/StandaloneScript.luau"))()
    end)
    if not okStandalone then
        warn("[Main] Para ejecutar vía loadstring, usa directamente StandaloneScript.luau o /script en el backend.")
    end
    return
end

local Config = ModulesFolder and safeRequire(ModulesFolder:WaitForChild("Config"))
local EggDetector = ModulesFolder and safeRequire(ModulesFolder:WaitForChild("EggDetector"))
local NetworkManager = ModulesFolder and safeRequire(ModulesFolder:WaitForChild("NetworkManager"))
local UIController = InterfaceFolder and safeRequire(InterfaceFolder:WaitForChild("UIController"))

print("[Main] Inicializando Steal An Egg Tracker...")

-- Iniciar UI
if UIController and UIController.Initialize then
    task.spawn(function()
        UIController.Initialize()
    end)
end

-- Iniciar Detección en segundo plano
if EggDetector and NetworkManager then
    task.spawn(function()
        EggDetector.StartMonitoring(nil, function(eggData)
            print(string.format("[Main] Nuevo huevo detectado: %s (%s, Valor: %d)", eggData.name, eggData.rarity, eggData.value))
            NetworkManager.QueueEgg(eggData)
        end)
    end)
end

print("[Main] Steal An Egg Tracker activo y monitoreando.")

