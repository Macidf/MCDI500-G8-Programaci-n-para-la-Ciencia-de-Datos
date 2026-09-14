"""
Funciones de diagnostico y exploracion del dataset.

Todas devuelven un `DataFrame` en lugar de imprimir: asi el mismo resultado sirve
para mostrarse en el notebook, exportarse como tabla del informe o compararse
antes y despues de una transformacion.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from ponds import rutas


def resumen_columnas(df: pd.DataFrame, n_ejemplos: int = 2) -> pd.DataFrame:
    """Resume tipo, nulos, cardinalidad y ejemplos de cada columna.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset a describir.
    n_ejemplos : int
        Cantidad de valores no nulos a mostrar como muestra.

    Returns
    -------
    pd.DataFrame
        Una fila por columna del dataset original.
    """
    filas = []
    for col in df.columns:
        s = df[col]
        no_nulos = s.dropna()
        filas.append(
            {
                "columna": col,
                "dtype": str(s.dtype),
                "n_nulos": int(s.isna().sum()),
                "pct_nulos": round(float(s.isna().mean() * 100), 3),
                "n_unicos": int(s.nunique(dropna=True)),
                "ejemplos": ", ".join(map(str, no_nulos.head(n_ejemplos).tolist())) or "-",
            }
        )
    return pd.DataFrame(filas)


def reporte_nulos(df: pd.DataFrame, solo_con_nulos: bool = True) -> pd.DataFrame:
    """Cuantifica los valores ausentes por columna, ordenados de mayor a menor."""
    rep = pd.DataFrame(
        {
            "n_nulos": df.isna().sum(),
            "pct_nulos": (df.isna().mean() * 100).round(3),
        }
    ).sort_values("n_nulos", ascending=False)
    rep.index.name = "columna"

    if solo_con_nulos:
        rep = rep[rep["n_nulos"] > 0]
    return rep.reset_index()


def reporte_duplicados(
    df: pd.DataFrame, claves: Optional[List[str]] = None
) -> pd.DataFrame:
    """Cuenta duplicados exactos y duplicados por clave de negocio.

    Se distinguen los dos casos porque tienen causas distintas: un duplicado
    exacto suele ser un fallo de exportacion, mientras que un duplicado por clave
    (mismo estanque y mismo instante, con valores distintos) indica un conflicto
    real de medicion que hay que resolver eligiendo un registro.

    Parameters
    ----------
    claves : list of str, optional
        Columnas que identifican univocamente una observacion.
    """
    filas = [
        {
            "criterio": "duplicados exactos (todas las columnas)",
            "n_filas": int(df.duplicated().sum()),
            "pct": round(float(df.duplicated().mean() * 100), 4),
        }
    ]
    if claves:
        presentes = [c for c in claves if c in df.columns]
        if presentes:
            filas.append(
                {
                    "criterio": f"duplicados por clave {tuple(presentes)}",
                    "n_filas": int(df.duplicated(subset=presentes).sum()),
                    "pct": round(float(df.duplicated(subset=presentes).mean() * 100), 4),
                }
            )
    return pd.DataFrame(filas)


def valores_no_convertibles(
    df: pd.DataFrame, columnas: Iterable[str]
) -> pd.DataFrame:
    """Detecta celdas que impiden convertir una columna de texto a numero.

    Es el diagnostico clave de este dataset: el CSV proviene de una hoja de
    calculo y arrastra errores de formula (`#VALUE!`) y la cadena literal `'NaN'`.
    Esta funcion los cuenta ANTES de castear, de modo que la conversion posterior
    sea una decision documentada y no una perdida silenciosa de datos.

    Returns
    -------
    pd.DataFrame
        Columnas afectadas, cantidad de celdas problematicas y los valores
        literales encontrados.
    """
    filas = []
    for col in columnas:
        if col not in df.columns:
            continue
        s = df[col]
        convertido = pd.to_numeric(s, errors="coerce")
        # Problematica = no se pudo convertir PERO no estaba vacia.
        mask = convertido.isna() & s.notna()
        problematicos = s[mask]
        filas.append(
            {
                "columna": col,
                "n_no_convertibles": int(mask.sum()),
                "valores_encontrados": (
                    ", ".join(f"{v!r} x{n}" for v, n in problematicos.value_counts().items())
                    or "-"
                ),
            }
        )
    return pd.DataFrame(filas)


def estadisticos(
    df: pd.DataFrame, columnas: Optional[List[str]] = None
) -> pd.DataFrame:
    """Estadisticos descriptivos ampliados de las variables numericas.

    Agrega a `describe()` la asimetria y la curtosis, que permiten anticipar si
    una variable necesitara un criterio robusto de deteccion de atipicos en lugar
    de uno basado en media y desviacion estandar.
    """
    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    sub = df[columnas]

    base = sub.describe().T
    base["asimetria"] = sub.skew()
    base["curtosis"] = sub.kurtosis()
    base["n_nulos"] = sub.isna().sum()
    base["unidad"] = [rutas.UNIDADES.get(c, "-") for c in base.index]
    base.index.name = "variable"
    return base.round(4).reset_index()


def fuera_de_rango(
    df: pd.DataFrame,
    rangos: Dict[str, tuple],
    etiqueta: str = "rango",
) -> pd.DataFrame:
    """Cuenta cuantos valores caen fuera de los rangos indicados, por variable.

    Se usa dos veces con semanticas distintas (ver `rutas.RANGOS_FISICOS` y
    `rutas.RANGOS_OPERACIONALES`): la primera identifica fallos de instrumento a
    corregir; la segunda identifica eventos de mala calidad de agua a conservar.
    """
    filas = []
    for col, (lo, hi) in rangos.items():
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        bajo = int((s < lo).sum())
        alto = int((s > hi).sum())
        filas.append(
            {
                "variable": col,
                f"{etiqueta}_min": lo,
                f"{etiqueta}_max": hi,
                "n_bajo_minimo": bajo,
                "n_sobre_maximo": alto,
                "n_total_fuera": bajo + alto,
                "pct_fuera": round((bajo + alto) / max(len(s), 1) * 100, 3),
            }
        )
    return pd.DataFrame(filas)


def atipicos_iqr(
    df: pd.DataFrame, columnas: Optional[List[str]] = None, factor: float = 3.0
) -> pd.DataFrame:
    """Cuenta atipicos por el criterio del rango intercuartilico.

    Se usa IQR y no z-score porque el IQR se apoya en cuantiles, que no se ven
    arrastrados por los propios valores extremos que se intenta detectar. El
    factor por defecto es 3.0 (y no el habitual 1.5) porque en series ambientales
    la variabilidad natural es alta y 1.5 marcaria como atipica una fraccion
    excesiva de observaciones legitimas.

    Nota: esta funcion DIAGNOSTICA, no modifica. La decision de que hacer con los
    atipicos se toma explicitamente en `limpieza.PipelineLimpieza`.
    """
    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    filas = []
    for col in columnas:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - factor * iqr, q3 + factor * iqr
        n = int(((s < lo) | (s > hi)).sum())
        filas.append(
            {
                "variable": col,
                "Q1": round(float(q1), 4),
                "Q3": round(float(q3), 4),
                "IQR": round(float(iqr), 4),
                "limite_inferior": round(float(lo), 4),
                "limite_superior": round(float(hi), 4),
                "n_atipicos": n,
                "pct_atipicos": round(n / len(s) * 100, 3),
            }
        )
    return pd.DataFrame(filas)


def comparar_antes_despues(
    antes: pd.DataFrame, despues: pd.DataFrame, etapa: str
) -> pd.DataFrame:
    """Compara dos estados del dataset para evidenciar el efecto de una etapa.

    Es la unidad de evidencia del pipeline: cada transformacion documenta cuantas
    filas y cuantos nulos habia antes y despues, de modo que el efecto sea
    verificable y no una afirmacion del texto.
    """
    return pd.DataFrame(
        [
            {
                "etapa": etapa,
                "filas_antes": len(antes),
                "filas_despues": len(despues),
                "delta_filas": len(despues) - len(antes),
                "nulos_antes": int(antes.isna().sum().sum()),
                "nulos_despues": int(despues.isna().sum().sum()),
                "columnas_antes": antes.shape[1],
                "columnas_despues": despues.shape[1],
            }
        ]
    )
