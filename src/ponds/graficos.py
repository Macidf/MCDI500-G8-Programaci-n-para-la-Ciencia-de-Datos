"""
Figuras con estilo homogeneo para la exploracion y el informe.

Todas las funciones guardan en `docs/figuras/` y devuelven la ruta escrita, de
modo que el informe pueda insertar exactamente las mismas imagenes que el
notebook muestra, sin capturas de pantalla manuales.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from ponds import rutas

# Paleta cualitativa estable: cada estanque conserva su color en todas las
# figuras del informe, de modo que el lector no tenga que releer la leyenda.
PALETA_ESTANQUES: dict = {
    "station1": "#2E7DB8",
    "station2": "#E08A1E",
    "station3": "#3E9B72",
}
COLOR_PRINCIPAL = "#2E7DB8"
COLOR_ALERTA = "#C4453C"


def _color_estanque(grupo: object) -> str:
    """Color de un estanque, sin depender de la capitalizacion del identificador.

    Los graficos de exploracion se dibujan sobre el dataset crudo, donde conviven
    `station1` y `Station2`; la busqueda en minusculas evita que un mismo estanque
    cambie de color (o haga fallar seaborn) segun como venga escrito.
    """
    return PALETA_ESTANQUES.get(str(grupo).strip().lower(), "#7F7F7F")


def _paleta(valores) -> dict:
    """Paleta para seaborn con una entrada por cada valor presente en los datos."""
    return {v: _color_estanque(v) for v in pd.Series(valores).dropna().unique()}


def aplicar_estilo() -> None:
    """Fija un estilo unico para todas las figuras del proyecto."""
    sns.set_theme(style="whitegrid", context="notebook")
    matplotlib.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
            "figure.facecolor": "white",
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.edgecolor": "#4A4A4A",
            "grid.alpha": 0.3,
            "legend.frameon": False,
            "font.size": 9,
        }
    )


def _guardar(fig: plt.Figure, nombre: str) -> Path:
    """Guarda la figura en `docs/figuras/` y devuelve su ruta."""
    rutas.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    destino = rutas.DIR_FIGURAS / f"{nombre}.png"
    fig.savefig(destino)
    return destino


# ---------------------------------------------------------------------------
# Exploracion
# ---------------------------------------------------------------------------
def mapa_nulos(df: pd.DataFrame, columnas: Optional[List[str]] = None,
               nombre: str = "f01_mapa_nulos") -> Path:
    """Dibuja el porcentaje de valores ausentes por columna."""
    columnas = columnas or list(df.columns)
    pct = (df[columnas].isna().mean() * 100).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(8, max(3, 0.32 * len(pct))))
    colores = [COLOR_ALERTA if v > 0 else "#C8D4DC" for v in pct]
    ax.barh(pct.index, pct.values, color=colores)
    ax.set_xlabel("Valores ausentes (%)")
    ax.set_title("Valores ausentes por columna (dataset crudo)")

    for y, v in enumerate(pct.values):
        if v > 0:
            ax.text(v, y, f"  {v:.3f}%", va="center", fontsize=8)

    fig.tight_layout()
    ruta = _guardar(fig, nombre)
    plt.close(fig)
    return ruta


def distribuciones(df: pd.DataFrame, columnas: Optional[List[str]] = None,
                   nombre: str = "f02_distribuciones") -> Path:
    """Histograma con curva de densidad para cada variable medida."""
    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    n = len(columnas)
    filas = int(np.ceil(n / 3))

    fig, axes = plt.subplots(filas, 3, figsize=(13, 3.1 * filas))
    axes = np.atleast_1d(axes).ravel()

    for ax, col in zip(axes, columnas):
        sns.histplot(df[col].dropna(), bins=60, kde=True, ax=ax,
                     color=COLOR_PRINCIPAL, edgecolor=None)
        ax.set_title(f"{col} ({rutas.UNIDADES.get(col, '-')})")
        ax.set_xlabel("")
        ax.set_ylabel("Frecuencia")

    for ax in axes[n:]:
        ax.set_visible(False)

    fig.suptitle("Distribucion de las variables de calidad del agua", y=1.0, fontsize=13, fontweight="bold")
    fig.tight_layout()
    ruta = _guardar(fig, nombre)
    plt.close(fig)
    return ruta


def cajas_por_estanque(df: pd.DataFrame, columnas: Optional[List[str]] = None,
                       nombre: str = "f03_cajas_estanque") -> Path:
    """Diagrama de caja de cada variable, separado por estanque."""
    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    n = len(columnas)
    filas = int(np.ceil(n / 3))

    fig, axes = plt.subplots(filas, 3, figsize=(13, 3.3 * filas))
    axes = np.atleast_1d(axes).ravel()

    for ax, col in zip(axes, columnas):
        sns.boxplot(data=df, x="estanque", y=col, ax=ax, hue="estanque",
                    palette=_paleta(df["estanque"]), legend=False, fliersize=1.2)
        ax.set_title(f"{col} ({rutas.UNIDADES.get(col, '-')})")
        ax.set_xlabel("")

    for ax in axes[n:]:
        ax.set_visible(False)

    fig.suptitle("Dispersion por estanque", y=1.0, fontsize=13, fontweight="bold")
    fig.tight_layout()
    ruta = _guardar(fig, nombre)
    plt.close(fig)
    return ruta


def serie_temporal(df: pd.DataFrame, variable: str, col_ts: str = "timestamp",
                   col_grupo: str = "estanque", periodo: str = "D",
                   nombre: Optional[str] = None) -> Path:
    """Serie temporal de una variable, agregada y separada por estanque.

    Se agrega antes de graficar: a la cadencia original de 20 minutos, un ano de
    datos son ~75.000 puntos y la linea se convierte en una mancha sin tendencia
    legible.
    """
    nombre = nombre or f"f04_serie_{variable}"
    agregado = (
        df.dropna(subset=[col_ts])
        .set_index(col_ts)
        .groupby(col_grupo, observed=True)[variable]
        .resample(periodo)
        .mean()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(13, 4.2))
    for grupo, g in agregado.groupby(col_grupo, observed=True):
        ax.plot(g[col_ts], g[variable], label=str(grupo), linewidth=1.1,
                color=_color_estanque(grupo))

    if variable in rutas.RANGOS_OPERACIONALES:
        lo, hi = rutas.RANGOS_OPERACIONALES[variable]
        ax.axhspan(lo, hi, color="#3E9B72", alpha=0.08)
        ax.axhline(lo, color=COLOR_ALERTA, linestyle="--", linewidth=0.9, alpha=0.6)
        ax.axhline(hi, color=COLOR_ALERTA, linestyle="--", linewidth=0.9, alpha=0.6,
                   label="Limites operacionales")

    ax.set_title(f"Evolucion temporal de {variable} (media {periodo})")
    ax.set_xlabel("Fecha")
    ax.set_ylabel(f"{variable} ({rutas.UNIDADES.get(variable, '-')})")
    ax.legend(title="Estanque", ncol=4)
    fig.tight_layout()
    ruta = _guardar(fig, nombre)
    plt.close(fig)
    return ruta


def cobertura_registro(cobertura: pd.DataFrame,
                       nombre: str = "f05_cobertura") -> Path:
    """Compara lecturas observadas y esperadas por estanque."""
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(cobertura))
    ancho = 0.38

    ax.bar(x - ancho / 2, cobertura["lecturas_esperadas"], ancho,
           label="Esperadas (cadencia nominal)", color="#C8D4DC")
    ax.bar(x + ancho / 2, cobertura["lecturas_observadas"], ancho,
           label="Observadas", color=COLOR_PRINCIPAL)

    for i, fila in cobertura.iterrows():
        ax.text(i, max(fila["lecturas_esperadas"], fila["lecturas_observadas"]) * 1.02,
                f"{fila['cobertura_pct']:.1f}%", ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(cobertura["estanque"])
    ax.set_ylabel("Numero de lecturas")
    ax.set_title("Cobertura real del registro frente a la cadencia nominal")
    ax.legend()
    fig.tight_layout()
    ruta = _guardar(fig, nombre)
    plt.close(fig)
    return ruta
