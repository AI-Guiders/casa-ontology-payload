#!/usr/bin/env python3
"""Host: wake unified agent-life reactor (continuous SN/CEN + partner + teacher inbox)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.cli.life_daemon import default_teacher_inbox
from casa.prisms.memory.agent_life import agent_wake, unified_agent_reactor_loop
from casa.prisms.shared.store_layout import default_agent_store


def main() -> None:
    p = argparse.ArgumentParser(
        description="Wake living agent — unified reactor (partner channel + teacher inbox + idle ticks)"
    )
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument(
        "--inbox-dir",
        type=Path,
        default=None,
        help="Teacher lesson inbox (default: {store}/teacher_inbox)",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="[lab/CI] one internal quantum then exit (legacy curiosity path)",
    )
    p.add_argument("--no-persist", action="store_true")
    p.add_argument("--poll-ms", type=int, default=500)
    args = p.parse_args()

    store = (args.store_dir or default_agent_store()).resolve()

    if args.once:
        rep = agent_wake(store, stop_after=1, persist=not args.no_persist)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return

    inbox = (args.inbox_dir or default_teacher_inbox(store)).resolve()
    inbox.mkdir(parents=True, exist_ok=True)

    print(
        json.dumps(
            {
                "status": "starting",
                "store_dir": str(store),
                "teacher_inbox": str(inbox),
                "note": "partner speech: body/voice; teacher inbox only for curriculum",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    try:
        from casa.cli.agent_inbox_ingest import ingest_inbox_payload
        from casa.prisms.memory.agent_inbox import drain_inbox_batch, ensure_inbox_dirs, inbox_layout

        layout = inbox_layout(inbox)
        ensure_inbox_dirs(layout)

        def _poll(runtime):
            return drain_inbox_batch(
                runtime,
                layout,
                ingest=ingest_inbox_payload,
                emit=lambda ev: print(json.dumps(ev, ensure_ascii=False), flush=True),
            )

        unified_agent_reactor_loop(
            store,
            poll_inbox=_poll,
            poll_ms=args.poll_ms,
        )
    except KeyboardInterrupt:
        print(json.dumps({"status": "stopped", "reason": "host_interrupt"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
