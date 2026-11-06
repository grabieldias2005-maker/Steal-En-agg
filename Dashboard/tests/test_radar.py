"""
Suite de pruebas automatizadas para Steal An Egg Radar
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
    """Verifica que la página principal renderice los componentes requeridos."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Steal An Egg · Radar" in html
    assert "107778070777162" in html
    assert "JOIN ↗" in html
    assert "Calculadora de rendimiento" in html
    assert "Evidencias de spawn" in html
    assert "Mejores oportunidades" in html
    assert "Contenido del servidor no disponible públicamente" in html

def test_api_servers_endpoint(client):
    """Verifica que /api/servers devuelva la lista estructurada de servidores oficiales."""
    res = client.get("/api/servers")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "data" in data
    assert "count" in data
    assert "total_players" in data

    if data["data"]:
        server = data["data"][0]
        assert "id" in server
        assert "playing" in server
        assert "maxPlayers" in server
        assert "freeSlots" in server
        assert "joinUrl" in server
        assert f"placeId={PLACE_ID}" in server["joinUrl"]
        assert server["joinUrl"].startswith("https://www.roblox.com/games/start?")

def test_api_servers_sorting(client):
    """Verifica el ordenamiento de servidores por espacios disponibles y jugadores."""
    res_free = client.get("/api/servers?sort_by=free_desc")
    assert res_free.status_code == 200
    servers = res_free.get_json().get("data", [])
    if len(servers) >= 2:
        for i in range(len(servers) - 1):
            assert servers[i]["freeSlots"] >= servers[i + 1]["freeSlots"]

def test_api_pets_baseline_catalog(client):
    """Verifica que el catálogo cargue las mascotas verificadas con sus atributos."""
    res = client.get("/api/pets")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] >= 200
    
    first = data["data"][0]
    assert "name" in first
    assert "rarity" in first
    assert "income" in first
    assert "origin_egg" in first
    assert "mutations_supported" in first

def test_strict_four_rarities_filtering(client):
    """
    Verifica que el filtro acepte estrictamente las 4 rarezas:
    Rare, Divine, Secret, Eternal y el grupo de las cuatro.
    """
    for rarity in ["rare", "divine", "secret", "eternal"]:
        res = client.get(f"/api/pets?rarity={rarity}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        for p in data["data"]:
            assert p["rarity"].lower() == rarity

    # Grupo de las 4 rarezas combinadas
    res_all_targets = client.get("/api/pets?rarity=all_target")
    assert res_all_targets.status_code == 200
    data_all = res_all_targets.get_json()
    valid_targets = {"Rare", "Divine", "Secret", "Eternal"}
    for p in data_all["data"]:
        assert p["rarity"] in valid_targets

def test_pets_search_and_egg_filter(client):
    """Verifica la búsqueda por nombre de mascota y filtro por huevo de origen."""
    res_search = client.get("/api/pets?search=chicken")
    assert res_search.status_code == 200
    pets = res_search.get_json()["data"]
    assert any("chicken" in p["name"].lower() for p in pets)

    res_egg = client.get("/api/pets?egg=forest")
    assert res_egg.status_code == 200
    pets_forest = res_egg.get_json()["data"]
    assert len(pets_forest) > 0
    for p in pets_forest:
        assert "forest" in p["origin_egg"].lower()

def test_profit_calculator_api(client):
    """
    Verifica la fórmula:
    GANANCIA TOTAL = BASE $/S × CANTIDAD × MUTACIÓN × TAMAÑO
    """
    # Caso 1: 5 mascotas de $100/s, Golden (x2.5), tamaño 1.0 -> 5 * 100 * 2.5 * 1.0 = 1250/s
    res = client.get("/api/calculate?base_income=100&quantity=5&mutation_mult=2.5&size_factor=1.0")
    assert res.status_code == 200
    d = res.get_json()
    assert d["success"] is True
    assert d["results"]["per_second"] == 1250.0
    assert d["results"]["per_minute"] == 1250.0 * 60
    assert d["results"]["per_hour"] == 1250.0 * 3600
    assert d["results"]["per_day"] == 1250.0 * 86400

    # Caso 2: Rainbow (x3.5) con tamaño x2.0
    res2 = client.post("/api/calculate", json={
        "base_income": 1000,
        "quantity": 2,
        "mutation_mult": 3.5,
        "size_factor": 2.0
    })
    assert res2.status_code == 200
    d2 = res2.get_json()
    # 1000 * 2 * 3.5 * 2.0 = 14000/s
    assert d2["results"]["per_second"] == 14000.0

def test_spawn_evidence_api(client):
    """Verifica que el endpoint de evidencia comunitaria responda con los registros y series observadas."""
    res = client.get("/api/spawn-evidence")
    assert res.status_code in (200, 502)
    if res.status_code == 200:
        d = res.get_json()
        assert "records" in d or "intervalSeries" in d

def test_best_opportunities_api(client):
    """Verifica la sección de mejores oportunidades por rareza y huevos top."""
    res = client.get("/api/best-opportunities")
    assert res.status_code == 200
    d = res.get_json()
    assert d["success"] is True
    assert "top_by_rarity" in d
    assert "Rare" in d["top_by_rarity"]
    assert "Divine" in d["top_by_rarity"]
    assert "Secret" in d["top_by_rarity"]
    assert "Eternal" in d["top_by_rarity"]
    assert "top_eggs" in d
    assert "server_telemetry_notice" in d

def test_rarity_normalization():
    """Verifica la normalización estricta de nombres de rarezas."""
    assert normalize_rarity("rare") == "Rare"
    assert normalize_rarity("  divine  ") == "Divine"
    assert normalize_rarity("SECRET") == "Secret"
    assert normalize_rarity("ETERNAL") == "Eternal"
    assert normalize_rarity("") == "Pendiente de verificación"
    assert normalize_rarity(None) == "Pendiente de verificación"

def test_currency_formatting():
    """Verifica el formateo numérico con sufijos K, M, B."""
    assert format_currency_per_second(500) == "$500/s"
    assert format_currency_per_second(1500) == "$1.50K/s"
    assert format_currency_per_second(2500000) == "$2.50M/s"
    assert format_currency_per_second(3500000000) == "$3.50B/s"

