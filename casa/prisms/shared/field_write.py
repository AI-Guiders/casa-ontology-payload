#!/usr/bin/env python3
"""Online field write: merge bundle → encode → DMN grid state."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import hashlib
import json
import os
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        data = json.dumps(obj, ensure_ascii=False, indent=2)
    tmp = path.with_name(path.name + ".tmp")
    last_err: PermissionError | None = None
    for attempt in range(8):
        try:
            tmp.write_text(data, encoding="utf-8")
            os.replace(tmp, path)
            return
        except PermissionError as err:
            last_err = err
            if attempt >= 7:
                break
            time.sleep(0.05 * (attempt + 1))
    if last_err is not None:
        raise last_err


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


def bundle_content_hash(bundle: dict) -> str:
    canonical = json.dumps(bundle, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def merge_store_bundles(bundles: list[dict]) -> dict:
    if not bundles:
        raise ValueError("no bundles to merge")
    out = deepcopy(bundles[0])
    for b in bundles[1:]:
        out = merge_bundles(out, b, action="add")
    return out


def nav_item_from_claim(c: dict, *, bundle_name: str | None = None) -> dict | None:
    cid = c.get("concept_id")
    dp = c.get("doc_path")
    if not cid or not dp:
        return None
    item: dict[str, Any] = {
        "concept_id": str(cid),
        "doc_path": str(dp),
        "section": str(c.get("section") or ""),
        "text": str(c.get("text") or "")[:500],
    }
    kind = c.get("claim_kind")
    if kind:
        item["claim_kind"] = str(kind)
    if bundle_name:
        item["bundle"] = bundle_name
    anchors = c.get("code_anchors")
    if anchors:
        item["code_anchors"] = anchors
    return item


def build_claims_nav(loaded: list[tuple[str, dict]]) -> list[dict]:
    nav: list[dict] = []
    seen: set[str] = set()
    for bundle_name, bundle in loaded:
        for c in bundle.get("claims") or []:
            item = nav_item_from_claim(c, bundle_name=bundle_name)
            if item and item["concept_id"] not in seen:
                seen.add(item["concept_id"])
                nav.append(item)
    return nav


def compute_field_fingerprint(state: dict, store_dir: Path) -> dict:
    bundles_meta: dict[str, Any] = {}
    for name in sorted(state.get("bundles") or {}):
        p = store_dir / "bundles" / name
        if p.is_file():
            bundles_meta[name] = {"content_hash": bundle_content_hash(_read_json(p))}
    return {"bundle_count": len(bundles_meta), "bundles": bundles_meta}


def list_store_bundles(state: dict, store_dir: Path) -> list[tuple[str, dict]]:
    loaded: list[tuple[str, dict]] = []
    for name in sorted(state.get("bundles") or {}):
        p = store_dir / "bundles" / name
        if p.is_file():
            loaded.append((name, _read_json(p)))
    return loaded


def rebuild_union_field(
    state: dict,
    *,
    store_dir: Path,
    layout: dict,
    concept_mode: str,
    digest: dict | None = None,
    last_bundle_name: str | None = None,
) -> dict:
    """v2: union all bundles in store → single grid + combined claims_nav."""
    loaded = list_store_bundles(state, store_dir)
    if not loaded:
        return state

    merged = merge_store_bundles([b for _, b in loaded])
    grid = encode_dmn_grid(merged, layout=layout, concept_mode=concept_mode)
    names = [n for n, _ in loaded]

    for bundle_name, bundle in loaded:
        claims = bundle.get("claims") or []
        meta = state.setdefault("bundles", {}).get(bundle_name) or {}
        state["bundles"][bundle_name] = {
            "concept_count": len({c.get("concept_id") for c in claims if c.get("concept_id")}),
            "claim_count": len(claims),
            "edge_count": len((bundle.get("graph") or {}).get("edges") or []),
            "content_hash": bundle_content_hash(bundle),
            "digest": meta.get("digest") or (digest if bundle_name == last_bundle_name else {}),
        }

    state["claims_nav"] = build_claims_nav(loaded)
    state["grid"] = {
        "width": grid["width"],
        "height": grid["height"],
        "cells": grid["cells"],
        "source_bundle": last_bundle_name or names[-1],
        "source_bundles": names,
        "codec": "v3",
        "union": True,
    }
    state["fingerprint"] = compute_field_fingerprint(state, store_dir)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    if digest:
        state["last_digest"] = digest
    return state


def apply_digest_only_update(
    state: dict,
    *,
    bundle_name: str,
    digest: dict,
    store_dir: Path,
) -> dict:
    """Refresh digest metadata + claims_nav without re-encoding grid."""
    if bundle_name not in (state.get("bundles") or {}):
        state.setdefault("bundles", {})[bundle_name] = {}
    state["bundles"][bundle_name]["digest"] = digest
    loaded = list_store_bundles(state, store_dir)
    state["claims_nav"] = build_claims_nav(loaded)
    state["last_digest"] = digest
    state["field_version"] = int(state.get("field_version") or 0) + 1
    state["fingerprint"] = compute_field_fingerprint(state, store_dir)
    return state


def encode_dmn_grid(bundle: dict, *, layout: dict, concept_mode: str, width: int = 64, height: int = 64, copies: int = 7) -> dict:
    from casa.prisms.shared.codec_grid_v3 import encode_bundle_to_grid
    from casa.prisms.shared.layout_apply import _get_region_rect, mask_outside_region

    full = encode_bundle_to_grid(bundle, width=width, height=height, copies=copies, concept_mode=concept_mode)
    rect = _get_region_rect(layout, "dmn_ontology")
    return mask_outside_region(full, rect)


def new_field_state(*, agent_id: str, cluster: str | None = None) -> dict:
    return {
        "schema_version": 2,
        "agent_id": agent_id,
        "cluster": cluster,
        "bundles": {},
        "grid": None,
        "field_version": 0,
        "fingerprint": {},
        "updated_at": None,
    }


def load_field_state(path: Path, *, store_dir: Path | None = None) -> dict:
    if not path.is_file():
        return {}
    sd = store_dir if store_dir is not None else path.parent
    from casa.prisms.shared.runtime_checkpoint import is_thin_checkpoint_file, load_state_with_thin_checkpoint

    if is_thin_checkpoint_file(path):
        return load_state_with_thin_checkpoint(sd.resolve(), path)
    return _read_json(path)


def save_field_state(path: Path, state: dict, *, compact: bool = False) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(path, state, compact=compact)


def write_bundle_to_field(
    state: dict,
    *,
    bundle_name: str,
    bundle: dict,
    grid: dict | None = None,
    digest: dict | None = None,
    store_dir: Path | None = None,
    layout: dict | None = None,
    concept_mode: str | None = None,
) -> dict:
    """Register bundle metadata; prefer rebuild_union_field when store_dir+layout provided."""
    if not state.get("schema_version"):
        state.update(new_field_state(agent_id=state.get("agent_id", "unknown"), cluster=state.get("cluster")))

    state.setdefault("bundles", {})[bundle_name] = {
        "concept_count": len({c.get("concept_id") for c in bundle.get("claims", []) if c.get("concept_id")}),
        "claim_count": len(bundle.get("claims") or []),
        "edge_count": len((bundle.get("graph") or {}).get("edges") or []),
        "content_hash": bundle_content_hash(bundle),
        "digest": digest or {},
    }

    if store_dir is not None and layout is not None and concept_mode is not None:
        return rebuild_union_field(
            state,
            store_dir=store_dir,
            layout=layout,
            concept_mode=concept_mode,
            digest=digest,
            last_bundle_name=bundle_name,
        )

    if grid is None:
        raise ValueError("grid required when store_dir/layout not provided")

    nav = build_claims_nav([(bundle_name, bundle)])
    state["claims_nav"] = nav
    state["grid"] = {
        "width": grid["width"],
        "height": grid["height"],
        "cells": grid["cells"],
        "source_bundle": bundle_name,
        "source_bundles": [bundle_name],
        "codec": "v3",
        "union": False,
    }
    state["field_version"] = int(state.get("field_version") or 0) + 1
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
    from casa.prisms.shared.canonical import CANONICAL_FIELD_MIN_VOTES
    from casa.prisms.shared.codec_grid import decode_grid

    try:
        from casa.prisms.control.cylinders import has_control_stack
        from casa.prisms.control.stack import decode_control_dmn

        if has_control_stack(state):
            mv = CANONICAL_FIELD_MIN_VOTES if min_votes is None else min_votes
            return decode_control_dmn(state, min_votes=mv)
    except Exception:
        pass

    grid = state.get("grid")
    if not grid or "cells" not in grid:
        raise ValueError("field_state has no grid and no prism_control DMN lattice")
    mv = CANONICAL_FIELD_MIN_VOTES if min_votes is None else min_votes
    decoded = decode_grid(grid, min_votes=mv)
    vote: dict[str, int] = {}
    for cell in grid.get("cells") or []:
        for t in cell:
            vote[t] = vote.get(t, 0) + 1
    decoded["present_token_list"] = sorted([t for t, v in vote.items() if v >= mv])
    return decoded


def bundle_from_field_state(state: dict, *, store_dir: Path) -> tuple[str, dict]:
    grid = state.get("grid") or {}
    names = list(grid.get("source_bundles") or [])
    if not names:
        name = grid.get("source_bundle")
        if not name:
            names = list((state.get("bundles") or {}).keys())
        else:
            names = [name]
    if not names:
        raise ValueError("field_state: no bundle ref in grid or bundles")

    loaded: list[dict] = []
    for name in names:
        path = store_dir / "bundles" / name
        if not path.is_file():
            raise FileNotFoundError(path)
        loaded.append(_read_json(path))

    primary = grid.get("source_bundle") or names[-1]
    if len(loaded) == 1:
        return primary, loaded[0]
    return primary, merge_store_bundles(loaded)


def field_state_stale(state: dict, store_dir: Path) -> bool:
    """True if on-disk bundle hash differs from fingerprint in field_state."""
    fp = state.get("fingerprint") or {}
    recorded = (fp.get("bundles") or {})
    for name in state.get("bundles") or {}:
        p = store_dir / "bundles" / name
        if not p.is_file():
            return True
        live = bundle_content_hash(_read_json(p))
        rec = (recorded.get(name) or {}).get("content_hash")
        if rec and rec != live:
            return True
    return False
