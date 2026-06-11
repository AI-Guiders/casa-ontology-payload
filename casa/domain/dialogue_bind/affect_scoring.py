"""Limbic state → bind/budget bias on social turns (ADR-0057/0058), not efferent phrases."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.speech_act_scoring import _active_speech_acts
from casa.prisms.memory.concept_layer import discourse_concept_id

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
    if intent != "social" or state is None:
        return
    try:
        from casa.prisms.affect import affect_compose_bias, core_affect_state
    except ImportError:
        return

    bias = affect_compose_bias(state)
    axes = core_affect_state(state).axes.clamped()
    acts = _active_speech_acts(blocks)
    act = acts[0] if acts else ""

    for row in blocks:
        disc = discourse_concept_id(row)
        delta = 0

        if bias.get("repair_pending"):
            if disc.startswith("ru.dialog.honest"):
                delta += 24
            if disc.startswith("ru.dialog.capabilities"):
                delta -= 28
            if disc.startswith("ru.dialog.greeting"):
                delta -= 16

        if act in ("how_are_you", "greeting"):
            if axes.security < 0.42:
                if disc.startswith("ru.dialog.honest"):
                    delta += 18
                if disc.startswith("ru.dialog.how_are_you"):
                    delta += 14
            elif axes.security >= 0.58:
                if disc.startswith("ru.dialog.self"):
                    delta += 16
                if disc.startswith("ru.dialog.how_are_you"):
                    delta += 12
            if axes.valence < -0.08:
                if disc.startswith("ru.dialog.honest"):
                    delta += 12
            if axes.arousal > 0.5 and axes.security < 0.5:
                if disc.startswith("ru.dialog.affect.overload"):
                    delta += 20

        if delta:
            row["score"] = int(row.get("score") or 0) + delta
