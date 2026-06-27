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


if __name__ == "__main__":
    unittest.main()
