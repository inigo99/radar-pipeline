# -*- coding: utf-8 -*-
"""Los años de experiencia: los que pide la oferta contra los que tiene el CV.

El filtro que faltaba. De los dieciocho descartes manuales del 10 sep 2026, seis
eran literalmente antigüedad —«Experiencia mínima: Más de 5 años», «Piden entre
6 y 9 años», «7+ years of total experience»—, y el radar no lo miraba: ponía
esas ofertas arriba con un encaje del 100 % porque la tecnología sí encajaba.

Dos piezas:

- **`anios_perfil(perfil)`** suma los meses de los puestos del CV (el campo
  `fechas` de `perfil_llm.experiencia`) y los devuelve en años. Sale del CV, así
  que **sube solo** con el tiempo y no hay que acordarse de tocar una constante.
  Al 10 sep 2026: Orisha 2,5 + Veridas 0,7 = **3,2 años**.
- **`anios_pedidos(...)`** saca los años que exige un anuncio de su texto.

`clasifica()` cruza las dos y devuelve `encaja`, `justo` (se pasa dentro del
margen: se aparta, pero se ve en «Filtradas»), `lejos` o `desconocido`. La
mayoría de los anuncios no dicen años: **la ausencia de dato nunca aparta una
oferta**, igual que la ausencia de frase de modalidad no la descarta.

El margen y los años del perfil se pueden fijar a mano en `config/filtros`
(`margen_anios`, `anios_perfil`); con `anios_perfil` a null se calcula del CV.
"""
import re

MARGEN_DEF = 1.0          # años por encima de los suyos que aún cuentan como «por poco»

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}
_MES = "|".join(sorted(MESES, key=len, reverse=True))
# «septiembre 2023 – marzo 2026» y «julio–septiembre 2021», con guion normal o largo.
_TRAMO = re.compile(
    rf"({_MES})\s*(\d{{4}})?\s*[–—-]\s*({_MES})\s*(\d{{4}})", re.I)

# Lo que dice un anuncio cuando exige antigüedad. Se coge el MÁXIMO de lo que
# aparezca: si pide «2 años con Python y 5 de experiencia total», manda el 5.
PATRONES = [
    r"(?:m[áa]s de|al menos|m[íi]nim[oa](?:\s+de)?|desde|a partir de)\s*(\d{1,2})\s*a[ñn]os",
    r"entre\s*(\d{1,2})\s*y\s*\d{1,2}\s*a[ñn]os",
    r"(\d{1,2})\s*\+\s*(?:years|a[ñn]os)",
    r"(\d{1,2})\s*(?:or more|o m[áa]s)\s*(?:years|a[ñn]os)",
    r"(?:at least|minimum of|a minimum of|over)\s*(\d{1,2})\s*years",
    r"(\d{1,2})\s*years?\s+of\s+(?:professional\s+|relevant\s+|hands-on\s+|total\s+)?experience",
    r"(\d{1,2})\s*a[ñn]os\s+de\s+experiencia",
    r"experiencia\s+m[íi]nima[^0-9]{0,20}(\d{1,2})",
]


def _meses_tramo(m):
    ini_mes, ini_anio, fin_mes, fin_anio = m.groups()
    fin_anio = int(fin_anio)
    ini_anio = int(ini_anio) if ini_anio else fin_anio      # «julio–septiembre 2021»
    ini = ini_anio * 12 + MESES[ini_mes.lower()]
    fin = fin_anio * 12 + MESES[fin_mes.lower()]
    return max(0, fin - ini + 1)                            # ambos meses cuentan


def anios_perfil(perfil, defecto=3.0):
    """Años de experiencia profesional que suman los puestos del CV.

    Lee `perfil_llm.experiencia[].fechas`. Si no hay nada parseable devuelve
    `defecto`: mejor un número razonable que un filtro que se desmadra.
    """
    meses = 0
    for puesto in (perfil.get("perfil_llm") or {}).get("experiencia", []):
        for m in _TRAMO.finditer(puesto.get("fechas", "") or ""):
            meses += _meses_tramo(m)
    return round(meses / 12.0, 1) if meses else defecto


def anios_pedidos(*textos):
    """Años que exige el anuncio, o None si no lo dice."""
    vistos = []
    for t in textos:
        t = (t or "").lower()
        for p in PATRONES:
            for m in re.finditer(p, t):
                try:
                    n = int(m.group(1))
                except (TypeError, ValueError):
                    continue
                if 0 < n <= 25:                 # 30 años de experiencia es una errata
                    vistos.append(n)
    return max(vistos) if vistos else None


def clasifica(anios_min, mios, margen=MARGEN_DEF):
    """(estado, nota) con estado en encaja | justo | lejos | desconocido."""
    if anios_min is None:
        return "desconocido", "La oferta no dice cuántos años pide."
    falta = anios_min - mios
    if falta <= 0.001:
        return "encaja", f"Pide {anios_min} años y tienes {mios}."
    if falta <= margen + 0.001:
        return "justo", (f"Pide {anios_min} años y tienes {mios}: te faltan "
                         f"{round(falta, 1)}. Se puede defender, pero es la primera criba.")
    return "lejos", (f"Pide {anios_min} años y tienes {mios}: te faltan "
                     f"{round(falta, 1)}.")
