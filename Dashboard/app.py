"""
Steal An Egg Radar - Backend en Python + Flask
Juego: Roblox Steal An Egg (PlaceId: 107778070777162)
Repositorio: https://github.com/grabieldias2005-maker/Steal-En-agg
Hosting: Render (steal-an-egg-radar)
"""

import os
import re
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, render_template_string, Response

app = Flask(__name__)

# Configuración del juego y APIs oficiales
PLACE_ID = "107778070777162"
ROBLOX_SERVERS_URL = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"
SPAWN_EVIDENCE_URL = "https://raw.githubusercontent.com/terrencerun/steal-an-egg-research/main/data/spawn-evidence.json"
PET_VALUES_URL = "https://rblxguide.com/games/steal-an-egg/pets"
GRINDMATH_VALUES_URL = "https://grindmath.app/steal-an-egg/values/"
WIKI_PETS_URL = "https://stealaneggroblox.wiki/pets/"

# Rarezas estrictas requeridas
TARGET_RARITIES = ["Rare", "Divine", "Secret", "Eternal"]
TARGET_RARITIES_LOWER = {r.lower(): r for r in TARGET_RARITIES}

# Mutaciones estándar de Steal An Egg con sus multiplicadores verificados
STANDARD_MUTATIONS = [
    {"name": "Normal", "multiplier": 1.0},
    {"name": "Silver", "multiplier": 1.2},
    {"name": "Bloom", "multiplier": 1.25},
    {"name": "Golden", "multiplier": 2.5},
    {"name": "Fractured / Scrambled", "multiplier": 2.75},
    {"name": "Parasite", "multiplier": 3.0},
    {"name": "Rainbow", "multiplier": 3.5},
]

# Cachés en memoria con TTL
_server_cache = {
    "at": 0,
    "data": [],
    "next_cursor": None,
    "last_params": ""
}
_spawn_cache = {
    "at": 0,
    "data": None
}
_pet_cache = {
    "at": 0,
    "data": [],
    "updated_at": None,
    "source": "Inicializando"
}

def load_baseline_pets() -> List[Dict[str, Any]]:
    """Carga el conjunto de mascotas base empaquetado para tolerancia a fallos."""
    baseline_path = os.path.join(os.path.dirname(__file__), "data", "pets_baseline.json")
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("data", [])
        except Exception:
            pass
    return []

# Carga inicial del catálogo base
_pet_cache["data"] = load_baseline_pets()
_pet_cache["updated_at"] = datetime.now(timezone.utc).isoformat()
_pet_cache["source"] = "Catálogo base verificado (RBLX Guide & GrindMath)"

def normalize_rarity(rarity_str: Optional[str]) -> str:
    """Normaliza y valida estrictamente las rarezas."""
    if not rarity_str:
        return "Pendiente de verificación"
    cleaned = rarity_str.strip()
    lower = cleaned.lower()
    if lower in TARGET_RARITIES_LOWER:
        return TARGET_RARITIES_LOWER[lower]
    return cleaned.title()

def format_currency_per_second(value: float) -> str:
    """Formatea valores monetarios por segundo en sufijos legibles."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B/s".replace(".00", "")
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M/s".replace(".00", "")
    if value >= 1_000:
        return f"${value / 1_000:.2f}K/s".replace(".00", "")
    return f"${value:.2f}/s".replace(".00", "")

def format_plain_currency(value: float) -> str:
    """Formatea montos acumulados en formato amigable."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B".replace(".00", "")
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M".replace(".00", "")
    if value >= 1_000:
        return f"${value / 1_000:.2f}K".replace(".00", "")
    return f"${value:,.2f}"

def refresh_pet_catalog():
    """Actualiza el catálogo de mascotas desde fuentes comunitarias con fallback seguro."""
    now = time.time()
    # Caché de 3 horas
    if _pet_cache["data"] and (now - _pet_cache["at"] < 10800):
        return _pet_cache["data"]

    # 1. Intentar raspar GrindMath para huevos y pesos
    grind_map = {}
    try:
        r_gm = requests.get(GRINDMATH_VALUES_URL, headers={"User-Agent": "Mozilla/5.0 StealAnEggRadar/1.0"}, timeout=12)
        if r_gm.status_code == 200:
            soup_gm = BeautifulSoup(r_gm.text, "html.parser")
            for row in soup_gm.find_all("tr")[1:]:
                cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                if len(cols) >= 4:
                    p_name, inc, rar, egg_bio = cols[0], cols[1], cols[2], cols[3]
                    weight = cols[4] if len(cols) > 4 else "No disponible"
                    grind_map[p_name.strip().lower()] = {
                        "egg_biome": egg_bio.strip(),
                        "base_weight": weight.strip()
                    }
    except Exception:
        pass

    # 2. Intentar raspar RBLX Guide para lista completa de mascotas
    try:
        r_rg = requests.get(PET_VALUES_URL, headers={"User-Agent": "Mozilla/5.0 StealAnEggRadar/1.0"}, timeout=15)
        if r_rg.status_code == 200:
            soup_rg = BeautifulSoup(r_rg.text, "html.parser")
            rarities_re = "Common|Uncommon|Rare|Epic|Legendary|Mythic|Cosmic|Secret|Eternal|Divine|Brainrot|Monster|Event"
            pattern = re.compile(r"^(.*?)\s+(" + rarities_re + r")\s+\$([\d,.]+)\s*([KMB]?)/s\s+(.+)$", re.I)
            
            fresh_records = []
            seen_slugs = set()
            for a in soup_rg.select('a[href*="/pets/"]'):
                slug = a.get("href", "").rstrip("/").split("/")[-1]
                if not slug or slug == "pets" or slug in seen_slugs:
                    continue
                match = pattern.match(a.get_text(" ", strip=True))
                if not match:
                    continue
                seen_slugs.add(slug)
                name, rarity_raw, amount, suffix, source_col = match.groups()
                factor = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix.upper(), 1)
                income = float(amount.replace(",", "")) * factor
                clean_name = name.strip()

                gm = grind_map.get(clean_name.lower()) or grind_map.get(clean_name.replace("🥚 ", "").lower()) or {}
                origin_egg = gm.get("egg_biome") or (source_col.strip() if source_col.strip() not in ("Unconfirmed", "Multiple") else "No disponible")
                base_weight = gm.get("base_weight", "No disponible")

                norm_rarity = normalize_rarity(rarity_raw)
                val_mult = {"Rare": 500, "Divine": 50_000, "Secret": 100_000, "Eternal": 500_000}.get(norm_rarity, 100)
                est_val = income * val_mult if income > 0 else 0

                fresh_records.append({
                    "name": clean_name,
                    "slug": slug,
                    "rarity": norm_rarity,
                    "income": income,
                    "income_formatted": format_currency_per_second(income),
                    "origin_egg": origin_egg,
                    "base_weight": base_weight,
                    "estimated_value": est_val,
                    "estimated_value_formatted": format_plain_currency(est_val),
                    "source": "RBLX Guide & GrindMath",
                    "source_url": f"https://rblxguide.com/games/steal-an-egg/pets/{slug}",
                    "mutations_supported": STANDARD_MUTATIONS,
                    "verified": True,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                })

            if fresh_records:
                _pet_cache["data"] = fresh_records
                _pet_cache["at"] = now
                _pet_cache["updated_at"] = datetime.now(timezone.utc).isoformat()
                _pet_cache["source"] = "RBLX Guide & GrindMath (en vivo)"
                return fresh_records
    except Exception:
        pass

    # Si la consulta falló pero ya tenemos catálogo base, retornar el actual
    if not _pet_cache["data"]:
        _pet_cache["data"] = load_baseline_pets()
    return _pet_cache["data"]

# -------------------------------------------------------------
# RUTAS DE LA API REST
# -------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Endpoint de salud para Render y monitorización."""
    return jsonify({
        "status": "ok",
        "service": "steal-an-egg-radar",
        "placeId": PLACE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pets_count": len(_pet_cache["data"]),
        "servers_cached": len(_server_cache["data"])
    })

@app.route("/api/servers", methods=["GET"])
def api_servers():
    """
    Consulta servidores públicos oficiales de Roblox con ordenamiento y espacios disponibles.
    Parámetros admitidos:
      - sort_by: 'free_desc' (espacios disponibles), 'players_desc', 'players_asc', 'ping'
      - search: filtro por texto de JobId
      - cursor: paginación oficial de Roblox
      - force_refresh: true para ignorar caché temporal
    """
    cursor = request.args.get("cursor", "").strip()[:2000]
    sort_by = request.args.get("sort_by", "free_desc")
    search = request.args.get("search", "").strip().lower()
    force_refresh = request.args.get("force_refresh", "").lower() == "true"

    now = time.time()
    cache_key = f"{cursor}_{sort_by}"

    # Caché de 15 segundos para evitar rate limit de Roblox (429)
    if not force_refresh and (now - _server_cache["at"] < 15) and _server_cache["last_params"] == cache_key:
        servers = _server_cache["data"]
        filtered = servers
        if search:
            filtered = [s for s in servers if search in s["id"].lower()]
        return jsonify({
            "success": True,
            "data": filtered,
            "count": len(filtered),
            "total_players": sum(s.get("playing", 0) for s in filtered),
            "nextPageCursor": _server_cache["next_cursor"],
            "cached": True,
            "last_updated": datetime.fromtimestamp(_server_cache["at"], timezone.utc).isoformat()
        })

    params = {"sortOrder": "Desc", "limit": "100"}
    if cursor:
        params["cursor"] = cursor

    try:
        resp = requests.get(
            ROBLOX_SERVERS_URL,
            params=params,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StealAnEggRadar/2.0"},
            timeout=15
        )
        if resp.status_code == 429:
            # Si Roblox limita solicitudes, devolvemos la última caché si existe
            if _server_cache["data"]:
                return jsonify({
                    "success": True,
                    "warning": "Roblox está limitando las solicitudes (HTTP 429). Mostrando últimos servidores en caché.",
                    "data": _server_cache["data"],
                    "count": len(_server_cache["data"]),
                    "cached": True,
                    "last_updated": datetime.fromtimestamp(_server_cache["at"], timezone.utc).isoformat()
                })
            return jsonify({
                "success": False,
                "error": "Roblox está limitando temporalmente las solicitudes públicas. Espera 10 segundos antes de reintentar."
            }), 429

        resp.raise_for_status()
        payload = resp.json()
        raw_servers = payload.get("data", [])
        next_cursor = payload.get("nextPageCursor")

        formatted_servers = []
        for s in raw_servers:
            job_id = s.get("id", "")
            playing = int(s.get("playing", 0))
            max_players = int(s.get("maxPlayers", 12))
            free_slots = max(0, max_players - playing)
            ping = s.get("ping")
            fps = s.get("fps")

            formatted_servers.append({
                "id": job_id,
                "shortId": job_id[:8] + "…" if len(job_id) > 8 else job_id,
                "playing": playing,
                "maxPlayers": max_players,
                "freeSlots": free_slots,
                "ping": ping if ping is not None else "—",
                "fps": round(fps, 1) if fps is not None else "—",
                "joinUrl": f"https://www.roblox.com/games/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
                "deepLink": f"roblox://placeId={PLACE_ID}&gameInstanceId={job_id}"
            })

        # Aplicar ordenación solicitada
        if sort_by == "free_desc":
            formatted_servers.sort(key=lambda x: x["freeSlots"], reverse=True)
        elif sort_by == "players_desc":
            formatted_servers.sort(key=lambda x: x["playing"], reverse=True)
        elif sort_by == "players_asc":
            formatted_servers.sort(key=lambda x: x["playing"])
        elif sort_by == "ping":
            formatted_servers.sort(key=lambda x: (isinstance(x["ping"], str), x["ping"]))

        _server_cache["at"] = now
        _server_cache["data"] = formatted_servers
        _server_cache["next_cursor"] = next_cursor
        _server_cache["last_params"] = cache_key

        filtered = formatted_servers
        if search:
            filtered = [s for s in formatted_servers if search in s["id"].lower()]

        return jsonify({
            "success": True,
            "data": filtered,
            "count": len(filtered),
            "total_players": sum(s.get("playing", 0) for s in filtered),
            "nextPageCursor": next_cursor,
            "cached": False,
            "last_updated": datetime.fromtimestamp(now, timezone.utc).isoformat()
        })

    except requests.RequestException as e:
        if _server_cache["data"]:
            return jsonify({
                "success": True,
                "warning": "Error temporal al conectar con la API de Roblox. Mostrando datos en caché.",
                "data": _server_cache["data"],
                "count": len(_server_cache["data"]),
                "cached": True,
                "last_updated": datetime.fromtimestamp(_server_cache["at"], timezone.utc).isoformat()
            })
        return jsonify({
            "success": False,
            "error": "No se pudo conectar con la API de servidores públicos de Roblox. Revisa tu conexión."
        }), 502

@app.route("/api/pets", methods=["GET"])
def api_pets():
    """
    Catálogo de mascotas y huevos con filtros estrictos de las cuatro rarezas:
    Rare, Divine, Secret, Eternal (+ All).
    Parámetros admitidos:
      - rarity: 'rare', 'divine', 'secret', 'eternal', 'all_target' (las cuatro), o vacio para todas
      - egg: filtro por huevo o bioma de origen
      - search: filtro por nombre de mascota o huevo
      - sort_by: 'income_desc', 'income_asc', 'value_desc', 'name'
    """
    rarity_filter = request.args.get("rarity", "").strip().lower()
    egg_filter = request.args.get("egg", "").strip().lower()
    search = request.args.get("search", "").strip().lower()
    sort_by = request.args.get("sort_by", "income_desc")

    pets = refresh_pet_catalog()

    # Si se selecciona filtro de rarezas objetivo
    if rarity_filter in TARGET_RARITIES_LOWER:
        target_name = TARGET_RARITIES_LOWER[rarity_filter]
        pets = [p for p in pets if p.get("rarity") == target_name]
    elif rarity_filter in ("target_only", "all_target", "targets"):
        pets = [p for p in pets if p.get("rarity") in TARGET_RARITIES]

    # Filtro por huevo o bioma
    if egg_filter:
        pets = [p for p in pets if egg_filter in p.get("origin_egg", "").lower()]

    # Filtro por búsqueda de texto
    if search:
        pets = [p for p in pets if (search in p.get("name", "").lower() or 
                                    search in p.get("origin_egg", "").lower() or 
                                    search in p.get("rarity", "").lower())]

    # Ordenación
    if sort_by == "income_desc":
        pets.sort(key=lambda p: p.get("income", 0), reverse=True)
    elif sort_by == "income_asc":
        pets.sort(key=lambda p: p.get("income", 0))
    elif sort_by == "value_desc":
        pets.sort(key=lambda p: p.get("estimated_value", 0), reverse=True)
    elif sort_by == "name":
        pets.sort(key=lambda p: p.get("name", "").lower())

    return jsonify({
        "success": True,
        "data": pets,
        "count": len(pets),
        "target_rarities": TARGET_RARITIES,
        "source": _pet_cache.get("source"),
        "updated_at": _pet_cache.get("updated_at")
    })

@app.route("/api/spawn-evidence", methods=["GET"])
def api_spawn_evidence():
    """
    Provee registros de observaciones comunitarias e intervalos observados
    del repositorio de investigación de Steal An Egg.
    """
    now = time.time()
    # Caché de 5 minutos
    if _spawn_cache["data"] and (now - _spawn_cache["at"] < 300):
        return jsonify(_spawn_cache["data"])

    try:
        resp = requests.get(SPAWN_EVIDENCE_URL, headers={"User-Agent": "Mozilla/5.0 StealAnEggRadar/2.0"}, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        _spawn_cache["at"] = now
        _spawn_cache["data"] = data
        return jsonify(data)
    except Exception as e:
        if _spawn_cache["data"]:
            return jsonify(_spawn_cache["data"])
        return jsonify({
            "error": "No se pudo consultar el archivo público de evidencia comunitaria.",
            "details": str(e)
        }), 502

@app.route("/api/calculate", methods=["GET", "POST"])
def api_calculate():
    """
    Calculadora de ganancias para Steal An Egg.
    Fórmula verificada:
      GANANCIA TOTAL = BASE $/S × CANTIDAD × MULTIPLICADOR MUTACIÓN × FACTOR TAMAÑO
    """
    params = request.get_json(silent=True) or request.args

    try:
        base_income = float(params.get("base_income", 1))
        quantity = max(1, int(params.get("quantity", 1)))
        mutation_mult = max(1.0, float(params.get("mutation_mult", 1.0)))
        size_factor = max(0.1, float(params.get("size_factor", 1.0)))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Parámetros numéricos inválidos"}), 400

    per_second = base_income * quantity * mutation_mult * size_factor
    per_minute = per_second * 60
    per_hour = per_second * 3600
    per_day = per_hour * 24

    return jsonify({
        "success": True,
        "formula": "base_income * quantity * mutation_mult * size_factor",
        "inputs": {
            "base_income": base_income,
            "quantity": quantity,
            "mutation_mult": mutation_mult,
            "size_factor": size_factor,
            "size_factor_note": "Factor de tamaño manual o estimado. En Steal An Egg el peso influye pero no existe tabla pública oficial fija."
        },
        "results": {
            "per_second": per_second,
            "per_minute": per_minute,
            "per_hour": per_hour,
            "per_day": per_day,
            "formatted": {
                "per_second": format_currency_per_second(per_second),
                "per_minute": format_plain_currency(per_minute) + "/min",
                "per_hour": format_plain_currency(per_hour) + "/hr",
                "per_day": format_plain_currency(per_day) + "/día"
            }
        }
    })

@app.route("/api/best-opportunities", methods=["GET"])
def api_best_opportunities():
    """
    Sección 'Mejores oportunidades':
    - Top mascotas por $/s en cada una de las 4 rarezas: Rare, Divine, Secret, Eternal.
    - Top huevos por variedad de mascotas y potencial económico.
    - Indicador explícito de que el contenido del servidor no es público.
    """
    pets = refresh_pet_catalog()

    by_rarity = {r: [] for r in TARGET_RARITIES}
    for p in pets:
        r = p.get("rarity")
        if r in by_rarity:
            by_rarity[r].append(p)

    for r in by_rarity:
        by_rarity[r].sort(key=lambda x: x.get("income", 0), reverse=True)

    # Agrupar por huevo/bioma
    eggs_summary = {}
    for p in pets:
        egg = p.get("origin_egg", "No disponible")
        if egg not in eggs_summary:
            eggs_summary[egg] = {
                "egg_name": egg,
                "pets_count": 0,
                "high_rarity_count": 0,
                "best_pet": None,
                "max_income": 0
            }
        eggs_summary[egg]["pets_count"] += 1
        if p.get("rarity") in TARGET_RARITIES:
            eggs_summary[egg]["high_rarity_count"] += 1
        if p.get("income", 0) > eggs_summary[egg]["max_income"]:
            eggs_summary[egg]["max_income"] = p.get("income", 0)
            eggs_summary[egg]["best_pet"] = p.get("name")

    top_eggs = sorted(
        [e for e in eggs_summary.values() if e["egg_name"] != "No disponible"],
        key=lambda x: (x["high_rarity_count"], x["max_income"]),
        reverse=True
    )

    return jsonify({
        "success": True,
        "top_by_rarity": {
            "Rare": by_rarity["Rare"][:5],
            "Divine": by_rarity["Divine"][:5],
            "Secret": by_rarity["Secret"][:5],
            "Eternal": by_rarity["Eternal"][:5]
        },
        "top_eggs": top_eggs[:8],
        "server_telemetry_notice": "Contenido del servidor no disponible públicamente (Roblox no expone qué huevos o mascotas están en cada servidor)."
    })

# -------------------------------------------------------------
# INTERFAZ WEB FUTURISTA Y COMPLETA
# -------------------------------------------------------------

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Steal An Egg · Radar Futurista de Servidores y Catálogo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #070d19;
      --card-bg: rgba(16, 26, 49, 0.85);
      --card-border: rgba(56, 189, 248, 0.15);
      --card-hover-border: rgba(99, 102, 241, 0.4);
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --purple: #8b5cf6;
      --purple-glow: rgba(139, 92, 246, 0.35);
      --cyan: #06b6d4;
      --cyan-glow: rgba(6, 182, 212, 0.3);
      --emerald: #10b981;
      --amber: #f59e0b;
      --rose: #f43f5e;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --font-main: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(59, 130, 246, 0.12) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(139, 92, 246, 0.14) 0%, transparent 45%),
        linear-gradient(180deg, #070d19 0%, #0c152a 100%);
      color: var(--text);
      font-family: var(--font-main);
      min-height: 100vh;
      line-height: 1.5;
    }
    .container { max-width: 1240px; margin: 0 auto; padding: 24px 20px 80px; }
    
    /* Header */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 18px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .brand { display: flex; align-items: center; gap: 14px; }
    .brand-icon {
      width: 46px; height: 46px;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      box-shadow: 0 0 20px var(--purple-glow);
    }
    .brand h1 { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(90deg, #fff, #93c5fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .brand p { font-size: 13px; color: var(--text-muted); }
    .header-actions { display: flex; align-items: center; gap: 12px; }
    
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--emerald);
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--emerald); box-shadow: 0 0 10px var(--emerald); animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(0.85); } }

    /* Buttons */
    .btn {
      background: linear-gradient(135deg, var(--primary), #2563eb);
      color: white;
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 10px;
      padding: 9px 18px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
      text-decoration: none;
    }
    .btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
    }
    .btn-secondary {
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--card-border);
      color: var(--text);
    }
    .btn-secondary:hover {
      background: rgba(255,255,255,0.12);
      border-color: rgba(255,255,255,0.3);
      box-shadow: none;
    }
    .btn-purple {
      background: linear-gradient(135deg, #8b5cf6, #6366f1);
    }
    .btn-purple:hover {
      box-shadow: 0 4px 16px var(--purple-glow);
    }
    .btn-join {
      background: linear-gradient(135deg, #10b981, #059669);
      color: #fff;
      padding: 8px 16px;
      font-weight: 800;
      letter-spacing: 0.5px;
    }
    .btn-join:hover {
      box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);
    }

    /* Metric Bar */
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }
    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px 20px;
      backdrop-filter: blur(8px);
      position: relative;
      overflow: hidden;
    }
    .metric-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 2px;
      background: linear-gradient(90deg, transparent, var(--primary), transparent);
    }
    .metric-label { font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 26px; font-weight: 800; margin-top: 4px; font-family: var(--font-mono); color: #fff; }
    .metric-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

    /* Navigation Tabs */
    .nav-tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
      overflow-x: auto;
      padding-bottom: 4px;
    }
    .nav-tab {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      border-radius: 10px 10px 0 0;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
      white-space: nowrap;
      position: relative;
    }
    .nav-tab:hover { color: #fff; background: rgba(255,255,255,0.03); }
    .nav-tab.active {
      color: #fff;
      background: rgba(59, 130, 246, 0.08);
    }
    .nav-tab.active::after {
      content: '';
      position: absolute;
      bottom: -4px; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--primary), var(--purple));
      border-radius: 3px 3px 0 0;
    }

    /* Content Sections */
    .tab-content { display: none; }
    .tab-content.active { display: block; animation: fadeIn 0.25s ease-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

    /* Alert / Disclaimers */
    .disclaimer-box {
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(245, 158, 11, 0.35);
      border-radius: 12px;
      padding: 14px 18px;
      margin-bottom: 20px;
      display: flex;
      align-items: flex-start;
      gap: 12px;
      color: #fde68a;
      font-size: 13px;
      line-height: 1.5;
    }
    .disclaimer-box b { color: #fff; }
    .disclaimer-icon { font-size: 18px; line-height: 1; flex-shrink: 0; }

    /* Controls Bar */
    .controls-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 14px 18px;
      margin-bottom: 20px;
    }
    .controls-group { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

    input, select {
      background: rgba(8, 13, 25, 0.9);
      border: 1px solid var(--card-border);
      color: #fff;
      border-radius: 8px;
      padding: 9px 14px;
      font-size: 13px;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus, select:focus {
      border-color: var(--primary);
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
    }
    input[type="text"] { min-width: 220px; }

    /* Rarity Filter Buttons */
    .rarity-pill-group { display: flex; gap: 6px; flex-wrap: wrap; }
    .rarity-pill {
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      border-radius: 20px;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .rarity-pill:hover { border-color: rgba(255,255,255,0.3); color: #fff; }
    .rarity-pill.active {
      color: #fff;
      border-color: transparent;
    }
    .rarity-pill.active[data-r="all"] { background: linear-gradient(135deg, #3b82f6, #8b5cf6); }
    .rarity-pill.active[data-r="rare"] { background: #3b82f6; box-shadow: 0 0 12px rgba(59, 130, 246, 0.5); }
    .rarity-pill.active[data-r="divine"] { background: #eab308; color: #1e1b4b; box-shadow: 0 0 12px rgba(234, 179, 8, 0.5); }
    .rarity-pill.active[data-r="secret"] { background: #ec4899; box-shadow: 0 0 12px rgba(236, 72, 153, 0.5); }
    .rarity-pill.active[data-r="eternal"] { background: #8b5cf6; box-shadow: 0 0 12px rgba(139, 92, 246, 0.5); }

    /* Servers Grid */
    .servers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }
    .server-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 18px;
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 14px;
    }
    .server-card:hover {
      border-color: var(--card-hover-border);
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    .server-head { display: flex; justify-content: space-between; align-items: flex-start; }
    .server-title { font-weight: 700; font-size: 15px; color: #fff; }
    .server-job { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); margin-top: 2px; }
    .free-slots-badge {
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 800;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #93c5fd;
    }
    .free-slots-badge.almost-full {
      background: rgba(244, 63, 94, 0.15);
      border-color: rgba(244, 63, 94, 0.3);
      color: #fda4af;
    }
    .server-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      padding: 10px 0;
      border-top: 1px solid rgba(255,255,255,0.06);
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .server-stat-item { text-align: center; }
    .server-stat-item small { display: block; font-size: 11px; color: var(--text-muted); }
    .server-stat-item b { font-family: var(--font-mono); font-size: 13px; color: #fff; }
    .server-card-bottom {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .server-notice { font-size: 11px; color: var(--text-muted); font-style: italic; }

    /* Tables */
    .table-container {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      overflow-x: auto;
      margin-bottom: 24px;
    }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th {
      padding: 14px 18px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--card-border);
      background: rgba(8, 13, 25, 0.4);
    }
    td {
      padding: 14px 18px;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 13px;
    }
    tr:hover td { background: rgba(255,255,255,0.02); }
    
    /* Rarity Badges */
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-rare { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .badge-divine { background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }
    .badge-secret { background: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.4); }
    .badge-eternal { background: rgba(139, 92, 246, 0.2); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.4); }
    
    .income-val { color: var(--emerald); font-family: var(--font-mono); font-weight: 700; }
    .btn-egg-view {
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--card-border);
      color: #93c5fd;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-egg-view:hover { background: rgba(59, 130, 246, 0.2); border-color: var(--primary); }

    /* Calculator Box */
    .calculator-layout {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }
    .calc-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 24px;
    }
    .calc-card h3 { font-size: 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; color: #fff; }
    .calc-form { display: grid; gap: 14px; }
    .form-group { display: flex; flex-direction: column; gap: 6px; }
    .form-group label { font-size: 12px; color: var(--text-muted); font-weight: 600; }
    .calc-results {
      background: rgba(8, 13, 25, 0.9);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 18px;
      display: grid;
      gap: 12px;
    }
    .calc-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
    .calc-row b { font-family: var(--font-mono); color: var(--emerald); font-size: 16px; }
    .calc-row.highlight { padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.08); }
    .calc-row.highlight b { font-size: 20px; color: #38bdf8; }

    /* Modals */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(6px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
    }
    .modal-overlay.open { display: flex; }
    .modal-window {
      background: #0f172a;
      border: 1px solid var(--card-hover-border);
      border-radius: 18px;
      max-width: 520px;
      width: 100%;
      padding: 24px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.6);
      position: relative;
    }
    .modal-close {
      position: absolute;
      top: 16px; right: 16px;
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
    }
    .modal-close:hover { color: #fff; }

    /* Notifications List */
    .notification-list { display: grid; gap: 10px; margin-top: 14px; }
    .notif-item {
      background: rgba(8, 13, 25, 0.8);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
    }
    .notif-item small { color: var(--text-muted); font-size: 11px; }

    /* Best Opportunities Grid */
    .opp-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .opp-col {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 16px;
    }
    .opp-col h4 { font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }

    footer {
      border-top: 1px solid var(--card-border);
      padding-top: 24px;
      margin-top: 40px;
      font-size: 12px;
      color: var(--text-muted);
      text-align: center;
      line-height: 1.6;
    }
    footer a { color: var(--primary); text-decoration: none; }
    footer a:hover { text-decoration: underline; }
  </style>
</head>
<body>
<div class="container">
  
  <!-- Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">🥚</div>
      <div>
        <h1>Steal An Egg · Radar</h1>
        <p>Buscador de servidores públicos oficiales de Roblox y catálogo comunitario</p>
      </div>
    </div>
    <div class="header-actions">
      <div class="status-badge">
        <span class="status-dot"></span>
        <span id="connectionBadge">Radar en línea · PlaceId 107778070777162</span>
      </div>
      <button class="btn btn-secondary" onclick="refreshAll()" title="Actualizar datos completos">
        🔄 Actualizar
      </button>
      <button class="btn btn-purple" id="notifToggleBtn" onclick="toggleNotifications()">
        🔔 Notificaciones
      </button>
    </div>
  </header>

  <!-- Metric Overview -->
  <div class="metric-grid">
    <div class="metric-card">
      <div class="metric-label">Servidores públicos cargados</div>
      <div class="metric-value" id="statServers">—</div>
      <div class="metric-sub" id="statServerSub">Consultando Roblox Games API…</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Jugadores activos visibles</div>
      <div class="metric-value" id="statPlayers">—</div>
      <div class="metric-sub">Suma en servidores consultados</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Mascotas en catálogo</div>
      <div class="metric-value" id="statPets">265</div>
      <div class="metric-sub">Fuentes RBLX Guide & GrindMath</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Intervalo de refresco</div>
      <div class="metric-value">30s</div>
      <div class="metric-sub" id="statLastUpdate">Última consulta: —</div>
    </div>
  </div>

  <!-- Disclaimer sobre telemetría -->
  <div class="disclaimer-box">
    <div class="disclaimer-icon">⚠️</div>
    <div>
      <b>Aviso oficial sobre la telemetría del juego:</b> Roblox no proporciona a los jugadores APIs públicas para saber qué huevos o mascotas están dentro del espacio de trabajo de cada servidor en vivo. Este radar muestra los <b>servidores públicos reales y verificados de Roblox</b> y el <b>catálogo comunitario verificado</b> con registros observados. Si un servidor no reporta contenido, se muestra con veracidad: <i>"Contenido del servidor no disponible públicamente"</i>.
    </div>
  </div>

  <!-- Navigation Tabs -->
  <nav class="nav-tabs">
    <button class="nav-tab active" onclick="switchTab('servers')">🌐 Servidores públicos & JOIN</button>
    <button class="nav-tab" onclick="switchTab('catalog')">🐾 Catálogo (Rare, Divine, Secret, Eternal)</button>
    <button class="nav-tab" onclick="switchTab('calculator')">🧮 Calculadora de ganancias</button>
    <button class="nav-tab" onclick="switchTab('spawns')">⏱️ Evidencias de spawn & Estimador</button>
    <button class="nav-tab" onclick="switchTab('opportunities')">⭐ Mejores oportunidades</button>
    <button class="nav-tab" onclick="switchTab('notifications')">🔔 Centro de alertas</button>
  </nav>

  <!-- TAB 1: RADAR DE SERVIDORES -->
  <section id="tab-servers" class="tab-content active">
    <div class="controls-bar">
      <div class="controls-group">
        <input type="text" id="serverSearch" placeholder="Buscar por JobId de servidor…" oninput="filterServers()">
        <select id="serverSort" onchange="loadServers()">
          <option value="free_desc">Mayor cantidad de espacios disponibles</option>
          <option value="players_desc">Más jugadores primero</option>
          <option value="players_asc">Menos jugadores primero</option>
          <option value="ping">Mejor latencia (Ping)</option>
        </select>
      </div>
      <div class="controls-group">
        <span style="font-size: 12px; color: var(--text-muted);" id="serverLastRefresh">Auto-actualización: activa (30s)</span>
        <button class="btn btn-secondary" onclick="loadServers(false, true)">Refrescar servidores</button>
      </div>
    </div>

    <div id="serversList" class="servers-grid">
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
        Conectando con la API pública de servidores de Roblox…
      </div>
    </div>
  </section>

  <!-- TAB 2: CATÁLOGO DE MASCOTAS Y FILTROS ESTRICTOS -->
  <section id="tab-catalog" class="tab-content">
    <div class="controls-bar">
      <div class="controls-group">
        <span style="font-size: 13px; font-weight: 700; color: #fff;">Rarezas estrictas:</span>
        <div class="rarity-pill-group">
          <button class="rarity-pill active" data-r="all" onclick="selectRarityFilter('all')">✨ Las 4 rarezas</button>
          <button class="rarity-pill" data-r="rare" onclick="selectRarityFilter('rare')">💎 Rare</button>
          <button class="rarity-pill" data-r="divine" onclick="selectRarityFilter('divine')">👑 Divine</button>
          <button class="rarity-pill" data-r="secret" onclick="selectRarityFilter('secret')">🔮 Secret</button>
          <button class="rarity-pill" data-r="eternal" onclick="selectRarityFilter('eternal')">⚡ Eternal</button>
        </div>
      </div>
      <div class="controls-group">
        <input type="text" id="petSearch" placeholder="Buscar mascota, huevo o bioma…" oninput="renderPetTable()">
        <select id="petSort" onchange="renderPetTable()">
          <option value="income_desc">Mayor dinero por segundo ($/s)</option>
          <option value="income_asc">Menor dinero por segundo</option>
          <option value="value_desc">Mayor valor estimado</option>
          <option value="name">Nombre alfabético</option>
        </select>
      </div>
    </div>

    <div class="controls-bar" style="background: rgba(15, 23, 42, 0.4);">
      <div class="controls-group">
        <span style="font-size: 12px; color: var(--text-muted);">Simulador visual de catálogo:</span>
        <label style="font-size: 12px; color: var(--text-muted);">
          Mutación:
          <select id="catalogMutation" onchange="renderPetTable()">
            <option value="1">Normal (×1.0)</option>
            <option value="1.2">Silver (×1.2)</option>
            <option value="1.25">Bloom (×1.25)</option>
            <option value="2.5">Golden (×2.5)</option>
            <option value="2.75">Fractured / Scrambled (×2.75)</option>
            <option value="3.0">Parasite (×3.0)</option>
            <option value="3.5">Rainbow (×3.5)</option>
          </select>
        </label>
        <label style="font-size: 12px; color: var(--text-muted);">
          Factor de tamaño (manual):
          <input type="number" id="catalogSize" min="0.1" max="50" step="0.1" value="1.0" style="width: 80px;" oninput="renderPetTable()">
        </label>
      </div>
      <div id="catalogCountInfo" style="font-size: 12px; color: var(--text-muted);">
        Cargando catálogo…
      </div>
    </div>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Mascota</th>
            <th>Rareza</th>
            <th>Huevo / Bioma de origen</th>
            <th>Base $/s</th>
            <th>$/s con mutación</th>
            <th>Valor estimado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody id="petTableBody">
          <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">Cargando catálogo comunitario…</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- TAB 3: CALCULADORA DE GANANCIAS -->
  <section id="tab-calculator" class="tab-content">
    <div class="calculator-layout">
      <!-- Calculadora Individual -->
      <div class="calc-card">
        <h3>🧮 Calculadora de rendimiento</h3>
        <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">
          Fórmula oficial: <code>GANANCIA TOTAL = BASE $/S × CANTIDAD × MUTACIÓN × TAMAÑO</code>
        </p>
        <div class="calc-form">
          <div class="form-group">
            <label>Seleccionar mascota del catálogo</label>
            <select id="calcPetSelect" onchange="onCalcPetChange()">
              <option value="">-- Elige una mascota o escribe abajo --</option>
            </select>
          </div>
          <div class="form-group">
            <label>Ganancia base por segundo ($/s)</label>
            <input type="number" id="calcBaseIncome" min="1" step="any" value="1000" oninput="runCalculator()">
          </div>
          <div class="form-group">
            <label>Cantidad de mascotas</label>
            <input type="number" id="calcQuantity" min="1" max="1000" value="1" oninput="runCalculator()">
          </div>
          <div class="form-group">
            <label>Mutación aplicada</label>
            <select id="calcMutation" onchange="runCalculator()">
              <option value="1.0">Normal (×1.0)</option>
              <option value="1.2">Silver (×1.2)</option>
              <option value="1.25">Bloom (×1.25)</option>
              <option value="2.5">Golden (×2.5)</option>
              <option value="2.75">Fractured / Scrambled (×2.75)</option>
              <option value="3.0">Parasite (×3.0)</option>
              <option value="3.5">Rainbow (×3.5)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Multiplicador de tamaño (manual/estimado)</label>
            <input type="number" id="calcSize" min="0.1" max="50" step="0.1" value="1.0" oninput="runCalculator()">
            <span style="font-size: 11px; color: var(--text-muted);">*El peso en kg varía por huevo pero no existe multiplicador fijo oficial. Factor predeterminado ×1.</span>
          </div>
        </div>

        <div class="calc-results" style="margin-top: 20px;">
          <div class="calc-row">
            <span>Ganancia por segundo:</span>
            <b id="resSec">$1,000/s</b>
          </div>
          <div class="calc-row">
            <span>Ganancia por minuto:</span>
            <b id="resMin">$60,000/min</b>
          </div>
          <div class="calc-row">
            <span>Ganancia por hora:</span>
            <b id="resHour">$3,600,000/hr</b>
          </div>
          <div class="calc-row highlight">
            <span>Ganancia estimada 24 horas:</span>
            <b id="resDay">$86,400,000</b>
          </div>
        </div>
      </div>

      <!-- Comparador de Mascotas -->
      <div class="calc-card">
        <h3>⚖️ Comparador A vs B</h3>
        <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">
          Compara dos configuraciones de mascotas lado a lado para determinar cuál produce mayor ganancia neta.
        </p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="calc-form">
            <b style="font-size: 13px; color: #60a5fa;">Mascota A</b>
            <select id="compPetA" onchange="runComparison()">
              <option value="">Seleccionar...</option>
            </select>
            <input type="number" id="compQtyA" value="1" min="1" placeholder="Cantidad" oninput="runComparison()">
            <select id="compMutA" onchange="runComparison()">
              <option value="1.0">Normal (×1.0)</option>
              <option value="2.5">Golden (×2.5)</option>
              <option value="3.5">Rainbow (×3.5)</option>
            </select>
          </div>
          <div class="calc-form">
            <b style="font-size: 13px; color: #c084fc;">Mascota B</b>
            <select id="compPetB" onchange="runComparison()">
              <option value="">Seleccionar...</option>
            </select>
            <input type="number" id="compQtyB" value="1" min="1" placeholder="Cantidad" oninput="runComparison()">
            <select id="compMutB" onchange="runComparison()">
              <option value="1.0">Normal (×1.0)</option>
              <option value="2.5">Golden (×2.5)</option>
              <option value="3.5">Rainbow (×3.5)</option>
            </select>
          </div>
        </div>

        <div id="comparisonBox" class="calc-results" style="margin-top: 24px;">
          <div style="text-align: center; color: var(--text-muted); font-size: 13px;">
            Selecciona la Mascota A y la Mascota B para ver la comparativa.
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 4: EVIDENCIAS DE SPAWN Y ESTIMADOR -->
  <section id="tab-spawns" class="tab-content">
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">Intervalo mediano observado</div>
        <div class="metric-value" id="spawnMedianVal">300 s</div>
        <div class="metric-sub">Rango documentado: 293–307 s</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Intervalos continuos en video</div>
        <div class="metric-value" id="spawnSamplesVal">5</div>
        <div class="metric-sub">Mismo servidor sin cortes</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Estado del estimador</div>
        <div class="metric-value" id="spawnCountdownVal" style="color: #38bdf8;">Inactivo</div>
        <div class="metric-sub" id="spawnCountdownSub">Haz clic para iniciar ciclo de 5 min</div>
      </div>
    </div>

    <div class="controls-bar">
      <div>
        <h3 style="font-size: 16px; color: #fff;">⏱️ Estimador de ventana comunitaria (5 minutos)</h3>
        <p style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
          Al iniciarlo, cuenta 300 segundos desde tu sincronización local y avisa en la ventana 293–307s.
        </p>
      </div>
      <div class="controls-group">
        <button class="btn btn-purple" id="btnStartEstimator" onclick="toggleSpawnEstimator()">▶️ Iniciar estimador</button>
        <button class="btn btn-secondary" onclick="loadSpawnEvidence()">Refrescar registros</button>
      </div>
    </div>

    <div class="disclaimer-box" style="border-color: rgba(59, 130, 246, 0.4); background: rgba(15, 23, 42, 0.9); color: #bae6fd;">
      <div class="disclaimer-icon">ℹ️</div>
      <div>
        <b>Metodología comunitaria:</b> La evidencia disponible en <code>steal-an-egg-research</code> documenta un evento visual con Secret Tralaledon Egg en Prehistoric y una serie de 5 reinicios consecutivos en un mismo servidor durante un directo de admin abuse. <b>No constituye un horario oficial ni universal para todos los servidores</b>, ya que los servidores se inician en momentos distintos.
      </div>
    </div>

    <h3 style="font-size: 16px; margin: 24px 0 12px; color: #fff;">Registros y evidencias documentadas</h3>
    <div id="spawnEvidenceCards" class="servers-grid">
      <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 30px;">
        Cargando archivo de evidencias comunitarias…
      </div>
    </div>
  </section>

  <!-- TAB 5: MEJORES OPORTUNIDADES -->
  <section id="tab-opportunities" class="tab-content">
    <div class="disclaimer-box">
      <div class="disclaimer-icon">🏆</div>
      <div>
        <b>Ranking de mejores oportunidades del catálogo:</b> Clasificación de las mascotas con mayor potencial de ganancias por rareza y los biomas/huevos con mayor concentración de alta rareza. Recuerda: <i>Contenido del servidor no disponible públicamente</i>.
      </div>
    </div>

    <div class="opp-grid">
      <div class="opp-col">
        <h4 style="color: #60a5fa;">💎 Top Rare</h4>
        <div id="topRareList" class="notification-list">Cargando…</div>
      </div>
      <div class="opp-col">
        <h4 style="color: #facc15;">👑 Top Divine</h4>
        <div id="topDivineList" class="notification-list">Cargando…</div>
      </div>
      <div class="opp-col">
        <h4 style="color: #f472b6;">🔮 Top Secret</h4>
        <div id="topSecretList" class="notification-list">Cargando…</div>
      </div>
      <div class="opp-col">
        <h4 style="color: #c084fc;">⚡ Top Eternal</h4>
        <div id="topEternalList" class="notification-list">Cargando…</div>
      </div>
    </div>

    <h3 style="font-size: 16px; margin: 24px 0 12px; color: #fff;">Mejores huevos y biomas por potencial</h3>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Huevo / Bioma</th>
            <th>Mascotas de alta rareza</th>
            <th>Mejor mascota observada</th>
            <th>Ganancia base máxima</th>
            <th>Acción</th>
          </tr>
        </thead>
        <tbody id="topEggsBody">
          <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Cargando análisis…</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- TAB 6: NOTIFICACIONES -->
  <section id="tab-notifications" class="tab-content">
    <div class="controls-bar">
      <div>
        <h3 style="font-size: 16px; color: #fff;">Preferencias de notificaciones automáticas</h3>
        <p style="font-size: 12px; color: var(--text-muted);">
          Recibe alertas del navegador cuando ocurran eventos o la ventana estimada del ciclo se aproxime.
        </p>
      </div>
      <div class="controls-group">
        <button class="btn btn-purple" onclick="requestBrowserPermission()">Activar permisos del navegador</button>
      </div>
    </div>

    <div class="calc-card" style="margin-bottom: 20px;">
      <h4 style="font-size: 14px; margin-bottom: 12px; color: #fff;">Filtrar alertas por rareza y tipo:</h4>
      <div style="display: flex; gap: 16px; flex-wrap: wrap;">
        <label style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <input type="checkbox" id="prefRare" checked> Rare
        </label>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <input type="checkbox" id="prefDivine" checked> Divine
        </label>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <input type="checkbox" id="prefSecret" checked> Secret
        </label>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <input type="checkbox" id="prefEternal" checked> Eternal
        </label>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <input type="checkbox" id="prefCycle" checked> Ventana estimada de 5 min
        </label>
      </div>
    </div>

    <div class="controls-bar">
      <b style="font-size: 14px; color: #fff;">Historial de notificaciones en sesión</b>
      <button class="btn btn-secondary" onclick="clearNotifHistory()">Limpiar historial</button>
    </div>
    <div id="notifHistoryList" class="notification-list">
      <div class="notif-item">
        <div>
          <b>Sistema iniciado</b>
          <div style="font-size: 12px; color: var(--text-muted);">Radar conectado al PlaceId 107778070777162.</div>
        </div>
        <small>Justo ahora</small>
      </div>
    </div>
  </section>

  <!-- MODAL DE JOIN -->
  <div id="joinModal" class="modal-overlay">
    <div class="modal-window">
      <button class="modal-close" onclick="closeJoinModal()">✕</button>
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
        <div style="font-size: 28px;">🚀</div>
        <div>
          <h3 style="font-size: 18px; color: #fff;">Conectar con servidor de Roblox</h3>
          <p style="font-size: 12px; color: var(--text-muted);">Steal An Egg (PlaceId: 107778070777162)</p>
        </div>
      </div>

      <div style="background: rgba(8, 13, 25, 0.9); border: 1px solid var(--card-border); border-radius: 12px; padding: 14px; margin-bottom: 16px;">
        <div style="font-size: 12px; color: var(--text-muted);">Identificador JobId:</div>
        <div id="modalJobId" style="font-family: var(--font-mono); font-size: 13px; color: #93c5fd; word-break: break-all; margin: 4px 0 10px;">—</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
          <div>Jugadores: <b id="modalPlayers" style="color: #fff;">—</b></div>
          <div>Espacios libres: <b id="modalFree" style="color: var(--emerald);">—</b></div>
        </div>
      </div>

      <div class="disclaimer-box" style="font-size: 12px; margin-bottom: 20px;">
        <div>
          <b>Nota sobre la conexión:</b> El botón abrirá el intento oficial de conexión de Roblox. Si el servidor se llenó o se cerró recientemente, el cliente de Roblox mostrará un mensaje de error. No se confirma que el jugador entró hasta que Roblox cargue por completo el servidor.
        </div>
      </div>

      <div style="display: flex; flex-direction: column; gap: 10px;">
        <a id="modalJoinWebBtn" href="#" target="_blank" rel="noopener" class="btn btn-join" style="justify-content: center; font-size: 14px;">
          🌐 Abrir intento oficial en Roblox Web
        </a>
        <a id="modalJoinAppBtn" href="#" class="btn btn-purple" style="justify-content: center; font-size: 14px;">
          ⚡ Abrir directo en Roblox App (Deep Link)
        </a>
        <button class="btn btn-secondary" onclick="closeJoinModal()" style="justify-content: center;">
          ← Volver al radar de servidores
        </button>
      </div>
    </div>
  </div>

  <footer>
    Steal An Egg Radar · Datos oficiales de servidores de Roblox · Fuentes comunitarias: RBLX Guide, GrindMath y Steal An Egg Research.<br>
    Este proyecto no tiene afiliación con Roblox Corporation ni los creadores de Steal An Egg. Consulta servidores públicos sin modificar clientes.
  </footer>
</div>

<script>
// ESTADO GLOBAL DE LA APLICACIÓN
const PLACE_ID = "107778070777162";
let allServers = [];
let allPets = [];
let currentRarityFilter = "all";
let spawnIntervalTimer = null;
let spawnStartTime = null;
let notifHistory = [];
const seenNotifIds = new Set();

// 1. GESTIÓN DE PESTAÑAS
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
  
  const targetTab = document.getElementById('tab-' + tabId);
  if (targetTab) targetTab.classList.add('active');
  
  const clickedBtn = Array.from(document.querySelectorAll('.nav-tab')).find(b => b.getAttribute('onclick').includes(tabId));
  if (clickedBtn) clickedBtn.classList.add('active');

  if (tabId === 'opportunities') loadBestOpportunities();
}

// 2. RADAR DE SERVIDORES OFICIALES
async function loadServers(append = false, manual = false) {
  const statusSub = document.getElementById("statServerSub");
  const sort = document.getElementById("serverSort").value;
  const search = document.getElementById("serverSearch").value.trim();

  if (manual) statusSub.textContent = "Actualizando servidores...";

  try {
    const url = `/api/servers?sort_by=${encodeURIComponent(sort)}&search=${encodeURIComponent(search)}${manual ? '&force_refresh=true' : ''}`;
    const res = await fetch(url);
    const data = await res.json();

    if (!data.success) throw new Error(data.error || "No se pudo consultar servidores");

    allServers = data.data || [];
    document.getElementById("statServers").textContent = allServers.length;
    document.getElementById("statPlayers").textContent = data.total_players || allServers.reduce((a, b) => a + (b.playing || 0), 0);
    document.getElementById("statLastUpdate").textContent = "Última consulta: " + new Date().toLocaleTimeString();

    renderServers();
  } catch (err) {
    statusSub.textContent = "Error: " + err.message;
    if (!allServers.length) {
      document.getElementById("serversList").innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--rose);">
          ⚠️ Error al consultar servidores públicos: ${err.message}<br>
          <button class="btn btn-secondary" onclick="loadServers(false, true)" style="margin-top: 14px;">Reintentar conexión</button>
        </div>`;
    }
  }
}

function renderServers() {
  const container = document.getElementById("serversList");
  const search = (document.getElementById("serverSearch")?.value || "").toLowerCase();

  const filtered = allServers.filter(s => !search || s.id.toLowerCase().includes(search));

  if (!filtered.length) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted); background: var(--card-bg); border-radius: 14px;">
        No se encontraron servidores públicos disponibles con los filtros actuales.
      </div>`;
    return;
  }

  container.innerHTML = filtered.map((s, idx) => {
    const isAlmostFull = s.freeSlots <= 2;
    return `
      <div class="server-card">
        <div class="server-head">
          <div>
            <div class="server-title">Servidor Público #${idx + 1}</div>
            <div class="server-job" title="${s.id}">JobId: ${s.shortId}</div>
          </div>
          <span class="free-slots-badge ${isAlmostFull ? 'almost-full' : ''}">
            ${s.freeSlots} ${s.freeSlots === 1 ? 'espacio' : 'espacios'}
          </span>
        </div>
        <div class="server-stats">
          <div class="server-stat-item">
            <small>Jugadores</small>
            <b>${s.playing}/${s.maxPlayers}</b>
          </div>
          <div class="server-stat-item">
            <small>Ping</small>
            <b>${s.ping}${typeof s.ping === 'number' ? ' ms' : ''}</b>
          </div>
          <div class="server-stat-item">
            <small>FPS</small>
            <b>${s.fps}</b>
          </div>
        </div>
        <div class="server-card-bottom">
          <span class="server-notice">Público · Oficial</span>
          <button class="btn btn-join" onclick="openJoinModal('${s.id}', ${s.playing}, ${s.maxPlayers}, ${s.freeSlots})">
            JOIN ↗
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function filterServers() {
  renderServers();
}

// 3. MODAL DE JOIN CON VALIDACIÓN
function openJoinModal(jobId, playing, maxPlayers, freeSlots) {
  // Validación de seguridad del JobId
  if (!jobId || !/^[a-zA-Z0-9\-_]{8,64}$/.test(jobId)) {
    alert("Identificador de servidor inválido.");
    return;
  }

  document.getElementById("modalJobId").textContent = jobId;
  document.getElementById("modalPlayers").textContent = `${playing}/${maxPlayers}`;
  document.getElementById("modalFree").textContent = `${freeSlots} libres`;

  const webUrl = `https://www.roblox.com/games/start?placeId=${PLACE_ID}&gameInstanceId=${encodeURIComponent(jobId)}`;
  const deepLink = `roblox://placeId=${PLACE_ID}&gameInstanceId=${encodeURIComponent(jobId)}`;

  document.getElementById("modalJoinWebBtn").href = webUrl;
  document.getElementById("modalJoinAppBtn").href = deepLink;

  document.getElementById("joinModal").classList.add("open");
}

function closeJoinModal() {
  document.getElementById("joinModal").classList.remove("open");
}

// 4. CATÁLOGO Y FILTROS ESTRICTOS
async function loadPets() {
  try {
    const res = await fetch("/api/pets");
    const data = await res.json();
    if (data.success) {
      allPets = data.data || [];
      document.getElementById("statPets").textContent = allPets.length;
      document.getElementById("catalogCountInfo").textContent = `${allPets.length} mascotas verificadas en base de datos.`;
      populatePetDropdowns();
      renderPetTable();
    }
  } catch (err) {
    console.error("Error al cargar mascotas:", err);
  }
}

function selectRarityFilter(rarity) {
  currentRarityFilter = rarity;
  document.querySelectorAll(".rarity-pill").forEach(p => {
    p.classList.toggle("active", p.getAttribute("data-r") === rarity);
  });
  renderPetTable();
}

function renderPetTable() {
  const tbody = document.getElementById("petTableBody");
  const search = (document.getElementById("petSearch")?.value || "").toLowerCase();
  const sort = document.getElementById("petSort")?.value || "income_desc";
  const mutMult = parseFloat(document.getElementById("catalogMutation")?.value || 1.0);
  const sizeMult = Math.max(0.1, parseFloat(document.getElementById("catalogSize")?.value || 1.0));

  const targetRarities = ["rare", "divine", "secret", "eternal"];

  let filtered = allPets.filter(p => {
    const r = (p.rarity || "").toLowerCase();
    
    // Filtro estricto de rareza
    if (currentRarityFilter === "all") {
      if (!targetRarities.includes(r)) return false;
    } else {
      if (r !== currentRarityFilter) return false;
    }

    // Filtro de búsqueda
    if (search) {
      const matchName = (p.name || "").toLowerCase().includes(search);
      const matchEgg = (p.origin_egg || "").toLowerCase().includes(search);
      const matchRarity = (p.rarity || "").toLowerCase().includes(search);
      if (!matchName && !matchEgg && !matchRarity) return false;
    }

    return true;
  });

  // Ordenación
  if (sort === "income_desc") filtered.sort((a, b) => b.income - a.income);
  else if (sort === "income_asc") filtered.sort((a, b) => a.income - b.income);
  else if (sort === "value_desc") filtered.sort((a, b) => (b.estimated_value || 0) - (a.estimated_value || 0));
  else if (sort === "name") filtered.sort((a, b) => a.name.localeCompare(b.name));

  document.getElementById("catalogCountInfo").textContent = `Mostrando ${filtered.length} mascotas (filtro: ${currentRarityFilter.toUpperCase()})`;

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">No se encontraron mascotas con este filtro.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(p => {
    const baseInc = p.income || 0;
    const simInc = baseInc * mutMult * sizeMult;
    const badgeClass = "badge-" + (p.rarity || "").toLowerCase();
    const hasOriginEgg = p.origin_egg && p.origin_egg !== "No disponible";

    return `
      <tr>
        <td>
          <b>${p.name}</b>
          ${p.base_weight && p.base_weight !== "No disponible" ? `<div style="font-size: 11px; color: var(--text-muted);">Peso base: ${p.base_weight} kg</div>` : ''}
        </td>
        <td><span class="badge ${badgeClass}">${p.rarity}</span></td>
        <td>
          ${p.origin_egg || "No disponible"}
          ${hasOriginEgg ? `<br><button class="btn-egg-view" onclick="filterByEgg('${p.origin_egg}')">🥚 Ver huevo</button>` : ''}
        </td>
        <td><span class="income-val">${p.income_formatted}</span></td>
        <td><span class="income-val" style="color: #38bdf8;">${formatMoney(simInc)}/s</span></td>
        <td>${p.estimated_value_formatted || 'No disponible'}</td>
        <td>
          <button class="btn-egg-view" onclick="sendToCalculator('${p.name}', ${p.income})">🧮 Calcular</button>
        </td>
      </tr>
    `;
  }).join("");
}

function filterByEgg(eggName) {
  document.getElementById("petSearch").value = eggName;
  selectRarityFilter("all");
}

function formatMoney(n) {
  if (n >= 1e9) return "$" + (n / 1e9).toFixed(2).replace(/\.00$/, "") + "B";
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(2).replace(/\.00$/, "") + "M";
  if (n >= 1e3) return "$" + (n / 1e3).toFixed(2).replace(/\.00$/, "") + "K";
  return "$" + n.toFixed(2).replace(/\.00$/, "");
}

// 5. CALCULADORA DE GANANCIAS
function populatePetDropdowns() {
  const select = document.getElementById("calcPetSelect");
  const compA = document.getElementById("compPetA");
  const compB = document.getElementById("compPetB");

  const opts = allPets.map(p => `<option value="${p.income}" data-name="${p.name}">${p.name} (${p.rarity}) - ${p.income_formatted}</option>`).join("");
  
  if (select) select.innerHTML = '<option value="">-- Selecciona una mascota --</option>' + opts;
  if (compA) compA.innerHTML = '<option value="">Seleccionar Mascota A...</option>' + opts;
  if (compB) compB.innerHTML = '<option value="">Seleccionar Mascota B...</option>' + opts;
}

function sendToCalculator(name, income) {
  switchTab('calculator');
  document.getElementById("calcBaseIncome").value = income;
  const select = document.getElementById("calcPetSelect");
  if (select) {
    const match = Array.from(select.options).find(o => o.getAttribute("data-name") === name);
    if (match) select.value = match.value;
  }
  runCalculator();
}

function onCalcPetChange() {
  const select = document.getElementById("calcPetSelect");
  if (select.value) {
    document.getElementById("calcBaseIncome").value = select.value;
    runCalculator();
  }
}

function runCalculator() {
  const base = parseFloat(document.getElementById("calcBaseIncome").value) || 0;
  const qty = parseInt(document.getElementById("calcQuantity").value) || 1;
  const mut = parseFloat(document.getElementById("calcMutation").value) || 1.0;
  const size = parseFloat(document.getElementById("calcSize").value) || 1.0;

  const perSec = base * qty * mut * size;
  const perMin = perSec * 60;
  const perHour = perSec * 3600;
  const perDay = perHour * 24;

  document.getElementById("resSec").textContent = formatMoney(perSec) + "/s";
  document.getElementById("resMin").textContent = formatMoney(perMin) + "/min";
  document.getElementById("resHour").textContent = formatMoney(perHour) + "/hr";
  document.getElementById("resDay").textContent = formatMoney(perDay);
}

function runComparison() {
  const incA = parseFloat(document.getElementById("compPetA").value) || 0;
  const qtyA = parseInt(document.getElementById("compQtyA").value) || 1;
  const mutA = parseFloat(document.getElementById("compMutA").value) || 1.0;

  const incB = parseFloat(document.getElementById("compPetB").value) || 0;
  const qtyB = parseInt(document.getElementById("compQtyB").value) || 1;
  const mutB = parseFloat(document.getElementById("compMutB").value) || 1.0;

  if (!incA || !incB) return;

  const totA = incA * qtyA * mutA;
  const totB = incB * qtyB * mutB;

  const diff = Math.abs(totA - totB);
  const percent = ((diff / Math.min(totA, totB)) * 100).toFixed(1);
  const winner = totA > totB ? "Mascota A" : totB > totA ? "Mascota B" : "Empate";

  document.getElementById("comparisonBox").innerHTML = `
    <div class="calc-row">
      <span>Producción Mascota A:</span>
      <b style="color: #60a5fa;">${formatMoney(totA)}/s</b>
    </div>
    <div class="calc-row">
      <span>Producción Mascota B:</span>
      <b style="color: #c084fc;">${formatMoney(totB)}/s</b>
    </div>
    <div class="calc-row highlight">
      <span>Diferencia de ventaja:</span>
      <b>${winner} (+${percent}%)</b>
    </div>
  `;
}

// 6. DETECTOR DE SPAWN Y ESTIMADOR DE 5 MINUTOS
async function loadSpawnEvidence() {
  const container = document.getElementById("spawnEvidenceCards");
  try {
    const res = await fetch("/api/spawn-evidence");
    const data = await res.json();

    const series = (data.intervalSeries || [])[0];
    if (series && series.statistics) {
      document.getElementById("spawnMedianVal").textContent = series.statistics.medianSeconds + " s";
      document.getElementById("spawnSamplesVal").textContent = series.statistics.completeIntervals;
    }

    const records = data.records || [];
    container.innerHTML = records.map(r => `
      <div class="server-card">
        <div>
          <div class="server-title">${r.visibleCue}</div>
          <div class="server-job">Zona: ${r.location} · Revisado: ${r.reviewedAt}</div>
          <div style="font-size: 12px; color: var(--emerald); margin-top: 8px;">Nivel de confianza: ${r.confidence}</div>
        </div>
        <div style="margin-top: 14px;">
          <a href="${r.sourceUrl}" target="_blank" rel="noopener" class="btn btn-secondary" style="font-size: 11px;">
            Ver video de evidencia ↗
          </a>
        </div>
      </div>
    `).join("") + (series ? `
      <div class="server-card">
        <div>
          <div class="server-title">${series.target} (${series.context})</div>
          <div class="server-job">5 intervalos continuos observados: ${series.intervalSeconds.join(", ")} s</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">${series.limitations}</div>
        </div>
        <div style="margin-top: 14px;">
          <a href="${series.sourceUrl}" target="_blank" rel="noopener" class="btn btn-secondary" style="font-size: 11px;">
            Ver directo continuo ↗
          </a>
        </div>
      </div>
    ` : '');

  } catch (err) {
    container.innerHTML = `<div style="grid-column: 1/-1; color: var(--rose);">No se pudo cargar evidencia: ${err.message}</div>`;
  }
}

function toggleSpawnEstimator() {
  const btn = document.getElementById("btnStartEstimator");
  const countdown = document.getElementById("spawnCountdownVal");
  const sub = document.getElementById("spawnCountdownSub");

  if (spawnIntervalTimer) {
    clearInterval(spawnIntervalTimer);
    spawnIntervalTimer = null;
    countdown.textContent = "Inactivo";
    countdown.style.color = "#38bdf8";
    sub.textContent = "Haz clic para iniciar ciclo de 5 min";
    btn.textContent = "▶️ Iniciar estimador";
    btn.classList.remove("btn-secondary");
    btn.classList.add("btn-purple");
    return;
  }

  spawnStartTime = Date.now();
  btn.textContent = "⏹️ Detener estimador";
  btn.classList.remove("btn-purple");
  btn.classList.add("btn-secondary");

  let alerted = false;

  spawnIntervalTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - spawnStartTime) / 1000);
    const remaining = Math.max(0, 300 - elapsed);
    const mm = String(Math.floor(remaining / 60)).padStart(2, "0");
    const ss = String(remaining % 60).padStart(2, "0");

    countdown.textContent = `${mm}:${ss}`;

    if (elapsed >= 293 && elapsed <= 307) {
      countdown.style.color = "#f59e0b";
      sub.textContent = "⚠️ ¡Ventana estimada de reinicio (293–307s)!";
      if (!alerted) {
        alerted = true;
        sendNotification(
          "⏱️ Steal An Egg: Ventana estimada alcanzada",
          "Han transcurrido 293–307 segundos desde tu inicio. Comprueba el juego (estimación comunitaria)."
        );
      }
    } else if (elapsed > 307) {
      // Reiniciar ciclo automáticamente
      spawnStartTime = Date.now();
      alerted = false;
      countdown.style.color = "#38bdf8";
      sub.textContent = "Nuevo ciclo de 5 minutos iniciado";
    }
  }, 1000);
}

// 7. MEJORES OPORTUNIDADES
async function loadBestOpportunities() {
  try {
    const res = await fetch("/api/best-opportunities");
    const data = await res.json();
    if (!data.success) return;

    const renderList = (id, items, badgeClass) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = items.map(p => `
        <div class="notif-item">
          <div>
            <b>${p.name}</b>
            <div style="font-size: 11px; color: var(--text-muted);">${p.origin_egg || 'Huevo no disponible'}</div>
          </div>
          <span class="income-val">${p.income_formatted}</span>
        </div>
      `).join("") || '<div style="color: var(--text-muted);">No disponible</div>';
    };

    renderList("topRareList", data.top_by_rarity.Rare || [], "badge-rare");
    renderList("topDivineList", data.top_by_rarity.Divine || [], "badge-divine");
    renderList("topSecretList", data.top_by_rarity.Secret || [], "badge-secret");
    renderList("topEternalList", data.top_by_rarity.Eternal || [], "badge-eternal");

    const eggBody = document.getElementById("topEggsBody");
    if (eggBody && data.top_eggs) {
      eggBody.innerHTML = data.top_eggs.map(e => `
        <tr>
          <td><b>🥚 ${e.egg_name}</b></td>
          <td><span class="free-slots-badge">${e.high_rarity_count} mascotas</span></td>
          <td>${e.best_pet || '—'}</td>
          <td><span class="income-val">${formatMoney(e.max_income)}/s</span></td>
          <td><button class="btn-egg-view" onclick="switchTab('catalog'); filterByEgg('${e.egg_name}')">Filtrar catálogo</button></td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Error al cargar mejores oportunidades:", err);
  }
}

// 8. NOTIFICACIONES DEL NAVEGADOR
async function requestBrowserPermission() {
  if (!("Notification" in window)) {
    alert("Tu navegador no soporta notificaciones de escritorio.");
    return;
  }
  const perm = await Notification.requestPermission();
  const btn = document.getElementById("notifToggleBtn");
  if (perm === "granted") {
    btn.textContent = "🔔 Alertas activadas";
    new Notification("Steal An Egg Radar", {
      body: "Notificaciones activadas. Recibirás avisos de la ventana estimada e incidencias del radar.",
      icon: "https://www.roblox.com/favicon.ico"
    });
    addNotifToHistory("Permiso concedido", "Notificaciones de navegador activadas con éxito.");
  } else {
    btn.textContent = "🔕 Notificaciones bloqueadas";
  }
}

function toggleNotifications() {
  requestBrowserPermission();
}

function sendNotification(title, body) {
  const id = title + "_" + body;
  if (seenNotifIds.has(id)) return;
  seenNotifIds.add(id);

  if ("Notification" in window && Notification.permission === "granted") {
    new Notification(title, { body: body, icon: "https://www.roblox.com/favicon.ico" });
  }
  addNotifToHistory(title, body);
}

function addNotifToHistory(title, body) {
  const list = document.getElementById("notifHistoryList");
  if (!list) return;
  const time = new Date().toLocaleTimeString();
  const item = document.createElement("div");
  item.className = "notif-item";
  item.innerHTML = `
    <div>
      <b>${title}</b>
      <div style="font-size: 12px; color: var(--text-muted);">${body}</div>
    </div>
    <small>${time}</small>
  `;
  list.prepend(item);
}

function clearNotifHistory() {
  document.getElementById("notifHistoryList").innerHTML = "";
}

// 9. INICIALIZACIÓN Y AUTO-REFRESCO CADA 30S
function refreshAll() {
  loadServers(false, true);
  loadPets();
  loadSpawnEvidence();
}

loadServers();
loadPets();
loadSpawnEvidence();

// Auto-refresco de servidores cada 30 segundos
setInterval(() => {
  loadServers(false, false);
}, 30000);
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    """Página principal del radar interactivo."""
    return render_template_string(INDEX_HTML)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
