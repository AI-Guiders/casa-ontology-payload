#!/usr/bin/env python3
"""Thin runtime checkpoint: lattice bodies in ltm/, JSON overlay only."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import copy
from pathlib import Path
from typing import Any

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.domain.prism_ids import PRISM_CONTROL, PRISM_HIPPO, PRISM_HOT_CONTEXT, PRISM_ROUTER
from casa.domain.prism_wire import normalize_prisms, prism_kind, prism_supports_lattices

THIN_CHECKPOINT_FORMAT = "thin_v1"

# Keys merged from thin overlay (not sourced from ltm/).
_RUNTIME_TOP_KEYS = (
    "schema_version",
    "field_version",
    "updated_at",
    "sn",
    "consolidation",
    "store",
    "nca",
    "l2_sharding",
    "fingerprint",
    "bundles",
    "grid",
    "agent_id",
    "cluster",
    "knowledge_trace",
    "last_weakest_link",
    "wake_decompose",
    "_checkpoint",
)

# Ephemeral boot flags — never persist in checkpoint JSON.
_EPHEMERAL_STATE_KEYS = frozenset({"_multi_prism_bootstrapped", "_runtime_dirty", "_bootstrap_depth"})


def ltm_pack_ready(store_dir: Path) -> bool:
    return (store_dir / "ltm" / "pack.manifest.json").is_file()


def use_thin_runtime_checkpoint(store_dir: Path) -> bool:
    """True when shipped ltm/ exists — checkpoint should not duplicate cells in JSON."""
    return ltm_pack_ready(store_dir.resolve())


def _strip_lattice_cells(lat: dict) -> dict:
    w = int(lat.get("width") or 0)
    h = int(lat.get("height") or 0)
    out = {k: v for k, v in lat.items() if k != "cells"}
    if w > 0 and h > 0:
        out["_cells_in_ltm"] = True
        out["cells"] = []
    return out


def _trim_consolidation_for_checkpoint(thin: dict) -> None:
    """Drop bulky sleep merge logs from runtime JSON (counts remain in consolidation)."""
    cons = thin.get("consolidation")
    if not isinstance(cons, dict):
        return
    last = cons.get("last_sleep")
    if not isinstance(last, dict) or "items" not in last:
        return
    items = last.get("items")
    omitted = len(items) if isinstance(items, list) else 0
    cons["last_sleep"] = {k: v for k, v in last.items() if k != "items"}
    if omitted:
        cons["last_sleep"]["items_omitted"] = omitted


def build_thin_snapshot(state: dict) -> dict[str, Any]:
    """Copy runtime state without content/control lattice cells (bodies live in ltm/)."""
    state = ensure_prisms(state)
    thin = copy.deepcopy(state)
    for key in _EPHEMERAL_STATE_KEYS:
        thin.pop(key, None)
    thin["checkpoint_format"] = THIN_CHECKPOINT_FORMAT
    root = thin.get("prisms") or {}
    for pid, block in list(root.items()):
        if not isinstance(block, dict):
            continue
        if pid == PRISM_HIPPO:
            lats = block.get("lattices")
            if isinstance(lats, dict):
                for lid, lat in list(lats.items()):
                    if isinstance(lat, dict):
                        lats[lid] = _strip_lattice_cells(lat)
            continue
        if pid in (PRISM_HOT_CONTEXT, PRISM_ROUTER):
            continue
        if not prism_supports_lattices(state, pid) and pid != PRISM_CONTROL:
            continue
        lats = block.get("lattices")
        if not isinstance(lats, dict):
            continue
        for lid, lat in list(lats.items()):
            if isinstance(lat, dict):
                lats[lid] = _strip_lattice_cells(lat)
    legacy = thin.get("sss")
    if isinstance(legacy, dict) and isinstance(legacy.get("lattices"), dict):
        for lid, lat in list(legacy["lattices"].items()):
            if isinstance(lat, dict):
                legacy["lattices"][lid] = _strip_lattice_cells(lat)
    _trim_consolidation_for_checkpoint(thin)
    return thin


def build_thin_stub(state: dict) -> dict[str, Any]:
    """Minimal JSON overlay when lattice bodies live in agent_field.db."""
    state = ensure_prisms(state)
    stub: dict[str, Any] = {"checkpoint_format": THIN_CHECKPOINT_FORMAT}
    for key in _RUNTIME_TOP_KEYS:
        if key in state and state[key] is not None:
            stub[key] = copy.deepcopy(state[key])
    stub["_checkpoint"] = {
        **(stub.get("_checkpoint") if isinstance(stub.get("_checkpoint"), dict) else {}),
        "bodies_in": "agent_field.db",
    }
    prisms_out: dict[str, Any] = {}
    root = state.get("prisms") or {}
    for pid, block in root.items():
        if not isinstance(block, dict):
            continue
        if pid == PRISM_HIPPO:
            slim: dict[str, Any] = {}
            if "episodes" in block:
                slim["episodes"] = copy.deepcopy(block["episodes"])
            if slim:
                prisms_out[pid] = slim
            continue
        if pid == PRISM_HOT_CONTEXT or prism_kind(state, pid) == "hot_context":
            slim = {}
            if "edges" in block:
                slim["edges"] = copy.deepcopy(block["edges"])
            for k in ("max_edges", "stack", "kind", "schema_version"):
                if k in block:
                    slim[k] = copy.deepcopy(block[k])
            if slim:
                prisms_out[pid] = slim
            continue
        if pid == PRISM_ROUTER or prism_kind(state, pid) == "router":
            slim = {}
            if "routes" in block:
                slim["routes"] = copy.deepcopy(block["routes"])
            if "default_content_prism" in block:
                slim["default_content_prism"] = block["default_content_prism"]
            if slim:
                prisms_out[pid] = slim
            continue
    if prisms_out:
        stub["prisms"] = prisms_out
    _trim_consolidation_for_checkpoint(stub)
    return stub


def merge_thin_overlay(state: dict, thin: dict) -> dict:
    """Apply runtime-only fields from a thin checkpoint onto ltm-booted state."""
    normalize_prisms(state)
    for key in _RUNTIME_TOP_KEYS:
        if key in thin and thin[key] is not None:
            if key == "store" and isinstance(thin[key], dict):
                state.setdefault("store", {}).update(thin[key])
            else:
                state[key] = copy.deepcopy(thin[key])

    thin_prisms = thin.get("prisms") or {}
    for pid, tblock in thin_prisms.items():
        if not isinstance(tblock, dict):
            continue
        if pid == PRISM_HIPPO:
            hip = state.setdefault("prisms", {}).setdefault(PRISM_HIPPO, {})
            if "episodes" in tblock:
                hip["episodes"] = copy.deepcopy(tblock["episodes"])
            for k in ("lattices", "subsystem", "stack"):
                if k in tblock:
                    hip[k] = copy.deepcopy(tblock[k])
            continue
        if prism_kind(state, pid) == "hot_context" or pid == PRISM_HOT_CONTEXT:
            block = state.setdefault("prisms", {}).setdefault(pid, {})
            if "edges" in tblock:
                block["edges"] = copy.deepcopy(tblock["edges"])
            for k in ("max_edges", "stack", "kind", "schema_version"):
                if k in tblock:
                    block[k] = copy.deepcopy(tblock[k])
            continue
        if prism_kind(state, pid) == "router" or pid == PRISM_ROUTER:
            block = state.setdefault("prisms", {}).setdefault(pid, {})
            if "routes" in tblock:
                block["routes"] = copy.deepcopy(tblock["routes"])
            if "default_content_prism" in tblock:
                block["default_content_prism"] = tblock["default_content_prism"]
            continue

        if not prism_supports_lattices(state, pid):
            continue
        block = state.setdefault("prisms", {}).setdefault(pid, {})
        for k in ("active_lattice", "stack", "kind", "subsystem", "nca", "payload"):
            if k in tblock:
                block[k] = copy.deepcopy(tblock[k])

    if thin.get("sn"):
        state["sn"] = copy.deepcopy(thin["sn"])
    ensure_prisms(state)
    return state


def _peek_field_version(path: Path) -> int | None:
    """Read field_version from thin checkpoint without full JSON parse."""
    if not path.is_file():
        return None
    try:
        head = path.read_text(encoding="utf-8")[:16384]
        import re

        m = re.search(r'"field_version"\s*:\s*(\d+)', head)
        return int(m.group(1)) if m else None
    except OSError:
        return None


def _hydrate_ltm_cells(state: dict, store_dir: Path) -> None:
    """Fill lattice cells from ltm/ into an existing field body (db or thin overlay)."""
    import json

    from casa.prisms.shared.import_ltm_pack import import_pack
    from casa.prisms.shared.store_layout import ltm_root

    ltm = ltm_root(store_dir)
    manifest_path = ltm / "pack.manifest.json"
    if not manifest_path.is_file():
        return
    fv = int(state.get("field_version") or 0)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    import_pack(state, ltm, manifest=manifest)
    if fv:
        state["field_version"] = fv


def load_state_with_thin_checkpoint(store_dir: Path, thin_path: Path) -> dict[str, Any]:
    """Boot ltm/ + runtime overlay; prefer agent_field.db when fresh vs thin JSON."""
    import json

    from casa.domain.agent_field import field_db_path, load_field_from_db
    from casa.prisms.shared.store_boot import apply_store_boot_profile, boot_store

    store_dir = store_dir.resolve()
    thin_fv = _peek_field_version(thin_path)
    db_state: dict[str, Any] | None = None
    db_fv = 0
    if field_db_path(store_dir).is_file():
        db_state = load_field_from_db(store_dir)
        if db_state is not None:
            db_fv = int(db_state.get("field_version") or 0)

    if db_state is not None and (thin_fv is None or db_fv >= thin_fv):
        _hydrate_ltm_cells(db_state, store_dir)
        apply_store_boot_profile(store_dir, db_state)
        db_state.setdefault("store", {})["boot_source"] = "ltm+field_db"
        db_state["store"]["checkpoint_format"] = THIN_CHECKPOINT_FORMAT
        return ensure_prisms(db_state)

    thin = json.loads(thin_path.read_text(encoding="utf-8"))
    if thin.get("checkpoint_format") != THIN_CHECKPOINT_FORMAT:
        return ensure_prisms(thin)
    boot = boot_store(store_dir.resolve(), prefer_field_state=False)
    state = boot["state"]
    merge_thin_overlay(state, thin)
    state.setdefault("store", {})["boot_source"] = "ltm+thin_checkpoint"
    state["store"]["checkpoint_format"] = THIN_CHECKPOINT_FORMAT
    return state


def is_thin_checkpoint_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        import json

        head = path.read_text(encoding="utf-8")[:4096]
        if THIN_CHECKPOINT_FORMAT in head:
            return True
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("checkpoint_format") == THIN_CHECKPOINT_FORMAT
    except (OSError, json.JSONDecodeError):
        return False
