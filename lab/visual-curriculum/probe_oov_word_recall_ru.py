#!/usr/bin/env python3
"""L2 OOV remember → recall (ADR-0049)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PROBE = "probe_oov_word_recall_ru"
_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/oov-recall-plan.json"


def main() -> None:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.memory.agent_memory_ops import agent_remember
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    cases = [c for c in plan.get("cases") or [] if c.get("wired", True)]
    store = default_store(args.store)
    items: list[dict] = []
    know = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in cases:
            novel = str(case.get("novel_surface") or "")
            remember_cue = f"Запомни слово: {novel}."
            recall_cue = str(case.get("cue") or f"Что означает слово {novel}?")
            agent_remember(
                store,
                state,
                {
                    "kind": "observation",
                    "text": remember_cue,
                    "concepts": [f"lang.word.{novel}"],
                    "tags": ["oov", "probe"],
                },
            )
            ctx = gather_subject_dialogue_blocks(recall_cue, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(recall_cue, ctx).lower()
            expect = [str(x).lower() for x in (case.get("expect_in_reply") or [novel[:5]])]
            ok = all(tok in reply for tok in expect)
            if ok:
                know += 1
            items.append(
                {
                    "case_id": case.get("case_id"),
                    "novel_surface": novel,
                    "verdict": "know" if ok else "wrong",
                    "reply_excerpt": reply[:160],
                }
            )

        total = len(items)
        report = {
            "store_id": store.name,
            "probe": _PROBE,
            "plan": str(args.plan),
            "total": total,
            "know": know,
            "wrong": total - know,
            "items": items,
            "gate_pass": total > 0 and know == total,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-oov-word-recall-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"probe": _PROBE, "gate_pass": report.get("gate_pass"), "know": know, "total": total}, ensure_ascii=False))
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
