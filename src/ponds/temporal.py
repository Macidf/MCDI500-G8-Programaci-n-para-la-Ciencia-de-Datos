"""
Construccion del eje temporal y variables derivadas del calendario.

Este modulo concentra el nucleo del enfoque del proyecto: el dataset no es una
tabla de observaciones independientes sino tres series de tiempo paralelas, y casi
todas las decisiones de limpieza dependen de respetar ese orden.
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from ponds import rutas


def construir_timestamp(
    df: pd.DataFrame,
    col_fecha: str = rutas.COL_FECHA_ORIGEN,
    col_hora: str = rutas.COL_HORA_ORIGEN,
    formato: str = "%d-%m-%Y %H:%M:%S",
    col_salida: str = "timestamp",
) -> pd.DataFrame:
    """Combina las columnas de fecha y hora en una unica marca temporal.

    Se especifica el formato de forma explicita (`%d-%m-%Y`) en lugar de dejar que
    pandas lo infiera. El dataset es dia-mes-anio y la inferencia automatica
    interpretaria '01-02-2022' como 1 de febrero o 2 de enero segun la fila,
    corrompiendo el orden temporal de manera silenciosa.

    Los valores no parseables quedan como `NaT`, nunca se descartan aqui: esa
    decision corresponde al pipeline de limpieza, que la documenta.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset con las columnas de fecha y hora por separado.
    col_fecha, col_hora : str
        Nombres de las columnas de origen.
    formato : str
        Formato `strftime` del texto combinado.
    col_salida : str
        Nombre de la columna a crear.

    Returns
    -------
    pd.DataFrame
        Copia del dataset con la columna `timestamp` anadida al inicio.
    """
    out = df.copy()
    combinado = (
        out[col_fecha].astype("string").str.strip()
        + " "
        + out[col_hora].astype("string").str.strip()
    )
    out[col_salida] = pd.to_datetime(combinado, format=formato, errors="coerce")

    # Mover la marca temporal al frente: es la clave de lectura del dataset.
    cols = [col_salida] + [c for c in out.columns if c != col_salida]
    return out[cols]


def agregar_features_calendario(
    df: pd.DataFrame, col_ts: str = "timestamp"
) -> pd.DataFrame:
    """Deriva variables de calendario a partir de la marca temporal.

    Estas variables no anaden informacion nueva -- son funciones deterministas del
    timestamp -- pero hacen que la estructura temporal sea agrupable y graficable
    directamente, que es justamente el objeto del analisis: comparar meses,
    contrastar horas del dia o separar por estacion del ano.

    La estacion del ano usa el calendario del subcontinente indio (invierno,
    verano, monzon, post-monzon), no el de cuatro estaciones templadas, porque los
    estanques estan en Guntur (Andhra Pradesh) y el monzon es el factor que
    domina la variabilidad del agua en esa region.

    Returns
    -------
    pd.DataFrame
        Copia con las columnas de calendario anadidas.
    """
    out = df.copy()
    ts = out[col_ts]

    out["anio"] = ts.dt.year.astype("Int16")
    out["mes"] = ts.dt.month.astype("Int8")
    out["dia"] = ts.dt.day.astype("Int8")
    out["hora"] = ts.dt.hour.astype("Int8")
    out["minuto"] = ts.dt.minute.astype("Int8")
    out["dia_semana"] = ts.dt.dayofweek.astype("Int8")  # 0 = lunes
    out["nombre_dia"] = ts.dt.day_name()
    out["anio_mes"] = ts.dt.to_period("M").astype("string")
    out["fecha"] = ts.dt.date
    out["estacion_anio"] = (
        ts.dt.month.map(rutas.ESTACIONES_ANIO).astype("category")
    )
    # Franja horaria: agrupa el ciclo diario en bloques interpretables para el
    # analisis del comportamiento intradiario del oxigeno disuelto.
    out["franja_horaria"] = pd.cut(
        ts.dt.hour,
        bins=[-1, 5, 11, 17, 23],
        labels=["Madrugada (00-05)", "Manana (06-11)", "Tarde (12-17)", "Noche (18-23)"],
    )
    return out


def detectar_huecos(
    df: pd.DataFrame,
    col_ts: str = "timestamp",
    col_grupo: str = "estanque",
    minutos_nominales: int = rutas.MINUTOS_NOMINALES,
) -> pd.DataFrame:
    """Localiza las interrupciones del registro en cada serie.

    Un "hueco" es un intervalo entre dos lecturas consecutivas mayor que la
    cadencia nominal. Detectarlos importa por dos razones: cuantifican la
    cobertura real del monitoreo (frente a la teorica) y delimitan hasta donde es
    legitimo interpolar.

    Returns
    -------
    pd.DataFrame
        Un registro por hueco: estanque, instante previo, instante siguiente,
        duracion en minutos y cuantas lecturas nominales se perdieron.
    """
    filas = []
    for grupo, g in df.dropna(subset=[col_ts]).groupby(col_grupo, observed=True):
        g = g.sort_values(col_ts)
        delta_min = g[col_ts].diff().dt.total_seconds().div(60)
        mask = delta_min > minutos_nominales

        for idx in g.index[mask]:
            pos = g.index.get_loc(idx)
            filas.append(
                {
                    "estanque": grupo,
                    "ultima_lectura": g[col_ts].iloc[pos - 1],
                    "siguiente_lectura": g[col_ts].iloc[pos],
                    "duracion_min": float(delta_min.loc[idx]),
                    "lecturas_perdidas": int(delta_min.loc[idx] / minutos_nominales) - 1,
                }
            )

    resultado = pd.DataFrame(
        filas,
        columns=[
            "estanque",
            "ultima_lectura",
            "siguiente_lectura",
            "duracion_min",
            "lecturas_perdidas",
        ],
    )
    return resultado.sort_values("duracion_min", ascending=False).reset_index(drop=True)


def resumen_cobertura(
    df: pd.DataFrame,
    col_ts: str = "timestamp",
    col_grupo: str = "estanque",
    minutos_nominales: int = rutas.MINUTOS_NOMINALES,
) -> pd.DataFrame:
    """Compara las lecturas observadas con las esperadas por cada estanque.

    La cobertura se calcula sobre el intervalo real de cada serie (de su primera a
    su ultima lectura), no sobre el ano completo: mezclar ambas cosas haria que un
    estanque que dejo de operar antes apareciera como si tuviera datos corruptos,
    cuando en realidad tiene una ventana de observacion mas corta.
    """
    filas = []
    for grupo, g in df.dropna(subset=[col_ts]).groupby(col_grupo, observed=True):
        ts = g[col_ts].sort_values()
        inicio, fin = ts.min(), ts.max()
        span_min = (fin - inicio).total_seconds() / 60
        esperadas = int(span_min / minutos_nominales) + 1

        filas.append(
            {
                "estanque": grupo,
                "inicio": inicio,
                "fin": fin,
                "dias_cubiertos": round(span_min / 1440, 1),
                "lecturas_observadas": len(ts),
                "lecturas_esperadas": esperadas,
                "lecturas_faltantes": esperadas - len(ts),
                "cobertura_pct": round(len(ts) / esperadas * 100, 2),
            }
        )
    return pd.DataFrame(filas).sort_values("estanque").reset_index(drop=True)


def resumir_por_periodo(
    df: pd.DataFrame,
    periodo: str,
    columnas: Optional[List[str]] = None,
    col_ts: str = "timestamp",
    col_grupo: str = "estanque",
    funcion: str = "mean",
) -> pd.DataFrame:
    """Agrega las variables a una granularidad temporal mayor.

    Sirve para pasar de la cadencia de 20 minutos a medias horarias, diarias o
    mensuales sin perder la separacion por estanque. Es la base de los graficos de
    estacionalidad: a 20 minutos la serie anual tiene 75.000 puntos y el ruido
    oculta por completo la tendencia.

    Parameters
    ----------
    periodo : str
        Alias de frecuencia de pandas ('h', 'D', 'W', 'ME').
    funcion : str
        Agregacion a aplicar ('mean', 'median', 'max', 'min', 'std').
    """
    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    base = df.dropna(subset=[col_ts]).set_index(col_ts)

    agregado = (
        base.groupby(col_grupo, observed=True)[columnas]
        .resample(periodo)
        .agg(funcion)
        .reset_index()
    )
    return agregado


def reindexar_a_frecuencia(
    df: pd.DataFrame,
    frecuencia: str = rutas.FRECUENCIA_NOMINAL,
    col_ts: str = "timestamp",
    col_grupo: str = "estanque",
    columnas: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Fuerza una rejilla temporal regular por estanque, dejando huecos explicitos.

    Tras esta operacion cada estanque tiene una fila por cada instante nominal de
    su ventana de observacion; los instantes sin medicion aparecen como filas con
    valores nulos. Esto convierte un hueco implicito (una fila que simplemente no
    existe) en un hueco explicito y contable, que es requisito para que cualquier
    metodo de series de tiempo de las fases siguientes se comporte correctamente.

    Returns
    -------
    pd.DataFrame
        Dataset reindexado, con la columna booleana `fila_imputada` que marca las
        filas creadas por la rejilla y que no provienen de una medicion real.
    """
    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    partes = []

    for grupo, g in df.dropna(subset=[col_ts]).groupby(col_grupo, observed=True):
        g = g.sort_values(col_ts).drop_duplicates(subset=[col_ts], keep="first")
        rejilla = pd.date_range(g[col_ts].min(), g[col_ts].max(), freq=frecuencia)

        reindexado = (
            g.set_index(col_ts)[columnas]
            .reindex(rejilla)
            .rename_axis(col_ts)
            .reset_index()
        )
        reindexado[col_grupo] = grupo
        reindexado["fila_imputada"] = ~reindexado[col_ts].isin(g[col_ts])
        partes.append(reindexado)

    resultado = pd.concat(partes, ignore_index=True)
    # `groupby` devuelve la etiqueta del grupo como escalar, por lo que la
    # asignacion anterior degrada la columna a `object`. Se restituye el tipo
    # `category` para no perder la eficiencia de memoria ni el orden de niveles.
    resultado[col_grupo] = resultado[col_grupo].astype("category")

    orden = [col_ts, col_grupo] + columnas + ["fila_imputada"]
    return resultado[orden].sort_values([col_grupo, col_ts]).reset_index(drop=True)


def interpolar_por_grupo(
    df: pd.DataFrame,
    columnas: Optional[List[str]] = None,
    col_ts: str = "timestamp",
    col_grupo: str = "estanque",
    limite: int = rutas.MAX_HUECOS_INTERPOLABLES,
) -> pd.DataFrame:
    """Interpola linealmente en el tiempo, con un limite estricto de huecos.

    Dos garantias importantes:

    1. La interpolacion es **por estanque**. Interpolar sobre el dataset completo
       mezclaria el final de la serie de un estanque con el inicio de la del
       siguiente, inventando transiciones que nunca ocurrieron.
    2. El parametro `limit` acota cuantas lecturas consecutivas se rellenan. Las
       variables de calidad de agua tienen continuidad fisica en escalas de
       minutos, pero no de horas: interpolar un hueco de medio dia fabricaria una
       recta donde pudo haber un evento critico (por ejemplo, una caida nocturna
       de oxigeno). Los huecos largos se conservan como nulos.

    Se usa `limit_area='inside'` para no extrapolar antes de la primera medicion
    ni despues de la ultima de cada serie.
    """
    columnas = columnas or [c for c in rutas.VARIABLES if c in df.columns]
    out = df.copy().sort_values([col_grupo, col_ts])

    def _interpolar_huecos_cortos(s: pd.Series) -> pd.Series:
        # El argumento `limit` de pandas rellenaria las primeras `limite`
        # posiciones de CUALQUIER hueco, incluso de uno de 20 horas. Aqui se
        # interpola el hueco completo solo si su largo total no supera el limite;
        # los huecos mas largos quedan intactos como nulos.
        completa = s.interpolate(method="linear", limit_area="inside")
        rellenable = s.isna() & (largo_rachas_nulas(s) <= limite)
        return s.where(~rellenable, completa)

    out[columnas] = (
        out.groupby(col_grupo, observed=True)[columnas]
        .transform(_interpolar_huecos_cortos)
    )
    return out.reset_index(drop=True)


def largo_rachas_nulas(s: pd.Series) -> pd.Series:
    """Devuelve, para cada posicion nula, el largo de la racha de nulos que la contiene.

    Las posiciones no nulas reciben 0. Ejemplo: `[1, NaN, NaN, 4, NaN]` produce
    `[0, 2, 2, 0, 1]`. Permite decidir si un hueco es corto (interpolable) o
    largo (se conserva), y verificar despues que la imputacion respeto ese criterio.
    """
    nulo = s.isna()
    id_racha = (nulo != nulo.shift()).cumsum()
    largo = nulo.groupby(id_racha).transform("sum")
    return largo.where(nulo, 0).astype(int)
