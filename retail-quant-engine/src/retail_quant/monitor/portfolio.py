"""Il portafoglio: i titoli che possiedi, con quantità e prezzo di carico.

Formato file (JSON):
    {
      "holdings": [
        {"ticker": "AAPL", "shares": 10, "cost_basis": 150.0},
        {"ticker": "PFE",  "shares": 50, "cost_basis": 28.0}
      ]
    }
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


def load_portfolio(path: str | Path) -> list[Holding]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    holdings = data.get("holdings", [])
    out: list[Holding] = []
    for h in holdings:
        if not h.get("ticker"):
            continue
        out.append(
            Holding(
                ticker=str(h["ticker"]).upper(),
                shares=float(h.get("shares", 0) or 0),
                cost_basis=float(h.get("cost_basis", 0) or 0),
            )
        )
    if not out:
        raise ValueError(f"Nessun titolo valido nel portafoglio: {path}")
    return out
