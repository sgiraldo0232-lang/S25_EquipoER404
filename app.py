"""Observatorio multiactivo · ¿Qué activo ofreció mejor rentabilidad ajustada por riesgo, 2021-2025?"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

import calculos as c

UNIVERSO = ["SPY", "GLD", "BTC-USD", "TLT", "CVX", "JNJ", "PG", "QQQ", "AAPL", "MSFT"]
BASE = ["SPY", "GLD", "BTC-USD", "TLT"]
NOMBRES = {"SPY": "ETF S&P 500", "GLD": "ETF oro", "BTC-USD": "Bitcoin", "TLT": "ETF bonos EE. UU. 20+ años",
           "CVX": "Chevron", "JNJ": "Johnson & Johnson", "PG": "Procter & Gamble", "QQQ": "ETF Nasdaq 100",
           "AAPL": "Apple", "MSFT": "Microsoft"}

st.set_page_config(page_title="Observatorio multiactivo", page_icon="📊", layout="wide")
st.markdown("""<style>
[data-testid="stMetric"]{padding:14px;border-radius:14px;border:1px solid rgba(128,128,128,.35)}
h1,h2,h3{letter-spacing:-.03em}
</style>""", unsafe_allow_html=True)
banner = Path(__file__).parent / "assets" / "banner_financiero.png"
if banner.exists():
    st.image(str(banner), width="stretch")
st.title("Observatorio multiactivo")
st.caption("¿Qué activo ofreció mejor rentabilidad ajustada por riesgo entre 2021 y 2025, y cómo cambió la correlación entre regímenes de mercado?")

# ---------------------------------------------------------------- controles
st.sidebar.header("⚙️ Configura tu análisis")
tickers = st.sidebar.multiselect("Activos", UNIVERSO, default=BASE, max_selections=8,
                                 format_func=lambda t: f"{t} · {NOMBRES[t]}")
desde = st.sidebar.date_input("Desde", value=date(2021, 1, 1), min_value=date(2010, 1, 1), max_value=date.today())
hasta = st.sidebar.date_input("Hasta", value=date(2025, 12, 31), min_value=date(2010, 1, 1), max_value=date.today())
rf = st.sidebar.number_input("Tasa libre de riesgo anual (%)", min_value=0.0, max_value=15.0, value=0.0, step=0.25) / 100
ventana = st.sidebar.slider("Ventana de correlación/volatilidad móvil (sesiones)", 20, 120, 60, step=10)
fuente = st.sidebar.radio("Fuente de datos", ["Yahoo Finance", "Simulados (práctica)"], index=0)
if (desde, hasta) != (date(2021, 1, 1), date(2025, 12, 31)):
    st.sidebar.info("Estás fuera del período definido en el README (2021-01-01 a 2025-12-31).")


@st.cache_data(ttl=3600, show_spinner=False)
def descargar(simbolos, ini, fin):
    # yfinance trata `end` como exclusivo: se suma un día para incluir la fecha final.
    d = yf.download(list(simbolos), start=ini, end=(pd.Timestamp(fin) + timedelta(days=1)).strftime("%Y-%m-%d"),
                    auto_adjust=True, progress=False, threads=False)
    if d is None or d.empty:
        raise ValueError("Yahoo Finance no devolvió datos")
    cierre = d["Close"] if isinstance(d.columns, pd.MultiIndex) else d[["Close"]].rename(columns={"Close": simbolos[0]})
    if isinstance(cierre, pd.Series):
        cierre = cierre.to_frame(simbolos[0])
    faltan = [t for t in simbolos if t not in cierre.columns or cierre[t].dropna().empty]
    if faltan:
        raise ValueError("Sin datos para: " + ", ".join(faltan))
    # yfinance nombra el índice ("Date") y las columnas ("Ticker"); se limpian para que los gráficos no dependan de esos nombres.
    return cierre.reindex(columns=list(simbolos)).rename_axis(index=None, columns=None)


if not tickers:
    st.info("Selecciona al menos un activo en la barra lateral.")
    st.stop()
if desde >= hasta:
    st.error("La fecha inicial debe ser anterior a la final.")
    st.stop()

simulados = fuente == "Simulados (práctica)"
bruto = None
if not simulados:
    try:
        with st.spinner("Consultando Yahoo Finance..."):
            bruto = descargar(tuple(tickers), str(desde), str(hasta))
    except Exception as error:
        st.warning("Yahoo Finance no está disponible. Se muestran DATOS SIMULADOS para continuar la práctica.")
        st.caption(f"Detalle técnico: {error}")
        simulados = True
if simulados:
    bruto = c.simular_precios(tickers, desde, hasta)

precios = c.alinear_fechas(bruto)
if len(precios) < 60:
    st.error("Hay menos de 60 sesiones comunes para los activos y fechas elegidos. Amplía el período.")
    st.stop()
if simulados:
    st.error("MODO DEMOSTRACIÓN: los resultados NO corresponden a cotizaciones reales.")
else:
    st.success(f"Datos de Yahoo Finance · {precios.index[0].date()} a {precios.index[-1].date()} · "
               f"{len(precios)} sesiones comunes (de {len(bruto)} fechas descargadas)")
if "BTC-USD" in tickers:
    st.caption("BTC-USD cotiza todos los días; se conservan solo las fechas en que cotizan todos los activos y se anualiza con 252 sesiones.")

rend = c.rendimientos(precios)
res = c.resumen(precios, rf)
base100 = precios.div(precios.iloc[0]) * 100
dd = c.drawdown(precios)

m = st.columns(4)
m[0].metric("Mejor rendimiento/riesgo", res["Rendimiento/riesgo"].idxmax(), f"{res['Rendimiento/riesgo'].max():.2f}", delta_color="off")
m[1].metric("Mayor rendimiento anualizado", res["Rendimiento anualizado"].idxmax(), f"{res['Rendimiento anualizado'].max():+.2%}", delta_color="off")
m[2].metric("Mayor volatilidad", res["Volatilidad anualizada"].idxmax(), f"{res['Volatilidad anualizada'].max():.2%}", delta_color="off")
m[3].metric("Peor drawdown", res["Máximo drawdown"].idxmin(), f"{res['Máximo drawdown'].min():.2%}", delta_color="off")

t1, t2, t3, t4, t5, t6, t7 = st.tabs(["🎯 Respuesta", "📈 Comparación", "⚖️ Riesgo y rendimiento", "🔗 Correlación",
                                      "📊 Estadística", "🧩 Pares 50/50", "ℹ️ Proyecto"])

with t1:
    st.subheader("Respuesta a la pregunta de investigación")
    st.markdown(c.conclusiones(precios, rf))
    st.subheader("Resumen por activo")
    st.dataframe(res.style.format({"Rendimiento acumulado": "{:+.2%}", "Rendimiento anualizado": "{:+.2%}",
                                   "Volatilidad anualizada": "{:.2%}", "Rendimiento/riesgo": "{:.2f}",
                                   "Máximo drawdown": "{:.2%}"}), width="stretch")

with t2:
    st.subheader("Precios normalizados · base 100")
    log = st.checkbox("Escala logarítmica (útil cuando un activo crece mucho más que los demás)")
    fig = px.line(base100, labels={"value": "Índice (inicio = 100)", "index": "Fecha", "variable": "Activo"})
    if log:
        fig.update_yaxes(type="log")
    st.plotly_chart(fig, width="stretch")
    st.subheader("Drawdown: caída desde el máximo previo")
    st.plotly_chart(px.line(dd * 100, labels={"value": "Drawdown (%)", "index": "Fecha", "variable": "Activo"}), width="stretch")
    st.subheader("Recuperación del máximo drawdown")
    rec = c.recuperacion(precios)
    mostrar = rec.copy()
    mostrar["Máximo drawdown"] = mostrar["Máximo drawdown"].map("{:.2%}".format)
    for col in ["Pico", "Valle", "Recuperación"]:
        mostrar[col] = pd.to_datetime(mostrar[col]).dt.date.astype(str).replace("NaT", "No recuperado")
    mostrar["Días valle→recuperación"] = mostrar["Días valle→recuperación"].map(lambda x: "—" if pd.isna(x) else f"{int(x)}")
    st.dataframe(mostrar, width="stretch")

with t3:
    st.subheader("Riesgo contra rendimiento")
    dfp = res.rename_axis("Activo").reset_index()
    fig = px.scatter(dfp, x="Volatilidad anualizada", y="Rendimiento anualizado", text="Activo", color="Activo")
    fig.update_traces(marker_size=14, textposition="top center")
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
    st.info("Arriba y a la izquierda es mejor: más rendimiento con menos volatilidad. "
            f"El ratio rendimiento/riesgo = (rendimiento anualizado − {rf:.1%}) / volatilidad anualizada.")
    st.subheader(f"Volatilidad móvil ({ventana} sesiones, anualizada)")
    volmovil = rend.rolling(ventana).std() * np.sqrt(c.DIAS_ANIO) * 100
    st.plotly_chart(px.line(volmovil.dropna(), labels={"value": "Volatilidad (%)", "index": "Fecha", "variable": "Activo"}),
                    width="stretch")

with t4:
    if len(tickers) < 2:
        st.info("Selecciona al menos dos activos para ver correlaciones.")
    else:
        regs = c.regimenes(rend.index)
        opciones = ["Período completo"] + list(regs)
        elegido = st.selectbox("Subperíodo", opciones)
        sub = rend if elegido == "Período completo" else rend.loc[regs[elegido][0]:regs[elegido][1]]
        izq, der = st.columns(2)
        with izq:
            fig = px.imshow(sub.corr(), text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale="RdBu_r",
                            title=f"Correlación de rendimientos diarios · {elegido} ({len(sub)} sesiones)")
            st.plotly_chart(fig, width="stretch")
        with der:
            st.markdown("**Correlación por subperíodo**")
            tabla = c.correlacion_por_periodo(rend, regs)
            st.dataframe(tabla.style.format("{:.2f}"), width="stretch")
        par = st.selectbox("Par para la correlación móvil", [f"{a}–{b}" for a, b in c.pares(rend.columns)])
        a, b = par.split("–")
        mov = rend[a].rolling(ventana).corr(rend[b]).dropna()
        fig = px.line(mov.rename("Correlación móvil"), labels={"value": "Correlación", "index": "Fecha"},
                      title=f"Correlación móvil {par} ({ventana} sesiones)")
        fig.add_hline(y=0, line_dash="dash")
        fig.update_yaxes(range=[-1, 1])
        st.plotly_chart(fig, width="stretch")
        st.info("Una correlación alta no implica causalidad, y su valor cambia con el período: "
                "por eso se muestra por subperíodo y en ventana móvil.")
        ref, n = c.refugio(rend)
        if ref is not None:
            st.markdown(f"**¿Refugio?** Rendimiento diario medio de cada activo en los {n} días en que SPY cayó más de 1 %:")
            st.dataframe(ref.rename("Rendimiento medio").to_frame().style.format("{:+.2%}"), width="stretch")

with t5:
    st.subheader("Estadística descriptiva de rendimientos diarios (%)")
    desc = pd.DataFrame({"Media": rend.mean() * 100, "Mediana": rend.median() * 100, "Desv. estándar": rend.std() * 100,
                         "Mínimo": rend.min() * 100, "Máximo": rend.max() * 100, "Curtosis en exceso": rend.kurt()})
    st.dataframe(desc.round(3), width="stretch")
    x1, x2 = st.columns(2)
    with x1:
        act = st.selectbox("Activo para el histograma", list(rend.columns))
        st.plotly_chart(px.histogram(x=rend[act] * 100, nbins=50, title=f"Distribución de rendimientos diarios · {act}",
                                     labels={"x": "Rendimiento (%)"}), width="stretch")
    with x2:
        largo = (rend * 100).melt(var_name="Activo", value_name="Rendimiento (%)")
        st.plotly_chart(px.box(largo, x="Activo", y="Rendimiento (%)", title="Boxplot comparativo"), width="stretch")
    st.subheader("Valores atípicos (regla 1,5 × IQR)")
    at = c.atipicos(rend)
    at["Rendimiento ese día"] = at["Rendimiento ese día"].map("{:+.2%}".format)
    st.dataframe(at, width="stretch")
    st.info("Un atípico es un día de reacción inusual; las colas pesadas (curtosis alta) indican que los eventos extremos "
            "ocurren más de lo que sugeriría una distribución normal.")

with t6:
    if len(tickers) < 2:
        st.info("Selecciona al menos dos activos.")
    else:
        st.subheader("Volatilidad de cada par con pesos 50/50 (rebalanceo diario)")
        pr = c.riesgo_pares(rend)
        st.dataframe(pr.style.format({"Correlación": "{:.2f}", "Volatilidad par 50/50": "{:.2%}"}), width="stretch")
        st.info("El riesgo conjunto depende de la correlación y de la volatilidad de cada activo: "
                "el par menos correlacionado no siempre es el de menor riesgo.")

with t7:
    st.subheader("Decisiones del proyecto")
    st.markdown(f"""
- **Pregunta:** ¿qué activo ofreció mejor rentabilidad ajustada por riesgo entre 2021 y 2025, y cómo cambió la correlación entre regímenes de mercado?
- **Activos base:** SPY (acciones), GLD (oro), BTC-USD (cripto) y TLT (bonos largos de EE. UU.).
- **Período:** 2021-01-01 a 2025-12-31, con subperíodos 2021, 2022 y 2023–2025.
- **Datos:** Yahoo Finance con `yfinance`, precios de cierre ajustados; solo fechas comunes a todos los activos.
- **Fórmulas:** r_t = P_t/P_(t−1) − 1; rendimiento anualizado = (P_final/P_inicial)^(252/n) − 1; volatilidad = σ_diaria·√252;
  ratio = (rendimiento anualizado − tasa libre de riesgo)/volatilidad; drawdown = P_t/máximo previo − 1.
- **Limitaciones:** resultados históricos; sin costos ni impuestos; tasa libre de riesgo fijada por el usuario (0 % por defecto);
  la convención de 252 sesiones con fechas comunes cambia la volatilidad de BTC-USD frente a una anualización de 365 días.
""")
    with st.expander("🔎 Ver datos y descargar CSV"):
        st.dataframe(precios.tail(30), width="stretch")
        st.download_button("Descargar precios CSV", precios.to_csv().encode("utf-8"), "precios_multiactivo.csv", "text/csv")
st.caption("Uso académico. Los resultados históricos no garantizan rentabilidades futuras.")
