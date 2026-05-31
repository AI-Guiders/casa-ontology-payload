#!/usr/bin/env python3
"""Export memory lattices from field_state.json → store/ltm/*.ltm."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.ltm_pack_v0 import lattice_subdir, write_ltm
from casa.prisms.shared.store_paths_v1 import ltm_write_targets, manifest_layout_block, mirror_ltm_file
from casa.prisms.control.cylinders_v0 import control_lattices, has_control_stack
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_l2_shard_v0 import l2_en_word_lattice_ids, l2_lexicon_lattice_ids, l2_word_lattice_ids
from casa.prisms.shared.store_layout_v0 import nca_train_registry_path, rel_to_repo


def _lattice_meta(lat: dict) -> dict[str, Any]:
    skip = {"width", "height", "cells"}
    return {k: v for k, v in lat.items() if k not in skip}


def _rel_nca_block(nca: dict | None) -> dict | None:
    """Copy the state NCA block with model paths rewritten repo-relative."""
    if not nca:
        return nca
    out = dict(nca)
    models = nca.get("models")
    if isinstance(models, dict):
        out["models"] = {lid: rel_to_repo(p) for lid, p in models.items()}
    if isinstance(nca.get("model_path"), str):
        out["model_path"] = rel_to_repo(nca["model_path"])
    return out


def _rel_registry(reg: dict) -> dict:
    """Copy a train registry with model paths rewritten repo-relative."""
    out = dict(reg)
    lattices = reg.get("lattices")
    if isinstance(lattices, dict):
        out["lattices"] = {
            lid: {**e, "model_path": rel_to_repo(e.get("model_path"))} for lid, e in lattices.items()
        }
    return out


def control_lattice_ids(state: dict) -> list[str]:
    if not has_control_stack(state):
        return []
    return sorted(control_lattices(state).keys())


def export_pack(
    state: dict,
    out_dir: Path,
    *,
    store_dir: Path | None = None,
    lattice_ids: list[str] | None = None,
    compress: bool = False,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    mem = memory_lattices(state)
    ctrl = control_lattices(state) if has_control_stack(state) else {}
    nca_block = _rel_nca_block(state.get("nca"))
    merged = {**mem, **ctrl}
    ids = lattice_ids or sorted(merged.keys())
    rows: dict[str, Any] = {}
    total_raw = 0
    total_file = 0

    for lid in ids:
        lat = merged.get(lid)
        if not lat:
            continue
        primary, aliases = ltm_write_targets(out_dir, lid)
        info = write_ltm(primary, lat, compress=compress)
        written = Path(info["path"])
        for alias in aliases:
            mirror_ltm_file(written, alias)
        try:
            store_rel = primary.relative_to(out_dir.parent).as_posix()
        except ValueError:
            store_rel = rel_to_repo(primary)
        rows[lid] = {**info, "path": store_rel, "meta": _lattice_meta(lat)}
        total_raw += int(info["raw_bytes"])
        total_file += int(info["file_bytes"])

    manifest = {
        "schema_version": 1,
        "format": "ltm-pack-v0",
        **manifest_layout_block(),
        "field_version": state.get("field_version"),
        "updated_at": state.get("updated_at"),
        "lattices": rows,
        "l2_sharding": state.get("l2_sharding"),
        "nca": nca_block,
        "totals": {
            "lattice_count": len(rows),
            "raw_bytes": total_raw,
            "file_bytes": total_file,
        },
    }
    if store_dir is not None:
        reg_path = nca_train_registry_path(store_dir)
        if reg_path.is_file():
            manifest["nca_train_registry"] = _rel_registry(
                json.loads(reg_path.read_text(encoding="utf-8"))
            )
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

    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))
    lattices = memory_lattices(state)
    targets: list[str] = []
    if args.layer in ("L2", "all"):
        targets.extend(l2_lexicon_lattice_ids(state))
        if "L2_word" in lattices and "L2_word" not in targets:
            targets.append("L2_word")
    if args.layer in ("L1", "all") and "L1_syllable" in lattices:
        targets.append("L1_syllable")
    if args.layer in ("L0", "all"):
        for lid in ("L0_grapheme_cyrl", "L0_grapheme_latn"):
            if lid in lattices:
                targets.append(lid)
    if args.layer in ("L3", "all") and "L3_phrase" in lattices:
        targets.append("L3_phrase")
    targets = list(dict.fromkeys(targets))

    out_dir = args.out or (args.store_dir / "ltm")
    manifest = export_pack(state, out_dir, store_dir=args.store_dir, lattice_ids=targets, compress=args.compress)
    print(json.dumps(manifest["totals"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
