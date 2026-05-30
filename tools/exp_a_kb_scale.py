#!/usr/bin/env python3
"""Experiment A: union train on all KB bundles, bench @ damage 0.4, curves on heavy docs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _glob_bundles(kb_dir: Path) -> list[Path]:
    return sorted(kb_dir.glob("*.bundle.v1.json"))


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment A — KB scale")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--kb-dir", type=Path, default=Path("lab/kb"))
    p.add_argument(
        "--extra-bundles",
        nargs="*",
        default=["lab/ca-substrate-agent.bundle.v1.json", "lab/casa-goals.bundle.v1.json", "lab/research-spec.bundle.v1.json"],
        help="Reference bundles merged into union train (recommended)",
    )
    p.add_argument("--epochs", type=int, default=1200)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--damage-bench", type=float, default=0.4)
    p.add_argument("--curve-bundles", default="research-ml,playbook-tda-flow,research-tda-flow")
    p.add_argument("--skip-train", action="store_true")
    p.add_argument("--out-dir", type=Path, default=Path("lab/exp_a_kb_scale_v1"))
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    kb_dir = (repo / args.kb_dir).resolve()
    bundles = _glob_bundles(kb_dir)
    for eb in args.extra_bundles or []:
        pth = (repo / eb).resolve()
        if pth.is_file() and pth not in bundles:
            bundles.append(pth)
    # Dedupe: prefer lab/*.bundle over lab/kb/* with same stem
    by_stem: dict[str, Path] = {}
    for b in bundles:
        stem = b.stem
        if stem not in by_stem or "/kb/" in str(by_stem[stem]).replace("\\", "/"):
            if stem in by_stem and "/kb/" not in str(b).replace("\\", "/"):
                by_stem[stem] = b
            elif stem not in by_stem:
                by_stem[stem] = b
    bundles = sorted(by_stem.values(), key=lambda p: p.name)
    if not bundles:
        raise SystemExit(f"No bundles in {kb_dir}")

    out_dir = (repo / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    model = out_dir / "model.pt"

    if not args.skip_train:
        _run(
            [
                sys.executable,
                str(tools / "train_dmn_nca_multibundle.py"),
                "--bundles",
                *[str(b) for b in bundles],
                "--codec",
                "v3",
                "--concept-mode",
                "section",
                "--epochs",
                str(args.epochs),
                "--save-model",
                "--out-dir",
                str(out_dir),
                "--seed",
                "42",
            ],
            repo,
        )

    if not model.is_file():
        raise SystemExit(f"Missing model: {model}")

    bench_rows: list[dict] = []
    for b in bundles:
        bench_out = out_dir / f"bench_damage{args.damage_bench:.2f}_{b.stem}.json"
        _run(
            [
                sys.executable,
                str(tools / "bench_dmn_nca_union.py"),
                "--bundle",
                str(b),
                "--model",
                str(model),
                "--codec",
                "v3",
                "--concept-mode",
                "section",
                "--damage",
                str(args.damage_bench),
                "--damage-patches",
                "8",
                "--seeds",
                str(args.seeds),
                "--out",
                str(bench_out),
            ],
            repo,
        )
        rep = json.loads(bench_out.read_text(encoding="utf-8"))
        bc = rep["baseline"]["concepts_f1"]["mean"]
        be = rep["baseline"]["edges_f1"]["mean"]
        nc = rep["nca"]["concepts_f1"]["mean"]
        ne = rep["nca"]["edges_f1"]["mean"]
        bench_rows.append(
            {
                "bundle": b.name,
                "baseline": {"concepts_f1": bc, "edges_f1": be, "mix": bc * 0.6 + be * 0.4},
                "nca": {"concepts_f1": nc, "edges_f1": ne, "mix": nc * 0.6 + ne * 0.4},
                "delta": {"concepts_f1": nc - bc, "edges_f1": ne - be, "mix": (nc * 0.6 + ne * 0.4) - (bc * 0.6 + be * 0.4)},
                "nca_wins_mix": (nc * 0.6 + ne * 0.4) >= (bc * 0.6 + be * 0.4),
            }
        )

    curve_names = [x.strip() for x in args.curve_bundles.split(",") if x.strip()]
    curve_rows: list[dict] = []
    for name in curve_names:
        b = kb_dir / f"{name}.bundle.v1.json"
        if not b.is_file():
            print(f"skip curve: {b}")
            continue
        curve_out = out_dir / f"curve_{name}_s{args.seeds}.json"
        _run(
            [
                sys.executable,
                str(tools / "bench_curve_dmn_nca_union.py"),
                "--bundle",
                str(b),
                "--model",
                str(model),
                "--codec",
                "v3",
                "--concept-mode",
                "section",
                "--seeds",
                str(args.seeds),
                "--out",
                str(curve_out),
            ],
            repo,
        )
        curve_rows.append({"bundle": name, "path": str(curve_out.relative_to(repo))})

    deltas_mix = [r["delta"]["mix"] for r in bench_rows]
    report = {
        "schema_version": 1,
        "experiment": "A_kb_scale_v1",
        "bundles_count": len(bundles),
        "bundles": [b.name for b in bundles],
        "model": str(model.relative_to(repo)),
        "train_epochs": args.epochs,
        "bench_damage": args.damage_bench,
        "seeds": args.seeds,
        "summary": {
            "mean_delta_mix": sum(deltas_mix) / len(deltas_mix),
            "nca_wins_count": sum(1 for r in bench_rows if r["nca_wins_mix"]),
            "all_nca_win": all(r["nca_wins_mix"] for r in bench_rows),
        },
        "bench_rows": bench_rows,
        "curves": curve_rows,
    }
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
