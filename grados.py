#!/usr/bin/env python3
"""Comparación del grado EUS/jornada de cada persona a través del tiempo."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import fuente as f

CAMPOS_SALIDA = [
    "nombre", "periodo_desde", "grado_desde", "periodo_hasta", "grado_hasta",
    "meses_entre", "cargo_desde", "cargo_hasta", "variacion",
]


def grade_key(grado: str) -> str:
    """Normaliza '12', '12.0' y '12,0' para comparar grados numéricos."""
    grado = grado.strip()
    try:
        numero = float(grado.replace(",", "."))
        return str(int(numero)) if numero.is_integer() else str(numero)
    except ValueError:
        return f.norm(grado)


def leer_archivo(path: Path) -> list[dict]:
    """Registros de un CSV, detectando las columnas por nombre."""
    filas = f.leer_csv(path)
    if not filas:
        return []
    idx = f.detectar_columnas(filas[0])
    faltan = [c for c in ("anio", "mes", "grado") if c not in idx]
    if faltan or ("nombre" not in idx and "nombres" not in idx):
        print(f"[omitido] {path.name}: faltan columnas {faltan}", file=sys.stderr)
        return []

    registros = []
    for fila in filas[1:]:
        if len(fila) <= max(idx.values()):
            continue
        try:
            anio = int(fila[idx["anio"]])
        except ValueError:
            continue
        mes = f.mes_numero(fila[idx["mes"]])
        grado = fila[idx["grado"]].strip()
        if not mes or not grado:
            continue

        nombre = f.nombre_de(fila, idx)
        if not nombre:
            continue
        cargo = fila[idx["cargo"]].strip() if "cargo" in idx else ""
        registros.append({
            "nombre": nombre,
            "clave": f.norm(nombre),
            "periodo": f"{anio:04d}-{mes:02d}",
            "anio": anio,
            "mes": mes,
            "grado": grado,
            "grado_key": grade_key(grado),
            "cargo": cargo,
            "archivo": path.name,
        })
    return registros


def analizar(archivos: list[Path]) -> tuple[list[dict], int, int, int, int]:
    """Devuelve (cambios, filas, únicas, personas, casos ambiguos)."""
    registros: list[dict] = []
    for path in archivos:
        registros += leer_archivo(path)

    # El combinado anual y los mensuales traen las mismas filas.
    vistos = set()
    unicos = []
    for r in registros:
        clave = (r["clave"], r["periodo"], r["grado_key"], f.norm(r["cargo"]))
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(r)

    por_persona = defaultdict(lambda: defaultdict(list))
    for r in unicos:
        por_persona[r["clave"]][r["periodo"]].append(r)

    cambios = []
    ambiguos = 0
    for clave, periodos in por_persona.items():
        linea = []
        for periodo in sorted(periodos):
            filas = periodos[periodo]
            grados = {x["grado_key"] for x in filas}
            if len(grados) > 1:
                ambiguos += 1
                print(f"[aviso] {filas[0]['nombre']} tiene varios grados en "
                      f"{periodo}: " + ", ".join(sorted(x["grado"] for x in filas)),
                      file=sys.stderr)
            x = filas[0]
            linea.append((periodo, x["grado"], x["grado_key"], x["cargo"]))

        for (p1, g1, k1, c1), (p2, g2, k2, c2) in zip(linea, linea[1:]):
            if k1 == k2:
                continue
            y1, m1 = map(int, p1.split("-"))
            y2, m2 = map(int, p2.split("-"))
            cambios.append({
                "nombre": por_persona[clave][p1][0]["nombre"],
                "periodo_desde": p1,
                "grado_desde": g1,
                "periodo_hasta": p2,
                "grado_hasta": g2,
                "meses_entre": (y2 - y1) * 12 + (m2 - m1),
                "cargo_desde": c1,
                "cargo_hasta": c2,
                "variacion": f"{g1} -> {g2}",
            })

    cambios.sort(key=lambda x: (f.norm(x["nombre"]), x["periodo_hasta"]))
    return cambios, len(registros), len(unicos), len(por_persona), ambiguos


def escribir(cambios: list[dict], destino: str | Path) -> None:
    f.escribir_dicts(destino, CAMPOS_SALIDA, cambios)
