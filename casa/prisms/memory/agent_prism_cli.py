#!/usr/bin/env python3
"""CLI for agent-owned prism — lattices + NCA (library in agent_prism.py)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from casa.domain.prism_ids import PRISM_AGENT
from casa.domain.prism_wire import prism_agent, set_active_prism
from casa.prisms.memory.agent_prism import (
    agent_lattices,
    create_agent_lattice,
    delete_agent_lattice,
    ensure_agent_prism,
    list_agent_lattices,
    load_agent_prism,
    place_agent_token,
    read_agent_lattice,
    save_agent_prism,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state, save_field_state


def main() -> None:
    p = argparse.ArgumentParser(description="Agent-owned prism — lattices + NCA outside profile ltm/")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_store(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--store-dir", type=Path, required=True)

    sp_create = sub.add_parser("create-lattice")
    add_store(sp_create)
    sp_create.add_argument("--id", required=True, dest="lattice_id")
    sp_create.add_argument("--width", type=int, default=32)
    sp_create.add_argument("--height", type=int, default=32)
    sp_create.add_argument("--z-level", type=int, default=0)
    sp_create.add_argument("--write", action="store_true")

    sp_place = sub.add_parser("place")
    add_store(sp_place)
    sp_place.add_argument("--lattice", required=True)
    sp_place.add_argument("--token", required=True)
    sp_place.add_argument("--x", type=int, default=None)
    sp_place.add_argument("--y", type=int, default=None)
    sp_place.add_argument("--copies", type=int, default=1)
    sp_place.add_argument("--write", action="store_true")

    sp_list = sub.add_parser("list")
    add_store(sp_list)

    sp_read = sub.add_parser("read")
    add_store(sp_read)
    sp_read.add_argument("--lattice", required=True)

    sp_delete = sub.add_parser("delete-lattice")
    add_store(sp_delete)
    sp_delete.add_argument("--lattice", required=True)
    sp_delete.add_argument("--write", action="store_true")

    sp_train = sub.add_parser("train-nca")
    add_store(sp_train)
    sp_train.add_argument("--lattice", required=True)
    sp_train.add_argument("--epochs", type=int, default=None)
    sp_train.add_argument("--device", default="auto")
    sp_train.add_argument("--write", action="store_true")

    sp_save = sub.add_parser("save")
    add_store(sp_save)

    sp_load = sub.add_parser("load")
    add_store(sp_load)

    sp_active = sub.add_parser("activate")
    add_store(sp_active)
    sp_active.add_argument("--lattice", required=True)
    sp_active.add_argument("--write", action="store_true")

    args = p.parse_args()
    store_dir = args.store_dir.resolve()
    fs = field_state_path(store_dir)
    state = ensure_prisms(load_field_state(fs)) if fs.is_file() else ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    load_agent_prism(store_dir, state)

    out: Any = None

    if args.cmd == "create-lattice":
        out = create_agent_lattice(
            state,
            args.lattice_id,
            width=args.width,
            height=args.height,
            z_level=args.z_level,
        )
    elif args.cmd == "place":
        out = place_agent_token(state, args.lattice, args.token, x=args.x, y=args.y, copies=args.copies)
    elif args.cmd == "list":
        out = {"lattices": list_agent_lattices(state), "active_prism": PRISM_AGENT}
    elif args.cmd == "read":
        out = read_agent_lattice(state, args.lattice)
    elif args.cmd == "delete-lattice":
        ok = delete_agent_lattice(state, args.lattice)
        out = {"deleted": ok, "lattice_id": args.lattice}
        if not ok:
            raise SystemExit(1)
    elif args.cmd == "train-nca":
        from casa.prisms.memory.agent_prism_nca import train_agent_lattice_nca

        out = train_agent_lattice_nca(state, store_dir, args.lattice, epochs=args.epochs, device=args.device)
    elif args.cmd == "save":
        out = save_agent_prism(store_dir, state)
    elif args.cmd == "load":
        out = load_agent_prism(store_dir, state)
    elif args.cmd == "activate":
        from casa.prisms.memory.agent_prism import safe_agent_lattice_id

        safe_agent_lattice_id(args.lattice)
        if args.lattice not in agent_lattices(state):
            raise SystemExit(f"unknown agent lattice: {args.lattice}")
        prism_agent(state)["active_lattice"] = args.lattice
        set_active_prism(state, PRISM_AGENT)
        state["sn"] = {**(state.get("sn") or {}), "active_lattice": args.lattice}
        out = {"active_prism": PRISM_AGENT, "active_lattice": args.lattice}

    write = getattr(args, "write", False) or args.cmd in ("save",)
    if write and args.cmd != "load":
        save_agent_prism(store_dir, state)
        if fs.parent.exists():
            save_field_state(fs, state, compact=True)

    print(json.dumps(out, ensure_ascii=False, indent=2))


def field_state_path(store_dir: Path) -> Path:
    from casa.prisms.shared.store_layout import field_state_path as _path

    return _path(store_dir)


if __name__ == "__main__":
    main()
