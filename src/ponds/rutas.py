"""
Rutas del proyecto, metadatos institucionales y constantes de dominio.

Centralizar estos valores en un unico modulo evita rutas absolutas dispersas por
los notebooks (principal causa de que un proyecto deje de ser reproducible al
cambiar de equipo) y permite que cualquier integrante clone el repositorio y
ejecute todo sin editar una sola celda.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Final, List, Tuple

# ---------------------------------------------------------------------------
# 1. Rutas del proyecto
# ---------------------------------------------------------------------------
# Se resuelven a partir de la ubicacion de ESTE archivo, no del directorio de
# trabajo: asi funcionan igual desde un notebook en F2/, desde la raiz del repo
# o desde una ejecucion por linea de comandos.
#   src/ponds/rutas.py -> parents[0]=ponds, parents[1]=src, parents[2]=raiz
RAIZ: Final[Path] = Path(__file__).resolve().parents[2]

DIR_DATOS: Final[Path] = RAIZ / "data"
DIR_CRUDO: Final[Path] = DIR_DATOS / "raw"
DIR_PROCESADO: Final[Path] = DIR_DATOS / "processed"
DIR_DOCS: Final[Path] = RAIZ / "docs"
DIR_FIGURAS: Final[Path] = DIR_DOCS / "figuras"
DIR_F1: Final[Path] = RAIZ / "F1"
DIR_F2: Final[Path] = RAIZ / "F2"

# Archivo fuente elegido dentro del ZIP de Kaggle (ver docs/decisiones.md, D-02).
ARCHIVO_CRUDO: Final[str] = "Ponds data.csv"
ARCHIVO_PROCESADO: Final[str] = "ponds_limpio.csv"


def asegurar_directorios() -> None:
    """Crea los directorios de salida si no existen (idempotente)."""
    for d in (DIR_CRUDO, DIR_PROCESADO, DIR_FIGURAS):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 2. Metadatos institucionales (portada del informe y README)
# ---------------------------------------------------------------------------
PROYECTO: Final[Dict[str, str]] = {
    "curso": "Programacion para la Ciencia de Datos",
    "codigo_curso": "MCDI500",
    "grupo": "G8",
    "institucion": "Universidad Andres Bello (UNAB)",
    "titulo": (
        "Caracterizacion del comportamiento temporal de la calidad del agua "
        "en estanques de acuicultura monitoreados por IoT"
    ),
    "docente": "[DOCENTE RESPONSABLE]",
    "integrantes": "Mauricio Cid Fuentes; [INTEGRANTE 2]; [INTEGRANTE 3]; [INTEGRANTE 4]",
    "repositorio": (
        "https://github.com/Macidf/MCDI500-G8-Programaci-n-para-la-Ciencia-de-Datos"
    ),
}

FUENTE_DATOS: Final[Dict[str, str]] = {
    "nombre": "Pondsdata",
    "autor": "Arepalli Peda Gopi",
    "url": "https://www.kaggle.com/datasets/apgopi/pondsdata",
    "cobertura": "Febrero 2022 - Enero 2023",
    "ubicacion": "Guntur, Andhra Pradesh, India",
    "descripcion": (
        "Registros de calidad de agua capturados por sensores IoT en tres "
        "estanques de acuicultura, con cadencia nominal de 20 minutos."
    ),
}

# ---------------------------------------------------------------------------
# 3. Esquema del dataset crudo
# ---------------------------------------------------------------------------
COL_ESTACION_ORIGEN: Final[str] = "station"
COL_FECHA_ORIGEN: Final[str] = "Date"
COL_HORA_ORIGEN: Final[str] = "Time"
COL_ETIQUETA_ORIGEN: Final[str] = "label"

# Mapeo origen -> nombre normalizado. Se pasa a snake_case sin unidades en el
# nombre porque las unidades se documentan aparte (ver UNIDADES): un nombre de
# columna con parentesis y barras obliga a usar df["..."] en todo el codigo.
RENOMBRE_COLUMNAS: Final[Dict[str, str]] = {
    "station": "estanque",
    "NITRATE(PPM)": "nitrato",
    "PH": "ph",
    "AMMONIA(mg/l)": "amonio",
    "TEMP": "temperatura",
    "DO": "oxigeno_disuelto",
    "TURBIDITY": "turbidez",
    "MANGANESE(mg/l)": "manganeso",
    "label": "etiqueta_calidad",
}

VARIABLES: Final[List[str]] = [
    "nitrato",
    "ph",
    "amonio",
    "temperatura",
    "oxigeno_disuelto",
    "turbidez",
    "manganeso",
]

UNIDADES: Final[Dict[str, str]] = {
    "nitrato": "ppm",
    "ph": "adimensional",
    "amonio": "mg/L",
    "temperatura": "grados Celsius",
    "oxigeno_disuelto": "mg/L",
    "turbidez": "NTU",
    "manganeso": "mg/L",
}

DESCRIPCION_VARIABLES: Final[Dict[str, str]] = {
    "estanque": "Identificador del estanque monitoreado (station1, station2, station3).",
    "nitrato": "Concentracion de nitrato; producto final de la nitrificacion.",
    "ph": "Acidez o alcalinidad del agua.",
    "amonio": "Amonio total; toxico para los peces en concentraciones elevadas.",
    "temperatura": "Temperatura del agua; gobierna el metabolismo y la solubilidad del oxigeno.",
    "oxigeno_disuelto": "Oxigeno disuelto; variable critica para la supervivencia del cultivo.",
    "turbidez": "Turbidez; mide solidos en suspension y penetracion de la luz.",
    "manganeso": "Concentracion de manganeso disuelto.",
    "etiqueta_calidad": (
        "Etiqueta binaria (0/1) provista por la fuente. Se interpreta 1 como calidad "
        "no apta; la fuente no documenta su definicion, por lo que es un supuesto."
    ),
}

# Cadenas que el archivo original usa para representar ausencia de dato. El CSV
# proviene de una hoja de calculo: '#VALUE!' es un error de formula de Excel y
# 'NaN' quedo escrito como texto literal, no como valor nulo.
CENTINELAS_NULOS: Final[List[str]] = ["", " ", "NaN", "nan", "NA", "N/A", "#VALUE!", "#N/A", "null"]

# ---------------------------------------------------------------------------
# 4. Constantes de dominio
# ---------------------------------------------------------------------------
# Se distinguen DOS tipos de rango, y la distincion es deliberada:
#
#   RANGOS_FISICOS      -> lo que el sensor puede medir sin estar averiado.
#                          Un valor fuera de aqui es un FALLO DE INSTRUMENTO y se
#                          convierte a nulo (no es informacion sobre el estanque).
#
#   RANGOS_OPERACIONALES-> lo que se considera seguro para el cultivo. Se usan
#                          solo como banda de referencia en los graficos de serie
#                          temporal: los valores fuera de este rango son datos
#                          validos y NO se eliminan ni se corrigen.
#
# Confundir ambos es el error clasico que destruye la senal de interes: si se
# recortaran los valores por rango operacional, desaparecerian justamente los
# eventos de mala calidad de agua que interesa conservar.
RANGOS_FISICOS: Final[Dict[str, Tuple[float, float]]] = {
    "nitrato": (0.0, 500.0),
    "ph": (0.0, 14.0),
    "amonio": (0.0, 10.0),
    "temperatura": (5.0, 50.0),
    "oxigeno_disuelto": (0.0, 30.0),
    "turbidez": (0.0, 1000.0),
    "manganeso": (0.0, 10.0),
}

RANGOS_OPERACIONALES: Final[Dict[str, Tuple[float, float]]] = {
    "nitrato": (0.0, 50.0),
    "ph": (6.5, 9.0),
    "amonio": (0.0, 0.50),
    "temperatura": (20.0, 32.0),
    "oxigeno_disuelto": (5.0, 20.0),
    "turbidez": (0.0, 40.0),
    "manganeso": (0.0, 1.0),
}

# Cadencia nominal del registro IoT: 72 lecturas diarias = una cada 20 minutos.
FRECUENCIA_NOMINAL: Final[str] = "20min"
MINUTOS_NOMINALES: Final[int] = 20

# Interpolacion temporal limitada: se rellenan como maximo 3 lecturas seguidas
# (1 hora). Mas alla de esa ventana no hay base fisica para suponer continuidad
# y el hueco se deja explicito (ver docs/decisiones.md, D-05).
MAX_HUECOS_INTERPOLABLES: Final[int] = 3

ESTACIONES_ANIO: Final[Dict[int, str]] = {
    1: "Invierno", 2: "Invierno", 3: "Verano", 4: "Verano", 5: "Verano",
    6: "Monzon", 7: "Monzon", 8: "Monzon", 9: "Monzon",
    10: "Post-monzon", 11: "Post-monzon", 12: "Invierno",
}
