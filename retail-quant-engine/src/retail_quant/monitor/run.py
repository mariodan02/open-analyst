"""CLI Fase 3 — monitoraggio del portafoglio.

    python -m retail_quant.monitor.run --file portfolio.json

Idempotente e schedulabile (cron/systemd): a ogni esecuzione confronta con lo
stato dell'ultimo controllo e salva il nuovo. Usa --no-save per una prova senza
toccare lo stato. La lente è quella in RQE_LENS. Non serve la chiave NVIDIA.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from .monitor import monitor
from .portfolio import load_portfolio
from .report import build_markdown
from .state import STATE_DIR, STATE_FILE, load_state, save_state

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"
DEFAULT_PORTFOLIO = Path(__file__).resolve().parents[3] / "portfolio.example.json"


def main() -> None:
    p = argparse.ArgumentParser(description="Monitoraggio portafoglio (Fase 3)")
    p.add_argument("--file", default=str(DEFAULT_PORTFOLIO), help="file portafoglio JSON")
    p.add_argument("--no-save", action="store_true", help="non aggiornare lo stato")
    p.add_argument("--notify", action="store_true",
                   help="invia gli alert sui canali configurati (email/ntfy/telegram)")
    p.add_argument("--notify-force", action="store_true",
                   help="con --notify, invia anche se gli alert non sono cambiati")
    p.add_argument("--dashboard", action="store_true",
                   help="rigenera anche la dashboard HTML in reports/dashboard.html")
    args = p.parse_args()

    settings = Settings.load(require_llm=False)
    holdings = load_portfolio(args.file)
    prev_state = load_state()
    first_run = not prev_state

    print(f"Monitoraggio di {len(holdings)} titoli — lente: {settings.lens}\n")
    results, new_state = monitor(holdings, settings, prev_state)
    md = build_markdown(results, settings.lens, first_run)
    print(md)

    if not args.no_save:
        save_state(new_state)
        print(f"\n[stato aggiornato: {STATE_FILE}]")

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"monitor-{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"[report salvato: {out}]")

    if args.notify:
        from ..notify import notifier
        print("[" + notifier.maybe_notify(results, STATE_DIR, force=args.notify_force) + "]")

    if args.dashboard:
        from ..dashboard.run import write_dashboard
        out = write_dashboard(holdings, settings, monitor_results=results)
        print(f"[dashboard: {out}]")


if __name__ == "__main__":
    main()
