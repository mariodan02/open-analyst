"""Backend Flask della GUI locale. Espone una piccola API JSON che riusa i
moduli del motore, più la dashboard HTML servita in un iframe.

Solo per uso LOCALE: si lega a 127.0.0.1 e non ha autenticazione.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from ..config import Settings
from ..monitor.portfolio import load_portfolio

PROJECT_DIR = Path(__file__).resolve().parents[3]
PORTFOLIO_FILE = PROJECT_DIR / "portfolio.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    # ----- frontend ----------------------------------------------------------
    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/dashboard.html")
    def dashboard_html():
        from ..dashboard import build

        settings = Settings.load(require_llm=False)
        holdings = _load_holdings()
        if not holdings:
            return "<p style='font-family:sans-serif;padding:24px'>Portafoglio vuoto: " \
                   "aggiungi titoli nella scheda <b>Posizioni</b>.</p>"
        return build.render(holdings, settings)

    # ----- portafoglio (lettura/scrittura del file) --------------------------
    @app.get("/api/portfolio")
    def get_portfolio():
        if PORTFOLIO_FILE.exists():
            data = json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
        else:
            data = {"holdings": []}
        return jsonify(data)

    @app.post("/api/portfolio")
    def save_portfolio():
        data = request.get_json(force=True)
        holdings = data.get("holdings", [])
        if not isinstance(holdings, list):
            return jsonify(error="formato non valido: 'holdings' deve essere una lista"), 400
        clean = []
        for h in holdings:
            if not h.get("ticker"):
                continue
            row = {"ticker": str(h["ticker"]).strip().upper(),
                   "shares": float(h.get("shares") or 0),
                   "cost_basis": float(h.get("cost_basis") or 0)}
            if h.get("isin"):
                row["isin"] = str(h["isin"]).strip().upper()
            if h.get("target_pct") not in (None, ""):
                row["target_pct"] = float(h["target_pct"])
            if isinstance(h.get("thesis"), dict):
                row["thesis"] = h["thesis"]  # preserva la tesi se presente
            clean.append(row)
        PORTFOLIO_FILE.write_text(json.dumps({"holdings": clean}, indent=2), encoding="utf-8")
        return jsonify(ok=True, saved=len(clean))

    # ----- strumenti ---------------------------------------------------------
    @app.post("/api/projection")
    def api_projection():
        from ..projection import projection
        from ..returns import returns

        p = request.get_json(force=True)
        settings = Settings.load(require_llm=False)
        initial = float(p.get("initial") or 0)
        if p.get("from_portfolio"):
            holdings = _load_holdings()
            if holdings:
                initial = returns.analyze(holdings, settings)["total_market"]
        # fasi: [[anni, mensile], ...]; in alternativa monthly+years (fase unica)
        if p.get("steps"):
            steps = [(int(y), float(m)) for y, m in p["steps"]]
        elif p.get("monthly") is not None and p.get("years") is not None:
            steps = [(int(p["years"]), float(p["monthly"]))]
        else:
            return jsonify(error="indica 'steps' oppure 'monthly' e 'years'"), 400
        try:
            res = projection.project_steps(
                steps, annual_return_pct=float(p["annual_return"]),
                initial=initial, inflation_pct=float(p.get("inflation") or 0),
            )
        except (ValueError, KeyError) as exc:
            return jsonify(error=str(exc)), 400
        out = asdict(res)
        out["currency"] = settings.base_currency
        return jsonify(out)

    @app.post("/api/comps")
    def api_comps():
        from ..comps import comps

        p = request.get_json(force=True)
        tickers = [t.strip().upper() for t in p.get("tickers", []) if t.strip()]
        if len(tickers) < 2:
            return jsonify(error="servono almeno 2 ticker (target + 1 pari)"), 400
        res = comps.compare(tickers[0], tickers[1:], Settings.load(require_llm=False))
        res["rows"] = [asdict(r) for r in res["rows"]]
        return jsonify(res)

    @app.post("/api/analyze")
    def api_analyze():
        from ..agent.graph import build_graph, initial_state

        p = request.get_json(force=True)
        ticker = str(p.get("ticker", "")).strip().upper()
        if not ticker:
            return jsonify(error="ticker mancante"), 400
        try:
            settings = Settings.load()  # qui serve la chiave NVIDIA
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 400
        graph = build_graph(settings)
        final = graph.invoke(initial_state(ticker, settings.lens, p.get("isin")))
        return jsonify(report=final["report"])

    @app.post("/api/export")
    def api_export():
        from datetime import date

        from ..export import csv_export

        settings = Settings.load(require_llm=False)
        holdings = _load_holdings()
        if not holdings:
            return jsonify(error="portafoglio vuoto"), 400
        out = PROJECT_DIR / "reports" / f"portfolio-{date.today().isoformat()}.csv"
        csv_export.write_csv(holdings, settings, out)
        return jsonify(ok=True, path=str(out))

    @app.get("/static/<path:name>")
    def static_files(name):
        return send_from_directory(STATIC_DIR, name)

    return app


def _load_holdings():
    if not PORTFOLIO_FILE.exists():
        return []
    try:
        return load_portfolio(PORTFOLIO_FILE)
    except (ValueError, json.JSONDecodeError):
        return []
