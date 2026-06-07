#!/usr/bin/env python3
"""RU-β productive morphology gate — neologism in context (scaffold)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports
from probe_nositel_gate_ru import _scenario_pass

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/morph-productive-plan-v1.json"
_PROBE = "probe_morph_productive_ru"


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
    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    know = 0
    wired_total = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            if not case.get("wired", True):
                items.append(
                    {
                        "scenario_id": case.get("scenario_id"),
                        "verdict": "deferred",
                        "wired": False,
                        "defer_reason": case.get("defer_reason"),
                    }
                )
                continue

            q = str(case.get("query") or "")
            intent = route_kb_read(q, bundle, store_dir=store).intent
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            paste = paste_ratio_against_blocks(reply, ctx.blocks)
            ok, detail = _scenario_pass(case, reply=reply, query_intent=intent, paste_ratio=paste)

            affixes = case.get("expect_neologism_affix_any") or []
            if affixes:
                rl = reply.lower()
                novel = re.findall(r"[\w\u0400-\u04FF-]+", rl, flags=re.UNICODE)
                has_affix = any(a in rl or any(a.strip("-") in w for w in novel) for a in affixes)
                if not has_affix:
                    detail.setdefault("failures", []).append("neologism_affix")
                    ok = False

            wired_total += 1
            if ok:
                know += 1
            items.append(
                {
                    "query": q[:120],
                    "verdict": "know" if ok else "wrong",
                    "reply_excerpt": reply[:320],
                    "wired": True,
                    **detail,
                }
            )

        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "plan": str(args.plan),
            "know": know,
            "total": wired_total,
            "items": items,
            "gate_pass": wired_total > 0 and know == wired_total,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-morph-productive-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"probe": _PROBE, "gate_pass": report.get("gate_pass"), "know": know, "total": wired_total}, ensure_ascii=False))
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
