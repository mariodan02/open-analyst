"""Criteri di screening per lente (deterministici).

Ogni lente ha: una soglia di PASS (regole secche) e uno SCORE per ordinare i
candidati. Tutto trasparente e tarabile: niente magia, sono i tuoi soldi.

`evaluate(lens, metrics)` -> (passes: bool, score: float, reasons: list[str])
dove reasons spiega in chiaro perché un titolo passa o no.
"""
from __future__ import annotations

# Soglie tarabili. Cambia qui per rendere lo screening più/meno severo.
THRESHOLDS = {
    "value": {"pe_max": 25.0, "fcf_yield_min": 4.0, "de_max": 1.5},
    "growth": {"rev_cagr_min": 10.0, "ni_cagr_min": 8.0},
    "dividends": {"yield_min": 3.0, "payout_max": 80.0, "fcf_cov_min": 1.0},
    "trading": {"mom3m_min": 0.0},
}


def _check(label: str, ok: bool, value) -> tuple[str, bool, object]:
    return (label, ok, value)


def evaluate(lens: str, m: dict) -> tuple[bool, float, list[str]]:
    fn = _DISPATCH.get(lens)
    if fn is None:
        raise ValueError(f"Lente sconosciuta: {lens}")
    checks, score = fn(m)
    passes = all(c[1] for c in checks)
    reasons = [
        f"{'✓' if ok else '✗'} {label}"
        + (f" ({_fmt(val)})" if val is not None else " (n/d)")
        for label, ok, val in checks
    ]
    return passes, round(score, 2), reasons


def _fmt(v) -> str:
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return str(v)


# --------------------------------------------------------------------------- #
def _value(m: dict):
    t = THRESHOLDS["value"]
    pe = m.get("pe_ratio")
    fcfy = m.get("fcf_yield_pct")
    de = m.get("debt_to_equity")
    # P/E valido solo se POSITIVO: un P/E negativo = utili negativi = azienda in
    # perdita, NON un titolo "economico".
    pe_ok = pe is not None and 0 < pe < t["pe_max"]
    checks = [
        _check(f"P/E positivo e < {t['pe_max']}", pe_ok, pe),
        _check(f"FCF yield > {t['fcf_yield_min']}%", fcfy is not None and fcfy > t["fcf_yield_min"], fcfy),
        _check(f"Debt/Equity < {t['de_max']}", de is not None and de < t["de_max"], de),
    ]
    # più FCF yield è meglio; P/E e leva penalizzano. Un P/E non valido
    # (mancante o <= 0) viene penalizzato come fosse alto, non premiato.
    pe_for_score = pe if (pe is not None and pe > 0) else 50
    score = (fcfy or 0) * 5 - pe_for_score * 0.5 - (de if de is not None else 3) * 5
    return checks, score


def _growth(m: dict):
    t = THRESHOLDS["growth"]
    rev = m.get("revenue_cagr_pct")
    ni = m.get("net_income_cagr_pct")
    margin = m.get("operating_margin_change_pp")
    checks = [
        _check(f"Crescita ricavi > {t['rev_cagr_min']}%", rev is not None and rev > t["rev_cagr_min"], rev),
        _check(f"Crescita utili > {t['ni_cagr_min']}%", ni is not None and ni > t["ni_cagr_min"], ni),
    ]
    score = (rev or 0) + (ni or 0) + (margin or 0) * 2
    return checks, score


def _dividends(m: dict):
    t = THRESHOLDS["dividends"]
    dy = m.get("dividend_yield_pct")
    payout = m.get("payout_ratio_pct")
    cov = m.get("fcf_coverage_x")
    checks = [
        _check(f"Dividend yield > {t['yield_min']}%", dy is not None and dy > t["yield_min"], dy),
        _check(f"Payout < {t['payout_max']}%", payout is not None and payout < t["payout_max"], payout),
        _check(f"Copertura FCF > {t['fcf_cov_min']}x", cov is not None and cov > t["fcf_cov_min"], cov),
    ]
    # premia rendimento alto ma sostenibile (payout basso, buona copertura)
    score = (dy or 0) * 10 - (payout or 100) * 0.2 + (cov or 0) * 5
    return checks, score


def _trading(m: dict):
    t = THRESHOLDS["trading"]
    mom3 = m.get("change_3m_pct")
    above = m.get("above_sma50")
    checks = [
        _check("Momentum 3m > 0%", mom3 is not None and mom3 > t["mom3m_min"], mom3),
        _check("Sopra SMA50", bool(above), above),
    ]
    score = (mom3 or 0) + (10 if above else 0)
    return checks, score


_DISPATCH = {
    "value": _value,
    "growth": _growth,
    "dividends": _dividends,
    "trading": _trading,
}
