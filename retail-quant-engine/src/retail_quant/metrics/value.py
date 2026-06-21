"""Value lens: P/E, FCF yield, debt/equity, a DCF-based margin of safety, and
moat indicators (durability of the advantage)."""
from __future__ import annotations

from ..data.schemas import FinancialHistory, PriceSnapshot
from ..valuation.dcf import intrinsic_value
from . import moat


def _latest(items):
    return items[0] if items else None


def compute(price: PriceSnapshot, fin: FinancialHistory) -> dict:
    inc = _latest(fin.income)
    bal = _latest(fin.balance)
    cf = _latest(fin.cash_flow)

    out: dict = {"lens": "value", "ticker": price.ticker}

    if inc and inc.net_income and price.market_cap:
        out["pe_ratio"] = round(price.market_cap / inc.net_income, 2)

    if cf and cf.free_cash_flow and price.market_cap:
        out["fcf_yield_pct"] = round(100 * cf.free_cash_flow / price.market_cap, 2)

    # equity must be positive: a negative denominator yields a misleadingly low ratio
    if bal and bal.total_debt is not None and bal.total_equity and bal.total_equity > 0:
        out["debt_to_equity"] = round(bal.total_debt / bal.total_equity, 2)

    # None when inputs are insufficient (e.g. non-positive FCF)
    dcf = intrinsic_value(price, fin)
    if dcf:
        out["intrinsic_per_share"] = dcf["intrinsic_per_share"]
        out["margin_of_safety_pct"] = dcf["margin_of_safety_pct"]
        out["wacc_pct"] = dcf["wacc_pct"]
        out["_valuation_method"] = dcf["_method"]

    # moat: la durabilità del vantaggio rafforza il giudizio value
    out.update(moat.compute(fin))
    return out
