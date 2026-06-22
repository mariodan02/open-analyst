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


def test_justetf_parser_offline():
    # Parsing deterministico (niente rete) su HTML rappresentativo: verifica
    # le ancore data-testid, la conversione del TER e l'azzeramento del
    # rendimento per gli ETF ad accumulazione.
    from retail_quant.data.providers import _enrich_from_justetf
    from retail_quant.data.schemas import EtfProfile

    html = (
        '<div data-testid="etf-profile-header_etf-name">Vanguard FTSE All-World UCITS ETF</div>'
        '<div data-testid="etf-profile-header_ter-value">0.19% p.a.</div>'
        '<div data-testid="etf-profile-header_distribution-policy-value">Accumulating</div>'
        '<td data-testid="tl_etf-basics_value_index-name">FTSE All-World</td>'
    )

    import retail_quant.data.providers as P

    class _Resp:
        text = html
        def raise_for_status(self): pass

    orig = P.requests.get
    P.requests.get = lambda *a, **k: _Resp()
    try:
        prof = EtfProfile(ticker="VWCE.MI", isin="IE00BK5BQT80", dividend_yield=0.0)
        _enrich_from_justetf(prof, "IE00BK5BQT80")
    finally:
        P.requests.get = orig

    assert prof.expense_ratio == 0.0019, prof.expense_ratio
    assert prof.distribution_policy == "Accumulating"
    assert prof.index_name == "FTSE All-World"
    assert prof.dividend_yield is None  # accumulazione -> nessun rendimento mostrato
    print("✓ parser justETF offline ok (TER, policy, indice)")


def test_real_monitor_etf():
    # Un ETF non ha bilancio: lo snapshot deve marcarlo come tale e NON
    # contenere metriche da azione (pe_ratio / margin_of_safety_pct).
    settings = Settings.load(require_llm=False)
    holdings = [Holding("VWCE.MI", shares=6, cost_basis=151.27)]
    results, new_state = monitor(holdings, settings, prev_state={})
    snap = new_state.get("VWCE.MI", {})
    assert results[0].error is None, results[0].error
    assert snap.get("asset_type") == "etf", snap
    assert "margin_of_safety_pct" not in snap
    assert "expense_ratio_pct" in snap  # chiave presente anche se valore None
    # il P/L sulla posizione deve comunque essere calcolato
    assert any("P/L" in a.message for a in results[0].alerts)
    print(f"  ETF snapshot: {snap}")
    print("✓ monitoraggio ETF ok (niente metriche da azione)")


if __name__ == "__main__":
    test_alerts_synthetic()
    test_portfolio_load()
    test_real_monitor_with_change()
    test_justetf_parser_offline()
    test_real_monitor_etf()
    print("\n✅ test_phase3: PASSATO")
