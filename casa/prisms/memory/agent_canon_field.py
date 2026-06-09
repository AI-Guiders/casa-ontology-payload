#!/usr/bin/env python3
"""Agent canon → prism_memory field + sleep episodes (materialize on ltm/)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_canon_lattice import load_canon_registry
from casa.prisms.memory.memory_prisms import (
    _strengthen_concept,
    append_episode,
    memory_lattices,
    persist_content_lattices,
)
from casa.prisms.shared.canon_lattice_policy import planned_agent_canon_lattices
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id
from casa.prisms.shared.store_persist import mark_runtime_dirty


def _empty_canon_lattice(*, lattice_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    prefixes = spec.get("concept_prefix") or spec.get("meta_prefix") or ["math."]
    prefix = str(prefixes[0]) if prefixes else "math."
    if not prefix.endswith("."):
        prefix = prefix + "."
    w, h = 32, 32
    return {
        "width": w,
        "height": h,
        "z_level": 4,
        "cells": [[] for _ in range(w * h)],
        "concept_prefix": prefix,
        "stability": "agent_canon",
        "owner": "agent",
        "lattice_id": lattice_id,
    }


def sync_agent_canon_to_field(
    state: dict,
    store_dir: Path,
    *,
    strength: int = 6,
) -> dict[str, Any]:
    """Materialize agent_canon registry entries on content prism lattices."""
    reg = load_canon_registry(store_dir)
    entries = list(reg.get("entries") or [])
    if not entries:
        return {"synced": False, "lattice_ids": [], "concept_count": 0}

    lattices = memory_lattices(state)
    planned = planned_agent_canon_lattices()
    touched: list[str] = []
    concept_count = 0

    for row in entries:
        lid = canonical_lattice_id(str(row.get("lattice_id") or ""))
        if not lid:
            continue
        spec = planned.get(lid) or {}
        if lid not in lattices:
            lattices[lid] = _empty_canon_lattice(lattice_id=lid, spec=spec)
        for cid in row.get("concept_ids") or []:
            c = str(cid or "").strip()
            if not c:
                continue
            if _strengthen_concept(
                lattices,
                lid,
                c,
                copies=strength,
                state=state,
                write_context="promote_canon",
            ):
                concept_count += 1
        touched.append(lid)

    if touched:
        persist_content_lattices(state, lattices, write_context="promote_canon")
        mark_runtime_dirty(state)

    state.setdefault("agent_canon", {})["last_field_sync"] = {
        "lattice_ids": touched,
        "concept_placements": concept_count,
    }
    return {"synced": bool(touched), "lattice_ids": touched, "concept_count": concept_count}


def enqueue_canon_sleep_episodes(
    state: dict,
    *,
    lattice_id: str,
    concept_ids: list[str],
    cue: str = "",
    journal_id: str | None = None,
) -> list[dict[str, Any]]:
    """Hippo episodes for sleep strengthen (structure_tag canon_promote)."""
    lid = canonical_lattice_id(lattice_id)
    created: list[dict[str, Any]] = []
    cue_text = (cue or "").strip() or f"canon:{lid}"
    for cid in concept_ids:
        c = str(cid or "").strip()
        if not c:
            continue
        ep = append_episode(
            state,
            cue=cue_text,
            surface_attempt=c,
            correct=c,
            lattice_id=lid,
            concept_id=c,
            structure_tag="canon_promote",
            correction_kind="self_promote",
            allow_teacher_links=True,
            min_recurrence=1,
            scene=f"agent_canon:{journal_id or 'promote'}",
        )
        if ep:
            created.append(ep)
    return created
