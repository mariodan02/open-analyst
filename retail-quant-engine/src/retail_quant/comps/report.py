"""Report comps in Markdown (deterministico)."""
from __future__ import annotations

_LABELS = {
    "pe": "P/E",
    "ps": "P/S",
    "gross_margin_pct": "Margine lordo %",
    "operating_margin_pct": "Margine operativo %",
}


def _fmt(v) -> str:
    return "-" if v is None else f"{v}"


def build_markdown(result: dict) -> str:
    target = result["target"]
    lines = [f"# Comps — {target} vs pari", ""]
    lines.append(f"**Verdetto:** {result['verdict']}")
    lines.append("")

    # tabella multipli
    lines.append("| Ticker | P/E | P/S | Margine lordo % | Margine op. % |")
    lines.append("|---|---|---|---|---|")
    for r in result["rows"]:
        flag = " ⟵ target" if r.ticker == target else ""
        if r.error:
            lines.append(f"| **{r.ticker}**{flag} | errore | - | - | - |")
            continue
        lines.append(
            f"| **{r.ticker}**{flag} | {_fmt(r.pe)} | {_fmt(r.ps)} | "
            f"{_fmt(r.gross_margin_pct)} | {_fmt(r.operating_margin_pct)} |"
        )

    med = result["peer_medians"]
    if med:
        lines.append(
            f"| _mediana pari_ | {_fmt(med.get('pe'))} | {_fmt(med.get('ps'))} | "
            f"{_fmt(med.get('gross_margin_pct'))} | {_fmt(med.get('operating_margin_pct'))} |"
        )

    rel = result["relative"]
    if rel:
        lines.append("\n## Target vs mediana pari")
        for field, d in rel.items():
            lines.append(
                f"- **{_LABELS.get(field, field)}**: {d['target']} vs {d['peer_median']} "
                f"({d['diff_pct']:+.1f}%)"
            )
    return "\n".join(lines)
