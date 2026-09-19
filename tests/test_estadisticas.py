# -*- coding: utf-8 -*-
"""Tests de la instrumentación de coste por ejecución (`pipeline/estadisticas.py`,
`pipeline/registrar_ejecucion.py`, `pipeline/resumen_historial.py`).

Añadida el 19-sep-2026 junto con la instrumentación misma: antes no había
ninguna manera de saber cuánto costaba una ejecución más allá de mirar
`fired_at`/`finished_at` del trigger.

    python tests/test_estadisticas.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))

FALLOS = []


def comprueba(condicion, que):
    print(("  ok   " if condicion else "  FALLA ") + que)
    if not condicion:
        FALLOS.append(que)
    return condicion


def main():
    print("[1] estadisticas.acumula() suma, no reemplaza")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["RADAR_DATA"] = tmp
        import estadisticas
        estadisticas.DATA = tmp
        estadisticas.RUTA = os.path.join(tmp, "estadisticas_ejecucion.json")

        estadisticas.acumula(candidatas_recibidas=3, filtradas_config=1)
        r = estadisticas.acumula(candidatas_recibidas=2, filtradas_config=0)
        comprueba(r["candidatas_recibidas"] == 5, "candidatas_recibidas se suma entre llamadas (3+2=5)")
        comprueba(r["filtradas_config"] == 1, "filtradas_config no cambia si se suma 0")
        comprueba(estadisticas.leer() == r, "leer() devuelve lo mismo que la última acumulación")

        print("\n[2] registrar_ejecucion.construye()")
        import registrar_ejecucion as reg
        doc = reg.construye(
            agente=dict(inicio="2026-09-19T08:00:00+00:00", fin="2026-09-19T08:10:00+00:00",
                        fuentes_cubiertas=["LinkedIn"], tokens_estimados=100000),
            contadores=r, fecha="2026-09-19",
        )
        comprueba(doc["duracion_min"] == 10.0, "duración calculada a partir de inicio/fin (10 min)")
        comprueba(doc["contadores"] == r, "los contadores acumulados pasan tal cual al documento")
        comprueba(doc["fuentes_omitidas"] == [], "fuentes_omitidas por defecto es lista vacía, no None")

        doc_sin_fechas = reg.construye(agente={}, contadores=r, fecha="2026-09-19")
        comprueba(doc_sin_fechas["duracion_min"] is None,
                  "sin inicio/fin del agente, duración es None (no se inventa un 0)")

    print("\n[3] resumen_historial.resume() agrega varios días")
    import resumen_historial as rh
    docs = [
        dict(fecha="2026-09-19", duracion_min=10.0,
             fuentes_cubiertas=["LinkedIn", "InfoJobs"],
             fuentes_omitidas=[{"fuente": "Indeed", "motivo": "captcha"}],
             tokens_estimados=100000,
             contadores=dict(ofertas_nuevas=3, podadas=1, duplicadas=1, candidatas_a_dedupe=4)),
        dict(fecha="2026-09-20", duracion_min=8.0,
             fuentes_cubiertas=["LinkedIn"],
             fuentes_omitidas=[{"fuente": "Indeed", "motivo": "captcha"}, {"fuente": "InfoJobs", "motivo": "timeout"}],
             tokens_estimados=140000,
             contadores=dict(ofertas_nuevas=1, podadas=0, duplicadas=1, candidatas_a_dedupe=2)),
    ]
    r = rh.resume(docs)
    comprueba(r["n_ejecuciones"] == 2, "cuenta las dos ejecuciones")
    comprueba(r["duracion_media_min"] == 9.0, "duración media (10+8)/2 = 9.0")
    comprueba(r["ofertas_nuevas_media"] == 2.0, "ofertas nuevas media (3+1)/2 = 2.0")
    comprueba(r["podadas_total"] == 1, "podadas se suman, no se promedian")
    comprueba(r["tasa_duplicados"] == round(2 / 6, 2),
               "tasa de duplicados = duplicadas totales / candidatas_a_dedupe totales (redondeada a 2 decimales)")
    comprueba(r["cobertura_por_fuente"]["LinkedIn"] == "2/2", "LinkedIn cubierto las dos ejecuciones")
    comprueba(r["cobertura_por_fuente"]["InfoJobs"] == "1/2", "InfoJobs cubierto sólo una de las dos")
    comprueba("Manfred" not in r["cobertura_por_fuente"], "una fuente que nunca se cubrió no aparece en cobertura")
    comprueba(r["motivos_omision"]["Indeed"] == ["captcha", "captcha"],
               "los motivos de omisión de Indeed se acumulan en las dos ejecuciones")

    print("\n[4] resumen_historial._carga() acepta lista, dict y directorio de volcado")
    with tempfile.TemporaryDirectory() as tmp:
        p_lista = os.path.join(tmp, "lista.json")
        with open(p_lista, "w", encoding="utf-8") as fh:
            json.dump(docs, fh)
        comprueba(len(rh._carga(p_lista)) == 2, "fichero con una lista de documentos")

        p_dict = os.path.join(tmp, "dict.json")
        with open(p_dict, "w", encoding="utf-8") as fh:
            json.dump({d["fecha"]: d for d in docs}, fh)
        comprueba(len(rh._carga(p_dict)) == 2, "fichero con un dict {fecha: documento}")

        dir_vol = os.path.join(tmp, "vol", "historial")
        os.makedirs(dir_vol)
        for d in docs:
            with open(os.path.join(dir_vol, f"{d['fecha']}.json"), "w", encoding="utf-8") as fh:
                json.dump(d, fh)
        comprueba(len(rh._carga(os.path.join(tmp, "vol"))) == 2,
                   "directorio de volcado por colecciones (historial/<fecha>.json)")

    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s):")
        for f in FALLOS:
            print("  ·", f)
        return 1
    print("todo en verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
