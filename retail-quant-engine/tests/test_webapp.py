"""Backend GUI: API portfolio + projection (Flask test client, niente rete).
Il file portfolio.json è isolato in tmp per non toccare quello reale.

    python tests/test_webapp.py
"""
from __future__ import annotations

import pytest

from retail_quant.webapp import app as webapp


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "PORTFOLIO_FILE", tmp_path / "portfolio.json")
    return webapp.create_app().test_client()


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200 and b"Retail Quant" in r.data
    print("✓ index servito ok")


def test_portfolio_roundtrip(client):
    # vuoto all'inizio
    assert client.get("/api/portfolio").get_json() == {"holdings": []}
    # salva (con campi extra da preservare/normalizzare)
    payload = {"holdings": [
        {"ticker": "vwce.mi", "shares": 6, "cost_basis": 151.27, "isin": "ie00bk5bqt80",
         "target_pct": 100, "thesis": {"max_pe": 30}},
        {"ticker": "", "shares": 1, "cost_basis": 1},  # scartato: senza ticker
    ]}
    res = client.post("/api/portfolio", json=payload).get_json()
    assert res["ok"] and res["saved"] == 1
    saved = client.get("/api/portfolio").get_json()["holdings"]
    assert len(saved) == 1
    h = saved[0]
    assert h["ticker"] == "VWCE.MI" and h["isin"] == "IE00BK5BQT80"  # normalizzati
    assert h["target_pct"] == 100.0 and h["thesis"] == {"max_pe": 30}  # preservati
    print("✓ portfolio round-trip + normalizzazione + thesis preservata ok")


def test_projection_endpoint(client):
    body = {"monthly": 100, "years": 2, "annual_return": 0, "inflation": 0, "from_portfolio": False}
    d = client.post("/api/projection", json=body).get_json()
    assert d["total_contributed"] == 2400 and d["final"] == 2400  # 0% = somma
    assert d["currency"] == "EUR" and len(d["rows"]) == 2
    # input non valido -> 400
    bad = client.post("/api/projection", json={"monthly": 1, "years": 0, "annual_return": 5})
    assert bad.status_code == 400
    print("✓ endpoint proiezione ok")


def test_comps_validation(client):
    r = client.post("/api/comps", json={"tickers": ["AAPL"]})
    assert r.status_code == 400  # serve almeno 1 pari
    print("✓ validazione comps ok")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
