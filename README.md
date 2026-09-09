# radar-pipeline

Motor del **Radar de ofertas**: puntúa ofertas de empleo contra un CV real, genera
un CV adaptado por oferta y construye el dashboard.

**Este repositorio no contiene datos personales ni ofertas.** El código es lo único
que vive aquí. Las ofertas, el perfil, el CV y el seguimiento viven en la base de
datos del artifact del dashboard, y la tarea diaria los vuelca en `data/` antes de
ejecutar el pipeline. Por eso el repo puede ser público y clonarse sin credenciales.

## Cómo se ejecuta

```bash
git clone https://github.com/<usuario>/radar-pipeline
cd radar-pipeline
mkdir -p data out cv
# volcar la base de datos del artifact (read_db con out_dir) y montarla:
python pipeline/preparar_datos.py <directorio_del_volcado> data

# el pipeline se ejecuta SIEMPRE desde la raíz del repo: los scripts leen y
# escriben en data/, cv/ y out/ relativos al directorio de trabajo.
python pipeline/puntuar.py       # -> data/resultado.json
python pipeline/generar_docs.py  # -> cv/*.pdf y data/manifest.json  (playwright + pdfinfo)
python pipeline/dashboard.py     # -> out/dashboard.html
```

`RADAR_DATA` cambia el directorio de datos (por defecto `data`).

## Requisitos

Python 3.11+, `playwright` con Chromium y `pdfinfo` (poppler-utils).

## Qué hace cada script

| Script | Entrada | Salida |
|---|---|---|
| `preparar_datos.py` | volcado de la BD | los cuatro JSON de `data/` |
| `puntuar.py` | ofertas, perfil | `data/resultado.json` con la puntuación original y adaptada |
| `generar_docs.py` | resultado, perfil, tailor | un CV en PDF por oferta y `data/manifest.json` |
| `dashboard.py` | resultado, manifest, perfil, tailor | `out/dashboard.html`, la página completa |

`datos.py` es el único punto de carga; `ofertas.py`, `tailor.py`, `base_cv.py` y
`perfil.py` son envoltorios finos sobre él.

## El candado anti-invención

`perfil.prominencia_adaptada` es la regla que impide que el CV adaptado presuma de
algo que no está en el CV real. Un término con evidencia `0.0` **nunca** sube, haga
lo que haga el resto del pipeline. Cambiar eso convierte la herramienta en una
máquina de mentir en entrevistas: no se toca.

## Licencia

MIT.
