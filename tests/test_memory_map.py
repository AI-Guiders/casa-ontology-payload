#!/usr/bin/env python3
"""Memory map summary stays compact vs full inventory."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa.prisms.memory.memory_map import (
    MEMORY_MAP_SUMMARY_JSON,
    build_memory_map,
    build_memory_map_summary,
    write_memory_map_artifacts,
)
from casa.prisms.memory.memory_prisms import ensure_prisms


class MemoryMapTests(unittest.TestCase):
    def test_summary_is_much_smaller_than_full_map(self) -> None:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            full = build_memory_map(store, state)
            full["lattice_stack"] = [{"id": f"L{i}", "memory_layer": "memory.lexicon", "token_count": i} for i in range(120)]
            summary = build_memory_map_summary(full)
            self.assertEqual(summary["kind"], "lexicon_memory_map_summary")
            self.assertEqual(summary["lattice_count"], 120)
            self.assertNotIn("lattice_stack", summary)
            full_bytes = len(json.dumps(full, ensure_ascii=False).encode("utf-8"))
            summary_bytes = len(json.dumps(summary, ensure_ascii=False).encode("utf-8"))
            self.assertLess(summary_bytes, full_bytes // 10)

    def test_write_artifacts_creates_md_and_summary(self) -> None:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 2})
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            memory_map = build_memory_map(store, state)
            paths = write_memory_map_artifacts(store, memory_map)
            self.assertTrue(Path(paths["md"]).is_file())
            self.assertTrue(Path(paths["summary"]).name == MEMORY_MAP_SUMMARY_JSON)


if __name__ == "__main__":
    unittest.main()
