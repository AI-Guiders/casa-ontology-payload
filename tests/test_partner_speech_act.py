#!/usr/bin/env python3
"""Partner speech act — read/bind feature, not efferent templates."""

from __future__ import annotations

import pytest

from casa.domain.dialogue_bind import SubjectDialogueContext, gather_subject_dialogue_blocks
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.tick.partner_speech_act import (
    resolve_partner_speech_act,
    resolve_partner_speech_act_claim,
)


def _compose_social(query: str, blocks: list[dict]) -> tuple[SubjectDialogueContext, str]:
    from casa.domain.dialogue_bind.scoring import reweight_blocks_for_reply

    rows = [dict(b) for b in blocks]
    reweight_blocks_for_reply(rows, query, kb_hits=[], intent="social")
    ctx = SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=rows,
        source_tags=["kb", "dialogue", "speech_act"],
        stance="partial",
        query_intent="social",
    )
    return ctx, compose_subject_utterance(query, ctx)


def test_compose_single_hub_ignored_for_efferent() -> None:
    from casa.domain.dialogue_bind.speech_act_scoring import compose_single_hub_from_bind

    blocks = [
        {
            "concept_id": "ru.speech_act.partner.how_are_you",
            "source": "speech_act",
            "score": 50,
            "slots": {"speech_act": "how_are_you", "compose_single_hub": "true"},
        },
    ]
    assert not compose_single_hub_from_bind(blocks)


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
    claim = resolve_partner_speech_act_claim("А что ты думаешь про это?")
    assert claim is not None
    self_hub = {
        "concept_id": "ru.dialog.self",
        "text": "Self hub.",
        "source": "kb",
        "score": 85,
        "slots": {
            "situation": "partner_asks_opinion",
            "hedge": "учусь",
            "predicate": "говорить",
            "scope": "по-русски",
        },
    }
    blocks = [
        self_hub,
        {
            "concept_id": str(claim.get("concept_id") or "ru.speech_act.partner.ask_thought"),
            "text": str(claim.get("text") or ""),
            "source": "speech_act",
            "score": 30,
            "slots": dict(claim.get("slots") or {}),
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
    q = "А что ты думаешь про это?"
    ctx, reply = _compose_social(q, blocks)
    low = reply.lower()
    assert reply.strip()
    assert "осторожно говорю" not in low
    assert meaning_provenance(ctx).get("partner_speech_acts") == ["ask_thought"]


@pytest.mark.skip(
    reason=(
        "Oracle efferent: expects composed self speech from ru.dialog.self slots; "
        "field-native reply path is under construction on fix/neumann-free-speech-recovery."
    )
)
def test_mirror_acknowledges_shared_uncertainty() -> None:
    claim = resolve_partner_speech_act_claim(
        "Хорошо, я тоже не знаю, но он не обязан совпадать"
    )
    assert claim is not None
    self_hub = {
        "concept_id": "ru.dialog.self",
        "text": "Self.",
        "source": "kb",
        "score": 82,
        "slots": {
            "situation": "mirror_ack",
            "hedge": "согласен",
            "predicate": "отвечаю",
            "scope": "своими словами",
        },
    }
    mirror = "Хорошо, я тоже не знаю, но он не обязан совпадать"
    blocks = [
        self_hub,
        {
            "concept_id": str(claim.get("concept_id") or "ru.speech_act.partner.mirror"),
            "text": str(claim.get("text") or ""),
            "source": "speech_act",
            "score": 30,
            "slots": dict(claim.get("slots") or {}),
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
    _, reply = _compose_social(mirror, blocks)
    low = reply.lower()
    assert "осторожно говорю" not in low
    assert "не знаю, совпадает ли мой опыт с человеческим" not in low
    assert "скажу" in low or "своими словами" in low or "отвечаю" in low
