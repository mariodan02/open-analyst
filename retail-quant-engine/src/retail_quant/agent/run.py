"""CLI Fase 1 — analisi completa di un titolo (usa NVIDIA):

    python -m retail_quant.agent.run AAPL
    python -m retail_quant.agent.run VWCE.MI --isin IE00BK5BQT80   # ETF

Richiede NVIDIA_API_KEY nel .env. La lente è quella in RQE_LENS. Per gli ETF
l'--isin (opzionale) abilita il profilo justETF (TER, politica dividendi).
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from .graph import build_graph, initial_state

# le analisi vengono salvate qui (cartella accanto al package, gitignorabile)
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main(ticker: str, isin: str | None = None) -> None:
    settings = Settings.load()  # qui serve davvero la chiave NVIDIA
    graph = build_graph(settings)
    final = graph.invoke(initial_state(ticker, settings.lens, isin))

    report = final["report"]
    print(report)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"{ticker.upper()}-{settings.lens}-{date.today().isoformat()}.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Analisi Fase 1 di un titolo o ETF.")
    ap.add_argument("ticker")
    ap.add_argument("--isin", default=None, help="ISIN dell'ETF (abilita justETF)")
    args = ap.parse_args()
    main(args.ticker, args.isin)
