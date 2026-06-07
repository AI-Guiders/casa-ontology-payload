#!/usr/bin/env python3
"""Emergent discourse — bind relevance and dedupe, not teacher length caps."""

from __future__ import annotations

import tempfile
from pathlib import Path


def test_field_recall_reply_excerpt_not_midword() -> None:
    from casa.cli.ingest_verbal_moment import _reply_excerpt

    long = "Между двумя кучками есть промежуток — пустое место на поле."
    ex = _reply_excerpt(long * 5, limit=200)
    assert ex.endswith("…")
    assert not ex.endswith(" на по")


def test_compare_query_emergent_no_verbatim_loops() -> None:
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.memory.agent_memory_ops import agent_remember
    from casa.prisms.shared.store_lock import store_session_lock

    tmp = Path(tempfile.mkdtemp(prefix="casa-recall-emergent-"))
    (tmp / "store_profile.json").write_text(
        '{"subject_mode": true, "display_name": "Тест"}',
        encoding="utf-8",
    )
    q = "Сравни: где палочек больше, где меньше? Скажи своими словами."
    with store_session_lock(tmp, holder="test"):
        state = resolve_ingest_state(tmp, None)
        for text in (
            "Слева палочек больше, справа меньше — так я это увидел на поле.",
            "Слева палочек больше, справа меньше — я это заfиксировал как сравнение на поле.",
            "Между двумя кучками есть промежуток — пустое место на поле.",
        ):
            agent_remember(
                tmp,
                state,
                {"kind": "observation", "text": text, "tags": ["test"]},
                scope="self",
            )
        ctx = gather_subject_dialogue_blocks(q, None, state, WorkingMemory(), tmp, bundle=None)
        assert ctx.query_intent == "explain"
        reply = compose_subject_utterance(q, ctx)
        rl = reply.lower()
        assert "больш" in rl and "меньш" in rl
        sents = [s.strip().lower() for s in reply.split(".") if s.strip()]
        assert len(sents) == len(set(sents))


def test_von_neumann_compare_uses_explain_intent() -> None:
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock

    store = Path(__file__).resolve().parents[1] / "agents/von-neumann"
    if not store.is_dir():
        return
    q = "Сравни: где палочек больше, где меньше? Скажи своими словами."
    with store_session_lock(store, holder="test"):
        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        ctx = gather_subject_dialogue_blocks(q, None, state, WorkingMemory(), store, bundle=bundle)
        assert ctx.query_intent == "explain"
        reply = compose_subject_utterance(q, ctx)
        assert reply.strip()
        assert "больш" in reply.lower()
