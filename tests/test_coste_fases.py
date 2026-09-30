# -*- coding: utf-8 -*-
"""coste_fases.py: reparto de tokens de la transcripción por fase (30-sep-2026)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
import coste_fases  # noqa: E402


def _msg(ts, mid, out, leido, herr=None):
    content = [{"type": "tool_use", "name": herr}] if herr else []
    return {"type": "assistant", "timestamp": ts, "message": {
        "id": mid, "content": content,
        "usage": {"input_tokens": 1, "cache_creation_input_tokens": 10,
                  "cache_read_input_tokens": leido, "output_tokens": out}}}


def test_reparte_por_hora_y_no_duplica_respuestas_partidas():
    d = tempfile.mkdtemp()
    ruta = os.path.join(d, "s.jsonl")
    lineas = [
        _msg("2026-09-30T08:00:30Z", "a", 5, 100, "mcp__x__fetch"),
        _msg("2026-09-30T08:00:31Z", "a", 50, 100),        # misma respuesta partida
        _msg("2026-09-30T08:05:00Z", "b", 20, 1000, "Bash"),
        {"type": "user", "timestamp": "2026-09-30T08:05:01Z",
         "message": {"content": [{"type": "tool_result", "content": "x" * 400}]}},
        _msg("2026-09-30T08:20:00Z", "c", 1, 1, None),     # después de «fin»
    ]
    with open(ruta, "w") as fh:
        fh.write("\n".join(json.dumps(x) for x in lineas))
    os.makedirs(os.path.join(d, "s", "subagents"))
    with open(os.path.join(d, "s", "subagents", "a1.jsonl"), "w") as fh:
        fh.write(json.dumps(_msg("2026-09-30T08:06:00Z", "z", 7, 0, "WebFetch")))
    fases = [{"fase": "linkedin", "inicio": "2026-09-30T08:00:00+00:00"},
             {"fase": "infojobs", "inicio": "2026-09-30T08:04:00+00:00"},
             {"fase": "_fin", "inicio": "2026-09-30T08:10:00+00:00"}]
    doc = coste_fases.calcula(ruta, fases)
    f = {x["fase"]: x for x in doc["fases"]}
    assert f["linkedin"]["respuestas"] == 1 and f["linkedin"]["salida"] == 50
    assert f["linkedin"]["llamadas"] == {"fetch": 1} and f["linkedin"]["duracion_min"] == 4.0
    assert f["infojobs"]["respuestas"] == 2 and f["infojobs"]["subagente_respuestas"] == 1
    assert f["infojobs"]["chars_resultados"] == 400
    assert f["cierre"]["respuestas"] == 1
    assert doc["subagentes"] == 1
    # equivalente = 1*1 + 10*2 + 100*0,1 + 50*5
    assert f["linkedin"]["equivalente"] == round(1 + 20 + 10 + 250)


if __name__ == "__main__":
    test_reparte_por_hora_y_no_duplica_respuestas_partidas()
    print("todo en verde")
