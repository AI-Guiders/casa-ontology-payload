"""Spanish parse layer (lang="es") — the same meaning graph as the RU/EN equivalents.

Spanish shares the Latin script with English, so the language is DECLARED by the caller
(the validator knows each side's language) instead of detected by script. The tests pin:
every supported ES clause form parses to a fingerprint byte-identical to its EN/RU twin,
the homograph guard blocks English readings (ES «red» is not the colour), and lang=None
keeps the old behaviour exactly.
"""

from __future__ import annotations

import pytest

from casa.curriculum.parse import parse_fingerprint, parse_graph, parse_rule, resolve_token
from casa.curriculum.world import build_meaning_state


@pytest.fixture(scope="module")
def world():
    state, lat = build_meaning_state()
    return state, lat


def _key(state, lat, text, lang=None):
    return parse_fingerprint(state, lat, text, lang=lang)["key"]


# --- ES clause forms parse to the SAME fingerprint as their EN twins -------------------
@pytest.mark.parametrize("es_text,en_text", [
    ("la manzana en la mesa", "the apple is on the table"),          # locative
    ("no abra el archivo", "do not open the file"),                  # imperative + negation
    ("guarde el documento", "save the document"),                    # imperative
    ("5 ml de agua en la mesa", "5 ml of water on the table"),       # measure + locative
    ("dos manzanas en la mesa", "two apples on the table"),          # count + plural lemma
    ("el archivo está abierto", "the file is open"),                 # predicative state
    ("el gato vive en la casa", "the cat lives in the house"),       # lives_in absorbs prep
    ("la mesa está hecha de madera", "the table is made of wood"),   # made_of copula
])
def test_es_en_same_fingerprint(world, es_text, en_text):
    state, lat = world
    assert _key(state, lat, es_text, lang="es") == _key(state, lat, en_text)


def test_es_ru_same_fingerprint(world):
    state, lat = world
    assert _key(state, lat, "la manzana en la mesa", lang="es") == _key(state, lat, "яблоко на столе")


def test_es_negation_flips_polarity(world):
    state, lat = world
    g = parse_graph(state, lat, "no abra el archivo", lang="es")
    assert any(e.get("satisfied") for e in g["edges"])
    assert all(e["polarity"] == "neg" for e in g["edges"])


def test_es_threshold_parses(world):
    state, lat = world
    # «el agua es más de 10 ml» — numeric threshold via the ES comparison layer
    g = parse_graph(state, lat, "agua más de 10 ml", lang="es")
    rels = {e["rel"] for e in g["edges"] if e.get("satisfied")}
    assert "num_gt" in rels


def test_es_homograph_red_refuses(world):
    state, lat = world
    # ES «red» = network — must NOT resolve to the EN colour concept, must not become an attr
    assert resolve_token(state, lat, "red", lang="es") is None
    g = parse_graph(state, lat, "la manzana red en la mesa", lang="es")
    apple = g["nodes"].get("concept.apple") or {}
    assert "red" not in (apple.get("attrs") or [])


def test_en_red_still_an_attribute(world):
    state, lat = world  # without lang, nothing changed
    g = parse_graph(state, lat, "the red apple is on the table")
    assert "red" in (g["nodes"]["concept.apple"].get("attrs") or [])


def test_es_rule_si_entonces(world):
    state, lat = world
    rule = parse_rule(state, lat, "si el archivo está abierto entonces la ventana está abierta", lang="es")
    assert rule is not None
    ante = {e["rel"] for e in rule["antecedent"]["edges"] if e.get("satisfied")}
    assert "has_state" in ante


def test_lang_none_unchanged(world):
    state, lat = world  # the ES layer must not leak into the default path
    g = parse_graph(state, lat, "en la mesa")  # «en» is not an EN/RU preposition
    assert not any(e.get("satisfied") for e in g.get("edges", []))
