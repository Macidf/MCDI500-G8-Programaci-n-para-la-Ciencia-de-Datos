# Bitácora de decisiones técnicas

Registro de las decisiones tomadas en las Fases 1 y 2: qué se decidió, por qué, qué
alternativas se descartaron y qué impacto tuvo en el desarrollo.

Formato de cada entrada: **contexto → decisión → alternativas descartadas → impacto**.

---

## Fase 1 — Entorno y organización

### D-00 · Separar la lógica en un paquete `src/ponds/`
- **Contexto.** Los tres notebooks de F2 comparten operaciones (carga, rutas, gráficos).
- **Decisión.** Toda la lógica se implementa como funciones y clases en `src/ponds/`; los
  notebooks sólo las invocan y documentan resultados.
- **Descartado.** Código directamente en celdas: obliga a copiar funciones entre
  notebooks, y una corrección en uno no llega a los otros.
- **Impacto.** Una sola implementación por operación, versionada y verificable por separado
  (ver `F2_03`).

### D-0A · Entorno virtual con `venv` y dependencias fijadas
- **Decisión.** `python -m venv .venv` y `requirements.txt` con versiones exactas (`==`).
- **Descartado.** Conda: agrega una herramienta más a instalar para todo el equipo sin
  beneficio para las librerías usadas, todas disponibles en PyPI.
- **Impacto.** Cualquier integrante reproduce el mismo entorno con dos comandos.

### D-0B · Rutas relativas a la raíz del proyecto
- **Decisión.** `rutas.py` calcula la raíz a partir de su propia ubicación, y cada notebook
  busca la carpeta `src/ponds` hacia arriba desde el directorio de trabajo.
- **Descartado.** Rutas absolutas (`C:\Users\...`): el proyecto dejaría de funcionar en
  cualquier otro equipo.
- **Impacto.** Los notebooks corren igual desde JupyterLab, VS Code o `nbconvert`.

---

## Fase 2 — Obtención

### D-01 · Descarga manual del dataset
- **Contexto.** Kaggle exige autenticación y responde con un desafío reCAPTCHA a las
  descargas automatizadas.
- **Decisión.** El dataset se descarga a mano; el código parte del archivo local y calcula
  su **SHA-256**, registrado en `data/raw/README_DATOS.md`.
- **Descartado.** API de Kaggle: exige que cada integrante configure un token personal, lo
  que agrega un punto de fallo sin mejorar la reproducibilidad del análisis.
- **Impacto.** La trazabilidad se garantiza por el hash, no por el método de descarga.

### D-02 · Usar `Ponds data.csv` como fuente primaria
- **Contexto.** El ZIP trae cinco CSV que son versiones del mismo registro.
- **Decisión.** Se usa `Ponds data.csv`.
- **Motivo.** Es el único que conserva a la vez estanque, fecha, hora y el registro completo.
- **Descartado.**
  - `Fish Ponds.csv`: más limpio, pero sin columnas de estanque ni de tiempo; sus filas no
    se pueden ubicar en la serie.
  - `Ponds.csv`: agregado a 18.102 filas, perdió la cadencia de 20 minutos.
  - `Aquaponds Dataset.csv`: 50.000 filas en orden no cronológico y con otra etiqueta.
- **Impacto.** La Fase 2 trabaja sobre el archivo con más información y más defectos, que
  es lo que da sentido al pipeline.

### D-03 · Cargar todo como texto
- **Decisión.** `cargar_crudo()` usa `dtype=str` y sólo considera nula la celda vacía.
- **Descartado.** Inferencia automática de tipos: las columnas contaminadas quedarían como
  `object` sin aviso y los centinelas `#VALUE!` y `'NaN'` no se podrían contar.
- **Impacto.** La exploración cuantificó 13 `#VALUE!` y 7 `'NaN'` antes de corregirlos.

---

## Fase 2 — Limpieza

### D-04 · Orden fijo de etapas mediante una clase
- **Decisión.** `PipelineLimpieza` encadena las 12 etapas y registra en una bitácora filas y
  nulos antes y después de cada una.
- **Motivo.** Las etapas no conmutan: los duplicados deben eliminarse **después** de las
  filas vacías (que eran todos los duplicados), y los centinelas deben unificarse **antes**
  del casting para poder contarlos.
- **Descartado.** Una función única sin registro: el efecto de cada paso no sería verificable.

### D-05 · Interpolar sólo huecos de hasta 1 hora
- **Contexto.** Tras regularizar la rejilla quedan nulos en huecos de 20 minutos a ~20 horas.
- **Decisión.** Interpolación lineal por estanque sólo en huecos de **3 lecturas o menos**;
  los huecos más largos se conservan como `NaN`.
- **Descartado.**
  - Media global: aplana la variación diaria y estacional.
  - Eliminar filas con nulos: rompe la rejilla regular.
  - Interpolar todo: inventa una recta en huecos de horas.
  - `interpolate(limit=3)` de pandas: rellena las **primeras 3** posiciones de cualquier
    hueco, incluso de uno largo. Se detectó al revisar el resultado y se reemplazó por una
    implementación que mide el largo total del hueco (`temporal.largo_rachas_nulas`).
- **Impacto.** Los nulos residuales son < 0,2 % y todos pertenecen a huecos largos
  (verificado en `F2_03`, prueba N05).

### D-06 · Anular valores imposibles sin eliminar la fila
- **Contexto.** 12 temperaturas de 0,0 °C la madrugada del 27-02-2022 (6 en `station2` y 6 en
  `station3`); en la misma ventana `station1` registra `NaN`. Es un mismo fallo de sensor que
  afectó a los tres estanques y quedó codificado de dos formas.
- **Decisión.** Rangos físicos amplios (`RANGOS_FISICOS`); lo que queda fuera se convierte en `NaN`.
- **Descartado.**
  - Eliminar la fila: perdería seis variables válidas por una defectuosa.
  - Recortar por rango operacional: eliminaría eventos reales de mala calidad del agua.
- **Impacto.** La temperatura mínima pasa de 0,0 °C a 14,5 °C, conservando todas las lecturas.

### D-07 · Descartar registros sin hora
- **Decisión.** Las 51 filas con fecha pero sin hora se eliminan.
- **Descartado.** Heredar la hora de la fila anterior: fabricaría una cadencia no observada.
- **Impacto.** Pérdida del 0,07 % de los registros; la rejilla de la etapa 9 deja esos
  instantes como huecos explícitos.

### D-08 · Rejilla regular con marca `fila_imputada`
- **Decisión.** Reindexar cada estanque a 20 minutos y marcar las filas creadas.
- **Motivo.** Los métodos de series de tiempo requieren paso constante, y los huecos
  implícitos no se pueden contar.
- **Impacto.** El dataset crece de 74.707 a 74.854 filas; la marca permite distinguir
  siempre medición real de andamiaje.

---

## Fase 2 — Transformación

### D-09 · Nombres en *snake_case* y unidades aparte
- **Decisión.** `NITRATE(PPM)` → `nitrato`, etc.; unidades en `rutas.UNIDADES`.
- **Impacto.** Acceso por atributo y menos errores de tipeo, sin perder la información de unidad.

### D-10 · Escalamiento en una copia aparte y por estanque
- **Decisión.** `escalar_variables()` (z-score o min-max) produce `ponds_escalado.csv`; el
  dataset limpio se mantiene en unidades físicas.
- **Motivo.** Las unidades físicas son las interpretables; el escalado sólo lo necesita el modelado.
  Se escala por estanque porque cada uno tiene su propio nivel de base.
- **Descartado.** Escalar el dataset principal: se perdería la interpretabilidad.
- **Pendiente para F3.** Calcular los parámetros de escalado sólo con el conjunto de
  entrenamiento, para evitar fuga de información.

### D-11 · Salida en CSV y restitución explícita de tipos
- **Contexto.** Se evaluó Parquet, que conserva tipos, pero agrega la dependencia `pyarrow`.
- **Decisión.** Exportar en CSV y restituir los tipos al recargar con `cargar_procesado()`.
- **Impacto.** Entorno más liviano; la equivalencia de tipos tras la recarga se verifica en `F2_02`.

---

## Fase 2 — Validación

### D-12 · Contratos de calidad que no se detienen en el primer fallo
- **Decisión.** `ValidadorDataset` evalúa 10 contratos y devuelve una tabla; `assert_valido()`
  lanza `ErrorValidacion` si alguno falla.
- **Impacto.** Diagnóstico completo en una pasada, con puerta de salida antes de exportar.

### D-13 · Pruebas en el notebook con datos sintéticos
- **Decisión.** Casos normales, límite y de excepción en `F2_03`, con registro exportado a
  `docs/registro_validacion.csv`.
- **Motivo.** Con datos sintéticos el resultado esperado se conoce de antemano con exactitud.
- **Descartado.** Carpeta `tests/` con pytest: se optó por mantener la evidencia visible
  dentro de los notebooks entregables.
