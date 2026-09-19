# -*- coding: utf-8 -*-
"""Puntúa cada oferta contra el CV: encaje original, encaje adaptado, familia,
prioridad y foco.

    python pipeline/puntuar.py            # -> data/resultado.json

`score_orig` es el encaje con el CV tal cual está hoy; `score_adap` es el
encaje si el CV adaptado (`tailor/<id>`) saca a un bullet o al resumen los
términos que ya tiene pero sólo lista en competencias -- nunca sube un término
con evidencia 0 (el candado de `perfil.py`). `huecos` y `fuertes` son las
etiquetas más relevantes de cada lado, para el panel de la oferta.

Consistente con el resto del pipeline: respeta `RADAR_DATA` (por defecto
`data`) y escribe siempre en UTF-8 explícito.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ofertas import OFERTAS
from perfil import ORIG, prominencia_adaptada
from tailor import T
from aprendizaje import peso_familia, clasifica
from foco import calcula as calcula_foco

DATA = os.environ.get("RADAR_DATA", "data")


def score(o):
    """(score_orig, score_adap, huecos, fuertes) en porcentaje sobre el peso total."""
    tot = sum(w for _, w, _ in o["reqs"])
    orig = sum(w * ORIG.get(k, 0.0) for k, w, _ in o["reqs"])
    adap = sum(w * prominencia_adaptada(k, set(o["surfaced"])) for k, w, _ in o["reqs"])
    huecos = sorted(((l, w) for k, w, l in o["reqs"] if ORIG.get(k, 0.0) == 0.0),
                     key=lambda x: -x[1])
    fuertes = sorted(((l, w) for k, w, l in o["reqs"] if ORIG.get(k, 0.0) >= 0.7),
                      key=lambda x: -x[1])
    return round(100 * orig / tot, 1), round(100 * adap / tot, 1), huecos, fuertes


def brecha_aprendizaje(o):
    """Huecos reales, clasificados por si merece la pena repasarlos antes de
    una posible entrevista. No toca el CV ni la carta -- ver aprendizaje.md."""
    items = sorted(((k, w, l) for k, w, l in o["reqs"] if ORIG.get(k, 0.0) == 0.0),
                    key=lambda x: -x[1])
    out = []
    for k, w, l in items[:10]:
        nivel, nota = clasifica(k)
        out.append(dict(clave=k, etiqueta=l, peso=w, nivel=nivel, nota=nota))
    return out


def puntuar(ofertas):
    res = []
    for o in ofertas:
        so, sa, huecos, fuertes = score(o)
        familia = (T.get(o["id"]) or {}).get("familia", "backend")
        prioridad = round(sa * peso_familia(familia), 1)
        foco, dias, motivo = calcula_foco(o, prioridad)
        res.append(dict(
            o,
            score_orig=so, score_adap=sa,
            delta=round(sa - so, 1),
            mejora_pct=round(100 * (sa - so) / so, 1) if so else 0,
            huecos=[h[0] for h in huecos[:5]],
            fuertes=[f[0] for f in fuertes[:5]],
            sal_medio=(o["sal_min"] + o["sal_max"]) // 2,
            url=o.get("url_apply") or f"https://www.linkedin.com/jobs/view/{o['id']}/",
            familia=familia,
            prioridad=prioridad,
            foco=foco, dias=dias, motivo_foco=motivo,
            brecha=brecha_aprendizaje(o),
        ))
    # El `foco` se guarda para que resultado.json salga ya ordenado y para
    # poder mirarlo por consola. El dashboard NO lo hereda: lo recalcula al
    # cargar la página (`refrescaFoco()`), porque depende de la fecha de hoy.
    # Ver foco.py.
    res.sort(key=lambda r: -r["foco"])
    return res


def _imprime(res):
    print(f"{'EMPRESA':<28}{'PUESTO':<44}{'ORIG':>6}{'ADAP':>7}{'Δ':>6}  {'SALARIO':>17}")
    for r in res:
        print(f"{r['empresa'][:27]:<28}{r['puesto'][:43]:<44}{r['score_orig']:>6}"
              f"{r['score_adap']:>7}{r['delta']:>+6}  "
              f"{r['sal_min'] // 1000:>6}k-{r['sal_max'] // 1000}k {r['sal_origen'][:4]}")


def main():
    res = puntuar(OFERTAS)
    ruta = os.path.join(DATA, "resultado.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    _imprime(res)


if __name__ == "__main__":
    main()
