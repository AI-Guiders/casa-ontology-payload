"""Lexicon usage axes materialized on L3 — field-only T9 oracle."""

from __future__ import annotations

from casa.prisms.memory.lexicon_field_oracle import (
    lexicon_oracle_for_predict,
    lexicon_oracle_from_l3,
    sync_lexicon_axes_to_field,
)
from casa.prisms.memory.lexicon_usage_axes import attach_axes_to_state, axis_record
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.ru_lexicon import ingest_ru_lex_batch
from casa.prisms.tick.predictor import l2_prefix_candidates


def test_axes_materialize_on_l3_and_predict_uses_field() -> None:
    state = ensure_prisms({})
    ingest_ru_lex_batch(state, ["мама", "мамаша"], copies=3, configure=True)
    axes = {
        "мама": axis_record("мама", era="modern", usage_band="active", ipm=100.0, rank=10),
        "мамаша": axis_record("мамаша", era="archaic", usage_band="unused", active_for_t9=False),
    }
    attach_axes_to_state(state, axes, materialize_field=True)
    field = lexicon_oracle_from_l3(state)
    assert "мама" in field
    assert field["мама"]["ipm"] == 100.0

    # Predict path reads L3 oracle, not a separate sidecar dict only
    state.pop("lexicon_axes", None)
    oracle = lexicon_oracle_for_predict(state)
    assert oracle["мама"]["rank"] == 10

    ranked = l2_prefix_candidates(state, "мам", top_k=4, t9_policy="prod")
    words = [w for w, _ in ranked]
    assert "мама" in words
    assert "мамаша" not in words


def test_sync_skips_existing_lemmas() -> None:
    state = ensure_prisms({})
    ingest_ru_lex_batch(state, ["кот"], copies=2, configure=False)
    row = axis_record("кот", ipm=5.0, rank=100)
    n1 = sync_lexicon_axes_to_field(state, {"кот": row})
    n2 = sync_lexicon_axes_to_field(state, {"кот": row})
    assert n1 == 1
    assert n2 == 0
