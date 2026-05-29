#!/usr/bin/env python3
"""Online field write: merge bundle → encode → DMN grid state."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _edge_key(e: dict) -> tuple[str, str, str]:
    return (str(e.get("src", "")), str(e.get("relation", "")), str(e.get("dst", "")))


def apply_graph_patch(bundle: dict, patch: dict | None) -> dict:
    if not patch:
        return bundle
    out = deepcopy(bundle)
    graph = out.setdefault("graph", {})
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])

    seen_nodes = {n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")}
    for n in patch.get("nodes_add") or []:
        if isinstance(n, dict) and n.get("id") and n["id"] not in seen_nodes:
            nodes.append(n)
            seen_nodes.add(n["id"])
    graph["nodes"] = nodes

    edge_set = {_edge_key(e) for e in edges if isinstance(e, dict)}
    for e in patch.get("edges_add") or []:
        if isinstance(e, dict) and all(e.get(k) for k in ("src", "relation", "dst")):
            k = _edge_key(e)
            if k not in edge_set:
                edges.append(e)
                edge_set.add(k)

    remove = {_edge_key(e) for e in patch.get("edges_remove") or [] if isinstance(e, dict)}
    if remove:
        edges = [e for e in edges if _edge_key(e) not in remove]
    graph["edges"] = edges
    out["graph"] = graph
    return out


def merge_bundles(existing: dict | None, incoming: dict, *, action: str, graph_patch: dict | None = None) -> dict:
    if action == "replace" or existing is None:
        out = deepcopy(incoming)
    elif action == "add":
        out = deepcopy(existing)
        by_cid = {c.get("concept_id"): c for c in out.get("claims", []) if c.get("concept_id")}
        for c in incoming.get("claims", []):
            cid = c.get("concept_id")
            if cid:
                by_cid[cid] = c
        out["claims"] = list(by_cid.values())
        g_in = incoming.get("graph") or {}
        out = apply_graph_patch(
            out,
            {
                "nodes_add": g_in.get("nodes") or [],
                "edges_add": g_in.get("edges") or [],
            },
        )
    elif action == "patch":
        out = deepcopy(existing)
        by_cid = {c.get("concept_id"): c for c in out.get("claims", []) if c.get("concept_id")}
        for c in incoming.get("claims", []):
            cid = c.get("concept_id")
            if cid:
                by_cid[cid] = c
        out["claims"] = list(by_cid.values())
    else:
        raise ValueError(f"unknown bundle action: {action}")

    return apply_graph_patch(out, graph_patch)


def encode_dmn_grid(bundle: dict, *, layout: dict, concept_mode: str, width: int = 64, height: int = 64, copies: int = 7) -> dict:
    from codec_grid_v3 import encode_bundle_to_grid  # type: ignore
    from layout_apply import _get_region_rect, mask_outside_region  # type: ignore

    full = encode_bundle_to_grid(bundle, width=width, height=height, copies=copies, concept_mode=concept_mode)
    rect = _get_region_rect(layout, "dmn_ontology")
    return mask_outside_region(full, rect)


def new_field_state(*, agent_id: str, cluster: str | None = None) -> dict:
    return {
        "schema_version": 1,
        "agent_id": agent_id,
        "cluster": cluster,
        "bundles": {},
        "grid": None,
        "updated_at": None,
    }


def load_field_state(path: Path) -> dict:
    if path.is_file():
        return _read_json(path)
    return {}


def save_field_state(path: Path, state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(path, state)


def write_bundle_to_field(
    state: dict,
    *,
    bundle_name: str,
    bundle: dict,
    grid: dict,
    digest: dict | None = None,
) -> dict:
    """Record bundle + its DMN grid footprint in agent field state (v1: single active bundle grid)."""
    if not state.get("schema_version"):
        state.update(new_field_state(agent_id=state.get("agent_id", "unknown"), cluster=state.get("cluster")))

    claims = bundle.get("claims") or []
    nav: list[dict] = []
    for c in claims:
        cid = c.get("concept_id")
        dp = c.get("doc_path")
        sec = c.get("section")
        if cid and dp:
            nav.append({"concept_id": str(cid), "doc_path": str(dp), "section": str(sec or "")})
    state["bundles"][bundle_name] = {
        "concept_count": len({c.get("concept_id") for c in claims if c.get("concept_id")}),
        "claim_count": len(claims),
        "edge_count": len((bundle.get("graph") or {}).get("edges") or []),
        "digest": digest or {},
        "claims_nav": nav,
    }
    state["claims_nav"] = nav
    state["grid"] = {
        "width": grid["width"],
        "height": grid["height"],
        "cells": grid["cells"],
        "source_bundle": bundle_name,
        "codec": "v3",
    }
    return state


def resolve_bundle_path(name: str, *, repo: Path, store_dir: Path, search_dirs: list[Path]) -> Path | None:
    """Find bundle file by filename in store or search dirs."""
    if (store_dir / "bundles" / name).is_file():
        return store_dir / "bundles" / name
    for d in search_dirs:
        p = d / name
        if p.is_file():
            return p
        p2 = repo / name
        if p2.is_file():
            return p2
    return None


def bundle_filename_from_ref(ref: str) -> str:
    return Path(ref.replace("\\", "/")).name


def decode_field_grid(state: dict, *, min_votes: int | None = None) -> dict:
    from canonical import CANONICAL_FIELD_MIN_VOTES  # type: ignore
    from codec_grid_v0 import decode_grid  # type: ignore

    grid = state.get("grid")
    if not grid or "cells" not in grid:
        raise ValueError("field_state has no grid")
    mv = CANONICAL_FIELD_MIN_VOTES if min_votes is None else min_votes
    return decode_grid(grid, min_votes=mv)


def bundle_from_field_state(state: dict, *, store_dir: Path) -> tuple[str, dict]:
    grid = state.get("grid") or {}
    name = grid.get("source_bundle")
    if not name:
        raise ValueError("field_state.grid.source_bundle missing")
    path = store_dir / "bundles" / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return name, _read_json(path)
