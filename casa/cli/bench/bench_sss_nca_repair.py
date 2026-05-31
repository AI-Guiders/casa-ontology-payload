#!/usr/bin/env python3
"""Bench SSS NCA train → damage → repair on L2_word."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path

from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_nca_codec_v0 import word_tokens_from_lattice  # type: ignore
from sss_nca_repair_v0 import nca_repair_state_lattice  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--lattice-id", default="L2_word")
    p.add_argument("--model", type=Path, default=None)
    p.add_argument("--train", action="store_true", help="Train model first (CPU-friendly epochs)")
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--out-dir", type=Path, default=Path("lab/nca_out_sss_l2_smoke"))
    p.add_argument("--damage-patches", type=int, default=4)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--write", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    out_dir = args.out_dir
    model = args.model or (out_dir / "model.pt")

    if args.train:
        subprocess.run(
            [
                sys.executable,
                "tools/train_sss_nca_v0.py",
                "--store-dir",
                str(args.store_dir),
                "--lattice-id",
                args.lattice_id,
                "--epochs",
                str(args.epochs),
                "--device",
                "cpu",
                "--out-dir",
                str(out_dir),
                "--save-model",
            ],
            check=True,
        )

    if not model.exists():
        raise SystemExit(f"Model not found: {model}")

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    w_before = len(word_tokens_from_lattice(memory_lattices(state)[args.lattice_id]))

    rep = nca_repair_state_lattice(
        state,
        args.lattice_id,
        model,
        damage_patches=args.damage_patches,
        seed=args.seed,
        device="cpu",
    )

    report = {
        "store": str(args.store_dir),
        "lattice_id": args.lattice_id,
        "model": str(model),
        "w_before": w_before,
        **{k: v for k, v in rep.items() if k != "lattice"},
        "nca_ok": rep["w_repaired"] >= max(1, int(w_before * 0.5)),
    }

    if args.write:
        state["field_version"] = int(state.get("field_version") or 0) + 1
        save_field_state(path, state)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
