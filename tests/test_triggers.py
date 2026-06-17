"""Meaning triggers: fire on the extracted context, not the words (paraphrase/language/structure).

A trigger keyed on the meaning of «яблоко на столе» fires for any phrasing or language, and
inside a richer phrase (containment); a structural trigger «agent eats food» fires on any
matching structure. Deterministic and auditable.
"""

from __future__ import annotations

import functools

from casa.curriculum.triggers import labels, new_registry, register
from casa.curriculum.world import build_meaning_state


@functools.lru_cache(maxsize=1)
def _state() -> tuple[dict, str]:
    return build_meaning_state()


def _registry(state: dict, lat: str) -> dict:
    r = new_registry()
    register(r, state, lat, pattern="яблоко на столе", label="APPLE_ON_TABLE", mode="contains")
    register(r, state, lat, pattern="собака ест мясо", label="AGENT_EATS_FOOD", mode="structural")
    return r


def test_contains_trigger_fires_across_phrasing_and_language() -> None:
    state, lat = _state()
    r = _registry(state, lat)
    for phrasing in ("яблоко на столе", "на столе яблоко", "apple on the table"):
        assert labels(r, state, lat, phrasing) == ["APPLE_ON_TABLE"]
    # the expected context is contained in a richer utterance -> still fires
    assert "APPLE_ON_TABLE" in labels(r, state, lat, "яблоко лежит на столе у окна")
    # a different concept does not fire
    assert labels(r, state, lat, "груша на столе") == []


def test_structural_trigger_fires_on_the_meaning_class() -> None:
    state, lat = _state()
    r = _registry(state, lat)
    assert labels(r, state, lat, "человек ест яблоко") == ["AGENT_EATS_FOOD"]  # agent eats food
    assert labels(r, state, lat, "привет") == []                               # not a clause


def test_exact_trigger_is_paraphrase_invariant() -> None:
    state, lat = _state()
    r = new_registry()
    register(r, state, lat, pattern="яблоко лежит на столе", label="X", mode="exact")
    assert labels(r, state, lat, "на столе яблоко") == ["X"]          # same fingerprint
    assert labels(r, state, lat, "apple on the table") == ["X"]       # same, other language
    assert labels(r, state, lat, "яблоко на столе у окна") == []      # different (bigger) situation
