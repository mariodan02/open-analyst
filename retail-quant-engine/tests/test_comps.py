"""Comps: confronto relativo con provider finti (niente rete) + uno reale.

    python tests/test_comps.py
"""
from __future__ import annotations

from retail_quant.comps import comps, report
from retail_quant.config import Settings
from retail_quant.data import providers
from retail_quant.data.schemas import FinancialHistory, IncomeStatement, PriceSnapshot


def _fake(ticker, mcap, ni, rev, gp, oi):
    price = PriceSnapshot(ticker=ticker, price=100.0, market_cap=mcap)
    fin = FinancialHistory(
        ticker=ticker,
        income=[IncomeStatement(ticker=ticker, fiscal_year=2025, net_income=ni,
                                operating_revenue=rev, gross_profit=gp, operating_income=oi, source="x")],
    )
    return price, fin


# target economico (P/E 10) vs pari cari (P/E 20 e 30)
_DATA = {
    "AAA": _fake("AAA", mcap=100, ni=10, rev=50, gp=30, oi=20),   # P/E 10, P/S 2
    "BBB": _fake("BBB", mcap=200, ni=10, rev=50, gp=25, oi=15),   # P/E 20, P/S 4
    "CCC": _fake("CCC", mcap=300, ni=10, rev=50, gp=20, oi=10),   # P/E 30, P/S 6
}


def test_relative_cheap(monkeypatch):
    monkeypatch.setattr(providers, "get_price", lambda t: _DATA[t][0])
    monkeypatch.setattr(providers, "get_financials", lambda t, s: _DATA[t][1])

    res = comps.compare("AAA", ["BBB", "CCC"], Settings.load(require_llm=False))
    assert res["peer_medians"]["pe"] == 25.0, res["peer_medians"]
    # target P/E 10 vs mediana 25 -> -60%
    assert res["relative"]["pe"]["diff_pct"] == -60.0, res["relative"]
    assert "economico" in res["verdict"].lower(), res["verdict"]
    # il report si costruisce senza errori e contiene il target
    assert "AAA" in report.build_markdown(res)
    print("✓ comps relativo (target economico) ok")


def test_isolates_broken_ticker(monkeypatch):
    def boom_price(t):
        if t == "CCC":
            raise ValueError("no data")
        return _DATA[t][0]
    monkeypatch.setattr(providers, "get_price", boom_price)
    monkeypatch.setattr(providers, "get_financials", lambda t, s: _DATA[t][1])

    res = comps.compare("AAA", ["BBB", "CCC"], Settings.load(require_llm=False))
    rows = {r.ticker: r for r in res["rows"]}
    assert rows["CCC"].error is not None
    assert rows["AAA"].pe == 10.0  # gli altri restano validi
    print("✓ comps isola il ticker rotto ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
