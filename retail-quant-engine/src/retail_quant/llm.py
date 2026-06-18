"""Cablaggio NVIDIA build via langchain-openai.

Le API di NVIDIA sono OpenAI-compatible: basta puntare base_url + api_key.
Esponiamo due "ruoli" (orchestratore/estrattore) come da TODO Fase 1.
"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from .config import NVIDIA_BASE_URL, Settings


def _make(model: str, settings: Settings, temperature: float) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=settings.nvidia_api_key,
        base_url=NVIDIA_BASE_URL,
        temperature=temperature,
    )


def orchestrator_llm(settings: Settings, temperature: float = 0.2) -> ChatOpenAI:
    """Modello grande per tesi/ragionamento/strategia."""
    return _make(settings.model_orchestrator, settings, temperature)


def extractor_llm(settings: Settings, temperature: float = 0.0) -> ChatOpenAI:
    """Modello per parsing/estrazione: temperatura 0 per output deterministico."""
    return _make(settings.model_extractor, settings, temperature)
