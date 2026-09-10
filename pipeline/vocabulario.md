# Vocabulario de `reqs` y convenciones de peso

Los `reqs` de una oferta son la única entrada del modelo de puntuación, así que
si cada día se inventan claves nuevas las ofertas dejan de ser comparables entre
sí y el ranking del dashboard pierde sentido. Este fichero existe para no tener
que abrir cuatro ofertas viejas cada mañana a ver cómo se llamaban las cosas.

## Formato

Cada requisito es una terna `[clave, peso, etiqueta]`:

```json
["python", 10, "Python (5+ años) y async/asyncio"]
```

- **clave**: de la lista de abajo. Si no está, mira si encaja alguna existente
  antes de crear una nueva; el fondo del asunto es que `perfil.evidencia_orig`
  sepa si Íñigo lo tiene o no, y una clave nueva vale 0 automáticamente.
- **peso**: 1-10, *la importancia que le da el anuncio*, no lo bien que encaje
  él. Ver la escala más abajo.
- **etiqueta**: cómo lo nombra el anuncio, en su idioma. Es lo que se ve en el
  dashboard, así que copia su vocabulario, no el tuyo.

`surfaced` es el subconjunto de claves que el CV adaptado saca a un bullet o al
resumen. Sólo pueden estar las que tengan evidencia (`evidencia_orig > 0`):
meter ahí algo que no tiene no sube la nota, es inventarse el CV.

## Escala de pesos

| Peso | Cuándo |
|---|---|
| 10 | El puesto es eso. Sin ello no hay candidatura. |
| 8-9 | Requisito imprescindible, listado como tal. |
| 6-7 | Requisito real, pero uno más de la lista. |
| 4-5 | «Se valorará», deseable, o parte del entorno. |
| 1-3 | Mención de pasada, o un extra que apenas pesa. |

Regla práctica: si un anuncio tiene más de tres claves con peso ≥ 9, es que
están mal puestas. Un anuncio normal tiene una o dos cosas que de verdad importan.

## Claves en uso

**Lenguajes y frameworks**
`python` `java` `javascript` `typescript` `csharp` `golang` `scala` `c_cpp` `php`
`react` `angular` `vuejs` `nodejs` `springboot` `fastapi` `django`

**Arquitectura y backend**
`fullstack` `apis_rest` `microservicios` `sistemas_distribuidos` `arquitectura`
`seguridad` `medios_pago` `pci_dss`

**IA generativa y agentes**
`llm` `genai` `rag` `agentes` `langchain` `prompt_engineering` `mcp_agents`
`evaluacion_modelos` `observability`

**Machine learning y visión**
`deep_learning` `pytorch_tf` `sklearn` `huggingface` `nlp` `computer_vision`
`opencv` `ocr` `cuantizacion` `gpu_serving` `CUDA` `onnx_movil` `rl_sft`
`tensor_decomposition` `speech`

**Datos**
`sql` `data_preprocessing` `etl` `spark` `pyspark` `databricks` `snowflake`
`airflow` `kafka` `powerbi` `estadistica` `mineria_datos` `modelado_datos`
`cloud_datos` `numpy_pandas` `data_governance` `ab_testing` `control_m`

**Cloud e infraestructura**
`aws` `azure` `gcp` `gcp_vertex` `docker` `kubernetes` `cicd` `terraform`
`ansible` `linux` `git` `mlops` `mlflow` `devsecops` `despliegue_produccion`

**Práctica de ingeniería**
`testing` `debugging` `documentacion` `automatizacion` `agile` `prototipado`
`opensource` `pydantic`

**Producto, negocio y persona**
`comunicacion_negocio` `liderazgo` `gestion_proyectos` `poc_negocio`
`erp_producto` `SaaS` `crm` `consultoria` `investigacion` `sostenibilidad`
`logistica` `iiot`

**Idiomas y titulación**
`ingles_c1` `espanol_nativo` `frances_b1` `euskera` `master_ds` `grado_ia`
`doctorado` `publicaciones` `certificacion_gcp`

## Trampas conocidas

- **No inflar.** Si el anuncio no nombra Kubernetes, no lo metas aunque «se
  sobreentienda». Los huecos que salen en el dashboard son información: un
  hueco inventado le hace descartar una oferta buena.
- **`sql` cubre bases de datos en general.** No hacen falta claves por motor.
- **`comunicacion_negocio` se dispara con facilidad** al extraer términos de
  HTML crudo, porque «cliente» aparece en cualquier pie de página. Compruébalo
  contra el texto de la descripción antes de darle peso alto.
- **Las claves nuevas valen 0** en `evidencia_orig`, así que una clave nueva
  mal elegida hunde la puntuación de la oferta sin motivo real. Si de verdad
  hace falta una nueva, dilo en el resumen final para que él decida si añadirla
  al perfil.
