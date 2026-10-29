/**
 * index.js
 * Servidor principal Express para Steal An Egg Tracker.
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const redisService = require('./services/redisService');
const eggsRouter = require('./routes/eggsRoutes');

const app = express();
const PORT = process.env.PORT || 3000;
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

// Middlewares
app.use(cors());
app.use(express.json({ limit: '1mb' }));

// Endpoint especial para cargar directamente vía loadstring en Roblox
app.get(['/script', '/loadstring'], (req, res) => {
  const scriptPath = path.join(__dirname, '../../Client/StandaloneScript.luau');
  if (!fs.existsSync(scriptPath)) {
    return res.status(404).type('text/plain').send('-- Error: StandaloneScript.luau no encontrado');
  }

  let content = fs.readFileSync(scriptPath, 'utf8');

  // Detectar la IP o Dominio con el que el ejecutor contactó al backend
  const protocol = req.headers['x-forwarded-proto'] || req.protocol || 'http';
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  const detectedUrl = `${protocol}://${host}`;

  // Reemplazar la URL base por defecto en el script dinámicamente
  content = content.replace(
    /BACKEND_URL\s*=\s*userConfig\.BACKEND_URL\s*or\s*"[^"]*"/,
    `BACKEND_URL = userConfig.BACKEND_URL or "${detectedUrl}"`
  );

  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.send(content);
});

// Logging básico de peticiones
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[HTTP] ${req.method} ${req.originalUrl} - ${res.statusCode} (${duration}ms)`);
  });
  next();
});

// Rutas API
app.use('/api/eggs', eggsRouter);

// Ruta raíz
app.get('/', (req, res) => {
  res.json({
    app: 'Steal An Egg Tracker API',
    version: '1.0.0',
    endpoints: {
      report: 'POST /api/eggs/report',
      search: 'GET /api/eggs/search?minRarity=Rare&limit=20',
      health: 'GET /api/eggs/health'
    }
  });
});

// Inicialización del servidor
async function bootstrap() {
  await redisService.connect(REDIS_URL);

  const server = app.listen(PORT, () => {
    console.log(`===============================================`);
    console.log(`  🚀 Servidor Egg Tracker escuchando en puerto ${PORT}`);
    console.log(`  📡 URL Local: http://localhost:${PORT}`);
    console.log(`  🕒 TTL de Servidores: ${process.env.SERVER_TTL || 180} segundos`);
    console.log(`===============================================`);
  });

  // Cierre limpio
  const gracefulShutdown = async () => {
    console.log('\n[Shutdown] Cerrando servidor y conexiones...');
    server.close(async () => {
      await redisService.close();
      console.log('[Shutdown] Salida completa.');
      process.exit(0);
    });
  };

  process.on('SIGINT', gracefulShutdown);
  process.on('SIGTERM', gracefulShutdown);
}

bootstrap().catch((err) => {
  console.error('[Bootstrap Error] Fallo al iniciar servidor:', err);
});

