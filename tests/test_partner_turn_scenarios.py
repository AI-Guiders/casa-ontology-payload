#!/usr/bin/env python3
"""Partner turns from chat — no echo, phatic acts route to one hub."""

from __future__ import annotations

import copy
from pathlib import Path

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory, read_session_meta, write_session_meta
from casa.prisms.control.sn_cen_runtime import TaskEmit


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


def _reply(query: str, state: dict, store: Path) -> str:
    ctx = gather_subject_dialogue_blocks(
        query, _task(), state, WorkingMemory(), store, compose_mode="social"
    )
    return compose_subject_utterance(query, ctx).strip()


def _fresh_store() -> tuple[Path, dict]:
    store = Path("agents/von-neumann")
    meta = read_session_meta(store)
    meta["dialogue_turns"] = []
    write_session_meta(store, meta)
    return store, resolve_ingest_state(store, None)


def test_how_are_you_variant_not_echo() -> None:
    store, state = _fresh_store()
    reply = _reply("Как у тебя дела?", state, store).lower()
    assert "да —" not in reply
    assert "как у тебя дела" not in reply
    assert "спасибо" in reply or "настроение" in reply or "хорош" in reply


def test_intro_not_echo_partner_line() -> None:
    store, state = _fresh_store()
    reply = _reply("Приятно познакомиться, я Света", state, store).lower()
    assert "да —" not in reply
    assert "приятно познакомиться, я света" not in reply
    assert "привет" in reply or "здравств" in reply or "нейманн" in reply
