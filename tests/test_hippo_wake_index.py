#!/usr/bin/env python3
"""ADR-0088 slice 0: hippo wake index — moment_id, episode_id, boundaries."""

from __future__ import annotations

import unittest

from casa.prisms.hippo.mode import (
    HIPPO_MODE_CONSOLIDATE,
    HIPPO_MODE_WAKE,
    get_hippo_mode,
    set_hippo_mode,
)
from casa.prisms.hippo.wake_index import (
    close_episode_boundary,
    ensure_hippo_index,
    hippo_wake_index_tick,
)


class HippoModeTests(unittest.TestCase):
    def test_set_and_get_mode(self) -> None:
        state: dict = {}
        self.assertEqual(set_hippo_mode(state, HIPPO_MODE_WAKE), HIPPO_MODE_WAKE)
        self.assertEqual(get_hippo_mode(state), HIPPO_MODE_WAKE)
        set_hippo_mode(state, HIPPO_MODE_CONSOLIDATE)
        self.assertEqual(get_hippo_mode(state), HIPPO_MODE_CONSOLIDATE)

    def test_invalid_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            set_hippo_mode({}, "dream")


class HippoWakeIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state: dict = {"field_version": 0, "sn": {}}

    def test_first_tick_opens_episode_and_moment(self) -> None:
        rep = hippo_wake_index_tick(self.state, scene_id="scene-a", beat_id="b004", seq=0)
        self.assertTrue(rep["moment_id"].startswith("mom-"))
        self.assertTrue(rep["episode_id"].startswith("epi-scene-a-"))
        self.assertIn("episode_opened", rep["boundaries"])
        self.assertIn("moment_opened", rep["boundaries"])

    def test_same_beat_same_ids(self) -> None:
        r1 = hippo_wake_index_tick(self.state, scene_id="scene-a", beat_id="b004", seq=0)
        r2 = hippo_wake_index_tick(self.state, scene_id="scene-a", beat_id="b004", seq=1, coactive=True)
        self.assertEqual(r1["moment_id"], r2["moment_id"])
        self.assertEqual(r1["episode_id"], r2["episode_id"])
        idx = ensure_hippo_index(self.state)
        buf = idx["moment_buffer"][r1["moment_id"]]
        self.assertEqual(len(buf["ticks"]), 2)
        self.assertIn("av_coactive", buf["modalities"])

    def test_beat_change_new_moment_same_episode(self) -> None:
        r1 = hippo_wake_index_tick(self.state, scene_id="scene-a", beat_id="b004")
        r2 = hippo_wake_index_tick(self.state, scene_id="scene-a", beat_id="b029")
        self.assertNotEqual(r1["moment_id"], r2["moment_id"])
        self.assertEqual(r1["episode_id"], r2["episode_id"])
        self.assertIn("beat_change", r2["boundaries"])

    def test_scene_change_new_episode(self) -> None:
        r1 = hippo_wake_index_tick(self.state, scene_id="scene-a", beat_id="b004")
        r2 = hippo_wake_index_tick(self.state, scene_id="scene-b", beat_id="b000")
        self.assertNotEqual(r1["episode_id"], r2["episode_id"])
        self.assertIn("scene_change", r2["boundaries"])

    def test_close_episode_boundary(self) -> None:
        hippo_wake_index_tick(self.state, scene_id="scene-a", beat_id="b004")
        idx = ensure_hippo_index(self.state)
        active = idx["active_episode_id"]
        rep = close_episode_boundary(self.state, reason="chapter_end")
        self.assertTrue(rep["closed"])
        self.assertEqual(rep["episode_id"], active)
        self.assertIsNone(ensure_hippo_index(self.state)["active_episode_id"])

    def test_record_tick_false_then_true(self) -> None:
        r_prep = hippo_wake_index_tick(
            self.state, scene_id="scene-a", beat_id="b004", seq=0, record_tick=False
        )
        self.assertTrue(r_prep["moment_id"].startswith("mom-"))
        idx = ensure_hippo_index(self.state)
        self.assertEqual(len(idx["journal"]), 2)  # episode_opened, moment_opened
        r_tick = hippo_wake_index_tick(
            self.state,
            scene_id="scene-a",
            beat_id="b004",
            seq=0,
            coactive=True,
            record_tick=True,
        )
        self.assertEqual(r_prep["moment_id"], r_tick["moment_id"])
        buf = idx["moment_buffer"][r_tick["moment_id"]]
        self.assertEqual(len(buf["ticks"]), 1)
        self.assertIn("av_coactive", buf["modalities"])


class ResolveBeatAtTRelTests(unittest.TestCase):
    def test_resolve_beat_in_window(self) -> None:
        from casa.domain.listen_beat_lookup import resolve_beat_id_at_t_rel

        scene = {
            "beats": [
                {"id": "b003", "t0": 15.5, "t1": 22.5},
                {"id": "b004", "t0": 22.5, "t1": 28.0},
                {"id": "b005", "t0": 28.0, "t1": 30.5},
            ]
        }
        self.assertEqual(resolve_beat_id_at_t_rel(scene, 24.0), "b004")
        self.assertEqual(resolve_beat_id_at_t_rel(scene, 22.5), "b004")
        self.assertEqual(resolve_beat_id_at_t_rel(scene, 28.0), "b005")
        self.assertEqual(resolve_beat_id_at_t_rel(scene, 30.0), "b005")
        self.assertIsNone(resolve_beat_id_at_t_rel(scene, 10.0))
        self.assertIsNone(resolve_beat_id_at_t_rel(scene, 31.0))

    def test_last_beat_includes_chapter_end(self) -> None:
        from casa.domain.listen_beat_lookup import resolve_beat_id_at_t_rel

        scene = {"beats": [{"id": "b042", "t0": 194.25, "t1": 201.0}]}
        self.assertEqual(resolve_beat_id_at_t_rel(scene, 201.0), "b042")


if __name__ == "__main__":
    unittest.main()
