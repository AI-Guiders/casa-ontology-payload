#!/usr/bin/env python3
"""Bench nca_stale_shards: pending ingest marks shard stale without full train."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from copy import deepcopy
from pathlib import Path

from casa.prisms.memory.lexicon_cold_ingest import process_lexicon_misses
from casa.prisms.shared.nca_registry import find_stale_shards, load_registry, merge_pending
from casa.prisms.shared.store_boot import boot_store


def run_bench(state: dict, store_dir: Path, *, headwords: Path, min_tokens: int) -> dict:
    state = deepcopy(state)
    word = "компьютер"
    prefix = "комп"

    before = find_stale_shards(state, store_dir, repair_smoke=False, min_tokens=min_tokens)
    ingest = process_lexicon_misses(
        state,
        [{"prefix": prefix, "word": word, "reason": "bench"}],
        store_dir=store_dir,
        headwords_path=headwords,
    )
    shard = next(iter(ingest.get("shard_histogram") or {}), None)
    if not shard:
        raise RuntimeError("cold ingest did not report shard_histogram")

    after = find_stale_shards(state, store_dir, repair_smoke=False, min_tokens=min_tokens)
    stale_ids = {r["lattice_id"] for r in after}
    reg = load_registry(store_dir)
    row = next((r for r in after if r["lattice_id"] == shard), None)

    ok = shard in stale_ids and row is not None and "pending_ingest" in row["reasons"]
    return {
        "schema_version": 1,
        "bench": "nca_stale_pending",
        "word": word,
        "shard": shard,
        "min_tokens": min_tokens,
        "ingest": ingest,
        "before_stale_count": len(before),
        "after_stale_count": len(after),
        "pending": reg.get("pending"),
        "stale_row": row,
        "shard_stale": ok,
        "ok": ok,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench stale shard detection after cold ingest")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--headwords", type=Path, required=True)
    p.add_argument("--min-tokens", type=int, default=1, help="Dev store shards are sparse; default 1")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    boot = boot_store(args.store_dir, prefer_field_state=True)
    report = run_bench(
        boot["state"],
        args.store_dir.resolve(),
        headwords=args.headwords,
        min_tokens=args.min_tokens,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
