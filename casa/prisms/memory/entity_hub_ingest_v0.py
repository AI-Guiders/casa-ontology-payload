#!/usr/bin/env python3
"""Ingest bilingual entity hub onto L3_phrase; strengthen L2 surfaces via listen_word."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.shared.prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism
import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.codec_grid_v0 import Grid
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.lattice_names_v1 import PHRASES
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_l2_shard_v0 import concept_votes_l2
from casa.prisms.memory.sss_stack_v0 import _place_token, decode_lattice, lattice_meta, load_stack
from casa.prisms.memory.sss_vocab_v0 import listen_word, norm_word
from casa.prisms.shared.store_boot_v0 import boot_store
from casa.prisms.shared.store_layout_v0 import field_state_path


def _surface_concept(word: str) -> str:
    return f"lang.word.{norm_word(word)}"


def _ensure_l3_lattice(state: dict) -> dict[str, Any]:
    lattices = memory_lattices(state)
    lid = PHRASES
    if lid in lattices:
        return lattices[lid]
    stack = load_stack()
    try:
        meta = lattice_meta(stack, "L3_phrase")
    except KeyError:
        meta = {"z_level": 3, "size": {"width": 32, "height": 32}, "concept_prefix": "ru.dialog."}
    size = meta.get("size") or {}
    w = int(size.get("width") or 32)
    h = int(size.get("height") or 32)
    lat = {
        "z_level": int(meta.get("z_level") or 3),
        "width": w,
        "height": h,
        "cells": [[] for _ in range(w * h)],
        "concept_prefix": str(meta.get("concept_prefix") or "ru.dialog."),
    }
    lattices[lid] = lat
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return lat


def _parse_entities(bundle: dict) -> list[dict[str, Any]]:
    if bundle.get("entities"):
        return list(bundle["entities"])
    out: list[dict[str, Any]] = []
    claims = {str(c.get("concept_id") or "") for c in bundle.get("claims") or []}
    entity_ids = sorted(cid for cid in claims if cid.startswith("entity."))
    edges = (bundle.get("graph") or {}).get("edges") or []
    surf_by_entity: dict[str, list[dict[str, str]]] = {eid: [] for eid in entity_ids}
    for e in edges:
        src, rel, dst = str(e.get("src") or ""), str(e.get("relation") or ""), str(e.get("dst") or "")
        if rel == "denotes" and dst.startswith("entity.") and src.startswith("lang.word."):
            word = src[len("lang.word.") :]
            lang = "ru" if any("\u0400" <= ch <= "\u04ff" for ch in word) else "en"
            surf_by_entity.setdefault(dst, []).append({"lang": lang, "word": word})
        elif rel.startswith("surface.") and src.startswith("entity.") and dst.startswith("lang.word."):
            word = dst[len("lang.word.") :]
            lang = rel.split(".", 1)[1]
            surf_by_entity.setdefault(src, []).append({"lang": lang, "word": word})
    for eid in entity_ids:
        seen: set[tuple[str, str]] = set()
        surfaces: list[dict[str, str]] = []
        for s in surf_by_entity.get(eid) or []:
            key = (s["lang"], norm_word(s["word"]))
            if key in seen:
                continue
            seen.add(key)
            surfaces.append({"lang": s["lang"], "word": norm_word(s["word"])})
        out.append({"entity_id": eid, "surfaces": surfaces})
    return out


def ingest_entity_hub(
    state: dict,
    bundle: dict,
    *,
    lattice_id: str = PHRASES,
    copies: int = 5,
    strengthen_l2: bool = True,
    listen_copies: int = 2,
) -> dict[str, Any]:
    """Place entity hub tokens on L3; optionally imprint missing surface words on L2."""
    state = ensure_prisms(state)
    lat = _ensure_l3_lattice(state)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])

    entities = _parse_entities(bundle)
    edge_count = 0
    entity_count = 0
    l2_strengthened: list[str] = []
    l2_skipped: list[str] = []

    for ent in entities:
        eid = str(ent.get("entity_id") or "")
        if not eid.startswith("entity."):
            continue
        g = _place_token(g, f"C:{eid}", f"C:{eid}", copies=copies, radius=5)
        entity_count += 1

        seen_surfaces: set[str] = set()
        for surf in ent.get("surfaces") or []:
            word = norm_word(str(surf.get("word") or ""))
            lang = str(surf.get("lang") or "").strip().lower()
            if not word or not lang:
                continue
            sid = _surface_concept(word)
            if sid in seen_surfaces:
                continue
            seen_surfaces.add(sid)

            tok_den = f"E:{sid}|denotes|{eid}"
            g = _place_token(g, tok_den, tok_den, copies=max(2, copies // 2), radius=4)
            edge_count += 1

            tok_surf = f"E:{eid}|surface.{lang}|{sid}"
            g = _place_token(g, tok_surf, tok_surf, copies=max(2, copies // 2), radius=4)
            edge_count += 1

            if strengthen_l2:
                cv, _ = concept_votes_l2(state, sid)
                if cv == 0:
                    listen_word(state, word, copies=listen_copies, link_scene=False)
                    l2_strengthened.append(word)
                else:
                    l2_skipped.append(word)

    lat["cells"] = g.cells
    lattices = memory_lattices(state)
    lattices[lattice_id] = lat
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state["entity_hub"] = {
        "bundle_id": bundle.get("bundle_id"),
        "lattice_id": lattice_id,
        "entity_count": entity_count,
    }
    state["field_version"] = int(state.get("field_version") or 0) + 1

    dec = decode_lattice(lat, min_votes=1)
    return {
        "lattice_id": lattice_id,
        "bundle_id": bundle.get("bundle_id"),
        "entities": entity_count,
        "edges_placed": edge_count,
        "l2_strengthened": l2_strengthened,
        "l2_already_present": l2_skipped,
        "l3_concepts": len(dec.get("concept_ids") or []),
        "l3_edges": len(dec.get("edges") or []),
        "field_version": state["field_version"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest entity hub bundle → phrases")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--boot-ltm-only", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument("--copies", type=int, default=5)
    p.add_argument("--no-l2", action="store_true", help="Skip listen_word on missing L2 surfaces")
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    fs = field_state_path(args.store_dir)
    if args.boot_ltm_only or not fs.is_file():
        state = boot_store(args.store_dir, prefer_field_state=False)["state"]
    else:
        state = ensure_prisms(load_field_state(fs))

    rep = ingest_entity_hub(
        state,
        bundle,
        copies=args.copies,
        strengthen_l2=not args.no_l2,
    )
    if args.write:
        save_field_state(fs, state, compact=True)
        rep["written"] = str(fs)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
