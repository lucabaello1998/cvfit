"""Servidor local con previsualización en vivo.

Sin frameworks: `http.server` de la biblioteca estándar y un HTML con fetch. Levanta en
http://localhost:8765, se usa y se apaga.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .adaptar import adaptar
from .cv import parsear
from .match import evaluar
from .plantillas import render

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "ejemplos" / "cv.md"

APP = """<!doctype html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>cvfit — encaje CV ↔ aviso</title>
<style>
:root{--bg:#0b0f14;--panel:#121a23;--panel2:#182430;--linea:#22303e;--txt:#e8eef6;--tenue:#93a6ba;
--ok:#35d39a;--medio:#fbbf24;--mal:#f87171;--acento:#60a5fa}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:18px 22px;border-bottom:1px solid var(--linea);display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
h1{margin:0;font-size:22px;letter-spacing:-.02em}
h1 span{color:var(--acento)}
header p{margin:0;color:var(--tenue);font-size:13px}
main{display:grid;grid-template-columns:420px 1fr;gap:18px;padding:18px 22px 40px;align-items:start}
@media(max-width:980px){main{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--linea);border-radius:14px;padding:14px}
label{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--tenue);margin:0 0 6px}
textarea{width:100%;background:var(--panel2);color:var(--txt);border:1px solid var(--linea);border-radius:10px;
padding:10px;font-family:ui-monospace,Consolas,monospace;font-size:12px;line-height:1.5;resize:vertical}
textarea:focus{outline:2px solid var(--acento);outline-offset:1px}
select,button{background:var(--panel2);color:var(--txt);border:1px solid var(--linea);border-radius:10px;
padding:9px 12px;font-size:13px;font-family:inherit;cursor:pointer}
button.principal{background:rgba(96,165,250,.16);border-color:rgba(96,165,250,.45);font-weight:600}
button:hover{border-color:var(--acento)}
.fila{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.score{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.aro{width:86px;height:86px;border-radius:50%;display:grid;place-items:center;font-size:24px;font-weight:700;
border:6px solid var(--linea)}
.aro.alta{border-color:var(--ok);color:var(--ok)}
.aro.media{border-color:var(--medio);color:var(--medio)}
.aro.baja{border-color:var(--mal);color:var(--mal)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 0}
.chip{font-size:12px;border:1px solid var(--linea);border-radius:999px;padding:2px 9px;color:var(--tenue)}
.chip.ok{border-color:rgba(53,211,154,.4);color:var(--ok)}
.chip.mal{border-color:rgba(248,113,113,.4);color:var(--mal)}
.lista{margin:8px 0 0;padding-left:18px;font-size:13px;color:#c9d6e4}
.lista li{margin-bottom:4px}
iframe{width:100%;height:640px;border:1px solid var(--linea);border-radius:12px;background:#fff}
.oculto{display:none}
small{color:var(--tenue)}
</style>
</head>
<body>
<header>
  <h1>cv<span>fit</span></h1>
  <p>Pegá tu CV en Markdown y el aviso. Te dice cuánto respaldás y qué te falta. No inventa: adaptar es reordenar.</p>
</header>
<main>
  <div class="panel">
    <label for="cv">CV (Markdown)</label>
    <textarea id="cv" rows="16" placeholder="# Nombre\n**Título**\n\n## EXPERIENCIA\n- ..."></textarea>
    <div class="fila"><button id="ejemplo">Cargar CV de ejemplo</button></div>

    <label for="aviso" style="margin-top:14px">Aviso / job description</label>
    <textarea id="aviso" rows="10" placeholder="Pegá el texto completo de la oferta..."></textarea>

    <div class="fila">
      <select id="estilo">
        <option value="ats">ATS</option>
        <option value="clasico">Clásico</option>
        <option value="compacto">Compacto</option>
      </select>
      <button class="principal" id="analizar">Analizar y adaptar</button>
      <button id="imprimir">Imprimir / PDF</button>
    </div>
    <p style="margin:10px 0 0"><small id="estado"></small></p>
  </div>

  <div>
    <div class="panel" id="resultado">
      <div class="score">
        <div class="aro" id="aro">–</div>
        <div>
          <div id="veredicto" style="font-size:16px;font-weight:600">Todavía sin analizar</div>
          <div id="detalle" style="color:var(--tenue);font-size:13px">Pegá el aviso y apretá Analizar.</div>
        </div>
      </div>
      <div id="cubiertas" class="chips"></div>
      <div id="faltantes" class="chips"></div>
      <ul class="lista" id="observaciones"></ul>
      <ul class="lista" id="cambios"></ul>
    </div>
    <div class="panel" style="margin-top:14px">
      <iframe id="preview" title="Previsualización del CV"></iframe>
    </div>
  </div>
</main>
<script>
const $ = id => document.getElementById(id);
const estado = texto => { $('estado').textContent = texto; };

$('ejemplo').onclick = async () => {
  const respuesta = await fetch('/api/ejemplo');
  $('cv').value = await respuesta.text();
  estado('CV de ejemplo cargado.');
};

function pintar(r) {
  $('aro').className = 'aro ' + r.veredicto;
  $('aro').textContent = r.score + '%';
  $('veredicto').textContent = {alta:'Encaje alto', media:'Encaje medio', baja:'Encaje bajo'}[r.veredicto]
    + (r.confiable ? '' : ' (orientativo)');
  $('detalle').textContent = r.cubiertas.length + ' de ' + r.total_requisitos + ' requisitos respaldados por tu CV.';
  $('cubiertas').innerHTML = r.cubiertas.map(s => '<span class="chip ok">' + s + '</span>').join('');
  $('faltantes').innerHTML = [...r.faltantes, ...r.blandas_faltantes].map(s => '<span class="chip mal">' + s + '</span>').join('');
  $('observaciones').innerHTML = r.observaciones.map(o => '<li>' + o + '</li>').join('');
  $('cambios').innerHTML = (r.cambios || []).map(c => '<li>' + c + '</li>').join('');
}

async function actualizar(renderizar) {
  const cuerpo = JSON.stringify({cv: $('cv').value, aviso: $('aviso').value});
  const r = await fetch('/api/analizar', {method:'POST', headers:{'Content-Type':'application/json'}, body: cuerpo});
  const datos = await r.json();
  pintar(datos);
  if (renderizar) {
    const p = await fetch('/api/render', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({cv: $('cv').value, aviso: $('aviso').value, estilo: $('estilo').value})
    });
    $('preview').srcdoc = await p.text();
  }
}

$('analizar').onclick = async () => {
  if (!$('aviso').value.trim()) { estado('Falta el texto del aviso.'); return; }
  estado('Analizando…');
  await actualizar(true);
  estado('Listo. Revisá los gaps y el CV adaptado.');
};
$('estilo').onchange = () => actualizar(true);
$('imprimir').onclick = () => { $('preview').contentWindow.print(); };
</script>
</body>
</html>
"""


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):  # silencio en consola
        return

    def _responder(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _html(self, texto: str) -> None:
        self._responder(200, texto.encode("utf-8"), "text/html; charset=utf-8")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._html(APP)
        elif self.path == "/api/ejemplo":
            self._responder(200, EJEMPLO.read_text(encoding="utf-8").encode("utf-8"), "text/markdown; charset=utf-8")
        else:
            self._responder(404, b"no existe", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        largo = int(self.headers.get("Content-Length", 0))
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            self._responder(400, b'{"error":"json invalido"}', "application/json")
            return

        cv_texto = datos.get("cv", "")
        aviso_texto = datos.get("aviso", "")
        cv = parsear(cv_texto)
        resultado = evaluar(cv, aviso_texto)
        adaptado = adaptar(cv, aviso_texto)

        if self.path == "/api/analizar":
            cuerpo = {
                "score": resultado.score,
                "veredicto": resultado.veredicto,
                "confiable": resultado.confiable,
                "total_requisitos": resultado.total_requisitos,
                "cubiertas": resultado.cubiertas,
                "faltantes": resultado.faltantes,
                "blandas_faltantes": resultado.blandas_faltantes,
                "observaciones": resultado.observaciones,
                "cambios": adaptado.cambios,
            }
            self._responder(200, json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), "application/json")
        elif self.path == "/api/render":
            html = render(adaptado, datos.get("estilo", "ats"))
            self._html(html)
        else:
            self._responder(404, b"no existe", "text/plain")


def main(puerto: int = 8765) -> int:
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    print(f"cvfit en http://localhost:{puerto}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nchau")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
