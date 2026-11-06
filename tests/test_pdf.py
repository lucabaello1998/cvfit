"""HTML a PDF con el navegador instalado: sin dependencias y con caída limpia si no hay."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cvfit import pdf
from cvfit.pdf import PdfError, a_pdf, navegador

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@page{size:A4;margin:0}body{margin:0;font-family:sans-serif}
</style></head><body><h1>Ana Prueba</h1><p>ana@ejemplo.com</p></body></html>"""


def test_sin_navegador_levanta_error_claro(monkeypatch):
    monkeypatch.setattr(pdf, "navegador", lambda: None)
    with pytest.raises(PdfError, match="Chrome ni Edge"):
        a_pdf(HTML, "salida.pdf")


def test_cvfit_navegador_tiene_prioridad(tmp_path, monkeypatch):
    falso = tmp_path / "chrome.exe"
    falso.write_bytes(b"")
    monkeypatch.setenv("CVFIT_NAVEGADOR", str(falso))
    assert navegador() == falso
    monkeypatch.setenv("CVFIT_NAVEGADOR", str(tmp_path / "no-existe.exe"))
    # Si la ruta forzada no existe, se ignora y se sigue buscando por las conocidas.
    assert navegador() != tmp_path / "no-existe.exe"


def test_arma_el_comando_con_las_banderas_de_impresion(tmp_path, monkeypatch):
    exe = tmp_path / "chrome.exe"
    exe.write_bytes(b"")
    destino = tmp_path / "cv.pdf"
    visto: dict[str, object] = {}

    def falso_run(comando, **kwargs):
        visto["comando"] = comando
        visto["kwargs"] = kwargs
        # El navegador real escribe el PDF en la ruta de --print-to-pdf.
        bandera = next(c for c in comando if str(c).startswith("--print-to-pdf="))
        Path(bandera.split("=", 1)[1]).write_bytes(b"%PDF-1.4\n%falso")
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(subprocess, "run", falso_run)
    ruta = a_pdf(HTML, destino, navegador_explicito=exe)

    comando = [str(c) for c in visto["comando"]]
    assert comando[0] == str(exe)
    assert "--headless=new" in comando
    assert "--no-pdf-header-footer" in comando
    assert any(c.startswith("--user-data-dir=") for c in comando)
    assert comando[-1].startswith("file://")
    assert ruta == destino
    assert ruta.read_bytes().startswith(b"%PDF-")
    assert visto["kwargs"]["timeout"] == pdf.TIEMPO_MAXIMO


def test_agrega_la_extension_si_falta(tmp_path, monkeypatch):
    exe = tmp_path / "chrome.exe"
    exe.write_bytes(b"")

    def falso_run(comando, **kwargs):
        bandera = next(c for c in comando if str(c).startswith("--print-to-pdf="))
        Path(bandera.split("=", 1)[1]).write_bytes(b"%PDF-1.4\n")
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(subprocess, "run", falso_run)
    assert a_pdf(HTML, tmp_path / "cv", navegador_explicito=exe).suffix == ".pdf"


def test_si_el_navegador_no_escribe_nada_avisa(tmp_path, monkeypatch):
    exe = tmp_path / "chrome.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(
        subprocess, "run", lambda comando, **kw: subprocess.CompletedProcess(comando, 1, "", "boom")
    )
    with pytest.raises(PdfError, match="no generó el PDF"):
        a_pdf(HTML, tmp_path / "cv.pdf", navegador_explicito=exe)


def test_si_lo_escrito_no_es_pdf_avisa(tmp_path, monkeypatch):
    exe = tmp_path / "chrome.exe"
    exe.write_bytes(b"")

    def falso_run(comando, **kwargs):
        bandera = next(c for c in comando if str(c).startswith("--print-to-pdf="))
        Path(bandera.split("=", 1)[1]).write_text("<html>error</html>", encoding="utf-8")
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(subprocess, "run", falso_run)
    with pytest.raises(PdfError, match="no es un PDF"):
        a_pdf(HTML, tmp_path / "cv.pdf", navegador_explicito=exe)


def test_timeout_se_informa_como_pdf_error(tmp_path, monkeypatch):
    exe = tmp_path / "chrome.exe"
    exe.write_bytes(b"")

    def lento(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("chrome", pdf.TIEMPO_MAXIMO)

    monkeypatch.setattr(subprocess, "run", lento)
    with pytest.raises(PdfError, match="tardó"):
        a_pdf(HTML, tmp_path / "cv.pdf", navegador_explicito=exe)


@pytest.mark.skipif(navegador() is None, reason="no hay Chrome ni Edge instalado")
def test_genera_un_pdf_de_verdad(tmp_path):
    ruta = a_pdf(HTML, tmp_path / "real.pdf")
    datos = ruta.read_bytes()
    assert datos.startswith(b"%PDF-")
    assert len(datos) > 1000
