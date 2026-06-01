#!/usr/bin/env python3
"""Migrate agent stores: full field_state.json → ltm/ + thin checkpoint overlay."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.compact_persist import compact_persist_store
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.migrate_progress import (
    StepTimer,
    progress,
    resolve_parallel_workers,
    set_progress_enabled,
)
from casa.prisms.shared.runtime_checkpoint import is_thin_checkpoint_file
from casa.prisms.shared.store_layout import (
    LAB_DATA_DIR,
    LAB_LEGACY_STORES_DIR,
    field_state_path,
    ltm_root,
)
from casa.prisms.shared.store_persist import save_runtime_state


def _mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024) if path.is_file() else 0.0


def migrate_store(
    store_dir: Path,
    *,
    backup: bool,
    dry_run: bool,
    min_legacy_mb: float,
    verbose: bool = True,
    parallel_workers: int = 0,
) -> dict:
    store_dir = store_dir.resolve()
    fs = field_state_path(store_dir)
    rep: dict = {"store": store_dir.name, "status": "skipped"}

    if not fs.is_file():
        rep["reason"] = "no_field_state"
        return rep

    if is_thin_checkpoint_file(fs):
        rep["status"] = "already_thin"
        rep["field_state_mb"] = round(_mb(fs), 2)
        progress(f"  already thin ({rep['field_state_mb']} MiB)")
        return rep

    before_mb = _mb(fs)
    rep["field_state_mb_before"] = round(before_mb, 2)
    if before_mb < min_legacy_mb:
        rep["reason"] = f"below_min_legacy_mb={min_legacy_mb}"
        return rep

    if dry_run:
        rep["status"] = "dry_run"
        rep["would_backup"] = backup
        return rep

    t0 = time.perf_counter()
    with StepTimer("load field_state", f"{before_mb:.1f} MiB"):
        state = ensure_prisms(load_field_state(fs, store_dir=store_dir))
    ltm_dir = ltm_root(store_dir)
    ltm_dir.mkdir(parents=True, exist_ok=True)

    from casa.prisms.memory.l2_remigrate import ensure_l2_sharded_for_export, needs_l2_remigrate
    from casa.prisms.memory.l3_remigrate import ensure_l3_sharded_for_export, needs_l3_remigrate

    if needs_l2_remigrate(state):
        with StepTimer("L2 remigrate", "monolith → shards"):
            rem = ensure_l2_sharded_for_export(
                state,
                on_word_progress=_remigrate_word_progress if verbose else None,
            )
    else:
        progress("  L2 remigrate skipped (already sharded)")
        rem = None
    if rem:
        rep["l2_remigrate"] = rem
        progress(
            f"  remigrate done: {rem.get('words_remigrated')} words, "
            f"max_shard_vocab={rem.get('max_shard_vocab')}"
        )

    workers = resolve_parallel_workers(parallel_workers)
    if workers >= 2 and verbose:
        progress(f"  parallel workers: {workers} (L3 remigrate + ltm writes)")

    if needs_l3_remigrate(state):
        with StepTimer("L3 remigrate", "monolith → phrase shards"):
            rem3 = ensure_l3_sharded_for_export(
                state,
                on_token_progress=_remigrate_token_progress if verbose else None,
                parallel_workers=workers,
            )
    else:
        progress("  L3 remigrate skipped (already sharded)")
        rem3 = None
    if rem3:
        rep["l3_remigrate"] = rem3
        progress(
            f"  L3 remigrate done: {rem3.get('tokens_remigrated')} tokens, "
            f"max_shard_vocab={rem3.get('max_shard_vocab')}"
        )

    ltm_parallel = workers if workers >= 2 else 0
    with StepTimer("compact_persist", "ltm/*.ltm"):
        cp = compact_persist_store(
            store_dir,
            state,
            reason="migrate_thin_checkpoint",
            skip_vocab_over=65535,
            progress=verbose,
            remigrate_l2=False,
            remigrate_l3=False,
            parallel_writes=ltm_parallel,
        )
    totals = cp.get("manifest_totals") or {}
    rep["compact_persist"] = {
        "lattice_count": totals.get("lattice_count"),
        "content_prisms": cp.get("content_prisms"),
    }
    skipped = (cp.get("manifest") or {}).get("skipped_vocab_lattices") if isinstance(cp.get("manifest"), dict) else None
    if skipped:
        rep["skipped_vocab_lattices"] = skipped
        progress(f"  skipped {len(skipped)} lattices over u16 vocab (see manifest)")

    legacy = store_dir / "field_state.legacy.json"
    if backup and not legacy.is_file():
        with StepTimer("backup", "field_state.legacy.json"):
            shutil.copy2(fs, legacy)
        rep["backup"] = str(legacy)

    with StepTimer("thin checkpoint", "field_state.json"):
        save_rep = save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=False)
    rep["save_runtime"] = {
        "thin": save_rep.get("thin_checkpoint"),
        "format": save_rep.get("checkpoint_format"),
    }

    after_mb = _mb(fs)
    rep["field_state_mb_after"] = round(after_mb, 2)
    rep["ltm_total_mb"] = round(
        sum(f.stat().st_size for f in ltm_dir.rglob("*") if f.is_file()) / (1024 * 1024),
        2,
    )
    rep["elapsed_s"] = round(time.perf_counter() - t0, 1)
    rep["status"] = "ok"
    progress(f"  done: field_state {before_mb:.1f} → {after_mb:.1f} MiB, ltm {rep['ltm_total_mb']} MiB")
    return rep


def _remigrate_word_progress(done: int, total: int, shard: str) -> None:
    progress(f"  remigrate words {done}/{total} (shard {shard})")


def _remigrate_token_progress(done: int, total: int, shard: str) -> None:
    progress(f"  remigrate L3 tokens {done}/{total} (shard {shard})")


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate stores to ltm/ + thin field_state")
    p.add_argument(
        "--stores-root",
        type=Path,
        default=_REPO / LAB_DATA_DIR / LAB_LEGACY_STORES_DIR,
        help="Parent of store-id directories",
    )
    p.add_argument("--store", type=str, default=None, help="Single store id")
    p.add_argument("--backup", action="store_true", help="Keep field_state.legacy.json copy")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--min-mb", type=float, default=1.0, help="Only migrate if field_state >= N MiB")
    p.add_argument("--quiet", action="store_true", help="No progress lines (JSON report only)")
    p.add_argument(
        "--parallel-workers",
        type=int,
        default=0,
        help="L3 remigrate + parallel ltm writes: 0=auto (cpu), 1=sequential, N>=2",
    )
    args = p.parse_args()

    set_progress_enabled(not args.quiet)

    root = args.stores_root.resolve()
    if args.store:
        stores = [root / args.store]
    else:
        stores = sorted(d for d in root.iterdir() if d.is_dir() and (d / "field_state.json").is_file())

    reports: list[dict] = []
    for sd in stores:
        progress(f"migrate {sd.name}")
        reports.append(
            migrate_store(
                sd,
                backup=args.backup,
                dry_run=args.dry_run,
                min_legacy_mb=args.min_mb,
                verbose=not args.quiet,
                parallel_workers=args.parallel_workers,
            )
        )

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    failed = [r for r in reports if r.get("status") not in ("ok", "already_thin", "skipped", "dry_run")]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
