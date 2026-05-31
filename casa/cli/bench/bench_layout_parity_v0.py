#!/usr/bin/env python3
"""Bench layout-parity BiT9: PhysicalKeyEvent → decode → layout_tick (ADR-0008)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from casa.prisms.memory.boot_linked_stores_v0 import boot_linked_stores
from casa.prisms.memory.en_lexicon_v0 import ingest_en_lex_batch, read_headwords
from casa.prisms.memory.entity_hub_ingest_v0 import ingest_entity_hub
from casa.prisms.memory.grapheme_ingest_v0 import bootstrap_linked_graphemes
from casa.prisms.memory.layout_tick_v0 import layout_tick
from casa.prisms.memory.keyboard_ortho_bridge_v0 import ingest_keyboard_ortho_bridge
from casa.prisms.memory.ortho_field_v0 import imprint_capitalize_bootstrap
from casa.prisms.shared.store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir
from casa.prisms.memory.vk_decode_v0 import decode_branches


def evaluate_item(state: dict, item: dict, *, top_k: int) -> dict[str, Any]:
    events = list(item.get("events") or [])
    decode = decode_branches(events)
    rep = layout_tick(state, events, top_k=top_k)

    ok = True
    checks: list[dict[str, Any]] = []

    exp_layout = item.get("expect_winner_layout")
    if exp_layout:
        c_ok = rep.get("winner_layout") == exp_layout
        checks.append({"name": "winner_layout", "pass": c_ok, "detail": rep.get("winner_layout")})
        ok = ok and c_ok

    exp_grapheme = item.get("expect_grapheme")
    if exp_grapheme:
        g_ok = decode.get(exp_layout or rep.get("winner_layout") or "") == exp_grapheme
        checks.append({"name": "expect_grapheme", "pass": g_ok, "detail": decode})
        ok = ok and g_ok

    exp_segment = item.get("expect_segment")
    if exp_segment:
        s_ok = rep.get("segment") == exp_segment
        checks.append({"name": "segment", "pass": s_ok, "detail": rep.get("segment")})
        ok = ok and s_ok

    if exp_en := item.get("expect_en_in"):
        found = set(exp_en) & set(rep.get("winner_anchors_en") or [])
        e_ok = len(found) >= 1
        checks.append({"name": "en_in", "pass": e_ok, "detail": sorted(found)})
        ok = ok and e_ok

    if exp_ru := item.get("expect_ru_in"):
        found = set(exp_ru) & set(rep.get("winner_anchors_ru") or [])
        r_ok = len(found) >= 1
        checks.append({"name": "ru_in", "pass": r_ok, "detail": sorted(found)})
        ok = ok and r_ok

    return {
        "id": item.get("id"),
        "ok": ok,
        "checks": checks,
        "decode": decode,
        "report": rep,
    }


def run_bench(state: dict, items: list[dict], *, top_k: int = 8) -> dict[str, Any]:
    rows = [evaluate_item(state, item, top_k=top_k) for item in items]
    passed = sum(1 for r in rows if r.get("ok"))
    return {
        "schema_version": 1,
        "bench": "layout_parity_v0",
        "passed": passed,
        "total": len(rows),
        "all_passed": passed == len(rows),
        "items": rows,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench layout-parity bilingual T9")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_LEXICON_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/layout_parity_cues.v1.json",
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument(
        "--command-headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/layout_command_headwords.v1.txt",
    )
    p.add_argument(
        "--bundle",
        type=Path,
        default=root / "lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json",
    )
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    items = json.loads(args.cues.read_text(encoding="utf-8"))
    headwords = read_headwords(args.headwords)
    headwords.extend(read_headwords(args.command_headwords))
    headwords = list(dict.fromkeys(headwords))

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    state = boot["state"]
    bootstrap_rep = bootstrap_linked_graphemes(state, en_words=headwords)
    ingest_en_lex_batch(state, read_headwords(args.command_headwords), copies=3, configure=True)
    hub_rep = ingest_entity_hub(state, json.loads(args.bundle.read_text(encoding="utf-8")))
    ortho_rep = imprint_capitalize_bootstrap(state)
    bridge_rep = ingest_keyboard_ortho_bridge(state, ensure_ortho_bootstrap=False)
    boot_ms = round((time.perf_counter() - t0) * 1000)

    report = run_bench(state, items, top_k=args.top_k)
    report["boot_ms"] = boot_ms
    report["bootstrap"] = bootstrap_rep
    report["hub"] = hub_rep
    report["ortho_bootstrap"] = ortho_rep
    report["keyboard_ortho_bridge"] = bridge_rep

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nSUMMARY: {report['passed']}/{report['total']} boot={boot_ms}ms", file=sys.stderr)
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
