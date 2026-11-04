"""Pruebas de las funciones de cálculo con series cuyo resultado se conoce de antemano.
Ejecutar:  python -m unittest tests_calculos -v
"""
import unittest

import numpy as np
import pandas as pd

import calculos as c


def serie(valores, inicio="2021-01-04"):
    idx = pd.bdate_range(inicio, periods=len(valores))
    return pd.DataFrame({"A": valores}, index=idx)


class Pruebas(unittest.TestCase):
    def test_cagr_crecimiento_constante(self):
        # 1 % diario durante 252 rendimientos -> 1,01^252 - 1
        p = serie(100 * 1.01 ** np.arange(253))
        self.assertAlmostEqual(c.cagr(p)["A"], 1.01 ** 252 - 1, places=9)

    def test_volatilidad_anualizada(self):
        p = serie([100, 101, 100, 101, 100, 101])
        r = c.rendimientos(p)
        self.assertAlmostEqual(c.vol_anual(r)["A"], r["A"].std(ddof=1) * np.sqrt(252), places=12)

    def test_drawdown_y_recuperacion(self):
        p = serie([100, 120, 90, 100, 120, 130])
        dd = c.drawdown(p)["A"]
        self.assertAlmostEqual(dd.min(), 90 / 120 - 1)
        rec = c.recuperacion(p).loc["A"]
        self.assertEqual(rec["Valle"], p.index[2])
        self.assertEqual(rec["Recuperación"], p.index[4])
        self.assertEqual(rec["Días valle→recuperación"], (p.index[4] - p.index[2]).days)

    def test_no_recuperado(self):
        p = serie([100, 120, 90, 100])
        self.assertTrue(pd.isna(c.recuperacion(p).loc["A", "Recuperación"]))

    def test_correlacion_identica_y_opuesta(self):
        rng = np.random.default_rng(1)
        r = pd.Series(rng.normal(0, .01, 200))
        df = pd.DataFrame({"X": r, "Y": r, "Z": -r})
        corr = df.corr()
        self.assertAlmostEqual(corr.loc["X", "Y"], 1.0)
        self.assertAlmostEqual(corr.loc["X", "Z"], -1.0)

    def test_riesgo_par_formula_de_dos_activos(self):
        rng = np.random.default_rng(2)
        df = pd.DataFrame(rng.normal(0, .01, (300, 2)), columns=["X", "Y"])
        sx, sy, rho = df["X"].std(ddof=1), df["Y"].std(ddof=1), df["X"].corr(df["Y"])
        teorica = np.sqrt(.25 * sx ** 2 + .25 * sy ** 2 + .5 * rho * sx * sy) * np.sqrt(252)
        self.assertAlmostEqual(c.riesgo_pares(df).loc["X–Y", "Volatilidad par 50/50"], teorica, places=10)

    def test_alinear_fechas_descarta_fines_de_semana_de_btc(self):
        dias = pd.date_range("2022-01-03", periods=14, freq="D")
        df = pd.DataFrame({"SPY": np.nan, "BTC-USD": 1.0}, index=dias)
        df.loc[dias.dayofweek < 5, "SPY"] = 2.0
        self.assertEqual(len(c.alinear_fechas(df)), 10)

    def test_refugio(self):
        r = pd.DataFrame({"SPY": [-0.02, 0.01, -0.03], "GLD": [0.01, 0.0, 0.03]})
        ref, n = c.refugio(r)
        self.assertEqual(n, 2)
        self.assertAlmostEqual(ref["GLD"], 0.02)

    def test_atipicos_regla_iqr(self):
        r = pd.DataFrame({"A": list(np.linspace(-0.01, 0.01, 99)) + [0.2]}, index=pd.bdate_range("2021-01-04", periods=100))
        self.assertEqual(c.atipicos(r).loc["A", "Atípicos (n)"], 1)

    def test_regimenes_requieren_sesiones_suficientes(self):
        idx = pd.bdate_range("2024-01-01", "2025-12-31")
        self.assertEqual(c.regimenes(idx), {"2023–2025": ("2023-01-01", "2025-12-31")})

    def test_conclusiones_no_falla_y_cita_cifras(self):
        p = c.simular_precios(["SPY", "GLD", "BTC-USD", "TLT"], "2021-01-01", "2025-12-31")
        txt = c.conclusiones(p, 0.0)
        self.assertIn("Rendimiento ajustado por riesgo", txt)
        self.assertIn("Correlación entre regímenes", txt)


if __name__ == "__main__":
    unittest.main()
