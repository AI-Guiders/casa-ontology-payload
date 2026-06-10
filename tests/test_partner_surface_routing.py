#!/usr/bin/env python3
"""Partner surface routing from bundle claims (not Python oracles)."""

from __future__ import annotations

from casa.domain.partner_cue_policy import social_concept_for_cue
from casa.prisms.tick.partner_surface_routing import partner_surface_hints
from casa.prisms.tick.semantic_read import concept_hints_from_surface, route_kb_read


def test_partner_surface_hints_from_design_pack():
    assert "lang.word.привет" in partner_surface_hints("Привет!")
    assert "ru.dialog.affect" in partner_surface_hints("Как ты?")
    assert "ru.dialog.self" in partner_surface_hints("Кто ты?")


def test_store_bundle_overrides_design_routing():
    bundle = {
        "claims": [
            {
                "concept_id": "ru.routing.partner_surface.custom",
                "slots": {"route_hint": "ru.dialog.custom.test", "cue_substrings": "тестовая фраза"},
            }
        ]
    }
    hints = partner_surface_hints("это тестовая фраза для проверки", bundle)
    assert hints == ["ru.dialog.custom.test"]
    assert "lang.word.привет" in partner_surface_hints("Привет!", bundle)


def test_social_concept_for_cue_uses_routing():
    assert social_concept_for_cue("Привет!", None) == "lang.word.привет"
    assert social_concept_for_cue("Как ты?", None) == "ru.dialog.affect"
    assert social_concept_for_cue("Кто ты?", None) == "ru.dialog.self"


def test_route_kb_read_includes_surface_hints():
    read = route_kb_read("Как дела?", None)
    assert "ru.dialog.affect" in read.concept_hints


def test_concept_hints_from_surface_backward_compat():
    hints = concept_hints_from_surface("привет")
    assert "lang.word.привет" in hints
