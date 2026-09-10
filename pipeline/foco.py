# -*- coding: utf-8 -*-
"""A cuál conviene echar hoy: el orden por «foco».

El radar ya sabía puntuar el encaje (`score_adap`) y empujar las familias de
IA/Data Science (`prioridad`). Lo que no sabía es que **ese número ya no
distingue**: con el perfil ampliado del 10 sep 2026, la cobertura ponderada
media de las ofertas es del 93,7 % y la mediana del 100 %. Ordenar por encaje
es, a estas alturas, ordenar por ruido — casi todo empata arriba.

`foco` no intenta adivinar quién va a contestar (con 15 candidaturas no hay
muestra para eso). Sólo aparta lo que **ya se sabe que no va a llegar a
ninguna parte**, que es una cosa distinta y sí está documentada en sus propias
notas del dashboard:

  - **Ofertas viejas.** Una oferta de hace tres semanas suele estar cerrada o
    con la criba hecha. El barrido de cerradas salió de la tarea diaria el 9 sep
    2026, así que nadie las está retirando.
  - **Títulos de sénior / lead / arquitecto.** Seis de sus dieciocho descartes
    manuales fueron literalmente «piden 5 años», «entre 6 y 9 años»,
    «7+ years»: el filtro real no es la tecnología, es la antigüedad.
  - **Salario sin publicar.** No es motivo para descartar, pero entre dos
    ofertas parecidas, la que publica banda ahorra una ronda entera.

Cada factor es un multiplicador sobre `prioridad`, y cada oferta se lleva un
`motivo_foco` que dice en una línea por qué está donde está. `score_adap` y
`prioridad` no se tocan: siguen ahí para ordenar por ellos cuando quiera.
"""
import datetime
import re

# Títulos que en la práctica se le cierran por antigüedad. «Senior» dentro de
# «Senior Analyst» cuenta igual: lo que filtra es la palabra en el anuncio.
SENIOR = re.compile(
    r"\b(senior|s[eé]nior|sr\.?|lead|principal|staff|head\s+of|arquitect[oa]|architect|"
    r"manager|director|expert[oa]?|chief)\b", re.I)

# Ventanas de frescura, en días desde la publicación.
FRESCURA = [(7, 1.00, ""),
            (14, 0.85, "publicada hace más de una semana"),
            (21, 0.55, "publicada hace más de dos semanas"),
            (10 ** 6, 0.25, "publicada hace más de tres semanas: probablemente cerrada")]

PENALIZACION_SENIOR = 0.55
BONUS_SALARIO_PUBLICADO = 1.06


def dias_desde(publicada, hoy=None):
    """Días entre la publicación y hoy. None si la fecha no se puede leer."""
    hoy = hoy or datetime.date.today()
    try:
        return (hoy - datetime.date.fromisoformat(str(publicada)[:10])).days
    except (ValueError, TypeError):
        return None


def _frescura(dias):
    if dias is None:
        return 1.0, ""
    for tope, factor, nota in FRESCURA:
        if dias <= tope:
            return factor, nota
    return FRESCURA[-1][1], FRESCURA[-1][2]


def es_senior(puesto):
    return bool(SENIOR.search(puesto or ""))


def calcula(oferta, prioridad, hoy=None):
    """Devuelve (foco, dias, motivo). `prioridad` es la que ya calcula puntuar.py."""
    dias = dias_desde(oferta.get("publicada"), hoy)
    factor, nota_fecha = _frescura(dias)
    motivos = [nota_fecha] if nota_fecha else []

    if es_senior(oferta.get("puesto", "")):
        factor *= PENALIZACION_SENIOR
        motivos.append("el título pide un perfil sénior o de arquitecto")

    if oferta.get("sal_origen") == "publicado":
        factor *= BONUS_SALARIO_PUBLICADO
        motivos.append("publica la banda salarial")

    return round(prioridad * factor, 1), dias, "; ".join(motivos)
