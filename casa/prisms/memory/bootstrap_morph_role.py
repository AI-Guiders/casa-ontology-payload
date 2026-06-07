#!/usr/bin/env python3
"""Host bootstrap: morph-role lattices (locale-parallel articulation slots, shared meta ids)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.memory_prisms import _strengthen_concept, memory_lattices, persist_content_lattices
from casa.prisms.shared.canon_lattice_policy import bootstrap_canon_lattice_ids
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

# Structural morph roles — locale-invariant semantics (immutable-lattice canon).
MORPH_ROLE_CONCEPTS: tuple[str, ...] = (
    "lang.meta.morph.prefix",
    "lang.meta.morph.root",
    "lang.meta.morph.suffix",
    "lang.meta.morph.stem",
    "lang.meta.morph.ending",
)

MORPH_ROLE_LATTICE_META: dict[str, dict[str, str]] = {
    "morph-role-ru": {
        "bootstrap_key": "morph_role_ru",
        "reason": "bootstrap_morph_role_ru",
    },
    "morph-role-en": {
        "bootstrap_key": "morph_role_en",
        "reason": "bootstrap_morph_role_en",
    },
}


def morph_role_lattice_ids() -> frozenset[str]:
    return frozenset(MORPH_ROLE_LATTICE_META.keys())


def bootstrap_morph_role_lattice(
    store_dir: Path,
    state: dict[str, Any],
    *,
    lattice_id: str = "morph-role-ru",
    strength: int = 8,
    persist: bool = True,
) -> dict[str, Any]:
    """Seed morph-role lattice on field (bootstrap canon, not agent promote)."""
    lid = canonical_lattice_id(lattice_id)
    meta = MORPH_ROLE_LATTICE_META.get(lid)
    if not meta:
        raise ValueError(f"unknown morph-role lattice {lattice_id!r}")
    allowed = bootstrap_canon_lattice_ids()
    if lid not in allowed:
        raise ValueError(f"{lid!r} is not a bootstrap_canon lattice in lattice-id-map")

    lattices = memory_lattices(state)
    if lid not in lattices:
        w, h = 32, 32
        lattices[lid] = {
            "width": w,
            "height": h,
            "z_level": 2,
            "cells": [[] for _ in range(w * h)],
            "concept_prefix": "lang.meta.morph.",
            "stability": "bootstrap_canon",
            "owner": "host",
            "locale_slot": lid.removeprefix("morph-role-"),
        }
    placed = 0
    for cid in MORPH_ROLE_CONCEPTS:
        if _strengthen_concept(lattices, lid, cid, copies=strength):
            placed += 1
    persist_content_lattices(state, lattices)
    mark_runtime_dirty(state)
    rep = {
        "lattice_id": lid,
        "concepts": list(MORPH_ROLE_CONCEPTS),
        "placed": placed,
    }
    state.setdefault("bootstrap", {})[meta["bootstrap_key"]] = rep
    from casa.prisms.memory.canon_nca_train import host_requests_nca_train_after_bootstrap

    rep["nca_train"] = host_requests_nca_train_after_bootstrap(
        store_dir,
        lid,
        reason=meta["reason"],
    )
    if persist:
        save_runtime_state(store_dir, state, force=True)
    return rep
