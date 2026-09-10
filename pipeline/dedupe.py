# -*- coding: utf-8 -*-
"""Deduplicación de ofertas: la misma vacante vista dos veces.

La misma oferta llega con ids distintos desde portales distintos, y muchas
están en LinkedIn **y** en InfoJobs. Hasta ahora esto se hacía a ojo o con un
script improvisado cada mañana, que es la clase de cosa que funciona hasta que
no. Aquí vive ya escrito, con las trampas dentro.

Tres pasadas, de la más barata a la más cara:

  1. **Por id.** Ya está en `ofertas`, en `pipeline/cerradas` o tiene
     seguimiento en `estado`.
  2. **Por huella.** Empresa y puesto normalizados: sin acentos, sin
     mayúsculas, sin sufijos de sociedad («S.L.», «GmbH», «Ltd»), sin el ruido
     de los títulos («(m/f/d)», «100% remoto», «- Madrid»).
  3. **Por solape de tokens del título**, y sólo dentro de la misma empresa.

**Nunca por subcadena.** Es la regla que impide que «Alan» case con «Talan» o
«UST» con «Braintrust». Comparar cadenas por `in` parece razonable durante diez
minutos y luego se come ofertas buenas en silencio.

Uso:

    python pipeline/dedupe.py candidatas.json          # criba y escribe el resultado
    python pipeline/dedupe.py candidatas.json --json ok.json
    python pipeline/dedupe.py --auditar                # duplicados ya dentro de `ofertas`

`candidatas.json` es una lista de ofertas nuevas (basta con `id`, `empresa` y
`puesto`). Lo conocido sale de `data/`: `ofertas.json`, `cerradas.json` y
`estado.json`.
"""
import json
import os
import re
import sys
import unicodedata

DATA = os.environ.get("RADAR_DATA", "data")

#: Umbral de solape (Jaccard) entre los tokens de dos títulos de la misma
#: empresa para considerarlos la misma vacante. Alto a propósito: ante la duda,
#: dos ofertas separadas cuestan una lectura de más; una fusionada mal cuesta
#: una oferta buena.
UMBRAL_SOLAPE = 0.75

SUFIJOS_SOCIEDAD = {
    "sl", "slu", "sa", "sau", "sas", "srl", "spa", "sarl", "sl.", "sccl",
    "gmbh", "mbh", "ag", "ab", "as", "oy", "bv", "nv", "plc", "ltd", "limited",
    "inc", "llc", "corp", "corporation", "co", "kg", "aps", "sp", "zoo",
    "group", "grupo", "holding", "holdings", "iberia", "spain", "espana",
    "technologies", "technology", "tech", "solutions", "consulting",
    "consultores", "consultoria", "services", "servicios", "digital",
}

#: Palabras que no distinguen una vacante de otra. Se quitan del título antes
#: de comparar: «Senior Python Developer (Remote)» y «Python Developer» son la
#: misma vacante vista con dos etiquetas de portal.
RUIDO_TITULO = {
    "senior", "sr", "jr", "junior", "mid", "midlevel", "semi", "ssr",
    "engineer", "engineering", "ingeniero", "ingeniera", "developer",
    "desarrollador", "desarrolladora", "programador", "programadora",
    "specialist", "especialista", "expert", "experto", "experta",
    "remote", "remoto", "remota", "teletrabajo", "hibrido", "presencial",
    "onsite", "hybrid", "fulltime", "full", "time", "jornada", "completa",
    "m", "f", "d", "h", "x", "w", "mfd", "hmx", "mwd",
    "de", "del", "la", "el", "los", "las", "y", "e", "o", "u", "en", "con",
    "para", "a", "al", "the", "and", "or", "for", "with", "in", "of", "to",
    "puesto", "oferta", "empleo", "trabajo", "job", "vacante", "position",
    "role", "nueva", "nuevo", "urgente", "inmediata",
}

_NO_PALABRA = re.compile(r"[^a-z0-9+#]+")
# «Talan España, S.L.U.» y «Acme, S.A.»: la forma jurídica con puntos se parte
# en letras sueltas al trocear por palabras, así que se quita antes.
_FORMA_JURIDICA = re.compile(
    r"[,\s]*\b(?:s\.\s*l\.?\s*u?\.?|s\.\s*a\.?\s*u?\.?|s\.\s*a\.?\s*s\.?|"
    r"s\.\s*r\.\s*l\.?|c\.\s*b\.?|s\.\s*c\.?)\s*$", re.I)
# «(m/f/d)», «100% remoto», «| Madrid», «- Barcelona», «[Híbrido]»: cola de
# etiquetas que los portales pegan al título y que no describen el puesto.
_COLA_TITULO = re.compile(
    r"\s*[\(\[\|/–—-]\s*(?:m\s*/\s*f\s*/\s*[dx]|h\s*/\s*m\s*/\s*x|"
    r"\d{1,3}\s*%\s*\w+|remote|remoto|teletrabajo|h[ií]brido|presencial|"
    r"full[\s-]?time|part[\s-]?time)\b.*$", re.I)


def sin_acentos(texto):
    """«Compañía Española» -> «compania espanola». La ñ cuenta como n."""
    plano = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in plano if unicodedata.category(c) != "Mn").lower()


def _palabras(texto):
    return [p for p in _NO_PALABRA.split(sin_acentos(texto)) if p]


def normaliza_empresa(nombre):
    """Nombre de empresa comparable: sin acentos, sin sufijos de sociedad."""
    limpio = _FORMA_JURIDICA.sub("", str(nombre or ""))
    palabras = [p for p in _palabras(limpio)
                if p not in SUFIJOS_SOCIEDAD and len(p) > 1]
    return " ".join(palabras) or sin_acentos(nombre).strip()


def tokens_puesto(puesto):
    """Los tokens del título que de verdad distinguen una vacante de otra.

    Si al quitar el ruido no queda nada —«Ingeniero de Software» es todo
    palabras genéricas—, se devuelven las palabras del título tal cual. Un
    conjunto vacío casaría con cualquier otro conjunto vacío de la misma
    empresa, que es justo el falso positivo que hay que evitar.
    """
    limpio = _COLA_TITULO.sub("", str(puesto or ""))
    palabras = [p for p in _palabras(limpio) if len(p) > 1 and not p.isdigit()]
    utiles = {p for p in palabras if p not in RUIDO_TITULO}
    return utiles or set(palabras)


def huella(oferta):
    """Empresa + puesto normalizados. Dos ofertas con la misma huella son la misma."""
    empresa = normaliza_empresa(oferta.get("empresa"))
    puesto = " ".join(sorted(tokens_puesto(oferta.get("puesto"))))
    return empresa + "|" + puesto


def solape(a, b):
    """Jaccard entre dos conjuntos de tokens. 1.0 = idénticos, 0.0 = ajenos."""
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _indice(conocidas):
    """Prepara lo ya conocido para consultarlo sin recorrerlo entero cada vez."""
    por_huella, por_empresa = {}, {}
    for o in conocidas:
        por_huella.setdefault(huella(o), o)
        por_empresa.setdefault(normaliza_empresa(o.get("empresa")), []).append(o)
    return por_huella, por_empresa


def _etiqueta(o):
    return f"{o.get('empresa', '?')} — {o.get('puesto', '?')} [{o.get('id', '?')}]"


def dedupe(candidatas, conocidas=(), ids_vetados=()):
    """(supervivientes, duplicadas). Cada duplicada dice contra qué chocó.

    `ids_vetados` son ids que no deben volver a entrar aunque no estén en
    `conocidas`: típicamente los de `pipeline/cerradas`.
    """
    vetados = set(ids_vetados)
    ids_conocidos = {o.get("id") for o in conocidas} | vetados
    por_huella, por_empresa = _indice(conocidas)

    supervivientes, duplicadas = [], []
    for cand in candidatas:
        cid = cand.get("id")

        if cid in ids_conocidos:
            duplicadas.append(dict(oferta=cand, motivo="id ya conocido", contra=cid))
            continue

        h = huella(cand)
        gemela = por_huella.get(h)
        if gemela is not None:
            duplicadas.append(dict(oferta=cand, motivo="misma empresa y mismo puesto",
                                   contra=_etiqueta(gemela)))
            continue

        empresa = normaliza_empresa(cand.get("empresa"))
        toks = tokens_puesto(cand.get("puesto"))
        parecida, mejor = None, 0.0
        for otra in por_empresa.get(empresa, []):
            s = solape(toks, tokens_puesto(otra.get("puesto")))
            if s > mejor:
                parecida, mejor = otra, s
        if parecida is not None and mejor >= UMBRAL_SOLAPE:
            duplicadas.append(dict(oferta=cand,
                                   motivo=f"mismo puesto en la misma empresa (solape {mejor:.0%})",
                                   contra=_etiqueta(parecida)))
            continue

        # Sobrevive: entra en el índice para que dos clones del mismo lote no
        # pasen los dos.
        supervivientes.append(cand)
        ids_conocidos.add(cid)
        por_huella[h] = cand
        por_empresa.setdefault(empresa, []).append(cand)

    return supervivientes, duplicadas


def _leer(nombre, defecto):
    ruta = os.path.join(DATA, nombre)
    if not os.path.exists(ruta):
        return defecto
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def conocidas_de_data():
    """Lo que ya está en el radar: ofertas vivas, cerradas y con seguimiento."""
    ofertas = _leer("ofertas.json", [])
    cerradas = _leer("cerradas.json", {"lista": []}).get("lista", [])
    estado = _leer("estado.json", {})
    vetados = {c.get("id") for c in cerradas if c.get("id")} | set(estado)
    return list(ofertas) + [c for c in cerradas if c.get("empresa")], vetados


def _auditar():
    """Duplicados que ya están dentro de `ofertas`. Sólo informa, no borra."""
    ofertas = _leer("ofertas.json", [])
    vistos, choques = {}, []
    for o in ofertas:
        h = huella(o)
        if h in vistos:
            choques.append((vistos[h], o))
        else:
            vistos[h] = o
    print(f"{len(ofertas)} ofertas en el radar, {len(choques)} pares duplicados.")
    for a, b in choques:
        print(f"  · {_etiqueta(a)}\n    {_etiqueta(b)}")
    return 0 if not choques else 1


def main(argv):
    if "--auditar" in argv:
        return _auditar()
    entradas = [a for a in argv if not a.startswith("--")]
    if not entradas:
        raise SystemExit(__doc__)

    with open(entradas[0], encoding="utf-8") as fh:
        candidatas = json.load(fh)
    if isinstance(candidatas, dict):
        candidatas = list(candidatas.values())

    conocidas, vetados = conocidas_de_data()
    supervivientes, duplicadas = dedupe(candidatas, conocidas, vetados)

    destino = None
    if "--json" in argv:
        destino = argv[argv.index("--json") + 1]
    elif len(entradas) > 1:
        destino = entradas[1]
    if destino:
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(supervivientes, fh, ensure_ascii=False, indent=1)

    print(f"{len(candidatas)} candidatas · {len(supervivientes)} nuevas · "
          f"{len(duplicadas)} duplicadas"
          + (f" -> {destino}" if destino else ""))
    for d in duplicadas:
        print(f"  ✕ {_etiqueta(d['oferta'])}\n    {d['motivo']}: {d['contra']}")
    for s in supervivientes:
        print(f"  ✓ {_etiqueta(s)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
