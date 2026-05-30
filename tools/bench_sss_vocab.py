#!/usr/bin/env python3
"""Bench vocabulary recall after read-aloud (field W: votes, scene links)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore
from sss_vocab_v0 import recall_words_for_scene, word_votes_from_field  # type: ignore


def eval_recall(state: dict, probes: list[dict]) -> list[dict]:
    rows = []
    wvotes = word_votes_from_field(state)
    for p in probes:
        sid = str(p.get("scene_id") or "")
        expect = str(p.get("word") or "").strip().lower()
        ranked = recall_words_for_scene(state, sid)
        top = ranked[0]["word"] if ranked else ""
        hit = any(r["word"] == expect for r in ranked[:3])
        rows.append(
            {
                "scene_id": sid,
                "expect": expect,
                "top": top,
                "hit_top3": hit,
                "w_votes": wvotes.get(expect, 0),
                "ranked": ranked[:5],
            }
        )
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--probes", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    probes_raw = json.loads(args.probes.read_text(encoding="utf-8"))
    probes = probes_raw if isinstance(probes_raw, list) else probes_raw.get("probes") or []

    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))
    rows = eval_recall(state, probes)
    passed = sum(1 for r in rows if r["hit_top3"])
    report = {
        "passed": passed,
        "total": len(rows),
        "pass_rate": round(passed / len(rows), 4) if rows else 0.0,
        "word_votes": word_votes_from_field(state),
        "items": rows,
        "vocab_ok": passed >= max(1, int(len(rows) * 0.6)),
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
