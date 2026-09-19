# -*- coding: utf-8 -*-
"""Aplica los filtros de `config/filtros` a las candidatas, en código.

Hasta el 16-sep-2026 esto se hacía a ojo: se leían las candidatas y se
descartaban a mano las que chocaban con `excluir_keywords`, `excluir_empresas`
o `salario_min`. Aparte del tiempo, dejaba huecos reales — `ij.filtrar()` y
`mf.filtrar()` nunca aplicaron `excluir_empresas`/`excluir_keywords` (sólo lo
hacía `li.filtrar()`, y sólo para LinkedIn), así que una oferta de una
intermediaria vetada que llegara por InfoJobs, Manfred o el subagente de
Tecnoempleo/Indeed sólo se caía si alguien la veía a tiempo. Este script se
aplica **después de recoger candidatas de todas las fuentes y antes de
`dedupe.py`**, así que cubre a todas por igual.

Tres comprobaciones, todas mecánicas sobre campos que ya vienen calculados
(nunca sobre HTML crudo):

  1. **`excluir_empresas`**: misma regla que ya usaba `li.filtrar()` en
     JavaScript (igualdad, o subcadena si el nombre vetado tiene más de 4
     letras) — se porta aquí tal cual, no se reinventa.
  2. **`excluir_keywords`**: subcadena sobre el título (`puesto`). Sólo el
     título: a esta altura no hay descripción completa de todas las
     candidatas (leerla entera para esto sería el mismo derroche que se quiso
     evitar), así que una palabra que sólo aparezca en el cuerpo del anuncio
     no se pilla aquí. Es la misma limitación que ya tiene `R.tituloVale()`.
  3. **`salario_min` / `exigir_salario_publicado`**: sólo sobre salario YA
     PUBLICADO (`oferta["salario"]`, el texto que saca `R.salario()`). Se
     compara la cifra MÁS ALTA que aparezca en el texto, no la más baja: ante
     la duda, mejor dejar pasar una oferta con banda ambigua que descartar una
     buena por su extremo inferior — el filtro de verdad, con la banda
     estimada de `pipeline/bandas.json`, ya llega más adelante en `puntuar.py`.
     Si `exigir_salario_publicado` es verdad y no hay ninguna cifra
     reconocible, también se descarta.

**Lo que este script NO toca, a propósito:**

  - **Modalidad** (`solo_remoto` + `areas_locales`). Para cuando una oferta
    llega aquí, `li.clasificar()`/`ij.clasificar()`/`mf.filtrar()` ya la
    han restringido a remoto/local/remoto_sin_confirmar — filtrar otra vez
    por modalidad en Python sería redundante casi siempre, y en el caso en
    que no lo fuera (alguien cambia `areas_locales` en el dashboard a una
    zona que `R.RE_LOCAL` no reconoce) no hay nada que rescatar aquí: la
    oferta nunca llegó a salir del navegador. Ver el aviso en el README.
  - **`ambitos`**. `R.ambito()` sólo devuelve la FRASE literal donde el
    anuncio habla de dónde se puede firmar — no dice si esa frase es una
    restricción («debes residir en EEUU») o una apertura («válido para
    cualquier país de la UE»); son la misma forma gramatical. Meter aquí una
    regla mecánica que adivine cuál de las dos es, es inventarse un criterio
    — y `pipeline/vocabulario.md` ya avisa de lo que cuesta un hueco
    inventado: una oferta buena descartada sin motivo real. Esto sigue
    necesitando que alguien lea la frase.

Uso:

    python pipeline/filtrar.py candidatas.json data/ok.json --filtros filtros.json

`filtros.json` es el volcado de `config/filtros` (bastan `excluir_keywords`,
`excluir_empresas`, `salario_min` y `exigir_salario_publicado`; el resto de
campos se ignoran aquí). Si no se pasa `--filtros`, no se descarta nada por
salario ni por listas de exclusión — imprime un aviso y deja pasar todo.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dedupe import sin_acentos  # reutiliza la misma normalización que dedupe.py
from estadisticas import acumula  # instrumentación de coste, ver pipeline/estadisticas.py

_RE_K = re.compile(r'(\d{1,3})\s*[kK]\b')
_RE_MIL = re.compile(r'(\d{1,3}(?:[.,]\d{3})+)')


def parsea_salario(raw):
    """La cifra anual MÁS ALTA que aparezca en el texto de salario publicado,
    en euros. `None` si no hay ninguna cifra reconocible (raw vacío o sin
    patrón). Usa el extremo alto del rango a propósito -- ver cabecera."""
    if not raw:
        return None
    texto = str(raw)
    valores = [int(m.group(1)) * 1000 for m in _RE_K.finditer(texto)]
    limpio = _RE_K.sub(' ', texto)
    valores += [int(m.group(1).replace('.', '').replace(',', ''))
                for m in _RE_MIL.finditer(limpio)]
    return max(valores) if valores else None


def _empresa_excluida(empresa, excluir_empresas):
    """Misma regla que `li.filtrar()`: igualdad, o subcadena si la vetada
    tiene más de 4 letras (para que «BBK» no case con cualquier cosa)."""
    e = sin_acentos(empresa)
    for malo in excluir_empresas or []:
        m = sin_acentos(malo)
        if not m:
            continue
        if e == m or (len(m) > 4 and m in e):
            return malo
    return None


def _keyword_excluida(puesto, excluir_keywords):
    p = sin_acentos(puesto)
    for kw in excluir_keywords or []:
        k = sin_acentos(kw)
        if k and k in p:
            return kw
    return None


def filtrar(candidatas, filtros):
    """(supervivientes, filtradas). Cada filtrada dice el motivo y el detalle,
    en el mismo formato que espera la colección `filtradas` del dashboard."""
    excluir_empresas = filtros.get("excluir_empresas") or []
    excluir_keywords = filtros.get("excluir_keywords") or []
    salario_min = filtros.get("salario_min")
    exigir_pub = bool(filtros.get("exigir_salario_publicado"))

    supervivientes, filtradas = [], []
    for cand in candidatas:
        empresa, puesto = cand.get("empresa", ""), cand.get("puesto", "")

        choque = _empresa_excluida(empresa, excluir_empresas)
        if choque:
            filtradas.append(dict(oferta=cand, motivo="empresa excluida",
                                   detalle=choque))
            continue

        choque = _keyword_excluida(puesto, excluir_keywords)
        if choque:
            filtradas.append(dict(oferta=cand, motivo="palabra excluida",
                                   detalle=choque))
            continue

        cifra = parsea_salario(cand.get("salario"))
        if cifra is None and exigir_pub:
            filtradas.append(dict(oferta=cand, motivo="sin salario publicado",
                                   detalle="exigir_salario_publicado activo"))
            continue
        if cifra is not None and salario_min and cifra < salario_min:
            filtradas.append(dict(oferta=cand, motivo="salario por debajo del mínimo",
                                   detalle=f"{cand.get('salario')} (< {salario_min})"))
            continue

        supervivientes.append(cand)

    return supervivientes, filtradas


def _etiqueta(o):
    return f"{o.get('empresa', '?')} — {o.get('puesto', '?')} [{o.get('id', '?')}]"


def main(argv):
    entradas = [a for a in argv if not a.startswith("--")]
    if not entradas:
        raise SystemExit(__doc__)

    with open(entradas[0], encoding="utf-8") as fh:
        candidatas = json.load(fh)
    if isinstance(candidatas, dict):
        candidatas = list(candidatas.values())

    filtros = {}
    if "--filtros" in argv:
        ruta = argv[argv.index("--filtros") + 1]
        with open(ruta, encoding="utf-8") as fh:
            filtros = json.load(fh)
    else:
        print("AVISO: sin --filtros, no se descarta nada por salario ni listas de exclusión.")

    supervivientes, filtradas = filtrar(candidatas, filtros)

    destino = None
    if "--json" in argv:
        destino = argv[argv.index("--json") + 1]
    elif len(entradas) > 1:
        destino = entradas[1]
    if destino:
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(supervivientes, fh, ensure_ascii=False, indent=1)

    acumula(candidatas_recibidas=len(candidatas), filtradas_config=len(filtradas))

    print(f"{len(candidatas)} candidatas · {len(supervivientes)} pasan · "
          f"{len(filtradas)} filtradas"
          + (f" -> {destino}" if destino else ""))
    for f in filtradas:
        print(f"  ✕ {_etiqueta(f['oferta'])}\n    {f['motivo']}: {f['detalle']}")
    for s in supervivientes:
        print(f"  ✓ {_etiqueta(s)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
