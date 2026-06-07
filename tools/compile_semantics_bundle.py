#!/usr/bin/env python3
"""Compile frames.jsonl → kb-lang-ru-lexicon-semantics bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_FRAMES = _REPO / "lessons/lang-ru-lexicon-semantics/frames.jsonl"
_DEFAULT_OUT = _REPO / "agents/von-neumann/bundles/kb-lang-ru-lexicon-semantics-v1.bundle.json"


def _load_frames(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def compile_bundle(frames_path: Path, out_path: Path) -> dict:
    frames = _load_frames(frames_path)
    if out_path.is_file():
        bundle = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        bundle = {
            "schema_version": 1,
            "bundle_id": "kb-lang-ru-lexicon-semantics-v1",
            "title": "RU lexicon semantics — meaning frames (ADR-0053)",
            "doc": "lessons/lang-ru-lexicon-semantics/README.md",
            "claims": [],
        }
    by_id = {str(c.get("concept_id") or ""): c for c in bundle.get("claims") or [] if c.get("concept_id")}
    for row in frames:
        cid = str(row.get("concept_id") or "")
        if not cid:
            continue
        by_id[cid] = row
    bundle["claims"] = list(by_id.values())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"out": str(out_path), "claims": len(bundle["claims"]), "frames_in": len(frames)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frames", type=Path, default=_DEFAULT_FRAMES)
    p.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = p.parse_args()
    summary = compile_bundle(args.frames, args.out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
