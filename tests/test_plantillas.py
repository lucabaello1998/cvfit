"""Foto, color y tamaño: lo que se pide se aplica, lo que no es válido se descarta."""

from __future__ import annotations

import base64

from cvfit.adaptar import adaptar
from cvfit.cv import parsear
from cvfit.plantillas import foto_desde_archivo, render

CV = """# Ana Pérez
Desarrolladora Full Stack

ana@ejemplo.com

## EXPERIENCIA
- Algo con React y TypeScript
"""

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
FOTO = "data:image/png;base64," + base64.b64encode(PNG).decode()


def _html(**opciones) -> str:
    return render(adaptar(parsear(CV), "React, TypeScript"), "clasico", **opciones)


def test_sin_foto_no_hay_imagen():
    assert "<img" not in _html()


def test_la_foto_entra_como_imagen_incrustada():
    html = _html(foto=FOTO)
    assert f'<img class="foto" src="{FOTO}"' in html


def test_foto_que_no_es_imagen_se_descarta():
    for trucha in (
        "javascript:alert(1)",
        "data:image/svg+xml;base64,PHN2Zy8+",
        "https://ejemplo.com/foto.png",
        "<img src=x onerror=alert(1)>",
    ):
        assert "<img" not in _html(foto=trucha)


def test_foto_enorme_se_descarta():
    assert "<img" not in _html(foto="data:image/png;base64," + "A" * 3_000_001)


def test_el_color_de_acento_se_aplica_en_el_css():
    assert ":root{--acento:#0f766e}" in _html(acento="#0f766e")


def test_un_color_invalido_se_ignora():
    for trucho in ("red", "#12345", "#fff", "#000; } body{display:none}", "rgb(1,2,3)"):
        assert _html(acento=trucho) == _html()


def test_la_escala_cambia_el_tamanio_de_letra():
    assert ":root{--escala:1.1}" in _html(escala=1.1)
    assert _html(escala=1) == _html()


def test_la_escala_se_recorta_a_un_rango_usable():
    assert ":root{--escala:1.3}" in _html(escala=5)
    assert ":root{--escala:0.85}" in _html(escala=0.1)


def test_escala_basura_no_rompe_el_render():
    assert _html(escala="mucho") == _html()


def test_foto_desde_archivo_arma_el_data_uri(tmp_path):
    archivo = tmp_path / "foto.png"
    archivo.write_bytes(PNG)
    assert foto_desde_archivo(archivo).startswith("data:image/png;base64,")


def test_foto_desde_archivo_rechaza_formatos_raros(tmp_path):
    archivo = tmp_path / "foto.svg"
    archivo.write_text("<svg/>", encoding="utf-8")
    try:
        foto_desde_archivo(archivo)
    except ValueError as error:
        assert "no soportado" in str(error)
    else:  # pragma: no cover
        raise AssertionError("debía rechazar el svg")


def _archivos(tmp_path):
    cv = tmp_path / "cv.md"
    cv.write_text(CV, encoding="utf-8")
    aviso = tmp_path / "aviso.txt"
    aviso.write_text("React y TypeScript", encoding="utf-8")
    foto = tmp_path / "foto.png"
    foto.write_bytes(PNG)
    return cv, aviso, foto


def test_cli_aplica_foto_color_y_escala(tmp_path):
    from cvfit.analizar import main

    cv, aviso, foto = _archivos(tmp_path)
    salida = tmp_path / "cv.html"

    codigo = main(
        [
            "--cv",
            str(cv),
            "--aviso",
            str(aviso),
            "--foto",
            str(foto),
            "--acento",
            "#0f766e",
            "--escala",
            "1.1",
            "--salida",
            str(salida),
        ]
    )

    assert codigo == 0
    html = salida.read_text(encoding="utf-8")
    assert '<img class="foto" src="data:image/png;base64,' in html
    assert ":root{--acento:#0f766e}" in html
    assert ":root{--escala:1.1}" in html


def test_cli_avisa_si_la_foto_no_sirve(tmp_path, capsys):
    from cvfit.analizar import main

    cv, aviso, _ = _archivos(tmp_path)
    rara = tmp_path / "foto.svg"
    rara.write_text("<svg/>", encoding="utf-8")

    assert main(["--cv", str(cv), "--aviso", str(aviso), "--foto", str(rara)]) == 2
    assert "no soportado" in capsys.readouterr().err
