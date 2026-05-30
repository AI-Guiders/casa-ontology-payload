#!/usr/bin/env python3
"""Bench: derive Lower/inverse only after ortho surprise (ADR-0003 §7)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from boot_linked_stores_v0 import boot_linked_stores  # type: ignore
from en_lexicon_v0 import read_headwords  # type: ignore
from grapheme_ingest_v0 import bootstrap_linked_graphemes  # type: ignore
from ortho_field_v0 import (  # type: ignore
    PROC_LOWER,
    PROC_LOWER_WORD,
    PROC_UPPER,
    apply_from_field,
    has_inverse_pair,
    has_process,
    imprint_capitalize_bootstrap,
    l3_process_ids,
)
from ortho_tick_v0 import simulate_ortho_plain_surprise  # type: ignore
from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir  # type: ignore


def run_lab(state: dict, *, word: str = "мама") -> dict[str, Any]:
    phases: list[dict[str, Any]] = []
    passed = 0
    total = 0

    def check(name: str, ok: bool, detail: dict) -> None:
        nonlocal passed, total
        total += 1
        if ok:
            passed += 1
        phases.append({"phase": name, "ok": ok, **detail})

    # Phase 0: bootstrap capitalize only — no Lower
    boot_rep = imprint_capitalize_bootstrap(state)
    procs = l3_process_ids(state)
    check(
        "bootstrap_no_lower",
        PROC_LOWER not in procs and PROC_LOWER_WORD not in procs,
        {"processes": sorted(procs), "bootstrap": boot_rep},
    )

    # Phase 1–4: hot-path (predict → act → critic → extract); no manual extract
    hot = simulate_ortho_plain_surprise(state, word=word, context="plain")
    t_surprise = hot["ticks"][0]
    t_undo = hot["ticks"][1]

    upper_surface = t_surprise["act"].get("surface")
    check(
        "upper_compose",
        upper_surface == "МАМА",
        {"word": word, "surface": upper_surface, "expect": "МАМА", "tick": "surprise"},
    )
    check(
        "surprise_plain_not_upper",
        hot["surprise_ok"],
        {"critic": t_surprise["critic"], "extract": t_surprise.get("extract")},
    )
    extract_rep = t_surprise.get("extract") or {}
    procs_after = l3_process_ids(state)
    check(
        "extract_lower_emerged",
        has_process(state, PROC_LOWER)
        and has_inverse_pair(state, "proc.grapheme.capitalize", PROC_LOWER),
        {"extract": extract_rep, "processes": sorted(procs_after), "hot_path": True},
    )
    check(
        "extract_lower_word_fold",
        has_process(state, PROC_LOWER_WORD),
        {"has_lower_word": has_process(state, PROC_LOWER_WORD)},
    )
    undone = t_undo["act"].get("surface")
    undo_crit = t_undo.get("undo_critic") or {}
    check(
        "lower_undo_upper",
        hot["undo_ok"],
        {"undone": undone, "critic": undo_crit, "tick": "undo"},
    )

    # Phase 5: EN sanity on linked field
    en_word = "mother"
    en_upper = apply_from_field(state, en_word, PROC_UPPER)
    en_lower = apply_from_field(state, en_upper or "", PROC_LOWER_WORD) if en_upper else None
    check(
        "en_roundtrip",
        en_upper == "MOTHER" and en_lower == en_word,
        {"word": en_word, "upper": en_upper, "lower": en_lower},
    )

    return {
        "schema_version": 1,
        "bench": "ortho_inverse_v0",
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "phases": phases,
        "word_ru": word,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench ortho inverse extract after surprise")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_LEXICON_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument("--word", default="мама")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    headwords = read_headwords(args.headwords)
    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    state = boot["state"]
    bootstrap_rep = bootstrap_linked_graphemes(state, en_words=headwords)
    boot_ms = round((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    report = run_lab(state, word=args.word)
    lab_ms = round((time.perf_counter() - t1) * 1000)

    report["boot_ms"] = boot_ms
    report["lab_ms"] = lab_ms
    report["bootstrap"] = bootstrap_rep
    report["boot"] = {k: v for k, v in boot.items() if k != "state"}

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)

    print(
        f"\nSUMMARY: {report['passed']}/{report['total']} "
        f"boot={boot_ms}ms lab={lab_ms}ms",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
