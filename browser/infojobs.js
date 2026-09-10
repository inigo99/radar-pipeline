/* Extractor de InfoJobs. Requiere common.js y una pestaña en infojobs.net (CORS).
 *
 *   await __radar.ij.buscar(['machine learning','full stack'], {remoto:true})
 *   await __radar.ij.buscar(['desarrollador','datos'], {provincia:'31'})   // Navarra
 *   __radar.ij.filtrar(HASHES_CONOCIDOS)
 *   await __radar.ij.detallar(10); __radar.saca(5)
 *
 * Si aparece el muro de cookies en pantalla: «Rechazar y cerrar», nunca
 * «Aceptar». Estos fetch no lo disparan.
 */
(function (R) {
  const ij = R.ij = {};
  ij.version = 'infojobs-2026-09-09';
  ij.ofertas = {};   // hash -> {hash, ciudad, slug}
  ij.det = [];
  ij.cola = [];

  const BUSCAR = 'https://www.infojobs.net/jobsearch/search-results/list.xhtml?';
  /* El listado SSR sólo pinta 5 anclas, pero el HTML crudo lleva ~21 URLs. */
  const RE_URL = /\/\/www\.infojobs\.net\/([a-z0-9-]+)\/([a-z0-9-]+)\/of-i([0-9a-f]+)/g;

  ij.url = o => 'https://www.infojobs.net/' + o.ciudad + '/' + o.slug + '/of-i' + o.hash;

  /* opts: {remoto, provincia, desde ('_24_HOURS' por defecto)} */
  ij.buscar = async (consultas, opts) => {
    opts = opts || {};
    const desde = opts.desde || '_24_HOURS';
    const res = await R.enTandas(consultas, async kw => {
      const qs = 'keyword=' + encodeURIComponent(kw)
        + (opts.remoto ? '&teleworkingIds=2' : '')
        + (opts.provincia ? '&provinceIds=' + opts.provincia : '')
        + '&sinceDate=' + desde;
      const html = await fetch(BUSCAR + qs, { credentials: 'include' }).then(r => r.text());
      let m, n = 0; RE_URL.lastIndex = 0;
      while ((m = RE_URL.exec(html)))
        if (!ij.ofertas[m[3]]) { ij.ofertas[m[3]] = { hash: m[3], ciudad: m[1], slug: m[2], kw }; n++; }
      return kw + ':+' + n;
    }, 300);
    return res.join(' ') + ' TOTAL=' + Object.keys(ij.ofertas).length;
  };

  /* El slug ya trae el puesto, así que se filtra por título sin pedir la ficha. */
  ij.filtrar = (hashesConocidos) => {
    const conocidos = new Set(hashesConocidos || []);
    ij.cola = Object.values(ij.ofertas).filter(o =>
      !conocidos.has(o.hash) && R.tituloVale(o.slug.replace(/-/g, ' ')));
    return { candidatas: Object.keys(ij.ofertas).length, sobreviven: ij.cola.length };
  };

  /* Recorta la descripción antes de mirar nada.
   *
   * OJO: sobre el HTML completo de InfoJobs cualquier conteo de tecnologías
   * sale envenenado — `\.net` casa con «infojobs.net» y da 45 apariciones de
   * C#/.NET en todas las ofertas, y «cliente» aparece en el pie de página.
   * Por eso se corta entre «Descripción» y el final de «Requisitos mínimos». */
  ij.descripcion = txt => {
    const i = txt.search(/Descripci[oó]n\b/);
    const j = txt.search(/Requisitos m[ií]nimos/);
    const ini = (i >= 0 && (j < 0 || i < j)) ? i : (j >= 0 ? j : 0);
    const fin = j >= 0 ? j + 1400 : ini + 1800;
    return txt.slice(ini, fin);
  };

  ij.detallar = async (n) => {
    const lote = ij.cola.splice(0, n || 10);
    await R.enTandas(lote, async o => {
      const html = await fetch(ij.url(o), { credentials: 'include' }).then(r => r.text());
      const meta = (html.match(/<meta name="description" content="([^"]{0,300})/) || ['', ''])[1];
      const todo = R.texto(html);
      const desc = ij.descripcion(todo);
      const dn = R.norm(desc);
      Object.assign(o, {
        empresa: (meta.match(/en la empresa ([^.,]{2,60})/) || ['', ''])[1].trim(),
        titulo: R.texto((html.match(/<h1[^>]*>([\s\S]{0,120}?)<\/h1>/) || ['', ''])[1]),
        /* El «Bruto/año» del panel lateral, no el del cuerpo. */
        salario: (todo.match(/[\d.]{4,9}\s*[-–]?\s*[\d.]{0,9}\s*€?\s*Bruto\/a[nñ]o/i) || [''])[0].trim(),
        anios: R.anios(R.norm(todo)),
        etiqueta: (R.norm(todo).match(/(solo teletrabajo|teletrabajo (parcial|h[ií]brido)|presencial|h[ií]brid)/) || [''])[0],
        publicado: (R.norm(todo).match(/hace\s+\d+\s*[dhm]\b|hace\s+\d+\s+(dias|horas|minutos)/) || [''])[0],
        /* La modalidad se decide con la descripción, no con la etiqueta:
         * hoy una oferta etiquetada «solo teletrabajo» decía en el cuerpo
         * «para nuestras oficinas centrales, ubicadas en Riudoms». */
        modalidad: R.modalidad(dn, R.norm(o.ciudad), /teletrabajo/.test(R.norm(todo))),
        _dn: dn,
        _desc: desc,
      });
      ij.det.push(o);
    }, 280);
    return 'detalladas=' + ij.det.length + ' pendientes=' + ij.cola.length;
  };

  ij.clasificar = () => {
    const fila = o => [o.hash.slice(0, 10), o.empresa, o.titulo, o.ciudad,
                       o.modalidad.tipo, o.publicado, o.salario || '-', o.anios || '-',
                       (o.modalidad.frases[0] || '').slice(0, 80)].join('|');
    const dentro = ij.det.filter(o => ['remoto', 'local', 'remoto_sin_confirmar'].includes(o.modalidad.tipo));
    R.cola = dentro.map(fila);
    return { dentro: dentro.length, fuera: ij.det.length - dentro.length };
  };

  /* Trozo de descripción de una oferta ya aceptada, para redactar sus `reqs`. */
  ij.leer = (hash, chars) => {
    const o = ij.det.find(x => x.hash.startsWith(hash));
    return o ? o._desc.slice(0, chars || 900) : 'no encontrada';
  };

  ij.terminos = (dicc) => ij.det.map(o => {
    const hits = [];
    for (const k in dicc) {
      const m = o._dn && o._dn.match(new RegExp(dicc[k], 'g'));
      if (m) hits.push(k + ':' + m.length);
    }
    hits.sort((a, b) => b.split(':')[1] - a.split(':')[1]);
    return o.hash.slice(0, 10) + '|' + hits.slice(0, 22).join(',');
  });
})(window.__radar);
