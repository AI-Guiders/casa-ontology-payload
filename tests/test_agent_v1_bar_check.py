"""ADR-0022 R1 — agent_v1_bar_check subset."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.memory_prisms import ensure_prisms, prism_hippo
from casa.prisms.shared.export_ltm_pack import export_pack
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.shared.store_layout import field_state_path, ltm_root
from tools.agent_v1_bar_check import run_bar_check


def _store_with_ltm(tmp_path: Path) -> Path:
    store = tmp_path / "store"
    ltm = ltm_root(store)
    ltm.mkdir(parents=True)
    cells = [[] for _ in range(64)]
    cells[0] = ["C:demo.alpha"]
    lat = {"width": 8, "height": 8, "cells": [list(c) for c in cells], "z_level": 0}
    state = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 1,
            "grid": {"width": 8, "height": 8, "cells": cells},
            "sss": {"lattices": {"L0_grapheme": lat}, "active_lattice": "L0_grapheme"},
        }
    )
    prism_hippo(state)
    export_pack(state, ltm, remigrate_l2=False, remigrate_l3=False)
    save_field_state(field_state_path(store), state)
    return store


def test_bar_check_passes_minimal_store(tmp_path: Path) -> None:
    store = _store_with_ltm(tmp_path)
    out = run_bar_check(store, boot_ltm=True, hippo_cap=512)
    assert out["ok"] is True
    ids = [c["id"] for c in out["checks"]]
    assert "A1_cold_boot" in ids and "C1_ltm_shipped" in ids
