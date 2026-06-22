"""Stato del grafo. total=False: i nodi riempiono campi parziali a turno."""
from __future__ import annotations

from typing import TypedDict

from ..data.schemas import EtfProfile, FinancialHistory, NewsItem, PriceSnapshot


class AnalysisState(TypedDict, total=False):
    ticker: str
    lens: str
    isin: str | None  # opzionale; per gli ETF abilita il profilo justETF
    # popolati da fetch
    price: PriceSnapshot | None
    financials: FinancialHistory | None
    etf_profile: EtfProfile | None  # solo per asset_type ETF/fondo
    news: list[NewsItem]
    # popolati da metrics
    metrics: dict
    # popolato da thesis (LLM)
    thesis: str
    # popolati da validate
    report: str
    warnings: list[str]
    errors: list[str]
