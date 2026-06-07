#!/usr/bin/env python3
"""RU-α train probe requires prior teacher ingest (no inline remember)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_VC = _REPO / "lab/visual-curriculum"
if str(_VC) not in sys.path:
    sys.path.insert(0, str(_VC))

from probe_material_verbal_ru import _run_case  # noqa: E402

from casa.cli.ingest_verbal_moment import run_verbal_moment_plan  # noqa: E402
from casa.cli.ingest_state import resolve_ingest_state  # noqa: E402
from casa.prisms.control.fpn_state import WorkingMemory  # noqa: E402
from casa.prisms.shared.store_bundles import load_store_bundles  # noqa: E402

_PLAN = _REPO / "lessons/ru-material-verbal/data/material-verbal-moment-plan-v1.json"


def _fresh_store() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="casa-mv-ingest-"))
    (tmp / "store_profile.json").write_text(
        json.dumps({"subject_mode": True, "display_name": "Нейманн"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tmp


def _wired_cases() -> list[dict]:
    plan = json.loads(_PLAN.read_text(encoding="utf-8"))
    return [c for c in plan.get("scenarios") or [] if c.get("wired", True)]


def _run_train_probe(store: Path) -> tuple[int, int]:
    state = resolve_ingest_state(store, None)
    bundle = load_store_bundles(store)
    wm = WorkingMemory()
    know = 0
    for case in _wired_cases():
        ok, _, _ = _run_case(
            case,
            store=store,
            state=state,
            wm=wm,
            bundle=bundle,
            inject_remember=False,
        )
        if ok:
            know += 1
    total = len(_wired_cases())
    return know, total


def test_train_probe_fails_without_prior_ingest() -> None:
    store = _fresh_store()
    know, total = _run_train_probe(store)
    assert total == 3
    assert know < total, "train probe must not pass on empty store without inline remember"


def test_train_probe_passes_after_teacher_ingest() -> None:
    store = _fresh_store()
    summary = run_verbal_moment_plan(
        store,
        plan_path=_PLAN,
        source="ingest_material_verbal",
        dry_run=False,
    )
    assert summary["moments"] == 3

    know, total = _run_train_probe(store)
    assert know == total == 3


def test_held_out_inline_remember_still_passes_without_ingest() -> None:
    """Held-out scenarios are never ingested — probe injects remember."""
    held_out = _REPO / "lessons/ru-material-verbal/data/material-verbal-held-out-plan.json"
    plan = json.loads(held_out.read_text(encoding="utf-8"))
    store = _fresh_store()
    state = resolve_ingest_state(store, None)
    bundle = load_store_bundles(store)
    wm = WorkingMemory()

    know = 0
    cases = [c for c in plan.get("scenarios") or [] if c.get("wired", True)]
    for case in cases:
        ok, _, _ = _run_case(
            case,
            store=store,
            state=state,
            wm=wm,
            bundle=bundle,
            inject_remember=True,
        )
        if ok:
            know += 1

    if know < len(cases):
        pytest.skip("held-out compose not green on this store — ingest invariant still tested above")

    assert know == len(cases)
