#!/usr/bin/env python3
"""Salida Markdown de los rankings."""

from __future__ import annotations

from pathlib import Path


def escribir_md(path: str | Path, titulo: str, resumen: str,
                cabecera: list[str], filas: list[list]) -> None:
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(f"# {titulo}\n\n{resumen}\n\n")
        f.write("| " + " | ".join(cabecera) + " |\n")
        f.write("|" + "|".join("---:" for _ in cabecera) + "|\n")
        for fila in filas:
            f.write("| " + " | ".join(
                str(c).replace("|", "\\|") for c in fila) + " |\n")
