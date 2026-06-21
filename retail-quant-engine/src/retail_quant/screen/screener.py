"""Lo screener: cicla su una lista di titoli, calcola metriche e applica i
criteri della lente. Deterministico, niente LLM. Errori per-titolo isolati
(un ticker rotto non ferma lo screening).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..data import providers
from ..metrics import compute as compute_metrics
from . import criteria


@dataclass
class ScreenRow:
    ticker: str
    score: float = 0.0
    passes: bool = False
    metrics: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    error: str | None = None


def screen_one(ticker: str, lens: str, settings: Settings) -> ScreenRow:
    ticker = ticker.upper()
    # tutto in un solo try: anche il calcolo metriche/criteri può sollevare su
    # dati anomali, e un titolo problematico non deve fermare l'intero screening.
    try:
        price = providers.get_price(ticker)
        fin = providers.get_financials(ticker, settings)
        metrics = compute_metrics(lens, price, fin)
        passes, score, reasons = criteria.evaluate(lens, metrics)
    except Exception as exc:  # noqa: BLE001 - isola il titolo problematico
        return ScreenRow(ticker=ticker, error=f"{type(exc).__name__}: {exc}")

    return ScreenRow(
        ticker=ticker, score=score, passes=passes, metrics=metrics, reasons=reasons
    )


def screen_universe(tickers: list[str], lens: str, settings: Settings) -> list[ScreenRow]:
    rows = [screen_one(t, lens, settings) for t in tickers]
    # ordina: prima chi passa, poi per score decrescente; gli errori in fondo
    rows.sort(key=lambda r: (r.error is not None, not r.passes, -r.score))
    return rows


def shortlist(rows: list[ScreenRow]) -> list[ScreenRow]:
    return [r for r in rows if r.passes and r.error is None]
