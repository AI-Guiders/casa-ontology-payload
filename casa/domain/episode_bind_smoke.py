#!/usr/bin/env python3
"""Smoke: episode bind + surprise concept_id (ADR-0047)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from casa.domain.episode_bind import (
    EpisodeBindClass,
    counts_toward_load,
    infer_bind_class,
    primary_surprise_concept,
    resolve_episode_concept_id,
)
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, hippo_episodes, run_sleep
from casa.prisms.shared.store_persist import save_runtime_state
from casa.prisms.tick.pdca_check_tick import surprise_to_hippo_episode


def main() -> int:
    from casa.prisms.control.fpn_state import WorkingMemory

    control = ControlExtensions(
        predicted=("grapheme.cyrl.б",),
        surprise=("grapheme.cyrl.а", "grapheme.cyrl.в"),
        prediction_error=0.5,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.8,
    )
    assert primary_surprise_concept(control) == "grapheme.cyrl.а"

    bind = infer_bind_class(
        structure_tag="predict_mismatch",
        scene="predict_surprise",
        concept_id="grapheme.cyrl.а",
        correct="grapheme.cyrl.а, grapheme.cyrl.в",
    )
    assert bind == EpisodeBindClass.BINDABLE_SURPRISE.value

    open_bind = infer_bind_class(
        structure_tag="predict_mismatch",
        scene="what_if",
        concept_id=None,
        correct="",
    )
    assert open_bind == EpisodeBindClass.OPEN_PROBE.value

    ep = {
        "correct": "grapheme.cyrl.а, grapheme.cyrl.б",
        "surface_attempt": "?",
        "cue": "Привет",
    }
    assert resolve_episode_concept_id(ep, None) == "grapheme.cyrl.а"

    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        state: dict = {"field_version": 1, "store": {"store_id": "bind-smoke"}}
        ensure_prisms(state)

        wm = WorkingMemory()
        hippo_ep = surprise_to_hippo_episode(
            state,
            control=control,
            wm=wm,
            user_query="Привет",
            lattice_id="alphabet-ru",
            bundle={"claims": [], "graph": {"edges": []}},
            min_value=0.3,
        )
        assert hippo_ep is not None
        assert hippo_ep.get("concept_id") == "grapheme.cyrl.а"
        assert hippo_ep.get("bind_class") == "bindable_surprise"

        append_episode(
            state,
            cue="3*2",
            surface_attempt="?",
            correct="",
            lattice_id="schema-math",
            scene="what_if",
            structure_tag="predict_mismatch",
            bind_class="open_probe",
        )
        pending_load = sum(1 for e in hippo_episodes(state) if counts_toward_load(e))
        assert pending_load == 1

        bundle = {"claims": [], "graph": {"edges": []}}
        rep = run_sleep(state, bundle, store_dir=store, compact_persist=False)
        save_runtime_state(store, state)
        after_pending = sum(1 for e in hippo_episodes(state) if not e.get("consolidated"))
        report = {
            "ok": True,
            "concept_id": hippo_ep.get("concept_id"),
            "bind_class": hippo_ep.get("bind_class"),
            "load_counted": pending_load,
            "sleep_merged": rep.get("merged"),
            "pending_after": after_pending,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if hippo_ep.get("concept_id") and pending_load == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
