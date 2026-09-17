# -*- coding: utf-8 -*-
"""Poda a ciegas: ofertas con `publicada` de hace más de 45 dias y sin
seguimiento se retiran sin comprobar si siguen abiertas.

Sin seguimiento = no hay documento en `estado` para ese id, o lo hay con
estado == 'activa'. Cualquier otra fase (aplicada, rechazada, descartada,
con notas) nunca se toca.

Imprime solo el recuento y la lista de ids retirados.
"""
import datetime
import json
import os
import sys

DATA = os.environ.get("RADAR_DATA", "data")
HOY = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
CORTE = HOY - datetime.timedelta(days=45)


def cargar(nombre, defecto):
    p = os.path.join(DATA, nombre)
    if not os.path.exists(p):
        return defecto
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ofertas = cargar("ofertas.json", [])
    estado = cargar("estado.json", {})
    tailor = cargar("tailor.json", {})

    retirar = []
    for o in ofertas:
        pub = o.get("publicada")
        if not pub:
            continue
        try:
            fpub = datetime.date.fromisoformat(pub[:10])
        except ValueError:
            continue
        if fpub >= CORTE:
            continue
        e = estado.get(o["id"])
        sin_seguimiento = e is None or (isinstance(e, dict) and e.get("estado") == "activa")
        if sin_seguimiento:
            retirar.append(o)

    print(f"CORTE={CORTE.isoformat()} ofertas={len(ofertas)} a_podar={len(retirar)}")
    for o in retirar:
        print(f"  {o['id']} | {o.get('empresa')} | {o.get('puesto')} | publicada={o.get('publicada')}")

    ids_retirar = {o["id"] for o in retirar}
    nuevas_ofertas = [o for o in ofertas if o["id"] not in ids_retirar]
    nuevo_tailor = {k: v for k, v in tailor.items() if k not in ids_retirar}

    with open(os.path.join(DATA, "ofertas.json"), "w", encoding="utf-8") as fh:
        json.dump(nuevas_ofertas, fh, ensure_ascii=False)
    with open(os.path.join(DATA, "tailor.json"), "w", encoding="utf-8") as fh:
        json.dump(nuevo_tailor, fh, ensure_ascii=False)

    with open(os.path.join(DATA, "podadas.json"), "w", encoding="utf-8") as fh:
        json.dump([{"id": o["id"], "empresa": o.get("empresa"), "puesto": o.get("puesto"),
                    "publicada": o.get("publicada")} for o in retirar], fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
