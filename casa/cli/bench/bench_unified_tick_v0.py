#!/usr/bin/env python3
"""Bench unified macro-turn: script → T9 → ortho/hub."""

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
from entity_hub_ingest_v0 import ingest_entity_hub  # type: ignore
from grapheme_ingest_v0 import bootstrap_linked_graphemes  # type: ignore
from ortho_field_v0 import imprint_capitalize_bootstrap  # type: ignore
from unified_tick_v0 import simulate_unified_type, unified_tick  # type: ignore
from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_GENERAL_V0, agent_store_dir  # type: ignore


def evaluate_item(state: dict, item: dict, *, top_k: int) -> dict[str, Any]:
    mode = str(item.get("mode") or "type")
    if mode == "type":
        sim = simulate_unified_type(
            state,
            str(item.get("word") or ""),
            expect_lang=str(item.get("expect_lang") or ""),
            with_ortho=bool(item.get("with_ortho")),
            with_hub=bool(item.get("with_hub")),
            top_k=top_k,
        )
        hub_ok = True
        if item.get("with_hub") and sim.get("passed"):
            last = sim["trace"][-1]
            hub = last.get("hub") or {}
            neighbors = [n.get("concept_id") for n in hub.get("neighbors") or []]
            word = str(item.get("word") or "")
            if word == "cow":
                hub_ok = any("корова" in str(n) for n in neighbors) or any("entity.cow" in str(n) for n in neighbors)
            elif word == "мама":
                hub_ok = any("mother" in str(n) for n in neighbors) or any("entity" in str(n) for n in neighbors)
        ok = bool(sim.get("passed")) and hub_ok
        return {"id": item.get("id"), "mode": mode, "ok": ok, "sim": sim, "hub_ok": hub_ok}

    steps = list(item.get("steps") or [])
    trace: list[dict[str, Any]] = []
    all_ok = True
    for step in steps:
        visual = str(step.get("visual") or "")
        commitment = step.get("expect_commitment")
        if commitment == "ambiguous":
            tick = unified_tick(
                state,
                visual,
                expect_en_in=step.get("expect_en_in"),
                expect_ru_in=step.get("expect_ru_in"),
                expect_preview_in=step.get("expect_preview_in"),
                expect_preview_en_any=step.get("expect_preview_en_any"),
                expect_preview_ru_any=step.get("expect_preview_ru_any"),
                top_k=top_k,
            )
            amb_ok = tick.get("commitment") == "ambiguous" and tick.get("verdict") == "pass"
            tick["step_ok"] = amb_ok
            all_ok = all_ok and amb_ok
        else:
            tick = unified_tick(
                state,
                visual,
                expect_lang=step.get("expect_lang"),
                expect_word=step.get("expect_word"),
                with_hub=bool(step.get("with_hub")),
                top_k=top_k,
            )
            all_ok = all_ok and tick["verdict"] == "pass"
        tick["step_id"] = step.get("id")
        trace.append(tick)
    return {"id": item.get("id"), "mode": "steps", "ok": all_ok, "trace": trace}


def run_bench(state: dict, items: list[dict], *, top_k: int = 8) -> dict[str, Any]:
    rows = [evaluate_item(state, item, top_k=top_k) for item in items]
    passed = sum(1 for r in rows if r.get("ok"))
    total = len(rows)
    return {
        "schema_version": 1,
        "bench": "unified_tick_v0",
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "items": rows,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench unified script→T9→ortho pipeline")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_GENERAL_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--bundle",
        type=Path,
        default=root / "lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json",
    )
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/unified_tick_cues.v1.json",
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    items = json.loads(args.cues.read_text(encoding="utf-8"))
    headwords = read_headwords(args.headwords)

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    state = boot["state"]
    bootstrap_rep = bootstrap_linked_graphemes(state, en_words=headwords)
    hub_rep = ingest_entity_hub(state, json.loads(args.bundle.read_text(encoding="utf-8")))
    ortho_rep = imprint_capitalize_bootstrap(state)
    boot_ms = round((time.perf_counter() - t0) * 1000)

    report = run_bench(state, items, top_k=args.top_k)
    report["boot_ms"] = boot_ms
    report["bootstrap"] = bootstrap_rep
    report["hub"] = hub_rep
    report["ortho_bootstrap"] = ortho_rep
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
