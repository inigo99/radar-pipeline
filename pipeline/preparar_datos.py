# -*- coding: utf-8 -*-
"""Convierte el volcado de la base de datos del artifact en los JSON que lee el pipeline.

La tarea diaria vuelca las colecciones con `read_db` + `out_dir`, que deja un fichero
por documento. Este script los junta en los cuatro ficheros que espera `datos.py`:

    python preparar_datos.py <directorio_del_volcado> [<directorio_data>]

Espera encontrar bajo el volcado:
    ofertas/<id>.json        tailor/<id>.json
    perfil/base.json         pipeline/cerradas.json

y escribe en `data/` (o en el directorio que se le pase):
    ofertas.json   tailor.json   perfil.json   cerradas.json
"""
import json, os, sys

def _cargar_dir(base, nombre):
    d = os.path.join(base, nombre)
    if not os.path.isdir(d):
        raise SystemExit(f"Falta el directorio {d} en el volcado.")
    out = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                out[f[:-5]] = json.load(fh)
    if not out:
        raise SystemExit(f"{d} está vacío: ¿se volcó la colección?")
    return out

def _cargar_doc(base, ruta):
    p = os.path.join(base, ruta)
    if not os.path.exists(p):
        raise SystemExit(f"Falta {p} en el volcado.")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)

def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    volcado = sys.argv[1]
    destino = sys.argv[2] if len(sys.argv) > 2 else "data"
    os.makedirs(destino, exist_ok=True)

    ofertas = _cargar_dir(volcado, "ofertas")
    tailor  = _cargar_dir(volcado, "tailor")
    perfil  = _cargar_doc(volcado, os.path.join("perfil", "base.json"))
    cerradas = _cargar_doc(volcado, os.path.join("pipeline", "cerradas.json"))

    faltan = sorted(set(ofertas) - set(tailor))
    if faltan:
        raise SystemExit(
            f"{len(faltan)} ofertas sin entrada en `tailor`: {faltan[:5]}… "
            "Cada oferta necesita su titular y su resumen antes de puntuar.")

    def escribe(nombre, dato):
        with open(os.path.join(destino, nombre), "w", encoding="utf-8") as fh:
            json.dump(dato, fh, ensure_ascii=False)

    escribe("ofertas.json", list(ofertas.values()))
    escribe("tailor.json", tailor)
    escribe("perfil.json", perfil)
    escribe("cerradas.json", cerradas)
    print(f"{len(ofertas)} ofertas, {len(tailor)} tailor, perfil y cerradas -> {destino}/")

if __name__ == "__main__":
    main()
