"""Schemi di output stabili.

REGOLA D'ORO (TODO Fase 0): i tool restituiscono SEMPRE le stesse chiavi,
in inglese, indipendentemente dalla fonte (yfinance o FMP). Così le metriche
e gli agenti a valle non si rompono se cambi provider.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# Tipi senza bilancio: le lenti da azione e il DCF non si applicano.
ETF_LIKE = frozenset({"etf", "mutualfund"})


class PriceSnapshot(BaseModel):
    ticker: str
    price: float
    currency: str = "USD"
    market_cap: float | None = None
    shares_outstanding: float | None = None
    beta: float | None = None  # per il WACC (CAPM) nel DCF
    # "equity" | "etf" | "mutualfund" | ... (da yfinance quoteType). Gli ETF/fondi
    # non hanno bilanci: le lenti da azione non si applicano.
    asset_type: str = "equity"
    source: str = "yfinance"


class EtfProfile(BaseModel):
    """Profilo per ETF/fondi: metriche adatte a uno strumento senza bilancio."""

    ticker: str
    isin: str | None = None
    name: str | None = None
    expense_ratio: float | None = None  # TER (frazione, es. 0.0019 = 0.19%)
    dividend_yield: float | None = None  # frazione (None se ad accumulazione)
    distribution_policy: str | None = None  # "Accumulating" | "Distributing"
    index_name: str | None = None
    category: str | None = None
    source: str = "yfinance"


class IncomeStatement(BaseModel):
    ticker: str
    fiscal_year: int
    operating_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None
    source: str


class BalanceSheet(BaseModel):
    ticker: str
    fiscal_year: int
    total_assets: float | None = None
    total_debt: float | None = None
    total_equity: float | None = None
    cash_and_equivalents: float | None = None
    source: str


class CashFlow(BaseModel):
    ticker: str
    fiscal_year: int
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    free_cash_flow: float | None = None
    dividends_paid: float | None = None
    source: str


class NewsItem(BaseModel):
    title: str
    url: str | None = None
    published: str | None = None


class FinancialHistory(BaseModel):
    """Serie storica multi-anno, ciò che serve a value/growth/dividendi."""

    ticker: str
    income: list[IncomeStatement] = Field(default_factory=list)
    balance: list[BalanceSheet] = Field(default_factory=list)
    cash_flow: list[CashFlow] = Field(default_factory=list)
