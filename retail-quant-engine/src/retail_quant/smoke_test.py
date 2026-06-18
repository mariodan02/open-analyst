"""Smoke test della Fase 0 — NON usa l'LLM, solo dati + metriche.

    python -m retail_quant.smoke_test AAPL

Verifica che: le chiavi siano caricate, i provider rispondano, e la lente
attiva produca metriche. È il primo controllo da fare prima di toccare NVIDIA.
"""
from __future__ import annotations

import json
import sys

from .config import Settings
from .data import providers
from .metrics import compute as compute_metrics


def main(ticker: str) -> None:
    settings = Settings.load(require_llm=False)
    print(f"Lente attiva: {settings.lens}")
    print(f"FMP: {'sì' if settings.fmp_api_key else 'no (fallback yfinance)'}\n")

    price = providers.get_price(ticker)
    print("PREZZO:", price.model_dump_json(indent=2))

    fin = providers.get_financials(ticker, settings)
    print(f"\nBILANCI: {len(fin.income)} anni di conto economico recuperati")

    metrics = compute_metrics(settings.lens, price, fin)
    print("\nMETRICHE:", json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m retail_quant.smoke_test <TICKER>")
        raise SystemExit(1)
    main(sys.argv[1])
