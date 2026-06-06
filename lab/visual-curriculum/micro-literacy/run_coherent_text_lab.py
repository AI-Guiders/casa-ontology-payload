#!/usr/bin/env python3
"""Coherent text sprint: agreement ingest → P2 self-drive → probes → write@sketch bench."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401

_REPO = Path(__file__).resolve().parents[3]
_CURRICULUM = Path(__file__).resolve().parents[1]
_MICRO = Path(__file__).resolve().parent
_PY = sys.executable


def _store_has_kb_field_bundle(store_dir: Path) -> bool:
    from casa.prisms.shared.field_write import bundle_from_field_state, load_field_state

    state = load_field_state(store_dir / "field_state.json", store_dir=store_dir)
    try:
        bundle_from_field_state(state, store_dir=store_dir)
        return True
    except (ValueError, FileNotFoundError):
        return False


def _run(cmd: list[str], *, label: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(_REPO))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--skip-agreement-ingest", action="store_true")
    p.add_argument("--skip-p2", action="store_true")
    p.add_argument("--skip-probes", action="store_true")
    p.add_argument("--skip-write-bench", action="store_true")
    args = p.parse_args()

    store_dir = _REPO / "agents" / args.store
    queries = _CURRICULUM / "data" / "queries_write_pilot-v1.jsonl"

    if not args.skip_agreement_ingest:
        _run(
            [
                _PY,
                str(_MICRO / "run_meta_grammar_agreement_pure.py"),
                "--rounds",
                "1",
                "--modes",
                "phrase_vis",
            ],
            label="agreement-ingest",
        )

    if not args.skip_p2:
        _run([_PY, str(_MICRO / "run_phrase_p2_lab.py"), "--store", args.store], label="p2")

    if not args.skip_probes:
        _run(
            [_PY, str(_CURRICULUM / "probe_phrase_agent_store.py"), "--store", args.store],
            label="phrase-agent-store",
        )
        _run(
            [_PY, str(_MICRO / "run_promote_bootstrap_routes.py"), "--store", args.store],
            label="promote-routes",
        )

    if not args.skip_write_bench:
        out_path = _CURRICULUM / "generated" / "bench-write-sketch-pilot.json"
        if _store_has_kb_field_bundle(store_dir):
            bench_cmd = [
                _PY,
                "-m",
                "casa.cli.bench.bench_write_sketch",
                "--queries",
                str(queries),
                "--store-dir",
                str(store_dir),
                "--out",
                str(out_path),
            ]
        else:
            bench_cmd = [
                _PY,
                str(_CURRICULUM / "bench_write_phrase_sketch.py"),
                "--queries",
                str(queries),
                "--store-dir",
                str(store_dir),
                "--out",
                str(out_path),
            ]
        _run(bench_cmd, label="write-bench")

    summary: dict = {"phase": "coherent_text_sprint", "store": args.store, "ok": True}
    bench_path = _CURRICULUM / "generated" / "bench-write-sketch-pilot.json"
    if bench_path.is_file():
        summary["write_bench"] = json.loads(bench_path.read_text(encoding="utf-8"))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
