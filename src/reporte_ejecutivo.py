"""Reporte HTML ejecutivo de precios por tamaño: una pantalla para dueños de negocio, sin dependencias externas.
Mismo texto, cifras y aviso que el post y el carrusel. Las cifras salen de data/processed/.
Uso: python src/reporte_ejecutivo.py   (escribe docs/index.html)
"""
import base64
import csv
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data" / "processed"
FUENTES = Path(__file__).with_name("fuentes")
SALIDA = RAIZ / "docs" / "index.html"

R = {k: v["cifra"] for k, v in json.load(open(PROC / "resultados.json", encoding="utf-8")).items()}


def leer(nombre):
    return list(csv.DictReader(open(PROC / nombre, encoding="utf-8-sig")))


CADENAS = sorted(leer("huevo_sj_por_formato.csv"), key=lambda f: float(f["pct_roto"]))
ESCALONES = sorted(leer("rupturas_por_escalon.csv"), key=lambda f: -float(f["pct_roto"]))


def b64(n):
    return base64.b64encode((FUENTES / n).read_bytes()).decode()


def p1(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def delta(v):
    """Triángulo + signo real + color por consecuencia: el grande más caro por unidad perjudica; más barato es lo esperado."""
    if abs(v) < 0.05:
        return '<span class="d neu">0%</span>'
    return (f'<span class="d neg">▲ +{p1(v)}%</span>' if v > 0 else f'<span class="d neu">▼ −{p1(abs(v))}%</span>')


SELLO = ('<svg viewBox="0 0 100 100" width="46" height="46"><path d="M0 0 H84 L100 16 V100 H0 Z" fill="#F5F0E6"/>'
         '<g fill="none" stroke="#12213C" stroke-width="6.5" stroke-linecap="square" stroke-linejoin="miter">'
         '<path d="M28 32 H14 V68 H28"/><path d="M38 68 V32 H48 A9 9 0 0 1 48 50 H38 M48 50 L57 68"/>'
         '<path d="M68 68 V32 H78 A9 9 0 0 1 78 50 H68 M78 50 L87 68"/></g>'
         '<line x1="14" y1="50" x2="25" y2="50" stroke="#C4533A" stroke-width="6.5" stroke-linecap="square"/></svg>')


def barras(filas, alto_fila=50, destacar=lambda i: False):
    """Barras horizontales en SVG. filas: (etiqueta, subetiqueta, valor %)."""
    W, L, Rr, T = 1100, 330, 110, 6
    ancho = W - L - Rr
    s = ""
    for i, (et, sub, v) in enumerate(filas):
        y = T + i * alto_fila
        col = "#C4533A" if destacar(i) else "#9DB0C6"
        s += (f'<text x="0" y="{y + 22}" font-size="18" font-weight="600" fill="#1B1F27">{et}</text>'
              f'<text x="0" y="{y + 40}" font-size="13" fill="#5B6573">{sub}</text>'
              f'<rect x="{L}" y="{y + 8}" width="{ancho}" height="26" fill="#ECE5D6" rx="2"/>'
              f'<rect x="{L}" y="{y + 8}" width="{max(v, 0.8) / 100 * ancho:.1f}" height="26" fill="{col}" rx="2"/>'
              f'<text x="{W}" y="{y + 30}" text-anchor="end" font-family="Instrument Serif,serif" font-size="32" fill="#12213C">{p1(v)}%</text>')
    h = T + len(filas) * alto_fila
    return f'<svg viewBox="0 0 {W} {h}" width="100%" role="img">{s}</svg>'


g_cadenas = barras([(f["formato"], f"{f['escalones']} tiendas", float(f["pct_roto"])) for f in CADENAS[::-1]],
                   destacar=lambda i: True)
g_marcas = barras([("Huevo El Calvario", "30 contra 18 piezas", R["roto_ec_18_30"]),
                   ("Chiles La Costeña", "340 contra 240 g", R["roto_raj_240_340"]),
                   ("Coca-Cola", "todos sus tamaños", R["roto_coca"])], destacar=lambda i: i < 2)

filas_tabla = "".join(
    f"<tr><td><b>{e['escalera']}</b></td><td>{e['escalon']}</td><td class='n'>{p1(float(e['pct_roto']))}%</td>"
    f"<td class='n'>{p1(float(e['ic90_inf']))}–{p1(float(e['ic90_sup']))}%</td><td class='n'>{delta(float(e['cambio_mediano']))}</td>"
    f"<td class='n'>{e['tiendas']}</td></tr>" for e in ESCALONES)

FUENTES_TABLA = [
    ("Precios por tienda y producto", "657,602 registros; 300 supermercados, 63 municipios",
     "Profeco, Quién es Quién en los Precios (qqp.profeco.gob.mx), quincena del 16 al 31 de agosto de 2026", "Oficial"),
]
filas_fuentes = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in FUENTES_TABLA)

HTML = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Precios por tamaño en supermercados de México</title>
<meta name="description" content="El cartón de 18 huevos San Juan sale más caro por huevo que el de 12 en las 6 cadenas que lo venden.">
<style>
@font-face{{font-family:"Instrument Serif";font-style:normal;font-weight:400;src:url(data:font/woff2;base64,{b64('instrument-serif-latin-400-normal.woff2')}) format("woff2")}}
@font-face{{font-family:"Instrument Serif";font-style:italic;font-weight:400;src:url(data:font/woff2;base64,{b64('instrument-serif-latin-400-italic.woff2')}) format("woff2")}}
@font-face{{font-family:"Inter";font-weight:400;src:url(data:font/woff2;base64,{b64('inter-latin-400-normal.woff2')}) format("woff2")}}
@font-face{{font-family:"Inter";font-weight:600;src:url(data:font/woff2;base64,{b64('inter-latin-600-normal.woff2')}) format("woff2")}}
:root{{--marino:#12213C;--acero:#4A6785;--terra:#C4533A;--marfil:#F5F0E6;--marfil-texto:#F6F1E8;--grafito:#1B1F27;--gris:#5B6573;
--tarjeta:#FBF8F1;--borde:#E3DBC9;--pista:#ECE5D6;--linea:#D9D2C2;--verde:#2B6A52;--vino:#8F2B3E}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--marfil);color:var(--grafito);font-family:"Inter",Arial,sans-serif;font-size:16px;line-height:1.45}}
.marco{{border:14px solid var(--marino);min-height:100vh;display:flex;flex-direction:column}}
main{{max-width:1120px;width:100%;margin:0 auto;padding:22px 28px 8px;flex:1}}
.etq{{font-weight:600;font-size:13px;letter-spacing:.16em;text-transform:uppercase;border-bottom:2px solid var(--acero);display:inline-block;padding-bottom:3px}}
h1{{font-family:"Instrument Serif",serif;font-weight:400;font-size:44px;line-height:1.05;margin:12px 0 6px}}
h1 em{{color:var(--terra)}}
.sub{{color:var(--gris);font-size:18px;max-width:900px}}
.card{{background:var(--tarjeta);border:1px solid var(--borde);border-radius:4px;padding:16px 18px}}
.pos{{color:var(--verde)}}.neg{{color:var(--vino)}}.neu{{color:var(--acero)}}.d{{font-weight:600}}
.veredicto{{display:flex;gap:16px;align-items:center;margin-top:18px}}
.veredicto .luz{{width:30px;height:30px;border-radius:50%;flex:none;background:var(--vino)}}
.veredicto b{{font-family:"Instrument Serif",serif;font-weight:400;font-size:38px;line-height:1.05;display:block;color:var(--vino)}}
.veredicto span{{font-size:18px;display:block;margin-top:2px}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}}
.kpi{{padding:12px 16px}}
.kpi .t{{font-size:15px;color:var(--gris);min-height:42px}}
.kpi .v{{font-family:"Instrument Serif",serif;font-size:54px;line-height:1.1;color:var(--marino);white-space:nowrap}}
.kpi .v .d{{font-weight:400}}
.kpi .v .tri{{font-family:Inter,Arial,sans-serif;font-size:26px;vertical-align:.25em;margin-right:6px}}
.kpi .p{{font-size:14px;color:var(--gris)}}
.paso{{font-weight:600;font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--acero);margin:22px 0 8px}}
.acciones{{padding:12px 18px 12px 40px;background:var(--tarjeta);border-left:4px solid var(--marino);font-size:18px}}
.acciones li{{margin:5px 0}} .acciones b{{font-weight:600}}
.graf{{margin-top:16px}} .graf h2{{font-family:"Instrument Serif",serif;font-weight:400;font-size:28px;margin-bottom:2px}}
.nota{{font-size:13.5px;color:var(--gris);margin-top:6px}}
svg text{{font-family:"Inter",Arial,sans-serif}}
.dos{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
details{{margin-top:14px;font-size:14px}} details summary{{cursor:pointer;color:var(--acero);font-weight:600;font-size:15px}}
table{{width:100%;border-collapse:collapse;margin-top:8px;font-size:13.5px}}
th{{text-align:left;font-weight:600;color:var(--grafito);border-bottom:1px solid var(--linea);padding:4px 8px 4px 0}}
td{{padding:5px 8px 5px 0;border-bottom:1px solid var(--pista);vertical-align:top;color:var(--gris)}} td.n{{text-align:right;white-space:nowrap}}
th.n{{text-align:right}}
.fuentes{{max-width:1120px;margin:8px auto 0;padding:0 28px 14px;width:100%}}
.fuentes p{{font-size:12.5px;color:var(--gris);margin-top:6px}} .fuentes p.legal{{font-style:italic}} .fuentes p b{{font-weight:600;color:var(--grafito)}}
.filete{{height:4px;background:var(--terra)}}
footer{{background:var(--marino);color:var(--marfil-texto);display:flex;justify-content:space-between;align-items:center;padding:12px 28px;gap:12px}}
footer .n{{display:flex;align-items:center;gap:12px;font-family:"Instrument Serif",serif;font-size:26px}}
footer .r{{font-weight:600;font-size:12px;letter-spacing:.06em}}
@media(max-width:900px){{.kpis,.dos{{grid-template-columns:1fr}}h1{{font-size:32px}}.kpi .v{{font-size:46px}}}}
</style></head>
<body><div class="marco"><main>
<span class="etq">Dueños de negocio · Precios por tamaño en supermercados de México</span>
<h1>Llevarte el cartón de 18 huevos San Juan en vez del de 12 sale <em>más caro por huevo</em></h1>
<p class="sub">En las 6 cadenas que lo venden. Pagas poco más de $1 de más por cartón.</p>

<div class="card veredicto"><div class="luz"></div><div><b>Se repite en las 6 cadenas</b>
<span>Si seis competidores hacen lo mismo, no parece decisión de una tienda. Parece venir de la lista de precios.</span></div></div>

<div class="kpis">
<div class="card kpi"><div class="t">Por huevo, el cartón de 18 cuesta</div><div class="v"><span class="d neg"><span class="tri">▲</span>+{p1(R['sj_12_18'])}%</span></div><div class="p">más que el de 12 (precio mediano)</div></div>
<div class="card kpi"><div class="t">Por cartón de 18 pagas de más</div><div class="v"><span class="d neg"><span class="tri">▲</span>+${R['sj_sobreprecio_18']:.2f}</span></div><div class="p">frente a pagar el precio por huevo del de 12</div></div>
<div class="card kpi"><div class="t">Tiendas donde pasa, por cadena</div><div class="v">{p1(R['sj_formato_min'])}–{p1(R['sj_formato_max'])}%</div><div class="p">en las {int(R['sj_formatos'])} cadenas con datos</div></div>
</div>

<div class="paso">Haz la cuenta con tu lista en 1 minuto</div>
<ol class="acciones">
<li><b>Divide</b> el precio entre las piezas (o gramos) de cada tamaño.</li>
<li><b>¿El grande sale más barato por unidad?</b> Si no, el cliente no tiene razón para llevarlo.</li>
<li><b>Si ahorra menos de 5%,</b> revísalo también.</li>
<li>Si pasa en varias cadenas, el tema es <b>la lista de precios, no una tienda.</b></li>
</ol>

<section class="card graf"><h2>Huevo San Juan: en cuántas tiendas de cada cadena pasa</h2>
<p class="nota" style="margin:0 0 6px">% de tiendas donde el cartón de 18 sale más caro por huevo que el de 12.</p>{g_cadenas}
<div class="nota">Son porcentajes de tiendas, no cambios de precio. Sin prueba de significancia en la gráfica; el rango probable está en el detalle.</div></section>

<section class="card graf"><h2>No es solo huevo</h2>
<p class="nota" style="margin:0 0 6px">% donde el tamaño grande sale más caro por unidad que el chico (Coca-Cola: % de sus comparaciones).</p>{g_marcas}
<div class="nota">Revisé {int(R['escalones']):,} comparaciones de tamaños en {int(R['tiendas'])} supermercados.</div></section>

<details><summary>Detalle por tamaño</summary>
<table><tr><th>Marca</th><th>Tamaños</th><th class="n">Grande más caro en</th><th class="n">Rango probable (90%)</th><th class="n">Cambio típico por unidad</th><th class="n">Tiendas</th></tr>{filas_tabla}</table>
<p class="nota">Cambio típico: ▲ vino = el grande cuesta más por unidad; ▼ azul = cuesta menos, lo esperado.</p></details>

<details><summary>Cómo se calculó y límites</summary>
<p class="nota">Cada comparación pone un tamaño contra el siguiente más chico de la misma tienda, por pieza, litro o kilo. Se revisaron marcas con 3 tamaños o más de la misma variante en 100 tiendas o más. El rango probable sale de un bootstrap de tiendas y municipios (500 réplicas). «Grande casi sin ahorro» significa descuento menor a 5% por unidad.</p>
<p class="nota">Solo supermercados que monitorea Profeco, una quincena de agosto de 2026. No mide el efecto en ventas ni explica por qué pasa; ningún resultado implica causalidad. Porcentajes con un decimal; pesos con dos.</p></details>
</main>

<div class="fuentes">
<table><tr><th>Dato</th><th>Valor</th><th>Fuente</th><th>Estatus</th></tr>{filas_fuentes}</table>
<p><b>Fuente:</b> elaboración propia con datos de Profeco, Quién es Quién en los Precios, quincena del 16 al 31 de agosto de 2026 (qqp.profeco.gob.mx).</p>
<p class="legal">Contenido informativo; no constituye asesoría legal, financiera ni comercial. Sin aval ni relación con Profeco ni con las empresas citadas. San Juan, El Calvario, La Costeña y Coca-Cola son marcas de sus respectivos titulares.</p>
</div>
<div class="filete"></div>
<footer><div class="n">{SELLO}<span>Ernesto Roldán</span></div><div class="r">Business Intelligence &amp; Analytics</div></footer>
</div></body></html>
"""


def build(path=SALIDA):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(HTML, encoding="utf-8")
    return Path(path)


if __name__ == "__main__":
    out = build()
    print(out, f"{out.stat().st_size / 1024:.0f} KB")
