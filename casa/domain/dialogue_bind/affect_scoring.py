"""Limbic state on bind — score nudges from affect_compose_bias (not hub oracle tuples)."""

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
    _ = query
    if not state or intent != "social":
        return
    from casa.prisms.affect import affect_compose_bias

    bias = affect_compose_bias(state)
    security = float(bias.get("security") or 0.5)
    valence = float(bias.get("valence") or 0.0)

    for block in blocks:
        cid = str(block.get("concept_id") or "")
        score = int(block.get("score") or 0)
        delta = 0

        if cid == _LIMBIC_CID:
            if security < 0.42:
                delta += 12
            elif security > 0.58:
                delta += 4
        elif cid.startswith("ru.dialog.honest."):
            if bias.get("honest_defer_bias"):
                delta += 14
        elif cid.startswith("ru.dialog.how_are_you"):
            if security >= 0.55 and valence >= 0.1:
                delta += 8
            elif security < 0.4:
                delta += 6

        if delta:
            block["score"] = score + delta
