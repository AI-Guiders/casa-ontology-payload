#!/usr/bin/env python3
"""Bench optional semantic prior in merged preview (taxonomy on L3)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from casa.prisms.memory.boot_linked_stores import boot_linked_stores
from casa.prisms.memory.en_lexicon import read_headwords
from casa.prisms.memory.entity_hub_ingest import ingest_entity_hub
from casa.prisms.memory.entity_taxonomy_ingest import ingest_entity_taxonomy
from casa.prisms.memory.grapheme_ingest import bootstrap_linked_graphemes
from casa.prisms.memory.homoglyph import dual_script_readings
from casa.prisms.memory.merge_preview import merge_preview_anchors, preview_words
from casa.prisms.tick.predictor import predict_t9
from casa.prisms.shared.store_layout import STORE_EN_FOLK_V0, STORE_RU_GENERAL_V0, agent_store_dir


def _branches(state: dict, visual: str, *, top_k: int) -> list[dict[str, Any]]:
    branches: list[dict[str, Any]] = []
    for rd in dual_script_readings(visual):
        gstr = str(rd["grapheme_string"])
        pred = predict_t9(state, gstr, top_k=top_k)
        branches.append(
            {
                "language": rd["language"],
                "script": rd["script"],
                "grapheme_string": gstr,
                "predict": pred,
                "anchors": [a.get("word") for a in pred.get("anchors") or []],
            }
        )
    return branches


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench semantic prior in merged preview")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_GENERAL_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument("--visual", default="co")
    p.add_argument("--expect_before", default="co", help="Word ranked higher without prior")
    p.add_argument("--expect_after", default="cow", help="Word ranked higher with taxonomy prior")
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    state = boot["state"]
    bootstrap_linked_graphemes(state, en_words=read_headwords(root / "lab/exp_bilingual/en_folk_headwords.v1.txt"))
    ingest_entity_hub(state, json.loads((root / "lab/exp_bilingual/kb-entity-surfaces-dev.v1.json").read_text(encoding="utf-8")))
    ingest_entity_taxonomy(state, json.loads((root / "lab/kb/kb-entity-taxonomy-v1.json").read_text(encoding="utf-8")))
    boot_ms = round((time.perf_counter() - t0) * 1000)

    branches = _branches(state, args.visual, top_k=args.top_k)
    plain = preview_words(merge_preview_anchors(branches, state=state, top_k=args.top_k, semantic_prior=False))
    prior = preview_words(merge_preview_anchors(branches, state=state, top_k=args.top_k, semantic_prior=True))

    def _rank(words: list[str], w: str) -> int:
        try:
            return words.index(w) + 1
        except ValueError:
            return 999

    rb = _rank(plain, args.expect_before)
    ra = _rank(prior, args.expect_after)
    ok = ra < rb and args.expect_after in prior
    report = {
        "schema_version": 1,
        "bench": "preview_semantic_prior",
        "visual": args.visual,
        "boot_ms": boot_ms,
        "plain_preview": plain,
        "prior_preview": prior,
        "rank_before_word": {args.expect_before: rb},
        "rank_after_word": {args.expect_after: ra},
        "ok": ok,
        "all_passed": ok,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(
        f"\nSUMMARY: semantic_prior ok={ok} plain={plain[:6]} prior={prior[:6]} boot={boot_ms}ms",
        file=sys.stderr,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
