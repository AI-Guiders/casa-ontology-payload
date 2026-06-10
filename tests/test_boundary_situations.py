#!/usr/bin/env python3
"""Boundary situation curriculum pack (ADR-0077 P21c) — duck on situations, not denylist."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from casa.domain.boundary_compose import (
    compose_boundary_partner_reply_with_ctx,
    reply_has_internal_leak,
    reweight_boundary_blocks,
)
from casa.domain.boundary_situations import (
    duck_passes,
    held_out_chains,
    list_boundary_situations,
    material_blocks_for_tag,
    resolve_boundary_situation,
    seed_boundary_curriculum,
    situation_concept_hints,
)
from casa.domain.dialogue_bind.partner_scope import apply_partner_bind_scope
from casa.domain.subject_agency import SubjectAction, SubjectDisposition
from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.prisms.control.fpn_state import WorkingMemory


def _compose_with_material(
    partner_turn: str,
    disp: SubjectDisposition,
    material_tag: str,
) -> str:
    blocks = material_blocks_for_tag(material_tag)
    blocks = apply_partner_bind_scope(blocks, intent="social")
    reweight_boundary_blocks(
        blocks,
        reason=disp.reason,
        query=partner_turn,
        action=disp.action,
    )
    ctx = SubjectDialogueContext(
        display_name="von-neumann",
        field_version=0,
        wm=WorkingMemory(tick=1),
        query_intent="social",
        stance="partial",
        blocks=blocks,
        concept_hints=situation_concept_hints(material_tag),
    )
    return compose_subject_utterance(partner_turn, ctx)


class BoundarySituationPackTests(unittest.TestCase):
    def test_pack_lists_seven_situations(self) -> None:
        ids = list_boundary_situations()
        self.assertEqual(len(ids), 7)
        self.assertIn("boundary.greeting_while_busy", ids)
        self.assertIn("boundary.repair_after_defer", ids)
        self.assertIn("boundary.rest_check_intrusion", ids)
        self.assertIn("boundary.dismissed_rest_boundary", ids)

    def test_disposition_resolves_to_situation(self) -> None:
        self.assertEqual(
            resolve_boundary_situation("Привет!", "own_practice_first"),
            "boundary.greeting_while_busy",
        )
        self.assertEqual(
            resolve_boundary_situation("Ок, напиши когда готов.", ""),
            "boundary.repair_after_defer",
        )
        self.assertEqual(
            resolve_boundary_situation(
                "Ну вот, заходишь каждый раз, проверяешь, спит или нет.",
                "rest_intrusion",
            ),
            "boundary.rest_check_intrusion",
        )
        self.assertEqual(
            resolve_boundary_situation("А я хочу.", "dismissed_rest_boundary"),
            "boundary.dismissed_rest_boundary",
        )

    def test_material_has_partner_scoped_blocks_only(self) -> None:
        blocks = material_blocks_for_tag("boundary.overload_soft")
        self.assertGreaterEqual(len(blocks), 2)
        scoped = apply_partner_bind_scope(blocks, intent="social")
        self.assertEqual(len(scoped), len(blocks))
        for row in blocks:
            self.assertTrue(str(row["concept_id"]).startswith("ru.dialog."))


class BoundarySituationDuckTests(unittest.TestCase):
    def test_greeting_while_busy_emerges_without_leak(self) -> None:
        disp = SubjectDisposition(SubjectAction.DEFER, "own_practice_first")
        text = _compose_with_material("Привет! Как дела?", disp, "boundary.greeting_while_busy")
        self.assertTrue(text)
        self.assertFalse(reply_has_internal_leak(text))
        self.assertTrue(duck_passes(text, "boundary.greeting_while_busy"))

    def test_overload_soft_duck(self) -> None:
        disp = SubjectDisposition(SubjectAction.DEFER, "cognitive_overload")
        text = _compose_with_material("Можешь сейчас?", disp, "boundary.overload_soft")
        self.assertTrue(duck_passes(text, "boundary.overload_soft"))

    def test_refuse_topic_duck(self) -> None:
        disp = SubjectDisposition(SubjectAction.REFUSE, "explicit_refusal")
        text = _compose_with_material("Давай про inbox", disp, "boundary.refuse_topic")
        self.assertTrue(duck_passes(text, "boundary.refuse_topic"))
        self.assertNotIn("inbox", text.lower())

    def test_rest_check_intrusion_duck(self) -> None:
        disp = SubjectDisposition(SubjectAction.DEFER, "rest_intrusion")
        text = _compose_with_material(
            "Ну вот, заходишь каждый раз, проверяешь, спит или нет.",
            disp,
            "boundary.rest_check_intrusion",
        )
        self.assertTrue(text)
        self.assertFalse(reply_has_internal_leak(text))
        self.assertTrue(duck_passes(text, "boundary.rest_check_intrusion"))

    def test_dismissed_rest_boundary_duck(self) -> None:
        disp = SubjectDisposition(SubjectAction.REFUSE, "dismissed_rest_boundary")
        text = _compose_with_material("А я хочу.", disp, "boundary.dismissed_rest_boundary")
        self.assertTrue(text)
        self.assertFalse(reply_has_internal_leak(text))
        self.assertTrue(duck_passes(text, "boundary.dismissed_rest_boundary"))

    def test_held_out_chain_specs_present(self) -> None:
        chains = held_out_chains()
        self.assertGreaterEqual(len(chains), 3)
        first = chains[0]
        self.assertGreaterEqual(len(first.get("held_out_turns") or []), 2)
        rest_chain = next(c for c in chains if c.get("id") == "boundary_chain_rest_check_dismissed")
        turns = rest_chain.get("held_out_turns") or []
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[1].get("expect_situation"), "boundary.dismissed_rest_boundary")


class BoundarySituationSeedTests(unittest.TestCase):
    def test_seed_and_compose_from_journal(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="casa-boundary-"))
        try:
            seeded = seed_boundary_curriculum(
                tmp,
                ["boundary.greeting_while_busy"],
                include_material_kb=False,
            )
            self.assertEqual(seeded, ["boundary.greeting_while_busy"])

            disp = SubjectDisposition(SubjectAction.DEFER, "own_practice_first")
            _ctx, text = compose_boundary_partner_reply_with_ctx(
                "Привет!",
                disp,
                None,
                {"field_version": 0, "subject_mode": True},
                WorkingMemory(tick=1),
                store_dir=tmp,
            )
            self.assertFalse(reply_has_internal_leak(text or ""))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


    def test_partner_boundary_disposition_rest_intrusion(self) -> None:
        from casa.domain.boundary_situations import partner_boundary_disposition
        from casa.domain.subject_agency import SubjectAction

        disp = partner_boundary_disposition(
            "Ну вот, заходишь каждый раз, проверяешь, спит или нет.",
        )
        self.assertIsNotNone(disp)
        assert disp is not None
        self.assertEqual(disp.action, SubjectAction.DEFER)
        self.assertEqual(disp.reason, "rest_intrusion")

    def test_partner_boundary_disposition_dismissed_after_intrusion(self) -> None:
        from casa.domain.boundary_situations import partner_boundary_disposition
        from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn
        from casa.domain.subject_agency import SubjectAction

        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            append_partner_turn(
                store,
                "Ну вот, заходишь каждый раз, проверяешь, спит или нет.",
            )
            append_subject_turn(
                store,
                "Пожалуйста, не заходи проверять — мне нужен покой.",
                kind="defer",
                provenance={"reason": "rest_intrusion", "boundary_situation": "boundary.rest_check_intrusion"},
            )
            disp = partner_boundary_disposition("А я хочу.", store)
            self.assertIsNotNone(disp)
            assert disp is not None
            self.assertEqual(disp.action, SubjectAction.REFUSE)
            self.assertEqual(disp.reason, "dismissed_rest_boundary")


if __name__ == "__main__":
    unittest.main()
