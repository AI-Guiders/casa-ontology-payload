#!/usr/bin/env python3
"""Teacher probe for venn-region frames (no runtime oracle)."""

from __future__ import annotations

import json

from probe_infra import default_store, generated_report_path, run_frame_probe, setup_probe_imports

REPORT_NAME = "teacher-venn-region-quiz.json"


def main() -> None:
    setup_probe_imports()
    report_path = generated_report_path(REPORT_NAME)
    old = json.loads(report_path.read_text(encoding="utf-8"))
    frames = [str(it["frame_id"]) for it in old["items"]]
    hints = {str(it["frame_id"]): it.get("teacher_hint") for it in old["items"]}

    def _hint(fid: str) -> str:
        h = hints.get(fid)
        return str(h) if h else ""

    def _predict(state, fid: str):
        from casa.prisms.visual.bridge_math import predict_math_for_vis_cue

        return predict_math_for_vis_cue(state, fid, top_k=5)

    def _extra(row: dict) -> dict:
        guess = row.get("teacher_guess")
        return {"is_num_not_set": guess is not None and str(guess).startswith("math.num.")}

    out = run_frame_probe(
        probe="venn-region-quiz",
        frames=frames,
        hint_for_frame=_hint,
        predict=_predict,
        report_filename=REPORT_NAME,
        lock_holder="probe:venn-region-quiz",
        preds_field="math_top",
        extra_out={
            "after": "micro-venn-5x",
            "total_with_hint": sum(1 for h in hints.values() if h),
        },
        line_extra=_extra,
    )
    for it in out["items"]:
        if it.get("teacher_hint"):
            mark = "OK" if it["verdict"] == "know" else "--"
            print(
                f"{mark} {it['frame_id']}: {it['teacher_guess']} "
                f"(hint {it['teacher_hint']}, score {it['top_score']})"
            )


if __name__ == "__main__":
    main()
