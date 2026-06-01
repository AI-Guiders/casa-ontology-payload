#!/usr/bin/env python3
"""Compact persist — agent-initiated flush of shipped memory (ltm/) without tar."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_hot_context import hot_edges
from casa.prisms.memory.prism_spawn import list_content_prism_ids
from casa.prisms.shared.export_ltm_pack import export_pack
from casa.prisms.shared.prism_state import prism_router
from casa.prisms.shared.store_layout import ltm_root


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_router_meta(ltm_dir: Path, state: dict) -> dict[str, Any]:
    """Persist router table for cold boot (audit; not hot-path oracle)."""
    r = prism_router(state)
    payload = {
        "schema_version": 1,
        "default_content_prism": r.get("default_content_prism"),
        "routes": r.get("routes") or [],
    }
    meta_dir = ltm_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = meta_dir / "router.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": path.as_posix(),
        "route_count": len(payload["routes"]),
        "default_content_prism": payload.get("default_content_prism"),
    }


def write_hot_context_audit(ltm_dir: Path, state: dict) -> dict[str, Any]:
    """Optional jsonl snapshot of hot edges (audit; aggressive prune at runtime)."""
    edges = hot_edges(state)
    meta_dir = ltm_dir / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = meta_dir / "hot_context.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for edge in edges:
            fh.write(json.dumps(edge, ensure_ascii=False) + "\n")
    return {"path": path.as_posix(), "edge_count": len(edges)}


def compact_persist_store(
    store_dir: Path,
    state: dict,
    *,
    compress: bool = False,
    content_prism_ids: list[str] | None = None,
    include_control: bool = True,
    skip_vocab_over: int | None = None,
    include_router_meta: bool = True,
    include_hot_audit: bool = False,
    reason: str = "agent",
) -> dict[str, Any]:
    """Write compact shipped tier under {store}/ltm/ (all content prisms by default).

    Does not create tar archives — distribution packaging is external ops.
    """
    store_dir = store_dir.resolve()
    state = ensure_prisms(state)
    ltm_dir = ltm_root(store_dir)
    pids = content_prism_ids if content_prism_ids is not None else list_content_prism_ids(state)

    manifest = export_pack(
        state,
        ltm_dir,
        store_dir=store_dir,
        content_prism_ids=pids,
        include_control=include_control,
        compress=compress,
        skip_vocab_over=skip_vocab_over,
    )
    report: dict[str, Any] = {
        "tier": "shipped",
        "reason": reason,
        "at": _utc_now(),
        "ltm_dir": str(ltm_dir),
        "content_prisms": pids,
        "manifest_totals": manifest.get("totals"),
        "field_version": state.get("field_version"),
    }
    if include_router_meta:
        report["router_meta"] = write_router_meta(ltm_dir, state)
    if include_hot_audit:
        report["hot_audit"] = write_hot_context_audit(ltm_dir, state)

    store = state.setdefault("store", {})
    store["last_compact_persist"] = {
        "at": report["at"],
        "reason": reason,
        "field_version": state.get("field_version"),
        "content_prism_count": len(pids),
        "lattice_count": (manifest.get("totals") or {}).get("lattice_count"),
    }
    store["store_id"] = store_dir.name
    return report


def compact_persist_on_sleep_enabled(state: dict) -> bool:
    store = state.get("store")
    if not isinstance(store, dict):
        return False
    return bool(store.get("compact_persist_on_sleep"))


def maybe_compact_persist_after_sleep(
    store_dir: Path,
    state: dict,
    sleep_report: dict[str, Any] | None,
    *,
    force: bool = False,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Run compact_persist when store policy requests flush after sleep."""
    if not force and not compact_persist_on_sleep_enabled(state):
        return None
    reason = "sleep" if not force else "sleep_forced"
    rep = compact_persist_store(store_dir, state, reason=reason, **kwargs)
    if sleep_report is not None:
        sleep_report["compact_persist"] = rep
    return rep


def main() -> None:
    from casa.prisms.shared.field_write import load_field_state
    from casa.prisms.shared.store_layout import field_state_path

    p = argparse.ArgumentParser(description="Compact persist all content prisms → store/ltm/")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--compress", action="store_true")
    p.add_argument("--hot-audit", action="store_true", help="write meta/hot_context.jsonl snapshot")
    p.add_argument("--no-control", action="store_true")
    p.add_argument("--reason", default="cli")
    args = p.parse_args()

    fs = field_state_path(args.store_dir)
    if not fs.is_file():
        raise SystemExit(f"no field_state: {fs}")
    state = ensure_prisms(load_field_state(fs))
    from casa.prisms.shared.store_boot import apply_store_boot_profile

    apply_store_boot_profile(args.store_dir, state)
    report = compact_persist_store(
        args.store_dir,
        state,
        compress=args.compress,
        include_control=not args.no_control,
        include_hot_audit=args.hot_audit,
        reason=args.reason,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
