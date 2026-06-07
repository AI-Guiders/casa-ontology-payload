"""Intent Prism — CLI entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from casa.prisms.memory.agent_prism import load_agent_prism, save_agent_prism
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_persist import save_runtime_state

from .lifecycle import intent_on_sleep_boundary
from .policy import list_agent_tracts, list_hypotheses
from .promote import promote_intent_hypothesis


def main() -> None:
    p = argparse.ArgumentParser(description="Intent Prism — agent tract hypotheses (ADR-0057)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--write", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List scratch hypotheses")
    sub.add_parser("list-tracts", help="List agent.tract.* emergent/promoted")

    sp_promote = sub.add_parser("promote-hypothesis")
    sp_promote.add_argument("--hypothesis-id", required=True)
    sp_promote.add_argument("--target", choices=("agent", "canon"), default="agent")
    sp_promote.add_argument("--slug", default=None)
    sp_promote.add_argument("--compose-mode", default="field")

    sub.add_parser("sleep-consolidate")

    args = p.parse_args()
    store_dir = args.store_dir.resolve()
    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]
    load_agent_prism(store_dir, state)
    write = bool(args.write)

    if args.cmd == "list":
        out = {"hypotheses": list_hypotheses(state)}
    elif args.cmd == "list-tracts":
        out = {"agent_tracts": list_agent_tracts(state)}
    elif args.cmd == "promote-hypothesis":
        out = promote_intent_hypothesis(
            state,
            args.hypothesis_id,
            target=args.target,
            slug=args.slug,
            compose_mode=args.compose_mode,
            store_dir=store_dir,
            persist=write,
        )
    elif args.cmd == "sleep-consolidate":
        out = intent_on_sleep_boundary(state, store_dir if write else None)
    else:
        out = {"error": "unknown cmd"}

    if write and args.cmd == "sleep-consolidate":
        save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)
    elif write and args.cmd not in ("promote-hypothesis",):
        save_agent_prism(store_dir, state)
        save_runtime_state(store_dir, state, force=True, thin=True, save_agent=True)

    print(json.dumps(out, ensure_ascii=False, indent=2))
