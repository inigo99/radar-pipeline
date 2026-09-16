/* Extractor de Manfred. Requiere common.js y una pestaña en getmanfred.com
 * (CORS). Añadido el 16-sep-2026, cuando Manfred pasó de ser un subagente sin
 * navegador -y por tanto sin cobertura real- a tener su propio script: hay
 * que hacerlo en el hilo principal, igual que LinkedIn/InfoJobs/JSearch,
 * porque el navegador es una sola instancia.
 *
 * A diferencia de LinkedIn e InfoJobs, aquí NO hace falta parsear HTML ni
 * adivinar modalidad por regex: el listado es una API JSON con salario,
 * `remotePercentage` y ubicación ya estructurados, y la ficha trae las
 * técnicas exigidas con su nivel («BASIC»/«INTERMEDIATE»/«ADVANCED») y su
 * sección («MUST»/«COULD»/«EXTRA») — mejor señal que cualquier conteo de
 * palabras sobre la descripción.
 *
 * Flujo típico de una ejecución:
 *   await __radar.mf.buscar()
 *   __radar.mf.filtrar(IDS_CONOCIDOS, '2026-09-11T09:15:00Z')
 *   await __radar.mf.detallar(10)
 *   __radar.saca(6)
 *
 * OJO con la fecha: Manfred sólo da `updatedAt` (última actualización), no
 * fecha de publicación. Para una oferta nunca vista antes es lo mismo, pero
 * si algún día se compara contra una ya conocida, `updatedAt` puede estar
 * más adelantada que la publicación real — no es una mentira del portal
 * como la etiqueta de remoto de LinkedIn, es sólo un campo distinto al que
 * hace falta.
 */
(function (R) {
  const mf = R.mf = {};
  mf.version = 'manfred-2026-09-16';
  mf.ofertas = {};   // id -> ficha del listado
  mf.det = [];        // fichas con técnicas ya extraídas
  mf.cola = [];        // pendientes de detallar

  const BASE = 'https://www.getmanfred.com/api/v2/public/offers';
  const QS = 'lang=ES&onlyActive=true&currency=' + encodeURIComponent('€');
  const QS_DETALLE = 'lang=ES&currency=' + encodeURIComponent('€');

  /* Nombres de técnica de Manfred -> clave de pipeline/vocabulario.md. Sólo
   * se listan las que tienen equivalente real: una técnica sin mapear se
   * descarta en vez de inventarse una clave nueva, porque una clave nueva
   * vale 0 en evidencia_orig y hundiría la oferta sin motivo (ver «Trampas
   * conocidas» de vocabulario.js). Si una técnica se repite mucho sin
   * mapear, es más fácil añadirla aquí que en mitad de una ejecución. */
  mf.MAPA_TECH = {
    'python': 'python', 'java': 'java', 'javascript': 'javascript', 'typescript': 'typescript',
    'c#': 'csharp', '.net': 'csharp', 'go': 'golang', 'golang': 'golang', 'scala': 'scala',
    'c++': 'c_cpp', 'php': 'php', 'react': 'react', 'react native': 'react', 'next.js': 'react',
    'angular': 'angular', 'vue': 'vuejs', 'vue.js': 'vuejs', 'node.js': 'nodejs', 'nodejs': 'nodejs',
    'nestjs': 'nodejs', 'express': 'nodejs', 'spring': 'springboot', 'spring boot': 'springboot',
    'fastapi': 'fastapi', 'django': 'django', 'flask': 'django',
    'api': 'apis_rest', 'rest': 'apis_rest', 'graphql': 'apis_rest',
    'microservicios': 'microservicios', 'microservices': 'microservicios',
    'aws': 'aws', 'azure': 'azure', 'azure cosmosdb': 'cloud_datos', 'gcp': 'gcp', 'google cloud': 'gcp',
    'docker': 'docker', 'kubernetes': 'kubernetes', 'k8s': 'kubernetes',
    'ci/cd': 'cicd', 'jenkins': 'cicd', 'github actions': 'cicd',
    'terraform': 'terraform', 'ansible': 'ansible', 'linux': 'linux', 'git': 'git',
    'sql': 'sql', 'postgresql': 'sql', 'postgres': 'sql', 'mysql': 'sql', 'sql server': 'sql',
    'nosql': 'sql', 'mongodb': 'sql', 'dynamodb': 'sql',
    'kafka': 'kafka', 'spark': 'spark', 'pyspark': 'spark', 'databricks': 'databricks',
    'snowflake': 'snowflake', 'airflow': 'airflow', 'dbt': 'airflow',
    'mlops': 'mlops', 'mlflow': 'mlflow', 'llm': 'llm', 'llms': 'llm',
    'genai': 'genai', 'generative ai': 'genai', 'langchain': 'langchain',
    'pytorch': 'pytorch_tf', 'tensorflow': 'pytorch_tf', 'scikit-learn': 'sklearn',
    'nlp': 'nlp', 'computer vision': 'computer_vision', 'opencv': 'opencv',
  };
  const WEIGHT = {
    MUST: { ADVANCED: 10, INTERMEDIATE: 8, BASIC: 7 },
    COULD: { ADVANCED: 6, INTERMEDIATE: 5, BASIC: 4 },
    EXTRA: { ADVANCED: 4, INTERMEDIATE: 3, BASIC: 2 },
  };

  const _stripHtml = h => (h || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

  /* Manfred no tiene búsqueda por palabra clave en el listado público: trae
   * todas las activas de golpe (típicamente 15-30, es un portal boutique),
   * y se filtra en el cliente igual que con InfoJobs. Una sola llamada. */
  mf.buscar = async () => {
    const r = await R.pide(BASE + '?' + QS);
    const lista = await r.json();
    for (const o of lista) mf.ofertas[String(o.id)] = o;
    return 'TOTAL=' + Object.keys(mf.ofertas).length;
  };

  mf.RE_LOCAL_MF = R.RE_LOCAL;   // alias, por claridad en clasificarModalidad

  /* La modalidad no hace falta adivinarla por regex: remotePercentage ya lo
   * dice. 100 = remoto; si no, se cuenta como local sólo cuando alguna
   * ubicación cae en Navarra/Gipuzkoa; cualquier otro caso (híbrido o
   * presencial fuera de esas provincias) se descarta aquí, como con las
   * demás fuentes. */
  mf._modalidad = o => {
    const ciudades = (o.locations || []).map(l => R.norm(l.city || l.town || '')).join(' ');
    if (Number(o.remotePercentage) >= 100) return 'remoto';
    if (R.RE_LOCAL.test(ciudades)) return 'local';
    return 'fuera';
  };

  /* Criba por título, por fecha (updatedAt) y contra lo ya conocido. */
  mf.filtrar = (idsConocidos, desde) => {
    const conocidos = new Set((idsConocidos || []).map(String));
    mf.cola = Object.values(mf.ofertas).filter(o => {
      const id = 'mf-' + o.slug;
      if (conocidos.has(id)) return false;
      if (desde && o.updatedAt && o.updatedAt < desde) return false;
      if (!R.tituloVale(o.position)) return false;
      const tipo = mf._modalidad(o);
      if (tipo !== 'remoto' && tipo !== 'local') return false;
      o._tipo = tipo;
      return true;
    });
    return { candidatas: Object.keys(mf.ofertas).length, sobreviven: mf.cola.length };
  };

  /* Pide la ficha completa sólo de lo que sobrevivió al filtro: técnicas con
   * nivel y sección, idiomas, y el texto de «lo que piden» para sacar años
   * si los dice. Nunca se lee la ficha entera a ojo — se cuenta y se
   * clasifica en código, igual que las demás fuentes. */
  mf.detallar = async (n) => {
    const lote = mf.cola.splice(0, n || 10);
    await R.enTandas(lote, async o => {
      const r = await R.pide(BASE + '/' + o.id + '?' + QS_DETALLE);
      const j = await r.json();
      const ask = _stripHtml(j.whatTheyAskFor);
      const reqs = (j.techs || [])
        .map(t => {
          const clave = mf.MAPA_TECH[R.norm(t.name)];
          if (!clave) return null;
          const w = (WEIGHT[t.section] || {})[t.level] || 5;
          return [clave, w, t.name];
        })
        .filter(Boolean)
        .sort((a, b) => b[1] - a[1]);
      Object.assign(o, {
        reqs,
        idiomas: (j.languages || []).map(l => l.name + ':' + l.level).join(','),
        anios: R.anios(R.norm(ask)),
        _ask: ask,
        _resp: _stripHtml(j.responsibilities || j.whatWillYouDo || ''),
      });
      mf.det.push(o);
    }, 300);
    return 'detalladas=' + mf.det.length + ' pendientes=' + mf.cola.length;
  };

  /* La modalidad y el título ya se cribaron en filtrar(); esto sólo da
   * formato a la fila de salida, igual que li.clasificar()/ij.clasificar(). */
  mf.clasificar = () => {
    const fila = o => ['mf-' + o.slug, (o.company || {}).name || '', o.position,
                       (o.locations || []).map(l => l.city).join('/') || 'remoto',
                       (o.updatedAt || '').slice(0, 10), o._tipo,
                       (o.salaryFrom ? o.salaryFrom + '-' : 'hasta ') + o.salaryTo + '€',
                       o.anios || '-',
                       (o.reqs || []).slice(0, 4).map(x => x[2]).join(',')].join('|');
    R.cola = mf.det.map(fila);
    return { total: mf.det.length };
  };

  /* Texto de «lo que piden» + responsabilidades, para redactar los `reqs`
   * definitivos de una oferta ya aceptada (la única excepción a no leer
   * ficha completa, como en las demás fuentes). */
  mf.leer = (id, chars) => {
    const o = mf.det.find(x => ('mf-' + x.slug) === id || String(x.id) === String(id));
    if (!o) return 'no encontrada (¿detallada?)';
    return (o._ask + ' ' + o._resp).slice(0, chars || 900);
  };
})(window.__radar);
