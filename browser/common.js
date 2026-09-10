/* Utilidades comunes de extracción para el Radar de ofertas.
 *
 * SE PEGA COMO CÓDIGO en una llamada a `javascript_tool`, al empezar con cada
 * dominio. No se puede cargar de ninguna otra forma en linkedin.com: la CSP
 * bloquea el `fetch` a githubusercontent (connect-src), la inyección de
 * <script> desde jsDelivr (script-src-elem con nonce y strict-dynamic) y
 * `eval`/`new Function` (falta unsafe-eval). Además LinkedIn parchea
 * `localStorage`, así que cachearlo ahí tampoco vale: setItem no guarda nada.
 * Lo que sí pasa es el código que inyecta la herramienta, porque entra por CDP
 * y no por el parser de la página. Ver el README.
 *
 * Todo cuelga de window.__radar para no ensuciar la página. Nada de esto
 * escribe en el portal: sólo lee.
 */
window.__radar = window.__radar || {};
(function (R) {
  R.version = 'common-2026-09-09';

  R.sleep = ms => new Promise(r => setTimeout(r, ms));

  /* Minúsculas y sin acentos. Todos los regex de abajo asumen texto ya normalizado. */
  R.norm = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  /* HTML -> texto plano conservando los saltos de bloque, que es donde viven
   * las frases de modalidad («100% remoto.» suele ir sola en su propio <li>). */
  R.texto = html => html
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<\/(p|li|div|h\d|tr)>/gi, '. ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ')
    .replace(/&aacute;/g, 'á').replace(/&eacute;/g, 'é').replace(/&iacute;/g, 'í')
    .replace(/&oacute;/g, 'ó').replace(/&uacute;/g, 'ú').replace(/&ntilde;/g, 'ñ')
    .replace(/&#\d+;/g, '')
    .replace(/\s+/g, ' ')
    .trim();

  /* ---- Modalidad -------------------------------------------------------
   * OJO: la primera versión de esto se dejó fuera «remote» y «remoto» a secas
   * y perdió 24 ofertas de 80 en un solo día, porque la forma más común en
   * inglés es «This is a remote position». No quitar los \b...\b sueltos.
   */
  R.RE_REMOTO = /(100\s*%?\s*remot|fully remote|full[- ]remote|remote[- ]first|totalmente remot|completamente remot|en remoto|teletrabajo|trabajo remot|remote work|work from home|work remotely|\bremote\b|\bremoto\b|\bremota\b)/;
  R.RE_HIBRIDO = /(hibrid|hybrid|\d\s*d[ií]as? (en|de) (oficina|casa)|days (in|at) the office)/;
  R.RE_PRESENCIAL = /(presencial|on-?site|onsite|en la oficina|nuestras oficinas|not remote|no remote)/;
  R.RE_LOCAL = /(navarr|pamplona|iruña|gipuzkoa|guipuzcoa|san sebasti|donostia|irun|tudela|mutilva|noain|estella|zarautz|tolosa)/;

  /* Devuelve hasta `max` frases con contexto donde el texto habla de modalidad.
   * Se devuelven las frases, no un veredicto: quien decide es quien lee. */
  R.frasesModalidad = (textoNorm, max) => {
    const re = new RegExp(R.RE_REMOTO.source + '|' + R.RE_HIBRIDO.source + '|' + R.RE_PRESENCIAL.source, 'g');
    const out = []; let m;
    while ((m = re.exec(textoNorm)) && out.length < (max || 3))
      out.push(textoNorm.slice(Math.max(0, m.index - 55), m.index + 80).replace(/\s+/g, ' '));
    return out;
  };

  /* Clasifica la modalidad a partir de las frases y de la etiqueta del portal.
   * `etiquetaRemoto` es lo que dice el listado, que miente a menudo.
   *
   * Devuelve: remoto | hibrido | presencial | local | remoto_sin_confirmar | desconocida
   *
   * `remoto_sin_confirmar` es el caso importante: el portal la marca remota y
   * la descripción no dice nada que lo contradiga. Antes se descartaban en
   * silencio; ahora entran con alerta para que él lo pregunte. */
  R.modalidad = (textoNorm, ubicacionNorm, etiquetaRemoto) => {
    const frases = R.frasesModalidad(textoNorm, 3);
    const enFrases = re => frases.some(f => re.test(f));
    const rem = enFrases(R.RE_REMOTO), hib = enFrases(R.RE_HIBRIDO), pre = enFrases(R.RE_PRESENCIAL);
    let tipo;
    if (rem && !hib && !pre) tipo = 'remoto';
    else if (rem && (hib || pre)) tipo = 'hibrido';       // «remoto» como ventaja suelta, no como modalidad
    else if (hib) tipo = 'hibrido';
    else if (pre) tipo = 'presencial';
    else if (etiquetaRemoto) tipo = 'remoto_sin_confirmar';
    else tipo = 'desconocida';
    if (R.RE_LOCAL.test(ubicacionNorm || '') && tipo !== 'remoto') tipo = 'local';
    return { tipo, frases };
  };

  /* ---- Ámbito ----------------------------------------------------------
   * ¿Se puede firmar el contrato residiendo en España? */
  R.ambito = textoNorm => {
    const restr = textoNorm.match(/(must be (located|based|resident)[^.]{0,70}|eligible to work[^.]{0,70}|authorized to work[^.]{0,70}|residir en[^.]{0,60}|imprescindible residir[^.]{0,60}|only accepting[^.]{0,60}|anywhere in the world|within the eu|across emea)/);
    const menciona = /\b(spain|espana|españa|eu\b|european union|emea|europe)\b/.test(textoNorm);
    return { restriccion: restr ? restr[0] : '', menciona_espana_o_ue: menciona };
  };

  /* ---- Salario y experiencia ------------------------------------------- */
  R.salario = texto => {
    const m = texto.match(/(\d{2}[.,]\d{3}\s*[-–a]{1,3}\s*\d{2}[.,]\d{3}\s*€?|\d{2}[.,]?\d{3}\s*€|€\s*\d{2}[.,]?\d{3}|\$\s?\d{2,3}[,.]?\d{0,3}\s*[kK]?\s*[-–]\s*\$?\s?\d{2,3}[,.]?\d{0,3}\s*[kK]?|\d{2,3}\s?k\s*[-–]\s*\d{2,3}\s?k)/);
    return m ? m[0].trim() : '';
  };
  R.anios = textoNorm => {
    const m = textoNorm.match(/(\d+\s*\+?\s*(?:-\s*\d+\s*)?(?:anos|años|years|year)\b|al menos \d+[^,.]{0,20}|m[aá]s de \d+ a[nñ]os)/);
    return m ? m[0].trim() : '';
  };

  /* ---- Filtro de títulos ----------------------------------------------
   * Lo que evita el 80 % del trabajo: nunca se pide una ficha sin pasar esto. */
  R.RE_TITULO_OK = /(ai engineer|a\.i\. engineer|artificial intelligence|inteligencia artificial|machine learning|ml engineer|ai\/ml|ai \/ ml|genai|gen ai|generative ai|\bllm\b|nlp engineer|computer vision|vision por comput|data scientist|cientific[oa] de datos|data engineer|ingenier[oa][\/ ]*a? de datos|full[- ]?stack|backend|back[- ]end|software engineer|ingenier[oa] de software|python developer|python engineer|desarrollador python|mlops|applied scientist|research engineer|forward deployed)/;
  R.RE_TITULO_NO = /(manager|director|head of|jefe|responsable|arquitect|architect|consultor|consultant|analyst|analista|devops|\bsre\b|site reliability|sysadmin|\bqa\b|tester|becari|internship|\bintern\b|practicas|sales|comercial|ventas|recruit|profesor|docente|teacher|product owner|project manager|scrum|marketing|designer|disenador|frontend|front-end|support|soporte|helpdesk|tecnico de sistemas|administrativ|prompt engineer|trainer)/;
  R.tituloVale = titulo => {
    const t = R.norm(titulo);
    return R.RE_TITULO_OK.test(t) && !R.RE_TITULO_NO.test(t);
  };

  /* ---- Paginación de resultados ---------------------------------------
   * La salida de javascript_tool se corta sobre los 1.200 caracteres, así que
   * nada se devuelve entero: se guarda y se saca a trocitos. */
  R.cola = [];
  R.pon = filas => { R.cola = R.cola.concat(filas); return 'en cola: ' + R.cola.length; };
  R.saca = n => R.cola.splice(0, n || 6).join('\n');

  /* Tandas cortas con pausa: por encima de ~45 s la llamada CDP da timeout. */
  R.enTandas = async (items, fn, pausa) => {
    const out = [];
    for (const it of items) {
      try { out.push(await fn(it)); } catch (e) { out.push({ error: String(e).slice(0, 60), item: it }); }
      await R.sleep(pausa || 230);
    }
    return out;
  };

  /* Un 429 no es una oferta cerrada: se reintenta una vez. */
  R.pide = async (url, opts) => {
    let r = await fetch(url, opts || { credentials: 'omit' });
    if (r.status === 429) { await R.sleep(2600); r = await fetch(url, opts || { credentials: 'omit' }); }
    return r;
  };
})(window.__radar);
