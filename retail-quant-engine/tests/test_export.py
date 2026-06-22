"""Export CSV (provider finto, niente rete).

    python tests/test_export.py
"""
from __future__ import annotations

import csv

from retail_quant.config import Settings
from retail_quant.data import providers
from retail_quant.data.schemas import PriceSnapshot
from retail_quant.export import csv_export
from retail_quant.monitor.portfolio import Holding


def test_csv_rows_and_total(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, "get_price",
                        lambda t: PriceSnapshot(ticker=t, price=200.0, currency="EUR"))
    monkeypatch.setattr(providers, "get_fx_rate", lambda f, b: 1.0)

    out = tmp_path / "pf.csv"
    csv_export.write_csv([Holding("AAA", shares=2.0, cost_basis=100)],
                         Settings.load(require_llm=False), out)

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    aaa = rows[0]
    assert aaa["ticker"] == "AAA" and aaa["shares"] == "2.0"
    assert aaa["market_value"] == "400.0" and aaa["pl_pct"] == "100.0"
    assert aaa["base_currency"] == "EUR"
    total = rows[-1]
    assert total["ticker"] == "TOTALE" and total["market_value"] == "400.0"
    print("✓ export CSV righe + totale ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
