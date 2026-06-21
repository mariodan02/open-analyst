"""Earnings deltas: variazioni anno-su-anno dell'ultimo esercizio.

Confronta l'ultimo bilancio col precedente (ricavi, utile, margine operativo).
Usato dalla Fase 3 per qualificare l'alert "nuovo bilancio": non solo che è
uscito, ma se i fondamentali migliorano o peggiorano.
"""
from __future__ import annotations

from ..data.schemas import FinancialHistory


def latest_changes(fin: FinancialHistory) -> dict:
    inc = fin.income  # dal più recente al più vecchio
    if len(inc) < 2:
        return {}
    new, prev = inc[0], inc[1]
    out: dict = {}

    if new.operating_revenue and prev.operating_revenue and prev.operating_revenue > 0:
        out["revenue_yoy_pct"] = round(100 * (new.operating_revenue / prev.operating_revenue - 1), 1)

    # YoY dell'utile solo con base positiva: da una perdita la percentuale è
    # priva di significato (la segnaliamo a parte come ritorno all'utile/perdita)
    if new.net_income is not None and prev.net_income and prev.net_income > 0:
        out["net_income_yoy_pct"] = round(100 * (new.net_income / prev.net_income - 1), 1)

    if (new.operating_income is not None and new.operating_revenue
            and prev.operating_income is not None and prev.operating_revenue):
        m_new = new.operating_income / new.operating_revenue
        m_prev = prev.operating_income / prev.operating_revenue
        out["op_margin_change_pp"] = round(100 * (m_new - m_prev), 1)

    return out
