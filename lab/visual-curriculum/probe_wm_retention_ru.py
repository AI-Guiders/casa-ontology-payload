#!/usr/bin/env python3
"""RU-ε½ WM retention gate — partner callback from WM/world, not ring buffer (ADR-0055)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/wm-retention-plan-v1.json"
_PROBE = "probe_wm_retention_ru"
_STAGE = "stage-05e-half-wm-retention-ru"


def _seed_wm_edges(state, pairs: list[list[str]], *, tick: int = 5) -> None:
    from casa.prisms.memory.wm import place_wm_edge, score_wm_edges, spawn_wm_lattice

    spawn_wm_lattice(state, tick=tick)
    for a, b in pairs:
        place_wm_edge(state, a, b, tick=tick)
        score_wm_edges(state, tick=tick + 1, query="как мы говорили")


def _run_case(
    case: dict[str, Any],
    *,
    store,
    state,
    wm,
    bundle,
) -> tuple[bool, dict[str, Any], str]:
    from casa.domain.dialogue_turn import append_partner_turn
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.memory.wm import reset_wm_probe_session
    from casa.prisms.tick.phrase_compose import paste_ratio_against_blocks

    reset_wm_probe_session(store, state)
    _seed_wm_edges(state, list(case.get("seed_edges") or []))
    for turn in case.get("turns") or []:
        append_partner_turn(
            store,
            str(turn.get("text") or ""),
            provenance=dict(turn.get("provenance") or {}),
        )

    q = str(case.get("recall_query") or "")
    ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
    reply = compose_subject_utterance(q, ctx)
    paste = paste_ratio_against_blocks(reply, ctx.blocks)
    wm_blocks = [b for b in ctx.blocks if b.get("source") == "wm_prism"]

    ok = paste <= float(case.get("max_paste_ratio") or 0.5)
    if case.get("require_wm_block"):
        ok = ok and bool(wm_blocks)
    for sub in case.get("expect_substrings") or []:
        if str(sub).lower() not in reply.lower():
            ok = False
    detail = {
        "paste_ratio": round(paste, 3),
        "wm_blocks": len(wm_blocks),
        "has_wm_retrieval": bool(wm_blocks),
    }
    return ok, detail, reply


def main() -> None:
    setup_probe_imports()
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    min_ratio = float(plan.get("min_pass_ratio") or 1.0)

    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    know = 0
    total = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory(tick=12)

        for case in scenarios:
            if not case.get("wired", True):
                continue
            total += 1
            ok, detail, reply = _run_case(case, store=store, state=state, wm=wm, bundle=bundle)
            if ok:
                know += 1
            items.append(
                {
                    "scenario_id": case.get("scenario_id"),
                    "stage": case.get("stage") or _STAGE,
                    "verdict": "know" if ok else "wrong",
                    "reply": reply,
                    "reply_excerpt": reply[:360],
                    "wired": True,
                    **detail,
                }
            )

        ratio = (know / total) if total else 0.0
        gate_pass = total > 0 and ratio >= min_ratio and know == total
        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "stage": _STAGE,
            "class_id": "ru-text-tract",
            "plan": str(args.plan),
            "know": know,
            "total": total,
            "pass_ratio": round(ratio, 3),
            "min_pass_ratio": min_ratio,
            "items": items,
            "gate_pass": gate_pass,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-wm-retention-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for case, item in zip(scenarios, items, strict=False):
        if not case.get("wired", True):
            continue
        print("\n=== WM retention:", case.get("scenario_id"), "|", item.get("verdict"), "===\n")
        for turn in case.get("turns") or []:
            print(f"Партнёр: {turn.get('text')}")
        print(f"\nПартнёр: {case.get('recall_query')}")
        print(f"\nНейманн: {item.get('reply') or item.get('reply_excerpt')}")
        print(
            f"\n[paste={item.get('paste_ratio')} wm_blocks={item.get('wm_blocks')} "
            f"wm_retrieval={item.get('has_wm_retrieval')}]"
        )

    print(
        json.dumps(
            {"probe": _PROBE, "gate_pass": report.get("gate_pass"), "know": know, "total": total, "path": str(out)},
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
