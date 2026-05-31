#!/usr/bin/env python3
"""
codec_grid_v3: v2 graph locality + concept placement strategies (no embeddings).

Concept modes (analogy to edge placement near endpoints):
- independent: hash anchor per concept (v2 baseline)
- doc: cluster near document node N:<doc_path>
- section: cluster near section hub S:<doc_path>|<section>
- doc_section: cluster near midpoint(doc node, section hub)

Edges/nodes: same as v2 (edge midpoint of endpoints).
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.codec_grid_v0 import Grid, _read_json, _stable_u64, decode_grid, score_recovery
from casa.prisms.shared.codec_grid_v2 import _anchor_for, _pick_cells_clustered

ConceptMode = str  # "independent" | "doc" | "section" | "doc_section"


def _section_key(doc_path: str, section: str) -> str:
    return f"{doc_path}|{section}"


def _claims_by_concept(claims: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for c in claims:
        cid = c.get("concept_id")
        if cid and cid not in out:
            out[cid] = c
    return out


def tokens_for_bundle(bundle: dict, *, concept_mode: ConceptMode = "independent") -> list[str]:
    """Token vocabulary for a bundle under v3 (includes section hubs when needed)."""
    claims = bundle.get("claims", [])
    graph = bundle.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    concept_ids = sorted({c.get("concept_id") for c in claims if c.get("concept_id")})
    node_ids: set[str] = set()
    for n in nodes:
        if isinstance(n, dict) and n.get("id"):
            node_ids.add(str(n["id"]))
    if not node_ids:
        for e in edges:
            if e.get("src"):
                node_ids.add(str(e["src"]))
            if e.get("dst"):
                node_ids.add(str(e["dst"]))

    section_tokens: list[str] = []
    if concept_mode in ("section", "doc_section"):
        seen: set[str] = set()
        for c in claims:
            dp, sec = c.get("doc_path"), c.get("section")
            if dp and sec:
                sk = _section_key(str(dp), str(sec))
                t = f"S:{sk}"
                if t not in seen:
                    seen.add(t)
                    section_tokens.append(t)
        section_tokens.sort()

    edge_tokens = []
    for e in edges:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if src and rel and dst:
            edge_tokens.append(f"E:{src}|{rel}|{dst}")

    return (
        [f"C:{cid}" for cid in concept_ids]
        + [f"N:{nid}" for nid in sorted(node_ids)]
        + section_tokens
        + sorted(edge_tokens)
    )


def _concept_anchor(
    cid: str,
    claim: dict | None,
    *,
    concept_mode: ConceptMode,
    node_anchor: dict[str, tuple[int, int]],
    section_anchor: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> tuple[int, int]:
    if concept_mode == "independent" or not claim:
        return _anchor_for(f"C:{cid}", width, height)

    doc_path = str(claim.get("doc_path") or "")
    section = str(claim.get("section") or "")

    if concept_mode == "doc":
        if doc_path in node_anchor:
            return node_anchor[doc_path]
        return _anchor_for(f"N:{doc_path}", width, height)

    if concept_mode == "section":
        sk = _section_key(doc_path, section) if doc_path and section else cid
        return section_anchor.get(sk, _anchor_for(f"S:{sk}", width, height))

    # doc_section
    ax_doc = node_anchor.get(doc_path, _anchor_for(f"N:{doc_path}", width, height)) if doc_path else _anchor_for(f"C:{cid}", width, height)
    if doc_path and section:
        sk = _section_key(doc_path, section)
        ax_sec = section_anchor.get(sk, _anchor_for(f"S:{sk}", width, height))
        return (ax_doc[0] + ax_sec[0]) // 2, (ax_doc[1] + ax_sec[1]) // 2
    return ax_doc


def encode_bundle_to_grid(
    bundle: dict,
    *,
    width: int = 64,
    height: int = 64,
    copies: int = 7,
    node_radius: int = 6,
    edge_radius: int = 4,
    concept_radius: int = 5,
    concept_mode: ConceptMode = "independent",
) -> dict:
    claims = bundle.get("claims", [])
    graph = bundle.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    claim_map = _claims_by_concept(claims)
    concept_ids = sorted(claim_map.keys())

    node_ids: set[str] = set()
    for n in nodes:
        if isinstance(n, dict) and n.get("id"):
            node_ids.add(str(n["id"]))
    if not node_ids:
        for e in edges:
            if e.get("src"):
                node_ids.add(str(e["src"]))
            if e.get("dst"):
                node_ids.add(str(e["dst"]))
    for c in claims:
        if c.get("doc_path"):
            node_ids.add(str(c["doc_path"]))
    node_ids_sorted = sorted(node_ids)

    node_anchor: dict[str, tuple[int, int]] = {nid: _anchor_for(f"N:{nid}", width, height) for nid in node_ids_sorted}

    section_anchor: dict[str, tuple[int, int]] = {}
    section_tokens: list[str] = []
    if concept_mode in ("section", "doc_section"):
        seen: set[str] = set()
        for c in claims:
            dp, sec = c.get("doc_path"), c.get("section")
            if not (dp and sec):
                continue
            sk = _section_key(str(dp), str(sec))
            if sk in seen:
                continue
            seen.add(sk)
            section_tokens.append(f"S:{sk}")
            section_anchor[sk] = _anchor_for(f"S:{sk}", width, height)

    edge_tokens: list[str] = []
    edge_mid_anchor: dict[str, tuple[int, int]] = {}
    for e in edges:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if not (src and rel and dst):
            continue
        src, dst = str(src), str(dst)
        t = f"E:{src}|{rel}|{dst}"
        edge_tokens.append(t)
        ax0 = node_anchor.get(src, _anchor_for(f"N:{src}", width, height))
        ax1 = node_anchor.get(dst, _anchor_for(f"N:{dst}", width, height))
        edge_mid_anchor[t] = ((ax0[0] + ax1[0]) // 2, (ax0[1] + ax1[1]) // 2)

    tokens = (
        [f"C:{cid}" for cid in concept_ids]
        + [f"N:{nid}" for nid in node_ids_sorted]
        + sorted(section_tokens)
        + sorted(edge_tokens)
    )

    grid = Grid.empty(width, height)

    for cid in concept_ids:
        t = f"C:{cid}"
        anchor = _concept_anchor(
            cid,
            claim_map.get(cid),
            concept_mode=concept_mode,
            node_anchor=node_anchor,
            section_anchor=section_anchor,
            width=width,
            height=height,
        )
        seed = _stable_u64(t) ^ _stable_u64(concept_mode)
        for x, y in _pick_cells_clustered(
            anchor=anchor, seed_u64=seed, width=width, height=height, copies=copies, radius=concept_radius
        ):
            grid = grid.with_token(x, y, t)

    for nid in node_ids_sorted:
        t = f"N:{nid}"
        for x, y in _pick_cells_clustered(
            anchor=node_anchor[nid],
            seed_u64=_stable_u64(t),
            width=width,
            height=height,
            copies=copies,
            radius=node_radius,
        ):
            grid = grid.with_token(x, y, t)

    for sk in sorted(section_anchor.keys()):
        t = f"S:{sk}"
        for x, y in _pick_cells_clustered(
            anchor=section_anchor[sk],
            seed_u64=_stable_u64(t),
            width=width,
            height=height,
            copies=copies,
            radius=max(3, concept_radius - 1),
        ):
            grid = grid.with_token(x, y, t)

    for t in sorted(edge_tokens):
        for x, y in _pick_cells_clustered(
            anchor=edge_mid_anchor[t],
            seed_u64=_stable_u64(t),
            width=width,
            height=height,
            copies=copies,
            radius=edge_radius,
        ):
            grid = grid.with_token(x, y, t)

    return {
        "schema_version": 1,
        "codec": "codec_grid_v3",
        "concept_mode": concept_mode,
        "width": width,
        "height": height,
        "copies": copies,
        "node_radius": node_radius,
        "edge_radius": edge_radius,
        "concept_radius": concept_radius,
        "tokens_count": len(tokens),
        "cells": grid.cells,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Encode bundle with v3 concept placement")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--out-grid", type=Path, required=True)
    p.add_argument("--concept-mode", choices=["independent", "doc", "section", "doc_section"], default="section")
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--min-votes", type=int, default=3)
    args = p.parse_args()

    bundle = _read_json(args.bundle)
    grid = encode_bundle_to_grid(bundle, width=args.width, height=args.height, copies=args.copies, concept_mode=args.concept_mode)
    args.out_grid.parent.mkdir(parents=True, exist_ok=True)
    args.out_grid.write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")
    decoded = decode_grid(grid, min_votes=args.min_votes)
    score = score_recovery(bundle, decoded)
    print(json.dumps({"concept_mode": args.concept_mode, "decoded": decoded, "score": score}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
