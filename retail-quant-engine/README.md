# retail-quant-engine

Il **motore** di analisi finanziaria per investitore retail. "Bring Your Own Engine":
usa i prompt/skill del repo `open-analyst` come *libreria di riferimento*, ma
l'orchestrazione e le chiamate ai modelli le fa questo progetto — verso i modelli
di **NVIDIA build** (OpenAI-compatible), non verso Anthropic.

Vedi `../TODO-retail-nvidia.txt` per la roadmap completa. Questo è il contenuto
della **Fase 0 (Fondazione)** + lo scheletro pronto per la **Fase 1**.

## Cosa c'è dentro (Fase 0)

```
src/retail_quant/
  config.py        # env, ruoli modello (orchestratore/estrattore), lente attiva
  llm.py           # cablaggio NVIDIA via langchain-openai
  data/
    schemas.py     # modelli Pydantic -> output JSON stabile, chiavi in inglese
    providers.py   # fetch dati retail: yfinance + FMP
  metrics/         # gli STILI vivono qui (calcoli, non prompt)
    value.py  growth.py  dividends.py  trading.py
  tools.py         # i data provider esposti come tool, con validazione difensiva
```

Principio: **stili = calcoli diversi sugli stessi dati**; **usi = grafi diversi
sugli stessi tool**. La fondazione si costruisce una volta.

## Avvio rapido

```bash
cd retail-quant-engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # poi inserisci le tue chiavi
python -m retail_quant.smoke_test AAPL   # verifica dati + metriche (senza LLM)
```

> Nota: il codice è uno **scaffold da eseguire in locale** con le tue chiavi.
> Le funzioni dati fanno chiamate di rete reali (yfinance/FMP) e qui non sono
> state eseguite — vanno provate sulla tua macchina.

## Variabili d'ambiente

| Var | A cosa serve |
|-----|--------------|
| `NVIDIA_API_KEY` | chiave di build.nvidia.com (`nvapi-...`) |
| `FMP_API_KEY` | Financial Modeling Prep (bilanci storici) |
| `RQE_LENS` | lente metriche attiva: `value`\|`growth`\|`dividends`\|`trading` |
| `RQE_MODEL_ORCHESTRATOR` | modello per tesi/ragionamento |
| `RQE_MODEL_EXTRACTOR` | modello per parsing/estrazione |
