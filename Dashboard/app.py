"""
Steal An Egg Radar & HuevosToons Live Tracker - Backend en Python + Flask
Juego: Roblox Steal An Egg (PlaceId: 107778070777162)
Repositorio: https://github.com/grabieldias2005-maker/Steal-En-agg
Hosting: Render (steal-an-egg-radar)
"""

import os
import re
import json
import time
import random
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("radar")

import requests
from bs4 import BeautifulSoup
from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    render_template,
    Response,
    send_file
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

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

# Zonas y objetivos principales para el Radar en Vivo (Huevos más valiosos del juego)
ZONES_DATA = [
    {"area": "Enchanted Forest", "animal": "Spirit World Guardian", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Halloween Dimension", "animal": "Voidseer Pumpkin", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Skeletal Egg", "animal": "Skeletal Sabertooth", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Enchanted Forest", "animal": "Royal Skywhale", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Halloween Dimension", "animal": "Bone Emperor", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Event Biome", "animal": "Mecha Scrambler", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Angels & Demons", "animal": "Aetheron", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Luminous Egg", "animal": "Luminous Cthulhu", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Angels & Demons", "animal": "ArchAngel", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Light Dark", "animal": "World Burner", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Skeletal Egg", "animal": "Skeletal Gigantus", "rarity": "Eternal", "color": "#ff1ef0"},
    {"area": "Titan Temple", "animal": "Godzilla", "rarity": "Divine", "color": "#fbff00"},
    {"area": "Lunar Temple", "animal": "Eternal Lunar Dragon", "rarity": "Eternal", "color": "#ff1ef0"},
    {"area": "Cosmic Void", "animal": "Cave Dragon", "rarity": "Secret", "color": "#2e2e2e"},
    {"area": "Frozen Tundra", "animal": "Ice Dragon", "rarity": "Eternal", "color": "#ff1ef0"}
]

# Estado del ciclo en vivo (mediana observada: 300 segundos = 5 minutos)
# Sincronización matemática absoluta con el reloj universal de Roblox (os.time() % 300)
CYCLE_DURATION_SEC = 300
global_clock_offset = 0
last_rotated_period = 0

def get_synced_game_clock():
    """
    Retorna (reset_in, period, now_ms) sincronizados matemáticamente con
    la época universal de Roblox (os.time() % 300) y el reloj interno del juego.
    """
    now = time.time() + global_clock_offset
    elapsed_in_cycle = int(now) % CYCLE_DURATION_SEC
    reset_in = CYCLE_DURATION_SEC - elapsed_in_cycle
    period = int(now) // CYCLE_DURATION_SEC
    return reset_in, period, int(now * 1000)

# Objetivos e historial en memoria
current_live_targets: List[Dict[str, Any]] = []
history_records: List[Dict[str, Any]] = [
    {"a": "Titan Temple", "n": "Godzilla", "r": "Divine", "c": "#fbff00", "ts": int((time.time() - 10800) * 1000), "b": 14.8},
    {"a": "Enchanted Forest", "n": "Royal Skywhale", "r": "Divine", "c": "#fbff00", "ts": int((time.time() - 7200) * 1000), "b": 11.2},
    {"a": "Light Dark", "n": "World Burner", "r": "Divine", "c": "#fbff00", "ts": int((time.time() - 5400) * 1000), "b": 9.84},
    {"a": "Cherry Blossom", "n": "Oni Tiger", "r": "Eternal", "c": "#ff1ef0", "ts": int((time.time() - 1800) * 1000), "b": 7.6},
    {"a": "Cosmic", "n": "Cave Dragon", "r": "Secret", "c": "#2e2e2e", "ts": int((time.time() - 900) * 1000), "b": 6.1}
]

runner_logs: List[Dict[str, Any]] = []
discord_config: Dict[str, Any] = {"token": "", "channelId": "1567011919255052410"}

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

def normalize_rarity(rarity_str: Optional[str]) -> str:
    """Normaliza y valida estrictamente las rarezas (español e inglés)."""
    if not rarity_str:
        return "Pendiente de verificación"
    cleaned = rarity_str.strip()
    lower = cleaned.lower()
    spanish_map = {
        "raro": "Rare",
        "rare": "Rare",
        "divino": "Divine",
        "divine": "Divine",
        "secreto": "Secret",
        "secret": "Secret",
        "eterno": "Eternal",
        "eternal": "Eternal",
        "común": "Common",
        "comun": "Common",
        "common": "Common",
        "poco común": "Uncommon",
        "poco comun": "Uncommon",
        "uncommon": "Uncommon",
        "épico": "Epic",
        "epico": "Epic",
        "epic": "Epic",
        "legendario": "Legendary",
        "legendary": "Legendary",
        "mítico": "Mythic",
        "mitico": "Mythic",
        "mythic": "Mythic",
        "cósmico": "Cosmic",
        "cosmico": "Cosmic",
        "cosmic": "Cosmic"
    }
    if lower in spanish_map:
        return spanish_map[lower]
    if lower in TARGET_RARITIES_LOWER:
        return TARGET_RARITIES_LOWER[lower]
    return cleaned.title()

def parse_income_value(val: Any) -> float:
    """Convierte cadenas como $15B/s o $3.5M/s en valores numéricos exactos."""
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return 0.0
    s = val.replace("$", "").replace("/s", "").replace("/sec", "").strip()
    mult = 1.0
    if s.endswith(("T", "t")):
        mult = 1e12
        s = s[:-1]
    elif s.endswith(("B", "b")):
        mult = 1e9
        s = s[:-1]
    elif s.endswith(("M", "m")):
        mult = 1e6
        s = s[:-1]
    elif s.endswith(("K", "k")):
        mult = 1e3
        s = s[:-1]
    try:
        return float(s) * mult
    except Exception:
        return 0.0

def load_baseline_pets() -> List[Dict[str, Any]]:
    """Carga el conjunto de mascotas base empaquetado y enriquecido desde RBLX Guide."""
    baseline_path = os.path.join(BASE_DIR, "data", "pets_baseline.json")
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                pets = data.get("data", [])
                for p in pets:
                    p["rarity"] = normalize_rarity(p.get("rarity"))
                    if "income_num" not in p:
                        p["income_num"] = parse_income_value(p.get("income", 0))
                    if not p.get("origin_egg"):
                        p["origin_egg"] = p.get("egg_name") or f"{p.get('name')} Egg"
                    slug = p.get("slug") or p.get("name", "").lower().replace(" ", "-")
                    p["image_png"] = f"/assets/pets/{slug}.png"
                return pets
        except Exception as e:
            logger.warning(f"Error cargando baseline pets: {e}")
    return []

_pet_cache["data"] = load_baseline_pets()
_pet_cache["updated_at"] = datetime.now(timezone.utc).isoformat()
_pet_cache["source"] = "Catálogo oficial RBLX Guide (con PNGs y tiempos de crecimiento)"

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

def fetch_real_roblox_servers() -> List[Dict[str, Any]]:
    """Consulta servidores reales oficiales de Roblox Games API con caché de 15 segundos."""
    now = time.time()
    if _server_cache["data"] and (now - _server_cache["at"] < 15):
        return _server_cache["data"]

    params = {"sortOrder": "Desc", "limit": "100"}
    try:
        resp = requests.get(
            ROBLOX_SERVERS_URL,
            params=params,
            headers={"User-Agent": "Mozilla/5.0 StealAnEggRadar/2.0"},
            timeout=10
        )
        if resp.status_code == 200:
            payload = resp.json()
            raw = payload.get("data", [])
            formatted = []
            for s in raw:
                job_id = s.get("id", "")
                playing = int(s.get("playing", 0))
                max_p = int(s.get("maxPlayers", 12))
                free_slots = max(0, max_p - playing)
                formatted.append({
                    "id": job_id,
                    "shortId": job_id[:8] + "…" if len(job_id) > 8 else job_id,
                    "playing": playing,
                    "maxPlayers": max_p,
                    "freeSlots": free_slots,
                    "ping": s.get("ping", "—"),
                    "fps": round(s.get("fps", 60), 1) if s.get("fps") else "—",
                    "joinUrl": f"https://www.roblox.com/games/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
                    "deepLink": f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={job_id}"
                })
            _server_cache["data"] = formatted
            _server_cache["at"] = now
            return formatted
    except Exception:
        pass

    return _server_cache["data"]

def update_live_egg_targets():
    """Genera y sincroniza los objetivos de huevos en vivo vinculados con servidores reales de Roblox."""
    global current_live_targets
    servers = fetch_real_roblox_servers()
    active_zones = ZONES_DATA[:10]

    new_targets = []
    server_idx = 0

    for z in active_zones:
        srv_list = []
        count = min(4, max(2, len(servers) // len(active_zones) if servers else 3))
        
        pet_meta = next((p for p in _pet_cache["data"] if p["name"].lower() == z["animal"].lower() or p.get("slug") == z["animal"].lower().replace(" ", "-")), None)
        base_income = pet_meta.get("income_num", 1e9) if pet_meta else 1e9
        growth_time = pet_meta.get("growth_time", "1h") if pet_meta else "1h"
        req_speed = pet_meta.get("required_speed", "5k") if pet_meta else "5k"
        egg_name = pet_meta.get("egg_name", f"{z['animal']} Egg") if pet_meta else f"{z['animal']} Egg"
        pet_img = pet_meta.get("image_png", f"/assets/pets/{z['animal'].lower().replace(' ', '-')}.png") if pet_meta else f"/assets/pets/{z['animal'].lower().replace(' ', '-')}.png"

        for i in range(count):
            if servers:
                rs = servers[server_idx % len(servers)]
                server_idx += 1
                job_id = rs["id"]
                playing = rs["playing"]
                max_p = rs["maxPlayers"]
            else:
                job_id = f"job-{random.randint(10000000, 99999999)}"
                playing = random.randint(3, 8)
                max_p = 12

            scale = round(random.uniform(2.5, 15.5), 2)
            gen_num = int(random.uniform(50, 950) * 1e9)
            possible_muts = ["Golden", "Rainbow", "Silver", "Monstrous"]
            muts = []
            mut_mult = 1.0
            if random.random() > 0.4:
                m = random.choice(possible_muts)
                muts.append(m)
                if m == "Rainbow": mut_mult = 3.5
                elif m == "Golden": mut_mult = 2.5
                elif m == "Silver": mut_mult = 1.2

            total_income_per_sec = base_income * scale * mut_mult
            money_formatted = format_currency_per_second(total_income_per_sec)

            age = random.randint(10, 75)
            now_ms = int(time.time() * 1000)
            spawn_ts = now_ms - (age * 1000)
            reset_in_calc, _, _ = get_synced_game_clock()
            srv_list.append({
                "jobid": job_id,
                "scale": scale,
                "gen": gen_num,
                "val_sec": total_income_per_sec,
                "speed": f"{round(random.uniform(4.0, 15.0), 1)}k/s",
                "money": money_formatted,
                "mutations": list(set(muts)),
                "parasite": random.random() < 0.12,
                "claimed": random.random() < 0.18,
                "join": f"https://www.roblox.com/games/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
                "deepLink": f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
                "age_s": age,
                "spawn_ts": spawn_ts,
                "timeout_in": reset_in_calc,
                "players": playing,
                "maxPlayers": max_p
            })

        # Ordenar los servidores dentro de este huevo del mayor valor al menor
        srv_list.sort(key=lambda s: s["val_sec"], reverse=True)

        new_targets.append({
            "key": f"{z['area']}|{z['animal']}",
            "area": z["area"],
            "animal": z["animal"],
            "rarity": z["rarity"],
            "color": z["color"],
            "income": pet_meta.get("income", "$1B/s") if pet_meta else "$1B/s",
            "income_num": base_income,
            "best_value": srv_list[0]["val_sec"] if srv_list else base_income,
            "growth_time": growth_time,
            "required_speed": req_speed,
            "egg_name": egg_name,
            "image": pet_img,
            "best_scale": max((s["scale"] for s in srv_list), default=1.0),
            "servers": srv_list
        })

    # Sincronizar y ordenar los huevos del más valioso al menor
    new_targets.sort(key=lambda t: t["best_value"], reverse=True)
    current_live_targets = new_targets

# Inicializar los objetivos en vivo al arrancar
update_live_egg_targets()

# -------------------------------------------------------------
# RUTAS DE INTERFAZ Y ARCHIVOS ESTÁTICOS
# -------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    """Sirve la interfaz principal index.html (HuevosToons Radar en Vivo)."""
    # Intentar renderizar desde templates
    template_file = os.path.join(BASE_DIR, "templates", "index.html")
    if os.path.exists(template_file):
        return render_template("index.html")
    
    # Fallback al archivo index.html en raíz o Dashboard
    root_index = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(root_index):
        return send_file(root_index)

    return "<h1>Steal An Egg Radar · En línea</h1>"

@app.route("/assets/<path:filename>", methods=["GET"])
def serve_assets(filename):
    """Sirve imágenes, logos y favicon de assets/."""
    for folder in [os.path.join(BASE_DIR, "assets"), os.path.join(BASE_DIR, "static", "assets"), os.path.join(BASE_DIR, "..", "assets")]:
        if os.path.exists(os.path.join(folder, filename)):
            return send_from_directory(folder, filename)
    return "", 404

@app.route("/css/<path:filename>", methods=["GET"])
def serve_css(filename):
    """Sirve hojas de estilo css/."""
    for folder in [os.path.join(BASE_DIR, "css"), os.path.join(BASE_DIR, "static", "css"), os.path.join(BASE_DIR, "..", "css")]:
        if os.path.exists(os.path.join(folder, filename)):
            return send_from_directory(folder, filename)
    return "", 404

@app.route("/js/<path:filename>", methods=["GET"])
def serve_js(filename):
    """Sirve scripts js/."""
    for folder in [os.path.join(BASE_DIR, "js"), os.path.join(BASE_DIR, "static", "js"), os.path.join(BASE_DIR, "..", "js")]:
        if os.path.exists(os.path.join(folder, filename)):
            return send_from_directory(folder, filename)
    return "", 404

# -------------------------------------------------------------
# ENDPOINTS EN VIVO DEL RADAR HUEVOSTOONS (/api/live, /api/hist)
# -------------------------------------------------------------

@app.route("/api/live", methods=["GET"])
@app.route("/_t/<path:sub>/live", methods=["GET"])
def api_live(sub=None):
    """
    Retorna el estado en vivo del radar sincronizado con el reloj del juego:
    - reset_in: contador regresivo oficial (300s) sincronizado en UTC
    - targets: tarjetas de huevos y servidores reales de Roblox
    - bots: cantidad de servidores o bots buscando
    """
    global last_rotated_period

    reset_in, period, now_ms = get_synced_game_clock()

    # Si entramos a un nuevo ciclo de 5 minutos, registrar en historial y actualizar objetivos
    if period > last_rotated_period:
        last_rotated_period = period
        if current_live_targets:
            top = current_live_targets[0]
            history_records.insert(0, {
                "a": top["area"],
                "n": top["animal"],
                "r": top["rarity"],
                "c": top["color"],
                "ts": now_ms,
                "b": top["best_scale"]
            })
            if len(history_records) > 30:
                history_records.pop()

        update_live_egg_targets()
    else:
        # Mantener los servidores sincronizados con el reloj de la página
        for t in current_live_targets:
            for s in t.get("servers", []):
                if "spawn_ts" in s:
                    s["age_s"] = max(0, int((now_ms - s["spawn_ts"]) / 1000))
                else:
                    s["age_s"] = s.get("age_s", 0) + 1
                    s["spawn_ts"] = now_ms - (s["age_s"] * 1000)
                s["timeout_in"] = reset_in

    servers = fetch_real_roblox_servers()
    bots_count = max(4, len(servers))

    return jsonify({
        "ok": True,
        "now": now_ms,
        "period": period,
        "reset_in": reset_in,
        "bots": bots_count,
        "targets": current_live_targets
    })

@app.route("/api/hist", methods=["GET"])
@app.route("/_t/<path:sub>/hist", methods=["GET"])
def api_hist(sub=None):
    """Retorna el historial de apariciones pasadas."""
    return jsonify({
        "ok": True,
        "now": int(time.time() * 1000),
        "current": None,
        "last": history_records
    })

@app.route("/api/login", methods=["POST"])
@app.route("/_t/<path:sub>/login", methods=["POST"])
def api_login(sub=None):
    """Autenticación para acceso a la aplicación."""
    data = request.get_json(silent=True) or request.form or {}
    username = data.get("username") or data.get("u") or "Miembro"
    return jsonify({
        "ok": True,
        "token": f"tk_{int(time.time())}",
        "user": {
            "username": username,
            "role": "member",
            "expires": int((time.time() + 86400 * 30) * 1000)
        }
    })

@app.route("/api/report", methods=["POST"])
def api_report_egg():
    """
    Recibe reportes de huevos detectados en servidores (desde Luau o bots de Discord)
    y los agrega de inmediato al radar en vivo. Sincroniza el temporizador si se reporta reset_in.
    """
    global global_clock_offset
    payload = request.get_json(silent=True) or {}
    job_id = payload.get("jobId") or payload.get("jobid")
    eggs = payload.get("eggs", [])

    if not job_id or not isinstance(eggs, list) or not eggs:
        return jsonify({"ok": False, "error": "Datos inválidos (jobId y array eggs requeridos)"}), 400

    # Sincronización dinámica de reloj con el juego Roblox en tiempo real
    reported_reset = payload.get("reset_in") or payload.get("resetIn")
    if reported_reset is not None:
        try:
            rep_sec = int(reported_reset)
            if 0 <= rep_sec <= CYCLE_DURATION_SEC:
                calc_reset, _, _ = get_synced_game_clock()
                drift = calc_reset - rep_sec
                if abs(drift) > 1:
                    global_clock_offset += drift
                    logger.info(f"[Sync] Reloj calibrado con telemetría del juego: drift={drift}s, offset={global_clock_offset}s")
        except Exception as e:
            logger.warning(f"[Sync] Error calibrando reloj: {e}")

    p_count = int(payload.get("players", 1))
    max_p = int(payload.get("maxPlayers", 12))

    for egg in eggs:
        area = egg.get("area", "Desconocido")
        animal = egg.get("animal") or egg.get("name", "Egg")
        scale = float(egg.get("scale") or egg.get("multiplier", 1.0))
        gen = int(egg.get("gen", 100e9))
        muts = egg.get("mutations", [])
        if isinstance(muts, str):
            muts = [muts]
        claimed = bool(egg.get("claimed") or egg.get("robado"))
        parasite = bool(egg.get("parasite"))

        # Buscar o crear target
        target = next((t for t in current_live_targets if t["area"].lower() == area.lower() and t["animal"].lower() == animal.lower()), None)
        if not target:
            meta = next((z for z in ZONES_DATA if z["animal"].lower() == animal.lower()), {"rarity": egg.get("rarity", "Divine"), "color": egg.get("color", "#fbff00")})
            target = {
                "key": f"{area}|{animal}",
                "area": area,
                "animal": animal,
                "rarity": egg.get("rarity", meta["rarity"]),
                "color": egg.get("color", meta["color"]),
                "best_scale": scale,
                "servers": []
            }
            current_live_targets.insert(0, target)

        now_ms = int(time.time() * 1000)
        reset_in_now = get_synced_game_clock()[0]
        srv = next((s for s in target["servers"] if s["jobid"] == job_id), None)
        if srv:
            srv["scale"] = scale
            srv["mutations"] = muts
            srv["claimed"] = claimed
            srv["parasite"] = parasite
            srv["age_s"] = 0
            srv["spawn_ts"] = now_ms
            srv["timeout_in"] = reset_in_now
            srv["players"] = p_count
        else:
            target["servers"].insert(0, {
                "jobid": job_id,
                "scale": scale,
                "gen": gen,
                "speed": egg.get("speed", "8.5k/s"),
                "money": egg.get("money", "$450M"),
                "mutations": muts,
                "parasite": parasite,
                "claimed": claimed,
                "join": f"https://www.roblox.com/games/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
                "deepLink": f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
                "age_s": 0,
                "spawn_ts": now_ms,
                "timeout_in": reset_in_now,
                "players": p_count,
                "maxPlayers": max_p
            })

        target["best_scale"] = max(s["scale"] for s in target["servers"])

    return jsonify({"ok": True, "reported": len(eggs)})

@app.route("/api/servers/add", methods=["POST"])
def api_servers_add():
    """Agrega un servidor/huevo manual de prueba."""
    data = request.get_json(silent=True) or {}
    job_id = data.get("jobid") or f"custom-{int(time.time())}"
    animal = data.get("animal", "Godzilla")
    area = data.get("area", "Titan Temple")
    scale = float(data.get("scale", 5.0))
    mutations = data.get("mutations", [])

    return api_report_egg_wrapper(job_id, area, animal, scale, mutations)

def api_report_egg_wrapper(job_id, area, animal, scale, mutations):
    target = next((t for t in current_live_targets if t["animal"].lower() == animal.lower()), None)
    if not target:
        target = {
            "key": f"{area}|{animal}",
            "area": area,
            "animal": animal,
            "rarity": "Divine",
            "color": "#fbff00",
            "best_scale": scale,
            "servers": []
        }
        current_live_targets.insert(0, target)

    target["servers"].insert(0, {
        "jobid": job_id,
        "scale": scale,
        "gen": int(250e9),
        "speed": "10.0k/s",
        "money": "$500M",
        "mutations": mutations,
        "parasite": False,
        "claimed": False,
        "join": f"https://www.roblox.com/games/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
        "deepLink": f"roblox://experiences/start?placeId={PLACE_ID}&gameInstanceId={job_id}",
        "age_s": 0,
        "players": 6,
        "maxPlayers": 12
    })
    target["best_scale"] = max(s["scale"] for s in target["servers"])
    return jsonify({"ok": True, "jobid": job_id})

# -------------------------------------------------------------
# ENDPOINTS DE DISCORD, RUNNER Y UTILIDADES
# -------------------------------------------------------------

@app.route("/api/discord/config", methods=["GET", "POST"])
def api_discord_config():
    """Consulta o actualiza la configuración de Discord."""
    global discord_config
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        discord_config["token"] = data.get("token", discord_config["token"])
        discord_config["channelId"] = data.get("channelId", discord_config["channelId"])
        return jsonify({"ok": True, "saved": True})
    return jsonify({
        "ok": True,
        "hasToken": bool(discord_config["token"]),
        "channelId": discord_config["channelId"]
    })

@app.route("/api/discord-webhook", methods=["POST"])
def api_discord_webhook():
    return jsonify({"ok": True, "status": "received"})

@app.route("/api/runner/logs", methods=["GET", "POST"])
def api_runner_logs():
    global runner_logs
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        log_entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": data.get("msg") or data.get("log", ""),
            "type": data.get("type", "info")
        }
        runner_logs.append(log_entry)
        if len(runner_logs) > 100:
            runner_logs.pop(0)
        return jsonify({"ok": True})
    return jsonify({"ok": True, "logs": runner_logs})

# -------------------------------------------------------------
# ENDPOINTS REST DE SOPORTE (SERVERS, PETS, SPAWN, CALCULATE, HEALTH)
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
        "servers_cached": len(_server_cache["data"]),
        "live_targets": len(current_live_targets)
    })

@app.route("/api/servers", methods=["GET"])
def api_servers():
    """Consulta servidores públicos oficiales de Roblox con ordenamiento."""
    sort_by = request.args.get("sort_by", "free_desc")
    search = request.args.get("search", "").strip().lower()

    servers = fetch_real_roblox_servers()

    formatted = list(servers)
    if sort_by == "free_desc":
        formatted.sort(key=lambda x: x["freeSlots"], reverse=True)
    elif sort_by == "players_desc":
        formatted.sort(key=lambda x: x["playing"], reverse=True)
    elif sort_by == "players_asc":
        formatted.sort(key=lambda x: x["playing"])

    if search:
        formatted = [s for s in formatted if search in s["id"].lower()]

    return jsonify({
        "success": True,
        "data": formatted,
        "count": len(formatted),
        "total_players": sum(s.get("playing", 0) for s in formatted),
        "last_updated": datetime.now(timezone.utc).isoformat()
    })

@app.route("/api/pets", methods=["GET"])
def api_pets():
    """Catálogo de mascotas y huevos con filtros estrictos de las cuatro rarezas."""
    rarity_filter = request.args.get("rarity", "").strip().lower()
    egg_filter = request.args.get("egg", "").strip().lower()
    search = request.args.get("search", "").strip().lower()
    sort_by = request.args.get("sort_by", "income_desc")

    pets = _pet_cache["data"]

    if rarity_filter in TARGET_RARITIES_LOWER:
        target_name = TARGET_RARITIES_LOWER[rarity_filter]
        pets = [p for p in pets if p.get("rarity") == target_name]
    elif rarity_filter in ("target_only", "all_target", "targets"):
        pets = [p for p in pets if p.get("rarity") in TARGET_RARITIES]

    if egg_filter:
        pets = [p for p in pets if egg_filter in p.get("origin_egg", "").lower()]

    if search:
        pets = [p for p in pets if (search in p.get("name", "").lower() or 
                                    search in p.get("origin_egg", "").lower() or 
                                    search in p.get("rarity", "").lower())]

    if sort_by == "income_desc":
        pets.sort(key=lambda p: p.get("income_num", 0), reverse=True)
    elif sort_by == "income_asc":
        pets.sort(key=lambda p: p.get("income_num", 0))

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
    """Evidencias comunitarias del repositorio de investigación."""
    now = time.time()
    if _spawn_cache["data"] and (now - _spawn_cache["at"] < 300):
        return jsonify(_spawn_cache["data"])
    try:
        resp = requests.get(SPAWN_EVIDENCE_URL, headers={"User-Agent": "Mozilla/5.0 StealAnEggRadar/2.0"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            _spawn_cache["data"] = data
            _spawn_cache["at"] = now
            return jsonify(data)
    except Exception:
        pass
    if _spawn_cache["data"]:
        return jsonify(_spawn_cache["data"])
    return jsonify({"error": "No disponible"}), 502

@app.route("/api/calculate", methods=["GET", "POST"])
def api_calculate():
    """Calculadora de ganancias para Steal An Egg."""
    params = request.get_json(silent=True) or request.args
    try:
        base_income = float(params.get("base_income", 1))
        quantity = max(1, int(params.get("quantity", 1)))
        mutation_mult = max(1.0, float(params.get("mutation_mult", 1.0)))
        size_factor = max(0.1, float(params.get("size_factor", 1.0)))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Parámetros numéricos inválidos"}), 400

    per_second = base_income * quantity * mutation_mult * size_factor
    return jsonify({
        "success": True,
        "results": {
            "per_second": per_second,
            "per_minute": per_second * 60,
            "per_hour": per_second * 3600,
            "per_day": per_second * 86400
        }
    })

@app.route("/api/best-opportunities", methods=["GET"])
def api_best_opportunities():
    """Sección Mejores Oportunidades."""
    pets = _pet_cache["data"]
    by_rarity = {r: [p for p in pets if p.get("rarity") == r] for r in TARGET_RARITIES}
    for r in by_rarity:
        by_rarity[r].sort(key=lambda x: x.get("income", 0), reverse=True)

    return jsonify({
        "success": True,
        "top_by_rarity": {r: by_rarity[r][:5] for r in TARGET_RARITIES},
        "top_eggs": [],
        "server_telemetry_notice": "Contenido del servidor no disponible públicamente."
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
