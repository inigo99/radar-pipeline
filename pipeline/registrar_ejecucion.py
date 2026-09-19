# -*- coding: utf-8 -*-
"""Cierra la instrumentación de la ejecución de hoy y deja `out/historial.json`,
listo para subir a la colección `historial` con `write_db` (`set`,
`doc_id:<fecha>`).

Junta dos fuentes:

  1. **Lo que ya se contó solo.** `poda_antiguedad.py`, `filtrar.py` y
     `dedupe.py` van llamando a `estadisticas.acumula()` con sus propios
     contadores a medida que corren (ver `pipeline/estadisticas.py`). Este
     script lee `data/estadisticas_ejecucion.json`, que es la suma de todo eso.
  2. **Lo que sólo sabe el agente.** Nada de lo anterior sabe cuánto ha durado
     la ejecución, qué fuentes se han cubierto hoy o se han omitido (y por
     qué), cuántas fichas completas se han leído en el navegador, ni el gasto
     de tokens: eso vive en la conversación de la tarea, no en ningún fichero
     del repo. Se pasa aquí como un JSON (`--agente ruta.json` o por stdin).

Por qué no tokens exactos: la tarea no tiene acceso a su propio recuento de
tokens de la conversación en curso. El campo `tokens_estimados` es una
estimación que el agente rellena a ojo (o se omite) -- mejor una cifra
aproximada y marcada como tal que ninguna cifra, pero sin pretender una
precisión que no existe.

Uso:

    python pipeline/registrar_ejecucion.py --agente agente.json
    python pipeline/registrar_ejecucion.py --agente agente.json --out out/historial.json

`agente.json` esperado (todos los campos opcionales; lo que falte se guarda
como `null` o lista vacía, nunca inventado):

    {
      "inicio": "2026-09-19T08:00:12+00:00",
      "fin": "2026-09-19T08:11:47+00:00",
      "fuentes_cubiertas": ["LinkedIn", "InfoJobs", "Tecnoempleo", "Manfred"],
      "fuentes_omitidas": [{"fuente": "Indeed", "motivo": "captcha persistente"}],
      "fichas_completas_leidas": 14,
      "tokens_estimados": 180000,
      "correo_novedades": 2,
      "errores": []
    }
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estadisticas  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _duracion_min(inicio, fin):
    if not inicio or not fin:
        return None
    try:
        i = datetime.datetime.fromisoformat(inicio)
        f = datetime.datetime.fromisoformat(fin)
        return round((f - i).total_seconds() / 60, 1)
    except ValueError:
        return None


def construye(agente, contadores, fecha=None):
    """El documento completo que se sube a `historial/<fecha>`."""
    fecha = fecha or datetime.date.today().isoformat()
    inicio = agente.get("inicio")
    fin = agente.get("fin")
    return {
        "fecha": fecha,
        "inicio": inicio,
        "fin": fin,
        "duracion_min": _duracion_min(inicio, fin),
        "fuentes_cubiertas": agente.get("fuentes_cubiertas") or [],
        "fuentes_omitidas": agente.get("fuentes_omitidas") or [],
        "fichas_completas_leidas": agente.get("fichas_completas_leidas"),
        "tokens_estimados": agente.get("tokens_estimados"),
        "correo_novedades": agente.get("correo_novedades"),
        "errores": agente.get("errores") or [],
        # Lo que se contó solo durante la ejecución (ver estadisticas.py):
        # candidatas_recibidas, filtradas_config, candidatas_a_dedupe,
        # duplicadas, ofertas_nuevas, ofertas_antes_de_podar, podadas.
        "contadores": contadores,
    }


def main(argv):
    agente = {}
    if "--agente" in argv:
        with open(argv[argv.index("--agente") + 1], encoding="utf-8") as fh:
            agente = json.load(fh)
    elif not sys.stdin.isatty():
        crudo = sys.stdin.read().strip()
        if crudo:
            agente = json.loads(crudo)

    contadores = estadisticas.leer()
    documento = construye(agente, contadores)

    destino = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(RAIZ, "out", "historial.json")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(documento, fh, ensure_ascii=False, indent=1)

    print(f"historial de {documento['fecha']} -> {destino}")
    print(f"  duración: {documento['duracion_min']} min" if documento["duracion_min"] is not None
          else "  duración: (sin inicio/fin del agente)")
    print(f"  fuentes cubiertas: {', '.join(documento['fuentes_cubiertas']) or '(ninguna)'}")
    if documento["fuentes_omitidas"]:
        print("  fuentes omitidas:")
        for f in documento["fuentes_omitidas"]:
            print(f"    · {f.get('fuente', '?')}: {f.get('motivo', '(sin motivo)')}")
    print(f"  contadores: {contadores}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
