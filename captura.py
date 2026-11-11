"""Capturas para el README: arma un estado demo con el motor real y lo fotografía con Chrome.

No hay atajos visuales: los números, los hallazgos y el CV de la vista previa salen de las mismas
funciones que usa la app; sólo se pintan de forma síncrona para que la captura no dependa del azar
de los fetch.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from cvfit.adaptar import adaptar
from cvfit.comparar import comparar_avisos, nombrar_avisos
from cvfit.cv import parsear
from cvfit.match import evaluar
from cvfit.pdf import navegador
from cvfit.plantillas import render
from cvfit.revisar import CONSEJOS, GUIA_ESTILOS, revisar
from cvfit.servidor import APP, Manejador, fila_json

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "docs" / "capturas"
PUERTO = 8771
AVISO = (
    "Desarrollador Fullstack SSR. Requisitos: React, Next.js, TypeScript, C#/.NET, SQL Server, "
    "tests automatizados y CI/CD. 3 anos de experiencia. Deseable: Docker y Azure."
)
OFERTAS = [
    (
        "Backend Java SSR — Remoto\n"
        "Excluyente: Java, Spring Boot y Kafka. Deseable: AWS.\n"
        "Cinco anos de experiencia, inglés B2."
    ),
    (
        "Full-Stack SSR (React + .NET) — Remoto LatAm\n"
        "Excluyente: React, TypeScript, .NET y SQL Server. Deseable: Azure y PostgreSQL.\n"
        "Trabajo con producto, equipos chicos, CI/CD propio."
    ),
    (
        "Analista QA SSR\n"
        "Excluyente: Playwright, TypeScript, CI/CD y Selenium.\n"
        "Testing automatizado de punta a punta."
    ),
]


def _json(valor) -> str:
    """JSON seguro para meter dentro de un <script>."""
    return json.dumps(valor, ensure_ascii=False).replace("</", "<\\/")


def estado_demo(aviso: str = AVISO, con_ofertas: bool = False) -> dict:
    cv_texto = (RAIZ / "ejemplos" / "cv.md").read_text(encoding="utf-8")
    cv = parsear(cv_texto)
    if con_ofertas:
        ofertas = comparar_avisos(cv, nombrar_avisos(OFERTAS))
        aviso = ofertas[0].texto
    resultado = evaluar(cv, aviso)
    adaptado = adaptar(cv, aviso)
    revision = revisar(cv, "ats")
    demo = {
        "cv": cv_texto,
        "aviso": aviso,
        "analisis": {
            "score": resultado.score,
            "veredicto": resultado.veredicto,
            "confiable": resultado.confiable,
            "total_requisitos": resultado.total_requisitos,
            "cubiertas": resultado.cubiertas,
            "faltantes": resultado.faltantes,
            "blandas_faltantes": resultado.blandas_faltantes,
            "observaciones": resultado.observaciones,
            "cambios": adaptado.cambios,
        },
        "revision": {
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
            "guia": GUIA_ESTILOS,
            "consejos": CONSEJOS,
        },
        "html": render(adaptado, "ats"),
    }
    if con_ofertas:
        demo["ofertas"] = [fila_json(oferta.nombre, oferta.resultado, oferta.texto) for oferta in ofertas]
    return demo


def pagina_demo(demo: dict, ofertas: bool = False) -> str:
    extra = ""
    if ofertas:
        extra = (
            "pintarOfertas(DEMO.ofertas);\n"
            "$('panel-revision').classList.add('oculto');\n"
            "abrirPestania('aviso');\n"
        )
    inyeccion = (
        "<script>\n"
        "const DEMO = " + _json(demo) + ";\n"
        "$('cv').value = DEMO.cv;\n"
        "$('aviso').value = DEMO.aviso;\n"
        "$('nombre-archivo').textContent = 'ejemplo.md';\n"
        "contar();\n"
        "pintar(DEMO.analisis);\n"
        "$('preview').srcdoc = DEMO.html;\n"
        "document.querySelector('.marco').classList.remove('vacio');\n"
        "marcarAcciones(true);\n"
        "pintarRevision(DEMO.revision);\n"
        "$('bloque-consejos').open = true;\n" + extra + "</script>\n"
    )
    marca = "</script>\n</body>"
    assert marca in APP, "cambió el cierre de la app"
    return APP.replace(marca, "</script>\n" + inyeccion + "</body>")


class Demo(Manejador):
    PAGINAS: dict[str, str] = {}
    REVISION: dict = {}

    def do_GET(self) -> None:
        if self.path in self.PAGINAS:
            self._html(self.PAGINAS[self.path])
        else:
            super().do_GET()

    def _revisar(self, datos: dict) -> None:
        """La captura siempre muestra la revisión del CV de ejemplo, aunque llegue un fetch vacío."""
        self._json(200, self.REVISION)


def main() -> int:
    exe = navegador()
    if exe is None:
        print("no hay navegador para las capturas", file=sys.stderr)
        return 2

    SALIDA.mkdir(parents=True, exist_ok=True)
    demo = estado_demo()
    Demo.PAGINAS = {
        "/": pagina_demo(demo),
        "/ofertas": pagina_demo(estado_demo(con_ofertas=True), ofertas=True),
    }
    Demo.REVISION = demo["revision"]
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Demo)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        for nombre, ancho, alto, ruta in (
            ("revision-1440.png", 1440, 1500, "/"),
            ("revision-900.png", 900, 1850, "/"),
            ("ofertas-1440.png", 1440, 1180, "/ofertas"),
        ):
            destino = SALIDA / nombre
            proceso = subprocess.run(
                [
                    str(exe),
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--no-first-run",
                    "--no-default-browser-check",
                    f"--user-data-dir={Path(tempfile.gettempdir()) / 'cvfit-captura'}",
                    f"--window-size={ancho},{alto}",
                    "--virtual-time-budget=3000",
                    f"--screenshot={destino}",
                    f"http://127.0.0.1:{PUERTO}{ruta}",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if not destino.exists() or destino.stat().st_size == 0:
                print(f"falló {nombre}: {(proceso.stderr or '').strip()[-200:]}", file=sys.stderr)
                return 1
            print(f"{destino.name}: {destino.stat().st_size} bytes")
    finally:
        servidor.shutdown()
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
