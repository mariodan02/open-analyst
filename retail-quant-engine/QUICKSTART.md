# Quick Start — Fase 1 (analisi di un singolo titolo)

Guida rapida per analizzare un ticker.

> ⚠️ **Il comando che fa l'analisi è `agent.run`.** `smoke_test` mostra solo
> dati e metriche e **NON** chiama l'IA — è un controllo, non l'analisi.

## 0. Prerequisiti (una volta sola)

```bash
cd retail-quant-engine
source .venv/bin/activate
```
---

## ▶️ Analizzare un ticker (il comando principale)

```bash
python -m retail_quant.agent.run GOOG
# ETF: aggiungi l'ISIN per il profilo justETF (TER, accumulazione/distribuzione)
python -m retail_quant.agent.run VWCE.MI --isin IE00BK5BQT80
```

- Esegue `fetch → metrics → thesis (LLM) → validate`.
- **ETF riconosciuti in automatico**: saltano bilanci e calcoli da azione; la
  tesi è scritta da un prompt dedicato (costo/struttura/diversificazione) sui
  dati justETF, non un DCF inapplicabile.
- Tempo tipico: ~60–70s (DeepSeek su NVIDIA).
- Salva il report in `reports/<TICKER>-<lente>-<data>.md` e lo stampa a video.

---

## ⚖️ Comps — valutazione relativa vs pari (Fase extra)

```bash
# primo ticker = target, gli altri = pari; niente LLM, solo numeri
python -m retail_quant.comps.run AAPL MSFT GOOGL META
```
Tabella di P/E, P/S e margini, mediana dei pari e verdetto (più caro/economico).

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

## 🐕 Monitoraggio del portafoglio (Fase 3)

```bash
# copia il modello e mettici i tuoi titoli, poi:
python -m retail_quant.monitor.run --file portfolio.json
```

- Calcola P/L vs prezzo di carico e avvisa solo sui **cambiamenti** (prezzo,
  nuovo bilancio con variazioni YoY ricavi/utile/margine, perdita oltre soglia).
  Stato persistito in `state/`.
- **Tesi d'acquisto** (opzionale): aggiungi `thesis` a un titolo e il monitor
  avvisa se le ipotesi si rompono (es. P/E oltre il tuo max, crescita sotto il
  minimo, moat sceso):

```json
{"ticker": "AAPL", "shares": 10, "cost_basis": 150.0,
 "thesis": {"max_pe": 35, "min_revenue_growth_pct": 3, "min_moat_rating": "wide"}}
```
- **ETF**: riconosciuti in automatico (saltano i conti da azione). Aggiungi
  l'`isin` nel JSON per il profilo justETF (TER, accumulazione/distribuzione):

```json
{"ticker": "VWCE.MI", "shares": 6, "cost_basis": 151.27, "isin": "IE00BK5BQT80"}
```

---

## Note / gotcha

- `margin_of_safety` è un **DCF reale** (FCF unlevered con crescita calante, WACC
  via CAPM, valore terminale di Gordon): per i mega-cap tech la lente `value`
  resta severa per costruzione. Con `growth` il giudizio cambia parecchio.
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
