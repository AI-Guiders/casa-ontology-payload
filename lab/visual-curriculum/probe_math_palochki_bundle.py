#!/usr/bin/env python3
"""Math-palochki bundle probe cues — sidecar spec lint (teacher-side)."""

from __future__ import annotations

import json
from pathlib import Path

from probe_infra import run_spec_regression, setup_probe_imports
from teacher_pedagogy import load_class_manifest

_REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    setup_probe_imports()
    manifest = load_class_manifest("lessons/math-palochki")
    cues = list(manifest.get("probe") or [])
    rows: list[dict] = []
    ok = True
    for row in cues:
        cue = str(row.get("cue") or "")
        expect = str(row.get("expect") or "").strip()
        valid = bool(expect.startswith("math."))
        if not valid:
            ok = False
        rows.append({"cue": cue, "expect": expect, "valid_id": valid})

    report = run_spec_regression(
        {
            "probe": "math-palochki-bundle",
            "pass": ok and bool(rows),
            "total": len(rows),
            "know": sum(1 for r in rows if r.get("valid_id")),
            "rows": rows,
        },
        report_filename="teacher-math-palochki-bundle.json",
    )
    raise SystemExit(0 if report.get("verdict_pass") else 1)


if __name__ == "__main__":
    main()
