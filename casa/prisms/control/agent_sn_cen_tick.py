#!/usr/bin/env python3

"""

One or more autonomous agent ticks T: field → act rollout → SN → CEN → surprise/hippo → sleep.



v0: session file `agent_session.json` in store (FPN mirror; grid wm.* later).

"""



from __future__ import annotations



from casa._paths import ensure_import_paths



ensure_import_paths()



import argparse

import json

import time

from pathlib import Path
from typing import Any

from casa.prisms.control.fpn_state import load_session, save_session

from casa.prisms.shared.store_persist import save_runtime_state

from casa.prisms.tick.orchestrator import LearningTickConfig, run_learning_tick





def run_tick(
    *,
    store_dir: Path,
    user_query: str | None,
    wm,
    config: LearningTickConfig | None = None,
    state: dict | None = None,
) -> tuple[dict, object, dict]:
    return run_learning_tick(
        store_dir=store_dir,
        user_query=user_query,
        wm=wm,
        config=config,
        state=state,
    )


def interactive_dialogue_config(*, act_rollout: bool = False) -> LearningTickConfig:
    """One macro tick T for partner dialogue — same engine as agent_sn_cen_tick, lighter act."""
    return LearningTickConfig(
        act_rollout=act_rollout,
        surprise_episode=True,
        remember_on_surprise=True,
        sleep_every=0,
        agent_self_drive=True,
        goal_from_surprise=True,
        metacog_gate=True,
        spacing_on_wake=False,
        tick_log=True,
        retro_after_sleep=True,
    )


def run_dialogue_partner_turn(
    store_dir: Path,
    *,
    user_query: str,
    wm,
    state: dict | None = None,
    config: LearningTickConfig | None = None,
) -> tuple[str, dict[str, Any], object, dict]:
    """Partner line → one agent-life tick; REPL is a mode, not a second contour."""
    report, wm_next, state_out = run_tick(
        store_dir=store_dir,
        user_query=user_query,
        wm=wm,
        state=state,
        config=config or interactive_dialogue_config(),
    )
    dialogue = report.get("dialogue") or {}
    reply = str(dialogue.get("reply_text") or "").strip()
    if not reply and dialogue.get("outbound"):
        reply = str(dialogue["outbound"][-1].get("text") or "").strip()
    if not reply:
        last = dialogue.get("last_outbound") or {}
        reply = str(last.get("text") or "").strip()
    return reply or "(молчит)", report, wm_next, state_out


def main() -> None:

    p = argparse.ArgumentParser()

    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))

    p.add_argument("--query", default=None, help="External query; if omitted uses WM goal or probe")

    p.add_argument("--ticks", type=int, default=1, help="Macro ticks T to run in sequence")

    p.add_argument("--goal", default=None, help="Seed WM goal before first tick")

    p.add_argument("--out", type=Path, default=None)

    p.add_argument(

        "--no-write-field",

        action="store_true",

        help="Skip field_state.json persist (session still saved)",

    )

    p.add_argument("--no-act-rollout", action="store_true", help="Skip NCA act rollout on memory lattice")

    p.add_argument("--sleep-every", type=int, default=0, help="Run sleep every N ticks when hippo has episodes")

    p.add_argument(

        "--sleep-on-value",

        type=float,

        default=1.0,

        help="Run sleep when control.value >= threshold and hippo has episodes",

    )

    p.add_argument("--no-surprise-episode", action="store_true", help="Skip hippo episode on predict surprise")

    p.add_argument("--no-remember-surprise", action="store_true", help="Skip agent_remember on high surprise")

    p.add_argument("--kolb-session", type=Path, default=None, help="Optional Kolb session JSON (batch hook)")

    p.add_argument(
        "--no-retro-on-wake",
        action="store_true",
        help="Skip Scrum retrospective (keep/stop/try) before first tick (default: run on wake)",
    )

    p.add_argument(
        "--body-check-on-wake",
        action="store_true",
        help="Run subject diagnostics snapshot before first tick (ADR-0037)",
    )

    p.add_argument(
        "--no-sync-ltm",
        action="store_true",
        help="Skip compact_persist ltm/ sync on final field save (faster tick batch)",
    )

    args = p.parse_args()



    kolb_session = None

    if args.kolb_session:

        kolb_session = json.loads(args.kolb_session.read_text(encoding="utf-8"))



    config = LearningTickConfig(
        act_rollout=not args.no_act_rollout,
        surprise_episode=not args.no_surprise_episode,
        remember_on_surprise=not args.no_remember_surprise,
        sleep_every=max(0, int(args.sleep_every)),
        sleep_on_value=float(args.sleep_on_value),
        kolb_session=kolb_session,
        agent_self_drive=True,
        goal_from_surprise=True,
        metacog_gate=True,
        spacing_on_wake=True,
        tick_log=True,
        retro_after_sleep=True,
    )



    store = args.store_dir.resolve()

    if args.body_check_on_wake:
        from casa.cli.ingest_state import resolve_ingest_state
        from casa.domain.subject_diagnostics import persist_diagnostics_snapshot, run_subject_diagnostics
        from casa.prisms.shared.store_lock import store_session_lock

        with store_session_lock(store, holder="subject:wake_body_check"):
            state = resolve_ingest_state(store, None)
            wm_wake = load_session(store)
            diag = run_subject_diagnostics(state, store, wm=wm_wake)
            persist_diagnostics_snapshot(store, diag)

    if not args.no_retro_on_wake:
        from casa.domain.subject_retrospective import maybe_run_retrospective_on_wake
        from casa.prisms.shared.store_lock import store_session_lock

        with store_session_lock(store, holder="subject:wake_retro"):
            maybe_run_retrospective_on_wake(store, force=False)
            from casa.domain.dialogue_tick import dialogue_initiate_from_wake_retro

            dialogue_initiate_from_wake_retro(store)

    wm = load_session(store)

    if args.goal:

        wm.goal = args.goal.strip()[:240]

        wm.mode = "kb_query"



    history: list[dict] = []

    tick_state: dict | None = None

    import sys

    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    for tick_i in range(max(1, args.ticks)):

        t0 = time.perf_counter()

        row, wm, tick_state = run_tick(

            store_dir=store,

            user_query=args.query if len(history) == 0 else None,

            wm=wm,

            state=tick_state,

            config=config if len(history) == 0 else LearningTickConfig(

                act_rollout=config.act_rollout,

                act_device=config.act_device,

                surprise_episode=config.surprise_episode,

                surprise_min_value=config.surprise_min_value,

                remember_on_surprise=config.remember_on_surprise,

                remember_min_value=config.remember_min_value,

                retain_on_verified_predict=config.retain_on_verified_predict,

                sleep_every=config.sleep_every,

                sleep_on_value=config.sleep_on_value,

                kolb_session=None,

                agent_self_drive=config.agent_self_drive,

                goal_from_surprise=config.goal_from_surprise,

                metacog_gate=config.metacog_gate,

                spacing_on_wake=False,

                tick_log=config.tick_log,

                retro_after_sleep=config.retro_after_sleep,

            ),

        )

        row["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        history.append(row)

        args.query = None

        promote = (row.get("agent_self_drive") or {}).get("skill_promote")

        dialogue = row.get("dialogue") or {}

        last_out = (dialogue.get("last_outbound") or {}).get("text", "")[:120]

        print(

            json.dumps(

                {

                    "tick": tick_i + 1,

                    "elapsed_ms": row["elapsed_ms"],

                    "wm_tick": wm.tick,

                    "step_index": wm.step_index,

                    "step_capability": wm.step_capability,

                    "skill_promote": promote,

                    "dialogue_outbound": last_out or None,

                },

                ensure_ascii=False,

            ),

            file=sys.stderr,

            flush=True,

        )



    last_state = tick_state



    if not wm.goal and history:

        last_q = history[-1].get("query")

        if last_q:

            wm.goal = str(last_q)[:240]



    save_session(store, wm)

    persist: dict | None = None

    if not args.no_write_field and last_state is not None:

        persist = save_runtime_state(
            store,
            last_state,
            sync_ltm_on_save=not args.no_sync_ltm,
        )



    doc = {

        "schema_version": 1,

        "store": str(store),

        "ticks_run": len(history),

        "wm": wm.to_dict(),

        "history": history,

        "persist": persist,

    }

    text = json.dumps(doc, ensure_ascii=False, indent=2)

    if args.out:

        args.out.parent.mkdir(parents=True, exist_ok=True)

        args.out.write_text(text, encoding="utf-8")

    import sys



    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(text)





if __name__ == "__main__":

    main()

