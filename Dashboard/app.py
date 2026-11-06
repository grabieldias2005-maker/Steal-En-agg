import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
PLACE_ID = "107778070777162"
PET_VALUES_URL = "https://grindmath.app/steal-an-egg/values/"
_pet_cache = {"at": 0, "data": []}
ROBLOX_SERVERS_URL = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"

PAGE = r"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Steal An Egg · Radar de servidores</title>
<style>
:root{color-scheme:dark;--bg:#070d1b;--panel:#101a31;--line:#243452;--blue:#4b8cff;--muted:#9aabc7;--green:#43d6a0}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#14274a 0,#070d1b 55%);color:#f4f7ff;font:15px Inter,system-ui,Arial}
main{max-width:1100px;margin:auto;padding:28px 18px 60px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
h1{font-size:clamp(26px,5vw,40px);margin:0}.sub{color:var(--muted);margin:8px 0 24px}.pill{border:1px solid #245b50;color:var(--green);padding:8px 12px;border-radius:30px;font-size:12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:20px 0}
.stat,.server,.notice{background:linear-gradient(145deg,#121f3a,#0c1528);border:1px solid var(--line);border-radius:16px;padding:17px}
.stat small{color:var(--muted)}.num{font-size:27px;font-weight:800;margin-top:6px}
.notice{border-color:#725b2c;color:#f2d99a;line-height:1.5;margin:16px 0}
.toolbar{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:22px 0 12px}
button{background:var(--blue);border:0;color:white;font-weight:700;padding:10px 15px;border-radius:10px;cursor:pointer}button.secondary{background:#1b2b49;border:1px solid var(--line)}
#servers{display:grid;gap:10px}.server{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
.server strong{display:block;font-size:16px}.meta{color:var(--muted);font-size:13px;margin-top:5px}.join{display:inline-block;text-decoration:none;background:#1f9b74;color:#041a13;padding:10px 17px;border-radius:10px;font-weight:800}
#status{color:var(--muted);font-size:13px}.empty{color:var(--muted);padding:24px;text-align:center;border:1px dashed var(--line);border-radius:14px}
footer{color:var(--muted);font-size:12px;margin-top:26px}.pets{margin-top:30px;background:linear-gradient(145deg,#121f3a,#0c1528);border:1px solid var(--line);border-radius:16px;padding:18px}.pets h2{margin:0 0 5px}.pet-tools{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}.pet-tools input,.pet-tools select{background:#081326;color:#f4f7ff;border:1px solid var(--line);border-radius:8px;padding:9px;max-width:180px}.pet-tools input#petSearch{max-width:280px;flex:1}.pet-tools label{font-size:12px;color:var(--muted)}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:650px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-size:12px}td:last-child{color:var(--green);font-weight:800}.pets a{color:#8db7ff}
</style>
</head>
<body><main>
<div class="top"><div><h1>🥚 Steal An Egg Radar</h1><div class="sub">Buscador de servidores públicos · Roblox</div></div><span class="pill">● CONEXIÓN DEL RADAR</span></div>
<div class="stats">
 <div class="stat"><small>Servidores cargados</small><div class="num" id="count">—</div></div>
 <div class="stat"><small>Jugadores visibles</small><div class="num" id="players">—</div></div>
 <div class="stat"><small>Actualización automática</small><div class="num">30s</div></div>
</div>
<div class="notice"><b>Sobre la detección de huevos:</b> Roblox no publica qué huevos están dentro de cada servidor. Esta sección muestra el catálogo comunitario de mascotas y su ganancia base; no confirma su presencia en un servidor.</div>
<section class="pets" id="spawnPanel">
<div class="toolbar"><div><h2>⏱️ Registro de apariciones y reinicios</h2><div class="meta">Evidencia comunitaria observada; no es un detector en vivo de todos los servidores.</div></div><button class="secondary" onclick="loadSpawnEvidence()">Actualizar evidencia</button></div>
<div class="stats">
 <div class="stat"><small>Intervalo mediano observado</small><div class="num" id="spawnMedian">—</div></div>
 <div class="stat"><small>Intervalos registrados</small><div class="num" id="spawnSamples">—</div></div>
 <div class="stat"><small>Estado del conteo</small><div class="num" id="spawnCountdown">Inactivo</div></div>
</div>
<div class="notice"><b>Importante:</b> la evidencia disponible registra un evento visual del Secret Tralaledon Egg y una serie de cinco intervalos de “All Egg Reset” en un mismo servidor, con mediana de 300 segundos. No demuestra que cada huevo aparezca cada cinco minutos ni que el horario sea universal.</div>
<div class="toolbar"><div class="meta" id="spawnStatus">Cargando evidencia…</div><div><button id="notifyBtn" onclick="enableSpawnAlerts()">Activar notificaciones</button> <button class="secondary" onclick="startSpawnEstimate()">Iniciar estimador de 5 minutos</button></div></div>
<div id="spawnRecords" class="meta">Cargando registros…</div>
<p class="meta">El estimador solo avisa de una ventana aproximada (293–307 s) desde que tú lo inicias. No confirma que haya aparecido un huevo. <a href="https://github.com/terrencerun/steal-an-egg-research/blob/main/data/spawn-evidence.json" target="_blank" rel="noopener">Ver archivo original de evidencia</a> · <a href="https://stealaneggwiki.com/research/spawn-observations" target="_blank" rel="noopener">Método y observaciones</a>.</p>
</section>
<section class="pets"><div class="toolbar"><div><h2>🐾 Catálogo de ganancias</h2><div class="meta">Ordena mascotas por dinero generado por segundo</div></div><button class="secondary" onclick="loadPets()">Actualizar catálogo</button></div><div class="pet-tools"><input id="petSearch" placeholder="Buscar mascota, rareza o zona…" oninput="drawPets()"><select id="petSort" onchange="drawPets()"><option value="desc">Mayor ganancia primero</option><option value="asc">Menor ganancia primero</option></select><label>Mutación <select id="mutation" onchange="drawPets()"><option value="1">Normal ×1</option><option value="1.2">Silver ×1.2</option><option value="2.5">Golden ×2.5</option><option value="3.5">Rainbow ×3.5</option><option value="1.25">Bloom ×1.25</option><option value="2.75">Fractured / Scrambled ×2.75</option><option value="3">Parasite ×3</option></select></label><label>Tamaño × <input id="sizeFactor" type="number" min="0.1" max="100" step="0.1" value="1" oninput="drawPets()"></label></div><div id="petStatus" class="meta">Cargando catálogo comunitario…</div><div class="table-wrap"><table><thead><tr><th>Mascota</th><th>Rareza</th><th>Zona / huevo</th><th>Base $/s</th><th>Estimado $/s</th></tr></thead><tbody id="petRows"><tr><td colspan="5">Cargando…</td></tr></tbody></table></div><p class="meta">Estimación = ganancia base × mutación × factor de tamaño introducido. El factor de tamaño predeterminado es ×1 porque no existe una tabla pública fiable de kg a multiplicador. Valores comunitarios, no oficiales.</p><p class="meta">Fuente: <a href="https://grindmath.app/steal-an-egg/values/" target="_blank" rel="noopener">GrindMath – catálogo de ganancias</a>. <a href="https://stealaneggroblox.wiki/pets/" target="_blank" rel="noopener">Índice comunitario alternativo</a>.</p></section>
<div class="toolbar"><b>Servidores públicos disponibles</b><div><button class="secondary" id="more" onclick="loadMore()" disabled>Cargar más</button> <button onclick="loadServers()">Actualizar</button></div></div>
<div id="status">Conectando con Roblox…</div><div id="servers"><div class="empty">Cargando servidores…</div></div>
<footer>Los servidores pueden llenarse o cerrarse antes de entrar. JOIN abre el cliente/página oficial de Roblox. No se accede a servidores privados ni a datos ocultos.</footer>
</main>
<script>
const PLACE_ID = "107778070777162";
let cursor = null, all = [], loading = false;
const $ = id => document.getElementById(id);
function joinUrl(job){return "https://www.roblox.com/games/start?placeId="+PLACE_ID+"&gameInstanceId="+encodeURIComponent(job);}
function draw(){
 $("count").textContent=all.length;
 $("players").textContent=all.reduce((n,s)=>n+(s.playing||0),0);
 $("servers").innerHTML=all.length?all.map((s,i)=>'<div class="server"><div><strong>Servidor #'+(i+1)+'</strong><div class="meta">Jugadores: '+s.playing+'/'+s.maxPlayers+' · Ping: '+(s.ping??"—")+' ms · FPS: '+(s.fps??"—")+'</div><div class="meta">ID: '+s.id.slice(0,8)+'…</div></div><a class="join" href="'+joinUrl(s.id)+'" target="_blank" rel="noopener">JOIN ↗</a></div>').join(""):'<div class="empty">No se encontraron servidores públicos en esta consulta.</div>';
 $("more").disabled=!cursor||loading;
}
async function loadServers(append=false){
 if(loading)return;loading=true;$("status").textContent="Consultando servidores públicos de Roblox…";
 if(!append){cursor=null;all=[];}
 try{
  const url="/api/servers"+(append&&cursor?"?cursor="+encodeURIComponent(cursor):"");
  const r=await fetch(url);const data=await r.json();
  if(!r.ok)throw new Error(data.error||"No se pudo consultar Roblox");
  const incoming=data.data||[];const seen=new Set(all.map(x=>x.id));
  all=all.concat(incoming.filter(x=>!seen.has(x.id)));cursor=data.nextPageCursor||null;
  $("status").textContent="Última consulta: "+new Date().toLocaleTimeString()+" · "+(cursor?"hay más servidores":"fin de la lista consultada");
  draw();
 }catch(e){$("status").textContent="Error: "+e.message;if(!all.length)$("servers").innerHTML='<div class="empty">No se pudo cargar la lista. Intenta actualizar en unos segundos.</div>';}
 finally{loading=false;$("more").disabled=!cursor;}
}
function loadMore(){loadServers(true)}
let spawnTimer=null,spawnStartedAt=null,spawnAlerted=false,spawnEvidence=null;
async function loadSpawnEvidence(){
 const box=$("spawnRecords");$("spawnStatus").textContent="Consultando registro comunitario…";
 try{
  const r=await fetch("/api/spawn-evidence");const d=await r.json();if(!r.ok)throw new Error(d.error||"No disponible");
  spawnEvidence=d;const series=(d.intervalSeries||[])[0],stats=series?.statistics||{};
  $("spawnMedian").textContent=stats.medianSeconds?stats.medianSeconds+" s":"—";
  $("spawnSamples").textContent=stats.completeIntervals??"—";
  const records=(d.records||[]).map(x=>'<div class="server"><div><strong>'+x.visibleCue+'</strong><div class="meta">Zona: '+x.location+' · Observado: '+x.reviewedAt+' · '+x.confidence+'</div><div class="meta">'+x.intervalStatus+'</div></div><a href="'+x.sourceUrl+'" target="_blank" rel="noopener">Ver evidencia ↗</a></div>');
  const intervals=(d.intervalSeries||[]).map(x=>'<div class="server"><div><strong>'+x.target+'</strong><div class="meta">'+x.context+' · '+x.statistics.completeIntervals+' intervalos: '+x.intervalSeconds.join(", ")+' s</div><div class="meta">Mediana: '+x.statistics.medianSeconds+' s · Rango: '+x.statistics.minimumSeconds+'–'+x.statistics.maximumSeconds+' s</div></div><a href="'+x.sourceUrl+'" target="_blank" rel="noopener">Ver video ↗</a></div>');
  box.innerHTML=records.concat(intervals).join("")||"No hay registros publicados.";
  $("spawnStatus").textContent="Fuente revisada: "+(d.reviewedAt||"sin fecha")+" · datos comunitarios, no oficiales.";
 }catch(e){$("spawnStatus").textContent="No se pudo cargar la evidencia: "+e.message;box.textContent="Revisa el enlace del archivo de evidencia.";}
}
async function enableSpawnAlerts(){
 if(!("Notification" in window)){alert("Este navegador no admite notificaciones.");return;}
 const permission=await Notification.requestPermission();
 $("notifyBtn").textContent=permission==="granted"?"Notificaciones activadas":"Permiso no concedido";
 if(permission==="granted")new Notification("Steal An Egg Radar",{body:"Avisos estimados activados. Inicia el estimador para contar desde ahora."});
}
function startSpawnEstimate(){
 if(spawnTimer)clearInterval(spawnTimer);
 spawnStartedAt=Date.now();spawnAlerted=false;
 $("spawnCountdown").textContent="05:00";
 spawnTimer=setInterval(()=>{
  const elapsed=(Date.now()-spawnStartedAt)/1000,remaining=Math.max(0,300-Math.floor(elapsed));
  const mm=String(Math.floor(remaining/60)).padStart(2,"0"),ss=String(remaining%60).padStart(2,"0");
  $("spawnCountdown").textContent=mm+":"+ss;
  if(elapsed>=293&&!spawnAlerted){
   spawnAlerted=true;$("spawnCountdown").textContent="Ventana estimada";
   if("Notification" in window&&Notification.permission==="granted")new Notification("Steal An Egg: ventana estimada",{body:"Han pasado unos 293 segundos desde que iniciaste el conteo. Comprueba el juego: no es una detección confirmada."});
   $("spawnStatus").textContent="Ventana estimada de reinicio (293–307 s). Comprueba el juego manualmente.";
  }
  if(elapsed>=307){clearInterval(spawnTimer);spawnTimer=null;$("spawnCountdown").textContent="Conteo finalizado";}
 },1000);
}
let pets=[];
function money(n){if(n>=1e9)return "$"+(n/1e9).toFixed(2).replace(/0+$/,"").replace(/\\.$/,"")+"B/s";if(n>=1e6)return "$"+(n/1e6).toFixed(2).replace(/0+$/,"").replace(/\\.$/,"")+"M/s";if(n>=1e3)return "$"+(n/1e3).toFixed(2).replace(/0+$/,"").replace(/\\.$/,"")+"K/s";return "$"+n+"/s";}
async function loadPets(){ $("petStatus").textContent="Consultando catálogo comunitario…";try{const r=await fetch("/api/pets");const d=await r.json();if(!r.ok)throw new Error(d.error||"Catálogo no disponible");pets=d.data||[];$("petStatus").textContent=pets.length+" registros · fuente comunitaria · actualizado "+new Date(d.updated_at).toLocaleString();drawPets();}catch(e){$("petStatus").textContent="No se pudo actualizar el catálogo: "+e.message;}}
function drawPets(){const q=($("petSearch")?.value||"").toLowerCase(),m=Number($("mutation")?.value||1),z=Math.max(.1,Number($("sizeFactor")?.value||1));const rows=pets.filter(p=>(p.name+" "+p.rarity+" "+p.source).toLowerCase().includes(q)).sort((a,b)=>$("petSort").value==="asc"?a.income-b.income:b.income-a.income);$("petRows").innerHTML=rows.map(p=>'<tr><td>'+p.name+'</td><td>'+p.rarity+'</td><td>'+p.source+'</td><td>'+money(p.income)+'</td><td>'+money(p.income*m*z)+'</td></tr>').join("")||'<tr><td colspan="5">No hay coincidencias.</td></tr>';}
loadServers();loadPets();loadSpawnEvidence();setInterval(()=>loadServers(false),30000);
</script></body></html>
"""

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.get("/api/servers")
def public_servers():
    params = {"sortOrder": "Desc", "limit": "100"}
    cursor = request.args.get("cursor", "")
    if cursor:
        params["cursor"] = cursor[:2000]
    try:
        response = requests.get(
            ROBLOX_SERVERS_URL,
            params=params,
            headers={"User-Agent": "StealAnEggPublicServerRadar/1.0"},
            timeout=15,
        )
        if response.status_code == 429:
            return jsonify({"error": "Roblox está limitando las consultas. Espera un momento."}), 429
        response.raise_for_status()
        payload = response.json()
        return jsonify({
            "data": payload.get("data", []),
            "nextPageCursor": payload.get("nextPageCursor"),
        })
    except requests.RequestException:
        return jsonify({"error": "No se pudo conectar con la API pública de Roblox."}), 502
    except ValueError:
        return jsonify({"error": "Roblox devolvió una respuesta inesperada."}), 502

@app.get("/api/pets")
def pet_values():
    # Community-maintained table; cache for six hours to avoid hammering the source.
    now = datetime.now(timezone.utc).timestamp()
    if _pet_cache["data"] and now - _pet_cache["at"] < 21600:
        return jsonify({"data": _pet_cache["data"], "updated_at": datetime.fromtimestamp(_pet_cache["at"], timezone.utc).isoformat(), "source": PET_VALUES_URL})
    try:
        response = requests.get(PET_VALUES_URL, headers={"User-Agent": "Mozilla/5.0 StealAnEggRadar/1.0"}, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        records = []
        for table in soup.find_all("table"):
            headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
            if not headers or not any("pet" in h for h in headers) or not any("income" in h for h in headers):
                continue
            for tr in table.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                if len(cells) < 4 or cells[0].lower() == "pet":
                    continue
                # Expected columns: pet, base income, rarity, biome/egg, weight.
                import re
                match = re.search(r"\$\s*([\d,.]+)\s*([KMB]?)\s*/s", cells[1], re.I)
                if not match:
                    continue
                multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[match.group(2).upper()]
                records.append({"name": cells[0], "income": float(match.group(1).replace(",", "")) * multiplier, "rarity": cells[2], "source": cells[3]})
            if records:
                break
        if not records:
            raise ValueError("No se reconoció la tabla de ganancias de la fuente.")
        _pet_cache.update({"at": now, "data": records})
        return jsonify({"data": records, "updated_at": datetime.fromtimestamp(now, timezone.utc).isoformat(), "source": PET_VALUES_URL})
    except (requests.RequestException, ValueError, IndexError):
        if _pet_cache["data"]:
            return jsonify({"data": _pet_cache["data"], "updated_at": datetime.fromtimestamp(_pet_cache["at"], timezone.utc).isoformat(), "source": PET_VALUES_URL, "stale": True})
        return jsonify({"error": "La fuente comunitaria no respondió o cambió su formato. Consulta el enlace de GrindMath."}), 502

@app.get("/api/spawn-evidence")
def spawn_evidence():
    # Public community evidence ledger. This records observations, not live server telemetry.
    url = "https://raw.githubusercontent.com/terrencerun/steal-an-egg-research/main/data/spawn-evidence.json"
    try:
        response = requests.get(url, headers={"User-Agent": "StealAnEggPublicServerRadar/1.0"}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        return jsonify(payload)
    except (requests.RequestException, ValueError):
        return jsonify({"error": "No se pudo consultar el archivo público de evidencia."}), 502

@app.get("/health")
def health():
    return jsonify({"status": "ok", "placeId": PLACE_ID})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
