#!/usr/bin/env python3
"""T_sleep + NCA regrow for every model in state.nca.models."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.prism_ids import PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL
from casa.domain.prism_wire import normalize_prisms, prism_memory, prism_hippo, prism_control, set_active_prism
import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices, run_sleep
from casa.prisms.memory.lexicon_shard import nca_model_registry
from casa.prisms.memory.nca_repair import nca_regrow_lattice


def regrow_all_nca(state: dict, *, device: str = "cpu") -> list[dict]:
    lattices = memory_lattices(state)
    rows: list[dict] = []
    for lid, raw in nca_model_registry(state).items():
        mp = Path(str(raw))
        if not mp.is_file() or lid not in lattices:
            rows.append({"lattice_id": lid, "skipped": True, "reason": "missing model or lattice"})
            continue
        rep = nca_regrow_lattice(lattices[lid], mp, device=device)
        lattices[lid] = rep["lattice"]
        rows.append({"lattice_id": lid, "regrow": {k: v for k, v in rep.items() if k != "lattice"}})
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--device", default="cpu")
    p.add_argument("--sleep-first", action="store_true", default=True)
    p.add_argument("--no-sleep-first", action="store_false", dest="sleep_first")
    args = p.parse_args()

    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))

    sleep_rep = None
    if args.sleep_first:
        state["sn"] = {**(state.get("sn") or {}), "mode": "sleep"}
        sleep_rep = run_sleep(state, bundle)

    regrows = regrow_all_nca(state, device=args.device)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    save_field_state(path, state, compact=True)

    print(
        json.dumps(
            {"sleep": sleep_rep, "nca_regrow": regrows, "field_version": state.get("field_version")},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
