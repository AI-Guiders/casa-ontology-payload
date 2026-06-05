"""Learning tick orchestrator — act rollout, surprise→hippo, sleep hook."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import run_control_extensions
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices, prism_hippo
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.shared.store_layout import field_state_path
from casa.prisms.tick.act_rollout import act_rollout_phase, merge_decoded_digests, resolve_nca_model_path
from casa.prisms.memory.memory_prisms import append_episode
from casa.prisms.tick.orchestrator import LearningTickConfig
from casa.prisms.tick.pdca_act_tick import maybe_sleep_phase
from casa.prisms.tick.pdca_check_tick import surprise_to_hippo_episode


def _minimal_store(tmp_path: Path) -> tuple[Path, dict]:
    store = tmp_path / "store"
    (store / "bundles").mkdir(parents=True)
    bundle = {
        "claims": [{"concept_id": "demo.alpha", "text": "alpha"}],
        "graph": {"edges": []},
    }
    (store / "bundles" / "demo.json").write_text(json.dumps(bundle), encoding="utf-8")

    cells = [[] for _ in range(64)]
    cells[0] = ["C:demo.alpha"]
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
            "bundles": {"demo.json": {"claim_count": 1}},
            "sss": {
                "lattices": {
                    "L0_grapheme": {
                        "width": 8,
                        "height": 8,
                        "cells": [list(c) for c in cells],
                        "z_level": 0,
                    }
                },
                "active_lattice": "L0_grapheme",
            },
        }
    )
    prism_hippo(state)
    save_field_state(field_state_path(store), state)
    return store, state


def test_merge_decoded_digests_unions_concepts() -> None:
    base = {"concept_ids": ["a"], "concepts": [{"concept_id": "a", "votes": 2}], "edges": []}
    extra = {"concept_ids": ["b"], "concepts": [{"concept_id": "b", "votes": 3}], "edges": ["E:x|y|z"]}
    merged = merge_decoded_digests(base, extra)
    assert "a" in merged["concept_ids"] and "b" in merged["concept_ids"]
    assert merged["edges"] == ["E:x|y|z"]


def test_act_rollout_skips_without_nca(tmp_path: Path) -> None:
    store, state = _minimal_store(tmp_path)
    rep = act_rollout_phase(state, store)
    assert rep["skipped"] is True
    assert rep["reason"] == "no_nca_model"
    assert resolve_nca_model_path(store, state, "L0_grapheme") is None


def test_surprise_creates_hippo_episode(tmp_path: Path) -> None:
    _, state = _minimal_store(tmp_path)
    control = run_control_extensions(
        prior_digest=["demo.alpha"],
        current_digest=["demo.beta"],
        goal=["demo.beta"],
        task_relevant=True,
    )
    assert control.surprise
    ep = surprise_to_hippo_episode(
        state,
        control=control,
        wm=WorkingMemory(goal="find beta"),
        user_query=None,
        lattice_id="L0_grapheme",
        bundle=None,
        min_value=0.1,
    )
    assert ep is not None
    hippo = prism_hippo(state)
    assert len(hippo.get("episodes") or []) == 1


def test_cue_dedup_casefold() -> None:
    from casa.prisms.tick.surprise_policy import normalize_cue

    assert normalize_cue("Два плюс два") == normalize_cue("два плюс два")


def test_surprise_dedup_hippo(tmp_path: Path) -> None:
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.control.tick import run_control_extensions
    from casa.prisms.memory.memory_prisms import prism_hippo
    from casa.prisms.tick.pdca_check_tick import surprise_to_hippo_episode

    _, state = _minimal_store(tmp_path)
    control = run_control_extensions(
        prior_digest=["demo.alpha"],
        current_digest=["demo.beta"],
        goal=["demo.beta"],
        task_relevant=True,
    )
    wm = WorkingMemory()
    ep1 = surprise_to_hippo_episode(
        state,
        control=control,
        wm=wm,
        user_query="два плюс два",
        lattice_id="L0_grapheme",
        bundle=None,
        min_value=0.1,
    )
    ep2 = surprise_to_hippo_episode(
        state,
        control=control,
        wm=wm,
        user_query="Два плюс два",
        lattice_id="L0_grapheme",
        bundle=None,
        min_value=0.1,
    )
    assert ep1 is not None and ep2 is not None
    assert ep2.get("deduped") is True
    assert len(prism_hippo(state).get("episodes") or []) == 1
    assert int(ep2.get("recurrence_seen") or 0) >= 1


def test_run_learning_tick_minimal(tmp_path: Path) -> None:
    from casa.prisms.control.agent_sn_cen_tick import run_tick

    store, _ = _minimal_store(tmp_path)
    wm = WorkingMemory(last_concepts=["demo.alpha"])
    cfg = LearningTickConfig(
        act_rollout=True,
        surprise_episode=True,
        surprise_min_value=0.1,
        remember_on_surprise=False,
        sleep_every=0,
    )
    report, wm_out, state = run_tick(
        store_dir=store,
        user_query="demo",
        wm=wm,
        config=cfg,
    )
    assert wm_out.tick == 1
    assert report["cen"]
    assert report["control"]["prediction_error"] >= 0
    assert report["learning_cycle"]["use"]["sn_cen"] is True
    assert memory_lattices(state)["L0_grapheme"]


def test_maybe_sleep_phase_batch_size(tmp_path: Path) -> None:
    from casa.prisms.control.tick import run_control_extensions

    _, state = _minimal_store(tmp_path)
    bundle = {"claims": [], "graph": {"edges": []}}
    for i in range(3):
        append_episode(
            state,
            cue=f"c{i}",
            surface_attempt="x",
            correct=f"w{i}",
            lattice_id="L0_grapheme",
            concept_id=f"lang.word.w{i}",
        )
    control = run_control_extensions(
        prior_digest=[],
        current_digest=["demo.alpha"],
        goal=["demo.alpha"],
        task_relevant=True,
    )
    state.setdefault("consolidation", {})["ticks_since_sleep"] = 99
    rep = maybe_sleep_phase(
        state,
        bundle,
        sleep_every=1,
        sleep_on_value=2.0,
        control=control,
        sleep_batch_size=1,
    )
    assert rep is not None
    assert rep["merged"] == 1
    assert len(prism_hippo(state).get("episodes") or []) == 2
    job = (state.get("consolidation") or {}).get("sleep_job") or {}
    assert int(job.get("batch_index") or 0) == 1
