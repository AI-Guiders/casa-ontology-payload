#!/usr/bin/env python3
"""Train NCA models for each L2 shard (and optional L0/L1) in a store."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.sss_l2_shard_v0 import (
    is_nca_trainable_lattice,
    l2_lexicon_lattice_ids,
    set_nca_model,
    shard_stats,
)
from casa.prisms.memory.sss_nca_codec_v0 import tokens_from_lattice
from casa.prisms.shared.lattice_names_v1 import is_alphabet_lattice
from casa.prisms.shared.nca_registry_v0 import mark_lattice_trained, repair_smoke_ratio
from casa.prisms.shared.nca_train_defaults_v0 import add_windowed_train_args, damage_defaults, epoch_budget, field_edge
from casa.prisms.shared.nca_train_util import add_device_args
from casa.prisms.shared.store_layout_v0 import nca_lattice_dir, nca_root, rel_to_repo
from casa.prisms.memory.sss_cylinders_v0 import memory_lattices


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Per-lattice train dirs (default: <store-dir>/nca/<lattice_id>/)",
    )
    p.add_argument("--layer", default="L2", help="L2 | L1 | L0 | all")
    p.add_argument("--skip-trained", action="store_true", default=True, help="Skip shards with model.pt (default on)")
    p.add_argument("--no-skip-trained", action="store_false", dest="skip_trained")
    p.add_argument("--from-lattice", default=None, help="Train only this id and later (lex sort)")
    p.add_argument("--epochs", type=int, default=epoch_budget("sss_shard_cuda"))
    p.add_argument("--max-tokens", type=int, default=4096, help="Skip shards above this token count")
    p.add_argument("--min-tokens", type=int, default=8)
    _dmg = damage_defaults()
    p.add_argument("--damage-patches", type=int, default=_dmg["damage_patches"])
    add_device_args(p)
    add_windowed_train_args(p, field_edge=field_edge("sss_lattice"), windowed_default=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    use_store_nca = args.out_dir is None
    report_dir = nca_root(args.store_dir) if use_store_nca else args.out_dir

    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))
    lattices = memory_lattices(state)

    targets: list[str] = []
    if args.layer in ("L2", "all"):
        targets.extend(l2_lexicon_lattice_ids(state))
    if args.layer in ("L1", "all"):
        targets.extend(sorted(lid for lid in lattices if lid.startswith("syllables-") or lid.startswith("L1_")))
    if args.layer in ("L0", "all"):
        targets.extend(sorted(lid for lid in lattices if is_alphabet_lattice(lid)))
    targets = list(dict.fromkeys(targets))
    if args.from_lattice:
        start = str(args.from_lattice)
        targets = [t for t in targets if t >= start]

    results: list[dict] = []
    for lid in targets:
        lat = lattices.get(lid) or {}
        token_count = len(tokens_from_lattice(lat))
        row = {"lattice_id": lid, "token_count": token_count, "trained": False, "skipped": False}
        if token_count < args.min_tokens:
            row["skipped"] = True
            row["reason"] = "min_tokens"
            results.append(row)
            continue
        if is_nca_trainable_lattice(lid) and token_count > args.max_tokens:
            row["skipped"] = True
            row["reason"] = "max_tokens"
            results.append(row)
            continue
        out = nca_lattice_dir(args.store_dir, lid) if use_store_nca else args.out_dir / lid.replace("/", "_")
        store_nca = nca_lattice_dir(args.store_dir, lid)
        model = out / "model.pt"
        row["out_dir"] = str(out)
        if args.skip_trained and store_nca.joinpath("model.pt").is_file():
            row["skipped"] = True
            row["reason"] = "already_trained"
            results.append(row)
            continue
        if not args.dry_run:
            out.mkdir(parents=True, exist_ok=True)
            cmd = [
                sys.executable,
                "tools/train_sss_nca_v0.py",
                "--store-dir",
                str(args.store_dir),
                "--lattice-id",
                lid,
                "--epochs",
                str(args.epochs),
                "--device",
                args.device,
                "--out-dir",
                str(out),
                "--save-model",
                "--tile-w",
                str(args.tile_w),
                "--tile-h",
                str(args.tile_h),
                "--stride-x",
                str(args.stride_x),
                "--stride-y",
                str(args.stride_y),
                "--ghost",
                str(args.ghost),
                "--windows-per-batch",
                str(args.windows_per_batch),
                "--max-windows-per-batch",
                str(args.max_windows_per_batch),
                "--damage-patches",
                str(args.damage_patches),
            ]
            if not args.windowed:
                cmd.append("--no-windowed")
            subprocess.run(cmd, check=True)
            store_nca.mkdir(parents=True, exist_ok=True)
            if out.resolve() != store_nca.resolve():
                import shutil

                shutil.copy2(model, store_nca / "model.pt")
            model_rel = rel_to_repo(store_nca / "model.pt")
            set_nca_model(state, lid, model_rel or str(store_nca / "model.pt"))
            row["trained"] = (store_nca / "model.pt").is_file()
            row["model_path"] = model_rel
            if row["trained"]:
                ratio = repair_smoke_ratio(lat, store_nca / "model.pt")
                row["registry"] = mark_lattice_trained(
                    args.store_dir,
                    state,
                    lid,
                    repair_ratio=ratio,
                )
        results.append(row)

    from casa.prisms.shared.field_write import save_field_state

    if not args.dry_run:
        save_field_state(args.store_dir / "field_state.json", state)

    report = {
        "store": str(args.store_dir),
        "layer": args.layer,
        "results": results,
        "shard_stats": shard_stats(state),
        "trained": sum(1 for r in results if r.get("trained")),
        "skipped": sum(1 for r in results if r.get("skipped")),
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "train_shards_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
