"""Cache JSON locale con TTL per dati esterni lenti o fragili (es. profili ETF
da justETF). Evita richieste ripetute e fa da rete di sicurezza se la fonte
diventa irraggiungibile entro la finestra di validità.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


class JsonCache:
    def __init__(self, path: str | Path, ttl_seconds: float):
        self.path = Path(path)
        self.ttl = ttl_seconds
        self._data: dict | None = None

    def _load(self) -> dict:
        if self._data is None:
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, ValueError):
                self._data = {}
        return self._data

    def get(self, key: str) -> dict | None:
        """Valore se presente e non scaduto, altrimenti None."""
        entry = self._load().get(key)
        if not entry or time.time() - entry.get("_ts", 0) > self.ttl:
            return None
        return {k: v for k, v in entry.items() if k != "_ts"}

    def set(self, key: str, value: dict) -> None:
        data = self._load()
        data[key] = {**value, "_ts": time.time()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
