#!/usr/bin/env python3
"""Bootstrap prism_auditory + A0…A2 lattices (ADR-0028)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.domain.auditory_tract import AUDITORY_LATTICE_IDS, LATTICE_AUDIO_SPECTRUM
from casa.domain.prism_ids import PRISM_AUDITORY, PRISM_KIND_CONTENT
from casa.domain.prism_wire import prism_block, prisms
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_router import add_route
from casa.prisms.memory.prism_spawn import empty_content_lattice, spawn_prism
from casa.prisms.shared.config_io import load_config

AUD_STACK = Path("design/prisms/auditory/stack.json")


def _load_aud_stack() -> dict:
    return load_config(REPO_ROOT / AUD_STACK)


def ensure_auditory_lattices(state: dict) -> list[str]:
    block = prism_block(state, PRISM_AUDITORY)
    lats = block.setdefault("lattices", {})
    stack = _load_aud_stack()
    created: list[str] = []
    for lat in stack.get("lattices") or []:
        if lat.get("status") == "roadmap":
            continue
        lid = str(lat.get("legacy_id") or lat.get("lattice_id") or "")
        if not lid:
            continue
        if lid in lats:
            lat_w = lats[lid]
            lat_w.setdefault("concept_prefix", str(lat.get("semantic_id") or "aud."))
            lat_w.setdefault("prism_id", PRISM_AUDITORY)
            continue
        lats[lid] = empty_content_lattice(
            width=32,
            height=32,
            z_level=int(lat.get("z_level") or 0),
            concept_prefix=str(lat.get("semantic_id") or "aud."),
        )
        lats[lid]["prism_id"] = PRISM_AUDITORY
        created.append(lid)
    if LATTICE_AUDIO_SPECTRUM in lats and not block.get("active_lattice"):
        block["active_lattice"] = LATTICE_AUDIO_SPECTRUM
    return created


def ensure_prism_auditory_routes(state: dict) -> None:
    add_route(
        state,
        {"modality": "listen"},
        PRISM_AUDITORY,
        lattice_hint=LATTICE_AUDIO_SPECTRUM,
        priority=95,
    )
    add_route(
        state,
        {"modality": "audio"},
        PRISM_AUDITORY,
        lattice_hint=LATTICE_AUDIO_SPECTRUM,
        priority=95,
    )


def ensure_prism_auditory(state: dict) -> dict[str, Any]:
    state = ensure_prisms(state)
    stack_path = str((REPO_ROOT / AUD_STACK).resolve())
    if PRISM_AUDITORY not in prisms(state):
        spawn_prism(
            state,
            PRISM_AUDITORY,
            kind=PRISM_KIND_CONTENT,
            stack=stack_path,
        )
    else:
        block = prism_block(state, PRISM_AUDITORY)
        block.setdefault("kind", PRISM_KIND_CONTENT)
        if not block.get("stack"):
            block["stack"] = stack_path
    created = ensure_auditory_lattices(state)
    ensure_prism_auditory_routes(state)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "prism_id": PRISM_AUDITORY,
        "lattice_ids": list(AUDITORY_LATTICE_IDS),
        "created_lattices": created,
    }
