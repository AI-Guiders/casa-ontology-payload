#!/usr/bin/env python3
"""Merge parallel batch shards into one field_state (token multiset union)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.memory.memory_prisms import ensure_prisms


def _merge_lattice_cells(target: dict, shard: dict) -> None:
    if int(target.get("width") or 0) != int(shard.get("width") or 0):
        raise ValueError(f"lattice width mismatch {target.get('width')} vs {shard.get('width')}")
    if int(target.get("height") or 0) != int(shard.get("height") or 0):
        raise ValueError(f"lattice height mismatch {target.get('height')} vs {shard.get('height')}")
    t_cells = target.setdefault("cells", [])
    s_cells = shard.get("cells") or []
    if len(t_cells) != len(s_cells):
        raise ValueError(f"cell count mismatch {len(t_cells)} vs {len(s_cells)}")
    for i, tokens in enumerate(s_cells):
        if tokens:
            t_cells[i].extend(tokens)


def _merge_memory_lattices(out: dict, shard: dict) -> None:
    out_lat = ensure_prisms(out)["prisms"]["prism_memory"]["lattices"]
    sh_lat = ensure_prisms(shard)["prisms"]["prism_memory"]["lattices"]
    for lid, slat in sh_lat.items():
        if lid not in out_lat:
            out_lat[lid] = deepcopy(slat)
            continue
        _merge_lattice_cells(out_lat[lid], slat)
    out.setdefault("sss", {})["lattices"] = out_lat


def _merge_hippo(out: dict, shard: dict) -> None:
    o_hip = ensure_prisms(out)["prisms"]["prism_hippo"]
    s_hip = ensure_prisms(shard)["prisms"]["prism_hippo"]
    seen = {str(e.get("id")) for e in o_hip.get("episodes") or [] if e.get("id")}
    for ep in s_hip.get("episodes") or []:
        eid = str(ep.get("id") or "")
        if eid and eid in seen:
            continue
        o_hip.setdefault("episodes", []).append(ep)
        if eid:
            seen.add(eid)
    for hid, hlat in (s_hip.get("lattices") or {}).items():
        if hid not in o_hip.setdefault("lattices", {}):
            o_hip["lattices"][hid] = deepcopy(hlat)
        else:
            _merge_lattice_cells(o_hip["lattices"][hid], hlat)


def merge_field_states(base: dict, shards: list[dict], *, base_field_version: int | None = None) -> dict:
    """Union token placements from shards onto base snapshot."""
    out = deepcopy(base)
    ensure_prisms(out)
    base_fv = int(base_field_version if base_field_version is not None else base.get("field_version") or 0)
    delta_total = 0
    done: set[str] = set((out.get("batch_progress") or {}).get("files") or [])

    for shard in shards:
        ensure_prisms(shard)
        _merge_memory_lattices(out, shard)
        _merge_hippo(out, shard)
        sh_fv = int(shard.get("field_version") or 0)
        sh_base = int(shard.get("_merge_base_fv") or base_fv)
        delta_total += max(0, sh_fv - sh_base)
        prog = shard.get("batch_progress") or {}
        done.update(prog.get("files") or [])

    prog = out.setdefault("batch_progress", {})
    prog["files"] = sorted(done)
    if done:
        prog["last_file"] = prog["files"][-1]
    out["field_version"] = base_fv + delta_total
    prog["field_version"] = out["field_version"]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Merge field_state base + shard JSON files")
    p.add_argument("--base", type=Path, required=True, help="Starting snapshot (e.g. after partial ingest)")
    p.add_argument("--shards", type=Path, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--compact", action="store_true", default=True)
    args = p.parse_args()

    base = load_field_state(args.base)
    base_fv = int(base.get("field_version") or 0)
    shards = [json.loads(s.read_text(encoding="utf-8")) for s in args.shards]
    merged = merge_field_states(base, shards, base_field_version=base_fv)
    save_field_state(args.out, merged, compact=args.compact)
    print(
        json.dumps(
            {
                "out": str(args.out),
                "shards": len(shards),
                "files": len(merged.get("batch_progress", {}).get("files") or []),
                "field_version": merged.get("field_version"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
