"""Earnings deltas + messaggio di alert (deterministico, niente rete).

    python tests/test_earnings.py
"""
from __future__ import annotations

from retail_quant.data.schemas import FinancialHistory, IncomeStatement
from retail_quant.metrics import earnings
from retail_quant.monitor import alerts as alert_rules


def _fin(rows):
    inc = [IncomeStatement(ticker="T", fiscal_year=y, operating_revenue=rev,
                           operating_income=oi, net_income=ni, source="x")
           for y, rev, oi, ni in rows]
    return FinancialHistory(ticker="T", income=inc)


def test_latest_changes():
    # FY2025 vs FY2024: ricavi +10%, utile -20%, margine op da 20% a 13.6%
    fin = _fin([(2025, 110, 15, 8), (2024, 100, 20, 10)])
    c = earnings.latest_changes(fin)
    assert c["revenue_yoy_pct"] == 10.0, c
    assert c["net_income_yoy_pct"] == -20.0, c
    assert c["op_margin_change_pp"] < 0, c  # margine compresso
    print("✓ variazioni YoY ok")


def test_earnings_alert_flags_decline():
    # nuovo FY con utile in calo -> il messaggio deve segnalarlo
    cur = {"price": 100, "fiscal_year": 2025, "revenue_yoy_pct": 10.0,
           "net_income_yoy_pct": -20.0, "op_margin_change_pp": -6.4}
    prev = {"price": 100, "fiscal_year": 2024}
    a = alert_rules.evaluate("AAA", 0, prev=prev, cur=cur, lens="value")
    msg = next(al.message for al in a if "bilancio" in al.message)
    assert "ricavi +10%" in msg and "utile -20%" in msg, msg
    assert "utile in calo" in msg and "margine compresso" in msg, msg
    print("✓ alert earnings con peggioramenti ok")


def test_single_year_no_changes():
    assert earnings.latest_changes(_fin([(2025, 100, 20, 10)])) == {}
    print("✓ un solo anno: nessuna variazione ok")


if __name__ == "__main__":
    test_latest_changes()
    test_earnings_alert_flags_decline()
    test_single_year_no_changes()
    print("\n✅ test_earnings: PASSATO")
