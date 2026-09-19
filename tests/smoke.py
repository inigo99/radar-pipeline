# -*- coding: utf-8 -*-
"""El test que faltaba: ejecuta el pipeline entero sobre la fixture sintética.

    python tests/smoke.py            # desde la raíz del repo

No comprueba que los números sean bonitos: comprueba que **el pipeline corre de
principio a fin y produce lo que el dashboard necesita**. Eso es exactamente lo
que se ha roto en la práctica —`CV.orden_skills[fam] is not iterable`, la
pestaña «Embudo» vacía porque faltaba un paso, el `dashboard.py` del repo por
detrás de lo publicado— y todo eso se cazaba aquí en dos segundos, sin base de
datos, sin navegador y sin red.

Qué hace, en orden:

  1. escribe la fixture en un directorio temporal;
  2. `puntuar.py` → `embudo.py` → `dashboard.py` → `exportar_snapshot.py`;
  3. round-trip: `preparar_datos.py` sobre el snapshot recién generado tiene
     que devolver las mismas ofertas (el snapshot es caché, y una caché que no
     vuelve a cargar igual es peor que no tenerla);
  4. `poda_antiguedad.py` retira la oferta de hace 70 días y la deja anotada en
     `filtradas` con motivo `podada`;
  5. `filtrar.py` aparta lo que dicen `excluir_empresas`/`salario_min`;
  6. `node --check` sobre el `<script>` de la página y, si hay jsdom,
     `tests/paridad.mjs` (la aritmética duplicada en JS tiene que dar lo mismo);
  7. las funciones de `browser/*.js` están también en `bundle.min.js` (avisa si
     alguien tocó una fuente y se olvidó de regenerar el bundle).

Sale con código 1 a la primera que falle, y dice cuál.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE = os.path.join(RAIZ, "pipeline")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FALLOS = []


def comprueba(condicion, que):
    print(("  ok   " if condicion else "  FALLA ") + que)
    if not condicion:
        FALLOS.append(que)
    return condicion


def corre(script, *args, cwd=None, espera_exito=True):
    r = subprocess.run([sys.executable, os.path.join(PIPELINE, script), *args],
                       cwd=cwd, capture_output=True, text=True)
    if espera_exito and r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:], file=sys.stderr)
        FALLOS.append(f"{script} terminó con código {r.returncode}")
    return r


def main():
    import fixture

    tmp = tempfile.mkdtemp(prefix="radar-smoke-")
    data = os.path.join(tmp, "data")
    os.makedirs(os.path.join(tmp, "out"), exist_ok=True)
    fixture.escribe(data)
    print(f"fixture en {data}")

    print("\n[1] pipeline")
    corre("puntuar.py", cwd=tmp)
    corre("embudo.py", cwd=tmp)
    corre("dashboard.py", cwd=tmp)
    corre("exportar_snapshot.py", cwd=tmp)

    res_p = os.path.join(data, "resultado.json")
    html_p = os.path.join(tmp, "out", "dashboard.html")
    comprueba(os.path.exists(res_p), "puntuar.py escribe data/resultado.json")
    comprueba(os.path.exists(os.path.join(data, "embudo.json")), "embudo.py escribe data/embudo.json")
    comprueba(os.path.exists(html_p), "dashboard.py escribe out/dashboard.html")
    comprueba(os.path.exists(os.path.join(tmp, "out", "snapshot.json")),
              "exportar_snapshot.py escribe out/snapshot.json")

    res = json.load(open(res_p, encoding="utf-8"))
    comprueba(len(res) == len(fixture.OFERTAS), "el resultado tiene todas las ofertas")
    comprueba(all(isinstance(r.get("foco"), (int, float)) for r in res),
              "todas las ofertas llevan foco")
    comprueba(all(r.get("score_adap", 0) >= r.get("score_orig", 0) for r in res),
              "el CV adaptado nunca puntúa por debajo del original")
    # El candado: una clave con evidencia 0 no puede subir aunque esté en surfaced.
    comprueba(all("databricks" not in (r.get("fuertes") or []) for r in res),
              "el candado anti-invención no saca un hueco como fuerte")

    if not os.path.exists(html_p):
        print("\nsin página generada: me salto las comprobaciones que dependen de ella")
        print(f"{len(FALLOS)} fallo(s): " + "; ".join(FALLOS))
        return 1
    html = open(html_p, encoding="utf-8").read()
    comprueba("__DATA__" not in html and "__CV__" not in html,
              "no queda ningún placeholder __X__ sin sustituir en la página")
    comprueba("EMBUDO = {}" not in html.replace("const ", ""),
              "la página lleva el embudo cargado (no sale vacío)")

    print("\n[2] round-trip del snapshot")
    data2 = os.path.join(tmp, "data2")
    corre("preparar_datos.py", os.path.join(tmp, "out", "snapshot.json"), data2, cwd=tmp)
    if os.path.exists(os.path.join(data2, "ofertas.json")):
        a = json.load(open(os.path.join(data, "ofertas.json"), encoding="utf-8"))
        b = json.load(open(os.path.join(data2, "ofertas.json"), encoding="utf-8"))
        comprueba(sorted(o["id"] for o in a) == sorted(o["id"] for o in b),
                  "el snapshot vuelve a cargar con las mismas ofertas")

    print("\n[3] poda de antigüedad")
    tmp_poda = os.path.join(tmp, "poda")
    shutil.copytree(data, os.path.join(tmp_poda, "data"))
    corre("poda_antiguedad.py", cwd=tmp_poda)
    ofertas_poda = json.load(open(os.path.join(tmp_poda, "data", "ofertas.json"), encoding="utf-8"))
    filtradas_poda = json.load(open(os.path.join(tmp_poda, "data", "filtradas.json"), encoding="utf-8"))
    comprueba("js-4004" not in {o["id"] for o in ofertas_poda},
              "la poda retira la oferta de hace 70 días sin seguimiento")
    comprueba(filtradas_poda.get("js-4004", {}).get("motivo") == "podada",
              "lo podado queda anotado en filtradas con motivo «podada»")
    comprueba("li-2003" in {o["id"] for o in ofertas_poda},
              "la poda no toca una oferta con seguimiento")
    comprueba(not os.path.exists(os.path.join(tmp_poda, "data", "podadas.json")),
              "ya no se escribe el podadas.json que no leía nadie")

    print("\n[4] filtrar.py")
    cand = os.path.join(tmp, "candidatas.json")
    filtros = os.path.join(tmp, "filtros.json")
    json.dump([dict(id="x1", empresa="Hire Feed", puesto="Python Developer", salario=""),
               dict(id="x2", empresa="Buena S.L.", puesto="AI Engineer", salario="45.000 - 55.000 € Bruto/año"),
               dict(id="x3", empresa="Baja S.L.", puesto="AI Engineer", salario="24k-28k"),
               dict(id="x4", empresa="Otra", puesto="Prácticas de verano", salario="")],
              open(cand, "w", encoding="utf-8"))
    json.dump(dict(excluir_empresas=["Hire Feed"], excluir_keywords=["prácticas"],
                   salario_min=30000, exigir_salario_publicado=False),
              open(filtros, "w", encoding="utf-8"), ensure_ascii=False)
    corre("filtrar.py", cand, os.path.join(tmp, "ok.json"), "--filtros", filtros, cwd=tmp)
    ok = json.load(open(os.path.join(tmp, "ok.json"), encoding="utf-8"))
    comprueba({o["id"] for o in ok} == {"x2"},
              "filtrar.py aparta empresa vetada, palabra vetada y salario bajo, y sólo eso")

    # La rama `exigir_salario_publicado=True` no se probaba: x4 no publica salario
    # y antes se dejaba pasar por no chocar con `excluir_keywords`/`excluir_empresas`.
    filtros_exig = os.path.join(tmp, "filtros_exigir.json")
    json.dump(dict(excluir_empresas=[], excluir_keywords=[],
                   salario_min=None, exigir_salario_publicado=True),
              open(filtros_exig, "w", encoding="utf-8"), ensure_ascii=False)
    corre("filtrar.py", cand, os.path.join(tmp, "ok_exig.json"), "--filtros", filtros_exig, cwd=tmp)
    ok_exig = json.load(open(os.path.join(tmp, "ok_exig.json"), encoding="utf-8"))
    comprueba({o["id"] for o in ok_exig} == {"x2", "x3"},
              "exigir_salario_publicado=True aparta las que no publican cifra, y sólo esas")

    print("\n[5] el JavaScript de la página")
    node = shutil.which("node")
    if not node:
        print("  (sin node: me salto node --check y la paridad)")
    else:
        # Desde el 19-sep-2026 `pipeline/dashboard.js` es un fichero de verdad
        # (ver README y el comentario en dashboard.py), así que se puede
        # comprobar solo, sin generar la página primero.
        r = subprocess.run([node, "--check", os.path.join(PIPELINE, "dashboard.js")],
                           capture_output=True, text=True)
        if not comprueba(r.returncode == 0, "node --check sobre pipeline/dashboard.js (sin plantilla)"):
            print(r.stderr[-1500:])

        js = "\n".join(re.findall(r"<script>(.*?)</script>", html, re.S))
        js_p = os.path.join(tmp, "dashboard.js")
        open(js_p, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, "--check", js_p], capture_output=True, text=True)
        if not comprueba(r.returncode == 0, "node --check sobre el <script> de la página"):
            print(r.stderr[-1500:])

        # Paridad Python <-> JS: necesita jsdom. Si no está, se avisa y se sigue;
        # en CI sí está, que es donde tiene que ser obligatorio.
        tiene_jsdom = subprocess.run(
            [node, "-e", "import('jsdom').then(()=>process.exit(0),()=>process.exit(1))"],
            capture_output=True, text=True, cwd=RAIZ).returncode == 0
        if not tiene_jsdom:
            print("  (sin jsdom: `npm install jsdom` para correr tests/paridad.mjs)")
        else:
            r = subprocess.run([node, os.path.join(RAIZ, "tests", "paridad.mjs"), html_p, data],
                               capture_output=True, text=True, cwd=RAIZ)
            print(r.stdout.rstrip())
            if not comprueba(r.returncode == 0,
                             "la aritmética de la página coincide con la del pipeline"):
                print(r.stderr[-1500:])

    print("\n[6] bundle.min.js al día")
    bundle = open(os.path.join(RAIZ, "browser", "bundle.min.js"), encoding="utf-8").read()

    # Chequeo fuerte (19-sep-2026): reconstruir el bundle de verdad con
    # tools/build_bundle.js y comparar byte a byte contra el commiteado. El
    # chequeo antiguo (nombre de función como subcadena) no detectaba un
    # bundle desactualizado si el CUERPO de una función cambiaba sin cambiar
    # su nombre; esto sí, porque es literalmente la misma reconstrucción.
    reconstruido = False
    if node:
        tiene_terser = subprocess.run(
            [node, "-e", "import('terser').then(()=>process.exit(0),()=>process.exit(1))"],
            capture_output=True, text=True, cwd=RAIZ).returncode == 0
        if tiene_terser:
            salida = os.path.join(tmp, "bundle_reconstruido.js")
            r = subprocess.run([node, os.path.join(RAIZ, "tools", "build_bundle.js"), salida],
                               capture_output=True, text=True, cwd=RAIZ)
            if comprueba(r.returncode == 0, "tools/build_bundle.js reconstruye el bundle sin errores"):
                nuevo = open(salida, encoding="utf-8").read()
                if not comprueba(nuevo == bundle,
                                 "browser/bundle.min.js coincide byte a byte con "
                                 "`node tools/build_bundle.js` sobre las fuentes actuales"):
                    print("    -> alguien tocó common.js/linkedin.js/infojobs.js sin regenerar el "
                          "bundle (o tocó el bundle a mano). Corre `node tools/build_bundle.js`.")
                reconstruido = True
            else:
                print(r.stderr[-1000:])
        else:
            print("  (sin terser: `npm install` para el chequeo fuerte del bundle)")

    if not reconstruido:
        # Respaldo sin red/terser: al menos que no falte ninguna función por nombre.
        faltan = []
        for f in ("common.js", "linkedin.js", "infojobs.js"):
            src = open(os.path.join(RAIZ, "browser", f), encoding="utf-8").read()
            for nombre in set(re.findall(r"^\s*(?:R|li|ij)\.([A-Za-z_][A-Za-z0-9_]*)\s*=", src, re.M)):
                if nombre not in bundle:
                    faltan.append(f"{f}:{nombre}")
        comprueba(not faltan,
                  "(chequeo débil, sin terser) toda función de common/linkedin/infojobs "
                  "está en el bundle"
                  + (f" (faltan: {', '.join(sorted(faltan)[:6])})" if faltan else ""))

    print()
    if FALLOS:
        print(f"{len(FALLOS)} fallo(s):")
        for f in FALLOS:
            print("  ·", f)
        return 1
    print("todo en verde")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
