#!/usr/bin/env python3
"""Bench letter-by-letter T9 predict_tick loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from predict_tick_v0 import simulate_t9_type  # type: ignore
from store_boot_v0 import boot_store  # type: ignore


def run_bench(state: dict, cues: list[dict], *, top_k: int = 8) -> dict:
    rows: list[dict] = []
    passed = 0
    for item in cues:
        word = str(item.get("word") or item.get("cue") or "")
        sim = simulate_t9_type(state, word, top_k=top_k)
        ok = bool(sim.get("passed"))
        if ok:
            passed += 1
        trace = sim.get("trace") or []
        rows.append(
            {
                "id": item.get("id"),
                "word": word,
                "ticks": sim.get("ticks"),
                "passed": ok,
                "final_focus": sim.get("final_focus"),
                "steps": [
                    {
                        "cue": t.get("cue"),
                        "anchors": [a.get("word") for a in (t.get("predict") or {}).get("anchors") or []][:6],
                        "focus": t.get("focus"),
                        "verdict": t.get("verdict"),
                        "step_ok": t.get("step_ok"),
                    }
                    for t in trace
                ],
            }
        )
    total = len(cues)
    return {
        "schema_version": 1,
        "bench": "predict_tick_v0",
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / max(1, total), 3),
        "items": rows,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench T9 letter-by-letter predict_tick")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cues", type=Path, required=True)
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    boot = boot_store(args.store_dir, prefer_field_state=False)
    report = run_bench(boot["state"], cues, top_k=args.top_k)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
