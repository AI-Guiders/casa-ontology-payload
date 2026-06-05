#!/usr/bin/env python3
"""ADR-0037/0038 subject diagnostics tests."""

from __future__ import annotations

import json
from pathlib import Path

from casa.domain.experience_ledger import build_experience_entry, experience_panel
from casa.domain.memory_hygiene import audit_routes, memory_hygiene_panel
from casa.domain.subject_diagnostics import run_subject_diagnostics
from casa.prisms.control.fpn_state import SESSION_NAME, WorkingMemory, save_session


def test_build_experience_entry_has_search_tags():
    wm = WorkingMemory(goal_id="goal.read.phrase", goal="мыла раму", step_capability="skill.read.phrase")
    report = {
        "tick": 7,
        "query": "мыла раму",
        "pdca": {"phase": "check", "check_tick": {"check_passed": True}},
        "self_organization": {"plan_arbiter": {"winner": {"source": "explicit"}}},
    }
    entry = build_experience_entry(wm=wm, report=report)
    assert entry["outcome"] == "verified"
    assert "goal.read.phrase" in entry["search_tags"]


def test_experience_panel_reads_journal(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    from casa.domain.agent_journal import append_experience_entry, append_tick_log_entry

    append_experience_entry(store, {"name": "x", "title": "t", "outcome": "verified"})
    append_tick_log_entry(store, {"at": "t", "executor": {}, "check": {}, "srl": "performance"})
    panel = experience_panel(store)
    assert panel["ledger_entries"] == 1
    assert panel["tick_log_entries"] == 1


def test_memory_hygiene_counts_routes():
    state = {"router": {"routes": []}}
    audit = audit_routes(state)
    assert audit["total"] == 0
    panel = memory_hygiene_panel(state)
    assert panel["panel"] == "memory"


def test_subject_diagnostics_three_panels(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    save_session(store, WorkingMemory(goal_id="goal.read.phrase", goal="phrase"))
    state = {"field_version": 1, "router": {"routes": []}, "sn": {}}
    report = run_subject_diagnostics(state, store, wm=WorkingMemory(goal_id="goal.read.phrase", goal="phrase"))
    assert "experience" in report
    assert "body" in report
    assert "memory" in report
    assert "skill_trace" in report
    assert "retrospective" in report


def test_save_session_preserves_meta(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    from casa.prisms.control.fpn_state import write_session_meta

    write_session_meta(store, {"schema_version": 2, "journal": "agent_journal.db", "macro_ticks": 3})
    save_session(store, WorkingMemory(goal_id="goal.test"))
    merged = json.loads((store / SESSION_NAME).read_text(encoding="utf-8"))
    assert merged["macro_ticks"] == 3
    assert merged["wm"]["goal_id"] == "goal.test"
