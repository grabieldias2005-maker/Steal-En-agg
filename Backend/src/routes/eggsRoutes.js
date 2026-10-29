/**
 * eggsRoutes.js
 * Enrutador de Express para telemetría y consultas de servidores.
 */

const express = require('express');
const router = express.Router();
const redisService = require('../services/redisService');
const { validateReportPayload, getRarityThreshold } = require('../utils/validators');

const SERVER_TTL = parseInt(process.env.SERVER_TTL, 10) || 180;

/**
 * POST /api/eggs/report
 * Recibe reportes en lotes emitidos por clientes Luau en juego.
 */
router.post('/report', async (req, res) => {
  const validation = validateReportPayload(req.body);
  if (!validation.valid) {
    return res.status(400).json({ error: validation.error });
  }

  const { placeId, jobId, serverRegion, reportTimestamp, eggs } = req.body;

  try {
    let highestValue = 0;
    let bestEggName = 'Unknown Egg';

    // Determinar el huevo de mayor valor en el lote reportado
    if (eggs.length > 0) {
      for (const egg of eggs) {
        const val = Number(egg.value) || 0;
        if (val >= highestValue) {
          highestValue = val;
          bestEggName = egg.name || bestEggName;
        }
      }
    }

    const serverData = {
      placeId: placeId || 0,
      jobId,
      serverRegion: serverRegion || 'Global',
      reportTimestamp: reportTimestamp || Math.floor(Date.now() / 1000),
      highestValue,
      bestEggName,
      eggCount: eggs.length,
      eggs
    };

    await redisService.saveServer(jobId, serverData, SERVER_TTL);

    return res.status(200).json({
      status: 'ok',
      message: 'Telemetría registrada exitosamente.',
      trackedCount: eggs.length,
      highestValue
    });
  } catch (err) {
    console.error('[EggsRoute] Error procesando reporte:', err);
    return res.status(500).json({ error: 'Error interno del servidor procesando reporte.' });
  }
});

/**
 * GET /api/eggs/search
 * Consulta servidores que cumplen con el filtro de rareza mínima.
 */
router.get('/search', async (req, res) => {
  try {
    const minRarity = req.query.minRarity || 'Rare';
    const limit = Math.min(parseInt(req.query.limit, 10) || 20, 50);
    const threshold = getRarityThreshold(minRarity);

    const servers = await redisService.searchServers(threshold, limit);
    return res.status(200).json(servers);
  } catch (err) {
    console.error('[EggsRoute] Error buscando servidores:', err);
    return res.status(500).json({ error: 'Error interno al consultar servidores.' });
  }
});

/**
 * GET /api/eggs/health
 * Verificación de estado del servicio.
 */
router.get('/health', (req, res) => {
  res.json({
    status: 'online',
    timestamp: new Date().toISOString(),
    redisConnected: redisService.isRedisConnected
  });
});

module.exports = router;

