"""
Steal An Egg Tracker - Backend en Python (FastAPI + Redis)
Permite recibir reportes de servidores de Roblox y responder a consultas de huevos filtrados.
"""

import os
import time
import json
import re
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Steal An Egg Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/script", response_class=PlainTextResponse)
@app.get("/loadstring", response_class=PlainTextResponse)
def get_loadstring_script(request: Request):
    """Devuelve StandaloneScript.luau listo para loadstring con la URL del servidor inyectada."""
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Client", "StandaloneScript.luau"))
    if not os.path.exists(script_path):
        return PlainTextResponse("-- Error: StandaloneScript.luau no encontrado", status_code=404)
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    base_url = str(request.base_url).rstrip("/")
    content = re.sub(
        r'BACKEND_URL\s*=\s*userConfig\.BACKEND_URL\s*or\s*"[^"]*"',
        f'BACKEND_URL = userConfig.BACKEND_URL or "{base_url}"',
        content
    )
    return PlainTextResponse(content)

SERVER_TTL = int(os.getenv("SERVER_TTL", "180"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Rango de rarezas
RARITY_THRESHOLDS = {
    "Common": 0,
    "Uncommon": 100,
    "Rare": 500,
    "Epic": 2000,
    "Legendary": 10000,
    "Mythic": 50000,
    "Secret": 250000
}

# Fallback en memoria si Redis no está instalado o activo
memory_db = {}

# Modelos Pydantic
class EggItem(BaseModel):
    id: Optional[str] = None
    name: str
    rarity: str
    value: float
    spawnTime: Optional[int] = None

class ReportPayload(BaseModel):
    placeId: int
    jobId: str
    serverRegion: Optional[str] = "Global"
    reportTimestamp: Optional[int] = None
    eggs: List[EggItem]

@app.post("/api/eggs/report")
def report_eggs(payload: ReportPayload):
    now = time.time()
    highest_value = 0.0
    best_egg_name = "Unknown Egg"

    for egg in payload.eggs:
        if egg.value >= highest_value:
            highest_value = egg.value
            best_egg_name = egg.name

    server_entry = {
        "placeId": payload.placeId,
        "jobId": payload.jobId,
        "region": payload.serverRegion,
        "reportTimestamp": payload.reportTimestamp or int(now),
        "expiresAt": now + SERVER_TTL,
        "highestValue": highest_value,
        "bestEggName": best_egg_name,
        "eggCount": len(payload.eggs)
    }

    memory_db[f"server:{payload.jobId}"] = server_entry
    return {"status": "ok", "highestValue": highest_value, "trackedEggs": len(payload.eggs)}

@app.get("/api/eggs/search")
def search_servers(minRarity: str = Query("Rare"), limit: int = Query(20)):
    now = time.time()
    threshold = RARITY_THRESHOLDS.get(minRarity, 500)
    results = []

    # Limpieza de expirados y filtrado
    expired_keys = []
    for key, data in memory_db.items():
        if data["expiresAt"] <= now:
            expired_keys.append(key)
            continue
        
        if data["highestValue"] >= threshold:
            results.append({
                "jobId": data["jobId"],
                "placeId": data["placeId"],
                "region": data["region"],
                "highestValue": data["highestValue"],
                "bestEggName": data["bestEggName"],
                "eggCount": data["eggCount"],
                "lastReportTime": data["reportTimestamp"],
                "timeLeft": int(data["expiresAt"] - now)
            })

    for exp in expired_keys:
        memory_db.pop(exp, None)

    results.sort(key=lambda s: s["highestValue"], reverse=True)
    return results[:limit]

@app.get("/api/eggs/health")
def health_check():
    return {"status": "online", "activeServers": len(memory_db)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)

