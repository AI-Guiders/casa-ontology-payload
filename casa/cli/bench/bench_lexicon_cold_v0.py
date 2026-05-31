#!/usr/bin/env python3
"""Bench lexicon_miss → cold ingest → T9 predict again (offline dictionary v0)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.lexicon_cold_ingest_v0 import (
    LEXICON_MISS_LOG,
    log_cold_ingest,
    process_lexicon_misses,
)
from casa.prisms.tick.predictor_v0 import l2_has_word, predict_t9
from casa.prisms.shared.store_boot_v0 import boot_store


def run_bench(
    state: dict,
    cues: list[dict],
    *,
    headwords_path: Path | None,
    store_dir: Path | None = None,
    write_log: bool = True,
) -> dict:
    rows: list[dict] = []
    passed = 0

    for item in cues:
        word = str(item.get("word") or item.get("expect") or "")
        prefix = str(item.get("prefix_cue") or item.get("cue") or word[: max(3, len(word) // 2)])
        expect = str(item.get("expect") or word)

        before = predict_t9(state, prefix)
        miss = before.get("lexicon_miss") or {}
        miss_ok = bool(miss.get("miss")) and not l2_has_word(state, word)

        ingest_report: dict = {}
        if miss_ok:
            misses = [{"prefix": prefix, "word": word, "reason": miss.get("reason")}]
            ingest_report = process_lexicon_misses(
                state,
                misses,
                store_dir=store_dir,
                headwords_path=headwords_path,
            )
            if store_dir and write_log:
                log_cold_ingest(store_dir, misses=misses, ingest_report=ingest_report)

        after = predict_t9(state, prefix)
        anchor_words = [a.get("word") for a in after.get("anchors") or []]
        has_word = l2_has_word(state, word)
        expect_ok = expect in anchor_words or (after.get("focus") or {}).get("word") == expect

        ok = miss_ok and has_word and expect_ok and int(ingest_report.get("words_ingested") or 0) >= 1
        if ok:
            passed += 1

        rows.append(
            {
                "id": item.get("id"),
                "word": word,
                "prefix_cue": prefix,
                "expect": expect,
                "before_miss": miss,
                "miss_detected": miss_ok,
                "ingest": ingest_report,
                "after_anchors": anchor_words[:6],
                "word_on_l2": has_word,
                "expect_in_anchors": expect_ok,
                "ok": ok,
            }
        )

    total = len(cues)
    return {
        "schema_version": 1,
        "bench": "lexicon_cold_v0",
        "log_file": LEXICON_MISS_LOG if store_dir else None,
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / max(1, total), 3),
        "items": rows,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench lexicon cold ingest v0")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cues", type=Path, required=True)
    p.add_argument("--headwords", type=Path, required=True, help="Offline dictionary for lookup")
    p.add_argument("--boot-ltm-only", action="store_true", default=False)
    p.add_argument("--no-log", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    if not isinstance(cues, list):
        raise SystemExit("cues must be a JSON array")

    boot = boot_store(args.store_dir, prefer_field_state=not args.boot_ltm_only)
    report = run_bench(
        boot["state"],
        cues,
        headwords_path=args.headwords,
        store_dir=args.store_dir.resolve(),
        write_log=not args.no_log,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
