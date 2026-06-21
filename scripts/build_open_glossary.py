#!/usr/bin/env python3
"""Build a clean single-word RU<->EN glossary from an open dictionary.

Source: OpenRussian.org data, redistributed by github.com/Badestrand/russian-dictionary
(nouns/verbs/adjectives CSVs). OpenRussian data is licensed CC BY-SA 4.0 — keep the
attribution if you redistribute the derived list.

Usage:
    python scripts/build_open_glossary.py --out lab/curriculum/en-glossary-ru-open.json
    # optional: --sample 3000 to cap the output (the repo ships a small sample)

Downloads the three CSVs, takes each headword's bare Russian form and the first
single-word English gloss, drops multi-word / non-alphabetic entries, dedupes by
Russian word, and writes a JSON list of [ru, en] pairs that teach_glossary ingests.
This is term-level translation memory — deterministic, auditable, no hallucination.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.request

BASE = "https://raw.githubusercontent.com/Badestrand/russian-dictionary/master"
FILES = ("nouns", "verbs", "adjectives")
RU = re.compile(r"^[а-яё]+$")
EN = re.compile(r"^[a-z]+$")
_LEAD = ("to ", "a ", "an ", "the ")


def first_gloss(raw: str) -> str:
    seg = re.split(r"[,;(/]", (raw or "").strip())[0].strip().lower()
    for lead in _LEAD:
        if seg.startswith(lead):
            seg = seg[len(lead):].strip()
    return seg


def build(sample: int | None) -> list[list[str]]:
    pairs: dict[str, str] = {}
    for name in FILES:
        url = f"{BASE}/{name}.csv"
        with urllib.request.urlopen(url) as resp:  # noqa: S310 (trusted raw GitHub)
            text = resp.read().decode("utf-8")
        for row in csv.DictReader(text.splitlines(), delimiter="\t"):
            ru = (row.get("bare") or "").strip().lower()
            en = first_gloss(row.get("translations_en") or "")
            if not RU.match(ru) or not EN.match(en) or len(ru) < 2 or len(en) < 2:
                continue
            pairs.setdefault(ru, en)
    out = [[ru, en] for ru, en in pairs.items()]
    return out[:sample] if sample else out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=None, help="cap the number of pairs")
    args = ap.parse_args()
    pairs = build(args.sample)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(pairs, fh, ensure_ascii=False)
    print(f"wrote {len(pairs)} RU<->EN pairs to {args.out}")


if __name__ == "__main__":
    main()
