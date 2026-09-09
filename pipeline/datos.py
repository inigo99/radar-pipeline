# -*- coding: utf-8 -*-
"""Carga de datos del radar.

El repositorio no contiene datos personales: las ofertas, el perfil y el CV
viven en la base de datos del artifact del dashboard, y la tarea diaria los
vuelca como JSON en el directorio `data/` antes de ejecutar el pipeline.

Ficheros esperados en `data/` (los escribe la tarea con `read_db`):
  ofertas.json      lista de ofertas            -> colección `ofertas`
  tailor.json       {id: {familia,titular,resumen}} -> colección `tailor`
  perfil.json       perfil, CV y candado        -> documento `perfil/base`
  cerradas.json     ofertas retiradas           -> documento `pipeline/cerradas`
  resultado.json    salida de puntuar.py (se genera durante la ejecución)
"""
import json, os

DATA = os.environ.get("RADAR_DATA", "data")

def _leer(nombre, defecto=None):
    ruta = os.path.join(DATA, nombre)
    if not os.path.exists(ruta):
        if defecto is not None:
            return defecto
        raise SystemExit(
            f"Falta {ruta}. Vuelca la colección correspondiente de la base de "
            f"datos del artifact antes de ejecutar el pipeline (ver README)."
        )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

OFERTAS = sorted(_leer("ofertas.json"), key=lambda o: o["id"])  # orden estable entre ejecuciones
TAILOR  = _leer("tailor.json")
PERFIL  = _leer("perfil.json")
CERRADAS = _leer("cerradas.json", {"lista": []})

# `reqs` viaja como listas en JSON; el pipeline las trata como secuencias.
for _o in OFERTAS:
    _o["reqs"] = [list(r) for r in _o.get("reqs", [])]
