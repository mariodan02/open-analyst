"""Rebalance (provider finto, niente rete).

    python tests/test_rebalance.py
"""
from __future__ import annotations

from retail_quant.config import Settings
from retail_quant.data import providers
from retail_quant.data.schemas import PriceSnapshot
from retail_quant.monitor.portfolio import Holding
from retail_quant.rebalance import rebalance

# AAA vale 150 (1 quota), BBB vale 50 (1 quota): totale 200, pesi 75/25
_PRICES = {
    "AAA": PriceSnapshot(ticker="AAA", price=150.0, currency="EUR"),
    "BBB": PriceSnapshot(ticker="BBB", price=50.0, currency="EUR"),
}


def _holds():
    return [Holding("AAA", 1, 100, target_pct=50), Holding("BBB", 1, 100, target_pct=50)]


def test_full_rebalance(monkeypatch):
    monkeypatch.setattr(providers, "get_price", lambda t: _PRICES[t])
    r = rebalance.rebalance(_holds(), Settings.load(require_llm=False))
    rows = {x.ticker: x for x in r["rows"]}
    # obiettivo 50/50 su 200 -> 100 ciascuno. AAA da 150 -> vendi 50, BBB compra 50
    assert rows["AAA"].trade_value == -50.0 and rows["AAA"].action == "Vendi", rows["AAA"]
    assert rows["BBB"].trade_value == 50.0 and rows["BBB"].action == "Compra", rows["BBB"]
    assert rows["AAA"].current_pct == 75.0
    print("✓ ribilanciamento pieno ok")


def test_cash_only_buys(monkeypatch):
    monkeypatch.setattr(providers, "get_price", lambda t: _PRICES[t])
    # verso 100 di nuova liquidità: nessuna vendita, solo acquisti sul sottopeso
    r = rebalance.rebalance(_holds(), Settings.load(require_llm=False), new_cash=100.0)
    rows = {x.ticker: x for x in r["rows"]}
    assert all(rows[t].trade_value >= 0 for t in rows), "con cash non si vende"
    # base 300, target BBB 150, attuale 50 -> shortfall 100; AAA target 150 attuale 150 -> 0
    assert rows["BBB"].trade_value == 100.0 and rows["AAA"].trade_value == 0.0, rows
    assert abs(sum(x.trade_value for x in rows.values()) - 100.0) < 0.01
    print("✓ versamento: solo acquisti sul sottopeso ok")


def test_missing_target_warns(monkeypatch):
    monkeypatch.setattr(providers, "get_price", lambda t: _PRICES[t])
    holds = [Holding("AAA", 1, 100, target_pct=100), Holding("BBB", 1, 100)]  # BBB senza target
    r = rebalance.rebalance(holds, Settings.load(require_llm=False))
    assert any("target_pct" in w for w in r["warnings"]), r["warnings"]
    print("✓ avviso target mancante ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
