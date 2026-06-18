"""Lente TRADING: prezzo e momentum più che fondamentali.

Usa la serie storica dei prezzi (yfinance), non i bilanci.
"""
from __future__ import annotations

from ..data.schemas import FinancialHistory, PriceSnapshot


def compute(price: PriceSnapshot, fin: FinancialHistory) -> dict:
    import yfinance as yf

    out: dict = {"lens": "trading", "ticker": price.ticker, "price": price.price}
    hist = yf.Ticker(price.ticker).history(period="6mo")
    if hist is None or hist.empty:
        return out

    closes = hist["Close"]
    out["change_1m_pct"] = _pct_change(closes, 21)
    out["change_3m_pct"] = _pct_change(closes, 63)
    if len(closes) >= 50:
        sma50 = closes.tail(50).mean()
        out["sma50"] = round(float(sma50), 2)
        out["above_sma50"] = bool(price.price > sma50)
    return out


def _pct_change(closes, lookback: int) -> float | None:
    if len(closes) > lookback:
        past = float(closes.iloc[-lookback - 1])
        now = float(closes.iloc[-1])
        if past:
            return round(100 * (now - past) / past, 2)
    return None
