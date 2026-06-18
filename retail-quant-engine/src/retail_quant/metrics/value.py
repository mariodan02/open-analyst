"""Lente VALUE: aziende solide sottovalutate (Buffett/Graham).

Metriche: P/E, FCF yield, debito/equity, e un margine di sicurezza GREZZO
basato su un DCF semplificato. NB: il margine di sicurezza serio lo fa la
skill dcf-model del fork (script Python) — qui è un primo segnale, non oro colato.
"""
from __future__ import annotations

from ..data.schemas import FinancialHistory, PriceSnapshot


def _latest(items):
    return items[0] if items else None


def compute(price: PriceSnapshot, fin: FinancialHistory) -> dict:
    inc = _latest(fin.income)
    bal = _latest(fin.balance)
    cf = _latest(fin.cash_flow)

    out: dict = {"lens": "value", "ticker": price.ticker}

    # P/E
    if inc and inc.net_income and price.market_cap:
        out["pe_ratio"] = round(price.market_cap / inc.net_income, 2)

    # FCF yield = FCF / market cap
    if cf and cf.free_cash_flow and price.market_cap:
        out["fcf_yield_pct"] = round(100 * cf.free_cash_flow / price.market_cap, 2)

    # leva finanziaria
    if bal and bal.total_debt is not None and bal.total_equity:
        out["debt_to_equity"] = round(bal.total_debt / bal.total_equity, 2)

    # margine di sicurezza GREZZO: FCF capitalizzato a un tasso prudente (10%)
    # come proxy di fair value, confrontato col market cap.
    if cf and cf.free_cash_flow and price.market_cap:
        fair_value = cf.free_cash_flow / 0.10  # perpetuity senza crescita
        out["rough_fair_value"] = round(fair_value, 0)
        out["margin_of_safety_pct"] = round(
            100 * (fair_value - price.market_cap) / fair_value, 1
        )
        out["_note"] = (
            "margin_of_safety è una stima grezza (FCF/10%); "
            "usa la skill dcf-model per la valutazione seria"
        )
    return out
