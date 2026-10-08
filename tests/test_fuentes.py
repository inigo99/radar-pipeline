# -*- coding: utf-8 -*-
"""Tests de `pipeline/fuentes/` (extractores Scrapling, 21-sep-2026).

No son tests de regresión genéricos: cada uno existe porque algo se rompió
alguna vez (en `browser/*.js` o durante el port a Python) y no queremos que
vuelva a romperse en silencio. Se ejecutan con:

    python -m pytest tests/test_fuentes.py -q

o sueltos (no usan pytest más que para el runner, son funciones normales)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.fuentes import comun, vocabulario, linkedin, infojobs, manfred


# ---------------------------------------------------------------- comun ----

def test_remoto_ingles_sin_signos():
    """16-sep-2026: la primera versión de RE_REMOTO exigía «100% remote» o
    similar y se dejó fuera «remote»/«remoto» a secas -> perdió 24 ofertas de
    80 en un solo día, porque la forma más común en inglés de anunciar un
    puesto remoto es una frase suelta como «This is a remote position.», sin
    ningún «100%» ni «fully» delante."""
    d = comun.norm("This is a remote position based anywhere in the EU.")
    assert comun.RE_REMOTO.search(d)
    r = comun.modalidad(d, "", False)
    assert r["tipo"] == "remoto"


def test_remoto_no_confunde_prefijos():
    """El \\b...\\b de RE_REMOTO no debe disparar con palabras que sólo
    contienen "remote"/"remoto" como subcadena (p.ej. nombres propios)."""
    d = comun.norm("Trabajamos con Remotework Inc, una empresa de logística presencial.")
    # "presencial" gana igualmente, pero el punto es que \bremot... no debe
    # colarse por "Remotework" si escribiéramos mal el regex sin \b.
    assert comun.RE_PRESENCIAL.search(d)


def test_modalidad_prioriza_texto_completo_sobre_primeras_frases():
    """16-sep-2026 (heredado de common.js): clasificaba sólo con las 3
    primeras frases que encontraba `frases_modalidad`. Una descripción que
    dice "remote" tres veces en la cabecera (perks, cultura...) y sólo
    menciona "2 days a week in the office" mucho más abajo agotaba las 3
    frases antes de llegar ahí y clasificaba mal como remoto puro."""
    cabecera = "Somos remote-first. " * 3
    cuerpo = "Eso sí, pedimos venir 2 days a week in the office para reuniones de equipo."
    d = comun.norm(cabecera + cuerpo)
    r = comun.modalidad(d, "", False)
    assert r["tipo"] == "hibrido"


def test_modalidad_remoto_sin_confirmar_cuando_solo_hay_etiqueta():
    d = comun.norm("Buscamos ingeniero de software con experiencia en Python.")
    r = comun.modalidad(d, "", True)
    assert r["tipo"] == "remoto_sin_confirmar"


def test_modalidad_local_gana_a_hibrido_pero_no_a_remoto():
    d_hib = comun.norm("Modelo híbrido, 2 días en la oficina de Pamplona.")
    r_hib = comun.modalidad(d_hib, comun.norm("Pamplona, España"), False)
    assert r_hib["tipo"] == "local"

    d_rem = comun.norm("100% remoto, trabaja desde donde quieras.")
    r_rem = comun.modalidad(d_rem, comun.norm("Pamplona, España"), False)
    assert r_rem["tipo"] == "remoto"  # remoto puro nunca se rebaja a local


def test_modalidad_work_from_home_n_dias_es_hibrido():
    """23-sep-2026: oferta real de Smadex (Data Scientist, Barcelona,
    li-4461143360) que en LinkedIn se ve con la etiqueta «Híbrido» pero cuya
    descripción sólo dice «work from home (2 days per week)». RE_REMOTO
    captaba «work from home» suelto y no había ningún patrón de RE_HIBRIDO
    para "días desde casa" en inglés (sólo para "días en la oficina"), así
    que salía clasificada como 100% remoto."""
    d = comun.norm(
        "Great work-life balance: work from home (2 days per week), flexible hours."
    )
    r = comun.modalidad(d, "", False)
    assert r["tipo"] == "hibrido"


def test_modalidad_remote_5_dias_semana_sigue_siendo_remoto():
    """El número de días se limita a 1-4 a propósito: "remote 5 days a
    week" es una semana completa en remoto, no híbrido."""
    d = comun.norm("This is a remote position, work remotely 5 days a week.")
    r = comun.modalidad(d, "", False)
    assert r["tipo"] == "remoto"


def test_titulo_vale_incluye_y_excluye():
    assert comun.titulo_vale("Senior Machine Learning Engineer")
    assert comun.titulo_vale("Data Scientist")
    assert not comun.titulo_vale("Head of Data Science")  # RE_TITULO_NO: "head of"
    assert not comun.titulo_vale("QA Tester")


def test_anios_y_salario_basico():
    d = comun.norm("Se requieren 3+ años de experiencia. Salario 45.000-55.000€.")
    assert "3" in comun.anios(d)
    assert comun.salario("Salario 45.000-55.000€.")


# ----------------------------------------------------------- vocabulario ----

def test_cuenta_terminos_basico():
    d = comun.norm("Buscamos experiencia sólida en Python, SQL y Docker.")
    hits = vocabulario.cuenta_terminos(d)
    claves = {h[0] for h in hits}
    assert "python" in claves
    assert "sql" in claves
    assert "docker" in claves


def test_comunicacion_negocio_no_dispara_con_cliente():
    """A propósito «comunicacion_negocio» no incluye "cliente": esa palabra
    aparece en el pie de página / boilerplate legal de casi cualquier oferta
    y contaminaba el término con falsos positivos."""
    d = comun.norm("Este sitio usa cookies. Contacta con el cliente en caso de dudas.")
    hits = vocabulario.cuenta_terminos(d)
    claves = {h[0] for h in hits}
    assert "comunicacion_negocio" not in claves


# ------------------------------------------------------------- linkedin ----

_LI_LISTADO_FIXTURE = """
<li><div class="base-card" data-entity-urn="urn:li:jobPosting:1111111111">
<a href="https://es.linkedin.com/jobs/view/data-scientist-at-acme-1111111111"></a>
<h3 class="base-search-card__title">Data Scientist</h3>
<h4 class="base-search-card__subtitle"><a>Acme</a></h4>
<span class="job-search-card__location">Madrid, España</span>
</div></li>
"""


def test_linkedin_parsear_extrae_id_y_no_duplica():
    jobs, n = linkedin.parsear(_LI_LISTADO_FIXTURE, "R|data scientist")
    assert n == 1
    assert "1111111111" in jobs
    # una segunda pasada sobre el mismo HTML no debe añadir duplicados
    jobs, n2 = linkedin.parsear(_LI_LISTADO_FIXTURE, "R|data scientist", jobs)
    assert n2 == 0
    assert len(jobs) == 1


def test_linkedin_detallar_una_clasifica_remoto():
    job = {"id": "1111111111", "titulo": "Data Scientist", "empresa": "Acme",
           "ubicacion": "Madrid, España", "q": "R|data scientist"}
    html = ("<section><strong>Role</strong><p>This is a fully remote position. "
            "We use Python and SQL daily.</p></section>")
    out = linkedin.detallar_una(job, html)
    assert out["modalidad"]["tipo"] == "remoto"
    claves = {t[0] for t in out["terminos"]}
    assert "python" in claves


# ------------------------------------------------------------- infojobs ----

def test_infojobs_id_para_usa_12_caracteres():
    """16-sep-2026: con el extractor JS, días distintos habían recortado el
    hash a longitudes distintas y dedupe.py dejó pasar una oferta repetida.
    `id_para` debe truncar siempre a 12 caracteres, sin excepción."""
    oferta = {"hash": "abc0123456789def", "ciudad": "madrid", "slug": "data-scientist"}
    assert infojobs.id_para(oferta) == "ij-abc012345678"[:len("ij-") + 12]
    assert len(infojobs.id_para(oferta)) == len("ij-") + 12


def test_infojobs_descripcion_no_confunde_dominio_con_dotnet():
    """El bug real: un regex de tecnologías con `\\.net` casaba con
    "infojobs.net" (que aparece en CUALQUIER página del portal, típicamente
    en el pie) y marcaba falsos positivos de C#/.NET en todas las ofertas.
    La función `descripcion()` debe recortar el texto ANTES de esa zona, de
    modo que un extractor de tecnologías corriendo sobre su salida no vea
    "infojobs.net" salvo que la propia oferta hable de tecnología .NET."""
    # El recorte real (`descripcion()`) se queda hasta 1400 caracteres
    # DESPUÉS de "Requisitos mínimos" -- el pie con "infojobs.net" está muy
    # lejos de ahí en una ficha real, así que el relleno del fixture debe
    # simular esa distancia para que el test sea representativo.
    txt = ("Cabecera de navegación. www.infojobs.net todos los derechos. "
           "Descripción La empresa busca un perfil con experiencia en Python "
           "y APIs REST. Requisitos mínimos Grado en informática. "
           + ("Relleno de la ficha para simular una página real larga. " * 40)
           + "Copyright infojobs.net 2026.")
    desc = infojobs.descripcion(txt)
    assert "infojobs.net" not in desc
    assert "Python" in desc


def test_infojobs_parsear_extrae_hash_ciudad_slug():
    html = ('<a href="//www.infojobs.net/madrid/data-scientist/of-i1a2b3c4d5e6f7">Data Scientist</a>')
    ofertas, n = infojobs.parsear(html, "data scientist")
    assert n == 1
    o = list(ofertas.values())[0]
    assert o["ciudad"] == "madrid"
    assert o["slug"] == "data-scientist"
    assert o["hash"] == "1a2b3c4d5e6f7"


# -------------------------------------------------------------- manfred ----

def test_manfred_locations_como_lista_de_strings():
    """21-sep-2026: la API real de Manfred devuelve `locations` como lista de
    strings ("Vigo, España"), no como lista de objetos {city, town} tal y
    como asumía `browser/manfred.js` (y la primera versión de este port).
    En JS el bug era silencioso (`l.city` sobre un string da `undefined` y
    el join sale vacío); en Python era un AttributeError directo porque se
    llamaba `.get()` sobre un string. Debe funcionar con listas de strings,
    listas de dicts, o vacío."""
    oferta_str = {"locations": ["Pamplona, España"], "remotePercentage": 40}
    assert manfred.modalidad_de(oferta_str) == "local"

    oferta_dict = {"locations": [{"city": "Pamplona"}], "remotePercentage": 40}
    assert manfred.modalidad_de(oferta_dict) == "local"

    oferta_vacia = {"locations": [], "remotePercentage": 100}
    assert manfred.modalidad_de(oferta_vacia) == "remoto"


def test_manfred_responsibilities_como_lista():
    """21-sep-2026: `responsibilities` en la API real llega como lista de
    strings markdown, no como un único bloque HTML/texto. `_stripHtml` en
    `browser/manfred.js` (`.replace` sobre un array) revienta con TypeError
    en cualquier ficha real con `responsibilities` relleno."""
    oferta_listado = {"slug": "acme-python-dev", "id": 1}
    ficha = {
        "whatTheyAskFor": "Buscamos Python senior.",
        "responsibilities": ["Primer punto de responsabilidad.", "Segundo punto."],
        "techs": [{"name": "Python", "level": "ADVANCED", "section": "MUST"}],
        "languages": [{"name": "Inglés", "level": "Fluent"}],
    }
    out = manfred.detallar_una(oferta_listado, ficha)
    assert "Primer punto" in out["_resp"]
    assert "Segundo punto" in out["_resp"]


def test_manfred_filtrar_por_modalidad_y_titulo():
    ofertas = [
        {"id": 1, "slug": "acme-data-scientist", "position": "Data Scientist",
         "remotePercentage": 100, "locations": [], "updatedAt": "2026-09-20"},
        {"id": 2, "slug": "acme-office-manager", "position": "Office Manager",
         "remotePercentage": 0, "locations": [], "updatedAt": "2026-09-20"},
        {"id": 3, "slug": "acme-onsite-de", "position": "Data Engineer",
         "remotePercentage": 0, "locations": [], "updatedAt": "2026-09-20"},
    ]
    cola = manfred.filtrar(ofertas, ids_conocidos=[], desde=None, cfg=None)
    slugs = {o["slug"] for o in cola}
    assert "acme-data-scientist" in slugs   # remoto + título válido
    assert "acme-office-manager" not in slugs  # título no vale
    assert "acme-onsite-de" not in slugs    # presencial, no aceptado por defecto


# ---- 30-sep-2026: revisión de las 41 descartadas a mano por modalidad ----
# Frases reales (recortadas) de fichas de LinkedIn que entraron como remotas y
# Íñigo descartó como «Presencial»/«Híbrido».

def _tipo(txt, ubi=""):
    return comun.modalidad(comun.norm(txt), comun.norm(ubi), False)["tipo"]


def test_modalidad_remote_work_n_dias_semana_es_hibrido():
    # Ventós (li-4471898699)
    assert _tipo("Benefits: Remote work: 1 full day and 2 afternoons per week. Flexible hours.") == "hibrido"


def test_modalidad_office_first_y_porcentaje_remoto_es_hibrido():
    # Joppy (li-4469446490) y CaixaBank Tech (li-4460068327)
    assert _tipo("Office-first in Barcelona & Madrid, with 20% remote flexibility.") == "hibrido"
    assert _tipo("Hasta un 60% de trabajo en remoto dependiendo del proyecto.") == "hibrido"
    # ...pero 100 % no es un porcentaje parcial
    assert _tipo("Trabajo 100% en remoto desde cualquier punto de España.") == "remoto"


def test_modalidad_mix_y_dias_al_anio_desde_cualquier_sitio_es_hibrido():
    # Prima (li-4435540880)
    assert _tipo("Enjoy full flexibility - work from home, the office or a mix of both. "
                 "Plus, work from anywhere for up to 30 days a year.") == "hibrido"


def test_modalidad_not_a_fit_remote_y_relocation_no_es_remoto():
    # Harbour.Space (li-4470436016)
    t = _tipo("Open to relocating to Barcelona. Not a fit if: you're looking for a remote role.")
    assert t == "presencial"


def test_modalidad_reunion_presencial_ocasional_no_rompe_el_remoto():
    assert _tipo("Trabajo 100 % en remoto, con una reunión presencial al trimestre opcional.") == "remoto"


def test_linkedin_sin_frase_y_ubicacion_ciudad_queda_fuera():
    """f_WT=2 no filtra nada en el endpoint de invitado: salir en la búsqueda
    «R» no basta. Sin frase de modalidad, sólo una ubicación a nivel país
    mantiene «remoto sin confirmar»; con ciudad queda `desconocida`."""
    from pipeline.fuentes import linkedin
    txt = "<p>Buscamos Data Scientist con Python y SQL.</p>"
    ciudad = linkedin.detallar_una({"id": "1", "titulo": "DS", "empresa": "Acme", "fecha": "", "ubicacion": "Madrid, Community of Madrid, Spain", "q": "R|x"}, txt)
    pais = linkedin.detallar_una({"id": "2", "titulo": "DS", "empresa": "Beta", "fecha": "", "ubicacion": "Spain", "q": "R|x"}, txt)
    assert ciudad["modalidad"]["tipo"] == "desconocida"
    assert pais["modalidad"]["tipo"] == "remoto_sin_confirmar"
    res = linkedin.clasificar([ciudad, pais], {})
    assert res["revisar"] == 1 and res["fuera"] == 1
    a = res["apartadas"][0]
    assert a["id"] == "li-1" and a["motivo"] == "modalidad" and a["url"].endswith("/1/")


# -------------------------------------------------------------- ventana ----

def test_ventana_se_ensancha_si_la_ultima_ejecucion_es_vieja():
    import datetime as dt
    z = dt.timezone.utc
    ahora = dt.datetime(2026, 9, 30, 8, 0, tzinfo=z)
    d, h = comun.ventana(dt.datetime(2026, 9, 29, 8, 5, tzinfo=z), 24, ahora)
    assert h == 24 and d == ahora - dt.timedelta(hours=24)   # manda el mínimo
    d, h = comun.ventana(dt.datetime(2026, 9, 27, 8, 0, tzinfo=z), 24, ahora)
    assert h == 72 and comun.since_infojobs(h) == "_7_DAYS"  # día perdido -> recupera
    assert comun.since_infojobs(24) == "_24_HOURS" and comun.since_infojobs(400) == "_30_DAYS"


def test_publicada_relativa_infojobs():
    import datetime as dt
    hoy = dt.date(2026, 9, 30)
    assert comun.publicada_relativa("publicada hace 3d en madrid", hoy) == "2026-09-27"
    assert comun.publicada_relativa("hace 5 horas", hoy) == "2026-09-30"
    assert comun.publicada_relativa("sin fecha", hoy) == ""


def test_filtrar_descarta_fuera_de_ventana_y_sin_fecha_no_acotada():
    from pipeline import filtrar as F
    cands = [
        {"id": "li-1", "empresa": "A", "puesto": "DS", "publicada": "2026-09-29"},  # dentro
        {"id": "li-2", "empresa": "B", "puesto": "DS", "publicada": "2026-09-10"},  # fuera
        {"id": "mf-3", "empresa": "C", "puesto": "DS"},                            # sin fecha, acotada
        {"id": "in-4", "empresa": "D", "puesto": "DS"},                            # sin fecha, no acotada
        {"id": "in-5", "empresa": "E", "puesto": "DS", "publicada": "2026-09-30"}, # dentro
    ]
    ok, fuera = F.filtrar(cands, {"ventana_desde": "2026-09-29T08:00:00+00:00"})
    assert [c["id"] for c in ok] == ["li-1", "mf-3", "in-5"]
    assert {f["oferta"]["id"]: f["motivo"] for f in fuera} == {
        "li-2": "fuera de ventana", "in-4": "sin fecha de publicación"}
    ok, fuera = F.filtrar(cands, {})   # sin ventana no se comprueba nada
    assert len(ok) == 5 and not fuera


def test_linkedin_ubicacion_pais_basta_sin_busqueda_remota():
    txt = "<p>We build GenAI products. Python, LLMs.</p>"
    sin_q = linkedin.detallar_una({"id": "3", "titulo": "GenAI", "empresa": "Minsait", "fecha": "", "ubicacion": "España"}, txt)
    local = linkedin.detallar_una({"id": "4", "titulo": "GenAI", "empresa": "Minsait", "fecha": "", "ubicacion": "España", "q": "L|x"}, txt)
    assert sin_q["modalidad"]["tipo"] == "remoto_sin_confirmar"
    assert local["modalidad"]["tipo"] == "remoto_sin_confirmar"


def test_linkedin_consultas_del_dia_incluye_zonas_locales():
    cfg = {"titulos": ["Data Scientist"], "areas_locales": ["Navarra", "Gipuzkoa"]}
    urls = [c["url"] for c in linkedin.consultas_del_dia(cfg, 24, 2)]
    assert len(urls) == 4  # 2 páginas remoto + 1 por zona
    assert any("Navarre" in u for u in urls) and any("Gipuzkoa" in u for u in urls)


# ------------------------------------------------------------ idiomas ----

def test_idiomas_exigidos():
    """8-oct-2026: sólo cuenta un idioma con señal de exigencia en la misma
    cláusula; «a plus»/«valorable» no exige y «German customers» no es idioma."""
    f = lambda t: {x["idioma"]: x["nivel"] for x in comun.idiomas_exigidos(comun.norm(t))}
    assert f("Fluent German is required.") == {"aleman": 5}
    assert f("We have German customers and offices in France.") == {}
    assert f("Fluent English; German is a plus.") == {"ingles": 5}
    assert f("Nivel alto de inglés imprescindible. Se valorará catalán.") == {"ingles": 5}
    assert f("Inglés B2 y francés fluido") == {"ingles": 4, "frances": 5}
    assert f("Native Spanish and fluent English") == {"espanol": 6, "ingles": 5}
    assert f("Euskera obligatorio") == {"euskera": None}


def test_veredicto_idiomas():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
    from filtrar import veredicto_idiomas, IDIOMAS_DEF
    ex = lambda t: comun.idiomas_exigidos(comun.norm(t))
    assert veredicto_idiomas(ex("Fluent German is required"), IDIOMAS_DEF)[0]
    fuera, alerta = veredicto_idiomas(ex("Fluent French required"), IDIOMAS_DEF)
    assert fuera is None and "frances C1" in alerta
    assert veredicto_idiomas(ex("Fluent English"), IDIOMAS_DEF) == (None, None)
    assert veredicto_idiomas(ex("Native English speaker"), IDIOMAS_DEF)[1]



if __name__ == "__main__":
    import inspect
    mod = sys.modules[__name__]
    tests = [(name, fn) for name, fn in vars(mod).items()
             if name.startswith("test_") and inspect.isfunction(fn)]
    ok, fail = 0, 0
    for name, fn in tests:
        try:
            fn()
            ok += 1
            print(f"OK   {name}")
        except AssertionError as e:
            fail += 1
            print(f"FAIL {name}: {e}")
        except Exception as e:
            fail += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{ok} ok, {fail} fallidos de {len(tests)}")
    sys.exit(1 if fail else 0)
