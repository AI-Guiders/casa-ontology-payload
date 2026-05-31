#!/usr/bin/env python3
"""Smoke bench: T9 prefix predict on dev English headwords (l2_prefix_candidates).

Boot from ltm/ by default; use --prefer-field-state after ingest --write
(loads field_state without re-importing ltm/, which would drop EN overlay).
Optional --headwords re-runs listen ingest in-process on ltm-only boot.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from casa.prisms.tick.critic import critic_validate
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.ingest_en_lex_dev import ingest_en_lex, read_headwords
from casa.prisms.tick.predictor import l2_prefix_candidates, predict_t9
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.segment import norm_word
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import field_state_path

DEFAULT_SMOKE_CUES: list[dict[str, Any]] = [
    {"id": "co_cow", "cue": "co", "expect": "cow"},
    {"id": "cow_full", "cue": "cow", "expect": "cow"},
    {"id": "mot_mother", "cue": "mot", "expect": "mother"},
    {"id": "mo_ambiguous", "cue": "mo", "expect_in": ["mom", "mother", "moon"]},
    {"id": "mom_full", "cue": "mom", "expect": "mom"},
    {"id": "ca_cat", "cue": "ca", "expect": "cat"},
    {"id": "do_dog", "cue": "do", "expect": "dog"},
    {"id": "hou_house", "cue": "hou", "expect": "house"},
    {"id": "wat_water", "cue": "wat", "expect": "water"},
    {"id": "wat_full", "cue": "water", "expect": "water"},
    {"id": "mot_full", "cue": "mother", "expect": "mother"},
    {"id": "ap_apple", "cue": "ap", "expect": "apple"},
]


def run_smoke(
    state: dict,
    cues: list[dict[str, Any]],
    *,
    top_k: int = 8,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passed = 0
    for item in cues:
        cue = norm_word(str(item.get("cue") or ""))
        pred = predict_t9(state, cue, top_k=top_k)
        ranked = l2_prefix_candidates(state, cue, top_k=top_k)
        crit = critic_validate(
            pred,
            expect=str(item["expect"]) if item.get("expect") is not None else None,
            expect_in=[str(x) for x in item.get("expect_in") or []] or None,
        )
        ok = crit["verdict"] in ("pass", "provisional") and crit["checks"][0].get("pass")
        if ok:
            passed += 1
        rows.append(
            {
                "id": item.get("id"),
                "cue": cue,
                "expect": item.get("expect"),
                "expect_in": item.get("expect_in"),
                "hypothesis": pred.get("hypothesis"),
                "anchors": [a.get("word") for a in pred.get("anchors") or []][:top_k],
                "ranked": [w for w, _ in ranked],
                "verdict": crit["verdict"],
                "ok": ok,
            }
        )
    total = len(cues)
    return {
        "schema_version": 1,
        "bench": "en_t9_smoke",
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / max(1, total), 4),
        "items": rows,
    }


def boot_for_smoke(
    store_dir: Path,
    *,
    prefer_field_state: bool,
) -> dict[str, Any]:
    """Load store for EN smoke: field_state alone, or ltm-only (+ optional ingest)."""
    store_dir = store_dir.resolve()
    fs = field_state_path(store_dir)
    if prefer_field_state and fs.is_file():
        # Do not call boot_store here: import_pack would replace L2 shards and drop EN overlay.
        state = ensure_prisms(load_field_state(fs))
        return {"source": "field_state", "state": state, "l2_shard_count": None}
    boot = boot_store(store_dir, prefer_field_state=False)
    return {
        "source": boot.get("source"),
        "state": boot["state"],
        "l2_shard_count": boot.get("l2_shard_count"),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="EN T9 prefix smoke bench (dev lexicon)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cues", type=Path, default=None, help="JSON array of {cue, expect|expect_in}")
    p.add_argument("--headwords", type=Path, default=None, help="Re-ingest EN words before bench")
    p.add_argument("--prefer-field-state", action="store_true", help="Load field_state.json if present")
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = DEFAULT_SMOKE_CUES
    if args.cues:
        cues = json.loads(args.cues.read_text(encoding="utf-8"))

    boot = boot_for_smoke(args.store_dir, prefer_field_state=args.prefer_field_state)
    state = boot["state"]
    ingest_rep: dict[str, Any] | None = None
    if args.headwords:
        words = read_headwords(args.headwords)
        ingest_rep = ingest_en_lex(state, words)

    report = run_smoke(state, cues, top_k=args.top_k)
    report["boot"] = {"source": boot.get("source"), "vocab_shards": boot.get("l2_shard_count")}
    if ingest_rep:
        report["ingest"] = ingest_rep
    report["passed_all"] = report["passed"] == report["total"]

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(
        f"\nSUMMARY: en_t9_smoke {report['passed']}/{report['total']} "
        f"({report['pass_rate']:.1%}) boot={boot.get('source')}",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["passed_all"] else 1)


if __name__ == "__main__":
    main()
