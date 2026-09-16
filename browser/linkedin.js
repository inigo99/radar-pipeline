/* Extractor de LinkedIn. Requiere common.js y una pestaña en linkedin.com (CORS).
 *
 * Flujo típico de una ejecución:
 *   await __radar.li.buscar(TITULOS, {remoto:true, location:'Spain'})
 *   await __radar.li.buscar(TITULOS, {location:'Navarre, Spain'})
 *   __radar.li.filtrar(IDS_CONOCIDOS, '2026-09-08')      // por título y fecha
 *   await __radar.li.detallar(20)                        // en tandas
 *   __radar.li.clasificar(); __radar.saca(6)             // sólo lo que sobrevive
 *
 * Carga también vocabulario.js ANTES de detallar(): desde el 16-sep-2026
 * detallar() saca los términos del vocabulario en la misma pasada que la
 * modalidad, para no volver a pedir la misma ficha dos veces (una para
 * filtrar, otra para escribir los `reqs` del paso 6). Si vocabulario.js no
 * está cargado, detallar() sigue funcionando igual, sólo que sin `j.terminos`
 * — li.terminos() cae entonces a calcularlo sobre `_tn` como hacía antes. */
(function (R) {
  const li = R.li = {};
  li.version = 'linkedin-2026-09-16';
  li.jobs = {};        // id -> ficha del listado
  li.det = [];         // fichas con descripción ya procesada
  li.cola = [];        // pendientes de detallar

  const GUEST = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?';
  const FICHA = 'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/';

  /* El HTML del endpoint de invitado NO se puede parsear con DOMParser desde
   * linkedin.com: devuelve 0 nodos. Hay que partir por <li> y sacar los campos
   * con regex sobre el HTML crudo. */
  li.parsear = (html, etiqueta) => {
    let n = 0;
    for (const trozo of html.split('<li')) {
      const id = (trozo.match(/data-entity-urn="urn:li:jobPosting:(\d+)"/) || [])[1];
      if (!id || li.jobs[id]) continue;
      const limpia = s => s ? R.texto(s) : '';
      li.jobs[id] = {
        id,
        titulo: limpia((trozo.match(/<h3[^>]*base-search-card__title[^>]*>([\s\S]*?)<\/h3>/) || [])[1]),
        empresa: limpia((trozo.match(/hidden-nested-link[^>]*>([\s\S]*?)<\/a>/) || [])[1]),
        ubicacion: limpia((trozo.match(/job-search-card__location[^>]*>([\s\S]*?)<\/span>/) || [])[1]),
        fecha: (trozo.match(/datetime="([\d-]+)"/) || [])[1] || '',
        q: etiqueta,
      };
      n++;
    }
    return n;
  };

  /* opts: {remoto, location, horas (por defecto 24), paginas} */
  li.buscar = async (titulos, opts) => {
    opts = opts || {};
    const horas = opts.horas || 24;
    const paginas = opts.paginas || 2;
    const consultas = [];
    for (const t of titulos)
      for (let p = 0; p < paginas; p++)
        consultas.push({
          etiqueta: (opts.remoto ? 'R' : 'L') + (p ? '2' : '') + '|' + t,
          qs: 'keywords=' + encodeURIComponent(t)
            + '&location=' + encodeURIComponent(opts.location || 'Spain')
            + '&f_TPR=r' + (horas * 3600)
            + (opts.remoto ? '&f_WT=2' : '')
            + '&start=' + (p * 10),
        });
    const res = await R.enTandas(consultas, async c => {
      const r = await R.pide(GUEST + c.qs);
      return c.etiqueta + ':' + r.status + ':+' + li.parsear(await r.text(), c.etiqueta);
    }, 220);
    return res.join(' ') + ' TOTAL=' + Object.keys(li.jobs).length;
  };

  /* Criba por título, por fecha y contra los ids que ya están en la base.
   * Es lo que baja de ~150 candidatas a ~20 fichas que merezca la pena pedir. */
  li.filtrar = (idsConocidos, desde, excluirEmpresas) => {
    const conocidos = new Set((idsConocidos || []).map(String));
    const malas = (excluirEmpresas || []).map(R.norm).filter(Boolean);
    li.cola = Object.values(li.jobs).filter(j => {
      if (conocidos.has(j.id)) return false;
      if (desde && j.fecha && j.fecha < desde) return false;
      if (!R.tituloVale(j.titulo)) return false;
      const e = R.norm(j.empresa);
      if (malas.some(m => e === m || (m.length > 4 && e.includes(m)))) return false;
      return true;
    });
    return { candidatas: Object.keys(li.jobs).length, sobreviven: li.cola.length };
  };

  /* Calcula los hits de vocabulario sobre texto ya normalizado. Compartida
   * con terminos() para no repetir la cuenta si ya está en j.terminos.
   *
   * Cada hit lleva un fragmento corto (~110 caracteres) alrededor de la
   * PRIMERA aparición del término: no para contar, sino para que al escribir
   * `reqs` en el paso 6 se pueda poner el peso («imprescindible» pesa más que
   * «se valorará») sin leer la ficha entera — ver snippets() más abajo, y el
   * porqué en la cabecera de vocabulario.js. */
  const _cuentaTerminos = (tn, dicc) => {
    const D = dicc || R.DICC;
    if (!D || !tn) return null;
    const hits = [];
    for (const k in D) {
      const re = D[k];
      const m = tn.match(new RegExp(re, 'g'));
      if (!m) continue;
      const idx = tn.search(new RegExp(re));
      const frag = idx >= 0 ? tn.slice(Math.max(0, idx - 40), idx + 70).replace(/\s+/g, ' ').trim() : '';
      hits.push([k, m.length, frag]);
    }
    hits.sort((a, b) => b[1] - a[1]);
    return hits;
  };

  /* Descarga la descripción y saca sólo los campos que importan: modalidad,
   * ámbito, salario, años y —si vocabulario.js está cargado— los términos
   * del vocabulario, todo de la misma lectura. Nunca get_page_text ni
   * read_page sobre una ficha: son miles de tokens. */
  li.detallar = async (n) => {
    const lote = li.cola.splice(0, n || 20);
    await R.enTandas(lote, async j => {
      const r = await R.pide(FICHA + j.id);
      if (r.status === 404) { j.cerrada = true; li.det.push(j); return; }
      const txt = R.texto(await r.text());
      const tn = R.norm(txt);
      const etiquetaRemoto = /^R/.test(j.q || '');
      Object.assign(j, {
        modalidad: R.modalidad(tn, R.norm(j.ubicacion), etiquetaRemoto),
        ambito: R.ambito(tn),
        salario: R.salario(txt),
        anios: R.anios(tn),
        largo: txt.length,
        terminos: _cuentaTerminos(tn),   // null si no hay vocabulario.js cargado
      });
      j._tn = tn;   // se guarda para leer() y para terminos() si hace falta recalcular
      li.det.push(j);
    }, 230);
    return 'detalladas=' + li.det.length + ' pendientes=' + li.cola.length;
  };

  /* Reparte en las tres cestas y deja las buenas en la cola de salida. */
  li.clasificar = (areasLocales) => {
    const dentro = [], fuera = [], revisar = [];
    for (const j of li.det) {
      if (j.cerrada) { fuera.push(j); continue; }
      const t = j.modalidad.tipo;
      if (t === 'remoto' || t === 'local') dentro.push(j);
      else if (t === 'remoto_sin_confirmar') revisar.push(j);
      else fuera.push(j);
    }
    const fila = j => [j.id, j.empresa, j.titulo, j.ubicacion, j.fecha,
                       j.modalidad.tipo, j.salario || '-', j.anios || '-',
                       (j.ambito.restriccion || '').slice(0, 60),
                       (j.modalidad.frases[0] || '').slice(0, 90)].join('|');
    R.cola = dentro.concat(revisar).map(fila);
    return { dentro: dentro.length, revisar: revisar.length, fuera: fuera.length };
  };

  /* Descripción completa de una oferta ya aceptada. Antes era la única forma
   * de escribir sus `reqs`; desde el 16-sep-2026 usa snippets() en su lugar
   * para eso (ver más abajo) y esto queda como último recurso, para cuando
   * la lista de términos salga corta o rara, o para redactar `resumen`.
   * Sale a trozos porque la salida se corta sobre los 1.200 caracteres. */
  li.leer = (id, desde, chars) => {
    const j = li.det.find(x => x.id === String(id));
    if (!j || !j._tn) return 'no encontrada (¿detallada?)';
    return j._tn.slice(desde || 0, (desde || 0) + (chars || 900));
  };

  /* Alternativa barata: sólo el vocabulario técnico, contado sobre la
   * descripción. Usa lo que detallar() ya calculó (j.terminos); si esa
   * oferta se detalló antes de cargar vocabulario.js, lo calcula ahora
   * sobre _tn con el diccionario que se le pase (o R.DICC). */
  li.terminos = (ids, dicc) => li.det
    .filter(j => !ids || ids.includes(j.id))
    .map(j => {
      const hits = j.terminos || _cuentaTerminos(j._tn, dicc) || [];
      return j.id + '|' + hits.slice(0, 22).map(h => h[0] + ':' + h[1]).join(',');
    });

  /* Lo que hace falta para escribir los `reqs` del paso 6 SIN leer la ficha
   * entera: los `maxTerms` términos con más apariciones, cada uno con un
   * trozo corto de dónde aparece por primera vez, para poner el peso y la
   * etiqueta con la frase real del anuncio. Una sola oferta por llamada
   * (las 4-5 que sobreviven al día), así que cabe de sobra en los ~1.200
   * caracteres de salida. Si sale vacío o insuficiente, cae a li.leer(). */
  li.snippets = (id, maxTerms) => {
    const j = li.det.find(x => x.id === String(id));
    if (!j) return 'no encontrada (¿detallada?)';
    const hits = j.terminos || _cuentaTerminos(j._tn) || [];
    if (!hits.length) return '(sin términos de vocabulario.js — usa li.leer())';
    return hits.slice(0, maxTerms || 10)
      .map(h => `${h[0]} (${h[1]}x): "${h[2] || ''}"`)
      .join('\n');
  };
})(window.__radar);
