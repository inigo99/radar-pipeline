# -*- coding: utf-8 -*-
import sys, os, json, re, html, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_cv import *
from tailor import T
from ofertas import OFERTAS

RES = json.load(open('data/resultado.json'))
BY = {r['id']: r for r in RES}

from base_cv import CV_LABELS as L


CSS = """
*{box-sizing:border-box} body{font-family:"Times New Roman",Georgia,serif;font-size:__FS__pt;line-height:1.26;color:#111;margin:0}
.page{padding:9mm 12mm}
h1{font-size:15.5pt;letter-spacing:.04em;margin:0 0 1px;font-weight:700}
.role{font-size:10.4pt;color:#111;margin:0 0 3px}
.contact{font-size:8.5pt;color:#111;margin:0 0 6px;border-bottom:1px solid #bbb;padding-bottom:5px}
h2{font-size:9.2pt;letter-spacing:.08em;font-weight:700;margin:7px 0 3px;border-bottom:.8px solid #999;padding-bottom:1.5px}
p{margin:0 0 3.5px;text-align:justify}
.jt{font-weight:700;font-size:9.7pt;margin:4px 0 0}
.jl{font-size:8.8pt;color:#555;margin:0 0 3px;font-style:italic}
ul{margin:0 0 3px;padding-left:13px} li{margin:0 0 1.5px;text-align:justify}
.sk{margin:0 0 2px} .sk b{font-weight:700}
.small{font-size:8.8pt}
"""

def cv_html(o, fs=9.6):
    t = T[o['id']]; lang = o['idioma']; lx = L[lang]
    B = BULLETS_ES if lang=='es' else BULLETS_EN
    SK = SKILLS_ES if lang=='es' else SKILLS_EN
    oo, vv = ORDEN[t['familia']]
    sk_order = ORDEN_SKILLS[t['familia']]
    nombre = CONTACTO['nombre_es'] if lang=='es' else CONTACTO['nombre_en']
    ciudad = CONTACTO['ciudad_es'] if lang=='es' else CONTACTO['ciudad_en']
    e = html.escape
    def li(keys): return "".join(f"<li>{e(B[k])}</li>" for k in keys)
    skills = "".join(f'<div class="sk">{e(SK[s]).replace("&amp;","&")}</div>' for s in sk_order)
    return f"""<html><head><meta charset="utf-8"><style>{CSS.replace("__FS__", str(fs))}</style></head><body><div class="page">
<h1>{e(nombre)}</h1>
<p class="role">{e(t['titular'])}</p>
<p class="contact">{e(ciudad)} · {e(CONTACTO['tel'])} · {e(CONTACTO['email'])} · {e(CONTACTO['linkedin'])}</p>
<h2>{lx['resumen']}</h2><p>{e(t['resumen'])}</p>
<h2>{lx['exp']}</h2>
<p class="jt">{e(lx['o_tit'])}</p><p class="jl">{e(lx['o_loc'])}</p><ul>{li(oo)}</ul>
<p class="jt">{e(lx['v_tit'])}</p><p class="jl">{e(lx['v_loc'])}</p><ul>{li(vv)}</ul>
<h2>{lx['form']}</h2>
<p class="jt">{e(lx['m_tit'])}</p><p class="jl">{e(lx['m_sub'])}</p><p class="small">{e(lx['m_tfm'])}</p>
<p class="jt">{e(lx['g_tit'])}</p><p class="jl">{e(lx['g_sub'])}</p><p class="small">{e(lx['g_tfg'])}</p>
<p class="jt" style="font-size:9.4pt">{lx['compl']}</p>
<ul class="small">{"".join(f"<li>{e(i)}</li>" for i in lx['compl_items'])}</ul>
<h2>{lx['skills']}</h2>{skills}
<h2>{lx['lid']}</h2><p>{e(lx['lid_txt'])}</p>
<h2>{lx['idi']}</h2><p>{e(lx['idi_txt'])}</p>
</div></body></html>"""

_CARTA_CSS_OBSOLETO = """
body{font-family:"Times New Roman",Georgia,serif;font-size:11pt;line-height:1.5;color:#111;margin:0}
.page{padding:22mm 22mm}
.h{font-size:14pt;font-weight:700;margin:0 0 2px}
.c{font-size:9.5pt;color:#444;margin:0 0 18px;border-bottom:1px solid #bbb;padding-bottom:8px}
.to{margin:0 0 14px;font-size:10pt;color:#333}
p{margin:0 0 12px;text-align:justify}
.sig{margin-top:18px}
"""
def slug(s):
    s = re.sub(r'[^A-Za-z0-9]+','_',s.replace('ñ','n').replace('Ñ','N'))
    return re.sub(r'_+','_',s).strip('_')[:38]

async def main():
    from playwright.async_api import async_playwright
    os.makedirs('cv',exist_ok=True)
    manifest=[]
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page()
        for o in OFERTAS:
            sl = f"{slug(o['empresa'])}__{slug(o['puesto'])}"
            import subprocess
            p = f"cv/CV_{sl}.pdf"
            for fs in (9.6,9.3,9.0,8.7,8.4,8.1):
                hp=f"/tmp/cv_{o['id']}.html"; open(hp,'w').write(cv_html(o,fs))
                await pg.goto("file://"+hp)
                await pg.pdf(path=p, format="A4", print_background=True,
                             margin={"top":"0","bottom":"0","left":"0","right":"0"})
                n=subprocess.run(["pdfinfo",p],capture_output=True,text=True).stdout
                if "Pages:" in n and int([l for l in n.split(chr(10)) if l.startswith("Pages")][0].split()[1])==1:
                    break
            manifest.append(dict(id=o['id'], slug=sl, cv=f"cv/CV_{sl}.pdf"))
        await b.close()
    json.dump(manifest, open('data/manifest.json','w'), ensure_ascii=False, indent=1)
    print("generados", len(manifest), "CV en PDF")
asyncio.run(main())
