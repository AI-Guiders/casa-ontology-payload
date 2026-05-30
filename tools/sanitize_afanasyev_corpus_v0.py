#!/usr/bin/env python3
"""In-place cleanup of Afanasyev per-tale txt — remove OCR/editorial garbage."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from sss_text_tokenize_v0 import norm_text  # type: ignore

_REPLACEMENT = "\ufffd"
_SIC = re.compile(r"\(\s*sic\s*\)|\[\s*sic\s*\]", re.IGNORECASE)
_EDITORIAL = re.compile(
    r"\(\?\)|\(\s*в\s+оригинале[^)]*\)|\(\s*т\.?\s*е\.?\s*[^)]*\)",
    re.IGNORECASE,
)
_CROSSREF_PARENS = re.compile(
    r"\([^)]*(?:продолжается|конец тот же|напечатанн)[^)]*no\s+\d+[^)]*\)\.?",
    re.IGNORECASE,
)
_CROSSREF_LINE = re.compile(
    r"^\(.*(?:продолжается|конец тот же|напечатанн).*no\s+\d+.*\)\.?\s*$",
    re.IGNORECASE,
)
_CTRL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u200b\u00ad]")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
_FOOTNOTE_ONLY = re.compile(r"^\[\d+\]\s*$")


def sanitize_text(text: str) -> tuple[str, list[str]]:
    fixes: list[str] = []
    t = norm_text(text)
    if _REPLACEMENT in t or "�" in t:
        t = t.replace(_REPLACEMENT, "").replace("�", "")
        fixes.append("dropped_replacement_char")
    if _SIC.search(t):
        t = _SIC.sub("", t)
        fixes.append("removed_sic")
    if _EDITORIAL.search(t):
        t = _EDITORIAL.sub("", t)
        fixes.append("removed_editorial")
    if _CROSSREF_PARENS.search(t):
        t = _CROSSREF_PARENS.sub("", t)
        fixes.append("removed_crossref")
    if _CTRL.search(t):
        t = _CTRL.sub("", t)
        fixes.append("removed_control_chars")

    lines: list[str] = []
    for line in t.splitlines():
        ln = _MULTI_SPACE.sub(" ", line).strip()
        if not ln:
            lines.append("")
            continue
        if _FOOTNOTE_ONLY.match(ln):
            fixes.append("dropped_footnote_line")
            continue
        if _CROSSREF_LINE.match(ln):
            fixes.append("dropped_crossref_line")
            continue
        lines.append(ln)

    t = "\n".join(lines)
    t = _MULTI_NL.sub("\n\n", t).strip()
    if t and not t.endswith("\n"):
        t += "\n"
    return t, fixes


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-dir", type=Path, default=Path("examples/text/corpus/afanasyev"))
    p.add_argument("--out", type=Path, default=Path("examples/exp_sss_v1/report_afanasyev_sanitize.json"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    changed = 0
    fix_counts: dict[str, int] = {}
    rows: list[dict] = []
    for fp in sorted(args.corpus_dir.glob("*.txt")):
        before = fp.read_text(encoding="utf-8", errors="replace")
        after, fixes = sanitize_text(before)
        if fixes:
            for f in fixes:
                fix_counts[f] = fix_counts.get(f, 0) + 1
        if after != before:
            changed += 1
            if not args.dry_run:
                fp.write_text(after, encoding="utf-8")
            rows.append({"file": fp.name, "fixes": fixes})

    report = {
        "corpus_dir": str(args.corpus_dir),
        "files": len(list(args.corpus_dir.glob("*.txt"))),
        "changed": changed,
        "fix_counts": fix_counts,
        "dry_run": args.dry_run,
        "samples": rows[:12],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
