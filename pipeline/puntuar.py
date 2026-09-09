# -*- coding: utf-8 -*-
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ofertas import OFERTAS
from perfil import ORIG, prominencia_adaptada

def score(o):
    tot = sum(w for _,w,_ in o["reqs"])
    orig = sum(w*ORIG.get(k,0.0) for k,w,_ in o["reqs"])
    adap = sum(w*prominencia_adaptada(k,set(o["surfaced"])) for k,w,_ in o["reqs"])
    huecos = [(l,w) for k,w,l in o["reqs"] if ORIG.get(k,0.0)==0.0]
    huecos.sort(key=lambda x:-x[1])
    fuertes = [(l,w) for k,w,l in o["reqs"] if ORIG.get(k,0.0)>=0.7]
    fuertes.sort(key=lambda x:-x[1])
    return round(100*orig/tot,1), round(100*adap/tot,1), huecos, fuertes

res=[]
for o in OFERTAS:
    so, sa, huecos, fuertes = score(o)
    res.append(dict(o, score_orig=so, score_adap=sa,
                    delta=round(sa-so,1),
                    mejora_pct=round(100*(sa-so)/so,1) if so else 0,
                    huecos=[h[0] for h in huecos[:5]],
                    fuertes=[f[0] for f in fuertes[:5]],
                    sal_medio=(o["sal_min"]+o["sal_max"])//2,
                    url=o.get('url_apply') or f"https://www.linkedin.com/jobs/view/{o['id']}/"))
res.sort(key=lambda r:-r["score_adap"])
json.dump(res, open('data/resultado.json','w'), ensure_ascii=False, indent=1)
print(f"{'EMPRESA':<28}{'PUESTO':<44}{'ORIG':>6}{'ADAP':>7}{'Δ':>6}  {'SALARIO':>17}")
for r in res:
    print(f"{r['empresa'][:27]:<28}{r['puesto'][:43]:<44}{r['score_orig']:>6}{r['score_adap']:>7}{r['delta']:>+6}  {r['sal_min']//1000:>6}k-{r['sal_max']//1000}k {r['sal_origen'][:4]}")
print("\ndescartadas por <35k:", [r['empresa'] for r in res if r['sal_medio']<35000])
