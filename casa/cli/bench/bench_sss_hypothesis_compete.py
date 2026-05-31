#!/usr/bin/env python3
"""Smoke: multi H: hypothesis competition on field."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.sss_field_hypotheses_v0 import compete_hypotheses, h_votes_for_word
from casa.prisms.memory.sss_segment_v0 import verify_segment


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--word", default="встреча")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    hyp = compete_hypotheses(state, args.word)
    ver = verify_segment(hyp)
    report = {
        "word": args.word,
        "attempt": hyp.get("segment"),
        "inner_ok": ver.get("ok"),
        "competition": hyp.get("competition"),
        "h_votes_after": h_votes_for_word(state, args.word),
        "rule_id": hyp.get("rule_id"),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
