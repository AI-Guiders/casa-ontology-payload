#!/usr/bin/env python3
"""Host bootstrap: morph-role-ru lattice topology (5 meta role slots)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.memory_prisms import _strengthen_concept, memory_lattices, persist_content_lattices
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

MORPH_ROLE_LATTICE = "morph-role-ru"
MORPH_ROLE_CONCEPTS: tuple[str, ...] = (
    "lang.meta.morph.prefix",
    "lang.meta.morph.root",
    "lang.meta.morph.suffix",
    "lang.meta.morph.stem",
    "lang.meta.morph.ending",
)


def bootstrap_morph_role_lattice(
    store_dir: Path,
    state: dict[str, Any],
    *,
    strength: int = 8,
    persist: bool = True,
) -> dict[str, Any]:
    """Seed morph-role-ru on field (bootstrap canon, not agent promote)."""
    lattices = memory_lattices(state)
    if MORPH_ROLE_LATTICE not in lattices:
        w, h = 32, 32
        lattices[MORPH_ROLE_LATTICE] = {
            "width": w,
            "height": h,
            "z_level": 2,
            "cells": [[] for _ in range(w * h)],
            "concept_prefix": "lang.meta.morph.",
            "stability": "bootstrap_canon",
            "owner": "host",
        }
    placed = 0
    for cid in MORPH_ROLE_CONCEPTS:
        if _strengthen_concept(lattices, MORPH_ROLE_LATTICE, cid, copies=strength):
            placed += 1
    persist_content_lattices(state, lattices)
    mark_runtime_dirty(state)
    rep = {
        "lattice_id": MORPH_ROLE_LATTICE,
        "concepts": list(MORPH_ROLE_CONCEPTS),
        "placed": placed,
    }
    state.setdefault("bootstrap", {})["morph_role_ru"] = rep
    from casa.prisms.memory.canon_nca_train import host_requests_nca_train_after_bootstrap

    rep["nca_train"] = host_requests_nca_train_after_bootstrap(
        store_dir,
        MORPH_ROLE_LATTICE,
        reason="bootstrap_morph_role_ru",
    )
    if persist:
        save_runtime_state(store_dir, state, force=True)
    return rep
