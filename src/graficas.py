"""Gráficas de la arquitectura de precio por tamaño con la plantilla del núcleo (charts.py).

Convenciones: rojo ▼ = el tamaño grande cuesta menos por unidad (lo esperado); verde ▲ = cuesta más (escalón roto);
gris = sin cambio; dorado = referencia.
"""
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator
from matplotlib.transforms import blended_transform_factory

import charts as C
from charts import n, b, g, r, minus, _box, _finish, _canvas, _frame, _save

import escalera as S

SRC_E = C.SRC + ". Supermercados; mismo producto y variante en la misma tienda."
UNIT = {"litro": "por litro", "kilo": "por kilo", "pieza": "por pieza"}


def gold(t):
    return (t, True, C.GOLD)


def _sizes(lp, k):
    d = lp[(lp.escalera == k) & (lp.tiendas >= 20)].sort_values("tam")
    return d


def _panel(ax, lp, be, k, size=6.6, compact=False):
    d = _sizes(lp, k)
    fmt = S._fmt_size(k)
    xs = np.arange(len(d))
    base = d.pu.iloc[0]
    y = d.pu.to_numpy() / base * 100
    steps = be[be.escalera == k].set_index("escalon")
    for i in range(len(d) - 1):
        lab = f"{fmt(d.tam.iloc[i])} → {fmt(d.tam.iloc[i + 1])}"
        rot = steps.pct_roto.get(lab, np.nan)
        up = y[i + 1] > y[i]
        col = C.GREEN if up else C.RED
        ax.plot(xs[i:i + 2], y[i:i + 2], color=col, lw=3.4 if up else 2.4, zorder=3, solid_capstyle="round")
        if not np.isnan(rot):
            strong = rot >= 25
            ax.text((xs[i] + xs[i + 1]) / 2, max(y[i], y[i + 1]) + 6, f"rota en\n{rot:.0f}%" if not compact else f"{rot:.0f}%",
                    ha="center", va="bottom", fontsize=size - 0.6, color=C.GREEN_T if strong else C.TEXT2,
                    fontweight="bold" if strong else "normal", linespacing=1.05, path_effects=C.HALO, zorder=5)
    ax.scatter(xs, y, s=46, color=C.TEXT, zorder=4)
    for xi, yi, pu in zip(xs, y, d.pu):
        ax.text(xi, yi - 7, C.money(pu), ha="center", va="top", fontsize=size - 0.8, color=C.TEXT2, path_effects=C.HALO)
    ax.set_xticks(xs, [fmt(t) for t in d.tam], fontsize=size - 0.6)
    ax.set(xlim=(-0.4, len(d) - 0.6), ylim=(min(20, y.min() - 20), max(125, y.max() + 25)))
    ax.axhline(100, color=C.GOLD, lw=0.9, ls=(0, (4, 3)), zorder=1)
    ax.yaxis.set_major_locator(MultipleLocator(25))
    _frame(ax, grid="y", size=size - 0.8)
    ax.set_title(f"{k}", loc="left", fontsize=size + 1.2, fontweight="bold", color=C.TEXT, pad=14)
    ax.text(0, 1.02, f"precio {UNIT[S.CANDIDATAS[k][4]]}; tamaño chico = 100", transform=ax.transAxes, fontsize=size - 1,
            color=C.TEXT2, va="bottom")


# --------------------------------------------------------------------------- 01 principal
def ladders(lp, be, sel, res, path, svg=True):
    order = ["Huevo San Juan", "Huevo El Calvario", "Chiles La Costeña en rajas", "Zucaritas", "Coca-Cola"]
    order = [k for k in order if k in sel]
    fig = _canvas(2200, 1500)
    pos = [(0.06, 0.46), (0.385, 0.46), (0.71, 0.46), (0.06, 0.08), (0.385, 0.08)]
    for k, (x0, y0) in zip(order, pos):
        ax = fig.add_axes([x0, y0, 0.26, 0.25])
        _panel(ax, lp, be, k)
    _box(fig, 0.71, 0.33, [b("¿Cómo leer?"), "Cada panel: precio por unidad de cada tamaño",
                           "(mediana de las tiendas), con el chico = 100.", [r("▼ rojo"), n(": el grande sale más barato por unidad.")],
                           [g("▲ verde"), n(": escalón roto, el grande cuesta más.")],
                           "«Rota en X%»: tiendas donde ese escalón está roto.", "Abajo de cada punto: precio por unidad."], "ul",
         size=7.6)
    v = res
    _finish(fig, [[n("El tamaño grande no siempre sale más barato: en "), g(f"{v['roto_sj_12_18']:.0f}%"),
                   n(" de las tiendas, un huevo San Juan")],
                  [n("cuesta más en el paquete de 18 que en el de 12; en Coca-Cola solo se rompe "), b(f"{v['roto_coca']:.1f}%"),
                   n(" de los escalones")]],
            f"Precio por unidad según tamaño, mismo producto y variante en la misma tienda; {v['escalones']:,.0f} escalones en "
            f"{v['tiendas']:.0f} supermercados",
            [n(SRC_E)], size=13, foot=6.4, top=1 - 26 / 1500)
    return _save(fig, path, svg)


def ladders_social(lp, be, res, fmt, path):
    W, H = C.SOCIAL[fmt]
    vertical = H > W
    fig = C.social_canvas(fmt)
    v = res
    if vertical:
        ks = ["Huevo San Juan", "Coca-Cola"]
        boxes = [(0.12, 0.47, 0.8, 0.26), (0.12, 0.1, 0.8, 0.26)]
        title = [[n("¿El tamaño grande sale más barato?")], [n("Huevo San Juan: de 12 a 18 piezas, el")],
                 [n("huevo sube en "), g(f"{v['roto_sj_12_18']:.0f}%"), n(" de las tiendas")]]
        sub = "Precio por unidad según tamaño en la misma tienda; 16–31 ago 2026"
    else:
        ks = ["Huevo San Juan", "Coca-Cola"]
        boxes = [(0.07, 0.17, 0.4, 0.5), (0.56, 0.17, 0.4, 0.5)]
        title = [[n("En "), g(f"{v['roto_sj_12_18']:.0f}%"), n(" de las tiendas, un huevo San Juan cuesta más en el")],
                 [n("paquete de 18 que en el de 12; en Coca-Cola el grande casi siempre sale más barato")]]
        sub = "Precio por unidad según tamaño, mismo producto en la misma tienda (tamaño chico = 100); 16–31 ago 2026"
    for k, bx in zip(ks, boxes):
        ax = fig.add_axes(bx)
        _panel(ax, lp, be, k, size=6.2, compact=False)
    C.finish_social(fig, title, sub, [n("Fuente: elaboración propia con datos de PROFECO, Quién es Quién en los Precios.")],
                    size=12.5 if vertical else 11, foot=5.4)
    fig.savefig(path, dpi=fig.dpi)
    return fig


# --------------------------------------------------------------------------- 02 por escalón
def broken_by_step(be, res, path):
    d = be.sort_values(["pct_roto"], ascending=False).reset_index(drop=True)
    k = len(d)
    row = 62
    top_px, bot_px = 420, 170
    h = top_px + bot_px + row * k
    fig = _canvas(2000, h)
    L = 0.33
    ax = fig.add_axes([L, bot_px / h, 0.42, row * k / h])
    ax.patch.set_alpha(0)
    tr = blended_transform_factory(fig.transFigure, ax.transData)
    for i, r_ in d.iterrows():
        if i % 2 == 0:
            ax.add_patch(Rectangle((0.015, i - 0.5), 0.97, 1, transform=tr, color=C.ZEBRA, lw=0, zorder=0))
        col = C.GREEN if r_.pct_roto >= 5 else C.NEUTRAL
        ax.barh(i, r_.pct_roto, height=0.56, color=col, alpha=0.85, zorder=2)
        ax.hlines(i, r_.ic90_inf, r_.ic90_sup, color=C.TEXT, lw=1.4, zorder=3)
        ax.text(L - 0.012, i - 0.12, r_.escalera, transform=tr, ha="right", va="center", fontsize=7.8, fontweight="bold")
        ax.text(L - 0.012, i + 0.25, r_.escalon, transform=tr, ha="right", va="center", fontsize=6.4, color=C.TEXT2)
        ax.text(0.77, i, f"{r_.pct_roto:.0f}%", transform=tr, ha="left", va="center", fontsize=8.2, fontweight="bold",
                color=C.GREEN_T if r_.pct_roto >= 5 else C.TEXT2)
        ax.text(0.83, i, f"IC90 {r_.ic90_inf:.0f}–{r_.ic90_sup:.0f}", transform=tr, ha="left", va="center", fontsize=6.4,
                color=C.TEXT2)
        ax.text(0.975, i, minus(f"{r_.cambio_mediano:+.0f}%"), transform=tr, ha="right", va="center", fontsize=7,
                color=C.GREEN_T if r_.cambio_mediano > 0 else C.RED_T)
    hy = (bot_px + row * k + 8) / h
    for x, lab, ha in [(0.77, "Rota en", "left"), (0.975, "Cambio\ntípico", "right")]:
        fig.text(x, hy, lab, ha=ha, va="bottom", fontsize=7, fontweight="bold", color=C.TEXT2, linespacing=1.15)
    ax.set(xlim=(0, 100), ylim=(k - 0.5, -0.5), yticks=[])
    ax.xaxis.set_major_locator(MultipleLocator(25))
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
    _frame(ax, grid="x", size=7.2)
    ax.set_xlabel("% de las tiendas donde el tamaño grande cuesta más por unidad (escalón roto)", fontsize=7.4, labelpad=4)
    _box(fig, 0.03, 1 - 200 / h, [[b("¿Cómo leer?  "), n("Barra: % de tiendas con el escalón roto (el tamaño grande cuesta más por unidad); "
                                   "línea blanca: rango probable (IC 90%).")],
                                  [n("Cambio típico: cuánto cambia el precio por unidad al pasar al tamaño grande. "), r("▼ rojo"),
                                   n(": baja, como se espera; "), g("▲ verde"), n(": sube.")]], "ul", size=7.4)
    v = res
    _finish(fig, [[n("Cada marca rompe su escalera en un escalón: huevo San Juan de 12 a 18 piezas en "),
                   g(f"{v['roto_sj_12_18']:.0f}%"), n(" de las tiendas,")],
                  [n("El Calvario de 18 a 30 en "), g(f"{v['roto_ec_18_30']:.0f}%"), n(" y rajas La Costeña de 240 a 340 g en "),
                   g(f"{v['roto_raj_240_340']:.0f}%")]],
            "Escalones contiguos con 20 tiendas o más; IC90 por bootstrap de tiendas y municipios",
            [n(SRC_E)], size=12.5, foot=6.4, top=1 - 26 / h)
    return _save(fig, path)


# --------------------------------------------------------------------------- 03 por formato
def broken_by_format(bf, res, path):
    d = bf.sort_values("pct_roto", ascending=False).reset_index(drop=True)
    k = len(d)
    row = 58
    top_px, bot_px = 410, 170
    h = top_px + bot_px + row * k
    fig = _canvas(1900, h)
    L = 0.24
    ax = fig.add_axes([L, bot_px / h, 0.5, row * k / h])
    ax.patch.set_alpha(0)
    tr = blended_transform_factory(fig.transFigure, ax.transData)
    for i, r_ in d.iterrows():
        if i % 2 == 0:
            ax.add_patch(Rectangle((0.015, i - 0.5), 0.97, 1, transform=tr, color=C.ZEBRA, lw=0, zorder=0))
        ax.hlines(i, r_.ic90_inf, r_.ic90_sup, color=C.GREEN, lw=7, alpha=0.4, zorder=2)
        ax.scatter([r_.pct_roto], [i], s=110, marker="D", color=C.GREEN if r_.pct_roto > 0 else C.NEUTRAL, edgecolor=C.TEXT,
                   lw=0.8, zorder=3)
        ax.text(L - 0.012, i, r_.formato, transform=tr, ha="right", va="center", fontsize=7.8, fontweight="bold")
        ax.text(0.77, i, f"{r_.pct_roto:.0f}%", transform=tr, ha="left", va="center", fontsize=8, fontweight="bold",
                color=C.GREEN_T if r_.pct_roto > 0 else C.TEXT2)
        ax.text(0.975, i, f"{int(r_.escalones)} escalones · {int(r_.tiendas)} tiendas", transform=tr, ha="right", va="center",
                fontsize=6.4, color=C.TEXT2)
    v = res
    ax.axvline(v["roto_total"], color=C.GOLD, lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.set(xlim=(0, 70), ylim=(k - 0.5, -0.5), yticks=[])
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
    _frame(ax, grid="x", size=7.2)
    ax.set_xlabel("% de escalones rotos en la cadena (las cinco escaleras juntas)", fontsize=7.4, labelpad=4)
    _box(fig, 0.03, 1 - 200 / h, [[b("¿Cómo leer?  "), b("◆"), n(" % de escalones rotos en la cadena; barra: IC 90%. "),
                                   ("Línea dorada", True, C.GOLD), n(f": total ({v['roto_total']:.0f}%).")],
                                  [n("Con la misma mezcla de escalones, ninguna cadena se aleja más de "),
                                   b(f"{v['ajuste_max_pp']:.0f} puntos"), n(" de lo esperado.")]], "ul", size=7.4)
    _finish(fig, [[n("La escalera se rompe en casi todas las cadenas: de "), b(f"{v['formato_min']:.0f}%"), n(" a "),
                   g(f"{v['formato_max']:.0f}%"), n(" de los escalones;")],
                  [n("el paso de 12 a 18 huevos San Juan está roto en "), g(f"{v['sj_formato_min']:.0f}–{v['sj_formato_max']:.0f}%"),
                   n(" de las tiendas de cada cadena")]],
            "% de escalones rotos por cadena (formato) con 20 escalones o más; IC90 por bootstrap de tiendas y municipios",
            [n(SRC_E)], size=12.5, foot=6.4, top=1 - 26 / h)
    return _save(fig, path)


# --------------------------------------------------------------------------- 04 caso huevo
def egg_case(p, res, path):
    fig = _canvas(2000, 1150)
    v = res
    cases = [("Huevo San Juan", "12 pzas → 18 pzas", "San Juan: de 12 a 18 piezas"),
             ("Huevo El Calvario", "18 pzas → 30 pzas", "El Calvario: de 18 a 30 piezas")]
    for j, (k, e, lab) in enumerate(cases):
        x = p[(p.escalera == k) & (p.escalon == e)].cambio_pct.to_numpy()
        ax = fig.add_axes([0.07 + j * 0.47, 0.17, 0.4, 0.5])
        bins = np.arange(-20, 22.5, 2.5)
        cnt, edges = np.histogram(np.clip(x, -20, 19.99), bins=bins)
        sh = cnt / len(x) * 100
        for c_, e0 in zip(sh, edges[:-1]):
            ax.bar(e0, c_, width=2.5, align="edge", color=C.GREEN if e0 >= 0 else C.RED, edgecolor=C.FIG, lw=0.8, zorder=2)
        ax.axvline(0, color=C.GOLD, lw=1.4, ls=(0, (4, 3)), zorder=3)
        med = np.median(x)
        rot = (x > 0).mean() * 100
        ax.set(xlim=(-20, 20), ylim=(0, sh.max() * 1.3))
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.xaxis.set_major_formatter(lambda t, _: "igual" if abs(t) < 1e-9 else minus(f"{t:+.0f}%"))
        ax.yaxis.set_major_formatter(lambda t, _: f"{t:.0f}%")
        _frame(ax, grid="y", size=7)
        ax.set_title(lab, loc="left", fontsize=8.6, fontweight="bold", pad=8)
        ax.text(0.98, 0.96, f"más caro por pieza\nen {rot:.0f}% de {len(x)} tiendas", transform=ax.transAxes, ha="right", va="top",
                fontsize=7.4, color=C.GREEN_T, fontweight="bold", linespacing=1.15)
        ax.set_xlabel("Cambio del precio por pieza al pasar al paquete grande", fontsize=7.2, labelpad=4)
        if j == 0:
            ax.set_ylabel("% de las tiendas", fontsize=7.4)
    _box(fig, 0.07, 0.80, [[b("¿Cómo leer?  "), n("Cada barra: % de tiendas con ese cambio del precio por huevo al comprar el paquete grande. "),
                            g("▲ verde"), n(": el grande cuesta más por pieza.")]], "ul", size=7.4)
    _finish(fig, [[n("En "), g(f"{v['roto_sj_12_18']:.0f}%"), n(" de las tiendas, un huevo San Juan cuesta más en el paquete de 18 que en el de 12;")],
                  [n("en El Calvario el paquete de 30 sale más caro por pieza que el de 18 en "), g(f"{v['roto_ec_18_30']:.0f}%")]],
            "Cambio del precio por pieza entre paquetes de huevo blanco de la misma marca en la misma tienda",
            [n(SRC_E)], size=12.5, foot=6.4, top=1 - 26 / 1150)
    return _save(fig, path)
