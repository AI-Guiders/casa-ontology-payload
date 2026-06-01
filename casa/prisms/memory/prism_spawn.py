#!/usr/bin/env python3
"""Spawn prisms and content lattices in agent memory (ADR-0016)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import re
import time
from typing import Any

from casa.prisms.shared.prism_state import (
    PRISM_AGENT,
    PRISM_CONTROL,
    PRISM_HIPPO,
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
    prism_supports_lattices,
    prisms,
    set_active_prism,
)
from casa.prisms.memory.memory_prisms import ensure_prisms

_PRISM_ID_RE = re.compile(r"^prism_[a-z][a-z0-9_]{0,47}$")
_KIND_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")

# Created only via ensure_* / migrate — not agent spawn.
_SYSTEM_PRISM_IDS = frozenset({PRISM_HIPPO, PRISM_CONTROL, PRISM_AGENT})

_DEFAULT_STACK: dict[str, str] = {
    PRISM_KIND_CONTENT: "design/prisms/memory/stack.json",
    PRISM_KIND_HOT_CONTEXT: "design/prisms/hot_context/stack.json",
    PRISM_KIND_ROUTER: "design/prisms/router/stack.json",
}


def normalize_prism_kind(kind: str | None) -> str:
    """Open vocabulary: agent may introduce new kind slugs (not a closed enum)."""
    k = (kind or PRISM_KIND_CONTENT).strip().lower()
    if not _KIND_RE.fullmatch(k):
        raise ValueError(f"prism kind must match [a-z][a-z0-9_]*: {kind!r}")
    return k


def validate_content_prism_id(prism_id: str) -> str:
    """Content-route targets and lattice host ids."""
    return validate_spawn_prism_id(prism_id, kind=PRISM_KIND_CONTENT)


def validate_spawn_prism_id(prism_id: str, *, kind: str) -> str:
    kind = normalize_prism_kind(kind)
    pid = str(prism_id or "").strip()
    if kind == PRISM_KIND_HOT_CONTEXT and pid in ("", PRISM_HOT_CONTEXT):
        return PRISM_HOT_CONTEXT
    if kind == PRISM_KIND_ROUTER and pid in ("", PRISM_ROUTER):
        return PRISM_ROUTER
    if not pid:
        raise ValueError("prism_id required for this kind")
    if pid in _SYSTEM_PRISM_IDS:
        raise ValueError(f"system prism {pid!r} is not created via spawn; use ensure_* paths")
    if pid == PRISM_MEMORY:
        return pid
    if not _PRISM_ID_RE.fullmatch(pid):
        raise ValueError(f"prism id must match prism_<slug>: {prism_id!r}")
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


def _new_hot_block(*, stack: str) -> dict[str, Any]:
    return {
        "kind": PRISM_KIND_HOT_CONTEXT,
        "schema_version": 1,
        "stack": stack,
        "edges": [],
        "max_edges": 4096,
    }


def _new_router_block(*, stack: str, default_content: str = PRISM_MEMORY) -> dict[str, Any]:
    return {
        "kind": PRISM_KIND_ROUTER,
        "schema_version": 1,
        "stack": stack,
        "default_content_prism": default_content,
        "routes": [],
    }


def _new_content_block(*, stack: str) -> dict[str, Any]:
    return {
        "kind": PRISM_KIND_CONTENT,
        "subsystem": "memory",
        "stack": stack,
        "lattices": {},
        "active_lattice": None,
        "nca": {"models": {}},
    }


def _new_agent_kind_block(*, kind: str, stack: str) -> dict[str, Any]:
    """Agent-defined kind — minimal shell; payload/lattices added by agent ops."""
    return {
        "kind": kind,
        "stack": stack,
        "payload": {},
    }


def spawn_prism(
    state: dict,
    prism_id: str,
    *,
    kind: str | None = None,
    stack: str | None = None,
    make_active: bool = False,
) -> dict[str, Any]:
    """Create or refresh a prism block (open kind vocabulary).

    Shipped bootstrap uses content / hot_context / router; agent may add e.g.
    prism_workspace + kind=workspace_meta or prism_nav + kind=router.
    """
    normalize_prisms(state)
    kind_n = normalize_prism_kind(kind)
    if kind_n == PRISM_KIND_CONTENT:
        state = ensure_prisms(state)

    pid = validate_spawn_prism_id(prism_id, kind=kind_n)
    root = prisms(state)
    if pid in root and root[pid].get("kind") not in (None, kind_n):
        raise ValueError(f"prism {pid!r} exists with kind {root[pid].get('kind')!r}")

    stack_path = stack or _DEFAULT_STACK.get(kind_n) or f"design/prisms/{kind_n}/stack.json"

    if pid == PRISM_HOT_CONTEXT and kind_n == PRISM_KIND_HOT_CONTEXT:
        block = prism_hot_context(state)
    elif pid == PRISM_ROUTER and kind_n == PRISM_KIND_ROUTER:
        block = prism_router(state)
        if prism_id and prism_id not in (PRISM_ROUTER, PRISM_HOT_CONTEXT):
            block["default_content_prism"] = validate_content_prism_id(prism_id)
    elif kind_n == PRISM_KIND_HOT_CONTEXT:
        block = root.setdefault(pid, _new_hot_block(stack=stack_path))
    elif kind_n == PRISM_KIND_ROUTER:
        block = root.setdefault(pid, _new_router_block(stack=stack_path))
    elif kind_n == PRISM_KIND_CONTENT:
        block = root.setdefault(pid, _new_content_block(stack=stack_path))
    else:
        block = root.setdefault(pid, _new_agent_kind_block(kind=kind_n, stack=stack_path))

    block["kind"] = kind_n
    if stack:
        block["stack"] = stack

    if make_active and prism_supports_lattices(state, pid):
        set_active_prism(state, pid)

    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "prism_id": pid,
        "kind": kind_n,
        "stack": block.get("stack"),
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
    """Add a lattice inside a prism that supports lattices (usually content)."""
    pid = validate_spawn_prism_id(prism_id, kind=PRISM_KIND_CONTENT)
    lid = validate_lattice_id(lattice_id)
    if not prism_supports_lattices(state, pid):
        spawn_prism(state, pid, kind=PRISM_KIND_CONTENT)
    block = prism_block(state, pid)
    if not prism_supports_lattices(state, pid):
        raise ValueError(f"prism {pid!r} (kind={prism_kind(state, pid)!r}) does not support lattices")
    lats = block.setdefault("lattices", {})
    block.setdefault("nca", {}).setdefault("models", {})
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
    """Bootstrap canonical hot + router prisms (no-op if present)."""
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
        if pid in (PRISM_AGENT, PRISM_HIPPO, PRISM_CONTROL, PRISM_HOT_CONTEXT, PRISM_ROUTER):
            continue
        if prism_supports_lattices(state, pid):
            out.append(pid)
    if PRISM_MEMORY not in out:
        out.insert(0, PRISM_MEMORY)
    return sorted(set(out))


def main() -> None:
    import argparse
    import json
    from pathlib import Path

    from casa.prisms.shared.field_write import load_field_state, save_field_state
    from casa.prisms.shared.store_layout import field_state_path

    p = argparse.ArgumentParser(
        description="Spawn agent prisms (open kind); canonical hot/router via --bootstrap-only",
    )
    p.add_argument("--store-dir", type=Path, help="Agent store; load/save field_state when set")
    p.add_argument("--spawn", metavar="PRISM_ID", help="prism_<slug> id")
    p.add_argument(
        "--kind",
        default=None,
        metavar="KIND",
        help="kind slug (default content); agent-defined kinds allowed, e.g. workspace_meta",
    )
    p.add_argument("--lattice", metavar="LATTICE_ID", help="with --spawn: spawn_content_lattice")
    p.add_argument("--z-level", type=int, default=0)
    p.add_argument("--make-active", action="store_true")
    p.add_argument("--bootstrap-only", action="store_true", help="ensure_default_router_and_hot only")
    p.add_argument("--write", action="store_true", help="save field_state.json")
    args = p.parse_args()

    if args.store_dir:
        from casa.prisms.shared.store_boot import apply_store_boot_profile

        fs = field_state_path(args.store_dir)
        state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms(
            {"schema_version": "multi_prism_v1", "field_version": 0}
        )
        apply_store_boot_profile(args.store_dir, state)
    else:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})

    out: dict[str, Any] = {}
    if args.bootstrap_only or not args.spawn:
        out["bootstrap"] = ensure_default_router_and_hot(state)
    if args.spawn:
        out["spawn"] = spawn_prism(state, args.spawn, kind=args.kind, make_active=args.make_active)
        if args.lattice:
            out["lattice"] = spawn_content_lattice(
                state,
                args.spawn,
                args.lattice,
                z_level=args.z_level,
                make_active=args.make_active,
            )
    out["content_prisms"] = list_content_prism_ids(state)
    out["field_version"] = state.get("field_version")

    if args.write and args.store_dir:
        save_field_state(field_state_path(args.store_dir), state, compact=True)
        out["written"] = str(field_state_path(args.store_dir))

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
