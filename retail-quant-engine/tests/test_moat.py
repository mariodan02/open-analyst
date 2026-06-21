"""Moat indicators (deterministici, niente rete).

    python tests/test_moat.py
"""
from __future__ import annotations

from retail_quant.data.schemas import BalanceSheet, FinancialHistory, IncomeStatement
from retail_quant.metrics import moat


def _fin(rows) -> FinancialHistory:
    """rows: lista (anno, ricavi, gross, op_income, net_income, equity)."""
    inc, bal = [], []
    for y, rev, gp, oi, ni, eq in rows:
        inc.append(IncomeStatement(ticker="T", fiscal_year=y, operating_revenue=rev,
                                   gross_profit=gp, operating_income=oi, net_income=ni, source="x"))
        bal.append(BalanceSheet(ticker="T", fiscal_year=y, total_equity=eq, source="x"))
    return FinancialHistory(ticker="T", income=inc, balance=bal)


def test_wide_moat():
    # margini lordi alti e stabili, ROE alto, ricavi sempre in crescita
    fin = _fin([
        (2025, 110, 77, 44, 33, 100),
        (2024, 100, 70, 40, 30, 100),
        (2023, 92, 64.4, 36, 27, 100),
    ])
    m = moat.compute(fin)
    assert m["gross_margin_avg_pct"] == 70.0, m
    assert m["roe_avg_pct"] == 30.0, m
    assert m["revenue_growth_consistency_pct"] == 100.0, m
    assert m["gross_margin_volatility_pp"] <= 1.0, m
    assert m["moat_rating"] == "wide", m
    print("✓ wide moat ok")


def test_no_moat():
    # margini bassi, ROE basso, ricavi altalenanti
    fin = _fin([
        (2025, 95, 14, 4, 3, 100),
        (2024, 100, 15, 5, 4, 100),
        (2023, 98, 14, 4, 3, 100),
    ])
    m = moat.compute(fin)
    assert m["moat_rating"] == "none", m
    print("✓ no moat ok")


def test_partial_data_no_crash():
    # solo ricavi: niente margini/ROE, nessun rating, nessun crash
    fin = _fin([(2025, 100, None, None, None, None), (2024, 90, None, None, None, None)])
    m = moat.compute(fin)
    assert "moat_rating" not in m
    assert m["revenue_growth_consistency_pct"] == 100.0
    print("✓ dati parziali gestiti ok")


if __name__ == "__main__":
    test_wide_moat()
    test_no_moat()
    test_partial_data_no_crash()
    print("\n✅ test_moat: PASSATO")
