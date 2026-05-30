#!/usr/bin/env python3
"""Corpus-wide word + punctuation coverage on field (post batch ingest)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore
from sss_text_tokenize_v0 import extract_punctuation_unique, extract_words, norm_text  # type: ignore
from sss_vocab_v0 import punct_votes_from_field, word_votes_from_field  # type: ignore


def scan_corpus(corpus_dir: Path, *, min_word_len: int = 1) -> tuple[set[str], set[str], int]:
    words: set[str] = set()
    punct: set[str] = set()
    files = 0
    for fp in sorted(corpus_dir.glob("*.txt")):
        text = norm_text(fp.read_text(encoding="utf-8"))
        if not text.strip():
            continue
        words.update(extract_words(text, min_len=min_word_len))
        punct.update(extract_punctuation_unique(text))
        files += 1
    return words, punct, files


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--min-votes", type=int, default=1)
    p.add_argument("--min-word-len", type=int, default=1)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    t0 = time.perf_counter()
    expect_w, expect_p, tale_files = scan_corpus(args.corpus_dir, min_word_len=args.min_word_len)
    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))
    wvotes = word_votes_from_field(state)
    pvotes = punct_votes_from_field(state)

    hits_w = [w for w in expect_w if wvotes.get(w, 0) >= args.min_votes]
    hits_p = [m for m in expect_p if pvotes.get(m, 0) >= args.min_votes]
    missing_w = sorted(w for w in expect_w if wvotes.get(w, 0) < args.min_votes)
    missing_p = sorted(m for m in expect_p if pvotes.get(m, 0) < args.min_votes)

    word_cov = round(len(hits_w) / len(expect_w), 4) if expect_w else 0.0
    punct_cov = round(len(hits_p) / len(expect_p), 4) if expect_p else 1.0
    report = {
        "store": str(args.store_dir),
        "corpus_dir": str(args.corpus_dir),
        "field_version": state.get("field_version"),
        "tale_files": tale_files,
        "words_unique_corpus": len(expect_w),
        "words_on_field": len(hits_w),
        "word_coverage": word_cov,
        "punct_unique_corpus": len(expect_p),
        "punct_on_field": len(hits_p),
        "punct_coverage": punct_cov,
        "punct_missing": missing_p,
        "missing_words_sample": missing_w[:32],
        "missing_words_count": len(missing_w),
        "top_word_votes": dict(sorted(wvotes.items(), key=lambda kv: -kv[1])[:16]),
        "punct_votes": {m: pvotes[m] for m in sorted(hits_p)},
        "corpus_ok": word_cov >= 0.95 and punct_cov >= 0.95,
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
