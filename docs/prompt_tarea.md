# El prompt del trigger

Esto es lo que va en el prompt de la tarea programada, **entero**. El
procedimiento no se repite aquí: está en `TAREA_DIARIA.md`, dentro del repo,
que es lo que se puede diffear y revertir.

Actualizar el trigger con `update_trigger` sobre el id existente. **Nunca
borrar y recrear la tarea**: se pierden el historial y el vínculo con el
ordenador.

---

```
Radar de ofertas — actualización diaria.

1. Clona el repositorio del pipeline:
   git clone --depth 1 https://github.com/<usuario>/radar-pipeline
   cd radar-pipeline && mkdir -p data out

2. Lee TAREA_DIARIA.md, que está en la raíz del repo. Es el procedimiento
   completo del día y manda sobre cualquier recuerdo que tengas de cómo se
   hacía esto antes: si algo de lo que creas saber lo contradice, gana el
   fichero. Síguelo paso por paso.

3. Trabaja con navegador (Claude en Chrome primero, en una pestaña nueva, sin
   tocar las suyas; si su Chrome no responde, el navegador integrado de la app
   de escritorio con preview_start).

4. Al terminar, deja el resumen del día del paso 8.
```

---

**Por qué tan corto.** Todo lo que se puede versionar, se versiona. En el
prompt sólo queda lo que no vive en el repo: dónde está el código, con qué
navegador se trabaja y qué se entrega. Un cambio de procedimiento pasa a ser un
push; `update_trigger` sólo hace falta si cambia la hora, el dispositivo o el
sitio de los datos.
