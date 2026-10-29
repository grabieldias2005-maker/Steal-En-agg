--[[
    ===================================================================
    STEAL AN EGG TRACKER - LOADER
    ===================================================================
    Copia y pega este código en tu ejecutor (Delta, Fluxus, Solara, Wave, Codex, Arceus X, etc.)
    o ejecútalo mediante loadstring remoto.
]]

-- Configuración personalizada (modifica según tus necesidades)
getgenv().EggTrackerConfig = {
    -- URL de tu backend (por defecto localhost:3000 o tu servidor VPS / ngrok)
    BACKEND_URL = (getgenv().EggTrackerConfig and getgenv().EggTrackerConfig.BACKEND_URL) or "http://localhost:3000",
    MIN_REPORT_RARITY = (getgenv().EggTrackerConfig and getgenv().EggTrackerConfig.MIN_REPORT_RARITY) or "Rare",
    REPORT_COOLDOWN = 3
}

-- Función auxiliar para obtener scripts remotos de forma segura
local function fetchAndRun(url)
    local ok, content = pcall(function()
        return game:HttpGet(url)
    end)
    if not ok or not content or #content == 0 then
        return false, "No se pudo descargar el script desde: " .. tostring(url)
    end
    local execOk, execErr = pcall(function()
        local func = loadstring(content)
        if func then
            func()
        else
            error("Error al compilar el script con loadstring")
        end
    end)
    if not execOk then
        return false, "Error durante la ejecución: " .. tostring(execErr)
    end
    return true, nil
end

-- 1. Intentar cargar directamente desde el backend local o remoto configurado
local backendScriptUrl = getgenv().EggTrackerConfig.BACKEND_URL .. "/script"
local okBackend, errBackend = fetchAndRun(backendScriptUrl)

if okBackend then
    print("[Loader] Steal An Egg Tracker cargado exitosamente desde el backend.")
else
    -- 2. Fallback a GitHub Raw si el backend no sirve el script directamente
    -- NOTA: Reemplaza TU_USUARIO y TU_REPO con tu repositorio si lo tienes en GitHub
    local githubRawUrl = "https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/Client/StandaloneScript.luau"
    local okGit, errGit = fetchAndRun(githubRawUrl)
    if not okGit then
        warn("[Loader] No se pudo cargar el script:")
        warn(" -> Desde Backend: " .. tostring(errBackend))
        warn(" -> Desde GitHub Fallback: " .. tostring(errGit))
        warn("[Loader] Asegúrate de que el backend esté corriendo o copia directamente el contenido de StandaloneScript.luau.")
    end
end
