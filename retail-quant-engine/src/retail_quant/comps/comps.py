"""Valutazione relativa: confronta i multipli del target con la mediana dei pari.

Multipli calcolati solo da dati affidabili (prezzo yfinance + bilanci). Si
evitano EV/EBITDA (D&A non sempre disponibile dal fallback yfinance) a favore di
P/E, P/S e margini, che reggono anche senza FMP. Tutto deterministico.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from ..config import Settings
from ..data import providers


@dataclass
class CompRow:
    ticker: str
    pe: float | None = None
    ps: float | None = None
    gross_margin_pct: float | None = None
    operating_margin_pct: float | None = None
    error: str | None = None


# multipli dove "più basso = più economico" (per il verdetto relativo)
VALUATION_MULTIPLES = ("pe", "ps")


def _row(ticker: str, settings: Settings) -> CompRow:
    try:
        price = providers.get_price(ticker)
        fin = providers.get_financials(ticker, settings)
        inc = fin.income[0] if fin.income else None
        row = CompRow(ticker=ticker.upper())
        if inc and price.market_cap:
            if inc.net_income and inc.net_income > 0:
                row.pe = round(price.market_cap / inc.net_income, 2)
            if inc.operating_revenue and inc.operating_revenue > 0:
                row.ps = round(price.market_cap / inc.operating_revenue, 2)
        if inc and inc.operating_revenue:
            if inc.gross_profit is not None:
                row.gross_margin_pct = round(100 * inc.gross_profit / inc.operating_revenue, 2)
            if inc.operating_income is not None:
                row.operating_margin_pct = round(100 * inc.operating_income / inc.operating_revenue, 2)
        return row
    except Exception as exc:  # noqa: BLE001 - isola il singolo ticker
        return CompRow(ticker=ticker.upper(), error=f"{type(exc).__name__}: {exc}")


def compare(target: str, peers: list[str], settings: Settings) -> dict:
    target = target.upper()
    rows = [_row(t, settings) for t in [target, *peers]]
    target_row = rows[0]
    peer_rows = [r for r in rows[1:] if r.error is None]

    medians: dict[str, float] = {}
    relative: dict[str, dict] = {}
    for field in ("pe", "ps", "gross_margin_pct", "operating_margin_pct"):
        vals = [getattr(r, field) for r in peer_rows if getattr(r, field) is not None]
        if not vals:
            continue
        med = round(median(vals), 2)
        medians[field] = med
        tv = getattr(target_row, field)
        if tv is not None and med:
            relative[field] = {
                "target": tv,
                "peer_median": med,
                "diff_pct": round(100 * (tv - med) / med, 1),
            }

    return {
        "target": target,
        "rows": rows,
        "peer_medians": medians,
        "relative": relative,
        "verdict": _verdict(relative),
    }


def _verdict(relative: dict[str, dict]) -> str:
    """Sintesi: i multipli di valutazione del target sono sotto/sopra i pari?"""
    checks = [relative[m]["diff_pct"] for m in VALUATION_MULTIPLES if m in relative]
    if not checks:
        return "Dati insufficienti per un confronto relativo."
    avg = sum(checks) / len(checks)
    if avg <= -10:
        return f"Più economico dei pari (multipli ~{avg:.0f}% sotto la mediana)."
    if avg >= 10:
        return f"Più caro dei pari (multipli ~{avg:+.0f}% sopra la mediana)."
    return f"In linea con i pari (multipli ~{avg:+.0f}% vs mediana)."
