#!/usr/bin/env python3
"""Register rewrite (C2) — not formal paste, facts preserved."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.semantic_read import route_kb_read


def _store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-rewrite-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Нейманн"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tmp


_C2_QUERY = (
    "Официально: Уважаемые родители! Информируем вас о переносе родительского собрания "
    "на 15 марта в 18:00 в актовом зале школы №12.\n\n"
    "Перепиши это письмо в дружеский тон для чата родителей, сохрани все факты."
)


def test_rewrite_intent_not_discuss() -> None:
    read = route_kb_read(_C2_QUERY, None)
    assert read.intent == "rewrite"


def test_rewrite_preserves_facts_not_formal() -> None:
    store = _store()
    bundle = {
        "claims": [
            {
                "concept_id": "ru.tract.rewrite",
                "slots": {
                    "requires_geometry": "passage_context",
                    "cue_substrings": "перепиш|дружеск",
                },
            },
            {
                "concept_id": "ru.meta.discourse.from_text",
                "text": "linkers",
                "slots": {"linker_2": "кстати"},
            },
        ]
    }
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(
        _C2_QUERY, None, state, WorkingMemory(), store, bundle=bundle
    )
    assert ctx.query_intent == "rewrite"
    reply = compose_subject_utterance(_C2_QUERY, ctx)
    rl = reply.lower()
    assert reply
    assert "15 марта" in rl
    assert "18:00" in rl
    assert "собран" in rl
    assert "информируем вас" not in rl
    assert "уважаемые родители" not in rl
    assert " переносе " not in f" {rl} "
