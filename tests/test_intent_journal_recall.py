#!/usr/bin/env python3
"""Intent routing — /remember recall without «на поле …» (recommendations №5)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.domain.dialogue_bind.recall_routing import journal_recall_tract_boost, should_prefer_recall_intent
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.semantic_read import classify_query_intent, route_kb_read


class IntentJournalRecallTests(unittest.TestCase):
    def test_journal_overlap_boosts_recall_tract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = ensure_prisms({"field_version": 0})
            agent_remember(
                store,
                state,
                {
                    "kind": "observation",
                    "text": "Мой любимый цвет — синий, не зелёный.",
                    "tags": ["chat", "correction"],
                },
                persist=True,
            )
            r_boost, _, sources = journal_recall_tract_boost(store, "какой твой любимый цвет синий")
            self.assertGreaterEqual(r_boost, 28)
            self.assertTrue(any("journal" in s for s in sources))

    def test_recall_beats_social_on_taught_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = ensure_prisms({"field_version": 0})
            agent_remember(
                store,
                state,
                {"kind": "observation", "text": "Кодовое слово проекта — оранжевый закат.", "tags": ["chat"]},
                persist=True,
            )
            query = "какое кодовое слово проекта оранжевый"
            intent = classify_query_intent(query, store_dir=store, state=state)
            self.assertIn(intent, ("recall", "explain"))
            read = route_kb_read(query, None, store_dir=store, state=state)
            self.assertIn(read.intent, ("recall", "explain"))
            self.assertTrue(should_prefer_recall_intent(store, query, social_score=32))

    def test_explicit_recall_cue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = ensure_prisms({"field_version": 0})
            agent_remember(
                store,
                state,
                {"kind": "observation", "text": "Партнёр любит чай без сахара.", "tags": ["remember"]},
                persist=True,
            )
            r_boost, _, _ = journal_recall_tract_boost(store, "напомни про чай партнёра")
            self.assertGreaterEqual(r_boost, 30)


if __name__ == "__main__":
    unittest.main()
