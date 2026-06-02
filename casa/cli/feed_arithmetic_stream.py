#!/usr/bin/env python3
"""Ingest a batch of generated arithmetic examples (teacher oracle at ingest time)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.arithmetic_stream import generate_batch
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import append_episode, memory_lattices, run_sleep
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.cli.ingest_state import resolve_ingest_state
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def feed_arithmetic_stream(
    store_dir: Path,
    *,
    count: int = 20,
    max_value: int = 50,
    seed: int | None = None,
    sleep: bool = True,
    persist: bool = True,
    bundle: dict[str, Any] | None = None,
    state: dict | None = None,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    bundle = bundle or {"claims": [], "graph": {"edges": []}}

    state = resolve_ingest_state(store_dir, state)
    state["store"]["last_feed"] = "arith_stream"

    if not (memory_lattices(state).get(SCHEMA_MATH) or {}).get("cells"):
        ingest_math_bundle(state, bundle, lattice_id=SCHEMA_MATH)

    examples = generate_batch(count, seed=seed, max_value=max_value)
    ep_ids: list[str] = []
    by_op: dict[str, int] = {}

    for ex in examples:
        ep = append_episode(
            state,
            cue=str(ex["cue"]),
            surface_attempt=str(ex["correct"]),
            correct=str(ex["correct"]),
            lattice_id=SCHEMA_MATH,
            concept_id=str(ex["concept_id"]),
            scene=str(ex.get("scene") or "arith_stream"),
            bundle=bundle,
            episode_source="ingest",
        )
        if ep:
            ep_ids.append(str(ep.get("id") or ""))
            by_op[str(ex.get("op") or "?")] = by_op.get(str(ex.get("op") or "?"), 0) + 1

    sleep_rep = run_sleep(state, bundle) if sleep and ep_ids else None

    rep: dict[str, Any] = {
        "store_dir": str(store_dir),
        "examples": len(examples),
        "episodes": len(ep_ids),
        "by_op": by_op,
        "max_value": max_value,
        "sleep": sleep_rep,
        "field_version": state.get("field_version"),
    }

    if persist:
        mark_runtime_dirty(state)
        rep["persist"] = save_runtime_state(
            store_dir,
            state,
            force=True,
            thin=True,
            sync_ltm_on_save=True,
        )
    return rep


def main() -> None:
    p = argparse.ArgumentParser(description="Feed arithmetic example stream into agent store")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--max-value", type=int, default=50)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args()

    rep = feed_arithmetic_stream(
        args.store_dir or default_agent_store(),
        count=max(1, args.count),
        max_value=max(1, args.max_value),
        seed=args.seed,
        sleep=not args.no_sleep,
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
