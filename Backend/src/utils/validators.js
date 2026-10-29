/**
 * validators.js
 * Validadores y normalizadores para los payloads enviados desde Roblox.
 */

const RARITY_THRESHOLDS = {
  Common: 0,
  Uncommon: 100,
  Rare: 500,
  Epic: 2000,
  Legendary: 10000,
  Mythic: 50000,
  Secret: 250000
};

function validateReportPayload(body) {
  if (!body || typeof body !== 'object') {
    return { valid: false, error: 'El cuerpo de la solicitud debe ser un objeto JSON.' };
  }

  const { placeId, jobId, eggs } = body;

  if (!jobId || typeof jobId !== 'string') {
    return { valid: false, error: 'jobId es obligatorio y debe ser una cadena.' };
  }

  if (!Array.isArray(eggs)) {
    return { valid: false, error: 'eggs debe ser una lista/array de huevos.' };
  }

  return { valid: true };
}

function getRarityThreshold(rarityName) {
  if (!rarityName) return RARITY_THRESHOLDS.Rare;
  return RARITY_THRESHOLDS[rarityName] !== undefined
    ? RARITY_THRESHOLDS[rarityName]
    : RARITY_THRESHOLDS.Rare;
}

module.exports = {
  validateReportPayload,
  getRarityThreshold,
  RARITY_THRESHOLDS
};

