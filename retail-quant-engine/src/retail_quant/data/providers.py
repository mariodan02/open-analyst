"""Provider dati retail: FMP (preferito per i bilanci storici) con fallback
su yfinance. Output sempre normalizzato sugli schemi in schemas.py.

Tutte le funzioni degradano con grazia: se un campo manca resta None, non
solleva. Le eccezioni di rete vengono propagate al chiamante (i tool in
tools.py le catturano e le trasformano in un messaggio per il modello).
"""
from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path

import requests

from ..config import Settings
from .cache import JsonCache
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

# Throttle globale: intervallo minimo tra due chiamate di rete, per non farsi
# rifiutare con HTTP 429 quando si itera su molti ticker (comps/screening).
# Tarabile con RQE_REQUEST_DELAY (secondi; 0 = nessun ritardo).
_REQUEST_DELAY = float(os.getenv("RQE_REQUEST_DELAY", "0.34"))
_RATE_LOCK = threading.Lock()
_LAST_CALL = [0.0]


def _throttle() -> None:
    if _REQUEST_DELAY <= 0:
        return
    with _RATE_LOCK:
        wait = _REQUEST_DELAY - (time.monotonic() - _LAST_CALL[0])
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL[0] = time.monotonic()


# Circuit breaker FMP: dopo un rifiuto per quota/piano (402/403/429) si smette di
# interrogare FMP per il resto della sessione e si usa solo yfinance.
_fmp_disabled = False


# --------------------------------------------------------------------------- #
# Prezzo / news: yfinance (gratis, real-time-ish)
# --------------------------------------------------------------------------- #
def get_price(ticker: str) -> PriceSnapshot:
    import yfinance as yf

    _throttle()
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

    _throttle()
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
# I profili sono cache-ati su disco (TER e politica cambiano di rado): meno
# richieste e resilienza se justETF è irraggiungibile entro la finestra.
# --------------------------------------------------------------------------- #
JUSTETF_PROFILE = "https://www.justetf.com/en/etf-profile.html"
_JUSTETF_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en"}
# TTL della cache profili ETF (solo metadati statici: TER, accumulazione,
# indice; MAI il prezzo). Tarabile via RQE_ETF_CACHE_DAYS; 0 = sempre fresco.
_ETF_CACHE_DAYS = float(os.getenv("RQE_ETF_CACHE_DAYS", "7"))
_ETF_CACHE = JsonCache(
    Path(__file__).resolve().parents[3] / "cache" / "etf_profiles.json",
    ttl_seconds=_ETF_CACHE_DAYS * 86400,
)


def _enrich_from_justetf(profile: EtfProfile, isin: str) -> None:
    data = _ETF_CACHE.get(isin)
    if data is None:
        _throttle()
        resp = requests.get(
            JUSTETF_PROFILE, params={"isin": isin}, headers=_JUSTETF_HEADERS, timeout=_HTTP_TIMEOUT
        )
        resp.raise_for_status()
        data = _parse_justetf(resp.text)
        _ETF_CACHE.set(isin, data)
    _apply_justetf(profile, data)


def _parse_justetf(html: str) -> dict:
    """Estrae i campi dal profilo justETF in un dict serializzabile (cache-abile)."""
    out: dict = {}
    name = _justetf_field(html, "etf-profile-header_etf-name")
    ter = _justetf_field(html, "etf-profile-header_ter-value")
    policy = _justetf_field(html, "etf-profile-header_distribution-policy-value")
    index = _justetf_field(html, "tl_etf-basics_value_index-name")
    replication = _justetf_field(html, "etf-profile-header_replication-value")
    domicile = _justetf_field(html, "tl_etf-basics_value_domicile-country")
    holdings = _justetf_field(html, "etf-profile-header_holdings-value")

    if name:
        out["name"] = name
    if index:
        out["index_name"] = index
    if replication:
        out["replication"] = replication
    if domicile:
        out["domicile"] = domicile
    if holdings:
        digits = re.sub(r"[^\d]", "", holdings)
        if digits:
            out["holdings"] = int(digits)
    if policy:
        out["distribution_policy"] = policy
    if ter:
        pct = _first_number(ter)
        if pct is not None:
            out["expense_ratio"] = pct / 100  # "0.19% p.a." -> 0.0019
    return out


def _apply_justetf(profile: EtfProfile, data: dict) -> None:
    for field in ("name", "index_name", "replication", "domicile", "holdings",
                  "distribution_policy", "expense_ratio"):
        if data.get(field) is not None:
            setattr(profile, field, data[field])
    # un ETF ad accumulazione non distribuisce: il rendimento da yfinance
    # (spesso 0/None) non è informativo, azzeralo per non confondere.
    if (profile.distribution_policy or "").lower().find("accumul") >= 0:
        profile.dividend_yield = None
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


def get_isin(ticker: str) -> str | None:
    """ISIN da yfinance. Funziona per le azioni; molti ETF europei tornano '-'
    (in quel caso passa l'ISIN a mano). None se non disponibile."""
    import yfinance as yf

    v = getattr(yf.Ticker(ticker), "isin", None)
    return v if v and v not in ("-", "") else None


# tasso di cambio: cache in-processo (i tassi cambiano al più giornalmente, un
# singolo run usa lo stesso valore)
_FX_CACHE: dict[tuple[str, str], float] = {}


def get_fx_rate(from_cur: str, to_cur: str) -> float:
    """Tasso per convertire 1 unità di from_cur in to_cur (yfinance FROMTO=X)."""
    from_cur, to_cur = from_cur.upper(), to_cur.upper()
    if from_cur == to_cur:
        return 1.0
    key = (from_cur, to_cur)
    if key not in _FX_CACHE:
        import yfinance as yf

        _throttle()
        hist = yf.Ticker(f"{from_cur}{to_cur}=X").history(period="5d")
        if hist is None or hist.empty:
            raise ValueError(f"Tasso di cambio non disponibile: {from_cur}->{to_cur}")
        _FX_CACHE[key] = float(hist["Close"].iloc[-1])
    return _FX_CACHE[key]


def get_catalysts(ticker: str) -> dict:
    """Prossimi eventi (date) da yfinance: earnings e stacco dividendo.

    Restituisce datetime.date o None. Le azioni hanno earnings; gli ETF di solito
    no (calendar vuoto). Degrada a None senza sollevare.
    """
    import yfinance as yf

    _throttle()
    cal = getattr(yf.Ticker(ticker), "calendar", None) or {}

    def _first_date(v):
        if isinstance(v, list):
            return v[0] if v else None
        return v

    return {
        "earnings_date": _first_date(cal.get("Earnings Date")),
        "ex_dividend_date": _first_date(cal.get("Ex-Dividend Date")),
    }


def get_news(ticker: str, limit: int = 5) -> list[NewsItem]:
    import yfinance as yf

    _throttle()
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
    _throttle()
    params["apikey"] = settings.fmp_api_key
    resp = requests.get(f"{FMP_BASE}/{path}", params=params, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("Error Message"):
        raise RuntimeError(f"FMP error: {data['Error Message']}")
    return data if isinstance(data, list) else []


def get_financials(ticker: str, settings: Settings, years: int = 5) -> FinancialHistory:
    global _fmp_disabled
    ticker = ticker.upper()
    if settings.fmp_api_key and not _fmp_disabled:
        try:
            return _financials_fmp(ticker, settings, years)
        except (requests.RequestException, RuntimeError) as exc:
            # FMP può rifiutare la richiesta (402 quota/piano, 403 chiave, 429
            # rate limit, rete). Non è fatale: si ripiega su yfinance.
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (402, 403, 429):
                # quota/piano: inutile insistere ticker dopo ticker -> spegni FMP
                _fmp_disabled = True
                print(f"[warn] FMP non disponibile (HTTP {status}): disabilitato per "
                      f"questa sessione, uso yfinance.")
            else:
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

    _throttle()
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
