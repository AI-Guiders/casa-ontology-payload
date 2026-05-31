#!/usr/bin/env python3
"""Bench answer@k: from-field vs NCA repair path (Experiment J)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import time
from pathlib import Path

import torch

from casa.cli.bench.bench_answer_recall import _hit
from casa.prisms.shared.canonical import CANONICAL_CONCEPT_MODE, CANONICAL_FIELD_MIN_VOTES
from casa.prisms.shared.field_write import bundle_from_field_state, decode_field_grid, load_field_state
from casa.prisms.control.sn_cen_infer import _load_dmn, _run_dmn_repair, _run_from_field
from casa.prisms.control.sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--model", type=Path, default=None, help="NCA model.pt for repair path")
    p.add_argument("--layout", type=Path, default=Path("design/layout.json"))
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--dmn-steps", type=int, default=48)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    field_path = store / "field_state.json"
    layout = _read_json(args.layout)
    lines = [json.loads(x) for x in args.queries.read_text(encoding="utf-8").splitlines() if x.strip()]

    model_path = args.model
    if model_path is None:
        cand = store / "checkpoints" / "model_hard.pt"
        model_path = cand if cand.is_file() else None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle_name, bundle, _, _, _, _ = _run_from_field(field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES)

    field_hits = 0
    repair_hits = 0
    rows = []

    for row in lines:
        q = row["query"]
        expect = row.get("expect_substr") or []
        optional = bool(row.get("optional"))

        t0 = time.perf_counter()
        _, _, decoded_f, _, ms_f, _ = _run_from_field(field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES)
        dg = digest_from_decoded(decoded_f)
        gated_f = sn_route(dg, bundle=bundle)
        task_f = cen_plan(gated_f, bundle=bundle, user_query=q)
        blocks_f = task_to_dict(task_f).get("answer_blocks") or []
        ok_f = _hit(blocks_f, expect) if expect else bool(blocks_f)
        ms_field = (time.perf_counter() - t0) * 1000

        ok_r = False
        ms_repair = 0.0
        recovery = None
        if model_path and model_path.is_file():
            t1 = time.perf_counter()
            decoded_r, recovery = _run_dmn_repair(
                bundle,
                model_path.resolve(),
                layout=layout,
                damage_patches=args.damage_patches,
                seed=args.seed,
                steps=args.dmn_steps,
                device=device,
            )
            dg_r = digest_from_decoded(decoded_r)
            gated_r = sn_route(dg_r, bundle=bundle)
            task_r = cen_plan(gated_r, bundle=bundle, user_query=q)
            blocks_r = task_to_dict(task_r).get("answer_blocks") or []
            ok_r = _hit(blocks_r, expect) if expect else bool(blocks_r)
            ms_repair = (time.perf_counter() - t1) * 1000

        if not optional:
            field_hits += 1 if ok_f else 0
            if model_path:
                repair_hits += 1 if ok_r else 0

        rows.append({
            "query": q,
            "optional": optional,
            "field_hit": ok_f,
            "field_ms": round(ms_field, 2),
            "repair_hit": ok_r if model_path else None,
            "repair_ms": round(ms_repair, 2) if model_path else None,
            "recovery_concepts_f1": (recovery or {}).get("concepts", {}).get("f1") if recovery else None,
        })

    scored = [r for r in rows if not r.get("optional")]
    n = len(scored) or 1
    report = {
        "store": str(store),
        "bundle": bundle_name,
        "model": str(model_path) if model_path else None,
        "queries": len(lines),
        "scored_queries": len(scored),
        "answer_at_1_field": field_hits / n,
        "answer_at_1_repair": (repair_hits / n) if model_path else None,
        "results": rows,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
