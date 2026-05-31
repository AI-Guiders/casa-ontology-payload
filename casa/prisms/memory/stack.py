#!/usr/bin/env python3
"""SSS lattice stack v0: one full grid per z_level (not y-bands)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.codec_grid import Grid, decode_grid
from casa.prisms.shared.codec_grid_v1 import _pick_cells_clustered
from casa.prisms.shared.lattice_names_v1 import ALPHABET_EN, ALPHABET_RU


def load_stack(path: Path | None = None) -> dict:
    from casa.prisms.shared.config_io import load_config

    p = path or Path("design/sss-lattice-stack.toml")
    return load_config(p)


def lattice_id_for_concept(stack: dict, concept_id: str) -> str:
    cid = concept_id or ""
    if cid.startswith("grapheme.cyrl."):
        return ALPHABET_RU
    if cid.startswith("grapheme.latn."):
        return ALPHABET_EN
    best: tuple[int, str] | None = None
    for lat in stack.get("lattices") or []:
        prefix = str(lat.get("concept_prefix") or "")
        if prefix and cid.startswith(prefix):
            cand = (len(prefix), str(lat["id"]))
            if best is None or cand[0] > best[0]:
                best = cand
    if best:
        return best[1]
    return ALPHABET_RU


def lattice_meta(stack: dict, lattice_id: str) -> dict:
    for lat in stack.get("lattices") or []:
        if lat.get("id") == lattice_id:
            return lat
    raise KeyError(lattice_id)


def _grid_to_dict(g: Grid) -> dict:
    return {"width": g.width, "height": g.height, "cells": g.cells}


def _place_token(
    grid: Grid,
    key: str,
    token: str,
    *,
    copies: int,
    radius: int = 5,
) -> Grid:
    """Place token copies; mutates grid.cells in place (no full-grid copy per cell)."""
    w, h = grid.width, grid.height
    cells = grid.cells
    for x, y in _pick_cells_clustered(key, w, h, copies, radius=radius):
        cells[grid.index(x, y)].append(token)
    return grid


def encode_lattice(
    claims: list[dict],
    edges: list[dict],
    *,
    width: int,
    height: int,
    copies: int,
    concept_prefix: str,
) -> dict:
    """Encode one z_level lattice (concepts + edges touching this prefix)."""
    grid = Grid.empty(width, height)
    cids = sorted(
        {str(c["concept_id"]) for c in claims if str(c.get("concept_id", "")).startswith(concept_prefix)}
    )
    for cid in cids:
        grid = _place_token(grid, f"C:{cid}", f"C:{cid}", copies=copies)

    for e in edges:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if not (src and rel and dst):
            continue
        if str(dst).startswith(concept_prefix):
            tok = f"E:{src}|{rel}|{dst}"
            grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)
        elif str(src).startswith(concept_prefix) and rel == "compose":
            tok = f"Z:out|{src}|{dst}"
            grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=3)

    return _grid_to_dict(grid)


def encode_sss_stack(
    bundle: dict,
    stack: dict | None = None,
    *,
    copies: int = 5,
) -> dict[str, dict]:
    """Return lattices[id] -> grid dict."""
    stack = stack or load_stack()
    claims = bundle.get("claims") or []
    edges = (bundle.get("graph") or {}).get("edges") or []
    out: dict[str, dict] = {}
    for lat in stack.get("lattices") or []:
        lid = str(lat["id"])
        size = lat.get("size") or {}
        w = int(size.get("width") or 32)
        h = int(size.get("height") or 32)
        prefix = str(lat.get("concept_prefix") or "")
        grid = encode_lattice(claims, edges, width=w, height=h, copies=copies, concept_prefix=prefix)
        out[lid] = {
            "z_level": int(lat.get("z_level") or 0),
            "width": w,
            "height": h,
            "cells": grid["cells"],
            "concept_prefix": prefix,
        }
    return out


def decode_lattice(lattice: dict, *, min_votes: int = 1) -> dict:
    vote: dict[str, int] = {}
    for cell in lattice.get("cells") or []:
        for t in cell:
            vote[t] = vote.get(t, 0) + 1
    concepts: list[dict[str, Any]] = []
    for t, v in vote.items():
        if t.startswith("C:") and v >= min_votes:
            concepts.append({"concept_id": t[2:], "votes": v})
    concepts.sort(key=lambda c: (-int(c["votes"]), c["concept_id"]))
    edges = sorted(t[2:] for t, v in vote.items() if t.startswith("E:") and v >= min_votes)
    return {
        "min_votes": min_votes,
        "concept_ids": [c["concept_id"] for c in concepts],
        "concepts": concepts,
        "edges": edges,
        "seen_tokens": len(vote),
    }


def lattice_digest(decoded: dict, *, prefix: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for c in decoded.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith(prefix):
            out.append((cid, int(c.get("votes") or 0)))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def compose_sources(bundle: dict, dst_cid: str) -> list[str]:
    srcs: list[str] = []
    for e in (bundle.get("graph") or {}).get("edges") or []:
        if e.get("relation") == "compose" and str(e.get("dst")) == dst_cid:
            srcs.append(str(e.get("src")))
    return srcs


def apply_z_compose(
    lattices: dict[str, dict],
    bundle: dict,
    stack: dict | None = None,
    *,
    min_votes: int = 1,
) -> dict[str, Any]:
    """
    Deterministic z_bridge: if all compose sources present on L0, boost dst on L1 (and up).
    Returns report of composed concepts per bridge.
    """
    stack = stack or load_stack()
    bridges = stack.get("z_bridges") or []
    composed: list[dict] = []

    lat_by_id = {str(l["id"]): l for l in stack.get("lattices") or []}
    decoded_cache: dict[str, dict] = {}

    def dec(lid: str) -> dict:
        if lid not in decoded_cache:
            decoded_cache[lid] = decode_lattice(lattices[lid], min_votes=min_votes)
        return decoded_cache[lid]

    def has_concept(lid: str, cid: str) -> bool:
        d = dec(lid)
        return any(str(c.get("concept_id")) == cid for c in d.get("concepts") or [])

    for br in bridges:
        fid = str(br.get("from"))
        tid = str(br.get("to"))
        if fid not in lattices or tid not in lattices:
            continue
        to_prefix = str(lat_by_id[tid].get("concept_prefix") or "")
        for c in dec(tid).get("concepts") or []:
            dst = str(c.get("concept_id") or "")
            if not dst.startswith(to_prefix):
                continue
            sources = compose_sources(bundle, dst)
            if sources and all(has_concept(fid, s) for s in sources):
                composed.append(
                    {
                        "bridge": br.get("id"),
                        "from": fid,
                        "to": tid,
                        "dst": dst,
                        "sources": sources,
                    }
                )
                # stamp bridge token on upper lattice for decode visibility
                tok = f"Z:composed|{dst}"
                lat = lattices[tid]
                w, h = int(lat["width"]), int(lat["height"])
                g = Grid(width=w, height=h, cells=[list(x) for x in lat["cells"]])
                g = _place_token(g, tok, tok, copies=2, radius=2)
                lat["cells"] = g.cells

    return {"composed": composed, "count": len(composed)}
