"""De HTML a PDF usando el Chrome o el Edge que ya está instalado.

Sin dependencias: se llama al navegador en modo headless con `--print-to-pdf`. Si no hay ninguno,
el programa lo dice y sigue: el HTML se puede imprimir a mano desde el navegador.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

TIEMPO_MAXIMO = 90


class PdfError(RuntimeError):
    """No se pudo generar el PDF (no hay navegador, falló o no escribió nada)."""


RUTAS_CONOCIDAS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\{usuario}\AppData\Local\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

ORDEN_BUSQUEDA = ("chrome", "google-chrome", "chromium", "msedge", "microsoft-edge")


def navegador() -> Path | None:
    """Primer navegador capaz de imprimir a PDF. `CVFIT_NAVEGADOR` tiene prioridad."""
    propio = os.environ.get("CVFIT_NAVEGADOR")
    if propio:
        ruta = Path(propio)
        if ruta.exists():
            return ruta
    usuario = Path.home()
    for plantilla in RUTAS_CONOCIDAS:
        ruta = Path(plantilla.format(usuario=usuario))
        if ruta.exists():
            return ruta
    for nombre in ORDEN_BUSQUEDA:
        encontrado = shutil.which(nombre)
        if encontrado:
            return Path(encontrado)
    return None


def _banderas(salida: Path, perfil: Path) -> list[str]:
    return [
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--user-data-dir={perfil}",
        f"--print-to-pdf={salida}",
    ]


def a_pdf(html: str, destino, navegador_explicito: Path | None = None) -> Path:
    """Escribe `html` en `destino` como PDF. Levanta `PdfError` con un motivo legible."""
    exe = navegador_explicito or navegador()
    if exe is None:
        raise PdfError("no encontré Chrome ni Edge para imprimir a PDF")

    destino = Path(destino)
    if destino.suffix.lower() != ".pdf":
        destino = destino.with_suffix(".pdf")
    destino.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cvfit-pdf-") as temporal:
        carpeta = Path(temporal)
        fuente = carpeta / "cv.html"
        fuente.write_text(html, encoding="utf-8")
        try:
            proceso = subprocess.run(
                [str(exe), *_banderas(destino, carpeta / "perfil"), fuente.as_uri()],
                capture_output=True,
                text=True,
                timeout=TIEMPO_MAXIMO,
            )
        except subprocess.TimeoutExpired as error:
            raise PdfError(f"el navegador tardó más de {TIEMPO_MAXIMO}s en imprimir") from error
        except OSError as error:
            raise PdfError(f"no pude ejecutar el navegador: {error}") from error

        if not destino.exists() or destino.stat().st_size == 0:
            detalle = (proceso.stderr or proceso.stdout or "").strip().splitlines()
            motivo = detalle[-1][:200] if detalle else "sin salida del navegador"
            raise PdfError(f"el navegador no generó el PDF ({motivo})")
        with destino.open("rb") as archivo:
            if archivo.read(5) != b"%PDF-":
                raise PdfError("lo que salió del navegador no es un PDF")
    return destino
