#!/usr/bin/env python3
"""Partner speech act — read/bind feature, not efferent templates."""

from __future__ import annotations

from casa.domain.dialogue_bind import SubjectDialogueContext, gather_subject_dialogue_blocks
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.tick.partner_speech_act import (
    resolve_partner_speech_act,
    resolve_partner_speech_act_claim,
)


def test_ask_thought_act() -> None:
    act = resolve_partner_speech_act("А что ты думаешь про это?")
    assert act == "ask_thought"


def test_mirror_act() -> None:
    q = "Хорошо, я тоже не знаю, но он не обязан совпадать"
    assert resolve_partner_speech_act(q) == "mirror_ack"


def test_how_are_you_act() -> None:
    assert resolve_partner_speech_act("Как ты?") == "how_are_you"


def test_speech_act_claim_has_bind_fields() -> None:
    claim = resolve_partner_speech_act_claim("Спасибо")
    assert claim is not None
    slots = claim.get("slots") or {}
    assert slots.get("speech_act") == "thanks"
    assert int(slots.get("cue_score") or 0) > 0


def test_gather_includes_speech_act_block() -> None:
    q = "Как ты?"
    task = TaskEmit(
        intent="query",
        action="answer_from_memory",
        concepts=[],
        edges=[],
        targets=[],
        query_to_dmn=None,
        confidence=0.5,
    )
    ctx = gather_subject_dialogue_blocks(
        q,
        task,
        {},
        WorkingMemory(),
        None,
        compose_mode="social",
    )
    speech = [
        b for b in ctx.blocks if str(b.get("concept_id") or "").startswith("ru.speech_act.partner.")
    ]
    assert speech
    prov = meaning_provenance(ctx)
    assert prov.get("partner_speech_acts") == ["how_are_you"]


def test_ask_thought_reply_uses_bind_not_template() -> None:
    affect = {
        "concept_id": "ru.dialog.affect",
        "text": "Affect hub.",
        "source": "kb",
        "score": 50,
        "slots": {
            "clause_1": "осторожно говорю, что чувствую в диалоге",
            "clause_2": "не знаю, совпадает ли мой опыт с человеческим",
            "clause_3": "скажу, когда уверен, а когда нет",
        },
    }
    blocks = [
        affect,
        {
            "concept_id": "ru.speech_act.partner.ask_thought",
            "text": "Partner asks subject's thought or opinion",
            "source": "speech_act",
            "score": 30,
            "slots": {"speech_act": "ask_thought", "cue_score": 8},
        },
        {
            "concept_id": "subject.dialog.partner_recent",
            "text": "Партнёр недавно: «А что ты думаешь про это?».",
            "source": "dialogue",
            "score": 80,
        },
        {
            "concept_id": "subject.dialog.self_recent",
            "text": "Я недавно: «Да — он не обязан совпадать.».",
            "source": "dialogue",
            "score": 60,
        },
    ]
    ctx = SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=sorted(blocks, key=lambda b: -int(b.get("score") or 0)),
        source_tags=["kb", "dialogue", "speech_act"],
        stance="partial",
        query_intent="social",
        concept_hints=["ru.dialog.affect"],
    )
    q = "А что ты думаешь про это?"
    reply = compose_subject_utterance(q, ctx)
    low = reply.lower()
    assert reply.strip()
    assert "осторожно говорю" not in low
    assert meaning_provenance(ctx).get("partner_speech_acts") == ["ask_thought"]


def test_mirror_acknowledges_shared_uncertainty() -> None:
    affect = {
        "concept_id": "ru.dialog.affect",
        "text": "Affect.",
        "source": "kb",
        "score": 50,
        "slots": {
            "clause_1": "осторожно говорю, что чувствую в диалоге",
            "clause_2": "не знаю, совпадает ли мой опыт с человеческим",
        },
    }
    mirror = "Хорошо, я тоже не знаю, но он не обязан совпадать"
    blocks = [
        affect,
        {
            "concept_id": "ru.speech_act.partner.mirror",
            "text": "Partner aligns / mirrors prior thread",
            "source": "speech_act",
            "score": 30,
            "slots": {"speech_act": "mirror_ack", "cue_score": 8},
        },
        {
            "concept_id": "subject.dialog.partner_recent",
            "text": f"Партнёр недавно: «{mirror}».",
            "source": "dialogue",
            "score": 80,
        },
        {
            "concept_id": "subject.dialog.self_recent",
            "text": "Я недавно: «Осторожно говорю, что чувствую в диалоге.».",
            "source": "dialogue",
            "score": 40,
        },
    ]
    ctx = SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=sorted(blocks, key=lambda b: -int(b.get("score") or 0)),
        source_tags=["kb", "dialogue", "speech_act"],
        stance="partial",
        query_intent="social",
        concept_hints=["ru.dialog.affect"],
    )
    reply = compose_subject_utterance(mirror, ctx)
    low = reply.lower()
    assert "не знаю" in low or "обязан" in low or "совпада" in low
    assert "не знаю, совпадает ли мой опыт с человеческим" not in low
