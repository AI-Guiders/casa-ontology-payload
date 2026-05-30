#!/usr/bin/env python3
"""CEN LLM hook stub — optional probe when SN is in probe mode (not on hot path)."""

from __future__ import annotations


def maybe_llm_probe(query: str | None, *, enabled: bool = False) -> dict | None:
    """
    Return None on hot path (default). When enabled, caller may route to Ollama/OpenAI later.
    """
    if not enabled or not query:
        return None
    return {
        "provider": "stub",
        "query": query[:500],
        "note": "LLM hook not wired; use --llm-enable when CEN v2 backend is configured",
    }
