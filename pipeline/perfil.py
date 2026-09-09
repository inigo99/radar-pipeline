# -*- coding: utf-8 -*-
"""Modelo de evidencia del CV y candado anti-invención.

prominencia 1.0 = demostrado en resumen o bullets
prominencia 0.5 = sólo listado en «Competencias técnicas»
prominencia 0.0 = no lo tiene -> NUNCA sube. Esta regla no se toca.
"""
from datos import PERFIL as _P

ORIG  = _P["evidencia_orig"]
TECHO = _P["techo"]

def prominencia_adaptada(term, usados):
    """Prominencia del término en el CV adaptado.
    Sólo sube si (a) ya lo tiene y (b) el CV adaptado lo saca a un bullet o al resumen."""
    base = ORIG.get(term, 0.0)
    if base == 0.0:
        return 0.0                      # no lo tiene -> no se inventa
    if term in usados:
        return max(base, TECHO.get(term, base))
    return base
