"""Servidor local con previsualización en vivo.

Sin frameworks: `http.server` de la biblioteca estándar y un HTML con fetch. Levanta en
http://localhost:8765, se usa y se apaga.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .adaptar import adaptar
from .comparar import comparar_textos
from .cv import parsear
from .extraer import ExtraccionError, desde_docx, desde_pdf, estructurar
from .match import evaluar
from .plantillas import render

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "ejemplos" / "cv.md"
MAXIMO = 12 * 1024 * 1024

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
.zona{border:1px dashed var(--linea);border-radius:10px;padding:10px;background:var(--panel2);margin-bottom:8px}
.zona.encima{border-color:var(--acento);background:rgba(96,165,250,.1)}
.zona input{display:block;font-size:12px;color:var(--txt);margin:0 0 6px;max-width:100%}
.zona small{display:block;line-height:1.4}
.tabla{width:100%;border-collapse:collapse;font-size:13px}
.tabla th{text-align:left;font-weight:600;color:var(--tenue);font-size:11px;text-transform:uppercase;
letter-spacing:.06em;padding:0 8px 6px;border-bottom:1px solid var(--linea)}
.tabla td{padding:7px 8px;border-bottom:1px solid rgba(34,48,62,.6);vertical-align:top}
.tabla tr.gana td{color:var(--ok)}
.tabla td.num{white-space:nowrap}
button.mini{padding:3px 9px;font-size:12px;border-radius:8px}
.oculto{display:none}
small{color:var(--tenue)}
</style>
</head>
<body>
<header>
  <h1>cv<span>fit</span></h1>
  <p>Arrastrá tu CV (PDF, Word o Markdown) y pegá el aviso. Te dice cuánto respaldás y qué te falta. No inventa: adaptar es reordenar.</p>
</header>
<main>
  <div class="panel">
    <label for="archivo">CV — arrastrá el archivo o pegá el texto</label>
    <div class="zona" id="zona">
      <input type="file" id="archivo" accept=".md,.markdown,.txt,.docx,.pdf" multiple>
      <small id="zona-ayuda">Markdown, TXT, Word (.docx) o PDF. Podés soltar <strong>varios</strong>: se comparan contra el mismo aviso y queda el que mejor encaja. Los PDF escaneados (imagen) no se pueden leer: convertilos a Word primero.</small>
    </div>
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
    <div class="panel oculto" id="panel-ranking" style="margin-bottom:14px">
      <label style="margin-bottom:8px">Varios CVs contra el mismo aviso</label>
      <table class="tabla" id="ranking"></table>
      <p style="margin:10px 0 0"><small>El ganador se carga solo en el CV adaptado. "Usar" cambia la versión que vas a mandar.</small></p>
    </div>
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

// --- ingesta: md/txt se leen en el navegador, docx/pdf en el servidor ---
let cargados = [];       // [{nombre, texto}] tal como se leyeron
let filasActuales = [];  // ranking de la última comparación

const escapar = texto => String(texto).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function textoDeArchivo(archivo) {
  if (/\\.(md|markdown|txt)$/i.test(archivo.name)) return archivo.text();
  const r = await fetch('/api/extraer?cv=1&nombre=' + encodeURIComponent(archivo.name), {
    method: 'POST', headers: {'Content-Type': 'application/octet-stream'}, body: archivo
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.error || 'no se pudo leer');
  return datos.texto;
}

async function cargarArchivos(lista) {
  const archivos = [...lista];
  if (!archivos.length) return;
  estado('Leyendo ' + archivos.length + (archivos.length > 1 ? ' archivos…' : ' archivo…'));
  cargados = [];
  const fallos = [];
  for (const archivo of archivos) {
    try {
      cargados.push({nombre: archivo.name, texto: await textoDeArchivo(archivo)});
    } catch (error) {
      fallos.push(archivo.name + ': ' + error.message);
    }
  }
  if (fallos.length) estado(fallos.join(' · '));
  if (!cargados.length) return;

  $('cv').value = cargados[0].texto;
  if (cargados.length > 1) {
    await compararCargados();
  } else {
    $('panel-ranking').classList.add('oculto');
    if (!fallos.length) estado('CV cargado desde ' + cargados[0].nombre + ' (' + cargados[0].texto.length + ' caracteres). Revisalo antes de analizar.');
  }
}

function pintarRanking(filas) {
  filasActuales = filas;
  $('panel-ranking').classList.remove('oculto');
  $('ranking').innerHTML =
    '<thead><tr><th>#</th><th>CV</th><th>Encaje</th><th>Respaldados</th><th>Gaps excluyentes</th><th></th></tr></thead><tbody>'
    + filas.map((f, i) =>
      '<tr class="' + (i === 0 ? 'gana' : '') + '">'
      + '<td class="num">' + (i + 1) + '</td>'
      + '<td>' + escapar(f.nombre) + '</td>'
      + '<td class="num">' + f.score + '%' + (f.confiable ? '' : ' (orientativo)') + '</td>'
      + '<td class="num">' + f.cubiertas.length + '/' + f.total_requisitos + '</td>'
      + '<td>' + (f.faltantes.map(escapar).join(', ') || '—') + '</td>'
      + '<td class="num"><button class="mini" data-i="' + i + '">usar</button></td>'
      + '</tr>').join('')
    + '</tbody>';
}

async function compararCargados() {
  const aviso = $('aviso').value.trim();
  if (!aviso) {
    $('panel-ranking').classList.add('oculto');
    estado('Cargué ' + cargados.length + ' CVs. Pegá el aviso para compararlos.');
    return;
  }
  estado('Comparando ' + cargados.length + ' CVs contra el aviso…');
  const r = await fetch('/api/comparar', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({cvs: cargados, aviso: aviso})
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) { estado(datos.error || 'No pude comparar los CVs.'); return; }

  pintarRanking(datos.filas);
  const mejor = datos.filas[0];
  const elegido = cargados.find(c => c.nombre === mejor.nombre);
  if (elegido) $('cv').value = elegido.texto;
  await actualizar(true);
  estado('Gana ' + mejor.nombre + ' con ' + mejor.score + '%. Cambiá de versión con "usar".');
}

$('ranking').addEventListener('click', async evento => {
  const indice = evento.target.dataset.i;
  if (indice === undefined) return;
  const elegido = cargados.find(c => c.nombre === filasActuales[Number(indice)].nombre);
  if (!elegido) return;
  $('cv').value = elegido.texto;
  await actualizar(true);
  estado('Usando ' + elegido.nombre + ' para el CV adaptado.');
});

$('archivo').onchange = evento => cargarArchivos(evento.target.files);
const zona = $('zona');
zona.addEventListener('dragover', evento => { evento.preventDefault(); zona.classList.add('encima'); });
zona.addEventListener('dragleave', () => zona.classList.remove('encima'));
zona.addEventListener('drop', evento => {
  evento.preventDefault();
  zona.classList.remove('encima');
  if (evento.dataTransfer.files.length) cargarArchivos(evento.dataTransfer.files);
});

// si edita el CV a mano, la comparación anterior deja de valer
$('cv').addEventListener('input', () => { cargados = []; $('panel-ranking').classList.add('oculto'); });

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
  if (cargados.length > 1) { await compararCargados(); return; }
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

    def _json(self, codigo: int, cuerpo: dict) -> None:
        self._responder(
            codigo, json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8"
        )

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._html(APP)
        elif self.path == "/api/ejemplo":
            self._responder(200, EJEMPLO.read_text(encoding="utf-8").encode("utf-8"), "text/markdown; charset=utf-8")
        else:
            self._responder(404, b"no existe", "text/plain; charset=utf-8")

    def _extraer(self) -> None:
        """Recibe el archivo binario y devuelve el texto ya listo para el textarea del CV."""
        from urllib.parse import parse_qs, urlparse

        consulta = parse_qs(urlparse(self.path).query)
        nombre = (consulta.get("nombre", ["archivo"])[0] or "archivo").strip()
        para_cv = consulta.get("cv", ["0"])[0] == "1"

        largo = int(self.headers.get("Content-Length", 0))
        if largo > MAXIMO:
            self._json(413, {"error": f"el archivo supera {MAXIMO // (1024 * 1024)} MB"})
            return
        datos = self.rfile.read(largo)
        if not datos:
            self._json(400, {"error": "el archivo está vacío"})
            return

        sufijo = Path(nombre).suffix.lower()
        try:
            if sufijo in (".md", ".markdown", ".txt"):
                texto = datos.decode("utf-8-sig", "replace")
            elif sufijo == ".docx":
                texto = desde_docx(datos)
            elif sufijo == ".pdf":
                texto = desde_pdf(datos)
                if para_cv:
                    texto = estructurar(texto)
            else:
                self._json(400, {"error": f"formato no soportado: {sufijo or 'sin extensión'}"})
                return
        except ExtraccionError as error:
            self._json(400, {"error": str(error)})
            return

        self._json(200, {"nombre": nombre, "texto": texto})

    def do_POST(self) -> None:
        from urllib.parse import urlparse

        ruta = urlparse(self.path).path
        if ruta == "/api/extraer":
            self._extraer()
            return

        largo = int(self.headers.get("Content-Length", 0))
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            self._responder(400, b'{"error":"json invalido"}', "application/json")
            return

        cv_texto = datos.get("cv", "")
        aviso_texto = datos.get("aviso", "")

        if ruta == "/api/comparar":
            entradas = datos.get("cvs") or []
            textos = {
                (entrada.get("nombre") or f"CV {posicion}").strip(): entrada.get("texto", "")
                for posicion, entrada in enumerate(entradas, start=1)
                if isinstance(entrada, dict)
            }
            if len(textos) < 2:
                self._json(400, {"error": "hacen falta al menos dos CV para comparar"})
                return
            if not aviso_texto.strip():
                self._json(400, {"error": "falta el texto del aviso"})
                return
            filas = comparar_textos(textos, aviso_texto)
            self._json(
                200,
                {
                    "filas": [
                        {
                            "nombre": fila.nombre,
                            "score": fila.resultado.score,
                            "veredicto": fila.resultado.veredicto,
                            "confiable": fila.resultado.confiable,
                            "total_requisitos": fila.resultado.total_requisitos,
                            "cubiertas": fila.resultado.cubiertas,
                            "faltantes": fila.resultado.faltantes,
                            "blandas_faltantes": fila.resultado.blandas_faltantes,
                        }
                        for fila in filas
                    ]
                },
            )
            return

        cv = parsear(cv_texto)
        resultado = evaluar(cv, aviso_texto)
        adaptado = adaptar(cv, aviso_texto)

        if ruta == "/api/analizar":
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
        elif ruta == "/api/render":
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
