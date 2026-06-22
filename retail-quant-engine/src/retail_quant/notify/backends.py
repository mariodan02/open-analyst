"""Canali di notifica. Ognuno è "attivo" se le sue variabili .env sono presenti;
così si abilita un canale semplicemente configurandolo, senza toccare il codice.

Config (.env):
  Email (Gmail):  RQE_SMTP_USER, RQE_SMTP_PASSWORD (app password)
                  [RQE_SMTP_HOST=smtp.gmail.com, RQE_SMTP_PORT=587,
                   RQE_NOTIFY_EMAIL_TO=<dest, default = SMTP_USER>]
  ntfy:           RQE_NTFY_TOPIC  [RQE_NTFY_SERVER=https://ntfy.sh]
  Telegram:       RQE_TELEGRAM_BOT_TOKEN, RQE_TELEGRAM_CHAT_ID
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import requests

_TIMEOUT = 30


def send_email(subject: str, body: str) -> None:
    user = os.environ["RQE_SMTP_USER"]
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = os.getenv("RQE_NOTIFY_EMAIL_TO", user)
    msg["Subject"] = subject
    msg.set_content(body)
    host = os.getenv("RQE_SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("RQE_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=_TIMEOUT) as s:
        s.starttls()
        s.login(user, os.environ["RQE_SMTP_PASSWORD"])
        s.send_message(msg)


def send_ntfy(subject: str, body: str) -> None:
    server = os.getenv("RQE_NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    topic = os.environ["RQE_NTFY_TOPIC"]
    # l'header Title deve essere latin-1: ripiega su ASCII se serve
    title = subject.encode("ascii", "replace").decode("ascii")
    resp = requests.post(
        f"{server}/{topic}", data=body.encode("utf-8"),
        headers={"Title": title, "Tags": "warning"}, timeout=_TIMEOUT,
    )
    resp.raise_for_status()


def send_telegram(subject: str, body: str) -> None:
    token = os.environ["RQE_TELEGRAM_BOT_TOKEN"]
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": os.environ["RQE_TELEGRAM_CHAT_ID"], "text": f"{subject}\n\n{body}"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()


# nome -> (funzione, variabili obbligatorie)
BACKENDS = {
    "email": (send_email, ("RQE_SMTP_USER", "RQE_SMTP_PASSWORD")),
    "ntfy": (send_ntfy, ("RQE_NTFY_TOPIC",)),
    "telegram": (send_telegram, ("RQE_TELEGRAM_BOT_TOKEN", "RQE_TELEGRAM_CHAT_ID")),
}


def active_backends() -> list[str]:
    return [name for name, (_, reqs) in BACKENDS.items() if all(os.getenv(r) for r in reqs)]
