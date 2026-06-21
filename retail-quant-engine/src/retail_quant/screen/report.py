"""Costruisce il report di screening in Markdown (deterministico) e, in modo
OPZIONALE, un breve commento dell'IA sulla sola lista corta.
"""
from __future__ import annotations

import json

from ..config import Settings
from .screener import ScreenRow, shortlist

# colonne mostrate per lente (chiave metrica -> intestazione)
_LENS_COLUMNS = {
    "value": [("pe_ratio", "P/E"), ("fcf_yield_pct", "FCF yield %"), ("debt_to_equity", "Debt/Eq")],
    "growth": [("revenue_cagr_pct", "Ricavi CAGR %"), ("net_income_cagr_pct", "Utili CAGR %"), ("operating_margin_change_pp", "Δ Margine pp")],
    "dividends": [("dividend_yield_pct", "Yield %"), ("payout_ratio_pct", "Payout %"), ("fcf_coverage_x", "Cop. FCF x")],
    "trading": [("change_3m_pct", "3m %"), ("change_1m_pct", "1m %"), ("above_sma50", "> SMA50")],
}


def build_markdown(rows: list[ScreenRow], lens: str, settings: Settings) -> str:
    cols = _LENS_COLUMNS.get(lens, [])
    header = "| # | Ticker | Pass | Score | " + " | ".join(h for _, h in cols) + " |"
    sep = "|---|--------|------|-------|" + "|".join("---" for _ in cols) + "|"
    lines = [f"# Screening — lente: {lens}", "", header, sep]
    for i, r in enumerate(rows, 1):
        if r.error:
            cells = " | ".join("—" for _ in cols)
            lines.append(f"| {i} | {r.ticker} | ⚠️ | — | {cells} |  ")
            continue
        vals = " | ".join(_fmt(r.metrics.get(k)) for k, _ in cols)
        flag = "✅" if r.passes else "—"
        lines.append(f"| {i} | {r.ticker} | {flag} | {r.score} | {vals} |")

    short = shortlist(rows)
    lines.append("")
    if short:
        lines.append(f"## Lista corta ({len(short)} che passano i criteri)")
        for r in short:
            lines.append(f"- **{r.ticker}** (score {r.score}): " + "; ".join(r.reasons))
    else:
        lines.append("## Lista corta")
        lines.append("- Nessun titolo passa tutti i criteri della lente.")

    errs = [r for r in rows if r.error]
    if errs:
        lines.append("\n## Errori")
        lines.extend(f"- {r.ticker}: {r.error}" for r in errs)
    return "\n".join(lines)


def _fmt(v) -> str:
    if v is None:
        return "n/d"
    if isinstance(v, bool):
        return "sì" if v else "no"
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return str(v)


def llm_comment(rows: list[ScreenRow], lens: str, settings: Settings, llm=None) -> str:
    """OPZIONALE: un solo giro di IA per commentare la lista corta.
    `llm` iniettabile per i test; in produzione usa l'orchestratore su NVIDIA."""
    short = shortlist(rows)
    if not short:
        return "_(nessun candidato in lista corta da commentare)_"
    if llm is None:
        from ..llm import orchestrator_llm

        llm = orchestrator_llm(settings)

    from langchain_core.messages import HumanMessage, SystemMessage

    payload = [{"ticker": r.ticker, "score": r.score, "metrics": r.metrics} for r in short]
    messages = [
        SystemMessage(
            content=(
                "You are a financial analyst helping a RETAIL investor. You are given a "
                "SHORTLIST of stocks that passed a screen, with their metrics. In English, "
                "briefly rank them and explain in 1-2 lines each why it stands out. Use ONLY "
                "the numbers provided; do not invent. This is analysis, not advice."
            )
        ),
        HumanMessage(content="Shortlist (JSON):\n\n" + json.dumps(payload, default=str, indent=2)),
    ]
    out = llm.invoke(messages)
    return getattr(out, "content", str(out))
