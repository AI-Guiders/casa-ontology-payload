#!/usr/bin/env python3
"""Tests for intelligence zone migration (ADR-0061)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.prisms.intelligence.migrate import migrate_intelligence_zones
from casa.prisms.memory.agent_prism import agent_lattices, load_agent_prism
from casa.prisms.shared.store_boot import boot_store


class MigrateIntelligenceZonesTests(unittest.TestCase):
    def test_migrate_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "bundles").mkdir(parents=True)
            rep1 = migrate_intelligence_zones(store, tick=1)
            rep2 = migrate_intelligence_zones(store, tick=2)
            self.assertTrue(rep1["zones"]["emotional"].get("spawned"))
            self.assertFalse(rep2["zones"]["emotional"].get("spawned"))
            boot = boot_store(store, prefer_field_state=True)
            load_agent_prism(store, boot["state"])
            lats = agent_lattices(boot["state"])
            self.assertIn("agent-limbic-core", lats)
            self.assertIn("agent-affect-sandbox", lats)
            self.assertIn("agent-exec-core", lats)
            self.assertIn("agent-social-core", lats)
            self.assertIn("agent-logical-core", lats)
            self.assertIn("agent-character-core", lats)


if __name__ == "__main__":
    unittest.main()
