#!/usr/bin/env python3
"""Subject body check CLI — three diagnostic panels on wake (ADR-0037)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.subject_diagnostics import persist_diagnostics_snapshot, run_subject_diagnostics
from casa.prisms.control.fpn_state import load_session
from casa.prisms.shared.store_lock import store_session_lock


def main() -> int:
    p = argparse.ArgumentParser(description="Subject diagnostics: experience / body / memory")
    p.add_argument("--store-dir", type=Path, default=Path("agents/von-neumann"))
    p.add_argument("--include-nca", action="store_true", help="Scan stale NCA shards (slow on large store)")
    p.add_argument("--experience-limit", type=int, default=8)
    p.add_argument("--save", action="store_true", help="Write last_diagnostics to agent_session.json")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    with store_session_lock(store, holder="subject:body_check"):
        state = resolve_ingest_state(store, None)
        wm = load_session(store)
        report = run_subject_diagnostics(
            state,
            store,
            wm=wm,
            include_nca=args.include_nca,
            experience_limit=max(1, args.experience_limit),
        )
        if args.save:
            persist_diagnostics_snapshot(store, report)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
