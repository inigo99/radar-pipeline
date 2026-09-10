# -*- coding: utf-8 -*-
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tailor import T

RES = json.load(open('data/resultado.json'))


def _opcional(nombre, defecto):
    """data/filtradas.json y data/embudo.json pueden no existir todavía."""
    try:
        with open('data/' + nombre, encoding='utf-8') as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return defecto


FILTRADAS = _opcional('filtradas.json', {})
EMBUDO = _opcional('embudo.json', {})

rows=[]
for r in RES:
    rows.append(dict(
      id=r['id'], empresa=r['empresa'], puesto=r['puesto'], ubicacion=r['ubicacion'],
      modalidad=r['modalidad'], publicada=r['publicada'], idioma=r['idioma'], fuente=r['fuente'],
      salMin=r['sal_min'], salMax=r['sal_max'], salMedio=r['sal_medio'], salOrigen=r['sal_origen'],
      salBase=r['sal_base'], url=r['url'], scoreOrig=r['score_orig'], scoreAdap=r['score_adap'],
      delta=r['delta'], mejora=r['mejora_pct'], fuertes=r['fuertes'], huecos=r['huecos'],
      alerta=r.get('alerta',''), titular=T[r['id']]['titular'],
      resumen=T[r['id']]['resumen'], familia=T[r['id']]['familia'],
      reqs=[f"{l} (peso {w})" for _,w,l in sorted(r['reqs'], key=lambda x:-x[1])[:12]],
      zona=('local' if ('Navarra' in r['modalidad'] or 'Gipuzkoa' in r['modalidad']) else 'remoto'),
      ambito=r['ambito'],
      prioridad=r.get('prioridad', r['score_adap']), brecha=r.get('brecha', []),
      foco=r.get('foco', r.get('prioridad', r['score_adap'])),
      dias=r.get('dias'), motivoFoco=r.get('motivo_foco',''),
      aniosMin=r.get('anios_min'),
    ))

DATA = json.dumps(rows, ensure_ascii=False, separators=(',',':'))
FILTRADAS_JS = json.dumps(sorted(FILTRADAS.values(),
                                 key=lambda f: (f.get('fecha', ''), f.get('empresa', '')),
                                 reverse=True),
                          ensure_ascii=False, separators=(',', ':'))
EMBUDO_JS = json.dumps(EMBUDO, ensure_ascii=False, separators=(',', ':'))

from base_cv import (BULLETS_ES, BULLETS_EN, SKILLS_ES, SKILLS_EN, CONTACTO,
                      ORDEN, ORDEN_SKILLS, CV_LABELS, PERFIL_LLM,
                      TFM_VARIANT, TFG_VARIANT)
from datos import PERFIL as _PERFIL_DOC
from experiencia import anios_perfil, MARGEN_DEF

# Los años de experiencia del CV, sumados de las fechas de sus puestos. Se
# recalculan en cada ejecución, así que la cifra sube sola con el tiempo.
ANIOS_PERFIL = anios_perfil(_PERFIL_DOC)
_pl = dict(PERFIL_LLM)
_pl["tel"], _pl["email"], _pl["linkedin"] = CONTACTO["tel"], CONTACTO["email"], CONTACTO["linkedin"]
_pl["experiencia"] = [
    {k: v for k, v in e.items() if k != "bullets"} |
    {"logros_es": [BULLETS_ES[b] for b in e["bullets"]],
     "logros_en": [BULLETS_EN[b] for b in e["bullets"]]}
    for e in PERFIL_LLM["experiencia"]]
PERFIL = json.dumps(_pl, ensure_ascii=False, separators=(',', ':'))

# Todo lo que necesita la página para armar el CV en el navegador, bajo demanda.
CV = json.dumps(dict(contacto=CONTACTO, bullets_es=BULLETS_ES, bullets_en=BULLETS_EN,
                     skills_es=SKILLS_ES, skills_en=SKILLS_EN, orden=ORDEN,
                     orden_skills=ORDEN_SKILLS, labels=CV_LABELS,
                     tfm_variant=TFM_VARIANT, tfg_variant=TFG_VARIANT),
                ensure_ascii=False, separators=(',', ':'))

TPL = r"""<title>Radar de ofertas</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#F2F5F4; --surface:#FFFFFF; --surface-2:#FAFBFB; --line:#DDE3E1; --line-soft:#EAEFED;
  --ink:#13181A; --ink-2:#495553; --ink-3:#78857F;
  --accent:#14625A; --accent-ink:#0D453F; --accent-soft:#DCEAE7;
  --good:#1F7A4C; --warn:#9C6B12; --crit:#A63A34;
  --good-bg:#E4F1E9; --warn-bg:#F7EEDA; --crit-bg:#F7E4E2;
  --meter-track:#E4EAE8;
  --on-accent:#FFFFFF; --int:#3B5BA5; --int-bg:#E3E9F6;
  --shadow:0 1px 2px rgba(19,24,26,.05),0 6px 18px -10px rgba(19,24,26,.18);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0E1413; --surface:#161D1C; --surface-2:#1B2322; --line:#2A3432; --line-soft:#222C2A;
  --ink:#E9EFEC; --ink-2:#A9B6B2; --ink-3:#7C8985;
  --accent:#5CBFB0; --accent-ink:#8FD8CC; --accent-soft:#16302C;
  --good:#5DC48C; --warn:#DCA83F; --crit:#E58077;
  --good-bg:#15291F; --warn-bg:#2C2313; --crit-bg:#2E1A18;
  --meter-track:#243230; --on-accent:#08201D; --int:#8FAEE8; --int-bg:#1B2438;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px -12px rgba(0,0,0,.6);
}}
:root[data-theme="dark"]{
  --ground:#0E1413; --surface:#161D1C; --surface-2:#1B2322; --line:#2A3432; --line-soft:#222C2A;
  --ink:#E9EFEC; --ink-2:#A9B6B2; --ink-3:#7C8985;
  --accent:#5CBFB0; --accent-ink:#8FD8CC; --accent-soft:#16302C;
  --good:#5DC48C; --warn:#DCA83F; --crit:#E58077;
  --good-bg:#15291F; --warn-bg:#2C2313; --crit-bg:#2E1A18;
  --meter-track:#243230; --on-accent:#08201D; --int:#8FAEE8; --int-bg:#1B2438;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px -12px rgba(0,0,0,.6);
}
*{box-sizing:border-box}
/* No dependemos de la hoja del envoltorio del artifact: la barra de filtros
   tiene display:flex y sin esto seguiría viéndose en las vistas de panel. */
[hidden]{display:none!important}
.vacio{border:1px dashed var(--line);border-radius:12px;padding:22px;text-align:center;background:var(--surface-2)}
.vacio p{margin:0 0 12px;color:var(--ink-2)}
.vacio .hint{margin:12px 0 0}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--accent);margin-right:6px;animation:pulso 1.1s ease-in-out infinite}
@keyframes pulso{0%,100%{opacity:.25}50%{opacity:1}}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"Public Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1440px;margin:0 auto;padding:28px 20px 64px}
header{margin-bottom:22px}
.hrow{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
.hrow .cfgbtn{flex:none;margin-top:6px}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--accent);margin:0 0 6px}
h1{font-family:"Fraunces","Iowan Old Style",Georgia,serif;font-weight:600;font-size:clamp(28px,4vw,40px);
  margin:0 0 6px;letter-spacing:-.01em;text-wrap:balance}
.sub{color:var(--ink-2);margin:0;max-width:62ch}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:13px 15px;box-shadow:var(--shadow)}
.stat .k{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}
.stat .v{font-family:"IBM Plex Mono",monospace;font-size:25px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:3px;letter-spacing:-.02em}
.stat .n{font-size:12px;color:var(--ink-3);margin-top:1px}
.toolbar{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px;
  display:flex;flex-wrap:wrap;gap:10px 14px;align-items:flex-end;margin-bottom:14px;box-shadow:var(--shadow)}
.fld{display:flex;flex-direction:column;gap:4px}
.fld label{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}
input[type=search],select{font-family:inherit;font-size:13.5px;color:var(--ink);background:var(--surface-2);
  border:1px solid var(--line);border-radius:7px;padding:7px 9px;min-width:150px}
input[type=search]{min-width:230px}
input[type=range]{width:150px;accent-color:var(--accent)}
.rngval{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-2);font-variant-numeric:tabular-nums}
button{font-family:inherit;cursor:pointer}
.reset{background:transparent;border:1px solid var(--line);color:var(--ink-2);border-radius:7px;padding:7px 12px;font-size:13px}
.reset:hover{border-color:var(--accent);color:var(--accent)}
.count{margin-left:auto;font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink-3);padding-bottom:7px}
.views{display:flex;gap:4px;margin-bottom:12px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.view{background:none;border:0;border-bottom:2px solid transparent;padding:9px 14px;margin-bottom:-1px;
  font-family:"Public Sans",sans-serif;font-size:13.5px;font-weight:600;color:var(--ink-3);
  display:flex;align-items:center;gap:7px}
.view:hover{color:var(--accent)}
.view.on{color:var(--accent);border-bottom-color:var(--accent)}
.view .n{font-family:"IBM Plex Mono",monospace;font-size:11px;font-weight:600;
  background:var(--meter-track);color:var(--ink-2);border-radius:20px;padding:1px 7px;font-variant-numeric:tabular-nums}
.view.on .n{background:var(--accent-soft);color:var(--accent-ink)}
.xbtn{background:none;border:1px solid transparent;border-radius:6px;color:var(--ink-3);
  font-size:15px;line-height:1;padding:3px 7px;transition:.13s}
.xbtn:hover{border-color:var(--crit);color:var(--crit);background:var(--crit-bg)}
.rebtn{background:none;border:1px solid var(--line);border-radius:6px;color:var(--ink-2);
  font-size:12px;padding:4px 9px;white-space:nowrap}
.rebtn:hover{border-color:var(--accent);color:var(--accent)}
.fase{font-family:inherit;font-size:12.5px;color:var(--ink);background:var(--surface);
  border:1px solid var(--line);border-radius:7px;padding:5px 7px}
.notas{width:100%;min-height:84px;resize:vertical;font-family:inherit;font-size:13px;line-height:1.55;
  color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:9px 11px}
.notas:focus{outline:2px solid var(--accent);outline-offset:1px}
.track{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px}
.saved{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--ink-3);opacity:0;transition:.2s}
.saved.on{opacity:1}
.p-fase{background:var(--accent-soft);color:var(--accent-ink)}
.p-f-rechazada{background:var(--crit-bg);color:var(--crit)}
.p-f-oferta{background:var(--good-bg);color:var(--good)}
.p-nov-rechazo{background:var(--crit-bg);color:var(--crit)}
.p-nov-avance{background:var(--good-bg);color:var(--good)}
.p-nov-acuse{background:var(--meter-track);color:var(--ink-2)}
.novbox{background:var(--surface-2);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:8px;padding:9px 11px;font-size:13px;line-height:1.5}
.novbox a{color:var(--accent);text-decoration:none}
.novbox a:hover{text-decoration:underline}
.huerf{background:var(--warn-bg);color:var(--warn);border-radius:8px;padding:10px 13px;font-size:12.5px;margin-bottom:12px}
.huerf ul{margin:6px 0 0 18px;padding:0}
.huerf li{margin:2px 0}
.cfgbtn{background:var(--surface);border:1px solid var(--line);border-radius:7px;color:var(--ink-2);
  padding:7px 12px;font-size:13px;white-space:nowrap}
.cfgbtn:hover{border-color:var(--accent);color:var(--accent)}
.modal{position:fixed;inset:0;background:rgba(19,24,26,.55);display:flex;align-items:center;
  justify-content:center;padding:20px;z-index:60}
.modal .box{background:var(--ground);border-radius:14px;box-shadow:0 20px 60px -20px rgba(0,0,0,.5);
  width:min(760px,100%);max-height:88vh;display:flex;flex-direction:column;overflow:hidden}
.modal h2{font-family:"Fraunces","Iowan Old Style",Georgia,serif;font-weight:600;font-size:24px;
  margin:0;padding:20px 24px 0}
.modal .body{padding:14px 24px 20px;overflow:auto}
.modal .foot{display:flex;gap:10px;justify-content:flex-end;align-items:center;
  padding:14px 24px;border-top:1px solid var(--line);background:var(--surface)}
fieldset{border:1px solid var(--line);border-radius:10px;padding:14px 16px 16px;margin:0 0 16px;background:var(--surface)}
legend{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--ink-3);padding:0 6px}
.cgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px 16px}
@media(max-width:640px){.cgrid{grid-template-columns:1fr}}
.cf{display:flex;flex-direction:column;gap:4px}
.cf.full{grid-column:1/-1}
.cf label{font-size:12.5px;font-weight:600;color:var(--ink-2)}
.cf .h{font-size:11.5px;color:var(--ink-3);line-height:1.45}
.cf input[type=text],.cf input[type=number],.cf textarea,.cf select{
  font-family:inherit;font-size:13.5px;color:var(--ink);background:var(--surface-2);
  border:1px solid var(--line);border-radius:7px;padding:7px 9px;width:100%}
.cf textarea{min-height:78px;resize:vertical;line-height:1.5}
.cf input:focus,.cf textarea:focus,.cf select:focus{outline:2px solid var(--accent);outline-offset:1px}
.chk{display:flex;align-items:flex-start;gap:8px;font-size:13px;color:var(--ink-2);line-height:1.4}
.chk input{accent-color:var(--accent);margin-top:2px;flex:none}
.cfgnota{background:var(--warn-bg);color:var(--warn);border-radius:8px;padding:9px 12px;font-size:12.5px;margin:0 0 14px}
.offline{background:var(--warn-bg);color:var(--warn);border-radius:8px;padding:9px 12px;font-size:12.5px;margin-bottom:12px}
.tablewrap{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow-x:auto;box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;min-width:1320px}
thead th{position:sticky;top:0;background:var(--surface);z-index:2;border-bottom:1.5px solid var(--line);
  padding:0;text-align:left;white-space:nowrap}
thead th button{width:100%;background:none;border:0;color:var(--ink-3);padding:11px 12px;text-align:left;
  font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  display:flex;align-items:center;gap:5px}
thead th button:hover{color:var(--accent)}
thead th.on button{color:var(--accent)}
.arrow{opacity:.35;font-size:9px}
thead th.on .arrow{opacity:1}
tbody tr.r{border-bottom:1px solid var(--line-soft);cursor:pointer}
tbody tr.r:hover{background:var(--surface-2)}
tbody tr.r.open{background:var(--accent-soft)}
td{padding:11px 10px;vertical-align:top}
.co{font-weight:600}
.pt{color:var(--ink-2);font-size:13px}
.num{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;white-space:nowrap}
.pill{display:inline-block;font-size:11px;font-weight:600;padding:2.5px 7px;border-radius:20px;white-space:nowrap;
  font-family:"IBM Plex Mono",monospace;letter-spacing:.02em}
.p-rem{background:var(--good-bg);color:var(--good)} .p-hib{background:var(--warn-bg);color:var(--warn)}
.p-pub{background:var(--good-bg);color:var(--good)} .p-est{background:var(--warn-bg);color:var(--warn)}
.p-lang{background:var(--accent-soft);color:var(--accent-ink);border:1px solid transparent}
.p-int{background:var(--int-bg);color:var(--int)} .p-es{background:var(--surface-2);color:var(--ink-2);border:1px solid var(--line)}
.p-loc{background:var(--warn-bg);color:var(--warn)}
.p-fam-foco{background:var(--accent-soft);color:var(--accent-ink)}
.p-fam-otro{background:var(--surface-2);color:var(--ink-2);border:1px solid var(--line)}
.meter{display:flex;align-items:center;gap:7px}
.mbar{width:56px;height:6px;border-radius:3px;background:var(--meter-track);overflow:hidden;flex:none}
.mbar i{display:block;height:100%;background:var(--accent);border-radius:3px}
.delta{color:var(--good);font-size:12px;font-weight:600}
.detail td{background:var(--surface-2);border-bottom:1px solid var(--line);padding:0}
.dwrap{position:sticky;left:0;width:min(100vw - 44px, 1396px);padding:16px 14px 20px;box-sizing:border-box}
.dgrid{display:grid;grid-template-columns:1.35fr 1fr;gap:22px}
@media(max-width:820px){.dgrid{grid-template-columns:1fr}}
.dh{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 6px}
.dsec{margin-bottom:16px}
.tags{display:flex;flex-wrap:wrap;gap:6px}
.tag{font-size:12px;padding:3px 9px;border-radius:6px;background:var(--surface);border:1px solid var(--line);color:var(--ink-2)}
.tag.gap{background:var(--crit-bg);color:var(--crit);border-color:transparent}
.tag.str{background:var(--good-bg);color:var(--good);border-color:transparent}
.tag.rapido{background:var(--good-bg);color:var(--good);border-color:transparent}
.tag.medio{background:var(--warn-bg);color:var(--warn);border-color:transparent}
.tag.lento{background:var(--crit-bg);color:var(--crit);border-color:transparent}
.brecha-nota{font-size:12.5px;color:var(--ink-2);line-height:1.5;margin:8px 0 0}
.brecha-nota li{margin:2px 0}
.note{font-size:13px;color:var(--ink-2);margin:0;line-height:1.55}
.alert{background:var(--crit-bg);color:var(--crit);border-radius:8px;padding:10px 12px;font-size:13px;margin:0 0 16px;line-height:1.5}
.actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:4px}
.btn{display:inline-flex;align-items:center;gap:7px;border-radius:8px;padding:9px 15px;font-size:13.5px;
  font-weight:600;text-decoration:none;border:1px solid var(--line);background:var(--surface);color:var(--ink);transition:.13s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.btn.primary:hover{filter:brightness(1.08);color:var(--on-accent)}
.btn:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{
  outline:2px solid var(--accent);outline-offset:2px}
.tabs{display:flex;gap:6px;margin-bottom:7px}
.tab{background:none;border:0;border-bottom:2px solid transparent;padding:4px 2px;margin-right:10px;
  font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.11em;text-transform:uppercase;color:var(--ink-3)}
.tab.on{color:var(--accent);border-bottom-color:var(--accent)}
.tab:hover{color:var(--accent)}
.hint{font-size:12px;color:var(--ink-3);margin:7px 0 0}
.letter{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px 14px;
  font-size:13px;line-height:1.6;color:var(--ink-2);white-space:pre-wrap;max-height:230px;overflow:auto}
.empty{padding:44px;text-align:center;color:var(--ink-3)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:18px 20px 22px;box-shadow:var(--shadow)}
.panel h3{font-family:"Fraunces","Iowan Old Style",Georgia,serif;font-weight:600;
  font-size:19px;margin:0 0 4px;letter-spacing:-.01em}
.panel .lede{color:var(--ink-2);margin:0 0 16px;max-width:74ch;font-size:13.5px;line-height:1.6}
.panel h4{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.11em;
  text-transform:uppercase;color:var(--ink-3);margin:22px 0 8px}
.ptab{width:100%;border-collapse:collapse;min-width:0;font-size:13px}
.ptab th{text-align:left;font-family:"IBM Plex Mono",monospace;font-size:10px;
  letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3);
  border-bottom:1px solid var(--line);padding:6px 9px 7px;white-space:nowrap}
.ptab td{padding:8px 9px;border-bottom:1px solid var(--line-soft);vertical-align:top}
.ptab tr:last-child td{border-bottom:0}
.ptab .num{text-align:right}
.motivo{font-size:12.5px;color:var(--ink-2);line-height:1.5}
.pill.p-mot-salario{background:var(--warn-bg);color:var(--warn)}
.pill.p-mot-modalidad{background:var(--int-bg);color:var(--int)}
.pill.p-mot-ambito{background:var(--crit-bg);color:var(--crit)}
.pill.p-mot-otro{background:var(--meter-track);color:var(--ink-2)}
.pill.p-mot-experiencia{background:var(--warn-bg);color:var(--warn)}
.pill.p-exp-justo{background:var(--warn-bg);color:var(--warn)}
.pill.p-exp-lejos{background:var(--crit-bg);color:var(--crit)}
.barra{height:7px;border-radius:4px;background:var(--meter-track);overflow:hidden;min-width:70px}
.barra i{display:block;height:100%;background:var(--accent);border-radius:4px}
.flaca{color:var(--ink-3);font-style:italic}
.hoygrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin-top:6px}
.tarjeta{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:14px 15px 15px;display:flex;flex-direction:column;gap:9px}
.tarjeta .co{font-size:15px;line-height:1.3}
.tarjeta .pt{font-size:13px;line-height:1.4}
.tarjeta .meta{display:flex;flex-wrap:wrap;gap:6px}
.tarjeta .acc{display:flex;flex-wrap:wrap;gap:7px;margin-top:auto;padding-top:4px}
.tarjeta .acc .btn{padding:6px 11px;font-size:12.5px}
.tarjeta .por{font-size:12.5px;color:var(--ink-2);line-height:1.5;margin:0}
.ritmo{display:flex;flex-wrap:wrap;gap:14px 26px;align-items:flex-end;margin:2px 0 18px}
.ritmo .cifra{font-family:"IBM Plex Mono",monospace;font-size:30px;font-weight:600;
  font-variant-numeric:tabular-nums;line-height:1;letter-spacing:-.02em}
.ritmo .et{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-3);margin-bottom:5px}
.ritmo .col{display:flex;flex-direction:column}
.ritmo .barra{width:190px;margin-top:7px}
.objin{width:58px;font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--ink);
  background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:4px 6px}
.p-dias-ok{background:var(--good-bg);color:var(--good)}
.p-dias-tibio{background:var(--warn-bg);color:var(--warn)}
.p-dias-frio{background:var(--crit-bg);color:var(--crit)}
.pgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
@media(max-width:640px){.ptab{font-size:12px}.ptab th,.ptab td{padding:6px 5px}}
footer{margin-top:26px;font-size:12.5px;color:var(--ink-3);line-height:1.7;max-width:78ch}
footer b{color:var(--ink-2);font-weight:600}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(20px);opacity:0;
  background:var(--ink);color:var(--ground);padding:10px 18px;border-radius:9px;font-size:13.5px;
  transition:.2s;pointer-events:none;z-index:50}
.toast.on{opacity:1;transform:translateX(-50%) translateY(0)}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<div class="wrap">
<header>
  <div class="hrow">
    <div>
      <p class="eyebrow">Actualizado el __FECHA__ · __N__ ofertas en el radar</p>
      <h1>Radar de ofertas</h1>
    </div>
    <button class="cfgbtn" id="cfgbtn">Configuración</button>
  </div>
  <p class="sub">Ofertas recientes que encajan con tu perfil: 100&nbsp;% remoto desde España o desde el extranjero, y presencial o híbrido en Navarra y Gipúzcoa. Rastreadas en LinkedIn, InfoJobs, Tecnoempleo, Indeed y los portales de empleo remoto. El CV adaptado, la cover letter y el correo a RRHH se generan desde dentro de la oferta, con un botón, sólo para las que te interesen. Pulsa cualquier fila para abrirla, o «Configuración» para cambiar qué se busca: la tarea diaria lo lee antes de cada ejecución.</p>
</header>

<div class="stats" id="stats"></div>

<div class="toolbar">
  <div class="fld"><label for="q">Buscar</label>
    <input type="search" id="q" placeholder="empresa, puesto, tecnología…"></div>
  <div class="fld"><label for="fmod">Modalidad</label>
    <select id="fmod"><option value="">Todas</option><option value="remoto">Remoto</option><option value="local">Navarra / Gipuzkoa</option></select></div>
  <div class="fld"><label for="famb">Ámbito</label>
    <select id="famb"><option value="">Todos</option><option>España</option><option>Internacional</option><option>Navarra / Gipuzkoa</option></select></div>
  <div class="fld"><label for="ffam">Familia</label>
    <select id="ffam"><option value="">Todas</option></select></div>
  <div class="fld"><label for="ffue">Fuente</label>
    <select id="ffue"><option value="">Todas</option></select></div>
  <div class="fld"><label for="flang">Idioma</label>
    <select id="flang"><option value="">Ambos</option><option value="es">Español</option><option value="en">Inglés</option></select></div>
  <div class="fld"><label for="fsal">Salario medio mínimo</label>
    <div style="display:flex;align-items:center;gap:8px">
      <input type="range" id="fsal" min="35000" max="90000" step="1000" value="35000">
      <span class="rngval" id="fsalv">35 000 €</span></div></div>
  <div class="fld"><label for="fsc">Coincidencia mínima</label>
    <div style="display:flex;align-items:center;gap:8px">
      <input type="range" id="fsc" min="0" max="100" step="5" value="0">
      <span class="rngval" id="fscv">0 %</span></div></div>
  <button class="reset" id="reset">Limpiar</button>
  <span class="count" id="count"></span>
</div>

<div id="aviso"></div>
<div class="views" id="views"></div>

<div class="tablewrap" id="tablawrap">
  <table>
    <thead><tr id="head"></tr></thead>
    <tbody id="body"></tbody>
  </table>
</div>

<div id="panelHoy" hidden></div>
<div id="panelFiltradas" hidden></div>
<div id="panelEmbudo" hidden></div>

<footer>
  <p><b>Cómo se calcula la coincidencia.</b> Cada oferta tiene sus requisitos con un peso según la importancia que les da el anuncio. Un requisito puntúa 1,0 si está demostrado en un bullet o en el resumen del CV, 0,5 si sólo aparece en la lista de competencias técnicas, y 0 si no lo tienes. La columna «adaptado» aplica lo mismo al CV generado para esa oferta: la mejora sale sólo de sacar a un bullet algo que ya sabes hacer. Ningún requisito que no cumplas sube de 0.</p>
  <p><b>Hoy y el orden por defecto.</b> La página abre en «Hoy»: la cola corta de las seis ofertas a las que conviene echar ahora, en orden de <em>foco</em>. El foco parte de la prioridad y le resta lo que ya sabes que no va a llegar a ningún sitio: las ofertas publicadas hace más de una, dos o tres semanas (que nadie está retirando desde que el barrido de cerradas salió de la tarea diaria) y los títulos de sénior, lead o arquitecto, que son literalmente el motivo de seis de tus descartes manuales. Suma un poco cuando la oferta publica banda salarial. El contador semanal y su objetivo se guardan en este navegador.</p>
  <p><b>Prioridad y familia.</b> La tabla ordena por «prioridad»: el CV adaptado con un pequeño plus para las familias de IA y Data Science (GenAI/LLM, Machine Learning, Computer Vision, Data Science/Eng.) mientras te reorientas hacia ahí; Full Stack/Backend sigue en el radar, sólo pesa algo menos por defecto. Pulsa la columna «CV adaptado» en cualquier momento para ver el encaje puro, sin ese ajuste.</p>
  <p><b>Años de experiencia.</b> Cada oferta lleva los años que exige el anuncio, cuando los dice. Tu CV suma los suyos solo, de las fechas de tus puestos, así que la cifra sube con el tiempo sin tocar nada. Lo que pida más de lo que tienes sale de la cola y se va a «Filtradas», separando lo que se te escapa <em>por poco</em> —dentro del margen que fijes— de lo que queda <em>lejos</em>. Nunca se borra nada, y una oferta que ya hayas aplicado o descartado no se esconde jamás. Las que no dicen años, que son la mayoría, pasan sin más: la falta de dato no aparta a nadie. Los dos números, tus años y el margen, se cambian desde «Configuración» y se aplican al momento, sin esperar a la ejecución de mañana.</p>
  <p><b>Requisitos que no cubres.</b> Dentro de cada oferta, los huecos van clasificados por si merece la pena repasarlos antes de una posible entrevista: en verde, cuestión de días; en ámbar, varias semanas de dedicación real; en rojo, lo que no es realista cubrir en ese plazo (una titulación, un idioma nuevo, años de experiencia, una disciplina muy especializada) — ahí la idea no es estudiar de un día para otro, es tener lista una respuesta honesta. Esto es sólo información para ti: nunca se usa para tocar el CV, la carta o el correo, que nunca dicen que sabes algo que no sabes.</p>
  <p><b>Ámbito.</b> «España» es contrato y empresa aquí. «Internacional» son empresas de fuera que contratan en remoto y cuya restricción geográfica permite residir en España — está verificada oferta por oferta, pero conviene confirmarla en el primer contacto. «Navarra / Gipuzkoa» son las presenciales e híbridas dentro de tus provincias.</p>
  <p><b>Salarios.</b> En verde, el que publica la oferta. En ámbar, una estimación; abre la fila para ver de dónde sale cada una. Referencias: Guía Salarial Manfred 2026, Informe de salarios en IA en España 2026 (Universidad VIU) y Levels.fyi por empresa. El mínimo está en 45 000 €, pero las que caen por publicar una cifra más baja ya no desaparecen: van a la pestaña «Filtradas», porque un filtro que no se puede auditar acaba costando ofertas buenas sin que te enteres.</p>
  <p><b>Modalidad.</b> Se decide con la frase literal de la descripción, no con la etiqueta del portal, que miente a menudo. Cuando el portal la marca remota y la descripción no dice nada que lo contradiga, la oferta entra igual pero marcada como <em>remoto sin confirmar</em>: es una llamada de treinta segundos, no un motivo para tirarla.</p>
</footer>
</div>
<div id="cfgmodal"></div>
<div class="toast" id="toast"></div>

<script>
const DATA = __DATA__;
const PERFIL = __PERFIL__;
const CONTACTO = __CONTACTO__;
const CV = __CV__;
const FILTRADAS = __FILTRADAS__;
const EMBUDO = __EMBUDO__;
const ANIOS_PERFIL = __ANIOS_PERFIL__;   // años de experiencia sumados de su CV
const MARGEN_DEF = __MARGEN_DEF__;
const FAMILIA_ES = {genai:'GenAI / LLM', ml:'Machine Learning', cv:'Computer Vision',
  ds:'Data Science / Eng.', mlops:'MLOps', backend:'Full Stack / Backend', research:'Investigación',
  general:'General / Perfil abierto'};
const FAMILIAS_FOCO = new Set(['genai','ml','cv','ds']);
const COLS = [
 {k:'empresa', t:'Empresa'},
 {k:'puesto', t:'Puesto'},
 {k:'ambito', t:'Ámbito'},
 {k:'familia', t:'Familia'},
 {k:'ubicacion', t:'Ubicación'},
 {k:'modalidad', t:'Modalidad'},
 {k:'idioma', t:'Idioma'},
 {k:'fuente', t:'Fuente'},
 {k:'publicada', t:'Publicada'},
 {k:'salMedio', t:'Salario medio', num:true},
 {k:'salOrigen', t:'Origen'},
 {k:'scoreOrig', t:'CV original', num:true},
 {k:'scoreAdap', t:'CV adaptado', num:true},
 {k:'mejora', t:'Mejora', num:true},
];
/* «Foco» es el orden nuevo por defecto: la prioridad de siempre, castigada por
   antigüedad de la oferta y por títulos de sénior/arquitecto, y premiada un poco
   cuando la oferta publica banda. Ver pipeline/foco.py. */
const FASES=['aplicada','respondida','entrevista','oferta','rechazada'];
const FASE_ES={aplicada:'Aplicada',respondida:'Respondida',entrevista:'Entrevista',oferta:'Oferta recibida',rechazada:'Rechazada'};
const NOV_ES={rechazo:'Rechazo',avance:'Avance',acuse:'Acuse de recibo'};
const CFG_DEF={
  titulos:["AI / Machine Learning Engineer","GenAI / LLM Engineer","Computer Vision Engineer",
           "Data Scientist","Data Engineer","Full Stack Developer","Backend Developer",
           "Software Engineer","Python Developer","MLOps Engineer","Forward Deployed Engineer"],
  keywords:[], excluir_keywords:[], excluir_empresas:["Hired","Hire Feed"],
  solo_remoto:true, areas_locales:["Navarra","Gipuzkoa"],
  ambitos:["España","Internacional","Navarra / Gipuzkoa"],
  salario_min:45000, exigir_salario_publicado:false,
  anios_perfil:null, margen_anios:MARGEN_DEF,
  ventana_horas:24,
  fuentes:["LinkedIn","InfoJobs","Tecnoempleo","Indeed","Manfred"],
  fuentes_semanales:["Himalayas","WeWorkRemotely","RemoteOK"]
};
const FUENTES_POS=["LinkedIn","InfoJobs","Tecnoempleo","Indeed","Manfred","Himalayas","WeWorkRemotely","RemoteOK"];
const AMBITOS_POS=["España","Internacional","Navarra / Gipuzkoa"];
const NOV_CLS={rechazo:'p-nov-rechazo',avance:'p-nov-avance',acuse:'p-nov-acuse'};
let sortK='foco', sortDir=-1, openId=null, vista='hoy';
const OBJ_DEF=10;   // candidaturas por semana; se cambia desde la pestaña «Hoy»
let STATE={}, DOCS={}, CORREO={}, db=null, dbListo=false, dbFallo=false;
let CFG=Object.assign({},CFG_DEF), cfgAbierta=false, cfgGuardando=false;
let sampleNs=null, sampleTried=false;
const GEN={};   // id -> {carta:{texto,estado},mail:{...}} en curso

const hoy = () => new Date().toISOString().slice(0,10);
const st = id => STATE[id] || {estado:'activa'};
const FASES_MOV=['respondida','entrevista','oferta'];
const esFaseRespondida = f => FASES_MOV.includes(f);
const esFaseAplicada   = f => !f || f==='aplicada';
const corr = id => CORREO[id] || null;

function lsLeer(){ try{ return JSON.parse(localStorage.getItem('radar-estado')||'{}'); }catch(e){ return {}; } }
function lsGuardar(){ try{ localStorage.setItem('radar-estado', JSON.stringify(STATE)); }catch(e){} }

async function initEstado(){
  STATE = lsLeer();
  render();
  try{ db = await claude.use('db'); }catch(e){ db=null; }
  if(!db){ dbFallo=true; dbListo=true; render(); return; }
  db.collection('docs').onSnapshot(snap=>{
    const nuevo={};
    snap.docs.forEach(d=>{ const v=d.data(); if(v) nuevo[d.id]=v; });
    DOCS=nuevo; render();
  }, e=>{});
  db.collection('config').onSnapshot(snap=>{
    snap.docs.forEach(d=>{ if(d.id==='filtros' && d.data()) CFG=Object.assign({},CFG_DEF,d.data()); });
    if(cfgAbierta) pintaCfg();
  }, e=>{});
  db.collection('correo').onSnapshot(snap=>{
    const nuevo={};
    snap.docs.forEach(d=>{ const v=d.data(); if(v) nuevo[d.id]=v; });
    CORREO=nuevo; render();
  }, e=>{});
  db.collection('estado').onSnapshot(snap=>{
    const nuevo={};
    snap.docs.forEach(d=>{ const v=d.data(); if(v) nuevo[d.id]=v; });
    STATE=nuevo; dbListo=true; lsGuardar(); render();
  }, e=>{ dbFallo=true; dbListo=true; render(); });
}

let guardando=0;
async function guardar(id, patch){
  const previo = st(id);
  const nuevo = Object.assign({}, previo, patch, {actualizado: new Date().toISOString()});
  if(nuevo.estado==='activa' && !nuevo.notas && !nuevo.fase){ delete STATE[id]; }
  else { STATE[id]=nuevo; }
  lsGuardar(); render();
  if(!db) return;
  try{
    if(STATE[id]) await db.doc('estado/'+id).set(STATE[id]);
    else await db.doc('estado/'+id).delete();
    marcaGuardado(id);
  }catch(e){
    if(e && e.code==='unavailable'){
      try{ if(STATE[id]) await db.doc('estado/'+id).set(STATE[id]); marcaGuardado(id); return; }catch(e2){}
    }
    toast('No se ha podido guardar el cambio; queda en este navegador');
  }
}
function marcaGuardado(id){
  const el=document.getElementById('saved-'+id);
  if(!el) return; el.textContent='Guardado'; el.classList.add('on');
  setTimeout(()=>el.classList.remove('on'),1600);
}
const eur = n => n.toLocaleString('es-ES').replace(/ /g,' ')+' €';
const esc = s => String(s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function filtered(){
  const q=document.getElementById('q').value.trim().toLowerCase();
  const mod=document.getElementById('fmod').value;
  const lang=document.getElementById('flang').value;
  const amb=document.getElementById('famb').value;
  const fam=document.getElementById('ffam').value;
  const fue=document.getElementById('ffue').value;
  const sal=+document.getElementById('fsal').value;
  const sc=+document.getElementById('fsc').value;
  let out = DATA.filter(r=>{
    const s = st(r.id), e = s.estado;
    if(vista==='activa'    && (e!=='activa' || (apartadaExp(r) && openId!==r.id))) return false;
    if(vista==='aplicada'  && (e!=='aplicada' || !esFaseAplicada(s.fase))) return false;
    if(vista==='respondida'&& (e!=='aplicada' || !esFaseRespondida(s.fase))) return false;
    if(vista==='rechazada' && (e!=='aplicada' || s.fase!=='rechazada')) return false;
    if(vista==='descartada'&& e!=='descartada') return false;
    if(sal && r.salMedio<sal) return false;
    if(sc && r.scoreAdap<sc) return false;
    if(lang && r.idioma!==lang) return false;
    if(amb && r.ambito!==amb) return false;
    if(fam && r.familia!==fam) return false;
    if(fue && r.fuente!==fue) return false;
    if(mod==='remoto' && r.zona!=='remoto') return false;
    if(mod==='local' && r.zona!=='local') return false;
    if(q){
      const hay=[r.empresa,r.puesto,r.ubicacion,r.titular,r.ambito,r.fuertes.join(' '),r.huecos.join(' ')].join(' ').toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  const val=(r,k)=> (k==='fase'||k==='fechaAplicacion') ? (st(r.id)[k]||'')
                  : (k==='novedad') ? ((corr(r.id)||{}).fecha||'') : r[k];
  out.sort((a,b)=>{
    let x=val(a,sortK), y=val(b,sortK);
    if(x===undefined||x===null) x = typeof y==='number' ? 0 : '';
    if(y===undefined||y===null) y = typeof x==='number' ? 0 : '';
    if(typeof x==='string'){ const c=x.localeCompare(y,'es'); return c*sortDir; }
    return (x-y)*sortDir;
  });
  return out;
}

const vistaSeguimiento = () => vista==='aplicada'||vista==='respondida'||vista==='rechazada';
function cols(){
  const base = COLS.slice();
  if(vistaSeguimiento()) base.splice(2,0,{k:'fase',t:'Fase'},{k:'fechaAplicacion',t:'Aplicada el'},{k:'novedad',t:'Novedad'});
  return base;
}
function renderHead(){
  document.getElementById('head').innerHTML = cols().map(c=>{
    const on = c.k===sortK;
    const ar = on ? (sortDir===1?'▲':'▼') : '▲';
    return `<th class="${on?'on':''}"><button data-k="${c.k}" aria-label="Ordenar por ${esc(c.t)}">${esc(c.t)}<span class="arrow">${ar}</span></button></th>`;
  }).join('') + '<th></th>';
  document.querySelectorAll('#head button').forEach(b=>b.onclick=()=>{
    const k=b.dataset.k;
    if(k===sortK) sortDir*=-1; else { sortK=k; sortDir = (cols().find(c=>c.k===k)||{}).num ? -1 : 1; }
    render();
  });
}

const lineas = v => (Array.isArray(v)?v:[]).join('\n');
const aLista  = v => String(v||'').split('\n').map(x=>x.trim()).filter(Boolean);
const chks = (name, posibles, sel) => posibles.map((o,i)=>
  `<label class="chk"><input type="checkbox" data-cfg="${name}" value="${esc(o)}" ${sel.includes(o)?'checked':''}>${esc(o)}</label>`).join('');

function cfgHTML(){
  const c = CFG;
  return `<div class="modal" role="dialog" aria-modal="true" aria-label="Configuración del radar"><div class="box">
    <h2>Configuración del radar</h2>
    <div class="body">
      <p class="cfgnota">Esto es lo que lee la tarea diaria antes de buscar. Lo que cambies aquí se aplica en la siguiente ejecución, sin tocar la tarea.</p>

      <fieldset><legend>Qué se busca</legend><div class="cgrid">
        <div class="cf full"><label for="c-tit">Puestos objetivo</label>
          <span class="h">Uno por línea. Se usan tal cual como consulta en cada fuente.</span>
          <textarea id="c-tit">${esc(lineas(c.titulos))}</textarea></div>
        <div class="cf"><label for="c-kw">Palabras clave extra</label>
          <span class="h">Una por línea. Se suman a las consultas.</span>
          <textarea id="c-kw">${esc(lineas(c.keywords))}</textarea></div>
        <div class="cf"><label for="c-xkw">Palabras que descartan</label>
          <span class="h">Si aparecen en la oferta, fuera.</span>
          <textarea id="c-xkw">${esc(lineas(c.excluir_keywords))}</textarea></div>
        <div class="cf full"><label for="c-xemp">Empresas que descartan</label>
          <span class="h">Intermediarias y clonadoras. Una por línea.</span>
          <textarea id="c-xemp">${esc(lineas(c.excluir_empresas))}</textarea></div>
      </div></fieldset>

      <fieldset><legend>Dónde</legend><div class="cgrid">
        <div class="cf full"><label class="chk"><input type="checkbox" id="c-rem" ${c.solo_remoto?'checked':''}>Sólo 100 % remoto, salvo en las zonas de abajo</label></div>
        <div class="cf"><label for="c-loc">Zonas donde aceptas presencial o híbrido</label>
          <span class="h">Una por línea.</span>
          <textarea id="c-loc">${esc(lineas(c.areas_locales))}</textarea></div>
        <div class="cf"><label>Ámbitos que cuentan</label>
          <div style="display:flex;flex-direction:column;gap:6px;margin-top:4px">${chks('ambitos',AMBITOS_POS,c.ambitos||[])}</div></div>
      </div></fieldset>

      <fieldset><legend>Filtros</legend><div class="cgrid">
        <div class="cf"><label for="c-sal">Salario medio mínimo (€ brutos/año)</label>
          <input type="number" id="c-sal" min="0" step="1000" value="${c.salario_min==null?'':c.salario_min}"></div>
        <div class="cf"><label for="c-exp">Tus años de experiencia</label>
          <span class="h">Vacío = calcularlo de las fechas de tu CV (ahora, ${ANIOS_PERFIL} años).</span>
          <input type="number" id="c-exp" min="0" step="0.5" placeholder="${ANIOS_PERFIL}" value="${c.anios_perfil==null?'':c.anios_perfil}"></div>
        <div class="cf"><label for="c-marg">Margen de años que aún te juegas</label>
          <span class="h">Todo lo que pida más años de los tuyos sale de la cola y va a «Filtradas». Este margen sólo separa ahí lo que se te escapa «por poco» de lo que queda «lejos».</span>
          <input type="number" id="c-marg" min="0" step="0.5" value="${c.margen_anios==null?MARGEN_DEF:c.margen_anios}"></div>
        <div class="cf full"><label class="chk"><input type="checkbox" id="c-pub" ${c.exigir_salario_publicado?'checked':''}>Sólo ofertas con el salario publicado (descarta las estimadas)</label></div>
        <div class="cf"><label for="c-ven">Ventana de búsqueda (horas)</label>
          <span class="h">Se busca desde la última ejecución con éxito, con este mínimo. Si un día falla, la siguiente recupera lo perdido.</span>
          <input type="number" id="c-ven" min="1" step="1" value="${c.ventana_horas==null?24:c.ventana_horas}"></div>
        <div class="cf"><label>Fuentes activas</label>
          <div style="display:flex;flex-direction:column;gap:6px;margin-top:4px">${chks('fuentes',FUENTES_POS,c.fuentes||[])}</div></div>
      </div></fieldset>
    </div>
    <div class="foot">
      <span class="pt" id="cfgmsg" style="margin-right:auto;font-size:12.5px"></span>
      <button class="btn" id="cfgcancel">Cancelar</button>
      <button class="btn primary" id="cfgsave">${cfgGuardando?'Guardando…':'Guardar'}</button>
    </div>
  </div></div>`;
}
function pintaCfg(){
  const cont=document.getElementById('cfgmodal');
  cont.innerHTML = cfgAbierta ? cfgHTML() : '';
  if(!cfgAbierta) return;
  document.getElementById('cfgcancel').onclick = cierraCfg;
  document.getElementById('cfgsave').onclick = guardaCfg;
  cont.querySelector('.modal').onclick = e=>{ if(e.target===cont.querySelector('.modal')) cierraCfg(); };
}
function abreCfg(){ cfgAbierta=true; pintaCfg(); }
function cierraCfg(){ cfgAbierta=false; pintaCfg(); }
function leeMarcados(name){
  return [...document.querySelectorAll(`[data-cfg="${name}"]:checked`)].map(i=>i.value);
}
function numOnull(id){
  const v=document.getElementById(id).value.trim();
  return v==='' ? null : Number(v);
}
async function guardaCfg(){
  if(cfgGuardando) return;
  const nuevo = {
    titulos: aLista(document.getElementById('c-tit').value),
    keywords: aLista(document.getElementById('c-kw').value),
    excluir_keywords: aLista(document.getElementById('c-xkw').value),
    excluir_empresas: aLista(document.getElementById('c-xemp').value),
    solo_remoto: document.getElementById('c-rem').checked,
    areas_locales: aLista(document.getElementById('c-loc').value),
    ambitos: leeMarcados('ambitos'),
    salario_min: numOnull('c-sal'),
    exigir_salario_publicado: document.getElementById('c-pub').checked,
    anios_perfil: numOnull('c-exp'),
    margen_anios: numOnull('c-marg') != null ? numOnull('c-marg') : MARGEN_DEF,
    ventana_horas: numOnull('c-ven') || 24,
    fuentes: leeMarcados('fuentes'),
    actualizado: new Date().toISOString()
  };
  if(!nuevo.titulos.length){ document.getElementById('cfgmsg').textContent='Deja al menos un puesto objetivo.'; return; }
  if(!nuevo.fuentes.length){ document.getElementById('cfgmsg').textContent='Deja al menos una fuente activa.'; return; }
  CFG = Object.assign({},CFG_DEF,nuevo);
  cfgGuardando=true; pintaCfg();
  if(!db){ cfgGuardando=false; cierraCfg(); toast('Guardado sólo en este navegador: no hay almacenamiento compartido'); return; }
  try{
    await db.doc('config/filtros').set(CFG);
    cfgGuardando=false; cierraCfg(); toast('Configuración guardada. Se aplica en la próxima ejecución.');
  }catch(e){
    cfgGuardando=false; pintaCfg();
    document.getElementById('cfgmsg').textContent='No se ha podido guardar; inténtalo otra vez.';
  }
}

function novPill(id){
  const c = corr(id);
  if(!c) return '<span class="pt">—</span>';
  return `<span class="pill ${NOV_CLS[c.tipo]||'p-nov-acuse'}">${esc(NOV_ES[c.tipo]||c.tipo)}</span>`
       + `<br><span class="pt" style="font-size:11.5px">${esc(c.fecha||'')}</span>`;
}
function novDetalle(r){
  const c = corr(r.id), e = st(r.id);
  if(!c) return '';
  const link = c.threadId
    ? `<p style="margin-top:6px;font-size:12.5px"><a href="https://mail.google.com/mail/u/0/#all/${esc(c.threadId)}" target="_blank" rel="noopener">Abrir el hilo en Gmail &rarr;</a></p>` : '';
  const sug = (c.tipo==='rechazo' && e.fase!=='rechazada')
    ? `<p class="note" style="margin-top:7px"><b>Sugerencia.</b> Este correo parece un rechazo. Si lo es, pon la fase en \u00abRechazada\u00bb y dejar\u00e1 de contar como proceso vivo.</p>` : '';
  return `<div class="dsec"><p class="dh">Novedad en el correo</p><div class="novbox">
    <p><span class="pill ${NOV_CLS[c.tipo]||'p-nov-acuse'}">${esc(NOV_ES[c.tipo]||c.tipo)}</span>
       <span class="pt">${esc(c.fecha||'')}${c.remitente?' \u00b7 '+esc(c.remitente):''}</span></p>
    <p style="margin-top:5px"><b>${esc(c.asunto||'')}</b></p>
    ${c.extracto?`<p class="note" style="margin-top:4px">${esc(c.extracto)}</p>`:''}
    ${link}${sug}</div></div>`;
}
function huerfanasHTML(){
  if(vista!=='aplicada') return '';
  const h = (CORREO['_huerfanas']||{}).lista || [];
  if(!h.length) return '';
  const li = h.map(x=>`<li><b>${esc(x.empresa||'')}</b>${x.puesto?' \u2014 '+esc(x.puesto):''}${x.fecha?` <span class="pt">(${esc(x.fecha)})</span>`:''}</li>`).join('');
  return `<div class="huerf"><p><b>En tu correo hay ${h.length} candidatura${h.length===1?'':'s'} que no est\u00e1${h.length===1?'':'n'} marcada${h.length===1?'':'s'} como aplicada aqu\u00ed.</b> Si alguna corresponde a una oferta del radar, \u00e1brela y pulsa \u00abMarcar como aplicada\u00bb.</p><ul>${li}</ul></div>`;
}

function brechaHTML(r){
  const b = r.brecha||[];
  if(!b.length) return '<div class="tags"><span class="tag">Sin huecos relevantes</span></div>';
  const tags = b.map(x=>`<span class="tag ${x.nivel}" title="${esc(x.nota)}">${esc(x.etiqueta)}</span>`).join('');
  const estudiar = b.filter(x=>x.nivel!=='lento');
  const lista = estudiar.length
    ? `<ul class="brecha-nota">${estudiar.map(x=>`<li><b>${esc(x.etiqueta)}</b> <span class="pt">(${x.nivel==='rapido'?'días':'semanas'})</span> — ${esc(x.nota)}</li>`).join('')}</ul>`
    : '';
  return `<div class="tags">${tags}</div>${lista}
    <p class="note" style="margin-top:7px">En verde y ámbar, lo que merece la pena repasar antes de una posible entrevista. En rojo, lo que no es realista cubrir a tiempo: mejor preparar una respuesta honesta que improvisar.</p>`;
}

function detailHTML(r){
  const e = st(r.id);
  const strs = r.fuertes.map(s=>`<span class="tag str">${esc(s)}</span>`).join('');
  return `<tr class="detail"><td colspan="${cols().length+1}"><div class="dwrap">
    ${r.alerta?`<p class="alert"><b>Aviso.</b> ${esc(r.alerta)}</p>`:''}
    <div class="dgrid">
      <div>
        <div class="dsec"><p class="dh">Titular del CV adaptado</p><p class="note"><b>${esc(r.titular)}</b></p></div>
        <div class="dsec"><p class="dh">Lo que juega a tu favor</p><div class="tags">${strs}</div></div>
        <div class="dsec"><p class="dh">Requisitos que no cubres</p>${brechaHTML(r)}</div>
        <div class="dsec"><p class="dh">De dónde sale el salario</p><p class="note">${esc(r.salBase)}</p></div>
        <div class="dsec"><p class="dh">Años de experiencia</p><p class="note">${esc(notaExp(r))}</p></div>
        <div class="dsec">
          <p class="dh">Seguimiento</p>
          <div class="track">
            ${e.estado==='aplicada'
              ? `<select class="fase" data-fase="${r.id}" aria-label="Fase del proceso">${FASES.map(f=>`<option value="${f}" ${e.fase===f?'selected':''}>${FASE_ES[f]}</option>`).join('')}</select>
                 <span class="pt" style="font-size:12.5px">Aplicada el ${esc(e.fechaAplicacion||hoy())}</span>
                 <button class="btn" data-unapply="${r.id}" style="padding:6px 12px;font-size:12.5px">Quitar de aplicadas</button>`
              : `<button class="btn" data-apply="${r.id}">Marcar como aplicada</button>`}
            <span class="saved" id="saved-${r.id}"></span>
          </div>
          <textarea class="notas" data-notas="${r.id}" placeholder="Notas: con quién has hablado, qué te dijeron, siguiente paso…">${esc(e.notas||'')}</textarea>
        </div>
        ${novDetalle(r)}
        <div class="actions">
          <a class="btn primary" href="${esc(r.url)}" target="_blank" rel="noopener">Aplicar en ${esc(r.fuente)} →</a>
          <button class="btn" data-cv="${r.id}">Generar CV adaptado (PDF)</button>
        </div>
        <p class="hint">El CV se arma en el momento con el titular, el resumen y el orden de logros calculados para esta oferta, en su idioma y en una sola página.</p>
      </div>
      <div>
        <div class="tabs">
          <button class="tab ${tabAbierta(r.id)==='carta'?'on':''}" data-tab="carta" data-for="${r.id}">Cover letter</button>
          <button class="tab ${tabAbierta(r.id)==='mail'?'on':''}" data-tab="mail" data-for="${r.id}">Correo a RRHH</button>
        </div>
        <div id="pane-carta-${r.id}" ${tabAbierta(r.id)==='carta'?'':'hidden'}>${panelDoc(r,'carta')}</div>
        <div id="pane-mail-${r.id}" ${tabAbierta(r.id)==='mail'?'':'hidden'}>${panelDoc(r,'mail')}</div>
      </div>
    </div></div></td></tr>`;
}

const TABS={};
const tabAbierta = id => TABS[id] || 'carta';
const NOMBRE={carta:'cover letter', mail:'correo a RRHH'};
const ART={carta:'la', mail:'el'};

function panelDoc(r, kind){
  const enCurso = GEN[r.id] && GEN[r.id][kind];
  if(enCurso){
    return `<div class="letter" id="stream-${kind}-${r.id}">${esc(enCurso.texto||'Pensando…')}</div>
      <p class="hint"><span class="dot"></span> Generando ${ART[kind]} ${NOMBRE[kind]} con Claude…
      <button class="btn" data-cancel="${kind}" data-id="${r.id}" style="padding:4px 10px;font-size:12px;margin-left:6px">Cancelar</button></p>`;
  }
  const guardado = (DOCS[r.id]||{})[kind];
  if(guardado && guardado.texto){
    const f = guardado.generado ? new Date(guardado.generado).toLocaleString('es-ES',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
    return `<div class="letter">${esc(guardado.texto)}</div>
      <div class="actions" style="margin-top:10px">
        <button class="btn" data-copy="${kind}" data-id="${r.id}">Copiar</button>
        <button class="btn" data-dlpdf="${kind}" data-id="${r.id}">Descargar PDF</button>
        <button class="btn" data-dl="${kind}" data-id="${r.id}">.txt</button>
        <button class="btn" data-gen="${kind}" data-id="${r.id}">Regenerar</button>
      </div>
      <p class="hint">${f?('Generado el '+esc(f)+'. '):''}${kind==='mail'?'Sustituye <b>[nombre]</b> por la persona de RRHH; si no sabes quién es, borra el nombre y deja el saludo.':'Repásalo antes de enviarlo: es un borrador, no un envío automático.'}</p>`;
  }
  return `<div class="vacio">
      <p>Aún no has generado ${ART[kind]} ${NOMBRE[kind]} de esta oferta.</p>
      <button class="btn primary" data-gen="${kind}" data-id="${r.id}">Generar ${NOMBRE[kind]}</button>
      <p class="hint">Se escribe en el momento con tu perfil real y el texto de esta oferta, y se guarda aquí para que no haya que repetirlo.</p>
    </div>`;
}

const REGLAS = `Escribes en nombre de __NOMBRE__, que se está presentando a una oferta de empleo. Reglas que no puedes saltarte:
- NUNCA inventes experiencia, tecnología, herramienta, empresa ni titulación que no aparezca en el PERFIL. Si la oferta pide algo que él no tiene, no lo insinúes.
- Usa logros concretos del PERFIL, con sus cifras tal y como están escritas.
- Nombra de forma explícita el hueco principal (el requisito de más peso que no cubre) en lugar de esconderlo: un reclutador sénior detecta el maquillaje.
- Lenguaje natural y directo, primera persona, sin adjetivos de relleno ("apasionado", "proactivo", "sinergia") ni frases hechas de plantilla.
- Escribe en el idioma que se te indique y devuelve SOLO el texto pedido, sin comentarios ni markdown.

CÓMO ESCRIBE ÉL (perfil de voz sacado de correos que ha escrito de verdad; respétalo):
- Saluda por el nombre de pila cuando lo sepas, sin fórmulas: «Buenos días, Ana.» o «Hi Ana,». Si no hay nombre, «Buenos días.» / «Hello,». NUNCA «Estimado/a», «Dear», «A quien corresponda».
- En español TUTEA siempre, también escribiendo en frío. Nada de «usted» ni de «quedo a la espera de su respuesta».
- Primera línea al grano, sin anunciar lo que vas a decir. Él escribe «Me presento: soy Íñigo Fernández, ingeniero informático especializado en IA y Ciencia de Datos.» o «Just one thing.», no «Me dirijo a ustedes con el fin de».
- Párrafos de dos a cuatro frases, en prosa. Nunca listas ni viñetas.
- Cuando elogia a la empresa, elogia algo concreto que ha visto en la oferta o en la compañía. El entusiasmo genérico no suena a él.
- Un paréntesis con un apunte personal le pega mucho, pero sólo uno y sólo si aporta.
- Al nombrar el hueco, lo dice y sigue: honesto y sin dramatizar, sin disculparse de más.
- Una exclamación como mucho, y sólo al despedirse. Cero emojis.
- Cierres suyos: «Un saludo,» · «Muchas gracias de antemano, quedo a tu disposición.» · «Cualquier cosa me dices.» · «Best,» · «Regards.» · «Thank you very much.»
- Firma con el nombre de pila y punto: «Íñigo.»
- Prohibidas por sonar a plantilla: «sinergia», «valor añadido», «no dudes en», «apasionado por», «altamente motivado», «encaje perfecto».
- Prueba final: ¿podría haberlo escrito él en cinco minutos? Si suena a carta modelo, sobra la mitad.`;

function ofertaTxt(r){
  return `Empresa: ${r.empresa}
Puesto: ${r.puesto}
Ubicación y modalidad: ${r.ubicacion} · ${r.modalidad} (${r.ambito})
Salario: ${r.salMin}–${r.salMax} € (${r.salOrigen}). ${r.salBase}
Titular con el que se presenta: ${r.titular}
Resumen profesional adaptado a esta oferta: ${r.resumen}
Requisitos de la oferta por peso: ${r.reqs.join('; ')}
Puntos fuertes que sí cubre: ${(r.fuertes||[]).join('; ') || '—'}
Huecos (NO los cubre; el principal va nombrado en el texto): ${(r.huecos||[]).join('; ') || '—'}
${r.alerta ? 'Aviso sobre esta oferta: '+r.alerta : ''}`;
}

function prompt(r, kind){
  const idioma = r.idioma==='es' ? 'español' : 'inglés';
  const tarea = kind==='carta'
    ? `Escribe la COVER LETTER en ${idioma}: saludo a la empresa, dos párrafos como máximo y despedida con su nombre. El primer párrafo conecta un logro concreto suyo con lo que pide la oferta; el segundo dice por qué esa empresa o ese producto en particular y nombra el hueco principal con naturalidad. Sin asunto y sin encabezado de datos de contacto.`
    : `Escribe el CORREO A RRHH en ${idioma}. Formato exacto: primera línea "Asunto: ..." (o "Subject: ..." en inglés), línea en blanco, saludo usando el marcador literal [nombre], dos párrafos y firma con su nombre, teléfono, email y LinkedIn. Párrafo 1: quién es y el logro concreto que conecta con ese puesto. Párrafo 2: por qué esa empresa en particular —algo real de la oferta o de la compañía, nunca un elogio genérico— y mención al CV adjunto. Si la oferta esconde algo (cliente sin nombrar, banda salarial de otro país, país de contratación sin especificar), el correo lo pregunta. Máximo 200 palabras.`;
  return `${REGLAS}

PERFIL (datos reales, no salgas de aquí):
${JSON.stringify(PERFIL)}

OFERTA:
${ofertaTxt(r)}

TAREA: ${tarea}`;
}

async function generar(id, kind){
  const r=DATA.find(x=>x.id===id); if(!r) return;
  if(!sampleTried){ sampleTried=true; try{ sampleNs = await claude.use('sample'); }catch(e){ sampleNs=null; } }
  if(!sampleNs){ toast('La generación con Claude no está disponible en esta vista.'); return; }
  const ctrl=new AbortController();
  GEN[id]=GEN[id]||{}; GEN[id][kind]={texto:'', ctrl};
  TABS[id]=kind; render();
  const pinta = t => { const el=document.getElementById(`stream-${kind}-${id}`); if(el) el.textContent=t; };
  try{
    const res = await sampleNs(prompt(r,kind), {
      modelTier:'default', signal:ctrl.signal, cache:false,
      onText:({text})=>{ if(GEN[id]&&GEN[id][kind]){ GEN[id][kind].texto=text; pinta(text); } }
    });
    const texto=(res.text||'').trim();
    delete GEN[id][kind];
    if(!texto){ render(); toast('Claude no ha devuelto texto; vuelve a intentarlo'); return; }
    DOCS[id]=Object.assign({}, DOCS[id], {[kind]:{texto, generado:new Date().toISOString()}});
    render();
    if(db){ try{ await db.doc('docs/'+id).set(DOCS[id]); }catch(e){ toast('Generado, pero no se ha podido guardar; cópialo antes de recargar'); } }
    toast(kind==='carta'?'Cover letter generada':'Correo generado');
  }catch(e){
    delete GEN[id][kind]; render();
    const c=e&&e.code;
    if(c==='cancelled') return;
    if(c==='not_granted') toast('No has dado permiso para generar con Claude');
    else if(c==='rate_limited') toast('Demasiadas peticiones seguidas; espera un momento');
    else toast('No se ha podido generar el texto');
  }
}

function renderViews(){
  const enCurso = DATA.filter(r=>st(r.id).estado==='aplicada' && esFaseAplicada(st(r.id).fase)).length;
  const respondidas = DATA.filter(r=>st(r.id).estado==='aplicada' && esFaseRespondida(st(r.id).fase)).length;
  const rechazadas = DATA.filter(r=>st(r.id).estado==='aplicada' && st(r.id).fase==='rechazada').length;
  const activas = DATA.filter(r=>st(r.id).estado==='activa' && !apartadaExp(r)).length;
  const descartadas = DATA.filter(r=>st(r.id).estado==='descartada').length;
  document.getElementById('views').innerHTML = [
    ['hoy','Hoy',Math.max(0, objetivo()-aplicadasDesde(lunes()))],
    ['activa','Activas',activas],['aplicada','Aplicadas',enCurso],
    ['respondida','Respondidas',respondidas],
    ['rechazada','Rechazadas',rechazadas],['descartada','Descartadas',descartadas],
    ['filtrada','Filtradas',FILTRADAS.length+apartadas().length],
    ['embudo','Embudo',(EMBUDO.total||{}).candidaturas||0]
  ].map(([v,t,c])=>`<button class="view ${vista===v?'on':''}" data-view="${v}">${t}<span class="n">${c}</span></button>`).join('');
  document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{
    if(vista===b.dataset.view) return;
    vista=b.dataset.view; openId=null;
    if(!vistaSeguimiento() && (sortK==='fase'||sortK==='fechaAplicacion'||sortK==='novedad')){ sortK='prioridad'; sortDir=-1; }
    render();
  });
}
/* Las dos vistas nuevas no son tablas de ofertas, así que se pintan aparte y
   se esconde la tabla principal en vez de forzarla a un formato que no es. */
const vistaPanel = () => vista==='filtrada' || vista==='embudo' || vista==='hoy';

function render(){
  stats();
  renderViews();
  document.getElementById('tablawrap').hidden = vistaPanel();
  document.querySelector('.toolbar').hidden = vistaPanel();
  document.getElementById('panelFiltradas').hidden = vista!=='filtrada';
  document.getElementById('panelEmbudo').hidden = vista!=='embudo';
  document.getElementById('panelHoy').hidden = vista!=='hoy';
  if(vista==='hoy'){ renderHoy(); return; }
  if(vista==='filtrada'){ renderFiltradas(); return; }
  if(vista==='embudo'){ renderEmbudo(); return; }
  renderHead();
  const rows = filtered();
  document.getElementById('count').textContent = `${rows.length} de ${DATA.length}`;
  const tb = document.getElementById('body');
  if(!rows.length){
    const msg = vista==='aplicada' ? 'Ninguna candidatura esperando respuesta. Las que marques como aplicadas salen aquí hasta que la empresa se mueva.'
              : vista==='respondida' ? 'Ninguna candidatura con movimiento todavía. Cuando una empresa te conteste, pon la fase en «Respondida», «Entrevista» u «Oferta recibida» y saldrá aquí.'
              : vista==='rechazada' ? 'Ninguna candidatura rechazada, de momento. Cuando te digan que no, abre la oferta y pon la fase en «Rechazada»: saldrá aquí y dejará de contar como proceso vivo.'
              : vista==='descartada' ? 'No has descartado ninguna oferta. Las que descartes con la ✕ aparecerán aquí y podrás recuperarlas.'
              : 'Ninguna oferta cumple estos filtros.';
    tb.innerHTML=`<tr><td colspan="${cols().length+1}" class="empty">${msg}</td></tr>`; bind(); return; }
  tb.innerHTML = rows.map(r=>{
    const rem = r.zona==='remoto';
    const det = openId===r.id ? detailHTML(r) : '';
    const e = st(r.id);
    const extra = vistaSeguimiento()
      ? `<td><span class="pill ${e.fase==='rechazada'?'p-f-rechazada':(e.fase==='oferta'?'p-f-oferta':'p-fase')}">${esc(FASE_ES[e.fase]||'Aplicada')}</span></td>
         <td class="num pt">${esc(e.fechaAplicacion||'—')}</td>
         <td class="num">${novPill(r.id)}</td>` : '';
    const accion = vista==='descartada'
      ? `<td><button class="rebtn" data-restore="${r.id}">Recuperar</button></td>`
      : `<td><button class="xbtn" data-discard="${r.id}" title="Descartar esta oferta" aria-label="Descartar ${esc(r.empresa)}">✕</button></td>`;
    return `<tr class="r ${openId===r.id?'open':''}" data-id="${r.id}">
      <td class="co">${esc(r.empresa)}</td>
      <td class="pt">${esc(r.puesto)}</td>
      ${extra}
      <td><span class="pill ${r.ambito==='Internacional'?'p-int':(r.ambito==='España'?'p-es':'p-loc')}">${esc(r.ambito)}</span></td>
      <td><span class="pill ${FAMILIAS_FOCO.has(r.familia)?'p-fam-foco':'p-fam-otro'}">${esc(FAMILIA_ES[r.familia]||r.familia)}</span></td>
      <td class="pt">${esc(r.ubicacion)}</td>
      <td><span class="pill ${rem?'p-rem':'p-hib'}">${esc(r.modalidad)}</span></td>
      <td><span class="pill p-lang">${r.idioma==='es'?'ES':'EN'}</span></td>
      <td class="pt">${esc(r.fuente)}</td>
      <td class="num pt">${esc(r.publicada)}</td>
      <td class="num"><b>${eur(r.salMedio)}</b><br><span class="pt" style="font-size:11.5px">${eur(r.salMin)} – ${eur(r.salMax)}</span></td>
      <td><span class="pill ${r.salOrigen==='publicado'?'p-pub':'p-est'}">${r.salOrigen==='publicado'?'Publicado':'Estimado'}</span></td>
      <td class="num pt">${r.scoreOrig.toFixed(1)} %</td>
      <td><div class="meter"><span class="mbar"><i style="width:${r.scoreAdap}%"></i></span><span class="num"><b>${r.scoreAdap.toFixed(1)} %</b></span></div></td>
      <td class="num"><span class="delta">+${r.delta.toFixed(1)} pp</span><br><span class="pt" style="font-size:11.5px">+${r.mejora.toFixed(1)} %</span></td>
      ${accion}
    </tr>${det}`;
  }).join('');
  document.getElementById('aviso').innerHTML = (dbFallo
    ? '<p class="offline">El almacenamiento compartido no está disponible en esta vista, así que lo que descartes o marques como aplicado se guarda solo en este navegador y no viajará a otros dispositivos.</p>'
    : '') + huerfanasHTML();
  bind();
}

function bind(){
  document.querySelectorAll('[data-ficha]').forEach(b=>b.onclick=()=>{
    vista='activa'; openId=b.dataset.ficha; render();
    const tr=document.querySelector(`tr.r[data-id="${openId}"]`);
    if(tr) tr.scrollIntoView({block:'center'});
  });
  document.querySelectorAll('tr.r').forEach(tr=>tr.onclick=e=>{
    if(e.target.closest('a,button')) return;
    openId = openId===tr.dataset.id ? null : tr.dataset.id; render();
  });
  document.querySelectorAll('[data-dl]').forEach(b=>b.onclick=()=>download(b.dataset.id,b.dataset.dl));
  document.querySelectorAll('[data-cv]').forEach(b=>b.onclick=()=>generarCV(b.dataset.cv));
  document.querySelectorAll('[data-dlpdf]').forEach(b=>b.onclick=()=>descargarPdf(b.dataset.id,b.dataset.dlpdf));
  document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{
    const d=(DOCS[b.dataset.id]||{})[b.dataset.copy];
    if(!d||!d.texto){ toast('Genera el texto primero'); return; }
    try{ await navigator.clipboard.writeText(d.texto); toast('Copiado al portapapeles'); }
    catch(e){ toast('No se ha podido copiar; selecciona el texto a mano'); }
  });
  document.querySelectorAll('[data-gen]').forEach(b=>b.onclick=()=>generar(b.dataset.id, b.dataset.gen));
  document.querySelectorAll('[data-cancel]').forEach(b=>b.onclick=()=>{
    const g=(GEN[b.dataset.id]||{})[b.dataset.cancel];
    if(g&&g.ctrl) g.ctrl.abort();
    delete GEN[b.dataset.id][b.dataset.cancel]; render();
  });
  document.querySelectorAll('[data-discard]').forEach(b=>b.onclick=()=>{
    const id=b.dataset.discard;
    if(openId===id) openId=null;
    guardar(id,{estado:'descartada'});
    toast('Oferta descartada. La tienes en la pestaña «Descartadas».');
  });
  document.querySelectorAll('[data-restore]').forEach(b=>b.onclick=()=>{
    guardar(b.dataset.restore,{estado:'activa'}); toast('Oferta recuperada');
  });
  document.querySelectorAll('[data-apply]').forEach(b=>b.onclick=()=>{
    guardar(b.dataset.apply,{estado:'aplicada', fase:'aplicada', fechaAplicacion:hoy()});
    toast('Marcada como aplicada. La sigues en la pestaña «Aplicadas».');
  });
  document.querySelectorAll('[data-unapply]').forEach(b=>b.onclick=()=>{
    guardar(b.dataset.unapply,{estado:'activa', fase:null, fechaAplicacion:null}); toast('Devuelta a activas');
  });
  document.querySelectorAll('[data-fase]').forEach(sel=>sel.onchange=()=>{
    guardar(sel.dataset.fase,{fase:sel.value});
  });
  document.querySelectorAll('[data-notas]').forEach(ta=>{
    let t; ta.oninput=()=>{ clearTimeout(t); t=setTimeout(()=>{
      const id=ta.dataset.notas, pos=ta.selectionStart;
      guardar(id,{notas:ta.value});
      const nuevo=document.querySelector(`[data-notas="${id}"]`);
      if(nuevo){ nuevo.focus(); try{ nuevo.setSelectionRange(pos,pos); }catch(e){} }
    }, 700); };
  });
  document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{
    const id=b.dataset.for, which=b.dataset.tab;
    TABS[id]=which;
    b.parentElement.querySelectorAll('.tab').forEach(x=>x.classList.toggle('on',x===b));
    document.getElementById('pane-carta-'+id).hidden = which!=='carta';
    document.getElementById('pane-mail-'+id).hidden  = which!=='mail';
  });
}

let dl=null, dlTried=false;
function slug(t){ return String(t).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^A-Za-z0-9]+/g,'_').replace(/_+/g,'_').replace(/^_|_$/g,'').slice(0,38); }
async function download(id,kind){
  const r=DATA.find(x=>x.id===id);
  const d=(DOCS[id]||{})[kind];
  if(!d||!d.texto){ toast('Genera el texto primero'); return; }
  await guardarArchivo((kind==='carta'?'Carta_':'Correo_')+slug(r.empresa)+'__'+slug(r.puesto)+'.txt',
                       new TextEncoder().encode(d.texto));
}

async function guardarArchivo(name, data){
  if(!dlTried){ dlTried=true; try{ dl = await claude.use('downloads'); }catch(e){ dl=null; } }
  if(!dl){ toast('La descarga no está disponible en esta vista; copia el texto a mano.'); return; }
  try{
    await dl.save({filename:name, data});
    toast('Guardado: '+name);
  }catch(e){
    const c = e && e.code;
    if(c==='declined') toast('Descarga cancelada');
    else if(c==='rate_limited') toast('Espera un momento y vuelve a pulsar');
    else toast('No se ha podido guardar el archivo');
  }
}


/* ---------- Generación de PDF (sin dependencias: fuentes base-14, WinAnsi) ---------- */
const FW={
H:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,278,278,355,556,556,889,667,191,333,333,389,584,278,333,278,278,556,556,556,556,556,556,556,556,556,556,278,278,584,584,584,556,1015,667,667,722,722,667,611,778,722,278,500,667,556,833,722,778,667,778,722,667,611,722,667,944,667,667,611,278,278,278,469,556,333,556,556,500,556,556,278,556,556,222,222,500,222,833,556,556,556,556,333,500,278,556,500,722,500,500,500,334,260,334,584,350,556,350,222,556,333,1000,556,556,333,1000,667,333,1000,350,611,350,350,222,222,333,333,350,556,1000,333,1000,500,333,944,350,500,667,278,333,556,556,556,556,260,556,333,737,370,556,584,333,737,333,400,584,333,333,333,556,537,278,333,333,365,556,834,834,834,611,667,667,667,667,667,667,1000,722,667,667,667,667,278,278,278,278,722,722,778,778,778,778,778,584,778,722,722,722,722,667,667,611,556,556,556,556,556,556,889,500,556,556,556,556,278,278,278,278,556,556,556,556,556,556,556,584,611,556,556,556,556,500,556,500],
HB:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,278,333,474,556,556,889,722,238,333,333,389,584,278,333,278,278,556,556,556,556,556,556,556,556,556,556,333,333,584,584,584,611,975,722,722,722,722,667,611,778,722,278,556,722,611,833,722,778,667,778,722,667,611,722,667,944,667,667,611,333,278,333,584,556,333,556,611,556,611,556,333,611,611,278,278,556,278,889,611,611,611,611,389,556,333,611,556,778,556,556,500,389,280,389,584,350,556,350,278,556,500,1000,556,556,333,1000,667,333,1000,350,611,350,350,278,278,500,500,350,556,1000,333,1000,556,333,944,350,500,667,278,333,556,556,556,556,280,556,333,737,370,556,584,333,737,333,400,584,333,333,333,611,556,278,333,333,365,556,834,834,834,611,722,722,722,722,722,722,1000,722,667,667,667,667,278,278,278,278,722,722,778,778,778,778,778,584,778,722,722,722,722,667,667,611,556,556,556,556,556,556,889,556,556,556,556,556,278,278,278,278,611,611,611,611,611,611,611,584,611,611,611,611,611,556,611,556],
TR:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,250,333,408,500,500,833,778,180,333,333,500,564,250,333,250,278,500,500,500,500,500,500,500,500,500,500,278,278,564,564,564,444,921,722,667,667,722,611,556,722,722,333,389,722,611,889,722,722,556,722,667,556,611,722,722,944,722,722,611,333,278,333,469,500,333,444,500,444,500,444,333,500,500,278,278,500,278,778,500,500,500,500,333,389,278,500,500,722,500,500,444,480,200,480,541,350,500,350,333,500,444,1000,500,500,333,1000,556,333,889,350,611,350,350,333,333,444,444,350,500,1000,333,980,389,333,722,350,444,722,250,333,500,500,500,500,200,500,333,760,276,500,564,333,760,333,400,564,300,300,333,500,453,250,333,300,310,500,750,750,750,444,722,722,722,722,722,722,889,667,611,611,611,611,333,333,333,333,722,722,722,722,722,722,722,564,722,722,722,722,722,722,556,500,444,444,444,444,444,444,667,444,444,444,444,444,278,278,278,278,500,500,500,500,500,500,500,564,500,500,500,500,500,500,500,500],
TB:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,250,333,555,500,500,1000,833,278,333,333,500,570,250,333,250,278,500,500,500,500,500,500,500,500,500,500,333,333,570,570,570,500,930,722,667,722,722,667,611,778,778,389,500,778,667,944,722,778,611,778,722,556,667,722,722,1000,722,722,667,333,278,333,581,500,333,500,556,444,556,444,333,500,556,278,333,556,278,833,556,500,556,556,444,389,333,556,500,722,500,500,444,394,220,394,520,350,500,350,333,500,500,1000,500,500,333,1000,556,333,1000,350,667,350,350,333,333,500,500,350,500,1000,333,1000,389,333,722,350,444,722,250,333,500,500,500,500,220,500,333,747,300,500,570,333,747,333,400,570,300,300,333,556,540,250,333,300,330,500,750,750,750,500,722,722,722,722,722,722,1000,722,667,667,667,667,389,389,389,389,722,722,778,778,778,778,778,570,778,722,722,722,722,722,611,556,500,500,500,500,500,500,722,444,444,444,444,444,278,278,278,278,500,556,500,500,500,500,500,570,500,556,556,556,556,500,556,500],
TI:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,250,333,420,500,500,833,778,214,333,333,500,675,250,333,250,278,500,500,500,500,500,500,500,500,500,500,333,333,675,675,675,500,920,611,611,667,722,611,611,722,722,333,444,667,556,833,667,722,611,722,611,500,556,722,611,833,611,556,556,389,278,389,422,500,333,500,500,444,500,444,278,500,500,278,278,444,278,722,500,500,500,500,389,389,278,500,444,667,444,444,389,400,275,400,541,350,500,350,333,500,556,889,500,500,333,1000,500,333,944,350,556,350,350,333,333,556,556,350,500,889,333,980,389,333,667,350,389,556,250,389,500,500,500,500,275,500,333,760,276,500,675,333,760,333,400,675,300,300,333,500,523,250,333,300,310,500,750,750,750,500,611,611,611,611,611,611,889,667,611,611,611,611,333,333,333,333,722,667,722,722,722,722,722,675,722,722,722,722,722,556,611,500,500,500,500,500,500,500,667,444,444,444,444,444,278,278,278,278,500,500,500,500,500,500,500,675,500,500,500,500,500,444,500,444]};
const CP1252={'€':128,'‚':130,'ƒ':131,'„':132,'…':133,'†':134,'‡':135,'ˆ':136,'‰':137,'Š':138,'‹':139,'Œ':140,'Ž':142,'‘':145,'’':146,'“':147,'”':148,'•':149,'–':150,'—':151,'˜':152,'™':153,'š':154,'›':155,'œ':156,'ž':158,'Ÿ':159};
const FONTID={H:'F1',HB:'F2',TR:'F3',TB:'F4',TI:'F5'};
const FONTBASE=[['F1','Helvetica'],['F2','Helvetica-Bold'],['F3','Times-Roman'],['F4','Times-Bold'],['F5','Times-Italic']];

function pdfByte(ch){
  const c=ch.codePointAt(0);
  if(c===9) return 32;
  if(c>=32 && c<256) return c;
  if(CP1252[ch]!==undefined) return CP1252[ch];
  const b=ch.normalize('NFD').replace(/[^\x20-\x7e]/g,'');
  return b ? b.codePointAt(0) : 63;
}
function anchoCar(ch,f){ const t=FW[f]||FW.H, b=pdfByte(ch); return t[b]||t[63]; }
function anchoTexto(s,size,f,tc){
  let t=0, n=0;
  for(const ch of s){ t+=anchoCar(ch,f); n++; }
  return t*size/1000 + (tc||0)*Math.max(0,n-1);
}

/* Parte el texto en líneas; `fin` marca la última línea de cada párrafo (no se justifica). */
function envolver(txt,size,f,maxW,tc){
  const out=[];
  for(const para of String(txt).replace(/\r/g,'').split('\n')){
    if(!para.trim()){ out.push({s:'',fin:true}); continue; }
    const linlas=[];
    let linea='';
    for(const pal of para.trim().split(/\s+/)){
      const cand = linea ? linea+' '+pal : pal;
      if(anchoTexto(cand,size,f,tc)<=maxW){ linea=cand; continue; }
      if(linea) linlas.push(linea);
      let p=pal;
      while(anchoTexto(p,size,f,tc)>maxW && p.length>1){
        let i=1; while(i<p.length && anchoTexto(p.slice(0,i+1),size,f,tc)<=maxW) i++;
        linlas.push(p.slice(0,i)); p=p.slice(i);
      }
      linea=p;
    }
    linlas.push(linea);
    linlas.forEach((s,i)=>out.push({s, fin:i===linlas.length-1}));
  }
  while(out.length && out[out.length-1].s==='') out.pop();
  return out;
}

function bytesAscii(arr,s){ for(let i=0;i<s.length;i++) arr.push(s.charCodeAt(i)&0xff); }
function bytesTexto(arr,s){
  for(const ch of s){ const b=pdfByte(ch); if(b===40||b===41||b===92) arr.push(92); arr.push(b); }
}
const n2 = v => (Math.round(v*100)/100).toString();

/* Escribe el PDF. `paginas` es una lista de listas de elementos:
   {s,size,f,x,y,rgb,tw,tc} para texto y {linea:{x1,x2,y,rgb,ancho}} para una regla. */
function construirPdf(paginas,W,H){
  const N=paginas.length, idFont=3+2*N;
  const bytes=[], off=[];
  const obj=(id,cuerpo)=>{ off[id]=bytes.length; bytesAscii(bytes,id+' 0 obj\n'+cuerpo+'\nendobj\n'); };
  const recursos='<</Font<<'+FONTBASE.map((f,i)=>'/'+f[0]+' '+(idFont+i)+' 0 R').join('')+'>>>>';

  bytesAscii(bytes,'%PDF-1.4\n');
  obj(1,'<</Type/Catalog/Pages 2 0 R>>');
  obj(2,'<</Type/Pages/Count '+N+'/Kids['+paginas.map((_,i)=>(3+2*i)+' 0 R').join(' ')+']>>');

  paginas.forEach((items,i)=>{
    const idPag=3+2*i, idCont=idPag+1;
    obj(idPag,'<</Type/Page/Parent 2 0 R/MediaBox[0 0 '+n2(W)+' '+n2(H)+']'
      +'/Resources'+recursos+'/Contents '+idCont+' 0 R>>');
    const cs=[];
    for(const it of items){
      if(it.linea){
        const g=it.linea.rgb||[0.80,0.84,0.83];
        bytesAscii(cs,g.map(n2).join(' ')+' RG '+n2(it.linea.ancho||0.8)+' w '
          +n2(it.linea.x1)+' '+n2(it.linea.y)+' m '+n2(it.linea.x2)+' '+n2(it.linea.y)+' l S\n');
        continue;
      }
      const rgb=it.rgb||[0.07,0.09,0.10];
      bytesAscii(cs,'BT /'+(FONTID[it.f]||'F1')+' '+n2(it.size)+' Tf '
        +rgb.map(n2).join(' ')+' rg '
        +n2(it.tw||0)+' Tw '+n2(it.tc||0)+' Tc '
        +'1 0 0 1 '+n2(it.x)+' '+n2(it.y)+' Tm (');
      bytesTexto(cs,it.s);
      bytesAscii(cs,') Tj ET\n');
    }
    off[idCont]=bytes.length;
    bytesAscii(bytes,idCont+' 0 obj\n<</Length '+cs.length+'>>\nstream\n');
    for(const b of cs) bytes.push(b);
    bytesAscii(bytes,'\nendstream\nendobj\n');
  });

  FONTBASE.forEach((f,i)=>obj(idFont+i,
    '<</Type/Font/Subtype/Type1/BaseFont/'+f[1]+'/Encoding/WinAnsiEncoding>>'));

  const total=idFont+FONTBASE.length-1, inicioXref=bytes.length;
  bytesAscii(bytes,'xref\n0 '+(total+1)+'\n0000000000 65535 f \n');
  for(let i=1;i<=total;i++) bytesAscii(bytes,String(off[i]).padStart(10,'0')+' 00000 n \n');
  bytesAscii(bytes,'trailer\n<</Size '+(total+1)+'/Root 1 0 R>>\nstartxref\n'+inicioXref+'\n%%EOF\n');
  return new Uint8Array(bytes);
}

const ETIQ = {
  carta:{es:'Carta de presentación', en:'Cover letter'},
  mail: {es:'Correo a Recursos Humanos', en:'Email to HR'},
};

function pdfDoc(r, kind, texto){
  const W=595.28, H=841.89, M=64, maxW=W-2*M, S=11, LEAD=16.4;
  const idi = r.idioma==='en' ? 'en' : 'es';
  const fecha = new Date().toLocaleDateString(idi==='en'?'en-GB':'es-ES',{day:'numeric',month:'long',year:'numeric'});

  const paginas=[]; let pag=[]; let y=H-M;
  function nuevaPagina(){ paginas.push(pag); pag=[]; y=H-M; }
  function avanzar(dy){ y-=dy; if(y<M){ nuevaPagina(); y-=dy; } }
  function poner(s,size,f,gris){ pag.push({s,size,f,x:M,y,rgb:gris?[0.44,0.50,0.49]:[0.07,0.09,0.10]}); }

  avanzar(15);
  poner(CONTACTO.nombre, 14.5, 'HB', false);
  avanzar(13.5);
  poner([CONTACTO.ciudad,CONTACTO.email,CONTACTO.tel,CONTACTO.linkedin].join('  ·  '), 8.6, 'H', true);
  avanzar(11);
  pag.push({linea:{x1:M, x2:W-M, y, rgb:[0.80,0.84,0.83], ancho:0.8}});
  avanzar(21);
  poner(r.empresa+'  ·  '+r.puesto, 10.8, 'HB', false);
  avanzar(12.5);
  poner(ETIQ[kind][idi]+'  ·  '+fecha, 8.8, 'H', true);
  avanzar(23);

  for(const l of envolver(texto,S,'H',maxW,0)){
    if(l.s===''){ avanzar(LEAD*0.6); continue; }
    avanzar(LEAD); poner(l.s,S,'H',false);
  }
  paginas.push(pag);
  return construirPdf(paginas,W,H);
}

/* ---------- CV adaptado, generado en el momento ----------
   Reproduce el CV que antes construía `generar_docs.py` con Chromium: mismo
   contenido, mismo orden y una sola página, bajando el cuerpo de letra hasta
   que cabe. Todo lo que se imprime sale de CV (el perfil real) y de la fila. */
const PX = 0.75;                      // 1 px CSS = 0.75 pt
const CV_ANCHO = 595.28, CV_ALTO = 841.89;
const CV_PADX = 34.02, CV_PADY = 25.51;   // 12 mm / 9 mm
const CV_LH = 1.36;   // más aire entre líneas: el CV corto ya no necesita apretar

function cvBloques(r, FS){
  const idi = r.idioma==='en' ? 'en' : 'es';
  const L  = CV.labels[idi];
  const B  = idi==='en' ? CV.bullets_en : CV.bullets_es;
  const SK_ALL = idi==='en' ? CV.skills_en  : CV.skills_es;
  const fam = CV.orden[r.familia] ? r.familia : 'backend';
  const oo = CV.orden[fam][0], vv = CV.orden[fam][1];
  const skCfg = CV.orden_skills[fam];
  const SK = SK_ALL[skCfg.variante];
  const tfmB = B[CV.tfm_variant[fam] || 'M1a'];
  const tfgB = B[CV.tfg_variant[fam] || 'G1a'];
  const nombre = idi==='en' ? CV.contacto.nombre_en : CV.contacto.nombre_es;
  const ciudad = idi==='en' ? CV.contacto.ciudad_en : CV.contacto.ciudad_es;
  const bl=[];
  const h2 = t => bl.push({s:t, size:9.4, f:'TB', mt:9*PX, mb:3.5*PX, tc:0.08*9.4,
                           regla:{pt:1.5*PX, rgb:[0.60,0.60,0.60], ancho:0.6}});
  const jt = (t,size) => bl.push({s:t, size:size||9.7, f:'TB', mt:4*PX});
  const jl = t => bl.push({s:t, size:8.8, f:'TI', mb:3*PX, rgb:[0.33,0.33,0.33]});

  bl.push({s:nombre, size:15.5, f:'TB', mb:1*PX});
  bl.push({s:r.titular, size:10.4, f:'TR', mb:3*PX});
  const contacto = [ciudad,CV.contacto.tel,CV.contacto.email,CV.contacto.linkedin];
  if(CV.contacto.github) contacto.push(CV.contacto.github);   // vacío hasta que haya repos que enseñar
  bl.push({s:contacto.join(' · '),
           size:8.7, f:'TR', mb:6*PX, regla:{pt:5*PX, rgb:[0.73,0.73,0.73], ancho:0.75}});

  h2(L.resumen);
  bl.push({s:r.resumen, size:FS, f:'TR', mb:3.5*PX, just:true});

  h2(L.exp);
  jt(L.o_tit); jl(L.o_loc);
  bl.push({items:oo.map(k=>B[k]), size:FS, f:'TR', mb:3*PX, just:true});
  jt(L.v_tit); jl(L.v_loc);
  bl.push({items:vv.map(k=>B[k]), size:FS, f:'TR', mb:3*PX, just:true});

  h2(L.form);
  jt(L.m_tit); jl(L.m_sub);
  /* Si el bullet de logro ya nombra la tesis, la línea del título sobra: decía
     dos veces lo mismo y se comía una línea de cada dos. Se mira sobre el texto
     del propio bullet para que siga valiendo si algún día se reescribe. */
  const nombraTesis = t => /\bTFM\b|\bTFG\b|Trabajo de Fin|Master'?s Thesis|Bachelor'?s Thesis/i.test(t||'');
  if(!nombraTesis(tfmB)) bl.push({s:L.m_tfm, size:8.8, f:'TR', mb:1.5*PX, just:true});
  bl.push({items:[tfmB], size:8.8, f:'TR', mb:3.5*PX, just:true});
  jt(L.g_tit); jl(L.g_sub);
  if(!nombraTesis(tfgB)) bl.push({s:L.g_tfg, size:8.8, f:'TR', mb:1.5*PX, just:true});
  bl.push({items:[tfgB], size:8.8, f:'TR', mb:3.5*PX, just:true});
  jt(L.compl, 9.4);
  bl.push({items:L.compl_items, size:8.8, f:'TR', mt:0, mb:3*PX});

  h2(L.skills);
  for(const s of skCfg.orden) bl.push({s:SK[s], size:FS, f:'TR', mb:2*PX});

  h2(L.lid);
  bl.push({s:L.lid_txt, size:FS, f:'TR', mb:3.5*PX, just:true});
  h2(L.idi);
  bl.push({s:L.idi_txt, size:FS, f:'TR', mb:3.5*PX, just:true});
  return bl;
}

function cvLinea(l, b, x, y, maxW){
  const it={s:l.s, size:b.size, f:b.f, x, y, rgb:b.rgb, tc:b.tc||0};
  if(b.just && !l.fin){
    const n=(l.s.match(/ /g)||[]).length;
    const hueco=maxW-anchoTexto(l.s,b.size,b.f,b.tc||0);
    if(n>0 && hueco>0 && hueco < maxW*0.25) it.tw=hueco/n;
  }
  return it;
}

function cvDisponer(bl, medir){
  const maxW = CV_ANCHO-2*CV_PADX, sangria = 13*PX;
  let y = CV_ALTO-CV_PADY, prevMB = 0;
  const items=[];
  for(const b of bl){
    y -= Math.max(prevMB, b.mt||0);          // los márgenes contiguos se solapan, como en CSS
    if(b.items){
      for(const t of b.items){
        const ls=envolver(t,b.size,b.f,maxW-sangria,0);
        ls.forEach((l,i)=>{
          y -= b.size*CV_LH;
          if(medir) return;
          if(i===0) items.push({s:'•', size:b.size, f:b.f, x:CV_PADX+2.5, y});
          items.push(cvLinea(l,b,CV_PADX+sangria,y,maxW-sangria));
        });
      }
    }else{
      for(const l of envolver(b.s,b.size,b.f,maxW,b.tc||0)){
        y -= b.size*CV_LH;
        if(!medir) items.push(cvLinea(l,b,CV_PADX,y,maxW));
      }
      if(b.regla){
        y -= b.regla.pt;
        if(!medir) items.push({linea:{x1:CV_PADX, x2:CV_ANCHO-CV_PADX, y, rgb:b.regla.rgb, ancho:b.regla.ancho}});
      }
    }
    prevMB = b.mb||0;
  }
  return {alto:(CV_ALTO-CV_PADY)-y, items};
}

function pdfCV(r){
  const util = CV_ALTO-2*CV_PADY;
  let FS = 8.1;
  for(const fs of [10.5,10.2,9.9,9.6,9.3,9.0,8.7,8.4,8.1]){
    if(cvDisponer(cvBloques(r,fs),true).alto <= util){ FS=fs; break; }
  }
  return construirPdf([cvDisponer(cvBloques(r,FS),false).items], CV_ANCHO, CV_ALTO);
}

function nombreCV(r){ return 'CV_'+slug(r.empresa)+'__'+slug(r.puesto)+'.pdf'; }

async function generarCV(id){
  const r=DATA.find(x=>x.id===id); if(!r) return;
  let bytes;
  try{ bytes=pdfCV(r); }
  catch(e){ toast('No se ha podido construir el CV'); return; }
  await guardarArchivo(nombreCV(r), bytes);
}

async function descargarPdf(id,kind){
  const r=DATA.find(x=>x.id===id);
  const d=(DOCS[id]||{})[kind];
  if(!d||!d.texto){ toast('Genera el texto primero'); return; }
  let bytes;
  try{ bytes=pdfDoc(r,kind,d.texto); }
  catch(e){ toast('No se ha podido construir el PDF; descárgalo en .txt'); return; }
  await guardarArchivo((kind==='carta'?'Carta_':'Correo_')+slug(r.empresa)+'__'+slug(r.puesto)+'.pdf', bytes);
}


let tt;
function toast(m){ const t=document.getElementById('toast'); t.textContent=m; t.classList.add('on');
  clearTimeout(tt); tt=setTimeout(()=>t.classList.remove('on'),3200); }

const MOT_CLS={salario:'p-mot-salario',modalidad:'p-mot-modalidad',ambito:'p-mot-ambito',experiencia:'p-mot-experiencia'};
const MOT_ES={salario:'Salario',modalidad:'Modalidad',ambito:'Ámbito',experiencia:'Experiencia',otro:'Otro'};

/* Lo que el filtro aparta. Existe porque un descarte silencioso no se puede
   discutir: si el mínimo de salario o los años están mal puestos, aquí se ve.
   Dos bloques distintos, y la diferencia importa:
     - las apartadas AL ENTRAR (colección `filtradas`) no llegaron al radar y no
       tienen ficha ni puntuación;
     - las apartadas POR AÑOS siguen en `ofertas` con todo: sólo se las quita de
       la cola, y vuelven en cuanto se toca el margen en «Configuración». */
function tablaExperiencia(){
  const filas = apartadas().sort((a,b)=>a.aniosMin-b.aniosMin || b.foco-a.foco);
  if(!filas.length) return '';
  const justo = filas.filter(r=>ajusteExp(r)==='justo').length;
  const m = margenExp();
  return `<h4>Apartadas por años de experiencia (${filas.length})</h4>
    <p class="lede" style="margin-bottom:12px">Tu CV suma <b>${aniosMios()} años</b> y estas piden más, así que salen de la cola. ${justo} se te escapan «por poco» —dentro de tu margen de ${m} ${m===1?'año':'años'}—: si una de ésas te interesa de verdad, el camino es el correo directo nombrando el hueco, porque por el formulario filtra la máquina. <b>No se ha borrado ninguna</b>: siguen con su ficha entera, y suben tus años en «Configuración» (o pasa el tiempo, que se recalculan del CV) y vuelven solas a la cola.</p>
    <table class="ptab">
      <thead><tr><th>Empresa</th><th>Puesto</th><th class="num">Pide</th><th>Distancia</th><th>Familia</th><th class="num">Salario</th><th></th></tr></thead>
      <tbody>${filas.map(r=>`<tr>
        <td><b>${esc(r.empresa)}</b></td>
        <td class="pt">${esc(r.puesto)}</td>
        <td class="num">${r.aniosMin} años</td>
        <td><span class="pill p-exp-${ajusteExp(r)}">${EXP_ES[ajusteExp(r)]}</span></td>
        <td class="pt">${esc(FAMILIA_ES[r.familia]||r.familia)}</td>
        <td class="num">${eur(r.salMedio)}</td>
        <td style="white-space:nowrap"><button class="rebtn" data-ficha="${r.id}">Ficha</button>
            <a class="btn" href="${esc(r.url)}" target="_blank" rel="noopener" style="padding:4px 9px;font-size:12px">Ver</a></td>
      </tr>`).join('')}</tbody>
    </table>`;
}

function tablaIngesta(){
  if(!FILTRADAS.length) return '';
  const porMotivo={};
  FILTRADAS.forEach(f=>{ porMotivo[f.motivo||'otro']=(porMotivo[f.motivo||'otro']||0)+1; });
  const resumen=Object.entries(porMotivo).sort((a,b)=>b[1]-a[1])
    .map(([m,n])=>`${n} por ${(MOT_ES[m]||m).toLowerCase()}`).join(', ');
  return `<h4>Apartadas al entrar (${FILTRADAS.length})</h4>
    <p class="lede" style="margin-bottom:12px">${esc(resumen)}. Éstas no llegaron al radar: el filtro las paró al buscarlas, así que no tienen ficha ni puntuación. Si ves aquí demasiadas cosas buenas, baja el mínimo de salario o afloja <em>solo remoto</em>.</p>
    <table class="ptab">
      <thead><tr><th>Empresa</th><th>Puesto</th><th>Motivo</th><th>Por qué</th><th>Fuente</th><th>Fecha</th><th></th></tr></thead>
      <tbody>${FILTRADAS.map(f=>`<tr>
        <td><b>${esc(f.empresa||'—')}</b></td>
        <td class="pt">${esc(f.puesto||'—')}</td>
        <td><span class="pill ${MOT_CLS[f.motivo]||'p-mot-otro'}">${esc(MOT_ES[f.motivo]||f.motivo||'Otro')}</span></td>
        <td class="motivo">${esc(f.detalle||'')}</td>
        <td class="pt">${esc(f.fuente||'—')}</td>
        <td class="num pt">${esc(f.fecha||'—')}</td>
        <td>${f.url?`<a class="btn" href="${esc(f.url)}" target="_blank" rel="noopener">Ver</a>`:''}</td>
      </tr>`).join('')}</tbody>
    </table>`;
}

function renderFiltradas(){
  const cont=document.getElementById('panelFiltradas');
  const exp=tablaExperiencia(), ing=tablaIngesta();
  if(!exp && !ing){
    cont.innerHTML='<div class="panel"><h3>Filtradas</h3><p class="lede">Todavía no hay ninguna. Aquí van a parar las ofertas que encajan por título y por fecha pero que el filtro aparta: las que publican un salario por debajo de tu mínimo, las que el portal marca como remotas sin que la descripción lo confirme, y las que piden más años de experiencia de los que tienes. Se guardan para que puedas ver lo que el filtro te está costando y cambiarlo desde «Configuración» si se pasa de estricto.</p></div>';
    return;
  }
  cont.innerHTML=`<div class="panel">
    <h3>Filtradas</h3>
    <p class="lede">Lo que el filtro aparta, a la vista. No es una lista de descartes definitivos: es lo que te está costando la configuración actual, para que puedas cambiarla sabiendo qué te deja fuera.</p>
    ${exp}${ing}
  </div>`;
  bind();
}



/* ---------- Los años que pide la oferta contra los que tienes ----------
   Seis de tus dieciocho descartes manuales fueron por antigüedad, no por
   tecnología. `anios_min` lo escribe la tarea diaria leyendo el anuncio (y se
   rellenó hacia atrás con lo que ya estaba escrito en las alertas y notas).
   La clasificación se hace AQUÍ y no en el pipeline a propósito: así, cambiar
   tus años o el margen desde «Configuración» devuelve ofertas a la cola en el
   acto, sin esperar a la ejecución de mañana. Nada se borra nunca. */
const aniosMios = () => (CFG.anios_perfil!=null && CFG.anios_perfil>0) ? +CFG.anios_perfil : ANIOS_PERFIL;
const margenExp = () => (CFG.margen_anios!=null && CFG.margen_anios>=0) ? +CFG.margen_anios : MARGEN_DEF;

function ajusteExp(r){
  if(r.aniosMin==null) return 'desconocido';    // sin dato NUNCA se aparta una oferta
  const falta = r.aniosMin - aniosMios();
  if(falta <= 0.001) return 'encaja';
  return falta <= margenExp()+0.001 ? 'justo' : 'lejos';
}
const EXP_ES = {justo:'Por poco', lejos:'Lejos'};
function notaExp(r){
  if(r.aniosMin==null) return 'La oferta no dice cuántos pide.';
  const mios = aniosMios(), falta = Math.round((r.aniosMin-mios)*10)/10;
  if(falta<=0) return `Pide ${r.aniosMin} años y tienes ${mios}: dentro.`;
  return `Pide ${r.aniosMin} años y tienes ${mios}: te faltan ${falta}. `
       + (ajusteExp(r)==='justo' ? 'Entra en tu margen, así que se aparta de la cola pero se defiende por correo directo.'
                                 : 'Fuera de tu margen: por el formulario filtra la máquina.');
}
/* Una oferta con seguimiento no se esconde jamás: si la has aplicado o
   descartada, su ficha tiene que seguir donde estaba. */
const apartadaExp = r => st(r.id).estado==='activa' && ajusteExp(r)!=='encaja' && ajusteExp(r)!=='desconocido';
const apartadas = () => DATA.filter(apartadaExp);

/* ---------- «Hoy»: la cola de candidaturas ----------
   El cuello de botella medido el 10 sep 2026 no era encontrar ofertas (222 en el
   radar) sino mandarlas: 188 no se habían tocado nunca y salían 1,7 candidaturas
   al día. Esta pestaña existe para convertir el radar en una cola corta: seis
   ofertas, en orden de foco, con los botones al lado y un contador semanal. */
const COLA_N = 6, DIAS_VIVA = 21;

function colaHoy(){
  const suelo = +CFG.salario_min || 0;      // ni siquiera el techo de la banda llega: fuera de la cola
  return DATA.filter(r => st(r.id).estado==='activa'
                       && !apartadaExp(r)
                       && (r.dias==null || r.dias<=DIAS_VIVA)
                       && !(suelo && r.salMax < suelo))
             .sort((a,b)=>b.foco-a.foco);
}
function objetivo(){
  const v=parseInt(localStorage.getItem('radar-objetivo'),10);
  return (v>0 && v<100) ? v : OBJ_DEF;
}
function lunes(){
  const d=new Date(); const n=(d.getDay()+6)%7;      // 0 = lunes
  d.setDate(d.getDate()-n); return d.toISOString().slice(0,10);
}
function aplicadasDesde(desde){
  return Object.values(STATE).filter(s=>s.estado==='aplicada' && (s.fechaAplicacion||'')>=desde).length;
}
function pillDias(d){
  if(d==null) return '';
  const cls = d<=7 ? 'p-dias-ok' : d<=14 ? 'p-dias-tibio' : 'p-dias-frio';
  return `<span class="pill ${cls}">${d===0?'hoy':'hace '+d+' d'}</span>`;
}

function tarjetaHoy(r){
  const hueco = (r.huecos||[])[0];
  return `<div class="tarjeta">
    <div>
      <div class="co">${esc(r.empresa)}</div>
      <div class="pt">${esc(r.puesto)}</div>
    </div>
    <div class="meta">
      ${pillDias(r.dias)}
      <span class="pill ${FAMILIAS_FOCO.has(r.familia)?'p-fam-foco':'p-fam-otro'}">${esc(FAMILIA_ES[r.familia]||r.familia)}</span>
      <span class="pill ${r.salOrigen==='publicado'?'p-pub':'p-est'}">${eur(r.salMedio)}</span>
      <span class="pill ${r.ambito==='Internacional'?'p-int':'p-es'}">${esc(r.ambito)}</span>
    </div>
    <p class="por">${hueco ? 'Hueco principal: <b>'+esc(hueco)+'</b>.' : 'Cubres todos los requisitos que pide.'}${r.motivoFoco ? ' '+esc(r.motivoFoco.charAt(0).toUpperCase()+r.motivoFoco.slice(1))+'.' : ''}</p>
    <div class="acc">
      <a class="btn primary" href="${esc(r.url)}" target="_blank" rel="noopener">Abrir oferta</a>
      <button class="btn" data-cv="${r.id}">CV</button>
      <button class="btn" data-ficha="${r.id}">Ficha</button>
      <button class="btn" data-apply="${r.id}">Aplicada</button>
      <button class="xbtn" data-discard="${r.id}" title="Descartar">✕</button>
    </div>
  </div>`;
}

function renderHoy(){
  const cont=document.getElementById('panelHoy');
  const cola=colaHoy(), obj=objetivo();
  const semana=aplicadasDesde(lunes()), total=Object.values(STATE).filter(s=>s.estado==='aplicada').length;
  const pct=Math.min(100, Math.round(100*semana/obj));
  const t=EMBUDO.total||{};
  const tasa = (t.tasa_respuesta==null) ? '—' : t.tasa_respuesta.toFixed(0)+' %';
  const caducadas=DATA.filter(r=>st(r.id).estado==='activa' && r.dias!=null && r.dias>DIAS_VIVA).length;
  const cuerpo = cola.length
    ? `<div class="hoygrid">${cola.slice(0,COLA_N).map(tarjetaHoy).join('')}</div>
       <p class="hint">${cola.length} ofertas activas con menos de ${DIAS_VIVA} días. Cuando despaches estas seis, entran las seis siguientes.${caducadas?' Además hay '+caducadas+' que pasan de tres semanas: casi todas estarán cerradas, y conviene descartarlas en bloque.':''}</p>`
    : `<div class="vacio"><p>No queda ninguna oferta activa reciente. Repasa las «Activas» antiguas o espera a la cosecha de mañana.</p></div>`;
  cont.innerHTML=`<div class="panel">
    <h3>Hoy</h3>
    <p class="lede">Seis ofertas, en orden de foco, con todo lo necesario para echarlas sin salir de aquí. El foco es la prioridad de siempre menos lo que ya sabes que no llega: ofertas viejas y títulos de sénior o arquitecto. Encontrar ofertas no es el problema; mandarlas, sí.</p>
    <div class="ritmo">
      <div class="col"><span class="et">Esta semana</span><span class="cifra">${semana} / ${obj}</span>
        <span class="barra"><i style="width:${pct}%"></i></span></div>
      <div class="col"><span class="et">Objetivo semanal</span>
        <input class="objin" id="objsem" type="number" min="1" max="99" value="${obj}"></div>
      <div class="col"><span class="et">Candidaturas totales</span><span class="cifra">${total}</span></div>
      <div class="col"><span class="et">Tasa de respuesta</span><span class="cifra">${tasa}</span></div>
    </div>
    ${cuerpo}
  </div>`;
  const inp=document.getElementById('objsem');
  if(inp) inp.onchange=()=>{ try{ localStorage.setItem('radar-objetivo', String(parseInt(inp.value,10)||OBJ_DEF)); }catch(e){} render(); };
  bind();
}

/* El embudo. La pregunta que el radar no se hacía: ¿esto convierte? */
function renderEmbudo(){
  const cont=document.getElementById('panelEmbudo');
  const t=EMBUDO.total;
  if(!t || !t.candidaturas){
    cont.innerHTML='<div class="panel"><h3>Embudo</h3><p class="lede">Sin candidaturas registradas todavía. En cuanto marques ofertas como aplicadas, aquí aparece qué fuente convierte, qué familia de puesto responde y si la coincidencia del CV predice algo. Hasta cinco candidaturas por grupo no se muestran porcentajes: con menos, no significarían nada.</p></div>';
    return;
  }
  const pct=v=>v===null||v===undefined?'<span class="flaca">muestra corta</span>':`${v.toFixed(1)} %`;
  const tabla=(titulo,grupo,etiqueta)=>{
    const filas=Object.entries(grupo||{}).sort((a,b)=>b[1].candidaturas-a[1].candidaturas);
    if(!filas.length) return '';
    return `<h4>${titulo}</h4><table class="ptab">
      <thead><tr><th>${etiqueta}</th><th class="num">Cand.</th><th class="num">Avance</th><th class="num">Rechazo</th><th class="num">Sin respuesta</th><th class="num">Tasa</th></tr></thead>
      <tbody>${filas.map(([k,g])=>`<tr>
        <td>${esc(k)}</td><td class="num">${g.candidaturas}</td>
        <td class="num">${g.avances}</td><td class="num">${g.rechazos}</td>
        <td class="num">${g.sin_respuesta}</td><td class="num">${pct(g.tasa_respuesta)}</td>
      </tr>`).join('')}</tbody></table>`;
  };
  const mediana=t.dias_mediana_respuesta!==null&&t.dias_mediana_respuesta!==undefined
    ? ` La mediana hasta la primera respuesta humana es de ${t.dias_mediana_respuesta} días.` : '';
  const espera=(EMBUDO.esperando||[]).length
    ? `<h4>Las que más llevan esperando</h4><table class="ptab">
       <thead><tr><th>Empresa</th><th>Puesto</th><th class="num">Días</th></tr></thead>
       <tbody>${EMBUDO.esperando.map(e=>`<tr><td><b>${esc(e.empresa)}</b></td><td class="pt">${esc(e.puesto)}</td><td class="num">${e.dias_esperando}</td></tr>`).join('')}</tbody></table>` : '';
  const sat=(EMBUDO.saturadas||[]).length
    ? `<h4>Empresas con más peso en el radar</h4><table class="ptab">
       <thead><tr><th>Empresa</th><th class="num">En el radar</th><th class="num">Aplicadas</th><th class="num">Respuestas</th></tr></thead>
       <tbody>${EMBUDO.saturadas.map(e=>`<tr><td><b>${esc(e.empresa)}</b></td><td class="num">${e.en_radar}</td><td class="num">${e.aplicadas}</td><td class="num">${e.respuestas}</td></tr>`).join('')}</tbody></table>` : '';
  cont.innerHTML=`<div class="panel">
    <h3>Embudo</h3>
    <p class="lede">${t.candidaturas} candidaturas sobre ${EMBUDO.n_ofertas||DATA.length} ofertas en el radar: ${t.avances} con avance, ${t.rechazos} rechazadas y ${t.sin_respuesta} sin respuesta humana.${mediana} Un acuse de recibo automático no cuenta como respuesta: lo manda el ATS, no una persona. Si la tasa no cambia entre los tramos de coincidencia, es que la puntuación no está prediciendo nada y hay que cambiarla, no seguir puliéndola.</p>
    ${tabla('Por fuente',EMBUDO.por_fuente,'Fuente')}
    ${tabla('Por familia de puesto',EMBUDO.por_familia,'Familia')}
    ${tabla('Por coincidencia del CV',EMBUDO.por_tramo,'Tramo')}
    <div class="pgrid">${espera}${sat}</div>
  </div>`;
}

function stats(){
  const n=DATA.length;
  const rem=DATA.filter(r=>r.zona==='remoto').length;
  const med=Math.round(DATA.reduce((s,r)=>s+r.salMedio,0)/n);
  const best=DATA.reduce((a,b)=>a.scoreAdap>b.scoreAdap?a:b);
  const dlt=(DATA.reduce((s,r)=>s+r.delta,0)/n);
  document.getElementById('stats').innerHTML=[
   ['Ofertas','' +n,'en seguimiento'],
   ['En remoto',''+rem,`${n-rem} presenciales o híbridas en Navarra y Gipuzkoa`],
   ['Internacionales',''+DATA.filter(r=>r.ambito==='Internacional').length,'empresas de fuera que contratan desde aquí'],
   ['Foco IA/DS',''+DATA.filter(r=>FAMILIAS_FOCO.has(r.familia)).length,'AI/ML, GenAI, Computer Vision o Data Science/Eng.'],
   ['Portales',''+new Set(DATA.map(r=>r.fuente)).size,'LinkedIn, InfoJobs, Tecnoempleo, Indeed y portales remotos'],
   ['Salario medio',eur(med),'mín. filtrado: 45 000 €'],
   ['Filtradas',''+FILTRADAS.length,'apartadas por salario o modalidad sin confirmar'],
   ['Sin tocar',''+DATA.filter(r=>st(r.id).estado==='activa'&&!apartadaExp(r)).length,'activas a las que aún no has aplicado ni descartado'],
   ['Por experiencia',''+apartadas().length,`piden más de ${aniosMios()} años; están en «Filtradas»`],
   ['Mejor encaje',best.scoreAdap.toFixed(1)+' %',best.empresa],
   ['Ganancia media','+'+dlt.toFixed(1)+' pp','del CV adaptado sobre el original'],
  ].map(([k,v,n2])=>`<div class="stat"><div class="k">${k}</div><div class="v">${v}</div><div class="n">${esc(n2)}</div></div>`).join('');
}

['q','fmod','flang','famb','ffam','ffue'].forEach(id=>document.getElementById(id).oninput=render);
const fs=document.getElementById('fsal'), fsv=document.getElementById('fsalv');
fs.oninput=()=>{fsv.textContent=eur(+fs.value);render()};
const fc=document.getElementById('fsc'), fcv=document.getElementById('fscv');
fc.oninput=()=>{fcv.textContent=fc.value+' %';render()};
document.getElementById('cfgbtn').onclick=abreCfg;
document.addEventListener('keydown', e=>{ if(e.key==='Escape' && cfgAbierta) cierraCfg(); });
document.getElementById('reset').onclick=()=>{
  document.getElementById('q').value=''; document.getElementById('fmod').value='';
  document.getElementById('flang').value=''; document.getElementById('famb').value=''; document.getElementById('ffam').value=''; document.getElementById('ffue').value=''; fs.value=35000; fsv.textContent=eur(35000);
  fc.value=0; fcv.textContent='0 %'; openId=null; render();
};
fsv.textContent=eur(35000);
document.getElementById('ffue').insertAdjacentHTML('beforeend',
  [...new Set(DATA.map(r=>r.fuente))].sort().map(f=>`<option>${esc(f)}</option>`).join(''));
document.getElementById('ffam').insertAdjacentHTML('beforeend',
  [...new Set(DATA.map(r=>r.familia))].sort((a,b)=>(FAMILIA_ES[a]||a).localeCompare(FAMILIA_ES[b]||b,'es'))
    .map(f=>`<option value="${esc(f)}">${esc(FAMILIA_ES[f]||f)}</option>`).join(''));
render(); initEstado();
</script>"""

import datetime
MESES = ["enero","febrero","marzo","abril","mayo","junio","julio",
         "agosto","septiembre","octubre","noviembre","diciembre"]
_h = datetime.date.today()
FECHA = "%d de %s de %d" % (_h.day, MESES[_h.month-1], _h.year)
CONTACTO_JS = json.dumps({
  "nombre": CONTACTO["nombre_es"], "ciudad": CONTACTO["ciudad_es"],
  "email": CONTACTO["email"], "tel": CONTACTO["tel"], "linkedin": CONTACTO["linkedin"],
}, ensure_ascii=False)
out = (TPL.replace("__DATA__", DATA).replace("__PERFIL__", PERFIL).replace("__CV__", CV)
          .replace("__FILTRADAS__", FILTRADAS_JS).replace("__EMBUDO__", EMBUDO_JS)
          .replace("__ANIOS_PERFIL__", json.dumps(ANIOS_PERFIL))
          .replace("__MARGEN_DEF__", json.dumps(MARGEN_DEF))
          .replace("__CONTACTO__", CONTACTO_JS).replace("__NOMBRE__", CONTACTO["nombre_es"])
          .replace("__N__", str(len(rows))).replace("__FECHA__", FECHA))
open('out/dashboard.html','w').write(out)
print("bytes", len(out.encode()))
