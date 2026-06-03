#!/usr/bin/env python3
"""Teacher probe for nline-set frames."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_state import resolve_ingest_state
from casa.cli.moment_plan import _FRAME_MATH
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.visual.bridge_math import predict_math_for_vis_cue, vis_frame_concept_id

FRAMES = (
    "nline-set-intersect",
    "nline-set-union",
    "nline-set-subset",
    "nline-set-disjoint",
    "nline-set-a-only",
)


def main() -> None:
    store = (_REPO / "agents" / "von-neumann").resolve()
    report_path = _REPO / "lab" / "visual-curriculum" / "reports" / "teacher-nline-set-quiz.json"

    with store_session_lock(store, holder="probe:nline-set-quiz"):
        state = resolve_ingest_state(store, None)
        items = []
        matched = 0
        for fid in FRAMES:
            row = _FRAME_MATH.get(fid)
            hint = row[2] if row else None
            preds = predict_math_for_vis_cue(state, fid, top_k=5)
            guess = preds[0][0] if preds else None
            top_score = preds[0][1] if preds else 0
            ok = hint is not None and guess == hint
            if ok:
                matched += 1
            items.append(
                {
                    "frame_id": fid,
                    "vis_concept": vis_frame_concept_id(fid),
                    "teacher_guess": guess,
                    "top_score": top_score,
                    "math_top": [{"concept_id": c, "score": s} for c, s in preds],
                    "teacher_hint": hint,
                    "matches_hint": ok,
                }
            )

    out = {
        "store_id": "von-neumann",
        "probe": "nline-set-quiz",
        "matched": matched,
        "total": len(FRAMES),
        "items": items,
    }
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"matched": matched, "total": len(FRAMES), "path": str(report_path)}, ensure_ascii=False))
    for it in items:
        mark = "OK" if it["matches_hint"] else "--"
        print(f"{mark} {it['frame_id']}: {it['teacher_guess']} (hint {it['teacher_hint']}, score {it['top_score']})")


if __name__ == "__main__":
    main()
