"""Proiezione di un PAC (Piano di Accumulo): si versa un importo fisso ogni mese
a interesse composto. Calcolo trasparente con un ciclo mensile.

Convenzioni: il rendimento annuo si compone su base mensile con il tasso
equivalente i = (1+r)^(1/12) - 1 (12 mesi -> esattamente r). Il versamento è a
fine mese. Tutto NOMINALE; con l'inflazione si mostra anche il valore reale
(potere d'acquisto di oggi). Nessuna tassa/commissione considerata.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class YearRow:
    year: int
    value: float
    contributed: float
    gains: float


@dataclass
class ProjectionResult:
    monthly: float
    annual_return_pct: float
    years: int
    initial: float
    final: float
    total_contributed: float
    gains: float
    inflation_pct: float = 0.0
    final_real: float | None = None
    rows: list[YearRow] = field(default_factory=list)


def project(monthly: float, annual_return_pct: float, years: int,
            initial: float = 0.0, inflation_pct: float = 0.0) -> ProjectionResult:
    if years <= 0 or monthly < 0:
        raise ValueError("years deve essere > 0 e monthly >= 0")

    i = (1 + annual_return_pct / 100) ** (1 / 12) - 1
    value = initial
    rows: list[YearRow] = []
    months = years * 12
    for m in range(1, months + 1):
        value = value * (1 + i) + monthly
        if m % 12 == 0:
            contributed = initial + monthly * m
            rows.append(YearRow(m // 12, round(value, 2),
                                round(contributed, 2), round(value - contributed, 2)))

    total_contributed = initial + monthly * months
    final = round(value, 2)
    res = ProjectionResult(
        monthly=monthly, annual_return_pct=annual_return_pct, years=years, initial=initial,
        final=final, total_contributed=round(total_contributed, 2),
        gains=round(final - total_contributed, 2),
        inflation_pct=inflation_pct, rows=rows,
    )
    if inflation_pct:
        res.final_real = round(final / (1 + inflation_pct / 100) ** years, 2)
    return res


def build_markdown(r: ProjectionResult, currency: str = "EUR") -> str:
    lines = [
        "# Proiezione PAC", "",
        f"**Ipotesi:** {r.monthly:g} {currency}/mese · rendimento {r.annual_return_pct:g}%/anno · "
        f"{r.years} anni" + (f" · capitale iniziale {r.initial:g} {currency}" if r.initial else ""),
        "",
        f"- **Capitale finale:** {r.final:,.2f} {currency}",
        f"- Totale versato: {r.total_contributed:,.2f} {currency}",
        f"- Interessi (guadagno): {r.gains:,.2f} {currency} "
        f"({100 * r.gains / r.total_contributed:+.1f}% sul versato)"
        if r.total_contributed else "",
    ]
    if r.final_real is not None:
        lines.append(f"- Valore reale (inflazione {r.inflation_pct:g}%): {r.final_real:,.2f} "
                     f"{currency} in potere d'acquisto di oggi")
    lines += ["", "| Anno | Valore | Versato | Interessi |", "|---|---|---|---|"]
    for row in r.rows:
        lines.append(f"| {row.year} | {row.value:,.2f} | {row.contributed:,.2f} | {row.gains:,.2f} |")
    lines.append("\n_Proiezione a rendimento costante: la realtà oscilla. Stima, non promessa._")
    return "\n".join(lines)
