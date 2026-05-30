#!/usr/bin/env python3
"""Bench text ingest: words and punctuation on field after stream listen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_cylinders  # type: ignore
from sss_text_tokenize_v0 import extract_punctuation_unique, extract_words, norm_text  # type: ignore
from sss_vocab_v0 import punct_votes_from_field, word_votes_from_field  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--text", type=Path, required=True)
    p.add_argument("--min-votes", type=int, default=1)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    text = norm_text(args.text.read_text(encoding="utf-8"))
    expect_w = extract_words(text, min_len=1)
    expect_p = extract_punctuation_unique(text)
    state = ensure_cylinders(load_field_state(args.store_dir / "field_state.json"))
    wvotes = word_votes_from_field(state)
    pvotes = punct_votes_from_field(state)

    hits_w = [w for w in expect_w if wvotes.get(w, 0) >= args.min_votes]
    hits_p = [m for m in expect_p if pvotes.get(m, 0) >= args.min_votes]
    report = {
        "words_in_text": len(expect_w),
        "words_on_field": len(hits_w),
        "word_coverage": round(len(hits_w) / len(expect_w), 4) if expect_w else 0.0,
        "punct_in_text": len(expect_p),
        "punct_on_field": len(hits_p),
        "punct_coverage": round(len(hits_p) / len(expect_p), 4) if expect_p else 1.0,
        "punct_missing": [m for m in expect_p if pvotes.get(m, 0) < args.min_votes],
        "missing_words": [w for w in expect_w if wvotes.get(w, 0) < args.min_votes][:24],
        "sample_p_votes": {m: pvotes[m] for m in hits_p[:12]},
        "sample_w_votes": {w: wvotes[w] for w in hits_w[:12]},
        "ingest_ok": len(hits_w) >= max(1, int(len(expect_w) * 0.7))
        and (not expect_p or len(hits_p) >= max(1, int(len(expect_p) * 0.7))),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
