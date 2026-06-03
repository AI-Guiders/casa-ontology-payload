#!/usr/bin/env python3
"""Переименовать legacy concept_id в field store (без переучивания)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_CURRICULUM = _REPO / "lab" / "visual-curriculum"
for entry in (_REPO, _CURRICULUM):
    s = str(entry)
    if s not in sys.path:
        sys.path.insert(0, s)

from casa.prisms.memory.meta_concept_aliases import LEX_CONCEPT_RENAMES
from curriculum_lab import CurriculumLabSession


def _replace_str(s: str, renames: dict[str, str]) -> tuple[str, int]:
    out = s
    n = 0
    for old, new in sorted(renames.items(), key=lambda kv: -len(kv[0])):
        if old in out:
            c = out.count(old)
            out = out.replace(old, new)
            n += c
    return out, n


def _walk(obj: Any, renames: dict[str, str]) -> tuple[Any, int]:
    if isinstance(obj, str):
        return _replace_str(obj, renames)
    if isinstance(obj, list):
        total = 0
        out: list[Any] = []
        for item in obj:
            new_item, c = _walk(item, renames)
            out.append(new_item)
            total += c
        return out, total
    if isinstance(obj, dict):
        total = 0
        out: dict[Any, Any] = {}
        for k, v in obj.items():
            nk, c1 = _walk(k, renames) if isinstance(k, str) else (k, 0)
            nv, c2 = _walk(v, renames)
            out[nk] = nv
            total += c1 + c2
        return out, total
    return obj, 0


def main() -> None:
    p = argparse.ArgumentParser(description="Rename legacy lang.word.* meta ids in agent store")
    p.add_argument("--store", type=str, default="von-neumann")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    lab = CurriculumLabSession(store_id=args.store, generated_subdir="micro-literacy")
    lab.load(phase_extra={"dry_run": args.dry_run})
    new_state, replacements = _walk(lab.state, LEX_CONCEPT_RENAMES)
    lab._state = new_state
    lab.log(
        {
            "store": str(lab.store_dir),
            "replacements": replacements,
            "renames": LEX_CONCEPT_RENAMES,
            "dry_run": args.dry_run,
        }
    )
    if not args.dry_run and replacements > 0:
        lab.save()


if __name__ == "__main__":
    main()
