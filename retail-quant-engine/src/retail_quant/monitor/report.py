"""Report di monitoraggio in Markdown (deterministico)."""
from __future__ import annotations

from ..data.schemas import ETF_LIKE
from .monitor import MonitorResult


def _head(r: MonitorResult) -> str:
    price = r.snapshot.get("price")
    if r.snapshot.get("asset_type") in ETF_LIKE:
        extras = []
        ter = r.snapshot.get("expense_ratio_pct")
        if ter is not None:
            extras.append(f"TER {ter}%")
        policy = (r.snapshot.get("distribution_policy") or "").lower()
        dy = r.snapshot.get("dividend_yield_pct")
        if "accumul" in policy:
            extras.append("accumulazione")
        elif dy is not None:
            extras.append(f"rendimento {dy}%")
        elif "distrib" in policy:
            extras.append("distribuzione")
        tag = "ETF" + (", " + ", ".join(extras) if extras else "")
        return f"- **{r.ticker}** (prezzo {price}) [{tag}]"
    return f"- **{r.ticker}** (prezzo {price})"


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
        head = _head(r)
        infos = [a.message for a in r.alerts]
        if infos:
            lines.append(head + ": " + "; ".join(infos))
        else:
            lines.append(head + ": nessuna novità")

    errs = [r for r in results if r.error]
    if errs:
        lines.append(f"\n_({len(errs)} titoli con errore di fetch — stato precedente mantenuto)_")
    return "\n".join(lines)
