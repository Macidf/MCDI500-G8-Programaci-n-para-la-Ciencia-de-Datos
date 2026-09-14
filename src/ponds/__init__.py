"""
Paquete `ponds` - Proyecto Transversal MCDI500 (G8)
==================================================

Modulos reutilizables para el analisis del comportamiento temporal de la calidad
del agua en tres estanques de acuicultura monitoreados por IoT.

La logica de procesamiento vive aqui; los notebooks de la Fase 2 solo orquestan
llamadas a estas funciones. Esta separacion permite (a) reutilizar el codigo entre
notebooks sin duplicarlo, (b) versionarlo de forma trazable en Git y (c) validarlo
de manera independiente del entorno de ejecucion interactivo.

Modulos
-------
rutas       : rutas del proyecto, metadatos y constantes de dominio.
io_datos    : ingesta trazable del dataset crudo y escritura del procesado.
perfilado   : funciones de diagnostico y exploracion (Fase 2 - exploracion).
limpieza    : pipeline de depuracion (Fase 2 - limpieza).
temporal    : construccion del eje temporal y variables derivadas.
validacion  : contratos de calidad del dataset resultante.
graficos    : figuras con estilo homogeneo.
"""

from ponds import rutas

__version__ = "0.2.0"
__all__ = [
    "rutas",
    "io_datos",
    "perfilado",
    "limpieza",
    "temporal",
    "validacion",
    "graficos",
]
