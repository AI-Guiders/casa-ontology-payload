#!/usr/bin/env python3
"""Memory Zone spawn + migrate (ADR-0068 P12a)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.prisms.intelligence.migrate import migrate_intelligence_zones
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism, load_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.zone import ensure_memory_zone, spawn_memory_zone
from casa.prisms.shared.store_boot import boot_store


class MemoryZoneTests(unittest.TestCase):
    def test_spawn_memory_zone_indexes_prisms(self) -> None:
        state = ensure_prisms({"field_version": 0})
        ensure_agent_prism(state)
        rep = spawn_memory_zone(state)
        zone = ensure_memory_zone(state)
        self.assertIn("agent-memory-core", agent_lattices(state))
        self.assertIn("agent-memory-sandbox", agent_lattices(state))
        self.assertEqual(zone["core_lattice_id"], rep["core_lattice_id"])
        self.assertIn("ltm_lattice_ids", zone["explicit"]["semantic"])
        self.assertIn("hippo_lattice_ids", zone["explicit"]["episodic"])
        self.assertEqual(zone["immutable"]["write_gate_ref"], "genetic.promote_canon")

    def test_migrate_spawns_memory_and_genetic_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "bundles").mkdir(parents=True)
            rep = migrate_intelligence_zones(store, tick=3)
            boot = boot_store(store, prefer_field_state=True)
            load_agent_prism(store, boot["state"])
            state = boot["state"]
            from casa.prisms.intelligence.model import intelligence_root

            zones = intelligence_root(state)
            self.assertIn("memory", zones)
            self.assertIn("genetic", zones)
            self.assertEqual(rep["intelligence_zones_version"], 5)
            self.assertIn("agent-memory-core", agent_lattices(state))


if __name__ == "__main__":
    unittest.main()
