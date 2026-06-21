"""Agent workbook — hypothesis write and predict check."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.agent_journal import DEFAULT_JOURNAL_DOMAIN, read_journal_entries, search_journal_entries
from casa.prisms.memory.agent_workbook import (
    workbook_check,
    workbook_list,
    workbook_open_questions,
    workbook_write,
)
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def test_workbook_write_and_list(tmp_path: Path) -> None:
    row = workbook_write(
        tmp_path,
        kind="hypothesis",
        text="skip by 2 is preparation for multiplication",
        concepts=["math.pattern.emerged.deadbeef0123", "math.op.mul"],
        test_cues=["14", "18"],
        expect="math.num.fourteen",
        status="open",
        notebook="sticks-l0",
    )
    assert row["id"].startswith("j-")
    assert "draft" in row["tags"]
    listed = workbook_list(tmp_path, kind="hypothesis", notebook="sticks-l0")
    assert len(listed) == 1
    assert listed[0]["meta"]["status"] == "open"
    open_rows = workbook_open_questions(tmp_path, notebook="sticks-l0")
    assert len(open_rows) == 1


def test_workbook_check_updates_status(tmp_path: Path) -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    from casa.prisms.memory.memory_prisms import append_episode, run_sleep

    append_episode(
        state,
        cue="14",
        surface_attempt="?",
        correct="14",
        lattice_id="schema-math",
        concept_id="math.num.fourteen",
        scene="lab",
        structure_tag="self_promote",  # sanctioned earned-write so the numeral mint runs
    )
    run_sleep(state, bundle)

    row = workbook_write(
        tmp_path,
        kind="hypothesis",
        text="14 is fourteen",
        concepts=["math.num.fourteen"],
        test_cues=["14"],
        expect="math.num.fourteen",
    )
    rep = workbook_check(tmp_path, state, row["id"], bundle, persist=False)
    assert rep["status"] == "confirmed"
    assert rep["passes"] == 1
    after = workbook_list(tmp_path, status="confirmed")
    assert len(after) == 1


def test_workbook_lives_in_self_shard_not_fixed_domain(tmp_path: Path) -> None:
    from casa.prisms.memory.agent_journal import append_journal_entry

    append_journal_entry(tmp_path, {"kind": "note", "text": "math note"}, domain="math")
    workbook_write(tmp_path, kind="question", text="what is IV?", concepts=["math.num.four"])
    assert len(read_journal_entries(tmp_path, domain="math")) == 1
    drafts = search_journal_entries(tmp_path, draft=True)
    assert len(drafts) == 1
    assert drafts[0]["_domain"] == DEFAULT_JOURNAL_DOMAIN


def test_multiple_notebooks(tmp_path: Path) -> None:
    workbook_write(tmp_path, kind="note", text="a", notebook="nb-one")
    workbook_write(tmp_path, kind="note", text="b", notebook="nb-two")
    assert len(workbook_list(tmp_path, notebook="nb-one")) == 1
    assert len(workbook_list(tmp_path, notebook="nb-two")) == 1
