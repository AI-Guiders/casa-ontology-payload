"""Emergent names — co-occurrence in episode scene, not teacher links."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_names_extract import extract_emergent_names_from_episodes, parse_bilingual_numeral_scene
from casa.prisms.memory.f0_stack import decode_f0_lattice
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


def test_parse_bilingual_scene() -> None:
    ru, en = parse_bilingual_numeral_scene("ru: пятнадцать — пять | en: fifteen — five-teen")
    assert ru == "пятнадцать"
    assert en == "fifteen"


def test_extract_names_from_episode_scene_not_links() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle, copies=2)
    append_episode(
        state,
        cue="15",
        surface_attempt="?",
        correct="15",
        lattice_id="schema-math",
        concept_id="math.num.fifteen",
        scene="ru: пятнадцать — пять на десятью | en: fifteen — five-teen (5+10)",
        form_extract_allowed=True,
    )
    from casa.prisms.memory.memory_prisms import prism_hippo

    lats = memory_lattices(state)
    rep = extract_emergent_names_from_episodes(
        lats, prism_hippo(state).get("episodes") or [], bundle, state, copies=4
    )
    assert rep
    dec = decode_f0_lattice(lats["schema-math"], min_votes=1)
    edges = set(dec.get("edges") or [])
    assert "math.num.fifteen|names|lang.word.fifteen" in edges


def test_sleep_mints_names_without_teacher_links() -> None:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    append_episode(
        state,
        cue="11",
        surface_attempt="?",
        correct="11",
        lattice_id="schema-math",
        concept_id="math.num.eleven",
        scene="ru: одиннадцать — один на десятью | en: eleven — one left",
    )
    sleep = run_sleep(state, bundle)
    assert any(x.get("kind") == "emergent_names" for x in sleep.get("items") or [])
    dec = decode_f0_lattice(memory_lattices(state)["schema-math"])
    assert "math.num.eleven|names|lang.word.eleven" in set(dec.get("edges") or [])
    assert "math.num.eleven|names|lang.word.одиннадцать" in set(dec.get("edges") or [])
