#!/usr/bin/env python3
"""Query skill_trace — situation / skill / outcome (ADR-0037 / ADR-0038)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.domain.skill_trace import query_skill_trace, skill_trace_panel


def main() -> int:
    p = argparse.ArgumentParser(description="Query skill application trace")
    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))
    p.add_argument("--goal-id", default="")
    p.add_argument("--skill", default="")
    p.add_argument("--outcome", default="", help="verified | surprise | fail | promoted")
    p.add_argument("--limit", type=int, default=16)
    p.add_argument("--summary", action="store_true", help="Panel aggregates instead of rows")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    if args.summary:
        doc = skill_trace_panel(store, limit=max(1, args.limit))
    else:
        rows = query_skill_trace(
            store,
            goal_id=args.goal_id,
            skill=args.skill,
            outcome=args.outcome,
            limit=max(1, args.limit),
        )
        doc = {
            "schema_version": 2,
            "tool": "skill_trace_query",
            "store": str(store),
            "journal": "agent_journal.db",
            "filters": {
                "goal_id": args.goal_id or None,
                "skill": args.skill or None,
                "outcome": args.outcome or None,
            },
            "count": len(rows),
            "rows": rows,
        }

    text = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
