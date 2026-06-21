"""Catalyst calendar + alert earnings imminente (provider finto, niente rete).

    python tests/test_catalyst.py
"""
from __future__ import annotations

from datetime import date, timedelta

from retail_quant.catalyst import catalyst
from retail_quant.config import Settings
from retail_quant.data import providers
from retail_quant.monitor import alerts as alert_rules
from retail_quant.monitor.portfolio import Holding

_TODAY = date(2026, 6, 1)


def test_upcoming_filters_and_sorts(monkeypatch):
    cats = {
        "AAA": {"earnings_date": _TODAY + timedelta(days=5), "ex_dividend_date": None},
        "BBB": {"earnings_date": _TODAY + timedelta(days=200), "ex_dividend_date": _TODAY + timedelta(days=2)},
    }
    monkeypatch.setattr(providers, "get_catalysts", lambda t: cats[t])
    res = catalyst.upcoming([Holding("AAA", 1, 1), Holding("BBB", 1, 1)],
                            Settings.load(require_llm=False), horizon_days=90, today=_TODAY)
    # earnings BBB a 200g è fuori orizzonte; restano ex-div BBB (2g) e earnings AAA (5g), ordinati
    kinds = [(e.ticker, e.kind, e.days_until) for e in res.events]
    assert kinds == [("BBB", "ex_dividend_date", 2), ("AAA", "earnings_date", 5)], kinds
    assert "Stacco dividendo" in catalyst.build_markdown(res, 90)
    print("✓ calendario filtra e ordina ok")


def test_etf_no_events(monkeypatch):
    monkeypatch.setattr(providers, "get_catalysts",
                        lambda t: {"earnings_date": None, "ex_dividend_date": None})
    res = catalyst.upcoming([Holding("VWCE.MI", 1, 1)], Settings.load(require_llm=False), today=_TODAY)
    assert res.events == []
    print("✓ ETF senza eventi ok")


def test_earnings_soon_alert():
    a = alert_rules.evaluate("AAA", 0, prev=None, cur={"price": 100, "days_to_earnings": 7}, lens="value")
    assert any("Earnings tra 7 giorni" in al.message for al in a), [x.message for x in a]
    # fuori finestra: nessun alert earnings
    a = alert_rules.evaluate("AAA", 0, prev=None, cur={"price": 100, "days_to_earnings": 30}, lens="value")
    assert not any("Earnings" in al.message for al in a)
    print("✓ alert earnings imminente ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
