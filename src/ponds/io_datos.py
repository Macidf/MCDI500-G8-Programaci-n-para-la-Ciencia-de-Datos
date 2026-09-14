"""
Ingesta trazable del dataset y escritura de los resultados.

Trazabilidad: toda carga registra el SHA-256 del archivo leido. Ese hash es la
prueba de que el analisis se ejecuto sobre exactamente el mismo archivo en
cualquier equipo; si alguien reemplaza el CSV, el hash cambia y la discrepancia
queda a la vista en lugar de pasar inadvertida.
"""

from __future__ import annotations

import hashlib
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ponds import rutas


# ---------------------------------------------------------------------------
# Trazabilidad del archivo fuente
# ---------------------------------------------------------------------------
def calcular_sha256(ruta: Path, tam_bloque: int = 1 << 20) -> str:
    """Devuelve el SHA-256 de un archivo leyendolo por bloques.

    Se lee en bloques de 1 MiB en lugar de cargar el archivo completo en memoria,
    de modo que la funcion sirve igual para un CSV de 6 MB que para uno de varios GB.

    Parameters
    ----------
    ruta : Path
        Archivo a resumir.
    tam_bloque : int, optional
        Tamano del bloque de lectura en bytes.

    Returns
    -------
    str
        Hash hexadecimal en minusculas.
    """
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(tam_bloque), b""):
            h.update(bloque)
    return h.hexdigest()


def descomprimir_si_existe(
    ruta_zip: Path, destino: Optional[Path] = None
) -> List[Path]:
    """Extrae un ZIP de Kaggle si esta presente y devuelve los CSV resultantes.

    Es idempotente: volver a ejecutarla sobre un ZIP ya extraido simplemente
    sobrescribe los mismos archivos.

    Parameters
    ----------
    ruta_zip : Path
        Ruta al archivo comprimido descargado desde Kaggle.
    destino : Path, optional
        Carpeta de extraccion. Por defecto `data/raw/`.

    Returns
    -------
    list of Path
        CSV disponibles en la carpeta de destino tras la extraccion.
    """
    destino = destino or rutas.DIR_CRUDO
    destino.mkdir(parents=True, exist_ok=True)

    if ruta_zip.exists():
        with zipfile.ZipFile(ruta_zip) as z:
            z.extractall(destino)

    return sorted(destino.glob("*.csv"))


def describir_fuente(ruta: Path) -> Dict[str, object]:
    """Construye el registro de procedencia de un archivo de datos."""
    return {
        "archivo": ruta.name,
        "ruta_relativa": str(ruta.relative_to(rutas.RAIZ)),
        "tamano_mb": round(ruta.stat().st_size / 1e6, 3),
        "sha256": calcular_sha256(ruta),
        "leido_el": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Carga del dataset crudo
# ---------------------------------------------------------------------------
def cargar_crudo(
    nombre_archivo: str = rutas.ARCHIVO_CRUDO,
    directorio: Optional[Path] = None,
) -> pd.DataFrame:
    """Carga el CSV crudo SIN conversiones de tipo ni limpieza implicita.

    Dos decisiones deliberadas:

    1. `dtype=str` -- todas las columnas se leen como texto. Si se dejara que
       pandas infiriera los tipos, las columnas contaminadas quedarian como
       `object` de forma silenciosa y el problema solo apareceria mas tarde, en
       medio de un calculo.
    2. `keep_default_na=False` con `na_values=[""]` -- solo la celda literalmente
       vacia se considera ausente. Los centinelas del archivo (el error de Excel
       `#VALUE!` y la cadena literal `'NaN'`) se conservan **tal como estan** para
       que la etapa de exploracion pueda contarlos y mostrarlos como evidencia.
       Neutralizarlos aqui haria que el dataset pareciera mas limpio de lo que es
       y dejaria sin justificacion la etapa correspondiente del pipeline.

    La conversion se hace despues, de forma explicita y cuantificada, en
    `limpieza.PipelineLimpieza`.

    Parameters
    ----------
    nombre_archivo : str
        Nombre del CSV dentro del directorio de datos crudos.
    directorio : Path, optional
        Directorio de busqueda. Por defecto `data/raw/`.

    Returns
    -------
    pd.DataFrame
        Dataset crudo, todas las columnas de tipo object.

    Raises
    ------
    FileNotFoundError
        Si el archivo no existe, con instrucciones de descarga.
    """
    directorio = directorio or rutas.DIR_CRUDO
    ruta = directorio / nombre_archivo

    if not ruta.exists():
        disponibles = [p.name for p in directorio.glob("*.csv")]
        raise FileNotFoundError(
            f"No se encontro '{nombre_archivo}' en {directorio}.\n"
            f"Descargue el dataset desde {rutas.FUENTE_DATOS['url']} y "
            f"descomprima el ZIP en data/raw/.\n"
            f"CSV disponibles actualmente: {disponibles or 'ninguno'}"
        )

    return pd.read_csv(
        ruta,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        encoding="utf-8",
    )


def registrar_procedencia(
    nombre_archivo: str = rutas.ARCHIVO_CRUDO,
    directorio: Optional[Path] = None,
) -> Path:
    """Escribe `data/raw/README_DATOS.md` con la procedencia de los datos.

    Este archivo es la evidencia de trazabilidad exigida por la Fase 2: deja
    constancia de origen, licencia, fecha de descarga y hash de cada CSV, de modo
    que el repositorio documenta los datos aunque estos no se versionen.

    Returns
    -------
    Path
        Ruta del archivo escrito.
    """
    directorio = directorio or rutas.DIR_CRUDO
    csvs = sorted(directorio.glob("*.csv"))

    filas = [
        "| Archivo | Tamano (MB) | SHA-256 |",
        "|---|---|---|",
    ]
    for c in csvs:
        info = describir_fuente(c)
        marca = " **(fuente primaria)**" if c.name == nombre_archivo else ""
        filas.append(f"| `{info['archivo']}`{marca} | {info['tamano_mb']} | `{info['sha256']}` |")

    contenido = f"""# Procedencia de los datos

> Generado automaticamente por `ponds.io_datos.registrar_procedencia()`.
> Ultima actualizacion: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Fuente

| Campo | Valor |
|---|---|
| Nombre | {rutas.FUENTE_DATOS['nombre']} |
| Autor | {rutas.FUENTE_DATOS['autor']} |
| URL | {rutas.FUENTE_DATOS['url']} |
| Cobertura temporal | {rutas.FUENTE_DATOS['cobertura']} |
| Ubicacion | {rutas.FUENTE_DATOS['ubicacion']} |

{rutas.FUENTE_DATOS['descripcion']}

## Archivos verificados

{chr(10).join(filas)}

## Por que los datos crudos no se versionan

`data/raw/` esta excluido en `.gitignore`. Un repositorio academico no debe
redistribuir un dataset de terceros: la licencia pertenece al autor original en
Kaggle. En su lugar se versiona este registro, que permite a cualquier integrante
descargar el mismo archivo y **comprobar con el hash** que es identico al usado
en el analisis.

## Como reponer los datos

1. Descargar el ZIP desde {rutas.FUENTE_DATOS['url']}
2. Descomprimirlo dentro de `data/raw/`
3. Ejecutar los notebooks de `F2/` en orden numerico

El archivo `{nombre_archivo}` es la fuente primaria del analisis. La justificacion
de esa eleccion frente a los otros CSV del ZIP esta en `docs/decisiones.md` (D-02).
"""
    salida = directorio / "README_DATOS.md"
    salida.write_text(contenido, encoding="utf-8")
    return salida


# ---------------------------------------------------------------------------
# Escritura de resultados
# ---------------------------------------------------------------------------
def guardar_procesado(
    df: pd.DataFrame,
    nombre_csv: str = rutas.ARCHIVO_PROCESADO,
) -> Path:
    """Guarda el dataset final en CSV (UTF-8, sin indice).

    Se usa CSV porque es legible por cualquier herramienta y no agrega
    dependencias al entorno. Su limitacion es que no conserva los tipos de dato;
    por eso la recarga se hace siempre con `cargar_procesado`, que los restituye
    de forma explicita.

    Returns
    -------
    Path
        Ruta del archivo escrito.
    """
    rutas.DIR_PROCESADO.mkdir(parents=True, exist_ok=True)
    ruta = rutas.DIR_PROCESADO / nombre_csv
    df.to_csv(ruta, index=False, encoding="utf-8")
    return ruta


def cargar_procesado(nombre_csv: str = rutas.ARCHIVO_PROCESADO) -> pd.DataFrame:
    """Recarga el dataset procesado restituyendo los tipos de dato.

    El CSV guarda todo como texto, asi que aqui se vuelven a declarar los tipos
    que el pipeline dejo establecidos: marca temporal, categorias y enteros
    anulables. Sin este paso, la validacion de tipos fallaria sobre un dataset
    que en realidad es correcto.
    """
    ruta = rutas.DIR_PROCESADO / nombre_csv
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecute antes F2/F2_02_Limpieza_Transformacion.ipynb."
        )

    df = pd.read_csv(ruta, parse_dates=["timestamp"], encoding="utf-8")

    for col in ("estanque", "estacion_anio", "franja_horaria"):
        if col in df.columns:
            df[col] = df[col].astype("category")
    enteros = {
        "anio": "Int16", "mes": "Int8", "dia": "Int8", "hora": "Int8",
        "minuto": "Int8", "dia_semana": "Int8", "etiqueta_calidad": "Int8",
    }
    for col, tipo in enteros.items():
        if col in df.columns:
            df[col] = df[col].astype(tipo)
    if "anio_mes" in df.columns:
        df["anio_mes"] = df["anio_mes"].astype("string")
    if "fila_imputada" in df.columns:
        df["fila_imputada"] = df["fila_imputada"].astype(bool)

    return df
