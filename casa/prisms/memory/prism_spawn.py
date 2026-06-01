#!/usr/bin/env python3
"""Spawn prisms and content lattices in agent memory (ADR-0016)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import re
import time
from typing import Any, Literal

from casa.prisms.shared.prism_state import (
    PRISM_AGENT,
    PRISM_HOT_CONTEXT,
    PRISM_KIND_CONTENT,
    PRISM_KIND_HOT_CONTEXT,
    PRISM_KIND_ROUTER,
    PRISM_MEMORY,
    PRISM_ROUTER,
    normalize_prisms,
    prism_block,
    prism_hot_context,
    prism_kind,
    prism_router,
    prisms,
    set_active_prism,
)
from casa.prisms.memory.memory_prisms import ensure_prisms

PrismKind = Literal["content", "hot_context", "router"]

_CONTENT_ID_RE = re.compile(r"^prism_[a-z][a-z0-9_]{0,47}$")
_RESERVED = frozenset(
    {
        PRISM_MEMORY,
        PRISM_HOT_CONTEXT,
        PRISM_ROUTER,
        PRISM_AGENT,
        "prism_hippo",
        "prism_control",
    }
)

_DEFAULT_STACK: dict[str, str] = {
    PRISM_KIND_CONTENT: "design/prisms/memory/stack.json",
    PRISM_KIND_HOT_CONTEXT: "design/prisms/hot_context/stack.json",
    PRISM_KIND_ROUTER: "design/prisms/router/stack.json",
}


def _now_id() -> str:
    return f"prism-{int(time.time() * 1000) % 10_000_000}"


def validate_content_prism_id(prism_id: str) -> str:
    pid = str(prism_id or "").strip()
    if pid == PRISM_MEMORY:
        return pid
    if not _CONTENT_ID_RE.fullmatch(pid):
        raise ValueError(f"content prism id must match prism_<slug>: {prism_id!r}")
    if pid in (PRISM_HOT_CONTEXT, PRISM_ROUTER):
        raise ValueError(f"reserved prism id for kind router/hot: {prism_id!r}")
    return pid


def validate_lattice_id(lattice_id: str) -> str:
    lid = str(lattice_id or "").strip()
    if not lid or len(lid) > 64:
        raise ValueError(f"invalid lattice_id: {lattice_id!r}")
    return lid


def empty_content_lattice(
    *,
    width: int = 32,
    height: int = 32,
    z_level: int = 0,
    concept_prefix: str = "",
) -> dict[str, Any]:
    n = width * height
    return {
        "z_level": z_level,
        "width": width,
        "height": height,
        "cells": [[] for _ in range(n)],
        "concept_prefix": concept_prefix,
    }


def spawn_prism(
    state: dict,
    prism_id: str,
    *,
    kind: PrismKind = PRISM_KIND_CONTENT,
    stack: str | None = None,
    make_active: bool = False,
) -> dict[str, Any]:
    """Create a prism block in field_state.prisms (idempotent if same kind)."""
    normalize_prisms(state)
    if kind == PRISM_KIND_CONTENT:
        state = ensure_prisms(state)
    kind = str(kind)
    if kind == PRISM_KIND_HOT_CONTEXT:
        pid = PRISM_HOT_CONTEXT
    elif kind == PRISM_KIND_ROUTER:
        pid = PRISM_ROUTER
    else:
        pid = validate_content_prism_id(prism_id)

    root = prisms(state)
    if pid in root and root[pid].get("kind") not in (None, kind):
        raise ValueError(f"prism {pid!r} exists with kind {root[pid].get('kind')!r}")

    if kind == PRISM_KIND_HOT_CONTEXT:
        block = prism_hot_context(state)
    elif kind == PRISM_KIND_ROUTER:
        block = prism_router(state)
        if prism_id and prism_id not in (PRISM_ROUTER, PRISM_HOT_CONTEXT):
            block["default_content_prism"] = validate_content_prism_id(prism_id)
    else:
        block = root.setdefault(
            pid,
            {
                "kind": PRISM_KIND_CONTENT,
                "subsystem": "memory",
                "stack": stack or _DEFAULT_STACK[PRISM_KIND_CONTENT],
                "lattices": {},
                "active_lattice": None,
                "nca": {"models": {}},
            },
        )
        block["kind"] = PRISM_KIND_CONTENT
        if stack:
            block["stack"] = stack
        block.setdefault("lattices", {})
        block.setdefault("nca", {}).setdefault("models", {})

    if make_active and kind == PRISM_KIND_CONTENT:
        set_active_prism(state, pid)

    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "prism_id": pid,
        "kind": kind,
        "stack": block.get("stack") if isinstance(block, dict) else _DEFAULT_STACK.get(kind),
    }


def spawn_content_lattice(
    state: dict,
    prism_id: str,
    lattice_id: str,
    *,
    width: int = 32,
    height: int = 32,
    z_level: int = 0,
    concept_prefix: str = "",
    make_active: bool = False,
) -> dict[str, Any]:
    """Add a lattice inside a content prism."""
    pid = validate_content_prism_id(prism_id)
    lid = validate_lattice_id(lattice_id)
    spawn_prism(state, pid, kind=PRISM_KIND_CONTENT)
    block = prism_block(state, pid)
    lats = block.setdefault("lattices", {})
    if lid in lats:
        raise ValueError(f"lattice already exists: {prism_id}/{lattice_id}")
    lats[lid] = empty_content_lattice(
        width=width,
        height=height,
        z_level=z_level,
        concept_prefix=concept_prefix,
    )
    if make_active:
        block["active_lattice"] = lid
        set_active_prism(state, pid)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "prism_id": pid,
        "lattice_id": lid,
        "width": width,
        "height": height,
        "z_level": z_level,
    }


def ensure_default_router_and_hot(state: dict) -> dict[str, Any]:
    """Bootstrap fixed hot + router prisms (no-op if present)."""
    normalize_prisms(state)
    prism_hot_context(state)
    prism_router(state)
    from casa.prisms.memory.prism_router import bootstrap_default_routes

    store = state.get("store") if isinstance(state.get("store"), dict) else {}
    locale = str(store.get("locale") or "ru")
    bootstrap_default_routes(state, locale=locale)
    return {"hot_context": PRISM_HOT_CONTEXT, "router": PRISM_ROUTER}


def list_content_prism_ids(state: dict) -> list[str]:
    state = ensure_prisms(state)
    out: list[str] = []
    for pid, block in prisms(state).items():
        if not isinstance(block, dict):
            continue
        if prism_kind(state, pid) == PRISM_KIND_CONTENT and block.get("lattices") is not None:
            if pid not in (PRISM_AGENT, "prism_hippo", "prism_control", PRISM_HOT_CONTEXT, PRISM_ROUTER):
                out.append(pid)
    if PRISM_MEMORY not in out:
        out.insert(0, PRISM_MEMORY)
    return sorted(set(out))
