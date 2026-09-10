# radar-pipeline

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
| `backfill_anios.py` | `data/` | rellena `anios_min` en las ofertas viejas leyendo sus alertas y notas (uno y no más) |
| `dedupe.py` | ofertas candidatas y lo ya conocido | las que de verdad son nuevas |
| `lint.py` | el perfil | las banderas rojas del CV base |
| `embudo.py` | estado, correo, resultado | `data/embudo.json`: conversión por fuente, familia y tramo |
| `dashboard.py` | resultado, perfil, tailor, filtradas, embudo | `out/dashboard.html`, la página completa |
| `exportar_snapshot.py` | todo `data/` | `out/snapshot.json`, que se sube a `pipeline/snapshot` |

`embudo.py` **no es opcional**: si no se ejecuta, `data/embudo.json` no existe y la
pestaña «Embudo» del dashboard sale vacía aunque haya candidaturas registradas.

`datos.py` es el único punto de carga; `ofertas.py`, `tailor.py`, `base_cv.py` y
`perfil.py` son envoltorios finos sobre él.

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
| `vocabulario.js` | diccionario término → regex para redactar los `reqs` |
| `bundle.min.js` | los tres primeros, concatenados y minificados |

### Cómo se cargan (y por qué no hay caché)

**Se pegan como código** en una llamada a `javascript_tool` al empezar con cada
dominio, y quedan en `window.__radar` para el resto de la sesión de esa pestaña.
Unos 10 KB, una vez por dominio y ejecución.

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

## La pestaña «Filtradas»

Las ofertas que caen por publicar un salario por debajo del mínimo ya no
desaparecen: van a la colección `filtradas` y se ven en el dashboard con su
motivo. El filtro de salario, tal cual estaba, penalizaba la transparencia —
descartaba a quien publica una cifra un poco baja y dejaba pasar a quien no
publica ninguna, con una estimación por encima del mínimo. Ahora se ve lo que
cuesta la configuración y se puede cambiar con conocimiento de causa.

## Deduplicación

La misma vacante llega con ids distintos desde portales distintos, y muchas
están en LinkedIn **y** en InfoJobs. `pipeline/dedupe.py` hace esa criba
siempre igual, en tres pasadas: por id, por huella de empresa y puesto
normalizados (sin acentos, sin `S.L.`, sin `(m/f/d)`) y por solape de tokens
del título dentro de la misma empresa.

**Nunca por subcadena.** Es la regla que impide que «Alan» case con «Talan» o
«UST» con «Braintrust». Comparar con `in` parece razonable diez minutos y luego
se come ofertas buenas en silencio.

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
| Formato | Que nombre a la empresa; que el correo empiece por asunto y lleve el marcador `[nombre]`. |

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
