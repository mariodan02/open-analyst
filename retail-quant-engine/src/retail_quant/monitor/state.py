"""Stato persistente tra un controllo e l'altro.

Salviamo per ogni titolo una piccola "istantanea" (prezzo, ultimo anno di
bilancio, metriche chiave) così al controllo successivo possiamo capire COSA
è cambiato. Senza stato non c'è monitoraggio: solo una foto del momento.
"""
from __future__ import annotations

import json
from pathlib import Path

# cartella di stato, accanto al package, gitignorata
STATE_DIR = Path(__file__).resolve().parents[3] / "state"
STATE_FILE = STATE_DIR / "monitor_state.json"


def load_state(path: Path = STATE_FILE) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
