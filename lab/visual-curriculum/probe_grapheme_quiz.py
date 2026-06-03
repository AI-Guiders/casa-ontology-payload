#!/usr/bin/env python3
"""Teacher probe: letter frame → grapheme.cyrl.* (register from manifest concept_id)."""

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
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue
from casa.prisms.visual.bridge_math import vis_frame_concept_id

from probe_lex_verdict import verdict_lex_probe

PILOT_FRAMES = (
    "letter-a-lower-sans",
    "letter-a-upper-sans",
    "word-mama-sans",
    "word-kot-sans",
    "word-dom-sans",
)


def main() -> None:
    store = (_REPO / "agents" / "von-neumann").resolve()
    manifest = json.loads(
        (_REPO / "lessons" / "literacy-cards" / "class.manifest.json").read_text(encoding="utf-8")
    )
    hints = {str(f["id"]): str(f.get("concept_id") or "") for f in manifest.get("frames") or []}
    report_path = _REPO / "lab" / "visual-curriculum" / "reports" / "teacher-grapheme-quiz.json"

    with store_session_lock(store, holder="probe:grapheme-quiz"):
        state = resolve_ingest_state(store, None)
        items = []
        counts = {"know": 0, "ambiguous": 0, "wrong": 0, "empty": 0}
        for fid in PILOT_FRAMES:
            hint = hints.get(fid) or ""
            preds = predict_lex_for_vis_cue(state, fid, top_k=5)
            v = verdict_lex_probe(preds, hint)
            counts[str(v["verdict"])] = counts.get(str(v["verdict"]), 0) + 1
            items.append(
                {
                    "frame_id": fid,
                    "vis_concept": vis_frame_concept_id(fid),
                    "teacher_hint": hint,
                    "teacher_guess": v["teacher_guess"],
                    "verdict": v["verdict"],
                    "matches_hint": v["matches_hint"],
                    "top_score": v["top_score"],
                    "leaders": v["leaders"],
                    "lex_top": [{"concept_id": c, "score": s} for c, s in preds],
                }
            )

    out = {
        "probe": "literacy-quiz",
        "total": len(PILOT_FRAMES),
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
                "total": len(PILOT_FRAMES),
                "path": str(report_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
