"""
Contratos de calidad del dataset resultante.

Un contrato es una condicion que el dataset procesado debe cumplir para que las
fases siguientes puedan confiar en el. La clase `ValidadorDataset` los evalua
todos y devuelve un informe tabulado en lugar de detenerse en el primer fallo:
saber que fallan tres contratos y cuales es mas util que saber que fallo uno.

El metodo `assert_valido()` sirve para el uso opuesto -- detener la ejecucion --
y es el que se invoca antes de exportar el dataset final.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from ponds import rutas


class ErrorValidacion(Exception):
    """Se lanza cuando el dataset no cumple uno o mas contratos de calidad."""


class ValidadorDataset:
    """Evalua los contratos de calidad sobre un dataset procesado.

    Uso tipico
    ----------
    >>> v = ValidadorDataset(df_limpio)
    >>> informe = v.validar()
    >>> v.aprobado()
    True

    Parameters
    ----------
    df : pd.DataFrame
        Dataset a validar.
    columnas_requeridas : list of str, optional
        Columnas que deben existir. Por defecto, identificacion + variables.
    rangos : dict, optional
        Rangos fisicos admisibles. Por defecto `rutas.RANGOS_FISICOS`.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        columnas_requeridas: Optional[List[str]] = None,
        rangos: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> None:
        self.df = df
        self.rangos = rangos or rutas.RANGOS_FISICOS
        self.columnas_requeridas = columnas_requeridas or (
            ["timestamp", "estanque"] + list(rutas.VARIABLES)
        )
        self._resultados: List[Dict[str, object]] = []

    # ------------------------------------------------------------------
    def _anotar(self, contrato: str, ok: bool, detalle: str) -> bool:
        self._resultados.append(
            {
                "contrato": contrato,
                "resultado": "OK" if ok else "FALLA",
                "detalle": detalle,
            }
        )
        return ok

    # ------------------------------------------------------------------
    # Contratos individuales
    # ------------------------------------------------------------------
    def c01_no_vacio(self) -> bool:
        """El dataset debe contener al menos una fila."""
        ok = len(self.df) > 0
        return self._anotar("C01 - Dataset no vacio", ok, f"{len(self.df)} filas")

    def c02_columnas_presentes(self) -> bool:
        """Deben existir todas las columnas del esquema acordado."""
        faltantes = [c for c in self.columnas_requeridas if c not in self.df.columns]
        return self._anotar(
            "C02 - Esquema completo",
            not faltantes,
            "todas presentes" if not faltantes else f"faltan: {faltantes}",
        )

    def c03_tipos_correctos(self) -> bool:
        """`timestamp` debe ser datetime y las variables, numericas."""
        problemas = []

        if "timestamp" in self.df.columns:
            if not pd.api.types.is_datetime64_any_dtype(self.df["timestamp"]):
                problemas.append(f"timestamp es {self.df['timestamp'].dtype}, no datetime")

        for col in rutas.VARIABLES:
            if col in self.df.columns and not pd.api.types.is_numeric_dtype(self.df[col]):
                problemas.append(f"{col} es {self.df[col].dtype}, no numerico")

        return self._anotar(
            "C03 - Tipos de dato correctos",
            not problemas,
            "correctos" if not problemas else "; ".join(problemas),
        )

    def c04_sin_timestamp_nulo(self) -> bool:
        """Ninguna observacion puede carecer de instante."""
        if "timestamp" not in self.df.columns:
            return self._anotar("C04 - Timestamp sin nulos", False, "columna ausente")
        n = int(self.df["timestamp"].isna().sum())
        return self._anotar("C04 - Timestamp sin nulos", n == 0, f"{n} nulos")

    def c05_clave_unica(self) -> bool:
        """El par (estanque, timestamp) debe identificar una unica observacion."""
        claves = [c for c in ("estanque", "timestamp") if c in self.df.columns]
        if len(claves) < 2:
            return self._anotar("C05 - Clave (estanque, timestamp) unica", False, "columnas ausentes")
        n = int(self.df.duplicated(subset=claves).sum())
        return self._anotar("C05 - Clave (estanque, timestamp) unica", n == 0, f"{n} duplicados")

    def c06_orden_temporal(self) -> bool:
        """Dentro de cada estanque, el tiempo debe avanzar de forma monotona."""
        if not {"estanque", "timestamp"}.issubset(self.df.columns):
            return self._anotar("C06 - Orden temporal monotono", False, "columnas ausentes")

        desordenados = [
            str(g)
            for g, sub in self.df.groupby("estanque", observed=True)
            if not sub["timestamp"].is_monotonic_increasing
        ]
        return self._anotar(
            "C06 - Orden temporal monotono",
            not desordenados,
            "todas las series ordenadas" if not desordenados else f"desordenadas: {desordenados}",
        )

    def c07_rangos_fisicos(self) -> bool:
        """Ningun valor puede estar fuera del rango medible del instrumento."""
        problemas = []
        for col, (lo, hi) in self.rangos.items():
            if col not in self.df.columns:
                continue
            s = self.df[col]
            n = int(((s < lo) | (s > hi)).sum())
            if n:
                problemas.append(f"{col}: {n} fuera de [{lo}, {hi}]")
        return self._anotar(
            "C07 - Valores dentro del rango fisico",
            not problemas,
            "todos dentro de rango" if not problemas else "; ".join(problemas),
        )

    def c08_estanques_esperados(self, esperados: int = 3) -> bool:
        """Deben conservarse los tres estanques del estudio original."""
        if "estanque" not in self.df.columns:
            return self._anotar("C08 - Estanques presentes", False, "columna ausente")
        valores = sorted(map(str, self.df["estanque"].dropna().unique()))
        return self._anotar(
            "C08 - Estanques presentes",
            len(valores) == esperados,
            f"{len(valores)}: {valores}",
        )

    def c09_nulos_controlados(self, umbral_pct: float = 5.0) -> bool:
        """Los nulos residuales deben mantenerse por debajo de un umbral.

        No se exige cero: los huecos largos se conservan deliberadamente como
        nulos (ver `limpieza.tratar_nulos`). Lo que se verifica es que esa
        conservacion sea marginal y no afecte a una porcion relevante del dataset.
        """
        cols = [c for c in rutas.VARIABLES if c in self.df.columns]
        if not cols:
            return self._anotar("C09 - Nulos residuales controlados", False, "sin variables")

        pct = float(self.df[cols].isna().mean().mean() * 100)
        return self._anotar(
            "C09 - Nulos residuales controlados",
            pct <= umbral_pct,
            f"{pct:.3f}% promedio (umbral {umbral_pct}%)",
        )

    def c10_cobertura_temporal(self) -> bool:
        """El rango cubierto debe corresponder al periodo declarado por la fuente."""
        if "timestamp" not in self.df.columns or self.df["timestamp"].isna().all():
            return self._anotar("C10 - Cobertura temporal esperada", False, "sin timestamps")

        ini, fin = self.df["timestamp"].min(), self.df["timestamp"].max()
        ok = ini.year == 2022 and fin.year in (2022, 2023)
        return self._anotar(
            "C10 - Cobertura temporal esperada",
            ok,
            f"{ini:%Y-%m-%d} a {fin:%Y-%m-%d}",
        )



    # ------------------------------------------------------------------
    # Ejecucion
    # ------------------------------------------------------------------
    def validar(self) -> pd.DataFrame:
        """Evalua todos los contratos y devuelve el informe completo.

        No se detiene ante el primer fallo: ejecuta los diez contratos para que el
        diagnostico sea completo en una sola pasada.
        """
        self._resultados = []

        contratos: List[Callable[[], bool]] = [
            self.c01_no_vacio,
            self.c02_columnas_presentes,
            self.c03_tipos_correctos,
            self.c04_sin_timestamp_nulo,
            self.c05_clave_unica,
            self.c06_orden_temporal,
            self.c07_rangos_fisicos,
            self.c08_estanques_esperados,
            self.c09_nulos_controlados,
            self.c10_cobertura_temporal,
        ]

        for contrato in contratos:
            try:
                contrato()
            except Exception as exc:  # noqa: BLE001 - se reporta, no se propaga
                self._anotar(
                    contrato.__name__,
                    False,
                    f"excepcion no prevista: {type(exc).__name__}: {exc}",
                )

        return pd.DataFrame(self._resultados)

    def aprobado(self) -> bool:
        """Indica si todos los contratos evaluados resultaron OK."""
        if not self._resultados:
            self.validar()
        return all(r["resultado"] == "OK" for r in self._resultados)

    def fallidos(self) -> pd.DataFrame:
        """Devuelve solo los contratos que no se cumplieron."""
        informe = pd.DataFrame(self._resultados) if self._resultados else self.validar()
        return informe[informe["resultado"] == "FALLA"].reset_index(drop=True)

    def assert_valido(self) -> None:
        """Lanza `ErrorValidacion` si algun contrato falla.

        Es la puerta de salida del pipeline: se invoca antes de exportar para que
        un dataset defectuoso nunca llegue a `data/processed/`.
        """
        if not self.aprobado():
            fallas = self.fallidos()
            detalle = "\n".join(
                f"  - {r.contrato}: {r.detalle}" for r in fallas.itertuples()
            )
            raise ErrorValidacion(
                f"El dataset no supero {len(fallas)} contrato(s) de calidad:\n{detalle}"
            )
