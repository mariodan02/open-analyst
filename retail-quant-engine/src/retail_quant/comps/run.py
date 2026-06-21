"""CLI comps — valutazione relativa di un titolo vs pari:

    python -m retail_quant.comps.run AAPL MSFT GOOGL META

Il primo ticker è il target, gli altri sono i pari. Niente LLM: solo numeri.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from ..config import Settings
from . import comps, report

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("Uso: python -m retail_quant.comps.run <TARGET> <PEER1> [PEER2 ...]")
        raise SystemExit(1)
    target, peers = argv[0], argv[1:]

    settings = Settings.load(require_llm=False)  # comps è deterministico
    result = comps.compare(target, peers, settings)
    md = report.build_markdown(result)
    print(md)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"comps-{target.upper()}-{date.today().isoformat()}.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n[salvato in: {out}]")


if __name__ == "__main__":
    main(sys.argv[1:])
