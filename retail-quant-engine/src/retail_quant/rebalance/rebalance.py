"""Ribilanciamento verso i pesi obiettivo (`target_pct` sugli holding).

Due modalità:
  - piena (new_cash=0): per ogni titolo calcola la differenza tra valore
    obiettivo e valore attuale -> comprare o vendere.
  - con nuova liquidità (new_cash>0): SOLO acquisti, distribuiti sui titoli
    sottopeso in proporzione al loro scostamento (riallineare versando, non
    vendendo: più efficiente fiscalmente per un PAC).

Deterministico (prezzi yfinance). Valuta unica assunta; se mista, i totali sono
nominali senza FX (il report lo segnala).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..data import providers
from ..monitor.portfolio import Holding


@dataclass
class RebalanceRow:
    ticker: str
    currency: str = "?"
    market_value: float = 0.0
    current_pct: float | None = None
    target_pct: float | None = None
    trade_value: float = 0.0          # + compra / - vendi
    trade_shares: float | None = None
    action: str = "-"
    error: str | None = None


def rebalance(holdings: list[Holding], settings: Settings, new_cash: float = 0.0) -> dict:
    base = settings.base_currency
    rows: list[RebalanceRow] = []
    prices: dict[str, float] = {}  # prezzo per quota nella valuta base
    warnings: list[str] = []

    for h in holdings:
        try:
            p = providers.get_price(h.ticker)
            try:
                rate = providers.get_fx_rate(p.currency, base)
            except Exception:  # noqa: BLE001
                rate = 1.0
                warnings.append(f"Cambio {p.currency}->{base} non disponibile: valore nominale.")
            price_base = p.price * rate
            prices[h.ticker] = price_base
            rows.append(RebalanceRow(
                ticker=h.ticker, currency=p.currency,
                market_value=round(h.shares * price_base, 2),
                target_pct=h.target_pct,
            ))
        except Exception as exc:  # noqa: BLE001
            rows.append(RebalanceRow(ticker=h.ticker, error=f"{type(exc).__name__}: {exc}"))

    valid = [r for r in rows if r.error is None]
    if any(r.target_pct is None for r in valid):
        warnings.append("Manca target_pct su uno o più titoli: aggiungilo nel portfolio.json.")
        return {"rows": rows, "warnings": sorted(set(warnings)), "new_cash": new_cash, "base_currency": base}

    total_market = sum(r.market_value for r in valid)
    target_sum = sum(r.target_pct for r in valid)
    if abs(target_sum - 100) > 0.5:
        warnings.append(f"I pesi obiettivo sommano a {target_sum:.1f}% (atteso 100%).")

    for r in valid:
        r.current_pct = round(100 * r.market_value / total_market, 2) if total_market else None

    patrimonio = total_market + new_cash  # totale dopo il versamento (in valuta base)
    if new_cash > 0:
        # solo acquisti: distribuisci la liquidità sui sottopeso
        shortfalls = {r.ticker: max(0.0, (r.target_pct / 100) * patrimonio - r.market_value) for r in valid}
        total_short = sum(shortfalls.values())
        for r in valid:
            share = shortfalls[r.ticker] / total_short if total_short else r.target_pct / 100
            r.trade_value = round(new_cash * share, 2)
            r.action = "Compra" if r.trade_value > 0 else "-"
    else:
        for r in valid:
            r.trade_value = round((r.target_pct / 100) * patrimonio - r.market_value, 2)
            r.action = "Compra" if r.trade_value > 0.005 else "Vendi" if r.trade_value < -0.005 else "-"

    for r in valid:
        px = prices.get(r.ticker)
        if px:
            r.trade_shares = round(r.trade_value / px, 4)

    return {
        "rows": rows,
        "warnings": sorted(set(warnings)),
        "new_cash": new_cash,
        "base_currency": base,
        "total_market": round(total_market, 2),
    }


def build_markdown(result: dict) -> str:
    base = result.get("base_currency", "")
    lines = [f"# Ribilanciamento (in {base})", ""]
    if result["new_cash"]:
        lines.append(f"**Nuova liquidità da versare:** {result['new_cash']} {base} (solo acquisti)")
    else:
        lines.append("**Modalità:** ribilanciamento pieno (compra/vendi)")
    for w in result["warnings"]:
        lines.append(f"\n> ⚠️ {w}")
    lines.append("")
    lines.append("| Titolo | Attuale % | Obiettivo % | Azione | Importo | ~Quote |")
    lines.append("|---|---|---|---|---|---|")
    for r in result["rows"]:
        if r.error:
            lines.append(f"| **{r.ticker}** | - | - | errore | - | - |")
            continue
        cur = "-" if r.current_pct is None else f"{r.current_pct}%"
        tgt = "-" if r.target_pct is None else f"{r.target_pct}%"
        sh = "-" if r.trade_shares is None else f"{r.trade_shares:+g}"
        lines.append(f"| **{r.ticker}** | {cur} | {tgt} | {r.action} | {r.trade_value:+.2f} | {sh} |")
    return "\n".join(lines)
