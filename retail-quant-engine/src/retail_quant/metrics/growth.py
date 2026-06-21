"""Lente GROWTH: crescita di ricavi/utili e tenuta dei margini."""
from __future__ import annotations

from ..data.schemas import FinancialHistory, PriceSnapshot


def _cagr(latest: float, oldest: float, years: int) -> float | None:
    # CAGR definito solo tra valori dello STESSO segno positivo. Se uno dei due
    # è ≤ 0 (es. utile passato in perdita) il calcolo non ha senso e darebbe un
    # numero complesso o un risultato fuorviante -> None.
    if latest and oldest and latest > 0 and oldest > 0 and years > 0:
        return round(100 * ((latest / oldest) ** (1 / years) - 1), 2)
    return None


def compute(price: PriceSnapshot, fin: FinancialHistory) -> dict:
    out: dict = {"lens": "growth", "ticker": price.ticker}
    inc = fin.income  # già ordinato dal più recente al più vecchio
    if len(inc) >= 2:
        new, old = inc[0], inc[-1]
        years = len(inc) - 1
        if new.operating_revenue and old.operating_revenue:
            out["revenue_cagr_pct"] = _cagr(
                new.operating_revenue, old.operating_revenue, years
            )
        if new.net_income and old.net_income:
            out["net_income_cagr_pct"] = _cagr(new.net_income, old.net_income, years)
        # espansione margine operativo
        if new.operating_income and new.operating_revenue and old.operating_income and old.operating_revenue:
            margin_new = new.operating_income / new.operating_revenue
            margin_old = old.operating_income / old.operating_revenue
            out["operating_margin_change_pp"] = round(100 * (margin_new - margin_old), 2)
    return out
