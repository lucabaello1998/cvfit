"""Plantillas de salida. Tres estilos, todos print-ready en A4.

`ats`: una columna, sin color, sin tablas, sin íconos — lo que los parsers leen bien.
`clasico`: una columna con jerarquía tipográfica y un acento discreto.
`compacto`: dos columnas, denso, para perfiles largos.

Los tres aceptan foto y color de acento, pero sólo si se piden: sin foto ni color, el ATS sale
igual de limpio que antes.
"""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path

from .adaptar import Adaptado

BASE = """
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:"Segoe UI",Calibri,Arial,Helvetica,sans-serif;color:#111;background:#fff;
font-size:calc(10.5pt * var(--escala,1));line-height:1.42;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.hoja{width:210mm;min-height:297mm;margin:0 auto;padding:14mm 16mm;background:#fff}
.encabezado{display:flex;align-items:center;gap:8mm;margin:0 0 10px}
.encabezado .quien{flex:1;min-width:0}
.foto{width:24mm;height:24mm;object-fit:cover;border-radius:50%;border:2px solid var(--acento,#1f5f8b)}
h1{margin:0;font-size:calc(21pt * var(--escala,1));letter-spacing:-.02em}
.titular{margin:2px 0 4px;font-size:calc(11pt * var(--escala,1))}
.contacto{margin:0 0 10px;font-size:calc(9.5pt * var(--escala,1));color:#333}
.encabezado .contacto{margin:0}
h2{font-size:calc(10.5pt * var(--escala,1));text-transform:uppercase;letter-spacing:.09em;margin:14px 0 6px;
padding-bottom:3px;border-bottom:1px solid #bbb}
h3{font-size:calc(10.5pt * var(--escala,1));margin:9px 0 1px}
.sub{font-size:calc(9.5pt * var(--escala,1));color:#444;margin:0 0 3px}
p{margin:0 0 6px}
ul{margin:2px 0 6px;padding-left:16px}
li{margin:0 0 3px}
.resumen{margin:0 0 10px}
.tabla-linea{margin:0 0 3px;font-size:calc(9.8pt * var(--escala,1))}
.ocultar-print{display:none}
@page{size:A4;margin:0}
@media print{
  body{background:#fff}
  .hoja{margin:0;padding:14mm 16mm;width:auto;min-height:auto}
  .ocultar-print{display:none}
  h2{break-after:avoid}
  h3{break-after:avoid}
  li{break-inside:avoid}
}
"""

ATS = """
:root{--acento:#000}
body{font-family:Arial,Helvetica,sans-serif;font-size:calc(10.5pt * var(--escala,1));color:#000}
h1{font-size:calc(18pt * var(--escala,1))}
h2{font-size:calc(10.5pt * var(--escala,1));border-bottom:1px solid var(--acento,#000);text-transform:uppercase;letter-spacing:.06em}
.titular,.contacto,.sub{color:#000}
.foto{border-radius:0;border:0;width:20mm;height:20mm;filter:grayscale(100%)}
"""

CLASICO = """
:root{--acento:#1f5f8b}
h1{font-size:calc(22pt * var(--escala,1));color:#101820}
.titular{color:var(--acento);font-weight:600}
h2{color:var(--acento);border-bottom:1.5px solid var(--acento)}
h3{color:#101820}
"""

COMPACTO = """
:root{--acento:#111827}
.hoja{padding:12mm 14mm}
h1{font-size:calc(19pt * var(--escala,1))}
h2{margin:11px 0 5px;break-after:avoid;color:var(--acento);border-bottom:1.5px solid var(--acento)}
.cuerpo-dos{column-count:2;column-gap:13mm}
.cuerpo-dos h2{margin-top:10px}
li{break-inside:avoid}
.foto{width:20mm;height:20mm}
"""

CSS = {"ats": BASE + ATS, "clasico": BASE + CLASICO, "compacto": BASE + COMPACTO}

NOMBRES = {
    "ats": "ATS (una columna, sin adornos)",
    "clasico": "Clásico (una columna, con acento)",
    "compacto": "Compacto (dos columnas)",
}

ACENTOS = ("#1f5f8b", "#0f766e", "#7c3aed", "#b91c1c", "#b45309", "#111827")

FOTO_VALIDA = re.compile(r"^data:image/(?:png|jpe?g|webp);base64,[A-Za-z0-9+/=]+$")
COLOR_VALIDO = re.compile(r"^#[0-9a-fA-F]{6}$")
MAXIMO_FOTO = 3_000_000  # ~2 MB de imagen en base64


def _e(texto: str) -> str:
    return html.escape(str(texto or ""))


def foto_segura(foto: str | None) -> str:
    """Sólo acepta data URI de imagen (png/jpg/webp). Cualquier otra cosa se descarta en silencio."""
    if not foto:
        return ""
    limpia = re.sub(r"\s+", "", foto.strip())
    if len(limpia) > MAXIMO_FOTO or not FOTO_VALIDA.match(limpia):
        return ""
    return limpia


def color_seguro(acento: str | None) -> str:
    if acento and COLOR_VALIDO.match(acento.strip()):
        return acento.strip()
    return ""


MIMES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAXIMO_ARCHIVO = 2 * 1024 * 1024


def foto_desde_archivo(ruta) -> str:
    """Lee una imagen local y la convierte en data URI (la foto tampoco viaja a ningún lado)."""
    camino = Path(ruta)
    mime = MIMES.get(camino.suffix.lower())
    if not mime:
        raise ValueError(f"formato de foto no soportado: {camino.suffix or 'sin extensión'} (usá png, jpg o webp)")
    if not camino.is_file():
        raise ValueError(f"no encuentro la foto: {camino}")
    datos = camino.read_bytes()
    if len(datos) > MAXIMO_ARCHIVO:
        raise ValueError(f"la foto supera {MAXIMO_ARCHIVO // (1024 * 1024)} MB")
    return f"data:{mime};base64,{base64.b64encode(datos).decode('ascii')}"


def _seccion_html(seccion, compacta: bool = False) -> str:
    partes = [f"<h2>{_e(seccion.nombre)}</h2>"]
    for parrafo in seccion.parrafos:
        partes.append(f"<p>{_e(parrafo)}</p>")
    if seccion.bullets:
        partes.append("<ul>" + "".join(f"<li>{_e(b)}</li>" for b in seccion.bullets) + "</ul>")
    for fila in seccion.tabla:
        if len(fila) >= 2:
            partes.append(f'<p class="tabla-linea"><b>{_e(fila[0])}</b>: {_e(" · ".join(fila[1:]))}</p>')
    for bloque in seccion.bloques:
        if bloque.nivel == 1:
            if bloque.titulo:
                partes.append(f"<h3>{_e(bloque.titulo)}</h3>")
            if bloque.subtitulo:
                partes.append(f'<p class="sub">{_e(bloque.subtitulo)}</p>')
        else:
            partes.append(f'<p class="sub"><b>{_e(bloque.subtitulo)}</b></p>')
        if bloque.bullets:
            partes.append("<ul>" + "".join(f"<li>{_e(b)}</li>" for b in bloque.bullets) + "</ul>")
    return "".join(partes)


def render(
    adaptado: Adaptado,
    estilo: str = "ats",
    *,
    foto: str | None = None,
    acento: str | None = None,
    escala: float | str | None = None,
) -> str:
    """HTML del CV. Sin foto ni acento, la salida es la de siempre."""
    estilo = estilo if estilo in CSS else "ats"
    cuerpo: list[str] = []

    if estilo == "compacto":
        cuerpo.append('<div class="cuerpo-dos">')
        cuerpo.extend(_seccion_html(s, True) for s in adaptado.secciones)
        cuerpo.append("</div>")
    else:
        cuerpo.extend(_seccion_html(s) for s in adaptado.secciones)

    imagen = foto_segura(foto)
    color = color_seguro(acento)
    try:
        factor = float(escala) if escala not in (None, "") else 1.0
    except (TypeError, ValueError):
        factor = 1.0
    factor = min(1.3, max(0.85, factor))

    ajustes: list[str] = []
    if color:
        ajustes.append(f":root{{--acento:{color}}}")
    if abs(factor - 1.0) > 1e-9:
        ajustes.append(f":root{{--escala:{factor:g}}}")

    cabecera = f"""<div class="encabezado">
  {f'<img class="foto" src="{imagen}" alt="">' if imagen else ""}
  <div class="quien">
    <h1>{_e(adaptado.nombre)}</h1>
    <p class="titular">{_e(adaptado.titulo)}</p>
    <p class="contacto">{_e(adaptado.contacto)}</p>
  </div>
</div>"""

    return f"""<!doctype html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(adaptado.nombre)} — CV</title>
<style>{CSS[estilo]}{"".join(ajustes)}</style>
</head>
<body class="estilo-{estilo}">
<div class="hoja">
  {cabecera}
  <div class="resumen"><p>{_e(adaptado.resumen)}</p></div>
  {"".join(cuerpo)}
</div>
</body>
</html>
"""
