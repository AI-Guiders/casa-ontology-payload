#!/usr/bin/env python3
"""Run five Venn micro-moments (one vis+math per sleep)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_lesson_moment import ingest_lesson_moment

MICRO = [
    ("venn-micro-intersect", "venn-micro-intersect.json"),
    ("venn-micro-union", "venn-micro-union.json"),
    ("venn-micro-subset", "venn-micro-subset.json"),
    ("venn-micro-disjoint", "venn-micro-disjoint.json"),
    ("venn-micro-a-only", "venn-micro-a-only.json"),
]


def main() -> None:
    store = (_REPO / "agents" / "von-neumann").resolve()
    class_dir = (_REPO / "lessons" / "visual-cards").resolve()
    steps_dir = Path(__file__).resolve().parent
    reports_dir = _REPO / "lab" / "visual-curriculum" / "reports" / "micro-venn"
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    for moment_id, steps_file in MICRO:
        steps = json.loads((steps_dir / steps_file).read_text(encoding="utf-8"))
        t0 = time.time()
        rep = ingest_lesson_moment(
            store,
            class_dir,
            moment_id=moment_id,
            steps=steps,
            sleep=True,
            persist=True,
            report_path=reports_dir / f"moment-{moment_id}.json",
        )
        elapsed = round(time.time() - t0, 1)
        row = {
            "moment_id": moment_id,
            "bridges_emergent": rep.get("bridges_emergent"),
            "sleep_merged": rep.get("sleep_merged"),
            "elapsed_s": elapsed,
            "report_path": rep.get("report_path"),
        }
        summary.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    out = reports_dir / "summary.json"
    out.write_text(json.dumps({"moments": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"done": len(summary), "summary": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
