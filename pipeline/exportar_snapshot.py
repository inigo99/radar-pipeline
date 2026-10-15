# -*- coding: utf-8 -*-
"""Arma el snapshot que la tarea diaria escribe en `pipeline/snapshot`.

Un único documento con todo lo que el pipeline necesita para arrancar mañana,
en vez de ~460 documentos sueltos. Se ejecuta al final de la ejecución, cuando
`data/` ya tiene las ofertas nuevas:

    python pipeline/exportar_snapshot.py            # -> out/snapshot.json

y ese fichero se sube con
`write_db` (`db_op:"set"`, `collection:"pipeline"`, `doc_id:"snapshot"`,
`file_path:"out/snapshot.json"`), así que su contenido tampoco pasa por el
contexto.

Va **comprimido**: el JSON en claro pasa de los 360 KB y el límite por documento
de la base de datos son 256 KB. El documento es
`{formato:"gzip+base64", generado, n_ofertas, datos:"<base64>"}` y
`preparar_datos.py` lo descomprime solo. Si el base64 no cabe en un documento
se parte en trozos: `snapshot.json` lleva `partes` y el primero, y
`snapshot_1.json`, `snapshot_2.json`… el resto (`{datos}`), que se suben a
`pipeline/snapshot_1`, `pipeline/snapshot_2`… (15 oct 2026: el 14 oct pasó de
256 KB, abortó, y el snapshot se quedó congelado perdiendo ofertas).

El snapshot es **caché, no fuente de verdad**: las colecciones `ofertas`,
`tailor`, `estado` y `correo` siguen mandando, porque el dashboard escribe
directamente en ellas cuando Íñigo cambia una fase o descarta una oferta. Por
eso lleva `generado` y `n_ofertas`: si el recuento no cuadra con la colección,
se vuelve al volcado por colecciones y se regenera.
"""
import base64, datetime, gzip, json, os, sys

TROZO = 240_000   # caracteres de base64 por documento (límite: 256 KB)

DATA = os.environ.get("RADAR_DATA", "data")
SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join("out", "snapshot.json")


def _leer(nombre, defecto=None):
    p = os.path.join(DATA, nombre)
    if not os.path.exists(p):
        if defecto is None:
            raise SystemExit(f"Falta {p}: ejecuta antes preparar_datos.py.")
        return defecto
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ofertas = _leer("ofertas.json")
    snap = {
        "generado": datetime.datetime.now(datetime.timezone.utc)
                    .isoformat(timespec="seconds").replace("+00:00", "Z"),
        "n_ofertas": len(ofertas),
        "ofertas": ofertas,
        "tailor": _leer("tailor.json"),
        "perfil": _leer("perfil.json"),
        "cerradas": _leer("cerradas.json"),
        "estado": _leer("estado.json", {}),
        "correo": _leer("correo.json", {}),
        "filtradas": _leer("filtradas.json", {}),
    }
    crudo = json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    b64 = base64.b64encode(gzip.compress(crudo, 9)).decode("ascii")
    trozos = [b64[i:i + TROZO] for i in range(0, len(b64), TROZO)]
    doc = {
        "formato": "gzip+base64",
        "generado": snap["generado"],
        "n_ofertas": snap["n_ofertas"],
        "partes": len(trozos),
        "datos": trozos[0],
    }
    os.makedirs(os.path.dirname(SALIDA) or ".", exist_ok=True)
    raiz, ext = os.path.splitext(SALIDA)
    for i, d in enumerate([doc] + [{"datos": t} for t in trozos[1:]]):
        with open(SALIDA if i == 0 else f"{raiz}_{i}{ext}", "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)

    print(f"snapshot -> {SALIDA} ({snap['n_ofertas']} ofertas, "
          f"{len(snap['filtradas'])} filtradas, {len(crudo)//1024} KB en claro, "
          f"{len(b64)//1024} KB comprimido, {len(trozos)} documento(s))")
    if len(trozos) > 1:
        print(f"SUBE TAMBIÉN {', '.join(f'{os.path.basename(raiz)}_{i}{ext}' for i in range(1, len(trozos)))} "
              f"a pipeline/snapshot_1… (mismo nombre sin .json)")


if __name__ == "__main__":
    main()
