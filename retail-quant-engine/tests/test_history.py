"""Storico patrimonio: record/dedup/load (niente rete).

    python tests/test_history.py
"""
from __future__ import annotations

from datetime import date

from retail_quant.history import history


def _rdata(market):
    return {"total_cost": 100.0, "total_market": market, "total_pl_pct": market - 100, "base_currency": "EUR"}


def test_record_dedup_and_order(tmp_path):
    p = tmp_path / "h.csv"
    history.record(_rdata(110), on=date(2026, 1, 2), path=p)
    history.record(_rdata(105), on=date(2026, 1, 1), path=p)
    history.record(_rdata(120), on=date(2026, 1, 2), path=p)  # stessa data -> aggiorna

    rows = history.load(p)
    assert [r["date"] for r in rows] == ["2026-01-01", "2026-01-02"], rows  # ordinato
    assert rows[1]["total_market"] == 120.0  # il secondo punto del 02 ha sovrascritto
    assert rows[0]["total_pl_pct"] == 5.0
    print("✓ record dedup + ordine ok")


def test_load_missing_file(tmp_path):
    assert history.load(tmp_path / "assente.csv") == []
    print("✓ file assente -> lista vuota ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
