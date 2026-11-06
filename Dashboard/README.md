# Steal An Egg Radar — Dashboard & API

Radar web oficial y catálogo comunitario para el juego de Roblox **Steal An Egg** (PlaceId: `107778070777162`).
Desarrollado en Python + Flask para despliegue en Render y ejecución local.

---

## 🚀 Características Principales

1. **Radar de Servidores Públicos Oficiales (`/api/servers`)**:
   - Consulta en vivo mediante la API de Roblox (`https://games.roblox.com/v1/games/107778070777162/servers/Public`).
   - Muestra JobId, jugadores actuales, capacidad máxima, espacios libres, ping y FPS.
   - Ordenación por espacios disponibles, mayor cantidad de jugadores, menor cantidad o latencia.
   - Auto-actualización cada 30 segundos con control de caché en memoria (15s) para evitar límites HTTP 429 de Roblox.
   - Manejo de reintentos con botón manual y mensajes informativos.

2. **Botón JOIN Verificado**:
   - Enlace oficial estándar: `https://www.roblox.com/games/start?placeId=107778070777162&gameInstanceId=JOB_ID`.
   - Soporte para Deep Link directo en la aplicación: `roblox://placeId=107778070777162&gameInstanceId=JOB_ID`.
   - Modal de validación de seguridad contra inyecciones en JobId.
   - Aviso de conexión: no se confirma la entrada hasta que el cliente de Roblox finalice la conexión.

3. **Catálogo de Mascotas y Huevos (`/api/pets`)**:
   - 265+ mascotas comunitarias con base de datos tolerante a fallos (`data/pets_baseline.json`).
   - Fuentes comunitarias integradas: **RBLX Guide**, **GrindMath** y **Steal An Egg Wiki**.
   - Muestra nombre, rareza, huevo o bioma de origen, ganancia base $/s, peso base en kg, valor estimado y mutaciones soportadas.
   - Botón directo **"Ver huevo"** en cada mascota que filtra automáticamente todas las mascotas que eclosionan de ese mismo huevo o bioma.
   - Si un dato no está en las fuentes comunitarias, se etiqueta estrictamente como *"No disponible"* sin invención de datos.

4. **Filtros Estrictos de Rareza**:
   - Filtros exclusivos para las 4 rarezas objetivo requeridas:
     - 💎 **Rare**
     - 👑 **Divine**
     - 🔮 **Secret**
     - ⚡ **Eternal**
     - ✨ **Las 4 rarezas combinadas**
   - Normalización robusta de mayúsculas, minúsculas y espacios. Las rarezas desconocidas o no verificadas no se incluyen sin evidencia comprobada.

5. **Calculadora de Ganancias (`/api/calculate`)**:
   - Fórmula verificada: `GANANCIA TOTAL = BASE $/S × CANTIDAD × MULTIPLICADOR MUTACIÓN × FACTOR TAMAÑO`.
   - Desglose simultáneo por segundo, por minuto, por hora y por día.
   - Mutaciones soportadas: Normal (×1.0), Silver (×1.2), Bloom (×1.25), Golden (×2.5), Fractured/Scrambled (×2.75), Parasite (×3.0), Rainbow (×3.5).
   - Comparador interactivo lado a lado de **Mascota A vs Mascota B** con cálculo automático de diferencia porcentual de rendimiento.

6. **Detector de Evidencias de Spawn (`/api/spawn-evidence`)**:
   - Consulta el registro público comunitario `terrencerun/steal-an-egg-research/data/spawn-evidence.json`.
   - Estadísticas del intervalo mediano de 300 segundos (rango observado de 293 a 307 s en directo continuo).
   - Estimador interactivo de 5 minutos con alertas visuales y sonoras en la ventana comunitaria.
   - **Nota de transparencia técnica:** Roblox no ofrece una API pública que reporte los objetos internos generados en el Workspace de cada servidor. Los servidores muestran con claridad: *"Contenido del servidor no disponible públicamente"*.

7. **Sección "Mejores Oportunidades" (`/api/best-opportunities`)**:
   - Clasificación de las 5 mejores mascotas por $/s en cada una de las 4 rarezas.
   - Ranking de huevos y biomas con mayor concentración de mascotas de alta rareza.

8. **Notificaciones del Navegador**:
   - Integración nativa con la API `Notification` del navegador.
   - Filtro de alertas por rareza y aviso de la ventana de ciclo.
   - Historial de notificaciones en sesión con prevención estricta de duplicados.

9. **Diseño Visual Futurista**:
   - Paleta moderna en modo oscuro: fondo azul marino espacial (`#070d19`), tarjetas translúcidas, acentos en azul eléctrico (`#3b82f6`) y púrpura neón (`#8b5cf6`).
   - Diseño completamente responsive adaptable a computadoras y teléfonos móviles.

---

## 🛠️ Ejecución Local

1. Clona el repositorio e ingresa al directorio `Dashboard`:
   ```bash
   cd Dashboard
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecuta la aplicación Flask:
   ```bash
   python app.py
   ```
   La aplicación se iniciará en `http://localhost:10000` (o el puerto configurado en la variable `PORT`).

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una suite completa de pruebas con `pytest`:

```bash
pytest tests/test_radar.py -v
```

Cubre los 12 aspectos críticos del sistema:
- Health check y validación del PlaceId (`107778070777162`).
- Renderizado de la interfaz HTML y componentes interactivos.
- Consumo y formateo de servidores públicos oficiales de Roblox.
- Algoritmos de ordenación por espacios disponibles y jugadores.
- Carga de catálogo de mascotas y tolerancia a fallos.
- Filtros estrictos de las 4 rarezas (`Rare`, `Divine`, `Secret`, `Eternal`).
- Búsqueda por texto y filtrado por huevo de origen.
- Fórmula matemática de la calculadora de ganancias.
- Parseo de evidencias comunitarias de spawn.
- Clasificación de mejores oportunidades.
- Normalización de cadenas de texto y sufijos numéricos (K, M, B).

---

## ☁️ Despliegue en Render (Paso a Paso)

El repositorio incluye un archivo de infraestructura como código `render.yaml` listo para despliegue con un clic:

1. Inicia sesión en tu cuenta de [Render Dashboard](https://dashboard.render.com/).
2. Haz clic en **New +** y selecciona **Blueprint**.
3. Conecta tu repositorio de GitHub: `https://github.com/grabieldias2005-maker/Steal-En-agg`.
4. Render detectará automáticamente `render.yaml`:
   - **Service Name**: `steal-an-egg-radar`
   - **Runtime**: `Python`
   - **Root Directory**: `Dashboard`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Health Check Path**: `/health`
5. Haz clic en **Apply**. Render compilará las dependencias y desplegará el servicio en una URL pública del tipo:
   `https://steal-an-egg-radar.onrender.com`.
