// browser/jsearch.js — JSearch (RapidAPI): Google for Jobs agregado (LinkedIn, Indeed,
// Glassdoor, ZipRecruiter, agregadores...). Se pega como código con javascript_tool en una
// pestaña cuyo origin sea https://rapidapi.com — la API sólo deja CORS desde ese origen
// (comprobado el 16 sep 2026: 403 CORS desde cualquier otro dominio, 200 desde rapidapi.com).
// No hace falta sesión ni login, sólo estar en ese dominio.
//
// La clave vive en config/api_keys (rapidapi_key) de la BD del artifact, nunca en el repo.
;void function () {
  const HOST = 'jsearch.p.rapidapi.com';
  // Sin job_description: con ella cada resultado pesa varios KB y revienta el corte de
  // ~1.200 caracteres de javascript_tool. Sólo se pide aparte (job-details) para las
  // supervivientes, en el paso 6.
  const FIELDS = 'job_id,job_title,employer_name,job_publisher,job_apply_link,job_is_remote,' +
    'job_location,job_city,job_country,job_posted_at,job_posted_at_datetime_utc,' +
    'job_min_salary,job_max_salary,job_salary_period,job_salary_string,job_employment_type';

  // opts.date_posted: 'today' suele dar 0-2 resultados; '3days' o 'week' rinden mejor y el
  // filtro de ventana_horas de la configuración se encarga de descartar lo que sobre,
  // igual que ya se hace con Indeed.
  window.__jsearch = async function (key, query, opts) {
    opts = opts || {};
    const params = new URLSearchParams({
      query: query,
      num_pages: String(opts.num_pages || 1),
      country: opts.country || 'es',
      date_posted: opts.date_posted || '3days',
      fields: FIELDS
    });
    const r = await fetch('https://' + HOST + '/search-v2?' + params.toString(), {
      headers: { 'x-rapidapi-key': key, 'x-rapidapi-host': HOST }
    });
    const j = await r.json();
    if (j.status !== 'OK') throw new Error('JSearch error: ' + JSON.stringify(j.error || j));
    window.__jsearch_last = (j.data && j.data.jobs) || [];
    return window.__jsearch_last.length;
  };

  // Saca resultados en trozos pequeños, como window.__pull de LinkedIn/InfoJobs: una línea
  // por oferta con los campos separados por '|'.
  window.__jsearch_pull = function (n) {
    const arr = window.__jsearch_last || [];
    const batch = arr.splice(0, n || 6);
    return batch.map(function (j) {
      return [
        j.job_id, j.employer_name, j.job_title, j.job_location, j.job_posted_at,
        j.job_is_remote, j.job_publisher, j.job_min_salary || '', j.job_max_salary || '',
        j.job_salary_string || '', j.job_apply_link
      ].join('|');
    });
  };

  // Detalle completo (con descripción) de una oferta ya filtrada — sólo cuando toca escribir
  // sus reqs (paso 6), cuatro o cinco al día, nunca para decidir si una oferta encaja.
  window.__jsearch_details = async function (key, job_id) {
    const params = new URLSearchParams({ job_id: job_id, country: 'es' });
    const r = await fetch('https://' + HOST + '/job-details?' + params.toString(), {
      headers: { 'x-rapidapi-key': key, 'x-rapidapi-host': HOST }
    });
    const j = await r.json();
    return (j.data && j.data[0]) || null;
  };
}();
