#!/usr/bin/env python3
"""Load and merge KB bundles from agent store (multi-bundle stores)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_store_bundles(store_dir: Path) -> dict[str, Any]:
    """Merge all ``store_dir/bundles/*.json`` into one routing bundle."""
    store_dir = store_dir.resolve()
    bundle_dir = store_dir / "bundles"
    if not bundle_dir.is_dir():
        return {"claims": [], "graph": {"edges": []}}

    claims: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    bundle_ids: list[str] = []
    titles: list[str] = []

    for path in sorted(bundle_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        bid = str(raw.get("bundle_id") or path.stem)
        bundle_ids.append(bid)
        if raw.get("title"):
            titles.append(str(raw["title"]))
        for c in raw.get("claims") or []:
            if isinstance(c, dict) and c.get("concept_id"):
                row = dict(c)
                row.setdefault("_bundle_id", bid)
                claims.append(row)
        graph = raw.get("graph") or {}
        for e in graph.get("edges") or []:
            if isinstance(e, dict):
                edges.append(dict(e))

    return {
        "schema_version": 1,
        "bundle_id": "+".join(bundle_ids[:3]) if bundle_ids else "empty",
        "bundle_ids": bundle_ids,
        "titles": titles,
        "claims": claims,
        "graph": {"edges": edges},
    }


def load_store_bundle(store_dir: Path) -> dict[str, Any] | None:
    """Backward-compatible single bundle loader — returns merged bundle or None."""
    merged = load_store_bundles(store_dir)
    if merged.get("claims"):
        return merged
    return None
