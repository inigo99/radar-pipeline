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
# volcar desde la base de datos del artifact a data/:
#   ofertas.json    <- colección `ofertas`      (lista)
#   tailor.json     <- colección `tailor`       ({id: {...}})
#   perfil.json     <- documento `perfil/base`
#   cerradas.json   <- documento `pipeline/cerradas`
cd pipeline
python puntuar.py          # -> data/resultado.json
python generar_docs.py     # -> cv/*.pdf y data/manifest.json   (playwright + pdfinfo)
python excel.py            # -> out/ofertas.xlsx
python dashboard.py        # -> out/dashboard.html
```

`RADAR_DATA` cambia el directorio de datos (por defecto `data`).
`RADAR_XLSX` cambia la ruta del Excel (por defecto `out/ofertas.xlsx`).

## Requisitos

Python 3.11+, `playwright` con Chromium, `pdfinfo` (poppler-utils) y `openpyxl`.

## Qué hace cada script

| Script | Entrada | Salida |
|---|---|---|
| `puntuar.py` | ofertas, perfil | `data/resultado.json` con la puntuación original y adaptada |
| `generar_docs.py` | resultado, perfil, tailor | un CV en PDF por oferta y `data/manifest.json` |
| `excel.py` | resultado, tailor, manifest | hoja de cálculo con todas las ofertas |
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
