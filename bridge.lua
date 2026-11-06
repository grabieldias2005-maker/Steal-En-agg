-- ==============================================================================
-- 🥚 HUEVOSTOONS - BRIDGE & RUNNER ENTORNO EN VIVO
-- Se ejecuta junto al loader de FlowAuth en Steal An Egg
-- ==============================================================================

local SERVER_URL = "http://localhost:3000"
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local Workspace = game:GetService("Workspace")
local TeleportService = game:GetService("TeleportService")

local requestFn = (syn and syn.request) or (http and http.request) or http_request or (fluxus and fluxus.request) or request

local function logWeb(msg)
    print("[HuevosToons] " .. msg)
    if requestFn then
        pcall(function()
            requestFn({
                Url = SERVER_URL .. "/api/runner/logs",
                Method = "POST",
                Headers = { ["Content-Type"] = "application/json" },
                Body = HttpService:JSONEncode({ message = msg, jobId = game.JobId, time = os.date("%X") })
            })
        end)
    end
end

logWeb("✅ Entorno de ejecución iniciado en servidor: " .. game.JobId)

-- Ejecutar el loader de FlowAuth si aún no se ha ejecutado
task.spawn(function()
    pcall(function()
        logWeb("🚀 Cargando script de FlowAuth...")
        loadstring(game:HttpGet("https://flowauth.net/v1/loaders/cacd453cf780cca1885f79c734f492fa.lua"))()
        logWeb("✨ Script FlowAuth activo.")
    end)
end)

-- Rastreador continuo de huevos
local function scanAndSync()
    local detected = {}
    
    for _, obj in ipairs(Workspace:GetDescendants()) do
        local n = string.lower(obj.Name)
        if string.find(n, "egg") or obj:FindFirstChild("BillboardGui") or string.find(n, "huevo") then
            local petName = nil
            local scale = 1.0
            local area = "Zona Principal"
            local mutations = {}
            local claimed = false
            
            for _, gui in ipairs(obj:GetDescendants()) do
                if gui:IsA("TextLabel") and gui.Text and #gui.Text > 0 then
                    local t = gui.Text
                    local mMatch = string.match(t, "x?([%d%.]+)x?")
                    if mMatch and tonumber(mMatch) and tonumber(mMatch) > 1 then
                        scale = tonumber(mMatch)
                    end
                    if string.find(string.lower(t), "gold") then table.insert(mutations, "Golden") end
                    if string.find(string.lower(t), "rainbow") then table.insert(mutations, "Rainbow") end
                    if string.find(string.lower(t), "silver") then table.insert(mutations, "Silver") end
                    if string.find(string.lower(t), "robado") or string.find(string.lower(t), "claimed") then claimed = true end
                end
            end
            
            if scale > 1.5 then
                table.insert(detected, {
                    animal = petName or obj.Name,
                    area = area,
                    scale = scale,
                    mutations = mutations,
                    claimed = claimed
                })
            end
        end
    end
    
    if #detected > 0 then
        logWeb("🎯 Detectados " .. #detected .. " huevos en este servidor. Sincronizando con el radar...")
        pcall(function()
            requestFn({
                Url = SERVER_URL .. "/api/report",
                Method = "POST",
                Headers = { ["Content-Type"] = "application/json" },
                Body = HttpService:JSONEncode({
                    jobId = game.JobId,
                    placeId = game.PlaceId,
                    players = #Players:GetPlayers(),
                    maxPlayers = Players.MaxPlayers or 7,
                    eggs = detected
                })
            })
        end)
    end
end

task.spawn(function()
    while true do
        task.wait(3)
        scanAndSync()
    end
end)

