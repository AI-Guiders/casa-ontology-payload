#!/usr/bin/env python3
"""Prism memory health checks (ADR-0016 / prism-memory-architecture-v1)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.memory_prisms import content_prism_lattices, ensure_prisms, hippo_episodes
from casa.prisms.memory.prism_hot_context import hot_edges, prune_hot_context
from casa.prisms.memory.prism_router import RouteContext, resolve_route
from casa.prisms.shared.prism_state import (
    PRISM_KIND_HOT_CONTEXT,
    PRISM_KIND_ROUTER,
    PRISM_MEMORY,
    active_prism_id,
    prism_kind,
    prisms,
)

HOT_SOFT_EDGE_COUNT = 1024
HOT_HARD_EDGE_COUNT = 4096
HIPPO_EPISODE_SOFT_CAP = 512


def run_prism_memory_health(
    state: dict,
    *,
    auto_prune_hot: bool = False,
    hippo_cap: int = HIPPO_EPISODE_SOFT_CAP,
) -> dict[str, Any]:
    """Run v0 checks; optional auto_prune_hot when over hard budget."""
    state = ensure_prisms(state)
    checks: list[dict[str, Any]] = []
    ok = True

    target = resolve_route(state, RouteContext())
    pid = target.prism_id
    lats = content_prism_lattices(state, pid)
    route_ok = bool(lats) or pid == PRISM_MEMORY
    checks.append(
        {
            "id": "router_resolves",
            "ok": route_ok,
            "detail": {"target_prism": pid, "lattice_count": len(lats)},
        }
    )
    ok = ok and route_ok

    edge_count = len(hot_edges(state))
    hot_ok = edge_count <= HOT_HARD_EDGE_COUNT
    checks.append(
        {
            "id": "hot_budget",
            "ok": hot_ok,
            "detail": {"edge_count": edge_count, "soft": HOT_SOFT_EDGE_COUNT, "hard": HOT_HARD_EDGE_COUNT},
        }
    )
    if not hot_ok and auto_prune_hot:
        prune_hot_context(state, max_edges=HOT_HARD_EDGE_COUNT - 1)
        edge_count = len(hot_edges(state))
        checks[-1]["pruned_to"] = edge_count
        checks[-1]["ok"] = edge_count <= HOT_HARD_EDGE_COUNT
        hot_ok = checks[-1]["ok"]
    ok = ok and hot_ok

    if edge_count > HOT_SOFT_EDGE_COUNT:
        checks.append(
            {
                "id": "hot_soft_warning",
                "ok": True,
                "warn": True,
                "detail": {"edge_count": edge_count, "threshold": HOT_SOFT_EDGE_COUNT},
            }
        )

    ep_count = len(hippo_episodes(state))
    hippo_ok = ep_count <= hippo_cap
    checks.append(
        {
            "id": "hippo_cap",
            "ok": hippo_ok,
            "detail": {"episode_count": ep_count, "cap": hippo_cap},
        }
    )
    ok = ok and hippo_ok

    active = active_prism_id(state)
    nca = state.get("nca") or {}
    models = nca.get("models") if isinstance(nca.get("models"), dict) else {}
    has_models = bool(models) or bool(nca.get("model_path"))
    nca_ok = has_models or not lats
    checks.append(
        {
            "id": "nca_registry",
            "ok": nca_ok,
            "detail": {"active_prism": active, "model_entries": len(models), "has_global_path": bool(nca.get("model_path"))},
        }
    )
    ok = ok and nca_ok

    kind_issues: list[str] = []
    for prism_id, block in prisms(state).items():
        if not isinstance(block, dict):
            continue
        kind = prism_kind(state, prism_id)
        if kind == PRISM_KIND_HOT_CONTEXT and block.get("lattices"):
            kind_issues.append(f"{prism_id}: hot_context must not have lattices")
        if kind == PRISM_KIND_ROUTER and block.get("lattices"):
            kind_issues.append(f"{prism_id}: router must not have lattices")
    kind_ok = not kind_issues
    checks.append({"id": "kind_integrity", "ok": kind_ok, "detail": {"issues": kind_issues}})
    ok = ok and kind_ok

    return {"ok": ok, "checks": checks, "field_version": state.get("field_version")}


def main() -> None:
    import argparse
    import json
    from pathlib import Path

    from casa.prisms.shared.field_write import load_field_state
    from casa.prisms.shared.store_boot import boot_store
    from casa.prisms.shared.store_layout import field_state_path

    p = argparse.ArgumentParser(description="Prism memory health (ADR-0016)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--auto-prune-hot", action="store_true")
    p.add_argument("--boot-ltm", action="store_true", help="boot from ltm/ instead of field_state only")
    args = p.parse_args()

    if args.boot_ltm:
        rep = boot_store(args.store_dir, prefer_field_state=False)
        state = rep["state"]
    else:
        fs = field_state_path(args.store_dir)
        state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms(
            {"schema_version": "multi_prism_v1", "field_version": 0}
        )

    out = run_prism_memory_health(state, auto_prune_hot=args.auto_prune_hot)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
