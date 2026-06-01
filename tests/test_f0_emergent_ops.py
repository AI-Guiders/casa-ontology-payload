"""Emergent math operators — unbound glyph detect + sleep Extract mint denotes."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_reading import analyze_cue, unbound_operators
from casa.prisms.memory.f0_stack import (
    analyze_f0_cue_ranking,
    concept_in_context,
    decode_f0_lattice,
    encode_f0_lattice,
    mint_operator_denotes_from_episode,
    _grapheme_for_glyph,
)
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.tick.predict_tick import predict_tick

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def test_spurious_pipe_infix_filtered() -> None:
    ops = [ix["op"] for ix in analyze_cue("|||| - | = |||")["infix"]]
    assert ops == ["-"]


def test_unbound_minus_in_stick_equation() -> None:
    b = _bundle()
    dec = decode_f0_lattice(encode_f0_lattice(b))
    unbound = unbound_operators(
        "|||| - | = |||",
        b,
        dec,
        concept_in_context=concept_in_context,
        grapheme_for_glyph=_grapheme_for_glyph,
    )
    assert len(unbound) == 1
    assert unbound[0]["op"] == "-"


def test_predict_flags_unbound_not_false_eq() -> None:
    b = _bundle()
    state = ensure_prisms({})
    ingest_math_bundle(state, b)
    tick = predict_tick(state, "|||| - | = |||", modality="schema", expect="math.op.sub", bundle=b)
    pred = tick["predict"]
    assert pred.get("unbound_operators")
    assert pred["hypothesis"] is None
    assert tick["verdict"] == "fail"
    assert "unbound" in str(tick["critic"]["checks"][0].get("detail", ""))


def test_roman_infix_not_livestock_after_sub_teacher() -> None:
    b = _bundle()
    state = ensure_prisms({})
    ingest_math_bundle(state, b)
    append_episode(
        state,
        cue="||| - || = |",
        surface_attempt="?",
        correct="|",
        lattice_id="schema-math",
        concept_id="math.op.sub",
        bundle=b,
        scene="sticks_sub",
    )
    run_sleep(state, b)
    tick = predict_tick(state, "III - II", modality="schema", expect="math.op.sub", bundle=b)
    pred = tick["predict"]
    assert pred.get("hypothesis") == "math.op.sub"
    assert pred.get("hypothesis") != "math.category.livestock"
    assert tick["verdict"] == "pass"


def test_identifier_infix_unbound_before_teacher() -> None:
    b = _bundle()
    state = ensure_prisms({})
    ingest_math_bundle(state, b)
    tick = predict_tick(state, "III - II", modality="schema", expect="math.op.sub", bundle=b)
    pred = tick["predict"]
    assert pred.get("unbound_operators")
    assert pred["hypothesis"] is None


def test_sleep_mint_denotes_enables_sub_predict() -> None:
    b = _bundle()
    state = ensure_prisms({})
    ingest_math_bundle(state, b)
    append_episode(
        state,
        cue="|||| - | = |||",
        surface_attempt="?",
        correct="math.op.sub",
        lattice_id="schema-math",
        concept_id="math.op.sub",
        bundle=b,
        scene="minus_teacher",
    )
    sleep = run_sleep(state, b)
    assert sleep["merged"] == 1
    extract = (sleep["items"][0].get("extract") or {})
    assert extract.get("concept_id") == "math.op.sub"
    assert extract.get("glyph") == "-"

    tick = predict_tick(state, "|||| - | = |||", modality="schema", expect="math.op.sub", bundle=b)
    assert not tick["predict"].get("unbound_operators")
    assert tick["predict"]["hypothesis"] == "math.op.sub"
    assert tick["verdict"] == "pass"

    mint = mint_operator_denotes_from_episode(
        memory_lattices(state),
        lattice_id="schema-math",
        cue="|||| - | = |||",
        concept_id="math.op.sub",
        bundle=b,
    )
    assert mint and mint.get("skipped")
