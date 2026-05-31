#!/usr/bin/env python3
"""Bench English syllable segmentation on cue list."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from sss_segment_en_v0 import (  # type: ignore
    format_segment,
    norm_word,
    segment_en_hypothesis,
    segment_en_vowel_nuclei,
    verify_segment_en,
    vowel_count_en,
)


def run_bench(cues: list[dict]) -> dict:
    rows: list[dict] = []
    passed = 0
    for item in cues:
        cue = str(item.get("cue") or "")
        expect = item.get("expect")
        word = norm_word(cue)
        hyp = segment_en_hypothesis(word)
        ver = verify_segment_en(hyp)
        hypothesis = hyp.get("hypothesis") or format_segment(hyp.get("syllables") or [])
        expect_seg = (
            format_segment(segment_en_vowel_nuclei(word))
            if expect is None
            else str(expect).replace(" ", "")
        )
        ok = ver["ok"] and bool(hyp.get("syllables"))
        if expect is not None:
            ok = ok and hypothesis == expect_seg
        if ok:
            passed += 1
        rows.append(
            {
                "id": item.get("id"),
                "cue": word,
                "expect": expect_seg,
                "hypothesis": hypothesis,
                "syllables": hyp.get("syllables"),
                "vowel_count": vowel_count_en(word),
                "verify": ver,
                "ok": ok,
            }
        )
    total = len(cues)
    return {
        "schema_version": 1,
        "bench": "segment_en_v0",
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / max(1, total), 3),
        "items": rows,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench English segment v0")
    p.add_argument("--cues", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    if not isinstance(cues, list):
        raise SystemExit("cues must be a JSON array")

    report = run_bench(cues)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
