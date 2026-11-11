"""Endpoints del servidor, levantados de verdad en un puerto libre."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from cvfit.pdf import PdfError
from cvfit.servidor import Manejador

CV = """# Ana Prueba
**Desarrolladora Fullstack | React · .NET**

Buenos Aires | ana@ejemplo.com | +54 11 5555-5555 | linkedin.com/in/ana

## PERFIL

Desarrolladora fullstack con 5 años en producto.

## EXPERIENCIA

### Desarrolladora — Empresa | Mar 2021 – Actual
- Migré 3 servicios a contenedores y bajé el deploy de 40 a 8 minutos
- Priorizé 60 tickets y reduje 22% los incidentes en producción

## EDUCACIÓN

### Licenciatura en Informática — UNAHUR | 2018 – 2023

## STACK

| Área | Tecnologías |
|---|---|
| Backend | C#/.NET, PostgreSQL |
"""

AVISO = """Buscamos Desarrollador Fullstack SSR.
Requisitos excluyentes: React, .NET, TypeScript y SQL.
Deseable: experiencia con tests automatizados y CI/CD."""


@pytest.fixture()
def base():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_address[1]}"
    finally:
        servidor.shutdown()
        servidor.server_close()
        hilo.join(timeout=5)


def pedir(url: str, cuerpo: dict | None = None):
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(
        url,
        data=datos,
        headers={"Content-Type": "application/json"} if datos else {},
        method="POST" if datos else "GET",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return respuesta.status, respuesta.headers, respuesta.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def json_de(url: str, cuerpo: dict) -> tuple[int, dict]:
    estado, _cabeceras, datos = pedir(url, cuerpo)
    return estado, json.loads(datos)


def test_la_portada_trae_la_app(base):
    estado, cabeceras, datos = pedir(base + "/")
    assert estado == 200
    assert "text/html" in cabeceras["Content-Type"]
    assert "Revisión del CV".encode() in datos
    assert b"/api/revisar" in datos


def test_revisar_devuelve_hallazgos_y_guias(base):
    estado, datos = json_de(base + "/api/revisar", {"cv": CV, "estilo": "ats"})
    assert estado == 200
    assert datos["vacio"] is False
    assert datos["estado"] in {"ok", "medio", "mal"}
    assert {g["nombre"] for g in datos["guia"]} == {"ATS", "Clásico", "Compacto"}
    assert len(datos["consejos"]) >= 4
    assert isinstance(datos["hallazgos"], list)
    assert all({"area", "nivel", "mensaje", "como"} <= set(h) for h in datos["hallazgos"])


def test_revisar_sin_cv_no_rompe_y_sigue_mostrando_las_guias(base):
    estado, datos = json_de(base + "/api/revisar", {"cv": "   ", "estilo": "ats"})
    assert estado == 200
    assert datos["vacio"] is True
    assert datos["hallazgos"] == []
    assert len(datos["guia"]) == 3
    assert len(datos["consejos"]) >= 4


def test_revisar_no_rompe_con_un_cv_que_no_es_texto(base):
    estado, datos = json_de(base + "/api/revisar", {"cv": {"no": "texto"}, "estilo": "ats"})
    assert estado == 200
    assert datos["vacio"] is True


def test_revisar_marca_las_reescrituras(base):
    texto = CV.replace(
        "- Migré 3 servicios a contenedores y bajé el deploy de 40 a 8 minutos",
        "- Responsable del equipo de frontend",
    )
    estado, datos = json_de(base + "/api/revisar", {"cv": texto, "estilo": "ats"})
    assert estado == 200
    assert datos["reescrituras"][0]["propuesta"] == "Lideré el equipo de frontend"


def test_revisar_tiene_en_cuenta_el_estilo(base):
    con_foto = CV + "\n![foto](perfil.png)\n"
    _, ats = json_de(base + "/api/revisar", {"cv": con_foto, "estilo": "ats"})
    _, clasico = json_de(base + "/api/revisar", {"cv": con_foto, "estilo": "clasico"})
    assert any("foto" in h["mensaje"].lower() for h in ats["hallazgos"])
    assert not any("foto" in h["mensaje"].lower() for h in clasico["hallazgos"])


def test_pdf_sin_cv_ni_html_es_400(base):
    estado, _cabeceras, datos = pedir(base + "/api/pdf", {"cv": "", "html": ""})
    assert estado == 400
    assert b"no hay CV" in datos


def test_pdf_devuelve_el_archivo_con_nombre(base, monkeypatch):
    visto = {}

    def falso_a_pdf(html, destino, navegador_explicito=None):
        from pathlib import Path

        visto["html"] = html
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"%PDF-1.4\n%prueba")
        return destino

    monkeypatch.setattr("cvfit.servidor.a_pdf", falso_a_pdf)
    estado, cabeceras, datos = pedir(
        base + "/api/pdf", {"html": "<html><body>hola</body></html>", "nombre": "CV_Ana_Prueba.pdf"}
    )
    assert estado == 200
    assert cabeceras["Content-Type"] == "application/pdf"
    assert 'filename="CV_Ana_Prueba.pdf"' in cabeceras["Content-Disposition"]
    assert datos.startswith(b"%PDF-")
    assert "hola" in visto["html"]


def test_pdf_limpia_el_nombre_del_archivo(base, monkeypatch):
    def falso_a_pdf(html, destino, navegador_explicito=None):
        from pathlib import Path

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"%PDF-1.4")
        return destino

    monkeypatch.setattr("cvfit.servidor.a_pdf", falso_a_pdf)
    _, cabeceras, _ = pedir(
        base + "/api/pdf", {"html": "<html></html>", "nombre": "../../CV Ñandú.pdf"}
    )
    assert 'filename="CV_Nandu.pdf"' in cabeceras["Content-Disposition"]


def test_pdf_sin_navegador_es_503(base, monkeypatch):
    def rompe(*_args, **_kwargs):
        raise PdfError("no encontré Chrome ni Edge para imprimir a PDF")

    monkeypatch.setattr("cvfit.servidor.a_pdf", rompe)
    estado, _cabeceras, datos = pedir(base + "/api/pdf", {"html": "<html></html>"})
    assert estado == 503
    assert b"Chrome ni Edge" in datos


def test_separar_avisos_corta_por_lineas_de_guiones():
    from cvfit.servidor import separar_avisos

    partes = separar_avisos("Uno\nExcluyente: React\n---\nDos\n  ---  \n\n---\nTres")
    assert partes == ["Uno\nExcluyente: React", "Dos", "Tres"]
    assert separar_avisos(["uno", 3, "   "]) == ["uno"]
    assert separar_avisos("") == []
    assert separar_avisos(42) == []


def test_comparar_avisos_ordena_por_encaje(base):
    avisos = AVISO + "\n---\nBuscamos Backend Java.\nExcluyente: Java, Spring y Kafka.\n"
    estado, datos = json_de(base + "/api/comparar-avisos", {"cv": CV, "avisos": avisos})
    assert estado == 200
    assert len(datos["filas"]) == 2
    assert datos["filas"][0]["score"] >= datos["filas"][1]["score"]
    assert datos["filas"][0]["nombre"].startswith("Buscamos Desarrollador")
    assert datos["filas"][0]["texto"].startswith("Buscamos Desarrollador")
    assert all({"nombre", "score", "veredicto", "texto", "faltantes"} <= set(fila) for fila in datos["filas"])


def test_comparar_avisos_tambien_acepta_una_lista(base):
    avisos = [AVISO, "Buscamos Data Engineer.\nExcluyente: Python, Spark y Airflow."]
    estado, datos = json_de(base + "/api/comparar-avisos", {"cv": CV, "avisos": avisos})
    assert estado == 200
    assert len(datos["filas"]) == 2


def test_comparar_avisos_pide_al_menos_dos(base):
    estado, datos = json_de(base + "/api/comparar-avisos", {"cv": CV, "avisos": AVISO})
    assert estado == 400
    assert "dos avisos" in datos["error"]


def test_comparar_avisos_sin_cv_es_400(base):
    estado, datos = json_de(base + "/api/comparar-avisos", {"cv": "", "avisos": AVISO + "\n---\n" + AVISO})
    assert estado == 400
    assert "falta el CV" in datos["error"]


def test_analizar_sigue_funcionando(base):
    estado, datos = json_de(base + "/api/analizar", {"cv": CV, "aviso": AVISO})
    assert estado == 200
    assert 0 <= datos["score"] <= 100
    assert datos["veredicto"] in {"alta", "media", "baja"}
    assert isinstance(datos["faltantes"], list)


def test_ruta_desconocida_es_404(base):
    estado, _cabeceras, _datos = pedir(base + "/api/no-existe", {"cv": CV})
    assert estado == 404
