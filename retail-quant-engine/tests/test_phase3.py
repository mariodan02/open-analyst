"""Test Fase 3. Gli alert si testano SENZA rete (istantanee finte) per coprire
tutte le regole; in fondo un monitoraggio reale con rilevamento del cambiamento.

    python tests/test_phase3.py
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from retail_quant.config import Settings
from retail_quant.monitor import alerts as alert_rules
from retail_quant.monitor.monitor import monitor
from retail_quant.monitor.portfolio import Holding, load_portfolio


def _levels(alerts):
    return {a.level for a in alerts}


def test_alerts_synthetic():
    # primo controllo (prev=None): solo P/L informativo, nessun alert di cambiamento
    a = alert_rules.evaluate("AAA", cost_basis=100.0, prev=None, cur={"price": 110.0}, lens="value")
    assert len(a) == 1 and a[0].level == "info"

    # perdita grossa sulla posizione -> warn
    a = alert_rules.evaluate("AAA", cost_basis=100.0, prev=None, cur={"price": 70.0}, lens="value")
    assert any(al.level == "warn" for al in a), "perdita -30% dovrebbe allertare"

    # scostamento prezzo dall'ultimo controllo -> warn
    a = alert_rules.evaluate("AAA", 0, prev={"price": 100.0}, cur={"price": 120.0}, lens="value")
    assert any("Prezzo" in al.message for al in a)

    # nuova trimestrale -> warn
    a = alert_rules.evaluate("AAA", 0, prev={"price": 100, "fiscal_year": 2024}, cur={"price": 100, "fiscal_year": 2025}, lens="value")
    assert any("bilancio" in al.message for al in a)

    # margine di sicurezza sparito -> warn
    a = alert_rules.evaluate("AAA", 0, prev={"price": 100, "margin_of_safety_pct": 20}, cur={"price": 100, "margin_of_safety_pct": -5}, lens="value")
    assert any("Margine di sicurezza" in al.message for al in a)

    # nessun cambiamento -> nessun warn
    a = alert_rules.evaluate("AAA", 0, prev={"price": 100, "fiscal_year": 2025}, cur={"price": 101, "fiscal_year": 2025}, lens="value")
    assert _levels(a).isdisjoint({"warn"})
    print("✓ alert sintetici ok (tutte le regole)")


def test_portfolio_load():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "pf.json"
        p.write_text(json.dumps({"holdings": [{"ticker": "aapl", "shares": 5, "cost_basis": 100}]}))
        hold = load_portfolio(p)
        assert hold[0].ticker == "AAPL" and hold[0].shares == 5
    print("✓ caricamento portafoglio ok")


def test_real_monitor_with_change():
    settings = Settings.load(require_llm=False)
    holdings = [Holding("AAPL", shares=1, cost_basis=150.0)]

    # 1) baseline (nessuno stato precedente)
    results, new_state = monitor(holdings, settings, prev_state={})
    assert results[0].error is None, results[0].error
    assert "AAPL" in new_state
    print(f"  baseline AAPL snapshot: {new_state['AAPL']}")

    # 2) inietto uno stato "vecchio" col prezzo dimezzato -> deve scattare l'alert prezzo
    fake_prev = {"AAPL": {**new_state["AAPL"], "price": new_state["AAPL"]["price"] * 0.5}}
    results2, _ = monitor(holdings, settings, prev_state=fake_prev)
    msgs = [a.message for a in results2[0].alerts]
    assert any("Prezzo" in m for m in msgs), msgs
    print(f"  alert su cambiamento: {msgs}")
    print("✓ monitoraggio reale + rilevamento cambiamento ok")


if __name__ == "__main__":
    test_alerts_synthetic()
    test_portfolio_load()
    test_real_monitor_with_change()
    print("\n✅ test_phase3: PASSATO")
