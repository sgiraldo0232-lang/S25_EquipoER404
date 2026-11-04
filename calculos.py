"""Funciones de cálculo del observatorio (sin Streamlit, para poder probarlas por separado)."""
from itertools import combinations

import numpy as np
import pandas as pd

DIAS_ANIO = 252  # convención: sesiones de trading al año; todos los activos se alinean a fechas comunes


# ------------------------------------------------------------------ datos
def alinear_fechas(cierre: pd.DataFrame) -> pd.DataFrame:
    """Conserva solo las fechas en que TODOS los activos tienen precio (sin rellenar)."""
    return cierre.sort_index().dropna(how="any")


def simular_precios(simbolos, inicio, fin, semilla=23):
    """Precios SIMULADOS (solo para practicar sin internet). Nunca son cotizaciones reales."""
    rng = np.random.default_rng(semilla)
    fechas = pd.bdate_range(inicio, fin)
    sigmas = {"BTC-USD": 0.035, "SPY": 0.011, "GLD": 0.009, "TLT": 0.009}
    return pd.DataFrame({t: 100 * np.cumprod(1 + rng.normal(0.0003, sigmas.get(t, 0.012), len(fechas)))
                         for t in simbolos}, index=fechas)


# -------------------------------------------------------------- indicadores
def rendimientos(precios):
    return precios.pct_change().dropna()


def cagr(precios):
    """Rendimiento anualizado geométrico: (P_final/P_inicial)^(252/n) - 1, con n = número de rendimientos."""
    n = len(precios) - 1
    return (precios.iloc[-1] / precios.iloc[0]) ** (DIAS_ANIO / n) - 1


def vol_anual(rend):
    return rend.std(ddof=1) * np.sqrt(DIAS_ANIO)


def drawdown(precios):
    return precios / precios.cummax() - 1


def recuperacion(precios):
    """Máximo drawdown, fechas de pico y valle y días hasta recuperar el pico (o NaT si no se recuperó)."""
    filas = {}
    for t in precios.columns:
        s = precios[t]
        dd = s / s.cummax() - 1
        valle = dd.idxmin()
        pico = s.loc[:valle].idxmax()
        despues = s.loc[valle:]
        rec = despues[despues >= s.loc[pico]]
        fecha_rec = rec.index[0] if len(rec) else pd.NaT
        filas[t] = {"Máximo drawdown": dd.min(), "Pico": pico, "Valle": valle, "Recuperación": fecha_rec,
                    "Días valle→recuperación": (fecha_rec - valle).days if pd.notna(fecha_rec) else np.nan}
    return pd.DataFrame(filas).T


def resumen(precios, rf=0.0):
    rend = rendimientos(precios)
    c, v = cagr(precios), vol_anual(rend)
    return pd.DataFrame({
        "Rendimiento acumulado": precios.iloc[-1] / precios.iloc[0] - 1,
        "Rendimiento anualizado": c,
        "Volatilidad anualizada": v,
        "Rendimiento/riesgo": (c - rf) / v,
        "Máximo drawdown": drawdown(precios).min(),
    })


# -------------------------------------------------------------- correlación
def pares(columnas):
    return list(combinations(columnas, 2))


def regimenes(indice, minimo=60):
    """Subperíodos de análisis que tienen al menos `minimo` sesiones dentro de los datos."""
    candidatos = {"2021": ("2021-01-01", "2021-12-31"), "2022": ("2022-01-01", "2022-12-31"),
                  "2023–2025": ("2023-01-01", "2025-12-31")}
    salida = {}
    for nombre, (a, b) in candidatos.items():
        if len(indice[(indice >= a) & (indice <= b)]) >= minimo:
            salida[nombre] = (a, b)
    return salida


def correlacion_por_periodo(rend, periodos):
    """Tabla pares × subperíodos (más el período completo)."""
    cols = {"Período completo": rend}
    for nombre, (a, b) in periodos.items():
        cols[nombre] = rend.loc[a:b]
    filas = {f"{x}–{y}": {n: r[x].corr(r[y]) for n, r in cols.items()} for x, y in pares(rend.columns)}
    return pd.DataFrame(filas).T


def correlacion_media(rend):
    c = rend.corr().values
    return c[np.triu_indices_from(c, k=1)].mean()


def refugio(rend, ref="SPY", umbral=-0.01):
    """Rendimiento medio de cada activo en los días en que `ref` cayó más que `umbral`."""
    if ref not in rend.columns:
        return None, 0
    dias = rend[rend[ref] < umbral]
    otros = [c for c in rend.columns if c != ref]
    return dias[otros].mean(), len(dias)


# -------------------------------------------------------------- estadística
def atipicos(rend):
    """Valores atípicos con la regla 1,5 × IQR (la misma del boxplot)."""
    q1, q3 = rend.quantile(.25), rend.quantile(.75)
    iqr = q3 - q1
    mask = (rend < q1 - 1.5 * iqr) | (rend > q3 + 1.5 * iqr)
    filas = {}
    for t in rend.columns:
        ext = rend[t].abs().idxmax()
        filas[t] = {"Atípicos (n)": int(mask[t].sum()), "Día más extremo": ext.date(), "Rendimiento ese día": rend.loc[ext, t]}
    return pd.DataFrame(filas).T


def riesgo_pares(rend):
    """Volatilidad anualizada de cada par con pesos 50/50 (rebalanceo diario) y su correlación."""
    filas = {f"{x}–{y}": {"Correlación": rend[x].corr(rend[y]),
                          "Volatilidad par 50/50": rend[[x, y]].mean(axis=1).std(ddof=1) * np.sqrt(DIAS_ANIO)}
             for x, y in pares(rend.columns)}
    return pd.DataFrame(filas).T.sort_values("Volatilidad par 50/50")


# ------------------------------------------------------------ conclusiones
def conclusiones(precios, rf=0.0):
    """Texto en Markdown redactado con los números de los datos (así siempre coincide con las tablas)."""
    rend = rendimientos(precios)
    res = resumen(precios, rf)
    rec = recuperacion(precios)
    mejor_ratio = res["Rendimiento/riesgo"].idxmax()
    mejor_cagr = res["Rendimiento anualizado"].idxmax()
    mas_vol = res["Volatilidad anualizada"].idxmax()
    peor_dd = res["Máximo drawdown"].idxmin()
    L = []
    L.append(f"**Rendimiento ajustado por riesgo.** {mejor_ratio} tuvo la mejor relación rendimiento/riesgo "
             f"({res.loc[mejor_ratio, 'Rendimiento/riesgo']:.2f}, con tasa libre de riesgo de {rf:.1%}). "
             f"{mejor_cagr} tuvo el mayor rendimiento anualizado ({res.loc[mejor_cagr, 'Rendimiento anualizado']:+.2%}) "
             f"y {mas_vol} la mayor volatilidad ({res.loc[mas_vol, 'Volatilidad anualizada']:.2%}). "
             + ("El mejor rendimiento y el mejor rendimiento/riesgo coinciden en el mismo activo."
                if mejor_ratio == mejor_cagr else
                f"El activo de mayor rendimiento ({mejor_cagr}) no es el de mejor relación rendimiento/riesgo ({mejor_ratio}): "
                "ganar más no siempre compensa el riesgo asumido."))
    r = rec.loc[peor_dd]
    L.append(f"**Peor caída.** {peor_dd} tuvo el mayor drawdown ({r['Máximo drawdown']:.2%}, con valle el {pd.Timestamp(r['Valle']).date()}). "
             + (f"Recuperó su máximo previo el {pd.Timestamp(r['Recuperación']).date()}, {int(r['Días valle→recuperación'])} días después del valle."
                if pd.notna(r["Recuperación"]) else "Al cierre del período no había recuperado su máximo previo."))
    if len(rend.columns) >= 2:
        reg = regimenes(rend.index)
        if "2022" in reg and "2023–2025" in reg:
            c22, c23 = correlacion_media(rend.loc["2022-01-01":"2022-12-31"]), correlacion_media(rend.loc["2023-01-01":"2025-12-31"])
            tabla = correlacion_por_periodo(rend, reg)
            hi22, lo22 = tabla["2022"].idxmax(), tabla["2022"].idxmin()
            L.append(f"**Correlación entre regímenes.** La correlación media entre los activos fue {c22:.2f} en 2022 y {c23:.2f} en 2023–2025 "
                     f"({'subió' if c23 > c22 else 'bajó'} {abs(c23 - c22):.2f}). En 2022 el par más correlacionado fue {hi22} "
                     f"({tabla.loc[hi22, '2022']:.2f}) y el menos correlacionado {lo22} ({tabla.loc[lo22, '2022']:.2f}). "
                     "Una correlación que cambia con el período advierte que la diversificación observada no es permanente.")
        else:
            L.append("**Correlación entre regímenes.** El rango de fechas elegido no cubre 2022 y 2023–2025 con suficientes sesiones; "
                     "amplíalo (2021–2025) para comparar regímenes.")
    ref, n = refugio(rend)
    if ref is not None and n > 0:
        partes = "; ".join(f"{t}: {v:+.2%}" for t, v in ref.items())
        L.append(f"**¿Refugio?** En los {n} días en que SPY cayó más de 1 %, el rendimiento diario medio fue: {partes}. "
                 "Un valor positivo indica que el activo tendió a compensar la caída del mercado accionario en esos días; uno negativo, que cayó con él.")
    pr = riesgo_pares(rend) if len(rend.columns) >= 2 else None
    if pr is not None:
        p = pr.index[0]
        L.append(f"**Combinación de menor riesgo.** Con pesos 50/50, el par de menor volatilidad fue {p} "
                 f"({pr.loc[p, 'Volatilidad par 50/50']:.2%} anualizada; correlación {pr.loc[p, 'Correlación']:.2f}).")
    L.append("*Resultados históricos del período analizado: no garantizan el comportamiento futuro. Ejercicio académico, no asesoría financiera.*")
    return "\n\n".join(L)
