"""Comparar varios CVs contra el mismo aviso: el ranking y el desempate."""

from __future__ import annotations

import pytest

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


# --- el ranking inverso: un CV contra varios avisos ---


def _aviso(titulo: str, *tecnologias: str) -> str:
    pedido = ", ".join(tecnologias) or "Excel"
    return f"{titulo}\nExcluyente: {pedido}. Remoto, Argentina."


def test_ordena_los_avisos_del_que_mejor_encaja_al_que_peor():
    from cvfit.comparar import comparar_avisos, nombrar_avisos

    ofertas = comparar_avisos(
        _cv("React", "TypeScript", ".NET"),
        nombrar_avisos(
            [
                _aviso("Dev React SSR", "React", "TypeScript", ".NET"),
                _aviso("Dev Java SSR", "Java", "Spring", "Kafka"),
                _aviso("Dev React junior", "React"),
            ]
        ),
    )
    assert [oferta.nombre for oferta in ofertas] == ["Dev React SSR", "Dev React junior", "Dev Java SSR"]
    assert ofertas[0].resultado.faltantes == []
    assert sorted(ofertas[-1].resultado.faltantes) == ["Java", "Kafka", "Spring"]


def test_el_nombre_del_aviso_sale_de_la_primera_linea_con_contenido():
    from cvfit.comparar import nombre_de_aviso

    assert nombre_de_aviso("\n\n# Dev Backend\nC# y SQL") == "Dev Backend"
    assert nombre_de_aviso("   ") == "Aviso 1"
    assert nombre_de_aviso("\n\n", 3) == "Aviso 3"
    largo = nombre_de_aviso("x" * 120)
    assert largo.endswith("…") and len(largo) == 61


def test_dos_avisos_que_empiezan_igual_no_se_pisan():
    from cvfit.comparar import nombrar_avisos

    nombrados = nombrar_avisos(["Dev React", "Dev React", "Dev React"])
    assert list(nombrados) == ["Dev React", "Dev React (2)", "Dev React (3)"]
    assert len(nombrados) == 3


def test_comparar_avisos_acepta_el_cv_como_texto_o_ya_parseado():
    from cvfit.comparar import comparar_avisos, nombrar_avisos
    from cvfit.cv import parsear

    textos = nombrar_avisos([_aviso("A", "React"), _aviso("B", "Java")])
    desde_texto = comparar_avisos(_cv("React"), textos)
    desde_cv = comparar_avisos(parsear(_cv("React")), textos)
    assert [oferta.nombre for oferta in desde_texto] == [oferta.nombre for oferta in desde_cv]
    assert desde_texto[0].nombre == "A"


def test_el_aviso_que_pide_menos_requisitos_queda_orientativo():
    from cvfit.comparar import comparar_avisos, nombrar_avisos

    ofertas = comparar_avisos(_cv("React"), nombrar_avisos(["Buscamos gente con React.", _aviso("Full", "React")]))
    assert ofertas[0].resultado.confiable is False
    assert ofertas[0].resultado.score == 100


def test_cli_compara_un_cv_contra_varios_avisos(tmp_path, capsys):
    from cvfit.analizar import main

    cv = tmp_path / "cv.md"
    cv.write_text(_cv("React", "TypeScript", ".NET"), encoding="utf-8")
    elegido = tmp_path / "elegido.txt"
    elegido.write_text(_aviso("Dev React SSR", "React", "TypeScript"), encoding="utf-8")
    descartado = tmp_path / "descartado.txt"
    descartado.write_text(_aviso("Dev Java SSR", "Java", "Kafka"), encoding="utf-8")
    salida = tmp_path / "cv.html"

    codigo = main(["--cv", str(cv), "--avisos", str(descartado), str(elegido), "--salida", str(salida)])

    assert codigo == 0
    impreso = capsys.readouterr().out
    assert "cv.md contra 2 avisos" in impreso
    assert "conviene: Dev React SSR" in impreso
    assert "respaldados (2/2): React, TypeScript" in impreso


def test_cli_no_mezcla_varios_cvs_con_varios_avisos(tmp_path, capsys):
    from cvfit.analizar import main

    uno = tmp_path / "uno.md"
    uno.write_text(_cv("React"), encoding="utf-8")
    dos = tmp_path / "dos.md"
    dos.write_text(_cv("Java"), encoding="utf-8")
    aviso = tmp_path / "aviso.txt"
    aviso.write_text(_aviso("Dev", "React"), encoding="utf-8")

    assert main(["--cv", str(uno), str(dos), "--avisos", str(aviso)]) == 2
    assert "un solo CV" in capsys.readouterr().err


def test_cli_aviso_y_avisos_son_excluyentes(tmp_path):
    from cvfit.analizar import main

    cv = tmp_path / "cv.md"
    cv.write_text(_cv("React"), encoding="utf-8")
    aviso = tmp_path / "aviso.txt"
    aviso.write_text(_aviso("Dev", "React"), encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["--cv", str(cv), "--aviso", str(aviso), "--avisos", str(aviso)])


def test_separar_avisos_acepta_crlf_y_espacios_alrededor():
    from cvfit.comparar import separar_avisos

    assert separar_avisos("Uno\r\n---\r\nDos") == ["Uno", "Dos"]
    assert separar_avisos("Uno\n\t---  \nDos") == ["Uno", "Dos"]
    assert separar_avisos("Uno\n---") == ["Uno"]


def test_cli_parte_un_archivo_con_varios_avisos(tmp_path, capsys):
    from cvfit.analizar import main

    cv = tmp_path / "cv.md"
    cv.write_text(_cv("React", "TypeScript"), encoding="utf-8")
    avisos = tmp_path / "avisos.txt"
    avisos.write_text(
        _aviso("Dev React SSR", "React", "TypeScript") + "\r\n---\r\n" + _aviso("Dev Java SSR", "Java", "Kafka"),
        encoding="utf-8",
    )
    salida = tmp_path / "cv.html"

    codigo = main(["--cv", str(cv), "--avisos", str(avisos), "--salida", str(salida)])

    assert codigo == 0
    impreso = capsys.readouterr().out
    assert "cv.md contra 2 avisos" in impreso
    assert "conviene: Dev React SSR" in impreso


def test_conviene_avisa_cuando_el_primero_es_orientativo(tmp_path, capsys):
    from cvfit.analizar import main

    cv = tmp_path / "cv.md"
    cv.write_text(_cv("React"), encoding="utf-8")
    aviso = tmp_path / "aviso.txt"
    aviso.write_text(_aviso("Dev React corto", "React"), encoding="utf-8")

    assert main(["--cv", str(cv), "--avisos", str(aviso), "--salida", str(tmp_path / "cv.html")]) == 0
    assert "conviene: Dev React corto (orientativo)" in capsys.readouterr().out
