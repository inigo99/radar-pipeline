# -*- coding: utf-8 -*-
"""Rellena `anios_min` en las ofertas que ya estaban en el radar (uno y no más).

    python pipeline/backfill_anios.py [margen]     # desde la raíz del repo

Las ofertas anteriores al 10 sep 2026 no traen el campo, pero muchas llevan el
dato escrito en su `alerta`, en las etiquetas de sus `reqs`, en `sal_base` o en
las notas que escribió Íñigo. Esto lo saca de ahí con `experiencia.py`: no
inventa nada, sólo lee lo que ya estaba escrito. Las que no lo digan se quedan
sin campo, y sin campo no se aparta ninguna oferta.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiencia import anios_pedidos, anios_perfil, clasifica

DATA = os.environ.get("RADAR_DATA", "data")
ofertas = json.load(open(os.path.join(DATA, 'ofertas.json'), encoding='utf-8'))
estado  = json.load(open(os.path.join(DATA, 'estado.json'), encoding='utf-8'))
perfil  = json.load(open(os.path.join(DATA, 'perfil.json'), encoding='utf-8'))
tailor  = json.load(open(os.path.join(DATA, 'tailor.json'), encoding='utf-8'))
mios = anios_perfil(perfil)
margen = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0

cambios, resumen = [], {'encaja': 0, 'justo': 0, 'lejos': 0, 'desconocido': 0}
for o in ofertas:
    if o.get('anios_min') is not None:
        y = o['anios_min']
    else:
        textos = [o.get('alerta'), o.get('sal_base'), (estado.get(o['id']) or {}).get('notas')]
        textos += [l for _, _, l in o.get('reqs', [])]
        y = anios_pedidos(*textos)
        if y is not None:
            o['anios_min'] = y
            cambios.append(o['id'])
    est, _ = clasifica(y, mios, margen)
    resumen[est] += 1
    o['_est'] = est

json.dump([{k: v for k, v in o.items() if k != '_est'} for o in ofertas],
          open(os.path.join(DATA, 'ofertas.json'), 'w', encoding='utf-8'), ensure_ascii=False)

print(f"perfil: {mios} años · margen: {margen} · {len(cambios)} ofertas con anios_min nuevo")
print(f"  encaja {resumen['encaja']} · desconocido {resumen['desconocido']} "
      f"· justo {resumen['justo']} · lejos {resumen['lejos']}")
IA = {'genai', 'ml', 'cv', 'ds', 'mlops', 'research'}
for est in ('justo', 'lejos'):
    fila = [o for o in ofertas if o['_est'] == est]
    print(f"\n{est.upper()} ({len(fila)}; {sum(1 for o in fila if (tailor.get(o['id']) or {}).get('familia') in IA)} de IA/DS):")
    for o in sorted(fila, key=lambda x: x['anios_min']):
        marca = (estado.get(o['id']) or {}).get('estado', '')
        print(f"  {o['anios_min']}a {o['empresa'][:24]:25} {o['puesto'][:44]:45} {marca}")
