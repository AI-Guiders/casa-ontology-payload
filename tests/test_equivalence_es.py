"""Cross-lingual EN↔ES equivalence triage — the benchmark's core path.

The validator receives a pair with DECLARED side languages (an EMEA row knows which side
is English and which Spanish): ``check_equivalence(..., langs=("en", "es"))``. The tests
pin the dangerous-class kernel across the EN↔ES boundary: polarity (dropped «no»),
quantity (2↔3), unit (ml↔mg) — plus honest ❓ when a side does not parse.
"""

from __future__ import annotations

import pytest

from casa.curriculum.equivalence import check_equivalence
from casa.curriculum.world import build_meaning_state


@pytest.fixture(scope="module")
def world():
    state, lat = build_meaning_state()
    return state, lat


def _check(world, en, es):
    state, lat = world
    return check_equivalence(state, lat, en, es, langs=("en", "es"))


def test_equivalent_cross_lingual(world):
    r = _check(world, "the apple is on the table", "la manzana en la mesa")
    assert r["verdict"] == "equivalent"


def test_equivalent_negated_both_sides(world):
    # correctly negating translation is NOT a divergence
    r = _check(world, "do not open the file", "no abra el archivo")
    assert r["verdict"] == "equivalent"


def test_dropped_negation_is_polarity(world):
    r = _check(world, "do not open the file", "abra el archivo")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "polarity" for d in r["divergences"])


def test_swapped_count_is_quantity(world):
    r = _check(world, "two apples on the table", "tres manzanas en la mesa")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "quantity" for d in r["divergences"])


def test_swapped_unit_is_unit(world):
    r = _check(world, "5 ml of water on the table", "5 mg de agua en la mesa")
    assert r["verdict"] == "divergent"
    assert any(d["class"] == "unit" for d in r["divergences"])


def test_unparsed_side_is_uncheckable(world):
    r = _check(world, "the apple is on the table", "frase sin estructura reconocible")
    assert r["verdict"] == "uncheckable"


def test_langs_omitted_backward_compatible(world):
    state, lat = world  # old two-argument-style call still works (RU↔EN path untouched)
    r = check_equivalence(state, lat, "яблоко на столе", "the apple is on the table")
    assert r["verdict"] == "equivalent"
