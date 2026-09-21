# Tarea diaria — Radar de ofertas

Este fichero **es** el procedimiento de la tarea programada de las 10:00. El
prompt del trigger no lo repite: lo apunta (ver `docs/prompt_tarea.md`).

**Por qué aquí y no en el prompt.** El prompt era la pieza más larga y más
frágil del sistema y la única que vivía fuera de git: no se podía diffear, ni
revisar, ni revertir, y la regla «si cambia el procedimiento, cambia los dos»
no tenía forma de comprobarse — ya falló una vez, cuando el prompt seguía
mandando recalcular un Excel que llevaba días sin existir, y otra vez cuando
seguía diciendo que la poda por antigüedad anota sus retiradas en
`pipeline/cerradas` cuando el código (`poda_antiguedad.py`) siempre las anotó
en `filtradas` (ver Paso 7). Con el procedimiento aquí, cambiarlo es un commit:
se ve qué cambió, cuándo y por qué, y la ejecución de mañana lee la versión
nueva sola, porque clona el repo de todos modos.

**Cómo se cambia el procedimiento:** se edita este fichero y se empuja el mismo
día. El prompt del trigger sólo se toca si cambia algo de fuera del repo (la
hora, el dispositivo, el sitio de los datos, las URLs del código o del
dashboard).

---

## Antes de nada

- El pipeline se ejecuta **desde la raíz del repo** (`python pipeline/puntuar.py`),
  nunca desde `pipeline/`: los scripts leen y escriben en `data/` y `out/`
  relativos al directorio de trabajo.
- `git clone --depth 1`: el historial no hace falta.
- Sólo Python 3.11+. Ni playwright ni poppler: el pipeline no genera PDF.
- Lo que la tarea **nunca** escribe: `config/filtros` y `estado` son de Íñigo.
  Si un filtro parece estar costando ofertas buenas, se dice en el resumen del
  día y decide él.
- **Extracción con Scrapling, no con navegador manual** (desde el 21-sep-2026).
  Las herramientas son `mcp__remote-devices__ScraplingServer__*`
  (`fetch`, `stealthy_fetch`, `make_request`; cargar con `ToolSearch` si
  aparecen diferidas). Corren en el dispositivo de Íñigo y usan su Chrome real
  vía Playwright cuando hace falta navegador — no la extensión Claude en
  Chrome ni el navegador integrado de la app: **esta tarea ya no necesita
  ninguno de los dos**, porque nada implica leer una página como la vería una
  persona ni interactuar con su interfaz. Si `ScraplingServer` no aparece o
  falla en todas las llamadas (ordenador apagado o sin la app), no insistir:
  cubrir lo que no lo necesite (Tecnoempleo/Indeed/semanales, que ya iban por
  WebFetch/MCP), decir al final qué fuentes se han quedado sin cubrir y **no
  escribir `config/estado_tarea`**, para que la ventana se recupere mañana.
- **Qué herramienta según la fuente** (el porqué de cada una, con lo
  comprobado en vivo el 21-sep-2026, está en README, sección
  `pipeline/fuentes/`):
  - **LinkedIn (listado y ficha):** `fetch` con `real_chrome:true,
    disable_resources:true`. Endpoints de invitado, sin login.
  - **InfoJobs (listado):** `fetch` con `real_chrome:true,
    disable_resources:true` también vale, pero pedir además
    `extraction_type:"markdown", main_content_only:true` (o un `css_selector`
    más estrecho): el HTML crudo de esa página son 1,5M de caracteres y sólo
    hace falta lo que lleva las URLs `of-i<hash>`.
  - **InfoJobs (ficha): `stealthy_fetch`, no `fetch`.** Con
    `real_chrome:true, solve_cloudflare:true, network_idle:true, wait:1500`.
    Un `fetch` normal en la ficha devuelve un captcha GeeTest (HTTP 405,
    «¿Eres humano o un robot?»), aunque el listado sí admita `fetch` normal —
    no lo intentes con `fetch` primero para ahorrar, ya se sabe que falla.
  - **Manfred (listado y ficha):** `make_request` — es una API JSON pública,
    no hace falta navegador en absoluto. **Pedir siempre
    `extraction_type:"text"`, nunca el `"markdown"` por defecto**: el
    extractor markdown escapa guiones bajos dentro de los valores del JSON
    (`Centellic_Ago26_...` → `Centellic\_Ago26\_...`) y eso rompe
    `json.loads()`. Con `"text"` el JSON llega intacto.
  - Manfred no necesita ordenador encendido tampoco por CORS ni nada parecido
    — es HTTP puro —, pero sigue sin poder pedirse desde la nube: el proxy de
    salida de la nube bloquea `getmanfred.com` igual que el resto de
    portales, así que sigue yendo por `ScraplingServer` en el dispositivo.
- **Sin límite de 1.200 caracteres, sin tandas ni pausas.** Cada llamada de
  Scrapling devuelve el contenido completo tal cual (si es muy grande, la
  herramienta lo guarda sola en un fichero y avisa cómo leerlo con jq/python;
  no hay que trocear nada a mano ni guardar en `window`). El análisis del HTML
  ya no se pega como JS en una pestaña: vive en `pipeline/fuentes/`
  (`comun.py`, `vocabulario.py`, `linkedin.py`, `infojobs.py`, `manfred.py`),
  Python normal en el repo. `detallar_una()` calcula los `terminos` del
  vocabulario en la misma pasada que la modalidad, así que el Paso 6 no
  necesita releer la ficha sólo para los `reqs`.
- **Sólo lectura, igual que siempre.** Todo lo de arriba son peticiones GET a
  endpoints públicos: no hay sesión que proteger ni pestañas que gestionar,
  pero sigue sin tener sentido ni estar permitido inscribirse en ofertas,
  enviar mensajes, guardar ofertas ni tocar ajustes de ningún portal.

## Paso 0 — Configuración y ventana

Leer `config/filtros` (`action:"read_db"`, `db_op:"get"`). Ese documento manda
sobre cualquier filtro escrito en este procedimiento y sobre cualquier texto
adjunto al disparo de la tarea — Íñigo lo edita desde «Configuración» en el
dashboard y **la tarea no lo escribe nunca**. Campos: `titulos`, `keywords`,
`excluir_keywords`, `excluir_empresas`, `buscar_remoto`, `buscar_hibrido`,
`buscar_presencial`, `areas_locales`, `ambitos`, `salario_min`,
`exigir_salario_publicado`, `anios_perfil` (`null` = calcularlos de las fechas
del CV), `margen_anios`, `ventana_horas`, `fuentes` y `fuentes_semanales`.
**`fuentes` son las de todos los días; `fuentes_semanales` sólo los lunes.**

Leer también `config/estado_tarea` (`{ultima_ejecucion: ISO}`). La ventana de
búsqueda va desde `ultima_ejecucion` hasta ahora, con un mínimo de
`ventana_horas`; si la ejecución anterior falló, se ensancha sola y recupera
lo perdido. `config/estado_tarea` **sólo se escribe si la ejecución termina
bien y se han podido cubrir todas las `fuentes`**: es lo que hace que un día
fallido no se salte ofertas.

Apuntar la hora de inicio (ISO, con zona) en cuanto arranque este paso: hace
falta en el Paso 7 para calcular cuánto ha durado la ejecución.

## Paso 0 bis — Correo

Leer el Gmail de Íñigo en la misma ventana y cruzar lo que aparezca con las
ofertas, por empresa y puesto. Clasificar cada hilo en **rechazo**, **avance**
(siguiente prueba, convocatoria, «CV leído» o cambio de estado de portal,
petición de documentación) o **acuse de recibo**, y descartar el ruido:
alertas de Indeed, recordatorios/confirmaciones de envío de LinkedIn, altas en
portales, avisos de GitHub.

- Escribir la novedad más reciente de cada oferta en `correo/<id>`: `tipo`,
  `fecha`, `asunto`, `remitente`, `extracto` (**cita literal**; vacío antes que
  inventar) y `threadId`.
- **No tocar la colección `estado`**: si hay un rechazo, la página lo sugiere y
  la fase la cambia Íñigo.
- Candidaturas cuya empresa no esté en `ofertas` van a `correo/_huerfanas`.
- Si hay una convocatoria con fecha y hora, **no crear el evento de
  calendario**: proponerlo en el resumen del Paso 8.

## Paso 1 — Datos de partida

1. `ArtifactData get collection:"pipeline" doc_id:"snapshot"` con `out_dir`.
2. `python pipeline/preparar_datos.py <volcado_snapshot> data`.
3. Si el snapshot falta o su `n_ofertas` no cuadra con la colección, volcado
   por colecciones (`ofertas`, `tailor`, `perfil/base`, `pipeline/cerradas`, y
   si están `estado`, `correo` y `filtradas`) y `preparar_datos.py` sobre él.
   El snapshot es **caché, no fuente de verdad**: `n_ofertas` está para
   desconfiar de él, no para creerlo a ciegas.

## Pasos 2-4 — Recogida por fuente

Diarias: LinkedIn, InfoJobs, Tecnoempleo, Indeed, Manfred.
Semanales (lunes): Himalayas, WeWorkRemotely, RemoteOK.

*(JSearch se eliminó el 19-sep-2026: no cubría InfoJobs en absoluto, cubría
LinkedIn sólo parcialmente y el resto eran agregadores de baja señal. Ver
README, sección de fuentes.)*

Ofertas publicadas dentro de la ventana del Paso 0, en las `fuentes` activas
de hoy, usando `titulos` y `keywords`. **Filtrar siempre por título antes de
pedir la ficha**, en todas las fuentes: es lo que evita la mayor parte del
trabajo.

**El reparto no se cambia** (aunque el motivo original ya no aplica del todo,
ver abajo):

- **LinkedIn, InfoJobs y Manfred, en el hilo principal.** El motivo original
  — «las herramientas del navegador son una sola instancia y dos agentes a la
  vez se pisan» — ya no es del todo cierto con Scrapling: cada llamada abre y
  cierra su propio proceso, no hay una pestaña compartida que pisarse. Se deja
  igual de todos modos por ahora, para no cambiar dos cosas el mismo día (la
  extracción y el reparto de agentes); si algún día conviene mover Manfred a
  un subagente (es sólo JSON, ni siquiera necesita navegador vía
  `make_request`), es un cambio aparte y deliberado, no un efecto colateral de
  esta migración.
- **Todo lo demás en UN solo subagente** (Tecnoempleo, Indeed y, los lunes,
  Himalayas/WeWorkRemotely/RemoteOK juntas), con `model: "sonnet"`. Recoger
  listados y filtrar por título no necesita más, y cada subagente nuevo
  arranca en frío y cuesta su propio prompt. Que devuelva una línea por oferta
  superviviente, no páginas.

**Al clasificar, pasar la configuración — no decidir la modalidad a mano.**
`linkedin.clasificar(cfg=CFG)` / `infojobs.clasificar(cfg=CFG)` /
`manfred.filtrar(ids_conocidos, desde, cfg=CFG)` reciben `config/filtros`
(bastan `buscar_remoto`/`buscar_hibrido`/`buscar_presencial`) y son ellas las
que deciden qué modalidades entran — sin ese argumento se comportan como sólo
remoto. `local` (zonas de `areas_locales`) entra siempre, al margen de esos
tres campos.

Notas por fuente:

- **LinkedIn**: `f_TPR=r86400&f_WT=2` (24 h, remoto) más búsquedas por las
  zonas locales sin `f_WT`, contra el endpoint de invitado
  (`jobs-guest/jobs/api/seeMoreJobPostings/search`), vía
  `ScraplingServer.fetch` (`real_chrome:true, disable_resources:true`). Partir
  el HTML por `<li>` y sacar campos con regex sobre
  `data-entity-urn="urn:li:jobPosting:` (`pipeline/fuentes/linkedin.py:parsear`).
  **La etiqueta «remoto» de LinkedIn miente a menudo**: la modalidad se decide
  con la frase literal de la descripción, no con la etiqueta del listado; si
  el listado la marca remota y la descripción no la contradice, entra como
  *remoto sin confirmar*.
- **InfoJobs**: `teleworkingIds=2&sinceDate=_7_DAYS`. Listado vía
  `ScraplingServer.fetch` con `extraction_type:"markdown", main_content_only:true`
  (el HTML crudo son 1,5M de caracteres; en markdown, ~50K, y las URLs
  `of-i<hash>` se siguen extrayendo igual por regex). **Ficha vía
  `ScraplingServer.stealthy_fetch`** (`real_chrome:true, solve_cloudflare:true,
  network_idle:true, wait:1500`) — un `fetch` normal en la ficha devuelve un
  captcha GeeTest (HTTP 405), comprobado el 21-sep-2026; el listado sí admite
  `fetch` normal, sólo la ficha necesita el stealthy. Empresa en
  `<meta name="description">`; sobre texto plano: `Bruto/año`,
  `Al menos N años`, `Solo teletrabajo`, `Hace Nd`. El recorte de la
  descripción (`infojobs.py:descripcion()`) sigue siendo necesario: el texto
  completo de la página contiene «infojobs.net» en el pie, y un contador de
  tecnologías sin recortar lo confunde con menciones a .NET en todas las
  ofertas.
- **Tecnoempleo**: por WebFetch el parámetro `keywords=` se ignora; verificar
  la fecha en la ficha, no en el listado.
- **Indeed**: MCP `search_jobs`/`get_job_details` (fecha absoluta de
  publicación). Devuelve mucha oferta antigua: filtrar por fecha con dureza.
- **Manfred**: API JSON pública vía `ScraplingServer.make_request` — sin
  navegador, y **siempre con `extraction_type:"text"`** (ver «Antes de nada»:
  el `"markdown"` por defecto rompe el JSON). El listado ya trae salario y
  `remotePercentage` estructurados; la ficha, técnicas exigidas con nivel y
  sección. Obliga a publicar salario. Priorizarla.
- **Himalayas** (lunes): los «X hours ago» son de re-rastreo, no de
  publicación. Rinde poco.
- **WeWorkRemotely/RemoteOK** (lunes): «Anywhere in the World» de WWR miente,
  hay que abrir la oferta y mirar «Your Location»; RemoteOK sólo es legible por
  su feed (`https://remoteok.com/api`), el HTML llega sin filas. Baja señal
  las dos.

## Paso 5 — Filtrado y deduplicación

```bash
python pipeline/filtrar.py candidatas.json data/ok.json --filtros filtros.json
python pipeline/dedupe.py data/ok.json nuevas.json
```

Volcar antes las candidatas de todas las fuentes a `candidatas.json` (al menos
`id`, `empresa`, `puesto`, `salario`) y `config/filtros` a `filtros.json`.

Lo que aparta `filtrar.py` (empresa excluida, palabra excluida, salario)
va a la colección `filtradas` con su motivo y su detalle. Los duplicados de
`dedupe.py` también, con `motivo: "duplicada"`.

Si `dedupe.py` avisa de duplicados **ya dentro** del radar, no borrar nada por
cuenta propia: puede haber seguimiento, notas o correo en uno de los dos.
Decirlo en el resumen y que decida Íñigo. Las intermediarias tipo «Hired»/
«Hire Feed» publican clones sin nombrar al cliente en LinkedIn: meter sólo la
que mejor encaje, con `alerta` pidiendo empresa final y país, y descartar el
resto del clon.

**Modalidad y `ambitos` no pasan por `filtrar.py`, a propósito.** La modalidad
ya se decidió al extraer y clasificar la ficha con la configuración real
(Pasos 2-4); repetirla en Python sería redundante. `ambitos` necesita que
alguien lea la frase de `comun.ambito()` — la misma forma gramatical vale para
una restricción o para una apertura, y decidirlo a ciegas es inventar un
criterio (ver `pipeline/vocabulario.md`).

**Los años de experiencia no son motivo de descarte aquí.** Se anotan en
`anios_min` (Paso 6) y la oferta entra igual; la comparación con el CV la hace
el dashboard en el navegador.

## Paso 6 — Fichas de las supervivientes

Cada oferta nueva necesita su entrada en `ofertas` **y** en `tailor` (familia,
titular y resumen; sin `carta` ni `skills_extra`).

- **`titular` y `resumen` son lo único del CV que se adapta a la oferta.**
  `resumen`: 2-3 frases, **máximo 240 caracteres** — quién es, el logro que
  conecta con la oferta y, opcionalmente, las tecnologías clave. Las ofertas
  anteriores al 10-sep-2026 llevan resúmenes más largos: no se reescriben en
  bloque, sólo las nuevas salen cortas.
- **Nunca «Senior»/«Sénior»/«Sr.» en el `titular`**, aunque el anuncio lo
  lleve — no tiene la experiencia para defenderlo en entrevista.
  `dashboard.py` lo limpia también al generar la página (`_limpia_titular()`),
  pero mejor no escribirlo de entrada.
- **El `titular` es quién es él, no texto de anuncio pegado.** Una identidad
  profesional genérica y defendible («Científico de Datos», «Full Stack
  Developer», «AI Engineer»...) vale **aunque coincida con el `puesto`**. Lo
  que nunca debe pasar es copiar el `puesto` tal cual viene en el anuncio
  cuando es literalmente texto de ficha: stack pegado, símbolos (`/`, `+`,
  `&`, `,`), acrónimos o nombre de producto interno, relleno («100%»,
  «(m/f/d)»), o un rol demasiado estrecho que no es una categoría profesional
  real. Ante esas señales, reescribir en 2-4 palabras la identidad real detrás
  del puesto para esa familia; si no hay nada mejor, «Ingeniero Informático»
  (o «Desarrollador Full Stack» si la familia es `backend`/`general`). Si el
  campo llega vacío, `dashboard.py` pone un valor por defecto según la
  `familia`, pero mejor escribir algo propio.
- `familia`: `genai`, `ml`, `cv`, `ds`, `mlops`, `research`, `backend` o
  `general` (esta última para ofertas abiertas o generalistas que no encajen
  en las otras siete). Decide qué bullets y qué variante de skills salen en
  el CV.
- `reqs`, por fuente: **Manfred** trae `oferta["reqs"]` ya en el formato
  exacto (`[clave, peso, etiqueta]`, ver `manfred.py:detallar_una`) — copiarlo
  tal cual. **LinkedIn/InfoJobs**: primero
  `python pipeline/fuentes/linkedin.py snippets --in ... --id <id>` /
  `python pipeline/fuentes/infojobs.py snippets --in ... --hash <hash>`
  (términos con más apariciones y un fragmento de dónde aparece cada uno, para
  poner peso y etiqueta); sólo si sale corta, vacía o rara, leer la ficha
  entera con el subcomando `leer` de esos mismos scripts. **Tecnoempleo/Indeed
  y semanales**: sin atajo, leer lo que devuelva el subagente. Usar el
  vocabulario de
  `pipeline/vocabulario.md` y mirar ofertas parecidas ya existentes para que
  la puntuación sea comparable.
- El salario, cuando la oferta no lo publica, sale de `pipeline/bandas.json`
  (`como_usar` dentro del fichero), no de criterio del día: banda por familia
  y tipo de empresa, factor del **país de contratación** (no de la sede),
  como mucho dos ajustes, redondeo a millares. Convertir divisa antes de
  comparar con `salario_min`. Anotar en `sal_base` familia/tipo/país/ajustes/
  conversión, de forma que la cifra se pueda rehacer leyendo esa línea. Si la
  oferta la publica, `sal_origen` es `publicado` y se copia tal cual.
- `skills_extra` **no se rellena a mano**: `dashboard.py` lo calcula solo a
  partir de `reqs` + `perfil.evidencia_orig` + la variante de skills de la
  `familia`, igual que `_limpia_titular()`. Un valor puesto a mano en
  `tailor/<id>.skills_extra` sigue teniendo prioridad si algún día hace falta
  forzar algo, pero eso es la excepción.

Recordatorios que ya están comprobados en código:

- `anios_min` se anota, **no se descarta** por experiencia.
- Nunca un campo `notas` en la oferta: choca con las notas de Íñigo. Un aviso
  va en `alerta`.
- Escribir en la BD con `write_db` en lotes (`db_op:"batch"`, `file_path`) y
  también en los JSON de `data/`.

Luego, desde la raíz del repo: `python pipeline/puntuar.py` y
`python pipeline/embudo.py` (**no es opcional**: sin él, `data/embudo.json`
no existe y la pestaña «Embudo» sale vacía aunque haya candidaturas).
`puntuar.py` calcula solo el foco (pestaña «Hoy»), la prioridad por familia y
la brecha de aprendizaje.

**No generar documentos por adelantado**: el CV adaptado, la carta y el
correo a RRHH los genera Íñigo desde el dashboard, oferta por oferta.
`generar_docs.py` está retirado y ya no hay Excel.

## Paso 7 — Pipeline, instrumentación y publicación

```bash
python pipeline/poda_antiguedad.py     # retira lo de +45 días sin seguimiento
python pipeline/puntuar.py             # -> data/resultado.json
python pipeline/embudo.py              # -> data/embudo.json  (NO es opcional)
mkdir -p out && python pipeline/dashboard.py
python pipeline/exportar_snapshot.py   # -> out/snapshot.json
```

Lo que retira `poda_antiguedad.py` se anota en `data/filtradas.json` con
`motivo: "podada"` (**no** en `pipeline/cerradas`: nunca fue así, aunque el
procedimiento lo dijera hasta el 19-sep-2026 — ver cabecera). Es lo que lee
`dashboard.py` (pestaña «Filtradas») y lo que veta reingresos en
`dedupe.py` (`conocidas_de_data()`), incluidos los reposts de la misma
vacante con un id nuevo.

Publicar `out/dashboard.html` **siempre en la misma URL del artifact**, con
`action:"read"` antes, **sin `capabilities`** (nunca `{}`: borrarlas se lleva
por delante el seguimiento y la generación de textos).

Subir `out/snapshot.json` a `pipeline/snapshot`, y sólo entonces escribir
`config/estado_tarea`.

**Instrumentación de coste (añadida el 19-sep-2026).** `poda_antiguedad.py`,
`filtrar.py` y `dedupe.py` ya han ido acumulando sus propios contadores en
`data/estadisticas_ejecucion.json` (ver `pipeline/estadisticas.py`) — nada que
hacer con ellos aparte de dejarlos correr. Falta cerrarlo con lo que sólo sabe
el agente:

1. Escribir un `agente.json` con lo que no está en ningún fichero del repo:

   ```json
   {
     "inicio": "<ISO del Paso 0>",
     "fin": "<ISO de ahora>",
     "fuentes_cubiertas": ["LinkedIn", "InfoJobs", "..."],
     "fuentes_omitidas": [{"fuente": "Indeed", "motivo": "captcha persistente"}],
     "fichas_completas_leidas": 0,
     "tokens_estimados": null,
     "correo_novedades": 0,
     "errores": []
   }
   ```

   `fichas_completas_leidas` cuenta sólo las veces que hizo falta el
   subcomando `leer` de `linkedin.py`/`infojobs.py` (leer la ficha entera; el
   atajo de `snippets` no cuenta). `tokens_estimados` es una estimación a ojo
   del gasto de la
   ejecución, o `null` si no se tiene ni idea — mejor sin cifra que una
   inventada.

2. `python pipeline/registrar_ejecucion.py --agente agente.json` — junta esto
   con los contadores acumulados y deja `out/historial.json`.
3. Subirlo con `write_db` (`db_op:"set"`, `collection:"historial"`,
   `doc_id:<fecha de hoy>`, `file_path`).

Esto es lo que permite, de aquí en adelante, decidir con datos si una fuente
merece la pena (`python pipeline/resumen_historial.py <volcado>`) en vez de
con una auditoría puntual del prompt — así se decidió lo de JSearch, sin tener
esto todavía.

## Paso 8 — Resumen del día

En pocas líneas: qué ventana se ha cubierto, si `ScraplingServer` ha estado
disponible y qué fuentes se han podido consultar y cuáles no (y por qué),
cuántas ofertas nuevas han entrado, cuáles son las mejores y por qué, cuántas
se han podado por antigüedad, qué novedades ha traído el correo, si hay
alguna entrevista que convenga meter en el calendario (proponerla, no
crearla — ver Paso 0 bis), y qué ha quedado pendiente.

Si el linter del CV (`pipeline/lint.py`, que pinta la pestaña «Tu CV») saca
algún `error`, decirlo: es la única pieza con efecto multiplicativo sobre
todas las candidaturas, no sólo una.

Si algún filtro de `config/filtros` parece estar costando ofertas buenas,
decirlo aquí y que decida Íñigo — la tarea nunca lo cambia por su cuenta.

## Si algo se rompe

- Sin shell o sin la herramienta Artifact: volcar la cosecha del día en
  `radar_<fecha>_ofertas_nuevas.json` con las ofertas sin deduplicar y una lista
  de pendientes. La siguiente ejecución sana lo ingiere.
- Ordenador apagado, sin la app de escritorio, o `ScraplingServer` sin
  responder: no pasa nada. Cubrir lo que no lo necesite
  (Tecnoempleo/Indeed/semanales), decir qué se ha quedado sin cubrir y **no
  escribir `config/estado_tarea`**, para que la ventana se ensanche sola al
  día siguiente.
- «GitHub access to this repository is not enabled»: el repo ha dejado de ser
  público. Sin eso la tarea no puede funcionar.
- Si se ha tocado código del repo durante la ejecución (poco habitual): commit
  y push con las herramientas de GitKraken sobre el clon local de Íñigo, y
  dejar el repo igual que lo publicado — si el dashboard publicado va por
  delante del `dashboard.py` del repo, la siguiente ejecución regenera desde
  el repo y se lleva por delante lo de en medio.
