# -*- coding: utf-8 -*-
"""Datos sintéticos con la forma real de `data/`, para los tests.

El repo no tiene datos: eso es lo que le da su valor (es público) y también lo
que hacía imposible probarlo sin la base de datos del artifact delante. Esta
fixture reproduce el **esquema**, no los datos de nadie: cuatro ofertas
elegidas para tocar los caminos que se han roto alguna vez —una fresca, una de
hace tres semanas, una con «Senior» en el título, una que pide más años de los
que suma el CV—, un perfil mínimo pero completo y un estado que da de comer al
embudo.

    python tests/fixture.py <directorio>      # escribe <directorio>/*.json

Si un consumidor empieza a pedir una clave nueva del perfil, este fichero es
donde se añade: es lo que convierte un `KeyError` a 2 000 líneas de distancia
en un test que falla con nombre y apellidos.
"""
import datetime
import json
import os
import sys

HOY = datetime.date.today()


def _dia(dias_atras):
    return (HOY - datetime.timedelta(days=dias_atras)).isoformat()


OFERTAS = [
    dict(id="li-2001", empresa="Nubaris Analytics", puesto="AI Engineer",
         ubicacion="Remoto (España)", modalidad="Remoto", publicada=_dia(2),
         idioma="es", fuente="LinkedIn", sal_min=45000, sal_max=60000,
         sal_origen="publicado", sal_base="Banda publicada en el anuncio.",
         ambito="España", alerta="", anios_min=2,
         reqs=[["python", 3, "Python (imprescindible)"],
               ["llm", 3, "Experiencia con LLMs"],
               ["rag", 2, "RAG y búsqueda semántica"],
               ["databricks", 2, "Databricks"]],
         surfaced=["python", "llm"]),
    dict(id="ij-3002abcd1234", empresa="Meseta Data, S.L.", puesto="Senior Data Scientist",
         ubicacion="Remoto", modalidad="Remoto", publicada=_dia(20),
         idioma="es", fuente="InfoJobs", sal_min=38000, sal_max=48000,
         sal_origen="estimado", sal_base="Estimado con pipeline/bandas.json.",
         ambito="España", alerta="", anios_min=5,
         reqs=[["python", 3, "Python"], ["sql", 2, "SQL"],
               ["spark", 2, "Spark"], ["estadistica", 1, "Estadística"]],
         surfaced=["python"]),
    dict(id="li-2003", empresa="Orbita Cloud", puesto="Backend Developer",
         ubicacion="Pamplona, Navarra", modalidad="Híbrido (Navarra)", publicada=_dia(6),
         idioma="es", fuente="Manfred", sal_min=36000, sal_max=44000,
         sal_origen="publicado", sal_base="Banda publicada en el anuncio.",
         ambito="España", alerta="", anios_min=None,
         reqs=[["python", 3, "Python"], ["apis_rest", 2, "APIs REST"],
               ["docker", 2, "Docker"], ["kubernetes", 2, "Kubernetes"]],
         surfaced=["python", "apis_rest"]),
    dict(id="js-4004", empresa="Helio Vision", puesto="Computer Vision Engineer",
         ubicacion="Remote (EU)", modalidad="Remoto", publicada=_dia(70),
         idioma="en", fuente="JSearch", sal_min=50000, sal_max=65000,
         sal_origen="estimado", sal_base="Estimado con pipeline/bandas.json.",
         ambito="Internacional", alerta="Confirmar país de contratación.",
         anios_min=None,
         reqs=[["computer_vision", 3, "Computer vision"],
               ["pytorch_tf", 2, "PyTorch"], ["opencv", 2, "OpenCV"],
               ["CUDA", 1, "CUDA"]],
         surfaced=["computer_vision"]),
]

FAMILIAS = {"li-2001": "genai", "ij-3002abcd1234": "ds",
            "li-2003": "backend", "js-4004": "cv"}

TAILOR = {o["id"]: dict(familia=FAMILIAS[o["id"]],
                        titular="Senior AI Engineer" if o["id"] == "li-2001" else "",
                        resumen="Resumen adaptado de prueba, corto y sin cifras nuevas.",
                        skills_extra="")
          for o in OFERTAS}

SKILLS = {"base": {"Lenguajes": "Python, SQL, JavaScript",
                   "IA / Datos": "PyTorch, scikit-learn, pandas",
                   "Infraestructura": "Docker, Git, Linux"}}

PERFIL = dict(
    contacto=dict(nombre_es="Nombre Apellido", nombre_en="Nombre Apellido",
                  titulo_es="Ingeniero de software", titulo_en="Software engineer",
                  email="correo@ejemplo.test", tel="+34 600 000 000",
                  linkedin="linkedin.com/in/ejemplo",
                  ciudad_es="Ciudad", ciudad_en="City",
                  ubicacion="Ciudad, País"),
    # "apis_rest" y "computer_vision" llevan evidencia 1,0 (demostrado) más
    # abajo: tienen que aparecer también aquí en texto, o "evidencia-sin-
    # demostrar" los marca -- y ahora sí se ejecuta de verdad (bug del
    # 19-sep-2026 en pipeline/lint.py, ver su cabecera).
    bullets_es={
        "empleo1": ["Reduje un 38 % el tiempo de carga del catálogo, de 4,1 s a 2,5 s.",
                    "Migré 12 servicios a contenedores sin caída de servicio.",
                    "Diseñé las APIs REST que consume el frontend del catálogo."],
        "empleo2": ["Entrené un clasificador con 0,91 de F1 sobre 40 000 documentos."],
        "M1a": ["TFM: detección de anomalías con redes convolucionales, 0,94 de AUC."],
        "G1a": ["TFG: Computer Vision aplicado a segmentación de imagen médica con U-Net."],
        "v1": ["Proyecto propio: asistente RAG sobre 2 000 documentos internos."],
    },
    bullets_en={
        "empleo1": ["Cut catalogue load time by 38 %, from 4.1 s to 2.5 s.",
                    "Migrated 12 services to containers with no downtime.",
                    "Designed the REST APIs the catalogue frontend consumes."],
        "empleo2": ["Trained a classifier scoring 0.91 F1 over 40,000 documents."],
        "M1a": ["MSc thesis: anomaly detection with CNNs, 0.94 AUC."],
        "G1a": ["BSc thesis: computer vision for medical image segmentation with U-Net."],
        "v1": ["Side project: RAG assistant over 2,000 internal documents."],
    },
    skills_es=SKILLS, skills_en=SKILLS,
    # `orden[familia]` son DOS listas de claves de bullets_es/en (no una lista
    # plana de claves, y no una lista por puesto): la sección "Experiencia"
    # (aquí, los bullets de los dos empleos) y una sección secundaria (aquí,
    # el proyecto personal) -- ver `cvBloques()` en dashboard.py
    # (`oo=CV.orden[fam][0]`, `vv=CV.orden[fam][1]`, cada uno mapeado con
    # `.map(k=>B[k])`). Antes de corregirlo (19-sep-2026) esta fixture llevaba
    # una lista plana de un solo nivel (`["empleo1", "v1"]`): con esa forma,
    # `_todos_los_bullets()` de `pipeline/lint.py` explotaba cada clave
    # carácter a carácter y de los cinco bloques de bullets sólo sobrevivían
    # "M1a"/"G1a" (por `tfm_variant`/`tfg_variant`, que van aparte) --
    # "empleo1", "empleo2" y "v1" quedaban fuera del contexto del linter sin
    # que ningún test lo notara.
    orden={f: [["empleo1", "empleo2"], ["v1"]]
           for f in ("genai", "ml", "cv", "ds", "backend", "general")},
    orden_skills={f: dict(variante="base", orden=["Lenguajes", "IA / Datos", "Infraestructura"])
                  for f in ("genai", "ml", "cv", "ds", "backend", "general")},
    cv_labels={"es": {}, "en": {}},
    perfil_llm=dict(experiencia=[
        dict(puesto="Desarrollador de software", empresa="Empresa Uno",
             fechas="septiembre 2023 – marzo 2026", bullets=["empleo1"],
             logros=["Reduje un 38 % el tiempo de carga del catálogo."]),
        dict(puesto="Investigador (prácticas)", empresa="Empresa Dos",
             fechas="febrero–junio 2022", bullets=["empleo2"],
             logros=["Entrené un clasificador con 0,91 de F1."]),
    ]),
    tfm_variant={f: "M1a" for f in ("genai", "ml", "cv", "ds", "backend", "general")},
    tfg_variant={f: "G1a" for f in ("genai", "ml", "cv", "ds", "backend", "general")},
    evidencia_orig={"python": 1.0, "sql": 1.0, "apis_rest": 1.0, "docker": 1.0,
                    "computer_vision": 1.0, "opencv": 0.5, "pytorch_tf": 0.5,
                    "llm": 0.5, "rag": 0.5, "estadistica": 0.5, "kubernetes": 0.5,
                    "databricks": 0.0, "spark": 0.0, "CUDA": 0.0},
    techo={"llm": 1.0, "rag": 1.0, "opencv": 1.0},
)

ESTADO = {
    "li-2001": dict(estado="aplicada", fase="aplicada", fecha=_dia(5)),
    "ij-3002abcd1234": dict(estado="aplicada", fase="rechazada", fecha=_dia(12)),
    "li-2003": dict(estado="descartada", fecha=_dia(3), notas="No encaja la modalidad."),
}

CORREO = {"ij-3002abcd1234": dict(novedad="rechazo", fecha=_dia(9),
                                  asunto="Sobre tu candidatura")}

FILTRADAS = {"li-9001": dict(id="li-9001", empresa="Hire Feed", puesto="Python Developer",
                             fuente="LinkedIn", url="", motivo="empresa excluida",
                             detalle="Hire Feed", fecha=_dia(1))}


def escribe(destino):
    os.makedirs(destino, exist_ok=True)
    datos = {"ofertas.json": OFERTAS, "tailor.json": TAILOR, "perfil.json": PERFIL,
             "cerradas.json": {"lista": []}, "estado.json": ESTADO,
             "correo.json": CORREO, "filtradas.json": FILTRADAS}
    for nombre, dato in datos.items():
        with open(os.path.join(destino, nombre), "w", encoding="utf-8") as fh:
            json.dump(dato, fh, ensure_ascii=False, indent=1)
    return destino


if __name__ == "__main__":
    print(escribe(sys.argv[1] if len(sys.argv) > 1 else "data"))
