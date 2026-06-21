"""Calendario eventi: raccoglie i prossimi catalizzatori (earnings, stacco
dividendo) per i titoli del portafoglio, entro un orizzonte di giorni.

Deterministico (yfinance). Gli ETF di norma non hanno earnings: semplicemente
non producono eventi. `today` è iniettabile per i test.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..config import Settings
from ..data import providers
from ..monitor.portfolio import Holding

_EVENT_LABELS = {"earnings_date": "Earnings", "ex_dividend_date": "Stacco dividendo"}


@dataclass
class Event:
    ticker: str
    kind: str
    on: date
    days_until: int


@dataclass
class CatalystResult:
    events: list[Event] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def upcoming(holdings: list[Holding], settings: Settings,
             horizon_days: int = 90, today: date | None = None) -> CatalystResult:
    today = today or date.today()
    res = CatalystResult()
    for h in holdings:
        try:
            cats = providers.get_catalysts(h.ticker)
        except Exception as exc:  # noqa: BLE001
            res.errors.append(f"{h.ticker}: {type(exc).__name__}: {exc}")
            continue
        for kind, when in cats.items():
            if not isinstance(when, date):
                continue
            days = (when - today).days
            if 0 <= days <= horizon_days:
                res.events.append(Event(h.ticker, kind, when, days))
    res.events.sort(key=lambda e: e.days_until)
    return res


def build_markdown(res: CatalystResult, horizon_days: int) -> str:
    lines = [f"# Prossimi eventi (entro {horizon_days} giorni)", ""]
    if not res.events:
        lines.append("_Nessun evento in calendario nell'orizzonte scelto._")
    else:
        lines.append("| Quando | Tra | Titolo | Evento |")
        lines.append("|---|---|---|---|")
        for e in res.events:
            lines.append(
                f"| {e.on.isoformat()} | {e.days_until}g | **{e.ticker}** | "
                f"{_EVENT_LABELS.get(e.kind, e.kind)} |"
            )
    if res.errors:
        lines.append(f"\n_({len(res.errors)} titoli senza calendario disponibile)_")
    return "\n".join(lines)
