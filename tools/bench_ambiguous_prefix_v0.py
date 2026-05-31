#!/usr/bin/env python3
"""Bench: ambiguous visual prefix — merged BiT9 preview (freq RU + EN homoglyph)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from ambiguous_prefix_v0 import ambiguous_tick, simulate_ambiguous_track  # type: ignore
from boot_linked_stores_v0 import boot_linked_stores  # type: ignore
from en_lexicon_v0 import read_headwords  # type: ignore
from grapheme_ingest_v0 import bootstrap_linked_graphemes  # type: ignore
from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_GENERAL_V0, agent_store_dir  # type: ignore


def evaluate_track(state: dict, track: dict, *, top_k: int) -> dict[str, Any]:
    steps = list(track.get("steps") or [])
    if steps:
        sim = simulate_ambiguous_track(state, steps, top_k=top_k)
        return {
            "id": track.get("id"),
            "description": track.get("description"),
            "mode": "track",
            "ok": sim.get("passed"),
            "sim": sim,
        }
    visual = str(track.get("visual") or "")
    tick = ambiguous_tick(
        state,
        visual,
        expect_commitment=track.get("expect_commitment"),
        expect_lang=track.get("expect_lang"),
        expect_en_in=track.get("expect_en_in"),
        expect_ru_in=track.get("expect_ru_in"),
        expect_preview_in=track.get("expect_preview_in"),
        expect_preview_en_any=track.get("expect_preview_en_any"),
        expect_preview_ru_any=track.get("expect_preview_ru_any"),
        top_k=top_k,
    )
    return {"id": track.get("id"), "mode": "single", "ok": tick["verdict"] == "pass", "tick": tick}


def run_bench(state: dict, tracks: list[dict], *, top_k: int = 8) -> dict[str, Any]:
    rows = [evaluate_track(state, t, top_k=top_k) for t in tracks]
    passed = sum(1 for r in rows if r.get("ok"))
    total = len(rows)
    return {
        "schema_version": 1,
        "bench": "ambiguous_prefix_v0",
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "tracks": rows,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench homoglyph ambiguous prefix (merged BiT9 preview)")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_GENERAL_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/ambiguous_prefix_cues.v1.json",
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    tracks = json.loads(args.cues.read_text(encoding="utf-8"))
    headwords = read_headwords(args.headwords)

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    state = boot["state"]
    bootstrap_rep = bootstrap_linked_graphemes(state, en_words=headwords)
    boot_ms = round((time.perf_counter() - t0) * 1000)

    report = run_bench(state, tracks, top_k=args.top_k)
    report["boot_ms"] = boot_ms
    report["bootstrap"] = bootstrap_rep
    report["boot"] = {k: v for k, v in boot.items() if k != "state"}

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    print(f"\nSUMMARY: {report['passed']}/{report['total']} boot={boot_ms}ms", file=sys.stderr)
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
