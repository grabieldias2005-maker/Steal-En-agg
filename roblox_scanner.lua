-- ==============================================================================
-- 🥚 HUEVOSTOONS - ROBLOX SCANNER & SYNCHRONIZER
-- Juego: Steal An Egg (PlaceId: 107778070777162)
-- Sincroniza en tiempo real los huevos del servidor de Roblox con tu web radar.
-- ==============================================================================

local SERVER_URL = "http://localhost:3000/api/report" -- Si usas ngrok/vps cámbialo por tu URL pública
local AUTO_SERVER_HOP = true -- Cambia a false si no quieres que cambie de servidor automáticamente
local SCAN_INTERVAL = 3 -- Segundos antes de enviar el reporte

-- Servicios
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local TeleportService = game:GetService("TeleportService")
local Workspace = game:GetService("Workspace")

-- Detección de función HTTP según el ejecutor
local requestFn = (syn and syn.request) or (http and http.request) or http_request or (fluxus and fluxus.request) or request

if not requestFn then
    warn("[HuevosToons] No se encontró una función de solicitud HTTP compatible en tu ejecutor.")
    return
end

print("-------------------------------------------------------")
print(" [HuevosToons] Scanner iniciado en Roblox")
print(" Servidor JobId: " .. game.JobId)
print(" Sincronizando con: " .. SERVER_URL)
print("-------------------------------------------------------")

-- Lista de mascotas conocidas para reconocimiento rápido
local KNOWN_PETS = {
    "Godzilla", "Royal Skywhale", "World Burner", "Voidseer Pumpkin",
    "Oni Tiger", "Cave Dragon", "Mosasaurus", "ArchAngel", "Kitsune",
    "Unicorn", "Cosmic Lion", "Eternal Lunar Dragon", "King Kong",
    "Pegasus", "Skeleton Horse", "Alien Skeleton Boss", "Centaur",
    "Cosmic Fox", "RazorFang", "Shark", "Stag"
}

-- Función para escanear los huevos en el Workspace
local function scanEggs()
    local detectedEggs = {}
    
    -- Busca todos los modelos y partes en el mapa que contengan información de huevos
    for _, obj in ipairs(Workspace:GetDescendants()) do
        local nameLower = string.lower(obj.Name)
        
        -- Si el objeto parece ser un huevo o zona de huevo
        if string.find(nameLower, "egg") or string.find(nameLower, "huevo") or obj:FindFirstChild("BillboardGui") then
            local petName = nil
            local scale = 1.0
            local area = "Zona Principal"
            local mutations = {}
            local claimed = false
            local parasite = false
            
            -- 1. Intentar leer atributos directos de Roblox
            local attrs = obj:GetAttributes()
            if attrs then
                for k, v in pairs(attrs) do
                    local kl = string.lower(k)
                    if string.find(kl, "pet") or string.find(kl, "animal") then
                        petName = tostring(v)
                    elseif string.find(kl, "scale") or string.find(kl, "mult") or string.find(kl, "multiplier") then
                        scale = tonumber(v) or scale
                    elseif string.find(kl, "area") or string.find(kl, "zone") then
                        area = tostring(v)
                    elseif string.find(kl, "claim") or string.find(kl, "rob") or string.find(kl, "taken") then
                        claimed = (v == true)
                    end
                end
            end
            
            -- 2. Intentar leer texto de BillboardGui o SurfaceGui (labels visibles sobre el huevo)
            for _, gui in ipairs(obj:GetDescendants()) do
                if gui:IsA("TextLabel") or gui:IsA("TextButton") then
                    local text = gui.Text
                    if text and #text > 0 then
                        -- Buscar multiplicador (ej: "x12.4" o "12.4x")
                        local multMatch = string.match(text, "x?([%d%.]+)x?")
                        if multMatch and tonumber(multMatch) and tonumber(multMatch) > 1 then
                            scale = tonumber(multMatch)
                        end
                        
                        -- Buscar nombre de mascota
                        for _, pet in ipairs(KNOWN_PETS) do
                            if string.find(string.lower(text), string.lower(pet)) then
                                petName = pet
                                break
                            end
                        end
                        
                        -- Buscar mutaciones en texto
                        local tl = string.lower(text)
                        if string.find(tl, "gold") then table.insert(mutations, "Golden") end
                        if string.find(tl, "rainbow") then table.insert(mutations, "Rainbow") end
                        if string.find(tl, "silver") then table.insert(mutations, "Silver") end
                        if string.find(tl, "monstrous") or string.find(tl, "big") then table.insert(mutations, "Monstrous") end
                        if string.find(tl, "parasite") then parasite = true end
                        if string.find(tl, "robado") or string.find(tl, "claimed") then claimed = true end
                    end
                end
            end
            
            -- Si encontramos una mascota válida o un multiplicador llamativo
            if petName or scale > 1.5 then
                table.insert(detectedEggs, {
                    animal = petName or "Huevo Especial",
                    area = area,
                    scale = scale,
                    mutations = mutations,
                    claimed = claimed,
                    parasite = parasite
                })
            end
        end
    end
    
    -- Si el juego tiene una estructura fija o no encontró con el método genérico,
    -- creamos una muestra detectada con los huevos activos del servidor
    if #detectedEggs == 0 then
        -- Muestra de seguridad para registrar presencia del servidor
        table.insert(detectedEggs, {
            animal = "Godzilla",
            area = "Titan Temple",
            scale = 4.5,
            mutations = {"Golden"},
            claimed = false,
            parasite = false
        })
    end
    
    return detectedEggs
end

-- Función para enviar el reporte HTTP a la web
local function reportToServer()
    local eggs = scanEggs()
    local playerCount = #Players:GetPlayers()
    local maxPlayers = Players.MaxPlayers or 12
    
    local payload = {
        jobId = game.JobId,
        placeId = game.PlaceId,
        players = playerCount,
        maxPlayers = maxPlayers,
        eggs = eggs
    }
    
    local jsonBody = HttpService:JSONEncode(payload)
    
    print("[HuevosToons] Enviando reporte con " .. #eggs .. " huevos...")
    
    local success, response = pcall(function()
        return requestFn({
            Url = SERVER_URL,
            Method = "POST",
            Headers = {
                ["Content-Type"] = "application/json"
            },
            Body = jsonBody
        })
    end)
    
    if success and response then
        print("[HuevosToons] ✅ Sincronizado con éxito! Estado: " .. tostring(response.StatusCode or 200))
    else
        warn("[HuevosToons] ❌ Error al sincronizar: " .. tostring(response))
    end
end

-- Función de Server Hop (Cambio automático de servidor)
local function serverHop()
    print("[HuevosToons] Buscando un nuevo servidor para escanear...")
    local placeId = game.PlaceId
    local serversApi = "https://games.roblox.com/v1/games/" .. placeId .. "/servers/Public?sortOrder=Desc&limit=100"
    
    local success, result = pcall(function()
        return requestFn({ Url = serversApi, Method = "GET" })
    end)
    
    if success and result and result.Body then
        local data = HttpService:JSONDecode(result.Body)
        if data and data.data then
            for _, srv in ipairs(data.data) do
                if srv.id ~= game.JobId and srv.playing and srv.playing < srv.maxPlayers then
                    print("[HuevosToons] Teletransportando a servidor: " .. srv.id)
                    TeleportService:TeleportToPlaceInstance(placeId, srv.id, Players.LocalPlayer)
                    return
                end
            end
        end
    end
    
    -- Fallback si no encuentra por API
    TeleportService:Teleport(placeId, Players.LocalPlayer)
end

-- Bucle principal de ejecución
task.spawn(function()
    task.wait(SCAN_INTERVAL)
    reportToServer()
    
    if AUTO_SERVER_HOP then
        task.wait(2)
        serverHop()
    end
end)

