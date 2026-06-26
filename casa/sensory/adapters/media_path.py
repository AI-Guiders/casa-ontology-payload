#!/usr/bin/env python3
"""Media path resolution — adapter helper (periphery refs → local files)."""

from __future__ import annotations

from pathlib import Path


def resolve_media_path(ref: str, bases: tuple[Path | None, ...]) -> Path | None:
    """Resolve a manifest-relative or absolute media ref against optional base dirs."""
    path = Path(ref)
    if path.is_file():
        return path
    for base in bases:
        if base is None:
            continue
        candidate = base / ref
        if candidate.is_file():
            return candidate
    return None
