# Quick Start — Fase 1 (analisi di un singolo titolo)

Guida rapida per analizzare un ticker.

> ⚠️ **Il comando che fa l'analisi è `agent.run`.** `smoke_test` mostra solo
> dati e metriche e **NON** chiama l'IA — è un controllo, non l'analisi.

## 0. Prerequisiti (una volta sola)

```bash
cd retail-quant-engine
source .venv/bin/activate
```

Il file `.env` deve contenere le chiavi (vedi `.env.example`):

| Variabile | Serve per | Obbligatoria? |
|---|---|---|
| `NVIDIA_API_KEY` | il nodo `thesis` (LLM) | sì, per l'analisi |
| `FMP_API_KEY` | i bilanci (5 anni) | opzionale; senza/se rifiuta → fallback yfinance |
| `RQ_LENS` | lente di calcolo (`value`/`growth`/`dividends`/`trading`) | opzionale, default `value` |

> yfinance (prezzo/news/bilanci) non richiede chiavi.

---

## ▶️ Analizzare un ticker (il comando principale)

```bash
python -m retail_quant.agent.run GOOG
```

- Esegue `fetch → metrics → thesis (LLM) → validate`.
- Tempo tipico: ~60–70s (DeepSeek su NVIDIA).
- Salva il report in `reports/<TICKER>-<lente>-<data>.md` e lo stampa a video.

---

## 🔍 Controlli opzionali (NON sono l'analisi)

**Solo dati + metriche, niente IA, niente costo** — utile per verificare un
ticker prima di spendere crediti:

```bash
python -m retail_quant.smoke_test GOOG
```
Atteso: blocco PREZZO + blocco METRICHE. Nessun giudizio scritto.

**Test del grafo end-to-end** con stub LLM (niente chiave):

```bash
python tests/test_phase1.py
```
Atteso: `✅ test_phase1: PASSATO`.

---

## Cambiare ticker o lente

```bash
# altro ticker
python -m retail_quant.agent.run NVDA

# cambiare lente per questa esecuzione
RQ_LENS=growth python -m retail_quant.agent.run NVDA
```

Lenti disponibili: `value` (default), `growth`, `dividends`, `trading`.
Cambi lente = cambi i calcoli (nodo metrics), **stessi dati**.

---

## Note / gotcha

- `margin_of_safety` è una **stima grezza** (FCF/10%), non un DCF serio: per i
  mega-cap tech la lente `value` risulta severa per costruzione. Con `growth` il
  giudizio cambia parecchio.
- Se manca `FMP_API_KEY` **o FMP rifiuta** (402 quota giornaliera, 403 chiave),
  il provider ripiega automaticamente su yfinance: stampa `[warn] FMP non
  disponibile ...` e prosegue. yfinance ora copre conto economico + stato
  patrimoniale + cash flow, quindi le metriche restano complete (storico ~4 anni
  invece di 5). Il tier free FMP ha un limite giornaliero basso e ogni ticker
  consuma 3 chiamate.
- Solo il nodo 3 (`thesis`) esce verso internet (NVIDIA); gli altri 3 nodi sono
  deterministici e girano in locale.

## Mappa rapida dei file

| File | Cosa fa |
|---|---|
| `agent/run.py` | CLI che lanci; salva in `reports/` |
| `agent/graph.py` | monta la catena di nodi |
| `agent/nodes.py` | i 4 passi fetch/metrics/thesis/validate |
| `agent/prompts.py` | istruzioni (prompt EN) per l'LLM |
| `data/providers.py` | scarica dati (yfinance/FMP) |
| `metrics/` | i calcoli delle 4 lenti |
| `config.py` | env, ruoli modello, lente (`Settings.load`) |
