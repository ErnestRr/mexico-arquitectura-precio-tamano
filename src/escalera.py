"""Arquitectura de precio por tamaño: escalones chico → grande del mismo producto y variante en la misma tienda
(motor pares.tamanos).

Escalón = un tamaño contra el siguiente más grande que la tienda tiene, por unidad (litro, kilo o pieza).
Cambio = precio por unidad del grande / del chico − 1. Lo esperado es que baje (descuento por volumen).
- Roto: el tamaño grande cuesta MÁS por unidad (cambio > 0).
- Plano: baja menos de 5% (casi sin descuento por volumen).
IC90 por bootstrap de dos vías: escalones (clave de producto y tamaños) y municipios, semilla 2026.
"""
import numpy as np
import pandas as pd

import entorno
import estadistica as E
import pares

CANAL = "Supermercado / Tienda de Autoservicio"
SEMILLA = 2026
MIN_TIENDAS3 = 100     # tiendas con 3 tamaños o más de la misma variante
PLANO = -5.0           # descuento menor a 5%: escalón plano
TOL = 1e-9
# Escaleras candidatas: marca literal, producto y patrón de la presentación que define la variante.
CANDIDATAS = {
    "Coca-Cola": ("Coca Cola", "Refresco", r"Lata 355|600 Ml|1 Lt|2\.75", "Refresco", "litro"),
    "Huevo San Juan": ("San Juan", "Huevo", "Blanco", "Huevo", "pieza"),
    "Huevo El Calvario": ("El Calvario", "Huevo", "Blanco", "Huevo", "pieza"),
    "Zucaritas": ("Zucaritas. Kellogg´s", "Cereales", r"30 Gr|380|600|620", "Cereal", "kilo"),
    "Chiles La Costeña en rajas": ("La Costeña", "Chiles", "Jalapeños Rajas", "Enlatados", "kilo"),
    "Agua Ciel": ("Ciel", "Agua Sin Gas", r"600 Ml|1 Lt|1\.5 Lt", "Agua", "litro"),
    "Galletas Saladitas": ("Gamesa", "Galletas Saladas", "Saladitas", "Galletas", "kilo"),
    "Caldo Knorr": ("Knorr", "Concentrado de Pollo", r"Frasco 450|Bolsa 750|Bolsa 950", "Condimentos", "kilo"),
    "Pan Bimbo blanco": ("Bimbo", "Pan de Caja", r"Rebanado Blanco$", "Pan", "kilo"),
    "Yoghurt Lala fresa (vaso y bote)": ("Lala", "Yoghurt", r"Vaso 120 Gr. Fresa|Bote 900 Gr. Fresa", "Lácteos", "kilo"),
}
KEY = {"Coca-Cola": "coca", "Huevo San Juan": "sj", "Huevo El Calvario": "ec", "Zucaritas": "zuc",
       "Chiles La Costeña en rajas": "raj"}


def load():
    st = entorno.tabla("tiendas")
    st = st[st.giro == CANAL].copy()
    pts = entorno.tabla("precio_tienda_sku", columns=["establecimiento_id", "sku_id", "precio", "observaciones"])
    pts = pts[pts.establecimiento_id.isin(st.establecimiento_id)].reset_index(drop=True)
    f = E.flag_prices(pts, sku="sku_id")
    pts["extremo"] = f.extremo.to_numpy()
    cat = entorno.tabla("sku_catalogo")
    return pts, st, cat


def skus(cat, nombre):
    m, p, pat, _, _ = CANDIDATAS[nombre]
    y = cat[(cat.marca == m) & (cat.producto == p) & cat.presentacion.str.contains(pat, regex=True)
            & ~cat.presentacion_ambigua & cat.cantidad_base.notna()]
    return y


def selection(pts, st, cat):
    """Tabla de candidatas con los criterios de selección."""
    rows = []
    for k, (m, p, pat, categoria, unidad) in CANDIDATAS.items():
        y = skus(cat, k)
        x = pts[pts.sku_id.isin(y.sku_id)]
        nt = x.groupby("establecimiento_id").sku_id.nunique()
        rows.append({"escalera": k, "categoria": categoria, "unidad": unidad, "tamanos": y.cantidad_base.nunique(),
                     "presentaciones": "; ".join(y.sort_values("cantidad_base").presentacion),
                     "tiendas_3_tamanos": int((nt >= 3).sum()), "empresa_verificada": y.empresa_propietaria.dropna().unique().tolist()})
    out = pd.DataFrame(rows)
    out["seleccionada"] = (out.tamanos >= 3) & (out.tiendas_3_tamanos >= MIN_TIENDAS3)
    return out


def steps(pts, st, cat, nombre):
    y = skus(cat, nombre)
    ids = set(y.sku_id)
    p = pares.tamanos(pts, st, cat, y.familia.iloc[0], y.producto.iloc[0], filtro=lambda x: x.sku_id.isin(ids))
    p["escalera"] = nombre
    p["cambio_pct"] = (p.precio_b / p.precio_a - 1) * 100
    p["clase"] = np.select([p.cambio_pct > TOL, p.cambio_pct > PLANO], ["roto", "plano"], "con descuento")
    p["escalon"] = p.tam_a.map(_fmt_size(nombre)) + " → " + p.tam_b.map(_fmt_size(nombre))
    tam = sorted(y.cantidad_base.unique())
    p["contiguo"] = [tam.index(b) - tam.index(a) == 1 for a, b in zip(p.tam_a, p.tam_b)]
    return p


def _fmt_size(nombre):
    unidad = CANDIDATAS[nombre][4]

    def f(q):
        if unidad == "pieza":
            return f"{q:.0f} pzas"
        if unidad == "litro":
            return f"{q * 1000:.0f} ml" if q < 1 else f"{q:g} L"
        return f"{q * 1000:.0f} g" if q < 1 else f"{q:g} kg"
    return f


def _w2(clave, mun, rng):
    kc, ku = pd.factorize(clave)
    mc, mu = pd.factorize(mun)
    while True:
        yield (np.bincount(rng.integers(0, len(ku), len(ku)), minlength=len(ku))[kc] *
               np.bincount(rng.integers(0, len(mu), len(mu)), minlength=len(mu))[mc]).astype(float)


def broken(p, reps=500, seed=SEMILLA):
    """% de escalones rotos y planos, cambio mediano, IC90 de dos vías del % roto."""
    rot = (p.cambio_pct > TOL).to_numpy(float)
    d = {"escalones": len(p), "tiendas": p.establecimiento_id.nunique(), "municipios": p.municipio_id.nunique(),
         "pct_roto": rot.mean() * 100, "pct_plano": ((p.cambio_pct <= TOL) & (p.cambio_pct > PLANO)).mean() * 100,
         "cambio_mediano": float(np.median(p.cambio_pct)),
         "cambio_roto_mediano": float(np.median(p.cambio_pct[p.cambio_pct > TOL])) if rot.any() else np.nan}
    if len(p) >= 10:
        gen = _w2(p.clave.to_numpy(), p.municipio_id.to_numpy(), np.random.default_rng(seed))
        vals = [np.average(rot, weights=w) * 100 if w.sum() else np.nan for w, _ in zip(gen, range(reps))]
        d["ic90_inf"], d["ic90_sup"] = np.nanpercentile(vals, [5, 95])
    else:
        d["ic90_inf"] = d["ic90_sup"] = np.nan
    return d


def by(p, cols, min_n=20, reps=300):
    rows = [{**dict(zip([cols] if isinstance(cols, str) else cols, k if isinstance(k, tuple) else (k,))), **broken(g, reps)}
            for k, g in p.groupby(cols) if len(g) >= min_n]
    return pd.DataFrame(rows)


def ladder_prices(p_all):
    """Precio por unidad mediano de cada tamaño, en las tiendas que tienen el escalón (para la gráfica)."""
    a = p_all[["escalera", "establecimiento_id", "tam_a", "precio_a"]].rename(columns={"tam_a": "tam", "precio_a": "pu"})
    b = p_all[["escalera", "establecimiento_id", "tam_b", "precio_b"]].rename(columns={"tam_b": "tam", "precio_b": "pu"})
    x = pd.concat([a, b]).drop_duplicates(["escalera", "establecimiento_id", "tam"])
    return x.groupby(["escalera", "tam"]).agg(pu=("pu", "median"), tiendas=("establecimiento_id", "nunique")).reset_index()
