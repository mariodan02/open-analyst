"""Regressioni per i bug trovati nella caccia (Fase 3 + review).

    python tests/test_bugfixes.py
"""
from __future__ import annotations

from retail_quant.data.schemas import (
    CashFlow,
    FinancialHistory,
    IncomeStatement,
    PriceSnapshot,
)
from retail_quant.metrics import dividends, growth, value


def test_value_no_fake_margin_with_negative_fcf():
    """FCF negativo NON deve produrre fair value / margine di sicurezza."""
    p = PriceSnapshot(ticker="X", price=10, market_cap=500e6)
    fin = FinancialHistory(
        ticker="X",
        cash_flow=[CashFlow(ticker="X", fiscal_year=2025, free_cash_flow=-100e6, source="t")],
    )
    m = value.compute(p, fin)
    assert "margin_of_safety_pct" not in m
    assert "rough_fair_value" not in m
    print("✓ value: nessun margine di sicurezza falso con FCF negativo")


def test_growth_cagr_no_crash_on_sign_change():
    """Utile da positivo a negativo: niente crash (era TypeError complex), None."""
    p = PriceSnapshot(ticker="X", price=10)
    inc = [
        IncomeStatement(ticker="X", fiscal_year=2025, operating_revenue=300, net_income=-50, source="t"),
        IncomeStatement(ticker="X", fiscal_year=2023, operating_revenue=200, net_income=20, source="t"),
        IncomeStatement(ticker="X", fiscal_year=2022, operating_revenue=100, net_income=100, source="t"),
    ]
    m = growth.compute(p, FinancialHistory(ticker="X", income=inc))  # non deve sollevare
    assert m["net_income_cagr_pct"] is None
    assert m["revenue_cagr_pct"] is not None  # i ricavi (sempre positivi) sì
    print("✓ growth: CAGR utile = None su cambio di segno, niente crash")


def test_dividends_no_payout_with_negative_income():
    """Payout non calcolato se l'utile è negativo (sarebbe ingannevolmente basso)."""
    p = PriceSnapshot(ticker="X", price=10, market_cap=1e9)
    fin = FinancialHistory(
        ticker="X",
        income=[IncomeStatement(ticker="X", fiscal_year=2025, net_income=-200e6, source="t")],
        cash_flow=[CashFlow(ticker="X", fiscal_year=2025, free_cash_flow=50e6, dividends_paid=-30e6, source="t")],
    )
    m = dividends.compute(p, fin)
    assert "payout_ratio_pct" not in m
    print("✓ dividends: nessun payout fuorviante con utile negativo")


def test_value_no_de_with_negative_equity():
    """Patrimonio netto negativo NON deve dare un debt/equity ingannevole."""
    from retail_quant.data.schemas import BalanceSheet

    p = PriceSnapshot(ticker="X", price=10, market_cap=1e9)
    fin = FinancialHistory(
        ticker="X",
        balance=[BalanceSheet(ticker="X", fiscal_year=2025, total_debt=800e6, total_equity=-200e6, source="t")],
    )
    m = value.compute(p, fin)
    assert "debt_to_equity" not in m
    print("✓ value: nessun debt/equity fuorviante con equity negativo")


if __name__ == "__main__":
    test_value_no_fake_margin_with_negative_fcf()
    test_growth_cagr_no_crash_on_sign_change()
    test_dividends_no_payout_with_negative_income()
    test_value_no_de_with_negative_equity()
    print("\n✅ test_bugfixes: PASSATO")
