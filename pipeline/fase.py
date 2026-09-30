# -*- coding: utf-8 -*-
"""Marca el inicio de cada fase de la tarea diaria, para poder medir cuánto
tiempo y cuántos tokens se lleva cada una (30-sep-2026).

    python pipeline/fase.py <nombre>   # abre la fase <nombre> (cierra la anterior)
    python pipeline/fase.py fin        # cierra la última

Sólo guarda la hora (UTC) en `data/fases.json`. El reparto de tokens lo hace
después `coste_fases.py`, leyendo la transcripción real de la sesión y
asignando cada mensaje a la fase en la que cayó por su hora: nada de
estimaciones a ojo.

Nombres de fase que usa TAREA_DIARIA.md (se puede usar cualquier otro):
config, correo, datos, linkedin, infojobs, manfred, subagente, filtrado,
fichas, publicar, resumen.
"""
import datetime
import json
import os
import sys

DATA = os.environ.get("RADAR_DATA", "data")
RUTA = os.path.join(DATA, "fases.json")


def ahora():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def marca(nombre, cuando=None):
    fases = []
    if os.path.exists(RUTA):
        with open(RUTA, encoding="utf-8") as fh:
            fases = json.load(fh)
    fases.append({"fase": nombre, "inicio": cuando or ahora()})
    os.makedirs(DATA, exist_ok=True)
    with open(RUTA, "w", encoding="utf-8") as fh:
        json.dump(fases, fh, ensure_ascii=False, indent=1)
    return fases


def leer():
    if not os.path.exists(RUTA):
        return []
    with open(RUTA, encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    nombre = sys.argv[1]
    marca("_fin" if nombre == "fin" else nombre)
    print(f"fase {'cerrada' if nombre == 'fin' else nombre!r} · {ahora()}")
