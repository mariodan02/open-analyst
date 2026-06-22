"""Dashboard HTML (render con provider finti, niente rete).

    python tests/test_dashboard.py
"""
from __future__ import annotations

from retail_quant.config import Settings
from retail_quant.dashboard import build
from retail_quant.data import providers
from retail_quant.data.schemas import PriceSnapshot
from retail_quant.monitor.alerts import Alert
from retail_quant.monitor.monitor import MonitorResult
from retail_quant.monitor.portfolio import Holding


def test_render_contains_key_sections(monkeypatch):
    monkeypatch.setattr(providers, "get_price",
                        lambda t: PriceSnapshot(ticker=t, price=200.0, currency="EUR"))
    monkeypatch.setattr(providers, "get_fx_rate", lambda f, b: 1.0)
    monkeypatch.setattr(providers, "get_catalysts",
                        lambda t: {"earnings_date": None, "ex_dividend_date": None})

    holdings = [Holding("AAA", shares=1, cost_basis=100)]  # +100%
    results = [MonitorResult("AAA", alerts=[Alert("AAA", "warn", "P/L -25%"),
                                            Alert("AAA", "info", "ignorami")])]

    htmltext = build.render(holdings, Settings.load(require_llm=False), monitor_results=results)
    assert "<!doctype html>" in htmltext.lower()
    assert "AAA" in htmltext
    assert "Da guardare" in htmltext and "P/L -25%" in htmltext   # alert warn presente
    assert "ignorami" not in htmltext                              # l'info è esclusa
    assert "+100.00%" in htmltext                                  # P/L colorato
    assert "Prossimi eventi" in htmltext
    print("✓ render dashboard ok (KPI, alert, no info, eventi)")


def test_html_escaping(monkeypatch):
    monkeypatch.setattr(providers, "get_price",
                        lambda t: PriceSnapshot(ticker=t, price=100.0, currency="EUR"))
    monkeypatch.setattr(providers, "get_fx_rate", lambda f, b: 1.0)
    monkeypatch.setattr(providers, "get_catalysts",
                        lambda t: {"earnings_date": None, "ex_dividend_date": None})
    results = [MonitorResult("AAA", alerts=[Alert("AAA", "warn", "rischio <script>")])]
    out = build.render([Holding("AAA", 1, 100)], Settings.load(require_llm=False), monitor_results=results)
    assert "<script>" not in out and "&lt;script&gt;" in out
    print("✓ escaping HTML ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
