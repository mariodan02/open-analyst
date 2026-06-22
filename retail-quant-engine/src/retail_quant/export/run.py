"""CLI export — posizioni + P/L in CSV:

    python -m retail_quant.export.run --file portfolio.json

Salva reports/portfolio-<data>.csv (apribile in Excel/LibreOffice).
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from ..monitor.portfolio import load_portfolio
from . import csv_export

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main() -> None:
    ap = argparse.ArgumentParser(description="Esporta il portafoglio in CSV.")
    ap.add_argument("--file", default="portfolio.json", help="file del portafoglio (JSON)")
    ap.add_argument("--out", default=None, help="percorso CSV di output")
    args = ap.parse_args()

    settings = Settings.load(require_llm=False)
    holdings = load_portfolio(args.file)
    out = Path(args.out) if args.out else REPORTS_DIR / f"portfolio-{date.today().isoformat()}.csv"
    csv_export.write_csv(holdings, settings, out)
    print(f"[CSV salvato: {out}]")


if __name__ == "__main__":
    main()
