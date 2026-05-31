#!/usr/bin/env python3
"""Migrate lang.word.* from legacy L2_word monolith into L2_word_XX shards."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
import argparse
import json
import time
from pathlib import Path
from typing import Any

from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_l2_shard_v0 import (  # type: ignore
    LEGACY_L2,
    SHARD_MODE_HASH,
    SHARD_MODE_LEXICOGRAPHIC,
    configure_lex_sharding,
    empty_l2_lattice,
    lex_sort_key,
    register_word_shard,
    route_l2_lattice,
    sharding_config,
    shard_stats,
)
from sss_stack_v0 import decode_lattice  # type: ignore
from sss_vocab_v0 import _strengthen_word_on_l2, norm_word  # type: ignore


def legacy_word_votes(state: dict) -> dict[str, int]:
    legacy = memory_lattices(state).get(LEGACY_L2) or {}
    votes: dict[str, int] = {}
    for cell in legacy.get("cells") or []:
        for t in cell:
            if t.startswith("W:"):
                w = t[2:]
                votes[w] = votes.get(w, 0) + 1
    if votes:
        return votes
    dec = decode_lattice(legacy, min_votes=1)
    for c in dec.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith("lang.word."):
            w = cid[len("lang.word.") :]
            votes[w] = int(c.get("votes") or 1)
    return votes


def migrate_monolith_to_shards(
    state: dict,
    *,
    clear_legacy: bool = True,
    max_copies: int = 6,
    progress_every: int = 2000,
    mode: str = SHARD_MODE_LEXICOGRAPHIC,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    cfg["enabled"] = True
    cfg["mode"] = mode
    state["l2_sharding"] = cfg

    words = legacy_word_votes(state)
    if mode == SHARD_MODE_LEXICOGRAPHIC:
        configure_lex_sharding(cfg, words.keys())
    else:
        cfg["letter_ranges"] = None
        cfg.pop("lex_shard_starts", None)
        cfg.pop("initial_letter_counts", None)
    state["l2_sharding"] = cfg
    sharding_config(state)
    t0 = time.perf_counter()
    migrated = 0
    order = sorted(words.items(), key=lambda kv: lex_sort_key(kv[0]))
    for i, (w, wv) in enumerate(order, 1):
        copies = max(1, min(max_copies, (wv + 1) // 2))
        lid = route_l2_lattice(state, w)
        _strengthen_word_on_l2(state, w, copies=copies)
        register_word_shard(state, w, lid)
        migrated += 1
        if progress_every and i % progress_every == 0:
            print(f"[migrate] {i}/{len(words)} last={w} shard={lid}", flush=True)

    if clear_legacy:
        lattices = memory_lattices(state)
        lattices[LEGACY_L2] = empty_l2_lattice()
        lattices[LEGACY_L2]["legacy_cleared"] = True
        prism_memory(state)["lattices"] = lattices
        state.setdefault("sss", {})["lattices"] = lattices

    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "words_migrated": migrated,
        "clear_legacy": clear_legacy,
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "shard_stats": shard_stats(state),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--clear-legacy", action="store_true", default=True)
    p.add_argument("--no-clear-legacy", action="store_false", dest="clear_legacy")
    p.add_argument("--max-copies", type=int, default=6)
    p.add_argument(
        "--shard-mode",
        choices=[SHARD_MODE_LEXICOGRAPHIC, SHARD_MODE_HASH],
        default=SHARD_MODE_LEXICOGRAPHIC,
    )
    p.add_argument("--compact", action="store_true", default=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    before = shard_stats(state)
    rep = migrate_monolith_to_shards(
        state,
        clear_legacy=args.clear_legacy,
        max_copies=args.max_copies,
        mode=args.shard_mode,
    )
    save_field_state(path, state, compact=args.compact)
    report = {"before": before, **rep, "after": shard_stats(state)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
