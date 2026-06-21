"""DCF intrinsic-value model.

Unlevered FCF projected with growth fading to the terminal rate, discounted at a
CAPM-derived WACC, plus a Gordon-growth terminal value, then bridged
Enterprise Value -> Equity -> per-share. Methodology follows the dcf-model skill.

Assumptions live in DCFAssumptions. Returns None when inputs are insufficient
(non-positive FCF, missing share count) rather than producing a misleading value.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data.schemas import FinancialHistory, PriceSnapshot


@dataclass(frozen=True)
class DCFAssumptions:
    projection_years: int = 5
    terminal_growth: float = 0.025      # long-run GDP proxy
    risk_free: float = 0.043            # 10Y Treasury
    equity_risk_premium: float = 0.05
    default_beta: float = 1.0
    tax_rate: float = 0.21
    debt_spread: float = 0.015          # over risk-free for cost of debt
    max_initial_growth: float = 0.15
    min_initial_growth: float = 0.0
    wacc_floor: float = 0.06
    wacc_cap: float = 0.15


def _cagr(latest: float, oldest: float, years: int) -> float | None:
    if latest and oldest and latest > 0 and oldest > 0 and years > 0:
        return (latest / oldest) ** (1 / years) - 1
    return None


def _wacc(price: PriceSnapshot, net_debt: float, a: DCFAssumptions) -> float:
    beta = price.beta if price.beta and price.beta > 0 else a.default_beta
    cost_equity = a.risk_free + beta * a.equity_risk_premium
    cost_debt_at = (a.risk_free + a.debt_spread) * (1 - a.tax_rate)

    mcap = price.market_cap or (price.price * (price.shares_outstanding or 0))
    debt_for_weights = max(net_debt, 0.0)
    total = mcap + debt_for_weights
    if total <= 0:
        return min(max(cost_equity, a.wacc_floor), a.wacc_cap)
    w_e = mcap / total
    w_d = debt_for_weights / total
    wacc = cost_equity * w_e + cost_debt_at * w_d
    return min(max(wacc, a.wacc_floor), a.wacc_cap)


def intrinsic_value(price: PriceSnapshot, fin: FinancialHistory,
                    a: DCFAssumptions | None = None) -> dict | None:
    a = a or DCFAssumptions()

    if not fin.cash_flow:
        return None
    fcf0 = fin.cash_flow[0].free_cash_flow
    shares = price.shares_outstanding
    if not fcf0 or fcf0 <= 0 or not shares or shares <= 0:
        return None

    net_debt = 0.0
    if fin.balance:
        bal = fin.balance[0]
        if bal.total_debt is not None and bal.cash_and_equivalents is not None:
            net_debt = bal.total_debt - bal.cash_and_equivalents

    wacc = _wacc(price, net_debt, a)
    if wacc <= a.terminal_growth:  # keep WACC > g so terminal value stays finite
        wacc = a.terminal_growth + 0.02

    # initial growth from historical FCF CAGR, clamped to the assumption bounds
    g0 = a.min_initial_growth + 0.08
    if len(fin.cash_flow) >= 2:
        oldest = fin.cash_flow[-1].free_cash_flow
        hist = _cagr(fcf0, oldest, len(fin.cash_flow) - 1)
        if hist is not None:
            g0 = hist
    g0 = min(max(g0, a.min_initial_growth), a.max_initial_growth)

    # growth fades linearly from g0 to terminal_growth over the horizon
    n = a.projection_years
    pv_fcf = 0.0
    fcf = fcf0
    last_fcf = fcf0
    for t in range(1, n + 1):
        g = g0 + (a.terminal_growth - g0) * (t - 1) / max(n - 1, 1)
        fcf = fcf * (1 + g)
        period = t - 0.5  # mid-year convention
        pv_fcf += fcf / (1 + wacc) ** period
        last_fcf = fcf

    tv = last_fcf * (1 + a.terminal_growth) / (wacc - a.terminal_growth)
    pv_tv = tv / (1 + wacc) ** (n - 0.5)

    enterprise_value = pv_fcf + pv_tv
    equity_value = enterprise_value - net_debt
    intrinsic_per_share = equity_value / shares
    if intrinsic_per_share <= 0:
        return None

    margin_of_safety = (intrinsic_per_share - price.price) / intrinsic_per_share * 100
    tv_share_of_ev = pv_tv / enterprise_value * 100 if enterprise_value else None

    return {
        "intrinsic_per_share": round(intrinsic_per_share, 2),
        "margin_of_safety_pct": round(margin_of_safety, 1),
        "wacc_pct": round(wacc * 100, 2),
        "initial_fcf_growth_pct": round(g0 * 100, 2),
        "terminal_value_share_pct": round(tv_share_of_ev, 1) if tv_share_of_ev else None,
        "_method": "DCF (FCF perpetuity, mid-year, CAPM WACC)",
    }
