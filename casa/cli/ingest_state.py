#!/usr/bin/env python3
"""Shared runtime state for ingest paths (CLI and inbox reactor)."""

from __future__ import annotations

from pathlib import Path

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store


def resolve_ingest_state(store_dir: Path, state: dict | None) -> dict:
    """Use in-memory agent state when provided; otherwise cold-load from store."""
    store_dir = store_dir.resolve()
    if state is not None:
        runtime = ensure_prisms(state)
        runtime.setdefault("store", {})["store_id"] = store_dir.name
        return runtime
    boot = boot_store(store_dir, prefer_field_state=True)
    return ensure_prisms(boot["state"])
