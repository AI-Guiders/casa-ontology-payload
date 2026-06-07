#!/usr/bin/env python3
"""Literature RC micro-class (Hwang passage-in-context)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports
from probe_nositel_gate_ru import _scenario_pass

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-literature/data/literature-rc-plan.json"
_PROBE = "probe_literature_rc_ru"


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
    args = p.parse_args()

    plan = json.loads(_PLAN.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    know = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            if not case.get("wired", True):
                continue
            q = str(case.get("query") or "")
            intent = route_kb_read(q, bundle, store_dir=store).intent
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            paste = paste_ratio_against_blocks(reply, ctx.blocks)
            ok, detail = _scenario_pass(case, reply=reply, query_intent=intent, paste_ratio=paste)
            if ok:
                know += 1
            items.append({"query": q[:120], "verdict": "know" if ok else "wrong", **detail})

        total = len(items)
        report = {
            "store_id": store.name,
            "probe": _PROBE,
            "plan": str(_PLAN),
            "know": know,
            "total": total,
            "items": items,
            "gate_pass": total > 0 and know == total,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-literature-rc-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"probe": _PROBE, "gate_pass": report.get("gate_pass"), "know": know, "total": total}, ensure_ascii=False))
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
