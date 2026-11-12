# Copiado de _profeco_core/src/pares.py por publicar.py; no editar aquí.
"""Motor único de comparación en pares (análisis 7, 8, 9 y 10).

Tres reglas de emparejamiento devuelven una tabla de pares con el mismo formato:
- `formatos(...)`:  formato A vs. formato B, mismo SKU, misma ciudad (precio de cada formato = mediana de sus tiendas
                    en la ciudad).
- `marcas(...)`:    marca A vs. marca B, misma tienda, presentación equivalente (misma clave), por unidad o por pieza.
- `tamanos(...)`:   tamaño chico vs. grande del mismo producto y variante, misma tienda, por unidad.

Tabla de pares: precio_a, precio_b (lo que se compara: precio o precio por unidad), pesos_a, pesos_b (precio del
empaque, para la brecha en pesos), clave (SKU o producto equivalente), municipio_id, region y, si aplica,
establecimiento_id, cadena, formato, grupo.

`resumir(pares, ...)` calcula:
- brecha en % = mediana de log(b / a), expresada en % (robusta a extremos, simétrica);
- brecha en pesos = mediana de (pesos_b − pesos_a);
- % de casos invertidos = pares donde el signo contradice lo esperado (p. ej., el tamaño grande sale más caro por
  unidad);
- IC90 por bootstrap de dos vías: remuestrea a la vez claves de producto y municipios (semilla 2026). Los precios de
  una cadena son casi nacionales, así que remuestrear solo municipios da intervalos falsamente estrechos (lección del
  análisis 5); remuestrear solo productos ignora que las tiendas de una ciudad no son independientes;
- n de pares, claves, tiendas y municipios; y el mismo resumen por cadena, formato o región.
"""
import numpy as np
import pandas as pd

SEMILLA = 2026


# --------------------------------------------------------------------------- reglas
def _base(pts, tiendas, catalogo=None):
    x = pts.merge(tiendas[["establecimiento_id", "cadena_comercial", "formato", "grupo", "giro", "municipio_id",
                           "region"]], on="establecimiento_id", how="inner", validate="many_to_one")
    if catalogo is not None:
        x = x.merge(catalogo, on="sku_id", how="left", validate="many_to_one")
    return x


def formatos(pts, tiendas, formato_a, formato_b, campo="formato"):
    """Mismo SKU y misma ciudad: mediana del formato A vs. mediana del formato B."""
    x = _base(pts, tiendas)
    x = x[x[campo].isin([formato_a, formato_b])]
    g = x.groupby(["sku_id", "municipio_id", "region", campo], observed=True).precio.median().unstack(campo)
    if formato_a not in g or formato_b not in g:
        return pd.DataFrame(columns=["clave", "municipio_id", "region", "precio_a", "precio_b", "pesos_a", "pesos_b"])
    g = g[[formato_a, formato_b]].dropna().reset_index()
    out = pd.DataFrame({"clave": g.sku_id, "municipio_id": g.municipio_id, "region": g.region,
                        "precio_a": g[formato_a], "precio_b": g[formato_b]})
    out["pesos_a"], out["pesos_b"] = out.precio_a, out.precio_b
    out["a"], out["b"] = formato_a, formato_b
    return out.reset_index(drop=True)


def marcas(pts, tiendas, catalogo, marca_a, marca_b, clave, por="unidad", tamano=None, filtro=None):
    """Misma tienda, presentación equivalente.

    marca_a, marca_b: familia de marca (o lista de familias) de cada lado.
    clave: columnas del catálogo que definen la equivalencia (p. ej. ["producto", "variedad"]); el emparejamiento
           exige la misma clave en la misma tienda.
    por: "unidad" (precio por kg, litro o pieza base), "pieza" (precio / piezas) o "empaque" (precio tal cual).
    tamano: (min, max) razón de tamaño admitida entre b y a; None = cualquiera (si por="empaque" debe ser igual).
    filtro: función opcional sobre el catálogo unido (p. ej., excluir presentaciones ambiguas).
    """
    x = _base(pts, tiendas, catalogo)
    if filtro is not None:
        x = x[filtro(x)]
    fa = [marca_a] if isinstance(marca_a, str) else list(marca_a)
    fb = [marca_b] if isinstance(marca_b, str) else list(marca_b)
    x = x[x.familia.isin(fa + fb)].copy()
    x["lado"] = np.where(x.familia.isin(fa), "a", "b")
    if por == "unidad":
        x["comp"], x["tam"] = x.precio / x.cantidad_base, x.cantidad_base
    elif por == "pieza":
        x["comp"], x["tam"] = x.precio / x.piezas, x.piezas
    else:
        x["comp"], x["tam"] = x.precio, x.cantidad_base
    x = x[np.isfinite(x.comp) & (x.comp > 0)]
    keys = ["establecimiento_id", "cadena_comercial", "formato", "grupo", "municipio_id", "region"] + list(clave)
    agg = x.groupby(keys + ["lado"], observed=True, dropna=False).agg(comp=("comp", "median"), pesos=("precio", "median"),
                                                                       tam=("tam", "median")).unstack("lado")
    agg = agg.dropna(subset=[("comp", "a"), ("comp", "b")])
    if tamano is not None:
        r = agg[("tam", "b")] / agg[("tam", "a")]
        agg = agg[(r >= tamano[0]) & (r <= tamano[1])]
    agg = agg.reset_index()
    out = agg[keys].copy()
    out.columns = keys
    out["clave"] = agg[list(clave)].astype(str).agg(" · ".join, axis=1)
    out["precio_a"], out["precio_b"] = agg[("comp", "a")].to_numpy(), agg[("comp", "b")].to_numpy()
    out["pesos_a"], out["pesos_b"] = agg[("pesos", "a")].to_numpy(), agg[("pesos", "b")].to_numpy()
    out["a"], out["b"] = " / ".join(fa), " / ".join(fb)
    return out.reset_index(drop=True)


def tamanos(pts, tiendas, catalogo, familia, producto, variante=None, filtro=None):
    """Misma tienda, mismo producto, marca y variante: cada tamaño contra el siguiente más grande, por unidad.
    a = tamaño chico, b = tamaño grande; lo esperado es que b cueste menos por unidad (brecha negativa).
    variante: columna del catálogo (o función sobre el catálogo unido) que define la variante; None = sin variante."""
    x = _base(pts, tiendas, catalogo)
    x = x[(x.familia == familia) & (x.producto == producto) & x.cantidad_base.notna()].copy()
    if filtro is not None:
        x = x[filtro(x)]
    x["variante"] = (variante(x) if callable(variante) else x[variante].astype(str)) if variante is not None else ""
    x["pu"] = x.precio / x.cantidad_base
    rows = []
    keys = ["establecimiento_id", "cadena_comercial", "formato", "grupo", "municipio_id", "region", "variante"]
    for k, g in x.groupby(keys, observed=True, dropna=False):
        s = g.groupby("cantidad_base").agg(pu=("pu", "median"), pesos=("precio", "median")).sort_index()
        for (q1, r1), (q2, r2) in zip(s.iloc[:-1].iterrows(), s.iloc[1:].iterrows()):
            rows.append(dict(zip(keys, k), tam_a=q1, tam_b=q2, precio_a=r1.pu, precio_b=r2.pu,
                             pesos_a=r1.pesos, pesos_b=r2.pesos))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["clave"] = familia + " · " + producto + " · " + out.variante.astype(str) + " · " + \
        out.tam_a.astype(str) + "→" + out.tam_b.astype(str)
    out["a"], out["b"] = "chico", "grande"
    return out


# --------------------------------------------------------------------------- resumen
def _wmedian(v, w):
    o = np.argsort(v)
    v, w = v[o], w[o]
    c = np.cumsum(w)
    return v[np.searchsorted(c, c[-1] / 2)]


def _boot(lr, clave, mun, reps, seed):
    rng = np.random.default_rng(seed)
    kc, ku = pd.factorize(clave)
    mc, mu = pd.factorize(mun)
    vals = np.full(reps, np.nan)
    for r in range(reps):
        w = (np.bincount(rng.integers(0, len(ku), len(ku)), minlength=len(ku))[kc] *
             np.bincount(rng.integers(0, len(mu), len(mu)), minlength=len(mu))[mc]).astype(float)
        k = w > 0
        if k.sum():
            vals[r] = _wmedian(lr[k], w[k])
    return (np.exp(np.nanpercentile(vals, [5, 95])) - 1) * 100


def _one(p, esperado, reps, seed, ic=True):
    lr = np.log(p.precio_b.to_numpy() / p.precio_a.to_numpy())
    d = {"n_pares": int(len(p)), "claves": int(p.clave.nunique()), "municipios": int(p.municipio_id.nunique()),
         "tiendas": int(p.establecimiento_id.nunique()) if "establecimiento_id" in p else None,
         "brecha_pct": float((np.exp(np.median(lr)) - 1) * 100) if len(p) else np.nan,
         "brecha_pesos": float(np.median(p.pesos_b - p.pesos_a)) if len(p) else np.nan,
         "pct_iguales": float((np.abs(lr) < 1e-9).mean() * 100) if len(p) else np.nan}
    if esperado == "b>a":
        d["pct_invertidos"] = float((lr < -1e-9).mean() * 100) if len(p) else np.nan
    elif esperado == "b<a":
        d["pct_invertidos"] = float((lr > 1e-9).mean() * 100) if len(p) else np.nan
    else:
        d["pct_invertidos"] = np.nan
    if ic and len(p) >= 5:
        lo, hi = _boot(lr, p.clave.to_numpy(), p.municipio_id.to_numpy(), reps, seed)
        d["ic90_inf"], d["ic90_sup"] = float(lo), float(hi)
    else:
        d["ic90_inf"] = d["ic90_sup"] = np.nan
    return d


def resumir(pares, esperado=None, por=("cadena_comercial", "formato", "region"), reps=500, seed=SEMILLA,
            min_pares=20, ic_desglose=True):
    """Brecha b vs. a en % y en pesos, % invertidos, IC90 y n; total y desglose por cada columna de `por`.

    esperado: "b>a" (b debería costar más; invertido = b más barato), "b<a" o None.
    Devuelve (total: dict, desglose: DataFrame con columna 'por' y 'grupo')."""
    total = _one(pares, esperado, reps, seed)
    rows = []
    for col in por:
        if col not in pares:
            continue
        for k, g in pares.groupby(col, observed=True):
            if len(g) >= min_pares:
                rows.append({"por": col, "grupo": k, **_one(g, esperado, reps, seed, ic=ic_desglose)})
    return total, pd.DataFrame(rows)
