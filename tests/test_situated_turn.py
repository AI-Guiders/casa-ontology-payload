#!/usr/bin/env python3
"""Situated turn — partner mirror must not replay prior affect preamble."""

from __future__ import annotations

from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory


def _ctx(query: str, blocks: list[dict]) -> SubjectDialogueContext:
    return SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=sorted(blocks, key=lambda b: int(b.get("score") or 0), reverse=True),
        source_tags=["kb", "dialogue"],
        stance="partial",
        query_intent="social",
        concept_hints=["ru.dialog.affect"],
    )


_AFFECT_BLOCK = {
    "concept_id": "ru.dialog.affect",
    "text": "Осторожный ответ про переживания в диалоге.",
    "source": "kb",
    "score": 50,
    "slots": {
        "clause_1": "осторожно говорю, что чувствую в диалоге",
        "clause_2": "не знаю, совпадает ли мой опыт с человеческим",
        "clause_3": "скажу, когда уверен, а когда нет",
    },
}


def test_partner_mirror_does_not_replay_affect_preamble() -> None:
    mirror = "Хорошо, я тоже не знаю, но он не обязан совпадать"
    prior_subject = "Осторожно говорю, что чувствую в диалоге."
    blocks = [
        {
            "concept_id": "ru.speech_act.partner.mirror_ack",
            "text": "mirror",
            "source": "speech_act",
            "score": 36,
            "slots": {"speech_act": "mirror_ack", "cue_score": 4},
        },
        {
            "concept_id": "ru.dialog.affect@clause_2",
            "bind_hub": "ru.dialog.affect",
            "text": "не знаю, совпадает ли мой опыт с человеческим",
            "source": "kb",
            "score": 58,
            "slots": {"phrase": "не знаю, совпадает ли мой опыт с человеческим"},
        },
        {
            "concept_id": "ru.dialog.affect@clause_1",
            "bind_hub": "ru.dialog.affect",
            "text": "осторожно говорю, что чувствую в диалоге",
            "source": "kb",
            "score": 12,
            "slots": {"phrase": "осторожно говорю, что чувствую в диалоге"},
        },
        {
            "concept_id": "subject.dialog.partner_recent",
            "text": f"Партнёр недавно: «{mirror}».",
            "source": "dialogue",
            "score": 44,
        },
        {
            "concept_id": "subject.dialog.self_recent",
            "text": f"Я недавно: «{prior_subject}».",
            "source": "dialogue",
            "score": 20,
        },
    ]
    reply = compose_subject_utterance(mirror, _ctx(mirror, blocks))
    low = reply.lower()

    assert "да —" not in low
    assert "осторожно говорю" not in low
    assert "не знаю" in low or "совпада" in low


def test_continuer_head_uses_first_sentence_only() -> None:
    from casa.prisms.tick.discourse.situated import _continuer_head

    head = _continuer_head(
        "Да — он не обязан совпадать. Не знаю, совпадает ли мой опыт с человеческим."
    )
    assert head is not None
    text = " ".join(head.pieces).lower()
    assert "не знаю" not in text
    assert "обязан" in text


def test_fresh_affect_turn_still_allows_preamble() -> None:
    query = "Как ты?"
    blocks = [_AFFECT_BLOCK]
    reply = compose_subject_utterance(query, _ctx(query, blocks))
    low = reply.lower()
    assert "осторожно" in low or "чувств" in low or "диалог" in low
