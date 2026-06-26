#!/usr/bin/env python3
"""ADR-0081: reject new partner-script clause_* on ru.dialog.* hubs in bundles.

Run: python tools/validate_dialog_script_slots.py [bundle.json ...]
Exit 0 = pass, 1 = violations.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = REPO / "agents/von-neumann/bundles/kb-lang-ru-grammar-dialog-v1.bundle.json"

_CLAUSE_KEY = re.compile(r"^clause_\d+$|^sentence_\d+$")
_SCRIPT_KEYS = {"phrase", "utterance", "reply", "answer"}
_FALSE_TRIPLE_KEYS = {"hedge", "predicate", "scope", "limit"}
_ALLOW_SLOT_KEYS = {
    # L0 morpheme / grapheme material
    "grapheme",
    "morpheme",
    "prefix",
    "root",
    "stem",
    "suffix",
    "ending",
    # L1 word material
    "lemma",
    "surface",
    "word",
    "form",
    "part_of_speech",
    # Minimal formula exchange
    "stimulus",
    "response",
    "response_informal",
    # L2 phrase material
    "head",
    "dependent",
    "modifier",
    "agreement",
    # L3 clause material
    "subject",
    "predicate",
    "role",
    "case",
    "gender",
    "number",
    "referent",
    "stance",
    "predicate_lemma",
    "object_lemma",
    "linker",
    "tone_register",
    "limit_kind",
    # L4-L5 discourse/text material
    "thesis",
    "intent",
    "outline",
    "outline_1",
    "outline_2",
    "outline_3",
    # Situation metadata
    "situation",
}


def _looks_partner_facing(text: str) -> bool:
    body = re.sub(r"\s+", " ", str(text or "").strip())
    if not body:
        return False
    return len(body.split()) >= 4 or len(body) >= 28 or bool(re.search(r"[.!?]$", body))


def _violations(bundle_path: Path) -> list[str]:
    raw = json.loads(bundle_path.read_text(encoding="utf-8"))
    out: list[str] = []
    for claim in raw.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        cid = str(claim.get("concept_id") or "")
        if not cid.startswith("ru.dialog."):
            continue
        slots = claim.get("slots") or {}
        if not isinstance(slots, dict):
            continue
        false_triple = {k for k in _FALSE_TRIPLE_KEYS if str(slots.get(k) or "").strip()}
        if len(false_triple) >= 2:
            joined = " ".join(str(slots.get(k) or "").strip() for k in ("hedge", "predicate", "scope", "limit"))
            out.append(f"{bundle_path.name}: {cid} hedge/predicate/scope false-slot script: {joined.strip()}")
        for key, val in slots.items():
            skey = str(key)
            text = str(val or "").strip()
            if not text:
                continue
            if _CLAUSE_KEY.match(skey) and _looks_partner_facing(text):
                out.append(f"{bundle_path.name}: {cid} slot {key} looks like utterance script")
            elif skey in _SCRIPT_KEYS and _looks_partner_facing(text):
                out.append(f"{bundle_path.name}: {cid} slot {key} looks like partner-facing phrase script")
            elif skey not in _ALLOW_SLOT_KEYS:
                out.append(f"{bundle_path.name}: {cid} slot {key} is not ADR-0081 lexical material")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-0081 bundle script-slot gate")
    parser.add_argument("bundles", nargs="*", help="Bundle JSON paths (default: dialog grammar bundle)")
    args = parser.parse_args(argv)

    paths = [Path(p) if Path(p).is_absolute() else REPO / p for p in args.bundles] if args.bundles else [DEFAULT_BUNDLE]
    hits: list[str] = []
    for path in paths:
        hits.extend(_violations(path))

    if not hits:
        print("PASS: validate_dialog_script_slots")
        return 0
    for line in hits:
        print(line)
    print(f"FAIL: validate_dialog_script_slots — {len(hits)} violation(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
