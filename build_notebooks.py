"""Genera los notebooks del proyecto. Después ejecutarlos en orden 00→05 (ver README)."""
from pathlib import Path
import nbformat as nbf
import yaml

root = Path(__file__).resolve().parent
CFG = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}
OBJ = CFG.get("objetivo", "")
KERNEL = {"display_name": "Python (mexico-costo-canasta)", "language": "python", "name": "python3"}
SETUP = """import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))
import entorno
entorno.setup()
import profeco, tablas, pares, estadistica as E, charts as C
import escalera as S
PROC, META, CHARTS, SOCIAL = entorno.PROC, entorno.META, entorno.CHARTS, entorno.SOCIAL
CFG = entorno.config()
reg = entorno.registrar
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 90)
pts, st, cat = S.load()
REPS = 500
"""
LOADP = """p = pd.read_csv(PROC / "escalones.csv")
SEL = json.loads((META / "parametros.json").read_text(encoding="utf-8"))["seleccionadas"]
"""


def write(name, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1]) for c in cells]
    nb.metadata.kernelspec = KERNEL
    (root / "notebooks").mkdir(exist_ok=True)
    nbf.write(nb, root / "notebooks" / name)


def head(num, title, question, why):
    return ("md", f"# {num} · {title}\n\n**Objetivo:** {OBJ}\n\n**Pregunta:** {question}\n\n{why}")


# --------------------------------------------------------------------------- 00
write("00_datos_y_seleccion.ipynb", [
    head("00", "Datos y selección de marcas", CFG.get("pregunta", ""),
         """Este notebook responde: ¿qué marcas tienen varios tamaños del mismo producto y la misma variante en la misma
tienda, y cuáles se analizan? Cierra con la tabla de decisiones metodológicas (plan aprobado en
`_specs/plan_metodologico_6_12.md`).

**Escalón** = un tamaño contra el siguiente más grande que tiene la tienda, comparando el precio por litro, kilo o pieza.
**Escalón roto** = el tamaño grande cuesta más por unidad que el chico."""),
    ("code", SETUP + """raw = entorno.load_raw()
manifest = entorno.write_manifest(raw)
print(f"Precios de tienda en supermercados: {len(pts):,} · tiendas: {pts.establecimiento_id.nunique()}")
sel = S.selection(pts, st, cat)
display(sel[["escalera", "categoria", "unidad", "tamanos", "tiendas_3_tamanos", "seleccionada", "presentaciones"]])"""),
    ("md", """## 1. Selección

**Decisión:** una escalera entra si tiene **3 tamaños o más de la misma variante** (mismo sabor, color o tipo, según el
texto de la presentación) y **100 tiendas o más con al menos 3 de esos tamaños**, en categorías distintas.

- **Entran:** Coca-Cola regular (lata 355 ml, 600 ml, 1 L y 2.75 L), huevo blanco San Juan (12, 18 y 30 piezas),
  Zucaritas (30, 380, 600 y 620 g) y chiles jalapeños en rajas La Costeña (105 a 380 g).
- **Huevo blanco El Calvario** entra como segunda marca de la misma categoría: sirve para comprobar que lo que pase con
  el huevo no es cosa de una sola marca.
- **No entran, aunque el plan las mencionaba como ejemplo:**
  - pan de caja Bimbo: solo 2 tamaños de la misma variante; el de 210 g es pan tostado, otro producto;
  - yoghurt Lala (y Alpura y Yoplait): el tamaño intermedio es bebible, otro producto; vaso y bote son solo 2 tamaños;
  - café Nescafé: cada variante tiene solo 2 tamaños.
- **No alcanzan 100 tiendas con 3 tamaños:** agua Ciel (74), galletas Saladitas y caldo Knorr (2 cada una; casi
  ninguna tienda tiene los tres tamaños a la vez).

La variante se define por el texto de la presentación y se revisó marca por marca (tabla de arriba). Las
presentaciones ambiguas («800 ó 880 g») quedan fuera (`sku_catalogo.presentacion_ambigua`).

**Propietaria:** solo Coca-Cola tiene empresa propietaria verificada en `sku_catalogo`; para las demás marcas no se
menciona la empresa."""),
    ("code", """SEL = sel[sel.seleccionada].escalera.tolist()
print("Seleccionadas:", SEL)
p = pd.concat([S.steps(pts, st, cat, k) for k in SEL], ignore_index=True)
print(f"Escalones: {len(p):,} · tiendas: {p.establecimiento_id.nunique()} · municipios: {p.municipio_id.nunique()}")
display(p.groupby(["escalera", "escalon"]).agg(escalones=("cambio_pct", "size"), contiguo=("contiguo", "first")))"""),
    ("md", """## 2. Calidad

- **Precio de tienda** = mediana de la quincena (`precio_tienda_sku`).
- **Extremos:** se marca cada precio con `estadistica.flag_prices`. Un escalón usa dos precios; la sensibilidad
  quita los escalones donde alguno de los dos es extremo.
- **Escalones no contiguos:** si la tienda no tiene el tamaño intermedio, el motor compara con el siguiente que sí
  tiene (p. ej., 12 contra 30 piezas). La sensibilidad usa solo escalones contiguos."""),
    ("code", """ext = pts.set_index(["establecimiento_id", "sku_id"]).extremo
y = pd.concat([S.skus(cat, k).assign(escalera=k) for k in SEL])
idx = y.set_index(["escalera", "cantidad_base"]).sku_id
p["extremo"] = [bool(ext.get((e, idx.get((k, a))), False) or ext.get((e, idx.get((k, b))), False))
                for e, k, a, b in zip(p.establecimiento_id, p.escalera, p.tam_a, p.tam_b)]
print(f"Escalones con algún precio extremo: {p.extremo.mean() * 100:.1f}% · no contiguos: {(~p.contiguo).mean() * 100:.1f}%")
p.to_csv(PROC / "escalones.csv", index=False, encoding="utf-8-sig")
sel.to_csv(META / "seleccion_marcas.csv", index=False, encoding="utf-8-sig")
params = {"semilla": S.SEMILLA, "bootstrap_replicas": REPS, "canal": S.CANAL, "min_tiendas_3_tamanos": S.MIN_TIENDAS3,
          "plano_pct": S.PLANO, "candidatas": {k: list(v) for k, v in S.CANDIDATAS.items()}, "seleccionadas": SEL}
_ = (META / "parametros.json").write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
F = "00_datos_y_seleccion"
reg("escalones", len(p), fuente=F); reg("tiendas", p.establecimiento_id.nunique(), fuente=F)
reg("municipios", p.municipio_id.nunique(), fuente=F); reg("marcas", len(SEL), fuente=F)
for k in SEL:
    reg("t3_" + S.KEY[k], sel.set_index("escalera").loc[k, "tiendas_3_tamanos"], fuente=F)
reg("ciel_t3", sel.set_index("escalera").loc["Agua Ciel", "tiendas_3_tamanos"], fuente=F)"""),
    ("md", "## 3. Decisiones metodológicas"),
    ("code", """display(Markdown(f'''
| # | Decisión | Propuesta | Por qué | Alternativas descartadas |
|---|---|---|---|---|
| 1 | Selección | 3 tamaños o más de la misma variante en 100 tiendas o más, categorías distintas: {len(SEL)} escaleras | escalones comparables y con cobertura | marcas «conocidas» sin revisar variante (Bimbo y yoghurt mezclan productos) |
| 2 | Comparación | misma tienda, mismo producto y variante (`pares.tamanos`); precio por litro, kilo o pieza | lo que ve el cliente frente al anaquel | promedios nacionales por tamaño (mezclan tiendas) |
| 3 | Escalón | cada tamaño contra el siguiente más grande que tiene la tienda | es la decisión real del cliente | todos contra todos (cuenta doble) |
| 4 | Ruptura | el grande cuesta más por unidad; además «plano» = descuento menor a 5% | una escalera rota cobra más por comprar más | solo la pendiente de una regresión precio–tamaño (queda descriptiva) |
| 5 | Incertidumbre | IC90 del % roto por bootstrap de dos vías (escalones y municipios), 500 réplicas, semilla 2026 | las tiendas de una ciudad no son independientes | IC por escalón |
| 6 | Desglose | escalera, escalón, cadena y formato con 20 escalones o más | ¿dónde se rompe más? | — |
| 7 | Calidad | extremos y escalones no contiguos marcados; % roto repetido sin ellos | no borrar en silencio | borrar extremos |
'''))"""),
    ("code", """display(Markdown(
    f"**Conclusión.** Cumplen la regla {len(SEL)} escaleras: " + ", ".join(SEL) + f". Suman **{len(p):,} escalones** en "
    f"{p.establecimiento_id.nunique()} supermercados de {p.municipio_id.nunique()} municipios. Bimbo, yoghurt y café no tienen 3 tamaños de "
    "la misma variante."))"""),
])

# --------------------------------------------------------------------------- 01
write("01_escalera_por_marca.ipynb", [
    head("01", "¿Baja el precio por unidad al subir el tamaño?",
         "Para cada marca, ¿cuánto baja el precio por litro, kilo o pieza en cada escalón?",
         """Importa porque la arquitectura de precios por tamaño es una promesa al cliente: comprar más sale más barato
por unidad. Si no se cumple, el cliente que compra el tamaño grande paga de más."""),
    ("code", SETUP + LOADP + """lp = S.ladder_prices(p)
display(lp.round(2))
st_ = p[p.contiguo].groupby(["escalera", "escalon"]).agg(tiendas=("cambio_pct", "size"), cambio_mediano=("cambio_pct", "median"),
                                                        p10=("cambio_pct", lambda v: v.quantile(.1)), p90=("cambio_pct", lambda v: v.quantile(.9)))
display(st_.round(1))"""),
    ("code", """lp.to_csv(PROC / "precio_unidad_por_tamano.csv", index=False, encoding="utf-8-sig")
st_.to_csv(PROC / "cambio_por_escalon.csv", encoding="utf-8-sig")
F = "01_escalera_por_marca"
g = st_.cambio_mediano
reg("coca_lata_600", g[("Coca-Cola", "355 ml → 600 ml")], fuente=F)
reg("coca_1_275", g[("Coca-Cola", "1 L → 2.75 L")], fuente=F)
reg("coca_600_1", g[("Coca-Cola", "600 ml → 1 L")], fuente=F)
reg("sj_12_18", g[("Huevo San Juan", "12 pzas → 18 pzas")], fuente=F); reg("sj_18_30", g[("Huevo San Juan", "18 pzas → 30 pzas")], fuente=F)
reg("ec_12_18", g[("Huevo El Calvario", "12 pzas → 18 pzas")], fuente=F); reg("ec_18_30", g[("Huevo El Calvario", "18 pzas → 30 pzas")], fuente=F)
pu = lp.set_index(["escalera", "tam"]).pu
reg("sj_pu_12", pu[("Huevo San Juan", 12.0)], fuente=F); reg("sj_pu_18", pu[("Huevo San Juan", 18.0)], fuente=F)
reg("sj_pu_30", pu[("Huevo San Juan", 30.0)], fuente=F)
display(Markdown(
    f"**Conclusión.** En Coca-Cola cada escalón baja con claridad el precio por litro (de lata a 600 ml, {g[('Coca-Cola', '355 ml → 600 ml')]:.0f}%; "
    f"de 1 L a 2.75 L, {g[('Coca-Cola', '1 L → 2.75 L')]:.0f}%). En el huevo no: el paquete de 18 piezas de San Juan cuesta "
    f"{g[('Huevo San Juan', '12 pzas → 18 pzas')]:+.0f}% por pieza frente al de 12, y en El Calvario el de 30 cuesta "
    f"{g[('Huevo El Calvario', '18 pzas → 30 pzas')]:+.0f}% frente al de 18."))"""),
])

# --------------------------------------------------------------------------- 02
write("02_rupturas.ipynb", [
    head("02", "¿En qué porcentaje de tiendas se rompe la escalera?",
         "¿Qué parte de los escalones tiene el tamaño grande más caro por unidad, por marca y por escalón?",
         """Importa porque mide qué tan seguido el cliente que compra más paga más por unidad. IC90 = rango probable
(bootstrap de escalones y ciudades)."""),
    ("code", SETUP + LOADP + """tot = S.broken(p, reps=REPS)
print({k: round(v, 1) if isinstance(v, float) else v for k, v in tot.items()})
bm = S.by(p, "escalera", reps=REPS).set_index("escalera").loc[SEL]
display(bm.round(1))
be = S.by(p[p.contiguo], ["escalera", "escalon"], reps=REPS)
display(be.round(1))"""),
    ("md", """## Sensibilidad

- solo escalones contiguos;
- sin escalones con algún precio extremo;
- ruptura solo si el grande cuesta más de 1% más por unidad (deja fuera redondeos de centavos)."""),
    ("code", """var = {"Principal": p, "Solo contiguos": p[p.contiguo], "Sin extremos": p[~p.extremo]}
sens = pd.DataFrame({k: S.by(v, "escalera", reps=200).set_index("escalera").pct_roto for k, v in var.items()})
sens["Ruptura > 1%"] = p.groupby("escalera").cambio_pct.apply(lambda v: (v > 1).mean() * 100)
sens.loc["Total"] = [S.broken(v, reps=10)["pct_roto"] for v in var.values()] + [(p.cambio_pct > 1).mean() * 100]
display(sens.round(1))"""),
    ("code", """bm.to_csv(PROC / "rupturas_por_marca.csv", encoding="utf-8-sig")
be.to_csv(PROC / "rupturas_por_escalon.csv", index=False, encoding="utf-8-sig")
sens.to_csv(PROC / "sensibilidad_rupturas.csv", encoding="utf-8-sig")
F = "02_rupturas"
reg("roto_total", tot["pct_roto"], [tot["ic90_inf"], tot["ic90_sup"]], n=tot["escalones"], fuente=F)
reg("plano_total", tot["pct_plano"], n=tot["escalones"], fuente=F)
for k, r_ in bm.iterrows():
    kk = S.KEY[k]
    reg(f"roto_{kk}", r_.pct_roto, [r_.ic90_inf, r_.ic90_sup], n=r_.escalones, fuente=F)
    reg(f"plano_{kk}", r_.pct_plano, fuente=F); reg(f"tiendas_{kk}", r_.tiendas, fuente=F)
E_ = be.set_index(["escalera", "escalon"])
for (k, e), kk in {("Huevo San Juan", "12 pzas → 18 pzas"): "sj_12_18", ("Huevo El Calvario", "18 pzas → 30 pzas"): "ec_18_30",
                   ("Chiles La Costeña en rajas", "240 g → 340 g"): "raj_240_340", ("Zucaritas", "380 g → 600 g"): "zuc_380_600",
                   ("Huevo San Juan", "18 pzas → 30 pzas"): "sj_18_30", ("Huevo El Calvario", "12 pzas → 18 pzas"): "ec_12_18"}.items():
    r_ = E_.loc[(k, e)]
    reg(f"roto_{kk}", r_.pct_roto, [r_.ic90_inf, r_.ic90_sup], n=r_.escalones, fuente=F)
reg("sens_total_min", sens.loc["Total"].min(), fuente=F); reg("sens_total_max", sens.loc["Total"].max(), fuente=F)
reg("sens_sj_min", sens.loc["Huevo San Juan"].min(), fuente=F); reg("sens_sj_max", sens.loc["Huevo San Juan"].max(), fuente=F)
display(Markdown(
    f"**Conclusión.** De {tot['escalones']:,} escalones, **{tot['pct_roto']:.0f}%** están rotos (IC90 {tot['ic90_inf']:.0f}–{tot['ic90_sup']:.0f}%) "
    f"y {tot['pct_plano']:.0f}% son planos. La ruptura se concentra en un escalón por marca: huevo San Juan de 12 a 18 piezas "
    f"({E_.loc[('Huevo San Juan', '12 pzas → 18 pzas'), 'pct_roto']:.0f}% de las tiendas), El Calvario de 18 a 30 "
    f"({E_.loc[('Huevo El Calvario', '18 pzas → 30 pzas'), 'pct_roto']:.0f}%) y rajas La Costeña de 240 a 340 g "
    f"({E_.loc[('Chiles La Costeña en rajas', '240 g → 340 g'), 'pct_roto']:.0f}%). Coca-Cola casi nunca: {bm.loc['Coca-Cola', 'pct_roto']:.1f}%."))"""),
])

# --------------------------------------------------------------------------- 03
write("03_cadenas_y_formatos.ipynb", [
    head("03", "¿Hay cadenas o formatos donde se rompe más?",
         "¿La ruptura depende de la cadena o del producto?",
         """Importa porque dice a quién reclamar: si se rompe igual en todas las cadenas, la escalera viene del precio de
lista del fabricante; si se concentra en algunas, es decisión de la cadena. Grupos con 20 escalones o más."""),
    ("code", SETUP + LOADP + """bf = S.by(p, "formato", reps=REPS).sort_values("pct_roto", ascending=False)
display(bf.round(1))
mx = S.by(p, ["escalera", "formato"], min_n=10, reps=100).pivot(index="formato", columns="escalera", values="pct_roto")
display(mx.round(0))"""),
    ("md", """**¿Es la cadena o la mezcla de productos?** Las cadenas no venden la misma mezcla de escaleras. Se compara cada
formato con el % roto esperado si tuviera las tasas promedio de cada escalón (mezcla igual)."""),
    ("code", """rate = p.groupby(["escalera", "escalon"]).cambio_pct.apply(lambda v: (v > S.TOL).mean())
p["esperado"] = [rate[(a, b)] for a, b in zip(p.escalera, p.escalon)]
adj = p.groupby("formato").agg(n=("cambio_pct", "size"), observado=("cambio_pct", lambda v: (v > S.TOL).mean() * 100),
                               esperado=("esperado", lambda v: v.mean() * 100)).query("n >= 20")
adj["diferencia_pp"] = adj.observado - adj.esperado
display(adj.sort_values("diferencia_pp").round(1))
sj = p[(p.escalera == "Huevo San Juan") & (p.escalon == "12 pzas → 18 pzas")]
sjf = S.by(sj, "formato", min_n=10, reps=REPS).sort_values("pct_roto")
display(sjf.round(1))"""),
    ("code", """bf.to_csv(PROC / "rupturas_por_formato.csv", index=False, encoding="utf-8-sig")
mx.to_csv(PROC / "rupturas_formato_marca.csv", encoding="utf-8-sig")
adj.to_csv(PROC / "rupturas_formato_ajustadas.csv", encoding="utf-8-sig")
sjf.to_csv(PROC / "huevo_sj_por_formato.csv", index=False, encoding="utf-8-sig")
F = "03_cadenas_y_formatos"
reg("formato_max", bf.pct_roto.max(), fuente=F, nota=bf.iloc[0].formato); reg("formato_min", bf.pct_roto.min(), fuente=F, nota=bf.iloc[-1].formato)
reg("formatos_n", len(bf), fuente=F)
reg("ajuste_max_pp", adj.diferencia_pp.abs().max(), fuente=F, nota=adj.diferencia_pp.abs().idxmax())
reg("sj_formato_min", sjf.pct_roto.min(), fuente=F, nota=sjf.iloc[0].formato); reg("sj_formato_max", sjf.pct_roto.max(), fuente=F, nota=sjf.iloc[-1].formato)
reg("sj_formatos", len(sjf), fuente=F)
display(Markdown(
    f"**Conclusión.** El % roto va de {bf.pct_roto.min():.0f}% en {bf.iloc[-1].formato} a {bf.pct_roto.max():.0f}% en {bf.iloc[0].formato}, pero "
    f"con la misma mezcla de escalones la diferencia frente a lo esperado es de a lo más {adj.diferencia_pp.abs().max():.0f} puntos. "
    f"El escalón de 12 a 18 huevos San Juan está roto en {sjf.pct_roto.min():.0f}% a {sjf.pct_roto.max():.0f}% de las tiendas de los "
    f"{len(sjf)} formatos con datos: la ruptura viene del producto, no de la cadena."))"""),
])

# --------------------------------------------------------------------------- 04
write("04_que_revisar.ipynb", [
    head("04", "¿Qué debe revisar una marca o un retailer?",
         "¿Cuánto paga de más el cliente en un escalón roto y qué escalones conviene revisar?",
         """Importa porque convierte el % de rupturas en pesos: cuánto cuesta al cliente comprar el tamaño grande donde la
escalera está rota, y qué tan grande es el descuento por volumen donde sí funciona."""),
    ("code", SETUP + LOADP + """x = p[p.contiguo].copy()
x["sobreprecio_unidad"] = x.precio_b - x.precio_a
x["sobreprecio_empaque"] = x.sobreprecio_unidad * x.tam_b
tab = x.groupby(["escalera", "escalon"]).agg(
    tiendas=("cambio_pct", "size"), pct_roto=("cambio_pct", lambda v: (v > S.TOL).mean() * 100),
    cambio_mediano=("cambio_pct", "median"),
    sobreprecio_empaque_si_roto=("sobreprecio_empaque", lambda v: v[v > 0].median() if (v > 0).any() else 0.0))
display(tab.round(2))"""),
    ("md", """**Lectura.** Sobreprecio por empaque = lo que paga de más el cliente por todo el paquete grande frente a comprar
la misma cantidad al precio por unidad del chico (mediana de las tiendas donde el escalón está roto)."""),
    ("code", """tab.to_csv(PROC / "que_revisar.csv", encoding="utf-8-sig")
F = "04_que_revisar"
t = tab.loc[("Huevo San Juan", "12 pzas → 18 pzas")]
reg("sj_sobreprecio_18", t.sobreprecio_empaque_si_roto, fuente=F, nota="pesos de más por el paquete de 18 frente al precio por pieza del de 12")
t2 = tab.loc[("Huevo El Calvario", "18 pzas → 30 pzas")]
reg("ec_sobreprecio_30", t2.sobreprecio_empaque_si_roto, fuente=F)
t3 = tab.loc[("Chiles La Costeña en rajas", "240 g → 340 g")]
reg("raj_sobreprecio_340", t3.sobreprecio_empaque_si_roto, fuente=F)
display(Markdown(
    f"**Conclusión.** Donde la escalera del huevo San Juan está rota, el paquete de 18 cuesta ${t.sobreprecio_empaque_si_roto:.2f} más que 18 "
    f"huevos al precio por pieza del de 12; en El Calvario, el de 30 cuesta ${t2.sobreprecio_empaque_si_roto:.2f} más que 30 huevos al precio "
    f"del de 18. Son pocos pesos por paquete, pero rompen la promesa de que comprar más sale más barato."))"""),
])

# --------------------------------------------------------------------------- 05
write("05_visualizaciones.ipynb", [
    head("05", "Visualizaciones, reporte e implicaciones", "¿Cómo se comunica el hallazgo y qué hace cada audiencia?",
         """Convenciones: **rojo ▼** = el tamaño grande cuesta menos por unidad (lo esperado); **verde ▲** = cuesta más
(escalón roto); gris = sin cambio claro; dorado = referencia."""),
    ("code", SETUP + LOADP + """import graficas as G, reporte, plantillas, re
res = entorno.cifras()
lp = pd.read_csv(PROC / "precio_unidad_por_tamano.csv")
be = pd.read_csv(PROC / "rupturas_por_escalon.csv")
bf = pd.read_csv(PROC / "rupturas_por_formato.csv")
bm = pd.read_csv(PROC / "rupturas_por_marca.csv", index_col=0)"""),
    ("md", "## Gráfica principal: escaleras de precio por tamaño"),
    ("code", """G.ladders(lp, be, SEL, res, CHARTS / "01_escaleras_por_tamano.png", svg=True); plt.show()"""),
    ("md", "### Versiones para publicar (1280×720 y 1080×1350)"),
    ("code", """G.ladders_social(lp, be, res, "horizontal", SOCIAL / "01_escaleras_1280x720.png"); plt.show()
G.ladders_social(lp, be, res, "vertical", SOCIAL / "01_escaleras_1080x1350.png"); plt.show()"""),
    ("md", "## Complementarias"),
    ("code", """G.broken_by_step(be, res, CHARTS / "02_rupturas_por_escalon.png"); plt.show()"""),
    ("code", """G.broken_by_format(bf, res, CHARTS / "03_rupturas_por_formato.png"); plt.show()"""),
    ("code", """G.egg_case(p, res, CHARTS / "04_huevo_12_vs_18.png"); plt.show()"""),
    ("md", "## Reporte HTML y README"),
    ("code", """GALERIA = [(g_["titulo"], g_["pie"], CHARTS / g_["archivo"]) for g_ in CFG["graficas"]]
out = reporte.build(be, bf, bm, res, CFG, GALERIA, ROOT / "docs/index.html")
print(out, f"{out.stat().st_size / 1e6:.1f} MB")
estructura = (ROOT / "src/estructura.md").read_text(encoding="utf-8")
(ROOT / "README.md").write_text(plantillas.readme(CFG, res, estructura), encoding="utf-8")
txt = (ROOT / "README.md").read_text(encoding="utf-8")
assert not re.search(r"\\{[a-z][a-z0-9_]*(:[^}]*)?\\}", txt), re.findall(r"\\{[a-z][a-z0-9_]*(?::[^}]*)?\\}", txt)[:5]
print("README actualizado")"""),
    ("md", "## Qué hacer con esto"),
    ("code", """for aud, acc in CFG["readme"]["acciones"].items():
    display(Markdown(f"**{aud}**\\n\\n" + "\\n".join(f"- {plantillas.render(a, res)}" for a in acc)))"""),
])

print("Notebooks generados.")
