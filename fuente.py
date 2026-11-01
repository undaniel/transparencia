#!/usr/bin/env python3
"""Constantes y utilidades compartidas de la fuente de datos."""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

ORG_POR_DEFECTO = "AJ011"
BASE = "https://www.cplt.cl/transparencia_activa/datoabierto/archivos/"
FICHA = "https://www.portaltransparencia.cl/PortalPdT/directorio-de-organismos-regulados/"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DATASETS = {
    "contrata": "TA_PersonalContrata.csv",
    "planta": "TA_PersonalPlanta.csv",
    "honorarios": "TA_PersonalContratohonorarios.csv",
    "codigo_trabajo": "TA_PersonalCodigotrabajo.csv",
}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Nombres de columna aceptados en los CSV del botón y del archivo nacional.
CAMPOS = {
    "anio": ["año", "ano", "anyo", "year"],
    "mes": ["mes", "month"],
    "grado": ["grado eus o jornada", "grado eus", "grado_eus", "grado"],
    "nombre": ["nombre completo"],
    "nombres": ["nombres"],
    "paterno": ["paterno"],
    "materno": ["materno"],
    "cargo": ["cargo o función", "cargo o funcion", "tipo cargo", "cargo"],
}


def norm(texto: object) -> str:
    """Minúsculas, sin tildes y con espacios simples."""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def mes_numero(valor: object) -> int | None:
    """'Septiembre', '09' o 9 -> 9. Cualquier otra cosa -> None."""
    s = norm(valor)
    if s.isdigit():
        n = int(s)
        return n if 1 <= n <= 12 else None
    return MESES.get(s)


def leer_texto(path: Path | str) -> str:
    """Lee un CSV probando las codificaciones habituales del portal."""
    datos = Path(path).read_bytes()
    for codificacion in ("utf-8-sig", "utf-8", "iso-8859-15", "cp1252"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"no se pudo decodificar {path}")


def leer_csv(path: Path | str) -> list[list[str]]:
    texto = leer_texto(path)
    primera = texto.split("\n", 1)[0]
    delimitador = ";" if primera.count(";") >= primera.count(",") else ","
    return list(csv.reader(texto.splitlines(), delimiter=delimitador))


def leer_dicts(path: Path | str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def escribir_csv(path: Path | str, cabecera: list[str], filas) -> None:
    """CSV en UTF-8 con BOM y separador ';', como el resto del proyecto."""
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        if cabecera:
            w.writerow(cabecera)
        w.writerows(filas)


def escribir_dicts(path: Path | str, campos: list[str], filas) -> None:
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


def detectar_columnas(cabecera: list[str]) -> dict[str, int]:
    """Índice de cada campo, sin depender del orden ni de tildes."""
    h = [norm(x).replace("_", " ") for x in cabecera]
    idx: dict[str, int] = {}
    for campo, alias in CAMPOS.items():
        for a in alias:
            a = norm(a).replace("_", " ")
            if a in h:
                idx[campo] = h.index(a)
                break
    if "grado" not in idx:
        for i, nombre in enumerate(h):
            if nombre.startswith("grado"):
                idx["grado"] = i
                break
    return idx


def nombre_de(fila: list[str], idx: dict[str, int]) -> str:
    if "nombre" in idx:
        return fila[idx["nombre"]].strip()
    partes = [fila[idx[k]].strip() for k in ("nombres", "paterno", "materno")
              if k in idx and idx[k] < len(fila)]
    return " ".join(p for p in partes if p)
