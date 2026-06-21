"""Cache JSON con TTL + FX identity (niente rete).

    python tests/test_cache.py
"""
from __future__ import annotations

import time

from retail_quant.data import providers
from retail_quant.data.cache import JsonCache


def test_cache_hit_and_expiry(tmp_path):
    c = JsonCache(tmp_path / "c.json", ttl_seconds=100)
    assert c.get("k") is None              # vuota
    c.set("k", {"ter": 0.0019})
    assert c.get("k") == {"ter": 0.0019}   # hit (senza _ts)

    # TTL scaduto -> miss
    expired = JsonCache(tmp_path / "c.json", ttl_seconds=0)
    expired._data = None  # forza rilettura da disco
    time.sleep(0.01)
    assert expired.get("k") is None
    print("✓ cache hit/expiry ok")


def test_cache_persists_across_instances(tmp_path):
    JsonCache(tmp_path / "c.json", ttl_seconds=100).set("x", {"v": 1})
    fresh = JsonCache(tmp_path / "c.json", ttl_seconds=100)
    assert fresh.get("x") == {"v": 1}      # letta da disco da una nuova istanza
    print("✓ cache persistente su disco ok")


def test_fx_identity_no_network():
    # stessa valuta -> 1.0 senza toccare la rete
    assert providers.get_fx_rate("EUR", "EUR") == 1.0
    assert providers.get_fx_rate("usd", "USD") == 1.0
    print("✓ FX identity senza rete ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
