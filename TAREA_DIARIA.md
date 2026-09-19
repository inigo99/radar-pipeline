# Tarea diaria — Radar de ofertas

Este fichero **es** el procedimiento de la tarea programada de las 10:00. El
prompt del trigger no lo repite: lo apunta (ver `docs/prompt_tarea.md`).

**Por qué aquí y no en el prompt.** El prompt era la pieza más larga y más
frágil del sistema y la única que vivía fuera de git: no se podía diffear, ni
revisar, ni revertir, y la regla «si cambia el procedimiento, cambia los dos»
no tenía forma de comprobarse — ya falló una vez, cuando el prompt seguía
mandando recalcular un Excel que llevaba días sin existir. Con el procedimiento
aquí, cambiarlo es un commit: se ve qué cambió, cuándo y por qué, y la
ejecución de mañana lee la versión nueva sola, porque clona el repo de todos
modos.

**Cómo se cambia el procedimiento:** se edita este fichero y se empuja el mismo
día. El prompt del trigger sólo se toca si cambia algo de fuera del repo (la
hora, el dispositivo, el sitio de los datos).

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

## Paso 0 — Configuración y ventana

Leer `config/filtros` y `config/estado_tarea`. La ventana de búsqueda va desde
`ultima_ejecucion` hasta ahora, con un mínimo de `ventana_horas`. `config/estado_tarea`
**sólo se escribe si la ejecución termina bien**: es lo que hace que un día
fallido no se salte ofertas.

<!-- PENDIENTE: pegar aquí el texto exacto del paso 0 del prompt vivo -->

## Paso 0 bis — Correo

<!-- PENDIENTE: pegar aquí el barrido de Gmail y la clasificación de `correo` -->

## Paso 1 — Datos de partida

1. `ArtifactData get collection:"pipeline" doc_id:"snapshot"` con `out_dir`.
2. `python pipeline/preparar_datos.py <volcado_snapshot> data`.
3. Si el snapshot falta o su `n_ofertas` no cuadra con la colección, volcado por
   colecciones y `preparar_datos.py` sobre él.

## Pasos 2-4 — Recogida por fuente

Diarias: LinkedIn, InfoJobs, JSearch, Tecnoempleo, Indeed, Manfred.
Semanales (lunes): Himalayas, WeWorkRemotely, RemoteOK.

Extractores en `browser/`, pegados como código con `javascript_tool` una vez por
dominio y ejecución. Todo lo que hay que saber de por qué se pegan y no se
cachean está en el README, sección `browser/`.

<!-- PENDIENTE: pegar aquí las consultas por fuente, el reparto entre el hilo
     principal y el subagente Sonnet, y los topes (JSearch: 6 consultas) -->

## Paso 5 — Filtrado y deduplicación

```bash
python pipeline/filtrar.py candidatas.json data/ok.json --filtros filtros.json
python pipeline/dedupe.py data/ok.json nuevas.json
```

Lo que aparta `filtrar.py` va a la colección `filtradas` con su motivo y su
detalle. Los duplicados también, con `motivo: "duplicada"`.

## Paso 6 — Fichas de las supervivientes

<!-- PENDIENTE: pegar aquí la redacción de `reqs`, `surfaced`, familia, titular
     y resumen, con la regla del resumen ≤ 240 caracteres y la lista de
     familias posibles -->

Recordatorios que sí están comprobados:

- `resumen` de `tailor` ≤ 240 caracteres.
- `anios_min` se anota, **no se descarta** por experiencia: eso lo decide el
  dashboard con los años del perfil, en el navegador.
- Nunca un campo `notas` en la oferta: choca con las notas que escribe Íñigo.
  Lo que sea un aviso va en `alerta`.
- `skills_extra` ya no hace falta rellenarlo a mano: `dashboard.py` lo deduce.

## Paso 7 — Pipeline y publicación

```bash
python pipeline/poda_antiguedad.py     # retira lo de +45 días sin seguimiento
python pipeline/puntuar.py             # -> data/resultado.json
python pipeline/embudo.py              # -> data/embudo.json  (NO es opcional)
mkdir -p out && python pipeline/dashboard.py
python pipeline/exportar_snapshot.py   # -> out/snapshot.json
```

Publicar `out/dashboard.html` **siempre en la misma URL del artifact**, con
`action:"read"` antes, **sin `capabilities`** (nunca `{}`: borrarlas se lleva
por delante el seguimiento y la generación de textos).

Subir `out/snapshot.json` a `pipeline/snapshot`, y sólo entonces escribir
`config/estado_tarea`.

## Paso 8 — Resumen del día

<!-- PENDIENTE: pegar aquí qué se resume y en qué orden -->

Si el linter del CV (`pipeline/lint.py`, que pinta la pestaña «Tu CV») saca
algún `error`, decirlo: es la única pieza con efecto multiplicativo.

## Si algo se rompe

- Sin shell o sin la herramienta Artifact: volcar la cosecha del día en
  `radar_<fecha>_ofertas_nuevas.json` con las ofertas sin deduplicar y una lista
  de pendientes. La siguiente ejecución sana lo ingiere.
- Ordenador apagado: no pasa nada. No se escribe `config/estado_tarea` y la
  ventana se ensancha sola al día siguiente.
- «GitHub access to this repository is not enabled»: el repo ha dejado de ser
  público. Sin eso la tarea no puede funcionar.
