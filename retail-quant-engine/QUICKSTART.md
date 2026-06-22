# Quick Start

```bash
cd retail-quant-engine && source .venv/bin/activate
```

## 🖥️ GUI (la via più semplice)

```bash
python -m retail_quant.webapp.run --open      # http://127.0.0.1:5000
```
Pagina web locale: scheda **Portafoglio** (dashboard live), **Posizioni** (aggiungi/
modifica/salva i titoli senza toccare il JSON), **Strumenti** (proiezione PAC, comps,
analisi IA, export CSV). Solo locale, nessuna autenticazione. (Richiede `flask`:
`pip install -r requirements.txt`.)

I comandi da terminale qui sotto restano tutti validi.

## Comandi

```bash
# Analisi di un titolo (usa l'LLM su NVIDIA, ~60-70s) -> reports/
python -m retail_quant.agent.run GOOG
python -m retail_quant.agent.run VWCE.MI --isin IE00BK5BQT80   # ETF

# Screening di una lista
python -m retail_quant.screen.run AAPL MSFT PFE [--summary]

# Comps: target vs pari (P/E, P/S, margini, verdetto)
python -m retail_quant.comps.run AAPL MSFT GOOGL META

# Portafoglio (file portfolio.json — vedi sotto)
python -m retail_quant.monitor.run   --file portfolio.json   # guardia: P/L, alert sui cambiamenti
python -m retail_quant.monitor.run   --file portfolio.json --notify   # + invia gli alert (email/ntfy/telegram)
python -m retail_quant.returns.run   --file portfolio.json   # performance: P/L, pesi
python -m retail_quant.rebalance.run --file portfolio.json --cash 500   # riallinea ai target_pct
python -m retail_quant.catalyst.run  --file portfolio.json --days 90    # prossimi earnings/dividendi
python -m retail_quant.dashboard.run --file portfolio.json --open       # dashboard HTML (con equity curve)
python -m retail_quant.export.run    --file portfolio.json              # posizioni + P/L in CSV

# Proiezione PAC: X€/mese a Y% per N anni (--file = parti dal valore attuale)
python -m retail_quant.projection.run --monthly 200 --years 20 --return 6 --inflation 2 --file portfolio.json
# ...a fasi: 200/mese per 5 anni, poi 400/mese per 10 anni
python -m retail_quant.projection.run --phase 5:200 --phase 10:400 --return 6 --inflation 2

# Controlli senza LLM e senza costo
python -m retail_quant.smoke_test GOOG    # solo dati + metriche
python -m pytest -q                       # i test
```

Tutto deterministico **tranne** `agent.run` (l'unico che chiama l'LLM e costa crediti).
Lente di calcolo via `RQ_LENS` (`value` default, `growth`, `dividends`, `trading`).
Gli **ETF** sono riconosciuti in automatico ovunque (saltano i conti da azione).

## Il file `portfolio.json`

Campi **dall'estratto della banca**:

| Campo | Colonna estratto | Esempio |
|---|---|---|
| `ticker` | Simbolo (vedi nota) | `VWCE.MI` |
| `shares` | Quantità | `6` |
| `cost_basis` | Prezzo medio di carico | `151.27` |
| `isin` | ISIN (ETF, opzionale) | `IE00BK5BQT80` |

Campi **tuoi**, opzionali: `target_pct` (peso obiettivo, sommano a 100, per il rebalance),
`thesis` (paletti per gli alert, es. `{"max_pe": 35}`). File completo: `portfolio.example.json`.

> ⚠️ Il `ticker` è quello **di Yahoo Finance**, col suffisso di mercato: `.MI` Milano,
> `.DE` Xetra, `.PA` Parigi, `.L` Londra; azioni USA senza suffisso. Se il motore trova
> il prezzo, è corretto.

## Note

- `margin_of_safety` (lente value) è un **DCF reale**: severo per i mega-cap tech.
- Senza `FMP_API_KEY` o se FMP rifiuta (402/403), i bilanci vengono da yfinance
  (storico ~4 anni invece di 5); stampa un `[warn]` e prosegue.
- **Valuta base** dei totali (returns/rebalance): `RQE_BASE_CURRENCY` (default
  `EUR`). I titoli in altre valute sono convertiti via cambio yfinance; **i prezzi
  sono sempre live**.
- **Cache ETF**: i metadati justETF (TER, accumulazione…) sono in `cache/` per
  `RQE_ETF_CACHE_DAYS` giorni (default 7; `0` = sempre fresco). Mai il prezzo.
- **Rate limit (429)**: throttle globale tra le chiamate di rete
  (`RQE_REQUEST_DELAY`, default 0.34s; `0` = nessuno) + circuit breaker FMP (al
  primo 402/403/429 si passa a yfinance per la sessione).
- **Scheduler + notifiche**: `deploy/install-timer.sh` (systemd, una volta al
  giorno) + canali nel `.env` (email/ntfy/telegram). Guida: `deploy/README.md`.
- **Equity curve**: la dashboard logga un punto al giorno in `history/`; la curva
  compare dal 2º giorno (il timer la alimenta da solo).
- Mappa del codice e changelog: vedi `CLAUDE.md`.
