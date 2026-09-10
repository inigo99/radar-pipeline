# Prioridad por familia y brecha de aprendizaje

Creado el 10 sep 2026. Íñigo quiere reorientar la búsqueda hacia Data Science e
IA, manteniendo Full Stack/Backend en el radar pero con menos peso, y quiere
que cada oferta le diga qué podría aprender razonablemente entre mandar la
candidatura y una posible entrevista. El código vive en `pipeline/aprendizaje.py`
y se consume desde `puntuar.py` (que calcula `prioridad` y `brecha` por oferta)
y desde `dashboard.py` (que los pinta). **No toca el CV ni la carta**: el
candado anti-invención de [[redaccion-cv-cartas]] sigue intacto, esto es sólo
información para él.

## Prioridad por familia (`PESO_FAMILIA`)

Un multiplicador sobre `score_adap` que **sólo decide el orden inicial** de la
tabla del dashboard, nunca la nota de encaje que se muestra (esa sigue siendo
honesta y sin ponderar). Las familias de IA/Data Science (`genai`, `ml`, `cv`,
`ds`) pesan más, `mlops`/`research` un poco más, y `backend` un poco menos.
Íñigo puede seguir ordenando por «CV adaptado» en cualquier momento para ver
el encaje puro sin el empujón.

Si dentro de unos meses ya no hace falta el empujón hacia IA/Data Science, o si
decide sacar Full Stack/Backend del radar del todo, esto se ajusta aquí y en
`config/filtros` (los `titulos` de búsqueda), no hace falta tocar nada más.

## Dificultad de aprendizaje (`DIFICULTAD`)

Para cada requisito de una oferta que es un hueco real (`evidencia_orig == 0`),
clasifica si merece la pena repasarlo antes de una posible entrevista:

- **rapido** — días a una semana: una librería, framework o herramienta sobre
  una base que ya tiene.
- **medio** — varias semanas de dedicación real para hablar de ello con
  criterio, no sólo de oídas.
- **lento** — no es realista cubrirlo bien en el plazo de un proceso de
  selección: una disciplina profunda (CUDA, cuantización…), una certificación
  pesada, una titulación, un idioma nuevo o años de experiencia. Aquí la nota
  no sugiere estudiar, sugiere preparar una respuesta honesta — igual que ya
  hacía el panel de huecos antes de esto.

**Esto no decide si algo es un hueco** (eso lo sigue haciendo `perfil.py`,
comparando contra la evidencia real). Sólo clasifica huecos que ya existen.

## Cómo mantenerla

- Las claves son las mismas de `vocabulario.md` (pipeline/vocabulario.md). Si
  aparece una clave nueva ahí, añádela aquí también con criterio; si no, cae
  en el nivel por defecto (`medio`, con una nota genérica) y no rompe nada,
  pero tampoco ayuda mucho.
- Juzga por lo que **razonablemente** puede aprender él en ese tiempo, no por
  lo que sería ideal. Si dudas entre `rapido` y `medio`, o entre `medio` y
  `lento`, pregúntale — igual que con los pesos de `reqs`.
- No mezcles esto con el candado del CV: aunque algo sea "rapido" de aprender,
  eso **no** lo mete en el CV ni en la carta hasta que de verdad lo aprenda.
  Es información para decidir en qué invertir el tiempo entre la candidatura y
  la entrevista, nada más.
