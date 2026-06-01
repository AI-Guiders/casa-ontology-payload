"""Autonomous Self retain after verified predict."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.agent_autonomous_retain import (
    maybe_autonomous_retain_tick,
    retain_from_check_row,
    retain_verified_predict,
    self_verify_predict,
)
from casa.prisms.memory.agent_journal import search_journal_entries
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, run_sleep
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def _trained_state() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    append_episode(
        state,
        cue="14",
        surface_attempt="?",
        correct="14",
        lattice_id="schema-math",
        concept_id="math.num.fourteen",
        scene="lab",
    )
    run_sleep(state, bundle)
    return state


def test_retain_from_teacher_check_row(tmp_path: Path) -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = _trained_state()
    row = {
        "cue": "14",
        "expect": "math.num.fourteen",
        "hypothesis": "math.num.fourteen",
        "verdict": "pass",
        "label": "2×7",
    }
    rep = retain_from_check_row(tmp_path, state, bundle, row)
    assert rep is not None
    assert rep["status"] == "confirmed"
    assert rep.get("skipped") is not True

    again = retain_from_check_row(tmp_path, state, bundle, row)
    assert again is not None
    assert again.get("skipped") is True


def test_self_verify_and_tick_retain(tmp_path: Path) -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = _trained_state()
    tick = self_verify_predict(state, "14", bundle=bundle)
    assert tick is not None
    assert tick.get("verdict") == "pass"

    rep = maybe_autonomous_retain_tick(tmp_path, state, cue="14", bundle=bundle)
    assert rep is not None
    assert rep["status"] == "confirmed"

    rows = search_journal_entries(tmp_path, draft=True)
    assert len(rows) >= 1
    assert any(r.get("meta", {}).get("status") == "confirmed" for r in rows)


def test_retain_skips_mismatch(tmp_path: Path) -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = _trained_state()
    rep = retain_verified_predict(
        tmp_path,
        state,
        cue="99",
        expect="math.num.nine",
        hypothesis="math.num.eight",
        bundle=bundle,
    )
    assert rep is None
