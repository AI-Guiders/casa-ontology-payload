#!/usr/bin/env python3
"""CLI: L3_phrase monolith → L3_phrase_XX shards (kernel API)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.prisms.memory.l3_remigrate import ensure_l3_sharded_for_export, needs_l3_remigrate, remigrate_l3_from_monolith
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.store_layout import field_state_path


def main() -> None:
    p = argparse.ArgumentParser(description="Remigrate L3_phrase monolith to shards")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--write", action="store_true", help="save field_state.json")
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--import-legacy-l3",
        action="store_true",
        help="copy L3_phrase lattice from field_state.legacy.json before remigrate",
    )
    p.add_argument("--compact", action="store_true", help="flush ltm/ after remigrate")
    args = p.parse_args()

    fs = field_state_path(args.store_dir)
    if not fs.is_file():
        raise SystemExit(f"no field_state: {fs}")
    state = ensure_prisms(load_field_state(fs, store_dir=args.store_dir))

    if args.import_legacy_l3:
        import json

        from casa.prisms.memory.phrase_shard import LEGACY_L3
        from casa.prisms.memory.memory_prisms import memory_lattices
        from casa.prisms.shared.prism_state import prism_memory

        leg_path = args.store_dir / "field_state.legacy.json"
        if not leg_path.is_file():
            raise SystemExit(f"no legacy: {leg_path}")
        leg = ensure_prisms(json.loads(leg_path.read_text(encoding="utf-8")))
        l3 = memory_lattices(leg).get(LEGACY_L3)
        if not l3:
            raise SystemExit(f"{LEGACY_L3} not in legacy")
        lattices = memory_lattices(state)
        lattices[LEGACY_L3] = l3
        prism_memory(state)["lattices"] = lattices
        state.setdefault("sss", {})["lattices"] = lattices

    if not args.force and not needs_l3_remigrate(state):
        rep = {"status": "noop", "reason": "needs_l3_remigrate=false"}
    elif args.force:
        rep = remigrate_l3_from_monolith(state) or {"status": "noop"}
    else:
        from casa.prisms.shared.migrate_progress import progress, set_progress_enabled

        set_progress_enabled(True)

        def _tok(done: int, total: int, shard: str) -> None:
            progress(f"  remigrate L3 tokens {done}/{total} (shard {shard})")

        rep = ensure_l3_sharded_for_export(state, on_token_progress=_tok) or {"status": "noop"}

    if args.write and rep.get("status") == "ok":
        from casa.prisms.shared.store_persist import save_runtime_state

        save_runtime_state(args.store_dir, state, force=True, thin=True)
        rep["written"] = str(fs)

    if args.compact and rep.get("status") == "ok":
        from casa.prisms.shared.compact_persist import compact_persist_store

        rep["compact_persist"] = compact_persist_store(
            args.store_dir,
            state,
            reason="remigrate_l3_phrase",
            remigrate_l2=False,
            remigrate_l3=False,
            progress=True,
        )

    report_path = args.store_dir / "l3_remigrate.report.json"
    report_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": rep.get("status"),
        "written": rep.get("written"),
        "shards": rep.get("shards") or rep.get("num_shards"),
        "tokens": rep.get("tokens"),
        "report_file": str(report_path),
    }
    cp = rep.get("compact_persist")
    if isinstance(cp, dict):
        summary["compact_persist"] = {
            k: cp[k]
            for k in (
                "status",
                "lattices_written",
                "skipped_vocab_lattices",
                "ltm_dir",
                "field_version",
            )
            if k in cp
        }
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
