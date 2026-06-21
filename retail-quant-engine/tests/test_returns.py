"""Returns analysis (provider finto, niente rete).

    python tests/test_returns.py
"""
from __future__ import annotations

from retail_quant.config import Settings
from retail_quant.data import providers
from retail_quant.data.schemas import PriceSnapshot
from retail_quant.monitor.portfolio import Holding
from retail_quant.returns import returns

_PRICES = {
    "AAA": PriceSnapshot(ticker="AAA", price=200.0, currency="EUR"),  # carico 100 -> +100%
    "BBB": PriceSnapshot(ticker="BBB", price=50.0, currency="EUR"),   # carico 100 -> -50%
}


def test_totals_and_weights(monkeypatch):
    monkeypatch.setattr(providers, "get_price", lambda t: _PRICES[t])
    holdings = [Holding("AAA", shares=1, cost_basis=100), Holding("BBB", shares=1, cost_basis=100)]

    r = returns.analyze(holdings, Settings.load(require_llm=False))  # base EUR, titoli EUR
    # carico 200, mercato 250 -> +25%
    assert r["total_cost"] == 200.0 and r["total_market"] == 250.0
    assert r["total_pl_pct"] == 25.0, r
    assert r["base_currency"] == "EUR"
    rows = {x.ticker: x for x in r["rows"]}
    assert rows["AAA"].pl_pct == 100.0 and rows["BBB"].pl_pct == -50.0
    # pesi sul valore di mercato: AAA 200/250=80%, BBB 20%
    assert rows["AAA"].weight_pct == 80.0 and rows["BBB"].weight_pct == 20.0
    assert "Performance" in returns.build_markdown(r)
    print("✓ totali, P/L e pesi ok")


def test_fx_conversion(monkeypatch):
    # titolo in USD convertito in EUR a 0.9: carico 100$ -> 90€, mercato 200$ -> 180€
    prices = {"USD1": PriceSnapshot(ticker="USD1", price=200.0, currency="USD")}
    monkeypatch.setattr(providers, "get_price", lambda t: prices[t])
    monkeypatch.setattr(providers, "get_fx_rate", lambda f, b: 0.9 if (f, b) == ("USD", "EUR") else 1.0)
    r = returns.analyze([Holding("USD1", 1, 100)], Settings.load(require_llm=False))
    row = r["rows"][0]
    assert row.cost_value == 90.0 and row.market_value == 180.0, row
    assert r["base_currency"] == "EUR" and not r["warnings"]
    print("✓ conversione FX ok")


def test_fx_unavailable_warns(monkeypatch):
    prices = {"USD1": PriceSnapshot(ticker="USD1", price=200.0, currency="USD")}
    monkeypatch.setattr(providers, "get_price", lambda t: prices[t])
    def boom(f, b):
        raise ValueError("no rate")
    monkeypatch.setattr(providers, "get_fx_rate", boom)
    r = returns.analyze([Holding("USD1", 1, 100)], Settings.load(require_llm=False))
    assert r["rows"][0].market_value == 200.0  # valore nominale
    assert any("USD->EUR" in w for w in r["warnings"]), r["warnings"]
    print("✓ FX non disponibile: avviso + nominale ok")


def test_isolates_broken(monkeypatch):
    def boom(t):
        if t == "BBB":
            raise ValueError("no price")
        return _PRICES[t]
    monkeypatch.setattr(providers, "get_price", boom)
    r = returns.analyze([Holding("AAA", 1, 100), Holding("BBB", 1, 100)], Settings.load(require_llm=False))
    rows = {x.ticker: x for x in r["rows"]}
    assert rows["BBB"].error is not None and rows["AAA"].pl_pct == 100.0
    assert r["total_cost"] == 100.0  # solo il titolo valido
    print("✓ isola il titolo rotto ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
