#!/usr/bin/env python3
from __future__ import annotations

from casa.prisms.hippo.kolb_cycle import kolb_cycle
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_kolb_count_row_batch_runs():
    state = ensure_prisms({})
    rep = kolb_cycle(state, {"kind": "kolb_count_row", "start": 1, "end": 3})
    assert rep is not None
    assert rep["kind"] == "kolb_count_row"
