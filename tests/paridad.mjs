/* Paridad Python <-> JavaScript.
 *
 * La misma aritmética vive dos veces: en `pipeline/puntuar.py`, `perfil.py`,
 * `foco.py` y `aprendizaje.py` (que es lo que corre la tarea diaria) y en
 * `dashboard.py`, portada a JS para que el botón «+ Oferta» y el orden de la
 * página no dependan de una ejecución del pipeline. Las CONSTANTES se inyectan
 * desde el propio repo, así que ésas no divergen. La LÓGICA está escrita dos
 * veces, y eso sí diverge: basta con arreglar un redondeo en un lado.
 *
 * Esto carga la página generada con jsdom y llama a sus funciones con los
 * mismos datos con los que corrió el pipeline. Si los números no coinciden,
 * falla y dice cuál.
 *
 *     node tests/paridad.mjs <out/dashboard.html> <data/>
 */
import fs from 'node:fs';
import path from 'node:path';
import { JSDOM } from 'jsdom';

const [htmlPath, dataDir] = process.argv.slice(2);
if (!htmlPath || !dataDir) {
  console.error('uso: node tests/paridad.mjs <dashboard.html> <data/>');
  process.exit(2);
}

const leer = (f) => JSON.parse(fs.readFileSync(path.join(dataDir, f), 'utf-8'));
const ofertas = leer('ofertas.json');
const resultado = leer('resultado.json');

const dom = new JSDOM(fs.readFileSync(htmlPath, 'utf-8'), {
  runScripts: 'dangerously',
  url: 'https://localhost/',
  virtualConsole: new (await import('jsdom')).VirtualConsole(),  // silencio
});
const { window } = dom;

/* Las variables de nivel superior del script se declaran con let/const, así que
 * NO cuelgan de window: hay que leerlas con un eval indirecto, que comparte el
 * ámbito léxico del script de la página. Las `function foo(){}` sí cuelgan. */
const ev = (expr) => window.eval(expr);

let fallos = 0;
const igual = (a, b, que) => {
  const ok = a === b || (typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) < 0.051);
  console.log(`  ${ok ? 'ok  ' : 'FALLA'} ${que}${ok ? '' : `  (python=${a} js=${b})`}`);
  if (!ok) fallos++;
};

console.log('paridad: puntuación');
for (const o of ofertas) {
  const r = resultado.find((x) => x.id === o.id);
  if (!r) continue;
  const p = ev(`puntuarOferta(${JSON.stringify(o.reqs)}, ${JSON.stringify(o.surfaced || [])})`);
  igual(r.score_orig, p.scoreOrig, `${o.id} score_orig`);
  igual(r.score_adap, p.scoreAdap, `${o.id} score_adap`);
}

console.log('paridad: peso de familia y foco');
for (const r of resultado) {
  const peso = ev(`pesoFamilia(${JSON.stringify(r.familia)})`);
  const prioridad = Math.round(r.score_adap * peso * 10) / 10;
  igual(r.prioridad, prioridad, `${r.id} prioridad`);
  const fc = ev(`calculaFoco(${JSON.stringify(r.puesto)}, ${JSON.stringify(r.publicada)}, ` +
                `${JSON.stringify(r.sal_origen)}, ${prioridad})`);
  igual(r.foco, fc.foco, `${r.id} foco`);
  igual(r.dias, fc.dias, `${r.id} días desde la publicación`);
}

console.log('paridad: candado anti-invención');
for (const o of ofertas) {
  for (const [clave] of o.reqs) {
    const js = ev(`prominenciaAdaptada(${JSON.stringify(clave)}, new Set(${JSON.stringify(o.surfaced || [])}))`);
    const evid = ev(`EVIDENCIA`)[clave] || 0;
    if (evid === 0) igual(0, js, `${clave}: evidencia 0 nunca sube`);
  }
}

console.log('paridad: limpieza del titular');
for (const t of ['Senior AI Engineer', 'Sr. Data Scientist', 'Sénior Backend', 'AI Engineer']) {
  const js = ev(`limpiaTitular(${JSON.stringify(t)})`);
  const esperado = t.replace(/\b(senior|sénior|sr\.?)\b/gi, '').replace(/\s+/g, ' ').trim();
  igual(esperado.toLowerCase(), String(js).toLowerCase(), `limpiaTitular(${t})`);
}

/* El foco que pinta la página tiene que ser el recalculado hoy, no el que venía
 * horneado: si alguien quita refrescaFoco(), esto lo nota. */
console.log('paridad: la página recalcula el foco al cargar');
const dataPagina = ev('DATA');
for (const r of dataPagina) {
  const fc = ev(`calculaFoco(${JSON.stringify(r.puesto)}, ${JSON.stringify(r.publicada)}, ` +
                `${JSON.stringify(r.salOrigen)}, ${r.prioridad})`);
  igual(fc.foco, r.foco, `${r.id} foco de DATA recalculado`);
}

console.log('paridad: cvBloques() no revienta y orden[familia] tiene la forma que espera');
for (const r of resultado.slice(0, 3)) {
  try {
    const bloques = ev(`cvBloques(${JSON.stringify(r)}, 9.7)`);
    const oo = ev(`CV.orden['${r.familia}'] ? CV.orden['${r.familia}'][0] : CV.orden.backend[0]`);
    const vv = ev(`CV.orden['${r.familia}'] ? CV.orden['${r.familia}'][1] : CV.orden.backend[1]`);
    igual(true, Array.isArray(bloques) && bloques.length > 0, `${r.id} cvBloques() devuelve bloques`);
    igual(true, Array.isArray(oo) && Array.isArray(vv),
          `${r.id} CV.orden[familia] son dos listas de claves (bug del 19-sep-2026: `
          + `si alguna vuelve a ser una clave suelta en vez de una lista, oo.map()/vv.map() `
          + `revientan al generar el CV real)`);
  } catch (e) {
    igual('sin excepción', `excepción: ${e.message}`, `${r.id} cvBloques()`);
  }
}

console.log(fallos ? `\n${fallos} divergencia(s)` : '\nsin divergencias');
process.exit(fallos ? 1 : 0);
