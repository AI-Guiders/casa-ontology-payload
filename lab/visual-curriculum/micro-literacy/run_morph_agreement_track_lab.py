#!/usr/bin/env python3
"""ADR-0036 W4–W7 track: agreement → P2 → paradigm → agent store → write bench."""

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
    p.add_argument("--skip-ingest", action="store_true")
    p.add_argument("--skip-p2", action="store_true")
    p.add_argument("--skip-probes", action="store_true")
    p.add_argument("--skip-write-bench", action="store_true")
    args = p.parse_args()

    store_dir = _REPO / "agents" / args.store
    queries = _CURRICULUM / "data" / "queries_write_pilot-v1.jsonl"

    if not args.skip_ingest:
        for script, extra in (
            ("run_meta_grammar_agreement_pure.py", ["--modes", "phrase_vis"]),
            ("run_meta_grammar_possessive_pure.py", ["--modes", "phrase_vis"]),
            ("run_meta_grammar_numeral_pure.py", ["--modes", "phrase_vis"]),
        ):
            _run(
                [_PY, str(_MICRO / script), "--rounds", "1", *extra],
                label=script,
            )

    if not args.skip_p2:
        _run([_PY, str(_MICRO / "run_phrase_p2_lab.py"), "--store", args.store], label="p2")

    if not args.skip_probes:
        for probe in ("probe_paradigm_select.py", "probe_phrase_agent_store.py"):
            _run([_PY, str(_CURRICULUM / probe), "--store", args.store], label=probe)
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

    summary: dict = {"phase": "morph_agreement_track", "store": args.store, "ok": True}
    for name in ("bench-write-sketch-pilot.json", "teacher-paradigm-select.json", "teacher-phrase-agent-store.json"):
        path = _CURRICULUM / "generated" / name
        if path.is_file():
            summary[name.replace(".json", "")] = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
