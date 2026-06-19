"""CLI Fase 1 — analisi completa di un titolo (usa NVIDIA):

    python -m retail_quant.agent.run AAPL

Richiede NVIDIA_API_KEY nel .env. La lente è quella in RQE_LENS.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from ..config import Settings
from .graph import build_graph, initial_state

# le analisi vengono salvate qui (cartella accanto al package, gitignorabile)
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main(ticker: str) -> None:
    settings = Settings.load()  # qui serve davvero la chiave NVIDIA
    graph = build_graph(settings)
    final = graph.invoke(initial_state(ticker, settings.lens))

    report = final["report"]
    print(report)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"{ticker.upper()}-{settings.lens}-{date.today().isoformat()}.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m retail_quant.agent.run <TICKER>")
        raise SystemExit(1)
    main(sys.argv[1])
