# -*- coding: utf-8 -*-
"""Tests de `pipeline/dedupe.py`.

No tenía ninguno, a pesar de ser la pieza con más historial de bugs reales
documentado en su propia cabecera (hash de InfoJobs truncado a longitudes
distintas, "Banco Santander" vs "Grupo Santander") y de ser la que decide si
una oferta que ya se vio (o que se decidió descartar) vuelve a entrar.

    python tests/test_dedupe.py            # desde la raíz del repo

Sin base de datos, sin red: todo en memoria salvo la sección [7], que escribe
un `data/` temporal para probar `conocidas_de_data()` contra ficheros reales.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
import dedupe  # noqa: E402

FALLOS = []


def comprueba(condicion, que):
    print(("  ok   " if condicion else "  FALLA ") + que)
    if not condicion:
        FALLOS.append(que)
    return condicion


def main():
    print("[1] normalización de empresa")
    comprueba(dedupe.normaliza_empresa("Banco Santander") == dedupe.normaliza_empresa("Grupo Santander"),
               "Banco Santander == Grupo Santander (bug del 16-sep-2026)")
    comprueba(dedupe.normaliza_empresa("Talan España, S.L.U.") != dedupe.normaliza_empresa("Alan Consulting"),
               "Talan no se confunde con Alan por la forma jurídica")

    print("\n[2] guardas contra falsos positivos por subcadena")
    huella_alan = dedupe.huella(dict(empresa="Alan", puesto="Data Engineer"))
    huella_talan = dedupe.huella(dict(empresa="Talan España, S.L.U.", puesto="Data Engineer"))
    comprueba(huella_alan != huella_talan, "«Alan» no cae dentro de «Talan» por huella")
    huella_ust = dedupe.huella(dict(empresa="UST", puesto="Backend Engineer"))
    huella_braintrust = dedupe.huella(dict(empresa="Braintrust", puesto="Backend Engineer"))
    comprueba(huella_ust != huella_braintrust, "«UST» no cae dentro de «Braintrust» por huella")

    print("\n[3] hash de InfoJobs truncado a longitudes distintas")
    conocidas = [dict(id="ij-abcdef1234567890", empresa="Sopra Steria", puesto="Java Developer")]
    supervivientes, duplicadas = dedupe.dedupe(
        [dict(id="ij-abcdef12", empresa="Sopra Steria", puesto="Java Developer")], conocidas)
    comprueba(not supervivientes and duplicadas,
              "el hash de InfoJobs truncado a 8 caracteres se reconoce contra el largo")

    print("\n[4] URL antes que huella, huella antes que solape")
    conocidas = [dict(id="li-1", empresa="Acme", puesto="Data Scientist", url="https://x/1")]
    _, dup_url = dedupe.dedupe([dict(id="li-2", empresa="Acme Corp", puesto="Otra cosa",
                                      url="https://x/1")], conocidas)
    comprueba(dup_url and dup_url[0]["motivo"] == "misma URL",
              "misma URL detecta duplicado aunque el puesto no case")

    print("\n[5] solape de tokens, sólo dentro de la misma empresa, con umbral alto")
    # Distintos de la huella (que exigiría el mismo conjunto de tokens tras
    # quitar ruido): aquí falta una palabra real ("python"), no una de ruido,
    # así que huella no casa pero el Jaccard sí llega a 0.75.
    conocidas = [dict(id="li-1", empresa="Acme", puesto="Machine Learning NLP Python Engineer")]
    _, dup_solape = dedupe.dedupe([dict(id="li-2", empresa="Acme", puesto="Machine Learning NLP Engineer")],
                                   conocidas)
    comprueba(dup_solape and "solape" in dup_solape[0]["motivo"],
              "mismo puesto en la misma empresa con una palabra real de menos se detecta por solape")
    _, sin_dup = dedupe.dedupe([dict(id="li-3", empresa="Otra Empresa", puesto="Data Engineer")], conocidas)
    comprueba(not sin_dup, "el solape nunca cruza empresas distintas")

    print("\n[6] nunca por subcadena cruda")
    conocidas = [dict(id="li-1", empresa="Talan España", puesto="Consultor SAP")]
    supervivientes, dup = dedupe.dedupe([dict(id="li-2", empresa="Alan", puesto="Consultor SAP")], conocidas)
    comprueba(supervivientes and not dup, "«Alan» sobrevive contra «Talan España»: no hay match por subcadena")

    print("\n[7] conocidas_de_data(): la poda por antigüedad veta reingresos (bug del 19-sep-2026)")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["RADAR_DATA"] = tmp
        dedupe.DATA = tmp
        with open(os.path.join(tmp, "ofertas.json"), "w", encoding="utf-8") as fh:
            json.dump([], fh)
        with open(os.path.join(tmp, "estado.json"), "w", encoding="utf-8") as fh:
            json.dump({}, fh)
        with open(os.path.join(tmp, "filtradas.json"), "w", encoding="utf-8") as fh:
            json.dump({
                "js-vieja": dict(id="js-vieja", empresa="Acme", puesto="AI Engineer",
                                  motivo="podada", detalle="publicada hace 60 días"),
                "js-vetada": dict(id="js-vetada", empresa="Hire Feed", puesto="Python Developer",
                                   motivo="empresa excluida", detalle="Hire Feed"),
            }, fh)

        conocidas, vetados = dedupe.conocidas_de_data()
        comprueba("js-vieja" in vetados, "lo podado por antigüedad queda vetado por id")
        comprueba("js-vetada" not in vetados,
                  "un motivo distinto de 'podada' (config) NO se veta para siempre")

        # Repost: misma vacante, id nuevo -- lo que antes del fix volvía a entrar como "nueva".
        repost = dict(id="js-nueva-2", empresa="Acme", puesto="AI Engineer")
        supervivientes, dup = dedupe.dedupe([repost], conocidas, vetados)
        comprueba(not supervivientes and dup,
                  "un repost de una vacante ya podada (id nuevo, misma empresa+puesto) "
                  "se detecta como duplicado y no vuelve a entrar")

        # Una vacante nueva de verdad de la misma empresa filtrada por config sí puede entrar:
        # el veto es sólo por antigüedad, nunca por los motivos que dependen de config/filtros.
        distinta = dict(id="js-otra", empresa="Hire Feed", puesto="Data Analyst")
        supervivientes2, dup2 = dedupe.dedupe([distinta], conocidas, vetados)
        comprueba(supervivientes2 and not dup2,
                  "una vacante distinta de una empresa que sólo estaba en 'filtradas' por config "
                  "sigue pudiendo entrar (la volverá a filtrar filtrar.py si sigue vetada)")

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
