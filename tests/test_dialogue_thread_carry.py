#!/usr/bin/env python3
"""Plan C — focus_recent thread carry without cue markers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.domain.dialogue_bind.continuer_scoring import apply_continuer_bind_deltas
from casa.domain.dialogue_bind.dialogue import dialogue_continuity_blocks
from casa.domain.dialogue_bind.partner_scoring import continuer_active, thread_continuer_turn
from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn


class DialogueThreadCarryTest(unittest.TestCase):
    def test_focus_recent_without_cue_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            append_partner_turn(store, "Как ты?")
            append_subject_turn(
                store,
                "Сейчас на связи по полю.",
                kind="reply",
                provenance={
                    "partner_speech_acts": ["how_are_you"],
                    "dialog_hubs": ["ru.dialog.how_are_you"],
                },
            )
            query = "Хорошо, я тоже не знаю, но он не обязан совпадать"
            blocks = dialogue_continuity_blocks(store, query)
            ids = [str(b.get("concept_id") or "") for b in blocks]
            self.assertIn("dialog.context.focus_recent", ids)
            self.assertIn("subject.dialog.partner_recent", ids)
            focus = next(b for b in blocks if b["concept_id"] == "dialog.context.focus_recent")
            slots = focus.get("slots") or {}
            self.assertIn("ru.dialog.how_are_you", str(slots.get("thread_terms") or ""))

    def test_thread_continuer_active_without_substring_markers(self) -> None:
        blocks = [
            {
                "concept_id": "dialog.context.focus_recent",
                "text": "Текущий фокус диалога: ru.dialog.how_are_you.",
                "source": "dialogue",
                "score": 20,
                "slots": {"thread_overlap": "12", "thread_age": "0"},
            }
        ]
        self.assertTrue(continuer_active(blocks))
        self.assertTrue(thread_continuer_turn(blocks, "случайная реплика без маркеров"))

    def test_continuer_scoring_uses_decay_not_flat_seventy_two(self) -> None:
        blocks = [
            {
                "concept_id": "dialog.context.focus_recent",
                "text": "focus",
                "source": "dialogue",
                "score": 12,
                "slots": {"thread_age": "2", "thread_overlap": "10"},
            },
            {
                "concept_id": "ru.dialog.self",
                "text": "self",
                "source": "kb",
                "score": 80,
                "slots": {"situation": "x", "hedge": "a", "predicate": "b", "scope": "c"},
            },
        ]
        apply_continuer_bind_deltas(blocks, "не связанный офф-топик запрос", intent="social")
        focus_score = next(b["score"] for b in blocks if b["concept_id"] == "dialog.context.focus_recent")
        self.assertGreater(focus_score, 40)
        self.assertLess(focus_score, 120)
        self_score = next(b["score"] for b in blocks if b["concept_id"] == "ru.dialog.self")
        self.assertLess(self_score, 80)


if __name__ == "__main__":
    unittest.main()
