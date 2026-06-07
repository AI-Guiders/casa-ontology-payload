#!/usr/bin/env python3
"""Smoke: agent dialogue REPL wiring."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


def _fresh_store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-repl-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Тест"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tmp


def test_repl_import_and_subject_gate() -> None:
    from casa.cli.agent_dialogue_repl import _partner_reply, run_repl

    store = _fresh_store()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.domain.subject_mode import apply_subject_profile
    from casa.prisms.control.fpn_state import WorkingMemory

    state = resolve_ingest_state(store, None)
    apply_subject_profile(store, state)
    reply, _ = _partner_reply(
        "Привет!",
        store=store,
        state=state,
        wm=WorkingMemory(tick=0),
        tick=1,
        verbose=False,
    )
    assert reply.strip()
    assert run_repl  # callable


def test_repl_quit_via_pipe() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "casa.cli.agent_dialogue_repl", "--store", "von-neumann"],
        cwd=str(_REPO),
        input="/quit\n",
        text=True,
        capture_output=True,
        timeout=180,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    assert "Пока" in proc.stdout
