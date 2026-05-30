#!/usr/bin/env python3
"""Bench linked RU + EN stores: L2 on each side + entity hub cross-language."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from bench_entity_hub_v0 import DEFAULT_CUES, run_bench as run_hub_bench  # type: ignore
from boot_linked_stores_v0 import boot_linked_stores  # type: ignore
from entity_hub_ingest_v0 import ingest_entity_hub  # type: ignore
from hub_neighbors_v0 import hub_neighbors  # type: ignore
from predictor_v0 import predict_t9  # type: ignore
from sss_l2_shard_v0 import L2_CONCEPT_PREFIX, concept_votes_l2  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore
from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir  # type: ignore

L2_CHECK_PAIRS = [
    ("cow", "en"),
    ("корова", "ru"),
    ("mother", "en"),
    ("мама", "ru"),
    ("the", "en"),
    ("and", "en"),
]

T9_LINKED_CUES = [
    {"id": "co_cow", "cue": "co", "expect_in": ["cow"]},
    {"id": "cow_full", "cue": "cow", "expect": "cow"},
    {"id": "the_full", "cue": "the", "expect": "the"},
]


def check_l2_presence(state: dict, pairs: list[tuple[str, str]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passed = 0
    for word, lang in pairs:
        cid = f"{L2_CONCEPT_PREFIX}{norm_word(word)}"
        votes, lid = concept_votes_l2(state, cid)
        ok = votes > 0
        if ok:
            passed += 1
        rows.append({"word": word, "lang": lang, "votes": votes, "lattice_id": lid, "ok": ok})
    total = len(pairs)
    return {
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "items": rows,
    }


def check_t9(state: dict, cues: list[dict]) -> dict[str, Any]:
    from critic_v0 import critic_validate  # type: ignore

    rows: list[dict] = []
    passed = 0
    for item in cues:
        cue = norm_word(str(item.get("cue") or ""))
        pred = predict_t9(state, cue, top_k=8)
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
                "anchors": [a.get("word") for a in pred.get("anchors") or []][:8],
                "ok": ok,
            }
        )
    total = len(cues)
    return {"passed": passed, "total": total, "all_passed": passed == total, "items": rows}


def check_hub_links(state: dict, samples: list[tuple[str, str]]) -> dict[str, Any]:
    rows: list[dict] = []
    passed = 0
    for anchor, expect_surface in samples:
        rep = hub_neighbors(state, anchor)
        expect_cid = f"{L2_CONCEPT_PREFIX}{norm_word(expect_surface)}"
        ok = expect_cid in rep.get("concept_ids") or []
        if ok:
            passed += 1
        rows.append(
            {
                "anchor": anchor,
                "expect_surface": expect_surface,
                "entities": rep.get("entities"),
                "concept_ids": rep.get("concept_ids"),
                "ok": ok,
            }
        )
    total = len(samples)
    return {"passed": passed, "total": total, "all_passed": passed == total, "items": rows}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench linked RU+EN stores + entity hub")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_LEXICON_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--bundle",
        type=Path,
        default=root / "examples/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json",
    )
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    boot_ms = round((time.perf_counter() - t0) * 1000)
    state = boot["state"]

    t1 = time.perf_counter()
    ingest_rep = ingest_entity_hub(state, bundle, strengthen_l2=False)
    ingest_ms = round((time.perf_counter() - t1) * 1000)

    l2_rep = check_l2_presence(state, L2_CHECK_PAIRS)
    t9_rep = check_t9(state, T9_LINKED_CUES)
    hub_rep = run_hub_bench(state, DEFAULT_CUES)
    cross_rep = check_hub_links(state, [("cow", "корова"), ("корова", "cow"), ("mother", "мама")])

    all_ok = (
        l2_rep["all_passed"]
        and t9_rep["all_passed"]
        and hub_rep["all_passed"]
        and cross_rep["all_passed"]
    )

    report = {
        "schema_version": 1,
        "bench": "bilingual_linked_v0",
        "all_passed": all_ok,
        "boot_ms": boot_ms,
        "ingest_ms": ingest_ms,
        "boot": {k: v for k, v in boot.items() if k != "state"},
        "ingest": ingest_rep,
        "l2_presence": l2_rep,
        "t9_en": t9_rep,
        "entity_hub": {
            "passed": hub_rep["passed"],
            "total": hub_rep["total"],
            "all_passed": hub_rep["all_passed"],
        },
        "cross_links": cross_rep,
    }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)

    print(
        f"\nSUMMARY: linked ok={all_ok} "
        f"L2={l2_rep['passed']}/{l2_rep['total']} "
        f"T9={t9_rep['passed']}/{t9_rep['total']} "
        f"hub={hub_rep['passed']}/{hub_rep['total']} "
        f"cross={cross_rep['passed']}/{cross_rep['total']} "
        f"boot={boot_ms}ms ingest={ingest_ms}ms",
        file=sys.stderr,
    )
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
