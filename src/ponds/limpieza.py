"""
Pipeline de depuracion y transformacion del dataset.

Se implementa como una clase (`PipelineLimpieza`) y no como una funcion suelta
por tres razones concretas:

1. **Orden garantizado.** Las etapas no son conmutativas: no se puede eliminar
   duplicados por marca temporal antes de haber construido la marca temporal, ni
   detectar fallos de sensor antes de castear a numerico. La clase fija el orden.
2. **Trazabilidad.** Cada etapa registra su efecto (filas y nulos antes/despues)
   en una bitacora interna, que se consulta al final con `bitacora()`. El informe
   no afirma que la limpieza funciono: lo demuestra con esa tabla.
3. **Estado compartido.** Varias etapas necesitan saber que hizo la anterior
   (por ejemplo, cuantos valores se anularon por fallo de instrumento para no
   contarlos luego como huecos de registro).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ponds import rutas, temporal


class PipelineLimpieza:
    """Ejecuta y documenta la depuracion del dataset crudo.

    Uso tipico
    ----------
    >>> pipe = PipelineLimpieza(df_crudo)
    >>> df_limpio = pipe.ejecutar()
    >>> pipe.bitacora()

    Tambien puede ejecutarse etapa por etapa desde el notebook para mostrar el
    efecto individual de cada una.

    Attributes
    ----------
    df : pd.DataFrame
        Estado actual del dataset a medida que avanza el pipeline.
    """

    def __init__(self, df: pd.DataFrame, verboso: bool = True) -> None:
        self.df_original: pd.DataFrame = df.copy()
        self.df: pd.DataFrame = df.copy()
        self.verboso: bool = verboso
        self._bitacora: List[Dict[str, object]] = []

    # ------------------------------------------------------------------
    # Infraestructura de registro
    # ------------------------------------------------------------------
    def _registrar(self, etapa: str, antes: pd.DataFrame, detalle: str = "") -> None:
        """Anota el efecto de una etapa en la bitacora interna."""
        entrada = {
            "n": len(self._bitacora) + 1,
            "etapa": etapa,
            "filas_antes": len(antes),
            "filas_despues": len(self.df),
            "delta_filas": len(self.df) - len(antes),
            "nulos_antes": int(antes.isna().sum().sum()),
            "nulos_despues": int(self.df.isna().sum().sum()),
            "detalle": detalle,
        }
        self._bitacora.append(entrada)
        if self.verboso:
            print(
                f"[{entrada['n']:>2}] {etapa:<42} "
                f"filas {entrada['filas_antes']:>6} -> {entrada['filas_despues']:>6} "
                f"({entrada['delta_filas']:+d}) | nulos {entrada['nulos_antes']:>5} -> "
                f"{entrada['nulos_despues']:>5}"
                + (f" | {detalle}" if detalle else "")
            )

    def bitacora(self) -> pd.DataFrame:
        """Devuelve la bitacora de ejecucion como tabla."""
        return pd.DataFrame(self._bitacora)

    # ------------------------------------------------------------------
    # Etapa 1 - Estandarizacion de nombres
    # ------------------------------------------------------------------
    def normalizar_nombres(self) -> "PipelineLimpieza":
        """Renombra las columnas a snake_case en espanol.

        Los nombres originales mezclan mayusculas, unidades y caracteres
        especiales (`NITRATE(PPM)`, `AMMONIA(mg/l)`). Normalizarlos permite el
        acceso por atributo y elimina una fuente habitual de errores de tipeo;
        las unidades no se pierden, quedan documentadas en `rutas.UNIDADES`.
        """
        antes = self.df.copy()
        self.df = self.df.rename(columns=rutas.RENOMBRE_COLUMNAS)
        renombradas = sum(1 for c in rutas.RENOMBRE_COLUMNAS if c in antes.columns)
        self._registrar("Normalizar nombres de columnas", antes, f"{renombradas} columnas renombradas")
        return self

    # ------------------------------------------------------------------
    # Etapa 2 - Centinelas de nulo
    # ------------------------------------------------------------------
    def normalizar_centinelas(
        self, centinelas: Optional[List[str]] = None
    ) -> "PipelineLimpieza":
        """Convierte en nulo real las cadenas que representan ausencia de dato.

        El CSV proviene de una hoja de calculo y arrastra dos codificaciones
        distintas del mismo concepto: `#VALUE!` (error de formula de Excel) y la
        cadena literal `'NaN'`, que quedo escrita como texto y que pandas no
        reconoce como valor ausente. Ambas se unifican aqui en `NaN`.

        Hacerlo en una etapa propia -- y no en la lectura del archivo -- permite
        cuantificar exactamente cuantos valores estaban enmascarados, que es la
        evidencia de que la etapa era necesaria.
        """
        centinelas = centinelas or rutas.CENTINELAS_NULOS
        antes = self.df.copy()

        conteo: Dict[str, int] = {}
        for cent in centinelas:
            if cent.strip() == "":
                continue
            n = int((self.df == cent).sum().sum())
            if n:
                conteo[cent] = n

        self.df = self.df.replace(centinelas, np.nan)

        detalle = ", ".join(f"{k!r} x{v}" for k, v in conteo.items()) or "ninguno encontrado"
        self._registrar("Unificar centinelas de nulo", antes, detalle)
        return self

    # ------------------------------------------------------------------
    # Etapa 3 - Filas sin contenido
    # ------------------------------------------------------------------
    def eliminar_filas_vacias(self) -> "PipelineLimpieza":
        """Elimina las filas en las que todas las columnas son nulas.

        Son artefactos de la exportacion desde hoja de calculo: no aportan
        informacion y, si se conservan, contaminan todo conteo de nulos posterior
        haciendo parecer que cada variable tiene datos faltantes cuando en realidad
        se trata de las mismas filas fantasma repetidas.
        """
        antes = self.df.copy()
        mask_vacias = self.df.isna().all(axis=1)
        self.df = self.df[~mask_vacias].reset_index(drop=True)
        self._registrar("Eliminar filas completamente vacias", antes, f"{int(mask_vacias.sum())} filas fantasma")
        return self

    # ------------------------------------------------------------------
    # Etapa 4 - Identificador de estanque
    # ------------------------------------------------------------------
    def normalizar_estanque(self, col: str = "estanque") -> "PipelineLimpieza":
        """Unifica la capitalizacion del identificador de estanque.

        El archivo contiene `station1` en minuscula junto a `Station2` y
        `Station3` con inicial mayuscula. Sin normalizar, cualquier `groupby`
        trataria correctamente los tres, pero un filtro escrito a mano fallaria de
        forma silenciosa segun como se escriba el valor.
        """
        antes = self.df.copy()
        valores_previos = sorted(self.df[col].dropna().unique().tolist())

        self.df[col] = (
            self.df[col].astype("string").str.strip().str.lower().astype("category")
        )
        valores_nuevos = sorted(self.df[col].dropna().unique().tolist())
        self._registrar("Normalizar identificador de estanque",
            antes,
            f"{valores_previos} -> {valores_nuevos}",
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 5 - Conversion de tipos
    # ------------------------------------------------------------------
    def convertir_tipos(self, columnas: Optional[List[str]] = None) -> "PipelineLimpieza":
        """Convierte a numerico las variables leidas como texto.

        `errors='coerce'` transforma en `NaN` las celdas no convertibles: los
        errores de Excel `#VALUE!` y la cadena literal `'NaN'` detectados en la
        exploracion. Se cuenta cuantos valores se perdieron en la conversion para
        que la operacion quede cuantificada y no sea una perdida invisible.
        """
        columnas = columnas or [c for c in rutas.VARIABLES if c in self.df.columns]
        antes = self.df.copy()

        perdidos = 0
        for col in columnas:
            previo_nulos = self.df[col].isna().sum()
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce").astype("float64")
            perdidos += int(self.df[col].isna().sum() - previo_nulos)

        if "etiqueta_calidad" in self.df.columns:
            self.df["etiqueta_calidad"] = pd.to_numeric(
                self.df["etiqueta_calidad"], errors="coerce"
            ).astype("Int8")

        self._registrar("Convertir variables a numerico",
            antes,
            f"{perdidos} celdas no convertibles -> NaN",
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 6 - Eje temporal
    # ------------------------------------------------------------------
    def construir_eje_temporal(self) -> "PipelineLimpieza":
        """Crea la columna `timestamp` y descarta las filas sin instante valido.

        Una observacion sin marca temporal no puede ubicarse en la serie y por
        tanto es inutilizable para este proyecto. No se intenta reconstruir la
        hora faltante: cualquier suposicion (por ejemplo, heredar la hora de la
        fila anterior) inventaria una cadencia que no se observo.
        """
        antes = self.df.copy()
        self.df = temporal.construir_timestamp(self.df)

        sin_ts = int(self.df["timestamp"].isna().sum())
        self.df = self.df.dropna(subset=["timestamp"]).reset_index(drop=True)
        self.df = self.df.drop(
            columns=[rutas.COL_FECHA_ORIGEN, rutas.COL_HORA_ORIGEN], errors="ignore"
        )
        self._registrar("Construir timestamp y descartar sin fecha/hora",
            antes,
            f"{sin_ts} filas sin instante valido",
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 7 - Duplicados
    # ------------------------------------------------------------------
    def eliminar_duplicados(self, claves: Optional[List[str]] = None) -> "PipelineLimpieza":
        """Elimina duplicados exactos y conflictos por clave temporal.

        Primero se quitan las filas identicas en todas las columnas (fallo de
        exportacion, sin ambiguedad). Despues se resuelven los casos en que un
        mismo estanque tiene dos registros para el mismo instante con valores
        distintos: se conserva el primero, porque el archivo esta ordenado
        cronologicamente por origen y el primero corresponde a la lectura
        efectivamente transmitida por el sensor.
        """
        claves = claves or ["estanque", "timestamp"]
        antes = self.df.copy()

        n_exactos = int(self.df.duplicated().sum())
        self.df = self.df.drop_duplicates().reset_index(drop=True)

        presentes = [c for c in claves if c in self.df.columns]
        n_clave = int(self.df.duplicated(subset=presentes).sum()) if presentes else 0
        if presentes:
            self.df = self.df.drop_duplicates(subset=presentes, keep="first").reset_index(drop=True)

        self._registrar("Eliminar duplicados",
            antes,
            f"{n_exactos} exactos + {n_clave} por {tuple(presentes)}",
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 8 - Fallos de instrumento
    # ------------------------------------------------------------------
    def anular_fallos_de_sensor(
        self, rangos: Optional[Dict[str, tuple]] = None
    ) -> "PipelineLimpieza":
        """Convierte a nulo los valores fisicamente imposibles.

        Un valor fuera del rango que el instrumento puede medir no es un dato
        extremo: es la ausencia de dato codificada como numero. El caso claro en
        este dataset es la temperatura de 0.0 grados registrada en station2 y
        station3 durante la madrugada del 27-02-2022, en el mismo tramo horario en
        que station1 registro nulos: un unico fallo de sensor codificado de dos
        formas distintas. Tratar ese 0.0 como una medicion real hundiria cualquier media
        de temperatura y sugeriria un evento de frio extremo inexistente.

        Se anula el valor, **no se elimina la fila**: el resto de variables de esa
        observacion sigue siendo valido y utilizable.
        """
        rangos = rangos or rutas.RANGOS_FISICOS
        antes = self.df.copy()

        detalle = []
        total = 0
        for col, (lo, hi) in rangos.items():
            if col not in self.df.columns:
                continue
            mask = (self.df[col] < lo) | (self.df[col] > hi)
            n = int(mask.sum())
            if n:
                self.df.loc[mask, col] = np.nan
                detalle.append(f"{col}={n}")
                total += n

        self._registrar("Anular valores fisicamente imposibles",
            antes,
            f"{total} valores anulados" + (f" ({', '.join(detalle)})" if detalle else ""),
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 9 - Rejilla temporal regular
    # ------------------------------------------------------------------
    def regularizar_frecuencia(
        self, frecuencia: str = rutas.FRECUENCIA_NOMINAL
    ) -> "PipelineLimpieza":
        """Reindexa cada serie a la cadencia nominal de 20 minutos.

        Convierte los huecos implicitos (filas ausentes) en huecos explicitos
        (filas presentes con valores nulos), lo que permite contarlos, graficarlos
        y decidir sobre ellos. La columna `fila_imputada` distingue de forma
        permanente que filas provienen de una medicion real y cuales las creo esta
        rejilla; sin esa marca, las fases posteriores no podrian saber que parte
        del dataset es observacion y que parte es andamiaje.
        """
        antes = self.df.copy()
        columnas = [c for c in rutas.VARIABLES if c in self.df.columns]

        # La etiqueta de la fuente se arrastra por separado: no es una medicion
        # continua y no debe interpolarse.
        etiquetas = None
        if "etiqueta_calidad" in self.df.columns:
            etiquetas = self.df[["estanque", "timestamp", "etiqueta_calidad"]].copy()

        self.df = temporal.reindexar_a_frecuencia(
            self.df, frecuencia=frecuencia, columnas=columnas
        )

        if etiquetas is not None:
            self.df = self.df.merge(etiquetas, on=["estanque", "timestamp"], how="left")

        creadas = int(self.df["fila_imputada"].sum())
        self._registrar("Regularizar a frecuencia nominal",
            antes,
            f"{creadas} instantes sin medicion hechos explicitos",
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 10 - Valores ausentes
    # ------------------------------------------------------------------
    def tratar_nulos(
        self, limite: int = rutas.MAX_HUECOS_INTERPOLABLES
    ) -> "PipelineLimpieza":
        """Interpola linealmente en el tiempo los huecos cortos, por estanque.

        Estrategia deliberadamente conservadora. Se descartaron dos alternativas
        habituales (ver `docs/decisiones.md`, D-05):

        - *Imputar con la media global*: destruiria por completo la estructura que
          el proyecto estudia, aplanando el ciclo diario y la estacionalidad.
        - *Eliminar toda fila con algun nulo*: romperia la regularidad temporal
          recien construida, que es justamente lo que se quiere preservar.

        La interpolacion lineal limitada a `limite` lecturas consecutivas (1 hora)
        respeta la continuidad fisica de las variables en escalas cortas y deja
        los huecos largos visibles como nulos.
        """
        antes = self.df.copy()
        nulos_previos = int(self.df[[c for c in rutas.VARIABLES if c in self.df.columns]].isna().sum().sum())

        self.df = temporal.interpolar_por_grupo(self.df, limite=limite)

        nulos_post = int(self.df[[c for c in rutas.VARIABLES if c in self.df.columns]].isna().sum().sum())
        self._registrar("Interpolar huecos cortos (max 1 hora)",
            antes,
            f"{nulos_previos - nulos_post} valores imputados, {nulos_post} huecos largos conservados",
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 11 - Variables derivadas
    # ------------------------------------------------------------------
    def derivar_variables(self) -> "PipelineLimpieza":
        """Anade las variables de calendario derivadas de la marca temporal.

        No incorporan informacion nueva -- son funciones deterministas del
        `timestamp` -- pero dejan el dataset listo para agruparse y graficarse por
        mes, dia u hora sin repetir la extraccion en cada celda. Es la ultima
        transformacion del pipeline: a partir de aqui el dataset esta completo.
        """
        antes = self.df.copy()
        self.df = temporal.agregar_features_calendario(self.df)

        nuevas = [c for c in self.df.columns if c not in antes.columns]
        self._registrar(
            "Derivar variables de calendario",
            antes,
            f"{len(nuevas)} variables anadidas: {', '.join(nuevas)}",
        )
        return self

    # ------------------------------------------------------------------
    # Etapa 12 - Orden final
    # ------------------------------------------------------------------
    def ordenar_y_finalizar(self) -> "PipelineLimpieza":
        """Ordena por estanque e instante y fija el orden de columnas."""
        antes = self.df.copy()

        self.df = self.df.sort_values(["estanque", "timestamp"]).reset_index(drop=True)

        identificacion = ["timestamp", "estanque"]
        medidas = [c for c in rutas.VARIABLES if c in self.df.columns]
        calendario = [
            c
            for c in [
                "anio", "mes", "dia", "hora", "minuto", "dia_semana",
                "nombre_dia", "anio_mes", "fecha", "estacion_anio", "franja_horaria",
            ]
            if c in self.df.columns
        ]
        resto = [
            c for c in self.df.columns if c not in identificacion + medidas + calendario
        ]

        self.df = self.df[identificacion + medidas + calendario + resto]
        self._registrar("Ordenar por estanque e instante", antes, f"{self.df.shape[1]} columnas finales")
        return self

    # ------------------------------------------------------------------
    # Ejecucion completa
    # ------------------------------------------------------------------
    def ejecutar(self) -> pd.DataFrame:
        """Corre todas las etapas en el orden correcto y devuelve el resultado."""
        (
            self.normalizar_nombres()
            .normalizar_centinelas()
            .eliminar_filas_vacias()
            .normalizar_estanque()
            .convertir_tipos()
            .construir_eje_temporal()
            .eliminar_duplicados()
            .anular_fallos_de_sensor()
            .regularizar_frecuencia()
            .tratar_nulos()
            .derivar_variables()
            .ordenar_y_finalizar()
        )
        return self.df

    def resumen(self) -> pd.DataFrame:
        """Compara el estado inicial y final del dataset."""
        return pd.DataFrame(
            [
                {
                    "estado": "crudo",
                    "filas": len(self.df_original),
                    "columnas": self.df_original.shape[1],
                    "nulos": int(self.df_original.isna().sum().sum()),
                },
                {
                    "estado": "procesado",
                    "filas": len(self.df),
                    "columnas": self.df.shape[1],
                    "nulos": int(self.df.isna().sum().sum()),
                },
            ]
        )


# ---------------------------------------------------------------------------
# Escalamiento
# ---------------------------------------------------------------------------
METODOS_ESCALADO = ("zscore", "minmax")


def escalar_variables(
    df: pd.DataFrame,
    columnas: Optional[List[str]] = None,
    metodo: str = "zscore",
    col_grupo: str = "estanque",
) -> pd.DataFrame:
    """Escala las variables medidas por estanque, sin tocar el dataset limpio.

    Queda fuera del pipeline a proposito: el dataset limpio se conserva en
    unidades fisicas (grados, mg/L, NTU), que son las que tienen interpretacion.
    El escalado produce una copia aparte, pensada para las fases de modelado.

    - `zscore`: (x - media) / desviacion estandar. Deja cada variable con media 0
      y desviacion 1; es el adecuado para metodos sensibles a la magnitud.
    - `minmax`: (x - minimo) / (maximo - minimo). Lleva cada variable a [0, 1].

    Se escala **por estanque** porque los tres tienen niveles de base distintos;
    un escalado global mezclaria esa diferencia de nivel con la variacion propia
    de cada serie. Si una variable es constante dentro de un estanque, el divisor
    es cero y el resultado queda en `NaN` en lugar de `inf`.

    Nota para F3: aqui se escala con todo el dataset porque no hay modelo. Al
    modelar, los parametros deben calcularse solo con el conjunto de
    entrenamiento para no filtrar informacion del conjunto de prueba.

    Raises
    ------
    ValueError
        Si el metodo no es uno de `METODOS_ESCALADO`.
    KeyError
        Si faltan columnas a escalar o la columna de grupo.
    """
    if metodo not in METODOS_ESCALADO:
        raise ValueError(
            f"Metodo de escalado '{metodo}' no soportado. Opciones: {METODOS_ESCALADO}"
        )

    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    faltantes = [c for c in list(columnas) + [col_grupo] if c not in df.columns]
    if faltantes:
        raise KeyError(f"Columnas ausentes para escalar: {faltantes}")

    out = df.copy()
    grupos = out.groupby(col_grupo, observed=True)[columnas]

    if metodo == "zscore":
        centro = grupos.transform("mean")
        escala = grupos.transform("std")
    else:
        centro = grupos.transform("min")
        escala = grupos.transform("max") - centro

    out[columnas] = (out[columnas] - centro) / escala.replace(0, np.nan)
    return out
