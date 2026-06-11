#!/usr/bin/env python3
"""Limbic state bind bias — ADR-0058 wire on social how_are_you."""

from __future__ import annotations

from casa.domain.dialogue_bind.affect_scoring import apply_affect_state_bind_deltas
from casa.domain.dialogue_bind.scoring import reweight_blocks_for_reply
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
from casa.prisms.control.fpn_state import WorkingMemory


def _state_repair_pending() -> dict:
    state: dict = {}
    spawn_emotional_zone(state, tick=1)
    affect_after_turn(state, "self_failure", tick=2)
    return state


def test_repair_boosts_honest_over_capabilities() -> None:
    state = _state_repair_pending()
    blocks = [
        {
            "concept_id": "ru.dialog.honest.partial",
            "text": "honest",
            "source": "kb",
            "score": 40,
        },
        {
            "concept_id": "ru.dialog.capabilities",
            "text": "cap",
            "source": "kb",
            "score": 45,
        },
        {
            "concept_id": "ru.speech_act.partner.how_are_you",
            "text": "how",
            "source": "speech_act",
            "score": 30,
            "slots": {"speech_act": "how_are_you"},
        },
    ]
    reweight_blocks_for_reply(
        blocks,
        "Как ты?",
        kb_hits=[],
        intent="social",
        state=state,
        concept_hints=["ru.dialog.affect"],
    )
    honest = next(b for b in blocks if b["concept_id"].startswith("ru.dialog.honest"))
    assert int(honest["score"]) >= 64
    assert not any(b["concept_id"].startswith("ru.dialog.capabilities") for b in blocks)


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
