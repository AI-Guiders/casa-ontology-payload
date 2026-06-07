#!/usr/bin/env python3
"""Passage why → discuss tract; weekday facts in rewrite."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.semantic_read import route_kb_read


def _store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-open-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Нейманн"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tmp


_WHY_QUERY = (
    "Соседка принесла пирог, но дверь была закрыта. Она оставила записку и ушла.\n\n"
    "Почему она могла уйти, не дождавшись? Объясни по тексту."
)

_REGISTER_QUERY = (
    "Уважаемые родители! Собрание перенесли на среду.\n\n"
    "Перепиши это сообщение для чата класса — коротко и по-человечески, факты сохрани."
)


def test_why_passage_prefers_discuss_tract() -> None:
    read = route_kb_read(_WHY_QUERY, None)
    assert read.intent == "discuss"


def test_why_passage_reply_not_empty() -> None:
    store = _store()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(_WHY_QUERY, None, state, WorkingMemory(), store, bundle=None)
    reply = compose_subject_utterance(_WHY_QUERY, ctx)
    assert reply.strip()
    rl = reply.lower()
    assert any(m in rl for m in ("двер", "записк", "ушл", "закрыт"))


def test_rewrite_short_notice_preserves_weekday() -> None:
    store = _store()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(_REGISTER_QUERY, None, state, WorkingMemory(), store, bundle=None)
    assert ctx.query_intent == "rewrite"
    reply = compose_subject_utterance(_REGISTER_QUERY, ctx)
    rl = reply.lower()
    assert reply
    assert "сред" in rl
    assert "собран" in rl
