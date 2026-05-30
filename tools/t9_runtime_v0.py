#!/usr/bin/env python3
"""Bilingual T9 runtime: boot linked field + unified_tick for C# console (stdio JSON)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from boot_linked_stores_v0 import boot_linked_stores  # type: ignore
from en_lexicon_v0 import read_headwords as read_en_headwords  # type: ignore
from entity_hub_ingest_v0 import ingest_entity_hub  # type: ignore
from grapheme_ingest_v0 import bootstrap_linked_graphemes  # type: ignore
from ortho_field_v0 import imprint_capitalize_bootstrap  # type: ignore
from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir  # type: ignore
from unified_tick_v0 import unified_tick  # type: ignore


def boot_demo_field(
    *,
    root: Path,
    ru_store: Path,
    en_store: Path,
    bundle_path: Path,
    headwords_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Same bootstrap as bench_unified_tick_v0."""
    t0 = time.perf_counter()
    boot = boot_linked_stores(ru_store, en_store)
    state = boot["state"]
    headwords = read_en_headwords(headwords_path)
    bootstrap_rep = bootstrap_linked_graphemes(state, en_words=headwords)
    hub_rep = ingest_entity_hub(state, json.loads(bundle_path.read_text(encoding="utf-8")))
    ortho_rep = imprint_capitalize_bootstrap(state)
    boot_ms = round((time.perf_counter() - t0) * 1000)
    meta = {
        "boot_ms": boot_ms,
        "bootstrap": bootstrap_rep,
        "hub": hub_rep,
        "ortho_bootstrap": ortho_rep,
        "boot": {k: v for k, v in boot.items() if k != "state"},
    }
    return state, meta


def tick_view(state: dict, prefix: str, *, top_k: int = 8) -> dict[str, Any]:
    """Unified tick + compact console-friendly view."""
    raw = unified_tick(state, prefix, top_k=top_k)
    branches: list[dict[str, Any]] = []
    for tb in raw.get("t9_branches") or []:
        pred = tb.get("predict") or {}
        anchors = pred.get("anchors") or []
        branches.append(
            {
                "language": tb.get("language"),
                "script": tb.get("script"),
                "grapheme_string": tb.get("grapheme_string"),
                "commitment": raw.get("commitment"),
                "anchors": [
                    {
                        "word": a.get("word"),
                        "activation": a.get("activation"),
                        "rank": a.get("rank"),
                    }
                    for a in anchors
                ],
                "focus": (pred.get("focus") or {}).get("word") if pred.get("focus") else None,
                "hypothesis": pred.get("hypothesis"),
            }
        )
    return {
        "schema_version": 1,
        "prefix": prefix,
        "script_mode": raw.get("script_mode"),
        "commitment": raw.get("commitment"),
        "script_lang": (raw.get("script") or {}).get("hypothesis_lang"),
        "branches": branches,
        "verdict": raw.get("verdict"),
        "raw": raw,
    }


def serve_stdio(state: dict, *, meta: dict[str, Any]) -> int:
    ready = {"schema_version": 1, "event": "ready", **meta}
    print(json.dumps(ready, ensure_ascii=False), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            err = {"schema_version": 1, "event": "error", "error": f"invalid json: {exc}"}
            print(json.dumps(err, ensure_ascii=False), flush=True)
            continue
        op = str(req.get("op") or "tick")
        if op in ("quit", "exit", "q"):
            print(json.dumps({"schema_version": 1, "event": "bye"}, ensure_ascii=False), flush=True)
            return 0
        if op != "tick":
            print(
                json.dumps(
                    {"schema_version": 1, "event": "error", "error": f"unknown op: {op}"},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue
        prefix = str(req.get("prefix") or "")
        top_k = int(req.get("top_k") or 8)
        t0 = time.perf_counter()
        view = tick_view(state, prefix, top_k=top_k)
        view["event"] = "tick"
        view["tick_ms"] = round((time.perf_counter() - t0) * 1000)
        print(json.dumps(view, ensure_ascii=False), flush=True)
    return 0


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bilingual T9 runtime (stdio JSON for Casa.T9.Console)")
    p.add_argument(
        "command",
        choices=("serve", "once"),
        nargs="?",
        default="serve",
        help="serve=stdio loop; once=single prefix",
    )
    p.add_argument("--prefix", type=str, default="", help="For once: visual prefix cue")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_LEXICON_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--bundle",
        type=Path,
        default=root / "examples/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json",
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "examples/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument("--top-k", type=int, default=8)
    args = p.parse_args()

    if not args.ru_store.is_dir():
        print(
            f"ERROR: RU store missing: {args.ru_store}\n"
            "Run: python tools/init_ru_dev_store_v0.py",
            file=sys.stderr,
        )
        return 2
    if not args.en_store.is_dir():
        print(
            f"ERROR: EN store missing: {args.en_store}\n"
            "Run: python tools/init_en_folk_store_v0.py",
            file=sys.stderr,
        )
        return 2

    state, meta = boot_demo_field(
        root=root,
        ru_store=args.ru_store,
        en_store=args.en_store,
        bundle_path=args.bundle,
        headwords_path=args.headwords,
    )

    if args.command == "once":
        view = tick_view(state, args.prefix, top_k=args.top_k)
        print(json.dumps({**meta, **view}, ensure_ascii=False, indent=2))
        return 0

    return serve_stdio(state, meta=meta)


if __name__ == "__main__":
    raise SystemExit(main())
