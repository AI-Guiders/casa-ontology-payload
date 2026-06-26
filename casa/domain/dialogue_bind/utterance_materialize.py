"""Materialize ru.dialog hub slots into competing utterance blocks at bind — not compose."""

from __future__ import annotations

from typing import Any


def materialize_dialog_utterances(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
) -> None:
    """ADR-0081: ru.dialog hubs are lexical/situation pieces — no clause_* competition."""
    return
