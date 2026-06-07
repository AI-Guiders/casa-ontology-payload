#!/usr/bin/env python3
"""Von-neumann next track — steps 1–6 orchestrator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CURRICULUM = Path(__file__).resolve().parent
_MICRO = _CURRICULUM / "micro-literacy"
_PY = sys.executable
_STORE_DEFAULT = "von-neumann"


def _run(cmd: list[str], *, label: str, check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(_REPO), check=check)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default=_STORE_DEFAULT)
    p.add_argument("--skip-repair", action="store_true")
    p.add_argument("--skip-nca", action="store_true")
    p.add_argument("--nca-dry-run", action="store_true")
    p.add_argument("--nca-max-shards", type=int, default=2, help="L3 pilot train cap")
    p.add_argument("--skip-paradigm-ingest", action="store_true")
    p.add_argument("--skip-write-hot", action="store_true")
    p.add_argument("--skip-read-spike", action="store_true")
    args = p.parse_args()

    store_dir = _REPO / "agents" / args.store
    gen = _CURRICULUM / "generated"
    gen.mkdir(parents=True, exist_ok=True)
    summary: dict = {"phase": "von_neumann_next_track", "store": args.store, "steps": {}}

    if not args.skip_repair:
        cp = _run(
            [
                _PY,
                str(_REPO / "tools" / "von_neumann_store_repair.py"),
                "--store-dir",
                str(store_dir),
                "--repair",
                "--force-repair",
                "--out",
                str(gen / "store-repair-report.json"),
            ],
            label="store-repair",
            check=False,
        )
        summary["steps"]["repair"] = {"exit_code": cp.returncode}
        if cp.returncode != 0:
            print("warn: store repair reported mismatches (see report)", flush=True)

    if not args.skip_nca:
        nca_cmd = [
            _PY,
            "-m",
            "casa.prisms.memory.train_memory_nca_shards",
            "--store-dir",
            str(store_dir),
            "--layer",
            "L3",
            "--max-shards",
            str(args.nca_max_shards),
            "--no-skip-trained",
        ]
        if args.nca_dry_run:
            nca_cmd.append("--dry-run")
        _run(nca_cmd, label="nca-l3-train")

    if not args.skip_paradigm_ingest:
        _run(
            [_PY, str(_MICRO / "run_paradigm_co_ingest_lab.py")],
            label="paradigm-co-ingest",
        )

    write_queries = _CURRICULUM / "data" / "queries_write_pilot-v1.jsonl"
    if not args.skip_write_hot:
        cp = _run(
            [
                _PY,
                str(_CURRICULUM / "bench_write_hot_path.py"),
                "--queries",
                str(write_queries),
                "--store-dir",
                str(store_dir),
                "--out",
                str(gen / "bench-write-hot-path.json"),
            ],
            label="write-hot-path",
            check=False,
        )
        summary["steps"]["write_hot"] = {"exit_code": cp.returncode}

    read_queries = _CURRICULUM / "data" / "queries_canon_read_spike-v1.jsonl"
    if not args.skip_read_spike:
        _run(
            [
                _PY,
                str(_CURRICULUM / "bench_read_discourse_spike.py"),
                "--queries",
                str(read_queries),
                "--store-dir",
                str(store_dir),
                "--out",
                str(gen / "bench-read-discourse-spike.json"),
            ],
            label="read-discourse-spike",
            check=False,
        )
        spike_path = gen / "bench-read-discourse-spike.json"
        if spike_path.is_file():
            summary["steps"]["read_spike"] = json.loads(spike_path.read_text(encoding="utf-8"))

    summary["ok"] = True
    out_path = gen / "von-neumann-next-track-summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
