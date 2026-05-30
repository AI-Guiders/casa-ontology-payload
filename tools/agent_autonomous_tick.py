#!/usr/bin/env python3
"""
One or more autonomous agent ticks T: field → SN → CEN → FPN session update.

v0: session file `agent_session.json` in store (FPN mirror; grid wm.* later).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from canonical import CANONICAL_FIELD_MIN_VOTES  # type: ignore
from fpn_state import (  # type: ignore
    effective_user_query,
    fpn_after_cen,
    load_session,
    salience_mode_bias,
    save_session,
)
from sn_cen_infer import _run_from_field  # type: ignore
from sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict  # type: ignore


def run_tick(
    *,
    store_dir: Path,
    user_query: str | None,
    wm,
) -> tuple[dict, object]:
    field_path = store_dir / "field_state.json"
    _, bundle, decoded, recovery, wall_ms, state = _run_from_field(
        field_path, store_dir, min_votes=CANONICAL_FIELD_MIN_VOTES
    )
    digest = digest_from_decoded(decoded)
    bias = salience_mode_bias(wm, digest.concept_ids)
    gated = sn_route(digest, bundle=bundle, wm_mode=wm.mode, wm_salience_bias=bias)
    q = effective_user_query(wm, user_query)
    task = cen_plan(gated, bundle=bundle, user_query=q)
    wm_next = fpn_after_cen(wm, task, user_query=q)
    report = {
        "tick": wm_next.tick,
        "query": q,
        "wall_ms": round(wall_ms, 2),
        "field_version": state.get("field_version"),
        "recovery_concepts_f1": (recovery or {}).get("concepts", {}).get("f1"),
        "sn_mode": gated.gate.mode,
        "cen": task_to_dict(task, fpn=wm_next.to_dict()),
    }
    return report, wm_next


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, default=Path("examples/agent-stores/language-agent-lab-v0"))
    p.add_argument("--query", default=None, help="External query; if omitted uses WM goal or probe")
    p.add_argument("--ticks", type=int, default=1, help="Macro ticks T to run in sequence")
    p.add_argument("--goal", default=None, help="Seed WM goal before first tick")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    wm = load_session(store)
    if args.goal:
        wm.goal = args.goal.strip()[:240]
        wm.mode = "kb_query"

    history: list[dict] = []
    for _ in range(max(1, args.ticks)):
        t0 = time.perf_counter()
        row, wm = run_tick(store_dir=store, user_query=args.query if len(history) == 0 else None, wm=wm)
        row["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        history.append(row)
        args.query = None  # follow-up ticks use WM goal

    if not wm.goal and history:
        last_q = history[-1].get("query")
        if last_q:
            wm.goal = str(last_q)[:240]

    save_session(store, wm, extra={"last_tick_reports": len(history)})
    doc = {"schema_version": 1, "store": str(store), "ticks_run": len(history), "wm": wm.to_dict(), "history": history}
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)


if __name__ == "__main__":
    main()
