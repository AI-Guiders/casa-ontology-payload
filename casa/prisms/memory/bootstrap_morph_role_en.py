#!/usr/bin/env python3
"""Host bootstrap: morph-role-en lattice (parallel EN articulation slot)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.bootstrap_morph_role import bootstrap_morph_role_lattice as _bootstrap

MORPH_ROLE_LATTICE = "morph-role-en"


def bootstrap_morph_role_en_lattice(
    store_dir: Path,
    state: dict[str, Any],
    *,
    strength: int = 8,
    persist: bool = True,
) -> dict[str, Any]:
    return _bootstrap(
        store_dir,
        state,
        lattice_id=MORPH_ROLE_LATTICE,
        strength=strength,
        persist=persist,
    )
