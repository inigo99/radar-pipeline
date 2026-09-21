# -*- coding: utf-8 -*-
"""Extractor de Manfred — portado de `browser/manfred.js` a Python.

A diferencia de LinkedIn e InfoJobs, aquí no hace falta parsear HTML ni
adivinar modalidad por regex: el listado es una API JSON pública con
salario, `remotePercentage` y ubicación ya estructurados, y la ficha trae
las técnicas exigidas con su nivel («BASIC»/«INTERMEDIATE»/«ADVANCED») y su
sección («MUST»/«COULD»/«EXTRA») — mejor señal que cualquier conteo de
palabras sobre la descripción.

Desde el 21-sep-2026 la petición la hace el agente con
`ScraplingServer.make_request` (HTTP puro, sin navegador: es una API JSON
normal, no hace falta Playwright) en vez de `fetch` dentro de una pestaña de
getmanfred.com — pero sigue corriendo en el dispositivo de Íñigo (el proxy
de salida de la nube bloquea `getmanfred.com` igual que el resto de
portales). Este script sólo procesa el JSON que ya llegó.

URLs:
  Listado: https://www.getmanfred.com/api/v2/public/offers
           ?lang=ES&onlyActive=true&currency=%E2%82%AC
  Ficha:   https://www.getmanfred.com/api/v2/public/offers/<id>
           ?lang=ES&currency=%E2%82%AC

OJO con la fecha: Manfred sólo da `updatedAt` (última actualización), no
fecha de publicación — para una oferta nunca vista antes es lo mismo."""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pipeline.fuentes import comun

LISTADO_URL = "https://www.getmanfred.com/api/v2/public/offers?lang=ES&onlyActive=true&currency=%E2%82%AC"


def ficha_url(oferta_id):
    return f"https://www.getmanfred.com/api/v2/public/offers/{oferta_id}?lang=ES&currency=%E2%82%AC"


# Nombres de técnica de Manfred -> clave de pipeline/vocabulario.md. Sólo se
# listan las que tienen equivalente real: una técnica sin mapear se descarta
# en vez de inventarse una clave nueva, porque una clave nueva vale 0 en
# evidencia_orig y hundiría la oferta sin motivo.
MAPA_TECH = {
    "python": "python", "java": "java", "javascript": "javascript", "typescript": "typescript",
    "c#": "csharp", ".net": "csharp", "go": "golang", "golang": "golang", "scala": "scala",
    "c++": "c_cpp", "php": "php", "react": "react", "react native": "react", "next.js": "react",
    "angular": "angular", "vue": "vuejs", "vue.js": "vuejs", "node.js": "nodejs", "nodejs": "nodejs",
    "nestjs": "nodejs", "express": "nodejs", "spring": "springboot", "spring boot": "springboot",
    "fastapi": "fastapi", "django": "django", "flask": "django",
    "api": "apis_rest", "rest": "apis_rest", "graphql": "apis_rest",
    "microservicios": "microservicios", "microservices": "microservicios",
    "aws": "aws", "azure": "azure", "azure cosmosdb": "cloud_datos", "gcp": "gcp", "google cloud": "gcp",
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    "ci/cd": "cicd", "jenkins": "cicd", "github actions": "cicd",
    "terraform": "terraform", "ansible": "ansible", "linux": "linux", "git": "git",
    "sql": "sql", "postgresql": "sql", "postgres": "sql", "mysql": "sql", "sql server": "sql",
    "nosql": "sql", "mongodb": "sql", "dynamodb": "sql",
    "kafka": "kafka", "spark": "spark", "pyspark": "spark", "databricks": "databricks",
    "snowflake": "snowflake", "airflow": "airflow", "dbt": "airflow",
    "mlops": "mlops", "mlflow": "mlflow", "llm": "llm", "llms": "llm",
    "genai": "genai", "generative ai": "genai", "langchain": "langchain",
    "pytorch": "pytorch_tf", "tensorflow": "pytorch_tf", "scikit-learn": "sklearn",
    "nlp": "nlp", "computer vision": "computer_vision", "opencv": "opencv",
}
WEIGHT = {
    "MUST": {"ADVANCED": 10, "INTERMEDIATE": 8, "BASIC": 7},
    "COULD": {"ADVANCED": 6, "INTERMEDIATE": 5, "BASIC": 4},
    "EXTRA": {"ADVANCED": 4, "INTERMEDIATE": 3, "BASIC": 2},
}

_RE_TAG = re.compile(r"<[^>]*>")
_RE_WS = re.compile(r"\s+")


def _strip_html(h):
    """`responsibilities` en la API real (comprobado el 21-sep-2026) llega
    como LISTA de strings markdown, no como un único HTML como asumía
    `browser/manfred.js` (`_stripHtml(j.responsibilities || ...)`: en JS
    `.replace` sobre un array no existe y esa línea revienta con TypeError
    en cualquier ficha con `responsibilities` relleno — es decir, en la
    inmensa mayoría). Aquí se admite string o lista de strings."""
    if isinstance(h, list):
        h = "\n".join(str(x) for x in h)
    return _RE_WS.sub(" ", _RE_TAG.sub(" ", h or "")).strip()


def _nombre_ciudad(l):
    """`locations` en la API real (comprobado el 21-sep-2026 con datos en vivo)
    es una lista de strings tipo "Vigo, España", no de objetos {city, town}
    como asumía `browser/manfred.js` (bug heredado: en JS `l.city` sobre un
    string da `undefined` y el join sale silenciosamente vacío, así que la
    rebaja a "local" nunca disparaba vía esta ruta; en Python es un
    AttributeError directo). Se acepta cualquiera de las dos formas por si
    Manfred cambia el formato otra vez."""
    if isinstance(l, str):
        return l
    if isinstance(l, dict):
        return l.get("city") or l.get("town") or ""
    return ""


def modalidad_de(oferta):
    """`remotePercentage` ya lo dice, con más grano que LinkedIn/InfoJobs:
    100 = remoto, 0 = presencial, en medio = híbrido. La zona local sigue
    mandando por encima de todo, salvo si ya es 100% remoto."""
    ciudades = " ".join(comun.norm(_nombre_ciudad(l))
                         for l in (oferta.get("locations") or []))
    pct = oferta.get("remotePercentage")
    pct = float(pct) if pct is not None else 0.0
    if pct >= 100:
        tipo = "remoto"
    elif pct > 0:
        tipo = "hibrido"
    else:
        tipo = "presencial"
    if comun.RE_LOCAL.search(ciudades) and tipo != "remoto":
        tipo = "local"
    return tipo


def filtrar(ofertas, ids_conocidos=None, desde=None, cfg=None):
    aceptadas = comun.modalidades_aceptadas(cfg)
    conocidos = set(str(x) for x in (ids_conocidos or []))
    cola = []
    for o in ofertas:
        oid = "mf-" + o["slug"]
        if oid in conocidos:
            continue
        if desde and o.get("updatedAt") and o["updatedAt"] < desde:
            continue
        if not comun.titulo_vale(o.get("position", "")):
            continue
        tipo = modalidad_de(o)
        if tipo not in aceptadas:
            continue
        o = dict(o)
        o["_tipo"] = tipo
        cola.append(o)
    return cola


def detallar_una(oferta_listado, ficha_json):
    j = ficha_json
    ask = _strip_html(j.get("whatTheyAskFor"))
    reqs = []
    for t in (j.get("techs") or []):
        clave = MAPA_TECH.get(comun.norm(t.get("name", "")))
        if not clave:
            continue
        w = WEIGHT.get(t.get("section"), {}).get(t.get("level"), 5)
        reqs.append([clave, w, t.get("name")])
    reqs.sort(key=lambda r: -r[1])
    out = dict(oferta_listado)
    out.update({
        "reqs": reqs,
        "idiomas": ",".join(f'{l.get("name")}:{l.get("level")}' for l in (j.get("languages") or [])),
        "anios": comun.anios(comun.norm(ask)),
        "_ask": ask,
        "_resp": _strip_html(j.get("responsibilities") or j.get("whatWillYouDo") or ""),
    })
    return out


def clasificar(detalladas):
    def fila(o):
        loc = "/".join(_nombre_ciudad(l) for l in (o.get("locations") or [])) or "remoto"
        salario = (f'{o.get("salaryFrom")}-' if o.get("salaryFrom") else "hasta ") + f'{o.get("salaryTo")}€'
        reqs_txt = ",".join(r[2] for r in (o.get("reqs") or [])[:4])
        return "|".join([
            "mf-" + o["slug"], (o.get("company") or {}).get("name", ""), o.get("position", ""),
            loc, (o.get("updatedAt") or "")[:10], o.get("_tipo", ""),
            salario, o.get("anios") or "-", reqs_txt,
        ])
    return {"filas": [fila(o) for o in detalladas], "total": len(detalladas)}


def leer(oferta, chars=900):
    txt = (oferta.get("_ask", "") + " " + oferta.get("_resp", "")).strip()
    return txt[:chars] if txt else "no encontrada (¿detallada?)"


# ---------------------------------------------------------------- CLI ----
def _leer_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _escribir_json(path, obj):
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("filtrar")
    sp.add_argument("--listado", required=True, help="JSON crudo de la API (lista)")
    sp.add_argument("--conocidos")
    sp.add_argument("--desde")
    sp.add_argument("--config")
    sp.add_argument("--out")

    sp = sub.add_parser("detallar")
    sp.add_argument("--in", dest="entrada", required=True,
                     help='JSON: [{"id":..., "ficha": {...}}, ...]')
    sp.add_argument("--ofertas", required=True, help="salida de filtrar (lista)")
    sp.add_argument("--out")

    sp = sub.add_parser("clasificar")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--out")

    sp = sub.add_parser("leer")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--id", required=True)
    sp.add_argument("--chars", type=int, default=900)

    args = p.parse_args()

    if args.cmd == "filtrar":
        ofertas = _leer_json(args.listado)
        conocidos = _leer_json(args.conocidos) if args.conocidos else []
        cfg = _leer_json(args.config) if args.config else None
        cola = filtrar(ofertas, conocidos, args.desde, cfg)
        _escribir_json(args.out, cola)
        print(f"candidatas={len(ofertas)} sobreviven={len(cola)}", file=sys.stderr)

    elif args.cmd == "detallar":
        fichas = _leer_json(args.entrada)
        ofertas = {str(o["id"]): o for o in _leer_json(args.ofertas)}
        out = []
        for f in fichas:
            base = ofertas.get(str(f["id"]))
            if base is None:
                continue
            out.append(detallar_una(base, f["ficha"]))
        _escribir_json(args.out, out)
        print(f"detalladas={len(out)}", file=sys.stderr)

    elif args.cmd == "clasificar":
        detalladas = _leer_json(args.entrada)
        res = clasificar(detalladas)
        if args.out:
            _escribir_json(args.out, res["filas"])
        else:
            print("\n".join(res["filas"]))
        print(f"total={res['total']}", file=sys.stderr)

    elif args.cmd == "leer":
        detalladas = _leer_json(args.entrada)
        o = next((x for x in detalladas
                  if ("mf-" + x.get("slug", "")) == args.id or str(x.get("id")) == args.id), None)
        print("no encontrada" if o is None else leer(o, args.chars))


if __name__ == "__main__":
    main()
