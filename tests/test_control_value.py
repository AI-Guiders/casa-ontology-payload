"""Deterministic assert-gate for lattice_value tags (CASA-ADR-0010 R5)."""

from __future__ import annotations

import casa.prisms.control.value as lv
import casa.prisms.hippo.replay_buffer as rb


def test_committed_correction_beats_pending():
    ortho = lv.value_from_correction("ortho_surface")
    wait = lv.value_from_correction("wait_prefix")
    assert ortho > wait


def test_surprise_adds_weight():
    assert lv.value_from_surprise(["a", "b"]) > lv.value_from_surprise([])


def test_episode_value_combines_signals():
    v = lv.episode_value(surprise=["x"], correction_kind="script_rule", task_relevant=True)
    assert v > lv.episode_value(correction_kind="wait_prefix")


def test_tag_replay_record_mutates_buffer():
    rec = {"episode_id": "e1", "kind": "surface", "cue": "x", "correct": "y", "correction_kind": "ortho_surface"}
    v = lv.tag_replay_record(rec, surprise=["unexpected"])
    assert rec["value"] == v and v > 0


def test_value_weight_reorders_with_lattice_value_tags():
    def _rec(ep_id: str, value: float) -> dict:
        return {
            "episode_id": ep_id,
            "kind": "surface",
            "cue": "x",
            "correct": "y",
            "correction_kind": "ortho_surface",
            "value": value,
            "first_archived_tick": 10,
            "last_replayed_tick": None,
            "replays": 0,
        }

    buf = [_rec("stale-low", 0.1), _rec("stale-high", 2.0)]
    order = [r["episode_id"] for r in rb.sample(buf, 1, now_tick=100, value_weight=1.0)]
    assert order == ["stale-high"]
