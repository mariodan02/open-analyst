"""Test end-to-end della Fase 1 SENZA chiave NVIDIA.

Inietta uno stub al posto del modello: verifica che il grafo
fetch -> metrics -> thesis -> validate giri su dati reali e assembli il report.
Esegui:  python tests/test_phase1.py
"""
from __future__ import annotations

from langchain_core.messages import AIMessage

from retail_quant.agent.graph import build_graph, initial_state
from retail_quant.config import Settings


class StubLLM:
    """Finto modello: ignora i messaggi e restituisce una tesi fissa.
    Verifica anche che riceva davvero il blocco dati col ticker."""

    def __init__(self):
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return AIMessage(content="TESI DI PROVA: l'azienda mostra numeri solidi.")


def test_graph_runs_end_to_end():
    settings = Settings.load(require_llm=False)  # niente chiave NVIDIA
    stub = StubLLM()
    graph = build_graph(settings, llm=stub)

    final = graph.invoke(initial_state("AAPL", "value"))

    # 1. il nodo thesis ha ricevuto il blocco dati con il ticker
    human = stub.last_messages[-1].content
    assert "AAPL" in human, "il blocco dati non contiene il ticker"

    # 2. il report finale è assemblato e contiene tesi + provenienza
    report = final["report"]
    assert "TESI DI PROVA" in report, "la tesi dello stub non è nel report"
    assert "Provenienza dati" in report, "manca la sezione provenienza"
    assert "AAPL" in report

    # 3. i dati reali sono stati presi
    assert final.get("price") is not None, "prezzo non recuperato"
    assert final.get("metrics"), "metriche non calcolate"

    print("REPORT GENERATO\n" + "=" * 60)
    print(report)
    print("=" * 60)
    print("\nlast errors:", final.get("errors"))
    print("metrics:", final.get("metrics"))


if __name__ == "__main__":
    test_graph_runs_end_to_end()
    print("\n✅ test_phase1: PASSATO")
