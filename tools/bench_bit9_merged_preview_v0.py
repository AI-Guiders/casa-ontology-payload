#!/usr/bin/env python3
"""Evaluate merged BiT9 preview chip — canonical pass/fail for product semantics."""

from __future__ import annotations

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
from homoglyph_v0 import dual_script_readings  # type: ignore
from hub_neighbors_v0 import neighbor_surfaces  # type: ignore
from merge_preview_v0 import merge_preview_anchors, preview_words, preview_words_for_lang  # type: ignore
from predictor_v0 import predict_t9  # type: ignore
from script_detect_v0 import predict_script  # type: ignore
from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_GENERAL_V0, agent_store_dir  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore
from unified_tick_v0 import unified_tick  # type: ignore


def _build_branches(state: dict, visual: str, *, top_k: int) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    readings = dual_script_readings(visual)
    if len(readings) >= 2:
        branches: list[dict[str, Any]] = []
        for rd in readings:
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
        return branches, "ambiguous", {"readings": readings}
    pred = predict_t9(state, visual, top_k=top_k)
    script = predict_script(state, visual)
    branches = [
        {
            "language": script.get("hypothesis_lang"),
            "script": script.get("hypothesis_script"),
            "grapheme_string": visual,
            "predict": pred,
            "anchors": [a.get("word") for a in pred.get("anchors") or []],
        }
    ]
    return branches, "commit", script


def evaluate_case(state: dict, case: dict[str, Any], *, top_k: int = 8) -> dict[str, Any]:
    visual = str(case.get("visual") or "")
    branches, mode, script_meta = _build_branches(state, visual, top_k=top_k)
    preview = merge_preview_anchors(branches, state=state, top_k=top_k, hub_boost=True)
    words = preview_words(preview)
    en_w = preview_words_for_lang(preview, "en")
    ru_w = preview_words_for_lang(preview, "ru")

    checks: list[dict[str, Any]] = []
    ok = True

    if case.get("expect_commitment"):
        c_ok = mode == case["expect_commitment"] or (
            case["expect_commitment"] == "ambiguous" and mode == "ambiguous"
        )
        if case["expect_commitment"] == "resolved":
            c_ok = mode == "commit"
        checks.append({"name": "commitment", "pass": c_ok, "detail": {"mode": mode, "expect": case["expect_commitment"]}})
        ok = ok and c_ok

    if case.get("expect_lang"):
        lang = script_meta.get("hypothesis_lang") if mode == "commit" else None
        if mode == "ambiguous":
            langs = {b.get("language") for b in branches}
            l_ok = case["expect_lang"] in langs
        else:
            l_ok = lang == case["expect_lang"]
        checks.append({"name": "lang", "pass": l_ok, "detail": {"expect": case["expect_lang"], "mode": mode}})
        ok = ok and l_ok

    for field, pool, hay in (
        ("preview_must", case.get("preview_must") or case.get("expect_preview_in"), words),
        ("preview_must_not", case.get("preview_must_not") or case.get("expect_preview_must_not"), words),
    ):
        if not pool:
            continue
        if field == "preview_must":
            missing = [w for w in pool if w not in hay]
            p_ok = not missing
            checks.append({"name": field, "pass": p_ok, "detail": {"required": pool, "missing": missing}})
            ok = ok and p_ok
        else:
            found_bad = [w for w in pool if w in hay]
            n_ok = not found_bad
            checks.append({"name": field, "pass": n_ok, "detail": {"forbidden": pool, "found": found_bad}})
            ok = ok and n_ok

    for label, expect_list, got in (
        ("preview_en_any", case.get("preview_en_any") or case.get("expect_preview_en_any"), en_w),
        ("preview_ru_any", case.get("preview_ru_any") or case.get("expect_preview_ru_any"), ru_w),
    ):
        if expect_list:
            found = sorted(set(expect_list) & set(got))
            a_ok = len(found) >= 1
            checks.append({"name": label, "pass": a_ok, "detail": {"any_of": expect_list, "found": found, "en_or_ru": got}})
            ok = ok and a_ok

    min_en = int(case.get("min_en_in_preview") or 0)
    min_ru = int(case.get("min_ru_in_preview") or 0)
    if min_en:
        e_ok = len(en_w) >= min_en
        checks.append({"name": "min_en", "pass": e_ok, "detail": {"min": min_en, "got": len(en_w), "words": en_w}})
        ok = ok and e_ok
    if min_ru:
        r_ok = len(ru_w) >= min_ru
        checks.append({"name": "min_ru", "pass": r_ok, "detail": {"min": min_ru, "got": len(ru_w), "words": ru_w}})
        ok = ok and r_ok

    if case.get("expect_both_langs"):
        b_ok = bool(en_w) and bool(ru_w)
        checks.append({"name": "both_langs", "pass": b_ok, "detail": {"en": en_w, "ru": ru_w}})
        ok = ok and b_ok

    hub_map = case.get("expect_hub_surface_for") or {}
    for en_anchor, ru_surface in hub_map.items():
        surfaces = neighbor_surfaces(state, str(en_anchor))
        hub_ok = f"lang.word.{norm_word(str(ru_surface))}" in surfaces
        in_preview = norm_word(str(ru_surface)) in ru_w
        h_ok = hub_ok or in_preview
        checks.append(
            {
                "name": f"hub_{en_anchor}",
                "pass": h_ok,
                "detail": {
                    "en": en_anchor,
                    "expect_ru": ru_surface,
                    "hub_has": hub_ok,
                    "in_preview": in_preview,
                },
            }
        )
        ok = ok and h_ok

    if case.get("unified_verdict_pass"):
        tick = unified_tick(
            state,
            visual,
            expect_preview_in=case.get("preview_must"),
            expect_preview_en_any=case.get("preview_en_any"),
            expect_preview_ru_any=case.get("preview_ru_any"),
            top_k=top_k,
        )
        u_ok = tick.get("verdict") == "pass"
        checks.append({"name": "unified_tick", "pass": u_ok, "detail": {"verdict": tick.get("verdict")}})
        ok = ok and u_ok

    return {
        "id": case.get("id"),
        "visual": visual,
        "ok": ok,
        "mode": mode,
        "preview": preview,
        "preview_flat": words,
        "checks": checks,
    }


def run_bench(state: dict, cases: list[dict], *, top_k: int = 8) -> dict[str, Any]:
    rows = [evaluate_case(state, c, top_k=top_k) for c in cases]
    passed = sum(1 for r in rows if r.get("ok"))
    failures = [r for r in rows if not r.get("ok")]
    return {
        "schema_version": 1,
        "bench": "bit9_merged_preview_v0",
        "passed": passed,
        "total": len(rows),
        "all_passed": passed == len(rows),
        "cases": rows,
        "failures": failures,
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="BiT9 merged preview evaluation (canonical)")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_GENERAL_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/merged_preview_eval_cues.v1.json",
    )
    p.add_argument(
        "--bundle",
        type=Path,
        default=root / "lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json",
    )
    p.add_argument("--headwords", type=Path, default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt")
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    state = boot["state"]
    bootstrap_linked_graphemes(state, en_words=read_headwords(args.headwords))
    ingest_entity_hub(state, json.loads(args.bundle.read_text(encoding="utf-8")))
    boot_ms = round((time.perf_counter() - t0) * 1000)

    cases = json.loads(args.cues.read_text(encoding="utf-8"))
    report = run_bench(state, cases, top_k=args.top_k)
    report["boot_ms"] = boot_ms

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")

    failed = report["failures"]
    flat = failed[0]["preview_flat"] if failed else (report["cases"][0]["preview_flat"] if report["cases"] else [])
    print(
        f"\nSUMMARY: merged_preview {report['passed']}/{report['total']} boot={boot_ms}ms"
        + (f" FAIL={failed[0]['id']}" if failed else "")
        + (f" sample={flat[:8]}" if flat else ""),
        file=sys.stderr,
    )
    if failed:
        for f in failed[:3]:
            bad = [c for c in f.get("checks") or [] if not c.get("pass")]
            print(f"  FAIL {f.get('id')}: {[c.get('name') for c in bad]}", file=sys.stderr)

    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
