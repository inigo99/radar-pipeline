# -*- coding: utf-8 -*-
"""Tests de `pipeline/lint.py`.

`dashboard.py` ya lo ejecuta de camino (y `tests/smoke.py` lo comprueba
indirectamente al generar la página), pero eso sólo prueba que no explota
-- no que sus reglas detecten lo que dicen detectar. Aquí se prueban en
directo las dos reglas propias del sistema (`evidencia-sin-demostrar` y
`techo-imposible`), que son las que sostienen el candado anti-invención.

    python tests/test_lint.py            # desde la raíz del repo
"""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
import lint  # noqa: E402
import fixture  # noqa: E402

FALLOS = []


def comprueba(condicion, que):
    print(("  ok   " if condicion else "  FALLA ") + que)
    if not condicion:
        FALLOS.append(que)
    return condicion


def _codigos(hallazgos, codigo=None, nivel=None):
    return [h for h in hallazgos
            if (codigo is None or h["codigo"] == codigo)
            and (nivel is None or h["nivel"] == nivel)]


def main():
    print("[0] ninguna regla se rompe (bug del 19-sep-2026: 8 de 18 llevaban "
          "rompiéndose en silencio, capturadas como 'regla-rota')")
    base = lint.analiza(fixture.PERFIL)
    rotas = _codigos(base, "regla-rota")
    comprueba(not rotas,
              "cero hallazgos 'regla-rota' sobre la fixture"
              + (f" (rota: {[h['mensaje'] for h in rotas]})" if rotas else ""))

    print("\n[1] el perfil de la fixture (bien formado) no dispara las reglas propias")
    comprueba(not _codigos(base, "techo-imposible"),
              "un perfil sano no saca techo-imposible")
    comprueba(not _codigos(base, "evidencia-sin-demostrar"),
              "un perfil sano no saca evidencia-sin-demostrar")

    print("\n[2] techo-imposible: techo > 0 con evidencia 0 es error")
    p = copy.deepcopy(fixture.PERFIL)
    p["evidencia_orig"]["databricks"] = 0.0     # ya lo es en la fixture, explícito por claridad
    p["techo"]["databricks"] = 0.5
    hallazgos = _codigos(lint.analiza(p), "techo-imposible")
    comprueba(any(h["nivel"] == "error" for h in hallazgos),
              "techo > 0 con evidencia 0 se marca como error, no como aviso")

    print("\n[3] techo-imposible: techo por debajo de la evidencia es aviso, no error")
    p = copy.deepcopy(fixture.PERFIL)
    p["evidencia_orig"]["python"] = 1.0
    p["techo"]["python"] = 0.5           # por debajo de su propia evidencia
    hallazgos = _codigos(lint.analiza(p), "techo-imposible")
    comprueba(any(h["nivel"] == "aviso" for h in hallazgos) and
              not any(h["nivel"] == "error" for h in hallazgos),
              "techo por debajo de la evidencia demostrada es aviso, no error")

    print("\n[4] evidencia-sin-demostrar: un 1.0 que no aparece en ningún logro")
    p = copy.deepcopy(fixture.PERFIL)
    p["evidencia_orig"]["kafka"] = 1.0    # no aparece en bullets_es/en ni en skills_es/en
    hallazgos = _codigos(lint.analiza(p), "evidencia-sin-demostrar")
    comprueba(any("kafka" in h["mensaje"] for h in hallazgos),
              "un término con evidencia 1,0 que no aparece en el CV se marca")

    print("\n[5] evidencia-sin-demostrar: sí aparece -> no se marca")
    p = copy.deepcopy(fixture.PERFIL)
    p["evidencia_orig"]["docker"] = 1.0   # "Docker" sí está en skills_es de la fixture
    hallazgos = _codigos(lint.analiza(p), "evidencia-sin-demostrar")
    comprueba(not any("docker" in h["mensaje"].lower() for h in hallazgos),
              "un término que sí aparece en el CV no se marca en falso")

    print("\n[6] las ocho reglas que trataban un grupo de bullets como una sola línea")
    p = copy.deepcopy(fixture.PERFIL)
    p["bullets_es"]["empleo1"] = [
        "Responsable de mantener el catálogo de productos.",     # lenguaje de funciones
        "Yo colaboré en la migración a contenedores.",           # primera persona
        "Amplia experiencia en trabajo en equipo y proactividad.",  # frase vacía
        "x" * (lint.MAX_BULLET + 1),                              # bullet largo
    ]
    hallazgos = lint.analiza(p)
    comprueba(_codigos(hallazgos, "lenguaje-de-funciones"),
              "lenguaje-de-funciones detecta 'responsable de' dentro de un grupo de bullets")
    comprueba(_codigos(hallazgos, "primera-persona"),
              "primera-persona detecta una línea en primera persona dentro del grupo")
    comprueba(_codigos(hallazgos, "frase-vacia"),
              "frase-vacia detecta relleno dentro del grupo")
    comprueba(_codigos(hallazgos, "bullet-largo"),
              "bullet-largo detecta una línea larga dentro del grupo")
    comprueba(not _codigos(hallazgos, "regla-rota"),
              "nada de esto rompe ninguna regla (antes del fix, las cuatro fallaban)")

    print("\n[7] tiempos-mezclados y demasiados-bullets miran líneas, no grupos")
    p = copy.deepcopy(fixture.PERFIL)
    p["bullets_es"]["empleo1"] = ["Reduciendo el tiempo de carga un 38 %.",  # gerundio
                                  "Migré 12 servicios sin caída de servicio."]  # pasado
    hallazgos = _codigos(lint.analiza(p), "tiempos-mezclados")
    comprueba(hallazgos, "gerundio y pasado en el mismo puesto se detectan como mezclados")

    p = copy.deepcopy(fixture.PERFIL)
    p["bullets_es"]["empleo1"] = [f"Logro número {i} con una cifra {i}." for i in range(8)]
    hallazgos = _codigos(lint.analiza(p), "demasiados-bullets")
    comprueba(hallazgos, "8 líneas de logro en un mismo puesto se cuentan como líneas, no como 1 clave")

    print("\n[8] _bullets_por_puesto nombra por pertenencia real, no por posición en orden[]")
    ctx = lint._contexto(fixture.PERFIL)
    nombres = {nombre for nombre, _, _ in ctx["puestos"]}
    comprueba("Empresa Uno" in nombres and "Empresa Dos" in nombres,
              "empleo1 y empleo2 se etiquetan cada uno con su propio puesto real "
              "(antes, la posición 1 de orden[] se etiquetaba siempre como el puesto "
              "2, así que 'v1' -- un proyecto personal -- se habría colado como "
              "'Empresa Dos' y empleo2 habría quedado sin agrupar)")
    comprueba(any("v1" in n for n in nombres if "Empresa" not in n),
              "el bloque que no pertenece a ningún puesto (proyecto personal 'v1') "
              "se etiqueta con su propia clave, no con el nombre de un puesto que no es")

    print("\n[9] una regla que lanza excepción no tumba el informe entero")
    def _rota(perfil, ctx):
        raise ValueError("regla de prueba, rota a propósito")
        yield  # pragma: no cover  (hace de esta función un generador)
    original = lint.REGLAS
    lint.REGLAS = list(original) + [_rota]
    try:
        hallazgos = lint.analiza(fixture.PERFIL)
        comprueba(any(h["codigo"] == "regla-rota" for h in hallazgos),
                  "una regla que lanza excepción se registra como 'regla-rota', "
                  "no tumba el análisis")
    finally:
        lint.REGLAS = original

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
