"""Lente DIVIDENDI: rendimento, sostenibilità, copertura."""
from __future__ import annotations

from ..data.schemas import FinancialHistory, PriceSnapshot


def _latest(items):
    return items[0] if items else None


def compute(price: PriceSnapshot, fin: FinancialHistory) -> dict:
    out: dict = {"lens": "dividends", "ticker": price.ticker}
    cf = _latest(fin.cash_flow)
    inc = _latest(fin.income)

    # dividendi pagati sono negativi nei cash flow statement
    div_paid = abs(cf.dividends_paid) if cf and cf.dividends_paid else None

    if div_paid and price.market_cap:
        out["dividend_yield_pct"] = round(100 * div_paid / price.market_cap, 2)

    # payout ratio = dividendi / utile netto
    if div_paid and inc and inc.net_income:
        out["payout_ratio_pct"] = round(100 * div_paid / inc.net_income, 1)

    # copertura con FCF (più severa del payout su utili)
    if div_paid and cf and cf.free_cash_flow:
        out["fcf_coverage_x"] = round(cf.free_cash_flow / div_paid, 2)
    return out
