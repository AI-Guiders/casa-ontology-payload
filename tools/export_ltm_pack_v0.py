#!/usr/bin/env python3
"""Export memory lattices from field_state.json → store/ltm/*.ltm."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from field_write import load_field_state  # type: ignore
from ltm_pack_v0 import lattice_subdir, write_ltm  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, memory_lattices  # type: ignore
from sss_l2_shard_v0 import l2_word_lattice_ids  # type: ignore


def _lattice_meta(lat: dict) -> dict[str, Any]:
    skip = {"width", "height", "cells"}
    return {k: v for k, v in lat.items() if k not in skip}


def export_pack(
    state: dict,
    out_dir: Path,
    *,
    lattice_ids: list[str] | None = None,
    compress: bool = False,
) -> dict[str, Any]:
    state = ensure_cylinders(state)
    lattices = memory_lattices(state)
    ids = lattice_ids or sorted(lattices.keys())
    rows: dict[str, Any] = {}
    total_raw = 0
    total_file = 0

    for lid in ids:
        lat = lattices.get(lid)
        if not lat:
            continue
        sub = lattice_subdir(lid)
        path = out_dir / sub / f"{lid}.ltm"
        info = write_ltm(path, lat, compress=compress)
        rows[lid] = {**info, "meta": _lattice_meta(lat)}
        total_raw += int(info["raw_bytes"])
        total_file += int(info["file_bytes"])

    manifest = {
        "schema_version": 1,
        "format": "ltm-pack-v0",
        "field_version": state.get("field_version"),
        "updated_at": state.get("updated_at"),
        "lattices": rows,
        "l2_sharding": state.get("l2_sharding"),
        "nca": state.get("nca"),
        "totals": {
            "lattice_count": len(rows),
            "raw_bytes": total_raw,
            "file_bytes": total_file,
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pack.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Export compact ltm/ pack from field_state")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None, help="Default: <store>/ltm")
    p.add_argument("--layer", default="all", help="L2 | L1 | L0 | L3 | all")
    p.add_argument("--compress", action="store_true")
    args = p.parse_args()

    state = ensure_cylinders(load_field_state(args.store_dir / "field_state.json"))
    lattices = memory_lattices(state)
    targets: list[str] = []
    if args.layer in ("L2", "all"):
        targets.extend(l2_word_lattice_ids(state))
        if "L2_word" in lattices and "L2_word" not in targets:
            targets.append("L2_word")
    if args.layer in ("L1", "all") and "L1_syllable" in lattices:
        targets.append("L1_syllable")
    if args.layer in ("L0", "all") and "L0_grapheme" in lattices:
        targets.append("L0_grapheme")
    if args.layer in ("L3", "all") and "L3_phrase" in lattices:
        targets.append("L3_phrase")
    targets = list(dict.fromkeys(targets))

    out_dir = args.out or (args.store_dir / "ltm")
    manifest = export_pack(state, out_dir, lattice_ids=targets, compress=args.compress)
    print(json.dumps(manifest["totals"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
