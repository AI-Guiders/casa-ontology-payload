#!/usr/bin/env python3
"""how_are_you must vary with limbic + speech-act routing — not affect clause_1 lock."""

from __future__ import annotations

import copy
from pathlib import Path

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
from casa.prisms.control.fpn_state import WorkingMemory, read_session_meta, write_session_meta
from casa.prisms.control.sn_cen_runtime import TaskEmit

AFFECT_PREAMBLE = "осторожно говорю, что чувствую в диалоге"
HOW_ARE_YOU_CLAUSE_1 = "спасибо что спросил"
HOW_ARE_YOU_CLAUSE_2 = "настроение описываю по ходу разговора"


def _task() -> TaskEmit:
    return TaskEmit(
        intent="query",
        action="answer_from_memory",
        concepts=[],
        edges=[],
        targets=[],
        query_to_dmn=None,
        confidence=0.5,
    )


def _reply(state: dict, store: Path) -> str:
    ctx = gather_subject_dialogue_blocks(
        "Как ты?",
        _task(),
        state,
        WorkingMemory(),
        store,
        compose_mode="social",
    )
    return compose_subject_utterance("Как ты?", ctx).strip()


def test_how_are_you_not_locked_to_affect_preamble() -> None:
    store = Path("agents/von-neumann")
    meta = read_session_meta(store)
    meta["dialogue_turns"] = []
    write_session_meta(store, meta)
    state = resolve_ingest_state(store, None)
    reply = _reply(state, store).lower()
    assert AFFECT_PREAMBLE not in reply
    assert HOW_ARE_YOU_CLAUSE_1 in reply or HOW_ARE_YOU_CLAUSE_2 in reply


def test_how_are_you_low_security_prefers_honest_material() -> None:
    """Limbic bias shifts bind winners — not realizer slot oracle."""
    store = Path("agents/von-neumann")
    meta = read_session_meta(store)
    meta["dialogue_turns"] = []
    write_session_meta(store, meta)

    base = resolve_ingest_state(store, None)
    low = copy.deepcopy(base)
    spawn_emotional_zone(low, tick=1)
    affect_after_turn(low, "security_threat", tick=2)

    ctx = gather_subject_dialogue_blocks(
        "Как ты?",
        TaskEmit(
            intent="query",
            action="answer_from_memory",
            concepts=[],
            edges=[],
            targets=[],
            query_to_dmn=None,
            confidence=0.5,
        ),
        low,
        WorkingMemory(),
        store,
        compose_mode="social",
    )
    top_cid = str(ctx.blocks[0].get("concept_id") or "")
    assert top_cid.startswith("ru.dialog.how_are_you") or top_cid.startswith("ru.dialog.honest")
    assert AFFECT_PREAMBLE not in _reply(low, store).lower()
