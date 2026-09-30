# -*- coding: utf-8 -*-
"""Calcula la ventana de búsqueda del día (Paso 0 de TAREA_DIARIA.md).

    python pipeline/ventana.py <ultima_ejecucion ISO|-> <ventana_horas> [ahora ISO]

Imprime JSON: `desde` (ISO), `horas` (para LinkedIn `f_TPR=r<horas*3600>`) e
`infojobs` (`sinceDate`). `desde` se pasa a `filtrar.py --desde`."""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.fuentes import comun


def _iso(s):
    d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    ultima = None if argv[0] in ("-", "", "null") else _iso(argv[0])
    ahora = _iso(argv[2]) if len(argv) > 2 else datetime.datetime.now(datetime.timezone.utc)
    desde, horas = comun.ventana(ultima, float(argv[1]), ahora)
    print(json.dumps({"desde": desde.isoformat(), "horas": horas,
                      "infojobs": comun.since_infojobs(horas)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
