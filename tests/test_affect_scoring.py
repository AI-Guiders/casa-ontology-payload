#!/usr/bin/env python3
"""Limbic on bind — provenance read feature, not hub score oracle."""

from __future__ import annotations

from casa.domain.dialogue_bind.affect_scoring import apply_affect_state_bind_deltas, limbic_state_block
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
from casa.prisms.control.fpn_state import WorkingMemory


def _state_repair_pending() -> dict:
    state: dict = {}
    spawn_emotional_zone(state, tick=1)
    affect_after_turn(state, "self_failure", tick=2)
    return state


def test_affect_bind_deltas_are_noop() -> None:
    blocks = [
        {"concept_id": "ru.dialog.honest.partial", "text": "h", "source": "kb", "score": 40},
        {
            "concept_id": "subject.limbic.state",
            "text": "limbic",
            "source": "limbic",
            "score": 16,
            "slots": {"security": 0.2, "repair_pending": True},
        },
    ]
    before = int(blocks[0]["score"])
    apply_affect_state_bind_deltas(blocks, "Как ты?", intent="social", state=_state_repair_pending())
    assert int(blocks[0]["score"]) == before


def test_limbic_block_readable() -> None:
    blocks = [
        {
            "concept_id": "subject.limbic.state",
            "text": "limbic",
            "source": "limbic",
            "score": 16,
            "slots": {"valence": 0.0, "arousal": 0.2, "security": 0.5, "repair_pending": True},
        }
    ]
    row = limbic_state_block(blocks)
    assert row is not None
    assert row["slots"]["repair_pending"] is True


def test_provenance_includes_affect_axes() -> None:
    ctx = SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=[
            {
                "concept_id": "subject.limbic.state",
                "text": "limbic",
                "source": "limbic",
                "score": 16,
                "slots": {"valence": 0.0, "arousal": 0.2, "security": 0.5},
            }
        ],
        query_intent="social",
    )
    prov = meaning_provenance(ctx)
    assert prov.get("affect_axes") == {"valence": 0.0, "arousal": 0.2, "security": 0.5}
