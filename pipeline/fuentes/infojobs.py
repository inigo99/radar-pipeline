# -*- coding: utf-8 -*-
"""Extractor de InfoJobs — portado de `browser/infojobs.js` a Python (ver
`pipeline/fuentes/linkedin.py` para el porqué del cambio de arquitectura:
Scrapling trae el HTML, este script lo analiza).

Flujo (ver TAREA_DIARIA.md, Pasos 2-4): `consultas` -> Scrapling fetch ->
`parsear` (saca hashes del listado) -> `filtrar` (por slug) -> Scrapling
fetch de cada ficha -> `detallar` -> `clasificar` -> `snippets`/`leer`.

Si aparece el muro de cookies al mirar la página con el navegador (no al
usar Scrapling: eso no lo dispara): «Rechazar y cerrar», nunca «Aceptar» —
nota heredada de infojobs.js, ya no aplica a este flujo pero se deja por si
algún día hace falta abrir InfoJobs a mano.

OJO con el hash al escribir el id final en `ofertas` (paso 6): usar siempre
`id_para()` (12 caracteres). El 16-sep-2026 (con el extractor JS) días
distintos habían recortado el hash a longitudes distintas y `dedupe.py` dejó
pasar una oferta que ya estaba."""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pipeline.fuentes import comun, vocabulario

BUSCAR = "https://www.infojobs.net/jobsearch/search-results/list.xhtml?"

# El listado SSR sólo pinta unas pocas anclas, pero el HTML crudo lleva
# todas las URLs de oferta.
_RE_URL = re.compile(r"//www\.infojobs\.net/([a-z0-9-]+)/([a-z0-9-]+)/of-i([0-9a-f]+)")
_RE_META_DESC = re.compile(r'<meta name="description" content="([^"]{0,300})')
_RE_EMPRESA = re.compile(r"en la empresa ([^.,]{2,60})")
_RE_H1 = re.compile(r"<h1[^>]*>([\s\S]{0,120}?)</h1>")
_RE_SALARIO = re.compile(r"[\d.]{4,9}\s*[-–]?\s*[\d.]{0,9}\s*€?\s*Bruto/a[nñ]o", re.I)
_RE_ETIQUETA = re.compile(r"(solo teletrabajo|teletrabajo (parcial|h[ií]brido)|presencial|h[ií]brid)")
_RE_PUBLICADO = re.compile(r"hace\s+\d+\s*[dhm]\b|hace\s+\d+\s+(dias|horas|minutos)")
_RE_DESCRIPCION_INI = re.compile(r"Descripci[oó]n\b")
_RE_REQUISITOS = re.compile(r"Requisitos m[ií]nimos")


def url_de(oferta):
    return f"https://www.infojobs.net/{oferta['ciudad']}/{oferta['slug']}/of-i{oferta['hash']}"


def construir_consulta(kw, remoto=False, provincia=None, desde="_24_HOURS"):
    from urllib.parse import urlencode
    qs = {"keyword": kw, "sinceDate": desde}
    if remoto:
        qs["teleworkingIds"] = "2"
    if provincia:
        qs["provinceIds"] = provincia
    return BUSCAR + urlencode(qs)


def parsear(html, kw, ofertas=None):
    ofertas = ofertas if ofertas is not None else {}
    n = 0
    for m in _RE_URL.finditer(html or ""):
        ciudad, slug, hash_ = m.group(1), m.group(2), m.group(3)
        if hash_ not in ofertas:
            ofertas[hash_] = {"hash": hash_, "ciudad": ciudad, "slug": slug, "kw": kw}
            n += 1
    return ofertas, n


def id_para(oferta):
    return "ij-" + oferta["hash"][:12]


def filtrar(ofertas, hashes_conocidos=None):
    """El slug ya trae el puesto, así que se filtra por título sin pedir la
    ficha."""
    conocidos = set(hashes_conocidos or [])
    return [o for o in ofertas.values()
            if o["hash"] not in conocidos and comun.titulo_vale(o["slug"].replace("-", " "))]


def descripcion(txt):
    """Recorta la descripción antes de contar nada. Sobre el HTML/texto
    completo de InfoJobs cualquier conteo de tecnologías sale envenenado:
    `\\.net` casa con «infojobs.net» y da apariciones de C#/.NET en TODAS las
    ofertas, y «cliente» aparece en el pie de página. Por eso se corta entre
    «Descripción» y el final de «Requisitos mínimos»."""
    m_i = _RE_DESCRIPCION_INI.search(txt)
    m_j = _RE_REQUISITOS.search(txt)
    i = m_i.start() if m_i else -1
    j = m_j.start() if m_j else -1
    ini = i if (i >= 0 and (j < 0 or i < j)) else (j if j >= 0 else 0)
    fin = (j + 1400) if j >= 0 else (ini + 1800)
    return txt[ini:fin]


def detallar_una(oferta, html_ficha):
    meta = _RE_META_DESC.search(html_ficha)
    meta_txt = meta.group(1) if meta else ""
    todo = comun.texto(html_ficha)
    desc = descripcion(todo)
    dn = comun.norm(desc)
    m_empresa = _RE_EMPRESA.search(meta_txt)
    m_h1 = _RE_H1.search(html_ficha)
    m_sal = _RE_SALARIO.search(todo)
    m_etq = _RE_ETIQUETA.search(comun.norm(todo))
    m_pub = _RE_PUBLICADO.search(comun.norm(todo))
    out = dict(oferta)
    out.update({
        "empresa": (m_empresa.group(1).strip() if m_empresa else ""),
        "titulo": comun.texto(m_h1.group(1)) if m_h1 else "",
        "salario": (m_sal.group(0).strip() if m_sal else ""),
        "anios": comun.anios(comun.norm(todo)),
        "etiqueta": (m_etq.group(0) if m_etq else ""),
        "publicado": (m_pub.group(0) if m_pub else ""),
        # La modalidad se decide con la descripción, no con la etiqueta del
        # panel: una oferta etiquetada «solo teletrabajo» puede decir en el
        # cuerpo «para nuestras oficinas centrales» (visto el 16-sep-2026).
        "modalidad": comun.modalidad(dn, comun.norm(oferta.get("ciudad", "")),
                                      "teletrabajo" in comun.norm(todo)),
        "terminos": vocabulario.cuenta_terminos(dn),
        "_dn": dn,
        "_desc": desc,
    })
    return out


def clasificar(detalladas, cfg=None):
    aceptadas = comun.modalidades_aceptadas(cfg)
    dentro = [o for o in detalladas if o["modalidad"]["tipo"] in aceptadas]

    def fila(o):
        return "|".join([
            id_para(o), o["empresa"], o["titulo"], o["ciudad"],
            o["modalidad"]["tipo"], o.get("publicado", ""), o.get("salario") or "-",
            o.get("anios") or "-",
            (o["modalidad"]["frases"][0] if o["modalidad"]["frases"] else "")[:80],
        ])

    return {"filas": [fila(o) for o in dentro], "dentro": len(dentro),
            "fuera": len(detalladas) - len(dentro)}


def snippets(oferta, max_terms=10):
    hits = oferta.get("terminos") or vocabulario.cuenta_terminos(oferta.get("_dn", "")) or []
    if not hits:
        return "(sin términos de vocabulario — usar leer())"
    return "\n".join(f'{h[0]} ({h[1]}x): "{h[2]}"' for h in hits[:max_terms])


def leer(oferta, chars=900):
    return (oferta.get("_desc") or "")[:chars] if oferta.get("_desc") else "no encontrada"


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

    sp = sub.add_parser("consulta")
    sp.add_argument("--kw", required=True)
    sp.add_argument("--remoto", action="store_true")
    sp.add_argument("--provincia")
    sp.add_argument("--desde", default="_24_HOURS")

    sp = sub.add_parser("parsear")
    sp.add_argument("--in", dest="entrada", required=True,
                     help='JSON: [{"kw":..., "html":...}, ...]')
    sp.add_argument("--out")

    sp = sub.add_parser("filtrar")
    sp.add_argument("--ofertas", required=True)
    sp.add_argument("--conocidos", help="JSON: lista de hashes")
    sp.add_argument("--out")

    sp = sub.add_parser("detallar")
    sp.add_argument("--in", dest="entrada", required=True,
                     help='JSON: [{"hash":..., "html":...}, ...] (fichas)')
    sp.add_argument("--ofertas", required=True, help="salida de filtrar (lista)")
    sp.add_argument("--out")

    sp = sub.add_parser("clasificar")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--config")
    sp.add_argument("--out")

    sp = sub.add_parser("snippets")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--hash", required=True)
    sp.add_argument("--max-terms", type=int, default=10)

    sp = sub.add_parser("leer")
    sp.add_argument("--in", dest="entrada", required=True)
    sp.add_argument("--hash", required=True)
    sp.add_argument("--chars", type=int, default=900)

    args = p.parse_args()

    if args.cmd == "consulta":
        print(construir_consulta(args.kw, args.remoto, args.provincia, args.desde))

    elif args.cmd == "parsear":
        entrada = _leer_json(args.entrada)
        ofertas = {}
        for pagina in entrada:
            ofertas, _ = parsear(pagina["html"], pagina.get("kw", ""), ofertas)
        _escribir_json(args.out, ofertas)
        print(f"TOTAL={len(ofertas)}", file=sys.stderr)

    elif args.cmd == "filtrar":
        ofertas = _leer_json(args.ofertas)
        conocidos = _leer_json(args.conocidos) if args.conocidos else []
        cola = filtrar(ofertas, conocidos)
        _escribir_json(args.out, cola)
        print(f"candidatas={len(ofertas)} sobreviven={len(cola)}", file=sys.stderr)

    elif args.cmd == "detallar":
        fichas = _leer_json(args.entrada)
        ofertas = {o["hash"]: o for o in _leer_json(args.ofertas)}
        out = []
        for f in fichas:
            base = ofertas.get(f["hash"], {"hash": f["hash"], "ciudad": "", "slug": "", "kw": ""})
            out.append(detallar_una(base, f["html"]))
        _escribir_json(args.out, out)
        print(f"detalladas={len(out)}", file=sys.stderr)

    elif args.cmd == "clasificar":
        detalladas = _leer_json(args.entrada)
        cfg = _leer_json(args.config) if args.config else None
        res = clasificar(detalladas, cfg)
        if args.out:
            _escribir_json(args.out, res["filas"])
        else:
            print("\n".join(res["filas"]))
        print(f"dentro={res['dentro']} fuera={res['fuera']}", file=sys.stderr)

    elif args.cmd == "snippets":
        detalladas = _leer_json(args.entrada)
        o = next((x for x in detalladas if x["hash"].startswith(args.hash)), None)
        print("no encontrada" if o is None else snippets(o, args.max_terms))

    elif args.cmd == "leer":
        detalladas = _leer_json(args.entrada)
        o = next((x for x in detalladas if x["hash"].startswith(args.hash)), None)
        print("no encontrada" if o is None else leer(o, args.chars))


if __name__ == "__main__":
    main()
