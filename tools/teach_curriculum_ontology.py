#!/usr/bin/env python3
"""Teach Built-In concept catalog + agent-concept-graph on a living agent store."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.memory.concept_built_in import ensure_concept_built_in
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import agent_store_dir, default_agent_store
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def _store_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    return agent_store_dir(arg).resolve()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann", help="Store id or path")
    p.add_argument("--base", action="store_const", const="base", dest="profile", help="~280 concept base net")
    p.add_argument("--wide", action="store_const", const="wide", dest="profile", help="Wide concept net (opt-in)")
    p.set_defaults(profile="base")
    p.add_argument("--dry-run", action="store_true", help="Report only; do not persist")
    p.add_argument("--force", action="store_true", help="Re-teach even if bundle hash matches")
    args = p.parse_args()

    store = _store_dir(args.store)
    if not store.is_dir():
        print(json.dumps({"error": f"store not found: {store}"}, ensure_ascii=False), file=sys.stderr)
        return 1

    with store_session_lock(store, holder="teach_curriculum_ontology"):
        boot = boot_store(store, prefer_field_state=True)
        state = ensure_prisms(boot["state"])
        rep = ensure_concept_built_in(state, profile=args.profile, force=args.force)
        if not args.dry_run and not rep.get("skipped"):
            mark_runtime_dirty(state)
            save_runtime_state(store, state, force=True, thin=True, save_agent=True)
        print(json.dumps({"store": str(store), **rep}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
