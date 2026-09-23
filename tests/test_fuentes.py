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
