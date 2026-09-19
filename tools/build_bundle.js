// Reconstruye browser/bundle.min.js a partir de common.js + linkedin.js +
// infojobs.js. Antes del 19-sep-2026 esto se hacía a mano con terser y nada
// en el repo garantizaba que el bundle commiteado siguiera correspondiendo a
// las fuentes: el único chequeo (tests/smoke.py) sólo comprobaba que el
// NOMBRE de cada función apareciera como subcadena en el bundle, lo que no
// detecta un bundle desactualizado si alguien cambia el CUERPO de una función
// sin cambiar su nombre.
//
// Ahora este script es la única forma soportada de generar el bundle, y
// tests/smoke.py lo ejecuta a un fichero temporal y compara bytes contra el
// que está commiteado: si no coinciden, alguien tocó una fuente y no
// regeneró el bundle (o tocó el bundle a mano).
//
//   node tools/build_bundle.js                    # -> browser/bundle.min.js
//   node tools/build_bundle.js /tmp/salida.js      # a otra ruta, para comparar
//
// Requiere `terser` (`npm install terser --no-save`, o ya en package.json).
import { minify } from 'terser';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const BROWSER = path.join(RAIZ, 'browser');

// Orden importa: common.js inicializa `window.__radar` y las demás cuelgan
// de él. vocabulario.js y manfred.js NO van en el bundle: se pegan por su
// cuenta (ver TAREA_DIARIA.md, paso de recogida por fuente).
const FUENTES = ['common.js', 'linkedin.js', 'infojobs.js'];

async function main() {
  const destino = process.argv[2] || path.join(BROWSER, 'bundle.min.js');
  const codigo = {};
  for (const f of FUENTES) {
    codigo[f] = fs.readFileSync(path.join(BROWSER, f), 'utf-8');
  }

  const resultado = await minify(codigo, {
    compress: true,
    mangle: true,
    format: { comments: false },
  });
  if (resultado.error) throw resultado.error;

  fs.mkdirSync(path.dirname(destino), { recursive: true });
  fs.writeFileSync(destino, resultado.code, 'utf-8');
  console.log(`bundle -> ${destino} (${resultado.code.length} bytes, de ${FUENTES.join(' + ')})`);
}

main().catch((e) => { console.error(e); process.exit(1); });
