# -*- coding: utf-8 -*-
"""Diccionario término -> regex, portado de `browser/vocabulario.js`, para
sacar los `reqs` de una oferta aceptada sin volcar la descripción entera al
contexto. Las claves son las de `pipeline/vocabulario.md`: si aquí aparece
una que allí no está, la puntuación la tratará como evidencia 0 y hundirá la
oferta sin motivo.

Se aplica SIEMPRE sobre el texto de la descripción normalizado
(`comun.norm`), nunca sobre el HTML de la página — ver el aviso en
`infojobs.py` sobre por qué (el bug de `\\.net` casando con «infojobs.net»)."""
import re

DICC = {
    "python": r"\bpython\b", "java": r"\bjava\b(?!script)", "javascript": r"javascript",
    "typescript": r"typescript", "csharp": r"c#|\.net\b|dotnet", "golang": r"\bgolang\b",
    "scala": r"\bscala\b", "c_cpp": r"\bc\+\+\b", "php": r"\bphp\b|laravel|symfony",
    "react": r"\breact\b", "angular": r"angular", "vuejs": r"\bvue\b|quasar",
    "nodejs": r"node\.?js", "springboot": r"spring boot|spring\b", "fastapi": r"fastapi",
    "django": r"django|flask",
    "fullstack": r"full[- ]?stack", "apis_rest": r"\bapis?\b|\brest\b|graphql",
    "microservicios": r"microservici|microservice",
    "sistemas_distribuidos": r"distribuid|distributed|escalab|scalab",
    "arquitectura": r"arquitectur|architect", "seguridad": r"seguridad|security|gdpr|rgpd",
    "llm": r"\bllms?\b|large language model|modelos de lenguaje",
    "genai": r"generative ai|ia generativa|genai|gen ai",
    "rag": r"\brag\b|retrieval augmented|vector (db|database|store)|embedding",
    "agentes": r"agentic|multi-?agent|agentes? de ia|ai agents?",
    "langchain": r"langchain|langgraph|llamaindex|crewai",
    "mcp_agents": r"\bmcp\b|model context protocol",
    "prompt_engineering": r"prompt engineering|prompting",
    "evaluacion_modelos": r"evaluacion de modelos|model evaluation|\bevals?\b|benchmark",
    "deep_learning": r"deep learning|redes neuronales|neural network",
    "pytorch_tf": r"pytorch|tensorflow|keras", "sklearn": r"scikit|sklearn",
    "huggingface": r"hugging ?face|transformers", "nlp": r"\bnlp\b|natural language|lenguaje natural",
    "computer_vision": r"computer vision|vision artificial|vision por comput|deteccion de objetos",
    "opencv": r"opencv", "ocr": r"\bocr\b",
    "mlops": r"mlops|model serving|sagemaker", "mlflow": r"mlflow",
    "sql": r"\bsql\b|postgres|mysql|oracle|pl/sql",
    "data_preprocessing": r"limpieza de datos|data (cleaning|quality|preparation)|preprocesad|calidad del dato",
    "modelado_datos": r"modelo de datos|data model|dimensional|star schema",
    "etl": r"\betl\b|\belt\b|ingesta|ssis", "spark": r"\bspark\b|pyspark",
    "databricks": r"databricks", "snowflake": r"snowflake", "airflow": r"airflow|\bdbt\b",
    "kafka": r"kafka|streaming|event[- ]driven", "powerbi": r"power ?bi|tableau|looker|qlik",
    "estadistica": r"estadistic|statistic", "mineria_datos": r"mineria de datos|data mining",
    "cloud_datos": r"data (lake|warehouse|platform)|lakehouse|bigquery|redshift|synapse",
    "numpy_pandas": r"pandas|numpy", "control_m": r"control-?m",
    "data_governance": r"gobernanza|data governance", "ab_testing": r"a/b test",
    "aws": r"\baws\b|amazon web services|lambda\b", "azure": r"azure",
    "gcp": r"\bgcp\b|google cloud|cloud run", "docker": r"docker|contenedor|container",
    "kubernetes": r"kubernetes|k8s|openshift",
    "cicd": r"ci/cd|cicd|integracion continua|jenkins|github actions|gitlab ci|cloud build",
    "terraform": r"terraform|infrastructure as code|\biac\b", "ansible": r"ansible",
    "linux": r"linux|unix", "git": r"\bgit\b|github|gitlab|control de versiones",
    "observability": r"observab|monitoriz|monitoring|grafana|prometheus|logging|tracing",
    "despliegue_produccion": r"produccion|production|deploy|despliegue",
    "testing": r"\btests?\b|testing|unitari|pruebas|pytest|junit",
    "debugging": r"debug|troubleshoot|incidencia", "documentacion": r"documentaci|documentation",
    "automatizacion": r"automatiz|automation", "agile": r"agile|scrum|kanban",
    "prototipado": r"prototip|\bpoc\b|prueba de concepto", "pydantic": r"pydantic",
    "comunicacion_negocio": r"stakeholder|equipos de negocio|business team|comunicacion con negocio",
    "liderazgo": r"liderar|lideraz|mentor|tech lead|tutoriz",
    "gestion_proyectos": r"gestion de proyecto|project manage",
    "erp_producto": r"\berp\b", "SaaS": r"\bsaas\b", "crm": r"\bcrm\b",
    "consultoria": r"consultoria|consulting", "investigacion": r"investigacion|research",
    "ingles_c1": r"\bingles\b|\benglish\b|\bb2\b|\bc1\b|bilingue",
    "espanol_nativo": r"\bespanol\b|\bspanish\b|castellano",
    "frances_b1": r"\bfrances\b|\bfrench\b", "euskera": r"euskera|basque",
    "master_ds": r"\bmaster\b|msc\b", "doctorado": r"doctorad|\bphd\b",
}
# «comunicacion_negocio» a propósito NO incluye «cliente»: se disparaba en
# todas las ofertas por el pie de página (ver infojobs.py).


def cuenta_terminos(texto_norm, dicc=None):
    """Cada hit lleva un fragmento corto (~110 caracteres) alrededor de la
    PRIMERA aparición del término, para escribir `reqs` en el paso 6 sin leer
    la ficha entera. Devuelve None si no hay texto."""
    d = dicc if dicc is not None else DICC
    if not d or not texto_norm:
        return None
    hits = []
    for clave, patron in d.items():
        regex = re.compile(patron)
        m = list(regex.finditer(texto_norm))
        if not m:
            continue
        idx = m[0].start()
        frag = texto_norm[max(0, idx - 40):idx + 70]
        frag = re.sub(r"\s+", " ", frag).strip()
        hits.append([clave, len(m), frag])
    hits.sort(key=lambda h: -h[1])
    return hits
