"""Un .docx que descomprime de más no se procesa (zip bomb)."""

import io
import zipfile

import pytest

from cvfit.extraer import ExtraccionError, desde_docx


def test_docx_gigante_se_rechaza_antes_de_descomprimir():
    bomba = io.BytesIO()
    with zipfile.ZipFile(bomba, "w", zipfile.ZIP_DEFLATED) as archivo:
        archivo.writestr("word/document.xml", b"<w:document>" + b"A" * (40 * 1024 * 1024) + b"</w:document>")

    with pytest.raises(ExtraccionError, match="límite"):
        desde_docx(bomba.getvalue())
