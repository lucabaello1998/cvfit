"""Extracción de archivos: DOCX y PDF armados a mano, sin dependencias ni fixtures binarios."""

from __future__ import annotations

import io
import zipfile
import zlib

import pytest

from cvfit.extraer import ExtraccionError, desde_docx, desde_pdf, estructurar, extraer_desde_archivo

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(parrafos: list[tuple[str, str]]) -> bytes:
    """Arma un .docx mínimo: (estilo, texto) por párrafo."""
    from xml.sax.saxutils import escape

    cuerpo = []
    for estilo, texto in parrafos:
        ppr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>' if estilo else ""
        cuerpo.append(f"<w:p>{ppr}<w:r><w:t>{escape(texto)}</w:t></w:r></w:p>")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{W}"><w:body>{"".join(cuerpo)}</w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archivo:
        archivo.writestr("word/document.xml", xml)
    return buffer.getvalue()


def _pdf(lineas: list[str]) -> bytes:
    """PDF con un único stream FlateDecode y operadores de texto reales."""
    operadores = b"BT /F1 11 Tf 40 750 Td "
    for linea in lineas:
        operadores += b"(" + linea.encode("cp1252") + b") Tj T* "
    operadores += b"ET"
    comprimido = zlib.compress(operadores)
    return (
        b"%PDF-1.4\n1 0 obj\n<< /Length "
        + str(len(comprimido)).encode()
        + b" /Filter /FlateDecode >>\nstream\n"
        + comprimido
        + b"\nendstream\nendobj\ntrailer\n<<>>\n%%EOF\n"
    )


def test_docx_respeta_estilos_y_vinetas():
    datos = _docx(
        [
            ("Heading1", "Luca Baello"),
            ("Heading2", "experiencia"),
            ("Heading3", "Grupo CETA | 2024 - 2026"),
            ("", "Desarrollo fullstack en React y .NET."),
        ]
    )
    texto = desde_docx(datos)
    assert texto.startswith("# Luca Baello")
    assert "## EXPERIENCIA" in texto
    assert "### Grupo CETA" in texto
    assert "React y .NET" in texto


def test_docx_con_vinetas_las_convierte_en_bullets():
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{W}"><w:body>'
        "<w:p><w:pPr><w:numPr/></w:pPr><w:r><w:t>Primer logro</w:t></w:r></w:p>"
        "<w:p><w:pPr><w:numPr/></w:pPr><w:r><w:t>Segundo logro</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archivo:
        archivo.writestr("word/document.xml", xml)
    texto = desde_docx(buffer.getvalue())
    assert [linea for linea in texto.splitlines() if linea] == ["- Primer logro", "- Segundo logro"]


def test_docx_que_no_es_zip_falla_limpio():
    with pytest.raises(ExtraccionError, match="docx"):
        desde_docx(b"esto no es un docx")


def test_docx_sin_texto_falla_limpio():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archivo:
        archivo.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body/></w:document>')
    with pytest.raises(ExtraccionError, match="texto"):
        desde_docx(buffer.getvalue())


def test_pdf_extrae_las_lineas_de_texto():
    texto = desde_pdf(
        _pdf(
            [
                "Luca Nicolas Baello",
                "Desarrollador Fullstack SSR",
                "Buenos Aires, Argentina",
                "Experiencia con React, Next.js, C# y .NET.",
                "Responsable de features end-to-end en produccion.",
            ]
        )
    )
    assert "Luca Nicolas Baello" in texto
    assert "React" in texto
    assert ".NET" in texto


def test_pdf_sin_texto_explica_que_es_un_escaneo():
    with pytest.raises(ExtraccionError, match="escaneada"):
        desde_pdf(b"%PDF-1.4\nno hay streams\n%%EOF")


def test_pdf_cifrado_se_rechaza():
    with pytest.raises(ExtraccionError, match="contrase"):
        desde_pdf(b"%PDF-1.4\n/Encrypt 5 0 R\n%%EOF")


def test_estructurar_promueve_titulos_conocidos_y_vinetas():
    crudo = "\n".join(
        [
            "Luca Nicolas Baello",
            "Desarrollador Fullstack SSR",
            "EXPERIENCIA",
            "• APIs en .NET 8 con SQL Server",
            "• Front en React y Next.js",
            "EDUCACION",
            "Tecnicatura en Programacion",
        ]
    )
    markdown = estructurar(crudo)
    assert markdown.startswith("# Luca Nicolas Baello")
    assert "## EXPERIENCIA" in markdown
    assert "## EDUCACION" in markdown
    assert "- APIs en .NET 8 con SQL Server" in markdown


def test_estructurar_no_inventa_secciones():
    markdown = estructurar("Luca Baello\nUna linea cualquiera\nOtra linea")
    assert "##" not in markdown


def test_estructurar_no_confunde_una_oracion_con_una_seccion():
    markdown = estructurar("Luca Baello\nExperiencia con React y .NET en producción.")
    assert "##" not in markdown
    assert "Experiencia con React y .NET en producción." in markdown


def test_estructurar_descarta_pies_de_pagina_y_elige_el_nombre():
    crudo = "\n".join(["CV recruiter - Luca Baello", "Pagina 1", "Luca Nicolas Baello", "EXPERIENCIA"])
    markdown = estructurar(crudo)
    assert markdown.splitlines()[1] == "# Luca Nicolas Baello"
    assert "Pagina 1" not in markdown


def test_extraer_desde_archivo_md_y_txt(tmp_path):
    archivo = tmp_path / "cv.md"
    archivo.write_text("# Nombre\n\n## EXPERIENCIA\n", encoding="utf-8")
    assert extraer_desde_archivo(archivo).startswith("# Nombre")


def test_extraer_desde_archivo_rechaza_formato_desconocido(tmp_path):
    archivo = tmp_path / "cv.rtf"
    archivo.write_text("{\\rtf1}", encoding="utf-8")
    with pytest.raises(ExtraccionError, match="no soportado"):
        extraer_desde_archivo(archivo)
