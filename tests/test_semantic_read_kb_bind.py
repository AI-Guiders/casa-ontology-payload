#!/usr/bin/env python3
"""semantic_read + subject KB bind tests."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.shared.store_bundles import load_store_bundles
from casa.prisms.tick.semantic_read import classify_query_intent, route_kb_read


def test_merge_von_neumann_bundles():
    root = Path(__file__).resolve().parents[1]
    store = root / "agents" / "von-neumann"
    if not (store / "bundles").is_dir():
        return
    merged = load_store_bundles(store)
    assert len(merged.get("claims") or []) >= 120
    assert len(merged.get("bundle_ids") or []) >= 2


def test_math_surface_routes_kb():
    root = Path(__file__).resolve().parents[1]
    store = root / "agents" / "von-neumann"
    if not (store / "bundles").is_dir():
        return
    bundle = load_store_bundles(store)
    read = route_kb_read("||| + ||", bundle)
    assert read.intent == "math"
    assert "math_glyph" in read.locales
    assert "math.num.three" in read.concept_hints
    assert "math.op.add" in read.concept_hints
    assert any(str(c.get("concept_id", "")).startswith("math.") for c, _ in read.kb_hits)


def test_grammar_without_kb_is_honest_partial():
    tmp = Path(tempfile.mkdtemp(prefix="casa-grammar-honest-"))
    try:
        (tmp / "bundles").mkdir()
        (tmp / "bundles" / "empty.json").write_text(
            json.dumps({"bundle_id": "empty", "claims": []}), encoding="utf-8"
        )
        ctx = gather_subject_dialogue_blocks(
            "Согласно приказа верно?",
            None,
            {"field_version": 1},
            WorkingMemory(),
            tmp,
        )
        assert ctx.query_intent == "grammar"
        reply = compose_subject_utterance("Согласно приказа верно?", ctx)
        assert ctx.stance in ("partial", "unknown", "confident")
        assert "дательный" not in reply.lower()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_math_reply_uses_kb_not_journal():
    root = Path(__file__).resolve().parents[1]
    store = root / "agents" / "von-neumann"
    if not (store / "bundles").is_dir():
        return
    ctx = gather_subject_dialogue_blocks(
        "||| + ||",
        None,
        {"field_version": 1, "subject": {}},
        WorkingMemory(),
        store,
    )
    top = ctx.blocks[0] if ctx.blocks else {}
    assert top.get("source") == "kb" or str(top.get("concept_id", "")).startswith("math.")
    reply = compose_subject_utterance("||| + ||", ctx)
    assert "На поле (math)" in reply
    assert "журнал (Self tier)" not in reply
