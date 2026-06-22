#!/usr/bin/env bash
# Installa un systemd *user* timer che lancia il monitoraggio una volta al giorno
# con notifica. Persistent=true recupera il giro se il PC era spento all'orario.
#
# Uso:
#   ./deploy/install-timer.sh [HH:MM]      # default 08:00
#
# Disinstallare:
#   systemctl --user disable --now retail-quant-monitor.timer
set -euo pipefail

TIME="${1:-08:00}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$PROJECT_DIR/.venv/bin/python"
PORTFOLIO="$PROJECT_DIR/portfolio.json"
UNIT_DIR="$HOME/.config/systemd/user"

[ -x "$VENV_PY" ] || { echo "Manca il venv: $VENV_PY (crea l'ambiente e installa il pacchetto)"; exit 1; }
[ -f "$PORTFOLIO" ] || echo "Attenzione: $PORTFOLIO non esiste ancora — crealo prima del primo giro."

mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/retail-quant-monitor.service" <<EOF
[Unit]
Description=retail-quant-engine portfolio monitor

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PY -m retail_quant.monitor.run --file "$PORTFOLIO" --notify
EOF

cat > "$UNIT_DIR/retail-quant-monitor.timer" <<EOF
[Unit]
Description=Run retail-quant monitor daily

[Timer]
OnCalendar=*-*-* $TIME:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now retail-quant-monitor.timer

echo "Installato. Prossimo avvio:"
systemctl --user list-timers retail-quant-monitor.timer --no-pager || true
echo
echo "Note:"
echo " - I canali di notifica vanno configurati nel .env (email/ntfy/telegram)."
echo " - Per girare anche quando non sei loggato:  loginctl enable-linger $USER"
echo " - Prova subito un giro:  systemctl --user start retail-quant-monitor.service"
echo " - Log dell'ultimo giro:  journalctl --user -u retail-quant-monitor.service -n 30"
