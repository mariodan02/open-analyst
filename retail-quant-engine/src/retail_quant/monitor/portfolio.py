"""Il portafoglio: i titoli che possiedi, con quantità e prezzo di carico.

Formato file (JSON):
    {
      "holdings": [
        {"ticker": "AAPL", "shares": 10, "cost_basis": 150.0},
        {"ticker": "PFE",  "shares": 50, "cost_basis": 28.0},
        {"ticker": "VWCE.MI", "shares": 6, "cost_basis": 151.27, "isin": "IE00BK5BQT80"}
      ]
    }

L'ISIN è opzionale: per gli ETF abilita il profilo justETF (TER, politica
dividendi). Per le azioni è ignorato.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Holding:
    ticker: str
    shares: float = 0.0
    cost_basis: float = 0.0  # prezzo medio di acquisto per azione
    isin: str | None = None  # opzionale; abilita il profilo ETF via justETF


def load_portfolio(path: str | Path) -> list[Holding]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    holdings = data.get("holdings", [])
    out: list[Holding] = []
    for h in holdings:
        if not h.get("ticker"):
            continue
        isin = h.get("isin")
        out.append(
            Holding(
                ticker=str(h["ticker"]).upper(),
                shares=float(h.get("shares", 0) or 0),
                cost_basis=float(h.get("cost_basis", 0) or 0),
                isin=str(isin).upper() if isin else None,
            )
        )
    if not out:
        raise ValueError(f"Nessun titolo valido nel portafoglio: {path}")
    return out
