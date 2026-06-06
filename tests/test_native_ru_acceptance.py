#!/usr/bin/env python3
"""ADR-0049 nositel′ v0 acceptance — partner cue + KB grammar (unit)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from casa.domain.native_ru_bootstrap import bootstrap_native_ru_store
from casa.domain.partner_cue_policy import (
    adjust_control_for_partner_cue,
    skip_hippo_surprise_for_partner_cue,
    social_concept_for_cue,
)
from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.subject_dialogue_bind import gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.shared.store_bundles import load_store_bundles
from casa.prisms.tick.pdca_check_tick import surprise_to_hippo_episode


ROOT = Path(__file__).resolve().parents[1]
VON_STORE = ROOT / "agents" / "von-neumann"


def _bundle():
    if not (VON_STORE / "bundles").is_dir():
        pytest.skip("von-neumann bundles missing")
    return load_store_bundles(VON_STORE)


def test_privet_social_concept_from_kb():
    bundle = _bundle()
    assert social_concept_for_cue("Привет!", bundle) in ("lang.word.привет", "ru.dialog.greeting")


def test_privet_skips_grapheme_hippo():
    bundle = _bundle()
    assert skip_hippo_surprise_for_partner_cue("Привет", bundle)


def test_adjust_control_removes_grapheme_surprise():
    bundle = _bundle()
    control = ControlExtensions(
        predicted=("grapheme.cyrl.б",),
        surprise=tuple(f"grapheme.cyrl.{c}" for c in "абвгде"),
        prediction_error=0.8,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.9,
    )
    adjusted = adjust_control_for_partner_cue("Привет!", control, bundle=bundle)
    assert not any(str(c).startswith("grapheme.") for c in adjusted.surprise)
    assert adjusted.value < 0.3


def test_surprise_to_hippo_none_on_greeting():
    bundle = _bundle()
    state = {"field_version": 1}
    wm = WorkingMemory()
    control = ControlExtensions(
        predicted=(),
        surprise=("grapheme.cyrl.а",),
        prediction_error=0.5,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.9,
    )
    ep = surprise_to_hippo_episode(
        state,
        control=control,
        wm=wm,
        user_query="Привет",
        lattice_id="alphabet-ru",
        bundle=bundle,
        min_value=0.3,
    )
    assert ep is None


def test_greeting_reply_uses_kb_not_template():
    bundle = _bundle()
    tmp = Path(tempfile.mkdtemp(prefix="native-ru-"))
    try:
        (tmp / "bundles").mkdir()
        (tmp / "bundles" / "kb.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        (tmp / "store_profile.json").write_text(
            json.dumps({"subject_mode": True, "display_name": "von-neumann-test"}),
            encoding="utf-8",
        )
        bootstrap_native_ru_store(tmp, routes=False)
        ctx = gather_subject_dialogue_blocks(
            "Привет!",
            None,
            {"field_version": 1, "subject": {"subject_mode": True}},
            WorkingMemory(),
            tmp,
            bundle=bundle,
        )
        assert any(str(b.get("concept_id", "")).startswith(("lang.word.", "ru.dialog.")) for b in ctx.blocks)
        reply = compose_subject_utterance("Привет!", ctx)
        assert "привет" in reply.lower() or "«" in reply
        assert "grapheme" not in reply.lower()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_grammar_dative_on_real_bundle():
    bundle = _bundle()
    ctx = gather_subject_dialogue_blocks(
        "Согласно приказа верно?",
        None,
        {"field_version": 1},
        WorkingMemory(),
        VON_STORE,
        bundle=bundle,
    )
    assert ctx.query_intent == "grammar"
    assert any("ru.grammar.case.dative" in str(b.get("concept_id")) for b in ctx.blocks)
    reply = compose_subject_utterance("Согласно приказа верно?", ctx)
    assert "приказу" in reply.lower() or "датель" in reply.lower()


def test_punct_comma_on_real_bundle():
    bundle = _bundle()
    ctx = gather_subject_dialogue_blocks(
        "Нужна ли запятая в «я знаю что он придёт»?",
        None,
        {"field_version": 1},
        WorkingMemory(),
        VON_STORE,
        bundle=bundle,
    )
    reply = compose_subject_utterance("Нужна ли запятая в «я знаю что он придёт»?", ctx)
    assert "запят" in reply.lower()
