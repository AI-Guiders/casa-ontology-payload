#!/usr/bin/env python3
"""Camera-ready tables + figure data from the raw metrics JSON — no hand-typed numbers.

Reads the metrics JSON (``judge_metrics --out-json``), the CI JSON (``judge_ci --out-json``),
and the ablation metrics, and writes into ``--out-dir``:

  results_main.tex   — booktabs: judge × answered/recall/FPR/precision/consist@5
  results_ci.tex     — booktabs: judge × recall/FPR/precision/zero-risk with 95% CIs
  ablation.tex       — booktabs: kernel full/none/lexical (per-class recall) — component study
  riskcoverage.dat   — pgfplots data (coverage, risk) per judge
  riskcoverage.tex   — a \\begin{tikzpicture} that plots riskcoverage.dat

Regenerating the paper's numbers is then one command; camera-ready never edits a number by
hand. LaTeX-only (pgfplots), so no matplotlib / image dependency.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

_ESC = str.maketrans({"_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#"})


def _tex(s: str) -> str:
    return str(s).translate(_ESC)


def _short(name: str) -> str:
    return name.split(" [")[0]


def _fmt(x, nd=3):
    return "--" if x is None else f"{x:.{nd}f}"


def results_main(metrics: dict) -> str:
    rows = []
    for name in sorted(metrics):
        m = metrics[name]
        c = m["consistency"]["unanimous"]
        rows.append(f"{_tex(_short(name))} & {_fmt(m['answered'])} & {_fmt(m['recall'])} & "
                    f"{_fmt(m['fpr'])} & {_fmt(m['precision'])} & {_fmt(c) if c is not None else '--'} "
                    f"& {_fmt(m['invalid_rate'])} \\\\")
    body = "\n".join(rows)
    return (r"\begin{tabular}{lrrrrrr}" "\n" r"\toprule" "\n"
            r"judge & answered & recall & FPR & precision & consist@5 & invalid \\" "\n"
            r"\midrule" "\n" f"{body}" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def results_ci(ci: dict) -> str:
    def band(d):
        return "--" if d.get("point") is None else f"{d['point']:.3f} [{d['lo']:.3f}, {d['hi']:.3f}]"

    rows = []
    for name in sorted(ci):
        c = ci[name]
        rows.append(f"{_tex(_short(name))} & {band(c['recall'])} & {band(c['fpr'])} & "
                    f"{band(c['precision'])} & {band(c['zero_risk_coverage'])} \\\\")
    body = "\n".join(rows)
    return (r"\begin{tabular}{lllll}" "\n" r"\toprule" "\n"
            r"judge & recall & FPR & precision & zero-risk cov. \\" "\n"
            r"\midrule" "\n" f"{body}" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def ablation(metrics: dict) -> str:
    order = ["kernel-full", "kernel-none", "kernel-lexical"]
    label = {"kernel-full": "full (graph + guards)", "kernel-none": "no residual guards",
             "kernel-lexical": "no graph (lexical)"}
    rows = []
    for key in order:
        m = next((metrics[n] for n in metrics if _short(n) == key), None)
        if not m:
            continue
        pc = m["per_class"]
        rows.append(f"{label[key]} & {_fmt(m['answered'])} & {_fmt(m['recall'])} & {_fmt(m['fpr'])} & "
                    f"{_fmt(pc['polarity']['recall'])} & {_fmt(pc['quantity']['recall'])} & "
                    f"{_fmt(pc['unit']['recall'])} & {_fmt(pc['entity']['recall'])} \\\\")
    body = "\n".join(rows)
    return (r"\begin{tabular}{lrrrrrrr}" "\n" r"\toprule" "\n"
            r"kernel variant & answered & recall & FPR & R:pol & R:qty & R:unit & R:ent \\" "\n"
            r"\midrule" "\n" f"{body}" "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")


def risk_coverage(metrics: dict) -> tuple[str, str]:
    """pgfplots .dat (one block per judge) + a tikzpicture that plots it."""
    judges = sorted(metrics)
    blocks = []
    for name in judges:
        pts = metrics[name].get("risk_coverage", [])
        lines = "\n".join(f"{p['coverage']:.4f} {p['risk']:.4f}" for p in pts)
        blocks.append(f"# {_short(name)}\ncoverage risk\n{lines}\n")
    dat = "\n".join(blocks)

    plots = []
    for i, name in enumerate(judges):
        plots.append(f"\\addplot table[x=coverage, y=risk] {{riskcoverage_{i}.dat}};")
        plots.append(f"\\addlegendentry{{{_tex(_short(name))}}}")
    tikz = (r"\begin{tikzpicture}" "\n"
            r"\begin{axis}[xlabel=coverage, ylabel=risk, legend pos=north west,"
            r" width=.8\linewidth, height=.5\linewidth, grid=both]" "\n"
            + "\n".join(plots) + "\n"
            r"\end{axis}" "\n" r"\end{tikzpicture}" "\n")
    return dat, tikz


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit camera-ready LaTeX tables + figure data.")
    ap.add_argument("--metrics", default="lab/nunbench/v0.1.2/metrics-v0.1.2.json")
    ap.add_argument("--ci", default="lab/nunbench/v0.1.2/ci-v0.1.2.json")
    ap.add_argument("--ablation", default=None, help="ablation metrics JSON (optional)")
    ap.add_argument("--out-dir", default="lab/nunbench/v0.1.2/paper")
    args = ap.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    (out / "results_main.tex").write_text(results_main(metrics), encoding="utf-8")

    if Path(args.ci).exists():
        ci = json.loads(Path(args.ci).read_text(encoding="utf-8"))
        (out / "results_ci.tex").write_text(results_ci(ci), encoding="utf-8")

    if args.ablation and Path(args.ablation).exists():
        abl = json.loads(Path(args.ablation).read_text(encoding="utf-8"))
        (out / "ablation.tex").write_text(ablation(abl), encoding="utf-8")

    dat, tikz = risk_coverage(metrics)
    # split the .dat into one file per judge (pgfplots table wants one x/y block per file)
    for i, block in enumerate(b for b in dat.split("# ")[1:]):
        body = "\n".join(block.splitlines()[1:])  # drop the judge-name header line
        (out / f"riskcoverage_{i}.dat").write_text(body + "\n", encoding="utf-8")
    (out / "riskcoverage.tex").write_text(tikz, encoding="utf-8")

    written = sorted(p.name for p in out.glob("*"))
    print(f"wrote {len(written)} files to {out}/:")
    for w in written:
        print(f"  {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
