"""CLI proiezione PAC:

    python -m retail_quant.projection.run --monthly 200 --years 20 --return 6
    # parti dal valore attuale del portafoglio e considera l'inflazione:
    python -m retail_quant.projection.run --monthly 200 --years 20 --return 6 \\
        --file portfolio.json --inflation 2

Niente LLM: solo aritmetica.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from . import projection

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main() -> None:
    ap = argparse.ArgumentParser(description="Proiezione di un PAC a interesse composto.")
    ap.add_argument("--monthly", type=float, required=True, help="versamento mensile")
    ap.add_argument("--years", type=int, required=True, help="orizzonte in anni")
    ap.add_argument("--return", dest="annual_return", type=float, required=True,
                    help="rendimento annuo atteso, in %% (es. 6)")
    ap.add_argument("--initial", type=float, default=0.0, help="capitale iniziale")
    ap.add_argument("--inflation", type=float, default=0.0, help="inflazione annua in %% (per il valore reale)")
    ap.add_argument("--file", default=None,
                    help="se indicato, usa il valore di mercato attuale del portafoglio come capitale iniziale")
    args = ap.parse_args()

    settings = Settings.load(require_llm=False)
    initial = args.initial
    if args.file:
        from ..monitor.portfolio import load_portfolio
        from ..returns import returns
        rdata = returns.analyze(load_portfolio(args.file), settings)
        initial = rdata["total_market"]
        print(f"[capitale iniziale dal portafoglio: {initial:,.2f} {settings.base_currency}]")

    res = projection.project(args.monthly, args.annual_return, args.years,
                             initial=initial, inflation_pct=args.inflation)
    md = projection.build_markdown(res, settings.base_currency)
    print(md)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"projection-{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    main()
