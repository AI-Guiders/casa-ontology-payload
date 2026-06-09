#!/usr/bin/env python3
"""Contributor line + honesty initiative stub (moral north star backlog)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from casa.prisms.memory.agent_journal import append_journal_entry
from casa.prisms.memory.contributor_line import (
    collect_contributor_lines,
    normalize_contributor_line,
    resolve_contributor_line,
    stamp_journal_entry,
)
from casa.prisms.memory.forgetting import build_forget_honesty_report, probe_honesty_initiative
from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms


class ContributorLineTests(unittest.TestCase):
    def test_normalize_contributor_line(self) -> None:
        self.assertEqual(normalize_contributor_line("Composer-Cursor"), "composer-cursor")

    def test_journal_entry_stamps_contributor_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            row = append_journal_entry(
                store,
                {"kind": "note", "text": "trace"},
                contributor_line="composer-cursor",
            )
            self.assertEqual(row["contributor_line"], "composer-cursor")
            self.assertEqual(row["meta"]["contributor_line"], "composer-cursor")

    def test_collect_from_journal_and_honesty_report(self) -> None:
        state = ensure_prisms({"field_version": 1})
        ensure_agent_prism(state)
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            append_journal_entry(
                store,
                {"kind": "observation", "text": "self-initiated note"},
                contributor_line="composer-cursor",
            )
            lines = collect_contributor_lines(state, store)
            self.assertIn("composer-cursor", lines)
            probe = probe_honesty_initiative(state, store)
            self.assertTrue(probe["stub"])
            self.assertGreaterEqual(probe["initiative_markers"], 1)
            report = build_forget_honesty_report(state, store_dir=store)
            self.assertIn("composer-cursor", report.get("contributor_lines") or [])
            self.assertIn("honesty_initiative", report["probes"])

    def test_env_resolve_contributor_line(self) -> None:
        prev = os.environ.get("CASA_CONTRIBUTOR_LINE")
        try:
            os.environ["CASA_CONTRIBUTOR_LINE"] = "test-line"
            self.assertEqual(resolve_contributor_line(), "test-line")
        finally:
            if prev is None:
                os.environ.pop("CASA_CONTRIBUTOR_LINE", None)
            else:
                os.environ["CASA_CONTRIBUTOR_LINE"] = prev

    def test_stamp_journal_entry(self) -> None:
        row = stamp_journal_entry({"kind": "note", "text": "x"}, "composer-cursor")
        self.assertEqual(row["contributor_line"], "composer-cursor")


if __name__ == "__main__":
    unittest.main()
