# Scheduler + notifiche

Far girare il monitoraggio **una volta al giorno** e ricevere un avviso solo
quando c'è qualcosa "da guardare".

## 1. Configura i canali di notifica (`.env`)

Abiliti un canale semplicemente compilandone le variabili nel `.env` (vedi
`.env.example`). Puoi attivarne più di uno. La notifica parte **solo se ci sono
alert "warn" e solo se sono cambiati** dall'ultimo invio (niente spam).

- **Email (Gmail)** — serve una *app password* (non la password normale):
  Account Google → Sicurezza → Verifica in due passaggi → Password per le app.
  Poi `RQE_SMTP_USER` + `RQE_SMTP_PASSWORD`.
- **ntfy** (push sul telefono, gratis) — installa l'app *ntfy*, iscriviti a un
  topic con un nome segreto a tua scelta, e metti lo stesso in `RQE_NTFY_TOPIC`.
- **Telegram** — crea un bot con [@BotFather](https://t.me/botfather), prendi il
  token; ricava il `chat_id` (es. scrivi al bot e apri
  `https://api.telegram.org/bot<token>/getUpdates`). Metti entrambi nel `.env`.

Prova l'invio (anche senza cambiamenti) con:
```bash
python -m retail_quant.monitor.run --file portfolio.json --notify --notify-force
```

## 2. Schedula — systemd timer (consigliato)

```bash
./deploy/install-timer.sh 08:00      # ora a scelta, default 08:00
```
`Persistent=true`: se il PC era spento all'orario, il giro parte al riavvio.

Comandi utili:
```bash
systemctl --user list-timers retail-quant-monitor.timer   # quando girerà
systemctl --user start retail-quant-monitor.service        # giro manuale
journalctl --user -u retail-quant-monitor.service -n 30    # log ultimo giro
loginctl enable-linger $USER                               # gira anche da sloggato
systemctl --user disable --now retail-quant-monitor.timer  # disinstalla
```

## 3. Alternativa — cron

Più semplice ma **non recupera** i giri persi se il PC era spento. `crontab -e`:
```
0 8 * * *  cd /percorso/retail-quant-engine && .venv/bin/python -m retail_quant.monitor.run --file portfolio.json --notify >> reports/cron.log 2>&1
```
