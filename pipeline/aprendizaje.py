# -*- coding: utf-8 -*-
"""Reorientación hacia Data Science e IA: prioridad por familia y clasificación
de huecos por lo aprendibles que son entre la candidatura y una posible entrevista.

Creado el 10 sep 2026, a petición de Íñigo: quiere que el radar tire más de las
familias de IA/Data Science mientras se reorienta, y que cada oferta le diga qué
huecos merece la pena repasar antes de una entrevista y cuáles no son realistas
en ese plazo. Ver [[redaccion-cv-cartas]] para el candado: esta tabla NUNCA se usa
para tocar el CV ni la carta, sólo para un panel informativo en el dashboard.
"""

# ---------------------------------------------------------------------------
# 1. Prioridad por familia
#
# No es la nota de encaje del CV (esa no se toca: sigue siendo `score_adap`,
# honesta y sin ponderar). Es un multiplicador aparte, sólo para decidir el
# ORDEN por defecto de la tabla del dashboard, para que las familias de IA y
# Data Science asomen antes que Full Stack/Backend a igualdad de encaje.
# Full Stack/Backend sigue en el radar (Íñigo lo pidió así el 10 sep 2026):
# sólo pesa un poco menos por defecto. Revisar si dentro de unos meses ya no
# hace falta el empujón, o si hay que quitar del todo alguna familia.
PESO_FAMILIA = {
    "genai":    1.15,
    "ml":       1.12,
    "cv":       1.12,
    "ds":       1.12,
    "mlops":    1.05,
    "research": 1.05,
    "backend":  0.92,
}
PESO_FAMILIA_DEFECTO = 1.0

# Familias que cuentan como "foco" para el aviso del dashboard (stat "Foco IA/DS").
FAMILIAS_FOCO = {"genai", "ml", "cv", "ds"}


def peso_familia(familia):
    return PESO_FAMILIA.get(familia, PESO_FAMILIA_DEFECTO)


# ---------------------------------------------------------------------------
# 2. Dificultad de aprendizaje por clave de `reqs`
#
# Sólo se consulta para claves que ya son un hueco real (evidencia_orig == 0):
# esto no decide si algo es un hueco, sólo qué tan realista es cerrarlo en el
# tiempo típico entre mandar una candidatura y una posible entrevista (deja de
# tener sentido pensar en "semanas" cuando el requisito es una titulación, un
# idioma nuevo o años de experiencia: ahí el nivel es igualmente `lento`, pero
# la nota lo dice tal cual en vez de sugerir estudiar).
#
# Niveles:
#   rapido  - días a una semana: una librería, un framework o una herramienta
#             sobre una base que ya tiene. Se puede defender con soltura.
#   medio   - varias semanas de dedicación real para hablar de ello con
#             criterio, no sólo de oídas.
#   lento   - no es realista cubrirlo bien en el plazo de un proceso de
#             selección (una disciplina profunda, una certificación pesada,
#             una titulación, un idioma nuevo, años de experiencia). Aquí la
#             recomendación no es "estudia esto", es "prepara una respuesta
#             honesta", igual que ya hacía el panel de huecos.
#
# Que una clave no esté aquí no es un error: se clasifica con el valor por
# defecto (DEFECTO, más abajo) y no rompe nada. Si aparece a menudo, añádela
# con criterio -- igual que las claves nuevas de vocabulario.md.
DIFICULTAD = {
    # Lenguajes y frameworks
    "python":      ("rapido", "Ya programa a diario en varios lenguajes; una librería o framework concreto se cubre en días."),
    "java":        ("rapido", "Sintaxis cercana a lo que ya usa; en una o dos semanas se defiende en una entrevista técnica."),
    "javascript":  ("rapido", "Lo usa a diario en el front; lo que falte es cuestión de días."),
    "typescript":  ("rapido", "Es JavaScript con tipos; el salto es de días, no de semanas."),
    "csharp":      ("rapido", "Lenguaje C-like más sobre su base de Java/Python; una semana de repaso cubre lo básico."),
    "golang":      ("medio", "La sintaxis es sencilla, pero el modelo de concurrencia (goroutines, channels) pide varias semanas de práctica real."),
    "scala":       ("medio", "Cambia el paradigma (funcional + JVM); defenderlo con criterio pide varias semanas, no días."),
    "c_cpp":       ("medio", "Gestión manual de memoria y semántica distinta a lo que usa a diario; un repaso de un par de semanas cubre lo básico, no la profundidad que suele pedirse en C++."),
    "php":         ("rapido", "Sintaxis familiar viniendo de su stack; en días monta algo funcional."),
    "react":       ("rapido", "Con su base de front, un proyecto pequeño de una semana alcanza para hablar de él con soltura."),
    "angular":     ("rapido", "Mismo caso que React: una semana de proyecto de ejemplo cubre lo esencial."),
    "vuejs":       ("rapido", "Framework de componentes similar a lo que ya conoce; días, no semanas."),
    "nodejs":      ("rapido", "Ya conoce JavaScript; el runtime en sí se aprende en días."),
    "springboot":  ("rapido", "Con su base de Java, el framework se coge en días, una semana como mucho."),
    "fastapi":     ("rapido", "Framework ligero sobre Python; monta una API de ejemplo en un par de días."),
    "django":      ("rapido", "Con su experiencia en backend Python, lo esencial se cubre en días."),

    # Arquitectura y backend
    "fullstack":            ("rapido", "Es su perfil de base; si aparece como hueco es por una pieza concreta, no por el concepto."),
    "apis_rest":            ("rapido", "Lo construye a diario; cualquier hueco aquí es de detalle."),
    "microservicios":       ("medio", "El concepto se entiende rápido, pero defenderlo con ejemplos reales (versionado, resiliencia, comunicación entre servicios) pide varias semanas."),
    "sistemas_distribuidos":("medio", "Los conceptos (consenso, particionado, tolerancia a fallos) se estudian en semanas; la profundidad real viene de haberlo sufrido en producción."),
    "arquitectura":         ("medio", "Se puede repasar de forma seria en un par de semanas, pero criterio real pide más tiempo."),
    "seguridad":            ("medio", "OWASP y buenas prácticas se repasan en un par de semanas; una certificación formal no."),
    "medios_pago":          ("lento", "Regulación y flujos reales (PSD2, tokenización) se aprenden trabajando con ellos, no en un sprint de estudio."),
    "pci_dss":              ("lento", "Es una normativa de cumplimiento, no una habilidad técnica: se aprende trabajando bajo ella."),

    # IA generativa y agentes
    "llm":                  ("rapido", "Con su formación en IA, entender la arquitectura y el uso práctico de LLMs es cuestión de días de lectura dirigida."),
    "genai":                ("rapido", "Mismo caso que LLM: base ya cercana, cuestión de días."),
    "rag":                  ("rapido", "El patrón (embeddings + recuperación + generación) se monta en un proyecto de ejemplo en unos días."),
    "agentes":              ("rapido", "Con LangChain o similar, un agente de juguete se monta en días."),
    "langchain":            ("rapido", "Documentación extensa y ejemplos abundantes; un fin de semana de práctica da para hablar de ello con soltura."),
    "prompt_engineering":   ("rapido", "Se aprende practicando; días bastan para defenderlo con ejemplos propios."),
    "mcp_agents":           ("medio", "Es más reciente y con menos tutoriales asentados; construir algo real lleva más de unos días."),
    "evaluacion_modelos":   ("medio", "Las métricas se explican rápido, pero montar un pipeline de evaluación serio pide varias semanas."),
    "observability":        ("medio", "Las herramientas de trazas y logging estructurado se aprenden en semanas si no las ha tocado antes."),

    # Machine learning y visión
    "deep_learning":        ("medio", "Ya tiene la base del máster; refrescar arquitecturas concretas pide semanas, no días."),
    "pytorch_tf":           ("medio", "Si parte de cero con el framework, varias semanas de práctica real hacen falta para defenderlo."),
    "sklearn":              ("rapido", "API sencilla y bien documentada; en días monta un ejemplo funcional."),
    "huggingface":          ("rapido", "API de alto nivel; en días monta y ajusta un modelo de ejemplo."),
    "nlp":                  ("medio", "Los conceptos generales se repasan rápido; la práctica real con datos de texto pide más tiempo."),
    "computer_vision":      ("medio", "Con la base del máster, refrescar y montar un proyecto de ejemplo pide varias semanas."),
    "opencv":               ("rapido", "Librería concreta y bien documentada; días para un ejemplo funcional."),
    "ocr":                  ("rapido", "Con las librerías actuales, un pipeline de ejemplo se monta en días."),
    "cuantizacion":         ("lento", "Es optimización de bajo nivel; entenderla en profundidad pide semanas de estudio especializado."),
    "gpu_serving":          ("lento", "Infraestructura especializada (Triton, TensorRT…); no se improvisa en el margen de una candidatura."),
    "CUDA":                 ("lento", "Programación de bajo nivel; curva de meses, no algo que se cubra antes de una entrevista."),
    "onnx_movil":           ("lento", "Despliegue en dispositivo es un área propia; no realista a corto plazo."),
    "rl_sft":               ("lento", "Reinforcement learning y fine-tuning son un área de especialización propia; no es realista cubrirla a corto plazo."),
    "tensor_decomposition": ("lento", "Tema muy especializado de investigación; no aplica a un repaso corto."),
    "speech":               ("medio", "Con la base de deep learning, un proyecto de ejemplo con librerías actuales pide varias semanas."),

    # Datos
    "sql":                  ("rapido", "Lo usa habitualmente; cualquier hueco aquí es de detalle."),
    "data_preprocessing":   ("rapido", "Ya lo hace con pandas; adaptarlo a una herramienta nueva es cuestión de días."),
    "etl":                  ("rapido", "El concepto y las herramientas básicas se cubren en días desde su base de backend."),
    "spark":                ("medio", "Los conceptos se explican rápido, pero trabajar con Spark de verdad (particionado, shuffles, tuning) pide semanas."),
    "pyspark":              ("medio", "Mismo caso que Spark: sintaxis rápida, profundidad real más lenta."),
    "databricks":           ("medio", "Plataforma con su propio flujo de trabajo; un par de semanas para defenderse en una entrevista."),
    "snowflake":            ("medio", "Plataforma concreta con su propia sintaxis y modelo de costes; una o dos semanas para defenderse."),
    "airflow":              ("rapido", "Con su experiencia de backend, montar DAGs de ejemplo es cuestión de días."),
    "kafka":                ("medio", "El concepto se entiende rápido; operarlo con soltura (particiones, consumer groups, offsets) pide más tiempo."),
    "powerbi":              ("rapido", "Herramienta visual; en días monta un dashboard de ejemplo."),
    "estadistica":          ("medio", "Repasar lo justo para defenderse con criterio pide más que un fin de semana si no la usa a diario."),
    "mineria_datos":        ("medio", "Los algoritmos se repasan en el máster; un proyecto de ejemplo real pide varias semanas."),
    "modelado_datos":       ("medio", "El diseño de esquemas se aprende con la práctica; semanas, no días."),
    "cloud_datos":          ("medio", "Servicios concretos de un proveedor; un par de semanas para defenderse con ejemplos."),
    "numpy_pandas":         ("rapido", "Lo usa a diario; cualquier hueco aquí es de detalle."),
    "data_governance":      ("lento", "Es más una disciplina organizativa que una herramienta: se aprende participando en ella, no estudiándola sola."),
    "ab_testing":           ("rapido", "El diseño básico (grupos, significancia) se repasa en días."),
    "control_m":            ("lento", "Herramienta empresarial de nicho y con poca documentación pública; no hay forma realista de aprenderla sin acceso a ella."),

    # Cloud e infraestructura
    "aws":                  ("medio", "La consola y los servicios básicos se tocan en días, pero defenderse con criterio ante preguntas de arquitectura pide varias semanas."),
    "azure":                ("medio", "Mismo caso que AWS: básico rápido, criterio real más lento."),
    "gcp":                  ("medio", "Mismo caso que AWS/Azure."),
    "gcp_vertex":           ("medio", "Además de GCP en general, es un servicio concreto: cuenta con más tiempo."),
    "docker":               ("rapido", "Ya lo usa; cualquier hueco aquí es de detalle."),
    "kubernetes":           ("medio", "Los conceptos (pods, deployments, servicios) se explican en días; operarlo con soltura real pide semanas."),
    "cicd":                 ("rapido", "Ya trabaja con integración continua; adaptarse a una herramienta nueva es cuestión de días."),
    "terraform":            ("medio", "La sintaxis se coge rápido; diseñar módulos con criterio pide más práctica."),
    "ansible":              ("rapido", "Herramienta declarativa sencilla; en días monta un playbook de ejemplo."),
    "linux":                ("rapido", "Lo usa a diario; cualquier hueco aquí es de detalle."),
    "git":                  ("rapido", "Lo usa a diario; cualquier hueco aquí es de detalle."),
    "mlops":                ("medio", "Es más una disciplina que una herramienta suelta; montar un pipeline de ejemplo (versionado de modelos, CI para ML) pide varias semanas."),
    "mlflow":               ("rapido", "Herramienta concreta y bien documentada; en días monta un ejemplo de tracking."),
    "devsecops":            ("lento", "Integra seguridad, cumplimiento y automatización a la vez; no es un repaso de unos días."),
    "despliegue_produccion":("rapido", "Ya lo hace; cualquier hueco aquí es de detalle."),

    # Práctica de ingeniería
    "testing":        ("rapido", "Ya lo practica; adaptarse a un framework nuevo es cuestión de días."),
    "debugging":       ("rapido", "Es parte de su día a día."),
    "documentacion":   ("rapido", "Hábito de trabajo, no una tecnología que estudiar."),
    "automatizacion":  ("rapido", "Ya lo practica en su día a día."),
    "agile":           ("rapido", "Marco de trabajo, no una tecnología; se coge con la práctica de días."),
    "prototipado":     ("rapido", "Ya lo hace habitualmente."),
    "opensource":      ("rapido", "Basta con contribuir a algún proyecto real antes de la entrevista para poder hablar de ello con honestidad."),
    "pydantic":        ("rapido", "Librería concreta y sencilla; días para un ejemplo funcional."),

    # Producto, negocio y persona
    "comunicacion_negocio": ("medio", "Es una habilidad que se demuestra con casos reales, no con un repaso rápido."),
    "liderazgo":            ("lento", "Se demuestra con experiencia real liderando gente o proyectos; no se improvisa antes de una entrevista."),
    "gestion_proyectos":    ("medio", "Los marcos se repasan rápido; hablar de ello con casos propios pide más tiempo."),
    "poc_negocio":          ("medio", "Se puede preparar un caso de ejemplo propio en un par de semanas."),
    "erp_producto":         ("lento", "Cada ERP tiene su propio ecosistema; sin acceso a la herramienta no hay forma real de aprenderlo antes de tiempo."),
    "SaaS":                 ("medio", "El modelo de negocio se entiende rápido; hablar con criterio de métricas propias del sector pide más tiempo."),
    "crm":                  ("lento", "Igual que un ERP: sin haberlo usado de verdad, no hay mucho que estudiar por libre."),
    "consultoria":          ("lento", "Es un modo de trabajar que se aprende ejerciéndolo, no leyendo sobre él."),
    "investigacion":        ("medio", "Depende de qué pidan exactamente; un repaso serio de metodología pide varias semanas."),
    "sostenibilidad":       ("medio", "Se puede preparar un caso de ejemplo con lectura dirigida de un par de semanas."),
    "logistica":            ("lento", "Conocimiento de dominio que se adquiere trabajando en el sector, no en un repaso previo a una entrevista."),
    "iiot":                 ("lento", "Cruza hardware, redes industriales y protocolos específicos; no es terreno para un repaso corto."),

    # Idiomas y titulación (créditos, no habilidades: la nota lo dice tal cual)
    "ingles_c1":     ("lento", "Subir de nivel de idioma de verdad pide meses, no una preparación de última hora."),
    "espanol_nativo":("lento", "Es lengua materna; no debería aparecer como hueco real."),
    "frances_b1":    ("lento", "Subir de nivel de idioma pide meses."),
    "euskera":       ("lento", "Aprender un idioma nuevo no es cuestión de la ventana entre una candidatura y una entrevista."),
    "master_ds":     ("lento", "Es una titulación formal que no se obtiene en las semanas de un proceso de selección; si pesa mucho, vale la pena nombrar el máster que sí tiene (Ciencia de Datos y Aprendizaje Automático) como equivalente."),
    "grado_ia":      ("lento", "Titulación formal; no aplica preparación de corto plazo."),
    "doctorado":     ("lento", "Titulación de varios años; si pesa mucho en la oferta, conviene valorar si de verdad merece la pena aplicar."),
    "publicaciones": ("lento", "Se construyen con años de trabajo de investigación; no se improvisan."),
    "certificacion_gcp": ("lento", "Un examen de certificación real pide semanas de preparación dedicada; posible si el proceso se alarga, pero no cuentes con tenerla lista para una primera entrevista."),
}

DEFECTO = ("medio", "Clave sin clasificar en pipeline/aprendizaje.py. Trátala con cautela y añádela a la tabla si sigue apareciendo.")


def clasifica(clave):
    """Devuelve (nivel, nota) para una clave de `reqs` que ya es un hueco real."""
    return DIFICULTAD.get(clave, DEFECTO)
