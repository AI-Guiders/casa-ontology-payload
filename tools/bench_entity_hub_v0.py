#!/usr/bin/env python3
"""Bench bilingual entity hub: EN/RU surface → entity → other surface via L3."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from entity_hub_ingest_v0 import ingest_entity_hub  # type: ignore
from hub_neighbors_v0 import hub_neighbors, neighbor_surfaces  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore
from store_boot_v0 import boot_store  # type: ignore


DEFAULT_CUES: list[dict] = [
    {"id": "cow_ru", "anchor": "cow", "expect_surface": "корова"},
    {"id": "cow_en_token", "anchor": "W:cow", "expect_surface": "корова"},
    {"id": "korova_en", "anchor": "корова", "expect_surface": "cow"},
    {"id": "mom_ru", "anchor": "mom", "expect_surface": "мама"},
    {"id": "mother_ru", "anchor": "mother", "expect_surface": "мама"},
    {"id": "mama_en", "anchor": "мама", "expect_surface": "mom"},
    {"id": "cat_ru", "anchor": "cat", "expect_surface": "кот"},
    {"id": "dog_ru", "anchor": "dog", "expect_surface": "собака"},
    {"id": "house_ru", "anchor": "house", "expect_surface": "дом"},
    {"id": "book_ru", "anchor": "book", "expect_surface": "книга"},
    {"id": "sun_ru", "anchor": "sun", "expect_surface": "солнце"},
    {"id": "bird_ru", "anchor": "bird", "expect_surface": "птица"},
]


def _expect_concept(surface: str) -> str:
    return f"lang.word.{norm_word(surface)}"


def run_bench(
    state: dict,
    cues: list[dict],
    *,
    require_entity: bool = True,
) -> dict:
    passed = 0
    rows: list[dict] = []
    failures: list[dict] = []

    for item in cues:
        anchor = str(item.get("anchor") or "")
        expect_word = norm_word(str(item.get("expect_surface") or item.get("expect") or ""))
        expect_cid = _expect_concept(expect_word) if expect_word else ""
        expect_entity = str(item.get("expect_entity") or "")
        if not expect_entity and expect_word:
            ent_hint = item.get("entity_id")
            if ent_hint:
                expect_entity = str(ent_hint)

        rep = hub_neighbors(state, anchor, rel="denotes", via_entity=True)
        surfaces = neighbor_surfaces(state, anchor)
        entity_ids = rep.get("entities") or []
        ok_surface = expect_cid in surfaces or expect_cid in rep.get("concept_ids") or []
        ok_entity = (not require_entity) or any(eid.startswith("entity.") for eid in entity_ids)
        ok = ok_surface and ok_entity

        row = {
            "id": item.get("id"),
            "anchor": anchor,
            "expect_surface": expect_word,
            "expect_concept": expect_cid,
            "entities": entity_ids,
            "surfaces": surfaces,
            "concept_ids": rep.get("concept_ids"),
            "ok": ok,
        }
        rows.append(row)
        if ok:
            passed += 1
        else:
            failures.append(row)

    total = len(cues)
    return {
        "schema_version": 1,
        "bench": "entity_hub_v0",
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / max(1, total), 4),
        "all_passed": passed == total,
        "items": rows,
        "failures": failures,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench entity hub neighbors")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument(
        "--bundle",
        type=Path,
        default=root / "lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json",
    )
    p.add_argument("--cues", type=Path, default=None)
    p.add_argument("--no-ingest", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    cues = DEFAULT_CUES
    if args.cues:
        cues = json.loads(args.cues.read_text(encoding="utf-8"))

    t0 = time.perf_counter()
    boot = boot_store(args.store_dir, prefer_field_state=False)
    boot_ms = round((time.perf_counter() - t0) * 1000)
    state = boot["state"]

    ingest_rep: dict | None = None
    if not args.no_ingest:
        t1 = time.perf_counter()
        ingest_rep = ingest_entity_hub(state, bundle)
        ingest_ms = round((time.perf_counter() - t1) * 1000)
    else:
        ingest_ms = 0

    report = run_bench(state, cues)
    report["boot"] = {"source": boot.get("source"), "ms": boot_ms}
    report["ingest"] = ingest_rep
    report["ingest_ms"] = ingest_ms
    report["bundle_id"] = bundle.get("bundle_id")

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)

    print(
        f"\nSUMMARY: {report['passed']}/{report['total']} "
        f"boot={boot_ms}ms ingest={ingest_ms}ms "
        f"l2_new={len((ingest_rep or {}).get('l2_strengthened') or [])}",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
