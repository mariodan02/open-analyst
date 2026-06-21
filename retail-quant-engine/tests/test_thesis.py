"""Thesis tracker (deterministico, niente rete).

    python tests/test_thesis.py
"""
from __future__ import annotations

from retail_quant.monitor import thesis
from retail_quant.monitor.portfolio import load_portfolio


def test_breaches():
    th = {"max_pe": 30, "min_revenue_growth_pct": 5, "min_moat_rating": "narrow"}
    cur = {"pe_ratio": 45, "revenue_yoy_pct": 2, "moat_rating": "none"}
    a = thesis.evaluate("AAA", th, cur)
    msgs = " | ".join(al.message for al in a)
    assert "P/E 45" in msgs and "max 30" in msgs, msgs
    assert "crescita ricavi +2%" in msgs, msgs
    assert "moat 'none'" in msgs, msgs
    assert all(al.level == "warn" for al in a)
    print("✓ violazioni tesi ok")


def test_thesis_respected():
    th = {"max_pe": 50, "min_revenue_growth_pct": 0, "min_moat_rating": "narrow"}
    cur = {"pe_ratio": 30, "revenue_yoy_pct": 8, "moat_rating": "wide"}
    assert thesis.evaluate("AAA", th, cur) == []
    print("✓ tesi rispettata: nessun alert ok")


def test_no_thesis_and_partial(tmp_path):
    # nessuna tesi -> nessun alert
    assert thesis.evaluate("AAA", None, {"pe_ratio": 99}) == []
    # solo una chiave presente -> valuta solo quella
    a = thesis.evaluate("AAA", {"max_pe": 10}, {"pe_ratio": 20})
    assert len(a) == 1
    # load_portfolio legge il campo thesis
    p = tmp_path / "pf.json"
    p.write_text('{"holdings":[{"ticker":"AAPL","shares":1,"cost_basis":100,'
                 '"thesis":{"max_pe":35}}]}')
    h = load_portfolio(p)[0]
    assert h.thesis == {"max_pe": 35}
    print("✓ assente/parziale + load_portfolio ok")


if __name__ == "__main__":
    test_breaches()
    test_thesis_respected()
    import tempfile, pathlib
    test_no_thesis_and_partial(pathlib.Path(tempfile.mkdtemp()))
    print("\n✅ test_thesis: PASSATO")
