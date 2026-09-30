# -*- coding: utf-8 -*-
"""Tiempo y tokens REALES por fase de la ejecución de hoy (30-sep-2026).

Hasta ahora `tokens_estimados` era una cifra a ojo (o `null`): la tarea no
tiene un contador de sus propios tokens. Pero la sesión sí deja su
transcripción en disco — `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/*/<id>.jsonl`,
con el `usage` de cada respuesta del modelo y su hora — y los subagentes la
suya en la subcarpeta de la sesión. Este script cruza esas horas con las
marcas de `pipeline/fase.py` (`data/fases.json`) y reparte cada mensaje a la
fase en la que cayó.

Cuatro tipos de token, que no cuestan lo mismo:
  - `entrada`: entrada nueva sin caché.
  - `cache_escritura`: entrada que se guarda en caché (≈2x la entrada).
  - `cache_lectura`: contexto ya cacheado que se relee en cada turno (≈0,1x).
    Es de lejos el más numeroso: cada llamada a una herramienta vuelve a leer
    toda la conversación anterior.
  - `salida`: lo que escribe el modelo (≈5x la entrada).
`equivalente` los pondera así, en «tokens de entrada equivalentes», que es lo
que sirve para comparar fases entre sí.

Además cuenta, por fase, las llamadas a herramientas y los caracteres que
devolvieron (lo que engorda el contexto de ahí en adelante).

Uso:
    python pipeline/coste_fases.py                  # busca la transcripción sola
    python pipeline/coste_fases.py --transcripcion ruta.jsonl
    python pipeline/coste_fases.py --json out/fases_coste.json
"""
import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fase as _fase  # noqa: E402

PESOS = {"entrada": 1.0, "cache_escritura": 2.0, "cache_lectura": 0.1, "salida": 5.0}


def _ts(s):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def buscar_transcripcion():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    candidatos = glob.glob(os.path.join(base, "projects", "*", "*.jsonl"))
    return max(candidatos, key=os.path.getmtime) if candidatos else None


def _lineas(ruta):
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            try:
                yield json.loads(linea)
            except ValueError:
                continue


def mensajes(ruta, origen="principal"):
    """Una entrada por respuesta del modelo (las líneas repetidas de una misma
    respuesta comparten `message.id`; vale la última, que lleva el `usage`
    final) y una por resultado de herramienta."""
    por_id, resultados = {}, []
    for d in _lineas(ruta):
        t = _ts(d.get("timestamp"))
        if t is None:
            continue
        m = d.get("message") or {}
        if d.get("type") == "assistant" and m.get("usage"):
            previo = por_id.get(m.get("id"), {"herramientas": []})
            herr = previo["herramientas"] + [c.get("name") for c in m.get("content") or []
                                             if isinstance(c, dict) and c.get("type") == "tool_use"]
            por_id[m.get("id")] = {"t": t, "usage": m["usage"], "herramientas": herr, "origen": origen}
        elif d.get("type") == "user" and isinstance(m.get("content"), list):
            for c in m["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    contenido = c.get("content")
                    n = len(contenido) if isinstance(contenido, str) else len(json.dumps(contenido, ensure_ascii=False))
                    resultados.append({"t": t, "chars": n, "origen": origen})
    return list(por_id.values()), resultados


def _fase_de(t, cortes):
    nombre = "arranque"
    for inicio, fase in cortes:
        if t >= inicio:
            nombre = fase
        else:
            break
    return "cierre" if nombre == "_fin" else nombre


def reparte(fases, respuestas, resultados):
    cortes = sorted((_ts(f["inicio"]), f["fase"]) for f in fases if _ts(f["inicio"]))
    orden = []
    tabla = {}

    def fila(nombre):
        if nombre not in tabla:
            orden.append(nombre)
            tabla[nombre] = {"fase": nombre, "entrada": 0, "cache_escritura": 0, "cache_lectura": 0,
                             "salida": 0, "respuestas": 0, "llamadas": {}, "chars_resultados": 0,
                             "subagente_respuestas": 0}
        return tabla[nombre]

    fila("arranque")
    for _, f in cortes:
        if f != "_fin":
            fila(f)
    for r in sorted(respuestas, key=lambda x: x["t"]):
        f = fila(_fase_de(r["t"], cortes))
        u = r["usage"]
        f["entrada"] += u.get("input_tokens") or 0
        f["cache_escritura"] += u.get("cache_creation_input_tokens") or 0
        f["cache_lectura"] += u.get("cache_read_input_tokens") or 0
        f["salida"] += u.get("output_tokens") or 0
        f["respuestas"] += 1
        if r["origen"] != "principal":
            f["subagente_respuestas"] += 1
        for h in r["herramientas"]:
            corto = h.split("__")[-1] if h else "?"
            f["llamadas"][corto] = f["llamadas"].get(corto, 0) + 1
    for x in resultados:
        fila(_fase_de(x["t"], cortes))["chars_resultados"] += x["chars"]

    # duración de cada fase = hasta el inicio de la siguiente
    for (inicio, nombre), sig in zip(cortes, cortes[1:] + [(None, None)]):
        if nombre != "_fin" and sig[0]:
            tabla[nombre]["duracion_min"] = round((sig[0] - inicio).total_seconds() / 60, 1)
    for f in tabla.values():
        f["equivalente"] = round(sum(f[k] * p for k, p in PESOS.items()))
    return [tabla[n] for n in orden if tabla[n]["respuestas"] or tabla[n].get("duracion_min")]


def calcula(ruta=None, fases=None):
    ruta = ruta or buscar_transcripcion()
    if not ruta:
        return {"transcripcion": None, "fases": [], "aviso": "no se encontró la transcripción de la sesión"}
    fases = fases if fases is not None else _fase.leer()
    resp, res = mensajes(ruta)
    carpeta = os.path.splitext(ruta)[0]
    subagentes = sorted(glob.glob(os.path.join(carpeta, "**", "*.jsonl"), recursive=True))
    for sub in subagentes:
        r2, x2 = mensajes(sub, origen=os.path.basename(sub))
        resp += r2
        res += x2
    filas = reparte(fases, resp, res)
    total = {k: sum(f[k] for f in filas) for k in list(PESOS) + ["equivalente", "respuestas", "chars_resultados"]}
    return {"transcripcion": os.path.basename(ruta), "subagentes": len(subagentes),
            "pesos": PESOS, "fases": filas, "total": total}


def _k(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".", ",")
    return f"{n/1000:.0f}k" if n >= 1000 else str(n)


def imprime(doc):
    if not doc.get("fases"):
        print(doc.get("aviso", "sin datos"))
        return
    tot = doc["total"]["equivalente"] or 1
    print(f"{'fase':<11}{'min':>6}{'resp':>6}{'salida':>9}{'lect.cache':>12}{'equiv.':>9}{'%':>5}  herramientas")
    for f in doc["fases"]:
        top = ", ".join(f"{k}×{v}" for k, v in sorted(f["llamadas"].items(), key=lambda kv: -kv[1])[:3])
        print(f"{f['fase']:<11}{f.get('duracion_min', '-'):>6}{f['respuestas']:>6}{_k(f['salida']):>9}"
              f"{_k(f['cache_lectura']):>12}{_k(f['equivalente']):>9}{100*f['equivalente']/tot:>4.0f}%  {top}")
    t = doc["total"]
    print(f"TOTAL: {t['respuestas']} respuestas · entrada {_k(t['entrada'])} · escritura caché "
          f"{_k(t['cache_escritura'])} · lectura caché {_k(t['cache_lectura'])} · salida {_k(t['salida'])} "
          f"· equivalente {_k(t['equivalente'])} · subagentes {doc['subagentes']}")


def main(argv):
    ruta = argv[argv.index("--transcripcion") + 1] if "--transcripcion" in argv else None
    doc = calcula(ruta)
    if "--json" in argv:
        destino = argv[argv.index("--json") + 1]
        os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
    imprime(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
