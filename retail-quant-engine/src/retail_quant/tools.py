"""I data provider esposti come tool LangChain, con VALIDAZIONE DIFENSIVA.

Perché qui e non altrove: i modelli open-weight (Llama/Qwen) sbagliano il tool
calling più di Claude — passano ticker sporchi, chiamano col tipo sbagliato, ecc.
Ogni tool quindi:
  1. normalizza/valida l'input (ticker),
  2. cattura le eccezioni di rete e le restituisce come messaggio leggibile
     dal modello invece di far crashare il grafo,
  3. restituisce sempre JSON serializzabile.
"""
from __future__ import annotations

import json
import re

from langchain_core.tools import tool

from .config import Settings
from .data import providers
from .metrics import compute as compute_metrics

_TICKER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")


def _clean_ticker(raw: str) -> str:
    t = (raw or "").strip().upper()
    if not _TICKER_RE.match(t):
        raise ValueError(f"Ticker non valido: '{raw}'")
    return t


def _safe(fn):
    """Wrap: trasforma le eccezioni in un dict d'errore JSON (no crash del grafo)."""
    try:
        return json.dumps(fn(), default=str)
    except Exception as exc:  # noqa: BLE001 - vogliamo proprio catturare tutto
        return json.dumps({"error": type(exc).__name__, "detail": str(exc)})


def build_tools(settings: Settings):
    """Costruisce i tool legati alle settings correnti (chiavi + lente)."""

    @tool
    def get_price(ticker: str) -> str:
        """Ultimo prezzo, market cap e azioni in circolazione di un titolo."""
        return _safe(lambda: providers.get_price(_clean_ticker(ticker)).model_dump())

    @tool
    def get_financials(ticker: str) -> str:
        """Bilanci storici (conto economico, SP, cash flow) fino a 5 anni."""
        return _safe(
            lambda: providers.get_financials(
                _clean_ticker(ticker), settings
            ).model_dump()
        )

    @tool
    def get_news(ticker: str) -> str:
        """Ultime notizie su un titolo."""
        return _safe(
            lambda: [n.model_dump() for n in providers.get_news(_clean_ticker(ticker))]
        )

    @tool
    def get_metrics(ticker: str) -> str:
        """Metriche dello stile di investimento attivo (lente) per un titolo."""

        def _run():
            t = _clean_ticker(ticker)
            price = providers.get_price(t)
            fin = providers.get_financials(t, settings)
            return compute_metrics(settings.lens, price, fin)

        return _safe(_run)

    return [get_price, get_financials, get_news, get_metrics]
