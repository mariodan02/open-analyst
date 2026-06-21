"""Report di monitoraggio in Markdown (deterministico)."""
from __future__ import annotations

from .monitor import MonitorResult


def build_markdown(results: list[MonitorResult], lens: str, first_run: bool) -> str:
    lines = [f"# Monitoraggio portafoglio — lente: {lens}", ""]

    if first_run:
        lines.append(
            "> Primo controllo: registro lo stato di partenza. Gli alert sui "
            "*cambiamenti* (prezzo, nuove trimestrali) compariranno dai prossimi giri.\n"
        )

    warns = [a for r in results for a in r.alerts if a.level == "warn"]
    if warns:
        lines.append("## ⚠️ Da guardare")
        lines.extend(f"- **{a.ticker}**: {a.message}" for a in warns)
        lines.append("")

    lines.append("## Tutti i titoli")
    for r in results:
        if r.error:
            lines.append(f"- **{r.ticker}**: ⚠️ errore — {r.error}")
            continue
        price = r.snapshot.get("price")
        head = f"- **{r.ticker}** (prezzo {price})"
        infos = [a.message for a in r.alerts]
        if infos:
            lines.append(head + ": " + "; ".join(infos))
        else:
            lines.append(head + ": nessuna novità")

    errs = [r for r in results if r.error]
    if errs:
        lines.append(f"\n_({len(errs)} titoli con errore di fetch — stato precedente mantenuto)_")
    return "\n".join(lines)
