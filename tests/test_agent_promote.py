"""Self journal promote → profile field."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from casa.prisms.memory.agent_promote import promote_journal_entry
from casa.prisms.memory.agent_workbook import workbook_check, workbook_write
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


def test_promote_requires_confirmed_by_default(tmp_path: Path) -> None:
    row = workbook_write(
        tmp_path,
        kind="hypothesis",
        text="14 is fourteen",
        concepts=["math.num.fourteen"],
        test_cues=["14"],
        expect="math.num.fourteen",
    )
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="status"):
        promote_journal_entry(tmp_path, _trained_state(), row["id"], bundle, persist=False)


def test_promote_after_workbook_check(tmp_path: Path) -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = _trained_state()
    row = workbook_write(
        tmp_path,
        kind="hypothesis",
        text="14 is fourteen",
        concepts=["math.num.fourteen"],
        test_cues=["14"],
        expect="math.num.fourteen",
    )
    workbook_check(tmp_path, state, row["id"], bundle, persist=False)
    rep = promote_journal_entry(tmp_path, state, row["id"], bundle, persist=False)
    assert rep["promoted"] is True
    assert rep["sleep"]["merged"]

    rep2 = promote_journal_entry(tmp_path, state, row["id"], bundle, persist=False)
    assert rep2["promoted"] is False
    assert rep2["reason"] == "already_promoted"
