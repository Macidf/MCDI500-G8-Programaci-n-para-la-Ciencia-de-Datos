# Procedencia de los datos

> Generado automaticamente por `ponds.io_datos.registrar_procedencia()`.
> Ultima actualizacion: 2026-09-13 23:51:17

## Fuente

| Campo | Valor |
|---|---|
| Nombre | Pondsdata |
| Autor | Arepalli Peda Gopi |
| URL | https://www.kaggle.com/datasets/apgopi/pondsdata |
| Cobertura temporal | Febrero 2022 - Enero 2023 |
| Ubicacion | Guntur, Andhra Pradesh, India |

Registros de calidad de agua capturados por sensores IoT en tres estanques de acuicultura, con cadencia nominal de 20 minutos.

## Archivos verificados

| Archivo | Tamano (MB) | SHA-256 |
|---|---|---|
| `Aquaponds Dataset.csv` | 4.351 | `bdaea70564f5feae444ee16c7fb7196644579cbcc440088a26816c62777c5770` |
| `Fish Ponds.csv` | 4.34 | `da20a6ed5eaba1c3de9119390bdf66ccad6656dcbc7c1753e30a84f125f81726` |
| `Ponds data.csv` **(fuente primaria)** | 6.508 | `101523d7f3e99749afcaa1a37c5ce0d0d4d3f109c86a1b47d0942b01e2c92c71` |
| `Ponds.csv` | 1.065 | `9320b401d232bca3d453b9b4ce3c6667921e4f188da8dd87c01f999a51c56421` |
| `Ponds1.csv` | 6.361 | `64123f2c5eba84605651a3922f7a5f7fb700fc88c1388dedca964a18ff8df537` |

## Por que los datos crudos no se versionan

`data/raw/` esta excluido en `.gitignore`. Un repositorio academico no debe
redistribuir un dataset de terceros: la licencia pertenece al autor original en
Kaggle. En su lugar se versiona este registro, que permite a cualquier integrante
descargar el mismo archivo y **comprobar con el hash** que es identico al usado
en el analisis.

## Como reponer los datos

1. Descargar el ZIP desde https://www.kaggle.com/datasets/apgopi/pondsdata
2. Descomprimirlo dentro de `data/raw/`
3. Ejecutar los notebooks de `F2/` en orden numerico

El archivo `Ponds data.csv` es la fuente primaria del analisis. La justificacion
de esa eleccion frente a los otros CSV del ZIP esta en `docs/decisiones.md` (D-02).
