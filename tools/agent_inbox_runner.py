#!/usr/bin/env python3
"""Background runner: single-thread agent reactor + lesson inbox."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.cli.agent_inbox_ingest import ingest_inbox_payload
from casa.prisms.memory.agent_inbox import (
    ensure_inbox_dirs,
    inbox_layout,
    drain_inbox_batch,
)
from casa.prisms.memory.agent_life import AgentRuntime, agent_reactor_loop


def run(*, store_dir: Path, inbox_dir: Path, poll_ms: int = 500, persist_every: int = 8) -> None:
    store_dir = store_dir.resolve()
    layout = inbox_layout(inbox_dir)
    ensure_inbox_dirs(layout)

    def _emit(event: dict) -> None:
        print(json.dumps(event, ensure_ascii=False), flush=True)

    def _poll(runtime: AgentRuntime) -> bool:
        return drain_inbox_batch(
            runtime,
            layout,
            ingest=ingest_inbox_payload,
            emit=_emit,
        )

    print(
        json.dumps(
            {
                "status": "started",
                "mode": "reactor",
                "store_dir": str(store_dir),
                "inbox_dir": str(layout.inbox),
                "persist_every_ticks": persist_every,
                "note": "one writer per store; stop reactor before batch ingest CLI",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    try:
        agent_reactor_loop(
            store_dir,
            poll_inbox=_poll,
            poll_ms=poll_ms,
            persist_every=persist_every,
        )
    except KeyboardInterrupt:
        _emit({"status": "stopped", "reason": "host_interrupt"})


def main() -> None:
    p = argparse.ArgumentParser(description="Daemon: single-thread reactor + lesson inbox")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--inbox-dir", type=Path, required=True)
    p.add_argument("--poll-ms", type=int, default=500, help="Idle poll interval")
    p.add_argument(
        "--persist-every",
        type=int,
        default=8,
        help="Persist runtime checkpoint every N life ticks (inbox always persists)",
    )
    args = p.parse_args()
    run(
        store_dir=args.store_dir,
        inbox_dir=args.inbox_dir,
        poll_ms=args.poll_ms,
        persist_every=max(1, args.persist_every),
    )


if __name__ == "__main__":
    main()
