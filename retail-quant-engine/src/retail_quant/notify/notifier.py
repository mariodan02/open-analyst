"""Orchestrazione delle notifiche: raccoglie gli alert "warn", evita di
ripetere lo stesso avviso (dedup via firma persistente) e invia sui canali attivi.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import backends


def _warn_alerts(results) -> list[tuple[str, str]]:
    return [(r.ticker, a.message) for r in results for a in r.alerts if a.level == "warn"]


def _signature(warns: list[tuple[str, str]]) -> str:
    joined = "\n".join(sorted(f"{t}|{m}" for t, m in warns))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def dispatch(subject: str, body: str) -> list[str]:
    """Invia su tutti i canali attivi; ritorna lo stato per canale (non solleva)."""
    statuses: list[str] = []
    for name in backends.active_backends():
        fn = backends.BACKENDS[name][0]
        try:
            fn(subject, body)
            statuses.append(f"{name}: ok")
        except Exception as exc:  # noqa: BLE001 - un canale rotto non blocca gli altri
            statuses.append(f"{name}: ERRORE {type(exc).__name__}: {exc}")
    return statuses


def maybe_notify(results, state_dir: Path, force: bool = False) -> str:
    """Notifica gli alert warn, ma solo se cambiati dall'ultimo invio.

    Ritorna una riga di esito (cosa è stato fatto), da stampare al chiamante.
    """
    warns = _warn_alerts(results)
    if not warns:
        return "Niente da notificare (nessun alert da guardare)."

    sig = _signature(warns)
    sig_path = Path(state_dir) / "notify_state.json"
    if not force:
        try:
            prev = json.loads(sig_path.read_text(encoding="utf-8")).get("signature")
        except (FileNotFoundError, ValueError):
            prev = None
        if prev == sig:
            return "Alert invariati dall'ultimo invio: nessuna notifica."

    if not backends.active_backends():
        return "Nessun canale configurato nel .env (email/ntfy/telegram): notifica saltata."

    subject = f"[retail-quant] {len(warns)} avvisi da guardare"
    body = "\n".join(f"- {t}: {m}" for t, m in warns)
    statuses = dispatch(subject, body)

    # aggiorna la firma solo se almeno un canale ha avuto successo, così un invio
    # fallito verrà ritentato al prossimo giro
    if any(s.endswith(": ok") for s in statuses):
        sig_path.parent.mkdir(parents=True, exist_ok=True)
        sig_path.write_text(json.dumps({"signature": sig}), encoding="utf-8")
    return "Notifica -> " + "; ".join(statuses)
