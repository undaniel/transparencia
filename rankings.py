#!/usr/bin/env python3
"""Rankings de cargos y personas a partir de las variaciones de grado."""

from __future__ import annotations

from collections import Counter, defaultdict


def cargos(filas: list[dict], por: str = "cargo_hasta") -> list[dict]:
    """Agrupa los cambios por cargo y ordena por cantidad de cambios."""
    stats = defaultdict(lambda: {
        "cambios": 0,
        "personas": set(),
        "transiciones": Counter(),
        "anios": Counter(),
    })
    for r in filas:
        cargo = r[por].strip() or "(sin cargo)"
        s = stats[cargo]
        s["cambios"] += 1
        s["personas"].add(r["nombre"])
        s["transiciones"][r["variacion"]] += 1
        s["anios"][r["periodo_hasta"][:4]] += 1

    ranking = []
    for cargo, s in stats.items():
        transicion, veces = s["transiciones"].most_common(1)[0]
        ranking.append({
            "cargo": cargo,
            "cambios": s["cambios"],
            "personas": len(s["personas"]),
            "transicion_mas_comun": transicion,
            "veces_transicion": veces,
            "anios": "; ".join(f"{a}: {n}" for a, n in sorted(s["anios"].items())),
        })
    ranking.sort(key=lambda x: (-x["cambios"], -x["personas"], x["cargo"]))
    return ranking


def personas(filas: list[dict]) -> list[dict]:
    """Cuenta cambios por persona y arma su secuencia de grados."""
    por_persona = defaultdict(list)
    for r in filas:
        por_persona[r["nombre"]].append(r)

    ranking = []
    for nombre, cambios in por_persona.items():
        cambios.sort(key=lambda x: x["periodo_hasta"])
        grados = [cambios[0]["grado_desde"]]
        grados += [c["grado_hasta"] for c in cambios]
        cargos = set()
        for c in cambios:
            if c["cargo_desde"]:
                cargos.add(c["cargo_desde"])
            if c["cargo_hasta"]:
                cargos.add(c["cargo_hasta"])
        ranking.append({
            "nombre": nombre,
            "cambios": len(cambios),
            "periodo_primero": cambios[0]["periodo_desde"],
            "periodo_ultimo": cambios[-1]["periodo_hasta"],
            "grados": " -> ".join(grados),
            "cargos": " | ".join(sorted(cargos)),
            "detalle": "; ".join(
                f"{c['periodo_hasta']}: {c['variacion']}" for c in cambios),
        })
    ranking.sort(key=lambda x: (-x["cambios"], x["nombre"]))
    return ranking
