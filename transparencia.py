#!/usr/bin/env python3
"""CLI de descarga y análisis de personal y remuneraciones.

Ejemplos:
    python3 transparencia.py descargar --tipo contrata --anio 2026
    python3 transparencia.py comparar --patron "*contrata*.csv"
    python3 transparencia.py ranking cargos --por cargo_hasta
    python3 transparencia.py ranking personas --top 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import descarga
import fuente as f
import grados
import rankings
import reporte

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos"
VARIACIONES = DATOS / "variaciones_grado.csv"


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transparencia.py",
        description="Descarga y análisis de personal y remuneraciones desde el Portal de Transparencia.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python3 transparencia.py descargar --tipo contrata --anio 2026\n"
            "  python3 transparencia.py descargar --tipo contrata --mes 2026-09\n"
            "  python3 transparencia.py comparar --patron \"*contrata*.csv\"\n"
            "  python3 transparencia.py ranking cargos --por cargo_hasta\n"
            "  python3 transparencia.py ranking personas --top 15\n"
        ),
    )
    sub = p.add_subparsers(dest="comando", required=True)

    d = sub.add_parser("descargar", help="bajar CSV desde el portal")
    d.add_argument("--org", default=f.ORG_POR_DEFECTO,
                   help="código del organismo (por defecto AJ011)")
    d.add_argument("--tipo", nargs="+", choices=list(f.DATASETS),
                   default=list(f.DATASETS),
                   help="contrata, planta, honorarios, codigo_trabajo")
    d.add_argument("--out", default=str(DATOS), help="carpeta de destino")
    d.add_argument("--metodo", choices=["boton", "nacional"], default="boton",
                   help="boton = ficha (por defecto); nacional = CSV abierto")
    grupo = d.add_mutually_exclusive_group()
    grupo.add_argument("--mes", help="YYYY-MM")
    grupo.add_argument("--anio", type=int, help="YYYY")
    grupo.add_argument("--todo", action="store_true",
                       help="todo el historial (solo método nacional)")
    d.add_argument("--pagina", help="ID de publicación (solo método botón)")
    d.add_argument("--force", action="store_true",
                   help="volver a descargar aunque el archivo exista")

    c = sub.add_parser("comparar", help="comparar grados entre CSV")
    c.add_argument("--dir", default=str(DATOS), help="carpeta con los CSV")
    c.add_argument("--patron", default="*.csv", help="patrón de archivos")
    c.add_argument("--org", help="filtrar por código de organismo (ej. AJ011)")
    c.add_argument("--salida", default=str(VARIACIONES),
                   help="CSV de variaciones")

    r = sub.add_parser("ranking", help="generar rankings de cambios")
    rsub = r.add_subparsers(dest="tipo_ranking", required=True)

    rc = rsub.add_parser("cargos", help="cargos con más cambios de grado")
    rc.add_argument("--entrada", default=str(VARIACIONES))
    rc.add_argument("--por", choices=["cargo_hasta", "cargo_desde"],
                    default="cargo_hasta")
    rc.add_argument("--top", type=int, default=10)
    rc.add_argument("--salida", help="CSV de salida (también genera .md)")

    rp = rsub.add_parser("personas", help="personas con más cambios de grado")
    rp.add_argument("--entrada", default=str(VARIACIONES))
    rp.add_argument("--top", type=int, default=10)
    rp.add_argument("--salida", help="CSV de salida (también genera .md)")

    return p


def cmd_descargar(args) -> int:
    Path(args.out).mkdir(parents=True, exist_ok=True)
    if args.metodo == "boton":
        descarga.boton(args)
    else:
        descarga.nacional(args)
    return 0


def cmd_comparar(args) -> int:
    directorio = Path(args.dir)
    if not directorio.is_dir():
        print(f"no existe la carpeta {directorio}", file=sys.stderr)
        return 1

    salida = Path(args.salida).resolve()
    archivos = [p for p in sorted(directorio.glob(args.patron))
                if p.is_file() and p.resolve() != salida
                and (not args.org or p.name.startswith(f"{args.org}_"))]
    if not archivos:
        filtro = f" para {args.org}" if args.org else ""
        print(f"no hay archivos {args.patron}{filtro} en {directorio}",
              file=sys.stderr)
        return 1

    cambios, total, unicos, personas, ambiguos = grados.analizar(archivos)
    grados.escribir(cambios, salida)

    print(f"{len(archivos)} archivos, {total} filas, "
          f"{unicos} únicas, {personas} personas")
    print(f"{len(cambios)} variaciones de grado -> {salida}")
    if ambiguos:
        print(f"{ambiguos} casos con varios grados en el mismo mes (ver avisos)")
    return 0


def cmd_ranking(args) -> int:
    entrada = Path(args.entrada)
    if not entrada.exists():
        print(f"no existe {entrada}", file=sys.stderr)
        return 1

    filas = f.leer_dicts(entrada)
    if not filas:
        print(f"{entrada} no tiene variaciones", file=sys.stderr)
        return 1

    if args.tipo_ranking == "cargos":
        ranking = rankings.cargos(filas, args.por)
        salida = (Path(args.salida) if args.salida
                  else entrada.parent / f"ranking_cargos_{args.por}.csv")
        campos = ["cargo", "cambios", "personas", "transicion_mas_comun",
                  "veces_transicion", "anios"]
        f.escribir_dicts(salida, campos, ranking)

        n = min(args.top, len(ranking))
        reporte.escribir_md(
            salida.with_suffix(".md"),
            "Ranking de cargos por cambios de grado",
            f"{len(filas)} cambios en {len(ranking)} cargos. "
            f"Criterio: `{args.por}`. Top {n}.",
            ["#", "Cargo", "Cambios", "Personas", "Transición más común", "Años"],
            [[i, r["cargo"], r["cambios"], r["personas"],
              r["transicion_mas_comun"], r["anios"]]
             for i, r in enumerate(ranking[:args.top], 1)],
        )
        print(f"{len(filas)} cambios, {len(ranking)} cargos -> {salida}")
        print(f"markdown -> {salida.with_suffix('.md')}")
        print(f"\nTop {n} por {args.por}:")
        for r in ranking[:args.top]:
            print(f"  {r['cambios']:3d} cambios, {r['personas']:3d} personas  "
                  f"{r['cargo']}  ({r['transicion_mas_comun']})")
        return 0

    ranking = rankings.personas(filas)
    salida = (Path(args.salida) if args.salida
              else entrada.parent / "ranking_personas.csv")
    campos = ["nombre", "cambios", "periodo_primero", "periodo_ultimo",
              "grados", "cargos", "detalle"]
    f.escribir_dicts(salida, campos, ranking)

    n = min(args.top, len(ranking))
    reporte.escribir_md(
        salida.with_suffix(".md"),
        "Ranking de personas por cambios de grado",
        f"{len(filas)} cambios en {len(ranking)} personas. Top {n}.",
        ["#", "Persona", "Cambios", "Secuencia", "Período", "Detalle"],
        [[i, r["nombre"], r["cambios"], r["grados"],
          f"{r['periodo_primero']} a {r['periodo_ultimo']}", r["detalle"]]
         for i, r in enumerate(ranking[:args.top], 1)],
    )
    print(f"{len(filas)} cambios, {len(ranking)} personas -> {salida}")
    print(f"markdown -> {salida.with_suffix('.md')}")
    print(f"\nTop {n}:")
    for r in ranking[:args.top]:
        print(f"  {r['cambios']} cambios  {r['grados']}  {r['nombre']}  "
              f"({r['periodo_primero']} a {r['periodo_ultimo']})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    if args.comando == "descargar":
        if args.mes:
            partes = args.mes.split("-")
            if (len(partes) != 2 or not all(x.isdigit() for x in partes)
                    or not 1 <= int(partes[1]) <= 12):
                parser.error("--mes debe tener formato YYYY-MM")
        if args.metodo == "boton":
            if args.todo:
                parser.error("--todo solo funciona con --metodo nacional")
            if args.pagina and (args.mes or args.anio):
                parser.error("--pagina no se combina con --mes/--anio")
        elif args.pagina:
            parser.error("--pagina solo funciona con --metodo boton")
        return cmd_descargar(args)

    if args.comando == "comparar":
        return cmd_comparar(args)

    return cmd_ranking(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
