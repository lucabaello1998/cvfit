"""Servidor local con previsualización en vivo.

Sin frameworks: `http.server` de la biblioteca estándar y un HTML con fetch. Levanta en
http://localhost:8765, se usa y se apaga.
"""

from __future__ import annotations

import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unicodedata import normalize

from .adaptar import adaptar
from .comparar import comparar_textos
from .cv import parsear
from .extraer import ExtraccionError, desde_docx, desde_pdf, estructurar
from .match import evaluar
from .pdf import PdfError, a_pdf
from .plantillas import render
from .revisar import CONSEJOS, GUIA_ESTILOS, revisar

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "ejemplos" / "cv.md"
MAXIMO = 12 * 1024 * 1024

APP = """<!doctype html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>cvfit — encaje CV ↔ aviso</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230a0e14'/%3E%3Ctext x='16' y='22' font-family='system-ui' font-size='14' font-weight='700' fill='%2360a5fa' text-anchor='middle'%3Ecv%3C/text%3E%3C/svg%3E">
<style>
:root{
  --bg:#080b10; --bg-2:#0b1017; --panel:#0f151d; --panel-2:#141c26; --panel-3:#1a2431;
  --linea:#1e2936; --linea-2:#2a3a4c; --txt:#e8eef6; --tenue:#8ea3b8; --tenue-2:#64798e;
  --ok:#3ddc97; --medio:#f5c04a; --mal:#f87171; --acento:#60a5fa; --acento-2:#3b82f6;
  --radio:14px; --alto:34px;
}
*{box-sizing:border-box}
body{margin:0;color:var(--txt);font-size:14px;-webkit-font-smoothing:antialiased;
font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
background:
 radial-gradient(1000px 480px at 8% -14%,rgba(96,165,250,.14),transparent 62%),
 radial-gradient(800px 460px at 96% -8%,rgba(61,220,151,.06),transparent 58%),
 var(--bg)}
::selection{background:rgba(96,165,250,.3)}

/* ---------- barra superior ---------- */
.appbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
padding:12px 24px;border-bottom:1px solid var(--linea);background:rgba(8,11,16,.82);
backdrop-filter:blur(10px);position:sticky;top:0;z-index:20}
.marca{display:flex;align-items:center;gap:12px;min-width:0}
.logo{font-size:19px;font-weight:750;letter-spacing:-.04em}
.logo span{color:var(--acento)}
.tag{font-size:11.5px;color:var(--tenue-2);padding:3px 8px;border:1px solid var(--linea-2);
border-radius:999px;white-space:nowrap}
.acciones{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.chip-score{display:inline-flex;align-items:center;gap:8px;height:var(--alto);padding:0 12px;
border:1px solid var(--linea-2);border-radius:999px;background:var(--panel-2);font-size:12.5px;color:var(--tenue)}
.chip-score b{font-size:13px;color:var(--txt)}
.chip-score .dot{width:8px;height:8px;border-radius:50%;background:var(--tenue-2)}
.chip-score.alta{border-color:rgba(61,220,151,.4)}
.chip-score.alta .dot{background:var(--ok);box-shadow:0 0 0 3px rgba(61,220,151,.16)}
.chip-score.media{border-color:rgba(245,192,74,.4)}
.chip-score.media .dot{background:var(--medio);box-shadow:0 0 0 3px rgba(245,192,74,.16)}
.chip-score.baja{border-color:rgba(248,113,113,.4)}
.chip-score.baja .dot{background:var(--mal);box-shadow:0 0 0 3px rgba(248,113,113,.16)}

/* ---------- layout ---------- */
main{display:grid;grid-template-columns:396px minmax(0,1fr);gap:20px;
padding:20px 24px 48px;align-items:start}
@media(max-width:1080px){main{grid-template-columns:1fr}.der{position:static!important}}
.izq{display:flex;flex-direction:column;gap:16px;min-width:0}
.der{position:sticky;top:74px;min-width:0}
.panel{background:linear-gradient(180deg,rgba(20,28,38,.9),rgba(15,21,29,.92));
border:1px solid var(--linea);border-radius:var(--radio);padding:14px}

/* ---------- tipografía y controles ---------- */
button,select,input,textarea{font-family:inherit}
.rotulo{font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.09em;color:var(--tenue-2)}
button{height:var(--alto);display:inline-flex;align-items:center;justify-content:center;gap:7px;
padding:0 13px;border:1px solid var(--linea-2);border-radius:9px;background:var(--panel-2);
color:var(--txt);font-size:12.5px;cursor:pointer;
transition:background .16s,border-color .16s,color .16s,transform .06s}
button:hover{background:var(--panel-3);border-color:#38506a}
button:active{transform:translateY(1px)}
button:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible,
input:focus-visible,.pestania:focus-visible,.op:focus-visible,.muestra:focus-visible,.seg:focus-visible{
outline:2px solid rgba(96,165,250,.65);outline-offset:2px}
button.principal{background:linear-gradient(180deg,#3d8bfd,#2f6fe0);border-color:#3577ea;
color:#fff;font-weight:600;box-shadow:0 8px 20px -12px rgba(59,130,246,.9)}
button.principal:hover{background:linear-gradient(180deg,#4b95ff,#3275e8)}
button.ghost{background:transparent;border-color:var(--linea-2)}
button.ghost:hover{background:var(--panel-2)}
button.ghost.activo{background:rgba(96,165,250,.16);border-color:rgba(96,165,250,.5);color:#dbeafe}
button.ancho{width:100%;margin-top:12px;height:38px}
button.mini{height:28px;padding:0 10px;font-size:11.5px;border-radius:8px}
button:disabled{opacity:.42;cursor:not-allowed}
button:disabled:hover{background:var(--panel-2);border-color:var(--linea-2)}
button.principal:disabled:hover{background:linear-gradient(180deg,#3d8bfd,#2f6fe0)}

/* ---------- pestañas ---------- */
.pestanias{display:flex;gap:4px;padding:3px;background:var(--panel-2);border:1px solid var(--linea);
border-radius:10px;margin-bottom:12px}
.pestania{flex:1;height:28px;border:0;background:transparent;border-radius:7px;color:var(--tenue);
font-size:12.5px;font-weight:500;display:inline-flex;align-items:center;justify-content:center;gap:7px}
.pestania:hover{background:var(--panel-3);color:var(--txt)}
.pestania.activa{background:var(--panel-3);color:var(--txt);box-shadow:0 1px 0 rgba(255,255,255,.04) inset}
.conteo{font-size:10.5px;color:var(--tenue-2);font-variant-numeric:tabular-nums}
.pestania.activa .conteo{color:var(--tenue)}

/* ---------- zona de carga ---------- */
.zona{border:1.5px dashed var(--linea-2);border-radius:12px;padding:12px;background:rgba(20,28,38,.6);
margin-bottom:10px;transition:border-color .16s,background .16s}
.zona:hover{border-color:#3a5168;background:rgba(26,36,49,.7)}
.zona.encima{border-color:var(--acento);background:rgba(96,165,250,.1)}
.carga{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.archivo-nombre{font-size:12px;color:var(--tenue);overflow:hidden;text-overflow:ellipsis;
white-space:nowrap;max-width:215px}
.zona small{display:block;margin-top:8px;font-size:11.5px;line-height:1.5;color:var(--tenue-2)}
.boton-archivo{display:inline-flex;align-items:center;justify-content:center;height:28px;padding:0 11px;
border:1px solid var(--linea-2);border-radius:8px;background:var(--panel-2);color:var(--txt);
font-size:12px;cursor:pointer;transition:background .16s,border-color .16s}
.boton-archivo:hover{background:var(--panel-3);border-color:#38506a}

textarea{width:100%;display:block;padding:11px 12px;resize:vertical;min-height:72px;
background:rgba(10,15,22,.7);color:var(--txt);border:1px solid var(--linea);border-radius:10px;
font-family:ui-monospace,Consolas,"Cascadia Mono",monospace;font-size:12px;line-height:1.6;
transition:border-color .16s,background .16s}
textarea:hover{border-color:var(--linea-2)}
textarea:focus{border-color:transparent;background:rgba(10,15,22,.95)}
textarea::placeholder{color:#566b80}
textarea.alta{min-height:290px}

.barra-cv{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px;flex-wrap:wrap}
.foto-control{display:flex;align-items:center;gap:8px}
.avatar{width:30px;height:30px;flex:none;border-radius:50%;display:grid;place-items:center;overflow:hidden;
background:var(--panel-2);border:1.5px dashed var(--linea-2);color:var(--tenue-2);font-size:14px;
transition:border-color .16s}
.avatar::before{content:"+"}
.avatar.con-foto{border-style:solid;border-color:var(--acento)}
.avatar.con-foto::before{content:""}
.avatar img{width:100%;height:100%;object-fit:cover}
.ayuda{margin:8px 0 0;font-size:11.5px;line-height:1.5;color:var(--tenue-2)}
kbd{font-family:inherit;font-size:10.5px;padding:1px 5px;border:1px solid var(--linea-2);
border-bottom-width:2px;border-radius:5px;background:var(--panel-2);color:var(--tenue)}

/* ---------- resultado ---------- */
.fila-score{display:flex;align-items:center;gap:14px}
.aro{width:68px;height:68px;flex:none;border-radius:50%;display:grid;place-items:center;
font-size:19px;font-weight:700;color:var(--tenue-2);border:5px solid var(--linea);
font-variant-numeric:tabular-nums;transition:border-color .25s,color .25s}
.aro.alta{border-color:var(--ok);color:var(--ok)}
.aro.media{border-color:var(--medio);color:var(--medio)}
.aro.baja{border-color:var(--mal);color:var(--mal)}
.veredicto{font-size:14.5px;font-weight:600}
.detalle{margin-top:2px;font-size:12.5px;line-height:1.45;color:var(--tenue)}
.progreso{height:4px;margin:14px 0 2px;border-radius:99px;background:var(--panel-3);overflow:hidden}
.progreso span{display:block;height:100%;width:0;border-radius:99px;background:var(--acento);
transition:width .45s cubic-bezier(.2,.7,.2,1),background .25s}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:11.5px;border:1px solid var(--linea-2);border-radius:999px;padding:3px 9px;color:var(--tenue)}
.chip.ok{border-color:rgba(61,220,151,.35);color:var(--ok);background:rgba(61,220,151,.07)}
.chip.mal{border-color:rgba(248,113,113,.35);color:var(--mal);background:rgba(248,113,113,.07)}
.bloque{margin-top:12px;border-top:1px solid var(--linea);padding-top:4px}
.bloque:first-of-type{border-top:0}
summary{display:flex;align-items:center;justify-content:space-between;gap:8px;cursor:pointer;
padding:7px 0;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;
color:var(--tenue-2);list-style:none;transition:color .16s}
summary::-webkit-details-marker{display:none}
summary:hover{color:var(--tenue)}
summary::after{content:"";width:6px;height:6px;border-right:1.5px solid currentColor;
border-bottom:1.5px solid currentColor;transform:rotate(45deg);transition:transform .2s}
details[open] summary::after{transform:rotate(-135deg)}
.lista{margin:2px 0 6px;padding-left:16px;font-size:12.5px;line-height:1.55;color:#c3d2e2}
.lista li{margin-bottom:5px}

/* ---------- ranking ---------- */
.ranking{display:flex;flex-direction:column;gap:6px}
.r-fila{display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--linea);
border-radius:10px;background:rgba(20,28,38,.5)}
.r-fila.gana{border-color:rgba(61,220,151,.34);background:rgba(61,220,151,.06)}
.r-pos{flex:none;width:18px;text-align:center;font-size:11.5px;color:var(--tenue-2);
font-variant-numeric:tabular-nums}
.r-fila.gana .r-pos{color:var(--ok)}
.r-info{flex:1;min-width:0}
.r-nombre{font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.r-meta{margin-top:2px;font-size:11.5px;color:var(--tenue-2);white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
.r-meta b{color:var(--txt);font-variant-numeric:tabular-nums}
.r-meta .falta{color:var(--mal)}
.r-fila button{flex:none}

/* ---------- preview ---------- */
.barra-diseno{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:10px 12px;
margin-bottom:12px;background:var(--panel);border:1px solid var(--linea);border-radius:12px}
.grupo{display:flex;align-items:center;gap:8px}
.segmentado{display:flex;gap:2px;padding:2px;background:var(--panel-2);border:1px solid var(--linea);
border-radius:9px}
.op{height:26px;padding:0 11px;border:0;border-radius:7px;background:transparent;color:var(--tenue);
font-size:12px;font-weight:500}
.op:hover{background:var(--panel-3);color:var(--txt)}
.op.activa{background:rgba(96,165,250,.18);color:#dbeafe;font-weight:600;
box-shadow:0 0 0 1px rgba(96,165,250,.4) inset}
.colores{display:flex;align-items:center;gap:6px}
.muestra{height:20px;width:20px;padding:0;border-radius:50%;background:var(--c);
border:1px solid rgba(255,255,255,.14);cursor:pointer;transition:transform .13s,box-shadow .13s}
.muestra:hover{transform:scale(1.14);border-color:rgba(255,255,255,.4)}
.muestra.activa{box-shadow:0 0 0 2px var(--panel),0 0 0 4px var(--c)}
input.muestra{-webkit-appearance:none;appearance:none;overflow:hidden;
background:conic-gradient(#f87171,#f5c04a,#3ddc97,#60a5fa,#a78bfa,#f87171)}
input.muestra::-webkit-color-swatch-wrapper{padding:0}
input.muestra::-webkit-color-swatch{border:0;border-radius:50%}
input.muestra::-moz-color-swatch{border:0;border-radius:50%}
.escalas{display:flex;gap:2px;padding:2px;background:var(--panel-2);border:1px solid var(--linea);border-radius:9px}
.seg{min-width:28px;height:26px;padding:0;border:0;border-radius:7px;background:transparent;
color:var(--tenue-2);font-weight:600;transition:background .16s,color .16s}
.seg:hover{background:var(--panel-3);color:var(--txt)}
.seg.activa{background:rgba(96,165,250,.18);color:#dbeafe;
box-shadow:0 0 0 1px rgba(96,165,250,.4) inset}
.marco{padding:16px;border-radius:16px;border:1px solid var(--linea);
background:
 linear-gradient(rgba(255,255,255,.02) 1px,transparent 1px) 0 0/24px 24px,
 linear-gradient(90deg,rgba(255,255,255,.02) 1px,transparent 1px) 0 0/24px 24px,
 #0c1219}
iframe{display:block;width:100%;height:calc(100vh - 210px);min-height:480px;
border:1px solid #d8dee6;border-radius:8px;background:#fff;
box-shadow:0 24px 60px -30px rgba(0,0,0,.9),0 2px 6px rgba(0,0,0,.35)}
@media(max-width:1080px){iframe{height:640px}}
.marco.vacio iframe{height:430px}
.marco.vacio{display:grid;place-items:center}

/* ---------- revisión ---------- */
.rev-cabecera{display:flex;align-items:center;gap:11px}
.rev-semaforo{width:11px;height:11px;flex:none;border-radius:50%;background:var(--tenue-2);
box-shadow:0 0 0 4px rgba(142,163,184,.12);transition:background .2s,box-shadow .2s}
.rev-semaforo.ok{background:var(--ok);box-shadow:0 0 0 4px rgba(61,220,151,.14)}
.rev-semaforo.medio{background:var(--medio);box-shadow:0 0 0 4px rgba(245,192,74,.14)}
.rev-semaforo.mal{background:var(--mal);box-shadow:0 0 0 4px rgba(248,113,113,.14)}
.rev-titulo{font-size:13.5px;font-weight:600}
.rev-detalle{margin-top:2px;font-size:12px;line-height:1.4;color:var(--tenue)}
.hallazgos{list-style:none;padding-left:0;margin:8px 0 0}
.hallazgo{display:flex;gap:9px;padding:7px 0;border-top:1px solid var(--linea)}
.hallazgo:first-child{border-top:0}
.h-nivel{flex:none;margin-top:4px;width:7px;height:7px;border-radius:50%;background:var(--tenue-2)}
.h-nivel.alto{background:var(--mal)}
.h-nivel.medio{background:var(--medio)}
.h-texto{margin:0;font-size:12.5px;line-height:1.45;color:#d3e0ee}
.h-texto b{color:var(--txt);font-weight:600}
.h-como{margin:2px 0 0;font-size:11.5px;line-height:1.45;color:var(--tenue-2)}
.reescritura{padding:8px 0;border-top:1px solid var(--linea)}
.reescritura:first-child{border-top:0}
.r-antes{font-size:11.5px;color:var(--tenue-2);text-decoration:line-through}
.r-despues{font-size:12.5px;color:#dbeafe}
.r-motivo{margin-top:3px;font-size:11.5px;line-height:1.45;color:var(--tenue-2)}
.guia-item{padding:8px 0;border-top:1px solid var(--linea)}
.guia-item:first-child{border-top:0}
.guia-nombre{font-size:12.5px;font-weight:600}
.guia-cuando{margin-top:1px;font-size:11.5px;color:#93c5fd}
.guia-detalle{margin-top:3px;font-size:11.5px;line-height:1.45;color:var(--tenue-2)}
.consejo{padding:8px 0;border-top:1px solid var(--linea)}
.consejo:first-child{border-top:0}
.consejo b{display:block;margin-bottom:3px;font-size:12.5px;font-weight:600}
.consejo ul{margin:0;padding-left:15px;font-size:11.5px;line-height:1.5;color:var(--tenue-2)}
.consejo li{margin-bottom:3px}

/* ---------- toast ---------- */
.toast{position:fixed;left:50%;bottom:22px;transform:translate(-50%,16px);z-index:40;
max-width:min(560px,calc(100vw - 32px));padding:10px 16px;border-radius:10px;font-size:12.5px;
background:var(--panel-3);border:1px solid var(--linea-2);color:var(--txt);
box-shadow:0 18px 40px -18px rgba(0,0,0,.9);opacity:0;pointer-events:none;
transition:opacity .18s,transform .18s}
.toast.visible{opacity:1;transform:translate(-50%,0)}
.toast.mal{border-color:rgba(248,113,113,.5);background:#25161a}
.toast.ok{border-color:rgba(61,220,151,.45);background:#0f1f1a}
.oculto{display:none}
</style>
</head>
<body>
<header class="appbar">
  <div class="marca">
    <div class="logo">cv<span>fit</span></div>
    <span class="tag">CV ↔ aviso · local</span>
  </div>
  <div class="acciones">
    <div class="chip-score oculto" id="chip-score"><span class="dot"></span><b id="chip-num">–</b><span id="chip-txt">sin analizar</span></div>
    <button id="editar" class="ghost" type="button" disabled title="Editar el CV en la vista previa">Editar</button>
    <button id="descargar" class="ghost" type="button" disabled title="Descargar el CV en PDF con lo editado">Descargar</button>
    <button id="imprimir" class="principal" type="button" disabled title="Imprimir o guardar como PDF">Imprimir / PDF</button>
  </div>
</header>

<main>
  <div class="izq">
    <section class="panel">
      <div class="pestanias" role="tablist" aria-label="Entradas">
        <button class="pestania activa" type="button" role="tab" data-tab="cv" aria-selected="true">Tu CV <span class="conteo" id="conteo-cv"></span></button>
        <button class="pestania" type="button" role="tab" data-tab="aviso" aria-selected="false">El aviso <span class="conteo" id="conteo-aviso"></span></button>
      </div>

      <div id="vista-cv" role="tabpanel">
        <div class="zona" id="zona">
          <div class="carga">
            <label class="boton-archivo" for="archivo">Elegir archivos</label>
            <span class="archivo-nombre" id="nombre-archivo">o soltalos acá</span>
          </div>
          <input type="file" id="archivo" class="oculto" accept=".md,.markdown,.txt,.docx,.pdf" multiple>
          <small>Markdown, TXT, Word (.docx) o PDF. Soltá <strong>varios</strong> y se comparan contra el mismo aviso. Los PDF escaneados no se pueden leer.</small>
        </div>
        <textarea id="cv" rows="12" placeholder="# Nombre&#10;**Título**&#10;&#10;## EXPERIENCIA&#10;- ..."></textarea>
        <div class="barra-cv">
          <div class="foto-control">
            <span class="avatar" id="avatar" title="Foto para el encabezado"><img id="miniatura" class="oculto" alt=""></span>
            <label class="boton-archivo" for="foto" title="En ATS la foto va en gris: los filtros leen texto">Foto</label>
            <input type="file" id="foto" class="oculto" accept="image/png,image/jpeg,image/webp">
            <button id="quitar-foto" class="mini oculto" type="button">Quitar</button>
          </div>
          <button id="ejemplo" class="mini" type="button">Cargar ejemplo</button>
          <button id="limpiar" class="mini" type="button" title="Borrar el CV, el aviso y la sesión guardada">Limpiar</button>
        </div>
      </div>

      <div id="vista-aviso" class="oculto" role="tabpanel">
        <textarea id="aviso" rows="12" class="alta" placeholder="Pegá el texto completo de la oferta..."></textarea>
        <p class="ayuda">Cuanto más completo el aviso, mejor la detección de excluyentes.
        <span style="white-space:nowrap"><kbd>Ctrl</kbd> + <kbd>Enter</kbd></span> analiza sin tocar el mouse.</p>
      </div>

      <button class="principal ancho" id="analizar" type="button">Analizar y adaptar</button>
    </section>

    <section class="panel" id="resultado">
      <div class="fila-score">
        <div class="aro" id="aro">–</div>
        <div>
          <div class="veredicto" id="veredicto">Sin analizar</div>
          <div class="detalle" id="detalle">Subí tu CV, pegá el aviso y apretá Analizar.</div>
        </div>
      </div>
      <div class="progreso"><span id="barra"></span></div>
      <div id="cubiertas" class="chips"></div>
      <div id="faltantes" class="chips"></div>
      <details class="bloque oculto" id="bloque-obs"><summary>Observaciones <span id="n-obs"></span></summary><ul class="lista" id="observaciones"></ul></details>
      <details class="bloque oculto" id="bloque-cambios"><summary>Qué cambió en el CV <span id="n-cambios"></span></summary><ul class="lista" id="cambios"></ul></details>
    </section>

    <section class="panel" id="panel-revision">
      <div class="rev-cabecera">
        <span class="rev-semaforo" id="rev-semaforo"></span>
        <div>
          <div class="rev-titulo">Revisión del CV</div>
          <div class="rev-detalle" id="rev-detalle">Pegá tu CV y te marco lo que miraría un reclutador.</div>
        </div>
      </div>
      <ul class="hallazgos" id="rev-hallazgos"></ul>
      <details class="bloque oculto" id="bloque-reescrituras">
        <summary>Reescrituras sugeridas <span id="n-reescrituras"></span></summary>
        <div id="reescrituras"></div>
      </details>
      <details class="bloque oculto" id="bloque-bien">
        <summary>Lo que ya está bien <span id="n-bien"></span></summary>
        <ul class="lista" id="rev-bien"></ul>
      </details>
      <details class="bloque" id="bloque-guia">
        <summary>Qué estilo va con qué</summary>
        <div id="rev-guia"></div>
      </details>
      <details class="bloque" id="bloque-consejos">
        <summary>Consejos de reclutamiento</summary>
        <div id="rev-consejos"></div>
      </details>
    </section>

    <section class="panel oculto" id="panel-ranking">
      <div class="rotulo" style="margin-bottom:8px">Varios CVs contra el mismo aviso</div>
      <div class="ranking" id="ranking"></div>
      <p class="ayuda">El ganador se carga solo. "Usar" cambia la versión que vas a mandar.</p>
    </section>
  </div>

  <div class="der">
    <div class="barra-diseno">
      <div class="grupo">
        <span class="rotulo">Estilo</span>
        <div class="segmentado" id="estilos" role="group" aria-label="Estilo del CV">
          <button class="op activa" type="button" data-estilo="ats" title="Una columna, sin adornos: lo que los filtros leen mejor">ATS</button>
          <button class="op" type="button" data-estilo="clasico" title="Una columna con acento de color">Clásico</button>
          <button class="op" type="button" data-estilo="compacto" title="Dos columnas, para perfiles largos">Compacto</button>
        </div>
      </div>
      <div class="grupo">
        <span class="rotulo">Color</span>
        <div class="colores" id="colores" aria-label="Color de acento">
          <button class="muestra" type="button" data-color="#000000" style="--c:#000000" title="Negro" aria-label="Negro"></button>
          <button class="muestra" type="button" data-color="#1f5f8b" style="--c:#1f5f8b" title="Azul" aria-label="Azul"></button>
          <button class="muestra" type="button" data-color="#0f766e" style="--c:#0f766e" title="Verde" aria-label="Verde"></button>
          <button class="muestra" type="button" data-color="#7c3aed" style="--c:#7c3aed" title="Violeta" aria-label="Violeta"></button>
          <button class="muestra" type="button" data-color="#b91c1c" style="--c:#b91c1c" title="Rojo" aria-label="Rojo"></button>
          <button class="muestra" type="button" data-color="#b45309" style="--c:#b45309" title="Ámbar" aria-label="Ámbar"></button>
          <input type="color" id="color-libre" class="muestra" value="#1f5f8b" title="Otro color" aria-label="Otro color">
        </div>
      </div>
      <div class="grupo">
        <span class="rotulo">Tamaño</span>
        <div class="escalas" id="escalas" role="group" aria-label="Tamaño de letra">
          <button class="seg" type="button" data-escala="0.9" title="Más chico" style="font-size:11px">A</button>
          <button class="seg activa" type="button" data-escala="1" title="Normal" style="font-size:13px">A</button>
          <button class="seg" type="button" data-escala="1.1" title="Más grande" style="font-size:15px">A</button>
          <button class="seg" type="button" data-escala="1.2" title="El más grande" style="font-size:17px">A</button>
        </div>
      </div>
    </div>
    <div class="marco"><iframe id="preview" title="Previsualización del CV"></iframe></div>
  </div>
</main>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script>
const $ = id => document.getElementById(id);
let temporizadorToast;
function avisar(texto, tipo) {
  const t = $('toast');
  t.textContent = texto;
  t.className = 'toast visible' + (tipo ? ' ' + tipo : '');
  clearTimeout(temporizadorToast);
  temporizadorToast = setTimeout(() => t.classList.remove('visible'), 4200);
}

const PLACEHOLDER = '<!doctype html><html><head><meta charset="utf-8"><style>'
  + 'body{margin:0;display:grid;place-items:center;height:100vh;background:#f4f6f9;color:#64748b;'
  + 'font-family:ui-sans-serif,system-ui,-apple-system,sans-serif}'
  + '.caja{margin:28px;padding:40px 34px;max-width:380px;text-align:center;background:#fff;'
  + 'border:1.5px dashed #cbd5e1;border-radius:14px}'
  + 'svg{display:block;margin:0 auto 14px;color:#94a3b8}'
  + 'h2{margin:0 0 7px;font-size:15px;font-weight:650;color:#334155}'
  + 'p{margin:0;font-size:13px;line-height:1.55;color:#7c8b9e}'
  + 'b{color:#475569;font-weight:600}'
  + '</style></head><body><div class="caja">'
  + '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"'
  + ' stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
  + '<path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/></svg>'
  + '<h2>Tu CV adaptado aparece acá</h2>'
  + '<p>Pegá el aviso en <b>El aviso</b> y apretá <b>Analizar y adaptar</b>.</p>'
  + '</div></body></html>';
$('preview').srcdoc = PLACEHOLDER;

// --- pestañas ---
function abrirPestania(nombre) {
  document.querySelectorAll('.pestania').forEach(p => {
    const activa = p.dataset.tab === nombre;
    p.classList.toggle('activa', activa);
    p.setAttribute('aria-selected', activa ? 'true' : 'false');
  });
  $('vista-cv').classList.toggle('oculto', nombre !== 'cv');
  $('vista-aviso').classList.toggle('oculto', nombre !== 'aviso');
}
document.querySelectorAll('.pestania').forEach(p => { p.onclick = () => abrirPestania(p.dataset.tab); });

function contar() {
  const cv = $('cv').value.length, aviso = $('aviso').value.length;
  $('conteo-cv').textContent = cv ? (cv > 999 ? Math.round(cv / 1000) + 'k' : cv) : '';
  $('conteo-aviso').textContent = aviso ? (aviso > 999 ? Math.round(aviso / 1000) + 'k' : aviso) : '';
}

$('ejemplo').onclick = async () => {
  const respuesta = await fetch('/api/ejemplo');
  $('cv').value = await respuesta.text();
  $('nombre-archivo').textContent = 'ejemplo.md';
  contar();
  actualizarRevision();
  guardarSesion();
  avisar('CV de ejemplo cargado.');
};

// --- ingesta: md/txt se leen en el navegador, docx/pdf en el servidor ---
let cargados = [];
let filasActuales = [];
let indiceEnUso = 0;

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
  $('nombre-archivo').textContent = archivos.map(a => a.name).join(' · ');
  avisar('Leyendo ' + archivos.length + (archivos.length > 1 ? ' archivos…' : ' archivo…'));
  cargados = [];
  const fallos = [];
  for (const archivo of archivos) {
    try {
      cargados.push({nombre: archivo.name, texto: await textoDeArchivo(archivo)});
    } catch (error) {
      fallos.push(archivo.name + ': ' + error.message);
    }
  }
  if (cargados.length) {
    $('cv').value = cargados[0].texto;
    contar();
    actualizarRevision();
    guardarSesion();
  }
  if (fallos.length) avisar(fallos.join(' · '), 'mal');
  if (!cargados.length) return;

  if (cargados.length > 1) {
    await compararCargados();
  } else {
    $('panel-ranking').classList.add('oculto');
    if (!fallos.length) avisar(cargados[0].nombre + ' cargado (' + cargados[0].texto.length + ' caracteres).', 'ok');
  }
}

function pintarRanking(filas) {
  filasActuales = filas;
  $('panel-ranking').classList.remove('oculto');
  $('ranking').innerHTML = filas.map((f, i) => {
    const meta = '<b>' + f.score + '%</b>' + (f.confiable ? '' : ' orientativo')
      + ' · ' + f.cubiertas.length + '/' + f.total_requisitos + ' respaldados'
      + (f.faltantes.length ? ' · <span class="falta">faltan ' + f.faltantes.map(escapar).join(', ') + '</span>' : '');
    return '<div class="r-fila' + (i === 0 ? ' gana' : '') + '">'
      + '<div class="r-pos">' + (i + 1) + '</div>'
      + '<div class="r-info">'
      + '<div class="r-nombre" title="' + escapar(f.nombre) + '">' + escapar(f.nombre) + '</div>'
      + '<div class="r-meta" title="' + escapar(f.faltantes.join(', ')) + '">' + meta + '</div>'
      + '</div>'
      + '<button class="mini" type="button" data-i="' + i + '"'
      + (i === indiceEnUso ? ' disabled' : '') + '>' + (i === indiceEnUso ? 'en uso' : 'usar') + '</button>'
      + '</div>';
  }).join('');
}

async function compararCargados() {
  const aviso = $('aviso').value.trim();
  if (!aviso) {
    $('panel-ranking').classList.add('oculto');
    abrirPestania('aviso');
    avisar('Cargué ' + cargados.length + ' CVs. Pegá el aviso para compararlos.', 'mal');
    return;
  }
  avisar('Comparando ' + cargados.length + ' CVs contra el aviso…');
  const r = await fetch('/api/comparar', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({cvs: cargados, aviso: aviso})
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) { avisar(datos.error || 'No pude comparar los CVs.', 'mal'); return; }

  pintarRanking(datos.filas);
  indiceEnUso = 0;
  const mejor = datos.filas[0];
  const elegido = cargados.find(c => c.nombre === mejor.nombre);
  if (elegido) { $('cv').value = elegido.texto; contar(); }
  pintarRanking(datos.filas);
  await actualizar(true);
  avisar('Gana ' + mejor.nombre + ' con ' + mejor.score + '%.', 'ok');
}

$('ranking').addEventListener('click', async evento => {
  const boton = evento.target.closest('button[data-i]');
  if (!boton || boton.disabled) return;
  const indice = Number(boton.dataset.i);
  const elegido = cargados.find(c => c.nombre === filasActuales[indice].nombre);
  if (!elegido) return;
  indiceEnUso = indice;
  $('cv').value = elegido.texto;
  contar();
  pintarRanking(filasActuales);
  await actualizar(true);
  avisar('Usando ' + elegido.nombre + '.');
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

$('cv').addEventListener('input', () => {
  cargados = [];
  $('panel-ranking').classList.add('oculto');
  contar();
  programarRevision();
  programarGuardado();
});
$('aviso').addEventListener('input', () => { contar(); programarGuardado(); });

// --- resultado ---
function pintar(r) {
  const clase = r.veredicto;
  $('aro').className = 'aro ' + clase;
  $('aro').textContent = r.score + '%';
  $('barra').style.width = r.score + '%';
  $('barra').style.background = {alta:'var(--ok)', media:'var(--medio)', baja:'var(--mal)'}[clase];
  $('veredicto').textContent = {alta:'Encaje alto', media:'Encaje medio', baja:'Encaje bajo'}[clase]
    + (r.confiable ? '' : ' · orientativo');
  $('detalle').textContent = r.cubiertas.length + ' de ' + r.total_requisitos + ' requisitos respaldados por tu CV.';
  $('cubiertas').innerHTML = r.cubiertas.map(s => '<span class="chip ok">' + escapar(s) + '</span>').join('');
  $('faltantes').innerHTML = [...r.faltantes, ...r.blandas_faltantes].map(s => '<span class="chip mal">' + escapar(s) + '</span>').join('');
  $('observaciones').innerHTML = r.observaciones.map(o => '<li>' + escapar(o) + '</li>').join('');
  $('cambios').innerHTML = (r.cambios || []).map(c => '<li>' + escapar(c) + '</li>').join('');
  $('n-obs').textContent = r.observaciones.length ? '(' + r.observaciones.length + ')' : '';
  $('n-cambios').textContent = (r.cambios || []).length ? '(' + r.cambios.length + ')' : '';
  $('bloque-obs').classList.toggle('oculto', !r.observaciones.length);
  $('bloque-obs').open = r.observaciones.length > 0;
  $('bloque-cambios').classList.toggle('oculto', !(r.cambios || []).length);
  $('bloque-cambios').open = false;

  const chip = $('chip-score');
  chip.classList.remove('oculto', 'alta', 'media', 'baja');
  chip.classList.add(clase);
  $('chip-num').textContent = r.score + '%';
  $('chip-txt').textContent = {alta:'encaje alto', media:'encaje medio', baja:'encaje bajo'}[clase];
}

// --- retoques: foto, color y tamaño ---
let fotoData = '';
let colorActual = '#1f5f8b';
let escalaActual = '1';
let estiloActual = 'ats';
let colorManual = false;
const COLOR_POR_ESTILO = {ats: '#000000', clasico: '#1f5f8b', compacto: '#111827'};

function ajustes() {
  return {
    cv: $('cv').value, aviso: $('aviso').value, estilo: estiloActual,
    foto: fotoData, acento: colorActual, escala: escalaActual
  };
}

async function pintarPreview() {
  const marco = document.querySelector('.marco');
  if (!$('cv').value.trim()) {
    $('preview').srcdoc = PLACEHOLDER;
    marco.classList.add('vacio');
    marcarAcciones(false);
    return;
  }
  const p = await fetch('/api/render', {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(ajustes())
  });
  $('preview').srcdoc = await p.text();
  marco.classList.remove('vacio');
  marcarAcciones(true);
}

// Editar / Descargar / Imprimir solo tienen sentido cuando hay CV renderizado.
function marcarAcciones(activas) {
  ['editar', 'descargar', 'imprimir'].forEach(id => { $(id).disabled = !activas; });
  if (!activas) {
    editando = false;
    $('editar').textContent = 'Editar';
    $('editar').classList.remove('activo');
  }
}

async function actualizar(renderizar) {
  const r = await fetch('/api/analizar', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({cv: $('cv').value, aviso: $('aviso').value})});
  pintar(await r.json());
  if (renderizar) await pintarPreview();
}

// --- revisión del CV: reglas explícitas, sin IA ---
const AREAS = {
  contacto: 'Contacto', estructura: 'Estructura', fechas: 'Fechas',
  redaccion: 'Redacción', formato: 'Formato'
};
let temporizadorRevision;

function pintarRevision(r) {
  $('rev-guia').innerHTML = r.guia.map(g =>
    '<div class="guia-item"><div class="guia-nombre">' + escapar(g.nombre) + '</div>'
    + '<div class="guia-cuando">' + escapar(g.cuando) + '</div>'
    + '<div class="guia-detalle">' + escapar(g.detalle) + '</div></div>'
  ).join('');
  $('rev-consejos').innerHTML = r.consejos.map(c =>
    '<div class="consejo"><b>' + escapar(c.titulo) + '</b><ul>'
    + c.cuerpo.map(p => '<li>' + escapar(p) + '</li>').join('') + '</ul></div>'
  ).join('');

  if (r.vacio) { vaciarRevision(); return; }

  $('rev-semaforo').className = 'rev-semaforo ' + r.estado;
  if (r.estado === 'ok') {
    $('rev-detalle').textContent = 'Nada grave: está listo para mandar.';
  } else if (r.estado === 'mal') {
    $('rev-detalle').textContent = r.altos + (r.altos === 1 ? ' punto que puede descartarte' : ' puntos que pueden descartarte')
      + (r.medios ? ' y ' + r.medios + ' para pulir.' : '.');
  } else {
    const n = r.hallazgos.length;
    $('rev-detalle').textContent = n + (n === 1 ? ' punto para pulir antes de enviar.' : ' puntos para pulir antes de enviar.');
  }

  $('rev-hallazgos').innerHTML = r.hallazgos.map(h =>
    '<li class="hallazgo"><span class="h-nivel ' + h.nivel + '"></span><div>'
    + '<p class="h-texto"><b>' + (AREAS[h.area] || escapar(h.area)) + ':</b> ' + escapar(h.mensaje) + '</p>'
    + '<p class="h-como">' + escapar(h.como) + '</p></div></li>'
  ).join('');

  $('reescrituras').innerHTML = r.reescrituras.map(x =>
    '<div class="reescritura"><div class="r-antes">' + escapar(x.original) + '</div>'
    + '<div class="r-despues">' + escapar(x.propuesta) + '</div>'
    + '<div class="r-motivo">' + escapar(x.motivo) + '</div></div>'
  ).join('');
  $('n-reescrituras').textContent = r.reescrituras.length ? '(' + r.reescrituras.length + ')' : '';
  $('bloque-reescrituras').classList.toggle('oculto', !r.reescrituras.length);
  $('bloque-reescrituras').open = r.reescrituras.length > 0 && r.reescrituras.length <= 3;

  $('rev-bien').innerHTML = r.bien.map(b => '<li>' + escapar(b) + '</li>').join('');
  $('n-bien').textContent = r.bien.length ? '(' + r.bien.length + ')' : '';
  $('bloque-bien').classList.toggle('oculto', !r.bien.length);
}

function vaciarRevision() {
  $('rev-semaforo').className = 'rev-semaforo';
  $('rev-detalle').textContent = 'Pegá tu CV y te marco lo que miraría un reclutador.';
  $('rev-hallazgos').innerHTML = '';
  $('bloque-reescrituras').classList.add('oculto');
  $('bloque-bien').classList.add('oculto');
}

async function actualizarRevision() {
  const r = await fetch('/api/revisar', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({cv: $('cv').value, estilo: estiloActual})});
  if (!r.ok) { vaciarRevision(); return; }
  pintarRevision(await r.json());
}

function programarRevision() {
  clearTimeout(temporizadorRevision);
  temporizadorRevision = setTimeout(actualizarRevision, 650);
}


function marcarColor() {
  const hex = colorActual.toLowerCase();
  let encontrado = false;
  document.querySelectorAll('#colores .muestra[data-color]').forEach(boton => {
    const activo = boton.dataset.color.toLowerCase() === hex;
    boton.classList.toggle('activa', activo);
    boton.setAttribute('aria-pressed', activo ? 'true' : 'false');
    if (activo) encontrado = true;
  });
  const libre = $('color-libre');
  libre.classList.toggle('activa', !encontrado);
  libre.value = hex;
}

function ajustarColorPorEstilo() {
  if (colorManual) return;
  colorActual = COLOR_POR_ESTILO[estiloActual] || '#1f5f8b';
  marcarColor();
}

$('colores').addEventListener('click', evento => {
  const boton = evento.target.closest('.muestra[data-color]');
  if (!boton) return;
  colorManual = true;
  colorActual = boton.dataset.color;
  marcarColor();
  actualizar(true);
  programarRevision();
  guardarSesion();
});

let temporizadorColor;
$('color-libre').oninput = () => {
  colorManual = true;
  colorActual = $('color-libre').value;
  marcarColor();
  clearTimeout(temporizadorColor);
  temporizadorColor = setTimeout(() => { actualizar(true); guardarSesion(); }, 220);
};

$('escalas').addEventListener('click', evento => {
  const boton = evento.target.closest('.seg');
  if (!boton) return;
  escalaActual = boton.dataset.escala;
  document.querySelectorAll('#escalas .seg').forEach(s => s.classList.toggle('activa', s === boton));
  actualizar(true);
  guardarSesion();
});

$('estilos').addEventListener('click', evento => {
  const boton = evento.target.closest('.op');
  if (!boton) return;
  estiloActual = boton.dataset.estilo;
  document.querySelectorAll('#estilos .op').forEach(s => s.classList.toggle('activa', s === boton));
  ajustarColorPorEstilo();
  actualizar(true);
  programarRevision();
  guardarSesion();
});

$('foto').onchange = evento => {
  const archivo = evento.target.files[0];
  if (!archivo) return;
  if (archivo.size > 2 * 1024 * 1024) {
    avisar('La foto pasa los 2 MB: usá una más liviana o recortala.', 'mal');
    return;
  }
  const lector = new FileReader();
  lector.onload = async () => {
    fotoData = lector.result;
    $('miniatura').src = fotoData;
    $('miniatura').classList.remove('oculto');
    $('avatar').classList.add('con-foto');
    $('quitar-foto').classList.remove('oculto');
    await actualizar(true);
    guardarSesion();
    avisar('Foto cargada (' + Math.max(1, Math.round(archivo.size / 1024)) + ' KB).', 'ok');
  };
  lector.readAsDataURL(archivo);
};

$('quitar-foto').onclick = async () => {
  fotoData = '';
  $('miniatura').src = '';
  $('miniatura').classList.add('oculto');
  $('avatar').classList.remove('con-foto');
  $('quitar-foto').classList.add('oculto');
  $('foto').value = '';
  await actualizar(true);
  guardarSesion();
  avisar('Foto quitada.');
};

async function analizar() {
  if (!$('cv').value.trim()) { abrirPestania('cv'); avisar('Falta el CV: subí un archivo o pegá el texto.', 'mal'); return; }
  if (!$('aviso').value.trim()) { abrirPestania('aviso'); avisar('Falta el texto del aviso.', 'mal'); return; }
  if (cargados.length > 1) { await compararCargados(); return; }
  const boton = $('analizar');
  boton.disabled = true;
  const original = boton.textContent;
  boton.textContent = 'Analizando…';
  try {
    await actualizar(true);
    await actualizarRevision();
    guardarSesion();
    avisar('Listo. Revisá los gaps y el CV adaptado.', 'ok');
  } finally {
    boton.disabled = false;
    boton.textContent = original;
  }
}

$('analizar').onclick = analizar;
document.addEventListener('keydown', evento => {
  if ((evento.ctrlKey || evento.metaKey) && evento.key === 'Enter') { evento.preventDefault(); analizar(); }
});

$('imprimir').onclick = () => {
  if (!$('preview').contentDocument.querySelector('.hoja')) { avisar('Primero analizá el CV.', 'mal'); return; }
  $('preview').contentWindow.print();
};

// --- edición directa + descarga ---
let editando = false;
$('editar').onclick = () => {
  const doc = $('preview').contentDocument;
  const hoja = doc && doc.querySelector('.hoja');
  if (!hoja) { avisar('Primero analizá el CV.', 'mal'); return; }
  if (editando) {
    hoja.contentEditable = 'false';
    hoja.style.outline = '';
  } else {
    hoja.contentEditable = 'true';
    hoja.style.outline = '2px dashed #60a5fa';
    hoja.style.outlineOffset = '6px';
  }
  editando = !editando;
  $('editar').textContent = editando ? 'Terminar' : 'Editar';
  $('editar').classList.toggle('activo', editando);
  avisar(editando
    ? 'Tocá el CV en la vista previa: lo que dejes así es lo que se imprime y se descarga.'
    : 'Edición terminada. Si cambiás de estilo, color o analizás de nuevo, el CV se regenera.');
};

function nombreDeArchivo() {
  const hallado = $('cv').value.match(/^#\\s+(.+)$/m);
  const base = (hallado ? hallado[1] : 'cv')
    .normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
    .replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return 'CV_' + (base || 'cv') + '.pdf';
}

function bajarHtml(html) {
  const enlace = document.createElement('a');
  enlace.href = URL.createObjectURL(new Blob([html], {type: 'text/html;charset=utf-8'}));
  enlace.download = nombreDeArchivo().replace(/\\.pdf$/i, '.html');
  enlace.click();
  setTimeout(() => URL.revokeObjectURL(enlace.href), 2000);
}

$('descargar').onclick = async () => {
  const doc = $('preview').contentDocument;
  if (!doc || !doc.querySelector('.hoja')) { avisar('Primero analizá el CV.', 'mal'); return; }
  const boton = $('descargar');
  const original = boton.textContent;
  boton.disabled = true;
  boton.textContent = 'Generando…';
  const html = '<!doctype html>' + doc.documentElement.outerHTML;
  const nombre = nombreDeArchivo();
  try {
    const r = await fetch('/api/pdf', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({html: html, nombre: nombre})});
    if (r.ok) {
      const enlace = document.createElement('a');
      enlace.href = URL.createObjectURL(await r.blob());
      enlace.download = nombre;
      enlace.click();
      setTimeout(() => URL.revokeObjectURL(enlace.href), 4000);
      avisar('Descargado: ' + nombre, 'ok');
      return;
    }
    const datos = await r.json().catch(() => ({}));
    bajarHtml(html);
    avisar((datos.error || 'No pude generar el PDF') + '. Bajé el .html: abrilo e imprimí desde ahí.', 'mal');
  } catch (error) {
    bajarHtml(html);
    avisar('Se cayó la conexión con el servidor. Bajé el .html como respaldo.', 'mal');
  } finally {
    boton.disabled = false;
    boton.textContent = original;
  }
};

// --- sesión: un refresco no borra lo pegado ---
const CLAVE_SESION = 'cvfit.sesion.v1';
let temporizadorGuardado;

function guardarSesion() {
  try {
    localStorage.setItem(CLAVE_SESION, JSON.stringify({
      cv: $('cv').value, aviso: $('aviso').value, estilo: estiloActual,
      color: colorActual, escala: escalaActual, foto: fotoData, colorManual: colorManual
    }));
  } catch (error) { /* cuota llena o modo privado: se sigue sin guardar */ }
}

function programarGuardado() {
  clearTimeout(temporizadorGuardado);
  temporizadorGuardado = setTimeout(guardarSesion, 500);
}

function limpiarSesion() {
  try { localStorage.removeItem(CLAVE_SESION); } catch (error) { /* nada */ }
}

function marcarEstilo(valor) {
  document.querySelectorAll('#estilos .op').forEach(s => {
    s.classList.toggle('activa', s.dataset.estilo === valor);
  });
}

function marcarEscala(valor) {
  document.querySelectorAll('#escalas .seg').forEach(s => {
    s.classList.toggle('activa', s.dataset.escala === valor);
  });
}

function restaurarSesion() {
  let datos = null;
  try { datos = JSON.parse(localStorage.getItem(CLAVE_SESION) || 'null'); } catch (error) { datos = null; }
  if (!datos || typeof datos !== 'object') return false;

  if (datos.cv) $('cv').value = datos.cv;
  if (datos.aviso) $('aviso').value = datos.aviso;
  if (datos.estilo) { estiloActual = datos.estilo; marcarEstilo(estiloActual); }
  if (datos.escala) { escalaActual = String(datos.escala); marcarEscala(escalaActual); }
  if (datos.foto) {
    fotoData = datos.foto;
    $('miniatura').src = fotoData;
    $('miniatura').classList.remove('oculto');
    $('avatar').classList.add('con-foto');
    $('quitar-foto').classList.remove('oculto');
  }
  if (datos.color) {
    colorManual = Boolean(datos.colorManual);
    colorActual = datos.color;
    marcarColor();
  }
  contar();
  return Boolean(datos.cv || datos.aviso || datos.foto);
}

$('limpiar').onclick = () => {
  limpiarSesion();
  $('cv').value = '';
  $('aviso').value = '';
  $('nombre-archivo').textContent = 'o soltalos acá';
  cargados = [];
  indiceEnUso = 0;
  $('panel-ranking').classList.add('oculto');
  fotoData = '';
  $('miniatura').src = '';
  $('miniatura').classList.add('oculto');
  $('avatar').classList.remove('con-foto');
  $('quitar-foto').classList.add('oculto');
  $('foto').value = '';
  colorManual = false;
  ajustarColorPorEstilo();
  contar();
  vaciarRevision();
  marcarAcciones(false);
  $('preview').srcdoc = PLACEHOLDER;
  document.querySelector('.marco').classList.add('vacio');
  $('chip-score').classList.add('oculto');
  $('chip-score').className = 'chip-score oculto';
  $('aro').className = 'aro';
  $('aro').textContent = '–';
  $('barra').style.width = '0';
  $('veredicto').textContent = 'Sin analizar';
  $('detalle').textContent = 'Subí tu CV, pegá el aviso y apretá Analizar.';
  $('cubiertas').innerHTML = '';
  $('faltantes').innerHTML = '';
  $('bloque-obs').classList.add('oculto');
  $('bloque-cambios').classList.add('oculto');
  avisar('Listo: empezás de cero.');
};

ajustarColorPorEstilo();
contar();
const recuperado = restaurarSesion();
actualizarRevision();
if (recuperado) {
  pintarPreview();
  if ($('cv').value.trim() && $('aviso').value.trim()) actualizar(true);
  avisar('Recuperé lo último que tenías: CV, aviso y diseño.', 'ok');
}
</script>
</body>
</html>
"""


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):  # silencio en consola
        return

    @staticmethod
    def _texto(datos: dict, clave: str) -> str:
        """Campo de texto del payload, tolerante a un cliente que mande otra cosa."""
        valor = datos.get(clave)
        return valor.strip() if isinstance(valor, str) else ""

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

    def _revisar(self, datos: dict) -> None:
        """Reglas explícitas: no inventa experiencia, sólo marca qué conviene mejorar."""
        texto = self._texto(datos, "cv")
        cuerpo: dict = {"guia": GUIA_ESTILOS, "consejos": CONSEJOS}
        if not texto:
            cuerpo.update(
                {
                    "vacio": True,
                    "estado": "ok",
                    "altos": 0,
                    "medios": 0,
                    "hallazgos": [],
                    "reescrituras": [],
                    "bien": [],
                }
            )
            self._json(200, cuerpo)
            return

        revision = revisar(parsear(texto), datos.get("estilo", "ats"))
        cuerpo.update(
            {
                "vacio": False,
                "estado": revision.estado,
                "altos": revision.altos,
                "medios": revision.medios,
                "hallazgos": [
                    {"area": h.area, "nivel": h.nivel, "mensaje": h.mensaje, "como": h.como}
                    for h in revision.hallazgos
                ],
                "reescrituras": [
                    {"original": r.original, "propuesta": r.propuesta, "motivo": r.motivo}
                    for r in revision.reescrituras
                ],
                "bien": revision.bien,
            }
        )
        self._json(200, cuerpo)

    def _pdf(self, datos: dict) -> None:
        """PDF del HTML del iframe, así se respeta lo que se editó a mano en la vista previa."""
        html = self._texto(datos, "html")
        if not html:
            if not self._texto(datos, "cv"):
                self._json(400, {"error": "no hay CV para pasar a PDF"})
                return
            cv = parsear(self._texto(datos, "cv"))
            html = render(
                adaptar(cv, datos.get("aviso") or ""),
                datos.get("estilo", "ats"),
                foto=datos.get("foto"),
                acento=datos.get("acento"),
                escala=datos.get("escala"),
            )

        nombre = normalize("NFKD", Path(str(datos.get("nombre") or "cv")).name)
        nombre = nombre.encode("ascii", "ignore").decode("ascii").replace(" ", "_")
        nombre = "".join(c for c in nombre if c.isalnum() or c in "._-") or "cv"
        if not nombre.lower().endswith(".pdf"):
            nombre += ".pdf"

        try:
            with tempfile.TemporaryDirectory(prefix="cvfit-entrega-") as temporal:
                cuerpo = a_pdf(html, Path(temporal) / "cv.pdf").read_bytes()
        except PdfError as error:
            self._json(503, {"error": str(error)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Content-Disposition", f'attachment; filename="{nombre}"')
        self.end_headers()
        self.wfile.write(cuerpo)

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
        if not isinstance(datos, dict):
            self._json(400, {"error": "el cuerpo tiene que ser un objeto JSON"})
            return

        cv_texto = self._texto(datos, "cv")
        aviso_texto = self._texto(datos, "aviso")

        if ruta == "/api/revisar":
            self._revisar(datos)
            return
        if ruta == "/api/pdf":
            self._pdf(datos)
            return

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
            html = render(
                adaptado,
                datos.get("estilo", "ats"),
                foto=datos.get("foto"),
                acento=datos.get("acento"),
                escala=datos.get("escala"),
            )
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
