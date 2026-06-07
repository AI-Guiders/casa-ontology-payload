#!/usr/bin/env python3
"""CEFR written gate — A1..C2 levels from descriptor scenarios (honest achieved_level)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports
from probe_nositel_gate_ru import _scenario_pass

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/cefr-gate-plan-v1.json"
_PROBE = "probe_cefr_gate_ru"
_LEVEL_ORDER = ("A1", "A2", "B1", "B2", "C1", "C2")


def _level_index(level: str) -> int:
    try:
        return _LEVEL_ORDER.index(level)
    except ValueError:
        return -1


def _compute_achieved_level(
    by_level: dict[str, dict[str, Any]],
    level_rules: dict[str, dict[str, Any]],
    level_order: list[str],
) -> str | None:
    achieved: str | None = None
    for level in level_order:
        rule = level_rules.get(level) or {}
        if not rule.get("wired", True):
            by_level.setdefault(level, {"status": rule.get("status", "deferred"), "wired": False})
            continue
        bucket = by_level.get(level) or {}
        total = int(bucket.get("total") or 0)
        know = int(bucket.get("know") or 0)
        if total <= 0:
            break
        ratio = know / total
        min_ratio = float(rule.get("min_pass_ratio") or 1.0)
        if ratio >= min_ratio:
            achieved = level
        else:
            break
    return achieved


def main() -> None:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.tick.phrase_compose import paste_ratio_against_blocks
    from casa.prisms.tick.semantic_read import route_kb_read

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    level_rules = dict(plan.get("level_rules") or {})
    level_order = list(plan.get("level_order") or _LEVEL_ORDER)
    block_exit = str(plan.get("level_targets", {}).get("block_12_exit") or "B1")
    nositel_requires = str(plan.get("level_targets", {}).get("nositel_claim_requires") or "C1")

    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    wired_know = 0
    wired_total = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            wired = bool(case.get("wired", True))
            if not wired:
                items.append(
                    {
                        "scenario_id": case.get("scenario_id"),
                        "cefr_level": case.get("cefr_level"),
                        "descriptor_id": case.get("descriptor_id"),
                        "skill": case.get("skill"),
                        "verdict": "deferred",
                        "wired": False,
                        "status": case.get("status", "deferred"),
                    }
                )
                continue

            q = str(case.get("query") or "")
            intent = route_kb_read(q, bundle).intent
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            paste = paste_ratio_against_blocks(reply, ctx.blocks)
            ok, detail = _scenario_pass(case, reply=reply, query_intent=intent, paste_ratio=paste)
            wired_total += 1
            if ok:
                wired_know += 1
            items.append(
                {
                    "query": q[:120],
                    "verdict": "know" if ok else "wrong",
                    "reply_excerpt": reply[:360],
                    "wired": True,
                    "cefr_level": case.get("cefr_level"),
                    "descriptor_id": case.get("descriptor_id"),
                    "skill": case.get("skill"),
                    "descriptor_ru": case.get("descriptor_ru"),
                    **detail,
                }
            )

        by_level: dict[str, dict[str, Any]] = {}
        for row in items:
            if not row.get("wired"):
                lvl = str(row.get("cefr_level") or "")
                by_level[lvl] = {
                    "status": row.get("status", "deferred"),
                    "wired": False,
                    "know": 0,
                    "total": 0,
                }
                continue
            lvl = str(row.get("cefr_level") or "other")
            bucket = by_level.setdefault(lvl, {"know": 0, "total": 0, "wired": True})
            bucket["total"] += 1
            if row.get("verdict") == "know":
                bucket["know"] += 1

        achieved = _compute_achieved_level(by_level, level_rules, level_order)
        block_pass = (
            achieved is not None and _level_index(achieved) >= _level_index(block_exit)
        )
        nositel_pass = (
            achieved is not None and _level_index(achieved) >= _level_index(nositel_requires)
        )

        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "plan": str(args.plan),
            "framework": plan.get("framework"),
            "gate_policy": plan.get("gate_policy"),
            "scope": plan.get("scope"),
            "level_targets": plan.get("level_targets"),
            "achieved_level": achieved,
            "block_12_pass": block_pass,
            "nositel_claim_pass": nositel_pass,
            "wired_total": wired_total,
            "wired_know": wired_know,
            "wired_wrong": wired_total - wired_know,
            "by_level": by_level,
            "items": items,
            "gate_pass": block_pass,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-cefr-gate-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "achieved_level": achieved,
                "block_12_pass": block_pass,
                "nositel_claim_pass": nositel_pass,
                "wired_know": wired_know,
                "wired_total": wired_total,
                "by_level": by_level,
                "path": str(out),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
