"""Working Memory Prism — CLI entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path
from casa.prisms.shared.store_persist import save_runtime_state

from .graph import place_wm_edge
from .lattice import list_wm_state, prune_wm_lattice, spawn_wm_lattice
from .lifecycle import wm_on_sleep_boundary
from .promote import promote_wm_edge, promote_wm_edge_to_canon


def main() -> None:
    p = argparse.ArgumentParser(description="Working Memory Prism (ADR-0055)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_store(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--store-dir", type=Path, required=True)

    sp_list = sub.add_parser("list")
    add_store(sp_list)

    sp_promote = sub.add_parser("promote-edge")
    add_store(sp_promote)
    sp_promote.add_argument("--edge-id", required=True)
    sp_promote.add_argument("--relation", default="link")
    sp_promote.add_argument("--write", action="store_true")

    sp_canon = sub.add_parser("promote-canon")
    add_store(sp_canon)
    sp_canon.add_argument("--edge-id", required=True)
    sp_canon.add_argument("--law-label", default="wm_law")
    sp_canon.add_argument("--write", action="store_true")

    sp_prune = sub.add_parser("prune")
    add_store(sp_prune)
    sp_prune.add_argument("--tick", type=int, default=0)
    sp_prune.add_argument("--aggressive", action="store_true")
    sp_prune.add_argument("--write", action="store_true")

    sp_sleep = sub.add_parser("sleep-consolidate")
    add_store(sp_sleep)
    sp_sleep.add_argument("--write", action="store_true")

    sp_spawn = sub.add_parser("spawn")
    add_store(sp_spawn)
    sp_spawn.add_argument("--topic", default="scratch")
    sp_spawn.add_argument("--tick", type=int, default=0)
    sp_spawn.add_argument("--write", action="store_true")

    args = p.parse_args()
    store_dir = args.store_dir.resolve()
    fs = field_state_path(store_dir)
    state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})

    from casa.prisms.memory.agent_prism import load_agent_prism

    load_agent_prism(store_dir, state)

    if args.cmd == "list":
        out = list_wm_state(state)
    elif args.cmd == "promote-edge":
        out = promote_wm_edge(store_dir, state, args.edge_id, relation_kind=args.relation, persist=args.write)
    elif args.cmd == "promote-canon":
        out = promote_wm_edge_to_canon(store_dir, state, args.edge_id, law_label=args.law_label, persist=args.write)
    elif args.cmd == "prune":
        out = prune_wm_lattice(state, tick=args.tick, store_dir=store_dir, aggressive=args.aggressive)
    elif args.cmd == "sleep-consolidate":
        out = wm_on_sleep_boundary(state, store_dir)
    elif args.cmd == "spawn":
        out = {"lattice_id": spawn_wm_lattice(state, tick=args.tick, topic_slug=args.topic)}
    else:
        raise SystemExit(f"unknown cmd: {args.cmd}")

    write = getattr(args, "write", False)
    if write and args.cmd not in ("promote-edge", "promote-canon"):
        save_runtime_state(store_dir, state, force=True)

    print(json.dumps(out, ensure_ascii=False, indent=2))
