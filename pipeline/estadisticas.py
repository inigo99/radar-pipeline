# -*- coding: utf-8 -*-
"""Acumulador de contadores de la ejecución de hoy, para poder medir el coste
real de la tarea diaria en vez de auditarlo a ojo.

Creado el 19-sep-2026: hasta entonces no había ninguna instrumentación del
coste de una ejecución más allá de `fired_at`/`finished_at` del trigger (hora
de inicio y fin, nada de fases). Las decisiones sobre qué fuente merece la
pena (JSearch, Himalayas/WWR/RemoteOK...) se tomaban con una "auditoría
estructural" del prompt, no con datos: no había manera de saber, por ejemplo,
cuánto tardaba cada fase o qué proporción de lo recogido acababa duplicado.

Varios scripts del pipeline (`poda_antiguedad.py`, `filtrar.py`, `dedupe.py`)
llaman a `acumula()` con sus propios contadores; `registrar_ejecucion.py` los
junta al final con lo que sólo sabe el agente (fuentes cubiertas/omitidas,
duración, fichas completas leídas) y deja `out/historial.json`, listo para
subir a la colección `historial` con `write_db`.

Cada script es un proceso Python independiente (la tarea los llama uno detrás
de otro, nunca en paralelo), así que la acumulación es "leer todo el fichero,
añadir la clave, escribir todo el fichero" -- sin bloqueos, porque no hace
falta: nunca hay dos scripts escribiendo a la vez.
"""
import json
import os

DATA = os.environ.get("RADAR_DATA", "data")
RUTA = os.path.join(DATA, "estadisticas_ejecucion.json")


def acumula(**contadores):
    """Suma (no reemplaza) cada contador con lo que ya hubiera de hoy.

    Sumar en vez de reemplazar importa cuando un mismo script se corre más de
    una vez en una ejecución (p.ej. `filtrar.py` una vez por lote de fuentes).
    """
    actual = {}
    if os.path.exists(RUTA):
        with open(RUTA, encoding="utf-8") as fh:
            actual = json.load(fh)
    for clave, valor in contadores.items():
        actual[clave] = actual.get(clave, 0) + valor
    os.makedirs(DATA, exist_ok=True)
    with open(RUTA, "w", encoding="utf-8") as fh:
        json.dump(actual, fh, ensure_ascii=False, indent=1)
    return actual


def leer():
    if not os.path.exists(RUTA):
        return {}
    with open(RUTA, encoding="utf-8") as fh:
        return json.load(fh)
