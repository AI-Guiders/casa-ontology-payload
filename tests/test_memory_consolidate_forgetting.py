#!/usr/bin/env python3
"""Memory consolidate snapshot + forgetting honesty (ADR-0068 P12e-f / ADR-0070 P15f)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.prisms.intelligence.scope_bind import apply_bind_scope
from casa.prisms.memory.consolidate_report import (
    FORGET_HONESTY_JSON,
    memory_consolidate_snapshot,
    probe_math_habit_implicit,
    probe_recall_uses_episodic_scope,
)
from casa.prisms.memory.forgetting import (
    DEFAULT_PRIMING_ALPHA,
    build_forget_honesty_report,
    finalize_memory_sleep_reports,
    forget_snapshot,
    probe_canon_immutable_touched,
    probe_priming_alpha,
    write_forget_honesty_report,
)
from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.memory.memory_prisms import (
    append_episode,
    ensure_prisms,
    hippo_episodes,
    run_sleep,
)
from casa.prisms.memory.zone import ensure_memory_zone, spawn_memory_zone

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


class MemoryConsolidateForgettingTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 1})
        ensure_agent_prism(state)
        spawn_memory_zone(state)
        return state

    def test_memory_consolidate_snapshot_mirrors_sleep_report(self) -> None:
        state = self._state()
        sleep_report = {
            "merged": 2,
            "pending": 5,
            "immutable_skipped": [{"lattice_id": "schema-math", "reason": "immutable_sleep_gate"}],
            "items": [{"kind": "episode"}],
            "z_compose": 3,
        }
        digest = memory_consolidate_snapshot(state, sleep_report)
        zone = ensure_memory_zone(state)
        self.assertEqual(digest["merged"], 2)
        self.assertEqual(digest["pending"], 5)
        self.assertEqual(digest["immutable_skipped_count"], 1)
        self.assertEqual(zone["consolidate"]["last_report"]["items_count"], 1)
        self.assertEqual(zone["consolidate"]["replay_queue_depth"], 5)

    def test_probe_recall_uses_explicit_episodic(self) -> None:
        state = self._state()
        probe = probe_recall_uses_episodic_scope(state)
        self.assertTrue(probe["pass"])
        self.assertTrue(probe["explicit_episodic"])
        rep = apply_bind_scope(state, tract="recall", client_zone="executive")
        self.assertTrue(rep["scope"]["explicit_episodic"])

    def test_probe_math_habit_implicit_procedural(self) -> None:
        state = self._state()
        probe = probe_math_habit_implicit(state)
        self.assertTrue(probe["pass"])
        self.assertGreater(probe["procedural_scale"], 1.0)
        self.assertFalse(probe["requires_new_l3_lemma"])

    def test_forget_snapshot_and_honesty_gate_healthy(self) -> None:
        state = self._state()
        state["consolidation"] = {
            "last_sleep": {
                "merged": 0,
                "pending": 0,
                "immutable_skipped": [],
                "items": [],
            }
        }
        snap = forget_snapshot(state)
        self.assertEqual(snap["canon_immutable_touched"], 0)
        self.assertEqual(snap["pathology_mode"], "none")
        self.assertEqual(snap["alpha_retain"], DEFAULT_PRIMING_ALPHA)
        honesty = build_forget_honesty_report(state)
        self.assertTrue(honesty["gate_pass"])
        self.assertTrue(honesty["probes"]["canon_immutable_touched"]["pass"])
        self.assertTrue(honesty["probes"]["priming_alpha"]["pass"])

    def test_sleep_writes_consolidate_and_honesty_artifact(self) -> None:
        if not BUNDLE.is_file():
            self.skipTest("math bundle missing")
        bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
        state = self._state()
        before = len(hippo_episodes(state))
        append_episode(
            state,
            cue="3",
            surface_attempt="?",
            correct="3",
            lattice_id="schema-math",
            concept_id="math.num.three",
            scene="lab",
        )
        self.assertEqual(len(hippo_episodes(state)), before + 1)
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            rep = run_sleep(state, bundle, strength=2, store_dir=store)
            self.assertTrue(rep.get("immutable_skipped"))
            self.assertIn("forget_honesty", rep)
            self.assertEqual(rep["forget_honesty"]["canon_immutable_touched"], 0)
            zone = ensure_memory_zone(state)
            self.assertIn("last_report", zone["consolidate"])
            self.assertTrue((store / FORGET_HONESTY_JSON).is_file())
            artifact = json.loads((store / FORGET_HONESTY_JSON).read_text(encoding="utf-8"))
            self.assertTrue(artifact["gate_pass"])

    def test_finalize_memory_sleep_reports_on_state(self) -> None:
        state = self._state()
        sleep_report = {"merged": 1, "pending": 2, "immutable_skipped": [], "items": []}
        with tempfile.TemporaryDirectory() as tmp:
            out = finalize_memory_sleep_reports(state, sleep_report, store_dir=Path(tmp))
            self.assertIn("consolidate", out)
            self.assertTrue(out["honesty"]["gate_pass"])
            self.assertIn("forget_honesty", sleep_report)
            path = write_forget_honesty_report(Path(tmp), out["honesty"])
            self.assertTrue(path.is_file())

    def test_probe_canon_immutable_touched_counts_merged_items(self) -> None:
        state = self._state()
        state["consolidation"] = {
            "last_sleep": {
                "items": [{"lattice_id": "schema-math", "kind": "episode"}],
                "immutable_skipped": [],
            }
        }
        probe = probe_canon_immutable_touched(state)
        self.assertGreater(probe["canon_immutable_touched"], 0)
        self.assertFalse(probe["pass"])


if __name__ == "__main__":
    unittest.main()
