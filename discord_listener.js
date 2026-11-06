/**
 * HuevosToons - BK RADAR Discord Channel Listener
 * Canal: 1567011919255052410
 * Escucha los mensajes y embeds de BK RADAR y los sincroniza al instante con el radar web.
 */

const { Client, GatewayIntentBits } = require('discord.js');
const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, 'discord_config.json');
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
const TARGET_CHANNEL_ID = config.channelId || "1567011919255052410";

console.log("=======================================================");
console.log(" 🥚 HUEVOSTOONS - BK RADAR DISCORD LISTENER");
console.log(` Canal objetivo: ${TARGET_CHANNEL_ID}`);
console.log("=======================================================");

function parseBkRadarEmbed(msg) {
  let eggName = null;
  let location = "Titan Temple";
  let jobId = null;
  let moneyStr = null;
  let speedStr = null;
  let rarity = "Divine";
  let color = "#fbff00";

  if (msg.embeds && msg.embeds.length > 0) {
    const emb = msg.embeds[0];
    const title = emb.title || "";
    const desc = emb.description || "";

    if (/Divine/i.test(title)) {
      rarity = "Divine";
      color = "#fbff00";
    } else if (/Eternal/i.test(title)) {
      rarity = "Eternal";
      color = "#ff1ef0";
    } else if (/Secret/i.test(title)) {
      rarity = "Secret";
      color = "#2e2e2e";
    } else if (/Cosmic/i.test(title)) {
      rarity = "Cosmic";
      color = "#38bdf8";
    }

    // 1. Egg: 🪺 **Egg:** Gorilla King
    const eggMatch = desc.match(/\*\*Egg:\*\*\s*([^\n\r]+)/i);
    if (eggMatch) eggName = eggMatch[1].trim();

    // 2. Location: 🏛️ **Location:** Titan Temple
    const locMatch = desc.match(/\*\*Location:\*\*\s*([^\n\r]+)/i);
    if (locMatch) location = locMatch[1].trim();

    // 3. Money: 💵 **Money:** ~$707m/s or ~$12b/s
    const moneyMatch = desc.match(/\*\*Money:\*\*\s*~?\$?([0-9\.]+[bBmMtT]?\/s)/i) || desc.match(/\*\*Money:\*\*\s*~?\$?([0-9\.]+[bBmMtT]?)/i);
    if (moneyMatch) moneyStr = moneyMatch[1].trim();

    // 3.5 Speed: 👟 **Recommended Speed:** 15B
    const speedMatch = desc.match(/\*\*Recommended Speed:\*\*\s*([^\n\r]+)/i);
    if (speedMatch) speedStr = speedMatch[1].trim();

    // 4. JobID: gameInstanceId=1151e158-d4b2-4dc8-9010-6e9ee8720bca
    const jobMatch = desc.match(/gameInstanceId=([0-9a-f-]{36})/i);
    if (jobMatch) jobId = jobMatch[1];
  }

  // Fallback to text content if not in embed
  if (!eggName && msg.content) {
    const eggContentMatch = msg.content.match(/\*\*([^*]+)\*\*\s+spawned/i);
    if (eggContentMatch) eggName = eggContentMatch[1].trim();
    const locContentMatch = msg.content.match(/in\s+([^!]+)!/i);
    if (locContentMatch) location = locContentMatch[1].trim();
  }

  if (!eggName) return null;

  // Multiplier / Scale calculation from money
  let scale = 12.0;
  let genNum = 100e9;
  if (moneyStr) {
    const num = parseFloat(moneyStr);
    if (/t/i.test(moneyStr)) {
      scale = +(num * 4.5 + 10).toFixed(2);
      genNum = num * 1e12;
    } else if (/b/i.test(moneyStr)) {
      scale = +(num * 1.5 + 4).toFixed(2);
      genNum = num * 1e9;
    } else if (/m/i.test(moneyStr)) {
      scale = +(num * 0.01 + 2.5).toFixed(2);
      genNum = num * 1e6;
    }
  }

  return {
    jobId: jobId || ('dc-' + Math.random().toString(16).substring(2, 10)),
    placeId: 107778070777162,
    players: Math.floor(Math.random() * 3) + 5,
    maxPlayers: 7,
    eggs: [
      {
        area: location,
        animal: eggName,
        scale: scale,
        gen: genNum,
        speed: speedStr || null,
        money: moneyStr || null,
        rarity: rarity,
        color: color,
        mutations: scale > 12 ? ["Rainbow"] : (scale > 8 ? ["Golden"] : []),
        claimed: false,
        parasite: false
      }
    ]
  };
}

async function sendToRadar(payload) {
  try {
    const res = await fetch('http://localhost:3000/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    console.log(`[Discord -> Radar] ⚡ ¡SINCRONIZADO!: ${payload.eggs[0].animal} (${payload.eggs[0].scale}x) en ${payload.eggs[0].area} | Servidor: ${payload.jobId}`);
  } catch (err) {
    console.error(`[Discord -> Radar] Error enviando al radar:`, err.message);
  }
}

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages]
});

const onReady = async () => {
  console.log(`[Discord] ✅ Conectado como: ${client.user.tag}`);
  console.log(`[Discord] 👂 Escuchando en vivo el canal: ${TARGET_CHANNEL_ID}`);

  try {
    const channel = await client.channels.fetch(TARGET_CHANNEL_ID);
    if (channel && channel.isTextBased()) {
      const messages = await channel.messages.fetch({ limit: 15 });
      console.log(`[Discord] 📥 Leyendo los últimos ${messages.size} huevos reportados...`);
      let count = 0;
      messages.forEach(msg => {
        const parsed = parseBkRadarEmbed(msg);
        if (parsed) {
          sendToRadar(parsed);
          count++;
        }
      });
      console.log(`[Discord] ✨ ${count} huevos iniciales cargados en tu página web.`);
    }
  } catch (err) {
    console.error(`[Discord] Error leyendo canal:`, err.message);
  }
};

client.on('ready', onReady);
client.on('clientReady', onReady);

client.on('messageCreate', (message) => {
  if (message.channelId === TARGET_CHANNEL_ID) {
    console.log(`[Discord] 📩 Nueva alerta recibida de ${message.author.tag}`);
    const parsed = parseBkRadarEmbed(message);
    if (parsed) {
      sendToRadar(parsed);
    }
  }
});

client.on('error', (err) => {
  console.error(`[Discord] Error:`, err.message);
});

client.login(config.token).catch(err => {
  console.error(`[Discord] Error al iniciar sesión:`, err.message);
});

module.exports = { parseBkRadarEmbed, sendToRadar };
