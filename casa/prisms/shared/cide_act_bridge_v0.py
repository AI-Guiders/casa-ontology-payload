#!/usr/bin/env python3
"""CIDE act bridge: layout-parity tick → preview chip JSON (stdio v0)."""

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
from casa.prisms.tick.unified_tick_v0 import unified_tick


def boot_state(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    ru = agent_store_dir(STORE_RU_LEXICON_V0, root=root)
    en = agent_store_dir(STORE_EN_FOLK_V0, root=root)
    t0 = time.perf_counter()
    boot = boot_linked_stores(ru, en)
    state = boot["state"]
    headwords = read_headwords(root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt")
    headwords.extend(read_headwords(root / "lab/exp_bilingual_v0/layout_command_headwords.v1.txt"))
    headwords = list(dict.fromkeys(headwords))
    bootstrap_linked_graphemes(state, en_words=headwords)
    ingest_en_lex_batch(state, ["attach"], copies=2, configure=False)
    bundle = root / "lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json"
    ingest_entity_hub(state, json.loads(bundle.read_text(encoding="utf-8")))
    imprint_capitalize_bootstrap(state)
    ingest_keyboard_ortho_bridge(state, ensure_ortho_bootstrap=False)
    meta = {"boot_ms": round((time.perf_counter() - t0) * 1000), "stores": {"ru": str(ru), "en": str(en)}}
    return state, meta


def preview_from_layout(rep: dict[str, Any]) -> dict[str, Any]:
    winner = rep.get("winner_layout")
    grapheme = rep.get("winner_grapheme") or ""
    en = list(rep.get("winner_anchors_en") or [])[:6]
    ru = list(rep.get("winner_anchors_ru") or [])[:6]
    focus = en[0] if en and rep.get("segment") == "command" else (ru[0] if ru else (en[0] if en else ""))
    return {
        "kind": "preview_chip",
        "segment": rep.get("segment"),
        "winner_layout": winner,
        "grapheme_string": grapheme,
        "focus_word": focus,
        "columns": [
            {"language": "en", "anchors": en},
            {"language": "ru", "anchors": ru},
        ],
    }


def preview_from_prefix(state: dict, prefix: str, *, top_k: int) -> dict[str, Any]:
    tick = unified_tick(state, prefix, top_k=top_k)
    en: list[str] = []
    ru: list[str] = []
    for tb in tick.get("t9_branches") or []:
        words = list(tb.get("anchors") or [])
        if tb.get("language") == "en":
            en.extend(words)
        if tb.get("language") == "ru":
            ru.extend(words)
    focus = ru[0] if ru and tick.get("commitment") != "ambiguous" else (en[0] if en else prefix)
    return {
        "kind": "preview_chip",
        "segment": "prose",
        "grapheme_string": prefix,
        "focus_word": focus,
        "commitment": tick.get("commitment"),
        "columns": [
            {"language": "en", "anchors": en[:6]},
            {"language": "ru", "anchors": ru[:6]},
        ],
        "tick": tick,
    }


def handle_request(state: dict, req: dict[str, Any], *, top_k: int) -> dict[str, Any]:
    op = str(req.get("op") or "tick")
    if op == "tick":
        if events := req.get("events"):
            rep = layout_tick(state, list(events), top_k=top_k)
            chip = preview_from_layout(rep)
            return {"schema_version": 1, "event": "preview", "preview": chip, "layout": rep}
        prefix = str(req.get("prefix") or "")
        chip = preview_from_prefix(state, prefix, top_k=top_k)
        return {"schema_version": 1, "event": "preview", "preview": chip}
    if op == "ping":
        return {"schema_version": 1, "event": "pong"}
    return {"schema_version": 1, "event": "error", "error": f"unknown op: {op}"}


def serve_loop(state: dict, *, top_k: int) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({"schema_version": 1, "event": "ready", "bridge": "cide_act_v0"}, ensure_ascii=False), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as ex:
            print(json.dumps({"event": "error", "error": str(ex)}, ensure_ascii=False), flush=True)
            continue
        if str(req.get("op") or "") == "quit":
            break
        print(json.dumps(handle_request(state, req, top_k=top_k), ensure_ascii=False), flush=True)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="CIDE act bridge (preview chip stdio)")
    p.add_argument("mode", nargs="?", default="serve", choices=["serve", "once"])
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--json", type=Path, default=None, help="once: request document")
    args = p.parse_args()

    state, meta = boot_state(root)
    if args.mode == "once":
        req = json.loads(args.json.read_text(encoding="utf-8")) if args.json else {"op": "tick", "prefix": "co"}
        out = handle_request(state, req, top_k=args.top_k)
        out["boot"] = meta
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    meta["bridge"] = "cide_act_v0"
    print(json.dumps({"schema_version": 1, "event": "boot", **meta}, ensure_ascii=False), flush=True)
    serve_loop(state, top_k=args.top_k)


if __name__ == "__main__":
    main()
