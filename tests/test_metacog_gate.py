#!/usr/bin/env python3
from __future__ import annotations

from casa.domain.metacog_gate import metacog_pre_check
from casa.domain.scaffold import ScaffoldLevel
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_metacog_defer_when_no_capability():
    state = ensure_prisms({})
    rep = metacog_pre_check(state, step_capability="skill.read.analytic", min_votes=99)
    assert rep["defer_predict"] is True
    assert rep["scaffold_level"] in {ScaffoldLevel.GUIDED.value, ScaffoldLevel.INDEPENDENT.value}
