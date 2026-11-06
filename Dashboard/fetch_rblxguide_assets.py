"""
Script para descargar imágenes oficiales en PNG/WebP y extraer datos de mascotas y timeouts
desde https://rblxguide.com/es/games/steal-an-egg/pets
"""
import os
import sys
import re
import json
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from PIL import Image
import io

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

TARGET_DIRS = [
    os.path.join(PROJECT_ROOT, "assets", "pets"),
    os.path.join(BASE_DIR, "assets", "pets"),
    os.path.join(BASE_DIR, "static", "assets", "pets")
]

for d in TARGET_DIRS:
    os.makedirs(d, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_pet_list():
    url = "https://rblxguide.com/es/games/steal-an-egg/pets"
    print(f"[*] Obteniendo lista de mascotas desde {url}...")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    
    cards = soup.find_all("a", href=lambda h: h and "/pets/" in h)
    seen = set()
    pets = []

    for c in cards:
        href = c.get("href")
        slug = href.split("/pets/")[-1].strip("/")
        if slug in seen or not slug:
            continue
        seen.add(slug)
        
        img = c.find("img")
        img_url = None
        if img:
            src = img.get("src", "")
            if "url=" in src:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(src).query)
                if "url" in qs:
                    img_url = qs["url"][0]
            elif src.startswith("http"):
                img_url = src
                
        # Si no vino url de imagen directa, inferir de supabase pattern
        if not img_url:
            img_url = f"https://tgaylapgankrdavwpebz.supabase.co/storage/v1/object/public/game-images/sae_pets/{slug}.webp"

        text = c.get_text(separator="|", strip=True)
        parts = text.split("|")
        name = parts[0] if len(parts) > 0 else slug.replace("-", " ").title()
        rarity = parts[1] if len(parts) > 1 else "Común"
        income = parts[2] if len(parts) > 2 else "$0/s"
        area = parts[3] if len(parts) > 3 else "Forest"

        pets.append({
            "slug": slug,
            "name": name,
            "rarity": rarity,
            "income": income,
            "area": area,
            "img_url": img_url,
            "detail_url": f"https://rblxguide.com/es/games/steal-an-egg/pets/{slug}"
        })

    print(f"[+] Total mascotas identificadas: {len(pets)}")
    return pets

def download_and_save_image(pet):
    slug = pet["slug"]
    img_url = pet.get("img_url")
    if not img_url:
        return False

    try:
        r = requests.get(img_url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 500:
            # Convertir a PNG con PIL para máxima calidad y compatibilidad
            image = Image.open(io.BytesIO(r.content)).convert("RGBA")
            
            # Guardar en todas las carpetas destino
            filenames = [
                f"{slug}.webp",
                f"{slug}.png",
                f"{slug.replace('-', '_')}.png",
                f"{slug.replace('-', '_')}.webp"
            ]
            
            for t_dir in TARGET_DIRS:
                for fn in filenames:
                    p = os.path.join(t_dir, fn)
                    if fn.endswith(".png"):
                        image.save(p, "PNG")
                    else:
                        with open(p, "wb") as f:
                            f.write(r.content)
            return True
    except Exception as e:
        # print(f"[-] Error descargando imagen de {slug}: {e}")
        pass
    return False

def enrich_pet_details(pet):
    """Extrae tiempo de crecimiento, huevo y velocidad requerida."""
    det_url = pet.get("detail_url")
    try:
        r = requests.get(det_url, headers=HEADERS, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(separator="|", strip=True)
            parts = text.split("|")
            for i, p in enumerate(parts):
                if "Tiempo de crecimiento" in p and i + 1 < len(parts):
                    pet["growth_time"] = parts[i+1]
                elif "Speed requerida" in p and i + 1 < len(parts):
                    pet["required_speed"] = parts[i+1]
                elif "Recompensa de Speed" in p and i + 1 < len(parts):
                    pet["speed_reward"] = parts[i+1]
                elif "Recompensa en efectivo" in p and i + 1 < len(parts):
                    pet["cash_reward"] = parts[i+1]
                elif p == "Huevo" and i + 1 < len(parts) and "Egg" in parts[i+1]:
                    pet["egg_name"] = parts[i+1]
    except Exception:
        pass
    
    # Defaults si no se obtuvieron
    if "egg_name" not in pet:
        pet["egg_name"] = f"{pet['name']} Egg"
    if "growth_time" not in pet:
        pet["growth_time"] = "5m"
    if "required_speed" not in pet:
        pet["required_speed"] = "1k"

    return pet

def main():
    pets = fetch_pet_list()
    
    print("[*] Descargando y convirtiendo imágenes PNG/WebP...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(download_and_save_image, p): p for p in pets}
        success_count = sum(1 for f in as_completed(futures) if f.result())
    print(f"[+] {success_count} imágenes descargadas y convertidas a PNG en assets/pets/")

    print("[*] Enriqueciendo mascotas clave con tiempos de crecimiento y requerimientos...")
    # Priorizar enriquecer las rarezas clave (Divine, Secret, Eternal, Rare)
    key_pets = [p for p in pets if any(r in p["rarity"].lower() for r in ["divin", "secret", "etern", "rar", "mític", "legend"])]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(enrich_pet_details, p): p for p in key_pets}
        for f in as_completed(futures):
            pass

    # Rellenar defaults para las demás
    for p in pets:
        if "growth_time" not in p:
            p["growth_time"] = "10m"
        if "egg_name" not in p:
            p["egg_name"] = f"{p['name']} Egg"
        if "required_speed" not in p:
            p["required_speed"] = "5k"

    # Guardar en pets_baseline.json
    baseline_path = os.path.join(BASE_DIR, "data", "pets_baseline.json")
    out_data = {
        "count": len(pets),
        "source": "https://rblxguide.com/es/games/steal-an-egg/pets",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": pets
    }
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
    print(f"[+] Catálogo guardado en {baseline_path} con {len(pets)} mascotas!")

if __name__ == "__main__":
    main()

