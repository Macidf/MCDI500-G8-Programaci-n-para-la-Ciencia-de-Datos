# Calidad del agua en estanques de acuicultura monitoreados por IoT

**Proyecto Transversal — MCDI500 Programación para la Ciencia de Datos — Grupo 8**
Universidad Andrés Bello (UNAB)

Avance correspondiente a las **Fases 1 y 2**: definición del proyecto, entorno reproducible,
obtención, exploración, limpieza, transformación y validación del conjunto de datos.

---

## 1. Descripción

El proyecto trabaja con el registro de sensores IoT de tres estanques de acuicultura en
Guntur (Andhra Pradesh, India), capturado cada 20 minutos entre febrero de 2022 y enero
de 2023. El archivo original presenta defectos que impiden usarlo directamente: columnas
numéricas leídas como texto por errores de Excel (`#VALUE!`), filas vacías, registros sin
hora, un fallo de sensor codificado como 0 °C e interrupciones del registro.

La Fase 2 construye un **dataset temporal limpio, tipado y validado**, sobre una rejilla
regular de 20 minutos por estanque, que sirve de base para las fases siguientes.

## 2. Conjunto de datos

| Campo | Valor |
|---|---|
| Nombre | Pondsdata |
| Autor | Arepalli Peda Gopi |
| Fuente | https://www.kaggle.com/datasets/apgopi/pondsdata |
| Archivo utilizado | `Ponds data.csv` (74.796 filas, 11 columnas) |
| Variables | nitrato, pH, amonio, temperatura, oxígeno disuelto, turbidez, manganeso |

Los datos crudos **no se versionan** (pertenecen a su autor). Su procedencia y el hash
SHA-256 de cada archivo quedan registrados en [`data/raw/README_DATOS.md`](data/raw/README_DATOS.md).

## 3. Estructura del repositorio

```
.
├── README.md
├── requirements.txt            Dependencias con versiones fijadas
├── pyrightconfig.json          Resolución del paquete src/ en el editor
├── F1/                         Fase 1 — definición del proyecto
│   └── F1_Definición.ipynb     Problemática, objetivos y entorno científico
├── F2/                         Fase 2 — notebooks ejecutables
│   ├── F2_01_Obtencion_Exploracion.ipynb
│   ├── F2_02_Limpieza_Transformacion.ipynb
│   └── F2_03_Validacion.ipynb
├── src/ponds/                  Código reutilizable importado por los notebooks
│   ├── rutas.py                Rutas, metadatos y constantes de dominio
│   ├── io_datos.py             Ingesta trazable (SHA-256) y exportación
│   ├── perfilado.py            Diagnóstico: nulos, duplicados, tipos, rangos
│   ├── limpieza.py             PipelineLimpieza (12 etapas) y escalamiento
│   ├── temporal.py             Timestamp, huecos, rejilla regular, interpolación
│   ├── validacion.py           ValidadorDataset (10 contratos de calidad)
│   └── graficos.py             Figuras con estilo homogéneo
├── data/
│   ├── raw/                    Datos originales (no versionados)
│   └── processed/              Datasets generados por F2 (no versionados)
└── docs/
    ├── decisiones.md           Bitácora de decisiones técnicas
    ├── mapa_conceptual.md      Vínculo entre el mapa conceptual y la implementación
    ├── guia_git.md             Flujo de trabajo con Git para el equipo
    ├── registro_validacion.csv Resultado de las pruebas de F2_03
    └── figuras/                Figuras generadas por los notebooks
```

**Principio de diseño:** toda la lógica vive en `src/ponds/`. Los notebooks sólo
orquestan llamadas a esas funciones y documentan los resultados; no reimplementan
transformaciones.

## 4. Instalación del entorno

Requisitos: **Python 3.10** y Git.

```bash
# 1. Clonar el repositorio
git clone https://github.com/Macidf/MCDI500-G8-Programaci-n-para-la-Ciencia-de-Datos.git
cd MCDI500-G8-Programaci-n-para-la-Ciencia-de-Datos

# 2. Crear y activar el entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt
```

Para ejecutar los notebooks se necesita además un entorno Jupyter: **JupyterLab**
(`pip install jupyterlab`) o **VS Code** con la extensión Jupyter, seleccionando el
intérprete de `.venv` como kernel (VS Code ofrece instalar `ipykernel` si falta).

Verificación rápida de la instalación:

```bash
python -c "import sys; sys.path.insert(0, 'src'); import ponds, pandas, numpy; print('OK', pandas.__version__, numpy.__version__)"
```

## 5. Obtención de los datos

1. Descargar el ZIP desde https://www.kaggle.com/datasets/apgopi/pondsdata (requiere cuenta).
2. Descomprimirlo dentro de `data/raw/` (o dejar el ZIP como `data/raw/pondsdata.zip`;
   `F2_01` lo descomprime automáticamente).
3. Comprobar que `data/raw/Ponds data.csv` existe.

## 6. Ejecución

Se comienza por la lectura de `F1/F1_Definición.ipynb`, que no contiene código. Luego, los
notebooks de F2 deben ejecutarse **en orden**, porque cada uno usa la salida del anterior.

| Orden | Notebook | Qué hace | Produce |
|---|---|---|---|
| 0 | `F1_Definición.ipynb` | Lectura previa: problemática, objetivos, entorno científico y relación con el mapa conceptual (solo markdown) | — |
| 1 | `F2_01_Obtencion_Exploracion.ipynb` | Carga trazable, diagnóstico de defectos, estructura temporal | `data/raw/README_DATOS.md`, figuras f01–f05 |
| 2 | `F2_02_Limpieza_Transformacion.ipynb` | Pipeline de 12 etapas con bitácora, escalamiento | `data/processed/ponds_limpio.csv`, `ponds_escalado.csv`, figuras f06–f07 |
| 3 | `F2_03_Validacion.ipynb` | Contratos de calidad y pruebas normales, límite y de excepción | `docs/registro_validacion.csv` |

Ejecución completa desde la línea de comandos (requiere `nbconvert`, incluido en JupyterLab):

```bash
jupyter nbconvert --to notebook --execute --inplace F2/F2_01_Obtencion_Exploracion.ipynb
jupyter nbconvert --to notebook --execute --inplace F2/F2_02_Limpieza_Transformacion.ipynb
jupyter nbconvert --to notebook --execute --inplace F2/F2_03_Validacion.ipynb
```

Uso de los módulos fuera de los notebooks:

```python
import sys; sys.path.insert(0, "src")
from ponds import io_datos, limpieza
from ponds.validacion import ValidadorDataset

pipe = limpieza.PipelineLimpieza(io_datos.cargar_crudo())
df = pipe.ejecutar()
pipe.bitacora()                      # efecto de cada etapa
ValidadorDataset(df).assert_valido() # lanza ErrorValidacion si algo falla
```

## 7. Resultado de la Fase 2

| | Crudo | Procesado |
|---|---|---|
| Filas | 74.796 | 74.854 (rejilla regular de 20 min) |
| Columnas | 11, todas texto | 22, tipadas |
| Registros descartados | — | 38 filas vacías + 51 sin hora |
| Valores imposibles anulados | — | 12 temperaturas de 0 °C |
| Contratos de calidad | — | 10 de 10 superados |

El detalle de cada decisión está en [`docs/decisiones.md`](docs/decisiones.md).

## 8. Fases del proyecto

| Fase | Contenido | Estado |
|---|---|---|
| F1 | Definición del problema, objetivos, mapa conceptual y entorno reproducible (`F1/F1_Definición.ipynb`) | Completada |
| F2 | Obtención, exploración, limpieza, transformación y validación | Completada |
| F3 | Análisis y modelado | Pendiente |
| F4 | Resultados y comunicación | Pendiente |

## 9. Equipo

| Integrante |
|---|
| Mauricio Cid Fuentes |
