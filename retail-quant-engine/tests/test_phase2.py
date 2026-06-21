"""Test Fase 2. I criteri si testano SENZA rete e SENZA LLM (dati finti);
lo screener reale e il commento IA (con stub) sono in fondo.

    python tests/test_phase2.py
"""
from __future__ import annotations

from langchain_core.messages import AIMessage

from retail_quant.config import Settings
from retail_quant.screen import criteria
from retail_quant.screen.report import build_markdown, llm_comment
from retail_quant.screen.screener import ScreenRow, screen_universe, shortlist


def test_criteria_deterministic():
    # value: questo passa tutto (P/E basso, FCF alto, poca leva)
    ok, score, reasons = criteria.evaluate(
        "value", {"pe_ratio": 12.0, "fcf_yield_pct": 7.0, "debt_to_equity": 0.5}
    )
    assert ok is True, reasons
    assert any("P/E" in r for r in reasons)

    # value: questo NON passa (P/E altissimo)
    ok2, _, _ = criteria.evaluate(
        "value", {"pe_ratio": 80.0, "fcf_yield_pct": 1.0, "debt_to_equity": 2.0}
    )
    assert ok2 is False

    # dati mancanti -> non deve crashare, semplicemente non passa
    ok3, _, _ = criteria.evaluate("value", {})
    assert ok3 is False
    print("✓ criteri deterministici ok")


def test_ranking_and_report():
    rows = [
        ScreenRow("AAA", score=10, passes=True, metrics={"pe_ratio": 12, "fcf_yield_pct": 7, "debt_to_equity": 0.5}, reasons=["✓ tutto"]),
        ScreenRow("BBB", score=-5, passes=False, metrics={"pe_ratio": 40, "fcf_yield_pct": 1, "debt_to_equity": 2}, reasons=["✗ caro"]),
        ScreenRow("ZZZ", error="boom"),
    ]
    rows.sort(key=lambda r: (r.error is not None, not r.passes, -r.score))
    assert rows[0].ticker == "AAA"  # chi passa e ha score alto è primo
    assert rows[-1].ticker == "ZZZ"  # gli errori in fondo
    md = build_markdown(rows, "value", Settings.load(require_llm=False))
    assert "Lista corta" in md and "AAA" in md
    assert len(shortlist(rows)) == 1
    print("✓ ranking e report ok")


class StubLLM:
    def invoke(self, messages):
        self.last = messages
        return AIMessage(content="COMMENTO DI PROVA: AAA è il migliore.")


def test_llm_comment_with_stub():
    rows = [ScreenRow("AAA", score=10, passes=True, metrics={"pe_ratio": 12})]
    out = llm_comment(rows, "value", Settings.load(require_llm=False), llm=StubLLM())
    assert "COMMENTO DI PROVA" in out
    print("✓ commento IA (stub) ok")


def test_real_screen_small():
    """Screening reale su 3 titoli (usa la rete, niente LLM)."""
    settings = Settings.load(require_llm=False)
    rows = screen_universe(["AAPL", "KO", "JNJ"], settings.lens, settings)
    assert len(rows) == 3
    for r in rows:
        print(f"  {r.ticker}: pass={r.passes} score={r.score} err={r.error}")
    print("✓ screening reale ok")


if __name__ == "__main__":
    test_criteria_deterministic()
    test_ranking_and_report()
    test_llm_comment_with_stub()
    test_real_screen_small()
    print("\n✅ test_phase2: PASSATO")
