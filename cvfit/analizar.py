"""CLI: analizar un CV contra un aviso y escribir el CV adaptado."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .adaptar import adaptar
from .comparar import comparar
from .cv import cargar, parsear
from .extraer import ExtraccionError, estructurar, extraer_desde_archivo
from .plantillas import NOMBRES, foto_desde_archivo, render

VEREDICTOS = {
    "alta": "Encaje alto: podés respaldar casi todo lo que pide el aviso.",
    "media": "Encaje medio: llegás a la entrevista si tapás los gaps marcados.",
    "baja": "Encaje bajo: el aviso pide cosas que hoy no podés respaldar.",
}


def leer_cv(ruta):
    """Acepta .md/.txt/.docx/.pdf. Un PDF se estructura a Markdown antes de parsear."""
    if ruta.suffix.lower() == ".pdf":
        return parsear(estructurar(extraer_desde_archivo(ruta)))
    if ruta.suffix.lower() == ".docx":
        return parsear(extraer_desde_archivo(ruta))
    return cargar(ruta)


def _tabla(filas) -> str:
    """Ranking en texto: sin dependencias, alineado a ojo."""
    ancho_nombre = max(len(fila.nombre) for fila in filas) + 2
    encabezado = f"{'#':>2}  {'CV':<{ancho_nombre}}{'encaje':>7}  {'respaldados':>11}  gaps excluyentes"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cvfit", description="Encaje CV ↔ aviso y CV adaptado")
    parser.add_argument(
        "--cv",
        required=True,
        type=Path,
        nargs="+",
        help="uno o varios CV (.md, .txt, .docx o .pdf); con varios se comparan contra el mismo aviso",
    )
    parser.add_argument("--aviso", required=True, type=Path, help="texto del aviso")
    parser.add_argument("--estilo", default="ats", choices=sorted(NOMBRES))
    parser.add_argument("--foto", type=Path, help="foto de perfil (.png, .jpg o .webp) para el encabezado")
    parser.add_argument("--acento", help="color de acento en hex, por ejemplo #1f5f8b")
    parser.add_argument("--escala", type=float, help="tamaño de letra: 0.9 a 1.3 (1 = normal)")
    parser.add_argument("--salida", type=Path, help="archivo HTML de salida")
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

    aviso = args.aviso.read_text(encoding="utf-8")
    filas = comparar(cvs, aviso)
    ganadora = filas[0]

    if len(filas) > 1:
        print(f"\ncomparando {len(filas)} CVs contra el mismo aviso\n")
        print(_tabla(filas))
        print(f"\ngana: {ganadora.nombre}")

    resultado = ganadora.resultado
    adaptado = adaptar(ganadora.cv, aviso)

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

    if args.salida:
        html = render(adaptado, args.estilo, foto=foto, acento=args.acento, escala=args.escala)
        args.salida.write_text(html, encoding="utf-8")
        print(f"\nescrito: {args.salida}  (estilo {args.estilo})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
