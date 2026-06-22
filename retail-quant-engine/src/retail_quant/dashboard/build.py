"""Costruisce una dashboard HTML autonoma (CSS inline, nessuna dipendenza,
nessun server) che aggrega: riepilogo P/L, "Da guardare" (alert warn) e prossimi
eventi. Pensata per essere aperta nel browser e rigenerata dal timer giornaliero.
"""
from __future__ import annotations

import html
from datetime import datetime

from ..catalyst import catalyst
from ..catalyst.catalyst import _EVENT_LABELS
from ..config import Settings
from ..monitor.monitor import monitor as run_monitor
from ..monitor.state import load_state
from ..returns import returns

_CSS = """
:root{color-scheme:light dark}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;
  background:#f6f7f9;color:#1c2024;padding:24px;max-width:980px;margin:0 auto}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#6b7280;font-size:13px;margin-bottom:20px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px;margin-bottom:18px}
.kpis{display:flex;gap:28px;flex-wrap:wrap}
.kpi .label{color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.kpi .value{font-size:26px;font-weight:700;margin-top:2px}
h2{font-size:15px;margin:0 0 12px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:right;padding:8px 10px;border-bottom:1px solid #eef0f2}
th:first-child,td:first-child{text-align:left}
th{color:#6b7280;font-weight:600;font-size:12px;text-transform:uppercase}
.pos{color:#15803d}.neg{color:#b91c1c}
.alert{background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:10px 12px;margin:8px 0;font-size:14px}
.alert b{color:#92400e}
.muted{color:#6b7280;font-size:13px}
.warnbox{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:8px 12px;font-size:13px;color:#9a3412;margin-top:10px}
@media(prefers-color-scheme:dark){
  body{background:#0f1115;color:#e5e7eb}.card{background:#171a21;border-color:#262b35}
  th,td{border-color:#262b35}.sub,.kpi .label,.muted,th{color:#9aa4b2}
  .alert{background:#3a2e12;border-color:#5a4a1e}.alert b{color:#fcd34d}
  .warnbox{background:#3a230f;border-color:#7c3d12;color:#fdba74}}
"""


def _cls(v) -> str:
    return "pos" if (v or 0) >= 0 else "neg"


def render(holdings, settings: Settings, monitor_results=None) -> str:
    base = settings.base_currency
    rdata = returns.analyze(holdings, settings)
    cats = catalyst.upcoming(holdings, settings, horizon_days=90)
    if monitor_results is None:
        monitor_results, _ = run_monitor(holdings, settings, load_state())
    warns = [(r.ticker, a.message) for r in monitor_results for a in r.alerts if a.level == "warn"]

    parts = [
        "<!doctype html><html lang='it'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>Portafoglio</title><style>", _CSS, "</style></head><body>",
        "<h1>Portafoglio</h1>",
        f"<div class='sub'>Aggiornato il {html.escape(datetime.now().strftime('%d/%m/%Y %H:%M'))}"
        f" · valuta base {html.escape(base)}</div>",
    ]
    parts.append(_kpis(rdata, base))
    parts.append(_holdings_table(rdata, base))
    parts.append(_alerts(warns))
    parts.append(_events(cats))
    parts.append("</body></html>")
    return "".join(parts)


def _kpis(rdata: dict, base: str) -> str:
    pl = rdata["total_pl_pct"]
    pl_txt = f"{pl:+.2f}%" if pl is not None else "—"
    out = ["<div class='card'><div class='kpis'>"]
    out.append(f"<div class='kpi'><div class='label'>Valore di mercato</div>"
               f"<div class='value'>{rdata['total_market']:,.2f} {html.escape(base)}</div></div>")
    out.append(f"<div class='kpi'><div class='label'>P/L totale</div>"
               f"<div class='value {_cls(pl)}'>{pl_txt}</div></div>")
    out.append(f"<div class='kpi'><div class='label'>P/L assoluto</div>"
               f"<div class='value {_cls(rdata['total_pl_abs'])}'>{rdata['total_pl_abs']:+,.2f} {html.escape(base)}</div></div>")
    out.append("</div>")
    for w in rdata.get("warnings", []):
        out.append(f"<div class='warnbox'>⚠️ {html.escape(w)}</div>")
    out.append("</div>")
    return "".join(out)


def _holdings_table(rdata: dict, base: str) -> str:
    rows = ["<div class='card'><h2>Posizioni</h2><table><thead><tr>"
            f"<th>Titolo</th><th>Quotaz.</th><th>Carico ({html.escape(base)})</th>"
            f"<th>Mercato ({html.escape(base)})</th><th>P/L %</th><th>Peso %</th>"
            "</tr></thead><tbody>"]
    for r in rdata["rows"]:
        if r.error:
            rows.append(f"<tr><td>{html.escape(r.ticker)}</td><td colspan='5' class='muted'>"
                        f"errore: {html.escape(r.error)}</td></tr>")
            continue
        rows.append(
            f"<tr><td>{html.escape(r.ticker)}</td><td>{html.escape(r.currency)}</td>"
            f"<td>{r.cost_value:,.2f}</td><td>{r.market_value:,.2f}</td>"
            f"<td class='{_cls(r.pl_pct)}'>{r.pl_pct:+.2f}%</td><td>{r.weight_pct}%</td></tr>"
        )
    rows.append("</tbody></table></div>")
    return "".join(rows)


def _alerts(warns: list[tuple[str, str]]) -> str:
    out = ["<div class='card'><h2>⚠️ Da guardare</h2>"]
    if not warns:
        out.append("<div class='muted'>Nessun avviso. Tutto tranquillo.</div>")
    else:
        for ticker, msg in warns:
            out.append(f"<div class='alert'><b>{html.escape(ticker)}</b> — {html.escape(msg)}</div>")
    out.append("</div>")
    return "".join(out)


def _events(cats) -> str:
    out = ["<div class='card'><h2>Prossimi eventi (90 giorni)</h2>"]
    if not cats.events:
        out.append("<div class='muted'>Nessun evento in calendario.</div>")
    else:
        out.append("<table><thead><tr><th>Quando</th><th>Tra</th><th>Titolo</th><th>Evento</th>"
                   "</tr></thead><tbody>")
        for e in cats.events:
            out.append(
                f"<tr><td>{e.on.isoformat()}</td><td>{e.days_until}g</td>"
                f"<td>{html.escape(e.ticker)}</td>"
                f"<td>{html.escape(_EVENT_LABELS.get(e.kind, e.kind))}</td></tr>"
            )
        out.append("</tbody></table>")
    out.append("</div>")
    return "".join(out)
