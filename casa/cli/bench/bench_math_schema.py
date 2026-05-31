#!/usr/bin/env python3
"""Bench Exp L0: math schema@1 — F0 digest from field, no claim.text."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.shared.store_boot import boot_store


def run_bench(
    state: dict,
    bundle: dict,
    cues: list[dict],
    *,
    lattice_id: str = "schema-math",
) -> dict:
    ingest_math_bundle(state, bundle, lattice_id=lattice_id)
    lattices = memory_lattices(state)

    decoded = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    rows: list[dict] = []
    passed = 0
    for item in cues:
        cue = str(item.get("cue") or "")
        expect = str(item.get("expect_top") or item.get("expect") or "")
        min_score = int(item.get("min_score") or 1)
        ranked = rank_cue_on_f0(bundle, decoded, cue)
        top = ranked[0][0] if ranked else None
        top_score = ranked[0][1] if ranked else 0
        ok = top == expect and top_score >= min_score
        if ok:
            passed += 1
        rows.append(
            {
                "id": item.get("id"),
                "cue": cue,
                "expect_top": expect,
                "got_top": top,
                "top_score": top_score,
                "ranked": ranked[:5],
                "ok": ok,
            }
        )

    return {
        "schema_version": 1,
        "bench": "math_schema",
        "lattice_id": lattice_id,
        "decoded_concepts": decoded.get("concept_ids"),
        "math_tokens": decoded.get("math_tokens"),
        "passed": passed,
        "total": len(cues),
        "pass_rate": round(passed / max(1, len(cues)), 3),
        "items": rows,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench F0 math schema@1 (field-only ranking)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--cues", type=Path, required=True)
    p.add_argument("--boot-ltm-only", action="store_true", default=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    if not isinstance(cues, list):
        raise SystemExit("cues file must be a JSON array")

    if args.boot_ltm_only:
        state = boot_store(args.store_dir, prefer_field_state=False)["state"]
    else:
        from casa.prisms.shared.field_write import load_field_state

        state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))

    report = run_bench(state, bundle, cues)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
