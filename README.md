# Observatorio multiactivo · Comportamiento histórico de activos financieros

Aplicación interactiva hecha con Python y Streamlit para analizar el comportamiento histórico de varios activos de distinta clase y comunicar los hallazgos con tablas, gráficos y conclusiones generadas con los datos.

**Pregunta de investigación**

> ¿Qué activo ofreció mejor rentabilidad ajustada por riesgo entre 2021 y 2025, y cómo cambió la correlación entre los activos entre el año bajista de 2022 y la recuperación de 2023 a 2025?

## Decisiones del equipo

### 1. ¿Qué activos queremos investigar y por qué?
| Ticker | Clase | Por qué se eligió |
|---|---|---|
| SPY | ETF de acciones (S&P 500) | Referencia del mercado accionario de EE. UU.; muy líquido |
| GLD | ETF de oro (commodity) | Activo refugio tradicional; muy líquido |
| BTC-USD | Criptomoneda | Alta volatilidad; contrasta con los demás |
| TLT | ETF de bonos del Tesoro de EE. UU. a 20 años o más | Renta fija larga, sensible a tasas de interés |

Se eligieron cuatro clases de activos distintas porque con activos del mismo tipo las correlaciones y los riesgos serían muy parecidos y no habría contraste que analizar. Los cuatro tienen historia diaria disponible en Yahoo Finance y buena liquidez. La aplicación permite sumar CVX, JNJ, PG, QQQ, AAPL y MSFT.

**Período: 2021-01-01 a 2025-12-31.** Cinco años cerrados: incluyen un mercado alcista (2021), un año de caídas y alza de tasas de interés (2022, hipótesis que la app contrasta con los datos de SPY) y una recuperación (2023–2025). Un período más corto ocultaría esos regímenes; uno más largo mezclaría contextos muy distintos. Para no mezclar contextos, la app permite ver los resultados por subperíodo (2021, 2022 y 2023–2025). La fecha final fija hace los resultados reproducibles.

### 2. ¿Qué queremos descubrir?
La pregunta de arriba, con estas preguntas de apoyo (cada una se responde en una pestaña):
1. ¿Cuál activo tuvo mayor rendimiento anualizado y cuál mayor volatilidad?
2. ¿Cuál tuvo el peor drawdown y cuánto tardó en recuperar su máximo previo?
3. ¿Los activos considerados refugio (oro y bonos) compensaron las caídas de SPY?
4. ¿Qué combinación de dos activos minimizó el riesgo conjunto con pesos 50/50?

### 3. ¿Qué información y herramientas necesitamos?
- **Datos:** Yahoo Finance mediante `yfinance`, precios de cierre ajustados (`auto_adjust=True`).
- **Herramientas:** `pandas` (series de tiempo, `pct_change`, `rolling`, `corr`), `numpy`, `plotly` y `streamlit`.
- **Indicadores:** rendimiento acumulado y anualizado, volatilidad anualizada, ratio rendimiento/riesgo, máximo drawdown y tiempo de recuperación, correlación (total, por subperíodo y móvil), estadística descriptiva, curtosis, valores atípicos (1,5 × IQR) y riesgo de pares 50/50.
- **Visualizaciones:** base 100 (con escala logarítmica opcional), drawdown, dispersión riesgo-rendimiento, volatilidad móvil, mapas de calor, histograma y boxplot.

## Definiciones de los indicadores
| Indicador | Cálculo |
|---|---|
| Rendimiento diario | `P_t / P_(t−1) − 1` |
| Rendimiento anualizado | `(P_final / P_inicial)^(252/n) − 1`, con n = número de rendimientos |
| Volatilidad anualizada | desviación estándar diaria (ddof = 1) × √252 |
| Rendimiento/riesgo | `(rendimiento anualizado − tasa libre de riesgo) / volatilidad anualizada` (tipo Sharpe) |
| Drawdown | `P_t / máximo previo − 1`; se reporta el máximo y los días de valle a recuperación |
| Correlación | Pearson entre rendimientos diarios |
| Par 50/50 | volatilidad anualizada de la media de los rendimientos de los dos activos (rebalanceo diario) |

## Supuestos y limitaciones
- **Fechas comunes:** BTC-USD cotiza todos los días y los demás solo en días hábiles. Se conservan únicamente las fechas en que cotizan todos los activos y se anualiza con 252 sesiones. Anualizar BTC con 365 días daría otra volatilidad.
- **Tasa libre de riesgo:** 0 % por defecto (ajustable en la barra lateral). Con 0 %, el ratio es rendimiento sobre volatilidad.
- Los resultados son históricos y no garantizan el futuro; no incluyen costos de transacción ni impuestos.
- Si Yahoo Finance no responde, la app avisa en rojo y muestra **datos simulados**, que no son cotizaciones reales.
- Ejercicio académico: no constituye asesoría financiera.

## Estructura
```
app.py                 interfaz de Streamlit
calculos.py            funciones de cálculo (sin Streamlit)
tests_calculos.py      pruebas con series de resultado conocido
requirements.txt
assets/banner_financiero.png
```

## Cómo ejecutarla
```bash
pip install -r requirements.txt
streamlit run app.py
```
Pruebas de los cálculos: `python -m unittest tests_calculos -v`

## Fuentes consultadas
- yfinance, documentación: https://ranaroussi.github.io/yfinance/
- pandas, series de tiempo: https://pandas.pydata.org/docs/user_guide/timeseries.html
- pandas, ventanas móviles: https://pandas.pydata.org/docs/user_guide/window.html
- MIT OpenCourseWare 15.401, Finance Theory I: https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/
