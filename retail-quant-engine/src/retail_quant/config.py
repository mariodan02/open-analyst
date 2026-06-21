"""Configurazione centrale: env, ruoli modello, lente metriche attiva.

Carica il .env una sola volta all'import. Tutto il resto del progetto legge
da qui, così non c'è os.getenv sparso ovunque.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# lenti supportate = i quattro stili di investimento
VALID_LENSES = ("value", "growth", "dividends", "trading")


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Variabile d'ambiente mancante: {name}. "
            f"Copia .env.example in .env e inserisci le chiavi."
        )
    return val


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str | None
    fmp_api_key: str | None
    lens: str
    base_currency: str
    model_orchestrator: str
    model_extractor: str

    @classmethod
    def load(cls, require_llm: bool = True) -> "Settings":
        """require_llm=False per i percorsi solo-dati (es. smoke test)."""
        lens = os.getenv("RQE_LENS", "value").lower()
        if lens not in VALID_LENSES:
            raise RuntimeError(
                f"RQE_LENS='{lens}' non valida. Scegli tra: {', '.join(VALID_LENSES)}"
            )
        return cls(
            nvidia_api_key=_require("NVIDIA_API_KEY") if require_llm else os.getenv("NVIDIA_API_KEY"),
            fmp_api_key=os.getenv("FMP_API_KEY"),  # opzionale: fallback su yfinance
            lens=lens,
            # valuta dei totali di portafoglio (returns/rebalance); i valori in
            # altre valute vengono convertiti via FX
            base_currency=os.getenv("RQE_BASE_CURRENCY", "EUR").upper(),
            model_orchestrator=os.getenv(
                "RQE_MODEL_ORCHESTRATOR", "meta/llama-3.1-405b-instruct"
            ),
            model_extractor=os.getenv(
                "RQE_MODEL_EXTRACTOR", "meta/llama-3.1-70b-instruct"
            ),
        )
