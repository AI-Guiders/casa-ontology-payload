#!/usr/bin/env python3
"""Re-assign all L2 words to shards using lexicographic (dictionary) routing."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_l2_shard_v0 import (
    LEX_PLAN_ALPHA,
    LEGACY_L2,
    SHARD_MODE_HASH,
    SHARD_MODE_LEXICOGRAPHIC,
    clear_l2_shards,
    configure_lex_sharding,
    empty_l2_lattice,
    is_l2_word_lattice,
    lex_sort_key,
    register_word_shard,
    route_l2_lattice,
    sharding_config,
    shard_stats,
)
from casa.prisms.memory.sss_stack_v0 import decode_lattice
from casa.prisms.memory.sss_vocab_v0 import _strengthen_word_on_l2, norm_word

_L2_WORD_RE = re.compile(r"^W:(.+)$")
_L2_CONCEPT_RE = re.compile(r"^lang\.word\.(.+)$")


def collect_words_from_l2(state: dict) -> dict[str, int]:
    """Gather headwords + vote weight from all L2 lattices."""
    votes: dict[str, int] = {}
    for lid, lat in memory_lattices(state).items():
        if not is_l2_word_lattice(lid):
            continue
        for cell in lat.get("cells") or []:
            for t in cell:
                m = _L2_WORD_RE.match(str(t))
                if m:
                    w = norm_word(m.group(1))
                    votes[w] = votes.get(w, 0) + 1
        dec = decode_lattice(lat, min_votes=1)
        for c in dec.get("concepts") or []:
            cid = str(c.get("concept_id") or "")
            m = _L2_CONCEPT_RE.match(cid)
            if m:
                w = norm_word(m.group(1))
                votes[w] = max(votes.get(w, 0), int(c.get("votes") or 1))
    return votes


def remigrate_lex(
    state: dict,
    *,
    mode: str = SHARD_MODE_LEXICOGRAPHIC,
    lex_plan: str | None = None,
    max_copies: int = 6,
    progress_every: int = 2000,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    words = collect_words_from_l2(state)
    if not words:
        raise SystemExit("No L2 words found in store")

    cfg = sharding_config(state)
    cfg["enabled"] = True
    cfg["mode"] = mode
    if mode == SHARD_MODE_LEXICOGRAPHIC:
        if lex_plan == LEX_PLAN_ALPHA:
            from casa.prisms.memory.sss_l2_shard_v0 import build_letter_ranges

            n = int(cfg.get("num_shards") or 64)
            cfg["letter_ranges"] = build_letter_ranges(n)
            cfg["lex_plan"] = LEX_PLAN_ALPHA
            cfg.pop("lex_shard_starts", None)
            cfg.pop("initial_letter_counts", None)
        else:
            configure_lex_sharding(cfg, words.keys())
    else:
        cfg["letter_ranges"] = None
        cfg.pop("lex_shard_starts", None)
        cfg.pop("initial_letter_counts", None)
        cfg.pop("lex_plan", None)
    state["l2_sharding"] = cfg
    sharding_config(state)

    clear_l2_shards(state, keep_legacy=True)
    lattices = memory_lattices(state)
    lattices[LEGACY_L2] = empty_l2_lattice()
    lattices[LEGACY_L2]["legacy_cleared"] = True

    t0 = time.perf_counter()
    migrated = 0
    items = sorted(words.items(), key=lambda kv: lex_sort_key(kv[0]))
    for i, (w, wv) in enumerate(items, 1):
        copies = max(1, min(max_copies, (wv + 1) // 2))
        lid = route_l2_lattice(state, w)
        _strengthen_word_on_l2(state, w, copies=copies)
        register_word_shard(state, w, lid)
        migrated += 1
        if progress_every and i % progress_every == 0:
            print(f"[remigrate] {i}/{len(items)} last={w} shard={lid}", flush=True)

    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "words_remigrated": migrated,
        "mode": mode,
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "shard_stats": shard_stats(state),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Re-shard L2 by dictionary letter order")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument(
        "--mode",
        choices=[SHARD_MODE_LEXICOGRAPHIC, SHARD_MODE_HASH],
        default=SHARD_MODE_LEXICOGRAPHIC,
    )
    p.add_argument(
        "--lex-plan",
        choices=[LEX_PLAN_ALPHA],
        default=None,
        help="Force alphabet-slice plan (default: corpus quantile from headwords)",
    )
    p.add_argument("--max-copies", type=int, default=6)
    p.add_argument("--compact", action="store_true", default=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    before = shard_stats(state)
    rep = remigrate_lex(
        state,
        mode=args.mode,
        lex_plan=args.lex_plan,
        max_copies=args.max_copies,
    )
    save_field_state(path, state, compact=args.compact)
    report = {"before": before, **rep, "after": shard_stats(state)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
