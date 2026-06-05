#!/usr/bin/env python3
"""Orchestrator — retrospective after sleep."""

from __future__ import annotations

from unittest.mock import patch

from casa.prisms.tick.orchestrator import LearningTickConfig, run_learning_tick


def test_retrospective_hook_after_sleep(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    (store / "bundles").mkdir()
    import json

    from casa.prisms.memory.memory_prisms import ensure_prisms
    from casa.prisms.shared.field_write import save_field_state
    from casa.prisms.shared.store_layout import field_state_path

    bundle = {"claims": [], "graph": {"edges": []}}
    (store / "bundles" / "demo.json").write_text(json.dumps(bundle), encoding="utf-8")
    cells = [[] for _ in range(64)]
    state = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 1,
            "grid": {
                "width": 8,
                "height": 8,
                "cells": cells,
                "source_bundle": "demo.json",
                "source_bundles": ["demo.json"],
            },
            "bundles": {"demo.json": {"claim_count": 0}},
        }
    )
    save_field_state(field_state_path(store), state)

    from casa.prisms.control.fpn_state import WorkingMemory

    wm = WorkingMemory(tick=1, goal_id="goal.read.phrase")
    fake_sleep = {"merged": 1, "reason": "test"}
    fake_retro = {"trigger": "after_sleep", "stop": [], "try": [], "keep": []}

    with patch(
        "casa.prisms.tick.pdca_act_tick.maybe_pdca_act_tick",
        return_value={"act_kind": "sleep", "sleep": fake_sleep},
    ), patch(
        "casa.prisms.tick.pdca_check_tick.maybe_pdca_check_tick",
        return_value={"check_passed": False, "scaffold_level": "guided"},
    ), patch(
        "casa.domain.subject_retrospective.maybe_run_retrospective_after_sleep",
        return_value=fake_retro,
    ) as retro_mock:
        report, _, _ = run_learning_tick(
            store_dir=store,
            user_query="test",
            wm=wm,
            config=LearningTickConfig(
                act_rollout=False,
                tick_log=False,
                retro_after_sleep=True,
            ),
            state=state,
        )

    retro_mock.assert_called_once_with(store)
    assert report.get("retrospective") == fake_retro
    assert report["learning_cycle"]["reflect"]["retrospective"] is True
