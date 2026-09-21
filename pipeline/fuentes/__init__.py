"""Extracción y clasificación de ofertas por fuente (LinkedIn, InfoJobs, Manfred).

Hasta el 21-sep-2026 esto vivía en `browser/*.js` y se pegaba como código en
una pestaña de Chrome (ver el commit anterior a este para el porqué: CSP de
LinkedIn, límite de 1.200 caracteres de `javascript_tool`, etc.). Desde el
21-sep-2026 la recogida usa Scrapling (`ScraplingServer`, MCP local en el
dispositivo, con `real_chrome:true`): no inyecta código en la página, así que
ni la CSP ni el límite de caracteres ni el requisito de "pestaña del mismo
dominio" por CORS aplican. Scrapling hace SOLO la petición HTTP/navegación;
todo el análisis (parsear el listado, decidir modalidad, contar vocabulario)
vive aquí, en Python, en vez de en JS inyectado.

La lógica de cada función es una traducción fiel de la versión JS que
sustituye — mismos regex, mismos comentarios sobre bugs históricos ya
corregidos (ver cada módulo) — no una reescritura desde cero. El objetivo era
cambiar DÓNDE corre el código, no reinventar CÓMO decide.
"""
