"""Test del DCF

    python tests/test_dcf.py
"""
from __future__ import annotations

from retail_quant.config import Settings
from retail_quant.data import providers
from retail_quant.data.schemas import (
    BalanceSheet,
    CashFlow,
    FinancialHistory,
    PriceSnapshot,
)
from retail_quant.valuation.dcf import intrinsic_value


def test_dcf_basic_positive():
    # azienda con FCF positivo e crescente, poco debito
    p = PriceSnapshot(ticker="X", price=50, shares_outstanding=100e6, market_cap=5e9, beta=1.1)
    fin = FinancialHistory(
        ticker="X",
        cash_flow=[
            CashFlow(ticker="X", fiscal_year=2025, free_cash_flow=300e6, source="t"),
            CashFlow(ticker="X", fiscal_year=2023, free_cash_flow=240e6, source="t"),
            CashFlow(ticker="X", fiscal_year=2021, free_cash_flow=200e6, source="t"),
        ],
        balance=[BalanceSheet(ticker="X", fiscal_year=2025, total_debt=500e6, cash_and_equivalents=300e6, source="t")],
    )
    d = intrinsic_value(p, fin)
    assert d is not None
    assert d["intrinsic_per_share"] > 0
    assert 6.0 <= d["wacc_pct"] <= 15.0, d["wacc_pct"]
    assert "margin_of_safety_pct" in d
    print("  DCF sintetico:", d)
    print("✓ DCF base positivo ok")


def test_dcf_none_when_fcf_negative():
    p = PriceSnapshot(ticker="X", price=50, shares_outstanding=100e6)
    fin = FinancialHistory(ticker="X", cash_flow=[CashFlow(ticker="X", fiscal_year=2025, free_cash_flow=-100e6, source="t")])
    assert intrinsic_value(p, fin) is None
    print("✓ DCF = None con FCF negativo")


def test_dcf_none_without_shares():
    p = PriceSnapshot(ticker="X", price=50)  # niente shares_outstanding
    fin = FinancialHistory(ticker="X", cash_flow=[CashFlow(ticker="X", fiscal_year=2025, free_cash_flow=100e6, source="t")])
    assert intrinsic_value(p, fin) is None
    print("✓ DCF = None senza numero azioni")


def test_dcf_real_aapl():
    settings = Settings.load(require_llm=False)
    price = providers.get_price("AAPL")
    fin = providers.get_financials("AAPL", settings)
    d = intrinsic_value(price, fin)
    print(f"  AAPL prezzo {price.price} | DCF: {d}")
    assert d is not None and d["intrinsic_per_share"] > 0
    print("✓ DCF reale AAPL ok")


if __name__ == "__main__":
    test_dcf_basic_positive()
    test_dcf_none_when_fcf_negative()
    test_dcf_none_without_shares()
    test_dcf_real_aapl()
    print("\n✅ test_dcf: PASSATO")
