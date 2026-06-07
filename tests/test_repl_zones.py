#!/usr/bin/env python3
"""Agent zone_state persist + REPL boot (ADR-0061)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.prism_wire import prism_agent
from casa.prisms.affect import affect_after_turn, core_affect_state, spawn_emotional_zone
from casa.prisms.intelligence.social import spawn_social_zone
from casa.prisms.intelligence.tick import intelligence_before_partner_compose
from casa.prisms.memory.agent_prism import load_agent_prism, save_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms


class AgentZonePersistTests(unittest.TestCase):
    def test_zone_state_roundtrip_in_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "agent" / "lattices").mkdir(parents=True)
            state: dict = {}
            ensure_prisms(state)
            spawn_emotional_zone(state)
            spawn_social_zone(state)
            affect_after_turn(state, "self_failure", tick=1)
            save_agent_prism(store, state)

            fresh: dict = {}
            ensure_prisms(fresh)
            load_agent_prism(store, fresh)
            block = prism_agent(fresh)
            zones = block.get("intelligence_zones") or {}
            self.assertIn("emotional", zones)
            self.assertNotIn("emotional_zone", block)
            self.assertIn(
                "dialog.repair_pending",
                core_affect_state(fresh).episodic,
            )

            manifest = json.loads((store / "agent" / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("zone_state", manifest)

    def test_resolve_ingest_state_loads_agent_prism(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "store_profile.json").write_text(
                json.dumps({"subject_mode": True}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (store / "agent" / "lattices").mkdir(parents=True)
            state: dict = {}
            ensure_prisms(state)
            spawn_emotional_zone(state)
            save_agent_prism(store, state)

            loaded = resolve_ingest_state(store, None)
            block = prism_agent(loaded)
            self.assertIn("emotional", (block.get("intelligence_zones") or {}))


class IntelligenceBeforeComposeTests(unittest.TestCase):
    def test_repair_invite_biases_same_turn(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        spawn_social_zone(state)
        pre = intelligence_before_partner_compose(
            state,
            partner_text="прости, это было неожиданно",
            query_intent="social",
            tick=2,
        )
        self.assertEqual(pre.get("life_event"), "partner_repair_invite")
        from casa.prisms.intelligence.apply import intelligence_compose_deltas

        deltas = intelligence_compose_deltas(state)
        self.assertGreater(deltas.get("subject.dialog.partner_recent", 0), 0)


if __name__ == "__main__":
    unittest.main()
