"""CLI rebalance — riallinea il portafoglio ai pesi obiettivo:

    python -m retail_quant.rebalance.run --file portfolio.json
    python -m retail_quant.rebalance.run --file portfolio.json --cash 500

Senza --cash: ribilanciamento pieno (compra/vendi). Con --cash: distribuisce
la nuova liquidità solo in acquisti sui titoli sottopeso. Niente LLM.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from ..monitor.portfolio import load_portfolio
from . import rebalance

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main() -> None:
    ap = argparse.ArgumentParser(description="Ribilanciamento del portafoglio.")
    ap.add_argument("--file", default="portfolio.json", help="file del portafoglio (JSON)")
    ap.add_argument("--cash", type=float, default=0.0, help="nuova liquidità da versare (solo acquisti)")
    args = ap.parse_args()

    settings = Settings.load(require_llm=False)
    holdings = load_portfolio(args.file)
    result = rebalance.rebalance(holdings, settings, new_cash=args.cash)
    md = rebalance.build_markdown(result)
    print(md)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"rebalance-{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    main()
