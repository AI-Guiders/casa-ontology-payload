#!/usr/bin/env python3
"""Print partner/subject turns for nositel gate scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import default_store, setup_probe_imports


def main() -> None:
    setup_probe_imports()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.tick.semantic_read import route_kb_read

    p = argparse.ArgumentParser()
    p.add_argument("--store", default="von-neumann")
    p.add_argument(
        "--plan",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "lessons/ru-text-tract/data/nositel-gate-plan-v1.json",
    )
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    store = default_store(args.store)
    state = resolve_ingest_state(store, None)
    bundle = load_store_bundles(store)
    wm = WorkingMemory()

    for i, case in enumerate(plan.get("scenarios") or [], 1):
        q = str(case.get("query") or "")
        intent = route_kb_read(q, bundle).intent
        ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
        reply = compose_subject_utterance(q, ctx)
        top = [str(b.get("concept_id") or "") for b in ctx.blocks[:4]]
        print("=" * 60)
        print(f"[{i}] {case.get('scenario_id')} ({case.get('dimension')}) intent={intent}")
        print("ПАРТНЁР:")
        print(q)
        print("НЕЙМАНН:")
        print(reply)
        print("bind:", ", ".join(top))
        print()


if __name__ == "__main__":
    main()
