#!/usr/bin/env python3
"""Bench letter-by-letter script/lang detection from L0 basins."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from boot_linked_stores_v0 import boot_linked_stores  # type: ignore
from en_lexicon_v0 import read_headwords  # type: ignore
from grapheme_ingest_v0 import bootstrap_linked_graphemes  # type: ignore
from script_tick_v0 import script_tick, simulate_script_prefix  # type: ignore
from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir  # type: ignore


def evaluate_cue(state: dict, item: dict) -> dict[str, Any]:
    cue = str(item.get("cue") or "")
    expect_lang = str(item.get("expect_lang") or "")
    expect_script = item.get("expect_script")
    expect_script_s = str(expect_script) if expect_script else None
    by_letter = bool(item.get("letter_by_letter"))

    if by_letter and len(cue) > 1:
        sim = simulate_script_prefix(
            state,
            cue,
            expect_lang=expect_lang,
            expect_script=expect_script_s,
        )
        ok = sim.get("passed", False)
        first = sim.get("first_char_lang")
        detail = {"mode": "letter_by_letter", "sim": sim}
    else:
        tick = script_tick(
            state,
            cue,
            expect_lang=expect_lang,
            expect_script=expect_script_s,
        )
        ok = tick["verdict"] == "pass"
        first = tick.get("hypothesis_lang")
        detail = {"mode": "single", "tick": tick}

    return {
        "id": item.get("id"),
        "cue": cue,
        "expect_lang": expect_lang,
        "expect_script": expect_script_s,
        "first_char_or_tick_lang": first,
        "ok": ok,
        **detail,
    }


def run_bench(state: dict, cues: list[dict]) -> dict[str, Any]:
    rows = [evaluate_cue(state, item) for item in cues]
    passed = sum(1 for r in rows if r.get("ok"))
    total = len(rows)
    return {
        "schema_version": 1,
        "bench": "script_detect_v0",
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "items": rows,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench L0 letter-by-letter script/lang detect")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_LEXICON_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/script_detect_cues.v1.json",
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    headwords = read_headwords(args.headwords)

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    state = boot["state"]
    bootstrap_rep = bootstrap_linked_graphemes(state, en_words=headwords)
    boot_ms = round((time.perf_counter() - t0) * 1000)

    report = run_bench(state, cues)
    report["boot_ms"] = boot_ms
    report["bootstrap"] = bootstrap_rep
    report["boot"] = {k: v for k, v in boot.items() if k != "state"}

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)

    print(
        f"\nSUMMARY: {report['passed']}/{report['total']} boot={boot_ms}ms",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
