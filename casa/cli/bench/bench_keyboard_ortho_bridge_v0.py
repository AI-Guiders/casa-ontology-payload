#!/usr/bin/env python3
"""Bench keyboard ↔ ortho bridge (Shift/Caps Lock vs Capitalize/Upper)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
from pathlib import Path

from casa.prisms.memory.boot_core_ltm_v0 import default_core_ltm_dir, merge_core_ltm
from casa.prisms.memory.boot_linked_stores_v0 import boot_linked_stores
from casa.prisms.memory.grapheme_ingest_v0 import bootstrap_linked_graphemes
from casa.prisms.memory.keyboard_ortho_bridge_v0 import bridge_edges_present, ingest_keyboard_ortho_bridge
from casa.prisms.memory.ortho_field_v0 import imprint_capitalize_bootstrap
from casa.prisms.memory.ortho_process_v0 import PROC_CAPITALIZE, PROC_UPPER, upper_word
from casa.prisms.memory.ortho_tick_v0 import ortho_tick
from casa.prisms.shared.store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir
from casa.prisms.memory.vk_decode_v0 import decode_events


def run_bench(state: dict, items: list[dict]) -> dict:
    rows: list[dict] = []
    passed = 0
    bridge_ok = bridge_edges_present(state)

    for item in items:
        iid = item.get("id")
        ok = True
        detail: dict = {}

        if events := item.get("events"):
            text = decode_events(list(events), str(item.get("layout") or "qwerty_us"), state=state)
            detail["decode"] = text
            if exp := item.get("expect_decode"):
                ok = text == exp
            if sub := item.get("expect_decode_contains"):
                ok = ok and sub in text

        if ctx := item.get("ortho_context"):
            word = str(item.get("word") or "attach")
            tick = ortho_tick(state, word, context=ctx, auto_extract=False)
            display = (tick.get("act") or {}).get("surface") or tick.get("hypothesis")
            detail["ortho"] = {"context": ctx, "display": display, "verdict": tick.get("verdict")}
            exp = item.get("expect_ortho_display")
            if exp is not None:
                ok = ok and display == exp
            if exp == "ALL_CAPS" and item.get("word"):
                ok = ok and display == upper_word(str(item["word"]))

        if item.get("require_bridge"):
            ok = ok and bridge_ok
            detail["bridge_on_field"] = bridge_ok

        if ok:
            passed += 1
        rows.append({"id": iid, "ok": ok, "detail": detail})

    return {
        "schema_version": 1,
        "bench": "keyboard_ortho_bridge_v1",
        "bridge_on_field": bridge_ok,
        "passed": passed,
        "total": len(rows),
        "all_passed": passed == len(rows) and bridge_ok,
        "items": rows,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench keyboard ↔ ortho bridge")
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/keyboard_ortho_bridge_cues.v1.json",
    )
    p.add_argument("--core-ltm", type=Path, default=default_core_ltm_dir(root=root))
    args = p.parse_args()

    items = json.loads(args.cues.read_text(encoding="utf-8"))
    ru = agent_store_dir(STORE_RU_LEXICON_V0, root=root)
    en = agent_store_dir(STORE_EN_FOLK_V0, root=root)
    boot = boot_linked_stores(ru, en, core_ltm_dir=args.core_ltm)
    state = boot["state"]
    bootstrap_linked_graphemes(state, en_words=["attach", "cow"])
    imprint_capitalize_bootstrap(state)
    ingest_keyboard_ortho_bridge(state, ensure_ortho_bootstrap=False)

    report = run_bench(state, items)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSUMMARY: {report['passed']}/{report['total']} bridge={report['bridge_on_field']}", file=sys.stderr)
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
