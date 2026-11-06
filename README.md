# Steal An Egg Radar & Tracker 🥚

Sistema integral para el juego de Roblox **"Steal An Egg"** (PlaceId: `107778070777162`).
Incluye:
1. **Radar Web & Dashboard (`Dashboard/`)**: Aplicación Python + Flask lista para Render con radar en vivo de servidores públicos de Roblox, botón JOIN seguro, catálogo comunitario de 265+ mascotas con filtros estrictos de 4 rarezas (`Rare`, `Divine`, `Secret`, `Eternal`), calculadora de ganancias, evidences de spawn e historial de notificaciones.
2. **Client Luau (`Client/`)**: Módulos para escaneo local e inyección en Roblox Studio o ejecutores.
3. **Backend API (`Backend/` & `Backend_Python/`)**: Servidores Node.js (Express + Redis) y Python (FastAPI).

---

## 📁 Estructura del Proyecto

```text
Steal-En-agg/
├── Dashboard/                  # Dashboard Web Principal (Python + Flask para Render)
│   ├── app.py                  # Servidor Flask, APIs (/api/servers, /api/pets, /api/calculate, etc.) y UI
│   ├── requirements.txt        # Dependencias (Flask, requests, gunicorn, beautifulsoup4, pytest)
│   ├── render.yaml             # Definición de despliegue como Blueprint en Render
│   ├── data/
│   │   └── pets_baseline.json  # Catálogo verificado de 265 mascotas (RBLX Guide & GrindMath)
│   ├── tests/
│   │   └── test_radar.py       # Suite de pruebas automatizadas con pytest (12 pruebas)
│   └── README.md               # Guía específica del Dashboard
│
├── Client/                     # Scripts y módulos para el cliente Luau (Roblox)
│   ├── Modules/
│   │   ├── Config.luau         # Umbrales de rareza, URLs y alias de propiedades
│   │   ├── EggDetector.luau    # Monitoreo reactivo de Workspace con .ChildAdded
│   │   └── NetworkManager.luau # Cola por lotes (debounce) y comunicación HTTP
│   ├── Interface/
│   │   └── UIController.luau   # Interfaz gráfica (Rayfield / Fallback) y TeleportService
│   ├── Main.luau               # Punto de entrada modular (Roblox Studio / LocalScript)
│   └── StandaloneScript.luau   # Script monolítico "listo para pegar" en ejecutores
│
├── Backend/                    # Servidor REST central en Node.js + Express + Redis
│   ├── src/
│   │   ├── index.js            # Punto de entrada del servidor
│   │   ├── routes/eggsRoutes.js# Rutas POST /report y GET /search
│   │   ├── services/redisService.js # TTL automático (con fallback en memoria)
│   │   └── utils/validators.js # Validación de payloads y mapeo de rarezas
│   ├── package.json
│   └── ...
│
├── Backend_Python/             # Alternativa de backend en Python (FastAPI)
│   ├── app.py
│   └── requirements.txt
│
├── render.yaml                 # Configuración de despliegue raíz para Render (Dashboard)
└── README.md
```

---

## 🚀 Inicio Rápido con el Dashboard Web (Render)

El servicio principal de producción es el **Dashboard** en Python + Flask:

```bash
cd Dashboard
pip install -r requirements.txt
python app.py
```
Abre tu navegador en `http://localhost:10000` para acceder al Radar de servidores, catálogo con filtros de 4 rarezas y calculadora.

Para ejecutar las pruebas:
```bash
pytest Dashboard/tests/test_radar.py -v
```

---

## 1. Detección y Lectura de Datos Local (Luau)

- **Inspección de Jerarquía:**
  `EggDetector.luau` utiliza un algoritmo de búsqueda adaptativo. Revisa carpetas conocidas (`Eggs`, `SpawnedEggs`, `MapEggs`, `DroppedEggs`) y busca coincidencias por nombre o atributos.
- **Extracción de Propiedades:**
  La función `extractProperty` examina:
  1. **Attributes nativos de Roblox** (`instance:GetAttribute("Rarity")`).
  2. **ValueObjects hijos** (`StringValue`, `IntValue`, `NumberValue`).
  3. **BillboardGuis / TextLabels** que el juego suele proyectar sobre el huevo.
  4. Nombres del modelo (inferencia heurística si contiene palabras clave).
- **Rendimiento:**
  Usa `.ChildAdded` y `.ChildRemoved` sobre el contenedor específico en lugar de bucles `while task.wait()` o escaneo continuo de todo el Workspace, protegiendo los FPS del juego.

### 🛠️ ¿Cómo adaptar las rutas si el juego actualiza sus nombres?
Abre [`Client/Modules/Config.luau`](file:///c:/Users/SANTANA/Documents/Steal%20An%20egg%20scripte/Client/Modules/Config.luau) (o el bloque `CONFIG` en `StandaloneScript.luau`):
- Si cambian la carpeta contenedora en Workspace, agrégala en `EGG_FOLDER_CANDIDATES`:
  ```lua
  Config.EGG_FOLDER_CANDIDATES = {
      "NombreDeNuevaCarpeta",
      "Eggs",
      ...
  }
  ```
- Si cambian los nombres de las propiedades o valores del huevo, agrégalos en `PROPERTY_ALIASES`:
  ```lua
  Config.PROPERTY_ALIASES = {
      Rarity = {"NuevaPropiedadRareza", "Rarity", "Tier"},
      Value  = {"NuevoMultiplicador", "Value", "Price"},
      Name   = {"NuevoNombreHuevo", "Name"}
  }
  ```

---

## 2. Comunicación y Telemetría (Cliente -> Backend)

- **Manejo de Ratelimits:**
  `NetworkManager.luau` agrupa los huevos detectados en una cola en memoria y los envía mediante un temporizador de debounce (`REPORT_COOLDOWN = 3s`). No satura el canal HTTP ni dispara bloqueos de red.
- **Estructura del Payload JSON:**
  ```json
  {
    "placeId": 123456789,
    "jobId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "serverRegion": "US",
    "reportTimestamp": 1730200000,
    "eggs": [
      {
        "id": "uuid-12345",
        "name": "Golden Dragon Egg",
        "rarity": "Legendary",
        "value": 15000,
        "spawnTime": 1730199990
      }
    ]
  }
  ```

---

## 3. Backend & Base de Datos (Node.js o Python)

### Opción A: Node.js (Recomendada)
1. Entra a la carpeta del backend:
   ```bash
   cd Backend
   npm install
   npm start
   ```
2. **Características:**
   - Si Redis está activo en `localhost:6379`, utiliza claves con expiración (`EX: 180s`).
   - **Fallback automático:** Si Redis no está instalado o activo, el servidor conmuta a un almacén en memoria con temporizadores automáticos sin caerse ni generar errores.

### Opción B: Python (FastAPI)
1. Entra a la carpeta:
   ```bash
   cd Backend_Python
   pip install -r requirements.txt
   python app.py
   ```

---

## 4. Interfaz Gráfica (UI) y Server Hopping

- **Librería Rayfield:**
  Proporciona una ventana moderna con:
  - **Dropdown de Rareza Mínima:** Filtra servidores según el tipo de huevo (desde `Common` hasta `Secret`).
  - **Lista de Servidores Activos:** Muestra nombre del mejor huevo, valor formateado (ej. `15.0K`, `1.2M`) y tiempo restante del TTL (`TTL: 140s`).
  - **Botón "Join":** Invoca `TeleportService:TeleportToPlaceInstance(placeId, jobId, LocalPlayer)` para transferir al jugador inmediatamente al servidor deseado.
- **Uso directo:**
  Para usar todo el sistema en un solo archivo sin dependencias de módulos de Studio, copia y pega el código de [`Client/StandaloneScript.luau`](file:///c:/Users/SANTANA/Documents/Steal%20An%20egg%20scripte/Client/StandaloneScript.luau).

