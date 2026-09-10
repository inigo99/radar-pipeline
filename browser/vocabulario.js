/* Diccionario término -> regex, para sacar los `reqs` de una oferta aceptada
 * sin volcar la descripción entera al contexto. Las claves son las de
 * pipeline/vocabulario.md: si aquí aparece una que allí no está, la puntuación
 * la tratará como evidencia 0 y hundirá la oferta sin motivo.
 *
 * Se aplica SIEMPRE sobre el texto de la descripción normalizado (R.norm),
 * nunca sobre el HTML de la página: ver el aviso de infojobs.js.
 */
(function (R) {
  R.DICC = {
    python: '\\bpython\\b', java: '\\bjava\\b(?!script)', javascript: 'javascript',
    typescript: 'typescript', csharp: 'c#|\\.net\\b|dotnet', golang: '\\bgolang\\b',
    scala: '\\bscala\\b', c_cpp: '\\bc\\+\\+\\b', php: '\\bphp\\b|laravel|symfony',
    react: '\\breact\\b', angular: 'angular', vuejs: '\\bvue\\b|quasar',
    nodejs: 'node\\.?js', springboot: 'spring boot|spring\\b', fastapi: 'fastapi',
    django: 'django|flask',
    fullstack: 'full[- ]?stack', apis_rest: '\\bapis?\\b|\\brest\\b|graphql',
    microservicios: 'microservici|microservice', sistemas_distribuidos: 'distribuid|distributed|escalab|scalab',
    arquitectura: 'arquitectur|architect', seguridad: 'seguridad|security|gdpr|rgpd',
    llm: '\\bllms?\\b|large language model|modelos de lenguaje',
    genai: 'generative ai|ia generativa|genai|gen ai',
    rag: '\\brag\\b|retrieval augmented|vector (db|database|store)|embedding',
    agentes: 'agentic|multi-?agent|agentes? de ia|ai agents?',
    langchain: 'langchain|langgraph|llamaindex|crewai',
    mcp_agents: '\\bmcp\\b|model context protocol',
    prompt_engineering: 'prompt engineering|prompting',
    evaluacion_modelos: 'evaluacion de modelos|model evaluation|\\bevals?\\b|benchmark',
    deep_learning: 'deep learning|redes neuronales|neural network',
    pytorch_tf: 'pytorch|tensorflow|keras', sklearn: 'scikit|sklearn',
    huggingface: 'hugging ?face|transformers', nlp: '\\bnlp\\b|natural language|lenguaje natural',
    computer_vision: 'computer vision|vision artificial|vision por comput|deteccion de objetos',
    opencv: 'opencv', ocr: '\\bocr\\b',
    mlops: 'mlops|model serving|sagemaker', mlflow: 'mlflow',
    sql: '\\bsql\\b|postgres|mysql|oracle|pl/sql',
    data_preprocessing: 'limpieza de datos|data (cleaning|quality|preparation)|preprocesad|calidad del dato',
    modelado_datos: 'modelo de datos|data model|dimensional|star schema',
    etl: '\\betl\\b|\\belt\\b|ingesta|ssis', spark: '\\bspark\\b|pyspark',
    databricks: 'databricks', snowflake: 'snowflake', airflow: 'airflow|\\bdbt\\b',
    kafka: 'kafka|streaming|event[- ]driven', powerbi: 'power ?bi|tableau|looker|qlik',
    estadistica: 'estadistic|statistic', mineria_datos: 'mineria de datos|data mining',
    cloud_datos: 'data (lake|warehouse|platform)|lakehouse|bigquery|redshift|synapse',
    numpy_pandas: 'pandas|numpy', control_m: 'control-?m',
    data_governance: 'gobernanza|data governance', ab_testing: 'a/b test',
    aws: '\\baws\\b|amazon web services|lambda\\b', azure: 'azure',
    gcp: '\\bgcp\\b|google cloud|cloud run', docker: 'docker|contenedor|container',
    kubernetes: 'kubernetes|k8s|openshift',
    cicd: 'ci/cd|cicd|integracion continua|jenkins|github actions|gitlab ci|cloud build',
    terraform: 'terraform|infrastructure as code|\\biac\\b', ansible: 'ansible',
    linux: 'linux|unix', git: '\\bgit\\b|github|gitlab|control de versiones',
    observability: 'observab|monitoriz|monitoring|grafana|prometheus|logging|tracing',
    despliegue_produccion: 'produccion|production|deploy|despliegue',
    testing: '\\btests?\\b|testing|unitari|pruebas|pytest|junit',
    debugging: 'debug|troubleshoot|incidencia', documentacion: 'documentaci|documentation',
    automatizacion: 'automatiz|automation', agile: 'agile|scrum|kanban',
    prototipado: 'prototip|\\bpoc\\b|prueba de concepto', pydantic: 'pydantic',
    comunicacion_negocio: 'stakeholder|equipos de negocio|business team|comunicacion con negocio',
    liderazgo: 'liderar|lideraz|mentor|tech lead|tutoriz',
    gestion_proyectos: 'gestion de proyecto|project manage',
    erp_producto: '\\berp\\b', SaaS: '\\bsaas\\b', crm: '\\bcrm\\b',
    consultoria: 'consultoria|consulting', investigacion: 'investigacion|research',
    ingles_c1: '\\bingles\\b|\\benglish\\b|\\bb2\\b|\\bc1\\b|bilingue',
    espanol_nativo: '\\bespanol\\b|\\bspanish\\b|castellano',
    frances_b1: '\\bfrances\\b|\\bfrench\\b', euskera: 'euskera|basque',
    master_ds: '\\bmaster\\b|msc\\b', doctorado: 'doctorad|\\bphd\\b',
  };
  /* «comunicacion_negocio» a propósito NO incluye «cliente»: se disparaba en
   * todas las ofertas por el pie de página. */
})(window.__radar);
