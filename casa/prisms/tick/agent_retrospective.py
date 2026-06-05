#!/usr/bin/env python3
"""Run subject retrospective (Scrum 3Q) on skill_trace."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.domain.subject_retrospective import maybe_run_retrospective, retro_panel
from casa.prisms.shared.store_lock import store_session_lock


def main() -> int:
    p = argparse.ArgumentParser(description="Subject retrospective: keep / stop / try")
    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))
    p.add_argument("--window", type=int, default=16)
    p.add_argument("--force", action="store_true", help="Run even with fewer skill_trace entries")
    p.add_argument("--panel-only", action="store_true", help="Show last retro without recomputing")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    with store_session_lock(store, holder="subject:retro"):
        if args.panel_only:
            doc = retro_panel(store)
        else:
            retro = maybe_run_retrospective(
                store,
                window=max(4, args.window),
                force=args.force,
            )
            if retro is None:
                doc = {
                    "schema_version": 1,
                    "tool": "subject_retrospective",
                    "skipped": True,
                    "reason": "insufficient skill_trace entries",
                    "panel": retro_panel(store),
                }
            else:
                doc = retro

    text = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
