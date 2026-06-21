"""CLI returns — performance del portafoglio:

    python -m retail_quant.returns.run --file portfolio.json

Niente LLM: solo prezzi e aritmetica.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from ..monitor.portfolio import load_portfolio
from . import returns

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main() -> None:
    ap = argparse.ArgumentParser(description="Performance del portafoglio.")
    ap.add_argument("--file", default="portfolio.json", help="file del portafoglio (JSON)")
    args = ap.parse_args()

    settings = Settings.load(require_llm=False)
    holdings = load_portfolio(args.file)
    result = returns.analyze(holdings, settings)
    md = returns.build_markdown(result)
    print(md)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"returns-{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    main()
