"""Reporte HTML de la arquitectura de precio por tamaño: versión ejecutiva (reporte_ejecutivo), sin Plotly.
Se conserva la firma build(...) que usa el notebook 05; el contenido sale de data/processed/."""
import reporte_ejecutivo as RE


def build(be, bf, bm, res, cfg, gallery, path):
    return RE.build(path)
