import os
import requests
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
PLACE_ID = "107778070777162"
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
footer{color:var(--muted);font-size:12px;margin-top:26px}
</style>
</head>
<body><main>
<div class="top"><div><h1>🥚 Steal An Egg Radar</h1><div class="sub">Buscador de servidores públicos · Roblox</div></div><span class="pill">● CONEXIÓN DEL RADAR</span></div>
<div class="stats">
 <div class="stat"><small>Servidores cargados</small><div class="num" id="count">—</div></div>
 <div class="stat"><small>Jugadores visibles</small><div class="num" id="players">—</div></div>
 <div class="stat"><small>Actualización automática</small><div class="num">30s</div></div>
</div>
<div class="notice"><b>Sobre la detección de huevos:</b> Roblox no publica los huevos que hay dentro de cada servidor en su lista pública. Esta página muestra servidores y permite intentar entrar; para mostrar huevos reales hace falta una fuente de datos autorizada del juego.</div>
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
loadServers();setInterval(()=>loadServers(false),30000);
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

@app.get("/health")
def health():
    return jsonify({"status": "ok", "placeId": PLACE_ID})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
