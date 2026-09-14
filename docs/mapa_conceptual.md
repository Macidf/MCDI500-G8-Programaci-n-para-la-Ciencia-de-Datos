# Vinculación del mapa conceptual técnico con el avance

El mapa conceptual técnico elaborado en la actividad formativa se encuentra en `F1/`.
Este documento establece qué elemento del mapa se materializó en qué producto, y qué
queda proyectado para las fases siguientes.

> **Nota para el equipo:** los nombres de la columna "Elemento del mapa" deben
> ajustarse a los rótulos exactos del diagrama en `F1/`.

## 1. Elementos materializados en F1–F2

| Elemento del mapa | Materialización | Dónde verificarlo |
|---|---|---|
| **Problemática:** calidad del agua en acuicultura monitoreada por IoT | Selección del dataset Pondsdata y descripción del contexto | Informe §II–III · `README.md` §1 |
| **Herramienta:** Python 3.10 | Intérprete del entorno virtual | `requirements.txt` · celda de entorno de cada notebook |
| **Herramienta:** NumPy | Operaciones numéricas, `np.nan`, `linspace` en pruebas | `limpieza.py` · `F2_03` |
| **Herramienta:** Pandas | Carga, casting, `groupby`, `resample`, `reindex`, interpolación | Todo `src/ponds/` |
| **Herramienta:** Matplotlib / Seaborn | Figuras de exploración y series de tiempo | `graficos.py` · `docs/figuras/` |
| **Herramienta:** Jupyter | Notebooks ejecutables con narrativa | `F2/*.ipynb` |
| **Herramienta:** Git / GitHub | Historial de commits, ramas `main` y `dev` | `git log` · `docs/guia_git.md` |
| **Flujo reproducible:** entorno virtual + dependencias | `.venv` y `requirements.txt` con versiones fijadas | `README.md` §4 |
| **Flujo reproducible:** rutas relativas | `rutas.py` y búsqueda de la raíz en cada notebook | `rutas.py` · primera celda de cada notebook |
| **Etapa:** obtención de datos | Carga trazable con SHA-256 | `io_datos.py` · `F2_01` §2 · `data/raw/README_DATOS.md` |
| **Etapa:** exploración | Diagnóstico con 9 hallazgos (H-01 a H-09) | `perfilado.py` · `F2_01` §3–5 |
| **Etapa:** limpieza | `PipelineLimpieza`, 12 etapas con bitácora | `limpieza.py` · `F2_02` §2–3 |
| **Etapa:** transformación | Casting, timestamp, rejilla regular, calendario, escalamiento | `temporal.py` · `limpieza.py` · `F2_02` §2, §4 |
| **Etapa:** validación | `ValidadorDataset` + 22 pruebas normales, límite y de excepción | `validacion.py` · `F2_03` · `docs/registro_validacion.csv` |
| **Organización del repositorio** | Carpetas `F1`, `F2`, `src`, `data`, `docs` | Árbol del repositorio · `README.md` §3 |
| **Documentación de decisiones** | Bitácora con alternativas descartadas | `docs/decisiones.md` |
| **Modularidad / POO** | Funciones parametrizadas y clases `PipelineLimpieza`, `ValidadorDataset` | `src/ponds/` |

## 2. Ajustes respecto de la planificación

| Planificado | Implementado | Motivo |
|---|---|---|
| Descarga automatizada desde Kaggle | Descarga manual con verificación por hash | Kaggle bloquea descargas sin sesión (D-01) |
| Exportación en Parquet | Exportación en CSV con restitución de tipos | Evitar la dependencia `pyarrow` (D-11) |
| Suite de pruebas con pytest | Pruebas dentro de `F2_03` | Mantener la evidencia visible en los notebooks (D-13) |

## 3. Elementos proyectados para fases posteriores

| Elemento del mapa | Fase | Base que deja F2 |
|---|---|---|
| Análisis exploratorio profundo (estacionalidad, ciclo diario, comparación entre estanques) | F3 | Variables de calendario y rejilla regular en `ponds_limpio.csv` |
| Modelado (clasificación de calidad o pronóstico) | F3 | `etiqueta_calidad`, `ponds_escalado.csv`, marca `fila_imputada` |
| Separación entrenamiento / prueba sin fuga de información | F3 | Nota en D-10 sobre recalcular el escalado |
| Evaluación de modelos y métricas | F3–F4 | — |
| Visualización final y comunicación de resultados | F4 | Estilo homogéneo en `graficos.py` |
| Informe final y presentación | F4 | Estructura de este avance |
