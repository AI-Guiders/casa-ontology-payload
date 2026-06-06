#!/usr/bin/env python3
"""Generic block held-out gate — reads block spec JSON (Blocks 1–5)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from block_pedagogy import gate_pass, held_out_frame_ids, load_block_spec
from probe_infra import manifest_hints, run_frame_probe


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--block", default="block-01-grapheme-cyrl")
    p.add_argument("--spec", type=Path, default=None)
    p.add_argument("--store", default="von-neumann")
    args = p.parse_args()

    spec = load_block_spec(args.spec, block_id=args.block)
    frame_ids = held_out_frame_ids(spec)
    if not frame_ids:
        raise SystemExit(f"no held-out frames for block {args.block!r}")

    class_rel = str(spec.get("class_rel") or "lessons/literacy-cards")
    hints = manifest_hints(class_rel)
    probe_id = str((spec.get("gate") or {}).get("probe_id") or f"probe_{args.block.replace('-', '_')}_held_out")
    report_name = f"teacher-probe-{args.block}-held-out.json"

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        return predict_lex_for_vis_cue(state, fid, top_k=5)

    report = run_frame_probe(
        probe=probe_id,
        frames=frame_ids,
        hint_for_frame=lambda fid: hints.get(fid, ""),
        predict=_predict,
        report_filename=report_name,
        lock_holder=f"probe:{probe_id}",
        preds_field="lex_top",
        store_id=args.store,
        extra_out={
            "block_id": spec.get("block_id"),
            "held_out": True,
            "held_out_count": len(frame_ids),
        },
        print_lines=False,
    )
    report["gate_pass"] = gate_pass(spec, report)
    out_path = Path(__file__).resolve().parent / "generated" / report_name
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": probe_id,
                "block": spec.get("block_id"),
                "know": report.get("know"),
                "total": report.get("total"),
                "gate_pass": report["gate_pass"],
                "path": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report["gate_pass"] else 1)


if __name__ == "__main__":
    main()
