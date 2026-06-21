"""Regole di alert (deterministiche). Confrontano l'istantanea precedente con
quella attuale e segnalano SOLO ciò che richiede attenzione.
"""
from __future__ import annotations

from dataclasses import dataclass

# soglie tarabili
PRICE_MOVE_PCT = 10.0       # scostamento prezzo dall'ultimo controllo
POSITION_LOSS_PCT = -20.0   # perdita sulla posizione vs prezzo di carico


@dataclass
class Alert:
    ticker: str
    level: str   # "info" | "warn"
    message: str


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def evaluate(ticker: str, cost_basis: float, prev: dict | None, cur: dict, lens: str) -> list[Alert]:
    alerts: list[Alert] = []
    cur_price = _num(cur.get("price"))

    # 1) Profitto/perdita sulla posizione (sempre informativo; warn se sotto soglia)
    if cur_price is not None and cost_basis:
        pl = (cur_price - cost_basis) / cost_basis * 100
        level = "warn" if pl <= POSITION_LOSS_PCT else "info"
        alerts.append(Alert(ticker, level, f"P/L posizione: {pl:+.1f}% (carico {cost_basis:.2f}, ora {cur_price:.2f})"))

    # le regole sotto richiedono un controllo precedente con cui confrontare
    if prev:
        # 2) Scostamento di prezzo dall'ultimo controllo
        prev_price = _num(prev.get("price"))
        if cur_price is not None and prev_price:
            move = (cur_price - prev_price) / prev_price * 100
            if abs(move) >= PRICE_MOVE_PCT:
                alerts.append(Alert(ticker, "warn", f"Prezzo {move:+.1f}% dall'ultimo controllo ({prev_price:.2f} → {cur_price:.2f})"))

        # 3) Nuova trimestrale/annuale pubblicata
        prev_fy = _num(prev.get("fiscal_year"))
        cur_fy = _num(cur.get("fiscal_year"))
        if prev_fy and cur_fy and cur_fy > prev_fy:
            alerts.append(Alert(ticker, "warn", f"Nuovi dati di bilancio pubblicati (FY{int(cur_fy)})"))

        # 4) Lente value: margine di sicurezza passato da positivo a negativo
        if lens == "value":
            prev_mos = _num(prev.get("margin_of_safety_pct"))
            cur_mos = _num(cur.get("margin_of_safety_pct"))
            if prev_mos is not None and cur_mos is not None and prev_mos > 0 >= cur_mos:
                alerts.append(Alert(ticker, "warn", "Margine di sicurezza sparito (era positivo, ora ≤ 0)"))

    return alerts
