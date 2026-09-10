# -*- coding: utf-8 -*-
"""Deja en `data/` los JSON que lee el pipeline, desde el snapshot o desde el volcado.

Hay dos caminos, y el rápido es el primero:

1. **Snapshot** (recomendado, y el que usa la tarea diaria). Un único documento
   `pipeline/snapshot` de la base de datos con todo dentro. Se vuelca con
   `read_db` + `out_dir` en una sola llamada, así que el contexto se come una
   línea en vez de las ~460 del volcado documento a documento:

       python pipeline/preparar_datos.py <volcado_snapshot> data

   El script detecta el snapshot solo, esté en `<volcado>/snapshot.json`,
   en `<volcado>/pipeline/snapshot.json` o sea el propio fichero pasado.

2. **Volcado por colecciones** (respaldo, y lo que hay que usar el día que el
   snapshot no exista o se haya quedado atrás). Espera bajo el volcado:
   `ofertas/<id>.json`, `tailor/<id>.json`, `perfil/base.json`,
   `pipeline/cerradas.json` y, si están, `estado/<id>.json`, `correo/<id>.json`
   y `filtradas/<id>.json`.

En ambos casos escribe en `data/`: ofertas.json, tailor.json, perfil.json,
cerradas.json y —cuando haya datos— estado.json, correo.json y filtradas.json.
"""
import base64, gzip, json, os, sys

CLAVES_SNAPSHOT = {"ofertas", "tailor", "perfil", "cerradas"}


def _leer(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _descomprime(d):
    """El snapshot viaja comprimido para caber en un documento de 256 KB."""
    if isinstance(d, dict) and d.get("formato") == "gzip+base64" and "datos" in d:
        return json.loads(gzip.decompress(base64.b64decode(d["datos"])).decode("utf-8"))
    return d


def _busca_snapshot(ruta):
    """Devuelve el dict del snapshot, o None si por ahí no hay ninguno."""
    candidatos = [ruta,
                  os.path.join(ruta, "snapshot.json"),
                  os.path.join(ruta, "pipeline", "snapshot.json")]
    for c in candidatos:
        if os.path.isfile(c):
            try:
                d = _leer(c)
            except (ValueError, OSError):
                continue
            try:
                d = _descomprime(d)
            except Exception as exc:
                raise SystemExit(f"El snapshot {c} no se puede descomprimir: {exc}")
            if isinstance(d, dict) and CLAVES_SNAPSHOT <= set(d):
                return d
    return None


def _cargar_dir(base, nombre, obligatorio=True):
    d = os.path.join(base, nombre)
    if not os.path.isdir(d):
        if obligatorio:
            raise SystemExit(f"Falta el directorio {d} en el volcado.")
        return {}
    out = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            out[f[:-5]] = _leer(os.path.join(d, f))
    if obligatorio and not out:
        raise SystemExit(f"{d} está vacío: ¿se volcó la colección?")
    return out


def _cargar_doc(base, ruta, obligatorio=True, defecto=None):
    p = os.path.join(base, ruta)
    if not os.path.exists(p):
        if obligatorio:
            raise SystemExit(f"Falta {p} en el volcado.")
        return defecto
    return _leer(p)


def _desde_volcado(volcado):
    ofertas = _cargar_dir(volcado, "ofertas")
    return dict(
        ofertas=list(ofertas.values()),
        tailor=_cargar_dir(volcado, "tailor"),
        perfil=_cargar_doc(volcado, os.path.join("perfil", "base.json")),
        cerradas=_cargar_doc(volcado, os.path.join("pipeline", "cerradas.json")),
        estado=_cargar_dir(volcado, "estado", obligatorio=False),
        correo=_cargar_dir(volcado, "correo", obligatorio=False),
        filtradas=_cargar_dir(volcado, "filtradas", obligatorio=False),
    )


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    volcado = sys.argv[1]
    destino = sys.argv[2] if len(sys.argv) > 2 else "data"
    os.makedirs(destino, exist_ok=True)

    snap = _busca_snapshot(volcado)
    if snap is not None:
        datos = dict(snap)
        origen = "snapshot"
    else:
        datos = _desde_volcado(volcado)
        origen = "volcado por colecciones"

    ofertas = datos["ofertas"]
    if isinstance(ofertas, dict):          # el snapshot puede venir indexado por id
        ofertas = list(ofertas.values())
    tailor = datos["tailor"]

    faltan = sorted({o["id"] for o in ofertas} - set(tailor))
    if faltan:
        raise SystemExit(
            f"{len(faltan)} ofertas sin entrada en `tailor`: {faltan[:5]}… "
            "Cada oferta necesita su titular y su resumen antes de puntuar.")

    def escribe(nombre, dato):
        with open(os.path.join(destino, nombre), "w", encoding="utf-8") as fh:
            json.dump(dato, fh, ensure_ascii=False)

    escribe("ofertas.json", ofertas)
    escribe("tailor.json", tailor)
    escribe("perfil.json", datos["perfil"])
    escribe("cerradas.json", datos["cerradas"])
    for extra in ("estado", "correo", "filtradas"):
        escribe(extra + ".json", datos.get(extra) or {})

    print(f"[{origen}] {len(ofertas)} ofertas, {len(tailor)} tailor, "
          f"{len(datos.get('estado') or {})} estado, "
          f"{len(datos.get('filtradas') or {})} filtradas -> {destino}/")


if __name__ == "__main__":
    main()
