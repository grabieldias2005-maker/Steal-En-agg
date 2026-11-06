-- ==============================================================================
-- 🥚 HUEVOSTOONS - ROBLOX SCANNER & SYNCHRONIZER
-- Juego: Steal An Egg (PlaceId: 107778070777162)
-- Sincroniza en tiempo real los huevos del servidor de Roblox con tu web radar.
-- ==============================================================================

local SERVER_URL = _G.RADAR_URL or "http://localhost:5000/api/report"
local FALLBACK_URL = "https://steal-an-egg-radar.onrender.com/api/report"
local AUTO_SERVER_HOP = false -- Cambia a true si quieres que rote de servidor automáticamente
local SCAN_INTERVAL = 2 -- Segundos entre comprobaciones en vivo

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
print(" [HuevosToons] Scanner en Vivo Iniciado en Roblox")
print(" Servidor JobId: " .. game.JobId)
print(" Sincronizando con Web Radar: " .. SERVER_URL)
print("-------------------------------------------------------")

-- Lista de mascotas principales de Steal An Egg (RBLX Guide)
local KNOWN_PETS = {
    "Spirit World Guardian", "Voidseer Pumpkin", "Skeletal Sabertooth",
    "Royal Skywhale", "Bone Emperor", "Mecha Scrambler", "Aetheron",
    "Luminous Cthulhu", "ArchAngel", "World Burner", "Skeletal Gigantus",
    "Godzilla", "Eternal Lunar Dragon", "Cave Dragon", "Ice Dragon",
    "Cerberus", "Oni Tiger", "Mosasaurus", "Unicorn", "Cosmic Lion",
    "King Kong", "Pegasus", "Skeleton Horse", "Alien Skeleton Boss",
    "Centaur", "Cosmic Fox", "RazorFang", "Shark", "Stag", "Kraken",
    "Phoenix", "Lava Dragon", "El Maja", "King Snake", "Yeti",
    "Burrowing Owl", "Raccoon", "Fox", "Chicken", "Dog", "Bird"
}

-- Función para deducir el nombre limpio de la mascota a partir de un texto u objeto
local function extractPetName(rawText)
    if not rawText or type(rawText) ~= "string" then return nil end
    local clean = string.gsub(rawText, " Egg", "")
    clean = string.gsub(clean, "Egg", "")
    clean = string.gsub(clean, " Huevo", "")
    clean = string.gsub(clean, "Huevo", "")
    clean = string.gsub(clean, "^%s*(.-)%s*$", "%1") -- trim

    for _, pet in ipairs(KNOWN_PETS) do
        if string.find(string.lower(rawText), string.lower(pet)) or string.find(string.lower(clean), string.lower(pet)) then
            return pet
        end
    end
    if #clean > 2 and clean ~= "Model" and clean ~= "Part" and clean ~= "MeshPart" and clean ~= "Spawn" then
        return clean
    end
    return nil
end

-- Función para escanear todos los huevos activos en el Workspace
local function scanEggs()
    local detectedEggs = {}
    local seenKeys = {}
    
    -- Busca todos los modelos y partes en el mapa que contengan información de huevos
    for _, obj in ipairs(Workspace:GetDescendants()) do
        local nameLower = string.lower(obj.Name)
        
        -- Si el objeto parece ser un huevo, nido o contiene BillboardGui
        if string.find(nameLower, "egg") or string.find(nameLower, "huevo") or obj:FindFirstChild("BillboardGui") or obj:FindFirstChildWhichIsA("BillboardGui") then
            local petName = extractPetName(obj.Name)
            local scale = 1.0
            local area = "Zona Principal"
            local mutations = {}
            local claimed = false
            local parasite = false
            
            -- 1. Leer atributos de Roblox
            local attrs = obj:GetAttributes()
            if attrs then
                for k, v in pairs(attrs) do
                    local kl = string.lower(k)
                    if string.find(kl, "pet") or string.find(kl, "animal") or string.find(kl, "name") then
                        petName = extractPetName(tostring(v)) or petName
                    elseif string.find(kl, "scale") or string.find(kl, "mult") or string.find(kl, "multiplier") or string.find(kl, "size") then
                        scale = tonumber(v) or scale
                    elseif string.find(kl, "area") or string.find(kl, "zone") or string.find(kl, "biome") then
                        area = tostring(v)
                    elseif string.find(kl, "claim") or string.find(kl, "rob") or string.find(kl, "taken") or string.find(kl, "stolen") then
                        claimed = (v == true)
                    elseif string.find(kl, "parasite") then
                        parasite = (v == true)
                    end
                end
            end
            
            -- 2. Leer texto de BillboardGui o SurfaceGui (etiquetas flotantes sobre el huevo)
            for _, gui in ipairs(obj:GetDescendants()) do
                if gui:IsA("TextLabel") or gui:IsA("TextButton") then
                    local text = gui.Text
                    if text and #text > 0 then
                        -- Buscar multiplicador (ej: "x14.8" o "14.8x")
                        local multMatch = string.match(text, "x?([%d%.]+)x?")
                        if multMatch and tonumber(multMatch) and tonumber(multMatch) > 1 then
                            scale = tonumber(multMatch)
                        end
                        
                        -- Extraer nombre de mascota si aún no se tiene
                        if not petName then
                            petName = extractPetName(text)
                        end
                        
                        -- Buscar mutaciones en texto
                        local tl = string.lower(text)
                        if string.find(tl, "rainbow") or string.find(tl, "arcoiris") then table.insert(mutations, "Rainbow") end
                        if string.find(tl, "gold") or string.find(tl, "dorado") then table.insert(mutations, "Golden") end
                        if string.find(tl, "silver") or string.find(tl, "plata") then table.insert(mutations, "Silver") end
                        if string.find(tl, "bloom") then table.insert(mutations, "Bloom") end
                        if string.find(tl, "fractured") or string.find(tl, "scrambled") then table.insert(mutations, "Fractured") end
                        if string.find(tl, "monstrous") or string.find(tl, "big") or string.find(tl, "gigante") then table.insert(mutations, "Monstrous") end
                        if string.find(tl, "parasite") or string.find(tl, "parasito") then parasite = true end
                        if string.find(tl, "robado") or string.find(tl, "claimed") or string.find(tl, "taken") then claimed = true end
                    end
                end
            end
            
            -- Evitar duplicados del mismo objeto
            local eggKey = tostring(petName or "Egg") .. "|" .. tostring(scale) .. "|" .. tostring(area)
            if (petName or scale > 1.2) and not seenKeys[eggKey] then
                seenKeys[eggKey] = true
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
    
    return detectedEggs
end

-- Función para obtener el tiempo exacto del temporizador en el juego
local function getInGameResetTime()
    local lp = Players.LocalPlayer
    
    -- 1. Buscar en PlayerGui del jugador algún TextLabel visible con contador MM:SS
    if lp and lp:FindFirstChild("PlayerGui") then
        for _, gui in ipairs(lp.PlayerGui:GetDescendants()) do
            if gui:IsA("TextLabel") and gui.Visible then
                local text = gui.Text
                if text and #text > 0 then
                    local m, s = string.match(text, "(%d%d?):(%d%d)")
                    if m and s then
                        local minVal = tonumber(m)
                        local secVal = tonumber(s)
                        if minVal and secVal and minVal < 60 and secVal < 60 then
                            local totalSec = (minVal * 60) + secVal
                            if totalSec <= 300 then
                                return totalSec
                            end
                        end
                    end
                end
            end
        end
    end
    
    -- 2. Buscar en Workspace por textos de cuenta regresiva de huevos
    for _, obj in ipairs(Workspace:GetDescendants()) do
        if obj:IsA("TextLabel") then
            local text = obj.Text
            if text and (string.find(string.lower(text), "reset") or string.find(string.lower(text), "egg")) then
                local m, s = string.match(text, "(%d%d?):(%d%d)")
                if m and s then
                    local totalSec = (tonumber(m) * 60) + tonumber(s)
                    if totalSec <= 300 then
                        return totalSec
                    end
                end
            end
        end
    end
    
    -- 3. Fallback sincronizado matemáticamente con el epoch universal de Roblox
    local now = os.time()
    local resetIn = 300 - (now % 300)
    return resetIn
end

-- Función para enviar el reporte HTTP a la web
local function reportToServer()
    local eggs = scanEggs()
    local playerCount = #Players:GetPlayers()
    local maxPlayers = Players.MaxPlayers or 12
    local inGameReset = getInGameResetTime()
    
    local payload = {
        jobId = game.JobId,
        placeId = game.PlaceId,
        players = playerCount,
        maxPlayers = maxPlayers,
        reset_in = inGameReset,
        game_time = os.time(),
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
    
    if not (success and response and response.StatusCode == 200) and FALLBACK_URL then
        -- Intentar fallback a Render
        pcall(function()
            response = requestFn({
                Url = FALLBACK_URL,
                Method = "POST",
                Headers = {
                    ["Content-Type"] = "application/json"
                },
                Body = jsonBody
            })
        end)
    end

    if response and (response.StatusCode == 200 or response.StatusCode == 201) then
        print("[HuevosToons] ✅ ¡" .. #eggs .. " huevos sincronizados con el radar web!")
    else
        warn("[HuevosToons] ⚠️ Estado de reporte: " .. tostring(response and response.StatusCode or "Desconectado"))
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

-- Bucle principal de escaneo continuo en el servidor actual
task.spawn(function()
    while true do
        task.wait(SCAN_INTERVAL)
        reportToServer()
        
        if AUTO_SERVER_HOP then
            task.wait(3)
            serverHop()
            break
        end
    end
end)

-- Escuchar en tiempo real cuando un nuevo huevo aparece en Workspace
Workspace.DescendantAdded:Connect(function(descendant)
    local nameLower = string.lower(descendant.Name)
    if string.find(nameLower, "egg") or string.find(nameLower, "huevo") then
        task.wait(0.6) -- Breve espera a que carguen los TextLabels y atributos
        reportToServer()
    end
end)

