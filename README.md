# radar-pipeline

THIS IS MY PERSONAL VERSION OF JOBRADAR, FOR MY PERSONAL USE.

Motor del **Radar de ofertas**: puntúa ofertas de empleo contra un CV real y construye
el dashboard desde el que se trabajan.

**Este repositorio no contiene datos personales ni ofertas.** El código es lo único
que vive aquí. Las ofertas, el perfil, el CV y el seguimiento viven en la base de
datos del artifact del dashboard, y la tarea diaria los vuelca en `data/` antes de
ejecutar el pipeline. Por eso el repo puede ser público y clonarse sin credenciales.

## Cómo se ejecuta

```bash
git clone https://github.com/<usuario>/radar-pipeline
cd radar-pipeline
mkdir -p data out

# Camino rápido: un único documento `pipeline/snapshot` de la base de datos.
python pipeline/preparar_datos.py <volcado_del_snapshot> data

# Camino de respaldo, si el snapshot falta o se quedó atrás: volcado por
# colecciones (ofertas/, tailor/, perfil/base.json, pipeline/cerradas.json).
python pipeline/preparar_datos.py <volcado_por_colecciones> data

# el pipeline se ejecuta SIEMPRE desde la raíz del repo: los scripts leen y
# escriben en data/ y out/ relativos al directorio de trabajo.
python pipeline/puntuar.py            # -> data/resultado.json
python pipeline/embudo.py             # -> data/embudo.json
python pipeline/dashboard.py          # -> out/dashboard.html
python pipeline/exportar_snapshot.py  # -> out/snapshot.json, para mañana
```

`RADAR_DATA` cambia el directorio de datos (por defecto `data`).

## Requisitos

Python 3.11+. Nada más: el pipeline ya no genera PDF, así que no hacen falta
playwright ni poppler.

## Qué hace cada script

| Script | Entrada | Salida |
|---|---|---|
| `preparar_datos.py` | snapshot o volcado de la BD | los JSON de `data/` |
| `puntuar.py` | ofertas, perfil | `data/resultado.json` con la puntuación original, la adaptada y el foco |
| `foco.py` | una oferta y su prioridad | el orden «foco»: prioridad menos antigüedad y menos títulos de sénior |
| `experiencia.py` | el perfil y el texto de una oferta | los años que suma el CV y los que pide el anuncio |
| `dedupe.py` | ofertas candidatas y lo ya conocido | las que de verdad son nuevas |
| `lint.py` | el perfil | las banderas rojas del CV base |
| `embudo.py` | estado, correo, resultado | `data/embudo.json`: conversión por fuente, familia y tramo |
| `dashboard.py` | resultado, perfil, tailor, filtradas, embudo | `out/dashboard.html`, la página completa |
| `exportar_snapshot.py` | todo `data/` | `out/snapshot.json`, que se sube a `pipeline/snapshot` |

`tools/backfill_anios.py` rellenaba `anios_min` en las ofertas viejas leyendo
sus alertas y notas. Se ejecutó una vez, el 10-sep-2026, y vive en `tools/`
—no en `pipeline/`— para que nadie la encadene por error a la tarea diaria:
reescribe `data/ofertas.json` entero.

`embudo.py` **no es opcional**: si no se ejecuta, `data/embudo.json` no existe y la
pestaña «Embudo» del dashboard sale vacía aunque haya candidaturas registradas.

`dashboard.py` es sólo el ensamblaje: lee `pipeline/dashboard_template.html`
(el armazón HTML/CSS) y `pipeline/dashboard.js` (todo el JavaScript del lado
del cliente — puntuación, foco, CV, PDF, validadores...), sustituye el hueco
`__SCRIPT__` y rellena el resto de `__PLACEHOLDER__` con los datos del día.
Hasta el 19-sep-2026 ese JavaScript — casi 2500 líneas — vivía como una única
cadena Python de 174 KB dentro de `dashboard.py` (entonces 3092 líneas): el
fichero que más de una vez ha llegado corrompido en silencio al escribirlo en
el ordenador de Íñigo con `device_commit_files` (por eso conviene comprobar
el hash tras cada subida de un fichero grande, no sólo con éste). Cuanto más
grande y más ajeno a cualquier herramienta es un fichero, menos se nota cuando
algo lo daña. Con el JS aparte, `node --check pipeline/dashboard.js` lo
comprueba solo, sin generar la página, y editarlo no toca ni una línea de
Python.

`datos.py` es el único punto de carga; `ofertas.py`, `tailor.py`, `base_cv.py` y
`perfil.py` son envoltorios finos sobre él.

## La tarea diaria

El procedimiento de la tarea programada de las 10:00 está en
[`TAREA_DIARIA.md`](TAREA_DIARIA.md), en este repo. El prompt del trigger no lo
repite: lo apunta (ver [`docs/prompt_tarea.md`](docs/prompt_tarea.md)). Así un
cambio de procedimiento es un commit que se puede leer, revisar y revertir, en
vez de un texto que sólo existe dentro del trigger.

## Pruebas

```bash
python tests/smoke.py          # el pipeline entero sobre una fixture sintética
python tests/test_dedupe.py    # deduplicación: hashes truncados, huella, poda vetada
python tests/test_lint.py      # las 18 reglas del linter del CV
npm install                    # jsdom (test de paridad) y terser (build del bundle)
```

El repo no tiene datos, así que hasta ahora no había forma de probarlo sin la
base de datos del artifact delante. `tests/fixture.py` reproduce el **esquema**
—cuatro ofertas elegidas para tocar los caminos que se han roto alguna vez, un
perfil mínimo pero completo— y `tests/smoke.py` ejecuta encima el pipeline
completo, el round-trip del snapshot, la poda, el filtrado, `node --check`
sobre el `<script>` de la página y que el `bundle.min.js` sea exactamente lo
que produce `node tools/build_bundle.js` sobre las fuentes actuales (no sólo
que no falte ninguna función por nombre, que es lo que había hasta el
19-sep-2026 y no detectaba un bundle desactualizado si cambiaba el cuerpo de
una función sin cambiar su nombre).

`tests/paridad.mjs` es el que se gana el sitio: la misma aritmética vive dos
veces —en Python, que es lo que corre la tarea, y portada a JavaScript dentro
de `dashboard.py`, para el botón «+ Oferta» y el orden de la página— y las
constantes se inyectan pero la lógica está escrita dos veces. El test carga la
página con jsdom y llama a sus funciones con los mismos datos con los que corrió
el pipeline. En su primera ejecución encontró que `diasDesde()` daba un día de
más a partir del mediodía, que es media ventana de frescura de diferencia; el
19-sep-2026 se le añadió una comprobación de `cvBloques()` (el generador real
del CV en PDF) después de encontrar que `orden[familia]` llevaba tiempo con una
forma que no era la que `dashboard.py` espera -- ver `pipeline/lint.py`.

`dedupe.py` y `lint.py` no tenían ningún test hasta el 19-sep-2026, a pesar de
ser dos de las piezas con más historial de bugs reales del repo (dedupe: hash
de InfoJobs truncado, "Banco Santander" vs "Grupo Santander"; lint: ocho de
sus dieciocho reglas llevaban rompiéndose en silencio -- ver la cabecera de
`pipeline/lint.py`).

Todo esto corre en cada push (`.github/workflows/ci.yml`). Importa porque la
tarea diaria clona `master` a ciegas: lo que esté roto en master se descubre de
otro modo a las 10:00 de la mañana siguiente, en una ejecución que nadie mira.

## El snapshot

`pipeline/snapshot` es **caché, no fuente de verdad**. Las colecciones `ofertas`,
`tailor`, `estado` y `correo` siguen mandando, porque el dashboard escribe
directamente en ellas cuando se cambia una fase o se descarta una oferta. El
snapshot existe sólo para que arrancar el pipeline cueste una llamada en vez de
volcar ~460 documentos, cuyo *listado* se comía unos 11 000 tokens de contexto
cada mañana.

Lleva `generado` y `n_ofertas` justamente para poder desconfiar de él: si el
recuento no cuadra con la colección, se ignora, se vuelve al volcado por
colecciones y se regenera al final de la ejecución.

## `browser/`: los extractores de los portales

LinkedIn e InfoJobs no se dejan leer con WebFetch ni por HTTP directo. Hay que
usar un navegador y hacer `fetch` desde una pestaña del propio dominio, y ahí el
coste está en el HTML que se descarga y se tira. Estos ficheros son ese trabajo
ya resuelto, para no volver a derivarlo —ni a romperlo— cada mañana:

| Fichero | Qué trae |
|---|---|
| `common.js` | normalización, HTML a texto, clasificación de modalidad y ámbito, filtro de títulos, tandas con pausa y reintento de `429` |
| `linkedin.js` | endpoint de invitado, parseo por `<li>`, criba y fichas |
| `infojobs.js` | listado por regex sobre el HTML crudo, recorte de la descripción, fichas |
| `manfred.js` | API JSON pública de Manfred: salario, `remotePercentage` y técnicas con nivel ya estructurados, sin parseo de HTML |
| `vocabulario.js` | diccionario término → regex para redactar los `reqs`, sin leer la ficha entera |
| `bundle.min.js` | los tres primeros (común + LinkedIn + InfoJobs), concatenados y minificados |

`bundle.min.js` se genera con `node tools/build_bundle.js` (necesita
`npm install`, que instala `terser`). **No se edita a mano ni se regenera con
otro comando**: `tests/smoke.py` reconstruye el bundle con este mismo script y
compara bytes contra el commiteado, así que un bundle generado de otra forma
(u olvidado de regenerar tras tocar una fuente) hace fallar el test.

**Manfred no necesita subagente.** Como usa una API JSON en vez de HTML, no
tiene el coste que justifica pegar código en una pestaña sólo por LinkedIn e
InfoJobs — pero sí necesita el navegador (el proxy de salida de la nube
bloquea `getmanfred.com` igual que bloquea el resto), así que va en el hilo
principal, nunca en el subagente de Tecnoempleo/Indeed: ese subagente no
tiene navegador y Manfred se queda sin cubrir si se le delega ahí (pasó el
16-sep-2026).

### Cómo se cargan (y por qué no hay caché)

**Se pegan como código** en una llamada a `javascript_tool` al empezar con cada
dominio, y quedan en `window.__radar` para el resto de la sesión de esa pestaña.
Unos 10 KB, una vez por dominio y ejecución. Para LinkedIn e InfoJobs, carga
también `vocabulario.js` desde el principio (junto con `common.js` y
`linkedin.js`/`infojobs.js`): desde el 16-sep-2026 `detallar()` saca los
términos del vocabulario en la misma pasada que la modalidad, así que cada
ficha se pide una sola vez en toda la ejecución — antes se pedía dos, una para
filtrar (paso 4) y otra para escribir los `reqs` (paso 6), literalmente el
mismo HTML descargado dos veces.

Ese segundo ahorro no se aprovechaba del todo: el paso 6 seguía volcando la
ficha entera al contexto para redactar los `reqs`, aunque ya no hiciera falta
un segundo `fetch` para conseguirla — sólo se ahorraba la descarga, no la
lectura. Desde el 16-sep-2026, `li.snippets(id)` / `ij.snippets(hash)`
devuelven, de una sola oferta, los términos con más apariciones junto con un
fragmento corto (~110 caracteres) de dónde aparece cada uno por primera vez
— lo justo para decidir el peso («imprescindible» pesa más que «se
valorará») y copiar la etiqueta en las palabras del anuncio, sin las
900-1.200 caracteres de `li.leer()`/`ij.leer()`. Estas dos funciones quedan
como último recurso: cuando la lista de términos sale corta o rara, o para
redactar el `resumen` de `tailor`. Para **Manfred** no hace falta ni eso:
`o.reqs` ya sale de `detallar()` con el formato exacto de `vocabulario.md`
(`[clave, peso, etiqueta]`), calculado a partir del nivel y la sección de
cada técnica (`MAPA_TECH`/`WEIGHT` en `manfred.js`) — se copia tal cual.

Se probaron tres atajos el 9 de septiembre de 2026 y **los tres fallan en
linkedin.com**; no vuelvas a intentarlos:

| Atajo | Qué pasa |
|---|---|
| `fetch` a `raw.githubusercontent` | Bloqueado: `connect-src` de la CSP. |
| `<script src>` desde jsDelivr | Bloqueado: `script-src-elem` con nonce y `strict-dynamic`. |
| Cachear en `localStorage` y `eval` | LinkedIn **parchea** `localStorage` (`Storage.prototype.setItem` ya no es nativo): `setItem` no lanza pero no guarda nada. Y aunque guardara, `eval` y `new Function` están bloqueados por CSP (`unsafe-eval` no está permitido). IndexedDB sí escribe, pero sigue haciendo falta `eval` para ejecutar lo leído, así que tampoco sirve. |

El código que inyecta `javascript_tool` no pasa por la CSP porque entra por CDP,
no por el parser de la página. Por eso pegar funciona y todo lo demás no.

Los ficheros están troceados en sentencias independientes (`;void function(e){…}`)
para poder pegarlos en varias llamadas: la entrada y la salida de las
herramientas de navegador se cortan sobre los 1.200 caracteres. Unir los trozos
con `;` + `function(e){` da SyntaxError; hay que dejar el `void`.

### Dos trampas que ya costaron una tanda entera de `fetch`

- La detección de modalidad **tiene que incluir `\b remote \b` y `\b remoto \b`
  a secas** (sin los espacios). Una primera versión sólo buscaba «100% remoto»,
  «teletrabajo», «remote work»… y se dejó fuera *«This is a remote position»*,
  que es la forma más común en inglés: 24 ofertas de 80 descartadas en silencio.
- En InfoJobs hay que **recortar la descripción antes de contar términos**:
  sobre el HTML completo, `\.net` casa con «infojobs.net» y da 45 apariciones de
  C#/.NET en todas las ofertas.

## Modalidad: `remoto_sin_confirmar`

La etiqueta «remoto» de los portales miente a menudo, así que la modalidad se
decide con la frase literal de la descripción. Pero cuando el portal la marca
remota y la descripción **no dice nada que lo contradiga**, tirarla es peor que
quedársela: la oferta entra marcada como `remoto_sin_confirmar`, con una alerta
para preguntarlo en el primer contacto. Un descarte silencioso no se puede
auditar; una alerta, sí.

## Qué modalidades se buscan: `buscar_remoto`/`buscar_hibrido`/`buscar_presencial`

Hasta el 16-sep-2026 esto era un único interruptor (`solo_remoto`) que, en la
práctica, no hacía nada: `li.clasificar()`, `ij.clasificar()` y `mf.filtrar()`
tenían el remoto/local/`remoto_sin_confirmar` **fijo en el código**, así que
poner `solo_remoto` a `false` en el dashboard no cambiaba nada — híbrido y
presencial (fuera de las zonas locales) nunca llegaban a `candidatas`, los
descartara quien los descartara.

Ahora hay tres campos independientes en `config/filtros` —
`buscar_remoto`, `buscar_hibrido`, `buscar_presencial` — y los tres extractores
reciben la configuración en vez de tenerla escrita a fuego:

    li.clasificar(CFG)
    ij.clasificar(CFG)
    mf.filtrar(idsConocidos, desde, CFG)

`R.modalidadesAceptadas(cfg)` (en `common.js`) es la única fuente de verdad
sobre qué `modalidad.tipo` pasa el filtro. `local` (las zonas de
`areas_locales`, Navarra/Gipuzkoa por defecto) entra **siempre**, gane o
pierda cualquiera de los otros tres campos: es una excepción por zona, no una
modalidad más. Sin argumento (o con los tres campos a `undefined`), la
función se comporta como el valor por defecto del dashboard — sólo remoto —
para que un extractor viejo o un olvido no abra la puerta de golpe.

**Manfred distingue híbrido de presencial mejor que LinkedIn o InfoJobs**,
porque no depende de una frase suelta en la descripción: `remotePercentage`
ya lo dice con un número (100 = remoto, 0 = presencial, lo de en medio =
híbrido). Antes de este cambio, todo lo que no fuera 100 % remoto o local
caía en un «fuera» sin más detalle, así que `buscar_hibrido`/
`buscar_presencial` no tenían ningún efecto sobre Manfred aunque se activaran.

## La pestaña «Filtradas»

Las ofertas que caen por publicar un salario por debajo del mínimo ya no
desaparecen: van a la colección `filtradas` y se ven en el dashboard con su
motivo. El filtro de salario, tal cual estaba, penalizaba la transparencia —
descartaba a quien publica una cifra un poco baja y dejaba pasar a quien no
publica ninguna, con una estimación por encima del mínimo. Ahora se ve lo que
cuesta la configuración y se puede cambiar con conocimiento de causa.

## Filtrado de configuración

Hasta el 16-sep-2026, `excluir_keywords`, `excluir_empresas`, `salario_min`
y `exigir_salario_publicado` se aplicaban a ojo sobre las candidatas. Aparte
del tiempo, dejaba un hueco real: `li.filtrar()` sí aplicaba
`excluir_empresas`, pero `ij.filtrar()` y `mf.filtrar()` nunca lo hicieron —
una intermediaria vetada que llegara por InfoJobs, Manfred o el subagente de
Tecnoempleo/Indeed sólo se caía si alguien la pillaba a tiempo. Ahora
`pipeline/filtrar.py` aplica esas cuatro reglas en código, igual para las
candidatas de cualquier fuente, entre el paso 4 y `dedupe.py`:

    python pipeline/filtrar.py candidatas.json data/ok.json --filtros filtros.json

Sólo esas cuatro — **modalidad y `ambitos` siguen sin tocarse aquí, a
propósito, pero por motivos distintos**. La modalidad ya se decide en el
navegador con la configuración de verdad (`buscar_remoto`/`buscar_hibrido`/
`buscar_presencial`, ver más arriba): filtrarla otra vez en Python sería
repetir un trabajo ya hecho, no tapar un hueco. Y `ambitos` necesita saber si
la frase que encuentra `R.ambito()` es una restricción o una apertura —
gramaticalmente son iguales, así que decidirlo a ciegas es inventarse un
criterio y arriesgarse a tirar una oferta buena, justo lo que avisa
`pipeline/vocabulario.md`. Eso sigue necesitando que alguien lea la frase.

## Deduplicación

La misma vacante llega con ids distintos desde portales distintos, y muchas
están en LinkedIn **y** en InfoJobs. `pipeline/dedupe.py` hace esa criba
siempre igual, en cuatro pasadas: por id (tolerando el hash truncado de
InfoJobs), por URL cuando la candidata la trae, por huella de empresa y
puesto normalizados (sin acentos, sin `S.L.`, sin `Banco`/`Grupo`, sin
`(m/f/d)`) y por solape de tokens del título dentro de la misma empresa.

**Nunca por subcadena.** Es la regla que impide que «Alan» case con «Talan» o
«UST» con «Braintrust». Comparar con `in` parece razonable diez minutos y luego
se come ofertas buenas en silencio.

**El id de InfoJobs se truncó a longitudes distintas según el día** (8
caracteres unas veces, 10 otras), y una comparación exacta dejó pasar una
oferta de Sopra Steria que ya estaba, dos veces, con dos ids del mismo hash
(16-sep-2026). El paso 1 ahora compara los ids `ij-*` por prefijo compartido
en vez de por igualdad, así que el bug no depende de que nadie vuelva a
truncar bien — pero al escribir un id nuevo en el paso 6, usa siempre
`ij.idPara(o)` (`browser/infojobs.js`), que fija la longitud en 12
caracteres, para no depender de esa tolerancia. La misma ejecución coló
«Grupo Santander» junto a «Banco Santander» como si fueran dos empresas: por
eso `Banco` está ahora en `SUFIJOS_SOCIEDAD`.

    python pipeline/dedupe.py candidatas.json nuevas.json   # criba un lote
    python pipeline/dedupe.py --auditar                     # duplicados ya dentro

`preparar_datos.py` pasa la auditoría al terminar y **avisa** si encuentra
duplicados en el radar, pero no borra: una de las dos copias puede tener
seguimiento, notas o documentos, y el script no sabe cuál conservar.

Los duplicados apartados al entrar se anotan en la colección `filtradas` con
`motivo: "duplicada"`, así que salen en el recuento de la pestaña «Filtradas»
como cualquier otro filtro. Ver cuánta ingesta llega duplicada es la mitad de
la razón para medirlo.

## El linter del CV base

`pipeline/lint.py` es la única pieza que no mira ofertas: mira el perfil. Es
también la única con efecto multiplicativo, porque arreglar un logro sin cifra
mejora todas las candidaturas a la vez.

    python pipeline/lint.py            # informe por consola
    python pipeline/lint.py --json

`dashboard.py` lo importa y lo pinta en la pestaña «Tu CV», así que no hay un
paso más en la tarea diaria ni un fichero más en `data/`: si se genera la
página, el informe está hecho.

Reglas en tres niveles: cronología rota o un puesto sin fechas son `error`;
huecos de más de cinco meses, logros sin cifra, lenguaje de funciones y frases
de relleno son `aviso`; tiempos verbales mezclados o demasiados bullets en un
puesto son `info`. **Ninguna regla cultural**: si un CV lleva foto o fecha de
nacimiento depende del país, y penalizar a un CV alemán por seguir la
convención alemana es peor que no revisar nada.

Dos reglas son propias de este sistema y no salen en ningún manual:
`evidencia-sin-demostrar` avisa cuando un término marcado con evidencia 1,0 ya
no aparece en ningún logro —el bullet que lo argumentaba se reescribió y la
puntuación sigue contándolo—, y `techo-imposible` avisa cuando el techo
promete más de lo que la evidencia permite. Las dos existen para que el candado
de `perfil.py` siga apoyándose en datos verdaderos.

## Las preguntas de los formularios

Casi ninguna candidatura se queda en «adjunta tu CV». Hay tres o cuatro campos
de texto libre —por qué nosotros, un proyecto del que estés orgulloso,
pretensión salarial— que se acaban respondiendo a las once de la noche y suenan
a plantilla, o peor, prometen algo que no está en el CV.

Dentro de cada oferta, la pestaña **«Respuestas»** es un chat: pegas la pregunta
tal y como viene del formulario y sale respondida con el perfil real, el
contexto de esa oferta y el mismo perfil de voz que la carta. Si no encaja se lo
dices en el mismo hilo —«más corto», «menos formal», «en inglés»— en vez de
regenerar desde cero. El hilo se guarda en `docs/<id>`, junto a la carta y el
correo.

Tres cosas lo separan de la carta:

| | |
|---|---|
| **El límite manda** | Los formularios cortan a 500 caracteres o a 150 palabras sin avisar. El límite se fija por oferta, entra en el prompt y el contador está a la vista, en rojo cuando se pasa. |
| **El banco** | Las preguntas se repiten entre empresas. Una respuesta que te gusta se guarda en la colección `respuestas`, y la siguiente vez que alguien pregunte algo parecido entra en el contexto como precedente: se adapta, no se reescribe de cero. El parecido se mide por solape de palabras, quitando las que salen en toda pregunta («cuéntanos», «por qué», «describe»), y nunca contra la propia oferta. |
| **Pasa por el validador** | Una respuesta de formulario es justo donde más fácil se cuela una cifra inventada, así que se revisa igual que la carta. La única comprobación que se salta es la de nombrar a la empresa: media docena de preguntas no van de ellos. |

Dos reglas propias de este modo, además de las de siempre: es un **campo de
formulario**, así que no lleva saludo, despedida ni firma; y si piden una cifra
o una fecha que no está en el perfil —pretensión salarial, disponibilidad—
**no se la inventa**: deja un `[pendiente: …]` para que lo rellenes tú. Si la
oferta publica banda, puede referirse a ella.

El banco vive sólo en la base de datos y en la página: el pipeline no lo lee ni
lo escribe, así que no hay nada nuevo que volcar en la tarea diaria.

## El validador de la carta y el correo

El candado protege el CV, pero la carta y el correo salían del modelo directos
a la pantalla: los sostenía sólo el prompt, y un prompt se cumple casi siempre,
que no es lo mismo que siempre. `validaTexto()`, dentro de `dashboard.py`,
es ese «casi»: compara el texto ya escrito con el perfil real y con la oferta.

| Comprobación | Qué caza |
|---|---|
| Cifras | Un número que no está ni en tu CV ni en la oferta. Los modelos redondean el 38 % al 40 %, y esa es la cifra por la que preguntan en la entrevista. |
| Tecnología | Un término con evidencia 0 nombrado en el texto. |
| Años | «5 años» dicho como propio cuando el CV suma 3,2. |
| Estilo | Las fórmulas prohibidas en tus propias reglas: «sinergia», «no dudes en», «Estimado/a»… |
| Formato | Que nombre a la empresa (salvo en las respuestas de formulario), y que el correo empiece por asunto y lleve el marcador `[nombre]`. |

**No bloquea nada, señala.** Nombrar un hueco es correcto —es lo que pide el
prompt— y citar la banda de la oferta también, así que la decisión sigue siendo
de quien envía. Se ejecuta al generar y al volver a abrir un texto guardado,
para que los borradores anteriores pasen también por aquí.

## Bandas salariales

`pipeline/bandas.json` es la tabla de referencia para estimar cuando la oferta
no publica cifra: familia × tipo de empresa, un factor por país de contratación
y unos pocos ajustes. No es ciencia, pero hace que dos ofertas parecidas salgan
con la misma banda y que la cifra se pueda discutir, en lugar de reinventarse
cada mañana.

El país que manda es **dónde te contratan**, no dónde está la sede: una empresa
alemana que contrata en España paga banda española. La tabla de divisas es
orientativa a propósito, y el fichero lo dice: si la cifra convertida cae a
menos de un 10 % del mínimo, hay que buscar el tipo del día antes de apartar la
oferta. Un descarte por un tipo de cambio viejo es justo el que no se puede
defender.

## Los documentos se generan bajo demanda, en la página

El pipeline **no** genera un CV por oferta. Antes lo hacía (`generar_docs.py`, con
Chromium), y el resultado eran 200 PDF incrustados en el HTML: 15 MB de página para
que se descargasen tres o cuatro. Ahora cada oferta lleva en el dashboard un botón
que arma su CV en el momento, en el navegador, y lo mismo hacen la cover letter y el
correo a RRHH.

El CV lo construye `pdfCV()` dentro de `dashboard.py`: un escritor de PDF 1.4 en
JavaScript, sin librerías —la CSP del artifact casi no deja cargar nada de fuera—,
con las fuentes base-14 (Times y Helvetica en `WinAnsiEncoding`) y sus tablas de
anchos incrustadas para partir y justificar líneas. Reproduce el CV que hacía
Chromium: mismo contenido, mismo orden y una sola página, bajando el cuerpo de letra
hasta que cabe.

Lo que se imprime sale de `perfil/base` (bullets reales, competencias, formación) y
de `tailor/<id>` (familia, titular y resumen adaptados). El botón no inventa nada:
sólo reordena y maqueta lo que ya está.

## El candado anti-invención

`perfil.prominencia_adaptada` es la regla que impide que el CV adaptado presuma de
algo que no está en el CV real. Un término con evidencia `0.0` **nunca** sube, haga
lo que haga el resto del pipeline. Cambiar eso convierte la herramienta en una
máquina de mentir en entrevistas: no se toca.

`pipeline/vocabulario.md` fija las claves de `reqs` y la escala de pesos. Una clave
inventada cuenta como evidencia 0 y hunde la puntuación de la oferta sin motivo
real, así que conviene usar las que ya están.

## Licencia

MIT.
