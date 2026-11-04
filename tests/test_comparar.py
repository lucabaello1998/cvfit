"""Comparar varios CVs contra el mismo aviso: el ranking y el desempate."""

from __future__ import annotations

from cvfit.comparar import comparar, comparar_textos

AVISO = """
Buscamos Desarrollador Full Stack SSR.

Excluyente: React, TypeScript, .NET y SQL Server.
Deseable: Docker, Azure, Next.js.

Remoto, Argentina. Ingles B2.
"""


def _cv(*tecnologias: str) -> str:
    stack = ", ".join(tecnologias) or "Word"
    return f"""# Ana Pérez
Desarrolladora Full Stack

## EXPERIENCIA
- Trabajé con {stack} en sistemas productivos.
"""


def test_ordena_del_mejor_al_peor_encaje():
    filas = comparar_textos(
        {
            "completo.md": _cv("React", "TypeScript", ".NET", "SQL Server", "Azure", "Docker", "Next.js"),
            "medio.md": _cv("React", "TypeScript"),
            "flojo.md": _cv("Excel"),
        },
        AVISO,
    )
    assert [fila.nombre for fila in filas] == ["completo.md", "medio.md", "flojo.md"]
    assert filas[0].resultado.score >= filas[1].resultado.score >= filas[2].resultado.score


def test_el_primero_es_el_que_cubre_los_excluyentes():
    filas = comparar_textos(
        {
            "con_excluyentes.md": _cv("React", "TypeScript", ".NET", "SQL Server"),
            "con_deseables.md": _cv("React", "TypeScript", "Docker", "Azure", "Next.js"),
        },
        AVISO,
    )
    # mismos 100 puntos posibles, pero el primero no deja gaps excluyentes
    assert filas[0].nombre == "con_excluyentes.md"
    assert filas[0].resultado.faltantes == []


def test_un_cv_ilegible_no_rompe_la_comparacion(tmp_path):
    desde_archivo = {"vacio.md": ""}
    filas = comparar_textos({**desde_archivo, "real.md": _cv("React", "TypeScript", ".NET")}, AVISO)
    assert filas[0].nombre == "real.md"
    assert filas[-1].nombre == "vacio.md"


def test_comparar_acepta_cvs_ya_parseados():
    from cvfit.cv import parsear

    filas = comparar(
        {"a.md": parsear(_cv("React")), "b.md": parsear(_cv("React", "TypeScript", ".NET", "SQL Server"))},
        AVISO,
    )
    assert filas[0].nombre == "b.md"


def test_dos_cvs_iguales_se_ordenan_por_nombre_y_no_se_pisan():
    filas = comparar_textos({"zeta.md": _cv("React", "TypeScript"), "alfa.md": _cv("React", "TypeScript")}, AVISO)
    assert [fila.nombre for fila in filas] == ["alfa.md", "zeta.md"]


def test_cli_compara_varios_y_escribe_el_ganador(tmp_path, capsys):
    from cvfit.analizar import main

    completo = tmp_path / "completo.md"
    completo.write_text(_cv("React", "TypeScript", ".NET", "SQL Server"), encoding="utf-8")
    flojo = tmp_path / "flojo.md"
    flojo.write_text(_cv("Excel"), encoding="utf-8")
    aviso = tmp_path / "aviso.txt"
    aviso.write_text(AVISO, encoding="utf-8")
    salida = tmp_path / "cv.html"

    codigo = main(["--cv", str(completo), str(flojo), "--aviso", str(aviso), "--salida", str(salida)])

    assert codigo == 0
    impreso = capsys.readouterr().out
    assert "comparando 2 CVs" in impreso
    assert "gana: completo.md" in impreso
    assert "Ana Pérez" in salida.read_text(encoding="utf-8")


def test_cli_saltea_un_archivo_ilegible_y_sigue(tmp_path, capsys):
    from cvfit.analizar import main

    bueno = tmp_path / "bueno.md"
    bueno.write_text(_cv("React", "TypeScript", ".NET"), encoding="utf-8")
    roto = tmp_path / "roto.docx"  # no es un zip: ExtraccionError
    roto.write_bytes(b"no soy un docx")
    aviso = tmp_path / "aviso.txt"
    aviso.write_text(AVISO, encoding="utf-8")

    assert main(["--cv", str(roto), str(bueno), "--aviso", str(aviso)]) == 0
    assert "salteado roto.docx" in capsys.readouterr().err


def test_cli_falla_si_no_puede_leer_ninguno(tmp_path, capsys):
    from cvfit.analizar import main

    roto = tmp_path / "roto.docx"
    roto.write_bytes(b"no soy un docx")
    aviso = tmp_path / "aviso.txt"
    aviso.write_text(AVISO, encoding="utf-8")

    assert main(["--cv", str(roto), "--aviso", str(aviso)]) == 2
    assert "no pude leer ninguno" in capsys.readouterr().err
