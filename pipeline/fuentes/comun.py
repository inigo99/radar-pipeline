# -*- coding: utf-8 -*-
"""Utilidades comunes de clasificación, portadas de `browser/common.js` (ver
`pipeline/fuentes/__init__.py` para el porqué del cambio). Traducción fiel:
mismos regex, mismos comentarios de bugs ya corregidos, para no perder el
conocimiento acumulado al cambiar dónde corre el código."""
import re
import unicodedata


def norm(s):
    """Minúsculas y sin acentos. Todos los regex de abajo asumen texto ya
    normalizado."""
    s = s or ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


_RE_TAGS_BLOQUE = re.compile(r"</(p|li|div|h\d|tr)>", re.I)
_RE_BR = re.compile(r"<br\s*/?>", re.I)
_RE_SCRIPT = re.compile(r"<script[\s\S]*?</script>", re.I)
_RE_STYLE = re.compile(r"<style[\s\S]*?</style>", re.I)
_RE_TAG = re.compile(r"<[^>]*>")
_RE_WS = re.compile(r"\s+")
_ENTIDADES = {
    "&amp;": "&", "&nbsp;": " ", "&aacute;": "á", "&eacute;": "é",
    "&iacute;": "í", "&oacute;": "ó", "&uacute;": "ú", "&ntilde;": "ñ",
}
_RE_ENTIDAD_NUM = re.compile(r"&#\d+;")


def texto(html):
    """HTML -> texto plano conservando los saltos de bloque, que es donde
    viven las frases de modalidad («100% remoto.» suele ir sola en su propio
    <li>). Sólo hace falta cuando se pide `extraction_type:"html"` a
    Scrapling; con `extraction_type:"text"` esto ya viene hecho, pero se
    mantiene para los sitios (LinkedIn) donde hace falta el HTML crudo para
    el regex de listado."""
    h = html or ""
    h = _RE_BR.sub(" ", h)
    h = _RE_TAGS_BLOQUE.sub(". ", h)
    h = _RE_SCRIPT.sub(" ", h)
    h = _RE_STYLE.sub(" ", h)
    h = _RE_TAG.sub(" ", h)
    for ent, rep in _ENTIDADES.items():
        h = h.replace(ent, rep)
    h = _RE_ENTIDAD_NUM.sub("", h)
    h = _RE_WS.sub(" ", h).strip()
    return h


# ---- Modalidad -------------------------------------------------------
# OJO: la primera versión de esto se dejó fuera «remote» y «remoto» a secas
# y perdió 24 ofertas de 80 en un solo día, porque la forma más común en
# inglés es «This is a remote position». No quitar los \b...\b sueltos.
RE_REMOTO = re.compile(
    r"(100\s*%?\s*remot|fully remote|full[- ]remote|remote[- ]first|"
    r"totalmente remot|completamente remot|en remoto|teletrabajo|"
    r"trabajo remot|remote work|work from home|work remotely|"
    r"\bremote\b|\bremoto\b|\bremota\b)"
)
RE_HIBRIDO = re.compile(
    r"(hibrid|hybrid|\d\s*d[ií]as? (en|de|a la) (oficina|casa|semana)|"
    r"days? (in|at|per week in) (the )?office|"
    r"office[^.]{0,40}\d+\s*days?\s*(a|per)\s*week|"
    r"\d+\s*days?\s*(a|per)\s*week[^.]{0,40}office|"
    r"d[ií]as? (de )?presencialidad|modelo h[ií]brido|parcialmente remot|"
    r"remoto parcial|combinaci[oó]n de (teletrabajo|remoto)|"
    r"flexib\w* .{0,25}remot|some days? (a week )?(in|at) (the )?office|"
    r"office[- ]based .{0,25}(flexib|remot)|"
    # 23-sep-2026: «work from home (2 days per week)» / «remote 3 days a
    # week» se colaban como 100% remoto -> RE_REMOTO capta «work from home»
    # o «remote» sueltos y nada exigía "office" cerca. Es el mismo patrón que
    # arriba pero en la forma inversa: cuántos días trabaja desde CASA, no
    # cuántos días va a la oficina. Encontrado con una oferta real de Smadex.
    # OJO: el número se limita a 1-4 a propósito — «remote 5 days a week» es
    # 100% remoto (semana completa), no híbrido; sólo <5 implica que el
    # resto de días son de oficina.
    r"(work(ing)? from home|remote(ly)?)[^.]{0,40}[1-4]\s*days?\s*(a|per)\s*week|"
    r"[1-4]\s*days?\s*(a|per)\s*week[^.]{0,40}(work(ing)? from home|remote(ly)?)|"
    # 30-sep-2026: revisión de las 41 descartadas a mano por «Presencial»/
    # «Híbrido». Formas reales de decir «remoto sólo una parte» que se
    # colaban como 100 % remoto porque llevan la palabra remote/remoto:
    #  - «Remote work: 1 full day and 2 afternoons per week» (Ventós)
    r"(remote work|work(ing)? from home|teletrabajo|en remoto)[^.]{0,20}\b[1-4]\s*(full\s*)?"
    r"(days?|dias?)\b[^.]{0,40}(week|semana)|"
    #  - «Office-first ... with 20% remote flexibility» (Joppy), «Hasta un
    #    60% de trabajo en remoto» (CaixaBank). Un porcentaje de 1 a 99: el
    #    \b impide que «100%» case como «10%» o «00%».
    r"office[- ]first|remote flexibility|\b[1-9]\d?\s*%[^.]{0,20}(remote|remot|teletrabajo)|"
    #  - «work from home, the office or a mix of both. Plus, work from
    #    anywhere for up to 30 days a year» (Prima): días al año desde
    #    cualquier sitio sólo tienen sentido si el resto es desde la oficina.
    r"mix of both|work(ing)? from anywhere (for )?(up to )?\d+ (days|weeks)|"
    r"\d+ (days|weeks) (a|per) year (from anywhere|of remote|remote))"
)
RE_PRESENCIAL = re.compile(
    r"(presencial|on-?site|onsite|in-?person|en la oficina|nuestras? oficinas?|"
    r"not remote|no remote|not a remote|no es (un puesto )?remoto|"
    r"no (se admite|se permite|admite|permite) (el )?teletrabajo|"
    r"sin (opcion|opción) de teletrabajo|acudir a (la )?oficina|"
    r"asistencia (a|diaria) (la )?oficina|desde (la|nuestra) oficina|"
    r"from (our|the) office|based in (our|the) office|office[- ]based role\b|"
    # 30-sep-2026 (Harbour.Space): «Open to relocating to Barcelona» = hay
    # que vivir allí. «Relocation package» a secas NO: muchas remotas lo
    # ofrecen como opción.
    r"(open|willing|able) to relocat\w* to|must relocate|relocat\w* to (barcelona|madrid|valencia|"
    r"bilbao|sevilla|malaga|london|lisbon|berlin|paris|amsterdam|dublin))"
)
# Menciones de «presencial» que no son la modalidad del puesto: una reunión o
# un evento presencial de vez en cuando cabe en un 100 % remoto. Se quitan del
# texto antes de buscar RE_PRESENCIAL.
RE_PRESENCIAL_OCASIONAL = re.compile(
    r"((reunion|encuentro|evento|visita|jornada|quedada|formacion)(es|s)?( \w+){0,2} presencial(es)?|"
    r"presencial(es)? (opcional|puntual|ocasional)(es)?)"
)
RE_LOCAL = re.compile(
    r"(navarr|pamplona|iruña|gipuzkoa|guipuzcoa|san sebasti|donostia|irun|"
    r"tudela|mutilva|noain|estella|zarautz|tolosa)"
)
# 30-sep-2026: el endpoint de invitado de LinkedIn IGNORA `f_WT` (comprobado:
# f_WT=1, 2, 3 y sin f_WT devuelven exactamente las mismas ofertas, en el
# endpoint `seeMoreJobPostings` y en `/jobs/search`). Así que «salió en la
# búsqueda de remoto» no significa nada. Lo único del listado que sí apunta a
# remoto es una ubicación a nivel de país o región: las remotas de verdad se
# publican casi siempre como «Spain»/«España»/«European Union»/«EMEA», y las
# de oficina con la ciudad. De las 22 que Íñigo descartó a mano por
# presencial/híbrido tras entrar como «remoto sin confirmar», ninguna tenía
# ubicación a nivel país.
RE_UBICACION_PAIS = re.compile(
    r"^\s*(spain|espana|european union|union europea|european economic area|"
    r"espacio economico europeo|emea|europe|europa|eu|ue|worldwide|remote|remoto)\s*$"
)


def ubicacion_nivel_pais(ubicacion_norm):
    """¿La ubicación del listado es un país/región entero y no una ciudad?
    Se quita lo que vaya entre paréntesis («España (remoto)»)."""
    u = re.sub(r"\(.*?\)", " ", ubicacion_norm or "")
    return bool(RE_UBICACION_PAIS.match(u))


RE_NO_REMOTO = re.compile(
    r"(not remote|no remote|not a remote|no es (un puesto )?remoto|"
    r"no (se admite|se permite|admite|permite) (el )?teletrabajo|"
    r"sin (opcion|opción) de teletrabajo|"
    # 30-sep-2026 (Harbour.Space): «Not a fit if: you're looking for a
    # remote role».
    r"not a fit if[^.]{0,60}remote|(isn'?t|is not|not) (a )?(fully )?remote (role|position|job))"
)

_RE_MODALIDAD_JUNTO = re.compile(
    RE_REMOTO.pattern + "|" + RE_HIBRIDO.pattern + "|" + RE_PRESENCIAL.pattern
)


def frases_modalidad(texto_norm, maximo=3):
    """Hasta `maximo` frases con contexto donde el texto habla de modalidad.
    Se devuelven las frases, no un veredicto: quien decide es quien lee."""
    out = []
    for m in _RE_MODALIDAD_JUNTO.finditer(texto_norm or ""):
        out.append(_RE_WS.sub(" ", texto_norm[max(0, m.start() - 55):m.start() + 80]))
        if len(out) >= maximo:
            break
    return out


def modalidad(texto_norm, ubicacion_norm, etiqueta_remoto):
    """Clasifica la modalidad a partir de la descripción entera y de la
    etiqueta del portal. `etiqueta_remoto` es lo que dice el listado, que
    miente a menudo.

    Devuelve: remoto | hibrido | presencial | local | remoto_sin_confirmar |
    desconocida.

    OJO (16-sep-2026, heredado de common.js): esto clasificaba sólo con las 3
    primeras frases que `frases_modalidad` encontraba, en orden de aparición
    y mezclando los tres tipos. Una descripción que menciona «remote» tres
    veces en la cabecera y sólo dice «2 days a week in the office» más abajo
    agotaba las 3 frases antes de llegar ahí. Por eso `hib`/`pre` se
    comprueban sobre el texto COMPLETO; `frases_modalidad` sólo guarda
    contexto legible, no decide."""
    texto_norm = texto_norm or ""
    frases = frases_modalidad(texto_norm, 4)
    rem = bool(RE_REMOTO.search(texto_norm))
    hib = bool(RE_HIBRIDO.search(texto_norm))
    pre = bool(RE_PRESENCIAL.search(RE_PRESENCIAL_OCASIONAL.sub(" ", texto_norm)))
    negacion = bool(RE_NO_REMOTO.search(texto_norm))
    if negacion and not hib:
        tipo = "presencial"
    elif rem and not hib and not pre:
        tipo = "remoto"
    elif rem and (hib or pre):
        tipo = "hibrido"  # «remoto» como ventaja suelta, no como modalidad
    elif hib:
        tipo = "hibrido"
    elif pre:
        tipo = "presencial"
    elif etiqueta_remoto:
        tipo = "remoto_sin_confirmar"
    else:
        tipo = "desconocida"
    if RE_LOCAL.search(ubicacion_norm or "") and tipo != "remoto":
        tipo = "local"
    return {"tipo": tipo, "frases": frases}


def modalidades_aceptadas(cfg):
    """Qué tipos de `modalidad["tipo"]` dejan pasar la criba, según
    `config/filtros` (`buscar_remoto`/`buscar_hibrido`/`buscar_presencial`).
    `local` entra siempre. Sin `cfg` (o con los campos ausentes) se comporta
    como el valor por defecto del dashboard: sólo remoto."""
    cfg = cfg or {}
    s = {"local"}
    if cfg.get("buscar_remoto") is not False:
        s.add("remoto")
        s.add("remoto_sin_confirmar")
    if cfg.get("buscar_hibrido"):
        s.add("hibrido")
    if cfg.get("buscar_presencial"):
        s.add("presencial")
    return s


# ---- Ámbito ------------------------------------------------------------
_RE_AMBITO = re.compile(
    r"(must be (located|based|resident)[^.]{0,70}|eligible to work[^.]{0,70}|"
    r"authorized to work[^.]{0,70}|residir en[^.]{0,60}|"
    r"imprescindible residir[^.]{0,60}|only accepting[^.]{0,60}|"
    r"anywhere in the world|within the eu|across emea)"
)
_RE_AMBITO_MENCIONA = re.compile(r"\b(spain|espana|españa|eu\b|european union|emea|europe)\b")


def ambito(texto_norm):
    """¿Se puede firmar el contrato residiendo en España?"""
    m = _RE_AMBITO.search(texto_norm or "")
    menciona = bool(_RE_AMBITO_MENCIONA.search(texto_norm or ""))
    return {"restriccion": m.group(0) if m else "", "menciona_espana_o_ue": menciona}


# ---- Salario y experiencia ----------------------------------------------
_RE_SALARIO = re.compile(
    r"(\d{2}[.,]\d{3}\s*[-–a]{1,3}\s*\d{2}[.,]\d{3}\s*€?|\d{2}[.,]?\d{3}\s*€|"
    r"€\s*\d{2}[.,]?\d{3}|\$\s?\d{2,3}[,.]?\d{0,3}\s*[kK]?\s*[-–]\s*\$?\s?"
    r"\d{2,3}[,.]?\d{0,3}\s*[kK]?|\d{2,3}\s?k\s*[-–]\s*\d{2,3}\s?k)"
)


def salario(t):
    m = _RE_SALARIO.search(t or "")
    return m.group(0).strip() if m else ""


_RE_ANIOS = re.compile(
    r"(\d+\s*\+?\s*(?:-\s*\d+\s*)?(?:anos|años|years|year)\b|"
    r"al menos \d+[^,.]{0,20}|m[aá]s de \d+ a[nñ]os)"
)


def anios(texto_norm):
    m = _RE_ANIOS.search(texto_norm or "")
    return m.group(0).strip() if m else ""


# ---- Filtro de títulos ---------------------------------------------------
# Lo que evita el 80 % del trabajo: nunca se pide una ficha sin pasar esto.
RE_TITULO_OK = re.compile(
    r"(ai engineer|a\.i\. engineer|artificial intelligence|inteligencia artificial|"
    r"machine learning|ml engineer|ai\/ml|ai \/ ml|genai|gen ai|generative ai|"
    r"\bllm\b|nlp engineer|computer vision|vision por comput|data scientist|"
    r"cientific[oa] de datos|data engineer|ingenier[oa][\/ ]*a? de datos|"
    r"full[- ]?stack|backend|back[- ]end|software engineer|"
    r"ingenier[oa] de software|python developer|python engineer|"
    r"desarrollador python|mlops|applied scientist|research engineer|"
    r"forward deployed)"
)
RE_TITULO_NO = re.compile(
    r"(manager|director|head of|jefe|responsable|arquitect|architect|consultor|"
    r"consultant|analyst|analista|devops|\bsre\b|site reliability|sysadmin|\bqa\b|"
    r"tester|becari|internship|\bintern\b|practicas|sales|comercial|ventas|recruit|"
    r"profesor|docente|teacher|product owner|project manager|scrum|marketing|"
    r"designer|disenador|frontend|front-end|support|soporte|helpdesk|"
    r"tecnico de sistemas|administrativ|prompt engineer|trainer)"
)


def titulo_vale(titulo):
    t = norm(titulo)
    return bool(RE_TITULO_OK.search(t)) and not RE_TITULO_NO.search(t)
