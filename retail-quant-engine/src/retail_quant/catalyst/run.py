"""CLI catalyst — prossimi eventi del portafoglio:

    python -m retail_quant.catalyst.run --file portfolio.json --days 60

Niente LLM: solo il calendario yfinance.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from ..monitor.portfolio import load_portfolio
from . import catalyst

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main() -> None:
    ap = argparse.ArgumentParser(description="Calendario eventi del portafoglio.")
    ap.add_argument("--file", default="portfolio.json", help="file del portafoglio (JSON)")
    ap.add_argument("--days", type=int, default=90, help="orizzonte in giorni")
    args = ap.parse_args()

    settings = Settings.load(require_llm=False)
    holdings = load_portfolio(args.file)
    res = catalyst.upcoming(holdings, settings, horizon_days=args.days)
    md = catalyst.build_markdown(res, args.days)
    print(md)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"catalysts-{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    main()
