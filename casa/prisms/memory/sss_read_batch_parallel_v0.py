#!/usr/bin/env python3
"""Parallel Afanasyev-style batch: N workers × shard store → merge."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import multiprocessing as mp
import os
import time
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, save_state
from casa.prisms.memory.sss_merge_field_states_v0 import merge_field_states
from casa.prisms.memory.sss_read_batch_v0 import read_batch
from casa.prisms.memory.sss_text_tokenize_v0 import norm_text


def _worker_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    os.chdir(payload["root"])
    bukvar = json.loads(Path(payload["bukvar"]).read_text(encoding="utf-8"))
    base = ensure_prisms(load_field_state(Path(payload["base_store"])))
    base_fv = int(base.get("field_version") or 0)
    shard_dir = Path(payload["shard_dir"])
    shard_dir.mkdir(parents=True, exist_ok=True)
    shard_store = shard_dir / "field_state.json"

    # Temp corpus dir with symlinks/hardlinks not needed — pass files via mini dir
    work_dir = shard_dir / "corpus"
    work_dir.mkdir(exist_ok=True)
    for src in payload["files"]:
        src_p = Path(src)
        dst = work_dir / src_p.name
        if not dst.exists():
            try:
                os.link(src_p, dst)
            except OSError:
                dst.write_text(src_p.read_text(encoding="utf-8"), encoding="utf-8")

    t0 = time.perf_counter()
    report = read_batch(
        base,
        work_dir,
        bukvar_bundle=bukvar,
        listen_copies=int(payload["listen_copies"]),
        sleep_once=False,
        min_word_len=int(payload["min_word_len"]),
        use_field=bool(payload["use_field"]),
        store_path=None,
        checkpoint_every=0,
        resume=False,
        compact_save=True,
        progress_sidecar=False,
    )
    base["_merge_base_fv"] = base_fv
    save_state(shard_store, base, compact=True)
    meta = shard_dir / "shard_meta.json"
    meta.write_text(
        json.dumps(
            {
                "worker": payload["worker_id"],
                "files": payload["files"],
                "tales_read": report.get("tales_read"),
                "field_version": base.get("field_version"),
                "_merge_base_fv": base_fv,
                "elapsed_s": round(time.perf_counter() - t0, 1),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "worker_id": payload["worker_id"],
        "shard_store": str(shard_store),
        "tales_read": report.get("tales_read"),
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }


def _chunk_files(files: list[Path], workers: int) -> list[list[Path]]:
    n = max(1, workers)
    chunks: list[list[Path]] = [[] for _ in range(n)]
    for i, fp in enumerate(files):
        chunks[i % n].append(fp)
    return [c for c in chunks if c]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--bukvar", type=Path, default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--listen-copies", type=int, default=1)
    p.add_argument("--field", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--workers", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    p.add_argument("--shard-dir", type=Path, default=None, help="Temp shards (default store-dir/_parallel_shards)")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--sleep", action="store_true", help="Run sleep once after merge")
    args = p.parse_args()

    root = Path.cwd().resolve()
    store_path = args.store_dir / "field_state.json"
    base_state = ensure_prisms(load_field_state(store_path))
    done = set((base_state.get("batch_progress") or {}).get("files") or []) if args.resume else set()

    all_files = sorted(args.corpus_dir.glob("*.txt"))
    pending = [fp for fp in all_files if fp.name not in done]
    if not pending:
        print(json.dumps({"status": "nothing_to_do", "done": len(done)}, ensure_ascii=False))
        return

    workers = min(max(1, args.workers), len(pending))
    chunks = _chunk_files(pending, workers)
    shard_root = args.shard_dir or (args.store_dir / "_parallel_shards")
    shard_root.mkdir(parents=True, exist_ok=True)

    print(
        f"[parallel] {len(pending)} tales, {len(chunks)} workers, base_fv={base_state.get('field_version')}",
        flush=True,
    )

    payloads = []
    for wid, chunk in enumerate(chunks):
        payloads.append(
            {
                "worker_id": wid,
                "root": str(root),
                "base_store": str(store_path),
                "bukvar": str(args.bukvar.resolve()),
                "files": [str(f.resolve()) for f in chunk],
                "shard_dir": str((shard_root / f"worker_{wid:02d}").resolve()),
                "listen_copies": max(1, args.listen_copies),
                "use_field": args.field,
                "min_word_len": 1,
            }
        )

    t0 = time.perf_counter()
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=len(chunks)) as pool:
        results = pool.map(_worker_ingest, payloads)

    shards = [json.loads(Path(r["shard_store"]).read_text(encoding="utf-8")) for r in results]
    base_fv = int(base_state.get("field_version") or 0)
    merged = merge_field_states(base_state, shards, base_field_version=base_fv)

    sleep_report = None
    if args.sleep and args.bukvar.exists():
        bukvar = json.loads(args.bukvar.read_text(encoding="utf-8"))
        from casa.prisms.memory.sss_cylinders_v0 import run_sleep

        sleep_report = run_sleep(merged, bukvar)

    save_state(store_path, merged, compact=True)
    report = {
        "parallel": True,
        "workers": len(chunks),
        "pending_tales": len(pending),
        "worker_results": results,
        "sleep": sleep_report,
        "field_version": merged.get("field_version"),
        "files_done": len(merged.get("batch_progress", {}).get("files") or []),
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
