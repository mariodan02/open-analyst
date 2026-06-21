"""Orchestrazione del monitoraggio: per ogni titolo posseduto prende i dati,
costruisce l'istantanea attuale, la confronta con quella salvata e raccoglie
gli alert. Aggiorna lo stato per il prossimo giro.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..data import providers
from ..metrics import compute as compute_metrics
from . import alerts as alert_rules
from .portfolio import Holding


@dataclass
class MonitorResult:
    ticker: str
    snapshot: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)
    error: str | None = None


def _snapshot(ticker: str, settings: Settings, lens: str) -> dict:
    """Istantanea minima da persistere e confrontare."""
    price = providers.get_price(ticker)
    fin = providers.get_financials(ticker, settings)
    metrics = compute_metrics(lens, price, fin)
    latest_fy = fin.income[0].fiscal_year if fin.income else None
    return {
        "price": price.price,
        "fiscal_year": latest_fy,
        "pe_ratio": metrics.get("pe_ratio"),
        "margin_of_safety_pct": metrics.get("margin_of_safety_pct"),
    }


def monitor(holdings: list[Holding], settings: Settings, prev_state: dict) -> tuple[list[MonitorResult], dict]:
    results: list[MonitorResult] = []
    new_state: dict = {}
    for h in holdings:
        try:
            cur = _snapshot(h.ticker, settings, settings.lens)
        except Exception as exc:  # noqa: BLE001 - isola il titolo problematico
            results.append(MonitorResult(h.ticker, error=f"{type(exc).__name__}: {exc}"))
            # mantieni lo stato precedente se il fetch fallisce
            if h.ticker in prev_state:
                new_state[h.ticker] = prev_state[h.ticker]
            continue

        a = alert_rules.evaluate(h.ticker, h.cost_basis, prev_state.get(h.ticker), cur, settings.lens)
        results.append(MonitorResult(h.ticker, snapshot=cur, alerts=a))
        new_state[h.ticker] = cur
    return results, new_state
