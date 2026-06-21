"""Thesis tracker: verifica i guardrail della tesi d'acquisto contro i dati
correnti e segnala quando un'ipotesi non regge più.

La tesi è un dict di soglie opzionali sull'holding:
    max_pe                  -> avvisa se il P/E supera questo valore
    min_revenue_growth_pct  -> avvisa se la crescita ricavi YoY scende sotto
    min_moat_rating         -> avvisa se il moat scende sotto ("none"<"narrow"<"wide")
Solo le chiavi presenti vengono valutate; il resto è ignorato.
"""
from __future__ import annotations

from .alerts import Alert, _num

_MOAT_ORDER = {"none": 0, "narrow": 1, "wide": 2}


def evaluate(ticker: str, thesis: dict | None, cur: dict) -> list[Alert]:
    if not thesis:
        return []
    out: list[Alert] = []

    pe, max_pe = _num(cur.get("pe_ratio")), _num(thesis.get("max_pe"))
    if pe is not None and max_pe is not None and pe > max_pe:
        out.append(Alert(ticker, "warn", f"Tesi a rischio: P/E {pe:.0f} oltre il tuo max {max_pe:.0f}"))

    g, min_g = _num(cur.get("revenue_yoy_pct")), _num(thesis.get("min_revenue_growth_pct"))
    if g is not None and min_g is not None and g < min_g:
        out.append(Alert(ticker, "warn",
                         f"Tesi a rischio: crescita ricavi {g:+.0f}% sotto il minimo {min_g:+.0f}%"))

    mr, min_mr = cur.get("moat_rating"), thesis.get("min_moat_rating")
    if mr and min_mr and _MOAT_ORDER.get(mr, 0) < _MOAT_ORDER.get(min_mr, 0):
        out.append(Alert(ticker, "warn", f"Tesi a rischio: moat '{mr}' sotto l'atteso '{min_mr}'"))

    return out
