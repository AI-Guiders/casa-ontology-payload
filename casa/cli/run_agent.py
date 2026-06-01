#!/usr/bin/env python3
"""Host: wake agent process. Curiosity is agent-owned — no host commands for Kolb."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.agent_life import agent_wake
from casa.prisms.shared.store_layout import default_agent_store


def main() -> None:
    p = argparse.ArgumentParser(
        description="Wake living agent (host starts process; agent drives own curiosity loop)"
    )
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument(
        "--once",
        action="store_true",
        help="[lab/CI] one internal quantum then exit; prod: omit — run until Ctrl+C",
    )
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args()

    rep = agent_wake(
        args.store_dir or default_agent_store(),
        stop_after=1 if args.once else None,
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
