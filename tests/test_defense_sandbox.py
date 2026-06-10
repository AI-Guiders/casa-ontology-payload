#!/usr/bin/env python3
"""Defense sandbox rechannel promote (ADR-0076 P20b)."""

from __future__ import annotations

import unittest

from casa.domain.subject_agency import SubjectAction, evaluate_external_proposal
from casa.prisms.affect import spawn_emotional_zone
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.defense import (
    list_defense_sandbox_state,
    place_defense_rechannel_edge,
    promote_rechannel_experiment,
    sandbox_bump_rechannel_score,
    sandbox_record_rechannel,
    spawn_defense_scratch_lattice,
    try_auto_promote_rechannel_experiments,
)
from casa.prisms.defense.trauma_cement import trauma_edges
from casa.prisms.intelligence.defense_zone import ensure_defense_zone
from casa.prisms.memory.memory_prisms import ensure_prisms


class DefenseSandboxTests(unittest.TestCase):
    def _painful_state(self) -> dict:
        state = ensure_prisms({"field_version": 0})
        spawn_emotional_zone(
            state,
            config={"initial_axes": {"valence": -0.4, "arousal": 0.6, "security": 0.2}},
        )
        spawn_defense = __import__(
            "casa.prisms.intelligence.defense_zone", fromlist=["spawn_defense_zone"]
        ).spawn_defense_zone
        spawn_defense(state)
        return state

    def test_sublimation_defer_records_sandbox(self) -> None:
        state = self._painful_state()
        wm = WorkingMemory(step_capability="math")
        disp = evaluate_external_proposal(state, wm, load_rep={"overloaded": False})
        self.assertEqual(disp.action, SubjectAction.DEFER)
        self.assertEqual(disp.reason, "defense_sublimation")
        zone = ensure_defense_zone(state)
        experiments = zone.get("sandbox", {}).get("experiments") or []
        self.assertGreaterEqual(len(experiments), 1)
        self.assertEqual(experiments[-1].get("mechanism"), "sublimation")
        self.assertTrue(experiments[-1].get("lattice_id"))
        snap = list_defense_sandbox_state(state)
        self.assertGreaterEqual(len(snap.get("lattices") or []), 1)

    def test_spawn_scratch_lattice_and_place_edge(self) -> None:
        state = self._painful_state()
        lid = spawn_defense_scratch_lattice(state, tick=2, topic_slug="math-coping")
        rep = place_defense_rechannel_edge(
            state,
            threat_concept="agent.defense.lab.threat.strah",
            proxy_concept="math.rechannel.coping",
            tick=2,
            lattice_id=lid,
        )
        self.assertIn("edge_id", rep)
        snap = list_defense_sandbox_state(state)
        lat = next(x for x in snap["lattices"] if x["lattice_id"] == lid)
        self.assertGreaterEqual(lat["edge_count"], 1)

    def test_promote_with_lattice_evidence(self) -> None:
        state = self._painful_state()
        lid = spawn_defense_scratch_lattice(state, tick=1, topic_slug="evidence")
        place_defense_rechannel_edge(
            state,
            threat_concept="agent.defense.lab.threat.bol",
            proxy_concept="math.rechannel.evidence",
            tick=1,
            lattice_id=lid,
        )
        row = sandbox_record_rechannel(
            state,
            threat_cues=["боль"],
            proxy_prefixes=["math."],
            score=0.62,
            tick=2,
            lattice_id=lid,
        )
        rep = promote_rechannel_experiment(state, row.experiment_id, tick=3)
        self.assertTrue(rep.get("promoted"))

    def test_promote_rechannel_to_core(self) -> None:
        state = self._painful_state()
        row = sandbox_record_rechannel(
            state,
            threat_cues=["страх", "боль"],
            proxy_prefixes=["math."],
            rechannel_domain="math",
            rechannel_tract="math",
            tick=3,
            score=0.5,
        )
        sandbox_bump_rechannel_score(state, tract="math", delta=0.2)
        rep = promote_rechannel_experiment(state, row.experiment_id, tick=4)
        self.assertIsNotNone(rep)
        self.assertTrue(rep.get("promoted"))
        edges = trauma_edges(state)
        self.assertGreaterEqual(len(edges), 1)
        self.assertTrue(any("страх" in (e.get("threat_cues") or []) for e in edges))

    def test_auto_promote_on_tick_threshold(self) -> None:
        state = self._painful_state()
        row = sandbox_record_rechannel(
            state,
            threat_cues=["страх"],
            proxy_prefixes=["math."],
            score=0.7,
            tick=1,
        )
        promoted = try_auto_promote_rechannel_experiments(state, tick=2)
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0]["experiment_id"], row.experiment_id)

    def test_promote_blocked_below_theta(self) -> None:
        state = self._painful_state()
        row = sandbox_record_rechannel(state, threat_cues=["боль"], score=0.2, tick=1)
        rep = promote_rechannel_experiment(state, row.experiment_id, tick=2)
        self.assertIsNotNone(rep)
        self.assertFalse(rep.get("promoted"))


if __name__ == "__main__":
    unittest.main()
