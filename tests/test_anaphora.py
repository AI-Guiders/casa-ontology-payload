#!/usr/bin/env python3
"""Anaphora — deictic gating and referent blocks."""

from __future__ import annotations

from pathlib import Path

from casa.domain.dialogue_bind.anaphora import (
    anaphora_referent_blocks,
    query_has_deictic,
    recent_ring_referent,
)
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn
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


def test_deictic_vs_introspective() -> None:
    assert query_has_deictic("А что ты думаешь про это?")
    assert not query_has_deictic("О чём ты думаешь?")


def test_referent_block_only_on_deictic(tmp_path: Path) -> None:
    store = tmp_path / "agent"
    store.mkdir()
    (store / "bundles").mkdir()
    meta = {"dialogue_turns": []}
    write_session_meta(store, meta)
    append_partner_turn(
        store,
        "Хорошо, опыт не обязан совпадать",
        provenance={"prop_ids": ["ru.prop.partner.experience"]},
    )
    assert anaphora_referent_blocks(store, "О чём думаешь?") == []
    blocks = anaphora_referent_blocks(store, "Что думаешь про это?")
    assert blocks and blocks[0]["concept_id"] == "dialog.context.referent"
    ref, _, _ = recent_ring_referent(store)
    assert ref == "ru.prop.partner.experience"


def test_gather_includes_referent_on_deictic(tmp_path: Path) -> None:
    store = tmp_path / "agent2"
    store.mkdir()
    (store / "bundles").mkdir()
    write_session_meta(store, {"dialogue_turns": []})
    append_partner_turn(
        store,
        "Мы говорили про опыт",
        provenance={"dialog_hubs": ["ru.dialog.self"]},
    )
    append_subject_turn(store, "Согласен", kind="reply", provenance={"dialog_hubs": ["ru.dialog.self"]})
    ctx = gather_subject_dialogue_blocks(
        "А что ты думаешь про это?",
        _task(),
        {},
        WorkingMemory(),
        store,
        compose_mode="social",
    )
    cids = [str(b.get("concept_id") or "") for b in ctx.blocks]
    assert "dialog.context.referent" in cids
    assert "dialog.context.focus_recent" in cids
