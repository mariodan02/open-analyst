"""Lente VALUE: aziende solide sottovalutate (Buffett/Graham).

Metriche: P/E, FCF yield, debito/equity, e un margine di sicurezza GREZZO
basato su un DCF semplificato. NB: il margine di sicurezza lo fa la
skill dcf-model del fork (script Python) — qui è un primo segnale, non oro colato.
"""
from __future__ import annotations

from ..data.schemas import FinancialHistory, PriceSnapshot
from ..valuation.dcf import intrinsic_value


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

    # leva finanziaria. Solo con patrimonio netto POSITIVO: con equity ≤ 0 il
    # rapporto diventa negativo e sembrerebbe "poca leva" mentre è il contrario
    # (azienda molto tirata) -> meglio non calcolarlo (n/d).
    if bal and bal.total_debt is not None and bal.total_equity and bal.total_equity > 0:
        out["debt_to_equity"] = round(bal.total_debt / bal.total_equity, 2)

    # margine di sicurezza: DCF (metodologia skill dcf-model del fork).
    # Restituisce None se i dati non bastano (es. FCF negativo) -> niente MoS finto.
    dcf = intrinsic_value(price, fin)
    if dcf:
        out["intrinsic_per_share"] = dcf["intrinsic_per_share"]
        out["margin_of_safety_pct"] = dcf["margin_of_safety_pct"]
        out["wacc_pct"] = dcf["wacc_pct"]
        out["_valuation_method"] = dcf["_method"]
    return out
