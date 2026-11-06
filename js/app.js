/**
 * HuevosToons - Live Egg Radar Tracker
 * Clone of https://egg.report/eggstoons
 */
(function () {
  "use strict";

  const PET_IMAGES = {
    "Godzilla": "assets/pets/godzilla.png",
    "Royal Skywhale": "assets/pets/royal_skywhale.png",
    "World Burner": "assets/pets/world_burner.png",
    "Voidseer Pumpkin": "assets/pets/voidseer_pumpkin.png",
    "Oni Tiger": "assets/pets/oni_tiger.png",
    "Cave Dragon": "assets/pets/cave_dragon.png",
    "Mosasaurus": "assets/pets/mosasaurus.png",
    "ArchAngel": "assets/pets/archangel.png",
    "Kitsune": "assets/pets/kitsune.png",
    "Unicorn": "assets/pets/unicorn.png",
    "Cosmic Lion": "assets/pets/cosmic_lion.png",
    "Eternal Lunar Dragon": "assets/pets/eternal_lunar_dragon.png",
    "King Kong": "assets/pets/king_kong.png",
    "Gorilla King": "assets/pets/gorilla_king.png",
    "Pure Jellyfish": "assets/pets/pure_jellyfish.png",
    "Celestial Sunlion": "assets/pets/celestial_sunlion.webp",
    "Gargoyle": "assets/pets/gargoyle.png",
    "Aetheron": "assets/pets/aetheron.png",
    "Pegasus": "assets/pets/pegasus.png",
    "Skeleton Horse": "assets/pets/skeleton_horse.png",
    "Alien Skeleton Boss": "assets/pets/alien_skeleton_boss.png",
    "Centaur": "assets/pets/centaur.png",
    "Cosmic Fox": "assets/pets/cosmic_fox.png",
    "RazorFang": "assets/pets/razorfang.png",
    "Shark": "assets/pets/shark.png",
    "Stag": "assets/pets/stag.png"
  };

  function getPetImage(target) {
    if (!target) return "assets/logo.png";
    if (target.image && !target.image.includes("eggstock")) return target.image;
    const name = target.animal || target.name || "";
    if (PET_IMAGES[name]) return PET_IMAGES[name];
    if (target.thumbnail && !target.thumbnail.includes("eggstock")) return target.thumbnail;

    const slug = name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const under = name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    return `assets/pets/${slug}.png`;
  }

  const RARITY_COLORS = {
    "Divine": "#fbff00",
    "Eternal": "#ff1ef0",
    "Secret": "#2e2e2e",
    "Cosmic": "#38bdf8",
    "Mythic": "#ef4444",
    "Legendary": "#f97316"
  };

  const UFO_SVG = '<svg class="ufo-ic" viewBox="0 0 44 26" aria-hidden="true"><path class="ufo-beam" d="M17.6 21.2h8.8L35 42H9z" fill="url(#eggrUfoBeam)"/>'
    + '<ellipse cx="22" cy="10.6" rx="8" ry="7.6" fill="url(#eggrUfoDome)"/><path d="M17.2 7.9c.9-1.8 2.6-3 4.6-3.2" fill="none" stroke="#fff" stroke-width="1.3" stroke-linecap="round" opacity=".9"/>'
    + '<ellipse cx="22" cy="15.3" rx="19.5" ry="5.4" fill="url(#eggrUfoHull)"/><ellipse cx="22" cy="14" rx="18.6" ry="3" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width=".6"/>'
    + '<ellipse cx="22" cy="20.3" rx="7.2" ry="2.3" fill="#3a4354"/><ellipse class="ufo-core" cx="22" cy="21" rx="4.6" ry="1.25" fill="#c8ff7a"/>'
    + '<g class="ufo-lights" fill="#a6ff4d"><circle cx="6.6" cy="16.5" r="1.25"/><circle cx="10.1" cy="17.6" r="1.25"/><circle cx="16.7" cy="18.3" r="1.25"/><circle cx="27.3" cy="18.3" r="1.25"/><circle cx="33.9" cy="17.6" r="1.25"/><circle cx="37.4" cy="16.5" r="1.25"/></g></svg>';

  const ICONS = {
    clock: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7.5V12l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    filter: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><path d="M3 5h18v2.2L14 14v6l-4-2v-4L3 7.2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>',
    bell: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><path d="M18 16v-5a6 6 0 1 0-12 0v5l-2 2v1h16v-1l-2-2zM10 20a2 2 0 0 0 4 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>',
    bellOff: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><path d="M13.7 3.3a6 6 0 0 0-7.7 7.7M6 16l-2 2v1h14M10 20a2 2 0 0 0 4 0M2 2l20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    dice: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><rect x="3" y="3" width="18" height="18" rx="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="8" cy="8" r="1.5" fill="currentColor"/><circle cx="16" cy="16" r="1.5" fill="currentColor"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/><circle cx="16" cy="8" r="1.5" fill="currentColor"/><circle cx="8" cy="16" r="1.5" fill="currentColor"/></svg>',
    popout: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><path d="M14 3h7v7M21 3l-9 9M5 7H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-1" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    discord: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><path d="M20.3 4.4A19.8 19.8 0 0 0 15.3 3a13.6 13.6 0 0 0-.6 1.3 18.3 18.3 0 0 0-5.4 0A13.5 13.5 0 0 0 8.7 3a19.7 19.7 0 0 0-5 1.4C1 8.4.3 16.3 1.4 20a19.9 19.9 0 0 0 6 3 14.8 14.8 0 0 0 1.3-2.1c-.7-.3-1.4-.6-2-.9l.5-.4a14.2 14.2 0 0 0 12.6 0l.5.4c-.6.3-1.3.6-2 .9.4.7.8 1.4 1.3 2.1a19.9 19.9 0 0 0 6-3c1.3-4.4.2-12.3-2.3-15.6zm-11.8 12c-1.2 0-2.1-1.1-2.1-2.4s.9-2.4 2.1-2.4c1.3 0 2.2 1.1 2.1 2.4s-1 2.4-2.1 2.4zm7 0c-1.2 0-2.1-1.1-2.1-2.4s1-2.4 2.1-2.4 2.2 1.1 2.1 2.4c0 1.3-.9 2.4-2.1 2.4z" fill="currentColor"/></svg>',
    user: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><circle cx="12" cy="7" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M4 21v-2a6 6 0 0 1 12 0v2" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    bug: '<svg viewBox="0 0 24 24" aria-hidden="true" width="14" height="14"><path d="M12 7c-3 0-5 2.4-5 6 0 3.3 2.2 6 5 6s5-2.7 5-6c0-3.6-2-6-5-6z" fill="currentColor"/><path d="M9 4l2 3M15 4l-2 3M4 10l3 1M20 10l-3 1M4 16l3-1M20 16l-3-1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    arrowUp: '<svg viewBox="0 0 24 24" aria-hidden="true" width="14" height="14"><path d="M12 19V5M5 12l7-7 7 7" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    arrowDown: '<svg viewBox="0 0 24 24" aria-hidden="true" width="14" height="14"><path d="M12 5v14M5 12l7 7 7-7" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    plus: '<svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16"><path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    close: '<svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18"><path d="M18 6L6 18M6 6l12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
  };

  // State
  let session = localStorage.getItem("eggr.session") ? JSON.parse(localStorage.getItem("eggr.session")) : null;
  let view = "live"; // "live" | "history"
  let sortKey = "scale"; // "scale" | "gen" | "recent" | "rare"
  let sortDir = -1; // -1 desc, 1 asc
  let showRobados = true;
  let filterHide = JSON.parse(localStorage.getItem("eggr.filterHide") || "[]");
  let activeSheet = null; // null | "filters" | "alerts" | "add_server"
  let targets = [];
  let historyList = [];
  let resetIn = 300;
  let targetResetTimestamp = null;
  let pollTimer = null;
  let clockOff = 0;
  let audioCtx = null;
  let lastSpawnCount = 0;

  // Alerts Settings
  let alerts = JSON.parse(localStorage.getItem("eggr.alerts") || JSON.stringify({
    on: true,
    sound: "classic",
    volume: 70,
    min: 0,
    ufo: true,
    ufoLead: 60,
    notify: false
  }));

  function saveAlerts() {
    localStorage.setItem("eggr.alerts", JSON.stringify(alerts));
  }

  // Audio Synthesizer (Zero external dependencies, identical to egg.report tones)
  const TONES = {
    classic: [[880, 0, .12], [1175, .14, .12], [1568, .28, .22]],
    soft: [[660, 0, .25], [880, .22, .35]],
    bell: [[1318, 0, .6], [1760, 0, .5], [988, .05, .7]],
    alarm: [[1046, 0, .12], [784, .15, .12], [1046, .3, .12], [784, .45, .12], [1046, .6, .2]]
  };

  function getAudioCtx() {
    if (!audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) audioCtx = new AC();
    }
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    return audioCtx;
  }

  function playAlert(kind = "classic") {
    if (!alerts.on || alerts.sound === "none") return;
    const toneType = kind || alerts.sound || "classic";
    const notes = TONES[toneType] || TONES.classic;
    const ctx = getAudioCtx();
    if (!ctx) return;

    const vol = (alerts.volume || 70) / 100;
    const gainNode = ctx.createGain();
    gainNode.gain.value = 0.35 * vol;
    gainNode.connect(ctx.destination);

    const now = ctx.currentTime;
    notes.forEach(n => {
      const osc = ctx.createOscillator();
      const env = ctx.createGain();
      osc.type = toneType === "alarm" ? "square" : "sine";
      osc.frequency.value = n[0];

      env.gain.setValueAtTime(0, now + n[1]);
      env.gain.linearRampToValueAtTime(1, now + n[1] + 0.015);
      env.gain.exponentialRampToValueAtTime(0.001, now + n[1] + n[2]);

      osc.connect(env);
      env.connect(gainNode);
      osc.start(now + n[1]);
      osc.stop(now + n[1] + n[2] + 0.05);
    });
  }

  // Desktop Web Notification
  function sendDesktopNotification(title, body) {
    if (!alerts.notify || !("Notification" in window) || Notification.permission !== "granted") return;
    try {
      new Notification(title, {
        body: body,
        icon: "assets/logo.png"
      });
    } catch(e) {}
  }

  // Toast System
  function showToast(title, desc = "") {
    const cont = document.getElementById("toasts");
    if (!cont) return;
    const t = document.createElement("div");
    t.className = "toast";
    t.innerHTML = `<b>${esc(title)}</b>${desc ? `<small>${esc(desc)}</small>` : ""}`;
    cont.appendChild(t);
    setTimeout(() => {
      t.style.opacity = "0";
      t.style.transform = "translateY(10px)";
      setTimeout(() => t.remove(), 250);
    }, 2800);
  }

  function copyToClipboard(text, customToast = "Copiado al portapapeles") {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => showToast(customToast, text));
    } else {
      const input = document.createElement("input");
      input.value = text;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      showToast(customToast, text);
    }
  }

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, c => "&#" + c.charCodeAt(0) + ";");
  }

  function fmtMult(val) {
    const n = Number(val) || 0;
    return "x" + n.toFixed(2);
  }

  function fmtGen(n) {
    if (!n) return "";
    if (n >= 1e12) return (n / 1e12).toFixed(2) + "T";
    if (n >= 1e9) return (n / 1e9).toFixed(0) + "B";
    if (n >= 1e6) return (n / 1e6).toFixed(0) + "M";
    return n.toLocaleString();
  }

  function fmtAge(sec) {
    const s = Math.max(0, Math.floor(sec));
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}m ${rem}s`;
  }

  function ageColor(sec) {
    const t = Math.min(1, Math.max(0, (sec || 0) / 300));
    const hue = Math.round(t < 0.5 ? 140 - 160 * t : 100 - 100 * t);
    return `hsl(${hue}, 85%, 60%)`;
  }

  function fmtTime(sec) {
    const s = Math.max(0, Math.floor(sec));
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m < 10 ? "0" : ""}${m}:${rem < 10 ? "0" : ""}${rem}`;
  }

  function ufoTime(now) {
    const UFO_EVERY = 1800000; // 30 min
    const UFO_LEN = 300000;    // 5 min
    const since = (now % UFO_EVERY + UFO_EVERY) % UFO_EVERY;
    return { since, left: UFO_EVERY - since, live: since < UFO_LEN };
  }

  // App Initialization
  function init() {
    setupSvgGradients();
    if (!session) {
      renderLogin();
    } else {
      renderApp();
      startPolling();
    }
  }

  function setupSvgGradients() {
    if (document.getElementById("eggrUfoDefs")) return;
    const d = document.createElement("div");
    d.id = "eggrUfoDefs";
    d.className = "ufo-defs";
    d.setAttribute("aria-hidden", "true");
    d.innerHTML = `<svg width="0" height="0" focusable="false"><defs>
      <radialGradient id="eggrUfoDome" cx="38%" cy="30%" r="78%">
        <stop offset="0" stop-color="#f6e6ff"/>
        <stop offset=".33" stop-color="#cb94ff"/>
        <stop offset=".7" stop-color="#9447ec"/>
        <stop offset="1" stop-color="#5a1daa"/>
      </radialGradient>
      <linearGradient id="eggrUfoHull" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#f2f6fa"/>
        <stop offset=".5" stop-color="#b5c0cf"/>
        <stop offset="1" stop-color="#5f6b7c"/>
      </linearGradient>
      <linearGradient id="eggrUfoBeam" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#c8ff7a" stop-opacity=".9"/>
        <stop offset=".55" stop-color="#8cff4a" stop-opacity=".35"/>
        <stop offset="1" stop-color="#8cff4a" stop-opacity="0"/>
      </linearGradient>
    </defs></svg>`;
    document.body.appendChild(d);
  }

  // --- LOGIN SCREEN ---
  function renderLogin(errorMsg = "") {
    clearInterval(pollTimer);
    document.body.classList.remove("has-bg");
    const appEl = document.getElementById("app");
    appEl.innerHTML = `
      <div class="login has-bg" style="background-image: url('assets/background.png')">
        <div class="lcard">
          <img class="lg" src="assets/logo.png" alt="HuevosToons Logo">
          <h1>Acceso privado</h1>
          <p>Entra con el usuario y la clave que te dieron para ver el radar en vivo.</p>
          <form id="loginForm" autocomplete="on">
            <label>
              Usuario
              <input id="loginUser" type="text" name="username" value="Miembro" placeholder="Tu usuario" required>
            </label>
            <label>
              Clave
              <input id="loginPass" type="password" name="password" value="huevostoons" placeholder="Tu contraseña" required>
            </label>
            <button class="btn main" id="loginBtn" type="submit">Entrar</button>
            <button class="btn" id="guestBtn" type="button" style="margin-top: 8px; width: 100%;">
              ⚡ Entrar en Modo Demo / Invitado
            </button>
          </form>
          ${errorMsg ? `<div class="msg error" style="margin-top: 12px; color: #ff6b6b;">${esc(errorMsg)}</div>` : ""}
          <a class="btn" href="https://discord.gg/huevostoons" target="_blank" rel="noopener noreferrer" style="margin-top: 18px; width: 100%;">
            ${ICONS.discord} <span>DISCORD DE HUEVOSTOONS.</span>
          </a>
        </div>
      </div>
    `;

    document.getElementById("loginForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const u = document.getElementById("loginUser").value.trim();
      const p = document.getElementById("loginPass").value.trim();
      doLogin(u, p);
    });

    document.getElementById("guestBtn").addEventListener("click", () => {
      doLogin("Invitado", "demo");
    });
  }

  function doLogin(username, password) {
    session = {
      username: username || "Miembro",
      token: "tk_" + Date.now(),
      loggedAt: Date.now()
    };
    localStorage.setItem("eggr.session", JSON.stringify(session));
    showToast("¡Bienvenido a HuevosToons!", `Sesión iniciada como ${session.username}`);
    renderApp();
    startPolling();
  }

  function doLogout() {
    session = null;
    localStorage.removeItem("eggr.session");
    renderLogin();
  }

  // --- MAIN APP SHELL ---
  function renderApp() {
    document.body.classList.add("has-bg");
    document.documentElement.style.setProperty("--bg-img", 'url("assets/background.png")');

    const appEl = document.getElementById("app");
    appEl.innerHTML = `
      <header class="top">
        <div class="top-in">
          <div class="brand">
            <img src="assets/logo.png" alt="HuevosToons">
            <div class="brand-t">
              <b>HuevosToons.</b>
              <small>Discord: https://discord.gg/huevostoons</small>
            </div>
          </div>
          <div class="cyc">
            <small>Próximo reset</small>
            <b id="cnt">05:00</b>
          </div>
          <div class="act">
            <span class="bots" id="botsn">4 bots buscando</span>
            <a class="btn" href="https://discord.gg/huevostoons" target="_blank" rel="noopener noreferrer">
              ${ICONS.discord} <span>DISCORD</span>
            </a>
            <button class="btn" id="userBtn" type="button" title="Perfil y salir">
              ${ICONS.user} <span><b>${esc(session.username)}</b></span>
            </button>
          </div>
        </div>
        <div class="track"><i id="fill" style="width: 0%;"></i></div>
      </header>

      <!-- UFO Event Band -->
      <div class="ufo-w">
        <div class="ufo" id="ufo">
          ${UFO_SVG}
          <b class="ufo-n" id="ufoN">UFO</b>
          <i class="ufo-s" id="ufoS"></i>
          <span class="ufo-t" id="ufoT">--:--</span>
          <button type="button" class="ufo-bell" id="ufoBell" title="Alertas de UFO">
            ${alerts.ufo ? ICONS.bell : ICONS.bellOff}
          </button>
        </div>
      </div>

      <!-- Navigation & Action Bar -->
      <div class="bar">
        <div class="tabs">
          <button type="button" class="${view === 'live' ? 'on' : ''}" data-view="live">En vivo</button>
          <button type="button" class="${view === 'history' ? 'on' : ''}" data-view="history">Historial</button>
        </div>

        <span id="livebar" class="bar" style="margin: 0; padding: 0; flex: 1;">
          <button class="btn" id="filterBtn" type="button">
            ${ICONS.filter} <span>Filtros</span>
            <i class="n" id="fltn" ${filterHide.length ? '' : 'hidden'}>${filterHide.length}</i>
          </button>

          <div class="seg" id="sortGroup">
            <button type="button" class="${sortKey === 'gen' ? 'on' : ''}" data-sort="gen">Generación</button>
            <button type="button" class="${sortKey === 'scale' ? 'on' : ''}" data-sort="scale">Tamaño</button>
            <button type="button" class="${sortKey === 'recent' ? 'on' : ''}" data-sort="recent">Reciente</button>
            <button type="button" class="${sortKey === 'rare' ? 'on' : ''}" data-sort="rare">Raro</button>
            <button type="button" class="dir" id="sortDirBtn" title="Cambiar dirección">
              ${sortDir === -1 ? ICONS.arrowDown : ICONS.arrowUp}
            </button>
          </div>

          <button class="btn ${showRobados ? 'on' : ''}" id="robadosToggle" type="button">
            Robados
          </button>

          <button class="btn" id="addServerBtn" type="button" title="Reportar o agregar servidor de prueba">
            ${ICONS.plus} <span>Reportar Huevo</span>
          </button>

          <button class="btn" id="discordConfigBtn" type="button" title="Conexión Discord (Canal: 1567011919255052410)">
            ${ICONS.discord} <span>Discord (1567011919255052410)</span>
          </button>

          <button class="btn" id="runnerBtn" type="button" title="Entorno de Ejecución y Consola del Script" style="border-color: rgba(255, 194, 26, 0.4); color: var(--accent);">
            ⚡ <span>Entorno de Ejecución</span>
          </button>

          <span class="gap"></span>

          <button class="btn" id="alertsBtn" type="button" title="Configurar Alertas">
            ${ICONS.bell} <span>Alertas</span>
          </button>

          <button class="btn main" id="randomServerBtn" type="button">
            ${ICONS.dice} <span>Servidor aleatorio</span>
          </button>
        </span>
      </div>

      <!-- Main Content -->
      <main id="content"></main>

      <!-- Toast Containers & Sheet Drawer -->
      <div class="toasts" id="toasts"></div>
      <div id="sheetCont"></div>
    `;

    bindHeaderEvents();
    renderContent();
  }

  function bindHeaderEvents() {
    // Tab switching
    document.querySelectorAll(".tabs button").forEach(btn => {
      btn.addEventListener("click", () => {
        view = btn.dataset.view;
        document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b === btn));
        renderContent();
      });
    });

    // Sorting
    document.querySelectorAll("#sortGroup button[data-sort]").forEach(btn => {
      btn.addEventListener("click", () => {
        sortKey = btn.dataset.sort;
        document.querySelectorAll("#sortGroup button[data-sort]").forEach(b => b.classList.toggle("on", b === btn));
        renderContent();
      });
    });

    const dirBtn = document.getElementById("sortDirBtn");
    if (dirBtn) {
      dirBtn.addEventListener("click", () => {
        sortDir = sortDir === -1 ? 1 : -1;
        dirBtn.innerHTML = sortDir === -1 ? ICONS.arrowDown : ICONS.arrowUp;
        renderContent();
      });
    }

    // Robados toggle
    const robToggle = document.getElementById("robadosToggle");
    if (robToggle) {
      robToggle.addEventListener("click", () => {
        showRobados = !showRobados;
        robToggle.classList.toggle("on", showRobados);
        renderContent();
      });
    }

    // Filters sheet
    document.getElementById("filterBtn").addEventListener("click", () => openSheet("filters"));

    // Alerts sheet
    document.getElementById("alertsBtn").addEventListener("click", () => openSheet("alerts"));

    // Add server modal
    document.getElementById("addServerBtn").addEventListener("click", () => openSheet("add_server"));

    // Discord modal
    const dcBtn = document.getElementById("discordConfigBtn");
    if (dcBtn) dcBtn.addEventListener("click", () => openSheet("discord"));

    // Runner modal
    const rnBtn = document.getElementById("runnerBtn");
    if (rnBtn) rnBtn.addEventListener("click", () => openSheet("runner"));

    // Random server
    document.getElementById("randomServerBtn").addEventListener("click", joinRandomServer);

    // UFO Bell
    document.getElementById("ufoBell").addEventListener("click", () => {
      alerts.ufo = !alerts.ufo;
      saveAlerts();
      document.getElementById("ufoBell").innerHTML = alerts.ufo ? ICONS.bell : ICONS.bellOff;
      showToast(alerts.ufo ? "Alertas de UFO activadas" : "Alertas de UFO silenciadas");
    });

    // User logout
    document.getElementById("userBtn").addEventListener("click", () => {
      if (confirm(`Sesión iniciada como ${session.username}.\n¿Deseas cerrar sesión?`)) {
        doLogout();
      }
    });
  }

  // --- CONTENT RENDERING ---
  function renderContent() {
    const mainEl = document.getElementById("content");
    if (!mainEl) return;

    if (view === "history") {
      renderHistoryView(mainEl);
    } else {
      renderLiveView(mainEl);
    }
  }

  function renderLiveView(container) {
    if (!targets.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; color: var(--muted);">
          <div class="egg" style="display:inline-block; margin-bottom: 14px;"></div>
          <p style="font-size: 16px;">Buscando huevos en los servidores...</p>
        </div>
      `;
      return;
    }

    // Filter targets
    let visibleTargets = targets.filter(t => !filterHide.includes(t.key));

    // Sort targets
    visibleTargets.sort((a, b) => {
      if (sortKey === "scale") {
        return (b.best_scale - a.best_scale) * sortDir;
      }
      if (sortKey === "gen") {
        const genA = (a.servers[0] && a.servers[0].gen) || 0;
        const genB = (b.servers[0] && b.servers[0].gen) || 0;
        return (genB - genA) * sortDir;
      }
      if (sortKey === "rare") {
        const order = { "Divine": 5, "Eternal": 4, "Secret": 3, "Cosmic": 2, "Mythic": 1 };
        return ((order[b.rarity] || 0) - (order[a.rarity] || 0)) * sortDir;
      }
      if (sortKey === "recent") {
        const ageA = (a.servers[0] && a.servers[0].age_s) || 999;
        const ageB = (b.servers[0] && b.servers[0].age_s) || 999;
        return (ageA - ageB) * sortDir;
      }
      return 0;
    });

    let html = '<div class="cards">';
    visibleTargets.forEach(t => {
      let svList = t.servers;
      if (!showRobados) {
        svList = svList.filter(s => !s.claimed);
      }
      if (!svList.length) return;

      const petImg = getPetImage(t);
      const rarColor = t.color || RARITY_COLORS[t.rarity] || "#ffc21a";
      const best = t.best_scale || (svList[0] && svList[0].scale) || 1;
      const bestGen = svList[0] && svList[0].gen;

      html += `
        <div class="card" style="--zone-color: ${rarColor}">
          <div class="zone">
            <i style="background: ${rarColor}"></i>
            <span>${esc(t.area)}</span>
          </div>
          <div class="tt">
            <div class="tn">
              <img class="pet" src="${petImg}" alt="${esc(t.animal)}" onerror="this.onerror=null; this.src='assets/logo.png';" style="filter: drop-shadow(0 0 10px ${rarColor}66);">
              <div style="min-width: 0">
                <h2 class="nm" style="color: ${rarColor}">${esc(t.animal)}</h2>
                <div class="mt">
                  <span>${esc(t.rarity)}</span>
                  <span>${svList.length} ${svList.length === 1 ? 'servidor' : 'servidores'}</span>
                  ${t.growth_time ? `<span title="Tiempo de eclosión / crecimiento (RBLX Guide)">🥚 ${esc(t.growth_time)}</span>` : ""}
                  ${t.required_speed ? `<span title="Velocidad requerida para robar (RBLX Guide)">⚡ ${esc(t.required_speed)}</span>` : ""}
                </div>
              </div>
            </div>
            ${best ? `
              <div class="best">
                <small>mayor</small>
                <b>${fmtMult(best)}</b>
                ${bestGen ? `<span class="gen-chip">${fmtGen(bestGen)}</span>` : ""}
              </div>
            ` : ""}
          </div>

          <div class="rows">
            ${svList.map(s => renderServerRow(s, best)).join("")}
          </div>
        </div>
      `;
    });
    html += '</div>';

    container.innerHTML = html;
    bindRowEvents();
  }

  function renderServerRow(s, maxScale) {
    const fillPercent = Math.min(100, Math.round((s.scale / Math.max(maxScale, 1)) * 100));
    const isRobado = !!s.claimed;
    const isParasite = !!s.parasite;

    // Sincronización continua de la edad del servidor con el reloj del cliente
    const now = Date.now();
    const spawnMs = s.spawn_ts || (now - (s.age_s || 0) * 1000);
    const ageSec = Math.max(0, Math.floor((now - spawnMs) / 1000));

    // Timeout del servidor exactamente sincronizado con el contador regresivo de la página
    const timeoutSec = targetResetTimestamp != null
      ? Math.max(0, Math.round((targetResetTimestamp - now) / 1000))
      : (s.timeout_in != null ? s.timeout_in : resetIn);

    const color = ageColor(ageSec);

    return `
      <div class="row ${isRobado ? 'is-robado' : ''}">
        <div class="row-bar" style="width: ${fillPercent}%;"></div>

        <div class="m" title="Multiplicador">
          <b>${fmtMult(s.scale)}</b>
        </div>

        <div class="chips">
          ${(s.mutations || []).map(m => {
            const low = m.toLowerCase();
            return `<span class="mut mut-${low}">${esc(m.toUpperCase())}</span>`;
          }).join("")}

          ${isRobado ? `<span class="mut mut-robado">ROBADO</span>` : ""}
          ${isParasite ? `<span class="mut mut-parasite" title="Parásito">${ICONS.bug} PARASITE</span>` : ""}
          ${s.gen ? `<span class="chip-gen">Gen ${fmtGen(s.gen)}</span>` : ""}
          ${s.speed ? `<span class="chip-speed" title="Velocidad Recomendada">👟 ${esc(s.speed)}</span>` : ""}
          ${s.money ? `<span class="chip-money" title="Ingresos Estimados">💵 ${esc(s.money)}</span>` : ""}
          <span class="chip-users" title="Jugadores en servidor">${s.players || 4}/${s.maxPlayers || 12}</span>
          <span class="chip-age" data-spawn="${spawnMs}" title="Tiempo activo en el servidor" style="color: ${color}; font-weight: 600;">⏱️ <b class="val-age">${fmtAge(ageSec)}</b></span>
          <span class="chip-timeout" title="Tiempo restante antes del próximo reset de servidores" style="color: ${timeoutSec <= 40 ? '#f87171' : 'var(--muted)'};">⏳ <b class="val-timeout">${fmtTime(timeoutSec)}</b></span>
        </div>

        <div class="act">
          <button class="join" type="button" data-join="${esc(s.join)}" data-jobid="${esc(s.jobid)}" title="Unirse vía Roblox o copiar enlace">
            JOIN
          </button>
        </div>
      </div>
    `;
  }

  function renderHistoryView(container) {
    if (!historyList.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; color: var(--muted);">
          <p>No hay registros históricos recientes aún.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="history-container" style="max-width: 900px; margin: 20px auto; padding: 0 16px;">
        <h3 style="margin-bottom: 16px; font-family: var(--font); color: var(--accent);">Historial de Resets y Apariciones</h3>
        <div class="history-list">
          ${historyList.map(h => {
            const petImg = getPetImage({ animal: h.n, thumbnail: h.thumbnail });
            const timeAgo = fmtAge(Math.floor((Date.now() - (h.ts || Date.now())) / 1000));
            return `
              <div class="history-item" style="display:flex; align-items:center; gap:14px; background:var(--surface); border:1px solid var(--line); border-radius:var(--r); padding:12px 16px; margin-bottom:10px;">
                <img src="${petImg}" alt="${esc(h.n)}" onerror="this.onerror=null; this.src='assets/logo.png';" style="width:40px; height:40px; object-fit:contain;">
                <div style="flex:1;">
                  <b style="display:block; font-size:16px; color:${h.c || '#fff'};">${esc(h.n)}</b>
                  <small style="color:var(--muted);">${esc(h.a)} · ${esc(h.r || 'Divine')}</small>
                </div>
                <div style="text-align:right;">
                  <b style="color:var(--accent); font-size:18px;">${fmtMult(h.b)}</b>
                  <small style="display:block; color:var(--muted);">${timeAgo}</small>
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }

  function bindRowEvents() {
    document.querySelectorAll(".join").forEach(btn => {
      btn.addEventListener("click", () => {
        const joinUrl = btn.dataset.join;
        const jobid = btn.dataset.jobid;
        // Attempt deep link and copy
        copyToClipboard(joinUrl, "Enlace de Roblox copiado");
        try {
          window.location.href = joinUrl;
        } catch(e) {}
      });
    });
  }

  function joinRandomServer() {
    const allServers = [];
    targets.forEach(t => {
      t.servers.forEach(s => {
        if (!s.claimed) allServers.push(s);
      });
    });

    if (!allServers.length) {
      showToast("No hay servidores disponibles en este momento");
      return;
    }

    // Pick a high-tier server
    allServers.sort((a, b) => b.scale - a.scale);
    const topPool = allServers.slice(0, Math.min(3, allServers.length));
    const chosen = topPool[Math.floor(Math.random() * topPool.length)];

    copyToClipboard(chosen.join, `Uniéndose a servidor con ${fmtMult(chosen.scale)}`);
    window.location.href = chosen.join;
  }

  // --- SLIDING SHEETS (FILTROS / ALERTAS / REPORTAR) ---
  function openSheet(kind) {
    activeSheet = kind;
    const cont = document.getElementById("sheetCont");
    if (!cont) return;

    let bodyHtml = "";
    let titleHtml = "";

    if (kind === "filters") {
      titleHtml = "Filtros de Radar";
      bodyHtml = `
        <div class="grp">
          <h4>Huevos Visibles (${targets.length})</h4>
          <p class="hint" style="margin-bottom:12px; font-size:12px; color:var(--muted);">
            Toca un huevo para ocultarlo o mostrarlo. Los ocultos no mostrarán notificaciones.
          </p>
          <div class="chk" style="display:flex; flex-direction:column; gap:8px;">
            ${targets.map(t => {
              const off = filterHide.includes(t.key);
              const petImg = getPetImage(t);
              return `
                <button type="button" class="tg ${off ? 'off' : ''}" data-key="${esc(t.key)}" style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:var(--surface); border:1px solid var(--line); border-radius:var(--r); color:inherit; text-align:left;">
                  <img src="${petImg}" onerror="this.onerror=null; this.src='assets/logo.png';" style="width:26px; height:26px; object-fit:contain;">
                  <div style="flex:1;">
                    <b style="display:block; font-size:13px; color:${t.color || '#fff'};">${esc(t.animal)}</b>
                    <small style="color:var(--muted);">${esc(t.area)}</small>
                  </div>
                  <span>${off ? '🚫 Oculto' : '✅ Visible'}</span>
                </button>
              `;
            }).join("")}
          </div>
        </div>
        <button class="btn" id="showAllBtn" type="button" style="margin-top:14px; width:100%;">
          Ver todos los huevos otra vez
        </button>
      `;
    } else if (kind === "alerts") {
      titleHtml = "Configuración de Alertas";
      bodyHtml = `
        <label class="field" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <span>Avisar cuando salga un huevo nuevo</span>
          <input type="checkbox" id="alertOn" ${alerts.on ? 'checked' : ''} style="width:18px; height:18px;">
        </label>

        <div class="field" style="margin-bottom:14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span>Tipo de Sonido</span>
            <button class="btn" id="testSoundBtn" type="button" style="height:28px; padding:0 8px; font-size:11px;">Probar</button>
          </div>
          <select id="alertSound" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff;">
            <option value="classic" ${alerts.sound === 'classic' ? 'selected' : ''}>Clásico (HuevosToons)</option>
            <option value="soft" ${alerts.sound === 'soft' ? 'selected' : ''}>Suave</option>
            <option value="bell" ${alerts.sound === 'bell' ? 'selected' : ''}>Campana</option>
            <option value="alarm" ${alerts.sound === 'alarm' ? 'selected' : ''}>Alarma Intensa</option>
            <option value="none" ${alerts.sound === 'none' ? 'selected' : ''}>Sin sonido</option>
          </select>
        </div>

        <div class="field" style="margin-bottom:14px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span>Volumen</span>
            <b id="volVal">${alerts.volume}%</b>
          </div>
          <input type="range" id="alertVol" min="0" max="100" value="${alerts.volume}" style="width:100%;">
        </div>

        <div class="field" style="margin-bottom:14px;">
          <span style="display:block; margin-bottom:4px;">Avisar solo desde rareza:</span>
          <select id="alertMin" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff;">
            <option value="0" ${alerts.min === 0 ? 'selected' : ''}>Cualquier rareza</option>
            <option value="1" ${alerts.min === 1 ? 'selected' : ''}>Mythic o superior</option>
            <option value="2" ${alerts.min === 2 ? 'selected' : ''}>Cosmic o superior</option>
            <option value="3" ${alerts.min === 3 ? 'selected' : ''}>Secret o superior</option>
            <option value="4" ${alerts.min === 4 ? 'selected' : ''}>Eternal o superior</option>
            <option value="5" ${alerts.min === 5 ? 'selected' : ''}>Solo Divine</option>
          </select>
        </div>

        <label class="field" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <span>Notificaciones del navegador</span>
          <input type="checkbox" id="alertNotify" ${alerts.notify ? 'checked' : ''} style="width:18px; height:18px;">
        </label>
      `;
    } else if (kind === "add_server") {
      titleHtml = "Reportar Nuevo Servidor";
      bodyHtml = `
        <form id="addServerForm" style="display:flex; flex-direction:column; gap:12px;">
          <label>
            Zona:
            <select id="addArea" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff; margin-top:4px;">
              <option value="Titan Temple">Titan Temple</option>
              <option value="Enchanted Forest">Enchanted Forest</option>
              <option value="Light Dark">Light Dark</option>
              <option value="Abandoned Manor">Abandoned Manor</option>
              <option value="Cherry Blossom">Cherry Blossom</option>
              <option value="Cosmic">Cosmic</option>
              <option value="Prehistoric">Prehistoric</option>
              <option value="Heavenly Gate">Heavenly Gate</option>
              <option value="Mystic Shrine">Mystic Shrine</option>
            </select>
          </label>

          <label>
            Mascota / Huevo:
            <select id="addAnimal" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff; margin-top:4px;">
              ${Object.keys(PET_IMAGES).map(name => `<option value="${esc(name)}">${esc(name)}</option>`).join("")}
            </select>
          </label>

          <label>
            Multiplicador (x):
            <input type="number" step="0.01" min="1" max="100" id="addScale" value="12.40" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff; margin-top:4px;" required>
          </label>

          <label>
            Mutación:
            <select id="addMut" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff; margin-top:4px;">
              <option value="">Ninguna</option>
              <option value="Golden">Golden</option>
              <option value="Rainbow">Rainbow</option>
              <option value="Silver">Silver</option>
              <option value="Monstrous">Monstrous</option>
            </select>
          </label>

          <label>
            Roblox Job ID (Opcional):
            <input type="text" id="addJobId" placeholder="Ej: f92a7b1c-99d2..." style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff; margin-top:4px;">
          </label>

          <button class="btn main" type="submit" style="margin-top:8px;">Agregar al Radar</button>
        </form>
      `;
    } else if (kind === "discord") {
      titleHtml = "Conexión Discord (Canal: 1567011919255052410)";
      bodyHtml = `
        <div style="background:rgba(88,101,242,0.1); border:1px solid rgba(88,101,242,0.3); border-radius:var(--r); padding:12px; margin-bottom:14px;">
          <b style="color:#5865F2; display:block; margin-bottom:4px;">📡 Canal de Huevos Vinculado</b>
          <div style="font-family:var(--fn); font-size:16px; color:#fff;">Canal ID: <b>1567011919255052410</b></div>
          <small style="color:var(--muted); display:block; margin-top:4px;">
            Todos los huevos, multiplicadores y servidores que reporte tu bot en este canal aparecerán automáticamente aquí en tiempo real.
          </small>
        </div>

        <form id="discordConfigForm" style="display:flex; flex-direction:column; gap:12px;">
          <label>
            Token del Bot de Discord:
            <input type="password" id="dcTokenInput" placeholder="Pega tu Bot Token de Discord aquí" style="width:100%; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#fff; margin-top:4px;">
            <small style="color:var(--muted); font-size:11px; display:block; margin-top:4px;">
              Obtén el token gratis en <a href="https://discord.com/developers/applications" target="_blank" style="color:var(--accent);">Discord Developer Portal</a>.
            </small>
          </label>

          <button class="btn main" type="submit">Guardar y Conectar</button>
        </form>

        <div style="margin-top:20px; padding-top:16px; border-top:1px solid var(--line);">
          <b style="display:block; margin-bottom:8px;">🧪 Probar Conexión con un Mensaje de Prueba:</b>
          <button class="btn" id="simulateDcBtn" type="button" style="width:100%;">
            ⚡ Simular Detección de Huevo desde Discord
          </button>
        </div>

        <div style="margin-top:16px;">
          <small style="color:var(--muted);">
            <b>Opción Webhook:</b> Si tu bot admite enviar webhooks HTTP, puede enviar un POST directamente a:
            <code style="display:block; background:rgba(0,0,0,0.4); padding:6px; border-radius:4px; margin-top:4px; word-break:break-all;">http://localhost:3000/api/discord-webhook</code>
          </small>
        </div>
      `;
    } else if (kind === "runner") {
      titleHtml = "Entorno de Ejecución & Runner";
      bodyHtml = `
        <div style="background:rgba(255,194,26,0.1); border:1px solid rgba(255,194,26,0.3); border-radius:var(--r); padding:12px; margin-bottom:14px;">
          <b style="color:var(--accent); display:block; margin-bottom:4px;">⚡ Entorno de Script Vinculado</b>
          <small style="color:var(--muted); display:block;">
            Este puente ejecuta tu loader de FlowAuth en Roblox y transmite la información exacta de cada huevo y JobID directamente a la página web.
          </small>
        </div>

        <div class="field" style="display:flex; flex-direction:column; gap:6px; margin-bottom:14px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <b style="font-size:12px;">Script para tu Ejecutor (Solara, Wave, Delta, etc.):</b>
            <button class="btn" id="copyRunnerScriptBtn" type="button" style="height:26px; padding:0 8px; font-size:11px;">Copiar</button>
          </div>
          <textarea id="runnerScriptBox" readonly style="width:100%; height:75px; background:var(--bg); border:1px solid var(--line); border-radius:var(--r); color:#86efac; font-family:var(--fm, monospace); font-size:11px; padding:8px; resize:none;">loadstring(game:HttpGet("http://localhost:3000/bridge.lua"))()</textarea>
          <small style="color:var(--muted); font-size:10.5px;">
            Este script incluye tu loader: <code style="word-break:break-all;">https://flowauth.net/v1/loaders/cacd453cf780cca1885f79c734f492fa.lua</code>
          </small>
        </div>

        <div style="margin-bottom:14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <b style="font-size:12px;">Consola de Ejecución en Vivo (Roblox Logs):</b>
            <button class="btn" id="clearRunnerLogsBtn" type="button" style="height:24px; padding:0 6px; font-size:10px;">Limpiar</button>
          </div>
          <div id="runnerConsole" style="background:#050914; border:1px solid var(--line); border-radius:var(--r); height:220px; overflow-y:auto; padding:10px; font-family:var(--fm, monospace); font-size:11.5px; display:flex; flex-direction:column; gap:6px;">
            <span style="color:var(--muted);">Cargando consola...</span>
          </div>
        </div>

        <button class="btn" id="testRunnerEggBtn" type="button" style="width:100%;">
          🧪 Simular Detección de Huevo desde el Runner
        </button>
      `;
    }

    cont.innerHTML = `
      <div class="sheet" style="position:fixed; z-index:99; top:0; right:0; bottom:0; width:min(420px, 100vw); background:var(--surface); border-left:1px solid var(--line); box-shadow:-20px 0 50px rgba(0,0,0,0.5); display:flex; flex-direction:column;">
        <div class="sheet-h" style="display:flex; justify-content:space-between; align-items:center; padding:16px; border-bottom:1px solid var(--line);">
          <b style="font-family:var(--font); font-size:17px;">${titleHtml}</b>
          <button class="btn icon" id="closeSheetBtn" type="button">${ICONS.close}</button>
        </div>
        <div class="sheet-b" style="flex:1; overflow-y:auto; padding:16px;">
          ${bodyHtml}
        </div>
      </div>
      <div id="sheetOverlay" style="position:fixed; inset:0; background:rgba(0,0,0,0.4); z-index:98;"></div>
    `;

    // Event listeners
    document.getElementById("closeSheetBtn").addEventListener("click", closeSheet);
    document.getElementById("sheetOverlay").addEventListener("click", closeSheet);

    if (kind === "filters") {
      document.querySelectorAll(".tg[data-key]").forEach(btn => {
        btn.addEventListener("click", () => {
          const k = btn.dataset.key;
          if (filterHide.includes(k)) {
            filterHide = filterHide.filter(x => x !== k);
          } else {
            filterHide.push(k);
          }
          localStorage.setItem("eggr.filterHide", JSON.stringify(filterHide));
          openSheet("filters"); // refresh
          renderContent();
          updateFilterBadge();
        });
      });

      document.getElementById("showAllBtn").addEventListener("click", () => {
        filterHide = [];
        localStorage.setItem("eggr.filterHide", JSON.stringify(filterHide));
        openSheet("filters");
        renderContent();
        updateFilterBadge();
      });
    } else if (kind === "alerts") {
      document.getElementById("alertOn").addEventListener("change", (e) => {
        alerts.on = e.target.checked;
        saveAlerts();
      });
      document.getElementById("alertSound").addEventListener("change", (e) => {
        alerts.sound = e.target.value;
        saveAlerts();
      });
      document.getElementById("testSoundBtn").addEventListener("click", () => {
        playAlert(document.getElementById("alertSound").value);
      });
      document.getElementById("alertVol").addEventListener("input", (e) => {
        alerts.volume = +e.target.value;
        document.getElementById("volVal").textContent = alerts.volume + "%";
        saveAlerts();
      });
      document.getElementById("alertMin").addEventListener("change", (e) => {
        alerts.min = +e.target.value;
        saveAlerts();
      });
      document.getElementById("alertNotify").addEventListener("change", (e) => {
        if (e.target.checked && "Notification" in window) {
          Notification.requestPermission().then(perm => {
            alerts.notify = perm === "granted";
            e.target.checked = alerts.notify;
            saveAlerts();
          });
        } else {
          alerts.notify = false;
          saveAlerts();
        }
      });
    } else if (kind === "add_server") {
      document.getElementById("addServerForm").addEventListener("submit", (e) => {
        e.preventDefault();
        const area = document.getElementById("addArea").value;
        const animal = document.getElementById("addAnimal").value;
        const scale = +document.getElementById("addScale").value;
        const mut = document.getElementById("addMut").value;
        const jobid = document.getElementById("addJobId").value.trim();

        fetch("/api/servers/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            area,
            animal,
            scale,
            mutations: mut ? [mut] : [],
            jobid: jobid || undefined
          })
        }).then(r => r.json()).then(res => {
          if (res.ok) {
            showToast("Huevo reportado con éxito", `${animal} en ${area} (${fmtMult(scale)})`);
            closeSheet();
            fetchLiveData();
          }
        }).catch(() => {
          // Client-side fallback if offline
          let target = targets.find(t => t.animal === animal);
          if (!target) {
            target = {
              key: `${area}|${animal}`,
              area,
              animal,
              rarity: "Divine",
              color: "#fbff00",
              best_scale: scale,
              servers: []
            };
            targets.unshift(target);
          }
          const jid = jobid || ('f9' + Math.random().toString(16).substring(2, 10));
          target.servers.unshift({
            jobid: jid,
            scale,
            gen: 100e9,
            mutations: mut ? [mut] : [],
            parasite: false,
            claimed: false,
            join: `roblox://experiences/start?placeId=107778070777162&gameInstanceId=${jid}`,
            age_s: 0,
            players: 3,
            maxPlayers: 12
          });
          target.servers.sort((a, b) => b.scale - a.scale);
          target.best_scale = target.servers[0].scale;
          showToast("Huevo agregado localmente", `${animal} (${fmtMult(scale)})`);
          closeSheet();
          renderContent();
        });
      });
    } else if (kind === "discord") {
      fetch("/api/discord/config")
        .then(r => r.json())
        .then(d => {
          if (d.hasToken) {
            const input = document.getElementById("dcTokenInput");
            if (input) input.placeholder = "•••••••••••••••••••• (Token guardado)";
          }
        }).catch(() => {});

      document.getElementById("discordConfigForm").addEventListener("submit", (e) => {
        e.preventDefault();
        const token = document.getElementById("dcTokenInput").value.trim();
        fetch("/api/discord/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, channelId: "1567011919255052410" })
        }).then(r => r.json()).then(res => {
          showToast("Configuración de Discord guardada", "Escuchando canal 1567011919255052410");
          closeSheet();
        });
      });

      document.getElementById("simulateDcBtn").addEventListener("click", () => {
        const mockAnimals = ["Godzilla", "Royal Skywhale", "World Burner", "Voidseer Pumpkin", "Cave Dragon", "Oni Tiger"];
        const chosen = mockAnimals[Math.floor(Math.random() * mockAnimals.length)];
        const scale = +(Math.random() * 8 + 12).toFixed(2);
        fetch("/api/discord-webhook", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: `🥚 **¡HUEVO EN VIVO DETECTADO!**\n**Mascota:** ${chosen}\n**Zona:** Titan Temple\n**Multiplicador:** ${scale}x\n**Mutación:** Golden, Rainbow\n**JobId:** ba0be03e-cb74-4441-b978-2067e7ffb154\n**Jugadores:** 6/7`
          })
        }).then(r => r.json()).then(() => {
          showToast(`Discord: ${chosen} (${scale}x)`, "Sincronizado al radar");
          fetchLiveData();
        });
      });
    } else if (kind === "runner") {
      const scriptBox = document.getElementById("runnerScriptBox");
      document.getElementById("copyRunnerScriptBtn").addEventListener("click", () => {
        copyToClipboard(scriptBox.value, "Script copiado para tu ejecutor de Roblox");
      });

      const consoleEl = document.getElementById("runnerConsole");
      function fetchLogs() {
        fetch("/api/runner/logs")
          .then(r => r.json())
          .then(d => {
            if (consoleEl && d.logs) {
              consoleEl.innerHTML = d.logs.map(l => `
                <div style="line-height:1.4; word-break:break-word;">
                  <span style="color:#64748b;">[${esc(l.time)}]</span>
                  <span style="color:#e2e8f0;">${esc(l.message)}</span>
                  ${l.jobId ? `<span style="color:#38bdf8; font-size:10px;">(Job: ${esc(l.jobId.slice(0,8))}...)</span>` : ""}
                </div>
              `).join("");
            }
          }).catch(() => {});
      }
      fetchLogs();
      if (window._activeRunnerPoll) clearInterval(window._activeRunnerPoll);
      window._activeRunnerPoll = setInterval(fetchLogs, 1500);

      document.getElementById("clearRunnerLogsBtn").addEventListener("click", () => {
        if (consoleEl) consoleEl.innerHTML = "<span style='color:var(--muted);'>Consola limpia.</span>";
      });

      document.getElementById("testRunnerEggBtn").addEventListener("click", () => {
        const mockJobId = "f9" + Math.random().toString(16).substring(2, 10);
        fetch("/api/runner/logs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: "🎯 Detectado huevo en servidor: Godzilla (x19.50) en Titan Temple",
            jobId: mockJobId
          })
        });
        fetch("/api/report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jobId: mockJobId,
            placeId: 107778070777162,
            players: 6,
            maxPlayers: 7,
            eggs: [{
              area: "Titan Temple",
              animal: "Godzilla",
              scale: 19.50,
              mutations: ["Rainbow", "Golden"],
              claimed: false,
              parasite: false
            }]
          })
        }).then(() => {
          showToast("Runner: Godzilla x19.50 sincronizado", "Añadido con JobId exacto");
          fetchLogs();
          fetchLiveData();
        });
      });
    }
  }

  function closeSheet() {
    if (window._activeRunnerPoll) {
      clearInterval(window._activeRunnerPoll);
      window._activeRunnerPoll = null;
    }
    activeSheet = null;
    const cont = document.getElementById("sheetCont");
    if (cont) cont.innerHTML = "";
  }

  function updateFilterBadge() {
    const badge = document.getElementById("fltn");
    if (badge) {
      if (filterHide.length) {
        badge.removeAttribute("hidden");
        badge.textContent = filterHide.length;
      } else {
        badge.setAttribute("hidden", "true");
      }
    }
  }

  // --- POLLING & TIMERS (SINCRONIZACIÓN ABSOLUTA EN TIEMPO REAL) ---
  function startPolling() {
    fetchLiveData();
    fetchHistoryData();

    if (pollTimer) clearInterval(pollTimer);
    // Polling de servidores cada 3.5 segundos para no sobrecargar y mantener frescura
    pollTimer = setInterval(() => {
      fetchLiveData();
    }, 3500);

    // Reloj continuo de alta precisión cada 500ms (sin desincronización ni saltos)
    setInterval(() => {
      updateClockDisplay();
      updateServerTimes();
      updateUfoDisplay();
    }, 500);
  }

  function fetchLiveData() {
    fetch("/api/live")
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          if (data.reset_in != null) {
            resetIn = data.reset_in;
            // Sincronización absoluta milisegundo a milisegundo contra Date.now()
            targetResetTimestamp = Date.now() + (data.reset_in * 1000);
          }
          const bn = document.getElementById("botsn");
          if (bn && data.bots != null) {
            bn.textContent = `${data.bots} bots buscando`;
          }
          const oldLen = targets.reduce((sum, t) => sum + t.servers.length, 0);
          targets = data.targets || [];
          const newLen = targets.reduce((sum, t) => sum + t.servers.length, 0);

          // Si aparecen nuevos servidores, reproducir alerta sonora y notificación
          if (newLen > oldLen && oldLen > 0) {
            playAlert(alerts.sound);
            sendDesktopNotification("¡Nuevo Huevo Detectado!", "Un huevo ha aparecido en el radar de HuevosToons.");
          }
          lastSpawnCount = newLen;

          if (view === "live") {
            renderContent();
          }
        }
      })
      .catch(() => {
        // Fallback local simulation si el backend no responde
        simulateLocalTick();
      });
  }

  function fetchHistoryData() {
    fetch("/api/hist")
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          historyList = data.last || [];
          if (view === "history") renderContent();
        }
      })
      .catch(() => {});
  }

  function simulateLocalTick() {
    if (resetIn > 0) {
      resetIn--;
    } else {
      resetIn = 300;
    }
    targets.forEach(t => t.servers.forEach(s => s.age_s++));
    if (view === "live") renderContent();
  }

  function updateClockDisplay() {
    const cntEl = document.getElementById("cnt");
    const fillEl = document.getElementById("fill");
    const bigEl = document.getElementById("bigc");
    if (!cntEl && !bigEl) return;

    let remaining = resetIn;
    if (targetResetTimestamp != null) {
      const leftSec = (targetResetTimestamp - Date.now()) / 1000;
      if (leftSec <= 0) {
        remaining = 0;
        targetResetTimestamp = Date.now() + (300 * 1000);
      } else {
        remaining = Math.round(leftSec);
      }
    } else if (resetIn > 0) {
      resetIn--;
      remaining = resetIn;
    }

    const t = fmtTime(remaining);
    const isLast = remaining <= 30;

    if (cntEl) {
      cntEl.textContent = t;
      cntEl.classList.toggle("last", isLast);
    }
    if (bigEl) {
      bigEl.textContent = t;
    }

    if (fillEl) {
      const total = 300;
      const pct = Math.min(100, Math.max(0, ((total - remaining) / total) * 100));
      fillEl.style.width = pct + "%";
      fillEl.classList.toggle("last", isLast);
    }
  }

  function updateServerTimes() {
    const now = Date.now();
    const remainingReset = targetResetTimestamp != null 
      ? Math.max(0, Math.round((targetResetTimestamp - now) / 1000))
      : resetIn;
    const timeoutFormatted = fmtTime(remainingReset);
    const isUrgent = remainingReset <= 40;

    // Sincronizar todos los contadores de timeout de servidores con la página en tiempo real
    const timeoutEls = document.querySelectorAll(".chip-timeout");
    for (let i = 0; i < timeoutEls.length; i++) {
      const el = timeoutEls[i];
      const b = el.querySelector(".val-timeout") || el;
      if (b && b.textContent !== timeoutFormatted) {
        b.textContent = timeoutFormatted;
      }
      el.style.color = isUrgent ? "#f87171" : "var(--muted)";
    }

    // Sincronizar la edad activa de cada servidor de forma continua y suave
    const ageEls = document.querySelectorAll(".chip-age[data-spawn]");
    for (let i = 0; i < ageEls.length; i++) {
      const el = ageEls[i];
      const spawnMs = Number(el.getAttribute("data-spawn"));
      if (!spawnMs) continue;
      const ageSec = Math.max(0, Math.floor((now - spawnMs) / 1000));
      const b = el.querySelector(".val-age") || el;
      const ageTxt = fmtAge(ageSec);
      if (b && b.textContent !== ageTxt) {
        b.textContent = ageTxt;
      }
      el.style.color = ageColor(ageSec);
    }
  }

  function updateUfoDisplay() {
    const ufoEl = document.getElementById("ufo");
    const ufoT = document.getElementById("ufoT");
    const ufoN = document.getElementById("ufoN");
    const ufoS = document.getElementById("ufoS");
    if (!ufoEl || !ufoT) return;

    const t = ufoTime(Date.now());
    const isLive = t.live;
    const isSoon = !isLive && t.left <= 60000;

    ufoEl.classList.toggle("live", isLive);
    ufoEl.classList.toggle("soon", isSoon);

    if (isLive) {
      if (ufoN) ufoN.textContent = "¡A UFO has been sighted!";
      if (ufoS) ufoS.textContent = "En curso";
      ufoT.textContent = fmtTime(t.left / 1000);
    } else {
      if (ufoN) ufoN.textContent = "UFO";
      if (ufoS) ufoS.textContent = "";
      ufoT.textContent = fmtTime(t.left / 1000);
    }
  }

  // Run when DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

