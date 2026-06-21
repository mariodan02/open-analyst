"""Moat indicators: durability signals from multi-year financials.

A durable competitive advantage shows up as high and stable gross margins
(pricing power), efficient use of capital (ROE) and consistent revenue growth
(demand durability). These are computed deterministically; the thesis node
interprets them. Used to reinforce the value lens.
"""
from __future__ import annotations

from statistics import mean, pstdev

from ..data.schemas import FinancialHistory


def compute(fin: FinancialHistory) -> dict:
    inc = fin.income  # ordinato dal più recente al più vecchio
    bal_by_year = {b.fiscal_year: b for b in fin.balance}
    out: dict = {}

    gross_margins = [
        i.gross_profit / i.operating_revenue
        for i in inc
        if i.gross_profit is not None and i.operating_revenue
    ]
    if gross_margins:
        out["gross_margin_avg_pct"] = round(100 * mean(gross_margins), 2)
        if len(gross_margins) >= 2:
            # deviazione std in punti percentuali: bassa = pricing power stabile
            out["gross_margin_volatility_pp"] = round(100 * pstdev(gross_margins), 2)

    op_margins = [
        i.operating_income / i.operating_revenue
        for i in inc
        if i.operating_income is not None and i.operating_revenue
    ]
    if op_margins:
        out["operating_margin_avg_pct"] = round(100 * mean(op_margins), 2)

    # ROE medio come proxy di efficienza del capitale (il ROIC richiederebbe il
    # capitale investito, non sempre disponibile dal fallback yfinance).
    roes = []
    for i in inc:
        b = bal_by_year.get(i.fiscal_year)
        if b and i.net_income is not None and b.total_equity and b.total_equity > 0:
            roes.append(i.net_income / b.total_equity)
    if roes:
        out["roe_avg_pct"] = round(100 * mean(roes), 2)

    # consistenza crescita ricavi: quota di anni con ricavi in aumento YoY
    revs = [i.operating_revenue for i in inc if i.operating_revenue]
    if len(revs) >= 2:
        ups = sum(1 for new, old in zip(revs, revs[1:]) if new > old)
        out["revenue_growth_consistency_pct"] = round(100 * ups / (len(revs) - 1), 2)

    rating = _rating(out)
    if rating:
        out["moat_rating"] = rating
    return out


def _rating(m: dict) -> str | None:
    """Sintesi euristica: wide / narrow / none. Soglie volutamente prudenti."""
    gm = m.get("gross_margin_avg_pct")
    roe = m.get("roe_avg_pct")
    vol = m.get("gross_margin_volatility_pp")
    if gm is None and roe is None:
        return None
    high_margin = gm is not None and gm >= 40
    score = 0
    if high_margin:
        score += 1
    if roe is not None and roe >= 15:
        score += 1
    # la stabilità è un fossato solo se i margini sono già alti: margini bassi
    # ma stabili sono un business mediocre, non un vantaggio competitivo
    if high_margin and vol is not None and vol <= 3:
        score += 1
    return "wide" if score >= 3 else "narrow" if score >= 1 else "none"
