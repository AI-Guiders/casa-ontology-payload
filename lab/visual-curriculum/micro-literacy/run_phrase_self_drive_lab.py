#!/usr/bin/env python3
"""Macro-tick phrase self-drive: trial plan → per-word analytic → compose (ADR-0035)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument(
        "--goal",
        default="goal.read.phrase#lang.event.transitive.wash.v0",
        help="goal_id with optional #event_id suffix",
    )
    args = p.parse_args()

    from casa.domain.emergent_promote import promote_from_probe_report, promote_routes_from_probe_report
    from casa.domain.mastery_gate import record_gate_attempt, skill_gate_id
    from casa.domain.plan_tick import PlanTick
    from casa.domain.wake_decompose import current_word_focus, init_phrase_queue, phrase_event_id_from_goal
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.control.tick import ControlExtensions
    from casa.prisms.tick.agent_self_drive_tick import (
        maybe_agent_self_drive_tick,
        maybe_promote_skill_on_verify,
        prepare_phrase_agent_tick,
    )

    lab = lab_session(LITERACY, micro_dir=_MICRO, store_id=args.store)
    lab.load()
    state = lab.state

    for report in (
        {"probe": "analytic-read-corpus-r1", "items": [{"verdict": "analytic_know"}]},
        {"probe": "phrase-compose-pilot", "phrase_know": True, "verdict": "phrase_know"},
    ):
        promote_from_probe_report(state, report, tick=1)
        promote_from_probe_report(state, report, tick=2)
        promote_routes_from_probe_report(state, report, min_mastery_streak=2)

    wm = WorkingMemory(goal_id=args.goal)
    mem_prep: dict = {"plan_tick": {}, "routing_chain": None}
    prepare_phrase_agent_tick(state, wm, mem_prep)
    event_id = phrase_event_id_from_goal(args.goal)
    init_phrase_queue(state, args.goal)
    words_done: list[str] = []
    analytic_gid = skill_gate_id("skill.read.analytic")

    with patch(
        "casa.prisms.visual.analytic_read.verify_analytic_read_frame",
        return_value=True,
    ):
        while True:
            focus = current_word_focus(state, goal_id=args.goal)
            if not focus:
                break
            wm.step_capability = "skill.read.analytic"
            wm.step_index = 0
            wm.step_focus = focus
            mem_prep["plan_tick"] = PlanTick.from_wm(wm).to_dict()
            record_gate_attempt(state, analytic_gid, passed=True, tick=wm.tick)
            record_gate_attempt(state, analytic_gid, passed=True, tick=wm.tick + 1)
            rep = maybe_promote_skill_on_verify(
                state,
                wm=wm,
                mem_prep=mem_prep,
                knowledge={"predict_verdict": "pass", "hypothesis": event_id},
            )
            words_done.append(focus)
            dec = state.get("wake_decompose") or {}
            if int(dec.get("word_index") or 0) >= len(dec.get("words") or []) - 1:
                break

        wm.step_capability = "skill.compose.slots"
        wm.step_index = 1
        mem_prep["plan_tick"] = PlanTick.from_wm(wm).to_dict()
        compose_gid = skill_gate_id("skill.compose.slots")
        record_gate_attempt(state, compose_gid, passed=True, tick=wm.tick)
        record_gate_attempt(state, compose_gid, passed=True, tick=wm.tick + 1)
        maybe_promote_skill_on_verify(
            state,
            wm=wm,
            mem_prep=mem_prep,
            knowledge={"predict_verdict": "pass", "hypothesis": event_id},
        )

        control = ControlExtensions(
            predicted=(),
            surprise=(),
            prediction_error=0.0,
            dan_mask=(),
            sparse_ratio=0.0,
            masked_digest=(),
            value=0.5,
        )
        macro = maybe_agent_self_drive_tick(
            lab.store_dir,
            state,
            wm=wm,
            control=control,
            mem_prep=mem_prep,
        )

    lab.save(sync_ltm=False)
    dec = state.get("wake_decompose") or {}
    word_count = len(dec.get("words") or [])
    out = {
        "goal": args.goal,
        "event_id": event_id,
        "words_analytic": words_done,
        "word_count": word_count,
        "macro_tick": macro is not None,
        "wake_complete": int(dec.get("word_index") or 0) >= word_count - 1,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["wake_complete"] and len(words_done) == word_count else 1)


if __name__ == "__main__":
    main()
