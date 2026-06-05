#!/usr/bin/env python3
"""ADR-0038 agent journal tests."""

from __future__ import annotations

import json
from pathlib import Path

from casa.domain.agent_journal import (
    JOURNAL_NAME,
    append_skill_trace,
    journal_path,
    migrate_legacy_session_arrays,
    query_skill_trace,
)
from casa.domain.experience_ledger import record_experience_from_tick
from casa.domain.skill_trace import record_skill_trace_from_tick
from casa.domain.subject_retrospective import maybe_run_retrospective, persist_retrospective, run_retrospective
from casa.prisms.control.fpn_state import SESSION_NAME, WorkingMemory, read_session_meta, save_session
from casa.prisms.control.session_log import append_tick_log


def test_journal_skill_trace_query(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    entry = {
        "at": "2026-06-05T12:00:00Z",
        "situation": {"goal_id": "goal.read.phrase"},
        "skill": "skill.read.analytic",
        "plan_step": 0,
        "outcome": "verified",
    }
    append_skill_trace(store, entry)
    rows = query_skill_trace(store, skill="analytic", outcome="verified")
    assert len(rows) == 1
    assert journal_path(store).is_file()


def test_legacy_session_migration(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    legacy = {
        "schema_version": 1,
        "wm": {"goal_id": "goal.test"},
        "skill_trace": [
            {
                "at": "t",
                "situation": {"goal_id": "goal.test"},
                "skill": "skill.read.analytic",
                "plan_step": 0,
                "outcome": "fail",
            }
        ],
    }
    (store / SESSION_NAME).write_text(json.dumps(legacy), encoding="utf-8")
    imported = migrate_legacy_session_arrays(store)
    assert imported.get("skill_trace") == 1
    meta = read_session_meta(store)
    assert meta.get("journal") == JOURNAL_NAME
    assert meta.get("journal_migrated") is True
    assert "skill_trace" not in meta or not isinstance(meta.get("skill_trace"), list)


def test_tick_log_writes_journal_not_session_arrays(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    wm = WorkingMemory(goal_id="goal.test", step_capability="skill.read.analytic")
    report = {
        "tick": 1,
        "query": "q",
        "pdca": {"phase": "check", "check_tick": {"check_passed": False}},
        "control": {},
    }
    append_tick_log(store, wm=wm, report=report)
    meta = read_session_meta(store)
    assert meta.get("macro_ticks") == 1
    assert meta.get("journal") == JOURNAL_NAME
    session_raw = json.loads((store / SESSION_NAME).read_text(encoding="utf-8"))
    assert "tick_log" not in session_raw


def test_save_session_compact_and_preserves_meta(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    meta = {"schema_version": 2, "journal": JOURNAL_NAME, "macro_ticks": 5}
    from casa.prisms.control.fpn_state import write_session_meta

    write_session_meta(store, meta)
    save_session(store, WorkingMemory(goal_id="goal.x"))
    text = (store / SESSION_NAME).read_text(encoding="utf-8")
    assert "\n  " not in text
    loaded = read_session_meta(store)
    assert loaded["macro_ticks"] == 5
    assert loaded["wm"]["goal_id"] == "goal.x"


def test_retrospective_from_journal(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    for _ in range(3):
        append_skill_trace(
            store,
            {
                "at": "t",
                "situation": {"goal_id": "goal.read.phrase"},
                "skill": "skill.read.analytic",
                "plan_step": 0,
                "outcome": "surprise",
                "weak_link": {"concept_id": "syllable.ла"},
            },
        )
    retro = maybe_run_retrospective(store, force=False)
    assert retro is not None
    assert retro.get("stop")


def test_record_skill_trace_from_tick(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    wm = WorkingMemory(goal_id="goal.read.phrase", step_capability="skill.read.analytic")
    report = {"tick": 2, "pdca": {"check_tick": {"check_passed": True}}, "control": {}}
    record_skill_trace_from_tick(store, wm=wm, report=report)
    assert len(query_skill_trace(store)) == 1
