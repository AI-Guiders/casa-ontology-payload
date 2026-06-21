"""Concept-mediated RU<->EN term translation over the field's name edges."""

from __future__ import annotations

import json

from casa.curriculum.teach import teach
from casa.curriculum.translate import concepts_for_term, script_of, translate_term
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def _taught_bilingual() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    # teach one concept its RU + EN word via a bilingual scene
    teach(
        state,
        concept_id="math.num.eleven",
        lattice_id="schema-math",
        examples=[{"cue": "11", "correct": "11", "scene": "ru: одиннадцать — один на десятью | en: eleven — one left"}],
        bundle=bundle,
    )
    return state


def test_script_detection() -> None:
    assert script_of("eleven") == "latn"
    assert script_of("одиннадцать") == "cyrl"


def test_shared_concept_links_both_languages() -> None:
    state = _taught_bilingual()
    assert "math.num.eleven" in concepts_for_term(state, "schema-math", "одиннадцать")
    assert "math.num.eleven" in concepts_for_term(state, "schema-math", "eleven")


def test_translate_ru_to_en() -> None:
    state = _taught_bilingual()
    assert "eleven" in translate_term(state, "schema-math", "одиннадцать", to_script="latn")


def test_translate_en_to_ru() -> None:
    state = _taught_bilingual()
    assert "одиннадцать" in translate_term(state, "schema-math", "eleven", to_script="cyrl")


def test_translate_unknown_term_is_empty_not_invented() -> None:
    # bounded to what the field knows — no hallucinated translation
    state = _taught_bilingual()
    assert translate_term(state, "schema-math", "несуществующее", to_script="latn") == []
