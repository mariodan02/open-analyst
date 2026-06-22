"""Composizione del grafo LangGraph: fetch -> metrics -> thesis -> validate.

`llm` è iniettabile: in produzione è il modello orchestratore su NVIDIA, nei
test si passa uno stub per esercitare il grafo senza chiave API.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from ..config import Settings
from ..llm import orchestrator_llm
from . import nodes
from .state import AnalysisState


def build_graph(settings: Settings, llm=None):
    llm = llm if llm is not None else orchestrator_llm(settings)

    g = StateGraph(AnalysisState)
    g.add_node("fetch", nodes.make_fetch(settings))
    g.add_node("metrics", nodes.make_metrics(settings))
    g.add_node("thesis", nodes.make_thesis(llm))
    g.add_node("validate", nodes.make_validate())

    g.set_entry_point("fetch")
    g.add_edge("fetch", "metrics")
    g.add_edge("metrics", "thesis")
    g.add_edge("thesis", "validate")
    g.add_edge("validate", END)
    return g.compile()


def initial_state(ticker: str, lens: str, isin: str | None = None) -> AnalysisState:
    return {
        "ticker": ticker.upper(),
        "lens": lens,
        "isin": isin.upper() if isin else None,
        "news": [],
        "warnings": [],
        "errors": [],
    }
