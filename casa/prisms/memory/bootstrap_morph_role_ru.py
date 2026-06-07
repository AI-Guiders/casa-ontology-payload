#!/usr/bin/env python3
"""Host bootstrap: morph-role-ru lattice topology (5 meta role slots)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.bootstrap_morph_role import (
    MORPH_ROLE_CONCEPTS,
    bootstrap_morph_role_lattice as _bootstrap,
)

MORPH_ROLE_LATTICE = "morph-role-ru"


def bootstrap_morph_role_lattice(
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
