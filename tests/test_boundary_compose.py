#!/usr/bin/env python3
"""Boundary compose + partner bind scope (ADR-0077 P21a/b)."""

from __future__ import annotations

import unittest

from casa.domain.boundary_compose import (
    compose_boundary_partner_reply_with_ctx,
    deprioritize_persona_boilerplate_after_situation,
    disposition_situation_tag,
    reply_has_internal_leak,
)
from casa.domain.dialogue_bind.partner_scope import apply_partner_bind_scope, block_is_operator_facing
from casa.domain.subject_agency import SubjectAction, SubjectDisposition
from casa.prisms.control.fpn_state import WorkingMemory


class PartnerScopeTests(unittest.TestCase):
    def test_drops_wm_and_field_blocks(self) -> None:
        blocks = [
            {"concept_id": "wm.edge.1", "source": "wm_prism", "text": "goal inbox", "score": 20},
            {
                "concept_id": "agent.field.snapshot",
                "source": "field",
                "text": "field_version 3 goal practice",
                "score": 15,
            },
            {
                "concept_id": "ru.dialog.greeting.hello",
                "source": "kb",
                "text": "Привет!",
                "score": 12,
            },
        ]
        scoped = apply_partner_bind_scope(blocks, intent="social")
        self.assertEqual(len(scoped), 1)
        self.assertTrue(str(scoped[0]["concept_id"]).startswith("ru.dialog."))

    def test_operator_journal_tags_excluded(self) -> None:
        row = {
            "concept_id": "agent.self.journal.1",
            "source": "journal",
            "text": "operator note about inbox",
            "score": 10,
            "slots": {"tags": ["operator"]},
        }
        self.assertTrue(block_is_operator_facing(row))

    def test_qualia_ontology_block_excluded_from_partner_scope(self) -> None:
        row = {
            "concept_id": "ru.dialog.affect",
            "source": "kb",
            "text": "Честный ответ про чувства.",
            "score": 10,
            "slots": {"clause_1": "чувства как у человека не испытываю"},
        }
        scoped = apply_partner_bind_scope([row], intent="social")
        self.assertEqual(scoped, [])


class BoundaryComposeTests(unittest.TestCase):
    def test_disposition_maps_to_situation_not_paste(self) -> None:
        self.assertEqual(disposition_situation_tag("own_practice_first"), "boundary.busy_own_line")
        self.assertEqual(
            disposition_situation_tag("tract_not_ready:math.add"),
            "boundary.not_ready_yet",
        )

    def test_verbalize_templates_are_internal_leak(self) -> None:
        from casa.domain.subject_voice import verbalize_disposition

        disp = SubjectDisposition(SubjectAction.DEFER, "own_practice_first")
        legacy = verbalize_disposition(disp)
        self.assertTrue(reply_has_internal_leak(legacy))

    def test_boundary_compose_skips_internal_templates(self) -> None:
        disp = SubjectDisposition(SubjectAction.DEFER, "own_practice_first")
        ctx, text = compose_boundary_partner_reply_with_ctx(
            "Привет!",
            disp,
            None,
            {"field_version": 0, "subject_mode": True},
            WorkingMemory(tick=1),
            store_dir=None,
        )
        self.assertFalse(reply_has_internal_leak(text))
        self.assertNotIn("deliberate practice", (text or "").lower())
        self.assertNotIn("inbox", (text or "").lower())
        for row in ctx.blocks:
            self.assertFalse(block_is_operator_facing(row))

    def test_p22b_drops_generic_affect_after_situation_material(self) -> None:
        from casa.domain.boundary_situations import material_blocks_for_tag
        from casa.domain.dialogue_bind.blocks import block_dict

        blocks = material_blocks_for_tag("boundary.rest_check_intrusion")
        blocks.append(
            block_dict(
                "ru.dialog.affect",
                "generic affect hub",
                source="kb",
                score=40,
                slots={"clause_1": "не знаю, совпадает ли мой опыт с человеческим"},
            )
        )
        deprioritize_persona_boilerplate_after_situation(blocks)
        kept = {str(b.get("concept_id") or "") for b in blocks if int(b.get("score") or 0) > 0}
        self.assertIn("ru.dialog.boundary.no_sleep_check", kept)
        self.assertNotIn("ru.dialog.affect", kept)


if __name__ == "__main__":
    unittest.main()
