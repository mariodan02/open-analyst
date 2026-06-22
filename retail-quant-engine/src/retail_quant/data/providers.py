"""Provider dati retail: FMP (preferito per i bilanci storici) con fallback
su yfinance. Output sempre normalizzato sugli schemi in schemas.py.

Tutte le funzioni degradano con grazia: se un campo manca resta None, non
solleva. Le eccezioni di rete vengono propagate al chiamante (i tool in
tools.py le catturano e le trasformano in un messaggio per il modello).
"""
from __future__ import annotations

import re

import requests

from ..config import Settings
from .schemas import (
    BalanceSheet,
    CashFlow,
    EtfProfile,
    FinancialHistory,
    IncomeStatement,
    NewsItem,
    PriceSnapshot,
)

# API "stable" di FMP (la v3 è legacy e bloccata per le chiavi emesse dopo
# il 31/8/2025). Gli endpoint stable usano ?symbol=TICKER come query param.
FMP_BASE = "https://financialmodelingprep.com/stable"
_HTTP_TIMEOUT = 30


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
        beta=info.get("beta"),
        asset_type=(info.get("quoteType") or "equity").lower(),
    )


def get_etf_profile(ticker: str, isin: str | None = None) -> EtfProfile:
    """Metriche per ETF/fondi (TER, rendimento, politica dividendi).

    Base da yfinance; se è noto l'ISIN, arricchisce con justETF (TER e politica
    dividendi affidabili). Lo scraping justETF è best-effort: ogni errore di rete
    o di parsing degrada senza sollevare, lasciando i campi yfinance.
    """
    import yfinance as yf

    info = yf.Ticker(ticker).info
    profile = EtfProfile(
        ticker=ticker.upper(),
        isin=isin,
        name=info.get("longName") or info.get("shortName"),
        expense_ratio=info.get("annualReportExpenseRatio") or info.get("netExpenseRatio"),
        dividend_yield=info.get("yield"),
        category=info.get("category"),
    )
    if isin:
        try:
            _enrich_from_justetf(profile, isin)
        except (requests.RequestException, ValueError) as exc:
            print(f"[warn] justETF non disponibile per {isin} ({exc}); uso solo yfinance.")
    return profile


# --------------------------------------------------------------------------- #
# justETF: profilo ETF per ISIN (TER, politica dividendi, indice). Nessuna
# chiave; pagina pubblica. Le ancore data-testid sono stabili nel frontend.
# --------------------------------------------------------------------------- #
JUSTETF_PROFILE = "https://www.justetf.com/en/etf-profile.html"
_JUSTETF_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en"}


def _enrich_from_justetf(profile: EtfProfile, isin: str) -> None:
    resp = requests.get(
        JUSTETF_PROFILE, params={"isin": isin}, headers=_JUSTETF_HEADERS, timeout=_HTTP_TIMEOUT
    )
    resp.raise_for_status()
    html = resp.text

    name = _justetf_field(html, "etf-profile-header_etf-name")
    ter = _justetf_field(html, "etf-profile-header_ter-value")
    policy = _justetf_field(html, "etf-profile-header_distribution-policy-value")
    index = _justetf_field(html, "tl_etf-basics_value_index-name")

    if name:
        profile.name = name
    if index:
        profile.index_name = index
    if policy:
        profile.distribution_policy = policy
        # un ETF ad accumulazione non distribuisce: il rendimento da yfinance
        # (spesso 0/None) non è informativo, azzeralo per non confondere.
        if "accumul" in policy.lower():
            profile.dividend_yield = None
    if ter:
        pct = _first_number(ter)
        if pct is not None:
            profile.expense_ratio = pct / 100  # "0.19% p.a." -> 0.0019
    profile.source = "justetf+yfinance"


def _justetf_field(html: str, testid: str) -> str | None:
    """Testo subito dopo un data-testid (fino al primo tag). None se assente."""
    m = re.search(rf'data-testid="{re.escape(testid)}"[^>]*>([^<]*)', html)
    if not m:
        return None
    text = m.group(1).strip()
    return text or None


def _first_number(text: str) -> float | None:
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


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
        try:
            return _financials_fmp(ticker, settings, years)
        except (requests.RequestException, RuntimeError) as exc:
            # FMP può rifiutare la richiesta (402 quota/piano, 403 chiave, rete).
            # Non è un errore fatale: ripieghiamo su yfinance (conto economico
            # parziale) così l'analisi prosegue invece di andare in crash.
            print(f"[warn] FMP non disponibile per {ticker} ({exc}); uso yfinance.")
    return _financials_yfinance(ticker, years)


def _financials_fmp(ticker: str, settings: Settings, years: int) -> FinancialHistory:
    inc = _fmp_get("income-statement", settings, symbol=ticker, limit=years)
    bal = _fmp_get("balance-sheet-statement", settings, symbol=ticker, limit=years)
    cf = _fmp_get("cash-flow-statement", settings, symbol=ticker, limit=years)

    return FinancialHistory(
        ticker=ticker,
        income=[
            IncomeStatement(
                ticker=ticker,
                fiscal_year=int(r.get("fiscalYear", 0)),
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
                fiscal_year=int(r.get("fiscalYear", 0)),
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
                fiscal_year=int(r.get("fiscalYear", 0)),
                operating_cash_flow=r.get("operatingCashFlow"),
                capital_expenditure=r.get("capitalExpenditure"),
                free_cash_flow=r.get("freeCashFlow"),
                # nella API stable il campo si chiama netDividendsPaid (negativo)
                dividends_paid=r.get("netDividendsPaid", r.get("dividendsPaid")),
                source="fmp",
            )
            for r in cf
        ],
    )


def _financials_yfinance(ticker: str, years: int) -> FinancialHistory:
    """Fallback senza chiave FMP (o se FMP rifiuta). Meno granulare ma gratis.

    yfinance espone tre DataFrame separati (righe=voci, colonne=anni). Le
    etichette delle righe cambiano tra versioni, quindi `_safe` prova più nomi
    e torna None se nessuno c'è — così le metriche calcolano ciò che possono.
    """
    import yfinance as yf

    t = yf.Ticker(ticker)
    hist = FinancialHistory(ticker=ticker)

    fin = t.financials  # conto economico
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

    bal = t.balance_sheet  # stato patrimoniale -> debito/equity
    if bal is not None and not bal.empty:
        for col in list(bal.columns)[:years]:
            hist.balance.append(
                BalanceSheet(
                    ticker=ticker,
                    fiscal_year=getattr(col, "year", 0),
                    total_assets=_safe(bal, "Total Assets", col),
                    total_debt=_safe(bal, "Total Debt", col),
                    total_equity=_safe(
                        bal, "Stockholders Equity", col, "Total Stockholder Equity"
                    ),
                    cash_and_equivalents=_safe(
                        bal, "Cash And Cash Equivalents", col
                    ),
                    source="yfinance",
                )
            )

    cf = t.cashflow  # rendiconto finanziario -> FCF
    if cf is not None and not cf.empty:
        for col in list(cf.columns)[:years]:
            hist.cash_flow.append(
                CashFlow(
                    ticker=ticker,
                    fiscal_year=getattr(col, "year", 0),
                    operating_cash_flow=_safe(cf, "Operating Cash Flow", col),
                    capital_expenditure=_safe(cf, "Capital Expenditure", col),
                    free_cash_flow=_safe(cf, "Free Cash Flow", col),
                    dividends_paid=_safe(cf, "Cash Dividends Paid", col),
                    source="yfinance",
                )
            )

    return hist


def _safe(df, row: str, col, *alt_rows: str):
    """Legge df.loc[row, col] provando anche nomi-riga alternativi (yfinance
    cambia le etichette tra versioni). Torna None se assente o NaN."""
    for name in (row, *alt_rows):
        try:
            val = df.loc[name, col]
        except (KeyError, TypeError):
            continue
        try:
            return float(val) if val == val else None  # NaN check
        except (TypeError, ValueError):
            return None
    return None
