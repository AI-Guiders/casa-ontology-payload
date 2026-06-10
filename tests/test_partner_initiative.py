#!/usr/bin/env python3
"""Partner initiative outbox + defer_scheduled (partnership design §2)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.domain.boundary_situations import partner_boundary_disposition
from casa.domain.partner_initiative import (
    drain_partner_outbox,
    enqueue_partner_outbox,
    open_partner_thread,
    peek_partner_outbox_pending,
    record_defer_open_thread,
    subject_busy_for_partner,
)
from casa.domain.subject_agency import SubjectAction
from casa.prisms.control.fpn_state import WorkingMemory


class PartnerInitiativeTests(unittest.TestCase):
    def test_outbox_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            eid = enqueue_partner_outbox(store, "Привет, я освободился.", kind="defer_scheduled", tick=3)
            self.assertTrue(eid)
            self.assertEqual(len(peek_partner_outbox_pending(store)), 1)
            drained = drain_partner_outbox(store)
            self.assertEqual(len(drained), 1)
            self.assertEqual(drained[0]["text"], "Привет, я освободился.")
            self.assertEqual(peek_partner_outbox_pending(store), [])

    def test_open_thread_record(self) -> None:
        state: dict = {}
        record_defer_open_thread(state, partner_text="Привет!", reason="own_practice_first", tick=1)
        thread = open_partner_thread(state)
        assert thread is not None
        self.assertEqual(thread["partner_text"], "Привет!")

    def test_greeting_not_busy_skips_boundary_override(self) -> None:
        disp = partner_boundary_disposition(
            "Привет!",
            state={"field_version": 0},
            wm=WorkingMemory(tick=1),
        )
        self.assertIsNone(disp)

    def test_greeting_busy_applies_boundary(self) -> None:
        wm = WorkingMemory(tick=1, goal_id="goal.math.practice", goal="practice:math.add")
        disp = partner_boundary_disposition("Привет!", state={}, wm=wm)
        self.assertIsNotNone(disp)
        assert disp is not None
        self.assertEqual(disp.action, SubjectAction.DEFER)
        self.assertEqual(disp.reason, "own_practice_first")

    def test_partner_line_not_busy_for_greeting(self) -> None:
        wm = WorkingMemory(tick=1, goal_id="goal.dialog.partner", goal="practice:lang.word.foo")
        self.assertFalse(subject_busy_for_partner({}, None, wm))
        disp = partner_boundary_disposition("Привет!", state={}, wm=wm)
        self.assertIsNone(disp)

    def test_subject_busy_from_wm_goal(self) -> None:
        wm = WorkingMemory(tick=1, goal="deliberate practice", goal_id="goal.field.practice")
        self.assertTrue(subject_busy_for_partner({}, None, wm))


if __name__ == "__main__":
    unittest.main()
