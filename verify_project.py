"""Verificación independiente: recalcula las cifras clave solo con pandas y numpy a partir de los precios originales
(extracto publicado o Parquet del núcleo), sin usar los módulos de src/, y comprueba que coinciden con el README y con
data/processed/resultados.json."""
from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PROC = ROOT / "data/processed"
README = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
RES = json.loads((PROC / "resultados.json").read_text(encoding="utf-8"))
src = PROC / "profeco_extracto.parquet"
if not src.exists():
    src = ROOT.parent / "_profeco_core/data/profeco_2026_08_q2.parquet"
df = pd.read_parquet(src, columns=["precio_num", "giro", "marca", "producto", "presentacion", "establecimiento_id"])
df = df[(df.precio_num > 0) & (df.giro.astype(str) == "Supermercado / Tienda de Autoservicio")]
for c in ["marca", "producto", "presentacion"]:
    df[c] = df[c].astype(str)


def step(marca, producto, chico, grande, q_chico, q_grande):
    """% de tiendas con las dos presentaciones donde la grande cuesta más por unidad (precio de tienda = mediana)."""
    x = df[(df.marca == marca) & (df.producto == producto) & df.presentacion.isin([chico, grande])]
    t = x.groupby(["establecimiento_id", "presentacion"]).precio_num.median().unstack().dropna()
    return ((t[grande] / q_grande) > (t[chico] / q_chico) + 1e-12).mean() * 100, len(t)


sj, n_sj = step("San Juan", "Huevo", "Paquete C/12 Blanco", "Paquete C/18 Blanco", 12, 18)
ec, _ = step("El Calvario", "Huevo", "Paquete C/18 Blanco", "Paquete C/30 Blanco", 18, 30)
rj, _ = step("La Costeña", "Chiles", "Lata 240 Gr. Jalapeños Rajas", "Lata 340 Gr. Jalapeños Rajas", 0.24, 0.34)
checks = {
    "huevo San Juan 12→18": (sj, "roto_sj_12_18", f"En {sj:.0f}% de las tiendas (IC90"),
    "huevo El Calvario 18→30": (ec, "roto_ec_18_30", f"roto en {ec:.0f}% de las tiendas"),
    "rajas 240→340 g": (rj, "roto_raj_240_340", f"de 240 a 340 g: {rj:.0f}%"),
}
for name, (val, key, txt) in checks.items():
    assert abs(val - RES[key]["cifra"]) < 1e-6, f"{name}: {val} vs resultados.json {RES[key]['cifra']}"
    assert txt in README, f"{name}: «{txt}» no aparece en el README"
    print(f"OK  {name:26s} {txt}")
assert n_sj == RES["roto_sj_12_18"]["n"], (n_sj, RES["roto_sj_12_18"]["n"])

for nb_path in sorted((ROOT / "notebooks").glob("0*.ipynb")):
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is not None, f"{nb_path.name} sin ejecutar"
            assert not any(o["output_type"] == "error" for o in cell["outputs"]), nb_path.name
for f in ["outputs/charts/01_escaleras_por_tamano.png", "outputs/charts/01_escaleras_por_tamano.svg",
          "outputs/social/01_escaleras_1280x720.png", "outputs/social/01_escaleras_1080x1350.png",
          "outputs/charts/02_rupturas_por_escalon.png", "outputs/charts/03_rupturas_por_formato.png",
          "outputs/charts/04_huevo_12_vs_18.png", "docs/index.html", "data/metadata/manifiesto_insumos.json",
          "data/metadata/seleccion_marcas.csv"]:
    assert (ROOT / f).exists(), f"Falta {f}"
assert "elaboración propia con datos de PROFECO" in README
assert "URL oficial" in README
print("Verificación correcta: las cifras clave del README se reproducen de forma independiente "
      "y los notebooks 00–05 se ejecutaron sin errores.")
