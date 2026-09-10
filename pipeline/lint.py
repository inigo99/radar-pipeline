# -*- coding: utf-8 -*-
"""Las banderas rojas del CV base: lo que un reclutador ve en diez segundos.

Todo lo demás del radar juzga las **ofertas**. Esto juzga tu **perfil**, que es
la única pieza del sistema con efecto multiplicativo: arreglar un logro sin
cifra mejora las doscientas candidaturas a la vez, no una.

Se ejecuta sobre `perfil/base` entero, una vez, no por oferta:

    python pipeline/lint.py            # informe por consola
    python pipeline/lint.py --json     # el mismo informe en JSON

`dashboard.py` lo importa y pinta el resultado en su propio panel, así que no
hace falta un paso más en la tarea diaria ni un fichero más en `data/`.

**Tres niveles.** `error` es algo que cuesta la criba (una cronología rota, un
puesto sin fechas, un modelo de evidencia que se contradice). `aviso` es algo
que se nota al leer. `info` es una preferencia defendible en la que conviene
ser consciente de lo que se está haciendo.

**Lo que no hay aquí, a propósito:** ninguna regla cultural. Si un CV lleva
foto o fecha de nacimiento depende del país, y un linter que penaliza a un CV
alemán por seguir la convención alemana es peor que no tener linter.

Dos reglas son propias de este sistema y no salen en ningún manual de CV:
`evidencia-sin-demostrar` y `techo-imposible` comprueban que el modelo de
evidencia —el que sostiene el candado anti-invención de `perfil.py`— siga
diciendo la verdad sobre los bullets que realmente hay.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiencia import MESES, _TRAMO  # noqa: E402  (mismo parseo de fechas que el resto)

#: Cuánto pesa cada nivel al resumir el informe en un número.
PESO = {"error": 12, "aviso": 5, "info": 1}

#: Meses de hueco entre dos puestos a partir de los cuales conviene explicarlo.
HUECO_MESES = 5
#: Proporción mínima de logros con una cifra dentro.
MIN_CON_METRICA = 0.5
#: Longitud a partir de la cual un bullet deja de leerse.
MAX_BULLET = 300
#: Logros por puesto a partir de los cuales el lector se salta la lista.
MAX_BULLETS_PUESTO = 6
#: Términos listados en competencias a partir de los cuales dejan de creerse.
MAX_SKILLS = 40

_CIFRA = re.compile(r"\d")
_SIGLA = re.compile(r"^[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9./+-]{1,5}$")

FUNCIONES = [
    (r"\bresponsable de\b", "responsable de"),
    (r"\bencargad[oa] de\b", "encargado de"),
    (r"\bme encargu[eé]\b", "me encargué de"),
    (r"\bparticip[eé] en\b", "participé en"),
    (r"\bcolabor[eé] en\b", "colaboré en"),
    (r"\btareas de\b", "tareas de"),
    (r"\bayud[eé] a\b", "ayudé a"),
    (r"\binvolucrad[oa] en\b", "involucrado en"),
    (r"\bresponsible for\b", "responsible for"),
    (r"\bworked on\b", "worked on"),
    (r"\bhelped (?:with|to)\b", "helped with"),
    (r"\binvolved in\b", "involved in"),
    (r"\bin charge of\b", "in charge of"),
    (r"\bassisted (?:with|in)\b", "assisted with"),
    (r"\bduties included\b", "duties included"),
]

VACIAS = [
    "apasionad", "proactiv", "orientad[oa] a resultados", "altamente motivad",
    "gran capacidad", "capacidad de trabajo en equipo", "valor añadido",
    "sinergia", "encaje perfecto", "no dudes en", "amplia experiencia",
    "results[- ]driven", "team player", "detail[- ]oriented", "self[- ]starter",
    "passionate about", "hard[- ]working", "think outside the box", "synergy",
    "proven track record",
]

_GERUNDIO = re.compile(r"^\s*\w+(?:ando|endo|ing)\b", re.I)
_PASADO = re.compile(r"^\s*\w+(?:[éíó]|amos|imos|aron|ieron|ed)\b", re.I)
_PRIMERA_PERSONA = re.compile(r"^\s*(?:yo\b|i\s+[a-z])", re.I)


def hallazgo(codigo, nivel, mensaje, detalle="", donde=""):
    return dict(codigo=codigo, nivel=nivel, mensaje=mensaje,
                detalle=detalle, donde=donde)


# ---------------------------------------------------------------- utilidades

def _meses(m):
    """(inicio, fin) de un tramo «septiembre 2023 – marzo 2026», en meses."""
    ini_mes, ini_anio, fin_mes, fin_anio = m.groups()
    fin_anio = int(fin_anio)
    ini_anio = int(ini_anio) if ini_anio else fin_anio
    return (ini_anio * 12 + MESES[ini_mes.lower()],
            fin_anio * 12 + MESES[fin_mes.lower()])


def tramos(texto):
    """Todos los tramos de una cadena de fechas, en meses absolutos."""
    return [_meses(m) for m in _TRAMO.finditer(texto or "")]


def _bullets_por_puesto(perfil):
    """[(nombre del puesto, [textos de sus logros])] uniendo todas las familias.

    Un bullet puede salir en unas familias y no en otras; para el linter
    interesa el conjunto, que es lo que puede acabar en un CV.
    """
    orden = perfil.get("orden") or {}
    textos = perfil.get("bullets_es") or {}
    exp = (perfil.get("perfil_llm") or {}).get("experiencia") or []
    puestos = {}
    for familia, listas in orden.items():
        for i, claves in enumerate(listas or []):
            nombre = _nombre_puesto(exp, i)
            puestos.setdefault(nombre, {"claves": set(), "por_familia": {}})
            puestos[nombre]["claves"].update(claves or [])
            puestos[nombre]["por_familia"][familia] = list(claves or [])
    return [(nombre, d, textos) for nombre, d in puestos.items()]


def _nombre_puesto(exp, i):
    if i < len(exp):
        e = exp[i]
        for clave in ("empresa", "compania", "compañia", "organizacion"):
            if e.get(clave):
                return str(e[clave])
        for clave in ("puesto", "cargo", "titulo", "rol"):
            if e.get(clave):
                return str(e[clave])
    return f"puesto {i + 1}"


def _todos_los_bullets(perfil):
    """{clave: texto} de los bullets que salen en algún CV, en español."""
    textos = perfil.get("bullets_es") or {}
    usadas = set()
    for listas in (perfil.get("orden") or {}).values():
        for claves in listas or []:
            usadas.update(claves or [])
    usadas.update((perfil.get("tfm_variant") or {}).values())
    usadas.update((perfil.get("tfg_variant") or {}).values())
    return {k: textos[k] for k in usadas if k in textos}


def _terminos_skills(perfil):
    """Los términos listados en «Competencias técnicas», de todas las variantes."""
    fuera = set()
    for grupos in (perfil.get("skills_es") or {}).values():
        for texto in (grupos or {}).values():
            cuerpo = str(texto).split(":", 1)[-1]
            for parte in re.split(r"[,;·|]| y | and ", cuerpo):
                parte = parte.strip(" .·–—-")
                if parte:
                    fuera.add(parte)
    return fuera


# -------------------------------------------------------------------- reglas

def regla_contacto(perfil, _ctx):
    c = perfil.get("contacto") or {}
    if not c.get("nombre_es") and not c.get("nombre_en"):
        yield hallazgo("falta-nombre", "error", "El CV no lleva nombre.")
    if not c.get("email"):
        yield hallazgo("falta-email", "error",
                       "No hay dirección de correo: no hay forma de contestarte.")
    if c.get("email") and not c.get("tel") and not c.get("linkedin"):
        yield hallazgo("contacto-pobre", "aviso",
                       "Sólo un correo, sin teléfono ni LinkedIn.")


def regla_fechas(perfil, ctx):
    for i, e in enumerate(ctx["experiencia"]):
        if not tramos(e.get("fechas")):
            yield hallazgo("fechas-ausentes", "error",
                           "Un puesto sin fechas legibles.",
                           detalle=str(e.get("fechas") or "(vacío)"),
                           donde=_nombre_puesto(ctx["experiencia"], i))


def regla_cronologia(perfil, ctx):
    fines = []
    for i, e in enumerate(ctx["experiencia"]):
        t = tramos(e.get("fechas"))
        if t:
            fines.append((i, max(f for _, f in t)))
    for (ia, fa), (ib, fb) in zip(fines, fines[1:]):
        if fb > fa:
            yield hallazgo(
                "cronologia", "error",
                "Los puestos no van del más reciente al más antiguo.",
                detalle=f"«{_nombre_puesto(ctx['experiencia'], ib)}» termina después "
                        f"que «{_nombre_puesto(ctx['experiencia'], ia)}» y va detrás.")


def regla_huecos(perfil, ctx):
    bordes = []
    for i, e in enumerate(ctx["experiencia"]):
        t = tramos(e.get("fechas"))
        if t:
            bordes.append((i, min(a for a, _ in t), max(b for _, b in t)))
    bordes.sort(key=lambda x: x[1])
    for (ia, _, fin), (ib, ini, _) in zip(bordes, bordes[1:]):
        hueco = ini - fin - 1
        if hueco >= HUECO_MESES:
            yield hallazgo(
                "hueco-empleo", "aviso",
                f"Hueco de {hueco} meses sin explicar entre dos puestos.",
                detalle="Si fue el máster, ponlo también en la experiencia o "
                        "nómbralo en el resumen: el lector no lo va a suponer.",
                donde=f"{_nombre_puesto(ctx['experiencia'], ia)} → "
                      f"{_nombre_puesto(ctx['experiencia'], ib)}")


def regla_hay_logros(perfil, ctx):
    if not ctx["bullets"]:
        yield hallazgo("sin-logros", "error",
                       "No hay ningún logro bajo ningún puesto: el CV son títulos.")
        return
    for nombre, d, textos in ctx["puestos"]:
        if not d["claves"]:
            yield hallazgo("sin-logros", "error",
                           "Un puesto sin ningún logro debajo.", donde=nombre)


def regla_metricas(perfil, ctx):
    bullets = ctx["bullets"]
    if not bullets:
        return
    con = [t for t in bullets.values() if _CIFRA.search(t)]
    ratio = len(con) / float(len(bullets))
    if ratio < MIN_CON_METRICA:
        sin = [k for k, t in bullets.items() if not _CIFRA.search(t)]
        yield hallazgo(
            "pocas-metricas", "aviso",
            f"Sólo {len(con)} de {len(bullets)} logros llevan una cifra "
            f"({ratio:.0%}).",
            detalle="La fórmula es «conseguí X, medido por Y, haciendo Z». "
                    "Sin la Y, el logro es una descripción de tarea. "
                    "Sin cifra: " + ", ".join(sorted(sin)[:8]))


def regla_lenguaje_funciones(perfil, ctx):
    for clave, texto in sorted(ctx["bullets"].items()):
        for patron, etiqueta in FUNCIONES:
            if re.search(patron, texto, re.I):
                yield hallazgo(
                    "lenguaje-de-funciones", "aviso",
                    f"«{etiqueta}» describe el puesto, no lo que conseguiste.",
                    detalle=texto[:140], donde=clave)
                break


def regla_bullet_largo(perfil, ctx):
    for clave, texto in sorted(ctx["bullets"].items()):
        if len(texto) > MAX_BULLET:
            yield hallazgo("bullet-largo", "aviso",
                           f"Un logro de {len(texto)} caracteres; nadie lo lee entero.",
                           detalle=texto[:140] + "…", donde=clave)


def regla_demasiados_bullets(perfil, ctx):
    vistos = set()
    for nombre, d, _ in ctx["puestos"]:
        for familia, claves in sorted(d["por_familia"].items()):
            if len(claves) > MAX_BULLETS_PUESTO and (nombre, len(claves)) not in vistos:
                vistos.add((nombre, len(claves)))
                yield hallazgo(
                    "demasiados-bullets", "info",
                    f"{len(claves)} logros en un mismo puesto "
                    f"(familia «{familia}»); a partir de {MAX_BULLETS_PUESTO} se saltan.",
                    donde=nombre)


def regla_frases_vacias(perfil, ctx):
    for clave, texto in sorted(ctx["bullets"].items()):
        for patron in VACIAS:
            if re.search(patron, texto, re.I):
                yield hallazgo("frase-vacia", "aviso",
                               "Frase de relleno: no dice nada que se pueda comprobar.",
                               detalle=texto[:140], donde=clave)
                break


def regla_tiempos(perfil, ctx):
    for nombre, d, textos in ctx["puestos"]:
        aperturas = [textos[k] for k in d["claves"] if k in textos]
        ger = [t for t in aperturas if _GERUNDIO.match(t)]
        pas = [t for t in aperturas if _PASADO.match(t) and not _GERUNDIO.match(t)]
        if ger and pas:
            yield hallazgo(
                "tiempos-mezclados", "info",
                "Dentro del mismo puesto hay logros en gerundio y en pasado.",
                detalle=f"«{ger[0][:60]}…» junto a «{pas[0][:60]}…»", donde=nombre)


def regla_primera_persona(perfil, ctx):
    for clave, texto in sorted(ctx["bullets"].items()):
        if _PRIMERA_PERSONA.match(texto):
            yield hallazgo("primera-persona", "info",
                           "Un logro que empieza en primera persona.",
                           detalle=texto[:140], donde=clave)


def regla_exceso_skills(perfil, ctx):
    n = len(ctx["skills"])
    if n > MAX_SKILLS:
        yield hallazgo(
            "exceso-skills", "aviso",
            f"{n} términos listados en competencias; por encima de {MAX_SKILLS} "
            "dejan de creerse.",
            detalle="Quita lo que no defenderías veinte minutos en una entrevista.")


def regla_keyword_repetido(perfil, ctx):
    bullets = list(ctx["bullets"].values())
    if len(bullets) < 4:
        return
    limite = max(3, int(len(bullets) * 0.6))
    for termino in sorted(ctx["evidencia"]):
        if len(termino) < 3:
            continue
        patron = re.compile(r"\b" + re.escape(termino) + r"\b", re.I)
        veces = sum(1 for t in bullets if patron.search(t))
        if veces > limite:
            yield hallazgo(
                "keyword-repetido", "info",
                f"«{termino}» aparece en {veces} de {len(bullets)} logros.",
                detalle="Repetir un término no mejora el filtrado de ningún ATS "
                        "moderno, y al lector le suena a relleno.")


def regla_evidencia_sin_demostrar(perfil, ctx):
    """Un término con evidencia 1,0 tiene que estar demostrado en algún logro.

    Es la regla que mantiene honesto el candado: `perfil.py` deja subir a su
    techo lo que el CV adaptado saca a un bullet, y da por hecho que un 1,0 ya
    está argumentado. Si el bullet que lo argumentaba se reescribió y el término
    desapareció, la puntuación sigue contándolo y nadie se entera.
    """
    texto = " \n".join(ctx["bullets"].values()) + " \n" + " ".join(ctx["skills"])
    # Las claves del vocabulario van en minúscula y con guiones bajos
    # («github_actions»); el CV escribe «GitHub Actions». Se comparan las dos
    # formas aplanadas para no inventar hallazgos por la separación.
    plano_texto = re.sub(r"[^a-z0-9]", "", texto.lower())
    for termino, valor in sorted(ctx["evidencia"].items()):
        if valor < 1.0 or len(termino) < 2:
            continue
        plano_termino = re.sub(r"[^a-z0-9]", "", str(termino).lower())
        if plano_termino and plano_termino in plano_texto:
            continue
        if not re.search(r"\b" + re.escape(termino) + r"\b", texto, re.I):
            yield hallazgo(
                "evidencia-sin-demostrar", "aviso",
                f"«{termino}» está marcado como demostrado (1,0) pero no aparece "
                "en ningún logro.",
                detalle="O el logro que lo demostraba cambió, o el término se "
                        "escribe de otra forma en el CV. Mientras tanto, la "
                        "puntuación lo está contando como demostrado.")


def regla_techo_imposible(perfil, ctx):
    """El techo nunca puede prometer más de lo que la evidencia permite."""
    techo = perfil.get("techo") or {}
    for termino, valor in sorted(techo.items()):
        base = ctx["evidencia"].get(termino, 0.0)
        if base == 0.0 and valor > 0.0:
            yield hallazgo(
                "techo-imposible", "error",
                f"«{termino}» tiene techo {valor} con evidencia 0.",
                detalle="El candado de `perfil.py` lo ignora, así que hoy no hace "
                        "daño, pero el dato dice que podrías presumir de algo que "
                        "no tienes. Bórralo del techo.")
        elif valor < base:
            yield hallazgo(
                "techo-imposible", "aviso",
                f"«{termino}» tiene techo {valor}, por debajo de su evidencia {base}.",
                detalle="Un techo por debajo de la evidencia no significa nada: "
                        "el CV adaptado nunca baja lo que ya está demostrado.")


def regla_skills_desincronizadas(perfil, ctx):
    """Términos listados en competencias que el modelo de evidencia no conoce.

    No puntúan, así que una oferta que los pida sale con un hueco que en
    realidad no lo es.
    """
    def plano(t):
        # «GitHub Actions», «github_actions» y «github-actions» son el mismo término.
        return re.sub(r"[^a-z0-9]", "", str(t).lower())

    conocidos = {plano(t) for t in ctx["evidencia"] if plano(t)}
    huerfanos = []
    for termino in sorted(ctx["skills"]):
        limpio = plano(termino)
        if len(limpio) < 2:
            continue
        if any(limpio == c or limpio in c or c in limpio for c in conocidos):
            continue          # variantes de nombre: «PostgreSQL» / «postgres»
        huerfanos.append(termino)
    if huerfanos:
        yield hallazgo(
            "skills-desincronizadas", "info",
            f"{len(huerfanos)} términos listados en competencias no están en "
            "`evidencia_orig`.",
            detalle="Una oferta que los pida los cuenta como hueco. Revisa: "
                    + ", ".join(huerfanos[:10]))


def regla_resumen(perfil, ctx):
    resumen = ctx["resumen"]
    if not resumen:
        return          # el resumen de este sistema es por oferta, en `tailor`
    if len(resumen) > 400:
        yield hallazgo("resumen-largo", "aviso",
                       f"El resumen base tiene {len(resumen)} caracteres.")
    if not _CIFRA.search(resumen):
        yield hallazgo("resumen-sin-cifra", "info",
                       "El resumen base no lleva ni una cifra.")
    palabras = resumen.split()
    siglas = [p for p in palabras if _SIGLA.match(p.strip(".,;:()"))]
    if palabras and len(siglas) / float(len(palabras)) > 0.25:
        yield hallazgo("sopa-de-siglas", "aviso",
                       f"El resumen base es {len(siglas)/len(palabras):.0%} siglas.",
                       detalle=" ".join(siglas[:10]))


REGLAS = (
    regla_contacto, regla_fechas, regla_cronologia, regla_huecos,
    regla_hay_logros, regla_metricas, regla_lenguaje_funciones,
    regla_bullet_largo, regla_demasiados_bullets, regla_frases_vacias,
    regla_tiempos, regla_primera_persona, regla_exceso_skills,
    regla_keyword_repetido, regla_evidencia_sin_demostrar,
    regla_techo_imposible, regla_skills_desincronizadas, regla_resumen,
)


def _contexto(perfil):
    llm = perfil.get("perfil_llm") or {}
    resumen = ""
    for clave in ("resumen", "resumen_es", "perfil", "summary"):
        if isinstance(llm.get(clave), str):
            resumen = llm[clave]
            break
    return dict(
        experiencia=llm.get("experiencia") or [],
        bullets=_todos_los_bullets(perfil),
        puestos=_bullets_por_puesto(perfil),
        skills=_terminos_skills(perfil),
        evidencia=perfil.get("evidencia_orig") or {},
        resumen=resumen,
    )


def analiza(perfil):
    """Todos los hallazgos, los más graves primero."""
    ctx = _contexto(perfil)
    salida = []
    for regla in REGLAS:
        try:
            salida.extend(regla(perfil, ctx))
        except Exception as exc:                       # una regla rota no tumba el informe
            salida.append(hallazgo("regla-rota", "info",
                                   f"La regla {regla.__name__} ha fallado.",
                                   detalle=repr(exc)))
    orden = {"error": 0, "aviso": 1, "info": 2}
    salida.sort(key=lambda h: (orden[h["nivel"]], h["codigo"], h["donde"]))
    return salida


def puntuacion(hallazgos):
    """Un número para poder ver si el CV mejora o empeora con el tiempo."""
    return sum(PESO[h["nivel"]] for h in hallazgos)


def informe(perfil):
    h = analiza(perfil)
    cuenta = {n: sum(1 for x in h if x["nivel"] == n) for n in PESO}
    return dict(hallazgos=h, cuenta=cuenta, puntuacion=puntuacion(h))


def main(argv):
    from datos import PERFIL                            # noqa: E402
    inf = informe(PERFIL)
    if "--json" in argv:
        json.dump(inf, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    c = inf["cuenta"]
    print(f"{c['error']} errores · {c['aviso']} avisos · {c['info']} apuntes "
          f"(penalización {inf['puntuacion']})")
    if not inf["hallazgos"]:
        print("Nada que objetar.")
    for x in inf["hallazgos"]:
        marca = {"error": "!!", "aviso": " !", "info": "  ·"}[x["nivel"]]
        donde = f" [{x['donde']}]" if x["donde"] else ""
        print(f"{marca} {x['codigo']}{donde}: {x['mensaje']}")
        if x["detalle"]:
            print(f"      {x['detalle']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
