"""Layer metriche: gli STILI di investimento vivono qui.

Ogni lente è una funzione pura (dati -> dict di metriche). Stessi dati grezzi,
calcoli diversi. Si seleziona la lente attiva via Settings.lens.
"""
from __future__ import annotations

from ..data.schemas import FinancialHistory, PriceSnapshot
from . import dividends, growth, trading, value

_REGISTRY = {
    "value": value.compute,
    "growth": growth.compute,
    "dividends": dividends.compute,
    "trading": trading.compute,
}


def compute(lens: str, price: PriceSnapshot, fin: FinancialHistory) -> dict:
    """Calcola le metriche della lente scelta. Restituisce un dict JSON-safe."""
    fn = _REGISTRY.get(lens)
    if fn is None:
        raise ValueError(f"Lente sconosciuta: {lens}")
    return fn(price, fin)
