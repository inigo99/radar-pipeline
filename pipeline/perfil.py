# -*- coding: utf-8 -*-
"""Modelo de evidencia del CV y candado anti-invención.

prominencia 1.0 = demostrado en resumen o bullets
prominencia 0.5 = sólo listado en «Competencias técnicas»
prominencia 0.0 = no lo tiene -> NUNCA sube. Esta regla no se toca.
"""
from datos import PERFIL as _P

ORIG  = _P["evidencia_orig"]
TECHO = _P["techo"]

def prominencia_adaptada(term, usados):
    """Prominencia del término en el CV adaptado.
    Sólo sube si (a) ya lo tiene y (b) el CV adaptado lo saca a un bullet o al resumen."""
    base = ORIG.get(term, 0.0)
    if base == 0.0:
        return 0.0                      # no lo tiene -> no se inventa
    if term in usados:
        return max(base, TECHO.get(term, base))
    return base


# Término corto (ES/EN) para cada clave de `pipeline/vocabulario.md`, usado
# SÓLO para imprimir `skills_extra` en el CV (ver `_skills_extra_auto()` en
# `dashboard.py`). No es la etiqueta del anuncio (esa la escribe cada oferta
# a su manera): es un nombre de tecnología corto y estable, para que la línea
# "También relevante para esta oferta" no arrastre frases largas del tipo
# "Python (5+ años) y async/asyncio". Si se añade una clave nueva a
# `vocabulario.md`/`evidencia_orig` y no aparece aquí, `_skills_extra_auto()`
# la ignora en vez de inventarse un término -- añadir la entrada aquí es lo
# que hace falta para que empiece a contar.
#
# A propósito NO están aquí las claves que no son "stack" en el sentido que
# pidió Íñigo (tecnologías/herramientas): idiomas hablados (`ingles_c1`,
# `espanol_nativo`, `frances_b1`), titulaciones (`master_ds`, `grado_ia`) y
# etiquetas de negocio/blandas o de categoría de puesto (`comunicacion_negocio`,
# `liderazgo`, `poc_negocio`, `fullstack`, `SaaS`, `erp_producto`). Añadirlas
# haría que casi cualquier oferta sacara la misma línea genérica ("Inglés C1",
# "Full Stack"...) en vez de la tecnología concreta que la oferta señala.
TERMINOS_SKILL = {
    "CUDA": ("CUDA", "CUDA"),
    "ab_testing": ("A/B testing", "A/B testing"),
    "agentes": ("Agentes de IA", "AI agents"),
    "agentes_function_calling": ("Function calling", "Function calling"),
    "agile": ("Scrum/Jira", "Scrum/Jira"),
    "airflow": ("Airflow", "Airflow"),
    "angular": ("Angular", "Angular"),
    "apis_rest": ("APIs REST", "REST APIs"),
    "aws": ("AWS", "AWS"),
    "azure": ("Azure", "Azure"),
    "bash_linux": ("Linux/Bash", "Linux/Bash"),
    "c_cpp": ("C/C++", "C/C++"),
    "cicd": ("CI/CD", "CI/CD"),
    "computer_vision": ("Visión por computador", "Computer vision"),
    "csharp": ("C#", "C#"),
    "css": ("CSS", "CSS"),
    "cuDF": ("cuDF", "cuDF"),
    "cuantizacion": ("Cuantización de modelos", "Model quantization"),
    "data_preprocessing": ("Preprocesamiento de datos", "Data preprocessing"),
    "dbt": ("dbt", "dbt"),
    "debugging": ("Debugging", "Debugging"),
    "deep_learning": ("Deep Learning", "Deep learning"),
    "despliegue_produccion": ("Despliegue en producción", "Production deployment"),
    "docker": ("Docker", "Docker"),
    "documentacion": ("Documentación técnica", "Technical documentation"),
    "embeddings_semantic_search": ("Embeddings y búsqueda semántica", "Embeddings & semantic search"),
    "estadistica": ("Estadística", "Statistics"),
    "estadistica_inferencial": ("Estadística inferencial", "Inferential statistics"),
    "excel_avanzado": ("Excel avanzado", "Advanced Excel"),
    "fastapi": ("FastAPI", "FastAPI"),
    "feature_engineering": ("Feature engineering", "Feature engineering"),
    "fine_tuning": ("Fine-tuning", "Fine-tuning"),
    "gcp": ("GCP", "GCP"),
    "gcp_vertex": ("GCP Vertex AI", "GCP Vertex AI"),
    "genai": ("IA Generativa", "Generative AI"),
    "git": ("Git", "Git"),
    "github_actions": ("GitHub Actions", "GitHub Actions"),
    "gpu_serving": ("Serving en GPU (Triton/ONNX)", "GPU serving (Triton/ONNX)"),
    "grafana": ("Grafana", "Grafana"),
    "html": ("HTML", "HTML"),
    "huggingface": ("HuggingFace", "HuggingFace"),
    "interpretabilidad_lime": ("Interpretabilidad (LIME)", "Interpretability (LIME)"),
    "java": ("Java", "Java"),
    "javascript": ("JavaScript", "JavaScript"),
    "jenkins": ("Jenkins", "Jenkins"),
    "kafka": ("Kafka", "Kafka"),
    "kubernetes": ("Kubernetes", "Kubernetes"),
    "langchain": ("LangChain", "LangChain"),
    "linux": ("Linux", "Linux"),
    "llamaindex": ("LlamaIndex", "LlamaIndex"),
    "llm": ("LLMs", "LLMs"),
    "lora": ("LoRA", "LoRA"),
    "microservicios": ("Microservicios", "Microservices"),
    "mineria_datos": ("Minería de datos", "Data mining"),
    "mlops": ("MLOps", "MLOps"),
    "mongodb": ("MongoDB", "MongoDB"),
    "monitorizacion_modelos": ("Monitorización de modelos", "Model monitoring"),
    "nginx": ("Nginx", "Nginx"),
    "nlp": ("NLP", "NLP"),
    "nodejs": ("Node.js", "Node.js"),
    "numpy_pandas": ("NumPy/Pandas", "NumPy/Pandas"),
    "ocr": ("OCR", "OCR"),
    "opencv": ("OpenCV", "OpenCV"),
    "patrones_diseno": ("Patrones de diseño (SOLID)", "Design patterns (SOLID)"),
    "php": ("PHP", "PHP"),
    "powerbi": ("Power BI", "Power BI"),
    "prompt_engineering": ("Prompt engineering", "Prompt engineering"),
    "python": ("Python", "Python"),
    "pytorch_tf": ("PyTorch/TensorFlow", "PyTorch/TensorFlow"),
    "r_lang": ("R", "R"),
    "rabbitmq": ("RabbitMQ", "RabbitMQ"),
    "rag": ("RAG", "RAG"),
    "react": ("React", "React"),
    "responsible_ai": ("IA Responsable", "Responsible AI"),
    "scrum_jira": ("Scrum/Jira", "Scrum/Jira"),
    "series_temporales": ("Series temporales", "Time series"),
    "sistemas_distribuidos": ("Sistemas distribuidos", "Distributed systems"),
    "sklearn": ("Scikit-learn", "Scikit-learn"),
    "snowflake": ("Snowflake", "Snowflake"),
    "spark": ("Spark", "Spark"),
    "sql": ("SQL", "SQL"),
    "swagger": ("Swagger/OpenAPI", "Swagger/OpenAPI"),
    "tensor_decomposition": ("Descomposición tensorial", "Tensor decomposition"),
    "testing": ("Testing (unitario/integración)", "Testing (unit/integration)"),
    "triton_onnx": ("Triton/ONNX", "Triton/ONNX"),
    "typescript": ("TypeScript", "TypeScript"),
    "vertex_ai": ("Vertex AI", "Vertex AI"),
    "visualizacion": ("Visualización de datos", "Data visualization"),
    "wandb": ("Weights & Biases", "Weights & Biases"),
    "websockets": ("WebSockets", "WebSockets"),
}


def termino_skill(clave, idioma):
    """Nombre corto de una clave de vocabulario, en el idioma pedido.
    None si la clave no tiene término asignado (no se inventa uno)."""
    par = TERMINOS_SKILL.get(clave)
    if not par:
        return None
    return par[1] if idioma == "en" else par[0]
