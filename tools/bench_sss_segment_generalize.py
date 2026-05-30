#!/usr/bin/env python3
"""Bench: rule from one correction → generalize segment on held-out words."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, run_sleep, save_state  # type: ignore
from sss_hypothesis_v0 import hypothesis_turn  # type: ignore
from sss_segment_v0 import format_segment, segment_vowel_nuclei  # type: ignore


def _eval(state: dict, words: list[str]) -> list[dict]:
    rows = []
    for w in words:
        r = hypothesis_turn(state, w)
        gold = format_segment(segment_vowel_nuclei(w))
        rows.append(
            {
                "word": w,
                "attempt": r["attempt"],
                "gold": gold,
                "rule_id": r["hypothesis"]["rule_id"],
                "ok": r["attempt"] == gold,
                "verify": r["verify"],
            }
        )
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--train-word", default="встреча")
    p.add_argument("--train-gold", default="встре|ча")
    p.add_argument("--heldout", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    heldout = json.loads(args.heldout.read_text(encoding="utf-8"))
    words = heldout if isinstance(heldout, list) else heldout.get("words") or []

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))

    before = _eval(copy.deepcopy(state), words)

    train = hypothesis_turn(
        state,
        args.train_word,
        teacher_segment=args.train_gold,
        rule_id="rule.segment.vowel_nuclei",
        rule_hint="сколько гласных, столько слогов; каждый слог — одна гласная",
        bundle=bundle,
    )
    sleep = run_sleep(state, bundle)
    after = _eval(state, words)

    passed_before = sum(1 for r in before if r["ok"])
    passed_after = sum(1 for r in after if r["ok"])

    report = {
        "train": train,
        "sleep": sleep,
        "active_rules": (state.get("sss") or {}).get("active_segment_rules"),
        "before": {"passed": passed_before, "total": len(before), "items": before},
        "after": {"passed": passed_after, "total": len(after), "items": after},
        "generalized": passed_after > passed_before,
    }

    save_state(path, state)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
