# -*- coding: utf-8 -*-
"""Extractor de LinkedIn — portado de `browser/linkedin.js` a Python. Desde el
21-sep-2026 el HTML lo trae Scrapling (`ScraplingServer.fetch`/`bulk_fetch`,
`real_chrome:true`), no una pestaña de linkedin.com — así que ya no hace
falta pegar código ni estar en el propio dominio (era sólo para saltarse la
CSP y el CORS). Este script sólo analiza lo que Scrapling ya descargó.

Flujo típico de una ejecución (ver TAREA_DIARIA.md, Pasos 2-4):

  1. `consultas`   -> URLs a pedir con Scrapling (el agente las pasa a
                      `bulk_fetch`, extraction_type "html", real_chrome:true).
  2. `parsear`     -> junta el HTML de esas páginas en un diccionario de
                      ofertas (id, título, empresa, ubicación, fecha).
  3. `filtrar`     -> criba por título, fecha y empresas excluidas: de ~150
                      candidatas a ~20 fichas que merece la pena pedir.
  4. (Scrapling pide la ficha de cada superviviente: extraction_type "html")
  5. `detallar`    -> modalidad, ámbito, salario, años y términos de
                      vocabulario, todo de la misma lectura.
  6. `clasificar`  -> reparte en dentro/revisar/fuera según
                      `buscar_remoto`/`buscar_hibrido`/`buscar_presencial`.
  7. `snippets`/`leer` -> para redactar los `reqs` y el `resumen` del paso 6.

El endpoint de invitado (`jobs-guest/.../search`) NO se puede parsear con un
parser de DOM normal: hay que partir por `<li` y sacar los campos con regex
sobre el HTML crudo — eso no ha cambiado, es una característica del propio
HTML de LinkedIn, no del método de descarga.
"""
import argparse
import json
import os
import re
import sys

# Permite `python pipeline/fuentes/linkedin.py ...` desde la raíz del repo
# (la convención de todo el pipeline) sin instalar el paquete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pipeline.fuentes import comun, vocabulario

GUEST = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
FICHA = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/"
FICHA_COMPLETA = "https://www.linkedin.com/jobs/view/"

_RE_ID = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"')
_RE_TITULO = re.compile(r'<h3[^>]*base-search-card__title[^>]*>([\s\S]*?)</h3>')
_RE_EMPRESA = re.compile(r'hidden-nested-link[^>]*>([\s\S]*?)</a>')
_RE_UBICACION = re.compile(r'job-search-card__location[^>]*>([\s\S]*?)</span>')
_RE_FECHA = re.compile(r'datetime="([\d-]+)"')

# Ver linkedin.js: la insignia («Remoto»/«Híbrido»/«Presencial») sólo vive en
# la página completa (jobs/view/<id>), no en la ficha ligera del endpoint de
# invitado, y sólo se pide para las pocas ofertas que quedan en
# `remoto_sin_confirmar` tras leer la descripción — no para todas.
_RE_ETIQUETA = re.compile(r'>\s*(Remoto|H[ií]brido|Presencial|Remote|Hybrid|On-?site)\s*<')
_MAPA_ETIQUETA = {
    "remoto": "remoto", "remote": "remoto",
    "hibrido": "hibrido", "hybrid": "hibrido",
    "presencial": "presencial", "on-site": "presencial", "onsite": "presencial",
}


def construir_consultas(titulos, location="Spain", horas=24, paginas=2, remoto=False):
    """Igual que `li.buscar()` en construir las URLs, sin hacer la petición:
    eso lo hace Scrapling. `paginas` = nº de páginas de 10 resultados por
    título (start=0,10,20...)."""
    out = []
    for t in titulos:
        for p in range(paginas):
            etiqueta = ("R" if remoto else "L") + ("2" if p else "") + "|" + t
            qs = {
                "keywords": t,
                "location": location,
                "f_TPR": "r" + str(horas * 3600),
            }
            if remoto:
                qs["f_WT"] = "2"
            qs["start"] = str(p * 10)
            from urllib.parse import urlencode
            out.append({"etiqueta": etiqueta, "url": GUEST + urlencode(qs)})
    return out


def parsear(html, etiqueta, jobs=None):
    """Trocea por `<li` y saca los campos con regex sobre el HTML crudo (el
    endpoint de invitado no se puede parsear con DOMParser/BeautifulSoup de
    forma fiable). Devuelve (jobs actualizado, nº de ofertas nuevas)."""
    jobs = jobs if jobs is not None else {}
    n = 0
    for trozo in html.split("<li"):
        m_id = _RE_ID.search(trozo)
        if not m_id:
            continue
        jid = m_id.group(1)
        if jid in jobs:
            continue
        limpia = lambda mm: comun.texto(mm.group(1)) if mm else ""
        jobs[jid] = {
            "id": jid,
            "titulo": limpia(_RE_TITULO.search(trozo)),
            "empresa": limpia(_RE_EMPRESA.search(trozo)),
            "ubicacion": limpia(_RE_UBICACION.search(trozo)),
            "fecha": (_RE_FECHA.search(trozo).group(1) if _RE_FECHA.search(trozo) else ""),
            "q": etiqueta,
        }
        n += 1
    return jobs, n


def filtrar(jobs, conocidos=None, desde=None, excluir_empresas=None):
    """Criba por título, por fecha y contra los ids ya conocidos. Es lo que
    baja de ~150 candidatas a ~20 fichas que merezca la pena pedir."""
    conocidos = set(str(x) for x in (conocidos or []))
    malas = [comun.norm(e) for e in (excluir_empresas or []) if e]
    cola = []
    for j in jobs.values():
        if j["id"] in conocidos:
            continue
        if desde and j.get("fecha") and j["fecha"] < desde:
            continue
        if not comun.titulo_vale(j["titulo"]):
            continue
        e = comun.norm(j["empresa"])
        if any(e == m or (len(m) > 4 and m in e) for m in malas):
            continue
        cola.append(j)
    return cola


def detallar_una(job, html_ficha):
    """Ficha ligera del endpoint de invitado -> campos calculados. `job` es
    la entrada del listado (para ubicacion/q); `html_ficha` es lo que
    Scrapling trajo de `FICHA + id`."""
    txt = comun.texto(html_ficha)
    tn = comun.norm(txt)
    etiqueta_remoto = job.get("q", "").startswith("R")
    mod = comun.modalidad(tn, comun.norm(job.get("ubicacion", "")), etiqueta_remoto)
    out = dict(job)
    out.update({
        "modalidad": mod,
        "ambito": comun.ambito(tn),
        "salario": comun.salario(txt),
        "anios": comun.anios(tn),
        "largo": len(txt),
        "terminos": vocabulario.cuenta_terminos(tn),
        "_tn": tn,
    })
    return out


def resolver_etiqueta(html_pagina_completa):
    """Lee la insignia de modalidad de la página completa (`jobs/view/<id>`),
    sólo para desambiguar `remoto_sin_confirmar`. Se lee de los primeros
    60.000 caracteres (zona de cabecera, antes de "empleos similares", que
    repite la palabra para OTRAS ofertas)."""
    cabecera = (html_pagina_completa or "")[:60000]
    m = _RE_ETIQUETA.search(cabecera)
    if not m:
        return None
    return _MAPA_ETIQUETA.get(comun.norm(m.group(1)))


def clasificar(detalladas, cfg=None):
    aceptadas = comun.modalidades_aceptadas(cfg)
    dentro, fuera, revisar = [], [], []
    for j in detalladas:
        if j.get("cerrada"):
            fuera.append(j)
            continue
        t = j["modalidad"]["tipo"]
        if t not in aceptadas:
            fuera.append(j)
            continue
        (revisar if t == "remoto_sin_confirmar" else dentro).append(j)

    def fila(j):
        return "|".join([
            j["id"], j["empresa"], j["titulo"], j["ubicacion"], j.get("fecha", ""),
            j["modalidad"]["tipo"], j.get("salario") or "-", j.get("anios") or "-",
            (j.get("ambito", {}).get("restriccion") or "")[:60],
            (j["modalidad"]["frases"][0] if j["modalidad"]["frases"] else "")[:90],
        ])

    filas = [fila(j) for j in dentro + revisar]
    return {"filas": filas, "dentro": len(dentro), "revisar": len(revisar), "fuera": len(fuera)}


def snippets(job, max_terms=10):
    hits = job.get("terminos") or vocabulario.cuenta_terminos(job.get("_tn", "")) or []
    if not hits:
        return "(sin términos de vocabulario — usar leer())"
    return "\n".join(f'{h[0]} ({h[1]}x): "{h[2]}"' for h in hits[:max_terms])


def leer(job, desde=0, chars=900):
    tn = job.get("_tn", "")
    if not tn:
        return "no encontrada (¿detallada?)"
    return tn[desde:desde + chars]


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

    sp = sub.add_parser("consultas")
    sp.add_argument("--titulos", required=True, help="JSON: lista de títulos")
    sp.add_argument("--location", default="Spain")
    sp.add_argument("--horas", type=int, default=24)
    sp.add_argument("--paginas", type=int, default=2)
    sp.add_argument("--remoto", action="store_true")
    sp.add_argument("--out")

    sp = sub.add_parser("parsear")
    sp.add_argument("--in", dest="entrada", required=True,
                     help='JSON: [{"etiqueta":..., "html":...}, ...]')
    sp.add_argument("--out")

    sp = sub.add_parser("filtrar")
    sp.add_argument("--jobs", required=True)
    sp.add_argument("--conocidos", help="JSON: lista de ids")
    sp.add_argument("--desde")
    sp.add_argument("--excluir-empresas", help="JSON: lista de nombres")
    sp.add_argument("--out")

    sp = sub.add_parser("detallar")
    sp.add_argument("--in", dest="entrada", required=True,
                     help='JSON: [{"id":..., "html":...}, ...] (fichas)')
    sp.add_argument("--jobs", required=True, help="jobs.json del paso parsear")
    sp.add_argument("--out")

    sp = sub.add_parser("resolver-etiquetas")
    sp.add_argument("--in", dest="entrada", required=True,
                     help="JSON de detallar, a corregir in place")
    sp.add_argument("--paginas", required=True,
                     help='JSON: [{"id":..., "html":...}, ...] (jobs/view completas)')
    sp.add_argument("--out")

    sp = sub.add_parser("clasificar")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--config", help="config/filtros como JSON")
    sp.add_argument("--out")

    sp = sub.add_parser("snippets")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--id", required=True)
    sp.add_argument("--max-terms", type=int, default=10)

    sp = sub.add_parser("leer")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--id", required=True)
    sp.add_argument("--desde", type=int, default=0)
    sp.add_argument("--chars", type=int, default=900)

    args = p.parse_args()

    if args.cmd == "consultas":
        titulos = _leer_json(args.titulos)
        out = construir_consultas(titulos, args.location, args.horas, args.paginas, args.remoto)
        _escribir_json(args.out, out)

    elif args.cmd == "parsear":
        entrada = _leer_json(args.entrada)
        jobs = {}
        total_nuevas = 0
        for pagina in entrada:
            jobs, n = parsear(pagina["html"], pagina["etiqueta"], jobs)
            total_nuevas += n
        _escribir_json(args.out, jobs)
        print(f"TOTAL={len(jobs)}", file=sys.stderr)

    elif args.cmd == "filtrar":
        jobs = _leer_json(args.jobs)
        conocidos = _leer_json(args.conocidos) if args.conocidos else []
        excluir = _leer_json(args.excluir_empresas) if args.excluir_empresas else []
        cola = filtrar(jobs, conocidos, args.desde, excluir)
        _escribir_json(args.out, cola)
        print(f"candidatas={len(jobs)} sobreviven={len(cola)}", file=sys.stderr)

    elif args.cmd == "detallar":
        fichas = _leer_json(args.entrada)
        jobs = _leer_json(args.jobs)
        out = []
        for f in fichas:
            job = jobs.get(f["id"], {"id": f["id"], "titulo": "", "empresa": "",
                                      "ubicacion": "", "fecha": "", "q": ""})
            out.append(detallar_una(job, f["html"]))
        _escribir_json(args.out, out)
        print(f"detalladas={len(out)}", file=sys.stderr)

    elif args.cmd == "resolver-etiquetas":
        detalladas = _leer_json(args.entrada)
        paginas = {x["id"]: x["html"] for x in _leer_json(args.paginas)}
        for j in detalladas:
            if j["modalidad"]["tipo"] != "remoto_sin_confirmar":
                continue
            html = paginas.get(j["id"])
            if not html:
                continue
            et = resolver_etiqueta(html)
            if et:
                j["modalidad"]["frases"] = [f"etiqueta de LinkedIn: {et}"] + j["modalidad"]["frases"]
                j["modalidad"]["tipo"] = et
        _escribir_json(args.out, detalladas)

    elif args.cmd == "clasificar":
        detalladas = _leer_json(args.entrada)
        cfg = _leer_json(args.config) if args.config else None
        res = clasificar(detalladas, cfg)
        if args.out:
            _escribir_json(args.out, res["filas"])
        else:
            print("\n".join(res["filas"]))
        print(f"dentro={res['dentro']} revisar={res['revisar']} fuera={res['fuera']}",
              file=sys.stderr)

    elif args.cmd == "snippets":
        detalladas = _leer_json(args.entrada)
        job = next((j for j in detalladas if j["id"] == args.id), None)
        print("no encontrada" if job is None else snippets(job, args.max_terms))

    elif args.cmd == "leer":
        detalladas = _leer_json(args.entrada)
        job = next((j for j in detalladas if j["id"] == args.id), None)
        print("no encontrada" if job is None else leer(job, args.desde, args.chars))


if __name__ == "__main__":
    main()
