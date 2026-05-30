#!/usr/bin/env python3
"""
Compare concept placement modes (codec v3) with a minimal train+bench loop.

Modes:
- independent (v2-style hash anchors)
- doc (concept cluster at document node)
- section (concept cluster at section hub)
- doc_section (midpoint of doc node + section hub)

For each mode: train multi-bundle NCA, then bench concepts/edges F1 (patch damage).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Bench v3 concept placement modes")
    p.add_argument(
        "--bundles",
        nargs="+",
        type=Path,
        default=[
            Path("lab/ca-substrate-agent.bundle.v1.json"),
            Path("lab/casa-goals.bundle.v1.json"),
            Path("lab/research-spec.bundle.v1.json"),
        ],
    )
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--damage", type=float, default=0.4)
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--epochs", type=int, default=1000)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--modes", default="independent,doc,section,doc_section")
    p.add_argument("--out", type=Path, default=Path("lab/concept_locality_bench.json"))
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    py = sys.executable
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    rows: list[dict] = []
    for mode in modes:
        out_dir = root / "lab" / f"nca_out_v3_{mode}"
        model = out_dir / "model.pt"
        _run(
            [
                py,
                "tools/train_dmn_nca_multibundle.py",
                "--bundles",
                *[str(root / b) for b in args.bundles],
                "--layout",
                str(root / args.layout),
                "--codec",
                "v3",
                "--concept-mode",
                mode,
                "--damage-mode",
                "patches",
                "--damage-patches",
                str(args.damage_patches),
                "--patch-w",
                "10",
                "--patch-h",
                "10",
                "--epochs",
                str(args.epochs),
                "--steps",
                "48",
                "--batch-size",
                "8",
                "--hidden",
                "192",
                "--edge-weight",
                "5.0",
                "--out-dir",
                str(out_dir),
                "--save-model",
            ],
            cwd=root,
        )

        mode_row: dict = {"concept_mode": mode, "model": str(model), "bundles": {}}
        for bundle in args.bundles:
            bpath = root / bundle
            bench_out = root / "lab" / f"_bench_v3_{mode}_{bundle.stem}.json"
            _run(
                [
                    py,
                    "tools/bench_dmn_nca_union.py",
                    "--bundle",
                    str(bpath),
                    "--layout",
                    str(root / args.layout),
                    "--codec",
                    "v3",
                    "--concept-mode",
                    mode,
                    "--damage-mode",
                    "patches",
                    "--damage-patches",
                    str(args.damage_patches),
                    "--patch-w",
                    "10",
                    "--patch-h",
                    "10",
                    "--damage",
                    str(args.damage),
                    "--seeds",
                    str(args.seeds),
                    "--steps",
                    "48",
                    "--model",
                    str(model),
                    "--out",
                    str(bench_out),
                ],
                cwd=root,
            )
            rep = json.loads(bench_out.read_text(encoding="utf-8"))
            bc = rep["baseline"]["concepts_f1"]["mean"]
            nc = rep["nca"]["concepts_f1"]["mean"]
            be = rep["baseline"]["edges_f1"]["mean"]
            ne = rep["nca"]["edges_f1"]["mean"]
            mode_row["bundles"][str(bundle)] = {
                "concepts_f1": {"baseline": bc, "nca": nc, "delta": nc - bc},
                "edges_f1": {"baseline": be, "nca": ne, "delta": ne - be},
            }
        rows.append(mode_row)

    out_obj = {
        "schema_version": 1,
        "damage": args.damage,
        "damage_patches": args.damage_patches,
        "epochs": args.epochs,
        "seeds": args.seeds,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out_obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
