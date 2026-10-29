--!strict
--[[
    NetworkManager.luau
    Módulo para comunicación HTTP bidireccional entre el cliente y el backend.
    Soporta ejecutores (request, http_request, syn.request, fluxus.request)
    y Roblox HttpService nativo como fallback.
]]

local HttpService = game:GetService("HttpService")

local Config
local success, result = pcall(function()
    return require(script.Parent.Config)
end)
if success and result then
    Config = result
else
    Config = {
        BACKEND_URL = "http://localhost:3000",
        ENDPOINTS = { REPORT = "/api/eggs/report", SEARCH = "/api/eggs/search" },
        NETWORK = { REPORT_COOLDOWN = 3, REQUEST_TIMEOUT = 10 }
    }
end

local NetworkManager = {}
local pendingBatch: { any } = {}
local isFlushing = false
local lastReportTime = 0

-- Detección de la función de HTTP disponible en el entorno
local function getHttpRequestFunction(): (any) -> any
    local env = getfenv()
    local customRequest = env.request or env.http_request or (env.syn and env.syn.request) or (env.fluxus and env.fluxus.request)
    if customRequest then
        return customRequest
    end

    -- Fallback nativo de HttpService (Studio o juegos con HttpEnabled activado)
    return function(options: { Url: string, Method: string, Headers: any, Body: string? })
        local response = HttpService:RequestAsync({
            Url = options.Url,
            Method = options.Method or "GET",
            Headers = options.Headers or {},
            Body = options.Body
        })
        return {
            StatusCode = response.StatusCode,
            Success = response.Success,
            Body = response.Body
        }
    end
end

local performRequest = getHttpRequestFunction()

--[[
    Envía una petición HTTP de forma segura envuelta en un pcall asíncrono.
]]
function NetworkManager.Request(url: string, method: string, bodyData: any?): (boolean, any)
    local headers = {
        ["Content-Type"] = "application/json"
    }

    local payloadBody = nil
    if bodyData ~= nil then
        if type(bodyData) == "string" then
            payloadBody = bodyData
        else
            payloadBody = HttpService:JSONEncode(bodyData)
        end
    end

    local ok, res = pcall(function()
        return performRequest({
            Url = url,
            Method = method,
            Headers = headers,
            Body = payloadBody
        })
    end)

    if not ok then
        return false, tostring(res)
    end

    local statusCode = res.StatusCode or res.status or 0
    if statusCode >= 200 and statusCode < 300 then
        local decodeOk, decoded = pcall(function()
            return HttpService:JSONDecode(res.Body or res.body)
        end)
        return true, decodeOk and decoded or res.Body
    else
        return false, string.format("HTTP Error %d: %s", statusCode, tostring(res.Body or res.body))
    end
end

--[[
    Agrega un huevo a la cola de envío en batch y programa el envío respetando el cooldown.
]]
function NetworkManager.QueueEgg(eggData: any)
    -- Crear una copia serializable (evitando instancias de Roblox para JSON)
    local cleanData = {
        id = eggData.id,
        name = eggData.name,
        rarity = eggData.rarity,
        value = eggData.value,
        spawnTime = eggData.spawnTime
    }

    table.insert(pendingBatch, cleanData)

    if not isFlushing then
        isFlushing = true
        task.delay(Config.NETWORK.REPORT_COOLDOWN, function()
            NetworkManager.FlushQueue()
        end)
    end
end

--[[
    Envía todos los huevos acumulados en la cola en un único payload JSON al backend.
]]
function NetworkManager.FlushQueue()
    isFlushing = false
    if #pendingBatch == 0 then return end

    local now = os.time()
    if now - lastReportTime < Config.NETWORK.REPORT_COOLDOWN then
        task.wait(Config.NETWORK.REPORT_COOLDOWN - (now - lastReportTime))
    end
    lastReportTime = os.time()

    local eggsToSend = pendingBatch
    pendingBatch = {}

    local serverRegion = "Unknown"
    pcall(function()
        serverRegion = (game :: any).ServerRegion or "Global"
    end)

    local payload = {
        placeId = game.PlaceId,
        jobId = game.JobId ~= "" and game.JobId or "standalone-test-job-id",
        serverRegion = serverRegion,
        reportTimestamp = os.time(),
        eggs = eggsToSend
    }

    local targetUrl = Config.BACKEND_URL .. Config.ENDPOINTS.REPORT
    task.spawn(function()
        local successReq, response = NetworkManager.Request(targetUrl, "POST", payload)
        if successReq then
            print(string.format("[NetworkManager] Telemetría enviada: %d huevos reportados al backend.", #eggsToSend))
        else
            warn(string.format("[NetworkManager] Error enviando telemetría: %s", tostring(response)))
        end
    end)
end

--[[
    Consulta los servidores activos en el backend con filtro opcional de rareza.
]]
function NetworkManager.FetchServers(minRarity: string?, limit: number?): (boolean, any)
    local queryRarity = minRarity or "Rare"
    local queryLimit = limit or 25
    local targetUrl = string.format("%s%s?minRarity=%s&limit=%d",
        Config.BACKEND_URL,
        Config.ENDPOINTS.SEARCH,
        queryRarity,
        queryLimit
    )

    return NetworkManager.Request(targetUrl, "GET", nil)
end

return NetworkManager

