#!/usr/bin/env python3
"""Run five nline-set micro-moments (one vis+math per sleep)."""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_state import resolve_ingest_state
from casa.cli.ingest_lesson_moment import ingest_lesson_moment
from casa.prisms.shared.store_persist import save_runtime_state

MICRO = [
    ("nline-micro-intersect", "nline-micro-intersect.json"),
    ("nline-micro-union", "nline-micro-union.json"),
    ("nline-micro-subset", "nline-micro-subset.json"),
    ("nline-micro-disjoint", "nline-micro-disjoint.json"),
    ("nline-micro-a-only", "nline-micro-a-only.json"),
]


def main() -> None:
    store = (_REPO / "agents" / "von-neumann").resolve()
    class_dir = (_REPO / "lessons" / "visual-cards").resolve()
    steps_dir = Path(__file__).resolve().parent
    reports_dir = _REPO / "lab" / "visual-curriculum" / "reports" / "micro-nline"
    reports_dir.mkdir(parents=True, exist_ok=True)

    print(json.dumps({"phase": "load_store", "store": str(store)}, ensure_ascii=False), flush=True)
    t_load = time.time()
    state = resolve_ingest_state(store, None)
    print(
        json.dumps({"phase": "ready", "load_s": round(time.time() - t_load, 1)}, ensure_ascii=False),
        flush=True,
    )

    summary: list[dict] = []
    try:
        for moment_id, steps_file in MICRO:
            steps = json.loads((steps_dir / steps_file).read_text(encoding="utf-8"))
            print(json.dumps({"phase": "moment_start", "moment_id": moment_id}, ensure_ascii=False), flush=True)
            t0 = time.time()
            rep = ingest_lesson_moment(
                store,
                class_dir,
                moment_id=moment_id,
                steps=steps,
                sleep=True,
                persist=False,
                state=state,
                report_path=reports_dir / f"moment-{moment_id}.json",
            )
            elapsed = round(time.time() - t0, 1)
            row = {
                "moment_id": moment_id,
                "bridges_emergent": rep.get("bridges_emergent"),
                "sleep_merged": rep.get("sleep_merged"),
                "elapsed_s": elapsed,
            }
            summary.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

        print(json.dumps({"phase": "persist_store"}, ensure_ascii=False), flush=True)
        t_p = time.time()
        persist_rep = save_runtime_state(store, state, force=True, thin=True, sync_ltm_on_save=True)
        print(
            json.dumps(
                {"phase": "persist_done", "persist_s": round(time.time() - t_p, 1), "saved": persist_rep.get("saved")},
                ensure_ascii=False,
            ),
            flush=True,
        )
    except Exception as exc:
        print(json.dumps({"error": repr(exc), "traceback": traceback.format_exc()}, ensure_ascii=False), flush=True)
        raise

    out = reports_dir / "summary.json"
    out.write_text(json.dumps({"moments": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"done": len(summary), "summary": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
