"""Proiezione di un PAC (Piano di Accumulo) a interesse composto.

Supporta versamenti a FASI: es. 200/mese per 5 anni, poi 400/mese per 10 anni.
Il caso a versamento costante è una sola fase.

Convenzioni: il rendimento annuo si compone su base mensile col tasso
equivalente i = (1+r)^(1/12) - 1 (12 mesi -> esattamente r). Versamento a fine
mese. Tutto NOMINALE; con l'inflazione si mostra anche il valore reale. Nessuna
tassa/commissione considerata.
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
    steps: list[tuple[int, float]]  # [(anni, versamento_mensile), ...]
    annual_return_pct: float
    years: int
    initial: float
    final: float
    total_contributed: float
    gains: float
    inflation_pct: float = 0.0
    final_real: float | None = None
    rows: list[YearRow] = field(default_factory=list)


def project_steps(steps, annual_return_pct: float,
                  initial: float = 0.0, inflation_pct: float = 0.0) -> ProjectionResult:
    steps = [(int(y), float(m)) for y, m in steps]
    if not steps or any(y <= 0 or m < 0 for y, m in steps):
        raise ValueError("ogni fase deve avere anni > 0 e versamento >= 0")

    i = (1 + annual_return_pct / 100) ** (1 / 12) - 1
    value = initial
    contributed = initial
    rows: list[YearRow] = []
    month = 0
    for seg_years, monthly in steps:
        for _ in range(seg_years * 12):
            value = value * (1 + i) + monthly
            contributed += monthly
            month += 1
            if month % 12 == 0:
                rows.append(YearRow(month // 12, round(value, 2),
                                    round(contributed, 2), round(value - contributed, 2)))

    years = sum(y for y, _ in steps)
    final = round(value, 2)
    res = ProjectionResult(
        steps=steps, annual_return_pct=annual_return_pct, years=years, initial=initial,
        final=final, total_contributed=round(contributed, 2),
        gains=round(final - contributed, 2), inflation_pct=inflation_pct, rows=rows,
    )
    if inflation_pct:
        res.final_real = round(final / (1 + inflation_pct / 100) ** years, 2)
    return res


def project(monthly: float, annual_return_pct: float, years: int,
            initial: float = 0.0, inflation_pct: float = 0.0) -> ProjectionResult:
    """Caso a versamento costante: una sola fase."""
    return project_steps([(years, monthly)], annual_return_pct, initial, inflation_pct)


def _schedule_text(steps: list[tuple[int, float]], currency: str) -> str:
    return " poi ".join(f"{m:g} {currency}/mese per {y} anni" for y, m in steps)


def build_markdown(r: ProjectionResult, currency: str = "EUR") -> str:
    lines = [
        "# Proiezione PAC", "",
        f"**Ipotesi:** {_schedule_text(r.steps, currency)} · rendimento "
        f"{r.annual_return_pct:g}%/anno · {r.years} anni totali"
        + (f" · capitale iniziale {r.initial:g} {currency}" if r.initial else ""),
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
