# -*- coding: utf-8 -*-
"""Lee el historial de ejecuciones acumulado (colección `historial`) y saca un
resumen de tendencia: duración, cobertura por fuente, cuánto se descarta y por
qué. Pensado para decidir con datos en vez de a ojo -- la baja de JSearch se
decidió con una auditoría puntual del prompt, no con esto, porque esto no
existía todavía.

Uso:

    python pipeline/resumen_historial.py <volcado>

`<volcado>` puede ser:

  - un fichero JSON con una lista de documentos (lo que devuelve `query` sobre
    la colección `historial`), o un dict `{doc_id: documento}`;
  - un directorio con `historial/<fecha>.json` (o `<fecha>.json` directamente
    dentro), es decir, el mismo volcado por colecciones documento a documento
    que ya usa `preparar_datos.py` para el resto de la base de datos.

No escribe nada: sólo imprime. Cada documento es el que deja
`registrar_ejecucion.py` en `out/historial.json` cada día.
"""
import json
import os
import sys


def _carga(ruta):
    if os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as fh:
            datos = json.load(fh)
        if isinstance(datos, list):
            return datos
        if isinstance(datos, dict):
            return list(datos.values())
        raise SystemExit(f"{ruta}: formato no reconocido (se esperaba lista o dict de documentos)")

    if os.path.isdir(ruta):
        for base in (os.path.join(ruta, "historial"), ruta):
            if os.path.isdir(base):
                docs = []
                for nombre in sorted(os.listdir(base)):
                    if nombre.endswith(".json"):
                        with open(os.path.join(base, nombre), encoding="utf-8") as fh:
                            docs.append(json.load(fh))
                if docs:
                    return docs
        raise SystemExit(f"No se encontró ningún documento de historial bajo {ruta}")

    raise SystemExit(f"{ruta} no existe")


def resume(docs):
    """Agregados sobre una lista de documentos de `historial`, ordenados por fecha."""
    docs = sorted((d for d in docs if d.get("fecha")), key=lambda d: d["fecha"])

    duraciones = [d["duracion_min"] for d in docs if isinstance(d.get("duracion_min"), (int, float))]
    ofertas_nuevas = [d.get("contadores", {}).get("ofertas_nuevas", 0) for d in docs]
    podadas = [d.get("contadores", {}).get("podadas", 0) for d in docs]
    duplicadas = [d.get("contadores", {}).get("duplicadas", 0) for d in docs]
    candidatas = [d.get("contadores", {}).get("candidatas_a_dedupe", 0) for d in docs]

    cobertura = {}
    omision = {}
    for d in docs:
        for f in d.get("fuentes_cubiertas") or []:
            cobertura[f] = cobertura.get(f, [0, 0])
            cobertura[f][0] += 1
        for o in d.get("fuentes_omitidas") or []:
            f = o.get("fuente", "?")
            omision.setdefault(f, []).append(o.get("motivo", "(sin motivo)"))
    for f in cobertura:
        cobertura[f][1] = len(docs)

    total_dup = sum(duplicadas)
    total_cand = sum(candidatas) or 1
    tokens = [d.get("tokens_estimados") for d in docs if isinstance(d.get("tokens_estimados"), (int, float))]

    return {
        "n_ejecuciones": len(docs),
        "duracion_media_min": round(sum(duraciones) / len(duraciones), 1) if duraciones else None,
        "ofertas_nuevas_media": round(sum(ofertas_nuevas) / len(docs), 1) if docs else 0,
        "podadas_total": sum(podadas),
        "tasa_duplicados": round(total_dup / total_cand, 2),
        "cobertura_por_fuente": {f: f"{v[0]}/{v[1]}" for f, v in sorted(cobertura.items())},
        "motivos_omision": omision,
        "tokens_estimados_media": round(sum(tokens) / len(tokens)) if tokens else None,
        "docs": docs,
    }


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    docs = _carga(argv[0])
    if not docs:
        print("Sin documentos de historial todavía.")
        return 0

    r = resume(docs)
    print(f"{r['n_ejecuciones']} ejecución(es) de {docs[0]['fecha']} a {docs[-1]['fecha']}")
    print(f"  duración media: {r['duracion_media_min']} min" if r["duracion_media_min"] is not None
          else "  duración media: (sin datos)")
    print(f"  ofertas nuevas por ejecución (media): {r['ofertas_nuevas_media']}")
    print(f"  podadas por antigüedad (total del periodo): {r['podadas_total']}")
    print(f"  tasa de duplicados sobre lo llevado a dedupe: {r['tasa_duplicados']:.0%}")
    if r["tokens_estimados_media"] is not None:
        print(f"  tokens estimados por ejecución (media): {r['tokens_estimados_media']}")
    print("  cobertura por fuente (ejecuciones en que apareció / total):")
    for f, cob in r["cobertura_por_fuente"].items():
        print(f"    · {f}: {cob}")
    if r["motivos_omision"]:
        print("  omisiones por fuente (motivo más repetido primero):")
        for f, motivos in r["motivos_omision"].items():
            from collections import Counter
            top = Counter(motivos).most_common(3)
            print(f"    · {f}: " + ", ".join(f"{m} ({n}×)" for m, n in top))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
