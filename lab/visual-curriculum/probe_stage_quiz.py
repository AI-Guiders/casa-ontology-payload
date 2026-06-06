#!/usr/bin/env python3
"""Generic stage gate — held-out frames from any class manifest (agent KSA)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import finalize_honest_probe_report, generated_report_path, manifest_hints, setup_probe_imports


def _predict_for_hint(state, fid: str, hint: str):
    cid = str(hint or "").strip()
    if cid.startswith("math."):
        from casa.prisms.visual.bridge_math import predict_math_for_vis_cue

        return predict_math_for_vis_cue(state, fid, top_k=8)
    from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

    return predict_lex_for_vis_cue(state, fid, top_k=8)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--class-rel", default="lessons/literacy-cards")
    p.add_argument("--stage", required=True)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--store", default="von-neumann")
    args = p.parse_args()

    setup_probe_imports()
    from literacy_pedagogy import frames_for_stage
    from teacher_pedagogy import load_class_manifest, stage_probe_id

    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.bridge_math import vis_frame_concept_id

    from probe_lex_verdict import verdict_lex_probe

    manifest = load_class_manifest(args.class_rel)
    class_id = str(manifest.get("class_id") or Path(args.class_rel).name)
    frames = frames_for_stage(
        manifest,
        args.stage,
        limit=args.limit,
        offset=args.offset,
        order="frame_id",
    )
    frame_ids = [str(f["id"]) for f in frames]
    if not frame_ids:
        raise SystemExit(f"no frames for stage {args.stage!r}")

    hints = manifest_hints(args.class_rel)
    probe = stage_probe_id(class_id, args.stage)
    report_name = f"teacher-{class_id}-{args.stage}.json".replace(":", "-")
    report_path = generated_report_path(report_name)

    from probe_infra import default_store

    store = default_store(args.store)

    with store_session_lock(store, holder=f"probe:{probe}"):
        state = resolve_ingest_state(store, None)
        items: list[dict] = []
        counts = {"know": 0, "ambiguous": 0, "wrong": 0, "empty": 0}
        preds_field = "math_top" if args.class_rel.endswith("visual-cards") else "lex_top"

        for fid in frame_ids:
            hint = hints.get(fid, "")
            preds = _predict_for_hint(state, fid, hint)
            v = verdict_lex_probe(preds, hint)
            counts[str(v["verdict"])] = counts.get(str(v["verdict"]), 0) + 1
            items.append(
                {
                    "frame_id": fid,
                    "vis_concept": vis_frame_concept_id(fid),
                    "teacher_hint": hint or None,
                    "teacher_guess": v["teacher_guess"],
                    "verdict": v["verdict"],
                    "matches_hint": v["matches_hint"],
                    "top_score": v["top_score"],
                    preds_field: [{"concept_id": c, "score": s} for c, s in preds],
                }
            )

        out = {
            "store_id": args.store,
            "class_id": class_id,
            "class_rel": args.class_rel,
            "stage": args.stage,
            "probe": probe,
            "total": len(frame_ids),
            "know": counts["know"],
            "ambiguous": counts["ambiguous"],
            "wrong": counts["wrong"],
            "empty": counts["empty"],
            "matched": counts["know"],
            "items": items,
        }
        out = finalize_honest_probe_report(state, out, store=store, probe_id=probe)

    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": probe,
                "stage": args.stage,
                "know": counts["know"],
                "total": len(frame_ids),
                "gate_kind": out.get("gate_kind"),
                "path": str(report_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
