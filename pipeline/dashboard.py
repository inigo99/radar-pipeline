# -*- coding: utf-8 -*-
import os, re, sys, json, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tailor import T
from perfil import ORIG, termino_skill, TERMINOS_SKILL
from base_cv import SKILLS_ES, SKILLS_EN, ORDEN_SKILLS

RES = json.load(open('data/resultado.json'))

# Candado anti-«Senior» (16 sep 2026): a Íñigo no le corresponde presentarse
# como sénior todavía, así que se quita del titular pase lo que pase, aunque
# el título del anuncio lo lleve o se cuele en `tailor`. Es determinista, no
# depende de que la tarea diaria se acuerde de evitarlo, y limpia también las
# ofertas ya cargadas la próxima vez que se regenera el dashboard.
_SENIOR_RE = re.compile(r'(?i)\b(senior|s[eé]nior|sr\.?)\b')


def _limpia_titular(t):
    if not t:
        return t
    t = _SENIOR_RE.sub('', t)
    t = re.sub(r'\(\s*\)', '', t)                  # paréntesis que quedan vacíos
    t = re.sub(r'\s{2,}', ' ', t)                   # huecos dobles
    t = re.sub(r'^[\s/\-·]+|[\s/\-·]+$', '', t)     # separador colgante al inicio/final
    t = re.sub(r'\s*/\s*/\s*', ' / ', t)            # doble barra si el hueco caía entre dos
    return t.strip()


# Candado (18 sep 2026): el titular tiene que decir quién ES Íñigo, nunca
# repetir el nombre del puesto del anuncio. Si `tailor/<id>.titular` llega
# vacío (o queda vacío tras _limpia_titular), no hay `puesto` de reserva --
# se usa un titular genérico razonable según la `familia`, igual que
# `tituloPorDefecto()` en JS (mismo candado, mismo criterio, para el alta
# manual con "+ Oferta").
_TITULO_DEFECTO = {
    'genai': 'Ingeniero de IA', 'ml': 'Ingeniero de Machine Learning',
    'cv': 'Ingeniero de Visión por Computador', 'ds': 'Científico de Datos',
    'mlops': 'Ingeniero MLOps', 'research': 'Ingeniero de IA',
    'backend': 'Desarrollador Full Stack', 'general': 'Ingeniero Informático',
}


def _titulo_por_defecto(familia):
    return _TITULO_DEFECTO.get(familia, 'Ingeniero Informático')


def _opcional(nombre, defecto):
    """data/filtradas.json y data/embudo.json pueden no existir todavía."""
    try:
        with open('data/' + nombre, encoding='utf-8') as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return defecto


FILTRADAS = _opcional('filtradas.json', {})
EMBUDO = _opcional('embudo.json', {})


def _norm_txt(s):
    """Minúsculas y sin acentos, para comparar contra el blob de skills_es/en
    igual que hace `normTxt()` en JS (`filtraSkillsExtra`)."""
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower()


def _skills_extra_auto(reqs, familia, idioma):
    """`skills_extra` determinista: si la oferta pesa una clave de vocabulario
    que Íñigo tiene de verdad (`evidencia_orig > 0`, mismo candado que
    `prominencia_adaptada`) y la variante de skills de su `familia` no la
    enseña ya, se imprime como línea extra bajo «Competencias técnicas».

    Hasta el 18 sep 2026 esto dependía de que la tarea diaria lo rellenara a
    mano en `tailor/<id>.skills_extra` (paso 6 de TAREA_DIARIA.md) -- en la
    práctica casi nunca lo hacía (0 de 327 ofertas lo llevaban relleno), así
    que las palabras clave de la oferta no llegaban al CV aunque él tuviera
    la tecnología. Ahora es determinista, igual que `_limpia_titular()` con
    "Senior": no depende de que nadie se acuerde de un paso opcional.
    `tailor/<id>.skills_extra`, si alguien lo rellena a mano (p.ej. el botón
    "+ Oferta"), sigue teniendo prioridad -- ver la llamada más abajo."""
    cfg = ORDEN_SKILLS.get(familia) or ORDEN_SKILLS.get('general') or {}
    variante = cfg.get('variante')
    tabla = SKILLS_EN if idioma == 'en' else SKILLS_ES
    cats = (tabla.get(variante) or {})
    orden_cats = cfg.get('orden') or list(cats.keys())
    blob = _norm_txt(' | '.join(cats.get(c, '') for c in orden_cats))
    vistos, salida = set(), []
    for k, w, _l in sorted(reqs, key=lambda x: -x[1]):
        if ORIG.get(k, 0.0) <= 0:
            continue                                    # candado: no lo tiene -> no se inventa
        termino = termino_skill(k, idioma)
        if not termino or termino in vistos:
            continue
        if _norm_txt(termino) in blob:
            continue                                    # ya sale en la variante de la familia
        vistos.add(termino)
        salida.append(termino)
        if len(salida) >= 4:
            break
    return ', '.join(salida)


rows=[]
for r in RES:
    _familia = T[r['id']]['familia']
    _skills_manual = (T[r['id']].get('skills_extra') or '').strip()
    rows.append(dict(
      id=r['id'], empresa=r['empresa'], puesto=r['puesto'], ubicacion=r['ubicacion'],
      modalidad=r['modalidad'], publicada=r['publicada'], idioma=r['idioma'], fuente=r['fuente'],
      salMin=r['sal_min'], salMax=r['sal_max'], salMedio=r['sal_medio'], salOrigen=r['sal_origen'],
      salBase=r['sal_base'], url=r['url'], scoreOrig=r['score_orig'], scoreAdap=r['score_adap'],
      delta=r['delta'], mejora=r['mejora_pct'], fuertes=r['fuertes'], huecos=r['huecos'],
      alerta=r.get('alerta',''),
      titular=_limpia_titular(T[r['id']]['titular']) or _titulo_por_defecto(T[r['id']]['familia']),
      resumen=T[r['id']]['resumen'], familia=_familia,
      skillsExtra=_skills_manual or _skills_extra_auto(r['reqs'], _familia, r['idioma']),
      reqs=[f"{l} (peso {w})" for _,w,l in sorted(r['reqs'], key=lambda x:-x[1])[:12]],
      zona=('local' if ('Navarra' in r['modalidad'] or 'Gipuzkoa' in r['modalidad']) else 'remoto'),
      ambito=r['ambito'],
      prioridad=r.get('prioridad', r['score_adap']), brecha=r.get('brecha', []),
      foco=r.get('foco', r.get('prioridad', r['score_adap'])),
      dias=r.get('dias'), motivoFoco=r.get('motivo_foco',''),
      aniosMin=r.get('anios_min'),
    ))

DATA = json.dumps(rows, ensure_ascii=False, separators=(',',':'))
FILTRADAS_JS = json.dumps(sorted(FILTRADAS.values(),
                                 key=lambda f: (f.get('fecha', ''), f.get('empresa', '')),
                                 reverse=True),
                          ensure_ascii=False, separators=(',', ':'))
EMBUDO_JS = json.dumps(EMBUDO, ensure_ascii=False, separators=(',', ':'))

from base_cv import (BULLETS_ES, BULLETS_EN, CONTACTO,
                      ORDEN, CV_LABELS, PERFIL_LLM,
                      TFM_VARIANT, TFG_VARIANT)
from datos import PERFIL as _PERFIL_DOC

# Añadir oferta a mano (16 sep 2026): el botón "+" del dashboard reconstruye,
# en el navegador y con la capacidad `sample`, el mismo trabajo que hoy hace
# la tarea diaria a mano en el Paso 6 -- reqs, familia, titular/resumen,
# salario si falta. Para que no diverja de las reglas reales, estas tablas se
# incrustan tal cual desde su fuente en el repo, no se retipean en JS:
# `pipeline/aprendizaje.py` (prioridad por familia y dificultad de huecos),
# `pipeline/foco.py` (antigüedad/sénior) y `pipeline/bandas.json` (salario
# estimado). Si esos ficheros cambian, el dashboard los recoge solo en la
# siguiente publicación.
from aprendizaje import PESO_FAMILIA, PESO_FAMILIA_DEFECTO, DIFICULTAD, DEFECTO as DIFICULTAD_DEFECTO
from foco import SENIOR as _SENIOR_RE_FOCO, FRESCURA, PENALIZACION_SENIOR, BONUS_SALARIO_PUBLICADO
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocabulario.md'), encoding='utf-8') as _fh:
    VOCABULARIO_MD = _fh.read()
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bandas.json'), encoding='utf-8') as _fh:
    BANDAS = _fh.read()  # ya es JSON válido tal cual; se pasa sin retocar
from experiencia import anios_perfil, MARGEN_DEF

# Los años de experiencia del CV, sumados de las fechas de sus puestos. Se
# recalculan en cada ejecución, así que la cifra sube sola con el tiempo.
ANIOS_PERFIL = anios_perfil(_PERFIL_DOC)

# El linter del CV base. Corre aquí y no como un paso más de la tarea diaria
# porque no necesita ningún dato que no esté ya cargado: `perfil/base` y nada
# más. Así no hay fichero nuevo en `data/` ni paso nuevo que se pueda olvidar.
from lint import informe as _informe_lint
LINT = _informe_lint(_PERFIL_DOC)
LINT_JS = json.dumps(LINT, ensure_ascii=False, separators=(',', ':'))
_pl = dict(PERFIL_LLM)
_pl["tel"], _pl["email"], _pl["linkedin"] = CONTACTO["tel"], CONTACTO["email"], CONTACTO["linkedin"]
_pl["experiencia"] = [
    {k: v for k, v in e.items() if k != "bullets"} |
    {"logros_es": [BULLETS_ES[b] for b in e["bullets"]],
     "logros_en": [BULLETS_EN[b] for b in e["bullets"]]}
    for e in PERFIL_LLM["experiencia"]]
PERFIL = json.dumps(_pl, ensure_ascii=False, separators=(',', ':'))

# Todo lo que necesita la página para armar el CV en el navegador, bajo demanda.
CV = json.dumps(dict(contacto=CONTACTO, bullets_es=BULLETS_ES, bullets_en=BULLETS_EN,
                     skills_es=SKILLS_ES, skills_en=SKILLS_EN, orden=ORDEN,
                     orden_skills=ORDEN_SKILLS, labels=CV_LABELS,
                     tfm_variant=TFM_VARIANT, tfg_variant=TFG_VARIANT,
                     # Sólo para que `autoSkillsExtra()` (JS) pueda calcular
                     # `skills_extra` igual que `_skills_extra_auto()` en
                     # Python, cuando se añade una oferta a mano con "+ Oferta".
                     terminos_skill=TERMINOS_SKILL),
                ensure_ascii=False, separators=(',', ':'))

# La plantilla vive fuera de este fichero desde el 19-sep-2026 (ver README):
# hasta entonces ~2500 líneas de JavaScript vivían como una sola cadena Python
# de 174 KB dentro de `TPL`, lo que hacía de este fichero el punto más frágil
# del pipeline -- ni el editor ni el linter de JS podían ayudar dentro de una
# cadena, y `device_commit_files` corrompió esa cadena en silencio más de una
# vez (verificado con sha256sum tras el hecho). `dashboard_template.html` es el
# armazón HTML/CSS con un único hueco, `__SCRIPT__`; `dashboard.js` es todo el
# JavaScript del lado del cliente, comprobable solo con `node --check
# pipeline/dashboard.js` sin tener que ejecutar el pipeline entero. Los
# `__PLACEHOLDER__` que quedan (`__DATA__`, `__PERFIL__`...) se rellenan igual
# que siempre, con los `.replace()` de más abajo -- da igual en qué fichero
# viva el texto que los contiene.
_AQUI = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_AQUI, "dashboard_template.html"), encoding="utf-8") as _fh:
    _PLANTILLA_HTML = _fh.read()
with open(os.path.join(_AQUI, "dashboard.js"), encoding="utf-8") as _fh:
    _PLANTILLA_JS = _fh.read()
TPL = _PLANTILLA_HTML.replace("__SCRIPT__", _PLANTILLA_JS)


import datetime
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio",
         "agosto","septiembre","octubre","noviembre","diciembre"]
_h = datetime.date.today()
FECHA = "%d de %s de %d" % (_h.day, MESES[_h.month-1], _h.year)
CONTACTO_JS = json.dumps({
  "nombre": CONTACTO["nombre_es"], "ciudad": CONTACTO["ciudad_es"],
  "email": CONTACTO["email"], "tel": CONTACTO["tel"], "linkedin": CONTACTO["linkedin"],
}, ensure_ascii=False)
out = (TPL.replace("__DATA__", DATA).replace("__PERFIL__", PERFIL).replace("__CV__", CV)
          .replace("__FILTRADAS__", FILTRADAS_JS).replace("__EMBUDO__", EMBUDO_JS)
          .replace("__ANIOS_PERFIL__", json.dumps(ANIOS_PERFIL))
          .replace("__MARGEN_DEF__", json.dumps(MARGEN_DEF))
          .replace("__LINT__", LINT_JS)
          .replace("__EVIDENCIA__", json.dumps(_PERFIL_DOC.get("evidencia_orig") or {},
                                               ensure_ascii=False, separators=(',', ':')))
          .replace("__TECHO__", json.dumps(_PERFIL_DOC.get("techo") or {},
                                           ensure_ascii=False, separators=(',', ':')))
          .replace("__PESO_FAMILIA__", json.dumps(PESO_FAMILIA, ensure_ascii=False, separators=(',', ':')))
          .replace("__PESO_FAMILIA_DEFECTO__", json.dumps(PESO_FAMILIA_DEFECTO))
          .replace("__DIFICULTAD__", json.dumps({k: list(v) for k, v in DIFICULTAD.items()},
                                                ensure_ascii=False, separators=(',', ':')))
          .replace("__DIFICULTAD_DEFECTO__", json.dumps(list(DIFICULTAD_DEFECTO), ensure_ascii=False))
          .replace("__SENIOR_RE_FOCO__", json.dumps(_SENIOR_RE_FOCO.pattern, ensure_ascii=False))
          .replace("__FRESCURA__", json.dumps(FRESCURA, ensure_ascii=False))
          .replace("__PENALIZACION_SENIOR__", json.dumps(PENALIZACION_SENIOR))
          .replace("__BONUS_SALARIO_PUBLICADO__", json.dumps(BONUS_SALARIO_PUBLICADO))
          .replace("__VOCABULARIO_MD__", json.dumps(VOCABULARIO_MD, ensure_ascii=False))
          .replace("__BANDAS__", BANDAS)
          .replace("__CONTACTO__", CONTACTO_JS).replace("__NOMBRE__", CONTACTO["nombre_es"])
          .replace("__N__", str(len(rows))).replace("__FECHA__", FECHA))
open('out/dashboard.html','w').write(out)
print("bytes", len(out.encode()))
