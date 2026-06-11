"""Limbic state on bind — provenance read feature only until emotional zone efferent is wired."""

from __future__ import annotations

from typing import Any

_LIMBIC_CID = "subject.limbic.state"


def limbic_state_block(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in blocks:
        if str(row.get("concept_id") or "") == _LIMBIC_CID:
            return row
    return None


def apply_affect_state_bind_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
    state: dict | None,
) -> None:
    """No hub score oracle — limbic block stays bind evidence for provenance / zones."""
    _ = blocks, query, intent, state
