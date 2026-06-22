"""Esporta posizioni + P/L in CSV. Valori convertiti nella valuta base (come
returns). Una riga per titolo più una riga di totale.
"""
from __future__ import annotations

import csv
from pathlib import Path

from ..config import Settings
from ..monitor.portfolio import Holding
from ..returns import returns

FIELDS = ["ticker", "quote_currency", "shares", "cost_basis",
          "cost_value", "market_value", "pl_abs", "pl_pct", "weight_pct", "base_currency"]


def write_csv(holdings: list[Holding], settings: Settings, path: Path) -> dict:
    rdata = returns.analyze(holdings, settings)
    by_ticker = {h.ticker: h for h in holdings}
    base = rdata["base_currency"]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rdata["rows"]:
            if r.error:
                w.writerow({"ticker": r.ticker, "base_currency": base, "pl_pct": f"errore: {r.error}"})
                continue
            h = by_ticker.get(r.ticker)
            w.writerow({
                "ticker": r.ticker,
                "quote_currency": r.currency,
                "shares": h.shares if h else "",
                "cost_basis": h.cost_basis if h else "",
                "cost_value": r.cost_value,
                "market_value": r.market_value,
                "pl_abs": r.pl_abs,
                "pl_pct": r.pl_pct,
                "weight_pct": r.weight_pct,
                "base_currency": base,
            })
        w.writerow({
            "ticker": "TOTALE",
            "cost_value": rdata["total_cost"],
            "market_value": rdata["total_market"],
            "pl_abs": rdata["total_pl_abs"],
            "pl_pct": rdata["total_pl_pct"],
            "weight_pct": 100.0,
            "base_currency": base,
        })
    return rdata
