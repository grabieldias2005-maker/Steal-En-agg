"""
Suite de pruebas automatizadas para Steal An Egg Radar & HuevosToons Live Tracker
Backend: Python + Flask (Dashboard/app.py)
"""

import sys
import os
import pytest

# Asegurar que el módulo Dashboard pueda ser importado
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import (
    app,
    PLACE_ID,
    TARGET_RARITIES,
    normalize_rarity,
    format_currency_per_second,
    format_plain_currency
)

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Verifica que el endpoint de salud devuelva 200 y el PlaceId correcto."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "steal-an-egg-radar"
    assert data["placeId"] == "107778070777162"
    assert "pets_count" in data

def test_home_page_rendering(client):
    """Verifica que la página principal sirva index.html."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "HuevosToons" in html or "Radar" in html
    assert "app" in html

def test_api_live_radar_endpoint(client):
    """Verifica el radar en vivo y el contador regresivo de 300 segundos."""
    res = client.get("/api/live")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert "reset_in" in data
    assert 0 <= data["reset_in"] <= 300
    assert "targets" in data
    assert len(data["targets"]) > 0
    
    first_target = data["targets"][0]
    assert "animal" in first_target
    assert "area" in first_target
    assert "servers" in first_target
    if first_target["servers"]:
        srv = first_target["servers"][0]
        assert "jobid" in srv
        assert "scale" in srv
        assert "join" in srv
        assert "placeId=107778070777162" in srv["join"]

def test_api_hist_endpoint(client):
    """Verifica el historial de eventos pasados."""
    res = client.get("/api/hist")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert "last" in data
    assert len(data["last"]) > 0

def test_api_login_endpoint(client):
    """Verifica la autenticación."""
    res = client.post("/api/login", json={"username": "TestUser", "password": "123"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert "token" in data
    assert data["user"]["username"] == "TestUser"

def test_api_report_egg(client):
    """Verifica la recepción de reportes en vivo de huevos."""
    report_payload = {
        "jobId": "test-job-9999",
        "placeId": 107778070777162,
        "players": 5,
        "maxPlayers": 12,
        "eggs": [
            {
                "area": "Titan Temple",
                "animal": "Godzilla",
                "scale": 15.5,
                "gen": 500000000000,
                "mutations": ["Golden", "Rainbow"],
                "claimed": False,
                "parasite": False,
                "speed": "12.0k/s",
                "money": "$850M"
            }
        ]
    }
    res = client.post("/api/report", json=report_payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True

    # Verificar que el huevo reportado está en /api/live
    res_live = client.get("/api/live")
    live_data = res_live.get_json()
    godzilla = next((t for t in live_data["targets"] if t["animal"] == "Godzilla"), None)
    assert godzilla is not None
    assert any(s["jobid"] == "test-job-9999" for s in godzilla["servers"])

def test_api_servers_endpoint(client):
    """Verifica que /api/servers devuelva la lista estructurada de servidores oficiales."""
    res = client.get("/api/servers")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "data" in data

def test_api_pets_baseline_catalog(client):
    """Verifica que el catálogo cargue las mascotas verificadas con sus atributos."""
    res = client.get("/api/pets")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] >= 200

def test_profit_calculator_api(client):
    """Verifica la fórmula GANANCIA TOTAL = BASE $/S × CANTIDAD × MUTACIÓN × TAMAÑO."""
    res = client.get("/api/calculate?base_income=100&quantity=5&mutation_mult=2.5&size_factor=1.0")
    assert res.status_code == 200
    d = res.get_json()
    assert d["success"] is True
    assert d["results"]["per_second"] == 1250.0

def test_rarity_normalization():
    """Verifica la normalización estricta de nombres de rarezas."""
    assert normalize_rarity("rare") == "Rare"
    assert normalize_rarity("  divine  ") == "Divine"
    assert normalize_rarity("SECRET") == "Secret"
    assert normalize_rarity("ETERNAL") == "Eternal"
    assert normalize_rarity("") == "Pendiente de verificación"

def test_time_synchronization_and_calibration(client):
    """Verifica la sincronización del temporizador del juego con la API."""
    from app import get_synced_game_clock
    reset_in, period, now_ms = get_synced_game_clock()
    assert 0 <= reset_in <= 300
    assert period > 0
    assert now_ms > 0

    # Enviar un reporte con reset_in específico para verificar calibración
    res = client.post("/api/report", json={
        "jobId": "test-sync-job",
        "reset_in": 142,
        "eggs": [{"area": "Void", "animal": "Unicorn", "scale": 5.0}]
    })
    assert res.status_code == 200
    
    # Comprobar que /api/live refleja la calibración cercana a 142
    live_res = client.get("/api/live")
    live_data = live_res.get_json()
    assert abs(live_data["reset_in"] - 142) <= 2
