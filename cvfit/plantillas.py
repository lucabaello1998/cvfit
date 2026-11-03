"""Plantillas de salida. Tres estilos, todos print-ready en A4.

`ats`: una columna, sin color, sin tablas, sin íconos — lo que los parsers leen bien.
`clasico`: una columna con jerarquía tipográfica y un acento discreto.
`compacto`: dos columnas, denso, para perfiles largos.
"""

from __future__ import annotations

import html

from .adaptar import Adaptado

BASE = """
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:"Segoe UI",Calibri,Arial,Helvetica,sans-serif;color:#111;background:#fff;
font-size:10.5pt;line-height:1.42;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.hoja{width:210mm;min-height:297mm;margin:0 auto;padding:14mm 16mm;background:#fff}
h1{margin:0;font-size:21pt;letter-spacing:-.02em}
.titular{margin:2px 0 4px;font-size:11pt}
.contacto{margin:0 0 10px;font-size:9.5pt;color:#333}
h2{font-size:10.5pt;text-transform:uppercase;letter-spacing:.09em;margin:14px 0 6px;
padding-bottom:3px;border-bottom:1px solid #bbb}
h3{font-size:10.5pt;margin:9px 0 1px}
.sub{font-size:9.5pt;color:#444;margin:0 0 3px}
p{margin:0 0 6px}
ul{margin:2px 0 6px;padding-left:16px}
li{margin:0 0 3px}
.resumen{margin:0 0 10px}
.tabla-linea{margin:0 0 3px;font-size:9.8pt}
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
body{font-family:Arial,Helvetica,sans-serif;font-size:10.5pt;color:#000}
h1{font-size:18pt}
h2{font-size:10.5pt;border-bottom:1px solid #000;text-transform:uppercase;letter-spacing:.06em}
.titular,.contacto,.sub{color:#000}
"""

CLASICO = """
:root{--acento:#1f5f8b}
h1{font-size:22pt;color:#101820}
.titular{color:var(--acento);font-weight:600}
h2{color:var(--acento);border-bottom:1.5px solid var(--acento)}
h3{color:#101820}
"""

COMPACTO = """
.hoja{padding:12mm 14mm}
h1{font-size:19pt}
h2{margin:11px 0 5px;break-after:avoid}
.cuerpo-dos{column-count:2;column-gap:13mm}
.cuerpo-dos h2{margin-top:10px}
li{break-inside:avoid}
"""

CSS = {"ats": BASE + ATS, "clasico": BASE + CLASICO, "compacto": BASE + COMPACTO}

NOMBRES = {
    "ats": "ATS (una columna, sin adornos)",
    "clasico": "Clásico (una columna, con acento)",
    "compacto": "Compacto (dos columnas)",
}


def _e(texto: str) -> str:
    return html.escape(str(texto or ""))


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


def render(adaptado: Adaptado, estilo: str = "ats") -> str:
    estilo = estilo if estilo in CSS else "ats"
    cuerpo: list[str] = []

    if estilo == "compacto":
        cuerpo.append('<div class="cuerpo-dos">')
        cuerpo.extend(_seccion_html(s, True) for s in adaptado.secciones)
        cuerpo.append("</div>")
    else:
        cuerpo.extend(_seccion_html(s) for s in adaptado.secciones)

    return f"""<!doctype html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(adaptado.nombre)} — CV</title>
<style>{CSS[estilo]}</style>
</head>
<body>
<div class="hoja">
  <h1>{_e(adaptado.nombre)}</h1>
  <p class="titular">{_e(adaptado.titulo)}</p>
  <p class="contacto">{_e(adaptado.contacto)}</p>
  <div class="resumen"><p>{_e(adaptado.resumen)}</p></div>
  {"".join(cuerpo)}
</div>
</body>
</html>
"""
