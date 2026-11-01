#!/usr/bin/env python3
"""Descarga de los CSV de personal y remuneraciones.

Método por defecto: el botón "Descargar CSV" de la ficha del organismo.
Método de respaldo: el CSV nacional de datos abiertos, leyendo por HTTP
Range solo el tramo del organismo.
"""

from __future__ import annotations

import csv
import html
import io
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import fuente as f

PAD = 65536          # margen para no cortar la primera/última fila del tramo
PROBE = 32768        # bytes para leer el código de organismo en la búsqueda
BLOQUE = 256 * 1024  # lectura incremental del tramo nacional
LIMITE_PRIMERA = 512 * 1024


def curl(args: list[str], intentos: int = 3, timeout: int = 60) -> bytes:
    for intento in range(intentos):
        p = subprocess.run(
            ["curl", "-sSL", "-A", f.UA, "--max-time", str(timeout)] + args,
            capture_output=True)
        if p.returncode == 0:
            return p.stdout
        if intento + 1 < intentos:
            time.sleep(2 * (intento + 1))
    raise RuntimeError("falló curl tras varios intentos")


def size_of(url: str) -> int:
    for intento in range(3):
        p = subprocess.run(["curl", "-sSIL", "-A", f.UA, "--max-time", "30", url],
                           capture_output=True, text=True)
        tamanos = re.findall(r"(?im)^content-length:\s*(\d+)", p.stdout)
        if tamanos:
            return int(tamanos[-1])
        if intento < 2:
            time.sleep(2)
    raise RuntimeError(f"no se pudo leer Content-Length de {url}")


def range_bytes(url: str, inicio: int, fin: int) -> bytes:
    return curl(["-r", f"{inicio}-{fin}", url])


def first_code(url: str, offset: int) -> str | None:
    """Código de organismo de la primera fila completa desde offset."""
    b = range_bytes(url, offset, offset + PROBE - 1)
    if offset > 0:
        i = b.find(b"\n")
        b = b[i + 1:] if i >= 0 else b""
    for linea in b.split(b"\n"):
        partes = linea.split(b";")
        if len(partes) > 4:
            codigo = partes[4].decode("cp1252", "replace").strip()
            if codigo and codigo != "organismo_codigo":
                return codigo
    return None


def org_range(url: str, org: str, size: int) -> tuple[int, int] | None:
    """[inicio, fin) en bytes del tramo del organismo, o None."""
    lo, hi = 0, size
    while lo < hi:
        mid = (lo + hi) // 2
        code = first_code(url, mid)
        if code is None or code >= org:
            hi = mid
        else:
            lo = mid + 1
    inicio = lo

    lo, hi = inicio, size
    while lo < hi:
        mid = (lo + hi) // 2
        code = first_code(url, mid)
        if code is None or code > org:
            hi = mid
        else:
            lo = mid + 1
    fin = lo

    if inicio >= fin:
        return None
    return max(0, inicio - PAD), min(size - 1, fin + PAD)


def header_of(url: str) -> list[str]:
    texto = range_bytes(url, 0, 65535).decode("cp1252", "replace")
    return next(csv.reader([texto.split("\n", 1)[0]], delimiter=";"))


def rows_of(url: str, org: str, size: int) -> tuple[list[str], list[list[str]]]:
    tramo = org_range(url, org, size)
    if not tramo:
        return header_of(url), []
    inicio, fin = tramo
    texto = range_bytes(url, inicio, fin).decode("cp1252", "replace")
    if inicio > 0:
        texto = texto.split("\n", 1)[-1]
    filas = [r for r in csv.reader(io.StringIO(texto), delimiter=";")
             if len(r) > 7 and r[4].strip() == org]
    return header_of(url), filas


def mes_de(fila: list[str]) -> tuple[int, int] | None:
    try:
        return int(fila[6]), f.mes_numero(fila[7]) or 0
    except (ValueError, IndexError):
        return None


def primer_pagina(org: str, archivo: str) -> tuple[str, int, int] | None:
    """(pagina, año, mes) de la primera fila del organismo en el CSV nacional."""
    url = f.BASE + archivo
    size = size_of(url)
    lo, hi = 0, size
    while lo < hi:
        mid = (lo + hi) // 2
        code = first_code(url, mid)
        if code is None or code >= org:
            hi = mid
        else:
            lo = mid + 1
    inicio = lo

    crudo = range_bytes(url, max(0, inicio - 8192),
                        min(size - 1, inicio + LIMITE_PRIMERA))
    texto = crudo.decode("cp1252", "replace")
    if inicio > 8192:
        texto = texto.split("\n", 1)[-1]
    for fila in csv.reader(io.StringIO(texto), delimiter=";"):
        if len(fila) > 7 and fila[4].strip() == org:
            mes = f.mes_numero(fila[7])
            if mes:
                return fila[0].strip(), int(fila[6]), mes
    return None


def meses_publicados(org: str, archivo: str, anio: int | None = None) -> dict[int, str]:
    """{mes: pagina} del año pedido (o del año más reciente si anio=None)."""
    url = f.BASE + archivo
    size = size_of(url)
    tramo = org_range(url, org, size)
    if not tramo:
        return {}

    inicio, fin = tramo
    paginas: dict[int, str] = {}
    objetivo = anio
    pos = inicio
    pendiente = ""
    descartar_primera = inicio > 0

    while pos <= fin:
        crudo = range_bytes(url, pos, min(fin, pos + BLOQUE - 1))
        if not crudo:
            break
        texto = pendiente + crudo.decode("cp1252", "replace")
        pendiente = ""

        if descartar_primera:
            corte = texto.find("\n")
            if corte < 0:
                pos += len(crudo)
                continue
            texto = texto[corte + 1:]
            descartar_primera = False

        lineas = texto.split("\n")
        pendiente = lineas.pop()
        for linea in lineas:
            fila = next(csv.reader([linea], delimiter=";"), [])
            if len(fila) <= 7 or fila[4].strip() != org:
                continue
            try:
                y = int(fila[6])
            except ValueError:
                continue
            mes = f.mes_numero(fila[7])
            if not mes:
                continue

            if objetivo is None:
                objetivo = y
            if y > objetivo:
                continue
            if y < objetivo:
                return paginas
            paginas.setdefault(mes, fila[0].strip())
            if len(paginas) == 12:
                return paginas

        pos += len(crudo)

    return paginas


def http_get(url: str, jar: str) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        destino = tmp.name
    try:
        p = curl(["-b", jar, "-c", jar, "-o", destino, "-w", "%{http_code}", url])
        codigo = p.decode().strip()
        if codigo != "200":
            raise RuntimeError(f"HTTP {codigo}")
        return Path(destino).read_bytes()
    finally:
        os.unlink(destino)


def http_post(url: str, jar: str, datos: dict[str, str]) -> tuple[str, bytes]:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        destino = tmp.name
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        cabeceras = tmp.name
    try:
        args = ["-b", jar, "-c", jar, "-D", cabeceras,
                "-o", destino, "-w", "%{http_code}"]
        for clave, valor in datos.items():
            args += ["--data-urlencode", f"{clave}={valor}"]
        p = curl(args + [url])
        codigo = p.decode().strip()
        if codigo != "200":
            raise RuntimeError(f"HTTP {codigo}")
        head = Path(cabeceras).read_text(encoding="latin-1")
        return head, Path(destino).read_bytes()
    finally:
        os.unlink(destino)
        os.unlink(cabeceras)


def datos_formulario(h: str) -> tuple[str, str, str, str, str]:
    """(id_formulario, action, ViewState, encodedURL, botón) de la ficha.

    El id del formulario cambia entre organismos/versiones del portal, así que
    se descubre desde el HTML en vez de fijarlo.
    """
    form = re.search(r'<form[^>]*id="([^"]*formInfo[^"]*)"[^>]*>', h)
    if not form:
        raise RuntimeError("no se encontró el formulario de la ficha")
    form_id = form.group(1)

    accion = re.search(r'action="([^"]+)"', form.group(0))
    vs = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', h)
    enc = re.search(r'name="javax\.faces\.encodedURL"[^>]*value="([^"]+)"', h)
    if not accion or not vs or not enc:
        raise RuntimeError("no se encontraron los campos JSF de la ficha")

    boton = ""
    for tag in re.findall(r"<button[^>]*>", h):
        if "Descargar CSV" in tag:
            encontrado = re.search(r'name="([^"]+)"', tag)
            if encontrado:
                boton = encontrado.group(1)
                break
    if not boton:
        raise RuntimeError("no se encontró el nombre del botón CSV")

    return (form_id, html.unescape(accion.group(1)), vs.group(1),
            html.unescape(enc.group(1)), boton)


def descargar_pagina(org: str, pagina: str, tipo: str, out: str | Path,
                     anio: int | None = None, mes: int | None = None,
                     force: bool = False) -> tuple[Path, int | None, int, int]:
    """Descarga una publicación con el botón CSV y devuelve (ruta, filas, año, mes)."""
    salida = Path(out)
    salida.mkdir(parents=True, exist_ok=True)

    if anio and mes and not force:
        destino = salida / f"{org}_personal_{tipo}_{anio:04d}-{mes:02d}.csv"
        if destino.exists():
            print(f"[{tipo}] ya existe {destino.name}, se omite", flush=True)
            return destino, None, anio, mes

    for intento in range(3):
        with tempfile.TemporaryDirectory() as tmp:
            jar = str(Path(tmp) / "cookies.txt")
            try:
                url = f"{f.FICHA}?org={org}&pagina={pagina}"
                h = http_get(url, jar).decode("utf-8", "replace")
                if "Descargar CSV" not in h:
                    raise RuntimeError("la página no tiene el botón Descargar CSV")

                form_id, action, vs, enc, boton = datos_formulario(h)
                datos = {
                    form_id: form_id,
                    f"{form_id}:searchBar": "",
                    boton: "",
                    "javax.faces.ViewState": vs,
                    "javax.faces.encodedURL": enc,
                }
                cabeceras, cuerpo = http_post(action, jar, datos)
                if "text/csv" not in cabeceras.lower():
                    raise RuntimeError("respuesta no es CSV: " + cabeceras[:200])

                texto = cuerpo.decode("iso-8859-15", "replace")
                filas = list(csv.reader(io.StringIO(texto), delimiter=";"))
                if len(filas) < 2:
                    raise RuntimeError("CSV vacío")
                anio_csv = int(filas[1][0])
                mes_csv = f.mes_numero(filas[1][1])
                if not mes_csv:
                    raise RuntimeError("no se pudo leer el mes del CSV")

                destino = salida / (
                    f"{org}_personal_{tipo}_{anio_csv:04d}-{mes_csv:02d}.csv")
                f.escribir_csv(destino, filas[0], filas[1:])
                return destino, len(filas) - 1, anio_csv, mes_csv
            except Exception as e:
                if intento == 2:
                    raise
                print(f"  reintentando ({e})", flush=True)
                time.sleep(3)

    raise RuntimeError("no se pudo descargar la publicación")


def combinar_anual(paths: list[Path], destino: Path) -> int:
    """Une los CSV mensuales sin cargarlos completos en memoria."""
    total = 0
    with open(destino, "w", encoding="utf-8-sig", newline="") as out:
        for i, path in enumerate(paths):
            with open(path, encoding="utf-8-sig", newline="") as src:
                for n, linea in enumerate(src):
                    if n == 0:
                        if i == 0:
                            out.write(linea)
                        continue
                    if linea.strip():
                        out.write(linea)
                        total += 1
    return total


def nacional(args) -> None:
    """Descarga desde el CSV nacional usando HTTP Range."""
    pedido = None
    if args.mes:
        anio, mes = map(int, args.mes.split("-"))
        pedido = (anio, mes)

    for tipo in args.tipo:
        archivo = f.DATASETS[tipo]
        url = f.BASE + archivo
        print(f"[{tipo}] leyendo {archivo} ...", flush=True)
        size = size_of(url)
        cabecera, filas = rows_of(url, args.org, size)
        if not filas:
            print(f"[{tipo}] sin datos para {args.org}")
            continue

        if args.todo:
            elegidas, etiqueta = filas, "historico"
        elif args.anio:
            elegidas = [r for r in filas
                        if (mes_de(r) or (0, 0))[0] == args.anio]
            etiqueta = str(args.anio)
        else:
            meses = {m for m in (mes_de(r) for r in filas) if m and m[1]}
            if not meses:
                print(f"[{tipo}] sin meses válidos")
                continue
            objetivo = pedido or max(meses)
            elegidas = [r for r in filas if mes_de(r) == objetivo]
            etiqueta = f"{objetivo[0]:04d}-{objetivo[1]:02d}"

        if not elegidas:
            print(f"[{tipo}] sin filas para {etiqueta}")
            continue

        destino = Path(args.out) / f"{args.org}_personal_{tipo}_{etiqueta}.csv"
        if destino.exists() and not args.force:
            print(f"[{tipo}] ya existe {destino.name}, se omite")
            continue
        f.escribir_csv(destino, cabecera, elegidas)
        print(f"[{tipo}] {len(elegidas)} filas -> {destino}")


def boton(args) -> None:
    """Descarga desde el botón CSV de la ficha (método por defecto)."""
    if args.pagina:
        tipo = args.tipo[0] if len(args.tipo) == 1 else "personal"
        destino, filas, anio, mes = descargar_pagina(
            args.org, args.pagina, tipo, args.out, force=args.force)
        if filas is None:
            print(f"[{tipo}] {destino}")
        else:
            print(f"[{tipo}] {filas} filas ({mes:02d}/{anio}) -> {destino}")
        return

    for tipo in args.tipo:
        if args.mes:
            anio, mes = map(int, args.mes.split("-"))
            print(f"[{tipo}] buscando {anio}-{mes:02d} ...", flush=True)
            paginas = meses_publicados(args.org, f.DATASETS[tipo], anio)
            pagina = paginas.get(mes)
            if not pagina:
                print(f"[{tipo}] sin publicación para {anio}-{mes:02d}")
                continue
            destino, filas, _, _ = descargar_pagina(
                args.org, pagina, tipo, args.out, anio, mes, args.force)
            if filas is not None:
                print(f"[{tipo}] {filas} filas -> {destino}")
            continue

        if args.anio:
            print(f"[{tipo}] buscando meses de {args.anio} ...", flush=True)
            paginas = meses_publicados(args.org, f.DATASETS[tipo], args.anio)
            if not paginas:
                print(f"[{tipo}] sin datos para {args.anio}")
                continue

            destinos = []
            for mes in sorted(paginas):
                pagina = paginas[mes]
                print(f"[{tipo}] {mes:02d}/{args.anio} página {pagina} ...",
                      flush=True)
                destino, filas, _, _ = descargar_pagina(
                    args.org, pagina, tipo, args.out, args.anio, mes, args.force)
                if filas is not None:
                    print(f"[{tipo}] {filas} filas -> {destino}")
                destinos.append(destino)

            combinado = Path(args.out) / (
                f"{args.org}_personal_{tipo}_{args.anio}.csv")
            if combinado.exists() and not args.force:
                print(f"[{tipo}] ya existe {combinado.name}, se omite")
            else:
                total = combinar_anual(destinos, combinado)
                print(f"[{tipo}] {total} filas -> {combinado}")
            continue

        print(f"[{tipo}] buscando último mes ...", flush=True)
        ultimo = primer_pagina(args.org, f.DATASETS[tipo])
        if not ultimo:
            print(f"[{tipo}] sin datos para {args.org}")
            continue
        pagina, anio, mes = ultimo
        print(f"[{tipo}] página {pagina} ({mes} {anio}), descargando ...",
              flush=True)
        destino, filas, _, _ = descargar_pagina(
            args.org, pagina, tipo, args.out, anio, mes, args.force)
        if filas is not None:
            print(f"[{tipo}] {filas} filas -> {destino}")
