# El prompt del trigger

Esto es lo que va en el prompt de la tarea programada, **entero**. El
procedimiento no se repite aquí: está en `TAREA_DIARIA.md`, dentro del repo,
que es lo que se puede diffear y revertir.

Actualizar el trigger con `update_trigger` sobre el id existente. **Nunca
borrar y recrear la tarea**: se pierden el historial y el vínculo con el
ordenador.

---

```
Actualiza el Radar de ofertas de Íñigo. Todo el estado vive en la base de
datos del artifact del dashboard y el código en un repo público. Esta tarea
corre con acceso al ordenador de Íñigo, así que tiene navegador.

Dashboard: https://claude.ai/code/artifact/ccb18000-2f48-4930-bb0d-f787ace9e7a7
Código:    https://github.com/inigo99/radar-pipeline

1. Clona el repositorio del pipeline:
   git clone --depth 1 https://github.com/inigo99/radar-pipeline
   cd radar-pipeline && mkdir -p data out

2. Lee TAREA_DIARIA.md, que está en la raíz del repo. Es el procedimiento
   completo del día y manda sobre cualquier recuerdo que tengas de cómo se
   hacía esto antes: si algo de lo que creas saber lo contradice, gana el
   fichero. Síguelo paso por paso, incluida la parte de navegador (a partir
   de "Antes de nada") y la instrumentación de coste del Paso 7.

3. Publica siempre en la MISMA URL del dashboard de arriba, con action:"read"
   antes y sin pasar el parámetro capabilities.

4. Al terminar, deja el resumen del día del Paso 8.
```

---

**Por qué tan corto.** Todo lo que se puede versionar, se versiona. En el
prompt sólo queda lo que no vive en el repo: dónde está el código, dónde está
el dashboard y qué se entrega al final — el resto (navegador, correo,
recogida, instrumentación...) es procedimiento y vive en `TAREA_DIARIA.md`. Un
cambio de procedimiento pasa a ser un push; `update_trigger` sólo hace falta
si cambia la hora, el dispositivo o el sitio de los datos.
