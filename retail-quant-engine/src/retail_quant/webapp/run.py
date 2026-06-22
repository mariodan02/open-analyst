"""Avvia la GUI locale:

    python -m retail_quant.webapp.run            # http://127.0.0.1:5000
    python -m retail_quant.webapp.run --port 8080 --open

Solo locale (127.0.0.1), nessuna autenticazione.
"""
from __future__ import annotations

import argparse
import threading
import webbrowser

from .app import create_app


def main() -> None:
    ap = argparse.ArgumentParser(description="GUI locale del portafoglio.")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--open", action="store_true", help="apri il browser all'avvio")
    args = ap.parse_args()

    app = create_app()
    url = f"http://127.0.0.1:{args.port}"
    print(f"GUI su {url}  (Ctrl+C per fermare)")
    if args.open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
