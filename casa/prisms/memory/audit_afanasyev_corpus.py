#!/usr/bin/env python3
"""Audit Afanasyev corpus for OCR / encoding garbage before SSS ingest."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from casa.prisms.memory.text_tokenize import extract_punctuation_unique, extract_words, norm_text

_LATIN_IN_WORD = re.compile(r"[a-zA-Z]")
_OLD_ORPHAN = re.compile(r"[ѣѢіІїЇєЄґҐ]")
_GARBAGE_CHARS = re.compile(r"[\u0000-\u0008\u0b0b\u000e-\u001f\ufffd\u200b\u00ad]")
_HTMLISH = re.compile(r"&(?:[a-z]+|#\d+);|<[^>]+>")
_OCR_GLUE = re.compile(r"[|#]{2,}|_{2,}|\*{2,}")
_DIGIT_ONLY_LINE = re.compile(r"^\d+$")
_PAGE_MARK = re.compile(r"^(стр\.|page\s+\d+|--\s*\d+\s*--)", re.I)


def audit_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = norm_text(raw)
    issues: list[str] = []
    samples: list[str] = []

    if _GARBAGE_CHARS.search(text):
        issues.append("control_or_replacement_char")
        samples.append(_GARBAGE_CHARS.search(text).group(0) if _GARBAGE_CHARS.search(text) else "")
    if "\ufffd" in text:
        issues.append("unicode_replacement")
    if _HTMLISH.search(text):
        issues.append("html_artifact")
    if _OCR_GLUE.search(text):
        issues.append("ocr_glue")

    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if _PAGE_MARK.match(line.strip()):
            issues.append("page_marker")
            if len(samples) < 5:
                samples.append(f"L{i}: {line[:80]}")
        if _LATIN_IN_WORD.search(line) and re.search(r"[а-яё]", line, re.I):
            issues.append("latin_in_cyrillic_line")
            if len(samples) < 5:
                samples.append(f"L{i}: {line[:80]}")
        if _OLD_ORPHAN.search(line):
            issues.append("old_orthography_char")
            if len(samples) < 5:
                samples.append(f"L{i}: {line[:80]}")
        if _DIGIT_ONLY_LINE.match(line.strip()) and len(line.strip()) >= 3:
            issues.append("digit_only_line")

    words = extract_words(text)
    punct = extract_punctuation_unique(text)
    short = len(text.strip()) < 80
    if short:
        issues.append("very_short")

    return {
        "file": path.name,
        "chars": len(text),
        "words_unique": len(set(words)),
        "punct": punct,
        "issues": sorted(set(issues)),
        "samples": samples[:5],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-dir", type=Path, default=Path("lab/text/corpus/afanasyev"))
    p.add_argument("--out", type=Path, default=Path("lab/exp_lexicon_v1/report_afanasyev_audit.json"))
    p.add_argument("--fail-on-issues", action="store_true")
    args = p.parse_args()

    files = sorted(args.corpus_dir.glob("*.txt"))
    rows = [audit_file(fp) for fp in files]
    issue_counts: Counter[str] = Counter()
    flagged = []
    for r in rows:
        for iss in r["issues"]:
            issue_counts[iss] += 1
        bad = [x for x in r["issues"] if x not in ("old_orthography_char",)]
        if bad:
            flagged.append(r)

    report = {
        "corpus_dir": str(args.corpus_dir),
        "files": len(files),
        "flagged_files": len(flagged),
        "issue_counts": dict(issue_counts),
        "punct_corpus_unique": sorted({p for r in rows for p in r["punct"]}),
        "flagged": flagged[:40],
        "clean_enough": len(flagged) == 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "flagged"}, ensure_ascii=False, indent=2))
    if flagged:
        print(f"\nFirst flagged: {flagged[0]['file']} -> {flagged[0]['issues']}")
    if args.fail_on_issues and flagged:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
