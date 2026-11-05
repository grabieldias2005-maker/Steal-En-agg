# Publicar el radar en Render

El radar web está en la carpeta `Dashboard/` y usa la API pública de servidores de Roblox para mostrar servidores disponibles y generar enlaces JOIN.

## Publicación
1. Entra en https://dashboard.render.com/ y crea una cuenta o inicia sesión.
2. Selecciona **New + → Blueprint**.
3. Conecta el repositorio `grabieldias2005-maker/Steal-En-agg`.
4. Render detectará el archivo `render.yaml` de la raíz. Revisa el servicio `steal-an-egg-radar` y selecciona **Apply**.
5. Espera a que termine el despliegue. Render mostrará una URL pública con dominio `.onrender.com`.

## Configuración incluida
- Directorio de la aplicación: `Dashboard/`
- Instalación: `pip install -r requirements.txt`
- Inicio: `gunicorn app:app`
- Comprobación: `/health`

## Límites
La web muestra servidores públicos y su cantidad de jugadores. Roblox no incluye información sobre los huevos que aparecen dentro de cada servidor en este listado público; la detección real de huevos requiere una fuente de telemetría autorizada del juego. El botón JOIN intenta abrir la instancia pública, pero el servidor puede llenarse o cerrarse antes de entrar.

El plan gratuito de Render puede suspender servicios inactivos y tardar en despertarlos.
