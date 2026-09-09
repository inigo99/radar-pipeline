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
# volcar la base de datos del artifact (read_db con out_dir) y montarla:
python pipeline/preparar_datos.py <directorio_del_volcado> data

# el pipeline se ejecuta SIEMPRE desde la raíz del repo: los scripts leen y
# escriben en data/ y out/ relativos al directorio de trabajo.
python pipeline/puntuar.py     # -> data/resultado.json
python pipeline/dashboard.py   # -> out/dashboard.html
```

`RADAR_DATA` cambia el directorio de datos (por defecto `data`).

## Requisitos

Python 3.11+. Nada más: el pipeline ya no genera PDF, así que no hacen falta
playwright ni poppler.

## Qué hace cada script

| Script | Entrada | Salida |
|---|---|---|
| `preparar_datos.py` | volcado de la BD | los cuatro JSON de `data/` |
| `puntuar.py` | ofertas, perfil | `data/resultado.json` con la puntuación original y adaptada |
| `dashboard.py` | resultado, perfil, tailor | `out/dashboard.html`, la página completa |

`datos.py` es el único punto de carga; `ofertas.py`, `tailor.py`, `base_cv.py` y
`perfil.py` son envoltorios finos sobre él.

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

## Licencia

MIT.
