"""CLI dashboard — genera una pagina HTML del portafoglio:

    python -m retail_quant.dashboard.run --file portfolio.json [--open]

Salva reports/dashboard.html (apribile nel browser). --open la apre subito.
"""
from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from ..config import Settings
from ..history import history
from ..monitor.portfolio import load_portfolio
from ..returns import returns
from . import build

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def write_dashboard(holdings, settings: Settings, monitor_results=None) -> Path:
    # calcola i returns una volta sola: serve sia per registrare lo storico
    # (equity curve) sia per la pagina
    rdata = returns.analyze(holdings, settings)
    history.record(rdata)
    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / "dashboard.html"
    out.write_text(build.render(holdings, settings, monitor_results, rdata=rdata), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Dashboard HTML del portafoglio.")
    ap.add_argument("--file", default="portfolio.json", help="file del portafoglio (JSON)")
    ap.add_argument("--open", action="store_true", help="apri la pagina nel browser")
    args = ap.parse_args()

    settings = Settings.load(require_llm=False)
    holdings = load_portfolio(args.file)
    out = write_dashboard(holdings, settings)
    print(f"[dashboard: {out}]")
    if args.open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
