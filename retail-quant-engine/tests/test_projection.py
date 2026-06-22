"""Proiezione PAC (aritmetica pura, niente rete).

    python tests/test_projection.py
"""
from __future__ import annotations

from retail_quant.projection import projection


def test_zero_return_is_just_sum():
    # rendimento 0%: il finale è solo la somma dei versamenti (+ iniziale)
    r = projection.project(monthly=100, annual_return_pct=0, years=2, initial=500)
    assert r.total_contributed == 500 + 100 * 24
    assert r.final == r.total_contributed and r.gains == 0.0
    assert len(r.rows) == 2 and r.rows[-1].year == 2
    print("✓ rendimento 0% = somma versamenti ok")


def test_growth_and_gains():
    # con rendimento positivo il finale supera il versato; gli interessi sono la differenza
    r = projection.project(monthly=200, annual_return_pct=6, years=10)
    assert r.total_contributed == 200 * 120
    assert r.final > r.total_contributed
    assert abs(r.gains - (r.final - r.total_contributed)) < 0.01
    # 12 mesi al 6% compongono ~ esattamente il 6% annuo: 100 -> ~106 su un anno
    one_year = projection.project(monthly=0, annual_return_pct=6, years=1, initial=100)
    assert abs(one_year.final - 106.0) < 0.01, one_year.final
    print("✓ crescita + interessi + composizione annua ok")


def test_real_value_with_inflation():
    r = projection.project(monthly=0, annual_return_pct=10, years=10, initial=1000, inflation_pct=10)
    # rendimento = inflazione -> potere d'acquisto invariato (~1000)
    assert r.final_real is not None and abs(r.final_real - 1000) < 1, r.final_real
    print("✓ valore reale con inflazione ok")


def test_stepped_contributions():
    # 200/mese per 5 anni, poi 400/mese per 10 anni (15 anni totali)
    r = projection.project_steps([(5, 200), (10, 400)], annual_return_pct=6)
    assert r.years == 15 and len(r.rows) == 15
    assert r.total_contributed == 200 * 60 + 400 * 120  # versato a fasi
    assert r.final > r.total_contributed
    # equivale a una fase unica con lo stesso schema solo se i versamenti coincidono:
    flat = projection.project(monthly=200, annual_return_pct=6, years=15)
    assert r.final > flat.final  # versando di più nella 2ª fase si arriva più in alto
    print("✓ versamenti a fasi ok")


def test_guards():
    for bad in (dict(monthly=100, annual_return_pct=5, years=0),
                dict(monthly=-1, annual_return_pct=5, years=5)):
        try:
            projection.project(**bad)
            assert False, "doveva sollevare"
        except ValueError:
            pass
    print("✓ guardie input ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
