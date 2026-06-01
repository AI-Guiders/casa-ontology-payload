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



from casa.prisms.control.fpn_state import load_session, save_session

from casa.prisms.shared.store_persist import save_runtime_state

from casa.prisms.tick.orchestrator import LearningTickConfig, run_learning_tick





def run_tick(

    *,

    store_dir: Path,

    user_query: str | None,

    wm,

    config: LearningTickConfig | None = None,

) -> tuple[dict, object, dict]:

    return run_learning_tick(

        store_dir=store_dir,

        user_query=user_query,

        wm=wm,

        config=config,

    )





def main() -> None:

    p = argparse.ArgumentParser()

    p.add_argument("--store-dir", type=Path, default=Path("lab/agent-stores/language-agent-lab"))

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

    )



    store = args.store_dir.resolve()

    wm = load_session(store)

    if args.goal:

        wm.goal = args.goal.strip()[:240]

        wm.mode = "kb_query"



    history: list[dict] = []

    last_state: dict | None = None

    for _ in range(max(1, args.ticks)):

        t0 = time.perf_counter()

        row, wm, last_state = run_tick(

            store_dir=store,

            user_query=args.query if len(history) == 0 else None,

            wm=wm,

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

            ),

        )

        row["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        history.append(row)

        args.query = None



    if not wm.goal and history:

        last_q = history[-1].get("query")

        if last_q:

            wm.goal = str(last_q)[:240]



    save_session(store, wm)

    persist: dict | None = None

    if not args.no_write_field and last_state is not None:

        persist = save_runtime_state(store, last_state)



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

