#!/usr/bin/env python3
"""Smoke: L2 sharding stats + new word route + babble on small store."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state, save_field_state  # type: ignore
from sss_babble_v0 import babble_from_sss  # type: ignore
from sss_cylinders_v0 import ensure_cylinders  # type: ignore
from sss_l2_shard_v0 import resolve_l2_lattice_for_read, route_l2_lattice, shard_stats  # type: ignore
from sss_vocab_v0 import listen_word  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--new-word", default="класс")
    p.add_argument("--cue-word", default="колобок")
    p.add_argument("--write", action="store_true")
    args = p.parse_args()

    path = args.store_dir / "field_state.json"
    state = ensure_cylinders(load_field_state(path))
    before = shard_stats(state)

    rep = listen_word(state, args.new_word, copies=2, link_scene=False)
    route_new = route_l2_lattice(state, args.new_word)
    route_cue = resolve_l2_lattice_for_read(state, args.cue_word)
    wake = babble_from_sss(state, lattice_id="L2_word", prompt=args.cue_word)
    top = (wake.get("active") or [{}])[0]

    if args.write:
        save_field_state(path, state)

    report = {
        "before": before,
        "after": shard_stats(state),
        "new_word_listen": rep,
        "route_new": route_new,
        "route_cue_legacy": route_cue,
        "babble_cue": args.cue_word,
        "babble_top": top,
        "ok": top.get("concept_id") == f"lang.word.{args.cue_word}",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
