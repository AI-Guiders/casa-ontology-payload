#!/usr/bin/env python3
"""Run segment generalize smoke from UTF-8 JSON config."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--train", type=Path, required=True)
    p.add_argument("--heldout", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cfg = json.loads(args.train.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parent

    subprocess.run(
        [
            sys.executable,
            str(root / "sss_hypothesis_v0.py"),
            "--store-dir",
            str(args.store_dir),
            "--word",
            cfg["probe_word"],
        ],
        check=True,
    )
    cmd = [
        sys.executable,
        str(root / "bench_sss_segment_generalize.py"),
        "--store-dir",
        str(args.store_dir),
        "--bundle",
        str(args.bundle),
        "--train-word",
        cfg["train_word"],
        "--train-gold",
        cfg["train_gold"],
        "--heldout",
        str(args.heldout),
    ]
    if args.out:
        cmd.extend(["--out", str(args.out)])
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
