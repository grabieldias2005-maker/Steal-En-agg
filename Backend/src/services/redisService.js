/**
 * redisService.js
 * Servicio de almacenamiento y expiración automática (TTL) en Redis
 * con fallback transparente en memoria para desarrollo local sin Redis.
 */

const redis = require('redis');

class RedisService {
  constructor() {
    this.client = null;
    this.isRedisConnected = false;
    this.memoryStore = new Map(); // Fallback en memoria si Redis no está activo
    this.ttlTimers = new Map();
  }

  async connect(redisUrl = 'redis://localhost:6379') {
    try {
      this.client = redis.createClient({
        url: redisUrl,
        socket: {
          connectTimeout: 3000,
          reconnectStrategy: (retries) => {
            if (retries > 3) {
              console.warn('[RedisService] Límite de reconexiones alcanzado. Manteniendo almacenamiento en memoria.');
              return false;
            }
            return Math.min(retries * 500, 2000);
          }
        }
      });

      this.client.on('error', (err) => {
        if (!this.isRedisConnected) {
          // Silencioso durante intento inicial
        } else {
          console.error('[RedisService] Error en Redis:', err.message);
        }
      });

      await this.client.connect();
      this.isRedisConnected = true;
      console.log('[RedisService] Conectado exitosamente a Redis en:', redisUrl);
    } catch (error) {
      this.isRedisConnected = false;
      console.warn('[RedisService] No se pudo conectar a Redis. Modo fallback en memoria activado automáticamente.');
    }
  }

  /**
   * Guarda o actualiza el estado de un servidor de Roblox con expiración TTL.
   */
  async saveServer(jobId, serverData, ttlSeconds = 180) {
    const key = `server:${jobId}`;
    const serialized = JSON.stringify(serverData);

    if (this.isRedisConnected && this.client) {
      await this.client.set(key, serialized, { EX: ttlSeconds });
    } else {
      // Fallback en memoria
      this.memoryStore.set(key, {
        data: serialized,
        expiresAt: Date.now() + ttlSeconds * 1000
      });

      if (this.ttlTimers.has(key)) {
        clearTimeout(this.ttlTimers.get(key));
      }

      const timer = setTimeout(() => {
        this.memoryStore.delete(key);
        this.ttlTimers.delete(key);
      }, ttlSeconds * 1000);

      this.ttlTimers.set(key, timer);
    }
  }

  /**
   * Obtiene la lista de servidores activos filtrados por valor mínimo y ordenados descendente.
   */
  async searchServers(minThreshold = 0, limit = 20) {
    const results = [];
    const now = Date.now();

    if (this.isRedisConnected && this.client) {
      const keys = await this.client.keys('server:*');
      for (const key of keys) {
        const raw = await this.client.get(key);
        if (!raw) continue;
        const ttl = await this.client.ttl(key);
        const parsed = JSON.parse(raw);

        if (parsed.highestValue >= minThreshold) {
          results.push({
            jobId: key.replace('server:', ''),
            placeId: parsed.placeId,
            region: parsed.serverRegion || 'Global',
            highestValue: parsed.highestValue,
            bestEggName: parsed.bestEggName,
            eggCount: parsed.eggCount,
            lastReportTime: parsed.reportTimestamp,
            timeLeft: ttl > 0 ? ttl : 0
          });
        }
      }
    } else {
      // Fallback en memoria
      for (const [key, entry] of this.memoryStore.entries()) {
        if (entry.expiresAt <= now) {
          this.memoryStore.delete(key);
          continue;
        }

        const parsed = JSON.parse(entry.data);
        const timeLeft = Math.max(0, Math.floor((entry.expiresAt - now) / 1000));

        if (parsed.highestValue >= minThreshold) {
          results.push({
            jobId: key.replace('server:', ''),
            placeId: parsed.placeId,
            region: parsed.serverRegion || 'Global',
            highestValue: parsed.highestValue,
            bestEggName: parsed.bestEggName,
            eggCount: parsed.eggCount,
            lastReportTime: parsed.reportTimestamp,
            timeLeft
          });
        }
      }
    }

    // Ordenar de mayor valor a menor valor
    results.sort((a, b) => b.highestValue - a.highestValue);
    return results.slice(0, limit);
  }

  async close() {
    if (this.isRedisConnected && this.client) {
      await this.client.quit();
    }
    for (const timer of this.ttlTimers.values()) {
      clearTimeout(timer);
    }
    this.memoryStore.clear();
  }
}

module.exports = new RedisService();

