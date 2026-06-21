"""Performance del portafoglio: per ogni titolo valore di carico vs di mercato,
P/L e peso; in fondo i totali e il contributo di ciascuno al rendimento.

Deterministico (solo prezzi yfinance). I prezzi sono nella valuta di quotazione
del titolo: se il portafoglio mescola valute, i totali sono una somma nominale
SENZA conversione FX — il report lo segnala.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..data import providers
from ..monitor.portfolio import Holding


@dataclass
class HoldingReturn:
    ticker: str
    currency: str = "?"
    cost_value: float = 0.0
    market_value: float = 0.0
    pl_abs: float = 0.0
    pl_pct: float | None = None
    weight_pct: float | None = None
    contribution_pct: float | None = None  # contributo al rendimento totale
    error: str | None = None


def analyze(holdings: list[Holding], settings: Settings) -> dict:
    base = settings.base_currency
    warnings: list[str] = []
    rows: list[HoldingReturn] = []
    for h in holdings:
        try:
            price = providers.get_price(h.ticker)
            rate, note = _fx(price.currency, base)
            if note:
                warnings.append(note)
            cost_value = h.shares * h.cost_basis * rate
            market_value = h.shares * price.price * rate
            pl_abs = market_value - cost_value
            rows.append(HoldingReturn(
                ticker=h.ticker,
                currency=price.currency,  # valuta di quotazione (i valori sono in base)
                cost_value=round(cost_value, 2),
                market_value=round(market_value, 2),
                pl_abs=round(pl_abs, 2),
                pl_pct=round(100 * pl_abs / cost_value, 2) if cost_value else None,
            ))
        except Exception as exc:  # noqa: BLE001 - isola il singolo titolo
            rows.append(HoldingReturn(ticker=h.ticker, error=f"{type(exc).__name__}: {exc}"))

    valid = [r for r in rows if r.error is None]
    total_cost = sum(r.cost_value for r in valid)
    total_market = sum(r.market_value for r in valid)
    for r in valid:
        if total_market:
            r.weight_pct = round(100 * r.market_value / total_market, 2)
        if total_cost:
            r.contribution_pct = round(100 * r.pl_abs / total_cost, 2)

    return {
        "rows": rows,
        "base_currency": base,
        "total_cost": round(total_cost, 2),
        "total_market": round(total_market, 2),
        "total_pl_abs": round(total_market - total_cost, 2),
        "total_pl_pct": round(100 * (total_market - total_cost) / total_cost, 2) if total_cost else None,
        "warnings": sorted(set(warnings)),
    }


def _fx(currency: str, base: str) -> tuple[float, str | None]:
    """Tasso valuta->base. Se il cambio non è disponibile, 1.0 + avviso."""
    try:
        return providers.get_fx_rate(currency, base), None
    except Exception:  # noqa: BLE001
        return 1.0, f"Cambio {currency}->{base} non disponibile: {currency} contato a valore nominale."


def build_markdown(result: dict) -> str:
    base = result["base_currency"]
    lines = [f"# Performance del portafoglio (in {base})", ""]
    tot_pl = result["total_pl_pct"]
    lines.append(
        f"**Totale:** carico {result['total_cost']} → mercato {result['total_market']} {base} "
        f"(**{tot_pl:+.2f}%**, {result['total_pl_abs']:+.2f})"
        if tot_pl is not None else "**Totale:** dati insufficienti."
    )
    for w in result.get("warnings", []):
        lines.append(f"\n> ⚠️ {w}")
    lines.append("")
    lines.append(f"| Titolo | Quotaz. | Carico ({base}) | Mercato ({base}) | P/L | P/L % | Peso % |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in result["rows"]:
        if r.error:
            lines.append(f"| **{r.ticker}** | - | - | - | errore | - | - |")
            continue
        lines.append(
            f"| **{r.ticker}** | {r.currency} | {r.cost_value} | {r.market_value} | "
            f"{r.pl_abs:+.2f} | {r.pl_pct:+.2f}% | {r.weight_pct}% |"
        )
    return "\n".join(lines)
