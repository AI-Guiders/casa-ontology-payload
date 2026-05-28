#!/usr/bin/env python3
"""CI smoke: short train + bench; fail if NCA does not beat baseline on mix F1."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run([sys.executable, *args], cwd=str(cwd), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="CI smoke bench for ontology-in-field")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--epsilon", type=float, default=0.02, help="Min required (nca_mix - base_mix) in --strict mode")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Require NCA to beat baseline; default is pipeline health only (short train)",
    )
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    bundles = [
        repo / "examples/ca-substrate-agent.bundle.v1.json",
        repo / "examples/casa-goals.bundle.v1.json",
        repo / "examples/research-spec.bundle.v1.json",
    ]
    out_dir = repo / "examples/nca_out_ci_smoke"
    model = out_dir / "model.pt"
    bench_out = repo / "examples/nca_ci_smoke_bench.json"

    _run(
        [
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

    _run(
        [
            str(tools / "bench_dmn_nca_union.py"),
            "--bundle",
            str(bundles[0]),
            "--model",
            str(model),
            "--codec",
            "v3",
            "--concept-mode",
            "section",
            "--damage",
            "0.25",
            "--damage-patches",
            "6",
            "--seeds",
            str(args.seeds),
            "--out",
            str(bench_out),
        ],
        repo,
    )

    rep = json.loads(bench_out.read_text(encoding="utf-8"))
    base_c = float(rep["baseline"]["concepts_f1"]["mean"])
    base_e = float(rep["baseline"]["edges_f1"]["mean"])
    nca_c = float(rep["nca"]["concepts_f1"]["mean"])
    nca_e = float(rep["nca"]["edges_f1"]["mean"])
    base_mix = base_c * 0.6 + base_e * 0.4
    nca_mix = nca_c * 0.6 + nca_e * 0.4
    delta = nca_mix - base_mix
    delta_c = nca_c - base_c
    delta_e = nca_e - base_e
    if args.strict:
        ok = delta >= args.epsilon or delta_c >= args.epsilon or delta_e >= args.epsilon
    else:
        ok = model.is_file() and "nca" in rep and "baseline" in rep
    summary = {
        "ok": ok,
        "base_mix": base_mix,
        "nca_mix": nca_mix,
        "delta": delta,
        "delta_concepts": delta_c,
        "delta_edges": delta_e,
        "epsilon": args.epsilon,
        "strict": args.strict,
        "bench": str(bench_out),
        "model": str(model),
    }
    print(json.dumps(summary, indent=2))
    if not ok:
        raise SystemExit(
            f"CI smoke failed: mixΔ={delta:.4f} conceptsΔ={delta_c:.4f} edgesΔ={delta_e:.4f} (epsilon={args.epsilon})"
        )


if __name__ == "__main__":
    main()
