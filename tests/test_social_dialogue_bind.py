#!/usr/bin/env python3
"""Social dialogue bind — speech situation via semantic_read + bind, not lexicon lists."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn
from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.subject_mode import apply_subject_profile
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.domain.dialogue_bind.scoring import partner_self_label, social_dialog_slot_allowed
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.shared.store_bundles import load_store_bundles
from casa.prisms.tick.semantic_read import route_kb_read


def _dialogue_store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-social-dialog-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Нейманн"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (tmp / "bundles").mkdir()
    for bundle in (REPO_ROOT / "agents" / "von-neumann" / "bundles").glob("*.bundle.json"):
        shutil.copy(bundle, tmp / "bundles" / bundle.name)
    return tmp


def _task() -> TaskEmit:
    return TaskEmit(
        intent="query",
        action="answer_from_memory",
        concepts=[],
        edges=[],
        targets=[],
        query_to_dmn=None,
        confidence=0.5,
        answer_blocks=(),
        answer_text="",
    )


def test_speech_situation_from_semantic_read() -> None:
    bundle = load_store_bundles(_dialogue_store())
    here = route_kb_read("Как тебе здесь?", bundle)
    assert "ru.dialog.affect" in here.concept_hints
    assert social_dialog_slot_allowed("ru.dialog.self", concept_hints=here.concept_hints) is False
    assert social_dialog_slot_allowed("ru.dialog.how_are_you", concept_hints=here.concept_hints) is False

    mood = route_kb_read("как раз учу", bundle)
    assert "ru.dialog.affect" not in mood.concept_hints

    assert partner_self_label("Я знаю. Я Света, учу тебя") == "Света"


def test_sveta_repl_transcript() -> None:
    store = _dialogue_store()
    state = resolve_ingest_state(store, None)
    apply_subject_profile(store, state)
    wm = WorkingMemory(tick=0)
    bundle = load_store_bundles(store)
    task = _task()

    def say(partner: str) -> str:
        append_partner_turn(store, partner, provenance={"source": "test"})
        ctx = gather_subject_dialogue_blocks(partner, task, state, wm, store, bundle=bundle)
        reply = compose_subject_utterance(partner, ctx)
        append_subject_turn(store, reply, kind="reply", provenance={"source": "test"})
        return reply

    assert say("привет").strip() == "Привет."

    here = say("Как тебе здесь?")
    assert "Я Нейманн" not in here
    assert "настроение" not in here.lower()

    intro = say("Я знаю. Я Света, я вместе с кучой LLM тебя как раз учу)")
    assert "спасибо что спросил" not in intro.lower()
    assert "настроение по-человечески не чувствую" not in intro.lower()
    assert "Я Нейманн" not in intro


def test_greeting_and_mood_same_turn() -> None:
    store = _dialogue_store()
    state = resolve_ingest_state(store, None)
    apply_subject_profile(store, state)
    bundle = load_store_bundles(store)
    task = _task()
    q = "Привет! Как ты?"
    ctx = gather_subject_dialogue_blocks(q, task, state, WorkingMemory(tick=0), store, bundle=bundle)
    reply = compose_subject_utterance(q, ctx)
    low = reply.lower()
    assert "привет" in low
    assert "спасибо что спросил" not in low
    assert "чувства" in low or "линия диалога" in low or "уверен" in low
