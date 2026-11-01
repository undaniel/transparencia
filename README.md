# transparencia

Descarga y análisis de los registros de personal y remuneraciones publicados
en el Portal de Transparencia. Funciona con **cualquier organismo**: el código
se indica con `--org` (por defecto `AJ011`, usado solo como ejemplo).

El método de descarga por defecto es el botón **Descargar CSV** de la ficha
del organismo. Como respaldo usa el CSV nacional de datos abiertos, leyendo
por HTTP `Range` solo el tramo del organismo pedido.

## Requisitos

- Python 3.8 o superior.
- `curl`.
- Sin dependencias de terceros.

## Estructura

```text
transparencia/
├── transparencia.py   # CLI: descargar | comparar | ranking
├── fuente.py          # URLs, tipos de dato, lectura/escritura CSV
├── descarga.py        # botón CSV (defecto) y CSV nacional (respaldo)
├── grados.py          # comparación de "Grado EUS o jornada"
├── rankings.py        # rankings de cargos y personas
├── reporte.py         # salida Markdown
├── tests/             # pruebas sin red
├── datos/             # CSV descargados y resultados
├── .gitignore
└── README.md
```

## Uso rápido

```bash
cd transparencia

# Último mes publicado del organismo por defecto (AJ011)
python3 transparencia.py descargar

# Solo contrata, un mes concreto
python3 transparencia.py descargar --tipo contrata --mes 2026-09

# Contrata, todos los meses de un año
python3 transparencia.py descargar --tipo contrata --anio 2026

# Otro organismo
python3 transparencia.py descargar --org MU306 --tipo contrata --mes 2026-09

# Respaldo con el CSV nacional
python3 transparencia.py descargar --org MU306 --tipo contrata --anio 2026 \
  --metodo nacional
```

Los archivos se guardan en `datos/` con el código del organismo en el nombre:

```text
AJ011_personal_contrata_2026-09.csv      # un mes
AJ011_personal_contrata_2026.csv         # combinado del año
MU306_personal_contrata_2026-09.csv
```

Si el archivo ya existe se omite. Usa `--force` para volver a descargarlo.

## Trabajar con otros organismos

El código de organismo es el parámetro `org` de la URL del portal, por ejemplo
`?org=MU306`. Se puede obtener desde el directorio de organismos regulados.

Descargar:

```bash
python3 transparencia.py descargar --org MU306 --tipo contrata --anio 2026
```

Comparar solo los archivos de ese organismo:

```bash
python3 transparencia.py comparar --org MU306 --patron "*contrata*.csv" \
  --salida datos/variaciones_MU306.csv
```

Rankings de ese organismo:

```bash
python3 transparencia.py ranking cargos --entrada datos/variaciones_MU306.csv
python3 transparencia.py ranking personas --entrada datos/variaciones_MU306.csv
```

El filtro `--org` evita mezclar instituciones en la comparación. Los nombres de
archivo ya incluyen el código, así que varios organismos pueden convivir en la
misma carpeta.

## Descarga

### Método `boton` (por defecto)

1. Ubica el `pagina=` de cada mes leyendo el tramo del organismo en el CSV
   nacional (viene ordenado con el mes más reciente primero).
2. Abre la ficha `?org=<código>&pagina=<id>`.
3. Descubre el formulario JSF de la ficha y replica el POST del botón
   **Descargar CSV**.
4. Guarda el CSV en UTF-8 con BOM y separador `;`.

El id del formulario y el nombre del botón se leen del HTML, no están fijos:
sirven para distintos organismos y versiones del portal.

Para un año, además de un archivo por mes genera el combinado anual.

### Método `nacional` (respaldo)

Descarga solo el tramo del organismo del CSV nacional mediante HTTP `Range`
(~23 MB en vez de ~14,6 GB) y recorta el mes o año pedido. Trae las 42
columnas oficiales.

### Parámetros

| Parámetro | Qué hace |
|---|---|
| `--org` | Código del organismo (por defecto `AJ011`) |
| `--tipo` | `contrata`, `planta`, `honorarios`, `codigo_trabajo` |
| `--mes` | `YYYY-MM` |
| `--anio` | `YYYY`, todos los meses publicados |
| `--todo` | Todo el historial (solo `--metodo nacional`) |
| `--pagina` | ID de publicación concreta (solo `--metodo boton`) |
| `--out` | Carpeta de destino (por defecto `datos/`) |
| `--metodo` | `boton` (por defecto) o `nacional` |
| `--force` | Ignora los archivos existentes |

## Comparar grados

```bash
# Todos los CSV de una carpeta
python3 transparencia.py comparar

# Solo contrata de un organismo
python3 transparencia.py comparar --org AJ011 --patron "*contrata*.csv"

# Guardar en otra ruta
python3 transparencia.py comparar --org AJ011 --patron "*contrata*.csv" \
  --salida datos/variaciones_grado_contrata.csv
```

Salida: `datos/variaciones_grado.csv` (o la ruta de `--salida`), con:

| Columna | Contenido |
|---|---|
| `nombre` | Nombre completo |
| `periodo_desde` / `grado_desde` | Último mes con el grado anterior |
| `periodo_hasta` / `grado_hasta` | Primer mes con el grado nuevo |
| `meses_entre` | Meses entre ambos registros |
| `cargo_desde` / `cargo_hasta` | Cargo en cada momento |
| `variacion` | Ejemplo: `15 -> 14` |

Detecta las columnas del botón (`Año`, `Mes`, `Nombre completo`,
`Grado EUS o jornada`) y las del CSV nacional (`anyo`, `Mes`,
`Nombres`/`Paterno`/`Materno`, `grado_eus`). Elimina duplicados entre el
archivo anual y los mensuales.

## Rankings

```bash
# Cargos con más cambios (cargo posterior al cambio)
python3 transparencia.py ranking cargos --por cargo_hasta

# Cargos por cargo anterior
python3 transparencia.py ranking cargos --por cargo_desde

# Personas con más cambios
python3 transparencia.py ranking personas --top 15
```

Cada comando genera un CSV y un Markdown con el top de `--top` (10 por
defecto):

```text
datos/ranking_cargos_cargo_hasta.csv
datos/ranking_cargos_cargo_hasta.md
datos/ranking_cargos_cargo_desde.csv
datos/ranking_cargos_cargo_desde.md
datos/ranking_personas.csv
datos/ranking_personas.md
```

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas no usan red: verifican lectura de columnas, descubrimiento del
formulario JSF, comparación, deduplicación y rankings.

## Limitaciones

- Los CSV no traen RUT. La identidad se arma con el nombre completo; dos
  homónimos podrían mezclarse.
- **No mezcles los dos métodos en la misma carpeta.** El botón entrega
  `Paterno, Nombres` y el CSV nacional entrega `Nombres Paterno Materno`, así
  que la misma persona se vería como dos. Usa `datos/` para el botón y, por
  ejemplo, `datos_nacional/` para el método nacional.
- No todos los organismos publican todos los tipos de dato; si no hay filas,
  el script lo informa y continúa.
- El portal puede estar en mantención. El botón reintenta 3 veces; si falla,
  usa `--metodo nacional`.
- La ficha es JSF. El formulario y el botón se descubren del HTML, pero si el
  portal cambia su estructura habrá que ajustar `descarga.py`.
- Los datos se publican con desfase: el mes recién pasado suele aparecer
  durante la primera quincena del mes siguiente.

## Fuente

- Datos abiertos: <https://opendata.portaltransparencia.cl/dataset/transparencia-activa-publicada-en-el-portal>
- Portal: <https://www.portaltransparencia.cl/PortalPdT/directorio-de-organismos-regulados/>
- Licencia: CC-BY, Consejo para la Transparencia.
