#!/usr/bin/env python3
"""Find and optionally train stale NCA shards only (incremental sleep repair v0)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path

from field_write import load_field_state, save_field_state  # type: ignore
from nca_registry_v0 import (  # type: ignore
    find_stale_shards,
    mark_lattice_trained,
    merge_pending,
    repair_smoke_ratio,
    sync_registry_from_store,
)
from nca_train_defaults_v0 import add_windowed_train_args, damage_defaults, epoch_budget, field_edge  # type: ignore
from nca_train_util import add_device_args, resolve_train_device  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_l2_shard_v0 import is_nca_trainable_lattice, set_nca_model  # type: ignore
from sss_nca_codec_v0 import tokens_from_lattice  # type: ignore
from store_layout_v0 import field_state_path, nca_lattice_dir, rel_to_repo  # type: ignore


def _train_one_shard(
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
    windows_per_batch: int,
    max_windows_per_batch: int,
    damage_patches: int,
) -> Path:
    out = nca_lattice_dir(store_dir, lattice_id)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "tools/train_sss_nca_v0.py",
        "--store-dir",
        str(store_dir),
        "--lattice-id",
        lattice_id,
        "--epochs",
        str(epochs),
        "--device",
        device,
        "--out-dir",
        str(out),
        "--save-model",
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
        str(windows_per_batch),
        "--max-windows-per-batch",
        str(max_windows_per_batch),
        "--damage-patches",
        str(damage_patches),
    ]
    if not windowed:
        cmd.append("--no-windowed")
    subprocess.run(cmd, check=True)
    model = out / "model.pt"
    if not model.is_file():
        raise FileNotFoundError(f"train finished without model: {model}")
    return model


def main() -> None:
    _dmg = damage_defaults()
    p = argparse.ArgumentParser(description="Stale NCA shard detect + incremental train")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--sync-registry", action="store_true", help="Bootstrap registry from existing model.pt")
    p.add_argument("--repair-smoke", action="store_true", help="Flag shards with low recovery ratio")
    p.add_argument("--min-recovery", type=float, default=0.85)
    p.add_argument("--train", action="store_true", help="Train stale shards only")
    p.add_argument("--epochs", type=int, default=epoch_budget("sss_shard_incremental"))
    p.add_argument("--max-shards", type=int, default=0, help="0 = all stale")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--mark-pending", nargs="*", default=None, help="Test: queue lattice ids")
    p.add_argument("--damage-patches", type=int, default=_dmg["damage_patches"])
    p.add_argument("--min-tokens", type=int, default=8, help="Skip shards below this token count (bench/dev: 1–2)")
    add_device_args(p)
    p.set_defaults(device="cuda")
    add_windowed_train_args(p, field_edge=field_edge("sss_lattice"), windowed_default=True)
    args = p.parse_args()

    train_device = "cuda" if args.device in ("auto", "cuda") else args.device
    if args.train and train_device == "cuda":
        resolve_train_device("cuda")

    store = args.store_dir.resolve()
    fs_path = field_state_path(store)
    state = ensure_prisms(load_field_state(fs_path))
    if not state:
        raise SystemExit(f"field_state missing: {fs_path}")

    if args.sync_registry:
        sync_registry_from_store(store, state)
    if args.mark_pending:
        merge_pending(store, list(args.mark_pending))

    stale = find_stale_shards(
        state,
        store,
        repair_smoke=args.repair_smoke,
        min_recovery=args.min_recovery,
        min_tokens=args.min_tokens,
    )
    if args.max_shards > 0:
        stale = stale[: args.max_shards]

    trained: list[dict] = []
    if args.train and not args.dry_run:
        for row in stale:
            lid = str(row["lattice_id"])
            lat = memory_lattices(state).get(lid) or {}
            if len(tokens_from_lattice(lat)) < args.min_tokens:
                continue
            if not is_nca_trainable_lattice(lid):
                continue
            model = _train_one_shard(
                store,
                lid,
                epochs=args.epochs,
                device=train_device,
                windowed=args.windowed,
                tile_w=args.tile_w,
                tile_h=args.tile_h,
                stride_x=args.stride_x,
                stride_y=args.stride_y,
                ghost=args.ghost,
                windows_per_batch=args.windows_per_batch,
                max_windows_per_batch=args.max_windows_per_batch,
                damage_patches=args.damage_patches,
            )
            set_nca_model(state, lid, rel_to_repo(model) or str(model))
            ratio = repair_smoke_ratio(lat, model)
            trained.append(
                {
                    "lattice_id": lid,
                    "model_path": rel_to_repo(model),
                    "repair_ratio": ratio,
                    **mark_lattice_trained(store, state, lid, repair_ratio=ratio),
                }
            )
        save_field_state(fs_path, state)

    report = {
        "schema_version": 1,
        "tool": "nca_stale_shards_v0",
        "store": str(store),
        "field_version": state.get("field_version"),
        "stale_count": len(stale),
        "trained_count": len(trained),
        "dry_run": args.dry_run and not args.train,
        "stale": stale,
        "trained": trained,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
