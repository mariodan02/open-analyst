"""Orchestrazione del monitoraggio: per ogni titolo posseduto prende i dati,
costruisce l'istantanea attuale, la confronta con quella salvata e raccoglie
gli alert. Aggiorna lo stato per il prossimo giro.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..data import providers
from ..data.schemas import ETF_LIKE
from ..metrics import compute as compute_metrics
from ..metrics import earnings as earnings_metrics
from . import alerts as alert_rules
from . import thesis as thesis_rules
from .portfolio import Holding


@dataclass
class MonitorResult:
    ticker: str
    snapshot: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)
    error: str | None = None


def _snapshot(holding: Holding, settings: Settings, lens: str) -> dict:
    """Istantanea minima da persistere e confrontare."""
    ticker = holding.ticker
    price = providers.get_price(ticker)

    # ETF/fondi: nessun bilancio. Salta i calcoli da azione (evita anche il
    # tentativo FMP che fallirebbe) e registra metriche adatte allo strumento.
    if price.asset_type in ETF_LIKE:
        prof = providers.get_etf_profile(ticker, holding.isin)
        return {
            "price": price.price,
            "asset_type": price.asset_type,
            "name": prof.name,
            "expense_ratio_pct": _pct(prof.expense_ratio),
            "dividend_yield_pct": _pct(prof.dividend_yield),
            "distribution_policy": prof.distribution_policy,
            "index_name": prof.index_name,
        }

    fin = providers.get_financials(ticker, settings)
    metrics = compute_metrics(lens, price, fin)
    latest_fy = fin.income[0].fiscal_year if fin.income else None
    snap = {
        "price": price.price,
        "asset_type": price.asset_type,
        "fiscal_year": latest_fy,
        "pe_ratio": metrics.get("pe_ratio"),
        "margin_of_safety_pct": metrics.get("margin_of_safety_pct"),
        "moat_rating": metrics.get("moat_rating"),
    }
    # variazioni YoY dell'ultimo bilancio: qualificano l'alert "nuovo bilancio"
    snap.update(earnings_metrics.latest_changes(fin))
    return snap


def _pct(frac: float | None) -> float | None:
    """Frazione (0.0022) -> percentuale arrotondata (0.22)."""
    return round(frac * 100, 2) if frac is not None else None


def monitor(holdings: list[Holding], settings: Settings, prev_state: dict) -> tuple[list[MonitorResult], dict]:
    results: list[MonitorResult] = []
    new_state: dict = {}
    for h in holdings:
        try:
            cur = _snapshot(h, settings, settings.lens)
        except Exception as exc:  # noqa: BLE001 - isola il titolo problematico
            results.append(MonitorResult(h.ticker, error=f"{type(exc).__name__}: {exc}"))
            # mantieni lo stato precedente se il fetch fallisce
            if h.ticker in prev_state:
                new_state[h.ticker] = prev_state[h.ticker]
            continue

        a = alert_rules.evaluate(h.ticker, h.cost_basis, prev_state.get(h.ticker), cur, settings.lens)
        a += thesis_rules.evaluate(h.ticker, h.thesis, cur)
        results.append(MonitorResult(h.ticker, snapshot=cur, alerts=a))
        new_state[h.ticker] = cur
    return results, new_state
