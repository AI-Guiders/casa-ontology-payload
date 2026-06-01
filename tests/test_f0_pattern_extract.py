"""Emergent count-pattern Extract from episode clusters."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_pattern_extract import (
    extract_emergent_count_patterns,
    is_emergent_pattern_id,
    is_emergent_struct_id,
    match_emergent_patterns_for_values,
    parse_comma_numeral_cue,
)
from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def _bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def _state_with_f0() -> dict:
    state = ensure_prisms({})
    ingest_math_bundle(state, _bundle(), copies=2)
    return state


def _episodes_for_step(step: int, start: int, count: int) -> list[dict]:
    from casa.prisms.memory.f0_pattern_extract import numeral_int_to_concept_id

    rows = []
    v = start
    for i in range(count):
        cid = numeral_int_to_concept_id(v)
        assert cid
        rows.append(
            {
                "id": f"ep-test-{step}-{i}",
                "kind": "surface",
                "cue": str(v),
                "correct": str(v),
                "concept_id": cid,
                "scene": f"count_row:lab",
                "form_extract_allowed": True,
                "_value": v,
            }
        )
        v += step
    return rows


def test_extract_mints_opaque_pattern_hub() -> None:
    state = _state_with_f0()
    lats = memory_lattices(state)
    eps = _episodes_for_step(5, 5, 4)
    merged = extract_emergent_count_patterns(lats, eps, state, copies=4)
    assert len(merged) == 1
    pid = merged[0]["concept_id"]
    assert is_emergent_pattern_id(pid)
    assert "step_5" not in pid
    dec = decode_f0_lattice(lats["schema-math"], min_votes=1)
    ids = {c["concept_id"] for c in dec.get("concepts") or []}
    assert pid in ids
    assert any(is_emergent_struct_id(c) for c in ids)
    edges = {e for e in dec.get("edges") or []}
    assert f"{pid}|step|math.num.five" in edges


def test_same_cluster_idempotent_different_runs_new_ids() -> None:
    state1 = _state_with_f0()
    lats1 = memory_lattices(state1)
    eps1 = _episodes_for_step(2, 2, 3)
    eps1[0]["id"] = "ep-a"
    eps1[1]["id"] = "ep-b"
    eps1[2]["id"] = "ep-c"
    m1 = extract_emergent_count_patterns(lats1, eps1, state1, copies=3)
    state2 = _state_with_f0()
    lats2 = memory_lattices(state2)
    eps2 = _episodes_for_step(2, 2, 3)
    eps2[0]["id"] = "ep-x"
    eps2[1]["id"] = "ep-y"
    eps2[2]["id"] = "ep-z"
    m2 = extract_emergent_count_patterns(lats2, eps2, state2, copies=3)
    assert m1[0]["concept_id"] != m2[0]["concept_id"]


def test_sleep_extract_from_count_row_episodes() -> None:
    state = _state_with_f0()
    bundle = _bundle()
    for row in _episodes_for_step(2, 2, 4):
        append_episode(
            state,
            cue=row["cue"],
            surface_attempt="?",
            correct=row["correct"],
            lattice_id="schema-math",
            concept_id=row["concept_id"],
            scene="count_row:lab",
            form_extract_allowed=True,
        )
    rep = run_sleep(state, bundle, strength=4)
    emergent = [x for x in rep.get("items") or [] if x.get("kind") == "emergent_pattern"]
    assert emergent
    assert is_emergent_pattern_id(emergent[0]["concept_id"])


def test_predict_ranks_by_field_edges_not_name() -> None:
    state = _state_with_f0()
    lats = memory_lattices(state)
    extract_emergent_count_patterns(lats, _episodes_for_step(5, 5, 4), state, copies=5)
    bundle = _bundle()
    dec = decode_f0_lattice(lats["schema-math"], min_votes=1)
    ranked = rank_cue_on_f0(bundle, dec, "5, 10, 15, 20")
    matches = match_emergent_patterns_for_values(dec, [5, 10, 15, 20])
    assert matches
    assert ranked[0][0] == matches[0][0]
    assert is_emergent_pattern_id(ranked[0][0])


def test_parse_comma_numeral_cue() -> None:
    assert parse_comma_numeral_cue("5, 10, 15, 20") == [5, 10, 15, 20]
    assert parse_comma_numeral_cue("5") is None
