"""CLI Fase 2 — screening di molti titoli.

    # lista esplicita:
    python -m retail_quant.screen.run AAPL MSFT GOOGL KO JNJ
    # da file (un ticker per riga):
    python -m retail_quant.screen.run --file watchlist.txt
    # aggiungi il commento dell'IA sulla lista corta (usa NVIDIA, costa crediti):
    python -m retail_quant.screen.run AAPL MSFT KO --summary

La lente è quella in RQE_LENS. Senza --summary NON serve la chiave NVIDIA.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..config import Settings
from .report import build_markdown, llm_comment
from .screener import screen_universe

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"

# piccolo universo di default, utile per provare al volo
DEFAULT_UNIVERSE = ["AAPL", "MSFT", "GOOGL", "KO", "JNJ", "INTC", "PFE", "XOM"]


def _read_file(path: str) -> list[str]:
    return [
        line.strip().upper()
        for line in Path(path).read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def main() -> None:
    p = argparse.ArgumentParser(description="Screening di molti titoli (Fase 2)")
    p.add_argument("tickers", nargs="*", help="lista di ticker")
    p.add_argument("--file", help="file con un ticker per riga")
    p.add_argument("--summary", action="store_true", help="commento IA sulla lista corta")
    args = p.parse_args()

    tickers = args.tickers or (_read_file(args.file) if args.file else DEFAULT_UNIVERSE)
    settings = Settings.load(require_llm=args.summary)

    print(f"Screening di {len(tickers)} titoli — lente: {settings.lens}\n")
    rows = screen_universe(tickers, settings.lens, settings)
    md = build_markdown(rows, settings.lens, settings)

    if args.summary:
        print("Genero il commento IA sulla lista corta...\n")
        md += "\n\n## Commento dell'IA (lista corta)\n\n" + llm_comment(rows, settings.lens, settings)

    print(md)
    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"screen-{settings.lens}-{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    main()
