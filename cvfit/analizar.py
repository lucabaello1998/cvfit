"""CLI: analizar un CV contra un aviso y escribir el CV adaptado.

Tres modos: un CV contra un aviso, varios CV contra el mismo aviso, y un CV contra varios avisos.
"""

from __future__ import annotations

import argparse
import sys
from contextlib import suppress
from pathlib import Path

from . import __version__
from .adaptar import adaptar
from .comparar import comparar, comparar_avisos, nombrar_avisos, separar_avisos
from .cv import cargar, parsear
from .extraer import ExtraccionError, estructurar, extraer_desde_archivo
from .pdf import PdfError, a_pdf
from .plantillas import NOMBRES, foto_desde_archivo, render
from .revisar import revisar

VEREDICTOS = {
    "alta": "Encaje alto: podés respaldar casi todo lo que pide el aviso.",
    "media": "Encaje medio: llegás a la entrevista si tapás los gaps marcados.",
    "baja": "Encaje bajo: el aviso pide cosas que hoy no podés respaldar.",
}

ESTADOS = {
    "ok": "sin nada grave",
    "medio": "hay cosas para pulir",
    "mal": "hay cosas que pueden descartarte",
}


def _revision_texto(revision) -> str:
    """La revisión en consola: mismo motor que la interfaz, sin adornos."""
    lineas = [f"\nrevisión del CV — {ESTADOS[revision.estado]}"]
    marcas = {"alto": "!!", "medio": " !", "bajo": " ·"}
    for hallazgo in revision.hallazgos:
        lineas.append(f"  {marcas[hallazgo.nivel]} [{hallazgo.area}] {hallazgo.mensaje}")
        lineas.append(f"       {hallazgo.como}")
    if revision.reescrituras:
        lineas.append("\n  reescrituras sugeridas:")
        for reescritura in revision.reescrituras:
            lineas.append(f"    - {reescritura.original}")
            lineas.append(f"      {reescritura.propuesta}")
    if revision.bien:
        lineas.append("\n  ya está bien:")
        for texto in revision.bien:
            lineas.append(f"    · {texto}")
    return "\n".join(lineas)


def leer_cv(ruta):
    """Acepta .md/.txt/.docx/.pdf. Un PDF se estructura a Markdown antes de parsear."""
    if ruta.suffix.lower() == ".pdf":
        return parsear(estructurar(extraer_desde_archivo(ruta)))
    if ruta.suffix.lower() == ".docx":
        return parsear(extraer_desde_archivo(ruta))
    return cargar(ruta)


def _tabla(filas, etiqueta: str = "CV") -> str:
    """Ranking en texto: sin dependencias, alineado a ojo."""
    ancho_nombre = max(len(fila.nombre) for fila in filas) + 2
    encabezado = f"{'#':>2}  {etiqueta:<{ancho_nombre}}{'encaje':>7}  {'respaldados':>11}  gaps excluyentes"
    lineas = [encabezado, "-" * len(encabezado)]
    for posicion, fila in enumerate(filas, start=1):
        resultado = fila.resultado
        respaldados = f"{len(resultado.cubiertas)}/{resultado.total_requisitos}"
        gaps = ", ".join(resultado.faltantes) or "—"
        marca = " (orientativo)" if not resultado.confiable else ""
        lineas.append(
            f"{posicion:>2}  {fila.nombre:<{ancho_nombre}}{str(resultado.score) + '%':>7}  {respaldados:>11}  {gaps}{marca}"
        )
    return "\n".join(lineas)


def _resumen(resultado, adaptado) -> None:
    """El bloque de siempre: encaje, respaldados, gaps y cambios."""
    print(f"\n{resultado.score}% — {VEREDICTOS[resultado.veredicto]}")
    if not resultado.confiable:
        print("(orientativo: el aviso tiene pocos requisitos reconocibles)")
    print(
        f"\nrespaldados ({len(resultado.cubiertas)}/{resultado.total_requisitos}): {', '.join(resultado.cubiertas) or '—'}"
    )
    if resultado.faltantes:
        print(f"excluyentes que faltan: {', '.join(resultado.faltantes)}")
    if resultado.blandas_faltantes:
        print(f"deseables que faltan:   {', '.join(resultado.blandas_faltantes)}")
    if resultado.observaciones:
        print("\nantes de postularte:")
        for observacion in resultado.observaciones:
            print(f"  · {observacion}")
    if adaptado.cambios:
        print("\ndistinto en el CV:")
        for cambio in adaptado.cambios:
            print(f"  · {cambio}")


def _consola_tolerante() -> None:
    """Una consola Windows en cp1252 revienta con «↔» o «—»: que reemplace en vez de romper."""
    for flujo in (sys.stdout, sys.stderr):
        with suppress(AttributeError, ValueError):
            flujo.reconfigure(errors="replace")


def main(argv: list[str] | None = None) -> int:
    _consola_tolerante()
    parser = argparse.ArgumentParser(prog="cvfit", description="Encaje CV ↔ aviso y CV adaptado")
    parser.add_argument(
        "--cv",
        required=True,
        type=Path,
        nargs="+",
        help="uno o varios CV (.md, .txt, .docx o .pdf); con varios se comparan contra el mismo aviso",
    )
    avisos = parser.add_mutually_exclusive_group(required=True)
    avisos.add_argument("--aviso", type=Path, help="texto del aviso")
    avisos.add_argument(
        "--avisos",
        type=Path,
        nargs="+",
        help="varios avisos: con un solo CV, dice a cuál conviene postular primero",
    )
    parser.add_argument("--estilo", default="ats", choices=sorted(NOMBRES))
    parser.add_argument("--foto", type=Path, help="foto de perfil (.png, .jpg o .webp) para el encabezado")
    parser.add_argument("--acento", help="color de acento en hex, por ejemplo #1f5f8b")
    parser.add_argument("--escala", type=float, help="tamaño de letra: 0.9 a 1.3 (1 = normal)")
    parser.add_argument("--salida", type=Path, help="archivo HTML o PDF de salida")
    parser.add_argument("--version", action="version", version=f"cvfit {__version__}")
    args = parser.parse_args(argv)

    foto = ""
    if args.foto:
        try:
            foto = foto_desde_archivo(args.foto)
        except (OSError, ValueError) as error:
            print(f"foto: {error}", file=sys.stderr)
            return 2

    cvs = {}
    for ruta in args.cv:
        try:
            cvs[ruta.name] = leer_cv(ruta)
        except ExtraccionError as error:
            print(f"salteado {ruta.name}: {error}", file=sys.stderr)

    if not cvs:
        print("no pude leer ninguno de los CV", file=sys.stderr)
        return 2

    if args.avisos:
        if len(cvs) > 1:
            print("con --avisos va un solo CV: es un CV contra varios avisos", file=sys.stderr)
            return 2
        textos = []
        for ruta in args.avisos:
            try:
                textos.extend(separar_avisos(ruta.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError) as error:
                print(f"salteado {ruta.name}: {error}", file=sys.stderr)
        if not textos:
            print("no pude leer ninguno de los avisos", file=sys.stderr)
            return 2

        nombre_cv, cv = next(iter(cvs.items()))
        ofertas = comparar_avisos(cv, nombrar_avisos(textos))
        print(f"\n{nombre_cv} contra {len(ofertas)} avisos\n")
        print(_tabla(ofertas, "aviso"))
        marca = " (orientativo)" if not ofertas[0].resultado.confiable else ""
        print(f"\nconviene: {ofertas[0].nombre}{marca}")
        aviso = ofertas[0].texto
        resultado = ofertas[0].resultado
        base = cv
        adaptado = adaptar(cv, aviso)
    else:
        aviso = args.aviso.read_text(encoding="utf-8")
        filas = comparar(cvs, aviso)
        ganadora = filas[0]
        if len(filas) > 1:
            print(f"\ncomparando {len(filas)} CVs contra el mismo aviso\n")
            print(_tabla(filas))
            print(f"\ngana: {ganadora.nombre}")
        resultado = ganadora.resultado
        base = ganadora.cv
        adaptado = adaptar(base, aviso)

    _resumen(resultado, adaptado)
    print(_revision_texto(revisar(base, args.estilo)))

    if args.salida:
        html = render(adaptado, args.estilo, foto=foto, acento=args.acento, escala=args.escala)
        if args.salida.suffix.lower() == ".pdf":
            try:
                ruta = a_pdf(html, args.salida)
                print(f"\nescrito: {ruta}  (estilo {args.estilo}, PDF)")
            except PdfError as error:
                alternativa = args.salida.with_suffix(".html")
                alternativa.write_text(html, encoding="utf-8")
                print(f"\nno pude hacer el PDF: {error}")
                print(f"escribí {alternativa}: abrilo e imprimí desde el navegador.")
        else:
            args.salida.write_text(html, encoding="utf-8")
            print(f"\nescrito: {args.salida}  (estilo {args.estilo})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
