# -*- coding: utf-8 -*-
"""Una oferta de `manual/` que no está en el snapshot acaba en data/."""
import json, os, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_manual_entra_aunque_el_snapshot_sea_anterior():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "pipeline")); os.makedirs(os.path.join(tmp, "manual"))
        snap = {"ofertas": [{"id": "a"}], "tailor": {"a": {}}, "perfil": {}, "cerradas": []}
        json.dump(snap, open(os.path.join(tmp, "pipeline", "snapshot.json"), "w"))
        man = {"row": {}, "oferta": {"id": "manual-x"}, "tailor": {"familia": "ml"}}
        json.dump(man, open(os.path.join(tmp, "manual", "manual-x.json"), "w"))
        json.dump({"oferta": {"id": "a"}, "tailor": {"pisa": 1}}, open(os.path.join(tmp, "manual", "a.json"), "w"))
        out = os.path.join(tmp, "data")
        subprocess.run([sys.executable, os.path.join(RAIZ, "pipeline", "preparar_datos.py"), tmp, out], check=True)
        ids = [o["id"] for o in json.load(open(os.path.join(out, "ofertas.json")))]
        tailor = json.load(open(os.path.join(out, "tailor.json")))
        assert ids == ["a", "manual-x"], ids
        assert tailor["manual-x"] == {"familia": "ml"} and tailor["a"] == {}

def test_snapshot_en_trozos_ida_y_vuelta():
    with tempfile.TemporaryDirectory() as tmp:
        data = os.path.join(tmp, "data"); os.makedirs(data)
        ofertas = [{"id": f"o{i}", "txt": os.urandom(400).hex()} for i in range(400)]  # incomprimible
        for n, v in {"ofertas": ofertas, "tailor": {o["id"]: {} for o in ofertas},
                     "perfil": {}, "cerradas": []}.items():
            json.dump(v, open(os.path.join(data, n + ".json"), "w"))
        out = os.path.join(tmp, "o", "snapshot.json")
        subprocess.run([sys.executable, os.path.join(RAIZ, "pipeline", "exportar_snapshot.py"), out],
                       check=True, cwd=tmp, env={**os.environ, "RADAR_DATA": data})
        doc = json.load(open(out))
        assert doc["partes"] > 1 and os.path.exists(os.path.join(tmp, "o", "snapshot_1.json"))
        assert all(os.path.getsize(os.path.join(tmp, "o", f)) < 262144 for f in os.listdir(os.path.join(tmp, "o")))
        d2 = os.path.join(tmp, "d2")
        subprocess.run([sys.executable, os.path.join(RAIZ, "pipeline", "preparar_datos.py"), os.path.join(tmp, "o"), d2], check=True)
        assert json.load(open(os.path.join(d2, "ofertas.json"))) == ofertas

if __name__ == "__main__":
    test_manual_entra_aunque_el_snapshot_sea_anterior()
    test_snapshot_en_trozos_ida_y_vuelta(); print("ok")
