# -*- coding: utf-8 -*-
"""El embudo de candidaturas: ¿esto está funcionando?

Cruza `estado` (lo que Íñigo marca en el dashboard) con `correo` (lo que
contestan las empresas) y responde a tres preguntas que el radar no se hacía:

  1. ¿Qué fuente convierte? Meter 40 ofertas al día de un portal que nunca
     contesta es trabajo tirado.
  2. ¿La puntuación predice algo? Si las ofertas de 60 % convierten igual que
     las de 95 %, el modelo de `reqs` no se está ganando el sitio y hay que
     cambiarlo, no seguir puliéndolo.
  3. ¿Qué empresas están saturadas? Diez candidaturas a la misma consultora sin
     una sola respuesta es una señal, no mala suerte.

    python pipeline/embudo.py        # -> data/embudo.json, y un resumen por consola

Definiciones, para que los números signifiquen algo:
  - **candidatura**: documento en `estado` con `estado == "aplicada"`.
  - **respuesta**: novedad en `correo` de tipo `avance` o `rechazo`. Un acuse de
    recibo automático NO cuenta como respuesta: lo manda el ATS, no una persona.
  - **viva**: candidatura sin rechazo y con fase distinta de `rechazada`.
  - **tasa de respuesta**: respuestas / candidaturas. Con menos de 5
    candidaturas en un grupo no se imprime porcentaje: no significaría nada.
"""
import datetime, json, os

DATA = os.environ.get("RADAR_DATA", "data")
MIN_MUESTRA = 5
TRAMOS = [(0, 60, "< 60 %"), (60, 75, "60-75 %"), (75, 90, "75-90 %"), (90, 101, "90 % +")]


def _leer(nombre, defecto):
    p = os.path.join(DATA, nombre)
    if not os.path.exists(p):
        return defecto
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _dias(desde, hasta):
    try:
        a = datetime.date.fromisoformat(str(desde)[:10])
        b = datetime.date.fromisoformat(str(hasta)[:10])
    except ValueError:
        return None
    return (b - a).days


def _tramo(score):
    for lo, hi, etiqueta in TRAMOS:
        if lo <= score < hi:
            return etiqueta
    return TRAMOS[-1][2]


def _vacio():
    return dict(candidaturas=0, acuses=0, avances=0, rechazos=0, vivas=0, sin_respuesta=0)


def _rechazada(cand):
    """Un rechazo cuenta tanto si lo dice el correo como si él ya movió la fase."""
    return cand["novedad"] == "rechazo" or cand["fase"] == "rechazada"


def _respondida(cand):
    """Respuesta = una persona se movió. Un acuse automático del ATS no lo es."""
    return _rechazada(cand) or cand["novedad"] == "avance"


def _suma(grupo, cand):
    grupo["candidaturas"] += 1
    if cand["novedad"] == "acuse":
        grupo["acuses"] += 1
    if _rechazada(cand):
        grupo["rechazos"] += 1
    else:
        grupo["vivas"] += 1
        if cand["novedad"] == "avance":
            grupo["avances"] += 1
    if not _respondida(cand):
        grupo["sin_respuesta"] += 1


def _tasa(g):
    """Respuestas humanas sobre candidaturas, o None si la muestra es ridícula."""
    if g["candidaturas"] < MIN_MUESTRA:
        return None
    return round(100.0 * (g["avances"] + g["rechazos"]) / g["candidaturas"], 1)


def calcular():
    estado = _leer("estado.json", {})
    correo = _leer("correo.json", {})
    ofertas = {o["id"]: o for o in _leer("ofertas.json", [])}
    tailor = _leer("tailor.json", {})
    scores = {r["id"]: r.get("score_adap", 0) for r in _leer("resultado.json", [])}
    hoy = datetime.date.today().isoformat()

    candidaturas = []
    for oid, s in estado.items():
        if s.get("estado") != "aplicada":
            continue
        o = ofertas.get(oid, {})
        nov = (correo.get(oid) or {}).get("tipo", "")
        fecha_nov = (correo.get(oid) or {}).get("fecha", "")
        aplicada = s.get("fechaAplicacion", "")
        candidaturas.append(dict(
            id=oid,
            empresa=o.get("empresa", "—"),
            puesto=o.get("puesto", "—"),
            fuente=o.get("fuente", "—"),
            familia=(tailor.get(oid) or {}).get("familia", "—"),
            score=scores.get(oid, 0),
            fase=s.get("fase", "aplicada"),
            novedad=nov,
            aplicada=aplicada,
            dias_hasta_respuesta=_dias(aplicada, fecha_nov)
                if (aplicada and fecha_nov and nov in ("avance", "rechazo")) else None,
            dias_esperando=None,   # se rellena abajo, cuando ya se sabe si respondieron
        ))
    for c in candidaturas:
        if aplicada := c["aplicada"]:
            if not _respondida(c):
                c["dias_esperando"] = _dias(aplicada, hoy)

    total = _vacio()
    por_fuente, por_familia, por_tramo = {}, {}, {}
    for c in candidaturas:
        _suma(total, c)
        _suma(por_fuente.setdefault(c["fuente"], _vacio()), c)
        _suma(por_familia.setdefault(c["familia"], _vacio()), c)
        _suma(por_tramo.setdefault(_tramo(c["score"]), _vacio()), c)

    for grupo in (por_fuente, por_familia, por_tramo):
        for g in grupo.values():
            g["tasa_respuesta"] = _tasa(g)
    total["tasa_respuesta"] = _tasa(total)

    esperas = [c["dias_hasta_respuesta"] for c in candidaturas
               if c["dias_hasta_respuesta"] is not None]
    esperas.sort()
    total["dias_mediana_respuesta"] = esperas[len(esperas) // 2] if esperas else None

    # Empresas saturadas: muchas ofertas suyas en el radar y ningún movimiento.
    empresas = {}
    for o in ofertas.values():
        e = empresas.setdefault(o.get("empresa", "—"), dict(en_radar=0, aplicadas=0, respuestas=0))
        e["en_radar"] += 1
    for c in candidaturas:
        e = empresas.setdefault(c["empresa"], dict(en_radar=0, aplicadas=0, respuestas=0))
        e["aplicadas"] += 1
        if c["novedad"] in ("avance", "rechazo"):
            e["respuestas"] += 1
    saturadas = sorted(
        ({"empresa": k, **v} for k, v in empresas.items()
         if v["en_radar"] >= 4 or v["aplicadas"] >= 3),
        key=lambda x: (-x["en_radar"], -x["aplicadas"]))[:12]

    # Las que llevan más tiempo esperando, para decidir si toca insistir.
    esperando = sorted((c for c in candidaturas if c["dias_esperando"] is not None),
                       key=lambda c: -c["dias_esperando"])[:10]

    return dict(
        generado=hoy,
        total=total,
        por_fuente=por_fuente,
        por_familia=por_familia,
        por_tramo=por_tramo,
        saturadas=saturadas,
        esperando=[{k: c[k] for k in ("id", "empresa", "puesto", "dias_esperando", "aplicada")}
                   for c in esperando],
        n_ofertas=len(ofertas),
    )


def _fila(nombre, g):
    tasa = "—" if g["tasa_respuesta"] is None else f"{g['tasa_respuesta']:>5.1f} %"
    return (f"{nombre[:24]:<25}{g['candidaturas']:>6}{g['avances']:>8}"
            f"{g['rechazos']:>10}{g['sin_respuesta']:>14}  {tasa}")


def main():
    emb = calcular()
    with open(os.path.join(DATA, "embudo.json"), "w", encoding="utf-8") as fh:
        json.dump(emb, fh, ensure_ascii=False, indent=1)

    t = emb["total"]
    print(f"\n{t['candidaturas']} candidaturas sobre {emb['n_ofertas']} ofertas en el radar. "
          f"{t['avances']} con avance, {t['rechazos']} rechazadas, "
          f"{t['sin_respuesta']} sin respuesta humana.")
    if t["dias_mediana_respuesta"] is not None:
        print(f"Mediana hasta la primera respuesta: {t['dias_mediana_respuesta']} días.")
    if t["tasa_respuesta"] is None:
        print(f"(Menos de {MIN_MUESTRA} candidaturas: los porcentajes aún no dicen nada.)")

    cab = f"{'':<25}{'CAND':>6}{'AVANCE':>8}{'RECHAZO':>10}{'SIN RESPUESTA':>14}  {'TASA':>7}"
    for titulo, grupo in (("POR FUENTE", emb["por_fuente"]),
                          ("POR FAMILIA", emb["por_familia"]),
                          ("POR COINCIDENCIA", emb["por_tramo"])):
        print(f"\n{titulo}\n{cab}")
        for k, g in sorted(grupo.items(), key=lambda kv: -kv[1]["candidaturas"]):
            print(_fila(k, g))

    if emb["saturadas"]:
        print("\nEMPRESAS CON MÁS PESO EN EL RADAR")
        for e in emb["saturadas"]:
            print(f"{e['empresa'][:24]:<25}{e['en_radar']:>4} ofertas"
                  f"{e['aplicadas']:>6} aplicadas{e['respuestas']:>4} respuestas")


if __name__ == "__main__":
    main()
