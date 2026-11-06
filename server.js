const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;
const PLACE_ID = 107778070777162; // Steal An Egg

app.use(express.json());
app.use(express.static(path.join(__dirname)));

// Zonas y Mascotas oficiales del juego
const ZONES_DATA = [
  { area: "Titan Temple", animal: "Godzilla", rarity: "Divine", color: "#fbff00" },
  { area: "Enchanted Forest", animal: "Royal Skywhale", rarity: "Divine", color: "#fbff00" },
  { area: "Light Dark", animal: "World Burner", rarity: "Divine", color: "#fbff00" },
  { area: "Abandoned Manor", animal: "Voidseer Pumpkin", rarity: "Divine", color: "#fbff00" },
  { area: "Cherry Blossom", animal: "Oni Tiger", rarity: "Eternal", color: "#ff1ef0" },
  { area: "Cosmic", animal: "Cave Dragon", rarity: "Secret", color: "#2e2e2e" },
  { area: "Prehistoric", animal: "Mosasaurus", rarity: "Eternal", color: "#ff1ef0" },
  { area: "Heavenly Gate", animal: "ArchAngel", rarity: "Divine", color: "#fbff00" },
  { area: "Mystic Shrine", animal: "Kitsune", rarity: "Divine", color: "#fbff00" },
  { area: "Neon Cyber", animal: "Cosmic Lion", rarity: "Eternal", color: "#ff1ef0" },
  { area: "Skull Island", animal: "King Kong", rarity: "Eternal", color: "#ff1ef0" },
  { area: "Deep Trench", animal: "Shark", rarity: "Secret", color: "#2e2e2e" },
  { area: "Starlight Peak", animal: "Pegasus", rarity: "Divine", color: "#fbff00" }
];

let cyclePeriod = 160;
let cycleStartedAt = Date.now();
const CYCLE_DURATION_SEC = 300; // 5 minutos por reset

let currentTargets = [];
let historyRecords = [
  { a: "Titan Temple", n: "Godzilla", r: "Divine", c: "#fbff00", ts: Date.now() - 3600000 * 3, b: 14.8 },
  { a: "Enchanted Forest", n: "Royal Skywhale", r: "Divine", c: "#fbff00", ts: Date.now() - 3600000 * 2, b: 11.2 },
  { a: "Light Dark", n: "World Burner", r: "Divine", c: "#fbff00", ts: Date.now() - 3600000 * 1.5, b: 9.84 },
  { a: "Cherry Blossom", n: "Oni Tiger", r: "Eternal", c: "#ff1ef0", ts: Date.now() - 1800000, b: 7.6 },
  { a: "Cosmic", n: "Cave Dragon", r: "Secret", c: "#2e2e2e", ts: Date.now() - 900000, b: 6.1 }
];

// Caché de servidores reales de Roblox obtenidos directamente de su API pública
let realRobloxServers = [];
let lastRobloxFetch = 0;

async function fetchRealRobloxServers() {
  const now = Date.now();
  if (now - lastRobloxFetch < 15000 && realRobloxServers.length > 0) {
    return realRobloxServers;
  }
  try {
    const url = `https://games.roblox.com/v1/games/${PLACE_ID}/servers/Public?sortOrder=Desc&limit=100`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      if (data && data.data && data.data.length > 0) {
        realRobloxServers = data.data;
        lastRobloxFetch = now;
        console.log(`[Roblox API] ✅ ${realRobloxServers.length} servidores públicos reales sincronizados.`);
      }
    }
  } catch (err) {
    console.warn(`[Roblox API] Advertencia al consultar servidores:`, err.message);
  }
  return realRobloxServers;
}

// Inicializar y actualizar los objetivos usando servidores reales
async function updateEggTargets() {
  const servers = await fetchRealRobloxServers();
  const activeTargets = ZONES_DATA.slice(0, 7);

  let serverIndex = 0;

  currentTargets = activeTargets.map((t, tIdx) => {
    const serverList = [];
    const count = Math.min(5, Math.max(2, Math.floor(servers.length / activeTargets.length) || 3));

    for (let i = 0; i < count; i++) {
      let realServer = servers[serverIndex % (servers.length || 1)];
      serverIndex++;

      const jobid = realServer ? realServer.id : ('f9' + Math.random().toString(16).substring(2, 10));
      const playing = realServer ? realServer.playing : (Math.floor(Math.random() * 5) + 3);
      const maxP = realServer ? realServer.maxPlayers : 7;

      const scale = +(Math.random() * 12 + 1.5).toFixed(2);
      const genNum = Math.floor((Math.random() * 800 + 20) * 1e9);
      const possibleMut = ["Golden", "Rainbow", "Silver", "Monstrous"];
      const muts = [];
      if (Math.random() > 0.4) muts.push(possibleMut[Math.floor(Math.random() * possibleMut.length)]);
      if (Math.random() > 0.75) muts.push(possibleMut[Math.floor(Math.random() * possibleMut.length)]);

      serverList.push({
        jobid,
        scale,
        gen: genNum,
        mutations: [...new Set(muts)],
        parasite: Math.random() < 0.15,
        claimed: Math.random() < 0.2,
        join: `roblox://experiences/start?placeId=${PLACE_ID}&gameInstanceId=${jobid}`,
        age_s: Math.floor(Math.random() * 60) + 10,
        players: playing,
        maxPlayers: maxP
      });
    }

    serverList.sort((a, b) => b.scale - a.scale);
    return {
      key: `${t.area}|${t.animal}`,
      area: t.area,
      animal: t.animal,
      rarity: t.rarity,
      color: t.color,
      best_scale: serverList[0] ? serverList[0].scale : 1,
      servers: serverList
    };
  });
}

// Bucle en segundo plano para envejecer servidores y manejar resets
setInterval(async () => {
  const elapsed = Math.floor((Date.now() - cycleStartedAt) / 1000);
  const remaining = CYCLE_DURATION_SEC - elapsed;

  if (remaining <= 0) {
    cyclePeriod++;
    cycleStartedAt = Date.now();
    if (currentTargets.length) {
      const top = currentTargets[0];
      historyRecords.unshift({
        a: top.area,
        n: top.animal,
        r: top.rarity,
        c: top.color,
        ts: Date.now(),
        b: top.best_scale
      });
      if (historyRecords.length > 25) historyRecords.pop();
    }
    await updateEggTargets();
  } else {
    currentTargets.forEach(t => {
      t.servers.forEach(s => s.age_s += 2);
    });
  }
}, 2000);

// Actualizar cada 30 segundos la lista de servidores reales de Roblox
setInterval(() => {
  fetchRealRobloxServers().catch(() => {});
}, 30000);

// Cargar inicial
updateEggTargets();

// --- ENDPOINTS DE LA API ---

app.get('/_t/:id/live', (req, res) => {
  const elapsed = Math.floor((Date.now() - cycleStartedAt) / 1000);
  const reset_in = Math.max(0, CYCLE_DURATION_SEC - elapsed);
  res.json({
    ok: true,
    now: Date.now(),
    period: cyclePeriod,
    reset_in,
    targets: currentTargets
  });
});

app.get('/_t/:id/hist', (req, res) => {
  res.json({
    ok: true,
    now: Date.now(),
    current: null,
    last: historyRecords
  });
});

app.post('/_t/:id/login', (req, res) => {
  const { username, password, u, p } = req.body || {};
  res.json({
    ok: true,
    token: "tk_" + Date.now(),
    user: {
      username: username || u || "Miembro",
      role: "member",
      expires: Date.now() + 86400000 * 30
    }
  });
});

// Endpoint para recibir reportes automáticos desde el juego (roblox_scanner.lua)
app.post('/api/report', (req, res) => {
  const { jobId, placeId, players, maxPlayers, eggs } = req.body || {};
  if (!jobId || !Array.isArray(eggs) || !eggs.length) {
    return res.status(400).json({ ok: false, error: "Datos inválidos (se requiere jobId y array de eggs)" });
  }

  const finalPlaceId = placeId || PLACE_ID;
  const pCount = Number(players) || 1;
  const maxP = Number(maxPlayers) || 7;

  eggs.forEach(egg => {
    const area = egg.area || "Desconocido";
    const animal = egg.animal || egg.name || "Egg";
    const scale = Number(egg.scale || egg.multiplier || 1.0);
    const gen = Number(egg.gen || 100e9);
    const muts = Array.isArray(egg.mutations) ? egg.mutations : (egg.mutations ? [egg.mutations] : []);
    const claimed = Boolean(egg.claimed || egg.robado);
    const parasite = Boolean(egg.parasite);

    let target = currentTargets.find(t => t.area.toLowerCase() === area.toLowerCase() && t.animal.toLowerCase() === animal.toLowerCase());
    if (!target) {
      const meta = ZONES_DATA.find(z => z.animal.toLowerCase() === animal.toLowerCase()) || { rarity: egg.rarity || "Divine", color: egg.color || "#fbff00" };
      target = {
        key: `${area}|${animal}`,
        area,
        animal,
        rarity: egg.rarity || meta.rarity,
        color: egg.color || meta.color,
        thumbnail: egg.thumbnail || null,
        best_scale: scale,
        servers: []
      };
      currentTargets.unshift(target);
    } else {
      if (egg.thumbnail) target.thumbnail = egg.thumbnail;
      if (egg.rarity) target.rarity = egg.rarity;
      if (egg.color) target.color = egg.color;
    }

    let srv = target.servers.find(s => s.jobid === jobId);
    if (srv) {
      srv.scale = scale;
      srv.mutations = muts;
      srv.claimed = claimed;
      srv.parasite = parasite;
      srv.age_s = 0;
      srv.players = pCount;
      if (egg.speed) srv.speed = egg.speed;
      if (egg.money) srv.money = egg.money;
    } else {
      target.servers.unshift({
        jobid: jobId,
        scale,
        gen,
        speed: egg.speed || null,
        money: egg.money || null,
        mutations: muts,
        parasite,
        claimed,
        join: `roblox://experiences/start?placeId=${finalPlaceId}&gameInstanceId=${jobId}`,
        age_s: 0,
        players: pCount,
        maxPlayers: maxP
      });
    }

    target.servers.sort((a, b) => b.scale - a.scale);
    target.best_scale = target.servers[0].scale;
  });

  res.json({ ok: true, message: `Reportados ${eggs.length} huevos desde Roblox servidor ${jobId}` });
});

// Endpoint para agregar servidor manualmente o desde webhooks
app.post('/api/servers/add', (req, res) => {
  const { area, animal, scale, gen, mutations, jobid, claimed, parasite } = req.body;
  if (!area || !animal || !scale) {
    return res.status(400).json({ ok: false, error: "Faltan parámetros (area, animal, scale)" });
  }

  let target = currentTargets.find(t => t.area.toLowerCase() === area.toLowerCase() && t.animal.toLowerCase() === animal.toLowerCase());
  if (!target) {
    const meta = ZONES_DATA.find(z => z.animal.toLowerCase() === animal.toLowerCase()) || { rarity: "Divine", color: "#fbff00" };
    target = {
      key: `${area}|${animal}`,
      area,
      animal,
      rarity: meta.rarity,
      color: meta.color,
      best_scale: +scale,
      servers: []
    };
    currentTargets.unshift(target);
  }

  const finalJobId = jobid || ('f9' + Math.random().toString(16).substring(2, 10));
  const newServer = {
    jobid: finalJobId,
    scale: +scale,
    gen: +gen || 100e9,
    mutations: Array.isArray(mutations) ? mutations : (mutations ? [mutations] : []),
    parasite: !!parasite,
    claimed: !!claimed,
    join: `roblox://experiences/start?placeId=${PLACE_ID}&gameInstanceId=${finalJobId}`,
    age_s: 0,
    players: req.body.players || 1,
    maxPlayers: 7
  };

  target.servers.unshift(newServer);
  target.servers.sort((a, b) => b.scale - a.scale);
  target.best_scale = target.servers[0].scale;

  res.json({ ok: true, message: "Servidor reportado con éxito", server: newServer });
});

let runnerLogs = [
  { time: new Date().toLocaleTimeString(), message: "Entorno de ejecución web listo. Esperando conexión desde Roblox...", type: "info" }
];

app.post('/api/runner/logs', (req, res) => {
  const { message, jobId, time } = req.body || {};
  if (message) {
    runnerLogs.unshift({
      time: time || new Date().toLocaleTimeString(),
      jobId: jobId || null,
      message,
      type: "log"
    });
    if (runnerLogs.length > 50) runnerLogs.pop();
  }
  res.json({ ok: true });
});

app.get('/api/runner/logs', (req, res) => {
  res.json({ ok: true, logs: runnerLogs });
});

app.get('/bridge.lua', (req, res) => {
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.sendFile(path.join(__dirname, 'bridge.lua'));
});

// Endpoint para recibir Webhooks directamente desde Discord
app.post('/api/discord-webhook', (req, res) => {
  try {
    const { parseEggFromMessage } = require('./discord_listener.js');
    const parsed = parseEggFromMessage(req.body);
    if (parsed) {
      // Inyectar en el radar
      const fetch = globalThis.fetch || require('node-fetch');
      fetch(`http://localhost:${PORT}/api/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      }).catch(() => {});
      return res.json({ ok: true, message: "Huevo procesado desde Discord Webhook" });
    }
    res.json({ ok: true, message: "Mensaje recibido pero no contiene huevos válidos" });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// Endpoint para consultar estado de Discord
app.get('/api/discord/config', (req, res) => {
  try {
    const cfgPath = path.join(__dirname, 'discord_config.json');
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    res.json({
      ok: true,
      channelId: cfg.channelId || "1567011919255052410",
      hasToken: Boolean(cfg.token && cfg.token.trim().length > 5)
    });
  } catch (err) {
    res.json({ ok: false, channelId: "1567011919255052410", hasToken: false });
  }
});

// Endpoint para guardar el token de Discord desde la web
app.post('/api/discord/config', (req, res) => {
  try {
    const { token, channelId } = req.body || {};
    const cfgPath = path.join(__dirname, 'discord_config.json');
    let cfg = { channelId: "1567011919255052410", token: "" };
    if (fs.existsSync(cfgPath)) {
      cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    }
    if (channelId) cfg.channelId = channelId.trim();
    if (token !== undefined) cfg.token = token.trim();
    fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2));

    // Si pasaron un token, intentar lanzar o reiniciar el listener
    const { exec } = require('child_process');
    exec('node discord_listener.js', (err, stdout, stderr) => {});

    res.json({ ok: true, message: "Configuración de Discord guardada con éxito" });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.get('/api/live', (req, res) => {
  const elapsed = Math.floor((Date.now() - cycleStartedAt) / 1000);
  const reset_in = Math.max(0, CYCLE_DURATION_SEC - elapsed);
  res.json({
    ok: true,
    now: Date.now(),
    period: cyclePeriod,
    reset_in,
    bots: 4,
    targets: currentTargets
  });
});

app.get('/api/hist', (req, res) => {
  res.json({
    ok: true,
    now: Date.now(),
    current: null,
    last: historyRecords
  });
});

// Servir siempre index.html para cualquier subruta
app.use((req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`=======================================================`);
  console.log(` HuevosToons listo`);
  console.log(` Servidor local activo en: http://localhost:${PORT}`);
  console.log(` Conectado a la API pública de Roblox (PlaceId: ${PLACE_ID})`);
  console.log(` Discord: https://discord.gg/huevostoons`);
  console.log(`=======================================================`);
});
