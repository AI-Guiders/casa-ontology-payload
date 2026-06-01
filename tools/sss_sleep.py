#!/usr/bin/env python3
"""T_sleep CLI — consolidate prism_hippo → prism_memory; persist runtime checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.memory.memory_prisms import ensure_prisms, hippo_episodes, run_sleep
from casa.prisms.memory.sleep_job import note_sleep_batch, sleep_job_should_yield
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.migrate_progress import progress, set_progress_enabled
from casa.prisms.shared.store_boot import apply_store_boot_profile
from casa.prisms.shared.store_layout import field_state_path, ltm_root
from casa.prisms.shared.store_persist import save_runtime_state


def _load_bundle(store_dir: Path, bundle: Path | None) -> dict:
    if bundle is not None:
        return json.loads(bundle.read_text(encoding="utf-8"))
    bs = sorted((store_dir / "bundles").glob("*.json"))
    if not bs:
        raise SystemExit(f"no bundle in {store_dir / 'bundles'} and --bundle not set")
    return json.loads(bs[0].read_text(encoding="utf-8"))


def _maybe_thin_first(store_dir: Path) -> dict | None:
    from casa.prisms.shared.runtime_checkpoint import is_thin_checkpoint_file

    fs = field_state_path(store_dir)
    if is_thin_checkpoint_file(fs):
        return None
    if not (ltm_root(store_dir) / "pack.manifest.json").is_file():
        return None
    from migrate_thin_checkpoint import migrate_store

    progress("thin-first: migrate fat field_state → ltm/ + thin checkpoint")
    return migrate_store(store_dir, backup=True, dry_run=False, min_legacy_mb=1.0, verbose=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Run T_sleep (hippo consolidate → memory)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, default=None, help="KB payload; default: first store/bundles/*.json")
    p.add_argument("--strength", type=int, default=4)
    p.add_argument("--replay-k", type=int, default=0)
    p.add_argument("--replay-value-weight", type=float, default=0.0)
    p.add_argument("--nca-model", type=Path, default=None)
    p.add_argument("--nca-lattice-id", default="L1_syllable")
    p.add_argument(
        "--compact-persist",
        action="store_true",
        help="force compact_persist after sleep (also when store.compact_persist_on_sleep)",
    )
    p.add_argument("--no-save", action="store_true", help="dry run: sleep in memory only")
    p.add_argument(
        "--batch-size",
        type=int,
        default=0,
        help="max episodes per run_sleep call (0 = all in one pass, ADR-0023 v0 compat)",
    )
    p.add_argument("--max-batches", type=int, default=0, help="stop after N batches (0 = until hippo empty)")
    p.add_argument("--progress", action="store_true", help="stderr progress between batches")
    p.add_argument(
        "--thin-first",
        action="store_true",
        help="if fat checkpoint and ltm manifest exist: migrate to thin once before sleep",
    )
    p.add_argument(
        "--parallel-ltm",
        type=int,
        default=0,
        help="parallel .ltm writers in compact_persist (0=sequential, 4–8 typical)",
    )
    args = p.parse_args()

    set_progress_enabled(args.progress)

    store_dir = args.store_dir.resolve()
    fs = field_state_path(store_dir)
    if not fs.is_file():
        raise SystemExit(f"no field_state: {fs}")

    t0 = time.perf_counter()
    thin_rep = _maybe_thin_first(store_dir) if args.thin_first else None
    state = ensure_prisms(load_field_state(fs))
    apply_store_boot_profile(store_dir, state)
    bundle = _load_bundle(store_dir, args.bundle)
    before_total = len(hippo_episodes(state))

    batches: list[dict] = []
    batch_size = max(0, int(args.batch_size))
    max_batches = max(0, int(args.max_batches))
    parallel_ltm = max(0, int(args.parallel_ltm))
    if parallel_ltm >= 2:
        state.setdefault("store", {})["compact_persist_parallel_writes"] = parallel_ltm

    if batch_size <= 0:
        rep = run_sleep(
            state,
            bundle,
            strength=args.strength,
            nca_model_path=args.nca_model,
            nca_lattice_id=args.nca_lattice_id,
            replay_k=args.replay_k,
            replay_value_weight=args.replay_value_weight,
            store_dir=store_dir if not args.no_save else None,
            compact_persist=True if args.compact_persist else None,
        )
        batches.append(rep)
    else:
        batch_i = 0
        while True:
            if sleep_job_should_yield(state):
                if args.progress:
                    progress("sleep yield: wake/interrupt before next batch")
                break
            pending_before = len(hippo_episodes(state))
            if pending_before == 0:
                break
            batch_i += 1
            t_batch = time.perf_counter()
            rep = run_sleep(
                state,
                bundle,
                strength=args.strength,
                nca_model_path=args.nca_model,
                nca_lattice_id=args.nca_lattice_id,
                replay_k=args.replay_k,
                replay_value_weight=args.replay_value_weight,
                store_dir=store_dir if not args.no_save else None,
                compact_persist=True if args.compact_persist else None,
                max_episodes=batch_size,
            )
            pending_after = len(hippo_episodes(state))
            batch_elapsed = time.perf_counter() - t_batch
            note_sleep_batch(
                state,
                pending_after=pending_after,
                merged=int(rep.get("merged") or 0),
                max_episodes=batch_size,
            )
            batches.append(rep)
            if args.progress:
                progress(
                    f"sleep batch {batch_i}: merged={rep.get('merged')} "
                    f"pending {pending_before}→{pending_after} "
                    f"elapsed={batch_elapsed:.1f}s"
                )
            if not args.no_save:
                save_runtime_state(store_dir, state, force=True)
            if max_batches and batch_i >= max_batches:
                break
            if pending_after >= pending_before:
                break
            if pending_after == 0:
                break

    after_total = len(hippo_episodes(state))
    elapsed = time.perf_counter() - t0
    last = batches[-1] if batches else {}

    out: dict = {
        "store_dir": str(store_dir),
        "hippo_episodes_before": before_total,
        "hippo_episodes_after": after_total,
        "sleep": last,
        "batches": len(batches),
        "elapsed_s": round(elapsed, 3),
        "field_version": int(state.get("field_version") or 0),
    }
    if thin_rep is not None:
        out["thin_first"] = thin_rep
    if len(batches) > 1:
        out["sleep_batches"] = [
            {
                "merged": b.get("merged"),
                "pending": b.get("pending"),
                "batch": b.get("batch"),
            }
            for b in batches
        ]

    if not args.no_save and batch_size <= 0:
        out["persist"] = save_runtime_state(store_dir, state, force=True)
    elif not args.no_save and batch_size > 0:
        out["persist"] = {"saved": True, "note": "checkpoint flushed each batch"}

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
