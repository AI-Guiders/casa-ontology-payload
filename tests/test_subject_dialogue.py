#!/usr/bin/env python3
"""Subject dialogue — field/journal bind + articulate (ADR-0045 full path)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.subject_dialogue_bind import gather_subject_dialogue_blocks
from casa.domain.subject_voice import compose_subject_partner_reply
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import AnswerBlock, TaskEmit
from casa.prisms.memory.agent_journal import append_journal_entry


def _tmp_store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-subject-dialogue-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "von-neumann-test"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    append_journal_entry(
        tmp,
        {
            "kind": "note",
            "text": "Я — von-neumann-test. Это мой журнал Self tier — черновики и гипотезы на поле.",
            "tags": ["bootstrap", "notebook:self"],
            "meta": {"notebook": "self", "scope": "self"},
        },
        domain="self",
    )
    return tmp


def test_greeting_from_journal_not_hardcoded_template():
    tmp = _tmp_store()
    try:
        state = {"field_version": 7, "subject": {"subject_mode": True}, "store": {"store_id": "von-neumann-test"}}
        wm = WorkingMemory(tick=3)
        reply = compose_subject_partner_reply("Привет!", None, state, wm, store_dir=tmp)
        assert "language store нет болтовни" not in reply
        assert "помощник по русскому" not in reply.lower()
        assert "не paste claim" in reply
        assert "von-neumann-test" in reply or "журнал" in reply.lower()
        assert "headless worker" not in reply
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cen_blocks_woven_into_reply():
    tmp = _tmp_store()
    try:
        state = {"field_version": 1, "subject": {"subject_mode": True}}
        wm = WorkingMemory()
        task = TaskEmit(
            intent="query",
            action="answer_from_memory",
            concepts=["ru.grammar.punct.comma"],
            edges=[],
            targets=[],
            query_to_dmn=None,
            confidence=0.8,
            answer_blocks=(
                AnswerBlock(
                    concept_id="ru.grammar.punct.comma",
                    text="Правильно: запятая перед придаточным с «что».",
                    section="grammar",
                    doc_path="kb",
                    score=20,
                ),
            ),
        )
        ctx = gather_subject_dialogue_blocks("Нужна ли запятая в «я знаю что он придёт»?", task, state, wm, tmp)
        assert any("ru.grammar" in str(b.get("concept_id")) for b in ctx.blocks)
        reply = compose_subject_utterance("Нужна ли запятая в «я знаю что он придёт»?", ctx)
        assert "запят" in reply.lower() or "придаточ" in reply.lower()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_soft_miss_honest_without_template_ban():
    tmp = _tmp_store()
    try:
        state = {"field_version": 0, "subject": {"subject_mode": True}}
        reply = compose_subject_partner_reply(
            "Расскажи про квантовую гравитацию",
            TaskEmit("query", "answer_from_memory", [], [], [], None, 0.2),
            state,
            WorkingMemory(),
            store_dir=tmp,
        )
        assert "Console" not in reply
        assert "не paste claim" in reply
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
