"""Notifiche: dedup, dispatch e rilevamento canali (niente rete).

    python tests/test_notify.py
"""
from __future__ import annotations

from retail_quant.monitor.alerts import Alert
from retail_quant.monitor.monitor import MonitorResult
from retail_quant.notify import backends, notifier


def _results(*warn_msgs):
    alerts = [Alert("AAA", "warn", m) for m in warn_msgs] + [Alert("AAA", "info", "ignorami")]
    return [MonitorResult("AAA", alerts=alerts)]


def test_no_warns_no_notify(tmp_path):
    res = [MonitorResult("AAA", alerts=[Alert("AAA", "info", "solo info")])]
    out = notifier.maybe_notify(res, tmp_path)
    assert "Niente da notificare" in out
    print("✓ nessun warn -> nessuna notifica ok")


def test_dedup(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(backends, "active_backends", lambda: ["ntfy"])
    monkeypatch.setattr(notifier, "dispatch", lambda s, b: calls.append((s, b)) or ["ntfy: ok"])

    out1 = notifier.maybe_notify(_results("P/L -25%"), tmp_path)
    assert "ntfy: ok" in out1 and len(calls) == 1, out1
    # stessi alert -> niente reinvio
    out2 = notifier.maybe_notify(_results("P/L -25%"), tmp_path)
    assert "invariati" in out2.lower() and len(calls) == 1, out2
    # alert diverso -> reinvio
    out3 = notifier.maybe_notify(_results("Earnings tra 7 giorni"), tmp_path)
    assert len(calls) == 2, out3
    # force ignora la dedup
    notifier.maybe_notify(_results("Earnings tra 7 giorni"), tmp_path, force=True)
    assert len(calls) == 3
    print("✓ dedup + force ok")


def test_dispatch_isolates_failure(monkeypatch):
    def ok(s, b): pass
    def boom(s, b): raise RuntimeError("smtp down")
    monkeypatch.setattr(backends, "BACKENDS", {"ntfy": (ok, ()), "email": (boom, ())})
    monkeypatch.setattr(backends, "active_backends", lambda: ["ntfy", "email"])
    statuses = notifier.dispatch("s", "b")
    assert "ntfy: ok" in statuses
    assert any("email: ERRORE" in s for s in statuses), statuses
    print("✓ dispatch isola il canale rotto ok")


def test_active_backends_env(monkeypatch):
    for v in ("RQE_SMTP_USER", "RQE_SMTP_PASSWORD", "RQE_NTFY_TOPIC",
              "RQE_TELEGRAM_BOT_TOKEN", "RQE_TELEGRAM_CHAT_ID"):
        monkeypatch.delenv(v, raising=False)
    assert backends.active_backends() == []
    monkeypatch.setenv("RQE_NTFY_TOPIC", "il-mio-topic")
    assert backends.active_backends() == ["ntfy"]
    monkeypatch.setenv("RQE_SMTP_USER", "x@gmail.com")
    monkeypatch.setenv("RQE_SMTP_PASSWORD", "app-pw")
    assert set(backends.active_backends()) == {"email", "ntfy"}
    print("✓ rilevamento canali da .env ok")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
