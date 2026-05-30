#!/usr/bin/env python3
"""Sweep windows_per_batch for windowed train — wall time / epoch (short run)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--batches", type=int, nargs="+", default=[24, 32, 40, 48])
    p.add_argument("--out", type=Path, default=Path("lab/exp_j_ru_v1/bench_window_batch_sweep.json"))
    args = p.parse_args()
    root = Path(__file__).resolve().parent.parent
    train = root / "tools" / "train_dmn_nca_windowed.py"
    rows: list[dict] = []

    for b in args.batches:
        out_dir = root / "lab" / f"_tmp_winbatch_{b}"
        cmd = [
            sys.executable,
            str(train),
            "--bundles",
            str(args.bundle.resolve()),
            "--codec",
            "v3",
            "--concept-mode",
            "section",
            "--epochs",
            str(args.epochs),
            "--windows-per-batch",
            str(b),
            "--out-dir",
            str(out_dir),
        ]
        print(f"=== windows_per_batch={b} epochs={args.epochs} ===", flush=True)
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        wall = time.perf_counter() - t0
        for line in (proc.stdout or "").splitlines():
            if "Train wall-clock" in line or line.startswith("epoch"):
                print(line, flush=True)
        if proc.returncode != 0:
            rows.append({"windows_per_batch": b, "ok": False, "stderr": (proc.stderr or "")[-500:]})
            continue
        rep_path = out_dir / "report.json"
        rep = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.is_file() else {}
        train_sec = rep.get("train_wall_sec") or wall
        rows.append(
            {
                "windows_per_batch": b,
                "ok": True,
                "epochs": args.epochs,
                "train_wall_sec": train_sec,
                "sec_per_epoch": train_sec / max(args.epochs, 1),
                "best_mix": rep.get("best_mix"),
                "tile_count": (rep.get("planner") or {}).get("tile_count"),
            }
        )

    out = {"schema_version": 1, "epochs": args.epochs, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
