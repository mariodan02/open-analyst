"""Provider dati retail: FMP (preferito per i bilanci storici) con fallback
su yfinance. Output sempre normalizzato sugli schemi in schemas.py.

Tutte le funzioni degradano con grazia: se un campo manca resta None, non
solleva. Le eccezioni di rete vengono propagate al chiamante (i tool in
tools.py le catturano e le trasformano in un messaggio per il modello).
"""
from __future__ import annotations

import requests

from ..config import Settings
from .schemas import (
    BalanceSheet,
    CashFlow,
    FinancialHistory,
    IncomeStatement,
    NewsItem,
    PriceSnapshot,
)

FMP_BASE = "https://financialmodelingprep.com/api/v3"
_HTTP_TIMEOUT = 20


# --------------------------------------------------------------------------- #
# Prezzo / news: yfinance (gratis, real-time-ish)
# --------------------------------------------------------------------------- #
def get_price(ticker: str) -> PriceSnapshot:
    import yfinance as yf

    info = yf.Ticker(ticker).info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if price is None:
        raise ValueError(f"Prezzo non disponibile per {ticker}")
    return PriceSnapshot(
        ticker=ticker.upper(),
        price=float(price),
        currency=info.get("currency", "USD"),
        market_cap=info.get("marketCap"),
        shares_outstanding=info.get("sharesOutstanding"),
    )


def get_news(ticker: str, limit: int = 5) -> list[NewsItem]:
    import yfinance as yf

    raw = getattr(yf.Ticker(ticker), "news", None) or []
    out: list[NewsItem] = []
    for item in raw[:limit]:
        content = item.get("content", item)  # yfinance ha cambiato schema nel tempo
        out.append(
            NewsItem(
                title=content.get("title", "(senza titolo)"),
                url=(content.get("canonicalUrl") or {}).get("url")
                if isinstance(content.get("canonicalUrl"), dict)
                else content.get("link"),
                published=content.get("pubDate") or content.get("providerPublishTime"),
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Bilanci storici: FMP se hai la chiave, altrimenti yfinance
# --------------------------------------------------------------------------- #
def _fmp_get(path: str, settings: Settings, **params) -> list[dict]:
    params["apikey"] = settings.fmp_api_key
    resp = requests.get(f"{FMP_BASE}/{path}", params=params, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("Error Message"):
        raise RuntimeError(f"FMP error: {data['Error Message']}")
    return data if isinstance(data, list) else []


def get_financials(ticker: str, settings: Settings, years: int = 5) -> FinancialHistory:
    ticker = ticker.upper()
    if settings.fmp_api_key:
        return _financials_fmp(ticker, settings, years)
    return _financials_yfinance(ticker, years)


def _financials_fmp(ticker: str, settings: Settings, years: int) -> FinancialHistory:
    inc = _fmp_get(f"income-statement/{ticker}", settings, limit=years)
    bal = _fmp_get(f"balance-sheet-statement/{ticker}", settings, limit=years)
    cf = _fmp_get(f"cash-flow-statement/{ticker}", settings, limit=years)

    return FinancialHistory(
        ticker=ticker,
        income=[
            IncomeStatement(
                ticker=ticker,
                fiscal_year=int(r.get("calendarYear", 0)),
                operating_revenue=r.get("revenue"),
                gross_profit=r.get("grossProfit"),
                operating_income=r.get("operatingIncome"),
                net_income=r.get("netIncome"),
                eps=r.get("eps"),
                source="fmp",
            )
            for r in inc
        ],
        balance=[
            BalanceSheet(
                ticker=ticker,
                fiscal_year=int(r.get("calendarYear", 0)),
                total_assets=r.get("totalAssets"),
                total_debt=r.get("totalDebt"),
                total_equity=r.get("totalStockholdersEquity"),
                cash_and_equivalents=r.get("cashAndCashEquivalents"),
                source="fmp",
            )
            for r in bal
        ],
        cash_flow=[
            CashFlow(
                ticker=ticker,
                fiscal_year=int(r.get("calendarYear", 0)),
                operating_cash_flow=r.get("operatingCashFlow"),
                capital_expenditure=r.get("capitalExpenditure"),
                free_cash_flow=r.get("freeCashFlow"),
                dividends_paid=r.get("dividendsPaid"),
                source="fmp",
            )
            for r in cf
        ],
    )


def _financials_yfinance(ticker: str, years: int) -> FinancialHistory:
    """Fallback senza chiave FMP. Meno granulare ma gratis."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    hist = FinancialHistory(ticker=ticker)

    fin = t.financials  # DataFrame: righe=voci, colonne=anni
    if fin is not None and not fin.empty:
        for col in list(fin.columns)[:years]:
            year = getattr(col, "year", 0)
            hist.income.append(
                IncomeStatement(
                    ticker=ticker,
                    fiscal_year=year,
                    operating_revenue=_safe(fin, "Total Revenue", col),
                    gross_profit=_safe(fin, "Gross Profit", col),
                    operating_income=_safe(fin, "Operating Income", col),
                    net_income=_safe(fin, "Net Income", col),
                    source="yfinance",
                )
            )
    return hist


def _safe(df, row: str, col):
    try:
        val = df.loc[row, col]
        return float(val) if val == val else None  # NaN check
    except (KeyError, TypeError, ValueError):
        return None
