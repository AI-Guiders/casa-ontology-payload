#!/usr/bin/env python3
"""Teacher probe: geometry figure → math.geom.* (Russian word on field)."""

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

from probe_lex_verdict import verdict_lex_probe

FRAMES = (
    "geom-circle",
    "geom-square",
    "geom-rectangle",
    "geom-stroke",
    "geom-segment",
    "geom-line",
)


def main() -> None:
    store = (_REPO / "agents" / "von-neumann").resolve()
    report_path = _REPO / "lab" / "visual-curriculum" / "generated" / "teacher-geom-lex-quiz.json"

    with store_session_lock(store, holder="probe:geom-lex-quiz"):
        state = resolve_ingest_state(store, None)
        items = []
        counts = {"know": 0, "ambiguous": 0, "wrong": 0, "empty": 0}
        for fid in FRAMES:
            row = _FRAME_MATH.get(fid)
            hint = str(row[2]) if row else ""
            preds = predict_math_for_vis_cue(state, fid, top_k=5)
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
                    "leaders": v["leaders"],
                    "math_top": [{"concept_id": c, "score": s} for c, s in preds],
                }
            )

    out = {
        "store_id": "von-neumann",
        "probe": "geom-lex-quiz",
        "total": len(FRAMES),
        "know": counts["know"],
        "ambiguous": counts["ambiguous"],
        "wrong": counts["wrong"],
        "empty": counts["empty"],
        "matched": counts["know"],
        "items": items,
    }
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "know": counts["know"],
                "ambiguous": counts["ambiguous"],
                "wrong": counts["wrong"],
                "total": len(FRAMES),
                "path": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    for it in items:
        mark = {"know": "OK", "ambiguous": "??", "wrong": "--", "empty": "  "}.get(str(it["verdict"]), "?")
        print(
            f"{mark} {it['frame_id']}: {it['teacher_guess']} "
            f"(hint {it['teacher_hint']}, score {it['top_score']}, verdict {it['verdict']})"
        )


if __name__ == "__main__":
    main()
