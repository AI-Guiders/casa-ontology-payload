#!/usr/bin/env python3
"""[LAB] CLI: external instrumentation — not agent life (see agent_life.py)."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.agent_autonomous_engine import autonomous_rehearse, rehearse_class_manifest
from casa.prisms.memory.agent_kolb_cycle import kolb_count_row_what_if, kolb_cycle, kolb_open_what_if
from casa.prisms.memory.agent_notebook import create_agent_notebook, list_agent_notebooks
from casa.prisms.shared.store_layout import default_agent_store


def main() -> None:
    p = argparse.ArgumentParser(description="[LAB] Agent notebooks + macro tick / rehearse / kolb debug")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp_nb = sub.add_parser("notebook", help="Create or list agent-owned notebooks")
    nb_sub = sp_nb.add_subparsers(dest="nb_cmd", required=True)

    sp_create = nb_sub.add_parser("create", help="Create journal shard for a notebook")
    sp_create.add_argument("--store-dir", type=Path, default=None)
    sp_create.add_argument("--id", required=True, help="Notebook id (journal domain), e.g. count-practice")
    sp_create.add_argument("--title", default="")
    sp_create.add_argument("--intro", default=None, help="Optional opening note from agent")
    sp_create.add_argument("--if-exists", default="skip", choices=("skip", "error", "append_intro"))

    sp_list = nb_sub.add_parser("list", help="List notebooks")
    sp_list.add_argument("--store-dir", type=Path, default=None)

    sp_reh = sub.add_parser("rehearse", help="Autonomous predict + retain on probe cues")
    sp_reh.add_argument("--store-dir", type=Path, default=None)
    sp_reh.add_argument("--class-dir", type=Path, default=None, help="Use class.manifest.json probe[]")
    sp_reh.add_argument("--cue", action="append", default=[], help="cue:expect pair or cue only")
    sp_reh.add_argument("--notebook", default="autonomous")
    sp_reh.add_argument("--no-create-notebook", action="store_true")
    sp_reh.add_argument("--self-verify", action="store_true", help="No teacher expect — self-confirmed only")
    sp_reh.add_argument("--no-persist", action="store_true")
    sp_reh.add_argument("--no-summary", action="store_true")

    sp_kolb = sub.add_parser("kolb", help="Autonomous Kolb cycle: what-if → sleep → re-probe")
    sp_kolb.add_argument("--store-dir", type=Path, default=None)
    sp_kolb.add_argument("--class-dir", type=Path, default=None, help="Load bundle from class dir")
    sp_kolb.add_argument("--count-row", default=None, metavar="START:END", help="e.g. 0:6 → try 0…5")
    sp_kolb.add_argument("--what-if", action="append", default=[], help="Open cue probes (repeatable)")
    sp_kolb.add_argument("--notebook", default="kolb")
    sp_kolb.add_argument("--no-create-notebook", action="store_true")
    sp_kolb.add_argument("--no-persist", action="store_true")
    sp_kolb.add_argument("--no-journal", action="store_true")

    args = p.parse_args()
    store = (args.store_dir or default_agent_store()).resolve()

    if args.cmd == "kolb":
        bundle = None
        if args.class_dir:
            manifest = json.loads((args.class_dir / "class.manifest.json").read_text(encoding="utf-8"))
            bundle_path = args.class_dir / str(manifest.get("bundle") or "kb-math-palochki-v1.bundle.json")
            if bundle_path.is_file():
                bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        kw = {
            "bundle": bundle,
            "notebook": args.notebook,
            "create_notebook": not args.no_create_notebook,
            "persist": not args.no_persist,
            "write_journal": not args.no_journal,
        }
        if args.count_row:
            part = args.count_row.split(":", 1)
            start = int(part[0])
            end = int(part[1]) if len(part) > 1 else start + 6
            rep = kolb_count_row_what_if(store, start=start, end=end, **kw)
        elif args.what_if:
            rep = kolb_open_what_if(store, cues=args.what_if, **kw)
        else:
            rep = kolb_count_row_what_if(store, start=0, end=6, **kw)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return

    if args.cmd == "notebook":
        if args.nb_cmd == "create":
            rep = create_agent_notebook(
                store,
                args.id,
                title=args.title,
                intro=args.intro,
                if_exists=args.if_exists,
            )
        else:
            rep = {"notebooks": list_agent_notebooks(store)}
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return

    cues: list[dict] = []
    if args.class_dir:
        manifest = json.loads((args.class_dir / "class.manifest.json").read_text(encoding="utf-8"))
        cues = list(manifest.get("probe") or [])
    for raw in args.cue or []:
        if ":" in raw:
            cue, expect = raw.split(":", 1)
            cues.append({"cue": cue.strip(), "expect": expect.strip()})
        else:
            cues.append({"cue": raw.strip()})

    if not cues:
        raise SystemExit("provide --class-dir or --cue")

    if args.class_dir and not args.cue:
        rep = rehearse_class_manifest(
            store,
            args.class_dir,
            notebook=args.notebook,
            create_notebook=not args.no_create_notebook,
            self_verify=args.self_verify,
            persist=not args.no_persist,
            write_summary=not args.no_summary,
        )
    else:
        rep = autonomous_rehearse(
            store,
            cues=cues,
            notebook=args.notebook,
            create_notebook=not args.no_create_notebook,
            self_verify=args.self_verify,
            persist=not args.no_persist,
            write_summary=not args.no_summary,
        )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
