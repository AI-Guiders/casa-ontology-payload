#!/usr/bin/env python3
"""Train NCA on ADR-0010 control lattices (predict / dan / value) on prism_control."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path

from casa.prisms.control.cylinders import control_lattices, has_control_stack
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.nca_registry import mark_lattice_trained
from casa.prisms.shared.nca_train_defaults import add_windowed_train_args, damage_defaults, epoch_budget, field_edge
from casa.prisms.shared.nca_train_util import add_device_args
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.lexicon_shard import set_nca_model
from casa.prisms.shared.lattice_names_v1 import CONTROL_NCA_TRAIN_STACK
from casa.prisms.shared.store_layout import nca_lattice_dir, rel_to_repo, repo_root, use_compact_field_state

DEFAULT_STACK = CONTROL_NCA_TRAIN_STACK


def _train_one(
    store_dir: Path,
    lattice_id: str,
    *,
    epochs: int,
    device: str,
    windowed: bool,
    tile_w: int,
    tile_h: int,
    stride_x: int,
    stride_y: int,
    ghost: int,
    max_windows_per_batch: int,
    damage_patches: int,
) -> Path:
    out = nca_lattice_dir(store_dir, lattice_id)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "tools/train_memory_nca.py",
        "--store-dir",
        str(store_dir),
        "--prism",
        "control",
        "--lattice-id",
        lattice_id,
        "--epochs",
        str(epochs),
        "--device",
        device,
        "--out-dir",
        str(out),
        "--save-model",
        "--damage-patches",
        str(damage_patches),
        "--tile-w",
        str(tile_w),
        "--tile-h",
        str(tile_h),
        "--stride-x",
        str(stride_x),
        "--stride-y",
        str(stride_y),
        "--ghost",
        str(ghost),
        "--windows-per-batch",
        "0",
        "--max-windows-per-batch",
        str(max_windows_per_batch),
    ]
    if windowed:
        cmd.append("--windowed")
    else:
        cmd.append("--no-windowed")
    subprocess.run(cmd, check=True, cwd=repo_root())
    model = out / "model.pt"
    if not model.is_file():
        raise FileNotFoundError(model)
    return model


def main() -> None:
    _dmg = damage_defaults()
    _fe = field_edge("sss_lattice")
    _epochs = epoch_budget("sss_shard_incremental")

    p = argparse.ArgumentParser(description="Train control stack NCA (predict/dan/value)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--lattice-id", action="append", dest="lattice_ids", help="Repeatable; default stack")
    p.add_argument("--epochs", type=int, default=_epochs)
    add_device_args(p)
    add_windowed_train_args(p, field_edge=_fe, windowed_default=True)
    p.add_argument("--damage-patches", type=int, default=_dmg["damage_patches"])
    args = p.parse_args()

    store = args.store_dir.resolve()
    fs_path = store / "field_state.json"
    state = ensure_prisms(load_field_state(fs_path))
    if not has_control_stack(state):
        raise SystemExit(f"{store.name}: no prism_control stack — run migrate_control_stack first")

    ids = args.lattice_ids or list(DEFAULT_STACK)
    ctrl = control_lattices(state)
    reports: list[dict] = []

    for lid in ids:
        if lid not in ctrl:
            raise SystemExit(f"unknown control lattice: {lid}")
        model = _train_one(
            store,
            lid,
            epochs=args.epochs,
            device=args.device,
            windowed=args.windowed,
            tile_w=args.tile_w,
            tile_h=args.tile_h,
            stride_x=args.stride_x,
            stride_y=args.stride_y,
            ghost=args.ghost,
            max_windows_per_batch=args.max_windows_per_batch,
            damage_patches=args.damage_patches,
        )
        rel = rel_to_repo(model) or str(model)
        set_nca_model(state, lid, rel)
        mark_lattice_trained(store, state, lid)
        rep_path = model.parent / "report.json"
        reports.append(
            {
                "lattice_id": lid,
                "model_path": rel,
                "report": json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.is_file() else None,
            }
        )

    save_field_state(fs_path, state, compact=use_compact_field_state(store))
    print(json.dumps({"schema_version": 1, "store": str(store), "trained": reports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
