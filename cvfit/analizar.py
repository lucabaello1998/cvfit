"""CLI: analizar un CV contra un aviso y escribir el CV adaptado."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .adaptar import adaptar
from .cv import cargar, parsear
from .extraer import ExtraccionError, estructurar, extraer_desde_archivo
from .match import evaluar
from .plantillas import NOMBRES, render

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cvfit", description="Encaje CV ↔ aviso y CV adaptado")
    parser.add_argument("--cv", required=True, type=Path, help="CV en .md, .txt, .docx o .pdf")
    parser.add_argument("--aviso", required=True, type=Path, help="texto del aviso")
    parser.add_argument("--estilo", default="ats", choices=sorted(NOMBRES))
    parser.add_argument("--salida", type=Path, help="archivo HTML de salida")
    args = parser.parse_args(argv)

    try:
        cv = leer_cv(args.cv)
    except ExtraccionError as error:
        print(f"no pude leer {args.cv.name}: {error}", file=sys.stderr)
        return 2

    aviso = args.aviso.read_text(encoding="utf-8")
    resultado = evaluar(cv, aviso)
    adaptado = adaptar(cv, aviso)

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
        args.salida.write_text(render(adaptado, args.estilo), encoding="utf-8")
        print(f"\nescrito: {args.salida}  (estilo {args.estilo})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
