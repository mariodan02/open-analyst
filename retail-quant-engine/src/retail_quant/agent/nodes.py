"""I quattro nodi del grafo. Solo `thesis` usa l'LLM; gli altri sono
deterministici (e quindi testabili senza chiave NVIDIA).
"""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import Settings
from ..data import providers
from ..metrics import compute as compute_metrics
from .prompts import RETAIL_ANALYST_SYSTEM
from .state import AnalysisState


# --------------------------------------------------------------------------- #
# 1. FETCH — dati grezzi (deterministico). Gli errori non fanno crashare il
#    grafo: vengono raccolti in state["errors"].
# --------------------------------------------------------------------------- #
def make_fetch(settings: Settings):
    def fetch(state: AnalysisState) -> dict:
        ticker = state["ticker"]
        errors: list[str] = []
        price = financials = None
        news: list = []
        try:
            price = providers.get_price(ticker)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"price: {exc}")
        try:
            financials = providers.get_financials(ticker, settings)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"financials: {exc}")
        try:
            news = providers.get_news(ticker)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"news: {exc}")
        return {"price": price, "financials": financials, "news": news, "errors": errors}

    return fetch


# --------------------------------------------------------------------------- #
# 2. METRICS — applica la lente attiva (deterministico).
# --------------------------------------------------------------------------- #
def make_metrics(settings: Settings):
    def metrics(state: AnalysisState) -> dict:
        price = state.get("price")
        fin = state.get("financials")
        if not price or not fin:
            return {"metrics": {}, "warnings": ["Dati insufficienti per le metriche."]}
        return {"metrics": compute_metrics(state["lens"], price, fin)}

    return metrics


# --------------------------------------------------------------------------- #
# 3. THESIS — l'unico nodo con LLM. Riceve SOLO i dati raccolti e scrive la tesi.
# --------------------------------------------------------------------------- #
def make_thesis(llm):
    def thesis(state: AnalysisState) -> dict:
        price = state.get("price")
        fin = state.get("financials")
        ctx = {
            "ticker": state["ticker"],
            "lens": state["lens"],
            "price": price.model_dump() if price else None,
            "metrics": state.get("metrics", {}),
            "financials_years": len(fin.income) if fin else 0,
            "news_headlines": [n.title for n in state.get("news", [])][:5],
        }
        messages = [
            SystemMessage(content=RETAIL_ANALYST_SYSTEM),
            HumanMessage(
                content=(
                    "Blocco dati (JSON). Usa SOLO questi numeri:\n\n"
                    + json.dumps(ctx, default=str, indent=2)
                )
            ),
        ]
        out = llm.invoke(messages)
        return {"thesis": getattr(out, "content", str(out))}

    return thesis


# --------------------------------------------------------------------------- #
# 4. VALIDATE — provenienza dati + warning (deterministico). Niente parsing
#    fragile dei numeri: costruiamo la tracciabilità da ciò che ABBIAMO preso.
# --------------------------------------------------------------------------- #
def make_validate():
    def validate(state: AnalysisState) -> dict:
        warnings = list(state.get("warnings", []))
        prov: list[str] = []

        price = state.get("price")
        if price:
            prov.append(f"- Prezzo / market cap: fonte `{price.source}`")
        fin = state.get("financials")
        if fin and fin.income:
            prov.append(f"- Bilanci: fonte `{fin.income[0].source}` ({len(fin.income)} anni)")
        if state.get("news"):
            prov.append(f"- Notizie: {len(state['news'])} headline (yfinance)")

        # warning specifici per lente quando mancano dati chiave
        m = state.get("metrics", {})
        lens = state["lens"]
        if lens == "value" and "fcf_yield_pct" not in m:
            warnings.append(
                "FCF/debito non disponibili (fallback yfinance) — aggiungi FMP_API_KEY "
                "per margine di sicurezza e leva."
            )
        if lens == "dividends" and "dividend_yield_pct" not in m:
            warnings.append("Dati dividendi non disponibili senza FMP_API_KEY.")

        report = _assemble(state, prov, warnings)
        return {"report": report, "warnings": warnings}

    return validate


def _assemble(state: AnalysisState, prov: list[str], warnings: list[str]) -> str:
    parts = [f"# Analisi {state['ticker']} — lente: {state['lens']}", ""]
    parts.append(state.get("thesis", "(nessuna tesi generata)"))
    parts.append("\n---\n## Provenienza dati")
    parts.extend(prov or ["- (nessun dato recuperato)"])
    if warnings:
        parts.append("\n## Avvertenze")
        parts.extend(f"- {w}" for w in warnings)
    if state.get("errors"):
        parts.append("\n## Errori di fetch")
        parts.extend(f"- {e}" for e in state["errors"])
    return "\n".join(parts)
